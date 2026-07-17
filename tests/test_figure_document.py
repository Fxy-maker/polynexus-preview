"""Tests for object-level figure document state."""

import json
import math

from polynexus.core.figure_document import (
    annotation_to_figure_object,
    create_generated_figure_document,
    create_static_figure_document,
    figure_document_path,
    load_figure_document,
    normalize_figure_document,
    save_generated_figure_document,
    save_figure_document,
)
from polynexus.core.figure_objects import normalize_figure_object
from polynexus.core.plot_edits import (
    load_figure_document_path,
    save_figure_document_path,
)


def test_load_figure_document_accepts_direct_document_path(tmp_path):
    document_path = tmp_path / "figure.pnfig.json"
    document_path.write_text(
        json.dumps({"version": 2, "figure_id": "direct", "mode": "object"}),
        encoding="utf-8",
    )

    document = load_figure_document(str(document_path))

    assert document["figure_id"] == "direct"
    assert document["mode"] == "object"


def test_normalize_document_preserves_explicit_run_relative_data_path():
    document = normalize_figure_document(
        {
            "figure_id": "ir.frame.spectrum.001",
            "mode": "object",
            "data_sources": [
                {
                    "id": "spectrum-data",
                    "kind": "csv",
                    "path": "figures/ir.frame.spectrum.001/data/spectrum-data.csv",
                    "path_kind": "run_relative",
                }
            ],
        }
    )

    assert document["data_sources"][0]["path"] == (
        "figures/ir.frame.spectrum.001/data/spectrum-data.csv"
    )


def test_static_background_document_round_trips(tmp_path):
    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    figure_path.write_bytes(b"fake")

    document = create_static_figure_document(
        str(figure_path),
        asset_spec={"figure_id": "source", "width_px": 80, "height_px": 40},
        style={"title": "Edited"},
        annotations=[
            {
                "id": "ann-1",
                "type": "text",
                "text": "Peak",
                "x": 0.25,
                "y": 0.5,
            }
        ],
    )

    path = save_figure_document(str(figure_path), document)
    loaded = load_figure_document(str(figure_path))

    assert figure_document_path(str(figure_path)) == figure_path.with_suffix(".pnfig.json")
    assert path == figure_path.with_suffix(".pnfig.json")
    assert loaded["version"] == 1
    assert loaded["figure_id"] == "source"
    assert loaded["mode"] == "static_background"
    assert loaded["canvas"]["width_px"] == 80
    assert loaded["canvas"]["height_px"] == 40
    assert loaded["style"]["title"] == "Edited"
    assert [item["type"] for item in loaded["objects"]] == ["image_background", "text"]
    assert loaded["objects"][0]["source_path"] == str(figure_path.resolve())
    assert loaded["objects"][1]["text"] == "Peak"


def test_static_annotation_is_a_layered_canonical_object():
    document = create_static_figure_document(
        "figure.png",
        annotations=[
            {
                "id": "ann-1",
                "type": "line",
                "layer_id": "layer-legacy",
                "x1": 0.1,
                "y1": 0.2,
                "x2": 0.8,
                "y2": 0.9,
                "color": "#0072B2",
                "line_width": 2.0,
            },
        ],
    )

    line = next(item for item in document["objects"] if item["id"] == "ann-1")

    assert line["layer_id"] == "layer-1"
    assert line["bounds"] == {"x1": 0.1, "y1": 0.2, "x2": 0.8, "y2": 0.9}
    assert line["style"]["color"] == "#0072B2"
    assert document["layers"][0]["object_ids"] == ["background", "ann-1"]
    assert document["objects"][0]["layer_id"] == "layer-1"


def test_normalize_figure_object_preserves_canonical_fields_and_unknown_fields():
    payload = {
        "id": "future-1",
        "type": "future_artist",
        "layer_id": "layer-legacy",
        "bounds": {"x": 0.1, "custom_axis": "x"},
        "style": {"future_stroke": {"width": 3}},
        "future_payload": {"x": 1},
    }

    normalized = normalize_figure_object(payload)

    assert normalized["layer_id"] == "layer-1"
    assert normalized["bounds"] == {"x": 0.1, "custom_axis": "x"}
    assert normalized["style"] == {"future_stroke": {"width": 3}}
    assert normalized["future_payload"] == {"x": 1}


