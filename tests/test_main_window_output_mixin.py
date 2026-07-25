from __future__ import annotations

from polynexus.gui.main_window import MainWindow
from polynexus.gui.main_window_output_mixin import MainWindowOutputMixin
from polynexus.gui.i18n import tr


class _ResultsPanelRecorder:
    def __init__(self) -> None:
        self.review_hint_calls = []
        self.clear_review_hint_calls = 0

    def set_review_hint(self, **kwargs) -> None:
        self.review_hint_calls.append(kwargs)

    def clear_review_hint(self) -> None:
        self.clear_review_hint_calls += 1


class _ResultsHintWindow:
    def __init__(self, technique: str, submodule_id: str) -> None:
        self._current_technique = technique
        self._current_submodule_id = submodule_id
        self._results_panel = _ResultsPanelRecorder()
        self.jump_targets = []

    def _jump_to_tab(self, index: int) -> None:
        self.jump_targets.append(index)


def test_main_window_reuses_output_and_export_helpers_from_output_mixin():
    assert MainWindow._set_results_summary is MainWindowOutputMixin._set_results_summary
    assert (
        MainWindow._set_results_default_order_control_visible
        is MainWindowOutputMixin._set_results_default_order_control_visible
    )
    assert (
        MainWindow._set_results_copy_control_visible
        is MainWindowOutputMixin._set_results_copy_control_visible
    )
    assert (
        MainWindow._set_results_export_control_visible
        is MainWindowOutputMixin._set_results_export_control_visible
    )
    assert (
        MainWindow._store_results_table_default_order
        is MainWindowOutputMixin._store_results_table_default_order
    )
    assert (
        MainWindow._clear_results_table_default_order
        is MainWindowOutputMixin._clear_results_table_default_order
    )
    assert (
        MainWindow._restore_results_table_default_order
        is MainWindowOutputMixin._restore_results_table_default_order
    )
    assert (
        MainWindow._copy_results_table_to_clipboard
        is MainWindowOutputMixin._copy_results_table_to_clipboard
    )
    assert MainWindow._results_table_text_matrix is MainWindowOutputMixin._results_table_text_matrix
    assert MainWindow._export_results_table is MainWindowOutputMixin._export_results_table
    assert MainWindow._display_table_rows is MainWindowOutputMixin._display_table_rows
    assert MainWindow._set_results_item is MainWindowOutputMixin._set_results_item
    assert (
        MainWindow._apply_results_table_layout is MainWindowOutputMixin._apply_results_table_layout
    )
    assert MainWindow._display_joint_report is MainWindowOutputMixin._display_joint_report
    assert MainWindow._show_batch_results is MainWindowOutputMixin._show_batch_results
    assert MainWindow._display_results is MainWindowOutputMixin._display_results
    assert MainWindow._export_context_payload is MainWindowOutputMixin._export_context_payload
    assert MainWindow._export_results is MainWindowOutputMixin._export_results


def test_saxs_temperature_summary_updates_results_review_hint_recorder():
    window = _ResultsHintWindow("saxs", "saxs.temperature")

    MainWindowOutputMixin._update_results_review_hint(
        window,
        summary="温度总览完成",
        risk_text="1 帧需复核",
        next_text="先查看温度总览",
    )

    assert len(window._results_panel.review_hint_calls) == 1
    call = window._results_panel.review_hint_calls[0]
    assert call["title"] == "温度总览完成"
    assert call["detail"] == "1 帧需复核"
    assert call["next_text"] == "先查看温度总览"
    assert call["status"] == "review"
    assert call["action_text"]
    assert callable(call["action"])

    window._current_technique = "waxs"
    MainWindowOutputMixin._update_results_review_hint(
        window,
        summary="其他技术结果",
        risk_text="其他技术风险",
        next_text="其他技术下一步",
    )

    assert len(window._results_panel.review_hint_calls) == 1
    assert window._results_panel.clear_review_hint_calls == 1


def test_saxs_strain_summary_updates_results_review_hint_recorder():
    window = _ResultsHintWindow("saxs", "saxs.strain")

    MainWindowOutputMixin._update_results_review_hint(
        window,
        summary="strain summary complete",
        risk_text="2 frames need review",
        next_text="review the evolution panel first",
    )

    assert len(window._results_panel.review_hint_calls) == 1
    call = window._results_panel.review_hint_calls[0]
    assert call["title"] == "strain summary complete"
    assert call["detail"] == "2 frames need review"
    assert call["next_text"] == "review the evolution panel first"
    assert call["status"] == "review"
    assert call["action_text"]
    assert callable(call["action"])


def test_saxs_temperature_review_hint_falls_back_to_localized_title():
    window = _ResultsHintWindow("saxs", "temperature")

    MainWindowOutputMixin._update_results_review_hint(
        window,
        summary="",
        risk_text="需复核风险",
        next_text="下一步",
    )

    call = window._results_panel.review_hint_calls[0]
    assert call["title"] == tr("SAXS_RESULTS_REVIEW_HINT_TITLE")
    assert call["detail"] == "需复核风险"
    assert call["next_text"] == "下一步"
