from __future__ import annotations

from uuid import uuid4

from PySide6.QtCore import QPointF, QRect

from ...core.figure_document import annotation_to_figure_object
from ...core.figure_edit_capabilities import capabilities_for
from ...core.figure_text_geometry import clamp_axes_box, is_axes_text_box
from ...core.figure_edit_commands import (
    AddObjectCommand,
    DeleteObjectCommand,
    SetLockCommand,
    UpdateGeometryCommand,
    UpdateStyleCommand,
    UpdateTextCommand,
)
from ..chart_editor_generated_helpers import (
    annotation_line_style_value as _shared_annotation_line_style_value,
    annotation_marker_value as _shared_annotation_marker_value,
    generated_plot_series_marker_value as _shared_generated_plot_series_marker_value,
    line_style_label_for_value as _shared_line_style_label_for_value,
    marker_label_for_value as _shared_marker_label_for_value,
)
from ..chart_editor_generated_object_helpers import (
    generated_object_capabilities as _shared_generated_object_capabilities,
    generated_object_geometry_config as _shared_generated_object_geometry_config,
)
from ..i18n import tr

LINE_STYLE_OPTIONS = {
    "Solid": "-",
    "Dashed": "--",
    "Dotted": ":",
    "Dash Dot": "-.",
}

MARKER_OPTIONS = {
    "None": "",
    "Circle": "o",
    "Square": "s",
    "Triangle": "^",
    "Diamond": "D",
    "Plus": "+",
    "Cross": "x",
}


