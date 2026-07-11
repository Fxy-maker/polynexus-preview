from __future__ import annotations

from ..chart_editor_status_service import (
    build_generated_drag_status_text,
    build_generated_hover_status_text,
    generated_hover_cursor_shape,
    format_generated_status_number,
)
from ..i18n import tr


class ChartEditorGeneratedStatusMixin:
    def _generated_hover_cursor_shape(self, drag_state):
        return generated_hover_cursor_shape(drag_state)

    def _restore_generated_status_hint(self):
        if getattr(self, "_status_label", None) is None:
            return
        if self._generated_document_mode:
            if self._selection_status_text:
                self._status_label.setText(self._selection_status_text)
                return
            self._status_label.setText(tr("EDITOR_OBJECT_MODE_HINT"))
        elif self._static_file_mode:
            self._status_label.setText(tr("EDITOR_STATIC_MODE_HINT"))
        else:
            self._status_label.setText("")

    def _set_generated_selection_status(self, figure_object):
        if getattr(self, "_status_label", None) is None:
            return
        if not isinstance(figure_object, dict):
            self._clear_generated_selection_status()
            return
        label = self._figure_object_list_label(figure_object)
        if self._selection_cycle_hint_active:
            self._selection_status_text = tr(
                "EDITOR_SELECTED_STATUS_OBJECT_CYCLE_HINT",
                label,
            )
        else:
            self._selection_status_text = tr(
                "EDITOR_SELECTED_STATUS_OBJECT",
                label,
            )
        if not self._hover_status_text and not self._drag_status_text:
            self._status_label.setText(self._selection_status_text)

    def _clear_generated_selection_status(self):
        previous_text = str(self._selection_status_text or "")
        self._selection_status_text = ""
        if not previous_text:
            return
        if getattr(self, "_status_label", None) is None:
            return
        if self._status_label.text() != previous_text:
            return
        self._restore_generated_status_hint()

    def _clear_generated_hover_status(self):
        hover_status_text = str(self._hover_status_text or "")
        self._hover_status_text = ""
        if not hover_status_text:
            return
        if getattr(self, "_status_label", None) is None:
            return
        if self._status_label.text() != hover_status_text:
            return
        self._restore_generated_status_hint()

    def _clear_generated_drag_status(self):
        drag_status_text = str(self._drag_status_text or "")
        self._drag_status_text = ""
        if not drag_status_text:
            return
        if getattr(self, "_status_label", None) is None:
            return
        if self._status_label.text() != drag_status_text:
            return
        self._restore_generated_status_hint()

    def _can_show_generated_hover_status(self):
        if not self._generated_document_mode or getattr(self, "_status_label", None) is None:
            return False
        current_text = self._status_label.text()
        return current_text in {
            "",
            tr("EDITOR_OBJECT_MODE_HINT"),
            str(self._selection_status_text or ""),
            str(self._hover_status_text or ""),
        }

    def _generated_hover_status_text(self, object_id, drag_state):
        figure_object = self._generated_figure_object_by_id(object_id)
        if not figure_object:
            return ""
        label = self._figure_object_list_label(figure_object)
        return build_generated_hover_status_text(label, drag_state)

    def _set_generated_hover_status(self, object_id, drag_state):
        if str(object_id or "") == str(self._selected_figure_object_id or ""):
            kind = str(drag_state.get("kind", "") or "")
            if self._suppress_generated_hover_until_pointer_move or kind == "select":
                self._clear_generated_hover_status()
                return
        if not self._can_show_generated_hover_status():
            return
        hover_status_text = self._generated_hover_status_text(object_id, drag_state)
        if not hover_status_text:
            self._clear_generated_hover_status()
            return
        self._hover_status_text = hover_status_text
        self._status_label.setText(hover_status_text)

    def _generated_drag_status_text(self, object_id, drag_state):
        figure_object = self._generated_figure_object_by_id(object_id)
        if not figure_object:
            return ""
        label = self._figure_object_list_label(figure_object)
        return build_generated_drag_status_text(
            label,
            drag_state,
            figure_object,
            number_formatter=self._format_generated_status_number,
        )

    def _set_generated_drag_status(self, object_id, drag_state):
        if not self._generated_document_mode or getattr(self, "_status_label", None) is None:
            return
        drag_status_text = self._generated_drag_status_text(object_id, drag_state)
        if not drag_status_text:
            return
        self._drag_status_text = drag_status_text
        self._status_label.setText(drag_status_text)

    def _format_generated_status_number(self, value):
        return format_generated_status_number(self._optional_float(value))
