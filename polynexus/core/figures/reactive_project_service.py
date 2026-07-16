"""Persistence and publication lifecycle for the opt-in V2 figure runtime."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from polynexus.plot_runtime.commands import PlotState
from polynexus.plot_runtime.layout import LayoutResolver
from polynexus.plot_runtime.matplotlib_renderer import (
    MatplotlibPublicationRenderer,
    PublicationProfile,
)
from polynexus.plot_runtime.models import GraphDocument, Worksheet
from polynexus.plot_runtime.session import FigureSession

from .manifest import FigureManifestEntry, RunFigureManifest, RunFigureManifestRepository


@dataclass
class ReactiveFigureHandle:
    run_id: str
    figure_id: str
    run_root: Path
    entry: FigureManifestEntry
    session: FigureSession
    sidecar_path: Path


@dataclass(frozen=True)
class ReactiveFigureSaveResult:
    working_revision: int
    sidecar_path: Path
    manifest: RunFigureManifest


@dataclass(frozen=True)
class ReactiveFigurePublishResult:
    published_revision: int
    assets: tuple[Path, ...]
    manifest: RunFigureManifest


@dataclass(frozen=True)
class ReactiveFigureReviewResult:
    reviewed: bool
    manifest: RunFigureManifest


class ReactiveFigureProjectService:
    """Keep V2 working/publication revisions separate from legacy artifacts."""

    def __init__(
        self,
        output_root: str | Path,
        *,
        renderer: MatplotlibPublicationRenderer | None = None,
    ) -> None:
        self.output_root = Path(output_root).resolve()
        self.repository = RunFigureManifestRepository(self.output_root)
        self.renderer = renderer or MatplotlibPublicationRenderer()
        self._last_run_root: Path | None = None

    def load(self, *, run_id: str, figure_id: str) -> ReactiveFigureHandle:
        run_root, manifest = self._load_manifest(run_id)
        entry = next((item for item in manifest.figures if item.figure_id == figure_id), None)
        if entry is None:
            raise KeyError(f"unknown figure ID: {figure_id}")
        capability = entry.capability_report
        if capability.get("v2_runtime") != "ready":
            raise ValueError(f"figure is not V2-ready: {figure_id}")
        sidecar_path = self._absolute_path(run_root, str(capability.get("v2_sidecar") or ""))
        payload = self._read_json(sidecar_path)
        worksheet = Worksheet.from_payload(payload["worksheet"])
        document = GraphDocument.from_payload(payload["graph_document"])
        session = FigureSession(PlotState(worksheet, document), LayoutResolver())
        return ReactiveFigureHandle(
            run_id=str(run_id),
            figure_id=str(figure_id),
            run_root=run_root,
            entry=entry,
            session=session,
            sidecar_path=sidecar_path,
        )

    def save_working(self, handle: ReactiveFigureHandle) -> ReactiveFigureSaveResult:
        revision = int(handle.entry.capability_report.get("v2_working_revision", 0) or 0) + 1
        sidecar_path = (
            handle.run_root
            / "figures"
            / handle.figure_id
            / "v2_revisions"
            / f"r{revision:04d}"
            / "reactive_figure_v2.json"
        )
        sidecar = self._sidecar_payload(handle, revision)
        self.repository._atomic_write_json(sidecar_path, sidecar)
        capability = dict(handle.entry.capability_report)
        capability.update(
            {
                "v2_runtime": "ready",
                "v2_default": False,
                "v2_reviewed": False,
                "v2_sidecar": self._relative(sidecar_path, handle.run_root),
                "v2_working_revision": revision,
            }
        )
        updated_entry = replace(handle.entry, capability_report=capability)
        manifest = self._replace_and_write(handle, updated_entry)
        handle.entry = updated_entry
        handle.sidecar_path = sidecar_path
        return ReactiveFigureSaveResult(revision, sidecar_path, manifest)

    def record_review(
        self,
        handle: ReactiveFigureHandle,
        *,
        reviewer: str,
        decision: str,
        scope: tuple[str, ...] = (),
        notes: str = "",
    ) -> ReactiveFigureReviewResult:
        """Persist a human review without enabling the V2 default route."""

        reviewer_text = str(reviewer or "").strip()
        decision_text = str(decision or "").strip().lower()
        if not reviewer_text:
            raise ValueError("reviewer is required")
        if decision_text not in {"approved", "rejected"}:
            raise ValueError("review decision must be approved or rejected")
        normalized_scope = tuple(
            sorted({str(item).strip() for item in scope if str(item).strip()})
        )
        if not normalized_scope:
            raise ValueError("review scope is required")

        capability = dict(handle.entry.capability_report)
        capability.update(
            {
                "v2_reviewed": decision_text == "approved",
                "v2_default": False,
                "v2_review_record": {
                    "reviewer": reviewer_text,
                    "decision": decision_text,
                    "scope": list(normalized_scope),
                    "notes": str(notes or "").strip(),
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                },
            }
        )
        updated_entry = replace(handle.entry, capability_report=capability)
        manifest = self._replace_and_write(handle, updated_entry)
        handle.entry = updated_entry
        return ReactiveFigureReviewResult(decision_text == "approved", manifest)

    def enable_default(self, handle: ReactiveFigureHandle) -> RunFigureManifest:
        """Enable the default V2 route only after an approved review record."""

        capability = dict(handle.entry.capability_report)
        review_record = capability.get("v2_review_record")
        if (
            capability.get("v2_runtime") != "ready"
            or capability.get("v2_reviewed") is not True
            or not isinstance(review_record, dict)
            or review_record.get("decision") != "approved"
        ):
            raise ValueError("enabling V2 default requires an approved V2 review")
        capability["v2_default"] = True
        updated_entry = replace(handle.entry, capability_report=capability)
        manifest = self._replace_and_write(handle, updated_entry)
        handle.entry = updated_entry
        return manifest

    def publish(
        self,
        handle: ReactiveFigureHandle,
        *,
        profile: PublicationProfile | None = None,
    ) -> ReactiveFigurePublishResult:
        revision = int(handle.entry.capability_report.get("v2_working_revision", 0) or 0)
        if revision <= 0:
            raise ValueError("V2 figure has no saved working revision")
        self._require_saved_current_state(handle, revision)
        publication_dir = (
            handle.run_root
            / "figures"
            / handle.figure_id
            / "v2_publications"
            / f"r{revision:04d}"
        )
        if publication_dir.exists():
            raise FileExistsError(f"V2 publication revision already exists: {publication_dir}")
        result = self.renderer.export(
            handle.session.scene,
            publication_dir / "figure",
            profile=profile or PublicationProfile(dpi=handle.session.scene.dpi),
            provenance={
                "run_id": handle.run_id,
                "figure_id": handle.figure_id,
                "data_revision_id": handle.session.state.worksheet.current.revision_id,
                "graph_revision_id": handle.session.state.document.revision_id,
                "scene_revision_id": handle.session.scene.revision_id,
            },
        )
        if not result.ok:
            raise ValueError("V2 publication failed: " + "; ".join(item.message for item in result.diagnostics))
        assets = {path.suffix.lstrip("."): self._relative(path, handle.run_root) for path in result.paths}
        capability = dict(handle.entry.capability_report)
        capability.update(
            {
                "v2_published_revision": revision,
                "v2_assets": assets,
                "v2_provenance": dict(result.provenance),
            }
        )
        updated_entry = replace(handle.entry, capability_report=capability)
        manifest = self._replace_and_write(handle, updated_entry)
        handle.entry = updated_entry
        return ReactiveFigurePublishResult(revision, result.paths, manifest)

    def read_manifest(self) -> RunFigureManifest:
        if self._last_run_root is None:
            raise RuntimeError("load a V2 figure before reading its manifest")
        return self.repository.read_manifest(self._last_run_root)

    def _require_saved_current_state(self, handle: ReactiveFigureHandle, revision: int) -> None:
        payload = self._read_json(handle.sidecar_path)
        if int(payload.get("working_revision", 0) or 0) != revision:
            raise ValueError("V2 working sidecar does not match the manifest revision")
        saved_data_revision = str(payload.get("source_revision_id") or "")
        saved_graph_revision = str(payload.get("graph_revision_id") or "")
        current_data_revision = handle.session.state.worksheet.current.revision_id
        current_graph_revision = handle.session.state.document.revision_id
        if (saved_data_revision, saved_graph_revision) != (
            current_data_revision,
            current_graph_revision,
        ):
            raise ValueError("Save the working revision before publishing V2 figure changes")

    def _load_manifest(self, run_id: str) -> tuple[Path, RunFigureManifest]:
        run_root = (self.output_root / "runs" / str(run_id)).resolve()
        run_root.relative_to((self.output_root / "runs").resolve())
        manifest = self.repository.read_manifest(run_root)
        if manifest.run_id != str(run_id):
            raise ValueError(f"run ID mismatch: {run_id} != {manifest.run_id}")
        self._last_run_root = run_root
        return run_root, manifest

    def _replace_and_write(
        self,
        handle: ReactiveFigureHandle,
        updated_entry: FigureManifestEntry,
    ) -> RunFigureManifest:
        manifest = self.repository.read_manifest(handle.run_root)
        updated = replace(
            manifest,
            figures=tuple(
                updated_entry if item.figure_id == updated_entry.figure_id else item
                for item in manifest.figures
            ),
        )
        self.repository.write_manifest(handle.run_root, updated)
        return updated

    @staticmethod
    def _sidecar_payload(handle: ReactiveFigureHandle, revision: int) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "runtime": "reactive_figure_v2",
            "figure_id": handle.figure_id,
            "working_revision": revision,
            "source_revision_id": handle.session.state.worksheet.current.revision_id,
            "graph_revision_id": handle.session.state.document.revision_id,
            "worksheet": handle.session.state.worksheet.to_payload(),
            "graph_document": handle.session.state.document.to_payload(),
        }

    @staticmethod
    def _relative(path: Path, run_root: Path) -> str:
        return Path(path).resolve().relative_to(Path(run_root).resolve()).as_posix()

    @staticmethod
    def _absolute_path(run_root: Path, relative_path: str) -> Path:
        if not relative_path:
            raise ValueError("V2 sidecar path is empty")
        path = (run_root / Path(relative_path)).resolve()
        path.relative_to(run_root)
        return path

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise ValueError(f"JSON object expected: {path}")
        return payload
