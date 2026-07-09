from __future__ import annotations

import math
from typing import Any

from .analysis_evidence_utils import _clean_float, _safe_int
from .analysis_evidence_waxs_metrics import _waxs_peak_metrics


def _waxs_constraint_context(
    output: dict[str, Any],
    observed: Any,
    config_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config_snapshot = config_snapshot if isinstance(config_snapshot, dict) else {}
    waxs_metrics = _waxs_peak_metrics(output)
    peak_count = waxs_metrics.get("peak_count")
    peak_widths = waxs_metrics.get("peak_widths", [])
    peak_gap_spread = waxs_metrics.get("peak_gap_spread")
    peak_width_spread = waxs_metrics.get("peak_width_spread")
    x_method = str(output.get("Xc_method", "") or "").strip().lower()
    x_pct = _clean_float(output.get("Xc_pct"))
    two_theta_offset = _clean_float(output.get("two_theta_offset"))
    if two_theta_offset is None:
        two_theta_offset = _clean_float(config_snapshot.get("two_theta_offset"))
    temperature_missing_count = _safe_int(output.get("temperature_missing_count"), 0)
    temperature_duplicate_count = _safe_int(output.get("temperature_duplicate_count"), 0)
    temperature_monotonic = bool(output.get("temperature_monotonic", False))
    temperature_axis_confidence = _clean_float(
        output.get("temperature_axis_confidence", output.get("condition_confidence"))
    )
    family_count = _safe_int(output.get("peak_family_count"), 0)
    family_continuity = _clean_float(output.get("peak_family_continuity_score"))
    family_missing_count = _safe_int(output.get("peak_family_missing_frame_count"), 0)
    family_missing_ratio = _clean_float(output.get("peak_family_missing_ratio"))
    family_swap_count = _safe_int(output.get("peak_family_identity_swap_count"), 0)
    family_fragmented_count = _safe_int(output.get("peak_family_fragmented_count"), 0)
    position_drift_map = output.get("peak_position_drift_per_family")
    width_drift_map = output.get("peak_width_drift_per_family")
    d_values = output.get("D_values_nm", [])
    if not isinstance(d_values, list):
        d_values = []
    d_support_peak_count = _safe_int(output.get("D_support_peak_count"), 0)
    d_support_family_count = _safe_int(output.get("D_support_family_count"), 0)
    d_trend_support_score = _clean_float(output.get("D_trend_support_score"))
    d_monotonicity = str(output.get("D_trend_monotonicity", "") or "").strip().lower()
    d_jump_count = _safe_int(output.get("D_jump_single_frame_count"), 0)
    d_jump_indices = output.get("D_jump_single_frame_indices", [])
    if not isinstance(d_jump_indices, list):
        d_jump_indices = []
    d_confidence_by_frame = output.get("D_confidence_by_frame", [])
    if not isinstance(d_confidence_by_frame, list):
        d_confidence_by_frame = []
    instrument_broadening_present = bool(output.get("instrument_broadening_present"))

    max_fwhm_drift = None
    if isinstance(width_drift_map, dict) and width_drift_map:
        width_drift_values = [_clean_float(value) for value in width_drift_map.values()]
        finite_width_drifts = [value for value in width_drift_values if value is not None]
        if finite_width_drifts:
            max_fwhm_drift = max(finite_width_drifts)

    xc_values = output.get("Xc_values", [])
    xc_support_score = _clean_float(output.get("Xc_trend_support_score"))
    xc_background_sensitivity = _clean_float(output.get("Xc_background_sensitivity"))
    xc_peak_support_ratio = _clean_float(output.get("Xc_peak_support_ratio"))
    xc_monotonicity = str(output.get("Xc_trend_monotonicity", "") or "").strip().lower()
    xc_jump_count = _safe_int(output.get("crystallinity_jump_single_frame_count"), 0)
    xc_jump_indices = output.get("crystallinity_jump_single_frame_indices", [])
    if not isinstance(xc_jump_indices, list):
        xc_jump_indices = []
    transition_support_score = _clean_float(output.get("transition_support_score"))
    transition_candidate_count = _safe_int(output.get("transition_candidate_count"), 0)
    transition_candidates = output.get("Xc_transition_candidates", [])
    if not isinstance(transition_candidates, list):
        transition_candidates = []
    if transition_candidate_count <= 0 and transition_candidates:
        transition_candidate_count = len(transition_candidates)

    max_position_drift = None
    if isinstance(position_drift_map, dict) and position_drift_map:
        position_values = [_clean_float(value) for value in position_drift_map.values()]
        finite_position_values = [value for value in position_values if value is not None]
        if finite_position_values:
            max_position_drift = max(finite_position_values)

    max_width_drift = None
    if isinstance(width_drift_map, dict) and width_drift_map:
        width_values = [_clean_float(value) for value in width_drift_map.values()]
        finite_width_values = [value for value in width_values if value is not None]
        if finite_width_values:
            max_width_drift = max(finite_width_values)

    frame_records = output.get("frame_evidence", [])
    if not isinstance(frame_records, list):
        frame_records = []
    peak_area_series: list[float] = []
    x_c_series: list[float] = []
    for row in frame_records:
        if not isinstance(row, dict):
            continue
        area = _clean_float(row.get("peak_area_sum"))
        if area is not None and math.isfinite(area):
            peak_area_series.append(area)
        x_val = _clean_float(row.get("Xc_pct"))
        if x_val is not None and math.isfinite(x_val):
            x_c_series.append(x_val)

    return {
        "config_snapshot": config_snapshot,
        "observed": observed,
        "waxs_metrics": waxs_metrics,
        "peak_count": peak_count,
        "peak_widths": peak_widths,
        "peak_gap_spread": peak_gap_spread,
        "peak_width_spread": peak_width_spread,
        "x_method": x_method,
        "x_pct": x_pct,
        "two_theta_offset": two_theta_offset,
        "temperature_missing_count": temperature_missing_count,
        "temperature_duplicate_count": temperature_duplicate_count,
        "temperature_monotonic": temperature_monotonic,
        "temperature_axis_confidence": temperature_axis_confidence,
        "family_count": family_count,
        "family_continuity": family_continuity,
        "family_missing_count": family_missing_count,
        "family_missing_ratio": family_missing_ratio,
        "family_swap_count": family_swap_count,
        "family_fragmented_count": family_fragmented_count,
        "position_drift_map": position_drift_map,
        "width_drift_map": width_drift_map,
        "d_values": d_values,
        "d_support_peak_count": d_support_peak_count,
        "d_support_family_count": d_support_family_count,
        "d_trend_support_score": d_trend_support_score,
        "d_monotonicity": d_monotonicity,
        "d_jump_count": d_jump_count,
        "d_jump_indices": d_jump_indices,
        "d_confidence_by_frame": d_confidence_by_frame,
        "instrument_broadening_present": instrument_broadening_present,
        "max_fwhm_drift": max_fwhm_drift,
        "xc_values": xc_values,
        "xc_support_score": xc_support_score,
        "xc_background_sensitivity": xc_background_sensitivity,
        "xc_peak_support_ratio": xc_peak_support_ratio,
        "xc_monotonicity": xc_monotonicity,
        "xc_jump_count": xc_jump_count,
        "xc_jump_indices": xc_jump_indices,
        "transition_support_score": transition_support_score,
        "transition_candidate_count": transition_candidate_count,
        "transition_candidates": transition_candidates,
        "max_position_drift": max_position_drift,
        "max_width_drift": max_width_drift,
        "peak_area_series": peak_area_series,
        "x_c_series": x_c_series,
    }


__all__ = ["_waxs_constraint_context"]
