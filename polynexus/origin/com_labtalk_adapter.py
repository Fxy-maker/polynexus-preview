"""Compatibility adapter using Origin's COM server and bounded LabTalk."""

from __future__ import annotations

import platform
import re
from typing import Any, Callable

from .capability_probe import ORIGIN_COM_PROGIDS, OriginCapabilityProbe
from .contracts import ExportRequest, ExportResult
from .mapping import map_figure_document
from .path_resolution import resolve_source_path


class ComLabTalkAdapter:
    adapter_id = "com_labtalk"
    priority = 80

    def __init__(
        self,
        *,
        app_factory: Callable[[], Any] | None = None,
        com_available: Callable[[], bool] | None = None,
    ) -> None:
        self._app_factory = app_factory or _default_app_factory
        self._com_available = com_available or _default_com_available

    def can_handle(self, request: ExportRequest) -> bool:
        if request.mode != "editable_origin" or platform.system() != "Windows":
            return False
        try:
            return bool(self._com_available())
        except Exception:
            return False

    def export(self, request: ExportRequest) -> ExportResult:
        if not self.can_handle(request):
            return ExportResult(
                status="unavailable",
                adapter_id=self.adapter_id,
                message="COM/LabTalk is unavailable for this request",
                recoverable=True,
            )

        model = map_figure_document(request.document)
        app = None
        commands_started = False
        try:
            app = self._app_factory()
            if app is None:
                return ExportResult(
                    status="unavailable",
                    adapter_id=self.adapter_id,
                    message="Origin COM server could not be opened",
                    recoverable=True,
                )
            request.output_root.mkdir(parents=True, exist_ok=True)
            project_path = request.output_root / f"{_safe_name(model.figure_id)}.opju"
            self._execute(app, "newbook;")
            commands_started = True
            for source in model.sources:
                source_path = resolve_source_path(source.path, request)
                if not source_path.is_file():
                    raise FileNotFoundError(f"data source does not exist: {source.path}")
                self._execute(
                    app,
                    f'impCSV fname:="{_labtalk_quote(str(source_path))}";',
                )
            for plot in model.plots:
                self._execute(
                    app,
                    "plotxy "
                    f'"{_labtalk_quote(plot.x_column)}" '
                    f'"{_labtalk_quote(plot.y_column)}";',
                )
            if model.title:
                self._execute(app, f'label -s "{_labtalk_quote(model.title)}";')
            app.Save(str(project_path))
        except ImportError as exc:
            return ExportResult(
                status="unavailable",
                adapter_id=self.adapter_id,
                message=str(exc),
                recoverable=True,
            )
        except Exception as exc:
            return ExportResult(
                status=("partial" if commands_started else "unavailable"),
                adapter_id=self.adapter_id,
                warnings=model.warnings,
                message=str(exc),
                recoverable=not commands_started,
            )

        return ExportResult.success_result(
            self.adapter_id,
            project_path,
            warnings=model.warnings,
            message="Exported to Origin using COM compatibility mode",
        )

    @staticmethod
    def _execute(app: Any, command: str) -> None:
        executor = getattr(app, "LTExec", None) or getattr(app, "lt_exec", None)
        if not callable(executor):
            raise AttributeError("Origin COM object does not expose LabTalk execution")
        executor(command)


def _default_com_available() -> bool:
    return OriginCapabilityProbe().probe().com_available


def _default_app_factory() -> Any:
    import win32com.client

    last_error: Exception | None = None
    for progid in ORIGIN_COM_PROGIDS:
        try:
            return win32com.client.Dispatch(progid)
        except Exception as exc:
            last_error = exc
    raise RuntimeError("Unable to connect to an Origin COM server") from last_error


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "figure"))
    return cleaned.strip("._") or "figure"


def _labtalk_quote(value: str) -> str:
    return str(value).replace('"', '""')
