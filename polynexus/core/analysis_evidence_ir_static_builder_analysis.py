from __future__ import annotations

from typing import Any

from .analysis_evidence_ir_static_builder_feature import _ir_static_feature_bundle
from .analysis_evidence_ir_static_peak import (
    _ir_peak_observation_bundle,
    _ir_peak_records,
    _ir_processing_context,
)
from .analysis_evidence_ir_static_reference import (
    _ir_match_reference_bands,
    _ir_reference_band_context,
)
from .analysis_evidence_utils import _clean_float


def _ir_static_analysis_bundle(
    output: dict[str, Any],
    validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    feature_evidence: dict[str, Any] = {}
    confidence_signals: list[dict[str, Any]] = []

    for key in (
        "polymer_name",
        "polymer_score",
        "assignment_confidence",
        "Xc_pct",
        "Xc_method",
        "Xc_calibration_status",
        "n_peaks",
        "r_squared",
    ):
        if key in output:
            feature_evidence[key] = output.get(key)
    if output.get("polymer_score") is not None:
        confidence_signals.append(
            {
                "name": "polymer_score",
                "value": _clean_float(output.get("polymer_score")),
                "source": "IR",
            }
        )

    peak_positions: list[float] = []
    peak_heights: list[float] = []
    peak_prominences: list[float] = []
    peak_widths: list[float] = []
    peak_assignments: list[str] = []
    assigned_peaks: list[dict[str, Any]] = []
    unassigned_peaks: list[dict[str, Any]] = []
    peak_support_count = 0
    assigned_peak_count = 0
    matched_peak_count = 0

    raw_peaks = _ir_peak_records(output)
    if raw_peaks:
        peak_observation_bundle = _ir_peak_observation_bundle(raw_peaks)
        peak_positions = peak_observation_bundle.get("peak_positions", [])
        peak_heights = peak_observation_bundle.get("peak_heights", [])
        peak_prominences = peak_observation_bundle.get("peak_prominences", [])
        peak_widths = peak_observation_bundle.get("peak_widths", [])
        peak_assignments = peak_observation_bundle.get("peak_assignments", [])
        assigned_peaks = peak_observation_bundle.get("assigned_peaks", [])
        unassigned_peaks = peak_observation_bundle.get("unassigned_peaks", [])
        peak_support_count = int(peak_observation_bundle.get("peak_support_count", 0))
        assigned_peak_count = int(peak_observation_bundle.get("assigned_peak_count", 0))
        matched_peak_count = int(peak_observation_bundle.get("matched_peak_count", 0))

    reference_context = _ir_reference_band_context(output, validation)
    polymer_name = str(reference_context.get("polymer_name", "") or "")
    reference_band_records = reference_context.get("reference_band_records", [])
    band_matches = _ir_match_reference_bands(raw_peaks, reference_band_records)
    key_band_hits = band_matches.get("key_band_hits", [])
    key_band_missing = band_matches.get("key_band_missing", [])

    processing_context = _ir_processing_context(
        output,
        validation,
        peak_positions=peak_positions,
        peak_prominences=peak_prominences,
        peak_heights=peak_heights,
    )
    reference_band_source = str(reference_context.get("reference_band_source", "") or "") or None
    ir_static_bundle = _ir_static_feature_bundle(
        output,
        polymer_name=polymer_name,
        reference_band_records=reference_band_records,
        reference_band_source=reference_band_source,
        peak_positions=peak_positions,
        peak_heights=peak_heights,
        peak_prominence_distribution=processing_context.get("peak_prominence_distribution"),
        peak_widths=peak_widths,
        peak_assignments=peak_assignments,
        assigned_peaks=assigned_peaks,
        unassigned_peaks=unassigned_peaks,
        assigned_peak_count=assigned_peak_count,
        matched_peak_count=matched_peak_count,
        peak_support_count=peak_support_count,
        key_band_hits=key_band_hits,
        key_band_missing=key_band_missing,
        baseline_method=str(processing_context.get("baseline_method", "") or ""),
        normalization_method=str(processing_context.get("normalization_method", "") or ""),
        smooth_window=_clean_float(processing_context.get("smooth_window")),
        peak_distance=_clean_float(processing_context.get("peak_distance")),
        peak_fit_window=_clean_float(processing_context.get("peak_fit_window")),
        assignment_tolerance=_clean_float(processing_context.get("assignment_tolerance")),
        wn_min=_clean_float(processing_context.get("wn_min")),
        wn_max=_clean_float(processing_context.get("wn_max")),
        wn_span=_clean_float(processing_context.get("wn_span")),
        x_calibration_status=str(processing_context.get("x_calibration_status", "") or "") or None,
    )

    feature_evidence.update(ir_static_bundle.get("feature_evidence", {}))
    confidence_signals.extend(ir_static_bundle.get("confidence_signals", []))

    return {
        "signal_evidence": ir_static_bundle.get("signal_evidence", {}),
        "peak_evidence": ir_static_bundle.get("peak_evidence", {}),
        "background_evidence": ir_static_bundle.get("background_evidence", {}),
        "assignment_evidence": ir_static_bundle.get("assignment_evidence", {}),
        "reference_evidence": ir_static_bundle.get("reference_evidence", {}),
        "phase_evidence": ir_static_bundle.get("phase_evidence", {}),
        "structure_evidence": ir_static_bundle.get("structure_evidence", {}),
        "feature_evidence": feature_evidence,
        "confidence_signals": confidence_signals,
    }


__all__ = ["_ir_static_analysis_bundle"]
