from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EditorTool(str, Enum):
    SELECT = "select"
    TEXT = "text"
    LINE = "line"
    ARROW = "arrow"
    CURVE = "curve"
    RECTANGLE = "rectangle"


class GestureState(str, Enum):
    SELECT_IDLE = "select_idle"
    CREATING = "creating"
    TEXT_EDITING = "text_editing"
    BODY_DRAGGING = "body_dragging"
    HANDLE_DRAGGING = "handle_dragging"


@dataclass(frozen=True)
class InteractionTransition:
    accepted: bool
    state: GestureState
    tool: EditorTool
    object_id: str = ""
    handle_index: int | None = None
    press_point: tuple[float, float] | None = None
    current_point: tuple[float, float] | None = None
    committed: bool = False


class EditorInteractionController:
    """Qt-independent state machine for direct chart editing gestures."""

    def __init__(self):
        self.tool = EditorTool.SELECT
        self.state = GestureState.SELECT_IDLE
        self.object_id = ""
        self.handle_index = None
        self.press_point = None
        self.current_point = None

    def _transition(self, *, accepted=True, committed=False):
        return InteractionTransition(
            accepted=bool(accepted),
            state=self.state,
            tool=self.tool,
            object_id=self.object_id,
            handle_index=self.handle_index,
            press_point=self.press_point,
            current_point=self.current_point,
            committed=bool(committed),
        )

    def _reset(self):
        self.tool = EditorTool.SELECT
        self.state = GestureState.SELECT_IDLE
        self.object_id = ""
        self.handle_index = None
        self.press_point = None
        self.current_point = None

    @staticmethod
    def _point(value):
        if not isinstance(value, (tuple, list)) or len(value) < 2:
            return None
        try:
            point = (float(value[0]), float(value[1]))
        except (TypeError, ValueError):
            return None
        if not all(map(lambda item: item == item and abs(item) != float("inf"), point)):
            return None
        return point

    @staticmethod
    def _tool(value):
        if isinstance(value, EditorTool):
            return value
        try:
            return EditorTool(str(value or "").strip().lower())
        except ValueError:
            return None

    def set_tool(self, tool):
        selected = self._tool(tool)
        if selected is None:
            return False
        self._reset()
        self.tool = selected
        return True

    def begin_create(self, point):
        point = self._point(point)
        if self.state is not GestureState.SELECT_IDLE or self.tool is EditorTool.SELECT:
            return self._transition(accepted=False)
        if point is None:
            return self._transition(accepted=False)
        self.state = GestureState.CREATING
        self.press_point = point
        self.current_point = point
        return self._transition()

    def update_create(self, point):
        point = self._point(point)
        if self.state is not GestureState.CREATING or point is None:
            return self._transition(accepted=False)
        self.current_point = point
        return self._transition()

    def finish_create(self, point):
        point = self._point(point)
        if self.state is not GestureState.CREATING or point is None:
            return self._transition(accepted=False)
        self.current_point = point
        committed = self.press_point != self.current_point
        self._reset()
        return self._transition(committed=committed)

    def begin_text_edit(self):
        if self.state is not GestureState.CREATING:
            return self._transition(accepted=False)
        self.state = GestureState.TEXT_EDITING
        return self._transition()

    def begin_body_drag(self, object_id, point):
        return self._begin_drag(object_id, None, point, GestureState.BODY_DRAGGING)

    def begin_handle_drag(self, object_id, handle_index, point):
        try:
            handle_index = int(handle_index)
        except (TypeError, ValueError):
            return self._transition(accepted=False)
        return self._begin_drag(object_id, handle_index, point, GestureState.HANDLE_DRAGGING)

    def _begin_drag(self, object_id, handle_index, point, state):
        point = self._point(point)
        object_id = str(object_id or "").strip()
        if self.state is not GestureState.SELECT_IDLE or not object_id or point is None:
            return self._transition(accepted=False)
        self.state = state
        self.object_id = object_id
        self.handle_index = handle_index
        self.press_point = point
        self.current_point = point
        return self._transition()

    def update_drag(self, point):
        point = self._point(point)
        if self.state not in {
            GestureState.BODY_DRAGGING,
            GestureState.HANDLE_DRAGGING,
        } or point is None:
            return self._transition(accepted=False)
        self.current_point = point
        return self._transition()

    def finish_drag(self):
        if self.state not in {
            GestureState.BODY_DRAGGING,
            GestureState.HANDLE_DRAGGING,
        }:
            return self._transition(accepted=False)
        committed = self.press_point != self.current_point
        self._reset()
        return self._transition(committed=committed)

    def cancel(self):
        self._reset()
        return self._transition()


__all__ = [
    "EditorInteractionController",
    "EditorTool",
    "GestureState",
    "InteractionTransition",
]
