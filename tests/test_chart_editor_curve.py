from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from matplotlib.figure import Figure
from PySide6.QtWidgets import QApplication
import pytest

from polynexus.gui.widgets.chart_editor import ChartEditor


def _app():
    return QApplication.instance() or QApplication([])


def test_generated_editor_exposes_curve_tool():
    _app()
    editor = ChartEditor()
    editor._generated_document_mode = True

    assert "curve" in editor._editor_toolbar.action_ids()
    assert editor.set_tool("curve") is True
    assert editor._generated_draw_tool == "curve"

    editor.deleteLater()
    _app().processEvents()


def test_generated_tool_rejects_object_before_document_mutation(monkeypatch):
    _app()
    editor = ChartEditor()
    editor._generated_document_mode = True
    editor._figure_document = {"mode": "object", "objects": []}
    editor._reset_edit_session_from_document(editor._figure_document)
    monkeypatch.setattr(
        "polynexus.gui.widgets.chart_editor_generated_interaction_mixin.MatplotlibFigureRenderer.supports_object_type",
        staticmethod(lambda _object_type: False),
    )

    assert editor._add_generated_tool_object("curve", (0.0, 0.0), (1.0, 1.0)) is False
    assert editor._figure_document["objects"] == []
    assert editor._edit_session.history == ()
    assert "curve" in editor._status_label.text()
    assert editor._generated_draw_tool == "select"

    editor.deleteLater()
    _app().processEvents()


def test_generated_renderer_draws_bezier_curve():
    _app()
    editor = ChartEditor()
    figure = Figure()
    axis = figure.add_subplot(111)

    artists = editor._render_generated_figure_object(
        axis,
        {
            "id": "curve-1",
            "type": "curve",
            "x1": 0.0,
            "y1": 0.0,
            "x2": 1.0,
            "y2": 0.0,
            "control_x": 0.5,
            "control_y": 1.0,
            "style": {"color": "#0072B2", "line_width": 2.0},
        },
        {},
        0,
    )

    assert len(artists) == 1
    assert artists[0].get_path().vertices.tolist() == [
        [0.0, 0.0],
        [0.5, 1.0],
        [1.0, 0.0],
    ]

    editor.deleteLater()
    _app().processEvents()


def test_generated_text_box_renders_as_wrapped_clipped_text_without_a_frame():
    _app()
    editor = ChartEditor()
    figure = Figure()
    axis = figure.add_subplot(111)

    artists = editor._render_generated_figure_object(
        axis,
        {
            "id": "note-1",
            "type": "text",
            "x": 0.2,
            "y": 0.3,
            "width": 0.4,
            "height": 0.2,
            "text": "Peak region annotation",
            "style": {"color": "#0072B2", "font_size": 12.0},
        },
        {},
        0,
    )

    assert len(artists) == 1
    assert artists[0].get_wrap() is True
    assert artists[0].get_clip_on() is True
    assert len(axis.patches) == 0

    editor.deleteLater()
    _app().processEvents()


def test_generated_text_box_uses_persisted_bounds_geometry_when_reloaded():
    _app()
    editor = ChartEditor()
    figure = Figure()
    axis = figure.add_subplot(111)

    artists = editor._render_generated_figure_object(
        axis,
        {
            "id": "note-1",
            "type": "text",
            "text": "Peak region annotation",
            "bounds": {"x": 0.2, "y": 0.3, "width": 0.4, "height": 0.2},
            "style": {"color": "#0072B2", "font_size": 12.0},
        },
        {},
        0,
    )

    assert artists[0].get_position() == (0.2, 0.5)
    assert artists[0].get_ha() == "left"
    assert artists[0].get_va() == "top"
    assert artists[0].get_wrap() is True
    assert artists[0].get_clip_on() is True

    editor.deleteLater()
    _app().processEvents()


