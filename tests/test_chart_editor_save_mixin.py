from __future__ import annotations

import importlib
import importlib.util
from copy import deepcopy

from polynexus.gui.widgets.chart_editor import ChartEditor


def test_chart_editor_reuses_save_and_style_helpers_from_save_mixin() -> None:
    spec = importlib.util.find_spec("polynexus.gui.widgets.chart_editor_save_mixin")
    assert spec is not None

    module = importlib.import_module("polynexus.gui.widgets.chart_editor_save_mixin")
    mixin = module.ChartEditorSaveMixin

    assert ChartEditor.save_to_target is mixin.save_to_target
    assert ChartEditor.save_as is mixin.save_as
    assert ChartEditor._save_to_path is mixin._save_to_path
    assert (
        ChartEditor._save_generated_document_figure
        is mixin._save_generated_document_figure
    )
    assert (
        ChartEditor._generated_document_for_save
        is mixin._generated_document_for_save
    )
    assert ChartEditor._backup_current_static_source is mixin._backup_current_static_source
    assert ChartEditor._collect_style_state is mixin._collect_style_state
    assert ChartEditor._annotation_state is mixin._annotation_state
    assert ChartEditor._should_save_static_canvas is mixin._should_save_static_canvas
    assert ChartEditor._apply_saved_style is mixin._apply_saved_style
    assert (
        ChartEditor._apply_generated_document_style_controls
        is mixin._apply_generated_document_style_controls
    )
    assert ChartEditor._set_line_edit is mixin._set_line_edit
    assert ChartEditor._set_combo is mixin._set_combo


def test_chart_editor_save_mixin_save_to_target_delegates_to_save_as_without_target() -> None:
    module = importlib.import_module("polynexus.gui.widgets.chart_editor_save_mixin")

    class _Window(module.ChartEditorSaveMixin):
        def __init__(self):
            self._target_path = ""
            self.calls = []

        def save_as(self, fmt=None):
            self.calls.append(("save_as", fmt))

        def _save_to_path(self, path):
            self.calls.append(("save_to_path", path))

    window = _Window()

    window.save_to_target()

    assert window.calls == [("save_as", None)]


def test_chart_editor_save_mixin_generated_document_for_save_merges_style_state() -> None:
    module = importlib.import_module("polynexus.gui.widgets.chart_editor_save_mixin")

    class _Window(module.ChartEditorSaveMixin):
        def __init__(self):
            self._figure_document = {
                "mode": "draft",
                "style": {
                    "colour_scheme": "Old",
                    "font": "OldFont",
                    "line_width": "Thin",
                    "figure_size": "Legacy",
                    "grid_on": False,
                    "grid_alpha": 0.1,
                    "bg_color": "#000000",
                    "dpi": 72,
                    "title": "Old title",
                    "xlabel": "Old x",
                    "ylabel": "Old y",
                    "keep": "untouched",
                },
            }
            self._style_state = {
                "colour_scheme": "Wong (SCI)",
                "font": "Small",
                "line_width": "Normal",
                "figure_size": "Small (4in)",
                "grid_on": True,
                "grid_alpha": 0.4,
                "bg_color": "#FFFFFF",
                "dpi": 300,
                "title": "New title",
                "xlabel": "New x",
                "ylabel": "New y",
            }

        def _collect_style_state(self):
            return deepcopy(self._style_state)

    window = _Window()

    document = window._generated_document_for_save()

    assert document["mode"] == "object"
    assert document["style"]["colour_scheme"] == "Wong (SCI)"
    assert document["style"]["font"] == "Small"
    assert document["style"]["line_width"] == "Normal"
    assert document["style"]["figure_size"] == "Small (4in)"
    assert document["style"]["grid_on"] is True
    assert document["style"]["grid_alpha"] == 0.4
    assert document["style"]["bg_color"] == "#FFFFFF"
    assert document["style"]["dpi"] == 300
    assert document["style"]["title"] == "New title"
    assert document["style"]["xlabel"] == "New x"
    assert document["style"]["ylabel"] == "New y"
    assert document["style"]["keep"] == "untouched"
    assert window._figure_document["mode"] == "draft"
