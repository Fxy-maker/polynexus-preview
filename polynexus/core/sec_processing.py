"""Deterministic, sample-neutral processing for canonical SEC/GPC signals."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping, Sequence

import numpy as np


_PROCESSING_VERSION = "sec.processing.v1"
_RESPONSE_SIGNAL_KINDS = frozenset(
    {
        "refractive_index_response",
        "uv_response",
        "light_scattering_response",
        "viscometer_response",
        "concentration_response",
    }
)


@dataclass(frozen=True)
class SECSignalSeries:
    """One explicitly labelled chromatogram signal and its source coordinates."""

    measurement_id: str
    signal_kind: str
    detector_kind: str
    unit: str
    values: tuple[float, ...]
    x_values: tuple[float, ...] | None = None

    @classmethod
    def create(
        cls,
        *,
        measurement_id: str,
        signal_kind: str,
        detector_kind: str,
        unit: str,
        values: Sequence[float],
        x_values: Sequence[float] | None = None,
    ) -> "SECSignalSeries":
        identity = str(measurement_id).strip()
        kind = str(signal_kind).strip()
        detector = str(detector_kind).strip()
        if not identity or not kind or not detector:
            raise ValueError("SEC signal identity and semantics must not be empty")
        numeric_values = _finite_values(values, name="SEC signal values")
        numeric_x = (
            None
            if x_values is None
            else _finite_values(x_values, name="SEC signal coordinates")
        )
        if numeric_x is not None and len(numeric_x) != len(numeric_values):
            raise ValueError("SEC signal coordinates and values must have equal length")
        return cls(
            measurement_id=identity,
            signal_kind=kind,
            detector_kind=detector,
            unit=str(unit).strip() or "unknown",
            values=numeric_values,
            x_values=numeric_x,
        )


@dataclass(frozen=True)
class SECProcessingOutcome:
    """JSON-safe SEC descriptors plus metric-manifest metadata."""

    metrics: Mapping[str, Any]
    units: Mapping[str, str]
    methods: Mapping[str, str]
    parameters: Mapping[str, Mapping[str, Any]]


def analyze_sec_group(
    x_values: Sequence[float],
    *,
    axis_kind: str,
    axis_unit: str,
    signals: Sequence[SECSignalSeries],
) -> SECProcessingOutcome:
    """Describe source chromatograms without inventing calibration semantics."""

    coordinates = np.asarray(
        _finite_values(x_values, name="SEC group coordinates"), dtype=float
    )
    if coordinates.size < 2:
        raise ValueError("SEC processing requires at least two coordinates")
    selected_signals = tuple(signals)
    if not selected_signals:
        raise ValueError("SEC processing requires at least one signal")
    if not all(isinstance(signal, SECSignalSeries) for signal in selected_signals):
        raise TypeError("SEC signals must be SECSignalSeries values")
    identities = tuple(signal.measurement_id for signal in selected_signals)
    if len(set(identities)) != len(identities):
        raise ValueError("SEC signal measurement ids must be unique")

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
            raise ValueError("SEC signals require equal coordinate and value arrays")
        source_signals[signal.measurement_id] = {
            "signal_kind": signal.signal_kind,
            "detector_kind": signal.detector_kind,
            "unit": signal.unit,
            "coordinates": tuple(float(value) for value in signal_coordinates),
            "values": signal.values,
        }
        if signal.signal_kind not in _RESPONSE_SIGNAL_KINDS:
            continue

        prefix = f"response_descriptors.{signal.measurement_id}"
        peak_index = int(np.argmax(values))
        peak = {
            "status": "computed",
            "value": float(signal_coordinates[peak_index]),
            "unit": str(axis_unit),
            "canonical_index": peak_index,
        }
        units[f"{prefix}.peak_coordinate.value"] = str(axis_unit)
        methods[f"{prefix}.peak_coordinate.value"] = "recorded_global_maximum"
        parameters[f"{prefix}.peak_coordinate.value"] = {
            "selection": "first_global_maximum",
            "baseline_corrected": False,
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
                "warnings": ("baseline_and_detector_response_not_corrected",),
            }
            units[f"{prefix}.raw_integral.value"] = integral_unit
            methods[f"{prefix}.raw_integral.value"] = (
                "baseline_uncorrected_trapezoid_integral"
            )
            parameters[f"{prefix}.raw_integral.value"] = {
                "coordinate_direction": direction,
                "baseline_corrected": False,
                "detector_response_corrected": False,
            }
        response_descriptors[signal.measurement_id] = {
            "signal_kind": signal.signal_kind,
            "detector_kind": signal.detector_kind,
            "peak_coordinate": peak,
            "raw_integral": raw_integral,
        }

    molecular_weight_summary = {
        "status": "unavailable",
        "unavailable_reason": "calibration_and_distribution_semantics_required",
        "Mn": None,
        "Mw": None,
        "Mz": None,
        "dispersity": None,
    }
    return SECProcessingOutcome(
        metrics={
            "processing_version": _PROCESSING_VERSION,
            "axis_kind": str(axis_kind),
            "axis_unit": str(axis_unit),
            "source_signals": source_signals,
            "response_descriptors": response_descriptors,
            "molecular_weight_summary": molecular_weight_summary,
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


__all__ = ["SECProcessingOutcome", "SECSignalSeries", "analyze_sec_group"]
