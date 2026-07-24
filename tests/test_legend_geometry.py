from __future__ import annotations

from matplotlib import pyplot as plt
from matplotlib.transforms import Bbox


def test_import_legacy_style_and_serialize_to_explicit_geometry() -> None:
    from polynexus.core.figures.legend_geometry import import_legend_geometry

    figure, axes = plt.subplots(figsize=(4.0, 3.0), dpi=100)
    try:
        geometry = import_legend_geometry(
            {
                "loc": "upper left",
                "bbox_to_anchor": [0.25, 0.85],
                "box_size": [0.4, 0.16],
                "font_size": 9,
                "ncol": 2,
            },
            axes=axes,
            panel_id="main",
        )
    finally:
        plt.close(figure)

    assert geometry.panel_id == "main"
    assert geometry.rect_axes == (0.25, 0.69, 0.4, 0.16)
    assert geometry.font_size == 9.0
    assert geometry.ncol == 2
    serialized = geometry.serialize()
    assert serialized["legend_geometry"] == {
        "space": "axes",
        "x": 0.25,
        "y": 0.69,
        "width": 0.4,
        "height": 0.16,
    }
    assert "loc" not in serialized
    assert "bbox_to_anchor" not in serialized
    assert "box_size" not in serialized


def test_explicit_geometry_takes_precedence_over_legacy_fields() -> None:
    from polynexus.core.figures.legend_geometry import import_legend_geometry

    geometry = import_legend_geometry(
        {
            "loc": "upper right",
            "bbox_to_anchor": [0.1, 0.9],
            "box_size": [0.2, 0.1],
            "legend_geometry": {
                "space": "axes",
                "x": 0.4,
                "y": 0.3,
                "width": 0.5,
                "height": 0.2,
            },
        }
    )

    assert geometry.rect_axes == (0.4, 0.3, 0.5, 0.2)


def test_resize_preserves_opposite_corner_and_scales_font_monotonically() -> None:
    from polynexus.core.figures.legend_geometry import LegendGeometry

    original = LegendGeometry(
        panel_id="main",
        rect_axes=(0.1, 0.2, 0.3, 0.2),
        rect_display=Bbox.from_bounds(100.0, 80.0, 120.0, 60.0),
        font_size=10.0,
        ncol=2,
    )

    enlarged = original.resized(2, (280.0, 190.0))
    assert enlarged.rect_display is not None
    assert enlarged.rect_display.x0 == 100.0
    assert enlarged.rect_display.y0 == 80.0
    assert enlarged.rect_display.x1 == 280.0
    assert enlarged.rect_display.y1 == 190.0
    assert enlarged.font_size > original.font_size

    reduced = enlarged.resized(2, (110.0, 90.0))
    assert reduced.font_size < enlarged.font_size
    assert reduced.font_size >= 6.0


def test_invalid_geometry_reports_diagnostic_without_crashing() -> None:
    from polynexus.core.figures.legend_geometry import import_legend_geometry

    geometry = import_legend_geometry(
        {
            "legend_geometry": {
                "space": "axes",
                "x": 0.1,
                "y": 0.2,
                "width": float("nan"),
                "height": 0.2,
            }
        }
    )

    assert geometry.rect_axes is None
    assert geometry.diagnostic == "invalid legend geometry; using automatic layout"
