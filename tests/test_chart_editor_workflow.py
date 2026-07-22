import os
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from matplotlib.backend_bases import MouseEvent
from matplotlib.figure import Figure
from PySide6.QtCore import QEvent, QPointF, QRect, Qt
from PySide6.QtGui import QColor, QImage, QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QApplication

from polynexus.core.figure_document import save_generated_figure_document
from polynexus.core.figure_edit_commands import (
    AddObjectCommand,
    UpdateGeometryCommand,
    UpdateStyleCommand,
)
from polynexus.gui.figure_render_adapter import FigureRenderAdapter
from polynexus.gui.i18n import tr
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


def test_editor_surfaces_corrupt_document_warning(monkeypatch, tmp_path, app):
    from polynexus.gui.widgets import chart_editor as module

    source = tmp_path / "corrupt.png"
    image = QImage(160, 100, QImage.Format_RGBA8888)
    image.fill(QColor("white"))
    assert image.save(str(source))
    monkeypatch.setattr(
        module,
        "load_figure_document_report",
        lambda _path: SimpleNamespace(
            status="corrupt",
            document={},
            message="Figure document JSON is invalid.",
            error_type="json",
        ),
    )

    editor = ChartEditor()
    editor.set_source_figure(str(source))

    assert "Figure document JSON is invalid." in editor._status_label.text()


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


def test_static_text_drag_commits_one_box_after_inline_text(tmp_path, app):
    editor = make_static_editor(tmp_path)
    requests = []
    editor._annotation_canvas.text_entry_requested.connect(requests.append)

    assert editor._annotation_canvas.set_tool("text") is True
    editor._annotation_canvas._finish_mouse_draw(QPointF(16, 10), QPointF(96, 30))

    assert len(requests) == 1
    assert [
        item
        for item in editor._figure_document["objects"]
        if item.get("type") == "text"
    ] == []
    assert editor._commit_inline_text_entry("Peak region") is True

    text = next(
        item for item in editor._figure_document["objects"] if item.get("type") == "text"
    )
    assert text["type"] == "text"
    assert text["bounds"]["width"] == 0.5
    assert text["bounds"]["height"] == 0.2
    assert editor._edit_session.can_undo is True
    editor._on_annotation_undo()
    assert [
        item
        for item in editor._figure_document["objects"]
        if item.get("type") == "text"
    ] == []


def test_static_line_drag_commits_one_command_and_is_undoable(tmp_path, app):
    editor = make_static_editor(tmp_path)

    assert editor._annotation_canvas.set_tool("line") is True
    editor._annotation_canvas._finish_mouse_draw(QPointF(16, 10), QPointF(96, 30))

    line = next(
        item for item in editor._figure_document["objects"] if item.get("type") == "line"
    )
    assert line["bounds"] == {"x1": 0.1, "y1": 0.1, "x2": 0.6, "y2": 0.3}
    assert editor._edit_session.can_undo is True
    editor._on_annotation_undo()
    assert not any(item.get("type") == "line" for item in editor._figure_document["objects"])


def test_generated_selection_preserves_manual_axes_limits(editor):
    axes = editor._figure.axes[0]
    axes.set_xlim(-2.0, 3.0)
    axes.set_ylim(-4.0, 5.0)
    before = (tuple(axes.get_xlim()), tuple(axes.get_ylim()))

    editor._select_generated_object("line-1", "canvas")

    axes = editor._figure.axes[0]
    assert tuple(axes.get_xlim()) == before[0]
    assert tuple(axes.get_ylim()) == before[1]


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
        assert not editor._context_style_bar.isHidden()
        assert not editor._inspector_panel.isHidden()
        if tool == "text":
            assert not editor._context_font_size.isHidden()
            assert editor._context_line_width.isHidden()
        else:
            assert not editor._context_color.isHidden()
            assert not editor._context_line_width.isHidden()
            assert not editor._context_line_style.isHidden()

    editor.deleteLater()
    app.processEvents()


def test_generated_text_tool_waits_for_inline_text_before_adding_object(tmp_path, app):
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
    editor._on_generated_button_release(event)

    created = [
        item
        for item in editor._figure_document.get("objects", [])
        if item.get("type") == "text"
    ]
    assert created == []
    assert editor._commit_inline_text_entry("Peak") is True
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


def test_generated_text_drag_commits_persisted_box_geometry(tmp_path, app):
    editor = make_generated_editor(tmp_path)

    editor._begin_generated_text_box((0.2, 0.3), (0.5, 0.5), QRect(20, 20, 100, 28))

    assert not any(item.get("type") == "text" for item in editor._figure_document["objects"])
    assert editor._commit_inline_text_entry("Peak region") is True
    text = next(item for item in editor._figure_document["objects"] if item.get("type") == "text")
    assert text["width"] == 0.3
    assert text["height"] == 0.2


def test_generated_text_box_creation_marks_axes_coordinate_space(tmp_path, app):
    editor = make_generated_editor(tmp_path)

    editor._begin_generated_text_box((0.2, 0.3), (0.5, 0.5), QRect(20, 20, 100, 28))

    assert editor._commit_inline_text_entry("Viewport note") is True
    text = next(
        item
        for item in editor._figure_document["objects"]
        if item.get("type") == "text"
    )
    assert text["coordinate_space"] == "axes"
    assert text["bounds"] == {
        "x": pytest.approx(0.2),
        "y": pytest.approx(0.3),
        "width": pytest.approx(0.3),
        "height": pytest.approx(0.2),
    }

    editor.deleteLater()
    app.processEvents()


