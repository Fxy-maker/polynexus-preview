"""Immutable working-save and complete-publication figure revisions."""

from __future__ import annotations

import json
import shutil
from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

from .capabilities import resolve_figure_capabilities
from .export_service import FigureArtifactExportService
from .inspector import FigureArtifactInspector
from .manifest import (
    FigureManifestEntry,
    RunFigureManifest,
    RunFigureManifestRepository,
)
from .profiles import get_figure_output_profile
from .render_plan import FigureRenderPlanBuilder


@dataclass(frozen=True)
class FigureProjectUpdate:
    manifest: RunFigureManifest
    entry: FigureManifestEntry
    document: dict
    preview_path: str


class FigureProjectService:
    def __init__(
        self,
        output_root: Path,
        *,
        exporter: FigureArtifactExportService | None = None,
    ) -> None:
        self.output_root = Path(output_root).resolve()
        self.repository = RunFigureManifestRepository(self.output_root)
        self.exporter = exporter or FigureArtifactExportService()
        self.inspector = FigureArtifactInspector()

    def save_working(
        self,
        *,
        run_id: str,
        figure_id: str,
        document: dict,
    ) -> FigureProjectUpdate:
        run_root, manifest = self._load_run(run_id)
        entry = self._entry(manifest, figure_id)
        next_revision = max(
            entry.working_revision,
            int(document.get("revision", 0) or 0),
        ) + 1
        revision_dir = (
            run_root
            / "figures"
            / entry.figure_id
            / "revisions"
            / f"r{next_revision:04d}"
        )
        if revision_dir.exists():
            raise FileExistsError(f"working revision already exists: {revision_dir}")
        revision_dir.mkdir(parents=True)
        try:
            updated_document = deepcopy(document)
            updated_document["run_id"] = manifest.run_id
            updated_document["figure_id"] = entry.figure_id
            updated_document["revision"] = next_revision
            updated_document["updated_at"] = datetime.now(timezone.utc).isoformat()
            document_path = revision_dir / "figure.pnfig.json"
            self.repository._atomic_write_json(document_path, updated_document)
            plan = FigureRenderPlanBuilder(run_root).build(
                document_path,
                updated_document,
            )
            profile = get_figure_output_profile(manifest.output_profile)
            preview_path = revision_dir / profile.preview_filename
            self.exporter.export_preview(
                plan=plan,
                path=preview_path,
                profile=profile,
            )
            assets = dict(entry.assets)
            assets["preview"] = self._relative(preview_path, run_root)
            inspection = self.inspector.inspect(
                plan=plan,
                assets=self._absolute_assets(run_root, assets),
                profile=profile,
            )
            capability = resolve_figure_capabilities(
                plan=plan,
                inspection=inspection,
                working_revision=next_revision,
                published_revision=entry.published_revision,
            )
            updated_entry = replace(
                entry,
                document=self._relative(document_path, run_root),
                assets=assets,
                capability_report=capability.to_payload(),
                working_revision=next_revision,
                error="",
            )
            updated_manifest = self._replace_entry(manifest, updated_entry)
            self.repository.write_manifest(run_root, updated_manifest)
        except BaseException:
            shutil.rmtree(revision_dir, ignore_errors=True)
            raise
        return FigureProjectUpdate(
            manifest=updated_manifest,
            entry=updated_entry,
            document=updated_document,
            preview_path=str(preview_path),
        )

    def publish(self, *, run_id: str, figure_id: str) -> FigureProjectUpdate:
        run_root, manifest = self._load_run(run_id)
        entry = self._entry(manifest, figure_id)
        if entry.working_revision <= 0:
            raise ValueError(f"figure has no working revision: {figure_id}")
        document_path = self._absolute_path(run_root, entry.document)
        document = self._read_json(document_path)
        plan = FigureRenderPlanBuilder(run_root).build(document_path, document)
        profile = get_figure_output_profile(manifest.output_profile)
        publication_dir = (
            run_root
            / "figures"
            / entry.figure_id
            / "publications"
            / f"r{entry.working_revision:04d}"
        )
        if publication_dir.exists():
            raise FileExistsError(f"publication revision already exists: {publication_dir}")
        publication_dir.mkdir(parents=True)
        try:
            export = self.exporter.export_initial(
                plan=plan,
                figure_dir=publication_dir,
                profile=profile,
            )
            assets = {
                role: self._relative(path, run_root)
                for role, path in export.assets.items()
            }
            published_document = deepcopy(document)
            published_document["export"] = {
                "profile": profile.profile_id,
                "published_revision": entry.working_revision,
                "assets": assets,
            }
            published_document["updated_at"] = datetime.now(timezone.utc).isoformat()
            published_document_path = publication_dir / "figure.pnfig.json"
            self.repository._atomic_write_json(
                published_document_path,
                published_document,
            )
            capability = resolve_figure_capabilities(
                plan=plan,
                inspection=export.inspection,
                working_revision=entry.working_revision,
                published_revision=entry.working_revision,
            )
            updated_entry = replace(
                entry,
                document=self._relative(published_document_path, run_root),
                assets=assets,
                capability_report=capability.to_payload(),
                published_revision=entry.working_revision,
                error="",
            )
            updated_manifest = self._replace_entry(manifest, updated_entry)
            self.repository.write_manifest(run_root, updated_manifest)
        except BaseException:
            shutil.rmtree(publication_dir, ignore_errors=True)
            raise
        return FigureProjectUpdate(
            manifest=updated_manifest,
            entry=updated_entry,
            document=published_document,
            preview_path=str(run_root / assets["preview"]),
        )

    def _load_run(self, run_id: str) -> tuple[Path, RunFigureManifest]:
        run_root = (self.output_root / "runs" / str(run_id)).resolve()
        manifest = self.repository.read_manifest(run_root)
        if manifest.run_id != str(run_id):
            raise ValueError(f"run ID mismatch: {run_id} != {manifest.run_id}")
        return run_root, manifest

    @staticmethod
    def _entry(manifest: RunFigureManifest, figure_id: str) -> FigureManifestEntry:
        for entry in manifest.figures:
            if entry.figure_id == figure_id:
                if entry.status != "ready":
                    raise ValueError(f"figure is not ready: {figure_id}")
                return entry
        raise KeyError(f"unknown figure ID: {figure_id}")

    @staticmethod
    def _replace_entry(
        manifest: RunFigureManifest,
        updated_entry: FigureManifestEntry,
    ) -> RunFigureManifest:
        return replace(
            manifest,
            figures=tuple(
                updated_entry if entry.figure_id == updated_entry.figure_id else entry
                for entry in manifest.figures
            ),
        )

    @staticmethod
    def _relative(path: Path, run_root: Path) -> str:
        return Path(path).resolve().relative_to(Path(run_root).resolve()).as_posix()

    @staticmethod
    def _absolute_path(run_root: Path, relative_path: str) -> Path:
        path = (Path(run_root).resolve() / Path(relative_path)).resolve()
        path.relative_to(Path(run_root).resolve())
        return path

    def _absolute_assets(
        self,
        run_root: Path,
        assets: dict[str, str],
    ) -> dict[str, Path]:
        return {
            role: self._absolute_path(run_root, path)
            for role, path in assets.items()
        }

    @staticmethod
    def _read_json(path: Path) -> dict:
        with Path(path).open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise ValueError(f"document JSON object expected: {path}")
        return payload
