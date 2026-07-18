import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from polynexus.gui.origin_export_worker import OriginExportWorker
from polynexus.gui.i18n import tr
from polynexus.gui.widgets.chart_editor import ChartEditor
from polynexus.origin.contracts import ExportRequest, ExportResult


def _app():
    return QApplication.instance() or QApplication([])


class FakeOriginService:
    def __init__(self, result):
        self.result = result
        self.requests = []

    def export(self, request):
        self.requests.append(request)
        return self.result


def test_chart_editor_header_menu_exposes_origin_export(monkeypatch):
    _app()
    calls = []
    monkeypatch.setattr(
        ChartEditor,
        "_export_to_origin",
        lambda editor: calls.append(editor),
    )
    editor = ChartEditor()

    action = editor._header_export_actions.get("origin")
    assert action is not None
    assert action.text() == tr("EDITOR_EXPORT_ORIGIN")
    assert not action.isEnabled()

    editor.set_figure_generator(lambda axis: axis.plot([0, 1], [0, 1]))
    assert action.isEnabled()

    action.trigger()
    assert calls == [editor]
    editor.deleteLater()
    _app().processEvents()


def test_chart_editor_exposes_origin_action_and_builds_request(tmp_path):
    _app()
    editor = ChartEditor()
    editor.set_figure_generator(lambda axis: axis.plot([0, 1], [0, 1]))
    service = FakeOriginService(
        ExportResult.success_result("package", tmp_path / "Origin_Export")
    )
    editor._origin_export_service = service

    assert editor._btn_origin_export.text()
    request = editor._build_origin_export_request(tmp_path)

    assert request.output_root == tmp_path.resolve()
    assert request.document["mode"] == "object"
    editor._show_origin_export_result(service.result)
    assert editor._status_label.text()
    editor.deleteLater()
    _app().processEvents()


def test_chart_editor_origin_request_preserves_gallery_run_root(tmp_path):
    _app()
    editor = ChartEditor()
    editor._source_entry_context = SimpleNamespace(run_root=str(tmp_path / "run-1"))

    request = editor._build_origin_export_request(tmp_path / "out")

    assert request.source_root == (tmp_path / "run-1").resolve()
    editor.deleteLater()
    _app().processEvents()


def test_chart_editor_object_document_requests_editable_origin(tmp_path):
    _app()
    editor = ChartEditor()
    editor._figure_document = {"mode": "object", "objects": []}
    editor._generated_document_mode = False

    request = editor._build_origin_export_request(tmp_path)

    assert request.mode == "editable_origin"
    editor.deleteLater()
    _app().processEvents()


def test_chart_editor_origin_export_does_not_open_directory_dialog(monkeypatch, tmp_path):
    _app()
    editor = ChartEditor()
    editor._source_path = str(tmp_path / "figure.png")
    started = []
    monkeypatch.setattr(
        editor,
        "_choose_origin_output_root",
        lambda: pytest.fail("native Origin export should not open a directory dialog"),
    )
    monkeypatch.setattr(editor, "_start_origin_export", started.append)

    editor._export_to_origin()

    assert len(started) == 1
    editor.deleteLater()
    _app().processEvents()


def test_origin_export_worker_emits_service_result():
    request = ExportRequest(document={}, output_root=".", mode="package")
    result = ExportResult.success_result("package")
    service = FakeOriginService(result)
    worker = OriginExportWorker(service, request)
    results = []
    worker.finished.connect(results.append)

    worker.run()

    assert results == [result]
    assert service.requests == [request]
