"""Minimal figure annotation canvas for static exported images."""

from __future__ import annotations

import math
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsTextItem, QGraphicsView, QVBoxLayout, QWidget

from .annotation_render_adapter import AnnotationRenderAdapter, qt_pen_style_for_line_style


class AnnotationCanvas(QWidget):
    tool_changed = Signal(str)
    selection_changed = Signal(str)
    annotations_changed = Signal()
    object_edit_requested = Signal(object)
    object_create_requested = Signal(object)
    text_entry_requested = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self._render_adapter = AnnotationRenderAdapter(self._scene)
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
        self._draw_preview_item = None
        self._selection_handle_items: list[object] = []
        self._selection_handle_drag: dict | None = None
        self._annotation_body_drag: dict | None = None
        self._syncing_scene_selection = False
        self._clipboard_annotation: dict | None = None
        self._document_objects_mode = False
        self._document_interaction_enabled = False
        self._document_interaction_object_ids: set[str] = set()
        self._pending_object_geometry: dict[str, dict] = {}
        self.setFocusPolicy(Qt.StrongFocus)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)
        self._view.installEventFilter(self)
        self._view.viewport().installEventFilter(self)

    def load_image(self, path: str) -> bool:
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            return False

        self._render_adapter.clear()
        self._discard_scene_overlays()
        self._scene.clear()
        self._annotations = []
        self._undo_stack = []
        self._redo_stack = []
        self._selected_annotation_id = ""
        self._document_objects_mode = False
        self._document_interaction_enabled = False
        self._document_interaction_object_ids = set()
        self._pending_object_geometry = {}
        self._image_path = str(Path(path))
        self._image_width = pixmap.width()
        self._image_height = pixmap.height()
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._pixmap_item.setPos(0, 0)
        self._scene.setSceneRect(QRectF(0, 0, self._image_width, self._image_height))
        self.fit_to_window()
        return True

    def replace_image(self, image: QImage | QPixmap) -> bool:
        if isinstance(image, QImage):
            pixmap = QPixmap.fromImage(image)
        elif isinstance(image, QPixmap):
            pixmap = QPixmap(image)
        else:
            return False
        if pixmap.isNull():
            return False

        selected_id = self._selected_annotation_id
        self._image_width = pixmap.width()
        self._image_height = pixmap.height()
        self._render_adapter.clear()
        self._discard_scene_overlays()
        self._scene.clear()
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._pixmap_item.setPos(0, 0)
        self._scene.setSceneRect(QRectF(0, 0, self._image_width, self._image_height))
        if self._document_objects_mode:
            self._render_adapter.replace_objects(self._annotations)
        else:
            for annotation in self._annotations:
                self._draw_annotation(annotation)
        if selected_id and any(item.get("id") == selected_id for item in self._annotations):
            self.select_annotation(selected_id)
        elif selected_id:
            self._selected_annotation_id = ""
            self.selection_changed.emit("")
        return True

    def add_text_annotation(
        self,
        text: str,
        x: float,
        y: float,
        *,
        width: float | None = None,
        height: float | None = None,
    ) -> str:
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
        text_width = float(width) if width is not None and float(width) > 0 else max(24.0, len(str(text)) * 8.0)
        text_height = float(height) if height is not None and float(height) > 0 else 20.0
        annotation["width"] = self._normalize_x(
            min(text_width, max(1.0, float(self._image_width) - float(x)))
        )
        annotation["height"] = self._normalize_y(
            min(text_height, max(1.0, float(self._image_height) - float(y)))
        )
        self._annotations.append(annotation)
        self._draw_annotation(annotation)
        self.select_annotation(annotation_id)
        self.annotations_changed.emit()
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
        self.annotations_changed.emit()
        return annotation_id

    def add_line_annotation(self, x1: float, y1: float, x2: float, y2: float) -> str:
        return self._add_segment_annotation("line", x1, y1, x2, y2)

    def add_arrow_annotation(self, x1: float, y1: float, x2: float, y2: float) -> str:
        return self._add_segment_annotation("arrow", x1, y1, x2, y2)

    def add_curve_annotation(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        control_x: float,
        control_y: float,
    ) -> str:
        if self._image_width <= 0 or self._image_height <= 0:
            return ""
        self._push_undo()
        annotation_id = f"ann-{uuid4().hex[:12]}"
        annotation = {
            "id": annotation_id,
            "type": "curve",
            "x1": self._normalize_x(x1),
            "y1": self._normalize_y(y1),
            "x2": self._normalize_x(x2),
            "y2": self._normalize_y(y2),
            "control_x": self._normalize_x(control_x),
            "control_y": self._normalize_y(control_y),
            "color": "#D55E00",
            "line_width": 2.0,
        }
        self._annotations.append(annotation)
        self._draw_annotation(annotation)
        self.select_annotation(annotation_id)
        self.annotations_changed.emit()
        return annotation_id

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
        self.annotations_changed.emit()
        return annotation_id

    def set_tool(self, tool: str) -> bool:
        if tool not in {"select", "text", "line", "arrow", "curve", "rectangle", "highlight", "crop"}:
            return False
        if self._current_tool == tool:
            return True
        self._current_tool = tool
        self._draw_start = None
        self._clear_draw_preview()
        self.tool_changed.emit(tool)
        return True

    def current_tool(self) -> str:
        return self._current_tool

    def set_document_interaction_enabled(self, enabled: bool) -> None:
        """Route interactive gestures through document signals without projection."""

        self._document_interaction_enabled = bool(enabled)
        self._document_interaction_object_ids = (
            {
                str(annotation.get("id", "") or "")
                for annotation in self._annotations
                if annotation.get("id")
            }
            if self._document_interaction_enabled
            else set()
        )

    def _document_route_enabled(self, object_id: str = "") -> bool:
        return self._document_objects_mode or (
            self._document_interaction_enabled
            and str(object_id or "") in self._document_interaction_object_ids
        )

    def image_size(self) -> tuple[int, int]:
        return self._image_width, self._image_height

    def remove_annotation(self, annotation_id: str) -> bool:
        next_annotations = [
            item for item in self._annotations if item.get("id") != annotation_id
        ]
        if len(next_annotations) == len(self._annotations):
            return False
        if self._document_route_enabled(annotation_id):
            self.object_edit_requested.emit(
                {
                    "object_id": str(annotation_id),
                    "source": "annotation_canvas",
                    "operation": "delete",
                }
            )
            return True
        self._push_undo()
        self._annotations = next_annotations
        if self._selected_annotation_id == annotation_id:
            self._selected_annotation_id = ""
        self._rebuild_scene()
        self.annotations_changed.emit()
        return True

    def select_annotation(self, annotation_id: str) -> bool:
        if not any(item.get("id") == annotation_id for item in self._annotations):
            return False
        self._syncing_scene_selection = True
        try:
            for item in self._scene.items():
                item.setSelected(item.data(0) == annotation_id)
        finally:
            self._syncing_scene_selection = False
        self._selected_annotation_id = annotation_id
        self._refresh_selection_handles()
        self.selection_changed.emit(annotation_id)
        return True

    def selected_annotation_id(self) -> str:
        return self._selected_annotation_id

    def clear_selection(self) -> bool:
        had_selection = bool(self._selected_annotation_id)
        self._selected_annotation_id = ""
        for item in self._scene.items():
            item.setSelected(False)
        self._clear_selection_handles()
        self.selection_changed.emit("")
        return had_selection

    def selected_annotation(self) -> dict:
        if not self._selected_annotation_id:
            return {}
        if self._document_objects_mode:
            annotation = next(
                (
                    item
                    for item in self._render_adapter.scene_state()
                    if item.get("id") == self._selected_annotation_id
                ),
                None,
            )
        else:
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
        kind = annotation.get("type")
        dx_norm = self._normalize_x(dx)
        dy_norm = self._normalize_y(dy)
        geometry = self._geometry_from_payload(annotation)
        if kind in {"text", "rectangle", "highlight"}:
            geometry["x"] = round(float(annotation.get("x", 0.0)) + dx_norm, 6)
            geometry["y"] = round(float(annotation.get("y", 0.0)) + dy_norm, 6)
        elif kind in {"line", "arrow", "curve"}:
            geometry["x1"] = round(float(annotation.get("x1", 0.0)) + dx_norm, 6)
            geometry["y1"] = round(float(annotation.get("y1", 0.0)) + dy_norm, 6)
            geometry["x2"] = round(float(annotation.get("x2", 0.0)) + dx_norm, 6)
            geometry["y2"] = round(float(annotation.get("y2", 0.0)) + dy_norm, 6)
            if kind == "curve":
                geometry["control_x"] = round(
                    float(annotation.get("control_x", 0.0)) + dx_norm,
                    6,
                )
                geometry["control_y"] = round(
                    float(annotation.get("control_y", 0.0)) + dy_norm,
                    6,
                )
        else:
            return False
        if self._document_route_enabled(annotation_id):
            self.object_edit_requested.emit(
                {
                    "object_id": str(annotation_id),
                    "source": "annotation_canvas",
                    "geometry": geometry,
                    "object_type": kind,
                }
            )
            return True
        self._push_undo()
        annotation.update(geometry)
        self._rebuild_scene()
        self.select_annotation(annotation_id)
        self.annotations_changed.emit()
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
        self.annotations_changed.emit()
        return True

    def update_selected_properties(
        self,
        *,
        color: str | None = None,
        line_width: float | None = None,
        line_style: str | None = None,
        font_size: int | None = None,
        alpha: float | None = None,
    ) -> bool:
        if not self._selected_annotation_id:
            return False
        annotation = self._annotation_by_id(self._selected_annotation_id)
        if annotation is None:
            return False

        updates = self._validated_property_updates(
            annotation, color, line_width, line_style, font_size, alpha
        )
        if not updates:
            return False

        self._push_undo()
        annotation.update(updates)
        annotation_id = str(annotation.get("id", ""))
        self._rebuild_scene()
        self.select_annotation(annotation_id)
        self.annotations_changed.emit()
        return True

    def update_selected_geometry(
        self,
        *,
        x: float | None = None,
        y: float | None = None,
        width: float | None = None,
        height: float | None = None,
        x1: float | None = None,
        y1: float | None = None,
        x2: float | None = None,
        y2: float | None = None,
        control_x: float | None = None,
        control_y: float | None = None,
    ) -> bool:
        if not self._selected_annotation_id:
            return False
        annotation = self._annotation_by_id(self._selected_annotation_id)
        if annotation is None:
            return False

        updates = {}
        if x is not None and "x" in annotation:
            updates["x"] = round(min(1.0, max(0.0, float(x))), 6)
        if y is not None and "y" in annotation:
            updates["y"] = round(min(1.0, max(0.0, float(y))), 6)
        if width is not None and "width" in annotation:
            updates["width"] = round(min(1.0, max(0.0, float(width))), 6)
        if width is not None and annotation.get("type") == "text" and "width" not in annotation:
            updates["width"] = round(min(1.0, max(0.0, float(width))), 6)
        if height is not None and "height" in annotation:
            updates["height"] = round(min(1.0, max(0.0, float(height))), 6)
        if height is not None and annotation.get("type") == "text" and "height" not in annotation:
            updates["height"] = round(min(1.0, max(0.0, float(height))), 6)
        if x1 is not None and "x1" in annotation:
            updates["x1"] = round(min(1.0, max(0.0, float(x1))), 6)
        if y1 is not None and "y1" in annotation:
            updates["y1"] = round(min(1.0, max(0.0, float(y1))), 6)
        if x2 is not None and "x2" in annotation:
            updates["x2"] = round(min(1.0, max(0.0, float(x2))), 6)
        if y2 is not None and "y2" in annotation:
            updates["y2"] = round(min(1.0, max(0.0, float(y2))), 6)
        if control_x is not None and "control_x" in annotation:
            updates["control_x"] = round(min(1.0, max(0.0, float(control_x))), 6)
        if control_y is not None and "control_y" in annotation:
            updates["control_y"] = round(min(1.0, max(0.0, float(control_y))), 6)
        if not updates:
            return False
        if all(annotation.get(key) == value for key, value in updates.items()):
            return False

        self._push_undo()
        annotation.update(updates)
        annotation_id = str(annotation.get("id", ""))
        self._rebuild_scene()
        self.select_annotation(annotation_id)
        self.annotations_changed.emit()
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
        self.annotations_changed.emit()
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
        self._discard_scene_overlays()
        self._scene.clear()
        self._pixmap_item = self._scene.addPixmap(cropped)
        self._pixmap_item.setPos(0, 0)
        self._scene.setSceneRect(QRectF(0, 0, self._image_width, self._image_height))
        for annotation in self._annotations:
            self._draw_annotation(annotation)
        self.fit_to_window()
        self.annotations_changed.emit()
        return True

    def undo(self) -> bool:
        if not self._undo_stack:
            return False
        self._redo_stack.append(self._snapshot_state())
        self._restore_state(self._undo_stack.pop())
        self.annotations_changed.emit()
        return True

    def redo(self) -> bool:
        if not self._redo_stack:
            return False
        self._undo_stack.append(self._snapshot_state())
        self._restore_state(self._redo_stack.pop())
        self.annotations_changed.emit()
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
        if self._document_objects_mode:
            return self._render_adapter.scene_state()
        self.sync_scene_items_to_state()
        return deepcopy(self._annotations)

    def set_document_objects(self, objects: list[dict]) -> dict[str, object]:
        """Project shared-session objects without adding a canvas undo entry."""

        previous_selection = self._selected_annotation_id
        self._document_objects_mode = True
        self._pending_object_geometry = {}
        self._annotations = [
            deepcopy(object_payload)
            for object_payload in objects
            if isinstance(object_payload, dict)
        ]
        self._undo_stack = []
        self._redo_stack = []
        self._selected_annotation_id = ""
        self._rebuild_scene()
        projected = {
            str(item.data(0)): item
            for item in self._scene.items()
            if item.data(0)
        }
        selected_id = next(
            (
                str(object_payload.get("id", ""))
                for object_payload in self._annotations
                if object_payload.get("selected") or object_payload.get("is_selected")
            ),
            "",
        )
        if not selected_id and previous_selection in projected:
            selected_id = previous_selection
        if selected_id:
            self.select_annotation(selected_id)
        return projected

    def flush_pending_object_edit(self) -> bool:
        """Emit proposed geometry changes from projected scene items."""

        if not self._document_objects_mode:
            return False
        emitted = False
        projected_ids = {
            str(object_payload.get("id", ""))
            for object_payload in self._render_adapter.scene_state()
        }
        projected_items = {
            str(item.data(0)): item
            for item in self._scene.items()
            if item.data(0) and str(item.data(0)) in projected_ids
        }
        for object_id, item in projected_items.items():
            annotation = self._annotation_by_id(object_id)
            if annotation is None:
                continue
            geometry = self._geometry_from_scene_item(item, annotation)
            if not geometry:
                continue
            baseline = self._geometry_from_payload(annotation)
            if geometry == baseline or geometry == self._pending_object_geometry.get(object_id):
                continue
            self._pending_object_geometry[object_id] = geometry
            self.object_edit_requested.emit(
                {
                    "object_id": object_id,
                    "source": "annotation_canvas",
                    "geometry": geometry,
                    "object_type": annotation.get("type", ""),
                }
            )
            emitted = True
        return emitted

    def sync_scene_items_to_state(self, emit_changed=True) -> bool:
        if self._image_width <= 0 or self._image_height <= 0:
            return False
        if self._document_objects_mode:
            return self.flush_pending_object_edit()
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
            elif kind == "curve":
                updates[str(annotation_id)] = self._curve_geometry_from_item(item, annotation)

        changed = False
        document_requests: list[dict] = []
        next_annotations = deepcopy(self._annotations)
        for annotation in next_annotations:
            annotation_id = str(annotation.get("id", ""))
            item_updates = updates.get(annotation_id)
            if not item_updates:
                continue
            if self._document_route_enabled(annotation_id):
                baseline = self._geometry_from_payload(annotation)
                if item_updates != baseline and item_updates != self._pending_object_geometry.get(annotation_id):
                    self._pending_object_geometry[annotation_id] = item_updates
                    document_requests.append(
                        {
                            "object_id": annotation_id,
                            "source": "annotation_canvas",
                            "geometry": item_updates,
                            "object_type": annotation.get("type", ""),
                        }
                    )
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
            if emit_changed:
                self.annotations_changed.emit()
        for payload in document_requests:
            self.object_edit_requested.emit(payload)
        return changed or bool(document_requests)

    def load_annotation_state(self, annotations: list[dict]) -> None:
        self._render_adapter.clear()
        self._document_objects_mode = False
        self._document_interaction_enabled = False
        self._document_interaction_object_ids = set()
        self._pending_object_geometry = {}
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
                self.render_scene(painter, QRectF(image.rect()), rect)
            finally:
                painter.end()
        return image

    def render_scene(self, painter: QPainter, target: QRectF, source: QRectF | None = None) -> None:
        source = source if source is not None else self._scene.sceneRect()
        transient_items = [self._draw_preview_item, *self._selection_handle_items]
        visibility = []
        for item in transient_items:
            if item is None or item.scene() is not self._scene:
                continue
            visibility.append((item, item.isVisible()))
            item.setVisible(False)
        selected_items = list(self._scene.selectedItems())
        self._syncing_scene_selection = True
        try:
            for item in selected_items:
                item.setSelected(False)
            self._scene.render(painter, target, source)
        finally:
            for item in selected_items:
                if item.scene() is self._scene:
                    item.setSelected(True)
            self._syncing_scene_selection = False
            for item, was_visible in visibility:
                if item.scene() is self._scene:
                    item.setVisible(was_visible)

    def eventFilter(self, watched, event):
        if watched is self._view and event.type() == QEvent.KeyPress:
            self.keyPressEvent(event)
            return event.isAccepted()
        if watched is self._view.viewport() and self._current_tool == "select":
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                scene_point = self._scene_point_from_event(event)
                if self._begin_selection_handle_drag(scene_point):
                    event.accept()
                    return True
                if self._begin_annotation_body_drag(scene_point):
                    event.accept()
                    return True
            if event.type() == QEvent.MouseMove and self._selection_handle_drag is not None:
                self._update_selection_handle_drag(self._scene_point_from_event(event))
                event.accept()
                return True
            if event.type() == QEvent.MouseMove and self._annotation_body_drag is not None:
                self._update_annotation_body_drag(self._scene_point_from_event(event))
                event.accept()
                return True
            if event.type() == QEvent.MouseMove:
                annotation = self._annotation_by_id(self._selected_annotation_id)
                handle_index = None
                if annotation is not None:
                    handle_index = self._selection_handle_index_at(
                        annotation,
                        self._geometry_from_payload(annotation),
                        self._scene_point_from_event(event),
                    )
                if handle_index is None:
                    self._view.viewport().unsetCursor()
                else:
                    self._view.viewport().setCursor(
                        self._selection_handle_cursor_shape(annotation, handle_index)
                    )
                if handle_index is not None:
                    event.accept()
                    return True
                return False
            if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                if self._selection_handle_drag is not None:
                    self._finish_selection_handle_drag(self._scene_point_from_event(event))
                    event.accept()
                    return True
                if self._annotation_body_drag is not None:
                    self._finish_annotation_body_drag(self._scene_point_from_event(event))
                    event.accept()
                    return True
                self.sync_scene_items_to_state()
                return False
        if watched is self._view.viewport() and self._current_tool != "select":
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self._draw_start = self._scene_point_from_event(event)
                event.accept()
                return True
            if event.type() == QEvent.MouseMove and self._draw_start is not None:
                self._update_draw_preview(
                    self._draw_start,
                    self._scene_point_from_event(event),
                )
                event.accept()
                return True
            if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                if self._draw_start is not None:
                    end = self._scene_point_from_event(event)
                    self._clear_draw_preview()
                    self._finish_mouse_draw(self._draw_start, end)
                    self._draw_start = None
                    self.set_tool("select")
                    event.accept()
                    return True
        return super().eventFilter(watched, event)

    def keyPressEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            if event.key() == Qt.Key_Z:
                self.sync_scene_items_to_state(emit_changed=False)
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
        if event.key() == Qt.Key_Escape:
            if self._selection_handle_drag is not None:
                if self._cancel_selection_handle_drag():
                    event.accept()
                    return
            if self._annotation_body_drag is not None:
                if self._cancel_annotation_body_drag():
                    event.accept()
                    return
            if self._draw_start is not None:
                self._draw_start = None
                self._clear_draw_preview()
                self.set_tool("select")
                event.accept()
                return
            if self.clear_selection():
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

    def _geometry_from_scene_item(self, item, annotation: dict) -> dict:
        kind = annotation.get("type")
        if kind == "text":
            return {
                "x": self._normalize_x(item.pos().x()),
                "y": self._normalize_y(item.pos().y()),
            }
        if kind in {"rectangle", "highlight"} and hasattr(item, "rect"):
            rect = item.mapRectToScene(item.rect())
            return {
                "x": self._normalize_x(rect.x()),
                "y": self._normalize_y(rect.y()),
                "width": self._normalize_x(rect.width()),
                "height": self._normalize_y(rect.height()),
            }
        line_item = item if hasattr(item, "line") else self._line_child_item(item)
        if kind in {"line", "arrow"} and line_item is not None:
            line = line_item.line()
            p1 = line_item.mapToScene(line.p1())
            p2 = line_item.mapToScene(line.p2())
            return {
                "x1": self._normalize_x(p1.x()),
                "y1": self._normalize_y(p1.y()),
                "x2": self._normalize_x(p2.x()),
                "y2": self._normalize_y(p2.y()),
            }
        if kind == "curve":
            return self._curve_geometry_from_item(item, annotation)
        return {}

    def _curve_geometry_from_item(self, item, annotation: dict) -> dict:
        baseline = self._geometry_from_payload(annotation)
        required = ("x1", "y1", "x2", "y2", "control_x", "control_y")
        if any(key not in baseline for key in required):
            return {}
        dx = self._normalize_x(item.pos().x())
        dy = self._normalize_y(item.pos().y())
        return {
            "x1": round(baseline["x1"] + dx, 6),
            "y1": round(baseline["y1"] + dy, 6),
            "x2": round(baseline["x2"] + dx, 6),
            "y2": round(baseline["y2"] + dy, 6),
            "control_x": round(baseline["control_x"] + dx, 6),
            "control_y": round(baseline["control_y"] + dy, 6),
        }

    @staticmethod
    def _geometry_from_payload(annotation: dict) -> dict:
        kind = annotation.get("type")
        container = AnnotationCanvas._geometry_container(annotation)
        if kind in {"text", "rectangle", "highlight"}:
            keys = ("x", "y")
            if kind in {"rectangle", "highlight"}:
                keys += ("width", "height")
        elif kind in {"line", "arrow", "curve"}:
            keys = ("x1", "y1", "x2", "y2")
            if kind == "curve":
                keys += ("control_x", "control_y")
        else:
            return {}
        result = {}
        for key in keys:
            if key not in container:
                continue
            try:
                result[key] = round(float(container[key]), 6)
            except (TypeError, ValueError, OverflowError):
                continue
        return result

    @staticmethod
    def _geometry_container(payload: dict) -> dict:
        for key in ("geometry", "bounds"):
            value = payload.get(key)
            if isinstance(value, dict):
                return value
        return payload

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
            "selected_annotation_id": self._selected_annotation_id,
        }

    def _restore_state(self, state: dict) -> None:
        previous_selected_id = self._selected_annotation_id
        self._annotations = deepcopy(state.get("annotations", []))
        self._image_width = int(state.get("image_width", 0) or 0)
        self._image_height = int(state.get("image_height", 0) or 0)
        selected_id = str(state.get("selected_annotation_id", "") or "")
        pixmap = state.get("pixmap")
        self._discard_scene_overlays()
        self._scene.clear()
        self._pixmap_item = None
        if isinstance(pixmap, QPixmap) and not pixmap.isNull():
            self._pixmap_item = self._scene.addPixmap(QPixmap(pixmap))
            self._pixmap_item.setPos(0, 0)
        for annotation in self._annotations:
            self._draw_annotation(annotation)
        self._scene.setSceneRect(QRectF(0, 0, self._image_width, self._image_height))
        if selected_id and self.select_annotation(selected_id):
            return
        self._selected_annotation_id = ""
        if previous_selected_id:
            self.selection_changed.emit("")

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
            x = min(start.x(), end.x())
            y = min(start.y(), end.y())
            geometry = {
                "x": self._normalize_x(x),
                "y": self._normalize_y(y),
            }
            width = abs(end.x() - start.x())
            height = abs(end.y() - start.y())
            if width >= 3.0 and height >= 3.0:
                geometry["width"] = self._normalize_x(width)
                geometry["height"] = self._normalize_y(height)
            if self._document_objects_mode or self._document_interaction_enabled:
                self.text_entry_requested.emit({"type": "text", "geometry": geometry})
                return ""
            return self.add_text_annotation(
                "Annotation",
                start.x(),
                start.y(),
                width=width if "width" in geometry else None,
                height=height if "height" in geometry else None,
            )
        if tool in {"rectangle", "highlight"}:
            x = min(start.x(), end.x())
            y = min(start.y(), end.y())
            width = abs(end.x() - start.x())
            height = abs(end.y() - start.y())
            if width < 1.0 or height < 1.0:
                return ""
            if self._document_objects_mode or self._document_interaction_enabled:
                self.object_create_requested.emit(
                    {
                        "type": tool,
                        "geometry": {
                            "x": self._normalize_x(x),
                            "y": self._normalize_y(y),
                            "width": self._normalize_x(width),
                            "height": self._normalize_y(height),
                        },
                    }
                )
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
            if self._document_objects_mode or self._document_interaction_enabled:
                self.object_create_requested.emit(
                    {
                        "type": "line",
                        "geometry": {
                            "x1": self._normalize_x(start.x()),
                            "y1": self._normalize_y(start.y()),
                            "x2": self._normalize_x(end.x()),
                            "y2": self._normalize_y(end.y()),
                        },
                    }
                )
                return ""
            return self.add_line_annotation(start.x(), start.y(), end.x(), end.y())
        if tool == "arrow":
            if self._document_objects_mode or self._document_interaction_enabled:
                self.object_create_requested.emit(
                    {
                        "type": "arrow",
                        "geometry": {
                            "x1": self._normalize_x(start.x()),
                            "y1": self._normalize_y(start.y()),
                            "x2": self._normalize_x(end.x()),
                            "y2": self._normalize_y(end.y()),
                        },
                    }
                )
                return ""
            return self.add_arrow_annotation(start.x(), start.y(), end.x(), end.y())
        if tool == "curve":
            control_x, control_y = self._default_curve_control_point(start, end)
            if self._document_objects_mode or self._document_interaction_enabled:
                self.object_create_requested.emit(
                    {
                        "type": "curve",
                        "geometry": {
                            "x1": self._normalize_x(start.x()),
                            "y1": self._normalize_y(start.y()),
                            "x2": self._normalize_x(end.x()),
                            "y2": self._normalize_y(end.y()),
                            "control_x": self._normalize_x(control_x),
                            "control_y": self._normalize_y(control_y),
                        },
                    }
                )
                return ""
            return self.add_curve_annotation(
                start.x(), start.y(), end.x(), end.y(), control_x, control_y
            )
        return ""

    def _annotation_by_id(self, annotation_id: str) -> dict | None:
        for annotation in self._annotations:
            if annotation.get("id") == annotation_id:
                return annotation
        return None

    def _on_scene_selection_changed(self) -> None:
        if self._syncing_scene_selection:
            return
        for item in self._scene.selectedItems():
            annotation_id = item.data(0)
            if annotation_id and self._annotation_by_id(str(annotation_id)) is not None:
                annotation_id = str(annotation_id)
                if self._selected_annotation_id != annotation_id:
                    self._selected_annotation_id = annotation_id
                    self.selection_changed.emit(annotation_id)
                self._refresh_selection_handles()
                return
        if self._selected_annotation_id:
            self._selected_annotation_id = ""
            self.selection_changed.emit("")
        self._clear_selection_handles()

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
        line_style: str | None,
        font_size: int | None,
        alpha: float | None,
    ) -> dict:
        kind = annotation.get("type")
        updates = {}
        if color:
            updates["color"] = str(color)
        if line_width is not None and kind in {"line", "arrow", "curve", "rectangle"}:
            updates["line_width"] = max(0.1, round(float(line_width), 3))
        if line_style is not None and kind in {"line", "arrow", "curve", "rectangle"}:
            normalized_style = str(line_style)
            if normalized_style in {"-", "--", ":", "-."}:
                updates["line_style"] = normalized_style
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
        elif kind in {"line", "arrow", "curve"}:
            annotation["x1"] = round(float(annotation.get("x1", 0.0)) + dx_norm, 6)
            annotation["y1"] = round(float(annotation.get("y1", 0.0)) + dy_norm, 6)
            annotation["x2"] = round(float(annotation.get("x2", 0.0)) + dx_norm, 6)
            annotation["y2"] = round(float(annotation.get("y2", 0.0)) + dy_norm, 6)
            if kind == "curve":
                annotation["control_x"] = round(
                    float(annotation.get("control_x", 0.0)) + dx_norm,
                    6,
                )
                annotation["control_y"] = round(
                    float(annotation.get("control_y", 0.0)) + dy_norm,
                    6,
                )

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
        self.annotations_changed.emit()
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

        if kind in {"line", "arrow", "curve"}:
            points = [
                (
                    self._denormalize_x(float(annotation.get("x1", 0.0))),
                    self._denormalize_y(float(annotation.get("y1", 0.0))),
                ),
                (
                    self._denormalize_x(float(annotation.get("x2", 0.0))),
                    self._denormalize_y(float(annotation.get("y2", 0.0))),
                ),
            ]
            if kind == "curve":
                points.append(
                    (
                        self._denormalize_x(float(annotation.get("control_x", 0.0))),
                        self._denormalize_y(float(annotation.get("control_y", 0.0))),
                    )
                )
            min_x = min(point[0] for point in points)
            max_x = max(point[0] for point in points)
            min_y = min(point[1] for point in points)
            max_y = max(point[1] for point in points)
            if max_x < left or min_x > left + width or max_y < top or min_y > top + height:
                return None
            updated["x1"] = round(min(1.0, max(0.0, (points[0][0] - left) / width)), 6)
            updated["y1"] = round(min(1.0, max(0.0, (points[0][1] - top) / height)), 6)
            updated["x2"] = round(min(1.0, max(0.0, (points[1][0] - left) / width)), 6)
            updated["y2"] = round(min(1.0, max(0.0, (points[1][1] - top) / height)), 6)
            if kind == "curve":
                updated["control_x"] = round(
                    min(1.0, max(0.0, (points[2][0] - left) / width)),
                    6,
                )
                updated["control_y"] = round(
                    min(1.0, max(0.0, (points[2][1] - top) / height)),
                    6,
                )
            return updated

        return updated

    def _rebuild_scene(self) -> None:
        pixmap = self._pixmap_item.pixmap() if self._pixmap_item is not None else QPixmap()
        self._render_adapter.clear()
        self._discard_scene_overlays()
        self._scene.clear()
        self._draw_preview_item = None
        self._selection_handle_items = []
        self._selection_handle_drag = None
        self._pixmap_item = None
        if not pixmap.isNull():
            self._pixmap_item = self._scene.addPixmap(pixmap)
            self._pixmap_item.setPos(0, 0)
        if self._document_objects_mode:
            self._render_adapter.replace_objects(self._annotations)
        else:
            for annotation in self._annotations:
                self._draw_annotation(annotation)
        self._scene.setSceneRect(QRectF(0, 0, self._image_width, self._image_height))

    def _clear_draw_preview(self) -> None:
        item = self._draw_preview_item
        self._draw_preview_item = None
        if item is not None:
            self._scene.removeItem(item)

    def _discard_scene_overlays(self) -> None:
        self._draw_preview_item = None
        self._selection_handle_items = []
        self._selection_handle_drag = None
        self._annotation_body_drag = None

    def _update_draw_preview(self, start: QPointF, end: QPointF) -> None:
        self._clear_draw_preview()
        pen = QPen(QColor("#3B82F6"))
        pen.setWidthF(1.5)
        pen.setStyle(Qt.DashLine)
        tool = self._current_tool
        if tool in {"line", "arrow"}:
            item = self._scene.addLine(start.x(), start.y(), end.x(), end.y(), pen)
        elif tool in {"rectangle", "highlight", "crop", "text"}:
            rect = QRectF(start, end).normalized()
            item = self._scene.addRect(rect, pen, QBrush(Qt.NoBrush))
        elif tool == "curve":
            control_x, control_y = self._default_curve_control_point(start, end)
            path = QPainterPath(start)
            path.quadTo(QPointF(control_x, control_y), end)
            item = self._scene.addPath(path, pen)
        else:
            return
        item.setZValue(10_000)
        self._draw_preview_item = item

    def _clear_selection_handles(self) -> None:
        for item in self._selection_handle_items:
            self._scene.removeItem(item)
        self._selection_handle_items = []

    def _refresh_selection_handles(self, geometry: dict | None = None) -> None:
        self._clear_selection_handles()
        annotation = self._annotation_by_id(self._selected_annotation_id)
        if annotation is None:
            return
        geometry = dict(geometry) if geometry is not None else self._geometry_from_payload(annotation)
        for index, point in enumerate(self._selection_handle_points(annotation, geometry)):
            item = self._scene.addEllipse(
                QRectF(point.x() - 4.0, point.y() - 4.0, 8.0, 8.0),
                QPen(QColor("#1D4ED8")),
                QBrush(QColor("#DBEAFE")),
            )
            item.setData(0, "")
            item.setData(1, index)
            item.setAcceptedMouseButtons(Qt.NoButton)
            item.setZValue(10_001)
            self._selection_handle_items.append(item)

    def _selection_handle_points(self, annotation: dict, geometry: dict) -> list[QPointF]:
        kind = str(annotation.get("type", "") or "")
        if kind in {"line", "arrow"}:
            return [
                self._scene_point_from_normalized(geometry["x1"], geometry["y1"]),
                self._scene_point_from_normalized(geometry["x2"], geometry["y2"]),
            ]
        if kind == "curve":
            points = [
                self._scene_point_from_normalized(geometry["x1"], geometry["y1"]),
                self._scene_point_from_normalized(geometry["x2"], geometry["y2"]),
            ]
            if "control_x" in geometry and "control_y" in geometry:
                points.append(
                    self._scene_point_from_normalized(
                        geometry["control_x"], geometry["control_y"]
                    )
                )
            return points
        if kind in {"rectangle", "text"}:
            geometry = self._text_geometry_for_selection(annotation, geometry)
            left = geometry["x"]
            top = geometry["y"]
            right = left + geometry["width"]
            bottom = top + geometry["height"]
            return [
                self._scene_point_from_normalized(left, top),
                self._scene_point_from_normalized(right, top),
                self._scene_point_from_normalized(right, bottom),
                self._scene_point_from_normalized(left, bottom),
            ]
        return []

    def _begin_selection_handle_drag(self, scene_point: QPointF) -> bool:
        annotation = self._annotation_by_id(self._selected_annotation_id)
        if annotation is None:
            return False
        geometry = self._text_geometry_for_selection(
            annotation,
            self._geometry_from_payload(annotation),
        )
        handle_index = self._selection_handle_index_at(annotation, geometry, scene_point)
        if handle_index is None:
            return False
        self._view.viewport().setCursor(
            self._selection_handle_cursor_shape(annotation, handle_index)
        )
        self._selection_handle_drag = {
            "object_id": str(annotation.get("id", "") or ""),
            "object_type": str(annotation.get("type", "") or ""),
            "handle_index": handle_index,
            "original_geometry": geometry,
            "preview_geometry": dict(geometry),
        }
        return True

    def _update_selection_handle_drag(self, scene_point: QPointF) -> bool:
        state = self._selection_handle_drag
        if not isinstance(state, dict):
            return False
        geometry = self._geometry_with_handle_at(
            state["object_type"],
            dict(state["original_geometry"]),
            int(state["handle_index"]),
            scene_point,
        )
        state["preview_geometry"] = geometry
        annotation = self._annotation_by_id(str(state["object_id"]))
        if annotation is None:
            return False
        self._render_selection_handle_preview(annotation, geometry)
        return True

    def _finish_selection_handle_drag(self, scene_point: QPointF) -> bool:
        if not self._update_selection_handle_drag(scene_point):
            return False
        state = self._selection_handle_drag
        self._selection_handle_drag = None
        annotation = self._annotation_by_id(str(state["object_id"]))
        geometry = dict(state["preview_geometry"])
        if annotation is None:
            return False
        if self._document_route_enabled(str(annotation.get("id", "") or "")):
            self.object_edit_requested.emit(
                {
                    "object_id": str(annotation.get("id", "") or ""),
                    "source": "annotation_canvas",
                    "geometry": geometry,
                    "object_type": annotation.get("type", ""),
                }
            )
            return True
        return self.update_selected_geometry(**geometry)

    def _cancel_selection_handle_drag(self) -> bool:
        state = self._selection_handle_drag
        self._selection_handle_drag = None
        if not isinstance(state, dict):
            return False
        annotation = self._annotation_by_id(str(state["object_id"]))
        if annotation is not None:
            if self._document_objects_mode:
                self._render_selection_handle_preview(annotation, dict(state["original_geometry"]))
            else:
                self._clear_draw_preview()
                self._refresh_selection_handles(dict(state["original_geometry"]))
        self._view.viewport().unsetCursor()
        return True

    def _begin_annotation_body_drag(self, scene_point: QPointF) -> bool:
        item = next(
            (
                candidate
                for candidate in self._scene.items(scene_point)
                if candidate.data(0) and self._annotation_by_id(str(candidate.data(0))) is not None
            ),
            None,
        )
        if item is None:
            return False
        annotation_id = str(item.data(0) or "")
        if annotation_id != self._selected_annotation_id:
            self.select_annotation(annotation_id)
        annotation = self._annotation_by_id(annotation_id)
        if annotation is None:
            return False
        geometry = self._text_geometry_for_selection(
            annotation,
            self._geometry_from_payload(annotation),
        )
        if not geometry:
            return False
        self._annotation_body_drag = {
            "object_id": annotation_id,
            "object_type": str(annotation.get("type", "") or ""),
            "press_point": QPointF(scene_point),
            "original_geometry": geometry,
            "preview_geometry": dict(geometry),
        }
        self._view.viewport().setCursor(Qt.ClosedHandCursor)
        return True

    def _update_annotation_body_drag(self, scene_point: QPointF) -> bool:
        state = self._annotation_body_drag
        if not isinstance(state, dict):
            return False
        press_point = state["press_point"]
        original = dict(state["original_geometry"])
        dx = self._normalize_x(scene_point.x() - press_point.x())
        dy = self._normalize_y(scene_point.y() - press_point.y())
        kind = str(state["object_type"] or "")
        if kind in {"text", "rectangle", "highlight"}:
            original["x"] = round(float(original.get("x", 0.0)) + dx, 6)
            original["y"] = round(float(original.get("y", 0.0)) + dy, 6)
        elif kind in {"line", "arrow", "curve"}:
            for x_key, y_key in (("x1", "y1"), ("x2", "y2")):
                original[x_key] = round(float(original.get(x_key, 0.0)) + dx, 6)
                original[y_key] = round(float(original.get(y_key, 0.0)) + dy, 6)
            if kind == "curve":
                original["control_x"] = round(float(original.get("control_x", 0.0)) + dx, 6)
                original["control_y"] = round(float(original.get("control_y", 0.0)) + dy, 6)
        else:
            return False
        state["preview_geometry"] = original
        annotation = self._annotation_by_id(str(state["object_id"]))
        if annotation is None:
            return False
        self._render_selection_handle_preview(annotation, original)
        return True

    def _finish_annotation_body_drag(self, scene_point: QPointF) -> bool:
        if not self._update_annotation_body_drag(scene_point):
            return False
        state = self._annotation_body_drag
        self._annotation_body_drag = None
        annotation = self._annotation_by_id(str(state["object_id"]))
        if annotation is None:
            return False
        geometry = dict(state["preview_geometry"])
        if geometry == state["original_geometry"]:
            self._clear_draw_preview()
            self._refresh_selection_handles(geometry)
            self._view.viewport().unsetCursor()
            return False
        if self._document_route_enabled(str(annotation.get("id", "") or "")):
            self.object_edit_requested.emit(
                {
                    "object_id": str(annotation.get("id", "") or ""),
                    "source": "annotation_canvas",
                    "geometry": geometry,
                    "object_type": annotation.get("type", ""),
                }
            )
            self._view.viewport().unsetCursor()
            return True
        self._push_undo()
        annotation.update(geometry)
        annotation_id = str(annotation.get("id", "") or "")
        self._rebuild_scene()
        self.select_annotation(annotation_id)
        self.annotations_changed.emit()
        self._view.viewport().unsetCursor()
        return True

    def _cancel_annotation_body_drag(self) -> bool:
        state = self._annotation_body_drag
        self._annotation_body_drag = None
        if not isinstance(state, dict):
            return False
        annotation = self._annotation_by_id(str(state["object_id"]))
        if annotation is not None:
            self._render_selection_handle_preview(annotation, dict(state["original_geometry"]))
        self._view.viewport().unsetCursor()
        return True

    def _selection_handle_index_at(
        self, annotation: dict, geometry: dict, scene_point: QPointF
    ) -> int | None:
        points = self._selection_handle_points(annotation, geometry)
        if not points:
            return None
        handle_index = min(
            range(len(points)),
            key=lambda index: (points[index] - scene_point).manhattanLength(),
        )
        if (points[handle_index] - scene_point).manhattanLength() > 10.0:
            return None
        return handle_index

    @staticmethod
    def _selection_handle_cursor_shape(annotation: dict, handle_index: int):
        if str(annotation.get("type", "") or "") in {"rectangle", "text"}:
            return (
                Qt.SizeFDiagCursor
                if int(handle_index) in {0, 2}
                else Qt.SizeBDiagCursor
            )
        return Qt.SizeAllCursor

    def _render_selection_handle_preview(self, annotation: dict, geometry: dict) -> None:
        payload = deepcopy(annotation)
        container = self._geometry_container(payload)
        container.update(geometry)
        if self._document_objects_mode:
            self._syncing_scene_selection = True
            try:
                item = self._render_adapter.sync_object(payload)
                if item is not None:
                    item.setSelected(True)
            finally:
                self._syncing_scene_selection = False
            self._selected_annotation_id = str(annotation.get("id", ""))
            self._refresh_selection_handles(geometry)
            return
        self._clear_draw_preview()
        preview_payload = deepcopy(annotation)
        preview_payload.update(geometry)
        item = self._draw_annotation(preview_payload)
        if item is not None:
            item.setData(0, "")
            item.setFlag(item.GraphicsItemFlag.ItemIsSelectable, False)
            item.setFlag(item.GraphicsItemFlag.ItemIsMovable, False)
            item.setZValue(10_000)
            self._draw_preview_item = item
        self._refresh_selection_handles(geometry)

    def _geometry_with_handle_at(
        self, kind: str, geometry: dict, handle_index: int, point: QPointF
    ) -> dict:
        x = self._normalize_x(point.x())
        y = self._normalize_y(point.y())
        if kind in {"line", "arrow"}:
            geometry[("x1", "x2")[handle_index]] = x
            geometry[("y1", "y2")[handle_index]] = y
            return geometry
        if kind == "curve":
            key_pairs = {
                0: ("x1", "y1"),
                1: ("x2", "y2"),
                2: ("control_x", "control_y"),
            }
            x_key, y_key = key_pairs[handle_index]
            geometry[x_key] = x
            geometry[y_key] = y
            return geometry
        if kind in {"rectangle", "text"}:
            left = geometry["x"]
            top = geometry["y"]
            right = left + geometry["width"]
            bottom = top + geometry["height"]
            opposite = ((right, bottom), (left, bottom), (left, top), (right, top))[handle_index]
            geometry["x"] = min(x, opposite[0])
            geometry["y"] = min(y, opposite[1])
            geometry["width"] = abs(x - opposite[0])
            geometry["height"] = abs(y - opposite[1])
        return geometry

    def _scene_point_from_normalized(self, x: float, y: float) -> QPointF:
        return QPointF(self._denormalize_x(x), self._denormalize_y(y))

    def _text_geometry_for_selection(self, annotation: dict, geometry: dict) -> dict:
        if str(annotation.get("type", "") or "") != "text":
            return geometry
        result = dict(geometry)
        for key in ("width", "height"):
            if key in annotation:
                result.setdefault(key, float(annotation[key]))
        item = next(
            (
                candidate
                for candidate in self._scene.items()
                if str(candidate.data(0) or "") == str(annotation.get("id", "") or "")
                and isinstance(candidate, QGraphicsTextItem)
            ),
            None,
        )
        if item is not None:
            result.setdefault("width", self._normalize_x(item.textWidth() or item.boundingRect().width()))
            result.setdefault("height", self._normalize_y(item.boundingRect().height()))
        result.setdefault("width", 0.01)
        result.setdefault("height", 0.02)
        return result

    def _default_curve_control_point(self, start: QPointF, end: QPointF) -> tuple[float, float]:
        dx = float(end.x()) - float(start.x())
        dy = float(end.y()) - float(start.y())
        length = math.hypot(dx, dy)
        midpoint_x = (float(start.x()) + float(end.x())) / 2.0
        midpoint_y = (float(start.y()) + float(end.y())) / 2.0
        if length <= 1e-6:
            return midpoint_x, midpoint_y
        bend = min(max(float(self._image_width), float(self._image_height)) * 0.35, length * 0.35)
        bend = max(12.0, bend)
        normal_x = -dy / length
        normal_y = dx / length
        if normal_y > 0.0:
            normal_x *= -1.0
            normal_y *= -1.0
        control_x = min(max(midpoint_x + normal_x * bend, 0.0), float(self._image_width))
        control_y = min(max(midpoint_y + normal_y * bend, 0.0), float(self._image_height))
        return control_x, control_y

    def _draw_annotation(self, annotation: dict):
        kind = annotation.get("type")
        if kind == "text":
            item = QGraphicsTextItem(str(annotation.get("text", "")))
            item.setDefaultTextColor(QColor(str(annotation.get("color", "#111111"))))
            font = item.font()
            font.setPointSize(int(annotation.get("font_size", 12) or 12))
            item.setFont(font)
            width = self._denormalize_x(float(annotation.get("width", 0.0) or 0.0))
            if width > 0:
                item.setTextWidth(width)
            item.setPos(
                self._denormalize_x(float(annotation.get("x", 0.0))),
                self._denormalize_y(float(annotation.get("y", 0.0))),
            )
            self._scene.addItem(item)
            self._configure_annotation_item(item, annotation.get("id", ""))
            return item

        if kind == "rectangle":
            pen = QPen(QColor(str(annotation.get("color", "#D55E00"))))
            pen.setWidthF(float(annotation.get("line_width", 2.0) or 2.0))
            pen.setStyle(qt_pen_style_for_line_style(annotation.get("line_style", "-")))
            rect = QRectF(
                self._denormalize_x(float(annotation.get("x", 0.0))),
                self._denormalize_y(float(annotation.get("y", 0.0))),
                self._denormalize_x(float(annotation.get("width", 0.0))),
                self._denormalize_y(float(annotation.get("height", 0.0))),
            )
            item = self._scene.addRect(rect, pen, QBrush(Qt.NoBrush))
            self._configure_annotation_item(item, annotation.get("id", ""))
            return item

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
            return item

        if kind in {"line", "arrow"}:
            x1 = self._denormalize_x(float(annotation.get("x1", 0.0)))
            y1 = self._denormalize_y(float(annotation.get("y1", 0.0)))
            x2 = self._denormalize_x(float(annotation.get("x2", 0.0)))
            y2 = self._denormalize_y(float(annotation.get("y2", 0.0)))
            pen = QPen(QColor(str(annotation.get("color", "#D55E00"))))
            pen.setWidthF(float(annotation.get("line_width", 2.0) or 2.0))
            pen.setStyle(qt_pen_style_for_line_style(annotation.get("line_style", "-")))
            line_item = self._scene.addLine(x1, y1, x2, y2, pen)
            if kind == "arrow":
                head_item = self._draw_arrow_head(x1, y1, x2, y2, pen)
                group = self._scene.createItemGroup([line_item, head_item])
                self._configure_annotation_item(group, annotation.get("id", ""))
            else:
                self._configure_annotation_item(line_item, annotation.get("id", ""))
                group = line_item
            return group

        if kind == "curve":
            path = QPainterPath(
                QPointF(
                    self._denormalize_x(float(annotation.get("x1", 0.0))),
                    self._denormalize_y(float(annotation.get("y1", 0.0))),
                )
            )
            path.quadTo(
                QPointF(
                    self._denormalize_x(float(annotation.get("control_x", 0.0))),
                    self._denormalize_y(float(annotation.get("control_y", 0.0))),
                ),
                QPointF(
                    self._denormalize_x(float(annotation.get("x2", 0.0))),
                    self._denormalize_y(float(annotation.get("y2", 0.0))),
                ),
            )
            pen = QPen(QColor(str(annotation.get("color", "#D55E00"))))
            pen.setWidthF(float(annotation.get("line_width", 2.0) or 2.0))
            pen.setStyle(qt_pen_style_for_line_style(annotation.get("line_style", "-")))
            item = self._scene.addPath(path, pen)
            self._configure_annotation_item(item, annotation.get("id", ""))
            return item
        return None

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
        self.annotations_changed.emit()
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
