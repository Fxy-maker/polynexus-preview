from __future__ import annotations

from PySide6.QtCore import Qt


class ChartEditorGeneratedHoverMixin:
    def _set_generated_canvas_cursor(self, cursor_shape):
        if self._canvas is None:
            return
        try:
            self._canvas.setCursor(cursor_shape)
        except Exception:
            return

    def _reset_generated_canvas_cursor(self):
        if self._canvas is None:
            return
        try:
            self._canvas.unsetCursor()
        except Exception:
            return

    def _clear_generated_hover_highlight(self, redraw=True):
        changed = self._figure_render_adapter.clear_hover_highlight()
        changed = self._clear_generated_hover_preview_handle(redraw=False) or changed
        self._hovered_figure_object_id = ""
        self._clear_generated_hover_status()
        if changed and redraw and self._canvas is not None:
            self._canvas.draw_idle()

    def _set_generated_hover_object(self, object_id):
        object_id = str(object_id or "")
        selected_object_id = str(self._selected_figure_object_id or "")
        if not self._generated_document_mode or not object_id or object_id == selected_object_id:
            self._clear_generated_hover_highlight()
            return
        if object_id == self._hovered_figure_object_id:
            return
        artists = self._figure_render_adapter.artists_for_object_id(object_id)
        self._clear_generated_hover_highlight(redraw=False)
        if not artists:
            self._canvas.draw_idle()
            return
        self._figure_render_adapter.highlight_hover(artists)
        self._hovered_figure_object_id = object_id
        self._canvas.draw_idle()

    def _clear_generated_hover_preview_handle(self, redraw=True):
        changed = False
        hover_handle_artist = self._generated_hover_handle_artist()
        if hover_handle_artist is not None:
            try:
                hover_handle_artist.remove()
                changed = True
            except Exception:
                pass
        self._hover_preview_figure_object_id = ""
        self._hover_preview_handle_index = None
        if changed and redraw and self._canvas is not None:
            self._canvas.draw_idle()
        return changed

    def _set_generated_hover_preview_handle(self, object_id, drag_state):
        object_id = str(object_id or "")
        kind = str(drag_state.get("kind", "") or "") if isinstance(drag_state, dict) else ""
        if (
            not self._generated_document_mode
            or not object_id
            or not isinstance(drag_state, dict)
            or kind not in {"plot_series", "line"}
            or self._figure is None
            or not self._figure.axes
        ):
            self._clear_generated_hover_preview_handle(redraw=False)
            return
        figure_object = self._generated_figure_object_by_id(object_id)
        if not isinstance(figure_object, dict):
            self._clear_generated_hover_preview_handle(redraw=False)
            return
        try:
            handle_index = int(drag_state.get("handle_index"))
        except (TypeError, ValueError):
            self._clear_generated_hover_preview_handle(redraw=False)
            return
        preview_x = None
        preview_y = None
        if kind == "plot_series":
            chart_kind = str(figure_object.get("chart_kind", "") or "")
            if chart_kind in {"heatmap", "bar", "barh", "image_grid"}:
                self._clear_generated_hover_preview_handle(redraw=False)
                return
            x_values, y_values = self._generated_object_xy(figure_object, {})
            if (
                handle_index < 0
                or handle_index >= min(len(x_values), len(y_values))
                or not x_values
                or not y_values
            ):
                self._clear_generated_hover_preview_handle(redraw=False)
                return
            preview_x = float(x_values[handle_index])
            preview_y = float(y_values[handle_index])
        else:
            line_artist = self._generated_line_artist(object_id)
            if line_artist is None:
                self._clear_generated_hover_preview_handle(redraw=False)
                return
            try:
                x_values = list(line_artist.get_xdata())
                y_values = list(line_artist.get_ydata())
            except Exception:
                self._clear_generated_hover_preview_handle(redraw=False)
                return
            if handle_index < 0 or handle_index >= min(len(x_values), len(y_values), 2):
                self._clear_generated_hover_preview_handle(redraw=False)
                return
            x_value = self._optional_float(x_values[handle_index])
            y_value = self._optional_float(y_values[handle_index])
            if x_value is None or y_value is None:
                self._clear_generated_hover_preview_handle(redraw=False)
                return
            preview_x = float(x_value)
            preview_y = float(y_value)
        hover_handle_artist = self._generated_hover_handle_artist()
        if (
            hover_handle_artist is not None
            and self._hover_preview_figure_object_id == object_id
            and self._hover_preview_handle_index == handle_index
        ):
            hover_handle_artist.set_offsets([[preview_x, preview_y]])
            return
        self._clear_generated_hover_preview_handle(redraw=False)
        hover_handle_artist = self._figure.axes[0].scatter(
            [preview_x],
            [preview_y],
            s=76,
            facecolors="none",
            edgecolors="#D55E00",
            linewidths=1.8,
            alpha=0.78,
            zorder=10_001,
        )
        hover_handle_artist.set_gid(f"pn-hover-handle:{object_id}")
        self._hover_preview_figure_object_id = object_id
        self._hover_preview_handle_index = handle_index
        self._canvas.draw_idle()

    def _update_generated_canvas_cursor(self, event):
        if self._generated_handle_drag_state:
            self._set_generated_canvas_cursor(Qt.CursorShape.ClosedHandCursor)
            return
        if not self._generated_document_mode:
            self._last_generated_pointer_drag_target = None
            self._clear_generated_hover_highlight()
            self._reset_generated_canvas_cursor()
            return
        drag_target = self._generated_press_drag_target(event)
        if drag_target is None:
            candidate_ids = self._figure_render_adapter.object_ids_for_mouseevent(event)
            if candidate_ids and self._generated_object_uses_select_only_press(candidate_ids[0]):
                object_id = str(candidate_ids[0] or "")
                hover_state = {"kind": "select"}
                self._last_generated_pointer_drag_target = (object_id, dict(hover_state))
                self._set_generated_hover_object(object_id)
                self._set_generated_hover_preview_handle(object_id, hover_state)
                self._set_generated_hover_status(object_id, hover_state)
                self._set_generated_canvas_cursor(
                    self._generated_hover_cursor_shape(hover_state)
                )
                return
            self._last_generated_pointer_drag_target = None
            self._clear_generated_hover_highlight()
            self._reset_generated_canvas_cursor()
            return
        object_id, drag_state = drag_target
        self._last_generated_pointer_drag_target = (str(object_id or ""), dict(drag_state))
        self._set_generated_hover_object(object_id)
        self._set_generated_hover_preview_handle(object_id, drag_state)
        self._set_generated_hover_status(object_id, drag_state)
        self._set_generated_canvas_cursor(self._generated_hover_cursor_shape(drag_state))
