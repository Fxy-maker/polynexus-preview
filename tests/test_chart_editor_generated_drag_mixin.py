from __future__ import annotations

import importlib
import importlib.util
from copy import deepcopy

from polynexus.core.figure_edit_session import EditSession
from polynexus.gui.widgets.chart_editor import ChartEditor


def test_chart_editor_reuses_generated_drag_helpers_from_drag_mixin() -> None:
    spec = importlib.util.find_spec(
        "polynexus.gui.widgets.chart_editor_generated_drag_mixin"
    )
    assert spec is not None

    module = importlib.import_module(
        "polynexus.gui.widgets.chart_editor_generated_drag_mixin"
    )
    mixin = module.ChartEditorGeneratedDragMixin

    assert (
        ChartEditor._activate_generated_drag_state
        is mixin._activate_generated_drag_state
    )
    assert (
        ChartEditor._restore_generated_drag_snapshot
        is mixin._restore_generated_drag_snapshot
    )
    assert ChartEditor._cancel_generated_drag is mixin._cancel_generated_drag


def test_generated_drag_commit_is_one_session_command():
    module = importlib.import_module(
        "polynexus.gui.widgets.chart_editor_generated_drag_mixin"
    )

    class _Harness(module.ChartEditorGeneratedDragMixin):
        def __init__(self):
            self._figure_document = {
                "objects": [
                    {"id": "line-1", "type": "line", "x1": 0.1, "y1": 0.2, "x2": 0.8, "y2": 0.9}
                ]
            }
            self._edit_session = EditSession(self._figure_document)
            self._selected_figure_object_id = "line-1"

        def _generated_figure_object_by_id(self, object_id):
            return next(
                item for item in self._figure_document["objects"] if item["id"] == object_id
            )

        def _execute_edit(self, command):
            return self._edit_session.execute(command)

    editor = _Harness()
    original = deepcopy(editor._figure_document["objects"][0])
    editor._figure_document["objects"][0]["x1"] = 0.35
    editor._figure_document["objects"][0]["y1"] = 0.45

    assert editor._commit_generated_drag_transaction(
        {"object_id": "line-1", "original_object": original, "dirty": True}
    ) is True
    assert len(editor._edit_session.history) == 1
    assert editor._edit_session.document["objects"][0]["x1"] == 0.35
