from __future__ import annotations

from polynexus.gui.chart_editor_generated_helpers import (
    annotation_line_style_value,
    annotation_marker_value,
    coerce_plot_value,
    format_generated_grid_label,
    generated_plot_series_marker_value,
    line_style_label_for_value,
    marker_label_for_value,
    optional_float,
)


LINE_STYLE_OPTIONS = {
    "Solid": "-",
    "Dashed": "--",
    "Dotted": ":",
}

MARKER_OPTIONS = {
    "None": "",
    "Circle": "o",
    "Square": "s",
}


def test_annotation_style_values_use_mapping_fallbacks() -> None:
    assert annotation_line_style_value("Dashed", LINE_STYLE_OPTIONS) == "--"
    assert annotation_line_style_value("", LINE_STYLE_OPTIONS) == "-"
    assert annotation_marker_value("Circle", MARKER_OPTIONS) == "o"
    assert annotation_marker_value("", MARKER_OPTIONS) == ""


def test_style_labels_round_trip_known_values() -> None:
    assert line_style_label_for_value("--", LINE_STYLE_OPTIONS) == "Dashed"
    assert line_style_label_for_value("?", LINE_STYLE_OPTIONS) == "Solid"
    assert marker_label_for_value("s", MARKER_OPTIONS) == "Square"
    assert marker_label_for_value("?", MARKER_OPTIONS) == "None"


def test_generated_plot_series_marker_value_prefers_explicit_style() -> None:
    assert generated_plot_series_marker_value({"style": {"marker": "^"}}) == "^"
    assert generated_plot_series_marker_value({"chart_kind": "scatter"}) == "o"
    assert generated_plot_series_marker_value({"chart_kind": "line"}) == ""


def test_numeric_helpers_preserve_existing_behaviour() -> None:
    assert format_generated_grid_label(3.0) == "3"
    assert format_generated_grid_label(3.25) == "3.25"
    assert format_generated_grid_label("  raw  ") == "raw"
    assert optional_float("2.5") == 2.5
    assert optional_float("") is None
    assert coerce_plot_value("2.5") == 2.5
    assert coerce_plot_value("") is None
