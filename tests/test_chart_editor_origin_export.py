import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from polynexus.gui.origin_export_worker import OriginExportWorker
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