@pytest.mark.parametrize(
    ("object_id", "object_payload", "point"),
    (
        (
            "movable-text",
            {"id": "movable-text", "type": "text", "x": 0.25, "y": 0.35, "text": "Peak"},
            (0.25, 0.35),
        ),
        (
            "movable-rectangle",
            {
                "id": "movable-rectangle",
                "type": "rectangle",
                "x": 0.25,
                "y": 0.35,
                "width": 0.3,
                "height": 0.2,
            },
            (0.4, 0.45),
        ),
    ),
)
def test_generated_text_and_rectangle_body_presses_start_move_drag(
    tmp_path, app, object_id, object_payload, point
):
    editor = make_generated_editor(tmp_path)
    editor._execute_edit(AddObjectCommand(object_payload))
    editor._show_generated_figure_document()
    editor._select_generated_object(object_id, "list")
    axis = editor._figure.axes[0]
    event = MouseEvent(
        "button_press_event",
        editor._canvas,
        *axis.transData.transform(point),
        button=1,
    )
    event.inaxes = axis
    event.xdata, event.ydata = point

    target = editor._generated_drag_state_for_press(event, object_id)

    assert target is not None
    assert target["kind"] == "body"

    editor.deleteLater()
    app.processEvents()


def test_generated_axes_text_body_press_uses_axes_coordinates(tmp_path, app):
    editor = make_generated_editor(tmp_path)
    editor._execute_edit(
        AddObjectCommand(
            {
                "id": "axes-text",
                "type": "text",
                "coordinate_space": "axes",
                "bounds": {"x": 0.2, "y": 0.3, "width": 0.3, "height": 0.15},
                "text": "Viewport",
            }
        )
    )
    editor._show_generated_figure_document()
    editor._select_generated_object("axes-text", "list")
    axis = editor._figure.axes[0]
    axis.set_yscale("log")
    editor._canvas.draw()
    text_artist = editor._figure_render_adapter.artists_for_object_id("axes-text")[0]
    extent = text_artist.get_window_extent(editor._canvas.get_renderer())
    press_x = (float(extent.x0) + float(extent.x1)) / 2.0
    press_y = (float(extent.y0) + float(extent.y1)) / 2.0
    event = MouseEvent(
        "button_press_event",
        editor._canvas,
        press_x,
        press_y,
        button=1,
    )
    event.inaxes = axis

    target = editor._generated_drag_state_for_press(event, "axes-text")

    assert target is not None
    assert target["kind"] == "body"
    expected_axes = axis.transAxes.inverted().transform((press_x, press_y))
    assert target["press_data"] == pytest.approx(expected_axes, abs=0.002)

    editor._activate_generated_drag_state(target, event)
    target["current_pixels"] = (float(event.x) + 20.0, float(event.y) + 20.0)
    assert editor._apply_generated_body_drag(
        "axes-text",
        target,
        0.4,
        0.42,
    ) is True
    preview = target["preview_geometry"]
    assert preview["x"] > 0.2
    assert preview["y"] > 0.3

    editor.deleteLater()
    app.processEvents()


def test_legacy_generated_text_converts_to_axes_box_when_saved(tmp_path, app):
    editor = make_generated_editor(tmp_path)
    editor._execute_edit(
        AddObjectCommand(
            {
                "id": "legacy-text",
                "type": "text",
                "x": 0.4,
                "y": 0.5,
                "text": "Legacy",
            }
        )
    )
    editor._show_generated_figure_document()

    saved = editor._generated_document_for_save()
    text = next(item for item in saved["objects"] if item.get("id") == "legacy-text")

    assert text["coordinate_space"] == "axes"
    assert text["bounds"]["width"] > 0.0
    assert text["bounds"]["height"] > 0.0
    assert text["x"] == text["bounds"]["x"]
    assert text["y"] == text["bounds"]["y"]

    editor.deleteLater()
    app.processEvents()


def test_generated_axes_text_inspector_edits_the_same_box_geometry(tmp_path, app):
    editor = make_generated_editor(tmp_path)
    editor._execute_edit(
        AddObjectCommand(
            {
                "id": "inspector-text",
                "type": "text",
                "coordinate_space": "axes",
                "bounds": {"x": 0.2, "y": 0.3, "width": 0.25, "height": 0.12},
                "text": "Inspector",
            }
        )
    )
    editor._show_generated_figure_document()
    editor._select_generated_object("inspector-text", "list")
    editor._annotation_x_spin.setValue(0.35)
    editor._annotation_y_spin.setValue(0.4)
    editor._annotation_w_spin.setValue(0.3)
    editor._annotation_h_spin.setValue(0.15)
    editor._update_selected_generated_object_geometry()

    text = editor._generated_figure_object_by_id("inspector-text")
    assert text["bounds"] == {
        "x": pytest.approx(0.35),
        "y": pytest.approx(0.4),
        "width": pytest.approx(0.3),
        "height": pytest.approx(0.15),
    }

    editor.deleteLater()
    app.processEvents()


def test_generated_curve_default_bend_is_not_a_fixed_shallow_offset(tmp_path, app):
    editor = make_generated_editor(tmp_path)
    assert editor._add_generated_tool_object("curve", (0.1, 0.5), (0.9, 0.5)) is True

    curve = next(
        item
        for item in editor._figure_document["objects"]
        if item.get("type") == "curve"
    )
    assert abs(float(curve["control_y"]) - 0.5) >= 0.25

    editor.deleteLater()
    app.processEvents()


