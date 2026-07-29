from dataclasses import replace

from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import numpy as np
import pytest

from polynexus.core.figures.render_plan import FigureRenderPlanBuilder
from polynexus.core.figures.renderer import MatplotlibFigureRenderer
from polynexus.gui.figure_render_adapter import FigureRenderAdapter


def test_automatic_multiseries_legend_becomes_single_column_on_narrow_canvas():
    from polynexus.core.figures.legend_presentation import legend_presentation

    presentation = legend_presentation(
        {"auto_generated": True, "style": {"ncol": 2}},
        handle_count=5,
        available_width_px=360,
        default_fontsize=9.0,
    )

    assert presentation.ncol == 1
    assert presentation.fontsize == pytest.approx(7.65)


def test_automatic_multiseries_legend_retains_two_columns_on_wide_canvas():
    from polynexus.core.figures.legend_presentation import legend_presentation

    presentation = legend_presentation(
        {"auto_generated": True, "style": {"ncol": 2}},
        handle_count=5,
        available_width_px=900,
        default_fontsize=9.0,
    )

    assert presentation.ncol == 2
    assert presentation.fontsize == 9.0


def test_automatic_long_name_legend_uses_one_column_before_plot_is_crowded():
    from polynexus.core.figures.legend_presentation import legend_presentation

    presentation = legend_presentation(
        {"auto_generated": True, "style": {"ncol": 2}},
        handle_count=5,
        available_width_px=780,
        labels=("PA6-250-170-S_0_00000",) * 5,
        default_fontsize=9.0,
    )

    assert presentation.ncol == 1


def test_explicit_legend_font_size_overrides_automatic_compact_scaling():
    from polynexus.core.figures.legend_presentation import legend_presentation

    presentation = legend_presentation(
        {"auto_generated": True, "style": {"ncol": 2, "font_size": 15.0}},
        handle_count=5,
        available_width_px=780,
        labels=("PA6-250-170-S_0_00000",) * 5,
        default_fontsize=9.0,
    )

    assert presentation.ncol == 1
    assert presentation.fontsize == 15.0


def test_legend_box_width_limits_columns_without_changing_explicit_font_size():
    from polynexus.core.figures.legend_presentation import legend_presentation

    presentation = legend_presentation(
        {
            "auto_generated": True,
            "style": {"ncol": 2, "font_size": 15.0, "box_size": [0.34, 0.18]},
        },
        handle_count=5,
        available_width_px=2000,
        labels=("PA6-250-170-S_0_00000",) * 5,
        default_fontsize=9.0,
    )

    assert presentation.ncol == 1
    assert presentation.fontsize == 15.0


def test_renderer_anchors_legend_to_persisted_box_size():
    from polynexus.core.figures.renderer import MatplotlibFigureRenderer

    kwargs = MatplotlibFigureRenderer._legend_kwargs(
        {
            "style": {
                "loc": "upper left",
                "bbox_to_anchor": [0.2, 0.8],
                "box_size": [0.4, 0.16],
            }
        }
    )

    assert kwargs["loc"] == "lower left"
    assert kwargs["bbox_to_anchor"] == (0.2, 0.64, 0.4, 0.16)


def test_renderer_legacy_four_value_anchor_matches_resolved_fixed_layout():
    from polynexus.core.figures.legend_layout import resolve_legend_layout
    from polynexus.core.figures.renderer import MatplotlibFigureRenderer

    style = {
        "loc": "lower left",
        "bbox_to_anchor": [0.1, 0.2, 0.35, 0.25],
    }
    layout = resolve_legend_layout(style)
    kwargs = MatplotlibFigureRenderer._legend_kwargs({"style": style})

    assert layout.mode == "fixed"
    assert kwargs["loc"] == "lower left"
    assert kwargs["bbox_to_anchor"] == (0.1, 0.2, 0.35, 0.25)


