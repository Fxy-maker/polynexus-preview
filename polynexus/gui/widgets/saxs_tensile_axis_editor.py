"""Focused nullable detector-coordinate tensile-axis editor."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from PySide6.QtCore import QPointF, Signal
from PySide6.QtGui import QDoubleValidator, QTransform
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.saxs_engine.config import (
    TENSILE_AXIS_CONVENTION,
    normalize_tensile_axis,
)


def screen_vector_to_detector_axis(
    screen_start: QPointF,
    screen_end: QPointF,
    screen_to_detector: QTransform,
) -> float:
    """Convert a screen vector into detector-image clockwise axis degrees."""

    start = screen_to_detector.map(screen_start)
    end = screen_to_detector.map(screen_end)
    d_col = float(end.x() - start.x())
    d_row = float(end.y() - start.y())
    if (
        not all(math.isfinite(value) for value in (d_col, d_row))
        or math.hypot(d_col, d_row) < 2.0
    ):
        raise ValueError("tensile_axis_drag_too_short")
    return float(math.degrees(math.atan2(d_row, d_col)) % 180.0)


class SAXSTensileAxisEditor(QWidget):
    """Capture an explicit axis; drag stays disabled until parity is proven."""

    axisChanged = Signal(object, object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._axis_deg: float | None = None
        self._convention: str | None = None
        self._drag_enabled = False
        self._validation_state = "preview_transform_unverified"

        self._angle_input = QLineEdit(self)
        self._angle_input.setPlaceholderText("None")
        self._angle_input.setValidator(QDoubleValidator(-360000.0, 360000.0, 6, self))
        self._angle_input.editingFinished.connect(self._apply_text_value)
        self._clear_button = QPushButton("Clear", self)
        self._clear_button.clicked.connect(self.clear_axis)
        self._status_label = QLabel(self._validation_state, self)
        self._convention_label = QLabel(TENSILE_AXIS_CONVENTION, self)

        row = QHBoxLayout()
        row.addWidget(self._angle_input)
        row.addWidget(self._clear_button)
        layout = QVBoxLayout(self)
        layout.addLayout(row)
        layout.addWidget(self._convention_label)
        layout.addWidget(self._status_label)

    @property
    def drag_enabled(self) -> bool:
        return self._drag_enabled

    @property
    def validation_state(self) -> str:
        return self._validation_state

    def config_keys(self) -> tuple[str, str]:
        return "tensile_axis_deg", "tensile_axis_convention"

    def config_values(self) -> dict[str, Any]:
        return {
            "tensile_axis_deg": self._axis_deg,
            "tensile_axis_convention": self._convention,
        }

    def set_axis(self, value: Any, convention: Any) -> None:
        axis, normalized_convention = normalize_tensile_axis(value, convention)
        self._axis_deg = axis
        self._convention = normalized_convention
        self._angle_input.setText("" if axis is None else f"{axis:.6f}".rstrip("0").rstrip("."))
        self.axisChanged.emit(axis, normalized_convention)

    def clear_axis(self) -> None:
        self.set_axis(None, None)

    def set_config_values(self, values: Mapping[str, Any] | None) -> None:
        if not isinstance(values, Mapping):
            return
        self.set_axis(
            values.get("tensile_axis_deg"),
            values.get("tensile_axis_convention"),
        )

    def _apply_text_value(self) -> None:
        text = self._angle_input.text().strip()
        if not text:
            self.clear_axis()
            return
        self.set_axis(text, TENSILE_AXIS_CONVENTION)


__all__ = ["SAXSTensileAxisEditor", "screen_vector_to_detector_axis"]
