"""Deterministic replay and uncertainty-boundary reports for TGA processing.

The replay suite exercises the public sample-neutral processing contract using
synthetic curves.  It is useful for regression and algorithm-boundary checks,
but deliberately is not represented as independent instrument or material
validation.  Measurement uncertainty is likewise reported as unavailable
until the required experimental evidence and a reviewed model exist.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from types import MappingProxyType
from typing import Any, Mapping, Sequence

import numpy as np

from .ai_platform.contracts import canonical_json_hash
from .tga_processing import TGAProcessingConfig, TGAProcessingOutcome, analyze_tga_curve


_CASE_ID = re.compile(r"[a-z][a-z0-9_]{0,127}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_OBSERVATION_STATUSES = frozenset({"passed", "failed"})
_REPORT_STATUSES = _OBSERVATION_STATUSES


def _public(value: Any) -> Any:
    """Return a JSON-safe public copy after validating the input contract."""

    canonical_json_hash(value)
    if isinstance(value, Mapping):
        return {str(key): _public(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_public(item) for item in value]
    return value


def _freeze(value: Any) -> Any:
    public = _public(value)
    if isinstance(public, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in public.items()})
    if isinstance(public, list):
        return tuple(_freeze(item) for item in public)
    return public


def _sha256(value: object, label: str) -> str:
    text = str(value).strip().lower()
    if not _SHA256.fullmatch(text):
        raise ValueError(f"{label} must be a 64-character hexadecimal SHA-256")
    return text


def _reason_codes(values: Sequence[object]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
        raise TypeError("reason_codes must be a sequence of nonempty strings")
    result: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("reason_codes must contain nonempty strings")
        reason = value.strip()
        if reason not in result:
            result.append(reason)
    return tuple(result)


def _numeric_values(values: Sequence[object], label: str) -> tuple[float, ...]:
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
        raise TypeError(f"{label} must be a sequence of finite numbers")
    normalized: list[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{label} must contain finite numbers")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"{label} must contain finite numbers")
        normalized.append(number)
    return tuple(normalized)


@dataclass(frozen=True)
class TGAReplayCase:
    """One source-preserving TGA replay input and its expected boundaries."""

    case_id: str
    x_values: tuple[float, ...]
    mass_values: tuple[float, ...]
    axis_kind: str = "temperature"
    axis_unit: str = "°C"
    signal_unit: str = "%"
    config: TGAProcessingConfig = TGAProcessingConfig()
    expected: Mapping[str, Any] = MappingProxyType({})
    case_hash: str = ""
    schema_version: str = "1"

    SCHEMA_VERSION = "1"

    def __post_init__(self) -> None:
        if self.schema_version != self.SCHEMA_VERSION:
            raise ValueError("Unsupported TGA replay case schema_version")
        if not isinstance(self.case_id, str) or not _CASE_ID.fullmatch(self.case_id):
            raise ValueError("TGA replay case_id must be a stable lowercase identifier")
        x_values = _numeric_values(self.x_values, "x_values")
        mass_values = _numeric_values(self.mass_values, "mass_values")
        if len(x_values) != len(mass_values):
            raise ValueError("TGA replay x_values and mass_values must have equal length")
        if len(x_values) < 2:
            raise ValueError("TGA replay values must contain at least two points")
        for name in ("axis_kind", "axis_unit", "signal_unit"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"TGA replay {name} must be nonempty")
            object.__setattr__(self, name, value.strip())
        config = TGAProcessingConfig.coerce(self.config)
        if not isinstance(self.expected, Mapping):
            raise TypeError("TGA replay expected values must be a mapping")
        object.__setattr__(self, "x_values", x_values)
        object.__setattr__(self, "mass_values", mass_values)
        object.__setattr__(self, "config", config)
        object.__setattr__(self, "expected", _freeze(self.expected))
        expected_hash = canonical_json_hash(self._identity_payload())
        if self.case_hash and _sha256(self.case_hash, "TGA replay case_hash") != expected_hash:
            raise ValueError("TGA replay case_hash does not match its content")
        object.__setattr__(self, "case_hash", expected_hash)

    @classmethod
    def create(
        cls,
        *,
        case_id: str,
        x_values: Sequence[object],
        mass_values: Sequence[object],
        axis_kind: str = "temperature",
        axis_unit: str = "°C",
        signal_unit: str = "%",
        config: TGAProcessingConfig | Mapping[str, Any] | None = None,
        expected: Mapping[str, Any] | None = None,
    ) -> "TGAReplayCase":
        return cls(
            case_id=case_id,
            x_values=tuple(x_values),
            mass_values=tuple(mass_values),
            axis_kind=axis_kind,
            axis_unit=axis_unit,
            signal_unit=signal_unit,
            config=TGAProcessingConfig.coerce(config),
            expected={} if expected is None else expected,
        )

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "case_id": self.case_id,
            "x_values": list(self.x_values),
            "mass_values": list(self.mass_values),
            "axis_kind": self.axis_kind,
            "axis_unit": self.axis_unit,
            "signal_unit": self.signal_unit,
            "config": self.config.to_dict(),
            "expected": _public(self.expected),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._identity_payload(), "case_hash": self.case_hash}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TGAReplayCase":
        if not isinstance(value, Mapping):
            raise TypeError("TGA replay case must be a mapping")
        return cls(
            case_id=value["case_id"],
            x_values=tuple(value["x_values"]),
            mass_values=tuple(value["mass_values"]),
            axis_kind=value.get("axis_kind", "temperature"),
            axis_unit=value.get("axis_unit", "°C"),
            signal_unit=value.get("signal_unit", "%"),
            config=TGAProcessingConfig.coerce(value.get("config")),
            expected=value.get("expected", {}),
            case_hash=value.get("case_hash", ""),
            schema_version=value.get("schema_version", ""),
        )


@dataclass(frozen=True)
class TGAReplayObservation:
    """One immutable observation from replaying a `TGAReplayCase` twice."""

    case_id: str
    case_hash: str
    status: str
    expected: Mapping[str, Any]
    observed: Mapping[str, Any]
    checks: Mapping[str, bool]
    reason_codes: tuple[str, ...] = ()
    observation_hash: str = ""
    schema_version: str = "1"

    SCHEMA_VERSION = "1"

    def __post_init__(self) -> None:
        if self.schema_version != self.SCHEMA_VERSION:
            raise ValueError("Unsupported TGA replay observation schema_version")
        if not isinstance(self.case_id, str) or not _CASE_ID.fullmatch(self.case_id):
            raise ValueError("TGA replay observation case_id is invalid")
        object.__setattr__(self, "case_hash", _sha256(self.case_hash, "TGA replay case_hash"))
        if self.status not in _OBSERVATION_STATUSES:
            raise ValueError("Unsupported TGA replay observation status")
        if not isinstance(self.expected, Mapping) or not isinstance(self.observed, Mapping):
            raise TypeError("TGA replay expected and observed values must be mappings")
        if not isinstance(self.checks, Mapping) or not self.checks:
            raise TypeError("TGA replay checks must be a nonempty mapping")
        normalized_checks: dict[str, bool] = {}
        for name, value in self.checks.items():
            if not isinstance(name, str) or not name or not isinstance(value, bool):
                raise TypeError("TGA replay checks must map nonempty names to booleans")
            normalized_checks[name] = value
        expected_status = "passed" if all(normalized_checks.values()) else "failed"
        if self.status != expected_status:
            raise ValueError("TGA replay observation status does not match its checks")
        object.__setattr__(self, "expected", _freeze(self.expected))
        object.__setattr__(self, "observed", _freeze(self.observed))
        object.__setattr__(self, "checks", MappingProxyType(normalized_checks))
        object.__setattr__(self, "reason_codes", _reason_codes(self.reason_codes))
        expected_hash = canonical_json_hash(self._identity_payload())
        if self.observation_hash and _sha256(
            self.observation_hash, "TGA replay observation_hash"
        ) != expected_hash:
            raise ValueError("TGA replay observation_hash does not match its content")
        object.__setattr__(self, "observation_hash", expected_hash)

    @classmethod
    def create(
        cls,
        *,
        case: TGAReplayCase,
        status: str,
        observed: Mapping[str, Any],
        checks: Mapping[str, bool],
        reason_codes: Sequence[str] = (),
    ) -> "TGAReplayObservation":
        if type(case) is not TGAReplayCase:
            raise TypeError("TGA replay observation requires an exact TGAReplayCase")
        return cls(
            case_id=case.case_id,
            case_hash=case.case_hash,
            status=status,
            expected=case.expected,
            observed=observed,
            checks=checks,
            reason_codes=tuple(reason_codes),
        )

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "case_id": self.case_id,
            "case_hash": self.case_hash,
            "status": self.status,
            "expected": _public(self.expected),
            "observed": _public(self.observed),
            "checks": dict(self.checks),
            "reason_codes": list(self.reason_codes),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._identity_payload(), "observation_hash": self.observation_hash}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TGAReplayObservation":
        if not isinstance(value, Mapping):
            raise TypeError("TGA replay observation must be a mapping")
        return cls(
            case_id=value["case_id"],
            case_hash=value["case_hash"],
            status=value["status"],
            expected=value.get("expected", {}),
            observed=value.get("observed", {}),
            checks=value.get("checks", {}),
            reason_codes=tuple(value.get("reason_codes", ())),
            observation_hash=value.get("observation_hash", ""),
            schema_version=value.get("schema_version", ""),
        )


@dataclass(frozen=True)
class TGAUncertaintyReport:
    """Honest boundary report for measurement uncertainty availability.

    This object intentionally does not compute intervals.  Parameter sensitivity
    and synthetic replay examine algorithm behavior; neither supplies replicate,
    calibration, instrument, or standard-sample uncertainty evidence.
    """

    status: str
    reason_codes: tuple[str, ...]
    evidence: Mapping[str, bool]
    intervals: Mapping[str, Any]
    method_sensitivity_is_measurement_uncertainty: bool = False
    report_hash: str = ""
    schema_version: str = "1"

    SCHEMA_VERSION = "1"
    STATUS = "unavailable"

    def __post_init__(self) -> None:
        if self.schema_version != self.SCHEMA_VERSION:
            raise ValueError("Unsupported TGA uncertainty report schema_version")
        if self.status != self.STATUS:
            raise ValueError("TGA measurement uncertainty status must be unavailable")
        object.__setattr__(self, "reason_codes", _reason_codes(self.reason_codes))
        if not self.reason_codes:
            raise ValueError("TGA unavailable uncertainty requires a reason code")
        if not isinstance(self.evidence, Mapping) or not isinstance(self.intervals, Mapping):
            raise TypeError("TGA uncertainty evidence and intervals must be mappings")
        normalized_evidence: dict[str, bool] = {}
        for name, value in self.evidence.items():
            if not isinstance(name, str) or not name or not isinstance(value, bool):
                raise TypeError("TGA uncertainty evidence must map names to booleans")
            normalized_evidence[name] = value
        if self.intervals:
            raise ValueError("TGA unavailable uncertainty cannot include intervals")
        if self.method_sensitivity_is_measurement_uncertainty is not False:
            raise ValueError("method sensitivity must not be represented as measurement uncertainty")
        object.__setattr__(self, "evidence", MappingProxyType(normalized_evidence))
        object.__setattr__(self, "intervals", MappingProxyType({}))
        expected_hash = canonical_json_hash(self._identity_payload())
        if self.report_hash and _sha256(self.report_hash, "TGA uncertainty report_hash") != expected_hash:
            raise ValueError("TGA uncertainty report_hash does not match its content")
        object.__setattr__(self, "report_hash", expected_hash)

    @classmethod
    def unavailable(
        cls,
        *,
        replicate_measurements: int = 0,
        instrument_error: bool = False,
        calibration_error: bool = False,
        standard_sample: bool = False,
    ) -> "TGAUncertaintyReport":
        if (
            not isinstance(replicate_measurements, int)
            or isinstance(replicate_measurements, bool)
            or replicate_measurements < 0
        ):
            raise ValueError("replicate_measurements must be a nonnegative integer")
        for name, value in {
            "instrument_error": instrument_error,
            "calibration_error": calibration_error,
            "standard_sample": standard_sample,
        }.items():
            if not isinstance(value, bool):
                raise TypeError(f"{name} evidence flag must be boolean")
        evidence = {
            "replicate_measurements": replicate_measurements >= 2,
            "instrument_error": instrument_error,
            "calibration_error": calibration_error,
            "standard_sample": standard_sample,
        }
        reasons = [
            name + "_required"
            for name, present in evidence.items()
            if not present
        ]
        if not reasons:
            reasons.append("measurement_uncertainty_model_not_implemented")
        return cls(
            status=cls.STATUS,
            reason_codes=tuple(reasons),
            evidence=evidence,
            intervals={},
        )

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "status": self.status,
            "reason_codes": list(self.reason_codes),
            "evidence": dict(self.evidence),
            "intervals": {},
            "method_sensitivity_is_measurement_uncertainty": False,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._identity_payload(), "report_hash": self.report_hash}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TGAUncertaintyReport":
        if not isinstance(value, Mapping):
            raise TypeError("TGA uncertainty report must be a mapping")
        return cls(
            status=value["status"],
            reason_codes=tuple(value.get("reason_codes", ())),
            evidence=value.get("evidence", {}),
            intervals=value.get("intervals", {}),
            method_sensitivity_is_measurement_uncertainty=value.get(
                "method_sensitivity_is_measurement_uncertainty", False
            ),
            report_hash=value.get("report_hash", ""),
            schema_version=value.get("schema_version", ""),
        )


@dataclass(frozen=True)
class TGAValidationReport:
    """Content-addressed TGA algorithm-boundary replay report."""

    status: str
    observations: tuple[TGAReplayObservation, ...]
    uncertainty: TGAUncertaintyReport
    validation_scope: str = "algorithm_boundary_only"
    independent_validation: bool = False
    promotion_eligible: bool = False
    content_hash: str = ""
    schema_version: str = "1"

    SCHEMA_VERSION = "1"

    def __post_init__(self) -> None:
        if self.schema_version != self.SCHEMA_VERSION:
            raise ValueError("Unsupported TGA validation report schema_version")
        if self.validation_scope != "algorithm_boundary_only":
            raise ValueError("TGA replay report must remain an algorithm-boundary validation")
        if self.independent_validation is not False or self.promotion_eligible is not False:
            raise ValueError("TGA synthetic replay cannot claim independent validation or promotion")
        if isinstance(self.observations, (str, bytes, bytearray)) or not isinstance(
            self.observations, Sequence
        ):
            raise TypeError("TGA validation observations must be a nonempty sequence")
        observations = tuple(self.observations)
        if not observations or not all(type(item) is TGAReplayObservation for item in observations):
            raise TypeError("TGA validation observations must contain exact replay observations")
        if len({item.case_id for item in observations}) != len(observations):
            raise ValueError("TGA validation observation case IDs must be unique")
        if type(self.uncertainty) is not TGAUncertaintyReport:
            raise TypeError("TGA validation report requires an exact uncertainty report")
        expected_status = "passed" if all(item.status == "passed" for item in observations) else "failed"
        if self.status not in _REPORT_STATUSES or self.status != expected_status:
            raise ValueError("TGA validation report status does not match observations")
        object.__setattr__(self, "observations", observations)
        expected_hash = canonical_json_hash(self._identity_payload())
        if self.content_hash and _sha256(self.content_hash, "TGA validation content_hash") != expected_hash:
            raise ValueError("TGA validation content_hash does not match its content")
        object.__setattr__(self, "content_hash", expected_hash)

    @classmethod
    def create(
        cls,
        *,
        observations: Sequence[TGAReplayObservation],
        uncertainty: TGAUncertaintyReport | None = None,
    ) -> "TGAValidationReport":
        observation_tuple = tuple(observations)
        return cls(
            status="passed" if all(item.status == "passed" for item in observation_tuple) else "failed",
            observations=observation_tuple,
            uncertainty=TGAUncertaintyReport.unavailable() if uncertainty is None else uncertainty,
        )

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "status": self.status,
            "observations": [item.to_dict() for item in self.observations],
            "uncertainty": self.uncertainty.to_dict(),
            "validation_scope": self.validation_scope,
            "independent_validation": False,
            "promotion_eligible": False,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._identity_payload(), "content_hash": self.content_hash}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TGAValidationReport":
        if not isinstance(value, Mapping):
            raise TypeError("TGA validation report must be a mapping")
        return cls(
            status=value["status"],
            observations=tuple(
                TGAReplayObservation.from_dict(item) for item in value.get("observations", ())
            ),
            uncertainty=TGAUncertaintyReport.from_dict(value["uncertainty"]),
            validation_scope=value.get("validation_scope", ""),
            independent_validation=value.get("independent_validation", False),
            promotion_eligible=value.get("promotion_eligible", False),
            content_hash=value.get("content_hash", ""),
            schema_version=value.get("schema_version", ""),
        )


def _outcome_payload(outcome: TGAProcessingOutcome) -> dict[str, Any]:
    return {
        "metrics": _public(outcome.metrics),
        "units": _public(outcome.units),
        "methods": _public(outcome.methods),
        "parameters": _public(outcome.parameters),
    }


def _first_residue_target(residue: Mapping[str, Any]) -> Mapping[str, Any] | None:
    targets = sorted(key for key in residue if key.startswith("target_"))
    if not targets:
        return None
    value = residue[targets[0]]
    return value if isinstance(value, Mapping) else None


def _event_bounds_are_valid(metrics: Mapping[str, Any], point_count: int) -> bool:
    events = metrics.get("mass_loss_events")
    if not isinstance(events, Mapping) or events.get("status") != "computed":
        return True
    for key, event in events.items():
        if not key.startswith("event_") or not isinstance(event, Mapping):
            continue
        try:
            start = int(event["canonical_index_start"])
            peak = int(event["peak_index"])
            end = int(event["canonical_index_end"])
            onset = float(event["onset_candidate_x"])
            peak_x = float(event["peak_x"])
            endset = float(event["endset_candidate_x"])
        except (KeyError, TypeError, ValueError):
            return False
        if not (0 <= start < peak < end < point_count and onset < peak_x < endset):
            return False
    return True


def _observed_summary(
    *,
    case: TGAReplayCase,
    outcome: TGAProcessingOutcome,
    input_hash: str,
    first_output_hash: str,
    second_output_hash: str,
) -> dict[str, Any]:
    metrics = outcome.metrics
    normalization = metrics.get("normalization", {})
    dtg = metrics.get("dtg", {})
    events = metrics.get("mass_loss_events", {})
    residue = metrics.get("residue", {})
    target = _first_residue_target(residue) if isinstance(residue, Mapping) else None
    return {
        "input_hash": input_hash,
        "first_output_hash": first_output_hash,
        "second_output_hash": second_output_hash,
        "normalization_status": normalization.get("status") if isinstance(normalization, Mapping) else None,
        "normalization_reason": normalization.get("unavailable_reason") if isinstance(normalization, Mapping) else None,
        "dtg_status": dtg.get("status") if isinstance(dtg, Mapping) else None,
        "dtg_reason": dtg.get("unavailable_reason") if isinstance(dtg, Mapping) else None,
        "dtg_rate_unit": dtg.get("rate_unit") if isinstance(dtg, Mapping) else None,
        "events_status": events.get("status") if isinstance(events, Mapping) else None,
        "event_count": events.get("event_count", 0) if isinstance(events, Mapping) else 0,
        "residue_status": residue.get("status") if isinstance(residue, Mapping) else None,
        "residue_target_status": None if target is None else target.get("status"),
        "residue_target_reason": None if target is None else target.get("unavailable_reason"),
        "axis_kind": metrics.get("axis_kind"),
        "axis_unit": metrics.get("axis_unit"),
    }


def _matches_expected(observed: Mapping[str, Any], expected: Mapping[str, Any]) -> tuple[bool, tuple[str, ...]]:
    failures: list[str] = []
    for key, expected_value in expected.items():
        if key == "event_count_at_least":
            actual = observed.get("event_count")
            if not isinstance(expected_value, int) or isinstance(expected_value, bool) or actual < expected_value:
                failures.append(str(key))
        elif observed.get(key) != expected_value:
            failures.append(str(key))
    return not failures, tuple(failures)


def _run_case(case: TGAReplayCase) -> TGAReplayObservation:
    x = np.asarray(case.x_values, dtype=float)
    mass = np.asarray(case.mass_values, dtype=float)
    source_x = x.copy()
    source_mass = mass.copy()
    input_hash = canonical_json_hash(
        {
            "x_values": list(case.x_values),
            "mass_values": list(case.mass_values),
            "axis_kind": case.axis_kind,
            "axis_unit": case.axis_unit,
            "signal_unit": case.signal_unit,
            "config": case.config.to_dict(),
        }
    )
    try:
        first = analyze_tga_curve(
            x,
            mass,
            axis_kind=case.axis_kind,
            axis_unit=case.axis_unit,
            signal_unit=case.signal_unit,
            config=case.config,
        )
        second = analyze_tga_curve(
            x,
            mass,
            axis_kind=case.axis_kind,
            axis_unit=case.axis_unit,
            signal_unit=case.signal_unit,
            config=case.config,
        )
    except (TypeError, ValueError, ArithmeticError) as exc:
        observed = {
            "input_hash": input_hash,
            "processing_status": "failed",
            "error_type": type(exc).__name__,
        }
        checks = {
            "source_arrays_preserved": bool(
                np.array_equal(x, source_x) and np.array_equal(mass, source_mass)
            ),
            "replay_deterministic": False,
            "expected_observations": False,
            "event_bounds_valid": False,
            "axis_semantics_preserved": False,
        }
        return TGAReplayObservation.create(
            case=case,
            status="failed",
            observed=observed,
            checks=checks,
            reason_codes=(f"processing_failed:{type(exc).__name__}",),
        )

    first_payload = _outcome_payload(first)
    second_payload = _outcome_payload(second)
    first_hash = canonical_json_hash(first_payload)
    second_hash = canonical_json_hash(second_payload)
    observed = _observed_summary(
        case=case,
        outcome=first,
        input_hash=input_hash,
        first_output_hash=first_hash,
        second_output_hash=second_hash,
    )
    expected_ok, failed_expected = _matches_expected(observed, case.expected)
    checks = {
        "source_arrays_preserved": bool(
            np.array_equal(x, source_x) and np.array_equal(mass, source_mass)
        ),
        "replay_deterministic": first_hash == second_hash,
        "expected_observations": expected_ok,
        "event_bounds_valid": _event_bounds_are_valid(first.metrics, int(x.size)),
        "axis_semantics_preserved": (
            observed["axis_kind"] == case.axis_kind and observed["axis_unit"] == case.axis_unit
        ),
    }
    reasons: list[str] = [f"expected_mismatch:{name}" for name in failed_expected]
    reasons.extend(name for name, passed in checks.items() if not passed and name != "expected_observations")
    return TGAReplayObservation.create(
        case=case,
        status="passed" if all(checks.values()) else "failed",
        observed=observed,
        checks=checks,
        reason_codes=tuple(reasons),
    )


def assess_tga_measurement_uncertainty(
    *,
    replicate_measurements: int = 0,
    instrument_error: bool = False,
    calibration_error: bool = False,
    standard_sample: bool = False,
) -> TGAUncertaintyReport:
    """Return an explicit unavailable state until a reviewed model exists."""

    return TGAUncertaintyReport.unavailable(
        replicate_measurements=replicate_measurements,
        instrument_error=instrument_error,
        calibration_error=calibration_error,
        standard_sample=standard_sample,
    )


def run_tga_replay_suite(
    cases: Sequence[TGAReplayCase] | None = None,
    *,
    uncertainty: TGAUncertaintyReport | None = None,
) -> TGAValidationReport:
    """Replay the shared TGA processing path and retain every observation."""

    replay_cases = default_tga_replay_cases() if cases is None else tuple(cases)
    if isinstance(replay_cases, (str, bytes, bytearray)) or not isinstance(replay_cases, Sequence):
        raise TypeError("TGA replay cases must be a sequence")
    if not replay_cases:
        raise ValueError("TGA replay suite requires at least one case")
    if not all(type(case) is TGAReplayCase for case in replay_cases):
        raise TypeError("TGA replay suite requires exact TGAReplayCase values")
    return TGAValidationReport.create(
        observations=tuple(_run_case(case) for case in replay_cases),
        uncertainty=uncertainty,
    )


def _one_step_curve(x: np.ndarray, *, midpoint: float, loss: float, width: float) -> np.ndarray:
    return 100.0 - loss / (1.0 + np.exp(-(x - midpoint) / width))


def default_tga_replay_cases() -> tuple[TGAReplayCase, ...]:
    """Return deterministic normal and anomalous algorithm-boundary inputs."""

    temperature = np.linspace(25.0, 800.0, 157)
    single_step = _one_step_curve(temperature, midpoint=350.0, loss=55.0, width=12.0)
    double_step = (
        100.0
        - 20.0 / (1.0 + np.exp(-(temperature - 300.0) / 8.0))
        - 30.0 / (1.0 + np.exp(-(temperature - 500.0) / 10.0))
    )
    noisy = double_step + 0.12 * np.sin(temperature * 0.31) + 0.04 * np.cos(temperature * 0.07)
    short_x = np.asarray((25.0, 75.0, 125.0, 175.0), dtype=float)
    time = np.linspace(0.0, 20.0, 61)
    time_mass = _one_step_curve(time, midpoint=10.0, loss=18.0, width=0.8)
    target_config = TGAProcessingConfig(residue_targets=(400.0,))
    return (
        TGAReplayCase.create(
            case_id="single_step",
            x_values=temperature,
            mass_values=single_step,
            expected={
                "normalization_status": "computed",
                "dtg_status": "computed",
                "event_count_at_least": 1,
            },
        ),
        TGAReplayCase.create(
            case_id="double_step",
            x_values=temperature,
            mass_values=double_step,
            expected={
                "normalization_status": "computed",
                "dtg_status": "computed",
                "event_count_at_least": 2,
            },
        ),
        TGAReplayCase.create(
            case_id="noisy_curve",
            x_values=temperature,
            mass_values=noisy,
            expected={"normalization_status": "computed", "dtg_status": "computed"},
        ),
        TGAReplayCase.create(
            case_id="too_few_points",
            x_values=short_x,
            mass_values=(100.0, 98.0, 95.0, 90.0),
            expected={"normalization_status": "computed", "dtg_status": "unavailable"},
        ),
        TGAReplayCase.create(
            case_id="non_monotonic_axis",
            x_values=(25.0, 100.0, 90.0, 200.0, 300.0, 400.0),
            mass_values=(100.0, 99.0, 98.0, 80.0, 70.0, 60.0),
            expected={"normalization_status": "computed", "dtg_status": "unavailable"},
        ),
        TGAReplayCase.create(
            case_id="nonpositive_initial_mass",
            x_values=np.linspace(25.0, 400.0, 16),
            mass_values=np.zeros(16),
            expected={"normalization_status": "unavailable", "dtg_status": "unavailable"},
        ),
        TGAReplayCase.create(
            case_id="time_axis",
            x_values=time,
            mass_values=time_mass,
            axis_kind="time",
            axis_unit="min",
            signal_unit="mg",
            config=TGAProcessingConfig(residue_targets=(10.0,)),
            expected={
                "dtg_status": "computed",
                "residue_target_status": "unavailable",
                "residue_target_reason": "temperature_axis_required",
            },
        ),
        TGAReplayCase.create(
            case_id="unknown_temperature_unit",
            x_values=temperature,
            mass_values=single_step,
            axis_kind="temperature",
            axis_unit="unknown",
            signal_unit="mg",
            config=target_config,
            expected={
                "dtg_status": "computed",
                "dtg_rate_unit": "percent_initial_mass_per_unknown",
                "residue_target_status": "unavailable",
                "residue_target_reason": "temperature_unit_unknown",
            },
        ),
        TGAReplayCase.create(
            case_id="residue_target_out_of_range",
            x_values=temperature,
            mass_values=single_step,
            config=TGAProcessingConfig(residue_targets=(900.0,)),
            expected={
                "dtg_status": "computed",
                "residue_target_status": "unavailable",
                "residue_target_reason": "target_outside_recorded_axis",
            },
        ),
    )


__all__ = [
    "TGAReplayCase",
    "TGAReplayObservation",
    "TGAUncertaintyReport",
    "TGAValidationReport",
    "assess_tga_measurement_uncertainty",
    "default_tga_replay_cases",
    "run_tga_replay_suite",
]
