"""Atomic, relocatable project-package export for one figure document."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import tempfile
import zipfile
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


_SAFE_SOURCE_ID = re.compile(r"^[A-Za-z0-9_.-]+$")
_ASSET_EXTENSIONS = (".png", ".svg", ".pdf", ".jpg", ".jpeg")


class FigureProjectBundleError(RuntimeError):
    """Raised when a project package cannot be produced safely."""


@dataclass(frozen=True)
class FigureProjectBundleResult:
    output_path: Path
    files: tuple[str, ...]
    manifest: Mapping[str, Any]


@dataclass(frozen=True)
class _BundleFile:
    archive_path: str
    payload: bytes


def export_figure_project_bundle(
    *,
    document: Mapping[str, Any],
    output_path: str | Path,
    figure_path: str | Path | None = None,
    source_root: str | Path | None = None,
) -> FigureProjectBundleResult:
    """Write a self-contained figure project package without partial output."""

    destination = Path(output_path).expanduser().resolve()
    if destination.exists():
        raise FigureProjectBundleError(f"output already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)

    figure = Path(figure_path).expanduser().resolve() if figure_path else None
    root = Path(source_root).expanduser().resolve() if source_root else None
    try:
        files, bundled_document = _prepare_bundle(
            document,
            figure_path=figure,
            source_root=root,
        )
        manifest = _build_manifest(files, bundled_document)
        files = [
            *files,
            _BundleFile(
                "figure_document.json",
                _json_bytes(bundled_document),
            ),
        ]
        manifest = _build_manifest(files, bundled_document)
        files.append(_BundleFile("manifest.json", _json_bytes(manifest)))
        _write_atomic_zip(destination, files)
    except FigureProjectBundleError:
        raise
    except (OSError, ValueError, TypeError, zipfile.BadZipFile) as exc:
        raise FigureProjectBundleError(str(exc)) from exc

    return FigureProjectBundleResult(
        output_path=destination,
        files=tuple(item.archive_path for item in files),
        manifest=manifest,
    )


def _prepare_bundle(
    document: Mapping[str, Any],
    *,
    figure_path: Path | None,
    source_root: Path | None,
) -> tuple[list[_BundleFile], dict[str, Any]]:
    if not isinstance(document, Mapping):
        raise FigureProjectBundleError("figure document must be a mapping")
    bundled_document = deepcopy(dict(document))
    files: list[_BundleFile] = []

    if figure_path is not None:
        for asset_path in _figure_assets(figure_path):
            files.append(
                _BundleFile(
                    f"assets/{asset_path.name}",
                    _read_file(asset_path, "figure asset"),
                )
            )

    raw_sources = bundled_document.get("data_sources", [])
    if raw_sources is None:
        raw_sources = []
    if not isinstance(raw_sources, list):
        raise FigureProjectBundleError("data_sources must be a list")

    normalized_sources: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw_source in enumerate(raw_sources):
        if not isinstance(raw_source, Mapping):
            raise FigureProjectBundleError(f"data source {index} must be a mapping")
        source = deepcopy(dict(raw_source))
        source_id = str(source.get("id") or f"source-{index + 1}").strip()
        if not _SAFE_SOURCE_ID.fullmatch(source_id):
            raise FigureProjectBundleError(f"unsafe data source id: {source_id}")
        if source_id in seen_ids:
            raise FigureProjectBundleError(f"duplicate data source id: {source_id}")
        seen_ids.add(source_id)

        path_text = str(source.get("path") or "").strip()
        if path_text:
            source_path = _resolve_source_path(
                path_text,
                source,
                figure_path=figure_path,
                source_root=source_root,
            )
            payload = _read_file(source_path, "data source")
            suffix = source_path.suffix.lower() or ".csv"
        else:
            payload = _inline_source_bytes(source, source_id)
            suffix = ".csv"

        archive_path = f"sources/{source_id}{suffix}"
        files.append(_BundleFile(archive_path, payload))
        source["id"] = source_id
        source["path"] = archive_path
        source["path_kind"] = "bundle_relative"
        normalized_sources.append(source)

    bundled_document["data_sources"] = normalized_sources
    bundled_document["bundle_format_version"] = 1
    return files, bundled_document


def _figure_assets(figure_path: Path) -> list[Path]:
    if not figure_path.is_file():
        raise FigureProjectBundleError(f"figure asset does not exist: {figure_path}")
    assets: list[Path] = []
    seen: set[str] = set()
    for candidate in [figure_path, *[figure_path.with_suffix(ext) for ext in _ASSET_EXTENSIONS]]:
        if not candidate.is_file():
            continue
        key = os.path.normcase(str(candidate.resolve()))
        if key in seen:
            continue
        seen.add(key)
        assets.append(candidate)
    return assets


def _resolve_source_path(
    path_text: str,
    source: Mapping[str, Any],
    *,
    figure_path: Path | None,
    source_root: Path | None,
) -> Path:
    candidate = Path(path_text).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    path_kind = str(source.get("path_kind") or "").strip().lower()
    if path_kind == "run_relative":
        if source_root is None:
            raise FigureProjectBundleError("run-relative source requires source root")
        resolved = (source_root / candidate).resolve()
        try:
            resolved.relative_to(source_root)
        except ValueError as exc:
            raise FigureProjectBundleError(
                f"source path escapes source root: {path_text}"
            ) from exc
        return resolved
    if figure_path is None:
        return candidate.resolve()
    return (figure_path.parent / candidate).resolve()


def _read_file(path: Path, label: str) -> bytes:
    if not path.is_file():
        raise FigureProjectBundleError(f"{label} does not exist: {path}")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise FigureProjectBundleError(f"{label} is unreadable: {path}") from exc


def _inline_source_bytes(source: Mapping[str, Any], source_id: str) -> bytes:
    values = source.get("values")
    if not isinstance(values, Mapping):
        values = source.get("data")
    if not isinstance(values, Mapping):
        raise FigureProjectBundleError(
            f"data source has no path or inline values: {source_id}"
        )
    column_names = [
        str(column.get("name") or "")
        for column in source.get("columns", [])
        if isinstance(column, Mapping) and str(column.get("name") or "")
    ]
    if not column_names:
        column_names = [str(key) for key in values]
    rows = zip(*(values.get(name, []) for name in column_names))
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(column_names)
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def _build_manifest(
    files: list[_BundleFile], document: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "format": "polynexus.figure-project",
        "version": 1,
        "figure_id": str(document.get("figure_id") or ""),
        "document": "figure_document.json",
        "files": {
            item.archive_path: {
                "size": len(item.payload),
                "sha256": hashlib.sha256(item.payload).hexdigest(),
            }
            for item in files
        },
    }


def _write_atomic_zip(destination: Path, files: list[_BundleFile]) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(
            temporary,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            for item in files:
                archive.writestr(item.archive_path, item.payload)
        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, default=_json_default)
        .encode("utf-8")
    )


def _json_default(value: Any):
    tolist = getattr(value, "tolist", None)
    if callable(tolist):
        return tolist()
    return str(value)


__all__ = [
    "FigureProjectBundleError",
    "FigureProjectBundleResult",
    "export_figure_project_bundle",
]
