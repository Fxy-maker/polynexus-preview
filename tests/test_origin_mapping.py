from polynexus.origin.mapping import map_figure_document


def test_mapping_preserves_series_columns_and_basic_style():
    document = {
        "figure_id": "saxs-1",
        "style": {"title": "Intensity", "xlabel": "q", "ylabel": "I(q)"},
        "data_sources": [{"id": "source-1", "path": "data/source-1.csv"}],
        "objects": [
            {
                "id": "series-1",
                "type": "plot_series",
                "name": "sample",
                "data_ref": "source-1",
                "x_column": "q",
                "y_column": "intensity",
                "style": {"color": "#336699", "line_width": 1.5},
            }
        ],
    }

    mapped = map_figure_document(document)

    assert mapped.title == "Intensity"
    assert mapped.sources[0].source_id == "source-1"
    assert mapped.plots[0].x_column == "q"
    assert mapped.plots[0].y_column == "intensity"
    assert mapped.plots[0].style["color"] == "#336699"
    assert mapped.warnings == ()


def test_mapping_reports_unsupported_objects_without_dropping_the_document():
    mapped = map_figure_document({"objects": [{"type": "image_background"}]})

    assert mapped.warnings
    assert "image_background" in mapped.warnings[0]


def test_mapping_preserves_band_columns_and_simple_annotations():
    mapped = map_figure_document(
        {
            "objects": [
                {
                    "id": "band",
                    "type": "plot_series",
                    "data_ref": "source",
                    "x_column": "x",
                    "lower_y_column": "lower",
                    "upper_y_column": "upper",
                },
                {"id": "label", "type": "text", "text": "Peak"},
            ]
        }
    )

    assert mapped.plots[0].lower_y_column == "lower"
    assert mapped.plots[0].upper_y_column == "upper"
    assert mapped.annotations[0].object_type == "text"
