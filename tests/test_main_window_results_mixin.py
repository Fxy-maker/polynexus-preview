from __future__ import annotations

from polynexus.gui.main_window import MainWindow
from polynexus.gui.main_window_results_mixin import MainWindowResultsMixin
from polynexus.gui.main_window_workspace_mixin import MainWindowWorkspaceMixin
from polynexus.gui.workspace_context import WorkspaceContext, WorkspaceResultStatus


class _FakeResultsWindow(MainWindowResultsMixin):
    def __init__(self) -> None:
        self._results_compare_selected_run_id = "  run-42  "
        self._confirmed = False

    def _current_results_record(self) -> dict:
        return {"id": "current", "confirmed": self._confirmed, "results_summary": {}}

    def _is_current_result_confirmed(self) -> bool:
        return self._confirmed


def test_results_compare_selected_candidate_id_trims_whitespace() -> None:
    window = _FakeResultsWindow()

    assert window._results_compare_selected_candidate_id() == "run-42"


def test_results_confirm_state_text_reflects_confirmation_state() -> None:
    window = _FakeResultsWindow()

    assert window._results_confirm_state_text()

    window._confirmed = True

    assert window._results_confirm_state_text() != ""


def test_main_window_reuses_result_context_helpers_from_results_mixin() -> None:
    assert MainWindow._current_results_payload is MainWindowResultsMixin._current_results_payload
    assert MainWindow._current_results_record is MainWindowResultsMixin._current_results_record
    assert MainWindow._current_result_history_context is MainWindowResultsMixin._current_result_history_context
    assert MainWindow._current_result_tuning_context is MainWindowResultsMixin._current_result_tuning_context
    assert MainWindow._current_analysis_evidence is MainWindowResultsMixin._current_analysis_evidence
    assert MainWindow._current_result_origin is MainWindowResultsMixin._current_result_origin
    assert MainWindow._current_result_origin_label is MainWindowResultsMixin._current_result_origin_label
    assert MainWindow._result_origin_label is MainWindowResultsMixin._result_origin_label
    assert MainWindow._build_results_tab is MainWindowResultsMixin._build_results_tab
    assert MainWindow._build_joint_metric_label is MainWindowResultsMixin._build_joint_metric_label


class _StaleResultsWindow(MainWindowResultsMixin, MainWindowWorkspaceMixin):
    def __init__(self) -> None:
        self._current_technique = "waxs"
        self._results = {"waxs": {"parameters": {"r2": 0.9}}}
        self._result_contexts = {
            "waxs": WorkspaceContext(
                technique="saxs",
                source_path="D:/old/sample.edf",
                run_id="run-old",
                result_status=WorkspaceResultStatus.COMPLETE,
            )
        }
        self._workspace_context = WorkspaceContext(
            technique="waxs",
            source_path="D:/new/sample.edf",
            result_status=WorkspaceResultStatus.EMPTY,
        )
        self._results_context_banner = type("Banner", (), {
            "setVisible": lambda self, value: setattr(self, "visible", value),
            "setText": lambda self, value: setattr(self, "text", value),
        })()


def test_stale_result_context_is_not_projected_as_current_payload() -> None:
    window = _StaleResultsWindow()

    assert window._current_results_payload() == {}
    assert window._results_context_banner.visible is True
