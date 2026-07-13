from __future__ import annotations

import math
from abc import ABC, abstractmethod
from numbers import Real
from typing import Any, Iterable, Sequence

from ..contracts import PreprocessEvidence, PreprocessIntent, SCHEMA_VERSION
from ..peak_metrics import compare_peak_sets
from ..snapshot import AnalysisSnapshot


WINDOW_STEPS = {"light": 2, "medium": 4, "strong": 6}
STRENGTH_MULTIPLIERS = {
    "light": (0.75, 1.25),
    "medium": (0.50, 2.00),
    "strong": (0.25, 4.00),
}


def finite_float(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def relative_change(before: object, after: object) -> float | None:
    left = finite_float(before)
    right = finite_float(after)
    if left is None or right is None:
        return None
    return abs(right - left) / max(abs(left), 1e-12)


def bounded_odd_windows(
    current: int,
    step: int,
    *,
    minimum: int,
    maximum: int,
    order: int,
) -> list[int]:
    values: list[int] = []
    for candidate in (current - step, current + step):
        candidate = max(minimum, min(maximum, int(candidate)))
        if candidate % 2 == 0:
            candidate += 1 if candidate < maximum else -1
        if candidate <= order or candidate == current or candidate in values:
            continue
        values.append(candidate)
    return values


def nested_number(mapping: dict[str, Any], paths: Iterable[Sequence[str]]) -> float | None:
    for path in paths:
        current: Any = mapping
        for key in path:
            if not isinstance(current, dict) or key not in current:
                current = None
                break
            current = current[key]
        value = finite_float(current)
        if value is not None:
            return value
    return None


class TechniquePreprocessAdapter(ABC):
    technique: str
    name: str
    version = "1"
    peak_tolerance: float
    physical_keys: tuple[str, ...] = ()
    integrated_area_keys: tuple[str, ...] = ()
    baseline_score_paths: tuple[tuple[str, ...], ...] = ()

    @abstractmethod
    def baseline_deltas(
        self,
        intent: PreprocessIntent,
        base_config: dict[str, Any],
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def smoothing_deltas(
        self,
        intent: PreprocessIntent,
        base_config: dict[str, Any],
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def normalize_peaks(self, output: dict[str, Any]) -> list[dict[str, Any]]:
        raise NotImplementedError

    def build_evidence(
        self,
        candidate_id: str,
        control: AnalysisSnapshot,
        candidate: AnalysisSnapshot,
    ) -> PreprocessEvidence:
        control_peaks = self.normalize_peaks(control.output_parameters)
        candidate_peaks = self.normalize_peaks(candidate.output_parameters)
        peak_metrics = compare_peak_sets(
            control_peaks,
            candidate_peaks,
            center_tolerance=self.peak_tolerance,
        )

        control_rmse = finite_float(control.residual_pattern.get("rmse"))
        candidate_rmse = finite_float(candidate.residual_pattern.get("rmse"))
        noise_reduction = None
        if control_rmse is not None and candidate_rmse is not None and control_rmse > 0:
            noise_reduction = (control_rmse - candidate_rmse) / control_rmse

        baseline_before = nested_number(control.analysis_evidence, self.baseline_score_paths)
        baseline_after = nested_number(candidate.analysis_evidence, self.baseline_score_paths)
        baseline_flatness = None
        if baseline_before is not None and baseline_after is not None:
            baseline_flatness = baseline_after - baseline_before

        residual_autocorrelation = finite_float(
            candidate.residual_pattern.get(
                "residual_autocorrelation",
                candidate.residual_pattern.get("autocorrelation"),
            )
        )
        negative_fraction = self._negative_fraction(candidate)

        physical_changes: dict[str, float] = {}
        for key in self.physical_keys:
            change = relative_change(
                control.output_parameters.get(key),
                candidate.output_parameters.get(key),
            )
            if change is not None:
                physical_changes[key] = change
        physical_drift = max(physical_changes.values()) if physical_changes else None

        named_area_changes: dict[str, float] = {}
        for key in self.integrated_area_keys:
            change = relative_change(
                control.output_parameters.get(key),
                candidate.output_parameters.get(key),
            )
            if change is not None:
                named_area_changes[key] = change
        area_changes = list(named_area_changes.values())
        if peak_metrics.integrated_area_change is not None:
            area_changes.append(peak_metrics.integrated_area_change)
        integrated_area_change = max(area_changes) if area_changes else None

        peak_shift = peak_metrics.max_peak_shift
        fwhm_change = peak_metrics.max_fwhm_change
        weak_peak_retention = (
            peak_metrics.weak_peak_retention if peak_metrics.control_count else None
        )
        required_values = (
            noise_reduction,
            negative_fraction,
            peak_shift,
            fwhm_change,
            integrated_area_change,
            weak_peak_retention,
            physical_drift,
        )
        evidence_coverage = sum(value is not None for value in required_values) / len(
            required_values
        )
        technique_specific: dict[str, Any] = {
            f"{key}_change": value for key, value in physical_changes.items()
        }
        technique_specific.update(
            {f"{key}_change": value for key, value in named_area_changes.items()}
        )
        technique_specific["peak_coverage"] = peak_metrics.coverage

        return PreprocessEvidence(
            schema_version=SCHEMA_VERSION,
            candidate_id=candidate_id,
            run_status="ok",
            evidence_coverage=round(evidence_coverage, 12),
            noise_reduction=noise_reduction,
            baseline_flatness=baseline_flatness,
            residual_autocorrelation=residual_autocorrelation,
            negative_fraction=negative_fraction,
            peak_shift=peak_shift,
            fwhm_change=fwhm_change,
            integrated_area_change=integrated_area_change,
            weak_peak_retention=weak_peak_retention,
            physical_parameter_drift=physical_drift,
            technique_specific=technique_specific,
        )

    @staticmethod
    def _negative_fraction(snapshot: AnalysisSnapshot) -> float | None:
        paths = (
            ("negative_fraction",),
            ("signal_evidence", "negative_fraction"),
            ("background_evidence", "negative_fraction"),
        )
        value = nested_number(snapshot.output_parameters, paths)
        if value is not None:
            return value
        return nested_number(snapshot.analysis_evidence, paths)


def normalized_peak(
    peak: dict[str, Any],
    *,
    center_keys: Sequence[str],
    fwhm_keys: Sequence[str],
    area_keys: Sequence[str] = ("area",),
    height_keys: Sequence[str] = ("height", "amplitude"),
) -> dict[str, float]:
    normalized: dict[str, float] = {}
    for target, keys in (
        ("center", center_keys),
        ("fwhm", fwhm_keys),
        ("area", area_keys),
        ("height", height_keys),
    ):
        for key in keys:
            value = finite_float(peak.get(key))
            if value is not None:
                normalized[target] = value
                break
    return normalized
