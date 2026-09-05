"""Replay and diagnostic validation contracts for mechanics results.

These helpers deliberately validate against independently supplied expected
values. They do not manufacture a standard-sample reference and do not change
the shared ComputeRun or capability-promotion contracts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from .mechanics_processing import (
    MechanicsAnalysisSpec,
    MechanicsSignalSeries,
    analyze_mechanics_group,
)


_SCHEMA_VERSION = "1"


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Mechanics replay values must be finite")
        return float(value)
    return value


def _hash_payload(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        _json_safe(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class MechanicsReplayCase:
    """Serialized canonical-style input plus an external expected-value oracle."""

    case_id: str
    axis_kind: str
    axis_unit: str
    axis_values: tuple[float, ...]
    signals: tuple[MechanicsSignalSeries, ...]
    analysis_spec: MechanicsAnalysisSpec
    expected_metrics: Mapping[str, float]
    tolerances: Mapping[str, float]
    reference_kind: str
    schema_version: str = _SCHEMA_VERSION
    replay_hash: str = ""

    def __post_init__(self) -> None:
        case_id = str(self.case_id).strip()
        if not case_id:
            raise ValueError("Mechanics replay case_id is required")
        if self.schema_version != _SCHEMA_VERSION:
            raise ValueError("Unsupported mechanics replay schema version")
        axis_values = tuple(float(value) for value in self.axis_values)
        if len(axis_values) < 2 or any(not math.isfinite(value) for value in axis_values):
            raise ValueError("Mechanics replay axis must contain finite values")
        signals = tuple(self.signals)
        if not signals or not all(isinstance(item, MechanicsSignalSeries) for item in signals):
            raise TypeError("Mechanics replay signals must be MechanicsSignalSeries values")
        expected = _finite_mapping(self.expected_metrics, nonnegative=False, name="expected_metrics")
        tolerance = _finite_mapping(self.tolerances, nonnegative=True, name="tolerances")
        missing_tolerances = sorted(set(expected).difference(tolerance))
        if missing_tolerances:
            raise ValueError("Mechanics replay tolerances missing: " + ", ".join(missing_tolerances))
        reference_kind = str(self.reference_kind).strip()
        if not reference_kind or reference_kind.casefold() == "core_recomputed":
            raise ValueError("Mechanics replay requires an independent reference kind")
        object.__setattr__(self, "case_id", case_id)
        object.__setattr__(self, "axis_kind", str(self.axis_kind))
        object.__setattr__(self, "axis_unit", str(self.axis_unit))
        object.__setattr__(self, "axis_values", axis_values)
        object.__setattr__(self, "signals", signals)
        object.__setattr__(self, "expected_metrics", MappingProxyType(expected))
        object.__setattr__(self, "tolerances", MappingProxyType(tolerance))
        object.__setattr__(self, "reference_kind", reference_kind)
        expected_hash = _hash_payload(self._identity_payload())
        if self.replay_hash and self.replay_hash != expected_hash:
            raise ValueError("Mechanics replay hash does not match case content")
        object.__setattr__(self, "replay_hash", expected_hash)

    @classmethod
    def create(
        cls,
        *,
        case_id: str,
        axis_kind: str,
        axis_unit: str,
        axis_values: Sequence[float],
        signals: Sequence[MechanicsSignalSeries],
        analysis_spec: MechanicsAnalysisSpec | Mapping[str, Any],
        expected_metrics: Mapping[str, float],
        tolerances: Mapping[str, float],
        reference_kind: str,
    ) -> "MechanicsReplayCase":
        spec = (
            analysis_spec
            if isinstance(analysis_spec, MechanicsAnalysisSpec)
            else MechanicsAnalysisSpec.from_mapping(analysis_spec)
        )
        return cls(
            case_id=case_id,
            axis_kind=axis_kind,
            axis_unit=axis_unit,
            axis_values=tuple(axis_values),
            signals=tuple(signals),
            analysis_spec=spec,
            expected_metrics=expected_metrics,
            tolerances=tolerances,
            reference_kind=reference_kind,
        )

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "case_id": self.case_id,
            "axis_kind": self.axis_kind,
            "axis_unit": self.axis_unit,
            "axis_values": list(self.axis_values),
            "signals": [signal.to_dict() for signal in self.signals],
            "analysis_spec": self.analysis_spec.to_dict(),
            "expected_metrics": dict(self.expected_metrics),
            "tolerances": dict(self.tolerances),
            "reference_kind": self.reference_kind,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._identity_payload(), "replay_hash": self.replay_hash}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MechanicsReplayCase":
        if not isinstance(value, Mapping):
            raise TypeError("Mechanics replay case must be a mapping")
        return cls(
            case_id=value.get("case_id", ""),
            axis_kind=value.get("axis_kind", ""),
            axis_unit=value.get("axis_unit", ""),
            axis_values=tuple(value.get("axis_values", ())),
            signals=tuple(MechanicsSignalSeries.from_dict(item) for item in value.get("signals", ())),
            analysis_spec=MechanicsAnalysisSpec.from_mapping(value.get("analysis_spec", {})),
            expected_metrics=value.get("expected_metrics", {}),
            tolerances=value.get("tolerances", {}),
            reference_kind=value.get("reference_kind", ""),
            schema_version=value.get("schema_version", ""),
            replay_hash=value.get("replay_hash", ""),
        )


@dataclass(frozen=True)
class MechanicsReplayReport:
    """Deterministic validation report; a failure never mutates a run."""

    case_id: str
    replay_hash: str
    status: str
    computed_metrics: Mapping[str, float] = field(default_factory=dict)
    mismatches: tuple[Mapping[str, Any], ...] = ()
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in {"passed", "failed", "needs_input"}:
            raise ValueError("Unsupported mechanics replay report status")
        object.__setattr__(self, "computed_metrics", MappingProxyType(dict(self.computed_metrics)))
        object.__setattr__(self, "mismatches", tuple(dict(item) for item in self.mismatches))
        object.__setattr__(self, "reason_codes", tuple(str(item) for item in self.reason_codes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": _SCHEMA_VERSION,
            "case_id": self.case_id,
            "replay_hash": self.replay_hash,
            "status": self.status,
            "computed_metrics": dict(self.computed_metrics),
            "mismatches": [dict(item) for item in self.mismatches],
            "reason_codes": list(self.reason_codes),
        }


def run_mechanics_replay(case: MechanicsReplayCase) -> MechanicsReplayReport:
    """Replay a serialized case against externally supplied expected metrics."""

    if not isinstance(case, MechanicsReplayCase):
        raise TypeError("Mechanics replay requires a MechanicsReplayCase")
    try:
        outcome = analyze_mechanics_group(
            case.axis_values,
            axis_kind=case.axis_kind,
            axis_unit=case.axis_unit,
            signals=case.signals,
            analysis_spec=case.analysis_spec,
        )
    except (TypeError, ValueError, FloatingPointError) as exc:
        return MechanicsReplayReport(
            case_id=case.case_id,
            replay_hash=case.replay_hash,
            status="failed",
            reason_codes=("replay_execution_failed", str(exc)),
        )

    summary = outcome.metrics.get("mechanics_property_summary", {})
    computed: dict[str, float] = {}
    mismatches: list[dict[str, Any]] = []
    for metric, expected in case.expected_metrics.items():
        record = summary.get(metric)
        actual = record.get("value") if isinstance(record, Mapping) else None
        if isinstance(actual, (int, float)) and math.isfinite(float(actual)):
            actual_value = float(actual)
            computed[metric] = actual_value
            delta = abs(actual_value - float(expected))
            if delta > float(case.tolerances[metric]):
                mismatches.append(
                    {
                        "metric": metric,
                        "expected": float(expected),
                        "actual": actual_value,
                        "absolute_error": delta,
                        "tolerance": float(case.tolerances[metric]),
                    }
                )
        else:
            mismatches.append(
                {
                    "metric": metric,
                    "expected": float(expected),
                    "actual": None,
                    "tolerance": float(case.tolerances[metric]),
                    "reason": "metric_unavailable",
                }
            )
    return MechanicsReplayReport(
        case_id=case.case_id,
        replay_hash=case.replay_hash,
        status="passed" if not mismatches else "failed",
        computed_metrics=computed,
        mismatches=tuple(mismatches),
        reason_codes=() if not mismatches else ("replay_expected_value_mismatch",),
    )


def _finite_mapping(
    value: Mapping[str, float], *, nonnegative: bool, name: str
) -> dict[str, float]:
    if not isinstance(value, Mapping) or not value:
        raise ValueError(f"Mechanics replay {name} must be a nonempty mapping")
    normalized: dict[str, float] = {}
    for key, item in value.items():
        metric = str(key).strip()
        number = float(item)
        if not metric or not math.isfinite(number) or (nonnegative and number < 0.0):
            raise ValueError(f"Mechanics replay {name} contains an invalid value")
        normalized[metric] = number
    return normalized


__all__ = ["MechanicsReplayCase", "MechanicsReplayReport", "run_mechanics_replay"]
