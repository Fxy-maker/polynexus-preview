"""Pure helpers for selecting and scanning exported plot figures."""

from __future__ import annotations

import os
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from ..core.figure_assets import discover_figure_asset
from ..core.figure_document import OBJECT_MODE, STATIC_BACKGROUND_MODE, load_figure_document


DEFAULT_FIGURE_EXTENSIONS: tuple[str, ...] = (".svg", ".png", ".pdf", ".jpg", ".jpeg")
FIGURE_SUBDIR_HINTS: tuple[str, ...] = ("figures", "summary", "per_frame")
FIGURE_CATEGORY_ALL = "all"
FIGURE_CATEGORY_SERIES_OVERVIEW = "series_overview"
FIGURE_CATEGORY_PER_FRAME = "per_frame_results"
FIGURE_CATEGORY_OTHER_EXPORTS = "other_exports"
FIGURE_STATE_OBJECT = "object_editing"
FIGURE_STATE_STATIC = "static_background"
FIGURE_STATE_UNLINKED_EXPORT = "unlinked_export"


@dataclass(frozen=True)
class FigureGalleryAsset:
    format: str
    label: str
    role: str
    path: str


@dataclass(frozen=True)
class FigureGalleryEntry:
    figure_id: str
    title: str
    category: str
    state: str
    preview_path: str
    primary_path: str
    editable_path: str
    document_mode: str
    asset_paths: tuple[str, ...]
    assets: tuple[FigureGalleryAsset, ...]


@dataclass(frozen=True)
class PlotGallerySelection:
    selected_figure_id: str = ""
    selected_path: str = ""
    matched_preferred: bool = False
    emit_preview: bool = False


def collect_plot_figure_paths(
    output_dir: str,
    *,
    extensions: Iterable[str] = DEFAULT_FIGURE_EXTENSIONS,
    preferred_paths: Iterable[str] | None = None,
) -> list[str]:
    root_text = str(output_dir or "").strip()
    if not root_text:
        return []

    root = Path(root_text)
    if not root.exists():
        return []

    allowed_extensions = {str(ext).lower() for ext in extensions}
    preferred = _existing_figure_paths(preferred_paths or (), allowed_extensions)

    discovered = sorted(
        str(path.resolve())
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in allowed_extensions
        and any(part.lower() in FIGURE_SUBDIR_HINTS for part in path.parts)
    )
    root_level = sorted(
        str(path.resolve())
        for path in root.iterdir()
        if path.is_file() and path.suffix.lower() in allowed_extensions
    )

    merged: list[str] = []
    seen: set[str] = set()
    for candidate in [*preferred, *discovered, *root_level]:
        norm = os.path.normcase(os.path.abspath(candidate))
        if norm in seen:
            continue
        seen.add(norm)
        merged.append(str(Path(candidate).resolve()))
    return merged


def result_figure_paths(
    result,
    *,
    extensions: Iterable[str] = DEFAULT_FIGURE_EXTENSIONS,
) -> list[str]:
    figures = {}
    if isinstance(result, dict):
        candidate = result.get("figures", {})
        figures = candidate if isinstance(candidate, dict) else {}
    else:
        candidate = getattr(result, "figures", {})
        figures = candidate if isinstance(candidate, dict) else {}
    if not figures:
        return []
    allowed_extensions = {str(ext).lower() for ext in extensions}
    return _existing_figure_paths(figures.values(), allowed_extensions)


