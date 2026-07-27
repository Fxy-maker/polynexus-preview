"""Serializable quality and evidence contracts for SAXS analysis.

The contracts in this module deliberately describe evidence and data quality;
they do not repair curves, choose a Guinier window, or replace physical gates.
Those operations remain in the existing deterministic analysis pipeline.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import json
from collections.abc import Mapping
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
    return _jsonable(asdict(value))


def _string_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(item) for item in value)


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
class MetricEvidence:
    """Evidence bundle for one physical metric."""

    metric_name: str
    value: Any = None
    unit: str = ""
    level: QualityLevel = QualityLevel.UNUSABLE
    applicable: bool = False
    uncertainty: Any = None
    fit_evidence: dict[str, Any] = field(default_factory=dict)
    physical_checks: dict[str, Any] = field(default_factory=dict)
    reason_codes: tuple[str, ...] = ()
    source_ref: str = ""
    data_quality_ref: str = ""
    processing_ref: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _contract_dict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MetricEvidence":
        data = dict(payload)
        data["level"] = _quality_level(data.get("level"))
        data["reason_codes"] = _string_tuple(data.get("reason_codes"))
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
class RescueCandidate:
    """A proposed deterministic or AI processing change awaiting validation."""

    candidate_id: str
    kind: str = "deterministic"
    parameters: dict[str, Any] = field(default_factory=dict)
    reason_codes: tuple[str, ...] = ()
    source: str = ""
    requires_validation: bool = True

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

    def effective_decision(self) -> str:
        reasons = list(self.rejection_reasons)
        if not self.hard_gate_passed:
            reasons.append("hard_gate_failed")
        if not self.physical_gate_passed:
            reasons.append("physical_gate_failed")
        if not self.data_preserved:
            reasons.append("data_preservation_failed")
        if not self.sequence_gate_passed:
            reasons.append("sequence_gate_failed")
        unique_reasons = tuple(dict.fromkeys(reasons))
        if unique_reasons:
            object.__setattr__(self, "rejection_reasons", unique_reasons)
            return "rejected"
        if self.decision == "accepted":
            return "accepted"
        if self.decision == "rejected":
            return "rejected"
        return "pending"

    def to_dict(self) -> dict[str, Any]:
        return _contract_dict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RescueValidationReport":
        data = dict(payload)
        data["rejection_reasons"] = _string_tuple(data.get("rejection_reasons"))
        return cls(**{key: data[key] for key in cls.__dataclass_fields__ if key in data})


def _as_1d_float_array(values: Any) -> np.ndarray:
    try:
        return np.asarray(values, dtype=float).reshape(-1)
    except (TypeError, ValueError):
        return np.asarray([], dtype=float)


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
    usable = pair_finite & (i_pair > 0)

    nonfinite_q_count = int(np.count_nonzero(~finite_q))
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
        nonfinite_intensity_count=nonfinite_i_count,
        nonpositive_intensity_count=nonpositive_i_count,
        duplicate_q_count=duplicate_q_count,
        nonmonotonic_q=nonmonotonic_q,
        actions=_string_tuple(actions),
        reason_codes=tuple(dict.fromkeys(reasons)),
        level=level,
    )


def contract_json(value: Any) -> str:
    """Return a stable strict-JSON representation for audit persistence."""
    payload = value.to_dict() if hasattr(value, "to_dict") else _jsonable(value)
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False)


__all__ = [
    "DataQualityReport",
    "GuinierEvidence",
    "MetricEvidence",
    "QualityLevel",
    "RescueCandidate",
    "RescueValidationReport",
    "build_data_quality_report",
    "contract_json",
]
