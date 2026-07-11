from __future__ import annotations

from typing import Any


def _ir_residual_constraint_symptoms(
    triggered: dict[str, Any],
    residual: dict[str, Any],
    residual_type: str,
) -> list[dict[str, Any]]:
    symptom_list: list[dict[str, Any]] = []

    def add(symptom: dict[str, Any] | None) -> None:
        if isinstance(symptom, dict) and symptom.get("name"):
            symptom_list.append(symptom)

    if "baseline_drift_low_wn" in triggered:
        add(
            {
                "name": "baseline_drift_low_wn",
                "severity": "warning",
                "source": "IR",
                "summary": "The low-wavenumber edge is drifting and should be stabilized first.",
                "target_params": ["baseline_method", "smooth_window"],
                "observed": {
                    "residual_type": residual_type,
                    "max_residual_region": residual.get("max_residual_region", "unknown"),
                },
                "expected_evidence_change": [
                    "low-wavenumber residuals should weaken",
                    "baseline method should settle before peak thresholds move again",
                ],
            }
        )
    if "baseline_drift_high_wn" in triggered:
        add(
            {
                "name": "baseline_drift_high_wn",
                "severity": "warning",
                "source": "IR",
                "summary": "The high-wavenumber edge is drifting and should be stabilized first.",
                "target_params": ["baseline_method", "normalization_method"],
                "observed": {
                    "residual_type": residual_type,
                    "max_residual_region": residual.get("max_residual_region", "unknown"),
                },
                "expected_evidence_change": [
                    "high-wavenumber residuals should weaken",
                    "normalization should stop steering the conclusion",
                ],
            }
        )
    if "key_band_mismatch" in triggered:
        add(
            {
                "name": "key_band_mismatch",
                "severity": "warning",
                "source": "IR",
                "summary": "Characteristic bands are locally mismatched against the observed spectrum.",
                "target_params": ["peak_fit_window_cm1", "peak_prominence_min", "peak_height_min"],
                "observed": {
                    "residual_type": residual_type,
                    "max_residual_region": residual.get("max_residual_region", "unknown"),
                },
                "expected_evidence_change": [
                    "key-band hits should rise",
                    "assignment confidence should better match band support",
                ],
            }
        )
    if "crowded_band_underfit" in triggered:
        add(
            {
                "name": "crowded_band_underfit",
                "severity": "warning",
                "source": "IR",
                "summary": "Crowded bands are not being separated cleanly enough.",
                "target_params": ["peak_distance", "lineshape"],
                "observed": {
                    "residual_type": residual_type,
                    "max_residual_region": residual.get("max_residual_region", "unknown"),
                },
                "expected_evidence_change": [
                    "peak families should separate more cleanly",
                    "peak widths should become easier to compare",
                ],
            }
        )
    if "over_smoothed_weak_bands" in triggered:
        add(
            {
                "name": "over_smoothed_weak_bands",
                "severity": "warning",
                "source": "IR",
                "summary": "Weak bands are likely being smoothed away.",
                "target_params": ["smooth_window", "peak_height_min"],
                "observed": {
                    "residual_type": residual_type,
                    "max_residual_region": residual.get("max_residual_region", "unknown"),
                },
                "expected_evidence_change": [
                    "weak bands should reappear",
                    "peak count should stay useful without over-promoting noise",
                ],
            }
        )
    if "normalization_bias" in triggered:
        add(
            {
                "name": "normalization_bias",
                "severity": "warning",
                "source": "IR",
                "summary": "Normalization is biasing the relative band balance.",
                "target_params": ["normalization_method", "baseline_method"],
                "observed": {
                    "residual_type": residual_type,
                    "max_residual_region": residual.get("max_residual_region", "unknown"),
                },
                "expected_evidence_change": [
                    "band balance should become more stable",
                    "assignment confidence should stop jumping with scaling changes",
                ],
            }
        )
    if "noise_dominant" in triggered:
        add(
            {
                "name": "noise_dominant",
                "severity": "warning",
                "source": "IR",
                "summary": "The residual is dominated by noise rather than a localized mismatch.",
                "target_params": ["smooth_window"],
                "observed": {
                    "residual_type": residual_type,
                    "max_residual_region": residual.get("max_residual_region", "unknown"),
                },
                "expected_evidence_change": [
                    "sign flips should drop",
                    "weak-band recovery should become more stable",
                ],
            }
        )

    return symptom_list


__all__ = ["_ir_residual_constraint_symptoms"]
