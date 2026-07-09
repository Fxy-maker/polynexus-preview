from __future__ import annotations

from typing import Any


def _ir_temperature_2d_symptom_bridge_lines(
    symptom: dict[str, Any] | None,
    output: dict[str, Any] | None = None,
) -> list[str]:
    if not isinstance(symptom, dict):
        return []

    output = dict(output or {})
    name = str(symptom.get("name", "") or "").strip().lower()
    targets = symptom.get("target_params", [])
    if not isinstance(targets, list):
        targets = []
    target_text = " / ".join(str(item).strip() for item in targets if str(item).strip())

    bridge_map = {
        "sequence_axis_incomplete": "sequence_axis_incomplete -> recover temperature/time ordering before promoting the 2D map",
        "temperature_axis_missing": "temperature_axis_missing -> recover an explicit temperature axis before treating the sequence as real perturbation data",
        "stage_order_ambiguous": "stage_order_ambiguous -> separate heating, hold, and cooling before reading the trend",
        "hold_time_missing_or_estimated": "hold_time_missing_or_estimated -> recover the hold segment timing before using it as evidence",
        "matrix_shape_inconsistent": "matrix_shape_inconsistent -> make the dynamic matrix and 2D-COS shapes line up first",
        "negative_matrix_fraction_high": "negative_matrix_fraction_high -> reduce baseline over-subtraction before trusting the 2D map",
        "matrix_nan_fraction_high": "matrix_nan_fraction_high -> fill the matrix holes before interpreting 2D-COS peaks",
        "wavenumber_grid_inconsistent": "wavenumber_grid_inconsistent -> align every frame to the same wavenumber grid before cross-peak ranking",
        "frame_intensity_scale_unstable": "frame_intensity_scale_unstable -> stabilize frame intensity scaling before promoting the transition",
        "dynamic_signal_too_weak": "dynamic_signal_too_weak -> recover a stronger dynamic signal before trusting the cross-peak map",
        "weak_cos_signal": "weak_cos_signal -> stabilize the sync/async peaks before drawing transitions from them",
        "cross_peak_near_diagonal": "cross_peak_near_diagonal -> push the leading cross peaks away from the diagonal before reading them as real coupling",
        "cross_peak_without_band_assignment": "cross_peak_without_band_assignment -> recover reference-band assignment before using the cross-peak map for mechanism claims",
        "async_peak_without_sync_support": "async_peak_without_sync_support -> require a matching synchronous pair before trusting async ordering",
        "noda_rule_not_applicable": "noda_rule_not_applicable -> keep Noda-rule interpretation disabled until sync/async support and assignment both hold",
        "band_index_jump_single_frame": "band_index_jump_single_frame -> require multi-band support before calling the transition real",
        "band_index_denominator_unstable": "band_index_denominator_unstable -> stabilize the band-index scale before trusting the transition magnitude",
        "transition_single_frame_only": "transition_single_frame_only -> keep the transition tentative until adjacent frames support it",
        "band_tracking_missing_key_band": "band_tracking_missing_key_band -> recover the missing tracked bands before strengthening the conclusion",
        "temperature_trend_not_reproducible": "temperature_trend_not_reproducible -> require the same trend to repeat across multiple tracked bands",
        "insufficient_perturbation_frames": "insufficient_perturbation_frames -> gather more perturbation frames before paper-ready interpretation",
        "transition_candidate_present": "transition_candidate_present -> keep the transition as evidence-only until the sequence and matrix stay stable",
    }

    lead = bridge_map.get(name)
    if not lead:
        summary = str(symptom.get("summary", "") or "").strip()
        if target_text:
            lead = f"{name} -> {target_text}"
        elif summary:
            lead = f"{name} -> {summary}"
        else:
            return []

    lines = [lead]
    expected = symptom.get("expected_evidence_change", [])
    if not isinstance(expected, list):
        expected = []
    lines.extend(f"expected evidence change: {str(item).strip()}" for item in expected if str(item).strip())
    quality_flag = str(output.get("quality_flag", "") or "").strip()
    validation_summary = str(output.get("validation_summary", "") or "").strip()
    if quality_flag:
        lines.append(f"current quality_flag: {quality_flag}")
    if validation_summary and validation_summary != "All checks passed":
        lines.append(f"current validation_summary: {validation_summary}")
    return lines


__all__ = ["_ir_temperature_2d_symptom_bridge_lines"]
