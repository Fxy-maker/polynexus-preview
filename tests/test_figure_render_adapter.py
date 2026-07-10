from types import SimpleNamespace

from matplotlib import colors as mcolors
from matplotlib.backend_bases import MouseEvent
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
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
