"""JSON-friendly object schema helpers for editable figures."""

from __future__ import annotations

from copy import deepcopy
import math
from uuid import uuid4


KNOWN_FIGURE_OBJECT_TYPES = {
    "image_background",
    "text",
    "arrow",
    "line",
    "rectangle",
    "highlight",
    "axis",
    "plot_series",
    "heatmap",
    "image_grid",
    "legend",
    "panel_label",
}

STYLE_KEYS = {"color", "font_size", "line_width", "alpha", "fill", "stroke"}
GEOMETRY_KEYS = ("x", "y", "width", "height", "x1", "y1", "x2", "y2")

DEFAULT_OBJECT_NAMES = {
    "image_background": "Background",
    "text": "Text",
    "arrow": "Arrow",
    "line": "Line",
    "rectangle": "Rectangle",
    "highlight": "Highlight",
    "axis": "Axis",
    "plot_series": "Plot Series",
    "heatmap": "Heatmap",
    "image_grid": "Image Grid",
    "legend": "Legend",
    "panel_label": "Panel Label",
}


def normalize_figure_object(payload: dict) -> dict:
    obj = deepcopy(payload) if isinstance(payload, dict) else {}
    object_type = str(obj.get("type") or "unknown").strip().lower()
    if object_type not in KNOWN_FIGURE_OBJECT_TYPES:
        obj.setdefault("original_type", object_type)
        object_type = "unknown"
    obj["type"] = object_type
    obj.setdefault("id", f"obj-{uuid4().hex[:12]}")
    obj.setdefault("name", DEFAULT_OBJECT_NAMES.get(object_type, "Object"))
    obj.setdefault("visible", True)
    obj.setdefault("locked", False)
    obj.setdefault("z_index", 0)
    obj["layer_id"] = "layer-1"
    bounds = obj.get("bounds")
    if not isinstance(bounds, dict):
        bounds = {}
    for key in GEOMETRY_KEYS:
        if key in bounds or key not in obj:
            continue
        try:
            value = float(obj[key])
        except (TypeError, ValueError, OverflowError):
            continue
        if math.isfinite(value):
            bounds[key] = value
    obj["bounds"] = bounds
    if not isinstance(obj.get("style"), dict):
        obj["style"] = {}
    return obj


def style_from_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {}
    return {
        key: deepcopy(payload[key])
        for key in STYLE_KEYS
        if key in payload
    }
