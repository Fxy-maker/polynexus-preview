import math
from types import SimpleNamespace

from matplotlib import colors as mcolors
from matplotlib.backend_bases import MouseEvent
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
import pytest

from polynexus.gui.figure_render_adapter import FigureRenderAdapter


def _render_object(ax, obj, index):
    style = obj.get("style", {})
    if obj.get("type") == "plot_series":
        return ax.plot(
            obj["data"]["x"],
            obj["data"]["y"],
            label=obj.get("name", f"Series {index}"),
            color=style.get("color", "#111111"),
            linewidth=style.get("line_width", 0.8),
            alpha=style.get("alpha"),
        )
    if obj.get("type") == "line":
        return ax.axvline(
            obj.get("x", 0.5),
            color=style.get("color", "#333333"),
            linewidth=style.get("line_width", 1.0),
            alpha=style.get("alpha"),
        )
    return []


def _apply_axes_style(ax):
    ax.legend()


def test_figure_render_adapter_maps_rendered_artists_back_to_object_ids_and_highlights_selection():
    adapter = FigureRenderAdapter()
    objects = [
        {
            "id": "series-b",
            "type": "plot_series",
            "name": "Reference",
            "z_index": 2,
            "data": {"x": [0.0, 1.0], "y": [0.5, 1.5]},
            "style": {"color": "#0072B2", "line_width": 0.8, "alpha": 0.2},
        },
        {
            "id": "series-a",
            "type": "plot_series",
            "name": "Observed",
            "z_index": 1,
            "data": {"x": [0.0, 1.0], "y": [1.0, 2.0]},
            "style": {"color": "#D55E00", "line_width": 0.8, "alpha": 0.2},
        },
    ]

    fig, artist_map = adapter.render_document(
        document={},
        objects=objects,
        figsize=(4.0, 3.0),
        dpi=100,
        background="#FFFFFF",
        render_object=_render_object,
        apply_axes_style=_apply_axes_style,
        selected_object_id="series-a",
    )

    assert fig is not None
    assert set(artist_map) >= {"series-a", "series-b", "legend"}

    selected_artist = artist_map["series-a"][0]
    other_artist = artist_map["series-b"][0]

    assert adapter.object_id_for_artist(selected_artist) == "series-a"
    assert adapter.object_id_for_artist(other_artist) == "series-b"
    assert selected_artist.get_linewidth() == pytest.approx(0.8)
    assert other_artist.get_linewidth() == pytest.approx(0.8)
    assert selected_artist.get_path_effects()
    assert other_artist.get_path_effects() == []
    assert selected_artist.get_zorder() > other_artist.get_zorder()
    assert other_artist.get_alpha() == pytest.approx(0.2)
    assert selected_artist.get_pickradius() == pytest.approx(10.0)
    assert other_artist.get_pickradius() == pytest.approx(10.0)


def test_figure_render_adapter_maps_legend_artists_to_legend_object_id():
    adapter = FigureRenderAdapter()
    objects = [
        {
            "id": "series-a",
            "type": "plot_series",
            "name": "Observed",
            "data": {"x": [0.0, 1.0], "y": [1.0, 2.0]},
            "style": {"line_width": 1.0},
        }
    ]

    fig, artist_map = adapter.render_document(
        document={},
        objects=objects,
        figsize=(4.0, 3.0),
        dpi=100,
        background="#FFFFFF",
        render_object=_render_object,
        apply_axes_style=_apply_axes_style,
    )

    assert fig is not None
    assert "legend" in artist_map
    assert artist_map["legend"][0] is fig.axes[0].get_legend()

    for artist in artist_map["legend"]:
        assert adapter.object_id_for_artist(artist) == "legend"


