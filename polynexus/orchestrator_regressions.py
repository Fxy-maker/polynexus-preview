from __future__ import annotations

from typing import Any

from polynexus.orchestrator_actions import SAXS_LOW_Q_PRIORITY_SYMPTOMS


def _saxs_low_q_priority_reason(
    self: Any,
    candidate_metrics: dict[str, Any],
    previous_metrics: dict[str, Any],
    candidate: Any,
    previous_record: Any,
) -> str:
    if self.technique != "saxs":
        return ""

    previous_symptoms = set(previous_record.symptom_names or [])
    candidate_symptoms = set(candidate.symptom_names or [])
    if not (previous_symptoms & SAXS_LOW_Q_PRIORITY_SYMPTOMS):
        return ""

    candidate_changes = set((candidate.changes or {}).keys()) if isinstance(candidate.changes, dict) else set()
    low_q_param_names = {
        "q_bragg_min",
        "q_bragg_max",
        "q_corr_min",
        "q_corr_max",
        "savgol_window",
        "savgol_order",
        "idf_peak_rel_thresh",
        "idf_valley_rel_thresh",
    }
    touched_low_q_path = bool(candidate_changes & low_q_param_names)
    low_q_problem_names = {
        "beamstop_or_low_q_contamination",
        "low_q_void_dominant",
        "strain_void_lamellar_conflict",
        "lamellar_anchor_lost_under_strain",
        "qstar_rel_without_lamellar_support",
        "orientation_shift_breaks_lamellar_comparison",
    }

    if (
        previous_symptoms & low_q_problem_names
        and candidate_symptoms & low_q_problem_names
        and not touched_low_q_path
    ):
        return "low_q_contamination_unresolved"

    if (
        "temperature_calibration_fallback_active" in previous_symptoms
        and (
            "batch_summary_conflicts_with_frame_evidence" in previous_symptoms
            or "thickness_chain_unreliable" in previous_symptoms
        )
        and (
            "temperature_calibration_fallback_active" in candidate_symptoms
            or "batch_summary_conflicts_with_frame_evidence" in candidate_symptoms
            or "thickness_chain_unreliable" in candidate_symptoms
        )
        and not touched_low_q_path
    ):
        return "fallback_still_dominant"

    prev_validation = self._safe_float(previous_metrics.get("validation_score", 0.0))
    cand_validation = self._safe_float(candidate_metrics.get("validation_score", 0.0))
    if prev_validation - cand_validation > 0.02:
        return "low_q_contamination_unresolved"

    return ""


