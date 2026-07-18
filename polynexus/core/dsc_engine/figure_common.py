"""Immutable DSC evidence views used by publication figure providers."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

import numpy as np

from ..figures.contracts import FigureEligibilityDecision


@dataclass(frozen=True)
class DSCScanView:
    """A plotting-only snapshot of one completed DSC result."""

    index: int
    label: str
    temperature_C: tuple[float, ...]
    heat_flow_W_g: tuple[float, ...]
    parameters: Mapping[str, Any]
    quality_score: float
    quality_flags: tuple[str, ...]
    direction: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "temperature_C", tuple(float(value) for value in self.temperature_C))
        object.__setattr__(self, "heat_flow_W_g", tuple(float(value) for value in self.heat_flow_W_g))
        object.__setattr__(self, "parameters", _freeze_value(self.parameters))
        object.__setattr__(self, "quality_flags", tuple(str(flag) for flag in self.quality_flags))
        object.__setattr__(self, "quality_score", float(self.quality_score))
        direction = str(self.direction or "").strip().lower()
        if direction not in {"heating", "cooling", "isothermal"}:
            direction = ""
        object.__setattr__(self, "direction", direction)


def _finite_float(value: Any, default: float = np.nan) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if np.isfinite(number) else default


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze_value(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_value(item) for item in value)
    if isinstance(value, np.ndarray):
        return tuple(_freeze_value(item) for item in value.reshape(-1).tolist())
    return value


def _array_tuple(value: Any) -> tuple[float, ...]:
    try:
        array = np.asarray(value, dtype=float).reshape(-1)
    except (TypeError, ValueError):
        return ()
    return tuple(float(item) for item in array)


def _result_parameters(result: Any) -> Mapping[str, Any]:
    parameters = getattr(result, "parameters", {})
    if isinstance(parameters, Mapping):
        return parameters
    return {}


def scan_views_from_engine(engine: Any) -> tuple[DSCScanView, ...]:
    """Project emitted engine results without running any DSC computation."""

    views: list[DSCScanView] = []
    for index, result in enumerate(tuple(getattr(engine, "_results", ()) or ())):
        views.append(
            DSCScanView(
                index=index,
                label=str(getattr(result, "label", "") or f"scan-{index}"),
                temperature_C=_array_tuple(getattr(result, "T", ())),
                heat_flow_W_g=_array_tuple(getattr(result, "HF", ())),
                parameters=_result_parameters(result),
                quality_score=_finite_float(getattr(result, "quality_score", np.nan)),
                quality_flags=tuple(getattr(result, "quality_flags", ()) or ()),
                direction=str(
                    getattr(result, "technique", "")
                    or getattr(result, "direction", "")
                    or ""
                ),
            )
        )
    return tuple(views)


def classify_dsc_scan_eligibility(view: DSCScanView) -> FigureEligibilityDecision:
    """Classify a result using emitted quality evidence only."""

    flags = {str(flag).strip().lower() for flag in view.quality_flags}
    if flags & {
        "analysis_error",
        "baseline_unstable",
        "integration_failed",
        "contains_nan_inf",
        "non_monotonic_temperature",
        "flat_signal",
        "too_few_points",
    }:
        return FigureEligibilityDecision("diagnostic", ("analysis_quality_failure",))
    if not np.isfinite(view.quality_score) or view.quality_score < 0.50:
        return FigureEligibilityDecision("si", ("low_quality_score",))
    if flags - {"quality_ok"}:
        return FigureEligibilityDecision("si", ("unclassified_quality_flag",))
    if len(view.temperature_C) != len(view.heat_flow_W_g):
        return FigureEligibilityDecision("diagnostic", ("misaligned_curve_arrays",))
    valid_points = sum(
        bool(np.isfinite(temperature) and np.isfinite(heat_flow))
        for temperature, heat_flow in zip(view.temperature_C, view.heat_flow_W_g)
    )
    if valid_points < 5:
        return FigureEligibilityDecision("diagnostic", ("insufficient_curve_points",))
    return FigureEligibilityDecision("main", ("quality_ok",))


def finite_parameter(view: DSCScanView, key: str) -> float:
    return _finite_float(view.parameters.get(key))


__all__ = [
    "DSCScanView",
    "classify_dsc_scan_eligibility",
    "finite_parameter",
    "scan_views_from_engine",
]