def test_legend_selection_overlay_reflows_when_figure_viewport_changes():
    figure = Figure(figsize=(4.0, 3.0), dpi=100)
    FigureCanvasAgg(figure)
    axes = figure.add_subplot(111)
    axes.plot([0.0, 1.0], [0.0, 1.0], label="Observed")
    axes.plot([0.0, 1.0], [1.0, 0.0], label="Reference")
    axes.legend(loc="upper right")
    adapter = FigureRenderAdapter()
    legend_object = {"id": "legend", "type": "legend"}

    frames = adapter.add_selection_frame(axes, legend_object)
    handles = adapter.add_selection_handles(axes, legend_object)
    assert frames and handles

    figure.canvas.draw()
    figure.set_size_inches(7.0, 3.0, forward=False)
    axes.set_position((0.12, 0.14, 0.78, 0.74))
    figure.canvas.draw()

    live_bounds = axes.get_legend().get_window_extent(figure.canvas.get_renderer()).bounds
    assert frames[0].get_bbox().bounds == pytest.approx(live_bounds)
    offsets = handles[0].get_offsets()
    assert tuple(offsets[0]) == pytest.approx(live_bounds[:2])
    assert tuple(offsets[2]) == pytest.approx(
        (live_bounds[0] + live_bounds[2], live_bounds[1] + live_bounds[3])
    )


def test_figure_render_adapter_expands_pick_radius_for_registered_scatter_artists():
    adapter = FigureRenderAdapter()

    def render_scatter(ax, obj, _index):
        return ax.scatter(
            obj["data"]["x"],
            obj["data"]["y"],
            label=obj.get("name", "Scatter"),
        )

    fig, artist_map = adapter.render_document(
        document={},
        objects=[
            {
                "id": "scatter-a",
                "type": "plot_series",
                "name": "Observed",
                "data": {"x": [0.0, 1.0], "y": [1.0, 2.0]},
            }
        ],
        figsize=(4.0, 3.0),
        dpi=100,
        background="#FFFFFF",
        render_object=render_scatter,
        apply_axes_style=lambda ax: None,
    )

    assert fig is not None
    scatter_artist = artist_map["scatter-a"][0]
    assert adapter.object_id_for_artist(scatter_artist) == "scatter-a"
    assert scatter_artist.get_pickradius() == pytest.approx(10.0)


def test_figure_render_adapter_gives_selected_scatter_artists_a_visible_outline():
    adapter = FigureRenderAdapter()

    def render_scatter(ax, obj, _index):
        return ax.scatter(
            obj["data"]["x"],
            obj["data"]["y"],
            label=obj.get("name", "Scatter"),
            color=obj.get("style", {}).get("color", "#0072B2"),
        )

    fig, artist_map = adapter.render_document(
        document={},
        objects=[
            {
                "id": "scatter-a",
                "type": "plot_series",
                "name": "Observed",
                "data": {"x": [0.0, 1.0], "y": [1.0, 2.0]},
                "style": {"color": "#0072B2"},
            },
            {
                "id": "scatter-b",
                "type": "plot_series",
                "name": "Reference",
                "data": {"x": [0.0, 1.0], "y": [2.0, 1.0]},
                "style": {"color": "#009E73"},
            },
        ],
        figsize=(4.0, 3.0),
        dpi=100,
        background="#FFFFFF",
        render_object=render_scatter,
        apply_axes_style=lambda ax: None,
        selected_object_id="scatter-a",
    )

    assert fig is not None
    selected_artist = artist_map["scatter-a"][0]
    other_artist = artist_map["scatter-b"][0]

    assert adapter.object_id_for_artist(selected_artist) == "scatter-a"
    assert selected_artist.get_linewidths()[0] == pytest.approx(2.5)
    assert tuple(selected_artist.get_edgecolor()[0]) == pytest.approx(
        mcolors.to_rgba("#D55E00")
    )
    assert other_artist.get_linewidths()[0] == pytest.approx(1.0)


