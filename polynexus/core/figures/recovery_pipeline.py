"""Rebuild a portable historical FigureDocument as a new immutable run."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from .capabilities import resolve_figure_capabilities
from .export_service import FigureArtifactExportService
from .manifest import (
    FigureManifestEntry,
    RunFigureManifest,
    RunFigureManifestRepository,
)
from .profiles import get_figure_output_profile
from .render_plan import FigureRenderPlanBuilder


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class FigureRecoveryPipeline:
    """Repair one object document without rerunning scientific analysis."""

    def __init__(
        self,
        output_root: str | Path,
        *,
        exporter: FigureArtifactExportService | None = None,
    ) -> None:
        self.output_root = Path(output_root).resolve()
        self.exporter = exporter or FigureArtifactExportService()
        self.repository = RunFigureManifestRepository(self.output_root)

    def recover_document(
        self,
        *,
        run_id: str,
        technique: str,
        document_path: str | Path,
        data_root: str | Path,
        profile_id: str = "paper_complete",
    ) -> RunFigureManifest:
        run_id = str(run_id)
        if not _SAFE_ID.fullmatch(run_id):
            raise ValueError(f"invalid run ID: {run_id!r}")
        source_document_path = Path(document_path).resolve()
        source_document = self._read_json(source_document_path)
        figure_id = str(source_document.get("figure_id") or "").strip()
        if not _SAFE_ID.fullmatch(figure_id):
            raise ValueError(f"invalid recovered figure ID: {figure_id!r}")
        if str(source_document.get("mode") or "") != "object":
            raise ValueError("only object FigureDocuments can be repaired as a run")

        runs_dir = self.output_root / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        final_run_root = runs_dir / run_id
        staging = runs_dir / f".{run_id}.staging"
        if final_run_root.exists() or staging.exists():
            raise FileExistsError(f"recovery run already exists: {run_id}")
        staging.mkdir()
        committed = False
        try:
            figure_dir = staging / "figures" / figure_id
            figure_dir.mkdir(parents=True)
            document = deepcopy(source_document)
            document["run_id"] = run_id
            document["revision"] = 1
            document["updated_at"] = datetime.now(timezone.utc).isoformat()
            document["data_sources"] = self._copy_data_sources(
                sources=document.get("data_sources", []),
                data_root=Path(data_root).resolve(),
                figure_dir=figure_dir,
                run_root=staging,
            )
            recovered_document_path = figure_dir / "figure.pnfig.json"
            self.repository._atomic_write_json(recovered_document_path, document)

            plan = FigureRenderPlanBuilder(staging).build(
                recovered_document_path,
                document,
            )
            profile = get_figure_output_profile(profile_id)
            export = self.exporter.export_initial(
                plan=plan,
                figure_dir=figure_dir,
                profile=profile,
            )
            assets = {
                role: self._relative(path, staging)
                for role, path in export.assets.items()
            }
            document["export"] = {
                "profile": profile.profile_id,
                "published_revision": 1,
                "assets": assets,
            }
            self.repository._atomic_write_json(recovered_document_path, document)
            capability = resolve_figure_capabilities(
                plan=plan,
                inspection=export.inspection,
                audit=export.audit,
                working_revision=1,
                published_revision=1,
            )
            data_sources = tuple(
                str(source["path"])
                for source in document["data_sources"]
                if isinstance(source, dict) and source.get("path")
            )
            entry = FigureManifestEntry(
                figure_id=figure_id,
                title=str(document.get("title") or figure_id),
                category=self._recovered_category(document.get("category")),
                status="ready",
                document=self._relative(recovered_document_path, staging),
                data_sources=data_sources,
                assets=assets,
                capability_report=capability.to_payload(),
                working_revision=1,
                published_revision=1,
                error="",
            )
            manifest = RunFigureManifest(
                schema_version=1,
                run_id=run_id,
                technique=str(technique),
                output_profile=profile.profile_id,
                figures=(entry,),
            )
            self.repository._atomic_write_json(
                staging / "run_metadata.json",
                {
                    "schema_version": 1,
                    "run_id": run_id,
                    "technique": str(technique),
                    "output_profile": profile.profile_id,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "recovery_kind": "document_repair",
                    "source_document": str(source_document_path),
                },
            )
            self.repository.write_manifest(staging, manifest)
            staging.rename(final_run_root)
            committed = True
            self.repository.activate(run_id)
            return manifest
        except BaseException:
            if not committed:
                shutil.rmtree(staging, ignore_errors=True)
            raise

    def _copy_data_sources(
        self,
        *,
        sources: object,
        data_root: Path,
        figure_dir: Path,
        run_root: Path,
    ) -> list[dict[str, object]]:
        if not isinstance(sources, list) or not sources:
            raise ValueError("recovered document has no data sources")
        destination_dir = figure_dir / "data"
        destination_dir.mkdir()
        recovered_sources = []
        for index, raw_source in enumerate(sources, start=1):
            if not isinstance(raw_source, dict):
                raise ValueError("recovered data source must be an object")
            source = deepcopy(raw_source)
            if str(source.get("kind") or "") != "csv":
                raise ValueError(
                    f"unsupported recovered data source kind: {source.get('kind')}"
                )
            source_path = self._source_path(data_root, str(source.get("path") or ""))
            if not source_path.is_file():
                raise FileNotFoundError(source_path)
            source_id = re.sub(
                r"[^A-Za-z0-9._-]+",
                "-",
                str(source.get("id") or f"source-{index:03d}"),
            ).strip("-.") or f"source-{index:03d}"
            suffix = source_path.suffix.lower() or ".csv"
            destination = destination_dir / f"{source_id}{suffix}"
            if destination.exists():
                destination = destination_dir / f"{source_id}-{index:03d}{suffix}"
            shutil.copy2(source_path, destination)
            source["path_kind"] = "run_relative"
            source["path"] = self._relative(destination, run_root)
            source["sha256"] = hashlib.sha256(destination.read_bytes()).hexdigest()
            recovered_sources.append(source)
        return recovered_sources

    @staticmethod
    def _source_path(data_root: Path, path_text: str) -> Path:
        path = Path(path_text)
        return path.resolve() if path.is_absolute() else (data_root / path).resolve()

    @staticmethod
    def _relative(path: Path, run_root: Path) -> str:
        return Path(path).resolve().relative_to(Path(run_root).resolve()).as_posix()

    @staticmethod
    def _recovered_category(value: object) -> str:
        category = str(value or "")
        if category in {"series_overview", "per_frame", "diagnostic", "supplementary"}:
            return category
        return "supplementary"

    @staticmethod
    def _read_json(path: Path) -> dict[str, object]:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise ValueError(f"document JSON object expected: {path}")
        return payload
