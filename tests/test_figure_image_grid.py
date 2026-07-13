from __future__ import annotations

from polynexus.core.figure_objects import normalize_figure_object
from polynexus.core.figures.contracts import (
    AxisDefinition,
    DataColumnDefinition,
    FigureDataSourceDefinition,
    FigureDefinition,
    FigureLayoutDefinition,
    PanelDefinition,
)
from polynexus.core.figures.render_plan import FigureRenderPlan, RenderAxis, RenderPanel
from polynexus.core.figures.renderer import MatplotlibFigureRenderer
from polynexus.core.figures.validation import validate_figure_definition


def _definition() -> FigureDefinition:
    panel = PanelDefinition(
        panel_id="patterns",
        row=0,
        column=0,
        x_axis=AxisDefinition("x", "Pixel x"),
        y_axis=AxisDefinition("y", "Pixel y"),
        panel_label="(a)",
    )
    source = FigureDataSourceDefinition(
        source_id="patterns-data",
        columns=tuple(
            DataColumnDefinition(name, "", dtype)
            for name, dtype in (
                ("grid_column", "int64"),
                ("grid_row", "int64"),
                ("pixel_x", "float64"),
                ("pixel_y", "float64"),
                ("intensity", "float64"),
            )
        ),
        values={
            "grid_column": (0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1),
            "grid_row": (0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1),
            "pixel_x": (0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1),
            "pixel_y": (0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1),
            "intensity": (1, 2, 3, 4, 2, 3, 4, 5, 3, 4, 5, 6),
        },
    )
    return FigureDefinition(
        figure_id="waxs.strain.evolution",
        technique="waxs",
        scope="series",
        category="series_overview",
        publication_role="main",
        title="WAXS strain patterns",
        layout=FigureLayoutDefinition(7.0, 3.8, 1, 1, (panel,)),
        data_sources=(source,),
        objects=({
            "id": "pattern-grid",
            "type": "image_grid",
            "panel_id": "patterns",
            "data_ref": "patterns-data",
            "grid_column": "grid_column",
            "grid_row": "grid_row",
            "x_column": "pixel_x",
            "y_column": "pixel_y",
            "z_column": "intensity",
            "style": {"cmap": "viridis"},
        },),
        recipe={"module": "test", "function": "test"},
        style_profile="sci_default",
    )


def test_image_grid_is_known_and_validated_as_editable_figure_object() -> None:
    assert normalize_figure_object({"type": "image_grid"})["type"] == "image_grid"
    validate_figure_definition(_definition())


def test_renderer_draws_each_grid_cell_as_an_image() -> None:
    plan = FigureRenderPlan(
        run_id="run",
        figure_id="waxs.strain.evolution",
        revision=1,
        width_in=7.0,
        height_in=3.8,
        rows=1,
        columns=1,
        horizontal_spacing=0.25,
        vertical_spacing=0.25,
        panels=(RenderPanel("patterns", 0, 0, RenderAxis("Pixel x", "", "linear", False), RenderAxis("Pixel y", "", "linear", False), panel_label="(a)"),),
        objects=tuple(_definition().objects),
        data_tables={"patterns-data": {name: list(values) for name, values in _definition().data_sources[0].values.items()}},
        background="white",
    )
    figure = MatplotlibFigureRenderer().render(plan, dpi=100)
    assert sum(
        len(child.images)
        for axis in figure.axes
        for child in getattr(axis, "child_axes", ())
    ) == 4
