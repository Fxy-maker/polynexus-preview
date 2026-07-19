"""Helpers for exported-figure preview and window launching."""

from __future__ import annotations

import csv
import os
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import Qt

from ..core.figure_document import load_figure_document
from .i18n import tr
from .widgets.chart_editor import ChartEditor
from .widgets.chart_viewer import ChartViewer


def normalize_figure_path(filepath, fallback_path: str = "") -> str:
    if isinstance(filepath, bool):
        filepath = None
    return str(filepath or fallback_path or "").strip()


def current_chart_raw_data(result) -> dict[str, Any] | None:
    if result is None:
        return None
    if isinstance(result, dict):
        raw_data = result.get("raw_data")
        return raw_data if isinstance(raw_data, dict) else None
    raw_data = getattr(result, "raw_data", None)
    return raw_data if isinstance(raw_data, dict) else None


@dataclass(frozen=True)
class FigureDataResolution:
    """Normalized table data and provenance for one persisted figure."""

    headers: tuple[str, ...] = ()
    rows: tuple[tuple[Any, ...], ...] = ()
    source_label: str = ""
    error: str = ""


def resolve_figure_data(
    figure_path: str,
    *,
    document: dict[str, Any] | None = None,
    entry: object | None = None,
    fallback_data: object | None = None,
) -> FigureDataResolution:
    """Resolve data belonging to a persisted figure without guessing across figures."""

    payload = document if isinstance(document, dict) else {}
    sources = payload.get("data_sources")
    if isinstance(sources, list) and sources:
        source = _selected_figure_data_source(payload, sources)
        if source is None:
            return FigureDataResolution(error="source_unavailable")
        return _resolve_figure_data_source(figure_path, entry, source, payload)

    fallback = _fallback_data_resolution(fallback_data)
    if fallback is not None:
        return fallback
    return FigureDataResolution(error="source_unavailable")


def _selected_figure_data_source(
    document: dict[str, Any], sources: list[object]
) -> dict[str, Any] | None:
    source_map = {
        str(source.get("id") or ""): source
        for source in sources
        if isinstance(source, dict) and str(source.get("id") or "")
    }
    for figure_object in document.get("objects", []):
        if not isinstance(figure_object, dict):
            continue
        data_ref = str(figure_object.get("data_ref") or "")
        if data_ref and isinstance(source_map.get(data_ref), dict):
            return source_map[data_ref]
    return next((source for source in sources if isinstance(source, dict)), None)


def _resolve_figure_data_source(
    figure_path: str,
    entry: object | None,
    source: dict[str, Any],
    document: dict[str, Any],
) -> FigureDataResolution:
    kind = str(source.get("kind") or "").strip().lower()
    if kind == "inline":
        return _inline_data_resolution(source, document)

    path_text = str(source.get("path") or "").strip()
    if not path_text:
        return FigureDataResolution(error="source_missing")
    path = _resolve_figure_source_path(figure_path, entry, path_text, source)
    if not path.is_file():
        return FigureDataResolution(error="source_missing")
    if kind not in {"csv", "tsv", ""}:
        return FigureDataResolution(error="source_unreadable")
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle, delimiter="\t" if kind == "tsv" else ",")
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error):
        return FigureDataResolution(error="source_unreadable")
    if not rows or not rows[0]:
        return FigureDataResolution(error="source_unreadable")
    headers = tuple(str(value) for value in rows[0])
    values = tuple(tuple(value for value in row) for row in rows[1:])
    return FigureDataResolution(headers, values, str(path), "")


def _resolve_figure_source_path(
    figure_path: str,
    entry: object | None,
    path_text: str,
    source: dict[str, Any],
) -> Path:
    candidate = Path(path_text)
    if candidate.is_absolute():
        return candidate.resolve()
    path_kind = str(source.get("path_kind") or "").strip().lower()
    run_root = str(getattr(entry, "run_root", "") or "").strip()
    if path_kind == "run_relative" and run_root:
        return (Path(run_root).resolve() / candidate).resolve()
    return (Path(figure_path).resolve().parent / candidate).resolve()


