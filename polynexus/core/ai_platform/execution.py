"""Small deterministic execution graph used by the AI platform.

The graph intentionally stays synchronous.  It provides a stable planning and
provenance boundary which can later be adapted by ``ComputeRun`` or a queued
worker without giving the GUI or an agent a second result representation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
        elif not isinstance(self.state, ComputationState):
            if isinstance(self.state, Mapping):
                object.__setattr__(self, "state", ComputationState.from_dict(self.state))
            else:
                raise TypeError("Execution node state must be a ComputationState or mapping")
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

    def cache_key(
        self,
        context: ExecutionContext,
        dependency_keys: Mapping[str, str] | Sequence[tuple[str, str]] | None = None,
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
            "parameters": _public(self.parameters),
            "node_metadata": _public(self.metadata),
            "input_hashes": list(context.input_hashes),
            "calibration_hashes": list(context.calibration_hashes) if self.uses_calibration else [],
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
        if not isinstance(self.state, ComputationState):
            raise TypeError("NodeResult state must be a ComputationState")
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
    missing: Sequence[str] = (),
    reason: Sequence[str] = (),
    actions: Sequence[str] = (),
) -> ComputationState:
    state = node.state
    promotion = state.promotion if computability == "computed" else "diagnostic_only"
    validity = state.validity if computability == "computed" else "not_assessed"
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


def _known_descriptor(capability_id: str, registry: Any) -> Any | None:
    """Resolve a descriptor without making the graph import-heavy.

    ExecutionGraph is also used by small compatibility tests and by external
    plugins whose capability IDs are not yet in the process-wide registry.  A
    missing descriptor therefore remains an opaque legacy capability, while a
    known descriptor is subject to its declared status and executor binding.
    """

    if registry is None:
        return None
    try:
        getter = getattr(registry, "get", None)
        if not callable(getter):
            return None
        return getter(capability_id)
    except Exception:  # noqa: BLE001 - unknown legacy IDs are compatible
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
        selected_registry = descriptor_registry if descriptor_registry is not None else capability_registry
        if selected_registry is None:
            # Resolve lazily so importing the low-level graph does not trigger
            # legacy provider registration.  If the optional registry cannot
            # be built, unknown IDs retain the established compatibility path.
            try:
                from .capabilities import default_descriptor_registry

                selected_registry = default_descriptor_registry()
            except Exception:  # noqa: BLE001 - keep opaque plugin IDs usable
                selected_registry = None
        by_id = {node.node_id: node for node in self.nodes}
        results: dict[str, NodeResult] = {}
        for node_id in self._order:
            node = by_id[node_id]
            dependency_identities = {
                dependency: results[dependency].cache_key for dependency in node.dependencies
            }
            key = node.cache_key(context, dependency_identities)
            provenance = {
                "node_id": node.node_id,
                "capability_id": node.capability_id,
                "descriptor_version": node.descriptor_version,
                "cache_key": key,
                "dependencies": [
                    {"node_id": dependency, "cache_key": dependency_identities[dependency]}
                    for dependency in node.dependencies
                ],
                "input_hashes": list(context.input_hashes),
                "calibration_hashes": list(context.calibration_hashes) if node.uses_calibration else [],
                "runtime_fingerprint": context.runtime_fingerprint,
                "parameters": _public(node.parameters),
                "cache_hit": False,
            }

            descriptor = _known_descriptor(node.capability_id, selected_registry)

            if node.state.computability in {"needs_input", "blocked", "not_applicable", "failed"}:
                status = node.state.computability
                # A declared failed state still needs a stable error payload;
                # NodeResult deliberately rejects failed results without one.
                error = (
                    f"declared_failed:{node.capability_id}"
                    if status == "failed"
                    else None
                )
                result = NodeResult(
                    node.node_id,
                    node.capability_id,
                    status,
                    node.state,
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
                    if isinstance(cached, NodeResult):
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
                        # Raw output remains a supported compatibility form,
                        # provided it is JSON-safe.  Arbitrary Python objects
                        # are rejected instead of being exposed as a hit.
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
                                provenance | {"cache_hit": True},
                            )
                            candidate = None

                    if cache_value_valid and candidate is not None:
                        try:
                            # All identities must match the lookup request;
                            # this rejects cross-capability and stale entries.
                            if (
                                candidate.node_id != node.node_id
                                or candidate.capability_id != node.capability_id
                                or candidate.cache_key != key
                            ):
                                cache_value_valid = False
                            else:
                                cached_result = NodeResult(
                                    candidate.node_id,
                                    candidate.capability_id,
                                    candidate.status,
                                    candidate.state,
                                    candidate.cache_key,
                                    candidate.output,
                                    provenance | {"cache_hit": True},
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
            result = NodeResult(node.node_id, node.capability_id, "completed", state, key, output, provenance)
            results[node_id] = result
        return ExecutionResult(self.graph_id, context, tuple(results[node_id] for node_id in self._order))


__all__ = [
    "ExecutionContext",
    "ExecutionNode",
    "NodeResult",
    "ExecutionResult",
    "GraphResult",
    "ExecutionGraph",
]
