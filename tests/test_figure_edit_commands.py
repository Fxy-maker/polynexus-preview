from copy import deepcopy

from polynexus.core.figure_edit_commands import (
    AddObjectCommand,
    CropCanvasCommand,
    DeleteObjectCommand,
    MoveLayerCommand,
    PasteObjectCommand,
    SetLockCommand,
    SetVisibilityCommand,
    UpdateGeometryCommand,
    UpdatePlotSeriesDataCommand,
    UpdateStyleCommand,
    UpdateTextCommand,
)
from polynexus.core.figure_edit_session import EditSession


def _document():
    return {
        "canvas": {"width": 100, "height": 80},
        "objects": [
            {
                "id": "background",
                "type": "image_background",
                "locked": True,
                "bounds": {"x": 0, "y": 0, "width": 100, "height": 80},
            },
            {
                "id": "line-1",
                "type": "line",
                "style": {"color": "black", "line_width": 1.0, "line_style": "-"},
                "x1": 1.0,
                "y1": 2.0,
                "x2": 20.0,
                "y2": 30.0,
            },
            {"id": "text-1", "type": "text", "text": "Old", "style": {"color": "black"}},
            {"id": "series-1", "type": "plot_series", "style": {"color": "blue"}},
            {"id": "unknown-1", "type": "extension_object"},
        ],
    }


def _ids(session):
    return [item["id"] for item in session.document["objects"]]


def test_update_style_execute_undo_redo():
    session = EditSession(_document())
    command = UpdateStyleCommand("line-1", {"color": "#12AbEF", "line_width": 2.5})

    result = session.execute(command)
    assert result.changed is True
    assert session.document["objects"][1]["style"] == {
        "color": "#12AbEF",
        "line_width": 2.5,
        "line_style": "-",
    }

    assert session.undo().changed is True
    assert session.document["objects"][1]["style"]["color"] == "black"
    assert session.redo().changed is True
    assert session.document["objects"][1]["style"]["line_width"] == 2.5


def test_update_legend_geometry_drops_legacy_placement_fields():
    document = {
        "objects": [
            {
                "id": "legend",
                "type": "legend",
                "style": {
                    "loc": "upper right",
                    "bbox_to_anchor": [0.8, 0.9],
                    "box_size": [0.2, 0.1],
                    "ncol": 2,
                },
            }
        ]
    }
    session = EditSession(document)

    result = session.execute(
        UpdateStyleCommand(
            "legend",
            {
                "legend_geometry": {
                    "space": "axes",
                    "x": 0.4,
                    "y": 0.3,
                    "width": 0.35,
                    "height": 0.2,
                }
            },
        )
    )

    assert result.changed is True
    style = session.document["objects"][0]["style"]
    assert style["legend_geometry"]["x"] == 0.4
    assert all(key not in style for key in ("loc", "bbox_to_anchor", "box_size"))
    assert session.undo().changed is True
    assert session.document["objects"][0]["style"]["loc"] == "upper right"


def test_add_object_execute_undo_redo_and_duplicate_failure():
    session = EditSession(_document())
    payload = {"id": "rectangle-1", "type": "rectangle", "style": {"color": "red"}}

    assert session.execute(AddObjectCommand(payload)).changed
    assert _ids(session)[-1] == "rectangle-1"
    assert session.undo().changed
    assert "rectangle-1" not in _ids(session)
    assert session.redo().changed
    assert "rectangle-1" in _ids(session)

    before = session.document
    duplicate = session.execute(AddObjectCommand(payload))
    assert duplicate.changed is False
    assert duplicate.error_code == "object_exists"
    assert session.document == before


def test_delete_object_execute_undo_redo_and_background_failure():
    session = EditSession(_document())

    assert session.execute(DeleteObjectCommand("line-1")).changed
    assert "line-1" not in _ids(session)
    assert session.undo().changed
    assert "line-1" in _ids(session)
    assert session.redo().changed
    assert "line-1" not in _ids(session)

    failed = session.execute(DeleteObjectCommand("background"))
    assert failed.changed is False
    assert failed.error_code in {"locked", "capability_not_supported"}


def test_update_text_execute_noop_undo_redo_and_unsupported_object():
    session = EditSession(_document())

    assert session.execute(UpdateTextCommand("text-1", "New")).changed
    assert session.execute(UpdateTextCommand("text-1", "New")).changed is False
    assert len(session.history) == 1
    assert session.undo().changed
    assert session.document["objects"][2]["text"] == "Old"
    assert session.redo().changed
    assert session.document["objects"][2]["text"] == "New"

    failed = session.execute(UpdateTextCommand("line-1", "not allowed"))
    assert failed.changed is False
    assert failed.error_code == "capability_not_supported"


def test_update_geometry_execute_noop_undo_redo_and_locked_failure():
    session = EditSession(_document())
    command = UpdateGeometryCommand("line-1", {"x1": 5.0, "y2": 40.0})

    assert session.execute(command).changed
    assert session.document["objects"][1]["x1"] == 5.0
    assert session.execute(command).changed is False
    assert session.undo().changed
    assert session.document["objects"][1]["x1"] == 1.0
    assert session.redo().changed
    assert session.document["objects"][1]["y2"] == 40.0

    failed = session.execute(UpdateGeometryCommand("background", {"x": 1.0}))
    assert failed.changed is False
    assert failed.error_code == "locked"