@pytest.mark.parametrize(
    ("object_payload", "press_point", "release_point", "expected_keys"),
    (
        (
            {"id": "move-text", "type": "text", "x": 0.25, "y": 0.35, "text": "Peak"},
            (0.25, 0.35),
            (0.4, 0.5),
            {"x": 0.4, "y": 0.5},
        ),
        (
            {
                "id": "move-rectangle",
                "type": "rectangle",
                "x": 0.25,
                "y": 0.35,
                "width": 0.3,
                "height": 0.2,
            },
            (0.4, 0.45),
            (0.55, 0.6),
            {"x": 0.4, "y": 0.5},
        ),
    ),
)
def test_generated_body_drag_commits_one_geometry_command(
    tmp_path, app, object_payload, press_point, release_point, expected_keys
):
    editor = make_generated_editor(tmp_path)
    editor._execute_edit(AddObjectCommand(object_payload))
    editor._show_generated_figure_document()
    editor._select_generated_object(object_payload["id"], "list")
    axis = editor._figure.axes[0]

    def event(name, point):
        result = MouseEvent(
            name,
            editor._canvas,
            *axis.transData.transform(point),
            button=1,
        )
        result.inaxes = axis
        result.xdata, result.ydata = point
        return result

    history_before = len(editor._edit_session.history)
    editor._on_generated_button_press(event("button_press_event", press_point))
    editor._on_generated_mouse_move(event("motion_notify_event", release_point))
    editor._on_generated_button_release(event("button_release_event", release_point))

    moved = editor._generated_figure_object_by_id(object_payload["id"])
    assert {key: moved[key] for key in expected_keys} == expected_keys
    assert len(editor._edit_session.history) == history_before + 1

    editor._on_annotation_undo()
    restored = editor._generated_figure_object_by_id(object_payload["id"])
    assert restored["x"] == object_payload.get("x")
    assert restored["y"] == object_payload.get("y")
    editor._on_annotation_redo()
    redone = editor._generated_figure_object_by_id(object_payload["id"])
    assert redone["x"] == expected_keys["x"]
    assert redone["y"] == expected_keys["y"]

    editor.deleteLater()
    app.processEvents()


def test_generated_line_body_drag_preserves_endpoint_delta(tmp_path, app):
    editor = make_generated_editor(tmp_path)
    editor._select_generated_object("line-1", "list")
    axis = editor._figure.axes[0]
    original = editor._generated_figure_object_by_id("line-1").copy()

    def event(name, point):
        result = MouseEvent(
            name,
            editor._canvas,
            *axis.transData.transform(point),
            button=1,
        )
        result.inaxes = axis
        result.xdata, result.ydata = point
        return result

    start = ((original["x1"] + original["x2"]) / 2.0, (original["y1"] + original["y2"]) / 2.0)
    end = (start[0] + 0.1, start[1] + 0.2)
    editor._on_generated_button_press(event("button_press_event", start))
    editor._on_generated_mouse_move(event("motion_notify_event", end))
    editor._on_generated_button_release(event("button_release_event", end))

    moved = editor._generated_figure_object_by_id("line-1")
    assert moved["x2"] - moved["x1"] == pytest.approx(original["x2"] - original["x1"])
    assert moved["y2"] - moved["y1"] == pytest.approx(original["y2"] - original["y1"])

    editor.deleteLater()
    app.processEvents()


def test_generated_text_body_hit_uses_rendered_text_bounds_on_log_axis(tmp_path, app):
    editor = make_generated_editor(tmp_path)
    payload = {
        "id": "log-text",
        "type": "text",
        "x": 0.5,
        "y": 1_000_000.0,
        "text": "Peak label",
    }
    editor._execute_edit(AddObjectCommand(payload))
    editor._show_generated_figure_document()
    axis = editor._figure.axes[0]
    axis.set_yscale("log")
    axis.set_ylim(1e4, 1e8)
    editor._canvas.draw()
    artist = editor._figure_render_adapter.artists_for_object_id("log-text")[0]
    bbox = artist.get_window_extent(editor._canvas.get_renderer())
    pixel = ((bbox.x0 + bbox.x1) / 2.0, (bbox.y0 + bbox.y1) / 2.0)
    data = axis.transData.inverted().transform(pixel)
    event = MouseEvent("button_press_event", editor._canvas, *pixel, button=1)
    event.inaxes = axis
    event.xdata, event.ydata = float(data[0]), float(data[1])
    target = editor._generated_drag_state_for_press(event, "log-text")

    assert target is not None
    assert target["kind"] == "body"

    editor.deleteLater()
    app.processEvents()


def test_generated_text_double_click_opens_inline_editor(tmp_path, app):
    editor = make_generated_editor(tmp_path)
    payload = {
        "id": "editable-text",
        "type": "text",
        "coordinate_space": "axes",
        "bounds": {"x": 0.2, "y": 0.3, "width": 0.3, "height": 0.12},
        "text": "Original label",
    }
    editor._execute_edit(AddObjectCommand(payload))
    editor._show_generated_figure_document()
    editor._select_generated_object(payload["id"], "list")
    axis = editor._figure.axes[0]
    editor._canvas.draw()
    artist = editor._figure_render_adapter.artists_for_object_id(payload["id"])[0]
    bbox = artist.get_window_extent(editor._canvas.get_renderer())
    press_pixel = ((bbox.x0 + bbox.x1) / 2.0, (bbox.y0 + bbox.y1) / 2.0)
    event = MouseEvent(
        "button_press_event",
        editor._canvas,
        *press_pixel,
        button=1,
        dblclick=True,
    )
    event.inaxes = axis

    editor._on_generated_button_press(event)

    assert editor._pending_inline_text["mode"] == "generated-edit"
    assert editor._pending_inline_text["object_id"] == payload["id"]
    assert editor._inline_text_editor.text() == "Original label"

    editor._inline_text_editor.setText("Updated label")
    assert editor._commit_inline_text_entry() is True
    assert editor._generated_figure_object_by_id(payload["id"])["text"] == "Updated label"
    editor._on_annotation_undo()
    assert editor._generated_figure_object_by_id(payload["id"])["text"] == "Original label"

    editor.deleteLater()
    app.processEvents()