def _inline_data_resolution(
    source: dict[str, Any], document: dict[str, Any]
) -> FigureDataResolution:
    data = source.get("data")
    if not isinstance(data, dict):
        return FigureDataResolution(error="source_unreadable")
    selected_object = next(
        (
            item
            for item in document.get("objects", [])
            if isinstance(item, dict)
            and str(item.get("data_ref") or "") == str(source.get("id") or "")
        ),
        {},
    )
    preferred = [
        str(selected_object.get(key) or "")
        for key in ("x_column", "y_column")
        if str(selected_object.get(key) or "") in data
    ]
    headers = tuple(preferred or [str(key) for key in data])
    columns = [data.get(header) for header in headers]
    if not columns or not all(isinstance(column, (list, tuple)) for column in columns):
        return FigureDataResolution(error="source_unreadable")
    row_count = max((len(column) for column in columns), default=0)
    rows = tuple(
        tuple(column[index] if index < len(column) else "" for column in columns)
        for index in range(row_count)
    )
    return FigureDataResolution(headers, rows, str(source.get("id") or "inline"), "")


def _fallback_data_resolution(data: object | None) -> FigureDataResolution | None:
    if not isinstance(data, dict) or not data:
        return None
    headers = tuple(str(key) for key in data)
    columns = [data[key] for key in data]
    if not all(isinstance(column, (list, tuple)) for column in columns):
        return None
    row_count = max((len(column) for column in columns), default=0)
    rows = tuple(
        tuple(column[index] if index < len(column) else "" for column in columns)
        for index in range(row_count)
    )
    return FigureDataResolution(headers, rows, "fallback", "")


@dataclass(frozen=True)
class FigureEditorOpenRequest:
    figure_path: str
    entry: object | None
    force_static: bool


_STATIC_ONLY_RECIPE_FUNCTIONS = {
    "fig_temperature_overview",
    "fig_strain_overview",
    "fig_static_overview",
    "fig_v2_temperature_parameters",
    "fig_t3_structure_evolution",
    "fig_v4_avrami",
}


def chart_viewer_status_line(message, level: str = "info", *, timestamp: datetime | None = None) -> str:
    ts = timestamp or datetime.now()
    ts_text = ts.strftime("%H:%M:%S") if hasattr(ts, "strftime") else str(ts)
    color_map = {
        "success": "#16a34a",
        "warning": "#d97706",
        "error": "#dc2626",
        "info": "#2563eb",
    }
    color = color_map.get(level, color_map["info"])
    return f'[{ts_text}] <span style="color:{color};">{message}</span>'


def show_chart_preview(preview_widget, figure_path: str, *, view_button=None, entry=None) -> str:
    path = normalize_figure_path(figure_path)
    if not path or preview_widget is None:
        return path
    if view_button is not None:
        view_button.setEnabled(True)
    if entry is not None and hasattr(preview_widget, "set_entry_context"):
        preview_widget.set_entry_context(entry)
    preview_widget.setVisible(True)
    preview_widget.load_figure(path)
    return path


def open_chart_viewer(
    figure_path: str,
    raw_data=None,
    *,
    entry=None,
    viewer=None,
    viewer_factory: Callable[[], ChartViewer] = ChartViewer,
    edit_requested_handler=None,
    status_message_handler=None,
):
    path = normalize_figure_path(figure_path)
    if not path:
        return viewer
    if viewer is None:
        viewer = viewer_factory()
        if edit_requested_handler is not None:
            viewer.edit_requested.connect(edit_requested_handler)
        if status_message_handler is not None:
            viewer.status_message.connect(status_message_handler)
    viewer.setWindowTitle(tr("FIGURE_VIEWER_WINDOW", os.path.basename(path)))
    document_path = normalize_figure_path(getattr(entry, "document_path", ""))
    document = load_figure_document(document_path or path)
    data_resolution = resolve_figure_data(
        path,
        document=document,
        entry=entry,
        fallback_data=raw_data,
    )
    try:
        viewer.load_figure(
            path,
            raw_data,
            entry=entry,
            data_resolution=data_resolution,
        )
    except TypeError:
        viewer.load_figure(path, raw_data)
    viewer.resize(1180, 820)
    viewer.show()
    viewer.raise_()
    viewer.activateWindow()
    return viewer


def open_convergence_viewer(
    current_viewer,
    *,
    viewer_factory: Callable[[], object],
    closed_handler=None,
    warning_handler=None,
    critical_handler=None,
    logger=None,
):
    if current_viewer is not None:
        try:
            raise_view = getattr(current_viewer, "raise_", None)
            activate_view = getattr(current_viewer, "activateWindow", None)
            if callable(raise_view):
                raise_view()
            if callable(activate_view):
                activate_view()
        except RuntimeError:
            pass
        return current_viewer

    try:
        viewer = viewer_factory(parent=None)
        viewer.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        if closed_handler is not None:
            viewer.destroyed.connect(closed_handler)
        viewer.show()
        return viewer
    except SystemExit as exc:
        if warning_handler is not None:
            warning_handler(exc)
        return None
    except Exception as exc:
        if critical_handler is not None:
            critical_handler(exc)
        if logger is not None:
            logger.warning("Failed to open convergence dashboard.", exc_info=True)
        return None


