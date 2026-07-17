from __future__ import annotations

from ...core.figure_object_store import FigureObjectStore
from ...core.figure_edit_capabilities import capabilities_for
from ...core.plot_edits import save_figure_document_path
from ...core.figure_document import save_figure_document


class ChartEditorGeneratedSelectionMixin:
    def _reset_generated_selection_model(self):
        self._figure_selection_model.blockSignals(True)
        try:
            self._figure_selection_model.clear("reset")
        finally:
            self._figure_selection_model.blockSignals(False)

    def _generated_store(self):
        if not isinstance(self._figure_document, dict):
            return FigureObjectStore({})
        if self._figure_document.get("mode") != "object":
            return FigureObjectStore({})
        self._ensure_generated_legend_object()
        return FigureObjectStore(self._figure_document)

    def _persist_generated_document(self):
        if not self._source_path:
            return False
        document_path = save_figure_document(self._source_path, self._figure_document)
        save_figure_document_path(self._source_path, str(document_path))
        return True

    def _select_generated_object(self, object_id, source):
        object_id = str(object_id or "")
        source = str(source or "")
        if object_id:
            self._figure_selection_model.select(object_id, source)
            return
        self._figure_selection_model.clear(source)

    def _on_generated_selection_changed(self, object_id, source):
        self._selected_figure_object_id = str(object_id or "")
        session = self._edit_session_for_adapter()
        figure_object = self._generated_figure_object_by_id(self._selected_figure_object_id)
        if session is not None and figure_object is not None and not self._session_has_object(
            self._selected_figure_object_id
        ):
            session = self._reset_edit_session_from_document(self._figure_document)
        if session is not None:
            session.select(self._selected_figure_object_id, f"generated-{source}")
        if not self._generated_document_mode and not self._is_generated_figure_document():
            return
        if source != "canvas":
            self._selection_cycle_hint_active = False
            if source != "list":
                self._clear_selected_generated_line_handle_context()
            self._clear_selected_generated_plot_series_handle_context()
        if self._annotation_canvas is not None and not self._annotation_canvas.isHidden():
            self._annotation_canvas.clear_selection()
        if source == "list":
            if isinstance(figure_object, dict) and str(figure_object.get("type", "") or "") == "line":
                restored_handle_index = self._generated_last_line_handle_indices.get(
                    self._selected_figure_object_id
                )
                if restored_handle_index is not None:
                    self._set_selected_generated_line_handle_context(
                        self._selected_figure_object_id,
                        restored_handle_index,
                    )
                elif self._selected_generated_line_handle_index is None:
                    self._set_selected_generated_line_handle_context(
                        self._selected_figure_object_id,
                        0,
                    )
            else:
                self._clear_selected_generated_line_handle_context()
        if isinstance(figure_object, dict):
            if (
                str(figure_object.get("type", "") or "") != "line"
                or str(self._selected_generated_line_object_id or "")
                != self._selected_figure_object_id
            ):
                self._clear_selected_generated_line_handle_context()
            if (
                str(figure_object.get("type", "") or "") == "line"
                and self._selected_generated_line_handle_index is None
            ):
                self._set_selected_generated_line_handle_context(
                    self._selected_figure_object_id,
                    0,
                )
            if source == "list" and str(figure_object.get("type", "") or "") == "plot_series":
                restored_handle_index = self._generated_last_plot_series_handle_indices.get(
                    self._selected_figure_object_id
                )
                if restored_handle_index is not None:
                    self._set_selected_generated_plot_series_handle_context(
                        self._selected_figure_object_id,
                        restored_handle_index,
                    )
                else:
                    self._set_selected_generated_plot_series_handle_context(
                        self._selected_figure_object_id,
                        0,
                    )
        self._show_generated_figure_document()
        if source != "list":
            self._refresh_object_list(self._selected_figure_object_id)
        if not self._selected_figure_object_id:
            self._clear_selected_generated_line_handle_context()
            self._clear_selected_generated_plot_series_handle_context()
            self._clear_generated_selection_status()
            self._clear_annotation_property_controls()
            return
        if not figure_object:
            self._clear_selected_generated_line_handle_context()
            self._clear_selected_generated_plot_series_handle_context()
            self._clear_generated_selection_status()
            self._clear_annotation_property_controls()
            return
        if (
            str(figure_object.get("type", "") or "") != "line"
            or str(self._selected_generated_line_object_id or "")
            != self._selected_figure_object_id
        ):
            self._clear_selected_generated_line_handle_context()
        if (
            str(figure_object.get("type", "") or "") != "plot_series"
            or str(self._selected_generated_plot_series_object_id or "")
            != self._selected_figure_object_id
        ):
            self._clear_selected_generated_plot_series_handle_context()
        if (
            str(figure_object.get("type", "") or "") == "line"
            and self._selected_generated_line_handle_index is None
        ):
            self._set_selected_generated_line_handle_context(
                self._selected_figure_object_id,
                0,
            )
        self._selected_object_label.setText(self._figure_object_list_label(figure_object))
        self._sync_generated_object_property_controls(self._selected_figure_object_id)
        self._sync_inspector_capabilities()
        object_capabilities = capabilities_for(figure_object)
        self._annotation_text_edit.setEnabled(bool(object_capabilities.text))
        self._annotation_font_size_spin.setEnabled(bool(object_capabilities.font_size))
        if str(figure_object.get("type", "") or "") != "plot_series":
            self._annotation_line_width_spin.setEnabled(bool(object_capabilities.line_width))
            self._annotation_line_style_combo.setEnabled(bool(object_capabilities.line_style))
            self._annotation_marker_combo.setEnabled(bool(object_capabilities.marker))
            self._annotation_marker_size_spin.setEnabled(bool(object_capabilities.marker_size))
        self._set_generated_selection_status(figure_object)
