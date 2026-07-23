from polynexus.core.figure_object_store import FigureObjectStore


def _sample_document():
    return {
        "objects": [
            {
                "id": "background",
                "type": "image_background",
                "name": "Background",
                "visible": True,
            },
            {
                "id": "series-a",
                "type": "plot_series",
                "name": "Observed",
                "style": {"color": "#111111", "alpha": 0.4},
                "visible": True,
            },
            {
                "id": "series-b",
                "type": "plot_series",
                "name": "Reference",
                "visible": False,
            },
            {
                "id": "line-deleted",
                "type": "line",
                "name": "Deleted line",
                "deleted": True,
                "visible": False,
            },
        ]
    }


def test_figure_object_store_filters_background_and_deleted_objects_from_active_lookup():
    document = _sample_document()
    store = FigureObjectStore(document)

    assert [obj["id"] for obj in store.objects()] == [
        "background",
        "series-a",
        "series-b",
        "line-deleted",
    ]
    assert [obj["id"] for obj in store.visible_objects()] == ["series-a", "series-b"]
    assert store.get("background") is None
    assert store.get("line-deleted") is None
    assert store.get("series-b") is document["objects"][2]
    assert store.get_including_deleted("line-deleted") is document["objects"][3]
    assert store.get_including_deleted("missing") is None


def test_figure_object_store_renames_objects_and_updates_style_in_place():
    document = _sample_document()
    store = FigureObjectStore(document)
    updates = {
        "color": "#D55E00",
        "alpha": None,
        "label_style": {"weight": "bold"},
    }

    assert store.rename("series-a", "  Edited Spectrum  ") is True
    assert document["objects"][1]["name"] == "Edited Spectrum"
    assert store.rename("series-a", "Edited Spectrum") is False
    assert store.rename("series-a", "   ") is False
    assert store.rename("missing", "Anything") is False

    assert store.update_style("series-a", updates) is True
    updates["label_style"]["weight"] = "light"

    assert document["objects"][1]["style"]["color"] == "#D55E00"
    assert document["objects"][1]["style"]["alpha"] == 0.4
    assert document["objects"][1]["style"]["label_style"] == {"weight": "bold"}
    assert store.update_style("series-a", {"color": "#D55E00"}) is False
    assert store.update_style("missing", {"color": "#000000"}) is False


def test_figure_object_store_toggles_visibility_and_supports_soft_delete_restore():
    document = _sample_document()
    store = FigureObjectStore(document)

    assert store.set_visible("series-a", False) is True
    assert document["objects"][1]["visible"] is False
    assert store.set_visible("series-a", False) is False

    assert store.soft_delete("series-a") is True
    assert document["objects"][1]["deleted"] is True
    assert document["objects"][1]["visible"] is False
    assert store.get("series-a") is None

    assert store.restore("series-a") is True
    assert document["objects"][1]["deleted"] is False
    assert document["objects"][1]["visible"] is True
    assert store.get("series-a") is document["objects"][1]

    assert store.soft_delete("missing") is False
    assert store.restore("missing") is False


def test_figure_object_store_updates_geometry_in_place():
    document = {
        "objects": [
            {
                "id": "line-qstar",
                "type": "line",
                "name": "q*",
                "x1": 1.5,
                "y1": 0.25,
                "x2": 2.5,
                "y2": 3.75,
            }
        ]
    }
    store = FigureObjectStore(document)

    assert store.update_geometry(
        "line-qstar",
        {"x1": 1.75, "y1": 0.5, "x2": 2.75, "y2": 4.25},
    ) is True
    assert document["objects"][0]["x1"] == 1.75
    assert document["objects"][0]["y1"] == 0.5
    assert document["objects"][0]["x2"] == 2.75
    assert document["objects"][0]["y2"] == 4.25
    assert store.update_geometry("line-qstar", {"x1": 1.75}) is False
    assert store.update_geometry("missing", {"x1": 0.0}) is False


def test_figure_object_store_ensures_compact_legend_for_named_visible_series():
    document = {
        "objects": [
            {
                "id": "background",
                "type": "image_background",
                "name": "Background",
                "visible": True,
            },
            {
                "id": "series-a",
                "type": "plot_series",
                "name": "Observed",
                "visible": True,
            },
            {
                "id": "series-b",
                "type": "plot_series",
                "name": "Reference",
                "visible": True,
            },
        ]
    }
    store = FigureObjectStore(document)

    assert store.ensure_legend_object() is True
    assert document["objects"][-1] == {
        "id": "legend",
        "type": "legend",
        "name": "Legend",
        "visible": True,
        "locked": False,
        "z_index": 3,
        "style": {"loc": "upper right", "ncol": 1},
    }
    assert store.ensure_legend_object() is False


def test_figure_object_store_skips_legend_for_one_named_visible_series():
    document = {
        "objects": [
            {
                "id": "background",
                "type": "image_background",
                "name": "Background",
                "visible": True,
            },
            {
                "id": "series-a",
                "type": "plot_series",
                "name": "Observed",
                "visible": True,
            }
        ]
    }

    assert FigureObjectStore(document).ensure_legend_object() is False
    assert [item["id"] for item in document["objects"]] == ["background", "series-a"]


