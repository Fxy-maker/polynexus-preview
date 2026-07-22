import pytest

from polynexus.core.figure_text_geometry import (
    axes_box_from_display,
    clamp_axes_box,
    is_axes_text_box,
    text_box_anchor,
)


def test_text_box_anchor_uses_box_left_top_by_default() -> None:
    assert text_box_anchor(0.2, 0.3, 0.4, 0.2) == (0.2, 0.5)


def test_text_box_anchor_keeps_unboxed_legacy_position() -> None:
    assert text_box_anchor(0.2, 0.3) == (0.2, 0.3)


def test_text_box_anchor_respects_explicit_alignment() -> None:
    assert text_box_anchor(
        0.2,
        0.3,
        0.4,
        0.2,
        horizontal_alignment="right",
        vertical_alignment="center",
    ) == pytest.approx((0.6, 0.4))


def test_axes_text_box_clamps_position_and_extent_to_axes_bounds() -> None:
    assert clamp_axes_box(-0.2, 0.8, 0.6, 0.5) == pytest.approx(
        {"x": 0.0, "y": 0.5, "width": 0.6, "height": 0.5}
    )


def test_axes_box_from_display_uses_axes_transform() -> None:
    class _Transform:
        def inverted(self):
            return self

        def transform(self, point):
            return (point[0] / 100.0, point[1] / 200.0)

    assert axes_box_from_display((10.0, 40.0, 30.0, 80.0), _Transform()) == pytest.approx(
        {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.4}
    )


def test_axes_text_box_marker_is_explicit_and_legacy_payloads_stay_legacy() -> None:
    assert is_axes_text_box({"type": "text", "coordinate_space": "axes"}) is True
    assert is_axes_text_box({"type": "text", "x": 0.2, "y": 0.3}) is False
