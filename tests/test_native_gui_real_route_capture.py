"""Native Windows Qt acceptance for real shared GUI routes.

The test is intentionally skipped under the normal offscreen pytest setup.
Run it with ``QT_QPA_PLATFORM=windows`` and an external basetemp when a live
font/route capture is required.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication

from polynexus.core.engine import get_engine
from polynexus.gui.main_window import MainWindow
from polynexus.gui.plot_gallery_service import build_active_manifest_gallery_entries
from polynexus.origin.package_exporter import PackageExporter
from polynexus.origin.service import OriginExportService
from tests.test_real_published_run_walkthrough import (
    _full_2d_real_cases,
    _real_cases,
)


_NATIVE_CASES = tuple(dict.fromkeys((*_real_cases(), *_full_2d_real_cases())))


pytestmark = pytest.mark.skipif(
    os.environ.get("QT_QPA_PLATFORM", "").lower() != "windows",
    reason="native GUI acceptance requires QT_QPA_PLATFORM=windows",
)


@pytest.fixture(autouse=True)
def _cleanup_qt_widgets():
    yield
    app = QApplication.instance()
    if app is None:
        return
    for widget in QApplication.topLevelWidgets():
        widget.close()
        widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()


def _capture_root(tmp_path: Path) -> Path:
    configured = str(os.environ.get("POLYNEXUS_NATIVE_GUI_CAPTURE_DIR", "") or "").strip()
    root = Path(configured) if configured else tmp_path / "native_gui_captures"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _mode_slug(mode: str) -> str:
    return mode.replace(".", "_").replace("-", "_")


@pytest.mark.parametrize(
    "technique,mode,source",
    _NATIVE_CASES,
    ids=[case[1] for case in _NATIVE_CASES],
)
def test_native_windows_gui_real_route_capture(
    tmp_path: Path,
    technique: str,
    mode: str,
    source: Path,
) -> None:
    if not source.exists():
        pytest.skip(f"real fixture unavailable: {source}")

    output_root = tmp_path / "output"
    config = {"fig_format": "png"}
    if technique == "nmr":
        config["max_peaks"] = 18
    result = get_engine(technique, config=config, submodule_id=mode).run_pipeline(
        str(source), str(output_root)
    )
    run_id = str(result.metadata.get("figure_run_id") or "")
    entries = build_active_manifest_gallery_entries(output_root)
    assert run_id and entries

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.finish_deferred_startup()
    assert window._restore_history_record(
        {
            "id": f"native-{mode}",
            "technique": technique,
            "submodule": mode,
            "created_at": "2026-07-28 00:00:00",
            "output_dir": str(output_root),
            "parameters": {},
            "results_summary": {"data_file": str(source)},
        }
    )
    window._populate_plots()
    window.resize(1600, 1000)
    window.show()
    app.processEvents()

    assert window._current_submodule_id == mode
    assert window._tabs.count() >= 5
    assert window._chart_gallery._entries

    capture_root = _capture_root(tmp_path)
    slug = _mode_slug(mode)
    for index, surface in ((2, "results"), (3, "gallery"), (4, "history")):
        window._tabs.setCurrentIndex(index)
        app.processEvents()
        assert window.grab().save(str(capture_root / f"{slug}_{surface}.png"))

    window._tabs.setCurrentIndex(3)
    app.processEvents()
    entry = window._chart_gallery.current_entry()
    assert entry is not None
    window._open_selected_chart_editor(entry)
    app.processEvents()
    editor = getattr(window, "_chart_editor", None)
    assert editor is not None
    editor.resize(1500, 950)
    editor.show()
    app.processEvents()
    assert editor.grab().save(str(capture_root / f"{slug}_editor.png"))

    # Native acceptance must not launch a user's installed Origin process. It
    # still exercises the real Editor menu, worker thread, and package output.
    editor._origin_export_service = OriginExportService((PackageExporter(),))
    export_action = editor._header_export_actions["origin"]
    assert export_action.isEnabled()
    # Trigger the QAction exposed by the real Export popup. Opening a native
    # QMenu with QTest.mouseClick can block on Windows window activation.
    export_action.trigger()
    deadline = time.monotonic() + 20.0
    while getattr(editor, "_origin_export_thread", None) is not None:
        app.processEvents()
        if time.monotonic() >= deadline:
            break
        time.sleep(0.02)
    assert editor._origin_export_thread is None
    export_root = Path(editor._default_origin_output_root()) / "Origin_Export"
    assert (export_root / "figure_document.json").is_file()
    assert (export_root / "metadata.json").is_file()
    assert (export_root / "import.ogs").is_file()
    print(f"NATIVE_GUI_EXPORT {mode} root={export_root}")
    print(f"NATIVE_GUI_ROUTE {mode} run={run_id} captures={capture_root}")
