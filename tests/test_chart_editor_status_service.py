import pytest

from polynexus.gui.chart_editor_status_service import (
    build_editor_selection_hint,
    build_editor_tool_hint,
    build_generated_drag_status_text,
    build_generated_hover_status_text,
    generated_hover_cursor_shape,
)
from PySide6.QtCore import Qt
from polynexus.gui.i18n import get_language, set_language


def test_build_generated_hover_status_text_for_line_endpoint():
    previous = get_language()
    try:
        set_language("en")
        text = build_generated_hover_status_text(
            "Line",
            {"kind": "line"},
        )
        assert text == "Line: drag endpoint."
    finally:
        set_language(previous)


def test_build_generated_drag_status_text_for_line_body_uses_number_formatter():
    previous = get_language()
    try:
        set_language("en")
        figure_object = {"x1": 1.2345, "y1": 2.3456, "x2": 3.4567, "y2": 4.5678}
        text = build_generated_drag_status_text(
            "Line",
            {"kind": "line-body"},
            figure_object,
            number_formatter=lambda value: f"<{value}>",
        )
        assert text == "Line: line (<1.2345>, <2.3456>) -> (<3.4567>, <4.5678>)"
    finally:
        set_language(previous)


def test_generated_hover_cursor_shape_uses_expected_mapping():
    assert generated_hover_cursor_shape({"kind": "line"}) == Qt.CursorShape.CrossCursor
    assert generated_hover_cursor_shape({"kind": "plot_series"}) == Qt.CursorShape.CrossCursor
    assert generated_hover_cursor_shape({"kind": "curve"}) == Qt.CursorShape.CrossCursor
    assert generated_hover_cursor_shape({"kind": "rectangle", "handle_index": 0}) == Qt.CursorShape.SizeFDiagCursor
    assert generated_hover_cursor_shape({"kind": "rectangle", "handle_index": 1}) == Qt.CursorShape.SizeBDiagCursor
    assert generated_hover_cursor_shape({"kind": "select"}) == Qt.CursorShape.PointingHandCursor
    assert generated_hover_cursor_shape({"kind": "legend"}) == Qt.CursorShape.OpenHandCursor


def test_build_editor_tool_hint_explains_creation_and_cancellation():
    previous = get_language()
    try:
        set_language("en")
        for tool in ("text", "line", "arrow", "curve", "rectangle"):
            text = build_editor_tool_hint(tool)
            assert "create" in text.lower()
            assert "esc" in text.lower()
    finally:
        set_language(previous)


def test_build_editor_selection_hint_explains_body_and_handle_actions():
    previous = get_language()
    try:
        set_language("en")
        text = build_editor_selection_hint("rectangle", "Rectangle")
        assert "Rectangle" in text
        assert "drag" in text.lower()
        assert "body" in text.lower()
        assert "handle" in text.lower()
        assert "esc" in text.lower()
    finally:
        set_language(previous)


@pytest.mark.parametrize("object_type", ("text", "line", "arrow", "curve", "rectangle"))
def test_build_editor_selection_hint_covers_each_editable_object_type(object_type):
    previous = get_language()
    try:
        set_language("en")
        text = build_editor_selection_hint(object_type, object_type.title())
        assert object_type.title() in text
        assert "drag" in text.lower()
        assert "esc" in text.lower()
        if object_type in {"line", "arrow"}:
            assert "endpoint" in text.lower()
        elif object_type == "curve":
            assert "middle handle" in text.lower()
        else:
            assert "handle" in text.lower()
    finally:
        set_language(previous)