def test_generated_text_body_drag_moves_on_log_axis(tmp_path, app):
    editor = make_generated_editor(tmp_path)
    payload = {
        "id": "movable-log-text",
        "type": "text",
        "x": 0.5,
        "y": 1_000_000.0,
        "text": "Peak label",
    }
    editor._execute_edit(AddObjectCommand(payload))
    editor._show_generated_figure_document()
    axis = editor._figure.axes[0]
    axis.set_yscale("log")
    axis.set_ylim(1e4, 1e8)
    editor._canvas.draw()
    artist = editor._figure_render_adapter.artists_for_object_id(payload["id"])[0]
    bbox = artist.get_window_extent(editor._canvas.get_renderer())
    press_pixel = ((bbox.x0 + bbox.x1) / 2.0, (bbox.y0 + bbox.y1) / 2.0)
    press = MouseEvent("button_press_event", editor._canvas, *press_pixel, button=1)
    press.inaxes = axis
    press.xdata, press.ydata = axis.transData.inverted().transform(press_pixel)
    editor._on_generated_button_press(press)

    move_pixel = (float(press_pixel[0]) + 48.0, float(press_pixel[1]) - 20.0)
    move = MouseEvent("motion_notify_event", editor._canvas, *move_pixel, button=1)
    move.inaxes = None
    move.xdata = None
    move.ydata = None
    editor._on_generated_mouse_move(move)

    preview = editor._generated_handle_drag_state["preview_geometry"]
    assert preview["x"] != pytest.approx(payload["x"])
    assert preview["y"] > 0.0

    editor._cancel_generated_drag()
    editor.deleteLater()
    app.processEvents()


def test_generated_text_body_drag_preview_keeps_box_geometry_and_selection_frame(
    tmp_path, app
):
    editor = make_generated_editor(tmp_path)
    payload = {
        "id": "boxed-text",
        "type": "text",
        "x": 0.72,
        "y": 1.0,
        "width": 0.15,
        "height": 0.5,
        "text": "Peak label",
    }
    editor._execute_edit(AddObjectCommand(payload))
    editor._show_generated_figure_document()
    editor._select_generated_object(payload["id"], "list")
    axis = editor._figure.axes[0]
    axis.set_yscale("log")
    axis.set_ylim(0.1, 10.0)
    editor._canvas.draw()
    artist = editor._figure_render_adapter.artists_for_object_id(payload["id"])[0]
    bbox = artist.get_window_extent(editor._canvas.get_renderer())
    pixel = ((bbox.x0 + bbox.x1) / 2.0, (bbox.y0 + bbox.y1) / 2.0)

    def event(name, point, *, inaxes=True):
        result = MouseEvent(name, editor._canvas, *point, button=1)
        result.inaxes = axis if inaxes else None
        result.xdata, result.ydata = axis.transData.inverted().transform(point)
        return result

    editor._on_generated_button_press(event("button_press_event", pixel))
    editor._on_generated_mouse_move(
        event("motion_notify_event", (float(pixel[0]) + 32.0, float(pixel[1]) + 18.0), inaxes=False)
    )

    preview = editor._generated_handle_drag_state["preview_geometry"]
    assert preview["width"] == pytest.approx(payload["width"])
    assert preview["height"] == pytest.approx(payload["height"])
    text_artist = editor._figure_render_adapter.artists_for_object_id(payload["id"])[0]
    assert text_artist.get_position() == pytest.approx(
        (preview["x"], preview["y"] + preview["height"])
    )
    frame = next(
        artist
        for artist in editor._figure.axes[0].patches
        if artist.get_gid() == f"pn-selection-frame:{payload['id']}"
    )
    assert frame.get_x() != pytest.approx(payload["x"])

    editor._cancel_generated_drag()
    editor.deleteLater()
    app.processEvents()


def test_generated_axes_text_body_drag_commits_one_viewport_geometry_command(
    tmp_path, app
):
    editor = make_generated_editor(tmp_path)
    payload = {
        "id": "viewport-drag-text",
        "type": "text",
        "coordinate_space": "axes",
        "bounds": {"x": 0.2, "y": 0.6, "width": 0.25, "height": 0.12},
        "text": "Viewport drag",
    }
    editor._execute_edit(AddObjectCommand(payload))
    editor._show_generated_figure_document()
    editor._select_generated_object(payload["id"], "list")
    axis = editor._figure.axes[0]
    frame = next(
        artist
        for artist in axis.patches
        if artist.get_gid() == f"pn-selection-frame:{payload['id']}"
    )
    handles = next(
        artist
        for artist in axis.collections
        if artist.get_gid() == f"pn-selection-handles:{payload['id']}"
    )
    assert frame.get_data_transform().transform((0.0, 0.0)) == pytest.approx((0.0, 0.0))
    assert handles.get_offset_transform().transform((0.0, 0.0)) == pytest.approx((0.0, 0.0))
    axis.set_yscale("log")
    editor._canvas.draw()
    artist = editor._figure_render_adapter.artists_for_object_id(payload["id"])[0]
    extent = artist.get_window_extent(editor._canvas.get_renderer())
    press_pixel = ((extent.x0 + extent.x1) / 2.0, (extent.y0 + extent.y1) / 2.0)

    press = MouseEvent("button_press_event", editor._canvas, *press_pixel, button=1)
    press.inaxes = axis
    editor._on_generated_button_press(press)
    history_before = len(editor._edit_session.history)
    move_pixel = (float(press_pixel[0]) + 36.0, float(press_pixel[1]) - 24.0)
    move = MouseEvent("motion_notify_event", editor._canvas, *move_pixel, button=1)
    move.inaxes = None
    editor._on_generated_mouse_move(move)

    preview = editor._generated_handle_drag_state["preview_geometry"]
    assert preview["y"] < payload["bounds"]["y"]
    editor._on_generated_button_release(move)

    moved = editor._generated_figure_object_by_id(payload["id"])
    assert moved["bounds"]["y"] < payload["bounds"]["y"]
    assert len(editor._edit_session.history) == history_before + 1
    editor._on_annotation_undo()
    assert editor._generated_figure_object_by_id(payload["id"])["bounds"] == payload["bounds"]

    editor.deleteLater()
    app.processEvents()


