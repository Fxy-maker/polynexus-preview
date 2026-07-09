from __future__ import annotations

from typing import Any

from .analysis_evidence_saxs_post_stability_score import (
    _clean_float,
    _clamp_unit,
    _non_empty_mapping,
    _safe_int,
    _saxs_stability_core_scores,
)
from .analysis_evidence_saxs_post_stability_strain import _saxs_stability_strain_adjustments
from .saxs_symptom_detector import symptom_bridge_lines


def _saxs_post_analysis_bundle(
    output: dict[str, Any],
    *,
    symptoms: list[dict[str, Any]] | None = None,
    constraint_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    symptoms = symptoms if isinstance(symptoms, list) else []
    constraint_summary = dict(constraint_summary or {})
    stability_evidence = _build_saxs_stability_evidence(output, symptoms=symptoms)
    feature_evidence: dict[str, Any] = {}
    confidence_signals: list[dict[str, Any]] = []
    actionable_symptoms: list[str] = []

    if stability_evidence:
        feature_evidence["stability_evidence"] = stability_evidence
        for key in (
            "stability_score",
            "parameter_stability_score",
            "method_agreement_score",
            "batch_continuity_score",
        ):
            if stability_evidence.get(key) is not None:
                confidence_signals.append(
                    {
                        "name": key,
                        "value": _clean_float(stability_evidence.get(key)),
                        "source": "SAXS_stability",
                    }
                )

    for symptom in symptoms:
        actionable_symptoms.extend(symptom_bridge_lines(symptom))

    triggered_names = constraint_summary.get("triggered_names", {}) if isinstance(constraint_summary, dict) else {}
    soft_warn_names = triggered_names.get("soft_warn", []) if isinstance(triggered_names, dict) else []
    if "fit_regions_unstable" in soft_warn_names and not any(
        "fit_regions_unstable" in str(item) for item in actionable_symptoms
    ):
        actionable_symptoms.append(
            "fit_regions_unstable -> do not trust pretty figures; stabilize preprocessing before another AI round"
        )

    return {
        "stability_evidence": stability_evidence,
        "feature_evidence": feature_evidence,
        "confidence_signals": confidence_signals,
        "actionable_symptoms": actionable_symptoms,
    }


def _build_saxs_stability_evidence(
    output: dict[str, Any],
    *,
    symptoms: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    symptom_names = {
        str(item.get("name", "")).strip()
        for item in (symptoms or [])
        if isinstance(item, dict) and str(item.get("name", "")).strip()
    }
    core_scores = _saxs_stability_core_scores(output, symptom_names)
    adjusted_scores = _saxs_stability_strain_adjustments(output, core_scores)

    parameter_stability_score = float(adjusted_scores["parameter_stability_score"])
    method_agreement_score = float(adjusted_scores["method_agreement_score"])
    batch_continuity_score = _clamp_unit(adjusted_scores["batch_continuity_score"], default=0.0)
    condition_label = str(adjusted_scores.get("condition_label", "") or "").strip().lower()
    stability_score = _clamp_unit(
        0.45 * parameter_stability_score
        + 0.35 * method_agreement_score
        + 0.20 * batch_continuity_score,
        default=0.0,
    )

    flags: list[str] = []
    if parameter_stability_score < 0.55:
        flags.append("parameter_stability_low")
    if method_agreement_score < 0.60:
        flags.append("method_agreement_low")
    if batch_continuity_score < 0.65:
        flags.append("batch_continuity_low")
    if stability_score < 0.60:
        flags.append("stability_low")
    if condition_label == "strain":
        strain_status = str(output.get("strain_reliability_status", "") or "").strip().lower()
        if strain_status == "low_confidence":
            flags.append("strain_reliability_low")
        elif strain_status == "diagnostic_only":
            flags.append("strain_reliability_diagnostic")
        if _safe_int(output.get("phase_ambiguous_frame_count"), default=0) > 0:
            flags.append("phase_ambiguous")
        if _safe_int(output.get("void_dominant_frame_count"), default=0) > 0:
            flags.append("void_dominant")

    return _non_empty_mapping(
        [
            ("stability_score", round(stability_score, 3)),
            ("parameter_stability_score", round(parameter_stability_score, 3)),
            ("method_agreement_score", round(method_agreement_score, 3)),
            ("batch_continuity_score", round(batch_continuity_score, 3)),
            ("stability_flags", flags),
            ("l_method_relative_spread", round(float(core_scores["l_spread"]), 4) if core_scores["l_spread"] is not None else None),
            ("lc_method_relative_spread", round(float(core_scores["lc_spread"]), 4) if core_scores["lc_spread"] is not None else None),
            ("phi_method_relative_spread", round(float(core_scores["phi_spread"]), 4) if core_scores["phi_spread"] is not None else None),
            ("condition_continuity_score", core_scores["condition_continuity_score"]),
            ("condition_frame_coverage", round(float(core_scores["coverage_score"]), 3) if core_scores["coverage_score"] is not None else None),
            ("strain_reliability_status", str(output.get("strain_reliability_status", "") or "").strip() or None),
            ("strain_reliability_reason", str(output.get("strain_reliability_reason", "") or "").strip() or None),
            (
                "phase_ambiguous_frame_count",
                _safe_int(output.get("phase_ambiguous_frame_count"), default=0)
                if output.get("phase_ambiguous_frame_count") is not None
                else None,
            ),
            (
                "frame_low_conf_count",
                _safe_int(output.get("frame_low_conf_count"), default=0)
                if output.get("frame_low_conf_count") is not None
                else None,
            ),
            (
                "void_dominant_frame_count",
                _safe_int(output.get("void_dominant_frame_count"), default=0)
                if output.get("void_dominant_frame_count") is not None
                else None,
            ),
            ("effective_param_ratio", _clean_float(output.get("effective_param_ratio"))),
        ]
    )


__all__ = [
    "_saxs_stability_core_scores",
    "_saxs_stability_strain_adjustments",
    "_build_saxs_stability_evidence",
    "_saxs_post_analysis_bundle",
]
