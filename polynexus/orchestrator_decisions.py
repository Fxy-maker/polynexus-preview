from __future__ import annotations

from typing import Any


def _decision_metrics(self: Any, candidate: Any, previous_record: Any) -> dict[str, Any]:
    return {
        "candidate": self._score_snapshot(
            candidate.output_parameters,
            candidate.residuals_pattern,
            candidate.analysis_evidence,
        ),
        "previous": self._score_snapshot(
            previous_record.output_parameters,
            previous_record.residuals_pattern,
            previous_record.analysis_evidence,
        ),
    }


def _evaluate_candidate(
    self: Any,
    candidate: Any,
    previous_record: Any,
) -> tuple[bool, str, dict[str, Any]]:
    candidate_metrics = self._score_snapshot(
        candidate.output_parameters,
        candidate.residuals_pattern,
        candidate.analysis_evidence,
    )
    previous_metrics = self._score_snapshot(
        previous_record.output_parameters,
        previous_record.residuals_pattern,
        previous_record.analysis_evidence,
    )
    is_waxs_temperature = self.technique == "waxs" and self._submodule_id() in {
        "waxs.temperature",
        "waxs.in_situ_temp",
    }
    decision_metrics = {
        "candidate": candidate_metrics,
        "previous": previous_metrics,
        "delta": {
            key: candidate_metrics[key] - previous_metrics[key]
            for key in (
                "objective_score",
                "r_squared",
                "quality_score",
                "physical_score",
                "validation_score",
                "residual_score",
                "stability_score",
                "parameter_stability_score",
                "method_agreement_score",
                "batch_continuity_score",
            )
        },
    }
    if self.technique == "waxs":
        decision_metrics["delta"].update(
            {
                key: candidate_metrics[key] - previous_metrics[key]
                for key in (
                    "peak_support_score",
                    "background_stability_score",
                    "phase_support_score",
                    "size_support_score",
                    "waxs_support_score",
                )
            }
        )
    if is_waxs_temperature:
        decision_metrics["delta"].update(
            {
                key: candidate_metrics[key] - previous_metrics[key]
                for key in (
                    "transition_support_score",
                    "transition_candidate_count",
                    "temperature_axis_confidence",
                    "peak_family_continuity_score",
                    "Xc_trend_support_score",
                    "D_trend_support_score",
                    "frame_low_conf_count",
                    "peak_family_identity_swap_count",
                )
            }
        )
    if self.technique == "ir":
        decision_metrics["delta"].update(
            {
                key: candidate_metrics[key] - previous_metrics[key]
                for key in (
                    "peak_count",
                    "assigned_peak_count",
                    "reference_band_hit_count",
                    "reference_band_missing_count",
                    "assignment_confidence_score",
                    "key_band_support_score",
                    "baseline_stability_score",
                    "peak_coverage_score",
                    "ir_support_score",
                    "triggered_constraint_count",
                    "unassigned_key_band_count",
                )
            }
        )
    if self.technique == "dsc":
        decision_metrics["delta"].update(
            {
                key: candidate_metrics[key] - previous_metrics[key]
                for key in (
                    "event_support_score",
                    "dsc_baseline_stability_score",
                    "thermodynamic_consistency_score",
                    "crystallinity_support_score",
                    "dsc_support_score",
                    "dsc_scan_r_squared_median",
                    "dsc_scan_r_squared_spread",
                    "dsc_supported_event_fraction",
                    "dsc_triggered_constraint_count",
                    "dsc_validation_passed_count",
                )
            }
        )

    hard_fail_names = candidate_metrics.get("hard_fail_names", [])
    if hard_fail_names:
        return False, f"new_hard_fail_introduced:{','.join(hard_fail_names)}", decision_metrics

    regression_reason = self._regression_reason(candidate_metrics, previous_metrics)
    if regression_reason:
        return False, regression_reason, decision_metrics

    stability_reason = self._stability_regression_reason(candidate_metrics, previous_metrics)
    if stability_reason:
        return False, stability_reason, decision_metrics

    low_q_reason = self._saxs_low_q_priority_reason(
        candidate_metrics,
        previous_metrics,
        candidate,
        previous_record,
    )
    if low_q_reason:
        return False, low_q_reason, decision_metrics

    objective_delta = candidate_metrics["objective_score"] - previous_metrics["objective_score"]
    r_squared_delta = candidate_metrics["r_squared"] - previous_metrics["r_squared"]

    if objective_delta <= max(0.0, self._objective_gain_threshold() - 0.001):
        return False, "no_meaningful_gain", decision_metrics

    if r_squared_delta < -self._r_squared_drop_tolerance():
        return False, "fit_score_dropped", decision_metrics

    return True, "", decision_metrics
