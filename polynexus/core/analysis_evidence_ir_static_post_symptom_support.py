from __future__ import annotations

from typing import Any

from .analysis_evidence_common import _clean_float


def _ir_support_constraint_symptoms(
    triggered: dict[str, Any],
    support: dict[str, Any],
) -> list[dict[str, Any]]:
    symptom_list: list[dict[str, Any]] = []
    peak_count = support.get("peak_count")
    assigned_peak_count = support.get("assigned_peak_count")
    reference_band_count = support.get("reference_band_count")
    reference_band_hit_count = support.get("reference_band_hit_count")
    reference_band_missing_count = support.get("reference_band_missing_count")
    peak_width_spread = support.get("peak_width_spread")
    baseline_method = str(support.get("baseline_method", "") or "").strip().lower()
    normalization_method = str(support.get("normalization_method", "") or "").strip().lower()
    peak_distance = _clean_float(support.get("peak_distance"))
    peak_fit_window = _clean_float(support.get("peak_fit_window_cm1"))
    assignment_confidence = _clean_float(support.get("assignment_confidence"))

    def add(symptom: dict[str, Any] | None) -> None:
        if isinstance(symptom, dict) and symptom.get("name"):
            symptom_list.append(symptom)

    if "key_band_support_insufficient" in triggered:
        add(
            {
                "name": "key_band_support_insufficient",
                "severity": "warning",
                "source": "IR",
                "summary": "Reference-band coverage is too weak to support a stable polymer call.",
                "target_params": ["assignment_tolerance_cm1", "peak_fit_window_cm1"],
                "observed": {
                    "reference_band_count": reference_band_count,
                    "reference_band_hit_count": reference_band_hit_count,
                    "reference_band_missing_count": reference_band_missing_count,
                },
                "expected_evidence_change": [
                    "reference_band_hit_count should rise",
                    "reference_band_missing_count should drop to 0",
                ],
            }
        )
    if "assignment_without_characteristic_bands" in triggered:
        add(
            {
                "name": "assignment_without_characteristic_bands",
                "severity": "warning",
                "source": "IR",
                "summary": "Assignment exists, but characteristic bands are not yet consistently matched.",
                "target_params": ["assignment_tolerance_cm1", "peak_fit_window_cm1"],
                "observed": {
                    "assignment_confidence": assignment_confidence,
                    "reference_band_hit_count": reference_band_hit_count,
                    "reference_band_missing_count": reference_band_missing_count,
                },
                "expected_evidence_change": [
                    "assignment_confidence should align with key-band coverage",
                    "paper_conclusion_ready should remain false until the chain is stable",
                ],
            }
        )
    if "baseline_sensitive_assignment" in triggered:
        add(
            {
                "name": "baseline_sensitive_assignment",
                "severity": "warning",
                "source": "IR",
                "summary": "Polymer assignment depends too much on baseline or normalization settings.",
                "target_params": ["baseline_method", "normalization_method", "smooth_window"],
                "observed": {
                    "baseline_method": baseline_method or None,
                    "normalization_method": normalization_method or None,
                    "peak_width_spread": peak_width_spread,
                },
                "expected_evidence_change": [
                    "baseline_method should settle on a stable choice",
                    "peak widths should become less spread out",
                ],
            }
        )
    if "weak_peak_only_support" in triggered:
        add(
            {
                "name": "weak_peak_only_support",
                "severity": "warning",
                "source": "IR",
                "summary": "Peak detection alone is not enough to support a confident IR conclusion.",
                "target_params": ["peak_height_min", "peak_prominence_min", "peak_distance"],
                "observed": {
                    "peak_count": peak_count,
                    "assigned_peak_count": assigned_peak_count,
                    "reference_band_hit_count": reference_band_hit_count,
                },
                "expected_evidence_change": [
                    "reference_band_hit_count should reach a stable minimum",
                    "assigned_peak_count should rise with real characteristic bands",
                ],
            }
        )
    if "overcrowded_band_separation_unstable" in triggered:
        add(
            {
                "name": "overcrowded_band_separation_unstable",
                "severity": "warning",
                "source": "IR",
                "summary": "Crowded bands or wide fit windows make the local band separation unstable.",
                "target_params": ["peak_distance", "peak_fit_window_cm1"],
                "observed": {
                    "peak_count": peak_count,
                    "peak_distance": peak_distance,
                    "peak_fit_window_cm1": peak_fit_window,
                    "peak_width_spread": peak_width_spread,
                },
                "expected_evidence_change": [
                    "peak distance should better separate nearby bands",
                    "peak_fit_window_cm1 should narrow around the active peak",
                ],
            }
        )
    if "polymer_score_without_assignment_support" in triggered:
        add(
            {
                "name": "polymer_score_without_assignment_support",
                "severity": "warning",
                "source": "IR",
                "summary": "Polymer score is present but not backed by enough assigned peaks or key bands.",
                "target_params": ["assignment_confidence", "peak_fit_window_cm1"],
                "observed": {
                    "polymer_score": _clean_float(support.get("polymer_score")),
                    "reference_band_hit_count": reference_band_hit_count,
                    "assigned_peak_count": assigned_peak_count,
                },
                "expected_evidence_change": [
                    "reference_band_hit_count should reach 3 or more",
                    "assigned_peak_count should rise to a stable band family",
                ],
            }
        )
    if "crystallinity_index_without_band_support" in triggered:
        add(
            {
                "name": "crystallinity_index_without_band_support",
                "severity": "warning",
                "source": "IR",
                "summary": "Crystallinity index is being reported without enough supporting bands.",
                "target_params": ["crystallinity_band", "crystallinity_ref_band"],
                "observed": {
                    "Xc_pct": _clean_float(support.get("Xc_pct")),
                    "reference_band_hit_count": reference_band_hit_count,
                    "reference_band_missing_count": reference_band_missing_count,
                },
                "expected_evidence_change": [
                    "reference_band_missing_count should drop to zero",
                    "Xc should only be promoted when the band support chain is stable",
                ],
            }
        )
    if "ir_xc_uncalibrated" in triggered:
        add(
            {
                "name": "ir_xc_uncalibrated",
                "severity": "warning",
                "source": "IR",
                "summary": "IR crystallinity is an uncalibrated band index and should remain diagnostic.",
                "target_params": ["crystallinity_band", "crystallinity_ref_band"],
                "observed": {
                    "Xc_pct": _clean_float(support.get("Xc_pct")),
                    "Xc_method": support.get("Xc_method"),
                    "Xc_calibration_status": support.get("Xc_calibration_status"),
                },
                "expected_evidence_change": [
                    "Xc_calibration_status should become calibrated before entering paper-ready conclusions",
                    "calibrated reference bands or an external calibration curve should be recorded",
                ],
            }
        )

    return symptom_list


__all__ = ["_ir_support_constraint_symptoms"]
