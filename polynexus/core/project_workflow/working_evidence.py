"""Mutable current evidence-set index backed by validated run manifests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

@dataclass(frozen=True)
class WorkingEvidenceEntry:
    run_id: str
    manifest_path: str
    source_artifact_ids: tuple[str, ...]
    source_keys: tuple[str, ...]
    source_hashes: tuple[str, ...]
    techniques: tuple[str, ...]
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "manifest_path": self.manifest_path,
            "source_artifact_ids": list(self.source_artifact_ids),
            "source_keys": list(self.source_keys),
            "source_hashes": list(self.source_hashes),
            "techniques": list(self.techniques),
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "WorkingEvidenceEntry":
        if not isinstance(value, Mapping):
            raise TypeError("working evidence entry must be a mapping")
        entry = cls(
            run_id=str(value["run_id"]),
            manifest_path=str(value["manifest_path"]),
            source_artifact_ids=tuple(str(item) for item in value.get("source_artifact_ids", ())),
            source_keys=tuple(str(item) for item in value.get("source_keys", ())),
            source_hashes=tuple(str(item) for item in value.get("source_hashes", ())),
            techniques=tuple(str(item) for item in value.get("techniques", ())),
            status=str(value["status"]),
        )
        if not entry.run_id or not entry.manifest_path or not entry.source_artifact_ids or not entry.source_keys:
            raise ValueError("working evidence entry is incomplete")
        if len(entry.source_artifact_ids) != len(entry.source_keys):
            raise ValueError("working evidence sources are misaligned")
        if entry.status not in {"completed", "review_required"}:
            raise ValueError("working evidence entry status is invalid")
        return entry


@dataclass(frozen=True)
class WorkingEvidenceStatus:
    total: int
    completed: int
    review_required: int
    techniques: tuple[str, ...]
    run_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "completed": self.completed,
            "review_required": self.review_required,
            "techniques": list(self.techniques),
            "run_ids": list(self.run_ids),
        }


class WorkingEvidenceIndex:
    """Source-keyed mutable draft frontier for an eventual package freeze."""

    def __init__(self, entries: Iterable[WorkingEvidenceEntry] = ()) -> None:
        self._entries: dict[str, WorkingEvidenceEntry] = {}
        for entry in entries:
            self.upsert(entry)

    @property
    def entries(self) -> tuple[WorkingEvidenceEntry, ...]:
        return tuple(self._entries[key] for key in sorted(self._entries))

    def upsert(self, entry: WorkingEvidenceEntry) -> None:
        conflicts = set(entry.source_keys)
        self._entries = {
            run_id: value
            for run_id, value in self._entries.items()
            if not conflicts.intersection(value.source_keys)
        }
        self._entries[entry.run_id] = entry

    def remove(self, run_id: str) -> bool:
        return self._entries.pop(str(run_id), None) is not None

    def status(self) -> WorkingEvidenceStatus:
        entries = self.entries
        return WorkingEvidenceStatus(
            total=len(entries),
            completed=sum(entry.status == "completed" for entry in entries),
            review_required=sum(entry.status == "review_required" for entry in entries),
            techniques=tuple(sorted({technique for entry in entries for technique in entry.techniques})),
            run_ids=tuple(entry.run_id for entry in entries),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "entries": [entry.to_dict() for entry in self.entries],
            "status": self.status().to_dict(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "WorkingEvidenceIndex":
        if not isinstance(value, Mapping) or value.get("version") != 1:
            raise ValueError("working evidence index is invalid")
        raw_entries = value.get("entries", ())
        if not isinstance(raw_entries, (list, tuple)):
            raise ValueError("working evidence entries are invalid")
        return cls(WorkingEvidenceEntry.from_dict(item) for item in raw_entries)


__all__ = ["WorkingEvidenceEntry", "WorkingEvidenceIndex", "WorkingEvidenceStatus"]