def test_generated_axes_text_box_uses_axes_transform():
    _app()
    editor = ChartEditor()
    figure = Figure()
    axis = figure.add_subplot(111)

    artists = editor._render_generated_figure_object(
        axis,
        {
            "id": "axes-note-1",
            "type": "text",
            "coordinate_space": "axes",
            "bounds": {"x": 0.2, "y": 0.3, "width": 0.4, "height": 0.2},
            "text": "Viewport annotation",
            "style": {"color": "#0072B2", "font_size": 12.0},
        },
        {},
        0,
    )

    assert artists[0].get_transform() == axis.transAxes
    assert artists[0].get_position() == (0.2, 0.5)

    editor.deleteLater()
    _app().processEvents()


def test_generated_text_draw_preview_uses_axes_transform():
    _app()
    editor = ChartEditor()
    figure = Figure()
    axis = figure.add_subplot(111)
    axis.set_xlim(0.0, 10.0)
    axis.set_ylim(0.0, 20.0)
    editor._figure = figure

    artist = editor._make_generated_draw_preview_artist(
        "text",
        (0.2, 0.3),
        (0.5, 0.5),
    )

    assert artist.get_transform().transform((0.0, 0.0)) == pytest.approx(
        axis.transAxes.transform((0.2, 0.3))
    )

    editor.deleteLater()
    _app().processEvents()


def test_generated_curve_control_handle_updates_canonical_geometry():
    _app()
    editor = ChartEditor()
    editor._generated_document_mode = True
    editor._figure_document = {
        "mode": "object",
        "objects": [
            {
                "id": "curve-1",
                "type": "curve",
                "x1": 0.0,
                "y1": 0.0,
                "x2": 1.0,
                "y2": 0.0,
                "control_x": 0.5,
                "control_y": 0.2,
            }
        ],
    }
    editor._reset_edit_session_from_document(editor._figure_document)

    assert editor._apply_generated_curve_handle_drag("curve-1", 2, 0.4, 0.8)
    curve = editor._generated_figure_object_by_id("curve-1")
    assert curve["control_x"] == 0.4
    assert curve["control_y"] == 0.8

    editor.deleteLater()
    _app().processEvents()


def test_generated_rectangle_corner_handle_updates_geometry_through_edit_session():
    _app()
    editor = ChartEditor()
    editor._generated_document_mode = True
    editor._figure_document = {
        "mode": "object",
        "objects": [
            {
                "id": "region",
                "type": "rectangle",
                "x": 1.0,
                "y": 1.0,
                "width": 2.0,
                "height": 1.0,
            }
        ],
    }
    editor._reset_edit_session_from_document(editor._figure_document)

    assert editor._apply_generated_rectangle_handle_drag("region", 2, 4.0, 3.0)
    rectangle = editor._generated_figure_object_by_id("region")
    assert rectangle["x"] == 1.0
    assert rectangle["y"] == 1.0
    assert rectangle["width"] == 3.0
    assert rectangle["height"] == 2.0

    editor._on_annotation_undo()
    rectangle = editor._generated_figure_object_by_id("region")
    assert rectangle["width"] == 2.0
    assert rectangle["height"] == 1.0

    editor.deleteLater()
    _app().processEvents()


def test_generated_rectangle_corner_handle_updates_bounds_geometry_through_edit_session():
    _app()
    editor = ChartEditor()
    editor._generated_document_mode = True
    editor._figure_document = {
        "mode": "object",
        "objects": [
            {
                "id": "region",
                "type": "rectangle",
                "bounds": {"x": 1.0, "y": 1.0, "width": 2.0, "height": 1.0},
            }
        ],
    }
    editor._reset_edit_session_from_document(editor._figure_document)

    assert editor._apply_generated_rectangle_handle_drag("region", 2, 4.0, 3.0)
    assert editor._generated_figure_object_by_id("region")["bounds"] == {
        "x": 1.0,
        "y": 1.0,
        "width": 3.0,
        "height": 2.0,
    }

    editor.deleteLater()
    _app().processEvents()


