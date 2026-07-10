from __future__ import annotations

import importlib
import importlib.util

from polynexus.gui.widgets.chart_editor import ChartEditor


def test_chart_editor_reuses_generated_selection_helpers_from_mixin() -> None:
    spec = importlib.util.find_spec(
        "polynexus.gui.widgets.chart_editor_generated_selection_mixin"
    )
    assert spec is not None

    module = importlib.import_module(
        "polynexus.gui.widgets.chart_editor_generated_selection_mixin"
    )
    mixin = module.ChartEditorGeneratedSelectionMixin

    assert (
        ChartEditor._reset_generated_selection_model
        is mixin._reset_generated_selection_model
    )
    assert ChartEditor._generated_store is mixin._generated_store
    assert (
        ChartEditor._persist_generated_document
        is mixin._persist_generated_document
    )
    assert (
        ChartEditor._select_generated_object
        is mixin._select_generated_object
    )
    assert (
        ChartEditor._on_generated_selection_changed
        is mixin._on_generated_selection_changed
    )
