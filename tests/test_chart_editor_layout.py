import os
import warnings

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent, QPointF, QSize, Qt
from PySide6.QtGui import QColor, QImage, QKeyEvent, QMouseEvent, QPixmap
from PySide6.QtWidgets import QApplication

from polynexus.core.figure_document import save_generated_figure_document
from polynexus.gui.i18n import get_language, set_language, tr
from polynexus.gui.widgets.chart_editor import ChartEditor


def _app():
    return QApplication.instance() or QApplication([])


def _write_static_source(tmp_path):
    path = tmp_path / "figure.png"
    image = QImage(16, 16, QImage.Format_RGBA8888)
    image.fill(0xFFFFFFFF)
    assert image.save(str(path))
    return path


def test_editor_uses_canvas_first_inspector_layout():
    _app()
    editor = ChartEditor()

    assert editor._inspector_tabs.count() == 4
    assert [editor._inspector_tabs.tabText(i) for i in range(4)] == [
        tr("EDITOR_INSPECTOR_OBJECT"),
        tr("EDITOR_INSPECTOR_STYLE"),
        tr("EDITOR_INSPECTOR_ANNOTATION"),
        tr("EDITOR_INSPECTOR_EXPORT"),
    ]
    assert not editor._editor_header.isHidden()
    assert not editor._editor_status_bar.isHidden()

    editor.deleteLater()
    _app().processEvents()


def test_editor_shows_inspector_by_default_for_discoverable_controls():
    app = _app()
    editor = ChartEditor()
    editor.resize(1100, 720)
    editor.show()
    app.processEvents()

    assert not editor._inspector_panel.isHidden()
    assert editor._btn_header_inspector.isChecked()

    editor.close()
    editor.deleteLater()
    app.processEvents()


def test_editor_surface_exposes_readable_tools_and_non_scrolling_inspector_tabs():
    _app()
    editor = ChartEditor()

    assert editor._editor_toolbar.toolButtonStyle() == Qt.ToolButtonTextUnderIcon
    assert editor._editor_toolbar.width() >= 72
    assert not editor._inspector_tabs.tabBar().usesScrollButtons()

    editor.deleteLater()
    _app().processEvents()


def test_object_tab_exposes_common_actions_next_to_layer_tree():
    _app()
    editor = ChartEditor()

    assert set(editor._object_action_buttons) >= {
        "visibility",
        "lock",
        "align",
        "distribute",
        "group",
        "ungroup",
        "delete",
    }

    editor.deleteLater()
    _app().processEvents()


def test_generated_object_mode_keeps_navigation_toolbar_from_stealing_canvas_gestures(
    tmp_path,
):
    _app()
    source = _write_static_source(tmp_path)
    save_generated_figure_document(
        str(source),
        figure_id="navigation-conflict",
        objects=[
            {
                "id": "line-1",
                "type": "line",
                "x1": 0.2,
                "y1": 0.2,
                "x2": 0.8,
                "y2": 0.8,
            }
        ],
    )
    editor = ChartEditor()
    editor.set_source_figure(str(source))

    assert editor._generated_document_mode
    assert editor._toolbar.isHidden()

    editor._toolbar.zoom()
    assert getattr(editor._toolbar.mode, "name", "") == "ZOOM"
    editor.set_tool("text")
    assert getattr(editor._toolbar.mode, "name", "") == "NONE"

    editor.deleteLater()
    _app().processEvents()


def test_editor_keeps_canvas_usable_at_narrow_window_width():
    app = _app()
    editor = ChartEditor()
    editor.resize(640, 520)
    editor.show()
    app.processEvents()

    assert editor._editor_splitter.sizes()[0] >= 220

    editor.close()
    editor.deleteLater()
    app.processEvents()


def test_inspector_drawer_restores_canvas_width_after_manual_close():
    app = _app()
    editor = ChartEditor()
    editor.resize(1100, 720)
    editor.show()
    app.processEvents()

    expanded_canvas_width = editor._canvas.width()
    editor._btn_header_inspector.click()
    app.processEvents()

    assert editor._inspector_panel.isHidden()
    assert editor._canvas.width() > expanded_canvas_width

    editor._set_inspector_collapsed(False)
    app.processEvents()

    assert not editor._inspector_panel.isHidden()
    assert editor._canvas.width() < expanded_canvas_width + 1
    editor.close()
    editor.deleteLater()
    app.processEvents()


