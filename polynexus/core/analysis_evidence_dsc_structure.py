from __future__ import annotations

from typing import Any

from .analysis_evidence_utils import _clean_float, _non_empty_mapping, _safe_int


def _dsc_structure_evidence(
    output: dict[str, Any],
    *,
    feature_bundle: dict[str, Any],
    constraint_summary: dict[str, Any] | None = None,
    hard_fail_names: set[str] | None = None,
) -> dict[str, Any]:
    constraint_summary = dict(constraint_summary or {})
    hard_fail_names = set(hard_fail_names or set())

    feature_evidence = feature_bundle.get("feature_evidence", {})
    baseline_evidence = feature_evidence.get("baseline_evidence", {}) if isinstance(feature_evidence, dict) else {}
    crystallinity_evidence = feature_evidence.get("crystallinity_evidence", {}) if isinstance(feature_evidence, dict) else {}

    scan_mode = str(feature_bundle.get("scan_mode", "") or "") or None
    exo_up = feature_bundle.get("exo_up")
    dhm_mean = _clean_float(feature_bundle.get("dhm_mean"))
    dhm_std = _clean_float(feature_bundle.get("dhm_std"))
    dhcc_mean = _clean_float(feature_bundle.get("dhcc_mean"))
    dhcc_std = _clean_float(feature_bundle.get("dhcc_std"))
    xc_mean = _clean_float(feature_bundle.get("xc_mean"))
    xc_std = _clean_float(feature_bundle.get("xc_std"))
    xc_ci95 = _clean_float(feature_bundle.get("xc_ci95"))
    xc_reliability_status = str(feature_bundle.get("xc_reliability_status", "") or "") or None
    baseline_sensitivity = _clean_float(
        baseline_evidence.get("baseline_sensitivity_pct") if isinstance(baseline_evidence, dict) else None
    )
    boundary_sensitivity = _clean_float(
        baseline_evidence.get("integration_boundary_sensitivity_pct") if isinstance(baseline_evidence, dict) else None
    )
    baseline_variant_count = (
        _safe_int(crystallinity_evidence.get("baseline_variant_count"), default=0)
        if isinstance(crystallinity_evidence, dict)
        else 0
    )
    integration_variant_count = (
        _safe_int(crystallinity_evidence.get("integration_variant_count"), default=0)
        if isinstance(crystallinity_evidence, dict)
        else 0
    )
    dhm0_source = str(feature_bundle.get("dhm0_source", "") or "") or None
    supported_components = feature_bundle.get("supported_components", [])
    supported_melting_components = feature_bundle.get("supported_melting_components", [])
    supported_crystallization_components = feature_bundle.get("supported_crystallization_components", [])
    supported_event_fraction = _clean_float(feature_bundle.get("supported_event_fraction"))
    event_support_score = _clean_float(feature_bundle.get("event_support_score"))
    baseline_stability_score = _clean_float(feature_bundle.get("baseline_stability_score"))
    thermodynamic_consistency_score = _clean_float(feature_bundle.get("thermodynamic_consistency_score"))
    scan_r_squared_median = _clean_float(feature_bundle.get("scan_r_squared_median"))
    scan_r_squared_spread = _clean_float(feature_bundle.get("scan_r_squared_spread"))
    structure_support_score = _clean_float(feature_bundle.get("structure_support_score"))

    return _non_empty_mapping(
        [
            ("scan_mode", scan_mode),
            ("exo_up", exo_up if exo_up is not None else None),
            ("Tg_C", _clean_float(output.get("Tg_C"))),
            ("Tm_peak_C", _clean_float(output.get("Tm_peak_C"))),
            ("Tcc_peak_C", _clean_float(output.get("Tcc_peak_C"))),
            ("DHm_Jg", _clean_float(output.get("DHm_Jg"))),
            ("DHm_Jg_mean", dhm_mean),
            ("DHm_Jg_std", dhm_std),
            ("DHcc_Jg", _clean_float(output.get("DHcc_Jg"))),
            ("DHcc_Jg_mean", dhcc_mean),
            ("DHcc_Jg_std", dhcc_std),
            ("Xc_pct", _clean_float(output.get("Xc_pct"))),
            ("Xc_pct_mean", xc_mean),
            ("Xc_pct_std", xc_std),
            ("Xc_pct_ci95", xc_ci95),
            ("Xc_reliability_status", xc_reliability_status),
            ("baseline_sensitivity_pct", baseline_sensitivity),
            ("integration_boundary_sensitivity_pct", boundary_sensitivity),
            ("baseline_variant_count", baseline_variant_count if baseline_variant_count > 0 else None),
            ("integration_variant_count", integration_variant_count if integration_variant_count > 0 else None),
            ("DHm0_source", dhm0_source),
            ("supported_event_count", len(supported_components)),
            ("supported_melting_event_count", len(supported_melting_components)),
            ("supported_crystallization_event_count", len(supported_crystallization_components)),
            ("supported_event_fraction", supported_event_fraction),
            ("event_support_score", event_support_score),
            ("baseline_stability_score", baseline_stability_score),
            ("thermodynamic_consistency_score", thermodynamic_consistency_score),
            ("scan_r_squared_median", scan_r_squared_median),
            ("scan_r_squared_spread", scan_r_squared_spread),
            ("structure_support_score", structure_support_score),
            (
                "physical_support_pass",
                bool(
                    len(supported_components) >= 1
                    and len(supported_melting_components) >= 1
                    and (event_support_score or 0.0) >= 0.75
                    and (baseline_stability_score or 0.0) >= 0.55
                    and (thermodynamic_consistency_score or 0.0) >= 0.55
                    and constraint_summary.get("status") != "hard_fail"
                ),
            ),
            ("constraint_status", constraint_summary.get("status")),
            ("triggered_constraint_count", constraint_summary.get("triggered_total")),
            (
                "paper_conclusion_candidate",
                bool(
                    (structure_support_score or 0.0) >= 0.82
                    and (event_support_score or 0.0) >= 0.85
                    and (baseline_stability_score or 0.0) >= 0.65
                    and (thermodynamic_consistency_score or 0.0) >= 0.65
                    and len(supported_components) >= 2
                    and len(supported_melting_components) >= 1
                    and (scan_r_squared_median is None or scan_r_squared_median >= 0.85)
                    and (scan_r_squared_spread is None or scan_r_squared_spread <= 0.08)
                    and constraint_summary.get("status") != "hard_fail"
                ),
            ),
            (
                "paper_conclusion_ready",
                bool(
                    (structure_support_score or 0.0) >= 0.88
                    and (event_support_score or 0.0) >= 0.88
                    and (baseline_stability_score or 0.0) >= 0.75
                    and (thermodynamic_consistency_score or 0.0) >= 0.75
                    and len(supported_components) >= 2
                    and len(supported_melting_components) >= 1
                    and (scan_r_squared_median is None or scan_r_squared_median >= 0.90)
                    and (scan_r_squared_spread is None or scan_r_squared_spread <= 0.05)
                    and constraint_summary.get("status") == "ok"
                    and not hard_fail_names
                ),
            ),
        ]
    )


__all__ = ["_dsc_structure_evidence"]
