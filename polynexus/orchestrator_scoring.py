from __future__ import annotations

import math
from typing import Any

from polynexus.orchestrator_scoring_helpers import _first_text
from polynexus.orchestrator_scoring_helpers import _mean_or_none
from polynexus.orchestrator_scoring_dsc import (
    _dsc_support_snapshot as _shared_dsc_support_snapshot,
)
from polynexus.orchestrator_scoring_ir import _ir_support_snapshot
from polynexus.orchestrator_scoring_saxs import _saxs_evidence_snapshot
from polynexus.orchestrator_scoring_waxs import (
    _waxs_support_snapshot as _shared_waxs_support_snapshot,
)
from polynexus.orchestrator_scoring_waxs import _waxs_support_snapshot

def _score_snapshot(
    self: Any,
    output: dict[str, Any],
    residuals_pattern: dict[str, Any],
    analysis_evidence: dict[str, Any],
) -> dict[str, Any]:
    output = dict(output or {})
    residuals_pattern = dict(residuals_pattern or {})
    analysis_evidence = dict(analysis_evidence or {})

    fit_score = self._safe_float(output.get("r_squared", 0.0))
    quality_score = output.get("quality_score")
    if quality_score is None and isinstance(analysis_evidence.get("fit_evidence"), dict):
        quality_score = analysis_evidence["fit_evidence"].get("quality_score")
    quality_score = self._safe_float(quality_score if quality_score is not None else fit_score)

    quality_flag = self._first_text(analysis_evidence.get("physical_evidence", {}), output, ("quality_flag",))
    validation_summary = self._first_text(
        analysis_evidence.get("physical_evidence", {}),
        output,
        ("validation_summary",),
    )

    constraint_summary = analysis_evidence.get("constraint_summary", {})
    constraints = analysis_evidence.get("constraints", [])
    hard_fail_names: list[str] = []
    soft_warn_count = 0
    evidence_only_count = 0
    if isinstance(constraints, list):
        for item in constraints:
            if not isinstance(item, dict) or not item.get("triggered"):
                continue
            kind = str(item.get("kind", "")).strip()
            name = str(item.get("name", "")).strip()
            if kind == "hard_fail" and name:
                hard_fail_names.append(name)
            elif kind == "soft_warn":
                soft_warn_count += 1
            elif kind == "evidence_only":
                evidence_only_count += 1
    if isinstance(constraint_summary, dict):
        triggered_names = constraint_summary.get("triggered_names", {})
        if isinstance(triggered_names, dict):
            summary_hard = [
                str(item).strip()
                for item in triggered_names.get("hard_fail", [])
                if str(item).strip()
            ]
            summary_soft = [
                str(item).strip()
                for item in triggered_names.get("soft_warn", [])
                if str(item).strip()
            ]
            summary_evidence = [
                str(item).strip()
                for item in triggered_names.get("evidence_only", [])
                if str(item).strip()
            ]
            if not hard_fail_names and summary_hard:
                hard_fail_names.extend(summary_hard)
            soft_warn_count = max(soft_warn_count, len(summary_soft))
            evidence_only_count = max(evidence_only_count, len(summary_evidence))
        summary_status = str(constraint_summary.get("status", "") or "").strip().lower()
        if summary_status == "hard_fail" and not hard_fail_names:
            hard_fail_names.append("constraint_summary:hard_fail")
        elif summary_status == "soft_warn" and soft_warn_count == 0:
            soft_warn_count = 1
        elif summary_status == "evidence_only" and evidence_only_count == 0:
            evidence_only_count = 1

    physical_score = 1.0
    if quality_flag:
        upper = quality_flag.upper()
        if any(token in upper for token in ("ERROR", "FAIL", "INVALID")):
            physical_score -= 0.24
        elif any(token in upper for token in ("WARN", "LOW", "SKIP")):
            physical_score -= 0.10
        else:
            physical_score -= 0.05
    if validation_summary and validation_summary != "All checks passed":
        upper = validation_summary.upper()
        if any(token in upper for token in ("ERROR", "FAIL", "INVALID")):
            physical_score -= 0.18
        elif any(token in upper for token in ("WARN", "LOW", "SKIP")):
            physical_score -= 0.08
        else:
            physical_score -= 0.05
    physical_score -= 0.05 * min(soft_warn_count, 3)
    physical_score -= 0.02 * min(evidence_only_count, 3)
    physical_score = max(0.0, min(1.0, physical_score))

    validation_score = 1.0
    cross_validation = analysis_evidence.get("cross_validation", {})
    if isinstance(cross_validation, dict):
        total_checks = 0
        passed_checks = 0
        warn_checks = 0
        error_checks = 0

        def visit(node: Any) -> None:
            nonlocal total_checks, passed_checks, warn_checks, error_checks
            if isinstance(node, dict):
                if "passed" in node:
                    total_checks += 1
                    if bool(node.get("passed")):
                        passed_checks += 1
                    severity = str(node.get("severity", "")).upper()
                    if severity == "WARN":
                        warn_checks += 1
                    elif severity == "ERROR":
                        error_checks += 1
                else:
                    for value in node.values():
                        visit(value)
            elif isinstance(node, list):
                for value in node:
                    visit(value)

        visit(cross_validation)
        if total_checks > 0:
            validation_score = passed_checks / total_checks
            validation_score -= 0.08 * min(warn_checks, 3)
            validation_score -= 0.16 * min(error_checks, 3)
    if validation_summary and validation_summary != "All checks passed":
        upper = validation_summary.upper()
        if any(token in upper for token in ("ERROR", "FAIL", "INVALID")):
            validation_score -= 0.10
        elif any(token in upper for token in ("WARN", "LOW", "SKIP")):
            validation_score -= 0.05

    joint_ai_context = self._joint_ai_context()
    joint_penalty = 0.0
    if joint_ai_context:
        issue_count = self._safe_float(joint_ai_context.get("issue_count"))
        warning_count = self._safe_float(joint_ai_context.get("warning_count"))
        error_count = self._safe_float(joint_ai_context.get("error_count"))
        issue_families = joint_ai_context.get("issue_families")

        if math.isfinite(issue_count) and issue_count > 0:
            validation_score -= 0.02 * min(issue_count, 4.0)
            joint_penalty += 0.004 * min(issue_count, 5.0)
        if math.isfinite(warning_count) and warning_count > 0:
            validation_score -= 0.01 * min(warning_count, 3.0)
        if math.isfinite(error_count) and error_count > 0:
            validation_score -= 0.04 * min(error_count, 3.0)
            joint_penalty += 0.008 * min(error_count, 3.0)

        families = set()
        if isinstance(issue_families, list):
            families = {str(item).strip().lower() for item in issue_families if str(item).strip()}
        if "phi_c inconsistency" in families:
            validation_score -= 0.03
            joint_penalty += 0.004
        if "tm bidirectional gap" in families:
            validation_score -= 0.03
            joint_penalty += 0.004
        if "l consistency unstable" in families:
            validation_score -= 0.025
            joint_penalty += 0.003
    validation_score = max(0.0, min(1.0, validation_score))

    residual_score = self._residual_score(residuals_pattern)
    stability_snapshot = self._stability_snapshot(output, analysis_evidence)
    stability_score = stability_snapshot["stability_score"]
    waxs_support_snapshot = self._waxs_support_snapshot(
        output,
        residuals_pattern,
        analysis_evidence,
    )
    dsc_support_snapshot = self._dsc_support_snapshot(output, analysis_evidence)
    ir_support_snapshot = self._ir_support_snapshot(output, analysis_evidence)
    saxs_evidence_snapshot = self._saxs_evidence_snapshot(output, analysis_evidence)
    is_waxs_temperature = self.technique == "waxs" and self._submodule_id() in {
        "waxs.temperature",
        "waxs.in_situ_temp",
    }

    if self.technique == "saxs":
        objective_score = (
            0.37 * fit_score
            + 0.22 * quality_score
            + 0.14 * physical_score
            + 0.08 * validation_score
            + 0.07 * residual_score
            + 0.12 * stability_score
        )
    elif self.technique == "waxs":
        transition_support_score = (
            self._safe_float(output.get("transition_support_score", 0.0))
            if is_waxs_temperature
            else 0.0
        )
        objective_score = (
            0.38 * fit_score
            + 0.16 * quality_score
            + 0.10 * physical_score
            + 0.07 * validation_score
            + 0.05 * residual_score
            + 0.08 * stability_score
            + 0.08 * waxs_support_snapshot["waxs_support_score"]
            + (0.08 * transition_support_score if is_waxs_temperature else 0.0)
        )
    elif self.technique == "ir":
        objective_score = (
            0.34 * fit_score
            + 0.18 * quality_score
            + 0.12 * physical_score
            + 0.08 * validation_score
            + 0.08 * residual_score
            + 0.20 * ir_support_snapshot["ir_support_score"]
        )
    elif self.technique == "dsc":
        stability_score = dsc_support_snapshot["baseline_stability_score"]
        objective_score = (
            0.34 * fit_score
            + 0.18 * quality_score
            + 0.14 * physical_score
            + 0.10 * validation_score
            + 0.10 * residual_score
            + 0.14 * dsc_support_snapshot["dsc_support_score"]
        )
    else:
        objective_score = (
            0.42 * fit_score
            + 0.24 * quality_score
            + 0.16 * physical_score
            + 0.09 * validation_score
            + 0.09 * residual_score
        )
    if joint_penalty > 0:
        objective_score -= joint_penalty
        objective_score = max(0.0, min(1.0, objective_score))

    return {
        "r_squared": fit_score,
        "fit_score": fit_score,
        "quality_score": quality_score,
        "physical_score": physical_score,
        "validation_score": validation_score,
        "residual_score": residual_score,
        "stability_score": stability_score,
        "parameter_stability_score": stability_snapshot["parameter_stability_score"],
        "method_agreement_score": stability_snapshot["method_agreement_score"],
        "batch_continuity_score": stability_snapshot["batch_continuity_score"],
        "stability_flags": stability_snapshot["stability_flags"],
        "peak_support_score": waxs_support_snapshot["peak_support_score"],
        "background_stability_score": waxs_support_snapshot["background_stability_score"],
        "phase_support_score": waxs_support_snapshot["phase_support_score"],
        "size_support_score": waxs_support_snapshot["size_support_score"],
        "waxs_support_score": waxs_support_snapshot["waxs_support_score"],
        "transition_support_score": (
            self._safe_float(output.get("transition_support_score", 0.0))
            if is_waxs_temperature
            else 0.0
        ),
        "transition_candidate_count": (
            self._safe_float(output.get("transition_candidate_count", 0.0))
            if is_waxs_temperature
            else 0.0
        ),
        "peak_count": ir_support_snapshot["peak_count"],
        "assigned_peak_count": ir_support_snapshot["assigned_peak_count"],
        "reference_band_hit_count": ir_support_snapshot["reference_band_hit_count"],
        "reference_band_missing_count": ir_support_snapshot["reference_band_missing_count"],
        "assignment_confidence_score": ir_support_snapshot["assignment_confidence_score"],
        "key_band_support_score": ir_support_snapshot["key_band_support_score"],
        "baseline_stability_score": ir_support_snapshot["baseline_stability_score"],
        "peak_coverage_score": ir_support_snapshot["peak_coverage_score"],
        "ir_support_score": ir_support_snapshot["ir_support_score"],
        "triggered_constraint_count": ir_support_snapshot["triggered_constraint_count"],
        "unassigned_key_band_count": ir_support_snapshot["unassigned_key_band_count"],
        "classification_basis": ir_support_snapshot["classification_basis"],
        "event_support_score": dsc_support_snapshot["event_support_score"],
        "dsc_baseline_stability_score": dsc_support_snapshot["baseline_stability_score"],
        "thermodynamic_consistency_score": dsc_support_snapshot[
            "thermodynamic_consistency_score"
        ],
        "crystallinity_support_score": dsc_support_snapshot[
            "crystallinity_support_score"
        ],
        "dsc_support_score": dsc_support_snapshot["dsc_support_score"],
        "dsc_scan_r_squared_median": dsc_support_snapshot["scan_r_squared_median"],
        "dsc_scan_r_squared_spread": dsc_support_snapshot["scan_r_squared_spread"],
        "dsc_supported_event_fraction": dsc_support_snapshot[
            "supported_event_fraction"
        ],
        "dsc_supported_component_count": dsc_support_snapshot[
            "supported_component_count"
        ],
        "dsc_triggered_constraint_count": dsc_support_snapshot[
            "triggered_constraint_count"
        ],
        "dsc_validation_passed_count": dsc_support_snapshot[
            "validation_passed_count"
        ],
        "dsc_validation_total_count": dsc_support_snapshot[
            "validation_total_count"
        ],
        "fallback_ratio": saxs_evidence_snapshot["fallback_ratio"],
        "raw_snapshot_rows": saxs_evidence_snapshot["raw_snapshot_rows"],
        "raw_vs_calibrated_gap": saxs_evidence_snapshot["raw_vs_calibrated_gap"],
        "thickness_chain_risk": saxs_evidence_snapshot["thickness_chain_risk"],
        "q_contamination_frame_ratio": saxs_evidence_snapshot[
            "q_contamination_frame_ratio"
        ],
        "mask_truncated_frame_ratio": saxs_evidence_snapshot[
            "mask_truncated_frame_ratio"
        ],
        "low_conf_frame_ratio": saxs_evidence_snapshot["low_conf_frame_ratio"],
        "objective_score": objective_score,
        "quality_flag": quality_flag,
        "validation_summary": validation_summary,
        "residual_type": str(
            residuals_pattern.get("residual_type", "")
            or analysis_evidence.get("residual_evidence", {}).get("residual_type", "")
            or ""
        ).strip(),
        "hard_fail_names": hard_fail_names,
        "soft_warn_count": soft_warn_count,
        "joint_ai_context": joint_ai_context,
        "joint_context_penalty": joint_penalty,
    }
