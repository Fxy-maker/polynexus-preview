"""Aggregate existing replay and smoke evidence into one safe report.

This layer does not calculate metrics and does not promote capabilities.  It
only gives AI/CLI/GUI consumers one compact, content-addressed view over the
existing deterministic replay batch and the external all-module smoke report.
Raw archives and provider outputs remain in their existing locations.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import re
from typing import Any

from .ai_platform.contracts import canonical_json_hash
from .project_workflow.validation import ProjectValidationBatch


_SCHEMA_VERSION = "1"
_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{0,127}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_EVIDENCE_KINDS = frozenset({"deterministic_replay", "smoke_only", "unavailable"})
_EVIDENCE_STATUSES = frozenset({"passed", "failed", "unavailable", "needs_review"})
_SUITE_STATUSES = frozenset({"complete_with_review", "failed"})


def _json(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("validation suite values must be finite")
        return float(value)
    if isinstance(value, Mapping):
        return {str(key): _json(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json(item) for item in value]
    raise TypeError(f"validation suite values do not support {type(value).__name__}")


def _freeze(value: Any) -> Any:
    normalized = _json(value)
    if isinstance(normalized, dict):
        return {key: _freeze(item) for key, item in normalized.items()}
    if isinstance(normalized, list):
        return tuple(_freeze(item) for item in normalized)
    return normalized


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")
    return value.strip()


def _id(value: Any, label: str) -> str:
    result = _text(value, label).lower()
    if not _ID_PATTERN.fullmatch(result):
        raise ValueError(f"{label} must be a stable lowercase identifier")
    return result


def _hash(value: Any, label: str, *, allow_empty: bool = True) -> str:
    if value in (None, "") and allow_empty:
        return ""
    result = _text(value, label).lower()
    if not _SHA256_PATTERN.fullmatch(result):
        raise ValueError(f"{label} must be a SHA-256")
    return result


def _strings(value: Sequence[str], label: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise TypeError(f"{label} must be a sequence")
    return tuple(_text(item, f"{label} item") for item in value)


@dataclass(frozen=True)
class ValidationSuiteEntry:
    """One typed evidence observation included in an aggregate report."""

    evidence_id: str
    technique: str
    kind: str
    status: str
    source_ref: str
    source_hash: str = ""
    case_count: int = 1
    replay_count: int = 0
    deterministic: bool | None = None
    valid_result: bool | None = None
    reason_codes: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    entry_hash: str = ""
    schema_version: str = _SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != _SCHEMA_VERSION:
            raise ValueError("unsupported validation suite entry schema version")
        evidence_id = _id(self.evidence_id, "evidence_id")
        technique = _id(self.technique, "technique")
        kind = _text(self.kind, "kind")
        if kind not in _EVIDENCE_KINDS:
            raise ValueError(f"unsupported validation suite evidence kind: {kind}")
        status = _text(self.status, "status")
        if status not in _EVIDENCE_STATUSES:
            raise ValueError(f"unsupported validation suite evidence status: {status}")
        source_ref = _text(self.source_ref, "source_ref")
        if isinstance(self.case_count, bool) or not isinstance(self.case_count, int) or self.case_count < 1:
            raise ValueError("case_count must be a positive integer")
        if isinstance(self.replay_count, bool) or not isinstance(self.replay_count, int) or self.replay_count < 0:
            raise ValueError("replay_count must be a nonnegative integer")
        if self.deterministic is not None and not isinstance(self.deterministic, bool):
            raise TypeError("deterministic must be boolean or null")
        if self.valid_result is not None and not isinstance(self.valid_result, bool):
            raise TypeError("valid_result must be boolean or null")
        reasons = _strings(self.reason_codes, "reason_codes")
        limitations = _strings(self.limitations, "limitations")
        metadata = _freeze(self.metadata)
        if not isinstance(metadata, Mapping):
            raise TypeError("metadata must be a mapping")
        object.__setattr__(self, "evidence_id", evidence_id)
        object.__setattr__(self, "technique", technique)
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "source_ref", source_ref)
        object.__setattr__(self, "source_hash", _hash(self.source_hash, "source_hash"))
        object.__setattr__(self, "reason_codes", tuple(dict.fromkeys(reasons)))
        object.__setattr__(self, "limitations", tuple(dict.fromkeys(limitations)))
        object.__setattr__(self, "metadata", metadata)
        expected_hash = canonical_json_hash(self._identity_payload())
        if self.entry_hash and _hash(self.entry_hash, "entry_hash", allow_empty=False) != expected_hash:
            raise ValueError("validation suite entry_hash does not match entry content")
        object.__setattr__(self, "entry_hash", expected_hash)

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "evidence_id": self.evidence_id,
            "technique": self.technique,
            "kind": self.kind,
            "status": self.status,
            "source_ref": self.source_ref,
            "source_hash": self.source_hash,
            "case_count": self.case_count,
            "replay_count": self.replay_count,
            "deterministic": self.deterministic,
            "valid_result": self.valid_result,
            "reason_codes": list(self.reason_codes),
            "limitations": list(self.limitations),
            "metadata": _json(self.metadata),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._identity_payload(), "entry_hash": self.entry_hash}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ValidationSuiteEntry":
        if not isinstance(value, Mapping):
            raise TypeError("validation suite entry must be a mapping")
        return cls(
            evidence_id=value.get("evidence_id", ""),
            technique=value.get("technique", ""),
            kind=value.get("kind", ""),
            status=value.get("status", ""),
            source_ref=value.get("source_ref", ""),
            source_hash=value.get("source_hash", ""),
            case_count=value.get("case_count", 1),
            replay_count=value.get("replay_count", 0),
            deterministic=value.get("deterministic"),
            valid_result=value.get("valid_result"),
            reason_codes=tuple(value.get("reason_codes", ())),
            limitations=tuple(value.get("limitations", ())),
            metadata=value.get("metadata", {}),
            entry_hash=value.get("entry_hash", ""),
            schema_version=value.get("schema_version", ""),
        )


@dataclass(frozen=True)
class ValidationSuiteReport:
    """Content-addressed aggregate of deterministic replay and smoke evidence."""

    suite_id: str
    status: str
    entries: tuple[ValidationSuiteEntry, ...]
    scientific_review_required: bool = True
    limitations: tuple[str, ...] = ()
    report_hash: str = ""
    schema_version: str = _SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != _SCHEMA_VERSION:
            raise ValueError("unsupported validation suite report schema version")
        suite_id = _id(self.suite_id, "suite_id")
        entries = tuple(self.entries)
        if not entries or not all(type(item) is ValidationSuiteEntry for item in entries):
            raise ValueError("validation suite report requires entries")
        if len({item.evidence_id for item in entries}) != len(entries):
            raise ValueError("validation suite evidence IDs must be unique")
        expected_status = "failed" if any(item.status == "failed" for item in entries) else "complete_with_review"
        if self.status != expected_status:
            raise ValueError("validation suite report status does not match entries")
        if not isinstance(self.scientific_review_required, bool) or not self.scientific_review_required:
            raise ValueError("validation suite reports always require scientific review")
        limitations = _strings(self.limitations, "limitations")
        object.__setattr__(self, "suite_id", suite_id)
        object.__setattr__(self, "entries", entries)
        object.__setattr__(self, "limitations", tuple(dict.fromkeys(limitations)))
        expected_hash = canonical_json_hash(self._identity_payload())
        if self.report_hash and _hash(self.report_hash, "report_hash", allow_empty=False) != expected_hash:
            raise ValueError("validation suite report_hash does not match report content")
        object.__setattr__(self, "report_hash", expected_hash)

    @property
    def techniques(self) -> tuple[str, ...]:
        return tuple(sorted({item.technique for item in self.entries}))

    @property
    def coverage(self) -> dict[str, Any]:
        by_kind: dict[str, int] = {}
        by_status: dict[str, int] = {}
        for item in self.entries:
            by_kind[item.kind] = by_kind.get(item.kind, 0) + 1
            by_status[item.status] = by_status.get(item.status, 0) + 1
        return {
            "entry_count": len(self.entries),
            "techniques": list(self.techniques),
            "by_kind": dict(sorted(by_kind.items())),
            "by_status": dict(sorted(by_status.items())),
            "replay_case_count": sum(item.case_count for item in self.entries if item.kind == "deterministic_replay"),
            "replay_count": sum(item.replay_count for item in self.entries),
        }

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "suite_id": self.suite_id,
            "status": self.status,
            "entries": [item.to_dict() for item in self.entries],
            "scientific_review_required": self.scientific_review_required,
            "limitations": list(self.limitations),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._identity_payload(),
            "coverage": self.coverage,
            "report_hash": self.report_hash,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ValidationSuiteReport":
        if not isinstance(value, Mapping):
            raise TypeError("validation suite report must be a mapping")
        report = cls(
            suite_id=value.get("suite_id", ""),
            status=value.get("status", ""),
            entries=tuple(ValidationSuiteEntry.from_dict(item) for item in value.get("entries", ())),
            scientific_review_required=value.get("scientific_review_required", True),
            limitations=tuple(value.get("limitations", ())),
            report_hash=value.get("report_hash", ""),
            schema_version=value.get("schema_version", ""),
        )
        supplied_coverage = value.get("coverage")
        if supplied_coverage is not None and _json(supplied_coverage) != report.coverage:
            raise ValueError("validation suite coverage does not match entries")
        return report


def _smoke_entry(
    value: Mapping[str, Any],
    *,
    index: int,
    source_ref: str,
    report_hash: str,
) -> ValidationSuiteEntry:
    technique = _id(value.get("technique", "unknown"), "smoke technique")
    raw_status = str(value.get("status") or "unavailable").strip().lower()
    valid_result = value.get("valid_result")
    if raw_status == "completed" and valid_result is True:
        kind = "smoke_only"
        status = "needs_review"
    elif raw_status in {"unavailable", "not_attempted", "candidate"} or valid_result is False:
        kind = "unavailable"
        status = "unavailable"
    else:
        kind = "smoke_only"
        status = "needs_review"
    reason = str(value.get("reason") or value.get("error_code") or value.get("core_status") or "").strip()
    limitations = [
        "Smoke/parser evidence is not an independent scientific validation.",
        "Capability promotion and publication use remain blocked pending review.",
    ]
    scientific_use = str(value.get("scientific_use") or "").strip()
    if scientific_use:
        limitations.append(scientific_use)
    metadata_keys = (
        "route",
        "core_status",
        "input_kind",
        "promotion",
        "scientific_use",
        "source_archive",
        "source_member",
        "output_dir",
    )
    metadata = {key: value[key] for key in metadata_keys if key in value and value[key] not in (None, "")}
    metadata.update({"source_report_hash": report_hash, "raw_status": raw_status})
    return ValidationSuiteEntry(
        evidence_id=f"smoke-{technique}-{index + 1:03d}",
        technique=technique,
        kind=kind,
        status=status,
        source_ref=f"{source_ref}#entries[{index}]",
        source_hash=canonical_json_hash(_json(dict(value))),
        case_count=1,
        valid_result=valid_result if isinstance(valid_result, bool) else None,
        reason_codes=(reason,) if reason else (),
        limitations=tuple(limitations),
        metadata=metadata,
    )


def build_validation_suite_report(
    *,
    suite_id: str = "polynexus-validation-suite-v1",
    replay_batch: ProjectValidationBatch | None = None,
    replay_source_ref: str = "public-replay-batch",
    smoke_report: Mapping[str, Any] | None = None,
    smoke_source_ref: str = "all-module-smoke-report",
) -> ValidationSuiteReport:
    """Build one aggregate report from existing validation projections."""

    if replay_batch is None and smoke_report is None:
        raise ValueError("validation suite requires a replay batch or smoke report")
    entries: list[ValidationSuiteEntry] = []
    if replay_batch is not None:
        if type(replay_batch) is not ProjectValidationBatch:
            raise TypeError("replay_batch must be an exact ProjectValidationBatch")
        for report in sorted(replay_batch.reports, key=lambda item: item.case_id):
            entries.append(
                ValidationSuiteEntry(
                    evidence_id=f"replay-{report.case_id}",
                    technique=report.technique,
                    kind="deterministic_replay",
                    status=report.status,
                    source_ref=f"{replay_source_ref}#case={report.case_id}",
                    source_hash=report.report_hash,
                    case_count=1,
                    replay_count=report.replay_count,
                    deterministic=report.deterministic,
                    reason_codes=report.reason_codes,
                    limitations=(
                        "Deterministic parser/Core replay evidence is not a certified standard.",
                        "Independent instrument/material replay, uncertainty, and human scientific review remain required.",
                    ),
                    metadata={
                        "batch_hash": replay_batch.batch_hash,
                        "first_output_hash": report.first_output_hash,
                        "second_output_hash": report.second_output_hash,
                        "scientific_review_required": report.scientific_review_required,
                    },
                )
            )
    if smoke_report is not None:
        if not isinstance(smoke_report, Mapping):
            raise TypeError("smoke_report must be a mapping")
        raw_entries = smoke_report.get("entries")
        if not isinstance(raw_entries, Sequence) or isinstance(raw_entries, (str, bytes, bytearray)):
            raise ValueError("smoke_report entries must be a sequence")
        report_hash = canonical_json_hash(_json(dict(smoke_report)))
        for index, value in enumerate(raw_entries):
            if not isinstance(value, Mapping):
                raise TypeError("smoke report entries must be mappings")
            entries.append(
                _smoke_entry(
                    value,
                    index=index,
                    source_ref=smoke_source_ref,
                    report_hash=report_hash,
                )
            )
    return ValidationSuiteReport(
        suite_id=suite_id,
        status="failed" if any(item.status == "failed" for item in entries) else "complete_with_review",
        entries=tuple(entries),
        limitations=(
            "This aggregate is an evidence index, not an independent scientific validation or capability decision.",
            "Smoke-only and unavailable entries must not be presented as validated material results.",
        ),
    )


__all__ = [
    "ValidationSuiteEntry",
    "ValidationSuiteReport",
    "build_validation_suite_report",
]
