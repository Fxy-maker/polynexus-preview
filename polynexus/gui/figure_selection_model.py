"""Selection state for generated figure object editing."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class FigureSelectionModel(QObject):
    selection_changed = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._object_id = ""
        self._selected_ids = ()
        self._source = ""

    def select(self, object_id: str, source: str) -> None:
        self.select_many([object_id] if object_id else [], source)

    def select_many(self, object_ids, source: str) -> None:
        normalized = []
        seen = set()
        for object_id in object_ids or ():
            value = str(object_id or "").strip()
            if value and value not in seen:
                seen.add(value)
                normalized.append(value)
        selected_ids = tuple(normalized)
        source = str(source or "")
        if self._selected_ids == selected_ids and self._source == source:
            return
        self._selected_ids = selected_ids
        self._object_id = selected_ids[0] if selected_ids else ""
        self._source = source
        self.selection_changed.emit(self._object_id, source)

    def clear(self, source: str) -> None:
        self.select("", source)

    @property
    def object_id(self) -> str:
        return self._object_id

    @property
    def selected_ids(self) -> tuple[str, ...]:
        return self._selected_ids

    @property
    def source(self) -> str:
        return self._source