class ChartEditorAnnotationControlsMixin:
    def _on_annotation_object_create_requested(self, payload):
        if self._annotation_canvas is None or not isinstance(payload, dict):
            return False
        kind = str(payload.get("type", "") or "")
        geometry = payload.get("geometry")
        if kind not in {"line", "arrow", "curve", "rectangle", "highlight"} or not isinstance(
            geometry, dict
        ):
            return False
        annotation_id = f"ann-{uuid4().hex[:12]}"
        style = self._active_draw_style()
        object_payload = annotation_to_figure_object(
            {"id": annotation_id, "type": kind, **geometry, **style}
        )
        session = self._edit_session_for_adapter()
        if session is None:
            return False
        result = self._execute_edit(AddObjectCommand(object_payload))
        if result is None or not result.changed:
            return False
        session.select(annotation_id, "annotation_canvas")
        self._annotation_canvas.select_annotation(annotation_id)
        self._refresh_object_list(annotation_id)
        return True

    def _on_annotation_text_entry_requested(self, payload):
        if self._annotation_canvas is None or not isinstance(payload, dict):
            return
        geometry = payload.get("geometry")
        if not isinstance(geometry, dict):
            return
        canvas = self._annotation_canvas
        x = float(geometry.get("x", 0.0) or 0.0) * canvas._image_width
        y = float(geometry.get("y", 0.0) or 0.0) * canvas._image_height
        width = float(geometry.get("width", 0.0) or 0.0) * canvas._image_width
        height = float(geometry.get("height", 0.0) or 0.0) * canvas._image_height
        start = canvas._view.mapFromScene(QPointF(x, y))
        end = canvas._view.mapFromScene(QPointF(x + width, y + height))
        self._begin_inline_text_entry(
            {"mode": "static", **payload},
            host=canvas._view.viewport(),
            rect=QRect(start, end).normalized(),
        )

    def _commit_inline_text_payload(self, payload: dict, text: str) -> bool:
        mode = str(payload.get("mode", "") or "")
        if mode == "generated":
            return self._commit_generated_text_payload(payload, text)
        if mode != "static":
            return False
        geometry = payload.get("geometry")
        if not isinstance(geometry, dict):
            return False
        annotation_id = f"ann-{uuid4().hex[:12]}"
        style = self._active_draw_style()
        object_payload = annotation_to_figure_object(
            {
                "id": annotation_id,
                "type": "text",
                "text": str(text),
                **geometry,
                **style,
            }
        )
        session = self._edit_session_for_adapter()
        if session is not None:
            result = self._execute_edit(AddObjectCommand(object_payload))
            if result is None or not result.changed:
                return False
            session.select(annotation_id, "annotation_canvas")
            self._annotation_canvas.select_annotation(annotation_id)
            self._refresh_object_list(annotation_id)
            return True
        width = float(geometry.get("width", 0.0) or 0.0) * self._annotation_canvas._image_width
        height = float(geometry.get("height", 0.0) or 0.0) * self._annotation_canvas._image_height
        created = self._annotation_canvas.add_text_annotation(
            str(text),
            float(geometry.get("x", 0.0) or 0.0) * self._annotation_canvas._image_width,
            float(geometry.get("y", 0.0) or 0.0) * self._annotation_canvas._image_height,
            width=width if width > 0 else None,
            height=height if height > 0 else None,
        )
        return bool(created)

    def _on_add_text_annotation(self):
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        text = self._annotation_text_edit.text().strip() or "Annotation"
        session = self._edit_session_for_adapter()
        if session is not None:
            annotation_id = f"ann-{uuid4().hex[:12]}"
            object_payload = annotation_to_figure_object(
                {
                    "id": annotation_id,
                    "type": "text",
                    "x": 0.125,
                    "y": 0.2,
                    "text": text,
                    "font_size": 12,
                    "color": "#111111",
                }
            )
            result = self._execute_edit(AddObjectCommand(object_payload))
            if result is not None and result.changed:
                session.select(annotation_id, "annotation_canvas")
                self._annotation_canvas.select_annotation(annotation_id)
                self._refresh_object_list(annotation_id)
            return
        self._annotation_canvas.add_text_annotation(text, 20, 20)
        self._refresh_object_list(self._annotation_canvas.selected_annotation_id())

    def _on_update_selected_text_annotation(self):
        if self._selected_figure_object_id and self._is_generated_figure_document():
            self._rename_selected_generated_object()
            return
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        text = self._annotation_text_edit.text().strip()
        session = self._edit_session_for_adapter()
        annotation_id = self._annotation_canvas.selected_annotation_id()
        if session is not None and self._session_has_object(annotation_id) and text:
            session.select(annotation_id, "annotation_canvas")
            result = self._execute_edit(UpdateTextCommand(annotation_id, text))
            if result is not None and result.changed:
                self._annotation_canvas.select_annotation(annotation_id)
                self._refresh_object_list(annotation_id)
            return
        if text and self._annotation_canvas.update_selected_text(text):
            self._refresh_object_list(self._annotation_canvas.selected_annotation_id())

    def _on_annotation_apply_style(self):
        if self._selected_figure_object_id and self._is_generated_figure_document():
            self._apply_style_to_selected_generated_object()
            return
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        color = self._annotation_color_edit.text().strip() or None
        session = self._edit_session_for_adapter()
        annotation_id = self._annotation_canvas.selected_annotation_id()
        if session is not None and self._session_has_object(annotation_id):
            updates = {
                "font_size": float(self._annotation_font_size_spin.value()),
                "line_width": float(self._annotation_line_width_spin.value()),
                "line_style": LINE_STYLE_OPTIONS.get(
                    self._annotation_line_style_combo.currentText(), "-"
                ),
                "alpha": float(self._annotation_alpha_spin.value()),
            }
            if color:
                updates["color"] = color
            session.select(annotation_id, "annotation_canvas")
            self._execute_edit(UpdateStyleCommand(annotation_id, updates))
            return
        if self._annotation_canvas.update_selected_properties(
            color=color,
            font_size=self._annotation_font_size_spin.value(),
            line_width=self._annotation_line_width_spin.value(),
            line_style=LINE_STYLE_OPTIONS.get(
                self._annotation_line_style_combo.currentText(), "-"
            ),
            alpha=self._annotation_alpha_spin.value(),
        ):
            return

    def _on_add_rectangle_annotation(self):
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        self.set_tool("rectangle")

    def _on_add_line_annotation(self):
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        self.set_tool("line")

    def _on_add_arrow_annotation(self):
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        self.set_tool("arrow")

    def _on_add_highlight_annotation(self):
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        self.set_tool("highlight")

    def _on_crop_annotation_canvas(self):
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        self.set_tool("crop")

    def _on_annotation_undo(self):
        session = self._edit_session_for_adapter()
        if session is not None and session.can_undo:
            self._project_edit_result(session.undo())
            return
        if self._is_generated_figure_document() and self._last_deleted_figure_object_id:
            self._restore_last_deleted_generated_object()
            return
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        self._annotation_canvas.undo()

    def _on_annotation_redo(self):
        session = self._edit_session_for_adapter()
        if session is not None and session.can_redo:
            self._project_edit_result(session.redo())
            return
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        self._annotation_canvas.redo()

    def _on_annotation_delete(self):
        if self._selected_figure_object_id and self._is_generated_figure_document():
            self._soft_delete_selected_generated_object()
            return
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        session = self._edit_session_for_adapter()
        annotation_id = self._annotation_canvas.selected_annotation_id()
        if session is not None and self._session_has_object(annotation_id):
            session.select(annotation_id, "annotation_canvas")
            self._execute_edit(DeleteObjectCommand(annotation_id))
            return
        if self._annotation_canvas.delete_selected_annotation():
            self._refresh_object_list()

    def _on_annotation_copy(self):
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        self._annotation_canvas.copy_selected_annotation()

    def _on_annotation_paste(self):
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        if self._annotation_canvas.paste_annotation():
            self._refresh_object_list(self._annotation_canvas.selected_annotation_id())

    def _on_annotation_front(self):
        if self._selected_figure_object_id and self._is_generated_figure_document():
            self._move_selected_generated_object(to_front=True)
            return
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        if self._annotation_canvas.bring_selected_to_front():
            self._refresh_object_list(self._annotation_canvas.selected_annotation_id())

    def _on_annotation_back(self):
        if self._selected_figure_object_id and self._is_generated_figure_document():
            self._move_selected_generated_object(to_front=False)
            return
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        if self._annotation_canvas.send_selected_to_back():
            self._refresh_object_list(self._annotation_canvas.selected_annotation_id())

    def _sync_annotation_tool_buttons(self, tool):
        mapping = {
            "line": self._btn_annotation_add_line,
            "arrow": self._btn_annotation_add_arrow,
            "rectangle": self._btn_annotation_add_rect,
            "highlight": self._btn_annotation_add_highlight,
            "crop": self._btn_annotation_crop,
        }
        for name, button in mapping.items():
            button.blockSignals(True)
            button.setChecked(name == tool)
            button.blockSignals(False)

    def _on_annotation_tool_changed(self, tool):
        self._sync_annotation_tool_buttons(tool)
        self._sync_editor_toolbar()

    def _on_annotation_interaction_cancelled(self):
        canvas = getattr(self, "_annotation_canvas", None)
        if canvas is not None and canvas.current_tool() != "select":
            canvas.set_tool("select")
        self._set_editor_cancel_status()
        self._sync_editor_toolbar()

    def _sync_annotation_property_controls(self, _annotation_id=""):
        if self._annotation_canvas is None:
            return
        self._refresh_object_list(_annotation_id)
        annotation = self._annotation_canvas.selected_annotation()
        if not annotation:
            self._clear_annotation_property_controls()
            self._sync_context_style_bar()
            return
        self._reveal_inspector_for_selection()
        session = self._edit_session_for_adapter()
        if session is not None:
            annotation_id = str(annotation.get("id", "") or "")
            session.select(annotation_id, "annotation-canvas")
            self._sync_inspector_capabilities()
        self._sync_object_action_buttons(str(annotation.get("id", "") or ""))
        self._selected_object_label.setText(self._object_list_label(annotation))
        has_position = "x" in annotation and "y" in annotation
        has_size = "width" in annotation and "height" in annotation
        has_segment = all(key in annotation for key in ("x1", "y1", "x2", "y2"))
        is_curve = str(annotation.get("type", "") or "") == "curve"
        self._set_geometry_spin_ranges(0.0, 1.0)
        self._set_geometry_controls_enabled(has_position or has_segment, has_size or has_segment)
        self._set_curve_control_enabled(is_curve)
        self._set_curve_control_ranges(0.0, 1.0)
        if has_segment:
            self._set_geometry_label_mode("segment")
        elif has_size:
            self._set_geometry_label_mode("box")
        else:
            self._set_geometry_label_mode("position")
        self._syncing_geometry_controls = True
        try:
            if "x" in annotation:
                self._annotation_x_spin.setValue(float(annotation.get("x", 0.0) or 0.0))
            if "y" in annotation:
                self._annotation_y_spin.setValue(float(annotation.get("y", 0.0) or 0.0))
            if "width" in annotation:
                self._annotation_w_spin.setValue(float(annotation.get("width", 0.0) or 0.0))
            if "height" in annotation:
                self._annotation_h_spin.setValue(float(annotation.get("height", 0.0) or 0.0))
            if "x1" in annotation:
                self._annotation_x_spin.setValue(float(annotation.get("x1", 0.0) or 0.0))
            if "y1" in annotation:
                self._annotation_y_spin.setValue(float(annotation.get("y1", 0.0) or 0.0))
            if "x2" in annotation:
                self._annotation_w_spin.setValue(float(annotation.get("x2", 0.0) or 0.0))
            if "y2" in annotation:
                self._annotation_h_spin.setValue(float(annotation.get("y2", 0.0) or 0.0))
            if is_curve:
                self._set_control_value_silently(
                    self._annotation_curve_control_x_spin,
                    self._curve_control_value(annotation, "control_x"),
                )
                self._set_control_value_silently(
                    self._annotation_curve_control_y_spin,
                    self._curve_control_value(annotation, "control_y"),
                )
        finally:
            self._syncing_geometry_controls = False
        is_text_annotation = "text" in annotation
        self._btn_annotation_update_text.setEnabled(is_text_annotation)
        self._annotation_text_edit.blockSignals(True)
        self._annotation_text_edit.setText(str(annotation.get("text", "") or "") if is_text_annotation else "")
        self._annotation_text_edit.blockSignals(False)
        kind = str(annotation.get("type", "") or "")
        self._set_style_controls_enabled(
            kind == "text",
            kind in {"line", "arrow", "curve", "rectangle"},
            kind == "highlight",
        )
        color = str(annotation.get("color", "") or "")
        if color:
            self._annotation_color_edit.blockSignals(True)
            self._annotation_color_edit.setText(color)
            self._annotation_color_edit.blockSignals(False)
        self._set_control_value_silently(
            self._annotation_font_size_spin,
            int(annotation.get("font_size", 12) or 12),
        )
        self._set_control_value_silently(
            self._annotation_line_width_spin,
            float(annotation.get("line_width", 2.0) or 2.0),
        )
        self._set_control_value_silently(
            self._annotation_alpha_spin,
            float(annotation.get("alpha", 0.35) or 0.35),
        )
        self._annotation_line_style_combo.blockSignals(True)
        self._annotation_line_style_combo.setCurrentText("Solid")
        self._annotation_line_style_combo.blockSignals(False)
        self._annotation_marker_combo.blockSignals(True)
        self._annotation_marker_combo.setCurrentText("None")
        self._annotation_marker_combo.blockSignals(False)
        self._set_control_value_silently(self._annotation_marker_size_spin, 6.0)
        self._sync_context_style_bar()

    def _on_annotation_canvas_changed(self):
        if self._annotation_canvas is None:
            return
        self._sync_annotation_property_controls(
            self._annotation_canvas.selected_annotation_id()
        )
        self.figure_changed.emit()

    def _set_geometry_controls_enabled(self, position_enabled, size_enabled=False):
        self._set_geometry_control_enabled_state(
            bool(position_enabled),
            bool(position_enabled),
            bool(size_enabled),
            bool(size_enabled),
        )

    def _set_geometry_control_enabled_state(self, x_enabled, y_enabled, w_enabled, h_enabled):
        self._annotation_x_spin.setEnabled(bool(x_enabled))
        self._annotation_y_spin.setEnabled(bool(y_enabled))
        self._annotation_w_spin.setEnabled(bool(w_enabled))
        self._annotation_h_spin.setEnabled(bool(h_enabled))

    def _set_geometry_spin_ranges(self, minimum, maximum):
        for control in (
            self._annotation_x_spin,
            self._annotation_y_spin,
            self._annotation_w_spin,
            self._annotation_h_spin,
        ):
            control.setRange(float(minimum), float(maximum))

    def _set_curve_control_ranges(self, minimum, maximum):
        for control in (
            self._annotation_curve_control_x_spin,
            self._annotation_curve_control_y_spin,
        ):
            control.setRange(float(minimum), float(maximum))

    def _set_curve_control_enabled(self, enabled):
        visible = bool(enabled)
        self._annotation_curve_control.setVisible(visible)
        self._annotation_curve_control_label.setVisible(visible)
        self._annotation_curve_control_x_spin.setEnabled(visible)
        self._annotation_curve_control_y_spin.setEnabled(visible)

    @staticmethod
    def _curve_control_value(figure_object, key):
        container = figure_object
        for container_key in ("geometry", "bounds"):
            candidate = figure_object.get(container_key)
            if isinstance(candidate, dict):
                container = candidate
                break
        try:
            return float(container.get(key, 0.0) or 0.0)
        except (TypeError, ValueError, OverflowError):
            return 0.0

    def _set_style_controls_enabled(
        self,
        font_size_enabled,
        line_width_enabled,
        alpha_enabled,
        color_enabled=True,
        line_style_enabled=False,
        marker_enabled=False,
        marker_size_enabled=False,
    ):
        self._annotation_color_edit.setEnabled(bool(color_enabled))
        self._annotation_font_size_spin.setEnabled(bool(font_size_enabled))
        self._annotation_line_width_spin.setEnabled(bool(line_width_enabled))
        self._annotation_alpha_spin.setEnabled(bool(alpha_enabled))
        self._annotation_line_style_combo.setEnabled(bool(line_style_enabled))
        self._annotation_marker_combo.setEnabled(bool(marker_enabled))
        self._annotation_marker_size_spin.setEnabled(bool(marker_size_enabled))
        button = getattr(self, "_btn_annotation_apply_style", None)
        if button is not None:
            button.setEnabled(
                bool(
                    font_size_enabled
                    or
                    color_enabled
                    or line_style_enabled
                    or marker_enabled
                    or marker_size_enabled
                )
            )

    def _set_object_action_buttons_enabled(self, enabled):
        for button_name in (
            "_btn_annotation_delete",
            "_btn_annotation_copy",
            "_btn_annotation_front",
            "_btn_annotation_back",
            "_btn_annotation_lock",
        ):
            button = getattr(self, button_name, None)
            if button is not None:
                button.setEnabled(bool(enabled))

    def _sync_object_action_buttons(self, annotation_id):
        self._btn_annotation_delete.setEnabled(bool(annotation_id))
        self._btn_annotation_copy.setEnabled(bool(annotation_id))
        annotations = []
        if self._annotation_canvas is not None and not self._annotation_canvas.isHidden():
            annotations = self._annotation_canvas.annotation_state()
        annotation_ids = [str(item.get("id", "") or "") for item in annotations]
        try:
            index = annotation_ids.index(str(annotation_id))
        except ValueError:
            index = -1
        self._btn_annotation_back.setEnabled(index > 0)
        self._btn_annotation_front.setEnabled(index >= 0 and index < len(annotation_ids) - 1)

    def _on_toggle_selected_lock(self):
        object_id = str(getattr(self, "_selected_figure_object_id", "") or "")
        if not object_id:
            object_id = str(
                getattr(self._annotation_canvas, "selected_annotation_id", lambda: "")()
                or ""
            )
        object_payload = self._selected_canonical_object()
        if not object_id or not isinstance(object_payload, dict):
            return
        session = self._edit_session_for_adapter()
        if session is None:
            return
        session.select(object_id, "lock")
        result = self._execute_edit(SetLockCommand(object_id, not bool(object_payload.get("locked"))))
        if result is not None and result.changed:
            self._refresh_object_list(object_id)

    def _set_control_value_silently(self, control, value):
        control.blockSignals(True)
        control.setValue(value)
        control.blockSignals(False)

    def _clear_annotation_property_controls(self):
        self._selected_figure_object_id = ""
        self._selected_object_label.setText(tr("EDITOR_OBJECT_NONE"))
        self._annotation_text_edit.blockSignals(True)
        self._annotation_text_edit.setText("")
        self._annotation_text_edit.blockSignals(False)
        self._btn_annotation_update_text.setEnabled(False)
        self._set_geometry_label_mode("box")
        self._set_geometry_spin_ranges(0.0, 1.0)
        self._set_geometry_controls_enabled(False)
        self._set_curve_control_enabled(False)
        self._set_style_controls_enabled(False, False, False, color_enabled=False)
        self._set_object_action_buttons_enabled(False)
        self._set_control_value_silently(self._annotation_font_size_spin, 12)
        self._set_control_value_silently(self._annotation_line_width_spin, 2.0)
        self._set_control_value_silently(self._annotation_alpha_spin, 0.35)
        self._annotation_line_style_combo.blockSignals(True)
        self._annotation_line_style_combo.setCurrentText("Solid")
        self._annotation_line_style_combo.blockSignals(False)
        self._annotation_marker_combo.blockSignals(True)
        self._annotation_marker_combo.setCurrentText("None")
        self._annotation_marker_combo.blockSignals(False)
        self._set_control_value_silently(self._annotation_marker_size_spin, 6.0)

    def _set_geometry_label_mode(self, mode):
        labels = {
            "segment": ("X1", "Y1", "X2", "Y2"),
            "vertical": ("X", "", "", ""),
            "horizontal": ("", "Y", "", ""),
            "point": ("X", "Y", "", ""),
            "box": ("X", "Y", "W", "H"),
            "position": ("X", "Y", "W", "H"),
        }.get(mode, ("X", "Y", "W", "H"))
        self._annotation_x_label.setText(labels[0])
        self._annotation_y_label.setText(labels[1])
        self._annotation_w_label.setText(labels[2])
        self._annotation_h_label.setText(labels[3])

    def _on_annotation_geometry_changed(self, *_):
        if self._syncing_geometry_controls:
            return
        if self._selected_figure_object_id and self._is_generated_figure_document():
            self._update_selected_generated_object_geometry()
            return
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        if self._annotation_canvas.update_selected_geometry(
            x=self._annotation_x_spin.value(),
            y=self._annotation_y_spin.value(),
            width=self._annotation_w_spin.value(),
            height=self._annotation_h_spin.value(),
            x1=self._annotation_x_spin.value(),
            y1=self._annotation_y_spin.value(),
            x2=self._annotation_w_spin.value(),
            y2=self._annotation_h_spin.value(),
        ):
            self._refresh_object_list(self._annotation_canvas.selected_annotation_id())

    def _on_annotation_curve_control_changed(self, *_):
        if self._syncing_geometry_controls:
            return
        control_x = float(self._annotation_curve_control_x_spin.value())
        control_y = float(self._annotation_curve_control_y_spin.value())
        if self._selected_figure_object_id and self._is_generated_figure_document():
            if self._apply_generated_curve_handle_drag(
                self._selected_figure_object_id,
                2,
                control_x,
                control_y,
            ):
                self._persist_generated_document()
                self.figure_changed.emit()
            return
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        if self._annotation_canvas.update_selected_geometry(
            control_x=control_x,
            control_y=control_y,
        ):
            self._refresh_object_list(self._annotation_canvas.selected_annotation_id())

    def _update_selected_generated_object_geometry(self):
        figure_object = self._generated_figure_object_by_id(self._selected_figure_object_id)
        if not figure_object:
            return
        if str(figure_object.get("type", "") or "") == "plot_series":
            point_index = self._selected_generated_plot_series_point_index(figure_object)
            if point_index is None:
                return
            if not self._apply_generated_plot_series_handle_drag(
                self._selected_figure_object_id,
                point_index,
                float(self._annotation_x_spin.value()),
                float(self._annotation_y_spin.value()),
            ):
                return
            self._persist_generated_document()
            self._show_generated_figure_document()
            self.figure_changed.emit()
            return
        if str(figure_object.get("type", "") or "") == "legend":
            if not self._apply_generated_legend_drag(
                self._selected_figure_object_id,
                float(self._annotation_x_spin.value()),
                float(self._annotation_y_spin.value()),
            ):
                return
            self._persist_generated_document()
            self._show_generated_figure_document()
            self.figure_changed.emit()
            return
        if str(figure_object.get("type", "") or "") == "text":
            updates = {
                "x": float(self._annotation_x_spin.value()),
                "y": float(self._annotation_y_spin.value()),
                "width": float(self._annotation_w_spin.value()),
                "height": float(self._annotation_h_spin.value()),
            }
            if is_axes_text_box(figure_object):
                updates = clamp_axes_box(
                    updates["x"],
                    updates["y"],
                    updates["width"],
                    updates["height"],
                )
            session = self._edit_session_for_adapter()
            if session is not None:
                session.select(self._selected_figure_object_id, "generated-inspector")
                result = self._execute_edit(
                    UpdateGeometryCommand(self._selected_figure_object_id, updates)
                )
                if result is None or not result.changed:
                    return
            elif not self._generated_store().update_geometry(
                self._selected_figure_object_id,
                updates,
            ):
                return
            self._persist_generated_document()
            self._show_generated_figure_document()
            self.figure_changed.emit()
            return
        if str(figure_object.get("type", "") or "") not in {"line", "curve"}:
            return
        store = self._generated_store()
        geometry = self._generated_object_geometry_config(figure_object)
        mode = str(geometry["mode"] or "segment")
        if mode == "vertical":
            updates = {
                "x1": float(self._annotation_x_spin.value()),
            }
        elif mode == "horizontal":
            updates = {
                "y1": float(self._annotation_y_spin.value()),
            }
        else:
            updates = {
                "x1": float(self._annotation_x_spin.value()),
                "y1": float(self._annotation_y_spin.value()),
                "x2": float(self._annotation_w_spin.value()),
                "y2": float(self._annotation_h_spin.value()),
            }
        session = self._edit_session_for_adapter()
        if session is not None:
            session.select(self._selected_figure_object_id, "generated-inspector")
            result = self._execute_edit(
                UpdateGeometryCommand(self._selected_figure_object_id, updates)
            )
            if result is None or not result.changed:
                return
            self._persist_generated_document()
            self._show_generated_figure_document()
            self.figure_changed.emit()
            return
        if not store.update_geometry(self._selected_figure_object_id, updates):
            return
        self._persist_generated_document()
        self._show_generated_figure_document()
        self.figure_changed.emit()

    def _sync_generated_object_property_controls(self, object_id):
        figure_object = self._generated_figure_object_by_id(object_id)
        if not figure_object:
            self._clear_annotation_property_controls()
            return
        style = figure_object.get("style", {}) if isinstance(figure_object.get("style"), dict) else {}
        capabilities = self._generated_object_capabilities(figure_object)
        self._set_geometry_controls_enabled(False)
        self._set_style_controls_enabled(
            bool(capabilities["font_size"]),
            bool(capabilities["style"]),
            bool(capabilities["style"]),
            color_enabled=bool(capabilities["style"]),
            line_style_enabled=bool(capabilities["line_style"]),
            marker_enabled=bool(capabilities["marker"]),
            marker_size_enabled=bool(capabilities["marker_size"]),
        )
        geometry = self._generated_object_geometry_config(figure_object)
        self._set_geometry_spin_ranges(
            -1_000_000_000.0 if capabilities["geometry"] else 0.0,
            1_000_000_000.0 if capabilities["geometry"] else 1.0,
        )
        is_curve = str(figure_object.get("type", "") or "") == "curve"
        self._set_curve_control_enabled(is_curve)
        self._set_curve_control_ranges(
            -1_000_000_000.0 if is_curve else 0.0,
            1_000_000_000.0 if is_curve else 1.0,
        )
        self._set_geometry_control_enabled_state(*geometry["enabled"])
        self._set_geometry_label_mode(str(geometry.get("mode", "box") or "box"))
        self._set_object_action_buttons_enabled(False)
        self._btn_annotation_delete.setEnabled(bool(capabilities["deletable"]))
        can_reorder = (
            bool(capabilities["reorderable"])
            and len(self._reorderable_generated_figure_objects()) > 1
        )
        self._btn_annotation_front.setEnabled(can_reorder)
        self._btn_annotation_back.setEnabled(can_reorder)
        lock_button = getattr(self, "_btn_annotation_lock", None)
        if lock_button is not None:
            lock_button.setEnabled(str(figure_object.get("type", "") or "") != "image_background")
            lock_button.blockSignals(True)
            lock_button.setChecked(bool(figure_object.get("locked", False)))
            lock_button.blockSignals(False)
        self._btn_annotation_update_text.setEnabled(bool(capabilities["renameable"]))
        self._annotation_text_edit.blockSignals(True)
        self._annotation_text_edit.setText(str(figure_object.get("name", "") or ""))
        self._annotation_text_edit.blockSignals(False)
        color = str(style.get("color", "") or self._current_colours[0])
        self._annotation_color_edit.blockSignals(True)
        self._annotation_color_edit.setText(color)
        self._annotation_color_edit.blockSignals(False)
        self._set_control_value_silently(
            self._annotation_line_width_spin,
            float(style.get("line_width", self._line_width) or self._line_width),
        )
        self._set_control_value_silently(
            self._annotation_font_size_spin,
            int(float(style.get("font_size", 12) or 12)),
        )
        self._set_control_value_silently(
            self._annotation_alpha_spin,
            float(style.get("alpha", 1.0) or 1.0),
        )
        self._annotation_line_style_combo.blockSignals(True)
        self._annotation_line_style_combo.setCurrentText(
            self._line_style_label_for_value(str(style.get("line_style", "-") or "-"))
        )
        self._annotation_line_style_combo.blockSignals(False)
        marker_value = self._generated_plot_series_marker_value(figure_object)
        self._annotation_marker_combo.blockSignals(True)
        self._annotation_marker_combo.setCurrentText(
            self._marker_label_for_value(marker_value)
        )
        self._annotation_marker_combo.blockSignals(False)
        self._set_control_value_silently(
            self._annotation_marker_size_spin,
            float(style.get("marker_size", 6.0) or 6.0),
        )
        if capabilities["geometry"]:
            self._set_control_value_silently(
                self._annotation_x_spin,
                float(geometry["values"][0]),
            )
            self._set_control_value_silently(
                self._annotation_y_spin,
                float(geometry["values"][1]),
            )
            self._set_control_value_silently(
                self._annotation_w_spin,
                float(geometry["values"][2]),
            )
            self._set_control_value_silently(
                self._annotation_h_spin,
                float(geometry["values"][3]),
            )
        if is_curve:
            self._set_control_value_silently(
                self._annotation_curve_control_x_spin,
                self._curve_control_value(figure_object, "control_x"),
            )
            self._set_control_value_silently(
                self._annotation_curve_control_y_spin,
                self._curve_control_value(figure_object, "control_y"),
            )

    def _generated_object_capabilities(self, figure_object):
        return _shared_generated_object_capabilities(
            figure_object,
            selected_plot_series_point_geometry=self._selected_generated_plot_series_point_index(
                figure_object
            )
            is not None,
        )

    def _generated_object_geometry_config(self, figure_object):
        legend_anchor = None
        if str(figure_object.get("type", "") or "") == "legend":
            legend = self._generated_legend_artist()
            axes = self._figure.axes[0] if self._figure and self._figure.axes else None
            legend_anchor = self._generated_legend_anchor_for_drag(figure_object, legend, axes)
        point_index = self._selected_generated_plot_series_point_index(figure_object)
        inline_data = (
            self._materialize_generated_plot_series_inline_data(figure_object)
            if point_index is not None
            else None
        )
        return _shared_generated_object_geometry_config(
            figure_object,
            legend_anchor=legend_anchor,
            point_index=point_index,
            inline_data=inline_data,
        )

    def _apply_style_to_selected_generated_object(self):
        store = self._generated_store()
        if not self._source_path:
            return
        figure_object = self._generated_figure_object_by_id(self._selected_figure_object_id)
        if not figure_object:
            return
        capabilities = self._generated_object_capabilities(figure_object)
        edit_capabilities = capabilities_for(figure_object)
        color = self._annotation_color_edit.text().strip()
        updates = {"alpha": float(self._annotation_alpha_spin.value())}
        if edit_capabilities.line_width:
            updates["line_width"] = float(self._annotation_line_width_spin.value())
        if color:
            updates["color"] = color
        if capabilities["line_style"]:
            line_style = self._annotation_line_style_value()
            updates["line_style"] = line_style or "-"
        if capabilities["marker"]:
            marker = self._annotation_marker_value()
            if str(figure_object.get("chart_kind", "") or "") == "scatter" and not marker:
                marker = "o"
            updates["marker"] = marker
        if capabilities["marker_size"]:
            updates["marker_size"] = float(self._annotation_marker_size_spin.value())
        if capabilities["font_size"]:
            updates["font_size"] = float(self._annotation_font_size_spin.value())
        session = self._edit_session_for_adapter()
        if session is not None:
            session.select(self._selected_figure_object_id, "list")
            result = self._execute_edit(UpdateStyleCommand(self._selected_figure_object_id, updates))
            if result is not None and result.changed:
                self._show_generated_figure_document()
                self._persist_generated_document()
            return
        if not store.update_style(self._selected_figure_object_id, updates):
            return
        self._persist_generated_document()
        self._show_generated_figure_document()
        self.figure_changed.emit()

    def _annotation_line_style_value(self):
        return _shared_annotation_line_style_value(
            self._annotation_line_style_combo.currentText(), LINE_STYLE_OPTIONS
        )

    def _annotation_marker_value(self):
        return _shared_annotation_marker_value(
            self._annotation_marker_combo.currentText(), MARKER_OPTIONS
        )

    def _line_style_label_for_value(self, value):
        return _shared_line_style_label_for_value(value, LINE_STYLE_OPTIONS)

    def _marker_label_for_value(self, value):
        return _shared_marker_label_for_value(value, MARKER_OPTIONS)

    def _generated_plot_series_marker_value(self, figure_object):
        return _shared_generated_plot_series_marker_value(figure_object)
