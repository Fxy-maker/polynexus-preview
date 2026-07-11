from __future__ import annotations

from .analysis_evidence_utils import (
    _clean_float,
    _clamp_unit,
    _non_empty_mapping,
    _relative_spread,
)


def _ir_support_enrichment_bundle(
    *,
    peak_evidence: dict[str, Any],
    assignment_evidence: dict[str, Any],
    reference_evidence: dict[str, Any],
    background_evidence: dict[str, Any],
    structure_evidence: dict[str, Any],
    triggered_total: int,
    triggered_soft_warn: set[str],
) -> dict[str, Any]:
    peak_count_value = _clean_float(peak_evidence.get("peak_count"))
    assigned_peak_count_value = _clean_float(peak_evidence.get("assigned_peak_count"))
    key_band_hit_count_value = int(
        reference_evidence.get("hit_count")
        or assignment_evidence.get("key_band_hit_count")
        or 0
    )
    key_band_missing_count_value = int(
        reference_evidence.get("missing_count")
        or assignment_evidence.get("key_band_missing_count")
        or 0
    )
    reference_band_count_value = int(reference_evidence.get("band_count") or 0)
    if reference_band_count_value <= 0:
        reference_band_count_value = key_band_hit_count_value + key_band_missing_count_value

    assignment_confidence_score = _clamp_unit(
        _clean_float(
            assignment_evidence.get(
                "assignment_confidence",
                assignment_evidence.get("polymer_score"),
            )
        )
    )
    key_band_support_score = _clamp_unit(
        (key_band_hit_count_value / reference_band_count_value)
        if reference_band_count_value > 0
        else 0.0
    )
    peak_coverage_score = _clamp_unit(
        (assigned_peak_count_value / peak_count_value)
        if peak_count_value and peak_count_value > 0
        else 0.0
    )

    peak_width_spread = _clean_float(peak_evidence.get("peak_width_spread"))
    peak_widths = peak_evidence.get("peak_widths")
    if peak_width_spread is None and isinstance(peak_widths, list) and len(peak_widths) >= 2:
        peak_width_spread = _relative_spread(peak_widths)

    baseline_method = str(background_evidence.get("baseline_method", "") or "").strip().lower()
    normalization_method = str(
        background_evidence.get("normalization_method", "") or ""
    ).strip().lower()
    smooth_window = _clean_float(background_evidence.get("smooth_window"))
    peak_distance = _clean_float(background_evidence.get("peak_distance"))
    peak_fit_window = _clean_float(background_evidence.get("peak_fit_window_cm1"))

    baseline_stability_score = 0.42
    if baseline_method and baseline_method not in {"none", "unknown"}:
        baseline_stability_score += 0.18
    if normalization_method and normalization_method not in {"none", "unknown"}:
        baseline_stability_score += 0.16
    if smooth_window is not None:
        baseline_stability_score += 0.04
    if peak_distance is not None:
        baseline_stability_score += 0.04
    if peak_fit_window is not None:
        baseline_stability_score += 0.04
    if peak_width_spread is not None:
        baseline_stability_score += 0.12 * max(
            0.0,
            1.0 - min(peak_width_spread, 0.6) / 0.6,
        )
    if "baseline_sensitive_assignment" in triggered_soft_warn:
        baseline_stability_score -= 0.12
    if (
        "baseline_drift_low_wn" in triggered_soft_warn
        or "baseline_drift_high_wn" in triggered_soft_warn
    ):
        baseline_stability_score -= 0.15
    if "normalization_bias" in triggered_soft_warn:
        baseline_stability_score -= 0.10
    if "over_smoothed_weak_bands" in triggered_soft_warn:
        baseline_stability_score -= 0.06
    baseline_stability_score -= 0.03 * min(triggered_total, 3)
    baseline_stability_score = _clamp_unit(baseline_stability_score)

    ir_support_score = _clamp_unit(
        0.38 * assignment_confidence_score
        + 0.30 * key_band_support_score
        + 0.18 * peak_coverage_score
        + 0.14 * baseline_stability_score
    )

    ir_support_evidence = _non_empty_mapping(
        [
            ("assignment_confidence_score", assignment_confidence_score),
            ("key_band_support_score", key_band_support_score),
            ("peak_coverage_score", peak_coverage_score),
            ("baseline_stability_score", baseline_stability_score),
            ("triggered_constraint_count", triggered_total),
            ("unassigned_key_band_count", key_band_missing_count_value),
            ("ir_support_score", ir_support_score),
        ]
    )

    peak_evidence_out = dict(peak_evidence)
    if peak_evidence_out:
        peak_evidence_out["peak_coverage_score"] = peak_coverage_score

    assignment_evidence_out = dict(assignment_evidence)
    if assignment_evidence_out:
        assignment_evidence_out["assignment_confidence_score"] = assignment_confidence_score
        assignment_evidence_out["key_band_support_score"] = key_band_support_score
        assignment_evidence_out["peak_coverage_score"] = peak_coverage_score
        assignment_evidence_out["unassigned_key_band_count"] = key_band_missing_count_value

    structure_evidence_out = dict(structure_evidence)
    if structure_evidence_out:
        structure_evidence_out["assignment_confidence_score"] = assignment_confidence_score
        structure_evidence_out["key_band_support_score"] = key_band_support_score
        structure_evidence_out["peak_coverage_score"] = peak_coverage_score
        structure_evidence_out["baseline_stability_score"] = baseline_stability_score
        structure_evidence_out["triggered_constraint_count"] = triggered_total
        structure_evidence_out["unassigned_key_band_count"] = key_band_missing_count_value
        structure_evidence_out["ir_support_score"] = ir_support_score
        paper_candidate = bool(
            structure_evidence_out.get(
                "paper_conclusion_candidate",
                structure_evidence_out.get("paper_conclusion_ready"),
            )
        )
        paper_blocking_warnings = {
            "assignment_confidence",
            "key_band_support_insufficient",
            "assignment_without_characteristic_bands",
            "baseline_sensitive_assignment",
            "baseline_drift_low_wn",
            "baseline_drift_high_wn",
            "key_band_mismatch",
            "crowded_band_underfit",
            "over_smoothed_weak_bands",
            "normalization_bias",
            "noise_dominant",
            "weak_peak_only_support",
            "overcrowded_band_separation_unstable",
            "polymer_score_without_assignment_support",
            "crystallinity_index_without_band_support",
            "ir_xc_uncalibrated",
        }
        structure_evidence_out["paper_conclusion_ready"] = bool(
            paper_candidate
            and assignment_confidence_score is not None
            and assignment_confidence_score >= 0.80
            and key_band_support_score >= 0.85
            and peak_coverage_score >= 0.60
            and baseline_stability_score >= 0.60
            and ir_support_score >= 0.78
            and key_band_missing_count_value == 0
            and not (triggered_soft_warn & paper_blocking_warnings)
        )

    feature_evidence: dict[str, Any] = {}
    if ir_support_evidence:
        feature_evidence["ir_support_evidence"] = ir_support_evidence
    if peak_evidence_out:
        feature_evidence["peak_evidence"] = peak_evidence_out
    if assignment_evidence_out:
        feature_evidence["assignment_evidence"] = assignment_evidence_out
    if structure_evidence_out:
        feature_evidence["structure_evidence"] = structure_evidence_out
        feature_evidence["classification_evidence"] = structure_evidence_out

    confidence_signals: list[dict[str, Any]] = []
    if assignment_confidence_score is not None:
        confidence_signals.append(
            {
                "name": "assignment_confidence_score",
                "value": assignment_confidence_score,
                "source": "IR",
            }
        )
    confidence_signals.append(
        {"name": "key_band_support_score", "value": key_band_support_score, "source": "IR"}
    )
    confidence_signals.append(
        {"name": "peak_coverage_score", "value": peak_coverage_score, "source": "IR"}
    )
    confidence_signals.append(
        {
            "name": "baseline_stability_score",
            "value": baseline_stability_score,
            "source": "IR",
        }
    )
    if structure_evidence_out and structure_evidence_out.get("paper_conclusion_ready") is not None:
        confidence_signals.append(
            {
                "name": "paper_conclusion_ready",
                "value": 1.0
                if bool(structure_evidence_out.get("paper_conclusion_ready"))
                else 0.0,
                "source": "IR",
            }
        )

    return {
        "peak_evidence": peak_evidence_out,
        "assignment_evidence": assignment_evidence_out,
        "structure_evidence": structure_evidence_out,
        "feature_evidence": feature_evidence,
        "confidence_signals": confidence_signals,
    }


__all__ = ["_ir_support_enrichment_bundle"]
