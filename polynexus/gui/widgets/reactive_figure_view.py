"""Qt view boundary for the renderer-independent reactive figure runtime."""

from __future__ import annotations

from typing import Any, Callable, Iterable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTransform
from PySide6.QtWidgets import QGraphicsItem, QGraphicsView, QMainWindow, QToolBar

from polynexus.plot_runtime.qt_renderer import QtSceneRenderer
from polynexus.plot_runtime.scene import RenderScene, SceneDiagnostic, SceneDiff

from ..i18n import tr


class ReactiveFigureView(QGraphicsView):
    """Display a resolved scene without owning data or scientific layout logic."""

    command_requested = Signal(object)

    def __init__(self, parent: Any | None = None, renderer: QtSceneRenderer | None = None):
        super().__init__(parent)
        self._renderer = renderer or QtSceneRenderer()
        self.setScene(self._renderer.graphics_scene)
        self._scene_model: RenderScene | None = None
        self._session: Any | None = None
        self._selected_object_id: str | None = None
        self._diagnostics: tuple[tuple[str, str], ...] = ()
        self._drag_command_factory: Callable[[str, tuple[float, float], tuple[float, float]], Any | None] | None = None
        self._pointer_drag: tuple[str, tuple[float, float]] | None = None
        self._project_service: Any | None = None
        self._project_handle: Any | None = None

    def set_render_scene(self, scene: RenderScene, diff: SceneDiff | None = None) -> None:
        self._renderer.render(scene, diff)
        self._scene_model = scene

    def apply_update(self, update: Any) -> None:
        self.set_render_scene(update.scene, update.diff)
        self.set_diagnostics(update.diagnostics)

    def attach_session(self, session: Any) -> None:
        self._session = session
        self.set_render_scene(session.scene)

    def attach_project_lifecycle(self, service: Any, handle: Any) -> None:
        """Attach persistence/publication services without moving them into Qt."""
        self._project_service = service
        self._project_handle = handle

    def save_working(self) -> Any:
        if self._project_service is None or self._project_handle is None:
            raise RuntimeError("ReactiveFigureView has no project lifecycle")
        result = self._project_service.save_working(self._project_handle)
        return result

    def publish(self, *, profile: Any | None = None) -> Any:
        if self._project_service is None or self._project_handle is None:
            raise RuntimeError("ReactiveFigureView has no project lifecycle")
        return self._project_service.publish(self._project_handle, profile=profile)

    def execute_command(self, command: Any) -> Any:
        if self._session is None:
            raise RuntimeError("ReactiveFigureView has no FigureSession")
        update = self._session.execute(command)
        self.apply_update(update)
        return update

    def request_command(self, command: Any) -> None:
        """Emit user intent for a controller to execute through ``FigureSession``."""

        self.command_requested.emit(command)

    def set_drag_command_factory(
        self,
        factory: Callable[[str, tuple[float, float], tuple[float, float]], Any | None] | None,
    ) -> None:
        self._drag_command_factory = factory

    def drag_object(
        self,
        object_id: str,
        start: tuple[float, float],
        end: tuple[float, float],
    ) -> Any | None:
        """Convert a pointer gesture through an injected V2 command factory."""

        if self.object_item(object_id) is None or self._drag_command_factory is None:
            return None
        command = self._drag_command_factory(str(object_id), start, end)
        if command is not None:
            self.request_command(command)
        return command

    def mousePressEvent(self, event: Any) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            scene_point = self.mapToScene(event.position().toPoint())
            item = self._renderer.graphics_scene.itemAt(scene_point, QTransform())
            object_id = self._object_id_for_item(item)
            if object_id:
                start = (float(scene_point.x()), float(scene_point.y()))
                self.select_object(object_id)
                self._pointer_drag = (object_id, start)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: Any) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._pointer_drag is not None:
            object_id, start = self._pointer_drag
            scene_point = self.mapToScene(event.position().toPoint())
            end = (float(scene_point.x()), float(scene_point.y()))
            self._pointer_drag = None
            if start != end:
                self.drag_object(object_id, start, end)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    @staticmethod
    def _object_id_for_item(item: Any) -> str | None:
        current = item
        while current is not None:
            value = current.data(0)
            if value:
                object_id = str(value)
                return None if object_id.endswith("::axes") else object_id
            current = current.parentItem()
        return None

    def undo(self) -> Any:
        if self._session is None:
            raise RuntimeError("ReactiveFigureView has no FigureSession")
        update = self._session.undo()
        self.apply_update(update)
        return update

    def redo(self) -> Any:
        if self._session is None:
            raise RuntimeError("ReactiveFigureView has no FigureSession")
        update = self._session.redo()
        self.apply_update(update)
        return update

    def keyPressEvent(self, event: Any) -> None:
        modifiers = event.modifiers()
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_Z and not modifiers & Qt.KeyboardModifier.ShiftModifier:
                self.undo()
                event.accept()
                return
            if event.key() == Qt.Key.Key_Y or (
                event.key() == Qt.Key.Key_Z and modifiers & Qt.KeyboardModifier.ShiftModifier
            ):
                self.redo()
                event.accept()
                return
        super().keyPressEvent(event)

    def render_scene_model(self) -> RenderScene | None:
        return self._scene_model

    def object_item(self, object_id: str) -> Any | None:
        return self._renderer.item_for_id(object_id)

    def object_ids(self) -> tuple[str, ...]:
        """Return graph-object IDs in scene z-order, excluding helper axes."""

        if self._scene_model is None:
            return ()
        return tuple(node.node_id for node in self._scene_model.nodes)

    def object_entries(self) -> tuple[dict[str, Any], ...]:
        """Return stable, renderer-neutral entries for an object-list widget."""

        if self._scene_model is None:
            return ()
        selected = self._selected_object_id
        return tuple(
            {
                "object_id": node.node_id,
                "node_type": node.node_type,
                "selected": node.node_id == selected,
            }
            for node in self._scene_model.nodes
        )

    def select_object(self, object_id: str | None) -> None:
        if self._selected_object_id:
            previous = self.object_item(self._selected_object_id)
            if previous is not None:
                previous.setSelected(False)
        self._selected_object_id = None if object_id is None else str(object_id)
        if self._selected_object_id:
            item = self.object_item(self._selected_object_id)
            if item is not None:
                item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
                item.setSelected(True)

    def selected_object_id(self) -> str | None:
        return self._selected_object_id

    def set_diagnostics(self, diagnostics: Iterable[SceneDiagnostic | tuple[str, str]]) -> None:
        normalized: list[tuple[str, str]] = []
        for diagnostic in diagnostics:
            if isinstance(diagnostic, SceneDiagnostic):
                normalized.append((diagnostic.reason_code, diagnostic.message))
            else:
                normalized.append((str(diagnostic[0]), str(diagnostic[1])))
        self._diagnostics = tuple(normalized)

    def diagnostics(self) -> tuple[tuple[str, str], ...]:
        return self._diagnostics


