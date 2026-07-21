"""Renderer-neutral hit targets for generated chart editing.

The Matplotlib canvas remains the renderer.  This small adapter gives the
interaction layer a stable description of what a pointer can do, so cursor
feedback and gesture state do not need to know how a particular artist was
hit-tested.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HitTarget:
    object_id: str
    object_type: str
    kind: str = "body"
    handle_index: int | None = None
    cursor_role: str = "move"
    locked: bool = False

    @property
    def cursor(self) -> str:
        """Compatibility alias for callers that use the short contract."""

        return self.cursor_role


class GeneratedInteractionAdapter:
    """Translate existing generated hit-test results into ``HitTarget``."""

    _CURSOR_ROLES = {
        "line": "resize",
        "curve": "curve",
        "rectangle": "resize",
        "plot_series": "point",
        "body": "move",
        "line-body": "move",
        "legend": "move",
        "text": "move",
    }

    def __init__(self, host=None):
        self.host = host

    @classmethod
    def target_from_drag_state(
        cls,
        object_id,
        drag_state,
        *,
        object_type="",
    ) -> HitTarget | None:
        if not isinstance(drag_state, dict):
            return None
        object_id = str(object_id or "").strip()
        if not object_id:
            return None
        kind = str(drag_state.get("kind", "body") or "body")
        object_type = str(
            object_type or drag_state.get("object_type", "") or kind
        )
        if kind == "body":
            object_type = str(drag_state.get("object_type", object_type) or object_type)
        handle_index = drag_state.get("handle_index")
        if handle_index is not None:
            try:
                handle_index = int(handle_index)
            except (TypeError, ValueError):
                handle_index = None
        locked = bool(drag_state.get("locked", False))
        cursor_role = "not-allowed" if locked else cls._CURSOR_ROLES.get(
            kind,
            cls._CURSOR_ROLES.get(object_type, "move"),
        )
        return HitTarget(
            object_id=object_id,
            object_type=object_type,
            kind=kind,
            handle_index=handle_index,
            cursor_role=cursor_role,
            locked=locked,
        )

    def hit_test(self, event) -> HitTarget | None:
        """Return the first existing drag target under ``event``."""

        host = self.host
        if host is None:
            return None
        object_ids = getattr(host, "_generated_press_drag_object_ids", lambda: ())()
        for object_id in object_ids:
            drag_state = getattr(host, "_generated_drag_state_for_press", lambda *_: None)(
                event,
                object_id,
            )
            if drag_state is None:
                continue
            figure_object = getattr(host, "_generated_figure_object_by_id", lambda _id: None)(
                object_id
            )
            object_type = (
                figure_object.get("type", "")
                if isinstance(figure_object, dict)
                else ""
            )
            return self.target_from_drag_state(
                object_id,
                drag_state,
                object_type=object_type,
            )
        return None

    @staticmethod
    def feedback_for(target: HitTarget | None) -> str:
        if target is None:
            return "default"
        return target.cursor_role


__all__ = ["GeneratedInteractionAdapter", "HitTarget"]
