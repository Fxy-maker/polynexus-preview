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
    "build_guinier_evidence",
    "contract_json",
]
