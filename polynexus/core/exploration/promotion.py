"""Explicit, evidence-gated capability promotion for explorations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from polynexus.core.ai_platform.capabilities import CapabilityDescriptor
from polynexus.core.ai_platform.contracts import canonical_json_hash


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
        object.__setattr__(self, "details", dict(details))

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "evidence_id": self.evidence_id,
            "passed": self.passed,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class CapabilityPromotionAssessment:
    """Immutable result of checking all promotion gates."""

    source_descriptor_hash: str
    proposed_descriptor: CapabilityDescriptor
    evidence: tuple[CapabilityPromotionEvidence, ...]
    human_scientific_review: bool = False
    assessment_hash: str = ""

    REQUIRED_KINDS = frozenset({"independent_replay", "standard_sample", "negative_control", "uncertainty"})

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
    "CapabilityPromotionService",
]
