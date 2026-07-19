from __future__ import annotations

from polynexus.core.figure_edit_commands import (
    AlignObjectsCommand,
    GroupObjectsCommand,
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
