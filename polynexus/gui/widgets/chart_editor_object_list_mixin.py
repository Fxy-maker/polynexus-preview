from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QListWidgetItem,
    QTreeWidget,
)

from ..i18n import tr
from ...core.figure_edit_commands import SetVisibilityCommand
from .chart_editor_layer_model import LayerTreeNode, build_layer_tree
from .chart_editor_layer_widget import LayerTreeItem


class ChartEditorObjectListMixin:
    def _schedule_object_list_refresh(self, selected_id=""):
        """Refresh after itemChanged returns to avoid deleting a live Qt item."""
        if getattr(self, "_object_list_refresh_pending", False):
            return
        self._object_list_refresh_pending = True

        def refresh():
            self._object_list_refresh_pending = False
            if getattr(self, "_object_list", None) is not None:
                self._refresh_object_list(selected_id)

        QTimer.singleShot(0, refresh)

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
            label = kind
        else:
            label = f"{kind}: {name}" if name else kind
        if bool(figure_object.get("locked")):
            return f"{tr('EDITOR_OBJECT_LOCKED')} · {label}"
        return label

    def _reorderable_generated_figure_objects(self):
        return [obj for obj in self._generated_figure_objects() if obj.get("type") != "legend"]

    def _refresh_object_list(self, selected_id=""):
        if not hasattr(self, "_object_list"):
            return
        if hasattr(self._object_list, "setSelectionMode"):
            self._object_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        query = str(
            getattr(getattr(self, "_object_search_edit", None), "text", lambda: "")()
            or ""
        ).strip().casefold()
        self._syncing_object_list = True
        try:
            self._object_list.clear()
            selected_row = 0
            figure_objects = self._generated_figure_objects()
            if not selected_id and self._annotation_canvas is not None:
                selected_id = self._annotation_canvas.selected_annotation_id()
            if isinstance(self._object_list, QTreeWidget):
                background = LayerTreeItem([tr("EDITOR_OBJECT_BACKGROUND")])
                background.setData(0, Qt.UserRole, "__background__")
                background.setData(0, Qt.UserRole + 1, "background")
                self._object_list.addTopLevelItem(background)
                for node in build_layer_tree(
                    figure_objects,
                    query=query,
                    label_for=self._figure_object_list_label,
                ):
                    self._add_layer_tree_node(node)
                self._add_tree_annotations(query)
                self._set_tree_current_item(selected_id)
            else:
                background = QListWidgetItem(tr("EDITOR_OBJECT_BACKGROUND"))
                background.setData(Qt.UserRole, "__background__")
                background.setData(Qt.UserRole + 1, "background")
                self._object_list.addItem(background)

                for figure_object in figure_objects:
                    object_id = str(figure_object.get("id", ""))
                    label = self._figure_object_list_label(figure_object)
                    searchable = " ".join(
                        (
                            object_id,
                            str(figure_object.get("name", "") or ""),
                            str(figure_object.get("type", "") or ""),
                            label,
                        )
                    ).casefold()
                    if query and query not in searchable:
                        continue
                    item = QListWidgetItem(label)
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
            if not isinstance(self._object_list, QTreeWidget):
                for annotation in annotations:
                    annotation_id = str(annotation.get("id", ""))
                    label = self._object_list_label(annotation)
                    searchable = " ".join(
                        (
                            annotation_id,
                            str(annotation.get("text", "") or ""),
                            str(annotation.get("type", "") or ""),
                            label,
                        )
                    ).casefold()
                    if query and query not in searchable:
                        continue
                    item = QListWidgetItem(label)
                    item.setData(Qt.UserRole, annotation_id)
                    item.setData(Qt.UserRole + 1, "annotation")
                    self._object_list.addItem(item)
                    if annotation_id and annotation_id == selected_id:
                        selected_row = self._object_list.count() - 1
                self._object_list.setCurrentRow(selected_row)
        finally:
            self._syncing_object_list = False

    def _add_layer_tree_node(self, node: LayerTreeNode, parent=None):
        if parent is None:
            item = LayerTreeItem([node.label])
            self._object_list.addTopLevelItem(item)
        else:
            item = LayerTreeItem(parent, [node.label])
        item.setData(0, Qt.UserRole, node.object_id or node.node_id)
        item.setData(
            0,
            Qt.UserRole + 1,
            "figure_object" if node.role == "object" else node.role,
        )
        item.setToolTip(0, node.label)
        if node.role == "object":
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(0, Qt.Checked if node.visible else Qt.Unchecked)
        for child in node.children:
            self._add_layer_tree_node(child, item)
        if node.children:
            item.setExpanded(True)
        return item

    def _add_tree_annotations(self, query):
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        for annotation in self._annotation_canvas.annotation_state():
            annotation_id = str(annotation.get("id", ""))
            label = self._object_list_label(annotation)
            searchable = " ".join(
                (
                    annotation_id,
                    str(annotation.get("text", "") or ""),
                    str(annotation.get("type", "") or ""),
                    label,
                )
            ).casefold()
            if query and query.casefold() not in searchable:
                continue
            item = LayerTreeItem([label])
            item.setData(0, Qt.UserRole, annotation_id)
            item.setData(0, Qt.UserRole + 1, "annotation")
            self._object_list.addTopLevelItem(item)

    def _set_tree_current_item(self, selected_id):
        if not selected_id:
            background = self._object_list.topLevelItem(0)
            self._object_list.setCurrentItem(background)
            self._object_list.clearSelection()
            return
        stack = [self._object_list.topLevelItem(index) for index in range(self._object_list.topLevelItemCount())]
        while stack:
            item = stack.pop(0)
            if str(item.data(0, Qt.UserRole) or "") == str(selected_id):
                self._object_list.setCurrentItem(item)
                self._object_list.scrollToItem(item)
                return
            stack.extend(item.child(index) for index in range(item.childCount()))

    def _object_list_selected_ids(self) -> tuple[str, ...]:
        if not hasattr(self, "_object_list"):
            return ()
        ids = []
        for item in self._object_list.selectedItems():
            if isinstance(self._object_list, QTreeWidget):
                role = item.data(0, Qt.UserRole + 1)
                object_id = str(item.data(0, Qt.UserRole) or "").strip()
                if role == "group":
                    for index in range(item.childCount()):
                        child = item.child(index)
                        child_id = str(child.data(0, Qt.UserRole) or "").strip()
                        if child.data(0, Qt.UserRole + 1) == "object" and child_id:
                            ids.append(child_id)
                elif role in {"object", "figure_object", "annotation"} and object_id:
                    ids.append(object_id)
                continue
            role = item.data(Qt.UserRole + 1)
            object_id = str(item.data(Qt.UserRole) or "").strip()
            if role in {"figure_object", "annotation"} and object_id:
                ids.append(object_id)
        return tuple(ids)

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
        if isinstance(self._object_list, QTreeWidget):
            object_id = current.data(0, Qt.UserRole)
            object_role = current.data(0, Qt.UserRole + 1)
        else:
            object_id = current.data(Qt.UserRole)
            object_role = current.data(Qt.UserRole + 1)
        if object_role in {"figure_object", "object", "group"}:
            selected_ids = self._object_list_selected_ids()
            select_many = getattr(self, "_select_generated_objects", None)
            if callable(select_many):
                select_many(selected_ids or [str(object_id or "")], "list")
            else:
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
                self._selected_object_label.setText(tr("EDITOR_OBJECT_BACKGROUND"))
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
        item_role = (
            item.data(0, Qt.UserRole + 1)
            if isinstance(self._object_list, QTreeWidget)
            else item.data(Qt.UserRole + 1)
        )
        if item_role not in {"figure_object", "object"}:
            return
        object_id = (
            item.data(0, Qt.UserRole)
            if isinstance(self._object_list, QTreeWidget)
            else item.data(Qt.UserRole)
        )
        session_has_object = getattr(self, "_session_has_object", None)
        if (
            getattr(self, "_generated_document_mode", False)
            and callable(session_has_object)
            and not session_has_object(object_id)
        ):
            self._reset_edit_session_from_document(self._figure_document)
        result = self._execute_edit(
            SetVisibilityCommand(
                object_id,
                (
                    item.checkState(0) == Qt.Checked
                    if isinstance(self._object_list, QTreeWidget)
                    else item.checkState() == Qt.Checked
                ),
            )
        )
        if result is None or not getattr(result, "changed", False):
            return
        if getattr(self, "_source_path", "") and getattr(
            self, "_generated_document_mode", False
        ):
            self._persist_generated_document()
            self._show_generated_figure_document()
        self._schedule_object_list_refresh(str(object_id or ""))
