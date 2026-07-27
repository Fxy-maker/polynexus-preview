"""Serializable quality and evidence contracts for SAXS analysis.

The contracts in this module deliberately describe evidence and data quality;
they do not repair curves, choose a Guinier window, or replace physical gates.
Those operations remain in the existing deterministic analysis pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum
import json
from collections.abc import Mapping
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
        actions=_string_tuple(actions),
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
    elif len(valid_indices) < 2 or invalid_temperature_indices or duplicate_temperature_indices or nonmonotonic_temperature_indices:
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


def contract_json(value: Any) -> str:
    """Return a stable strict-JSON representation for audit persistence."""
    payload = value.to_dict() if hasattr(value, "to_dict") else _jsonable(value)
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False)


__all__ = [
    "DataQualityReport",
    "GuinierEvidence",
    "GuinierSequenceEvidence",
    "MetricEvidence",
    "QualityLevel",
    "RescueCandidate",
    "RescueValidationReport",
    "build_data_quality_report",
    "build_guinier_evidence",
    "build_guinier_sequence_evidence",
    "contract_json",
]
