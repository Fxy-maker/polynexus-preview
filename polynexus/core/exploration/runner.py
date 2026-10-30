"""Bounded in-process execution for registered exploration methods."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import inspect
from pathlib import Path
from typing import Any, Callable, Mapping

from polynexus.core.ai_platform.contracts import ComputationState, ProviderResultInput, canonical_json_hash
from polynexus.core.ai_platform.capabilities import normalize_technique
from .canonical import CanonicalAdmissionRegistry
from .validation import validate_input_contract, validate_output_contract

from .contracts import ExplorationExecutorDescriptor, ExplorationRequest, ExplorationRun


ExplorationExecutor = Callable[[ExplorationRequest], ProviderResultInput | Mapping[str, Any]]


@dataclass(frozen=True)
class RegisteredExplorationExecutor:
    descriptor: ExplorationExecutorDescriptor
    executor: ExplorationExecutor
    actual_implementation_hash: str


def implementation_hash_for(executor: ExplorationExecutor) -> str:
    """Derive an implementation identity from the loaded callable's code.

    The digest covers the callable's qualified source and its containing module
    bytes when available.  Callers cannot replace this with a self-asserted
    value; registry registration recomputes it and compares it to the descriptor.
    """

    if not callable(executor):
        raise TypeError("exploration executor must be callable")
    try:
        source = inspect.getsource(executor)
    except (OSError, TypeError) as exc:
        raise ValueError("exploration executor source is unavailable") from exc
    module = inspect.getmodule(executor)
    module_name = getattr(module, "__name__", "")
    qualname = getattr(executor, "__qualname__", getattr(executor, "__name__", ""))
    module_hash = ""
    source_file = inspect.getsourcefile(executor)
    if source_file:
        try:
            module_hash = hashlib.sha256(Path(source_file).read_bytes()).hexdigest()
        except OSError:
            module_hash = ""
    return canonical_json_hash(
        {
            "module": module_name,
            "qualname": qualname,
            "source": source,
            "module_sha256": module_hash,
        }
    )


class ExplorationExecutorRegistry:
    """Explicit allowlist of in-process exploration executors.

    The registry deliberately stores callable objects only.  It has no code
    strings, imports-by-name, subprocess, or network execution path.
    """

    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], RegisteredExplorationExecutor] = {}

    def register(
        self,
        descriptor: ExplorationExecutorDescriptor,
        executor: ExplorationExecutor,
    ) -> None:
        if type(descriptor) is not ExplorationExecutorDescriptor:
            raise TypeError("exploration registry requires an exact descriptor DTO")
        if not callable(executor):
            raise TypeError("exploration executor must be a callable")
        key = (descriptor.executor_id, descriptor.version)
        if key in self._entries:
            raise ValueError("exploration executor id/version is already registered")
        actual_hash = implementation_hash_for(executor)
        if descriptor.implementation_hash != actual_hash:
            raise ValueError("exploration executor implementation hash does not match loaded code")
        self._entries[key] = RegisteredExplorationExecutor(descriptor, executor, actual_hash)

    def resolve(self, executor_id: str, version: str) -> RegisteredExplorationExecutor | None:
        return self._entries.get((str(executor_id), str(version)))

    @property
    def descriptors(self) -> tuple[ExplorationExecutorDescriptor, ...]:
        return tuple(entry.descriptor for _, entry in sorted(self._entries.items()))


class ExplorationRunner:
    """Run only an explicitly registered executor and retain every outcome."""

    def __init__(
        self,
        registry: ExplorationExecutorRegistry,
        admissions: CanonicalAdmissionRegistry | None = None,
    ) -> None:
        if type(registry) is not ExplorationExecutorRegistry:
            raise TypeError("ExplorationRunner requires an exact executor registry")
        self.registry = registry
        self.admissions = admissions or CanonicalAdmissionRegistry()

    def run(self, request: ExplorationRequest) -> ExplorationRun:
        if type(request) is not ExplorationRequest:
            raise TypeError("ExplorationRunner requires an exact exploration request")
        registered, preflight = self._preflight(request)
        if preflight is not None:
            return preflight
        assert registered is not None
        try:
            raw_result = registered.executor(request)
        except Exception as exc:
            return ExplorationRun.failed(
                request,
                "exploration_executor_failed",
                {"error_type": type(exc).__name__},
            )
        return self._complete_from_result(request, registered.descriptor, raw_result)

    def _preflight(
        self, request: ExplorationRequest
    ) -> tuple[RegisteredExplorationExecutor | None, ExplorationRun | None]:
        """Validate every admission gate without invoking the executor.

        Isolated workers use this method so malformed requests never reach an
        untrusted callable.  The returned run is already a retained, immutable
        failure/needs-input outcome.
        """

        registered = self.registry.resolve(request.executor_id, request.executor_version)
        if registered is None:
            return None, ExplorationRun.needs_input(request, "exploration_executor_unregistered")
        descriptor = registered.descriptor
        admission = request.canonical_admission
        if admission is None:
            return registered, ExplorationRun.needs_input(
                request, "exploration_canonical_admission_missing"
            )
        registered_admission = self.admissions.resolve(admission.admission_hash)
        if registered_admission is None or registered_admission != admission:
            return registered, ExplorationRun.needs_input(
                request, "exploration_canonical_admission_unregistered"
            )
        if request.executor_implementation_hash != registered.actual_implementation_hash:
            return registered, ExplorationRun.needs_input(
                request, "exploration_executor_implementation_mismatch"
            )
        if descriptor.implementation_hash != request.executor_implementation_hash:
            return registered, ExplorationRun.needs_input(
                request, "exploration_executor_implementation_mismatch"
            )
        if request.executor_descriptor_hash != descriptor.descriptor_hash:
            return registered, ExplorationRun.needs_input(
                request, "exploration_executor_descriptor_mismatch"
            )
        if request.technique not in descriptor.supported_techniques:
            return registered, ExplorationRun.failed(
                request, "exploration_executor_technique_unsupported"
            )
        input_errors = validate_input_contract(descriptor, request, admission)
        if input_errors:
            return registered, ExplorationRun.failed(
                request,
                "exploration_input_contract_violation",
                {"violations": input_errors},
            )
        return registered, None

    def _complete_from_result(
        self,
        request: ExplorationRequest,
        descriptor: ExplorationExecutorDescriptor,
        raw_result: ProviderResultInput | Mapping[str, Any],
    ) -> ExplorationRun:
        try:
            result = self._provider_result(raw_result)
        except (KeyError, TypeError, ValueError):
            return ExplorationRun.failed(request, "exploration_invalid_provider_result")
        if result.source_artifact_id != request.source_artifact_id:
            return ExplorationRun.failed(request, "exploration_provider_result_source_mismatch")
        if normalize_technique(result.technique) != request.technique:
            return ExplorationRun.failed(request, "exploration_provider_result_technique_mismatch")
        if result.provenance.get("source_content_hash") != request.source_content_hash:
            return ExplorationRun.failed(request, "exploration_provider_result_content_mismatch")
        if type(result.computation_state) is not ComputationState:
            return ExplorationRun.failed(request, "exploration_provider_result_state_missing")
        if result.computation_state.computability != "computed":
            return ExplorationRun.failed(request, "exploration_provider_result_not_computed")
        output_errors = validate_output_contract(descriptor, result)
        if output_errors:
            return ExplorationRun.failed(
                request,
                "exploration_output_contract_violation",
                {"violations": output_errors},
            )
        try:
            return ExplorationRun.completed(request, result)
        except (TypeError, ValueError):
            return ExplorationRun.failed(request, "exploration_invalid_provider_result")

    @staticmethod
    def _provider_result(value: ProviderResultInput | Mapping[str, Any]) -> ProviderResultInput:
        if type(value) is ProviderResultInput:
            return value
        if isinstance(value, ProviderResultInput):
            raise TypeError("exploration output must use the exact ProviderResultInput type")
        if not isinstance(value, Mapping):
            raise TypeError("exploration executor must return ProviderResultInput or a mapping")
        return ProviderResultInput.from_dict(value)


__all__ = [
    "ExplorationExecutor",
    "ExplorationExecutorRegistry",
    "ExplorationRunner",
    "RegisteredExplorationExecutor",
    "implementation_hash_for",
]