def test_figure_render_adapter_markerless_line_series_selection_handles_only_show_current_point():
    adapter = FigureRenderAdapter()
    fig = Figure(figsize=(4.0, 3.0), dpi=100, facecolor="#FFFFFF")
    ax = fig.add_subplot(111)

    handle_artists = adapter.add_selection_handles(
        ax,
        {
            "id": "series-line",
            "type": "plot_series",
            "name": "Line",
            "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
            "style": {"line_width": 1.2},
        },
        selected_handle_index=1,
    )

    assert len(handle_artists) == 1
    assert handle_artists[0].get_gid() == "pn-selection-handles:series-line"
    assert handle_artists[0].get_offsets().tolist() == [[2.0, 3.0]]
    assert getattr(handle_artists[0], "_pn_handle_indices", None) == [1]


def test_figure_render_adapter_scatter_selection_handles_add_current_point_emphasis():
    adapter = FigureRenderAdapter()
    fig = Figure(figsize=(4.0, 3.0), dpi=100, facecolor="#FFFFFF")
    ax = fig.add_subplot(111)

    handle_artists = adapter.add_selection_handles(
        ax,
        {
            "id": "series-scatter",
            "type": "plot_series",
            "chart_kind": "scatter",
            "name": "Scatter",
            "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
            "style": {"marker_size": 8.0},
        },
        selected_handle_index=2,
    )

    assert len(handle_artists) == 2
    assert handle_artists[0].get_gid() == "pn-selection-handles:series-scatter"
    assert handle_artists[0].get_offsets().tolist() == [[1.0, 1.0], [2.0, 3.0], [3.0, 2.0]]
    assert getattr(handle_artists[0], "_pn_handle_indices", None) == [0, 1, 2]
    assert handle_artists[1].get_gid() == "pn-current-handle:series-scatter"
    assert handle_artists[1].get_offsets().tolist() == [[3.0, 2.0]]


def test_figure_render_adapter_adds_four_editable_rectangle_corners():
    adapter = FigureRenderAdapter()
    fig = Figure(figsize=(4.0, 3.0), dpi=100, facecolor="#FFFFFF")
    ax = fig.add_subplot(111)

    handle_artists = adapter.add_selection_handles(
        ax,
        {
            "id": "region",
            "type": "rectangle",
            "x": 1.0,
            "y": 2.0,
            "width": 3.0,
            "height": 4.0,
        },
    )

    assert len(handle_artists) == 1
    assert handle_artists[0].get_gid() == "pn-selection-handles:region"
    assert handle_artists[0].get_offsets().tolist() == [
        [1.0, 2.0],
        [4.0, 2.0],
        [4.0, 6.0],
        [1.0, 6.0],
    ]
    assert getattr(handle_artists[0], "_pn_handle_indices", None) == [0, 1, 2, 3]


def test_figure_render_adapter_adds_rectangle_handles_from_bounds_geometry():
    adapter = FigureRenderAdapter()
    fig = Figure(figsize=(4.0, 3.0), dpi=100, facecolor="#FFFFFF")
    ax = fig.add_subplot(111)

    handle_artists = adapter.add_selection_handles(
        ax,
        {
            "id": "region",
            "type": "rectangle",
            "bounds": {"x": 1.0, "y": 2.0, "width": 3.0, "height": 4.0},
        },
    )

    assert handle_artists[0].get_offsets().tolist() == [
        [1.0, 2.0],
        [4.0, 2.0],
        [4.0, 6.0],
        [1.0, 6.0],
    ]


def test_figure_render_adapter_adds_text_box_handles_from_persisted_geometry():
    adapter = FigureRenderAdapter()
    fig = Figure(figsize=(4.0, 3.0), dpi=100, facecolor="#FFFFFF")
    ax = fig.add_subplot(111)

    handle_artists = adapter.add_selection_handles(
        ax,
        {
            "id": "text-box",
            "type": "text",
            "x": 1.0,
            "y": 2.0,
            "width": 3.0,
            "height": 4.0,
        },
    )

    assert len(handle_artists) == 1
    assert handle_artists[0].get_offsets().tolist() == [
        [1.0, 2.0],
        [4.0, 2.0],
        [4.0, 6.0],
        [1.0, 6.0],
    ]
    assert getattr(handle_artists[0], "_pn_handle_indices", None) == [0, 1, 2, 3]


