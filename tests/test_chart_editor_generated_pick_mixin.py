from __future__ import annotations

import importlib
import importlib.util

from polynexus.gui.widgets.chart_editor import ChartEditor


def test_chart_editor_reuses_generated_pick_helpers_from_pick_mixin() -> None:
    spec = importlib.util.find_spec(
        "polynexus.gui.widgets.chart_editor_generated_pick_mixin"
    )
    assert spec is not None

    module = importlib.import_module(
        "polynexus.gui.widgets.chart_editor_generated_pick_mixin"
    )
    mixin = module.ChartEditorGeneratedPickMixin

    assert ChartEditor._on_generated_pick_event is mixin._on_generated_pick_event
    assert ChartEditor._generated_pick_signature is mixin._generated_pick_signature
    assert (
        ChartEditor._select_generated_object_from_candidates
        is mixin._select_generated_object_from_candidates
    )
    assert (
        ChartEditor._generated_object_uses_select_only_press
        is mixin._generated_object_uses_select_only_press
    )
    assert ChartEditor._generated_gui_event_id is mixin._generated_gui_event_id
    assert (
        ChartEditor._cycle_generated_selection_after_click
        is mixin._cycle_generated_selection_after_click
    )
