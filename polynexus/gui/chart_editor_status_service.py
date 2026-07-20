"""Pure helpers for chart-editor generated hover and drag status text."""

from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import Qt

from .i18n import tr


def format_generated_status_number(value: Any) -> str:
    try:
        if value is None or value == "":
            return ""
        numeric_value = float(value)
    except Exception:
        return str(value or "")
    text = f"{numeric_value:.3f}".rstrip("0").rstrip(".")
    return text or "0"


def build_generated_hover_status_text(label: str, drag_state: dict[str, Any]) -> str:
    kind = str(drag_state.get("kind", "") or "")
    if kind == "line":
        return tr("EDITOR_HOVER_HINT_DRAG_ENDPOINT", label)
    if kind == "plot_series":
        if drag_state.get("nearest_point_hit"):
            return tr("EDITOR_HOVER_HINT_DRAG_NEAREST_POINT", label)
        return tr("EDITOR_HOVER_HINT_DRAG_POINT", label)
    if kind == "line-body":
        return tr("EDITOR_HOVER_HINT_DRAG_LINE", label)
    if kind == "legend":
        return tr("EDITOR_HOVER_HINT_DRAG_LEGEND", label)
    if kind == "select":
        return tr("EDITOR_HOVER_HINT_CLICK_SELECT", label)
    return ""


def generated_hover_cursor_shape(drag_state: dict[str, Any]):
    kind = str(drag_state.get("kind", "") or "")
    if kind in {"line", "curve", "plot_series"}:
        return Qt.CursorShape.CrossCursor
    if kind == "rectangle":
        try:
            handle_index = int(drag_state.get("handle_index", 0))
        except (TypeError, ValueError):
            handle_index = 0
        if handle_index in {0, 2}:
            return Qt.CursorShape.SizeFDiagCursor
        return Qt.CursorShape.SizeBDiagCursor
    if kind == "select":
        return Qt.CursorShape.PointingHandCursor
    return Qt.CursorShape.OpenHandCursor


def build_generated_drag_status_text(
    label: str,
    drag_state: dict[str, Any],
    figure_object: dict[str, Any],
    *,
    number_formatter: Callable[[Any], str] = format_generated_status_number,
) -> str:
    kind = str(drag_state.get("kind", "") or "")
    if kind == "plot_series":
        inline_data = figure_object.get("data", {})
        if not isinstance(inline_data, dict):
            return ""
        point_index = int(drag_state.get("handle_index", 0) or 0)
        x_values = list(inline_data.get("x", []) or [])
        y_values = list(inline_data.get("y", []) or [])
        if point_index < 0 or point_index >= min(len(x_values), len(y_values)):
            return ""
        x_value = number_formatter(x_values[point_index])
        y_value = number_formatter(y_values[point_index])
        return tr("EDITOR_DRAG_STATUS_POINT", label, x_value, y_value)
    if kind == "line":
        handle_index = int(drag_state.get("handle_index", 0) or 0)
        if handle_index <= 0:
            x_value = number_formatter(figure_object.get("x1"))
            y_value = number_formatter(figure_object.get("y1"))
        else:
            x_value = number_formatter(figure_object.get("x2"))
            y_value = number_formatter(figure_object.get("y2"))
        return tr("EDITOR_DRAG_STATUS_ENDPOINT", label, x_value, y_value)
    if kind == "line-body":
        return tr(
            "EDITOR_DRAG_STATUS_LINE",
            label,
            number_formatter(figure_object.get("x1")),
            number_formatter(figure_object.get("y1")),
            number_formatter(figure_object.get("x2")),
            number_formatter(figure_object.get("y2")),
        )
    if kind == "legend":
        style = figure_object.get("style", {}) if isinstance(figure_object.get("style"), dict) else {}
        bbox_to_anchor = style.get("bbox_to_anchor")
        if not isinstance(bbox_to_anchor, (list, tuple)) or len(bbox_to_anchor) < 2:
            return ""
        return tr(
            "EDITOR_DRAG_STATUS_LEGEND",
            label,
            number_formatter(bbox_to_anchor[0]),
            number_formatter(bbox_to_anchor[1]),
        )
    return ""