def _stability_regression_reason(
    self: Any,
    candidate_metrics: dict[str, Any],
    previous_metrics: dict[str, Any],
) -> str:
    if self.technique != "saxs":
        return ""

    candidate_strain_status = str(candidate_metrics.get("strain_reliability_status", "") or "").strip().lower()
    previous_strain_status = str(previous_metrics.get("strain_reliability_status", "") or "").strip().lower()
    if previous_strain_status == "usable" and candidate_strain_status in {"low_confidence", "diagnostic_only"}:
        return "strain_reliability_degraded"

    candidate_phase_ambiguous = self._safe_float(candidate_metrics.get("phase_ambiguous_frame_count", 0))
    previous_phase_ambiguous = self._safe_float(previous_metrics.get("phase_ambiguous_frame_count", 0))
    if candidate_phase_ambiguous > previous_phase_ambiguous and candidate_phase_ambiguous > 0:
        return "phase_ambiguity_increased"

    candidate_void_dominant = self._safe_float(candidate_metrics.get("void_dominant_frame_count", 0))
    previous_void_dominant = self._safe_float(previous_metrics.get("void_dominant_frame_count", 0))
    if candidate_void_dominant > previous_void_dominant and candidate_void_dominant > 0:
        return "void_dominance_increased"

    candidate_paper = bool(candidate_metrics.get("paper_conclusion_candidate"))
    previous_paper = bool(previous_metrics.get("paper_conclusion_candidate"))
    if previous_paper and not candidate_paper:
        return "paper_candidate_lost"

    candidate_fallback = self._safe_float(candidate_metrics.get("fallback_ratio", 0.0))
    previous_fallback = self._safe_float(previous_metrics.get("fallback_ratio", 0.0))
    if previous_fallback >= 0.4 and candidate_fallback - previous_fallback > 0.08:
        return "fallback_still_dominant"

    candidate_gap = self._safe_float(candidate_metrics.get("raw_vs_calibrated_gap", 0.0))
    previous_gap = self._safe_float(previous_metrics.get("raw_vs_calibrated_gap", 0.0))
    if previous_gap > 0.0 and candidate_gap - previous_gap > 0.035:
        return "raw_calibrated_conflict_worsened"

    candidate_thickness_risk = self._safe_float(candidate_metrics.get("thickness_chain_risk", 0.0))
    previous_thickness_risk = self._safe_float(previous_metrics.get("thickness_chain_risk", 0.0))
    if candidate_thickness_risk >= 0.55 and candidate_thickness_risk - previous_thickness_risk > 0.08:
        return "thickness_chain_still_unreliable"

    candidate_batch = self._safe_float(candidate_metrics.get("batch_continuity_score", 1.0))
    previous_batch = self._safe_float(previous_metrics.get("batch_continuity_score", 1.0))
    if previous_batch - candidate_batch > 0.08:
        return "condition_continuity_worsened"

    candidate_method = self._safe_float(candidate_metrics.get("method_agreement_score", 1.0))
    previous_method = self._safe_float(previous_metrics.get("method_agreement_score", 1.0))
    if previous_method - candidate_method > 0.12:
        return "structure_jump_too_large"

    candidate_stability = self._safe_float(candidate_metrics.get("stability_score", 1.0))
    previous_stability = self._safe_float(previous_metrics.get("stability_score", 1.0))
    if previous_stability - candidate_stability > 0.06:
        return "stability_score_dropped"

    candidate_flags = {str(item).strip() for item in candidate_metrics.get("stability_flags", []) if str(item).strip()}
    if "stability_low" in candidate_flags and candidate_stability < 0.60:
        return "symptom_unresolved"

    return ""


def _regression_reason(self: Any, candidate_metrics: dict[str, Any], previous_metrics: dict[str, Any]) -> str:
    if self.technique == "dsc":
        dsc_reason = self._dsc_regression_reason(candidate_metrics, previous_metrics)
        if dsc_reason:
            return dsc_reason
    if self.technique == "waxs":
        if self._submodule_id() in {"waxs.temperature", "waxs.in_situ_temp"}:
            return self._waxs_temperature_regression_reason(candidate_metrics, previous_metrics)
        waxs_reason = self._waxs_regression_reason(candidate_metrics, previous_metrics)
        if waxs_reason:
            return waxs_reason
    if self.technique == "ir":
        ir_reason = self._ir_regression_reason(candidate_metrics, previous_metrics)
        if ir_reason:
            return ir_reason
    deltas = {
        "quality_score_dropped": candidate_metrics["quality_score"] - previous_metrics["quality_score"],
        "validation_risk_increased": candidate_metrics["validation_score"] - previous_metrics["validation_score"],
        "residual_risk_increased": candidate_metrics["residual_score"] - previous_metrics["residual_score"],
        "fit_improved_but_phys_worse": candidate_metrics["physical_score"] - previous_metrics["physical_score"],
    }
    for reason, delta in deltas.items():
        if delta < -self._component_drop_tolerance():
            return reason
    return ""


