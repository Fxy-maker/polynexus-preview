"""Qt-free capability and command contracts for editable figure documents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from matplotlib.colors import is_color_like


@dataclass(frozen=True)
class EditCapabilities:
    style: bool = False
    color: bool = False
    line_width: bool = False
    line_style: bool = False
    marker: bool = False
    marker_size: bool = False
    text: bool = False
    font_size: bool = False
    geometry: bool = False
    crop: bool = False
    deletable: bool = False
    reorderable: bool = False
    locked: bool = False


@dataclass(frozen=True)
class EditResult:
    changed: bool
    error_code: str = ""
    message: str = ""
    affected_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class SelectionState:
    object_id: str = ""
    source: str = ""


class EditCommand(Protocol):
    def apply(self, document: dict) -> tuple[EditResult, object]: ...

    def revert(self, document: dict, snapshot: object) -> EditResult: ...


_KNOWN_TYPES = {
    "image_background",
    "text",
    "line",
    "curve",
    "arrow",
    "rectangle",
    "highlight",
    "plot_series",
    "legend",
}


def object_type_for(object_payload: object) -> str:
    """Return the normalized object type without importing any UI module."""

    if not isinstance(object_payload, dict):
        return "unknown"
    for key in ("type", "object_type", "kind"):
        value = object_payload.get(key)
        if value is not None and str(value).strip():
            return str(value).strip().lower()
    return "unknown"


def capabilities_for(object_payload: object) -> EditCapabilities:
    """Describe the supported edits for an Origin-style figure object.

    The mapping is deliberately conservative: a type not explicitly listed here
    receives no editing capability.  An image background is intrinsically locked
    but retains its dedicated crop capability.
    """

    object_type = object_type_for(object_payload)
    explicitly_locked = bool(
        isinstance(object_payload, dict)
        and (object_payload.get("locked") or object_payload.get("lock"))
    )

    base = {
        "style": False,
        "color": False,
        "line_width": False,
        "line_style": False,
        "marker": False,
        "marker_size": False,
        "text": False,
        "font_size": False,
        "geometry": False,
        "crop": False,
        "deletable": False,
        "reorderable": False,
        "locked": explicitly_locked,
    }

    if object_type == "line":
        base.update(
            style=True,
            color=True,
            line_width=True,
            line_style=True,
            geometry=True,
            deletable=True,
            reorderable=True,
        )
    elif object_type == "curve":
        base.update(
            style=True,
            color=True,
            line_width=True,
            line_style=True,
            geometry=True,
            deletable=True,
            reorderable=True,
        )
    elif object_type == "arrow":
        base.update(
            style=True,
            color=True,
            line_width=True,
            line_style=True,
            geometry=True,
            deletable=True,
            reorderable=True,
        )
    elif object_type == "rectangle":
        base.update(
            style=True,
            color=True,
            line_width=True,
            line_style=True,
            geometry=True,
            deletable=True,
            reorderable=True,
        )
    elif object_type == "highlight":
        base.update(style=True, color=True, geometry=True, deletable=True, reorderable=True)
    elif object_type == "text":
        base.update(
            style=True,
            color=True,
            text=True,
            font_size=True,
            geometry=True,
            deletable=True,
            reorderable=True,
        )
    elif object_type == "plot_series":
        base.update(
            style=True,
            color=True,
            line_width=True,
            line_style=True,
            marker=True,
            marker_size=True,
            geometry=True,
            deletable=True,
            reorderable=True,
        )
    elif object_type == "image_background":
        base.update(crop=True, locked=True)
    elif object_type == "legend":
        base.update(text=True, geometry=True, deletable=True, reorderable=True)

    if object_type in _KNOWN_TYPES and object_type != "image_background" and explicitly_locked:
        for key in tuple(base):
            if key not in {"locked"}:
                base[key] = False

    return EditCapabilities(**base)


def is_known_object_type(object_payload: object) -> bool:
    """Return whether an object type has an explicit capability mapping."""

    return object_type_for(object_payload) in _KNOWN_TYPES


def is_valid_color(value: object) -> bool:
    """Return whether *value* is a finite Matplotlib-compatible color string."""

    if not isinstance(value, str):
        return False
    candidate = value.strip()
    if not candidate or candidate.casefold() in {"nan", "+nan", "-nan"}:
        return False
    try:
        return bool(is_color_like(candidate))
    except (TypeError, ValueError, OverflowError):
        return False


def validate_color(value: object) -> bool:
    """Compatibility alias for callers that prefer a validation verb."""

    return is_valid_color(value)


__all__ = [
    "EditCapabilities",
    "EditCommand",
    "EditResult",
    "SelectionState",
    "capabilities_for",
    "is_valid_color",
    "is_known_object_type",
    "object_type_for",
    "validate_color",
]
