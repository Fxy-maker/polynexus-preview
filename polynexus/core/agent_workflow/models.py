"""JSON-safe public contracts for agent-orchestrated analysis workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from polynexus.core.artifacts import raw_artifact_id


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


def _freeze_json_value(value: Any) -> Any:
    """Recursively freeze JSON-safe data retained by a public contract."""
    normalized = _json_safe(value)
    if isinstance(normalized, Mapping):
        return MappingProxyType({str(key): _freeze_json_value(item) for key, item in normalized.items()})
    if isinstance(normalized, list):
        return tuple(_freeze_json_value(item) for item in normalized)
    return normalized


def _normalize_computation_state(value: Any):
    """Validate and freeze the shared four-axis computation state."""

    if value is None:
        return None
    from polynexus.core.ai_platform.contracts import ComputationState

    # A subclass may override ``to_dict``/axis properties and therefore is
    # not an attestation of the canonical state contract.  Requiring the exact
    # DTO keeps workflow/evidence projections on the same non-polymorphic
    # trust boundary as the Core execution contracts.
    if type(value) is ComputationState:
        value = value.to_dict()
    elif isinstance(value, ComputationState):
        raise TypeError("Workflow computation_state must use the exact ComputationState type")
    elif not isinstance(value, Mapping):
        raise TypeError("Workflow computation_state must be a ComputationState or mapping")
    # Parsing through the canonical contract catches malformed or incomplete
    # axes before an agent/evidence bundle can persist them.
    state = ComputationState.from_dict(value)
    return state


def _projection_state_alias(value: Mapping[str, Any]) -> Any:
    """Resolve ``computation_state``/``state`` without hiding conflicts."""

    candidates: list[Any] = []
    containers: list[Mapping[str, Any]] = [value]
    nested_result = value.get("result")
    if isinstance(nested_result, Mapping):
        containers.append(nested_result)
    for container in containers:
        for key in ("computation_state", "state"):
            if key not in container or container[key] is None:
                continue
            candidate = container[key]
            # ``state`` is a historical provider alias and is often a free-
            # form string/partial mapping.  Only a complete four-axis mapping
            # is a shared state; otherwise leave the compatibility alias
            # uninterpreted.  An explicitly named ``computation_state`` is
            # always contract data and therefore fails closed when malformed.
            if key == "state":
                if not isinstance(candidate, Mapping):
                    continue
                if not {
                    "data_availability",
                    "computability",
                    "validity",
                    "promotion",
                }.issubset(candidate):
                    continue
            candidates.append(_normalize_computation_state(candidate))
    if not candidates:
        return None
    first = candidates[0]
    if any(candidate.to_dict() != first.to_dict() for candidate in candidates[1:]):
        raise ValueError("Workflow compute_run state aliases do not match")
    return first


def _projection_descriptor_alias(value: Mapping[str, Any]) -> str | None:
    """Resolve descriptor IDs at run and nested-result levels."""

    candidates: list[str] = []
    containers: list[Mapping[str, Any]] = [value]
    nested_result = value.get("result")
    if isinstance(nested_result, Mapping):
        containers.append(nested_result)
    for container in containers:
        if "descriptor_id" not in container or container["descriptor_id"] is None:
            continue
        descriptor = container["descriptor_id"]
        if not isinstance(descriptor, str) or not descriptor.strip():
            raise ValueError("Workflow descriptor_id must be a non-empty string or null")
        candidates.append(descriptor.strip())
    if not candidates:
        return None
    first = candidates[0]
    if any(candidate != first for candidate in candidates[1:]):
        raise ValueError("Workflow compute_run descriptor_id values do not match")
    return first


def _projection_mapping_alias(value: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    """Validate run/result provenance-like mappings and reject conflicts."""

    candidates: list[Mapping[str, Any]] = []
    containers: list[Mapping[str, Any]] = [value]
    nested_result = value.get("result")
    if isinstance(nested_result, Mapping):
        containers.append(nested_result)
    for container in containers:
        if field_name not in container or container[field_name] is None:
            continue
        candidate = container[field_name]
        if not isinstance(candidate, Mapping):
            raise TypeError(f"Workflow compute_run {field_name} must be a mapping")
        candidates.append(_freeze_json_value(dict(candidate)))
    if not candidates:
        return MappingProxyType({})
    first = candidates[0]
    # Empty mappings are the historical "not supplied" sentinel.  A single
    # non-empty projection therefore fills an omitted/empty counterpart;
    # two non-empty projections must agree exactly.
    nonempty = [candidate for candidate in candidates if candidate]
    if len(nonempty) > 1 and any(candidate != nonempty[0] for candidate in nonempty[1:]):
        raise ValueError(f"Workflow compute_run {field_name} values do not match")
    return nonempty[0] if nonempty else first


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
        object.__setattr__(self, "header_facts", _freeze_json_value(dict(self.header_facts)))
        object.__setattr__(self, "reason_codes", tuple(str(code) for code in self.reason_codes))

    @classmethod
    def ready(cls, *, path: str, technique: str, sha256: str, format: str = "") -> "InputArtifact":
        normalized_path = str(Path(path).expanduser().resolve(strict=False))
        suffix = (format or ("directory" if Path(normalized_path).is_dir() else Path(normalized_path).suffix.lower().lstrip("."))).lower()
        technique_key = str(technique).lower()
        artifact_id = raw_artifact_id(
            normalized_path,
            technique=technique_key,
            format=suffix,
            sha256=sha256,
        )
        return cls(
            artifact_id=artifact_id,
            path=normalized_path,
            technique=technique_key,
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
            "header_facts": _json_safe(self.header_facts),
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
        object.__setattr__(self, "parameters", _freeze_json_value(dict(self.parameters)))
        object.__setattr__(
            self,
            "parameter_sources",
            _freeze_json_value({str(key): str(value) for key, value in self.parameter_sources.items()}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "technique": self.technique,
            "evidence_role": self.evidence_role,
            "parameters": _json_safe(self.parameters),
            "parameter_sources": _json_safe(self.parameter_sources),
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
    execution_receipt: str | None = None

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
            "execution_receipt": self.execution_receipt,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AnalysisRun":
        evidence_payload = payload.get("evidence")
        evidence = EvidenceRecord.from_dict(evidence_payload) if isinstance(evidence_payload, Mapping) else None
        return cls(
            recipe=AnalysisRecipe.from_dict(payload["recipe"]),
            status=str(payload["status"]),
            reason_codes=tuple(payload.get("reason_codes", ())),
            steps=tuple(WorkflowStepResult.from_dict(item) for item in payload.get("steps", ())),
            evidence=evidence,
            validated=bool(payload.get("validated", False)),
            execution_receipt=str(payload["execution_receipt"]) if payload.get("execution_receipt") else None,
        )


@dataclass(frozen=True)
class WorkflowStepResult:
    """A provider result reduced to its stable public summary and evidence."""

    step_id: str
    technique: str
    status: str
    result_summary: Mapping[str, Any] = field(default_factory=dict)
    analysis_evidence: Mapping[str, Any] = field(default_factory=dict)
    figure_references: Mapping[str, Any] = field(default_factory=dict)
    # JSON-safe projection of the shared ComputeRun.  It is optional so
    # historical workflow bundles remain byte-for-byte readable.
    compute_run: Mapping[str, Any] | None = None
    reason_codes: tuple[str, ...] = ()
    # Optional shared four-axis state and descriptor identity.  Appended after
    # historical fields so existing positional construction remains valid.
    computation_state: Any = None
    descriptor_id: str | None = None
    # ``None`` is the historical in-memory absence sentinel, but a serialized
    # payload can explicitly contain ``compute_run: null``.  Keep that field
    # presence so strict consumers never reinterpret an explicit null as a
    # legacy-compatible omission.
    _compute_run_present: bool = field(default=False, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.status not in _VALID_RUN_STATUSES:
            raise ValueError(f"Unsupported step status: {self.status}")
        object.__setattr__(self, "result_summary", _freeze_json_value(dict(self.result_summary)))
        object.__setattr__(self, "analysis_evidence", _freeze_json_value(dict(self.analysis_evidence)))
        object.__setattr__(self, "figure_references", _freeze_json_value(dict(self.figure_references)))
        if self.compute_run is not None:
            if not isinstance(self.compute_run, Mapping):
                raise TypeError("Workflow compute_run must be a mapping or null")
            object.__setattr__(self, "compute_run", _freeze_json_value(dict(self.compute_run)))
            object.__setattr__(self, "_compute_run_present", True)
        object.__setattr__(self, "reason_codes", tuple(str(code) for code in self.reason_codes))
        state = self.computation_state
        run_state = None
        run_descriptor = None
        if self.compute_run is not None:
            run_state = _projection_state_alias(self.compute_run)
            run_descriptor = _projection_descriptor_alias(self.compute_run)
            run_status = self.compute_run.get("status")
            expected_computability = {
                "completed": "computed",
                "needs_input": "needs_input",
                "failed": "failed",
                "ready": "blocked",
            }.get(run_status)
            if (
                expected_computability is not None
                and run_state is not None
                and run_state.computability != expected_computability
            ):
                raise ValueError("Workflow compute_run status and computation_state do not match")
            # Validate optional provenance/uncertainty at both run and nested
            # result levels before persisting an agent step.  The normalized
            # values are not duplicated onto the step; the nested ComputeRun
            # remains the source of truth.
            _projection_mapping_alias(self.compute_run, "provenance")
            _projection_mapping_alias(self.compute_run, "uncertainty")
        if state is None:
            state = run_state
        normalized_state = _normalize_computation_state(state)
        if normalized_state is not None and run_state is not None:
            if run_state.to_dict() != normalized_state.to_dict():
                raise ValueError("Workflow step and compute_run computation_state do not match")
        object.__setattr__(self, "computation_state", normalized_state)
        descriptor = self.descriptor_id
        if descriptor is not None:
            if not isinstance(descriptor, str) or not descriptor.strip():
                raise ValueError("Workflow descriptor_id must be a non-empty string or null")
            descriptor = descriptor.strip()
        if run_descriptor is not None:
            if descriptor is not None and descriptor != run_descriptor:
                raise ValueError("Workflow step and compute_run descriptor_id do not match")
            descriptor = descriptor or run_descriptor
        if descriptor is not None:
            descriptor = descriptor.strip()
        object.__setattr__(self, "descriptor_id", descriptor)

    @property
    def state(self):
        """Compatibility alias exposing the canonical state projection."""

        return self.computation_state

    @property
    def compute_run_present(self) -> bool:
        """Whether the serialized step explicitly carried ``compute_run``."""

        return self._compute_run_present

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "step_id": self.step_id,
            "technique": self.technique,
            "status": self.status,
            "result_summary": _json_safe(self.result_summary),
            "analysis_evidence": _json_safe(self.analysis_evidence),
            "figure_references": _json_safe(self.figure_references),
            "reason_codes": list(self.reason_codes),
        }
        if self.compute_run is not None or self._compute_run_present:
            payload["compute_run"] = _json_safe(self.compute_run)
        if self.computation_state is not None:
            payload["computation_state"] = self.computation_state.to_dict()
        if self.descriptor_id is not None:
            payload["descriptor_id"] = self.descriptor_id
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "WorkflowStepResult":
        step = cls(
            step_id=str(payload["step_id"]),
            technique=str(payload["technique"]),
            status=str(payload["status"]),
            result_summary=payload.get("result_summary", {}),
            analysis_evidence=payload.get("analysis_evidence", {}),
            figure_references=payload.get("figure_references", {}),
            compute_run=payload.get("compute_run"),
            reason_codes=tuple(payload.get("reason_codes", ())),
            computation_state=payload.get("computation_state", payload.get("state")),
            descriptor_id=payload.get("descriptor_id"),
        )
        if "compute_run" in payload:
            object.__setattr__(step, "_compute_run_present", True)
        return step


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

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "EvidenceRecord":
        return cls(
            observed=tuple(payload.get("observed", ())),
            supported_interpretations=tuple(payload.get("supported_interpretations", ())),
            disallowed_conclusions=tuple(payload.get("disallowed_conclusions", ())),
        )
