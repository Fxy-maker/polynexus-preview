"""Small, explicit SAXS static detector-mask editor."""

from __future__ import annotations

from typing import Any

import numpy as np
from PySide6.QtCore import QPoint, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ...core.saxs_engine.saxs_mask_edit import (
    MaskEditValidationError,
    build_mask_edit_candidate,
    confirm_mask_edit_candidate,
)


class _MaskCanvas(QWidget):
    changed = Signal(int)

    def __init__(self, image: np.ndarray, base_mask: np.ndarray, parent=None):
        super().__init__(parent)
        self._image = np.asarray(image, dtype=float).copy()
        self._base_mask = np.asarray(base_mask, dtype=bool).copy()
        self._edited_mask = self._base_mask.copy()
        self._image_rect = QRectF()
        self.setMinimumSize(480, 420)
        self.setMouseTracking(True)

    @property
    def edited_mask(self) -> np.ndarray:
        return self._edited_mask.copy()

    def set_cell_state(self, row: int, column: int, state: bool) -> None:
        if not (0 <= row < self._edited_mask.shape[0]):
            return
        if not (0 <= column < self._edited_mask.shape[1]):
            return
        if bool(self._edited_mask[row, column]) == bool(state):
            return
        self._edited_mask[row, column] = bool(state)
        self.changed.emit(self.changed_pixel_count())
        self.update()

    def reset(self) -> None:
        if np.array_equal(self._edited_mask, self._base_mask):
            return
        self._edited_mask = self._base_mask.copy()
        self.changed.emit(0)
        self.update()

    def changed_pixel_count(self) -> int:
        return int(np.count_nonzero(self._edited_mask != self._base_mask))

    def sizeHint(self) -> QSize:
        return QSize(720, 560)

    def _display_rect(self) -> QRectF:
        height, width = self._image.shape
        scale = min((self.width() - 16) / max(width, 1), (self.height() - 16) / max(height, 1))
        display_width = max(1.0, width * scale)
        display_height = max(1.0, height * scale)
        return QRectF(
            (self.width() - display_width) / 2.0,
            (self.height() - display_height) / 2.0,
            display_width,
            display_height,
        )

    def _cell_at(self, point: QPoint) -> tuple[int, int] | None:
        if not self._image_rect.contains(point):
            return None
        height, width = self._image.shape
        column = int((point.x() - self._image_rect.left()) / self._image_rect.width() * width)
        row = int((point.y() - self._image_rect.top()) / self._image_rect.height() * height)
        if 0 <= row < height and 0 <= column < width:
            return row, column
        return None

    def _set_from_mouse(self, event: QMouseEvent) -> None:
        cell = self._cell_at(event.position().toPoint())
        if cell is None:
            return
        state = not bool(event.buttons() & Qt.MouseButton.RightButton)
        self.set_cell_state(*cell, state)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._set_from_mouse(event)
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & (Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton):
            self._set_from_mouse(event)
        event.accept()

    @staticmethod
    def _image_from_values(values: np.ndarray) -> QImage:
        finite = np.isfinite(values)
        if not np.any(finite):
            normalized = np.zeros(values.shape, dtype=np.uint8)
        else:
            low, high = np.percentile(values[finite], [2.0, 98.0])
            if not np.isfinite(low) or not np.isfinite(high) or high <= low:
                low = float(np.min(values[finite]))
                high = float(np.max(values[finite]))
            if high <= low:
                normalized = np.zeros(values.shape, dtype=np.uint8)
            else:
                clipped = np.clip(np.nan_to_num(values, nan=low), low, high)
                normalized = np.asarray((clipped - low) / (high - low) * 255.0, dtype=np.uint8)
        gray = QImage(
            np.ascontiguousarray(normalized).data,
            normalized.shape[1],
            normalized.shape[0],
            normalized.strides[0],
            QImage.Format.Format_Grayscale8,
        )
        return gray.copy()

    def paintEvent(self, _event: Any) -> None:
        self._image_rect = self._display_rect()
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#11161d"))
        painter.drawImage(self._image_rect, self._image_from_values(self._image))

        overlay = np.zeros((*self._edited_mask.shape, 4), dtype=np.uint8)
        overlay[..., 0] = 235
        overlay[..., 1] = 70
        overlay[..., 2] = 55
        overlay[..., 3] = self._edited_mask.astype(np.uint8) * 125
        overlay_image = QImage(
            np.ascontiguousarray(overlay).data,
            overlay.shape[1],
            overlay.shape[0],
            overlay.strides[0],
            QImage.Format.Format_RGBA8888,
        )
        painter.drawImage(self._image_rect, overlay_image)
        painter.end()


class SAXSDetectorMaskEditor(QDialog):
    """Review and explicitly confirm a static detector-mask candidate."""

    candidate_confirmed = Signal(object)

    def __init__(self, image: np.ndarray, base_mask: np.ndarray, *, source_path: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("SAXS detector mask review")
        self.setModal(True)
        self.canvas = _MaskCanvas(image, base_mask, self)
        self._source_path = str(source_path or "")
        self._count_label = QLabel("Changed pixels: 0")
        self._count_label.setWordWrap(True)

        hint = QLabel(
            "Left-click to mask pixels, right-click to unmask them. "
            "The raw image is unchanged until you confirm a rerun."
        )
        hint.setWordWrap(True)

        self._reset_button = QPushButton("Reset")
        self._reset_button.clicked.connect(self.canvas.reset)
        self._cancel_button = QPushButton("Cancel")
        self._cancel_button.clicked.connect(self.reject)
        self._confirm_button = QPushButton("Confirm mask and rerun")
        self._confirm_button.setEnabled(False)
        self._confirm_button.clicked.connect(self._confirm_candidate)
        self.canvas.changed.connect(self._on_changed)

        actions = QHBoxLayout()
        actions.addWidget(self._count_label)
        actions.addStretch(1)
        actions.addWidget(self._reset_button)
        actions.addWidget(self._cancel_button)
        actions.addWidget(self._confirm_button)

        layout = QVBoxLayout(self)
        layout.addWidget(hint)
        layout.addWidget(self.canvas, 1)
        layout.addLayout(actions)
        self.resize(820, 680)

    def _on_changed(self, count: int) -> None:
        self._count_label.setText(f"Changed pixels: {int(count)}")
        self._confirm_button.setEnabled(int(count) > 0)

    def _confirm_candidate(self) -> None:
        if self.canvas.changed_pixel_count() <= 0:
            return
        try:
            candidate = build_mask_edit_candidate(
                self.canvas._base_mask,
                self.canvas.edited_mask,
                source_path=self._source_path,
            )
            confirmed = confirm_mask_edit_candidate(candidate, self.canvas._base_mask)
        except (MaskEditValidationError, TypeError, ValueError, OverflowError):
            return
        self.candidate_confirmed.emit(confirmed)
        self.accept()


__all__ = ["SAXSDetectorMaskEditor"]