def test_generated_text_selection_overlays_follow_rendered_extent_and_hit_display_handles(
    tmp_path, app
):
    editor = make_generated_editor(tmp_path)
    payload = {
        "id": "tight-label",
        "type": "text",
        "coordinate_space": "axes",
        "bounds": {"x": 0.2, "y": 0.6, "width": 0.7, "height": 0.5},
        "text": "Peak",
        "style": {"font_size": 12.0},
    }
    editor._execute_edit(AddObjectCommand(payload))
    editor._show_generated_figure_document()
    editor._select_generated_object(payload["id"], "list")
    axis = editor._figure.axes[0]
    editor._canvas.draw()
    renderer = editor._canvas.get_renderer()
    text_artist = editor._figure_render_adapter.artists_for_object_id(payload["id"])[0]
    text_bbox = text_artist.get_window_extent(renderer)
    frame = next(
        artist
        for artist in axis.patches
        if artist.get_gid() == f"pn-selection-frame:{payload['id']}"
    )
    handles = next(
        artist
        for artist in axis.collections
        if artist.get_gid() == f"pn-selection-handles:{payload['id']}"
    )

    assert frame.get_data_transform().transform((0.0, 0.0)) == pytest.approx((0.0, 0.0))
    assert frame.get_x() == pytest.approx(text_bbox.x0 - 4.0)
    assert frame.get_y() == pytest.approx(text_bbox.y0 - 4.0)
    assert frame.get_width() == pytest.approx(text_bbox.width + 8.0)
    assert frame.get_height() == pytest.approx(text_bbox.height + 8.0)
    assert frame.get_width() < 100.0
    assert handles.get_offset_transform().transform((0.0, 0.0)) == pytest.approx((0.0, 0.0))
    expected_corners = [
        (text_bbox.x0 - 4.0, text_bbox.y0 - 4.0),
        (text_bbox.x1 + 4.0, text_bbox.y0 - 4.0),
        (text_bbox.x1 + 4.0, text_bbox.y1 + 4.0),
        (text_bbox.x0 - 4.0, text_bbox.y1 + 4.0),
    ]
    for offset, expected_corner in zip(handles.get_offsets(), expected_corners):
        assert tuple(offset) == pytest.approx(expected_corner)

    corner = handles.get_offsets()[2]
    event = MouseEvent("button_press_event", editor._canvas, *corner, button=1)
    event.inaxes = axis
    assert editor._generated_point_handle_hit(event, payload["id"]) == 2

    editor.deleteLater()
    app.processEvents()


def test_generated_text_selection_overlays_refresh_after_canvas_resize(tmp_path, app):
    editor = make_generated_editor(tmp_path)
    payload = {
        "id": "resized-label",
        "type": "text",
        "coordinate_space": "axes",
        "bounds": {"x": 0.2, "y": 0.6, "width": 0.7, "height": 0.5},
        "text": "Peak",
        "style": {"font_size": 12.0},
    }
    editor._execute_edit(AddObjectCommand(payload))
    editor._show_generated_figure_document()
    editor._select_generated_object(payload["id"], "list")
    axis = editor._figure.axes[0]
    editor._canvas.draw()
    text_artist = editor._figure_render_adapter.artists_for_object_id(payload["id"])[0]
    original_bbox = text_artist.get_window_extent(editor._canvas.get_renderer())

    editor._canvas.resize(editor._canvas.width() + 180, editor._canvas.height() + 120)
    editor._fit_figure_to_live_canvas(editor._figure)
    editor._canvas.draw()

    text_bbox = text_artist.get_window_extent(editor._canvas.get_renderer())
    assert text_bbox != original_bbox
    frame = next(
        artist
        for artist in axis.patches
        if artist.get_gid() == f"pn-selection-frame:{payload['id']}"
    )
    handles = next(
        artist
        for artist in axis.collections
        if artist.get_gid() == f"pn-selection-handles:{payload['id']}"
    )
    assert frame.get_x() == pytest.approx(text_bbox.x0 - 4.0)
    assert frame.get_y() == pytest.approx(text_bbox.y0 - 4.0)
    assert frame.get_width() == pytest.approx(text_bbox.width + 8.0)
    assert frame.get_height() == pytest.approx(text_bbox.height + 8.0)
    assert tuple(handles.get_offsets()[2]) == pytest.approx(
        (text_bbox.x1 + 4.0, text_bbox.y1 + 4.0)
    )
    corner = handles.get_offsets()[2]
    event = MouseEvent("button_press_event", editor._canvas, *corner, button=1)
    event.inaxes = axis
    assert editor._generated_point_handle_hit(event, payload["id"]) == 2

    editor.deleteLater()
    app.processEvents()


def test_rendered_text_selection_bbox_preserves_figure_canvas_on_agg_fallback():
    figure = Figure(figsize=(4.0, 3.0), dpi=100)
    axis = figure.add_subplot(111)
    artist = axis.text(0.2, 0.3, "Peak")
    adapter = FigureRenderAdapter()
    adapter.register_artists("label", [artist])
    original_canvas = figure.canvas

    bbox = adapter.rendered_text_selection_bbox("label")

    assert bbox is not None
    assert figure.canvas is original_canvas


