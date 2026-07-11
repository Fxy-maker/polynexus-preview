"""Pure text helpers used by the results review service."""

from __future__ import annotations

from typing import Any, Callable, Iterable

from .analysis_history_service import (
    ai_tuning_constraint_summary_parts,
    ai_tuning_stability_summary_parts,
    batch_fallback_summary_parts,
    gui_coerce_summary_float,
    gui_display_text,
    gui_display_text_value,
    gui_format_score_value,
    result_review_metric_summary,
)
from .i18n import tr
from .window_text_helpers import ir_conclusion_state_display as _ir_conclusion_state_display


def evidence_symptom_names(analysis_evidence) -> set[str]:
    symptoms = analysis_evidence.get("symptoms", []) if isinstance(analysis_evidence, dict) else []
    names: set[str] = set()
    if not isinstance(symptoms, list):
        return names
    for item in symptoms:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "") or "").strip()
        if name:
            names.add(name)
    return names


def ai_tuning_report_summary_text(report: dict[str, Any] | None) -> str:
    report = report if isinstance(report, dict) else {}
    rounds = report.get("rounds", 0)
    best_r2 = report.get("best_r_squared", "")
    improvement = report.get("improvement") if isinstance(report.get("improvement"), dict) else {}
    delta = improvement.get("r_squared_abs", "")
    reason = str(report.get("convergence_reason", "") or "").strip()
    if reason:
        return tr("AI_TUNING_REPORT_SUMMARY_WITH_REASON", rounds, best_r2, delta, reason)
    return tr("AI_TUNING_REPORT_SUMMARY", rounds, best_r2, delta)


def ai_tuning_report_decision_text(report: dict[str, Any] | None) -> str:
    report = report if isinstance(report, dict) else {}
    history = report.get("history") if isinstance(report.get("history"), list) else []
    accepted = 0
    rolled_back = 0
    rollback_reasons: list[str] = []
    for item in history:
        if not isinstance(item, dict):
            continue
        round_num = int(item.get("round_num", item.get("round_idx", 0)) or 0)
        if round_num <= 0:
            continue
        if bool(item.get("accepted", True)):
            accepted += 1
        else:
            rolled_back += 1
            advice = item.get("llm_advice") if isinstance(item.get("llm_advice"), dict) else {}
            reason = str(advice.get("rollback_reason", "") or "").strip()
            if reason:
                rollback_reasons.append(reason)

    if rolled_back and rollback_reasons:
        return tr(
            "AI_TUNING_REPORT_DECISION_WITH_ROLLBACK",
            accepted,
            rolled_back,
            rollback_reasons[0],
        )
    return tr("AI_TUNING_REPORT_DECISION", accepted, rolled_back)


def ai_tuning_report_benchmark_text(
    report: dict[str, Any] | None,
    *,
    delta_text_fn: Callable[[Any], str],
    rate_text_fn: Callable[[Any], str],
) -> str:
    report = report if isinstance(report, dict) else {}
    benchmark = report.get("benchmark_summary")
    if not isinstance(benchmark, dict) or not benchmark:
        return ""

    return tr(
        "AI_TUNING_REPORT_BENCHMARK",
        delta_text_fn(benchmark.get("average_objective_delta")),
        rate_text_fn(benchmark.get("acceptance_rate")),
        rate_text_fn(benchmark.get("rejection_rate")),
        rate_text_fn(benchmark.get("constraint_hit_rate")),
        rate_text_fn(benchmark.get("symptom_fix_rate")),
    )


