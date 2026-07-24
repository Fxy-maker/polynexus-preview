"""Canonical runtime geometry for editable legends.

The persisted document may still contain the historical Matplotlib placement
fields.  This module is the single import boundary for those fields; editor
interaction code works with :class:`LegendGeometry` instead.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import isfinite, sqrt
from typing import Any

from matplotlib.transforms import Bbox

from .legend_layout import resolve_legend_layout


DEFAULT_FONT_SIZE = 9.0
MIN_FONT_SIZE = 6.0
MAX_FONT_SIZE = 72.0
MIN_DISPLAY_SIZE = 8.0


@dataclass(frozen=True)
class LegendGeometry:
    """One legend rectangle shared by rendering and editor interaction."""

    panel_id: str = ""
    rect_axes: tuple[float, float, float, float] | None = None
    rect_display: Bbox | None = None
    font_size: float = DEFAULT_FONT_SIZE
    ncol: int = 1
    diagnostic: str | None = None

    def with_display_rect(self, rect: Bbox | None, *, axes: Any = None) -> "LegendGeometry":
        normalized = _finite_bbox(rect)
        rect_axes = self.rect_axes
        if normalized is not None and axes is not None:
            rect_axes = _display_bbox_to_axes(axes, normalized)
        return replace(self, rect_display=normalized, rect_axes=rect_axes)

    def moved(self, dx_display: float, dy_display: float, *, axes: Any = None) -> "LegendGeometry":
        if self.rect_display is None:
            return self
        try:
            dx = float(dx_display)
            dy = float(dy_display)
        except (TypeError, ValueError):
            return self
        if not isfinite(dx) or not isfinite(dy):
            return self
        rect = Bbox.from_extents(
            self.rect_display.x0 + dx,
            self.rect_display.y0 + dy,
            self.rect_display.x1 + dx,
            self.rect_display.y1 + dy,
        )
        return self.with_display_rect(rect, axes=axes)

    def resized(
        self,
        handle_index: int,
        target_display_point: tuple[float, float],
        *,
        axes: Any = None,
    ) -> "LegendGeometry":
        """Resize from one corner while preserving the opposite corner."""

        if self.rect_display is None or int(handle_index) not in {0, 1, 2, 3}:
            return self
        try:
            target_x = float(target_display_point[0])
            target_y = float(target_display_point[1])
        except (TypeError, ValueError, IndexError):
            return self
        if not isfinite(target_x) or not isfinite(target_y):
            return self

        left, bottom = float(self.rect_display.x0), float(self.rect_display.y0)
        right, top = float(self.rect_display.x1), float(self.rect_display.y1)
        original_width = max(right - left, MIN_DISPLAY_SIZE)
        original_height = max(top - bottom, MIN_DISPLAY_SIZE)
        if int(handle_index) in {0, 3}:
            left = min(target_x, right - MIN_DISPLAY_SIZE)
        else:
            right = max(target_x, left + MIN_DISPLAY_SIZE)
        if int(handle_index) in {0, 1}:
            bottom = min(target_y, top - MIN_DISPLAY_SIZE)
        else:
            top = max(target_y, bottom + MIN_DISPLAY_SIZE)
        width = max(right - left, MIN_DISPLAY_SIZE)
        height = max(top - bottom, MIN_DISPLAY_SIZE)
        area_scale = sqrt((width / original_width) * (height / original_height))
        font_size = min(MAX_FONT_SIZE, max(MIN_FONT_SIZE, self.font_size * area_scale))
        return self.with_display_rect(
            Bbox.from_bounds(left, bottom, width, height),
            axes=axes,
        ).with_font_size(font_size)

    def with_font_size(self, value: float) -> "LegendGeometry":
        try:
            font_size = float(value)
        except (TypeError, ValueError):
            return self
        if not isfinite(font_size) or font_size <= 0.0:
            return self
        return replace(
            self,
            font_size=min(MAX_FONT_SIZE, max(MIN_FONT_SIZE, font_size)),
        )

    def serialize(self, original_style: dict[str, Any] | None = None) -> dict[str, Any]:
        """Serialize canonical geometry while dropping legacy placement keys."""

        style = dict(original_style) if isinstance(original_style, dict) else {}
        for key in ("loc", "bbox_to_anchor", "box_size"):
            style.pop(key, None)
        if self.rect_axes is not None:
            x, y, width, height = self.rect_axes
            style["legend_geometry"] = {
                "space": "axes",
                "x": round(float(x), 12),
                "y": round(float(y), 12),
                "width": round(float(width), 12),
                "height": round(float(height), 12),
            }
        style["font_size"] = round(float(self.font_size), 3)
        style["ncol"] = max(1, int(self.ncol))
        return style


def import_legend_geometry(
    style: dict[str, Any] | None,
    *,
    axes: Any = None,
    content_bbox_display: Bbox | None = None,
    panel_id: str = "",
) -> LegendGeometry:
    """Import canonical or legacy style fields into one runtime geometry."""

    normalized_style = style if isinstance(style, dict) else {}
    font_size = _positive_float(normalized_style.get("font_size")) or DEFAULT_FONT_SIZE
    ncol = _positive_int(normalized_style.get("ncol")) or 1
    diagnostic: str | None = None
    rect_axes: tuple[float, float, float, float] | None = None

    explicit = normalized_style.get("legend_geometry")
    if explicit is not None:
        rect_axes = _axes_rect(explicit)
        if rect_axes is None:
            diagnostic = "invalid legend geometry; using automatic layout"
    else:
        layout = resolve_legend_layout(
            normalized_style,
            axes=axes,
            content_bbox_display=content_bbox_display,
        )
        if layout.anchor_axes is not None and layout.size_axes is not None:
            rect_axes = (*layout.anchor_axes, *layout.size_axes)
        diagnostic = layout.diagnostic

    rect_display = None
    if rect_axes is not None and axes is not None:
        rect_display = _axes_rect_to_display(axes, rect_axes)
    elif content_bbox_display is not None:
        rect_display = _finite_bbox(content_bbox_display)
        if rect_axes is None and rect_display is not None and axes is not None:
            rect_axes = _display_bbox_to_axes(axes, rect_display)

    return LegendGeometry(
        panel_id=str(panel_id or ""),
        rect_axes=rect_axes,
        rect_display=rect_display,
        font_size=font_size,
        ncol=ncol,
        diagnostic=diagnostic,
    )


def measure_legend_geometry(
    geometry: LegendGeometry,
    legend: Any,
    renderer: Any,
    *,
    axes: Any = None,
) -> LegendGeometry:
    """Refresh a geometry snapshot from a live Matplotlib legend artist."""

    try:
        bbox = legend.get_window_extent(renderer)
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return geometry
    return geometry.with_display_rect(bbox, axes=axes)


def _axes_rect(value: object) -> tuple[float, float, float, float] | None:
    if not isinstance(value, dict) or str(value.get("space", "axes")) != "axes":
        return None
    values = [
        _finite_float(value.get("x")),
        _finite_float(value.get("y")),
        _finite_float(value.get("width")),
        _finite_float(value.get("height")),
    ]
    if any(item is None for item in values) or values[2] <= 0.0 or values[3] <= 0.0:
        return None
    return tuple(float(item) for item in values)  # type: ignore[arg-type]


def _axes_rect_to_display(axes: Any, rect: tuple[float, float, float, float]) -> Bbox | None:
    try:
        x, y, width, height = rect
        lower_left = axes.transAxes.transform((x, y))
        upper_right = axes.transAxes.transform((x + width, y + height))
        return _finite_bbox(Bbox.from_extents(*lower_left, *upper_right))
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return None


def _display_bbox_to_axes(axes: Any, bbox: Bbox) -> tuple[float, float, float, float] | None:
    try:
        lower_left = axes.transAxes.inverted().transform((bbox.x0, bbox.y0))
        upper_right = axes.transAxes.inverted().transform((bbox.x1, bbox.y1))
        return (
            float(lower_left[0]),
            float(lower_left[1]),
            float(upper_right[0] - lower_left[0]),
            float(upper_right[1] - lower_left[1]),
        )
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return None


def _finite_bbox(value: Bbox | None) -> Bbox | None:
    if value is None:
        return None
    try:
        values = (float(value.x0), float(value.y0), float(value.x1), float(value.y1))
    except (AttributeError, TypeError, ValueError):
        return None
    if not all(isfinite(item) for item in values) or values[2] <= values[0] or values[3] <= values[1]:
        return None
    return Bbox.from_extents(*values)


def _finite_float(value: object) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if isfinite(parsed) else None


def _positive_float(value: object) -> float | None:
    parsed = _finite_float(value)
    return parsed if parsed is not None and parsed > 0.0 else None


def _positive_int(value: object) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None
