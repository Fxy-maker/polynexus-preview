from __future__ import annotations

from PySide6.QtCore import Qt

from polynexus.gui.widgets.chart_editor import ChartEditor
from polynexus.gui.widgets.chart_editor_object_list_mixin import ChartEditorObjectListMixin


def test_object_tree_search_filters_by_name_and_keeps_background_row():
    from PySide6.QtWidgets import QApplication, QLineEdit, QListWidget

    QApplication.instance() or QApplication([])

    class _Store:
        def visible_objects(self):
            return [
                {"id": "line-a", "type": "line", "name": "Baseline"},
                {"id": "text-peak", "type": "text", "name": "Peak marker"},
            ]

    class _Harness(ChartEditorObjectListMixin):
        def __init__(self):
            self._object_list = QListWidget()
            self._object_search_edit = QLineEdit()
            self._generated_document_mode = True
            self._annotation_canvas = None
            self._syncing_object_list = False
            self._selected_figure_object_id = ""
            self._store = _Store()

        def _generated_store(self):
            return self._store

    editor = _Harness()
    editor._refresh_object_list()
    editor._object_search_edit.setText("peak")
    editor._refresh_object_list()

    assert editor._object_list.count() == 2
    assert editor._object_list.item(0).data(Qt.UserRole) == "__background__"
    assert editor._object_list.item(1).data(Qt.UserRole) == "text-peak"


def test_object_tree_exposes_extended_selected_ids_in_order():
    from PySide6.QtWidgets import QApplication, QListWidget

    QApplication.instance() or QApplication([])

    class _Store:
        def visible_objects(self):
            return [
                {"id": "line-a", "type": "line", "name": "A"},
                {"id": "line-b", "type": "line", "name": "B"},
            ]

    class _Harness(ChartEditorObjectListMixin):
        def __init__(self):
            self._object_list = QListWidget()
            self._generated_document_mode = True
            self._annotation_canvas = None
            self._syncing_object_list = False
            self._selected_figure_object_id = ""
            self._store = _Store()

        def _generated_store(self):
            return self._store

    editor = _Harness()
    editor._refresh_object_list()
    editor._object_list.item(1).setSelected(True)
    editor._object_list.item(2).setSelected(True)

    assert editor._object_list_selected_ids() == ("line-a", "line-b")


def test_chart_editor_reuses_object_list_helpers_from_object_list_mixin() -> None:
    assert ChartEditor._object_list_label is ChartEditorObjectListMixin._object_list_label
    assert ChartEditor._generated_figure_objects is ChartEditorObjectListMixin._generated_figure_objects
    assert ChartEditor._figure_object_list_label is ChartEditorObjectListMixin._figure_object_list_label
    assert ChartEditor._reorderable_generated_figure_objects is ChartEditorObjectListMixin._reorderable_generated_figure_objects
    assert ChartEditor._refresh_object_list is ChartEditorObjectListMixin._refresh_object_list
    assert ChartEditor._rename_selected_generated_object is ChartEditorObjectListMixin._rename_selected_generated_object
    assert ChartEditor._soft_delete_selected_generated_object is ChartEditorObjectListMixin._soft_delete_selected_generated_object
    assert ChartEditor._restore_last_deleted_generated_object is ChartEditorObjectListMixin._restore_last_deleted_generated_object
    assert ChartEditor._move_selected_generated_object is ChartEditorObjectListMixin._move_selected_generated_object
    assert ChartEditor._on_object_list_selection_changed is ChartEditorObjectListMixin._on_object_list_selection_changed
    assert ChartEditor._on_object_list_item_changed is ChartEditorObjectListMixin._on_object_list_item_changed


def test_object_visibility_change_routes_through_edit_session_command():
    from polynexus.core.figure_edit_capabilities import EditResult
    from PySide6.QtWidgets import QApplication, QListWidget

    QApplication.instance() or QApplication([])

    class _Harness(ChartEditorObjectListMixin):
        def __init__(self):
            self._object_list = QListWidget()
            self._generated_document_mode = True
            self._syncing_object_list = False
            self.calls = []

        def _execute_edit(self, command):
            self.calls.append(command)
            return EditResult(True)

        def _refresh_object_list(self, selected_id=""):
            self.refreshed = selected_id

        def _show_generated_figure_document(self):
            self.rendered = True

    editor = _Harness()
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QListWidgetItem

    item = QListWidgetItem("Line")
    item.setData(Qt.UserRole, "line-a")
    item.setData(Qt.UserRole + 1, "figure_object")
    item.setCheckState(Qt.Unchecked)
    editor._object_list.addItem(item)
    editor._on_object_list_item_changed(item)

    assert editor.calls[-1].object_id == "line-a"
    assert editor.calls[-1].visible is False
