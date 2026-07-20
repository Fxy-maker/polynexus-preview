from __future__ import annotations

from polynexus.core.figure_style_bundle import (
    apply_style_bundle,
    capture_style_bundle,
)


def test_style_bundle_captures_supported_style_without_geometry_or_data():
    bundle = capture_style_bundle(
        {
            "id": "line-a",
            "type": "line",
            "data": {"x": [1], "y": [2]},
            "bounds": {"x1": 0.1, "y1": 0.2, "x2": 0.8, "y2": 0.9},
            "style": {"color": "#D55E00", "line_width": 2.0},
        }
    )

    assert bundle["object_type"] == "line"
    assert bundle["style"] == {"color": "#D55E00", "line_width": 2.0}
    assert "data" not in bundle
    assert "bounds" not in bundle


def test_style_bundle_reports_incompatible_fields_instead_of_mutating_them():
    bundle = {
        "version": 1,
        "object_type": "plot_series",
        "style": {"color": "#0072B2", "marker": "o", "marker_size": 8},
    }
    target = {"id": "text-a", "type": "text", "style": {"font_size": 12}}

    result = apply_style_bundle(target, bundle)

    assert result.changed is True
    assert result.object["style"]["color"] == "#0072B2"
    assert result.applied == ("color",)
    assert result.skipped == ("marker", "marker_size")
