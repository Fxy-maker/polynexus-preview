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
