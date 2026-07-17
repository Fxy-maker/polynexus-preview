from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem

from ..i18n import tr


class ChartEditorObjectListMixin:
    def _object_list_label(self, annotation):
        kind = str(annotation.get("type", "annotation") or "annotation").title()
        if annotation.get("text"):
            return f"{kind}: {annotation.get('text')}"
        return kind

    def _generated_figure_objects(self):
        return self._generated_store().visible_objects()

    def _figure_object_list_label(self, figure_object):
        object_type = str(figure_object.get("type", "object") or "object")
        chart_kind = str(figure_object.get("chart_kind", "") or "")
        if chart_kind == "heatmap":
            kind = "Heatmap"
        elif chart_kind == "image_grid":
            kind = "Image Grid"
        else:
            kind = object_type.replace("_", " ").title()
        name = str(figure_object.get("name", "") or "").strip()
        if name and name.casefold() == kind.casefold():
            return kind
        return f"{kind}: {name}" if name else kind

    def _reorderable_generated_figure_objects(self):
        return [obj for obj in self._generated_figure_objects() if obj.get("type") != "legend"]

    def _refresh_object_list(self, selected_id=""):
        if not hasattr(self, "_object_list"):
            return
        self._syncing_object_list = True
        try:
            self._object_list.clear()
            background = QListWidgetItem(tr("EDITOR_OBJECT_BACKGROUND"))
            background.setData(Qt.UserRole, "__background__")
            background.setData(Qt.UserRole + 1, "background")
            self._object_list.addItem(background)

            selected_row = 0
            figure_objects = self._generated_figure_objects()
            for figure_object in figure_objects:
                object_id = str(figure_object.get("id", ""))
                item = QListWidgetItem(self._figure_object_list_label(figure_object))
                item.setData(Qt.UserRole, object_id)
                item.setData(Qt.UserRole + 1, "figure_object")
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(
                    Qt.Checked if figure_object.get("visible", True) is not False else Qt.Unchecked
                )
                self._object_list.addItem(item)
                if object_id and object_id == selected_id:
                    selected_row = self._object_list.count() - 1

            annotations = []
            if self._annotation_canvas is not None and not self._annotation_canvas.isHidden():
                annotations = self._annotation_canvas.annotation_state()
            if not selected_id and self._annotation_canvas is not None:
                selected_id = self._annotation_canvas.selected_annotation_id()

            for annotation in annotations:
                annotation_id = str(annotation.get("id", ""))
                item = QListWidgetItem(self._object_list_label(annotation))
                item.setData(Qt.UserRole, annotation_id)
                item.setData(Qt.UserRole + 1, "annotation")
                self._object_list.addItem(item)
                if annotation_id and annotation_id == selected_id:
                    selected_row = self._object_list.count() - 1

            self._object_list.setCurrentRow(selected_row)
        finally:
            self._syncing_object_list = False

    def _rename_selected_generated_object(self):
        store = self._generated_store()
        if not self._source_path:
            return
        name = self._annotation_text_edit.text().strip()
        if not store.rename(self._selected_figure_object_id, name):
            return
        figure_object = store.get(self._selected_figure_object_id)
        self._persist_generated_document()
        self._show_generated_figure_document()
        self._refresh_object_list(self._selected_figure_object_id)
        self._selected_object_label.setText(self._figure_object_list_label(figure_object))
        self.figure_changed.emit()

    def _soft_delete_selected_generated_object(self):
        store = self._generated_store()
        selected_id = str(self._selected_figure_object_id or "")
        if not selected_id or not self._source_path:
            return
        if not store.soft_delete(selected_id):
            return
        self._last_deleted_figure_object_id = selected_id
        self._persist_generated_document()
        self._select_generated_object("", "delete")
        self.figure_changed.emit()

    def _restore_last_deleted_generated_object(self):
        store = self._generated_store()
        if not self._source_path:
            self._last_deleted_figure_object_id = ""
            return
        restored_id = str(self._last_deleted_figure_object_id or "")
        if not store.restore(restored_id):
            self._last_deleted_figure_object_id = ""
            return
        self._persist_generated_document()
        self._last_deleted_figure_object_id = ""
        figure_object = store.get(restored_id)
        self._select_generated_object(restored_id, "restore")
        self._selected_object_label.setText(self._figure_object_list_label(figure_object))
        self.figure_changed.emit()

    def _move_selected_generated_object(self, *, to_front):
        store = self._generated_store()
        selected_id = str(self._selected_figure_object_id or "")
        if not store.move(selected_id, to_front=bool(to_front)):
            return
        if self._source_path:
            self._persist_generated_document()
        self._select_generated_object(selected_id, f"reorder-{'front' if to_front else 'back'}")
        self.figure_changed.emit()

    def _on_object_list_selection_changed(self, current, _previous=None):
        if self._syncing_object_list or current is None:
            return
        object_id = current.data(Qt.UserRole)
        object_role = current.data(Qt.UserRole + 1)
        if object_role == "figure_object":
            self._select_generated_object(str(object_id or ""), "list")
            return
        if self._generated_document_mode:
            self._select_generated_object("", "list")
        else:
            self._selected_figure_object_id = ""
            session = self._edit_session_for_adapter()
            if session is not None:
                session.select("background" if object_id == "__background__" else "", "list")
                self._sync_inspector_capabilities()
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            if object_id == "__background__":
                self._clear_annotation_property_controls()
            return
        if object_id == "__background__":
            self._annotation_canvas.clear_selection()
            self._selected_object_label.setText(tr("EDITOR_OBJECT_BACKGROUND"))
            return
        if object_id:
            self._annotation_canvas.select_annotation(str(object_id))

    def _on_object_list_item_changed(self, item):
        if self._syncing_object_list or item is None:
            return
        if item.data(Qt.UserRole + 1) != "figure_object":
            return
        store = self._generated_store()
        if not store.set_visible(item.data(Qt.UserRole), item.checkState() == Qt.Checked):
            return
        if self._source_path:
            self._persist_generated_document()
        self._show_generated_figure_document()
        self.figure_changed.emit()
