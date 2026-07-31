"""Helpers for composing the results review panel text."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .analysis_history_service import (
    ControlledOptimizationReviewParts,
    controlled_optimization_review_parts,
    ai_tuning_chain_summary,
    gui_coerce_summary_float,
    gui_display_text_value,
    has_condition_axis_risk,
    has_fallback_conflict_risk,
    quality_flag_summary_text,
    results_has_critical_risk,
    results_next_step_translation_key,
    joint_ai_reminder_parts,
    joint_compare_hint_parts,
    saxs_lc_status_summary_parts,
    saxs_lc_status_text,
    saxs_reason_text,
    saxs_structure_status_snapshot,
    saxs_strain_next_step_text,
    saxs_strain_risk_summary_text,
    saxs_strain_summary_text,
    result_review_metric_summary,
)
from .i18n import get_language, tr, tr_for_language
from .window_text_helpers import ir_conclusion_state_display as _ir_conclusion_state_display
from .results_review_text_helpers import (
    _batch_fallback_summary_text,
    _constraint_summary_text,
    _dsc_conclusion_state_display,
    _display_text,
    _empty_value_text,
    _format_score_value,
    _ir_basis_label_text,
    _stability_summary_text,
    _waxs_temperature_trend_evidence,
    ai_tuning_report_benchmark_text,
    ai_tuning_report_decision_text,
    ai_tuning_report_summary_text,
    evidence_symptom_names as _evidence_symptom_names,
    result_review_constraint_summary_text,
    result_review_ir_temperature_2d_user_summary_lines,
    result_review_stability_summary_text,
)

__all__ = [
    "ai_tuning_report_benchmark_text",
    "ai_tuning_report_decision_text",
    "ai_tuning_report_summary_text",
    "result_review_constraint_summary_text",
    "result_review_stability_summary_text",
]


def _nmr_vendor_axis_text(declaration: Any) -> str:
    """Format the vendor declaration compactly enough for the review panel."""
    if not isinstance(declaration, dict):
        return ""
    domain = str(declaration.get("domain", "") or "").strip()
    origin_field = str(declaration.get("origin_field", "") or "").strip()
    sweep_field = str(declaration.get("sweep_field", "") or "").strip()
    points_field = str(declaration.get("points_field", "") or "").strip()
    units = str(declaration.get("units", "") or "").strip()
    if not domain or not origin_field or not sweep_field or not points_field:
        return ""

    def compact(value: Any) -> str:
        if isinstance(value, bool):
            return str(value).lower()
        if isinstance(value, (int, float)):
            return f"{value:g}"
        return str(value or "").strip()

    status = str(declaration.get("status", "") or "").strip()
    if status == "declared_not_applied":
        status = "not applied"
    dimension = f"{declaration.get('dimension', '')}/{declaration.get('dimension_index', '')}"
    return (
        f"{dimension} | {domain} | origin {origin_field}={compact(declaration.get('origin'))} {units} | "
        f"sweep {sweep_field}={compact(declaration.get('sweep'))} {units} | "
        f"points {points_field}={compact(declaration.get('points'))} | {status}"
    )


def _dsc_support_block_text(analysis_evidence: dict[str, Any] | None, *, include_measurement: bool) -> str:
    feature = analysis_evidence.get("feature_evidence", {}) if isinstance(analysis_evidence, dict) else {}
    if not isinstance(feature, dict):
        feature = {}
    thermal = feature.get("thermal_event_evidence", {}) if isinstance(feature.get("thermal_event_evidence"), dict) else {}
    event_support = feature.get("event_support_evidence", {}) if isinstance(feature.get("event_support_evidence"), dict) else {}
    baseline = feature.get("baseline_evidence", {}) if isinstance(feature.get("baseline_evidence"), dict) else {}
    structure = feature.get("structure_evidence", {}) if isinstance(feature.get("structure_evidence"), dict) else {}

    sections: list[str] = []

    if include_measurement:
        measured_bits: list[str] = []
        for key in ("Tg_C", "Tm_peak_C", "Tcc_peak_C", "DHm_Jg", "DHc_Jg", "DHcc_Jg", "Xc_pct"):
            value = thermal.get(key)
            if value is None:
                value = feature.get(key)
            text = _display_text(value)
            if text != _empty_value_text():
                measured_bits.append(f"{key}={text}")
        if measured_bits:
            sections.append(tr("RESULTS_REVIEW_DSC_MEASURED", ", ".join(measured_bits[:5])))

    support_bits: list[str] = []
    for label, key in (
        ("event", "event_support_score"),
        ("baseline", "baseline_stability_score"),
        ("thermo", "thermodynamic_consistency_score"),
        ("structure", "structure_support_score"),
        ("fraction", "supported_event_fraction"),
        ("scan", "scan_r_squared_median"),
    ):
        value = event_support.get(key)
        if value is None:
            value = feature.get(key)
        if value is None:
            continue
        if key == "supported_event_fraction":
            support_bits.append(f"{label}={_display_text(value)}")
        else:
            support_bits.append(f"{label}={_format_score_value(value)}")
    if support_bits:
        sections.append(tr("RESULTS_REVIEW_DSC_SUPPORT", " | ".join(support_bits[:5])))

    conclusion_state = _dsc_conclusion_state_display(structure)
    if conclusion_state != _empty_value_text():
        sections.append(tr("RESULTS_REVIEW_DSC_CONCLUSION_STATE", conclusion_state))

    context_bits: list[str] = []
    if structure.get("paper_conclusion_candidate") is not None:
        context_bits.append(f"paper_candidate={_display_text(structure.get('paper_conclusion_candidate'))}")
    if structure.get("paper_conclusion_ready") is not None:
        context_bits.append(f"paper_ready={_display_text(structure.get('paper_conclusion_ready'))}")
    for label, source, key in (
        ("scan", thermal, "scan_mode"),
        ("exo", thermal, "exo_up"),
        ("baseline", baseline, "baseline_corr"),
        ("residual", baseline, "residual_type"),
    ):
        value = source.get(key) if isinstance(source, dict) else None
        if value is not None:
            context_bits.append(f"{label}={_display_text(value)}")
    if context_bits:
        sections.append(tr("RESULTS_REVIEW_DSC_RISK_DETAIL", " | ".join(context_bits[:4])))

    if not sections:
        return _empty_value_text()
    return " | ".join(sections[:4])


def result_review_dsc_support_block_text(
    analysis_evidence: dict[str, Any] | None,
    *,
    include_measurement: bool = False,
) -> str:
    return _dsc_support_block_text(
        analysis_evidence,
        include_measurement=include_measurement,
    )


def result_review_ir_support_block_text(
    analysis_evidence: dict[str, Any] | None,
    *,
    include_reference_summary: bool = False,
) -> str:
    feature = analysis_evidence.get("feature_evidence", {}) if isinstance(analysis_evidence, dict) else {}
    if not isinstance(feature, dict):
        feature = {}
    reference = feature.get("reference_evidence", {}) if isinstance(feature.get("reference_evidence"), dict) else {}
    assignment = feature.get("assignment_evidence", {}) if isinstance(feature.get("assignment_evidence"), dict) else {}
    structure = feature.get("structure_evidence", {}) if isinstance(feature.get("structure_evidence"), dict) else {}
    peak = feature.get("peak_evidence", {}) if isinstance(feature.get("peak_evidence"), dict) else {}
    baseline = feature.get("baseline_evidence", {}) if isinstance(feature.get("baseline_evidence"), dict) else {}
    mapping = feature.get("mapping_evidence", {}) if isinstance(feature.get("mapping_evidence"), dict) else {}

    sections: list[str] = []

    if mapping:
        semantics = mapping.get("mapping_semantics") if isinstance(mapping.get("mapping_semantics"), dict) else {}
        axes = semantics.get("spatial_axes") if isinstance(semantics.get("spatial_axes"), dict) else {}
        x_axis = axes.get("x") if isinstance(axes.get("x"), dict) else {}
        y_axis = axes.get("y") if isinstance(axes.get("y"), dict) else {}
        origin = semantics.get("origin") if isinstance(semantics.get("origin"), dict) else {}
        roi = semantics.get("roi") if isinstance(semantics.get("roi"), dict) else {}
        serialization = semantics.get("serialization") if isinstance(semantics.get("serialization"), dict) else {}
        shape = mapping.get("map_shape") if isinstance(mapping.get("map_shape"), (list, tuple)) else []
        shape_text = "x".join(_display_text(value) for value in shape[:2]) if len(shape) >= 2 else "unknown"
        mapping_bits = [
            f"source={_display_text(mapping.get('source_id'))}",
            f"map={shape_text}",
            "x=" + "/".join(
                _display_text(x_axis.get(key)) for key in ("coordinate_role", "physical_axis")
            ) + f" ({_display_text(x_axis.get('unit'))})",
            "y=" + "/".join(
                _display_text(y_axis.get(key)) for key in ("coordinate_role", "physical_axis")
            ) + f" ({_display_text(y_axis.get('unit'))})",
            f"origin={_display_text(origin.get('kind'))} ({_display_text(origin.get('x'))}, {_display_text(origin.get('y'))})",
            f"roi={_display_text(roi.get('kind'))}",
            f"order={_display_text(serialization.get('order'))}",
            f"status={_display_text(semantics.get('status'))}",
        ]
        sections.append(tr("RESULTS_REVIEW_IR_MAPPING_PROVENANCE", " | ".join(mapping_bits)))

    detected_bits: list[str] = []
    if isinstance(peak, dict) and peak:
        for key in ("peak_count", "assigned_peak_count", "unassigned_peak_count"):
            value = peak.get(key)
            if value is not None:
                detected_bits.append(f"{key}={_display_text(value)}")
    if not detected_bits and isinstance(reference, dict):
        for key in ("band_count", "hit_count", "missing_count"):
            value = reference.get(key)
            if value is not None:
                detected_bits.append(f"{key}={_display_text(value)}")
    if detected_bits:
        sections.append(tr("RESULTS_REVIEW_IR_DETECTED", ", ".join(detected_bits[:3])))

    if include_reference_summary and isinstance(reference, dict) and reference:
        sections.append(
            tr(
                "RESULTS_REVIEW_IR_REFERENCE",
                _display_text(reference.get("band_count")),
                _display_text(reference.get("hit_count")),
                _display_text(reference.get("missing_count")),
            )
        )

    if isinstance(assignment, dict) and assignment.get("assignment_confidence") is not None:
        sections.append(tr("RESULTS_REVIEW_IR_ASSIGNMENT", _format_score_value(assignment.get("assignment_confidence"))))

    support_bits: list[str] = []
    if isinstance(assignment, dict):
        for label, key in (
            ("key", "key_band_support_score"),
            ("peak", "peak_coverage_score"),
            ("baseline", "baseline_stability_score"),
            ("total", "ir_support_score"),
        ):
            value = assignment.get(key)
            if value is None and isinstance(structure, dict):
                value = structure.get(key)
            if value is not None:
                support_bits.append(f"{label}={_format_score_value(value)}")
    if support_bits:
        sections.append(tr("RESULTS_REVIEW_IR_SUPPORT_DETAIL", " | ".join(support_bits[:4])))

    band_tracking = feature.get("band_tracking_evidence", {}) if isinstance(feature.get("band_tracking_evidence"), dict) else {}
    if isinstance(band_tracking, dict) and band_tracking:
        tracking_bits: list[str] = []
        for key in (
            "band_index_series_count",
            "band_index_transition_support_band_count",
            "band_index_transition_support_ratio",
            "band_index_transition_reproducible",
            "band_tracking_missing_key_band",
        ):
            value = band_tracking.get(key)
            if value is None:
                continue
            if isinstance(value, float):
                tracking_bits.append(f"{key}={_format_score_value(value)}")
            else:
                tracking_bits.append(f"{key}={_display_text(value)}")
        if tracking_bits:
            sections.append(tr("RESULTS_REVIEW_IR_BAND_TRACKING", " | ".join(tracking_bits[:5])))

    temp2d = feature.get("temperature_2d_evidence", {}) if isinstance(feature.get("temperature_2d_evidence"), dict) else {}
    if isinstance(temp2d, dict) and temp2d:
        trust_bits: list[str] = []
        for label, key in (
            ("sequence", "sequence_axis_score"),
            ("matrix", "matrix_quality_score"),
            ("cos", "cos_signal_score"),
            ("band", "band_tracking_score"),
        ):
            value = temp2d.get(key)
            if value is not None:
                trust_bits.append(f"{label}={_format_score_value(value)}")
        if trust_bits:
            sections.append(tr("RESULTS_REVIEW_IR_SEQUENCE_TRUST", " | ".join(trust_bits[:4])))

    basis = str(structure.get("classification_basis", "") or "").strip() if isinstance(structure, dict) else ""
    if basis:
        sections.append(tr("RESULTS_REVIEW_IR_BASIS", _ir_basis_label_text(basis)))
    if isinstance(structure, dict) and structure.get("characteristic_band_support_ok") is not None:
        support_text = tr("IR_SUPPORT_COMPLETE") if bool(structure.get("characteristic_band_support_ok")) else tr("IR_SUPPORT_INCOMPLETE")
        sections.append(tr("RESULTS_REVIEW_IR_SUPPORT", support_text))
    if isinstance(structure, dict) and structure.get("paper_conclusion_ready") is not None:
        sections.append(
            tr(
                "RESULTS_REVIEW_IR_CONCLUSION_STATE",
                _ir_conclusion_state_display(structure.get("paper_conclusion_ready")),
            )
        )
    if isinstance(temp2d, dict) and temp2d:
        matrix_value = temp2d.get("matrix_quality_score")
        cos_value = temp2d.get("cos_signal_score")
        transition_value = temp2d.get("paper_conclusion_ready")
        matrix_bits = []
        if matrix_value is not None:
            matrix_bits.append(f"matrix={_format_score_value(matrix_value)}")
        if cos_value is not None:
            matrix_bits.append(f"cos={_format_score_value(cos_value)}")
        if matrix_bits:
            sections.append(tr("RESULTS_REVIEW_IR_MATRIX_TRUST", " | ".join(matrix_bits[:3])))
        if transition_value is not None:
            sections.append(
                tr(
                    "RESULTS_REVIEW_IR_TRANSITION_TRUST",
                    _ir_conclusion_state_display(transition_value),
                )
            )

    risk_bits: list[str] = []
    if isinstance(reference, dict) and reference.get("missing_count") is not None:
        risk_bits.append(f"missing={_display_text(reference.get('missing_count'))}")
    if isinstance(baseline, dict):
        for key in ("baseline_method", "normalization_method"):
            value = baseline.get(key)
            if value:
                risk_bits.append(f"{key}={_display_text(value)}")
    if risk_bits:
        sections.append(tr("RESULTS_REVIEW_IR_RISK_DETAIL", " | ".join(risk_bits[:3])))

    if not sections:
        return _empty_value_text()
    return " | ".join(sections)


def result_review_analysis_evidence_card_text(
    analysis_evidence,
    *,
    technique: str,
    language: str = "en",
) -> str:
    if not isinstance(analysis_evidence, dict) or not analysis_evidence:
        return _empty_value_text()

    technique_key = str(technique or "").strip().lower()
    sections: list[str] = []

    if technique_key == "waxs":
        peak = analysis_evidence.get("peak_evidence", {}) if isinstance(analysis_evidence.get("peak_evidence"), dict) else {}
        background = analysis_evidence.get("background_evidence", {}) if isinstance(analysis_evidence.get("background_evidence"), dict) else {}
        phase = analysis_evidence.get("phase_evidence", {}) if isinstance(analysis_evidence.get("phase_evidence"), dict) else {}
        trend = _waxs_temperature_trend_evidence(analysis_evidence)

        parts: list[str] = []

        peak_bits = []
        for label, value in (("n", peak.get("peak_count")), ("spread", peak.get("peak_gap_spread")), ("width", peak.get("peak_width_spread"))):
            text = _display_text(value)
            if text != _empty_value_text():
                peak_bits.append(f"{label}={text}")
        if peak_bits:
            parts.append("peak=" + ", ".join(peak_bits))

        background_bits = []
        for label, value in (("offset", background.get("two_theta_offset")), ("method", background.get("background_method")), ("halo", background.get("amorphous_subtraction"))):
            text = _display_text(value)
            if text != _empty_value_text():
                background_bits.append(f"{label}={text}")
        if background_bits:
            parts.append("background=" + ", ".join(background_bits))

        phase_bits = []
        for label, value in (("Xc", phase.get("Xc_pct")), ("method", phase.get("crystallinity_method")), ("D", phase.get("D_Scherrer_nm"))):
            text = _display_text(value)
            if text != _empty_value_text():
                phase_bits.append(f"{label}={text}")
        if phase_bits:
            parts.append("phase=" + ", ".join(phase_bits))

        trend_bits = []
        for label, value in (
            ("score", trend.get("D_trend_support_score")),
            ("mode", trend.get("D_trend_monotonicity")),
            ("support", trend.get("D_support_peak_count")),
        ):
            text = _display_text(value)
            if text != _empty_value_text():
                trend_bits.append(f"{label}={text}")
        if trend.get("instrument_broadening_present") is not None:
            trend_bits.append(f"instrument_broadening={bool(trend.get('instrument_broadening_present'))}")
        if trend_bits:
            parts.append("trend=" + ", ".join(trend_bits))

        if parts:
            sections.append("WAXS | " + " ; ".join(parts))

        support_bits = []
        for label, value in (
            ("peak", analysis_evidence.get("peak_support_score")),
            ("background", analysis_evidence.get("background_stability_score")),
            ("phase", analysis_evidence.get("phase_support_score")),
            ("size", analysis_evidence.get("size_support_score")),
            ("D_trend", trend.get("D_trend_support_score") if isinstance(trend, dict) else None),
            ("waxs_support_score", analysis_evidence.get("waxs_support_score")),
        ):
            text = _format_score_value(value)
            if text != _empty_value_text():
                support_bits.append(f"{label}={text}")
        if support_bits:
            sections.append("Support | " + " | ".join(support_bits))

    elif technique_key == "saxs":
        strain_text = saxs_strain_summary_text(
            None,
            analysis_evidence,
            symptom_names=_evidence_symptom_names(analysis_evidence),
            language=language,
        )
        if strain_text:
            sections.append("SAXS | " + strain_text)

    elif technique_key == "ir":
        feature = analysis_evidence.get("feature_evidence", {}) if isinstance(analysis_evidence.get("feature_evidence"), dict) else {}
        reference = feature.get("reference_evidence", {}) if isinstance(feature.get("reference_evidence"), dict) else {}
        assignment = feature.get("assignment_evidence", {}) if isinstance(feature.get("assignment_evidence"), dict) else {}
        structure = feature.get("structure_evidence", {}) if isinstance(feature.get("structure_evidence"), dict) else {}
        parts = []

        if isinstance(reference, dict) and reference:
            parts.append(
                tr(
                    "RESULTS_REVIEW_IR_REFERENCE",
                    _display_text(reference.get("band_count")),
                    _display_text(reference.get("hit_count")),
                    _display_text(reference.get("missing_count")),
                )
            )

        if isinstance(assignment, dict) and assignment.get("assignment_confidence") is not None:
            confidence = _format_score_value(assignment.get("assignment_confidence"))
            if confidence != _empty_value_text():
                parts.append(tr("RESULTS_REVIEW_IR_ASSIGNMENT", confidence))

        if isinstance(structure, dict):
            basis = str(structure.get("classification_basis", "") or "").strip()
            if basis:
                parts.append(tr("RESULTS_REVIEW_IR_BASIS", _ir_basis_label_text(basis)))
            if structure.get("characteristic_band_support_ok") is not None:
                support_text = tr("IR_SUPPORT_COMPLETE") if bool(structure.get("characteristic_band_support_ok")) else tr("IR_SUPPORT_INCOMPLETE")
                parts.append(tr("RESULTS_REVIEW_IR_SUPPORT", support_text))
            if structure.get("paper_conclusion_ready") is not None:
                parts.append(
                    tr(
                        "RESULTS_REVIEW_IR_CONCLUSION_STATE",
                        _ir_conclusion_state_display(structure.get("paper_conclusion_ready")),
                    )
                )
        if parts:
            sections.append("IR | " + " ; ".join(parts))

    elif technique_key == "nmr":
        feature = analysis_evidence.get("feature_evidence", {}) if isinstance(analysis_evidence.get("feature_evidence"), dict) else {}
        assignment = feature.get("assignment_evidence", {}) if isinstance(feature.get("assignment_evidence"), dict) else {}
        structure = feature.get("structure_evidence", {}) if isinstance(feature.get("structure_evidence"), dict) else {}
        axis = feature.get("axis_evidence", {}) if isinstance(feature.get("axis_evidence"), dict) else {}
        parts = []
        readiness = structure.get("assignment_readiness") or assignment.get("readiness")
        if isinstance(readiness, dict) and readiness.get("class"):
            parts.append(
                tr_for_language(
                    "RESULTS_REVIEW_NMR_ASSIGNMENT",
                    language,
                    str(readiness["class"]),
                )
            )
        if isinstance(axis, dict) and axis:
            axis_parts = []
            for key in ("source", "units", "calibrated"):
                value = axis.get(key)
                if value is not None and str(value).strip():
                    axis_parts.append(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
            if axis_parts:
                parts.append(tr("RESULTS_REVIEW_NMR_AXIS", " | ".join(axis_parts)))
            vendor_axis_text = _nmr_vendor_axis_text(axis.get("vendor_declaration"))
            if vendor_axis_text:
                parts.append(tr("RESULTS_REVIEW_NMR_VENDOR_AXIS", vendor_axis_text))
        if parts:
            sections.append("NMR | " + " ; ".join(parts))

    elif technique_key == "dsc":
        dsc_text = result_review_dsc_support_block_text(analysis_evidence, include_measurement=True)
        if dsc_text != _empty_value_text():
            sections.append("DSC | " + dsc_text)

    else:
        for label, key in (
            ("fit", "fit_evidence"),
            ("physical", "physical_evidence"),
            ("residual", "residual_evidence"),
            ("stability", "stability_evidence"),
        ):
            block = analysis_evidence.get(key, {})
            if isinstance(block, dict) and block:
                preview_items = []
                for item_key in list(block.keys())[:3]:
                    value = block.get(item_key)
                    text = _display_text(value)
                    if text != _empty_value_text():
                        preview_items.append(f"{item_key}={text}")
                if preview_items:
                    sections.append(f"{label}: " + " | ".join(preview_items))

    constraint_summary = analysis_evidence.get("constraint_summary", {})
    if isinstance(constraint_summary, dict) and constraint_summary:
        sections.append("constraints=" + _constraint_summary_text(analysis_evidence))

    if not sections:
        return _empty_value_text()
    return " | ".join(sections[:4])


def result_review_round_core_summary_text(
    output_parameters,
    *,
    technique: str,
) -> str:
    output = output_parameters if isinstance(output_parameters, dict) else {}
    technique_key = str(technique or "").strip().lower()
    if technique_key == "waxs":
        keys = ("n_peaks", "Xc_pct", "D_Scherrer_nm")
    elif technique_key == "ir":
        keys = ("n_peaks", "polymer_score", "assignment_confidence", "Xc_pct")
    elif technique_key == "dsc":
        keys = ("Tg_C", "Tm_peak_C", "Tcc_peak_C", "DHm_Jg", "Xc_pct", "quality_score")
    else:
        keys = ("r_squared", "quality_score", "L_nm", "Xc_pct", "Tm_peak_C", "Tc_peak_C")

    parts = []
    for key in keys:
        text = _display_text(output.get(key))
        if text != _empty_value_text():
            parts.append(f"{key}={text}")
    if not parts:
        return _empty_value_text()
    return " | ".join(parts[:4])


def result_review_round_support_summary_text(
    analysis_evidence,
    *,
    technique: str,
    language: str = "en",
) -> str:
    evidence = analysis_evidence if isinstance(analysis_evidence, dict) else {}
    if not evidence:
        return _empty_value_text()

    technique_key = str(technique or "").strip().lower()
    if technique_key == "waxs":
        parts = []
        for label, key in (
            ("peak", "peak_support_score"),
            ("background", "background_stability_score"),
            ("phase", "phase_support_score"),
            ("size", "size_support_score"),
            ("waxs_support_score", "waxs_support_score"),
        ):
            text = _format_score_value(evidence.get(key))
            if text != _empty_value_text():
                parts.append(f"{label}={text}")
        return " | ".join(parts) if parts else _empty_value_text()

    if technique_key == "ir":
        feature = evidence.get("feature_evidence", {}) if isinstance(evidence.get("feature_evidence"), dict) else {}
        reference = feature.get("reference_evidence", {}) if isinstance(feature.get("reference_evidence"), dict) else {}
        assignment = feature.get("assignment_evidence", {}) if isinstance(feature.get("assignment_evidence"), dict) else {}
        structure = feature.get("structure_evidence", {}) if isinstance(feature.get("structure_evidence"), dict) else {}

        parts = []
        if isinstance(reference, dict) and reference:
            parts.append(
                tr(
                    "RESULTS_REVIEW_IR_REFERENCE",
                    _display_text(reference.get("band_count")),
                    _display_text(reference.get("hit_count")),
                    _display_text(reference.get("missing_count")),
                )
            )

        if isinstance(assignment, dict):
            confidence = _format_score_value(assignment.get("assignment_confidence"))
            if confidence != _empty_value_text():
                parts.append(tr("RESULTS_REVIEW_IR_ASSIGNMENT", confidence))

        if isinstance(structure, dict):
            basis = str(structure.get("classification_basis", "") or "").strip()
            if basis:
                parts.append(tr("RESULTS_REVIEW_IR_BASIS", _ir_basis_label_text(basis)))
            if structure.get("characteristic_band_support_ok") is not None:
                support_text = tr("IR_SUPPORT_COMPLETE") if bool(structure.get("characteristic_band_support_ok")) else tr("IR_SUPPORT_INCOMPLETE")
                parts.append(tr("RESULTS_REVIEW_IR_SUPPORT", support_text))
            if structure.get("paper_conclusion_ready") is not None:
                parts.append(
                    tr(
                        "RESULTS_REVIEW_IR_CONCLUSION_STATE",
                        _ir_conclusion_state_display(structure.get("paper_conclusion_ready")),
                    )
                )

        return " | ".join(parts) if parts else _empty_value_text()

    if technique_key == "nmr":
        feature = evidence.get("feature_evidence", {}) if isinstance(evidence.get("feature_evidence"), dict) else {}
        assignment = feature.get("assignment_evidence", {}) if isinstance(feature.get("assignment_evidence"), dict) else {}
        structure = feature.get("structure_evidence", {}) if isinstance(feature.get("structure_evidence"), dict) else {}
        axis = feature.get("axis_evidence", {}) if isinstance(feature.get("axis_evidence"), dict) else {}

        parts = []
        readiness = structure.get("assignment_readiness") or assignment.get("readiness")
        if isinstance(readiness, dict) and readiness.get("class"):
            parts.append(
                tr_for_language(
                    "RESULTS_REVIEW_NMR_ASSIGNMENT",
                    language,
                    str(readiness["class"]),
                )
            )
        assignment_source = str(
            assignment.get("assignment_source")
            or assignment.get("assignment_library_source")
            or ""
        ).strip()
        if assignment_source:
            parts.append(
                tr_for_language(
                    "RESULTS_REVIEW_NMR_ASSIGNMENT_SOURCE",
                    language,
                    assignment_source,
                )
            )
        if isinstance(axis, dict) and axis:
            axis_parts = []
            for key in ("source", "units", "calibrated"):
                value = axis.get(key)
                if value is not None and str(value).strip():
                    axis_parts.append(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
            if axis_parts:
                parts.append(
                    tr_for_language(
                        "RESULTS_REVIEW_NMR_AXIS",
                        language,
                        " | ".join(axis_parts),
                    )
                )
            vendor_axis_text = _nmr_vendor_axis_text(axis.get("vendor_declaration"))
            if vendor_axis_text:
                parts.append(
                    tr_for_language(
                        "RESULTS_REVIEW_NMR_VENDOR_AXIS",
                        language,
                        vendor_axis_text,
                    )
                )
        xc_status = str(structure.get("Xc_assignment_status") or "").strip()
        if xc_status:
            ready = structure.get("paper_conclusion_ready") is True
            allowed = isinstance(readiness, dict) and readiness.get("allowed") is True
            gate = "allowed" if ready and allowed else "blocked"
            reason = str(readiness.get("reason") or "") if isinstance(readiness, dict) else ""
            parts.append(
                tr_for_language(
                    "RESULTS_REVIEW_NMR_XC_GATE",
                    language,
                    gate,
                    reason or xc_status,
                )
            )
        if parts:
            return " | ".join(parts)

    if technique_key == "dsc":
        support_text = result_review_dsc_support_block_text(evidence, include_measurement=False)
        return support_text if support_text != _empty_value_text() else _empty_value_text()

    parts = []
    stability = _stability_summary_text(evidence)
    if stability != _empty_value_text():
        parts.append(stability)
    constraint = _constraint_summary_text(evidence)
    if constraint != _empty_value_text():
        parts.append(constraint)
    if not parts:
        return _empty_value_text()
    return " | ".join(parts[:2])


def _saxs_lc_status_summary_text(params, analysis_evidence=None) -> str:
    analysis_evidence = analysis_evidence if isinstance(analysis_evidence, dict) else {}
    parts = saxs_lc_status_summary_parts(params, analysis_evidence)
    if parts is None:
        return ""
    status, diagnostic_rows_int, within_window_rows_int, reason = parts

    return tr(
        "RESULTS_SUMMARY_RISK_SAXS_LC_STATUS",
        saxs_lc_status_text(status) or tr("AI_TUNING_EMPTY_VALUE"),
        diagnostic_rows_int,
        within_window_rows_int,
        reason or tr("AI_TUNING_EMPTY_VALUE"),
    )


def _waxs_support_snapshot(analysis_evidence=None) -> dict[str, float | None]:
    analysis_evidence = analysis_evidence if isinstance(analysis_evidence, dict) else {}
    snapshot = {}
    for key in (
        "peak_support_score",
        "background_stability_score",
        "phase_support_score",
        "size_support_score",
        "D_trend_support_score",
        "waxs_support_score",
    ):
        try:
            value = float(analysis_evidence.get(key))
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


def result_review_saxs_semantic_details(
    params=None,
    analysis_evidence=None,
    *,
    language: str = "en",
) -> dict[str, str]:
    evidence = analysis_evidence if isinstance(analysis_evidence, dict) else {}
    snapshot = saxs_structure_status_snapshot(
        params,
        evidence,
        symptom_names=_evidence_symptom_names(evidence),
    )
    status = str(snapshot.get("lc_reliability_status") or "").strip().lower()
    melting_status = str(snapshot.get("melting_window_status") or "").strip().lower()
    symptoms = snapshot.get("symptoms", [])
    param_values = params if isinstance(params, dict) else {}
    batch_rows = int(snapshot.get("batch_rows") or 0)
    diagnostic_rows = int(snapshot.get("diagnostic_only_rows") or 0)
    low_conf_rows = int(snapshot.get("low_confidence_rows") or 0)
    usable_rows = int(snapshot.get("usable_rows") or 0)
    within_window_rows = int(snapshot.get("within_window_rows") or 0)
    near_onset_rows = int(snapshot.get("near_onset_rows") or 0)
    post_end_rows = int(snapshot.get("post_end_rows") or 0)
    reason_text = saxs_reason_text(snapshot.get("lc_reliability_reason"), language=language)
    melting_reason_text = saxs_reason_text(snapshot.get("melting_window_reason"), language=language)
    zh = str(language or "").strip().lower().startswith("zh")

    details: dict[str, str] = {}

    if status or diagnostic_rows > 0 or low_conf_rows > 0 or usable_rows > 0:
        if status == "diagnostic_only" or diagnostic_rows > 0:
            affected = diagnostic_rows or 1
            if zh:
                interpretation = f"{affected} 帧 lc 仅适合作诊断，不应直接当作最终层片厚度结果"
            else:
                interpretation = f"{affected} frame(s) are diagnostic-only for lc, so those thickness values should not be treated as final"
        elif status == "low_confidence" or low_conf_rows > 0:
            affected = low_conf_rows or 1
            if zh:
                interpretation = f"{affected} 帧 lc 仅适合低置信趋势判断，暂不宜写成稳定结构结论"
            else:
                interpretation = f"{affected} frame(s) keep only low-confidence lc support, so use them for trend reading rather than a firm structure conclusion"
        else:
            affected = usable_rows or batch_rows or 1
            if zh:
                interpretation = f"{affected} 帧 lc 具备可用结构支撑"
            else:
                interpretation = f"{affected} frame(s) keep usable lc support for structure interpretation"
        if reason_text and status != "usable":
            suffix = f"；原因：{reason_text}" if zh else f"; reason: {reason_text}"
            interpretation += suffix
        details["interpretation"] = interpretation
        if status:
            details["status"] = (
                f"strain status: {saxs_lc_status_text(status, language=language)}"
                if not zh
                else f"strain 状态：{saxs_lc_status_text(status, language=language)}"
            )
        paper_figure = snapshot.get("paper_figure_candidate")
        paper_candidate = snapshot.get("paper_conclusion_candidate")
        if paper_figure is not None or paper_candidate is not None:
            paper_figure_text = str(bool(paper_figure)).lower() if paper_figure is not None else ""
            paper_candidate_text = str(bool(paper_candidate)).lower() if paper_candidate is not None else ""
            details["candidate"] = (
                f"paper figure={paper_figure_text}; paper conclusion={paper_candidate_text}"
                if not zh
                else f"论文图候选={paper_figure_text}；论文结论候选={paper_candidate_text}"
            )

    if melting_status or within_window_rows > 0 or near_onset_rows > 0 or post_end_rows > 0:
        if melting_status == "near_onset" or near_onset_rows > 0:
            if zh:
                window_text = "当前序列已接近 SAXS 推导的熔融起点"
            else:
                window_text = "the current sequence is near the SAXS-derived melting onset"
        elif melting_status == "within_window" or within_window_rows > 0:
            if zh:
                window_text = "当前序列已有帧进入 SAXS 推导的熔融窗口"
            else:
                window_text = "the current sequence has frames inside the SAXS-derived melting window"
        elif melting_status == "post_end" or post_end_rows > 0:
            if zh:
                window_text = "当前序列已有帧越过 SAXS 推导的熔融终点"
            else:
                window_text = "the current sequence has frames past the SAXS-derived melting end"
        elif melting_status == "outside_window":
            if zh:
                window_text = "当前主导帧仍在 SAXS 熔融窗口之外"
            else:
                window_text = "the dominant frames remain outside the SAXS melting window"
        else:
            if zh:
                window_text = "SAXS 熔融窗口还未稳定解析"
            else:
                window_text = "the SAXS melting window is not resolved yet"

        count_bits = []
        if near_onset_rows > 0:
            count_bits.append(f"near-onset={near_onset_rows}")
        if within_window_rows > 0:
            count_bits.append(f"within-window={within_window_rows}")
        if post_end_rows > 0:
            count_bits.append(f"post-end={post_end_rows}")
        if count_bits:
            window_text += f" ({', '.join(count_bits)})"
        if melting_reason_text and melting_status in {"", "undetermined"}:
            suffix = f"；依据：{melting_reason_text}" if zh else f"; basis: {melting_reason_text}"
            window_text += suffix
        details["window"] = window_text

    calibration_bits = []
    lc_method = str(param_values.get("lc_method") or "").strip()
    if lc_method:
        calibration_bits.append(f"lc_method={lc_method}")
    fallback_active = param_values.get("calibrated_fallback_active")
    if fallback_active is not None:
        calibration_bits.append(f"calibrated_fallback_active={bool(fallback_active)}")
    calibration_reason = str(param_values.get("calibration_skipped_reason") or "").strip()
    if calibration_reason:
        calibration_bits.append(f"calibration_skipped_reason={calibration_reason}")
    if calibration_bits:
        if zh:
            details["calibration"] = f"校准状态：{'；'.join(calibration_bits)}"
        else:
            details["calibration"] = f"calibration state: {'; '.join(calibration_bits)}"

    if "lc_unreliable_without_melting_proof" in symptoms:
        details["boundary"] = (
            "这还不能判作熔融，当前问题是熔融窗口尚未被证明前，lc 提取已经失稳"
            if zh
            else "do not call this melting yet; the problem is unstable lc extraction before the melting window is proven"
        )
    elif "temperature_sequence_near_melting_window" in symptoms:
        details["boundary"] = (
            "这些帧应按过渡敏感区解读，而不是按普通固态层片继续解释"
            if zh
            else "treat these frames as transition-sensitive rather than as ordinary solid-state lamellar evolution"
        )
    elif "diagnostic_lc_frames_present" in symptoms:
        details["boundary"] = (
            "在 2D 图、峰连续性和温度序列支撑恢复前，不要把这些 lc 当成最终结构参数"
            if zh
            else "do not treat those lc values as final structure parameters before the 2D pattern and sequence support recover"
        )

    return details


def result_review_saxs_semantic_lines(
    params=None,
    analysis_evidence=None,
    *,
    language: str = "en",
) -> list[str]:
    details = result_review_saxs_semantic_details(
        params,
        analysis_evidence,
        language=language,
    )
    lines = []
    interpretation = str(details.get("interpretation") or "").strip()
    if interpretation:
        lines.append(tr("RESULTS_REVIEW_SAXS_INTERPRETATION", interpretation))
    window_text = str(details.get("window") or "").strip()
    if window_text:
        lines.append(tr("RESULTS_REVIEW_SAXS_WINDOW", window_text))
    calibration_text = str(details.get("calibration") or "").strip()
    if calibration_text:
        lines.append(tr("RESULTS_REVIEW_SAXS_CALIBRATION", calibration_text))
    boundary = str(details.get("boundary") or "").strip()
    if boundary:
        lines.append(tr("RESULTS_REVIEW_SAXS_BOUNDARY", boundary))
    return lines


def result_review_saxs_trend_text(
    params=None,
    analysis_evidence=None,
    *,
    language: str = "en",
) -> str:
    details = result_review_saxs_semantic_details(
        params,
        analysis_evidence,
        language=language,
    )
    return " | ".join(
        str(part).strip()
        for part in (
            details.get("interpretation"),
            details.get("window"),
            details.get("calibration"),
            details.get("boundary"),
        )
        if part is not None and str(part).strip()
    )


def _waxs_structure_evidence(analysis_evidence=None) -> dict:
    analysis_evidence = analysis_evidence if isinstance(analysis_evidence, dict) else {}
    if not isinstance(analysis_evidence, dict):
        return {}
    structure = analysis_evidence.get("structure_evidence")
    return structure if isinstance(structure, dict) else {}


@dataclass(frozen=True)
class ResultReviewPanelTexts:
    meta_text: str = ""
    benchmark_text: str = ""
    chain_text: str = ""
    trend_text: str = ""
    boundary_text: str = ""
    joint_text: str = ""
    joint_visible: bool = False
    ir_support_text: str = ""
    nmr_support_text: str = ""
    risk_text: str = ""
    next_text: str = ""
    title_text: str = ""


def build_result_review_summary_snapshot(
    *,
    current,
    technique: str,
    measured_text: str = "",
    origin_label: str = "",
    confirmed_label: str = "",
    validation_summary: str = "",
    comparison_summary: str = "",
    current_metrics=None,
    strain_active: bool = False,
    source_summary: str = "",
    ir_lines=None,
    ir_support_text: str = "",
    waxs_core_text: str = "",
    waxs_support_text: str = "",
    waxs_semantic_lines=None,
    saxs_semantic_lines=None,
    saxs_strain_text: str = "",
    saxs_method_bits=None,
    fallback_text: str = "",
    current_origin: str = "",
    tuning_context=None,
    history_context=None,
    tuning_goal_label_fn: Callable[[str], str] | None = None,
    benchmark_summary_text_fn: Callable[[dict], str] | None = None,
    chain_text: str = "",
    joint_summary: str = "",
    joint_reminder_text: str = "",
    responsibility_boundary: str = "",
) -> dict[str, Any]:
    optimization_parts = None
    if str(current_origin or "").strip() == "controlled_optimization_rerun":
        optimization_parts = controlled_optimization_review_parts(
            tuning_context,
            history_context,
            tuning_goal_label_fn=tuning_goal_label_fn,
            benchmark_summary_text_fn=benchmark_summary_text_fn,
        )

    return {
        "current": current if isinstance(current, dict) else {},
        "technique": str(technique or "").strip().lower(),
        "measured_text": str(measured_text or "").strip(),
        "origin_label": str(origin_label or "").strip(),
        "confirmed_label": str(confirmed_label or "").strip(),
        "validation_summary": str(validation_summary or "").strip(),
        "comparison_summary": str(comparison_summary or "").strip(),
        "current_metrics": current_metrics if isinstance(current_metrics, dict) else {},
        "strain_active": bool(strain_active),
        "source_summary": str(source_summary or "").strip(),
        "ir_lines": [str(line or "").strip() for line in (ir_lines or []) if str(line or "").strip()],
        "ir_support_text": str(ir_support_text or "").strip(),
        "waxs_core_text": str(waxs_core_text or "").strip(),
        "waxs_support_text": str(waxs_support_text or "").strip(),
        "waxs_semantic_lines": [str(line or "").strip() for line in (waxs_semantic_lines or []) if str(line or "").strip()],
        "saxs_semantic_lines": [str(line or "").strip() for line in (saxs_semantic_lines or []) if str(line or "").strip()],
        "saxs_strain_text": str(saxs_strain_text or "").strip(),
        "saxs_method_bits": [str(bit or "").strip() for bit in (saxs_method_bits or []) if str(bit or "").strip()],
        "fallback_text": str(fallback_text or "").strip(),
        "optimization_parts": optimization_parts,
        "chain_text": str(chain_text or "").strip(),
        "joint_summary": str(joint_summary or "").strip(),
        "joint_reminder_text": str(joint_reminder_text or "").strip(),
        "responsibility_boundary": str(responsibility_boundary or "").strip(),
    }


def build_result_review_summary_snapshot_from_window(window) -> dict[str, Any]:
    current = window._current_results_record()
    if not isinstance(current, dict) or not current:
        return {}

    summary = current.get("results_summary") if isinstance(current.get("results_summary"), dict) else {}
    analysis_evidence = window._current_analysis_evidence()
    technique = str(getattr(window, "_current_technique", "") or "").strip().lower()
    current_metrics = window._history_result_metrics(current)
    measured_text = window._measured_result_summary_text(current)
    origin_label = window._current_result_origin_label()
    confirmed_label = tr("RESULTS_REVIEW_CONFIRMED") if window._is_current_result_confirmed() else tr("RESULTS_REVIEW_PENDING")

    validation_summary = str(summary.get("validation_summary") or current.get("validation_summary") or "").strip()
    if not validation_summary and hasattr(window, "_results_summary_risk_label"):
        validation_summary = str(window._results_summary_risk_label.text() or "").strip()
    comparison_summary = str(window._result_comparison_summary() or "").strip()
    source_summary = window._result_source_summary_text(current)
    strain_active = bool(window._saxs_strain_evidence_snapshot(current.get("parameters"), analysis_evidence).get("active")) if technique == "saxs" else False
    params = current.get("parameters") if isinstance(current.get("parameters"), dict) else {}
    saxs_method_bits = []
    if technique == "saxs":
        lc_method = str(params.get("lc_method") or current_metrics.get("lc_method") or "").strip()
        if lc_method:
            saxs_method_bits.append(f"lc_method={lc_method}")
        skip_reason = str(params.get("calibration_skipped_reason") or current_metrics.get("calibration_skipped_reason") or "").strip()
        if skip_reason:
            saxs_method_bits.append(f"calibration_skipped_reason={skip_reason}")
        fallback_active = params.get("calibrated_fallback_active")
        if fallback_active is not None:
            saxs_method_bits.append(f"calibrated_fallback_active={bool(fallback_active)}")

    history_context = window._current_result_history_context(current)
    tuning_context = window._current_result_tuning_context(current)
    joint_context = window._joint_ai_context()
    if not isinstance(joint_context, dict):
        joint_context = {}
    joint_summary = str(joint_context.get("summary") or "").strip()
    joint_reminder_text = window._joint_ai_reminder_text(joint_context) if joint_context else ""

    snapshot = build_result_review_summary_snapshot(
        current=current,
        technique=technique,
        measured_text=measured_text,
        origin_label=origin_label,
        confirmed_label=confirmed_label,
        validation_summary=validation_summary,
        comparison_summary=comparison_summary,
        current_metrics=current_metrics,
        strain_active=strain_active,
        source_summary=source_summary,
        ir_lines=result_review_ir_temperature_2d_user_summary_lines(analysis_evidence) if technique == "ir" else [],
        ir_support_text=result_review_ir_support_block_text(analysis_evidence) if technique == "ir" else "",
        waxs_core_text=result_review_waxs_core_text(current_metrics) if technique == "waxs" else "",
        waxs_support_text=result_review_waxs_support_text(analysis_evidence) if technique == "waxs" else "",
        waxs_semantic_lines=window._waxs_result_semantic_lines(current_metrics, analysis_evidence) if technique == "waxs" else [],
        saxs_semantic_lines=result_review_saxs_semantic_lines(params, analysis_evidence, language=get_language()) if technique == "saxs" else [],
        saxs_strain_text=(
            saxs_strain_summary_text(
                params,
                analysis_evidence,
                symptom_names=_evidence_symptom_names(analysis_evidence),
                language=get_language(),
            )
            if technique == "saxs"
            else ""
        ),
        saxs_method_bits=saxs_method_bits,
        fallback_text=window._fallback_evidence_summary_text(analysis_evidence),
        current_origin=window._current_result_origin(),
        tuning_context=tuning_context,
        history_context=history_context,
        tuning_goal_label_fn=getattr(window, "_ai_tuning_goal_label", None),
        benchmark_summary_text_fn=getattr(window, "_benchmark_summary_text", None),
        chain_text=window._ai_tuning_chain_snapshot(tuning_context) if isinstance(tuning_context, dict) and tuning_context else "",
        joint_summary=joint_summary,
        joint_reminder_text=joint_reminder_text,
        responsibility_boundary=window._responsibility_boundary_summary(),
    )
    return snapshot


def build_result_review_summary_text_from_window(window) -> str:
    snapshot = build_result_review_summary_snapshot_from_window(window)
    if not snapshot:
        return ""
    return result_review_summary_text(snapshot)


def build_result_review_panel_texts_from_window(window) -> ResultReviewPanelTexts:
    current = window._current_results_record()
    if not isinstance(current, dict) or not current:
        return ResultReviewPanelTexts()

    analysis_evidence = window._current_analysis_evidence()
    history_context = window._current_result_history_context(current)
    tuning_context = window._current_result_tuning_context(current)
    joint_context = window._joint_ai_context()
    if not isinstance(joint_context, dict):
        joint_context = {}
    params = current.get("parameters") if isinstance(current.get("parameters"), dict) else {}
    technique = str(getattr(window, "_current_technique", "") or "").strip().lower()
    trend_text = ""
    if technique == "waxs":
        trend_text = window._waxs_temperature_trend_text(analysis_evidence)
    elif technique == "saxs":
        trend_text = result_review_saxs_trend_text(params, analysis_evidence, language=get_language())

    current_origin = window._current_result_origin()
    is_controlled_rerun = current_origin == "controlled_optimization_rerun"
    validation_summary = str(current.get("validation_summary") or "").strip()
    summary = current.get("results_summary") if isinstance(current.get("results_summary"), dict) else {}
    if not validation_summary and isinstance(summary, dict):
        validation_summary = str(summary.get("validation_summary") or "").strip()
    if not validation_summary and hasattr(window, "_results_summary_risk_label"):
        validation_summary = str(window._results_summary_risk_label.text() or "").strip()

    current_confirmed = tr("RESULTS_REVIEW_CONFIRMED") if window._is_current_result_confirmed() else tr("RESULTS_REVIEW_PENDING")
    return result_review_panel_texts(
        {
            "current": current,
            "technique": technique,
            "current_origin": current_origin,
            "current_label": window._current_result_label_for_confirmation(),
            "current_origin_label": window._current_result_origin_label(),
            "current_confirmed_label": current_confirmed,
            "measured_text": window._measured_result_summary_text(current),
            "validation_summary": validation_summary,
            "analysis_evidence": analysis_evidence,
            "history_context": history_context,
            "tuning_context": tuning_context,
            "joint_context": joint_context,
            "responsibility_boundary": window._responsibility_boundary_summary() if is_controlled_rerun else "",
            "fallback_next_text": str(window._results_summary_next_label.text() or "").strip() if hasattr(window, "_results_summary_next_label") else "",
            "trend_text": trend_text,
            "is_controlled_rerun": is_controlled_rerun,
        },
        language=get_language(),
        tuning_goal_label_fn=getattr(window, "_ai_tuning_goal_label", None),
        benchmark_summary_text_fn=getattr(window, "_benchmark_summary_text", None),
        benchmark_delta_text_fn=getattr(window, "_benchmark_delta_text", None),
        family_label_fn=getattr(window, "_joint_issue_family_label", None),
    )


def _panel_tuning_goal_text(
    tuning_context,
    history_context,
    *,
    tuning_goal_label_fn: Callable[[str], str] | None = None,
) -> str:
    tuning = tuning_context if isinstance(tuning_context, dict) else {}
    history = history_context if isinstance(history_context, dict) else {}
    tuning_goal = str(tuning.get("tuning_goal_label") or "").strip()
    if tuning_goal:
        return tuning_goal
    raw_goal = str(tuning.get("tuning_goal") or "").strip()
    if raw_goal:
        formatter = tuning_goal_label_fn or (lambda value: value)
        tuning_goal = str(formatter(raw_goal) or "").strip()
        if tuning_goal:
            return tuning_goal
    tuning_goal = str(history.get("tuning_goal_label") or "").strip()
    if tuning_goal:
        return tuning_goal
    raw_goal = str(history.get("tuning_goal") or "").strip()
    if raw_goal:
        formatter = tuning_goal_label_fn or (lambda value: value)
        return str(formatter(raw_goal) or "").strip()
    return ""


def _panel_benchmark_text(
    tuning_context,
    history_context,
    *,
    benchmark_summary_text_fn: Callable[[dict], str] | None = None,
) -> str:
    tuning = tuning_context if isinstance(tuning_context, dict) else {}
    history = history_context if isinstance(history_context, dict) else {}

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
    return benchmark_text


def _panel_chain_text(
    tuning_context,
    *,
    current_origin: str,
    language: str,
    benchmark_delta_text_fn: Callable[[object], str] | None = None,
) -> str:
    return ai_tuning_chain_summary(
        tuning_context,
        current_origin=current_origin,
        language=language,
        benchmark_delta_text_fn=benchmark_delta_text_fn,
    )


def _panel_joint_text(
    joint_context,
    *,
    language: str = "en",
    family_label_fn: Callable[[object], str] | None = None,
) -> tuple[str, bool]:
    joint = joint_context if isinstance(joint_context, dict) else {}
    if not joint:
        return "", False
    formatter = family_label_fn or (lambda value: str(value))
    separator = "、" if str(language or "").strip().lower().startswith("zh") else ", "
    reminder_parts = joint_ai_reminder_parts(
        joint,
        family_label_fn=formatter,
        separator=separator,
    )
    compare_parts = joint_compare_hint_parts(
        joint,
        family_label_fn=formatter,
        separator=separator,
    )
    joint_summary = str(joint.get("summary") or "").strip()
    joint_reminder_text = tr(reminder_parts.translation_key, *reminder_parts.args) if reminder_parts else ""
    joint_compare_hint_text = tr(compare_parts.translation_key, *compare_parts.args) if compare_parts else ""
    conclusion = joint.get("joint_conclusion") if isinstance(joint.get("joint_conclusion"), dict) else {}
    conclusion_class = str(conclusion.get("class") or "").strip()
    conclusion_reason = str(conclusion.get("reason") or "").strip()
    conclusion_allowed = conclusion.get("allowed")
    joint_conclusion_text = ""
    if conclusion_class or conclusion_reason or conclusion_allowed is not None:
        joint_conclusion_text = tr(
            "RESULTS_REVIEW_JOINT_CONCLUSION",
            conclusion_class or "unknown",
            str(conclusion_allowed).lower() if isinstance(conclusion_allowed, bool) else str(conclusion_allowed or "unknown"),
            conclusion_reason or "unspecified",
        )
    joint_parts = [
        part
        for part in [joint_summary, joint_conclusion_text, joint_reminder_text, joint_compare_hint_text]
        if part
    ]
    if not joint_parts:
        return tr("RESULTS_REVIEW_NO_JOINT"), False
    return tr("RESULTS_REVIEW_JOINT", " | ".join(joint_parts)), True


def _strip_leading_panel_prefix(text: str, key: str, *, language: str) -> str:
    """Remove repeated localized panel decoration while preserving the body."""
    value = str(text or "").strip()
    if not value:
        return ""

    language_code = "zh" if str(language or "").strip().lower().startswith("zh") else "en"
    prefix_languages = (language_code, "en" if language_code == "zh" else "zh")
    prefixes = tuple(
        tr_for_language(key, prefix_language, "").rstrip()
        for prefix_language in prefix_languages
    )
    while value:
        for prefix in prefixes:
            if prefix and value.startswith(prefix):
                value = value[len(prefix) :].lstrip()
                break
        else:
            break
    return value


def _panel_risk_text(
    validation_summary: str,
    history_context,
    *,
    is_controlled_rerun: bool,
    language: str,
) -> str:
    risk_text = _strip_leading_panel_prefix(
        validation_summary,
        "RESULTS_REVIEW_RISK",
        language=language,
    ) or tr("RESULTS_REVIEW_NO_RISK")
    history = history_context if isinstance(history_context, dict) else {}
    if is_controlled_rerun and history:
        risk_bits = []
        stop_reason = str(history.get("stop_reason") or "").strip()
        remaining_risks = str(history.get("remaining_risks") or "").strip()
        if stop_reason:
            risk_bits.append(stop_reason)
        if remaining_risks:
            risk_bits.append(remaining_risks)
        if risk_bits:
            if risk_text != tr("RESULTS_REVIEW_NO_RISK"):
                risk_text = " | ".join([risk_text] + risk_bits)
            else:
                risk_text = " | ".join(risk_bits)
    return tr("RESULTS_REVIEW_RISK", risk_text)


def _panel_next_text(
    tuning_context,
    history_context,
    *,
    fallback_next_text: str,
    is_controlled_rerun: bool,
    language: str,
) -> str:
    tuning = tuning_context if isinstance(tuning_context, dict) else {}
    history = history_context if isinstance(history_context, dict) else {}
    next_step = ""
    if is_controlled_rerun:
        next_step = str(tuning.get("next_goal") or "").strip()
        if not next_step:
            next_step = str(history.get("next_goal") or "").strip()
    if not next_step:
        next_step = str(fallback_next_text or "").strip()
    next_step = _strip_leading_panel_prefix(
        next_step,
        "RESULTS_REVIEW_NEXT",
        language=language,
    )
    if not next_step:
        next_step = tr("RESULTS_REVIEW_NO_NEXT")
    return tr("RESULTS_REVIEW_NEXT", next_step)


def result_review_panel_texts(
    snapshot: dict[str, Any] | None,
    *,
    language: str = "en",
    tuning_goal_label_fn: Callable[[str], str] | None = None,
    benchmark_summary_text_fn: Callable[[dict], str] | None = None,
    benchmark_delta_text_fn: Callable[[object], str] | None = None,
    family_label_fn: Callable[[object], str] | None = None,
) -> ResultReviewPanelTexts:
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    current = snapshot.get("current") if isinstance(snapshot.get("current"), dict) else {}
    if not current:
        return ResultReviewPanelTexts()

    technique = str(snapshot.get("technique") or "").strip().lower()
    current_label = str(snapshot.get("current_label") or "").strip()
    current_origin_label = str(snapshot.get("current_origin_label") or "").strip()
    current_confirmed_label = str(snapshot.get("current_confirmed_label") or "").strip()
    measured_text = str(snapshot.get("measured_text") or "").strip()
    validation_summary = str(snapshot.get("validation_summary") or "").strip()
    analysis_evidence = snapshot.get("analysis_evidence") if isinstance(snapshot.get("analysis_evidence"), dict) else {}
    history_context = snapshot.get("history_context") if isinstance(snapshot.get("history_context"), dict) else {}
    tuning_context = snapshot.get("tuning_context") if isinstance(snapshot.get("tuning_context"), dict) else {}
    joint_context = snapshot.get("joint_context") if isinstance(snapshot.get("joint_context"), dict) else {}
    current_origin = str(snapshot.get("current_origin") or "").strip()
    is_controlled_rerun = bool(snapshot.get("is_controlled_rerun"))
    fallback_next_text = str(snapshot.get("fallback_next_text") or "").strip()

    tuning_goal_text = str(snapshot.get("tuning_goal_text") or "").strip()
    if not tuning_goal_text:
        tuning_goal_text = _panel_tuning_goal_text(
            tuning_context,
            history_context,
            tuning_goal_label_fn=tuning_goal_label_fn,
        )

    meta_parts = [part for part in [current_label, current_origin_label, current_confirmed_label] if part]
    if tuning_goal_text:
        meta_parts.append(tr("RESULTS_REVIEW_TUNING_GOAL", tuning_goal_text))

    benchmark_detail_text = str(snapshot.get("benchmark_text") or "").strip()
    if not benchmark_detail_text:
        benchmark_detail_text = _panel_benchmark_text(
            tuning_context,
            history_context,
            benchmark_summary_text_fn=benchmark_summary_text_fn,
        )
    benchmark_base = tr("RESULTS_REVIEW_BENCHMARK", measured_text or current_label)
    benchmark_parts = [benchmark_base]
    if benchmark_detail_text:
        benchmark_parts.append(benchmark_detail_text)
    elif is_controlled_rerun:
        benchmark_parts.append(tr("RESULTS_REVIEW_NO_BENCHMARK"))
    benchmark_text = " | ".join(part for part in benchmark_parts if part)

    chain_text = str(snapshot.get("chain_text") or "").strip()
    if not chain_text:
        chain_text = _panel_chain_text(
            tuning_context,
            current_origin=current_origin,
            language=language,
            benchmark_delta_text_fn=benchmark_delta_text_fn,
        )
    chain_label = tr("RESULTS_REVIEW_CHAIN", chain_text) if chain_text else ""

    trend_text = str(snapshot.get("trend_text") or "").strip()
    trend_label = ""
    if trend_text:
        if technique == "waxs":
            trend_label = tr("RESULTS_REVIEW_WAXS_TREND", trend_text)
        elif technique == "saxs":
            trend_label = tr("RESULTS_REVIEW_SAXS_STATUS", trend_text)

    boundary_text = str(snapshot.get("responsibility_boundary") or "").strip()
    fallback_text = str(snapshot.get("fallback_text") or "").strip()
    if not fallback_text and analysis_evidence:
        fallback_text = _batch_fallback_summary_text(analysis_evidence, symptom_names=_evidence_symptom_names(analysis_evidence))
        if fallback_text:
            fallback_text = tr("RESULTS_REVIEW_FALLBACK", fallback_text)
    if fallback_text:
        boundary_text = " | ".join(part for part in [boundary_text, fallback_text] if part)

    joint_text, joint_visible = _panel_joint_text(
        joint_context,
        language=language,
        family_label_fn=family_label_fn,
    )

    ir_support_text = (
        result_review_ir_support_block_text(analysis_evidence)
        if technique == "ir"
        else ""
    )
    nmr_support_text = (
        result_review_round_support_summary_text(
            analysis_evidence,
            technique="nmr",
            language=language,
        )
        if technique == "nmr"
        else ""
    )
    if nmr_support_text == _empty_value_text():
        nmr_support_text = ""

    risk_text = _panel_risk_text(
        validation_summary,
        history_context,
        is_controlled_rerun=is_controlled_rerun,
        language=language,
    )

    next_text = _panel_next_text(
        tuning_context,
        history_context,
        fallback_next_text=fallback_next_text,
        is_controlled_rerun=is_controlled_rerun,
        language=language,
    )

    title_text = tr("RESULTS_REVIEW_TITLE_CONFIRMED") if current_confirmed_label == tr("RESULTS_REVIEW_CONFIRMED") else tr("RESULTS_REVIEW_TITLE")

    return ResultReviewPanelTexts(
        meta_text=" | ".join(meta_parts),
        benchmark_text=benchmark_text,
        chain_text=chain_label,
        trend_text=trend_label,
        boundary_text=boundary_text,
        joint_text=joint_text,
        joint_visible=joint_visible,
        ir_support_text=ir_support_text,
        nmr_support_text=nmr_support_text,
        risk_text=risk_text,
        next_text=next_text,
        title_text=title_text,
    )


def results_risk_summary_text(
    params,
    result=None,
    *,
    technique: str,
    analysis_evidence: dict | None = None,
    language: str = "en",
) -> str:
    technique_key = str(technique or "").strip().lower()
    evidence = analysis_evidence if isinstance(analysis_evidence, dict) else {}
    symptom_names = _evidence_symptom_names(evidence)
    validation_summary = ""
    validation_warnings: list[str] = []
    quality_flags = {}

    if result is not None:
        validation_summary = str(getattr(result, "validation_summary", "") or "").strip()
        validation_warnings = list(getattr(result, "validation_warnings", []) or [])
        quality_flags = dict(getattr(result, "quality_flags", {}) or {})
        if validation_summary and validation_summary != "All checks passed":
            if validation_warnings:
                detail = ", ".join(str(item) for item in validation_warnings[:4] if str(item).strip())
                if detail:
                    validation_summary = f"{validation_summary} | {detail}"
            return tr("RESULTS_SUMMARY_RISK_VALIDATION", validation_summary)

    if technique_key == "saxs" and result is not None:
        mask_truncated = bool(getattr(result, "mask_truncated", False))
        beamstop_warning = bool(getattr(result, "beam_stop_contaminated", False))
        if mask_truncated or beamstop_warning:
            eff_q = getattr(result, "effective_q_min", 0.0)
            try:
                eff_q_text = f"{float(eff_q):.3f}"
            except (TypeError, ValueError):
                eff_q_text = "0.000"
            if mask_truncated and beamstop_warning:
                return tr("RESULTS_SUMMARY_RISK_MASK_AND_BEAMSTOP", eff_q_text)
            if mask_truncated:
                return tr("RESULTS_SUMMARY_RISK_MASK_ONLY", eff_q_text)
            return tr("RESULTS_SUMMARY_RISK_BEAMSTOP_ONLY", eff_q_text)

        fallback_text = _batch_fallback_summary_text(evidence, symptom_names=symptom_names)
        if fallback_text:
            return tr("RESULTS_REVIEW_FALLBACK", fallback_text)

        strain_risk_text = saxs_strain_risk_summary_text(
            params,
            evidence,
            symptom_names=symptom_names,
            language=language,
        )
        if strain_risk_text:
            return strain_risk_text

        lc_status_text = _saxs_lc_status_summary_text(params, evidence)
        if lc_status_text:
            return lc_status_text

        quality_flag_text = quality_flag_summary_text(result, language=language)
        if quality_flag_text:
            return tr("RESULTS_SUMMARY_RISK_VALIDATION", quality_flag_text)

    if technique_key == "waxs":
        analysis_evidence = evidence
        structure = _waxs_structure_evidence(analysis_evidence)
        support = _waxs_support_snapshot(analysis_evidence)
        constraint_summary = analysis_evidence.get("constraint_summary", {}) if isinstance(analysis_evidence, dict) else {}
        if validation_summary and validation_summary != "All checks passed":
            return tr("RESULTS_SUMMARY_RISK_VALIDATION", validation_summary)
        if (
            structure.get("physical_support_pass") is False
            or structure.get("paper_ready_candidate") is False
            or (support.get("waxs_support_score") is not None and float(support["waxs_support_score"]) < 0.72)
            or (support.get("D_trend_support_score") is not None and float(support["D_trend_support_score"]) < 0.60)
            or (isinstance(constraint_summary, dict) and str(constraint_summary.get("status") or "").strip() in {"soft_warn", "hard_fail"})
        ):
            return tr("RESULTS_SUMMARY_RISK_WAXS_LIMITED")

    if technique_key == "dsc":
        analysis_evidence = evidence
        feature = analysis_evidence.get("feature_evidence", {}) if isinstance(analysis_evidence, dict) else {}
        structure = feature.get("structure_evidence", {}) if isinstance(feature.get("structure_evidence"), dict) else {}
        event_support = feature.get("event_support_evidence", {}) if isinstance(feature.get("event_support_evidence"), dict) else {}
        support_values = [
            gui_coerce_summary_float(event_support.get("event_support_score")),
            gui_coerce_summary_float(event_support.get("baseline_stability_score")),
            gui_coerce_summary_float(event_support.get("thermodynamic_consistency_score")),
        ]
        if structure.get("paper_conclusion_ready") is False and any(value is not None and value < 0.72 for value in support_values):
            return tr("RESULTS_SUMMARY_RISK_DSC_LIMITED")

    if isinstance(params, dict):
        condition_source = ""
        condition_confidence = None
        condition_missing_frames = None
        condition_continuity_score = None
        batch_frames = 0
        if technique_key == "saxs":
            condition_source = str(params.get("condition_source") or "").strip()
            condition_confidence = gui_coerce_summary_float(params.get("condition_confidence"))
            condition_missing_frames = params.get("condition_missing_frames")
            condition_continuity_score = gui_coerce_summary_float(params.get("condition_continuity_score"))
            try:
                batch_frames = int(params.get("batch_frames", 0) or 0)
            except (TypeError, ValueError):
                batch_frames = 0
            if (
                batch_frames > 1
                and (
                    condition_source
                    or condition_confidence is not None
                    or condition_missing_frames not in (None, [], {})
                    or condition_continuity_score is not None
                )
            ):
                confidence_text = (
                    f"{condition_confidence:.2f}"
                    if condition_confidence is not None
                    else tr("AI_TUNING_EMPTY_VALUE")
                )
                continuity_text = (
                    f"{condition_continuity_score:.2f}"
                    if condition_continuity_score is not None
                    else tr("AI_TUNING_EMPTY_VALUE")
                )
                missing_text = gui_display_text_value(condition_missing_frames, empty_text=tr("AI_TUNING_EMPTY_VALUE"))
                return tr(
                    "RESULTS_SUMMARY_RISK_CONDITION_AXIS",
                    condition_source or tr("AI_TUNING_EMPTY_VALUE"),
                    confidence_text,
                    missing_text,
                    continuity_text,
                )
        strain_risk_text = saxs_strain_risk_summary_text(
            params,
            evidence,
            symptom_names=symptom_names,
            language=language,
        )
        if strain_risk_text:
            return strain_risk_text
        if not validation_summary:
            lc_status_text = _saxs_lc_status_summary_text(params, evidence)
            if lc_status_text:
                return lc_status_text
            validation_summary = str(params.get("validation_summary") or "").strip()
        if not validation_warnings and isinstance(params.get("validation_warnings"), list):
            validation_warnings = [str(item) for item in params.get("validation_warnings") or [] if str(item).strip()]
        if not quality_flags and isinstance(params.get("quality_flags"), dict):
            quality_flags = dict(params.get("quality_flags") or {})
        if params.get("validation_summary"):
            display = str(params.get("validation_summary") or "").strip()
            if validation_warnings:
                detail = ", ".join(validation_warnings[:4])
                if detail:
                    display = f"{display} | {detail}"
            return tr("RESULTS_SUMMARY_RISK_VALIDATION", display)

    if validation_summary and validation_summary != "All checks passed":
        detail_items = validation_warnings or [
            str(key)
            for key, flag in quality_flags.items()
            if str(flag).upper() == "WARN"
        ]
        if detail_items:
            detail = ", ".join(detail_items[:4])
            validation_summary = f"{validation_summary} | {detail}"
        return tr("RESULTS_SUMMARY_RISK_VALIDATION", validation_summary)

    return ""


def results_next_step_text(
    params,
    result=None,
    *,
    mode: str,
    technique: str,
    analysis_evidence: dict | None = None,
    language: str = "en",
) -> str:
    technique_key = str(technique or "").strip().lower()
    evidence = analysis_evidence if isinstance(analysis_evidence, dict) else {}
    symptom_names = _evidence_symptom_names(evidence)
    condition_axis_risk = has_condition_axis_risk(
        params,
        analysis_evidence=evidence,
        symptom_names=symptom_names,
    )
    fallback_conflict_risk = has_fallback_conflict_risk(symptom_names)
    waxs_structure = _waxs_structure_evidence(evidence) if technique_key == "waxs" else {}
    waxs_support = _waxs_support_snapshot(evidence) if technique_key == "waxs" else {}
    has_risk = results_has_critical_risk(
        params,
        technique=technique_key,
        result=result,
        analysis_evidence=evidence,
        condition_axis_risk=condition_axis_risk,
        fallback_conflict_risk=fallback_conflict_risk,
        waxs_structure=waxs_structure,
        waxs_support=waxs_support,
    )

    if technique_key == "saxs":
        if fallback_conflict_risk:
            return tr("RESULTS_SUMMARY_NEXT_FALLBACK_CONFLICT")
        if condition_axis_risk:
            return tr("RESULTS_SUMMARY_NEXT_CONDITION_AXIS")
        strain_next_text = saxs_strain_next_step_text(
            params,
            evidence,
            symptom_names=symptom_names,
            language=language,
        )
        if strain_next_text:
            return strain_next_text
        if _saxs_lc_status_summary_text(params, evidence):
            return tr("RESULTS_SUMMARY_NEXT_SAXS_LC_STATUS")

    translation_key = results_next_step_translation_key(
        params,
        mode=mode,
        technique=technique_key,
        has_risk=has_risk,
        has_result=result is not None,
    )
    if translation_key:
        return tr(translation_key)
    return ""


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

    source_summary = str(snapshot.get("source_summary") or "").strip()
    if source_summary:
        parts.append(source_summary)

    if technique == "waxs":
        waxs_core_text = str(snapshot.get("waxs_core_text") or "").strip()
        if waxs_core_text:
            parts.append(tr("WAXS_REVIEW_CORE", waxs_core_text))
        waxs_support_text = str(snapshot.get("waxs_support_text") or "").strip()
        if waxs_support_text:
            parts.append(tr("WAXS_REVIEW_SUPPORT", waxs_support_text))
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
            parts.append(f"SAXS | {saxs_strain_text}")
        saxs_method_bits = snapshot.get("saxs_method_bits") if isinstance(snapshot.get("saxs_method_bits"), list) else []
        method_bits = [str(bit or "").strip() for bit in saxs_method_bits if str(bit or "").strip()]
        if method_bits:
            parts.append("SAXS | " + ", ".join(method_bits[:3]))

    fallback_text = str(snapshot.get("fallback_text") or "").strip()
    if fallback_text:
        parts.append(fallback_text)

    optimization_parts = snapshot.get("optimization_parts")
    if isinstance(optimization_parts, ControlledOptimizationReviewParts):
        if optimization_parts.tuning_goal:
            parts.append(tr("RESULTS_REVIEW_TUNING_GOAL", optimization_parts.tuning_goal))
        if optimization_parts.benchmark_text:
            parts.append(optimization_parts.benchmark_text)
        if optimization_parts.stop_reason:
            parts.append(optimization_parts.stop_reason)
        if optimization_parts.remaining_risks:
            parts.append(optimization_parts.remaining_risks)
        if optimization_parts.next_goal:
            parts.append(optimization_parts.next_goal)
        if not optimization_parts.benchmark_text:
            parts.append(tr("RESULTS_REVIEW_NO_BENCHMARK"))
        if not optimization_parts.stop_reason and not optimization_parts.remaining_risks:
            parts.append(tr("RESULTS_REVIEW_NO_RISK"))

        chain_text = str(snapshot.get("chain_text") or "").strip()
        if chain_text:
            parts.append(chain_text)

        joint_summary = str(snapshot.get("joint_summary") or "").strip()
        joint_reminder_text = str(snapshot.get("joint_reminder_text") or "").strip()
        joint_parts = [part for part in [joint_summary, joint_reminder_text] if part]
        if joint_parts:
            parts.append(" | ".join(joint_parts))

    boundary_text = str(snapshot.get("responsibility_boundary") or "").strip()
    if boundary_text:
        parts.append(boundary_text)

    return " | ".join(parts)