def _dsc_regression_reason(self: Any, candidate_metrics: dict[str, Any], previous_metrics: dict[str, Any]) -> str:
    if self.technique != "dsc":
        return ""

    candidate_event = self._safe_float(candidate_metrics.get("event_support_score", 0.0))
    previous_event = self._safe_float(previous_metrics.get("event_support_score", 0.0))
    candidate_baseline = self._safe_float(candidate_metrics.get("baseline_stability_score", 0.0))
    previous_baseline = self._safe_float(previous_metrics.get("baseline_stability_score", 0.0))
    candidate_thermal = self._safe_float(candidate_metrics.get("thermodynamic_consistency_score", 0.0))
    previous_thermal = self._safe_float(previous_metrics.get("thermodynamic_consistency_score", 0.0))
    candidate_cryst = self._safe_float(candidate_metrics.get("crystallinity_support_score", 0.0))
    previous_cryst = self._safe_float(previous_metrics.get("crystallinity_support_score", 0.0))
    candidate_validation = self._safe_float(candidate_metrics.get("validation_score", 0.0))
    previous_validation = self._safe_float(previous_metrics.get("validation_score", 0.0))
    candidate_triggered = self._safe_float(candidate_metrics.get("triggered_constraint_count", 0.0))
    previous_triggered = self._safe_float(previous_metrics.get("triggered_constraint_count", 0.0))
    candidate_support = self._safe_float(candidate_metrics.get("dsc_support_score", 0.0))
    previous_support = self._safe_float(previous_metrics.get("dsc_support_score", 0.0))

    if previous_event >= 0.55 and candidate_event < previous_event - 0.08:
        return "event_support_weakened"
    if previous_baseline >= 0.55 and candidate_baseline < previous_baseline - 0.08:
        return "baseline_became_less_stable"
    if previous_thermal >= 0.55 and candidate_thermal < previous_thermal - 0.08:
        return "thermal_consistency_worsened"
    if previous_cryst >= 0.55 and candidate_cryst < previous_cryst - 0.08:
        return "crystallinity_support_weakened"
    if previous_validation >= 0.55 and candidate_validation < previous_validation - 0.05:
        return "cross_validation_conflict_worsened"
    if candidate_triggered > previous_triggered + 0.5 and candidate_support <= previous_support + 0.01:
        return "triggered_constraint_pressure_increased"
    if candidate_support <= previous_support + 0.01:
        return "dsc_support_not_improving"
    return ""


def _waxs_regression_reason(self: Any, candidate_metrics: dict[str, Any], previous_metrics: dict[str, Any]) -> str:
    peak_delta = self._safe_float(candidate_metrics.get("peak_support_score", 1.0)) - self._safe_float(
        previous_metrics.get("peak_support_score", 1.0)
    )
    background_delta = self._safe_float(candidate_metrics.get("background_stability_score", 1.0)) - self._safe_float(
        previous_metrics.get("background_stability_score", 1.0)
    )
    phase_delta = self._safe_float(candidate_metrics.get("phase_support_score", 1.0)) - self._safe_float(
        previous_metrics.get("phase_support_score", 1.0)
    )
    size_delta = self._safe_float(candidate_metrics.get("size_support_score", 1.0)) - self._safe_float(
        previous_metrics.get("size_support_score", 1.0)
    )
    overall_delta = self._safe_float(candidate_metrics.get("waxs_support_score", 1.0)) - self._safe_float(
        previous_metrics.get("waxs_support_score", 1.0)
    )

    if self._safe_float(previous_metrics.get("peak_support_score", 1.0)) >= 0.55 and peak_delta < -0.08:
        return "peak_family_became_less_stable"
    if self._safe_float(previous_metrics.get("background_stability_score", 1.0)) >= 0.55 and background_delta < -0.08:
        return "background_partition_worsened"
    if (
        self._safe_float(previous_metrics.get("phase_support_score", 1.0)) >= 0.55
        and phase_delta < -0.08
    ) or (
        self._safe_float(previous_metrics.get("size_support_score", 1.0)) >= 0.55
        and size_delta < -0.08
    ):
        return "crystallinity_support_collapsed"
    if self._safe_float(previous_metrics.get("waxs_support_score", 1.0)) >= 0.60 and overall_delta < -0.07:
        return "physical_support_weakened"
    return ""


