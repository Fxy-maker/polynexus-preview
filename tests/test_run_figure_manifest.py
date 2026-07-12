import json

import pytest

from polynexus.core.figures.capabilities import resolve_figure_capabilities
from polynexus.core.figures.manifest import (
    FigureManifestEntry,
    RunFigureManifest,
    RunFigureManifestRepository,
)
from polynexus.core.figures.publication_audit import FigurePublicationAuditResult


def test_capability_report_separates_editing_from_publication(
    render_plan,
    complete_inspection,
):
    report = resolve_figure_capabilities(
        plan=render_plan,
        inspection=complete_inspection,
        working_revision=2,
        published_revision=1,
    )

    assert report.editing_mode == "object"
    assert report.object_editing is True
    assert report.publication_status == "unpublished_changes"
    assert report.audit_passed is True
    assert report.audit_issues == ()


def test_capability_report_marks_explicit_audit_failure(
    render_plan,
    complete_inspection,
):
    audit = FigurePublicationAuditResult(
        passed=False,
        issues=(
            {
                "code": "missing_panel_label",
                "message": "Expected panel labels.",
                "severity": "error",
                "detail": "found 0, expected 1",
            },
        ),
    )

    report = resolve_figure_capabilities(
        plan=render_plan,
        inspection=complete_inspection,
        audit=audit,
        working_revision=1,
        published_revision=1,
    )

    assert report.publication_status == "quality_failed"
    assert report.audit_passed is False
    assert report.audit_issues == audit.issues
    assert report.to_payload()["audit_issues"] == [dict(audit.issues[0])]


def test_manifest_repository_commits_relative_paths_and_active_pointer(tmp_path):
    repository = RunFigureManifestRepository(tmp_path)
    manifest = _ready_manifest()

    repository.write_manifest(tmp_path / "runs" / "run-1", manifest)
    repository.activate("run-1")

    payload = json.loads(
        (tmp_path / "runs" / "run-1" / "figure_manifest.json").read_text("utf-8")
    )
    active = json.loads((tmp_path / "active_run.json").read_text("utf-8"))
    assert payload["figures"][0]["document"].startswith("figures/")
    assert active == {"run_id": "run-1"}


def test_manifest_repository_rejects_absolute_ready_paths(tmp_path):
    manifest = _ready_manifest(document=str((tmp_path / "figure.json").resolve()))

    with pytest.raises(ValueError, match="run-relative"):
        RunFigureManifestRepository(tmp_path).write_manifest(
            tmp_path / "runs" / "run-1",
            manifest,
        )


def test_manifest_repository_reads_manifest_and_active_run(tmp_path):
    repository = RunFigureManifestRepository(tmp_path)
    manifest = _ready_manifest()
    run_root = tmp_path / "runs" / "run-1"
    repository.write_manifest(run_root, manifest)
    repository.activate("run-1")

    loaded = repository.read_manifest(run_root)
    active_root, active = repository.read_active_manifest()

    assert loaded == manifest
    assert active == manifest
    assert active_root == run_root.resolve()


def _ready_manifest(*, document="figures/ir.frame.spectrum.001/figure.pnfig.json"):
    return RunFigureManifest(
        schema_version=1,
        run_id="run-1",
        technique="ir",
        output_profile="paper_complete",
        figures=(
            FigureManifestEntry(
                figure_id="ir.frame.spectrum.001",
                title="IR Spectrum",
                category="per_frame",
                status="ready",
                document=document,
                data_sources=(
                    "figures/ir.frame.spectrum.001/data/spectrum-data.csv",
                ),
                assets={
                    "preview": "figures/ir.frame.spectrum.001/assets/preview.png",
                    "svg": "figures/ir.frame.spectrum.001/assets/figure.svg",
                    "png": "figures/ir.frame.spectrum.001/assets/figure.png",
                    "pdf": "figures/ir.frame.spectrum.001/assets/figure.pdf",
                },
                capability_report={
                    "editing_mode": "object",
                    "object_editing": True,
                    "static_annotation": True,
                    "reason_code": "",
                    "publication_status": "complete",
                },
                working_revision=1,
                published_revision=1,
                error="",
            ),
        ),
    )
