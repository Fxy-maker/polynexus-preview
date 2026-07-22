from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from matplotlib.figure import Figure
from PySide6.QtWidgets import QApplication

from polynexus.gui.widgets.chart_editor import ChartEditor


def _app():
    return QApplication.instance() or QApplication([])


def _editor_with_axis():
    _app()
    editor = ChartEditor()
    editor._generated_document_mode = True
    editor._figure_document = {"mode": "object", "objects": []}
    editor._reset_edit_session_from_document(editor._figure_document)
    figure = Figure()
    axis = figure.add_subplot(111)
    axis.set_xlim(0.0, 10.0)
    axis.set_ylim(-1.0, 5.0)
    editor._replace_canvas_figure(figure)
    return editor, axis


def test_generated_draw_preview_updates_without_document_rebuild():
    editor, axis = _editor_with_axis()
    rebuilds = []
    editor._show_generated_figure_document = lambda: rebuilds.append(True)
    editor._generated_draw_tool = "rectangle"

    editor._begin_generated_draw_preview((0.1, 0.2), (20.0, 30.0))
    editor._update_generated_draw_preview(
        "rectangle",
        (0.1, 0.2),
        (0.6, 0.7),
    )

    assert editor._generated_draw_preview_artists
    assert rebuilds == []
    assert editor._edit_session.history == ()
    assert tuple(axis.get_xlim()) == (0.0, 10.0)
    assert tuple(axis.get_ylim()) == (-1.0, 5.0)

    editor.deleteLater()
    _app().processEvents()


def test_generated_curve_draw_preview_uses_a_visible_quadratic_path():
    editor, _axis = _editor_with_axis()

    editor._begin_generated_draw_preview((0.0, 0.0), None)
    editor._update_generated_draw_preview("curve", (0.0, 0.0), (1.0, 0.0))

    assert len(editor._generated_draw_preview_artists) == 1
    assert editor._generated_draw_preview_artists[0].get_gid() == "pn-preview:curve"
    vertices = editor._generated_draw_preview_artists[0].get_path().vertices.tolist()
    assert vertices[0] == [0.0, 0.0]
    assert vertices[1] == [0.5, 0.35]
    assert vertices[2] == [1.0, 0.0]

    editor.deleteLater()
    _app().processEvents()


def test_generated_draw_preview_clear_removes_every_artist():
    editor, axis = _editor_with_axis()
    editor._begin_generated_draw_preview((0.0, 0.0), None)
    editor._update_generated_draw_preview("line", (0.0, 0.0), (1.0, 1.0))

    assert editor._clear_generated_draw_preview() is True
    assert editor._generated_draw_preview_artists == []
    assert not any(
        getattr(artist, "get_gid", lambda: "")() == "pn-preview:line"
        for artist in axis.get_children()
    )

    editor.deleteLater()
    _app().processEvents()


def test_replacing_canvas_figure_fits_after_qt_canvas_assignment():
    from polynexus.gui.widgets.chart_editor_generated_document_mixin import (
        ChartEditorGeneratedDocumentMixin,
    )
    from polynexus.gui.widgets.chart_editor_render_mixin import ChartEditorRenderMixin

    class _Canvas:
        def __init__(self):
            self._figure = Figure(figsize=(2, 2), dpi=100)

        @property
        def figure(self):
            return self._figure

        @figure.setter
        def figure(self, value):
            # FigureCanvasQTAgg performs this logical-pixel resize when a new
            # Figure is assigned; the editor must fit after this setter.
            value.set_size_inches(10.0, 8.0, forward=False)
            self._figure = value

        def width(self):
            return 1000

        def height(self):
            return 800

        def devicePixelRatioF(self):
            return 1.5

        def draw(self):
            pass

    class _Editor(ChartEditorGeneratedDocumentMixin, ChartEditorRenderMixin):
        _dpi = 100

        def __init__(self):
            self._canvas = _Canvas()
            self._generated_viewport_snapshot = None
            self._hovered_figure_object_id = ""

        def _connect_canvas_interaction_events(self):
            pass

        def _restore_generated_viewport(self):
            self._canvas.figure.set_size_inches(10.0, 8.0, forward=False)

    editor = _Editor()
    editor._replace_canvas_figure(Figure(figsize=(2, 2), dpi=100))

    assert tuple(editor._canvas.figure.bbox.bounds)[2:] == (1500.0, 1200.0)
