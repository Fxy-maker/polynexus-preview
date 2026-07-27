"""SAXS bridge into the shared preprocessing candidate/decision contracts.

The bridge treats model-provided intents as untrusted input.  It creates
candidate-only plans and delegates all evidence gates and automation-state
semantics to ``preprocess_optimization``; it never applies a candidate.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from collections.abc import Mapping, Sequence
from typing import Any

from ..preprocess_optimization import (
    DecisionOutcome,
    PreprocessCandidate,
    PreprocessEvidence,
    PreprocessIntent,
    PreprocessPolicy,
    generate_preprocess_candidates,
    get_preprocess_adapter,
    get_preprocess_policy,
    parse_preprocess_intent,
)
from ..preprocess_optimization.decision import decide_preprocess_candidate
from ..preprocess_optimization.intent_schema import ContractValidationError
from ..preprocess_optimization.policy import PolicyValidationError


_REQUIRED_PROTECTED_FEATURES = frozenset(
    {
        "weak_peaks",
        "integrated_area",
        "guinier_region",
        "beamstop_boundaries",
        "peak_position",
        "peak_width",
        "physical_parameters",
    }
)


@dataclass(frozen=True)
class SAXSAIRescuePlan:
    """Candidate-only plan produced from a validated SAXS AI intent."""

    intent: PreprocessIntent
    candidates: tuple[PreprocessCandidate, ...]
    policy_version: str
    automation_state: str = "shadow"
    candidate_only: bool = True
    original_preserved: bool = True
    physical_validation_required: bool = True
    reason_codes: tuple[str, ...] = (
        "candidate_only",
        "original_preserved",
        "physical_validation_required",
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent.to_dict(),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "policy_version": self.policy_version,
            "automation_state": self.automation_state,
            "candidate_only": self.candidate_only,
            "original_preserved": self.original_preserved,
            "physical_validation_required": self.physical_validation_required,
            "reason_codes": list(self.reason_codes),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)


@dataclass(frozen=True)
class SAXSAIRescueDecision:
    """Auditable wrapper around the shared preprocessing decision outcome."""

    outcome: DecisionOutcome
    original_preserved: bool = True
    physical_validation_required: bool = True
    apply_allowed: bool = False

    @property
    def decision(self) -> str:
        return self.outcome.decision

    @property
    def simulated_decision(self) -> str:
        return self.outcome.simulated_decision

    @property
    def reason_codes(self) -> tuple[str, ...]:
        return self.outcome.reason_codes

    def to_dict(self) -> dict[str, Any]:
        payload = self.outcome.to_dict()
        payload.update(
            {
                "original_preserved": self.original_preserved,
                "physical_validation_required": self.physical_validation_required,
                "apply_allowed": self.apply_allowed,
            }
        )
        return payload

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)


def _validated_intent(payload: Mapping[str, Any], policy: PreprocessPolicy) -> PreprocessIntent:
    try:
        intent = parse_preprocess_intent(dict(payload))
    except (ContractValidationError, TypeError, ValueError):
        raise
    if intent.technique.upper() != "SAXS":
        raise ContractValidationError("SAXS AI intent must use technique SAXS")
    missing = _REQUIRED_PROTECTED_FEATURES - set(intent.protected_features)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ContractValidationError(f"SAXS AI intent missing protected features: {missing_text}")
    try:
        policy.validate_intent(intent)
    except PolicyValidationError as exc:
        raise ContractValidationError(str(exc)) from exc
    return intent


def validate_saxs_ai_intent(
    intent_payload: Mapping[str, Any],
    *,
    policy: PreprocessPolicy | None = None,
) -> PreprocessIntent:
    """Validate a SAXS intent without generating or executing candidates."""

    selected_policy = policy or get_preprocess_policy("SAXS")
    if selected_policy.technique.upper() != "SAXS":
        raise PolicyValidationError("SAXS rescue requires the SAXS preprocessing policy")
    return _validated_intent(intent_payload, selected_policy)


def build_saxs_ai_rescue_plan(
    intent_payload: Mapping[str, Any],
    base_config: Mapping[str, Any],
    *,
    policy: PreprocessPolicy | None = None,
    experience_deltas: Sequence[Mapping[str, Any]] = (),
) -> SAXSAIRescuePlan:
    """Validate an AI intent and generate bounded SAXS candidates only."""

    selected_policy = policy or get_preprocess_policy("SAXS")
    intent = validate_saxs_ai_intent(intent_payload, policy=selected_policy)
    candidates = generate_preprocess_candidates(
        intent,
        dict(base_config),
        selected_policy,
        get_preprocess_adapter("SAXS"),
        experience_deltas=[dict(delta) for delta in experience_deltas],
    )
    return SAXSAIRescuePlan(
        intent=intent,
        candidates=tuple(candidates),
        policy_version=selected_policy.policy_version,
        automation_state=selected_policy.automation_state,
    )


def assess_saxs_ai_candidate(
    evidence: PreprocessEvidence,
    *,
    candidate_margin: float,
    metadata_complete: bool,
    automation_state: str | None = None,
    policy: PreprocessPolicy | None = None,
) -> SAXSAIRescueDecision:
    """Evaluate candidate evidence through the shared SAXS decision policy."""

    selected_policy = policy or get_preprocess_policy("SAXS")
    if selected_policy.technique.upper() != "SAXS":
        raise PolicyValidationError("SAXS AI decision requires the SAXS preprocessing policy")
    if automation_state is not None and automation_state != selected_policy.automation_state:
        selected_policy = selected_policy.with_automation_state(automation_state)
    outcome = decide_preprocess_candidate(
        evidence,
        selected_policy,
        candidate_margin=candidate_margin,
        metadata_complete=metadata_complete,
    )
    apply_allowed = bool(
        outcome.decision == "auto_accept"
        and all(outcome.hard_guard_results.values())
    )
    return SAXSAIRescueDecision(
        outcome=outcome,
        original_preserved=True,
        physical_validation_required=True,
        apply_allowed=apply_allowed,
    )


__all__ = [
    "SAXSAIRescueDecision",
    "SAXSAIRescuePlan",
    "assess_saxs_ai_candidate",
    "build_saxs_ai_rescue_plan",
    "validate_saxs_ai_intent",
]
