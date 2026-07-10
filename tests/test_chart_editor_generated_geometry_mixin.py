from __future__ import annotations

import importlib
import importlib.util

from polynexus.gui.widgets.chart_editor import ChartEditor


def test_chart_editor_reuses_generated_geometry_helpers_from_mixin() -> None:
    spec = importlib.util.find_spec(
        "polynexus.gui.widgets.chart_editor_generated_geometry_mixin"
    )
    assert spec is not None

    module = importlib.import_module(
        "polynexus.gui.widgets.chart_editor_generated_geometry_mixin"
    )
    mixin = module.ChartEditorGeneratedGeometryMixin

    assert ChartEditor._generated_line_artist is mixin._generated_line_artist
    assert (
        ChartEditor._generated_hover_handle_artist
        is mixin._generated_hover_handle_artist
    )
    assert (
        ChartEditor._generated_current_handle_artist
        is mixin._generated_current_handle_artist
    )
    assert (
        ChartEditor._generated_event_data_coordinates
        is mixin._generated_event_data_coordinates
    )
    assert (
        ChartEditor._generated_event_axes_fraction
        is mixin._generated_event_axes_fraction
    )
    assert (
        ChartEditor._apply_generated_line_handle_drag
        is mixin._apply_generated_line_handle_drag
    )
    assert (
        ChartEditor._apply_generated_line_body_drag
        is mixin._apply_generated_line_body_drag
    )
    assert (
        ChartEditor._apply_generated_plot_series_handle_drag
        is mixin._apply_generated_plot_series_handle_drag
    )
    assert ChartEditor._generated_legend_artist is mixin._generated_legend_artist
    assert (
        ChartEditor._generated_legend_window_extent
        is mixin._generated_legend_window_extent
    )
    assert (
        ChartEditor._window_extent_contains_with_slop
        is mixin._window_extent_contains_with_slop
    )
    assert (
        ChartEditor._generated_legend_drag_start
        is mixin._generated_legend_drag_start
    )
    assert (
        ChartEditor._generated_legend_anchor_for_drag
        is mixin._generated_legend_anchor_for_drag
    )
    assert (
        ChartEditor._apply_generated_legend_drag
        is mixin._apply_generated_legend_drag
    )
    assert (
        ChartEditor._materialize_generated_plot_series_inline_data
        is mixin._materialize_generated_plot_series_inline_data
    )
    assert (
        ChartEditor._update_generated_line_preview
        is mixin._update_generated_line_preview
    )
    assert (
        ChartEditor._update_generated_plot_series_preview
        is mixin._update_generated_plot_series_preview
    )
    assert (
        ChartEditor._update_generated_legend_preview
        is mixin._update_generated_legend_preview
    )
    assert ChartEditor._is_left_mouse_button is mixin._is_left_mouse_button
    assert (
        ChartEditor._ensure_generated_legend_object
        is mixin._ensure_generated_legend_object
    )
    assert (
        ChartEditor._generated_legend_visible
        is mixin._generated_legend_visible
    )
    assert (
        ChartEditor._generated_figure_object_by_id
        is mixin._generated_figure_object_by_id
    )
    assert (
        ChartEditor._generated_figure_object_by_id_including_deleted
        is mixin._generated_figure_object_by_id_including_deleted
    )
    assert (
        ChartEditor._clear_selected_generated_plot_series_handle_context
        is mixin._clear_selected_generated_plot_series_handle_context
    )
    assert (
        ChartEditor._clear_selected_generated_line_handle_context
        is mixin._clear_selected_generated_line_handle_context
    )
    assert (
        ChartEditor._reset_generated_handle_memory
        is mixin._reset_generated_handle_memory
    )
    assert (
        ChartEditor._set_selected_generated_line_handle_context
        is mixin._set_selected_generated_line_handle_context
    )
    assert (
        ChartEditor._selected_generated_line_handle_index_for_object
        is mixin._selected_generated_line_handle_index_for_object
    )
    assert (
        ChartEditor._set_selected_generated_plot_series_handle_context
        is mixin._set_selected_generated_plot_series_handle_context
    )
    assert (
        ChartEditor._selected_generated_plot_series_point_index
        is mixin._selected_generated_plot_series_point_index
    )