def test_header_inspector_toggle_controls_drawer():
    app = _app()
    editor = ChartEditor()
    editor.resize(1100, 720)
    editor.show()
    app.processEvents()

    assert not editor._inspector_panel.isHidden()
    editor._btn_header_inspector.click()
    app.processEvents()
    assert editor._inspector_panel.isHidden()

    editor._btn_header_inspector.click()
    app.processEvents()
    assert not editor._inspector_panel.isHidden()
    editor.close()
    editor.deleteLater()
    app.processEvents()


def test_figure_size_change_keeps_live_canvas_pixel_size():
    app = _app()
    editor = ChartEditor()
    editor.set_figure_generator(lambda axis: axis.plot([0, 1], [0, 1]))
    editor.resize(1100, 720)
    editor.show()
    app.processEvents()

    before = editor._canvas.get_width_height()
    editor._figsize_cb.setCurrentText("Small (4in)")
    app.processEvents()

    assert editor._canvas.get_width_height() == before
    editor._set_editor_dirty(False)
    editor.close()
    editor.deleteLater()
    app.processEvents()


def test_inspector_starts_expanded_and_selection_does_not_change_visibility():
    app = _app()
    editor = ChartEditor()
    editor.resize(1100, 720)
    editor.show()
    app.processEvents()

    assert not editor._inspector_panel.isHidden()
    editor._on_generated_selection_changed("missing", "canvas")
    app.processEvents()
    assert not editor._inspector_panel.isHidden()

    editor._btn_header_inspector.click()
    app.processEvents()
    assert editor._inspector_panel.isHidden()

    editor._on_generated_selection_changed("missing", "canvas")
    app.processEvents()
    assert editor._inspector_panel.isHidden()

    editor._btn_header_inspector.click()
    app.processEvents()
    assert not editor._inspector_panel.isHidden()

    editor._on_generated_selection_changed("missing", "canvas")
    app.processEvents()
    assert not editor._inspector_panel.isHidden()
    editor.close()
    editor.deleteLater()
    app.processEvents()


def test_annotation_inspector_hides_legacy_creation_actions_but_keeps_advanced_editing():
    _app()
    editor = ChartEditor()

    assert editor._btn_annotation_add_text.isHidden()
    assert editor._btn_annotation_add_line.isHidden()
    assert editor._btn_annotation_add_arrow.isHidden()
    assert editor._btn_annotation_add_rect.isHidden()
    assert editor._btn_annotation_add_highlight.isHidden()
    assert editor._btn_annotation_crop.isHidden()
    assert editor._btn_annotation_copy.isHidden()
    assert editor._btn_annotation_paste.isHidden()
    assert not editor._btn_annotation_update_text.isHidden()
    assert not editor._btn_annotation_delete.isHidden()
    assert not editor._btn_annotation_front.isHidden()
    assert not editor._btn_annotation_back.isHidden()

    editor.deleteLater()
    _app().processEvents()


def test_escape_cancels_generated_draw_without_creating_an_object():
    _app()
    editor = ChartEditor()
    editor._generated_document_mode = True
    editor._figure_document = {"mode": "object", "objects": []}
    editor._reset_edit_session_from_document(editor._figure_document)
    assert editor.set_tool("line") is True
    editor._generated_draw_start_data = (1.0, 2.0)
    editor._generated_draw_start_display = (20.0, 30.0)

    event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)

    assert editor.eventFilter(editor._canvas, event) is True
    assert event.isAccepted()
    assert editor._generated_draw_start_data is None
    assert editor._generated_draw_start_display is None
    assert editor._generated_draw_tool == "select"
    assert editor._figure_document["objects"] == []
    assert not editor._inspector_panel.isHidden()

    editor.deleteLater()
    _app().processEvents()


