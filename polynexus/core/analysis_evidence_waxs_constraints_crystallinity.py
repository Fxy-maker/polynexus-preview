from __future__ import annotations

from typing import Any

from .analysis_evidence_utils import _clean_float


_CRYSTALLINITY_CONSTRAINT_NAMES = {
    "crystallinity_trend_without_peak_support",
    "crystallinity_jump_single_frame",
    "crystallinity_background_driven",
    "crystallinity_trend_conflicts_with_peak_area",
    "crystallinity_outside_physical_range",
    "melting_trend_without_peak_disappearance",
    "cold_crystallization_without_new_peak_support",
    "amorphous_partition_unstable",
    "crystallinity_without_peak_support",
    "scherrer_trend_without_multi_peak_support",
    "scherrer_jump_single_frame",
    "scherrer_dominated_by_peak_width_noise",
    "scherrer_instrument_broadening_unresolved",
    "scherrer_conflicts_with_peak_family_tracking",
    "scherrer_unphysical_temperature_trend",
}


def _evaluate_waxs_crystallinity_constraint(
    name: str,
    output: dict[str, Any],
    context: dict[str, Any],
    observed: Any,
) -> tuple[bool, Any] | None:
    if name not in _CRYSTALLINITY_CONSTRAINT_NAMES:
        return None

    peak_count = context["peak_count"]
    x_method = context["x_method"]
    x_pct = context["x_pct"]
    family_continuity = context["family_continuity"]
    family_swap_count = context["family_swap_count"]
    family_fragmented_count = context["family_fragmented_count"]
    d_values = context["d_values"]
    d_support_peak_count = context["d_support_peak_count"]
    d_support_family_count = context["d_support_family_count"]
    d_trend_support_score = context["d_trend_support_score"]
    d_monotonicity = context["d_monotonicity"]
    d_jump_count = context["d_jump_count"]
    d_jump_indices = context["d_jump_indices"]
    d_confidence_by_frame = context["d_confidence_by_frame"]
    instrument_broadening_present = context["instrument_broadening_present"]
    max_fwhm_drift = context["max_fwhm_drift"]
    xc_values = context["xc_values"]
    xc_support_score = context["xc_support_score"]
    xc_background_sensitivity = context["xc_background_sensitivity"]
    xc_peak_support_ratio = context["xc_peak_support_ratio"]
    xc_monotonicity = context["xc_monotonicity"]
    xc_jump_count = context["xc_jump_count"]
    xc_jump_indices = context["xc_jump_indices"]
    peak_area_series = context["peak_area_series"]
    x_c_series = context["x_c_series"]

    if name == "crystallinity_trend_without_peak_support":
        return (
            (xc_support_score is not None and xc_support_score < 0.52)
            or (xc_peak_support_ratio is not None and xc_peak_support_ratio < 0.60),
            {
                "Xc_trend_support_score": xc_support_score,
                "Xc_peak_support_ratio": xc_peak_support_ratio,
                "Xc_trend_monotonicity": xc_monotonicity,
            },
        )
    if name == "crystallinity_jump_single_frame":
        return (
            xc_jump_count > 0,
            {
                "crystallinity_jump_single_frame_count": xc_jump_count,
                "crystallinity_jump_single_frame_indices": xc_jump_indices,
            },
        )
    if name == "crystallinity_background_driven":
        return (
            (xc_background_sensitivity is not None and xc_background_sensitivity > 0.45)
            or (xc_support_score is not None and xc_support_score < 0.45),
            {
                "Xc_background_sensitivity": xc_background_sensitivity,
                "Xc_trend_support_score": xc_support_score,
            },
        )
    if name == "crystallinity_trend_conflicts_with_peak_area":
        area_delta_sum = None
        if len(peak_area_series) >= 2:
            area_delta_sum = float(peak_area_series[-1] - peak_area_series[0])
        xc_delta = None
        if len(x_c_series) >= 2:
            xc_delta = float(x_c_series[-1] - x_c_series[0])
        return (
            area_delta_sum is not None
            and xc_delta is not None
            and area_delta_sum * xc_delta < 0
            and abs(xc_delta) > 0.02,
            {
                "peak_area_start_end_delta": area_delta_sum,
                "Xc_start_end_delta": xc_delta,
            },
        )
    if name == "crystallinity_outside_physical_range":
        invalid_xc = [
            value
            for value in (xc_values if isinstance(xc_values, list) else [])
            if _clean_float(value) is not None and (_clean_float(value) < 0 or _clean_float(value) > 95.0)
        ]
        return bool(invalid_xc), {"invalid_Xc_values": invalid_xc}
    if name == "melting_trend_without_peak_disappearance":
        xc_start = _clean_float(output.get("Xc_initial_pct"))
        xc_end = _clean_float(output.get("Xc_final_pct"))
        disappearance_count = len(output.get("peak_disappearance_temperatures", []) or [])
        return (
            xc_start is not None
            and xc_end is not None
            and xc_end < xc_start - 0.02
            and disappearance_count <= 0,
            {
                "Xc_initial_pct": xc_start,
                "Xc_final_pct": xc_end,
                "peak_disappearance_temperatures": output.get("peak_disappearance_temperatures", []),
            },
        )
    if name == "cold_crystallization_without_new_peak_support":
        xc_start = _clean_float(output.get("Xc_initial_pct"))
        xc_end = _clean_float(output.get("Xc_final_pct"))
        birth_count = len(output.get("new_peak_birth_temperatures", []) or [])
        return (
            xc_start is not None
            and xc_end is not None
            and xc_end > xc_start + 0.02
            and birth_count <= 0,
            {
                "Xc_initial_pct": xc_start,
                "Xc_final_pct": xc_end,
                "new_peak_birth_temperatures": output.get("new_peak_birth_temperatures", []),
            },
        )
    if name == "amorphous_partition_unstable":
        return (
            x_method in {"peak_area", "no_sharp_peak"}
            or (x_pct is not None and peak_count is not None and peak_count < 2 and x_pct > 0),
            {
                "Xc_method": output.get("Xc_method"),
                "amorphous_subtraction": output.get(
                    "amorphous_subtraction",
                    context["config_snapshot"].get("amorphous_subtraction"),
                ),
                "amorphous_n_peaks": output.get(
                    "amorphous_n_peaks",
                    context["config_snapshot"].get("amorphous_n_peaks"),
                ),
            },
        )
    if name == "crystallinity_without_peak_support":
        return (
            x_pct is not None and x_pct > 0 and peak_count is not None and peak_count < 2,
            {
                "Xc_pct": x_pct,
                "peak_count": peak_count,
                "Xc_method": output.get("Xc_method"),
            },
        )
    if name == "scherrer_trend_without_multi_peak_support":
        return (
            (d_support_peak_count < 2 and any(_clean_float(value) is not None for value in d_values))
            or (d_support_family_count < 2 and len(d_values) >= 2)
            or (d_trend_support_score is not None and d_trend_support_score < 0.60),
            {
                "D_support_peak_count": d_support_peak_count,
                "D_support_family_count": d_support_family_count,
                "D_trend_support_score": d_trend_support_score,
            },
        )
    if name == "scherrer_jump_single_frame":
        return (
            d_jump_count > 0,
            {
                "D_jump_single_frame_count": d_jump_count,
                "D_jump_single_frame_indices": d_jump_indices,
            },
        )
    if name == "scherrer_dominated_by_peak_width_noise":
        return (
            (d_trend_support_score is not None and d_trend_support_score < 0.55)
            or (max_fwhm_drift is not None and max_fwhm_drift > 0.40),
            {
                "D_trend_support_score": d_trend_support_score,
                "max_peak_width_drift_deg": max_fwhm_drift,
                "D_slope_distribution": output.get("D_slope_distribution"),
            },
        )
    if name == "scherrer_instrument_broadening_unresolved":
        return (
            d_support_peak_count > 0 and not instrument_broadening_present,
            {
                "instrument_broadening_present": instrument_broadening_present,
                "config_snapshot": context["config_snapshot"],
            },
        )
    if name == "scherrer_conflicts_with_peak_family_tracking":
        return (
            (
                family_swap_count > 0
                or family_fragmented_count > 0
                or (family_continuity is not None and family_continuity < 0.65)
            )
            and (d_support_peak_count > 0 or d_support_family_count > 0),
            {
                "peak_family_continuity_score": family_continuity,
                "peak_family_identity_swap_count": family_swap_count,
                "peak_family_fragmented_count": family_fragmented_count,
                "D_confidence_by_frame": d_confidence_by_frame[:3],
            },
        )
    return (
        (
            d_monotonicity == "mixed"
            and (d_trend_support_score is not None and d_trend_support_score < 0.65)
        )
        or (d_jump_count >= 2),
        {
            "D_trend_monotonicity": d_monotonicity,
            "D_values_nm": d_values,
            "D_jump_single_frame_count": d_jump_count,
        },
    )


__all__ = ["_evaluate_waxs_crystallinity_constraint"]
