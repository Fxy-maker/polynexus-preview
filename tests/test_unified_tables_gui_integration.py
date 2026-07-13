from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtWidgets import QApplication, QLabel

from polynexus.gui.i18n import get_language, set_language
from polynexus.gui.main_window import MainWindow
from polynexus.gui.workspace_mode import WorkspaceMode


def _temperature_params() -> dict:
    return {
        "batch_frames": 2,
        "_batch_data": [
            {
                "temperature_C": 185.0,
                "stage": "heating",
                "L_nm": 11.234,
                "lc_nm": 4.126,
                "lc_method": "calibrated",
                "melting_window_status": "near_onset",
                "lc_reliability_status": "low_confidence",
            },
            {
                "temperature_C": 205.0,
                "stage": "heating",
                "L_nm": 12.0,
                "lc_nm": 2.0,
                "lc_method": "raw",
                "melting_window_status": "within_window",
                "lc_reliability_status": "usable",
            },
        ],
    }


def _close_window(window: MainWindow) -> None:
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    app = QApplication.instance()
    if app is not None:
        app.processEvents()


def test_main_window_renders_structured_results_through_unified_panel() -> None:
    app = QApplication.instance() or QApplication([])
    previous = get_language()
    set_language("en")
    window = MainWindow()
    try:
        window._current_technique = "saxs"
        window._current_submodule_id = "saxs.temperature"
        window._display_results(_temperature_params())
        app.processEvents()

        assert window._results_table is window._results_panel.primary_table
        assert not window._results_panel.isHidden()
        assert window._current_results_table_model.kind == "saxs.temperature"
        assert window._results_panel.tabs.isTabVisible(1)
        assert window._results_panel.tabs.isTabVisible(2)
        assert window._results_table.item(0, 2).data(Qt.UserRole) == 11.234
        assert any(
            label.text() == "Review"
            for label in window._results_table.findChildren(QLabel)
            if label.property("resultStatus") is not None
        )
        assert any(
            "calibrated" in (window._results_table.item(0, column).toolTip() or "")
            for column in range(window._results_table.columnCount())
        )
    finally:
        _close_window(window)
        set_language(previous)


def test_workspace_switch_keeps_current_structured_table_context() -> None:
    QApplication.instance() or QApplication([])
    window = MainWindow()
    try:
        window._current_technique = "saxs"
        window._current_submodule_id = "saxs.temperature"
        window._display_results(_temperature_params())
        raw_value = window._results_table.item(0, 2).data(Qt.UserRole)

        window._set_workspace_mode(WorkspaceMode.JOINT)
        window._update_workspace_context()
        window._set_workspace_mode(WorkspaceMode.ANALYSIS)
        window._update_workspace_context()

        assert window._current_results_table_model.kind == "saxs.temperature"
        assert window._results_table.item(0, 2).data(Qt.UserRole) == raw_value
        assert window._results_panel.primary_table is window._results_table
    finally:
        _close_window(window)


def test_history_restore_rehydrates_structured_table_context(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    data_file = tmp_path / "history.edf"
    data_file.write_text("placeholder", encoding="utf-8")
    window = MainWindow()
    try:
        record = {
            "technique": "saxs",
            "submodule": "saxs.temperature",
            "parameters": _temperature_params(),
            "results_summary": {
                "data_file": str(data_file),
                "confirmed": True,
            },
        }

        assert window._restore_history_record(record)
        app.processEvents()

        assert window._current_results_table_model.kind == "saxs.temperature"
        assert window._results_table.item(0, 2).data(Qt.UserRole) == 11.234
        assert not window._results_panel.isHidden()
        assert window._current_result_confirmed_flag is True
    finally:
        _close_window(window)


def test_history_restore_without_submodule_clears_stale_structured_context(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    data_file = tmp_path / "legacy.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")
    window = MainWindow()
    try:
        window._current_technique = "saxs"
        window._current_submodule_id = "saxs.temperature"
        window._display_results(_temperature_params())

        record = {
            "technique": "saxs",
            "parameters": {"L_nm": 12.0, "Xc": 0.31},
            "results_summary": {"data_file": str(data_file)},
        }
        assert window._restore_history_record(record)
        app.processEvents()

        assert window._current_submodule_id == ""
        assert window._current_results_table_model.kind == "single"
        assert window._current_results_table_model.primary_section is None
        assert window._results_table.horizontalHeaderItem(0).text() == "Parameter"
    finally:
        _close_window(window)


def test_retranslate_rebuilds_structured_headers_without_changing_raw_values() -> None:
    app = QApplication.instance() or QApplication([])
    previous = get_language()
    set_language("en")
    window = MainWindow()
    try:
        window._current_technique = "saxs"
        window._current_submodule_id = "saxs.temperature"
        window._display_results(_temperature_params())
        raw_value = window._results_table.item(0, 2).data(Qt.UserRole)
        english_header = window._results_table.horizontalHeaderItem(0).text()

        set_language("zh")
        window._retranslate_ui()
        app.processEvents()

        assert english_header == "Temperature / °C"
        assert window._results_table.horizontalHeaderItem(0).text() == "温度 / °C"
        assert window._results_table.item(0, 2).data(Qt.UserRole) == raw_value
        assert any(
            label.text() == "需复核"
            for label in window._results_table.findChildren(QLabel)
            if label.property("resultStatus") is not None
        )
    finally:
        _close_window(window)
        set_language(previous)