def result_review_ir_temperature_2d_user_summary_lines(analysis_evidence: dict[str, Any] | None) -> list[str]:
    feature = analysis_evidence.get("feature_evidence", {}) if isinstance(analysis_evidence, dict) else {}
    if not isinstance(feature, dict):
        return []
    temp2d = feature.get("temperature_2d_evidence", {}) if isinstance(feature.get("temperature_2d_evidence"), dict) else {}
    transform = feature.get("transform_evidence", {}) if isinstance(feature.get("transform_evidence"), dict) else {}
    single_frame = feature.get("single_frame_evidence", {}) if isinstance(feature.get("single_frame_evidence"), dict) else {}
    sequence = feature.get("sequence_evidence", {}) if isinstance(feature.get("sequence_evidence"), dict) else {}
    if not isinstance(temp2d, dict) or not temp2d:
        return []

    lines: list[str] = []
    sequence_ready = bool(feature.get("sequence_axis_ready", temp2d.get("sequence_axis_score", 0.0) >= 0.75))
    if sequence_ready:
        lines.append(tr("RESULTS_REVIEW_IR_SEQUENCE_STATUS", tr("IR_SEQUENCE_RESOLVED")))
    else:
        lines.append(tr("RESULTS_REVIEW_IR_SEQUENCE_STATUS", tr("IR_SEQUENCE_UNRESOLVED")))

    paper_ready = bool(temp2d.get("paper_conclusion_ready"))
    interpretation_ready = bool(temp2d.get("interpretation_ready"))
    if paper_ready:
        lines.append(tr("RESULTS_REVIEW_IR_FIGURE_STATUS", tr("IR_FIGURE_PAPER_READY")))
    elif interpretation_ready:
        lines.append(tr("RESULTS_REVIEW_IR_FIGURE_STATUS", tr("IR_FIGURE_USABLE_PENDING")))
    else:
        lines.append(tr("RESULTS_REVIEW_IR_FIGURE_STATUS", tr("IR_FIGURE_DIAGNOSTIC_ONLY")))

    if interpretation_ready and bool(transform.get("noda_rule_interpretation_ready")):
        lines.append(tr("RESULTS_REVIEW_IR_INTERPRETATION_STATUS", tr("IR_INTERPRETATION_READY")))
    else:
        lines.append(tr("RESULTS_REVIEW_IR_INTERPRETATION_STATUS", tr("IR_INTERPRETATION_TENTATIVE")))

    if isinstance(single_frame, dict) and single_frame:
        low_ratio = single_frame.get("low_confidence_frame_ratio")
        assign_mean = single_frame.get("frame_assignment_confidence_mean")
        key_band_mean = single_frame.get("frame_key_band_support_mean")
        if low_ratio is not None or assign_mean is not None or key_band_mean is not None:
            try:
                low_text = f"{float(low_ratio):.2f}" if low_ratio is not None else tr("AI_TUNING_EMPTY_VALUE")
            except Exception:
                low_text = tr("AI_TUNING_EMPTY_VALUE")
            try:
                assign_text = f"{float(assign_mean):.2f}" if assign_mean is not None else tr("AI_TUNING_EMPTY_VALUE")
            except Exception:
                assign_text = tr("AI_TUNING_EMPTY_VALUE")
            try:
                key_text = f"{float(key_band_mean):.2f}" if key_band_mean is not None else tr("AI_TUNING_EMPTY_VALUE")
            except Exception:
                key_text = tr("AI_TUNING_EMPTY_VALUE")
            lines.append(
                tr(
                    "RESULTS_REVIEW_IR_FRAME_STATUS",
                    tr("IR_FRAME_STATUS_TEMPLATE", low_text, assign_text, key_text),
                )
            )

    if isinstance(sequence, dict):
        stage_counts = sequence.get("stage_counts")
        if isinstance(stage_counts, dict) and stage_counts:
            stage_bits = ", ".join(
                f"{key}={value}" for key, value in list(stage_counts.items())[:3]
            )
            lines.append(tr("RESULTS_REVIEW_IR_SEQUENCE_TRUST", stage_bits))

    return [line for line in lines if str(line).strip()]


def _batch_fallback_summary_text(analysis_evidence, *, symptom_names: Iterable[str]) -> str:
    parts = batch_fallback_summary_parts(
        analysis_evidence,
        symptom_names=symptom_names,
    )
    return " | ".join(tr(part.translation_key, *part.args) for part in parts)


def _empty_value_text() -> str:
    return tr("AI_TUNING_EMPTY_VALUE")


def _display_text(value) -> str:
    return gui_display_text(value, empty_text=_empty_value_text())


def _display_text_value(value) -> str:
    return gui_display_text_value(value, empty_text=_empty_value_text())


def _format_score_value(value, *, signed: bool = False) -> str:
    return gui_format_score_value(value, empty_text=_empty_value_text(), signed=signed)


def _ir_basis_label_text(value: str) -> str:
    key = str(value or "").strip().lower()
    mapping = {
        "peak_assignment": tr("IR_BASIS_PEAK_ASSIGNMENT"),
        "peak_detection": tr("IR_BASIS_PEAK_DETECTION"),
    }
    return mapping.get(key, tr("IR_BASIS_UNKNOWN"))


