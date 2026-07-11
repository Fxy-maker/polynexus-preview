"""Selection state for generated figure object editing."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class FigureSelectionModel(QObject):
    selection_changed = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._object_id = ""
        self._source = ""

    def select(self, object_id: str, source: str) -> None:
        object_id = str(object_id or "")
        source = str(source or "")
        if self._object_id == object_id and self._source == source:
            return
        self._object_id = object_id
        self._source = source
        self.selection_changed.emit(object_id, source)

    def clear(self, source: str) -> None:
        self.select("", source)

    @property
    def object_id(self) -> str:
        return self._object_id

    @property
    def source(self) -> str:
        return self._source
