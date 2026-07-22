import pytest

from polynexus.core.figure_text_geometry import text_box_anchor


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