class ReactiveFigureWindow(QMainWindow):
    """User-facing V2 window with explicit save and publication actions."""

    def __init__(
        self,
        parent: Any | None = None,
        *,
        view: ReactiveFigureView | None = None,
    ) -> None:
        super().__init__(parent)
        self.view = view or ReactiveFigureView()
        self.setCentralWidget(self.view)
        toolbar = QToolBar(tr("REACTIVE_FIGURE_TOOLBAR"), self)
        self.addToolBar(toolbar)
        self._save_action = toolbar.addAction(tr("REACTIVE_FIGURE_SAVE_WORKING"))
        self._publish_action = toolbar.addAction(tr("REACTIVE_FIGURE_PUBLISH"))
        self._save_action.triggered.connect(self._save_working)
        self._publish_action.triggered.connect(self._publish)
        self._save_action.setEnabled(False)
        self._publish_action.setEnabled(False)

    def attach_session(self, session: Any) -> None:
        self.view.attach_session(session)

    def attach_project_lifecycle(self, service: Any, handle: Any) -> None:
        self.view.attach_project_lifecycle(service, handle)
        self._save_action.setEnabled(True)
        self._publish_action.setEnabled(True)

    def _save_working(self) -> None:
        try:
            result = self.view.save_working()
            self.statusBar().showMessage(
                tr("REACTIVE_FIGURE_SAVE_DONE", result.working_revision),
                5000,
            )
        except Exception as exc:
            self.statusBar().showMessage(str(exc), 8000)

    def _publish(self) -> None:
        try:
            result = self.view.publish()
            self.statusBar().showMessage(
                tr("REACTIVE_FIGURE_PUBLISH_DONE", result.published_revision),
                5000,
            )
        except Exception as exc:
            self.statusBar().showMessage(str(exc), 8000)

    def __getattr__(self, name: str) -> Any:
        """Preserve the existing direct-view surface for callers/tests."""
        view = self.__dict__.get("view")
        if view is not None:
            return getattr(view, name)
        raise AttributeError(name)
