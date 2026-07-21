from __future__ import annotations

from PySide6.QtCore import Qt

GENERATED_DRAG_START_THRESHOLD_PX = 3.0


class ChartEditorGeneratedDragExecutionMixin:
    def _generated_drag_motion_exceeded_threshold(self, drag_state, event):
        if not isinstance(drag_state, dict):
            return False
        press_pixels = drag_state.get("press_pixels")
        if not isinstance(press_pixels, (list, tuple)) or len(press_pixels) < 2:
            return True
        press_x = self._optional_float(press_pixels[0])
        press_y = self._optional_float(press_pixels[1])
        event_x = self._optional_float(getattr(event, "x", None))
        event_y = self._optional_float(getattr(event, "y", None))
        if press_x is None or press_y is None or event_x is None or event_y is None:
            return True
        dx = float(event_x) - float(press_x)
        dy = float(event_y) - float(press_y)
        return dx * dx + dy * dy >= float(GENERATED_DRAG_START_THRESHOLD_PX) ** 2

    def _on_generated_mouse_move(self, event):
        self._remember_generated_pointer_event(event)
        drag_state = self._generated_handle_drag_state
        if not drag_state:
            draw_start = getattr(self, "_generated_draw_start_data", None)
            if draw_start is not None:
                end = self._generated_event_data_coordinates(event)
                if end is not None:
                    controller = getattr(self, "_interaction_controller", None)
                    if controller is not None:
                        controller.update_create(end)
                    self._update_generated_draw_preview(
                        str(getattr(self, "_generated_draw_tool", "select") or "select"),
                        draw_start,
                        end,
                    )
                return
            self._suppress_generated_hover_until_pointer_move = False
            self._update_generated_canvas_cursor(event)
            return
        if not self._generated_document_mode:
            self._generated_handle_drag_state = None
            self._clear_generated_drag_status()
            self._reset_generated_canvas_cursor()
            return
        self._set_generated_canvas_cursor(Qt.CursorShape.ClosedHandCursor)
        object_id = str(drag_state.get("object_id", "") or "")
        figure_object = self._generated_figure_object_by_id(object_id)
        object_type = str(figure_object.get("type", "") or "") if figure_object else ""
        if not figure_object:
            self._generated_handle_drag_state = None
            self._clear_generated_drag_status()
            self._reset_generated_canvas_cursor()
            return
        if not drag_state.get("activated"):
            if not self._generated_drag_motion_exceeded_threshold(drag_state, event):
                self._set_generated_canvas_cursor(
                    self._generated_hover_cursor_shape(drag_state)
                )
                return
            drag_state["activated"] = True
        drag_state["current_pixels"] = (
            float(getattr(event, "x", 0.0) or 0.0),
            float(getattr(event, "y", 0.0) or 0.0),
        )
        controller = getattr(self, "_interaction_controller", None)
        if controller is not None:
            controller.update_drag(drag_state["current_pixels"])
        drag_kind = str(drag_state.get("kind", "") or object_type)
        self._set_generated_canvas_cursor(Qt.CursorShape.ClosedHandCursor)
        session = getattr(self, "_edit_session", None)
        if session is not None:
            self._edit_session = None
        try:
            if drag_kind == "line":
                coordinates = self._generated_event_data_coordinates(event)
                if coordinates is None:
                    return
                x_value, y_value = coordinates
                handle_index = int(drag_state.get("handle_index", 0) or 0)
                changed = self._apply_generated_line_handle_drag(
                    object_id, handle_index, x_value, y_value
                )
            elif drag_kind == "curve":
                coordinates = self._generated_event_data_coordinates(event)
                if coordinates is None:
                    return
                x_value, y_value = coordinates
                changed = self._apply_generated_curve_handle_drag(
                    object_id,
                    int(drag_state.get("handle_index", 0) or 0),
                    x_value,
                    y_value,
                )
            elif drag_kind == "rectangle":
                coordinates = self._generated_event_data_coordinates(event)
                if coordinates is None:
                    return
                x_value, y_value = coordinates
                changed = self._apply_generated_rectangle_handle_drag(
                    object_id,
                    int(drag_state.get("handle_index", 0) or 0),
                    x_value,
                    y_value,
                    preview=True,
                )
            elif drag_kind == "text":
                coordinates = self._generated_event_data_coordinates(event)
                if coordinates is None:
                    return
                x_value, y_value = coordinates
                changed = self._apply_generated_text_handle_drag(
                    object_id,
                    int(drag_state.get("handle_index", 0) or 0),
                    x_value,
                    y_value,
                )
            elif drag_kind == "line-body":
                coordinates = self._generated_event_data_coordinates(event)
                if coordinates is None:
                    return
                x_value, y_value = coordinates
                changed = self._apply_generated_line_body_drag(
                    object_id, drag_state, x_value, y_value
                )
            elif drag_kind == "body":
                coordinates = self._generated_event_data_coordinates(event)
                if coordinates is None:
                    return
                x_value, y_value = coordinates
                changed = self._apply_generated_body_drag(
                    object_id, drag_state, x_value, y_value
                )
            elif drag_kind == "plot_series":
                coordinates = self._generated_event_data_coordinates(event)
                if coordinates is None:
                    return
                x_value, y_value = coordinates
                handle_index = int(drag_state.get("handle_index", 0) or 0)
                changed = self._apply_generated_plot_series_handle_drag(
                    object_id, handle_index, x_value, y_value
                )
            elif object_type == "legend":
                axes_fraction = self._generated_event_axes_fraction(event)
                if axes_fraction is None:
                    self._set_generated_canvas_cursor(Qt.CursorShape.ClosedHandCursor)
                    return
                offset_x, offset_y = drag_state.get("grab_offset_axes", (0.0, 0.0))
                changed = self._apply_generated_legend_drag(
                    object_id,
                    float(axes_fraction[0]) - float(offset_x),
                    float(axes_fraction[1]) - float(offset_y),
                )
            else:
                self._generated_handle_drag_state = None
                self._clear_generated_drag_status()
                self._reset_generated_canvas_cursor()
                return
        finally:
            if session is not None:
                self._edit_session = session
        if not changed:
            return
        self._set_generated_drag_status(object_id, drag_state)
        drag_state["dirty"] = True
