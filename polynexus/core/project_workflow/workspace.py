"""Project-local storage that never writes to primary research materials."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
from typing import Any, Mapping

from .models import canonical_json


_DERIVED_DIRECTORIES = (
    "inventory",
    "requests",
    "canonical",
    "runs",
    "figures",
    "evidence",
)
_PRIMARY_DIRECTORIES = frozenset({"raw", "notes", "manuscript"})


class ProjectWorkspace:
    """Validated project root with a write boundary limited to ``.polynexus``."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.derived_root = root / ".polynexus"
        self.inventory_dir = self.derived_root / "inventory"
        self.requests_dir = self.derived_root / "requests"
        self.canonical_dir = self.derived_root / "canonical"
        self.runs_dir = self.derived_root / "runs"
        self.figures_dir = self.derived_root / "figures"
        self.evidence_dir = self.derived_root / "evidence"

    @classmethod
    def open(cls, root: str | Path) -> "ProjectWorkspace":
        """Open a project root and create only documented derived directories."""
        resolved = Path(root).expanduser().resolve()
        if not resolved.is_dir():
            raise ValueError("project root must be an existing directory")
        workspace = cls(resolved)
        if workspace.derived_root.exists():
            try:
                workspace.derived_root.resolve().relative_to(resolved)
            except ValueError as exc:
                raise ValueError(".polynexus must resolve inside the project root") from exc
        workspace.derived_root.mkdir(exist_ok=True)
        for directory in workspace.derived_directories:
            directory.mkdir(exist_ok=True)
        return workspace

    @property
    def derived_directories(self) -> tuple[Path, ...]:
        return (
            self.inventory_dir,
            self.requests_dir,
            self.canonical_dir,
            self.runs_dir,
            self.figures_dir,
            self.evidence_dir,
        )

    def require_derived_path(self, path: str | Path) -> Path:
        """Return a resolved output path or reject paths outside approved storage."""
        candidate = Path(path).expanduser().resolve()
        try:
            relative_to_root = candidate.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("derived path must be inside the project root") from exc

        if not relative_to_root.parts:
            raise ValueError("derived path must not be the project root")
        if relative_to_root.parts[0] in _PRIMARY_DIRECTORIES:
            raise ValueError("derived path must not write to primary project materials")
        try:
            relative_to_derived = candidate.relative_to(self.derived_root.resolve())
        except ValueError as exc:
            raise ValueError("derived path must be inside .polynexus") from exc
        if not relative_to_derived.parts or relative_to_derived.parts[0] not in _DERIVED_DIRECTORIES:
            raise ValueError("derived path must be inside a documented derived directory")
        return candidate

    def write_json(self, path: str | Path, payload: Mapping[str, Any]) -> Path:
        """Atomically write JSON to a validated derived path."""
        destination = self.require_derived_path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        handle = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        )
        try:
            with handle:
                handle.write(canonical_json(payload))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            Path(handle.name).replace(destination)
        finally:
            temporary = Path(handle.name)
            if temporary.exists():
                temporary.unlink()
        return destination

    def read_json(self, path: str | Path) -> dict[str, Any] | None:
        """Read a validated derived JSON document when it exists."""
        import json

        source = self.require_derived_path(path)
        if not source.exists():
            return None
        with source.open(encoding="utf-8") as handle:
            value = json.load(handle)
        if not isinstance(value, dict):
            raise ValueError("derived JSON document must contain an object")
        return value


__all__ = ["ProjectWorkspace"]
