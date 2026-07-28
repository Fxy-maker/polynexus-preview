"""Serializable quality and evidence contracts for SAXS analysis.

The contracts in this module deliberately describe evidence and data quality;
they do not repair curves, choose a Guinier window, or replace physical gates.
Those operations remain in the existing deterministic analysis pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum
import json
from collections.abc import Iterable, Mapping
from types import MappingProxyType
from typing import Any

import numpy as np


class QualityLevel(str, Enum):
    """The strongest claim a frame or metric is currently allowed to carry."""

    QUANTITATIVE = "Quantitative"
    TREND = "Trend"
    DIAGNOSTIC = "Diagnostic"
    UNUSABLE = "Unusable"


def _quality_level(value: Any) -> QualityLevel:
    if isinstance(value, QualityLevel):
        return value
    try:
        return QualityLevel(str(value))
    except (TypeError, ValueError):
        return QualityLevel.UNUSABLE


def _finite_or_none(value: Any) -> Any:
    if isinstance(value, (float, np.floating)):
        number = float(value)
        return number if np.isfinite(number) else None
    if isinstance(value, (int, str, bool)) or value is None:
        return value
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def _jsonable(value: Any) -> Any:
    """Convert contract payloads to values accepted by strict ``json.dumps``."""
    if is_dataclass(value):
        return {
            item.name: _jsonable(getattr(value, item.name))
            for item in fields(value)
        }
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, np.ndarray):
        return [_jsonable(item) for item in value.tolist()]
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (np.integer, np.floating, np.bool_)):
        return _finite_or_none(value)
    if isinstance(value, float):
        return _finite_or_none(value)
    return value


def _contract_dict(value: Any) -> dict[str, Any]:
    payload = _jsonable(value)
    return dict(payload) if isinstance(payload, Mapping) else {}


def _freeze(value: Any) -> Any:
    """Recursively freeze nested contract payloads at construction time."""
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _freeze(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    return value


def _string_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(item) for item in value)


def _int_tuple(value: Any) -> tuple[int, ...]:
    if value is None:
        return ()
    if isinstance(value, (int, np.integer)):
        return (int(value),)
    if isinstance(value, (str, bytes)):
        value = (value,)
    try:
        items = iter(value)
    except TypeError:
        return ()
    result: list[int] = []
    for item in items:
        try:
            result.append(int(item))
        except (TypeError, ValueError):
            continue
    return tuple(result)
@dataclass(frozen=True)
class DataQualityReport:
    """Deterministic, non-mutating inventory of a 1D q-I input pair."""

    source_id: str = ""
    raw_data_ref: str = ""
    processed_data_ref: str = ""
    processing_config_ref: str = ""
    low_q_truncated: bool = False
    original_point_count: int = 0
    finite_point_count: int = 0
    usable_point_count: int = 0
    invalid_point_count: int = 0
    nonfinite_q_count: int = 0
    nonpositive_q_count: int = 0
    nonfinite_intensity_count: int = 0
    nonpositive_intensity_count: int = 0
    duplicate_q_count: int = 0
    nonmonotonic_q: bool = False
    actions: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    level: QualityLevel = QualityLevel.UNUSABLE

    def to_dict(self) -> dict[str, Any]:
        return _contract_dict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DataQualityReport":
        data = dict(payload)
        data["actions"] = _string_tuple(data.get("actions"))
        data["reason_codes"] = _string_tuple(data.get("reason_codes"))
        data["level"] = _quality_level(data.get("level"))
        return cls(**{key: data[key] for key in cls.__dataclass_fields__ if key in data})


@dataclass(frozen=True)
class DetectorQualityReport:
    """Non-mutating quality inventory for a 2D detector or sector map.

    Saturation is counted only when the caller supplies an explicit detector
    limit.  A sector-integrated map is intentionally reported as such rather
    than being presented as raw detector evidence.
    """

    shape: tuple[int, ...] = ()
    pixel_count: int = 0
    finite_pixel_count: int = 0
    nonfinite_pixel_count: int = 0
    nonpositive_pixel_count: int = 0
    masked_pixel_count: int = 0
    saturated_pixel_count: int = 0
    valid_pixel_count: int = 0
    coverage_fraction: float | None = None
    source_kind: str = "unknown"
    saturation_detection_available: bool = False
    beam_center_available: bool = False
    beam_center: tuple[float, float] | None = None
    geometry_provenance: Mapping[str, Any] | None = None
    mask_provenance: Mapping[str, Any] | None = None
    reason_codes: tuple[str, ...] = ()
    level: QualityLevel = QualityLevel.UNUSABLE

    def to_dict(self) -> dict[str, Any]:
        return _contract_dict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DetectorQualityReport":
        data = dict(payload)
        data["shape"] = _int_tuple(data.get("shape"))
        data["reason_codes"] = _string_tuple(data.get("reason_codes"))
        data["level"] = _quality_level(data.get("level"))
        center = data.get("beam_center")
        if center is not None:
            try:
                data["beam_center"] = (float(center[0]), float(center[1]))
            except (IndexError, TypeError, ValueError):
                data["beam_center"] = None
        return cls(**{key: data[key] for key in cls.__dataclass_fields__ if key in data})


def build_detector_quality_report(
    image: Any,
    *,
    mask: Any = None,
    saturation_value: Any = None,
    source_kind: str = "unknown",
    beam_center: Any = None,
    geometry_provenance: Mapping[str, Any] | None = None,
    mask_provenance: Mapping[str, Any] | None = None,
) -> DetectorQualityReport:
    """Build a strict, read-only quality report for a 2D intensity input."""

    reasons: list[str] = []
    normalized_source = str(source_kind or "unknown").strip().lower()
    if normalized_source not in {"raw_detector", "sector_map", "unknown"}:
        normalized_source = "unknown"
        reasons.append("source_kind_unknown")

    try:
        array = np.asarray(image, dtype=float)
    except (TypeError, ValueError):
        array = np.asarray([], dtype=float)
        reasons.append("detector_input_invalid")

    shape = tuple(int(item) for item in array.shape)
    pixel_count = int(array.size) if array.ndim == 2 else 0
    if array.ndim != 2:
        reasons.append("detector_input_not_2d")
    if pixel_count == 0:
        reasons.append("detector_input_empty")

    if array.ndim == 2:
        finite = np.isfinite(array)
        finite_count = int(np.count_nonzero(finite))
        nonfinite_count = int(array.size - finite_count)
        nonpositive_count = int(np.count_nonzero(finite & (array <= 0)))
    else:
        finite = np.zeros(array.shape, dtype=bool)
        finite_count = 0
        nonfinite_count = 0
        nonpositive_count = 0

    if mask is None:
        mask_array = np.zeros(array.shape, dtype=bool)
    else:
        try:
            candidate_mask = np.asarray(mask, dtype=bool)
        except (TypeError, ValueError):
            candidate_mask = np.asarray([], dtype=bool)
        if candidate_mask.shape == array.shape:
            mask_array = candidate_mask
        else:
            mask_array = np.zeros(array.shape, dtype=bool)
            reasons.append("mask_shape_mismatch")
    masked_count = int(np.count_nonzero(mask_array)) if array.ndim == 2 else 0

    saturation_available = False
    saturated = np.zeros(array.shape, dtype=bool)
    try:
        saturation = float(saturation_value) if saturation_value is not None else None
    except (TypeError, ValueError):
        saturation = None
        if saturation_value is not None:
            reasons.append("saturation_value_invalid")
    if saturation is not None and np.isfinite(saturation) and array.ndim == 2:
        saturation_available = True
        saturated = finite & (array == saturation)
    elif saturation_value is None:
        reasons.append("detector_saturation_unknown")
    else:
        reasons.append("detector_saturation_unknown")
    saturated_count = int(np.count_nonzero(saturated))

    center: tuple[float, float] | None = None
    if beam_center is not None:
        try:
            x_center = float(beam_center[0])
            y_center = float(beam_center[1])
            if np.isfinite(x_center) and np.isfinite(y_center):
                center = (x_center, y_center)
            else:
                reasons.append("beam_center_invalid")
        except (IndexError, TypeError, ValueError):
            reasons.append("beam_center_invalid")
    if center is None:
        reasons.append("beam_center_missing")

    valid = finite & (array > 0) & ~mask_array & ~saturated if array.ndim == 2 else finite
    valid_count = int(np.count_nonzero(valid))
    coverage = float(valid_count / pixel_count) if pixel_count else None

    if nonfinite_count:
        reasons.append("nonfinite_pixels")
    if nonpositive_count:
        reasons.append("nonpositive_pixels")
    if masked_count:
        reasons.append("masked_pixels")
    if saturated_count:
        reasons.append("saturated_pixels")
    if normalized_source == "unknown":
        reasons.append("source_kind_unknown")

    defect_reasons = {
        "detector_input_invalid", "detector_input_not_2d", "detector_input_empty",
        "mask_shape_mismatch", "saturation_value_invalid", "nonfinite_pixels",
        "nonpositive_pixels", "masked_pixels", "saturated_pixels", "beam_center_invalid",
    }
    if pixel_count == 0 or valid_count == 0:
        level = QualityLevel.UNUSABLE
    elif any(reason in defect_reasons for reason in reasons):
        level = QualityLevel.DIAGNOSTIC
    elif normalized_source == "raw_detector" and center is not None:
        level = QualityLevel.TREND
    else:
        level = QualityLevel.DIAGNOSTIC

    return DetectorQualityReport(
        shape=shape,
        pixel_count=pixel_count,
        finite_pixel_count=finite_count,
        nonfinite_pixel_count=nonfinite_count,
        nonpositive_pixel_count=nonpositive_count,
        masked_pixel_count=masked_count,
        saturated_pixel_count=saturated_count,
        valid_pixel_count=valid_count,
        coverage_fraction=coverage,
        source_kind=normalized_source,
        saturation_detection_available=saturation_available,
        beam_center_available=center is not None,
        beam_center=center,
        geometry_provenance=geometry_provenance,
        mask_provenance=mask_provenance,
        reason_codes=tuple(dict.fromkeys(reasons)),
        level=level,
    )


@dataclass(frozen=True)
class MetricEvidence:
    """Evidence bundle for one physical metric."""

    metric_name: str
    value: Any = None
    unit: str = ""
    level: QualityLevel = QualityLevel.UNUSABLE
    applicable: bool = False
    uncertainty: Any = None
    fit_evidence: Mapping[str, Any] = field(default_factory=dict)
    physical_checks: Mapping[str, Any] = field(default_factory=dict)
    reason_codes: tuple[str, ...] = ()
    source_ref: str = ""
    data_quality_ref: str = ""
    processing_ref: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "fit_evidence", _freeze(self.fit_evidence))
        object.__setattr__(self, "physical_checks", _freeze(self.physical_checks))

    def to_dict(self) -> dict[str, Any]:
        return _contract_dict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MetricEvidence":
        data = dict(payload)
        data["level"] = _quality_level(data.get("level"))
        data["reason_codes"] = _string_tuple(data.get("reason_codes"))
        return cls(**{key: data[key] for key in cls.__dataclass_fields__ if key in data})


@dataclass(frozen=True)
class MetricEvidenceSummary:
    """Conservative aggregation of one metric across a SAXS series."""

    metric_name: str
    frame_count: int = 0
    evidence_frame_count: int = 0
    usable_frame_count: int = 0
    diagnostic_frame_count: int = 0
    unusable_frame_count: int = 0
    missing_frame_count: int = 0
    coverage_fraction: float | None = None
    level: QualityLevel = QualityLevel.UNUSABLE
    applicable: bool = False
    level_counts: Mapping[str, int] = field(default_factory=dict)
    reason_codes: tuple[str, ...] = ()
    source_ref: str = ""
    evidence_frame_indices: tuple[int, ...] = ()
    missing_frame_indices: tuple[int, ...] = ()
    diagnostic_frame_indices: tuple[int, ...] = ()
    unusable_frame_indices: tuple[int, ...] = ()
    invalid_level_indices: tuple[int, ...] = ()
    frame_source_indices: tuple[int, ...] = ()
    condition_axis: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "level_counts", _freeze(self.level_counts))
        object.__setattr__(self, "reason_codes", _string_tuple(self.reason_codes))
        object.__setattr__(self, "condition_axis", _freeze(self.condition_axis))
        for field_name in (
            "evidence_frame_indices",
            "missing_frame_indices",
            "diagnostic_frame_indices",
            "unusable_frame_indices",
            "invalid_level_indices",
            "frame_source_indices",
        ):
            object.__setattr__(self, field_name, _int_tuple(getattr(self, field_name)))

    def to_dict(self) -> dict[str, Any]:
        return _contract_dict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MetricEvidenceSummary":
        data = dict(payload)
        data["level"] = _quality_level(data.get("level"))
        data["reason_codes"] = _string_tuple(data.get("reason_codes"))
        raw_counts = data.get("level_counts")
        data["level_counts"] = (
            {str(key): int(value) for key, value in raw_counts.items()}
            if isinstance(raw_counts, Mapping)
            else {}
        )
        for key in (
            "evidence_frame_indices",
            "missing_frame_indices",
            "diagnostic_frame_indices",
            "unusable_frame_indices",
            "invalid_level_indices",
            "frame_source_indices",
        ):
            data[key] = _int_tuple(data.get(key))
        raw_axis = data.get("condition_axis")
        data["condition_axis"] = raw_axis if isinstance(raw_axis, Mapping) else {}
        return cls(**{key: data[key] for key in cls.__dataclass_fields__ if key in data})


@dataclass(frozen=True)
class GuinierEvidence:
    """Evidence fields needed to decide whether an Rg result is quantitative."""

    rg_nm: float | None = None
    i0: float | None = None
    q_min_nm1: float | None = None
    q_max_nm1: float | None = None
    q_rg_max: float | None = None
    point_count: int = 0
    r_squared: float | None = None
    slope: float | None = None
    slope_uncertainty: float | None = None
    rg_uncertainty_nm: float | None = None
    assumption_supported: bool = False
    level: QualityLevel = QualityLevel.UNUSABLE
    reason_codes: tuple[str, ...] = ()
    metric: MetricEvidence | None = None

    def to_dict(self) -> dict[str, Any]:
        return _contract_dict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "GuinierEvidence":
        data = dict(payload)
        data["level"] = _quality_level(data.get("level"))
        data["reason_codes"] = _string_tuple(data.get("reason_codes"))
        metric = data.get("metric")
        data["metric"] = MetricEvidence.from_dict(metric) if isinstance(metric, Mapping) else None
        return cls(**{key: data[key] for key in cls.__dataclass_fields__ if key in data})


@dataclass(frozen=True)
class GuinierSequenceEvidence:
    """Evidence for whether a temperature sequence supports an Rg trend."""

    frame_count: int = 0
    finite_temperature_count: int = 0
    valid_frame_count: int = 0
    missing_frame_indices: tuple[int, ...] = ()
    diagnostic_frame_indices: tuple[int, ...] = ()
    invalid_temperature_indices: tuple[int, ...] = ()
    duplicate_temperature_indices: tuple[int, ...] = ()
    nonmonotonic_temperature_indices: tuple[int, ...] = ()
    continuity_break_indices: tuple[int, ...] = ()
    frame_source_indices: tuple[int, ...] = ()
    temperature_min_C: float | None = None
    temperature_max_C: float | None = None
    rg_min_nm: float | None = None
    rg_max_nm: float | None = None
    relative_change_stats: Mapping[str, Any] = field(default_factory=dict)
    level: QualityLevel = QualityLevel.UNUSABLE
    reason_codes: tuple[str, ...] = ()
    metric: MetricEvidence | None = None
    source_ref: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "missing_frame_indices", _int_tuple(self.missing_frame_indices))
        object.__setattr__(self, "diagnostic_frame_indices", _int_tuple(self.diagnostic_frame_indices))
        object.__setattr__(self, "invalid_temperature_indices", _int_tuple(self.invalid_temperature_indices))
        object.__setattr__(self, "duplicate_temperature_indices", _int_tuple(self.duplicate_temperature_indices))
        object.__setattr__(self, "nonmonotonic_temperature_indices", _int_tuple(self.nonmonotonic_temperature_indices))
        object.__setattr__(self, "continuity_break_indices", _int_tuple(self.continuity_break_indices))
        object.__setattr__(self, "frame_source_indices", _int_tuple(self.frame_source_indices))
        object.__setattr__(self, "relative_change_stats", _freeze(self.relative_change_stats))

    def to_dict(self) -> dict[str, Any]:
        return _contract_dict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "GuinierSequenceEvidence":
        data = dict(payload)
        for key in (
            "missing_frame_indices",
            "diagnostic_frame_indices",
            "invalid_temperature_indices",
            "duplicate_temperature_indices",
            "nonmonotonic_temperature_indices",
            "continuity_break_indices",
            "frame_source_indices",
        ):
            data[key] = _int_tuple(data.get(key))
        data["level"] = _quality_level(data.get("level"))
        data["reason_codes"] = _string_tuple(data.get("reason_codes"))
        metric = data.get("metric")
        data["metric"] = MetricEvidence.from_dict(metric) if isinstance(metric, Mapping) else None
        return cls(**{key: data[key] for key in cls.__dataclass_fields__ if key in data})


@dataclass(frozen=True)
class RescueCandidate:
    """A proposed deterministic or AI processing change awaiting validation."""

    candidate_id: str
    kind: str = "deterministic"
    parameters: Mapping[str, Any] = field(default_factory=dict)
    reason_codes: tuple[str, ...] = ()
    source: str = ""
    requires_validation: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "parameters", _freeze(self.parameters))

    def to_dict(self) -> dict[str, Any]:
        return _contract_dict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RescueCandidate":
        data = dict(payload)
        data["reason_codes"] = _string_tuple(data.get("reason_codes"))
        return cls(**{key: data[key] for key in cls.__dataclass_fields__ if key in data})


@dataclass(frozen=True)
class RescueValidationReport:
    """Hard-gate result for a rescue candidate.

    ``effective_decision`` records deterministic rejection reasons on the
    frozen object via ``object.__setattr__`` so the original report remains
    immutable to callers while the audit payload becomes self-explanatory.
    """

    candidate_id: str
    hard_gate_passed: bool = False
    physical_gate_passed: bool = False
    data_preserved: bool = False
    sequence_gate_passed: bool = True
    soft_score: float | None = None
    rejection_reasons: tuple[str, ...] = ()
    decision: str = "pending"

    def _computed_rejection_reasons(self) -> tuple[str, ...]:
        reasons = list(self.rejection_reasons)
        if not self.hard_gate_passed:
            reasons.append("hard_gate_failed")
        if not self.physical_gate_passed:
            reasons.append("physical_gate_failed")
        if not self.data_preserved:
            reasons.append("data_preservation_failed")
        if not self.sequence_gate_passed:
            reasons.append("sequence_gate_failed")
        return tuple(dict.fromkeys(reasons))

    def effective_decision(self) -> str:
        if self._computed_rejection_reasons():
            return "rejected"
        if self.decision == "accepted":
            return "accepted"
        if self.decision == "rejected":
            return "rejected"
        return "pending"

    def to_dict(self) -> dict[str, Any]:
        payload = _contract_dict(self)
        payload["rejection_reasons"] = list(self._computed_rejection_reasons())
        payload["decision"] = self.effective_decision()
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RescueValidationReport":
        data = dict(payload)
        data["rejection_reasons"] = _string_tuple(data.get("rejection_reasons"))
        return cls(**{key: data[key] for key in cls.__dataclass_fields__ if key in data})


def _as_1d_float_array(values: Any) -> np.ndarray:
    """Coerce a possibly dirty 1D axis without discarding valid neighbors."""
    try:
        return np.asarray(values, dtype=float).reshape(-1)
    except (TypeError, ValueError):
        pass

    try:
        raw_values = np.asarray(values, dtype=object)
    except (TypeError, ValueError):
        try:
            raw_values = np.asarray(list(values), dtype=object)
        except (TypeError, ValueError):
            raw_values = np.asarray([values], dtype=object)

    if raw_values.ndim == 0:
        items = (raw_values.item(),)
    else:
        items = tuple(raw_values.reshape(-1).tolist())

    coerced = np.full(len(items), np.nan, dtype=float)
    for index, item in enumerate(items):
        try:
            coerced[index] = float(item)
        except (TypeError, ValueError, OverflowError):
            continue
    return coerced


@dataclass(frozen=True)
class Sanitized1DProfile:
    """Detached, deterministic q/I profile used by 1D analysis."""

    q: np.ndarray
    intensity: np.ndarray
    original_point_count: int = 0
    aligned_point_count: int = 0
    usable_point_count: int = 0
    actions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        q_array = np.asarray(self.q, dtype=float).reshape(-1).copy()
        intensity_array = np.asarray(self.intensity, dtype=float).reshape(-1).copy()
        q_array.setflags(write=False)
        intensity_array.setflags(write=False)
        object.__setattr__(self, "q", q_array)
        object.__setattr__(self, "intensity", intensity_array)
        object.__setattr__(self, "actions", tuple(dict.fromkeys(_string_tuple(self.actions))))


def sanitize_1d_profile(q: Any, intensity: Any) -> Sanitized1DProfile:
    """Build a finite, positive, stably ordered analysis copy of q/I.

    The caller-owned arrays are never modified. Invalid pairs are excluded,
    surviving observations are stably sorted by q, and exact duplicate q
    observations are retained because no measurement-error model is available
    for a scientifically justified aggregation.
    """

    q_array = _as_1d_float_array(q)
    intensity_array = _as_1d_float_array(intensity)
    original_count = max(q_array.size, intensity_array.size)
    aligned_count = min(q_array.size, intensity_array.size)
    actions: list[str] = []

    if q_array.size != intensity_array.size:
        actions.append("axis_length_aligned")

    q_pair = q_array[:aligned_count]
    intensity_pair = intensity_array[:aligned_count]
    valid = (
        np.isfinite(q_pair)
        & np.isfinite(intensity_pair)
        & (q_pair > 0)
        & (intensity_pair > 0)
    )
    if int(np.count_nonzero(valid)) != aligned_count:
        actions.append("invalid_pairs_dropped")

    q_valid = q_pair[valid].copy()
    intensity_valid = intensity_pair[valid].copy()
    if q_valid.size > 1 and np.any(np.diff(q_valid) < 0):
        order = np.argsort(q_valid, kind="stable")
        q_valid = q_valid[order]
        intensity_valid = intensity_valid[order]
        actions.append("q_sorted")

    if q_valid.size > 1 and np.any(np.diff(q_valid) == 0):
        actions.append("duplicate_q_retained")

    return Sanitized1DProfile(
        q=q_valid,
        intensity=intensity_valid,
        original_point_count=int(original_count),
        aligned_point_count=int(aligned_count),
        usable_point_count=int(q_valid.size),
        actions=tuple(actions),
    )


def build_data_quality_report(
    q: Any,
    intensity: Any,
    *,
    source_id: str = "",
    raw_data_ref: str = "",
    processed_data_ref: str = "",
    processing_config_ref: str = "",
    low_q_truncated: bool = False,
    actions: tuple[str, ...] | list[str] = (),
) -> DataQualityReport:
    """Count input defects without sorting, repairing, or mutating q/I."""
    q_arr = _as_1d_float_array(q)
    i_arr = _as_1d_float_array(intensity)
    original_count = max(q_arr.size, i_arr.size)
    pair_count = min(q_arr.size, i_arr.size)
    q_pair = q_arr[:pair_count]
    i_pair = i_arr[:pair_count]

    finite_q = np.isfinite(q_arr)
    finite_i = np.isfinite(i_arr)
    pair_finite = np.isfinite(q_pair) & np.isfinite(i_pair)
    usable = pair_finite & (q_pair > 0) & (i_pair > 0)

    nonfinite_q_count = int(np.count_nonzero(~finite_q))
    nonpositive_q_count = int(np.count_nonzero(finite_q & (q_arr <= 0)))
    nonfinite_i_count = int(np.count_nonzero(~finite_i))
    nonpositive_i_count = int(np.count_nonzero(finite_i & (i_arr <= 0)))
    finite_q_values = q_arr[finite_q]
    unique_q_count = np.unique(finite_q_values).size if finite_q_values.size else 0
    duplicate_q_count = int(max(0, finite_q_values.size - unique_q_count))
    nonmonotonic_q = bool(
        finite_q_values.size > 1 and np.any(np.diff(finite_q_values) <= 0)
    )

    reasons: list[str] = []
    if q_arr.size != i_arr.size:
        reasons.append("axis_length_mismatch")
    if nonfinite_q_count:
        reasons.append("q_nonfinite")
    if nonpositive_q_count:
        reasons.append("q_nonpositive")
    if nonfinite_i_count:
        reasons.append("intensity_nonfinite")
    if nonpositive_i_count:
        reasons.append("intensity_nonpositive")
    if duplicate_q_count:
        reasons.append("q_duplicate")
    if nonmonotonic_q:
        reasons.append("q_nonmonotonic")
    if low_q_truncated:
        reasons.append("low_q_truncated")

    usable_count = int(np.count_nonzero(usable))
    if usable_count < 5:
        level = QualityLevel.UNUSABLE
        reasons.append("insufficient_points")
    elif low_q_truncated:
        level = QualityLevel.DIAGNOSTIC
    elif usable_count < 10:
        level = QualityLevel.DIAGNOSTIC
    elif reasons:
        level = QualityLevel.TREND
    else:
        level = QualityLevel.QUANTITATIVE

    return DataQualityReport(
        source_id=str(source_id or ""),
        raw_data_ref=str(raw_data_ref or ""),
        processed_data_ref=str(processed_data_ref or ""),
        processing_config_ref=str(processing_config_ref or ""),
        low_q_truncated=bool(low_q_truncated),
        original_point_count=int(original_count),
        finite_point_count=int(np.count_nonzero(pair_finite)),
        usable_point_count=usable_count,
        invalid_point_count=int(max(original_count - usable_count, 0)),
        nonfinite_q_count=nonfinite_q_count,
        nonpositive_q_count=nonpositive_q_count,
        nonfinite_intensity_count=nonfinite_i_count,
        nonpositive_intensity_count=nonpositive_i_count,
        duplicate_q_count=duplicate_q_count,
        nonmonotonic_q=nonmonotonic_q,
        actions=tuple(dict.fromkeys(_string_tuple(actions))),
        reason_codes=tuple(dict.fromkeys(reasons)),
        level=level,
    )


def build_guinier_evidence(
    q_guinier: Any,
    ln_i_guinier: Any,
    *,
    rg_nm: float | None,
    i0: float | None,
    quality_report: DataQualityReport,
    applicability: str = "unknown",
    source_ref: str = "",
) -> GuinierEvidence:
    """Build evidence and physical gates from an existing Guinier fit window.

    The function intentionally does not choose or repair the fit window.  The
    existing ``guinier_analysis`` implementation remains the source of the
    selected q/ln(I) points; this function only quantifies the evidence.
    """
    q_arr = _as_1d_float_array(q_guinier)
    y_arr = _as_1d_float_array(ln_i_guinier)
    pair_count = min(q_arr.size, y_arr.size)
    q_arr = q_arr[:pair_count]
    y_arr = y_arr[:pair_count]
    finite = np.isfinite(q_arr) & np.isfinite(y_arr)
    q_fit = q_arr[finite]
    y_fit = y_arr[finite]

    reasons: list[str] = []
    fit_evidence: dict[str, Any] = {"point_count": int(q_fit.size)}
    slope = np.nan
    slope_uncertainty = np.nan
    r_squared = np.nan
    rg_value = _finite_or_none(rg_nm)
    i0_value = _finite_or_none(i0)
    q_min = float(np.min(q_fit)) if q_fit.size else None
    q_max = float(np.max(q_fit)) if q_fit.size else None

    if q_fit.size < 5:
        reasons.append("guinier_fit_insufficient_points")
    else:
        x = q_fit**2
        try:
            coeff = np.polyfit(x, y_fit, 1)
            slope = float(coeff[0])
            intercept = float(coeff[1])
            predicted = np.polyval(coeff, x)
            residual = y_fit - predicted
            ss_res = float(np.sum(residual**2))
            ss_tot = float(np.sum((y_fit - float(np.mean(y_fit))) ** 2))
            r_squared = 1.0 - ss_res / ss_tot if ss_tot > 1e-15 else np.nan
            degrees_of_freedom = int(q_fit.size - 2)
            centered_x = x - float(np.mean(x))
            sxx = float(np.sum(centered_x**2))
            mse = ss_res / degrees_of_freedom if degrees_of_freedom > 0 else np.nan
            if np.isfinite(mse) and sxx > 1e-15:
                slope_uncertainty = float(np.sqrt(mse / sxx))
            fit_evidence.update(
                {
                    "intercept": intercept,
                    "slope": slope,
                    "r_squared": r_squared,
                    "rmse": float(np.sqrt(ss_res / q_fit.size)),
                    "degrees_of_freedom": degrees_of_freedom,
                }
            )
        except (TypeError, ValueError, np.linalg.LinAlgError):
            reasons.append("guinier_fit_failed")

    if not np.isfinite(slope) or slope >= 0:
        reasons.append("guinier_slope_nonnegative")
        if not (isinstance(rg_value, (int, float)) and rg_value > 0):
            rg_value = None
    elif not (isinstance(rg_value, (int, float)) and np.isfinite(rg_value) and rg_value > 0):
        rg_value = float(np.sqrt(-3.0 * slope))

    if isinstance(rg_value, (int, float)) and np.isfinite(rg_value) and rg_value > 0:
        if np.isfinite(slope_uncertainty):
            rg_uncertainty = float(3.0 * slope_uncertainty / (2.0 * rg_value))
        else:
            rg_uncertainty = None
        q_rg_max = float(q_max * rg_value) if q_max is not None else None
    else:
        rg_uncertainty = None
        q_rg_max = None

    if q_rg_max is None or q_rg_max >= 1.3:
        reasons.append("qrg_gate_failed")
    if not np.isfinite(r_squared) or r_squared < 0.90:
        reasons.append("guinier_fit_poor")

    normalized_applicability = str(applicability or "unknown").strip().lower()
    assumption_supported = normalized_applicability == "supported"
    if normalized_applicability == "unknown":
        reasons.append("guinier_applicability_unresolved")
    elif not assumption_supported:
        reasons.append("guinier_assumption_unsupported")

    if quality_report.level is QualityLevel.UNUSABLE:
        reasons.append("data_quality_unusable")

    fit_gate_passed = bool(
        q_fit.size >= 5
        and np.isfinite(slope)
        and slope < 0
        and isinstance(rg_value, (int, float))
        and np.isfinite(rg_value)
        and q_rg_max is not None
        and q_rg_max < 1.3
        and np.isfinite(r_squared)
        and r_squared >= 0.90
    )
    if quality_report.level is QualityLevel.UNUSABLE:
        level = QualityLevel.UNUSABLE
    elif not fit_gate_passed or not assumption_supported:
        level = QualityLevel.DIAGNOSTIC
    elif quality_report.level is QualityLevel.QUANTITATIVE and rg_uncertainty is not None:
        level = QualityLevel.QUANTITATIVE
    elif quality_report.level in {QualityLevel.QUANTITATIVE, QualityLevel.TREND}:
        level = QualityLevel.TREND
    else:
        level = QualityLevel.DIAGNOSTIC

    unique_reasons = tuple(dict.fromkeys(reasons))
    fit_evidence.update(
        {
            "q_min_nm1": q_min,
            "q_max_nm1": q_max,
            "slope_uncertainty": _finite_or_none(slope_uncertainty),
        }
    )
    physical_checks = {
        "q_rg_max": q_rg_max,
        "q_rg_limit": 1.3,
        "assumption_supported": assumption_supported,
        "fit_gate_passed": fit_gate_passed,
    }
    metric = MetricEvidence(
        metric_name="Rg",
        value=rg_value,
        unit="nm",
        level=level,
        applicable=bool(assumption_supported and fit_gate_passed),
        uncertainty=rg_uncertainty,
        fit_evidence=fit_evidence,
        physical_checks=physical_checks,
        reason_codes=unique_reasons,
        source_ref=str(source_ref or ""),
        data_quality_ref=str(
            quality_report.source_id
            or quality_report.raw_data_ref
            or quality_report.processed_data_ref
            or quality_report.processing_config_ref
            or ""
        ),
    )
    return GuinierEvidence(
        rg_nm=rg_value,
        i0=i0_value,
        q_min_nm1=q_min,
        q_max_nm1=q_max,
        q_rg_max=q_rg_max,
        point_count=int(q_fit.size),
        r_squared=_finite_or_none(r_squared),
        slope=_finite_or_none(slope),
        slope_uncertainty=_finite_or_none(slope_uncertainty),
        rg_uncertainty_nm=rg_uncertainty,
        assumption_supported=assumption_supported,
        level=level,
        reason_codes=unique_reasons,
        metric=metric,
    )


def _legacy_build_guinier_sequence_evidence(
    temperatures: Any,
    frame_evidence: Any,
    *,
    source_ref: str = "",
) -> GuinierSequenceEvidence:
    """Legacy sequence summary retained only for diff-local recovery.

    Only finite positive ``Rg`` values from quantitative or trend-level frame
    evidence are eligible for sequence diagnostics. Missing and diagnostic
    frames stay at their original positions, and sequence evidence is never
    promoted to a quantitative claim.
    """
    temperature_arr = _as_1d_float_array(temperatures)
    if frame_evidence is None:
        frame_items: list[Any] = []
    elif isinstance(frame_evidence, Mapping):
        frame_items = [frame_evidence]
    else:
        try:
            frame_items = list(frame_evidence)
        except TypeError:
            frame_items = []

    frame_count = max(int(temperature_arr.size), len(frame_items))
    finite_temperatures = np.isfinite(temperature_arr)
    finite_temperature_count = int(np.count_nonzero(finite_temperatures))
    invalid_temperature_indices = tuple(
        index
        for index in range(frame_count)
        if index >= temperature_arr.size or not finite_temperatures[index]
    )

    duplicate_indices: set[int] = set()
    for index in range(temperature_arr.size):
        if not finite_temperatures[index]:
            continue
        for previous in range(index):
            if finite_temperatures[previous] and np.isclose(
                temperature_arr[index], temperature_arr[previous], rtol=0.0, atol=1e-9
            ):
                duplicate_indices.update((previous, index))
                break

    missing_indices: list[int] = []
    diagnostic_indices: list[int] = []
    valid_indices: list[int] = []
    valid_rg: list[float] = []
    for index in range(frame_count):
        item = frame_items[index] if index < len(frame_items) else None
        if item is None:
            missing_indices.append(index)
            continue
        if hasattr(item, "to_dict"):
            item = item.to_dict()
        if not isinstance(item, Mapping):
            diagnostic_indices.append(index)
            continue
        level = _quality_level(item.get("level"))
        rg_value = _finite_or_none(item.get("rg_nm"))
        if (
            index < temperature_arr.size
            and np.isfinite(temperature_arr[index])
            and isinstance(rg_value, (int, float))
            and np.isfinite(rg_value)
            and rg_value > 0
            and level in {QualityLevel.QUANTITATIVE, QualityLevel.TREND}
        ):
            valid_indices.append(index)
            valid_rg.append(float(rg_value))
        else:
            diagnostic_indices.append(index)

    pair_indices: list[tuple[int, int]] = []
    relative_changes: list[float] = []
    for previous_index, current_index in zip(valid_indices, valid_indices[1:]):
        previous_rg = valid_rg[valid_indices.index(previous_index)]
        current_rg = valid_rg[valid_indices.index(current_index)]
        denominator = max(abs(previous_rg), 1e-12)
        pair_indices.append((previous_index, current_index))
        relative_changes.append(float((current_rg - previous_rg) / denominator))

    if relative_changes:
        median_change = float(np.median(relative_changes))
        mad_change = float(np.median(np.abs(np.asarray(relative_changes) - median_change)))
        max_absolute_change = float(np.max(np.abs(relative_changes)))
    else:
        median_change = 0.0
        mad_change = 0.0
        max_absolute_change = 0.0

    continuity_break_indices: list[int] = []
    continuity_threshold = max(0.25, 1.5 * mad_change)
    if len(valid_indices) >= 4:
        for (previous_index, current_index), change in zip(pair_indices, relative_changes):
            deviation = abs(change - median_change)
            same_direction = median_change != 0 and change * median_change > 0
            if deviation > continuity_threshold and not same_direction:
                continuity_break_indices.append(current_index)

    reason_codes: list[str] = []
    if frame_count != len(frame_items) or frame_count != int(temperature_arr.size):
        reason_codes.append("guinier_sequence_length_mismatch")
    if missing_indices:
        reason_codes.append("guinier_sequence_missing_frames")
    if diagnostic_indices:
        reason_codes.append("guinier_sequence_diagnostic_frames")
    if invalid_temperature_indices or duplicate_indices:
        reason_codes.append("guinier_sequence_temperature_axis_invalid")
    if continuity_break_indices:
        reason_codes.append("guinier_sequence_continuity_break")
    if not valid_indices:
        reason_codes.append("guinier_sequence_no_valid_frames")
    elif len(valid_indices) < 2:
        reason_codes.append("guinier_sequence_insufficient_frames")

    axis_valid = not invalid_temperature_indices and not duplicate_indices and frame_count == len(frame_items)
    if not valid_indices:
        level = QualityLevel.UNUSABLE
    elif len(valid_indices) < 2 or not axis_valid:
        level = QualityLevel.DIAGNOSTIC
    else:
        level = QualityLevel.TREND

    finite_temperature_values = temperature_arr[finite_temperatures]
    relative_stats = {
        "pair_count": int(len(relative_changes)),
        "median_relative_change": median_change,
        "mad_relative_change": mad_change,
        "max_absolute_relative_change": max_absolute_change,
        "continuity_threshold": continuity_threshold,
        "relative_changes": tuple(relative_changes),
        "pair_indices": tuple(pair_indices),
    }
    metric = MetricEvidence(
        metric_name="Rg_sequence",
        value=int(len(valid_indices)),
        unit="frames",
        level=level,
        applicable=bool(len(valid_indices) >= 2 and axis_valid),
        fit_evidence=relative_stats,
        physical_checks={
            "temperature_axis_valid": axis_valid,
            "continuity_break_count": len(continuity_break_indices),
            "valid_frame_count": len(valid_indices),
        },
        reason_codes=tuple(dict.fromkeys(reason_codes)),
        source_ref=str(source_ref or ""),
        data_quality_ref=str(source_ref or ""),
    )
    return GuinierSequenceEvidence(
        frame_count=frame_count,
        finite_temperature_count=finite_temperature_count,
        valid_frame_count=len(valid_indices),
        missing_frame_indices=tuple(missing_indices),
        diagnostic_frame_indices=tuple(diagnostic_indices),
        invalid_temperature_indices=invalid_temperature_indices,
        duplicate_temperature_indices=tuple(sorted(duplicate_indices)),
        continuity_break_indices=tuple(continuity_break_indices),
        temperature_min_C=(float(np.min(finite_temperature_values)) if finite_temperature_values.size else None),
        temperature_max_C=(float(np.max(finite_temperature_values)) if finite_temperature_values.size else None),
        rg_min_nm=(float(np.min(valid_rg)) if valid_rg else None),
        rg_max_nm=(float(np.max(valid_rg)) if valid_rg else None),
        relative_change_stats=relative_stats,
        level=level,
        reason_codes=tuple(dict.fromkeys(reason_codes)),
        metric=metric,
    )


def _sequence_frame_payload(frame: Any) -> tuple[float | None, QualityLevel, bool]:
    if frame is None:
        return None, QualityLevel.UNUSABLE, False
    if isinstance(frame, GuinierEvidence):
        return _finite_or_none(frame.rg_nm), frame.level, True
    if hasattr(frame, "to_dict"):
        frame = frame.to_dict()
    if not isinstance(frame, Mapping):
        return None, QualityLevel.UNUSABLE, True
    rg_value = _finite_or_none(frame.get("rg_nm"))
    level = _quality_level(frame.get("level"))
    return rg_value if isinstance(rg_value, (int, float)) else None, level, True


def build_guinier_sequence_evidence(
    temperatures: Any,
    frame_evidence: Any,
    *,
    source_indices: Any = None,
    source_ref: str = "",
) -> GuinierSequenceEvidence:
    """Summarize Rg evidence across observed temperature frames.

    The builder is deliberately observational: it never sorts, interpolates,
    smooths, deletes, or rewrites a frame.  A sequence-level ``Trend`` is only
    a statement that at least two eligible observations share a valid axis; it
    never upgrades a frame or creates a sequence-level quantitative claim.
    """
    temperature_arr = _as_1d_float_array(temperatures)
    try:
        frames = list(frame_evidence) if frame_evidence is not None else []
    except TypeError:
        frames = []
    frame_count = max(int(temperature_arr.size), len(frames))
    frame_source_indices = _int_tuple(source_indices)
    source_index_mapping_mismatch = (
        source_indices is not None and len(frame_source_indices) != frame_count
    )

    reasons: list[str] = []
    missing_indices: list[int] = []
    diagnostic_indices: list[int] = []
    invalid_temperature_indices: list[int] = []
    duplicate_temperature_indices: list[int] = []
    nonmonotonic_temperature_indices: list[int] = []
    valid_indices: list[int] = []
    valid_rg: list[float] = []
    finite_temperature_count = 0

    if isinstance(frame_evidence, Mapping) or isinstance(frame_evidence, GuinierEvidence):
        frames = [frame_evidence]
        frame_count = max(int(temperature_arr.size), len(frames))
    if temperature_arr.size != len(frames):
        reasons.append("guinier_sequence_length_mismatch")
    if source_index_mapping_mismatch:
        reasons.append("guinier_sequence_source_index_mismatch")

    for index in range(frame_count):
        temperature = float(temperature_arr[index]) if index < temperature_arr.size else np.nan
        temperature_is_valid = bool(np.isfinite(temperature))
        if temperature_is_valid:
            finite_temperature_count += 1
        else:
            invalid_temperature_indices.append(index)

        rg_value, level, has_payload = _sequence_frame_payload(
            frames[index] if index < len(frames) else None
        )
        eligible = bool(
            has_payload
            and level in {QualityLevel.QUANTITATIVE, QualityLevel.TREND}
            and isinstance(rg_value, (int, float))
            and np.isfinite(rg_value)
            and rg_value > 0
        )
        if not has_payload:
            missing_indices.append(index)
        elif not eligible or not temperature_is_valid:
            diagnostic_indices.append(index)
        if eligible and temperature_is_valid:
            valid_indices.append(index)
            valid_rg.append(float(rg_value))

    for position, temperature in enumerate(temperature_arr):
        if not np.isfinite(temperature):
            continue
        previous = temperature_arr[:position]
        duplicate_positions = np.flatnonzero(
            np.isclose(previous, temperature, rtol=0.0, atol=1e-12, equal_nan=False)
        )
        if duplicate_positions.size:
            duplicate_temperature_indices.extend(int(item) for item in duplicate_positions)
            duplicate_temperature_indices.append(position)
        if position and np.isfinite(temperature_arr[position - 1]) and temperature <= temperature_arr[position - 1]:
            nonmonotonic_temperature_indices.append(position)

    if invalid_temperature_indices or duplicate_temperature_indices or nonmonotonic_temperature_indices:
        reasons.append("guinier_sequence_temperature_axis_invalid")
    if missing_indices:
        reasons.append("guinier_sequence_missing_frames")
    if diagnostic_indices:
        reasons.append("guinier_sequence_diagnostic_frames")
    if not valid_indices:
        reasons.append("guinier_sequence_no_valid_frames")
    elif len(valid_indices) < 2:
        reasons.append("guinier_sequence_insufficient_frames")

    relative_changes: list[float] = []
    for previous, current in zip(valid_rg, valid_rg[1:]):
        denominator = max(abs(previous), 1e-12)
        relative_changes.append(float(abs(current - previous) / denominator))

    continuity_break_indices: list[int] = []
    local_deviations: list[float] = []
    if len(valid_rg) >= 4:
        for position in range(1, len(valid_rg) - 1):
            neighbor_mean = (valid_rg[position - 1] + valid_rg[position + 1]) / 2.0
            denominator = max(abs(neighbor_mean), 1e-12)
            local_deviations.append(float(abs(valid_rg[position] - neighbor_mean) / denominator))
        baseline = float(np.median(local_deviations))
        mad = float(np.median(np.abs(np.asarray(local_deviations) - baseline)))
        threshold = max(0.5, 3.0 * mad)
        for position, deviation in enumerate(local_deviations, start=1):
            if deviation > threshold:
                continuity_break_indices.append(valid_indices[position])
    else:
        baseline = mad = 0.0
        threshold = np.nan

    if continuity_break_indices:
        reasons.append("guinier_sequence_continuity_break")

    if not valid_indices:
        level = QualityLevel.UNUSABLE
    elif (
        len(valid_indices) < 2
        or invalid_temperature_indices
        or duplicate_temperature_indices
        or nonmonotonic_temperature_indices
        or source_index_mapping_mismatch
    ):
        level = QualityLevel.DIAGNOSTIC
    else:
        level = QualityLevel.TREND

    relative_stats = {
        "sample_count": len(relative_changes),
        "pair_count": len(relative_changes),
        "relative_change_median": float(np.median(relative_changes)) if relative_changes else 0.0,
        "relative_change_mad": float(np.median(np.abs(np.asarray(relative_changes) - np.median(relative_changes)))) if relative_changes else 0.0,
        "relative_change_max": float(max(relative_changes)) if relative_changes else 0.0,
        "median_relative_change": float(np.median(relative_changes)) if relative_changes else 0.0,
        "mad_relative_change": float(np.median(np.abs(np.asarray(relative_changes) - np.median(relative_changes)))) if relative_changes else 0.0,
        "max_absolute_relative_change": float(max(relative_changes)) if relative_changes else 0.0,
        "relative_changes": tuple(relative_changes),
        "pair_indices": tuple(zip(valid_indices, valid_indices[1:])),
        "frame_source_indices": frame_source_indices,
        "pair_source_indices": (
            tuple(
                zip(
                    [frame_source_indices[index] for index in valid_indices],
                    [frame_source_indices[index] for index in valid_indices[1:]],
                )
            )
            if len(frame_source_indices) == frame_count
            else ()
        ),
        "local_deviation_median": _finite_or_none(baseline),
        "local_deviation_mad": _finite_or_none(mad),
        "local_deviation_threshold": _finite_or_none(threshold),
    }
    temperature_values = [float(value) for value in temperature_arr if np.isfinite(value)]
    rg_values = valid_rg
    metric = MetricEvidence(
        metric_name="Rg_sequence",
        value=int(len(valid_indices)),
        unit="frames",
        level=level,
        applicable=level is QualityLevel.TREND,
        fit_evidence=relative_stats,
        physical_checks={
            "sequence_axis_valid": not bool(
                invalid_temperature_indices or duplicate_temperature_indices or nonmonotonic_temperature_indices
            ),
            "temperature_axis_valid": not bool(
                invalid_temperature_indices or duplicate_temperature_indices or nonmonotonic_temperature_indices
            ),
            "source_index_mapping_valid": not source_index_mapping_mismatch,
            "interpolation_used": False,
            "continuity_break_count": len(continuity_break_indices),
        },
        reason_codes=tuple(dict.fromkeys(reasons)),
        source_ref=str(source_ref or ""),
        data_quality_ref=str(source_ref or ""),
    )
    return GuinierSequenceEvidence(
        frame_count=frame_count,
        finite_temperature_count=finite_temperature_count,
        valid_frame_count=len(valid_indices),
        missing_frame_indices=tuple(missing_indices),
        diagnostic_frame_indices=tuple(diagnostic_indices),
        invalid_temperature_indices=tuple(invalid_temperature_indices),
        duplicate_temperature_indices=tuple(sorted(set(duplicate_temperature_indices))),
        nonmonotonic_temperature_indices=tuple(nonmonotonic_temperature_indices),
        continuity_break_indices=tuple(continuity_break_indices),
        frame_source_indices=frame_source_indices,
        temperature_min_C=float(min(temperature_values)) if temperature_values else None,
        temperature_max_C=float(max(temperature_values)) if temperature_values else None,
        rg_min_nm=float(min(rg_values)) if rg_values else None,
        rg_max_nm=float(max(rg_values)) if rg_values else None,
        relative_change_stats=relative_stats,
        level=level,
        reason_codes=tuple(dict.fromkeys(reasons)),
        metric=metric,
        source_ref=str(source_ref or ""),
    )


def _method_applicability(applicability: str, method_name: str, reasons: list[str]) -> bool:
    normalized = str(applicability or "unknown").strip().lower()
    if normalized == "unknown":
        reasons.append(f"{method_name}_applicability_unresolved")
    elif normalized != "supported":
        reasons.append(f"{method_name}_applicability_unsupported")
    return normalized == "supported"


def _finish_method_metric(
    *,
    method_name: str,
    value: Any,
    unit: str,
    quality_report: DataQualityReport | None,
    applicability: str,
    physical_gate_passed: bool,
    reasons: list[str],
    fit_evidence: Mapping[str, Any],
    physical_checks: Mapping[str, Any],
    uncertainty: Any = None,
    source_ref: str = "",
) -> MetricEvidence:
    supported = _method_applicability(applicability, method_name.lower(), reasons)
    if quality_report is None or quality_report.level is QualityLevel.UNUSABLE:
        reasons.append("data_quality_unusable")
        level = QualityLevel.UNUSABLE
    elif not physical_gate_passed or not supported:
        level = QualityLevel.DIAGNOSTIC
    else:
        # Method-specific quantitative cutoffs are intentionally deferred until
        # real-data calibration; this stage only establishes Trend evidence.
        level = QualityLevel.TREND
    unique_reasons = tuple(dict.fromkeys(reasons))
    checks = dict(physical_checks)
    checks["applicability_supported"] = supported
    checks["method_gate_passed"] = bool(physical_gate_passed)
    return MetricEvidence(
        metric_name=method_name,
        value=_finite_or_none(value),
        unit=unit,
        level=level,
        applicable=bool(supported and physical_gate_passed and level is not QualityLevel.UNUSABLE),
        uncertainty=_finite_or_none(uncertainty),
        fit_evidence=dict(fit_evidence),
        physical_checks=checks,
        reason_codes=unique_reasons,
        source_ref=str(source_ref or ""),
        data_quality_ref=str(
            quality_report.source_id
            if quality_report is not None and quality_report.source_id
            else source_ref or ""
        ),
    )


def build_porod_evidence(
    porod: Mapping[str, Any] | None,
    *,
    quality_report: DataQualityReport,
    applicability: str = "unknown",
    source_ref: str = "",
) -> MetricEvidence:
    """Build conservative evidence from the existing Porod result payload."""
    reasons: list[str] = []
    payload = porod if isinstance(porod, Mapping) else {}
    if not payload:
        reasons.append("porod_payload_missing")
    q_arr = _as_1d_float_array(payload.get("q_porod"))
    iq4_arr = _as_1d_float_array(payload.get("Iq4", payload.get("Iq4_porod")))
    pair_count = min(q_arr.size, iq4_arr.size)
    finite = np.isfinite(q_arr[:pair_count]) & np.isfinite(iq4_arr[:pair_count])
    q_fit = q_arr[:pair_count][finite]
    iq4_fit = iq4_arr[:pair_count][finite]
    if q_fit.size < 10:
        reasons.append("porod_insufficient_points")
    kp = _finite_or_none(payload.get("Kp"))
    if not (isinstance(kp, (int, float)) and np.isfinite(kp) and kp > 0):
        reasons.append("porod_kp_missing")
        kp = None
    slope = _finite_or_none(payload.get("slope"))
    if slope is None:
        reasons.append("porod_slope_missing")
    iq4_median = float(np.median(iq4_fit)) if iq4_fit.size else None
    iq4_cv = (
        float(np.std(iq4_fit) / max(abs(iq4_median), 1e-12))
        if iq4_fit.size and iq4_median is not None
        else None
    )
    slope_deviation = abs(float(slope) + 4.0) if isinstance(slope, (int, float)) else None
    if slope_deviation is not None and slope_deviation > 0:
        reasons.append("porod_slope_deviation_observed")
    return _finish_method_metric(
        method_name="Porod",
        value=kp,
        unit="a.u.",
        quality_report=quality_report,
        applicability=applicability,
        physical_gate_passed=bool(q_fit.size >= 10 and kp is not None and slope is not None),
        reasons=reasons,
        fit_evidence={
            "point_count": int(q_fit.size),
            "q_min_nm1": float(np.min(q_fit)) if q_fit.size else None,
            "q_max_nm1": float(np.max(q_fit)) if q_fit.size else None,
            "slope": slope,
            "slope_reference": -4.0,
            "slope_deviation": slope_deviation,
            "iq4_plateau_median": iq4_median,
            "iq4_plateau_cv": iq4_cv,
        },
        physical_checks={"Kp_positive": kp is not None, "Sv": _finite_or_none(payload.get("Sv"))},
        source_ref=source_ref or "saxs_engine.porod_analysis",
    )


def build_kratky_evidence(
    kratky: Mapping[str, Any] | None,
    *,
    quality_report: DataQualityReport,
    applicability: str = "unknown",
    source_ref: str = "",
) -> MetricEvidence:
    """Build conservative evidence from the existing Kratky payload."""
    reasons: list[str] = []
    payload = kratky if isinstance(kratky, Mapping) else {}
    if not payload:
        reasons.append("kratky_payload_missing")
    q_arr = _as_1d_float_array(payload.get("q"))
    k_arr = _as_1d_float_array(payload.get("kratky"))
    pair_count = min(q_arr.size, k_arr.size)
    finite = np.isfinite(q_arr[:pair_count]) & np.isfinite(k_arr[:pair_count])
    q_fit = q_arr[:pair_count][finite]
    k_fit = k_arr[:pair_count][finite]
    q_peak = _finite_or_none(payload.get("q_peak_kratky"))
    peak_value = float(np.max(k_fit)) if k_fit.size else None
    if q_fit.size < 5:
        reasons.append("kratky_insufficient_points")
    if q_peak is None or not (isinstance(q_peak, (int, float)) and q_peak > 0):
        reasons.append("kratky_peak_missing")
        q_peak = None
    return _finish_method_metric(
        method_name="Kratky",
        value=q_peak,
        unit="nm^-1",
        quality_report=quality_report,
        applicability=applicability,
        physical_gate_passed=bool(q_fit.size >= 5 and q_peak is not None),
        reasons=reasons,
        fit_evidence={
            "point_count": int(q_fit.size),
            "q_min_nm1": float(np.min(q_fit)) if q_fit.size else None,
            "q_max_nm1": float(np.max(q_fit)) if q_fit.size else None,
            "q_peak_nm1": q_peak,
            "peak_value": peak_value,
            "peak_present": bool(q_peak is not None),
        },
        physical_checks={"peak_present": bool(q_peak is not None)},
        source_ref=source_ref or "saxs_engine.kratky_analysis",
    )


def build_invariant_evidence(
    q_star: Any,
    *,
    quality_report: DataQualityReport,
    valid: bool = True,
    beam_stop_contaminated: bool = False,
    applicability: str = "unknown",
    source_ref: str = "",
) -> MetricEvidence:
    """Build evidence for the existing Porod invariant value."""
    reasons: list[str] = []
    value = _finite_or_none(q_star)
    if value is None or not (isinstance(value, (int, float)) and value > 0):
        reasons.append("invariant_value_invalid")
        value = None
    if not valid:
        reasons.append("invariant_quality_flag_failed")
    if beam_stop_contaminated:
        reasons.append("invariant_beamstop_contaminated")
    return _finish_method_metric(
        method_name="Q_star",
        value=value,
        unit="a.u.",
        quality_report=quality_report,
        applicability=applicability,
        physical_gate_passed=bool(value is not None and valid and not beam_stop_contaminated),
        reasons=reasons,
        fit_evidence={"finite_positive": bool(value is not None)},
        physical_checks={
            "valid": bool(valid),
            "beam_stop_contaminated": bool(beam_stop_contaminated),
        },
        source_ref=source_ref or "saxs_engine.scattering_invariant",
    )


def build_lamellar_evidence(
    long_period: Any,
    structure: Any,
    *,
    quality_report: DataQualityReport,
    applicability: str = "unknown",
    source_ref: str = "",
) -> MetricEvidence:
    """Build evidence from existing ensemble and structure DTOs."""
    reasons: list[str] = []
    L = _finite_or_none(getattr(long_period, "L_best", np.nan)) if long_period is not None else None
    lc = _finite_or_none(getattr(structure, "lc", np.nan)) if structure is not None else None
    la = _finite_or_none(getattr(structure, "la", np.nan)) if structure is not None else None
    phi_c = _finite_or_none(getattr(structure, "phi_c", np.nan)) if structure is not None else None
    confidence = _finite_or_none(getattr(structure, "confidence_lc", np.nan)) if structure is not None else None
    if L is None or not (isinstance(L, (int, float)) and L > 0):
        reasons.append("lamellar_long_period_missing")
        L = None
    if lc is None or not (isinstance(lc, (int, float)) and lc > 0):
        reasons.append("lamellar_lc_missing")
        lc = None
    if la is None or not (isinstance(la, (int, float)) and la > 0):
        reasons.append("lamellar_la_missing")
        la = None
    phi_valid = isinstance(phi_c, (int, float)) and np.isfinite(phi_c) and 0 < phi_c <= 1
    if not phi_valid:
        reasons.append("lamellar_phi_c_invalid")
        phi_c = None
    structure_gate = bool(L is not None and lc is not None and la is not None and phi_valid)
    return _finish_method_metric(
        method_name="Lamellar",
        value=L,
        unit="nm",
        quality_report=quality_report,
        applicability=applicability,
        physical_gate_passed=structure_gate,
        reasons=reasons,
        fit_evidence={
            "L_nm": L,
            "lc_nm": lc,
            "la_nm": la,
            "phi_c": phi_c,
            "confidence_lc": confidence,
            "method_used": getattr(long_period, "method_used", "") if long_period is not None else "",
        },
        physical_checks={
            "positive_dimensions": bool(L is not None and lc is not None and la is not None),
            "phi_c_in_range": bool(phi_valid),
        },
        source_ref=source_ref or "saxs_engine.compute_structure_params",
    )


def build_orientation_evidence(
    anisotropy_payload: Mapping[str, Any] | None,
    detector_quality: DetectorQualityReport,
    *,
    applicability: str = "unknown",
    source_ref: str = "",
) -> MetricEvidence:
    """Wrap existing anisotropy outputs in conservative orientation evidence.

    This builder reports whether the current evidence is usable; it does not
    add orientation thresholds or reinterpret a pattern label as a material
    mechanism.
    """

    payload = anisotropy_payload if isinstance(anisotropy_payload, Mapping) else {}
    numeric_fields = (
        "f_herman", "P2", "P4", "anisotropy_ratio", "anisotropy_index", "confidence"
    )
    fit_evidence: dict[str, Any] = {}
    for key in numeric_fields:
        value = _finite_or_none(payload.get(key))
        if value is not None:
            fit_evidence[key] = value
    pattern_type = payload.get("pattern_type")
    if isinstance(pattern_type, str) and pattern_type.strip() and pattern_type != "unknown":
        fit_evidence["pattern_type"] = pattern_type
    metrics_present = bool(fit_evidence)

    normalized_applicability = str(applicability or "unknown").strip().lower()
    supported = normalized_applicability == "supported"
    reasons: list[str] = []
    if not metrics_present:
        reasons.append("orientation_metrics_missing")
    if normalized_applicability == "unknown":
        reasons.append("applicability_unresolved")
    elif not supported:
        reasons.append("orientation_applicability_unsupported")
    if detector_quality.level is QualityLevel.UNUSABLE:
        reasons.append("detector_quality_unusable")
    elif detector_quality.level is QualityLevel.DIAGNOSTIC:
        reasons.append("detector_quality_diagnostic")

    physical_checks = {
        "detector_source_kind": detector_quality.source_kind,
        "detector_quality_level": detector_quality.level,
        "detector_coverage_fraction": detector_quality.coverage_fraction,
        "detector_saturation_detection_available": detector_quality.saturation_detection_available,
        "detector_beam_center_available": detector_quality.beam_center_available,
        "detector_quality_report": detector_quality.to_dict(),
        "applicability_supported": supported,
        "orientation_metrics_present": metrics_present,
    }
    if not metrics_present or detector_quality.level is QualityLevel.UNUSABLE:
        level = QualityLevel.UNUSABLE
    elif not supported or detector_quality.level is QualityLevel.DIAGNOSTIC:
        level = QualityLevel.DIAGNOSTIC
    else:
        # Orientation remains a Trend claim until calibrated physical gates
        # are explicitly defined and validated on real detector data.
        level = QualityLevel.TREND

    return MetricEvidence(
        metric_name="Orientation",
        value=dict(fit_evidence),
        unit="",
        level=level,
        applicable=bool(level is QualityLevel.TREND and supported and metrics_present),
        fit_evidence=fit_evidence,
        physical_checks=physical_checks,
        reason_codes=tuple(dict.fromkeys(reasons)),
        source_ref=str(source_ref or ""),
        data_quality_ref="detector_quality_report",
    )


def build_series_metric_evidence(
    frame_evidence: Iterable[Mapping[str, Any] | None] | None,
    *,
    metric_names: Iterable[str] | None = None,
    source_ref: str = "",
    frame_source_indices: Iterable[Any] | None = None,
    condition_name: str = "",
    condition_values: Iterable[Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """Summarize existing per-frame metric evidence without mutating it."""

    frames = list(frame_evidence or ())
    source_indices_supplied = frame_source_indices is not None
    source_indices = _int_tuple(frame_source_indices)
    source_index_mapping_valid = not source_indices_supplied or len(source_indices) == len(frames)
    if not source_index_mapping_valid:
        source_indices = ()
    condition_values_supplied = condition_values is not None
    condition_axis: dict[str, Any] = {}
    condition_axis_reason = ""
    if condition_values_supplied:
        try:
            raw_conditions = list(condition_values)
        except TypeError:
            raw_conditions = []
        condition_name_text = str(condition_name or "")
        if len(raw_conditions) != len(frames):
            condition_axis = {
                "condition_name": condition_name_text,
                "condition_values": [],
                "invalid_condition_indices": [],
                "duplicate_condition_indices": [],
                "nonmonotonic_condition_indices": [],
                "status": "diagnostic",
            }
            condition_axis_reason = "series_metric_condition_axis_length_mismatch"
        else:
            normalized_conditions: list[float | None] = []
            invalid_condition_indices: list[int] = []
            for position, raw_value in enumerate(raw_conditions):
                try:
                    value = float(raw_value)
                except (TypeError, ValueError):
                    value = np.nan
                if not np.isfinite(value):
                    normalized_conditions.append(None)
                    invalid_condition_indices.append(position)
                else:
                    normalized_conditions.append(float(value))

            duplicate_condition_indices: list[int] = []
            for position, value in enumerate(normalized_conditions):
                if value is None:
                    continue
                previous_positions = [
                    previous
                    for previous, previous_value in enumerate(normalized_conditions[:position])
                    if previous_value is not None
                    and np.isclose(previous_value, value, rtol=0.0, atol=1e-12)
                ]
                if previous_positions:
                    duplicate_condition_indices.extend(previous_positions)
                    duplicate_condition_indices.append(position)
            duplicate_condition_indices = list(dict.fromkeys(duplicate_condition_indices))

            nonmonotonic_condition_indices = [
                position
                for position in range(1, len(normalized_conditions))
                if normalized_conditions[position] is not None
                and normalized_conditions[position - 1] is not None
                and normalized_conditions[position] <= normalized_conditions[position - 1]
            ]
            axis_defective = bool(
                invalid_condition_indices
                or duplicate_condition_indices
                or nonmonotonic_condition_indices
            )
            condition_axis = {
                "condition_name": condition_name_text,
                "condition_values": normalized_conditions,
                "invalid_condition_indices": invalid_condition_indices,
                "duplicate_condition_indices": duplicate_condition_indices,
                "nonmonotonic_condition_indices": nonmonotonic_condition_indices,
                "status": (
                    "empty"
                    if not frames
                    else "diagnostic"
                    if axis_defective
                    else "ordered"
                ),
            }
            if axis_defective:
                condition_axis_reason = "series_metric_condition_axis_invalid"
    names = {str(name) for name in (metric_names or ()) if str(name)}
    if metric_names is None:
        for frame in frames:
            if isinstance(frame, Mapping):
                names.update(str(name) for name in frame if str(name))

    summaries: dict[str, dict[str, Any]] = {}
    for metric_name in sorted(names):
        level_counts = {level.value: 0 for level in QualityLevel}
        reasons: list[str] = []
        evidence_frame_count = 0
        usable_frame_count = 0
        diagnostic_frame_count = 0
        unusable_frame_count = 0
        missing_frame_count = 0
        evidence_frame_indices: list[int] = []
        missing_frame_indices: list[int] = []
        diagnostic_frame_indices: list[int] = []
        unusable_frame_indices: list[int] = []
        invalid_level_indices: list[int] = []

        for frame_index, frame in enumerate(frames):
            payload = frame.get(metric_name) if isinstance(frame, Mapping) else None
            if not isinstance(payload, Mapping):
                missing_frame_count += 1
                missing_frame_indices.append(frame_index)
                continue

            evidence_frame_count += 1
            evidence_frame_indices.append(frame_index)
            raw_level = payload.get("level")
            try:
                level = raw_level if isinstance(raw_level, QualityLevel) else QualityLevel(str(raw_level))
                valid_level = True
            except (TypeError, ValueError):
                level = QualityLevel.UNUSABLE
                valid_level = False
                invalid_level_indices.append(frame_index)
                if "series_metric_invalid_level" not in reasons:
                    reasons.append("series_metric_invalid_level")

            level_counts[level.value] += 1
            if level in {QualityLevel.QUANTITATIVE, QualityLevel.TREND}:
                usable_frame_count += 1
            elif level is QualityLevel.DIAGNOSTIC:
                diagnostic_frame_count += 1
                diagnostic_frame_indices.append(frame_index)
            else:
                unusable_frame_count += 1
                unusable_frame_indices.append(frame_index)

            if not valid_level and "series_metric_unusable_frames" not in reasons:
                reasons.append("series_metric_unusable_frames")

        frame_count = len(frames)
        coverage_fraction = (
            float(evidence_frame_count / frame_count) if frame_count else None
        )
        if missing_frame_count:
            reasons.append("series_metric_missing_frames")
        if diagnostic_frame_count:
            reasons.append("series_metric_diagnostic_frames")
        if unusable_frame_count and "series_metric_unusable_frames" not in reasons:
            reasons.append("series_metric_unusable_frames")
        if not source_index_mapping_valid:
            reasons.append("series_metric_source_index_mismatch")
        if condition_axis_reason:
            reasons.append(condition_axis_reason)

        if frame_count == 0:
            reasons.append("series_no_frames")
            level = QualityLevel.UNUSABLE
        elif evidence_frame_count == 0:
            reasons.append("series_metric_missing_all_frames")
            level = QualityLevel.UNUSABLE
        elif usable_frame_count == 0:
            level = QualityLevel.UNUSABLE
        elif (
            missing_frame_count
            or diagnostic_frame_count
            or unusable_frame_count
            or frame_count < 2
        ):
            level = QualityLevel.DIAGNOSTIC
            if frame_count < 2:
                reasons.append("series_requires_multiple_frames")
        else:
            level = QualityLevel.TREND
            if level_counts[QualityLevel.QUANTITATIVE.value]:
                reasons.append("series_level_capped_at_trend")

        summaries[metric_name] = MetricEvidenceSummary(
            metric_name=metric_name,
            frame_count=frame_count,
            evidence_frame_count=evidence_frame_count,
            usable_frame_count=usable_frame_count,
            diagnostic_frame_count=diagnostic_frame_count,
            unusable_frame_count=unusable_frame_count,
            missing_frame_count=missing_frame_count,
            coverage_fraction=coverage_fraction,
            level=level,
            applicable=bool(level is QualityLevel.TREND and coverage_fraction == 1.0),
            level_counts=level_counts,
            reason_codes=tuple(dict.fromkeys(reasons)),
            source_ref=str(source_ref or ""),
            evidence_frame_indices=tuple(evidence_frame_indices),
            missing_frame_indices=tuple(missing_frame_indices),
            diagnostic_frame_indices=tuple(diagnostic_frame_indices),
            unusable_frame_indices=tuple(unusable_frame_indices),
            invalid_level_indices=tuple(invalid_level_indices),
            frame_source_indices=source_indices if source_index_mapping_valid else (),
            condition_axis=condition_axis,
        ).to_dict()
    return summaries


def _build_series_2d_summary(
    frame_payloads: Iterable[Mapping[str, Any] | None] | None,
    *,
    field_name: str,
    metric_name: str,
    source_ref: str,
) -> dict[str, Any] | None:
    """Aggregate one existing 2D evidence field without inventing frames."""

    frames = list(frame_payloads or ())
    if not any(isinstance(payload, Mapping) for payload in frames):
        return None

    wrapped = [
        {field_name: dict(payload)} if isinstance(payload, Mapping) else None
        for payload in frames
    ]
    summary = build_series_metric_evidence(
        wrapped,
        metric_names=(field_name,),
        source_ref=source_ref,
    ).get(field_name)
    if not isinstance(summary, dict):
        return None

    summary["metric_name"] = metric_name
    reason_codes = list(summary.get("reason_codes") or ())
    source_kinds: set[str] = set()
    for payload in frames:
        if not isinstance(payload, Mapping):
            continue
        for reason in payload.get("reason_codes", ()) or ():
            reason_text = str(reason).strip()
            if reason_text and reason_text not in reason_codes:
                reason_codes.append(reason_text)
        source_kind = str(payload.get("source_kind") or "").strip().lower()
        if source_kind:
            source_kinds.add(source_kind)
    summary["reason_codes"] = reason_codes
    if field_name == "detector_quality_report":
        summary["source_kinds"] = sorted(source_kinds)
        if len(source_kinds) > 1:
            summary["reason_codes"] = [*reason_codes, "series_detector_mixed_source_kinds"]
    return summary


def build_series_detector_quality_report(
    frame_reports: Iterable[Mapping[str, Any] | None] | None,
    *,
    source_ref: str = "",
) -> dict[str, Any] | None:
    """Conservatively summarize supplied detector/sector-map reports."""

    return _build_series_2d_summary(
        frame_reports,
        field_name="detector_quality_report",
        metric_name="DetectorQuality",
        source_ref=source_ref,
    )


def build_series_orientation_evidence(
    frame_evidence: Iterable[Mapping[str, Any] | None] | None,
    *,
    source_ref: str = "",
) -> dict[str, Any] | None:
    """Conservatively summarize orientation evidence as its own field."""

    return _build_series_2d_summary(
        frame_evidence,
        field_name="orientation_evidence",
        metric_name="Orientation",
        source_ref=source_ref,
    )


def contract_json(value: Any) -> str:
    """Return a stable strict-JSON representation for audit persistence."""
    payload = value.to_dict() if hasattr(value, "to_dict") else _jsonable(value)
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False)


__all__ = [
    "DataQualityReport",
    "DetectorQualityReport",
    "GuinierEvidence",
    "GuinierSequenceEvidence",
    "MetricEvidence",
    "MetricEvidenceSummary",
    "QualityLevel",
    "RescueCandidate",
    "RescueValidationReport",
    "build_data_quality_report",
    "build_guinier_evidence",
    "build_guinier_sequence_evidence",
    "build_porod_evidence",
    "build_kratky_evidence",
    "build_invariant_evidence",
    "build_lamellar_evidence",
    "build_series_metric_evidence",
    "build_series_detector_quality_report",
    "build_series_orientation_evidence",
    "build_detector_quality_report",
    "build_orientation_evidence",
    "contract_json",
]