def test_figure_render_adapter_highlights_selected_image_grid_frame_and_title():
    adapter = FigureRenderAdapter()

    def render_image_grid(ax, obj, _index):
        image_artist = ax.imshow([[1.0, 2.0], [3.0, 4.0]])
        title_artist = ax.set_title(obj.get("name", "Grid"))
        return [image_artist, ax.patch, title_artist]

    fig, artist_map = adapter.render_document(
        document={},
        objects=[
            {
                "id": "grid-a",
                "type": "plot_series",
                "chart_kind": "image_grid",
                "name": "25",
            }
        ],
        figsize=(4.0, 3.0),
        dpi=100,
        background="#FFFFFF",
        render_object=render_image_grid,
        apply_axes_style=lambda ax: None,
        selected_object_id="grid-a",
    )

    assert fig is not None
    frame_artist = artist_map["grid-a"][1]
    title_artist = artist_map["grid-a"][2]

    assert tuple(frame_artist.get_edgecolor()) == pytest.approx(
        mcolors.to_rgba("#D55E00")
    )
    assert frame_artist.get_linewidth() == pytest.approx(2.0)
    assert title_artist.get_color() == "#D55E00"


def test_figure_render_adapter_returns_overlapping_pick_candidates_front_to_back():
    adapter = FigureRenderAdapter()
    objects = [
        {
            "id": "series-back",
            "type": "plot_series",
            "name": "Back",
            "z_index": 0,
            "data": {"x": [0.0, 1.0], "y": [1.0, 2.0]},
            "style": {"line_width": 6.0},
        },
        {
            "id": "series-front",
            "type": "plot_series",
            "name": "Front",
            "z_index": 1,
            "data": {"x": [0.0, 1.0], "y": [1.0, 2.0]},
            "style": {"line_width": 6.0},
        },
    ]

    fig, artist_map = adapter.render_document(
        document={},
        objects=objects,
        figsize=(4.0, 3.0),
        dpi=100,
        background="#FFFFFF",
        render_object=_render_object,
        apply_axes_style=lambda ax: None,
    )

    assert fig is not None
    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    ax = fig.axes[0]
    back_artist = artist_map["series-back"][0]
    xpix, ypix = ax.transData.transform((0.5, 1.5))
    mouseevent = MouseEvent("button_press_event", canvas, xpix, ypix)
    mouseevent.inaxes = ax

    assert adapter.object_ids_for_pick_event(
        SimpleNamespace(artist=back_artist, mouseevent=mouseevent)
    ) == ["series-front", "series-back"]


def test_figure_render_adapter_treats_near_edge_bar_patch_as_hover_candidate():
    adapter = FigureRenderAdapter()

    def render_bar(ax, obj, _index):
        return ax.bar(
            obj["data"]["x"],
            obj["data"]["y"],
            width=obj.get("style", {}).get("width", 0.8),
            color=obj.get("style", {}).get("color", "#0072B2"),
            alpha=obj.get("style", {}).get("alpha", 0.9),
        )

    fig, artist_map = adapter.render_document(
        document={},
        objects=[
            {
                "id": "series-bar",
                "type": "plot_series",
                "chart_kind": "bar",
                "name": "Bar Series",
                "data": {"x": [1.0], "y": [3.0]},
                "style": {"width": 0.8, "color": "#0072B2", "alpha": 0.9},
            }
        ],
        figsize=(4.0, 3.0),
        dpi=100,
        background="#FFFFFF",
        render_object=render_bar,
        apply_axes_style=lambda ax: (ax.set_xlim(0.0, 2.0), ax.set_ylim(0.0, 4.0)),
    )

    assert fig is not None
    assert artist_map["series-bar"]

    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    ax = fig.axes[0]
    edge_xpix, edge_ypix = ax.transData.transform((1.4, 1.5))
    mouseevent = MouseEvent("motion_notify_event", canvas, edge_xpix + 6.0, edge_ypix)
    mouseevent.inaxes = ax

    assert adapter.object_ids_for_mouseevent(mouseevent) == ["series-bar"]


