from __future__ import annotations

import math

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPointF
from PySide6.QtGui import QTransform
from PySide6.QtWidgets import QApplication

from polynexus.core.saxs_engine.config import TENSILE_AXIS_CONVENTION
from polynexus.gui.widgets.saxs_tensile_axis_editor import (
    SAXSTensileAxisEditor,
    screen_vector_to_detector_axis,
)


def _qapp() -> QApplication:
    app = QApplication.instance()
    return app if app is not None else QApplication([])


def _detector_axis_points(angle_deg: float) -> tuple[QPointF, QPointF]:
    start = QPointF(128.0, 96.0)
    length = 32.0
    radians = math.radians(angle_deg)
    return start, QPointF(
        start.x() + length * math.cos(radians),
        start.y() + length * math.sin(radians),
    )


@pytest.mark.parametrize(
    "transform",
    (
        QTransform(),
        QTransform(2.0, 0.0, 0.0, 0.5, 10.0, -5.0),
    ),
)
def test_screen_drag_round_trips_to_detector_axis(transform: QTransform) -> None:
    detector_start, detector_end = _detector_axis_points(35.0)
    screen_start = transform.map(detector_start)
    screen_end = transform.map(detector_end)
    screen_to_detector, invertible = transform.inverted()

    assert invertible
    assert screen_vector_to_detector_axis(
        screen_start,
        screen_end,
        screen_to_detector,
    ) == pytest.approx(35.0)


def test_editor_clear_is_none_explicit_zero_is_zero_and_drag_stays_disabled_without_parity() -> None:
    _qapp()
    editor = SAXSTensileAxisEditor()

    editor.set_axis(0.0, TENSILE_AXIS_CONVENTION)
    assert editor.config_values()["tensile_axis_deg"] == 0.0
    assert editor.config_values()["tensile_axis_convention"] == TENSILE_AXIS_CONVENTION

    editor.clear_axis()
    assert editor.config_values()["tensile_axis_deg"] is None
    assert editor.config_values()["tensile_axis_convention"] is None
    assert editor.drag_enabled is False
    assert editor.validation_state == "preview_transform_unverified"