def test_context_toolbar_has_stable_actions_and_retranslates():
    _app()
    editor = ChartEditor()

    assert editor._editor_toolbar.orientation() == Qt.Vertical
    assert editor._editor_toolbar.parentWidget() is editor._canvas_tool_shell
    assert editor._editor_toolbar.toolButtonStyle() == Qt.ToolButtonTextUnderIcon
    assert editor._editor_toolbar.iconSize() == QSize(20, 20)
    assert editor._editor_toolbar.action_ids() == [
        "select",
        "text",
        "line",
        "arrow",
        "curve",
        "rectangle",
        "undo",
        "redo",
        "export",
    ]
    for action_id in editor._editor_toolbar.action_ids():
        action = editor._editor_toolbar.action(action_id)
        button = editor._editor_toolbar.widgetForAction(action)
        assert not action.icon().isNull()
        assert action.toolTip() == action.text()
        assert button.accessibleName() == action.text()

    previous = get_language()
    try:
        set_language("en")
        editor.retranslate()
        assert editor._editor_toolbar.action("select").text() == "Select"
        assert editor._editor_toolbar.action("select").toolTip() == "Select"
        assert (
            editor._editor_toolbar.widgetForAction(
                editor._editor_toolbar.action("select")
            ).accessibleName()
            == "Select"
        )
        assert editor._editor_toolbar.action("export").text() == "Export"
        assert not editor._editor_toolbar.action("select").icon().isNull()

        set_language("zh")
        editor.retranslate()
        assert editor._editor_toolbar.action("select").text() != "Select"
        assert (
            editor._editor_toolbar.action("select").toolTip()
            == editor._editor_toolbar.action("select").text()
        )
        assert (
            editor._editor_toolbar.widgetForAction(
                editor._editor_toolbar.action("select")
            ).accessibleName()
            == editor._editor_toolbar.action("select").text()
        )
        assert editor._editor_toolbar.action("export").text() != "Export"
        assert not editor._editor_toolbar.action("select").icon().isNull()
    finally:
        set_language(previous)
        editor.retranslate()

    editor.deleteLater()
    _app().processEvents()


def test_context_toolbar_marks_the_checked_tool_button_with_an_accent_property():
    _app()
    editor = ChartEditor()
    editor._generated_document_mode = True
    editor._figure_document = {"mode": "object", "objects": []}
    editor._reset_edit_session_from_document(editor._figure_document)
    editor._sync_editor_toolbar()

    select_button = editor._editor_toolbar.widgetForAction(
        editor._editor_toolbar.action("select")
    )
    line_button = editor._editor_toolbar.widgetForAction(
        editor._editor_toolbar.action("line")
    )

    assert select_button.property("editor-tool-active") is True
    assert line_button.property("editor-tool-active") is False

    assert editor.set_tool("line") is True

    assert select_button.property("editor-tool-active") is False
    assert line_button.property("editor-tool-active") is True

    editor.deleteLater()
    _app().processEvents()


def test_static_tool_change_updates_the_checked_tool_button(tmp_path):
    _app()
    editor = ChartEditor()
    previous = get_language()
    try:
        set_language("en")
        editor.set_source_figure(str(_write_static_source(tmp_path)))
        rectangle_button = editor._editor_toolbar.widgetForAction(
            editor._editor_toolbar.action("rectangle")
        )

        editor._on_add_rectangle_annotation()
        assert rectangle_button.property("editor-tool-active") is True
        assert "esc" in editor._status_label.text().lower()
    finally:
        set_language(previous)
        editor.deleteLater()
        _app().processEvents()


@pytest.mark.parametrize(
    ("method_name", "tool"),
    (
        ("_on_add_rectangle_annotation", "rectangle"),
        ("_on_add_line_annotation", "line"),
        ("_on_add_arrow_annotation", "arrow"),
        ("_on_add_highlight_annotation", "highlight"),
        ("_on_crop_annotation_canvas", "crop"),
    ),
)
def test_static_annotation_tool_actions_route_through_editor_set_tool(
    tmp_path, monkeypatch, method_name, tool
):
    _app()
    editor = ChartEditor()
    editor.set_source_figure(str(_write_static_source(tmp_path)))
    calls = []
    original_set_tool = editor.set_tool

    def set_tool(value):
        calls.append(value)
        return original_set_tool(value)

    monkeypatch.setattr(editor, "set_tool", set_tool)
    getattr(editor, method_name)()

    assert calls == [tool]
    assert editor._annotation_canvas.current_tool() == tool

    editor.deleteLater()
    _app().processEvents()


def test_new_source_or_generator_clears_the_previous_tool_hint(tmp_path):
    _app()
    editor = ChartEditor()
    editor._generated_document_mode = True
    editor._figure_document = {"mode": "object", "objects": []}
    editor._reset_edit_session_from_document(editor._figure_document)
    editor._sync_editor_toolbar()

    assert editor.set_tool("line") is True
    assert editor._tool_status_text

    editor.set_figure_generator(lambda axis: axis.plot([0, 1], [0, 1]))
    assert editor._tool_status_text == ""

    editor.set_tool("line")
    editor.set_source_figure(str(_write_static_source(tmp_path)))
    assert editor._tool_status_text == ""

    editor.deleteLater()
    _app().processEvents()