def test_generated_rectangle_drag_commits_one_undoable_geometry_command():
    _app()
    editor = ChartEditor()
    editor._generated_document_mode = True
    editor._figure_document = {
        "mode": "object",
        "objects": [
            {
                "id": "region",
                "type": "rectangle",
                "x": 1.0,
                "y": 1.0,
                "width": 2.0,
                "height": 1.0,
            }
        ],
    }
    session = editor._reset_edit_session_from_document(editor._figure_document)
    drag_state = {"object_id": "region", "kind": "rectangle", "handle_index": 2}
    editor._activate_generated_drag_state(drag_state)

    assert editor._apply_generated_rectangle_handle_drag("region", 2, 3.5, 2.5, preview=True)
    assert editor._apply_generated_rectangle_handle_drag("region", 2, 4.0, 3.0, preview=True)
    assert session.history == ()

    assert editor._commit_generated_drag(drag_state) is True
    assert len(session.history) == 1
    assert editor._generated_figure_object_by_id("region")["width"] == 3.0
    assert editor._on_annotation_undo() is None
    assert editor._generated_figure_object_by_id("region")["width"] == 2.0

    editor.deleteLater()
    _app().processEvents()


def test_escape_cancels_generated_rectangle_preview_without_history_mutation():
    _app()
    editor = ChartEditor()
    editor._generated_document_mode = True
    editor._figure_document = {
        "mode": "object",
        "objects": [
            {
                "id": "region",
                "type": "rectangle",
                "x": 1.0,
                "y": 1.0,
                "width": 2.0,
                "height": 1.0,
            }
        ],
    }
    session = editor._reset_edit_session_from_document(editor._figure_document)
    drag_state = {"object_id": "region", "kind": "rectangle", "handle_index": 2}
    editor._activate_generated_drag_state(drag_state)

    assert editor._apply_generated_rectangle_handle_drag("region", 2, 4.0, 3.0, preview=True)
    assert editor._cancel_generated_drag() is True

    assert session.history == ()
    assert editor._generated_figure_object_by_id("region")["width"] == 2.0
    assert editor._generated_figure_object_by_id("region")["height"] == 1.0

    editor.deleteLater()
    _app().processEvents()


def test_generated_line_drag_coalesces_multiple_moves_into_one_undo_command():
    _app()
    editor = ChartEditor()
    editor._generated_document_mode = True
    editor._figure_document = {
        "mode": "object",
        "objects": [
            {"id": "line-1", "type": "line", "x1": 1.0, "y1": 1.0, "x2": 3.0, "y2": 2.0}
        ],
    }
    session = editor._reset_edit_session_from_document(editor._figure_document)
    drag_state = {"object_id": "line-1", "kind": "line", "handle_index": 1}
    editor._activate_generated_drag_state(drag_state)

    assert editor._apply_generated_line_handle_drag("line-1", 1, 3.5, 2.5)
    assert editor._apply_generated_line_handle_drag("line-1", 1, 4.0, 3.0)
    assert len(session.history) == 0
    assert editor._generated_handle_drag_state["preview_geometry"]["x2"] == 4.0

    assert editor._commit_generated_drag(drag_state) is True
    assert len(session.history) == 1
    editor._on_annotation_undo()
    assert editor._generated_figure_object_by_id("line-1")["x2"] == 3.0
    assert editor._generated_figure_object_by_id("line-1")["y2"] == 2.0

    editor.deleteLater()
    _app().processEvents()


def test_generated_rectangle_bounds_preview_updates_and_commits_nested_geometry():
    _app()
    editor = ChartEditor()
    editor._generated_document_mode = True
    editor._figure_document = {
        "mode": "object",
        "objects": [
            {
                "id": "region",
                "type": "rectangle",
                "bounds": {"x": 1.0, "y": 1.0, "width": 2.0, "height": 1.0},
            }
        ],
    }
    session = editor._reset_edit_session_from_document(editor._figure_document)
    drag_state = {"object_id": "region", "kind": "rectangle", "handle_index": 2}
    editor._activate_generated_drag_state(drag_state)

    assert editor._apply_generated_rectangle_handle_drag("region", 2, 4.0, 3.0, preview=True)
    assert session.history == ()
    assert editor._generated_handle_drag_state["preview_geometry"]["width"] == 3.0
    assert editor._generated_figure_object_by_id("region")["bounds"]["width"] == 2.0
    assert editor._commit_generated_drag(drag_state) is True
    assert len(session.history) == 1

    editor.deleteLater()
    _app().processEvents()