def test_update_plot_series_data_execute_undo_redo():
    document = _document()
    document["objects"].append(
        {"id": "points", "type": "plot_series", "data": {"x": [1.0], "y": [2.0]}}
    )
    session = EditSession(document)

    command = UpdatePlotSeriesDataCommand("points", [1.0, 2.0], [2.0, 3.0])
    assert session.execute(command).changed
    assert session.document["objects"][-1]["data"] == {
        "x": [1.0, 2.0],
        "y": [2.0, 3.0],
    }
    assert session.undo().changed
    assert session.document["objects"][-1]["data"] == {"x": [1.0], "y": [2.0]}
    assert session.redo().changed
    assert session.document["objects"][-1]["data"] == {
        "x": [1.0, 2.0],
        "y": [2.0, 3.0],
    }


def test_move_layer_execute_noop_undo_redo_and_background_failure():
    session = EditSession(_document())
    command = MoveLayerCommand("text-1", 1)

    assert session.execute(command).changed
    assert _ids(session)[1:3] == ["text-1", "line-1"]
    assert session.execute(MoveLayerCommand("text-1", 1)).changed is False
    assert session.undo().changed
    assert _ids(session)[1:3] == ["line-1", "text-1"]
    assert session.redo().changed
    assert _ids(session)[1:3] == ["text-1", "line-1"]

    failed = session.execute(MoveLayerCommand("background", 2))
    assert failed.changed is False
    assert failed.error_code == "locked"


def test_visibility_execute_noop_undo_redo_and_unknown_failure():
    session = EditSession(_document())
    command = SetVisibilityCommand("line-1", False)

    assert session.execute(command).changed
    assert session.document["objects"][1]["visible"] is False
    assert session.execute(SetVisibilityCommand("line-1", False)).changed is False
    assert session.undo().changed
    assert "visible" not in session.document["objects"][1]
    assert session.redo().changed
    assert session.document["objects"][1]["visible"] is False

    failed = session.execute(SetVisibilityCommand("unknown-1", False))
    assert failed.changed is False
    assert failed.error_code == "capability_not_supported"


def test_lock_execute_undo_redo_blocks_normal_edits():
    session = EditSession(_document())

    assert session.execute(SetLockCommand("line-1", True)).changed
    assert session.document["objects"][1]["locked"] is True
    blocked = session.execute(UpdateStyleCommand("line-1", {"color": "red"}))
    assert blocked.changed is False
    assert blocked.error_code == "locked"

    assert session.undo().changed
    assert "locked" not in session.document["objects"][1]
    assert session.redo().changed
    assert session.document["objects"][1]["locked"] is True


def test_paste_object_execute_undo_redo_and_missing_source_failure():
    session = EditSession(_document())

    result = session.execute(PasteObjectCommand("line-1"))
    assert result.changed
    assert "line-1-copy" in _ids(session)
    pasted = next(item for item in session.document["objects"] if item["id"] == "line-1-copy")
    assert pasted is not session.document["objects"][1]
    assert session.undo().changed
    assert "line-1-copy" not in _ids(session)
    assert session.redo().changed
    assert "line-1-copy" in _ids(session)

    failed = session.execute(PasteObjectCommand("missing"))
    assert failed.changed is False
    assert failed.error_code == "object_not_found"


def test_crop_canvas_execute_noop_undo_redo_and_invalid_crop_failure():
    session = EditSession(_document())
    command = CropCanvasCommand(
        {"x": 10.0, "y": 5.0, "width": 70.0, "height": 50.0}, object_id="background"
    )

    assert session.execute(command).changed
    assert session.document["canvas"]["crop"]["width"] == 70.0
    assert session.execute(command).changed is False
    assert session.undo().changed
    assert "crop" not in session.document["canvas"]
    assert session.redo().changed
    assert "crop" in session.document["canvas"]

    before = session.document
    failed = session.execute(CropCanvasCommand({"x": 0, "y": 0, "width": float("nan"), "height": 2}))
    assert failed.changed is False
    assert failed.error_code == "invalid_crop"
    assert session.document == before


def test_invalid_color_does_not_change_document_or_create_history():
    session = EditSession(_document())
    before = session.document

    result = session.execute(UpdateStyleCommand("line-1", {"color": "bad"}))

    assert result.changed is False
    assert result.error_code == "invalid_color"
    assert session.document == before
    assert session.can_undo is False


def test_commands_copy_payloads_and_do_not_mutate_input_document():
    source = _document()
    original = deepcopy(source)
    session = EditSession(source)
    source["objects"][1]["style"]["color"] = "red"
    source["objects"].append({"id": "outside", "type": "line"})
    source_after_external_changes = deepcopy(source)

    assert session.document == original
    session.execute(UpdateStyleCommand("line-1", {"color": "green"}))
    assert source == source_after_external_changes
