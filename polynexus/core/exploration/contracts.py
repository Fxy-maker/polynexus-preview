"""Immutable contracts for bounded AI/Codex exploration runs.

Exploration is deliberately a Core-owned provenance path.  It can retain
unknown or experimental methods without representing them as registered
scientific capabilities, and it never accepts an arbitrary code payload.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
import re
from typing import Any, Mapping, Sequence

from polynexus.core.ai_platform.capabilities import normalize_technique
from polynexus.core.ai_platform.contracts import (
    ComputationState,
    ProviderResultInput,
    canonical_json_hash,
)
from .canonical import CanonicalAdmission


_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_RUN_STATUSES = frozenset({"completed", "needs_input", "failed"})


def _identifier(value: object, label: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"{label} must be a stable identifier")
    return value


def _sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value.lower()):
        raise ValueError(f"{label} must be a 64-character hexadecimal SHA-256")
    return value.lower()


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be nonempty")
    return value.strip()


def _freeze_json(value: Any) -> Any:
    """Validate JSON identity data before freezing it for a public DTO."""

    canonical_json_hash(value)
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_json(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    return value


def _public(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _public(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_public(item) for item in value]
    return value


def _reason_codes(values: Sequence[object]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
        raise TypeError("reason_codes must be a sequence of nonempty strings")
    normalized: list[str] = []
    for value in values:
        reason = _text(value, "reason code")
        if reason not in normalized:
            normalized.append(reason)
    return tuple(normalized)


def _completed_state(provider_result: ProviderResultInput) -> ComputationState:
    state = provider_result.computation_state
    if type(state) is not ComputationState or state.computability != "computed":
        raise ValueError("completed exploration output requires a computed computation_state")
    return ComputationState.create(
        state.data_availability,
        state.computability,
        state.validity,
        "review_required",
        state.missing_inputs,
        state.reason_codes,
        state.preconditions,
        state.next_actions,
    )


@dataclass(frozen=True)
class ExplorationExecutorDescriptor:
    """Versioned declaration for one explicitly registered exploration callable."""

    executor_id: str
    version: str
    implementation_hash: str
    supported_techniques: tuple[str, ...]
    input_contract: Mapping[str, Any]
    output_contract: Mapping[str, Any]
    descriptor_hash: str
    schema_version: str = "1"

    SCHEMA_VERSION = "1"

    def __post_init__(self) -> None:
        if self.schema_version != self.SCHEMA_VERSION:
            raise ValueError("Unsupported exploration executor descriptor schema_version")
        object.__setattr__(self, "executor_id", _identifier(self.executor_id, "executor_id"))
        object.__setattr__(self, "version", _identifier(self.version, "executor version"))
        object.__setattr__(
            self, "implementation_hash", _sha256(self.implementation_hash, "implementation_hash")
        )
        if isinstance(self.supported_techniques, (str, bytes, bytearray)) or not isinstance(
            self.supported_techniques, Sequence
        ):
            raise TypeError("supported_techniques must be a nonempty sequence")
        techniques: list[str] = []
        for value in self.supported_techniques:
            technique = normalize_technique(value)
            if not technique:
                raise ValueError("supported_techniques must not contain empty techniques")
            if technique not in techniques:
                techniques.append(technique)
        if not techniques:
            raise ValueError("supported_techniques must be nonempty")
        object.__setattr__(self, "supported_techniques", tuple(techniques))
        if not isinstance(self.input_contract, Mapping) or not isinstance(self.output_contract, Mapping):
            raise TypeError("exploration executor contracts must be mappings")
        object.__setattr__(self, "input_contract", _freeze_json(self.input_contract))
        object.__setattr__(self, "output_contract", _freeze_json(self.output_contract))
        expected = canonical_json_hash(self._identity_payload())
        if _sha256(self.descriptor_hash, "descriptor_hash") != expected:
            raise ValueError("exploration executor descriptor hash does not match its content")
        object.__setattr__(self, "descriptor_hash", expected)

    @property
    def code_hash(self) -> str:
        """Compatibility-friendly name for the declared implementation hash."""

        return self.implementation_hash

    @classmethod
    def create(
        cls,
        *,
        executor_id: str,
        version: str,
        implementation_hash: str,
        supported_techniques: Sequence[str],
        input_contract: Mapping[str, Any],
        output_contract: Mapping[str, Any],
    ) -> "ExplorationExecutorDescriptor":
        payload = cls._identity_payload_static(
            executor_id=executor_id,
            version=version,
            implementation_hash=implementation_hash,
            supported_techniques=supported_techniques,
            input_contract=input_contract,
            output_contract=output_contract,
        )
        return cls(
            executor_id=executor_id,
            version=version,
            implementation_hash=implementation_hash,
            supported_techniques=tuple(supported_techniques),
            input_contract=input_contract,
            output_contract=output_contract,
            descriptor_hash=canonical_json_hash(payload),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExplorationExecutorDescriptor":
        if not isinstance(value, Mapping):
            raise TypeError("exploration executor descriptor must be a mapping")
        return cls(
            executor_id=value["executor_id"],
            version=value["version"],
            implementation_hash=value["implementation_hash"],
            supported_techniques=tuple(value["supported_techniques"]),
            input_contract=value.get("input_contract", {}),
            output_contract=value.get("output_contract", {}),
            descriptor_hash=value["descriptor_hash"],
            schema_version=value.get("schema_version", ""),
        )

    @staticmethod
    def _identity_payload_static(
        *,
        executor_id: object,
        version: object,
        implementation_hash: object,
        supported_techniques: Sequence[object],
        input_contract: Mapping[str, Any],
        output_contract: Mapping[str, Any],
    ) -> dict[str, Any]:
        if isinstance(supported_techniques, (str, bytes, bytearray)):
            raise TypeError("supported_techniques must be a sequence")
        techniques = tuple(dict.fromkeys(normalize_technique(item) for item in supported_techniques))
        return {
            "schema_version": ExplorationExecutorDescriptor.SCHEMA_VERSION,
            "executor_id": _identifier(executor_id, "executor_id"),
            "version": _identifier(version, "executor version"),
            "implementation_hash": _sha256(implementation_hash, "implementation_hash"),
            "supported_techniques": list(techniques),
            "input_contract": _public(_freeze_json(input_contract)),
            "output_contract": _public(_freeze_json(output_contract)),
        }

    def _identity_payload(self) -> dict[str, Any]:
        return self._identity_payload_static(
            executor_id=self.executor_id,
            version=self.version,
            implementation_hash=self.implementation_hash,
            supported_techniques=self.supported_techniques,
            input_contract=self.input_contract,
            output_contract=self.output_contract,
        )

    def to_dict(self) -> dict[str, Any]:
        return {"descriptor_hash": self.descriptor_hash, **self._identity_payload()}


@dataclass(frozen=True)
class ExplorationRequest:
    """Content-addressed request for a bounded exploration executor."""

    request_id: str
    source_artifact_id: str
    source_content_hash: str
    technique: str
    executor_id: str
    executor_version: str
    executor_implementation_hash: str
    method_intent: str
    parameters: Mapping[str, Any]
    executor_descriptor_hash: str | None = None
    parent_run_id: str | None = None
    canonical_admission: CanonicalAdmission | None = None
    seed: int | None = None
    attempt_id: str | None = None
    schema_version: str = "1"

    SCHEMA_VERSION = "1"

    def __post_init__(self) -> None:
        if self.schema_version != self.SCHEMA_VERSION:
            raise ValueError("Unsupported exploration request schema_version")
        object.__setattr__(self, "source_artifact_id", _sha256(self.source_artifact_id, "source_artifact_id"))
        object.__setattr__(
            self, "source_content_hash", _sha256(self.source_content_hash, "source_content_hash")
        )
        technique = normalize_technique(self.technique)
        if not technique:
            raise ValueError("exploration technique must be nonempty")
        object.__setattr__(self, "technique", technique)
        object.__setattr__(self, "executor_id", _identifier(self.executor_id, "executor_id"))
        object.__setattr__(self, "executor_version", _identifier(self.executor_version, "executor version"))
        object.__setattr__(
            self,
            "executor_implementation_hash",
            _sha256(self.executor_implementation_hash, "executor_implementation_hash"),
        )
        if self.executor_descriptor_hash is not None:
            object.__setattr__(
                self,
                "executor_descriptor_hash",
                _sha256(self.executor_descriptor_hash, "executor_descriptor_hash"),
            )
        object.__setattr__(self, "method_intent", _text(self.method_intent, "method_intent"))
        if not isinstance(self.parameters, Mapping):
            raise TypeError("exploration parameters must be a mapping")
        object.__setattr__(self, "parameters", _freeze_json(self.parameters))
        if self.parent_run_id is not None:
            object.__setattr__(self, "parent_run_id", _identifier(self.parent_run_id, "parent_run_id"))
        if self.canonical_admission is not None and type(self.canonical_admission) is not CanonicalAdmission:
            raise TypeError("canonical_admission must use the exact CanonicalAdmission type")
        if self.canonical_admission is not None:
            if self.canonical_admission.source_artifact_id != self.source_artifact_id:
                raise ValueError("request source artifact does not match canonical admission")
            if self.canonical_admission.source_content_hash != self.source_content_hash:
                raise ValueError("request source content does not match canonical admission")
            if self.canonical_admission.technique != technique:
                raise ValueError("request technique does not match canonical admission")
        if self.seed is not None:
            if not isinstance(self.seed, int) or isinstance(self.seed, bool) or self.seed < 0:
                raise ValueError("exploration seed must be a nonnegative integer or null")
        if self.attempt_id is not None:
            object.__setattr__(self, "attempt_id", _identifier(self.attempt_id, "attempt_id"))
        expected = canonical_json_hash(self._identity_payload())
        if _sha256(self.request_id, "request_id") != expected:
            raise ValueError("exploration request id does not match its content")
        object.__setattr__(self, "request_id", expected)

    @classmethod
    def create(
        cls,
        *,
        source_artifact_id: str,
        source_content_hash: str,
        technique: str,
        executor_id: str,
        executor_version: str,
        executor_implementation_hash: str,
        executor_descriptor_hash: str | None = None,
        method_intent: str,
        parameters: Mapping[str, Any],
        parent_run_id: str | None = None,
        canonical_admission: CanonicalAdmission | None = None,
        seed: int | None = None,
        attempt_id: str | None = None,
    ) -> "ExplorationRequest":
        payload = cls._identity_payload_static(
            source_artifact_id=source_artifact_id,
            source_content_hash=source_content_hash,
            technique=technique,
            executor_id=executor_id,
            executor_version=executor_version,
            executor_implementation_hash=executor_implementation_hash,
            executor_descriptor_hash=executor_descriptor_hash,
            method_intent=method_intent,
            parameters=parameters,
            parent_run_id=parent_run_id,
            canonical_admission=canonical_admission,
            seed=seed,
            attempt_id=attempt_id,
        )
        return cls(
            request_id=canonical_json_hash(payload),
            source_artifact_id=source_artifact_id,
            source_content_hash=source_content_hash,
            technique=technique,
            executor_id=executor_id,
            executor_version=executor_version,
            executor_implementation_hash=executor_implementation_hash,
            executor_descriptor_hash=executor_descriptor_hash,
            method_intent=method_intent,
            parameters=parameters,
            parent_run_id=parent_run_id,
            canonical_admission=canonical_admission,
            seed=seed,
            attempt_id=attempt_id,
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExplorationRequest":
        if not isinstance(value, Mapping):
            raise TypeError("exploration request must be a mapping")
        return cls(
            request_id=value["request_id"],
            source_artifact_id=value["source_artifact_id"],
            source_content_hash=value["source_content_hash"],
            technique=value["technique"],
            executor_id=value["executor_id"],
            executor_version=value["executor_version"],
            executor_implementation_hash=value["executor_implementation_hash"],
            executor_descriptor_hash=value.get("executor_descriptor_hash"),
            method_intent=value["method_intent"],
            parameters=value.get("parameters", {}),
            parent_run_id=value.get("parent_run_id"),
            canonical_admission=(
                None
                if value.get("canonical_admission") is None
                else CanonicalAdmission.from_dict(value["canonical_admission"])
            ),
            seed=value.get("seed"),
            attempt_id=value.get("attempt_id"),
            schema_version=value.get("schema_version", ""),
        )

    @staticmethod
    def _identity_payload_static(
        *,
        source_artifact_id: object,
        source_content_hash: object,
        technique: object,
        executor_id: object,
        executor_version: object,
        executor_implementation_hash: object,
        executor_descriptor_hash: object | None,
        method_intent: object,
        parameters: Mapping[str, Any],
        parent_run_id: object | None,
        canonical_admission: CanonicalAdmission | None,
        seed: object | None,
        attempt_id: object | None,
    ) -> dict[str, Any]:
        normalized_technique = normalize_technique(technique)
        if not normalized_technique:
            raise ValueError("exploration technique must be nonempty")
        if parent_run_id is not None:
            parent_run_id = _identifier(parent_run_id, "parent_run_id")
        if canonical_admission is not None and type(canonical_admission) is not CanonicalAdmission:
            raise TypeError("canonical_admission must use the exact CanonicalAdmission type")
        if seed is not None and (not isinstance(seed, int) or isinstance(seed, bool) or seed < 0):
            raise ValueError("exploration seed must be a nonnegative integer or null")
        if attempt_id is not None:
            attempt_id = _identifier(attempt_id, "attempt_id")
        return {
            "schema_version": ExplorationRequest.SCHEMA_VERSION,
            "source_artifact_id": _sha256(source_artifact_id, "source_artifact_id"),
            "source_content_hash": _sha256(source_content_hash, "source_content_hash"),
            "technique": normalized_technique,
            "executor_id": _identifier(executor_id, "executor_id"),
            "executor_version": _identifier(executor_version, "executor version"),
            "executor_implementation_hash": _sha256(
                executor_implementation_hash, "executor_implementation_hash"
            ),
            "executor_descriptor_hash": (
                None
                if executor_descriptor_hash is None
                else _sha256(executor_descriptor_hash, "executor_descriptor_hash")
            ),
            "method_intent": _text(method_intent, "method_intent"),
            "parameters": _public(_freeze_json(parameters)),
            "parent_run_id": parent_run_id,
            "canonical_admission": None if canonical_admission is None else canonical_admission.to_dict(),
            "seed": seed,
            "attempt_id": attempt_id,
        }

    def _identity_payload(self) -> dict[str, Any]:
        return self._identity_payload_static(
            source_artifact_id=self.source_artifact_id,
            source_content_hash=self.source_content_hash,
            technique=self.technique,
            executor_id=self.executor_id,
            executor_version=self.executor_version,
            executor_implementation_hash=self.executor_implementation_hash,
            executor_descriptor_hash=self.executor_descriptor_hash,
            method_intent=self.method_intent,
            parameters=self.parameters,
            parent_run_id=self.parent_run_id,
            canonical_admission=self.canonical_admission,
            seed=self.seed,
            attempt_id=self.attempt_id,
        )

    def to_dict(self) -> dict[str, Any]:
        return {"request_id": self.request_id, **self._identity_payload()}


@dataclass(frozen=True)
class ExplorationRun:
    """One immutable outcome of an exploration request.

    ``run_id`` is intentionally request-derived.  Re-executing identical
    inputs through an identical declared implementation cannot quietly replace
    a persisted outcome with a different result.
    """

    run_id: str
    request: ExplorationRequest
    status: str
    computation_state: ComputationState
    provider_result: ProviderResultInput | None
    reason_codes: tuple[str, ...] = ()
    failure_metadata: Mapping[str, Any] = field(default_factory=dict)
    run_hash: str = ""
    schema_version: str = "1"

    SCHEMA_VERSION = "1"

    def __post_init__(self) -> None:
        if self.schema_version != self.SCHEMA_VERSION:
            raise ValueError("Unsupported exploration run schema_version")
        if type(self.request) is not ExplorationRequest:
            raise TypeError("exploration run request must use the exact ExplorationRequest type")
        status = _text(self.status, "exploration run status")
        if status not in _RUN_STATUSES:
            raise ValueError("Unsupported exploration run status")
        object.__setattr__(self, "status", status)
        if type(self.computation_state) is not ComputationState:
            raise TypeError("exploration run must use the exact ComputationState type")
        object.__setattr__(self, "reason_codes", _reason_codes(self.reason_codes))
        if not isinstance(self.failure_metadata, Mapping):
            raise TypeError("exploration failure_metadata must be a mapping")
        object.__setattr__(self, "failure_metadata", _freeze_json(self.failure_metadata))
        if self.provider_result is not None and type(self.provider_result) is not ProviderResultInput:
            raise TypeError("exploration provider_result must use the exact ProviderResultInput type")
        expected_run_id = self._run_id_for(self.request)
        if self.run_id != expected_run_id:
            raise ValueError("exploration run id does not match its request")
        if self.status == "completed":
            if self.provider_result is None:
                raise ValueError("completed exploration run requires provider_result")
            if self.computation_state.to_dict() != _completed_state(self.provider_result).to_dict():
                raise ValueError("completed exploration run state does not match provider_result")
            if self.failure_metadata:
                raise ValueError("completed exploration run cannot have failure metadata")
        else:
            if self.provider_result is not None:
                raise ValueError("noncompleted exploration run cannot have provider_result")
            expected_computability = "needs_input" if self.status == "needs_input" else "failed"
            state = self.computation_state
            if (
                state.data_availability != "raw"
                or state.computability != expected_computability
                or state.validity != "not_assessed"
                or state.promotion != "diagnostic_only"
            ):
                raise ValueError("noncompleted exploration run has an inconsistent computation state")
            if not self.reason_codes:
                raise ValueError("noncompleted exploration run requires a reason code")
        expected_hash = canonical_json_hash(self._content_payload())
        if _sha256(self.run_hash, "run_hash") != expected_hash:
            raise ValueError("exploration run hash does not match its content")
        object.__setattr__(self, "run_hash", expected_hash)

    @classmethod
    def completed(cls, request: ExplorationRequest, provider_result: ProviderResultInput) -> "ExplorationRun":
        state = _completed_state(provider_result)
        return cls(
            run_id=cls._run_id_for(request),
            request=request,
            status="completed",
            computation_state=state,
            provider_result=provider_result,
            run_hash=cls._hash_for(
                request=request,
                status="completed",
                computation_state=state,
                provider_result=provider_result,
                reason_codes=(),
                failure_metadata={},
            ),
        )

    @classmethod
    def needs_input(cls, request: ExplorationRequest, reason_code: str) -> "ExplorationRun":
        return cls._noncompleted(request, "needs_input", reason_code)

    @classmethod
    def failed(
        cls,
        request: ExplorationRequest,
        reason_code: str,
        failure_metadata: Mapping[str, Any] | None = None,
    ) -> "ExplorationRun":
        return cls._noncompleted(request, "failed", reason_code, failure_metadata)

    @classmethod
    def _noncompleted(
        cls,
        request: ExplorationRequest,
        status: str,
        reason_code: str,
        failure_metadata: Mapping[str, Any] | None = None,
    ) -> "ExplorationRun":
        if type(request) is not ExplorationRequest:
            raise TypeError("exploration run request must use the exact ExplorationRequest type")
        computation_state = ComputationState.create(
            "raw",
            "needs_input" if status == "needs_input" else "failed",
            "not_assessed",
            "diagnostic_only",
            reason_codes=(reason_code,),
        )
        metadata = {} if failure_metadata is None else failure_metadata
        return cls(
            run_id=cls._run_id_for(request),
            request=request,
            status=status,
            computation_state=computation_state,
            provider_result=None,
            reason_codes=(reason_code,),
            failure_metadata=metadata,
            run_hash=cls._hash_for(
                request=request,
                status=status,
                computation_state=computation_state,
                provider_result=None,
                reason_codes=(reason_code,),
                failure_metadata=metadata,
            ),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExplorationRun":
        if not isinstance(value, Mapping):
            raise TypeError("exploration run must be a mapping")
        provider_result = value.get("provider_result")
        return cls(
            run_id=value["run_id"],
            request=ExplorationRequest.from_dict(value["request"]),
            status=value["status"],
            computation_state=ComputationState.from_dict(value["computation_state"]),
            provider_result=(
                None if provider_result is None else ProviderResultInput.from_dict(provider_result)
            ),
            reason_codes=tuple(value.get("reason_codes", ())),
            failure_metadata=value.get("failure_metadata", {}),
            run_hash=value["run_hash"],
            schema_version=value.get("schema_version", ""),
        )

    @staticmethod
    def _run_id_for(request: ExplorationRequest) -> str:
        return f"exploration-{canonical_json_hash({'request_id': request.request_id})}"

    @classmethod
    def _hash_for(
        cls,
        *,
        request: ExplorationRequest,
        status: str,
        computation_state: ComputationState,
        provider_result: ProviderResultInput | None,
        reason_codes: Sequence[object],
        failure_metadata: Mapping[str, Any],
    ) -> str:
        return canonical_json_hash(
            cls._content_payload_static(
                request=request,
                status=status,
                computation_state=computation_state,
                provider_result=provider_result,
                reason_codes=reason_codes,
                failure_metadata=failure_metadata,
            )
        )

    @staticmethod
    def _content_payload_static(
        *,
        request: ExplorationRequest,
        status: str,
        computation_state: ComputationState,
        provider_result: ProviderResultInput | None,
        reason_codes: Sequence[object],
        failure_metadata: Mapping[str, Any],
    ) -> dict[str, Any]:
        if type(request) is not ExplorationRequest or type(computation_state) is not ComputationState:
            raise TypeError("exploration run content requires exact shared DTO types")
        if provider_result is not None and type(provider_result) is not ProviderResultInput:
            raise TypeError("exploration run content requires exact ProviderResultInput type")
        return {
            "schema_version": ExplorationRun.SCHEMA_VERSION,
            "run_id": ExplorationRun._run_id_for(request),
            "request": request.to_dict(),
            "status": status,
            "computation_state": computation_state.to_dict(),
            "provider_result": None if provider_result is None else provider_result.to_dict(),
            "reason_codes": list(_reason_codes(reason_codes)),
            "failure_metadata": _public(_freeze_json(failure_metadata)),
        }

    def _content_payload(self) -> dict[str, Any]:
        return self._content_payload_static(
            request=self.request,
            status=self.status,
            computation_state=self.computation_state,
            provider_result=self.provider_result,
            reason_codes=self.reason_codes,
            failure_metadata=self.failure_metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        return {"run_hash": self.run_hash, **self._content_payload()}

    def to_full_snapshot(self) -> dict[str, Any]:
        """Return the complete immutable exploration history for workspace use."""

        return self.to_dict()

    def to_evidence_item(self, selection: Any):
        """Project only an explicit metric selection into shared evidence."""

        from .evidence import ExplorationEvidenceSelection

        if type(selection) is not ExplorationEvidenceSelection:
            raise TypeError("exploration evidence requires an explicit selection")
        return selection.project(self)


__all__ = [
    "ExplorationExecutorDescriptor",
    "ExplorationRequest",
    "ExplorationRun",
]
