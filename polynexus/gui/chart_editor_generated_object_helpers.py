"""Pure object-level helpers used by the chart editor."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from ..core.figures.legend_geometry import import_legend_geometry
from .chart_editor_generated_helpers import optional_float


def generated_object_capabilities(
    figure_object: Any,
    *,
    selected_plot_series_point_geometry: bool,
) -> dict[str, bool]:
    object_type = str(figure_object.get("type", "") or "")
    chart_kind = str(figure_object.get("chart_kind", "") or "")
    is_image_grid = object_type == "image_grid" or chart_kind == "image_grid"
    is_legend = object_type == "legend"
    is_line = object_type in {"line", "curve"}
    return {
        "renameable": not is_legend,
        "style": not is_image_grid,
        "deletable": not is_legend,
        "reorderable": not is_legend and not is_image_grid,
        "font_size": object_type in {"text", "legend"},
        "geometry": is_line
        or is_legend
        or (object_type == "plot_series" and selected_plot_series_point_geometry),
        "line_style": object_type in {"line", "curve", "plot_series"}
        and chart_kind not in {"heatmap", "bar", "barh", "image_grid", "scatter"},
        "marker": object_type == "plot_series"
        and chart_kind not in {"heatmap", "bar", "barh", "image_grid"},
        "marker_size": object_type == "plot_series"
        and chart_kind not in {"heatmap", "bar", "barh", "image_grid"},
    }


def generated_object_geometry_config(
    figure_object: Any,
    *,
    legend_anchor: tuple[float, float] | None,
    point_index: int | None,
    inline_data: Mapping[str, Sequence[Any]] | None,
) -> dict[str, Any]:
    object_type = str(figure_object.get("type", "") or "")
    if object_type == "legend":
        if legend_anchor is None:
            return {
                "mode": "box",
                "enabled": (False, False, False, False),
                "values": (0.0, 0.0, 0.0, 0.0),
            }
        style = figure_object.get("style", {})
        imported_geometry = import_legend_geometry(style if isinstance(style, dict) else {})
        if imported_geometry.rect_axes is not None:
            return {
                "mode": "box",
                "enabled": (True, True, True, True),
                "values": tuple(float(value) for value in imported_geometry.rect_axes),
            }
        anchor = imported_geometry.anchor_axes or legend_anchor
        if anchor is None:
            return {
                "mode": "box",
                "enabled": (False, False, False, False),
                "values": (0.0, 0.0, 0.0, 0.0),
            }
        return {
            "mode": "point",
            "enabled": (True, True, False, False),
            "values": (float(anchor[0]), float(anchor[1]), 0.0, 0.0),
        }
    if object_type == "plot_series":
        if point_index is None or not isinstance(inline_data, dict):
            return {
                "mode": "box",
                "enabled": (False, False, False, False),
                "values": (0.0, 0.0, 0.0, 0.0),
            }
        x_values = list(inline_data.get("x", []) or [])
        y_values = list(inline_data.get("y", []) or [])
        if point_index < 0 or point_index >= min(len(x_values), len(y_values)):
            return {
                "mode": "box",
                "enabled": (False, False, False, False),
                "values": (0.0, 0.0, 0.0, 0.0),
            }
        return {
            "mode": "point",
            "enabled": (True, True, False, False),
            "values": (
                float(optional_float(x_values[point_index]) or 0.0),
                float(optional_float(y_values[point_index]) or 0.0),
                0.0,
                0.0,
            ),
        }
    if object_type not in {"line", "curve"}:
        return {
            "mode": "box",
            "enabled": (False, False, False, False),
            "values": (0.0, 0.0, 0.0, 0.0),
        }
    x1 = float(optional_float(figure_object.get("x1")) or 0.0)
    y1 = float(optional_float(figure_object.get("y1")) or 0.0)
    x2 = optional_float(figure_object.get("x2"))
    y2 = optional_float(figure_object.get("y2"))
    if x2 is None:
        return {
            "mode": "vertical",
            "enabled": (True, False, False, False),
            "values": (x1, 0.0, 0.0, 0.0),
        }
    if y2 is None:
        return {
            "mode": "horizontal",
            "enabled": (False, True, False, False),
            "values": (0.0, y1, 0.0, 0.0),
        }
    return {
        "mode": "segment",
        "enabled": (True, True, True, True),
        "values": (x1, y1, float(x2), float(y2)),
    }


def generated_object_xy(
    figure_object: Any,
    data_sources: Mapping[str, Mapping[str, Sequence[Any]]],
) -> tuple[list[Any], list[Any]]:
    inline_data = figure_object.get("data", {})
    if isinstance(inline_data, dict):
        x_values = inline_data.get("x", inline_data.get("x_values", []))
        y_values = inline_data.get("y", inline_data.get("y_values", []))
        if x_values and y_values:
            return list(x_values), list(y_values)
    return (
        generated_column_values(figure_object, data_sources, "x_column"),
        generated_column_values(figure_object, data_sources, "y_column"),
    )


def generated_column_values(
    figure_object: Any,
    data_sources: Mapping[str, Mapping[str, Sequence[Any]]],
    key: str,
) -> list[Any]:
    data_ref = str(figure_object.get("data_ref", "") or "")
    column = str(figure_object.get(key, "") or "")
    if not data_ref or not column:
        return []
    return list(data_sources.get(data_ref, {}).get(column, []))
