"""Bounded in-process execution for registered exploration methods."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from polynexus.core.ai_platform.contracts import ComputationState, ProviderResultInput
from polynexus.core.ai_platform.capabilities import normalize_technique

from .contracts import ExplorationExecutorDescriptor, ExplorationRequest, ExplorationRun


ExplorationExecutor = Callable[[ExplorationRequest], ProviderResultInput | Mapping[str, Any]]


@dataclass(frozen=True)
class RegisteredExplorationExecutor:
    descriptor: ExplorationExecutorDescriptor
    executor: ExplorationExecutor


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
        self._entries[key] = RegisteredExplorationExecutor(descriptor, executor)

    def resolve(self, executor_id: str, version: str) -> RegisteredExplorationExecutor | None:
        return self._entries.get((str(executor_id), str(version)))

    @property
    def descriptors(self) -> tuple[ExplorationExecutorDescriptor, ...]:
        return tuple(entry.descriptor for _, entry in sorted(self._entries.items()))


class ExplorationRunner:
    """Run only an explicitly registered executor and retain every outcome."""

    def __init__(self, registry: ExplorationExecutorRegistry) -> None:
        if type(registry) is not ExplorationExecutorRegistry:
            raise TypeError("ExplorationRunner requires an exact executor registry")
        self.registry = registry

    def run(self, request: ExplorationRequest) -> ExplorationRun:
        if type(request) is not ExplorationRequest:
            raise TypeError("ExplorationRunner requires an exact exploration request")
        registered = self.registry.resolve(request.executor_id, request.executor_version)
        if registered is None:
            return ExplorationRun.needs_input(request, "exploration_executor_unregistered")
        descriptor = registered.descriptor
        if descriptor.implementation_hash != request.executor_implementation_hash:
            return ExplorationRun.needs_input(
                request, "exploration_executor_implementation_mismatch"
            )
        if request.technique not in descriptor.supported_techniques:
            return ExplorationRun.failed(request, "exploration_executor_technique_unsupported")
        try:
            raw_result = registered.executor(request)
        except Exception as exc:
            return ExplorationRun.failed(
                request,
                "exploration_executor_failed",
                {"error_type": type(exc).__name__},
            )
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
]
