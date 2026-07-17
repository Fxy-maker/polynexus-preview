from __future__ import annotations

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication

from polynexus.gui.i18n import get_language, set_language, tr
from polynexus.gui.main_window import MainWindow


def test_main_window_reuses_retranslate_helpers_from_retranslate_mixin() -> None:
    from polynexus.gui.main_window_retranslate_mixin import MainWindowRetranslateMixin

    assert MainWindow._retranslate_ui is MainWindowRetranslateMixin._retranslate_ui
    assert MainWindow._toggle_language is MainWindowRetranslateMixin._toggle_language


def test_retranslate_rebuilds_batch_results_source_in_current_language() -> None:
    QApplication.instance() or QApplication([])
    previous_language = get_language()
    set_language("en")
    window = MainWindow()
    try:
        window._current_filepath = "batch-input"
        window._current_technique = "saxs"
        window._current_submodule_id = "saxs.temperature"
        window._show_batch_results(
            [
                {"file": "a.dat", "params": {"temperature_C": 100}},
                {"file": "b.dat", "params": {"temperature_C": 120}},
            ]
        )
        english_summary = window._results_summary_label.text()
        assert window._current_results_table_source["kind"] == "batch"

        set_language("zh")
        window._retranslate_ui()

        assert window._current_results_table_source["kind"] == "batch"
        assert window._results_summary_label.text() == tr(
            "RESULTS_SUMMARY_BATCH", 2, "batch-input"
        )
        assert window._results_summary_label.text() != english_summary
    finally:
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        set_language(previous_language)
