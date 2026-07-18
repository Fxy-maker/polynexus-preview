import os
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from matplotlib.backend_bases import MouseEvent
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from polynexus.core.figure_document import save_generated_figure_document
from polynexus.core.figure_edit_commands import UpdateGeometryCommand
from polynexus.gui.widgets.chart_editor import ChartEditor


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


def make_static_editor(tmp_path, source=None):
    path = Path(source or (tmp_path / "source.png"))
    if source is None:
        image = QImage(160, 100, QImage.Format_RGBA8888)
        image.fill(QColor("white"))
        assert image.save(str(path))
    editor = ChartEditor()
    editor.set_source_figure(str(path))
    return editor


def make_generated_editor(tmp_path):
    path = tmp_path / "generated.png"
    image = QImage(160, 100, QImage.Format_RGBA8888)
    image.fill(QColor("white"))
    assert image.save(str(path))
    save_generated_figure_document(
        str(path),
        figure_id="generated",
        objects=[
            {
                "id": "line-1",
                "type": "line",
                "name": "Line 01",
                "x1": 0.1,
                "y1": 0.2,
                "x2": 0.8,
                "y2": 0.9,
                "style": {
                    "color": "#000000",
                    "line_width": 1.0,
                    "line_style": "-",
                },
            }
        ],
    )
    editor = ChartEditor()
    editor.generated_line_path = str(path)
    editor.set_source_figure(str(path))
    return editor


def make_capability_editor(tmp_path):
    path = tmp_path / "capabilities.png"
    image = QImage(160, 100, QImage.Format_RGBA8888)
    image.fill(QColor("white"))
    assert image.save(str(path))
    save_generated_figure_document(
        str(path),
        figure_id="capabilities",
        objects=[
            {
                "id": "line-1",
                "type": "line",
                "name": "Line 01",
                "x1": 0.1,
                "y1": 0.2,
                "x2": 0.8,
                "y2": 0.9,
                "style": {"color": "#000000", "line_width": 1.0},
            },
            {
                "id": "text-1",
                "type": "text",
                "name": "Label",
                "text": "Label",
                "bounds": {"x": 0.2, "y": 0.3, "width": 0.2, "height": 0.1},
                "style": {"color": "#111111", "font_size": 12},
            },
        ],
    )
    editor = ChartEditor()
    editor.set_source_figure(str(path))
    return editor


@pytest.fixture
def editor(tmp_path, app):
    return make_generated_editor(tmp_path)


def test_selected_generated_line_color_update_reaches_document(editor):
    editor._select_generated_object("line-1", "list")
    editor._annotation_color_edit.setText("#0072B2")
    editor._btn_annotation_apply_style.click()

    assert editor._generated_store().get("line-1")["style"]["color"] == "#0072B2"
    assert editor._last_edit_result.changed is True


def test_generated_style_and_geometry_share_one_edit_history(editor):
    editor._select_generated_object("line-1", "list")
    editor._annotation_color_edit.setText("#0072B2")
    editor._btn_annotation_apply_style.click()
    before_geometry = editor._generated_store().get("line-1")["x1"]

    editor._execute_edit(UpdateGeometryCommand("line-1", {"x1": 0.25}))
    assert len(editor._edit_session.history) == 2

    editor._on_annotation_undo()
    assert editor._generated_store().get("line-1")["x1"] == before_geometry
    assert editor._generated_store().get("line-1")["style"]["color"] == "#0072B2"

    editor._on_annotation_undo()
    assert editor._generated_store().get("line-1")["style"]["color"] == "#000000"


def test_static_text_annotation_round_trips_through_one_history(tmp_path, app):
    editor = make_static_editor(tmp_path)
    editor._annotation_text_edit.setText("Peak")
    editor._btn_annotation_add_text.click()
    annotation_id = editor._annotation_canvas.selected_annotation_id()
    assert editor._edit_session.can_undo is True

    editor._annotation_text_edit.setText("Peak value")
    editor._btn_annotation_update_text.click()
    assert editor._annotation_canvas.selected_annotation()["text"] == "Peak value"
    editor._on_annotation_undo()
    assert editor._annotation_canvas.selected_annotation()["text"] == "Peak"
    editor._on_annotation_redo()
    assert editor._annotation_canvas.selected_annotation()["text"] == "Peak value"

    target = tmp_path / "edited.png"
    editor._save_to_path(str(target))
    reloaded = make_static_editor(tmp_path, source=target)
    assert reloaded._annotation_canvas.annotation_state()[0]["id"] == annotation_id
    assert reloaded._annotation_canvas.annotation_state()[0]["text"] == "Peak value"


def test_invalid_color_keeps_object_and_history_unchanged(editor):
    editor._select_generated_object("line-1", "list")
    before = deepcopy(editor._generated_store().get("line-1"))
    editor._annotation_color_edit.setText("not-a-color")
    editor._btn_annotation_apply_style.click()

    assert editor._generated_store().get("line-1") == before
    assert "invalid" in editor._status_label.text().lower()


