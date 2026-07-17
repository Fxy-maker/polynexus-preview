"""End-to-end orchestration for one manifest-backed figure run."""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .capabilities import resolve_figure_capabilities
from .contracts import FigureDefinition
from .data_writer import FigureDataSnapshotWriter
from .document_builder import FigureDocumentBuilder
from .export_service import FigureArtifactExportService
from .manifest import (
    FigureManifestEntry,
    RunFigureManifest,
    RunFigureManifestRepository,
)
from .profiles import FigureOutputProfile, get_figure_output_profile
from .render_plan import FigureRenderPlanBuilder
from .validation import validate_figure_definition
from .v2_capabilities import build_v2_definition_artifact


_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class FigurePipeline:
    """Build and atomically publish all figure artifacts for one run."""

    def __init__(
        self,
        *,
        exporter: FigureArtifactExportService | None = None,
    ) -> None:
        self._exporter = exporter or FigureArtifactExportService()

    def run(
        self,
        *,
        output_root: Path,
        run_id: str,
        technique: str,
        definitions: Iterable[FigureDefinition],
        profile_id: str = "paper_complete",
    ) -> RunFigureManifest:
        run_id = str(run_id)
        if not _RUN_ID_PATTERN.fullmatch(run_id):
            raise ValueError(f"invalid run ID: {run_id!r}")

        profile = get_figure_output_profile(profile_id)
        output_root = Path(output_root).resolve()
        runs_dir = output_root / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        final_run_root = runs_dir / run_id
        staging = runs_dir / f".{run_id}.staging"
        if final_run_root.exists():
            raise FileExistsError(f"figure run already exists: {final_run_root}")
        if staging.exists():
            raise FileExistsError(f"figure run staging already exists: {staging}")

        staging.mkdir()
        repository = RunFigureManifestRepository(output_root)
        committed = False
        try:
            entries: list[FigureManifestEntry] = []
            seen_figure_ids: set[str] = set()
            for definition in definitions:
                if definition.figure_id in seen_figure_ids:
                    entries.append(
                        self._failed_entry(
                            definition,
                            ValueError(
                                f"duplicate figure_id in run: {definition.figure_id}"
                            ),
                        )
                    )
                    continue
                seen_figure_ids.add(definition.figure_id)
                entries.append(
                    self._process_definition(
                        definition=definition,
                        run_id=run_id,
                        staging=staging,
                        profile=profile,
                    )
                )

            manifest = RunFigureManifest(
                schema_version=1,
                run_id=run_id,
                technique=str(technique),
                output_profile=profile.profile_id,
                figures=tuple(entries),
            )
            self._write_json(
                staging / "run_metadata.json",
                {
                    "schema_version": 1,
                    "run_id": run_id,
                    "technique": str(technique),
                    "output_profile": profile.profile_id,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "figure_count": len(entries),
                },
            )
            repository.write_manifest(staging, manifest)
            staging.rename(final_run_root)
            committed = True
            repository.activate(run_id)
            return manifest
        except BaseException:
            if not committed:
                shutil.rmtree(staging, ignore_errors=True)
            raise

    def _process_definition(
        self,
        *,
        definition: FigureDefinition,
        run_id: str,
        staging: Path,
        profile: FigureOutputProfile,
    ) -> FigureManifestEntry:
        figure_dir: Path | None = None
        try:
            validate_figure_definition(definition)
            figure_dir = staging / "figures" / definition.figure_id
            data_sources = FigureDataSnapshotWriter(staging).write(
                definition,
                figure_dir,
            )
            document_path, document = FigureDocumentBuilder().write(
                definition=definition,
                run_id=run_id,
                revision=1,
                figure_dir=figure_dir,
                data_sources=data_sources,
            )
            v2_artifact = build_v2_definition_artifact(definition)
            v2_sidecar_path: Path | None = None
            if v2_artifact.sidecar is not None:
                v2_sidecar_path = figure_dir / "reactive_figure_v2.json"
                self._write_json(v2_sidecar_path, v2_artifact.sidecar)
            plan = FigureRenderPlanBuilder(staging).build(document_path, document)
            export = self._exporter.export_initial(
                plan=plan,
                figure_dir=figure_dir,
                profile=profile,
            )
            asset_paths = {
                role: self._run_relative(path, staging)
                for role, path in export.assets.items()
            }
            document["export"] = {
                "profile": profile.profile_id,
                "published_revision": 1,
                "assets": asset_paths,
            }
            self._write_json(document_path, document)
            capability = resolve_figure_capabilities(
                plan=plan,
                inspection=export.inspection,
                audit=export.audit,
                working_revision=1,
                published_revision=1,
            )
            capability_payload = capability.to_payload()
            capability_payload.update(v2_artifact.capability)
            if v2_sidecar_path is not None:
                capability_payload["v2_sidecar"] = self._run_relative(v2_sidecar_path, staging)
            return FigureManifestEntry(
                figure_id=definition.figure_id,
                title=definition.title,
                category=definition.category,
                status="ready",
                document=self._run_relative(document_path, staging),
                data_sources=tuple(str(item["path"]) for item in data_sources),
                assets=asset_paths,
                capability_report=capability_payload,
                working_revision=1,
                published_revision=1,
                error="",
                publication_role=definition.publication_role,
                display_order=self._definition_display_order(definition),
            )
        except Exception as exc:
            if figure_dir is not None:
                shutil.rmtree(figure_dir, ignore_errors=True)
            return self._failed_entry(definition, exc)

    @staticmethod
    def _failed_entry(
        definition: FigureDefinition,
        error: Exception,
    ) -> FigureManifestEntry:
        return FigureManifestEntry(
            figure_id=definition.figure_id,
            title=definition.title,
            category=definition.category,
            status="generation_failed",
            document="",
            data_sources=(),
            assets={},
            capability_report={},
            working_revision=0,
            published_revision=0,
            error=f"{type(error).__name__}: {error}",
            publication_role=definition.publication_role,
            display_order=FigurePipeline._definition_display_order(definition),
        )

    @staticmethod
    def _definition_display_order(definition: FigureDefinition) -> int:
        recipe = definition.recipe if isinstance(definition.recipe, dict) else {}
        parameters = recipe.get("parameters", {})
        if not isinstance(parameters, dict):
            return 0
        try:
            return int(parameters.get("display_order", 0) or 0)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _run_relative(path: Path, run_root: Path) -> str:
        resolved_root = Path(run_root).resolve()
        resolved_path = Path(path).resolve()
        try:
            return resolved_path.relative_to(resolved_root).as_posix()
        except ValueError as exc:
            raise ValueError(f"path escapes run root: {resolved_path}") from exc

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
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
