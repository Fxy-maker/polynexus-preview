from __future__ import annotations

from polynexus.core.figure_edit_commands import ReplaceObjectCommand
from polynexus.core.figure_edit_session import EditSession


def test_replace_object_commits_a_drag_result_as_one_undoable_command():
    document = {
        "objects": [
            {"id": "line-1", "type": "line", "x1": 0.1, "y1": 0.2, "x2": 0.8, "y2": 0.9}
        ]
    }
    session = EditSession(document)
    changed = dict(document["objects"][0], x1=0.3, y1=0.4)

    result = session.execute(ReplaceObjectCommand("line-1", changed))

    assert result.changed is True
    assert len(session.history) == 1
    assert session.document["objects"][0]["x1"] == 0.3
    assert session.undo().changed is True
    assert session.document == document
