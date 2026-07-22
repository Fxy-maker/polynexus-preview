from __future__ import annotations

import importlib
import importlib.util

from polynexus.gui.widgets.chart_editor import ChartEditor


def test_chart_editor_reuses_render_helper_from_render_mixin() -> None:
    spec = importlib.util.find_spec("polynexus.gui.widgets.chart_editor_render_mixin")
    assert spec is not None

    module = importlib.import_module("polynexus.gui.widgets.chart_editor_render_mixin")
    mixin = module.ChartEditorRenderMixin

    assert ChartEditor._render is mixin._render


def test_chart_editor_render_mixin_prefers_generated_document_preview_before_placeholder() -> None:
    module = importlib.import_module("polynexus.gui.widgets.chart_editor_render_mixin")

    class _Window(module.ChartEditorRenderMixin):
        def __init__(self):
            self._fig_generator = None
            self._generated_document_mode = True
            self._static_file_mode = True
            self.calls = []

        def _show_generated_figure_document(self):
            self.calls.append("generated")
            return True

        def _refresh_static_annotation_canvas_preview(self):
            self.calls.append("static-preview")
            return False

        def _show_style_preview_figure(self):
            self.calls.append("placeholder")

    window = _Window()

    window._render()

    assert window.calls == ["generated"]


def test_chart_editor_render_mixin_uses_placeholder_when_static_preview_cannot_refresh() -> None:
    module = importlib.import_module("polynexus.gui.widgets.chart_editor_render_mixin")

    class _Window(module.ChartEditorRenderMixin):
        def __init__(self):
            self._fig_generator = None
            self._generated_document_mode = False
            self._static_file_mode = True
            self.calls = []

        def _refresh_static_annotation_canvas_preview(self):
            self.calls.append("static-preview")
            return False

        def _show_style_preview_figure(self):
            self.calls.append("placeholder")

    window = _Window()

    window._render()

    assert window.calls == ["static-preview", "placeholder"]


def test_fit_figure_to_live_canvas_accounts_for_high_dpi_device_pixels():
    module = importlib.import_module("polynexus.gui.widgets.chart_editor_render_mixin")
    from matplotlib.figure import Figure

    class _Canvas:
        def width(self):
            return 1000

        def height(self):
            return 800

        def devicePixelRatioF(self):
            return 1.5

    class _Window(module.ChartEditorRenderMixin):
        _dpi = 100

        def __init__(self):
            self._canvas = _Canvas()

    figure = Figure(figsize=(2, 2), dpi=100)
    _Window()._fit_figure_to_live_canvas(figure)

    assert tuple(figure.bbox.bounds)[2:] == (1500.0, 1200.0)
