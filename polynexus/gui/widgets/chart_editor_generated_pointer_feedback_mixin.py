from __future__ import annotations

from matplotlib.backend_bases import MouseEvent


class ChartEditorGeneratedPointerFeedbackMixin:
    def _remember_generated_pointer_event(self, event):
        mouseevent = getattr(event, "mouseevent", event)
        event_x = self._optional_float(getattr(mouseevent, "x", None))
        event_y = self._optional_float(getattr(mouseevent, "y", None))
        if event_x is None or event_y is None:
            return
        axes_index = None
        axes = getattr(mouseevent, "inaxes", None)
        if axes is not None and self._figure is not None and axes in self._figure.axes:
            axes_index = self._figure.axes.index(axes)
        self._last_generated_pointer_state = (
            float(event_x),
            float(event_y),
            axes_index,
        )

    def _refresh_generated_feedback_from_last_pointer(self):
        if not self._generated_document_mode or self._canvas is None:
            return False
        pointer_state = self._last_generated_pointer_state
        if not isinstance(pointer_state, (list, tuple)) or len(pointer_state) < 3:
            return False
        remembered_drag_target = self._last_generated_pointer_drag_target
        event_x = self._optional_float(pointer_state[0])
        event_y = self._optional_float(pointer_state[1])
        if event_x is None or event_y is None:
            return False
        refresh_event = MouseEvent(
            "motion_notify_event",
            self._canvas,
            float(event_x),
            float(event_y),
        )
        axes_index = pointer_state[2]
        if (
            axes_index is not None
            and self._figure is not None
            and 0 <= int(axes_index) < len(self._figure.axes)
        ):
            refresh_event.inaxes = self._figure.axes[int(axes_index)]
        else:
            refresh_event.inaxes = None
        self._update_generated_canvas_cursor(refresh_event)
        if (
            not self._selected_figure_object_id
            and not self._hovered_figure_object_id
            and isinstance(remembered_drag_target, (list, tuple))
            and len(remembered_drag_target) == 2
        ):
            object_id = str(remembered_drag_target[0] or "")
            drag_state = remembered_drag_target[1]
            if object_id and isinstance(drag_state, dict):
                self._set_generated_hover_object(object_id)
                self._set_generated_hover_status(object_id, drag_state)
                self._set_generated_canvas_cursor(
                    self._generated_hover_cursor_shape(drag_state)
                )
        return True
