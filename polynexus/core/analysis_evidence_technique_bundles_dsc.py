from __future__ import annotations

from typing import Any

from .analysis_evidence_dsc import _dsc_feature_bundle
from .analysis_evidence_utils import _clean_float, _safe_int


def build_dsc_technique_bundle(
    output: dict[str, Any],
    validation: dict[str, Any],
    *,
    validation_summary: str,
    residual_type: str,
    residual_summary: str,
    feature_evidence: dict[str, Any],
) -> dict[str, Any]:
    feature_evidence = dict(feature_evidence)
    dsc_bundle = _dsc_feature_bundle(
        output,
        validation,
        validation_summary=validation_summary,
        residual_type=residual_type,
        residual_summary=residual_summary,
    )
    physical_evidence = dict(dsc_bundle.get("physical_evidence", {}))
    feature_evidence.update(dsc_bundle.get("feature_evidence", {}))
    peak_evidence = dsc_bundle.get("peak_evidence", {})
    confidence_signals = list(dsc_bundle.get("confidence_signals", []))
    scan_mode = str(dsc_bundle.get("scan_mode", "") or "")
    exo_up = dsc_bundle.get("exo_up")
    dhm_mean = _clean_float(dsc_bundle.get("dhm_mean"))
    dhm_std = _clean_float(dsc_bundle.get("dhm_std"))
    dhcc_mean = _clean_float(dsc_bundle.get("dhcc_mean"))
    dhcc_std = _clean_float(dsc_bundle.get("dhcc_std"))
    xc_mean = _clean_float(dsc_bundle.get("xc_mean"))
    xc_std = _clean_float(dsc_bundle.get("xc_std"))
    xc_ci95 = _clean_float(dsc_bundle.get("xc_ci95"))
    xc_reliability_status = str(dsc_bundle.get("xc_reliability_status", "") or "")
    baseline_sensitivity = _clean_float(
        dsc_bundle.get("feature_evidence", {}).get("baseline_evidence", {}).get("baseline_sensitivity_pct")
    )
    boundary_sensitivity = _clean_float(
        dsc_bundle.get("feature_evidence", {}).get("baseline_evidence", {}).get("integration_boundary_sensitivity_pct")
    )
    baseline_variant_count = _safe_int(
        dsc_bundle.get("feature_evidence", {}).get("crystallinity_evidence", {}).get("baseline_variant_count"),
        default=0,
    )
    integration_variant_count = _safe_int(
        dsc_bundle.get("feature_evidence", {}).get("crystallinity_evidence", {}).get("integration_variant_count"),
        default=0,
    )
    dhm0_source = str(dsc_bundle.get("dhm0_source", "") or "") or None
    supported_components = dsc_bundle.get("supported_components", [])
    supported_melting_components = dsc_bundle.get("supported_melting_components", [])
    supported_crystallization_components = dsc_bundle.get("supported_crystallization_components", [])
    supported_event_fraction = _clean_float(dsc_bundle.get("supported_event_fraction"))
    event_support_score = _clean_float(dsc_bundle.get("event_support_score"))
    baseline_stability_score = _clean_float(dsc_bundle.get("baseline_stability_score"))
    thermodynamic_consistency_score = _clean_float(dsc_bundle.get("thermodynamic_consistency_score"))
    scan_r_squared_median = _clean_float(dsc_bundle.get("scan_r_squared_median"))
    scan_r_squared_spread = _clean_float(dsc_bundle.get("scan_r_squared_spread"))
    structure_support_score = _clean_float(dsc_bundle.get("structure_support_score"))
    _ = (
        scan_mode,
        exo_up,
        dhm_mean,
        dhm_std,
        dhcc_mean,
        dhcc_std,
        xc_mean,
        xc_std,
        xc_ci95,
        xc_reliability_status,
        baseline_sensitivity,
        boundary_sensitivity,
        baseline_variant_count,
        integration_variant_count,
        dhm0_source,
        supported_components,
        supported_melting_components,
        supported_crystallization_components,
        supported_event_fraction,
        event_support_score,
        baseline_stability_score,
        thermodynamic_consistency_score,
        scan_r_squared_median,
        scan_r_squared_spread,
        structure_support_score,
    )
    return {
        "dsc_bundle": dsc_bundle,
        "physical_evidence": physical_evidence,
        "feature_evidence": feature_evidence,
        "peak_evidence": peak_evidence,
        "confidence_signals": confidence_signals,
    }
