"""Immutable identity and result-state contract for the main GUI workspace."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Any


class WorkspaceResultStatus(str, Enum):
    """Lifecycle states used by context-bound GUI surfaces."""

    EMPTY = "empty"
    CONFIGURED = "configured"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STALE = "stale"


def _text(value: Any, *, lower: bool = False) -> str:
    result = str(value or "").strip()
    return result.casefold() if lower else result


def _path_text(value: Any) -> str:
    """Normalize Windows/Unix spellings without touching the filesystem."""

    result = _text(value, lower=True).replace("\\", "/")
    if len(result) > 1:
        result = result.rstrip("/")
    return result


def _status(value: Any) -> WorkspaceResultStatus:
    if isinstance(value, WorkspaceResultStatus):
        return value
    try:
        return WorkspaceResultStatus(_text(value, lower=True))
    except ValueError:
        return WorkspaceResultStatus.EMPTY


@dataclass(frozen=True)
class WorkspaceContext:
    """The identity of the data/result currently projected by the GUI."""

    technique: str = ""
    submodule: str = ""
    source_path: str = ""
    input_mode: str = ""
    output_dir: str = ""
    run_id: str = ""
    run_root: str = ""
    result_status: WorkspaceResultStatus = WorkspaceResultStatus.EMPTY
    result_origin: str = ""
    revision: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "technique", _text(self.technique, lower=True))
        object.__setattr__(self, "submodule", _text(self.submodule, lower=True))
        object.__setattr__(self, "source_path", _path_text(self.source_path))
        object.__setattr__(self, "input_mode", _text(self.input_mode, lower=True))
        object.__setattr__(self, "output_dir", _path_text(self.output_dir))
        object.__setattr__(self, "run_id", _text(self.run_id))
        object.__setattr__(self, "run_root", _path_text(self.run_root))
        object.__setattr__(self, "result_status", _status(self.result_status))
        object.__setattr__(self, "result_origin", _text(self.result_origin))
        try:
            revision = max(0, int(self.revision or 0))
        except (TypeError, ValueError):
            revision = 0
        object.__setattr__(self, "revision", revision)

    @classmethod
    def empty(cls) -> "WorkspaceContext":
        return cls()

    @property
    def identity_key(self) -> tuple[str, str, str, str, str]:
        return (
            self.technique,
            self.submodule,
            self.source_path,
            self.input_mode,
            self.output_dir,
        )

    def with_result(
        self,
        *,
        run_id: str | None = None,
        result_status: WorkspaceResultStatus | str | None = None,
        result_origin: str | None = None,
        revision: int | None = None,
    ) -> "WorkspaceContext":
        next_run_id = self.run_id if run_id is None else _text(run_id)
        next_status = self.result_status if result_status is None else _status(result_status)
        if (
            result_status is None
            and self.run_id
            and next_run_id
            and next_run_id != self.run_id
        ):
            next_status = WorkspaceResultStatus.STALE
        return replace(
            self,
            run_id=next_run_id,
            result_status=next_status,
            result_origin=self.result_origin if result_origin is None else result_origin,
            revision=self.revision if revision is None else revision,
        )

    def with_source(self, source_path: str) -> "WorkspaceContext":
        next_context = replace(self, source_path=source_path)
        if self.run_id and next_context.identity_key != self.identity_key:
            next_context = replace(next_context, result_status=WorkspaceResultStatus.STALE)
        return next_context

    def result_matches(self, result_context: "WorkspaceContext") -> bool:
        """Return whether ``result_context`` belongs to this active context."""

        if not isinstance(result_context, WorkspaceContext):
            return False
        if self.result_status in {
            WorkspaceResultStatus.STALE,
            WorkspaceResultStatus.FAILED,
            WorkspaceResultStatus.CANCELLED,
        }:
            return False
        return bool(
            self.identity_key == result_context.identity_key
            and self.run_id
            and self.run_id == result_context.run_id
            and result_context.result_status is WorkspaceResultStatus.COMPLETE
        )


__all__ = ["WorkspaceContext", "WorkspaceResultStatus"]
