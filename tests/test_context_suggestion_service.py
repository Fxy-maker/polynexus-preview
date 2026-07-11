from polynexus.gui.analysis_history_service import context_suggestion_spec as history_context_suggestion_spec
from polynexus.gui.analysis_history_service import ai_tuning_goal_recommendation as history_ai_tuning_goal_recommendation
from polynexus.gui.analysis_history_service import workflow_task_context_spec as history_workflow_task_context_spec
from polynexus.gui.analysis_history_service import workflow_task_tech_label as history_workflow_task_tech_label


def test_history_module_reexports_context_suggestion_helpers():
    from polynexus.gui.context_suggestion_service import (
        ai_tuning_goal_recommendation,
        context_suggestion_spec,
        workflow_task_context_spec,
        workflow_task_tech_label,
    )

    assert history_ai_tuning_goal_recommendation is ai_tuning_goal_recommendation
    assert history_context_suggestion_spec is context_suggestion_spec
    assert history_workflow_task_context_spec is workflow_task_context_spec
    assert history_workflow_task_tech_label is workflow_task_tech_label


def test_context_suggestion_spec_handles_data_and_config_slots():
    from polynexus.gui.context_suggestion_service import context_suggestion_spec

    assert context_suggestion_spec("data", has_file=False) == {
        "title_key": "CONTEXT_HINT_DATA_TITLE",
        "detail_key": "CONTEXT_HINT_DATA_NEED_INPUT",
        "detail_args": (),
        "items": [
            {"text_key": "CONTEXT_HINT_ACTION_BROWSE_FILE", "action_key": "browse_file", "callback_key": "browse_file"},
            {"text_key": "CONTEXT_HINT_ACTION_BROWSE_FOLDER", "action_key": "browse_folder", "callback_key": "browse_folder"},
        ],
    }

    assert context_suggestion_spec("config", has_file=True, technique="saxs", has_config=True, has_recent_calibration=True) is not None


def test_workflow_task_context_spec_and_label_helpers():
    from polynexus.gui.context_suggestion_service import workflow_task_context_spec, workflow_task_tech_label

    assert workflow_task_tech_label("samples", technique_labels={}, no_tech_text="No tech") == "Samples"
    assert workflow_task_context_spec(
        tech="joint",
        input_mode="single",
        filepath="",
        is_dir=False,
        is_native_directory_context=False,
        ai_tuning_active=False,
        running=False,
        source_name="",
        mode_text="",
        no_data_text="No data",
    ) == {
        "title_key": "WORKFLOW_TASK_JOINT_TITLE",
        "detail_key": "WORKFLOW_TASK_JOINT_DETAIL",
        "status_key": "WORKFLOW_TASK_STATUS_JOINT",
        "source": "No data",
    }


def test_ai_tuning_goal_recommendation_handles_joint_risk_and_stability_contexts():
    from polynexus.gui.context_suggestion_service import ai_tuning_goal_recommendation

    assert ai_tuning_goal_recommendation(
        joint_context={
            "issue_count": "bad-count",
            "summary": "Gap between SAXS and WAXS trends remains unstable.",
        },
        tuning_context={},
        validation_text="",
    ) == ("joint", "AI_TUNING_GOAL_REASON_JOINT")

    assert ai_tuning_goal_recommendation(
        joint_context={},
        tuning_context={"remaining_risks": "beamstop warning remains"},
        validation_text="",
    ) == ("risk", "AI_TUNING_GOAL_REASON_RISK")

    assert ai_tuning_goal_recommendation(
        joint_context={},
        tuning_context={"benchmark_text": "quality guard reached with accepted update"},
        validation_text="",
    ) == ("stability", "AI_TUNING_GOAL_REASON_STABILITY")


def test_safe_jsonable_method_result_warns_and_returns_none_on_method_failure():
    from polynexus.gui.context_suggestion_service import safe_jsonable_method_result

    class Broken:
        def tolist(self):
            raise RuntimeError("bad list")

        def item(self):
            raise RuntimeError("bad item")

    warnings = []

    assert safe_jsonable_method_result(Broken(), "tolist", warning_message="tolist failed", warning_fn=warnings.append) == (False, None)
    assert safe_jsonable_method_result(Broken(), "item", warning_message="item failed", warning_fn=warnings.append) == (False, None)
    assert warnings == ["tolist failed", "item failed"]