def test_static_annotation_selection_updates_the_editor_status_hint(tmp_path):
    _app()
    editor = ChartEditor()
    previous = get_language()
    try:
        set_language("en")
        editor.set_source_figure(str(_write_static_source(tmp_path)))

        annotation_id = editor._annotation_canvas.add_rectangle_annotation(0.1, 0.1, 0.4, 0.3)
        editor._annotation_canvas.select_annotation(annotation_id)

        assert "drag" in editor._status_label.text().lower()
        assert "handle" in editor._status_label.text().lower()
        assert "esc" in editor._status_label.text().lower()
    finally:
        set_language(previous)
        editor.deleteLater()
        _app().processEvents()


def test_drag_status_has_priority_over_selection_and_tool_hints():
    _app()
    editor = ChartEditor()
    editor._generated_document_mode = True
    editor._figure_document = {
        "mode": "object",
        "objects": [
            {"id": "line-1", "type": "line", "x1": 0.1, "y1": 0.2, "x2": 0.8, "y2": 0.9}
        ],
    }
    editor._reset_edit_session_from_document(editor._figure_document)

    editor._set_generated_drag_status("line-1", {"kind": "line-body"})
    drag_status = editor._status_label.text()
    editor._set_editor_selection_hint("line", "Line")
    editor._set_editor_tool_hint("rectangle")

    assert drag_status
    assert editor._status_label.text() == drag_status

    editor.deleteLater()
    _app().processEvents()


def test_cancel_status_has_priority_over_restore_selection_and_tool_hints():
    _app()
    editor = ChartEditor()
    editor._generated_document_mode = True
    editor._figure_document = {"mode": "object", "objects": []}
    editor._reset_edit_session_from_document(editor._figure_document)
    editor._sync_editor_toolbar()
    editor.set_tool("line")
    editor._generated_draw_start_data = (0.2, 0.3)

    assert editor._cancel_active_draw() is True
    cancel_status = editor._status_label.text()
    editor._restore_generated_status_hint()
    editor._set_editor_selection_hint("line", "Line")
    editor._set_editor_tool_hint("rectangle")

    assert cancel_status
    assert editor._status_label.text() == cancel_status

    editor.deleteLater()
    _app().processEvents()


def test_static_escape_cancel_resets_editor_toolbar_tool_state(tmp_path):
    _app()
    editor = ChartEditor()
    editor.set_source_figure(str(_write_static_source(tmp_path)))
    editor.set_tool("rectangle")
    editor._annotation_canvas._draw_start = QPointF(2.0, 3.0)

    select_button = editor._editor_toolbar.widgetForAction(
        editor._editor_toolbar.action("select")
    )
    rectangle_button = editor._editor_toolbar.widgetForAction(
        editor._editor_toolbar.action("rectangle")
    )
    assert rectangle_button.property("editor-tool-active") is True

    assert editor._cancel_active_draw() is True

    assert editor._annotation_canvas.current_tool() == "select"
    assert select_button.property("editor-tool-active") is True
    assert rectangle_button.property("editor-tool-active") is False

    editor.deleteLater()
    _app().processEvents()


def test_static_real_escape_cancel_syncs_editor_toolbar_and_status(tmp_path):
    app = _app()
    previous = get_language()
    try:
        set_language("en")
        editor = ChartEditor()
        editor.set_source_figure(str(_write_static_source(tmp_path)))
        canvas = editor._annotation_canvas
        canvas.set_zoom_100()
        assert editor.set_tool("rectangle") is True

        viewport = canvas._view.viewport()
        start = QPointF(canvas._view.mapFromScene(QPointF(2.0, 2.0)))
        global_start = QPointF(viewport.mapToGlobal(start.toPoint()))
        press = QMouseEvent(
            QEvent.MouseButtonPress,
            start,
            start,
            global_start,
            Qt.LeftButton,
            Qt.LeftButton,
            Qt.NoModifier,
        )
        app.sendEvent(viewport, press)
        assert canvas._draw_start is not None

        escape = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        app.sendEvent(canvas._view, escape)
        app.processEvents()

        select_button = editor._editor_toolbar.widgetForAction(
            editor._editor_toolbar.action("select")
        )
        rectangle_button = editor._editor_toolbar.widgetForAction(
            editor._editor_toolbar.action("rectangle")
        )
        assert escape.isAccepted()
        assert canvas.current_tool() == "select"
        assert select_button.property("editor-tool-active") is True
        assert rectangle_button.property("editor-tool-active") is False
        assert editor._status_label.text() == tr("EDITOR_DRAW_CANCELLED")
    finally:
        set_language(previous)
        editor.deleteLater()
        app.processEvents()


