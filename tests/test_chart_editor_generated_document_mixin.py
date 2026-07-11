from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from polynexus.gui.widgets.chart_editor import ChartEditor


def test_chart_editor_reuses_generated_document_and_static_preview_helpers_from_mixin() -> None:
    from polynexus.gui.widgets.chart_editor_generated_document_mixin import (
        ChartEditorGeneratedDocumentMixin,
    )

    assert (
        ChartEditor._show_style_preview_figure
        is ChartEditorGeneratedDocumentMixin._show_style_preview_figure
    )
    assert (
        ChartEditor._is_generated_figure_document
        is ChartEditorGeneratedDocumentMixin._is_generated_figure_document
    )
    assert (
        ChartEditor._show_generated_figure_document
        is ChartEditorGeneratedDocumentMixin._show_generated_figure_document
    )
    assert (
        ChartEditor._build_generated_figure_document
        is ChartEditorGeneratedDocumentMixin._build_generated_figure_document
    )
    assert (
        ChartEditor._has_generated_image_grid_object
        is ChartEditorGeneratedDocumentMixin._has_generated_image_grid_object
    )
    assert (
        ChartEditor._build_generated_image_grid_figure
        is ChartEditorGeneratedDocumentMixin._build_generated_image_grid_figure
    )
    assert (
        ChartEditor._load_image_grid_records
        is ChartEditorGeneratedDocumentMixin._load_image_grid_records
    )
    assert (
        ChartEditor._format_generated_grid_label
        is ChartEditorGeneratedDocumentMixin._format_generated_grid_label
    )
    assert (
        ChartEditor._load_generated_document_data_sources
        is ChartEditorGeneratedDocumentMixin._load_generated_document_data_sources
    )
    assert (
        ChartEditor._render_generated_figure_object
        is ChartEditorGeneratedDocumentMixin._render_generated_figure_object
    )
    assert (
        ChartEditor._render_generated_heatmap
        is ChartEditorGeneratedDocumentMixin._render_generated_heatmap
    )
    assert (
        ChartEditor._generated_object_xy
        is ChartEditorGeneratedDocumentMixin._generated_object_xy
    )
    assert (
        ChartEditor._generated_column_values
        is ChartEditorGeneratedDocumentMixin._generated_column_values
    )
    assert (
        ChartEditor._add_generated_selection_handles
        is ChartEditorGeneratedDocumentMixin._add_generated_selection_handles
    )
    assert (
        ChartEditor._apply_generated_document_axes_style
        is ChartEditorGeneratedDocumentMixin._apply_generated_document_axes_style
    )
    assert (
        ChartEditor._coerce_plot_value
        is ChartEditorGeneratedDocumentMixin._coerce_plot_value
    )
    assert (
        ChartEditor._optional_float
        is ChartEditorGeneratedDocumentMixin._optional_float
    )
    assert (
        ChartEditor._show_source_image_figure
        is ChartEditorGeneratedDocumentMixin._show_source_image_figure
    )
    assert (
        ChartEditor._build_source_image_figure
        is ChartEditorGeneratedDocumentMixin._build_source_image_figure
    )
    assert (
        ChartEditor._refresh_static_annotation_canvas_preview
        is ChartEditorGeneratedDocumentMixin._refresh_static_annotation_canvas_preview
    )
    assert (
        ChartEditor._figure_to_qimage
        is ChartEditorGeneratedDocumentMixin._figure_to_qimage
    )
    assert (
        ChartEditor._load_source_image_array
        is ChartEditorGeneratedDocumentMixin._load_source_image_array
    )
    assert (
        ChartEditor._save_static_rendered_figure
        is ChartEditorGeneratedDocumentMixin._save_static_rendered_figure
    )
    assert (
        ChartEditor._save_static_canvas_to_path
        is ChartEditorGeneratedDocumentMixin._save_static_canvas_to_path
    )
    assert (
        ChartEditor._save_static_canvas_vector
        is ChartEditorGeneratedDocumentMixin._save_static_canvas_vector
    )
    assert (
        ChartEditor._replace_canvas_figure
        is ChartEditorGeneratedDocumentMixin._replace_canvas_figure
    )
    assert (
        ChartEditor._show_placeholder_style_preview
        is ChartEditorGeneratedDocumentMixin._show_placeholder_style_preview
    )
    assert (
        ChartEditor._apply_sci_defaults
        is ChartEditorGeneratedDocumentMixin._apply_sci_defaults
    )


def test_manifest_document_builds_figure_from_shared_render_plan(
    monkeypatch,
    tmp_path,
) -> None:
    from polynexus.gui.widgets import chart_editor_generated_document_mixin as module

    calls = {}
    expected_plan = SimpleNamespace(figure_id="manifest-figure")
    expected_figure = object()
    document_path = tmp_path / "figure.pnfig.json"

    class _Builder:
        def __init__(self, run_root):
            calls["run_root"] = run_root

        def build(self, path, document):
            calls["document_path"] = path
            calls["document"] = document
            return expected_plan

    class _Renderer:
        def render(self, plan, *, dpi):
            calls["plan"] = plan
            calls["dpi"] = dpi
            return expected_figure

    monkeypatch.setattr(module, "FigureRenderPlanBuilder", _Builder, raising=False)
    monkeypatch.setattr(module, "MatplotlibFigureRenderer", _Renderer, raising=False)

    editor = object.__new__(module.ChartEditorGeneratedDocumentMixin)
    editor._figure_document = {"mode": "object", "figure_id": "manifest-figure"}
    editor._source_entry_context = SimpleNamespace(
        run_root=str(tmp_path),
        document_path=str(document_path),
    )
    editor._dpi = 150
    editor._shared_render_plan = None

    figure = editor._build_generated_figure_document()

    assert figure is expected_figure
    assert calls == {
        "run_root": Path(tmp_path),
        "document_path": document_path,
        "document": editor._figure_document,
        "plan": expected_plan,
        "dpi": 150,
    }
    assert editor._shared_render_plan is expected_plan
