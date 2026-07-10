"""Run-level figure manifests and atomic active-run pointers."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any


@dataclass(frozen=True)
class FigureManifestEntry:
    figure_id: str
    title: str
    category: str
    status: str
    document: str
    data_sources: tuple[str, ...]
    assets: dict[str, str]
    capability_report: dict[str, Any]
    working_revision: int
    published_revision: int
    error: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "figure_id": self.figure_id,
            "title": self.title,
            "category": self.category,
            "status": self.status,
            "document": self.document,
            "data_sources": list(self.data_sources),
            "assets": dict(self.assets),
            "capability_report": dict(self.capability_report),
            "working_revision": self.working_revision,
            "published_revision": self.published_revision,
            "error": self.error,
        }


@dataclass(frozen=True)
class RunFigureManifest:
    schema_version: int
    run_id: str
    technique: str
    output_profile: str
    figures: tuple[FigureManifestEntry, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "technique": self.technique,
            "output_profile": self.output_profile,
            "figures": [entry.to_payload() for entry in self.figures],
        }


class RunFigureManifestRepository:
    """Atomically store manifests and the current active-run identity."""

    def __init__(self, output_root: Path):
        self.output_root = Path(output_root).resolve()

    def write_manifest(
        self,
        run_root: Path,
        manifest: RunFigureManifest,
    ) -> Path:
        self._validate_ready_paths(manifest)
        path = Path(run_root).resolve() / "figure_manifest.json"
        self._atomic_write_json(path, manifest.to_payload())
        return path

    def activate(self, run_id: str) -> Path:
        run_id = str(run_id)
        if not run_id or "/" in run_id or "\\" in run_id:
            raise ValueError(f"invalid run ID: {run_id!r}")
        path = self.output_root / "active_run.json"
        self._atomic_write_json(path, {"run_id": run_id})
        return path

    @classmethod
    def _validate_ready_paths(cls, manifest: RunFigureManifest) -> None:
        for entry in manifest.figures:
            if entry.status != "ready":
                continue
            paths = {
                "document": entry.document,
                **{
                    f"data_sources[{index}]": path
                    for index, path in enumerate(entry.data_sources)
                },
                **{f"assets.{role}": path for role, path in entry.assets.items()},
            }
            for label, path in paths.items():
                if not cls._is_run_relative_posix_path(path):
                    raise ValueError(
                        f"ready figure path must be run-relative POSIX: "
                        f"{entry.figure_id} {label}={path!r}"
                    )

    @staticmethod
    def _is_run_relative_posix_path(value: str) -> bool:
        text = str(value)
        if not text or "\\" in text:
            return False
        posix_path = PurePosixPath(text)
        windows_path = PureWindowsPath(text)
        return (
            not posix_path.is_absolute()
            and not windows_path.is_absolute()
            and ".." not in posix_path.parts
            and posix_path.as_posix() == text
        )

    @staticmethod
    def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, path)
        except BaseException:
            temporary_path.unlink(missing_ok=True)
            raise
