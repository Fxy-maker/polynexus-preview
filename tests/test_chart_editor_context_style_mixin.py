from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from polynexus.gui.widgets.chart_editor import ChartEditor


def _app():
    return QApplication.instance() or QApplication([])


def _generated_editor_with_object(figure_object: dict) -> ChartEditor:
    editor = ChartEditor()
    editor._generated_document_mode = True
    editor._figure_document = {"mode": "object", "objects": [figure_object]}
    editor._reset_edit_session_from_document(editor._figure_document)
    return editor


def test_context_style_bar_shows_text_controls_for_selected_text():
    _app()
    editor = _generated_editor_with_object(
        {"id": "note", "type": "text", "x": 0.2, "y": 0.4, "text": "Peak"}
    )

    editor._select_generated_object("note", "test")

    assert not editor._context_style_bar.isHidden()
    assert not editor._context_color.isHidden()
    assert not editor._context_font_size.isHidden()
    assert editor._context_line_width.isHidden()
    assert editor._context_line_style.isHidden()

    editor.deleteLater()
    _app().processEvents()


def test_context_style_bar_updates_selected_line_through_edit_session():
    _app()
    editor = _generated_editor_with_object(
        {"id": "line", "type": "line", "x1": 0.0, "y1": 0.0, "x2": 1.0, "y2": 1.0}
    )

    editor._select_generated_object("line", "test")

    assert editor._apply_context_color("#0072B2") is True
    assert editor._generated_figure_object_by_id("line")["style"]["color"] == "#0072B2"
    assert editor._edit_session.can_undo is True

    editor.deleteLater()
    _app().processEvents()


def test_tool_selection_shows_draw_defaults_without_hiding_inspector():
    _app()
    editor = _generated_editor_with_object(
        {"id": "line", "type": "line", "x1": 0.0, "y1": 0.0, "x2": 1.0, "y2": 1.0}
    )

    assert not editor._inspector_panel.isHidden()
    assert editor.set_tool("line") is True

    assert not editor._context_style_bar.isHidden()
    assert not editor._context_color.isHidden()
    assert not editor._context_line_width.isHidden()
    assert not editor._inspector_panel.isHidden()

    editor.deleteLater()
    _app().processEvents()


def test_context_style_bar_does_not_resize_the_live_canvas(tmp_path):
    app = _app()
    editor = _generated_editor_with_object(
        {"id": "line", "type": "line", "x1": 0.0, "y1": 0.0, "x2": 1.0, "y2": 1.0}
    )
    editor.resize(900, 700)
    editor.show()
    app.processEvents()

    before = editor._canvas.geometry()
    editor._generated_draw_tool = "line"
    editor._sync_context_style_bar()
    app.processEvents()
    after = editor._canvas.geometry()

    assert after == before

    editor.deleteLater()
    app.processEvents()
