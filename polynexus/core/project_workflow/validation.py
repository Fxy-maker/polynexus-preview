"""Project-local aggregation for technique-neutral validation reports."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ..ai_platform.contracts import canonical_json_hash
from ..validation_harness import ValidationCase, ValidationReport, run_validation


_SCHEMA_VERSION = "1"


def _mapping(value: Mapping[str, Any], label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    return {str(key): value_item for key, value_item in value.items()}


@dataclass(frozen=True)
class ProjectValidationEntry:
    """One case and its two persisted public result projections."""

    case: ValidationCase
    first_output: Mapping[str, Any]
    second_output: Mapping[str, Any]
    raw_hash_before: str | None = None
    raw_hash_after: str | None = None
    entry_hash: str = ""
    schema_version: str = _SCHEMA_VERSION

    def __post_init__(self) -> None:
        if type(self.case) is not ValidationCase:
            raise TypeError("project validation entry requires an exact ValidationCase")
        if self.schema_version != _SCHEMA_VERSION:
            raise ValueError("Unsupported project validation entry schema version")
        first = _mapping(self.first_output, "first_output")
        second = _mapping(self.second_output, "second_output")
        before = self.raw_hash_before
        after = self.raw_hash_after
        if before is not None:
            before = str(before).strip().lower()
            if len(before) != 64:
                raise ValueError("raw_hash_before must be a SHA-256")
        if after is not None:
            after = str(after).strip().lower()
            if len(after) != 64:
                raise ValueError("raw_hash_after must be a SHA-256")
        object.__setattr__(self, "first_output", first)
        object.__setattr__(self, "second_output", second)
        object.__setattr__(self, "raw_hash_before", before)
        object.__setattr__(self, "raw_hash_after", after)
        expected = canonical_json_hash(self._identity_payload())
        if self.entry_hash and self.entry_hash != expected:
            raise ValueError("validation entry_hash does not match entry content")
        object.__setattr__(self, "entry_hash", expected)

    @classmethod
    def create(cls, *, case: ValidationCase, first_output: Mapping[str, Any], second_output: Mapping[str, Any], **kwargs: Any) -> "ProjectValidationEntry":
        return cls(case=case, first_output=first_output, second_output=second_output, **kwargs)

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "case": self.case.to_dict(),
            "first_output": self.first_output,
            "second_output": self.second_output,
            "raw_hash_before": self.raw_hash_before,
            "raw_hash_after": self.raw_hash_after,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._identity_payload(), "entry_hash": self.entry_hash}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProjectValidationEntry":
        if not isinstance(value, Mapping):
            raise TypeError("project validation entry must be a mapping")
        return cls(
            case=ValidationCase.from_dict(value.get("case", {})),
            first_output=value.get("first_output", {}),
            second_output=value.get("second_output", {}),
            raw_hash_before=value.get("raw_hash_before"),
            raw_hash_after=value.get("raw_hash_after"),
            entry_hash=value.get("entry_hash", ""),
            schema_version=value.get("schema_version", ""),
        )


@dataclass(frozen=True)
class ProjectValidationBatch:
    """Immutable aggregate of per-case validation observations."""

    status: str
    reports: tuple[ValidationReport, ...]
    batch_hash: str = ""
    schema_version: str = _SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != _SCHEMA_VERSION:
            raise ValueError("Unsupported project validation batch schema version")
        reports = tuple(self.reports)
        if not reports or not all(type(item) is ValidationReport for item in reports):
            raise ValueError("project validation batch requires validation reports")
        if len({item.case_id for item in reports}) != len(reports):
            raise ValueError("project validation case IDs must be unique")
        expected_status = "passed" if all(item.status == "passed" for item in reports) else "failed"
        if self.status != expected_status:
            raise ValueError("project validation batch status does not match reports")
        object.__setattr__(self, "reports", reports)
        expected = canonical_json_hash(self._identity_payload())
        if self.batch_hash and self.batch_hash != expected:
            raise ValueError("validation batch_hash does not match batch content")
        object.__setattr__(self, "batch_hash", expected)

    @property
    def techniques(self) -> tuple[str, ...]:
        return tuple(sorted({item.technique for item in self.reports}))

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "reports": [item.to_dict() for item in self.reports],
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._identity_payload(), "batch_hash": self.batch_hash}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProjectValidationBatch":
        if not isinstance(value, Mapping):
            raise TypeError("project validation batch must be a mapping")
        return cls(
            status=value.get("status", ""),
            reports=tuple(ValidationReport.from_dict(item) for item in value.get("reports", ())),
            batch_hash=value.get("batch_hash", ""),
            schema_version=value.get("schema_version", ""),
        )


def run_project_validation_batch(entries: Sequence[ProjectValidationEntry]) -> ProjectValidationBatch:
    """Run all entries in stable case-ID order; one failure does not stop peers."""

    if isinstance(entries, (str, bytes, bytearray)) or not isinstance(entries, Sequence):
        raise TypeError("project validation entries must be a sequence")
    normalized = tuple(entries)
    if not normalized or not all(type(item) is ProjectValidationEntry for item in normalized):
        raise ValueError("project validation batch requires entries")
    reports: list[ValidationReport] = []
    for entry in sorted(normalized, key=lambda item: item.case.case_id):
        outputs = [entry.first_output, entry.second_output]

        def calculator(_payload: Mapping[str, Any]) -> Mapping[str, Any]:
            return outputs.pop(0)

        hashes = [entry.raw_hash_before, entry.raw_hash_after]
        raw_provider = None
        if any(item is not None for item in hashes):
            if hashes[0] is None or hashes[1] is None:
                # A one-sided snapshot cannot prove preservation.
                hashes = [hashes[0], hashes[1] or hashes[0]]
            raw_values = iter(hashes)

            def raw_provider() -> str:
                value = next(raw_values)
                if value is None:
                    raise ValueError("raw hash snapshot missing")
                return value

        reports.append(run_validation(entry.case, calculator, raw_hash_provider=raw_provider))
    return ProjectValidationBatch(
        status="passed" if all(item.status == "passed" for item in reports) else "failed",
        reports=tuple(reports),
    )


__all__ = ["ProjectValidationEntry", "ProjectValidationBatch", "run_project_validation_batch"]
