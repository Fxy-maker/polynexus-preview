from __future__ import annotations

import importlib
import json

import pytest

from polynexus.core.figure_assets import read_figure_asset_dimensions
from polynexus.core.figures.pipeline import FigurePipeline


def test_recovery_pipeline_repairs_document_into_new_immutable_run(
    built_ir_document,
    tmp_path,
):
    module = importlib.import_module("polynexus.core.figures.recovery_pipeline")
    legacy_run_root, document_path, document = built_ir_document
    source_paths = [legacy_run_root / item["path"] for item in document["data_sources"]]
    document_before = document_path.read_bytes()
    data_before = {path: path.read_bytes() for path in source_paths}
    output_root = tmp_path / "recovered-output"

    manifest = module.FigureRecoveryPipeline(output_root).recover_document(
        run_id="recovered-run",
        technique="ir",
        document_path=document_path,
        data_root=legacy_run_root,
        profile_id="paper_complete",
    )

    entry = manifest.figures[0]
    run_root = output_root / "runs" / "recovered-run"
    recovered_document = json.loads((run_root / entry.document).read_text("utf-8"))
    assert entry.status == "ready"
    assert entry.working_revision == entry.published_revision == 1
    assert entry.capability_report["editing_mode"] == "object"
    assert entry.capability_report["publication_status"] == "quality_failed"
    assert entry.capability_report["audit_passed"] is False
    assert entry.capability_report["audit_issues"]
    assert set(entry.assets) == {"preview", "svg", "png", "pdf"}
    assert read_figure_asset_dimensions(run_root / entry.assets["png"])[2] == 600
    assert recovered_document["run_id"] == "recovered-run"
    assert recovered_document["revision"] == 1
    assert all(
        source["path_kind"] == "run_relative"
        and not source["path"].startswith(("/", "\\"))
        and source["sha256"]
        for source in recovered_document["data_sources"]
    )
    assert document_path.read_bytes() == document_before
    assert all(path.read_bytes() == data_before[path] for path in source_paths)
    assert json.loads((output_root / "active_run.json").read_text("utf-8")) == {
        "run_id": "recovered-run"
    }


def test_recovery_pipeline_failure_preserves_active_run_and_cleans_staging(
    built_ir_document,
    ir_definition,
    tmp_path,
):
    module = importlib.import_module("polynexus.core.figures.recovery_pipeline")
    legacy_run_root, document_path, _document = built_ir_document
    output_root = tmp_path / "recovered-output"
    FigurePipeline().run(
        output_root=output_root,
        run_id="current-run",
        technique="ir",
        definitions=(ir_definition,),
    )
    active_pointer = output_root / "active_run.json"
    pointer_before = active_pointer.read_bytes()

    class _FailingExporter:
        def export_initial(self, **_kwargs):
            raise RuntimeError("recovery export failed")

    pipeline = module.FigureRecoveryPipeline(
        output_root,
        exporter=_FailingExporter(),
    )

    with pytest.raises(RuntimeError, match="recovery export failed"):
        pipeline.recover_document(
            run_id="failed-run",
            technique="ir",
            document_path=document_path,
            data_root=legacy_run_root,
        )

    assert active_pointer.read_bytes() == pointer_before
    assert not (output_root / "runs" / "failed-run").exists()
    assert not (output_root / "runs" / ".failed-run.staging").exists()
