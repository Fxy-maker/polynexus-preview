"""Immutable, JSON-safe experiment templates used by deterministic providers."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "1"


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Canonical templates do not allow non-finite floats")
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    raise TypeError(f"Canonical templates do not support {type(value).__name__}")


def _canonical_json(value: Any) -> str:
    return json.dumps(_json_safe(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _freeze(value: Any) -> Any:
    """Freeze a canonical JSON value after checking it is persistable."""
    _canonical_json(value)
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _public(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _public(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_public(item) for item in value]
    return value


def _hash(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ConversionRecord:
    """Auditable observations and decisions made while converting raw data."""

    conversion_id: str
    source_artifact_id: str
    contract_version: str = CONTRACT_VERSION
    observed_columns: tuple[str, ...] = ()
    extracted_segments: tuple[Mapping[str, Any], ...] = ()
    excluded_segments: tuple[Mapping[str, Any], ...] = ()
    warnings: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    conversion_hash: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "observed_columns", tuple(str(column) for column in self.observed_columns))
        object.__setattr__(self, "extracted_segments", tuple(_freeze(item) for item in self.extracted_segments))
        object.__setattr__(self, "excluded_segments", tuple(_freeze(item) for item in self.excluded_segments))
        object.__setattr__(self, "warnings", tuple(str(item) for item in self.warnings))
        object.__setattr__(self, "reason_codes", tuple(str(item) for item in self.reason_codes))

    @classmethod
    def create(
        cls,
        *,
        conversion_id: str,
        source_artifact_id: str,
        observed_columns: Sequence[str] = (),
        extracted_segments: Sequence[Mapping[str, Any]] = (),
        excluded_segments: Sequence[Mapping[str, Any]] = (),
        warnings: Sequence[str] = (),
        reason_codes: Sequence[str] = (),
        contract_version: str = CONTRACT_VERSION,
    ) -> "ConversionRecord":
        payload = cls._payload(
            conversion_id=conversion_id,
            source_artifact_id=source_artifact_id,
            contract_version=contract_version,
            observed_columns=observed_columns,
            extracted_segments=extracted_segments,
            excluded_segments=excluded_segments,
            warnings=warnings,
            reason_codes=reason_codes,
        )
        return cls(
            conversion_id=str(conversion_id),
            source_artifact_id=str(source_artifact_id),
            contract_version=str(contract_version),
            observed_columns=tuple(observed_columns),
            extracted_segments=tuple(extracted_segments),
            excluded_segments=tuple(excluded_segments),
            warnings=tuple(warnings),
            reason_codes=tuple(reason_codes),
            conversion_hash=_hash(payload),
        )

    @staticmethod
    def _payload(**values: Any) -> dict[str, Any]:
        return {
            "conversion_id": str(values["conversion_id"]),
            "source_artifact_id": str(values["source_artifact_id"]),
            "contract_version": str(values["contract_version"]),
            "observed_columns": list(values["observed_columns"]),
            "extracted_segments": _public(tuple(values["extracted_segments"])),
            "excluded_segments": _public(tuple(values["excluded_segments"])),
            "warnings": list(values["warnings"]),
            "reason_codes": list(values["reason_codes"]),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(
                conversion_id=self.conversion_id,
                source_artifact_id=self.source_artifact_id,
                contract_version=self.contract_version,
                observed_columns=self.observed_columns,
                extracted_segments=self.extracted_segments,
                excluded_segments=self.excluded_segments,
                warnings=self.warnings,
                reason_codes=self.reason_codes,
            ),
            "conversion_hash": self.conversion_hash,
        }


@dataclass(frozen=True)
class CanonicalExperiment:
    """A validated template that can be passed to a deterministic provider."""

    template_id: str
    source_artifact_id: str
    payload: Mapping[str, Any]
    conversion_record: ConversionRecord
    contract_version: str = CONTRACT_VERSION
    content_hash: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", _freeze(self.payload))

    @classmethod
    def create(
        cls,
        *,
        template_id: str,
        source_artifact_id: str,
        payload: Mapping[str, Any],
        conversion_record: ConversionRecord,
        contract_version: str = CONTRACT_VERSION,
    ) -> "CanonicalExperiment":
        identity_payload = cls._payload(
            template_id=template_id,
            source_artifact_id=source_artifact_id,
            payload=payload,
            conversion_record=conversion_record,
            contract_version=contract_version,
        )
        return cls(
            template_id=str(template_id),
            source_artifact_id=str(source_artifact_id),
            payload=payload,
            conversion_record=conversion_record,
            contract_version=str(contract_version),
            content_hash=_hash(identity_payload),
        )

    @staticmethod
    def _payload(**values: Any) -> dict[str, Any]:
        return {
            "template_id": str(values["template_id"]),
            "source_artifact_id": str(values["source_artifact_id"]),
            "payload": _public(values["payload"]),
            "conversion_record": values["conversion_record"].to_dict(),
            "contract_version": str(values["contract_version"]),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(
                template_id=self.template_id,
                source_artifact_id=self.source_artifact_id,
                payload=self.payload,
                conversion_record=self.conversion_record,
                contract_version=self.contract_version,
            ),
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CanonicalExperiment":
        record_value = value.get("conversion_record")
        if not isinstance(record_value, Mapping):
            raise ValueError("Canonical template conversion record is missing")
        record = ConversionRecord.create(
            conversion_id=str(record_value["conversion_id"]),
            source_artifact_id=str(record_value["source_artifact_id"]),
            contract_version=str(record_value.get("contract_version", CONTRACT_VERSION)),
            observed_columns=record_value.get("observed_columns", ()),
            extracted_segments=record_value.get("extracted_segments", ()),
            excluded_segments=record_value.get("excluded_segments", ()),
            warnings=record_value.get("warnings", ()),
            reason_codes=record_value.get("reason_codes", ()),
        )
        if str(record_value.get("conversion_hash", "")) != record.conversion_hash:
            raise ValueError("Canonical conversion record hash does not match its content")
        template = cls.create(
            template_id=str(value["template_id"]),
            source_artifact_id=str(value["source_artifact_id"]),
            payload=value.get("payload", {}),
            conversion_record=record,
            contract_version=str(value.get("contract_version", CONTRACT_VERSION)),
        )
        if str(value.get("content_hash", "")) != template.content_hash:
            raise ValueError("Canonical template content hash does not match its content")
        return template


@dataclass(frozen=True)
class ConversionOutcome:
    """Explicit conversion status; blocked conversions cannot supply a template."""

    status: str
    record: ConversionRecord
    template: CanonicalExperiment | None = None
    reason_codes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.status not in {"ready", "review_required", "blocked"}:
            raise ValueError(f"Unsupported conversion status: {self.status}")
        if self.status == "blocked" and self.template is not None:
            raise ValueError("Blocked conversion cannot contain a canonical template")
        object.__setattr__(self, "reason_codes", tuple(str(code) for code in self.reason_codes))
