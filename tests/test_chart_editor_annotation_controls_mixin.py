from __future__ import annotations

from polynexus.gui.widgets.chart_editor import ChartEditor


def test_chart_editor_reuses_annotation_control_helpers_from_mixin() -> None:
    from polynexus.gui.widgets.chart_editor_annotation_controls_mixin import (
        ChartEditorAnnotationControlsMixin,
    )

    assert (
        ChartEditor._on_add_text_annotation
        is ChartEditorAnnotationControlsMixin._on_add_text_annotation
    )
    assert (
        ChartEditor._on_update_selected_text_annotation
        is ChartEditorAnnotationControlsMixin._on_update_selected_text_annotation
    )
    assert (
        ChartEditor._on_annotation_apply_style
        is ChartEditorAnnotationControlsMixin._on_annotation_apply_style
    )
    assert (
        ChartEditor._on_add_rectangle_annotation
        is ChartEditorAnnotationControlsMixin._on_add_rectangle_annotation
    )
    assert (
        ChartEditor._on_add_line_annotation
        is ChartEditorAnnotationControlsMixin._on_add_line_annotation
    )
    assert (
        ChartEditor._on_add_arrow_annotation
        is ChartEditorAnnotationControlsMixin._on_add_arrow_annotation
    )
    assert (
        ChartEditor._on_add_highlight_annotation
        is ChartEditorAnnotationControlsMixin._on_add_highlight_annotation
    )
    assert (
        ChartEditor._on_crop_annotation_canvas
        is ChartEditorAnnotationControlsMixin._on_crop_annotation_canvas
    )
    assert (
        ChartEditor._on_annotation_undo
        is ChartEditorAnnotationControlsMixin._on_annotation_undo
    )
    assert (
        ChartEditor._on_annotation_redo
        is ChartEditorAnnotationControlsMixin._on_annotation_redo
    )
    assert (
        ChartEditor._on_annotation_delete
        is ChartEditorAnnotationControlsMixin._on_annotation_delete
    )
    assert (
        ChartEditor._on_annotation_copy
        is ChartEditorAnnotationControlsMixin._on_annotation_copy
    )
    assert (
        ChartEditor._on_annotation_paste
        is ChartEditorAnnotationControlsMixin._on_annotation_paste
    )
    assert (
        ChartEditor._on_annotation_front
        is ChartEditorAnnotationControlsMixin._on_annotation_front
    )
    assert (
        ChartEditor._on_annotation_back
        is ChartEditorAnnotationControlsMixin._on_annotation_back
    )
    assert (
        ChartEditor._sync_annotation_tool_buttons
        is ChartEditorAnnotationControlsMixin._sync_annotation_tool_buttons
    )
    assert (
        ChartEditor._sync_annotation_property_controls
        is ChartEditorAnnotationControlsMixin._sync_annotation_property_controls
    )
    assert (
        ChartEditor._on_annotation_canvas_changed
        is ChartEditorAnnotationControlsMixin._on_annotation_canvas_changed
    )
    assert (
        ChartEditor._set_geometry_controls_enabled
        is ChartEditorAnnotationControlsMixin._set_geometry_controls_enabled
    )
    assert (
        ChartEditor._set_geometry_control_enabled_state
        is ChartEditorAnnotationControlsMixin._set_geometry_control_enabled_state
    )
    assert (
        ChartEditor._set_geometry_spin_ranges
        is ChartEditorAnnotationControlsMixin._set_geometry_spin_ranges
    )
    assert (
        ChartEditor._set_style_controls_enabled
        is ChartEditorAnnotationControlsMixin._set_style_controls_enabled
    )
    assert (
        ChartEditor._set_object_action_buttons_enabled
        is ChartEditorAnnotationControlsMixin._set_object_action_buttons_enabled
    )
    assert (
        ChartEditor._sync_object_action_buttons
        is ChartEditorAnnotationControlsMixin._sync_object_action_buttons
    )
    assert (
        ChartEditor._set_control_value_silently
        is ChartEditorAnnotationControlsMixin._set_control_value_silently
    )
    assert (
        ChartEditor._clear_annotation_property_controls
        is ChartEditorAnnotationControlsMixin._clear_annotation_property_controls
    )
    assert (
        ChartEditor._set_geometry_label_mode
        is ChartEditorAnnotationControlsMixin._set_geometry_label_mode
    )
    assert (
        ChartEditor._on_annotation_geometry_changed
        is ChartEditorAnnotationControlsMixin._on_annotation_geometry_changed
    )
    assert (
        ChartEditor._update_selected_generated_object_geometry
        is ChartEditorAnnotationControlsMixin._update_selected_generated_object_geometry
    )
    assert (
        ChartEditor._sync_generated_object_property_controls
        is ChartEditorAnnotationControlsMixin._sync_generated_object_property_controls
    )
    assert (
        ChartEditor._generated_object_capabilities
        is ChartEditorAnnotationControlsMixin._generated_object_capabilities
    )
    assert (
        ChartEditor._generated_object_geometry_config
        is ChartEditorAnnotationControlsMixin._generated_object_geometry_config
    )
    assert (
        ChartEditor._apply_style_to_selected_generated_object
        is ChartEditorAnnotationControlsMixin._apply_style_to_selected_generated_object
    )
    assert (
        ChartEditor._annotation_line_style_value
        is ChartEditorAnnotationControlsMixin._annotation_line_style_value
    )
    assert (
        ChartEditor._annotation_marker_value
        is ChartEditorAnnotationControlsMixin._annotation_marker_value
    )
    assert (
        ChartEditor._line_style_label_for_value
        is ChartEditorAnnotationControlsMixin._line_style_label_for_value
    )
    assert (
        ChartEditor._marker_label_for_value
        is ChartEditorAnnotationControlsMixin._marker_label_for_value
    )
    assert (
        ChartEditor._generated_plot_series_marker_value
        is ChartEditorAnnotationControlsMixin._generated_plot_series_marker_value
    )
