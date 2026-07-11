from __future__ import annotations

from typing import Any

from .analysis_evidence_dsc_rows import _dsc_peak_component_rows, _dsc_scan_rows
from .analysis_evidence_dsc_feature_sections import _dsc_feature_evidence_sections
from .analysis_evidence_utils import _clean_float, _safe_int


def _dsc_feature_context(
    output: dict[str, Any],
    validation: dict[str, Any] | None = None,
    *,
    validation_summary: str = "",
    residual_type: str = "",
    residual_summary: str = "",
) -> dict[str, Any]:
    validation = dict(validation or {})
    config_snapshot = validation.get("config_snapshot", {})
    if not isinstance(config_snapshot, dict):
        config_snapshot = {}

    peak_components = _dsc_peak_component_rows(output.get("peak_components"))
    scan_rows = _dsc_scan_rows(output.get("scan_r_squared"))
    scan_mode = str(output.get("scan_mode", output.get("technique", "")) or "").strip().lower()
    baseline_corr = str(output.get("baseline_corr", config_snapshot.get("baseline_corr", "")) or "").strip() or None
    exo_up = config_snapshot.get("exo_up", output.get("exo_up"))
    tg_method = str(output.get("Tg_method", config_snapshot.get("Tg_method", "")) or "").strip() or None
    tg_low = _clean_float(output.get("Tg_search_low_C", config_snapshot.get("Tg_search_low_C")))
    tg_high = _clean_float(output.get("Tg_search_high_C", config_snapshot.get("Tg_search_high_C")))
    tm_low = _clean_float(output.get("Tm_search_low_C", config_snapshot.get("Tm_search_low_C")))
    tm_high = _clean_float(output.get("Tm_search_high_C", config_snapshot.get("Tm_search_high_C")))
    tc_low = _clean_float(output.get("Tc_search_low_C", config_snapshot.get("Tc_search_low_C")))
    tc_high = _clean_float(output.get("Tc_search_high_C", config_snapshot.get("Tc_search_high_C")))
    peak_function = str(output.get("peak_function", config_snapshot.get("peak_function", "")) or "").strip() or None
    peak_prominence_ratio = _clean_float(output.get("peak_prominence_ratio", config_snapshot.get("peak_prominence_ratio")))
    min_event_enthalpy = _clean_float(output.get("min_event_enthalpy_Jg", config_snapshot.get("min_event_enthalpy_Jg")))
    max_melting_peak_width = _clean_float(output.get("max_melting_peak_width_C", config_snapshot.get("max_melting_peak_width_C")))
    dhm0 = _clean_float(output.get("DHm0_Jg", config_snapshot.get("user_DHm0", config_snapshot.get("crystallinity_std"))))
    dhm0_source = str(output.get("DHm0_source") or config_snapshot.get("DHm0_source") or "").strip() or None
    baseline_sensitivity = _clean_float(output.get("baseline_sensitivity_pct"))
    boundary_sensitivity = _clean_float(output.get("integration_boundary_sensitivity_pct"))
    dhm_mean = _clean_float(output.get("DHm_Jg_mean"))
    dhm_std = _clean_float(output.get("DHm_Jg_std"))
    dhcc_mean = _clean_float(output.get("DHcc_Jg_mean"))
    dhcc_std = _clean_float(output.get("DHcc_Jg_std"))
    xc_mean = _clean_float(output.get("Xc_pct_mean"))
    xc_std = _clean_float(output.get("Xc_pct_std"))
    xc_ci95 = _clean_float(output.get("Xc_pct_ci95"))
    baseline_variant_count = _safe_int(output.get("baseline_variant_count"), default=0)
    integration_variant_count = _safe_int(output.get("integration_variant_count"), default=0)

    xc_reliability_status = "usable"
    if (baseline_sensitivity is not None and baseline_sensitivity >= 10.0) or (
        boundary_sensitivity is not None and boundary_sensitivity >= 8.0
    ) or (xc_ci95 is not None and xc_ci95 >= 8.0):
        xc_reliability_status = "low_confidence"
    if baseline_variant_count == 1 or integration_variant_count == 1:
        xc_reliability_status = "low_confidence"
    if dhm0 is None or dhm0_source == "missing":
        xc_reliability_status = "diagnostic_only"

    supported_components = [
        row
        for row in peak_components
        if _clean_float(row.get("peak_C")) is not None
        and _clean_float(row.get("enthalpy_Jg")) is not None
        and abs(_clean_float(row.get("enthalpy_Jg")) or 0.0) >= max(0.0, float(min_event_enthalpy or 0.0))
    ]
    supported_melting_components = [
        row
        for row in supported_components
        if str(row.get("type", "") or "").strip().lower() in {"melting", "deconv_melting"}
    ]
    supported_crystallization_components = [
        row
        for row in supported_components
        if str(row.get("type", "") or "").strip().lower()
        in {
            "crystallisation",
            "crystallization",
            "cold_crystallisation",
            "cold_crystallization",
            "recrystallisation",
            "recrystallization",
        }
    ]

    section_context = {
        "config_snapshot": config_snapshot,
        "peak_components": peak_components,
        "scan_rows": scan_rows,
        "scan_mode": scan_mode,
        "baseline_corr": baseline_corr,
        "exo_up": exo_up,
        "tg_method": tg_method,
        "tg_low": tg_low,
        "tg_high": tg_high,
        "tm_low": tm_low,
        "tm_high": tm_high,
        "tc_low": tc_low,
        "tc_high": tc_high,
        "peak_function": peak_function,
        "peak_prominence_ratio": peak_prominence_ratio,
        "min_event_enthalpy": min_event_enthalpy,
        "max_melting_peak_width": max_melting_peak_width,
        "dhm0": dhm0,
        "dhm0_source": dhm0_source,
        "baseline_sensitivity": baseline_sensitivity,
        "boundary_sensitivity": boundary_sensitivity,
        "dhm_mean": dhm_mean,
        "dhm_std": dhm_std,
        "dhcc_mean": dhcc_mean,
        "dhcc_std": dhcc_std,
        "xc_mean": xc_mean,
        "xc_std": xc_std,
        "xc_ci95": xc_ci95,
        "baseline_variant_count": baseline_variant_count,
        "integration_variant_count": integration_variant_count,
        "xc_reliability_status": xc_reliability_status,
        "supported_components": supported_components,
        "supported_melting_components": supported_melting_components,
        "supported_crystallization_components": supported_crystallization_components,
    }
    sections = _dsc_feature_evidence_sections(
        output,
        section_context,
        validation_summary=validation_summary,
        residual_type=residual_type,
        residual_summary=residual_summary,
    )

    return {
        "output": output,
        "validation": validation,
        "config_snapshot": config_snapshot,
        "peak_components": peak_components,
        "scan_rows": scan_rows,
        "scan_mode": scan_mode,
        "baseline_corr": baseline_corr,
        "exo_up": exo_up,
        "tg_method": tg_method,
        "peak_function": peak_function,
        "min_event_enthalpy": min_event_enthalpy,
        "dhm0_source": dhm0_source,
        "dhm_mean": dhm_mean,
        "dhm_std": dhm_std,
        "dhcc_mean": dhcc_mean,
        "dhcc_std": dhcc_std,
        "xc_mean": xc_mean,
        "xc_std": xc_std,
        "xc_ci95": xc_ci95,
        "xc_reliability_status": xc_reliability_status,
        "supported_components": supported_components,
        "supported_melting_components": supported_melting_components,
        "supported_crystallization_components": supported_crystallization_components,
        "thermal_event_evidence": sections["thermal_event_evidence"],
        "scan_evidence": sections["scan_evidence"],
        "baseline_evidence": sections["baseline_evidence"],
        "crystallinity_evidence": sections["crystallinity_evidence"],
        "peak_evidence": sections["peak_evidence"],
        "feature_evidence": sections["feature_evidence"],
        "physical_evidence": sections["physical_evidence"],
        "confidence_signals": sections["confidence_signals"],
        "scan_r_squared_median": sections["scan_r_squared_median"],
        "scan_r_squared_spread": sections["scan_r_squared_spread"],
        "quality_flag_text": sections["quality_flag_text"],
        "residual_type": residual_type,
        "baseline_corr_value": baseline_corr,
        "quality_score": _clean_float(output.get("quality_score")),
    }


__all__ = [
    "_dsc_feature_evidence_sections",
    "_dsc_feature_context",
]
