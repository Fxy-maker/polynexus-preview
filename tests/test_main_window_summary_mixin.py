from __future__ import annotations

from types import SimpleNamespace

from polynexus.gui.main_window import MainWindow
from polynexus.gui.main_window_summary_mixin import MainWindowSummaryMixin
from polynexus.gui.i18n import get_language, set_language, tr


class _DummyWindow(MainWindowSummaryMixin):
    def __init__(self) -> None:
        self._current_filepath = r"D:\data\input.csv"
        self._current_input_mode = "sequence"
        self._current_technique = "ir"
        self._current_result_confirmed_flag = False

    def _current_result_origin(self) -> str:
        return "manual_run"

    def _current_analysis_evidence(self):
        return {}

    def _has_condition_axis_risk(self, params, analysis_evidence=None):
        return False

    def _has_fallback_conflict_risk(self, analysis_evidence=None):
        return False

    def _waxs_structure_evidence(self, analysis_evidence=None):
        return {}

    def _waxs_support_snapshot(self, analysis_evidence=None):
        return {}


def test_main_window_summary_mixin_formats_core_copy_and_risk_texts():
    previous = get_language()
    try:
        set_language("en")
        window = _DummyWindow()

        assert window._series_scope_summary_text(1) == tr("RESULTS_SUMMARY_SCOPE_SINGLE_SAMPLE_FRAME")
        assert window._series_scope_summary_text(3) == tr("RESULTS_SUMMARY_SCOPE_SINGLE_SAMPLE_FRAMES", 3)
        assert window._frame_results_summary_text(2) == tr("RESULTS_SUMMARY_SEQUENCE", tr("RESULTS_SUMMARY_SCOPE_SINGLE_SAMPLE_FRAMES", 2), "input.csv")
        assert window._batch_results_summary_text(4) == tr("RESULTS_SUMMARY_BATCH", 4, "input.csv")
        assert window._single_results_summary_text({"a": 1, "b": 2}) == tr("RESULTS_SUMMARY_SINGLE", 2, "input.csv")
        assert window._display_text_value(None) == tr("AI_TUNING_EMPTY_VALUE")
        assert window._display_text({"a": 1}) == '{"a": 1}'
        assert window._quality_flag_summary_text({"quality_flag": "WARN:low_snr"}) == "low peak SNR"
        assert window._results_has_critical_risk({}, SimpleNamespace(validation_summary="Needs review")) is True
        assert window._results_has_critical_risk({}, SimpleNamespace(validation_summary="All checks passed")) is False
        assert window._results_next_step_text({}, result=None) == tr("RESULTS_SUMMARY_NEXT_SEQUENCE")
        assert window._ordered_results_columns(["unknown", "L_nm", "L_nm", "sample"]) == ["sample", "L_nm", "unknown"]
    finally:
        set_language(previous)


def test_main_window_reuses_summary_and_work_memory_helpers_from_summary_mixin():
    assert MainWindow._work_memory_payload is MainWindowSummaryMixin._work_memory_payload
    assert MainWindow._work_memory_summary is MainWindowSummaryMixin._work_memory_summary
    assert MainWindow._update_work_memory_panel is MainWindowSummaryMixin._update_work_memory_panel
    assert MainWindow._workspace_context_summary is MainWindowSummaryMixin._workspace_context_summary
    assert MainWindow._joint_ai_context is MainWindowSummaryMixin._joint_ai_context
    assert MainWindow._joint_ai_reminder_text is MainWindowSummaryMixin._joint_ai_reminder_text
    assert MainWindow._joint_compare_hint_text is MainWindowSummaryMixin._joint_compare_hint_text
