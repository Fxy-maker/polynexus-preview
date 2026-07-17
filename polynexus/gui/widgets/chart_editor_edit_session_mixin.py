"""Qt-independent adapters between chart-editor widgets and an edit session."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy

from ...core.figure_edit_commands import UpdateGeometryCommand, UpdateStyleCommand


class ChartEditorEditSessionMixin:
    """Route widget proposals through the shared, undoable edit session."""

    def _execute_edit(self, command):
        session = self._edit_session_for_adapter()
        if session is None:
            return None
        result = session.execute(command)
        return self._project_edit_result(result)

    def _project_edit_result(self, result):
        if getattr(result, "changed", False):
            self._sync_editor_from_session()
        return result

    def _sync_editor_from_session(self):
        session = self._edit_session_for_adapter()
        if session is None:
            return None
        document = session.document
        if not isinstance(document, dict):
            document = {}
        self._figure_document = deepcopy(document)
        canvas = getattr(self, "_annotation_canvas", None)
        project = getattr(canvas, "set_document_objects", None)
        if not callable(project):
            return self._figure_document

        self._connect_annotation_canvas_edit_session()
        objects = document.get("objects", [])
        if not isinstance(objects, list):
            objects = []
        previous = False
        signals_blocked = getattr(canvas, "signalsBlocked", None)
        if callable(signals_blocked):
            previous = bool(signals_blocked())
        block_signals = getattr(canvas, "blockSignals", None)
        if callable(block_signals):
            block_signals(True)
        try:
            project(objects)
        finally:
            if callable(block_signals):
                block_signals(previous)
        return self._figure_document

    def _connect_annotation_canvas_edit_session(self):
        canvas = getattr(self, "_annotation_canvas", None)
        signal = getattr(canvas, "object_edit_requested", None)
        if signal is None or not callable(getattr(signal, "connect", None)):
            return False
        if getattr(self, "_annotation_edit_signal", None) is signal:
            return True
        signal.connect(self._on_annotation_object_edit_requested)
        self._annotation_edit_signal = signal
        return True

    def _connect_annotation_edit_session(self):
        return self._connect_annotation_canvas_edit_session()

    def _on_annotation_object_edit_requested(self, payload):
        object_id = self._payload_value(payload, "object_id", "id")
        source = self._payload_value(payload, "source")
        if not object_id:
            return None
        session = self._edit_session_for_adapter()
        if session is not None and callable(getattr(session, "select", None)):
            session.select(object_id, source)

        geometry = self._payload_value(payload, "geometry")
        style = self._payload_value(payload, "style")
        if isinstance(geometry, Mapping) and geometry:
            return self._execute_edit(UpdateGeometryCommand(object_id, dict(geometry)))
        if isinstance(style, Mapping) and style:
            return self._execute_edit(UpdateStyleCommand(object_id, dict(style)))
        return None

    def _edit_session_for_adapter(self):
        for name in ("_edit_session", "_figure_edit_session", "edit_session"):
            session = getattr(self, name, None)
            if session is not None:
                return session
        return None

    @staticmethod
    def _payload_value(payload, *names):
        if isinstance(payload, Mapping):
            for name in names:
                if name in payload:
                    value = payload[name]
                    return str(value).strip() if name in {"object_id", "id", "source"} else value
            return "" if names and names[0] in {"object_id", "id", "source"} else None
        for name in names:
            if hasattr(payload, name):
                value = getattr(payload, name)
                return str(value).strip() if name in {"object_id", "id", "source"} else value
        return "" if names and names[0] in {"object_id", "id", "source"} else None


__all__ = ["ChartEditorEditSessionMixin"]
