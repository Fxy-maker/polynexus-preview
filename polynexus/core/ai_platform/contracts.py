"""Immutable, JSON-safe contracts shared by AI and GUI entry points."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
from types import MappingProxyType
from typing import Any, Mapping, Sequence


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Contract values must be finite")
        return value
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("Contract mappings must use string keys")
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    raise TypeError(f"Contract JSON values do not support {type(value).__name__}")


def _freeze(value: Any) -> Any:
    safe = _json_safe(value)
    if isinstance(safe, dict):
        return MappingProxyType({key: _freeze(item) for key, item in safe.items()})
    if isinstance(safe, list):
        return tuple(_freeze(item) for item in safe)
    return safe


def _public(value: Any) -> Any:
    return _json_safe(value)


def _dedupe(values: Sequence[Any], label: str = "values") -> tuple[str, ...]:
    """Normalize a contract list without turning malformed input into IDs."""
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
        raise TypeError(f"{label} must be a sequence of nonempty strings")
    normalized: list[str] = []
    for value in values:
        if not isinstance(value, str):
            raise TypeError(f"{label} entries must be strings")
        if not value:
            raise ValueError(f"{label} entries must be nonempty")
        normalized.append(value)
    return tuple(sorted(set(normalized)))


def _dedupe_actions(values: Sequence[Any], label: str = "actions") -> tuple[Any, ...]:
    """Normalize string or structured JSON actions deterministically."""
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
        raise TypeError(f"{label} must be a sequence")
    normalized: list[Any] = []
    seen: set[str] = set()
    for value in values:
        if isinstance(value, str):
            if not value:
                raise ValueError(f"{label} entries must be nonempty")
            item = value
        elif isinstance(value, Mapping):
            item = _freeze(value)
        else:
            raise TypeError(f"{label} entries must be strings or mappings")
        identity = json.dumps(_public(item), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if identity not in seen:
            seen.add(identity)
            normalized.append(item)
    return tuple(normalized)


def canonical_json_hash(value: Any) -> str:
    """Return a deterministic SHA-256 digest of a JSON-safe value."""
    payload = json.dumps(_json_safe(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _sha256(value: Any, label: str) -> None:
    if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdefABCDEF" for char in value):
        raise ValueError(f"{label} must be a 64-character hexadecimal SHA-256")


def _artifact_ref(value: Mapping[str, Any], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    reference = _freeze(value)
    uri = reference.get("uri")
    if not isinstance(uri, str) or not uri:
        raise ValueError(f"{label} requires a nonempty string uri")
    _sha256(reference.get("sha256"), f"{label} sha256")
    return reference


class CapabilityResultStatus:
    """Stable status strings for technique-neutral capability results."""

    COMPLETED = "completed"
    NEEDS_INPUT = "needs_input"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"
    ALL = frozenset({COMPLETED, NEEDS_INPUT, FAILED, NOT_APPLICABLE})


@dataclass(frozen=True)
class MissingnessPolicy:
    """Typed declaration of how absent or unusable values are represented."""

    strategy: str
    sentinel: Any | None = None
    mask_semantics: str | None = None
    reason: str | None = None

    STRATEGIES = frozenset({"not_declared", "none", "mask", "nan", "sentinel", "explicit", "unknown"})

    def __post_init__(self) -> None:
        strategy = str(self.strategy)
        if strategy not in self.STRATEGIES:
            raise ValueError(f"Unsupported missingness strategy: {strategy}")
        object.__setattr__(self, "strategy", strategy)
        if strategy == "sentinel" and self.sentinel is None:
            raise ValueError("Sentinel missingness requires a sentinel value")
        if self.sentinel is not None:
            object.__setattr__(self, "sentinel", _freeze(self.sentinel))
        for name in ("mask_semantics", "reason"):
            value = getattr(self, name)
            if value is not None:
                if not isinstance(value, str) or not value:
                    raise ValueError(f"Missingness {name} must be a nonempty string")
                object.__setattr__(self, name, value)

    @classmethod
    def create(
        cls,
        strategy: str,
        sentinel: Any | None = None,
        mask_semantics: str | None = None,
        reason: str | None = None,
    ) -> "MissingnessPolicy":
        return cls(strategy, sentinel, mask_semantics, reason)

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "sentinel": _public(self.sentinel),
            "mask_semantics": self.mask_semantics,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MissingnessPolicy":
        if not isinstance(value, Mapping):
            raise TypeError("Missingness policy must be a mapping")
        return cls.create(
            value["strategy"],
            value.get("sentinel"),
            value.get("mask_semantics"),
            value.get("reason"),
        )


@dataclass(frozen=True)
class CalibrationRef:
    calibration_id: str
    scope: str
    method: str
    source: str
    status: str
    parameters: Mapping[str, Any] = field(default_factory=dict)
    record_locator: str | None = None
    record_sha256: str | None = None

    STATUSES = frozenset({"reviewed", "applied_unreviewed", "not_applied", "missing"})

    def __post_init__(self) -> None:
        for name in ("calibration_id", "scope", "method", "source", "status"):
            value = str(getattr(self, name))
            if not value:
                raise ValueError(f"Calibration {name} must be nonempty")
            object.__setattr__(self, name, value)
        if self.status not in self.STATUSES:
            raise ValueError(f"Unsupported calibration status: {self.status}")
        if not isinstance(self.parameters, Mapping):
            raise TypeError("Calibration parameters must be a mapping")
        object.__setattr__(self, "parameters", _freeze(self.parameters))
        if (self.record_locator is None) != (self.record_sha256 is None):
            raise ValueError("Calibration record_locator and record_sha256 must be supplied together")
        if self.record_locator is not None:
            if not isinstance(self.record_locator, str) or not self.record_locator:
                raise ValueError("Calibration record_locator must be a nonempty string")
        if self.record_sha256 is not None:
            _sha256(self.record_sha256, "Calibration record_sha256")
        if self.status == "reviewed" and self.record_locator is None:
            raise ValueError("Reviewed calibration requires a record locator and hash")

    @classmethod
    def create(cls, calibration_id: str, scope: str, method: str, source: str, status: str, parameters: Mapping[str, Any] | None = None, record_locator: str | None = None, record_sha256: str | None = None) -> "CalibrationRef":
        return cls(calibration_id, scope, method, source, status, {} if parameters is None else parameters, record_locator, record_sha256)

    def to_dict(self) -> dict[str, Any]:
        return {"calibration_id": self.calibration_id, "scope": self.scope, "method": self.method, "source": self.source, "status": self.status, "parameters": _public(self.parameters), "record_locator": self.record_locator, "record_sha256": self.record_sha256}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CalibrationRef":
        if not isinstance(value, Mapping):
            raise TypeError("Calibration reference must be a mapping")
        return cls.create(value["calibration_id"], value["scope"], value["method"], value["source"], value["status"], value.get("parameters", {}), value.get("record_locator"), value.get("record_sha256"))


@dataclass(frozen=True)
class UncertaintyRef:
    kind: str
    value_ref: Mapping[str, Any] | None = None
    inline: Mapping[str, Any] | None = None

    KINDS = frozenset({"std", "stderr", "ci", "covariance", "distribution", "unknown"})

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", str(self.kind))
        if self.kind not in self.KINDS:
            raise ValueError(f"Unsupported uncertainty kind: {self.kind}")
        if self.value_ref is not None:
            object.__setattr__(self, "value_ref", _artifact_ref(self.value_ref, "Uncertainty value_ref"))
        if self.inline is not None:
            if not isinstance(self.inline, Mapping):
                raise TypeError("Uncertainty inline must be a mapping")
            object.__setattr__(self, "inline", _freeze(self.inline))
        provided = int(self.value_ref is not None) + int(self.inline is not None)
        if provided > 1:
            raise ValueError("Uncertainty requires exactly one of value_ref or inline summary")
        if provided == 0 and self.kind != "unknown":
            raise ValueError("Uncertainty requires exactly one of value_ref or inline summary")

    @classmethod
    def create(cls, kind: str, value_ref: Mapping[str, Any] | None = None, inline: Mapping[str, Any] | None = None, summary: Mapping[str, Any] | None = None) -> "UncertaintyRef":
        if inline is None:
            inline = summary
        return cls(kind, value_ref, inline)

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "value_ref": _public(self.value_ref), "inline": _public(self.inline)}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "UncertaintyRef":
        if not isinstance(value, Mapping):
            raise TypeError("Uncertainty reference must be a mapping")
        return cls.create(value["kind"], value.get("value_ref"), value.get("inline"), value.get("summary"))


@dataclass(frozen=True)
class AxisProvenance:
    name: str
    source: str
    method: str
    quantity: str | None = None
    unit: str | None = None
    status: str | None = None
    calibration_ref: CalibrationRef | Mapping[str, Any] | None = None
    uncertainty: UncertaintyRef | Mapping[str, Any] | None = None
    reason_codes: tuple[str, ...] = ()
    source_locator: Mapping[str, Any] | None = None
    transform_chain: tuple[Mapping[str, Any], ...] = ()
    accepts_quantitative: bool = field(init=False)

    SOURCES = frozenset({"observed", "calibrated", "inferred", "user_confirmed", "synthetic"})
    STATUSES = frozenset({"verified", "declared", "inferred", "assumed", "unresolved"})

    def __post_init__(self) -> None:
        for name in ("name", "source", "method"):
            value = str(getattr(self, name))
            if not value:
                raise ValueError(f"Axis {name} must be nonempty")
            object.__setattr__(self, name, value)
        if self.source not in self.SOURCES:
            raise ValueError(f"Unsupported axis source: {self.source}")
        defaults = {"observed": "verified", "calibrated": "verified", "user_confirmed": "declared", "inferred": "inferred", "synthetic": "assumed"}
        status = defaults[self.source] if self.status is None else str(self.status)
        if status not in self.STATUSES:
            raise ValueError(f"Unsupported axis status: {status}")
        object.__setattr__(self, "status", status)
        for name in ("quantity", "unit"):
            value = getattr(self, name)
            object.__setattr__(self, name, None if value is None else str(value))
        if isinstance(self.calibration_ref, Mapping):
            object.__setattr__(self, "calibration_ref", CalibrationRef.from_dict(self.calibration_ref))
        elif self.calibration_ref is not None and not isinstance(self.calibration_ref, CalibrationRef):
            raise TypeError("Axis calibration_ref must be a CalibrationRef or mapping")
        if self.source == "calibrated":
            if self.calibration_ref is None or self.calibration_ref.status not in {"reviewed", "applied_unreviewed"}:
                raise ValueError("Calibrated axis requires reviewed or applied_unreviewed calibration")
        if isinstance(self.uncertainty, Mapping):
            object.__setattr__(self, "uncertainty", UncertaintyRef.from_dict(self.uncertainty))
        elif self.uncertainty is not None and not isinstance(self.uncertainty, UncertaintyRef):
            raise TypeError("Axis uncertainty must be an UncertaintyRef or mapping")
        object.__setattr__(self, "reason_codes", _dedupe(self.reason_codes, "Axis reason_codes"))
        if self.source_locator is not None:
            if not isinstance(self.source_locator, Mapping):
                raise TypeError("Axis source_locator must be a mapping")
            object.__setattr__(self, "source_locator", _freeze(self.source_locator))
        if isinstance(self.transform_chain, (str, bytes, bytearray)) or not isinstance(self.transform_chain, Sequence):
            raise TypeError("Axis transform_chain must be a sequence of mappings")
        transforms: list[Mapping[str, Any]] = []
        for transform in self.transform_chain:
            if not isinstance(transform, Mapping):
                raise TypeError("Axis transform_chain entries must be mappings")
            if not isinstance(transform.get("method"), str) or not transform["method"]:
                raise ValueError("Axis transforms require a nonempty method")
            parameters = transform.get("parameters", {})
            if not isinstance(parameters, Mapping):
                raise TypeError("Axis transform parameters must be a mapping")
            normalized = dict(transform)
            normalized["method"] = transform["method"]
            normalized["parameters"] = parameters
            transforms.append(_freeze(normalized))
        object.__setattr__(self, "transform_chain", tuple(transforms))
        object.__setattr__(self, "accepts_quantitative", self.source not in {"synthetic", "inferred"} and status not in {"assumed", "inferred"})

    @classmethod
    def create(cls, name: str, source: str, method: str, quantity: str | None = None, unit: str | None = None, status: str | None = None, calibration_ref: CalibrationRef | Mapping[str, Any] | None = None, uncertainty: UncertaintyRef | Mapping[str, Any] | None = None, reason_codes: Sequence[str] = (), source_locator: Mapping[str, Any] | None = None, transform_chain: Sequence[Mapping[str, Any]] = ()) -> "AxisProvenance":
        return cls(name, source, method, quantity, unit, status, calibration_ref, uncertainty, reason_codes, source_locator, transform_chain)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "source": self.source, "method": self.method, "quantity": self.quantity, "unit": self.unit, "status": self.status, "calibration_ref": None if self.calibration_ref is None else self.calibration_ref.to_dict(), "uncertainty": None if self.uncertainty is None else self.uncertainty.to_dict(), "reason_codes": list(self.reason_codes), "source_locator": _public(self.source_locator), "transform_chain": _public(self.transform_chain)}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AxisProvenance":
        if not isinstance(value, Mapping):
            raise TypeError("Axis provenance must be a mapping")
        return cls.create(value["name"], value["source"], value["method"], value.get("quantity"), value.get("unit"), value.get("status"), value.get("calibration_ref"), value.get("uncertainty"), value.get("reason_codes", ()), value.get("source_locator"), value.get("transform_chain", ()))


def axis_allows_quantitative(axis: AxisProvenance | Mapping[str, Any]) -> bool:
    if isinstance(axis, Mapping):
        axis = AxisProvenance.from_dict(axis)
    if not isinstance(axis, AxisProvenance):
        raise TypeError("axis_allows_quantitative expects AxisProvenance")
    return axis.accepts_quantitative


@dataclass(frozen=True)
class DataBlock:
    block_id: str
    schema_version: str
    kind: str
    shape: tuple[int, ...]
    dims: tuple[str, ...]
    coords: Mapping[str, Any]
    coord_units: Mapping[str, str]
    array_ref: Mapping[str, Any]
    mask_ref: Mapping[str, Any] | None = None
    uncertainty_ref: UncertaintyRef | Mapping[str, Any] | None = None
    axis_provenance: Mapping[str, AxisProvenance | Mapping[str, Any]] | None = None
    source_artifact_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    missingness: MissingnessPolicy | Mapping[str, Any] | None = None
    quality_flags: tuple[str, ...] = ()
    non_physical_dims: tuple[str, ...] = ()

    KINDS = frozenset({"scalar", "series", "matrix", "cube", "complex", "table", "event"})
    SCHEMA_VERSION = "1"

    def __post_init__(self) -> None:
        if self.schema_version != self.SCHEMA_VERSION:
            raise ValueError(f"Unsupported data block schema_version: {self.schema_version}")
        object.__setattr__(self, "kind", str(self.kind))
        if self.kind not in self.KINDS:
            raise ValueError(f"Unsupported data block kind: {self.kind}")
        if isinstance(self.shape, (str, bytes, bytearray)) or not isinstance(self.shape, Sequence):
            raise ValueError("Data block shape must be a sequence")
        shape = tuple(self.shape)
        if any(type(item) is not int or item < 0 for item in shape):
            raise ValueError("Data block shape must contain nonnegative integers")
        if isinstance(self.dims, (str, bytes, bytearray)) or not isinstance(self.dims, Sequence):
            raise TypeError("Data block dims must be a sequence of strings")
        if any(not isinstance(dim, str) for dim in self.dims):
            raise TypeError("Data block dims must contain strings")
        dims = tuple(self.dims)
        if len(shape) != len(dims):
            raise ValueError("Data block shape length must equal dims length")
        if any(not dim for dim in dims) or len(set(dims)) != len(dims):
            raise ValueError("Data block dims must be unique and nonempty")
        expected_dimensions = {
            "scalar": 0,
            "series": 1,
            "matrix": 2,
            "cube": None,
        }
        expected_rank = expected_dimensions.get(self.kind)
        if expected_rank is not None and len(shape) != expected_rank:
            raise ValueError(f"Data block kind {self.kind} requires rank {expected_rank}")
        if self.kind == "cube" and len(shape) < 3:
            raise ValueError("Data block kind cube requires rank >= 3")
        if self.kind in {"table", "event", "complex"} and not shape and self.kind != "event":
            raise ValueError(f"Data block kind {self.kind} requires at least one dimension")
        object.__setattr__(self, "shape", shape)
        object.__setattr__(self, "dims", dims)
        if not isinstance(self.coords, Mapping) or not isinstance(self.coord_units, Mapping):
            raise TypeError("Data block coords and coord_units must be mappings")
        allowed = set(dims)
        if any(not isinstance(key, str) for key in self.coords) or any(not isinstance(key, str) for key in self.coord_units):
            raise TypeError("Data block coordinate mappings must use string keys")
        if not set(self.coords).issubset(allowed) or not set(self.coord_units).issubset(allowed):
            raise ValueError("Data block coordinate keys must match dims")
        if isinstance(self.non_physical_dims, (str, bytes, bytearray)) or not isinstance(self.non_physical_dims, Sequence):
            raise TypeError("Data block non_physical_dims must be a sequence of strings")
        if any(not isinstance(dim, str) for dim in self.non_physical_dims):
            raise TypeError("Data block non_physical_dims must contain strings")
        non_physical_dims = _dedupe(self.non_physical_dims, "Data block non_physical_dims")
        if not set(non_physical_dims).issubset(allowed):
            raise ValueError("Data block non_physical_dims must match dims")
        physical_dims = allowed.difference(non_physical_dims)
        if not physical_dims.issubset(set(self.coords)):
            raise ValueError("A coordinate is required for every physical dimension")
        normalized_coords = {}
        for dim, value in self.coords.items():
            if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
                raise ValueError(f"Data block coordinate for {dim} must be a sequence")
            if len(value) != shape[dims.index(dim)]:
                raise ValueError(f"coordinate length for {dim} must match shape")
            normalized_coords[dim] = _freeze(tuple(value))
        object.__setattr__(self, "coords", MappingProxyType(normalized_coords))
        units = {}
        for key, value in self.coord_units.items():
            if not isinstance(value, str) or not value:
                raise ValueError("Data block coordinate units must be nonempty strings")
            units[key] = value
        object.__setattr__(self, "coord_units", MappingProxyType(units))
        object.__setattr__(self, "array_ref", _artifact_ref(self.array_ref, "Data block array_ref"))
        if self.mask_ref is not None:
            object.__setattr__(self, "mask_ref", _artifact_ref(self.mask_ref, "Data block mask_ref"))
        if isinstance(self.uncertainty_ref, Mapping):
            object.__setattr__(self, "uncertainty_ref", UncertaintyRef.from_dict(self.uncertainty_ref))
        elif self.uncertainty_ref is not None and not isinstance(self.uncertainty_ref, UncertaintyRef):
            raise TypeError("Data block uncertainty_ref must be an UncertaintyRef or mapping")
        if self.axis_provenance is not None:
            if not isinstance(self.axis_provenance, Mapping) or not set(self.axis_provenance).issubset(allowed):
                raise ValueError("Data block axis_provenance keys must match dims")
            axes = {}
            for key, axis in self.axis_provenance.items():
                axes[str(key)] = axis if isinstance(axis, AxisProvenance) else AxisProvenance.from_dict(axis)
                if axes[str(key)].name != str(key):
                    raise ValueError("Data block axis provenance name must match its dimension key")
            object.__setattr__(self, "axis_provenance", MappingProxyType(axes))
        coord_keys = set(self.coords)
        if not coord_keys.issubset(set(self.coord_units)):
            raise ValueError("Data block coord_units are required for every coordinate key")
        if physical_dims and (self.axis_provenance is None or not physical_dims.issubset(set(self.axis_provenance))):
            raise ValueError("Data block axis provenance is required for every physical dimension")
        object.__setattr__(self, "non_physical_dims", non_physical_dims)
        if self.source_artifact_id is not None:
            if not isinstance(self.source_artifact_id, str) or not self.source_artifact_id:
                raise ValueError("Data block source_artifact_id must be a nonempty string")
        if not isinstance(self.metadata, Mapping):
            raise TypeError("Data block metadata must be a mapping")
        object.__setattr__(self, "metadata", _freeze(self.metadata))
        if self.missingness is None:
            missingness = MissingnessPolicy.create("not_declared")
        elif isinstance(self.missingness, Mapping):
            missingness = MissingnessPolicy.from_dict(self.missingness)
        elif isinstance(self.missingness, MissingnessPolicy):
            missingness = self.missingness
        else:
            raise TypeError("Data block missingness must be a MissingnessPolicy or mapping")
        if missingness.strategy == "mask" and self.mask_ref is None:
            raise ValueError("Mask missingness requires mask_ref")
        object.__setattr__(self, "missingness", missingness)
        object.__setattr__(self, "quality_flags", _dedupe(self.quality_flags, "Data block quality_flags"))
        expected = canonical_json_hash(self._identity_payload())
        _sha256(self.block_id, "Data block block_id")
        if self.block_id != expected:
            raise ValueError("Data block hash does not match its content")

    @classmethod
    def create(cls, kind: str, shape: Sequence[int], dims: Sequence[str], coords: Mapping[str, Any], coord_units: Mapping[str, str], array_ref: Mapping[str, Any], mask_ref: Mapping[str, Any] | None = None, uncertainty_ref: UncertaintyRef | Mapping[str, Any] | None = None, axis_provenance: Mapping[str, AxisProvenance | Mapping[str, Any]] | None = None, source_artifact_id: str | None = None, metadata: Mapping[str, Any] | None = None, missingness: MissingnessPolicy | Mapping[str, Any] | None = None, quality_flags: Sequence[str] = (), non_physical_dims: Sequence[str] = ()) -> "DataBlock":
        if isinstance(shape, (str, bytes, bytearray)) or not isinstance(shape, Sequence):
            raise ValueError("Data block shape must be a sequence")
        normalized_shape = tuple(shape)
        if any(type(item) is not int or item < 0 for item in normalized_shape):
            raise ValueError("Data block shape must contain nonnegative integers")
        if isinstance(dims, (str, bytes, bytearray)) or not isinstance(dims, Sequence):
            raise TypeError("Data block dims must be a sequence of strings")
        if any(not isinstance(dim, str) for dim in dims):
            raise TypeError("Data block dims must contain strings")
        normalized_dims = tuple(dims)
        if isinstance(coord_units, Mapping) and any(not isinstance(value, str) or not value for value in coord_units.values()):
            raise ValueError("Data block coordinate units must be nonempty strings")
        normalized_coords = {} if coords is None else dict(coords)
        if not isinstance(coords, Mapping):
            raise TypeError("Data block coords and coord_units must be mappings")
        for dim, values in normalized_coords.items():
            if not isinstance(dim, str):
                raise TypeError("Data block coordinate mappings must use string keys")
            if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
                raise ValueError(f"Data block coordinate for {dim} must be a sequence")
        normalized_axes = None if axis_provenance is None else {
            key: value if isinstance(value, AxisProvenance) else AxisProvenance.from_dict(value)
            for key, value in axis_provenance.items()
        }
        normalized_missingness = MissingnessPolicy.create("not_declared") if missingness is None else (missingness if isinstance(missingness, MissingnessPolicy) else MissingnessPolicy.from_dict(missingness))
        normalized_quality_flags = _dedupe(quality_flags, "Data block quality_flags")
        normalized_non_physical = _dedupe(non_physical_dims, "Data block non_physical_dims")
        payload = cls._identity_payload_static(cls.SCHEMA_VERSION, kind, normalized_shape, normalized_dims, normalized_coords, coord_units, array_ref, mask_ref, uncertainty_ref, normalized_axes, source_artifact_id, metadata or {}, normalized_missingness, normalized_quality_flags, normalized_non_physical)
        return cls(canonical_json_hash(payload), cls.SCHEMA_VERSION, kind, normalized_shape, normalized_dims, normalized_coords, coord_units, array_ref, mask_ref, uncertainty_ref, normalized_axes, source_artifact_id, metadata or {}, normalized_missingness, normalized_quality_flags, normalized_non_physical)

    @staticmethod
    def _identity_payload_static(schema_version: str, kind: str, shape: Sequence[int], dims: Sequence[str], coords: Mapping[str, Any], coord_units: Mapping[str, str], array_ref: Mapping[str, Any], mask_ref: Mapping[str, Any] | None, uncertainty_ref: Any, axis_provenance: Any, source_artifact_id: str | None, metadata: Mapping[str, Any], missingness: Any = None, quality_flags: Sequence[str] = (), non_physical_dims: Sequence[str] = ()) -> dict[str, Any]:
        return {"schema_version": schema_version, "kind": str(kind), "shape": list(shape), "dims": list(dims), "coords": _public(coords), "coord_units": _public(coord_units), "array_ref": _public(array_ref), "mask_ref": _public(mask_ref), "uncertainty_ref": None if uncertainty_ref is None else (uncertainty_ref.to_dict() if hasattr(uncertainty_ref, "to_dict") else _public(uncertainty_ref)), "axis_provenance": None if axis_provenance is None else {str(k): (v.to_dict() if hasattr(v, "to_dict") else _public(v)) for k, v in axis_provenance.items()}, "source_artifact_id": source_artifact_id, "metadata": _public(metadata), "missingness": None if missingness is None else (missingness.to_dict() if hasattr(missingness, "to_dict") else _public(missingness)), "quality_flags": list(quality_flags), "non_physical_dims": list(non_physical_dims)}

    def _identity_payload(self) -> dict[str, Any]:
        return self._identity_payload_static(self.schema_version, self.kind, self.shape, self.dims, self.coords, self.coord_units, self.array_ref, self.mask_ref, self.uncertainty_ref, self.axis_provenance, self.source_artifact_id, self.metadata, self.missingness, self.quality_flags, self.non_physical_dims)

    @property
    def content_hash(self) -> str:
        """Alias for the content-addressed block identifier."""
        return self.block_id

    def to_dict(self) -> dict[str, Any]:
        return {**self._identity_payload(), "block_id": self.block_id}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DataBlock":
        if not isinstance(value, Mapping):
            raise TypeError("Data block must be a mapping")
        if value.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("Unsupported or missing data block schema_version")
        missingness = value.get("missingness")
        if missingness is None:
            missingness = MissingnessPolicy.create("not_declared")
        expected_payload = cls._identity_payload_static(
            value["schema_version"], value["kind"], value["shape"], value["dims"],
            value.get("coords", {}), value.get("coord_units", {}), value["array_ref"],
            value.get("mask_ref"), value.get("uncertainty_ref"), value.get("axis_provenance"),
            value.get("source_artifact_id"), value.get("metadata", {}), missingness,
            value.get("quality_flags", ()), value.get("non_physical_dims", ()),
        )
        if value.get("block_id") != canonical_json_hash(expected_payload):
            raise ValueError("Data block hash does not match its content")
        block = cls.create(value["kind"], value["shape"], value["dims"], value.get("coords", {}), value.get("coord_units", {}), value["array_ref"], value.get("mask_ref"), value.get("uncertainty_ref"), value.get("axis_provenance"), value.get("source_artifact_id"), value.get("metadata", {}), missingness, value.get("quality_flags", ()), value.get("non_physical_dims", ()))
        if value.get("block_id") != block.block_id:
            raise ValueError("Data block hash does not match its content")
        return block


@dataclass(frozen=True)
class ComputationState:
    data_availability: str
    computability: str
    validity: str
    promotion: str
    missing_inputs: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    preconditions: tuple[str, ...] = ()
    next_actions: tuple[str | Mapping[str, Any], ...] = ()

    DATA = frozenset({"missing", "raw", "partial", "canonical"})
    COMPUTE = frozenset({"blocked", "needs_input", "computed", "not_applicable", "failed"})
    VALIDITY = frozenset({"not_assessed", "diagnostic", "validated"})
    PROMOTION = frozenset({"diagnostic_only", "review_required", "results_candidate"})

    def __post_init__(self) -> None:
        for name, choices in (("data_availability", self.DATA), ("computability", self.COMPUTE), ("validity", self.VALIDITY), ("promotion", self.PROMOTION)):
            value = str(getattr(self, name))
            if value not in choices:
                raise ValueError(f"Unsupported computation {name}: {value}")
            object.__setattr__(self, name, value)
        if self.promotion == "results_candidate" and (self.computability != "computed" or self.validity != "validated"):
            raise ValueError("results_candidate requires computed and validated state")
        for name in ("missing_inputs", "reason_codes", "preconditions"):
            object.__setattr__(self, name, _dedupe(getattr(self, name), f"ComputationState {name}"))
        object.__setattr__(self, "next_actions", _dedupe_actions(self.next_actions, "ComputationState next_actions"))

    @classmethod
    def create(cls, data_availability: str, computability: str, validity: str, promotion: str, missing_inputs: Sequence[str] = (), reason_codes: Sequence[str] = (), preconditions: Sequence[str] = (), next_actions: Sequence[str | Mapping[str, Any]] = ()) -> "ComputationState":
        return cls(data_availability, computability, validity, promotion, missing_inputs, reason_codes, preconditions, next_actions)

    def to_dict(self) -> dict[str, Any]:
        return {"data_availability": self.data_availability, "computability": self.computability, "validity": self.validity, "promotion": self.promotion, "missing_inputs": list(self.missing_inputs), "reason_codes": list(self.reason_codes), "preconditions": list(self.preconditions), "next_actions": _public(self.next_actions)}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ComputationState":
        if not isinstance(value, Mapping):
            raise TypeError("Computation state must be a mapping")
        return cls.create(value["data_availability"], value["computability"], value["validity"], value["promotion"], value.get("missing_inputs", ()), value.get("reason_codes", ()), value.get("preconditions", ()), value.get("next_actions", ()))


__all__ = ["DataBlock", "AxisProvenance", "CalibrationRef", "UncertaintyRef", "MissingnessPolicy", "ComputationState", "CapabilityResultStatus", "canonical_json_hash", "axis_allows_quantitative"]
