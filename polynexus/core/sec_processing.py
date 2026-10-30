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
_DISTRIBUTION_MODES = frozenset({"mass", "number"})


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
class SECCalibrationSpec:
    """Explicit SEC/GPC calibration and detector-response semantics.

    Calibration is represented as coordinate versus molar mass standards. The
    fit is performed in log10(molar mass); no chemistry, detector response, or
    extrapolation is inferred by this contract.
    """

    response_measurement_id: str
    calibration_coordinates: tuple[float, ...]
    calibration_molar_masses: tuple[float, ...]
    calibration_id: str
    standard_source: str
    standard_ids: tuple[str, ...]
    distribution_mode: str
    coordinate_kind: str | None = None
    polynomial_degree: int = 1
    calibration_unit: str | None = None
    molar_mass_unit: str = "g/mol"

    @classmethod
    def create(
        cls,
        *,
        response_measurement_id: str,
        calibration_coordinates: Sequence[float],
        calibration_molar_masses: Sequence[float],
        calibration_id: str,
        standard_source: str,
        standard_ids: Sequence[str],
        distribution_mode: str,
        coordinate_kind: str | None = None,
        polynomial_degree: int = 1,
        calibration_unit: str | None = None,
        molar_mass_unit: str = "g/mol",
    ) -> "SECCalibrationSpec":
        return cls(
            response_measurement_id=str(response_measurement_id).strip(),
            calibration_coordinates=_finite_values(
                calibration_coordinates, name="SEC calibration coordinates"
            ),
            calibration_molar_masses=_finite_values(
                calibration_molar_masses, name="SEC calibration molar masses"
            ),
            calibration_id=str(calibration_id).strip(),
            standard_source=str(standard_source).strip(),
            standard_ids=tuple(str(item).strip() for item in standard_ids),
            distribution_mode=str(distribution_mode).strip().casefold(),
            coordinate_kind=(
                None if coordinate_kind is None else str(coordinate_kind).strip()
            ),
            polynomial_degree=int(polynomial_degree),
            calibration_unit=(
                None if calibration_unit is None else str(calibration_unit).strip()
            ),
            molar_mass_unit=str(molar_mass_unit).strip() or "g/mol",
        )

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "SECCalibrationSpec":
        if not isinstance(value, Mapping):
            raise TypeError("SEC analysis spec must be a mapping")
        return cls.create(
            response_measurement_id=value.get("response_measurement_id", ""),
            calibration_coordinates=value.get("calibration_coordinates", ()),
            calibration_molar_masses=value.get("calibration_molar_masses", ()),
            calibration_id=value.get("calibration_id", ""),
            standard_source=value.get("standard_source", ""),
            standard_ids=value.get("standard_ids", ()),
            distribution_mode=value.get("distribution_mode", ""),
            coordinate_kind=value.get("coordinate_kind"),
            polynomial_degree=value.get("polynomial_degree", 1),
            calibration_unit=value.get("calibration_unit"),
            molar_mass_unit=value.get("molar_mass_unit", "g/mol"),
        )

    def __post_init__(self) -> None:
        if not self.response_measurement_id:
            raise ValueError("SEC calibration response_measurement_id is required")
        if len(self.calibration_coordinates) != len(self.calibration_molar_masses):
            raise ValueError("SEC calibration coordinates and masses must have equal length")
        if not self.calibration_id:
            raise ValueError("SEC calibration_id is required")
        if not self.standard_source:
            raise ValueError("SEC standard_source is required")
        if len(self.standard_ids) != len(self.calibration_coordinates):
            raise ValueError("SEC calibration standard_ids must match standards")
        if not all(self.standard_ids) or len(set(self.standard_ids)) != len(self.standard_ids):
            raise ValueError("SEC calibration standard_ids must be unique and nonempty")
        if len(self.calibration_coordinates) < self.polynomial_degree + 1:
            raise ValueError("SEC calibration has too few standards for polynomial degree")
        if len(set(self.calibration_coordinates)) != len(self.calibration_coordinates):
            raise ValueError("SEC calibration coordinates must be unique")
        if any(value <= 0.0 for value in self.calibration_molar_masses):
            raise ValueError("SEC calibration molar masses must be positive")
        if self.distribution_mode not in _DISTRIBUTION_MODES:
            raise ValueError("SEC distribution_mode must be 'mass' or 'number'")
        if self.polynomial_degree < 1 or self.polynomial_degree > 3:
            raise ValueError("SEC calibration polynomial_degree must be between 1 and 3")
        if self.coordinate_kind == "":
            raise ValueError("SEC calibration coordinate_kind must be nonempty or null")
        if self.calibration_unit == "":
            raise ValueError("SEC calibration_unit must be nonempty or null")
        if self.molar_mass_unit != "g/mol":
            raise ValueError("SEC calibration molar_mass_unit must be g/mol")
        order = np.argsort(np.asarray(self.calibration_coordinates, dtype=float), kind="mergesort")
        ordered_log_mass = np.log10(np.asarray(self.calibration_molar_masses, dtype=float))[order]
        differences = np.diff(ordered_log_mass)
        if not (np.all(differences > 0.0) or np.all(differences < 0.0)):
            raise ValueError("SEC calibration molar masses must vary monotonically with coordinate")

    def to_dict(self) -> dict[str, Any]:
        return {
            "response_measurement_id": self.response_measurement_id,
            "calibration_coordinates": list(self.calibration_coordinates),
            "calibration_molar_masses": list(self.calibration_molar_masses),
            "calibration_id": self.calibration_id,
            "standard_source": self.standard_source,
            "standard_ids": list(self.standard_ids),
            "distribution_mode": self.distribution_mode,
            "coordinate_kind": self.coordinate_kind,
            "polynomial_degree": self.polynomial_degree,
            "calibration_unit": self.calibration_unit,
            "molar_mass_unit": self.molar_mass_unit,
        }


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
    analysis_spec: SECCalibrationSpec | Mapping[str, Any] | None = None,
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

    molecular_weight_summary = _molecular_weight_summary(
        coordinates,
        selected_signals,
        axis_kind=str(axis_kind),
        axis_unit=str(axis_unit),
        analysis_spec=analysis_spec,
    )
    if molecular_weight_summary.get("status") == "computed":
        prefix = "molecular_weight_summary"
        for name in ("Mn", "Mw", "Mz"):
            units[f"{prefix}.{name}"] = str(molecular_weight_summary["molar_mass_unit"])
            methods[f"{prefix}.{name}"] = "calibrated_log_molar_mass_weighted_moment"
            parameters[f"{prefix}.{name}"] = {
                "response_measurement_id": molecular_weight_summary["response_measurement_id"],
                "distribution_mode": molecular_weight_summary["distribution_mode"],
                "calibration_polynomial_degree": molecular_weight_summary["calibration_polynomial_degree"],
                "calibration_id": molecular_weight_summary["calibration_id"],
                "standard_source": molecular_weight_summary["calibration_standard_source"],
                "standard_ids": molecular_weight_summary["calibration_standard_ids"],
            }
        units[f"{prefix}.dispersity"] = "1"
        methods[f"{prefix}.dispersity"] = "molecular_weight_ratio_Mw_over_Mn"
        parameters[f"{prefix}.dispersity"] = {
            "numerator": "Mw",
            "denominator": "Mn",
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


def _molecular_weight_summary(
    coordinates: np.ndarray,
    signals: Sequence[SECSignalSeries],
    *,
    axis_kind: str,
    axis_unit: str,
    analysis_spec: SECCalibrationSpec | Mapping[str, Any] | None,
) -> dict[str, Any]:
    unavailable = {
        "status": "unavailable",
        "unavailable_reason": "calibration_and_distribution_semantics_required",
        "Mn": None,
        "Mw": None,
        "Mz": None,
        "dispersity": None,
    }
    if analysis_spec is None:
        return unavailable
    try:
        spec = (
            analysis_spec
            if type(analysis_spec) is SECCalibrationSpec
            else SECCalibrationSpec.from_mapping(analysis_spec)
        )
    except (TypeError, ValueError, KeyError):
        unavailable["unavailable_reason"] = "calibration_spec_invalid"
        return unavailable
    signal = next(
        (item for item in signals if item.measurement_id == spec.response_measurement_id),
        None,
    )
    if signal is None:
        unavailable["unavailable_reason"] = "calibration_response_measurement_missing"
        return unavailable
    if spec.coordinate_kind is not None and spec.coordinate_kind != axis_kind:
        unavailable["unavailable_reason"] = "calibration_coordinate_kind_mismatch"
        return unavailable
    if spec.calibration_unit is not None and spec.calibration_unit != axis_unit:
        unavailable["unavailable_reason"] = "calibration_coordinate_unit_mismatch"
        return unavailable
    x = coordinates if signal.x_values is None else np.asarray(signal.x_values, dtype=float)
    y = np.asarray(signal.values, dtype=float)
    if x.size < 2 or y.size != x.size or np.any(y < 0.0) or not np.any(y > 0.0):
        unavailable["unavailable_reason"] = "response_must_be_nonnegative_and_nonzero"
        return unavailable
    calibration_x = np.asarray(spec.calibration_coordinates, dtype=float)
    calibration_log_m = np.log10(np.asarray(spec.calibration_molar_masses, dtype=float))
    fit_coefficients = np.polyfit(calibration_x, calibration_log_m, spec.polynomial_degree)
    x_min = float(np.min(calibration_x))
    x_max = float(np.max(calibration_x))
    if float(np.min(x)) < x_min or float(np.max(x)) > x_max:
        unavailable["unavailable_reason"] = "calibration_extrapolation_not_allowed"
        return unavailable
    order = np.argsort(x, kind="mergesort")
    sorted_x = x[order]
    sorted_y = y[order]
    if np.any(np.diff(sorted_x) <= 0.0):
        unavailable["unavailable_reason"] = "response_coordinate_not_strictly_monotonic"
        return unavailable
    molar_mass = np.power(10.0, np.polyval(fit_coefficients, sorted_x))
    weights = np.asarray(sorted_y, dtype=float)
    area = float(np.trapezoid(weights, sorted_x))
    if not math.isfinite(area) or area <= 0.0:
        unavailable["unavailable_reason"] = "response_integral_not_positive"
        return unavailable
    if spec.distribution_mode == "mass":
        denominator_number = float(np.trapezoid(weights / molar_mass, sorted_x))
        denominator_mass = area
        numerator_mass = float(np.trapezoid(weights * molar_mass, sorted_x))
        numerator_z = float(np.trapezoid(weights * molar_mass**2, sorted_x))
        if denominator_number <= 0.0 or numerator_mass <= 0.0:
            unavailable["unavailable_reason"] = "molecular_weight_moment_not_positive"
            return unavailable
        mn = area / denominator_number
        mw = numerator_mass / denominator_mass
        mz = numerator_z / numerator_mass
    else:
        denominator_number = area
        numerator_number = float(np.trapezoid(weights * molar_mass, sorted_x))
        numerator_weight = float(np.trapezoid(weights * molar_mass**2, sorted_x))
        numerator_z = float(np.trapezoid(weights * molar_mass**3, sorted_x))
        if numerator_number <= 0.0 or numerator_weight <= 0.0:
            unavailable["unavailable_reason"] = "molecular_weight_moment_not_positive"
            return unavailable
        mn = numerator_number / denominator_number
        mw = numerator_weight / numerator_number
        mz = numerator_z / numerator_weight
    if not all(math.isfinite(value) and value > 0.0 for value in (mn, mw, mz)):
        unavailable["unavailable_reason"] = "molecular_weight_moment_invalid"
        return unavailable
    residuals = calibration_log_m - np.polyval(fit_coefficients, calibration_x)
    ss_res = float(np.sum(residuals**2))
    ss_tot = float(np.sum((calibration_log_m - np.mean(calibration_log_m)) ** 2))
    r_squared = None if ss_tot == 0.0 else 1.0 - ss_res / ss_tot
    return {
        "status": "computed",
        "Mn": float(mn),
        "Mw": float(mw),
        "Mz": float(mz),
        "dispersity": float(mw / mn),
        "molar_mass_unit": spec.molar_mass_unit,
        "response_measurement_id": spec.response_measurement_id,
        "distribution_mode": spec.distribution_mode,
        "calibration_coordinate_kind": axis_kind,
        "calibration_coordinate_unit": axis_unit,
        "calibration_polynomial_degree": spec.polynomial_degree,
        "calibration_id": spec.calibration_id,
        "calibration_standard_source": spec.standard_source,
        "calibration_standard_ids": spec.standard_ids,
        "calibration_coefficients_log10_molar_mass": tuple(float(value) for value in fit_coefficients),
        "calibration_r_squared": None if r_squared is None else float(r_squared),
        "calibration_residuals_log10": tuple(float(value) for value in residuals),
        "calibration_range": (x_min, x_max),
        "molar_mass_distribution": {
            "coordinate": tuple(float(value) for value in sorted_x),
            "molar_mass": tuple(float(value) for value in molar_mass),
            "response": tuple(float(value) for value in sorted_y),
            "response_normalized": tuple(float(value / area) for value in sorted_y),
            "coordinate_unit": axis_unit,
            "molar_mass_unit": spec.molar_mass_unit,
            "response_measurement_id": spec.response_measurement_id,
            "distribution_mode": spec.distribution_mode,
        },
    }


def _product_unit(signal_unit: str, axis_unit: str) -> str:
    if "unknown" in {signal_unit, axis_unit}:
        return "unknown"
    return f"{signal_unit}*{axis_unit}"


def _unavailable(reason: str) -> dict[str, str]:
    return {"status": "unavailable", "unavailable_reason": reason}


__all__ = [
    "SECCalibrationSpec",
    "SECProcessingOutcome",
    "SECSignalSeries",
    "analyze_sec_group",
]
