import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QApplication

from polynexus.gui.widgets.reactive_figure_view import ReactiveFigureView, ReactiveFigureWindow
from polynexus.plot_runtime.commands import EditWorksheetCells, PlotState, UpdateGraphProperties
from polynexus.plot_runtime.layout import LayoutResolver
from polynexus.plot_runtime.qt_renderer import QtSceneRenderer
from polynexus.plot_runtime.session import FigureSession
from polynexus.plot_runtime.scene import (
    HeatmapCell,
    PanelScene,
    Point,
    Rect,
    RenderScene,
    SceneDiff,
    SceneNode,
    Segment,
    TickMark,
)


def _scene(*, curve_y: float = 30.0) -> RenderScene:
    panel = PanelScene(
        panel_id="panel-1",
        axis_rect=Rect(50.0, 30.0, 240.0, 160.0),
        x_ticks=(TickMark(0.0, "0", 50.0), TickMark(1.0, "1", 290.0)),
        y_ticks=(TickMark(0.0, "0", 190.0), TickMark(1.0, "1", 30.0)),
        x_label="q",
        y_label="I",
        title="Temperature slice",
    )
    return RenderScene(
        revision_id=f"rev-{curve_y}",
        width_px=360,
        height_px=240,
        dpi=100,
        background="#FFFFFF",
        panels=(panel,),
        nodes=(
            SceneNode(
                node_id="curve",
                node_type="plot_series",
                panel_id="panel-1",
                points=(Point(50.0, curve_y), Point(170.0, 90.0), Point(290.0, 50.0)),
                segments=(Segment(Point(110.0, curve_y - 8.0), Point(110.0, curve_y + 8.0)),),
                style={"color": "#1f77b4", "line_width": 2.0},
            ),
            SceneNode(
                node_id="guide",
                node_type="line",
                panel_id="panel-1",
                segments=(Segment(Point(50.0, 120.0), Point(290.0, 120.0)),),
                style={"color": "#888888", "line_style": "dashed"},
            ),
            SceneNode(
                node_id="heatmap",
                node_type="heatmap",
                panel_id="panel-1",
                rectangles=(HeatmapCell(Rect(60.0, 40.0, 30.0, 20.0), 0.5),),
                style={"color": "#dd4477"},
            ),
            SceneNode(
                node_id="legend",
                node_type="legend",
                panel_id="panel-1",
                bounds=Rect(180.0, 40.0, 100.0, 24.0),
                text_anchor=Point(190.0, 58.0),
                text="curve",
            ),
            SceneNode(
                node_id="annotation",
                node_type="text",
                panel_id="panel-1",
                text_anchor=Point(80.0, 80.0),
                text="300 K",
            ),
        ),
    )


def test_qt_renderer_creates_stable_items_for_scene_objects():
    app = QApplication.instance() or QApplication([])
    renderer = QtSceneRenderer()

    renderer.render(_scene())

    assert set(renderer.item_ids()) == {
        "panel-1::axes",
        "curve",
        "guide",
        "heatmap",
        "legend",
        "annotation",
    }
    assert renderer.item_for_id("curve") is not None
    assert renderer.item_for_id("heatmap") is not None
    assert app is not None


def test_qt_renderer_scene_diff_preserves_unchanged_item_instance():
    app = QApplication.instance() or QApplication([])
    renderer = QtSceneRenderer()
    before = _scene()
    renderer.render(before)
    guide_item = renderer.item_for_id("guide")
    annotation_item = renderer.item_for_id("annotation")

    after = _scene(curve_y=45.0)
    diff = SceneDiff.between(before, after)
    renderer.render(after, diff)

    assert renderer.item_for_id("guide") is guide_item
    assert renderer.item_for_id("annotation") is annotation_item
    assert "curve" in diff.updated_ids
    assert renderer.item_for_id("curve") is not None
    assert app is not None


def test_reactive_figure_view_applies_scene_update_and_selection():
    app = QApplication.instance() or QApplication([])
    view = ReactiveFigureView()

    view.set_render_scene(_scene())
    view.select_object("curve")

    assert view.object_item("curve") is not None
    assert view.selected_object_id() == "curve"
    assert view.diagnostics() == ()
    assert app is not None


def test_reactive_figure_view_keeps_last_scene_and_exposes_diagnostic():
    app = QApplication.instance() or QApplication([])
    view = ReactiveFigureView()
    scene = _scene()

    view.set_render_scene(scene)
    view.set_diagnostics((("invalid_log_axis", "log axis limits must be positive"),))

    assert view.render_scene_model() is scene
    assert view.object_item("curve") is not None
    assert view.diagnostics()[0][0] == "invalid_log_axis"
    assert app is not None


