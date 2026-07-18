from polynexus.core.figure_edit_commands import UpdateStyleCommand
from polynexus.core.figure_edit_session import EditSession


def _document():
    return {
        "objects": [
            {"id": "line-1", "type": "line", "style": {"color": "black"}},
            {"id": "text-1", "type": "text", "text": "Before"},
        ]
    }


def test_selection_state_and_dirty_follow_successful_edits_and_mark_saved():
    session = EditSession(_document())
    assert session.selection.object_id == ""
    assert session.dirty is False

    session.select("line-1", "object-list")
    assert session.selection.object_id == "line-1"
    assert session.selection.source == "object-list"
    assert session.execute(UpdateStyleCommand("line-1", {"color": "red"})).changed
    assert session.dirty is True

    session.mark_saved()
    assert session.dirty is False
    assert session.undo().changed
    assert session.dirty is True
    assert session.redo().changed
    assert session.dirty is False


def test_new_successful_command_clears_redo_but_noop_and_failure_do_not_change_history():
    session = EditSession(_document())
    first = UpdateStyleCommand("line-1", {"color": "red"})
    second = UpdateStyleCommand("line-1", {"color": "blue"})

    assert session.execute(first).changed
    assert session.undo().changed
    assert session.can_redo is True
    assert session.execute(UpdateStyleCommand("line-1", {"color": "black"})).changed is False
    assert session.can_redo is True
    assert session.execute(UpdateStyleCommand("missing", {"color": "green"})).changed is False
    assert session.can_redo is True
    assert session.execute(second).changed
    assert session.can_redo is False
    assert session.can_undo is True


def test_failed_command_preserves_document_selection_and_history():
    session = EditSession(_document())
    session.select("line-1", "canvas")
    before = session.document
    selection = session.selection

    result = session.execute(UpdateStyleCommand("line-1", {"color": "NaN"}))

    assert result.changed is False
    assert result.error_code == "invalid_color"
    assert session.document == before
    assert session.selection == selection
    assert session.history == ()
    assert session.can_undo is False


def test_document_and_history_views_do_not_expose_mutable_internal_state():
    source = _document()
    session = EditSession(source)
    session.execute(UpdateStyleCommand("line-1", {"color": "red"}))

    document_view = session.document
    document_view["objects"][0]["style"]["color"] = "changed-outside"
    history_view = session.history

    assert session.document["objects"][0]["style"]["color"] == "red"
    assert isinstance(history_view, tuple)
    assert len(history_view) == 1


def test_undo_redo_restore_exact_nested_document_state():
    source = _document()
    session = EditSession(source)
    before = session.document
    command = UpdateStyleCommand("line-1", {"color": "#123456", "nested": {"value": 1}})

    assert session.execute(command).changed
    changed = session.document
    assert session.undo().changed
    assert session.document == before
    assert session.redo().changed
    assert session.document == changed
