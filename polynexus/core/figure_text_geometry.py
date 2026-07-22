"""Shared geometry rules for editable figure text boxes."""

from __future__ import annotations

import math


AXES_MIN = 0.0
AXES_MAX = 1.0


def _finite(value: float, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return float(default)
    return number if math.isfinite(number) else float(default)


def clamp_axes_box(x: float, y: float, width: float, height: float) -> dict[str, float]:
    """Normalize a positive text box so it stays inside an Axes rectangle."""

    width = min(max(_finite(width), 0.0), AXES_MAX)
    height = min(max(_finite(height), 0.0), AXES_MAX)
    x = min(max(_finite(x), AXES_MIN), AXES_MAX - width)
    y = min(max(_finite(y), AXES_MIN), AXES_MAX - height)
    return {"x": x, "y": y, "width": width, "height": height}


def axes_box_from_display(display_rect, axes_transform) -> dict[str, float]:
    """Convert a display-pixel rectangle through ``axes.transAxes``."""

    if not isinstance(display_rect, (tuple, list)) or len(display_rect) < 4:
        raise ValueError("display_rect must contain x, y, width, and height")
    x0, y0, width, height = (_finite(value) for value in display_rect[:4])
    inverse = axes_transform.inverted()
    first_x, first_y = inverse.transform((x0, y0))
    second_x, second_y = inverse.transform((x0 + width, y0 + height))
    left, right = sorted((float(first_x), float(second_x)))
    bottom, top = sorted((float(first_y), float(second_y)))
    return clamp_axes_box(left, bottom, right - left, top - bottom)


def is_axes_text_box(payload) -> bool:
    """Return whether a figure text object uses the viewport contract."""

    return (
        isinstance(payload, dict)
        and str(payload.get("type", "") or "").lower() == "text"
        and str(payload.get("coordinate_space", "") or "").lower() == "axes"
    )


def text_box_anchor(
    x: float,
    y: float,
    width: float = 0.0,
    height: float = 0.0,
    *,
    horizontal_alignment: str | None = None,
    vertical_alignment: str | None = None,
) -> tuple[float, float]:
    """Return the Matplotlib anchor for a persisted text-box geometry.

    Persisted box coordinates use the lower-left corner.  A boxed text object
    defaults to a left/top visual anchor so its glyphs remain inside the box;
    unboxed legacy text keeps its center/bottom compatibility behavior.
    """

    anchor_x = float(x)
    anchor_y = float(y)
    box_width = float(width or 0.0)
    box_height = float(height or 0.0)
    has_box = box_width > 0.0 and box_height > 0.0
    horizontal = str(
        horizontal_alignment
        or ("left" if has_box else "center")
    )
    vertical = str(
        vertical_alignment
        or ("top" if has_box else "bottom")
    )
    if has_box:
        if horizontal == "center":
            anchor_x += box_width / 2.0
        elif horizontal == "right":
            anchor_x += box_width
        if vertical == "center":
            anchor_y += box_height / 2.0
        elif vertical == "top":
            anchor_y += box_height
    return anchor_x, anchor_y


__all__ = [
    "axes_box_from_display",
    "clamp_axes_box",
    "is_axes_text_box",
    "text_box_anchor",
]