def test_escape_cancels_generated_line_drag_and_restores_edit_session_history():
    _app()
    editor = ChartEditor()
    editor._generated_document_mode = True
    editor._figure_document = {
        "mode": "object",
        "objects": [
            {"id": "line-1", "type": "line", "x1": 1.0, "y1": 1.0, "x2": 3.0, "y2": 2.0}
        ],
    }
    session = editor._reset_edit_session_from_document(editor._figure_document)
    drag_state = {"object_id": "line-1", "kind": "line", "handle_index": 1}
    editor._activate_generated_drag_state(drag_state)

    assert editor._apply_generated_line_handle_drag("line-1", 1, 4.0, 3.0)
    assert editor._cancel_generated_drag() is True

    assert session.history == ()
    assert editor._generated_figure_object_by_id("line-1")["x2"] == 3.0
    assert editor._generated_figure_object_by_id("line-1")["y2"] == 2.0

    editor.deleteLater()
    _app().processEvents()


def test_generated_renderer_reads_rectangle_bounds_geometry():
    _app()
    editor = ChartEditor()
    figure = Figure()
    axis = figure.add_subplot(111)

    artists = editor._render_generated_figure_object(
        axis,
        {
            "id": "region",
            "type": "rectangle",
            "bounds": {"x": 1.0, "y": 2.0, "width": 3.0, "height": 4.0},
        },
        {},
        0,
    )

    assert len(artists) == 1
    assert artists[0].get_x() == 1.0
    assert artists[0].get_y() == 2.0
    assert artists[0].get_width() == 3.0
    assert artists[0].get_height() == 4.0

    editor.deleteLater()
    _app().processEvents()


def test_generated_curve_exposes_editable_control_coordinates_in_inspector():
    _app()
    editor = ChartEditor()
    editor._generated_document_mode = True
    editor._figure_document = {
        "mode": "object",
        "objects": [
            {
                "id": "curve-1",
                "type": "curve",
                "x1": 0.0,
                "y1": 0.0,
                "x2": 1.0,
                "y2": 0.0,
                "control_x": 0.5,
                "control_y": 0.2,
            }
        ],
    }
    editor._reset_edit_session_from_document(editor._figure_document)
    editor._select_generated_object("curve-1", "list")

    assert editor._annotation_curve_control_x_spin.isEnabled() is True
    assert editor._annotation_curve_control_y_spin.isEnabled() is True
    assert editor._annotation_curve_control_x_spin.value() == 0.5
    assert editor._annotation_curve_control_y_spin.value() == 0.2

    editor._annotation_curve_control_x_spin.setValue(0.4)

    curve = editor._generated_figure_object_by_id("curve-1")
    assert curve["control_x"] == 0.4
    assert curve["control_y"] == 0.2

    editor.deleteLater()
    _app().processEvents()


def test_generated_curve_endpoint_coordinates_use_the_undoable_edit_session():
    _app()
    editor = ChartEditor()
    editor._generated_document_mode = True
    editor._figure_document = {
        "mode": "object",
        "objects": [
            {
                "id": "curve-1",
                "type": "curve",
                "x1": 0.0,
                "y1": 0.0,
                "x2": 1.0,
                "y2": 0.0,
                "control_x": 0.5,
                "control_y": 0.2,
            }
        ],
    }
    editor._reset_edit_session_from_document(editor._figure_document)
    editor._select_generated_object("curve-1", "list")

    editor._annotation_x_spin.setValue(0.1)

    curve = editor._generated_figure_object_by_id("curve-1")
    assert curve["x1"] == 0.1
    session = editor._edit_session_for_adapter()
    assert session is not None
    assert session.can_undo is True
    editor._on_annotation_undo()
    assert editor._generated_figure_object_by_id("curve-1")["x1"] == 0.0

    editor.deleteLater()
    _app().processEvents()