def test_generated_rectangle_body_drag_preview_moves_the_visible_box(tmp_path, app):
    editor = make_generated_editor(tmp_path)
    payload = {
        "id": "boxed-rectangle",
        "type": "rectangle",
        "x": 0.72,
        "y": 0.3,
        "width": 0.15,
        "height": 0.2,
    }
    editor._execute_edit(AddObjectCommand(payload))
    editor._show_generated_figure_document()
    editor._select_generated_object(payload["id"], "list")
    axis = editor._figure.axes[0]
    axis.set_yscale("log")
    axis.set_ylim(0.1, 10.0)
    editor._canvas.draw()

    def event(name, point, *, inaxes=True):
        result = MouseEvent(name, editor._canvas, *axis.transData.transform(point), button=1)
        result.inaxes = axis if inaxes else None
        result.xdata, result.ydata = point
        return result

    press_point = (payload["x"] + payload["width"] / 2.0, payload["y"] + payload["height"] / 2.0)
    editor._on_generated_button_press(event("button_press_event", press_point))
    editor._on_generated_mouse_move(
        event("motion_notify_event", (press_point[0] + 0.1, press_point[1] + 0.08))
    )

    preview = editor._generated_handle_drag_state["preview_geometry"]
    assert preview["x"] != pytest.approx(payload["x"])
    assert preview["y"] != pytest.approx(payload["y"])
    assert preview["width"] == pytest.approx(payload["width"])
    assert preview["height"] == pytest.approx(payload["height"])

    editor._cancel_generated_drag()
    editor.deleteLater()
    app.processEvents()


def test_generated_text_box_uses_its_left_top_corner_as_visual_anchor(tmp_path, app):
    editor = make_generated_editor(tmp_path)
    payload = {
        "id": "anchored-text",
        "type": "text",
        "x": 0.2,
        "y": 0.3,
        "width": 0.25,
        "height": 0.12,
        "text": "Peak",
    }
    editor._execute_edit(AddObjectCommand(payload))
    editor._show_generated_figure_document()

    artist = editor._figure_render_adapter.artists_for_object_id(payload["id"])[0]
    assert artist.get_position() == pytest.approx(
        (payload["x"], payload["y"] + payload["height"])
    )
    assert artist.get_ha() == "left"
    assert artist.get_va() == "top"

    editor.deleteLater()
    app.processEvents()


def test_generated_text_inspector_applies_and_syncs_font_size(tmp_path, app):
    editor = make_generated_editor(tmp_path)
    payload = {
        "id": "styled-text",
        "type": "text",
        "x": 0.2,
        "y": 0.3,
        "width": 0.25,
        "height": 0.12,
        "text": "Peak",
        "style": {"font_size": 16},
    }
    editor._execute_edit(AddObjectCommand(payload))
    editor._show_generated_figure_document()
    editor._select_generated_object(payload["id"], "list")

    assert editor._annotation_font_size_spin.value() == 16
    assert editor._annotation_font_size_spin.isEnabled()

    editor._annotation_font_size_spin.setValue(24)
    editor._btn_annotation_apply_style.click()

    assert editor._generated_figure_object_by_id(payload["id"])["style"]["font_size"] == 24.0
    artist = editor._figure_render_adapter.artists_for_object_id(payload["id"])[0]
    assert artist.get_fontsize() == pytest.approx(24.0)

    editor.deleteLater()
    app.processEvents()


def test_generated_text_context_font_size_redraws_artist(tmp_path, app):
    editor = make_generated_editor(tmp_path)
    payload = {
        "id": "context-text",
        "type": "text",
        "x": 0.2,
        "y": 0.3,
        "width": 0.25,
        "height": 0.12,
        "text": "Peak",
        "style": {"font_size": 12},
    }
    editor._execute_edit(AddObjectCommand(payload))
    editor._show_generated_figure_document()
    editor._select_generated_object(payload["id"], "list")

    editor._context_font_size.setValue(30)

    assert editor._generated_figure_object_by_id(payload["id"])["style"]["font_size"] == 30.0
    artist = editor._figure_render_adapter.artists_for_object_id(payload["id"])[0]
    assert artist.get_fontsize() == pytest.approx(30.0)

    editor.deleteLater()
    app.processEvents()


def test_generated_text_corner_drag_scales_font_without_changing_persisted_geometry(
    tmp_path, app
):
    editor = make_generated_editor(tmp_path)
    payload = {
        "id": "resizable-text",
        "type": "text",
        "coordinate_space": "axes",
        "bounds": {"x": 0.2, "y": 0.3, "width": 0.25, "height": 0.12},
        "text": "Peak",
        "style": {"font_size": 12.0},
    }
    editor._execute_edit(AddObjectCommand(payload))
    editor._show_generated_figure_document()
    editor._select_generated_object(payload["id"], "list")
    axis = editor._figure.axes[0]
    editor._canvas.draw()
    handles = next(
        artist
        for artist in axis.collections
        if artist.get_gid() == f"pn-selection-handles:{payload['id']}"
    )
    original_corner = tuple(handles.get_offsets()[0])
    original_opposite_corner = tuple(handles.get_offsets()[2])
    original_font_size = payload["style"]["font_size"]
    original_bounds = deepcopy(payload["bounds"])
    history_before = len(editor._edit_session.history)

    def event(name, pixel):
        result = MouseEvent(name, editor._canvas, *pixel, button=1)
        result.inaxes = axis
        result.xdata, result.ydata = axis.transData.inverted().transform(pixel)
        return result

    editor._on_generated_button_press(event("button_press_event", original_corner))
    assert editor._generated_handle_drag_state["kind"] == "text"
    assert editor._generated_handle_drag_state["handle_index"] == 0
    moved_corner = (original_corner[0] - 36.0, original_corner[1] - 24.0)
    editor._on_generated_mouse_move(
        event("motion_notify_event", moved_corner)
    )
    preview = editor._generated_handle_drag_state["preview_style"]
    assert preview["font_size"] > original_font_size
    assert editor._annotation_font_size_spin.value() == pytest.approx(
        preview["font_size"], abs=1.0
    )
    assert editor._generated_figure_object_by_id(payload["id"])["bounds"] == original_bounds
    editor._canvas.draw()
    preview_handles = next(
        artist
        for artist in axis.collections
        if artist.get_gid() == f"pn-selection-handles:{payload['id']}"
    )
    assert tuple(preview_handles.get_offsets()[2]) == pytest.approx(
        original_opposite_corner, abs=1.0
    )
    editor._on_generated_button_release(
        event("button_release_event", moved_corner)
    )

    saved = editor._generated_figure_object_by_id(payload["id"])
    assert saved["bounds"] == original_bounds
    assert saved["style"]["font_size"] == pytest.approx(preview["font_size"])
    assert len(editor._edit_session.history) == history_before + 1
    assert isinstance(editor._edit_session.history[-1], UpdateStyleCommand)

    editor._on_annotation_undo()
    assert editor._generated_figure_object_by_id(payload["id"])["style"][
        "font_size"
    ] == pytest.approx(original_font_size)
    editor._on_annotation_redo()
    assert editor._generated_figure_object_by_id(payload["id"])["style"][
        "font_size"
    ] == pytest.approx(preview["font_size"])

    editor.deleteLater()
    app.processEvents()


