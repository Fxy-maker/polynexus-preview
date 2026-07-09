from __future__ import annotations

from typing import Any

from .analysis_evidence_dsc_rows import _dsc_peak_component_rows, _dsc_scan_rows
from .analysis_evidence_utils import _clean_float, _relative_spread


def _dsc_constraint_context(
    output: dict[str, Any],
    validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validation = dict(validation or {})
    config_snapshot = validation.get("config_snapshot", {})
    if not isinstance(config_snapshot, dict):
        config_snapshot = {}

    peak_rows = _dsc_peak_component_rows(output.get("peak_components"))
    scan_rows = _dsc_scan_rows(output.get("scan_r_squared"))
    scan_mode = str(output.get("scan_mode", output.get("technique", "")) or "").strip().lower()
    quality_flags = output.get("quality_flags")
    if isinstance(quality_flags, dict):
        quality_flag_text = " ".join(f"{key}:{value}" for key, value in quality_flags.items())
    elif isinstance(quality_flags, list):
        quality_flag_text = " ".join(str(value) for value in quality_flags)
    else:
        quality_flag_text = str(quality_flags or "")
    quality_flag_text = quality_flag_text.strip().lower()
    dtg = _clean_float(output.get("DTg_C"))
    dcp = _clean_float(output.get("DCp_JgK"))
    tg_c = _clean_float(output.get("Tg_C"))
    tm_peak = _clean_float(output.get("Tm_peak_C"))
    tm_onset = _clean_float(output.get("Tm_onset_C"))
    tcc_peak = _clean_float(output.get("Tcc_peak_C"))
    tcc_onset = _clean_float(output.get("Tcc_onset_C"))
    tc_peak = _clean_float(output.get("Tc_peak_C"))
    dhm = _clean_float(output.get("DHm_Jg"))
    dhcc = _clean_float(output.get("DHcc_Jg"))
    xc_pct = _clean_float(output.get("Xc_pct"))
    baseline_sensitive = _clean_float(output.get("baseline_sensitivity_pct"))
    boundary_sensitive = _clean_float(output.get("integration_boundary_sensitivity_pct"))
    quality = _clean_float(output.get("quality_score"))
    min_event_enthalpy = _clean_float(output.get("min_event_enthalpy_Jg", config_snapshot.get("min_event_enthalpy_Jg")))
    max_melt_width = _clean_float(
        output.get("max_melting_peak_width_C", config_snapshot.get("max_melting_peak_width_C"))
    )
    if max_melt_width is None:
        max_melt_width = 50.0
    tg_window_low = _clean_float(output.get("Tg_search_low_C", config_snapshot.get("Tg_search_low_C")))
    tg_window_high = _clean_float(output.get("Tg_search_high_C", config_snapshot.get("Tg_search_high_C")))
    exo_up = config_snapshot.get("exo_up", output.get("exo_up"))
    supported_components = [
        row for row in peak_rows
        if _clean_float(row.get("peak_C")) is not None
        and _clean_float(row.get("enthalpy_Jg")) is not None
        and abs(_clean_float(row.get("enthalpy_Jg")) or 0.0) >= max(0.0, float(min_event_enthalpy or 0.0))
    ]
    supported_melting_components = [
        row for row in supported_components
        if str(row.get("type", "") or "").strip().lower() in {"melting", "deconv_melting"}
    ]
    r2_values = [row.get("r_squared") for row in scan_rows if _clean_float(row.get("r_squared")) is not None]
    quality_values = [
        row.get("quality_score")
        for row in scan_rows
        if _clean_float(row.get("quality_score")) is not None
    ]

    return {
        "config_snapshot": config_snapshot,
        "peak_rows": peak_rows,
        "scan_rows": scan_rows,
        "scan_mode": scan_mode,
        "quality_flag_text": quality_flag_text,
        "dtg": dtg,
        "dcp": dcp,
        "tg_c": tg_c,
        "tm_peak": tm_peak,
        "tm_onset": tm_onset,
        "tcc_peak": tcc_peak,
        "tcc_onset": tcc_onset,
        "tc_peak": tc_peak,
        "dhm": dhm,
        "dhcc": dhcc,
        "xc_pct": xc_pct,
        "baseline_sensitive": baseline_sensitive,
        "boundary_sensitive": boundary_sensitive,
        "quality": quality,
        "min_event_enthalpy": min_event_enthalpy,
        "max_melt_width": max_melt_width,
        "tg_window_low": tg_window_low,
        "tg_window_high": tg_window_high,
        "exo_up": exo_up,
        "supported_components": supported_components,
        "supported_melting_components": supported_melting_components,
        "r2_values": r2_values,
        "quality_values": quality_values,
        "r2_spread": _relative_spread(r2_values),
        "quality_spread": _relative_spread(quality_values),
    }


__all__ = ["_dsc_constraint_context"]
