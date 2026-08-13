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

    def to_dict(self) -> dict[str, Any]:
        return {"candidate_id": self.candidate_id, "status": self.status, "score": self.score, "protected_metrics": list(self.protected_metrics), "reasons": list(self.reasons), "metrics": dict(self.metrics)}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CandidateEvaluation":
        return cls(str(value["candidate_id"]), str(value["status"]), float(value["score"]), tuple(value.get("protected_metrics", ())), tuple(value.get("reasons", ())), value.get("metrics", {}))


@dataclass(frozen=True)
class AnalysisPlanEvaluation:
    plan_id: str
    plan_hash: str = ""
    plan_version: str = ""
    symptoms: tuple[AnalysisSymptom, ...] = ()
    candidates: tuple[CandidateEvaluation, ...] = ()
    selected_candidate_id: str | None = None
    review_required: bool = True
    review_limits: tuple[str, ...] = ()
    replay: Mapping[str, Any] = None

    @classmethod
    def create(
        cls,
        *,
        plan_id: str,
        plan_hash: str = "",
        plan_version: str = "",
        symptoms=(),
        candidates=(),
        selected_candidate_id=None,
        review_required=True,
        review_limits=(),
        replay=None,
    ):
        return cls(
            str(plan_id),
            str(plan_hash or ""),
            str(plan_version or ""),
            tuple(symptoms),
            tuple(candidates),
            selected_candidate_id,
            bool(review_required),
            tuple(str(value) for value in review_limits),
            dict(replay or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "plan_hash": self.plan_hash,
            "plan_version": self.plan_version,
            "symptoms": [{"code": item.code, "severity": item.severity, "priority": item.priority, "value": item.value} for item in self.symptoms],
            "candidates": [item.to_dict() for item in self.candidates],
            "selected_candidate_id": self.selected_candidate_id,
            "review_required": self.review_required,
            "review_limits": list(self.review_limits),
            "replay": dict(self.replay or {}),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AnalysisPlanEvaluation":
        symptoms = tuple(AnalysisSymptom(str(item["code"]), float(item["severity"]), int(item["priority"]), float(item["value"])) for item in value.get("symptoms", ()))
        candidates = tuple(CandidateEvaluation.from_dict(item) for item in value.get("candidates", ()))
        return cls.create(
            plan_id=str(value["plan_id"]),
            plan_hash=str(value.get("plan_hash", "")),
            plan_version=str(value.get("plan_version", "")),
            symptoms=symptoms,
            candidates=candidates,
            selected_candidate_id=value.get("selected_candidate_id"),
            review_required=bool(value.get("review_required", True)),
            review_limits=value.get("review_limits", ()),
            replay=value.get("replay", {}),
        )


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


def project_analysis_plan_evaluation(plan: Any, evaluation: AnalysisPlanEvaluation) -> dict[str, Any]:
    """Project one plan and its evaluation into the shared AI/GUI/ARS JSON view."""
    plan_id = str(getattr(plan, "plan_id", ""))
    plan_hash = str(getattr(plan, "plan_hash", ""))
    if not plan_id or not plan_hash or evaluation.plan_id != plan_id:
        raise ValueError("analysis plan and evaluation identity do not match")
    if evaluation.plan_hash and evaluation.plan_hash != plan_hash:
        raise ValueError("analysis plan and evaluation hash do not match")
    plan_replay = getattr(plan, "replay", {})
    replay = dict(evaluation.replay or plan_replay or {})
    return {
        "version": 1,
        "plan_id": plan_id,
        "plan_hash": plan_hash,
        "plan_version": str(getattr(plan, "plan_version", "")),
        "analysis_intent": getattr(plan, "analysis_intent", None),
        "candidates": [item.to_dict() for item in evaluation.candidates],
        "symptoms": [
            {"code": item.code, "severity": item.severity, "priority": item.priority, "value": item.value}
            for item in evaluation.symptoms
        ],
        "selected_candidate_id": evaluation.selected_candidate_id,
        "review_required": bool(evaluation.review_required),
        "review_limits": list(evaluation.review_limits),
        "replay": replay,
    }


__all__ = ["AnalysisSymptom", "CandidateEvaluation", "AnalysisPlanEvaluation", "diagnose_symptoms", "evaluate_candidates", "project_analysis_plan_evaluation"]
