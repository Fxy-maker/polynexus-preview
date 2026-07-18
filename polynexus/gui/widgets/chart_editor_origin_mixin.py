"""Chart Editor action and worker lifecycle for optional Origin export."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QFileDialog, QPushButton

from ...core.figure_document import normalize_figure_document
from ...origin.contracts import ExportRequest, ExportResult
from ..i18n import tr
from ..origin_export_worker import OriginExportWorker


class ChartEditorOriginMixin:
    def _build_origin_export_control(self, form) -> None:
        self._btn_origin_export = QPushButton(tr("EDITOR_EXPORT_ORIGIN"))
        self._btn_origin_export.setObjectName("origin_export_btn")
        self._btn_origin_export.setAccessibleName(tr("EDITOR_EXPORT_ORIGIN"))
        self._btn_origin_export.clicked.connect(self._export_to_origin)
        form.addRow(self._btn_origin_export)

    def _origin_export_service_instance(self):
        service = getattr(self, "_origin_export_service", None)
        if service is None:
            from ...origin.service import default_origin_export_service

            service = default_origin_export_service()
            self._origin_export_service = service
        return service

    def _choose_origin_output_root(self) -> str:
        return QFileDialog.getExistingDirectory(
            self,
            tr("EDITOR_EXPORT_ORIGIN_SELECT_DIR"),
            str(self._target_path or self._source_path or ""),
        )

    def _build_origin_export_request(self, output_root) -> ExportRequest:
        document = normalize_figure_document(
            deepcopy(self._figure_document)
            if isinstance(self._figure_document, dict)
            else {}
        )
        source_root = str(
            getattr(self._source_entry_context, "run_root", "") or ""
        ).strip()
        return ExportRequest(
            document=document,
            figure_path=Path(self._source_path) if self._source_path else None,
            source_root=Path(source_root) if source_root else None,
            output_root=Path(output_root),
            mode=(
                "editable_origin"
                if self._generated_document_mode
                else "visual_fidelity"
            ),
            allow_open_origin=True,
        )

    def _export_to_origin(self) -> None:
        if getattr(self, "_origin_export_thread", None) is not None:
            return
        output_root = self._choose_origin_output_root()
        if not output_root:
            return
        self._start_origin_export(self._build_origin_export_request(output_root))

    def _start_origin_export(self, request: ExportRequest) -> None:
        thread = QThread(self)
        worker = OriginExportWorker(self._origin_export_service_instance(), request)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._show_origin_export_result)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._origin_export_finished)
        self._origin_export_thread = thread
        self._origin_export_worker = worker
        self._btn_origin_export.setEnabled(False)
        thread.start()

    def _origin_export_finished(self) -> None:
        self._origin_export_thread = None
        self._origin_export_worker = None
        self._sync_origin_export_enabled()

    def _sync_origin_export_enabled(self) -> None:
        active = getattr(self, "_origin_export_thread", None) is not None
        has_document = self._has_origin_export_document()
        enabled = bool(has_document and not active)
        if hasattr(self, "_btn_origin_export"):
            self._btn_origin_export.setEnabled(enabled)
        action = getattr(self, "_header_export_actions", {}).get("origin")
        if action is not None:
            action.setEnabled(enabled)

    def _has_origin_export_document(self) -> bool:
        return bool(
            self._source_path
            or getattr(self, "_fig_generator", None) is not None
            or self._generated_document_mode
            or self._static_file_mode
            or self._figure_document
        )

    def _show_origin_export_result(self, result: ExportResult) -> None:
        if result.status == "success":
            key_by_adapter = {
                "originpro": "EDITOR_EXPORT_ORIGIN_PYTHON_DONE",
                "com_labtalk": "EDITOR_EXPORT_ORIGIN_COM_DONE",
                "package": "EDITOR_EXPORT_ORIGIN_PACKAGE_DONE",
            }
            message = tr(key_by_adapter.get(result.adapter_id, "EDITOR_EXPORT_ORIGIN_PACKAGE_DONE"))
        elif result.status == "partial":
            message = tr("EDITOR_EXPORT_ORIGIN_PARTIAL")
        elif result.status == "unavailable":
            message = tr("EDITOR_EXPORT_ORIGIN_UNAVAILABLE")
        else:
            message = tr("EDITOR_EXPORT_ORIGIN_FAILED")
        if result.message:
            message = f"{message}: {result.message}"
        if result.warnings:
            message = f"{message} | " + "; ".join(result.warnings)
        self._status_label.setText(message)

    def retranslate_origin_export(self) -> None:
        if hasattr(self, "_btn_origin_export"):
            self._btn_origin_export.setText(tr("EDITOR_EXPORT_ORIGIN"))
            self._btn_origin_export.setAccessibleName(tr("EDITOR_EXPORT_ORIGIN"))
