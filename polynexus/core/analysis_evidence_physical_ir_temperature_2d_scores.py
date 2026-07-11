from __future__ import annotations

from typing import Any

from .analysis_evidence_utils import _clamp_unit


def _ir_temperature_2d_metric_scores(context: dict[str, Any]) -> dict[str, Any]:
    n_frames = context["n_frames"]
    stage_total = context["stage_total"]
    temperature_missing_count = context["temperature_missing_count"]
    time_missing_count = context["time_missing_count"]
    time_estimated_count = context["time_estimated_count"]
    heating_monotonic = context["heating_monotonic"]
    cooling_monotonic = context["cooling_monotonic"]
    hold_monotonic = context["hold_monotonic"]
    temperature_min = context["temperature_min_C"]
    temperature_max = context["temperature_max_C"]
    matrix_shape = context["matrix_shape"]
    dynamic_shape = context["dynamic_shape"]
    sync_shape = context["sync_shape"]
    async_shape = context["async_shape"]
    neg_fraction = context["neg_fraction"]
    dynamic_signal_rms = context["dynamic_signal_rms"]
    nan_fraction = context["nan_fraction"]
    wavenumber_grid_consistent = context["wavenumber_grid_consistent"]
    frame_intensity_scale_spread = context["frame_intensity_scale_spread"]
    sync_cross_peak_count = context["sync_cross_peak_count"]
    async_cross_peak_count = context["async_cross_peak_count"]
    max_sync_abs = context["max_sync_abs"]
    max_async_abs = context["max_async_abs"]
    band_index_series_count = context["band_index_series_count"]
    band_index_transition_support_band_count = context["band_index_transition_support_band_count"]
    band_index_transition_reproducible = context["band_index_transition_reproducible"]
    band_index_transition_single_frame_only = context["band_index_transition_single_frame_only"]
    transition_count = context["transition_count"]
    band_tracking_missing_key_band = context["band_tracking_missing_key_band"]
    band_index_transition_denominator_unstable = context["band_index_transition_denominator_unstable"]
    sequence_order_source = context["sequence_order_source"]

    sequence_axis_ready = bool(
        n_frames >= 3
        and stage_total == n_frames
        and temperature_missing_count == 0
        and heating_monotonic
        and cooling_monotonic
        and hold_monotonic
        and temperature_min is not None
        and temperature_max is not None
    )
    matrix_shapes_consistent = bool(
        matrix_shape
        and dynamic_shape
        and sync_shape
        and async_shape
        and len(matrix_shape) == 2
        and len(dynamic_shape) == 2
        and len(sync_shape) == 2
        and len(async_shape) == 2
        and matrix_shape == dynamic_shape
        and sync_shape[0] == sync_shape[1]
        and async_shape[0] == async_shape[1]
        and matrix_shape[1] == sync_shape[0] == async_shape[0]
    )

    sequence_axis_score = _clamp_unit(
        (0.52 if n_frames >= 3 else 0.18)
        + (0.14 if stage_total == n_frames and stage_total > 0 else 0.0)
        + (0.10 if temperature_missing_count == 0 else 0.0)
        + (0.07 if time_missing_count == 0 else 0.0)
        + (0.06 if heating_monotonic else 0.0)
        + (0.06 if cooling_monotonic else 0.0)
        + (0.03 if hold_monotonic else 0.0)
        + (0.03 if sequence_order_source else 0.0)
        - min(time_estimated_count, 5) * 0.01,
        default=0.0,
    )
    matrix_quality_score = 0.38
    if matrix_shapes_consistent:
        matrix_quality_score += 0.18
    if neg_fraction is not None:
        matrix_quality_score += 0.24 * max(
            0.0,
            1.0 - min(neg_fraction, 0.50) / 0.50,
        )
    if dynamic_signal_rms is not None:
        matrix_quality_score += 0.18 * min(dynamic_signal_rms / 0.05, 1.0)
    if nan_fraction is not None:
        matrix_quality_score += 0.08 * max(
            0.0,
            1.0 - min(nan_fraction, 0.30) / 0.30,
        )
    if wavenumber_grid_consistent:
        matrix_quality_score += 0.08
    if frame_intensity_scale_spread is not None:
        matrix_quality_score += 0.04 * max(
            0.0,
            1.0 - min(frame_intensity_scale_spread, 1.0),
        )
    matrix_quality_score = _clamp_unit(matrix_quality_score, default=0.0)
    cos_signal_score = _clamp_unit(
        0.45 * min(sync_cross_peak_count / 12.0, 1.0)
        + 0.35 * min(async_cross_peak_count / 12.0, 1.0)
        + 0.10 * min((max_sync_abs or 0.0) / 0.02, 1.0)
        + 0.10 * min((max_async_abs or 0.0) / 0.02, 1.0),
        default=0.0,
    )
    band_tracking_score = _clamp_unit(
        0.35
        + (0.12 if band_index_series_count >= 3 else 0.0)
        + (0.14 if band_index_transition_support_band_count >= 2 else 0.0)
        + (0.12 if band_index_transition_reproducible else 0.0)
        + (0.10 if not band_index_transition_single_frame_only else 0.0)
        + (0.08 if transition_count > 0 else 0.0)
        - (0.12 if band_tracking_missing_key_band else 0.0)
        - (0.10 if band_index_transition_denominator_unstable else 0.0),
        default=0.0,
    )
    interpretation_ready = bool(
        sequence_axis_ready
        and matrix_quality_score >= 0.60
        and sync_cross_peak_count > 0
        and async_cross_peak_count > 0
        and (
            band_index_transition_reproducible
            or band_index_transition_support_band_count >= 2
        )
    )
    paper_conclusion_ready = bool(
        interpretation_ready
        and transition_count > 0
        and neg_fraction is not None
        and neg_fraction <= 0.30
        and band_index_transition_reproducible
    )

    return {
        "sequence_axis_ready": sequence_axis_ready,
        "matrix_shapes_consistent": matrix_shapes_consistent,
        "sequence_axis_score": sequence_axis_score,
        "matrix_quality_score": matrix_quality_score,
        "cos_signal_score": cos_signal_score,
        "band_tracking_score": band_tracking_score,
        "interpretation_ready": interpretation_ready,
        "paper_conclusion_ready": paper_conclusion_ready,
    }


__all__ = ["_ir_temperature_2d_metric_scores"]
