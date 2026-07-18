"""Qt worker boundary for potentially blocking Origin automation."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from ..origin.contracts import ExportResult


class OriginExportWorker(QObject):
    finished = Signal(object)

    def __init__(self, service, request):
        super().__init__()
        self._service = service
        self._request = request

    @Slot()
    def run(self):
        try:
            result = self._service.export(self._request)
        except Exception as exc:  # pragma: no cover - defensive thread boundary
            result = ExportResult(
                status="failed",
                adapter_id="worker",
                message=str(exc),
                recoverable=True,
            )
        self.finished.emit(result)
