"""High-level Origin Python adapter with a lazy optional import."""

from __future__ import annotations

import platform
import re
import math
from pathlib import Path
from typing import Any, Callable, Mapping

from .capability_probe import OriginCapabilityProbe
from .contracts import ExportRequest, ExportResult
from .mapping import map_figure_document
from .path_resolution import resolve_source_path


_ORIGIN_SYMBOLS = {
    "alpha": "α",
    "beta": "β",
    "gamma": "γ",
    "delta": "δ",
    "epsilon": "ε",
    "eta": "η",
    "kappa": "κ",
    "lambda": "λ",
    "mu": "μ",
    "nu": "ν",
    "pi": "π",
    "rho": "ρ",
    "sigma": "σ",
    "tau": "τ",
    "phi": "φ",
    "chi": "χ",
    "psi": "ψ",
    "omega": "ω",
    "times": "×",
    "cdot": "·",
    "pm": "±",
    "infty": "∞",
}
_SUPERSCRIPT = str.maketrans("0123456789+-=()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ")
_SUBSCRIPT = str.maketrans("0123456789+-=()", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎")


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
                facade.add_plot(
                    plot.x_column,
                    plot.y_column,
                    dict(plot.style),
                    data_ref=plot.data_ref,
                    name=plot.name,
                )
            configure_figure = getattr(facade, "configure_figure", None)
            x_scale, y_scale = _document_axis_scales(request.document)
            if callable(configure_figure):
                configure_figure(
                    title=model.title,
                    xlabel=model.xlabel,
                    ylabel=model.ylabel,
                    x_scale=x_scale,
                    y_scale=y_scale,
                )
            else:
                configure_axes = getattr(facade, "configure_axes", None)
                if callable(configure_axes):
                    configure_axes(x_scale=x_scale, y_scale=y_scale)
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
        self._first_sheet = None
        self._sheet = None
        self._sheets: dict[str, Any] = {}
        self._dataframes: dict[str, Any] = {}
        self._current_source_id = ""
        self._graphs: list[Any] = []

    def new_book(self, kind: str = "w") -> Any:
        self._first_sheet = self._module.new_sheet(kind, lname="PolyNexus")
        get_book = getattr(self._first_sheet, "get_book", None)
        self._book = get_book() if callable(get_book) else self._first_sheet
        self._sheet = None
        self._sheets.clear()
        self._dataframes.clear()
        self._current_source_id = ""
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
        if self._book is None or not self._sheets:
            first_sheet = self._first_sheet
            if first_sheet is None:
                first_sheet = self.new_book("w")
            self._sheet = first_sheet
        else:
            add_sheet = getattr(self._book, "add_sheet", None)
            if not callable(add_sheet):
                raise RuntimeError("Origin workbook cannot create source worksheets")
            self._sheet = add_sheet(str(name))
        source_id = str(name or "").strip()
        if not source_id:
            raise ValueError("Origin data source id cannot be empty")
        self._sheets[source_id] = self._sheet
        self._current_source_id = source_id
        return self._sheet

    def from_csv(self, path: Path) -> None:
        import pandas as pd

        if self._sheet is None or not self._current_source_id:
            raise RuntimeError("Origin worksheet has not been selected")
        frame = pd.read_csv(path)
        self._dataframes[self._current_source_id] = frame
        self._sheet.from_df(frame)

    def add_plot(
        self,
        x_column: str,
        y_column: str,
        style: dict[str, Any],
        *,
        data_ref: str = "",
        name: str = "",
    ) -> None:
        sheet, frame = self._source_for_plot(data_ref)
        if x_column not in frame.columns or y_column not in frame.columns:
            raise KeyError(f"plot columns not found: {x_column}, {y_column}")
        set_label = getattr(sheet, "set_label", None)
        if name and callable(set_label):
            set_label(y_column, str(name))
        graph = (
            self._graphs[-1]
            if self._graphs
            else self._module.new_graph(template="Line")
        )
        layer = graph[0]
        plot = layer.add_plot(
            sheet,
            colx=int(frame.columns.get_loc(x_column)),
            coly=int(frame.columns.get_loc(y_column)),
        )
        _apply_plot_style(plot, style)
        layer.rescale()
        if not self._graphs:
            self._graphs.append(graph)

    def _source_for_plot(self, data_ref: str) -> tuple[Any, Any]:
        source_id = str(data_ref or "").strip()
        if source_id:
            sheet = self._sheets.get(source_id)
            frame = self._dataframes.get(source_id)
            if sheet is None or frame is None:
                raise KeyError(f"Origin data source is not loaded: {source_id}")
            return sheet, frame
        if self._sheet is None:
            raise RuntimeError("Origin worksheet has not been created")
        if isinstance(self._dataframes, dict):
            if self._current_source_id and self._current_source_id in self._dataframes:
                return self._sheet, self._dataframes[self._current_source_id]
            if len(self._dataframes) == 1:
                source_id, frame = next(iter(self._dataframes.items()))
                return self._sheets.get(source_id, self._sheet), frame
            raise KeyError("Origin plot requires a data_ref when multiple sources are loaded")
        if not self._dataframes:
            raise RuntimeError("Origin worksheet data has not been loaded")
        return self._sheet, self._dataframes[-1]

    def configure_figure(
        self,
        *,
        title: str = "",
        xlabel: str = "",
        ylabel: str = "",
        x_scale: str,
        y_scale: str,
    ) -> None:
        if not self._graphs:
            return
        graph = self._graphs[-1]
        layer = graph[0]
        if title:
            try:
                graph.lname = str(title)
            except (AttributeError, TypeError, ValueError):
                pass
        axis = getattr(layer, "axis", None)
        if callable(axis):
            if xlabel:
                axis("x").title = _origin_display_label(xlabel)
            if ylabel:
                axis("y").title = _origin_display_label(ylabel)
        origin_x_scale = _origin_axis_scale(x_scale)
        origin_y_scale = _origin_axis_scale(y_scale)
        if origin_x_scale:
            layer.xscale = origin_x_scale
        if origin_y_scale:
            layer.yscale = origin_y_scale
        layer.rescale()

    def configure_axes(self, *, x_scale: str, y_scale: str) -> None:
        self.configure_figure(x_scale=x_scale, y_scale=y_scale)

    def save(self, path: Path) -> None:
        save = getattr(self._module, "save", None)
        if callable(save):
            save(str(path))
            return
        if self._graphs:
            self._graphs[-1].save(str(path))
            return
        raise RuntimeError("Origin Python integration did not create a graph")


def _origin_display_label(value: str) -> str:
    """Convert Matplotlib mathtext labels into readable Origin text."""

    text = str(value or "").strip()
    if not text:
        return ""
    text = re.sub(
        r"\\(?:mathrm|operatorname|text)\s*\{([^{}]*)\}",
        r"\1",
        text,
    )
    text = re.sub(r"\\(?:left|right)\b", "", text)
    text = re.sub(
        r"\^\{([^{}]+)\}",
        lambda match: match.group(1).translate(_SUPERSCRIPT),
        text,
    )
    text = re.sub(
        r"_\{([^{}]+)\}",
        lambda match: match.group(1).translate(_SUBSCRIPT),
        text,
    )
    text = re.sub(
        r"\^([A-Za-z0-9+\-=()])",
        lambda match: match.group(1).translate(_SUPERSCRIPT),
        text,
    )
    text = re.sub(
        r"_([A-Za-z0-9+\-=()])",
        lambda match: match.group(1).translate(_SUBSCRIPT),
        text,
    )
    text = re.sub(
        r"\\([A-Za-z]+)",
        lambda match: _ORIGIN_SYMBOLS.get(match.group(1), match.group(1)),
        text,
    )
    text = text.replace("$", "").replace("{", "").replace("}", "")
    return " ".join(text.split())


def _apply_plot_style(plot: Any, style: Mapping[str, Any] | None) -> None:
    if plot is None or not isinstance(style, Mapping):
        return
    color = str(style.get("color") or "").strip()
    if color:
        try:
            plot.color = color
        except (AttributeError, TypeError, ValueError):
            pass
    try:
        line_width = float(style.get("line_width"))
    except (TypeError, ValueError, OverflowError):
        line_width = 0.0
    if math.isfinite(line_width) and line_width > 0:
        set_cmd = getattr(plot, "set_cmd", None)
        if callable(set_cmd):
            try:
                # Origin's LabTalk -w unit is 1/500 of a point (1000 = 2 pt).
                set_cmd(f"-w {int(round(line_width * 500))}")
            except (AttributeError, TypeError, ValueError):
                pass
        elif hasattr(type(plot), "width"):
            try:
                plot.width = line_width
            except (AttributeError, TypeError, ValueError):
                pass


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


def _document_axis_scales(document: Mapping[str, Any]) -> tuple[str, str]:
    layout = document.get("layout", {}) if isinstance(document, Mapping) else {}
    panels = layout.get("panels", []) if isinstance(layout, Mapping) else []
    panel = panels[0] if panels and isinstance(panels[0], Mapping) else {}
    x_axis = panel.get("x_axis", {}) if isinstance(panel, Mapping) else {}
    y_axis = panel.get("y_axis", {}) if isinstance(panel, Mapping) else {}
    x_scale = str(x_axis.get("scale") or "").strip().lower()
    y_scale = str(y_axis.get("scale") or "").strip().lower()
    return x_scale, y_scale


def _origin_axis_scale(value: str) -> str:
    scale = str(value or "").strip().lower()
    if scale == "log":
        return "log10"
    if scale in {"linear", "log10", "ln", "log2"}:
        return scale
    return ""