def test_normalization_is_idempotent_and_preserves_future_fields():
    payload = {
        "version": 1,
        "objects": [
            {
                "id": "future-1",
                "type": "future_artist",
                "future_payload": {"x": 1},
            }
        ],
    }

    once = normalize_figure_document(payload)

    assert normalize_figure_document(once) == once
    assert once["objects"][0]["future_payload"] == {"x": 1}


def test_annotation_to_figure_object_preserves_known_annotation_fields():
    annotation = {
        "id": "ann-2",
        "type": "arrow",
        "x1": 0.1,
        "y1": 0.2,
        "x2": 0.3,
        "y2": 0.4,
        "color": "#D55E00",
        "line_width": 2.5,
    }

    obj = annotation_to_figure_object(annotation)

    assert obj["id"] == "ann-2"
    assert obj["type"] == "arrow"
    assert obj["name"] == "Arrow"
    assert obj["x1"] == 0.1
    assert obj["y2"] == 0.4
    assert obj["style"]["color"] == "#D55E00"
    assert obj["style"]["line_width"] == 2.5


def test_text_annotation_bounds_include_all_convertible_geometry_and_legacy_values():
    annotation = {
        "id": "ann-text-bounds",
        "type": "text",
        "x": "0.1",
        "y": "0.2",
        "width": "0.4",
        "height": "0.5",
    }

    obj = annotation_to_figure_object(annotation)

    assert obj["bounds"] == {"x": 0.1, "y": 0.2, "width": 0.4, "height": 0.5}
    assert obj["x"] == "0.1"
    assert obj["y"] == "0.2"
    assert obj["width"] == "0.4"
    assert obj["height"] == "0.5"


def test_line_annotation_bounds_include_all_geometry_and_legacy_values():
    annotation = {
        "id": "ann-line-bounds",
        "type": "line",
        "x": "0.1",
        "y": "0.2",
        "width": "0.3",
        "height": "0.4",
        "x1": "0.5",
        "y1": "0.6",
        "x2": "0.7",
        "y2": "0.8",
    }

    obj = annotation_to_figure_object(annotation)

    assert obj["bounds"] == {
        "x": 0.1,
        "y": 0.2,
        "width": 0.3,
        "height": 0.4,
        "x1": 0.5,
        "y1": 0.6,
        "x2": 0.7,
        "y2": 0.8,
    }
    assert obj["x"] == "0.1"
    assert obj["width"] == "0.3"
    assert obj["x1"] == "0.5"
    assert obj["y2"] == "0.8"


def test_annotation_bounds_skip_nonconvertible_geometry_and_empty_types():
    invalid = annotation_to_figure_object(
        {
            "id": "ann-invalid-bounds",
            "type": "line",
            "x": "not-a-number",
            "y1": None,
            "x2": "0.8",
        }
    )
    empty = annotation_to_figure_object(
        {"id": "ann-future", "type": "future_artist", "future_payload": {"x": 1}}
    )

    assert invalid["bounds"] == {"x2": 0.8}
    assert empty["bounds"] == {}


def test_annotation_bounds_skip_nonfinite_geometry():
    obj = annotation_to_figure_object(
        {
            "id": "ann-nonfinite-bounds",
            "type": "rectangle",
            "x": float("nan"),
            "y": float("inf"),
            "width": "-Infinity",
            "height": "0.5",
        }
    )

    assert obj["bounds"] == {"height": 0.5}


def test_normalize_figure_object_migrates_legacy_geometry_without_overwriting_bounds():
    payload = {
        "id": "legacy-geometry",
        "type": "rectangle",
        "x": "0.1",
        "y": "0.2",
        "width": "0.3",
        "height": "0.4",
        "bounds": {"x": 0.9, "custom_axis": "x"},
    }

    normalized = normalize_figure_object(payload)

    assert normalized["bounds"] == {
        "x": 0.9,
        "y": 0.2,
        "width": 0.3,
        "height": 0.4,
        "custom_axis": "x",
    }
    assert normalized["x"] == "0.1"
    assert normalized["y"] == "0.2"


