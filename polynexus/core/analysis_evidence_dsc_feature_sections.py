from __future__ import annotations

from typing import Any

from .analysis_evidence_utils import (
    _clean_float,
    _mean_finite,
    _non_empty_mapping,
    _relative_spread,
    _safe_int,
)


def _dsc_feature_evidence_sections(
    output: dict[str, Any],
    context: dict[str, Any],
    *,
    validation_summary: str = "",
    residual_type: str = "",
    residual_summary: str = "",
) -> dict[str, Any]:
    peak_components = context["peak_components"]
    scan_rows = context["scan_rows"]
    scan_mode = context["scan_mode"]
    baseline_corr = context["baseline_corr"]
    exo_up = context["exo_up"]
    tg_method = context["tg_method"]
    tg_low = context["tg_low"]
    tg_high = context["tg_high"]
    tm_low = context["tm_low"]
    tm_high = context["tm_high"]
    tc_low = context["tc_low"]
    tc_high = context["tc_high"]
    peak_function = context["peak_function"]
    peak_prominence_ratio = context["peak_prominence_ratio"]
    min_event_enthalpy = context["min_event_enthalpy"]
    max_melting_peak_width = context["max_melting_peak_width"]
    dhm0 = context["dhm0"]
    dhm0_source = context["dhm0_source"]
    baseline_sensitivity = context["baseline_sensitivity"]
    boundary_sensitivity = context["boundary_sensitivity"]
    dhm_mean = context["dhm_mean"]
    dhm_std = context["dhm_std"]
    dhcc_mean = context["dhcc_mean"]
    dhcc_std = context["dhcc_std"]
    xc_mean = context["xc_mean"]
    xc_std = context["xc_std"]
    xc_ci95 = context["xc_ci95"]
    baseline_variant_count = context["baseline_variant_count"]
    integration_variant_count = context["integration_variant_count"]
    xc_reliability_status = context["xc_reliability_status"]
    supported_components = context["supported_components"]
    supported_melting_components = context["supported_melting_components"]
    supported_crystallization_components = context["supported_crystallization_components"]
    config_snapshot = context["config_snapshot"]

    thermal_event_evidence = _non_empty_mapping(
        [
            ("scan_mode", scan_mode or None),
            ("exo_up", exo_up if exo_up is not None else None),
            ("Tg_C", _clean_float(output.get("Tg_C"))),
            ("Tg_method", tg_method),
            ("Tg_search_low_C", tg_low),
            ("Tg_search_high_C", tg_high),
            ("DTg_C", _clean_float(output.get("DTg_C"))),
            ("DCp_JgK", _clean_float(output.get("DCp_JgK"))),
            ("Tm_onset_C", _clean_float(output.get("Tm_onset_C"))),
            ("Tm_peak_C", _clean_float(output.get("Tm_peak_C"))),
            ("Tm_end_C", _clean_float(output.get("Tm_end_C"))),
            ("Tm_search_low_C", tm_low),
            ("Tm_search_high_C", tm_high),
            ("Tc_onset_C", _clean_float(output.get("Tc_onset_C"))),
            ("Tc_peak_C", _clean_float(output.get("Tc_peak_C"))),
            ("Tc_end_C", _clean_float(output.get("Tc_end_C"))),
            ("Tc_search_low_C", tc_low),
            ("Tc_search_high_C", tc_high),
            ("Tcc_onset_C", _clean_float(output.get("Tcc_onset_C"))),
            ("Tcc_peak_C", _clean_float(output.get("Tcc_peak_C"))),
            ("DHm_Jg", _clean_float(output.get("DHm_Jg"))),
            ("DHc_Jg", _clean_float(output.get("DHc_Jg"))),
            ("DHcc_Jg", _clean_float(output.get("DHcc_Jg"))),
            ("peak_components", peak_components if peak_components else None),
            ("supported_event_count", len(supported_components)),
            ("supported_melting_event_count", len(supported_melting_components)),
            ("supported_crystallization_event_count", len(supported_crystallization_components)),
            ("n_peaks", _safe_int(output.get("n_peaks"), default=len(peak_components))),
        ]
    )
    scan_r_squared_median = _clean_float(_mean_finite([row.get("r_squared") for row in scan_rows]))
    scan_r_squared_spread = _relative_spread([row.get("r_squared") for row in scan_rows])
    scan_evidence = _non_empty_mapping(
        [
            ("scan_mode", scan_mode or None),
            ("scan_r_squared", scan_rows if scan_rows else None),
            ("scan_r_squared_median", scan_r_squared_median),
            ("scan_r_squared_spread", scan_r_squared_spread),
            ("scan_count", len(scan_rows)),
            ("r_squared_method", str(output.get("r_squared_method", "") or "").strip() or None),
        ]
    )
    baseline_evidence = _non_empty_mapping(
        [
            ("baseline_corr", baseline_corr),
            ("smooth_window", _clean_float(output.get("smooth_window", config_snapshot.get("smooth_window")))),
            ("exo_up", exo_up if exo_up is not None else None),
            ("Tg_method", tg_method),
            ("peak_function", peak_function),
            ("quality_flags", output.get("quality_flags")),
            ("validation_summary", validation_summary or None),
            ("residual_type", residual_type or None),
            ("residual_summary", residual_summary or None),
            ("peak_prominence_ratio", peak_prominence_ratio),
            ("min_event_enthalpy_Jg", min_event_enthalpy),
            ("baseline_sensitivity_pct", baseline_sensitivity),
            ("integration_boundary_sensitivity_pct", boundary_sensitivity),
        ]
    )
    crystallinity_evidence = _non_empty_mapping(
        [
            ("Xc_pct", _clean_float(output.get("Xc_pct"))),
            ("Xc_method", str(output.get("Xc_method", "") or "").strip() or None),
            ("DHm0_Jg", dhm0),
            ("DHm0_source", dhm0_source),
            ("DHm_Jg", _clean_float(output.get("DHm_Jg"))),
            ("DHm_Jg_mean", dhm_mean),
            ("DHm_Jg_std", dhm_std),
            ("DHcc_Jg", _clean_float(output.get("DHcc_Jg"))),
            ("DHcc_Jg_mean", dhcc_mean),
            ("DHcc_Jg_std", dhcc_std),
            ("Xc_pct_mean", xc_mean),
            ("Xc_pct_std", xc_std),
            ("Xc_pct_ci95", xc_ci95),
            ("baseline_sensitivity_pct", baseline_sensitivity),
            ("integration_boundary_sensitivity_pct", boundary_sensitivity),
            ("baseline_variant_count", baseline_variant_count if baseline_variant_count > 0 else None),
            ("integration_variant_count", integration_variant_count if integration_variant_count > 0 else None),
            ("Xc_reliability_status", xc_reliability_status),
        ]
    )
    peak_evidence = _non_empty_mapping(
        [
            ("peak_components", peak_components if peak_components else None),
            (
                "peak_component_types",
                sorted(
                    {
                        str(row.get("type", "") or "").strip().lower()
                        for row in peak_components
                        if str(row.get("type", "") or "").strip()
                    }
                )
                or None,
            ),
            ("peak_component_count", len(peak_components)),
            ("supported_component_count", len(supported_components)),
            ("supported_melting_component_count", len(supported_melting_components)),
            ("supported_crystallization_component_count", len(supported_crystallization_components)),
            ("Tm_peak_C", _clean_float(output.get("Tm_peak_C"))),
            ("Tm_onset_C", _clean_float(output.get("Tm_onset_C"))),
            ("Tm_end_C", _clean_float(output.get("Tm_end_C"))),
            ("Tc_peak_C", _clean_float(output.get("Tc_peak_C"))),
            ("Tcc_peak_C", _clean_float(output.get("Tcc_peak_C"))),
            ("max_melting_peak_width_C", max_melting_peak_width),
        ]
    )

    feature_evidence: dict[str, Any] = {
        "scan_evidence": scan_evidence,
        "thermal_event_evidence": thermal_event_evidence,
        "baseline_evidence": baseline_evidence,
        "crystallinity_evidence": crystallinity_evidence,
        "peak_evidence": peak_evidence,
        "peak_components": peak_components if peak_components else output.get("peak_components", []),
    }
    for key in (
        "Tm_peak_C",
        "Tm_onset_C",
        "Tm_end_C",
        "Tc_peak_C",
        "Tc_onset_C",
        "Tc_end_C",
        "Tcc_peak_C",
        "Tcc_onset_C",
        "Tg_C",
        "Tg_method",
        "DTg_C",
        "DCp_JgK",
        "Xc_pct",
        "Xc_method",
        "DHm_Jg",
        "DHc_Jg",
        "DHcc_Jg",
        "quality_score",
        "scan_r_squared",
        "scan_mode",
        "r_squared_method",
        "n_peaks",
        "peak_function",
    ):
        if key in output:
            feature_evidence[key] = output.get(key)

    physical_evidence: dict[str, Any] = {}
    if output.get("quality_flags") is not None:
        physical_evidence["quality_flags"] = output.get("quality_flags")

    confidence_signals: list[dict[str, Any]] = []
    if output.get("scan_r_squared") is not None:
        confidence_signals.append({"name": "scan_r_squared", "value": output.get("scan_r_squared"), "source": "DSC"})
    if output.get("quality_score") is not None:
        confidence_signals.append(
            {"name": "quality_score", "value": _clean_float(output.get("quality_score")), "source": "DSC"}
        )
    if scan_rows:
        confidence_signals.append(
            {
                "name": "scan_r_squared_median",
                "value": scan_r_squared_median,
                "source": "DSC",
            }
        )

    quality_flags_payload = output.get("quality_flags")
    if isinstance(quality_flags_payload, dict):
        quality_flag_text = " ".join(f"{key}:{value}" for key, value in quality_flags_payload.items()).strip().lower()
    elif isinstance(quality_flags_payload, list):
        quality_flag_text = " ".join(str(value) for value in quality_flags_payload).strip().lower()
    else:
        quality_flag_text = str(quality_flags_payload or "").strip().lower()

    return {
        "thermal_event_evidence": thermal_event_evidence,
        "scan_evidence": scan_evidence,
        "baseline_evidence": baseline_evidence,
        "crystallinity_evidence": crystallinity_evidence,
        "peak_evidence": peak_evidence,
        "feature_evidence": feature_evidence,
        "physical_evidence": physical_evidence,
        "confidence_signals": confidence_signals,
        "scan_r_squared_median": scan_r_squared_median,
        "scan_r_squared_spread": scan_r_squared_spread,
        "quality_flag_text": quality_flag_text,
    }


__all__ = ["_dsc_feature_evidence_sections"]
