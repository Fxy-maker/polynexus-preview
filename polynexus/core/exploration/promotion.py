"""Explicit, evidence-gated capability promotion for explorations."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from polynexus.core.ai_platform.capabilities import CapabilityDescriptor
from polynexus.core.ai_platform.contracts import canonical_json_hash


_REQUIRED_KINDS = (
    "independent_replay",
    "standard_sample",
    "negative_control",
    "uncertainty",
)
_AI_PREPARATION_ACTIONS = {
    "independent_replay": "prepare_independent_replay_from_admitted_inputs",
    "standard_sample": "prepare_standard_sample_comparison_from_admitted_inputs",
    "negative_control": "prepare_negative_control_comparison_from_admitted_inputs",
    "uncertainty": "prepare_uncertainty_assessment_from_admitted_inputs",
}


def _public(value: Any) -> Any:
    canonical_json_hash(value)
    if isinstance(value, Mapping):
        return {str(key): _public(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_public(item) for item in value]
    return value


def _freeze(value: Any) -> Any:
    public = _public(value)
    if isinstance(public, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in public.items()})
    if isinstance(public, list):
        return tuple(_freeze(item) for item in public)
    return public


@dataclass(frozen=True)
class CapabilityPromotionEvidence:
    """One independently produced promotion check."""

    kind: str
    evidence_id: str
    passed: bool
    details: Mapping[str, Any] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        kind = str(self.kind).strip()
        evidence_id = str(self.evidence_id).strip()
        if not kind or not evidence_id:
            raise ValueError("promotion evidence kind and evidence_id must be nonempty")
        if not isinstance(self.passed, bool):
            raise TypeError("promotion evidence passed must be boolean")
        details = {} if self.details is None else self.details
        if not isinstance(details, Mapping):
            raise TypeError("promotion evidence details must be a mapping")
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "evidence_id", evidence_id)
        object.__setattr__(self, "details", _freeze(details))

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "evidence_id": self.evidence_id,
            "passed": self.passed,
            "details": _public(self.details),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CapabilityPromotionEvidence":
        if not isinstance(value, Mapping):
            raise TypeError("promotion evidence must be a mapping")
        return cls(
            kind=value["kind"],
            evidence_id=value["evidence_id"],
            passed=value["passed"],
            details=value.get("details", {}),
        )


@dataclass(frozen=True)
class CapabilityPromotionReadiness:
    """Shared plan for AI evidence preparation before human review.

    The object is intentionally not a promotion decision. AI can use its
    preparation actions after real inputs have entered Core contracts, while a
    complete evidence set remains explicitly pending scientific review.
    """

    descriptor: CapabilityDescriptor
    evidence: tuple[CapabilityPromotionEvidence, ...]
    satisfied_evidence_kinds: tuple[str, ...]
    missing_evidence_kinds: tuple[str, ...]
    failed_evidence_kinds: tuple[str, ...]
    ai_preparation_actions: tuple[str, ...]
    human_actions: tuple[str, ...]
    ready_for_human_scientific_review: bool
    automatically_promotable: bool = False
    readiness_hash: str = ""
    schema_version: str = "1"

    SCHEMA_VERSION = "1"
    REQUIRED_KINDS = _REQUIRED_KINDS

    def __post_init__(self) -> None:
        if self.schema_version != self.SCHEMA_VERSION:
            raise ValueError("Unsupported capability promotion readiness schema_version")
        if type(self.descriptor) is not CapabilityDescriptor:
            raise TypeError("promotion readiness requires an exact CapabilityDescriptor")
        if isinstance(self.evidence, (str, bytes, bytearray)) or not isinstance(
            self.evidence, Sequence
        ):
            raise TypeError("promotion readiness evidence must be a sequence")
        evidence = tuple(self.evidence)
        if not all(type(item) is CapabilityPromotionEvidence for item in evidence):
            raise TypeError("promotion readiness evidence must contain exact evidence values")
        kinds = [item.kind for item in evidence]
        if len(kinds) != len(set(kinds)):
            raise ValueError("promotion readiness evidence kinds must be unique")
        object.__setattr__(self, "evidence", evidence)

        by_kind = {item.kind: item for item in evidence}
        satisfied = tuple(
            kind for kind in self.REQUIRED_KINDS if by_kind.get(kind) is not None and by_kind[kind].passed
        )
        failed = tuple(
            kind for kind in self.REQUIRED_KINDS if by_kind.get(kind) is not None and not by_kind[kind].passed
        )
        missing = tuple(kind for kind in self.REQUIRED_KINDS if kind not in by_kind)
        actions = tuple(_AI_PREPARATION_ACTIONS[kind] for kind in self.REQUIRED_KINDS if kind in failed or kind in missing)
        ready = not missing and not failed

        if self.satisfied_evidence_kinds != satisfied:
            raise ValueError("promotion readiness satisfied evidence does not match records")
        if self.missing_evidence_kinds != missing:
            raise ValueError("promotion readiness missing evidence does not match records")
        if self.failed_evidence_kinds != failed:
            raise ValueError("promotion readiness failed evidence does not match records")
        if self.ai_preparation_actions != actions:
            raise ValueError("promotion readiness AI actions do not match evidence")
        if self.human_actions != ("human_scientific_review_required",):
            raise ValueError("promotion readiness must retain the human scientific review action")
        if self.ready_for_human_scientific_review is not ready:
            raise ValueError("promotion readiness review state does not match evidence")
        if self.automatically_promotable is not False:
            raise ValueError("AI readiness must never make a capability automatically promotable")

        expected_hash = canonical_json_hash(self._identity_payload())
        if self.readiness_hash and self.readiness_hash != expected_hash:
            raise ValueError("promotion readiness hash does not match its content")
        object.__setattr__(self, "readiness_hash", expected_hash)

    @classmethod
    def create(
        cls,
        *,
        descriptor: CapabilityDescriptor,
        evidence: Sequence[CapabilityPromotionEvidence],
    ) -> "CapabilityPromotionReadiness":
        if type(descriptor) is not CapabilityDescriptor:
            raise TypeError("promotion readiness requires an exact CapabilityDescriptor")
        evidence_tuple = tuple(evidence)
        if not all(type(item) is CapabilityPromotionEvidence for item in evidence_tuple):
            raise TypeError("promotion readiness evidence must contain exact evidence values")
        kinds = [item.kind for item in evidence_tuple]
        if len(kinds) != len(set(kinds)):
            raise ValueError("promotion readiness evidence kinds must be unique")
        by_kind = {item.kind: item for item in evidence_tuple}
        satisfied = tuple(
            kind for kind in cls.REQUIRED_KINDS if by_kind.get(kind) is not None and by_kind[kind].passed
        )
        failed = tuple(
            kind for kind in cls.REQUIRED_KINDS if by_kind.get(kind) is not None and not by_kind[kind].passed
        )
        missing = tuple(kind for kind in cls.REQUIRED_KINDS if kind not in by_kind)
        return cls(
            descriptor=descriptor,
            evidence=evidence_tuple,
            satisfied_evidence_kinds=satisfied,
            missing_evidence_kinds=missing,
            failed_evidence_kinds=failed,
            ai_preparation_actions=tuple(
                _AI_PREPARATION_ACTIONS[kind]
                for kind in cls.REQUIRED_KINDS
                if kind in failed or kind in missing
            ),
            human_actions=("human_scientific_review_required",),
            ready_for_human_scientific_review=not missing and not failed,
        )

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "descriptor": self.descriptor.to_dict(),
            "evidence": [item.to_dict() for item in self.evidence],
            "satisfied_evidence_kinds": list(self.satisfied_evidence_kinds),
            "missing_evidence_kinds": list(self.missing_evidence_kinds),
            "failed_evidence_kinds": list(self.failed_evidence_kinds),
            "ai_preparation_actions": list(self.ai_preparation_actions),
            "human_actions": list(self.human_actions),
            "ready_for_human_scientific_review": self.ready_for_human_scientific_review,
            "automatically_promotable": False,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._identity_payload(), "readiness_hash": self.readiness_hash}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CapabilityPromotionReadiness":
        if not isinstance(value, Mapping):
            raise TypeError("promotion readiness must be a mapping")
        return cls(
            descriptor=CapabilityDescriptor.from_dict(value["descriptor"]),
            evidence=tuple(
                CapabilityPromotionEvidence.from_dict(item) for item in value.get("evidence", ())
            ),
            satisfied_evidence_kinds=tuple(value.get("satisfied_evidence_kinds", ())),
            missing_evidence_kinds=tuple(value.get("missing_evidence_kinds", ())),
            failed_evidence_kinds=tuple(value.get("failed_evidence_kinds", ())),
            ai_preparation_actions=tuple(value.get("ai_preparation_actions", ())),
            human_actions=tuple(value.get("human_actions", ())),
            ready_for_human_scientific_review=value.get("ready_for_human_scientific_review"),
            automatically_promotable=value.get("automatically_promotable", False),
            readiness_hash=value.get("readiness_hash", ""),
            schema_version=value.get("schema_version", ""),
        )


@dataclass(frozen=True)
class CapabilityPromotionAssessment:
    """Immutable result of checking all promotion gates."""

    source_descriptor_hash: str
    proposed_descriptor: CapabilityDescriptor
    evidence: tuple[CapabilityPromotionEvidence, ...]
    human_scientific_review: bool = False
    assessment_hash: str = ""

    REQUIRED_KINDS = frozenset(_REQUIRED_KINDS)

    def __post_init__(self) -> None:
        if type(self.proposed_descriptor) is not CapabilityDescriptor:
            raise TypeError("proposed_descriptor must be a CapabilityDescriptor")
        source_hash = str(self.source_descriptor_hash).strip()
        if source_hash != self.proposed_descriptor.content_hash:
            raise ValueError("source_descriptor_hash must match proposed descriptor content")
        object.__setattr__(self, "source_descriptor_hash", source_hash)
        if isinstance(self.evidence, (str, bytes, bytearray)):
            raise TypeError("promotion evidence must be a sequence")
        evidence = tuple(self.evidence)
        if not all(type(item) is CapabilityPromotionEvidence for item in evidence):
            raise TypeError("promotion evidence must contain exact CapabilityPromotionEvidence values")
        kinds = [item.kind for item in evidence]
        if len(kinds) != len(set(kinds)):
            raise ValueError("promotion evidence kinds must be unique")
        object.__setattr__(self, "evidence", evidence)
        if not isinstance(self.human_scientific_review, bool):
            raise TypeError("human_scientific_review must be boolean")
        expected = canonical_json_hash(self._payload())
        if self.assessment_hash and self.assessment_hash != expected:
            raise ValueError("promotion assessment hash does not match its content")
        object.__setattr__(self, "assessment_hash", expected)

    @property
    def passed(self) -> bool:
        by_kind = {item.kind: item for item in self.evidence}
        return (
            self.human_scientific_review
            and self.REQUIRED_KINDS.issubset(by_kind)
            and all(by_kind[kind].passed for kind in self.REQUIRED_KINDS)
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "source_descriptor_hash": self.source_descriptor_hash,
            "proposed_descriptor": self.proposed_descriptor.to_dict(),
            "evidence": [item.to_dict() for item in self.evidence],
            "human_scientific_review": self.human_scientific_review,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "assessment_hash": self.assessment_hash, "passed": self.passed}


class CapabilityPromotionService:
    """Create a new available descriptor only after explicit human review."""

    @staticmethod
    def assess(
        descriptor: CapabilityDescriptor,
        evidence: Sequence[CapabilityPromotionEvidence],
        *,
        human_scientific_review: bool = False,
    ) -> CapabilityPromotionAssessment:
        if type(descriptor) is not CapabilityDescriptor:
            raise TypeError("promotion requires an exact CapabilityDescriptor")
        return CapabilityPromotionAssessment(
            source_descriptor_hash=descriptor.content_hash,
            proposed_descriptor=descriptor,
            evidence=tuple(evidence),
            human_scientific_review=human_scientific_review,
        )

    @staticmethod
    def readiness(
        descriptor: CapabilityDescriptor,
        evidence: Sequence[CapabilityPromotionEvidence],
    ) -> CapabilityPromotionReadiness:
        """Return AI-readable next actions without promoting any capability."""

        return CapabilityPromotionReadiness.create(
            descriptor=descriptor,
            evidence=evidence,
        )

    @staticmethod
    def promote(assessment: CapabilityPromotionAssessment) -> CapabilityDescriptor:
        if type(assessment) is not CapabilityPromotionAssessment:
            raise TypeError("promotion requires a CapabilityPromotionAssessment")
        if not assessment.passed:
            raise ValueError("capability promotion gates are not satisfied")
        descriptor = assessment.proposed_descriptor
        if descriptor.status == "available":
            raise ValueError("promotion requires a new descriptor version, not an already available descriptor")
        return CapabilityDescriptor.create(
            capability_id=descriptor.capability_id,
            version=f"{descriptor.version}.promoted",
            techniques=descriptor.techniques,
            input_contract=descriptor.input_contract,
            output_schema=descriptor.output_schema,
            preconditions=descriptor.preconditions,
            dependencies=descriptor.dependencies,
            alternatives=descriptor.alternatives,
            uncertainty_policy=descriptor.uncertainty_policy,
            status="available",
            executor_key=descriptor.executor_key,
            missing_input_actions=descriptor.missing_input_actions,
            evidence_policy={
                **dict(descriptor.evidence_policy),
                "promotion_assessment_hash": assessment.assessment_hash,
            },
            cost=descriptor.cost,
            failure_reason_codes=descriptor.failure_reason_codes,
            aliases=descriptor.aliases,
            schema_version=descriptor.schema_version,
        )


__all__ = [
    "CapabilityPromotionAssessment",
    "CapabilityPromotionEvidence",
    "CapabilityPromotionReadiness",
    "CapabilityPromotionService",
]
