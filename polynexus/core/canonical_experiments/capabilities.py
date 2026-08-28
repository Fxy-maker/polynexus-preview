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
class ProviderCapabilitySpec:
    """A registered projection from provider metrics to one public capability."""

    capability_id: str
    techniques: tuple[str, ...]
    metric_paths: tuple[str, ...]

    def __post_init__(self) -> None:
        capability_id = str(self.capability_id).strip()
        techniques = tuple(str(value).strip().lower() for value in self.techniques)
        metric_paths = tuple(str(value).strip() for value in self.metric_paths)
        if not capability_id or not techniques or not metric_paths:
            raise ValueError("Provider capability fields must not be empty")
        if any(not value for value in techniques + metric_paths):
            raise ValueError("Provider capability fields must not be empty")
        object.__setattr__(self, "capability_id", capability_id)
        object.__setattr__(self, "techniques", techniques)
        object.__setattr__(self, "metric_paths", metric_paths)


class ProviderCapabilityRegistry:
    """Closed registry of provider result projections; no values are inferred."""

    def __init__(self, specs: Sequence[ProviderCapabilitySpec] | None = None) -> None:
        selected = tuple(specs if specs is not None else _DEFAULT_PROVIDER_SPECS)
        identities = tuple((spec.techniques, spec.capability_id) for spec in selected)
        if len(set(identities)) != len(identities):
            raise ValueError("Provider capability technique/id pairs must be unique")
        self._specs = selected

    def for_technique(self, technique: str) -> tuple[ProviderCapabilitySpec, ...]:
        normalized = str(technique).strip().lower()
        return tuple(spec for spec in self._specs if normalized in spec.techniques)


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
        if isinstance(self.measurement_families, (str, bytes, bytearray)):
            raise TypeError("Capability measurement families must be a sequence of family strings")
        if not isinstance(self.measurement_families, Sequence):
            raise TypeError("Capability measurement families must be a sequence of family strings")
        families = tuple(str(family).strip() for family in self.measurement_families)
        if not families or any(not family for family in families):
            raise ValueError("Capability measurement families must not be empty")
        if any(not isinstance(family, str) for family in self.measurement_families):
            raise TypeError("Capability measurement families must be a sequence of family strings")
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

    def __init__(
        self,
        registry: CapabilityRegistry | None = None,
        *,
        provider_registry: ProviderCapabilityRegistry | None = None,
    ) -> None:
        self._registry = registry or default_capability_registry()
        self._provider_registry = provider_registry or default_provider_capability_registry()

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

    def execute_provider_result(
        self,
        *,
        source_artifact_id: str,
        technique: str,
        metrics: Mapping[str, Any],
    ) -> tuple[CapabilityItemResult, ...]:
        """Project existing provider metrics without recalculating or guessing."""
        if not isinstance(metrics, Mapping):
            raise TypeError("Provider capability metrics must be a mapping")
        results: list[CapabilityItemResult] = []
        for spec in self._provider_registry.for_technique(technique):
            found = _find_metric(metrics, spec.metric_paths)
            item_id = _provider_item_id(source_artifact_id, technique, spec.capability_id)
            if found is None:
                results.append(
                    CapabilityItemResult(
                        item_id=item_id,
                        measurement_id="provider-result",
                        capability_id=spec.capability_id,
                        status="needs_input",
                        reason_codes=("provider_metric_unavailable",),
                    )
                )
                continue
            path, value = found
            results.append(
                CapabilityItemResult(
                    item_id=item_id,
                    measurement_id="provider-result",
                    capability_id=spec.capability_id,
                    status="completed",
                    result={"metric_path": path, "value": value},
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
        "units": {
            "x": measurement.units["x"],
            "intensity": measurement.units["intensity"],
        },
    }


def _extrema(measurement: Measurement) -> Mapping[str, Any]:
    x_values = measurement.channels["x"]
    intensity_values = measurement.channels["intensity"]
    minimum_index = min(range(len(intensity_values)), key=intensity_values.__getitem__)
    maximum_index = max(range(len(intensity_values)), key=intensity_values.__getitem__)
    return {
        "minimum": {"x": x_values[minimum_index], "intensity": intensity_values[minimum_index]},
        "maximum": {"x": x_values[maximum_index], "intensity": intensity_values[maximum_index]},
        "units": {
            "x": measurement.units["x"],
            "intensity": measurement.units["intensity"],
        },
    }


_SUPPORTED_FAMILIES = ("spectrum_1d", "scattering_1d")
_DEFAULT_SPECS = (
    CapabilitySpec("curve.extrema.v1", _SUPPORTED_FAMILIES, _extrema),
    CapabilitySpec("curve.summary.v1", _SUPPORTED_FAMILIES, _summary),
)
_DEFAULT_REGISTRY = CapabilityRegistry(_DEFAULT_SPECS)


def _provider_specs() -> tuple[ProviderCapabilitySpec, ...]:
    aliases = {
        "dsc": {
            "Tg": ("Tg_C", "Tg"), "Tm": ("Tm_peak_C", "Tm_C", "Tm"),
            "Tc": ("Tc_C", "Tc"), "enthalpy": ("DHm_Jg", "DHc_Jg", "enthalpy"),
            "multi_peak": ("peak_components", "multi_peak"),
            "Avrami": ("Avrami_n", "avrami_n", "Avrami"),
            "nonisothermal_kinetics": ("nonisothermal_kinetics", "kinetics"),
        },
        "ftir": {name: (name, name.replace("_", "")) for name in (
            "peak_position", "peak_height", "peak_area", "FWHM", "peak_ratio", "temperature_tracking"
        )},
        "saxs": {name: (name, name.lower(), f"{name}_nm") for name in (
            "long_period", "crystalline_layer", "amorphous_layer", "Porod", "Kratky", "Guinier", "Invariant", "temperature_strain"
        )},
        "waxs": {name: (name, name.lower()) for name in (
            "peak_decomposition", "crystallinity", "crystallite_size", "lattice_parameters", "williamson_hall"
        )},
        "nmr": {name: (name, name.lower()) for name in (
            "peak_position", "area", "FWHM", "SNR", "region_integral", "relaxation", "solid_13C_phase"
        )},
    }
    return tuple(
        ProviderCapabilitySpec(capability_id=capability_id, techniques=(technique,), metric_paths=paths)
        for technique, entries in aliases.items()
        for capability_id, paths in entries.items()
    )


_DEFAULT_PROVIDER_SPECS = _provider_specs()
_DEFAULT_PROVIDER_REGISTRY = ProviderCapabilityRegistry(_DEFAULT_PROVIDER_SPECS)


def default_capability_registry() -> CapabilityRegistry:
    """Return the process-wide closed registry of generic curve capabilities."""

    return _DEFAULT_REGISTRY


def default_provider_capability_registry() -> ProviderCapabilityRegistry:
    return _DEFAULT_PROVIDER_REGISTRY


def _item_id(template: CanonicalExperiment, measurement: Measurement, spec: CapabilitySpec) -> str:
    payload = {
        "template_hash": template.content_hash,
        "measurement_id": measurement.measurement_id,
        "capability_id": spec.capability_id,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"item-{sha256(encoded).hexdigest()}"


def _provider_item_id(source_artifact_id: str, technique: str, capability_id: str) -> str:
    payload = {"source_artifact_id": str(source_artifact_id), "technique": str(technique).lower(), "capability_id": capability_id}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"provider-item-{sha256(encoded).hexdigest()}"


def _find_metric(metrics: Mapping[str, Any], paths: Sequence[str]) -> tuple[str, Any] | None:
    for path in paths:
        if path in metrics:
            return path, metrics[path]
        current: Any = metrics
        for part in path.split("."):
            if not isinstance(current, Mapping) or part not in current:
                break
            current = current[part]
        else:
            return path, current
    return None


__all__ = [
    "CapabilityCalculator",
    "CapabilityExecutor",
    "CapabilityRegistry",
    "CapabilitySpec",
    "ProviderCapabilitySpec",
    "ProviderCapabilityRegistry",
    "default_capability_registry",
    "default_provider_capability_registry",
]
