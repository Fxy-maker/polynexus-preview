"""Input-aware capability discovery for AI callers."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Mapping, Sequence

from .capabilities import CapabilityDescriptor, CapabilityDescriptorRegistry, default_descriptor_registry, normalize_technique
from .contracts import (
    ComputationState,
    DataBlock,
    _dedupe_actions,
    _dedupe as _dedupe_strings,
    axis_allows_quantitative,
    canonical_json_hash,
)


PLAN_OUTCOMES = frozenset({"executable", "blocked", "needs_input", "not_applicable"})


def _dedupe(values: Sequence[object]) -> tuple[str, ...]:
    return _dedupe_strings(values, "Capability planner values")


def _public(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _public(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_public(item) for item in value]
    return value


@dataclass(frozen=True)
class CapabilityPlanItem:
    """One immutable discovery result shared by AI, CLI, GUI and evidence."""

    capability_id: str
    descriptor_version: str
    outcome: str
    state: ComputationState
    data_block_ids: tuple[str, ...] = ()
    selected_data_block_id: str | None = None
    next_actions: tuple[str | Mapping[str, Any], ...] = ()
    descriptor_hash: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.outcome not in PLAN_OUTCOMES:
            raise ValueError(f"Unsupported capability plan outcome: {self.outcome}")
        if not isinstance(self.state, ComputationState):
            raise TypeError("Capability plan state must be a ComputationState")
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
        from .contracts import _freeze

        object.__setattr__(self, "metadata", _freeze(self.metadata))

    @property
    def status(self) -> str:
        """Compatibility alias for callers that use result-style status."""

        return self.outcome

    @property
    def computability(self) -> str:
        return self.state.computability

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
            "next_actions": list(self.next_actions),
            "metadata": _public(self.metadata),
        }


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
        executors: Mapping[str, Any] | None = None,
        executor_registry: Mapping[str, Any] | None = None,
        require_executor: bool = False,
    ) -> tuple[CapabilityPlanItem, ...]:
        """Return executable, blocked, needs-input and not-applicable plans."""

        if type(require_executor) is not bool:
            raise TypeError("require_executor must be a boolean")

        blocks = self._normalize_blocks(data_blocks)
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
        return self._item(descriptor, "executable", state, matching, selected)

    @staticmethod
    def _item(
        descriptor: CapabilityDescriptor,
        outcome: str,
        state: ComputationState,
        matching: Sequence[DataBlock] = (),
        selected: DataBlock | None = None,
    ) -> CapabilityPlanItem:
        return CapabilityPlanItem(
            capability_id=descriptor.capability_id,
            descriptor_version=descriptor.version,
            descriptor_hash=descriptor.content_hash,
            outcome=outcome,
            state=state,
            data_block_ids=tuple(block.block_id for block in matching),
            selected_data_block_id=None if selected is None else selected.block_id,
            next_actions=state.next_actions,
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
                if normalized in {"available", "provided", "ready", "observed", "calibrated"}:
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
    ) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
        blocked: list[str] = []
        missing: list[str] = []
        actions: list[str] = []
        contract = descriptor.input_contract
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

        for calibration in contract.get("required_calibrations", ()):
            calibration_name = cls._calibration_name(calibration)
            if calibration_name and not cls._has_calibration(block, calibration_name):
                missing.append(f"calibration:{calibration_name}")
                actions.append(f"provide_calibration:{calibration_name}")

        for precondition in descriptor.preconditions:
            cls._evaluate_precondition(block, precondition, blocked, missing, actions)
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
    def _has_calibration(block: DataBlock, name: str) -> bool:
        wanted = name.casefold()
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
                if any(str(candidate).casefold() == wanted for candidate in candidates if candidate is not None):
                    return True
        for axis in (block.axis_provenance or {}).values():
            calibration = axis.calibration_ref
            if calibration is None:
                continue
            if any(str(candidate).casefold() == wanted for candidate in (calibration.calibration_id, calibration.scope)):
                if calibration.status in {"reviewed", "applied_unreviewed"}:
                    return True
        return False

    @staticmethod
    def _evaluate_precondition(
        block: DataBlock,
        precondition: Mapping[str, Any],
        blocked: list[str],
        missing: list[str],
        actions: list[str],
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
            if name and not CapabilityPlanner._has_calibration(block, name):
                missing.append(f"calibration:{name}")
                actions.append(f"provide_calibration:{name}")


__all__ = ["PLAN_OUTCOMES", "CapabilityPlanItem", "CapabilityPlanner"]
