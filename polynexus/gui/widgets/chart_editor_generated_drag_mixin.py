from __future__ import annotations

from copy import deepcopy

from ...core.figure_edit_commands import ReplaceObjectCommand, UpdateGeometryCommand


class ChartEditorGeneratedDragMixin:
    def _commit_generated_drag_transaction(self, drag_state) -> bool:
        if not isinstance(drag_state, dict) or not drag_state.get("dirty"):
            return False
        object_id = str(drag_state.get("object_id", "") or "").strip()
        current = self._generated_figure_object_by_id(object_id)
        original = drag_state.get("original_object")
        if not object_id or not isinstance(current, dict) or not isinstance(original, dict):
            return False
        if current == original:
            return False
        session = getattr(self, "_edit_session", None)
        if session is None:
            session = getattr(self, "_edit_session_for_adapter", lambda: None)()
        if session is None:
            return False
        session.select(object_id, "generated-canvas")
        result = self._execute_edit(ReplaceObjectCommand(object_id, current))
        return bool(result is not None and result.changed)

    def _activate_generated_drag_state(self, drag_state, event=None):
        object_id = str(drag_state.get("object_id", "") or "")
        figure_object = self._generated_figure_object_by_id(object_id)
        if isinstance(figure_object, dict) and "original_object" not in drag_state:
            drag_state["original_object"] = deepcopy(figure_object)
        if event is not None and "press_pixels" not in drag_state:
            drag_state["press_pixels"] = (
                float(getattr(event, "x", 0.0) or 0.0),
                float(getattr(event, "y", 0.0) or 0.0),
            )
        session = self._edit_session_for_adapter()
        if session is not None and "history_length" not in drag_state:
            drag_state["history_length"] = len(session.history)
        drag_state.setdefault("activated", False)
        self._clear_generated_hover_highlight(redraw=False)
        self._generated_handle_drag_state = drag_state
        self._last_generated_pick_signature = None
        self._last_generated_pick_candidates = []
        self._set_generated_canvas_cursor(self._generated_hover_cursor_shape(drag_state))

    def _restore_generated_drag_snapshot(self, drag_state):
        if not isinstance(drag_state, dict):
            return False
        object_id = str(drag_state.get("object_id", "") or "")
        original_object = drag_state.get("original_object")
        return self._generated_store().replace(object_id, original_object)

    def _commit_generated_drag(self, drag_state):
        if not isinstance(drag_state, dict):
            return False
        drag_kind = str(drag_state.get("kind", "") or "")
        geometry_keys = {
            "line": ("x1", "y1", "x2", "y2"),
            "line-body": ("x1", "y1", "x2", "y2"),
            "curve": ("x1", "y1", "x2", "y2", "control_x", "control_y"),
            "rectangle": ("x", "y", "width", "height"),
        }.get(drag_kind)
        if geometry_keys is None:
            return True
        object_id = str(drag_state.get("object_id", "") or "")
        original_object = drag_state.get("original_object")
        current_object = self._generated_figure_object_by_id(object_id)
        if not object_id or not isinstance(original_object, dict) or not isinstance(
            current_object, dict
        ):
            return False
        current_geometry = (
            current_object.get("bounds", {})
            if isinstance(current_object.get("bounds"), dict)
            else current_object
        )
        original_geometry = (
            original_object.get("bounds", {})
            if isinstance(original_object.get("bounds"), dict)
            else original_object
        )
        updates = {
            key: deepcopy(current_geometry[key])
            for key in geometry_keys
            if key in current_geometry
            and current_geometry.get(key) != original_geometry.get(key)
        }
        session = self._edit_session_for_adapter()
        if session is None:
            return True
        history_length = int(drag_state.get("history_length", len(session.history)) or 0)
        while len(session.history) > history_length:
            undone = session.undo()
            if not undone.changed:
                return False
        if not updates:
            self._sync_editor_from_session()
            self._show_generated_figure_document()
            return True
        session.select(object_id, "generated-canvas")
        result = self._execute_edit(UpdateGeometryCommand(object_id, updates))
        if result is None or not result.changed:
            return False
        self._sync_generated_object_property_controls(object_id)
        self._show_generated_figure_document()
        return True

    def _cancel_generated_drag(self):
        drag_state = self._generated_handle_drag_state
        if not drag_state:
            return False
        self._generated_handle_drag_state = None
        session = self._edit_session_for_adapter()
        history_length = int(
            drag_state.get("history_length", len(session.history) if session else 0) or 0
        )
        restored = False
        if session is not None:
            while len(session.history) > history_length:
                undone = session.undo()
                if not undone.changed:
                    break
                restored = True
            if restored:
                self._sync_editor_from_session()
        if not restored:
            restored = self._restore_generated_drag_snapshot(drag_state)
        self._clear_generated_drag_status()
        self._clear_generated_hover_highlight(redraw=False)
        if restored:
            self._show_generated_figure_document()
            self._refresh_object_list(self._selected_figure_object_id)
            self._sync_generated_object_property_controls(self._selected_figure_object_id)
        if self._selected_figure_object_id:
            self._suppress_generated_hover_until_pointer_move = True
        if not self._refresh_generated_feedback_from_last_pointer():
            self._reset_generated_canvas_cursor()
        return True
