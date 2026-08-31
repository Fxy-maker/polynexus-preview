"""Input-aware capability discovery for AI callers."""

from __future__ import annotations

from dataclasses import dataclass, field
from numbers import Real
import re
from typing import Any, Mapping, Sequence

from .capabilities import CapabilityDescriptor, CapabilityDescriptorRegistry, default_descriptor_registry, normalize_technique
from .contracts import (
    ComputationState,
    DataBlock,
    ProviderResultInput,
    _dedupe_actions,
    _dedupe as _dedupe_strings,
    axis_allows_quantitative,
    canonical_json_hash,
)


PLAN_OUTCOMES = frozenset({"executable", "blocked", "needs_input", "not_applicable"})

# Planner admissions are intentionally issued only by ``CapabilityPlanner``.
# The marker is process-local and is not serialized; a JSON plan loaded from an
# untrusted caller must be re-planned before it can authorize execution.
_ADMISSION_TOKEN = object()


def _dedupe(values: Sequence[object]) -> tuple[str, ...]:
    return _dedupe_strings(values, "Capability planner values")


def _public(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _public(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_public(item) for item in value]
    return value


def _is_monotonic(values: Sequence[Real]) -> bool:
    """Return whether numeric coordinates are nondecreasing or nonincreasing."""

    if len(values) < 2:
        return True
    try:
        increasing = all(values[index] <= values[index + 1] for index in range(len(values) - 1))
        decreasing = all(values[index] >= values[index + 1] for index in range(len(values) - 1))
    except (TypeError, ValueError):
        return False
    return increasing or decreasing


_CALIBRATION_HASH_RE = re.compile(r"[0-9a-fA-F]{64}")
_CALIBRATION_IDENTITIES = ("name", "scope", "calibration_id", "id")
_DEPENDENCY_BINDING_KEYS = frozenset(
    {"capability_id", "descriptor_version", "descriptor_hash", "admission_hash"}
)


def _first_calibration_identity(value: Mapping[str, Any]) -> str:
    """Return the first non-empty identity field from a calibration record."""

    for key in _CALIBRATION_IDENTITIES:
        candidate = value.get(key)
        if candidate is None:
            continue
        normalized = str(candidate).strip()
        if normalized:
            return normalized
    return ""


def _calibration_requirements(contract: Mapping[str, Any]) -> tuple[Any, ...]:
    """Normalize the descriptor's scalar-or-sequence calibration declaration."""

    value = contract.get("required_calibrations", ())
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (bytes, bytearray)) or not isinstance(value, Sequence):
        return ()
    return tuple(value)


def _calibration_requirement_names(descriptor: CapabilityDescriptor) -> tuple[str, ...]:
    """Return the descriptor's explicit calibration identities in order."""

    contract = descriptor.input_contract
    names: list[str] = []
    if isinstance(contract, Mapping):
        for value in _calibration_requirements(contract):
            name = (
                _first_calibration_identity(value)
                if isinstance(value, Mapping)
                else str(value).strip()
            )
            if name:
                names.append(name)
    for precondition in descriptor.preconditions:
        if not isinstance(precondition, Mapping):
            continue
        kind = str(precondition.get("kind", precondition.get("type", ""))).strip().lower()
        if kind != "calibration":
            continue
        name = _first_calibration_identity(precondition)
        if name:
            names.append(name)
    return _dedupe_strings(names, "Capability calibration requirements")


def _calibration_record_values(value: Any) -> tuple[Any, ...]:
    """Normalize common calibration containers without treating bare IDs as records."""

    if isinstance(value, Mapping):
        if any(key in value for key in ("status", "scope", "calibration_id", "id", "name")):
            return (value,)
        return tuple(value.values())
    if isinstance(value, (str, bytes, bytearray)):
        return ()
    if isinstance(value, Sequence):
        return tuple(value)
    return ()


def _validated_calibration_hash(
    value: Mapping[str, Any],
    *,
    require_reviewed: bool = False,
) -> str | None:
    """Return a reviewed record hash only when its locator/hash pair is valid."""

    status = str(value.get("status", "")).strip().lower()
    accepted_statuses = {"reviewed"} if require_reviewed else {
        "reviewed",
        "applied_unreviewed",
    }
    if status not in accepted_statuses:
        return None
    locator = value.get("record_locator", value.get("uri"))
    digest = value.get("record_sha256", value.get("sha256"))
    if not isinstance(locator, str) or not locator:
        return None
    if not isinstance(digest, str) or _CALIBRATION_HASH_RE.fullmatch(digest) is None:
        return None
    return digest.lower()


def _calibration_hashes_for_block(
    block: DataBlock,
    descriptor: CapabilityDescriptor,
) -> tuple[str, ...]:
    """Resolve the exact reviewed calibration records satisfying a descriptor."""

    names = _calibration_requirement_names(descriptor)
    if not names:
        return ()
    policy = descriptor.evidence_policy
    require_reviewed = (
        isinstance(policy, Mapping)
        and policy.get("requires_reviewed_calibration") is True
    )
    metadata = block.metadata if isinstance(block.metadata, Mapping) else {}
    hashes: set[str] = set()
    for name in names:
        wanted = name.casefold()
        for key in ("calibrations", "calibration_refs", "calibration_ids"):
            for candidate in _calibration_record_values(metadata.get(key, ())):
                if not isinstance(candidate, Mapping):
                    continue
                identities = tuple(
                    candidate.get(key) for key in _CALIBRATION_IDENTITIES
                )
                if not any(
                    item is not None and str(item).strip().casefold() == wanted
                    for item in identities
                ):
                    continue
                digest = _validated_calibration_hash(
                    candidate,
                    require_reviewed=require_reviewed,
                )
                if digest is not None:
                    hashes.add(digest)
        for axis in (block.axis_provenance or {}).values():
            calibration = axis.calibration_ref
            if calibration is None:
                continue
            if not any(
                str(item).strip().casefold() == wanted
                for item in (calibration.calibration_id, calibration.scope)
            ):
                continue
            if calibration.status == "reviewed" or (
                calibration.status == "applied_unreviewed" and not require_reviewed
            ):
                digest = calibration.record_sha256
                if isinstance(digest, str) and _CALIBRATION_HASH_RE.fullmatch(digest):
                    hashes.add(digest.lower())
    return tuple(sorted(hashes))


