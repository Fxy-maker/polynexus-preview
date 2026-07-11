from __future__ import annotations

from copy import deepcopy


class ChartEditorGeneratedDragMixin:
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

    def _cancel_generated_drag(self):
        drag_state = self._generated_handle_drag_state
        if not drag_state:
            return False
        self._generated_handle_drag_state = None
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