def _dsc_conclusion_state_display(structure: dict[str, Any] | None) -> str:
    structure = structure if isinstance(structure, dict) else {}
    if structure.get("paper_conclusion_ready") is True:
        return tr("DSC_CONCLUSION_READY")
    if bool(structure.get("paper_conclusion_candidate")):
        return tr("DSC_CONCLUSION_CANDIDATE")
    if structure.get("paper_conclusion_ready") is False:
        return tr("DSC_CONCLUSION_PENDING")
    return _empty_value_text()


def _constraint_summary_text(analysis_evidence) -> str:
    parts = ai_tuning_constraint_summary_parts(
        analysis_evidence,
        empty_text=_empty_value_text(),
        display_text_fn=_display_text_value,
    )
    if parts is None:
        return _empty_value_text()
    base = tr("AI_TUNING_CONSTRAINT_SUMMARY", parts[0], parts[1], parts[2], parts[3])
    if parts[4]:
        return f"{base}; {tr('AI_TUNING_CONSTRAINT_NAMES', parts[4])}"
    return base


def _stability_summary_text(analysis_evidence) -> str:
    parts = ai_tuning_stability_summary_parts(
        analysis_evidence,
        empty_text=_empty_value_text(),
        format_score_fn=_format_score_value,
    )
    if parts is None:
        return _empty_value_text()
    return tr("AI_TUNING_STABILITY_SUMMARY", *parts)


def result_review_constraint_summary_text(analysis_evidence) -> str:
    return _constraint_summary_text(analysis_evidence)


def result_review_stability_summary_text(analysis_evidence) -> str:
    return _stability_summary_text(analysis_evidence)


def _waxs_temperature_trend_evidence(analysis_evidence=None) -> dict:
    evidence = analysis_evidence if isinstance(analysis_evidence, dict) else {}
    feature = evidence.get("feature_evidence", {})
    if not isinstance(feature, dict):
        return {}
    trend = feature.get("scherrer_trend_evidence")
    return trend if isinstance(trend, dict) else {}


def _waxs_support_snapshot(analysis_evidence=None) -> dict[str, float | None]:
    evidence = analysis_evidence if isinstance(analysis_evidence, dict) else {}
    feature = evidence.get("feature_evidence", {})
    if not isinstance(feature, dict):
        feature = {}
    snapshot: dict[str, float | None] = {}
    for key in (
        "peak_support_score",
        "background_stability_score",
        "phase_support_score",
        "size_support_score",
        "waxs_support_score",
    ):
        try:
            value = float(feature.get(key))
        except (TypeError, ValueError):
            value = None
        snapshot[key] = value
    return snapshot


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


def _waxs_support_summary_text(analysis_evidence=None, *, trend_evidence=None) -> str:
    evidence = analysis_evidence if isinstance(analysis_evidence, dict) else {}
    snapshot = _waxs_support_snapshot(evidence)
    trend = trend_evidence if isinstance(trend_evidence, dict) else {}
    parts: list[str] = []
    for label, key in (
        ("peak", "peak_support_score"),
        ("background", "background_stability_score"),
        ("phase", "phase_support_score"),
        ("size", "size_support_score"),
    ):
        value = snapshot.get(key)
        if value is not None:
            parts.append(f"{label}={value:.3f}")
    trend_value = gui_coerce_summary_float(trend.get("D_trend_support_score"))
    if trend_value is not None:
        parts.append(f"D_trend={trend_value:.3f}")
    waxs_support_value = gui_coerce_summary_float(evidence.get("waxs_support_score"))
    if waxs_support_value is not None:
        parts.append(f"waxs_support_score={waxs_support_value:.3f}")
    return " | ".join(parts)


def result_review_waxs_core_text(current_metrics=None) -> str:
    return _waxs_core_summary_text(current_metrics)


def result_review_waxs_support_text(analysis_evidence=None) -> str:
    evidence = analysis_evidence if isinstance(analysis_evidence, dict) else {}
    feature = evidence.get("feature_evidence", {})
    if not isinstance(feature, dict):
        feature = {}
    trend = feature.get("scherrer_trend_evidence", {})
    if not isinstance(trend, dict):
        trend = {}
    return _waxs_support_summary_text(evidence, trend_evidence=trend)


def _waxs_structure_evidence(analysis_evidence=None) -> dict:
    analysis_evidence = analysis_evidence if isinstance(analysis_evidence, dict) else {}
    if not isinstance(analysis_evidence, dict):
        return {}
    structure = analysis_evidence.get("structure_evidence")
    return structure if isinstance(structure, dict) else {}


