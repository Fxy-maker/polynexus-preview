"""Portable numerical snapshots for figure definitions."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

from .contracts import FigureDefinition

_SAFE_SOURCE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class FigureDataSnapshotWriter:
    def __init__(self, run_root: Path):
        self.run_root = Path(run_root).resolve()

    def write(
        self,
        definition: FigureDefinition,
        figure_dir: Path,
    ) -> list[dict[str, object]]:
        figure_dir = Path(figure_dir).resolve()
        self._ensure_within_run(figure_dir)
        data_dir = figure_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        records: list[dict[str, object]] = []
        schemas: list[dict[str, object]] = []
        for source in definition.data_sources:
            if not _SAFE_SOURCE_ID.fullmatch(source.source_id):
                raise ValueError(f"unsafe data source id: {source.source_id}")
            path = data_dir / f"{source.source_id}.csv"
            column_names = [column.name for column in source.columns]
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(column_names)
                writer.writerows(zip(*(source.values[name] for name in column_names)))
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            relative = path.relative_to(self.run_root).as_posix()
            column_payload = [column.to_payload() for column in source.columns]
            records.append(
                {
                    "id": source.source_id,
                    "kind": "csv",
                    "role": source.role,
                    "path": relative,
                    "path_kind": "run_relative",
                    "columns": column_payload,
                    "sha256": digest,
                }
            )
            schemas.append({"id": source.source_id, "columns": column_payload})
        schema_path = data_dir / "data_schema.json"
        schema_path.write_text(
            json.dumps({"sources": schemas}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return records

    def _ensure_within_run(self, path: Path) -> None:
        try:
            path.relative_to(self.run_root)
        except ValueError as exc:
            raise ValueError(f"figure directory escapes run root: {path}") from exc
