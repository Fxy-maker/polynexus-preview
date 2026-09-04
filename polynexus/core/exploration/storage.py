"""Append-only project persistence for immutable exploration manifests."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Mapping

from polynexus.core.project_workflow.models import canonical_json
from polynexus.core.project_workflow.workspace import ProjectWorkspace

from .contracts import ExplorationRun


_RUN_ID = re.compile(r"exploration-[0-9a-f]{64}")


class ExplorationRunStore:
    """Persist exploration manifests below ``.polynexus/research/exploration``."""

    def __init__(self, workspace: ProjectWorkspace) -> None:
        if type(workspace) is not ProjectWorkspace:
            raise TypeError("ExplorationRunStore requires an exact ProjectWorkspace")
        self.workspace = workspace
        self.root = workspace.research_dir / "exploration"
        self.workspace.require_derived_path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

    @classmethod
    def open(cls, root: str | Path) -> "ExplorationRunStore":
        return cls(ProjectWorkspace.open(root))

    def save(self, run: ExplorationRun) -> ExplorationRun:
        if type(run) is not ExplorationRun:
            raise TypeError("exploration store requires an exact ExplorationRun")
        destination = self._path(run.run_id)
        if destination.exists():
            existing = self.load(run.run_id)
            if existing != run:
                raise ValueError("exploration run manifest is immutable")
            return existing
        self._write_once(destination, run.to_dict())
        return run

    def load(self, run_id: str) -> ExplorationRun:
        source = self._path(run_id)
        if not source.is_file():
            raise ValueError("exploration run manifest is missing")
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
            if not isinstance(payload, Mapping):
                raise ValueError("manifest must contain an object")
            run = ExplorationRun.from_dict(payload)
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("exploration run manifest is invalid") from exc
        if run.run_id != run_id:
            raise ValueError("exploration run manifest filename is invalid")
        return run

    def list_runs(self) -> tuple[ExplorationRun, ...]:
        values: list[ExplorationRun] = []
        for path in sorted(self.root.glob("exploration-*.json"), key=lambda item: item.name):
            try:
                values.append(self.load(path.stem))
            except ValueError:
                continue
        return tuple(values)

    def _path(self, run_id: str) -> Path:
        if not isinstance(run_id, str) or not _RUN_ID.fullmatch(run_id):
            raise ValueError("exploration run id is invalid")
        destination = self.root / f"{run_id}.json"
        self.workspace.require_derived_path(destination)
        return destination

    @staticmethod
    def _write_once(destination: Path, payload: Mapping[str, Any]) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise ValueError("exploration run manifest is immutable")
        handle = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        )
        temporary = Path(handle.name)
        try:
            with handle:
                handle.write(canonical_json(payload))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(temporary, destination)
            except (FileExistsError, OSError):
                if destination.exists():
                    raise ValueError("exploration run manifest is immutable")
                temporary.replace(destination)
        finally:
            if temporary.exists():
                temporary.unlink()


__all__ = ["ExplorationRunStore"]
