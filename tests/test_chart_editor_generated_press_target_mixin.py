from __future__ import annotations

import importlib
import importlib.util

from polynexus.gui.widgets.chart_editor import ChartEditor


def test_chart_editor_reuses_generated_press_target_helpers_from_mixin() -> None:
    spec = importlib.util.find_spec(
        "polynexus.gui.widgets.chart_editor_generated_press_target_mixin"
    )
    assert spec is not None

    module = importlib.import_module(
        "polynexus.gui.widgets.chart_editor_generated_press_target_mixin"
    )
    mixin = module.ChartEditorGeneratedPressTargetMixin

    assert (
        ChartEditor._generated_selected_handle_drag_state_for_press
        is mixin._generated_selected_handle_drag_state_for_press
    )
    assert (
        ChartEditor._generated_drag_state_for_press
        is mixin._generated_drag_state_for_press
    )
    assert (
        ChartEditor._generated_press_drag_target
        is mixin._generated_press_drag_target
    )
    assert (
        ChartEditor._generated_press_drag_object_ids
        is mixin._generated_press_drag_object_ids
    )


def test_selected_rectangle_corner_starts_a_rectangle_handle_drag() -> None:
    from polynexus.gui.widgets.chart_editor_generated_press_target_mixin import (
        ChartEditorGeneratedPressTargetMixin,
    )

    class RectanglePressTarget(ChartEditorGeneratedPressTargetMixin):
        def _generated_figure_object_by_id(self, object_id):
            return {"id": object_id, "type": "rectangle"}

        def _generated_point_handle_hit(self, _event, _object_id):
            return 2

    state = RectanglePressTarget()._generated_selected_handle_drag_state_for_press(
        object(), "region"
    )

    assert state == {
        "object_id": "region",
        "kind": "rectangle",
        "handle_index": 2,
        "dirty": False,
    }
