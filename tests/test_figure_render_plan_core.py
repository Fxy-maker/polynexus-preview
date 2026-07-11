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
