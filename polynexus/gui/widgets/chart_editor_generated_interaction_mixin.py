from __future__ import annotations

from uuid import uuid4

from PySide6.QtCore import Qt

from ...core.figure_edit_commands import AddObjectCommand
from ..i18n import tr


class ChartEditorGeneratedInteractionMixin:
    def _on_generated_button_press(self, event):
        if not self._generated_document_mode:
            return
        self._remember_generated_pointer_event(event)
        if not self._is_left_mouse_button(getattr(event, "button", None)):
            return
        if self._generated_draw_tool != "select":
            if self._handle_generated_draw_press(event):
                return
        candidate_ids = self._figure_render_adapter.object_ids_for_mouseevent(event)
        overlap_cycle_hint_active = bool(candidate_ids and len(candidate_ids) > 1)
        pick_already_handled = (
            self._generated_gui_event_id(event) == self._last_generated_pick_gui_event_id
            and self._last_generated_pick_gui_event_id is not None
        )
        selected_object_id = str(self._selected_figure_object_id or "")
        selected_line_handle_index_before_press = (
            self._selected_generated_line_handle_index
        )
        selected_plot_series_handle_index_before_press = (
            self._selected_generated_plot_series_handle_index
        )
        if selected_object_id:
            drag_state = self._generated_selected_handle_drag_state_for_press(
                event, selected_object_id
            )
            if drag_state is not None:
                drag_kind = str(drag_state.get("kind", "") or "")
                if drag_kind == "line":
                    self._set_selected_generated_line_handle_context(
                        selected_object_id,
                        drag_state.get("handle_index"),
                    )
                else:
                    self._clear_selected_generated_line_handle_context()
                if drag_kind == "plot_series":
                    self._set_selected_generated_plot_series_handle_context(
                        selected_object_id,
                        drag_state.get("handle_index"),
                    )
                    self._sync_generated_object_property_controls(selected_object_id)
                else:
                    self._clear_selected_generated_plot_series_handle_context()
                self._selection_cycle_hint_active = (
                    overlap_cycle_hint_active and selected_object_id in candidate_ids
                )
                if overlap_cycle_hint_active and selected_object_id in candidate_ids:
                    drag_state["overlap_candidate_ids"] = list(candidate_ids)
                drag_state["selected_before_press"] = selected_object_id
                drag_state["selected_line_handle_index_before_press"] = (
                    selected_line_handle_index_before_press
                )
                drag_state["selected_plot_series_handle_index_before_press"] = (
                    selected_plot_series_handle_index_before_press
                )
                self._suppress_generated_hover_until_pointer_move = True
                self._activate_generated_drag_state(drag_state, event)
                return
        press_target = self._generated_press_drag_target(event)
        if press_target is None:
            if candidate_ids and pick_already_handled:
                return
            if candidate_ids and self._generated_object_uses_select_only_press(
                candidate_ids[0]
            ):
                self._clear_selected_generated_line_handle_context()
                self._clear_selected_generated_plot_series_handle_context()
                selected_object_id = self._select_generated_object_from_candidates(
                    candidate_ids,
                    event,
                )
                self._suppress_generated_hover_until_pointer_move = bool(
                    selected_object_id
                )
                return
            if selected_object_id:
                self._selection_cycle_hint_active = False
                self._select_generated_object("", "canvas")
            return
        object_id, drag_state = press_target
        drag_kind = str(drag_state.get("kind", "") or "")
        if drag_kind == "line":
            self._set_selected_generated_line_handle_context(
                object_id,
                drag_state.get("handle_index"),
            )
        else:
            self._clear_selected_generated_line_handle_context()
        if drag_kind == "plot_series":
            self._set_selected_generated_plot_series_handle_context(
                object_id,
                drag_state.get("handle_index"),
            )
        else:
            self._clear_selected_generated_plot_series_handle_context()
        self._selection_cycle_hint_active = (
            overlap_cycle_hint_active and object_id in candidate_ids
        )
        if overlap_cycle_hint_active and object_id in candidate_ids:
            drag_state["overlap_candidate_ids"] = list(candidate_ids)
        drag_state["selected_before_press"] = selected_object_id
        drag_state["selected_line_handle_index_before_press"] = (
            selected_line_handle_index_before_press
        )
        drag_state["selected_plot_series_handle_index_before_press"] = (
            selected_plot_series_handle_index_before_press
        )
        self._select_generated_object(object_id, "canvas")
        self._suppress_generated_hover_until_pointer_move = True
        self._activate_generated_drag_state(drag_state, event)

    def _on_generated_button_release(self, event):
        self._remember_generated_pointer_event(event)
        if self._generated_draw_start_data is not None:
            self._finish_generated_draw(event)
            return
        drag_state = self._generated_handle_drag_state
        self._generated_handle_drag_state = None
        self._clear_generated_drag_status()
        selected_object_id = str(self._selected_figure_object_id or "")
        suppress_selected_self_feedback = bool(
            self._suppress_generated_hover_until_pointer_move and selected_object_id
        )
        if suppress_selected_self_feedback:
            self._clear_generated_hover_highlight(redraw=False)
            self._clear_generated_hover_status()
            if isinstance(drag_state, dict):
                self._set_generated_canvas_cursor(
                    self._generated_hover_cursor_shape(drag_state)
                )
            elif (
                selected_object_id
                and self._generated_object_uses_select_only_press(selected_object_id)
            ):
                self._set_generated_canvas_cursor(Qt.CursorShape.PointingHandCursor)
            else:
                self._reset_generated_canvas_cursor()
        else:
            self._update_generated_canvas_cursor(event)
        if self._cycle_generated_selection_after_click(drag_state):
            return
        if not drag_state or not drag_state.get("dirty"):
            if (
                isinstance(drag_state, dict)
                and str(drag_state.get("kind", "") or "") == "line"
            ):
                object_id = str(drag_state.get("object_id", "") or "")
                previous_index = drag_state.get(
                    "selected_line_handle_index_before_press"
                )
                current_index = None
                if str(self._selected_generated_line_object_id or "") == object_id:
                    current_index = self._selected_generated_line_handle_index
                if (
                    object_id
                    and object_id == selected_object_id
                    and current_index != previous_index
                ):
                    self._show_generated_figure_document()
            if (
                isinstance(drag_state, dict)
                and str(drag_state.get("kind", "") or "") == "plot_series"
            ):
                object_id = str(drag_state.get("object_id", "") or "")
                previous_index = drag_state.get(
                    "selected_plot_series_handle_index_before_press"
                )
                current_index = None
                if (
                    str(self._selected_generated_plot_series_object_id or "")
                    == object_id
                ):
                    current_index = self._selected_generated_plot_series_handle_index
                if (
                    object_id
                    and object_id == selected_object_id
                    and current_index != previous_index
                ):
                    self._show_generated_figure_document()
                    self._sync_generated_object_property_controls(object_id)
            return
        committed = self._commit_generated_drag_transaction(drag_state)
        self._persist_generated_document()
        if not committed:
            self._show_generated_figure_document()
            self.figure_changed.emit()

    def _on_generated_figure_leave(self, _event):
        self._last_generated_pointer_state = None
        self._last_generated_pointer_drag_target = None
        self._suppress_generated_hover_until_pointer_move = False
        if self._generated_handle_drag_state:
            return
        self._clear_generated_hover_highlight()
        self._reset_generated_canvas_cursor()

    def _handle_generated_draw_press(self, event):
        tool = str(getattr(self, "_generated_draw_tool", "select") or "select")
        data = self._generated_event_data_coordinates(event)
        if data is None:
            return False
        if tool == "text":
            text = self._annotation_text_edit.text().strip() or "Annotation"
            return self._add_generated_tool_object(
                tool,
                data,
                data,
                text=text,
            )
        if tool in {"line", "arrow", "rectangle"}:
            self._generated_draw_start_data = data
            self._status_label.setText(tr("EDITOR_DRAW_OBJECT_HINT"))
            return True
        return False

    def _finish_generated_draw(self, event):
        start = self._generated_draw_start_data
        self._generated_draw_start_data = None
        end = self._generated_event_data_coordinates(event)
        if start is None or end is None:
            self.set_tool("select")
            return
        if start == end:
            self.set_tool("select")
            return
        self._add_generated_tool_object(self._generated_draw_tool, start, end)

    def _add_generated_tool_object(self, tool, start, end, *, text=""):
        x1, y1 = (float(start[0]), float(start[1]))
        x2, y2 = (float(end[0]), float(end[1]))
        object_id = f"annotation-{uuid4().hex[:12]}"
        color = self._annotation_color_edit.text().strip() or "#D55E00"
        line_style = {
            "Solid": "-",
            "Dashed": "--",
            "Dotted": ":",
            "Dash Dot": "-.",
        }.get(self._annotation_line_style_combo.currentText(), "-")
        style = {
            "color": color,
            "line_width": float(self._annotation_line_width_spin.value()),
            "line_style": line_style,
            "alpha": float(self._annotation_alpha_spin.value()),
        }
        payload = {
            "id": object_id,
            "type": tool,
            "name": {
                "text": "Text",
                "line": "Line",
                "arrow": "Arrow",
                "rectangle": "Rectangle",
            }[tool],
            "visible": True,
            "locked": False,
            "z_index": 1000,
            "style": style,
        }
        panel_id = next(
            (
                str(item.get("panel_id") or "")
                for item in self._figure_document.get("objects", [])
                if isinstance(item, dict) and item.get("panel_id")
            ),
            "",
        )
        if panel_id:
            payload["panel_id"] = panel_id
        if tool == "text":
            payload.update(
                x=x1,
                y=y1,
                text=str(text or "Annotation"),
                style={
                    **style,
                    "font_size": float(self._annotation_font_size_spin.value()),
                },
            )
        elif tool in {"line", "arrow"}:
            payload.update(x1=x1, y1=y1, x2=x2, y2=y2)
        else:
            payload.update(
                x=min(x1, x2),
                y=min(y1, y2),
                width=abs(x2 - x1),
                height=abs(y2 - y1),
            )

        result = self._execute_edit(AddObjectCommand(payload))
        if result is None or not result.changed:
            return False
        self.set_tool("select")
        self._show_generated_figure_document()
        self._select_generated_object(object_id, "canvas")
        return True
