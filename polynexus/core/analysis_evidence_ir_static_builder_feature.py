from __future__ import annotations

from typing import Any

from .analysis_evidence_utils import (
    _clean_float,
    _non_empty_mapping,
    _relative_spread,
)


def _ir_static_feature_bundle(
    output: dict[str, Any],
    *,
    polymer_name: str,
    reference_band_records: list[dict[str, Any]],
    reference_band_source: str | None,
    peak_positions: list[float],
    peak_heights: list[float],
    peak_prominence_distribution: dict[str, Any] | None,
    peak_widths: list[float],
    peak_assignments: list[str],
    assigned_peaks: list[dict[str, Any]],
    unassigned_peaks: list[dict[str, Any]],
    assigned_peak_count: int,
    matched_peak_count: int,
    peak_support_count: int,
    key_band_hits: list[dict[str, Any]],
    key_band_missing: list[dict[str, Any]],
    baseline_method: str,
    normalization_method: str,
    smooth_window: float | None,
    peak_distance: float | None,
    peak_fit_window: float | None,
    assignment_tolerance: float | None,
    wn_min: float | None,
    wn_max: float | None,
    wn_span: float | None,
    x_calibration_status: str | None,
) -> dict[str, Any]:
    signal_evidence = _non_empty_mapping(
        [
            ("wavenumber_min_cm1", wn_min),
            ("wavenumber_max_cm1", wn_max),
            ("wavenumber_span_cm1", wn_span),
        ]
    )

    peak_evidence: dict[str, Any] = {}
    if peak_positions:
        peak_evidence = _non_empty_mapping(
            [
                ("peak_count", len(peak_positions)),
                ("peak_positions", peak_positions),
                ("peak_heights", peak_heights if peak_heights else None),
                ("peak_prominence_distribution", peak_prominence_distribution),
                ("peak_widths", peak_widths if peak_widths else None),
                ("peak_assignments", peak_assignments if peak_assignments else None),
                ("assigned_peak_count", assigned_peak_count),
                ("unassigned_peak_count", len(unassigned_peaks)),
                ("matched_peak_count", matched_peak_count),
                ("peak_support_count", peak_support_count),
                ("assigned_peaks", assigned_peaks if assigned_peaks else None),
                ("unassigned_peaks", unassigned_peaks if unassigned_peaks else None),
            ]
        )
        peak_evidence = dict(peak_evidence)
        peak_evidence["peak_count"] = int(len(peak_positions))
        if peak_evidence.get("peak_widths") and len(peak_evidence.get("peak_widths", [])) >= 2:
            peak_evidence["peak_width_spread"] = _relative_spread(
                peak_evidence.get("peak_widths", [])
            )

    background_evidence = _non_empty_mapping(
        [
            ("baseline_method", baseline_method or None),
            ("normalization_method", normalization_method or None),
            ("smooth_window", smooth_window),
            ("peak_distance", peak_distance),
            ("peak_fit_window_cm1", peak_fit_window),
            ("assignment_tolerance_cm1", assignment_tolerance),
        ]
    )

    assignment_confidence = _clean_float(
        output.get("assignment_confidence", output.get("polymer_score"))
    )
    assignment_evidence = _non_empty_mapping(
        [
            ("polymer_name", polymer_name or None),
            ("polymer_score", _clean_float(output.get("polymer_score"))),
            ("assignment_confidence", assignment_confidence),
            ("assigned_peaks", assigned_peaks if assigned_peaks else None),
            ("unassigned_peaks", unassigned_peaks if unassigned_peaks else None),
            ("assigned_peak_count", len(assigned_peaks)),
            ("unassigned_peak_count", len(unassigned_peaks)),
            ("key_band_hits", key_band_hits if key_band_hits else None),
            ("key_band_missing", key_band_missing if key_band_missing else None),
            ("key_band_hit_count", len(key_band_hits)),
            ("key_band_missing_count", len(key_band_missing)),
        ]
    )

    reference_evidence = _non_empty_mapping(
        [
            ("polymer_name", polymer_name or None),
            ("band_count", len(reference_band_records)),
            ("bands", reference_band_records if reference_band_records else None),
            ("source", reference_band_source or None),
            ("hit_count", len(key_band_hits)),
            ("missing_count", len(key_band_missing)),
        ]
    )

    phase_evidence = _non_empty_mapping(
        [
            ("Xc_pct", _clean_float(output.get("Xc_pct"))),
            ("Xc_method", str(output.get("Xc_method", "") or "").strip() or None),
            ("Xc_calibration_status", x_calibration_status),
        ]
    )

    paper_conclusion_candidate = bool(
        len(peak_positions) >= 6
        and assigned_peak_count >= 4
        and len(key_band_hits) >= 3
        and len(key_band_missing) == 0
    )
    structure_evidence = _non_empty_mapping(
        [
            ("classification_basis", "peak_assignment" if key_band_hits else "peak_detection"),
            ("detected_peak_count", len(peak_positions) if peak_positions else None),
            ("assigned_peak_count", assigned_peak_count),
            ("matched_peak_count", matched_peak_count),
            ("reference_band_count", len(reference_band_records)),
            ("reference_band_hit_count", len(key_band_hits)),
            ("reference_band_missing_count", len(key_band_missing)),
            ("key_reference_bands_hit", key_band_hits if key_band_hits else None),
            ("key_reference_bands_missing", key_band_missing if key_band_missing else None),
            (
                "characteristic_band_support_ok",
                bool(len(key_band_hits) >= 3 and len(key_band_missing) == 0),
            ),
            ("Xc_pct", _clean_float(output.get("Xc_pct"))),
            ("Xc_method", str(output.get("Xc_method", "") or "").strip() or None),
            ("Xc_calibration_status", x_calibration_status),
            ("paper_conclusion_candidate", paper_conclusion_candidate),
            ("paper_conclusion_ready", paper_conclusion_candidate),
        ]
    )

    feature_evidence: dict[str, Any] = {}
    if peak_evidence:
        feature_evidence["peak_evidence"] = peak_evidence
    if background_evidence:
        feature_evidence["baseline_evidence"] = background_evidence
    if assignment_evidence:
        feature_evidence["assignment_evidence"] = assignment_evidence
    if reference_evidence:
        feature_evidence["reference_evidence"] = reference_evidence
    if phase_evidence:
        feature_evidence["phase_evidence"] = phase_evidence
    if structure_evidence:
        feature_evidence["structure_evidence"] = structure_evidence
        feature_evidence["classification_evidence"] = structure_evidence

    confidence_signals: list[dict[str, Any]] = []
    if peak_positions:
        confidence_signals.append({"name": "peak_count", "value": len(peak_positions), "source": "IR"})
    if assignment_evidence:
        confidence_signals.append(
            {
                "name": "assignment_confidence",
                "value": assignment_confidence,
                "source": "IR",
            }
        )

    return {
        "signal_evidence": signal_evidence,
        "peak_evidence": peak_evidence,
        "background_evidence": background_evidence,
        "assignment_evidence": assignment_evidence,
        "reference_evidence": reference_evidence,
        "phase_evidence": phase_evidence,
        "structure_evidence": structure_evidence,
        "feature_evidence": feature_evidence,
        "confidence_signals": confidence_signals,
    }


__all__ = ["_ir_static_feature_bundle"]
