from __future__ import annotations

from polynexus.plot_runtime.commands import EditWorksheetCells, PlotState, UpdateGraphStyle
from polynexus.plot_runtime.layout import LayoutResolver
from polynexus.plot_runtime.session import FigureSession
from tests.test_reactive_figure_layout import _line_document, _line_worksheet


def test_session_emits_local_scene_diff_for_one_changed_bound_column():
    worksheet = _line_worksheet()
    document = _line_document()
    session = FigureSession(PlotState(worksheet=worksheet, document=document), LayoutResolver())

    assert session.dependency_index["q"] == ("curve",)
    assert session.dependency_index["I"] == ("curve",)
    assert session.dependency_index["sigma"] == ("curve",)
    initial_curve = session.scene.node_by_id("curve")
    update = session.execute(EditWorksheetCells({"I": {1: 0.75}}))

    assert update.ok
    assert update.diff.updated_ids == ("curve",)
    assert update.diff.unchanged_ids == ()
    assert update.scene.node_by_id("curve") != initial_curve
    assert update.scene.node_by_id("curve").points[1].y < initial_curve.points[1].y


def test_session_keeps_last_valid_scene_when_new_revision_cannot_resolve():
    worksheet = _line_worksheet()
    document = _line_document()
    session = FigureSession(PlotState(worksheet=worksheet, document=document), LayoutResolver())
    initial_scene = session.scene

    update = session.execute(EditWorksheetCells({"I": {1: "not-a-number"}}))

    assert not update.ok
    assert update.scene is initial_scene
    assert update.diff.is_empty
    assert update.diagnostics[0].reason_code == "non_numeric_value"


def test_session_does_not_commit_an_unresolvable_edit():
    worksheet = _line_worksheet()
    document = _line_document()
    session = FigureSession(PlotState(worksheet=worksheet, document=document), LayoutResolver())
    initial_state = session.state

    update = session.execute(EditWorksheetCells({"I": {1: "not-a-number"}}))

    assert not update.ok
    assert update.state == initial_state
    assert update.command_result is None
    assert session.state == initial_state
    undo = session.undo()
    assert undo.state == initial_state
    assert undo.diff.is_empty
    redo = session.redo()
    assert redo.state == initial_state
    assert redo.diff.is_empty


def test_session_uses_incremental_resolver_for_style_only_command():
    class CountingResolver(LayoutResolver):
        def __init__(self):
            super().__init__()
            self.full_calls = 0
            self.incremental_calls = 0

        def resolve(self, document, revision):
            self.full_calls += 1
            return super().resolve(document, revision)

        def resolve_incremental(self, document, revision, previous_scene, dirty_object_ids, *, data_changed=False):
            self.incremental_calls += 1
            return super().resolve_incremental(
                document,
                revision,
                previous_scene,
                dirty_object_ids,
                data_changed=data_changed,
            )

    resolver = CountingResolver()
    session = FigureSession(
        PlotState(worksheet=_line_worksheet(), document=_line_document()),
        resolver,
    )

    update = session.execute(UpdateGraphStyle("curve", {"line_width": 2.0}))

    assert update.ok
    assert resolver.full_calls == 1
    assert resolver.incremental_calls == 1