def test_normalize_figure_object_replaces_nonfinite_bounds_with_finite_legacy_values():
    payload = {
        "id": "invalid-canonical-geometry",
        "type": "rectangle",
        "x": "0.1",
        "y": 0.2,
        "width": "0.3",
        "height": 0.4,
        "bounds": {
            "x": float("nan"),
            "y": float("inf"),
            "width": "-Infinity",
            "height": "not-a-number",
            "custom_axis": "x",
        },
    }

    normalized = normalize_figure_object(payload)

    assert normalized["bounds"] == {
        "x": 0.1,
        "y": 0.2,
        "width": 0.3,
        "height": 0.4,
        "custom_axis": "x",
    }


def test_normalize_figure_object_rejects_nonfinite_canonical_bounds_without_mutating_payload():
    payload = {
        "id": "bad-bounds",
        "type": "line",
        "x1": 0.1,
        "y1": 0.2,
        "bounds": {"x1": float("nan"), "y1": float("inf"), "custom": "keep"},
    }

    normalized = normalize_figure_object(payload)

    assert normalized["bounds"] == {
        "x1": 0.1,
        "y1": 0.2,
        "custom": "keep",
    }
    assert math.isnan(payload["bounds"]["x1"])
    assert math.isinf(payload["bounds"]["y1"])


def test_normalize_figure_object_drops_invalid_bounds_without_legacy_values():
    normalized = normalize_figure_object(
        {
            "id": "invalid-only-canonical-geometry",
            "type": "rectangle",
            "bounds": {
                "x": float("nan"),
                "y": float("inf"),
                "width": "not-a-number",
                "custom_axis": "x",
            },
        }
    )

    assert normalized["bounds"] == {"custom_axis": "x"}


def test_normalize_figure_object_does_not_mutate_payload():
    payload = {
        "id": "unmodified-payload",
        "type": "rectangle",
        "x": "0.1",
        "bounds": {"x": "not-a-number", "custom_axis": {"value": 1}},
    }

    normalized = normalize_figure_object(payload)

    assert payload == {
        "id": "unmodified-payload",
        "type": "rectangle",
        "x": "0.1",
        "bounds": {"x": "not-a-number", "custom_axis": {"value": 1}},
    }
    assert normalized["bounds"] is not payload["bounds"]


def test_normalize_figure_object_is_idempotent_after_rejecting_invalid_bounds():
    payload = {
        "id": "idempotent-invalid-geometry",
        "type": "rectangle",
        "x": "0.1",
        "bounds": {"x": float("nan"), "custom_axis": "x"},
    }

    normalized = normalize_figure_object(payload)

    assert normalize_figure_object(normalized) == normalized


def test_normalize_document_handles_legacy_geometry_null_lists_and_invalid_version():
    payload = {
        "version": "v1",
        "canvas": None,
        "asset_spec": None,
        "style": None,
        "layers": None,
        "objects": [
            {
                "id": "legacy-line",
                "type": "line",
                "x1": "0.1",
                "y1": "0.2",
                "x2": "0.3",
                "y2": "0.4",
                "bounds": {"x1": 0.8},
            }
        ],
        "data_sources": None,
    }

    normalized = normalize_figure_document(payload)

    assert normalized["version"] == 1
    assert normalized["canvas"] == {}
    assert normalized["asset_spec"] == {}
    assert normalized["style"] == {}
    assert normalized["layers"] == []
    assert normalized["data_sources"] == []
    assert normalized["objects"][0]["bounds"] == {
        "x1": 0.8,
        "y1": 0.2,
        "x2": 0.3,
        "y2": 0.4,
    }
    assert normalized["objects"][0]["x1"] == "0.1"
    assert normalize_figure_document(normalized) == normalized


def test_normalize_document_handles_null_object_and_data_source_lists():
    normalized = normalize_figure_document(
        {
            "version": "not-a-number",
            "objects": None,
            "data_sources": None,
        }
    )

    assert normalized["version"] == 1
    assert normalized["objects"] == []
    assert normalized["data_sources"] == []
    assert normalize_figure_document(normalized) == normalized