def test_renderer_legend_geometry_round_trip_uses_live_display_bounds():
    figure = Figure(figsize=(4.0, 3.0), dpi=100)
    FigureCanvasAgg(figure)
    axes = figure.add_subplot(111)
    axes.plot([1.0, 2.0], [1.0, 2.0], label="Series")
    axes.legend(loc="upper right")
    figure.canvas.draw()

    legend = axes.get_legend()
    assert legend is not None
    actual = legend.get_window_extent(figure.canvas.get_renderer())
    adapter = FigureRenderAdapter()
    figure_object = {
        "id": "legend",
        "type": "legend",
        "style": {
            "bbox_to_anchor": [0.1, 0.1],
            "box_size": [0.3, 0.15],
        },
    }

    selected = adapter.legend_selection_bbox(axes, figure_object)

    assert selected is not None
    assert selected.bounds == pytest.approx(actual.bounds)


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


def test_renderer_anchors_box_text_at_its_left_top_corner(built_ir_document):
    run_root, document_path, document = built_ir_document
    document["objects"].append(
        {
            "id": "boxed-text",
            "type": "text",
            "panel_id": "main",
            "text": "Peak",
            "x": 1700.0,
            "y": 0.2,
            "width": 50.0,
            "height": 0.3,
            "style": {"font_size": 12},
        }
    )
    plan = FigureRenderPlanBuilder(run_root).build(document_path, document)

    figure = MatplotlibFigureRenderer().render(plan, dpi=100)
    text_artist = next(
        text
        for text in figure.axes[0].texts
        if text.get_text() == "Peak"
    )

    assert text_artist.get_position() == pytest.approx((1700.0, 0.5))
    assert text_artist.get_ha() == "left"
    assert text_artist.get_va() == "top"


def test_renderer_keeps_axes_text_in_viewport_coordinate_space(built_ir_document):
    run_root, document_path, document = built_ir_document
    document["objects"].append(
        {
            "id": "viewport-text",
            "type": "text",
            "panel_id": "main",
            "coordinate_space": "axes",
            "text": "Viewport",
            "bounds": {"x": 0.2, "y": 0.3, "width": 0.25, "height": 0.1},
            "style": {"font_size": 12},
        }
    )
    plan = FigureRenderPlanBuilder(run_root).build(document_path, document)

    figure = MatplotlibFigureRenderer().render(plan, dpi=100)
    text_artist = next(
        text
        for text in figure.axes[0].texts
        if text.get_text() == "Viewport"
    )

    assert text_artist.get_transform() == figure.axes[0].transAxes
    assert text_artist.get_position() == pytest.approx((0.2, 0.4))


def test_renderer_uses_data_x_axes_transform_for_mixed_text(built_ir_document):
    run_root, document_path, document = built_ir_document
    document["objects"].append(
        {
            "id": "mixed-coordinate-text",
            "type": "text",
            "panel_id": "main",
            "coordinate_space": "xdata_yaxes",
            "text": "Peak assignment",
            "x": 1700.0,
            "y": 0.84,
            "rotation": 90.0,
            "style": {"font_size": 6},
        }
    )
    plan = FigureRenderPlanBuilder(run_root).build(document_path, document)

    figure = MatplotlibFigureRenderer().render(plan, dpi=100)
    text_artist = next(
        text
        for text in figure.axes[0].texts
        if text.get_text() == "Peak assignment"
    )

    assert text_artist.get_transform() == figure.axes[0].get_xaxis_transform()
    assert text_artist.get_position() == pytest.approx((1700.0, 0.84))


def test_renderer_supports_arrow_and_rectangle_annotations(built_ir_document):
    run_root, document_path, document = built_ir_document
    document["objects"].extend(
        [
            {
                "id": "arrow-peak",
                "type": "arrow",
                "panel_id": "main",
                "x1": 1800.0,
                "y1": 0.1,
                "x2": 1700.0,
                "y2": 0.4,
                "style": {"color": "#D55E00", "line_width": 1.2},
            },
            {
                "id": "region-peak",
                "type": "rectangle",
                "panel_id": "main",
                "x": 1700.0,
                "y": 0.1,
                "width": 50.0,
                "height": 0.3,
                "style": {"color": "#0072B2", "line_width": 0.8},
            },
        ]
    )
    plan = FigureRenderPlanBuilder(run_root).build(document_path, document)

    figure = MatplotlibFigureRenderer().render(plan, dpi=150)

    axis = figure.axes[0]
    assert any(
        getattr(artist, "get_gid", lambda: None)() == "pn-object:arrow-peak"
        for artist in figure.findobj()
    )
    assert any(artist.get_gid() == "pn-object:region-peak" for artist in axis.patches)


