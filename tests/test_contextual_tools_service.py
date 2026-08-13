from polynexus.gui.contextual_tools_service import contextual_tool_state
from polynexus.gui.main_window_navigation_mixin import MainWindowNavigationMixin
from polynexus.gui.workspace_context import WorkspaceContext, WorkspaceResultStatus


def test_contextual_tools_are_disabled_without_a_completed_run():
    state = contextual_tool_state(WorkspaceContext.empty(), {})

    assert state["joint"]["available"] is False
    assert state["robustness"]["available"] is False
    assert state["convergence"]["available"] is False


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

    state = contextual_tool_state(context, {"analysis_plan_evaluation": evaluation})

    assert state["joint"]["available"] is True
    assert state["robustness"] == {
        "available": True,
        "plan_id": "plan-42",
        "candidate_count": 1,
        "review_limits": ("human_scientific_review",),
    }
    assert state["convergence"]["available"] is True


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

    window = _Window()
    window._update_contextual_tool_actions()
    assert window._nav_buttons["joint.quick"].visible is False
    assert window.action_convergence_viewer.enabled is False

    window._workspace_context = WorkspaceContext(
        technique="saxs", run_id="run-42", result_status=WorkspaceResultStatus.COMPLETE
    )
    window._update_contextual_tool_actions()
    assert window._nav_buttons["joint.quick"].visible is True
    assert window.action_convergence_viewer.enabled is True