def test_generated_figure_document_records_data_recipe_style_and_objects(tmp_path):
    figure_path = tmp_path / "figures" / "Fig-W1_profile.svg"
    data_path = tmp_path / "data" / "waxs_profile.csv"
    figure_path.parent.mkdir()
    data_path.parent.mkdir()
    figure_path.write_text("<svg />", encoding="utf-8")
    data_path.write_text("two_theta,intensity\n1,2\n", encoding="utf-8")

    document = create_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="Fig-W1_profile",
        data_sources=[
            {
                "id": "profile-data",
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": "polynexus.core.waxs_engine.waxs_output",
            "function": "fig_w1_profile",
            "inputs": {"result_ref": "waxs:sample-a"},
        },
        style={"title": "WAXS profile", "xlabel": "2theta"},
        objects=[
            {
                "id": "series-observed",
                "type": "plot_series",
                "name": "Observed",
                "data_ref": "profile-data",
                "style": {"color": "#111111", "line_width": 0.8},
            }
        ],
    )
    save_figure_document(str(figure_path), document)
    loaded = load_figure_document(str(figure_path))

    assert loaded["mode"] == "object"
    assert loaded["figure_id"] == "Fig-W1_profile"
    assert loaded["technique"] == "waxs"
    assert loaded["recipe"]["function"] == "fig_w1_profile"
    assert loaded["data_sources"][0]["path"] == str(data_path.resolve())
    assert loaded["style"]["title"] == "WAXS profile"
    assert loaded["objects"][0]["type"] == "plot_series"
    assert loaded["objects"][0]["data_ref"] == "profile-data"
    assert loaded["layers"][0]["object_ids"] == ["series-observed"]


def test_save_generated_figure_document_records_plot_edit_pointer(tmp_path):
    figure_path = tmp_path / "figures" / "Fig-D1_full_curve.svg"
    data_path = tmp_path / "data" / "dsc_parameters.csv"
    figure_path.parent.mkdir()
    data_path.parent.mkdir()
    figure_path.write_text("<svg />", encoding="utf-8")
    data_path.write_text("label,Tg\nsample,80\n", encoding="utf-8")

    document_path = save_generated_figure_document(
        str(figure_path),
        technique="dsc",
        figure_id="Fig-D1_full_curve",
        data_sources=[{"id": "dsc-params", "path": str(data_path), "kind": "csv"}],
        recipe={"module": "polynexus.core.dsc_engine.dsc_output", "function": "fig_d1_full_curve"},
        style={"title": "DSC full curve"},
        objects=[{"id": "heat-flow", "type": "plot_series", "data_ref": "dsc-params"}],
    )

    loaded = load_figure_document(str(figure_path))

    assert document_path == figure_path.with_suffix(".pnfig.json")
    assert loaded["mode"] == "object"
    assert loaded["technique"] == "dsc"
    assert load_figure_document_path(str(figure_path)) == str(document_path.resolve())


def test_plot_edits_can_record_figure_document_path(tmp_path):
    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    figure_path.write_bytes(b"fake")
    document_path = figure_path.with_suffix(".pnfig.json")

    save_figure_document_path(str(figure_path), str(document_path))

    assert load_figure_document_path(str(figure_path)) == str(document_path.resolve())


def test_load_figure_document_uses_recorded_sidecar_path_for_export_variant(tmp_path):
    source_path = tmp_path / "figures" / "source.png"
    copied_path = tmp_path / "figures" / "copied.pdf"
    source_path.parent.mkdir()
    source_path.write_bytes(b"fake png")
    copied_path.write_bytes(b"%PDF-1.4 fake")

    document = create_generated_figure_document(
        str(source_path),
        technique="saxs",
        figure_id="source",
        style={"title": "Editable Source"},
        objects=[
            {
                "id": "series-source",
                "type": "plot_series",
                "name": "Source",
                "data": {"x": [0.1, 0.2], "y": [1.0, 2.0]},
            }
        ],
    )
    document_path = save_figure_document(str(source_path), document)
    save_figure_document_path(str(copied_path), str(document_path))

    loaded = load_figure_document(str(copied_path))

    assert loaded["mode"] == "object"
    assert loaded["figure_id"] == "source"
    assert loaded["style"]["title"] == "Editable Source"
    assert loaded["objects"][0]["id"] == "series-source"