def build_plot_gallery_entries(
    figure_paths: Iterable[str],
    *,
    output_root: str = "",
) -> list[FigureGalleryEntry]:
    grouped: OrderedDict[str, dict] = OrderedDict()

    for raw_path in figure_paths:
        path_text = str(raw_path or "").strip()
        if not path_text:
            continue

        spec = discover_figure_asset(path_text, output_root=output_root)
        document = load_figure_document(path_text)
        logical_figure_id = str(document.get("figure_id") or spec.figure_id or Path(path_text).stem)
        group_key = _entry_group_key(path_text, logical_figure_id)
        bucket = grouped.setdefault(
            group_key,
            {
                "figure_id": logical_figure_id,
                "category": _classify_gallery_entry(
                    path_text,
                    logical_figure_id,
                    output_root=output_root,
                ),
                "document_mode": "",
                "preview_path": "",
                "primary_path": "",
                "asset_paths": OrderedDict(),
            },
        )

        document_mode = str(document.get("mode") or "").strip().lower()
        if document_mode and not bucket["document_mode"]:
            bucket["document_mode"] = document_mode
        if not bucket["preview_path"]:
            bucket["preview_path"] = str(Path(spec.preview_path).resolve())
        if not bucket["primary_path"]:
            bucket["primary_path"] = str(Path(spec.master_path).resolve())
        _append_asset_paths(bucket["asset_paths"], spec)

    entries: list[FigureGalleryEntry] = []
    for bucket in grouped.values():
        asset_paths = tuple(bucket["asset_paths"].values())
        state = _resolve_gallery_state(bucket["document_mode"], asset_paths)
        preview_path = str(bucket["preview_path"] or (asset_paths[0] if asset_paths else ""))
        primary_path = str(bucket["primary_path"] or preview_path)
        editable_path = ""
        if state == FIGURE_STATE_OBJECT:
            editable_path = primary_path
        elif state == FIGURE_STATE_STATIC:
            editable_path = preview_path
        entries.append(
            FigureGalleryEntry(
                figure_id=str(bucket["figure_id"]),
                title=str(bucket["figure_id"]).replace("_", " "),
                category=str(bucket["category"] or FIGURE_CATEGORY_OTHER_EXPORTS),
                state=state,
                preview_path=preview_path,
                primary_path=primary_path,
                editable_path=editable_path,
                document_mode=str(bucket["document_mode"] or ""),
                asset_paths=asset_paths,
                assets=tuple(_build_asset_rows(asset_paths)),
            )
        )

    entries.sort(key=_entry_sort_key)
    return entries


def _existing_figure_paths(paths: Iterable[str], allowed_extensions: set[str]) -> list[str]:
    existing_paths: list[str] = []
    seen: set[str] = set()
    for raw_path in paths:
        path_text = str(raw_path or "").strip()
        if not path_text:
            continue
        path = Path(path_text)
        if not path.is_file():
            continue
        if path.suffix.lower() not in allowed_extensions:
            continue
        resolved = str(path.resolve())
        norm = os.path.normcase(resolved)
        if norm in seen:
            continue
        seen.add(norm)
        existing_paths.append(resolved)
    return existing_paths


def select_plot_gallery_entry(
    entries: Iterable[FigureGalleryEntry],
    *,
    preferred_path: str = "",
    preview_visible: bool = False,
) -> PlotGallerySelection:
    entry_list = list(entries)
    if not entry_list:
        return PlotGallerySelection()

    preferred_text = str(preferred_path or "").strip()
    preferred_norm = os.path.normcase(os.path.abspath(preferred_text)) if preferred_text else ""
    if preferred_norm:
        preferred_path_obj = Path(preferred_text)
        preferred_stem = preferred_path_obj.stem
        preferred_stem_base = preferred_stem[:-4] if preferred_stem.endswith("_LOW") else preferred_stem
        preferred_parent = os.path.normcase(os.path.abspath(str(preferred_path_obj.parent)))
        preferred_ext = preferred_path_obj.suffix.lower()
        exact_entry = None
        exact_asset_path = ""
        variant_entry = None
        variant_mtime = 0.0

        for entry in entry_list:
            for path in entry.asset_paths:
                asset_norm = os.path.normcase(os.path.abspath(path))
                if asset_norm == preferred_norm:
                    exact_entry = entry
                    exact_asset_path = path
                    continue
                candidate = Path(path)
                candidate_stem = candidate.stem
                candidate_stem_base = candidate_stem[:-4] if candidate_stem.endswith("_LOW") else candidate_stem
                candidate_parent = os.path.normcase(os.path.abspath(str(candidate.parent)))
                candidate_ext = candidate.suffix.lower()
                if (
                    candidate_parent == preferred_parent
                    and candidate_ext == preferred_ext
                    and candidate_stem_base == preferred_stem_base
                ):
                    try:
                        candidate_mtime = os.path.getmtime(path)
                    except OSError:
                        candidate_mtime = 0.0
                    if variant_entry is None or candidate_mtime > variant_mtime:
                        variant_entry = entry
                        variant_mtime = candidate_mtime

        if exact_entry is not None:
            if variant_entry is not None:
                try:
                    exact_mtime = os.path.getmtime(exact_asset_path)
                except OSError:
                    exact_mtime = 0.0
                if variant_mtime > exact_mtime:
                    return PlotGallerySelection(
                        selected_figure_id=variant_entry.figure_id,
                        selected_path=variant_entry.preview_path,
                        matched_preferred=True,
                        emit_preview=bool(preview_visible),
                    )
            return PlotGallerySelection(
                selected_figure_id=exact_entry.figure_id,
                selected_path=exact_entry.preview_path,
                matched_preferred=True,
                emit_preview=bool(preview_visible),
            )
        if variant_entry is not None:
            return PlotGallerySelection(
                selected_figure_id=variant_entry.figure_id,
                selected_path=variant_entry.preview_path,
                matched_preferred=True,
                emit_preview=bool(preview_visible),
            )

    first = entry_list[0]
    return PlotGallerySelection(
        selected_figure_id=first.figure_id,
        selected_path=first.preview_path,
        matched_preferred=False,
        emit_preview=bool(preview_visible or not preferred_text),
    )


