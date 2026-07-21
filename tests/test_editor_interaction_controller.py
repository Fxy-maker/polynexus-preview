from __future__ import annotations

from polynexus.gui.widgets.chart_editor_interaction_controller import (
    EditorInteractionController,
    EditorTool,
    GestureState,
)


def test_controller_returns_to_select_after_create_commit():
    controller = EditorInteractionController()

    assert controller.set_tool(EditorTool.RECTANGLE) is True
    started = controller.begin_create((10.0, 20.0))
    updated = controller.update_create((30.0, 40.0))
    finished = controller.finish_create((40.0, 60.0))

    assert started.state is GestureState.CREATING
    assert updated.current_point == (30.0, 40.0)
    assert finished.state is GestureState.SELECT_IDLE
    assert finished.committed is True
    assert controller.tool is EditorTool.SELECT


def test_controller_escape_cancels_text_edit_without_commit():
    controller = EditorInteractionController()

    controller.set_tool(EditorTool.TEXT)
    controller.begin_create((10.0, 20.0))
    editing = controller.begin_text_edit()
    cancelled = controller.cancel()

    assert editing.state is GestureState.TEXT_EDITING
    assert cancelled.state is GestureState.SELECT_IDLE
    assert cancelled.committed is False
    assert controller.tool is EditorTool.SELECT


def test_controller_keeps_object_and_handle_context_during_drag():
    controller = EditorInteractionController()

    body = controller.begin_body_drag("note", (12.0, 24.0))
    moved = controller.update_drag((20.0, 32.0))
    committed = controller.finish_drag()

    assert body.state is GestureState.BODY_DRAGGING
    assert body.object_id == "note"
    assert moved.current_point == (20.0, 32.0)
    assert committed.committed is True
    assert committed.state is GestureState.SELECT_IDLE

    handle = controller.begin_handle_drag("curve", 2, (4.0, 8.0))
    assert handle.state is GestureState.HANDLE_DRAGGING
    assert handle.object_id == "curve"
    assert handle.handle_index == 2


def test_controller_rejects_invalid_transitions_without_losing_selection():
    controller = EditorInteractionController()

    controller.set_tool(EditorTool.LINE)
    assert controller.begin_create((1.0, 2.0)).state is GestureState.CREATING
    invalid = controller.begin_body_drag("other", (3.0, 4.0))

    assert invalid.accepted is False
    assert controller.state is GestureState.CREATING
    assert controller.finish_create((1.0, 2.0)).committed is False
    assert controller.state is GestureState.SELECT_IDLE
