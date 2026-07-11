from copy import deepcopy

import pytest

from polynexus.core.figure_assets import read_figure_asset_dimensions
from polynexus.core.figures.pipeline import FigurePipeline
from polynexus.core.figures.project_service import FigureProjectService


def test_save_working_advances_only_working_revision(ir_definition, tmp_path):
    initial = FigurePipeline().run(
        output_root=tmp_path,
        run_id="run-1",
        technique="ir",
        definitions=(ir_definition,),
    )
    initial_entry = initial.figures[0]
    run_root = tmp_path / "runs" / "run-1"
    formal_before = {
        role: (run_root / initial_entry.assets[role]).read_bytes()
        for role in ("svg", "png", "pdf")
    }
    document = deepcopy(
        __import__("json").loads(
            (run_root / initial_entry.document).read_text("utf-8")
        )
    )
    document["objects"][0]["style"]["color"] = "#D55E00"

    update = FigureProjectService(tmp_path).save_working(
        run_id="run-1",
        figure_id=initial_entry.figure_id,
        document=document,
    )

    entry = update.entry
    assert entry.working_revision == 2
    assert entry.published_revision == 1
    assert entry.capability_report["publication_status"] == "unpublished_changes"
    assert "revisions/r0002/" in entry.document
    assert "revisions/r0002/" in entry.assets["preview"]
    assert {role: entry.assets[role] for role in formal_before} == {
        role: initial_entry.assets[role] for role in formal_before
    }
    assert all(
        (run_root / entry.assets[role]).read_bytes() == formal_before[role]
        for role in formal_before
    )


def test_publish_commits_one_complete_new_asset_group(ir_definition, tmp_path):
    initial = FigurePipeline().run(
        output_root=tmp_path,
        run_id="run-1",
        technique="ir",
        definitions=(ir_definition,),
    )
    run_root = tmp_path / "runs" / "run-1"
    document = deepcopy(
        __import__("json").loads(
            (run_root / initial.figures[0].document).read_text("utf-8")
        )
    )
    document["objects"][0]["style"]["line_width"] = 1.7
    service = FigureProjectService(tmp_path)
    service.save_working(
        run_id="run-1",
        figure_id=initial.figures[0].figure_id,
        document=document,
    )

    update = service.publish(
        run_id="run-1",
        figure_id=initial.figures[0].figure_id,
    )

    entry = update.entry
    assert entry.working_revision == entry.published_revision == 2
    assert entry.capability_report["publication_status"] == "complete"
    assert all("publications/r0002/assets/" in path for path in entry.assets.values())
    assert read_figure_asset_dimensions(run_root / entry.assets["png"])[2] == 600
    assert update.document["export"]["assets"] == entry.assets


def test_publish_failure_preserves_previous_manifest(ir_definition, tmp_path):
    initial = FigurePipeline().run(
        output_root=tmp_path,
        run_id="run-1",
        technique="ir",
        definitions=(ir_definition,),
    )
    run_root = tmp_path / "runs" / "run-1"
    document = __import__("json").loads(
        (run_root / initial.figures[0].document).read_text("utf-8")
    )
    service = FigureProjectService(tmp_path)
    service.save_working(
        run_id="run-1",
        figure_id=initial.figures[0].figure_id,
        document=document,
    )
    manifest_path = run_root / "figure_manifest.json"
    manifest_before = manifest_path.read_bytes()

    class _FailingExporter:
        def export_initial(self, **_kwargs):
            raise RuntimeError("writer failed")

    failing = FigureProjectService(tmp_path, exporter=_FailingExporter())
    with pytest.raises(RuntimeError, match="writer failed"):
        failing.publish(
            run_id="run-1",
            figure_id=initial.figures[0].figure_id,
        )

    assert manifest_path.read_bytes() == manifest_before
