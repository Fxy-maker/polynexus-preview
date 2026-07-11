from __future__ import annotations

from typing import Any


def _non_empty_mapping(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if value in (None, "", [], {}):
            continue
        out[key] = value
    return out


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _ir_temperature_2d_feature_bundle(temperature_2d_metrics: dict[str, Any]) -> dict[str, Any]:
    signal_evidence = _non_empty_mapping(
        [
            ("submodule_id", temperature_2d_metrics.get("submodule_id")),
            ("n_frames", temperature_2d_metrics.get("n_frames")),
            ("n_bands_tracked", temperature_2d_metrics.get("n_bands_tracked")),
            ("stage_counts", temperature_2d_metrics.get("stage_counts")),
            ("sequence_order_source", temperature_2d_metrics.get("sequence_order_source")),
            ("T_range_C", temperature_2d_metrics.get("T_range_C")),
            ("temperature_min_C", temperature_2d_metrics.get("temperature_min_C")),
            ("temperature_max_C", temperature_2d_metrics.get("temperature_max_C")),
            ("temperature_missing_count", temperature_2d_metrics.get("temperature_missing_count")),
            ("time_missing_count", temperature_2d_metrics.get("time_missing_count")),
            ("time_estimated_count", temperature_2d_metrics.get("time_estimated_count")),
        ]
    )
    peak_evidence = _non_empty_mapping(
        [
            ("dynamic_shape", temperature_2d_metrics.get("dynamic_shape")),
            ("sync_shape", temperature_2d_metrics.get("sync_shape")),
            ("async_shape", temperature_2d_metrics.get("async_shape")),
            ("matrix_shape", temperature_2d_metrics.get("matrix_shape")),
            ("dynamic_rms", temperature_2d_metrics.get("dynamic_rms")),
            ("dynamic_signal_rms", temperature_2d_metrics.get("dynamic_signal_rms")),
            ("neg_fraction", temperature_2d_metrics.get("neg_fraction")),
            ("nan_fraction", temperature_2d_metrics.get("nan_fraction")),
            ("wavenumber_grid_consistent", temperature_2d_metrics.get("wavenumber_grid_consistent")),
            ("frame_intensity_scale_spread", temperature_2d_metrics.get("frame_intensity_scale_spread")),
            ("max_sync_abs", temperature_2d_metrics.get("max_sync_abs")),
            ("max_async_abs", temperature_2d_metrics.get("max_async_abs")),
        ]
    )
    transform_evidence = _non_empty_mapping(
        [
            ("sync_cross_peak_count", temperature_2d_metrics.get("sync_cross_peak_count")),
            ("async_cross_peak_count", temperature_2d_metrics.get("async_cross_peak_count")),
            ("cross_peak_count", temperature_2d_metrics.get("cross_peak_count")),
            ("assigned_cross_peak_count", temperature_2d_metrics.get("assigned_cross_peak_count")),
            ("unassigned_cross_peak_count", temperature_2d_metrics.get("unassigned_cross_peak_count")),
            ("async_with_sync_support_count", temperature_2d_metrics.get("async_with_sync_support_count")),
            ("top_sync_cross_peak_cm1", temperature_2d_metrics.get("top_sync_cross_peak_cm1") or None),
            ("top_async_cross_peak_cm1", temperature_2d_metrics.get("top_async_cross_peak_cm1") or None),
            ("top_sync_diagonal_distance_cm1", temperature_2d_metrics.get("top_sync_diagonal_distance_cm1")),
            ("top_async_diagonal_distance_cm1", temperature_2d_metrics.get("top_async_diagonal_distance_cm1")),
            ("top_sync_assigned", temperature_2d_metrics.get("top_sync_assigned")),
            ("top_async_assigned", temperature_2d_metrics.get("top_async_assigned")),
            ("top_async_has_sync_support", temperature_2d_metrics.get("top_async_has_sync_support")),
            ("noda_rule_interpretation_ready", temperature_2d_metrics.get("noda_rule_interpretation_ready")),
            ("transition_count", temperature_2d_metrics.get("transition_count")),
            ("transition_temperatures_C", temperature_2d_metrics.get("transition_temperatures_C") or None),
        ]
    )
    structure_evidence = _non_empty_mapping(
        [
            ("sequence_axis_ready", temperature_2d_metrics.get("sequence_axis_ready")),
            ("matrix_shapes_consistent", temperature_2d_metrics.get("matrix_shapes_consistent")),
            ("sequence_axis_score", temperature_2d_metrics.get("sequence_axis_score")),
            ("matrix_quality_score", temperature_2d_metrics.get("matrix_quality_score")),
            ("cos_signal_score", temperature_2d_metrics.get("cos_signal_score")),
            ("band_tracking_score", temperature_2d_metrics.get("band_tracking_score")),
            ("interpretation_ready", temperature_2d_metrics.get("interpretation_ready")),
            ("paper_conclusion_ready", temperature_2d_metrics.get("paper_conclusion_ready")),
        ]
    )
    band_tracking_evidence = _non_empty_mapping(
        [
            ("band_index_series_count", temperature_2d_metrics.get("band_index_series_count")),
            ("band_index_transition_candidate_count", temperature_2d_metrics.get("band_index_transition_candidate_count")),
            ("band_index_transition_support_band_count", temperature_2d_metrics.get("band_index_transition_support_band_count")),
            ("band_index_transition_consensus_frame", temperature_2d_metrics.get("band_index_transition_consensus_frame")),
            ("band_index_transition_frame_spread", temperature_2d_metrics.get("band_index_transition_frame_spread")),
            ("band_index_transition_support_ratio", temperature_2d_metrics.get("band_index_transition_support_ratio")),
            ("band_index_transition_single_frame_only", temperature_2d_metrics.get("band_index_transition_single_frame_only")),
            ("band_index_transition_reproducible", temperature_2d_metrics.get("band_index_transition_reproducible")),
            ("band_index_transition_denominator_unstable", temperature_2d_metrics.get("band_index_transition_denominator_unstable")),
            ("band_index_transition_max_jump_cm1", temperature_2d_metrics.get("band_index_transition_max_jump_cm1")),
            ("band_index_transition_median_jump_cm1", temperature_2d_metrics.get("band_index_transition_median_jump_cm1")),
            ("band_index_transition_max_jump_ratio", temperature_2d_metrics.get("band_index_transition_max_jump_ratio")),
            ("band_tracking_missing_key_band", temperature_2d_metrics.get("band_tracking_missing_key_band")),
            ("band_index_transition_support_keys", temperature_2d_metrics.get("band_index_transition_support_keys") or None),
        ]
    )
    single_frame_evidence = _non_empty_mapping(
        [
            ("low_confidence_frame_count", temperature_2d_metrics.get("low_confidence_frame_count")),
            ("low_confidence_frame_ratio", temperature_2d_metrics.get("low_confidence_frame_ratio")),
            ("frame_assignment_confidence_mean", temperature_2d_metrics.get("frame_assignment_confidence_mean")),
            ("frame_polymer_score_mean", temperature_2d_metrics.get("frame_polymer_score_mean")),
            ("frame_key_band_support_mean", temperature_2d_metrics.get("frame_key_band_support_mean")),
        ]
    )
    temperature_2d_evidence = _non_empty_mapping(
        [
            ("sequence_axis_score", temperature_2d_metrics.get("sequence_axis_score")),
            ("matrix_quality_score", temperature_2d_metrics.get("matrix_quality_score")),
            ("cos_signal_score", temperature_2d_metrics.get("cos_signal_score")),
            ("band_tracking_score", temperature_2d_metrics.get("band_tracking_score")),
            ("interpretation_ready", temperature_2d_metrics.get("interpretation_ready")),
            ("paper_conclusion_ready", temperature_2d_metrics.get("paper_conclusion_ready")),
            ("low_confidence_frame_ratio", temperature_2d_metrics.get("low_confidence_frame_ratio")),
        ]
    )

    feature_evidence: dict[str, Any] = {}
    for key, value in temperature_2d_metrics.items():
        if key in {"stage_counts"}:
            continue
        feature_evidence[key] = value
    feature_evidence["sequence_evidence"] = signal_evidence
    feature_evidence["matrix_evidence"] = peak_evidence
    feature_evidence["peak_evidence"] = peak_evidence
    feature_evidence["transform_evidence"] = transform_evidence
    feature_evidence["cos_evidence"] = transform_evidence
    feature_evidence["interpretation_evidence"] = structure_evidence
    feature_evidence["band_tracking_evidence"] = band_tracking_evidence
    feature_evidence["single_frame_evidence"] = single_frame_evidence
    feature_evidence["temperature_2d_evidence"] = temperature_2d_evidence

    confidence_signals = [
        {
            "name": "sequence_axis_score",
            "value": temperature_2d_metrics.get("sequence_axis_score"),
            "source": "IR_temperature_2d",
        },
        {
            "name": "matrix_quality_score",
            "value": temperature_2d_metrics.get("matrix_quality_score"),
            "source": "IR_temperature_2d",
        },
        {
            "name": "cos_signal_score",
            "value": temperature_2d_metrics.get("cos_signal_score"),
            "source": "IR_temperature_2d",
        },
    ]

    return {
        "signal_evidence": signal_evidence,
        "peak_evidence": peak_evidence,
        "transform_evidence": transform_evidence,
        "structure_evidence": structure_evidence,
        "feature_evidence": feature_evidence,
        "confidence_signals": confidence_signals,
    }


__all__ = [
    "_non_empty_mapping",
    "_safe_int",
    "_ir_temperature_2d_feature_bundle",
]
