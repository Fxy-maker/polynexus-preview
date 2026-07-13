from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from numbers import Real
from typing import Any

from .contracts import PreprocessEvidence
from .policy import PreprocessPolicy


@dataclass(frozen=True)
class DecisionOutcome:
    decision: str
    simulated_decision: str
    confidence_band: str
    confidence_score: float
    score_components: dict[str, float]
    hard_guard_results: dict[str, bool]
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["reason_codes"] = list(self.reason_codes)
        return payload


def _finite(value: object) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(float(value))


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _metric_value(evidence: PreprocessEvidence, name: str) -> object:
    return getattr(evidence, name, None)


def _hard_guards(
    evidence: PreprocessEvidence,
    policy: PreprocessPolicy,
) -> tuple[dict[str, bool], list[str]]:
    results: dict[str, bool] = {"run_status": evidence.run_status == "ok"}
    reasons: list[str] = []
    if not results["run_status"]:
        reasons.append("run_status")

    for name in policy.required_evidence:
        value = _metric_value(evidence, name)
        if not _finite(value):
            results[name] = False
            reasons.append(f"required_evidence_missing:{name}")

    limit_rules = (
        ("evidence_coverage", "evidence_coverage_min", "min"),
        ("negative_fraction", "negative_fraction_max", "max"),
        ("peak_shift", "peak_shift_max", "max"),
        ("fwhm_change", "fwhm_change_max", "max"),
        ("integrated_area_change", "integrated_area_change_max", "max"),
        ("weak_peak_retention", "weak_peak_retention_min", "min"),
        ("physical_parameter_drift", "physical_parameter_drift_max", "max"),
    )
    for metric_name, limit_name, direction in limit_rules:
        value = _metric_value(evidence, metric_name)
        limit = policy.hard_limits.get(limit_name)
        if not _finite(value) or not _finite(limit):
            passed = False
        elif direction == "min":
            passed = float(value) >= float(limit)
        else:
            passed = float(value) <= float(limit)
        results[metric_name] = passed
        if not passed and metric_name not in reasons:
            reasons.append(metric_name)

    technique_guards = (
        ("cross_boundary_smoothing", False),
        ("zero_fill_unchanged", True),
    )
    for name, expected in technique_guards:
        if name not in evidence.technique_specific:
            continue
        passed = evidence.technique_specific[name] is expected
        results[name] = passed
        if not passed:
            reasons.append(name)

    noise_gain = float(evidence.noise_reduction) if _finite(evidence.noise_reduction) else 0.0
    baseline_gain = (
        float(evidence.baseline_flatness) if _finite(evidence.baseline_flatness) else 0.0
    )
    results["preprocess_gain"] = noise_gain > 0.0 or baseline_gain > 0.0
    if not results["preprocess_gain"]:
        reasons.append("no_preprocess_gain")
    return results, reasons


def _preservation_score(value: float | None, limit: float) -> float:
    if not _finite(value) or limit <= 0:
        return 0.0
    return _clamp(1.0 - float(value) / limit)


def _score_components(
    evidence: PreprocessEvidence,
    policy: PreprocessPolicy,
    candidate_margin: float,
) -> dict[str, float]:
    hard = policy.hard_limits
    signal_parts = [
        _preservation_score(evidence.peak_shift, hard["peak_shift_max"]),
        _preservation_score(evidence.fwhm_change, hard["fwhm_change_max"]),
        _preservation_score(
            evidence.integrated_area_change,
            hard["integrated_area_change_max"],
        ),
        _clamp(float(evidence.weak_peak_retention or 0.0)),
        _preservation_score(evidence.negative_fraction, hard["negative_fraction_max"]),
    ]
    stability = evidence.technique_specific.get("sensitivity_stability", 0.5)
    return {
        "noise_improvement": _clamp(float(evidence.noise_reduction or 0.0) / 0.20),
        "baseline_improvement": _clamp(float(evidence.baseline_flatness or 0.0) / 0.15),
        "signal_preservation": sum(signal_parts) / len(signal_parts),
        "physical_preservation": _preservation_score(
            evidence.physical_parameter_drift,
            hard["physical_parameter_drift_max"],
        ),
        "stability": _clamp(float(stability)) if _finite(stability) else 0.0,
        "candidate_margin": _clamp(
            float(candidate_margin) / max(policy.min_candidate_margin, 1e-12)
        )
        if _finite(candidate_margin)
        else 0.0,
    }


def _weighted_score(components: dict[str, float], policy: PreprocessPolicy) -> float:
    weight_sum = sum(
        weight
        for name, weight in policy.score_weights.items()
        if weight > 0 and name in components
    )
    if weight_sum <= 0:
        return 0.0
    return _clamp(
        sum(
            components[name] * weight
            for name, weight in policy.score_weights.items()
            if weight > 0 and name in components
        )
        / weight_sum
    )


def _band(score: float, policy: PreprocessPolicy) -> str:
    if score >= policy.high_threshold:
        return "high"
    if score >= policy.medium_threshold:
        return "medium"
    return "low"


def _simulated_decision(confidence_band: str) -> str:
    if confidence_band == "high":
        return "auto_accept"
    if confidence_band == "medium":
        return "request_confirmation"
    return "keep_original"


def decide_preprocess_candidate(
    evidence: PreprocessEvidence,
    policy: PreprocessPolicy,
    *,
    candidate_margin: float,
    metadata_complete: bool,
) -> DecisionOutcome:
    guard_results, reasons = _hard_guards(evidence, policy)
    if not all(guard_results.values()):
        return DecisionOutcome(
            decision="keep_original",
            simulated_decision="keep_original",
            confidence_band="low",
            confidence_score=0.0,
            score_components={},
            hard_guard_results=guard_results,
            reason_codes=tuple(dict.fromkeys(reasons)),
        )

    components = _score_components(evidence, policy, candidate_margin)
    score = _weighted_score(components, policy)
    confidence_band = _band(score, policy)
    if confidence_band == "high" and not metadata_complete:
        confidence_band = "medium"
        reasons.append("metadata_incomplete")

    simulated = _simulated_decision(confidence_band)
    if policy.automation_state == "shadow":
        decision = "keep_original"
        reasons.append("shadow_mode")
    elif policy.automation_state == "confirm_only" and simulated != "keep_original":
        decision = "request_confirmation"
        reasons.append("confirmation_required")
    else:
        decision = simulated
    if confidence_band == "low":
        reasons.append("insufficient_confidence")

    return DecisionOutcome(
        decision=decision,
        simulated_decision=simulated,
        confidence_band=confidence_band,
        confidence_score=score,
        score_components=components,
        hard_guard_results=guard_results,
        reason_codes=tuple(dict.fromkeys(reasons)),
    )
