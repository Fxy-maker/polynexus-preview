from __future__ import annotations

from types import SimpleNamespace

from polynexus.gui.widgets.chart_editor_batch_edit_mixin import ChartEditorBatchEditMixin


class _Harness(ChartEditorBatchEditMixin):
    def __init__(self):
        self._selected_figure_object_ids = ("a", "b")
        self._selected_figure_object_id = "a"
        self.calls = []

    def _execute_edit(self, command):
        self.calls.append(command)
        return SimpleNamespace(changed=True)


def test_batch_alignment_and_group_actions_submit_core_commands():
    editor = _Harness()

    assert editor._align_selected_objects("left") is True
    assert editor.calls[-1].object_ids == ("a", "b")
    assert editor.calls[-1].mode == "left"

    assert editor._group_selected_objects() is True
    assert editor.calls[-1].object_ids == ("a", "b")