def _stability_snapshot(
    self: Any,
    output: dict[str, Any],
    analysis_evidence: dict[str, Any],
) -> dict[str, Any]:
    if self.technique != "saxs":
        return {
            "stability_score": 1.0,
            "parameter_stability_score": 1.0,
            "method_agreement_score": 1.0,
            "batch_continuity_score": 1.0,
            "stability_flags": [],
        }

    evidence = (
        analysis_evidence.get("stability_evidence", {})
        if isinstance(analysis_evidence, dict)
        else {}
    )
    if not isinstance(evidence, dict):
        evidence = {}

    batch_frames_raw = output.get("batch_frames")
    try:
        batch_frames = int(batch_frames_raw) if batch_frames_raw is not None else 0
    except (TypeError, ValueError):
        batch_frames = 0
    continuity = self._safe_float(output.get("condition_continuity_score"))
    condition_confidence = self._safe_float(output.get("condition_confidence"))
    missing_frames = output.get("condition_missing_frames")
    try:
        missing = int(missing_frames) if missing_frames is not None else 0
    except (TypeError, ValueError):
        missing = 0
    coverage = 1.0
    if batch_frames > 0:
        coverage = max(0.0, min(1.0, 1.0 - (missing / max(batch_frames, 1))))

    def pick(name: str, fallback: float) -> float:
        value = self._safe_float(evidence.get(name))
        return value if value != 0.0 or evidence.get(name) is not None else fallback

    parameter_stability = pick(
        "parameter_stability_score",
        max(
            0.0,
            min(
                1.0,
                (
                    0.45 * self._safe_float(output.get("quality_score", 0.0))
                    + 0.35 * self._safe_float(output.get("L_confidence", 0.0))
                    + 0.20 * self._safe_float(output.get("lc_confidence", 0.0))
                ),
            ),
        ),
    )
    method_agreement = pick("method_agreement_score", 0.5)
    batch_continuity = pick(
        "batch_continuity_score",
        max(
            0.0,
            min(
                1.0,
                (
                    0.45 * continuity + 0.35 * condition_confidence + 0.20 * coverage
                )
                if batch_frames > 1 or continuity or condition_confidence
                else 1.0,
            ),
        ),
    )
    stability_score = pick(
        "stability_score",
        max(
            0.0,
            min(
                1.0,
                0.45 * parameter_stability
                + 0.35 * method_agreement
                + 0.20 * batch_continuity,
            ),
        ),
    )
    flags = evidence.get("stability_flags", [])
    if not isinstance(flags, list):
        flags = []
    return {
        "stability_score": stability_score,
        "parameter_stability_score": parameter_stability,
        "method_agreement_score": method_agreement,
        "batch_continuity_score": batch_continuity,
        "stability_flags": [str(item).strip() for item in flags if str(item).strip()],
    }


def _dsc_support_snapshot(
    self: Any,
    output: dict[str, Any],
    analysis_evidence: dict[str, Any],
) -> dict[str, Any]:
    return _shared_dsc_support_snapshot(self, output, analysis_evidence)


def _waxs_support_snapshot(
    self: Any,
    output: dict[str, Any],
    residuals_pattern: dict[str, Any],
    analysis_evidence: dict[str, Any],
) -> dict[str, float]:
    return _shared_waxs_support_snapshot(self, output, residuals_pattern, analysis_evidence)


def _joint_ai_context(self: Any) -> dict[str, Any]:
    workspace_context = self.workspace_context if isinstance(self.workspace_context, dict) else {}
    joint_ai_context = (
        workspace_context.get("joint_ai_context")
        if isinstance(workspace_context, dict)
        else {}
    )
    return joint_ai_context if isinstance(joint_ai_context, dict) else {}
