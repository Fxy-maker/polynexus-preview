"""Deterministic diagnostics and bounded analysis-plan candidate evaluation."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class AnalysisSymptom:
    code: str
    severity: float
    priority: int
    value: float


@dataclass(frozen=True)
class CandidateEvaluation:
    candidate_id: str
    status: str
    score: float
    protected_metrics: tuple[str, ...]
    reasons: tuple[str, ...] = ()
    metrics: Mapping[str, float] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "protected_metrics", tuple(str(value) for value in self.protected_metrics))
        object.__setattr__(self, "reasons", tuple(str(value) for value in self.reasons))
        object.__setattr__(self, "metrics", dict(self.metrics or {}))


def diagnose_symptoms(observations: Mapping[str, Any]) -> tuple[AnalysisSymptom, ...]:
    rules = (
        ("baseline_drift", "baseline_drift", 0.5),
        ("peak_instability", "peak_instability", 0.5),
        ("noisy_frames", "noisy_frames", 0.5),
        ("trend_discontinuity", "trend_discontinuity", 0.5),
        ("trend_gap", "trend_discontinuity", 0.5),
        ("cross_technique_disagreement", "cross_technique_disagreement", 0.5),
    )
    found: list[AnalysisSymptom] = []
    for priority, (input_code, code, threshold) in enumerate(rules, start=1):
        try:
            value = float(observations.get(input_code, 0.0))
        except (TypeError, ValueError):
            continue
        if math.isfinite(value) and value >= threshold:
            found.append(AnalysisSymptom(code, value, priority, value))
    return tuple(sorted(found, key=lambda item: (-item.severity, item.priority)))


def evaluate_candidates(
    *,
    default_config: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    observations: Mapping[str, Any],
    thresholds: Mapping[str, Any],
    protected_metrics: Sequence[str],
) -> tuple[CandidateEvaluation, ...]:
    evaluations: list[CandidateEvaluation] = []
    for candidate in candidates:
        candidate_id = str(candidate.get("id", ""))
        config = candidate.get("config")
        if not candidate_id or not isinstance(config, Mapping):
            raise ValueError("candidate config must contain id and mapping config")
        if set(config) - set(default_config):
            raise ValueError("candidate config contains an unknown parameter")
        reasons: list[str] = []
        for key, value in config.items():
            if not key.endswith("window"):
                continue
            try:
                numeric = int(value)
            except (TypeError, ValueError) as exc:
                raise ValueError("candidate config window is outside bounded range") from exc
            if numeric > 1000:
                raise ValueError("candidate config window is outside bounded range")
            if not 1 <= numeric <= 51 or numeric % 2 == 0:
                reasons.append("smooth_window_outside_bounded_range")
        metrics = _finite_metrics(observations)
        try:
            if metrics.get("peak_shift", 0.0) > float(thresholds.get("max_peak_shift", math.inf)):
                reasons.append("peak_shift_exceeds_threshold")
            if metrics.get("peak_retention", 1.0) < float(thresholds.get("min_peak_retention", -math.inf)):
                reasons.append("protected_peak_retention_below_threshold")
        except (TypeError, ValueError):
            reasons.append("threshold_invalid")
        score = (
            metrics.get("baseline_residual", 0.0)
            + metrics.get("peak_shift", 0.0)
            + (1.0 - metrics.get("peak_retention", 1.0))
            + metrics.get("runtime_s", 0.0) * 0.001
        )
        if config.get("smooth_window", default_config.get("smooth_window")) not in {default_config.get("smooth_window"), None}:
            try:
                if int(config["smooth_window"]) > 51:
                    reasons.append("smooth_window_unbounded")
            except (TypeError, ValueError):
                reasons.append("smooth_window_invalid")
        status = "unusable" if reasons else ("sensitive" if score > 1.0 else "stable")
        evaluations.append(CandidateEvaluation(candidate_id, status, float(score), tuple(protected_metrics), tuple(reasons), metrics))
    return tuple(evaluations)


def _finite_metrics(observations: Mapping[str, Any]) -> dict[str, float]:
    result: dict[str, float] = {}
    for key, value in observations.items():
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(numeric):
            result[str(key)] = numeric
    return result


__all__ = ["AnalysisSymptom", "CandidateEvaluation", "diagnose_symptoms", "evaluate_candidates"]