def test_generated_curve_body_hit_uses_rendered_path_on_log_axis(tmp_path, app):
    editor = make_generated_editor(tmp_path)
    payload = {
        "id": "log-curve",
        "type": "curve",
        "x1": 0.2,
        "y1": 1e4,
        "x2": 0.8,
        "y2": 1e7,
        "control_x": 0.5,
        "control_y": 1e5,
    }
    editor._execute_edit(AddObjectCommand(payload))
    editor._show_generated_figure_document()
    axis = editor._figure.axes[0]
    axis.set_yscale("log")
    axis.set_ylim(1e3, 1e8)
    editor._canvas.draw()
    artist = editor._figure_render_adapter.artists_for_object_id(payload["id"])[0]
    point = (
        0.25 * payload["x1"] + 0.5 * payload["control_x"] + 0.25 * payload["x2"],
        0.25 * payload["y1"] + 0.5 * payload["control_y"] + 0.25 * payload["y2"],
    )
    pixel = artist.get_transform().transform(point)
    event = MouseEvent("button_press_event", editor._canvas, *pixel, button=1)
    event.inaxes = axis
    event.xdata, event.ydata = axis.transData.inverted().transform(pixel)

    target = editor._generated_drag_state_for_press(event, payload["id"])

    assert target is not None
    assert target["kind"] == "body"

    editor._on_generated_button_press(event)
    move_pixel = (float(pixel[0]) + 36.0, float(pixel[1]) - 18.0)
    move = MouseEvent("motion_notify_event", editor._canvas, *move_pixel, button=1)
    move.inaxes = None
    move.xdata = None
    move.ydata = None
    editor._on_generated_mouse_move(move)
    preview = editor._generated_handle_drag_state["preview_geometry"]
    assert preview["control_x"] != pytest.approx(payload["control_x"])
    assert preview["control_y"] > 0.0

    editor._cancel_generated_drag()

    editor.deleteLater()
    app.processEvents()


def test_generated_line_body_drag_uses_display_delta_on_log_axis(tmp_path, app):
    editor = make_generated_editor(tmp_path)
    editor._select_generated_object("line-1", "list")
    axis = editor._figure.axes[0]
    axis.set_yscale("log")
    axis.set_ylim(0.1, 10.0)
    editor._canvas.draw()
    original = editor._generated_figure_object_by_id("line-1").copy()
    artist = editor._generated_line_artist("line-1")
    artist_pixels = artist.get_transform().transform(list(zip(artist.get_xdata(), artist.get_ydata())))
    press_pixel = (artist_pixels[0] + artist_pixels[1]) / 2.0
    start = tuple(axis.transData.inverted().transform(press_pixel))
    press = MouseEvent("button_press_event", editor._canvas, *press_pixel, button=1)
    press.inaxes = axis
    press.xdata, press.ydata = start
    editor._on_generated_button_press(press)

    move_pixel = (float(press_pixel[0]), float(press_pixel[1]) - 80.0)
    move = MouseEvent("motion_notify_event", editor._canvas, *move_pixel, button=1)
    move.inaxes = None
    move.xdata = None
    move.ydata = None
    editor._on_generated_mouse_move(move)

    preview = editor._generated_handle_drag_state["preview_geometry"]
    moved_pixel = axis.transData.transform((preview["x1"], preview["y1"]))
    assert moved_pixel[1] - axis.transData.transform((original["x1"], original["y1"]))[1] == pytest.approx(
        -80.0, abs=4.0
    )
    assert preview["y1"] > 0.0
    assert preview["y2"] > 0.0

    editor._cancel_generated_drag()
    editor.deleteLater()
    app.processEvents()


def test_generated_export_omits_editor_selection_handles_and_restores_selection(
    tmp_path, app, monkeypatch
):
    editor = make_generated_editor(tmp_path)
    editor._select_generated_object("line-1", "list")
    assert any(
        artist.get_gid() == "pn-selection-frame:line-1"
        for artist in editor._figure.axes[0].lines
    )
    assert any(
        artist.get_gid() == "pn-selection-handles:line-1"
        for artist in editor._figure.axes[0].collections
    )
    exported_gids = []
    original_savefig = Figure.savefig

    def capture_export(figure, *args, **kwargs):
        exported_gids.extend(
            str(artist.get_gid() or "")
            for axes in figure.axes
            for artist in (*axes.lines, *axes.patches, *axes.collections)
        )
        return original_savefig(figure, *args, **kwargs)

    monkeypatch.setattr(Figure, "savefig", capture_export)
    target = tmp_path / "exported.png"

    editor._save_generated_document_figure(target)

    assert not any(gid.startswith("pn-selection-handles:") for gid in exported_gids)
    assert not any(gid.startswith("pn-current-handle:") for gid in exported_gids)
    assert not any(gid.startswith("pn-selection-frame:") for gid in exported_gids)
    assert editor._selected_figure_object_id == "line-1"
    assert any(
        artist.get_gid() == "pn-selection-frame:line-1"
        for artist in editor._figure.axes[0].lines
    )
    assert any(
        artist.get_gid() == "pn-selection-handles:line-1"
        for artist in editor._figure.axes[0].collections
    )

    editor.deleteLater()
    app.processEvents()


