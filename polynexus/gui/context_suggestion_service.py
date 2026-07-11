"""Pure helpers for GUI context suggestion and workflow-task text."""

from __future__ import annotations

from typing import Iterable


def _context_item(text_key: str, action_key: str, callback_key: str | None = None) -> dict:
    return {
        "text_key": text_key,
        "action_key": action_key,
        "callback_key": callback_key or action_key,
    }


def safe_jsonable_method_result(
    value,
    method_name: str,
    *,
    warning_message: str,
    warning_fn=None,
) -> tuple[bool, object]:
    method = getattr(value, method_name, None)
    if not callable(method):
        return False, None
    try:
        return True, method()
    except Exception:
        if warning_fn is not None:
            warning_fn(warning_message)
        return False, None


def _joint_issue_count(joint_context: dict) -> int:
    try:
        return int(float(joint_context.get("issue_count") or 0))
    except (TypeError, ValueError):
        return 0


def ai_tuning_goal_recommendation(
    *,
    joint_context,
    tuning_context,
    validation_text: str = "",
) -> tuple[str, str]:
    goal = "symptom"
    reason_key = "AI_TUNING_GOAL_REASON_SYMPTOM"

    if isinstance(joint_context, dict) and joint_context:
        issue_count = _joint_issue_count(joint_context)
        joint_summary = str(joint_context.get("summary") or "").lower()
        issue_families = joint_context.get("issue_families") if isinstance(joint_context.get("issue_families"), list) else []
        families = {str(item).strip().lower() for item in issue_families if str(item).strip()}
        if issue_count > 0 or families or any(token in joint_summary for token in ("inconsistency", "gap", "unstable", "conflict")):
            return "joint", "AI_TUNING_GOAL_REASON_JOINT"

    if isinstance(tuning_context, dict) and tuning_context:
        risk_text = " ".join(
            str(tuning_context.get(key) or "")
            for key in ("remaining_risks", "stop_reason", "summary", "benchmark_text")
        ).lower()
        validation_lower = str(validation_text or "").lower()
        if any(token in risk_text for token in ("low-q", "beamstop", "constraint", "rollback", "warn", "risk")):
            return "risk", "AI_TUNING_GOAL_REASON_RISK"
        if "warn" in validation_lower or "risk" in validation_lower:
            return "risk", "AI_TUNING_GOAL_REASON_RISK"
        benchmark_text = str(tuning_context.get("benchmark_text") or "").lower()
        if any(token in benchmark_text for token in ("quality guard", "small delta", "stable", "accepted")):
            return "stability", "AI_TUNING_GOAL_REASON_STABILITY"

    return goal, reason_key


def context_suggestion_spec(
    slot: str,
    *,
    has_file: bool = False,
    source_name: str = "",
    has_results: bool = False,
    has_config: bool = False,
    technique: str = "",
    current_origin: str = "",
    has_recent_calibration: bool = False,
    calibration_scope_label: str = "",
) -> dict | None:
    slot_key = str(slot or "").strip()
    if slot_key == "data":
        if not has_file:
            return {
                "title_key": "CONTEXT_HINT_DATA_TITLE",
                "detail_key": "CONTEXT_HINT_DATA_NEED_INPUT",
                "detail_args": (),
                "items": [
                    _context_item("CONTEXT_HINT_ACTION_BROWSE_FILE", "browse_file"),
                    _context_item("CONTEXT_HINT_ACTION_BROWSE_FOLDER", "browse_folder"),
                ],
            }
        return {
            "title_key": "CONTEXT_HINT_DATA_TITLE",
            "detail_key": "CONTEXT_HINT_DATA_READY",
            "detail_args": (str(source_name or ""),),
            "items": [
                _context_item("CONTEXT_HINT_ACTION_OPEN_CONFIG", "open_config"),
                _context_item(
                    "CONTEXT_HINT_ACTION_OPEN_RESULTS" if has_results else "CONTEXT_HINT_ACTION_OPEN_HISTORY",
                    "open_results" if has_results else "open_history",
                ),
            ],
        }

    if slot_key == "config":
        if not has_file:
            return {
                "title_key": "CONTEXT_HINT_CONFIG_TITLE",
                "detail_key": "CONTEXT_HINT_CONFIG_NEED_INPUT",
                "detail_args": (),
                "items": [
                    _context_item("CONTEXT_HINT_ACTION_BACK_TO_DATA", "back_to_data"),
                    _context_item("CONTEXT_HINT_ACTION_OPEN_HISTORY", "open_history"),
                ],
            }

        if str(current_origin or "").strip() == "controlled_optimization_rerun":
            return {
                "title_key": "CONTEXT_HINT_CONFIG_TITLE",
                "detail_key": "CONTEXT_HINT_CONFIG_AI_TUNED",
                "detail_args": (),
                "items": [
                    _context_item("CONTEXT_HINT_ACTION_REVIEW_AI_RESULT", "review_ai_result"),
                    _context_item("CONTEXT_HINT_ACTION_RUN_CONTROLLED_OPTIMIZATION", "run_controlled_optimization"),
                ],
            }

        if str(technique or "").strip().lower() in {"saxs", "waxs"} and has_config:
            return {
                "title_key": "CONTEXT_HINT_CONFIG_TITLE",
                "detail_key": "CONTEXT_HINT_CONFIG_READY",
                "detail_args": (str(calibration_scope_label or ""),),
                "items": [
                    _context_item(
                        "CONTEXT_HINT_ACTION_APPLY_RECENT_CALIBRATION"
                        if has_recent_calibration
                        else "CONTEXT_HINT_ACTION_SAVE_RECENT_CALIBRATION",
                        "recent_calibration",
                        "apply_recent_calibration" if has_recent_calibration else "save_recent_calibration",
                    ),
                    _context_item(
                        "CONTEXT_HINT_ACTION_OPEN_RESULTS" if has_results else "CONTEXT_HINT_ACTION_OPEN_HISTORY",
                        "open_results" if has_results else "open_history",
                    ),
                ],
            }

        return {
            "title_key": "CONTEXT_HINT_CONFIG_TITLE",
            "detail_key": "CONTEXT_HINT_CONFIG_GENERIC",
            "detail_args": (),
            "items": [
                _context_item("CONTEXT_HINT_ACTION_BACK_TO_DATA", "back_to_data"),
                _context_item(
                    "CONTEXT_HINT_ACTION_OPEN_RESULTS" if has_results else "CONTEXT_HINT_ACTION_OPEN_HISTORY",
                    "open_results" if has_results else "open_history",
                ),
            ],
        }

    return None


