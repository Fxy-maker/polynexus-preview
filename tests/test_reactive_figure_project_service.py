from pathlib import Path

import pytest

from polynexus.core.figures.pipeline import FigurePipeline
from polynexus.core.figures.reactive_project_service import ReactiveFigureProjectService
from polynexus.plot_runtime.commands import EditWorksheetCells
from polynexus.plot_runtime.matplotlib_renderer import PublicationProfile
from tests.test_reactive_figure_temperature_saxs import _definition


def test_reactive_project_service_saves_and_publishes_new_v2_revisions(tmp_path):
    manifest = FigurePipeline().run(
        output_root=tmp_path,
        run_id="v2-project",
        technique="saxs",
        definitions=(_definition(),),
    )
    entry_before = manifest.figures[0]
    run_root = Path(tmp_path) / "runs" / "v2-project"
    source_files_before = {
        path: path.read_bytes()
        for path in (run_root / "figures" / entry_before.figure_id).rglob("*.csv")
    }
    service = ReactiveFigureProjectService(tmp_path)
    handle = service.load(run_id="v2-project", figure_id=entry_before.figure_id)

    update = handle.session.execute(EditWorksheetCells({"profile-0::intensity": {1: 4.0}}))
    assert update.ok
    saved = service.save_working(handle)
    published = service.publish(handle, profile=PublicationProfile(dpi=100))

    assert saved.working_revision == 1
    assert published.published_revision == 1
    assert len(published.assets) == 4
    assert all(path.exists() and path.stat().st_size > 0 for path in published.assets)
    assert source_files_before == {
        path: path.read_bytes()
        for path in source_files_before
    }
    manifest_after = service.read_manifest()
    updated_entry = manifest_after.figures[0]
    assert updated_entry.assets == entry_before.assets
    assert updated_entry.capability_report["v2_working_revision"] == 1
    assert updated_entry.capability_report["v2_published_revision"] == 1


def test_reactive_project_service_rejects_publication_of_unsaved_working_state(tmp_path):
    manifest = FigurePipeline().run(
        output_root=tmp_path,
        run_id="v2-unsaved-publication",
        technique="saxs",
        definitions=(_definition(),),
    )
    figure_id = manifest.figures[0].figure_id
    service = ReactiveFigureProjectService(tmp_path)
    handle = service.load(run_id="v2-unsaved-publication", figure_id=figure_id)

    assert handle.session.execute(EditWorksheetCells({"profile-0::intensity": {1: 4.0}})).ok
    assert service.save_working(handle).working_revision == 1
    assert handle.session.execute(EditWorksheetCells({"profile-0::intensity": {1: 5.0}})).ok

    with pytest.raises(ValueError, match="Save the working revision before publishing"):
        service.publish(handle, profile=PublicationProfile(dpi=100))

    publication_root = (
        tmp_path / "runs" / "v2-unsaved-publication" / "figures" / figure_id / "v2_publications"
    )
    assert not publication_root.exists()

    assert service.save_working(handle).working_revision == 2
    published = service.publish(handle, profile=PublicationProfile(dpi=100))
    assert published.published_revision == 2
    assert all(path.exists() for path in published.assets)


def test_approved_route_persists_review_and_default_enable_is_idempotent(tmp_path):
    manifest = FigurePipeline().run(
        output_root=tmp_path,
        run_id="v2-review",
        technique="saxs",
        definitions=(_definition(),),
    )
    figure_id = manifest.figures[0].figure_id
    service = ReactiveFigureProjectService(tmp_path)
    handle = service.load(run_id="v2-review", figure_id=figure_id)

    initial_capability = handle.entry.capability_report
    assert initial_capability["v2_reviewed"] is True
    assert initial_capability["v2_default"] is True
    assert initial_capability["v2_review_record"]["decision"] == "approved"

    reviewed = service.record_review(
        handle,
        reviewer="scientist@example.org",
        decision="approved",
        scope=("architecture", "temperature_saxs", "compatibility"),
        notes="review packet accepted",
    )
    capability = reviewed.manifest.figures[0].capability_report
    assert capability["v2_reviewed"] is True
    assert capability["v2_default"] is False
    assert capability["v2_review_record"]["decision"] == "approved"

    enabled = service.enable_default(handle)
    assert enabled.figures[0].capability_report["v2_default"] is True
    assert enabled.figures[0].capability_report["v2_reviewed"] is True


def test_new_working_revision_invalidates_previous_v2_review(tmp_path):
    manifest = FigurePipeline().run(
        output_root=tmp_path,
        run_id="v2-review-invalidate",
        technique="saxs",
        definitions=(_definition(),),
    )
    figure_id = manifest.figures[0].figure_id
    service = ReactiveFigureProjectService(tmp_path)
    handle = service.load(run_id="v2-review-invalidate", figure_id=figure_id)
    service.record_review(
        handle,
        reviewer="scientist@example.org",
        decision="approved",
        scope=("temperature_saxs",),
    )
    service.enable_default(handle)

    update = handle.session.execute(EditWorksheetCells({"profile-0::intensity": {1: 4.0}}))
    assert update.ok
    saved = service.save_working(handle)
    capability = saved.manifest.figures[0].capability_report

    assert capability["v2_default"] is False
    assert capability["v2_reviewed"] is False
