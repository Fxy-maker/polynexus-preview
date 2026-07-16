from __future__ import annotations

from polynexus.plot_runtime.bindings import ColumnReference, DataBinding
from polynexus.plot_runtime.layout import LayoutResolver
from polynexus.plot_runtime.models import (
    AxisModel,
    GraphDocument,
    GraphObject,
    PanelModel,
    SourceDataset,
    Worksheet,
)


def _line_worksheet() -> Worksheet:
    source = SourceDataset.from_columns(
        dataset_id="source",
        revision_id="r1",
        columns={"q": [0.0, 0.5, 1.0], "I": [0.0, 0.5, 1.0], "sigma": [0.1, 0.05, 0.1]},
        units={"q": "nm^-1", "I": "a.u.", "sigma": "a.u."},
    )
    return Worksheet.from_source(source)


def _line_document() -> GraphDocument:
    return GraphDocument(
        graph_id="line",
        revision_id="g1",
        canvas_width_px=640,
        canvas_height_px=480,
        panels=(
            PanelModel(
                panel_id="main",
                row=0,
                column=0,
                x_axis=AxisModel("q", "nm^-1", minimum=0.0, maximum=1.0),
                y_axis=AxisModel("I(q)", "a.u.", minimum=0.0, maximum=1.0),
            ),
        ),
        objects=(
            GraphObject(
                object_id="curve",
                object_type="plot_series",
                panel_id="main",
                binding_id="curve-binding",
            ),
        ),
        bindings=(
            DataBinding(
                binding_id="curve-binding",
                object_id="curve",
                kind="line",
                columns=(
                    ColumnReference("x", "q", "nm^-1"),
                    ColumnReference("y", "I", "a.u."),
                    ColumnReference("error", "sigma", "a.u."),
                ),
            ),
        ),
    )


def test_layout_resolver_maps_binding_values_to_panel_curve_and_error_geometry():
    result = LayoutResolver().resolve(_line_document(), _line_worksheet().current)

    assert result.ok
    assert result.scene is not None
    panel = result.scene.panel_by_id("main")
    curve = result.scene.node_by_id("curve")
    assert panel.axis_rect.left > 0
    assert curve.points[0].x == panel.axis_rect.left
    assert curve.points[-1].x == panel.axis_rect.right
    assert curve.points[0].y == panel.axis_rect.bottom
    assert curve.points[-1].y == panel.axis_rect.top
    assert len(curve.segments) == 3
    assert all(segment.start.x == segment.end.x for segment in curve.segments)


def test_layout_resolver_builds_heatmap_cells_and_reports_bad_log_values():
    source = SourceDataset.from_columns(
        dataset_id="heatmap-source",
        revision_id="r1",
        columns={"x": [0.0, 1.0, 0.0, 1.0], "y": [0.0, 0.0, 1.0, 1.0], "z": [1.0, 2.0, 3.0, 4.0]},
    )
    worksheet = Worksheet.from_source(source)
    document = GraphDocument(
        graph_id="heatmap",
        revision_id="g1",
        canvas_width_px=400,
        canvas_height_px=300,
        panels=(
            PanelModel(
                "main",
                0,
                0,
                AxisModel("x", minimum=0.0, maximum=1.0),
                AxisModel("y", minimum=0.0, maximum=1.0),
            ),
        ),
        objects=(GraphObject("heat", "heatmap", "main", "heat-binding"),),
        bindings=(
            DataBinding(
                "heat-binding",
                "heat",
                "heatmap",
                (ColumnReference("x", "x"), ColumnReference("y", "y"), ColumnReference("z", "z")),
            ),
        ),
    )

    result = LayoutResolver().resolve(document, worksheet.current)

    assert result.ok
    assert result.scene is not None
    assert len(result.scene.node_by_id("heat").rectangles) == 4

    bad_document = GraphDocument(
        graph_id="bad-log",
        revision_id="g1",
        canvas_width_px=400,
        canvas_height_px=300,
        panels=(
            PanelModel(
                "main",
                0,
                0,
                AxisModel("x", scale="log", minimum=0.0, maximum=1.0),
                AxisModel("y", minimum=0.0, maximum=1.0),
            ),
        ),
        objects=(GraphObject("curve", "plot_series", "main", "curve-binding"),),
        bindings=(
            DataBinding(
                "curve-binding",
                "curve",
                "line",
                (ColumnReference("x", "x"), ColumnReference("y", "z")),
            ),
        ),
    )
    bad_result = LayoutResolver().resolve(bad_document, worksheet.current)
    assert not bad_result.ok
    assert bad_result.diagnostics[0].reason_code == "invalid_log_axis"


def test_layout_resolver_maps_valid_log_axis_in_logarithmic_space():
    source = SourceDataset.from_columns(
        dataset_id="log-source",
        revision_id="r1",
        columns={"q": [1.0, 10.0, 100.0], "I": [1.0, 10.0, 100.0]},
    )
    worksheet = Worksheet.from_source(source)
    document = GraphDocument(
        graph_id="log-line",
        revision_id="g1",
        canvas_width_px=400,
        canvas_height_px=300,
        panels=(
            PanelModel(
                "main",
                0,
                0,
                AxisModel("q", scale="log", minimum=1.0, maximum=100.0),
                AxisModel("I", scale="log", minimum=1.0, maximum=100.0),
            ),
        ),
        objects=(GraphObject("curve", "plot_series", "main", "binding"),),
        bindings=(
            DataBinding(
                "binding",
                "curve",
                "line",
                (ColumnReference("x", "q"), ColumnReference("y", "I")),
            ),
        ),
    )

    result = LayoutResolver().resolve(document, worksheet.current)

    assert result.ok
    assert result.scene is not None
    panel = result.scene.panel_by_id("main")
    point = result.scene.node_by_id("curve").points[1]
    assert point.x == panel.axis_rect.left + panel.axis_rect.width / 2.0
    assert point.y == panel.axis_rect.top + panel.axis_rect.height / 2.0
