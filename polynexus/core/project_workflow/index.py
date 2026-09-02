"""Deterministic, read-only project input inspection and inventory projection."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Iterable

from polynexus.core.agent_workflow import inspect_artifact

from .models import ProjectArtifact, ProjectFact, ResearchGraph
from .workspace import ProjectWorkspace


_TECHNIQUE_ALIASES = (
    ("ftir", "ir"),
    ("infrared", "ir"),
    ("ir", "ir"),
    ("dsc", "dsc"),
    ("waxs", "waxs"),
    ("saxs", "saxs"),
    ("nmr", "nmr"),
)
_RAW_TEMPERATURE_PATTERN = re.compile(
    r"(?:method_)?temperature(?:_c)?\s*[:=]\s*(-?\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_FILENAME_TEMPERATURE_PATTERN = re.compile(
    r"(?<!\d)(-?\d+(?:\.\d+)?)\s*(?:deg(?:rees?)?\s*)?(?:°\s*)?c\b",
    re.IGNORECASE,
)


class ProjectIndexer:
    """Project inventory writer that keeps source facts ahead of inferred labels."""

    def __init__(self, workspace: ProjectWorkspace) -> None:
        self.workspace = workspace

    def inspect(self, paths: Iterable[str | Path]) -> ResearchGraph:
        """Inspect project inputs and atomically persist a stable inventory projection."""
        existing = self._load_existing_artifacts()
        current: dict[str, ProjectArtifact] = {}
        for path in paths:
            artifact = self._inspect_one(path)
            current[artifact.relative_path] = artifact
        refreshed = self._refresh_existing(existing, excluded=set(current))
        refreshed.update(current)
        artifacts = tuple(refreshed[key] for key in sorted(refreshed))
        graph = ResearchGraph.create(
            study_id=self._study_id(),
            artifacts=artifacts,
        )
        self.workspace.write_json(self.workspace.inventory_dir / "index.json", graph.to_dict())
        return graph

    def _load_existing_artifacts(self) -> dict[str, ProjectArtifact]:
        payload = self.workspace.read_json(self.workspace.inventory_dir / "index.json")
        if payload is None:
            return {}
        graph = ResearchGraph.from_dict(payload)
        return {artifact.relative_path: artifact for artifact in graph.artifacts}

    def _refresh_existing(
        self,
        existing: dict[str, ProjectArtifact],
        *,
        excluded: set[str],
    ) -> dict[str, ProjectArtifact]:
        refreshed: dict[str, ProjectArtifact] = {}
        for relative_path in sorted(existing):
            if relative_path in excluded:
                continue
            source = self.workspace.root / relative_path
            if not source.exists():
                continue
            artifact = self._inspect_one(source)
            refreshed[artifact.relative_path] = artifact
        return refreshed

    def _inspect_one(self, path: str | Path) -> ProjectArtifact:
        # Preserve the logical project path for a raw-directory link. This
        # allows read-only access to laboratory data without copying it into
        # the project, while output remains constrained to `.polynexus`.
        source = Path(path).expanduser()
        if not source.is_absolute():
            source = self.workspace.root / source
        source = source.absolute()
        self._require_source_path(source)
        technique = self._infer_technique(source)
        inspected = inspect_artifact(source, technique=technique)
        facts = self._facts_for(source, dict(inspected.header_facts))
        discrepancies = tuple(
            sorted({item for fact in facts.values() for item in fact.discrepancies})
        )
        base = ProjectArtifact.create(
            project_root=self.workspace.root,
            path=source,
            technique=inspected.technique,
            sha256=inspected.sha256,
            facts=facts,
            format=inspected.format,
            inspection_status=inspected.inspection_status,
            reason_codes=inspected.reason_codes,
        )
        return ProjectArtifact(
            artifact_id=base.artifact_id,
            relative_path=base.relative_path,
            technique=base.technique,
            sha256=base.sha256,
            facts=base.facts,
            format=base.format,
            inspection_status=base.inspection_status,
            reason_codes=base.reason_codes,
            discrepancies=discrepancies,
        )

    def _require_source_path(self, source: Path) -> None:
        try:
            relative = source.relative_to(self.workspace.root)
        except ValueError as exc:
            raise ValueError("source path must be inside the project root") from exc
        if not relative.parts or relative.parts[0] != "raw":
            raise ValueError("source path must be inside raw project data")

    @staticmethod
    def _infer_technique(source: Path) -> str:
        # Only project-local raw paths carry grouping semantics.  Matching the
        # full absolute path lets an unrelated parent name (for example
        # ``first-loop-real``) hijack the technique before the actual
        # ``raw/dsc`` segment is considered.
        parts = tuple(source.parts)
        raw_index = next(
            (index for index, part in enumerate(parts) if part.casefold() == "raw"),
            max(0, len(parts) - 2),
        )
        label = " ".join(part.lower() for part in parts[raw_index:])
        for marker, technique in _TECHNIQUE_ALIASES:
            if marker in label:
                return technique
        if source.is_file() and source.suffix.lower() in {".txt", ".dat", ".asc"}:
            try:
                header = source.read_bytes()[:65536].decode("latin-1", errors="replace").lower()
            except OSError:
                header = ""
            if "sample weight" in header or "curve values" in header:
                return "dsc"
        if source.is_file() and source.suffix.lower() in {".csv", ".spc", ".spa", ".dpt"}:
            try:
                header = source.read_bytes()[:8192].decode("latin-1", errors="replace").lower()
            except OSError:
                header = ""
            if "wavenumber" in header or "absorbance" in header or "infrared" in header:
                return "ir"
        return "unknown"

    def _facts_for(self, source: Path, header_facts: dict[str, object]) -> dict[str, ProjectFact]:
        facts = {
            key: ProjectFact.from_sources(key=key, raw_value=value)
            for key, value in sorted(header_facts.items())
        }
        raw_temperature = self._raw_temperature(source)
        filename_temperature = self._filename_temperature(source)
        if raw_temperature is not None or filename_temperature is not None:
            facts["condition.setpoint_C"] = ProjectFact.from_sources(
                key="condition.setpoint_C",
                raw_value=raw_temperature,
                filename_value=filename_temperature,
            )
        return facts

    @staticmethod
    def _raw_temperature(source: Path) -> float | None:
        if not source.is_file():
            return None
        try:
            header = source.read_bytes()[:65536].decode("latin-1", errors="replace")
        except OSError:
            return None
        match = _RAW_TEMPERATURE_PATTERN.search(header)
        return float(match.group(1)) if match else None

    @staticmethod
    def _filename_temperature(source: Path) -> float | None:
        match = _FILENAME_TEMPERATURE_PATTERN.search(source.name)
        return float(match.group(1)) if match else None

    def _study_id(self) -> str:
        return f"project-{self.workspace.root.name or 'root'}"


__all__ = ["ProjectIndexer"]
