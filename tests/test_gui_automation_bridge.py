from __future__ import annotations

import json
from pathlib import Path
import socket
import time

import pytest
from PySide6.QtCore import QCoreApplication

from polynexus.core.engine import AnalysisResult
from polynexus.gui.automation_bridge import GuiAutomationBridge


class FakeWindow:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []
        self._current_filepath = ""
        self._current_technique = ""
        self._results: dict[str, AnalysisResult] = {}

    def _apply_import_selection(self, path: str, **kwargs: object) -> None:
        self.calls.append(("import", path, kwargs))
        self._current_filepath = path
        self._current_technique = str(kwargs["technique"])

    def _run_analysis(self) -> None:
        self.calls.append(("run",))
        self._results[self._current_technique] = AnalysisResult(
            technique=self._current_technique,
            parameters={"tg": 50.0},
        )

    def _on_technique_selected(self, technique: str) -> None:
        self.calls.append(("select", technique))
        self._current_technique = technique

    def close(self) -> None:
        self.calls.append(("close",))

    def grab(self):
        class FakePixmap:
            def save(self, path: str) -> bool:
                Path(path).write_bytes(b"png")
                return True

        return FakePixmap()


def test_bridge_rejects_wrong_secret_without_calling_window() -> None:
    window = FakeWindow()
    bridge = GuiAutomationBridge(window, secret="expected")

    reply = bridge.handle_request({"secret": "wrong", "action": "status"})

    assert reply == {"ok": False, "error": {"code": "unauthorized"}}
    assert window.calls == []


def test_bridge_import_select_run_and_return_existing_result(tmp_path: Path) -> None:
    source = tmp_path / "curve.csv"
    source.write_text("x,y\n1,2\n", encoding="utf-8")
    window = FakeWindow()
    bridge = GuiAutomationBridge(window, secret="expected")

    imported = bridge.handle_request(
        {
            "secret": "expected",
            "action": "import_file",
            "path": str(source),
            "technique": "dsc",
        }
    )
    started = bridge.handle_request({"secret": "expected", "action": "run_analysis"})
    result = bridge.handle_request({"secret": "expected", "action": "get_result"})

    assert imported["ok"] is True
    assert started["ok"] is True
    assert window.calls == [
        ("import", str(source), {"is_dir": False, "input_mode": "single", "technique": "dsc"}),
        ("run",),
    ]
    assert result == {
        "ok": True,
        "result": {
            "technique": "dsc",
            "category": "experimental",
            "parameters": {"tg": 50.0},
            "validation_passed": True,
            "quality_flags": {},
            "validation_warnings": [],
            "validation_summary": "",
            "metadata": {},
            "analysis_evidence": {},
            "effective_q_min": None,
            "logs": [],
        },
    }


def test_app_automation_startup_creates_and_closes_bridge(monkeypatch: pytest.MonkeyPatch) -> None:
    from polynexus import app as app_module

    created: list[FakeServerBridge] = []

    class FakeServerBridge:
        def __init__(self, window: object, *, secret: str) -> None:
            self.window = window
            self.secret = secret
            self.started_port: int | None = None
            self.closed = False
            created.append(self)

        def start(self, port: int) -> dict[str, object]:
            self.started_port = port
            return {"host": "127.0.0.1", "port": 43123}

        def close(self) -> None:
            self.closed = True

    monkeypatch.setattr("polynexus.gui.automation_bridge.GuiAutomationBridge", FakeServerBridge)

    assert app_module.main(startup_probe=True, automation_port=0, automation_secret="expected") == 0
    assert len(created) == 1
    assert created[0].secret == "expected"
    assert created[0].started_port == 0
    assert created[0].closed is True


def test_bridge_listens_only_on_loopback_and_releases_port() -> None:
    QCoreApplication.instance() or QCoreApplication([])
    bridge = GuiAutomationBridge(FakeWindow(), secret="expected")

    ready = bridge.start(0)

    assert ready["host"] == "127.0.0.1"
    assert isinstance(ready["port"], int)
    assert ready["port"] > 0

    bridge.close()
    assert bridge.is_listening is False


def test_loopback_protocol_rejects_wrong_secret_without_window_calls() -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    window = FakeWindow()
    bridge = GuiAutomationBridge(window, secret="expected")
    ready = bridge.start(0)
    client = socket.create_connection((ready["host"], ready["port"]), timeout=2)
    try:
        client.setblocking(False)
        client.sendall(b'{"secret":"wrong","action":"status"}\n')
        deadline = time.monotonic() + 2
        response = b""
        while b"\n" not in response and time.monotonic() < deadline:
            app.processEvents()
            try:
                response += client.recv(4096)
            except BlockingIOError:
                pass
            time.sleep(0.01)
        assert json.loads(response.decode("utf-8")) == {
            "ok": False,
            "error": {"code": "unauthorized"},
        }
        assert window.calls == []
    finally:
        client.close()
        bridge.close()


def test_bridge_supports_fixed_selection_status_capture_and_close_actions() -> None:
    window = FakeWindow()
    bridge = GuiAutomationBridge(window, secret="expected")

    selected = bridge.handle_request(
        {"secret": "expected", "action": "select_technique", "technique": "ir"}
    )
    status = bridge.handle_request({"secret": "expected", "action": "status"})
    captured = bridge.handle_request({"secret": "expected", "action": "capture_window"})
    closed = bridge.handle_request({"secret": "expected", "action": "close"})

    assert selected["ok"] is True
    assert status == {
        "ok": True,
        "status": {"technique": "ir", "path": "", "has_result": False, "run_status": "idle"},
    }
    assert Path(captured["path"]).read_bytes() == b"png"
    assert closed == {"ok": True}
    assert window.calls == [("select", "ir"), ("close",)]
