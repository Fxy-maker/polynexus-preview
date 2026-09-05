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
    "DMAProcessingConfig",
    "DMAProcessingOutcome",
    "DMASignalSeries",
    "analyze_dma_group",
]
