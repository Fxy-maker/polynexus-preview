"""Small deterministic execution graph used by the AI platform.

The graph intentionally stays synchronous.  It provides a stable planning and
provenance boundary which can later be adapted by ``ComputeRun`` or a queued
worker without giving the GUI or an agent a second result representation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import MutableMapping
import re
from types import MappingProxyType
from typing import Any, Callable, Mapping, Sequence

from .contracts import ComputationState, canonical_json_hash


def _json_safe(value: Any) -> Any:
    """Normalize values accepted by the public execution contracts."""

    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        # canonical_json_hash also rejects non-finite values, but fail at the
        # contract boundary so malformed executor output is deterministic.
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("Execution values must be finite")
        return value
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("Execution mappings must use string keys")
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    raise TypeError(f"Execution values do not support {type(value).__name__}")


def _freeze(value: Any) -> Any:
    safe = _json_safe(value)
    if isinstance(safe, dict):
        return MappingProxyType({key: _freeze(item) for key, item in safe.items()})
    if isinstance(safe, list):
        return tuple(_freeze(item) for item in safe)
    return safe


def _public(value: Any) -> Any:
    """Return a JSON-compatible copy, including frozen mappings/tuples."""

    if isinstance(value, Mapping):
        return {str(key): _public(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_public(item) for item in value]
    if isinstance(value, list):
        return [_public(item) for item in value]
    return _json_safe(value)


def _hash(value: str, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or not re.fullmatch(r"[0-9a-fA-F]{64}", value):
        raise ValueError(f"{label} must be a 64-character hexadecimal SHA-256")
    return value.lower()


def _output_fingerprint(value: Any) -> str:
    """Return the content identity of a node's JSON-safe output."""

    return canonical_json_hash({"output": _public(value)})


