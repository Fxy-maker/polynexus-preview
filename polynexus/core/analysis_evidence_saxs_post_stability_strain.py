from __future__ import annotations

from typing import Any

from .analysis_evidence_saxs_post_stability_score import _clean_float, _safe_int


def _saxs_stability_strain_adjustments(
    output: dict[str, Any],
    scores: dict[str, Any],
) -> dict[str, Any]:
    adjusted = dict(scores)
    condition_label = str(adjusted.get("condition_label", "") or "").strip().lower()
    if condition_label != "strain":
        return adjusted

    parameter_stability_score = float(adjusted.get("parameter_stability_score", 0.0))
    method_agreement_score = float(adjusted.get("method_agreement_score", 0.0))
    batch_continuity_score = float(adjusted.get("batch_continuity_score", 0.0))

    strain_status = str(output.get("strain_reliability_status", "") or "").strip().lower()
    phase_ambiguous_frame_count = _safe_int(output.get("phase_ambiguous_frame_count"), default=0)
    frame_low_conf_count = _safe_int(output.get("frame_low_conf_count"), default=0)
    void_dominant_frame_count = _safe_int(output.get("void_dominant_frame_count"), default=0)
    effective_param_ratio = _clean_float(output.get("effective_param_ratio"))
    if strain_status == "diagnostic_only":
        parameter_stability_score -= 0.12
        batch_continuity_score -= 0.05
    elif strain_status == "low_confidence":
        parameter_stability_score -= 0.06
    if phase_ambiguous_frame_count > 0:
        method_agreement_score -= 0.06
    if void_dominant_frame_count > 0:
        method_agreement_score -= 0.05
    if frame_low_conf_count > 0:
        batch_continuity_score -= 0.04
    if effective_param_ratio is not None and effective_param_ratio < 0.55:
        batch_continuity_score -= 0.05

    adjusted["parameter_stability_score"] = parameter_stability_score
    adjusted["method_agreement_score"] = method_agreement_score
    adjusted["batch_continuity_score"] = batch_continuity_score
    return adjusted


__all__ = ["_saxs_stability_strain_adjustments"]