def select_plot_figure_path(
    figure_paths: Iterable[str],
    *,
    preferred_path: str = "",
    preview_visible: bool = False,
    get_mtime: Callable[[str], float] = os.path.getmtime,
) -> PlotGallerySelection:
    paths = [str(path) for path in figure_paths if str(path or "").strip()]
    if not paths:
        return PlotGallerySelection()

    preferred_text = str(preferred_path or "").strip()
    preferred_norm = os.path.normcase(os.path.abspath(preferred_text)) if preferred_text else ""
    preferred_stem_base = ""
    preferred_parent = ""
    preferred_ext = ""
    if preferred_text:
        preferred_path_obj = Path(preferred_text)
        preferred_stem = preferred_path_obj.stem
        preferred_stem_base = preferred_stem[:-4] if preferred_stem.endswith("_LOW") else preferred_stem
        preferred_parent = os.path.normcase(os.path.abspath(str(preferred_path_obj.parent)))
        preferred_ext = preferred_path_obj.suffix.lower()

    exact_match = ""
    fallback_match = ""
    variant_match = ""

    if preferred_text:
        for path in paths:
            path_norm = os.path.normcase(os.path.abspath(path))
            if path_norm == preferred_norm:
                exact_match = path
                continue
            candidate = Path(path)
            candidate_stem = candidate.stem
            candidate_stem_base = candidate_stem[:-4] if candidate_stem.endswith("_LOW") else candidate_stem
            candidate_parent = os.path.normcase(os.path.abspath(str(candidate.parent)))
            candidate_ext = candidate.suffix.lower()
            if (
                candidate_parent == preferred_parent
                and candidate_ext == preferred_ext
                and candidate_stem_base == preferred_stem_base
            ):
                fallback_match = path
                variant_match = path

    selected_path = ""
    matched_preferred = False
    emit_preview = bool(preview_visible)

    if exact_match and variant_match:
        try:
            exact_mtime = get_mtime(exact_match)
            variant_mtime = get_mtime(variant_match)
        except OSError:
            exact_mtime = variant_mtime = 0.0
        if variant_mtime > exact_mtime:
            selected_path = variant_match
        else:
            selected_path = exact_match
        matched_preferred = True
    elif exact_match:
        selected_path = exact_match
        matched_preferred = True
    elif fallback_match:
        selected_path = fallback_match
        matched_preferred = True
    else:
        selected_path = paths[0]
        emit_preview = bool(preview_visible or not preferred_text)

    return PlotGallerySelection(
        selected_path=selected_path,
        matched_preferred=matched_preferred,
        emit_preview=emit_preview,
    )


