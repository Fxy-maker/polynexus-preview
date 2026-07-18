"""High-level Origin Python adapter with a lazy optional import."""

from __future__ import annotations

import platform
import re
from pathlib import Path
from typing import Any, Callable

from .capability_probe import OriginCapabilityProbe
from .contracts import ExportRequest, ExportResult
from .mapping import map_figure_document
from .path_resolution import resolve_source_path


class OriginProAdapter:
    adapter_id = "originpro"
    priority = 100

    def __init__(
        self,
        *,
        originpro_factory: Callable[[], Any] | None = None,
        available: Callable[[], bool] | None = None,
    ) -> None:
        self._factory = originpro_factory or _default_originpro_factory
        self._available = available or (
            (lambda: True) if originpro_factory is not None else _default_available
        )

    def can_handle(self, request: ExportRequest) -> bool:
        if request.mode != "editable_origin" or platform.system() != "Windows":
            return False
        try:
            return bool(self._available())
        except Exception:
            return False

    def export(self, request: ExportRequest) -> ExportResult:
        if not self.can_handle(request):
            return ExportResult(
                status="unavailable",
                adapter_id=self.adapter_id,
                message="The high-level Origin Python integration is unavailable",
                recoverable=True,
            )

        model = map_figure_document(request.document)
        facade = None
        book_created = False
        try:
            facade = self._factory()
            facade.new_book("w")
            book_created = True
            if request.allow_open_origin:
                facade.show()
            for source in model.sources:
                source_path = resolve_source_path(source.path, request)
                if not source_path.is_file():
                    raise FileNotFoundError(f"data source does not exist: {source.path}")
                facade.add_sheet(source.source_id)
                facade.from_csv(source_path)
            for plot in model.plots:
                facade.add_plot(plot.x_column, plot.y_column, dict(plot.style))
            if request.allow_open_origin:
                facade.activate()
            request.output_root.mkdir(parents=True, exist_ok=True)
            project_path = _next_project_path(
                request.output_root / f"{_safe_name(model.figure_id)}.opju"
            )
            facade.save(project_path)
        except ImportError as exc:
            return ExportResult(
                status="unavailable",
                adapter_id=self.adapter_id,
                message=str(exc),
                recoverable=True,
            )
        except Exception as exc:
            return ExportResult(
                status=("partial" if book_created else "unavailable"),
                adapter_id=self.adapter_id,
                warnings=model.warnings,
                message=str(exc),
                recoverable=not book_created,
            )

        return ExportResult.success_result(
            self.adapter_id,
            Path(project_path),
            warnings=model.warnings,
            message="Exported to Origin using the Python integration",
        )


class _OriginProFacade:
    """Small compatibility facade around the installed originpro package."""

    def __init__(self, module: Any) -> None:
        self._module = module
        self._book = None
        self._sheet = None
        self._dataframes: list[Any] = []
        self._graphs: list[Any] = []

    def new_book(self, kind: str = "w") -> Any:
        self._book = self._module.new_sheet(kind, lname="PolyNexus")
        return self._book

    def show(self) -> None:
        set_show = getattr(self._module, "set_show", None)
        if not callable(set_show):
            raise RuntimeError("Origin Python integration cannot show the application")
        set_show(True)

    def activate(self) -> None:
        if self._graphs:
            activate = getattr(self._graphs[-1], "activate", None)
            if callable(activate):
                activate()
                return
        execute = getattr(self._module, "lt_exec", None)
        if callable(execute):
            execute("win -a;")
            return
        self.show()

    def add_sheet(self, name: str) -> Any:
        if self._book is None:
            self.new_book("w")
        self._sheet = self._book
        return self._sheet

    def from_csv(self, path: Path) -> None:
        import pandas as pd

        if self._sheet is None:
            raise RuntimeError("Origin worksheet has not been created")
        frame = pd.read_csv(path)
        self._dataframes.append(frame)
        self._sheet.from_df(frame)

    def add_plot(self, x_column: str, y_column: str, style: dict[str, Any]) -> None:
        if self._sheet is None or not self._dataframes:
            raise RuntimeError("Origin worksheet data has not been loaded")
        frame = self._dataframes[-1]
        if x_column not in frame.columns or y_column not in frame.columns:
            raise KeyError(f"plot columns not found: {x_column}, {y_column}")
        graph = self._module.new_graph(template="Line")
        layer = graph[0]
        layer.add_plot(
            self._sheet,
            colx=int(frame.columns.get_loc(x_column)),
            coly=int(frame.columns.get_loc(y_column)),
        )
        layer.rescale()
        self._graphs.append(graph)

    def save(self, path: Path) -> None:
        save = getattr(self._module, "save", None)
        if callable(save):
            save(str(path))
            return
        if self._graphs:
            self._graphs[-1].save(str(path))
            return
        raise RuntimeError("Origin Python integration did not create a graph")


def _default_available() -> bool:
    report = OriginCapabilityProbe().probe()
    return report.installed and report.originpro_available


def _default_originpro_factory() -> _OriginProFacade:
    import originpro

    return _OriginProFacade(originpro)


def _next_project_path(base: Path) -> Path:
    if not base.exists():
        return base
    index = 2
    while True:
        candidate = base.with_name(f"{base.stem}_{index}{base.suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "figure"))
    return cleaned.strip("._") or "figure"
