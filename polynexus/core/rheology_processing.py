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
_STRAIN_SCALE_DIMENSIONLESS = {
    "1": 1.0,
    "fraction": 1.0,
    "%": 0.01,
    "percent": 0.01,
}
_YIELD_MODELS = frozenset({"bingham", "herschel_bulkley"})


@dataclass(frozen=True)
class RheologyAdvancedSpec:
    """Explicit requests for sample-neutral time/frequency comparisons."""

    reference_temperature: float | None = None
    temperatures: tuple[float, ...] = ()
    shift_factors: tuple[float, ...] = ()
    model: str = ""

    @classmethod
    def create(cls, *, reference_temperature: float | None = None, temperatures: Sequence[float] = (), shift_factors: Sequence[float] = (), model: str = "") -> "RheologyAdvancedSpec":
        temps, shifts = tuple(float(v) for v in temperatures), tuple(float(v) for v in shift_factors)
        if len(temps) != len(shifts):
            raise ValueError("rheology temperatures and shift factors must align")
        if any(not math.isfinite(v) for v in (*temps, *shifts)) or any(v <= 0 for v in shifts):
            raise ValueError("rheology shift factors must be finite and positive")
        return cls(None if reference_temperature is None else float(reference_temperature), temps, shifts, str(model).strip())

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RheologyAdvancedSpec":
        return cls.create(reference_temperature=value.get("reference_temperature"), temperatures=value.get("temperatures", ()), shift_factors=value.get("shift_factors", ()), model=value.get("model", ""))

    def to_dict(self) -> dict[str, Any]:
        return {"reference_temperature": self.reference_temperature, "temperatures": list(self.temperatures), "shift_factors": list(self.shift_factors), "model": self.model}


def compare_cox_merz(frequency: Sequence[float], complex_viscosity: Sequence[float], shear_rate: Sequence[float], steady_viscosity: Sequence[float]) -> dict[str, Any]:
    """Return pointwise Cox–Merz diagnostic differences on matching axes."""
    if not (len(frequency) == len(complex_viscosity) == len(shear_rate) == len(steady_viscosity)):
        return {"status": "unavailable", "unavailable_reason": "cox_merz_series_length_mismatch"}
    residuals = tuple(float(a - b) for a, b in zip(complex_viscosity, steady_viscosity, strict=True))
    return {"status": "computed_with_warning", "method": "cox_merz_pointwise_comparison", "frequency": tuple(float(v) for v in frequency), "shear_rate": tuple(float(v) for v in shear_rate), "residuals": residuals, "warnings": ("diagnostic_candidate_requires_matching_protocols",)}


def integrate_thixotropy(time: Sequence[float], viscosity: Sequence[float]) -> dict[str, Any]:
    if len(time) != len(viscosity) or len(time) < 2:
        return {"status": "unavailable", "unavailable_reason": "thixotropy_series_invalid"}
    x, y = np.asarray(time, dtype=float), np.asarray(viscosity, dtype=float)
    if np.any(np.diff(x) <= 0) or not np.all(np.isfinite(y)):
        return {"status": "unavailable", "unavailable_reason": "thixotropy_time_axis_invalid"}
    return {"status": "computed_with_warning", "method": "viscosity_time_area", "area": float(np.trapezoid(y, x)), "warnings": ("diagnostic_candidate_requires_protocol_metadata",)}


