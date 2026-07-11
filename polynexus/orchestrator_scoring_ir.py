from __future__ import annotations

from typing import Any


def _ir_support_snapshot(
    self: Any,
    output: dict[str, Any],
    analysis_evidence: dict[str, Any],
) -> dict[str, Any]:
    if self.technique != "ir":
        return {
            "peak_count": 0.0,
            "assigned_peak_count": 0.0,
            "reference_band_hit_count": 0.0,
            "reference_band_missing_count": 0.0,
            "assignment_confidence_score": 0.0,
            "key_band_support_score": 0.0,
            "baseline_stability_score": 0.0,
            "peak_coverage_score": 0.0,
            "ir_support_score": 0.0,
            "triggered_constraint_count": 0.0,
            "unassigned_key_band_count": 0.0,
            "classification_basis": "",
        }

    output = dict(output or {})
    analysis_evidence = dict(analysis_evidence or {})
    feature_evidence = analysis_evidence.get("feature_evidence", {})
    if not isinstance(feature_evidence, dict):
        feature_evidence = {}
    peak_evidence = feature_evidence.get("peak_evidence", {})
    if not isinstance(peak_evidence, dict):
        peak_evidence = {}
    assignment_evidence = feature_evidence.get("assignment_evidence", {})
    if not isinstance(assignment_evidence, dict):
        assignment_evidence = {}
    structure_evidence = feature_evidence.get("structure_evidence", {})
    if not isinstance(structure_evidence, dict):
        structure_evidence = {}
    ir_support_evidence = feature_evidence.get("ir_support_evidence", {})
    if not isinstance(ir_support_evidence, dict):
        ir_support_evidence = {}
    reference_evidence = feature_evidence.get("reference_evidence", {})
    if not isinstance(reference_evidence, dict):
        reference_evidence = {}
    constraint_summary = analysis_evidence.get("constraint_summary", {})
    if not isinstance(constraint_summary, dict):
        constraint_summary = {}

    peak_count = self._safe_float(peak_evidence.get("peak_count", output.get("n_peaks")))
    assigned_peak_count = self._safe_float(
        peak_evidence.get(
            "assigned_peak_count",
            assignment_evidence.get("assigned_peak_count", 0.0),
        )
    )
    reference_band_hit_count = self._safe_float(
        reference_evidence.get(
            "hit_count",
            assignment_evidence.get("key_band_hit_count", 0.0),
        )
    )
    reference_band_missing_count = self._safe_float(
        reference_evidence.get(
            "missing_count",
            assignment_evidence.get("key_band_missing_count", 0.0),
        )
    )
    reference_band_count = self._safe_float(reference_evidence.get("band_count", 0.0))
    if reference_band_count <= 0:
        reference_band_count = reference_band_hit_count + reference_band_missing_count
    assignment_confidence_score = self._safe_float(
        ir_support_evidence.get(
            "assignment_confidence_score",
            assignment_evidence.get(
                "assignment_confidence_score",
                assignment_evidence.get(
                    "assignment_confidence",
                    output.get("assignment_confidence", output.get("polymer_score", 0.0)),
                ),
            ),
        )
    )
    key_band_support_score = self._safe_float(
        ir_support_evidence.get(
            "key_band_support_score",
            assignment_evidence.get(
                "key_band_support_score",
                (reference_band_hit_count / reference_band_count)
                if reference_band_count > 0
                else 0.0,
            ),
        )
    )
    baseline_stability_score = self._safe_float(
        ir_support_evidence.get(
            "baseline_stability_score",
            structure_evidence.get("baseline_stability_score", 0.0),
        )
    )
    peak_coverage_score = self._safe_float(
        ir_support_evidence.get(
            "peak_coverage_score",
            assignment_evidence.get(
                "peak_coverage_score",
                (assigned_peak_count / peak_count) if peak_count > 0 else 0.0,
            ),
        )
    )
    triggered_constraint_count = self._safe_float(
        ir_support_evidence.get(
            "triggered_constraint_count",
            constraint_summary.get("triggered_total", 0.0),
        )
    )
    unassigned_key_band_count = self._safe_float(
        ir_support_evidence.get(
            "unassigned_key_band_count",
            assignment_evidence.get(
                "unassigned_key_band_count",
                reference_band_missing_count,
            ),
        )
    )
    ir_support_score = self._safe_float(
        ir_support_evidence.get(
            "ir_support_score",
            structure_evidence.get("ir_support_score", 0.0),
        )
    )
    if ir_support_score <= 0.0 and any(
        value > 0.0
        for value in (
            assignment_confidence_score,
            key_band_support_score,
            baseline_stability_score,
            peak_coverage_score,
        )
    ):
        ir_support_score = max(
            0.0,
            min(
                1.0,
                0.38 * assignment_confidence_score
                + 0.30 * key_band_support_score
                + 0.18 * peak_coverage_score
                + 0.14 * baseline_stability_score,
            ),
        )
    classification_basis = str(structure_evidence.get("classification_basis", "") or "").strip()

    return {
        "peak_count": peak_count,
        "assigned_peak_count": assigned_peak_count,
        "reference_band_hit_count": reference_band_hit_count,
        "reference_band_missing_count": reference_band_missing_count,
        "assignment_confidence_score": assignment_confidence_score,
        "key_band_support_score": key_band_support_score,
        "baseline_stability_score": baseline_stability_score,
        "peak_coverage_score": peak_coverage_score,
        "ir_support_score": ir_support_score,
        "triggered_constraint_count": triggered_constraint_count,
        "unassigned_key_band_count": unassigned_key_band_count,
        "classification_basis": classification_basis,
    }
