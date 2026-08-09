"""Restricted automation actions for a dedicated PolyNexus GUI window."""

from __future__ import annotations

import json
import math
import secrets
import tempfile
from pathlib import Path
from typing import Any, Mapping

from PySide6.QtCore import QTimer
from PySide6.QtNetwork import QHostAddress, QTcpServer, QTcpSocket

_TECHNIQUES = frozenset({"dsc", "ir", "nmr", "saxs", "waxs"})
_MAX_REQUEST_BYTES = 64 * 1024


class GuiAutomationBridge:
    """Expose fixed, authenticated actions without reflecting on the window."""

    def __init__(self, window: Any, *, secret: str) -> None:
        if not secret:
            raise ValueError("automation secret must not be empty")
        self._window = window
        self._secret = secret
        self._server: QTcpServer | None = None
        self._clients: list[QTcpSocket] = []
        self._buffers: dict[int, bytearray] = {}

    @property
    def is_listening(self) -> bool:
        return self._server is not None and self._server.isListening()

    def start(self, port: int) -> dict[str, Any]:
        """Open an automation listener on IPv4 loopback only."""
        if self.is_listening:
            raise RuntimeError("automation bridge is already listening")
        server = QTcpServer()
        if not server.listen(QHostAddress.LocalHost, int(port)):
            raise RuntimeError(f"automation bridge failed to listen: {server.errorString()}")
        server.newConnection.connect(self._on_new_connection)
        self._server = server
        return {"host": "127.0.0.1", "port": int(server.serverPort())}

    def close(self) -> None:
        """Release the local listener owned by this bridge."""
        for client in self._clients:
            client.disconnectFromHost()
            client.deleteLater()
        self._clients.clear()
        self._buffers.clear()
        if self._server is not None:
            self._server.close()
            self._server.deleteLater()
            self._server = None

    def _on_new_connection(self) -> None:
        if self._server is None:
            return
        while self._server.hasPendingConnections():
            client = self._server.nextPendingConnection()
            if not client.peerAddress().isLoopback():
                client.disconnectFromHost()
                client.deleteLater()
                continue
            self._clients.append(client)
            self._buffers[id(client)] = bytearray()
            client.readyRead.connect(lambda client=client: self._on_ready_read(client))
            client.disconnected.connect(lambda client=client: self._on_client_disconnected(client))

    def _on_client_disconnected(self, client: QTcpSocket) -> None:
        self._buffers.pop(id(client), None)
        if client in self._clients:
            self._clients.remove(client)
        client.deleteLater()

    def _on_ready_read(self, client: QTcpSocket) -> None:
        buffer = self._buffers.get(id(client))
        if buffer is None:
            return
        buffer.extend(bytes(client.readAll()))
        if len(buffer) > _MAX_REQUEST_BYTES:
            self._write_response(client, {"ok": False, "error": {"code": "request_too_large"}})
            client.disconnectFromHost()
            return
        while b"\n" in buffer:
            raw, _, remaining = buffer.partition(b"\n")
            buffer[:] = remaining
            if not raw:
                continue
            try:
                request = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                response = {"ok": False, "error": {"code": "invalid_request"}}
            else:
                response = (
                    self.handle_request(request)
                    if isinstance(request, Mapping)
                    else {"ok": False, "error": {"code": "invalid_request"}}
                )
            self._write_response(client, response)

    @staticmethod
    def _write_response(client: QTcpSocket, response: Mapping[str, Any]) -> None:
        client.write((json.dumps(response, allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8"))
        client.flush()

    def handle_request(self, request: Mapping[str, Any]) -> dict[str, Any]:
        """Handle one already-decoded request from the local automation client."""
        supplied_secret = str(request.get("secret", ""))
        if not secrets.compare_digest(supplied_secret, self._secret):
            return {"ok": False, "error": {"code": "unauthorized"}}

        action = str(request.get("action", ""))
        if action == "status":
            return {"ok": True, "status": self._status()}
        if action == "import_file":
            return self._import_file(request)
        if action == "select_technique":
            return self._select_technique(request)
        if action == "run_analysis":
            return self._run_analysis()
        if action == "get_result":
            return self._get_result()
        if action == "capture_window":
            return self._capture_window()
        if action == "close":
            return self._close_window()
        return {"ok": False, "error": {"code": "unsupported_action"}}

    def _import_file(self, request: Mapping[str, Any]) -> dict[str, Any]:
        path = Path(str(request.get("path", ""))).expanduser()
        technique = str(request.get("technique", "")).strip().lower()
        if not path.is_file():
            return {"ok": False, "error": {"code": "invalid_file"}}
        if technique not in _TECHNIQUES:
            return {"ok": False, "error": {"code": "invalid_technique"}}

        self._window._apply_import_selection(
            str(path),
            is_dir=False,
            input_mode="single",
            technique=technique,
        )
        return {"ok": True, "status": self._status()}

    def _select_technique(self, request: Mapping[str, Any]) -> dict[str, Any]:
        technique = str(request.get("technique", "")).strip().lower()
        if technique not in _TECHNIQUES:
            return {"ok": False, "error": {"code": "invalid_technique"}}
        self._window._on_technique_selected(technique)
        return {"ok": True, "status": self._status()}

    def _run_analysis(self) -> dict[str, Any]:
        self._window._run_analysis()
        return {"ok": True, "status": self._status()}

    def _get_result(self) -> dict[str, Any]:
        technique = str(getattr(self._window, "_current_technique", ""))
        result = getattr(self._window, "_results", {}).get(technique)
        if result is None:
            return {"ok": False, "error": {"code": "result_unavailable"}}
        payload = result.to_dict() if hasattr(result, "to_dict") else result
        return {"ok": True, "result": _json_safe(payload)}

    def _capture_window(self) -> dict[str, Any]:
        destination = Path(tempfile.mkdtemp(prefix="polynexus-automation-")) / "window.png"
        if not self._window.grab().save(str(destination)):
            return {"ok": False, "error": {"code": "capture_failed"}}
        return {"ok": True, "path": str(destination)}

    def _close_window(self) -> dict[str, Any]:
        self._window.close()
        QTimer.singleShot(0, self.close)
        return {"ok": True}

    def _status(self) -> dict[str, Any]:
        run_state = getattr(self._window, "_run_state", None)
        status = getattr(run_state, "status", "idle")
        run_status = str(getattr(status, "value", status)).lower()
        return {
            "technique": str(getattr(self._window, "_current_technique", "")),
            "path": str(getattr(self._window, "_current_filepath", "")),
            "has_result": bool(
                getattr(self._window, "_results", {}).get(
                    str(getattr(self._window, "_current_technique", ""))
                )
            ),
            "run_status": run_status,
        }


def _json_safe(value: Any) -> Any:
    """Convert only response values to strict JSON-compatible data."""
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, bool)):
        return value
    return str(value)
