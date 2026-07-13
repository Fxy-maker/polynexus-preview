from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPERIENCE_SCHEMA_VERSION = "1.0"
_ALLOWED_ACCEPTED_BY = {"auto_accept", "user_confirmed"}


class ExperienceStoreError(RuntimeError):
    """Raised when scoped preprocessing experience is invalid or unavailable."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalized_text(value: str) -> str:
    return str(value or "").strip().casefold()


@dataclass(frozen=True)
class ExperienceKey:
    technique: str
    instrument_fingerprint: str
    sample_family: str
    schema_version: str
    core_major_version: str

    def __post_init__(self) -> None:
        for name in (
            "technique",
            "instrument_fingerprint",
            "sample_family",
            "schema_version",
            "core_major_version",
        ):
            if not str(getattr(self, name) or "").strip():
                raise ExperienceStoreError(f"Experience key requires {name}")

    def normalized(self) -> tuple[str, str, str, str, str]:
        return (
            _normalized_text(self.technique),
            _normalized_text(self.instrument_fingerprint),
            _normalized_text(self.sample_family),
            _normalized_text(self.schema_version),
            _normalized_text(self.core_major_version),
        )


@dataclass(frozen=True)
class ExperienceRecord:
    experience_id: str
    key: ExperienceKey
    config_delta: dict[str, Any]
    accepted_by: str
    evidence_summary: dict[str, Any] = field(default_factory=dict)
    intent_summary: dict[str, Any] = field(default_factory=dict)
    symptom_names: tuple[str, ...] = ()
    revoked: bool = False
    created_at: str = field(default_factory=_utc_now)
    revoked_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["symptom_names"] = list(self.symptom_names)
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ExperienceRecord":
        key_payload = payload.get("key")
        if not isinstance(key_payload, dict):
            raise ExperienceStoreError("corrupt experience record key")
        try:
            key = ExperienceKey(**key_payload)
            return cls(
                experience_id=str(payload["experience_id"]),
                key=key,
                config_delta=dict(payload.get("config_delta", {})),
                accepted_by=str(payload["accepted_by"]),
                evidence_summary=dict(payload.get("evidence_summary", {})),
                intent_summary=dict(payload.get("intent_summary", {})),
                symptom_names=tuple(str(item) for item in payload.get("symptom_names", [])),
                revoked=bool(payload.get("revoked", False)),
                created_at=str(payload.get("created_at", "")),
                revoked_at=str(payload.get("revoked_at", "")),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ExperienceStoreError(f"corrupt experience record: {exc}") from exc


class ExperienceStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def retrieve(self, key: ExperienceKey) -> list[ExperienceRecord]:
        scope = key.normalized()
        return [
            record
            for record in self._read_records()
            if not record.revoked and record.key.normalized() == scope
        ]

    def all_records(self) -> list[ExperienceRecord]:
        return self._read_records()

    def accept(self, record: ExperienceRecord) -> None:
        if record.accepted_by not in _ALLOWED_ACCEPTED_BY:
            raise ExperienceStoreError(
                f"accepted_by must be one of {sorted(_ALLOWED_ACCEPTED_BY)}"
            )
        if not record.experience_id.strip():
            raise ExperienceStoreError("experience_id is required")
        records = self._read_records()
        for index, existing in enumerate(records):
            if existing.experience_id != record.experience_id:
                continue
            if existing.revoked:
                raise ExperienceStoreError("revoked experience cannot be accepted again")
            records[index] = record
            self._write_records(records)
            return
        records.append(record)
        self._write_records(records)

    def revoke(self, experience_id: str) -> bool:
        records = self._read_records()
        changed = False
        for index, record in enumerate(records):
            if record.experience_id != experience_id or record.revoked:
                continue
            records[index] = replace(record, revoked=True, revoked_at=_utc_now())
            changed = True
            break
        if changed:
            self._write_records(records)
        return changed

    def _read_records(self) -> list[ExperienceRecord]:
        if not self.path.exists():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ExperienceStoreError(f"corrupt experience store: {exc}") from exc
        if not isinstance(payload, dict) or payload.get("schema_version") != EXPERIENCE_SCHEMA_VERSION:
            raise ExperienceStoreError("corrupt experience store: unsupported schema")
        raw_records = payload.get("records")
        if not isinstance(raw_records, list):
            raise ExperienceStoreError("corrupt experience store: records must be a list")
        return [ExperienceRecord.from_dict(item) for item in raw_records if isinstance(item, dict)]

    def _write_records(self, records: list[ExperienceRecord]) -> None:
        payload = {
            "schema_version": EXPERIENCE_SCHEMA_VERSION,
            "records": [record.to_dict() for record in records],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temp_path = Path(handle.name)
                json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, self.path)
            temp_path = None
        except OSError as exc:
            raise ExperienceStoreError(f"Failed to write experience store: {exc}") from exc
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass
