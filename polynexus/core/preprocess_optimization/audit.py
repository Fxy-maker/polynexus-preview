from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from .contracts import DecisionRecord


class AuditLogError(RuntimeError):
    """Raised when a structured decision audit cannot be read or written."""


_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()


def _lock_for(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(key, threading.Lock())


class DecisionAuditLog:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._lock = _lock_for(self.path)

    def append(self, record: DecisionRecord | dict[str, Any]) -> None:
        payload = record.to_dict() if isinstance(record, DecisionRecord) else dict(record)
        line = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self._lock, self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(line)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            raise AuditLogError(f"Failed to append decision audit: {exc}") from exc

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        try:
            with self._lock, self.path.open("r", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, start=1):
                    if not line.strip():
                        continue
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise AuditLogError(
                            f"Corrupt decision audit at line {line_number}: {exc.msg}"
                        ) from exc
                    if not isinstance(payload, dict):
                        raise AuditLogError(
                            f"Corrupt decision audit at line {line_number}: object required"
                        )
                    rows.append(payload)
        except OSError as exc:
            raise AuditLogError(f"Failed to read decision audit: {exc}") from exc
        return rows