def workflow_task_context_spec(
    *,
    tech: str,
    input_mode: str,
    filepath: str,
    is_dir: bool,
    is_native_directory_context: bool,
    ai_tuning_active: bool,
    running: bool,
    source_name: str,
    mode_text: str,
    no_data_text: str,
) -> dict:
    tech_key = str(tech or "").strip().lower()
    mode_key = str(input_mode or "").strip().lower()
    path_text = str(filepath or "").strip()
    source_text = str(source_name or "").strip() or str(no_data_text or "")
    mode_label = str(mode_text or "").strip()
    if mode_label and path_text:
        source_text = f"{mode_label} | {source_text}"

    if tech_key == "joint":
        title_key = "WORKFLOW_TASK_JOINT_TITLE"
        detail_key = "WORKFLOW_TASK_JOINT_DETAIL"
    elif tech_key == "samples":
        title_key = "WORKFLOW_TASK_SAMPLES_TITLE"
        detail_key = "WORKFLOW_TASK_SAMPLES_DETAIL"
    elif ai_tuning_active:
        title_key = "WORKFLOW_TASK_AI_TUNING_TITLE"
        detail_key = "WORKFLOW_TASK_AI_TUNING_DETAIL"
    elif path_text and is_dir:
        if is_native_directory_context:
            title_key = "WORKFLOW_TASK_SEQUENCE_TITLE" if mode_key == "sequence" else "WORKFLOW_TASK_DIRECTORY_TITLE"
            detail_key = "WORKFLOW_TASK_SEQUENCE_DETAIL" if mode_key == "sequence" else "WORKFLOW_TASK_DIRECTORY_DETAIL"
        else:
            title_key = "WORKFLOW_TASK_BATCH_TITLE"
            detail_key = "WORKFLOW_TASK_BATCH_DETAIL"
    elif path_text:
        title_key = "WORKFLOW_TASK_SINGLE_TITLE"
        detail_key = "WORKFLOW_TASK_SINGLE_DETAIL"
    else:
        title_key = "WORKFLOW_TASK_IDLE_TITLE"
        detail_key = "WORKFLOW_TASK_IDLE_DETAIL"

    if tech_key == "joint":
        status_key = "WORKFLOW_TASK_STATUS_JOINT"
    elif path_text and is_dir:
        status_key = "WORKFLOW_TASK_STATUS_DIRECTORY" if is_native_directory_context else "WORKFLOW_TASK_STATUS_BATCH"
    elif path_text:
        status_key = "WORKFLOW_TASK_STATUS_SINGLE"
    else:
        status_key = "WORKFLOW_TASK_STATUS_IDLE"
    if ai_tuning_active:
        status_key = "WORKFLOW_TASK_STATUS_AI_TUNING"
    if running:
        status_key = "WORKFLOW_TASK_STATUS_RUNNING"

    return {
        "title_key": title_key,
        "detail_key": detail_key,
        "status_key": status_key,
        "source": source_text,
    }


def workflow_task_tech_label(tech: str, *, technique_labels: dict, no_tech_text: str) -> str:
    tech_key = str(tech or "").strip().lower()
    if tech_key == "samples":
        return "Samples"
    if tech_key == "joint":
        return "Joint"
    return technique_labels.get(tech_key, tech_key.upper() if tech_key else str(no_tech_text or ""))
