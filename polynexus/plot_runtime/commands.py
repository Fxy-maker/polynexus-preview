"""Deterministic commands and undo/redo for the renderer-neutral plot state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import GraphDocument, Worksheet


@dataclass(frozen=True)
class PlotState:
    worksheet: Worksheet
    document: GraphDocument


@dataclass(frozen=True)
class CommandResult:
    state: PlotState
    affected_data_ids: tuple[str, ...]
    affected_object_ids: tuple[str, ...]


@dataclass(frozen=True)
class EditWorksheetCells:
    changes: Any

    def __post_init__(self) -> None:
        normalized = tuple(
            (
                str(column_id),
                tuple((int(row), value) for row, value in sorted(cell_changes.items())),
            )
            for column_id, cell_changes in sorted(dict(self.changes).items())
        )
        object.__setattr__(self, "changes", normalized)

    def changes_map(self) -> dict[str, dict[int, Any]]:
        return {column_id: dict(changes) for column_id, changes in self.changes}

    def to_payload(self) -> dict[str, Any]:
        return {
            "type": "edit_worksheet_cells",
            "changes": {
                column_id: {str(row): value for row, value in changes}
                for column_id, changes in self.changes
            },
        }


@dataclass(frozen=True)
class UpdateGraphStyle:
    object_id: str
    updates: Any

    def __post_init__(self) -> None:
        object.__setattr__(self, "updates", tuple(sorted(dict(self.updates).items())))

    def updates_map(self) -> dict[str, Any]:
        return dict(self.updates)

    def to_payload(self) -> dict[str, Any]:
        return {
            "type": "update_graph_style",
            "object_id": self.object_id,
            "updates": dict(self.updates),
        }


@dataclass(frozen=True)
class UpdateGraphProperties:
    object_id: str
    updates: Any

    def __post_init__(self) -> None:
        object.__setattr__(self, "updates", tuple(sorted(dict(self.updates).items())))

    def updates_map(self) -> dict[str, Any]:
        return dict(self.updates)

    def to_payload(self) -> dict[str, Any]:
        return {
            "type": "update_graph_properties",
            "object_id": self.object_id,
            "updates": dict(self.updates),
        }


class CommandStack:
    def __init__(self, state: PlotState):
        self.current = state
        self._undo: list[tuple[Any, PlotState, PlotState, CommandResult]] = []
        self._redo: list[tuple[Any, PlotState, PlotState, CommandResult]] = []

    def prepare(self, command: Any) -> CommandResult:
        before = self.current
        if isinstance(command, EditWorksheetCells):
            revision = before.worksheet.edit_cells(command.changes_map())
            worksheet = before.worksheet.checkout(revision)
            next_state = PlotState(worksheet=worksheet, document=before.document)
            affected_data_ids = tuple(column_id for column_id, _ in command.changes)
            affected_object_ids = before.document.object_ids_for_columns(set(affected_data_ids))
        elif isinstance(command, UpdateGraphStyle):
            object_item = before.document.object_by_id(command.object_id)
            next_state = PlotState(
                worksheet=before.worksheet,
                document=before.document.replace_object(
                    object_item.with_style(command.updates_map())
                ),
            )
            affected_data_ids = ()
            affected_object_ids = (command.object_id,)
        elif isinstance(command, UpdateGraphProperties):
            object_item = before.document.object_by_id(command.object_id)
            next_state = PlotState(
                worksheet=before.worksheet,
                document=before.document.replace_object(
                    object_item.with_properties(command.updates_map())
                ),
            )
            affected_data_ids = ()
            affected_object_ids = (command.object_id,)
        else:
            raise TypeError(f"unsupported plot command: {type(command).__name__}")
        return CommandResult(next_state, affected_data_ids, affected_object_ids)

    def commit(self, command: Any, result: CommandResult) -> CommandResult:
        before = self.current
        self.current = result.state
        self._undo.append((command, before, result.state, result))
        self._redo.clear()
        return result

    def execute(self, command: Any) -> CommandResult:
        return self.commit(command, self.prepare(command))

    def undo(self) -> PlotState:
        if not self._undo:
            return self.current
        item = self._undo.pop()
        self._redo.append(item)
        self.current = item[1]
        return self.current

    def redo(self) -> PlotState:
        if not self._redo:
            return self.current
        item = self._redo.pop()
        self._undo.append(item)
        self.current = item[2]
        return self.current

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)
