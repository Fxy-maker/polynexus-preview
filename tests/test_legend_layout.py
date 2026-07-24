from __future__ import annotations

from matplotlib import pyplot as plt
from matplotlib.transforms import Bbox


def test_empty_legacy_style_resolves_to_automatic_layout() -> None:
    from polynexus.core.figures.legend_layout import resolve_legend_layout

    content = Bbox.from_extents(10.0, 20.0, 90.0, 80.0)
    layout = resolve_legend_layout({}, content_bbox_display=content)

    assert layout.mode == "auto"
    assert layout.anchor_axes is None
    assert layout.size_axes is None
    assert layout.interaction_bbox_display == content
    assert layout.diagnostic is None


def test_upper_left_two_value_anchor_with_box_size_preserves_visible_lower_left() -> None:
    from polynexus.core.figures.legend_layout import resolve_legend_layout

    figure, axes = plt.subplots(figsize=(4.0, 3.0), dpi=100)
    try:
        layout = resolve_legend_layout(
            {
                "loc": "upper left",
                "bbox_to_anchor": [0.25, 0.85],
                "box_size": [0.4, 0.16],
            },
            axes=axes,
        )
    finally:
        plt.close(figure)

    assert layout.mode == "fixed"
    assert layout.anchor_axes == (0.25, 0.69)
    assert layout.size_axes == (0.4, 0.16)
    assert layout.diagnostic is None


def test_four_value_anchor_is_normalized_without_losing_unknown_style_keys() -> None:
    from polynexus.core.figures.legend_layout import (
        legend_style_updates,
        resolve_legend_layout,
    )

    style = {
        "loc": "lower left",
        "bbox_to_anchor": [0.1, 0.2, 0.35, 0.25],
        "future_key": "keep-me",
    }
    layout = resolve_legend_layout(style)

    assert layout.mode == "fixed"
    assert layout.anchor_axes == (0.1, 0.2)
    assert layout.size_axes == (0.35, 0.25)
    updates = legend_style_updates(layout, style)
    assert updates["loc"] == "lower left"
    assert updates["bbox_to_anchor"] == [0.1, 0.2]
    assert updates["box_size"] == [0.35, 0.25]
    assert updates["future_key"] == "keep-me"


def test_invalid_fixed_geometry_falls_back_to_auto_with_diagnostic() -> None:
    from polynexus.core.figures.legend_layout import resolve_legend_layout

    layout = resolve_legend_layout(
        {
            "loc": "upper left",
            "bbox_to_anchor": [0.2, 0.8],
            "box_size": [float("nan"), -0.1],
        }
    )

    assert layout.mode == "auto"
    assert layout.size_axes is None
    assert layout.diagnostic == "invalid legend box geometry; using automatic layout"


def test_auto_layout_uses_measured_content_for_interaction_box() -> None:
    from polynexus.core.figures.legend_layout import resolve_legend_layout

    content = Bbox.from_extents(12.0, 30.0, 110.0, 100.0)
    layout = resolve_legend_layout(
        {"loc": "upper right", "bbox_to_anchor": [1.0, 1.0]},
        content_bbox_display=content,
    )

    assert layout.mode == "auto"
    assert layout.interaction_bbox_display == content


def test_auto_legacy_anchor_remains_available_for_inspector_compatibility() -> None:
    from polynexus.core.figures.legend_layout import resolve_legend_layout

    layout = resolve_legend_layout(
        {"loc": "upper left", "bbox_to_anchor": [0.25, 0.85]}
    )

    assert layout.mode == "auto"
    assert layout.anchor_axes == (0.25, 0.85)
    assert layout.size_axes is None