def _entry_group_key(path_text: str, logical_figure_id: str) -> str:
    parent = Path(path_text).resolve().parent.as_posix()
    return f"{parent}::{str(logical_figure_id or '').strip().lower()}"


def _classify_gallery_entry(path_text: str, logical_figure_id: str, *, output_root: str = "") -> str:
    path = Path(path_text).resolve()
    parts = _relative_gallery_parts(path, output_root=output_root)
    figure_id = str(logical_figure_id or path.stem).strip().lower()
    if "summary" in parts:
        return FIGURE_CATEGORY_SERIES_OVERVIEW
    if "per_frame" in parts:
        return FIGURE_CATEGORY_PER_FRAME
    if "overview" in figure_id:
        return FIGURE_CATEGORY_OTHER_EXPORTS
    return FIGURE_CATEGORY_OTHER_EXPORTS


def _relative_gallery_parts(path: Path, *, output_root: str = "") -> tuple[str, ...]:
    root_text = str(output_root or "").strip()
    if root_text:
        try:
            relative = path.relative_to(Path(root_text).resolve())
            return tuple(part.lower() for part in relative.parts)
        except ValueError:
            pass
    return tuple(part.lower() for part in path.parts)


def _series_overview_rank(figure_id: str) -> int:
    lookup = str(figure_id or "").strip().lower()
    if "fig_1_overview" in lookup or lookup == "overview":
        return 0
    if "fig_2_waterfall" in lookup or "waterfall" in lookup:
        return 1
    if "fig_3_structure" in lookup or "structure" in lookup:
        return 2
    if "fig_4_heatmap" in lookup or "heatmap" in lookup:
        return 3
    if "invariant" in lookup:
        return 4
    return 50


def _entry_sort_key(entry: FigureGalleryEntry) -> tuple[int, int, str]:
    category_order = {
        FIGURE_CATEGORY_SERIES_OVERVIEW: 0,
        FIGURE_CATEGORY_PER_FRAME: 1,
        FIGURE_CATEGORY_OTHER_EXPORTS: 2,
    }
    semantic_rank = (
        _series_overview_rank(entry.figure_id)
        if entry.category == FIGURE_CATEGORY_SERIES_OVERVIEW
        else 99
    )
    return (category_order.get(entry.category, 9), semantic_rank, entry.title)


def _append_asset_paths(target: OrderedDict[str, str], spec) -> None:
    publication_paths = dict(spec.publication_paths or {})
    candidate_pairs = [
        (Path(spec.preview_path).suffix.lower().lstrip("."), spec.preview_path),
        (Path(spec.master_path).suffix.lower().lstrip("."), spec.master_path),
    ]
    candidate_pairs.extend((str(fmt).lower(), str(path)) for fmt, path in publication_paths.items())
    for fmt, path in candidate_pairs:
        if not fmt or not path:
            continue
        resolved = str(Path(path).resolve())
        target.setdefault(fmt, resolved)


def _resolve_gallery_state(document_mode: str, asset_paths: tuple[str, ...]) -> str:
    mode = str(document_mode or "").strip().lower()
    if mode == OBJECT_MODE:
        return FIGURE_STATE_OBJECT
    if mode == STATIC_BACKGROUND_MODE:
        return FIGURE_STATE_STATIC
    if len(asset_paths) > 1:
        return FIGURE_STATE_UNLINKED_EXPORT
    return FIGURE_STATE_STATIC


def _build_asset_rows(asset_paths: tuple[str, ...]) -> list[FigureGalleryAsset]:
    role_map = {"png": "preview", "svg": "master", "pdf": "publication"}
    rows: list[FigureGalleryAsset] = []
    for path in asset_paths:
        fmt = Path(path).suffix.lower().lstrip(".")
        if not fmt:
            continue
        role = role_map.get(fmt, "asset")
        rows.append(
            FigureGalleryAsset(
                format=fmt,
                label=f"{fmt.upper()} {role}".strip(),
                role=role,
                path=path,
            )
        )
    return rows
