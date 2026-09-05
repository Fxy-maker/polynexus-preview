"""Deterministic, sample-neutral processing for canonical rheology groups."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping, Sequence

import numpy as np


_PROCESSING_VERSION = "rheology.processing.v1"
_STRESS_SCALE_PA = {"Pa": 1.0, "kPa": 1.0e3, "MPa": 1.0e6, "GPa": 1.0e9}
_VISCOSITY_SCALE_PA_S = {
    "Pa*s": 1.0,
    "mPa*s": 1.0e-3,
    "kPa*s": 1.0e3,
    "MPa*s": 1.0e6,
    "cP": 1.0e-3,
}
_RATE_SCALE_PER_SECOND = {"s^-1": 1.0, "1/s": 1.0}


@dataclass(frozen=True)
class RheologySignalSeries:
    """One immutable canonical rheology signal used by group calculations."""

    measurement_id: str
    signal_kind: str
    unit: str
    values: tuple[float, ...]
    x_values: tuple[float, ...] | None = None

    def __post_init__(self) -> None:
        for name in ("measurement_id", "signal_kind", "unit"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a nonempty string")
        if len(self.values) < 2 or not all(math.isfinite(value) for value in self.values):
            raise ValueError("rheology signal values must contain at least two finite points")
        if self.x_values is not None:
            if len(self.x_values) != len(self.values):
                raise ValueError("rheology signal coordinates and values must have equal lengths")
            if not all(math.isfinite(value) for value in self.x_values):
                raise ValueError("rheology signal coordinates must be finite")

    @classmethod
    def create(
        cls,
        *,
        measurement_id: str,
        signal_kind: str,
        unit: str,
        values: Sequence[float],
        x_values: Sequence[float] | None = None,
    ) -> "RheologySignalSeries":
        return cls(
            measurement_id=str(measurement_id),
            signal_kind=str(signal_kind),
            unit=str(unit),
            values=tuple(float(value) for value in values),
            x_values=(
                None if x_values is None else tuple(float(value) for value in x_values)
            ),
        )


@dataclass(frozen=True)
class RheologyProcessingOutcome:
    """One JSON-safe processed signal group plus metric-manifest metadata."""

    metrics: Mapping[str, Any]
    units: Mapping[str, str]
    methods: Mapping[str, str]
    parameters: Mapping[str, Mapping[str, Any]]


def analyze_rheology_group(
    x_values: Sequence[float],
    *,
    axis_kind: str,
    axis_unit: str,
    signals: Sequence[RheologySignalSeries],
) -> RheologyProcessingOutcome:
    """Compute rheological identities without fitting a material model."""

    x = np.asarray(x_values, dtype=float)
    if x.ndim != 1 or x.size < 2 or not np.all(np.isfinite(x)):
        raise ValueError("rheology processing requires a finite one-dimensional axis")
    signal_items = tuple(signals)
    if not signal_items or not all(
        isinstance(item, RheologySignalSeries) for item in signal_items
    ):
        raise TypeError("signals must contain RheologySignalSeries values")

    units: dict[str, str] = {}
    methods: dict[str, str] = {}
    parameters: dict[str, Mapping[str, Any]] = {}
    source_signals: dict[str, dict[str, Any]] = {}
    for signal in signal_items:
        signal_x = _series_x(signal, x)
        source_signals[signal.measurement_id] = {
            "signal_kind": signal.signal_kind,
            "unit": signal.unit,
            "axis_values": tuple(float(value) for value in signal_x),
            "values": signal.values,
        }
        axis_path = f"source_signals.{signal.measurement_id}.axis_values"
        value_path = f"source_signals.{signal.measurement_id}.values"
        units[axis_path] = str(axis_unit)
        units[value_path] = signal.unit
        methods[axis_path] = "canonical_source_values"
        methods[value_path] = "canonical_source_values"

    rate = _rate_input(x, axis_kind=str(axis_kind), axis_unit=str(axis_unit))
    stress = _unique_signal(signal_items, "shear_stress", reference_x=x)
    viscosity = _unique_signal(signal_items, "viscosity", reference_x=x)
    derived_viscosity = _derive_apparent_viscosity(stress, rate)
    derived_stress = _derive_shear_stress(viscosity, rate)
    derived_rate = _derive_shear_rate(stress, viscosity)
    _add_record_metadata(
        derived_viscosity,
        path="derived_apparent_viscosity.values",
        units=units,
        methods=methods,
        parameters=parameters,
    )
    _add_record_metadata(
        derived_stress,
        path="derived_shear_stress.values",
        units=units,
        methods=methods,
        parameters=parameters,
    )
    _add_record_metadata(
        derived_rate,
        path="derived_shear_rate.values",
        units=units,
        methods=methods,
        parameters=parameters,
    )

    oscillatory = _oscillatory_metrics(
        x,
        axis_kind=str(axis_kind),
        axis_unit=str(axis_unit),
        signals=signal_items,
    )
    for name, record in oscillatory.items():
        _add_record_metadata(
            record,
            path=f"oscillatory.{name}.values",
            units=units,
            methods=methods,
            parameters=parameters,
        )

    metrics = {
        "processing_version": _PROCESSING_VERSION,
        "axis_kind": str(axis_kind),
        "axis_unit": str(axis_unit),
        "source_signals": source_signals,
        "derived_apparent_viscosity": derived_viscosity,
        "derived_shear_stress": derived_stress,
        "derived_shear_rate": derived_rate,
        "oscillatory": oscillatory,
    }
    return RheologyProcessingOutcome(metrics, units, methods, parameters)


def _rate_input(x: np.ndarray, *, axis_kind: str, axis_unit: str) -> dict[str, Any]:
    if axis_kind != "shear_rate":
        return _unavailable("shear_rate_required")
    factor = _scale_for(axis_unit, _RATE_SCALE_PER_SECOND)
    if factor is None:
        return _unavailable("shear_rate_unit_incompatible")
    return {
        "status": "computed",
        "measurement_id": "canonical_axis",
        "unit": "s^-1",
        "values": tuple(float(value * factor) for value in x),
        "parameters": {
            "source_unit": axis_unit,
            "rate_to_per_second_factor": factor,
        },
    }


def _unique_signal(
    signals: Sequence[RheologySignalSeries],
    signal_kind: str,
    *,
    reference_x: np.ndarray,
) -> dict[str, Any]:
    matches = tuple(item for item in signals if item.signal_kind == signal_kind)
    if not matches:
        return _unavailable(f"{signal_kind}_missing")
    if len(matches) != 1:
        return _unavailable(f"{signal_kind}_ambiguous")
    signal = matches[0]
    signal_x = _series_x(signal, reference_x)
    if signal_x.shape != reference_x.shape or not np.array_equal(signal_x, reference_x):
        return _unavailable(f"{signal_kind}_axis_incompatible")
    return {
        "status": "computed",
        "measurement_id": signal.measurement_id,
        "unit": signal.unit,
        "values": signal.values,
    }


def _derive_apparent_viscosity(
    stress: Mapping[str, Any],
    rate: Mapping[str, Any],
) -> dict[str, Any]:
    missing = _input_reason(stress, rate)
    if missing is not None:
        return _unavailable(missing)
    stress_factor = _scale_for(str(stress["unit"]), _STRESS_SCALE_PA)
    rate_factor = _scale_for(str(rate["unit"]), _RATE_SCALE_PER_SECOND)
    if stress_factor is None:
        return _unavailable("shear_stress_unit_incompatible")
    if rate_factor is None:
        return _unavailable("shear_rate_unit_incompatible")
    stress_pa = np.asarray(stress["values"], dtype=float) * stress_factor
    rate_per_second = np.asarray(rate["values"], dtype=float) * rate_factor
    parameters = {
        "stress_measurement_id": stress["measurement_id"],
        "rate_measurement_id": rate["measurement_id"],
        "stress_to_pa_factor": stress_factor,
        "rate_to_per_second_factor": rate_factor,
        "zero_denominator_policy": "preserve_point_as_unavailable",
    }
    return _divide_series(
        stress_pa,
        rate_per_second,
        unit="Pa*s",
        method="shear_stress_divided_by_shear_rate",
        parameters=parameters,
        zero_warning="shear_rate_zero_at_some_points",
        all_zero_reason="shear_rate_zero_at_all_points",
    )


def _derive_shear_stress(
    viscosity: Mapping[str, Any],
    rate: Mapping[str, Any],
) -> dict[str, Any]:
    missing = _input_reason(viscosity, rate)
    if missing is not None:
        return _unavailable(missing)
    viscosity_factor = _scale_for(str(viscosity["unit"]), _VISCOSITY_SCALE_PA_S)
    rate_factor = _scale_for(str(rate["unit"]), _RATE_SCALE_PER_SECOND)
    if viscosity_factor is None:
        return _unavailable("viscosity_unit_incompatible")
    if rate_factor is None:
        return _unavailable("shear_rate_unit_incompatible")
    values = (
        np.asarray(viscosity["values"], dtype=float)
        * viscosity_factor
        * np.asarray(rate["values"], dtype=float)
        * rate_factor
    )
    parameters = {
        "viscosity_measurement_id": viscosity["measurement_id"],
        "rate_measurement_id": rate["measurement_id"],
        "viscosity_to_pa_s_factor": viscosity_factor,
        "rate_to_per_second_factor": rate_factor,
    }
    return _computed_series(
        values,
        unit="Pa",
        method="viscosity_multiplied_by_shear_rate",
        parameters=parameters,
    )


def _derive_shear_rate(
    stress: Mapping[str, Any],
    viscosity: Mapping[str, Any],
) -> dict[str, Any]:
    missing = _input_reason(stress, viscosity)
    if missing is not None:
        return _unavailable(missing)
    stress_factor = _scale_for(str(stress["unit"]), _STRESS_SCALE_PA)
    viscosity_factor = _scale_for(str(viscosity["unit"]), _VISCOSITY_SCALE_PA_S)
    if stress_factor is None:
        return _unavailable("shear_stress_unit_incompatible")
    if viscosity_factor is None:
        return _unavailable("viscosity_unit_incompatible")
    stress_pa = np.asarray(stress["values"], dtype=float) * stress_factor
    viscosity_pa_s = np.asarray(viscosity["values"], dtype=float) * viscosity_factor
    parameters = {
        "stress_measurement_id": stress["measurement_id"],
        "viscosity_measurement_id": viscosity["measurement_id"],
        "stress_to_pa_factor": stress_factor,
        "viscosity_to_pa_s_factor": viscosity_factor,
        "zero_denominator_policy": "preserve_point_as_unavailable",
    }
    return _divide_series(
        stress_pa,
        viscosity_pa_s,
        unit="s^-1",
        method="shear_stress_divided_by_viscosity",
        parameters=parameters,
        zero_warning="viscosity_zero_at_some_points",
        all_zero_reason="viscosity_zero_at_all_points",
    )


def _oscillatory_metrics(
    x: np.ndarray,
    *,
    axis_kind: str,
    axis_unit: str,
    signals: Sequence[RheologySignalSeries],
) -> dict[str, dict[str, Any]]:
    storage = _unique_signal(signals, "storage_modulus", reference_x=x)
    loss = _unique_signal(signals, "loss_modulus", reference_x=x)
    missing = _input_reason(storage, loss)
    if missing is not None:
        unavailable = _unavailable(missing)
        return {
            "tan_delta": unavailable,
            "complex_modulus_magnitude": unavailable,
            "complex_viscosity_magnitude": _unavailable("complex_modulus_unavailable"),
        }
    storage_factor = _scale_for(str(storage["unit"]), _STRESS_SCALE_PA)
    loss_factor = _scale_for(str(loss["unit"]), _STRESS_SCALE_PA)
    if storage_factor is None or loss_factor is None:
        unavailable = _unavailable("modulus_units_incompatible")
        return {
            "tan_delta": unavailable,
            "complex_modulus_magnitude": unavailable,
            "complex_viscosity_magnitude": _unavailable("complex_modulus_unavailable"),
        }
    storage_pa = np.asarray(storage["values"], dtype=float) * storage_factor
    loss_pa = np.asarray(loss["values"], dtype=float) * loss_factor
    pair_parameters = {
        "storage_measurement_id": storage["measurement_id"],
        "loss_measurement_id": loss["measurement_id"],
        "storage_to_pa_factor": storage_factor,
        "loss_to_pa_factor": loss_factor,
    }
    tan_delta = _divide_series(
        loss_pa,
        storage_pa,
        unit="1",
        method="loss_modulus_divided_by_storage_modulus",
        parameters={
            **pair_parameters,
            "zero_denominator_policy": "preserve_point_as_unavailable",
        },
        zero_warning="storage_modulus_zero_at_some_points",
        all_zero_reason="storage_modulus_zero_at_all_points",
    )
    complex_modulus = _computed_series(
        np.hypot(storage_pa, loss_pa),
        unit="Pa",
        method="euclidean_magnitude_of_storage_and_loss_modulus",
        parameters=pair_parameters,
    )
    omega, frequency_parameters = _angular_frequency(
        x,
        axis_kind=axis_kind,
        axis_unit=axis_unit,
    )
    if omega is None:
        complex_viscosity = _unavailable("angular_frequency_required")
    else:
        complex_viscosity = _divide_series(
            np.asarray(complex_modulus["values"], dtype=float),
            omega,
            unit="Pa*s",
            method="complex_modulus_magnitude_divided_by_angular_frequency",
            parameters={
                **pair_parameters,
                **frequency_parameters,
                "zero_denominator_policy": "preserve_point_as_unavailable",
            },
            zero_warning="angular_frequency_zero_at_some_points",
            all_zero_reason="angular_frequency_zero_at_all_points",
        )
    return {
        "tan_delta": tan_delta,
        "complex_modulus_magnitude": complex_modulus,
        "complex_viscosity_magnitude": complex_viscosity,
    }


def _angular_frequency(
    x: np.ndarray,
    *,
    axis_kind: str,
    axis_unit: str,
) -> tuple[np.ndarray | None, dict[str, Any]]:
    normalized_unit = axis_unit.strip()
    if axis_kind == "frequency":
        scale = {"Hz": 1.0, "kHz": 1.0e3}.get(normalized_unit)
        if scale is None:
            return None, {}
        return (
            x * scale * 2.0 * math.pi,
            {
                "frequency_source": "canonical_axis",
                "frequency_source_unit": axis_unit,
                "frequency_to_hz_factor": scale,
                "frequency_to_angular_frequency": "omega=2*pi*f",
            },
        )
    if axis_kind == "angular_frequency" and normalized_unit == "rad/s":
        return (
            x.copy(),
            {
                "frequency_source": "canonical_axis",
                "frequency_source_unit": axis_unit,
                "frequency_to_angular_frequency": "canonical_axis_is_omega",
            },
        )
    return None, {}


def _divide_series(
    numerator: np.ndarray,
    denominator: np.ndarray,
    *,
    unit: str,
    method: str,
    parameters: Mapping[str, Any],
    zero_warning: str,
    all_zero_reason: str,
) -> dict[str, Any]:
    valid = denominator != 0.0
    values = tuple(
        float(numerator[index] / denominator[index]) if bool(is_valid) else None
        for index, is_valid in enumerate(valid)
    )
    if not np.any(valid):
        return {
            **_unavailable(all_zero_reason),
            "values": values,
            "validity_mask": tuple(False for _ in values),
            "unit": unit,
            "method": method,
            "parameters": dict(parameters),
        }
    warnings = (zero_warning,) if np.any(~valid) else ()
    return {
        "status": "computed_with_warning" if warnings else "computed",
        "values": values,
        "validity_mask": tuple(bool(value) for value in valid),
        "unit": unit,
        "method": method,
        "parameters": dict(parameters),
        "warnings": warnings,
    }


def _computed_series(
    values: np.ndarray,
    *,
    unit: str,
    method: str,
    parameters: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "status": "computed",
        "values": tuple(float(value) for value in values),
        "validity_mask": tuple(True for _ in values),
        "unit": unit,
        "method": method,
        "parameters": dict(parameters),
        "warnings": (),
    }


def _input_reason(*records: Mapping[str, Any]) -> str | None:
    for record in records:
        if record.get("status") != "computed":
            return str(record.get("unavailable_reason", "required_input_unavailable"))
    return None


def _scale_for(unit: str, scales: Mapping[str, float]) -> float | None:
    return scales.get(unit.strip())


def _series_x(signal: RheologySignalSeries, reference_x: np.ndarray) -> np.ndarray:
    if signal.x_values is None:
        return reference_x
    return np.asarray(signal.x_values, dtype=float)


def _add_record_metadata(
    record: Mapping[str, Any],
    *,
    path: str,
    units: dict[str, str],
    methods: dict[str, str],
    parameters: dict[str, Mapping[str, Any]],
) -> None:
    if record.get("status") not in {"computed", "computed_with_warning"}:
        return
    units[path] = str(record["unit"])
    methods[path] = str(record["method"])
    parameters[path] = dict(record["parameters"])


def _unavailable(reason: str) -> dict[str, str]:
    return {"status": "unavailable", "unavailable_reason": reason}


__all__ = [
    "RheologyProcessingOutcome",
    "RheologySignalSeries",
    "analyze_rheology_group",
]
