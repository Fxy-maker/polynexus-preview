"""Deterministic, sample-neutral processing for canonical mechanics curves."""

from __future__ import annotations

from dataclasses import dataclass
import math
from types import MappingProxyType
from typing import Any, Mapping, Sequence

import numpy as np


_PROCESSING_VERSION = "mechanics.processing.v1"
_SUPPORTED_TEST_MODES = frozenset({"tensile", "compression", "flexural"})
_SUPPORTED_TOUGHNESS_ENDPOINTS = frozenset({"last_valid"})
_STRESS_UNIT_FACTORS = {
    "pa": 1.0,
    "kpa": 1.0e3,
    "mpa": 1.0e6,
    "gpa": 1.0e9,
}
_STRAIN_UNIT_FACTORS = {
    "1": 1.0,
    "fraction": 1.0,
    "dimensionless": 1.0,
    "%": 1.0e-2,
    "percent": 1.0e-2,
}
_RESPONSE_SIGNAL_KINDS = frozenset(
    {
        "tensile_stress",
        "compressive_stress",
        "flexural_stress",
        "shear_stress",
        "stress",
        "force",
        "load",
        "strain",
        "displacement",
        "extension",
        "deflection",
        "energy",
        "work",
    }
)


@dataclass(frozen=True)
class MechanicsSignalSeries:
    """One explicitly labelled mechanics response and its source coordinates."""

    measurement_id: str
    signal_kind: str
    test_mode: str
    unit: str
    values: tuple[float, ...]
    x_values: tuple[float, ...] | None = None

    @classmethod
    def create(
        cls,
        *,
        measurement_id: str,
        signal_kind: str,
        test_mode: str,
        unit: str,
        values: Sequence[float],
        x_values: Sequence[float] | None = None,
    ) -> "MechanicsSignalSeries":
        identity = str(measurement_id).strip()
        kind = str(signal_kind).strip()
        mode = str(test_mode).strip() or "unspecified"
        if not identity or not kind:
            raise ValueError("Mechanics signal identity and semantics must not be empty")
        numeric_values = _finite_values(values, name="mechanics signal values")
        numeric_x = (
            None
            if x_values is None
            else _finite_values(x_values, name="mechanics signal coordinates")
        )
        if numeric_x is not None and len(numeric_x) != len(numeric_values):
            raise ValueError("Mechanics signal coordinates and values must have equal length")
        return cls(
            measurement_id=identity,
            signal_kind=kind,
            test_mode=mode,
            unit=str(unit).strip() or "unknown",
            values=numeric_values,
            x_values=numeric_x,
        )