def test_figure_render_adapter_treats_near_edge_image_artist_as_hover_candidate():
    adapter = FigureRenderAdapter()

    def render_image_grid(ax, obj, _index):
        return ax.imshow(
            [[1.0, 2.0], [3.0, 4.0]],
            extent=(0.0, 1.0, 0.0, 1.0),
            origin="lower",
            cmap=obj.get("style", {}).get("colormap", "viridis"),
        )

    fig, artist_map = adapter.render_document(
        document={},
        objects=[
            {
                "id": "series-grid",
                "type": "plot_series",
                "chart_kind": "image_grid",
                "name": "Grid",
                "style": {"colormap": "inferno"},
            }
        ],
        figsize=(4.0, 3.0),
        dpi=100,
        background="#FFFFFF",
        render_object=render_image_grid,
        apply_axes_style=lambda ax: (ax.set_xlim(0.0, 1.5), ax.set_ylim(0.0, 1.5)),
    )

    assert fig is not None
    assert artist_map["series-grid"]

    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    ax = fig.axes[0]
    edge_xpix, edge_ypix = ax.transData.transform((1.0, 0.5))
    mouseevent = MouseEvent("motion_notify_event", canvas, edge_xpix + 5.0, edge_ypix)
    mouseevent.inaxes = ax

    assert adapter.object_ids_for_mouseevent(mouseevent) == ["series-grid"]


def test_figure_render_adapter_returns_none_when_visible_objects_do_not_render_any_artists():
    adapter = FigureRenderAdapter()
    apply_calls = []

    fig, artist_map = adapter.render_document(
        document={},
        objects=[{"id": "series-a", "type": "plot_series", "name": "Observed"}],
        figsize=(4.0, 3.0),
        dpi=100,
        background="#FFFFFF",
        render_object=lambda ax, obj, index: [],
        apply_axes_style=lambda ax: apply_calls.append("called"),
    )

    assert fig is None
    assert artist_map == {}
    assert apply_calls == []


def test_figure_render_adapter_handles_empty_object_list_without_artist_mappings():
    adapter = FigureRenderAdapter()
    apply_calls = []

    fig, artist_map = adapter.render_document(
        document={},
        objects=[],
        figsize=(4.0, 3.0),
        dpi=100,
        background="#FFFFFF",
        render_object=_render_object,
        apply_axes_style=lambda ax: apply_calls.append("called"),
    )

    assert fig is not None
    assert artist_map == {}
    assert apply_calls == ["called"]


def test_figure_render_adapter_adds_transient_line_selection_frame_from_endpoints():
    adapter = FigureRenderAdapter()
    fig = Figure(figsize=(4.0, 3.0), dpi=100, facecolor="#FFFFFF")
    ax = fig.add_subplot(111)
    persisted = ax.plot([0.0, 4.0], [1.0, 3.0])[0]
    adapter.register_artists("line-1", [persisted])

    frames = adapter.add_selection_frame(
        ax,
        {"id": "line-1", "type": "line", "x1": 4.0, "y1": 3.0, "x2": 1.0, "y2": 1.0},
    )

    assert len(frames) == 1
    frame = frames[0]
    assert isinstance(frame, Line2D)
    assert frame.get_gid() == "pn-selection-frame:line-1"
    assert list(frame.get_xdata()) == [1.0, 4.0, 4.0, 1.0, 1.0]
    assert list(frame.get_ydata()) == [1.0, 1.0, 3.0, 3.0, 1.0]
    assert frame.get_color() == "#0072B2"
    assert frame.get_linestyle() == "--"
    assert frame.get_fillstyle() == "full"
    assert frame.get_zorder() > 1000
    assert adapter.object_id_for_artist(frame) == ""
    assert adapter.artists_for_object_id("line-1") == [persisted]


