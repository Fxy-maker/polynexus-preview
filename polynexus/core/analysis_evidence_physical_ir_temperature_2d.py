from __future__ import annotations

from typing import Any

from .analysis_evidence_physical_ir_temperature_2d_context import (
    _ir_temperature_2d_metric_context,
)
from .analysis_evidence_physical_ir_temperature_2d_scores import (
    _ir_temperature_2d_metric_scores,
)
from .analysis_evidence_utils import _shape_tuple


def _is_ir_temperature_2d(
    output: dict[str, Any],
    validation: dict[str, Any] | None = None,
) -> bool:
    validation = dict(validation or {})
    submodule_id = str(validation.get("submodule_id", "") or "").strip().lower()
    if submodule_id == "ir.temperature_2d":
        return True
    matrix_shape = _shape_tuple(output.get("matrix_shape"))
    dynamic_shape = _shape_tuple(output.get("dynamic_shape"))
    sync_shape = _shape_tuple(output.get("sync_shape"))
    async_shape = _shape_tuple(output.get("async_shape"))
    if matrix_shape and dynamic_shape and sync_shape and async_shape:
        return True
    return any(
        key in output
        for key in (
            "sync_cross_peak_count",
            "async_cross_peak_count",
            "n_frames",
            "stage_counts",
        )
    )


def _ir_temperature_2d_metrics(
    output: dict[str, Any],
    validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validation = dict(validation or {})
    context = _ir_temperature_2d_metric_context(output, validation)
    scores = _ir_temperature_2d_metric_scores(context)

    return {
        "submodule_id": str(validation.get("submodule_id", "") or "").strip()
        or "ir.temperature_2d",
        "stage_counts": context["stage_counts"],
        "matrix_shape": context["matrix_shape"],
        "dynamic_shape": context["dynamic_shape"],
        "sync_shape": context["sync_shape"],
        "async_shape": context["async_shape"],
        "n_frames": context["n_frames"],
        "n_bands_tracked": context["n_bands_tracked"],
        "temperature_missing_count": context["temperature_missing_count"],
        "time_missing_count": context["time_missing_count"],
        "time_estimated_count": context["time_estimated_count"],
        "hold_time_missing_count": context["hold_time_missing_count"],
        "hold_time_estimated_count": context["hold_time_estimated_count"],
        "transition_count": context["transition_count"],
        "transition_temperatures_C": str(output.get("transition_temperatures_C", "") or "").strip(),
        "sync_cross_peak_count": context["sync_cross_peak_count"],
        "async_cross_peak_count": context["async_cross_peak_count"],
        "cross_peak_count": context["cross_peak_count"],
        "assigned_cross_peak_count": context["assigned_cross_peak_count"],
        "unassigned_cross_peak_count": context["unassigned_cross_peak_count"],
        "async_with_sync_support_count": context["async_with_sync_support_count"],
        "band_index_series_count": context["band_index_series_count"],
        "band_index_transition_candidate_count": context["band_index_transition_candidate_count"],
        "band_index_transition_support_band_count": context["band_index_transition_support_band_count"],
        "band_index_transition_consensus_frame": context["band_index_transition_consensus_frame"],
        "band_index_transition_frame_spread": context["band_index_transition_frame_spread"],
        "band_index_transition_support_ratio": context["band_index_transition_support_ratio"],
        "band_index_transition_single_frame_only": context["band_index_transition_single_frame_only"],
        "band_index_transition_reproducible": context["band_index_transition_reproducible"],
        "band_index_transition_denominator_unstable": context["band_index_transition_denominator_unstable"],
        "band_index_transition_max_jump_cm1": context["band_index_transition_max_jump_cm1"],
        "band_index_transition_median_jump_cm1": context["band_index_transition_median_jump_cm1"],
        "band_index_transition_max_jump_ratio": context["band_index_transition_max_jump_ratio"],
        "band_tracking_missing_key_band": context["band_tracking_missing_key_band"],
        "band_index_transition_support_keys": context["band_index_transition_support_keys"],
        "low_confidence_frame_count": context["low_confidence_frame_count"],
        "low_confidence_frame_ratio": context["low_confidence_frame_ratio"],
        "frame_assignment_confidence_mean": context["frame_assignment_confidence_mean"],
        "frame_polymer_score_mean": context["frame_polymer_score_mean"],
        "frame_key_band_support_mean": context["frame_key_band_support_mean"],
        "sequence_order_source": context["sequence_order_source"],
        "heating_monotonic": context["heating_monotonic"],
        "cooling_monotonic": context["cooling_monotonic"],
        "hold_monotonic": context["hold_monotonic"],
        "temperature_min_C": context["temperature_min_C"],
        "temperature_max_C": context["temperature_max_C"],
        "T_range_C": str(output.get("T_range_C", "") or "").strip(),
        "neg_fraction": context["neg_fraction"],
        "nan_fraction": context["nan_fraction"],
        "dynamic_rms": context["dynamic_rms"],
        "dynamic_signal_rms": context["dynamic_signal_rms"],
        "max_sync_abs": context["max_sync_abs"],
        "max_async_abs": context["max_async_abs"],
        "frame_intensity_scale_spread": context["frame_intensity_scale_spread"],
        "wavenumber_grid_consistent": context["wavenumber_grid_consistent"],
        "top_sync_cross_peak_cm1": str(output.get("top_sync_cross_peak_cm1", "") or "").strip(),
        "top_async_cross_peak_cm1": str(output.get("top_async_cross_peak_cm1", "") or "").strip(),
        "top_sync_diagonal_distance_cm1": context["top_sync_diagonal_distance_cm1"],
        "top_async_diagonal_distance_cm1": context["top_async_diagonal_distance_cm1"],
        "top_sync_assigned": context["top_sync_assigned"],
        "top_async_assigned": context["top_async_assigned"],
        "top_async_has_sync_support": context["top_async_has_sync_support"],
        "noda_rule_interpretation_ready": context["noda_rule_interpretation_ready"],
        "sequence_axis_ready": scores["sequence_axis_ready"],
        "matrix_shapes_consistent": scores["matrix_shapes_consistent"],
        "sequence_axis_score": scores["sequence_axis_score"],
        "matrix_quality_score": scores["matrix_quality_score"],
        "cos_signal_score": scores["cos_signal_score"],
        "band_tracking_score": scores["band_tracking_score"],
        "interpretation_ready": scores["interpretation_ready"],
        "paper_conclusion_ready": scores["paper_conclusion_ready"],
    }


__all__ = [
    "_is_ir_temperature_2d",
    "_ir_temperature_2d_metric_context",
    "_ir_temperature_2d_metric_scores",
    "_ir_temperature_2d_metrics",
]
