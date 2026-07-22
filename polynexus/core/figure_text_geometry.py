"""Shared geometry rules for editable figure text boxes."""

from __future__ import annotations


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


__all__ = ["text_box_anchor"]
