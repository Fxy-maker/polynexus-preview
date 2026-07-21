"""Renderer-neutral geometry records used by direct editor interactions."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, ClassVar


MIN_SIZE = 1e-9


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _payload_geometry(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    for key in ("geometry", "bounds"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            return {**payload, **nested}
    return payload


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    width: float
    height: float

    MIN_SIZE: ClassVar[float] = MIN_SIZE

    def __post_init__(self) -> None:
        for name in ("x", "y", "width", "height"):
            value = _number(getattr(self, name))
            if value is None:
                raise ValueError(f"invalid box coordinate: {name}")
            object.__setattr__(self, name, value)

    @classmethod
    def from_drag(cls, start, end) -> Box | None:
        if not isinstance(start, (tuple, list)) or not isinstance(end, (tuple, list)):
            return None
        if len(start) < 2 or len(end) < 2:
            return None
        x1, y1, x2, y2 = (_number(value) for value in (*start[:2], *end[:2]))
        if None in {x1, y1, x2, y2}:
            return None
        return cls(
            min(x1, x2),
            min(y1, y2),
            max(abs(x2 - x1), cls.MIN_SIZE),
            max(abs(y2 - y1), cls.MIN_SIZE),
        )

    @classmethod
    def from_payload(cls, payload) -> Box | None:
        values = _payload_geometry(payload)
        numbers = [_number(values.get(key)) for key in ("x", "y", "width", "height")]
        if any(value is None for value in numbers):
            return None
        return cls(*numbers)

    def translated(self, dx: float, dy: float) -> Box:
        return Box(self.x + float(dx), self.y + float(dy), self.width, self.height)

    def resized(self, *, x=None, y=None, width=None, height=None) -> Box:
        return Box(
            self.x if x is None else x,
            self.y if y is None else y,
            self.width if width is None else max(float(width), self.MIN_SIZE),
            self.height if height is None else max(float(height), self.MIN_SIZE),
        )

    def to_payload(self) -> dict[str, float]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }


@dataclass(frozen=True)
class Segment:
    x1: float
    y1: float
    x2: float
    y2: float

    def __post_init__(self) -> None:
        for name in ("x1", "y1", "x2", "y2"):
            value = _number(getattr(self, name))
            if value is None:
                raise ValueError(f"invalid segment coordinate: {name}")
            object.__setattr__(self, name, value)

    @classmethod
    def from_drag(cls, start, end) -> Segment | None:
        if not isinstance(start, (tuple, list)) or not isinstance(end, (tuple, list)):
            return None
        if len(start) < 2 or len(end) < 2:
            return None
        values = [_number(value) for value in (*start[:2], *end[:2])]
        if any(value is None for value in values):
            return None
        return cls(*values)

    @classmethod
    def from_payload(cls, payload) -> Segment | None:
        values = _payload_geometry(payload)
        numbers = [_number(values.get(key)) for key in ("x1", "y1", "x2", "y2")]
        if any(value is None for value in numbers):
            return None
        return cls(*numbers)

    def translated(self, dx: float, dy: float) -> Segment:
        return Segment(self.x1 + float(dx), self.y1 + float(dy), self.x2 + float(dx), self.y2 + float(dy))

    def to_payload(self) -> dict[str, float]:
        return {"x1": self.x1, "y1": self.y1, "x2": self.x2, "y2": self.y2}


@dataclass(frozen=True)
class Curve:
    x1: float
    y1: float
    control_x: float
    control_y: float
    x2: float
    y2: float

    def __post_init__(self) -> None:
        for name in ("x1", "y1", "control_x", "control_y", "x2", "y2"):
            value = _number(getattr(self, name))
            if value is None:
                raise ValueError(f"invalid curve coordinate: {name}")
            object.__setattr__(self, name, value)

    @classmethod
    def from_payload(cls, payload) -> Curve | None:
        values = _payload_geometry(payload)
        numbers = [
            _number(values.get(key))
            for key in ("x1", "y1", "control_x", "control_y", "x2", "y2")
        ]
        if any(value is None for value in numbers):
            return None
        return cls(*numbers)

    def translated(self, dx: float, dy: float) -> Curve:
        dx = float(dx)
        dy = float(dy)
        return Curve(
            self.x1 + dx,
            self.y1 + dy,
            self.control_x + dx,
            self.control_y + dy,
            self.x2 + dx,
            self.y2 + dy,
        )

    def to_payload(self) -> dict[str, float]:
        return {
            "x1": self.x1,
            "y1": self.y1,
            "control_x": self.control_x,
            "control_y": self.control_y,
            "x2": self.x2,
            "y2": self.y2,
        }


__all__ = ["Box", "Curve", "MIN_SIZE", "Segment"]
