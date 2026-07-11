from __future__ import annotations

from typing import Any


def _ir_symptom_bridge_lines(
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

    if name == "key_band_support_insufficient":
        lead = "key_band_support_insufficient -> keep the polymer call tentative until reference bands are recovered"
    elif name == "assignment_without_characteristic_bands":
        lead = "assignment_without_characteristic_bands -> verify characteristic bands before accepting the assignment"
    elif name == "baseline_sensitive_assignment":
        lead = "baseline_sensitive_assignment -> stabilize baseline_method / normalization_method before another round"
    elif name == "weak_peak_only_support":
        lead = "weak_peak_only_support -> peak count alone is not enough; wait for band support"
    elif name == "overcrowded_band_separation_unstable":
        lead = "overcrowded_band_separation_unstable -> narrow peak_fit_window_cm1 and separate crowded bands first"
    elif name == "baseline_drift_low_wn":
        lead = "baseline_drift_low_wn -> stabilize baseline_method before changing peak thresholds"
    elif name == "baseline_drift_high_wn":
        lead = "baseline_drift_high_wn -> stabilize normalization_method before changing peak thresholds"
    elif name == "baseline_drift_low_t":
        lead = "baseline_drift_low_t -> stabilize baseline_type before changing event thresholds"
    elif name == "baseline_drift_high_t":
        lead = "baseline_drift_high_t -> stabilize baseline_type before changing event thresholds"
    elif name == "melting_peak_shift":
        lead = "melting_peak_shift -> re-center Tm/Tc windows before changing peak_function"
    elif name == "tg_step_missing":
        lead = "tg_step_missing -> re-check Tg support and DCp before trusting Tg"
    elif name == "cold_crystallization_overlap":
        lead = "cold_crystallization_overlap -> separate Tcc from the melting window first"
    elif name == "event_window_too_narrow":
        lead = "event_window_too_narrow -> widen the event window before re-fitting"
    elif name == "event_window_too_wide":
        lead = "event_window_too_wide -> narrow the event window before trusting the fit"
    elif name == "exo_up_down_confusion":
        lead = "exo_up_down_confusion -> verify exo_up and signed enthalpy convention"
    elif name == "multi_event_underfit":
        lead = "multi_event_underfit -> allow multiple thermal events or components"
    elif name == "segment_split_issue":
        lead = "segment_split_issue -> check whether the scan was split at the wrong point"
    elif name == "noise_dominant":
        lead = "noise_dominant -> stabilize preprocessing and smoothing before another attempt"
    elif name == "crystallinity_index_without_band_support":
        lead = "crystallinity_index_without_band_support -> keep Xc tentative until band support is stable"
    elif name == "ir_xc_uncalibrated":
        lead = "ir_xc_uncalibrated -> treat IR Xc as a diagnostic band index until a calibration curve is available"
    else:
        summary = str(symptom.get("summary", "") or "").strip()
        if target_text:
            lead = f"{name} -> {target_text}"
        elif summary:
            lead = f"{name} -> {summary}"
        else:
            return []

    expected = symptom.get("expected_evidence_change", [])
    if not isinstance(expected, list):
        expected = []
    lines = [lead]
    lines.extend(f"expected evidence change: {str(item).strip()}" for item in expected if str(item).strip())
    quality_flag = str(output.get("quality_flag", "") or "").strip()
    validation_summary = str(output.get("validation_summary", "") or "").strip()
    if quality_flag:
        lines.append(f"current quality_flag: {quality_flag}")
    if validation_summary and validation_summary != "All checks passed":
        lines.append(f"current validation_summary: {validation_summary}")
    return lines


__all__ = ["_ir_symptom_bridge_lines"]
