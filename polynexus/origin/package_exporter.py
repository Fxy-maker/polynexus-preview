"""Origin-compatible bundle exporter that has no Origin runtime dependency."""

from __future__ import annotations

import csv
import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from ..core.figure_document import normalize_figure_document
from .contracts import ExportRequest, ExportResult
from .mapping import OriginSourceSpec, map_figure_document
from .path_resolution import resolve_source_path


_SAFE_SOURCE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_PREVIEW_EXTENSIONS = ("png", "svg", "pdf")


class PackageExporter:
    adapter_id = "package"
    priority = 10

    def can_handle(self, request: ExportRequest) -> bool:
        return True

    def export(self, request: ExportRequest) -> ExportResult:
        output_root = request.output_root.resolve()
        output_root.mkdir(parents=True, exist_ok=True)
        final_root = self._next_target(output_root / "Origin_Export")
        staging_parent = Path(tempfile.mkdtemp(prefix=".origin-export-", dir=output_root))
        staging_root = staging_parent / "Origin_Export"
        staging_root.mkdir(parents=True, exist_ok=True)

        normalized = normalize_figure_document(dict(request.document))
        mapped = map_figure_document(normalized)
        warnings = list(mapped.warnings)

        try:
            self._write_document(staging_root / "figure_document.json", normalized)
            written_sources = self._write_sources(
                staging_root / "data",
                mapped.sources,
                request,
            )
            written_previews = self._copy_previews(staging_root, request.figure_path)
            self._write_import_script(staging_root / "import.ogs", written_sources)
            self._write_metadata(
                staging_root / "metadata.json",
                request,
                mapped,
                warnings,
                written_sources,
                written_previews,
            )
            staging_root.replace(final_root)
        except Exception as exc:
            shutil.rmtree(staging_parent, ignore_errors=True)
            return ExportResult(
                status="failed",
                adapter_id=self.adapter_id,
                warnings=tuple(warnings),
                message=str(exc),
                recoverable=True,
            )

        shutil.rmtree(staging_parent, ignore_errors=True)
        return ExportResult.success_result(
            self.adapter_id,
            final_root,
            warnings=tuple(warnings),
            message="Created an Origin-compatible export package",
        )

    @staticmethod
    def _next_target(base: Path) -> Path:
        if not base.exists():
            return base
        index = 2
        while True:
            candidate = base.with_name(f"{base.name}_{index}")
            if not candidate.exists():
                return candidate
            index += 1

    @staticmethod
    def _write_document(path: Path, document: dict[str, Any]) -> None:
        path.write_text(
            json.dumps(document, ensure_ascii=False, indent=2, default=_json_default),
            encoding="utf-8",
        )

    def _write_sources(
        self,
        data_root: Path,
        sources: tuple[OriginSourceSpec, ...],
        request: ExportRequest,
    ) -> list[str]:
        data_root.mkdir(parents=True, exist_ok=True)
        written: list[str] = []
        for source in sources:
            if not _SAFE_SOURCE_ID.fullmatch(source.source_id):
                raise ValueError(f"unsafe data source id: {source.source_id}")
            target = data_root / f"{source.source_id}.csv"
            if source.path:
                source_path = resolve_source_path(source.path, request)
                if not source_path.is_file():
                    raise FileNotFoundError(f"data source does not exist: {source.path}")
                shutil.copy2(source_path, target)
            elif source.values:
                self._write_inline_source(target, source)
            else:
                raise ValueError(f"data source has no path or values: {source.source_id}")
            written.append(target.relative_to(data_root.parent).as_posix())
        return written

    @staticmethod
    def _write_inline_source(path: Path, source: OriginSourceSpec) -> None:
        column_names = [
            str(column.get("name") or "")
            for column in source.columns
            if str(column.get("name") or "")
        ]
        if not column_names:
            column_names = list(source.values.keys())
        rows = zip(*(source.values.get(name, []) for name in column_names))
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(column_names)
            writer.writerows(rows)

    @staticmethod
    def _copy_previews(staging_root: Path, figure_path: Path | None) -> list[str]:
        if figure_path is None:
            return []
        source = figure_path.resolve()
        if not source.is_file():
            return []
        copied: list[str] = []
        for extension in _PREVIEW_EXTENSIONS:
            candidate = source.with_suffix(f".{extension}")
            if candidate.is_file():
                target = staging_root / f"preview.{extension}"
                shutil.copy2(candidate, target)
                copied.append(target.name)
        return copied

    @staticmethod
    def _write_import_script(path: Path, relative_sources: list[str]) -> None:
        lines = [
            "// PolyNexus Origin-compatible data import script",
            *[
                f'impCSV fname:="{_labtalk_quote(relative_path)}";'
                for relative_path in relative_sources
            ],
        ]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    @staticmethod
    def _write_metadata(
        path: Path,
        request: ExportRequest,
        mapped,
        warnings: list[str],
        sources: list[str],
        previews: list[str],
    ) -> None:
        path.write_text(
            json.dumps(
                {
                    "adapter_id": "package",
                    "mode": request.mode,
                    "figure_id": mapped.figure_id,
                    "sources": sources,
                    "previews": previews,
                    "warnings": warnings,
                    "message": "Open the data and import.ogs in Origin to create an editable project.",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


def _labtalk_quote(value: str) -> str:
    return str(value).replace('"', '""')


def _json_default(value: Any):
    tolist = getattr(value, "tolist", None)
    if callable(tolist):
        return tolist()
    return str(value)