@dataclass(frozen=True)
class MechanicsAnalysisSpec:
    """Explicit semantics required by geometry/model-dependent mechanics fits."""

    test_mode: str
    stress_measurement_id: str
    strain_measurement_id: str | None
    geometry: Mapping[str, float]
    stress_unit: str
    strain_unit: str
    modulus_window: tuple[float, float]
    yield_offset: float | None = None
    toughness_endpoint: str | None = None

    @classmethod
    def create(
        cls,
        *,
        test_mode: str,
        stress_measurement_id: str,
        geometry: Mapping[str, Any],
        stress_unit: str,
        strain_unit: str,
        modulus_window: Sequence[float],
        strain_measurement_id: str | None = None,
        yield_offset: float | None = None,
        toughness_endpoint: str | None = None,
    ) -> "MechanicsAnalysisSpec":
        mode = str(test_mode).strip().casefold()
        if mode == "compressive":
            mode = "compression"
        if mode not in _SUPPORTED_TEST_MODES:
            raise ValueError(f"Unsupported mechanics test mode: {test_mode}")
        stress_id = str(stress_measurement_id).strip()
        if not stress_id:
            raise ValueError("Mechanics stress measurement id must not be empty")
        if not isinstance(geometry, Mapping) or not geometry:
            raise ValueError("Mechanics geometry must contain explicit values")
        normalized_geometry: dict[str, float] = {}
        for name, value in geometry.items():
            numeric = float(value)
            if not math.isfinite(numeric) or numeric <= 0.0:
                raise ValueError("Mechanics geometry values must be finite and positive")
            normalized_geometry[str(name)] = numeric
        normalized_stress_unit = str(stress_unit).strip()
        normalized_strain_unit = str(strain_unit).strip()
        _stress_factor(normalized_stress_unit)
        _strain_factor(normalized_strain_unit)
        if isinstance(modulus_window, (str, bytes, bytearray)):
            raise TypeError("Mechanics modulus window must be a numeric pair")
        window = tuple(float(item) for item in modulus_window)
        if len(window) != 2 or any(not math.isfinite(item) for item in window) or window[0] >= window[1]:
            raise ValueError("Mechanics modulus window must be a finite increasing pair")
        offset = None if yield_offset is None else float(yield_offset)
        if offset is not None and (not math.isfinite(offset) or offset <= 0.0):
            raise ValueError("Mechanics yield offset must be finite and positive")
        endpoint = None if toughness_endpoint is None else str(toughness_endpoint).strip().casefold()
        if endpoint is not None and endpoint not in _SUPPORTED_TOUGHNESS_ENDPOINTS:
            raise ValueError(f"Unsupported mechanics toughness endpoint: {toughness_endpoint}")
        return cls(
            test_mode=mode,
            stress_measurement_id=stress_id,
            strain_measurement_id=(
                None if strain_measurement_id is None else str(strain_measurement_id).strip()
            ),
            geometry=MappingProxyType(normalized_geometry),
            stress_unit=normalized_stress_unit,
            strain_unit=normalized_strain_unit,
            modulus_window=window,
            yield_offset=offset,
            toughness_endpoint=endpoint,
        )

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "MechanicsAnalysisSpec":
        if not isinstance(value, Mapping):
            raise TypeError("Mechanics analysis spec must be a mapping")
        return cls.create(
            test_mode=value.get("test_mode", ""),
            stress_measurement_id=value.get("stress_measurement_id", ""),
            strain_measurement_id=value.get("strain_measurement_id"),
            geometry=value.get("geometry", {}),
            stress_unit=value.get("stress_unit", ""),
            strain_unit=value.get("strain_unit", ""),
            modulus_window=value.get("modulus_window", ()),
            yield_offset=value.get("yield_offset"),
            toughness_endpoint=value.get("toughness_endpoint"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_mode": self.test_mode,
            "stress_measurement_id": self.stress_measurement_id,
            "strain_measurement_id": self.strain_measurement_id,
            "geometry": dict(self.geometry),
            "stress_unit": self.stress_unit,
            "strain_unit": self.strain_unit,
            "modulus_window": list(self.modulus_window),
            "yield_offset": self.yield_offset,
            "toughness_endpoint": self.toughness_endpoint,
        }


@dataclass(frozen=True)
class MechanicsProcessingOutcome:
    """JSON-safe mechanics descriptors plus metric-manifest metadata."""

    metrics: Mapping[str, Any]
    units: Mapping[str, str]
    methods: Mapping[str, str]
    parameters: Mapping[str, Mapping[str, Any]]


def analyze_mechanics_group(
    x_values: Sequence[float],
    *,
    axis_kind: str,
    axis_unit: str,
    signals: Sequence[MechanicsSignalSeries],
    analysis_spec: MechanicsAnalysisSpec | Mapping[str, Any] | None = None,
) -> MechanicsProcessingOutcome:
    """Describe curves and run only explicitly configured mechanics models."""

    coordinates = np.asarray(
        _finite_values(x_values, name="mechanics group coordinates"), dtype=float
    )
    if coordinates.size < 2:
        raise ValueError("Mechanics processing requires at least two coordinates")
    selected_signals = tuple(signals)
    if not selected_signals:
        raise ValueError("Mechanics processing requires at least one signal")
    if not all(isinstance(signal, MechanicsSignalSeries) for signal in selected_signals):
        raise TypeError("Mechanics signals must be MechanicsSignalSeries values")
    identities = tuple(signal.measurement_id for signal in selected_signals)
    if len(set(identities)) != len(identities):
        raise ValueError("Mechanics signal measurement ids must be unique")

    units: dict[str, str] = {}
    methods: dict[str, str] = {}
    parameters: dict[str, Mapping[str, Any]] = {}
    source_signals: dict[str, dict[str, Any]] = {}
    response_descriptors: dict[str, dict[str, Any]] = {}

    for signal in selected_signals:
        signal_coordinates = (
            coordinates
            if signal.x_values is None
            else np.asarray(signal.x_values, dtype=float)
        )
        values = np.asarray(signal.values, dtype=float)
        if signal_coordinates.size != values.size or values.size < 2:
            raise ValueError("Mechanics signals require equal coordinate and value arrays")
        source_signals[signal.measurement_id] = {
            "signal_kind": signal.signal_kind,
            "test_mode": signal.test_mode,
            "unit": signal.unit,
            "coordinates": tuple(float(value) for value in signal_coordinates),
            "values": signal.values,
        }
        if signal.signal_kind not in _RESPONSE_SIGNAL_KINDS:
            continue

        prefix = f"response_descriptors.{signal.measurement_id}"
        peak_index = int(np.argmax(values))
        peak_coordinate = {
            "status": "computed",
            "value": float(signal_coordinates[peak_index]),
            "unit": str(axis_unit),
            "canonical_index": peak_index,
        }
        peak_response = {
            "status": "computed",
            "value": float(values[peak_index]),
            "unit": signal.unit,
            "canonical_index": peak_index,
        }
        units[f"{prefix}.peak_coordinate.value"] = str(axis_unit)
        methods[f"{prefix}.peak_coordinate.value"] = "recorded_global_maximum"
        parameters[f"{prefix}.peak_coordinate.value"] = {
            "selection": "first_global_maximum",
            "model_interpretation": False,
        }
        units[f"{prefix}.peak_response.value"] = signal.unit
        methods[f"{prefix}.peak_response.value"] = "recorded_global_maximum"
        parameters[f"{prefix}.peak_response.value"] = {
            "selection": "first_global_maximum",
            "model_interpretation": False,
        }

        delta = np.diff(signal_coordinates)
        if not (np.all(delta > 0.0) or np.all(delta < 0.0)):
            raw_integral = _unavailable("coordinate_not_strictly_monotonic")
        else:
            direction = "increasing" if bool(np.all(delta > 0.0)) else "decreasing"
            integration_x = signal_coordinates if direction == "increasing" else signal_coordinates[::-1]
            integration_values = values if direction == "increasing" else values[::-1]
            integral = float(np.trapezoid(integration_values, integration_x))
            integral_unit = _product_unit(signal.unit, str(axis_unit))
            raw_integral = {
                "status": "computed_with_warning",
                "value": integral,
                "unit": integral_unit,
                "warnings": ("baseline_and_geometry_not_corrected",),
            }
            units[f"{prefix}.raw_integral.value"] = integral_unit
            methods[f"{prefix}.raw_integral.value"] = (
                "baseline_uncorrected_trapezoid_integral"
            )
            parameters[f"{prefix}.raw_integral.value"] = {
                "coordinate_direction": direction,
                "baseline_corrected": False,
                "geometry_corrected": False,
            }
        response_descriptors[signal.measurement_id] = {
            "signal_kind": signal.signal_kind,
            "test_mode": signal.test_mode,
            "peak_coordinate": peak_coordinate,
            "peak_response": peak_response,
            "raw_integral": raw_integral,
        }

    spec: MechanicsAnalysisSpec | None
    spec_error: str | None = None
    if analysis_spec is None:
        spec = None
    elif isinstance(analysis_spec, MechanicsAnalysisSpec):
        spec = analysis_spec
    elif isinstance(analysis_spec, Mapping):
        try:
            spec = MechanicsAnalysisSpec.from_mapping(analysis_spec)
        except (TypeError, ValueError):
            spec = None
            spec_error = "analysis_spec_invalid"
    else:
        raise TypeError("Mechanics analysis spec must be MechanicsAnalysisSpec or mapping")

    mechanics_property_summary = _advanced_property_summary(
        axis_values=coordinates,
        axis_kind=str(axis_kind),
        axis_unit=str(axis_unit),
        signals=selected_signals,
        spec=spec,
        spec_error=spec_error,
        units=units,
        methods=methods,
        parameters=parameters,
    )
    return MechanicsProcessingOutcome(
        metrics={
            "processing_version": _PROCESSING_VERSION,
            "axis_kind": str(axis_kind),
            "axis_unit": str(axis_unit),
            "source_signals": source_signals,
            "response_descriptors": response_descriptors,
            "mechanics_property_summary": mechanics_property_summary,
        },
        units=units,
        methods=methods,
        parameters=parameters,
    )


def _advanced_property_summary(
    *,
    axis_values: np.ndarray,
    axis_kind: str,
    axis_unit: str,
    signals: Sequence[MechanicsSignalSeries],
    spec: MechanicsAnalysisSpec | None,
    spec_error: str | None,
    units: dict[str, str],
    methods: dict[str, str],
    parameters: dict[str, Mapping[str, Any]],
) -> dict[str, Any]:
    property_names = (
        "yield_stress",
        "yield_strain",
        "tensile_modulus",
        "compressive_modulus",
        "flexural_modulus",
        "toughness",
    )
    if spec is None:
        reason = spec_error or "analysis_spec_required"
        if spec_error is None and not signals:
            reason = "test_semantics_and_geometry_required"
        unavailable = {
            name: _property_unavailable(reason)
            for name in property_names
        }
        unavailable.update({"fatigue_life": None, "creep_parameters": None})
        return {
            "status": "unavailable",
            "unavailable_reason": (
                "test_semantics_and_geometry_required"
                if spec_error is None
                else spec_error
            ),
            **unavailable,
        }

    signal_by_id = {signal.measurement_id: signal for signal in signals}
    stress = signal_by_id.get(spec.stress_measurement_id)
    modulus_name = f"{spec.test_mode}_modulus"
    results: dict[str, Any] = {
        name: _property_unavailable("not_requested")
        for name in property_names
    }
    results["fatigue_life"] = None
    results["creep_parameters"] = None

    if stress is None:
        unavailable = _property_unavailable("stress_measurement_not_found")
        results[modulus_name] = unavailable
        results["yield_stress"] = unavailable
        results["yield_strain"] = unavailable
        results["toughness"] = unavailable
        return _summary_with_status(results, "stress_measurement_not_found")
    if not _is_stress_signal(stress.signal_kind):
        unavailable = _property_unavailable("stress_measurement_semantics_required")
        results[modulus_name] = unavailable
        results["yield_stress"] = unavailable
        results["yield_strain"] = unavailable
        results["toughness"] = unavailable
        return _summary_with_status(results, "stress_measurement_semantics_required")
    if stress.test_mode not in {"unspecified", spec.test_mode}:
        unavailable = _property_unavailable("test_mode_mismatch")
        results[modulus_name] = unavailable
        results["yield_stress"] = unavailable
        results["yield_strain"] = unavailable
        results["toughness"] = unavailable
        return _summary_with_status(results, "test_mode_mismatch")

    stress_unit = stress.unit
    stress_source_unit = (
        spec.stress_unit
        if str(stress_unit).strip().casefold() == "unknown"
        else stress_unit
    )
    try:
        stress_values = np.asarray(stress.values, dtype=float) * _stress_factor(stress_source_unit)
        _stress_factor(spec.stress_unit)
    except ValueError:
        unavailable = _property_unavailable("stress_unit_unsupported")
        results[modulus_name] = unavailable
        results["yield_stress"] = unavailable
        results["yield_strain"] = unavailable
        results["toughness"] = unavailable
        return _summary_with_status(results, "stress_unit_unsupported")

    strain_signal = (
        signal_by_id.get(spec.strain_measurement_id)
        if spec.strain_measurement_id is not None
        else None
    )
    if spec.strain_measurement_id is not None and strain_signal is None:
        strain_values = None
        strain_reason = "strain_measurement_not_found"
    elif strain_signal is not None:
        if strain_signal.signal_kind != "strain":
            strain_values = None
            strain_reason = "strain_measurement_semantics_required"
        else:
            strain_values = np.asarray(strain_signal.values, dtype=float)
            strain_reason = None
    elif str(axis_kind) == "strain":
        strain_values = np.asarray(axis_values, dtype=float)
        strain_reason = None
    else:
        strain_values = None
        strain_reason = "strain_axis_or_measurement_required"
    if strain_values is None:
        unavailable = _property_unavailable(strain_reason or "strain_semantics_required")
        results[modulus_name] = unavailable
        results["yield_stress"] = unavailable
        results["yield_strain"] = unavailable
        results["toughness"] = unavailable
        return _summary_with_status(results, strain_reason or "strain_semantics_required")
    if strain_values.size != stress_values.size:
        unavailable = _property_unavailable("stress_strain_length_mismatch")
        results[modulus_name] = unavailable
        results["yield_stress"] = unavailable
        results["yield_strain"] = unavailable
        results["toughness"] = unavailable
        return _summary_with_status(results, "stress_strain_length_mismatch")
    try:
        strain_source_unit = strain_signal.unit if strain_signal is not None else axis_unit
        if str(strain_source_unit).strip().casefold() == "unknown":
            strain_source_unit = spec.strain_unit
        strain_factor = _strain_factor(strain_source_unit)
        expected_strain_factor = _strain_factor(spec.strain_unit)
    except ValueError:
        unavailable = _property_unavailable("strain_unit_unsupported")
        results[modulus_name] = unavailable
        results["yield_stress"] = unavailable
        results["yield_strain"] = unavailable
        results["toughness"] = unavailable
        return _summary_with_status(results, "strain_unit_unsupported")

    strain = strain_values * strain_factor
    stress_pa = stress_values
    if not np.all(np.isfinite(strain)) or not np.all(np.isfinite(stress_pa)):
        unavailable = _property_unavailable("nonfinite_stress_strain")
        results[modulus_name] = unavailable
        results["yield_stress"] = unavailable
        results["yield_strain"] = unavailable
        results["toughness"] = unavailable
        return _summary_with_status(results, "nonfinite_stress_strain")
    if not np.all(np.diff(strain) > 0.0):
        unavailable = _property_unavailable("strain_not_strictly_increasing")
        results[modulus_name] = unavailable
        results["yield_stress"] = unavailable
        results["yield_strain"] = unavailable
        results["toughness"] = unavailable
        return _summary_with_status(results, "strain_not_strictly_increasing")

    window = tuple(value * expected_strain_factor for value in spec.modulus_window)
    fit_mask = (strain >= window[0]) & (strain <= window[1])
    if int(np.count_nonzero(fit_mask)) < 2:
        unavailable = _property_unavailable("modulus_window_has_too_few_points")
        results[modulus_name] = unavailable
        results["yield_stress"] = unavailable
        results["yield_strain"] = unavailable
        if spec.toughness_endpoint == "last_valid":
            results["toughness"] = _toughness_result(
                strain, stress_pa, source_ids=_source_ids(spec, strain_signal),
                parameters={"endpoint_rule": "last_valid"},
                methods=methods, units=units, metric_key="toughness",
                metric_parameters=parameters,
            )
        return _summary_with_status(results, "modulus_window_has_too_few_points")

    slope, intercept = np.polyfit(strain[fit_mask], stress_pa[fit_mask], 1)
    fit_parameters = {
        "test_mode": spec.test_mode,
        "geometry": dict(spec.geometry),
        "modulus_window": list(spec.modulus_window),
        "modulus_window_unit": spec.strain_unit,
        "stress_source_unit": stress_source_unit,
        "strain_source_unit": strain_source_unit,
        "declared_stress_unit": spec.stress_unit,
        "declared_strain_unit": spec.strain_unit,
        "fit_point_count": int(np.count_nonzero(fit_mask)),
        "intercept_pa": float(intercept),
    }
    modulus = _property_computed(
        value=float(slope),
        unit="Pa",
        method="linear_least_squares_stress_strain",
        source_ids=_source_ids(spec, strain_signal),
        parameters=fit_parameters,
    )
    results[modulus_name] = modulus
    _record_property(
        metric_key=modulus_name,
        result=modulus,
        units=units,
        methods=methods,
        parameters=parameters,
    )

    if spec.yield_offset is None:
        results["yield_stress"] = _property_unavailable("yield_offset_required")
        results["yield_strain"] = _property_unavailable("yield_offset_required")
    elif not math.isfinite(float(slope)) or slope <= 0.0:
        results["yield_stress"] = _property_unavailable("non_positive_modulus_slope")
        results["yield_strain"] = _property_unavailable("non_positive_modulus_slope")
    else:
        yield_result = _offset_yield_result(
            strain=strain,
            stress_pa=stress_pa,
            slope=float(slope),
            intercept=float(intercept),
            offset=float(spec.yield_offset) * expected_strain_factor,
            source_ids=_source_ids(spec, strain_signal),
            parameters={**fit_parameters, "yield_offset": spec.yield_offset, "yield_offset_unit": spec.strain_unit},
            methods=methods,
            units=units,
            metric_parameters=parameters,
        )
        results["yield_stress"] = yield_result[0]
        results["yield_strain"] = yield_result[1]

    if spec.toughness_endpoint == "last_valid":
        results["toughness"] = _toughness_result(
            strain, stress_pa, source_ids=_source_ids(spec, strain_signal),
            parameters={"endpoint_rule": "last_valid", **fit_parameters},
            methods=methods, units=units, metric_key="toughness",
            metric_parameters=parameters,
        )
    else:
        results["toughness"] = _property_unavailable("toughness_endpoint_required")
    return _summary_with_status(results, "advanced_model_outputs_available")


def _source_ids(spec: MechanicsAnalysisSpec, strain_signal: MechanicsSignalSeries | None) -> list[str]:
    ids = [spec.stress_measurement_id]
    if strain_signal is not None:
        ids.append(strain_signal.measurement_id)
    return ids


def _is_stress_signal(signal_kind: str) -> bool:
    return signal_kind in {
        "stress",
        "tensile_stress",
        "compressive_stress",
        "flexural_stress",
        "shear_stress",
    }


def _stress_factor(unit: str) -> float:
    key = str(unit).strip().casefold()
    if key not in _STRESS_UNIT_FACTORS:
        raise ValueError(f"Unsupported mechanics stress unit: {unit}")
    return _STRESS_UNIT_FACTORS[key]


def _strain_factor(unit: str) -> float:
    key = str(unit).strip().casefold()
    if key not in _STRAIN_UNIT_FACTORS:
        raise ValueError(f"Unsupported mechanics strain unit: {unit}")
    return _STRAIN_UNIT_FACTORS[key]


def _property_unavailable(reason: str) -> dict[str, Any]:
    return {"status": "unavailable", "unavailable_reason": str(reason)}


def _property_computed(
    *,
    value: float,
    unit: str,
    method: str,
    source_ids: Sequence[str],
    parameters: Mapping[str, Any],
    warnings: Sequence[str] = (),
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "computed" if not warnings else "computed_with_warning",
        "value": float(value),
        "unit": str(unit),
        "method": str(method),
        "source_measurements": list(source_ids),
        "parameters": dict(parameters),
    }
    if warnings:
        result["warnings"] = list(warnings)
    return result


def _record_property(
    *,
    metric_key: str,
    result: Mapping[str, Any],
    units: dict[str, str],
    methods: dict[str, str],
    parameters: dict[str, Mapping[str, Any]],
) -> None:
    if result.get("status") not in {"computed", "computed_with_warning"}:
        return
    value_key = f"mechanics_property_summary.{metric_key}.value"
    units[value_key] = str(result["unit"])
    methods[value_key] = str(result["method"])
    parameters[value_key] = dict(result.get("parameters", {}))


def _offset_yield_result(
    *,
    strain: np.ndarray,
    stress_pa: np.ndarray,
    slope: float,
    intercept: float,
    offset: float,
    source_ids: Sequence[str],
    parameters: Mapping[str, Any],
    methods: dict[str, str],
    units: dict[str, str],
    metric_parameters: dict[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    difference = stress_pa - (slope * (strain - offset) + intercept)
    crossing: int | None = None
    for index in range(1, len(strain)):
        if difference[index - 1] >= 0.0 and difference[index] <= 0.0:
            crossing = index
            break
    if crossing is None:
        unavailable = _property_unavailable("offset_line_no_crossing")
        return unavailable, unavailable
    left = crossing - 1
    right = crossing
    if difference[right] == difference[left]:
        fraction = 0.0
    else:
        fraction = float(-difference[left] / (difference[right] - difference[left]))
    yield_strain = float(strain[left] + fraction * (strain[right] - strain[left]))
    yield_stress = float(stress_pa[left] + fraction * (stress_pa[right] - stress_pa[left]))
    shared = _property_computed(
        value=yield_stress,
        unit="Pa",
        method="offset_line_intersection",
        source_ids=source_ids,
        parameters=dict(parameters),
    )
    stress_result = dict(shared)
    strain_result = dict(shared)
    strain_result["value"] = yield_strain
    strain_result["unit"] = "1"
    value_key = "mechanics_property_summary.yield_stress.value"
    units[value_key] = "Pa"
    methods[value_key] = "offset_line_intersection"
    methods["mechanics_property_summary.yield_strain.value"] = "offset_line_intersection"
    units["mechanics_property_summary.yield_strain.value"] = "1"
    metric_parameters[value_key] = dict(parameters)
    metric_parameters["mechanics_property_summary.yield_strain.value"] = dict(parameters)
    return stress_result, strain_result


def _toughness_result(
    strain: np.ndarray,
    stress_pa: np.ndarray,
    *,
    source_ids: Sequence[str],
    parameters: Mapping[str, Any],
    methods: dict[str, str],
    units: dict[str, str],
    metric_key: str,
    metric_parameters: dict[str, Mapping[str, Any]],
) -> dict[str, Any]:
    warnings = ("negative_stress_values",) if bool(np.any(stress_pa < 0.0)) else ()
    result = _property_computed(
        value=float(np.trapezoid(stress_pa, strain)),
        unit="Pa",
        method="stress_strain_trapezoid_to_last_valid",
        source_ids=source_ids,
        parameters=parameters,
        warnings=warnings,
    )
    _record_property(
        metric_key=metric_key,
        result=result,
        units=units,
        methods=methods,
        parameters=metric_parameters,
    )
    return result


def _summary_with_status(results: Mapping[str, Any], reason: str) -> dict[str, Any]:
    computed = tuple(
        name for name, value in results.items()
        if isinstance(value, Mapping) and value.get("status") in {"computed", "computed_with_warning"}
    )
    summary = {
        "status": "computed" if computed else "unavailable",
        "unavailable_reason": reason if not computed else None,
        "computed_properties": list(computed),
        **dict(results),
    }
    return summary


def _finite_values(values: Sequence[float], *, name: str) -> tuple[float, ...]:
    if isinstance(values, (str, bytes, bytearray)):
        raise TypeError(f"{name} must be a numeric sequence")
    numeric = tuple(float(value) for value in values)
    if not numeric or any(not math.isfinite(value) for value in numeric):
        raise ValueError(f"{name} must contain finite values")
    return numeric


def _product_unit(signal_unit: str, axis_unit: str) -> str:
    if "unknown" in {signal_unit, axis_unit}:
        return "unknown"
    return f"{signal_unit}*{axis_unit}"


def _unavailable(reason: str) -> dict[str, str]:
    return {"status": "unavailable", "unavailable_reason": reason}


__all__ = [
    "MechanicsAnalysisSpec",
    "MechanicsProcessingOutcome",
    "MechanicsSignalSeries",
    "analyze_mechanics_group",
]