def test_reactive_figure_view_routes_session_command_and_undo():
    app = QApplication.instance() or QApplication([])
    from tests.test_reactive_figure_layout import _line_document, _line_worksheet

    session = FigureSession(
        PlotState(worksheet=_line_worksheet(), document=_line_document()),
        LayoutResolver(),
    )
    view = ReactiveFigureView()
    view.attach_session(session)
    old_item = view.object_item("curve")

    update = view.execute_command(EditWorksheetCells({"I": {1: 0.75}}))

    assert update.ok
    assert view.render_scene_model() is update.scene
    assert view.object_item("curve") is not old_item
    undo = view.undo()
    assert undo.ok
    assert view.render_scene_model() is undo.scene
    assert app is not None


def test_reactive_figure_view_emits_v2_command_for_object_interaction():
    app = QApplication.instance() or QApplication([])
    view = ReactiveFigureView()
    view.set_render_scene(_scene())
    commands = []
    view.command_requested.connect(commands.append)
    command = UpdateGraphProperties("annotation", {"x": 120.0, "y": 90.0})

    view.request_command(command)

    assert commands == [command]
    assert app is not None


def test_reactive_figure_view_delegates_drag_semantics_to_command_factory():
    app = QApplication.instance() or QApplication([])
    view = ReactiveFigureView()
    view.set_render_scene(_scene())
    commands = []
    view.command_requested.connect(commands.append)
    command = UpdateGraphProperties("annotation", {"x": 120.0, "y": 90.0})
    view.set_drag_command_factory(
        lambda object_id, start, end: command
        if object_id == "annotation" and start == (1.0, 2.0) and end == (5.0, 8.0)
        else None
    )

    view.drag_object("annotation", (1.0, 2.0), (5.0, 8.0))

    assert commands == [command]
    assert app is not None


def test_reactive_figure_view_maps_keyboard_undo_and_redo_to_session():
    app = QApplication.instance() or QApplication([])
    from tests.test_reactive_figure_layout import _line_document, _line_worksheet

    session = FigureSession(
        PlotState(worksheet=_line_worksheet(), document=_line_document()),
        LayoutResolver(),
    )
    view = ReactiveFigureView()
    view.attach_session(session)
    view.execute_command(EditWorksheetCells({"I": {1: 0.75}}))
    changed_revision = session.state.worksheet.current.revision_id

    view.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier))
    assert session.state.worksheet.current.revision_id != changed_revision
    view.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Y, Qt.KeyboardModifier.ControlModifier))
    assert session.state.worksheet.current.revision_id == changed_revision
    assert app is not None


def test_reactive_figure_view_pointer_drag_hits_stable_object_and_emits_command():
    app = QApplication.instance() or QApplication([])
    view = ReactiveFigureView()
    scene = _scene()
    view.set_render_scene(scene)
    view.resize(420, 300)
    view.show()
    app.processEvents()
    commands = []
    view.command_requested.connect(commands.append)
    command = UpdateGraphProperties("curve", {"dragged": True})
    view.set_drag_command_factory(
        lambda object_id, start, end: command if object_id == "curve" and end[0] > start[0] else None
    )
    viewport = view.viewport()
    start = QPointF(view.mapFromScene(QPointF(170.0, 90.0)))
    end = QPointF(view.mapFromScene(QPointF(180.0, 95.0)))
    press = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        start,
        start,
        QPointF(viewport.mapToGlobal(start.toPoint())),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    release = QMouseEvent(
        QEvent.Type.MouseButtonRelease,
        end,
        end,
        QPointF(viewport.mapToGlobal(end.toPoint())),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )

    app.sendEvent(viewport, press)
    app.sendEvent(viewport, release)

    assert commands == [command]
    assert app is not None
    view.close()


def test_reactive_figure_view_exposes_synchronized_object_list_without_axes_helper():
    app = QApplication.instance() or QApplication([])
    view = ReactiveFigureView()
    before = _scene()
    view.set_render_scene(before)

    assert view.object_ids() == ("curve", "guide", "heatmap", "legend", "annotation")
    assert view.object_entries()[0] == {
        "object_id": "curve",
        "node_type": "plot_series",
        "selected": False,
    }

    view.set_render_scene(_scene(curve_y=45.0), SceneDiff.between(before, _scene(curve_y=45.0)))
    assert view.object_ids() == ("curve", "guide", "heatmap", "legend", "annotation")
    assert app is not None


def test_reactive_figure_window_keeps_actions_disabled_without_project_handle():
    app = QApplication.instance() or QApplication([])
    window = ReactiveFigureWindow()

    assert window._save_action.isEnabled() is False
    assert window._publish_action.isEnabled() is False
    assert window.view is not None
    window.close()
    assert app is not None
