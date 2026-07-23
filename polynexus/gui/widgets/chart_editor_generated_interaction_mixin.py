from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

from PySide6.QtCore import QRect, Qt

from ...core.figure_edit_commands import AddObjectCommand
from ...core.figures.renderer import MatplotlibFigureRenderer
from ...core.figure_text_geometry import clamp_axes_box
from ..i18n import tr
from .editor_geometry import Box


class ChartEditorGeneratedInteractionMixin:
    def _on_generated_button_press(self, event):
        if not self._generated_document_mode:
            return
        self._remember_generated_pointer_event(event)
        if not self._is_left_mouse_button(getattr(event, "button", None)):
            return
        if (
            bool(getattr(event, "dblclick", False))
            and self._generated_draw_tool == "select"
        ):
            legend_object_id = self._generated_legend_edit_target(event)
            if legend_object_id:
                self._select_generated_object(legend_object_id, "double-click")
                if self._begin_generated_legend_name_edit(legend_object_id):
                    self._suppress_generated_hover_until_pointer_move = False
                    return
            object_id = self._generated_text_edit_target(event)
            if object_id:
                self._select_generated_object(object_id, "double-click")
                if self._begin_generated_text_edit(object_id):
                    self._suppress_generated_hover_until_pointer_move = False
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
            else:
                # Keep the inspector aligned with the background row when the
                # user clicks empty canvas space without an active object.
                self._selected_object_label.setText(tr("EDITOR_OBJECT_BACKGROUND"))
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
        controller = getattr(self, "_interaction_controller", None)
        if controller is not None and drag_state:
            controller.finish_drag()
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
        drag_kind = str(drag_state.get("kind", "") or "")
        if drag_kind in {
            "line",
            "line-body",
            "curve",
            "rectangle",
            "text",
            "body",
            "plot_series",
            "legend",
        }:
            committed = self._commit_generated_drag(drag_state)
        else:
            committed = self._commit_generated_drag_transaction(drag_state)
        if not committed:
            self._restore_generated_drag_snapshot(drag_state)
            self._clear_generated_drag_preview()
            self._show_generated_figure_document()
            self._generated_viewport_snapshot = None
            return
        self._persist_generated_document()
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
        data = (
            self._generated_event_axes_fraction(event)
            if tool == "text"
            else self._generated_event_data_coordinates(event)
        )
        if data is None:
            return False
        controller = getattr(self, "_interaction_controller", None)
        if controller is not None:
            transition = controller.begin_create(data)
            if not transition.accepted:
                return False
        if tool == "text":
            self._generated_draw_start_data = data
            self._generated_draw_start_display = (
                float(getattr(event, "x", 0.0) or 0.0),
                float(getattr(event, "y", 0.0) or 0.0),
            )
            self._begin_generated_draw_preview(data, self._generated_draw_start_display)
            self._status_label.setText(tr("EDITOR_DRAW_TEXT_HINT"))
            return True
        if tool in {"line", "arrow", "curve", "rectangle"}:
            self._generated_draw_start_data = data
            self._begin_generated_draw_preview(data)
            self._status_label.setText(tr("EDITOR_DRAW_OBJECT_HINT"))
            return True
        return False

    def _finish_generated_draw(self, event):
        start = self._generated_draw_start_data
        self._generated_draw_start_data = None
        start_display = self._generated_draw_start_display
        self._generated_draw_start_display = None
        end = (
            self._generated_event_axes_fraction(event)
            if self._generated_draw_tool == "text"
            else self._generated_event_data_coordinates(event)
        )
        controller = getattr(self, "_interaction_controller", None)
        if controller is not None:
            controller.finish_create(end) if end is not None else controller.cancel()
        box = Box.from_drag(start, end) if start is not None and end is not None else None
        if start is None or end is None or box is None:
            self._clear_generated_draw_preview()
            self._generated_viewport_snapshot = None
            self.set_tool("select")
            return
        self._clear_generated_draw_preview(redraw=False)
        if self._generated_draw_tool == "text":
            self._select_generated_object("", "text-entry")
            self.set_tool("select")
            self._begin_generated_text_box(
                box,
                rect=self._generated_canvas_rect(start_display, event),
            )
            return
        if start == end:
            self._generated_viewport_snapshot = None
            self.set_tool("select")
            return
        self._add_generated_tool_object(self._generated_draw_tool, start, end)

    def _generated_canvas_rect(self, start_display, event) -> QRect:
        device_ratio = self._generated_canvas_device_ratio()
        start_x, start_y = start_display or (0.0, 0.0)
        start_x = float(start_x) / device_ratio
        start_y = float(start_y) / device_ratio
        end_x = float(getattr(event, "x", start_x * device_ratio) or start_x * device_ratio)
        end_y = float(getattr(event, "y", start_y * device_ratio) or start_y * device_ratio)
        end_x /= device_ratio
        end_y /= device_ratio
        left = int(round(min(start_x, end_x)))
        right = int(round(max(start_x, end_x)))
        canvas_height = max(1, int(self._canvas.height()))
        top = canvas_height - int(round(max(start_y, end_y)))
        bottom = canvas_height - int(round(min(start_y, end_y)))
        return QRect(left, top, max(1, right - left), max(1, bottom - top))

    def _generated_canvas_device_ratio(self) -> float:
        """Return the device-to-Qt-pixel ratio used by Matplotlib mouse events."""
        canvas = getattr(self, "_canvas", None)
        try:
            ratio = float(canvas.devicePixelRatioF()) if canvas is not None else 1.0
        except (AttributeError, TypeError, ValueError):
            ratio = 1.0
        return max(1.0, ratio)

    def _generated_text_edit_target(self, event) -> str:
        candidate_ids = []
        selected_id = str(self._selected_figure_object_id or "")
        if selected_id:
            candidate_ids.append(selected_id)
        candidate_ids.extend(self._figure_render_adapter.object_ids_for_mouseevent(event))
        candidate_ids.extend(self._generated_press_drag_object_ids())
        seen = set()
        for object_id in candidate_ids:
            object_id = str(object_id or "")
            if not object_id or object_id in seen:
                continue
            seen.add(object_id)
            figure_object = self._generated_figure_object_by_id(object_id)
            if not isinstance(figure_object, dict) or figure_object.get("type") != "text":
                continue
            if self._generated_annotation_body_drag_start(event, object_id) is not None:
                return object_id
        return ""

    def _generated_legend_edit_target(self, event) -> str:
        candidate_ids = []
        selected_id = str(self._selected_figure_object_id or "")
        if selected_id:
            candidate_ids.append(selected_id)
        candidate_ids.extend(self._figure_render_adapter.object_ids_for_mouseevent(event))
        candidate_ids.extend(self._generated_press_drag_object_ids())
        seen = set()
        for object_id in candidate_ids:
            object_id = str(object_id or "")
            if not object_id or object_id in seen:
                continue
            seen.add(object_id)
            figure_object = self._generated_figure_object_by_id(object_id)
            if (
                isinstance(figure_object, dict)
                and figure_object.get("type") == "legend"
                and self._generated_legend_drag_start(event, object_id) is not None
            ):
                return object_id
        return ""

    def _generated_legend_series(self, legend_object_id: str) -> list[dict]:
        legend = self._generated_figure_object_by_id(legend_object_id)
        if not isinstance(legend, dict) or legend.get("type") != "legend":
            return []
        legend_panel_id = str(legend.get("panel_id") or "")
        panel_ids = {
            str(figure_object.get("panel_id") or "")
            for figure_object in self._figure_document.get("objects", [])
            if isinstance(figure_object, dict)
            and figure_object.get("type") == "plot_series"
        }
        return [
            {
                "id": str(figure_object.get("id") or ""),
                "name": str(figure_object.get("name") or ""),
            }
            for figure_object in self._figure_document.get("objects", [])
            if isinstance(figure_object, dict)
            and figure_object.get("type") == "plot_series"
            and figure_object.get("visible", True) is not False
            and figure_object.get("deleted") is not True
            and str(figure_object.get("name") or "").strip()
            and (
                str(figure_object.get("panel_id") or "") == legend_panel_id
                if legend_panel_id or len(panel_ids) > 1
                else True
            )
        ]

    def _begin_generated_legend_name_edit(self, legend_object_id: str) -> bool:
        series = self._generated_legend_series(legend_object_id)
        if not series:
            return False
        from .chart_editor_legend_dialog import LegendSeriesNameDialog

        dialog = LegendSeriesNameDialog(series, self)
        dialog.accepted.connect(
            lambda: self._commit_generated_legend_series_names(series, dialog.names())
        )
        dialog.finished.connect(self._clear_generated_legend_name_dialog)
        self._active_legend_name_dialog = dialog
        dialog.open()
        return True

    def _clear_generated_legend_name_dialog(self, _result=0) -> None:
        self._active_legend_name_dialog = None

    def _commit_generated_legend_series_names(self, series, names) -> bool:
        updated_document = deepcopy(self._figure_document)
        objects = updated_document.get("objects", [])
        if not isinstance(objects, list):
            return False
        updates = {
            str(series[index].get("id") or ""): str(name or "").strip()
            for index, name in enumerate(names)
            if index < len(series) and str(name or "").strip()
        }
        changed = False
        for figure_object in objects:
            object_id = (
                str(figure_object.get("id") or "")
                if isinstance(figure_object, dict)
                else ""
            )
            name = updates.get(object_id)
            if name and isinstance(figure_object, dict) and figure_object.get("name") != name:
                figure_object["name"] = name
                changed = True
        if not changed:
            return False
        result = self._execute_edit(self._replace_document_command()(updated_document))
        if result is None or not getattr(result, "changed", False):
            return False
        self._persist_generated_document()
        self._show_generated_figure_document()
        self._refresh_object_list(self._selected_figure_object_id)
        return True

    def _begin_generated_text_edit(self, object_id: str) -> bool:
        figure_object = self._generated_figure_object_by_id(object_id)
        if not isinstance(figure_object, dict) or figure_object.get("type") != "text":
            return False
        renderer = None
        try:
            renderer = self._canvas.get_renderer()
        except (AttributeError, RuntimeError):
            renderer = None
        if renderer is None:
            return False
        artist = next(
            (
                item
                for item in self._figure_render_adapter.artists_for_object_id(object_id)
                if hasattr(item, "get_window_extent")
            ),
            None,
        )
        if artist is None:
            return False
        try:
            extent = artist.get_window_extent(renderer)
            ratio = self._generated_canvas_device_ratio()
            canvas_height = max(1, int(self._canvas.height()))
            left = int(round(float(extent.x0) / ratio))
            right = int(round(float(extent.x1) / ratio))
            top = canvas_height - int(round(float(extent.y1) / ratio))
            bottom = canvas_height - int(round(float(extent.y0) / ratio))
            rect = QRect(
                left,
                top,
                max(1, right - left),
                max(1, bottom - top),
            )
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return False
        self._begin_inline_text_entry(
            {
                "mode": "generated-edit",
                "object_id": str(object_id),
                "initial_text": str(figure_object.get("text", "") or ""),
            },
            host=self._canvas,
            rect=rect,
        )
        return isinstance(getattr(self, "_pending_inline_text", None), dict)

    def _begin_generated_text_box(self, start, end=None, rect: QRect | None = None) -> None:
        box = start if isinstance(start, Box) else Box.from_drag(start, end)
        if box is None or rect is None:
            return
        geometry = box.to_payload()
        self._begin_inline_text_entry(
            {
                "mode": "generated",
                "type": "text",
                "coordinate_space": "axes",
                "geometry": geometry,
            },
            host=self._canvas,
            rect=rect,
        )

    def _commit_generated_text_payload(self, payload: dict, text: str) -> bool:
        geometry = payload.get("geometry")
        if not isinstance(geometry, dict):
            return False
        x = float(geometry.get("x", 0.0) or 0.0)
        y = float(geometry.get("y", 0.0) or 0.0)
        width = float(geometry.get("width", 0.0) or 0.0)
        height = float(geometry.get("height", 0.0) or 0.0)
        if payload.get("coordinate_space") == "axes":
            geometry = clamp_axes_box(x, y, width, height)
            x = geometry["x"]
            y = geometry["y"]
            width = geometry["width"]
            height = geometry["height"]
        return self._add_generated_tool_object(
            "text",
            (x, y),
            (x + width, y + height),
            text=text,
        )

    def _add_generated_tool_object(self, tool, start, end, *, text=""):
        if not MatplotlibFigureRenderer.supports_object_type(tool):
            self._status_label.setText(tr("EDITOR_STATUS_UNSUPPORTED_OBJECT", tool))
            self.set_tool("select")
            self._generated_viewport_snapshot = None
            return False
        x1, y1 = (float(start[0]), float(start[1]))
        x2, y2 = (float(end[0]), float(end[1]))
        object_id = f"annotation-{uuid4().hex[:12]}"
        draw_style = self._active_draw_style()
        color = str(draw_style.get("color", "#D55E00") or "#D55E00")
        style = {
            "color": color,
            "line_width": float(draw_style.get("line_width", 2.0) or 2.0),
            "line_style": str(draw_style.get("line_style", "-") or "-"),
            "alpha": float(draw_style.get("alpha", 1.0) or 1.0),
        }
        payload = {
            "id": object_id,
            "type": tool,
            "name": {
                "text": "Text",
                "line": "Line",
                "arrow": "Arrow",
                "curve": "Curve",
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
                    "font_size": float(draw_style.get("font_size", 12.0) or 12.0),
                },
            )
            if all(0.0 <= value <= 1.0 for value in (x1, y1, x2, y2)):
                payload["coordinate_space"] = "axes"
            payload["bounds"] = {
                "x": x1,
                "y": y1,
                "width": abs(x2 - x1),
                "height": abs(y2 - y1),
            }
            if abs(x2 - x1) > 0 and abs(y2 - y1) > 0:
                payload["width"] = abs(x2 - x1)
                payload["height"] = abs(y2 - y1)
        elif tool in {"line", "arrow"}:
            payload.update(x1=x1, y1=y1, x2=x2, y2=y2)
        elif tool == "curve":
            control_x, control_y = self._generated_curve_control_point((x1, y1), (x2, y2))
            payload.update(
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
                control_x=control_x,
                control_y=control_y,
            )
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
        self._select_generated_object(object_id, "canvas")
        self._generated_viewport_snapshot = None
        return True
