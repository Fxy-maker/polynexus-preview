from __future__ import annotations

from polynexus.gui.main_window import MainWindow
from polynexus.gui.main_window_workspace_mixin import MainWindowWorkspaceMixin
from polynexus.gui.workspace_context import WorkspaceResultStatus


class _Label:
    def __init__(self, text=""):
        self._text = text

    def setText(self, text):
        self._text = str(text)

    def text(self):
        return self._text


class _FakeWorkspaceWindow(MainWindowWorkspaceMixin):
    def __init__(self, *, technique="", submodule="", filepath="", output_dir="", run_id=""):
        self._current_technique = technique
        self._current_submodule_id = submodule
        self._current_filepath = filepath
        self._current_input_mode = ""
        self._output_dir = output_dir
        self._last_persisted_run_id = run_id
        self._workspace_mode = "analysis"
        self._current_result_origin_value = "manual_run"
        self._joint_report = {}
        self._workspace_title = _Label()
        self._workspace_subtitle = _Label()
        self._workspace_context_summary = _Label()
        self._workflow_metric_tech = _Label()
        self._workflow_metric_data = _Label()
        self._workflow_metric_state = _Label("Ready")

    def _workspace_mode_value(self):
        return self._workspace_mode

    def _workspace_input_mode_text(self):
        return ""

    def _is_native_directory_run_context(self):
        return False

    def _history_submodule_text(self, submodule):
        return submodule

    def _idle_workflow_state_text(self):
        return "Ready"

    def _current_result_origin(self):
        return self._current_result_origin_value

    def _update_workflow_task_card(self):
        return None

    def _update_context_suggestions(self):
        return None

    def _update_work_memory_panel(self):
        return None

    def _update_results_compare_panel(self):
        return None


def test_main_window_reuses_workspace_and_context_helpers_from_workspace_mixin():
    assert MainWindow._update_workspace_context is MainWindowWorkspaceMixin._update_workspace_context
    assert MainWindow._workspace_input_mode_text is MainWindowWorkspaceMixin._workspace_input_mode_text
    assert MainWindow._workflow_task_tech_label is MainWindowWorkspaceMixin._workflow_task_tech_label
    assert MainWindow._workflow_task_context is MainWindowWorkspaceMixin._workflow_task_context
    assert MainWindow._update_workflow_task_card is MainWindowWorkspaceMixin._update_workflow_task_card
    assert MainWindow._context_suggestion_payload is MainWindowWorkspaceMixin._context_suggestion_payload
    assert MainWindow._materialize_context_suggestion_spec is MainWindowWorkspaceMixin._materialize_context_suggestion_spec
    assert MainWindow._context_suggestion_callback is MainWindowWorkspaceMixin._context_suggestion_callback
    assert MainWindow._update_context_suggestion_panel is MainWindowWorkspaceMixin._update_context_suggestion_panel
    assert MainWindow._update_context_suggestions is MainWindowWorkspaceMixin._update_context_suggestions


def test_workspace_context_projection_includes_run_identity():
    window = _FakeWorkspaceWindow(
        technique="saxs",
        submodule="saxs.temperature",
        filepath="D:/run/sample.edf",
        output_dir="D:/run/polynexus_output",
        run_id="run-42",
    )

    window._update_workspace_context()

    assert window._workspace_context.run_id == "run-42"
    assert "saxs" in window._workspace_context_summary.text().lower()
    assert "run-42" in window._workspace_context_summary.text()


def test_switching_technique_marks_previous_result_as_stale():
    window = _FakeWorkspaceWindow(technique="saxs", run_id="run-1")
    window._result_contexts = {}
    window._workspace_context = window._workspace_context_snapshot(
        result_status=WorkspaceResultStatus.COMPLETE,
        run_id="run-1",
    )
    window._record_result_context()
    window._current_technique = "waxs"

    window._update_workspace_context()

    assert window._result_context_is_current("saxs") is False
    assert window._workspace_context.technique == "waxs"


def test_joint_workflow_task_uses_report_identity_instead_of_no_data():
    window = _FakeWorkspaceWindow(technique="joint", submodule="joint.compare")
    window._joint_report = {"rows": [{"sample": "PA6-A", "batch": "annealed"}]}

    task = window._workflow_task_context()

    assert task["source"] == "PA6-A"
