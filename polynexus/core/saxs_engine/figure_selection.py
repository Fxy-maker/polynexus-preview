"""Deterministic representative-frame selection for SAXS figure recipes."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Sequence

import numpy as np

from .figure_common import SAXSFrameView, _coerce_numeric_array


@dataclass(frozen=True)
class SAXSFigureModeDecision:
    mode: str
    reason: str


def _declared_mode(engine: Any) -> str:
    condition_mode = str(getattr(engine, "_condition_type", "") or "").strip().lower()
    config_mode = str(
        getattr(getattr(engine, "cfg", None), "experiment_type", "") or ""
    ).strip().lower()
    if condition_mode in {"temperature", "strain"}:
        return condition_mode
    if config_mode in {"temperature", "strain"}:
        return config_mode
    if condition_mode == "static" or config_mode == "static":
        return "static"
    return "static"


def resolve_saxs_figure_mode(engine: Any) -> SAXSFigureModeDecision:
    """Resolve completed analysis state before consulting configuration hints."""

    temperature_result = getattr(engine, "_temperature_result", None)
    strain_result = getattr(engine, "_strain_result", None)
    if temperature_result is not None and strain_result is not None:
        return SAXSFigureModeDecision("unsupported", "mixed_completed_series")
    if temperature_result is not None:
        return SAXSFigureModeDecision("temperature", "completed_temperature_result")
    if strain_result is not None:
        return SAXSFigureModeDecision("strain", "completed_strain_result")
    declared = _declared_mode(engine)
    if declared == "temperature":
        return SAXSFigureModeDecision("incomplete", "temperature_result_missing")
    if declared == "strain":
        return SAXSFigureModeDecision("incomplete", "strain_result_missing")
    return SAXSFigureModeDecision("static", "static_analysis_state")


@dataclass(frozen=True)
class RepresentativeFrameSelection:
    """An immutable set of selected source indices and their provenance."""

    indices: tuple[int, ...]
    reasons: Mapping[int, str]
    source: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "indices", tuple(self.indices))
        object.__setattr__(self, "reasons", MappingProxyType(dict(self.reasons)))

    def to_payload(self) -> dict[str, Any]:
        """Return a detached JSON-safe representation for recipe persistence."""

        return {
            "indices": list(self.indices),
            "reasons": dict(self.reasons),
            "source": self.source,
        }


# Compatibility for callers that used the shorter draft name.
RepresentativeSelection = RepresentativeFrameSelection


def _finite_number(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return np.nan
    return number if np.isfinite(number) else np.nan


def _first_finite(*values: Any) -> float:
    for value in values:
        number = _finite_number(value)
        if np.isfinite(number):
            return number
    return np.nan


def _final_long_period(frame: SAXSFrameView) -> float:
    parameters = frame.parameters
    analysis = frame.analysis
    analysis_parameters = getattr(analysis, "final_parameters", {})
    if not isinstance(analysis_parameters, Mapping):
        analysis_parameters = {}
    long_period = getattr(analysis, "long_period", None)
    structure = getattr(analysis, "structure", None)
    return _first_finite(
        parameters.get("L_nm"),
        parameters.get("L_nm_effective"),
        parameters.get("L_nm_measured"),
        analysis_parameters.get("L_nm"),
        getattr(long_period, "L_best", np.nan),
        getattr(structure, "L", np.nan),
    )


def _display_q_star(frame: SAXSFrameView, long_period: float) -> float:
    parameters = frame.parameters
    analysis = frame.analysis
    analysis_parameters = getattr(analysis, "final_parameters", {})
    if not isinstance(analysis_parameters, Mapping):
        analysis_parameters = {}
    q_star = _first_finite(
        parameters.get("q_star_nm1"),
        parameters.get("q_star"),
        parameters.get("q_star_nm_inv"),
        analysis_parameters.get("q_star_nm1"),
        analysis_parameters.get("q_star"),
        getattr(analysis, "q_star_nm1", np.nan),
    )
    if np.isfinite(q_star):
        return q_star
    if np.isfinite(long_period) and long_period > 0:
        return float(2.0 * np.pi / long_period)
    return np.nan


def _intensity_features(frame: SAXSFrameView) -> tuple[float, float]:
    try:
        q = _coerce_numeric_array(frame.q)
        intensity = _coerce_numeric_array(frame.intensity)
    except (TypeError, ValueError):
        return np.nan, np.nan

    pair_count = min(q.size, intensity.size)
    q = q[:pair_count]
    intensity = intensity[:pair_count]
    finite_pairs = np.isfinite(q) & np.isfinite(intensity)
    finite_intensity = intensity[np.isfinite(intensity)]
    maximum = float(np.max(finite_intensity)) if finite_intensity.size else np.nan

    q = q[finite_pairs]
    intensity = intensity[finite_pairs]
    if q.size < 2:
        area = np.nan
    else:
        order = np.argsort(q, kind="stable")
        q = q[order]
        intensity = intensity[order]
        widths = np.diff(q)
        area = float(np.sum(widths * (intensity[:-1] + intensity[1:]) * 0.5))
    return area, maximum


def _log1p_feature(value: float) -> float:
    if not np.isfinite(value) or value <= -1.0:
        return np.nan
    return float(np.log1p(value))


def _transition_feature_vector(frame: SAXSFrameView) -> np.ndarray:
    long_period = _final_long_period(frame)
    q_star = _display_q_star(frame, long_period)
    area, maximum = _intensity_features(frame)
    log_area = _log1p_feature(area)
    log_maximum = _log1p_feature(maximum)
    return np.asarray([q_star, long_period, log_area, log_maximum], dtype=float)


def _mad_scaled_features(frames: Sequence[SAXSFrameView]) -> np.ndarray:
    features = np.vstack([_transition_feature_vector(frame) for frame in frames])
    scaled = np.zeros_like(features)
    for column_index in range(features.shape[1]):
        column = features[:, column_index]
        finite = np.isfinite(column)
        if not np.any(finite):
            continue
        median = float(np.median(column[finite]))
        scale = float(np.median(np.abs(column[finite] - median)))
        if not np.isfinite(scale) or scale <= np.finfo(float).eps:
            scale = float(np.std(column[finite]))
        if not np.isfinite(scale) or scale <= np.finfo(float).eps:
            continue
        scaled[finite, column_index] = (column[finite] - median) / scale
        # Missing emitted values contribute no artificial transition.
        scaled[~finite, column_index] = 0.0
    return scaled


def _condition_sort_key(frame: SAXSFrameView) -> tuple[int, float, int]:
    condition = _finite_number(frame.condition)
    return (
        0 if np.isfinite(condition) else 1,
        condition if np.isfinite(condition) else 0.0,
        frame.index,
    )


def _manual_selection(
    frames_by_index: Mapping[int, SAXSFrameView],
    manual_indices: Sequence[int],
    maximum: int,
) -> RepresentativeFrameSelection:
    indices = tuple(manual_indices)
    if not indices:
        raise ValueError("manual_indices must not be empty")
    if any(isinstance(index, bool) or not isinstance(index, (int, np.integer)) for index in indices):
        raise ValueError("manual indices must be integers")
    normalized = tuple(int(index) for index in indices)
    if len(set(normalized)) != len(normalized):
        raise ValueError("manual indices must be unique")
    if any(index not in frames_by_index for index in normalized):
        raise ValueError("override source index is unavailable")
    if len(normalized) > maximum:
        raise ValueError("manual selection exceeds maximum")

    selected_frames = sorted(
        (frames_by_index[index] for index in normalized),
        key=_condition_sort_key,
    )
    selected_indices = tuple(frame.index for frame in selected_frames)
    return RepresentativeFrameSelection(
        indices=selected_indices,
        reasons={index: "manual_override" for index in selected_indices},
        source="manual_override",
    )


def select_representative_frames(
    frames: Sequence[SAXSFrameView],
    *,
    maximum: int = 6,
    override_indices: Sequence[int] | None = None,
    minimum_separation: int = 2,
) -> RepresentativeFrameSelection:
    """Select endpoints plus the largest separated adjacent transitions."""

    if isinstance(maximum, bool) or not isinstance(maximum, (int, np.integer)) or maximum < 1:
        raise ValueError("maximum must be a positive integer")
    if (
        isinstance(minimum_separation, bool)
        or not isinstance(minimum_separation, (int, np.integer))
        or minimum_separation < 1
    ):
        raise ValueError("minimum_separation must be a positive integer")

    frame_tuple = tuple(frames)
    frames_by_index: dict[int, SAXSFrameView] = {}
    for frame in frame_tuple:
        if frame.index in frames_by_index:
            raise ValueError(f"duplicate SAXS source frame index: {frame.index}")
        frames_by_index[frame.index] = frame
    maximum = int(maximum)
    minimum_separation = int(minimum_separation)
    if override_indices is not None:
        return _manual_selection(frames_by_index, override_indices, maximum)
    frame_tuple = tuple(sorted(frame_tuple, key=_condition_sort_key))
    if not frame_tuple:
        return RepresentativeFrameSelection((), {}, "deterministic_transition")
    if len(frame_tuple) > 1 and maximum < 2:
        raise ValueError("maximum must retain both first and last frames")

    selected_positions = {0, len(frame_tuple) - 1}
    reasons: dict[int, str] = {
        frame_tuple[0].index: "first_frame",
        frame_tuple[-1].index: "last_frame",
    }
    if len(frame_tuple) == 1:
        reasons[frame_tuple[0].index] = "first_frame"
    elif len(frame_tuple) <= maximum:
        selected_positions.update(range(len(frame_tuple)))
        if len(frame_tuple) > 2:
            scaled = _mad_scaled_features(frame_tuple)
            changes = np.linalg.norm(np.diff(scaled, axis=0), axis=1)
            largest = min(
                range(1, len(frame_tuple) - 1),
                key=lambda index: (-float(changes[index - 1]), index),
            )
            reasons[frame_tuple[largest].index] = "largest_transition"
    else:
        scaled = _mad_scaled_features(frame_tuple)
        changes = np.linalg.norm(np.diff(scaled, axis=0), axis=1)
        ranked_transitions = sorted(
            range(1, len(frame_tuple)),
            key=lambda index: (-float(changes[index - 1]), index),
        )
        accepted_count = 0
        for index in ranked_transitions:
            if len(selected_positions) >= maximum:
                break
            if any(
                abs(index - selected) < minimum_separation
                for selected in selected_positions
            ):
                continue
            selected_positions.add(index)
            reasons[frame_tuple[index].index] = (
                "largest_transition" if accepted_count == 0 else "ranked_transition"
            )
            accepted_count += 1

    selected_frames = sorted(
        (frame_tuple[index] for index in selected_positions),
        key=_condition_sort_key,
    )
    selected_indices = tuple(frame.index for frame in selected_frames)
    for frame in selected_frames:
        reasons.setdefault(frame.index, "retained_transition")
    return RepresentativeFrameSelection(
        indices=selected_indices,
        reasons=reasons,
        source="deterministic_transition",
    )


__all__ = [
    "SAXSFigureModeDecision",
    "RepresentativeFrameSelection",
    "RepresentativeSelection",
    "resolve_saxs_figure_mode",
    "select_representative_frames",
]
