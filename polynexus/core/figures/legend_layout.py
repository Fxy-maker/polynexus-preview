"""Canonical generated-legend placement and interaction geometry."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any

from matplotlib.transforms import Bbox


_UPPER_LOCATIONS = {"upper left", "upper center", "upper right"}


@dataclass(frozen=True)
class LegendLayout:
    """Resolved legend geometry shared by renderers and editor interactions."""

    mode: str
    anchor_axes: tuple[float, float] | None
    size_axes: tuple[float, float] | None
    content_bbox_display: Bbox | None = None
    interaction_bbox_display: Bbox | None = None
    diagnostic: str | None = None


def resolve_legend_layout(
    style: dict[str, Any] | None,
    *,
    axes: Any = None,
    content_bbox_display: Bbox | None = None,
) -> LegendLayout:
    """Resolve legacy legend style fields into one canonical layout.

    A two-value anchor with ``box_size`` is interpreted according to the
    existing editor contract: upper locations store the top-left anchor and
    therefore convert to a lower-left interaction anchor. Four-value
    ``bbox_to_anchor`` values retain Matplotlib's rectangle lower-left
    semantics. Missing dimensions remain automatic and use the measured
    content box for interaction.
    """

    normalized_style = style if isinstance(style, dict) else {}
    loc = str(normalized_style.get("loc", "") or "").strip().lower()
    raw_anchor = normalized_style.get("bbox_to_anchor")
    anchor_values = _finite_values(raw_anchor, minimum=2)
    raw_box = normalized_style.get("box_size")
    box_values = _finite_values(raw_box, minimum=2)

    diagnostic: str | None = None
    anchor_axes: tuple[float, float] | None = None
    size_axes: tuple[float, float] | None = None

    if raw_box is not None and box_values is None:
        diagnostic = "invalid legend box geometry; using automatic layout"
    elif box_values is not None:
        if anchor_values is None:
            diagnostic = "invalid legend anchor geometry; using automatic layout"
        else:
            width, height = box_values[:2]
            if width <= 0.0 or height <= 0.0:
                diagnostic = "invalid legend box geometry; using automatic layout"
            else:
                x, y = anchor_values[:2]
                bottom = y - height if loc in _UPPER_LOCATIONS else y
                anchor_axes = (x, bottom)
                size_axes = (width, height)
    elif anchor_values is not None and len(anchor_values) >= 4:
        x, y, width, height = anchor_values[:4]
        if width > 0.0 and height > 0.0:
            anchor_axes = (x, y)
            size_axes = (width, height)
        else:
            diagnostic = "invalid legend box geometry; using automatic layout"
    elif anchor_values is not None:
        # Keep a legacy point anchor available to inspector and drag callers;
        # without a size it is not enough to define a fixed interaction box.
        anchor_axes = (anchor_values[0], anchor_values[1])

    if anchor_axes is None or size_axes is None:
        return LegendLayout(
            mode="auto",
            anchor_axes=anchor_axes,
            size_axes=None,
            content_bbox_display=content_bbox_display,
            interaction_bbox_display=content_bbox_display,
            diagnostic=diagnostic,
        )

    interaction_bbox_display = _axes_bbox(axes, anchor_axes, size_axes)
    return LegendLayout(
        mode="fixed",
        anchor_axes=anchor_axes,
        size_axes=size_axes,
        content_bbox_display=content_bbox_display,
        interaction_bbox_display=interaction_bbox_display,
        diagnostic=diagnostic,
    )


def legend_style_updates(
    layout: LegendLayout,
    original_style: dict[str, Any] | None,
) -> dict[str, Any]:
    """Serialize a resolved layout while retaining unknown legacy keys."""

    updates = dict(original_style) if isinstance(original_style, dict) else {}
    if layout.mode != "fixed" or layout.anchor_axes is None or layout.size_axes is None:
        return updates
    x, y = layout.anchor_axes
    width, height = layout.size_axes
    updates.update(
        {
            "loc": "lower left",
            "bbox_to_anchor": [round(x, 12), round(y, 12)],
            "box_size": [round(width, 12), round(height, 12)],
        }
    )
    return updates


def _finite_values(value: object, *, minimum: int) -> list[float] | None:
    if not isinstance(value, (list, tuple)) or len(value) < minimum:
        return None
    values: list[float] = []
    for item in value:
        try:
            candidate = float(item)
        except (TypeError, ValueError):
            return None
        if not isfinite(candidate):
            return None
        values.append(candidate)
    return values


def _axes_bbox(axes: Any, anchor: tuple[float, float], size: tuple[float, float]) -> Bbox | None:
    if axes is None or not hasattr(axes, "transAxes"):
        return None
    try:
        lower_left = axes.transAxes.transform(anchor)
        upper_right = axes.transAxes.transform(
            (anchor[0] + size[0], anchor[1] + size[1])
        )
        bbox = Bbox.from_extents(
            float(lower_left[0]),
            float(lower_left[1]),
            float(upper_right[0]),
            float(upper_right[1]),
        )
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return None
    return bbox if all(isfinite(float(value)) for value in bbox.extents) else None
