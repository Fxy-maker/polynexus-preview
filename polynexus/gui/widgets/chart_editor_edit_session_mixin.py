"""Qt-independent adapters between chart-editor widgets and an edit session."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy

from ...core.figure_edit_commands import UpdateGeometryCommand, UpdateStyleCommand
from ...core.figure_edit_session import EditSession
from ...core.figure_edit_capabilities import EditResult, capabilities_for


class ChartEditorEditSessionMixin:
    """Route widget proposals through the shared, undoable edit session."""

    def set_tool(self, tool):
        canvas = getattr(self, "_annotation_canvas", None)
        setter = getattr(canvas, "set_tool", None)
        return bool(setter(tool)) if callable(setter) else False

    def _reset_edit_session_from_document(self, document=None):
        payload = document if isinstance(document, dict) else {}
        self._edit_session = EditSession(payload)
        self._last_edit_result = EditResult(False)
        self._connect_annotation_canvas_edit_session()
        return self._edit_session

    def _selected_canonical_object(self):
        session = self._edit_session_for_adapter()
        object_id = ""
        if session is not None:
            object_id = str(getattr(session.selection, "object_id", "") or "")
        if not object_id:
            object_id = str(getattr(self, "_selected_figure_object_id", "") or "")
        if not object_id:
            canvas = getattr(self, "_annotation_canvas", None)
            object_id = str(getattr(canvas, "selected_annotation_id", lambda: "")() or "")
        if not object_id and not getattr(self, "_generated_document_mode", False):
            object_id = "background"
        document = getattr(self, "_figure_document", {})
        objects = document.get("objects", []) if isinstance(document, dict) else []
        return next(
            (
                object_payload
                for object_payload in objects
                if isinstance(object_payload, dict)
                and str(object_payload.get("id", "") or "") == object_id
            ),
            None,
        )

    def _sync_inspector_capabilities(self):
        object_payload = self._selected_canonical_object()
        capabilities = capabilities_for(object_payload or {})
        set_style = getattr(self, "_set_style_controls_enabled", None)
        if callable(set_style):
            set_style(
                capabilities.font_size,
                capabilities.line_width,
                capabilities.style,
                color_enabled=capabilities.color,
                line_style_enabled=capabilities.line_style,
                marker_enabled=capabilities.marker,
                marker_size_enabled=capabilities.marker_size,
            )
        set_geometry = getattr(self, "_set_geometry_controls_enabled", None)
        if callable(set_geometry):
            set_geometry(capabilities.geometry, capabilities.geometry)
        for name in ("_annotation_text_edit", "_btn_annotation_update_text"):
            control = getattr(self, name, None)
            if control is not None:
                control.setEnabled(capabilities.text)
        return capabilities

    def _execute_edit(self, command):
        session = self._edit_session_for_adapter()
        if session is None:
            return None
        result = session.execute(command)
        return self._project_edit_result(result)

    def _project_edit_result(self, result):
        self._last_edit_result = result
        if getattr(result, "changed", False):
            self._sync_editor_from_session()
            set_dirty = getattr(self, "_set_editor_dirty", None)
            if callable(set_dirty):
                set_dirty(True)
            figure_changed = getattr(self, "figure_changed", None)
            if figure_changed is not None:
                figure_changed.emit()
        status_label = getattr(self, "_status_label", None)
        if status_label is not None:
            message = getattr(result, "message", "") or getattr(result, "error_code", "")
            if getattr(result, "error_code", "") == "invalid_color":
                message = f"Invalid color: {message}"
            if message:
                status_label.setText(str(message))
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
        if getattr(self, "_generated_document_mode", False):
            render_document = getattr(self, "_show_generated_figure_document", None)
            if callable(render_document):
                render_document()
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
