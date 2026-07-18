"""Qt preview renderer for the immutable :mod:`plot_runtime.scene` model."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainterPath, QPen
from PySide6.QtWidgets import (
    QGraphicsItemGroup,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsTextItem,
)

from .scene import PanelScene, Point, RenderScene, SceneDiff, SceneNode, SceneTrace


class QtSceneRenderer:
    """Incrementally materialize a ``RenderScene`` in a ``QGraphicsScene``."""

    def __init__(self, graphics_scene: QGraphicsScene | None = None):
        self.graphics_scene = graphics_scene or QGraphicsScene()
        self._items: dict[str, Any] = {}
        self._scene: RenderScene | None = None

    def render(self, scene: RenderScene, diff: SceneDiff | None = None) -> QGraphicsScene:
        """Render a scene, replacing only nodes listed as added/updated/removed."""
        self.graphics_scene.setBackgroundBrush(QBrush(QColor(scene.background)))
        if self._scene is None:
            for panel in scene.panels:
                item = self._build_axes(panel)
                self._items[self._axis_id(panel)] = item
                self.graphics_scene.addItem(item)
            for node in scene.nodes:
                item = self._build_node(node)
                self._items[node.node_id] = item
                self.graphics_scene.addItem(item)
        else:
            actual_diff = diff or SceneDiff.between(self._scene, scene)
            previous_panels = {panel.panel_id: panel for panel in self._scene.panels}
            for panel in scene.panels:
                if previous_panels.get(panel.panel_id) != panel:
                    self._replace_item(self._axis_id(panel), self._build_axes(panel))
            for panel_id in previous_panels:
                if panel_id not in {panel.panel_id for panel in scene.panels}:
                    self._remove_item(f"{panel_id}::axes")
            after_nodes = {node.node_id: node for node in scene.nodes}
            for node_id in actual_diff.removed_ids:
                self._remove_item(node_id)
            for node_id in (*actual_diff.added_ids, *actual_diff.updated_ids):
                node = after_nodes.get(node_id)
                if node is not None:
                    self._replace_item(node_id, self._build_node(node))
        self._scene = scene
        return self.graphics_scene

    def item_ids(self) -> tuple[str, ...]:
        return tuple(self._items)

    def item_for_id(self, object_id: str) -> Any | None:
        return self._items.get(str(object_id))

    @staticmethod
    def trace(scene: RenderScene) -> SceneTrace:
        return SceneTrace.from_scene(scene, "qt")

    @staticmethod
    def _axis_id(panel: PanelScene) -> str:
        return f"{panel.panel_id}::axes"

    def _replace_item(self, item_id: str, item: Any) -> None:
        self._remove_item(item_id)
        self._items[item_id] = item
        self.graphics_scene.addItem(item)

    def _remove_item(self, item_id: str) -> None:
        old = self._items.pop(item_id, None)
        if old is not None:
            self.graphics_scene.removeItem(old)

    def _build_axes(self, panel: PanelScene) -> QGraphicsItemGroup:
        group = QGraphicsItemGroup()
        group.setData(0, self._axis_id(panel))
        rect = panel.axis_rect
        border = QGraphicsRectItem(QRectF(rect.left, rect.top, rect.width, rect.height))
        border.setPen(QPen(QColor("#333333"), 1.0))
        border.setBrush(Qt.BrushStyle.NoBrush)
        group.addToGroup(border)
        for tick in panel.x_ticks:
            line = QGraphicsLineItem(tick.position, rect.bottom, tick.position, rect.bottom + 5.0)
            line.setPen(QPen(QColor("#333333"), 1.0))
            group.addToGroup(line)
            group.addToGroup(self._text_item(tick.label, tick.position - 8.0, rect.bottom + 7.0, 8.0))
        for tick in panel.y_ticks:
            line = QGraphicsLineItem(rect.left - 5.0, tick.position, rect.left, tick.position)
            line.setPen(QPen(QColor("#333333"), 1.0))
            group.addToGroup(line)
            group.addToGroup(self._text_item(tick.label, rect.left - 34.0, tick.position - 7.0, 8.0))
        if panel.title:
            group.addToGroup(self._text_item(panel.title, rect.left, max(0.0, rect.top - 24.0), 10.0))
        if panel.x_label:
            group.addToGroup(self._text_item(panel.x_label, rect.left + rect.width / 2.0, rect.bottom + 25.0, 9.0))
        if panel.y_label:
            group.addToGroup(self._text_item(panel.y_label, max(0.0, rect.left - 45.0), rect.top - 2.0, 9.0))
        return group

    def _build_node(self, node: SceneNode) -> Any:
        if node.node_type in {"plot_series", "line"}:
            item = QGraphicsPathItem(self._path_for_node(node))
            item.setPen(self._pen(node.style_map))
            item.setData(0, node.node_id)
            return item
        if node.node_type in {"heatmap", "image_grid"}:
            group = QGraphicsItemGroup()
            group.setData(0, node.node_id)
            style = node.style_map
            values = [float(cell.value) for cell in node.rectangles]
            minimum = min(values) if values else 0.0
            maximum = max(values) if values else 1.0
            span = maximum - minimum or 1.0
            for cell in node.rectangles:
                rect = cell.rect
                item = QGraphicsRectItem(QRectF(rect.left, rect.top, rect.width, rect.height))
                if node.node_type == "image_grid":
                    normalized = max(0.0, min(1.0, (float(cell.value) - minimum) / span))
                    # QColor's HSV path is renderer-neutral enough for the
                    # preview while preserving each frame's intensity field.
                    color = QColor.fromHsvF((1.0 - normalized) * 0.66, 0.85, 0.95)
                else:
                    color = QColor(str(style.get("color", "#6699cc")))
                item.setPen(QPen(color, 0.5))
                item.setBrush(QBrush(color))
                group.addToGroup(item)
            return group
        if node.node_type == "legend":
            group = QGraphicsItemGroup()
            group.setData(0, node.node_id)
            if node.bounds is not None:
                bounds = node.bounds
                box = QGraphicsRectItem(QRectF(bounds.left, bounds.top, bounds.width, bounds.height))
                box.setPen(QPen(QColor("#777777"), 1.0))
                box.setBrush(QBrush(QColor(255, 255, 255, 220)))
                group.addToGroup(box)
            if node.text_anchor is not None:
                group.addToGroup(self._text_item(node.text, node.text_anchor.x, node.text_anchor.y - 12.0, 9.0))
            return group
        if node.node_type == "text":
            anchor = node.text_anchor or Point(0.0, 0.0)
            item = self._text_item(node.text, anchor.x, anchor.y, 9.0)
            item.setData(0, node.node_id)
            return item
        item = QGraphicsItemGroup()
        item.setData(0, node.node_id)
        return item

    @staticmethod
    def _path_for_node(node: SceneNode) -> QPainterPath:
        path = QPainterPath()
        if node.points:
            path.moveTo(QPointF(node.points[0].x, node.points[0].y))
            for point in node.points[1:]:
                path.lineTo(QPointF(point.x, point.y))
        for segment in node.segments:
            path.moveTo(QPointF(segment.start.x, segment.start.y))
            path.lineTo(QPointF(segment.end.x, segment.end.y))
        return path

    @staticmethod
    def _pen(style: dict[str, Any]) -> QPen:
        pen = QPen(QColor(str(style.get("color", "#1f77b4"))))
        pen.setWidthF(float(style.get("line_width", 1.0)))
        if style.get("line_style") == "dashed":
            pen.setStyle(Qt.PenStyle.DashLine)
        return pen

    @staticmethod
    def _text_item(text: str, x: float, y: float, size: float) -> QGraphicsTextItem:
        item = QGraphicsTextItem(str(text))
        item.setPos(x, y)
        item.setFont(QFont("Sans Serif", int(size)))
        return item