def _normalize_dependency_bindings(value: Any) -> tuple[Mapping[str, Any], ...]:
    """Validate immutable descriptor-dependency admission bindings."""

    if value is None:
        return ()
    if isinstance(value, Mapping):
        value = (value,)
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise TypeError("Capability plan dependency_bindings must be a sequence")
    normalized: list[Mapping[str, Any]] = []
    seen: set[str] = set()
    for index, binding in enumerate(value):
        if not isinstance(binding, Mapping):
            raise TypeError(
                f"Capability plan dependency_bindings[{index}] must be a mapping"
            )
        if set(binding) != _DEPENDENCY_BINDING_KEYS:
            unknown = sorted(set(binding) - _DEPENDENCY_BINDING_KEYS)
            missing = sorted(_DEPENDENCY_BINDING_KEYS - set(binding))
            details = []
            if unknown:
                details.append("unknown=" + ",".join(unknown))
            if missing:
                details.append("missing=" + ",".join(missing))
            raise ValueError(
                "Capability plan dependency binding keys are invalid"
                + (" (" + "; ".join(details) + ")" if details else "")
            )
        capability_id = binding["capability_id"]
        descriptor_version = binding["descriptor_version"]
        if not isinstance(capability_id, str) or not capability_id.strip():
            raise ValueError(
                f"Capability plan dependency_bindings[{index}].capability_id must be nonempty"
            )
        if not isinstance(descriptor_version, str) or not descriptor_version.strip():
            raise ValueError(
                f"Capability plan dependency_bindings[{index}].descriptor_version must be nonempty"
            )
        capability_id = capability_id.strip()
        descriptor_version = descriptor_version.strip()
        if capability_id in seen:
            raise ValueError(
                f"Capability plan dependency_bindings duplicate capability: {capability_id}"
            )
        seen.add(capability_id)
        entry: dict[str, Any] = {
            "capability_id": capability_id,
            "descriptor_version": descriptor_version,
        }
        for key in ("descriptor_hash", "admission_hash"):
            digest = binding[key]
            if not isinstance(digest, str) or _CALIBRATION_HASH_RE.fullmatch(digest) is None:
                raise ValueError(
                    f"Capability plan dependency_bindings[{index}].{key} must be a SHA-256"
                )
            entry[key] = digest.lower()
        normalized.append(entry)
    return tuple(normalized)


@dataclass(frozen=True)
class CapabilityPlanItem:
    """One immutable discovery result shared by AI, CLI, GUI and evidence."""

    capability_id: str
    descriptor_version: str
    outcome: str
    state: ComputationState
    data_block_ids: tuple[str, ...] = ()
    selected_data_block_id: str | None = None
    provider_result_ids: tuple[str, ...] = ()
    selected_provider_result_id: str | None = None
    next_actions: tuple[str | Mapping[str, Any], ...] = ()
    descriptor_hash: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    # Content-addressed calibration records selected by the planner for the
    # chosen input.  Execution must bind its runtime context to these exact
    # identities; a merely non-empty calibration context is insufficient.
    calibration_hashes: tuple[str, ...] = ()
    # Content-addressed bindings for every declared capability dependency.
    # These are included in the admission hash so a target admission cannot
    # be replayed with a dependency descriptor or admission from another
    # planner registry.
    dependency_bindings: tuple[Mapping[str, Any], ...] = ()
    _admission_token: object | None = field(default=None, init=False, repr=False, compare=False)
    # Keep a content fingerprint beside the process-local marker.  The marker
    # is deliberately ``init=False`` so ``dataclasses.replace`` cannot carry
    # admission authority to a clone; the fingerprint also detects low-level
    # mutation of a previously issued object.
    _admission_fingerprint: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.outcome not in PLAN_OUTCOMES:
            raise ValueError(f"Unsupported capability plan outcome: {self.outcome}")
        if type(self.state) is not ComputationState:
            raise TypeError(
                "Capability plan state must use the exact ComputationState type"
            )
        capability_id = str(self.capability_id).strip()
        descriptor_version = str(self.descriptor_version).strip()
        if not capability_id:
            raise ValueError("Capability plan capability_id must be nonempty")
        if not descriptor_version:
            raise ValueError("Capability plan descriptor_version must be nonempty")
        expected_computability = {
            "executable": "computed",
            "blocked": "blocked",
            "needs_input": "needs_input",
            "not_applicable": "not_applicable",
        }[self.outcome]
        if self.state.computability != expected_computability:
            raise ValueError(
                f"Capability plan outcome/state mismatch: {self.outcome} requires "
                f"state computability {expected_computability}"
            )
        object.__setattr__(self, "capability_id", capability_id)
        object.__setattr__(self, "descriptor_version", descriptor_version)
        data_block_ids = _dedupe(self.data_block_ids)
        object.__setattr__(self, "data_block_ids", data_block_ids)
        provider_result_ids = _dedupe(self.provider_result_ids)
        object.__setattr__(self, "provider_result_ids", provider_result_ids)
        calibration_hashes = _dedupe(self.calibration_hashes)
        for value in calibration_hashes:
            if not re.fullmatch(r"[0-9a-fA-F]{64}", value):
                raise ValueError("Capability plan calibration_hashes must be SHA-256 values")
        object.__setattr__(self, "calibration_hashes", tuple(value.lower() for value in calibration_hashes))
        dependency_bindings = _normalize_dependency_bindings(self.dependency_bindings)
        from .contracts import _freeze

        object.__setattr__(self, "dependency_bindings", _freeze(dependency_bindings))
        object.__setattr__(self, "next_actions", _dedupe_actions(self.next_actions, "Capability plan next_actions"))
        if self.selected_data_block_id is not None:
            selected = str(self.selected_data_block_id).strip()
            if not selected:
                raise ValueError("Capability plan selected_data_block_id must be nonempty")
            if selected not in data_block_ids:
                raise ValueError(
                    "Capability plan selected_data_block_id must reference a data_block_id"
                )
            object.__setattr__(self, "selected_data_block_id", selected)
        if self.selected_provider_result_id is not None:
            selected_provider = str(self.selected_provider_result_id).strip()
            if not selected_provider:
                raise ValueError(
                    "Capability plan selected_provider_result_id must be nonempty"
                )
            if selected_provider not in provider_result_ids:
                raise ValueError(
                    "Capability plan selected_provider_result_id must reference a provider_result_id"
                )
            object.__setattr__(self, "selected_provider_result_id", selected_provider)
        if self.selected_data_block_id is not None and self.selected_provider_result_id is not None:
            raise ValueError("Capability plan must select exactly one input representation")
        if self.descriptor_hash is not None:
            if not isinstance(self.descriptor_hash, str) or not re.fullmatch(
                r"[0-9a-fA-F]{64}", self.descriptor_hash
            ):
                raise ValueError("Capability plan descriptor_hash must be a SHA-256")
            object.__setattr__(self, "descriptor_hash", self.descriptor_hash.lower())
        if not isinstance(self.metadata, Mapping):
            raise TypeError("Capability plan metadata must be a mapping")
        # Reuse the strict JSON contract; this rejects NaN, unsupported values,
        # and non-string keys instead of producing a non-serializable DTO.
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    @property
    def status(self) -> str:
        """Compatibility alias for callers that use result-style status."""

        return self.outcome

    @property
    def computability(self) -> str:
        return self.state.computability

    @property
    def selected_input_id(self) -> str | None:
        """Identity of the selected DataBlock or provider-result input."""

        return self.selected_data_block_id or self.selected_provider_result_id

    @property
    def is_trusted_admission(self) -> bool:
        """Whether this item was issued by the in-process planner.

        The public fields remain useful as a serializable discovery result, but
        only planner-issued instances can authorize a graph node.  This keeps a
        caller from constructing a ``computed`` item by hand and skipping the
        descriptor gates that produced a real plan.
        """

        if type(self) is not CapabilityPlanItem or self._admission_token is not _ADMISSION_TOKEN:
            return False
        fingerprint = self._admission_fingerprint
        return fingerprint is not None and fingerprint == canonical_json_hash(self.to_dict())

    @property
    def admission_hash(self) -> str:
        """Content identity of the admission payload used by cache keys."""

        return canonical_json_hash(self.to_dict())

    def as_admission(self) -> "CapabilityPlanItem":
        """Return this item when it is a trusted execution admission."""

        if not self.is_trusted_admission:
            raise ValueError("Capability plan item was not issued by CapabilityPlanner")
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "descriptor_version": self.descriptor_version,
            "descriptor_hash": self.descriptor_hash,
            "outcome": self.outcome,
            "status": self.outcome,
            "state": self.state.to_dict(),
            "data_block_ids": list(self.data_block_ids),
            "selected_data_block_id": self.selected_data_block_id,
            "provider_result_ids": list(self.provider_result_ids),
            "selected_provider_result_id": self.selected_provider_result_id,
            "calibration_hashes": list(self.calibration_hashes),
            "dependency_bindings": [_public(value) for value in self.dependency_bindings],
            "next_actions": list(self.next_actions),
            "metadata": _public(self.metadata),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CapabilityPlanItem":
        """Load a discovery item without granting execution authority."""

        if not isinstance(value, Mapping):
            raise TypeError("Capability plan item must be a mapping")
        state = value.get("state")
        if isinstance(state, ComputationState):
            if type(state) is not ComputationState:
                raise TypeError(
                    "Capability plan state must use the exact ComputationState type"
                )
        else:
            state = ComputationState.from_dict(state)
        return cls(
            capability_id=value["capability_id"],
            descriptor_version=value.get("descriptor_version", "1"),
            outcome=value.get("outcome", value.get("status")),
            state=state,
            data_block_ids=value.get("data_block_ids", ()),
            selected_data_block_id=value.get("selected_data_block_id"),
            provider_result_ids=value.get("provider_result_ids", ()),
            selected_provider_result_id=value.get("selected_provider_result_id"),
            calibration_hashes=value.get("calibration_hashes", ()),
            dependency_bindings=value.get("dependency_bindings", ()),
            next_actions=value.get("next_actions", ()),
            descriptor_hash=value.get("descriptor_hash"),
            metadata=value.get("metadata", {}),
        )


