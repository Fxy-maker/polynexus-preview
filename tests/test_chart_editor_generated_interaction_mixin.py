from __future__ import annotations

import importlib
import importlib.util

from polynexus.gui.widgets.chart_editor import ChartEditor


def test_chart_editor_reuses_generated_interaction_helpers_from_mixin() -> None:
    spec = importlib.util.find_spec(
        "polynexus.gui.widgets.chart_editor_generated_interaction_mixin"
    )
    assert spec is not None

    module = importlib.import_module(
        "polynexus.gui.widgets.chart_editor_generated_interaction_mixin"
    )
    mixin = module.ChartEditorGeneratedInteractionMixin

    assert ChartEditor._on_generated_button_press is mixin._on_generated_button_press
    assert (
        ChartEditor._on_generated_button_release
        is mixin._on_generated_button_release
    )
    assert ChartEditor._on_generated_figure_leave is mixin._on_generated_figure_leave
