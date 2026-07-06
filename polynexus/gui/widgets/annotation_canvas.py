"""Minimal figure annotation canvas for static exported images."""

from __future__ import annotations

import math
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsTextItem, QGraphicsView, QVBoxLayout, QWidget


class AnnotationCanvas(QWidget):
    tool_changed = Signal(str)
    selection_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self._scene.selectionChanged.connect(self._on_scene_selection_changed)
        self._view = QGraphicsView(self._scene)
        self._view.setAlignment(Qt.AlignCenter)
        self._view.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._image_path = ""
        self._image_width = 0
        self._image_height = 0
        self._annotations: list[dict] = []
        self._undo_stack: list[dict] = []
        self._redo_stack: list[dict] = []
        self._selected_annotation_id = ""
        self._zoom_level = 1.0
        self._zoom_mode = "fit"
        self._current_tool = "select"
        self._draw_start: QPointF | None = None
        self._clipboard_annotation: dict | None = None
        self.setFocusPolicy(Qt.StrongFocus)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)
        self._view.viewport().installEventFilter(self)

    def load_image(self, path: str) -> bool:
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            return False

        self._scene.clear()
        self._annotations = []
        self._undo_stack = []
        self._redo_stack = []
        self._selected_annotation_id = ""
        self._image_path = str(Path(path))
        self._image_width = pixmap.width()
        self._image_height = pixmap.height()
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._pixmap_item.setPos(0, 0)
        self._scene.setSceneRect(QRectF(0, 0, self._image_width, self._image_height))
        self.fit_to_window()
        return True

    def add_text_annotation(self, text: str, x: float, y: float) -> str:
        if self._image_width <= 0 or self._image_height <= 0:
            return ""
        self._push_undo()
        annotation_id = f"ann-{uuid4().hex[:12]}"
        annotation = {
            "id": annotation_id,
            "type": "text",
            "x": self._normalize_x(x),
            "y": self._normalize_y(y),
            "text": str(text),
            "font_size": 12,
            "color": "#111111",
        }
        self._annotations.append(annotation)
        self._draw_annotation(annotation)
        self.select_annotation(annotation_id)
        return annotation_id

    def add_rectangle_annotation(self, x: float, y: float, width: float, height: float) -> str:
        if self._image_width <= 0 or self._image_height <= 0:
            return ""
        self._push_undo()
        annotation_id = f"ann-{uuid4().hex[:12]}"
        annotation = {
            "id": annotation_id,
            "type": "rectangle",
            "x": self._normalize_x(x),
            "y": self._normalize_y(y),
            "width": self._normalize_x(width),
            "height": self._normalize_y(height),
            "color": "#D55E00",
            "line_width": 2.0,
        }
        self._annotations.append(annotation)
        self._draw_annotation(annotation)
        self.select_annotation(annotation_id)
        return annotation_id

    def add_line_annotation(self, x1: float, y1: float, x2: float, y2: float) -> str:
        return self._add_segment_annotation("line", x1, y1, x2, y2)

    def add_arrow_annotation(self, x1: float, y1: float, x2: float, y2: float) -> str:
        return self._add_segment_annotation("arrow", x1, y1, x2, y2)

    def add_highlight_annotation(self, x: float, y: float, width: float, height: float) -> str:
        if self._image_width <= 0 or self._image_height <= 0:
            return ""
        self._push_undo()
        annotation_id = f"ann-{uuid4().hex[:12]}"
        annotation = {
            "id": annotation_id,
            "type": "highlight",
            "x": self._normalize_x(x),
            "y": self._normalize_y(y),
            "width": self._normalize_x(width),
            "height": self._normalize_y(height),
            "color": "#F0E442",
            "alpha": 0.35,
        }
        self._annotations.append(annotation)
        self._draw_annotation(annotation)
        self.select_annotation(annotation_id)
        return annotation_id

    def set_tool(self, tool: str) -> bool:
        if tool not in {"select", "text", "line", "arrow", "rectangle", "highlight", "crop"}:
            return False
        if self._current_tool == tool:
            return True
        self._current_tool = tool
        self._draw_start = None
        self.tool_changed.emit(tool)
        return True

    def current_tool(self) -> str:
        return self._current_tool

    def image_size(self) -> tuple[int, int]:
        return self._image_width, self._image_height

    def remove_annotation(self, annotation_id: str) -> bool:
        next_annotations = [
            item for item in self._annotations if item.get("id") != annotation_id
        ]
        if len(next_annotations) == len(self._annotations):
            return False
        self._push_undo()
        self._annotations = next_annotations
        if self._selected_annotation_id == annotation_id:
            self._selected_annotation_id = ""
        self._rebuild_scene()
        return True

    def select_annotation(self, annotation_id: str) -> bool:
        if not any(item.get("id") == annotation_id for item in self._annotations):
            return False
        self._selected_annotation_id = annotation_id
        for item in self._scene.items():
            item.setSelected(item.data(0) == annotation_id)
        self.selection_changed.emit(annotation_id)
        return True

    def selected_annotation_id(self) -> str:
        return self._selected_annotation_id

    def selected_annotation(self) -> dict:
        if not self._selected_annotation_id:
            return {}
        self.sync_scene_items_to_state()
        annotation = self._annotation_by_id(self._selected_annotation_id)
        return deepcopy(annotation) if annotation is not None else {}

    def delete_selected_annotation(self) -> bool:
        if not self._selected_annotation_id:
            return False
        return self.remove_annotation(self._selected_annotation_id)

    def move_annotation(self, annotation_id: str, dx: float, dy: float) -> bool:
        annotation = self._annotation_by_id(annotation_id)
        if annotation is None:
            return False
        self._push_undo()
        kind = annotation.get("type")
        dx_norm = self._normalize_x(dx)
        dy_norm = self._normalize_y(dy)
        if kind in {"text", "rectangle", "highlight"}:
            annotation["x"] = round(float(annotation.get("x", 0.0)) + dx_norm, 6)
            annotation["y"] = round(float(annotation.get("y", 0.0)) + dy_norm, 6)
        elif kind in {"line", "arrow"}:
            annotation["x1"] = round(float(annotation.get("x1", 0.0)) + dx_norm, 6)
            annotation["y1"] = round(float(annotation.get("y1", 0.0)) + dy_norm, 6)
            annotation["x2"] = round(float(annotation.get("x2", 0.0)) + dx_norm, 6)
            annotation["y2"] = round(float(annotation.get("y2", 0.0)) + dy_norm, 6)
        else:
            return False
        self._rebuild_scene()
        self.select_annotation(annotation_id)
        return True

    def update_selected_text(self, text: str) -> bool:
        if not self._selected_annotation_id:
            return False
        annotation = self._annotation_by_id(self._selected_annotation_id)
        if annotation is None or annotation.get("type") != "text":
            return False
        self._push_undo()
        annotation["text"] = str(text)
        self._rebuild_scene()
        self.select_annotation(str(annotation.get("id", "")))
        return True

    def update_selected_properties(
        self,
        *,
        color: str | None = None,
        line_width: float | None = None,
        font_size: int | None = None,
        alpha: float | None = None,
    ) -> bool:
        if not self._selected_annotation_id:
            return False
        annotation = self._annotation_by_id(self._selected_annotation_id)
        if annotation is None:
            return False

        updates = self._validated_property_updates(annotation, color, line_width, font_size, alpha)
        if not updates:
            return False

        self._push_undo()
        annotation.update(updates)
        annotation_id = str(annotation.get("id", ""))
        self._rebuild_scene()
        self.select_annotation(annotation_id)
        return True

    def copy_selected_annotation(self) -> bool:
        annotation = self.selected_annotation()
        if not annotation:
            return False
        self._clipboard_annotation = annotation
        return True

    def paste_annotation(self) -> str:
        if not self._clipboard_annotation or self._image_width <= 0 or self._image_height <= 0:
            return ""
        self._push_undo()
        annotation = deepcopy(self._clipboard_annotation)
        annotation["id"] = f"ann-{uuid4().hex[:12]}"
        self._offset_annotation(annotation, 5.0, 5.0)
        self._annotations.append(annotation)
        self._draw_annotation(annotation)
        annotation_id = str(annotation.get("id", ""))
        self.select_annotation(annotation_id)
        return annotation_id

    def bring_selected_to_front(self) -> bool:
        return self._move_selected_layer(to_front=True)

    def send_selected_to_back(self) -> bool:
        return self._move_selected_layer(to_front=False)

    def crop_to_rect(self, x: float, y: float, width: float, height: float) -> bool:
        if self._pixmap_item is None or self._image_width <= 0 or self._image_height <= 0:
            return False
        left = max(0.0, min(float(x), float(self._image_width)))
        top = max(0.0, min(float(y), float(self._image_height)))
        right = max(left, min(left + float(width), float(self._image_width)))
        bottom = max(top, min(top + float(height), float(self._image_height)))
        crop_width = int(round(right - left))
        crop_height = int(round(bottom - top))
        if crop_width < 1 or crop_height < 1:
            return False

        self.sync_scene_items_to_state()
        source_pixmap = self._pixmap_item.pixmap()
        cropped = source_pixmap.copy(int(round(left)), int(round(top)), crop_width, crop_height)
        if cropped.isNull():
            return False

        self._push_undo()
        self._annotations = self._annotations_after_crop(left, top, float(crop_width), float(crop_height))
        self._image_width = crop_width
        self._image_height = crop_height
        self._selected_annotation_id = ""
        self._scene.clear()
        self._pixmap_item = self._scene.addPixmap(cropped)
        self._pixmap_item.setPos(0, 0)
        self._scene.setSceneRect(QRectF(0, 0, self._image_width, self._image_height))
        for annotation in self._annotations:
            self._draw_annotation(annotation)
        self.fit_to_window()
        return True

    def undo(self) -> bool:
        if not self._undo_stack:
            return False
        self._redo_stack.append(self._snapshot_state())
        self._restore_state(self._undo_stack.pop())
        self._selected_annotation_id = ""
        return True

    def redo(self) -> bool:
        if not self._redo_stack:
            return False
        self._undo_stack.append(self._snapshot_state())
        self._restore_state(self._redo_stack.pop())
        self._selected_annotation_id = ""
        return True

    def zoom_level(self) -> float:
        return round(self._zoom_level, 3)

    def zoom_mode(self) -> str:
        return self._zoom_mode

    def set_zoom_100(self) -> bool:
        if self._image_width <= 0 or self._image_height <= 0:
            return False
        self._zoom_level = 1.0
        self._zoom_mode = "manual"
        self._apply_zoom()
        return True

    def zoom_in(self) -> bool:
        return self._set_zoom_level(self._zoom_level * 1.25)

    def zoom_out(self) -> bool:
        return self._set_zoom_level(self._zoom_level / 1.25)

    def fit_to_window(self) -> bool:
        if self._image_width <= 0 or self._image_height <= 0:
            return False
        self._zoom_mode = "fit"
        self._view.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)
        transform = self._view.transform()
        if transform.m11() > 0:
            self._zoom_level = transform.m11()
        return True

    def annotation_state(self) -> list[dict]:
        self.sync_scene_items_to_state()
        return deepcopy(self._annotations)

    def sync_scene_items_to_state(self) -> bool:
        if self._image_width <= 0 or self._image_height <= 0:
            return False
        updates: dict[str, dict] = {}
        for item in self._scene.items():
            annotation_id = item.data(0)
            if not annotation_id:
                continue
            annotation = self._annotation_by_id(str(annotation_id))
            if annotation is None:
                continue
            kind = annotation.get("type")
            if kind == "text":
                updates[str(annotation_id)] = {
                    "x": self._normalize_x(item.pos().x()),
                    "y": self._normalize_y(item.pos().y()),
                }
            elif kind in {"rectangle", "highlight"} and hasattr(item, "rect"):
                rect = item.mapRectToScene(item.rect())
                updates[str(annotation_id)] = {
                    "x": self._normalize_x(rect.x()),
                    "y": self._normalize_y(rect.y()),
                    "width": self._normalize_x(rect.width()),
                    "height": self._normalize_y(rect.height()),
                }
            elif kind in {"line", "arrow"} and hasattr(item, "line"):
                line = item.line()
                p1 = item.mapToScene(line.p1())
                p2 = item.mapToScene(line.p2())
                updates[str(annotation_id)] = {
                    "x1": self._normalize_x(p1.x()),
                    "y1": self._normalize_y(p1.y()),
                    "x2": self._normalize_x(p2.x()),
                    "y2": self._normalize_y(p2.y()),
                }
            elif kind == "arrow":
                line_item = self._line_child_item(item)
                if line_item is not None:
                    line = line_item.line()
                    p1 = line_item.mapToScene(line.p1())
                    p2 = line_item.mapToScene(line.p2())
                    updates[str(annotation_id)] = {
                        "x1": self._normalize_x(p1.x()),
                        "y1": self._normalize_y(p1.y()),
                        "x2": self._normalize_x(p2.x()),
                        "y2": self._normalize_y(p2.y()),
                    }

        changed = False
        next_annotations = deepcopy(self._annotations)
        for annotation in next_annotations:
            annotation_id = str(annotation.get("id", ""))
            item_updates = updates.get(annotation_id)
            if not item_updates:
                continue
            for key, value in item_updates.items():
                if annotation.get(key) != value:
                    annotation[key] = value
                    changed = True

        if changed:
            self._push_undo()
            self._annotations = next_annotations
            selected_id = self._selected_annotation_id
            self._rebuild_scene()
            if selected_id:
                self.select_annotation(selected_id)
        return changed

    def load_annotation_state(self, annotations: list[dict]) -> None:
        self._annotations = [
            deepcopy(annotation)
            for annotation in annotations
            if isinstance(annotation, dict)
        ]
        self._undo_stack = []
        self._redo_stack = []
        self._selected_annotation_id = ""
        self._rebuild_scene()

    def render_to_image(self, bg_color: str = "#FFFFFF") -> QImage:
        rect = self._scene.sceneRect()
        if rect.isNull():
            return QImage()
        image = QImage(
            max(1, int(rect.width())),
            max(1, int(rect.height())),
            QImage.Format_ARGB32,
        )
        image.fill(QColor(bg_color))
        painter = QPainter()
        if painter.begin(image):
            try:
                self._scene.render(painter, QRectF(image.rect()), rect)
            finally:
                painter.end()
        return image

    def eventFilter(self, watched, event):
        if watched is self._view.viewport() and self._current_tool != "select":
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self._draw_start = self._scene_point_from_event(event)
                event.accept()
                return True
            if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                if self._draw_start is not None:
                    end = self._scene_point_from_event(event)
                    self._finish_mouse_draw(self._draw_start, end)
                    self._draw_start = None
                    self.set_tool("select")
                    event.accept()
                    return True
        return super().eventFilter(watched, event)

    def keyPressEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            if event.key() == Qt.Key_Z:
                self.sync_scene_items_to_state()
                if self.undo():
                    event.accept()
                    return
            if event.key() == Qt.Key_Y:
                if self.redo():
                    event.accept()
                    return
            if event.key() == Qt.Key_C:
                if self.copy_selected_annotation():
                    event.accept()
                    return
            if event.key() == Qt.Key_V:
                if self.paste_annotation():
                    event.accept()
                    return
            if event.key() in {Qt.Key_Plus, Qt.Key_Equal}:
                if self.zoom_in():
                    event.accept()
                    return
            if event.key() == Qt.Key_Minus:
                if self.zoom_out():
                    event.accept()
                    return
            if event.key() == Qt.Key_0:
                if self.set_zoom_100():
                    event.accept()
                    return
        if event.key() in {Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down}:
            if self._nudge_selected_annotation(event.key(), event.modifiers()):
                event.accept()
                return
        if event.key() in {Qt.Key_Delete, Qt.Key_Backspace}:
            if self.delete_selected_annotation():
                event.accept()
                return
        super().keyPressEvent(event)

    def _normalize_x(self, value: float) -> float:
        return round(float(value) / float(self._image_width), 6)

    def _normalize_y(self, value: float) -> float:
        return round(float(value) / float(self._image_height), 6)

    def _denormalize_x(self, value: float) -> float:
        return float(value) * float(self._image_width)

    def _denormalize_y(self, value: float) -> float:
        return float(value) * float(self._image_height)

    def _push_undo(self) -> None:
        self._undo_stack.append(self._snapshot_state())
        self._redo_stack = []

    def _snapshot_state(self) -> dict:
        pixmap = QPixmap()
        if self._pixmap_item is not None:
            pixmap = QPixmap(self._pixmap_item.pixmap())
        return {
            "annotations": deepcopy(self._annotations),
            "image_width": self._image_width,
            "image_height": self._image_height,
            "pixmap": pixmap,
        }

    def _restore_state(self, state: dict) -> None:
        self._annotations = deepcopy(state.get("annotations", []))
        self._image_width = int(state.get("image_width", 0) or 0)
        self._image_height = int(state.get("image_height", 0) or 0)
        pixmap = state.get("pixmap")
        self._scene.clear()
        self._pixmap_item = None
        if isinstance(pixmap, QPixmap) and not pixmap.isNull():
            self._pixmap_item = self._scene.addPixmap(QPixmap(pixmap))
            self._pixmap_item.setPos(0, 0)
        for annotation in self._annotations:
            self._draw_annotation(annotation)
        self._scene.setSceneRect(QRectF(0, 0, self._image_width, self._image_height))

    def _set_zoom_level(self, level: float) -> bool:
        if self._image_width <= 0 or self._image_height <= 0:
            return False
        self._zoom_level = min(8.0, max(0.1, float(level)))
        self._zoom_mode = "manual"
        self._apply_zoom()
        return True

    def _apply_zoom(self) -> None:
        self._view.resetTransform()
        self._view.scale(self._zoom_level, self._zoom_level)

    def _scene_point_from_event(self, event) -> QPointF:
        position = event.position().toPoint()
        point = self._view.mapToScene(position)
        x = min(max(point.x(), 0.0), float(self._image_width))
        y = min(max(point.y(), 0.0), float(self._image_height))
        return QPointF(x, y)

    def _finish_mouse_draw(self, start: QPointF, end: QPointF) -> str:
        if self._image_width <= 0 or self._image_height <= 0:
            return ""
        tool = self._current_tool
        if tool == "text":
            return self.add_text_annotation("Annotation", start.x(), start.y())
        if tool in {"rectangle", "highlight"}:
            x = min(start.x(), end.x())
            y = min(start.y(), end.y())
            width = abs(end.x() - start.x())
            height = abs(end.y() - start.y())
            if width < 1.0 or height < 1.0:
                return ""
            if tool == "rectangle":
                return self.add_rectangle_annotation(x, y, width, height)
            return self.add_highlight_annotation(x, y, width, height)
        if tool == "crop":
            x = min(start.x(), end.x())
            y = min(start.y(), end.y())
            width = abs(end.x() - start.x())
            height = abs(end.y() - start.y())
            if width < 1.0 or height < 1.0:
                return ""
            return "crop" if self.crop_to_rect(x, y, width, height) else ""
        if tool == "line":
            return self.add_line_annotation(start.x(), start.y(), end.x(), end.y())
        if tool == "arrow":
            return self.add_arrow_annotation(start.x(), start.y(), end.x(), end.y())
        return ""

    def _annotation_by_id(self, annotation_id: str) -> dict | None:
        for annotation in self._annotations:
            if annotation.get("id") == annotation_id:
                return annotation
        return None

    def _on_scene_selection_changed(self) -> None:
        for item in self._scene.selectedItems():
            annotation_id = item.data(0)
            if annotation_id and self._annotation_by_id(str(annotation_id)) is not None:
                annotation_id = str(annotation_id)
                if self._selected_annotation_id != annotation_id:
                    self._selected_annotation_id = annotation_id
                    self.selection_changed.emit(annotation_id)
                return
        if self._selected_annotation_id:
            self._selected_annotation_id = ""
            self.selection_changed.emit("")

    def _nudge_selected_annotation(self, key, modifiers) -> bool:
        if not self._selected_annotation_id:
            return False
        step = 10.0 if modifiers & Qt.ShiftModifier else 1.0
        dx = 0.0
        dy = 0.0
        if key == Qt.Key_Left:
            dx = -step
        elif key == Qt.Key_Right:
            dx = step
        elif key == Qt.Key_Up:
            dy = -step
        elif key == Qt.Key_Down:
            dy = step
        else:
            return False
        return self.move_annotation(self._selected_annotation_id, dx, dy)

    def _validated_property_updates(
        self,
        annotation: dict,
        color: str | None,
        line_width: float | None,
        font_size: int | None,
        alpha: float | None,
    ) -> dict:
        kind = annotation.get("type")
        updates = {}
        if color:
            updates["color"] = str(color)
        if line_width is not None and kind in {"line", "arrow", "rectangle"}:
            updates["line_width"] = max(0.1, round(float(line_width), 3))
        if font_size is not None and kind == "text":
            updates["font_size"] = max(1, int(font_size))
        if alpha is not None and kind == "highlight":
            updates["alpha"] = min(1.0, max(0.0, round(float(alpha), 3)))
        return {
            key: value
            for key, value in updates.items()
            if annotation.get(key) != value
        }

    def _offset_annotation(self, annotation: dict, dx: float, dy: float) -> None:
        kind = annotation.get("type")
        dx_norm = self._normalize_x(dx)
        dy_norm = self._normalize_y(dy)
        if kind in {"text", "rectangle", "highlight"}:
            annotation["x"] = round(float(annotation.get("x", 0.0)) + dx_norm, 6)
            annotation["y"] = round(float(annotation.get("y", 0.0)) + dy_norm, 6)
        elif kind in {"line", "arrow"}:
            annotation["x1"] = round(float(annotation.get("x1", 0.0)) + dx_norm, 6)
            annotation["y1"] = round(float(annotation.get("y1", 0.0)) + dy_norm, 6)
            annotation["x2"] = round(float(annotation.get("x2", 0.0)) + dx_norm, 6)
            annotation["y2"] = round(float(annotation.get("y2", 0.0)) + dy_norm, 6)

    def _move_selected_layer(self, to_front: bool) -> bool:
        if not self._selected_annotation_id:
            return False
        index = next(
            (
                idx
                for idx, annotation in enumerate(self._annotations)
                if annotation.get("id") == self._selected_annotation_id
            ),
            -1,
        )
        if index < 0:
            return False
        target_index = len(self._annotations) - 1 if to_front else 0
        if index == target_index:
            return False
        self._push_undo()
        annotation = self._annotations.pop(index)
        if to_front:
            self._annotations.append(annotation)
        else:
            self._annotations.insert(0, annotation)
        annotation_id = str(annotation.get("id", ""))
        self._rebuild_scene()
        self.select_annotation(annotation_id)
        return True

    def _annotations_after_crop(
        self,
        left: float,
        top: float,
        width: float,
        height: float,
    ) -> list[dict]:
        cropped = []
        for annotation in self._annotations:
            updated = self._crop_annotation(annotation, left, top, width, height)
            if updated is not None:
                cropped.append(updated)
        return cropped

    def _crop_annotation(
        self,
        annotation: dict,
        left: float,
        top: float,
        width: float,
        height: float,
    ) -> dict | None:
        kind = annotation.get("type")
        updated = deepcopy(annotation)
        if kind == "text":
            x = self._denormalize_x(float(annotation.get("x", 0.0)))
            y = self._denormalize_y(float(annotation.get("y", 0.0)))
            if not (left <= x <= left + width and top <= y <= top + height):
                return None
            updated["x"] = round((x - left) / width, 6)
            updated["y"] = round((y - top) / height, 6)
            return updated

        if kind in {"rectangle", "highlight"}:
            x = self._denormalize_x(float(annotation.get("x", 0.0)))
            y = self._denormalize_y(float(annotation.get("y", 0.0)))
            rect_width = self._denormalize_x(float(annotation.get("width", 0.0)))
            rect_height = self._denormalize_y(float(annotation.get("height", 0.0)))
            ix1 = max(x, left)
            iy1 = max(y, top)
            ix2 = min(x + rect_width, left + width)
            iy2 = min(y + rect_height, top + height)
            if ix2 <= ix1 or iy2 <= iy1:
                return None
            updated["x"] = round((ix1 - left) / width, 6)
            updated["y"] = round((iy1 - top) / height, 6)
            updated["width"] = round((ix2 - ix1) / width, 6)
            updated["height"] = round((iy2 - iy1) / height, 6)
            return updated

        if kind in {"line", "arrow"}:
            x1 = self._denormalize_x(float(annotation.get("x1", 0.0)))
            y1 = self._denormalize_y(float(annotation.get("y1", 0.0)))
            x2 = self._denormalize_x(float(annotation.get("x2", 0.0)))
            y2 = self._denormalize_y(float(annotation.get("y2", 0.0)))
            min_x = min(x1, x2)
            max_x = max(x1, x2)
            min_y = min(y1, y2)
            max_y = max(y1, y2)
            if max_x < left or min_x > left + width or max_y < top or min_y > top + height:
                return None
            updated["x1"] = round(min(1.0, max(0.0, (x1 - left) / width)), 6)
            updated["y1"] = round(min(1.0, max(0.0, (y1 - top) / height)), 6)
            updated["x2"] = round(min(1.0, max(0.0, (x2 - left) / width)), 6)
            updated["y2"] = round(min(1.0, max(0.0, (y2 - top) / height)), 6)
            return updated

        return updated

    def _rebuild_scene(self) -> None:
        pixmap = self._pixmap_item.pixmap() if self._pixmap_item is not None else QPixmap()
        self._scene.clear()
        self._pixmap_item = None
        if not pixmap.isNull():
            self._pixmap_item = self._scene.addPixmap(pixmap)
            self._pixmap_item.setPos(0, 0)
        for annotation in self._annotations:
            self._draw_annotation(annotation)
        self._scene.setSceneRect(QRectF(0, 0, self._image_width, self._image_height))

    def _draw_annotation(self, annotation: dict) -> None:
        kind = annotation.get("type")
        if kind == "text":
            item = QGraphicsTextItem(str(annotation.get("text", "")))
            item.setDefaultTextColor(QColor(str(annotation.get("color", "#111111"))))
            font = item.font()
            font.setPointSize(int(annotation.get("font_size", 12) or 12))
            item.setFont(font)
            item.setPos(
                self._denormalize_x(float(annotation.get("x", 0.0))),
                self._denormalize_y(float(annotation.get("y", 0.0))),
            )
            self._scene.addItem(item)
            self._configure_annotation_item(item, annotation.get("id", ""))
            return

        if kind == "rectangle":
            pen = QPen(QColor(str(annotation.get("color", "#D55E00"))))
            pen.setWidthF(float(annotation.get("line_width", 2.0) or 2.0))
            rect = QRectF(
                self._denormalize_x(float(annotation.get("x", 0.0))),
                self._denormalize_y(float(annotation.get("y", 0.0))),
                self._denormalize_x(float(annotation.get("width", 0.0))),
                self._denormalize_y(float(annotation.get("height", 0.0))),
            )
            item = self._scene.addRect(rect, pen, QBrush(Qt.NoBrush))
            self._configure_annotation_item(item, annotation.get("id", ""))
            return

        if kind == "highlight":
            color = QColor(str(annotation.get("color", "#F0E442")))
            color.setAlphaF(float(annotation.get("alpha", 0.35) or 0.35))
            rect = QRectF(
                self._denormalize_x(float(annotation.get("x", 0.0))),
                self._denormalize_y(float(annotation.get("y", 0.0))),
                self._denormalize_x(float(annotation.get("width", 0.0))),
                self._denormalize_y(float(annotation.get("height", 0.0))),
            )
            item = self._scene.addRect(rect, QPen(Qt.NoPen), QBrush(color))
            self._configure_annotation_item(item, annotation.get("id", ""))
            return

        if kind in {"line", "arrow"}:
            x1 = self._denormalize_x(float(annotation.get("x1", 0.0)))
            y1 = self._denormalize_y(float(annotation.get("y1", 0.0)))
            x2 = self._denormalize_x(float(annotation.get("x2", 0.0)))
            y2 = self._denormalize_y(float(annotation.get("y2", 0.0)))
            pen = QPen(QColor(str(annotation.get("color", "#D55E00"))))
            pen.setWidthF(float(annotation.get("line_width", 2.0) or 2.0))
            line_item = self._scene.addLine(x1, y1, x2, y2, pen)
            if kind == "arrow":
                head_item = self._draw_arrow_head(x1, y1, x2, y2, pen)
                group = self._scene.createItemGroup([line_item, head_item])
                self._configure_annotation_item(group, annotation.get("id", ""))
            else:
                self._configure_annotation_item(line_item, annotation.get("id", ""))

    def _configure_annotation_item(self, item, annotation_id: str) -> None:
        item.setData(0, annotation_id)
        item.setFlag(item.GraphicsItemFlag.ItemIsSelectable, True)
        item.setFlag(item.GraphicsItemFlag.ItemIsMovable, True)
        item.setFlag(item.GraphicsItemFlag.ItemSendsGeometryChanges, True)

    def _line_child_item(self, item):
        for child in item.childItems():
            if hasattr(child, "line"):
                return child
        return None

    def _add_segment_annotation(self, kind: str, x1: float, y1: float, x2: float, y2: float) -> str:
        if self._image_width <= 0 or self._image_height <= 0:
            return ""
        self._push_undo()
        annotation_id = f"ann-{uuid4().hex[:12]}"
        annotation = {
            "id": annotation_id,
            "type": kind,
            "x1": self._normalize_x(x1),
            "y1": self._normalize_y(y1),
            "x2": self._normalize_x(x2),
            "y2": self._normalize_y(y2),
            "color": "#D55E00",
            "line_width": 2.0,
        }
        self._annotations.append(annotation)
        self._draw_annotation(annotation)
        self.select_annotation(annotation_id)
        return annotation_id

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
