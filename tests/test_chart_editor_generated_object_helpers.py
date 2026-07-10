from __future__ import annotations

from polynexus.gui.chart_editor_generated_object_helpers import (
    generated_column_values,
    generated_object_capabilities,
    generated_object_geometry_config,
    generated_object_xy,
)


def test_generated_object_capabilities_cover_common_generated_object_types() -> None:
    legend_caps = generated_object_capabilities(
        {"type": "legend", "chart_kind": "line"},
        selected_plot_series_point_geometry=False,
    )
    assert legend_caps == {
        "renameable": False,
        "style": False,
        "deletable": False,
        "reorderable": False,
        "geometry": True,
        "line_style": False,
        "marker": False,
        "marker_size": False,
    }

    scatter_caps = generated_object_capabilities(
        {"type": "plot_series", "chart_kind": "scatter"},
        selected_plot_series_point_geometry=True,
    )
    assert scatter_caps["renameable"] is True
    assert scatter_caps["geometry"] is True
    assert scatter_caps["line_style"] is False
    assert scatter_caps["marker"] is True
    assert scatter_caps["marker_size"] is True

    line_caps = generated_object_capabilities(
        {"type": "line", "chart_kind": "line"},
        selected_plot_series_point_geometry=False,
    )
    assert line_caps["geometry"] is True
    assert line_caps["line_style"] is True


def test_generated_object_geometry_config_handles_legend_plot_series_and_line() -> None:
    assert generated_object_geometry_config(
        {"type": "legend"},
        legend_anchor=None,
        point_index=None,
        inline_data=None,
    ) == {
        "mode": "box",
        "enabled": (False, False, False, False),
        "values": (0.0, 0.0, 0.0, 0.0),
    }

    assert generated_object_geometry_config(
        {"type": "legend"},
        legend_anchor=(0.25, 0.75),
        point_index=None,
        inline_data=None,
    ) == {
        "mode": "point",
        "enabled": (True, True, False, False),
        "values": (0.25, 0.75, 0.0, 0.0),
    }

    assert generated_object_geometry_config(
        {"type": "plot_series"},
        legend_anchor=None,
        point_index=1,
        inline_data={"x": [1, "2.5"], "y": [3, 4]},
    ) == {
        "mode": "point",
        "enabled": (True, True, False, False),
        "values": (2.5, 4.0, 0.0, 0.0),
    }

    assert generated_object_geometry_config(
        {"type": "line", "x1": "1.5", "x2": "3.0", "y1": "2", "y2": "4.25"},
        legend_anchor=None,
        point_index=None,
        inline_data=None,
    ) == {
        "mode": "segment",
        "enabled": (True, True, True, True),
        "values": (1.5, 2.0, 3.0, 4.25),
    }


def test_generated_object_xy_and_columns_use_inline_data_before_source_columns() -> None:
    data_sources = {"source-1": {"x": [10, 20], "y": [30, 40]}}
    assert generated_object_xy(
        {"data": {"x": [1, 2], "y": [3, 4]}},
        data_sources,
    ) == ([1, 2], [3, 4])

    assert generated_object_xy(
        {"data_ref": "source-1", "x_column": "x", "y_column": "y"},
        data_sources,
    ) == ([10, 20], [30, 40])

    assert generated_column_values(
        {"data_ref": "source-1", "x_column": "x"},
        data_sources,
        "x_column",
    ) == [10, 20]