def test_inline_text_escape_uses_common_draw_cancellation_status(tmp_path, app):
    editor = make_generated_editor(tmp_path)
    editor._begin_generated_text_box((1.0, 2.0), (4.0, 3.0), QRect(20, 20, 100, 28))

    event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
    app.sendEvent(editor._inline_text_editor, event)

    assert event.isAccepted()
    assert editor._pending_inline_text is None
    assert editor._inline_text_editor.isHidden()
    assert editor._status_label.text() == tr("EDITOR_DRAW_CANCELLED")

    editor.deleteLater()
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


def test_generated_shape_drag_preview_keeps_canvas_and_history_stable(tmp_path, app):
    editor = make_generated_editor(tmp_path)
    editor.set_tool("rectangle")
    axis = editor._figure.axes[0]
    original_figure = editor._figure
    original_limits = (axis.get_xlim(), axis.get_ylim())

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
    editor._on_generated_mouse_move(event("motion_notify_event", 0.4, 0.5))
    editor._on_generated_mouse_move(event("motion_notify_event", 0.8, 0.7))

    assert editor._figure is original_figure
    assert editor._generated_draw_preview_artists
    assert editor._edit_session.history == ()
    assert axis.get_xlim() == original_limits[0]
    assert axis.get_ylim() == original_limits[1]

    editor._on_generated_button_release(event("button_release_event", 0.8, 0.7))
    assert len(editor._edit_session.history) == 1

    editor.deleteLater()
    app.processEvents()


def test_generated_text_drag_previews_before_opening_inline_editor(tmp_path, app):
    editor = make_generated_editor(tmp_path)
    editor.set_tool("text")
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
    editor._on_generated_mouse_move(event("motion_notify_event", 0.6, 0.5))
    assert editor._generated_draw_preview_artists
    assert editor._pending_inline_text is None

    editor._on_generated_button_release(event("button_release_event", 0.6, 0.5))
    assert not editor._generated_draw_preview_artists
    assert editor._pending_inline_text is not None
    assert not any(
        item.get("type") == "text" for item in editor._figure_document.get("objects", [])
    )

    editor._cancel_inline_text_entry()
    editor.deleteLater()
    app.processEvents()


def test_generated_text_drag_places_inline_editor_above_canvas(tmp_path, app):
    editor = make_generated_editor(tmp_path)
    editor.resize(1400, 900)
    editor.show()
    app.processEvents()
    editor.set_tool("text")

    canvas = editor._canvas
    axis = editor._figure.axes[0]
    device_ratio = float(canvas.devicePixelRatioF() or 1.0)

    def canvas_position(x_value, y_value):
        x_pixel, y_pixel = axis.transData.transform((x_value, y_value))
        return QPointF(
            float(x_pixel) / device_ratio,
            (float(canvas.figure.bbox.height) - float(y_pixel)) / device_ratio,
        )

    def send_mouse_event(event_type, position, buttons):
        global_position = QPointF(canvas.mapToGlobal(position.toPoint()))
        event = QMouseEvent(
            event_type,
            position,
            position,
            global_position,
            Qt.LeftButton,
            buttons,
            Qt.NoModifier,
        )
        app.sendEvent(canvas, event)
        app.processEvents()

    start = canvas_position(0.2, 0.2)
    end = canvas_position(0.6, 0.5)
    send_mouse_event(QEvent.MouseButtonPress, start, Qt.LeftButton)
    send_mouse_event(QEvent.MouseMove, end, Qt.LeftButton)
    send_mouse_event(QEvent.MouseButtonRelease, end, Qt.NoButton)

    inline_editor = editor._inline_text_editor
    assert inline_editor.isVisible()
    center = inline_editor.mapToGlobal(inline_editor.rect().center())
    assert QApplication.widgetAt(center) is inline_editor

    editor.deleteLater()
    app.processEvents()


def test_generated_text_rect_converts_device_pixels_to_logical_canvas_coordinates(
    tmp_path, app, monkeypatch
):
    editor = make_generated_editor(tmp_path)
    editor.resize(1400, 900)
    editor.show()
    app.processEvents()
    monkeypatch.setattr(editor, "_generated_canvas_device_ratio", lambda: 2.0, raising=False)

    event = SimpleNamespace(x=600.0, y=500.0)
    rect = editor._generated_canvas_rect((200.0, 700.0), event)

    expected_top = editor._canvas.height() - 350
    assert rect == QRect(100, expected_top, 200, 100)

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
    selected_id = str(editor._figure_document["objects"][0]["id"])
    editor._select_generated_object(selected_id, "list")
    assert any(
        str(artist.get_gid() or "") == f"pn-selection-frame:{selected_id}"
        for axis in editor._figure.axes
        for artist in (*axis.lines, *axis.patches)
    )
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
    editor._on_generated_button_release(event)
    assert editor._commit_inline_text_entry("Peak") is True

    assert any(
        item.get("type") == "text" and item.get("text") == "Peak"
        for item in editor._figure_document.get("objects", [])
    )

    editor.deleteLater()
    app.processEvents()