def _waxs_temperature_regression_reason(
    self: Any,
    candidate_metrics: dict[str, Any],
    previous_metrics: dict[str, Any],
) -> str:
    axis_delta = self._safe_float(
        candidate_metrics.get("temperature_axis_confidence", candidate_metrics.get("condition_confidence", 0.0))
    ) - self._safe_float(
        previous_metrics.get("temperature_axis_confidence", previous_metrics.get("condition_confidence", 0.0))
    )
    family_delta = self._safe_float(candidate_metrics.get("peak_family_continuity_score", 0.0)) - self._safe_float(
        previous_metrics.get("peak_family_continuity_score", 0.0)
    )
    xc_delta = self._safe_float(candidate_metrics.get("Xc_trend_support_score", 0.0)) - self._safe_float(
        previous_metrics.get("Xc_trend_support_score", 0.0)
    )
    d_delta = self._safe_float(candidate_metrics.get("D_trend_support_score", 0.0)) - self._safe_float(
        previous_metrics.get("D_trend_support_score", 0.0)
    )
    transition_delta = self._safe_float(candidate_metrics.get("transition_support_score", 0.0)) - self._safe_float(
        previous_metrics.get("transition_support_score", 0.0)
    )
    low_conf_delta = self._safe_float(candidate_metrics.get("frame_low_conf_count", 0.0)) - self._safe_float(
        previous_metrics.get("frame_low_conf_count", 0.0)
    )
    swap_delta = self._safe_float(candidate_metrics.get("peak_family_identity_swap_count", 0.0)) - self._safe_float(
        previous_metrics.get("peak_family_identity_swap_count", 0.0)
    )

    if self._safe_float(previous_metrics.get("temperature_axis_confidence", previous_metrics.get("condition_confidence", 0.0))) >= 0.70 and axis_delta < -0.06:
        return "temperature_axis_confidence_worsened"
    if self._safe_float(previous_metrics.get("peak_family_continuity_score", 0.0)) >= 0.55 and family_delta < -0.06:
        return "peak_family_tracking_worsened"
    if self._safe_float(previous_metrics.get("Xc_trend_support_score", 0.0)) >= 0.55 and xc_delta < -0.07:
        return "Xc_trend_support_collapsed"
    if self._safe_float(previous_metrics.get("D_trend_support_score", 0.0)) >= 0.55 and d_delta < -0.07:
        return "D_trend_support_collapsed"
    if self._safe_float(previous_metrics.get("transition_support_score", 0.0)) >= 0.50 and transition_delta < -0.06:
        return "transition_support_weakened"
    if low_conf_delta > 0.5 and d_delta <= 0.01 and xc_delta <= 0.01:
        return "frame_fit_improved_but_sequence_worsened"
    if swap_delta > 0.5 and family_delta <= 0.01:
        return "peak_family_tracking_worsened"
    return ""


