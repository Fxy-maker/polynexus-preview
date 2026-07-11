from __future__ import annotations

from .analysis_evidence_utils import _clean_float, _non_empty_mapping


def _waxs_temperature_feature_evidence(output: dict[str, Any]) -> dict[str, Any]:
    temperature_values = output.get("temperature_values", [])
    if not isinstance(temperature_values, list):
        temperature_values = []
    temperature_axis_evidence = _non_empty_mapping(
        [
            ("condition_label", str(output.get("condition_label", "") or "").strip() or None),
            ("condition_unit", str(output.get("condition_unit", "") or "").strip() or None),
            ("condition_source", str(output.get("condition_source", "") or "").strip() or None),
            ("condition_source_key", str(output.get("condition_source_key", "") or "").strip() or None),
            ("condition_source_text", str(output.get("condition_source_text", "") or "").strip() or None),
            ("condition_confidence", _clean_float(output.get("condition_confidence"))),
            ("condition_missing_frames", _clean_float(output.get("condition_missing_frames"))),
            ("condition_continuity_score", _clean_float(output.get("condition_continuity_score"))),
            ("temperature_values", temperature_values if temperature_values else None),
            ("temperature_min_C", _clean_float(output.get("temperature_min_C"))),
            ("temperature_max_C", _clean_float(output.get("temperature_max_C"))),
            ("temperature_missing_count", _clean_float(output.get("temperature_missing_count"))),
            ("temperature_duplicate_count", _clean_float(output.get("temperature_duplicate_count"))),
            ("temperature_monotonic", output.get("temperature_monotonic")),
            ("temperature_step_median_C", _clean_float(output.get("temperature_step_median_C"))),
            ("temperature_step_spread", _clean_float(output.get("temperature_step_spread"))),
            ("sequence_order_source", str(output.get("sequence_order_source", "") or "").strip() or None),
            ("sequence_direction", str(output.get("sequence_direction", "") or "").strip() or None),
            ("temperature_axis_confidence", _clean_float(output.get("temperature_axis_confidence"))),
        ]
    )
    frame_evidence_records = output.get("frame_evidence")
    if not (isinstance(frame_evidence_records, list) and frame_evidence_records):
        frame_evidence_records = []
    frame_summary_evidence = _non_empty_mapping(
        [
            ("frame_count", _clean_float(output.get("frame_count"))),
            ("frame_pass_count", _clean_float(output.get("frame_pass_count"))),
            ("frame_low_conf_count", _clean_float(output.get("frame_low_conf_count"))),
            ("valid_frame_count", _clean_float(output.get("valid_frame_count"))),
            ("failed_frame_count", _clean_float(output.get("failed_frame_count"))),
            (
                "frame_quality_distribution",
                output.get("frame_quality_distribution")
                if isinstance(output.get("frame_quality_distribution"), dict)
                else None,
            ),
            (
                "frame_constraint_summary",
                output.get("frame_constraint_summary")
                if isinstance(output.get("frame_constraint_summary"), dict)
                else None,
            ),
            (
                "low_conf_frame_indices",
                output.get("low_conf_frame_indices")
                if isinstance(output.get("low_conf_frame_indices"), list)
                else None,
            ),
            (
                "low_conf_temperature_values",
                output.get("low_conf_temperature_values")
                if isinstance(output.get("low_conf_temperature_values"), list)
                else None,
            ),
            (
                "dominant_frame_failure_type",
                str(output.get("dominant_frame_failure_type", "") or "").strip() or None,
            ),
            ("median_r_squared", _clean_float(output.get("median_r_squared"))),
            ("median_peak_count", _clean_float(output.get("median_peak_count"))),
            (
                "median_structure_support_score",
                _clean_float(output.get("median_structure_support_score")),
            ),
            (
                "physical_support_pass_ratio",
                _clean_float(output.get("physical_support_pass_ratio")),
            ),
        ]
    )
    peak_family_evidence = _non_empty_mapping(
        [
            ("peak_family_count", _clean_float(output.get("peak_family_count"))),
            (
                "peak_family_assignment_method",
                str(output.get("peak_family_assignment_method", "") or "").strip() or None,
            ),
            (
                "peak_family_continuity_score",
                _clean_float(output.get("peak_family_continuity_score")),
            ),
            (
                "peak_family_missing_frame_count",
                _clean_float(output.get("peak_family_missing_frame_count")),
            ),
            (
                "peak_family_identity_swap_count",
                _clean_float(output.get("peak_family_identity_swap_count")),
            ),
            (
                "peak_position_drift_per_family",
                output.get("peak_position_drift_per_family")
                if isinstance(output.get("peak_position_drift_per_family"), dict)
                else None,
            ),
            (
                "peak_width_drift_per_family",
                output.get("peak_width_drift_per_family")
                if isinstance(output.get("peak_width_drift_per_family"), dict)
                else None,
            ),
            (
                "peak_area_drift_per_family",
                output.get("peak_area_drift_per_family")
                if isinstance(output.get("peak_area_drift_per_family"), dict)
                else None,
            ),
            (
                "new_peak_birth_temperatures",
                output.get("new_peak_birth_temperatures")
                if isinstance(output.get("new_peak_birth_temperatures"), list)
                else None,
            ),
            (
                "peak_disappearance_temperatures",
                output.get("peak_disappearance_temperatures")
                if isinstance(output.get("peak_disappearance_temperatures"), list)
                else None,
            ),
            (
                "peak_family_fragmented_count",
                _clean_float(output.get("peak_family_fragmented_count")),
            ),
            ("peak_family_missing_ratio", _clean_float(output.get("peak_family_missing_ratio"))),
            (
                "peak_family_tracks",
                output.get("peak_family_tracks")
                if isinstance(output.get("peak_family_tracks"), list)
                else None,
            ),
        ]
    )
    scherrer_trend_evidence = _non_empty_mapping(
        [
            ("D_values_nm", output.get("D_values_nm") if isinstance(output.get("D_values_nm"), list) else None),
            ("D_range_nm", output.get("D_range_nm") if isinstance(output.get("D_range_nm"), (list, tuple)) else None),
            (
                "D_slope_distribution",
                output.get("D_slope_distribution")
                if isinstance(output.get("D_slope_distribution"), dict)
                else None,
            ),
            ("D_trend_monotonicity", str(output.get("D_trend_monotonicity", "") or "").strip() or None),
            ("D_support_peak_count", _clean_float(output.get("D_support_peak_count"))),
            ("D_support_family_count", _clean_float(output.get("D_support_family_count"))),
            (
                "FWHM_values_by_family",
                output.get("FWHM_values_by_family")
                if isinstance(output.get("FWHM_values_by_family"), dict)
                else None,
            ),
            ("instrument_broadening_present", output.get("instrument_broadening_present")),
            ("D_trend_support_score", _clean_float(output.get("D_trend_support_score"))),
            (
                "D_confidence_by_frame",
                output.get("D_confidence_by_frame")
                if isinstance(output.get("D_confidence_by_frame"), list)
                else None,
            ),
            ("D_jump_single_frame_count", _clean_float(output.get("D_jump_single_frame_count"))),
            (
                "D_jump_single_frame_indices",
                output.get("D_jump_single_frame_indices")
                if isinstance(output.get("D_jump_single_frame_indices"), list)
                else None,
            ),
        ]
    )
    crystallinity_trend_evidence = _non_empty_mapping(
        [
            ("Xc_values", output.get("Xc_values") if isinstance(output.get("Xc_values"), list) else None),
            ("Xc_range_pct", output.get("Xc_range_pct") if isinstance(output.get("Xc_range_pct"), (list, tuple)) else None),
            (
                "Xc_slope_distribution",
                output.get("Xc_slope_distribution")
                if isinstance(output.get("Xc_slope_distribution"), dict)
                else None,
            ),
            ("Xc_trend_monotonicity", str(output.get("Xc_trend_monotonicity", "") or "").strip() or None),
            ("Xc_background_sensitivity", _clean_float(output.get("Xc_background_sensitivity"))),
            ("Xc_peak_support_ratio", _clean_float(output.get("Xc_peak_support_ratio"))),
            (
                "Xc_transition_candidates",
                output.get("Xc_transition_candidates")
                if isinstance(output.get("Xc_transition_candidates"), list)
                else None,
            ),
            ("Xc_trend_support_score", _clean_float(output.get("Xc_trend_support_score"))),
            (
                "crystallinity_jump_single_frame_count",
                _clean_float(output.get("crystallinity_jump_single_frame_count")),
            ),
            (
                "crystallinity_jump_single_frame_indices",
                output.get("crystallinity_jump_single_frame_indices")
                if isinstance(output.get("crystallinity_jump_single_frame_indices"), list)
                else None,
            ),
        ]
    )
    transition_evidence = _non_empty_mapping(
        [
            ("transition_candidate_count", _clean_float(output.get("transition_candidate_count"))),
            ("transition_support_score", _clean_float(output.get("transition_support_score"))),
            ("n_transitions", _clean_float(output.get("n_transitions"))),
            (
                "transition_candidates",
                output.get("Xc_transition_candidates")
                if isinstance(output.get("Xc_transition_candidates"), list)
                else None,
            ),
        ]
    )

    confidence_signals = []
    if temperature_axis_evidence:
        confidence_signals.append(
            {
                "name": "temperature_axis_confidence",
                "value": _clean_float(output.get("temperature_axis_confidence")),
                "source": "WAXS_temperature",
            }
        )
    if frame_summary_evidence:
        confidence_signals.append(
            {
                "name": "frame_pass_ratio",
                "value": _clean_float(frame_summary_evidence.get("physical_support_pass_ratio")),
                "source": "WAXS_temperature",
            }
        )
    if peak_family_evidence:
        confidence_signals.append(
            {
                "name": "peak_family_continuity_score",
                "value": _clean_float(output.get("peak_family_continuity_score")),
                "source": "WAXS_temperature",
            }
        )
    if scherrer_trend_evidence:
        confidence_signals.append(
            {
                "name": "D_trend_support_score",
                "value": _clean_float(output.get("D_trend_support_score")),
                "source": "WAXS_temperature",
            }
        )
    if crystallinity_trend_evidence:
        confidence_signals.append(
            {
                "name": "Xc_trend_support_score",
                "value": _clean_float(output.get("Xc_trend_support_score")),
                "source": "WAXS_temperature",
            }
        )
    if transition_evidence:
        confidence_signals.append(
            {
                "name": "transition_support_score",
                "value": _clean_float(output.get("transition_support_score")),
                "source": "WAXS_temperature",
            }
        )

    return {
        "sequence_evidence": temperature_axis_evidence,
        "condition_evidence": temperature_axis_evidence,
        "frame_evidence": frame_evidence_records,
        "frame_summary_evidence": frame_summary_evidence,
        "peak_family_evidence": peak_family_evidence,
        "scherrer_trend_evidence": scherrer_trend_evidence,
        "trend_evidence": crystallinity_trend_evidence,
        "crystallinity_trend_evidence": crystallinity_trend_evidence,
        "transition_evidence": transition_evidence,
        "confidence_signals": confidence_signals,
    }


__all__ = ["_waxs_temperature_feature_evidence"]
