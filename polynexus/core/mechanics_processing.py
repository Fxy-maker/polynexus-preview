"""Deterministic, sample-neutral processing for canonical mechanics curves."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping, Sequence

import numpy as np


_PROCESSING_VERSION = "mechanics.processing.v1"
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
) -> MechanicsProcessingOutcome:
    """Describe recorded mechanics curves without inferring test models."""

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

    mechanics_property_summary = {
        "status": "unavailable",
        "unavailable_reason": "test_semantics_and_geometry_required",
        "yield_stress": None,
        "yield_strain": None,
        "tensile_modulus": None,
        "flexural_modulus": None,
        "toughness": None,
        "fatigue_life": None,
        "creep_parameters": None,
    }
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
    "MechanicsProcessingOutcome",
    "MechanicsSignalSeries",
    "analyze_mechanics_group",
]
