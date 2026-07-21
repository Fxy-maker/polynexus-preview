from __future__ import annotations

from polynexus.gui.widgets.chart_editor_generated_interaction_adapter import (
    GeneratedInteractionAdapter,
    HitTarget,
)


def test_target_exposes_body_and_handle_feedback_without_renderer_details():
    body = GeneratedInteractionAdapter.target_from_drag_state(
        "note",
        {"kind": "body", "object_type": "text"},
    )
    handle = GeneratedInteractionAdapter.target_from_drag_state(
        "curve",
        {"kind": "curve", "handle_index": 2},
        object_type="curve",
    )

    assert body == HitTarget("note", "text", "body", None, "move")
    assert body.cursor == "move"
    assert handle.object_id == "curve"
    assert handle.handle_index == 2
    assert handle.cursor == "curve"


def test_adapter_hit_test_reuses_existing_generated_drag_contract():
    class FakeHost:
        def _generated_press_drag_object_ids(self):
            return ("behind", "front")

        def _generated_drag_state_for_press(self, _event, object_id):
            if object_id == "front":
                return {"kind": "rectangle", "handle_index": 1}
            return None

        def _generated_figure_object_by_id(self, object_id):
            return {"id": object_id, "type": "rectangle"}

    target = GeneratedInteractionAdapter(FakeHost()).hit_test(object())

    assert target is not None
    assert target.object_id == "front"
    assert target.object_type == "rectangle"
    assert target.kind == "rectangle"
    assert target.handle_index == 1
    assert target.cursor == "resize"
