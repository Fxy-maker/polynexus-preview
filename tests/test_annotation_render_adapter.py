from copy import deepcopy
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRectF, Qt
from PySide6.QtWidgets import QApplication, QGraphicsScene

from polynexus.core.figure_edit_session import EditSession
from polynexus.gui.widgets.annotation_render_adapter import AnnotationRenderAdapter
from polynexus.gui.widgets.chart_editor_edit_session_mixin import (
    ChartEditorEditSessionMixin,
)


def test_render_adapter_projects_supported_annotation_objects_and_selection():
    app = QApplication.instance() or QApplication([])
    scene = QGraphicsScene()
    scene.setSceneRect(QRectF(0, 0, 100, 50))
    adapter = AnnotationRenderAdapter(scene)
    objects = [
        {
            "id": "text-1",
            "type": "text",
            "x": 0.2,
            "y": 0.25,
            "text": "Peak",
            "selected": True,
        },
        {
            "id": "line-1",
            "type": "line",
            "x1": 0.1,
            "y1": 0.2,
            "x2": 0.8,
            "y2": 0.7,
        },
        {
            "id": "arrow-1",
            "type": "arrow",
            "x1": 0.1,
            "y1": 0.2,
            "x2": 0.8,
            "y2": 0.7,
        },
        {
            "id": "rectangle-1",
            "type": "rectangle",
            "x": 0.1,
            "y": 0.2,
            "width": 0.4,
            "height": 0.3,
        },
        {
            "id": "highlight-1",
            "type": "highlight",
            "x": 0.3,
            "y": 0.1,
            "width": 0.2,
            "height": 0.4,
        },
        {"id": "unknown-1", "type": "not-supported"},
    ]

    projected = adapter.replace_objects(objects)

    assert set(projected) == {
        "text-1",
        "line-1",
        "arrow-1",
        "rectangle-1",
        "highlight-1",
    }
    assert projected["text-1"].data(0) == "text-1"
    assert projected["text-1"].pos().x() == 20.0
    assert projected["text-1"].pos().y() == 12.5
    assert projected["text-1"].isSelected()
    assert adapter.scene_state() == objects[:-1]

    adapter.clear()
    assert adapter.scene_state() == []
    assert scene.items() == []
    app.processEvents()


def test_render_adapter_sync_and_unknown_objects_are_safe():
    app = QApplication.instance() or QApplication([])
    scene = QGraphicsScene()
    scene.setSceneRect(QRectF(0, 0, 100, 50))
    adapter = AnnotationRenderAdapter(scene)
    original = {"id": "text-1", "type": "text", "x": 0.1, "y": 0.2, "text": "Old"}
    adapter.replace_objects([original])

    updated = deepcopy(original)
    updated.update(x=0.4, text="New")
    item = adapter.sync_object(updated)

    assert item is not None
    assert item.data(0) == "text-1"
    assert adapter.scene_state() == [updated]
    assert adapter.sync_object({"id": "unknown-1", "type": "missing"}) is None
    assert adapter.scene_state() == [updated]
    app.processEvents()


def test_render_adapter_applies_persisted_line_style_to_strokes():
    app = QApplication.instance() or QApplication([])
    scene = QGraphicsScene()
    scene.setSceneRect(QRectF(0, 0, 100, 50))
    adapter = AnnotationRenderAdapter(scene)

    projected = adapter.replace_objects(
        [
            {
                "id": "line-1",
                "type": "line",
                "x1": 0.1,
                "y1": 0.2,
                "x2": 0.8,
                "y2": 0.7,
                "style": {"line_style": "--"},
            },
            {
                "id": "curve-1",
                "type": "curve",
                "x1": 0.1,
                "y1": 0.2,
                "x2": 0.8,
                "y2": 0.7,
                "control_x": 0.5,
                "control_y": 0.1,
                "style": {"line_style": ":"},
            },
        ]
    )

    assert projected["line-1"].pen().style() == Qt.DashLine
    assert projected["curve-1"].pen().style() == Qt.DotLine
    app.processEvents()


class _FakeSignal:
    def __init__(self):
        self._callbacks = []

    def connect(self, callback):
        self._callbacks.append(callback)

    def emit(self, payload):
        for callback in self._callbacks:
            callback(payload)


class _FakeCanvas:
    def __init__(self):
        self.object_edit_requested = _FakeSignal()
        self.objects = []
        self._signals_blocked = False

    def blockSignals(self, blocked):
        previous = self._signals_blocked
        self._signals_blocked = bool(blocked)
        return previous

    def signalsBlocked(self):
        return self._signals_blocked

    def set_document_objects(self, objects):
        self.objects = deepcopy(objects)


class _FakeEditor(ChartEditorEditSessionMixin):
    def __init__(self, document):
        self._edit_session = EditSession(document)
        self._figure_document = {}
        self._annotation_canvas = _FakeCanvas()
        self._connect_annotation_canvas_edit_session()


def test_edit_session_mixin_routes_annotation_geometry_and_reprojects():
    editor = _FakeEditor(
        {
            "objects": [
                {
                    "id": "text-1",
                    "type": "text",
                    "x": 0.1,
                    "y": 0.2,
                    "text": "Peak",
                }
            ]
        }
    )

    editor._sync_editor_from_session()
    editor._annotation_canvas.object_edit_requested.emit(
        {
            "object_id": "text-1",
            "source": "annotation_canvas",
            "geometry": {"x": 0.4, "y": 0.5},
        }
    )

    assert editor._edit_session.document["objects"][0]["x"] == 0.4
    assert editor._edit_session.document["objects"][0]["y"] == 0.5
    assert editor._figure_document["objects"][0]["x"] == 0.4
    assert editor._annotation_canvas.objects[0]["y"] == 0.5
    assert editor._edit_session.can_undo
    assert editor._annotation_canvas.signalsBlocked() is False


def test_edit_session_mixin_routes_annotation_delete_and_reprojects():
    editor = _FakeEditor(
        {
            "objects": [
                {
                    "id": "text-1",
                    "type": "text",
                    "x": 0.1,
                    "y": 0.2,
                    "text": "Peak",
                }
            ]
        }
    )

    editor._sync_editor_from_session()
    editor._annotation_canvas.object_edit_requested.emit(
        {
            "object_id": "text-1",
            "source": "annotation_canvas",
            "operation": "delete",
        }
    )

    assert editor._edit_session.document["objects"] == []
    assert editor._figure_document["objects"] == []
    assert editor._annotation_canvas.objects == []
    assert editor._edit_session.can_undo
    assert editor._annotation_canvas.signalsBlocked() is False