def open_chart_editor(
    figure_path: str,
    *,
    entry=None,
    force_static: bool = False,
    editor=None,
    editor_factory: Callable[[], ChartEditor] = ChartEditor,
    saved_handler=None,
):
    request = resolve_chart_editor_entry(
        figure_path,
        entry=entry,
        force_static=force_static,
    )
    path = request.figure_path
    if not path:
        return editor
    if editor is None:
        editor = editor_factory()
        if saved_handler is not None:
            editor.figure_saved.connect(saved_handler)
    title = str(getattr(request.entry, "title", "") or "").strip() or os.path.basename(path)
    editor.setWindowTitle(tr("FIGURE_SETTINGS_WINDOW", title))
    if request.entry is not None and hasattr(editor, "set_source_figure_entry"):
        editor.set_source_figure_entry(request.entry, force_static=request.force_static)
    elif request.entry is not None and hasattr(editor, "set_source_figure"):
        try:
            editor.set_source_figure(
                path,
                source_entry_context=request.entry,
                force_static=request.force_static,
            )
        except TypeError:
            editor.set_source_figure(path)
    else:
        editor.set_source_figure(path)
    editor.resize(1000, 650)
    editor.show()
    return editor


def refresh_saved_figure_in_gallery(gallery, figure_path: str) -> bool:
    path = normalize_figure_path(figure_path)
    if not path or gallery is None or not hasattr(gallery, "figure_paths"):
        return False

    existing_paths = list(gallery.figure_paths())
    target = os.path.normcase(os.path.abspath(path))
    exists_in_gallery = any(
        os.path.normcase(os.path.abspath(existing_path)) == target
        for existing_path in existing_paths
    )

    if exists_in_gallery:
        gallery.refresh_figure(path)
    else:
        gallery.load_files(existing_paths + [path])

    gallery.select_figure(path, emit=False)
    return exists_in_gallery


def resolve_chart_editor_entry(
    figure_path: str,
    *,
    entry=None,
    force_static: bool = False,
) -> FigureEditorOpenRequest:
    entry_path = normalize_figure_path(
        getattr(entry, "editable_path", "")
        or getattr(entry, "primary_path", "")
        or getattr(entry, "preview_path", ""),
    )
    path = normalize_figure_path(figure_path, entry_path)
    if not path:
        return FigureEditorOpenRequest("", entry, bool(force_static))

    manifest_document_path = normalize_figure_path(
        getattr(entry, "document_path", "")
    )
    capability_report = getattr(entry, "capability_report", None)
    if manifest_document_path and capability_report is not None:
        load_figure_document(manifest_document_path)
        if isinstance(capability_report, dict):
            editing_mode = str(capability_report.get("editing_mode") or "")
            object_editing = bool(capability_report.get("object_editing"))
        else:
            editing_mode = str(getattr(capability_report, "editing_mode", "") or "")
            object_editing = bool(
                getattr(capability_report, "object_editing", False)
            )
        manifest_object_mode = editing_mode == "object" and object_editing
        return FigureEditorOpenRequest(
            path,
            entry,
            bool(force_static) or not manifest_object_mode,
        )

    document = load_figure_document(path)
    entry_state = str(getattr(entry, "state", "") or "").strip().lower()
    entry_figure_id = str(getattr(entry, "figure_id", "") or "").strip()
    document_mode = str(document.get("mode") or "").strip().lower()
    document_figure_id = str(document.get("figure_id", "") or "").strip()

    resolved_force_static = bool(force_static)
    if entry is not None and entry_state and entry_state != "object_editing":
        resolved_force_static = True
    if document_mode != "object":
        resolved_force_static = True
    if entry_figure_id and not document_figure_id:
        resolved_force_static = True
    if entry_figure_id and document_figure_id and entry_figure_id != document_figure_id:
        resolved_force_static = True
    if _document_requires_static_fallback(document):
        resolved_force_static = True

    return FigureEditorOpenRequest(path, entry, resolved_force_static)


def _document_requires_static_fallback(document: dict) -> bool:
    if not isinstance(document, dict) or not document:
        return True

    style = document.get("style", {})
    if isinstance(style, dict):
        panels = style.get("panels", [])
        if isinstance(panels, (list, tuple)) and len(panels) > 1:
            return True

    recipe = document.get("recipe", {})
    if isinstance(recipe, dict):
        function_name = str(recipe.get("function", "") or "").strip().lower()
        if function_name in _STATIC_ONLY_RECIPE_FUNCTIONS:
            return True

    return False
