from __future__ import annotations

from typing import Any

from .analysis_evidence_dsc_feature_context import _dsc_feature_context
from .analysis_evidence_dsc_feature_support import _dsc_feature_support_bundle


def _dsc_feature_bundle(
    output: dict[str, Any],
    validation: dict[str, Any] | None = None,
    *,
    validation_summary: str = "",
    residual_type: str = "",
    residual_summary: str = "",
) -> dict[str, Any]:
    context = _dsc_feature_context(
        output,
        validation,
        validation_summary=validation_summary,
        residual_type=residual_type,
        residual_summary=residual_summary,
    )
    support_bundle = _dsc_feature_support_bundle(output, context)
    feature_evidence = dict(context["feature_evidence"])
    confidence_signals = list(context["confidence_signals"])
    if support_bundle["event_support_evidence"]:
        feature_evidence["event_support_evidence"] = support_bundle["event_support_evidence"]
        confidence_signals.extend(support_bundle["confidence_signals"])

    return {
        "physical_evidence": context["physical_evidence"],
        "feature_evidence": feature_evidence,
        "thermal_event_evidence": context["thermal_event_evidence"],
        "scan_evidence": context["scan_evidence"],
        "baseline_evidence": context["baseline_evidence"],
        "crystallinity_evidence": context["crystallinity_evidence"],
        "peak_evidence": context["peak_evidence"],
        "confidence_signals": confidence_signals,
        "peak_components": context["peak_components"],
        "scan_rows": context["scan_rows"],
        "scan_mode": context["scan_mode"],
        "baseline_corr": context["baseline_corr"],
        "exo_up": context["exo_up"],
        "peak_function": context["peak_function"],
        "min_event_enthalpy": context["min_event_enthalpy"],
        "dhm0_source": context["dhm0_source"],
        "dhm_mean": context["dhm_mean"],
        "dhm_std": context["dhm_std"],
        "dhcc_mean": context["dhcc_mean"],
        "dhcc_std": context["dhcc_std"],
        "xc_mean": context["xc_mean"],
        "xc_std": context["xc_std"],
        "xc_ci95": context["xc_ci95"],
        "xc_reliability_status": context["xc_reliability_status"],
        "supported_components": context["supported_components"],
        "supported_melting_components": context["supported_melting_components"],
        "supported_crystallization_components": context["supported_crystallization_components"],
        "event_support_score": support_bundle["event_support_score"],
        "baseline_stability_score": support_bundle["baseline_stability_score"],
        "thermodynamic_consistency_score": support_bundle["thermodynamic_consistency_score"],
        "scan_r_squared_median": context["scan_r_squared_median"],
        "scan_r_squared_spread": context["scan_r_squared_spread"],
        "supported_event_fraction": support_bundle["supported_event_fraction"],
        "structure_support_score": support_bundle["structure_support_score"],
    }


__all__ = [
    "_dsc_feature_context",
    "_dsc_feature_support_bundle",
    "_dsc_feature_bundle",
]
