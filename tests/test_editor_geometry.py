from __future__ import annotations

from polynexus.gui.widgets.editor_geometry import Box, Curve, Segment


def test_box_normalizes_reversed_drag_and_preserves_size():
    box = Box.from_drag((8, 24), (2, 10))

    assert box == Box(2.0, 10.0, 6.0, 14.0)


def test_segment_translation_moves_both_endpoints():
    assert Segment(1, 2, 5, 7).translated(3, -1) == Segment(4, 1, 8, 6)


def test_curve_translation_moves_control_point_too():
    curve = Curve(1, 2, 4, 8, 7, 3)

    assert curve.translated(2, -2) == Curve(3, 0, 6, 6, 9, 1)


def test_payload_helpers_accept_legacy_top_level_and_nested_geometry():
    assert Box.from_payload(
        {"bounds": {"x": 1, "y": 2, "width": 3, "height": 4}}
    ).width == 3
    assert Segment.from_payload({"x1": 1, "y1": 2, "x2": 3, "y2": 4}).x2 == 3
