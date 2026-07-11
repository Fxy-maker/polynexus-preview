from __future__ import annotations

import importlib
import importlib.util

from polynexus.gui.widgets.chart_editor import ChartEditor


def test_chart_editor_reuses_generated_hit_testing_helpers_from_mixin() -> None:
    spec = importlib.util.find_spec(
        "polynexus.gui.widgets.chart_editor_generated_hit_testing_mixin"
    )
    assert spec is not None

    module = importlib.import_module(
        "polynexus.gui.widgets.chart_editor_generated_hit_testing_mixin"
    )
    mixin = module.ChartEditorGeneratedHitTestingMixin

    assert ChartEditor._generated_line_drag_start is mixin._generated_line_drag_start
    assert ChartEditor._generated_line_endpoint_hit is mixin._generated_line_endpoint_hit
    assert (
        ChartEditor._generated_plot_series_drag_hit
        is mixin._generated_plot_series_drag_hit
    )
    assert (
        ChartEditor._generated_plot_series_point_hit
        is mixin._generated_plot_series_point_hit
    )
    assert ChartEditor._generated_point_handle_hit is mixin._generated_point_handle_hit
    assert (
        ChartEditor._nearest_pixel_point_match is mixin._nearest_pixel_point_match
    )
    assert (
        ChartEditor._generated_plot_series_points
        is mixin._generated_plot_series_points
    )