def test_renderer_supports_quadratic_curve_and_tags_artist(render_plan):
    plan = replace(
        render_plan,
        objects=(
            {
                "id": "curve-1",
                "type": "curve",
                "panel_id": "main",
                "x1": 0.0,
                "y1": 0.0,
                "x2": 1.0,
                "y2": 0.0,
                "control_x": 0.5,
                "control_y": 1.0,
                "style": {"color": "#0072B2", "line_width": 2.0},
            },
        ),
    )

    figure = MatplotlibFigureRenderer().render(plan, dpi=100)

    curve_artists = [
        artist
        for artist in figure.findobj()
        if getattr(artist, "get_gid", lambda: None)() == "pn-object:curve-1"
    ]
    assert len(curve_artists) == 1
    assert curve_artists[0].get_path().vertices.tolist() == [
        [0.0, 0.0],
        [0.5, 1.0],
        [1.0, 0.0],
    ]


def test_renderer_uses_midpoint_for_legacy_curve_control_point(render_plan):
    plan = replace(
        render_plan,
        objects=(
            {
                "id": "legacy-curve",
                "type": "curve",
                "panel_id": "main",
                "x1": 0.0,
                "y1": 0.0,
                "x2": 1.0,
                "y2": 1.0,
            },
        ),
    )

    figure = MatplotlibFigureRenderer().render(plan, dpi=100)

    curve_artist = next(
        artist
        for artist in figure.findobj()
        if getattr(artist, "get_gid", lambda: None)() == "pn-object:legacy-curve"
    )
    assert curve_artist.get_path().vertices.tolist() == [
        [0.0, 0.0],
        [0.5, 0.5],
        [1.0, 1.0],
    ]


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
    panel = replace(render_plan.panels[0], show_legend=False)
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
            "style": {
                "loc": "upper left",
                "bbox_to_anchor": [0.2, 0.8],
                "ncol": 2,
            },
        },
    )
    plan = replace(render_plan, panels=(panel,), objects=objects)

    figure = MatplotlibFigureRenderer().render(plan, dpi=100)

    legend = figure.axes[0].get_legend()
    assert legend is not None
    assert legend._loc == 2
    assert legend._ncols == 2
    assert legend.get_bbox_to_anchor() is not None

    hidden_plan = replace(
        plan,
        objects=(objects[0], {**objects[1], "visible": False}),
    )
    hidden_figure = MatplotlibFigureRenderer().render(hidden_plan, dpi=100)
    assert hidden_figure.axes[0].get_legend() is None


def test_renderer_hides_automatic_legend_when_only_one_series_remains_visible(render_plan):
    panel = replace(render_plan.panels[0], show_legend=False)
    objects = (
        {
            "id": "series-a",
            "type": "plot_series",
            "panel_id": "main",
            "data_ref": "spectrum-data",
            "x_column": "wavenumber_cm1",
            "y_column": "absorbance",
            "name": "Observed",
            "visible": True,
            "style": {},
        },
        {
            "id": "series-b",
            "type": "plot_series",
            "panel_id": "main",
            "data_ref": "spectrum-data",
            "x_column": "wavenumber_cm1",
            "y_column": "absorbance",
            "name": "Reference",
            "visible": True,
            "style": {},
        },
        {
            "id": "legend",
            "type": "legend",
            "panel_id": "main",
            "visible": True,
            "auto_generated": True,
            "style": {"loc": "upper right", "ncol": 1},
        },
    )
    plan = replace(render_plan, panels=(panel,), objects=objects)

    assert MatplotlibFigureRenderer().render(plan, dpi=100).axes[0].get_legend() is not None

    one_visible_plan = replace(
        plan,
        objects=({**objects[0], "visible": False}, objects[1], objects[2]),
    )
    assert MatplotlibFigureRenderer().render(one_visible_plan, dpi=100).axes[0].get_legend() is None