def test_figure_object_store_preserves_existing_hidden_legend():
    document = {
        "objects": [
            {
                "id": "series-a",
                "type": "plot_series",
                "name": "Observed",
                "visible": True,
            },
            {
                "id": "series-b",
                "type": "plot_series",
                "name": "Reference",
                "visible": True,
            },
            {
                "id": "legend",
                "type": "legend",
                "name": "Legend",
                "visible": False,
                "style": {"loc": "lower left"},
            },
        ]
    }

    assert FigureObjectStore(document).ensure_legend_object() is False
    assert document["objects"][-1]["visible"] is False
    assert document["objects"][-1]["style"] == {"loc": "lower left"}


def test_figure_object_store_uses_panel_id_without_provider_legend_gate():
    document = {
        "layout": {
            "panels": [
                {
                    "panel_id": "main",
                    "show_legend": False,
                }
            ]
        },
        "objects": [
            {
                "id": "series-a",
                "type": "plot_series",
                "name": "Observed",
                "panel_id": "main",
            },
            {
                "id": "series-b",
                "type": "plot_series",
                "name": "Reference",
                "panel_id": "main",
            },
        ],
    }
    store = FigureObjectStore(document)

    assert store.ensure_legend_object() is True
    assert document["objects"][-1]["id"] == "legend"
    assert document["objects"][-1]["panel_id"] == "main"


def test_figure_object_store_moves_selected_object_without_crossing_legend():
    document = {
        "objects": [
            {
                "id": "background",
                "type": "image_background",
                "name": "Background",
                "visible": True,
                "z_index": 0,
            },
            {
                "id": "series-a",
                "type": "plot_series",
                "name": "A",
                "visible": True,
                "z_index": 1,
            },
            {
                "id": "series-b",
                "type": "plot_series",
                "name": "B",
                "visible": True,
                "z_index": 2,
            },
            {
                "id": "legend",
                "type": "legend",
                "name": "Legend",
                "visible": True,
                "z_index": 3,
            },
        ]
    }
    store = FigureObjectStore(document)

    assert store.move("series-a", to_front=True) is True
    assert [obj["id"] for obj in document["objects"]] == [
        "background",
        "series-b",
        "series-a",
        "legend",
    ]
    assert [obj["z_index"] for obj in document["objects"]] == [0, 1, 2, 3]

    assert store.move("series-a", to_front=True) is False
    assert store.move("series-a", to_front=False) is True
    assert [obj["id"] for obj in document["objects"]] == [
        "background",
        "series-a",
        "series-b",
        "legend",
    ]
    assert [obj["z_index"] for obj in document["objects"]] == [0, 1, 2, 3]

    assert store.move("missing", to_front=True) is False


def test_figure_object_store_replaces_object_from_snapshot():
    document = {
        "objects": [
            {
                "id": "series-line",
                "type": "plot_series",
                "name": "Line",
                "data": {"x": [1.0, 2.35, 3.0], "y": [1.0, 2.45, 2.0]},
                "style": {"line_width": 1.2},
            }
        ]
    }
    store = FigureObjectStore(document)
    snapshot = {
        "id": "series-line",
        "type": "plot_series",
        "name": "Line",
        "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
        "style": {"line_width": 1.2},
    }

    assert store.replace("series-line", snapshot) is True
    snapshot["data"]["x"][1] = 99.0

    assert document["objects"][0]["data"]["x"] == [1.0, 2.0, 3.0]
    assert document["objects"][0]["data"]["y"] == [1.0, 3.0, 2.0]
    assert store.replace("missing", snapshot) is False


def test_figure_object_store_sets_plot_series_inline_data_without_touching_source_reference():
    document = {
        "objects": [
            {
                "id": "series-marked",
                "type": "plot_series",
                "name": "Marked",
                "data_ref": "series-data",
                "x_column": "q",
                "y_column": "intensity",
                "style": {"marker": "o", "marker_size": 8.0},
            }
        ]
    }
    store = FigureObjectStore(document)
    x_values = [1.0, 2.4, 3.0]
    y_values = [1.0, 2.6, 2.0]

    assert store.set_plot_series_inline_data("series-marked", x_values, y_values) is True
    x_values[1] = 99.0
    y_values[1] = 88.0

    series = document["objects"][0]
    assert series["data_ref"] == "series-data"
    assert series["x_column"] == "q"
    assert series["y_column"] == "intensity"
    assert series["data"] == {"x": [1.0, 2.4, 3.0], "y": [1.0, 2.6, 2.0]}
    assert store.set_plot_series_inline_data("series-marked", [1.0, 2.4, 3.0], [1.0, 2.6, 2.0]) is False
    assert store.set_plot_series_inline_data("missing", [1.0], [2.0]) is False
