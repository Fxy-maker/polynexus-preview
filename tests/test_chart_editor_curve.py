from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from matplotlib.figure import Figure
from PySide6.QtWidgets import QApplication

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