def test_figure_render_adapter_adds_transient_curve_selection_frame_from_control_extent():
    adapter = FigureRenderAdapter()
    fig = Figure(figsize=(4.0, 3.0), dpi=100, facecolor="#FFFFFF")
    ax = fig.add_subplot(111)

    frames = adapter.add_selection_frame(
        ax,
        {
            "id": "curve-1",
            "type": "curve",
            "x1": 2.0,
            "y1": 4.0,
            "x2": 8.0,
            "y2": 6.0,
            "control_x": 5.0,
            "control_y": 12.0,
        },
    )

    assert len(frames) == 1
    frame = frames[0]
    assert isinstance(frame, Line2D)
    assert list(frame.get_xdata()) == [2.0, 8.0, 8.0, 2.0, 2.0]
    assert list(frame.get_ydata()) == [4.0, 4.0, 12.0, 12.0, 4.0]
    assert frame.get_gid() == "pn-selection-frame:curve-1"
    assert frame.get_linestyle() == "--"
    assert frame.get_zorder() > 1000


def test_figure_render_adapter_adds_transient_rectangle_selection_frame_from_bounds():
    adapter = FigureRenderAdapter()
    fig = Figure(figsize=(4.0, 3.0), dpi=100, facecolor="#FFFFFF")
    ax = fig.add_subplot(111)

    frames = adapter.add_selection_frame(
        ax,
        {
            "id": "rect-1",
            "type": "rectangle",
            "bounds": {"x": 1.5, "y": 2.0, "width": 3.0, "height": 4.5},
        },
    )

    assert len(frames) == 1
    frame = frames[0]
    assert isinstance(frame, Rectangle)
    assert frame.get_x() == pytest.approx(1.5)
    assert frame.get_y() == pytest.approx(2.0)
    assert frame.get_width() == pytest.approx(3.0)
    assert frame.get_height() == pytest.approx(4.5)
    assert frame.get_gid() == "pn-selection-frame:rect-1"
    assert frame.get_edgecolor() == pytest.approx(mcolors.to_rgba("#0072B2"))
    assert frame.get_linestyle() == "--"
    assert frame.get_fill() is False
    assert frame.get_zorder() > 1000
    assert adapter.object_id_for_artist(frame) == ""
    assert adapter.artists_for_object_id("rect-1") == []


def test_figure_render_adapter_adds_transient_text_selection_frame_from_fallback_bounds():
    adapter = FigureRenderAdapter()
    fig = Figure(figsize=(4.0, 3.0), dpi=100, facecolor="#FFFFFF")
    ax = fig.add_subplot(111)

    frames = adapter.add_selection_frame(
        ax,
        {
            "id": "text-1",
            "type": "text",
            "x": 3.0,
            "y": 4.0,
            "width": 2.5,
            "height": 1.25,
        },
    )

    assert len(frames) == 1
    frame = frames[0]
    assert isinstance(frame, Rectangle)
    assert frame.get_x() == pytest.approx(3.0)
    assert frame.get_y() == pytest.approx(4.0)
    assert frame.get_width() == pytest.approx(2.5)
    assert frame.get_height() == pytest.approx(1.25)
    assert frame.get_gid() == "pn-selection-frame:text-1"
    assert frame.get_linestyle() == "--"
    assert frame.get_fill() is False
    assert adapter.object_id_for_artist(frame) == ""


