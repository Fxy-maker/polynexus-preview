"""Deterministic, sample-neutral processing for canonical DMA signal groups."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.signal import find_peaks


_PROCESSING_VERSION = "dma.processing.v1"
_MODULUS_UNIT_SCALE_PA = {
    "pa": 1.0,
    "kpa": 1.0e3,
    "mpa": 1.0e6,
    "gpa": 1.0e9,
}
_MODULUS_BASES = frozenset({"tensile", "shear", "unspecified"})


@dataclass(frozen=True)
class DMATTSSpec:
    """Explicit temperature/frequency shifting semantics for a diagnostic TTS."""

    reference_temperature: float
    temperatures: tuple[float, ...]
    shift_factors: tuple[float, ...]
    frequency_unit: str = "Hz"
    curve_measurement_ids: tuple[str, ...] = ()
    shift_mode: str = "explicit"
    modulus_unit: str = "unknown"

    @classmethod
    def create(cls, *, reference_temperature: float, temperatures: Sequence[float], shift_factors: Sequence[float] = (), frequency_unit: str = "Hz", curve_measurement_ids: Sequence[str] = (), shift_mode: str | None = None, modulus_unit: str = "unknown") -> "DMATTSSpec":
        ref = float(reference_temperature)
        temps = tuple(float(value) for value in temperatures)
        shifts = tuple(float(value) for value in shift_factors)
        if not math.isfinite(ref) or not temps:
            raise ValueError("DMA TTS reference and temperature vector are required")
        mode = str(shift_mode or ("explicit" if shifts else "overlap_least_squares")).strip().casefold()
        if mode not in {"explicit", "overlap_least_squares"}:
            raise ValueError("DMA TTS shift mode is unsupported")
        if mode == "explicit" and len(temps) != len(shifts):
            raise ValueError("DMA TTS temperature and shift vectors are required")
        if mode == "overlap_least_squares" and shifts and len(temps) != len(shifts):
            raise ValueError("DMA TTS initial shift factors must align with temperatures")
        if any(not math.isfinite(value) for value in (*temps, *shifts)) or any(value <= 0 for value in shifts):
            raise ValueError("DMA TTS temperatures must be finite and shift factors positive")
        if len(set(temps)) != len(temps):
            raise ValueError("DMA TTS temperatures must be unique")
        if ref not in temps:
            raise ValueError("DMA TTS reference temperature must be present in temperatures")
        ids = tuple(str(value).strip() for value in curve_measurement_ids)
        if ids and (len(ids) != len(temps) or any(not value for value in ids)):
            raise ValueError("DMA TTS curve measurement ids must align with temperatures")
        return cls(ref, temps, shifts, str(frequency_unit).strip() or "Hz", ids, mode, str(modulus_unit).strip() or "unknown")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "DMATTSSpec":
        return cls.create(reference_temperature=value.get("reference_temperature"), temperatures=value.get("temperatures", ()), shift_factors=value.get("shift_factors", ()), frequency_unit=value.get("frequency_unit", "Hz"), curve_measurement_ids=value.get("curve_measurement_ids", value.get("measurement_ids", ())), shift_mode=value.get("shift_mode"), modulus_unit=value.get("modulus_unit", "unknown"))

    def to_dict(self) -> dict[str, Any]:
        return {"reference_temperature": self.reference_temperature, "temperatures": list(self.temperatures), "shift_factors": list(self.shift_factors), "frequency_unit": self.frequency_unit, "curve_measurement_ids": list(self.curve_measurement_ids), "shift_mode": self.shift_mode, "modulus_unit": self.modulus_unit}


def build_dma_master_curve(curves: Sequence[Mapping[str, Any]], spec: DMATTSSpec | Mapping[str, Any]) -> dict[str, Any]:
    """Build a diagnostic horizontally shifted DMA master-curve candidate."""
    tts = spec if isinstance(spec, DMATTSSpec) else DMATTSSpec.from_mapping(spec)
    by_temperature = {float(curve.get("temperature")): curve for curve in curves}
    if any(temp not in by_temperature for temp in tts.temperatures):
        return {"status": "unavailable", "unavailable_reason": "tts_temperature_curve_missing"}
    shifts = tts.shift_factors
    shift_diagnostics: tuple[dict[str, Any], ...] = ()
    if tts.shift_mode == "overlap_least_squares":
        fitted = _fit_dma_shift_factors(by_temperature, tts)
        if fitted.get("status") == "unavailable":
            return fitted
        shifts = tuple(float(value) for value in fitted["shift_factors"])
        shift_diagnostics = tuple(fitted["diagnostics"])
    points: list[dict[str, float]] = []
    for temperature, shift in zip(tts.temperatures, shifts, strict=True):
        curve = by_temperature[temperature]
        frequencies = tuple(float(value) for value in curve.get("frequency", ()))
        values = tuple(float(value) for value in curve.get("modulus", ()))
        if len(frequencies) != len(values) or len(frequencies) < 2 or any(not math.isfinite(value) or value <= 0 for value in frequencies) or any(not math.isfinite(value) for value in values):
            return {"status": "unavailable", "unavailable_reason": "tts_curve_invalid"}
        points.extend({"temperature": temperature, "frequency": frequency * shift, "modulus": modulus} for frequency, modulus in zip(frequencies, values, strict=True))
    points.sort(key=lambda item: item["frequency"])
    curve_units = {str(item.get("modulus_unit", "unknown")) for item in by_temperature.values()}
    resolved_modulus_unit = tts.modulus_unit
    if resolved_modulus_unit == "unknown" and len(curve_units) == 1:
        resolved_modulus_unit = next(iter(curve_units))
    parameters = tts.to_dict()
    parameters["resolved_shift_factors"] = list(shifts)
    return {"status": "computed_with_warning", "method": "horizontal_frequency_shift", "reference_temperature": tts.reference_temperature, "frequency_unit": tts.frequency_unit, "modulus_unit": resolved_modulus_unit, "shift_mode": tts.shift_mode, "shift_factors": shifts, "shift_diagnostics": shift_diagnostics, "points": tuple(points), "parameters": parameters, "warnings": ("diagnostic_candidate_requires_independent_replay",)}


def _fit_dma_shift_factors(by_temperature: Mapping[float, Mapping[str, Any]], spec: DMATTSSpec) -> dict[str, Any]:
    reference = by_temperature.get(spec.reference_temperature)
    if reference is None:
        return {"status": "unavailable", "unavailable_reason": "tts_reference_temperature_curve_missing"}
    reference_frequency = np.asarray(reference.get("frequency", ()), dtype=float)
    reference_modulus = np.asarray(reference.get("modulus", ()), dtype=float)
    if reference_frequency.size < 3 or reference_frequency.size != reference_modulus.size or np.any(reference_frequency <= 0.0) or np.any(reference_modulus <= 0.0):
        return {"status": "unavailable", "unavailable_reason": "tts_reference_curve_invalid"}
    ref_order = np.argsort(reference_frequency, kind="mergesort")
    ref_x = np.log10(reference_frequency[ref_order])
    ref_y = np.log10(reference_modulus[ref_order])
    shifts: list[float] = []
    diagnostics: list[dict[str, Any]] = []
    for temperature in spec.temperatures:
        if temperature == spec.reference_temperature:
            shifts.append(1.0)
            diagnostics.append({"temperature": temperature, "log10_shift": 0.0, "overlap_points": int(ref_x.size), "rmse": 0.0})
            continue
        curve = by_temperature[temperature]
        frequency = np.asarray(curve.get("frequency", ()), dtype=float)
        modulus = np.asarray(curve.get("modulus", ()), dtype=float)
        if frequency.size < 3 or frequency.size != modulus.size or np.any(frequency <= 0.0) or np.any(modulus <= 0.0):
            return {"status": "unavailable", "unavailable_reason": "tts_curve_invalid"}
        order = np.argsort(frequency, kind="mergesort")
        curve_x = np.log10(frequency[order])
        curve_y = np.log10(modulus[order])
        candidates: list[tuple[float, int, float]] = []
        for log_shift in np.linspace(-12.0, 12.0, 481):
            shifted_x = curve_x + float(log_shift)
            mask = (shifted_x >= ref_x[0]) & (shifted_x <= ref_x[-1])
            overlap = int(np.count_nonzero(mask))
            if overlap < 2:
                continue
            expected = np.interp(shifted_x[mask], ref_x, ref_y)
            rmse = float(np.sqrt(np.mean((curve_y[mask] - expected) ** 2)))
            candidates.append((rmse, -overlap, float(log_shift)))
        if not candidates:
            return {"status": "unavailable", "unavailable_reason": "tts_curve_overlap_missing"}
        rmse, negative_overlap, log_shift = min(candidates)
        shifts.append(float(10.0**log_shift))
        diagnostics.append({"temperature": temperature, "log10_shift": log_shift, "overlap_points": -negative_overlap, "rmse_log10_modulus": rmse})
    return {"status": "computed_with_warning", "shift_factors": tuple(shifts), "diagnostics": tuple(diagnostics)}


@dataclass(frozen=True)
class DMAProcessingConfig:
    """Explicit parameters for material-neutral DMA response candidates."""

    peak_prominence_fraction: float = 0.02
    peak_minimum_prominence: float = 0.0

    def __post_init__(self) -> None:
        for name in ("peak_prominence_fraction", "peak_minimum_prominence"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be numeric")
            numeric = float(value)
            if not math.isfinite(numeric) or numeric < 0.0:
                raise ValueError(f"{name} must be finite and nonnegative")
            object.__setattr__(self, name, numeric)

    @classmethod
    def coerce(cls, value: Any) -> "DMAProcessingConfig":
        if value is None:
            return cls()
        if isinstance(value, cls):
            return value
        if not isinstance(value, Mapping):
            raise TypeError("DMA config must be DMAProcessingConfig, a mapping, or None")
        unknown = set(value).difference(cls.__dataclass_fields__)
        if unknown:
            raise ValueError(f"Unsupported DMA config field: {sorted(unknown)[0]}")
        return cls(**dict(value))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DMASignalSeries:
    """One immutable canonical DMA signal used by a group calculation."""

    measurement_id: str
    signal_kind: str
    modulus_basis: str
    unit: str
    values: tuple[float, ...]
    x_values: tuple[float, ...] | None = None

    def __post_init__(self) -> None:
        for name in ("measurement_id", "signal_kind", "unit"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a nonempty string")
        if self.modulus_basis not in _MODULUS_BASES:
            raise ValueError("modulus_basis must be tensile, shear, or unspecified")
        if len(self.values) < 2:
            raise ValueError("DMA signals require at least two points")
        if not all(math.isfinite(value) for value in self.values):
            raise ValueError("DMA signal values must be finite")
        if self.x_values is not None:
            if len(self.x_values) != len(self.values):
                raise ValueError("DMA signal coordinates and values must have equal lengths")
            if not all(math.isfinite(value) for value in self.x_values):
                raise ValueError("DMA signal coordinates must be finite")

    @classmethod
    def create(
        cls,
        *,
        measurement_id: str,
        signal_kind: str,
        modulus_basis: str,
        unit: str,
        values: Sequence[float],
        x_values: Sequence[float] | None = None,
    ) -> "DMASignalSeries":
        return cls(
            measurement_id=str(measurement_id),
            signal_kind=str(signal_kind),
            modulus_basis=str(modulus_basis),
            unit=str(unit),
            values=tuple(float(value) for value in values),
            x_values=(
                None if x_values is None else tuple(float(value) for value in x_values)
            ),
        )


@dataclass(frozen=True)
class DMAProcessingOutcome:
    """One JSON-safe processed signal group plus manifest metadata."""

    metrics: Mapping[str, Any]
    units: Mapping[str, str]
    methods: Mapping[str, str]
    parameters: Mapping[str, Mapping[str, Any]]


def analyze_dma_group(
    x_values: Sequence[float],
    *,
    axis_kind: str,
    axis_unit: str,
    signals: Sequence[DMASignalSeries],
    config: DMAProcessingConfig | Mapping[str, Any] | None = None,
) -> DMAProcessingOutcome:
    """Derive compatible DMA relationships without assigning transition meaning."""

    x = np.asarray(x_values, dtype=float)
    if x.ndim != 1 or x.size < 2 or not np.all(np.isfinite(x)):
        raise ValueError("DMA processing requires a finite one-dimensional axis")
    signal_items = tuple(signals)
    if not signal_items or not all(isinstance(item, DMASignalSeries) for item in signal_items):
        raise TypeError("signals must contain DMASignalSeries values")
    processing_config = DMAProcessingConfig.coerce(config)

    units: dict[str, str] = {}
    methods: dict[str, str] = {}
    parameters: dict[str, Mapping[str, Any]] = {}
    source_signals: dict[str, dict[str, Any]] = {}
    for signal in signal_items:
        signal_x = x if signal.x_values is None else np.asarray(signal.x_values, dtype=float)
        source_signals[signal.measurement_id] = {
            "signal_kind": signal.signal_kind,
            "modulus_basis": signal.modulus_basis,
            "unit": signal.unit,
            "axis_values": tuple(float(value) for value in signal_x),
            "values": signal.values,
        }
        units[f"source_signals.{signal.measurement_id}.axis_values"] = str(axis_unit)
        methods[f"source_signals.{signal.measurement_id}.axis_values"] = "canonical_source_values"
        path = f"source_signals.{signal.measurement_id}.values"
        units[path] = signal.unit
        methods[path] = "canonical_source_values"

    derived: dict[str, dict[str, Any]] = {}
    modulus_bases = sorted(
        {
            item.modulus_basis
            for item in signal_items
            if item.signal_kind in {"storage_modulus", "loss_modulus"}
        }
    )
    for basis in modulus_bases:
        storage = _signals_for(signal_items, "storage_modulus", basis)
        loss = _signals_for(signal_items, "loss_modulus", basis)
        derived[basis] = _derive_tan_delta(storage, loss, reference_x=x)
        path = f"derived_tan_delta.{basis}.values"
        record = derived[basis]
        if record.get("status") in {"computed", "computed_with_warning"}:
            units[path] = "1"
            methods[path] = str(record["method"])
            parameters[path] = dict(record["parameters"])

    candidates: dict[str, dict[str, Any]] = {}
    source_tan_delta = tuple(
        item for item in signal_items if item.signal_kind == "tan_delta"
    )
    for index, signal in enumerate(source_tan_delta, start=1):
        key = "source_tan_delta" if len(source_tan_delta) == 1 else f"source_tan_delta_{index:03d}"
        signal_x = x if signal.x_values is None else np.asarray(signal.x_values, dtype=float)
        candidates[key] = _response_peak_candidates(
            signal_x,
            signal.values,
            axis_kind=str(axis_kind),
            axis_unit=str(axis_unit),
            config=processing_config,
        )
        _add_candidate_metadata(
            candidates[key],
            path=f"transition_candidates.{key}",
            units=units,
            methods=methods,
            parameters=parameters,
        )
    for basis, record in derived.items():
        key = f"derived_tan_delta_{basis}"
        values = record.get("values")
        if record.get("status") not in {"computed", "computed_with_warning"} or values is None:
            candidates[key] = _unavailable("tan_delta_series_unavailable")
            continue
        candidates[key] = _response_peak_candidates(
            x,
            values,
            axis_kind=str(axis_kind),
            axis_unit=str(axis_unit),
            config=processing_config,
        )
        _add_candidate_metadata(
            candidates[key],
            path=f"transition_candidates.{key}",
            units=units,
            methods=methods,
            parameters=parameters,
        )

    metrics = {
        "processing_version": _PROCESSING_VERSION,
        "axis_kind": str(axis_kind),
        "axis_unit": str(axis_unit),
        "source_signals": source_signals,
        "derived_tan_delta": derived,
        "transition_candidates": candidates,
    }
    return DMAProcessingOutcome(metrics, units, methods, parameters)


def _signals_for(
    signals: Sequence[DMASignalSeries],
    signal_kind: str,
    modulus_basis: str,
) -> tuple[DMASignalSeries, ...]:
    return tuple(
        item
        for item in signals
        if item.signal_kind == signal_kind and item.modulus_basis == modulus_basis
    )


def _derive_tan_delta(
    storage: Sequence[DMASignalSeries],
    loss: Sequence[DMASignalSeries],
    *,
    reference_x: np.ndarray,
) -> dict[str, Any]:
    if not storage:
        return _unavailable("storage_modulus_missing_for_basis")
    if not loss:
        return _unavailable("loss_modulus_missing_for_basis")
    if len(storage) != 1:
        return _unavailable("storage_modulus_ambiguous_for_basis")
    if len(loss) != 1:
        return _unavailable("loss_modulus_ambiguous_for_basis")
    storage_signal = storage[0]
    loss_signal = loss[0]
    storage_x = _series_x(storage_signal, reference_x)
    loss_x = _series_x(loss_signal, reference_x)
    if (
        storage_x.shape != reference_x.shape
        or loss_x.shape != reference_x.shape
        or not np.array_equal(storage_x, reference_x)
        or not np.array_equal(loss_x, reference_x)
    ):
        return _unavailable("signal_axes_incompatible")
    unit_factor = _modulus_unit_factor(loss_signal.unit, storage_signal.unit)
    if unit_factor is None:
        return _unavailable("modulus_units_incompatible")

    storage_values = np.asarray(storage_signal.values, dtype=float)
    loss_values = np.asarray(loss_signal.values, dtype=float)
    valid = storage_values != 0.0
    parameters = {
        "storage_measurement_id": storage_signal.measurement_id,
        "loss_measurement_id": loss_signal.measurement_id,
        "storage_unit": storage_signal.unit,
        "loss_unit": loss_signal.unit,
        "loss_to_storage_unit_factor": unit_factor,
        "zero_denominator_policy": "preserve_point_as_unavailable",
    }
    values: list[float | None] = []
    for index, is_valid in enumerate(valid):
        values.append(
            float(loss_values[index] * unit_factor / storage_values[index])
            if bool(is_valid)
            else None
        )
    warnings = (
        ("storage_modulus_zero_at_some_points",)
        if np.any(~valid) and np.any(valid)
        else ()
    )
    if not np.any(valid):
        return {
            **_unavailable("storage_modulus_zero_at_all_points"),
            "values": tuple(values),
            "validity_mask": tuple(False for _ in values),
            "unit": "1",
            "method": "loss_modulus_divided_by_storage_modulus",
            "parameters": parameters,
        }
    return {
        "status": "computed_with_warning" if warnings else "computed",
        "values": tuple(values),
        "validity_mask": tuple(bool(value) for value in valid),
        "unit": "1",
        "method": "loss_modulus_divided_by_storage_modulus",
        "parameters": parameters,
        "warnings": warnings,
    }


def _modulus_unit_factor(source_unit: str, target_unit: str) -> float | None:
    source_scale = _MODULUS_UNIT_SCALE_PA.get(source_unit.strip().casefold())
    target_scale = _MODULUS_UNIT_SCALE_PA.get(target_unit.strip().casefold())
    if source_scale is None or target_scale is None:
        return None
    return float(source_scale / target_scale)


def _series_x(signal: DMASignalSeries, reference_x: np.ndarray) -> np.ndarray:
    if signal.x_values is None:
        return reference_x
    return np.asarray(signal.x_values, dtype=float)


def _response_peak_candidates(
    x: np.ndarray,
    values: Sequence[float | None],
    *,
    axis_kind: str,
    axis_unit: str,
    config: DMAProcessingConfig,
) -> dict[str, Any]:
    if axis_kind != "temperature":
        return _unavailable("temperature_axis_required")
    numeric = np.asarray(
        [np.nan if value is None else float(value) for value in values],
        dtype=float,
    )
    finite = np.isfinite(numeric)
    if np.count_nonzero(finite) < 3:
        return _unavailable("insufficient_valid_points_for_peak_detection")
    value_span = float(np.max(numeric[finite]) - np.min(numeric[finite]))
    prominence = max(
        config.peak_minimum_prominence,
        config.peak_prominence_fraction * value_span,
        float(np.finfo(float).eps * max(1.0, np.max(np.abs(numeric[finite])))),
    )
    method_parameters = {
        "peak_prominence_fraction": config.peak_prominence_fraction,
        "peak_minimum_prominence": config.peak_minimum_prominence,
        "resolved_minimum_prominence": prominence,
        "invalid_point_handling": "split_contiguous_valid_segments",
    }
    accepted: list[dict[str, Any]] = []
    for start, stop in _contiguous_true_ranges(finite):
        if stop - start < 3:
            continue
        segment = numeric[start:stop]
        peak_indices, properties = find_peaks(segment, prominence=prominence)
        for peak_index, left_base, right_base, peak_prominence in zip(
            peak_indices,
            properties.get("left_bases", ()),
            properties.get("right_bases", ()),
            properties.get("prominences", ()),
            strict=True,
        ):
            absolute_peak = start + int(peak_index)
            absolute_left = start + int(left_base)
            absolute_right = start + int(right_base)
            accepted.append(
                {
                    "status": "computed",
                    "method": "response_peak_prominence",
                    "parameters": method_parameters,
                    "interpretation": "response_peak_candidate_not_tg",
                    "axis_unit": axis_unit,
                    "canonical_index_start": absolute_left,
                    "peak_index": absolute_peak,
                    "canonical_index_end": absolute_right,
                    "onset_candidate_x": float(x[absolute_left]),
                    "peak_x": float(x[absolute_peak]),
                    "endset_candidate_x": float(x[absolute_right]),
                    "peak_value": float(numeric[absolute_peak]),
                    "peak_prominence": float(peak_prominence),
                }
            )
    result: dict[str, Any] = {
        "status": "computed",
        "method": "response_peak_prominence",
        "parameters": method_parameters,
        "candidate_count": len(accepted),
    }
    for index, candidate in enumerate(accepted, start=1):
        result[f"candidate_{index:03d}"] = candidate
    return result


def _contiguous_true_ranges(mask: np.ndarray) -> tuple[tuple[int, int], ...]:
    ranges: list[tuple[int, int]] = []
    start: int | None = None
    for index, value in enumerate(mask):
        if bool(value) and start is None:
            start = index
        elif not bool(value) and start is not None:
            ranges.append((start, index))
            start = None
    if start is not None:
        ranges.append((start, int(mask.size)))
    return tuple(ranges)


def _add_candidate_metadata(
    candidates: Mapping[str, Any],
    *,
    path: str,
    units: dict[str, str],
    methods: dict[str, str],
    parameters: dict[str, Mapping[str, Any]],
) -> None:
    candidate_parameters = dict(candidates.get("parameters", {}))
    for key, candidate in candidates.items():
        if not key.startswith("candidate_") or not isinstance(candidate, Mapping):
            continue
        candidate_path = f"{path}.{key}"
        for field in ("onset_candidate_x", "peak_x", "endset_candidate_x"):
            units[f"{candidate_path}.{field}"] = str(candidate["axis_unit"])
            methods[f"{candidate_path}.{field}"] = "response_peak_prominence"
            parameters[f"{candidate_path}.{field}"] = candidate_parameters
        methods[f"{candidate_path}.peak_value"] = "response_peak_prominence"
        parameters[f"{candidate_path}.peak_value"] = candidate_parameters


def _unavailable(reason: str) -> dict[str, str]:
    return {"status": "unavailable", "unavailable_reason": reason}


__all__ = [
    "DMATTSSpec",
    "build_dma_master_curve",
    "DMAProcessingConfig",
    "DMAProcessingOutcome",
    "DMASignalSeries",
    "analyze_dma_group",
]
