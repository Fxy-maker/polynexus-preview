from __future__ import annotations

from polynexus.core.figure_edit_commands import (
    AlignObjectsCommand,
    GroupObjectsCommand,
    DistributeObjectsCommand,
    SetVisibilityCommand,
    UngroupObjectsCommand,
)
from polynexus.core.figure_edit_session import EditSession


def _document():
    return {
        "objects": [
            {"id": "a", "type": "rectangle", "x": 0.1, "y": 0.2, "width": 0.2, "height": 0.1},
            {"id": "b", "type": "rectangle", "x": 0.6, "y": 0.5, "width": 0.1, "height": 0.2},
            {"id": "locked", "type": "rectangle", "locked": True, "x": 0.4, "y": 0.4, "width": 0.1, "height": 0.1},
        ]
    }


def test_align_objects_is_one_undoable_command_and_preserves_size():
    session = EditSession(_document())

    result = session.execute(AlignObjectsCommand(("a", "b"), "left"))

    assert result.changed is True
    objects = {item["id"]: item for item in session.document["objects"]}
    assert objects["a"]["x"] == objects["b"]["x"] == 0.1
    assert objects["b"]["width"] == 0.1
    assert len(session.history) == 1
    assert session.undo().changed is True
    assert session.document == _document()


def test_align_objects_rejects_locked_selection_without_partial_change():
    session = EditSession(_document())
    before = session.document

    result = session.execute(AlignObjectsCommand(("a", "locked"), "center"))

    assert result.changed is False
    assert result.error_code == "locked"
    assert session.document == before


def test_group_and_ungroup_round_trip_as_single_commands():
    session = EditSession(_document())
    group = GroupObjectsCommand(("a", "b"))

    assert session.execute(group).changed is True
    group_id = session.document["objects"][0]["group_id"]
    assert group_id
    assert session.document["objects"][1]["group_id"] == group_id
    assert session.undo().changed is True
    assert "group_id" not in session.document["objects"][0]
    assert session.redo().changed is True

    assert session.execute(UngroupObjectsCommand(("a", "b"))).changed is True
    assert all("group_id" not in item for item in session.document["objects"][:2])


def test_distribute_objects_keeps_outer_edges_and_dimensions():
    document = {
        "objects": [
            {"id": "a", "type": "rectangle", "x": 0.1, "y": 0.1, "width": 0.1, "height": 0.2},
            {"id": "b", "type": "rectangle", "x": 0.35, "y": 0.4, "width": 0.05, "height": 0.3},
            {"id": "c", "type": "rectangle", "x": 0.8, "y": 0.9, "width": 0.2, "height": 0.05},
        ]
    }
    session = EditSession(document)

    result = session.execute(DistributeObjectsCommand(("a", "b", "c"), "horizontal"))

    assert result.changed is True
    objects = {item["id"]: item for item in session.document["objects"]}
    assert objects["a"]["x"] == 0.1
    assert objects["b"]["x"] == 0.475
    assert objects["c"]["x"] == 0.8
    assert (objects["a"]["width"], objects["b"]["width"], objects["c"]["width"]) == (
        0.1,
        0.05,
        0.2,
    )
    assert len(session.history) == 1
    assert session.undo().changed is True
    assert session.document == document


def test_distribute_objects_rejects_two_objects_and_locked_selection():
    session = EditSession(_document())

    too_few = session.execute(DistributeObjectsCommand(("a", "b"), "vertical"))
    assert too_few.changed is False
    assert too_few.error_code == "selection_required"

    before = session.document
    locked = session.execute(DistributeObjectsCommand(("a", "b", "locked"), "vertical"))
    assert locked.changed is False
    assert locked.error_code == "locked"
    assert session.document == before


def test_visibility_command_round_trips_and_rejects_locked_objects():
    session = EditSession(_document())

    hidden = session.execute(SetVisibilityCommand("a", False))

    assert hidden.changed is True
    assert session.document["objects"][0]["visible"] is False
    assert session.undo().changed is True
    assert "visible" not in session.document["objects"][0]

    locked = session.execute(SetVisibilityCommand("locked", False))
    assert locked.changed is False
    assert locked.error_code == "locked"
