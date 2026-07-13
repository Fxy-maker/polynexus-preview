from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real
from typing import Any, Sequence


@dataclass(frozen=True)
class PeakComparison:
    control_count: int
    candidate_count: int
    matched_count: int
    coverage: float
    max_peak_shift: float | None
    max_fwhm_change: float | None
    integrated_area_change: float | None
    weak_peak_retention: float


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _peak_value(peak: dict[str, Any], name: str) -> float | None:
    return _number(peak.get(name))


def _strength(peak: dict[str, Any]) -> float:
    for name in ("area", "height"):
        value = _peak_value(peak, name)
        if value is not None:
            return abs(value)
    return 0.0


def _relative_change(before: float, after: float) -> float:
    return abs(after - before) / max(abs(before), 1e-12)


def _rounded(value: float) -> float:
    return round(float(value), 12)


def compare_peak_sets(
    control_peaks: Sequence[dict[str, Any]],
    candidate_peaks: Sequence[dict[str, Any]],
    *,
    center_tolerance: float,
) -> PeakComparison:
    control = [dict(item) for item in control_peaks if isinstance(item, dict)]
    candidate = [dict(item) for item in candidate_peaks if isinstance(item, dict)]
    if not control:
        return PeakComparison(
            control_count=0,
            candidate_count=len(candidate),
            matched_count=0,
            coverage=0.0,
            max_peak_shift=None,
            max_fwhm_change=None,
            integrated_area_change=None,
            weak_peak_retention=0.0,
        )

    pair_options: list[tuple[float, int, int]] = []
    for control_index, control_peak in enumerate(control):
        control_center = _peak_value(control_peak, "center")
        if control_center is None:
            continue
        for candidate_index, candidate_peak in enumerate(candidate):
            candidate_center = _peak_value(candidate_peak, "center")
            if candidate_center is None:
                continue
            distance = abs(candidate_center - control_center)
            if distance <= center_tolerance:
                pair_options.append((distance, control_index, candidate_index))

    matched_control: set[int] = set()
    matched_candidate: set[int] = set()
    matches: list[tuple[int, int, float]] = []
    for distance, control_index, candidate_index in sorted(pair_options):
        if control_index in matched_control or candidate_index in matched_candidate:
            continue
        matched_control.add(control_index)
        matched_candidate.add(candidate_index)
        matches.append((control_index, candidate_index, distance))

    fwhm_changes: list[float] = []
    for control_index, candidate_index, _distance in matches:
        before = _peak_value(control[control_index], "fwhm")
        after = _peak_value(candidate[candidate_index], "fwhm")
        if before is not None and after is not None:
            fwhm_changes.append(_relative_change(before, after))

    control_area = sum(_strength(peak) for peak in control)
    candidate_area = sum(_strength(peak) for peak in candidate)
    area_change = (
        _relative_change(control_area, candidate_area) if control_area > 0.0 else None
    )

    weak_count = max(1, math.ceil(len(control) * 0.25))
    weak_indices = {
        index
        for index, _peak in sorted(
            enumerate(control),
            key=lambda item: (_strength(item[1]), item[0]),
        )[:weak_count]
    }
    weak_retention = len(weak_indices & matched_control) / len(weak_indices)
    shifts = [distance for _control, _candidate, distance in matches]

    return PeakComparison(
        control_count=len(control),
        candidate_count=len(candidate),
        matched_count=len(matches),
        coverage=_rounded(len(matches) / len(control)),
        max_peak_shift=_rounded(max(shifts)) if shifts else None,
        max_fwhm_change=_rounded(max(fwhm_changes)) if fwhm_changes else None,
        integrated_area_change=_rounded(area_change) if area_change is not None else None,
        weak_peak_retention=_rounded(weak_retention),
    )
