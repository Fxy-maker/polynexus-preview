from __future__ import annotations

import importlib
import importlib.util

from polynexus.gui.widgets.chart_editor import ChartEditor


def test_chart_editor_reuses_generated_drag_execution_helpers_from_mixin() -> None:
    spec = importlib.util.find_spec(
        "polynexus.gui.widgets.chart_editor_generated_drag_execution_mixin"
    )
    assert spec is not None

    module = importlib.import_module(
        "polynexus.gui.widgets.chart_editor_generated_drag_execution_mixin"
    )
    mixin = module.ChartEditorGeneratedDragExecutionMixin

    assert (
        ChartEditor._generated_drag_motion_exceeded_threshold
        is mixin._generated_drag_motion_exceeded_threshold
    )
    assert ChartEditor._on_generated_mouse_move is mixin._on_generated_mouse_move
