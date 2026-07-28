from polynexus.gui.main_window_history_mixin import resolve_joint_history_project_label
from polynexus.data.sample_db import SampleDB
from polynexus.gui.main_window import MainWindow
from polynexus.gui.i18n import tr
from PySide6.QtWidgets import QApplication


def test_joint_history_identity_uses_one_report_sample_when_project_is_default():
    assert resolve_joint_history_project_label(
        "No project",
        {"rows": [{"sample": "PA6-A"}]},
    ) == "PA6-A"


def test_joint_history_identity_uses_translated_workspace_label_for_multiple_samples():
    label = resolve_joint_history_project_label(
        "无项目",
        {"rows": [{"sample": "PA6-A"}, {"sample": "PA66-B"}]},
    )
    assert label == tr("WORKFLOW_TASK_JOINT_TITLE")


def test_joint_history_identity_keeps_explicit_and_empty_labels():
    assert resolve_joint_history_project_label("Joint review", {"rows": []}) == "Joint review"
    assert resolve_joint_history_project_label("Joint review", {"rows": [{"sample": "PA6-A"}]}) == "Joint review"
    assert resolve_joint_history_project_label("No project", {"rows": []}) == "No project"


def test_joint_persistence_keeps_raw_project_identity_while_displaying_inferred_label(tmp_path):
    QApplication.instance() or QApplication([])
    window = MainWindow()
    window._sample_db = SampleDB(tmp_path / "samples.db")
    window._current_technique = "joint"
    window._current_submodule_id = "joint.compare"
    window._output_dir = str(tmp_path / "joint-output")
    window._project_label.setText("No project")
    report = {
        "name": "joint_analysis_hub",
        "rows": [{"sample": "PA6-A", "batch": "annealed"}],
        "validations": [],
    }

    window._persist_analysis_run(report)

    assert window._project_label.text() == "PA6-A"
    stored = window._ensure_sample_db().get_analysis_run(window._last_persisted_run_id)
    assert stored["results_summary"]["project_label"] == "No project"
