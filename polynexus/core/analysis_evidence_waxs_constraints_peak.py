from __future__ import annotations

from typing import Any

from .analysis_evidence_utils import _clean_float, _safe_int


_PEAK_CONSTRAINT_NAMES = {
    "temperature_axis_missing",
    "temperature_axis_low_confidence",
    "temperature_sequence_nonmonotonic",
    "temperature_duplicate_frames",
    "peak_count_insufficient",
    "peak_family_unstable",
    "peak_family_identity_swap",
    "peak_family_track_fragmented",
    "peak_family_missing_too_many_frames",
    "peak_position_drift_unphysical",
    "peak_width_trend_unstable",
    "phase_transition_without_peak_family_support",
    "peak_width_nonphysical",
    "offset_sensitive_solution",
    "size_without_multi_peak_support",
}


def _evaluate_waxs_peak_constraint(
    name: str,
    output: dict[str, Any],
    context: dict[str, Any],
    observed: Any,
) -> tuple[bool, Any] | None:
    if name not in _PEAK_CONSTRAINT_NAMES:
        return None

    waxs_metrics = context["waxs_metrics"]
    peak_count = context["peak_count"]
    peak_widths = context["peak_widths"]
    peak_gap_spread = context["peak_gap_spread"]
    peak_width_spread = context["peak_width_spread"]
    two_theta_offset = context["two_theta_offset"]
    temperature_missing_count = context["temperature_missing_count"]
    temperature_duplicate_count = context["temperature_duplicate_count"]
    temperature_monotonic = context["temperature_monotonic"]
    temperature_axis_confidence = context["temperature_axis_confidence"]
    family_count = context["family_count"]
    family_continuity = context["family_continuity"]
    family_missing_count = context["family_missing_count"]
    family_missing_ratio = context["family_missing_ratio"]
    family_swap_count = context["family_swap_count"]
    family_fragmented_count = context["family_fragmented_count"]
    position_drift_map = context["position_drift_map"]
    max_position_drift = context["max_position_drift"]
    width_drift_map = context["width_drift_map"]
    max_width_drift = context["max_width_drift"]
    transition_support_score = context["transition_support_score"]

    if name == "temperature_axis_missing":
        current_observed = {
            "temperature_missing_count": temperature_missing_count,
            "temperature_values": output.get("temperature_values", []),
        }
        return temperature_missing_count > 0, current_observed
    if name == "temperature_axis_low_confidence":
        return (
            temperature_axis_confidence is not None and temperature_axis_confidence < 0.70,
            {
                "condition_confidence": temperature_axis_confidence,
                "condition_continuity_score": _clean_float(output.get("condition_continuity_score")),
            },
        )
    if name == "temperature_sequence_nonmonotonic":
        return (
            not temperature_monotonic,
            {
                "temperature_monotonic": temperature_monotonic,
                "temperature_values": output.get("temperature_values", []),
            },
        )
    if name == "temperature_duplicate_frames":
        return (
            temperature_duplicate_count > 0,
            {
                "temperature_duplicate_count": temperature_duplicate_count,
                "temperature_values": output.get("temperature_values", []),
            },
        )
    if name == "peak_count_insufficient":
        return (
            peak_count is not None and peak_count < 2,
            {"peak_count": peak_count, "peak_positions": waxs_metrics.get("peak_positions", [])},
        )
    if name == "peak_family_unstable":
        width_trigger = peak_width_spread is not None and peak_width_spread > 0.45
        gap_trigger = (
            peak_count is not None
            and peak_count >= 3
            and peak_gap_spread is not None
            and peak_gap_spread > 0.35
        )
        return (
            width_trigger or gap_trigger,
            {
                "peak_count": peak_count,
                "peak_gap_spread": peak_gap_spread,
                "peak_width_spread": peak_width_spread,
            },
        )
    if name == "peak_family_identity_swap":
        return (
            family_swap_count > 0,
            {
                "peak_family_identity_swap_count": family_swap_count,
                "peak_family_continuity_score": family_continuity,
            },
        )
    if name == "peak_family_track_fragmented":
        return (
            family_fragmented_count > 0 or (family_continuity is not None and family_continuity < 0.72),
            {
                "peak_family_fragmented_count": family_fragmented_count,
                "peak_family_continuity_score": family_continuity,
            },
        )
    if name == "peak_family_missing_too_many_frames":
        return (
            (family_missing_ratio is not None and family_missing_ratio > 0.30) or family_missing_count >= 2,
            {
                "peak_family_missing_frame_count": family_missing_count,
                "peak_family_missing_ratio": family_missing_ratio,
            },
        )
    if name == "peak_position_drift_unphysical":
        return (
            max_position_drift is not None and max_position_drift > 0.85,
            {
                "peak_position_drift_per_family": position_drift_map,
                "max_position_drift_deg": max_position_drift,
            },
        )
    if name == "peak_width_trend_unstable":
        return (
            max_width_drift is not None and max_width_drift > 0.55,
            {
                "peak_width_drift_per_family": width_drift_map,
                "max_width_drift_deg": max_width_drift,
            },
        )
    if name == "phase_transition_without_peak_family_support":
        transition_count = _safe_int(output.get("n_transitions"), 0)
        return (
            transition_count > 0
            and (
                family_count < 2
                or (family_continuity is not None and family_continuity < 0.55)
                or (transition_support_score is not None and transition_support_score < 0.55)
            ),
            {
                "n_transitions": transition_count,
                "peak_family_count": family_count,
                "peak_family_continuity_score": family_continuity,
                "transition_support_score": transition_support_score,
                "transition_candidate_count": context["transition_candidate_count"],
            },
        )
    if name == "peak_width_nonphysical":
        invalid_widths = [width for width in peak_widths if width is None or width <= 0 or width > 6.0]
        return (
            bool(invalid_widths),
            {"peak_widths": peak_widths, "invalid_widths": invalid_widths},
        )
    if name == "offset_sensitive_solution":
        return (
            two_theta_offset is not None and abs(two_theta_offset) > 0.05,
            {"two_theta_offset": two_theta_offset},
        )
    size = _clean_float(observed)
    return (
        size is not None and size > 0 and peak_count is not None and peak_count < 2,
        {"D_Scherrer_nm": size, "peak_count": peak_count},
    )


__all__ = ["_evaluate_waxs_peak_constraint"]
