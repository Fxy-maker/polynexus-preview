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
    publication_role: str = "si"
    display_order: int = 0

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> FigureManifestEntry:
        capability_report = dict(payload.get("capability_report", {}))
        raw_display_order = payload.get("display_order", 0)
        try:
            display_order = int(raw_display_order or 0)
        except (TypeError, ValueError):
            display_order = 0
        raw_role = payload.get("publication_role")
        if not str(raw_role or "").strip():
            raw_role = _legacy_publication_role(payload.get("category"))
        return cls(
            figure_id=str(payload.get("figure_id") or ""),
            title=str(payload.get("title") or ""),
            category=str(payload.get("category") or ""),
            status=str(payload.get("status") or ""),
            document=str(payload.get("document") or ""),
            data_sources=tuple(str(path) for path in payload.get("data_sources", [])),
            assets={
                str(role): str(path)
                for role, path in dict(payload.get("assets", {})).items()
            },
            capability_report=capability_report,
            working_revision=int(payload.get("working_revision", 0) or 0),
            published_revision=int(payload.get("published_revision", 0) or 0),
            error=str(payload.get("error") or ""),
            publication_role=str(raw_role),
            display_order=display_order,
        )

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
            "publication_role": self.publication_role,
            "display_order": self.display_order,
        }


def _legacy_publication_role(category: object) -> str:
    """Map pre-role manifests to the safest publication role."""
    normalized = str(category or "").strip().lower()
    if normalized == "series_overview":
        return "main"
    if normalized in {"diagnostic", "per_frame"}:
        return "diagnostic"
    return "si"


@dataclass(frozen=True)
class RunFigureManifest:
    schema_version: int
    run_id: str
    technique: str
    output_profile: str
    figures: tuple[FigureManifestEntry, ...]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> RunFigureManifest:
        return cls(
            schema_version=int(payload.get("schema_version", 1) or 1),
            run_id=str(payload.get("run_id") or ""),
            technique=str(payload.get("technique") or ""),
            output_profile=str(payload.get("output_profile") or ""),
            figures=tuple(
                FigureManifestEntry.from_payload(item)
                for item in payload.get("figures", [])
                if isinstance(item, dict)
            ),
        )

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

    def read_manifest(self, run_root: Path) -> RunFigureManifest:
        path = Path(run_root).resolve() / "figure_manifest.json"
        payload = self._read_json(path)
        manifest = RunFigureManifest.from_payload(payload)
        self._validate_ready_paths(manifest)
        return manifest

    def read_active_manifest(self) -> tuple[Path, RunFigureManifest]:
        pointer = self._read_json(self.output_root / "active_run.json")
        run_id = str(pointer.get("run_id") or "")
        if not run_id or "/" in run_id or "\\" in run_id:
            raise ValueError(f"invalid active run ID: {run_id!r}")
        run_root = (self.output_root / "runs" / run_id).resolve()
        expected_runs_root = (self.output_root / "runs").resolve()
        try:
            run_root.relative_to(expected_runs_root)
        except ValueError as exc:
            raise ValueError(f"active run escapes output root: {run_id}") from exc
        manifest = self.read_manifest(run_root)
        if manifest.run_id != run_id:
            raise ValueError(
                f"active run pointer mismatch: {run_id} != {manifest.run_id}"
            )
        return run_root, manifest

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

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        with Path(path).open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise ValueError(f"JSON object expected: {path}")
        return payload