def result_review_summary_text(snapshot: dict[str, Any] | None) -> str:
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    current = snapshot.get("current") if isinstance(snapshot.get("current"), dict) else {}
    if not current:
        return ""

    technique = str(snapshot.get("technique") or "").strip().lower()
    parts: list[str] = []

    measured_text = str(snapshot.get("measured_text") or "").strip()
    if measured_text:
        parts.append(tr("RESULTS_REVIEW_MEASURED", measured_text))

    origin_label = str(snapshot.get("origin_label") or "").strip()
    if origin_label:
        parts.append(origin_label)

    confirmed_label = str(snapshot.get("confirmed_label") or "").strip()
    if confirmed_label:
        parts.append(confirmed_label)

    summary = current.get("results_summary") if isinstance(current.get("results_summary"), dict) else {}
    if not isinstance(summary, dict):
        summary = {}
    validation_summary = str(
        snapshot.get("validation_summary")
        or summary.get("validation_summary")
        or current.get("validation_summary")
        or ""
    ).strip()
    if validation_summary:
        parts.append(validation_summary)

    comparison_summary = str(snapshot.get("comparison_summary") or "").strip()
    if comparison_summary:
        parts.append(comparison_summary)

    current_metrics = snapshot.get("current_metrics") if isinstance(snapshot.get("current_metrics"), dict) else {}
    metric_summary = str(snapshot.get("metric_summary") or "").strip()
    if not metric_summary and isinstance(current_metrics, dict) and current_metrics:
        metric_summary = result_review_metric_summary(
            current_metrics,
            technique=technique,
            strain_active=bool(snapshot.get("strain_active")) if technique == "saxs" else False,
        )
    if metric_summary:
        parts.append(tr("RESULTS_REVIEW_METRICS", metric_summary))

    if technique == "ir":
        ir_lines = snapshot.get("ir_lines") if isinstance(snapshot.get("ir_lines"), list) else []
        for line in ir_lines:
            text = str(line or "").strip()
            if text:
                parts.append(text)
        ir_support_text = str(snapshot.get("ir_support_text") or "").strip()
        if ir_support_text:
            parts.append(ir_support_text)

    if technique == "waxs":
        waxs_core_text = str(snapshot.get("waxs_core_text") or "").strip()
        if waxs_core_text:
            parts.append(tr("RESULTS_REVIEW_WAXS_CORE", waxs_core_text))
        waxs_support_text = str(snapshot.get("waxs_support_text") or "").strip()
        if waxs_support_text:
            parts.append(tr("RESULTS_REVIEW_WAXS_SUPPORT", waxs_support_text))
        waxs_semantic_lines = snapshot.get("waxs_semantic_lines") if isinstance(snapshot.get("waxs_semantic_lines"), list) else []
        for line in waxs_semantic_lines:
            text = str(line or "").strip()
            if text:
                parts.append(text)

    if technique == "saxs":
        saxs_semantic_lines = snapshot.get("saxs_semantic_lines") if isinstance(snapshot.get("saxs_semantic_lines"), list) else []
        for line in saxs_semantic_lines:
            text = str(line or "").strip()
            if text:
                parts.append(text)
        saxs_strain_text = str(snapshot.get("saxs_strain_text") or "").strip()
        if saxs_strain_text:
            parts.append(tr("RESULTS_REVIEW_SAXS_STRAIN", saxs_strain_text))
        saxs_method_bits = snapshot.get("saxs_method_bits") if isinstance(snapshot.get("saxs_method_bits"), list) else []
        if saxs_method_bits:
            parts.append(tr("RESULTS_REVIEW_SAXS_METHOD", ", ".join(saxs_method_bits[:4])))

    fallback_text = str(snapshot.get("fallback_text") or "").strip()
    if fallback_text:
        parts.append(fallback_text)

    optimization_parts = snapshot.get("optimization_parts")
    if isinstance(optimization_parts, dict) and optimization_parts:
        optimization_text = str(optimization_parts.get("summary") or "").strip()
        if optimization_text:
            parts.append(optimization_text)

    chain_text = str(snapshot.get("chain_text") or "").strip()
    if chain_text:
        parts.append(chain_text)

    joint_summary = str(snapshot.get("joint_summary") or "").strip()
    if joint_summary:
        parts.append(joint_summary)

    joint_reminder_text = str(snapshot.get("joint_reminder_text") or "").strip()
    if joint_reminder_text:
        parts.append(joint_reminder_text)

    responsibility_boundary = str(snapshot.get("responsibility_boundary") or "").strip()
    if responsibility_boundary:
        parts.append(responsibility_boundary)

    return " | ".join(part for part in parts if str(part).strip())
