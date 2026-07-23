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
        def render(self, plan, *, dpi, viewport_width_px):
            calls["plan"] = plan
            calls["dpi"] = dpi
            calls["viewport_width_px"] = viewport_width_px
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
    editor._canvas = SimpleNamespace(width=lambda: 780)
    editor._ensure_generated_legend_object = lambda: None

    figure = editor._build_generated_figure_document()

    assert figure is expected_figure
    assert calls == {
        "run_root": Path(tmp_path),
        "document_path": document_path,
        "document": editor._figure_document,
        "plan": expected_plan,
        "dpi": 150,
        "viewport_width_px": 780.0,
    }
    assert editor._shared_render_plan is expected_plan


def test_manifest_editor_registers_native_image_grid_artists_for_object_editing(
    monkeypatch,
):
    from matplotlib.figure import Figure

    from polynexus.gui.figure_render_adapter import FigureRenderAdapter
    from polynexus.gui.widgets import chart_editor_generated_document_mixin as module

    expected_plan = SimpleNamespace(figure_id="native-grid")
    figure = Figure(figsize=(2.0, 1.0), dpi=100)
    image_artist = figure.add_subplot(111).imshow([[1.0, 2.0], [3.0, 4.0]])

    class _Builder:
        def __init__(self, _run_root):
            pass

        def build(self, _path, _document):
            return expected_plan

    class _Renderer:
        last_artist_map = {"pattern-grid": [image_artist]}

        def render(self, _plan, *, dpi, viewport_width_px=None):
            assert dpi == 120
            assert viewport_width_px is None
            return figure

    monkeypatch.setattr(module, "FigureRenderPlanBuilder", _Builder)
    monkeypatch.setattr(module, "MatplotlibFigureRenderer", _Renderer)

    editor = object.__new__(module.ChartEditorGeneratedDocumentMixin)
    editor._figure_document = {"mode": "object", "figure_id": "native-grid"}
    editor._source_entry_context = SimpleNamespace(
        run_root="/tmp/run",
        document_path="/tmp/run/figure.pnfig.json",
    )
    editor._dpi = 120
    editor._shared_render_plan = None
    editor._figure_render_adapter = FigureRenderAdapter()
    editor._selected_figure_object_id = "pattern-grid"
    editor._ensure_generated_legend_object = lambda: None
    editor._add_generated_selection_handles = lambda *_args: None

    assert editor._build_generated_figure_document() is figure
    assert editor._figure_render_adapter.artists_for_object_id("pattern-grid") == [
        image_artist
    ]


def test_formal_editor_style_preserves_object_text_font_size() -> None:
    from matplotlib.figure import Figure

    from polynexus.gui.widgets.chart_editor_generated_document_mixin import (
        ChartEditorGeneratedDocumentMixin,
    )

    figure = Figure(figsize=(4.0, 2.0), dpi=100)
    axis = figure.add_subplot(111)
    label = axis.text(0.5, 0.5, "Peak", fontsize=72.0)
    guide_label = axis.text(0.1, 0.1, "Guide", fontsize=72.0)

    editor = object.__new__(ChartEditorGeneratedDocumentMixin)
    editor._figure_document = {
        "objects": [{"id": "label", "type": "text", "style": {"font_size": 72.0}}]
    }
    editor._bg_color = "#FFFFFF"
    editor._fig_size = (4.0, 2.0)
    editor._title_edit = SimpleNamespace(text=lambda: "")
    editor._xlabel_edit = SimpleNamespace(text=lambda: "")
    editor._ylabel_edit = SimpleNamespace(text=lambda: "")
    editor._title_size = 14
    editor._label_size = 14
    editor._tick_size = 10
    editor._grid_on = False
    editor._current_colours = ["#000000"]
    editor._line_width = 1.0

    editor._apply_formal_editor_style(figure, {"label": [label]})

    assert label.get_fontsize() == 72.0
    assert guide_label.get_fontsize() == 12.0


def test_legacy_editor_rebuilds_native_image_grid_from_numeric_csv(tmp_path):
    from polynexus.gui.figure_render_adapter import FigureRenderAdapter
    from polynexus.gui.widgets.chart_editor_generated_document_mixin import (
        ChartEditorGeneratedDocumentMixin,
    )

    csv_path = tmp_path / "image-grid.csv"
    csv_path.write_text(
        "grid_column,grid_row,pixel_x,pixel_y,intensity,strain_pct\n"
        "0,0,0,0,1,0\n"
        "0,0,1,0,2,0\n"
        "0,0,0,1,3,0\n"
        "0,0,1,1,4,0\n"
        "1,0,0,0,5,50\n"
        "1,0,1,0,6,50\n"
        "1,0,0,1,7,50\n"
        "1,0,1,1,8,50\n",
        encoding="utf-8",
    )
    object_payload = {
        "id": "pattern-grid",
        "type": "image_grid",
        "data_ref": "grid-data",
        "grid_column": "grid_column",
        "grid_row": "grid_row",
        "x_column": "pixel_x",
        "y_column": "pixel_y",
        "z_column": "intensity",
        "label_column": "strain_pct",
        "style": {"cmap": "viridis", "origin": "lower"},
    }
    editor = object.__new__(ChartEditorGeneratedDocumentMixin)
    editor._source_path = str(tmp_path / "figure.png")
    editor._figure_document = {
        "mode": "object",
        "style": {},
        "data_sources": [
            {"id": "grid-data", "kind": "csv", "path": csv_path.name}
        ],
    }
    editor._generated_figure_objects = lambda: [object_payload]
    editor._figure_render_adapter = FigureRenderAdapter()
    editor._selected_figure_object_id = ""

    assert editor._has_generated_image_grid_object() is True
    records = editor._load_image_grid_records(object_payload, {})

    assert [(item["grid_col"], item["grid_row"]) for item in records] == [
        (0, 0),
        (1, 0),
    ]
    assert [item["image"].tolist() for item in records] == [
        [[1.0, 2.0], [3.0, 4.0]],
        [[5.0, 6.0], [7.0, 8.0]],
    ]

    editor._fig_size = (4.0, 2.0)
    editor._dpi = 100
    editor._bg_color = "#FFFFFF"
    editor._title_size = 8
    editor._tick_size = 6
    editor._title_edit = SimpleNamespace(text=lambda: "WAXS strain patterns")
    figure = editor._build_generated_image_grid_figure({})

    assert figure is not None
    assert len(figure.axes) == 2
    assert len(editor._figure_render_adapter.artists_for_object_id("pattern-grid")) == 6