class CapabilityPlanner:
    """Check descriptor contracts without invoking a scientific provider.

    Discovery is intentionally usable before a worker pool is configured.  In
    that contract-only mode an ``experimental`` descriptor may be reported as
    ready once its inputs/gates are satisfied; execution still has to bind a
    real callable (the execution graph enforces that boundary).  Callers that
    already have an executor registry can pass it here or to :meth:`inspect`
    to make provider availability part of planning as well.
    """

    def __init__(
        self,
        registry: CapabilityDescriptorRegistry | Sequence[CapabilityDescriptor] | None = None,
        *,
        executors: Mapping[str, Any] | None = None,
        executor_registry: Mapping[str, Any] | None = None,
    ) -> None:
        if registry is None:
            self.registry = default_descriptor_registry()
        elif isinstance(registry, CapabilityDescriptorRegistry):
            self.registry = registry
        else:
            self.registry = CapabilityDescriptorRegistry(tuple(registry))
        if executors is not None and executor_registry is not None and executors is not executor_registry:
            raise ValueError("Capability planner received conflicting executor registries")
        selected_executors = executors if executors is not None else executor_registry
        if selected_executors is not None and not isinstance(selected_executors, Mapping):
            raise TypeError("Capability planner executors must be a mapping")
        self.executors = selected_executors

    def inspect(
        self,
        *,
        data_blocks: Sequence[DataBlock | Mapping[str, Any]] = (),
        target_capabilities: Sequence[str] | None = None,
        technique: str | None = None,
        available_inputs: Mapping[str, Any] | None = None,
        input_declarations: Mapping[str, Any] | None = None,
        context: Mapping[str, Any] | None = None,
        provider_results: Sequence[ProviderResultInput | Mapping[str, Any]] = (),
        available_capabilities: Mapping[str, Any] | None = None,
        executors: Mapping[str, Any] | None = None,
        executor_registry: Mapping[str, Any] | None = None,
        require_executor: bool = False,
    ) -> tuple[CapabilityPlanItem, ...]:
        """Return executable, blocked, needs-input and not-applicable plans."""

        if type(require_executor) is not bool:
            raise TypeError("require_executor must be a boolean")

        blocks = self._normalize_blocks(data_blocks)
        normalized_provider_results = self._normalize_provider_results(provider_results)
        available_capability_admissions: Mapping[str, Any] = {}
        if available_capabilities is not None:
            if not isinstance(available_capabilities, Mapping):
                raise TypeError("available_capabilities must be a mapping")
            # Snapshot once at the public boundary.  The same snapshot drives
            # availability gates and dependency binding hashes, preventing a
            # mutable caller mapping from changing between those decisions.
            available_capability_admissions = dict(available_capabilities)
        declared_capabilities = (
            ()
            if not available_capability_admissions
            else self._available_capability_names(available_capability_admissions)
        )
        declared_inputs = self._planner_available_inputs(
            available_inputs=available_inputs,
            input_declarations=input_declarations,
            context=context,
        )
        if executors is not None and executor_registry is not None and executors is not executor_registry:
            raise ValueError("Capability planner received conflicting executor registries")
        selected_executors = executors if executors is not None else executor_registry
        if selected_executors is None:
            selected_executors = self.executors
        if selected_executors is not None and not isinstance(selected_executors, Mapping):
            raise TypeError("Capability planner executors must be a mapping")
        if target_capabilities is None:
            descriptors = self.registry.for_technique(technique) if technique is not None else self.registry.descriptors
        else:
            if isinstance(target_capabilities, (str, bytes, bytearray)):
                target_capabilities = (str(target_capabilities),)
            descriptors = tuple(self.registry.get(value, technique=technique) for value in target_capabilities)
        return tuple(
            self._inspect_descriptor(
                descriptor,
                blocks,
                declared_inputs,
                normalized_provider_results,
                declared_capabilities,
                available_capability_admissions,
                executors=selected_executors,
                require_executor=require_executor,
            )
            for descriptor in descriptors
        )

    def discover(
        self,
        data_blocks: Sequence[DataBlock | Mapping[str, Any]] = (),
        *,
        target_capabilities: Sequence[str] | None = None,
        technique: str | None = None,
        available_inputs: Mapping[str, Any] | None = None,
        input_declarations: Mapping[str, Any] | None = None,
        context: Mapping[str, Any] | None = None,
        provider_results: Sequence[ProviderResultInput | Mapping[str, Any]] = (),
        available_capabilities: Mapping[str, Any] | None = None,
        executors: Mapping[str, Any] | None = None,
        executor_registry: Mapping[str, Any] | None = None,
        require_executor: bool = False,
    ) -> tuple[CapabilityPlanItem, ...]:
        """Alias used by tool adapters that call this operation discovery."""

        return self.inspect(
            data_blocks=data_blocks,
            target_capabilities=target_capabilities,
            technique=technique,
            available_inputs=available_inputs,
            input_declarations=input_declarations,
            context=context,
            provider_results=provider_results,
            available_capabilities=available_capabilities,
            executors=executors,
            executor_registry=executor_registry,
            require_executor=require_executor,
        )

    @staticmethod
    def _normalize_blocks(data_blocks: Sequence[DataBlock | Mapping[str, Any]]) -> tuple[DataBlock, ...]:
        if isinstance(data_blocks, (DataBlock, Mapping)):
            data_blocks = (data_blocks,)
        if isinstance(data_blocks, (str, bytes, bytearray)):
            raise TypeError("Capability planner data_blocks must be a sequence")
        normalized: list[DataBlock] = []
        for block in data_blocks:
            if isinstance(block, DataBlock):
                normalized.append(block)
            elif isinstance(block, Mapping):
                normalized.append(DataBlock.from_dict(block))
            else:
                raise TypeError("Capability planner data_blocks must contain DataBlock values")
        return tuple(normalized)

    def _inspect_descriptor(
        self,
        descriptor: CapabilityDescriptor,
        blocks: tuple[DataBlock, ...],
        declared_inputs: tuple[str, ...],
        provider_results: tuple[ProviderResultInput, ...] = (),
        available_capabilities: tuple[str, ...] = (),
        available_capability_admissions: Mapping[str, Any] | None = None,
        *,
        executors: Mapping[str, Any] | None = None,
        require_executor: bool = False,
    ) -> CapabilityPlanItem:
        if descriptor.status in {"unsupported", "deprecated"}:
            state = ComputationState.create(
                data_availability="canonical" if blocks else "missing",
                computability="not_applicable",
                validity="not_assessed",
                promotion="diagnostic_only",
                reason_codes=("capability_unsupported" if descriptor.status == "unsupported" else "capability_deprecated",),
                next_actions=descriptor.missing_input_actions,
            )
            return self._item(descriptor, "not_applicable", state)

        if descriptor.status == "needs_input":
            state = ComputationState.create(
                data_availability="canonical" if blocks else "missing",
                computability="needs_input",
                validity="not_assessed",
                promotion="diagnostic_only",
                missing_inputs=self._required_input_labels(descriptor.input_contract) or ("descriptor_input",),
                reason_codes=("capability_declared_needs_input",),
                next_actions=descriptor.missing_input_actions,
            )
            return self._item(descriptor, "needs_input", state)

        if descriptor.input_contract.get("input_type", "data_block") == "provider_result":
            return self._inspect_provider_result_descriptor(
                descriptor,
                provider_results,
                available_capabilities,
                dependency_bindings=self._dependency_bindings(
                    descriptor, available_capability_admissions
                ),
            )

        # An explicit executor registry is an opt-in stronger planning mode.
        # It is deliberately not implied by the descriptor's string
        # ``executor_key``: a name alone is not a provider binding and must
        # never be allowed to produce a scientific value.
        if descriptor.status == "experimental" and (require_executor or executors is not None):
            executor_key = descriptor.executor_key or descriptor.capability_id
            bound = False
            if executors is not None:
                for key in (descriptor.capability_id, descriptor.executor_key):
                    if key is not None and callable(executors.get(key)):
                        bound = True
                        break
            if not bound:
                state = ComputationState.create(
                    data_availability="canonical" if blocks else "missing",
                    computability="needs_input",
                    validity="not_assessed",
                    promotion="diagnostic_only",
                    missing_inputs=(f"executor:{executor_key}",),
                    reason_codes=("executor_unavailable",),
                    next_actions=(f"register_executor:{executor_key}",),
                )
                return self._item(descriptor, "needs_input", state)

        matching = tuple(block for block in blocks if self._matches_input_contract(block, descriptor.input_contract, descriptor))
        if not matching:
            required = self._required_input_labels(descriptor.input_contract)
            state = ComputationState.create(
                data_availability="missing" if not blocks else "partial",
                computability="needs_input",
                validity="not_assessed",
                promotion="diagnostic_only",
                missing_inputs=required or ("data_block",),
                reason_codes=("data_block_missing",),
                next_actions=tuple(descriptor.missing_input_actions) + ("provide_data_block",),
            )
            return self._item(descriptor, "needs_input", state)

        evaluated: list[tuple[int, DataBlock, tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = []
        for candidate in matching:
            blocked_reasons, missing_inputs, actions = self._evaluate_gates(
                candidate,
                descriptor,
                declared_inputs,
                available_capabilities,
            )
            priority = 0 if not blocked_reasons and not missing_inputs else (1 if missing_inputs else 2)
            evaluated.append((priority, candidate, blocked_reasons, missing_inputs, actions))
        _, selected, blocked_reasons, missing_inputs, actions = min(
            evaluated, key=lambda item: (item[0], matching.index(item[1]))
        )
        if blocked_reasons:
            state = ComputationState.create(
                data_availability="canonical",
                computability="blocked",
                validity="not_assessed",
                promotion="diagnostic_only",
                reason_codes=blocked_reasons,
                next_actions=_dedupe_actions(tuple(descriptor.missing_input_actions) + actions, "Capability plan next_actions"),
            )
            return self._item(descriptor, "blocked", state, matching, selected)
        if missing_inputs:
            state = ComputationState.create(
                data_availability="canonical",
                computability="needs_input",
                validity="not_assessed",
                promotion="diagnostic_only",
                missing_inputs=missing_inputs,
                reason_codes=tuple(f"missing_input:{value}" for value in missing_inputs),
                next_actions=_dedupe_actions(tuple(descriptor.missing_input_actions) + actions, "Capability plan next_actions"),
            )
            return self._item(descriptor, "needs_input", state, matching, selected)

        state = ComputationState.create(
            data_availability="canonical",
            computability="computed",
            validity="not_assessed",
            promotion="diagnostic_only",
            next_actions=_dedupe_actions(descriptor.missing_input_actions, "Capability plan next_actions"),
        )
        return self._item(
            descriptor,
            "executable",
            state,
            matching,
            selected,
            dependency_bindings=self._dependency_bindings(
                descriptor, available_capability_admissions
            ),
        )

    def _dependency_bindings(
        self,
        descriptor: CapabilityDescriptor,
        available_capabilities: Mapping[str, Any] | None,
    ) -> tuple[Mapping[str, str], ...]:
        """Bind each declared dependency to its descriptor and admission hash."""

        if not descriptor.dependencies or not available_capabilities:
            return ()
        bindings: list[Mapping[str, str]] = []
        for dependency in descriptor.dependencies:
            admission = available_capabilities.get(dependency)
            if not self._capability_declaration_is_available(
                admission,
                expected_capability_id=dependency,
                registry=self.registry,
            ):
                continue
            try:
                dependency_descriptor = self.registry.get(dependency)
            except Exception:  # noqa: BLE001 - unresolved dependencies remain gated
                continue
            bindings.append(
                {
                    "capability_id": dependency,
                    "descriptor_version": dependency_descriptor.version,
                    "descriptor_hash": dependency_descriptor.content_hash,
                    "admission_hash": admission.admission_hash,
                }
            )
        return tuple(bindings)

    @staticmethod
    def _item(
        descriptor: CapabilityDescriptor,
        outcome: str,
        state: ComputationState,
        matching: Sequence[DataBlock] = (),
        selected: DataBlock | None = None,
        provider_results: Sequence[ProviderResultInput] = (),
        selected_provider_result: ProviderResultInput | None = None,
        dependency_bindings: Sequence[Mapping[str, Any]] = (),
    ) -> CapabilityPlanItem:
        item = CapabilityPlanItem(
            capability_id=descriptor.capability_id,
            descriptor_version=descriptor.version,
            descriptor_hash=descriptor.content_hash,
            outcome=outcome,
            state=state,
            data_block_ids=tuple(block.block_id for block in matching),
            selected_data_block_id=None if selected is None else selected.block_id,
            provider_result_ids=tuple(item.input_id for item in provider_results),
            selected_provider_result_id=(
                None
                if selected_provider_result is None
                else selected_provider_result.input_id
            ),
            next_actions=state.next_actions,
            calibration_hashes=(
                _calibration_hashes_for_block(selected, descriptor)
                if selected is not None
                else ()
            ),
            dependency_bindings=dependency_bindings,
        )
        # Keep issuance outside the public constructor.  This makes
        # ``dataclasses.replace`` lose authority (the init=False marker is not
        # copied) while the fingerprint also detects low-level mutation of a
        # previously issued object.
        object.__setattr__(item, "_admission_token", _ADMISSION_TOKEN)
        object.__setattr__(item, "_admission_fingerprint", canonical_json_hash(item.to_dict()))
        return item

    @staticmethod
    def _normalize_provider_results(
        provider_results: Sequence[ProviderResultInput | Mapping[str, Any]],
    ) -> tuple[ProviderResultInput, ...]:
        if isinstance(provider_results, (ProviderResultInput, Mapping)):
            provider_results = (provider_results,)
        if isinstance(provider_results, (str, bytes, bytearray)) or not isinstance(
            provider_results, Sequence
        ):
            raise TypeError("Capability planner provider_results must be a sequence")
        normalized: list[ProviderResultInput] = []
        for value in provider_results:
            # Provider-result DTOs are an authorization/input boundary.  A
            # subclass can override derived properties (for example
            # ``available_metric_paths``) without changing its content hash,
            # so only the exact validated DTO type is trusted here.  Mapping
            # inputs are rehydrated through the exact base constructor below.
            if type(value) is ProviderResultInput:
                normalized.append(value)
            elif isinstance(value, ProviderResultInput):
                raise TypeError(
                    "Capability planner provider_results must contain exact ProviderResultInput values"
                )
            elif isinstance(value, Mapping):
                normalized.append(ProviderResultInput.from_dict(value))
            else:
                raise TypeError(
                    "Capability planner provider_results must contain ProviderResultInput values"
                )
        return tuple(normalized)

    @classmethod
    def _inspect_provider_result_descriptor(
        cls,
        descriptor: CapabilityDescriptor,
        provider_results: tuple[ProviderResultInput, ...],
        available_capabilities: tuple[str, ...] = (),
        *,
        dependency_bindings: Sequence[Mapping[str, Any]] = (),
    ) -> CapabilityPlanItem:
        matching = tuple(
            item for item in provider_results if item.technique in descriptor.techniques
        )
        if not matching:
            state = ComputationState.create(
                data_availability="missing" if not provider_results else "partial",
                computability="needs_input",
                validity="not_assessed",
                promotion="diagnostic_only",
                missing_inputs=("provider_result",),
                reason_codes=("provider_result_missing",),
                next_actions=("provide_provider_result",),
            )
            return cls._item(descriptor, "needs_input", state, provider_results=matching)

        declared_paths = tuple(
            str(path).strip()
            for path in descriptor.input_contract.get("metric_paths", ())
        )
        eligible: list[ProviderResultInput] = []
        for item in matching:
            state = item.computation_state
            if state is not None and state.computability != "computed":
                continue
            if set(declared_paths).intersection(item.available_metric_paths):
                eligible.append(item)
        if not eligible:
            label = "provider_metric:" + "|".join(declared_paths or ("value",))
            state = ComputationState.create(
                data_availability="partial",
                computability="needs_input",
                validity="not_assessed",
                promotion="diagnostic_only",
                missing_inputs=(label,),
                reason_codes=("provider_metric_unavailable",),
                next_actions=("provide_provider_metric",),
            )
            return cls._item(descriptor, "needs_input", state, provider_results=matching)

        missing_dependencies = tuple(
            f"dependency:{dependency}"
            for dependency in descriptor.dependencies
            if dependency not in set(available_capabilities)
        )
        if missing_dependencies:
            state = ComputationState.create(
                data_availability="canonical",
                computability="needs_input",
                validity="not_assessed",
                promotion="diagnostic_only",
                missing_inputs=missing_dependencies,
                reason_codes=("capability_dependency_missing",),
                next_actions=tuple(
                    f"compute_dependency:{dependency}"
                    for dependency in descriptor.dependencies
                    if dependency not in set(available_capabilities)
                ),
            )
            return cls._item(
                descriptor,
                "needs_input",
                state,
                provider_results=matching,
                selected_provider_result=eligible[0],
                dependency_bindings=dependency_bindings,
            )

        selected = eligible[0]
        state = ComputationState.create(
            data_availability="canonical",
            computability="computed",
            validity="not_assessed",
            promotion="diagnostic_only",
            next_actions=descriptor.missing_input_actions,
        )
        return cls._item(
            descriptor,
            "executable",
            state,
            provider_results=matching,
            selected_provider_result=selected,
            dependency_bindings=dependency_bindings,
        )

    @staticmethod
    def _required_inputs(contract: Mapping[str, Any]) -> tuple[str, ...]:
        required = contract.get("required_inputs", ())
        if isinstance(required, str):
            required = (required,)
        return _dedupe(required)

    @staticmethod
    def _required_any_inputs(contract: Mapping[str, Any]) -> tuple[tuple[str, ...], ...]:
        groups = contract.get("required_any_inputs", ())
        if isinstance(groups, (str, bytes, bytearray)) or not isinstance(groups, Sequence):
            return ()
        normalized: list[tuple[str, ...]] = []
        for group in groups:
            if isinstance(group, (str, bytes, bytearray)) or not isinstance(group, Sequence):
                continue
            values = _dedupe(tuple(group))
            if values:
                normalized.append(values)
        return tuple(normalized)

    @classmethod
    def _required_input_labels(cls, contract: Mapping[str, Any]) -> tuple[str, ...]:
        labels = list(cls._required_inputs(contract))
        labels.extend(
            "one_of:" + "|".join(group)
            for group in cls._required_any_inputs(contract)
        )
        return _dedupe(labels)

    @classmethod
    def _planner_available_inputs(
        cls,
        *,
        available_inputs: Mapping[str, Any] | None,
        input_declarations: Mapping[str, Any] | None,
        context: Mapping[str, Any] | None,
    ) -> tuple[str, ...]:
        names: list[str] = []
        if available_inputs is not None:
            names.extend(cls._available_names(available_inputs, "available_inputs"))
        if input_declarations is not None:
            names.extend(cls._available_names(input_declarations, "input_declarations"))
        if context is not None:
            names.extend(cls._context_available_names(context, "context"))
        return _dedupe(names)

    @classmethod
    def _block_available_inputs(cls, block: DataBlock) -> tuple[str, ...]:
        metadata = block.metadata if isinstance(block.metadata, Mapping) else {}
        names: list[str] = []
        for key in ("available_inputs", "input_declarations"):
            if key in metadata:
                names.extend(cls._available_names(metadata[key], f"DataBlock.metadata.{key}"))
        if "context" in metadata:
            names.extend(cls._context_available_names(metadata["context"], "DataBlock.metadata.context"))
        return _dedupe(names)

    @classmethod
    def _context_available_names(cls, value: Any, label: str) -> tuple[str, ...]:
        if not isinstance(value, Mapping):
            raise TypeError(f"{label} must be a mapping")
        canonical_json_hash(value)
        names: list[str] = []
        namespaced = False
        for key in ("available_inputs", "input_declarations"):
            if key in value:
                namespaced = True
                names.extend(cls._available_names(value[key], f"{label}.{key}"))
        if not namespaced:
            names.extend(cls._available_names(value, label))
        return _dedupe(names)

    @staticmethod
    def _available_names(value: Any, label: str) -> tuple[str, ...]:
        if not isinstance(value, Mapping):
            raise TypeError(f"{label} must be a mapping")
        canonical_json_hash(value)
        names: list[str] = []
        for name, declaration in value.items():
            if not isinstance(name, str) or not name.strip():
                raise TypeError(f"{label} keys must be nonempty strings")
            if CapabilityPlanner._declaration_is_available(declaration):
                names.append(name.strip())
        return _dedupe(names)

    def _available_capability_names(self, value: Any) -> tuple[str, ...]:
        """Return only capabilities with an explicitly completed state.

        Capability dependencies are execution inputs, not merely planned or
        discoverable nodes.  A dependency declaration is therefore accepted
        only when it is the exact, in-process ``CapabilityPlanItem`` issued by
        this Core planner.  JSON status dictionaries and booleans are useful
        for ordinary input hints, but they are not execution attestations.
        """

        if not isinstance(value, Mapping):
            raise TypeError("available_capabilities must be a mapping")
        names: list[str] = []
        for name, declaration in value.items():
            if not isinstance(name, str) or not name.strip():
                raise TypeError("available_capabilities keys must be nonempty strings")
            if self._capability_declaration_is_available(
                declaration,
                expected_capability_id=name.strip(),
                registry=self.registry,
            ):
                names.append(name.strip())
        return _dedupe(names)

    @staticmethod
    def _capability_declaration_is_available(
        value: Any,
        *,
        expected_capability_id: str | None = None,
        registry: CapabilityDescriptorRegistry | None = None,
    ) -> bool:
        """Validate a Core-issued dependency admission without polymorphism."""

        # Keep this exact-type check aligned with ExecutionGraph's admission
        # boundary.  A subclass can override derived properties or authority
        # checks while retaining the same serialized fields.
        if type(value) is not CapabilityPlanItem:
            return False
        try:
            if not value.is_trusted_admission:
                return False
            if (
                expected_capability_id is not None
                and value.capability_id != expected_capability_id
            ):
                return False
            if registry is not None:
                try:
                    descriptor = registry.get(value.capability_id)
                except Exception:  # noqa: BLE001 - unknown/malformed registry fails closed
                    return False
                if (
                    descriptor.capability_id != value.capability_id
                    or descriptor.version != value.descriptor_version
                    or descriptor.content_hash != value.descriptor_hash
                ):
                    return False
            return value.outcome == "executable" and value.state.computability == "computed"
        except Exception:  # noqa: BLE001 - malformed declarations fail closed
            return False

    @staticmethod
    def _declaration_is_available(value: Any) -> bool:
        """Interpret only explicit declarations, never similarly named metadata."""

        if value is None:
            return False
        if type(value) is bool:
            return value
        if isinstance(value, Mapping):
            if "available" in value:
                available = value["available"]
                if type(available) is not bool:
                    raise TypeError("Input declaration available must be a boolean")
                return available
            if "status" in value:
                status = value["status"]
                if not isinstance(status, str):
                    raise TypeError("Input declaration status must be a string")
                normalized = status.strip().lower()
                if normalized in {
                    "available",
                    "provided",
                    "ready",
                    "observed",
                    "calibrated",
                    "computed",
                    "completed",
                }:
                    return True
                if normalized in {"missing", "unavailable", "unknown", "blocked", "invalid"}:
                    return False
                return False
            return "value" in value and value["value"] is not None
        if isinstance(value, str):
            return value.strip().lower() not in {"", "missing", "unavailable", "unknown"}
        if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
            return len(value) > 0
        return True

    @staticmethod
    def _matches_input_contract(block: DataBlock, contract: Mapping[str, Any], descriptor: CapabilityDescriptor) -> bool:
        kinds = contract.get("kinds", contract.get("kind"))
        if kinds is not None:
            if isinstance(kinds, str):
                kinds = (kinds,)
            accepted_kinds = {str(value) for value in kinds}
            if block.kind not in accepted_kinds:
                # A small compatibility escape hatch is retained for the
                # original ``curve.*`` descriptors.  Older persisted blocks
                # sometimes carry only a technique label (no family or
                # representation) even though they originated from a
                # one-dimensional Measurement.  They may still be discovered
                # through the legacy route, but explicitly labelled N-D
                # blocks must satisfy the strict series contract.
                metadata = block.metadata if isinstance(block.metadata, Mapping) else {}
                legacy_curve = (
                    descriptor.capability_id.startswith("curve.")
                    and block.kind in {"matrix", "cube", "complex"}
                    and isinstance(metadata.get("technique"), str)
                    and "measurement_family" not in metadata
                )
                if not legacy_curve:
                    return False
        required_dims = contract.get("required_dims", contract.get("required_dimensions", ()))
        if isinstance(required_dims, str):
            required_dims = (required_dims,)
        if required_dims and not set(str(value) for value in required_dims).issubset(set(block.dims)):
            return False
        metadata = block.metadata if isinstance(block.metadata, Mapping) else {}
        families = contract.get("measurement_families", contract.get("families"))
        if families is not None:
            if isinstance(families, str):
                families = (families,)
            declared_family = metadata.get("measurement_family", metadata.get("family"))
            # A constrained descriptor cannot safely match an unlabelled
            # block.  The two original ``curve.*`` descriptors predate the
            # family metadata field and remain a narrow compatibility
            # exception; all N-D and user-defined descriptors fail closed.
            if declared_family is None and not descriptor.capability_id.startswith("curve."):
                return False
            if declared_family is not None and (
                not isinstance(declared_family, str)
                or not declared_family.strip()
                or str(declared_family) not in {str(value) for value in families}
            ):
                return False
        metadata_technique = metadata.get("technique")
        contract_techniques = contract.get("techniques")
        accepted_techniques = set(descriptor.techniques)
        if contract_techniques is not None:
            if isinstance(contract_techniques, str):
                contract_techniques = (contract_techniques,)
            accepted_techniques = {normalize_technique(value) for value in contract_techniques}
        if metadata_technique is None or not isinstance(metadata_technique, str) or not metadata_technique.strip():
            # Technique provenance is never inferred from shape.  A caller
            # can intentionally use a descriptor with no technique namespace,
            # but every registered descriptor has one, so an unlabelled block
            # is not a match.
            return False
        if normalize_technique(metadata_technique) not in accepted_techniques:
            return False
        return True

    @classmethod
    def _evaluate_gates(
        cls,
        block: DataBlock,
        descriptor: CapabilityDescriptor,
        declared_inputs: Sequence[str] = (),
        available_capabilities: Sequence[str] = (),
    ) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
        blocked: list[str] = []
        missing: list[str] = []
        actions: list[str] = []
        contract = descriptor.input_contract
        available_capability_set = set(available_capabilities)
        for dependency in descriptor.dependencies:
            if dependency not in available_capability_set:
                missing.append(f"dependency:{dependency}")
                actions.append(f"compute_dependency:{dependency}")
        available_inputs = set(_dedupe(tuple(declared_inputs) + cls._block_available_inputs(block)))
        for required_input in cls._required_inputs(contract):
            if required_input not in available_inputs:
                missing.append(required_input)
                actions.append(f"provide_input:{required_input}")
        for group in cls._required_any_inputs(contract):
            if not available_inputs.intersection(group):
                label = "one_of:" + "|".join(group)
                missing.append(label)
                actions.append("provide_" + label)
        axis_requirements = contract.get("axis_requirements", {})
        if not isinstance(axis_requirements, Mapping):
            axis_requirements = {}
        quantitative_axes = contract.get("quantitative_axes", ())
        if isinstance(quantitative_axes, str):
            quantitative_axes = (quantitative_axes,)
        required_axes = contract.get("required_axes", ())
        if isinstance(required_axes, str):
            required_axes = (required_axes,)
        for axis_name in _dedupe(tuple(axis_requirements) + tuple(quantitative_axes) + tuple(required_axes)):
            axis = block.axis_provenance.get(axis_name) if block.axis_provenance else None
            requirement = axis_requirements.get(axis_name, {})
            if isinstance(requirement, str):
                requirement = {"accepted_sources": (requirement,)}
            if not isinstance(requirement, Mapping):
                requirement = {}
            if axis is None:
                if axis_name in required_axes or axis_name in quantitative_axes or requirement.get("required", True):
                    missing.append(f"axis:{axis_name}")
                    actions.append(f"provide_axis:{axis_name}")
                continue
            accepted_sources = requirement.get("accepted_sources", requirement.get("sources"))
            if isinstance(accepted_sources, str):
                accepted_sources = (accepted_sources,)
            if accepted_sources and axis.source not in {str(value) for value in accepted_sources}:
                blocked.append(f"axis_provenance_not_accepted:{axis_name}")
                continue
            quantitative = bool(requirement.get("quantitative", axis_name in quantitative_axes))
            if quantitative and not axis_allows_quantitative(axis):
                blocked.append(f"axis_provenance_not_accepted:{axis_name}")
            expected_units = requirement.get("unit", requirement.get("units"))
            if expected_units is not None:
                if isinstance(expected_units, str):
                    expected_units = (expected_units,)
                actual_units = {
                    str(value).strip()
                    for value in expected_units
                    if isinstance(value, str) and value.strip()
                }
                coordinate_unit = block.coord_units.get(axis_name)
                provenance_unit = axis.unit
                if (
                    not actual_units
                    or coordinate_unit not in actual_units
                    or provenance_unit not in actual_units
                    or coordinate_unit != provenance_unit
                ):
                    blocked.append(f"axis_unit_mismatch:{axis_name}")
            elif axis.unit is not None and block.coord_units.get(axis_name) is not None:
                if axis.unit != block.coord_units.get(axis_name):
                    blocked.append(f"axis_unit_provenance_mismatch:{axis_name}")
            expected_quantities = requirement.get(
                "quantity", requirement.get("quantities")
            )
            if expected_quantities is not None:
                if isinstance(expected_quantities, str):
                    expected_quantities = (expected_quantities,)
                accepted_quantities = {
                    str(value).strip()
                    for value in expected_quantities
                    if isinstance(value, str) and value.strip()
                }
                if axis.quantity not in accepted_quantities:
                    blocked.append(f"axis_quantity_mismatch:{axis_name}")
            coordinates = block.coords.get(axis_name)
            if requirement.get("unique") is True and coordinates is not None:
                if len({repr(value) for value in coordinates}) != len(coordinates):
                    blocked.append(f"axis_not_unique:{axis_name}")
            if requirement.get("monotonic") is True and coordinates is not None:
                numeric = tuple(
                    value
                    for value in coordinates
                    if isinstance(value, Real) and not isinstance(value, bool)
                )
                if len(numeric) != len(coordinates) or not _is_monotonic(numeric):
                    blocked.append(f"axis_not_monotonic:{axis_name}")

        shape_requirements = contract.get("shape_requirements", {})
        if isinstance(shape_requirements, Mapping):
            rank = shape_requirements.get("rank")
            if rank is not None and len(block.shape) != rank:
                blocked.append("shape_rank_mismatch")
            dimensions = shape_requirements.get("dimensions", {})
            if isinstance(dimensions, Mapping):
                for dimension, requirement in dimensions.items():
                    if dimension not in block.dims or not isinstance(requirement, Mapping):
                        blocked.append(f"shape_dimension_mismatch:{dimension}")
                        continue
                    size = block.shape[block.dims.index(dimension)]
                    exact = requirement.get("exact_size")
                    minimum = requirement.get("min_size")
                    maximum = requirement.get("max_size")
                    if exact is not None and size != exact:
                        blocked.append(f"shape_dimension_mismatch:{dimension}")
                    elif minimum is not None and size < minimum:
                        blocked.append(f"shape_dimension_too_short:{dimension}")
                    elif maximum is not None and size > maximum:
                        blocked.append(f"shape_dimension_too_long:{dimension}")

        policy = descriptor.evidence_policy
        require_reviewed_calibration = (
            isinstance(policy, Mapping)
            and policy.get("requires_reviewed_calibration") is True
        )
        for calibration in _calibration_requirements(contract):
            calibration_name = cls._calibration_name(calibration)
            gate = cls._calibration_gate(
                block,
                calibration_name,
                require_reviewed=require_reviewed_calibration,
            )
            if gate == "unreviewed":
                blocked.append(f"calibration_not_reviewed:{calibration_name}")
                actions.append(f"review_calibration:{calibration_name}")
            elif gate == "missing":
                missing.append(f"calibration:{calibration_name}")
                actions.append(f"provide_calibration:{calibration_name}")

        for precondition in descriptor.preconditions:
            cls._evaluate_precondition(
                block,
                precondition,
                blocked,
                missing,
                actions,
                require_reviewed_calibration=require_reviewed_calibration,
            )
        return _dedupe(blocked), _dedupe(missing), _dedupe(actions)

    @staticmethod
    def _calibration_name(value: Any) -> str:
        if isinstance(value, Mapping):
            # ``id`` is the compact identity accepted by the descriptor
            # contract.  Keep the lookup order explicit so a malformed
            # mapping can never silently disappear from the calibration gate.
            value = value.get(
                "name",
                value.get(
                    "scope",
                    value.get("calibration_id", value.get("id", "")),
                ),
            )
        return str(value).strip()

    @staticmethod
    def _calibration_gate(
        block: DataBlock,
        name: str,
        *,
        require_reviewed: bool = False,
    ) -> str:
        """Return available, unreviewed, or missing for one calibration identity."""

        if not name:
            return "missing"
        wanted = name.casefold()
        unreviewed_match = False
        metadata = block.metadata if isinstance(block.metadata, Mapping) else {}
        for key in ("calibrations", "calibration_refs", "calibration_ids"):
            values = metadata.get(key, ())
            if isinstance(values, Mapping):
                values = tuple(values.values()) + tuple(values.keys())
            elif isinstance(values, str):
                values = (values,)
            for value in values or ():
                if isinstance(value, Mapping):
                    status = str(value.get("status", "")).strip().lower()
                    if status not in {"reviewed", "applied_unreviewed"}:
                        continue
                    # A structured reference must carry a locator/hash pair
                    # when supplied; this prevents a name-only pseudo-ref from
                    # satisfying a quantitative calibration gate.
                    locator = value.get("record_locator", value.get("uri"))
                    digest = value.get("record_sha256", value.get("sha256"))
                    if locator is None or digest is None:
                        continue
                    if (
                        not isinstance(locator, str)
                        or not locator
                        or not isinstance(digest, str)
                        or not re.fullmatch(r"[0-9a-fA-F]{64}", digest)
                    ):
                        continue
                    candidates = (value.get("name"), value.get("scope"), value.get("calibration_id"), value.get("id"))
                else:
                    # Bare IDs are declarations, not validated calibration
                    # records, and therefore cannot satisfy a quantitative gate.
                    continue
                if any(
                    str(candidate).casefold() == wanted
                    for candidate in candidates
                    if candidate is not None
                ):
                    if status == "reviewed" or not require_reviewed:
                        return "available"
                    unreviewed_match = True
        for axis in (block.axis_provenance or {}).values():
            calibration = axis.calibration_ref
            if calibration is None:
                continue
            if any(str(candidate).casefold() == wanted for candidate in (calibration.calibration_id, calibration.scope)):
                if calibration.status == "reviewed" or (
                    calibration.status == "applied_unreviewed"
                    and not require_reviewed
                ):
                    return "available"
                if calibration.status == "applied_unreviewed":
                    unreviewed_match = True
        return "unreviewed" if unreviewed_match else "missing"

    @staticmethod
    def _has_calibration(
        block: DataBlock,
        name: str,
        *,
        require_reviewed: bool = False,
    ) -> bool:
        return (
            CapabilityPlanner._calibration_gate(
                block,
                name,
                require_reviewed=require_reviewed,
            )
            == "available"
        )

    @staticmethod
    def _evaluate_precondition(
        block: DataBlock,
        precondition: Mapping[str, Any],
        blocked: list[str],
        missing: list[str],
        actions: list[str],
        *,
        require_reviewed_calibration: bool = False,
    ) -> None:
        kind = str(precondition.get("kind", precondition.get("type", ""))).strip()
        if kind in {"axis_provenance", "axis"}:
            axis_name = str(precondition.get("axis", "")).strip()
            axis = block.axis_provenance.get(axis_name) if block.axis_provenance else None
            if axis is None:
                missing.append(f"axis:{axis_name}")
                actions.append(f"provide_axis:{axis_name}")
                return
            accepted = precondition.get("accepted_sources", precondition.get("sources"))
            if isinstance(accepted, str):
                accepted = (accepted,)
            if accepted and axis.source not in {str(value) for value in accepted}:
                blocked.append(f"axis_provenance_not_accepted:{axis_name}")
        elif kind == "calibration":
            name = CapabilityPlanner._calibration_name(precondition)
            gate = CapabilityPlanner._calibration_gate(
                block,
                name,
                require_reviewed=require_reviewed_calibration,
            )
            if gate == "unreviewed":
                blocked.append(f"calibration_not_reviewed:{name}")
                actions.append(f"review_calibration:{name}")
            elif gate == "missing":
                missing.append(f"calibration:{name}")
                actions.append(f"provide_calibration:{name}")


# ``CapabilityAdmission`` is a descriptive public alias.  Keeping one DTO for
# discovery and execution prevents AI/GUI adapters from inventing a second
# private authorization representation.
CapabilityAdmission = CapabilityPlanItem
PlannerAdmission = CapabilityPlanItem


__all__ = [
    "PLAN_OUTCOMES",
    "CapabilityPlanItem",
    "CapabilityAdmission",
    "PlannerAdmission",
    "CapabilityPlanner",
]
