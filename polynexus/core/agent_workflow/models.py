"""JSON-safe public contracts for agent-orchestrated analysis workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


CONTRACT_VERSION = "1"
_VALID_INSPECTION_STATUSES = frozenset({"ready", "review_required", "blocked"})
_VALID_RUN_STATUSES = frozenset({"completed", "review_required", "blocked", "failed"})


def _json_safe(value: Any) -> Any:
    """Normalize public contract data and reject values JSON cannot represent."""
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("Agent workflow contracts do not allow non-finite floats")
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    raise TypeError(f"Agent workflow contracts do not support {type(value).__name__}")


def canonical_json(value: Any) -> str:
    """Return stable JSON used for persisted public contract identities."""
    return json.dumps(
        _json_safe(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _hash_payload(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class InputArtifact:
    """A raw input identity and directly observed inspection facts."""

    artifact_id: str
    path: str
    technique: str
    format: str
    sha256: str | None
    header_facts: Mapping[str, Any] = field(default_factory=dict)
    inspection_status: str = "ready"
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.inspection_status not in _VALID_INSPECTION_STATUSES:
            raise ValueError(f"Unsupported inspection status: {self.inspection_status}")
        object.__setattr__(self, "header_facts", _json_safe(dict(self.header_facts)))
        object.__setattr__(self, "reason_codes", tuple(str(code) for code in self.reason_codes))

    @classmethod
    def ready(cls, *, path: str, technique: str, sha256: str, format: str = "") -> "InputArtifact":
        normalized_path = str(path)
        suffix = format or Path(normalized_path).suffix.lower().lstrip(".")
        artifact_id = hashlib.sha256(
            canonical_json({"path": normalized_path, "sha256": sha256}).encode("utf-8")
        ).hexdigest()
        return cls(
            artifact_id=artifact_id,
            path=normalized_path,
            technique=str(technique).lower(),
            format=suffix,
            sha256=sha256,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "path": self.path,
            "technique": self.technique,
            "format": self.format,
            "sha256": self.sha256,
            "header_facts": dict(self.header_facts),
            "inspection_status": self.inspection_status,
            "reason_codes": list(self.reason_codes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "InputArtifact":
        return cls(
            artifact_id=str(payload["artifact_id"]),
            path=str(payload["path"]),
            technique=str(payload.get("technique", "unknown")),
            format=str(payload.get("format", "")),
            sha256=str(payload["sha256"]) if payload.get("sha256") else None,
            header_facts=payload.get("header_facts", {}),
            inspection_status=str(payload.get("inspection_status", "ready")),
            reason_codes=tuple(payload.get("reason_codes", ())),
        )


@dataclass(frozen=True)
class RecipeStep:
    """One declared public provider call in a replayable analysis recipe."""

    step_id: str
    technique: str
    evidence_role: str = "supporting"
    parameters: Mapping[str, Any] = field(default_factory=dict)
    parameter_sources: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "parameters", _json_safe(dict(self.parameters)))
        object.__setattr__(
            self,
            "parameter_sources",
            {str(key): str(value) for key, value in self.parameter_sources.items()},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "technique": self.technique,
            "evidence_role": self.evidence_role,
            "parameters": dict(self.parameters),
            "parameter_sources": dict(self.parameter_sources),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RecipeStep":
        return cls(
            step_id=str(payload["step_id"]),
            technique=str(payload["technique"]),
            evidence_role=str(payload.get("evidence_role", "supporting")),
            parameters=payload.get("parameters", {}),
            parameter_sources=payload.get("parameter_sources", {}),
        )


@dataclass(frozen=True)
class AnalysisRecipe:
    """Versioned immutable recipe with an integrity hash over its public content."""

    workflow_id: str
    contract_version: str
    artifacts: tuple[InputArtifact, ...]
    steps: tuple[RecipeStep, ...]
    recipe_hash: str

    @classmethod
    def create(
        cls,
        *,
        workflow_id: str,
        artifacts: Sequence[InputArtifact],
        steps: Sequence[RecipeStep],
        contract_version: str = CONTRACT_VERSION,
    ) -> "AnalysisRecipe":
        payload = cls._payload(
            workflow_id=workflow_id,
            contract_version=contract_version,
            artifacts=artifacts,
            steps=steps,
        )
        return cls(
            workflow_id=str(workflow_id),
            contract_version=str(contract_version),
            artifacts=tuple(artifacts),
            steps=tuple(steps),
            recipe_hash=_hash_payload(payload),
        )

    @staticmethod
    def _payload(
        *,
        workflow_id: str,
        contract_version: str,
        artifacts: Sequence[InputArtifact],
        steps: Sequence[RecipeStep],
    ) -> dict[str, Any]:
        return {
            "workflow_id": str(workflow_id),
            "contract_version": str(contract_version),
            "artifacts": [artifact.to_dict() for artifact in artifacts],
            "steps": [step.to_dict() for step in steps],
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(
                workflow_id=self.workflow_id,
                contract_version=self.contract_version,
                artifacts=self.artifacts,
                steps=self.steps,
            ),
            "recipe_hash": self.recipe_hash,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AnalysisRecipe":
        artifacts = tuple(InputArtifact.from_dict(item) for item in payload.get("artifacts", ()))
        steps = tuple(RecipeStep.from_dict(item) for item in payload.get("steps", ()))
        recipe = cls.create(
            workflow_id=str(payload["workflow_id"]),
            contract_version=str(payload.get("contract_version", CONTRACT_VERSION)),
            artifacts=artifacts,
            steps=steps,
        )
        expected = str(payload.get("recipe_hash", ""))
        if expected != recipe.recipe_hash:
            raise ValueError("Recipe hash does not match its canonical public content")
        return recipe


@dataclass(frozen=True)
class RecipeProposal:
    """The explicit proposal outcome avoids special return types for blockers."""

    status: str
    recipe: AnalysisRecipe | None = None
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in _VALID_INSPECTION_STATUSES:
            raise ValueError(f"Unsupported proposal status: {self.status}")
        object.__setattr__(self, "reason_codes", tuple(str(code) for code in self.reason_codes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "recipe": self.recipe.to_dict() if self.recipe else None,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class AnalysisRun:
    """Public run envelope that never contains provider-private state."""

    recipe: AnalysisRecipe
    status: str
    reason_codes: tuple[str, ...] = ()
    steps: tuple["WorkflowStepResult", ...] = ()
    evidence: "EvidenceRecord | None" = None
    validated: bool = False

    def __post_init__(self) -> None:
        if self.status not in _VALID_RUN_STATUSES:
            raise ValueError(f"Unsupported run status: {self.status}")
        object.__setattr__(self, "reason_codes", tuple(str(code) for code in self.reason_codes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "recipe": self.recipe.to_dict(),
            "status": self.status,
            "reason_codes": list(self.reason_codes),
            "steps": [step.to_dict() for step in self.steps],
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "validated": self.validated,
        }


@dataclass(frozen=True)
class WorkflowStepResult:
    """A provider result reduced to its stable public summary and evidence."""

    step_id: str
    technique: str
    status: str
    result_summary: Mapping[str, Any] = field(default_factory=dict)
    analysis_evidence: Mapping[str, Any] = field(default_factory=dict)
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in _VALID_RUN_STATUSES:
            raise ValueError(f"Unsupported step status: {self.status}")
        object.__setattr__(self, "result_summary", _json_safe(dict(self.result_summary)))
        object.__setattr__(self, "analysis_evidence", _json_safe(dict(self.analysis_evidence)))
        object.__setattr__(self, "reason_codes", tuple(str(code) for code in self.reason_codes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "technique": self.technique,
            "status": self.status,
            "result_summary": dict(self.result_summary),
            "analysis_evidence": dict(self.analysis_evidence),
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class EvidenceRecord:
    """Explicit scopes prevent an agent from over-promoting a result."""

    observed: tuple[str, ...] = ()
    supported_interpretations: tuple[str, ...] = ()
    disallowed_conclusions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "observed": list(self.observed),
            "supported_interpretations": list(self.supported_interpretations),
            "disallowed_conclusions": list(self.disallowed_conclusions),
        }