def _hashes(values: Sequence[str], label: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
        raise TypeError(f"{label} must be a sequence of SHA-256 hashes")
    normalized = {_hash(value, label) for value in values}
    return tuple(sorted(normalized))


def _strings(values: Sequence[str], label: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
        raise TypeError(f"{label} must be a sequence of nonempty strings")
    result = []
    for value in values:
        if not isinstance(value, str) or not value:
            raise ValueError(f"{label} entries must be nonempty strings")
        result.append(value)
    if len(set(result)) != len(result):
        raise ValueError(f"{label} entries must be unique")
    return tuple(result)


@dataclass(frozen=True)
class ExecutionContext:
    """Immutable inputs that influence deterministic node execution."""

    input_hashes: tuple[str, ...] = ()
    calibration_hashes: tuple[str, ...] = ()
    runtime_fingerprint: str = "unknown"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "input_hashes", _hashes(self.input_hashes, "input_hashes"))
        object.__setattr__(self, "calibration_hashes", _hashes(self.calibration_hashes, "calibration_hashes"))
        if not isinstance(self.runtime_fingerprint, str) or not self.runtime_fingerprint:
            raise ValueError("runtime_fingerprint must be a nonempty string")
        if not isinstance(self.metadata, Mapping):
            raise TypeError("Execution metadata must be a mapping")
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    @classmethod
    def create(
        cls,
        input_hashes: Sequence[str] = (),
        calibration_hashes: Sequence[str] = (),
        runtime_fingerprint: str = "unknown",
        metadata: Mapping[str, Any] | None = None,
    ) -> "ExecutionContext":
        return cls(input_hashes, calibration_hashes, runtime_fingerprint, {} if metadata is None else metadata)

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_hashes": list(self.input_hashes),
            "calibration_hashes": list(self.calibration_hashes),
            "runtime_fingerprint": self.runtime_fingerprint,
            "metadata": _public(self.metadata),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExecutionContext":
        if not isinstance(value, Mapping):
            raise TypeError("Execution context must be a mapping")
        return cls.create(
            value.get("input_hashes", ()),
            value.get("calibration_hashes", ()),
            value.get("runtime_fingerprint", "unknown"),
            value.get("metadata", {}),
        )


@dataclass(frozen=True)
class ExecutionNode:
    """One capability invocation and its declared graph dependencies."""

    node_id: str
    capability_id: str
    descriptor_version: str = "1"
    parameters: Mapping[str, Any] = field(default_factory=dict)
    dependencies: tuple[str, ...] = ()
    state: ComputationState | None = None
    calibration_sensitive: bool | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("node_id", "capability_id", "descriptor_version"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"Execution {name} must be a nonempty string")
        if not isinstance(self.parameters, Mapping):
            raise TypeError("Execution node parameters must be a mapping")
        object.__setattr__(self, "parameters", _freeze(self.parameters))
        object.__setattr__(self, "dependencies", _strings(self.dependencies, "Execution dependencies"))
        if self.node_id in self.dependencies:
            raise ValueError("Execution node cannot depend on itself")
        if self.state is None:
            state = ComputationState.create(
                data_availability="canonical",
                computability="computed",
                validity="not_assessed",
                promotion="diagnostic_only",
            )
            object.__setattr__(self, "state", state)
        elif type(self.state) is ComputationState:
            pass
        elif isinstance(self.state, ComputationState):
            raise TypeError(
                "Execution node state must use the exact ComputationState type or mapping"
            )
        elif isinstance(self.state, Mapping):
            object.__setattr__(self, "state", ComputationState.from_dict(self.state))
        else:
            raise TypeError(
                "Execution node state must use the exact ComputationState type or mapping"
            )
        if self.calibration_sensitive is not None and not isinstance(self.calibration_sensitive, bool):
            raise TypeError("calibration_sensitive must be a bool or None")
        if not isinstance(self.metadata, Mapping):
            raise TypeError("Execution node metadata must be a mapping")
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    @classmethod
    def create(
        cls,
        node_id: str,
        capability_id: str,
        descriptor_version: str = "1",
        parameters: Mapping[str, Any] | None = None,
        dependencies: Sequence[str] = (),
        state: ComputationState | Mapping[str, Any] | None = None,
        calibration_sensitive: bool | None = None,
        metadata: Mapping[str, Any] | None = None,
        *,
        version: str | None = None,
    ) -> "ExecutionNode":
        if isinstance(dependencies, (str, bytes, bytearray)) or not isinstance(
            dependencies, Sequence
        ):
            raise TypeError("Execution dependencies must be a sequence of nonempty strings")
        if version is not None:
            descriptor_version = version
        return cls(
            node_id,
            capability_id,
            descriptor_version,
            {} if parameters is None else parameters,
            tuple(dependencies),
            state,
            calibration_sensitive,
            {} if metadata is None else metadata,
        )

    @property
    def uses_calibration(self) -> bool:
        """Whether calibration context belongs in this node's own cache key.

        Descriptors can set ``calibration_sensitive`` explicitly.  The small
        fallback recognizes common calibration capability IDs so an adapter
        can remain useful before every descriptor is migrated.
        """

        if self.calibration_sensitive is not None:
            return self.calibration_sensitive
        lowered = self.capability_id.casefold()
        return any(token in lowered for token in ("calibrat", "absolute_intensity", "absolute.", "q_calibration"))

    def uses_calibration_for(self, descriptor: Any | None = None) -> bool:
        """Resolve calibration sensitivity from the descriptor contract.

        Capability IDs are not a reliable scientific signal (for example,
        ``saxs.detector_radial_profile.v1`` requires calibration without
        containing the word ``calibrate``).  Keep the legacy heuristic for
        opaque nodes, but let a registered descriptor declare the dependency.
        """

        if descriptor is not None:
            contract = getattr(descriptor, "input_contract", {})
            if isinstance(contract, Mapping) and contract.get("required_calibrations"):
                return True
            for precondition in getattr(descriptor, "preconditions", ()) or ():
                if isinstance(precondition, Mapping):
                    kind = str(precondition.get("kind", precondition.get("type", ""))).strip().lower()
                    if kind == "calibration":
                        return True
            policy = getattr(descriptor, "evidence_policy", {})
            if isinstance(policy, Mapping) and policy.get("requires_reviewed_calibration"):
                return True
        if self.calibration_sensitive is not None:
            return self.calibration_sensitive
        return self.uses_calibration

    def cache_key(
        self,
        context: ExecutionContext,
        dependency_keys: Mapping[str, str] | Sequence[tuple[str, str]] | None = None,
        *,
        descriptor: Any | None = None,
        admission_hash: str | None = None,
    ) -> str:
        if not isinstance(context, ExecutionContext):
            raise TypeError("cache_key expects an ExecutionContext")
        # Cache identities are content identities.  Cosmetic graph labels
        # (``node_id`` values) must never affect a node's own key, otherwise
        # equivalent plans cannot share work.  Dependencies are represented
        # by their content keys in declared argument order; the graph still
        # uses node IDs to wire values to executors, but those labels are not
        # part of the cache identity.
        dependencies: list[str | None] = []
        if dependency_keys is not None:
            if isinstance(dependency_keys, Mapping):
                items = list(dependency_keys.items())
            else:
                if isinstance(dependency_keys, (str, bytes, bytearray)):
                    raise TypeError("dependency cache identities must be string pairs")
                try:
                    items = list(dependency_keys)
                except TypeError as exc:
                    raise TypeError("dependency cache identities must be string pairs") from exc
            identities: dict[str, str] = {}
            for pair in items:
                if not isinstance(pair, (tuple, list)) or len(pair) != 2:
                    raise TypeError("dependency cache identities must be string pairs")
                node_id, cache_key = pair
                if not isinstance(node_id, str) or not node_id:
                    raise TypeError("dependency cache identities must be string pairs")
                if node_id in identities:
                    raise ValueError("dependency cache identities must use unique node IDs")
                identities[node_id] = _hash(cache_key, "dependency cache key")
            expected = set(self.dependencies)
            supplied = set(identities)
            if expected:
                if supplied != expected:
                    raise ValueError("dependency cache identities must match declared dependencies")
                dependencies = [identities[dependency] for dependency in self.dependencies]
            elif identities:
                # There are no declared dependencies, so accepting an
                # explicitly supplied set would be ambiguous.  Reject it
                # rather than silently changing a content key.
                raise ValueError("dependency cache identities supplied for a node without dependencies")
        else:
            # Even a standalone key calculation must reflect the declared
            # dependency arity.  The graph fills in concrete cache keys at
            # execution time; ``None`` explicitly marks unresolved inputs.
            dependencies = [None for _ in self.dependencies]
        payload = {
            "capability_id": self.capability_id,
            "descriptor_version": self.descriptor_version,
            "descriptor_hash": (
                getattr(descriptor, "content_hash", None) if descriptor is not None else None
            ),
            "descriptor_dependencies": (
                list(getattr(descriptor, "dependencies", ())) if descriptor is not None else []
            ),
            "planner_admission_hash": (
                _hash(admission_hash, "planner admission hash") if admission_hash is not None else None
            ),
            "parameters": _public(self.parameters),
            "node_metadata": _public(self.metadata),
            "input_hashes": list(context.input_hashes),
            "calibration_hashes": list(context.calibration_hashes)
            if self.uses_calibration_for(descriptor)
            else [],
            "runtime_fingerprint": context.runtime_fingerprint,
            # Executors receive the complete context and may legitimately use
            # declared sample/condition metadata.  It therefore belongs in
            # the content key; otherwise two different requests could share a
            # stale cached result.
            "context_metadata": _public(context.metadata),
            "dependencies": dependencies,
        }
        return canonical_json_hash(payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "capability_id": self.capability_id,
            "descriptor_version": self.descriptor_version,
            "parameters": _public(self.parameters),
            "dependencies": list(self.dependencies),
            "state": self.state.to_dict(),
            "calibration_sensitive": self.calibration_sensitive,
            "metadata": _public(self.metadata),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExecutionNode":
        if not isinstance(value, Mapping):
            raise TypeError("Execution node must be a mapping")
        return cls.create(
            value["node_id"],
            value["capability_id"],
            value.get("descriptor_version", value.get("version", "1")),
            value.get("parameters", {}),
            value.get("dependencies", ()),
            value.get("state"),
            value.get("calibration_sensitive"),
            value.get("metadata", {}),
        )


@dataclass(frozen=True)
class NodeResult:
    """A JSON-safe result and provenance projection for one graph node."""

    node_id: str
    capability_id: str
    status: str
    state: ComputationState
    cache_key: str
    output: Any = None
    provenance: Mapping[str, Any] = field(default_factory=dict)
    error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.node_id, str) or not self.node_id:
            raise ValueError("NodeResult node_id must be a nonempty string")
        if not isinstance(self.capability_id, str) or not self.capability_id:
            raise ValueError("NodeResult capability_id must be a nonempty string")
        if not isinstance(self.status, str):
            raise TypeError("NodeResult status must be a string")
        if not isinstance(self.cache_key, str) or not self.cache_key:
            raise ValueError("NodeResult identity fields must be nonempty")
        # Every persisted cache key is a content hash.  Checking the digest
        # here makes both freshly-created and deserialized results fail closed
        # before they can enter a cache or be projected to another entrypoint.
        object.__setattr__(self, "cache_key", _hash(self.cache_key, "NodeResult cache_key"))
        allowed = {"completed", "needs_input", "blocked", "failed", "not_applicable"}
        if self.status not in allowed:
            raise ValueError(f"Unsupported node result status: {self.status}")
        if type(self.state) is not ComputationState:
            raise TypeError("NodeResult state must use the exact ComputationState type")
        if not isinstance(self.provenance, Mapping):
            raise TypeError("NodeResult provenance must be a mapping")
        expected_computability = {
            "completed": "computed",
            "needs_input": "needs_input",
            "blocked": "blocked",
            "failed": "failed",
            "not_applicable": "not_applicable",
        }[self.status]
        if self.state.computability != expected_computability:
            raise ValueError(
                f"NodeResult status/state mismatch: {self.status} requires "
                f"state computability {expected_computability}"
            )
        if self.status in {"needs_input", "blocked", "not_applicable"} and (
            self.output is not None or self.error is not None
        ):
            raise ValueError(f"NodeResult {self.status} cannot contain output or error")
        if self.status == "completed" and self.error is not None:
            raise ValueError("completed NodeResult cannot contain error")
        object.__setattr__(self, "output", _freeze(self.output) if self.output is not None else None)
        object.__setattr__(self, "provenance", _freeze(self.provenance))
        if self.error is not None and (not isinstance(self.error, str) or not self.error):
            raise ValueError("NodeResult error must be a nonempty string")
        if self.status == "failed" and (self.error is None or not isinstance(self.error, str) or not self.error):
            raise ValueError("failed NodeResult requires a nonempty error")
        # If a producer supplies a cache identity in provenance, it must agree
        # with the field-level identity.  Older producers may omit it, so the
        # check is conditional for backwards compatibility.
        if "cache_key" in self.provenance:
            provenance_key = self.provenance["cache_key"]
            if not isinstance(provenance_key, str) or _hash(provenance_key, "NodeResult provenance cache_key") != self.cache_key:
                raise ValueError("NodeResult provenance cache_key does not match cache_key")
        if "output_fingerprint" in self.provenance:
            fingerprint = self.provenance["output_fingerprint"]
            if not isinstance(fingerprint, str) or _hash(
                fingerprint, "NodeResult provenance output_fingerprint"
            ) != _output_fingerprint(self.output):
                raise ValueError("NodeResult provenance output_fingerprint does not match output")

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "capability_id": self.capability_id,
            "status": self.status,
            "state": self.state.to_dict(),
            "cache_key": self.cache_key,
            "output": _public(self.output),
            "provenance": _public(self.provenance),
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "NodeResult":
        if not isinstance(value, Mapping):
            raise TypeError("Node result must be a mapping")
        return cls(
            value["node_id"],
            value["capability_id"],
            value["status"],
            ComputationState.from_dict(value["state"]),
            value["cache_key"],
            value.get("output"),
            value.get("provenance", {}),
            value.get("error"),
        )


@dataclass(frozen=True)
class ExecutionResult:
    graph_id: str
    context: ExecutionContext
    node_results: tuple[NodeResult, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.graph_id, str) or not self.graph_id:
            raise ValueError("ExecutionResult graph_id must be a nonempty SHA-256")
        object.__setattr__(self, "graph_id", _hash(self.graph_id, "ExecutionResult graph_id"))
        if not isinstance(self.context, ExecutionContext):
            raise TypeError("ExecutionResult context must be an ExecutionContext")
        if isinstance(self.node_results, (str, bytes, bytearray)) or not isinstance(self.node_results, Sequence):
            raise TypeError("ExecutionResult node_results must be a sequence")
        if any(not isinstance(item, NodeResult) for item in self.node_results):
            raise TypeError("ExecutionResult node_results must contain NodeResult values")
        normalized = tuple(self.node_results)
        node_ids = [item.node_id for item in normalized]
        if len(set(node_ids)) != len(node_ids):
            raise ValueError("ExecutionResult node_results must use unique node IDs")
        object.__setattr__(self, "node_results", normalized)

    def to_dict(self) -> dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "context": self.context.to_dict(),
            "node_results": [item.to_dict() for item in self.node_results],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExecutionResult":
        if not isinstance(value, Mapping):
            raise TypeError("Execution result must be a mapping")
        return cls(
            value["graph_id"],
            ExecutionContext.from_dict(value["context"]),
            tuple(NodeResult.from_dict(item) for item in value.get("node_results", ())),
        )


# A descriptive alias makes adapters/readers less likely to invent another
# result class while retaining the concise name used by the public API.
GraphResult = ExecutionResult


def _state_for(
    node: ExecutionNode,
    computability: str,
    *,
    base_state: ComputationState | None = None,
    missing: Sequence[str] = (),
    reason: Sequence[str] = (),
    actions: Sequence[str] = (),
) -> ComputationState:
    # A node's state is a user/AI-supplied request hint, not an attestation of
    # scientific validity.  Core derives the persisted state from the actual
    # execution outcome.  ``base_state`` is reserved for a planner admission's
    # data-availability and gate diagnostics; validity/promotion are still
    # reset on every newly computed result.
    state = base_state if base_state is not None else node.state
    promotion = "diagnostic_only"
    validity = "not_assessed"
    return ComputationState.create(
        data_availability=state.data_availability,
        computability=computability,
        validity=validity,
        promotion=promotion,
        missing_inputs=tuple(state.missing_inputs) + tuple(missing),
        reason_codes=tuple(state.reason_codes) + tuple(reason),
        preconditions=state.preconditions,
        next_actions=tuple(state.next_actions) + tuple(actions),
    )


Executor = Callable[[Mapping[str, Any]], Any]


# A failed process-wide descriptor catalog is a trust-boundary failure, not an
# indication that every capability is an opaque legacy plugin.  Keep a private
# sentinel so ``ExecutionGraph`` can fail closed instead of silently allowing
# an executor to run without a descriptor/admission.
_DESCRIPTOR_REGISTRY_UNAVAILABLE = object()


def _known_descriptor(
    capability_id: str,
    registry: Any,
    *,
    builtin_registry: Any | None = None,
) -> Any:
    """Resolve a descriptor without making the graph import-heavy.

    ExecutionGraph is also used by small compatibility tests and by external
    plugins whose capability IDs are not yet in the process-wide registry.  A
    missing descriptor therefore remains an opaque legacy capability, while a
    known descriptor is subject to its declared status and executor binding.

    The process-wide descriptor registry is authoritative for built-in IDs.
    A caller-supplied registry is additive and may provide plugin descriptors,
    but it cannot hide or replace a built-in descriptor and thereby downgrade
    a known capability to the opaque legacy path.
    """

    builtin_lookup_failed = builtin_registry is _DESCRIPTOR_REGISTRY_UNAVAILABLE
    if builtin_registry is not None and not builtin_lookup_failed:
        try:
            getter = getattr(builtin_registry, "get", None)
            if callable(getter):
                descriptor = getter(capability_id)
                if descriptor is not None:
                    return descriptor
            else:
                builtin_lookup_failed = True
        except ValueError as exc:
            # The default registry uses this exact error shape for an ordinary
            # unknown ID.  Other ValueErrors indicate a broken catalog and
            # must not silently downgrade a capability to opaque legacy mode.
            if not str(exc).startswith("Unknown capability:"):
                builtin_lookup_failed = True
        except Exception:  # noqa: BLE001 - keep plugin compatibility below
            # A failed built-in lookup must not be allowed to silently turn a
            # known capability into an opaque one.  In practice the default
            # registry is immutable and this branch is only a defensive
            # fallback for a broken optional registry implementation.
            builtin_lookup_failed = True

    # Without a functioning process-wide catalog there is no trustworthy way
    # to distinguish a built-in ID from a plugin ID.  Do not let a caller
    # supplied registry fill that gap and thereby restore an unadmitted route.
    if builtin_lookup_failed:
        return _DESCRIPTOR_REGISTRY_UNAVAILABLE

    if registry is not None and registry is not builtin_registry:
        try:
            getter = getattr(registry, "get", None)
            if callable(getter):
                descriptor = getter(capability_id)
                if descriptor is not None:
                    return descriptor
        except Exception:  # noqa: BLE001 - unknown legacy IDs are compatible
            pass

    return None


def _executor_for(
    executors: Mapping[str, Executor],
    node: ExecutionNode,
    descriptor: Any | None,
) -> Executor | None:
    """Look up a callable by canonical capability ID or descriptor key."""

    keys = [node.capability_id]
    if descriptor is not None:
        key = getattr(descriptor, "executor_key", None)
        if isinstance(key, str) and key and key not in keys:
            keys.append(key)
    for key in keys:
        try:
            candidate = executors.get(key)
        except Exception:  # noqa: BLE001 - defensive mapping boundary
            candidate = None
        if callable(candidate):
            return candidate
    return None


def _descriptor_dependency_issue(
    node: ExecutionNode,
    descriptor: Any,
    by_id: Mapping[str, ExecutionNode],
    *,
    registry: Any | None = None,
    builtin_registry: Any | None = None,
    admissions: Mapping[str, Any] | None = None,
    target_admission: Any | None = None,
) -> tuple[str, tuple[str, ...], tuple[str, ...]] | None:
    """Validate that a descriptor's capability dependencies are wired in the DAG.

    Descriptor dependencies are capability identities, while graph edges use
    node IDs.  A matching capability node must therefore exist and be listed as
    a direct dependency of the consumer; otherwise an executable admission
    would authorize a provider that cannot receive the required upstream
    result.
    """

    declared = tuple(
        str(value).strip()
        for value in getattr(descriptor, "dependencies", ()) or ()
        if str(value).strip()
    )
    if not declared:
        return None
    capability_nodes = {
        candidate.capability_id
        for candidate in by_id.values()
    }
    missing = tuple(value for value in declared if value not in capability_nodes)
    if missing:
        return (
            "descriptor_dependency_missing",
            tuple(f"dependency:{value}" for value in missing),
            tuple(f"add_dependency_node:{value}" for value in missing),
        )
    direct_nodes_by_capability: dict[str, list[ExecutionNode]] = {}
    for dependency_node_id in node.dependencies:
        dependency_node = by_id.get(dependency_node_id)
        if dependency_node is None:
            continue
        direct_nodes_by_capability.setdefault(
            dependency_node.capability_id,
            [],
        ).append(dependency_node)
    direct_capabilities = set(direct_nodes_by_capability)
    unwired = tuple(value for value in declared if value not in direct_capabilities)
    if unwired:
        return (
            "descriptor_dependency_unwired",
            tuple(f"dependency:{value}" for value in unwired),
            tuple(f"wire_dependency:{value}" for value in unwired),
        )
    ambiguous = tuple(
        value
        for value in declared
        if len(direct_nodes_by_capability.get(value, ())) != 1
    )
    if ambiguous:
        return (
            "descriptor_dependency_ambiguous",
            tuple(f"dependency:{value}" for value in ambiguous),
            tuple(f"disambiguate_dependency:{value}" for value in ambiguous),
        )

    # A declared capability dependency is itself a canonical computation, not
    # an opaque plug-in input.  Resolve every wired dependency through the same
    # runtime catalog used for the consumer.  Otherwise a caller can provide a
    # target admission from a richer planner registry while the dependency is
    # silently downgraded to the legacy opaque path and executed without its
    # own descriptor/admission boundary.
    if registry is not None or builtin_registry is not None:
        unresolved: list[str] = []
        missing_admissions: list[str] = []
        mismatched_admissions: list[str] = []
        missing_bindings: list[str] = []
        for dependency in declared:
            dependency_nodes = direct_nodes_by_capability.get(dependency, ())
            if len(dependency_nodes) != 1:
                # The graph/edge checks above already report this case; keep
                # this guard for unusual Mapping implementations.
                continue
            dependency_descriptor = _known_descriptor(
                dependency,
                registry,
                builtin_registry=builtin_registry,
            )
            if dependency_descriptor is None or dependency_descriptor is _DESCRIPTOR_REGISTRY_UNAVAILABLE:
                unresolved.append(dependency)
                continue
            if admissions is None:
                missing_admissions.append(dependency)
                continue
            dependency_node = dependency_nodes[0]
            dependency_admission = admissions.get(dependency_node.node_id)
            if not _is_plan_item(dependency_admission) or not dependency_admission.is_trusted_admission:
                missing_admissions.append(dependency)
                continue
            if (
                dependency_admission.capability_id != dependency
                or dependency_admission.descriptor_version
                != str(getattr(dependency_descriptor, "version", ""))
                or dependency_admission.descriptor_hash
                != getattr(dependency_descriptor, "content_hash", None)
                or dependency_admission.outcome != "executable"
                or dependency_admission.state.computability != "computed"
            ):
                mismatched_admissions.append(dependency)
                continue
            if _is_plan_item(target_admission) and target_admission.is_trusted_admission:
                binding = next(
                    (
                        item
                        for item in getattr(target_admission, "dependency_bindings", ())
                        if item.get("capability_id") == dependency
                    ),
                    None,
                )
                if binding is None:
                    missing_bindings.append(dependency)
                    continue
                if (
                    binding.get("descriptor_version")
                    != str(getattr(dependency_descriptor, "version", ""))
                    or binding.get("descriptor_hash")
                    != getattr(dependency_descriptor, "content_hash", None)
                    or binding.get("admission_hash") != dependency_admission.admission_hash
                ):
                    mismatched_admissions.append(dependency)
        if unresolved:
            return (
                "descriptor_dependency_registry_missing",
                tuple(f"descriptor:{value}" for value in unresolved),
                ("restore_descriptor_registry",),
            )
        if missing_admissions:
            return (
                "descriptor_dependency_admission_missing",
                tuple(f"admission:{value}" for value in missing_admissions),
                tuple(f"plan_capability:{value}" for value in missing_admissions),
            )
        if mismatched_admissions:
            return (
                "descriptor_dependency_admission_mismatch",
                tuple(f"admission:{value}" for value in mismatched_admissions),
                ("replan_capability",),
            )
        if missing_bindings:
            return (
                "descriptor_dependency_admission_binding_missing",
                tuple(f"binding:{value}" for value in missing_bindings),
                ("replan_capability",),
            )
    return None


def _descriptor_declares_calibration(descriptor: Any) -> bool:
    """Whether a descriptor requires an explicit calibration identity."""

    contract = getattr(descriptor, "input_contract", {})
    if isinstance(contract, Mapping) and contract.get("required_calibrations"):
        return True
    for precondition in getattr(descriptor, "preconditions", ()) or ():
        if not isinstance(precondition, Mapping):
            continue
        kind = str(precondition.get("kind", precondition.get("type", ""))).strip().lower()
        if kind == "calibration":
            return True
    policy = getattr(descriptor, "evidence_policy", {})
    return isinstance(policy, Mapping) and policy.get("requires_reviewed_calibration") is True


def _calibration_binding_issue(
    node: ExecutionNode,
    descriptor: Any,
    admission: Any,
    context: ExecutionContext,
) -> tuple[str, tuple[str, ...], tuple[str, ...]] | None:
    """Require runtime calibration hashes to match the planner admission."""

    if not node.uses_calibration_for(descriptor):
        return None
    if not context.calibration_hashes:
        return (
            "calibration_context_missing",
            ("calibration_context",),
            ("provide_calibration_context",),
        )
    expected = tuple(getattr(admission, "calibration_hashes", ()) or ())
    if _descriptor_declares_calibration(descriptor) and not expected:
        return (
            "calibration_binding_missing",
            ("calibration_binding",),
            ("replan_capability",),
        )
    supplied = set(context.calibration_hashes)
    missing = tuple(f"calibration:{value}" for value in expected if value not in supplied)
    if missing:
        return ("calibration_binding_mismatch", missing, ("replan_capability",))
    return None


_RUNTIME_INPUT_NAMESPACES = (
    "runtime_inputs",
    "input_bindings",
    "available_inputs",
    "input_declarations",
    "inputs",
    "context",
)
_DECLARATION_MARKERS = {
    "status",
    "state",
    "computability",
    "available",
    "planned",
    "executable",
    "ready",
    "provided",
    "observed",
    "calibrated",
    "computed",
    "completed",
}
_EXPLICIT_BINDING_KEYS = {
    "value",
    "values",
    "data",
    "ref",
    "uri",
    "path",
    "array_ref",
    "artifact_id",
    "input_id",
}
_STATUS_ONLY_VALUES = frozenset(
    {
        "available",
        "provided",
        "ready",
        "observed",
        "calibrated",
        "computed",
        "completed",
        "planned",
        "executable",
        "missing",
        "unavailable",
        "unknown",
        "blocked",
        "invalid",
    }
)


def _runtime_input_is_materialized(value: Any) -> bool:
    """Return whether a required-input declaration carries a concrete value.

    Planner declarations intentionally only prove that an input is available;
    they do not bind that input to this graph invocation.  Runtime bindings
    therefore reject status-only mappings and accept explicit values/refs (or
    ordinary non-empty structured values).  ``False`` and ``0`` are valid
    concrete values, while ``None`` and blank strings are not.
    """

    if value is None:
        return False
    if isinstance(value, str):
        normalized = value.strip().casefold()
        return bool(normalized) and normalized not in _STATUS_ONLY_VALUES
    if isinstance(value, Mapping):
        explicit_binding = False
        for key in _EXPLICIT_BINDING_KEYS:
            if key in value:
                explicit_binding = True
                if _runtime_input_is_materialized(value[key]):
                    return True
        if explicit_binding:
            return False
        # A declaration containing only state/availability metadata is not a
        # binding.  Other mappings are treated as concrete structured values.
        if set(value).intersection(_DECLARATION_MARKERS):
            return False
        return bool(value)
    if isinstance(value, (tuple, list, set, frozenset)):
        return bool(value)
    return True


def _runtime_input_binding(node: ExecutionNode, context: ExecutionContext, name: str) -> Any:
    """Find a concrete required-input binding from node parameters/context."""

    sources: list[Mapping[str, Any]] = []
    if isinstance(node.parameters, Mapping):
        sources.append(node.parameters)
    metadata = context.metadata
    if isinstance(metadata, Mapping):
        sources.append(metadata)
    seen: set[int] = set()
    while sources:
        source = sources.pop(0)
        if id(source) in seen:
            continue
        seen.add(id(source))
        for namespace in _RUNTIME_INPUT_NAMESPACES:
            nested = source.get(namespace)
            if isinstance(nested, Mapping):
                if name in nested:
                    value = nested[name]
                    if _runtime_input_is_materialized(value):
                        return value
                # Permit a bounded context/input_bindings envelope while
                # retaining exact-name lookup and materialization checks.
                sources.append(nested)
        if name in source and _runtime_input_is_materialized(source[name]):
            return source[name]
    return None


def _required_input_context_issue(
    node: ExecutionNode,
    descriptor: Any,
    context: ExecutionContext,
) -> tuple[str, ...]:
    """Return required-input labels that lack a concrete runtime binding."""

    contract = getattr(descriptor, "input_contract", {})
    if not isinstance(contract, Mapping):
        return ()
    missing: list[str] = []
    required = contract.get("required_inputs", ())
    if isinstance(required, str):
        required = (required,)
    if isinstance(required, Sequence) and not isinstance(required, (str, bytes, bytearray)):
        for name in required:
            label = str(name).strip()
            if label and _runtime_input_binding(node, context, label) is None:
                missing.append(label)
    groups = contract.get("required_any_inputs", ())
    if isinstance(groups, Sequence) and not isinstance(groups, (str, bytes, bytearray)):
        for group in groups:
            if not isinstance(group, Sequence) or isinstance(group, (str, bytes, bytearray)):
                continue
            labels = tuple(str(name).strip() for name in group if str(name).strip())
            if labels and not any(_runtime_input_binding(node, context, label) is not None for label in labels):
                missing.append("one_of:" + "|".join(labels))
    return tuple(dict.fromkeys(missing))


def _is_plan_item(value: Any) -> bool:
    """Avoid importing the planner at module import time while type-checking."""

    try:
        from .planner import CapabilityPlanItem

        # Admission authority is deliberately not polymorphic.  A subclass
        # can override ``is_trusted_admission`` and otherwise make an
        # unissued object look trusted, so only the exact Core DTO is accepted
        # at this security boundary.
        return type(value) is CapabilityPlanItem
    except Exception:  # noqa: BLE001 - planner remains an optional boundary
        return False


def _plan_item_from_mapping(value: Mapping[str, Any]) -> Any:
    from .planner import CapabilityPlanItem

    return CapabilityPlanItem.from_dict(value)


def _normalize_admissions(admissions: Mapping[str, Any] | None) -> dict[str, Any]:
    if admissions is None:
        return {}
    if not isinstance(admissions, Mapping):
        raise TypeError("admissions must be a mapping of node IDs to planner items")
    normalized: dict[str, Any] = {}
    for node_id, admission in admissions.items():
        if not isinstance(node_id, str) or not node_id:
            raise TypeError("admission node IDs must be nonempty strings")
        if isinstance(admission, Mapping):
            admission = _plan_item_from_mapping(admission)
        normalized[node_id] = admission
    return normalized


class _ExecutionRequest(dict[str, Any]):
    """Mapping passed to executors, with typed convenience attributes.

    The mapping keeps lightweight adapters compatible with JSON-oriented
    callables, while attributes make the request pleasant for native Python
    executors.  It is intentionally private: the public persisted contract is
    the node result and its provenance, not an executor implementation type.
    """

    def __init__(
        self,
        *,
        context: ExecutionContext,
        node: ExecutionNode,
        parameters: Mapping[str, Any],
        dependencies: Mapping[str, Any],
        dependency_results: Mapping[str, Mapping[str, Any]],
        cache_key: str,
    ) -> None:
        super().__init__(
            context=context.to_dict(),
            node=node.to_dict(),
            parameters=_public(parameters),
            dependencies=_public(dependencies),
            dependency_results=_public(dependency_results),
            cache_key=cache_key,
        )
        self._context = context
        self._node = node

    @property
    def context(self) -> ExecutionContext:
        return self._context

    @property
    def node(self) -> ExecutionNode:
        return self._node


@dataclass(frozen=True)
class ExecutionGraph:
    """A validated DAG with deterministic synchronous execution."""

    nodes: tuple[ExecutionNode, ...]
    graph_id: str = field(init=False)
    _order: tuple[str, ...] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if isinstance(self.nodes, (str, bytes, bytearray)) or not isinstance(self.nodes, Sequence):
            raise TypeError("Execution graph nodes must be a sequence")
        nodes = tuple(self.nodes)
        if any(not isinstance(node, ExecutionNode) for node in nodes):
            raise TypeError("Execution graph nodes must contain ExecutionNode values")
        ids = [node.node_id for node in nodes]
        if len(set(ids)) != len(ids):
            raise ValueError("Execution graph node IDs must be unique")
        known = set(ids)
        for node in nodes:
            unknown = set(node.dependencies).difference(known)
            if unknown:
                raise ValueError(f"Execution graph has unknown dependency: {sorted(unknown)[0]}")
        # Persist and traverse nodes in a canonical order independent of the
        # caller's tuple/list ordering.  This keeps graph IDs and serialized
        # plans stable when an equivalent plan is assembled by different
        # entrypoints.
        nodes = tuple(sorted(nodes, key=lambda node: node.node_id))
        order = self._topological_order(nodes)
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "_order", order)
        payload = {"nodes": [node.to_dict() for node in nodes]}
        object.__setattr__(self, "graph_id", canonical_json_hash(payload))

    @staticmethod
    def _topological_order(nodes: tuple[ExecutionNode, ...]) -> tuple[str, ...]:
        by_id = {node.node_id: node for node in nodes}
        indegree = {node.node_id: len(node.dependencies) for node in nodes}
        dependents = {node.node_id: [] for node in nodes}
        for node in nodes:
            for dependency in node.dependencies:
                dependents[dependency].append(node.node_id)
        queue = sorted(node.node_id for node in nodes if indegree[node.node_id] == 0)
        order: list[str] = []
        while queue:
            current = queue.pop(0)
            order.append(current)
            for dependent in sorted(dependents[current]):
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    queue.append(dependent)
            queue.sort()
        if len(order) != len(nodes):
            raise ValueError("Execution graph contains a dependency cycle")
        # ``by_id`` is intentionally materialized above to validate all nodes
        # before traversal and keep this routine easy to audit.
        del by_id
        return tuple(order)

    @classmethod
    def create(cls, nodes: Sequence[ExecutionNode]) -> "ExecutionGraph":
        return cls(tuple(nodes))

    def to_dict(self) -> dict[str, Any]:
        return {"graph_id": self.graph_id, "nodes": [node.to_dict() for node in self.nodes]}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExecutionGraph":
        if not isinstance(value, Mapping):
            raise TypeError("Execution graph must be a mapping")
        graph = cls.create(tuple(ExecutionNode.from_dict(item) for item in value.get("nodes", ())))
        if value.get("graph_id") != graph.graph_id:
            raise ValueError("Execution graph ID does not match its content")
        return graph

    def execute(
        self,
        context: ExecutionContext,
        executors: Mapping[str, Executor] | None = None,
        *,
        cache: Mapping[str, Any] | None = None,
        descriptor_registry: Any | None = None,
        capability_registry: Any | None = None,
        admissions: Mapping[str, Any] | None = None,
    ) -> ExecutionResult:
        if not isinstance(context, ExecutionContext):
            raise TypeError("ExecutionGraph.execute expects an ExecutionContext")
        if executors is None:
            executors = {}
        if not isinstance(executors, Mapping):
            raise TypeError("executors must be a mapping")
        if cache is not None and not isinstance(cache, Mapping):
            raise TypeError("cache must be a mapping")
        if descriptor_registry is not None and capability_registry is not None and descriptor_registry is not capability_registry:
            raise ValueError("ExecutionGraph received conflicting descriptor registries")
        normalized_admissions = _normalize_admissions(admissions)
        selected_registry = descriptor_registry if descriptor_registry is not None else capability_registry
        # Resolve the process-wide catalog independently of any caller-supplied
        # registry.  Custom registries are additive plugin catalogs; they must
        # not be able to hide a built-in descriptor and downgrade it to the
        # opaque legacy path.
        try:
            from .capabilities import default_descriptor_registry

            builtin_registry = default_descriptor_registry()
        except Exception:  # noqa: BLE001 - fail closed at the descriptor boundary
            builtin_registry = _DESCRIPTOR_REGISTRY_UNAVAILABLE
        if selected_registry is None and builtin_registry is not _DESCRIPTOR_REGISTRY_UNAVAILABLE:
            selected_registry = builtin_registry
        by_id = {node.node_id: node for node in self.nodes}
        unknown_admissions = set(normalized_admissions).difference(by_id)
        if unknown_admissions:
            raise ValueError(
                f"ExecutionGraph received admission for unknown node: {sorted(unknown_admissions)[0]}"
            )
        # Record capability IDs that are declared as dependencies by any
        # descriptor in this graph.  If a runtime catalog cannot resolve such
        # a node, it must not be downgraded to the opaque legacy compatibility
        # path; it is part of a canonical dependency chain and therefore
        # needs the same descriptor/admission boundary as its consumer.
        declared_dependency_capabilities: set[str] = set()
        if builtin_registry is not _DESCRIPTOR_REGISTRY_UNAVAILABLE:
            for candidate in self.nodes:
                candidate_descriptor = _known_descriptor(
                    candidate.capability_id,
                    selected_registry,
                    builtin_registry=builtin_registry,
                )
                if candidate_descriptor in (None, _DESCRIPTOR_REGISTRY_UNAVAILABLE):
                    continue
                declared_dependency_capabilities.update(
                    str(value).strip()
                    for value in getattr(candidate_descriptor, "dependencies", ()) or ()
                    if str(value).strip()
                )
        results: dict[str, NodeResult] = {}
        for node_id in self._order:
            node = by_id[node_id]
            dependency_identities = {
                dependency: results[dependency].cache_key for dependency in node.dependencies
            }
            descriptor = _known_descriptor(
                node.capability_id,
                selected_registry,
                builtin_registry=builtin_registry,
            )
            admission = normalized_admissions.get(node.node_id)
            admission_hash = (
                admission.admission_hash
                if _is_plan_item(admission) and admission.is_trusted_admission
                else None
            )
            key = node.cache_key(
                context,
                dependency_identities,
                descriptor=descriptor,
                admission_hash=admission_hash,
            )
            provenance = {
                "node_id": node.node_id,
                "capability_id": node.capability_id,
                "descriptor_version": node.descriptor_version,
                "descriptor_hash": getattr(descriptor, "content_hash", None),
                "cache_key": key,
                "dependencies": [
                    {"node_id": dependency, "cache_key": dependency_identities[dependency]}
                    for dependency in node.dependencies
                ],
                "input_hashes": list(context.input_hashes),
                "calibration_hashes": list(context.calibration_hashes)
                if node.uses_calibration_for(descriptor)
                else [],
                "runtime_fingerprint": context.runtime_fingerprint,
                "parameters": _public(node.parameters),
                "cache_hit": False,
            }
            if admission_hash is not None:
                provenance["admission_hash"] = admission_hash

            if descriptor is _DESCRIPTOR_REGISTRY_UNAVAILABLE:
                state = _state_for(
                    node,
                    "blocked",
                    reason=("descriptor_registry_unavailable",),
                    actions=("restore_descriptor_registry",),
                )
                result = NodeResult(
                    node.node_id,
                    node.capability_id,
                    "blocked",
                    state,
                    key,
                    None,
                    provenance,
                )
                results[node_id] = result
                continue

            if descriptor is None and node.capability_id in declared_dependency_capabilities:
                state = _state_for(
                    node,
                    "blocked",
                    missing=(f"descriptor:{node.capability_id}",),
                    reason=("descriptor_dependency_registry_missing",),
                    actions=("restore_descriptor_registry",),
                )
                result = NodeResult(
                    node.node_id,
                    node.capability_id,
                    "blocked",
                    state,
                    key,
                    None,
                    provenance,
                )
                results[node_id] = result
                continue

            # Opaque legacy/plugin IDs retain the original node-state escape
            # hatch because no canonical descriptor exists to re-plan them.
            # Registered capabilities take the stricter admission path below;
            # callers cannot make one executable by setting node.state.
            if descriptor is None and node.state.computability in {
                "needs_input",
                "blocked",
                "not_applicable",
                "failed",
            }:
                status = node.state.computability
                # A declared failed state still needs a stable error payload;
                # NodeResult deliberately rejects failed results without one.
                error = f"declared_failed:{node.capability_id}" if status == "failed" else None
                state = _state_for(node, status)
                result = NodeResult(
                    node.node_id,
                    node.capability_id,
                    status,
                    state,
                    key,
                    None,
                    provenance,
                    error,
                )
                results[node_id] = result
                continue

            # A descriptor status is authoritative over a caller-supplied
            # callable.  In particular, an unsupported capability must never
            # be made executable by registering an arbitrary function under
            # its ID.  Experimental routes require an actual binding under
            # either the canonical ID or the descriptor's executor key;
            # merely declaring a string key in the descriptor is not enough.
            if descriptor is not None:
                descriptor_version = str(getattr(descriptor, "version", ""))
                if descriptor_version and node.descriptor_version != descriptor_version:
                    state = _state_for(
                        node,
                        "needs_input",
                        missing=(
                            f"descriptor_version:{node.capability_id}:{descriptor_version}",
                        ),
                        reason=("descriptor_version_mismatch",),
                        actions=(f"update_descriptor:{node.capability_id}",),
                    )
                    result = NodeResult(
                        node.node_id,
                        node.capability_id,
                        "needs_input",
                        state,
                        key,
                        None,
                        provenance,
                    )
                    results[node_id] = result
                    continue
                descriptor_status = getattr(descriptor, "status", None)
                if descriptor_status in {"unsupported", "deprecated"}:
                    state = _state_for(
                        node,
                        "not_applicable",
                        reason=(
                            "capability_unsupported"
                            if descriptor_status == "unsupported"
                            else "capability_deprecated",
                        ),
                    )
                    result = NodeResult(
                        node.node_id,
                        node.capability_id,
                        "not_applicable",
                        state,
                        key,
                        None,
                        provenance,
                    )
                    results[node_id] = result
                    continue
                if descriptor_status == "needs_input":
                    state = _state_for(
                        node,
                        "needs_input",
                        missing=(f"descriptor:{node.capability_id}",),
                        reason=("capability_declared_needs_input",),
                    )
                    result = NodeResult(
                        node.node_id,
                        node.capability_id,
                        "needs_input",
                        state,
                        key,
                        None,
                        provenance,
                    )
                    results[node_id] = result
                    continue
                dependency_issue = _descriptor_dependency_issue(
                    node,
                    descriptor,
                    by_id,
                    registry=selected_registry,
                    builtin_registry=builtin_registry,
                    admissions=normalized_admissions,
                    target_admission=admission,
                )
                if dependency_issue is not None:
                    issue_reason, missing_dependencies, actions = dependency_issue
                    state = _state_for(
                        node,
                        "blocked",
                        missing=missing_dependencies,
                        reason=(issue_reason,),
                        actions=actions,
                    )
                    result = NodeResult(
                        node.node_id,
                        node.capability_id,
                        "blocked",
                        state,
                        key,
                        None,
                        provenance,
                    )
                    results[node_id] = result
                    continue
                if admission is None:
                    state = _state_for(
                        node,
                        "needs_input",
                        missing=("planner_admission",),
                        reason=("planner_admission_required",),
                        actions=(f"plan_capability:{node.capability_id}",),
                    )
                    result = NodeResult(
                        node.node_id,
                        node.capability_id,
                        "needs_input",
                        state,
                        key,
                        None,
                        provenance,
                    )
                    results[node_id] = result
                    continue
                if not _is_plan_item(admission) or not admission.is_trusted_admission:
                    state = _state_for(
                        node,
                        "blocked",
                        reason=("planner_admission_untrusted",),
                    )
                    result = NodeResult(
                        node.node_id,
                        node.capability_id,
                        "blocked",
                        state,
                        key,
                        None,
                        provenance,
                    )
                    results[node_id] = result
                    continue
                admission_mismatch: list[str] = []
                if admission.capability_id != node.capability_id:
                    admission_mismatch.append("capability_id")
                if admission.descriptor_version != descriptor_version:
                    admission_mismatch.append("descriptor_version")
                if admission.descriptor_hash != getattr(descriptor, "content_hash", None):
                    admission_mismatch.append("descriptor_hash")
                if admission_mismatch:
                    state = _state_for(
                        node,
                        "blocked",
                        reason=("planner_admission_mismatch",),
                        actions=("replan_capability",),
                    )
                    provenance["admission_mismatch_fields"] = admission_mismatch
                    result = NodeResult(
                        node.node_id,
                        node.capability_id,
                        "blocked",
                        state,
                        key,
                        None,
                        provenance,
                    )
                    results[node_id] = result
                    continue
                selected_input_id = admission.selected_input_id
                input_type = getattr(descriptor, "input_contract", {}).get(
                    "input_type", "data_block"
                )
                if selected_input_id is None or selected_input_id not in context.input_hashes:
                    input_label = "provider_result" if input_type == "provider_result" else "data_block"
                    missing_input = (
                        f"{input_label}:{selected_input_id}"
                        if selected_input_id is not None
                        else input_label
                    )
                    state = _state_for(
                        node,
                        "needs_input",
                        missing=(missing_input,),
                        reason=("planner_admission_input_mismatch",),
                        actions=("replan_capability",),
                    )
                    result = NodeResult(
                        node.node_id,
                        node.capability_id,
                        "needs_input",
                        state,
                        key,
                        None,
                        provenance,
                    )
                    results[node_id] = result
                    continue
                calibration_issue = _calibration_binding_issue(
                    node,
                    descriptor,
                    admission,
                    context,
                )
                if calibration_issue is not None:
                    issue_reason, missing_calibration, calibration_actions = calibration_issue
                    state = _state_for(
                        node,
                        "needs_input",
                        missing=missing_calibration,
                        reason=(issue_reason,),
                        actions=calibration_actions,
                    )
                    result = NodeResult(
                        node.node_id,
                        node.capability_id,
                        "needs_input",
                        state,
                        key,
                        None,
                        provenance,
                    )
                    results[node_id] = result
                    continue
                if admission.outcome != "executable":
                    status = admission.outcome
                    state = _state_for(
                        node,
                        status,
                        base_state=admission.state,
                        reason=("planner_admission_denied",),
                    )
                    result = NodeResult(
                        node.node_id,
                        node.capability_id,
                        status,
                        state,
                        key,
                        None,
                        provenance,
                    )
                    results[node_id] = result
                    continue
                required_input_missing = _required_input_context_issue(node, descriptor, context)
                if required_input_missing:
                    state = _state_for(
                        node,
                        "needs_input",
                        missing=required_input_missing,
                        reason=("required_input_context_missing",),
                        actions=tuple(
                            f"provide_input:{name}" for name in required_input_missing
                        ),
                    )
                    result = NodeResult(
                        node.node_id,
                        node.capability_id,
                        "needs_input",
                        state,
                        key,
                        None,
                        provenance,
                    )
                    results[node_id] = result
                    continue
                if descriptor_status == "experimental":
                    bound = _executor_for(executors, node, descriptor)
                    if bound is None:
                        executor_key = getattr(descriptor, "executor_key", None) or node.capability_id
                        state = _state_for(
                            node,
                            "needs_input",
                            missing=(f"executor:{executor_key}",),
                            reason=("executor_unavailable",),
                            actions=(f"register_executor:{executor_key}",),
                        )
                        result = NodeResult(
                            node.node_id,
                            node.capability_id,
                            "needs_input",
                            state,
                            key,
                            None,
                            provenance,
                        )
                        results[node_id] = result
                        continue

            dependency_results = [results[dependency] for dependency in node.dependencies]
            needs = [
                f"dependency:{dependency.node_id}"
                for dependency in dependency_results
                if dependency.status == "needs_input"
            ]
            blocked = next(
                (dependency for dependency in dependency_results if dependency.status == "blocked"),
                None,
            )
            failed = next((dependency for dependency in dependency_results if dependency.status == "failed"), None)
            not_applicable = next(
                (dependency for dependency in dependency_results if dependency.status == "not_applicable"), None
            )
            if blocked is not None:
                state = _state_for(node, "blocked", reason=("dependency_blocked",))
                result = NodeResult(node.node_id, node.capability_id, "blocked", state, key, None, provenance)
                results[node_id] = result
                continue
            if needs:
                state = _state_for(node, "needs_input", missing=needs, reason=("dependency_needs_input",))
                result = NodeResult(node.node_id, node.capability_id, "needs_input", state, key, None, provenance)
                results[node_id] = result
                continue
            if failed is not None:
                state = _state_for(node, "failed", reason=("dependency_failed",))
                error = f"dependency_failed:{failed.node_id}"
                result = NodeResult(node.node_id, node.capability_id, "failed", state, key, None, provenance, error)
                results[node_id] = result
                continue
            if not_applicable is not None:
                state = _state_for(node, "not_applicable", reason=("dependency_not_applicable",))
                result = NodeResult(node.node_id, node.capability_id, "not_applicable", state, key, None, provenance)
                results[node_id] = result
                continue

            if cache is not None:
                # Cache data can come from a persisted JSON mapping, so every
                # hit is treated as untrusted input.  Any malformed or
                # identity-mismatched entry is a cache miss and must never be
                # silently relabelled as this node's result.
                try:
                    present = key in cache
                    cached = cache[key] if present else None
                except Exception:  # noqa: BLE001 - fail closed on cache adapters
                    present = False
                    cached = None
                if present:
                    cached_result: NodeResult | None = None
                    cache_value_valid = True
                    # Only the exact Core DTO is authoritative when a caller
                    # supplies an in-memory cache object.  Subclasses may add
                    # mutable or forged state while still passing
                    # ``isinstance``; serialized mappings remain supported
                    # through ``NodeResult.from_dict`` below.
                    if type(cached) is NodeResult:
                        candidate = cached
                    elif isinstance(cached, Mapping) and {
                        "node_id",
                        "capability_id",
                        "status",
                        "state",
                        "cache_key",
                    }.issubset(cached):
                        # Accept the serialized public result form, but parse
                        # it through the same constructor validations.
                        try:
                            candidate = NodeResult.from_dict(cached)
                        except Exception:  # noqa: BLE001 - malformed cache miss
                            candidate = None
                            cache_value_valid = False
                    else:
                        # A registered descriptor has a strict admission and
                        # result contract.  A bare raw value has no persisted
                        # status/state/attestation and therefore cannot be
                        # accepted as a completed cache hit.  Keep the old
                        # raw-output compatibility only for opaque plugin IDs
                        # where no shared descriptor exists.
                        if descriptor is not None:
                            cache_value_valid = False
                            candidate = None
                        else:
                            # Raw output remains a supported compatibility
                            # form for opaque IDs, provided it is JSON-safe.
                            try:
                                raw_output = _freeze(cached) if cached is not None else None
                            except Exception:  # noqa: BLE001 - malformed cache miss
                                raw_output = None
                                cache_value_valid = False
                            if cache_value_valid:
                                cached_result = NodeResult(
                                    node.node_id,
                                    node.capability_id,
                                    "completed",
                                    _state_for(node, "computed"),
                                    key,
                                    raw_output,
                                    provenance
                                    | {
                                        "cache_hit": True,
                                        "output_fingerprint": _output_fingerprint(raw_output),
                                    },
                                )
                                candidate = None

                    if cache_value_valid and candidate is not None:
                        try:
                            if descriptor is not None:
                                # Registered capabilities may only reuse a
                                # Core-issued result carrying the complete
                                # provenance for this exact request.  A
                                # matching lookup key alone is insufficient:
                                # persisted/caller-supplied NodeResult values
                                # are untrusted cache input.
                                expected_provenance = _freeze(provenance)
                                required_fields = (
                                    "node_id",
                                    "capability_id",
                                    "descriptor_version",
                                    "descriptor_hash",
                                    "cache_key",
                                    "dependencies",
                                    "input_hashes",
                                    "calibration_hashes",
                                    "runtime_fingerprint",
                                    "parameters",
                                )
                                candidate_provenance = candidate.provenance
                                if any(
                                    field not in candidate_provenance
                                    or candidate_provenance[field] != expected_provenance[field]
                                    for field in required_fields
                                ):
                                    cache_value_valid = False
                                elif type(candidate_provenance.get("cache_hit")) is not bool:
                                    # ``cache_hit`` is a Core-generated
                                    # observation, not a content identity.  A
                                    # caller may persist a result returned from
                                    # an earlier cache hit, so either boolean
                                    # value is valid, but the field itself must
                                    # be present and well-typed in a complete
                                    # Core provenance envelope.
                                    cache_value_valid = False
                                elif "admission_hash" in expected_provenance and (
                                    candidate_provenance.get("admission_hash")
                                    != expected_provenance["admission_hash"]
                                ):
                                    cache_value_valid = False
                                else:
                                    candidate_fingerprint = candidate_provenance.get(
                                        "output_fingerprint"
                                    )
                                    if not isinstance(candidate_fingerprint, str):
                                        cache_value_valid = False
                                    else:
                                        try:
                                            cache_value_valid = (
                                                _hash(
                                                    candidate_fingerprint,
                                                    "NodeResult provenance output_fingerprint",
                                                )
                                                == _output_fingerprint(candidate.output)
                                            )
                                        except Exception:  # noqa: BLE001 - malformed cache miss
                                            cache_value_valid = False
                            # All identities must match the lookup request;
                            # this rejects cross-capability and stale entries.
                            if cache_value_valid and (
                                candidate.node_id != node.node_id
                                or candidate.capability_id != node.capability_id
                                or candidate.cache_key != key
                                or candidate.status != "completed"
                            ):
                                cache_value_valid = False
                            elif cache_value_valid:
                                cached_result = NodeResult(
                                    candidate.node_id,
                                    candidate.capability_id,
                                    candidate.status,
                                    _state_for(node, "computed"),
                                    candidate.cache_key,
                                    candidate.output,
                                    provenance
                                    | {
                                        "cache_hit": True,
                                        "output_fingerprint": candidate.provenance[
                                            "output_fingerprint"
                                        ]
                                        if descriptor is not None
                                        else _output_fingerprint(candidate.output),
                                    },
                                    candidate.error,
                                )
                        except Exception:  # noqa: BLE001 - malformed cache miss
                            cache_value_valid = False

                    if cache_value_valid and cached_result is not None:
                        results[node_id] = cached_result
                        continue

            executor = _executor_for(executors, node, descriptor)
            if not callable(executor):
                state = _state_for(node, "failed", reason=("missing_executor",))
                result = NodeResult(node.node_id, node.capability_id, "failed", state, key, None, provenance, f"missing_executor:{node.capability_id}")
                results[node_id] = result
                continue
            request = _ExecutionRequest(
                context=context,
                node=node,
                parameters=node.parameters,
                dependencies={dependency: results[dependency].output for dependency in node.dependencies},
                dependency_results={dependency: results[dependency].to_dict() for dependency in node.dependencies},
                cache_key=key,
            )
            try:
                output = executor(request)
                # Validate and freeze output before exposing it to consumers.
                output = _freeze(output) if output is not None else None
            except Exception as exc:  # noqa: BLE001 - stable graph failure boundary
                state = _state_for(node, "failed", reason=("executor_error",))
                # Persist only the public reason and exception class.  Raw
                # provider messages may contain local paths, sample details,
                # or non-deterministic text and therefore do not belong in a
                # shared execution result or cache identity.
                error = f"executor_error:{type(exc).__name__}"
                result = NodeResult(node.node_id, node.capability_id, "failed", state, key, None, provenance, error)
                results[node_id] = result
                continue
            state = _state_for(node, "computed")
            provenance["output_fingerprint"] = _output_fingerprint(output)
            result = NodeResult(node.node_id, node.capability_id, "completed", state, key, output, provenance)
            results[node_id] = result
            if isinstance(cache, MutableMapping):
                # Only successful, Core-derived results enter a mutable cache.
                # Failed/blocked/needs-input outcomes must never poison a later
                # retry after the missing input or provider is repaired.
                try:
                    cache[key] = result
                except Exception:  # noqa: BLE001 - cache adapters are optional
                    pass
        return ExecutionResult(self.graph_id, context, tuple(results[node_id] for node_id in self._order))


__all__ = [
    "ExecutionContext",
    "ExecutionNode",
    "NodeResult",
    "ExecutionResult",
    "GraphResult",
    "ExecutionGraph",
]