@dataclass(frozen=True)
class RheologyYieldStressSpec:
    """Explicit semantics for a steady-shear yield-stress fit."""

    model: str
    stress_measurement_id: str
    rate_window: tuple[float, float] | None = None
    min_points: int = 3
    stress_unit: str | None = None
    rate_unit: str | None = None

    @classmethod
    def create(
        cls,
        *,
        model: str,
        stress_measurement_id: str,
        rate_window: Sequence[float] | None = None,
        min_points: int = 3,
        stress_unit: str | None = None,
        rate_unit: str | None = None,
    ) -> "RheologyYieldStressSpec":
        normalized_model = str(model).strip().casefold().replace("-", "_")
        if normalized_model not in _YIELD_MODELS:
            raise ValueError(f"Unsupported rheology yield-stress model: {model}")
        stress_id = str(stress_measurement_id).strip()
        if not stress_id:
            raise ValueError("Rheology yield-stress stress measurement id is required")
        count = int(min_points)
        if count < 2:
            raise ValueError("Rheology yield-stress min_points must be at least two")
        window = _optional_window(rate_window, name="rate_window", lower_bound=0.0)
        normalized_stress_unit = _optional_text(stress_unit)
        normalized_rate_unit = _optional_text(rate_unit)
        if normalized_rate_unit is not None and _scale_for(
            normalized_rate_unit, _RATE_SCALE_PER_SECOND
        ) is None:
            raise ValueError("Unsupported rheology yield-stress rate unit")
        if normalized_stress_unit is not None and _scale_for(
            normalized_stress_unit, _STRESS_SCALE_PA
        ) is None:
            raise ValueError("Unsupported rheology yield-stress stress unit")
        return cls(
            model=normalized_model,
            stress_measurement_id=stress_id,
            rate_window=window,
            min_points=count,
            stress_unit=normalized_stress_unit,
            rate_unit=normalized_rate_unit,
        )

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RheologyYieldStressSpec":
        if not isinstance(value, Mapping):
            raise TypeError("Rheology yield-stress spec must be a mapping")
        return cls.create(
            model=value.get("model", ""),
            stress_measurement_id=value.get("stress_measurement_id", ""),
            rate_window=value.get("rate_window"),
            min_points=value.get("min_points", 3),
            stress_unit=value.get("stress_unit"),
            rate_unit=value.get("rate_unit"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "stress_measurement_id": self.stress_measurement_id,
            "rate_window": None if self.rate_window is None else list(self.rate_window),
            "min_points": self.min_points,
            "stress_unit": self.stress_unit,
            "rate_unit": self.rate_unit,
        }


@dataclass(frozen=True)
class RheologyLVESpec:
    """Explicit semantics for strain-sweep LVE and crossover candidates."""

    storage_measurement_id: str
    loss_measurement_id: str
    strain_window: tuple[float, float] | None = None
    plateau_relative_tolerance: float = 0.05
    plateau_reference_points: int = 3
    min_plateau_points: int = 3
    strain_unit: str | None = None
    storage_unit: str | None = None
    loss_unit: str | None = None

    @classmethod
    def create(
        cls,
        *,
        storage_measurement_id: str,
        loss_measurement_id: str,
        strain_window: Sequence[float] | None = None,
        plateau_relative_tolerance: float = 0.05,
        plateau_reference_points: int = 3,
        min_plateau_points: int = 3,
        strain_unit: str | None = None,
        storage_unit: str | None = None,
        loss_unit: str | None = None,
    ) -> "RheologyLVESpec":
        storage_id = str(storage_measurement_id).strip()
        loss_id = str(loss_measurement_id).strip()
        if not storage_id or not loss_id:
            raise ValueError("Rheology LVE storage and loss measurement ids are required")
        tolerance = float(plateau_relative_tolerance)
        if not math.isfinite(tolerance) or tolerance <= 0.0:
            raise ValueError("Rheology LVE plateau tolerance must be finite and positive")
        reference_points = int(plateau_reference_points)
        minimum_points = int(min_plateau_points)
        if reference_points < 2:
            raise ValueError("Rheology LVE reference points must be at least two")
        if minimum_points < reference_points:
            raise ValueError("Rheology LVE minimum plateau points must cover the reference window")
        window = _optional_window(strain_window, name="strain_window", lower_bound=0.0)
        normalized_strain_unit = _optional_text(strain_unit)
        if normalized_strain_unit is not None and _scale_for(
            normalized_strain_unit, _STRAIN_SCALE_DIMENSIONLESS
        ) is None:
            raise ValueError("Unsupported rheology LVE strain unit")
        normalized_storage_unit = _optional_text(storage_unit)
        if normalized_storage_unit is not None and _scale_for(
            normalized_storage_unit, _STRESS_SCALE_PA
        ) is None:
            raise ValueError("Unsupported rheology LVE storage modulus unit")
        normalized_loss_unit = _optional_text(loss_unit)
        if normalized_loss_unit is not None and _scale_for(
            normalized_loss_unit, _STRESS_SCALE_PA
        ) is None:
            raise ValueError("Unsupported rheology LVE loss modulus unit")
        return cls(
            storage_measurement_id=storage_id,
            loss_measurement_id=loss_id,
            strain_window=window,
            plateau_relative_tolerance=tolerance,
            plateau_reference_points=reference_points,
            min_plateau_points=minimum_points,
            strain_unit=normalized_strain_unit,
            storage_unit=normalized_storage_unit,
            loss_unit=normalized_loss_unit,
        )

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RheologyLVESpec":
        if not isinstance(value, Mapping):
            raise TypeError("Rheology LVE spec must be a mapping")
        return cls.create(
            storage_measurement_id=value.get("storage_measurement_id", ""),
            loss_measurement_id=value.get("loss_measurement_id", ""),
            strain_window=value.get("strain_window"),
            plateau_relative_tolerance=value.get("plateau_relative_tolerance", 0.05),
            plateau_reference_points=value.get("plateau_reference_points", 3),
            min_plateau_points=value.get("min_plateau_points", 3),
            strain_unit=value.get("strain_unit"),
            storage_unit=value.get("storage_unit"),
            loss_unit=value.get("loss_unit"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "storage_measurement_id": self.storage_measurement_id,
            "loss_measurement_id": self.loss_measurement_id,
            "strain_window": None if self.strain_window is None else list(self.strain_window),
            "plateau_relative_tolerance": self.plateau_relative_tolerance,
            "plateau_reference_points": self.plateau_reference_points,
            "min_plateau_points": self.min_plateau_points,
            "strain_unit": self.strain_unit,
            "storage_unit": self.storage_unit,
            "loss_unit": self.loss_unit,
        }


@dataclass(frozen=True)
class RheologyAnalysisSpec:
    """Optional, explicit advanced rheology requests carried by a template."""

    yield_stress: RheologyYieldStressSpec | None = None
    lve: RheologyLVESpec | None = None

    @classmethod
    def create(
        cls,
        *,
        yield_stress: RheologyYieldStressSpec | Mapping[str, Any] | None = None,
        lve: RheologyLVESpec | Mapping[str, Any] | None = None,
    ) -> "RheologyAnalysisSpec":
        yield_spec = (
            None
            if yield_stress is None
            else yield_stress
            if isinstance(yield_stress, RheologyYieldStressSpec)
            else RheologyYieldStressSpec.from_mapping(yield_stress)
        )
        lve_spec = (
            None
            if lve is None
            else lve
            if isinstance(lve, RheologyLVESpec)
            else RheologyLVESpec.from_mapping(lve)
        )
        if yield_spec is None and lve_spec is None:
            raise ValueError("Rheology analysis spec must request at least one model")
        return cls(yield_stress=yield_spec, lve=lve_spec)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RheologyAnalysisSpec":
        if not isinstance(value, Mapping):
            raise TypeError("Rheology analysis spec must be a mapping")
        return cls.create(yield_stress=value.get("yield_stress"), lve=value.get("lve"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "yield_stress": None if self.yield_stress is None else self.yield_stress.to_dict(),
            "lve": None if self.lve is None else self.lve.to_dict(),
        }


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
    analysis_spec: RheologyAnalysisSpec | Mapping[str, Any] | None = None,
) -> RheologyProcessingOutcome:
    """Compute identities and explicitly requested advanced candidates."""

    x = np.asarray(x_values, dtype=float)
    if x.ndim != 1 or x.size < 2 or not np.all(np.isfinite(x)):
        raise ValueError("rheology processing requires a finite one-dimensional axis")
    signal_items = tuple(signals)
    if not signal_items or not all(
        isinstance(item, RheologySignalSeries) for item in signal_items
    ):
        raise TypeError("signals must contain RheologySignalSeries values")

    spec_errors: dict[str, str] = {}
    if analysis_spec is None:
        spec = None
    elif isinstance(analysis_spec, RheologyAnalysisSpec):
        spec = analysis_spec
    elif isinstance(analysis_spec, Mapping):
        spec, spec_errors = _parse_analysis_spec_mapping(analysis_spec)
    else:
        raise TypeError("analysis_spec must be RheologyAnalysisSpec or mapping")

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

    yield_stress_fit, lve_analysis = _advanced_metrics(
        x,
        axis_kind=str(axis_kind),
        axis_unit=str(axis_unit),
        signals=signal_items,
        spec=spec,
        spec_errors=spec_errors,
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
        "yield_stress_fit": yield_stress_fit,
        "lve_analysis": lve_analysis,
    }
    return RheologyProcessingOutcome(metrics, units, methods, parameters)


def _advanced_metrics(
    x: np.ndarray,
    *,
    axis_kind: str,
    axis_unit: str,
    signals: Sequence[RheologySignalSeries],
    spec: RheologyAnalysisSpec | None,
    spec_errors: Mapping[str, str],
    units: dict[str, str],
    methods: dict[str, str],
    parameters: dict[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if spec is None:
        reason = spec_errors.get("_all", "analysis_spec_required")
        return _unavailable(reason), _unavailable(reason)
    yield_fit = (
        _unavailable(spec_errors["yield_stress"])
        if "yield_stress" in spec_errors
        else _yield_stress_fit(
            x,
            axis_kind=axis_kind,
            axis_unit=axis_unit,
            signals=signals,
            spec=spec.yield_stress,
            units=units,
            methods=methods,
            parameters=parameters,
        )
        if spec.yield_stress is not None
        else _unavailable("not_requested")
    )
    lve = (
        _unavailable(spec_errors["lve"])
        if "lve" in spec_errors
        else _lve_analysis(
            x,
            axis_kind=axis_kind,
            axis_unit=axis_unit,
            signals=signals,
            spec=spec.lve,
            units=units,
            methods=methods,
            parameters=parameters,
        )
        if spec.lve is not None
        else _unavailable("not_requested")
    )
    return yield_fit, lve


def _parse_analysis_spec_mapping(
    value: Mapping[str, Any],
) -> tuple[RheologyAnalysisSpec | None, dict[str, str]]:
    """Parse yield and LVE branches independently for local failure isolation."""

    yield_spec: RheologyYieldStressSpec | None = None
    lve_spec: RheologyLVESpec | None = None
    errors: dict[str, str] = {}
    raw_yield = value.get("yield_stress")
    if raw_yield is not None:
        try:
            yield_spec = (
                raw_yield
                if isinstance(raw_yield, RheologyYieldStressSpec)
                else RheologyYieldStressSpec.from_mapping(raw_yield)
            )
        except (TypeError, ValueError, OverflowError):
            errors["yield_stress"] = "yield_stress_spec_invalid"
    raw_lve = value.get("lve")
    if raw_lve is not None:
        try:
            lve_spec = (
                raw_lve
                if isinstance(raw_lve, RheologyLVESpec)
                else RheologyLVESpec.from_mapping(raw_lve)
            )
        except (TypeError, ValueError, OverflowError):
            errors["lve"] = "lve_analysis_spec_invalid"
    if yield_spec is None and lve_spec is None:
        errors["_all"] = "analysis_spec_invalid"
        return None, errors
    return RheologyAnalysisSpec(yield_stress=yield_spec, lve=lve_spec), errors


def _yield_stress_fit(
    x: np.ndarray,
    *,
    axis_kind: str,
    axis_unit: str,
    signals: Sequence[RheologySignalSeries],
    spec: RheologyYieldStressSpec,
    units: dict[str, str],
    methods: dict[str, str],
    parameters: dict[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if axis_kind != "shear_rate":
        return _unavailable("shear_rate_axis_required")
    observed_rate_unit = (
        spec.rate_unit
        if str(axis_unit).strip().casefold() == "unknown" and spec.rate_unit is not None
        else axis_unit
    )
    rate_factor = _scale_for(observed_rate_unit, _RATE_SCALE_PER_SECOND)
    if rate_factor is None:
        return _unavailable("shear_rate_unit_incompatible")
    stress = _selected_signal(
        signals,
        measurement_id=spec.stress_measurement_id,
        signal_kind="shear_stress",
        reference_x=x,
    )
    if stress.get("status") != "computed":
        return _unavailable(str(stress.get("unavailable_reason", "stress_measurement_unavailable")))
    observed_stress_unit = (
        spec.stress_unit
        if str(stress["unit"]).strip().casefold() == "unknown" and spec.stress_unit is not None
        else str(stress["unit"])
    )
    stress_factor = _scale_for(observed_stress_unit, _STRESS_SCALE_PA)
    if stress_factor is None:
        return _unavailable("shear_stress_unit_incompatible")
    rates = np.asarray(x, dtype=float) * rate_factor
    stress_values = np.asarray(stress["values"], dtype=float) * stress_factor
    finite = np.isfinite(rates) & np.isfinite(stress_values) & (rates > 0.0)
    warnings: list[str] = []
    if np.any(~finite):
        warnings.append("nonpositive_or_nonfinite_fit_points_dropped")
    if spec.rate_window is not None:
        window_factor = _scale_for(
            spec.rate_unit if spec.rate_unit is not None else axis_unit,
            _RATE_SCALE_PER_SECOND,
        )
        if window_factor is None:
            return _unavailable("yield_rate_window_unit_incompatible")
        rate_window = tuple(value * window_factor for value in spec.rate_window)
        finite &= (rates >= rate_window[0]) & (rates <= rate_window[1])
    else:
        window_factor = None
        rate_window = None
    if not np.any(finite):
        return _unavailable("yield_rate_window_has_no_valid_points")
    fit_rates = rates[finite]
    fit_stress = stress_values[finite]
    if fit_rates.size < spec.min_points:
        return _unavailable("yield_fit_has_too_few_points")
    order = np.argsort(fit_rates, kind="mergesort")
    fit_rates = fit_rates[order]
    fit_stress = fit_stress[order]
    if np.unique(fit_rates).size < 2:
        return _unavailable("yield_fit_rate_axis_has_too_few_unique_points")

    method: str
    if spec.model == "bingham":
        try:
            slope, intercept = np.polyfit(fit_rates, fit_stress, 1)
        except (TypeError, ValueError, np.linalg.LinAlgError, FloatingPointError):
            return _unavailable("yield_stress_fit_failed")
        fitted = intercept + slope * fit_rates
        yield_value = float(intercept)
        consistency_value = float(slope)
        flow_value: float | None = None
        method = "bingham_linear_least_squares"
        flow_record = _unavailable("not_defined_for_bingham")
        consistency_unit = "Pa*s"
    else:
        try:
            from scipy.optimize import curve_fit

            def model(rate: np.ndarray, yield_stress: float, consistency: float, flow_index: float) -> np.ndarray:
                return yield_stress + consistency * np.power(rate, flow_index)

            linear_slope = float(np.polyfit(fit_rates, fit_stress, 1)[0])
            p0 = (
                float(max(0.0, np.min(fit_stress))),
                float(max(abs(linear_slope), 1e-12)),
                1.0,
            )
            fitted_parameters, _ = curve_fit(
                model,
                fit_rates,
                fit_stress,
                p0=p0,
                bounds=([-np.inf, 0.0, 0.05], [np.inf, np.inf, 3.0]),
                maxfev=20_000,
            )
        except (
            ImportError,
            TypeError,
            ValueError,
            RuntimeError,
            FloatingPointError,
            np.linalg.LinAlgError,
        ):
            return _unavailable("yield_stress_fit_failed")
        yield_value, consistency_value, flow_value = (
            float(item) for item in fitted_parameters
        )
        fitted = model(fit_rates, yield_value, consistency_value, flow_value)
        method = "herschel_bulkley_nonlinear_least_squares"
        flow_record = _scalar_record(
            value=flow_value,
            unit="1",
            method=method,
            source_ids=(spec.stress_measurement_id,),
        )
        consistency_unit = "Pa*s^n"

    if not (
        math.isfinite(yield_value)
        and math.isfinite(consistency_value)
        and np.all(np.isfinite(fitted))
    ):
        return _unavailable("yield_stress_fit_failed")

    residual = fit_stress - fitted
    sse = float(np.sum(residual * residual))
    rmse = float(math.sqrt(sse / fit_rates.size))
    centered = fit_stress - float(np.mean(fit_stress))
    total = float(np.sum(centered * centered))
    r_squared = None if total <= 0.0 else float(1.0 - sse / total)
    if yield_value < 0.0:
        warnings.append("negative_yield_stress_fit")
    if consistency_value < 0.0:
        warnings.append("negative_consistency_index_fit")
    status = "computed_with_warning" if warnings else "computed"
    fit_parameters = {
        "model": spec.model,
        "stress_measurement_id": spec.stress_measurement_id,
        "rate_axis_kind": axis_kind,
        "rate_source_unit": observed_rate_unit,
        "rate_to_per_second_factor": rate_factor,
        "stress_source_unit": observed_stress_unit,
        "stress_to_pa_factor": stress_factor,
        "rate_window": None if spec.rate_window is None else list(spec.rate_window),
        "rate_window_unit": spec.rate_unit if spec.rate_unit is not None else axis_unit,
        "rate_window_to_per_second_factor": window_factor,
        "rate_window_per_second": None if rate_window is None else list(rate_window),
        "fit_point_count": int(fit_rates.size),
        "dropped_point_count": int(x.size - fit_rates.size),
    }
    yield_record = _scalar_record(
        value=yield_value,
        unit="Pa",
        method=method,
        source_ids=(spec.stress_measurement_id,),
        parameters=fit_parameters,
        warnings=warnings,
    )
    consistency_record = _scalar_record(
        value=consistency_value,
        unit=consistency_unit,
        method=method,
        source_ids=(spec.stress_measurement_id,),
        parameters=fit_parameters,
        warnings=warnings,
    )
    fit = {
        "status": status,
        "model": spec.model,
        "yield_stress": yield_record,
        "consistency_index": consistency_record,
        "flow_index": flow_record,
        "fit_quality": {
            "fit_point_count": int(fit_rates.size),
            "sse_pa2": sse,
            "rmse_pa": rmse,
            "r_squared": r_squared,
        },
        "source_measurements": [spec.stress_measurement_id],
        "parameters": fit_parameters,
    }
    if warnings:
        fit["warnings"] = list(dict.fromkeys(warnings))
    for name, record in (
        ("yield_stress", yield_record),
        ("consistency_index", consistency_record),
        ("flow_index", flow_record),
    ):
        if record.get("status") in {"computed", "computed_with_warning"}:
            _add_record_metadata(
                record,
                path=f"yield_stress_fit.{name}.value",
                units=units,
                methods=methods,
                parameters=parameters,
            )
    return fit


def _lve_analysis(
    x: np.ndarray,
    *,
    axis_kind: str,
    axis_unit: str,
    signals: Sequence[RheologySignalSeries],
    spec: RheologyLVESpec,
    units: dict[str, str],
    methods: dict[str, str],
    parameters: dict[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if axis_kind != "strain":
        return _unavailable("strain_axis_required")
    observed_strain_unit = (
        spec.strain_unit
        if str(axis_unit).strip().casefold() == "unknown" and spec.strain_unit is not None
        else axis_unit
    )
    strain_factor = _scale_for(observed_strain_unit, _STRAIN_SCALE_DIMENSIONLESS)
    if strain_factor is None:
        return _unavailable("strain_unit_incompatible")
    storage = _selected_signal(
        signals,
        measurement_id=spec.storage_measurement_id,
        signal_kind="storage_modulus",
        reference_x=x,
    )
    loss = _selected_signal(
        signals,
        measurement_id=spec.loss_measurement_id,
        signal_kind="loss_modulus",
        reference_x=x,
    )
    missing = _input_reason(storage, loss)
    if missing is not None:
        return _unavailable(missing)
    observed_storage_unit = (
        spec.storage_unit
        if str(storage["unit"]).strip().casefold() == "unknown"
        and spec.storage_unit is not None
        else str(storage["unit"])
    )
    observed_loss_unit = (
        spec.loss_unit
        if str(loss["unit"]).strip().casefold() == "unknown" and spec.loss_unit is not None
        else str(loss["unit"])
    )
    storage_factor = _scale_for(observed_storage_unit, _STRESS_SCALE_PA)
    loss_factor = _scale_for(observed_loss_unit, _STRESS_SCALE_PA)
    if storage_factor is None or loss_factor is None:
        return _unavailable("modulus_units_incompatible")
    strain = np.asarray(x, dtype=float) * strain_factor
    storage_values = np.asarray(storage["values"], dtype=float) * storage_factor
    loss_values = np.asarray(loss["values"], dtype=float) * loss_factor
    finite = np.isfinite(strain) & np.isfinite(storage_values) & np.isfinite(loss_values)
    if not np.all(finite):
        return _unavailable("lve_nonfinite_input")
    if not np.all(strain > 0.0) or not np.all(np.diff(strain) > 0.0):
        return _unavailable("strain_axis_must_be_positive_and_increasing")
    if spec.strain_window is not None:
        window_unit = spec.strain_unit if spec.strain_unit is not None else axis_unit
        window_factor = _scale_for(window_unit, _STRAIN_SCALE_DIMENSIONLESS)
        if window_factor is None:
            return _unavailable("strain_window_unit_incompatible")
        strain_window = tuple(value * window_factor for value in spec.strain_window)
        window_mask = (strain >= strain_window[0]) & (strain <= strain_window[1])
    else:
        window_factor = None
        strain_window = None
        window_mask = np.ones(strain.size, dtype=bool)
    candidate_indices = np.flatnonzero(window_mask)
    lve_parameters = {
        "storage_measurement_id": spec.storage_measurement_id,
        "loss_measurement_id": spec.loss_measurement_id,
        "strain_source_unit": observed_strain_unit,
        "strain_to_dimensionless_factor": strain_factor,
        "storage_source_unit": observed_storage_unit,
        "storage_to_pa_factor": storage_factor,
        "loss_source_unit": observed_loss_unit,
        "loss_to_pa_factor": loss_factor,
        "plateau_relative_tolerance": spec.plateau_relative_tolerance,
        "plateau_reference_points": spec.plateau_reference_points,
        "min_plateau_points": spec.min_plateau_points,
        "strain_window": None if spec.strain_window is None else list(spec.strain_window),
        "strain_window_unit": spec.strain_unit if spec.strain_unit is not None else axis_unit,
        "strain_window_to_dimensionless_factor": window_factor,
        "strain_window_dimensionless": (
            None if strain_window is None else list(strain_window)
        ),
        "plateau_point_count": 0,
    }

    plateau_warnings: list[str] = []
    plateau_reason: str | None = None
    lve_limit: dict[str, Any] = _unavailable("lve_plateau_unavailable")
    plateau_modulus: dict[str, Any] = _unavailable("lve_plateau_unavailable")
    plateau_range: dict[str, Any] | None = None
    contiguous: list[int] = []
    if candidate_indices.size < spec.plateau_reference_points:
        plateau_reason = "lve_window_has_too_few_points"
    else:
        reference_indices = candidate_indices[: spec.plateau_reference_points]
        baseline = float(np.median(storage_values[reference_indices]))
        if not math.isfinite(baseline) or baseline <= 0.0:
            plateau_reason = "storage_modulus_plateau_nonpositive"
        else:
            relative_deviation = np.abs(storage_values - baseline) / abs(baseline)
            within_plateau = window_mask & (
                relative_deviation <= spec.plateau_relative_tolerance
            )
            for index in candidate_indices:
                if not within_plateau[index]:
                    break
                contiguous.append(int(index))
            if len(contiguous) < spec.min_plateau_points:
                plateau_reason = "lve_plateau_has_too_few_points"
            else:
                lve_parameters["plateau_point_count"] = len(contiguous)
                limit_index = contiguous[-1]
                if limit_index == candidate_indices[-1]:
                    plateau_warnings.append("lve_plateau_reaches_recorded_boundary")
                method = "initial_storage_modulus_plateau"
                lve_limit = _scalar_record(
                    value=float(strain[limit_index]),
                    unit="1",
                    method=method,
                    source_ids=(spec.storage_measurement_id, spec.loss_measurement_id),
                    parameters=lve_parameters,
                    warnings=plateau_warnings,
                )
                plateau_modulus = _scalar_record(
                    value=baseline,
                    unit="Pa",
                    method=method,
                    source_ids=(spec.storage_measurement_id,),
                    parameters=lve_parameters,
                    warnings=plateau_warnings,
                )
                plateau_range = {
                    "lower": float(strain[reference_indices[0]]),
                    "upper": float(strain[limit_index]),
                    "unit": "1",
                    "point_count": len(contiguous),
                }
    if plateau_reason is not None:
        lve_limit = _unavailable(plateau_reason)
        plateau_modulus = _unavailable(plateau_reason)

    # Gel-point crossover is independent of the plateau fit.  A failed or
    # underspecified plateau must not suppress a valid crossover candidate.
    gel_candidates = _gel_point_candidates(
        strain,
        storage_values,
        loss_values,
        indices=candidate_indices,
    )
    gel_warnings: list[str] = []
    if len(gel_candidates) == 0:
        gel_point = _unavailable("modulus_crossover_not_observed")
    else:
        gel_point = _scalar_record(
            value=float(gel_candidates[0]["strain"]),
            unit="1",
            method=str(
                gel_candidates[0].get(
                    "method", "log_strain_modulus_crossover_interpolation"
                )
            ),
            source_ids=(spec.storage_measurement_id, spec.loss_measurement_id),
            parameters={**lve_parameters, "candidate_selection": "lowest_strain_crossover"},
        )
        if len(gel_candidates) > 1:
            gel_warnings.append("multiple_modulus_crossovers_observed")
    warnings = [*plateau_warnings, *gel_warnings]
    if plateau_warnings:
        lve_limit = dict(lve_limit)
        lve_limit["status"] = "computed_with_warning"
        lve_limit["warnings"] = list(dict.fromkeys(plateau_warnings))
        plateau_modulus = dict(plateau_modulus)
        plateau_modulus["status"] = "computed_with_warning"
        plateau_modulus["warnings"] = list(dict.fromkeys(plateau_warnings))
    if gel_warnings and gel_point.get("status") in {"computed", "computed_with_warning"}:
        gel_point = dict(gel_point)
        gel_point["status"] = "computed_with_warning"
        gel_point["warnings"] = list(dict.fromkeys(gel_warnings))
    record_statuses = {
        str(record.get("status"))
        for record in (lve_limit, plateau_modulus, gel_point)
    }
    if "computed_with_warning" in record_statuses or warnings:
        status = "computed_with_warning"
    elif "computed" in record_statuses:
        status = "computed"
    else:
        status = "unavailable"
    lve = {
        "status": status,
        "lve_limit": lve_limit,
        "plateau_storage_modulus": plateau_modulus,
        "plateau_range": (
            plateau_range
            if plateau_range is not None
            else _unavailable(plateau_reason or "lve_plateau_unavailable")
        ),
        "gel_point": gel_point,
        "gel_point_candidates": {
            "count": len(gel_candidates),
            "candidates": gel_candidates,
        },
        "source_measurements": [spec.storage_measurement_id, spec.loss_measurement_id],
        "parameters": lve_parameters,
    }
    if status == "unavailable":
        lve["unavailable_reason"] = plateau_reason or str(
            gel_point.get("unavailable_reason", "lve_analysis_unavailable")
        )
    if warnings:
        lve["warnings"] = list(dict.fromkeys(warnings))
    for name, record in (
        ("lve_limit", lve_limit),
        ("plateau_storage_modulus", plateau_modulus),
        ("gel_point", gel_point),
    ):
        if record.get("status") in {"computed", "computed_with_warning"}:
            _add_record_metadata(
                record,
                path=f"lve_analysis.{name}.value",
                units=units,
                methods=methods,
                parameters=parameters,
            )
    return lve


def _selected_signal(
    signals: Sequence[RheologySignalSeries],
    *,
    measurement_id: str,
    signal_kind: str,
    reference_x: np.ndarray,
) -> dict[str, Any]:
    matches = tuple(item for item in signals if item.measurement_id == measurement_id)
    if not matches:
        return _unavailable("stress_measurement_not_found" if signal_kind == "shear_stress" else "measurement_not_found")
    if len(matches) != 1:
        return _unavailable("measurement_id_ambiguous")
    signal = matches[0]
    if signal.signal_kind != signal_kind:
        return _unavailable("measurement_signal_kind_mismatch")
    signal_x = _series_x(signal, reference_x)
    if signal_x.shape != reference_x.shape or not np.array_equal(signal_x, reference_x):
        return _unavailable("measurement_axis_incompatible")
    return {
        "status": "computed",
        "measurement_id": signal.measurement_id,
        "unit": signal.unit,
        "values": signal.values,
    }


def _scalar_record(
    *,
    value: float,
    unit: str,
    method: str,
    source_ids: Sequence[str],
    parameters: Mapping[str, Any] | None = None,
    warnings: Sequence[str] = (),
) -> dict[str, Any]:
    normalized_warnings = tuple(str(item) for item in warnings)
    record: dict[str, Any] = {
        "status": "computed_with_warning" if normalized_warnings else "computed",
        "value": float(value),
        "unit": str(unit),
        "method": str(method),
        "source_measurements": [str(item) for item in source_ids],
        "parameters": dict(parameters or {}),
    }
    if normalized_warnings:
        record["warnings"] = list(normalized_warnings)
    return record


def _gel_point_candidates(
    strain: np.ndarray,
    storage: np.ndarray,
    loss: np.ndarray,
    *,
    indices: np.ndarray | None = None,
) -> list[dict[str, Any]]:
    selected_indices = (
        np.arange(strain.size, dtype=int)
        if indices is None
        else np.asarray(indices, dtype=int)
    )
    if selected_indices.size == 0:
        return []
    difference = storage - loss
    candidates: list[dict[str, Any]] = []
    selected_difference = difference[selected_indices]
    for local_index, original_index in enumerate(selected_indices):
        if float(selected_difference[local_index]) != 0.0:
            continue
        if local_index > 0 and float(selected_difference[local_index - 1]) == 0.0:
            continue
        candidates.append(
            {
                "strain": float(strain[original_index]),
                "unit": "1",
                "left_index": int(original_index),
                "right_index": int(original_index),
                "method": "modulus_crossover_exact",
            }
        )

    for local_left in range(selected_indices.size - 1):
        local_right = local_left + 1
        left_value = float(selected_difference[local_left])
        right_value = float(selected_difference[local_right])
        if left_value == 0.0 or right_value == 0.0 or left_value * right_value > 0.0:
            continue
        left = int(selected_indices[local_left])
        right = int(selected_indices[local_right])
        fraction = abs(left_value) / (abs(left_value) + abs(right_value))
        coordinate = float(
            10.0
            ** (
                math.log10(float(strain[left]))
                + fraction
                * (math.log10(float(strain[right])) - math.log10(float(strain[left])))
            )
        )
        candidates.append(
            {
                "strain": coordinate,
                "unit": "1",
                "left_index": left,
                "right_index": right,
                "method": "log_strain_modulus_crossover_interpolation",
            }
        )
    return candidates


def _optional_text(value: object) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    return str(value).strip()


def _optional_window(
    value: Sequence[float] | None,
    *,
    name: str,
    lower_bound: float,
) -> tuple[float, float] | None:
    if value is None:
        return None
    if isinstance(value, (str, bytes, bytearray)):
        raise TypeError(f"Rheology {name} must be a numeric pair")
    window = tuple(float(item) for item in value)
    if (
        len(window) != 2
        or any(not math.isfinite(item) for item in window)
        or window[0] < lower_bound
        or window[0] >= window[1]
    ):
        raise ValueError(f"Rheology {name} must be a finite increasing pair")
    return window


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


def _unavailable(reason: str) -> dict[str, Any]:
    return {"status": "unavailable", "unavailable_reason": reason}


__all__ = [
    "RheologyAdvancedSpec",
    "RheologyAnalysisSpec",
    "RheologyLVESpec",
    "RheologyProcessingOutcome",
    "RheologySignalSeries",
    "RheologyYieldStressSpec",
    "analyze_rheology_group",
    "compare_cox_merz",
    "integrate_thixotropy",
]
