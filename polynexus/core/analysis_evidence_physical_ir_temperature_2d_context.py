from __future__ import annotations

from typing import Any

from .analysis_evidence_utils import _clean_float, _safe_int, _shape_tuple


def _ir_temperature_2d_metric_context(
    output: dict[str, Any],
    validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validation = dict(validation or {})
    stage_counts = output.get("stage_counts", {})
    if not isinstance(stage_counts, dict):
        stage_counts = {}
    matrix_shape = _shape_tuple(output.get("matrix_shape"))
    dynamic_shape = _shape_tuple(output.get("dynamic_shape"))
    sync_shape = _shape_tuple(output.get("sync_shape"))
    async_shape = _shape_tuple(output.get("async_shape"))

    n_frames = _safe_int(output.get("n_frames"), 0)
    n_bands_tracked = _safe_int(output.get("n_bands_tracked"), 0)
    temperature_missing_count = _safe_int(output.get("temperature_missing_count"), 0)
    time_missing_count = _safe_int(output.get("time_missing_count"), 0)
    time_estimated_count = _safe_int(output.get("time_estimated_count"), 0)
    hold_time_missing_count = _safe_int(output.get("hold_time_missing_count"), 0)
    hold_time_estimated_count = _safe_int(output.get("hold_time_estimated_count"), 0)
    transition_count = _safe_int(output.get("transition_count", output.get("n_transitions")), 0)
    sync_cross_peak_count = _safe_int(output.get("sync_cross_peak_count"), 0)
    async_cross_peak_count = _safe_int(output.get("async_cross_peak_count"), 0)
    cross_peak_count = _safe_int(
        output.get("cross_peak_count"),
        sync_cross_peak_count + async_cross_peak_count,
    )
    assigned_cross_peak_count = _safe_int(output.get("assigned_cross_peak_count"), 0)
    unassigned_cross_peak_count = _safe_int(output.get("unassigned_cross_peak_count"), 0)
    async_with_sync_support_count = _safe_int(output.get("async_with_sync_support_count"), 0)
    band_index_series_count = _safe_int(output.get("band_index_series_count"), 0)
    band_index_transition_candidate_count = _safe_int(
        output.get("band_index_transition_candidate_count"),
        0,
    )
    band_index_transition_support_band_count = _safe_int(
        output.get("band_index_transition_support_band_count"),
        0,
    )
    band_index_transition_consensus_frame = _safe_int(
        output.get("band_index_transition_consensus_frame"),
        -1,
    )
    band_index_transition_frame_spread = _clean_float(
        output.get("band_index_transition_frame_spread")
    )
    band_index_transition_support_ratio = _clean_float(
        output.get("band_index_transition_support_ratio")
    )
    band_index_transition_single_frame_only = bool(
        output.get("band_index_transition_single_frame_only", False)
    )
    band_index_transition_reproducible = bool(
        output.get("band_index_transition_reproducible", False)
    )
    band_index_transition_denominator_unstable = bool(
        output.get("band_index_transition_denominator_unstable", False)
    )
    band_index_transition_max_jump = _clean_float(
        output.get("band_index_transition_max_jump_cm1")
    )
    band_index_transition_median_jump = _clean_float(
        output.get("band_index_transition_median_jump_cm1")
    )
    band_index_transition_max_jump_ratio = _clean_float(
        output.get("band_index_transition_max_jump_ratio")
    )
    band_tracking_missing_key_band = bool(
        output.get("band_tracking_missing_key_band", False)
    )
    band_index_transition_support_keys = output.get("band_index_transition_support_keys", [])
    if not isinstance(band_index_transition_support_keys, list):
        band_index_transition_support_keys = []
    low_confidence_frame_count = _safe_int(output.get("low_confidence_frame_count"), 0)
    low_confidence_frame_ratio = _clean_float(output.get("low_confidence_frame_ratio"))
    frame_assignment_confidence_mean = _clean_float(
        output.get("frame_assignment_confidence_mean")
    )
    frame_polymer_score_mean = _clean_float(output.get("frame_polymer_score_mean"))
    frame_key_band_support_mean = _clean_float(
        output.get("frame_key_band_support_mean")
    )

    heating_monotonic = bool(output.get("heating_monotonic", False))
    cooling_monotonic = bool(output.get("cooling_monotonic", False))
    hold_monotonic = bool(output.get("hold_monotonic", False))
    sequence_order_source = str(
        output.get("sequence_order_source", validation.get("sequence_order_source", ""))
        or ""
    ).strip()
    temperature_min = _clean_float(output.get("temperature_min_C"))
    temperature_max = _clean_float(output.get("temperature_max_C"))
    neg_fraction = _clean_float(output.get("neg_fraction"))
    nan_fraction = _clean_float(output.get("nan_fraction", output.get("matrix_nan_fraction")))
    dynamic_rms = _clean_float(output.get("dynamic_rms"))
    dynamic_signal_rms = _clean_float(output.get("dynamic_signal_rms", dynamic_rms))
    max_sync_abs = _clean_float(output.get("max_sync_abs"))
    max_async_abs = _clean_float(output.get("max_async_abs"))
    top_sync_diagonal_distance = _clean_float(output.get("top_sync_diagonal_distance_cm1"))
    top_async_diagonal_distance = _clean_float(
        output.get("top_async_diagonal_distance_cm1")
    )
    top_sync_assigned = bool(output.get("top_sync_assigned", False))
    top_async_assigned = bool(output.get("top_async_assigned", False))
    top_async_has_sync_support = bool(output.get("top_async_has_sync_support", False))
    noda_rule_interpretation_ready = bool(
        output.get("noda_rule_interpretation_ready", False)
    )
    frame_intensity_scale_spread = _clean_float(
        output.get("frame_intensity_scale_spread")
    )
    wavenumber_grid_consistent = bool(output.get("wavenumber_grid_consistent", True))

    stage_total = 0
    for value in stage_counts.values():
        stage_total += _safe_int(value, 0)

    return {
        "validation": validation,
        "stage_counts": stage_counts,
        "matrix_shape": matrix_shape,
        "dynamic_shape": dynamic_shape,
        "sync_shape": sync_shape,
        "async_shape": async_shape,
        "n_frames": n_frames,
        "n_bands_tracked": n_bands_tracked,
        "temperature_missing_count": temperature_missing_count,
        "time_missing_count": time_missing_count,
        "time_estimated_count": time_estimated_count,
        "hold_time_missing_count": hold_time_missing_count,
        "hold_time_estimated_count": hold_time_estimated_count,
        "transition_count": transition_count,
        "sync_cross_peak_count": sync_cross_peak_count,
        "async_cross_peak_count": async_cross_peak_count,
        "cross_peak_count": cross_peak_count,
        "assigned_cross_peak_count": assigned_cross_peak_count,
        "unassigned_cross_peak_count": unassigned_cross_peak_count,
        "async_with_sync_support_count": async_with_sync_support_count,
        "band_index_series_count": band_index_series_count,
        "band_index_transition_candidate_count": band_index_transition_candidate_count,
        "band_index_transition_support_band_count": band_index_transition_support_band_count,
        "band_index_transition_consensus_frame": band_index_transition_consensus_frame,
        "band_index_transition_frame_spread": band_index_transition_frame_spread,
        "band_index_transition_support_ratio": band_index_transition_support_ratio,
        "band_index_transition_single_frame_only": band_index_transition_single_frame_only,
        "band_index_transition_reproducible": band_index_transition_reproducible,
        "band_index_transition_denominator_unstable": band_index_transition_denominator_unstable,
        "band_index_transition_max_jump_cm1": band_index_transition_max_jump,
        "band_index_transition_median_jump_cm1": band_index_transition_median_jump,
        "band_index_transition_max_jump_ratio": band_index_transition_max_jump_ratio,
        "band_tracking_missing_key_band": band_tracking_missing_key_band,
        "band_index_transition_support_keys": band_index_transition_support_keys,
        "low_confidence_frame_count": low_confidence_frame_count,
        "low_confidence_frame_ratio": low_confidence_frame_ratio,
        "frame_assignment_confidence_mean": frame_assignment_confidence_mean,
        "frame_polymer_score_mean": frame_polymer_score_mean,
        "frame_key_band_support_mean": frame_key_band_support_mean,
        "sequence_order_source": sequence_order_source,
        "heating_monotonic": heating_monotonic,
        "cooling_monotonic": cooling_monotonic,
        "hold_monotonic": hold_monotonic,
        "temperature_min_C": temperature_min,
        "temperature_max_C": temperature_max,
        "neg_fraction": neg_fraction,
        "nan_fraction": nan_fraction,
        "dynamic_rms": dynamic_rms,
        "dynamic_signal_rms": dynamic_signal_rms,
        "max_sync_abs": max_sync_abs,
        "max_async_abs": max_async_abs,
        "top_sync_diagonal_distance_cm1": top_sync_diagonal_distance,
        "top_async_diagonal_distance_cm1": top_async_diagonal_distance,
        "top_sync_assigned": top_sync_assigned,
        "top_async_assigned": top_async_assigned,
        "top_async_has_sync_support": top_async_has_sync_support,
        "noda_rule_interpretation_ready": noda_rule_interpretation_ready,
        "frame_intensity_scale_spread": frame_intensity_scale_spread,
        "wavenumber_grid_consistent": wavenumber_grid_consistent,
        "stage_total": stage_total,
    }


__all__ = ["_ir_temperature_2d_metric_context"]
