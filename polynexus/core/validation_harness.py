"""Technique-neutral deterministic validation for public Core projections.

The harness is deliberately smaller than a scientific validation program.  It
replays a canonical, hash-bound input twice, compares the resulting public
metric projection with an independently supplied case expectation, and emits a
content-addressed report.  Reports are observations only: they never mutate a
``ComputeRun`` or an evidence package and never promote a capability.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
import copy
import math
import re
from types import MappingProxyType
from typing import Any

from .ai_platform.contracts import canonical_json_hash


_SCHEMA_VERSION = "1"
_CASE_KINDS = frozenset({"regression", "standard", "negative_control"})
_REPORT_STATUSES = frozenset({"passed", "failed", "unavailable", "needs_review"})
_METRIC_STATUSES = frozenset(
    {
        "computed",
        "computed_with_warning",
        "unavailable",
        "failed",
        "needs_input",
        "blocked",
        "not_applicable",
    }
)
_CASE_ID = re.compile(r"[a-z][a-z0-9_-]{0,127}")
_SHA256 = re.compile(r"[0-9a-f]{64}")


def _json(value: Any) -> Any:
    """Return an immutable JSON-safe snapshot of a public value."""

    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Validation values must be finite")
        return float(value)
    if isinstance(value, Mapping):
        return {str(key): _json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json(item) for item in value]
    raise TypeError(f"Validation values do not support {type(value).__name__}")


def _freeze(value: Any) -> Any:
    safe = _json(value)
    if isinstance(safe, dict):
        return MappingProxyType({key: _freeze(item) for key, item in safe.items()})
    if isinstance(safe, list):
        return tuple(_freeze(item) for item in safe)
    return safe


def _mapping(value: Mapping[str, Any] | None, label: str) -> Mapping[str, Any]:
    if value is None:
        return MappingProxyType({})
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    return _freeze(value)


def _sha256(value: str, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value.strip().lower()):
        raise ValueError(f"{label} must be a 64-character hexadecimal SHA-256")
    return value.strip().lower()


def _nonempty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")
    return value.strip()


def _metric_path(root: Any, path: str) -> tuple[bool, Any]:
    """Resolve exact or dotted keys without alias or technique inference."""

    if not isinstance(root, Mapping):
        return False, None
    if path in root:
        return True, root[path]
    parts = path.split(".")
    current: Any = root
    index = 0
    while index < len(parts):
        if not isinstance(current, Mapping):
            return False, None
        found = False
        for end in range(len(parts), index, -1):
            key = ".".join(parts[index:end])
            if key in current:
                current = current[key]
                index = end
                found = True
                break
        if not found:
            return False, None
    return True, current


def _numeric_equal(expected: Any, actual: Any, absolute: float, relative: float) -> bool:
    if isinstance(expected, bool) or isinstance(actual, bool):
        return expected == actual and type(expected) is type(actual)
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        expected_float = float(expected)
        actual_float = float(actual)
        if not math.isfinite(expected_float) or not math.isfinite(actual_float):
            return False
        allowed = max(float(absolute), float(relative) * abs(expected_float))
        return abs(actual_float - expected_float) <= allowed
    if isinstance(expected, (list, tuple)) and isinstance(actual, (list, tuple)):
        return len(expected) == len(actual) and all(
            _numeric_equal(item, observed, absolute, relative)
            for item, observed in zip(expected, actual)
        )
    if isinstance(expected, Mapping) and isinstance(actual, Mapping):
        return set(expected) == set(actual) and all(
            _numeric_equal(expected[key], actual[key], absolute, relative) for key in expected
        )
    return expected == actual


@dataclass(frozen=True)
class ValidationExpectation:
    """One expected public metric leaf and optional contract assertions."""

    path: str
    expected: Any = None
    absolute_tolerance: float = 0.0
    relative_tolerance: float = 0.0
    expected_status: str | None = None
    unit: str | None = None
    method: str | None = None
    parameters: Mapping[str, Any] = field(default_factory=dict)
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _nonempty(self.path, "expectation path"))
        for name in ("absolute_tolerance", "relative_tolerance"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be a finite nonnegative number")
            value = float(value)
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be a finite nonnegative number")
            object.__setattr__(self, name, value)
        if self.expected_status is not None:
            status = _nonempty(self.expected_status, "expectation expected_status")
            if status not in _METRIC_STATUSES:
                raise ValueError(f"Unsupported expected metric status: {status}")
            object.__setattr__(self, "expected_status", status)
        for name in ("unit", "method"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _nonempty(value, f"expectation {name}"))
        object.__setattr__(self, "expected", _freeze(self.expected))
        object.__setattr__(self, "parameters", _mapping(self.parameters, "expectation parameters"))
        object.__setattr__(self, "provenance", _mapping(self.provenance, "expectation provenance"))

    @classmethod
    def create(cls, *, path: str, expected: Any = None, **kwargs: Any) -> "ValidationExpectation":
        return cls(path=path, expected=expected, **kwargs)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "expected": _json(self.expected),
            "absolute_tolerance": self.absolute_tolerance,
            "relative_tolerance": self.relative_tolerance,
            "expected_status": self.expected_status,
            "unit": self.unit,
            "method": self.method,
            "parameters": _json(self.parameters),
            "provenance": _json(self.provenance),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ValidationExpectation":
        if not isinstance(value, Mapping):
            raise TypeError("Validation expectation must be a mapping")
        return cls(
            path=value.get("path", ""),
            expected=value.get("expected"),
            absolute_tolerance=value.get("absolute_tolerance", 0.0),
            relative_tolerance=value.get("relative_tolerance", 0.0),
            expected_status=value.get("expected_status"),
            unit=value.get("unit"),
            method=value.get("method"),
            parameters=value.get("parameters", {}),
            provenance=value.get("provenance", {}),
        )


@dataclass(frozen=True)
class ValidationCase:
    """Hash-bound canonical input plus independently supplied expectations."""

    case_id: str
    technique: str
    canonical_dataset_id: str
    input_payload: Mapping[str, Any]
    expectations: tuple[ValidationExpectation, ...] = ()
    case_kind: str = "regression"
    canonical_experiment_id: str | None = None
    raw_sha256: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    case_hash: str = ""
    schema_version: str = _SCHEMA_VERSION

    def __post_init__(self) -> None:
        case_id = _nonempty(self.case_id, "case_id")
        if not _CASE_ID.fullmatch(case_id):
            raise ValueError("case_id must be a stable lowercase identifier")
        technique = _nonempty(self.technique, "technique")
        dataset_id = _nonempty(self.canonical_dataset_id, "canonical_dataset_id")
        if self.schema_version != _SCHEMA_VERSION:
            raise ValueError("Unsupported validation case schema version")
        case_kind = _nonempty(self.case_kind, "case_kind")
        if case_kind not in _CASE_KINDS:
            raise ValueError(f"Unsupported validation case kind: {case_kind}")
        payload = _mapping(self.input_payload, "input_payload")
        if not payload:
            raise ValueError("input_payload must be a nonempty canonical mapping")
        payload_dataset = payload.get("dataset_id")
        if payload_dataset is not None and payload_dataset != dataset_id:
            raise ValueError("input_payload dataset_id does not match canonical_dataset_id")
        if self.canonical_experiment_id is not None:
            experiment_id = _nonempty(self.canonical_experiment_id, "canonical_experiment_id")
        else:
            experiment_id = None
        raw_hash = None if self.raw_sha256 is None else _sha256(self.raw_sha256, "raw_sha256")
        expectations = tuple(self.expectations)
        if not all(type(item) is ValidationExpectation for item in expectations):
            raise TypeError("expectations must contain ValidationExpectation values")
        if len({item.path for item in expectations}) != len(expectations):
            raise ValueError("validation expectation paths must be unique")
        object.__setattr__(self, "case_id", case_id)
        object.__setattr__(self, "technique", technique)
        object.__setattr__(self, "canonical_dataset_id", dataset_id)
        object.__setattr__(self, "canonical_experiment_id", experiment_id)
        object.__setattr__(self, "input_payload", payload)
        object.__setattr__(self, "expectations", expectations)
        object.__setattr__(self, "raw_sha256", raw_hash)
        object.__setattr__(self, "metadata", _mapping(self.metadata, "metadata"))
        expected_hash = canonical_json_hash(self._identity_payload())
        if self.case_hash:
            supplied = _sha256(self.case_hash, "case_hash")
            if supplied != expected_hash:
                raise ValueError("validation case_hash does not match case content")
        object.__setattr__(self, "case_hash", expected_hash)

    @classmethod
    def create(
        cls,
        *,
        case_id: str,
        technique: str,
        canonical_dataset_id: str,
        input_payload: Mapping[str, Any],
        expectations: Sequence[ValidationExpectation] = (),
        **kwargs: Any,
    ) -> "ValidationCase":
        return cls(
            case_id=case_id,
            technique=technique,
            canonical_dataset_id=canonical_dataset_id,
            input_payload=input_payload,
            expectations=tuple(expectations),
            **kwargs,
        )

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "case_id": self.case_id,
            "technique": self.technique,
            "canonical_dataset_id": self.canonical_dataset_id,
            "canonical_experiment_id": self.canonical_experiment_id,
            "input_payload": _json(self.input_payload),
            "expectations": [item.to_dict() for item in self.expectations],
            "case_kind": self.case_kind,
            "raw_sha256": self.raw_sha256,
            "metadata": _json(self.metadata),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._identity_payload(), "case_hash": self.case_hash}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ValidationCase":
        if not isinstance(value, Mapping):
            raise TypeError("Validation case must be a mapping")
        return cls(
            case_id=value.get("case_id", ""),
            technique=value.get("technique", ""),
            canonical_dataset_id=value.get("canonical_dataset_id", ""),
            input_payload=value.get("input_payload", {}),
            expectations=tuple(
                ValidationExpectation.from_dict(item) for item in value.get("expectations", ())
            ),
            case_kind=value.get("case_kind", "regression"),
            canonical_experiment_id=value.get("canonical_experiment_id"),
            raw_sha256=value.get("raw_sha256"),
            metadata=value.get("metadata", {}),
            case_hash=value.get("case_hash", ""),
            schema_version=value.get("schema_version", ""),
        )


@dataclass(frozen=True)
class ValidationReport:
    """Immutable report from one validation case replay."""

    case_id: str
    case_hash: str
    technique: str
    status: str
    replay_count: int
    deterministic: bool
    first_output_hash: str | None = None
    second_output_hash: str | None = None
    metric_comparisons: tuple[Mapping[str, Any], ...] = ()
    provenance_checks: Mapping[str, bool] = field(default_factory=dict)
    raw_preservation: Mapping[str, Any] = field(default_factory=dict)
    reason_codes: tuple[str, ...] = ()
    scientific_review_required: bool = True
    report_hash: str = ""
    schema_version: str = _SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != _SCHEMA_VERSION:
            raise ValueError("Unsupported validation report schema version")
        object.__setattr__(self, "case_id", _nonempty(self.case_id, "report case_id"))
        object.__setattr__(self, "case_hash", _sha256(self.case_hash, "report case_hash"))
        object.__setattr__(self, "technique", _nonempty(self.technique, "report technique"))
        if self.status not in _REPORT_STATUSES:
            raise ValueError(f"Unsupported validation report status: {self.status}")
        if isinstance(self.replay_count, bool) or not isinstance(self.replay_count, int) or self.replay_count < 0:
            raise ValueError("replay_count must be a nonnegative integer")
        if not isinstance(self.deterministic, bool):
            raise TypeError("deterministic must be boolean")
        for name in ("first_output_hash", "second_output_hash"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _sha256(value, f"{name}"))
        comparisons = tuple(dict(item) for item in self.metric_comparisons)
        if not all(isinstance(item, Mapping) for item in self.metric_comparisons):
            raise TypeError("metric_comparisons must contain mappings")
        object.__setattr__(self, "metric_comparisons", tuple(_freeze(item) for item in comparisons))
        checks = _mapping(self.provenance_checks, "provenance_checks")
        if any(not isinstance(key, str) or not isinstance(value, bool) for key, value in checks.items()):
            raise TypeError("provenance_checks must map names to booleans")
        object.__setattr__(self, "provenance_checks", checks)
        object.__setattr__(self, "raw_preservation", _mapping(self.raw_preservation, "raw_preservation"))
        reasons = tuple(_nonempty(item, "reason_code") for item in self.reason_codes)
        object.__setattr__(self, "reason_codes", tuple(dict.fromkeys(reasons)))
        if not isinstance(self.scientific_review_required, bool):
            raise TypeError("scientific_review_required must be boolean")
        expected_hash = canonical_json_hash(self._identity_payload())
        if self.report_hash:
            supplied = _sha256(self.report_hash, "report_hash")
            if supplied != expected_hash:
                raise ValueError("validation report_hash does not match report content")
        object.__setattr__(self, "report_hash", expected_hash)

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "case_id": self.case_id,
            "case_hash": self.case_hash,
            "technique": self.technique,
            "status": self.status,
            "replay_count": self.replay_count,
            "deterministic": self.deterministic,
            "first_output_hash": self.first_output_hash,
            "second_output_hash": self.second_output_hash,
            "metric_comparisons": [_json(item) for item in self.metric_comparisons],
            "provenance_checks": _json(self.provenance_checks),
            "raw_preservation": _json(self.raw_preservation),
            "reason_codes": list(self.reason_codes),
            "scientific_review_required": self.scientific_review_required,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._identity_payload(), "report_hash": self.report_hash}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ValidationReport":
        if not isinstance(value, Mapping):
            raise TypeError("Validation report must be a mapping")
        return cls(
            case_id=value.get("case_id", ""),
            case_hash=value.get("case_hash", ""),
            technique=value.get("technique", ""),
            status=value.get("status", ""),
            replay_count=value.get("replay_count", 0),
            deterministic=value.get("deterministic", False),
            first_output_hash=value.get("first_output_hash"),
            second_output_hash=value.get("second_output_hash"),
            metric_comparisons=tuple(value.get("metric_comparisons", ())),
            provenance_checks=value.get("provenance_checks", {}),
            raw_preservation=value.get("raw_preservation", {}),
            reason_codes=tuple(value.get("reason_codes", ())),
            scientific_review_required=value.get("scientific_review_required", True),
            report_hash=value.get("report_hash", ""),
            schema_version=value.get("schema_version", ""),
        )


def _public_projection(value: Any) -> dict[str, Any]:
    """Normalize ComputeResult or a JSON-shaped public result mapping."""

    if hasattr(value, "to_public_dict") and callable(value.to_public_dict):
        value = value.to_public_dict()
    elif hasattr(value, "to_dict") and callable(value.to_dict):
        value = value.to_dict()
    if not isinstance(value, Mapping):
        raise TypeError("validation calculator must return a public mapping or result DTO")
    payload = _json(value)
    if "result" in payload and isinstance(payload["result"], Mapping) and "metrics" not in payload:
        payload = dict(payload["result"])
    metrics = payload.get("metrics")
    if metrics is None:
        # A bare mapping is accepted as a metrics projection for lightweight
        # adapters, while preserving all explicit metadata when supplied.
        metrics = {
            key: item
            for key, item in payload.items()
            if key not in {"metric_manifest", "metadata", "provenance", "uncertainty", "warnings"}
        }
        payload["metrics"] = metrics
    if not isinstance(metrics, Mapping):
        raise TypeError("validation result metrics must be a mapping")
    payload.setdefault("metric_manifest", _inferred_manifest(payload))
    return payload


def _inferred_manifest(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    metrics = payload.get("metrics", {})
    metadata = payload.get("metadata", {})
    units = metadata.get("units", {}) if isinstance(metadata, Mapping) else {}
    methods = metadata.get("methods", metadata.get("method", {})) if isinstance(metadata, Mapping) else {}
    parameters = metadata.get("parameters", {}) if isinstance(metadata, Mapping) else {}
    records: list[dict[str, Any]] = []

    def walk(current: Any, prefix: str = "") -> None:
        if isinstance(current, Mapping):
            for key, item in current.items():
                walk(item, f"{prefix}.{key}" if prefix else str(key))
            return
        path = prefix
        status = "unavailable" if current is None else "computed"
        unit_found, unit = _metric_path(units, path)
        method_found, method = _metric_path(methods, path)
        params_found, params = _metric_path(parameters, path)
        record = {"path": path, "kind": "series" if isinstance(current, (list, tuple)) else "scalar", "status": status}
        if unit_found:
            record["unit"] = unit
        if method_found:
            record["method"] = method
        if params_found:
            record["parameters"] = params
        if status == "computed":
            record["value"] = current
        records.append(record)

    walk(metrics)
    return records


def _manifest_index(payload: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    manifest = payload.get("metric_manifest", ())
    if not isinstance(manifest, Sequence) or isinstance(manifest, (str, bytes, bytearray)):
        return {}
    index: dict[str, Mapping[str, Any]] = {}
    for item in manifest:
        if isinstance(item, Mapping) and isinstance(item.get("path"), str):
            index[item["path"]] = item
    return index


def _report(
    case: ValidationCase,
    *,
    status: str,
    replay_count: int,
    deterministic: bool,
    first_output_hash: str | None = None,
    second_output_hash: str | None = None,
    metric_comparisons: Sequence[Mapping[str, Any]] = (),
    provenance_checks: Mapping[str, bool] | None = None,
    raw_preservation: Mapping[str, Any] | None = None,
    reason_codes: Sequence[str] = (),
) -> ValidationReport:
    return ValidationReport(
        case_id=case.case_id,
        case_hash=case.case_hash,
        technique=case.technique,
        status=status,
        replay_count=replay_count,
        deterministic=deterministic,
        first_output_hash=first_output_hash,
        second_output_hash=second_output_hash,
        metric_comparisons=tuple(metric_comparisons),
        provenance_checks={} if provenance_checks is None else provenance_checks,
        raw_preservation={} if raw_preservation is None else raw_preservation,
        reason_codes=tuple(reason_codes),
    )


def run_validation(
    case: ValidationCase,
    calculator: Callable[[Mapping[str, Any]], Any],
    *,
    raw_hash_provider: Callable[[], str] | None = None,
) -> ValidationReport:
    """Run one case twice and compare only public deterministic projections."""

    if type(case) is not ValidationCase:
        raise TypeError("validation requires an exact ValidationCase")
    if not callable(calculator):
        raise TypeError("validation calculator must be callable")
    raw_before: str | None = None
    raw_after: str | None = None
    raw_reasons: list[str] = []
    if raw_hash_provider is not None:
        try:
            raw_before = _sha256(raw_hash_provider(), "raw hash provider")
            if case.raw_sha256 is not None and raw_before != case.raw_sha256:
                raw_reasons.append("raw_hash_before_mismatch")
        except Exception as exc:  # noqa: BLE001 - report a failed observation
            raw_reasons.append(f"raw_hash_provider_failed:{type(exc).__name__}")

    try:
        first = _public_projection(calculator(copy.deepcopy(dict(case.input_payload))))
        second = _public_projection(calculator(copy.deepcopy(dict(case.input_payload))))
    except Exception as exc:  # noqa: BLE001 - calculator boundary is untrusted
        if raw_hash_provider is not None:
            try:
                raw_after = _sha256(raw_hash_provider(), "raw hash provider")
            except Exception:
                raw_reasons.append("raw_hash_after_unavailable")
        raw_state = {
            "before": raw_before,
            "after": raw_after,
            "before_matches_expected": case.raw_sha256 is None or raw_before == case.raw_sha256,
            "after_matches_before": raw_after is not None and raw_after == raw_before,
        }
        return _report(
            case,
            status="failed",
            replay_count=2,
            deterministic=False,
            raw_preservation=raw_state,
            reason_codes=("replay_execution_failed", *raw_reasons, type(exc).__name__),
        )

    first_hash = canonical_json_hash(first)
    second_hash = canonical_json_hash(second)
    deterministic = first_hash == second_hash
    if raw_hash_provider is not None:
        try:
            raw_after = _sha256(raw_hash_provider(), "raw hash provider")
        except Exception:
            raw_reasons.append("raw_hash_after_unavailable")
    raw_state = {
        "before": raw_before,
        "after": raw_after,
        "before_matches_expected": case.raw_sha256 is None or raw_before == case.raw_sha256,
        "after_matches_before": raw_before is None or raw_after == raw_before,
    }
    if not raw_state["before_matches_expected"]:
        raw_reasons.append("raw_hash_before_mismatch")
    if not raw_state["after_matches_before"]:
        raw_reasons.append("raw_input_changed")

    first_manifest = _manifest_index(first)
    comparisons: list[dict[str, Any]] = []
    provenance_checks: dict[str, bool] = {}
    for expectation in case.expectations:
        found, actual = _metric_path(first.get("metrics", {}), expectation.path.removeprefix("metrics."))
        record = first_manifest.get(expectation.path)
        if record is None:
            record = first_manifest.get(expectation.path.removeprefix("metrics."))
        observed_status = record.get("status") if isinstance(record, Mapping) else ("unavailable" if not found or actual is None else "computed")
        checks: dict[str, bool] = {
            "status": expectation.expected_status is None or observed_status == expectation.expected_status,
            "value": True,
        }
        if expectation.expected_status in {"unavailable", "failed", "needs_input", "blocked", "not_applicable"}:
            checks["value"] = expectation.expected is None or not found or actual is None
        elif expectation.expected_status is None or expectation.expected_status in {"computed", "computed_with_warning"}:
            checks["value"] = found and _numeric_equal(
                expectation.expected,
                actual,
                expectation.absolute_tolerance,
                expectation.relative_tolerance,
            )
        details: dict[str, Any] = {
            "path": expectation.path,
            "expected": _json(expectation.expected),
            "actual": _json(actual) if found else None,
            "observed_status": observed_status,
            "status": "passed" if all(checks.values()) else "failed",
            "checks": checks,
        }
        for name, expected_value in (("unit", expectation.unit), ("method", expectation.method)):
            if expected_value is not None:
                actual_value = record.get(name) if isinstance(record, Mapping) else None
                checks[name] = actual_value == expected_value
                details["actual_" + name] = actual_value
        for name, expected_value in (("parameters", expectation.parameters), ("provenance", expectation.provenance)):
            if expected_value:
                actual_value = record.get(name) if isinstance(record, Mapping) else None
                passed = isinstance(actual_value, Mapping) and _numeric_equal(expected_value, actual_value, 0.0, 0.0)
                checks[name] = passed
                details["actual_" + name] = _json(actual_value) if actual_value is not None else None
                if name == "provenance":
                    provenance_checks[expectation.path] = passed
        details["status"] = "passed" if all(checks.values()) else "failed"
        comparisons.append(details)

    reasons: list[str] = list(raw_reasons)
    if not deterministic:
        reasons.append("non_deterministic_replay")
    if any(item["status"] == "failed" for item in comparisons):
        reasons.append("expected_metric_mismatch")
    if case.raw_sha256 is not None and raw_hash_provider is None:
        reasons.append("raw_hash_provider_required")
    status = "passed" if not reasons else "failed"
    if case.raw_sha256 is not None and raw_hash_provider is None:
        status = "needs_review"
    if not case.expectations and not deterministic:
        status = "failed"
    return _report(
        case,
        status=status,
        replay_count=2,
        deterministic=deterministic,
        first_output_hash=first_hash,
        second_output_hash=second_hash,
        metric_comparisons=comparisons,
        provenance_checks=provenance_checks,
        raw_preservation=raw_state,
        reason_codes=tuple(dict.fromkeys(reasons)),
    )


__all__ = ["ValidationCase", "ValidationExpectation", "ValidationReport", "run_validation"]
