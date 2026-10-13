"""Deterministic, sample-neutral processing for canonical TGA curves."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.signal import find_peaks


_PROCESSING_VERSION = "tga.processing.v1"


@dataclass(frozen=True)
class TGAKineticsSpec:
    """Explicit semantics for multi-heating-rate diagnostic kinetics."""

    heating_rates: tuple[float, ...]
    conversion_levels: tuple[float, ...] = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
    gas_constant: float = 8.31446261815324
    curve_measurement_ids: tuple[str, ...] = ()
    heating_rate_unit: str = "K/min"

    @classmethod
    def create(cls, *, heating_rates: Sequence[float], conversion_levels: Sequence[float] | None = None, gas_constant: float = 8.31446261815324, curve_measurement_ids: Sequence[str] = (), heating_rate_unit: str = "K/min") -> "TGAKineticsSpec":
        rates = tuple(float(value) for value in heating_rates)
        levels = tuple(float(value) for value in (conversion_levels if conversion_levels is not None else cls.conversion_levels))
        if len(rates) < 2 or any(not math.isfinite(value) or value <= 0 for value in rates):
            raise ValueError("TGA kinetics requires at least two positive heating rates")
        if len(set(rates)) != len(rates):
            raise ValueError("TGA heating rates must be unique")
        if not levels or any(not math.isfinite(value) or not 0 < value < 1 for value in levels):
            raise ValueError("TGA conversion levels must be between zero and one")
        if any(a >= b for a, b in zip(levels, levels[1:])):
            raise ValueError("TGA conversion levels must be strictly increasing")
        gas = float(gas_constant)
        if not math.isfinite(gas) or gas <= 0:
            raise ValueError("TGA gas constant must be positive")
        ids = tuple(str(value).strip() for value in curve_measurement_ids)
        if ids and (len(ids) != len(rates) or any(not value for value in ids)):
            raise ValueError("TGA curve measurement ids must align with heating rates")
        rate_unit = str(heating_rate_unit).strip()
        if not rate_unit:
            raise ValueError("TGA heating rate unit must not be empty")
        return cls(rates, levels, gas, ids, rate_unit)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "TGAKineticsSpec":
        return cls.create(heating_rates=value.get("heating_rates", ()), conversion_levels=value.get("conversion_levels"), gas_constant=value.get("gas_constant", cls.gas_constant), curve_measurement_ids=value.get("curve_measurement_ids", value.get("measurement_ids", ())), heating_rate_unit=value.get("heating_rate_unit", "K/min"))

    def to_dict(self) -> dict[str, Any]:
        return {"heating_rates": list(self.heating_rates), "conversion_levels": list(self.conversion_levels), "gas_constant": self.gas_constant, "curve_measurement_ids": list(self.curve_measurement_ids), "heating_rate_unit": self.heating_rate_unit}


def analyze_tga_multirate_kinetics(
    peak_temperatures: Sequence[float],
    spec: TGAKineticsSpec | Mapping[str, Any],
) -> dict[str, Any]:
    """Fit a diagnostic Kissinger activation-energy candidate.

    The caller supplies one peak temperature per declared heating rate. No
    interpolation or material interpretation is inferred here.
    """
    kinetics = spec if isinstance(spec, TGAKineticsSpec) else TGAKineticsSpec.from_mapping(spec)
    temperatures = tuple(float(value) for value in peak_temperatures)
    if len(temperatures) != len(kinetics.heating_rates):
        return {"status": "unavailable", "unavailable_reason": "peak_temperature_count_mismatch"}
    if any(not math.isfinite(value) or value <= 0 for value in temperatures):
        return {"status": "unavailable", "unavailable_reason": "peak_temperature_invalid"}
    rates = np.asarray(kinetics.heating_rates, dtype=float)
    temp = np.asarray(temperatures, dtype=float)
    x = 1.0 / temp
    y = np.log(rates / temp**2)
    slope, intercept = np.polyfit(x, y, 1)
    activation_energy = float(-slope * kinetics.gas_constant)
    predicted = slope * x + intercept
    residuals = y - predicted
    ss_res = float(np.sum(residuals**2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = None if ss_tot == 0.0 else float(1.0 - ss_res / ss_tot)
    return {
        "status": "computed_with_warning",
        "method": "kissinger_linear_fit",
        "activation_energy_J_mol": activation_energy,
        "intercept": float(intercept),
        "r_squared": r_squared,
        "heating_rates": kinetics.heating_rates,
        "peak_temperatures_K": temperatures,
        "residuals": tuple(float(value) for value in residuals),
        "warnings": ("diagnostic_candidate_requires_independent_replay",),
        "parameters": kinetics.to_dict(),
    }


def analyze_tga_isoconversional_kinetics(
    curves: Sequence[Mapping[str, Any]],
    spec: TGAKineticsSpec | Mapping[str, Any],
) -> dict[str, Any]:
    """Fit diagnostic Ozawa–Flynn–Wall candidates at declared conversions."""
    kinetics = spec if isinstance(spec, TGAKineticsSpec) else TGAKineticsSpec.from_mapping(spec)
    if len(curves) != len(kinetics.heating_rates):
        return {"status": "unavailable", "unavailable_reason": "kinetics_curve_count_mismatch"}
    temperatures_at_conversion: dict[float, list[float]] = {
        level: [] for level in kinetics.conversion_levels
    }
    source_ids: list[str] = []
    for curve in curves:
        temperature = np.asarray(curve.get("temperature_K", ()), dtype=float)
        mass = np.asarray(curve.get("mass", ()), dtype=float)
        if temperature.ndim != 1 or mass.ndim != 1 or temperature.size != mass.size or temperature.size < 3:
            return {"status": "unavailable", "unavailable_reason": "kinetics_curve_invalid"}
        if not np.all(np.isfinite(temperature)) or not np.all(np.isfinite(mass)) or not np.all(np.diff(temperature) > 0.0):
            return {"status": "unavailable", "unavailable_reason": "kinetics_temperature_axis_invalid"}
        mass_span = float(mass[0] - mass[-1])
        if not math.isfinite(mass_span) or mass_span <= 0.0:
            return {"status": "unavailable", "unavailable_reason": "kinetics_mass_loss_required"}
        conversion = np.maximum.accumulate((mass[0] - mass) / mass_span)
        if float(conversion[-1]) <= 0.0:
            return {"status": "unavailable", "unavailable_reason": "kinetics_conversion_unavailable"}
        unique_conversion, unique_indices = np.unique(conversion, return_index=True)
        for level in kinetics.conversion_levels:
            if level < float(unique_conversion[0]) or level > float(unique_conversion[-1]):
                temperatures_at_conversion[level].append(float("nan"))
            else:
                temperatures_at_conversion[level].append(
                    float(np.interp(level, unique_conversion, temperature[unique_indices]))
                )
        source_ids.append(str(curve.get("measurement_id", "")))
    levels: dict[str, Any] = {}
    computed = 0
    rates = np.asarray(kinetics.heating_rates, dtype=float)
    for level in kinetics.conversion_levels:
        temperatures = np.asarray(temperatures_at_conversion[level], dtype=float)
        if not np.all(np.isfinite(temperatures)) or np.any(temperatures <= 0.0):
            levels[f"conversion_{level:.6g}"] = {
                "status": "unavailable",
                "unavailable_reason": "conversion_temperature_unavailable",
                "conversion": level,
            }
            continue
        x = 1.0 / temperatures
        y = np.log10(rates)
        slope, intercept = np.polyfit(x, y, 1)
        predicted = slope * x + intercept
        residuals = y - predicted
        total = float(np.sum((y - np.mean(y)) ** 2))
        residual_sum = float(np.sum(residuals**2))
        activation_energy = float(-slope * kinetics.gas_constant / 0.4567)
        record = {
            "status": "computed_with_warning",
            "conversion": level,
            "activation_energy_J_mol": activation_energy,
            "intercept": float(intercept),
            "r_squared": None if total == 0.0 else float(1.0 - residual_sum / total),
            "temperatures_K": tuple(float(value) for value in temperatures),
            "residuals": tuple(float(value) for value in residuals),
            "method": "ozawa_flynn_wall_linear_fit",
            "warnings": ("diagnostic_candidate_requires_independent_replay",),
        }
        levels[f"conversion_{level:.6g}"] = record
        computed += 1
    return {
        "status": "computed_with_warning" if computed else "unavailable",
        "unavailable_reason": None if computed else "no_conversion_level_computable",
        "method": "ozawa_flynn_wall_isoconversional",
        "computed_conversion_count": computed,
        "conversion_levels": levels,
        "source_measurement_ids": source_ids,
        "parameters": kinetics.to_dict(),
        "warnings": ("diagnostic_candidate_requires_independent_replay",) if computed else (),
    }


@dataclass(frozen=True)
class TGAProcessingConfig:
    """Explicit parameters for material-neutral TGA curve processing."""

    normalization_reference_points: int = 5
    dtg_window_points: int = 11
    dtg_polynomial_order: int = 2
    event_prominence_noise_factor: float = 3.0
    event_minimum_mass_loss_percent: float = 0.5
    residue_targets: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "normalization_reference_points",
            "dtg_window_points",
            "dtg_polynomial_order",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if self.dtg_polynomial_order >= self.dtg_window_points:
            raise ValueError("dtg_polynomial_order must be smaller than dtg_window_points")
        for name in (
            "event_prominence_noise_factor",
            "event_minimum_mass_loss_percent",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be numeric")
            if not math.isfinite(float(value)) or float(value) < 0.0:
                raise ValueError(f"{name} must be finite and nonnegative")
            object.__setattr__(self, name, float(value))
        if isinstance(self.residue_targets, (str, bytes, bytearray)):
            raise TypeError("residue_targets must be a sequence of finite coordinates")
        targets: list[float] = []
        for value in self.residue_targets:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError("residue_targets must contain numeric coordinates")
            target = float(value)
            if not math.isfinite(target):
                raise ValueError("residue_targets must contain finite coordinates")
            if target not in targets:
                targets.append(target)
        object.__setattr__(self, "residue_targets", tuple(targets))

    @classmethod
    def coerce(cls, value: Any) -> "TGAProcessingConfig":
        if value is None:
            return cls()
        if isinstance(value, cls):
            return value
        if not isinstance(value, Mapping):
            raise TypeError("TGA config must be TGAProcessingConfig, a mapping, or None")
        unknown = set(value).difference(cls.__dataclass_fields__)
        if unknown:
            raise ValueError(f"Unsupported TGA config field: {sorted(unknown)[0]}")
        return cls(**dict(value))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TGAProcessingOutcome:
    """One JSON-safe processed curve plus metric-manifest metadata."""

    metrics: Mapping[str, Any]
    units: Mapping[str, str]
    methods: Mapping[str, str]
    parameters: Mapping[str, Mapping[str, Any]]


def analyze_tga_curve(
    x_values: Sequence[float],
    mass_values: Sequence[float],
    *,
    axis_kind: str,
    axis_unit: str,
    signal_unit: str,
    config: TGAProcessingConfig,
) -> TGAProcessingOutcome:
    """Compute derived TGA quantities without interpreting sample chemistry."""

    x = np.asarray(x_values, dtype=float)
    mass = np.asarray(mass_values, dtype=float)
    if x.ndim != 1 or mass.ndim != 1 or x.size != mass.size or x.size < 2:
        raise ValueError("TGA processing requires equal one-dimensional arrays")
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(mass)):
        raise ValueError("TGA processing requires finite arrays")

    units: dict[str, str] = {"derived.x": str(axis_unit)}
    methods: dict[str, str] = {"derived.x": "canonical_source_values"}
    parameters: dict[str, Mapping[str, Any]] = {}
    metrics: dict[str, Any] = {
        "processing_version": _PROCESSING_VERSION,
        "axis_kind": str(axis_kind),
        "axis_unit": str(axis_unit),
        "source_signal_unit": str(signal_unit),
    }

    normalization, normalized = _normalize_mass(mass, signal_unit=signal_unit, config=config)
    metrics["normalization"] = normalization
    metrics["derived"] = {
        "x": tuple(float(value) for value in x),
        "normalized_mass_percent": (
            None if normalized is None else tuple(float(value) for value in normalized)
        ),
        "smoothed_mass_percent": None,
        "dtg": None,
    }
    normalization_parameters = {
        "requested_reference_points": config.normalization_reference_points,
        "used_reference_points": normalization.get("used_reference_points", 0),
    }
    if normalized is not None:
        normalized_paths = (
            "normalization.reference_mass",
            "normalization.initial_mass_percent",
            "normalization.final_mass_percent",
            "derived.normalized_mass_percent",
        )
        for path in normalized_paths:
            methods[path] = "initial_window_median"
            parameters[path] = normalization_parameters
        units["normalization.reference_mass"] = str(signal_unit)
        for path in normalized_paths[1:]:
            units[path] = "percent_initial_mass"

    if normalized is None:
        metrics["dtg"] = _unavailable("normalization_unavailable")
        metrics["mass_loss_events"] = _unavailable("dtg_unavailable")
        metrics["residue"] = _unavailable("normalization_unavailable")
        return TGAProcessingOutcome(metrics, units, methods, parameters)

    residue = _residue_metrics(
        x,
        normalized,
        axis_kind=str(axis_kind),
        axis_unit=str(axis_unit),
        targets=config.residue_targets,
    )
    metrics["residue"] = residue
    _add_residue_metadata(residue, units=units, methods=methods, parameters=parameters)

    if not np.all(np.diff(x) > 0.0):
        metrics["dtg"] = _unavailable("axis_not_strictly_increasing")
        metrics["mass_loss_events"] = _unavailable("dtg_unavailable")
        return TGAProcessingOutcome(metrics, units, methods, parameters)

    window = _resolved_window(
        point_count=int(x.size),
        requested=config.dtg_window_points,
        polynomial_order=config.dtg_polynomial_order,
    )
    if window is None:
        metrics["dtg"] = _unavailable("insufficient_points_for_local_polynomial")
        metrics["mass_loss_events"] = _unavailable("dtg_unavailable")
        return TGAProcessingOutcome(metrics, units, methods, parameters)

    smooth_mass, dtg = _local_polynomial_dtg(
        x,
        normalized,
        window_points=window,
        polynomial_order=config.dtg_polynomial_order,
    )
    metrics["derived"]["smoothed_mass_percent"] = tuple(
        float(value) for value in smooth_mass
    )
    metrics["derived"]["dtg"] = tuple(float(value) for value in dtg)
    rate_unit = _rate_unit(axis_unit)
    dtg_parameters = {
        "window_points": window,
        "requested_window_points": config.dtg_window_points,
        "polynomial_order": config.dtg_polynomial_order,
        "sign_convention": "-d(normalized_mass)/d(x)",
        "boundary_handling": "shifted_fixed_window",
        "coordinate_handling": "local_fit_uses_canonical_x_values",
    }
    metrics["dtg"] = {
        "status": "computed",
        "method": "local_polynomial_derivative",
        "parameters": dtg_parameters,
        "axis_unit": str(axis_unit),
        "rate_unit": rate_unit,
        "minimum_mass_loss_rate": float(np.min(dtg)),
        "maximum_mass_loss_rate": float(np.max(dtg)),
    }
    for path in (
        "derived.smoothed_mass_percent",
        "derived.dtg",
        "dtg.minimum_mass_loss_rate",
        "dtg.maximum_mass_loss_rate",
    ):
        units[path] = (
            "percent_initial_mass"
            if path == "derived.smoothed_mass_percent"
            else rate_unit
        )
        methods[path] = "local_polynomial_derivative"
        parameters[path] = dtg_parameters

    events = _event_metrics(
        x,
        smooth_mass,
        dtg,
        axis_unit=str(axis_unit),
        rate_unit=rate_unit,
        config=config,
    )
    metrics["mass_loss_events"] = events
    _add_event_metadata(events, units=units, methods=methods, parameters=parameters)
    return TGAProcessingOutcome(metrics, units, methods, parameters)


def _normalize_mass(
    mass: np.ndarray,
    *,
    signal_unit: str,
    config: TGAProcessingConfig,
) -> tuple[dict[str, Any], np.ndarray | None]:
    used = min(config.normalization_reference_points, int(mass.size))
    reference = float(np.median(mass[:used]))
    if reference <= 0.0:
        return _unavailable("normalization_reference_nonpositive"), None
    normalized = mass / reference * 100.0
    return {
        "status": "computed",
        "method": "initial_window_median",
        "requested_reference_points": config.normalization_reference_points,
        "used_reference_points": used,
        "canonical_reference_index_start": 0,
        "canonical_reference_index_end": used - 1,
        "reference_mass": reference,
        "source_signal_unit": str(signal_unit),
        "output_unit": "percent_initial_mass",
        "initial_mass_percent": float(normalized[0]),
        "final_mass_percent": float(normalized[-1]),
    }, normalized


def _resolved_window(
    *,
    point_count: int,
    requested: int,
    polynomial_order: int,
) -> int | None:
    window = min(requested, point_count)
    if window % 2 == 0:
        window -= 1
    minimum = polynomial_order + 2
    if minimum % 2 == 0:
        minimum += 1
    if window < minimum:
        return None
    return window


def _local_polynomial_dtg(
    x: np.ndarray,
    mass_percent: np.ndarray,
    *,
    window_points: int,
    polynomial_order: int,
) -> tuple[np.ndarray, np.ndarray]:
    half = window_points // 2
    smooth = np.empty_like(mass_percent, dtype=float)
    derivative = np.empty_like(mass_percent, dtype=float)
    last_start = int(x.size) - window_points
    for index in range(int(x.size)):
        start = min(max(index - half, 0), last_start)
        stop = start + window_points
        local_x = x[start:stop]
        local_mass = mass_percent[start:stop]
        scale = float(np.max(np.abs(local_x - x[index])))
        if scale <= 0.0:
            raise ValueError("Local polynomial coordinate window has zero span")
        local_coordinate = (local_x - x[index]) / scale
        coefficients = np.polynomial.polynomial.polyfit(
            local_coordinate,
            local_mass,
            polynomial_order,
        )
        smooth[index] = float(coefficients[0])
        derivative[index] = float(coefficients[1] / scale)
    return smooth, -derivative


def _event_metrics(
    x: np.ndarray,
    smooth_mass: np.ndarray,
    dtg: np.ndarray,
    *,
    axis_unit: str,
    rate_unit: str,
    config: TGAProcessingConfig,
) -> dict[str, Any]:
    centered = dtg - float(np.median(dtg))
    noise = float(1.4826 * np.median(np.abs(centered)))
    numerical_floor = float(np.finfo(float).eps * max(1.0, np.max(np.abs(dtg))))
    prominence_threshold = max(
        config.event_prominence_noise_factor * noise,
        numerical_floor,
    )
    peak_indices, properties = find_peaks(dtg, prominence=prominence_threshold)
    method_parameters = {
        "prominence_noise_factor": config.event_prominence_noise_factor,
        "robust_noise_estimate": noise,
        "prominence_threshold": prominence_threshold,
        "minimum_interval_mass_loss_percent": config.event_minimum_mass_loss_percent,
        "boundary_method": "scipy_peak_prominence_bases",
    }
    accepted: list[dict[str, Any]] = []
    for peak_index, left_index, right_index, prominence in zip(
        peak_indices,
        properties.get("left_bases", ()),
        properties.get("right_bases", ()),
        properties.get("prominences", ()),
        strict=True,
    ):
        interval_loss = float(smooth_mass[left_index] - smooth_mass[right_index])
        if dtg[peak_index] <= 0.0 or interval_loss < config.event_minimum_mass_loss_percent:
            continue
        warnings: list[str] = []
        if int(left_index) == 0:
            warnings.append("event_onset_reaches_record_boundary")
        if int(right_index) == int(x.size) - 1:
            warnings.append("event_endset_reaches_record_boundary")
        accepted.append(
            {
                "status": "computed_with_warning" if warnings else "computed",
                "method": "dtg_peak_prominence_bases",
                "axis_unit": axis_unit,
                "rate_unit": rate_unit,
                "parameters": method_parameters,
                "canonical_index_start": int(left_index),
                "peak_index": int(peak_index),
                "canonical_index_end": int(right_index),
                "onset_candidate_x": float(x[left_index]),
                "peak_x": float(x[peak_index]),
                "endset_candidate_x": float(x[right_index]),
                "peak_mass_loss_rate": float(dtg[peak_index]),
                "peak_prominence": float(prominence),
                "interval_mass_loss_percent": interval_loss,
                "warnings": warnings,
            }
        )
    result: dict[str, Any] = {
        "status": "computed",
        "method": "dtg_peak_prominence_bases",
        "parameters": method_parameters,
        "event_count": len(accepted),
    }
    for index, event in enumerate(accepted, start=1):
        result[f"event_{index:03d}"] = event
    return result


def _residue_metrics(
    x: np.ndarray,
    normalized_mass: np.ndarray,
    *,
    axis_kind: str,
    axis_unit: str,
    targets: Sequence[float],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "computed",
        "method": "normalized_mass_at_recorded_or_interpolated_coordinate",
        "final_recorded_x": float(x[-1]),
        "final_recorded_mass_percent": float(normalized_mass[-1]),
        "axis_unit": axis_unit,
        "mass_unit": "percent_initial_mass",
    }
    increasing = bool(np.all(np.diff(x) > 0.0))
    for index, target in enumerate(targets, start=1):
        key = f"target_{index:03d}"
        base = {"requested_x": float(target), "axis_unit": axis_unit}
        if axis_kind != "temperature":
            result[key] = {
                "status": "unavailable",
                **base,
                "unavailable_reason": "temperature_axis_required",
            }
        elif axis_unit == "unknown":
            result[key] = {
                "status": "unavailable",
                **base,
                "unavailable_reason": "temperature_unit_unknown",
            }
        elif not increasing:
            result[key] = {
                "status": "unavailable",
                **base,
                "unavailable_reason": "axis_not_strictly_increasing",
            }
        elif target < x[0] or target > x[-1]:
            result[key] = {
                "status": "unavailable",
                **base,
                "unavailable_reason": "target_outside_recorded_axis",
            }
        else:
            result[key] = {
                "status": "computed",
                **base,
                "mass_percent": float(np.interp(target, x, normalized_mass)),
                "mass_unit": "percent_initial_mass",
                "method": "linear_interpolation_no_extrapolation",
            }
    return result


def _add_residue_metadata(
    residue: Mapping[str, Any],
    *,
    units: dict[str, str],
    methods: dict[str, str],
    parameters: dict[str, Mapping[str, Any]],
) -> None:
    units["residue.final_recorded_x"] = str(residue["axis_unit"])
    units["residue.final_recorded_mass_percent"] = "percent_initial_mass"
    methods["residue.final_recorded_x"] = "canonical_final_recorded_coordinate"
    methods["residue.final_recorded_mass_percent"] = "initial_window_median"
    for key, item in residue.items():
        if not key.startswith("target_") or not isinstance(item, Mapping):
            continue
        path = f"residue.{key}"
        units[f"{path}.requested_x"] = str(item["axis_unit"])
        if item.get("status") == "computed":
            units[f"{path}.mass_percent"] = "percent_initial_mass"
            methods[f"{path}.mass_percent"] = "linear_interpolation_no_extrapolation"
            parameters[f"{path}.mass_percent"] = {
                "requested_x": item["requested_x"],
                "extrapolation": "forbidden",
            }


def _add_event_metadata(
    events: Mapping[str, Any],
    *,
    units: dict[str, str],
    methods: dict[str, str],
    parameters: dict[str, Mapping[str, Any]],
) -> None:
    event_parameters = dict(events.get("parameters", {}))
    for key, event in events.items():
        if not key.startswith("event_") or not isinstance(event, Mapping):
            continue
        prefix = f"mass_loss_events.{key}"
        for field in ("onset_candidate_x", "peak_x", "endset_candidate_x"):
            path = f"{prefix}.{field}"
            units[path] = str(event["axis_unit"])
            methods[path] = "dtg_peak_prominence_bases"
            parameters[path] = event_parameters
        for field in ("peak_mass_loss_rate", "peak_prominence"):
            path = f"{prefix}.{field}"
            units[path] = str(event["rate_unit"])
            methods[path] = "dtg_peak_prominence_bases"
            parameters[path] = event_parameters
        loss_path = f"{prefix}.interval_mass_loss_percent"
        units[loss_path] = "percent_initial_mass"
        methods[loss_path] = "endpoint_difference_on_local_polynomial_mass"
        parameters[loss_path] = event_parameters


def _rate_unit(axis_unit: str) -> str:
    normalized = str(axis_unit).strip() or "unknown"
    return f"percent_initial_mass_per_{normalized}"


def _unavailable(reason: str) -> dict[str, str]:
    return {"status": "unavailable", "unavailable_reason": str(reason)}


__all__ = [
    "TGAKineticsSpec",
    "analyze_tga_multirate_kinetics",
    "analyze_tga_isoconversional_kinetics",
    "TGAProcessingConfig",
    "TGAProcessingOutcome",
    "analyze_tga_curve",
]
