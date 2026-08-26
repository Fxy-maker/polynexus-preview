"""Finite deterministic capability execution for canonical measurements."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Any

from .models import CanonicalExperiment, CapabilityItemResult, Measurement


CapabilityCalculator = Callable[[Measurement], Mapping[str, Any]]


@dataclass(frozen=True)
class CapabilitySpec:
    """One explicitly registered deterministic measurement capability."""

    capability_id: str
    measurement_families: tuple[str, ...]
    calculator: CapabilityCalculator = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        capability_id = str(self.capability_id).strip()
        if not capability_id:
            raise ValueError("Capability id must not be empty")
        families = tuple(str(family).strip() for family in self.measurement_families)
        if not families or any(not family for family in families):
            raise ValueError("Capability measurement families must not be empty")
        if not callable(self.calculator):
            raise TypeError("Capability calculator must be callable")
        object.__setattr__(self, "capability_id", capability_id)
        object.__setattr__(self, "measurement_families", families)


class CapabilityRegistry:
    """Closed registry of finite capabilities; unknown ids are never inferred."""

    def __init__(self, specs: Sequence[CapabilitySpec] | None = None) -> None:
        selected = tuple(specs if specs is not None else _DEFAULT_SPECS)
        if not all(isinstance(spec, CapabilitySpec) for spec in selected):
            raise TypeError("Capability registry entries must be CapabilitySpec values")
        ids = tuple(spec.capability_id for spec in selected)
        if len(set(ids)) != len(ids):
            raise ValueError("Capability ids must be unique")
        self._specs = selected
        self._by_id = {spec.capability_id: spec for spec in selected}

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(spec.capability_id for spec in self._specs)

    def resolve(self, capability_ids: Sequence[str] | None = None) -> tuple[CapabilitySpec, ...]:
        if capability_ids is None:
            return self._specs
        requested = tuple(str(capability_id) for capability_id in capability_ids)
        unknown = [capability_id for capability_id in requested if capability_id not in self._by_id]
        if unknown:
            raise ValueError(f"Unknown capability: {unknown[0]}")
        return tuple(self._by_id[capability_id] for capability_id in requested)


class CapabilityExecutor:
    """Execute every selected capability independently for every measurement."""

    def __init__(self, registry: CapabilityRegistry | None = None) -> None:
        self._registry = registry or default_capability_registry()

    def execute(
        self,
        template: CanonicalExperiment,
        *,
        capability_ids: Sequence[str] | None = None,
    ) -> tuple[CapabilityItemResult, ...]:
        if not isinstance(template, CanonicalExperiment):
            raise TypeError("Capability execution requires a CanonicalExperiment")
        specs = self._registry.resolve(capability_ids)
        results: list[CapabilityItemResult] = []
        for measurement in template.measurements:
            for spec in specs:
                item_id = _item_id(template, measurement, spec)
                if measurement.family not in spec.measurement_families:
                    results.append(
                        CapabilityItemResult(
                            item_id=item_id,
                            measurement_id=measurement.measurement_id,
                            capability_id=spec.capability_id,
                            status="not_applicable",
                            reason_codes=("capability_family_unsupported",),
                        )
                    )
                    continue
                try:
                    result = spec.calculator(measurement)
                    if not isinstance(result, Mapping):
                        raise TypeError("Capability calculator must return a mapping")
                    results.append(
                        CapabilityItemResult(
                            item_id=item_id,
                            measurement_id=measurement.measurement_id,
                            capability_id=spec.capability_id,
                            status="completed",
                            result=result,
                        )
                    )
                except Exception:
                    results.append(
                        CapabilityItemResult(
                            item_id=item_id,
                            measurement_id=measurement.measurement_id,
                            capability_id=spec.capability_id,
                            status="failed",
                            reason_codes=("capability_execution_failed",),
                        )
                    )
        return tuple(results)


def _summary(measurement: Measurement) -> Mapping[str, Any]:
    x_values = measurement.channels["x"]
    intensity_values = measurement.channels["intensity"]
    intensity_min = min(intensity_values)
    intensity_max = max(intensity_values)
    return {
        "point_count": len(x_values),
        "x_min": min(x_values),
        "x_max": max(x_values),
        "intensity_min": intensity_min,
        "intensity_max": intensity_max,
        "intensity_range": intensity_max - intensity_min,
    }


def _extrema(measurement: Measurement) -> Mapping[str, Any]:
    x_values = measurement.channels["x"]
    intensity_values = measurement.channels["intensity"]
    minimum_index = min(range(len(intensity_values)), key=intensity_values.__getitem__)
    maximum_index = max(range(len(intensity_values)), key=intensity_values.__getitem__)
    return {
        "minimum": {"x": x_values[minimum_index], "intensity": intensity_values[minimum_index]},
        "maximum": {"x": x_values[maximum_index], "intensity": intensity_values[maximum_index]},
    }


_SUPPORTED_FAMILIES = ("spectrum_1d", "scattering_1d")
_DEFAULT_SPECS = (
    CapabilitySpec("curve.extrema.v1", _SUPPORTED_FAMILIES, _extrema),
    CapabilitySpec("curve.summary.v1", _SUPPORTED_FAMILIES, _summary),
)
_DEFAULT_REGISTRY = CapabilityRegistry(_DEFAULT_SPECS)


def default_capability_registry() -> CapabilityRegistry:
    """Return the process-wide closed registry of generic curve capabilities."""

    return _DEFAULT_REGISTRY


def _item_id(template: CanonicalExperiment, measurement: Measurement, spec: CapabilitySpec) -> str:
    payload = {
        "template_hash": template.content_hash,
        "measurement_id": measurement.measurement_id,
        "capability_id": spec.capability_id,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"item-{sha256(encoded).hexdigest()}"


__all__ = [
    "CapabilityCalculator",
    "CapabilityExecutor",
    "CapabilityRegistry",
    "CapabilitySpec",
    "default_capability_registry",
]