def test_figure_render_adapter_uses_rendered_text_extent_for_selection_frame():
    adapter = FigureRenderAdapter()
    fig = Figure(figsize=(4.0, 3.0), dpi=100, facecolor="#FFFFFF")
    ax = fig.add_subplot(111)
    text_artist = ax.text(2.0, 3.0, "Peak", fontsize=18)
    adapter.register_artists("text-rendered", [text_artist])
    FigureCanvasAgg(fig).draw()

    frame = adapter.add_selection_frame(
        ax,
        {"id": "text-rendered", "type": "text", "x": 2.0, "y": 3.0},
    )[0]

    text_bbox = text_artist.get_window_extent(fig.canvas.get_renderer())
    data_bbox = ax.transData.inverted().transform_bbox(text_bbox)
    assert frame.get_x() == pytest.approx(data_bbox.x0)
    assert frame.get_y() == pytest.approx(data_bbox.y0)
    assert frame.get_width() == pytest.approx(data_bbox.width)
    assert frame.get_height() == pytest.approx(data_bbox.height)


def test_figure_render_adapter_adds_transient_arrow_selection_frame_from_endpoints():
    adapter = FigureRenderAdapter()
    fig = Figure(figsize=(4.0, 3.0), dpi=100, facecolor="#FFFFFF")
    ax = fig.add_subplot(111)

    frames = adapter.add_selection_frame(
        ax,
        {"id": "arrow-1", "type": "arrow", "x1": 4.0, "y1": 3.0, "x2": 1.0, "y2": 1.0},
    )

    assert len(frames) == 1
    assert list(frames[0].get_xdata()) == [1.0, 4.0, 4.0, 1.0, 1.0]
    assert list(frames[0].get_ydata()) == [1.0, 1.0, 3.0, 3.0, 1.0]
    assert frames[0].get_gid() == "pn-selection-frame:arrow-1"


@pytest.mark.parametrize(
    "figure_object",
    [
        {"id": "missing-line", "type": "line", "x1": 1.0, "y1": 2.0},
        {"id": "missing-curve", "type": "curve", "x1": 1.0, "y1": 2.0, "x2": 3.0, "y2": 4.0},
        {"id": "missing-rect", "type": "rectangle", "bounds": {"x": 1.0, "y": 2.0}},
        {"id": "missing-text", "type": "text", "x": 1.0, "y": 2.0, "width": 3.0},
    ],
)
def test_figure_render_adapter_skips_selection_frame_for_invalid_geometry(figure_object):
    adapter = FigureRenderAdapter()
    fig = Figure(figsize=(4.0, 3.0), dpi=100, facecolor="#FFFFFF")
    ax = fig.add_subplot(111)

    assert adapter.add_selection_frame(ax, figure_object) == []


@pytest.mark.parametrize(
    "figure_object",
    [
        {
            "id": "nonfinite-line",
            "type": "line",
            "x1": math.nan,
            "y1": 2.0,
            "x2": 3.0,
            "y2": 4.0,
        },
        {
            "id": "nonfinite-curve",
            "type": "curve",
            "x1": 1.0,
            "y1": 2.0,
            "x2": 3.0,
            "y2": 4.0,
            "control_x": 2.0,
            "control_y": math.inf,
        },
        {
            "id": "nonfinite-rectangle",
            "type": "rectangle",
            "bounds": {"x": 1.0, "y": 2.0, "width": -math.inf, "height": 4.0},
        },
        {
            "id": "nonfinite-text",
            "type": "text",
            "x": 1.0,
            "y": -math.inf,
            "width": 3.0,
            "height": 2.0,
        },
    ],
)
def test_figure_render_adapter_skips_selection_frame_for_nonfinite_geometry(figure_object):
    adapter = FigureRenderAdapter()
    fig = Figure(figsize=(4.0, 3.0), dpi=100, facecolor="#FFFFFF")
    ax = fig.add_subplot(111)

    assert adapter.add_selection_frame(ax, figure_object) == []
