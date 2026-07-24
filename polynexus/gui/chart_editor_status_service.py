"""Pure helpers for chart-editor generated hover and drag status text."""

from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import Qt

from ..core.figures.legend_layout import resolve_legend_layout
from .i18n import get_language, tr


_EDITOR_TOOL_LABEL_KEYS = {
    "select": "EDITOR_TOOL_SELECT",
    "text": "EDITOR_TOOL_TEXT",
    "line": "EDITOR_TOOL_LINE",
    "arrow": "EDITOR_TOOL_ARROW",
    "curve": "EDITOR_TOOL_CURVE",
    "rectangle": "EDITOR_TOOL_RECTANGLE",
    "highlight": "EDITOR_ANNOTATION_ADD_HIGHLIGHT",
    "crop": "EDITOR_ANNOTATION_CROP",
}


def build_editor_tool_hint(tool: Any) -> str:
    """Return the short instruction shown after changing the editor tool."""
    normalized_tool = str(tool or "select").strip().lower()
    label = tr(_EDITOR_TOOL_LABEL_KEYS.get(normalized_tool, "EDITOR_TOOL_SELECT"))
    is_zh = get_language() == "zh"
    cancel = "按 Esc 取消。" if is_zh else " Press Esc to cancel."
    if normalized_tool == "select":
        instruction = (
            "点击对象选中；拖动主体移动，拖动手柄编辑。"
            if is_zh
            else "Click an object to select it; drag its body to move it or a handle to edit it."
        )
    elif normalized_tool == "text":
        instruction = tr("EDITOR_DRAW_TEXT_HINT")
    elif normalized_tool == "curve":
        instruction = tr("EDITOR_DRAW_CURVE_HINT")
    elif normalized_tool == "highlight":
        instruction = "拖动创建高亮。" if is_zh else "Drag to create a highlight."
    elif normalized_tool == "crop":
        instruction = "拖动裁剪画布。" if is_zh else "Drag to crop the canvas."
    else:
        instruction = f"拖动创建{label}。" if is_zh else f"Drag to create a {label.lower()}."
    return f"{label}：{instruction}{cancel}" if is_zh else f"{label}: {instruction}{cancel}"


def build_editor_selection_hint(object_type: Any, label: Any) -> str:
    """Return the body and handle instruction for a selected editor object."""
    normalized_type = str(object_type or "").strip().lower()
    display_label = str(label or "").strip() or tr("EDITOR_OBJECT_LIST_LABEL")
    is_zh = get_language() == "zh"
    if normalized_type in {"line", "arrow"}:
        instruction = (
            "拖动主体移动；拖动端点调整大小。"
            if is_zh
            else "Drag the body to move it; drag an endpoint to resize it."
        )
    elif normalized_type == "curve":
        instruction = (
            "拖动主体移动；拖动端点或中间手柄调整曲线。"
            if is_zh
            else "Drag the body to move it; drag an endpoint or middle handle to reshape it."
        )
    elif normalized_type in {"text", "rectangle", "highlight"}:
        instruction = (
            "拖动主体移动；拖动手柄调整大小。"
            if is_zh
            else "Drag the body to move it; drag a handle to resize it."
        )
    elif normalized_type == "plot_series":
        instruction = "拖动曲线或数据点编辑。" if is_zh else "Drag the line or a data point to edit it."
    elif normalized_type == "legend":
        instruction = "拖动主体移动。" if is_zh else "Drag the body to move it."
    else:
        instruction = (
            "拖动主体移动；拖动手柄编辑。"
            if is_zh
            else "Drag the body to move it; drag a handle to edit it."
        )
    cancel = "按 Esc 取消。" if is_zh else " Press Esc to cancel."
    separator = "" if is_zh else ". "
    return f"{tr('EDITOR_SELECTED_STATUS_OBJECT', display_label)}{separator}{instruction}{cancel}"


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
        preview_geometry = drag_state.get("preview_geometry")
        inline_data = (
            {
                "x": preview_geometry.get("x_values", []),
                "y": preview_geometry.get("y_values", []),
            }
            if isinstance(preview_geometry, dict)
            else figure_object.get("data", {})
        )
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
        geometry = drag_state.get("preview_geometry")
        source = geometry if isinstance(geometry, dict) else figure_object
        if handle_index <= 0:
            x_value = number_formatter(source.get("x1"))
            y_value = number_formatter(source.get("y1"))
        else:
            x_value = number_formatter(source.get("x2"))
            y_value = number_formatter(source.get("y2"))
        return tr("EDITOR_DRAG_STATUS_ENDPOINT", label, x_value, y_value)
    if kind == "line-body":
        geometry = drag_state.get("preview_geometry")
        source = geometry if isinstance(geometry, dict) else figure_object
        return tr(
            "EDITOR_DRAG_STATUS_LINE",
            label,
            number_formatter(source.get("x1")),
            number_formatter(source.get("y1")),
            number_formatter(source.get("x2")),
            number_formatter(source.get("y2")),
        )
    if kind == "legend":
        style = figure_object.get("style", {}) if isinstance(figure_object.get("style"), dict) else {}
        layout = resolve_legend_layout(style)
        if layout.diagnostic:
            return f"{label}: {layout.diagnostic}"
        preview_geometry = drag_state.get("preview_geometry")
        bbox_to_anchor = (
            preview_geometry.get("bbox_to_anchor")
            if isinstance(preview_geometry, dict)
            else style.get("bbox_to_anchor")
        )
        if not isinstance(bbox_to_anchor, (list, tuple)) or len(bbox_to_anchor) < 2:
            return ""
        return tr(
            "EDITOR_DRAG_STATUS_LEGEND",
            label,
            number_formatter(bbox_to_anchor[0]),
            number_formatter(bbox_to_anchor[1]),
        )
    return ""
