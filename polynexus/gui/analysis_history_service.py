"""Data helpers for the GUI analysis history panel."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable

from .context_suggestion_service import (
    ai_tuning_goal_recommendation,  # noqa: F401
    context_suggestion_spec,  # noqa: F401
    safe_jsonable_method_result,
    workflow_task_context_spec,  # noqa: F401
    workflow_task_tech_label,  # noqa: F401
)
from .i18n import tr  # noqa: F401
from .workspace_context_service import (
    work_memory_summary_text,  # noqa: F401
    workspace_context_summary_text,  # noqa: F401
)
from .analysis_history_risk_helpers import (
    DEFAULT_COMPARISON_KEYS,
    DEFAULT_REVIEW_METRIC_KEYS,
    DEFAULT_TECHNIQUE_FILTERS,
    PREFERRED_RESULT_COLUMNS,  # noqa: F401
    SAXS_COMPARISON_KEYS,
    SAXS_STRAIN_COMPARISON_KEYS,
    STRAIN_REVIEW_METRIC_KEYS,
    gui_coerce_summary_float,
    gui_display_text,  # noqa: F401
    gui_display_text_value,  # noqa: F401
    gui_format_score_value,  # noqa: F401
    has_condition_axis_risk,  # noqa: F401
    has_fallback_conflict_risk,  # noqa: F401
    measured_result_metric_parts,  # noqa: F401
    ordered_results_columns,  # noqa: F401
    result_mask_summary_text,  # noqa: F401
    results_has_critical_risk,  # noqa: F401
    results_next_step_translation_key,  # noqa: F401
)


SUMMARY_METRIC_KEYS_TO_SKIP: set[str] = {
    "result",
    "data_file",
    "project_label",
    "status",
    "polymer_type",
    "technique",
    "submodule",
    "confirmed",
    "validation_passed",
    "validation_summary",
    "validation_warnings",
    "quality_flags",
    "result_origin",
    "ai_tuned",
    "history_context",
    "review_summary",
    "work_memory_summary",
    "comparison_summary",
    "benchmark_summary",
    "benchmark_text",
    "tuning_context",
    "tuning_goal",
    "tuning_goal_label",
    "stop_reason",
    "remaining_risks",
    "next_goal",
    "joint_ai_context",
    "joint_summary",
}
_JOINT_AI_BOUNDARY: dict[str, str] = {
    "mode": "off",
    "provider_status": "not_configured",
    "fallback": "rule_based_report",
    "failure_policy": "preserve_source_evidence_and_diagnostic_status",
}
VALIDATION_KEYS: set[str] = {
    "validation_passed",
    "validation_summary",
    "validation_warnings",
    "quality_flags",
}
WAXS_METRICS_PREFERRED_KEYS: tuple[str, ...] = (
    "n_peaks",
    "Xc_pct",
    "D_Scherrer_nm",
    "temperature_axis_confidence",
    "peak_family_continuity_score",
    "transition_support_score",
    "Xc_trend_support_score",
    "D_trend_support_score",
    "peak_support_score",
    "background_stability_score",
    "phase_support_score",
    "size_support_score",
    "waxs_support_score",
)
SAXS_METRICS_PREFERRED_KEYS: tuple[str, ...] = (
    "lc_nm",
    "lc_method",
    "lc_reliability_status",
    "calibrated_fallback_active",
    "calibration_skipped_reason",
    "lc_reliability_reason",
    "melting_window_status",
    "melting_window_reason",
    "Tm_onset_C",
    "Tm_peak_C",
    "Tm_end_C",
    "Xc_pct",
    "L_nm",
)
DEFAULT_METRICS_PREFERRED_KEYS: tuple[str, ...] = (
    "L_nm",
    "lc_nm",
    "lc_reliability_status",
    "melting_window_status",
    "Xc_pct",
    "Xc",
    "D_Scherrer_nm",
    "Tm_C",
    "Tm_peak_C",
    "Tc_C",
    "Tc_peak_C",
    "Tg_C",
)
COMPARE_STATE_PRIORITY: dict[str, int] = {
    "changed": 0,
    "new": 1,
    "removed": 2,
    "same": 3,
}
@dataclass(frozen=True)
class ValidationSummaryParts:
    summary: str
    warnings: list[str]


@dataclass(frozen=True)
class HistoryActionState:
    has_record: bool
    has_source: bool
    has_compare: bool
    can_copy_summary: bool
    can_restore: bool
    can_rerun: bool
    can_compare: bool
    can_confirm: bool


@dataclass(frozen=True)
class ControlledOptimizationReviewParts:
    tuning_goal: str
    benchmark_text: str
    stop_reason: str
    remaining_risks: str
    next_goal: str


@dataclass(frozen=True)
class AiTuningChainStats:
    baseline_hint: str
    accepted_rounds: int
    rolled_back_rounds: int
    best_round: int | None
    best_r2: float | None
    last_accepted_round: int | None
    rollback_reasons: list[str]


@dataclass(frozen=True)
class JointPromptParts:
    translation_key: str
    args: tuple[str, ...] = ()


@dataclass(frozen=True)
class HistoryContextLine:
    kind: str
    text: str


@dataclass(frozen=True)
class HistoryStatusLabelParts:
    translation_key: str
    fallback_label: str
    include_saxs_suffix: bool


@dataclass(frozen=True)
class HistoryStatusTextParts:
    labels: list[str]
    source_missing: bool


@dataclass(frozen=True)
class HistoryRecordContextRef:
    kind: str
    value: str


def collect_history_rows(db) -> list[dict]:
    list_headers = getattr(db, "list_analysis_run_headers", None)
    if callable(list_headers):
        return list_headers()

    rows: list[dict] = []
    samples = db.list_samples(limit=10000)
    for sample in samples:
        sample_id = sample.get("id")
        if not sample_id:
            continue
        for batch in db.get_batches(sample_id):
            batch_id = batch.get("id")
            if not batch_id:
                continue
            rows.extend(db.get_analysis_runs(batch_id))
    rows.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
    return rows


def history_filter_items(rows: Iterable[dict], base: Iterable[str] = DEFAULT_TECHNIQUE_FILTERS) -> list[str]:
    base_items = list(base)
    techniques = sorted(
        {
            str(run.get("technique") or "")
            for run in rows
            if str(run.get("technique") or "")
        }
    )
    return base_items + [tech for tech in techniques if tech not in base_items]


def format_r2_value(value) -> str:
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return "nan"


def format_history_timestamp(value) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    normalized = text.replace("T", " ")
    for pattern in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(normalized, pattern)
            return dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            continue
    return normalized


def extract_result_r2(payload) -> float:
    if not isinstance(payload, dict):
        return float("nan")
    candidates = (
        payload.get("r2"),
        payload.get("r_squared"),
        payload.get("R2"),
    )
    parameters = payload.get("parameters")
    if isinstance(parameters, dict):
        candidates += (
            parameters.get("r2"),
            parameters.get("r_squared"),
            parameters.get("R2"),
        )
    for candidate in candidates:
        try:
            return float(candidate)
        except (TypeError, ValueError):
            continue
    return float("nan")


def history_run_r2(run) -> float:
    summary = run.get("results_summary") if isinstance(run, dict) else {}
    if not isinstance(summary, dict):
        summary = {}
    return extract_result_r2(summary)


def history_result_origin(record) -> str:
    if not isinstance(record, dict):
        return ""
    summary = record.get("results_summary") if isinstance(record.get("results_summary"), dict) else {}
    if not isinstance(summary, dict):
        return ""
    origin = str(summary.get("result_origin") or "").strip()
    if not origin and bool(summary.get("ai_tuned")):
        origin = "controlled_optimization_rerun"
    return origin


def current_result_origin(current_result, *, last_ai_tuned_run: bool = False) -> str:
    origin = history_result_origin(current_result)
    if origin:
        return origin
    if bool(last_ai_tuned_run):
        return "controlled_optimization_rerun"
    return "manual_run"


def current_result_history_context(current_result) -> dict:
    if not isinstance(current_result, dict) or not current_result:
        return {}
    summary = current_result.get("results_summary") if isinstance(current_result.get("results_summary"), dict) else {}
    if not isinstance(summary, dict) or not summary:
        return {}
    history_context = summary.get("history_context") if isinstance(summary.get("history_context"), dict) else {}
    return history_context if isinstance(history_context, dict) and history_context else {}


def current_result_tuning_context(current_result, *, live_tuning_context=None) -> dict:
    tuning_context = live_tuning_context if isinstance(live_tuning_context, dict) else {}
    if tuning_context:
        return tuning_context

    history_context = current_result_history_context(current_result)
    if not isinstance(history_context, dict) or not history_context:
        return {}
    restored_context = history_context.get("tuning_context") if isinstance(history_context.get("tuning_context"), dict) else {}
    if not isinstance(restored_context, dict) or not restored_context:
        return {}
    restored_context = dict(restored_context)
    joint_context = history_context.get("joint_ai_context") if isinstance(history_context.get("joint_ai_context"), dict) else {}
    if isinstance(joint_context, dict) and joint_context and not isinstance(restored_context.get("joint_ai_context"), dict):
        restored_context["joint_ai_context"] = joint_context
    return restored_context


def current_results_payload(result) -> dict:
    if result is None:
        return {}
    if isinstance(result, dict):
        payload = result
    elif hasattr(result, "to_dict"):
        payload = result.to_dict()
    else:
        payload = getattr(result, "__dict__", {})
        if not isinstance(payload, dict) or not payload:
            payload = {}
            for key in (
                "parameters",
                "validation_summary",
                "validation_warnings",
                "validation_passed",
                "quality_flags",
                "results_summary",
                "analysis_evidence",
            ):
                if hasattr(result, key):
                    payload[key] = getattr(result, key)
    return result_to_jsonable(payload) if isinstance(payload, dict) else {}


def current_results_record(
    payload,
    *,
    technique: str = "",
    submodule: str = "",
    project_label: str = "",
    inferred_sample_name: str = "",
    current_file: str = "",
    output_dir: str = "",
    result_origin: str = "manual_run",
    confirmed: bool = False,
    run_id: str = "current",
    created_at: str = "",
    is_default_project_label_fn: Callable[[str], bool] | None = None,
) -> dict:
    if not isinstance(payload, dict) or not payload:
        return {}

    params = payload.get("parameters") if isinstance(payload.get("parameters"), dict) else {}
    summary_payload = payload.get("results_summary") if isinstance(payload.get("results_summary"), dict) else {}
    history_context = summary_payload.get("history_context") if isinstance(summary_payload.get("history_context"), dict) else {}
    if not isinstance(history_context, dict) or not history_context:
        history_context = payload.get("history_context") if isinstance(payload.get("history_context"), dict) else {}
    if not isinstance(history_context, dict):
        history_context = {}

    def normalized_text_list(value) -> list[str]:
        value = result_to_jsonable(value)
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        text = str(value or "").strip()
        return [text] if text else []

    resolved_project_label = str(summary_payload.get("project_label") or "").strip()
    if not resolved_project_label:
        resolved_project_label = str(project_label or "").strip()
    is_default = is_default_project_label_fn or (lambda _label: False)
    if not resolved_project_label or is_default(resolved_project_label):
        resolved_project_label = str(inferred_sample_name or "").strip()

    validation_summary = str(
        payload.get("validation_summary")
        or summary_payload.get("validation_summary")
        or params.get("validation_summary")
        or ""
    ).strip()
    validation_warnings = normalized_text_list(
        payload.get("validation_warnings")
        or summary_payload.get("validation_warnings")
        or params.get("validation_warnings")
        or []
    )
    quality_flags = payload.get("quality_flags")
    if not isinstance(quality_flags, dict):
        quality_flags = summary_payload.get("quality_flags")
    if not isinstance(quality_flags, dict):
        quality_flags = params.get("quality_flags")
    if not isinstance(quality_flags, dict):
        quality_flags = {}

    validation_passed = payload.get("validation_passed")
    if validation_passed is None:
        validation_passed = summary_payload.get("validation_passed")
    if validation_passed is None:
        validation_passed = params.get("validation_passed")
    if validation_passed is None:
        validation_passed = True

    result_payload = dict(payload)
    if validation_summary:
        result_payload["validation_summary"] = validation_summary
    if validation_warnings:
        result_payload["validation_warnings"] = validation_warnings
    if quality_flags:
        result_payload["quality_flags"] = quality_flags
    result_payload["validation_passed"] = bool(validation_passed)

    technique_key = str(technique or "").strip().lower()
    submodule_id = str(submodule or "").strip()
    current_file_text = str(current_file or "").strip()
    origin = str(result_origin or "").strip()
    summary = {
        "result": result_payload,
        "data_file": current_file_text,
        "project_label": resolved_project_label,
        "status": "completed",
        "technique": technique_key,
        "submodule": submodule_id,
        "result_origin": origin,
        "ai_tuned": origin == "controlled_optimization_rerun",
        "confirmed": bool(confirmed),
        "validation_summary": validation_summary,
        "validation_warnings": validation_warnings,
        "validation_passed": bool(validation_passed),
        "quality_flags": quality_flags,
        "history_context": history_context,
    }
    return {
        "id": str(run_id or "current"),
        "batch_id": str(run_id or "current"),
        "technique": technique_key,
        "submodule": submodule_id,
        "created_at": str(created_at or "").strip(),
        "results_summary": summary,
        "parameters": params,
        "validation_summary": summary.get("validation_summary", ""),
        "validation_warnings": summary.get("validation_warnings", []),
        "validation_passed": summary.get("validation_passed", True),
        "quality_flags": summary.get("quality_flags", {}),
        "output_dir": str(output_dir or ""),
        "status": "completed",
        "source_data": current_file_text,
        "confirmed": bool(confirmed),
    }


def ai_tuning_benchmark_delta_text(value) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "N/A"
    sign = "+" if number > 0 else ""
    return f"{sign}{number:.3f}"


def ai_tuning_benchmark_rate_text(value) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "0.0%"
    return f"{number * 100:.1f}%"


def ai_tuning_chain_stats(
    tuning_context: dict | None,
    *,
    benchmark_delta_text_fn: Callable[[object], str] | None = None,
) -> AiTuningChainStats:
    context = tuning_context if isinstance(tuning_context, dict) else {}
    history = context.get("history") if isinstance(context.get("history"), list) else []
    benchmark_summary = context.get("benchmark_summary") if isinstance(context.get("benchmark_summary"), dict) else {}

    accepted_rounds = 0
    rolled_back_rounds = 0
    best_round = None
    best_r2 = None
    last_accepted_round = None
    rollback_reasons = []

    for item in history:
        if not isinstance(item, dict):
            continue
        round_num = int(item.get("round_num", item.get("round_idx", 0)) or 0)
        if round_num <= 0:
            continue
        accepted = bool(item.get("accepted", True))
        if accepted:
            accepted_rounds += 1
            last_accepted_round = round_num
        else:
            rolled_back_rounds += 1
            advice = item.get("llm_advice") if isinstance(item.get("llm_advice"), dict) else {}
            reason = str(advice.get("rollback_reason", "") or "").strip()
            if reason and reason not in rollback_reasons:
                rollback_reasons.append(reason)
        r2 = item.get("r_squared_after", item.get("r_squared", None))
        try:
            r2_value = float(r2)
        except (TypeError, ValueError):
            continue
        if best_r2 is None or r2_value > best_r2:
            best_r2 = r2_value
            best_round = round_num

    baseline_hint = ""
    if isinstance(benchmark_summary, dict) and benchmark_summary:
        formatter = benchmark_delta_text_fn or (lambda value: "")
        baseline_hint = str(formatter(benchmark_summary.get("average_objective_delta")) or "")

    return AiTuningChainStats(
        baseline_hint=baseline_hint,
        accepted_rounds=accepted_rounds,
        rolled_back_rounds=rolled_back_rounds,
        best_round=best_round,
        best_r2=best_r2,
        last_accepted_round=last_accepted_round,
        rollback_reasons=rollback_reasons,
    )


def ai_tuning_chain_summary(
    tuning_context: dict | None,
    *,
    current_origin: str,
    language: str = "en",
    benchmark_delta_text_fn: Callable[[object], str] | None = None,
) -> str:
    context = tuning_context if isinstance(tuning_context, dict) else {}
    if str(current_origin or "").strip() != "controlled_optimization_rerun" and not context:
        return ""

    history = context.get("history") if isinstance(context.get("history"), list) else []
    benchmark_summary = context.get("benchmark_summary") if isinstance(context.get("benchmark_summary"), dict) else {}

    accepted_rounds = 0
    rolled_back_rounds = 0
    best_round = None
    best_r2 = None
    rollback_reasons = []

    for item in history:
        if not isinstance(item, dict):
            continue
        round_num = int(item.get("round_num", item.get("round_idx", 0)) or 0)
        if round_num <= 0:
            continue
        if bool(item.get("accepted", True)):
            accepted_rounds += 1
        else:
            rolled_back_rounds += 1
            advice = item.get("llm_advice") if isinstance(item.get("llm_advice"), dict) else {}
            rollback_reason = str(advice.get("rollback_reason") or "").strip()
            if rollback_reason and rollback_reason not in rollback_reasons:
                rollback_reasons.append(rollback_reason)
        try:
            r2_value = float(item.get("r_squared_after", item.get("r_squared", "")))
        except (TypeError, ValueError):
            continue
        if best_r2 is None or r2_value > best_r2:
            best_r2 = r2_value
            best_round = round_num

    baseline_hint = ""
    if isinstance(benchmark_summary, dict) and benchmark_summary:
        formatter = benchmark_delta_text_fn or (lambda value: "")
        baseline_hint = formatter(benchmark_summary.get("average_objective_delta"))

    if str(language or "").strip().lower().startswith("zh"):
        parts = [
            f"基线变化：{baseline_hint or 'N/A'}",
            f"接受 {accepted_rounds} 轮，回滚 {rolled_back_rounds} 轮",
        ]
        if best_round is not None:
            parts.append(f"当前最佳：第 {best_round} 轮")
        if rollback_reasons:
            parts.append(f"保留风险：{'; '.join(rollback_reasons[:2])}")
        return " | ".join(parts)

    parts = [
        f"baseline delta {baseline_hint or 'N/A'}",
        f"accepted {accepted_rounds} rounds, rolled back {rolled_back_rounds} rounds",
    ]
    if best_round is not None:
        parts.append(f"best candidate round {best_round}")
    if rollback_reasons:
        parts.append(f"remaining risks: {'; '.join(rollback_reasons[:2])}")
    return " | ".join(parts)


def ai_tuning_report_context(
    report,
    *,
    benchmark_summary_text_fn: Callable[[dict], str] | None = None,
    accepted_summary_text_fn: Callable[[int, object, object, object], str] | None = None,
    empty_text_fn: Callable[[], str] | None = None,
    stop_text_fn: Callable[[str], str] | None = None,
    risks_text_fn: Callable[[str], str] | None = None,
    goal_body_fn: Callable[[str, str], str] | None = None,
    goal_text_fn: Callable[[str], str] | None = None,
) -> dict:
    report = report if isinstance(report, dict) else {}
    improvement = report.get("improvement") if isinstance(report.get("improvement"), dict) else {}
    best_r2 = report.get("best_r_squared", "")
    delta = improvement.get("r_squared_abs", "")
    rounds = report.get("rounds", 0)
    convergence_reason = str(report.get("convergence_reason", "") or "").strip()
    benchmark_summary = report.get("benchmark_summary") if isinstance(report.get("benchmark_summary"), dict) else {}
    benchmark_text = ""
    if benchmark_summary:
        formatter = benchmark_summary_text_fn or (lambda summary: "")
        benchmark_text = str(formatter(benchmark_summary) or "").strip()

    history = report.get("history") if isinstance(report.get("history"), list) else []
    rollback_reasons = []
    accepted_rounds = 0
    for item in history:
        if not isinstance(item, dict):
            continue
        if bool(item.get("accepted", True)):
            accepted_rounds += 1
            continue
        advice = item.get("llm_advice") if isinstance(item.get("llm_advice"), dict) else {}
        reason = str(advice.get("rollback_reason", "") or "").strip()
        if reason:
            rollback_reasons.append(reason)

    remaining_risks = ""
    if rollback_reasons:
        unique_reasons = []
        for reason in rollback_reasons:
            if reason not in unique_reasons:
                unique_reasons.append(reason)
        remaining_risks = "; ".join(unique_reasons[:3])

    accepted_formatter = accepted_summary_text_fn or (
        lambda accepted, best, gain, total: f"accepted={accepted}; best={best}; delta={gain}; rounds={total}"
    )
    accepted_summary = str(accepted_formatter(accepted_rounds, best_r2, delta, rounds) or "").strip()

    empty_text = str(empty_text_fn() if empty_text_fn is not None else "" or "").strip()
    goal_body_formatter = goal_body_fn or (lambda focus, watch: "")
    next_goal = str(
        goal_body_formatter(
            convergence_reason or empty_text,
            remaining_risks or empty_text,
        ) or ""
    ).strip()

    summary_parts = [accepted_summary]
    if benchmark_text:
        summary_parts.append(benchmark_text)
    if convergence_reason:
        formatter = stop_text_fn or (lambda reason: reason)
        summary_parts.append(str(formatter(convergence_reason) or "").strip())
    if remaining_risks:
        formatter = risks_text_fn or (lambda risks: risks)
        summary_parts.append(str(formatter(remaining_risks) or "").strip())
    goal_formatter = goal_text_fn or (lambda goal: goal)
    summary_parts.append(str(goal_formatter(next_goal) or "").strip())

    return {
        "summary": "\n".join(part for part in summary_parts if part),
        "accepted_summary": accepted_summary,
        "benchmark_summary": benchmark_summary,
        "benchmark_text": benchmark_text,
        "history": history,
        "stop_reason": convergence_reason,
        "remaining_risks": remaining_risks,
        "next_goal": next_goal,
    }


def ai_tuning_previous_round_summary_text(
    context,
    *,
    label_text: str,
    empty_text: str,
    stop_text_fn: Callable[[str], str],
    risks_text_fn: Callable[[str], str],
    goal_text_fn: Callable[[str], str],
) -> str:
    if not isinstance(context, dict) or not context:
        return str(empty_text or "")

    parts = []
    summary = str(context.get("summary") or "").strip()
    if summary:
        parts.append(summary)

    accepted = str(context.get("accepted_summary") or "").strip()
    benchmark_text = str(context.get("benchmark_text") or "").strip()
    stop_reason = str(context.get("stop_reason") or "").strip()
    remaining_risks = str(context.get("remaining_risks") or "").strip()
    next_goal = str(context.get("next_goal") or "").strip()

    if accepted:
        parts.append(accepted)
    if benchmark_text and benchmark_text not in parts:
        parts.append(benchmark_text)
    if stop_reason:
        parts.append(str(stop_text_fn(stop_reason) or "").strip())
    if remaining_risks:
        parts.append(str(risks_text_fn(remaining_risks) or "").strip())
    if next_goal:
        parts.append(str(goal_text_fn(next_goal) or "").strip())
    parts = [part for part in parts if part]
    if not parts:
        return str(empty_text or "")
    return "\n".join([str(label_text or "")] + parts)


def ai_tuning_tunable_summary_text(
    param_map,
    *,
    current_value_fn: Callable[[str], object],
    none_text: str,
    row_text_fn: Callable[[str, object, str], str],
    more_text_fn: Callable[[int], str],
) -> str:
    if not isinstance(param_map, dict) or not param_map:
        return str(none_text or "")

    rows = []
    for name, rule in list(param_map.items())[:4]:
        name_text = str(name)
        current = current_value_fn(name_text)
        constraint = getattr(rule, "constraint", ())
        if all(isinstance(item, str) for item in constraint):
            constraint_text = ", ".join(str(item) for item in constraint[:3])
            if len(constraint) > 3:
                constraint_text = f"{constraint_text}, ..."
        else:
            constraint_text = f"{constraint[0]} -> {constraint[1]}"
        rows.append(str(row_text_fn(name_text, current, constraint_text) or "").strip())

    rows = [row for row in rows if row]
    remaining = max(0, len(param_map) - len(rows))
    if remaining:
        rows.append(str(more_text_fn(remaining) or "").strip())
    return "\n".join(row for row in rows if row)


def controlled_optimization_review_parts(
    tuning_context: dict | None,
    history_context: dict | None,
    *,
    tuning_goal_label_fn: Callable[[str], str] | None = None,
    benchmark_summary_text_fn: Callable[[dict], str] | None = None,
) -> ControlledOptimizationReviewParts:
    tuning = tuning_context if isinstance(tuning_context, dict) else {}
    history = history_context if isinstance(history_context, dict) else {}

    tuning_goal = _context_tuning_goal(tuning, tuning_goal_label_fn)
    if not tuning_goal:
        tuning_goal = _context_tuning_goal(history, tuning_goal_label_fn)

    benchmark_text = str(tuning.get("benchmark_text") or "").strip()
    if not benchmark_text and str(tuning.get("summary") or "").strip():
        benchmark_text = str(tuning.get("summary") or "").strip()
    if not benchmark_text:
        benchmark_text = str(history.get("benchmark_text") or "").strip()
        if not benchmark_text:
            benchmark_summary = history.get("benchmark_summary") if isinstance(history.get("benchmark_summary"), dict) else {}
            if isinstance(benchmark_summary, dict) and benchmark_summary:
                formatter = benchmark_summary_text_fn or (lambda summary: "")
                benchmark_text = str(formatter(benchmark_summary) or "").strip()

    stop_reason = str(tuning.get("stop_reason") or "").strip()
    remaining_risks = str(tuning.get("remaining_risks") or "").strip()
    next_goal = str(tuning.get("next_goal") or "").strip()
    if not stop_reason:
        stop_reason = str(history.get("stop_reason") or "").strip()
    if not remaining_risks:
        remaining_risks = str(history.get("remaining_risks") or "").strip()
    if not next_goal:
        next_goal = str(history.get("next_goal") or "").strip()

    return ControlledOptimizationReviewParts(
        tuning_goal=tuning_goal,
        benchmark_text=benchmark_text,
        stop_reason=stop_reason,
        remaining_risks=remaining_risks,
        next_goal=next_goal,
    )


def _context_tuning_goal(context: dict, tuning_goal_label_fn: Callable[[str], str] | None) -> str:
    if not isinstance(context, dict) or not context:
        return ""
    tuning_goal = str(context.get("tuning_goal_label") or "").strip()
    if tuning_goal:
        return tuning_goal
    raw_goal = str(context.get("tuning_goal") or "").strip()
    if not raw_goal:
        return ""
    formatter = tuning_goal_label_fn or (lambda value: value)
    return str(formatter(raw_goal) or "").strip()


def history_record_confirmed(record) -> bool:
    if not isinstance(record, dict):
        return False
    confirmed = bool(record.get("confirmed"))
    summary = record.get("results_summary") if isinstance(record.get("results_summary"), dict) else {}
    if isinstance(summary, dict):
        confirmed = confirmed or bool(summary.get("confirmed"))
    return confirmed


def history_confirmation_translation_key(confirmed: bool) -> str:
    return "RESULTS_CONFIRM_STATUS_CONFIRMED" if bool(confirmed) else "RESULTS_CONFIRM_STATUS_PENDING"


def current_result_confirmation_label(
    record,
    *,
    inferred_sample_name: str = "",
    technique_label: str = "",
) -> str:
    summary = record.get("results_summary") if isinstance(record, dict) and isinstance(record.get("results_summary"), dict) else {}
    if isinstance(summary, dict):
        label = str(summary.get("project_label") or "").strip()
        if label:
            return label
    return str(inferred_sample_name or "").strip() or str(technique_label or "").strip()


def history_action_state(record, *, has_source: bool, has_compare: bool) -> HistoryActionState:
    has_record = isinstance(record, dict)
    return HistoryActionState(
        has_record=has_record,
        has_source=bool(has_source),
        has_compare=bool(has_compare),
        can_copy_summary=has_record,
        can_restore=has_record and bool(has_source),
        can_rerun=has_record and bool(has_source),
        can_compare=bool(has_compare),
        can_confirm=has_record,
    )


def history_status_label_parts(record) -> HistoryStatusLabelParts:
    raw_status = str(record.get("status") or "").strip().lower() if isinstance(record, dict) else ""
    translation_key = {
        "completed": "SAMPLE_RUN_STATUS_COMPLETED",
        "pending": "SAMPLE_RUN_STATUS_PENDING",
        "failed": "SAMPLE_RUN_STATUS_FAILED",
    }.get(raw_status, "")
    fallback_label = "" if translation_key else (str(record.get("status") or "").strip() if isinstance(record, dict) else "")
    include_saxs_suffix = (
        raw_status == "completed"
        and isinstance(record, dict)
        and str(record.get("technique") or "").strip().lower() == "saxs"
    )
    return HistoryStatusLabelParts(
        translation_key=translation_key,
        fallback_label=fallback_label,
        include_saxs_suffix=include_saxs_suffix,
    )


def history_status_text_parts(
    status_label: str,
    origin_label: str,
    *,
    source_available: bool,
) -> HistoryStatusTextParts:
    labels = [
        text
        for text in (
            str(status_label or "").strip(),
            str(origin_label or "").strip(),
        )
        if text
    ]
    return HistoryStatusTextParts(labels=labels, source_missing=not bool(source_available))


def history_record_context_ref(record) -> HistoryRecordContextRef:
    if not isinstance(record, dict):
        return HistoryRecordContextRef("", "")
    submodule = str(record.get("submodule") or "").strip()
    if submodule:
        return HistoryRecordContextRef("submodule", submodule)
    technique = str(record.get("technique") or "").strip()
    if technique:
        return HistoryRecordContextRef("technique", technique)
    return HistoryRecordContextRef("", "")


def history_copy_summary_tooltip_key(record) -> str:
    return "copy_summary" if isinstance(record, dict) else "select"


def history_restore_tooltip_key(record, *, has_source: bool) -> str:
    if not isinstance(record, dict):
        return "select"
    if not has_source:
        return "source_missing"
    return "restore"


def history_rerun_tooltip_key(record, *, has_source: bool) -> str:
    if not isinstance(record, dict):
        return "select"
    if not has_source:
        return "source_missing"
    return "rerun"


def history_compare_tooltip_key(record, *, has_compare: bool) -> str:
    if not isinstance(record, dict):
        return "select"
    if not has_compare:
        return "compare_unavailable"
    return "compare"


def history_tooltip_translation_key(key: str) -> str:
    return {
        "select": "HISTORY_TOOLTIP_SELECT",
        "source_missing": "HISTORY_TOOLTIP_SOURCE_MISSING",
        "compare_unavailable": "HISTORY_TOOLTIP_COMPARE_UNAVAILABLE",
        "restore": "HISTORY_RESTORE_TOOLTIP",
        "rerun": "HISTORY_RERUN_TOOLTIP",
        "compare": "HISTORY_COMPARE_TOOLTIP",
        "copy_summary": "HISTORY_COPY_SUMMARY_TOOLTIP",
    }.get(str(key or ""), "HISTORY_TOOLTIP_SELECT")


def history_metrics_summary(metrics: dict[str, str], *, technique: str = "", limit: int = 4) -> str:
    if not metrics:
        return ""

    technique_key = str(technique or "").strip().lower()
    if technique_key == "waxs":
        preferred = WAXS_METRICS_PREFERRED_KEYS
    elif technique_key == "saxs":
        preferred = SAXS_METRICS_PREFERRED_KEYS
    else:
        preferred = DEFAULT_METRICS_PREFERRED_KEYS

    ordered_keys = [key for key in preferred if key in metrics]
    ordered_keys.extend(key for key in metrics.keys() if key not in ordered_keys)
    max_items = max(1, int(limit or 0))
    if technique_key == "waxs":
        max_items = max(max_items, 8)
    parts = [f"{key}={metrics.get(key, '')}" for key in ordered_keys[:max_items]]
    return " | ".join(parts)


def history_export_rows(
    headers: Iterable[str],
    matrix: Iterable[Iterable[str]],
    cache: Iterable[dict],
    *,
    origin_label_fn: Callable[[dict], str],
) -> tuple[list[str], list[list[str]]]:
    table_headers = list(headers)
    table_matrix = [list(row) for row in matrix]
    if not table_headers or not table_matrix:
        return [], []

    export_headers = list(table_headers) + ["Result origin", "AI tuned", "Source data", "Output dir"]
    records = list(cache)
    rows = []
    for row_index, values in enumerate(table_matrix):
        record = records[row_index] if row_index < len(records) else {}
        summary = record.get("results_summary") if isinstance(record, dict) and isinstance(record.get("results_summary"), dict) else {}
        origin_label = origin_label_fn(record) if isinstance(record, dict) else ""
        ai_tuned = "Yes" if bool(summary.get("ai_tuned")) else "No"
        source_data = str(summary.get("data_file") or "").strip() if isinstance(summary, dict) else ""
        output_dir = str(record.get("output_dir") or "").strip() if isinstance(record, dict) else ""
        rows.append(list(values) + [origin_label, ai_tuned, source_data, output_dir])
    return export_headers, rows


def validation_summary_parts(record) -> ValidationSummaryParts:
    if not isinstance(record, dict):
        return ValidationSummaryParts(summary="", warnings=[])
    summary = record.get("results_summary") if isinstance(record.get("results_summary"), dict) else {}
    if not isinstance(summary, dict):
        summary = {}

    candidates = [
        summary.get("validation_summary"),
        summary.get("result", {}).get("validation_summary") if isinstance(summary.get("result"), dict) else "",
        record.get("validation_summary"),
    ]
    validation_summary = ""
    for candidate in candidates:
        text = str(candidate or "").strip()
        if text:
            validation_summary = text
            break

    validation_warnings: list[str] = []
    for container in (
        summary,
        summary.get("result", {}) if isinstance(summary.get("result"), dict) else {},
        record,
    ):
        if not isinstance(container, dict):
            continue
        warnings = container.get("validation_warnings")
        if isinstance(warnings, list):
            validation_warnings.extend(str(item).strip() for item in warnings if str(item).strip())

    return ValidationSummaryParts(
        summary=validation_summary,
        warnings=list(dict.fromkeys(validation_warnings)),
    )


def history_validation_summary_text(
    record,
    *,
    quality_flag_summary_fn: Callable[[dict], str] | None = None,
) -> str:
    parts = validation_summary_parts(record)
    validation_summary = parts.summary
    summary = record.get("results_summary") if isinstance(record, dict) and isinstance(record.get("results_summary"), dict) else {}
    result_payload = summary.get("result", {}) if isinstance(summary.get("result"), dict) else {}

    quality_flag_summary = ""
    if isinstance(result_payload, dict) and result_payload and quality_flag_summary_fn is not None:
        quality_flag_summary = str(quality_flag_summary_fn(result_payload) or "").strip()

    if not validation_summary:
        return quality_flag_summary
    if validation_summary == "All checks passed":
        return quality_flag_summary or validation_summary
    if parts.warnings:
        return f"{validation_summary} | {', '.join(parts.warnings[:4])}"
    return validation_summary


def history_compare_record(record, runs: Iterable[dict]) -> dict | None:
    if not isinstance(record, dict):
        return None
    run_id = str(record.get("id") or "")
    technique = str(record.get("technique") or "")
    submodule = str(record.get("submodule") or "")
    if not run_id or not technique:
        return None

    comparable = [
        run for run in runs
        if str(run.get("technique") or "") == technique
    ]
    if submodule:
        comparable = [
            run for run in comparable
            if str(run.get("submodule") or "") == submodule
        ]
    for index, run in enumerate(comparable):
        if str(run.get("id") or "") == run_id:
            if index + 1 < len(comparable):
                return comparable[index + 1]
            if index > 0:
                return comparable[index - 1]
            break
    for run in comparable:
        if str(run.get("id") or "") != run_id:
            return run
    return None


def history_compare_state_key(current_value: str, baseline_value: str) -> str:
    if current_value == baseline_value:
        return "same"
    if baseline_value == "":
        return "new"
    if current_value == "":
        return "removed"
    return "changed"


def history_compare_state_translation_key(state: str) -> str:
    return {
        "changed": "HISTORY_COMPARE_STATE_CHANGED",
        "new": "HISTORY_COMPARE_STATE_NEW",
        "removed": "HISTORY_COMPARE_STATE_REMOVED",
        "same": "HISTORY_COMPARE_STATE_SAME",
    }.get(str(state or ""), "HISTORY_COMPARE_STATE_CHANGED")


def history_compare_sort_key(row) -> tuple[int, str]:
    key, _current_value, _baseline_value, state = row
    return (COMPARE_STATE_PRIORITY.get(str(state or ""), 99), str(key))


def history_compare_rows(current_metrics: dict[str, str], baseline_metrics: dict[str, str]) -> list[tuple[str, str, str, str]]:
    current = current_metrics if isinstance(current_metrics, dict) else {}
    baseline = baseline_metrics if isinstance(baseline_metrics, dict) else {}
    keys = list(dict.fromkeys(list(current.keys()) + list(baseline.keys())))
    rows = []
    for key in keys:
        current_value = current.get(key, "")
        baseline_value = baseline.get(key, "")
        rows.append((key, current_value, baseline_value, history_compare_state_key(current_value, baseline_value)))
    rows.sort(key=history_compare_sort_key)
    return rows


def history_compare_counts(rows: Iterable[tuple[str, str, str, str]]) -> dict[str, int]:
    counts = {key: 0 for key in COMPARE_STATE_PRIORITY}
    for _key, _current_value, _baseline_value, state in rows:
        state_key = str(state or "")
        counts[state_key] = counts.get(state_key, 0) + 1
    return counts


def result_comparison_summary(
    *,
    current_label: str,
    baseline_label: str,
    current_metrics: dict[str, str],
    baseline_metrics: dict[str, str],
    technique: str,
    strain_active: bool = False,
) -> str:
    current_text = str(current_label or "").strip()
    baseline_text = str(baseline_label or "").strip()
    if not baseline_text:
        return f"Current: {current_text}"

    technique_key = str(technique or "").strip().lower()
    if strain_active:
        compare_keys = SAXS_STRAIN_COMPARISON_KEYS
    elif technique_key == "saxs":
        compare_keys = SAXS_COMPARISON_KEYS
    else:
        compare_keys = DEFAULT_COMPARISON_KEYS

    current = current_metrics if isinstance(current_metrics, dict) else {}
    baseline = baseline_metrics if isinstance(baseline_metrics, dict) else {}
    if strain_active:
        current = dict(current)
        baseline = dict(baseline)
        for metrics in (current, baseline):
            metrics.setdefault(
                "invariant_Q_rel_mean",
                metrics.get("Q_star_rel_mean", ""),
            )
            metrics.setdefault(
                "invariant_Q_rel_span",
                metrics.get("Q_star_rel_span", ""),
            )
    key_changes = []
    for key in compare_keys:
        current_value = current.get(key, "")
        baseline_value = baseline.get(key, "")
        if current_value == baseline_value:
            continue
        if not current_value and not baseline_value:
            continue
        key_changes.append(f"{key}: {baseline_value or '-'} -> {current_value or '-'}")
    if key_changes:
        return f"Current: {current_text} | Baseline: {baseline_text} | Key changes: " + "; ".join(key_changes[:3])
    return f"Current: {current_text} | Baseline: {baseline_text}"


def result_origin_translation_key(origin: str) -> str:
    return {
        "controlled_optimization_rerun": "RESULT_ORIGIN_AI_TUNED",
        "manual_run": "RESULT_ORIGIN_MANUAL",
    }.get(str(origin or "").strip(), "")


def result_comparison_record_label(
    record,
    *,
    context_label: str = "",
    origin_label: str = "",
) -> str:
    if not isinstance(record, dict):
        return ""
    summary = record.get("results_summary") if isinstance(record.get("results_summary"), dict) else {}
    sample = str(summary.get("project_label") or "").strip()
    context = str(context_label or "").strip()
    created = format_history_timestamp(record.get("created_at"))
    origin = str(origin_label or "").strip()
    return " | ".join(part for part in (sample, context, created, origin) if part)


def result_compare_candidate_id(record) -> str:
    if not isinstance(record, dict):
        return ""
    return str(record.get("id") or "").strip()


def result_compare_candidate_label(label: str, *, index=None, empty_label: str = "") -> str:
    text = str(label or "").strip() or str(empty_label or "").strip()
    if index is None:
        return text
    return f"{int(index) + 1}. {text}"


def result_comparison_baseline(candidates: Iterable[dict], *, selected_id: str = "") -> dict | None:
    items = list(candidates or [])
    if not items:
        return None
    selected = str(selected_id or "").strip()
    if selected:
        for candidate in items:
            if result_compare_candidate_id(candidate) == selected:
                return candidate
    return items[0]


def _comparison_created_score(value) -> float:
    text = str(value or "").replace("T", " ").strip()
    if not text:
        return 0.0
    for pattern in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, pattern).timestamp()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return 0.0


def _normalized_comparison_path(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return os.path.normcase(os.path.normpath(text))


def result_comparison_candidates(current, db, *, inferred_sample_name: str = "") -> list[dict]:
    if not isinstance(current, dict) or not current or db is None:
        return []
    summary = current.get("results_summary") if isinstance(current.get("results_summary"), dict) else {}
    sample_name = str(summary.get("project_label") or inferred_sample_name or "").strip().lower()
    current_technique = str(current.get("technique") or "").strip().lower()
    current_submodule = str(current.get("submodule") or "").strip().lower()
    current_data_file = _normalized_comparison_path(summary.get("data_file"))
    if not current_technique:
        return []

    scored = []
    for sample in db.list_samples(limit=100):
        sample_score = 2
        candidate_name = str(sample.get("polymer_name") or "").strip().lower()
        if sample_name and candidate_name == sample_name:
            sample_score = 0
        elif sample_name:
            continue
        for batch in db.get_batches(sample.get("id", "")):
            batch_score = 1 if sample_score == 0 else 2
            for run in db.get_analysis_runs(batch.get("id", "")):
                if str(run.get("technique") or "").strip().lower() != current_technique:
                    continue
                if str(run.get("id") or "") == "current":
                    continue
                run_submodule = str(run.get("submodule") or "").strip().lower()
                if current_submodule and run_submodule not in {current_submodule, ""}:
                    continue
                run_summary = run.get("results_summary") if isinstance(run.get("results_summary"), dict) else {}
                run_data_file = _normalized_comparison_path(run_summary.get("data_file"))
                data_file_score = 0 if current_data_file and run_data_file == current_data_file else 1
                submodule_score = 0 if current_submodule and run_submodule == current_submodule else 1
                scored.append((sample_score, data_file_score, batch_score, submodule_score, -_comparison_created_score(run.get("created_at")), run))

    if not scored:
        for sample in db.list_samples(limit=100):
            for batch in db.get_batches(sample.get("id", "")):
                for run in db.get_analysis_runs(batch.get("id", "")):
                    if str(run.get("id") or "") == "current":
                        continue
                    if str(run.get("technique") or "").strip().lower() != current_technique:
                        continue
                    run_submodule = str(run.get("submodule") or "").strip().lower()
                    if current_submodule and run_submodule not in {current_submodule, ""}:
                        continue
                    run_summary = run.get("results_summary") if isinstance(run.get("results_summary"), dict) else {}
                    run_data_file = _normalized_comparison_path(run_summary.get("data_file"))
                    scored.append((
                        3,
                        0 if current_data_file and run_data_file == current_data_file else 1,
                        3,
                        1 if current_submodule and run_submodule == current_submodule else 2,
                        -_comparison_created_score(run.get("created_at")),
                        run,
                    ))

    scored.sort(key=lambda item: (item[0], item[1], item[2], item[3], item[4]))
    return [item[5] for item in scored]


def result_to_jsonable(value, *, warning_fn: Callable[[str], None] | None = None):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): result_to_jsonable(item, warning_fn=warning_fn) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [result_to_jsonable(item, warning_fn=warning_fn) for item in value]
    if hasattr(value, "tolist"):
        success, converted = safe_jsonable_method_result(
            value,
            "tolist",
            warning_message="Failed to convert array-like value with tolist().",
            warning_fn=warning_fn,
        )
        if success:
            return result_to_jsonable(converted, warning_fn=warning_fn)
    if hasattr(value, "item"):
        success, converted = safe_jsonable_method_result(
            value,
            "item",
            warning_message="Failed to unwrap scalar value with item().",
            warning_fn=warning_fn,
        )
        if success:
            return converted
    return str(value)


def result_review_metric_summary(
    metrics: dict[str, str],
    *,
    technique: str = "",
    strain_active: bool = False,
    limit: int = 4,
) -> str:
    if not isinstance(metrics, dict) or not metrics:
        return ""
    is_strain = str(technique or "").strip().lower() == "saxs" and strain_active
    keys = STRAIN_REVIEW_METRIC_KEYS if is_strain else DEFAULT_REVIEW_METRIC_KEYS
    normalized_metrics = dict(metrics)
    if is_strain:
        normalized_metrics.setdefault(
            "invariant_Q_rel_mean",
            normalized_metrics.get("Q_star_rel_mean", ""),
        )
    metric_parts = []
    for key in keys:
        value = normalized_metrics.get(key, "")
        if value:
            metric_parts.append(f"{key}={value}")
    return ", ".join(metric_parts[: max(1, int(limit or 0))])


def _waxs_core_summary_text(current_metrics=None) -> str:
    metrics = current_metrics if isinstance(current_metrics, dict) else {}
    parts: list[str] = []
    for key in ("n_peaks", "Xc_pct", "D_Scherrer_nm"):
        value = metrics.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            parts.append(f"{key}={text}")
    return ", ".join(parts)


def _waxs_support_summary_text(
    analysis_evidence=None,
    *,
    trend_evidence=None,
    format_score_value_fn: Callable[[object], str] | None = None,
) -> str:
    evidence = analysis_evidence if isinstance(analysis_evidence, dict) else {}
    snapshot = {
        key: gui_coerce_summary_float(evidence.get(key))
        for key in (
            "peak_support_score",
            "background_stability_score",
            "phase_support_score",
            "size_support_score",
        )
    }
    trend = trend_evidence if isinstance(trend_evidence, dict) else {}
    parts: list[str] = []
    format_score = format_score_value_fn or (lambda value: f"{value:.3f}")
    for label, key in (
        ("peak", "peak_support_score"),
        ("background", "background_stability_score"),
        ("phase", "phase_support_score"),
        ("size", "size_support_score"),
    ):
        value = snapshot.get(key)
        if value is not None:
            parts.append(f"{label}={format_score(value)}")
    trend_value = gui_coerce_summary_float(trend.get("D_trend_support_score"))
    if trend_value is not None:
        parts.append(f"D_trend={format_score(trend_value)}")
    waxs_support_value = gui_coerce_summary_float(evidence.get("waxs_support_score"))
    if waxs_support_value is not None:
        parts.append(f"waxs_support_score={format_score(waxs_support_value)}")
    return " | ".join(parts)


def result_source_summary_text(
    record,
    *,
    current_metrics: dict[str, str] | None = None,
    evidence: dict | None = None,
    origin_label: str = "",
    technique: str = "",
    trend_evidence: dict | None = None,
    empty_text: str = "",
    format_score_value_fn: Callable[[object], str] | None = None,
    display_text_fn: Callable[[object], str] | None = None,
    constraint_text: str = "",
    dsc_support_text: str = "",
    ir_support_text: str = "",
) -> str:
    if not isinstance(record, dict) or not record:
        return str(empty_text or "")

    summary = record.get("results_summary") if isinstance(record.get("results_summary"), dict) else {}
    if not isinstance(summary, dict):
        summary = {}
    metrics = current_metrics if isinstance(current_metrics, dict) else {}
    evidence = evidence if isinstance(evidence, dict) else {}
    trend = trend_evidence if isinstance(trend_evidence, dict) else {}
    empty = str(empty_text or "")
    format_score = format_score_value_fn or (lambda value: str(value))
    display_text = display_text_fn or (lambda value: str(value or "").strip() or empty)

    bits = [part for part in [str(origin_label or "").strip()] if part]
    technique_key = str(technique or record.get("technique") or "").strip().lower()
    if technique_key == "waxs":
        waxs_parts = []
        core_text = _waxs_core_summary_text(metrics)
        if core_text:
            waxs_parts.append(core_text)
        support_parts = []
        support_text = _waxs_support_summary_text(
            evidence,
            trend_evidence=trend,
            format_score_value_fn=format_score,
        )
        if support_text:
            support_parts.append(support_text)
        trend_bits = []
        for label, value in (
            ("score", trend.get("D_trend_support_score")),
            ("mode", trend.get("D_trend_monotonicity")),
        ):
            text = display_text(value)
            if text != empty:
                trend_bits.append(f"{label}={text}")
        if trend.get("instrument_broadening_present") is not None:
            trend_bits.append(f"instrument_broadening={bool(trend.get('instrument_broadening_present'))}")
        if waxs_parts:
            bits.append("core=" + ", ".join(waxs_parts[:3]))
        if trend_bits:
            bits.append("trend=" + ", ".join(trend_bits))
        if support_parts:
            bits.append("support=" + " | ".join(support_parts[:6]))
    elif technique_key == "dsc":
        dsc_parts = []
        for key in ("Tg_C", "Tm_peak_C", "Tcc_peak_C", "DHm_Jg", "DHc_Jg", "DHcc_Jg", "Xc_pct"):
            value = metrics.get(key, "")
            if value:
                dsc_parts.append(f"{key}={value}")
        if dsc_parts:
            bits.append("core=" + ", ".join(dsc_parts[:5]))
        support_text = str(dsc_support_text or "").strip()
        if support_text and support_text != empty:
            bits.append(support_text)
    elif technique_key == "ir":
        support_text = str(ir_support_text or "").strip()
        if support_text:
            bits.append(support_text)
    else:
        metric_bits = []
        for key in ("r_squared", "quality_score", "L_nm", "Xc_pct", "D_Scherrer_nm"):
            value = metrics.get(key, "")
            if value:
                metric_bits.append(f"{key}={value}")
        if metric_bits:
            bits.append("core=" + ", ".join(metric_bits[:4]))

    validation = str(summary.get("validation_summary") or record.get("validation_summary") or "").strip()
    if validation:
        bits.append(f"validation={validation}")
    constraint = str(constraint_text or "").strip()
    if constraint and constraint != empty:
        bits.append(constraint)
    return " | ".join(bits) if bits else empty


def quality_flag_summary_text(result, *, language: str = "en") -> str:
    if result is None:
        return ""
    if isinstance(result, dict):
        quality_flag = str(result.get("quality_flag", "") or "").strip()
    else:
        quality_flag = str(getattr(result, "quality_flag", "") or "").strip()
    if not quality_flag or quality_flag == "OK":
        return ""

    flags = [item.strip() for item in quality_flag.split(";") if item.strip()]
    if not flags:
        return ""

    if str(language or "").strip().lower().startswith("zh"):
        mapping = {
            "WARN:low_snr": "主峰信噪比偏低",
            "WARN:sasmodels_low_r2": "sasmodels 拟合偏弱",
            "ERROR:sasmodels_failed": "sasmodels 拟合失败",
            "WARN:qstar_series_jump": "相邻帧 Q* 跳变较大",
            "WARN:qstar_anomalous": "Q* 数值异常",
            "ERROR:lc_ge_L": "lc 与 L 的关系不成立",
            "ERROR:L_out_of_range": "长周期超出物理范围",
            "ERROR:L_not_computed": "长周期未能稳定计算",
        }
        parts = [mapping.get(flag, flag.replace("ERROR:", "").replace("WARN:", "").replace("_", " ")) for flag in flags[:4]]
        return "；".join(parts)

    mapping = {
        "WARN:low_snr": "low peak SNR",
        "WARN:sasmodels_low_r2": "weak sasmodels fit",
        "ERROR:sasmodels_failed": "sasmodels fit failed",
        "WARN:qstar_series_jump": "adjacent-frame Q* jump",
        "WARN:qstar_anomalous": "anomalous Q*",
        "ERROR:lc_ge_L": "lc >= L",
        "ERROR:L_out_of_range": "L outside the physical range",
        "ERROR:L_not_computed": "long period not computed",
    }
    parts = [mapping.get(flag, flag.replace("ERROR:", "").replace("WARN:", "").replace("_", " ")) for flag in flags[:4]]
    return "; ".join(parts)


def ai_tuning_change_summary_text(
    changes,
    *,
    empty_text: str,
    display_text_fn: Callable[[object], str],
    more_text_fn: Callable[[int], str],
) -> str:
    if not isinstance(changes, dict) or not changes:
        return str(empty_text or "")
    parts = []
    items = list(changes.items())
    for key, value in items[:3]:
        parts.append(f"{key} -> {display_text_fn(value)}")
    remaining = len(items) - len(parts)
    if remaining > 0:
        parts.append(str(more_text_fn(remaining) or "").strip())
    return "; ".join(part for part in parts if part)


def ai_tuning_remaining_risks_text(history, *, empty_text: str) -> str:
    risks = []
    items = history if isinstance(history, list) else []
    for item in items:
        if not isinstance(item, dict) or bool(item.get("accepted", True)):
            continue
        detail = str(item.get("rollback_detail", "") or "").strip()
        if detail and detail not in risks:
            risks.append(detail)
        advice = item.get("llm_advice") if isinstance(item.get("llm_advice"), dict) else {}
        rollback_reason = str(advice.get("rollback_reason", "") or "").strip()
        if rollback_reason and rollback_reason not in risks:
            risks.append(rollback_reason)
    return "; ".join(risks[:3]) if risks else str(empty_text or "")


def ai_tuning_stability_summary_parts(
    analysis_evidence,
    *,
    empty_text: str,
    format_score_fn: Callable[[object], str],
) -> tuple[str, str, str, str, str] | None:
    evidence = analysis_evidence.get("stability_evidence", {}) if isinstance(analysis_evidence, dict) else {}
    if not isinstance(evidence, dict) or not evidence:
        return None
    flags = evidence.get("stability_flags", [])
    if isinstance(flags, list):
        flag_values = [str(item).strip() for item in flags if str(item).strip()]
    else:
        flag_values = [str(flags).strip()] if str(flags).strip() else []
    return (
        str(format_score_fn(evidence.get("stability_score"))),
        str(format_score_fn(evidence.get("parameter_stability_score"))),
        str(format_score_fn(evidence.get("method_agreement_score"))),
        str(format_score_fn(evidence.get("batch_continuity_score"))),
        ", ".join(flag_values[:4]) if flag_values else str(empty_text or ""),
    )


def ai_tuning_constraint_summary_parts(
    analysis_evidence,
    *,
    empty_text: str,
    display_text_fn: Callable[[object], str],
) -> tuple[str, int, int, int, str] | None:
    summary = analysis_evidence.get("constraint_summary", {}) if isinstance(analysis_evidence, dict) else {}
    if not isinstance(summary, dict) or not summary:
        return None
    counts = summary.get("triggered_counts", {}) if isinstance(summary.get("triggered_counts"), dict) else {}
    triggered_names = summary.get("triggered_names", {}) if isinstance(summary.get("triggered_names"), dict) else {}
    names = []
    for key in ("hard_fail", "soft_warn", "evidence_only"):
        value = triggered_names.get(key, [])
        if isinstance(value, list):
            for item in value:
                text = str(item or "").strip()
                if text and text not in names:
                    names.append(text)
    return (
        str(display_text_fn(summary.get("status")) or str(empty_text or "")),
        int(counts.get("hard_fail", 0) or 0),
        int(counts.get("soft_warn", 0) or 0),
        int(counts.get("evidence_only", 0) or 0),
        ", ".join(names[:4]),
    )


def batch_fallback_summary_parts(analysis_evidence, *, symptom_names: Iterable[str]) -> list[JointPromptParts]:
    if not isinstance(analysis_evidence, dict) or not analysis_evidence:
        return []
    batch = analysis_evidence.get("batch_evidence", {}) if isinstance(analysis_evidence.get("batch_evidence"), dict) else {}
    structure = analysis_evidence.get("structure_evidence", {}) if isinstance(analysis_evidence.get("structure_evidence"), dict) else {}
    batch_summary = batch.get("batch_calibration_summary") if isinstance(batch.get("batch_calibration_summary"), dict) else {}
    symptoms = {str(item or "").strip() for item in symptom_names if str(item or "").strip()}

    if not batch_summary and "temperature_calibration_fallback_active" not in symptoms:
        return []

    parts: list[JointPromptParts] = []
    fallback_ratio = gui_coerce_summary_float(batch_summary.get("fallback_ratio"))
    if fallback_ratio is not None and fallback_ratio > 0:
        parts.append(JointPromptParts("RESULTS_REVIEW_FALLBACK_ACTIVE", (f"{fallback_ratio * 100:.0f}",)))

    raw_rows = batch_summary.get("raw_snapshot_rows")
    try:
        raw_rows_int = int(raw_rows)
    except (TypeError, ValueError):
        raw_rows_int = 0
    if raw_rows_int > 0:
        parts.append(JointPromptParts("RESULTS_REVIEW_FALLBACK_RAW", (raw_rows_int,)))

    if "batch_summary_conflicts_with_frame_evidence" in symptoms:
        parts.append(JointPromptParts("RESULTS_REVIEW_FALLBACK_CONFLICT"))
    if "thickness_chain_unreliable" in symptoms:
        parts.append(JointPromptParts("RESULTS_REVIEW_FALLBACK_THICKNESS"))

    reason = str(
        batch_summary.get("calibrated_fallback_reason")
        or structure.get("calibrated_fallback_reason")
        or ""
    ).strip()
    if reason:
        parts.append(JointPromptParts("RESULTS_REVIEW_FALLBACK_REASON", (reason,)))
    skip_reason = str(
        batch_summary.get("calibration_skipped_reason")
        or structure.get("calibration_skipped_reason")
        or ""
    ).strip()
    if skip_reason:
        parts.append(JointPromptParts("RESULTS_REVIEW_FALLBACK_REASON", (skip_reason,)))

    return parts


def saxs_lc_status_summary_parts(params, analysis_evidence) -> tuple[str, int, int, str] | None:
    param_values = params if isinstance(params, dict) else {}
    evidence = analysis_evidence if isinstance(analysis_evidence, dict) else {}
    batch_summary = {}
    if evidence:
        batch = evidence.get("batch_evidence", {}) if isinstance(evidence.get("batch_evidence"), dict) else {}
        batch_summary = batch.get("batch_structure_summary", {}) if isinstance(batch.get("batch_structure_summary"), dict) else {}
        if not batch_summary:
            structure = evidence.get("structure_evidence", {}) if isinstance(evidence.get("structure_evidence"), dict) else {}
            status = str(structure.get("lc_reliability_status") or "").strip()
            if status:
                melting_status = str(structure.get("melting_window_status") or "").strip()
                batch_summary = {
                    "dominant_lc_reliability_status": status,
                    "dominant_lc_reliability_reason": str(structure.get("lc_reliability_reason") or "").strip() or "",
                    "dominant_melting_window_status": melting_status,
                    "diagnostic_only_rows": 1 if status == "diagnostic_only" else 0,
                    "within_window_rows": 1 if melting_status == "within_window" else 0,
                }

    if not batch_summary and isinstance(param_values.get("batch_structure_summary"), dict):
        batch_summary = param_values.get("batch_structure_summary", {})

    if not isinstance(batch_summary, dict) or not batch_summary:
        return None

    diagnostic_rows = batch_summary.get("diagnostic_only_rows")
    within_window_rows = batch_summary.get("within_window_rows")
    status = str(
        batch_summary.get("dominant_lc_reliability_status")
        or param_values.get("lc_reliability_status")
        or ""
    ).strip()
    reason = str(
        batch_summary.get("dominant_lc_reliability_reason")
        or param_values.get("lc_reliability_reason")
        or ""
    ).strip()

    try:
        diagnostic_rows_int = int(diagnostic_rows or 0)
    except (TypeError, ValueError):
        diagnostic_rows_int = 0
    try:
        within_window_rows_int = int(within_window_rows or 0)
    except (TypeError, ValueError):
        within_window_rows_int = 0

    if not status and diagnostic_rows_int <= 0 and within_window_rows_int <= 0:
        return None
    return status, diagnostic_rows_int, within_window_rows_int, reason


def saxs_structure_status_snapshot(
    params,
    analysis_evidence,
    *,
    symptom_names: Iterable[str] | None,
) -> dict[str, object]:
    param_values = params if isinstance(params, dict) else {}
    evidence = analysis_evidence if isinstance(analysis_evidence, dict) else {}
    batch = evidence.get("batch_evidence", {}) if isinstance(evidence.get("batch_evidence"), dict) else {}
    structure = evidence.get("structure_evidence", {}) if isinstance(evidence.get("structure_evidence"), dict) else {}
    batch_summary = batch.get("batch_structure_summary", {}) if isinstance(batch.get("batch_structure_summary"), dict) else {}
    if not batch_summary and isinstance(param_values.get("batch_structure_summary"), dict):
        batch_summary = param_values.get("batch_structure_summary", {})

    symptoms = sorted(
        {
            str(item or "").strip()
            for item in (symptom_names or ())
            if str(item or "").strip()
        }
    )

    def _as_int(value) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    status = str(
        batch_summary.get("dominant_lc_reliability_status")
        or structure.get("lc_reliability_status")
        or param_values.get("lc_reliability_status")
        or ""
    ).strip()
    reason = str(
        batch_summary.get("dominant_lc_reliability_reason")
        or structure.get("lc_reliability_reason")
        or param_values.get("lc_reliability_reason")
        or ""
    ).strip()
    melting_status = str(
        batch_summary.get("dominant_melting_window_status")
        or structure.get("melting_window_status")
        or param_values.get("melting_window_status")
        or ""
    ).strip()
    melting_reason = str(
        batch_summary.get("dominant_melting_window_reason")
        or structure.get("melting_window_reason")
        or param_values.get("melting_window_reason")
        or ""
    ).strip()
    batch_rows = _as_int(batch_summary.get("batch_rows") or param_values.get("batch_frames"))
    diagnostic_rows = _as_int(batch_summary.get("diagnostic_only_rows"))
    low_conf_rows = _as_int(batch_summary.get("low_confidence_rows"))
    usable_rows = _as_int(batch_summary.get("usable_rows"))
    within_window_rows = _as_int(batch_summary.get("within_window_rows"))
    near_onset_rows = _as_int(batch_summary.get("near_onset_rows"))
    post_end_rows = _as_int(batch_summary.get("post_end_rows"))
    if batch_rows <= 0:
        batch_rows = max(
            diagnostic_rows + low_conf_rows + usable_rows + within_window_rows + near_onset_rows + post_end_rows,
            1 if any([status, reason, melting_status, melting_reason]) else 0,
        )

    return {
        "batch_rows": batch_rows,
        "lc_reliability_status": status,
        "lc_reliability_reason": reason,
        "melting_window_status": melting_status,
        "melting_window_reason": melting_reason,
        "diagnostic_only_rows": diagnostic_rows,
        "low_confidence_rows": low_conf_rows,
        "usable_rows": usable_rows,
        "within_window_rows": within_window_rows,
        "near_onset_rows": near_onset_rows,
        "post_end_rows": post_end_rows,
        "symptoms": symptoms,
    }


def saxs_strain_evidence_snapshot(
    params,
    analysis_evidence,
    *,
    symptom_names: Iterable[str] | None,
) -> dict[str, object]:
    param_values = params if isinstance(params, dict) else {}
    evidence = analysis_evidence if isinstance(analysis_evidence, dict) else {}
    feature = evidence.get("feature_evidence", {}) if isinstance(evidence.get("feature_evidence"), dict) else {}
    condition = feature.get("condition_evidence", {}) if isinstance(feature.get("condition_evidence"), dict) else {}
    structure = feature.get("strain_structure_evidence", {}) if isinstance(feature.get("strain_structure_evidence"), dict) else {}
    if not condition and isinstance(evidence.get("condition_evidence"), dict):
        condition = evidence.get("condition_evidence", {})
    if not condition and isinstance(param_values.get("condition_evidence"), dict):
        condition = param_values.get("condition_evidence", {})
    if not structure and isinstance(param_values.get("strain_structure_evidence"), dict):
        structure = param_values.get("strain_structure_evidence", {})

    symptoms = sorted(
        {
            str(item or "").strip()
            for item in (symptom_names or ())
            if str(item or "").strip()
        }
    )
    condition_label = str(
        condition.get("condition_label")
        or param_values.get("condition_label")
        or evidence.get("condition_label")
        or ""
    ).strip().lower()
    strain_structure_keys = {
        "invariant_Q_rel_mean",
        "invariant_Q_rel_span",
        "Q_star_rel_mean",
        "Q_star_rel_span",
        "phi_void_mean",
        "phi_void_span",
        "void_detected_frames",
        "f_Herman_mean",
        "f_Herman_span",
        "porod_slope_mean",
        "porod_slope_span",
    }
    active = bool(
        condition_label == "strain"
        or any(key in structure for key in strain_structure_keys)
        or any(
            symptom in {
                "low_q_void_dominant",
                "strain_void_lamellar_conflict",
                "lamellar_anchor_lost_under_strain",
                "qstar_rel_without_lamellar_support",
                "orientation_shift_breaks_lamellar_comparison",
            }
            for symptom in symptoms
        )
    )

    def _as_float(value):
        return gui_coerce_summary_float(value)

    def _as_optional_bool(value):
        return bool(value) if value is not None else None

    return {
        "active": active,
        "condition_label": condition_label,
        "strain_axis_confidence": _as_float(condition.get("strain_axis_confidence", condition.get("condition_confidence"))),
        "strain_monotonic": condition.get("strain_monotonic"),
        "strain_missing_count": condition.get("strain_missing_count"),
        "strain_duplicate_count": condition.get("strain_duplicate_count"),
        "strain_min_pct": _as_float(condition.get("strain_min_pct")),
        "strain_max_pct": _as_float(condition.get("strain_max_pct")),
        "invariant_Q_rel_mean": _as_float(
            structure.get("invariant_Q_rel_mean", structure.get("Q_star_rel_mean"))
        ),
        "invariant_Q_rel_span": _as_float(
            structure.get("invariant_Q_rel_span", structure.get("Q_star_rel_span"))
        ),
        "phi_void_mean": _as_float(structure.get("phi_void_mean")),
        "phi_void_span": _as_float(structure.get("phi_void_span")),
        "void_detected_frames": structure.get("void_detected_frames"),
        "f_Herman_mean": _as_float(structure.get("f_Herman_mean")),
        "f_Herman_span": _as_float(structure.get("f_Herman_span")),
        "porod_slope_mean": _as_float(structure.get("porod_slope_mean")),
        "porod_slope_span": _as_float(structure.get("porod_slope_span")),
        "dominant_phase": str(structure.get("dominant_phase") or "").strip().lower(),
        "strain_reliability_status": str(structure.get("strain_reliability_status") or "").strip().lower(),
        "strain_reliability_reason": str(structure.get("strain_reliability_reason") or "").strip(),
        "paper_figure_candidate": _as_optional_bool(structure.get("paper_figure_candidate")),
        "paper_conclusion_candidate": _as_optional_bool(structure.get("paper_conclusion_candidate")),
        "paper_conclusion_ready": _as_optional_bool(structure.get("paper_conclusion_ready")),
        "phase_support_mean": _as_float(structure.get("phase_support_mean")),
        "phase_support_span": _as_float(structure.get("phase_support_span")),
        "symptoms": symptoms,
    }


def saxs_strain_summary_text(
    params,
    analysis_evidence,
    *,
    symptom_names: Iterable[str] | None,
    language: str = "en",
) -> str:
    snapshot = saxs_strain_evidence_snapshot(params, analysis_evidence, symptom_names=symptom_names)
    if not snapshot.get("active"):
        return ""

    zh = str(language or "").strip().lower().startswith("zh")
    axis_bits = []
    axis_conf = snapshot.get("strain_axis_confidence")
    if axis_conf is not None:
        axis_bits.append(f"{'置信度' if zh else 'confidence'}={axis_conf:.2f}")
    monotonic = snapshot.get("strain_monotonic")
    if monotonic is not None:
        if zh:
            axis_bits.append(f"单调={'是' if monotonic else '否'}")
        else:
            axis_bits.append(f"monotonic={'yes' if monotonic else 'no'}")
    for label, key in (("缺失" if zh else "missing", "strain_missing_count"), ("重复" if zh else "duplicate", "strain_duplicate_count")):
        value = snapshot.get(key)
        if value not in (None, "", []):
            axis_bits.append(f"{label}={value}")
    if snapshot.get("strain_min_pct") is not None or snapshot.get("strain_max_pct") is not None:
        low = snapshot.get("strain_min_pct")
        high = snapshot.get("strain_max_pct")
        if low is not None and high is not None:
            axis_bits.append(f"{'范围' if zh else 'range'}={low:.2f}-{high:.2f}%")

    structure_bits = []
    status = snapshot.get("strain_reliability_status")
    if status:
        structure_bits.append(f"{'状态' if zh else 'status'}={status}")
    dominant_phase = snapshot.get("dominant_phase")
    if dominant_phase:
        structure_bits.append(f"{'阶段' if zh else 'phase'}={dominant_phase}")
    q_mean = snapshot.get("invariant_Q_rel_mean")
    q_span = snapshot.get("invariant_Q_rel_span")
    if q_mean is not None:
        text = f"invariant_Q_rel={q_mean:.4f}"
        if q_span is not None:
            text += f"±{q_span / 2:.4f}" if q_span is not None else ""
        structure_bits.append(text)
    phi_mean = snapshot.get("phi_void_mean")
    phi_span = snapshot.get("phi_void_span")
    if phi_mean is not None:
        text = f"{'空穴' if zh else 'void'}={phi_mean:.4f}"
        if phi_span is not None:
            text += f" ({'span' if zh else 'span'}={phi_span:.4f})"
        structure_bits.append(text)
    void_frames = snapshot.get("void_detected_frames")
    if void_frames not in (None, ""):
        structure_bits.append(f"{'空穴帧' if zh else 'void frames'}={void_frames}")
    f_mean = snapshot.get("f_Herman_mean")
    f_span = snapshot.get("f_Herman_span")
    if f_mean is not None:
        text = f"f_Herman={f_mean:.4f}"
        if f_span is not None:
            text += f" ({'span' if zh else 'span'}={f_span:.4f})"
        structure_bits.append(text)
    porod_mean = snapshot.get("porod_slope_mean")
    porod_span = snapshot.get("porod_slope_span")
    if porod_mean is not None:
        text = f"Porod={porod_mean:.4f}"
        if porod_span is not None:
            text += f" ({'span' if zh else 'span'}={porod_span:.4f})"
        structure_bits.append(text)
    if snapshot.get("paper_figure_candidate") is not None:
        structure_bits.append(f"{'论文图候选' if zh else 'paper-figure'}={str(bool(snapshot.get('paper_figure_candidate'))).lower()}")
    if snapshot.get("paper_conclusion_candidate") is not None:
        structure_bits.append(f"{'论文结论候选' if zh else 'paper-conclusion'}={str(bool(snapshot.get('paper_conclusion_candidate'))).lower()}")
    if snapshot.get("paper_conclusion_ready") is not None:
        structure_bits.append(f"{'可直接结论' if zh else 'paper-ready'}={str(bool(snapshot.get('paper_conclusion_ready'))).lower()}")

    risk_bits = []
    for symptom in snapshot.get("symptoms", []):
        if symptom == "low_q_void_dominant":
            risk_bits.append("low-q / 空穴主导" if zh else "low-q / void dominant")
        elif symptom == "strain_void_lamellar_conflict":
            risk_bits.append("空穴与层片解释冲突" if zh else "void conflicts with lamellar reading")
        elif symptom == "lamellar_anchor_lost_under_strain":
            risk_bits.append("长周期锚点不稳" if zh else "long-period anchor lost")
        elif symptom == "qstar_rel_without_lamellar_support":
            risk_bits.append("Q*rel 缺少层片支撑" if zh else "Q*rel lacks lamellar support")
        elif symptom == "orientation_shift_breaks_lamellar_comparison":
            risk_bits.append("取向变化干扰比较" if zh else "orientation shift breaks comparison")

    parts = []
    if axis_bits:
        parts.append(("strain轴" if zh else "strain axis") + "=" + ", ".join(str(item) for item in axis_bits[:4]))
    if structure_bits:
        parts.append(("结构" if zh else "structure") + "=" + ", ".join(structure_bits[:4]))
    if risk_bits:
        parts.append(("主要问题" if zh else "main issues") + "=" + ", ".join(risk_bits[:3]))
    return " ; ".join(parts)


def saxs_strain_risk_summary_text(
    params,
    analysis_evidence,
    *,
    symptom_names: Iterable[str] | None,
    language: str = "en",
) -> str:
    snapshot = saxs_strain_evidence_snapshot(params, analysis_evidence, symptom_names=symptom_names)
    if not snapshot.get("active"):
        return ""

    symptoms = set(snapshot.get("symptoms") or [])
    high_risk = bool(
        symptoms.intersection(
            {
                "low_q_void_dominant",
                "strain_void_lamellar_conflict",
                "lamellar_anchor_lost_under_strain",
                "qstar_rel_without_lamellar_support",
                "orientation_shift_breaks_lamellar_comparison",
            }
        )
    )
    phi_void = snapshot.get("phi_void_mean")
    q_span = snapshot.get("invariant_Q_rel_span")
    f_span = snapshot.get("f_Herman_span")
    strain_conf = snapshot.get("strain_axis_confidence")
    status = str(snapshot.get("strain_reliability_status") or "").strip().lower()
    if not high_risk and not (
        (phi_void is not None and phi_void >= 0.02)
        or (q_span is not None and q_span >= 0.015)
        or (f_span is not None and f_span >= 0.20)
        or (strain_conf is not None and strain_conf < 0.75)
        or status in {"low_confidence", "diagnostic_only"}
    ):
        return ""

    if str(language or "").strip().lower().startswith("zh"):
        return "风险提示 | 拉伸 SAXS 的 low-q / 空穴 / 取向链还没站稳，不要硬把结果抬成稳定结论"
    if status:
        return f"Risk note | tensile SAXS status={status}, so keep the result in diagnostic framing until the chain stabilizes"
    return "Risk note | the tensile SAXS low-q / void / orientation chain is still unstable, so do not force a stable conclusion yet"


def saxs_strain_next_step_text(
    params,
    analysis_evidence,
    *,
    symptom_names: Iterable[str] | None,
    language: str = "en",
) -> str:
    snapshot = saxs_strain_evidence_snapshot(params, analysis_evidence, symptom_names=symptom_names)
    if not snapshot.get("active"):
        return ""
    if str(language or "").strip().lower().startswith("zh"):
        return "下一步 | 先对齐 strain 轴、low-q 覆盖、空穴证据和长周期锚点，再决定是否继续调参"
    return "Next step | align the strain axis, low-q coverage, void evidence, and long-period anchor before deciding whether to tune again"


def saxs_reason_text(reason, *, language: str = "en") -> str:
    text = str(reason or "").strip()
    if not text:
        return ""
    zh = str(language or "").strip().lower().startswith("zh")
    mapping = {
        "stable_structure_support": "结构支撑稳定" if zh else "stable structure support",
        "structure_unresolved": "结构未稳定解析" if zh else "structure unresolved",
        "low_lc_confidence": "lc 置信度低" if zh else "low lc confidence",
        "limited_lc_confidence": "lc 置信度有限" if zh else "limited lc confidence",
        "within_melting_window": "位于熔融窗口内" if zh else "within the melting window",
        "near_melting_onset": "接近熔融起点" if zh else "near the melting onset",
        "post_melting_window": "已越过熔融窗口" if zh else "past the melting window",
        "minority_fraction_too_low": "少数相比例过低" if zh else "minority fraction too low",
        "q_invariant_anomaly": "Q* 异常" if zh else "Q* anomaly",
        "frame_analysis_warning": "帧级分析警告" if zh else "frame-level warning",
        "temperature_series_status_unavailable": "温度序列状态不可用" if zh else "temperature-series status unavailable",
        "temperature_unresolved": "温度未解析" if zh else "temperature unresolved",
        "below_sequence_melting_onset": "低于序列熔融起点" if zh else "below the sequence melting onset",
        "near_sequence_melting_onset": "接近序列熔融起点" if zh else "near the sequence melting onset",
        "between_sequence_melting_onset_and_end": "位于序列熔融起点到终点之间" if zh else "between the sequence melting onset and end",
        "between_sequence_melting_onset_and_peak": "位于序列熔融起点到峰值之间" if zh else "between the sequence melting onset and peak",
        "above_sequence_melting_onset_with_unresolved_end": "已高于序列熔融起点但终点未解析" if zh else "above the sequence melting onset with unresolved end",
        "past_sequence_melting_end": "已超过序列熔融终点" if zh else "past the sequence melting end",
        "melting_onset_unresolved": "熔融起点未解析" if zh else "melting onset unresolved",
        "melting_onset_unresolved_peak_only": "仅解析到熔融峰值，起点未定" if zh else "only the melting peak is resolved",
        "above_peak_with_unresolved_end": "已高于峰值但终点未解析" if zh else "above the peak with unresolved end",
    }
    parts = []
    seen = set()
    for token in text.split("|"):
        key = str(token or "").strip()
        if not key:
            continue
        label = mapping.get(key, key.replace("_", " "))
        if label not in seen:
            seen.add(label)
            parts.append(label)
    return ", ".join(parts)


def saxs_lc_status_text(status, *, language: str = "en") -> str:
    text = str(status or "").strip().lower()
    if not text:
        return ""
    zh = str(language or "").strip().lower().startswith("zh")
    mapping = {
        "usable": "可用" if zh else "usable",
        "low_confidence": "低置信" if zh else "low-confidence",
        "diagnostic_only": "仅作诊断" if zh else "diagnostic-only",
    }
    return mapping.get(text, text.replace("_", "-"))


def joint_ai_context(
    report,
    *,
    tuning_context: dict | None = None,
    history_context: dict | None = None,
    no_issue_summary: str = "",
    joint_scope_label: str = "",
) -> dict:
    report = report if isinstance(report, dict) else {}
    context = report.get("ai_context") if isinstance(report.get("ai_context"), dict) else {}
    if context:
        return context

    tuning = tuning_context if isinstance(tuning_context, dict) else {}
    restored_context = tuning.get("joint_ai_context")
    if isinstance(restored_context, dict) and restored_context:
        return restored_context

    history = history_context if isinstance(history_context, dict) else {}
    restored_context = history.get("joint_ai_context") if isinstance(history.get("joint_ai_context"), dict) else {}
    if isinstance(restored_context, dict) and restored_context:
        return restored_context

    rows = report.get("rows") if isinstance(report.get("rows"), list) else []
    validations = report.get("validations") if isinstance(report.get("validations"), list) else []
    if not rows and not validations:
        return {}

    issue_rows = [
        item for item in validations
        if isinstance(item, dict) and str(item.get("severity") or "").strip().upper() in {"WARN", "ERROR"}
    ]
    if not issue_rows:
        return {
            "summary": str(no_issue_summary or "").strip(),
            "scope": str(joint_scope_label or "").strip(),
            "sample_count": len(rows),
            "batch_count": len(rows),
            "issue_count": 0,
            "warning_count": 0,
            "error_count": 0,
            "issue_families": [],
            "highlights": [],
            "samples": [],
            "batches": [],
            "row_count": len(rows),
            "ai_boundary": dict(_JOINT_AI_BOUNDARY),
        }

    family_order = []
    for item in issue_rows:
        check = str(item.get("check") or "").strip().lower()
        if "phi_c" in check:
            family = "phi_c inconsistency"
        elif "tm_gt" in check or "/tm_" in check:
            family = "Tm bidirectional gap"
        elif "l_consistency" in check:
            family = "L consistency unstable"
        else:
            family = "cross-tech issue"
        if family not in family_order:
            family_order.append(family)

    highlights = []
    for item in issue_rows[:3]:
        severity = str(item.get("severity") or "").strip().upper()
        sample = str(item.get("sample") or "").strip()
        batch = str(item.get("batch") or "").strip()
        check = str(item.get("check") or "").strip().rsplit("/", 1)[-1]
        message = str(item.get("message") or "").strip()
        highlight_parts = []
        if severity:
            highlight_parts.append(severity)
        sample_batch = " / ".join(part for part in [sample, batch] if part)
        if sample_batch:
            highlight_parts.append(sample_batch)
        if check:
            highlight_parts.append(check)
        if message:
            highlight_parts.append(message)
        highlights.append(" · ".join(highlight_parts))

    sample_names = []
    batch_labels = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        sample = str(row.get("sample") or "").strip()
        batch = str(row.get("batch") or "").strip()
        if sample and sample not in sample_names:
            sample_names.append(sample)
        if batch and batch not in batch_labels:
            batch_labels.append(batch)

    scope = "selected rows"
    if len(sample_names) == 1:
        scope = sample_names[0]
    elif sample_names:
        scope = " / ".join(sample_names[:2])

    error_count = len([i for i in issue_rows if str(i.get("severity") or "").strip().upper() == "ERROR"])
    warning_count = len([i for i in issue_rows if str(i.get("severity") or "").strip().upper() == "WARN"])
    summary = f"Cross-tech consistency for {scope}: {error_count} errors, {warning_count} warnings"
    if family_order:
        summary += "; focus on " + ", ".join(family_order[:3])
    if highlights:
        summary += "; example " + highlights[0]

    return {
        "summary": summary,
        "scope": scope,
        "sample_count": len(sample_names) or len(rows),
        "batch_count": len(batch_labels),
        "issue_count": len(issue_rows),
        "warning_count": warning_count,
        "error_count": error_count,
        "issue_families": family_order[:3],
        "highlights": highlights,
        "samples": sample_names[:3],
        "batches": batch_labels[:3],
        "row_count": len(rows),
        "ai_boundary": dict(_JOINT_AI_BOUNDARY),
    }


def _joint_issue_count(joint_context: dict) -> int:
    try:
        return int(float(joint_context.get("issue_count") or 0))
    except (TypeError, ValueError):
        return 0


def _joint_family_labels(
    joint_context: dict,
    family_label_fn: Callable[[object], str],
    *,
    limit: int = 3,
) -> list[str]:
    issue_families = joint_context.get("issue_families") if isinstance(joint_context.get("issue_families"), list) else []
    family_labels = []
    for family in issue_families:
        label = str(family_label_fn(family) or "").strip()
        if label and label not in family_labels:
            family_labels.append(label)
        if len(family_labels) >= limit:
            break
    return family_labels


def joint_ai_reminder_parts(
    joint_context,
    *,
    family_label_fn: Callable[[object], str],
    separator: str = ", ",
) -> JointPromptParts | None:
    if not isinstance(joint_context, dict) or not joint_context:
        return None
    issue_count = _joint_issue_count(joint_context)
    family_labels = _joint_family_labels(joint_context, family_label_fn)
    if family_labels:
        return JointPromptParts("JOINT_REMINDER_FOCUS", (str(separator or ", ").join(family_labels),))
    if issue_count > 0:
        return JointPromptParts("JOINT_REMINDER_GENERIC")
    return None


def joint_compare_hint_parts(
    joint_context,
    *,
    family_label_fn: Callable[[object], str],
    separator: str = ", ",
) -> JointPromptParts | None:
    if not isinstance(joint_context, dict) or not joint_context:
        return None
    issue_count = _joint_issue_count(joint_context)
    if issue_count <= 0:
        return None
    family_labels = _joint_family_labels(joint_context, family_label_fn)
    if family_labels:
        return JointPromptParts("JOINT_COMPARE_HINT_FAMILIES", (str(separator or ", ").join(family_labels),))
    return JointPromptParts("JOINT_COMPARE_HINT_GENERIC")


def history_context_snapshot(
    *,
    review_summary: str = "",
    work_memory_summary: str = "",
    comparison_summary: str = "",
    validation_summary: str = "",
    responsibility_boundary: str = "",
    tuning_context: dict | None = None,
    joint_context: dict | None = None,
) -> dict:
    tuning = tuning_context if isinstance(tuning_context, dict) else {}
    joint = joint_context if isinstance(joint_context, dict) else {}
    return {
        "review_summary": str(review_summary or "").strip(),
        "work_memory_summary": str(work_memory_summary or "").strip(),
        "comparison_summary": str(comparison_summary or "").strip(),
        "validation_summary": str(validation_summary or "").strip(),
        "responsibility_boundary": str(responsibility_boundary or "").strip(),
        "benchmark_summary": tuning.get("benchmark_summary") if isinstance(tuning.get("benchmark_summary"), dict) else {},
        "benchmark_text": str(tuning.get("benchmark_text") or "").strip(),
        "tuning_goal": str(tuning.get("tuning_goal") or "").strip(),
        "tuning_goal_label": str(tuning.get("tuning_goal_label") or "").strip(),
        "stop_reason": str(tuning.get("stop_reason") or "").strip(),
        "remaining_risks": str(tuning.get("remaining_risks") or "").strip(),
        "next_goal": str(tuning.get("next_goal") or "").strip(),
        "tuning_context": tuning,
        "joint_ai_context": joint,
        "joint_summary": str(joint.get("summary") or "").strip(),
    }


def build_history_context_snapshot_from_window(window) -> dict:
    current = window._current_results_record()
    tuning_context = getattr(window, "_last_ai_tuning_context", {})
    if not isinstance(tuning_context, dict):
        tuning_context = {}
    joint_context = window._joint_ai_context()
    if not isinstance(joint_context, dict):
        joint_context = {}
    return history_context_snapshot(
        review_summary=window._result_review_summary(),
        work_memory_summary=window._work_memory_summary(),
        comparison_summary=window._result_comparison_summary(),
        validation_summary=window._history_validation_summary(current),
        responsibility_boundary=window._responsibility_boundary_summary(),
        tuning_context=tuning_context,
        joint_context=joint_context,
    )


def history_context_line_parts(
    record,
    *,
    validation_summary: str = "",
    origin_label: str = "",
    boundary_text: str = "",
    chain_summary_fn: Callable[[dict], str] | None = None,
) -> list[HistoryContextLine]:
    if not isinstance(record, dict):
        return []

    summary = record.get("results_summary") if isinstance(record.get("results_summary"), dict) else {}
    if not isinstance(summary, dict):
        summary = {}

    snapshot = summary.get("history_context") if isinstance(summary.get("history_context"), dict) else {}
    if not isinstance(snapshot, dict):
        snapshot = {}

    current_lines = [
        HistoryContextLine("plain", str(snapshot.get("review_summary") or "").strip()),
        HistoryContextLine("plain", str(snapshot.get("comparison_summary") or "").strip()),
        HistoryContextLine("plain", str(snapshot.get("validation_summary") or "").strip()),
        HistoryContextLine("plain", str(snapshot.get("benchmark_text") or "").strip()),
        HistoryContextLine("plain", str(snapshot.get("work_memory_summary") or "").strip()),
        HistoryContextLine("plain", str(snapshot.get("joint_summary") or "").strip()),
        HistoryContextLine("plain", str(snapshot.get("responsibility_boundary") or "").strip()),
    ]
    tuning_context = snapshot.get("tuning_context") if isinstance(snapshot.get("tuning_context"), dict) else {}
    if tuning_context and chain_summary_fn is not None:
        chain_text = str(chain_summary_fn(tuning_context) or "").strip()
        if chain_text:
            current_lines.append(HistoryContextLine("review_chain", chain_text))
    current_lines = [line for line in current_lines if line.text]
    if current_lines:
        return current_lines

    fallback_lines = [
        HistoryContextLine("plain", str(validation_summary or "").strip()),
        HistoryContextLine("plain", str(origin_label or "").strip()),
    ]
    summary_origin = history_result_origin(record)
    if summary_origin == "controlled_optimization_rerun" or bool(summary.get("ai_tuned")):
        chain_text = ""
        if chain_summary_fn is not None:
            tuning_context = snapshot.get("tuning_context") if isinstance(snapshot.get("tuning_context"), dict) else {}
            chain_text = str(chain_summary_fn(tuning_context) or "").strip()
        if not chain_text:
            chain_text = str(origin_label or summary_origin or "").strip()
        if chain_text:
            fallback_lines.append(HistoryContextLine("review_chain", chain_text))

    existing_text = {line.text for line in fallback_lines if line.text}
    boundary = str(boundary_text or "").strip()
    if boundary and boundary not in existing_text:
        fallback_lines.append(HistoryContextLine("plain", boundary))
    return [line for line in fallback_lines if line.text]


def history_summary_lines(
    record,
    *,
    technique_text_fn: Callable[[str], str],
    context_text_fn: Callable[[dict], str],
    timestamp_text_fn: Callable[[object], str],
    metrics_text_fn: Callable[[dict], str],
    context_lines_fn: Callable[[dict], list[str]],
) -> list[str]:
    if not isinstance(record, dict):
        return []

    technique = str(technique_text_fn(str(record.get("technique") or "")) or "").strip()
    context = str(context_text_fn(record) or "").strip()
    created = str(timestamp_text_fn(record.get("created_at")) or "").strip()
    metrics = str(metrics_text_fn(record) or "").strip()

    lines = [part for part in [technique, context, created] if part]
    for part in context_lines_fn(record):
        if part and part not in lines:
            lines.append(part)
    if metrics and metrics not in lines:
        lines.append(metrics)
    return lines


def history_has_available_source(record) -> bool:
    if not isinstance(record, dict):
        return False
    summary = record.get("results_summary")
    if not isinstance(summary, dict):
        return True
    data_file = str(summary.get("data_file") or "").strip()
    if not data_file:
        return True
    return Path(data_file).exists()


def flatten_params(params, prefix=""):
    items = []
    if not isinstance(params, dict):
        return [(str(prefix) if prefix else "value", str(params))]

    for key, value in params.items():
        if key.startswith("_") or key == "batch_frames":
            continue
        full_key = f"{prefix}.{key}" if prefix else key

        if isinstance(value, dict) and any(isinstance(item, (int, float)) for item in value.values()):
            for child_key, child_value in value.items():
                if isinstance(child_value, (int, float, str, bool)):
                    items.append((f"{full_key}.{child_key}", child_value))
                elif isinstance(child_value, (list, tuple)) and len(child_value) <= 5:
                    items.append((f"{full_key}.{child_key}", str(child_value)))
            continue

        if isinstance(value, (list, tuple)):
            if len(value) == 0:
                items.append((full_key, "[]"))
            elif all(
                isinstance(item, (list, tuple))
                and len(item) == 2
                and isinstance(item[0], (int, float))
                and isinstance(item[1], (int, float))
                for item in value
            ):
                items.append(
                    (
                        full_key,
                        ", ".join(f"{item[0]:.1f}:{item[1]:.2f}" for item in value[:8])
                        + ("..." if len(value) > 8 else ""),
                    )
                )
            elif len(value) <= 6 and all(isinstance(item, (int, float)) for item in value):
                items.append((full_key, ", ".join(f"{item:.2f}" for item in value)))
            else:
                items.append((full_key, f"[{len(value)} items]"))
        elif isinstance(value, (int, float, str, bool)):
            items.append((full_key, value))
        elif isinstance(value, dict):
            items.extend(flatten_params(value, full_key))
        else:
            items.append((full_key, str(value)))
    return items


def find_analysis_evidence(node, *, max_depth: int = 5) -> dict:
    seen = set()
    stack = [(node, 0)]
    while stack:
        current, depth = stack.pop()
        if depth > max_depth or not isinstance(current, dict):
            continue
        marker = id(current)
        if marker in seen:
            continue
        seen.add(marker)

        evidence = current.get("analysis_evidence")
        if isinstance(evidence, dict) and evidence:
            return evidence

        if depth >= max_depth:
            continue

        for key in ("results_summary", "result"):
            child = current.get(key)
            if isinstance(child, dict):
                stack.append((child, depth + 1))

        for value in current.values():
            if isinstance(value, dict):
                stack.append((value, depth + 1))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        stack.append((item, depth + 1))
    return {}


def history_record_analysis_evidence(record) -> dict:
    evidence = find_analysis_evidence(record)
    if not isinstance(evidence, dict) or not evidence:
        return {}
    submodule = str(record.get("submodule") or "").strip().lower() if isinstance(record, dict) else ""
    technique = str(record.get("technique") or "").strip().lower() if isinstance(record, dict) else ""
    if technique != "waxs" and submodule != "waxs.temperature":
        return evidence

    feature = evidence.get("feature_evidence") if isinstance(evidence.get("feature_evidence"), dict) else {}
    if not isinstance(feature, dict):
        feature = {}

    normalized_feature = dict(feature)
    sequence = dict(normalized_feature.get("sequence_evidence")) if isinstance(normalized_feature.get("sequence_evidence"), dict) else {}
    peak_family = dict(normalized_feature.get("peak_family_evidence")) if isinstance(normalized_feature.get("peak_family_evidence"), dict) else {}
    trend = dict(
        normalized_feature.get("crystallinity_trend_evidence")
        if isinstance(normalized_feature.get("crystallinity_trend_evidence"), dict)
        else normalized_feature.get("trend_evidence")
        if isinstance(normalized_feature.get("trend_evidence"), dict)
        else {}
    )
    scherrer_trend = dict(normalized_feature.get("scherrer_trend_evidence")) if isinstance(normalized_feature.get("scherrer_trend_evidence"), dict) else {}
    transition = dict(normalized_feature.get("transition_evidence")) if isinstance(normalized_feature.get("transition_evidence"), dict) else {}

    for key in ("temperature_axis_confidence",):
        value = evidence.get(key)
        if value is not None and key not in sequence:
            sequence[key] = value
    for key in ("peak_family_continuity_score",):
        value = evidence.get(key)
        if value is not None and key not in peak_family:
            peak_family[key] = value
    for key in ("Xc_trend_support_score",):
        value = evidence.get(key)
        if value is not None and key not in trend:
            trend[key] = value
    for key in ("D_trend_support_score", "D_trend_monotonicity", "D_support_peak_count", "instrument_broadening_present"):
        value = evidence.get(key)
        if value is not None and key not in scherrer_trend:
            scherrer_trend[key] = value
    for key in ("transition_support_score", "transition_candidate_count"):
        value = evidence.get(key)
        if value is not None and key not in transition:
            transition[key] = value

    if sequence:
        normalized_feature["sequence_evidence"] = sequence
    if peak_family:
        normalized_feature["peak_family_evidence"] = peak_family
    if trend:
        normalized_feature["crystallinity_trend_evidence"] = trend
        normalized_feature.setdefault("trend_evidence", trend)
    if scherrer_trend:
        normalized_feature["scherrer_trend_evidence"] = scherrer_trend
    if transition:
        normalized_feature["transition_evidence"] = transition

    normalized = dict(evidence)
    normalized["feature_evidence"] = normalized_feature
    return normalized


def history_result_metrics(record) -> dict[str, str]:
    summary = record.get("results_summary") if isinstance(record, dict) else {}
    if not isinstance(summary, dict):
        summary = {}

    payload = summary.get("result") if isinstance(summary.get("result"), dict) else {}
    candidate = dict(payload.get("parameters") if isinstance(payload.get("parameters"), dict) else {})
    evidence = history_record_analysis_evidence(record)
    record_params = record.get("parameters") if isinstance(record, dict) and isinstance(record.get("parameters"), dict) else {}
    if isinstance(record_params, dict) and record_params:
        for key, value in flatten_params(record_params):
            if key not in candidate:
                candidate[key] = value
    for key, value in summary.items():
        if key in SUMMARY_METRIC_KEYS_TO_SKIP or key in candidate:
            continue
        if isinstance(value, (dict, list, tuple, set)):
            continue
        candidate[key] = value
    if not candidate:
        candidate = {
            key: value
            for key, value in summary.items()
            if key not in SUMMARY_METRIC_KEYS_TO_SKIP and not isinstance(value, (dict, list, tuple, set))
        }

    technique = str(record.get("technique") or "").strip().lower() if isinstance(record, dict) else ""
    if isinstance(evidence, dict) and evidence and technique == "waxs":
        _merge_waxs_evidence_metrics(candidate, evidence)
    elif isinstance(evidence, dict) and evidence and technique == "saxs":
        _merge_saxs_evidence_metrics(candidate, evidence)

    for canonical, legacy in (
        ("invariant_Q_rel_mean", "Q_star_rel_mean"),
        ("invariant_Q_rel_span", "Q_star_rel_span"),
    ):
        if canonical not in candidate and legacy in candidate:
            candidate[canonical] = candidate[legacy]
        candidate.pop(legacy, None)

    candidate = {key: value for key, value in candidate.items() if key not in VALIDATION_KEYS}
    rows = {}
    for key, value in flatten_params(candidate):
        rows[str(key)] = "" if value is None else str(value)
    return rows


def _merge_waxs_evidence_metrics(candidate: dict, evidence: dict) -> None:
    for key in (
        "n_peaks",
        "Xc_pct",
        "D_Scherrer_nm",
        "peak_support_score",
        "background_stability_score",
        "phase_support_score",
        "size_support_score",
        "waxs_support_score",
    ):
        value = evidence.get(key)
        if value is not None and key not in candidate:
            candidate[key] = value
    feature_evidence = evidence.get("feature_evidence", {})
    if not isinstance(feature_evidence, dict):
        feature_evidence = {}
    sequence_evidence = feature_evidence.get("sequence_evidence", {})
    if not isinstance(sequence_evidence, dict):
        sequence_evidence = {}
    peak_family_evidence = feature_evidence.get("peak_family_evidence", {})
    if not isinstance(peak_family_evidence, dict):
        peak_family_evidence = {}
    trend_evidence = feature_evidence.get("trend_evidence", feature_evidence.get("crystallinity_trend_evidence", {}))
    if not isinstance(trend_evidence, dict):
        trend_evidence = {}
    scherrer_trend_evidence = feature_evidence.get("scherrer_trend_evidence", {})
    if not isinstance(scherrer_trend_evidence, dict):
        scherrer_trend_evidence = {}
    transition_evidence = feature_evidence.get("transition_evidence", {})
    if not isinstance(transition_evidence, dict):
        transition_evidence = {}
    for key, source in (
        ("temperature_axis_confidence", sequence_evidence),
        ("peak_family_continuity_score", peak_family_evidence),
        ("Xc_trend_support_score", trend_evidence),
        ("D_trend_support_score", scherrer_trend_evidence),
        ("transition_support_score", transition_evidence),
    ):
        value = source.get(key) if isinstance(source, dict) else None
        if value is not None and key not in candidate:
            candidate[key] = value


def _merge_saxs_evidence_metrics(candidate: dict, evidence: dict) -> None:
    feature_evidence = evidence.get("feature_evidence", {})
    if not isinstance(feature_evidence, dict):
        feature_evidence = {}
    condition_evidence = feature_evidence.get("condition_evidence", {})
    if not isinstance(condition_evidence, dict):
        condition_evidence = {}
    strain_structure_evidence = feature_evidence.get("strain_structure_evidence", {})
    if not isinstance(strain_structure_evidence, dict):
        strain_structure_evidence = {}
    if condition_evidence.get("condition_label") == "strain" or strain_structure_evidence:
        for canonical, legacy in (
            ("invariant_Q_rel_mean", "Q_star_rel_mean"),
            ("invariant_Q_rel_span", "Q_star_rel_span"),
        ):
            value = strain_structure_evidence.get(
                canonical,
                strain_structure_evidence.get(legacy),
            )
            if value is not None and canonical not in candidate:
                candidate[canonical] = value
            if legacy in candidate:
                candidate.pop(legacy)
        for key in (
            "strain_axis_confidence",
            "strain_monotonic",
            "strain_missing_count",
            "strain_duplicate_count",
            "strain_min_pct",
            "strain_max_pct",
        ):
            value = condition_evidence.get(key)
            if value is None and key not in candidate:
                value = evidence.get(key)
            if value is not None and key not in candidate:
                candidate[key] = value
        for key in (
            "phi_void_mean",
            "phi_void_span",
            "void_detected_frames",
            "f_Herman_mean",
            "f_Herman_span",
            "porod_slope_mean",
            "porod_slope_span",
        ):
            value = strain_structure_evidence.get(key)
            if value is not None and key not in candidate:
                candidate[key] = value
