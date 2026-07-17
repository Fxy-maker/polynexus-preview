"""Project JSON-friendly annotation objects into a Qt graphics scene."""

from __future__ import annotations

import math
from copy import deepcopy

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsScene, QGraphicsTextItem


class AnnotationRenderAdapter:
    """Render annotation payloads without owning persistence or edit history."""

    _PROJECTED_ROLE = 1
    _SUPPORTED_TYPES = {"text", "line", "arrow", "rectangle", "highlight"}

    def __init__(self, scene: QGraphicsScene):
        self._scene = scene
        self._objects: dict[str, dict] = {}
        self._items: dict[str, object] = {}
        self._order: list[str] = []

    def replace_objects(self, objects: list[dict]) -> dict[str, object]:
        self.clear()
        projected: dict[str, object] = {}
        for payload in objects if isinstance(objects, list) else []:
            item = self.sync_object(payload)
            if item is not None:
                object_id = self._object_id(payload)
                projected[object_id] = item
        return projected

    def sync_object(self, object_payload: dict) -> object | None:
        if not isinstance(object_payload, dict):
            return None
        object_id = self._object_id(object_payload)
        if not object_id:
            return None
        if self._object_type(object_payload) not in self._SUPPORTED_TYPES:
            self._remove_object(object_id)
            return None

        existing = object_id in self._objects
        self._remove_item(object_id)
        if not existing:
            self._order.append(object_id)
        payload = deepcopy(object_payload)
        item = self._draw_object(payload)
        if item is None:
            if not existing:
                self._order.remove(object_id)
            self._objects.pop(object_id, None)
            return None
        self._objects[object_id] = payload
        self._items[object_id] = item
        return item

    def clear(self) -> None:
        for object_id in list(self._items):
            self._remove_item(object_id)
        self._objects.clear()
        self._items.clear()
        self._order.clear()

    def scene_state(self) -> list[dict]:
        return [deepcopy(self._objects[object_id]) for object_id in self._order if object_id in self._objects]

    def _draw_object(self, payload: dict):
        if payload.get("visible", True) is False:
            return None
        kind = self._object_type(payload)
        if kind == "text":
            item = QGraphicsTextItem(str(payload.get("text", "")))
            item.setDefaultTextColor(QColor(self._color(payload, "#111111")))
            font = item.font()
            font.setPointSize(max(1, int(self._number(payload, "font_size", 12))))
            item.setFont(font)
            item.setPos(self._x(payload, "x"), self._y(payload, "y"))
            self._scene.addItem(item)
            self._configure_item(item, payload)
            return item

        if kind in {"rectangle", "highlight"}:
            rect = QRectF(
                self._x(payload, "x"),
                self._y(payload, "y"),
                self._width(payload, "width"),
                self._height(payload, "height"),
            )
            if kind == "rectangle":
                pen = QPen(QColor(self._color(payload, "#D55E00")))
                pen.setWidthF(max(0.1, self._number(payload, "line_width", 2.0)))
                item = self._scene.addRect(rect, pen, QBrush(Qt.NoBrush))
            else:
                color = QColor(self._color(payload, "#F0E442"))
                color.setAlphaF(min(1.0, max(0.0, self._number(payload, "alpha", 0.35))))
                item = self._scene.addRect(rect, QPen(Qt.NoPen), QBrush(color))
            self._configure_item(item, payload)
            return item

        if kind in {"line", "arrow"}:
            x1 = self._x(payload, "x1")
            y1 = self._y(payload, "y1")
            x2 = self._x(payload, "x2")
            y2 = self._y(payload, "y2")
            pen = QPen(QColor(self._color(payload, "#D55E00")))
            pen.setWidthF(max(0.1, self._number(payload, "line_width", 2.0)))
            line_item = self._scene.addLine(x1, y1, x2, y2, pen)
            if kind == "arrow":
                head_item = self._draw_arrow_head(x1, y1, x2, y2, pen)
                item = self._scene.createItemGroup([line_item, head_item])
            else:
                item = line_item
            self._configure_item(item, payload)
            return item
        return None

    def _configure_item(self, item, payload: dict) -> None:
        object_id = self._object_id(payload)
        item.setData(0, object_id)
        item.setData(self._PROJECTED_ROLE, True)
        item.setFlag(item.GraphicsItemFlag.ItemIsSelectable, True)
        item.setFlag(item.GraphicsItemFlag.ItemIsMovable, True)
        item.setFlag(item.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        item.setSelected(bool(payload.get("selected", payload.get("is_selected", False))))

    def _draw_arrow_head(self, x1: float, y1: float, x2: float, y2: float, pen: QPen):
        angle = math.atan2(y2 - y1, x2 - x1)
        size = max(8.0, pen.widthF() * 5.0)
        left = QPointF(
            x2 - size * math.cos(angle - math.pi / 6.0),
            y2 - size * math.sin(angle - math.pi / 6.0),
        )
        right = QPointF(
            x2 - size * math.cos(angle + math.pi / 6.0),
            y2 - size * math.sin(angle + math.pi / 6.0),
        )
        path = QPainterPath(QPointF(x2, y2))
        path.lineTo(left)
        path.lineTo(right)
        path.closeSubpath()
        return self._scene.addPath(path, pen, QBrush(pen.color()))

    def _remove_item(self, object_id: str) -> None:
        item = self._items.pop(object_id, None)
        if item is not None:
            self._scene.removeItem(item)

    def _remove_object(self, object_id: str) -> None:
        self._remove_item(object_id)
        self._objects.pop(object_id, None)
        if object_id in self._order:
            self._order.remove(object_id)

    def _scene_size(self) -> tuple[float, float]:
        rect = self._scene.sceneRect()
        return max(1.0, float(rect.width())), max(1.0, float(rect.height()))

    def _geometry(self, payload: dict) -> dict:
        for key in ("geometry", "bounds"):
            value = payload.get(key)
            if isinstance(value, dict):
                return value
        return payload

    def _style_value(self, payload: dict, key: str, default):
        style = payload.get("style")
        if isinstance(style, dict) and key in style:
            return style[key]
        return payload.get(key, default)

    def _number(self, payload: dict, key: str, default: float) -> float:
        value = self._style_value(payload, key, default)
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return float(default)
        return number if math.isfinite(number) else float(default)

    def _x(self, payload: dict, key: str) -> float:
        value = self._geometry(payload).get(key, payload.get(key, 0.0))
        width, _ = self._scene_size()
        return self._number_from_geometry(value, width)

    def _y(self, payload: dict, key: str) -> float:
        value = self._geometry(payload).get(key, payload.get(key, 0.0))
        _, height = self._scene_size()
        return self._number_from_geometry(value, height)

    def _width(self, payload: dict, key: str) -> float:
        return self._x(payload, key)

    def _height(self, payload: dict, key: str) -> float:
        return self._y(payload, key)

    @staticmethod
    def _number_from_geometry(value, scale: float) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            number = 0.0
        if not math.isfinite(number):
            number = 0.0
        return number * scale

    @staticmethod
    def _object_id(payload: dict) -> str:
        value = payload.get("id", payload.get("object_id", ""))
        return str(value).strip() if value is not None else ""

    @staticmethod
    def _object_type(payload: dict) -> str:
        value = payload.get("type", payload.get("object_type", payload.get("kind", "")))
        return str(value).strip().lower() if value is not None else ""

    @staticmethod
    def _color(payload: dict, default: str) -> str:
        value = payload.get("color")
        style = payload.get("style")
        if value is None and isinstance(style, dict):
            value = style.get("color", style.get("stroke"))
        return str(value or default)


__all__ = ["AnnotationRenderAdapter"]
