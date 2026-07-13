"""Immutable WAXS evidence views used by publication figure providers."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

import numpy as np

from ..figures.contracts import FigureEligibilityDecision


@dataclass(frozen=True)
class WAXSScanView:
    """A plotting-only snapshot of one completed WAXS result."""

    index: int
    label: str
    two_theta_deg: tuple[float, ...]
    intensity: tuple[float, ...]
    fit: tuple[float, ...]
    background: tuple[float, ...]
    peaks: tuple[Mapping[str, Any], ...]
    parameters: Mapping[str, Any]
    r_squared: float
    size_reliability_status: str
    sector_used: str
    quality_flags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "two_theta_deg", _array_tuple(self.two_theta_deg))
        object.__setattr__(self, "intensity", _array_tuple(self.intensity))
        object.__setattr__(self, "fit", _array_tuple(self.fit))
        object.__setattr__(self, "background", _array_tuple(self.background))
        object.__setattr__(self, "peaks", tuple(_freeze_value(item) for item in self.peaks))
        object.__setattr__(self, "parameters", _freeze_value(self.parameters))
        object.__setattr__(self, "r_squared", _finite_float(self.r_squared))
        object.__setattr__(self, "size_reliability_status", str(self.size_reliability_status or ""))
        object.__setattr__(self, "sector_used", str(self.sector_used or "full"))
        object.__setattr__(self, "quality_flags", tuple(str(flag) for flag in self.quality_flags))

    @property
    def finite_pair_count(self) -> int:
        return finite_pair_count(self)


def _finite_float(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return np.nan
    return number if np.isfinite(number) else np.nan


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


def finite_pair_count(view: WAXSScanView) -> int:
    if len(view.two_theta_deg) != len(view.intensity):
        return 0
    return sum(
        bool(np.isfinite(two_theta) and np.isfinite(intensity))
        for two_theta, intensity in zip(view.two_theta_deg, view.intensity)
    )


def _result_parameters(result: Any) -> Mapping[str, Any]:
    parameters = getattr(result, "parameters", {})
    return parameters if isinstance(parameters, Mapping) else {}


def scan_views_from_engine(engine: Any) -> tuple[WAXSScanView, ...]:
    """Project completed results without running any WAXS computation."""

    views: list[WAXSScanView] = []
    for index, result in enumerate(tuple(getattr(engine, "_results", ()) or ())):
        two_theta = getattr(result, "two_theta", getattr(result, "two_theta_deg", ()))
        intensity = getattr(result, "I", getattr(result, "I_arb", ()))
        views.append(
            WAXSScanView(
                index=index,
                label=str(getattr(result, "label", "") or f"scan-{index}"),
                two_theta_deg=_array_tuple(two_theta),
                intensity=_array_tuple(intensity),
                fit=_array_tuple(getattr(result, "I_fit", ())),
                background=_array_tuple(getattr(result, "I_instrument_background", ())),
                peaks=tuple(getattr(result, "peaks", ()) or ()),
                parameters=_result_parameters(result),
                r_squared=_finite_float(getattr(result, "r_squared", np.nan)),
                size_reliability_status=str(getattr(result, "size_reliability_status", "") or ""),
                sector_used=str(getattr(result, "sector_used", "full") or "full"),
                quality_flags=tuple(getattr(result, "quality_flags", ()) or ()),
            )
        )
    return tuple(views)


def classify_waxs_scan_eligibility(view: WAXSScanView) -> FigureEligibilityDecision:
    """Classify a completed profile using emitted evidence only."""

    flags = {str(flag).strip().lower() for flag in view.quality_flags}
    if flags & {"analysis_error", "fit_failed", "contains_nan_inf", "invalid_profile"}:
        return FigureEligibilityDecision("diagnostic", ("analysis_quality_failure",))
    if len(view.two_theta_deg) != len(view.intensity):
        return FigureEligibilityDecision("diagnostic", ("misaligned_profile_arrays",))
    if view.finite_pair_count < 5:
        return FigureEligibilityDecision("diagnostic", ("insufficient_profile_points",))
    if not np.isfinite(view.r_squared) or view.r_squared < 0.85:
        return FigureEligibilityDecision("diagnostic", ("low_fit_quality",))
    if view.r_squared < 0.90:
        return FigureEligibilityDecision("si", ("fit_quality_not_main",))
    return FigureEligibilityDecision("main", ("reliable_profile",))


def finite_parameter(view: WAXSScanView, key: str) -> float:
    return _finite_float(view.parameters.get(key))


__all__ = [
    "WAXSScanView",
    "classify_waxs_scan_eligibility",
    "finite_pair_count",
    "finite_parameter",
    "scan_views_from_engine",
]