def test_renderer_compacts_automatic_multiseries_legend_on_narrow_canvas(render_plan):
    panel = replace(render_plan.panels[0], show_legend=False)
    objects = tuple(
        {
            "id": f"series-{index}",
            "type": "plot_series",
            "panel_id": "main",
            "data_ref": "spectrum-data",
            "x_column": "wavenumber_cm1",
            "y_column": "absorbance",
            "name": f"PA6-250-{170 + index * 5}-S_0_00000",
            "style": {},
        }
        for index in range(5)
    ) + (
        {
            "id": "legend",
            "type": "legend",
            "panel_id": "main",
            "visible": True,
            "auto_generated": True,
            "style": {"loc": "upper right", "ncol": 2},
        },
    )
    plan = replace(render_plan, width_in=12.0, panels=(panel,), objects=objects)

    renderer = MatplotlibFigureRenderer()
    wide_legend = renderer.render(plan, dpi=100).axes[0].get_legend()
    legend = renderer.render(plan, dpi=100, viewport_width_px=780).axes[0].get_legend()

    assert wide_legend is not None
    assert wide_legend._ncols == 2
    assert legend is not None
    assert legend._ncols == 1
    assert legend.get_texts()[0].get_fontsize() == pytest.approx(7.65)
    assert legend.get_frame().get_visible() is False


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


def test_renderer_supports_masked_regular_grid_heatmap(render_plan):
    plan = replace(
        render_plan,
        objects=(
            {
                "id": "masked-map",
                "type": "heatmap",
                "panel_id": "main",
                "data_ref": "grid",
                "x_column": "x",
                "y_column": "y",
                "z_column": "value",
                "style": {"cmap": "viridis", "colorbar_label": "Value"},
            },
        ),
        data_tables={
            "grid": {
                "x": [0.0, 1.0, 0.0, 1.0],
                "y": [0.0, 0.0, 1.0, 1.0],
                "value": [1.0, float("nan"), 3.0, 4.0],
            }
        },
    )

    figure = MatplotlibFigureRenderer().render(plan, dpi=100)

    assert len(figure.axes[0].collections) == 1


def test_renderer_masks_missing_partial_detector_cells_when_explicitly_allowed(
    render_plan,
):
    plan = replace(
        render_plan,
        objects=(
            {
                "id": "partial-detector",
                "type": "heatmap",
                "panel_id": "main",
                "data_ref": "grid",
                "x_column": "x",
                "y_column": "y",
                "z_column": "value",
                "allow_partial_detector_grid": True,
                "style": {"cmap": "magma", "colorbar_label": "log10(counts)"},
            },
        ),
        data_tables={
            "grid": {
                "x": [0.0, 1.0, 0.0],
                "y": [0.0, 0.0, 1.0],
                "value": [1.0, 2.0, 3.0],
            }
        },
    )

    figure = MatplotlibFigureRenderer().render(plan, dpi=100)

    image = figure.axes[0].collections[0]
    assert np.ma.count_masked(image.get_array()) == 1


def test_renderer_rejects_missing_grid_without_partial_detector_opt_in(
    render_plan,
):
    plan = replace(
        render_plan,
        objects=(
            {
                "id": "partial-detector-without-opt-in",
                "type": "heatmap",
                "panel_id": "main",
                "data_ref": "grid",
                "x_column": "x",
                "y_column": "y",
                "z_column": "value",
                "style": {},
            },
        ),
        data_tables={
            "grid": {
                "x": [0.0, 1.0, 0.0],
                "y": [0.0, 0.0, 1.0],
                "value": [1.0, 2.0, 3.0],
            }
        },
    )

    with pytest.raises(
        ValueError, match="heatmap data does not form a complete regular grid"
    ):
        MatplotlibFigureRenderer().render(plan, dpi=100)


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
