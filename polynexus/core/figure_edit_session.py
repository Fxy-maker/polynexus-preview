"""Undoable command session for a Qt-free figure editing core."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from .figure_edit_capabilities import EditCommand, EditResult, SelectionState


@dataclass(frozen=True)
class _HistoryEntry:
    command: EditCommand
    snapshot: object
    result: EditResult


def _session_failure(error_code: str, message: str) -> EditResult:
    return EditResult(False, error_code=error_code, message=message)


class EditSession:
    """Own a private document and apply atomic commands with undo/redo."""

    def __init__(self, document: dict):
        self._document = deepcopy(document) if isinstance(document, dict) else {}
        self._saved_document = deepcopy(self._document)
        self._selection = SelectionState()
        self._undo_stack: list[_HistoryEntry] = []
        self._redo_stack: list[_HistoryEntry] = []

    @property
    def document(self) -> dict:
        """Return a deep copy so callers cannot mutate the session behind history."""

        return deepcopy(self._document)

    @property
    def selection(self) -> SelectionState:
        return self._selection

    @property
    def dirty(self) -> bool:
        return self._document != self._saved_document

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    @property
    def history(self) -> tuple[EditCommand, ...]:
        """Expose command history without exposing its mutable snapshots."""

        return tuple(entry.command for entry in self._undo_stack)

    def select(self, object_id: str, source: str) -> None:
        self._selection = SelectionState(
            object_id=str(object_id or ""),
            source=str(source or ""),
        )

    def execute(self, command: EditCommand) -> EditResult:
        if not callable(getattr(command, "apply", None)) or not callable(
            getattr(command, "revert", None)
        ):
            return _session_failure("invalid_command", "Command must implement apply and revert.")

        working_document = deepcopy(self._document)
        before = deepcopy(self._document)
        try:
            result, snapshot = command.apply(working_document)
        except Exception as exc:  # Keep a custom command from breaking session atomicity.
            return _session_failure("command_error", str(exc))
        if not isinstance(result, EditResult):
            return _session_failure("invalid_command_result", "Command apply returned an invalid result.")
        if not result.changed:
            return result
        if result.error_code:
            return _session_failure(result.error_code, result.message)
        if working_document == before:
            return EditResult(
                False,
                message="Command reported a change without changing the document.",
                affected_ids=result.affected_ids,
            )

        self._document = working_document
        self._undo_stack.append(
            _HistoryEntry(command=command, snapshot=deepcopy(snapshot), result=result)
        )
        self._redo_stack.clear()
        return result

    def undo(self) -> EditResult:
        if not self._undo_stack:
            return _session_failure("nothing_to_undo", "There is no command to undo.")
        entry = self._undo_stack[-1]
        working_document = deepcopy(self._document)
        before = deepcopy(self._document)
        try:
            result = entry.command.revert(working_document, deepcopy(entry.snapshot))
        except Exception as exc:
            return _session_failure("command_error", str(exc))
        if not isinstance(result, EditResult):
            return _session_failure("invalid_command_result", "Command revert returned an invalid result.")
        if not result.changed:
            return result
        if result.error_code:
            return _session_failure(result.error_code, result.message)
        if working_document == before:
            return EditResult(
                False,
                message="Command reported a change without changing the document.",
                affected_ids=result.affected_ids,
            )
        self._document = working_document
        self._undo_stack.pop()
        self._redo_stack.append(entry)
        return result

    def redo(self) -> EditResult:
        if not self._redo_stack:
            return _session_failure("nothing_to_redo", "There is no command to redo.")
        entry = self._redo_stack[-1]
        working_document = deepcopy(self._document)
        before = deepcopy(self._document)
        try:
            result, snapshot = entry.command.apply(working_document)
        except Exception as exc:
            return _session_failure("command_error", str(exc))
        if not isinstance(result, EditResult):
            return _session_failure("invalid_command_result", "Command apply returned an invalid result.")
        if not result.changed:
            return result
        if result.error_code:
            return _session_failure(result.error_code, result.message)
        if working_document == before:
            return EditResult(
                False,
                message="Command reported a change without changing the document.",
                affected_ids=result.affected_ids,
            )
        self._document = working_document
        self._redo_stack.pop()
        self._undo_stack.append(
            _HistoryEntry(command=entry.command, snapshot=deepcopy(snapshot), result=result)
        )
        return result

    def mark_saved(self) -> None:
        self._saved_document = deepcopy(self._document)


__all__ = ["EditSession"]