def test_object_and_static_modes_update_header_and_inspector(tmp_path):
    _app()
    editor = ChartEditor()
    editor.set_figure_generator(lambda axis: axis.plot([0, 1], [0, 1]))
    assert editor._mode_badge.text() == tr("EDITOR_MODE_OBJECT")
    assert editor._inspector_tabs.currentIndex() == 0

    editor.set_source_figure(str(_write_static_source(tmp_path)))
    assert editor._mode_badge.text() == tr("EDITOR_MODE_STATIC")
    assert editor._inspector_tabs.currentIndex() == 2
    assert editor._source_title_label.text()

    editor.deleteLater()
    _app().processEvents()


def test_edit_marks_dirty_and_successful_save_clears_it(monkeypatch, tmp_path):
    _app()
    editor = ChartEditor()
    editor.set_figure_generator(lambda axis: axis.plot([0, 1], [0, 1]))

    assert editor._dirty_badge.text() == tr("EDITOR_STATE_SAVED")
    editor._on_grid_toggled(False)
    assert editor._dirty_badge.text() == tr("EDITOR_STATE_UNSAVED")

    monkeypatch.setattr(
        editor,
        "_save_to_path",
        lambda path: editor.figure_saved.emit(str(path)),
    )
    editor._target_path = str(tmp_path / "figure.svg")
    editor.save_to_target()
    assert editor._dirty_badge.text() == tr("EDITOR_STATE_SAVED")

    editor.deleteLater()
    _app().processEvents()


def test_static_style_edit_marks_dirty(tmp_path):
    _app()
    editor = ChartEditor()
    editor.set_source_figure(str(_write_static_source(tmp_path)))
    assert editor._dirty_badge.text() == tr("EDITOR_STATE_SAVED")

    editor._title_edit.setText("Edited")
    _app().processEvents()

    assert editor._dirty_badge.text() == tr("EDITOR_STATE_UNSAVED")
    editor.deleteLater()
    _app().processEvents()


def test_disabling_grid_does_not_emit_matplotlib_warning():
    _app()
    editor = ChartEditor()
    editor.set_figure_generator(lambda axis: axis.plot([0, 1], [0, 1]))

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        editor._on_grid_toggled(False)

    assert not any("grid() is false" in str(item.message) for item in caught)
    editor.deleteLater()
    _app().processEvents()


def test_refresh_clears_selection_when_selected_object_disappears(tmp_path):
    _app()
    figure_path = tmp_path / "generated.png"
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))
    save_generated_figure_document(
        str(figure_path),
        technique="saxs",
        figure_id="generated",
        objects=[
            {
                "id": "series-a",
                "type": "plot_series",
                "name": "A",
                "data": {"x": [0.1, 0.2], "y": [1.0, 2.0]},
            }
        ],
    )
    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._refresh_object_list()
    editor._object_list.setCurrentRow(1)
    selected_id = editor._object_list.currentItem().data(Qt.UserRole)
    editor._generated_store().soft_delete(selected_id)
    editor._refresh_object_list()

    current = editor._object_list.currentItem()
    assert current is None or current.data(Qt.UserRole) == "__background__"
    assert editor._inspector_tabs.isEnabled()

    editor.deleteLater()
    _app().processEvents()


def test_layout_retranslates_tabs_header_and_accessible_names():
    _app()
    editor = ChartEditor()
    previous = get_language()
    try:
        set_language("en")
        editor.retranslate()
        assert editor._inspector_tabs.tabText(0) == "Object"
        assert editor._btn_header_save.text() == "Save Edits"
        assert editor._btn_header_export.text() == "Export"
        assert editor._status_label.accessibleName() == "Editor status"
        assert editor._inspector_tabs.accessibleName() == "Editor Inspector"
    finally:
        set_language(previous)
        editor.retranslate()

    editor.deleteLater()
    _app().processEvents()
