from __future__ import annotations

import importlib
import importlib.util

from polynexus.gui.widgets.chart_editor import ChartEditor


def test_chart_editor_reuses_generated_drag_helpers_from_drag_mixin() -> None:
    spec = importlib.util.find_spec(
        "polynexus.gui.widgets.chart_editor_generated_drag_mixin"
    )
    assert spec is not None

    module = importlib.import_module(
        "polynexus.gui.widgets.chart_editor_generated_drag_mixin"
    )
    mixin = module.ChartEditorGeneratedDragMixin

    assert (
        ChartEditor._activate_generated_drag_state
        is mixin._activate_generated_drag_state
    )
    assert (
        ChartEditor._restore_generated_drag_snapshot
        is mixin._restore_generated_drag_snapshot
    )
    assert ChartEditor._cancel_generated_drag is mixin._cancel_generated_drag
