import os
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from matplotlib.backend_bases import MouseEvent
from matplotlib.figure import Figure
from PySide6.QtCore import QEvent, QPointF, QRect, Qt
from PySide6.QtGui import QColor, QImage, QKeyEvent
from PySide6.QtWidgets import QApplication

from polynexus.core.figure_document import save_generated_figure_document
from polynexus.core.figure_edit_commands import AddObjectCommand, UpdateGeometryCommand
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

    editor._begin_generated_text_box((1.0, 2.0), (4.0, 3.0), QRect(20, 20, 100, 28))

    assert not any(item.get("type") == "text" for item in editor._figure_document["objects"])
    assert editor._commit_inline_text_entry("Peak region") is True
    text = next(item for item in editor._figure_document["objects"] if item.get("type") == "text")
    assert text["width"] == 3.0
    assert text["height"] == 1.0


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
