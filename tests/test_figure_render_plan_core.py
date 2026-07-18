from dataclasses import replace

from matplotlib.figure import Figure
import pytest

from polynexus.core.figures.render_plan import FigureRenderPlanBuilder
from polynexus.core.figures.renderer import MatplotlibFigureRenderer


def test_render_plan_resolves_relative_csv_and_reversed_axis(
    built_ir_document,
):
    run_root, document_path, document = built_ir_document

    plan = FigureRenderPlanBuilder(run_root).build(document_path, document)

    assert plan.figure_id == "ir.frame.spectrum.001"
    assert plan.revision == 1
    assert plan.panels[0].x_axis.reversed is True
    assert plan.data_tables["spectrum-data"]["absorbance"] == [0.1, 0.4]


def test_render_plan_rejects_tampered_data_snapshot(built_ir_document):
    run_root, document_path, document = built_ir_document
    source = document["data_sources"][0]
    data_path = run_root / source["path"]
    data_path.write_text(
        "wavenumber_cm1,absorbance\n1800.0,99.0\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="checksum mismatch"):
        FigureRenderPlanBuilder(run_root).build(document_path, document)


def test_render_plan_preserves_panel_identity_metadata(built_ir_document):
    run_root, document_path, document = built_ir_document
    document["layout"]["panels"][0]["grid_span"] = {"rows": 2, "columns": 3}
    document["layout"]["panels"][0]["panel_label"] = "(a)"

    plan = FigureRenderPlanBuilder(run_root).build(document_path, document)

    panel = plan.panels[0]
    assert panel.row_span == 2
    assert panel.column_span == 3
    assert panel.panel_label == "(a)"


def test_renderer_emits_stable_panel_and_panel_label_ids(built_ir_document):
    run_root, document_path, document = built_ir_document
    document["layout"]["panels"][0]["panel_label"] = "(a)"
    plan = FigureRenderPlanBuilder(run_root).build(document_path, document)

    figure = MatplotlibFigureRenderer().render(plan, dpi=100)

    axis = figure.axes[0]
    assert axis.get_gid() == "pn-panel:main"
    assert axis.texts[0].get_text() == "(a)"
    assert axis.texts[0].get_gid() == "pn-panel-label:main"


@pytest.mark.filterwarnings("error")
def test_renderer_uses_one_plan_for_series_lines_and_text(built_ir_document):
    run_root, document_path, document = built_ir_document
    document["objects"].extend(
        [
            {
                "id": "line-peak",
                "type": "line",
                "panel_id": "main",
                "orientation": "vertical",
                "x": 1700.0,
                "style": {"color": "#D55E00", "line_width": 0.5},
            },
            {
                "id": "text-peak",
                "type": "text",
                "panel_id": "main",
                "text": "1700",
                "x": 1700.0,
                "y": 0.4,
                "rotation": 90.0,
                "style": {"color": "#D55E00", "font_size": 5},
            },
        ]
    )
    plan = FigureRenderPlanBuilder(run_root).build(document_path, document)

    figure = MatplotlibFigureRenderer().render(plan, dpi=150)

    assert isinstance(figure, Figure)
    assert len(figure.axes) == 1
    axis = figure.axes[0]
    assert axis.xaxis_inverted()
    assert len(axis.lines) == 2
    assert [text.get_text() for text in axis.texts] == ["1700"]


def test_renderer_supports_bar_series_and_panel_legend(render_plan):
    panel = replace(render_plan.panels[0], title="Metrics", show_legend=True)
    plan = replace(
        render_plan,
        panels=(panel,),
        objects=(
            {
                "id": "bars",
                "type": "plot_series",
                "panel_id": "main",
                "data_ref": "spectrum-data",
                "x_column": "wavenumber_cm1",
                "y_column": "absorbance",
                "name": "Absorbance",
                "chart_kind": "bar",
                "style": {"color": "#4477AA"},
            },
        ),
    )

    figure = MatplotlibFigureRenderer().render(plan, dpi=100)
    axis = figure.axes[0]

    assert axis.get_title() == "Metrics"
    assert len(axis.patches) == 2
    assert axis.get_legend() is not None


def test_renderer_applies_explicit_lifecycle_legend_visibility_and_position(
    render_plan,
):
    panel = replace(render_plan.panels[0], show_legend=True)
    objects = (
        {
            "id": "series",
            "type": "plot_series",
            "panel_id": "main",
            "data_ref": "spectrum-data",
            "x_column": "wavenumber_cm1",
            "y_column": "absorbance",
            "name": "Absorbance",
            "style": {},
        },
        {
            "id": "legend",
            "type": "legend",
            "panel_id": "main",
            "visible": True,
            "style": {"loc": "upper left", "bbox_to_anchor": [0.2, 0.8]},
        },
    )
    plan = replace(render_plan, panels=(panel,), objects=objects)

    figure = MatplotlibFigureRenderer().render(plan, dpi=100)

    legend = figure.axes[0].get_legend()
    assert legend is not None
    assert legend._loc == 2
    assert legend.get_bbox_to_anchor() is not None

    hidden_plan = replace(
        plan,
        objects=(objects[0], {**objects[1], "visible": False}),
    )
    hidden_figure = MatplotlibFigureRenderer().render(hidden_plan, dpi=100)
    assert hidden_figure.axes[0].get_legend() is None


def test_renderer_supports_regular_grid_heatmap(render_plan):
    plan = replace(
        render_plan,
        objects=(
            {
                "id": "map",
                "type": "heatmap",
                "panel_id": "main",
                "data_ref": "grid",
                "x_column": "q_nm1",
                "y_column": "temperature_C",
                "z_column": "intensity",
                "style": {"cmap": "viridis", "colorbar_label": "I(q)"},
            },
        ),
        data_tables={
            "grid": {
                "q_nm1": [0.1, 0.2, 0.1, 0.2],
                "temperature_C": [30.0, 30.0, 80.0, 80.0],
                "intensity": [10.0, 5.0, 8.0, 4.0],
            }
        },
    )

    figure = MatplotlibFigureRenderer().render(plan, dpi=100)

    assert len(figure.axes[0].collections) == 1
    assert len(figure.axes) == 2
    assert figure.axes[1].get_ylabel() == "I(q)"


def test_renderer_tags_native_image_grid_artists_with_object_id(render_plan):
    plan = replace(
        render_plan,
        objects=(
            {
                "id": "pattern-grid",
                "type": "image_grid",
                "panel_id": "main",
                "data_ref": "grid",
                "grid_column": "grid_column",
                "grid_row": "grid_row",
                "x_column": "pixel_x",
                "y_column": "pixel_y",
                "z_column": "intensity",
                "style": {"cmap": "viridis", "origin": "upper"},
            },
        ),
        data_tables={
            "grid": {
                "grid_column": [0, 0, 0, 0, 1, 1, 1, 1],
                "grid_row": [0, 0, 1, 1, 0, 0, 1, 1],
                "pixel_x": [0, 1, 0, 1, 0, 1, 0, 1],
                "pixel_y": [0, 0, 1, 1, 0, 0, 1, 1],
                "intensity": [1, 2, 3, 4, 5, 6, 7, 8],
            }
        },
    )

    figure = MatplotlibFigureRenderer().render(plan, dpi=100)

    image_artists = [
        artist
        for artist in figure.findobj()
        if getattr(artist, "get_gid", lambda: None)() == "pn-object:pattern-grid"
    ]
    assert len(image_artists) == 8
