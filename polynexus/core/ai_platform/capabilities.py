"""Versioned, technique-neutral capability descriptors and discovery registry.

The legacy canonical capability registries deliberately stay finite and
calculator-oriented.  This module adds the contract needed by AI callers:
inputs, gates, outputs, uncertainty policy, and an honest execution status.
Legacy provider ids remain aliases, while descriptor ids are namespaced and
versioned where a provider id is ambiguous.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from .contracts import canonical_json_hash


TECHNIQUE_ALIASES = {
    "ftir": "ir",
    "infrared": "ir",
    "fourier_transform_infrared": "ir",
    "saxs2d": "saxs",
    "waxs2d": "waxs",
    "sec/gpc": "sec",
    "gpc": "sec",
}


def normalize_technique(value: object) -> str:
    """Normalize a technique/provider alias to one descriptor namespace."""

    normalized = str(value).strip().lower()
    return TECHNIQUE_ALIASES.get(normalized, normalized)


def _safe(value: Any) -> Any:
    """Return a JSON-safe mutable representation for public serialization."""

    if isinstance(value, Mapping):
        return {str(key): _safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_safe(item) for item in value]
    return value


def _freeze(value: Any) -> Any:
    """Freeze descriptor payloads after canonical JSON validation."""

    # canonical_json_hash performs the finite-number and key validation used
    # by all AI-platform contracts.  It is intentionally called before
    # converting mappings so invalid payloads fail at descriptor creation.
    canonical_json_hash(value)
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(item) for item in value)
    return value


def _strings(values: Sequence[object], *, normalize: bool = False) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
        raise TypeError("Capability descriptor string fields must be sequences")
    result: list[str] = []
    for value in values:
        if not isinstance(value, str):
            raise TypeError("Capability descriptor string fields must contain strings")
        item = normalize_technique(value) if normalize else value.strip()
        if not item:
            raise ValueError("Capability descriptor string fields must not be empty")
        if item not in result:
            result.append(item)
    return tuple(result)


def _mapping_sequence(values: Sequence[Mapping[str, Any] | str], label: str) -> tuple[Any, ...]:
    if isinstance(values, (str, bytes, bytearray)):
        raise TypeError(f"Capability descriptor {label} must be a sequence")
    result: list[Any] = []
    for value in values:
        if isinstance(value, Mapping):
            result.append(_freeze(value))
        elif isinstance(value, str) and value.strip():
            result.append(value.strip())
        else:
            raise TypeError(f"Capability descriptor {label} entries must be mappings or strings")
    return tuple(result)


# ``CapabilityDescriptor`` is a public boundary.  Keep the input vocabulary
# finite so a typo cannot silently turn a constrained capability into an
# unconstrained one in ``CapabilityPlanner``.  The paired names below are
# retained for compatibility with the older capability registries.
_INPUT_CONTRACT_KEYS = frozenset(
    {
        "kind",
        "kinds",
        "required_dims",
        "required_dimensions",
        "measurement_families",
        "families",
        "techniques",
        "required_inputs",
        "required_any_inputs",
        "axis_requirements",
        "quantitative_axes",
        "required_axes",
        "required_calibrations",
        "metric_paths",
    }
)
_INPUT_CONTRACT_SEQUENCE_KEYS = frozenset(
    {
        "kind",
        "kinds",
        "required_dims",
        "required_dimensions",
        "measurement_families",
        "families",
        "techniques",
        "required_inputs",
        "quantitative_axes",
        "required_axes",
        "metric_paths",
    }
)
_INPUT_CONTRACT_ALIAS_PAIRS = (
    ("kind", "kinds"),
    ("required_dims", "required_dimensions"),
    ("measurement_families", "families"),
)
_AXIS_REQUIREMENT_KEYS = frozenset(
    {"accepted_sources", "sources", "quantitative", "required"}
)
_CALIBRATION_CONTRACT_KEYS = frozenset(
    {
        "name",
        "scope",
        "calibration_id",
        "id",
    }
)
_PRECONDITION_KINDS = frozenset({"axis", "axis_provenance", "calibration"})
_AXIS_PRECONDITION_KEYS = frozenset(
    {"kind", "type", "axis", "accepted_sources", "sources"}
)
_CALIBRATION_PRECONDITION_KEYS = frozenset(
    {"kind", "type", "name", "scope", "calibration_id", "id"}
)


def _sequence_tuple(values: Any, label: str) -> tuple[Any, ...]:
    """Materialize an explicitly declared sequence without splitting strings."""

    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
        raise TypeError(f"Capability descriptor {label} must be a sequence")
    return tuple(values)


def _contract_string_sequence(value: Any, label: str) -> tuple[str, ...]:
    """Validate one string-or-sequence input-contract field.

    Strings are accepted as a singleton because the planner has historically
    accepted both ``kind="series"`` and ``kinds=("series",)`` forms.  Sets,
    mappings, and arbitrary iterables are rejected to keep descriptor hashes
    deterministic and to avoid treating malformed values as no constraint.
    """

    if isinstance(value, str):
        values = (value,)
    elif isinstance(value, (bytes, bytearray)) or not isinstance(value, Sequence):
        raise TypeError(f"Capability descriptor input_contract {label} must be a string or sequence")
    else:
        values = tuple(value)
    normalized: list[str] = []
    for item in values:
        if not isinstance(item, str):
            raise TypeError(
                f"Capability descriptor input_contract {label} entries must be strings"
            )
        item = item.strip()
        if not item:
            raise ValueError(
                f"Capability descriptor input_contract {label} entries must not be empty"
            )
        normalized.append(item)
    if not normalized:
        raise ValueError(f"Capability descriptor input_contract {label} must not be empty")
    return tuple(normalized)


def _validate_calibration_requirements(value: Any) -> None:
    if isinstance(value, str):
        _contract_string_sequence(value, "required_calibrations")
        return
    if isinstance(value, (bytes, bytearray)) or not isinstance(value, Sequence):
        raise TypeError(
            "Capability descriptor input_contract required_calibrations must be a sequence"
        )
    if not value:
        raise ValueError(
            "Capability descriptor input_contract required_calibrations must not be empty"
        )
    for index, item in enumerate(value):
        label = f"required_calibrations[{index}]"
        if isinstance(item, str):
            _contract_string_sequence(item, label)
            continue
        if not isinstance(item, Mapping):
            raise TypeError(
                f"Capability descriptor input_contract {label} must be a string or mapping"
            )
        if any(not isinstance(key, str) for key in item):
            raise TypeError(f"Capability descriptor input_contract {label} keys must be strings")
        unknown = sorted(set(item) - _CALIBRATION_CONTRACT_KEYS)
        if unknown:
            raise ValueError(
                f"unknown input_contract calibration key(s): {', '.join(unknown)}"
            )
        identity_keys = ("name", "scope", "calibration_id", "id")
        present_identity_keys = tuple(key for key in identity_keys if key in item)
        if not present_identity_keys:
            raise ValueError(
                f"Capability descriptor input_contract {label} requires a calibration identity"
            )
        if len(present_identity_keys) > 1:
            raise ValueError(
                f"Capability descriptor input_contract {label} requires exactly one calibration identity"
            )
        for key in identity_keys:
            if key in item:
                _contract_string_sequence(item[key], f"{label}.{key}")


def _validate_axis_requirements(value: Any) -> None:
    if not isinstance(value, Mapping):
        raise TypeError(
            "Capability descriptor input_contract axis_requirements must be a mapping"
        )
    for axis_name, requirement in value.items():
        if not isinstance(axis_name, str) or not axis_name.strip():
            raise TypeError(
                "Capability descriptor input_contract axis_requirements keys must be nonempty strings"
            )
        label = f"axis_requirements[{axis_name!r}]"
        if isinstance(requirement, str):
            _contract_string_sequence(requirement, f"{label}.accepted_sources")
            continue
        if not isinstance(requirement, Mapping):
            raise TypeError(
                f"Capability descriptor input_contract {label} must be a string or mapping"
            )
        if any(not isinstance(key, str) for key in requirement):
            raise TypeError(f"Capability descriptor input_contract {label} keys must be strings")
        unknown = sorted(set(requirement) - _AXIS_REQUIREMENT_KEYS)
        if unknown:
            raise ValueError(
                f"unknown input_contract axis requirement key(s): {', '.join(unknown)}"
            )
        for left, right in (("accepted_sources", "sources"),):
            if left in requirement and right in requirement:
                raise ValueError(
                    f"Capability descriptor input_contract {label} declares both "
                    f"{left} and {right}"
                )
        for key in ("accepted_sources", "sources"):
            if key in requirement:
                _contract_string_sequence(requirement[key], f"{label}.{key}")
        for key in ("quantitative", "required"):
            if key in requirement and type(requirement[key]) is not bool:
                raise TypeError(
                    f"Capability descriptor input_contract {label}.{key} must be a boolean"
                )


def _validate_required_any_inputs(value: Any) -> None:
    """Validate groups where each group requires at least one available input."""

    if (
        isinstance(value, (str, bytes, bytearray, Mapping))
        or not isinstance(value, Sequence)
    ):
        raise TypeError(
            "Capability descriptor input_contract required_any_inputs must be a "
            "sequence of string groups"
        )
    if not value:
        raise ValueError(
            "Capability descriptor input_contract required_any_inputs must not be empty"
        )
    for index, group in enumerate(value):
        label = f"required_any_inputs[{index}]"
        if (
            isinstance(group, (str, bytes, bytearray, Mapping))
            or not isinstance(group, Sequence)
        ):
            raise TypeError(
                f"Capability descriptor input_contract {label} must be a string sequence"
            )
        _contract_string_sequence(group, label)


def _validate_preconditions(values: Sequence[Mapping[str, Any]]) -> None:
    """Restrict preconditions to the gates implemented by the planner."""

    for index, precondition in enumerate(values):
        label = f"precondition[{index}]"
        if not isinstance(precondition, Mapping):
            raise TypeError(f"Capability descriptor {label} must be a mapping")
        if any(not isinstance(key, str) for key in precondition):
            raise TypeError(f"Capability descriptor {label} keys must be strings")
        if "kind" in precondition and "type" in precondition:
            raise ValueError(
                f"Capability descriptor {label} must declare kind or type, not both"
            )
        raw_kind = precondition.get("kind", precondition.get("type"))
        if not isinstance(raw_kind, str):
            raise TypeError(f"Capability descriptor {label} kind must be a string")
        kind = raw_kind.strip()
        if not kind:
            raise ValueError(f"Capability descriptor {label} kind must not be empty")
        if kind not in _PRECONDITION_KINDS:
            raise ValueError(f"Unsupported capability descriptor {label} kind: {kind}")

        if kind in {"axis", "axis_provenance"}:
            unknown = sorted(set(precondition) - _AXIS_PRECONDITION_KEYS)
            if unknown:
                raise ValueError(
                    f"unknown capability descriptor {label} key(s): {', '.join(unknown)}"
                )
            axis = precondition.get("axis")
            if not isinstance(axis, str) or not axis.strip():
                raise ValueError(
                    f"Capability descriptor {label} axis must be a nonempty string"
                )
            if "accepted_sources" in precondition and "sources" in precondition:
                raise ValueError(
                    f"Capability descriptor {label} declares both accepted_sources and sources"
                )
            for key in ("accepted_sources", "sources"):
                if key in precondition:
                    _contract_string_sequence(precondition[key], f"{label}.{key}")
            continue

        unknown = sorted(set(precondition) - _CALIBRATION_PRECONDITION_KEYS)
        if unknown:
            raise ValueError(
                f"unknown capability descriptor {label} key(s): {', '.join(unknown)}"
            )
        identity_keys = tuple(
            key for key in ("name", "scope", "calibration_id", "id") if key in precondition
        )
        if len(identity_keys) != 1:
            raise ValueError(
                f"Capability descriptor {label} requires exactly one calibration identity"
            )
        identity = identity_keys[0]
        _contract_string_sequence(precondition[identity], f"{label}.{identity}")


def _validate_input_contract(value: Any) -> None:
    """Fail closed on unknown keys and malformed planner-facing fields."""

    if not isinstance(value, Mapping):
        raise TypeError("Capability descriptor input_contract must be a mapping")
    if any(not isinstance(key, str) for key in value):
        raise TypeError("Capability descriptor input_contract keys must be strings")
    unknown = sorted(set(value) - _INPUT_CONTRACT_KEYS)
    if unknown:
        raise ValueError(
            f"unknown input_contract key(s): {', '.join(unknown)}"
        )
    for key in _INPUT_CONTRACT_SEQUENCE_KEYS:
        if key in value:
            _contract_string_sequence(value[key], key)
    if "axis_requirements" in value:
        _validate_axis_requirements(value["axis_requirements"])
    if "required_calibrations" in value:
        _validate_calibration_requirements(value["required_calibrations"])
    if "required_any_inputs" in value:
        _validate_required_any_inputs(value["required_any_inputs"])
    for left, right in _INPUT_CONTRACT_ALIAS_PAIRS:
        if left in value and right in value:
            raise ValueError(
                f"Capability descriptor input_contract declares both {left} and {right}"
            )


@dataclass(frozen=True)
class CapabilityDescriptor:
    """Public contract for one discoverable polymer computation capability."""

    capability_id: str
    version: str = "1"
    techniques: tuple[str, ...] = field(default_factory=tuple)
    input_contract: Mapping[str, Any] = field(default_factory=dict)
    output_schema: Mapping[str, Any] = field(default_factory=dict)
    preconditions: tuple[Mapping[str, Any], ...] = ()
    dependencies: tuple[str, ...] = ()
    alternatives: tuple[str, ...] = ()
    uncertainty_policy: Mapping[str, Any] = field(default_factory=dict)
    status: str = "available"
    executor_key: str | None = None
    missing_input_actions: tuple[Mapping[str, Any] | str, ...] = ()
    evidence_policy: Mapping[str, Any] = field(default_factory=dict)
    cost: Mapping[str, Any] = field(default_factory=dict)
    failure_reason_codes: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    schema_version: str = "1"

    STATUSES = frozenset({"available", "experimental", "unsupported", "deprecated", "needs_input"})

    def __post_init__(self) -> None:
        capability_id = str(self.capability_id).strip()
        version = str(self.version).strip()
        if not capability_id:
            raise ValueError("Capability descriptor id must not be empty")
        if not version:
            raise ValueError("Capability descriptor version must not be empty")
        if self.schema_version != "1":
            raise ValueError(f"Unsupported capability descriptor schema_version: {self.schema_version}")
        if self.status not in self.STATUSES:
            raise ValueError(f"Unsupported capability descriptor status: {self.status}")
        if isinstance(self.techniques, (str, bytes, bytearray)):
            raise TypeError("Capability descriptor techniques must be a sequence")
        techniques = _strings(self.techniques, normalize=True)
        if not techniques:
            raise ValueError("Capability descriptor requires at least one technique")
        if not isinstance(self.input_contract, Mapping):
            raise TypeError("Capability descriptor input_contract must be a mapping")
        _validate_input_contract(self.input_contract)
        if not isinstance(self.output_schema, Mapping):
            raise TypeError("Capability descriptor output_schema must be a mapping")
        if not isinstance(self.uncertainty_policy, Mapping):
            raise TypeError("Capability descriptor uncertainty_policy must be a mapping")
        if not isinstance(self.evidence_policy, Mapping):
            raise TypeError("Capability descriptor evidence_policy must be a mapping")
        if not isinstance(self.cost, Mapping):
            raise TypeError("Capability descriptor cost must be a mapping")
        preconditions = _mapping_sequence(self.preconditions, "preconditions")
        if any(not isinstance(value, Mapping) for value in preconditions):
            raise TypeError("Capability descriptor preconditions must contain mappings")
        _validate_preconditions(preconditions)
        dependencies = _strings(self.dependencies)
        alternatives = _strings(self.alternatives)
        failure_codes = _strings(self.failure_reason_codes)
        aliases = _strings(self.aliases)
        executor_key = None if self.executor_key is None else str(self.executor_key).strip()
        if executor_key == "":
            raise ValueError("Capability descriptor executor_key must not be empty")
        if self.status == "unsupported" and executor_key is not None:
            raise ValueError("Unsupported capability descriptors cannot declare an executor")
        object.__setattr__(self, "capability_id", capability_id)
        object.__setattr__(self, "version", version)
        object.__setattr__(self, "schema_version", str(self.schema_version))
        object.__setattr__(self, "techniques", techniques)
        object.__setattr__(self, "input_contract", _freeze(self.input_contract))
        object.__setattr__(self, "output_schema", _freeze(self.output_schema))
        object.__setattr__(self, "preconditions", preconditions)
        object.__setattr__(self, "dependencies", dependencies)
        object.__setattr__(self, "alternatives", alternatives)
        object.__setattr__(self, "uncertainty_policy", _freeze(self.uncertainty_policy))
        object.__setattr__(self, "executor_key", executor_key)
        object.__setattr__(self, "missing_input_actions", _mapping_sequence(self.missing_input_actions, "missing_input_actions"))
        object.__setattr__(self, "evidence_policy", _freeze(self.evidence_policy))
        object.__setattr__(self, "cost", _freeze(self.cost))
        object.__setattr__(self, "failure_reason_codes", failure_codes)
        object.__setattr__(self, "aliases", aliases)

    @classmethod
    def create(
        cls,
        *,
        capability_id: str,
        techniques: Sequence[str],
        input_contract: Mapping[str, Any],
        output_schema: Mapping[str, Any],
        version: str | None = None,
        preconditions: Sequence[Mapping[str, Any]] = (),
        dependencies: Sequence[str] = (),
        alternatives: Sequence[str] = (),
        uncertainty_policy: Mapping[str, Any] | None = None,
        status: str = "available",
        executor_key: str | None = None,
        missing_input_actions: Sequence[Mapping[str, Any] | str] = (),
        evidence_policy: Mapping[str, Any] | None = None,
        cost: Mapping[str, Any] | None = None,
        failure_reason_codes: Sequence[str] = (),
        aliases: Sequence[str] = (),
        schema_version: str = "1",
    ) -> "CapabilityDescriptor":
        resolved_version = "1" if version is None else str(version)
        # IDs conventionally carry their version.  Keep an explicitly supplied
        # version authoritative, but derive a useful default for legacy ids.
        if version is None and ".v" in str(capability_id):
            suffix = str(capability_id).rsplit(".v", 1)[-1]
            if suffix.isdigit():
                resolved_version = suffix
        return cls(
            capability_id=str(capability_id),
            version=resolved_version,
            techniques=_sequence_tuple(techniques, "techniques"),
            input_contract=input_contract,
            output_schema=output_schema,
            preconditions=_sequence_tuple(preconditions, "preconditions"),
            dependencies=_sequence_tuple(dependencies, "dependencies"),
            alternatives=_sequence_tuple(alternatives, "alternatives"),
            uncertainty_policy={} if uncertainty_policy is None else uncertainty_policy,
            status=status,
            executor_key=executor_key,
            missing_input_actions=_sequence_tuple(
                missing_input_actions, "missing_input_actions"
            ),
            evidence_policy={} if evidence_policy is None else evidence_policy,
            cost={} if cost is None else cost,
            failure_reason_codes=_sequence_tuple(
                failure_reason_codes, "failure_reason_codes"
            ),
            aliases=_sequence_tuple(aliases, "aliases"),
            schema_version=schema_version,
        )

    @property
    def content_hash(self) -> str:
        return canonical_json_hash(self._identity_payload())

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "capability_id": self.capability_id,
            "version": self.version,
            "techniques": list(self.techniques),
            "input_contract": _safe(self.input_contract),
            "output_schema": _safe(self.output_schema),
            "preconditions": [_safe(value) for value in self.preconditions],
            "dependencies": list(self.dependencies),
            "alternatives": list(self.alternatives),
            "uncertainty_policy": _safe(self.uncertainty_policy),
            "status": self.status,
            "executor_key": self.executor_key,
            "missing_input_actions": [_safe(value) for value in self.missing_input_actions],
            "evidence_policy": _safe(self.evidence_policy),
            "cost": _safe(self.cost),
            "failure_reason_codes": list(self.failure_reason_codes),
            "aliases": list(self.aliases),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._identity_payload(), "content_hash": self.content_hash}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CapabilityDescriptor":
        if not isinstance(value, Mapping):
            raise TypeError("Capability descriptor must be a mapping")
        descriptor = cls.create(
            capability_id=value["capability_id"],
            version=value.get("version", "1"),
            techniques=value["techniques"],
            input_contract=value.get("input_contract", {}),
            output_schema=value.get("output_schema", {}),
            preconditions=value.get("preconditions", ()),
            dependencies=value.get("dependencies", ()),
            alternatives=value.get("alternatives", ()),
            uncertainty_policy=value.get("uncertainty_policy", {}),
            status=value.get("status", "available"),
            executor_key=value.get("executor_key"),
            missing_input_actions=value.get("missing_input_actions", ()),
            evidence_policy=value.get("evidence_policy", {}),
            cost=value.get("cost", {}),
            failure_reason_codes=value.get("failure_reason_codes", ()),
            aliases=value.get("aliases", ()),
            schema_version=value.get("schema_version", "1"),
        )
        expected = value.get("content_hash")
        if expected is not None and expected != descriptor.content_hash:
            raise ValueError("Capability descriptor content_hash does not match its content")
        return descriptor


class CapabilityDescriptorRegistry:
    """Immutable lookup registry with canonical technique and legacy aliases."""

    def __init__(self, descriptors: Sequence[CapabilityDescriptor]) -> None:
        selected = tuple(descriptors)
        if not all(isinstance(item, CapabilityDescriptor) for item in selected):
            raise TypeError("Capability descriptor registry entries must be CapabilityDescriptor values")
        ids = tuple(item.capability_id for item in selected)
        if len(set(ids)) != len(ids):
            raise ValueError("Capability descriptor ids must be unique")
        id_set = set(ids)
        for descriptor in selected:
            for alias in descriptor.aliases:
                if alias in id_set and alias != descriptor.capability_id:
                    raise ValueError(f"Capability descriptor alias conflicts with canonical id: {alias}")
        self._descriptors = selected
        self._by_id = {item.capability_id: item for item in selected}
        alias_candidates: dict[tuple[str | None, str], list[CapabilityDescriptor]] = {}
        for descriptor in selected:
            names = (descriptor.capability_id, *descriptor.aliases)
            for name in names:
                for technique in (*descriptor.techniques, None):
                    key = (technique, str(name))
                    candidates = alias_candidates.setdefault(key, [])
                    if descriptor not in candidates:
                        candidates.append(descriptor)
        # Ambiguous short aliases are intentionally omitted from the global
        # namespace; a caller must supply the technique in that case.
        self._aliases = {
            key: candidates[0]
            for key, candidates in alias_candidates.items()
            if len(candidates) == 1
        }

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(item.capability_id for item in self._descriptors)

    @property
    def descriptors(self) -> tuple[CapabilityDescriptor, ...]:
        return self._descriptors

    def get(self, capability_id: str, *, technique: str | None = None) -> CapabilityDescriptor:
        requested = str(capability_id).strip()
        if technique is not None:
            descriptor = self._aliases.get((normalize_technique(technique), requested))
        else:
            descriptor = self._by_id.get(requested) or self._aliases.get((None, requested))
        if descriptor is None:
            raise ValueError(f"Unknown capability: {requested}")
        return descriptor

    def resolve(self, capability_ids: Sequence[str] | None = None) -> tuple[CapabilityDescriptor, ...]:
        if capability_ids is None:
            return self._descriptors
        if isinstance(capability_ids, (str, bytes, bytearray)):
            capability_ids = (str(capability_ids),)
        return tuple(self.get(value) for value in capability_ids)

    def for_technique(self, technique: str) -> tuple[CapabilityDescriptor, ...]:
        normalized = normalize_technique(technique)
        return tuple(item for item in self._descriptors if normalized in item.techniques)

    def to_dict(self) -> dict[str, Any]:
        return {"descriptors": [item.to_dict() for item in self._descriptors]}


def descriptor_from_capability_spec(spec: Any) -> CapabilityDescriptor:
    """Adapt one legacy generic ``CapabilitySpec`` without changing execution."""

    return CapabilityDescriptor.create(
        capability_id=spec.capability_id,
        techniques=("ir", "saxs", "waxs", "nmr"),
        input_contract={
            # ``CapabilitySpec`` calculators accept the legacy
            # ``Measurement(x, intensity)`` view only.  Do not advertise
            # matrix/cube/complex blocks as executable merely because their
            # shape is compatible with a generic JSON envelope; N-D routes
            # have their own explicit descriptors below.
            "kinds": ("series",),
            "measurement_families": tuple(spec.measurement_families),
        },
        output_schema={"result": {"type": "mapping"}},
        status="available",
        executor_key=f"canonical.{spec.capability_id}",
        uncertainty_policy={"mode": "provider_or_unavailable"},
    )


def descriptor_from_provider_spec(spec: Any, *, technique: str | None = None) -> CapabilityDescriptor:
    """Adapt one legacy provider metric projection to a namespaced descriptor."""

    source_technique = normalize_technique(technique or spec.techniques[0])
    capability_id = f"{source_technique}.{spec.capability_id}.v1"
    return CapabilityDescriptor.create(
        capability_id=capability_id,
        techniques=(source_technique,),
        input_contract={
            "kind": "provider_result",
            "metric_paths": tuple(spec.metric_paths),
        },
        output_schema={"value": {"type": "scalar", "metric_paths": tuple(spec.metric_paths)}},
        status="available",
        executor_key="provider_result",
        aliases=(spec.capability_id,),
        uncertainty_policy={"mode": "provider_or_unavailable"},
    )


_UNSUPPORTED_CAPABILITIES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("dma.master_curve.v1", "dma", ("matrix", "series", "table")),
    ("dma.storage_modulus.v1", "dma", ("series", "table")),
    ("dma.loss_modulus.v1", "dma", ("series", "table")),
    ("dma.tan_delta.v1", "dma", ("series", "table")),
    ("dma.glass_transition.v1", "dma", ("series", "table")),
    ("dma.creep.v1", "dma", ("series", "table")),
    ("dma.relaxation.v1", "dma", ("series", "table")),
    ("rheology.viscosity.v1", "rheology", ("series", "table")),
    ("rheology.moduli.v1", "rheology", ("series", "table")),
    ("rheology.yield_stress.v1", "rheology", ("series", "table")),
    ("rheology.thixotropy.v1", "rheology", ("series", "table")),
    ("rheology.tts.v1", "rheology", ("matrix", "series", "table")),
    ("rheology.creep_recovery.v1", "rheology", ("series", "table")),
    ("rheology.stress_relaxation.v1", "rheology", ("series", "table")),
    ("tga.mass_loss_stages.v1", "tga", ("series", "table")),
    ("tga.dtg_peaks.v1", "tga", ("series", "table")),
    ("tga.residue.v1", "tga", ("series", "table")),
    ("tga.kinetics.v1", "tga", ("series", "table")),
    ("sec.molecular_weight.v1", "sec", ("series", "table")),
    ("sec.distribution.v1", "sec", ("series", "table")),
    ("mechanics.tensile.v1", "mechanics", ("series", "table")),
    ("mechanics.compression.v1", "mechanics", ("series", "table")),
    ("mechanics.flexural.v1", "mechanics", ("series", "table")),
    ("mechanics.impact.v1", "mechanics", ("series", "table")),
    ("mechanics.fatigue.v1", "mechanics", ("series", "table")),
    ("mechanics.fracture.v1", "mechanics", ("series", "table")),
    ("mechanics.creep.v1", "mechanics", ("series", "table")),
)


# N-D route descriptors describe contracts and gates only.  They are marked
# experimental until a registered deterministic provider is bound; the
# registry must never imply a scientific value merely because a source block
# has the right shape.  Keeping these declarations here lets AI capability
# discovery distinguish a missing provider/calibration from an unknown
# capability while preserving the old one-dimensional provider projections.
_NMR_SAMPLING_INPUTS = (
    "dwell_time",
    "sampling_interval",
    "spectral_width",
)
_NMR_PPM_REFERENCE_INPUTS = (
    "chemical_shift_calibration",
    "chemical_shift_reference",
    "ppm_reference",
)
_NMR_INDIRECT_AXIS_INPUTS = (
    "indirect_dwell_time",
    "indirect_sampling_interval",
    "indirect_spectral_width",
    "indirect_chemical_shift_calibration",
)


_ND_CAPABILITIES: tuple[dict[str, Any], ...] = (
    {
        "capability_id": "ir.temperature_matrix.v1",
        "techniques": ("ir",),
        "input_contract": {
            "kinds": ("matrix",),
            "required_dims": ("temperature", "wavenumber"),
            "measurement_families": ("spectrum_1d",),
            # A filename-derived temperature is useful for ordering and
            # visualization, but it is not a quantitative thermal axis.  The
            # capability therefore requires an observed/calibrated or
            # explicitly user-confirmed temperature provenance.
            "axis_requirements": {
                "temperature": {
                    "accepted_sources": ("observed", "calibrated", "user_confirmed"),
                    "quantitative": True,
                    "required": True,
                },
            },
        },
        "output_schema": {
            "matrix": {"type": "matrix", "dims": ("temperature", "wavenumber")},
            "temperature_axis": {"unit": "degC"},
            "wavenumber_axis": {"unit": "cm^-1"},
        },
        "status": "experimental",
        "executor_key": "canonical.ir.temperature_matrix",
        "aliases": ("ir.temperature_series.v1", "temperature_matrix"),
        "uncertainty_policy": {"mode": "provider_or_unavailable"},
        "evidence_policy": {"requires_axis_provenance": True},
    },
    {
        "capability_id": "ir.correlation_2d.v1",
        "techniques": ("ir",),
        "input_contract": {
            "kinds": ("matrix",),
            "required_dims": ("temperature", "wavenumber"),
            "measurement_families": ("spectrum_1d",),
            "axis_requirements": {
                "temperature": {
                    "accepted_sources": ("observed", "calibrated", "user_confirmed"),
                    "quantitative": True,
                    "required": True,
                },
            },
        },
        "output_schema": {
            "synchronous": {"type": "matrix", "dims": ("wavenumber", "wavenumber")},
            "asynchronous": {"type": "matrix", "dims": ("wavenumber", "wavenumber")},
        },
        "status": "experimental",
        "executor_key": "canonical.ir.correlation_2d",
        "aliases": ("ir.2d_correlation.v1", "correlation_2d"),
        "uncertainty_policy": {"mode": "provider_or_unavailable"},
        "evidence_policy": {"requires_axis_provenance": True},
    },
    {
        "capability_id": "saxs.detector_radial_profile.v1",
        "techniques": ("saxs",),
        "input_contract": {
            "kinds": ("matrix",),
            "required_dims": ("detector_y", "detector_x"),
            "measurement_families": ("detector_image",),
            "required_calibrations": ("saxs.detector_calibration",),
        },
        "output_schema": {
            "q": {"type": "series", "unit": "nm^-1"},
            "intensity": {"type": "series", "unit": "a.u."},
        },
        "status": "experimental",
        "executor_key": "canonical.saxs.detector_radial_profile",
        "aliases": ("saxs.radial_profile.v1", "radial_profile"),
        "uncertainty_policy": {"mode": "provider_or_unavailable"},
        "evidence_policy": {"requires_reviewed_calibration": True},
    },
    {
        "capability_id": "saxs.detector_azimuthal_profile.v1",
        "techniques": ("saxs",),
        "input_contract": {
            "kinds": ("matrix",),
            "required_dims": ("detector_y", "detector_x"),
            "measurement_families": ("detector_image",),
            "required_calibrations": ("saxs.detector_calibration",),
        },
        "output_schema": {
            "azimuth_deg": {"type": "series", "unit": "deg"},
            "intensity": {"type": "series", "unit": "a.u."},
        },
        "status": "experimental",
        "executor_key": "canonical.saxs.detector_azimuthal_profile",
        "aliases": ("saxs.azimuthal_profile.v1", "azimuthal_profile"),
        "uncertainty_policy": {"mode": "provider_or_unavailable"},
        "evidence_policy": {"requires_reviewed_calibration": True},
    },
    {
        "capability_id": "waxs.detector_radial_profile.v1",
        "techniques": ("waxs",),
        "input_contract": {
            "kinds": ("matrix",),
            "required_dims": ("detector_y", "detector_x"),
            "measurement_families": ("detector_image",),
            "required_calibrations": ("waxs.detector_calibration",),
        },
        "output_schema": {
            "two_theta": {"type": "series", "unit": "deg"},
            "intensity": {"type": "series", "unit": "a.u."},
        },
        "status": "experimental",
        "executor_key": "canonical.waxs.detector_radial_profile",
        "aliases": ("waxs.radial_profile.v1",),
        "uncertainty_policy": {"mode": "provider_or_unavailable"},
        "evidence_policy": {"requires_reviewed_calibration": True},
    },
    {
        "capability_id": "nmr.fid_fft.v1",
        "techniques": ("nmr",),
        "input_contract": {
            "kinds": ("complex", "cube"),
            "required_dims": ("time",),
            "measurement_families": ("fid",),
            # A dwell/spectral-width declaration defines the sampled
            # frequency grid; a separate reference/calibration is required
            # before the public ppm axis in ``output_schema`` is honest.
            "required_any_inputs": (
                _NMR_SAMPLING_INPUTS,
                _NMR_PPM_REFERENCE_INPUTS,
            ),
        },
        "output_schema": {
            "spectrum": {"type": "series", "axis": "chemical_shift", "unit": "ppm"},
        },
        "status": "experimental",
        "executor_key": "canonical.nmr.fid_fft",
        "aliases": ("nmr.fft.v1", "fid_fft"),
        "uncertainty_policy": {"mode": "provider_or_unavailable"},
        "evidence_policy": {"requires_complex_input": True},
    },
    {
        "capability_id": "nmr.t1_from_fid.v1",
        "techniques": ("nmr",),
        "input_contract": {
            "kinds": ("complex", "cube"),
            "required_dims": ("time",),
            "measurement_families": ("fid",),
            "required_inputs": ("relaxation_delays",),
            "required_any_inputs": (_NMR_SAMPLING_INPUTS,),
        },
        "output_schema": {"T1": {"type": "scalar", "unit": "s"}},
        "status": "experimental",
        "executor_key": "canonical.nmr.t1_from_fid",
        "aliases": ("nmr.t1.v1", "fid_t1"),
        "uncertainty_policy": {"mode": "provider_or_unavailable"},
        "evidence_policy": {"requires_complex_input": True},
    },
    {
        "capability_id": "nmr.t2_from_fid.v1",
        "techniques": ("nmr",),
        "input_contract": {
            "kinds": ("complex", "cube"),
            "required_dims": ("time",),
            "measurement_families": ("fid",),
            "required_inputs": ("relaxation_delays",),
            "required_any_inputs": (_NMR_SAMPLING_INPUTS,),
        },
        "output_schema": {"T2": {"type": "scalar", "unit": "s"}},
        "status": "experimental",
        "executor_key": "canonical.nmr.t2_from_fid",
        "aliases": ("nmr.t2.v1", "fid_t2"),
        "uncertainty_policy": {"mode": "provider_or_unavailable"},
        "evidence_policy": {"requires_complex_input": True},
    },
    {
        "capability_id": "nmr.2d_fft.v1",
        "techniques": ("nmr",),
        "input_contract": {
            "kinds": ("complex", "cube"),
            "required_dims": ("time", "indirect_time"),
            "measurement_families": ("fid",),
            "required_any_inputs": (
                _NMR_SAMPLING_INPUTS,
                _NMR_INDIRECT_AXIS_INPUTS,
            ),
        },
        "output_schema": {"spectrum": {"type": "matrix", "unit": "a.u."}},
        "status": "experimental",
        "executor_key": "canonical.nmr.2d_fft",
        "aliases": ("nmr.2d_spectrum.v1", "fid_2d_fft"),
        "uncertainty_policy": {"mode": "provider_or_unavailable"},
        "evidence_policy": {"requires_complex_input": True},
    },
)


def _default_descriptors() -> tuple[CapabilityDescriptor, ...]:
    # Imports stay local so importing contracts does not trigger the legacy
    # engine registration side effects before a caller asks for the catalog.
    from ..canonical_experiments.capabilities import (
        default_capability_registry,
        default_provider_capability_registry,
    )

    descriptors: list[CapabilityDescriptor] = [
        descriptor_from_capability_spec(spec)
        for spec in default_capability_registry().resolve()
    ]
    provider_registry = default_provider_capability_registry()
    seen_provider: set[tuple[str, str]] = set()
    for source_technique in ("dsc", "ftir", "saxs", "waxs", "nmr"):
        for spec in provider_registry.for_technique(source_technique):
            canonical_technique = normalize_technique(source_technique)
            identity = (canonical_technique, spec.capability_id)
            if identity in seen_provider:
                continue
            seen_provider.add(identity)
            descriptors.append(descriptor_from_provider_spec(spec, technique=canonical_technique))
    for capability_id, technique, kinds in _UNSUPPORTED_CAPABILITIES:
        descriptors.append(
            CapabilityDescriptor.create(
                capability_id=capability_id,
                techniques=(technique,),
                input_contract={"kinds": kinds, "required_inputs": ("raw_data",)},
                output_schema={"status": "unavailable", "reason": "provider_not_registered"},
                status="unsupported",
                uncertainty_policy={"mode": "not_available"},
                missing_input_actions=("register_provider",),
            )
        )
    for specification in _ND_CAPABILITIES:
        descriptors.append(CapabilityDescriptor.create(**specification))
    return tuple(descriptors)


_DEFAULT_REGISTRY: CapabilityDescriptorRegistry | None = None


def default_descriptor_registry() -> CapabilityDescriptorRegistry:
    """Return the process-wide descriptor registry."""

    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = CapabilityDescriptorRegistry(_default_descriptors())
    return _DEFAULT_REGISTRY


__all__ = [
    "TECHNIQUE_ALIASES",
    "normalize_technique",
    "CapabilityDescriptor",
    "CapabilityDescriptorRegistry",
    "descriptor_from_capability_spec",
    "descriptor_from_provider_spec",
    "default_descriptor_registry",
]