def test_inspector_controls_follow_session_capabilities_for_line_text_and_background(
    tmp_path, app
):
    editor = make_capability_editor(tmp_path)

    editor._select_generated_object("line-1", "list")
    assert editor._edit_session.selection.object_id == "line-1"
    assert editor._annotation_color_edit.isEnabled()
    assert editor._annotation_line_width_spin.isEnabled()
    assert editor._annotation_line_style_combo.isEnabled()
    assert not editor._annotation_marker_combo.isEnabled()
    assert not editor._annotation_text_edit.isEnabled()

    editor._select_generated_object("text-1", "list")
    assert editor._edit_session.selection.object_id == "text-1"
    assert editor._annotation_color_edit.isEnabled()
    assert editor._annotation_font_size_spin.isEnabled()
    assert editor._annotation_text_edit.isEnabled()
    assert not editor._annotation_line_width_spin.isEnabled()
    assert not editor._annotation_line_style_combo.isEnabled()

    static_editor = make_static_editor(tmp_path)
    static_editor._object_list.setCurrentRow(0)
    static_editor._sync_inspector_capabilities()
    assert static_editor._selected_canonical_object()["type"] == "image_background"
    assert not static_editor._annotation_color_edit.isEnabled()
    assert not static_editor._annotation_font_size_spin.isEnabled()
    assert not static_editor._annotation_x_spin.isEnabled()

    editor.deleteLater()
    static_editor.deleteLater()
    app.processEvents()


def test_generated_editor_toolbar_can_start_annotation_tools(tmp_path, app):
    editor = make_generated_editor(tmp_path)

    for tool in ("text", "line", "arrow", "rectangle"):
        action = editor._editor_toolbar.action(tool)
        assert action.isEnabled(), f"generated canvas tool {tool!r} is disabled"
        action.trigger()
        assert editor._generated_draw_tool == tool
        if tool == "text":
            assert editor._annotation_text_edit.isEnabled()
        else:
            assert editor._annotation_color_edit.isEnabled()
            assert editor._annotation_line_width_spin.isEnabled()
            assert editor._annotation_line_style_combo.isEnabled()

    editor.deleteLater()
    app.processEvents()


def test_generated_text_tool_adds_text_object_to_edit_session(tmp_path, app):
    editor = make_generated_editor(tmp_path)
    editor.set_tool("text")
    editor._annotation_text_edit.setText("Peak")

    axis = editor._figure.axes[0]
    event = MouseEvent(
        "button_press_event",
        editor._canvas,
        *axis.transData.transform((0.5, 0.5)),
        button=1,
    )
    event.inaxes = axis
    event.xdata = 0.5
    event.ydata = 0.5
    editor._on_generated_button_press(event)

    created = [
        item
        for item in editor._figure_document.get("objects", [])
        if item.get("type") == "text" and item.get("text") == "Peak"
    ]
    assert len(created) == 1
    assert editor._selected_figure_object_id == created[0]["id"]
    assert editor._generated_draw_tool == "select"

    target = tmp_path / "edited.png"
    editor._save_to_path(str(target))
    reloaded = ChartEditor()
    reloaded.set_source_figure(str(target))
    assert any(
        item.get("type") == "text" and item.get("text") == "Peak"
        for item in reloaded._figure_document.get("objects", [])
    )

    editor.deleteLater()
    reloaded.deleteLater()
    app.processEvents()


@pytest.mark.parametrize("tool", ("line", "arrow", "rectangle"))
def test_generated_shape_tools_add_objects_after_canvas_drag(tmp_path, app, tool):
    editor = make_generated_editor(tmp_path)
    editor.set_tool(tool)
    axis = editor._figure.axes[0]

    def event(name, x_value, y_value):
        event = MouseEvent(
            name,
            editor._canvas,
            *axis.transData.transform((x_value, y_value)),
            button=1,
        )
        event.inaxes = axis
        event.xdata = x_value
        event.ydata = y_value
        return event

    editor._on_generated_button_press(event("button_press_event", 0.2, 0.2))
    editor._on_generated_button_release(event("button_release_event", 0.8, 0.8))

    created = [
        item
        for item in editor._figure_document.get("objects", [])
        if item.get("type") == tool and item.get("id") != "line-1"
    ]
    assert len(created) == 1
    assert editor._selected_figure_object_id == created[0]["id"]
    assert editor._generated_draw_tool == "select"

    editor.deleteLater()
    app.processEvents()


def test_formal_generated_document_accepts_text_tool(built_ir_document, tmp_path, app):
    from polynexus.core.figure_document import load_figure_document

    run_root, document_path, _document = built_ir_document
    source = tmp_path / "formal.png"
    image = QImage(160, 100, QImage.Format_RGBA8888)
    image.fill(QColor("white"))
    assert image.save(str(source))
    entry = SimpleNamespace(
        run_root=str(run_root),
        document_path=str(document_path),
        figure_id="ir.frame.spectrum.001",
        title="Formal figure",
        editable_path=str(source),
        primary_path=str(source),
        preview_path=str(source),
        state="object_editing",
    )
    editor = ChartEditor()
    editor.set_source_figure(str(source), source_entry_context=entry)

    assert editor._generated_document_mode is True
    assert load_figure_document(str(document_path)).get("mode") == "object"
    editor._title_edit.setText("Edited title")
    app.processEvents()
    assert editor._figure.axes[0].get_title() == "Edited title"
    assert editor._editor_dirty is True
    editor._colour_cb.setCurrentText("Warm")
    app.processEvents()
    assert editor._figure.axes[0].lines[0].get_color() == "#8B0000"
    editor._grid_cb.setChecked(False)
    app.processEvents()
    assert not any(gridline.get_visible() for gridline in editor._figure.axes[0].get_xgridlines())

    editor.set_tool("text")
    editor._annotation_text_edit.setText("Peak")
    axis = editor._figure.axes[0]
    event = MouseEvent(
        "button_press_event",
        editor._canvas,
        *axis.transData.transform((1750.0, 0.2)),
        button=1,
    )
    event.inaxes = axis
    event.xdata = 1750.0
    event.ydata = 0.2
    editor._on_generated_button_press(event)

    assert any(
        item.get("type") == "text" and item.get("text") == "Peak"
        for item in editor._figure_document.get("objects", [])
    )

    editor.deleteLater()
    app.processEvents()
