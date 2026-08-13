import pytest

from polynexus.gui.contextual_tools_service import contextual_tool_state
from polynexus.gui.main_window_navigation_mixin import MainWindowNavigationMixin
from polynexus.gui.workspace_context import WorkspaceContext, WorkspaceResultStatus


def test_contextual_tools_are_disabled_without_a_completed_run():
    state = contextual_tool_state(WorkspaceContext.empty(), {})

    assert state["joint"]["available"] is False
    assert state["robustness"]["available"] is False
    assert state["convergence"]["available"] is False
    assert state["project_attachment"]["available"] is False


def test_contextual_tools_expose_shared_plan_evaluation_from_completed_run():
    context = WorkspaceContext(
        technique="saxs",
        source_path="sample.csv",
        run_id="run-42",
        result_status=WorkspaceResultStatus.COMPLETE,
    )
    evaluation = {
        "version": 1,
        "plan_id": "plan-42",
        "plan_hash": "hash-42",
        "candidates": [{"candidate_id": "base", "status": "stable"}],
        "review_limits": ["human_scientific_review"],
        "replay": {"status": "frozen"},
    }

    state = contextual_tool_state(
        context,
        {"analysis_plan_evaluation": evaluation, "analysis_plan_evaluation_run_id": "run-42"},
    )

    assert state["joint"]["available"] is True
    assert state["robustness"] == {
        "available": True,
        "plan_id": "plan-42",
        "candidate_count": 1,
        "review_limits": ("human_scientific_review",),
    }
    assert state["convergence"]["available"] is True


def test_contextual_tools_do_not_reuse_an_evaluation_from_a_different_run():
    context = WorkspaceContext(
        technique="saxs",
        source_path="sample-b.csv",
        run_id="run-b",
        result_status=WorkspaceResultStatus.COMPLETE,
    )
    evaluation = {
        "version": 1,
        "plan_id": "plan-a",
        "plan_hash": "hash-a",
        "candidates": [],
        "review_limits": [],
        "replay": {"status": "frozen"},
    }

    state = contextual_tool_state(
        context,
        {"analysis_plan_evaluation": evaluation, "analysis_plan_evaluation_run_id": "run-a"},
    )

    assert state["robustness"] == {
        "available": False,
        "plan_id": "",
        "candidate_count": 0,
        "review_limits": (),
    }


def test_contextual_tools_fail_closed_for_malformed_cached_evaluation():
    context = WorkspaceContext(
        technique="saxs",
        source_path="sample.csv",
        run_id="run-42",
        result_status=WorkspaceResultStatus.COMPLETE,
    )

    state = contextual_tool_state(
        context,
        {"analysis_plan_evaluation": {"version": 1}, "analysis_plan_evaluation_run_id": "run-42"},
    )

    assert state["robustness"] == {
        "available": False,
        "plan_id": "",
        "candidate_count": 0,
        "review_limits": (),
    }


@pytest.mark.parametrize(
    "mutation",
    [
        {"replay": "frozen"},
        {"candidates": ["stable"]},
        {"review_limits": [None]},
    ],
)
def test_contextual_tools_disable_plan_evaluation_for_malformed_nested_payloads(mutation):
    context = WorkspaceContext(
        technique="saxs",
        source_path="sample.csv",
        run_id="run-42",
        result_status=WorkspaceResultStatus.COMPLETE,
    )
    evaluation = {
        "version": 1,
        "plan_id": "plan-42",
        "plan_hash": "hash-42",
        "candidates": [],
        "review_limits": [],
        "replay": {"status": "frozen"},
    }
    evaluation.update(mutation)

    state = contextual_tool_state(
        context,
        {"analysis_plan_evaluation": evaluation, "analysis_plan_evaluation_run_id": "run-42"},
    )

    assert state["robustness"]["available"] is False


def test_contextual_tools_expose_current_run_for_reference_only_project_attachment():
    context = WorkspaceContext(
        technique="saxs",
        source_path="sample.csv",
        output_dir="results",
        run_id="run-42",
        result_status=WorkspaceResultStatus.COMPLETE,
    )

    state = contextual_tool_state(context, {})

    assert state["project_attachment"] == {
        "available": True,
        "run_id": "run-42",
        "technique": "saxs",
        "source_file": "sample.csv",
        "output_dir": "results",
    }


def test_navigation_hides_advanced_tools_until_the_current_run_is_available():
    class _Control:
        def __init__(self):
            self.visible = None
            self.enabled = None

        def setVisible(self, value):
            self.visible = value

        def setEnabled(self, value):
            self.enabled = value

    class _Window(MainWindowNavigationMixin):
        def __init__(self):
            self._workspace_context = WorkspaceContext.empty()
            self._last_ai_tuning_context = {}
            self._nav_buttons = {"joint.quick": _Control(), "joint.compare": _Control()}
            self._sidebar_section_labels = {"joint": _Control()}
            self.action_convergence_viewer = _Control()
            self._act_attach_quick_run = _Control()
            self._act_view_analysis_plan_evaluation = _Control()

    window = _Window()
    window._update_contextual_tool_actions()
    assert window._nav_buttons["joint.quick"].visible is False
    assert window.action_convergence_viewer.enabled is False
    assert window._act_attach_quick_run.enabled is False
    assert window._act_view_analysis_plan_evaluation.enabled is False

    window._workspace_context = WorkspaceContext(
        technique="saxs", source_path="sample.csv", run_id="run-42", result_status=WorkspaceResultStatus.COMPLETE
    )
    window._last_ai_tuning_context = {"analysis_plan_evaluation": {
        "version": 1,
        "plan_id": "plan-42",
        "plan_hash": "hash-42",
        "candidates": [],
        "review_limits": [],
        "replay": {"status": "frozen"},
    }, "analysis_plan_evaluation_run_id": "run-42"}
    window._update_contextual_tool_actions()
    assert window._nav_buttons["joint.quick"].visible is True
    assert window.action_convergence_viewer.enabled is True
    assert window._act_attach_quick_run.enabled is True
    assert window._act_view_analysis_plan_evaluation.enabled is True