def _ir_regression_reason(self: Any, candidate_metrics: dict[str, Any], previous_metrics: dict[str, Any]) -> str:
    if self.technique != "ir":
        return ""

    candidate_support = self._safe_float(candidate_metrics.get("ir_support_score", 0.0))
    previous_support = self._safe_float(previous_metrics.get("ir_support_score", 0.0))
    candidate_assignment = self._safe_float(
        candidate_metrics.get("assignment_confidence_score", candidate_metrics.get("quality_score", 0.0))
    )
    previous_assignment = self._safe_float(
        previous_metrics.get("assignment_confidence_score", previous_metrics.get("quality_score", 0.0))
    )
    candidate_key_band = self._safe_float(candidate_metrics.get("key_band_support_score", 0.0))
    previous_key_band = self._safe_float(previous_metrics.get("key_band_support_score", 0.0))
    candidate_baseline = self._safe_float(candidate_metrics.get("baseline_stability_score", 0.0))
    previous_baseline = self._safe_float(previous_metrics.get("baseline_stability_score", 0.0))
    candidate_peak_coverage = self._safe_float(candidate_metrics.get("peak_coverage_score", 0.0))
    previous_peak_coverage = self._safe_float(previous_metrics.get("peak_coverage_score", 0.0))
    candidate_peak_count = self._safe_float(candidate_metrics.get("peak_count", 0.0))
    previous_peak_count = self._safe_float(previous_metrics.get("peak_count", 0.0))
    candidate_triggered = self._safe_float(candidate_metrics.get("triggered_constraint_count", 0.0))
    previous_triggered = self._safe_float(previous_metrics.get("triggered_constraint_count", 0.0))
    candidate_unassigned = self._safe_float(candidate_metrics.get("unassigned_key_band_count", 0.0))
    previous_unassigned = self._safe_float(previous_metrics.get("unassigned_key_band_count", 0.0))
    candidate_basis = str(candidate_metrics.get("classification_basis", "") or "").strip()
    previous_basis = str(previous_metrics.get("classification_basis", "") or "").strip()

    if previous_key_band >= 0.55 and candidate_key_band < previous_key_band - 0.08:
        return "key_band_support_collapsed"
    if previous_assignment >= 0.55 and candidate_assignment < previous_assignment - 0.08:
        return "assignment_support_weakened"
    if previous_baseline >= 0.55 and candidate_baseline < previous_baseline - 0.08:
        return "baseline_became_less_stable"
    if previous_peak_coverage >= 0.55 and candidate_peak_count > previous_peak_count and candidate_key_band < previous_key_band - 0.05:
        return "peak_count_increased_but_key_bands_lost"
    if previous_basis == "peak_assignment" and candidate_basis != "peak_assignment" and candidate_key_band <= previous_key_band:
        return "classification_basis_became_weaker"
    if candidate_support <= previous_support + 0.01:
        if candidate_key_band < previous_key_band - 0.01:
            return "key_band_support_collapsed"
        if candidate_assignment < previous_assignment - 0.01:
            return "assignment_support_weakened"
        if candidate_baseline < previous_baseline - 0.01:
            return "baseline_became_less_stable"
        if candidate_peak_count > previous_peak_count and candidate_unassigned > previous_unassigned:
            return "peak_count_increased_but_key_bands_lost"
        if candidate_triggered > previous_triggered:
            return "classification_basis_became_weaker"
        return "classification_basis_became_weaker"
    return ""


def _residual_score(self: Any, residuals_pattern: dict[str, Any]) -> float:
    residual_type = str(residuals_pattern.get("residual_type", "") or "").strip().lower()
    score_map = {
        "random": 1.0,
        "unknown": 0.76,
        "background_drift": 0.72,
        "baseline_drift": 0.64,
        "baseline_drift_low_t": 0.60,
        "baseline_drift_high_t": 0.60,
        "melting_peak_shift": 0.62,
        "tg_step_missing": 0.58,
        "cold_crystallization_overlap": 0.56,
        "event_window_too_narrow": 0.58,
        "event_window_too_wide": 0.59,
        "exo_up_down_confusion": 0.48,
        "multi_event_underfit": 0.55,
        "segment_split_issue": 0.54,
        "noise_dominant": 0.56,
        "low_angle_background_drift": 0.68,
        "key_band_mismatch": 0.58,
        "crowded_band_underfit": 0.57,
        "normalization_bias": 0.59,
        "baseline_drift_low_wn": 0.64,
        "baseline_drift_high_wn": 0.64,
    }
    score = score_map.get(residual_type, 0.72)
    summary = str(residuals_pattern.get("summary", "") or "").strip().lower()
    if "background" in summary:
        score = min(score, 0.72)
    if "systematic" in summary:
        score = min(score, 0.60)
    if "noise" in summary:
        score = min(score, 0.58)
    return max(0.0, min(1.0, score))
