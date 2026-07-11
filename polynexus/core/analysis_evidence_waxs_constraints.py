from __future__ import annotations

from typing import Any

from .analysis_evidence_waxs_constraints_context import _waxs_constraint_context
from .analysis_evidence_waxs_constraints_crystallinity import (
    _evaluate_waxs_crystallinity_constraint,
)
from .analysis_evidence_waxs_constraints_peak import _evaluate_waxs_peak_constraint


_WAXS_CONSTRAINT_NAMES = {
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
    "crystallinity_trend_without_peak_support",
    "crystallinity_jump_single_frame",
    "crystallinity_background_driven",
    "crystallinity_trend_conflicts_with_peak_area",
    "crystallinity_outside_physical_range",
    "melting_trend_without_peak_disappearance",
    "cold_crystallization_without_new_peak_support",
    "amorphous_partition_unstable",
    "peak_width_nonphysical",
    "offset_sensitive_solution",
    "crystallinity_without_peak_support",
    "size_without_multi_peak_support",
}


def _evaluate_waxs_constraint(
    name: str,
    output: dict[str, Any],
    observed: Any,
    config_snapshot: dict[str, Any] | None = None,
) -> tuple[bool, Any]:
    context = _waxs_constraint_context(output, observed, config_snapshot)
    peak_result = _evaluate_waxs_peak_constraint(name, output, context, observed)
    if peak_result is not None:
        return peak_result
    crystallinity_result = _evaluate_waxs_crystallinity_constraint(name, output, context, observed)
    if crystallinity_result is not None:
        return crystallinity_result
    return False, observed


__all__ = [
    "_WAXS_CONSTRAINT_NAMES",
    "_evaluate_waxs_constraint",
]
