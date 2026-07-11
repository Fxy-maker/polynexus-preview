from __future__ import annotations

import importlib
import importlib.util

from polynexus.gui.widgets.chart_editor import ChartEditor


def test_chart_editor_reuses_generated_pointer_feedback_helpers_from_mixin() -> None:
    spec = importlib.util.find_spec(
        "polynexus.gui.widgets.chart_editor_generated_pointer_feedback_mixin"
    )
    assert spec is not None

    module = importlib.import_module(
        "polynexus.gui.widgets.chart_editor_generated_pointer_feedback_mixin"
    )
    mixin = module.ChartEditorGeneratedPointerFeedbackMixin

    assert (
        ChartEditor._remember_generated_pointer_event
        is mixin._remember_generated_pointer_event
    )
    assert (
        ChartEditor._refresh_generated_feedback_from_last_pointer
        is mixin._refresh_generated_feedback_from_last_pointer
    )
