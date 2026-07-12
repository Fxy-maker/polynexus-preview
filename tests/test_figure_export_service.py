from pathlib import Path

import matplotlib
import pytest

from polynexus.core.figure_assets import read_figure_asset_dimensions
from polynexus.core.figures.export_service import FigureArtifactExportService
from polynexus.core.figures.profiles import get_figure_output_profile


def test_export_service_creates_complete_paper_asset_group(render_plan, tmp_path):
    profile = get_figure_output_profile("paper_complete")

    result = FigureArtifactExportService().export_initial(
        plan=render_plan,
        figure_dir=tmp_path / "figure",
        profile=profile,
    )

    assert set(result.assets) == {"preview", "svg", "png", "pdf"}
    assert all(Path(path).exists() for path in result.assets.values())
    assert result.inspection.complete is True
    assert result.inspection.png_dpi == 600
    assert result.audit.passed is False
    assert result.audit.issues


def test_export_failure_does_not_commit_partial_assets(
    render_plan,
    tmp_path,
    monkeypatch,
):
    service = FigureArtifactExportService()
    monkeypatch.setattr(
        service,
        "_save_pdf",
        lambda *args: (_ for _ in ()).throw(RuntimeError("pdf failed")),
    )
    figure_dir = tmp_path / "figure"

    with pytest.raises(RuntimeError, match="pdf failed"):
        service.export_initial(
            plan=render_plan,
            figure_dir=figure_dir,
            profile=get_figure_output_profile("paper_complete"),
        )

    assert not (figure_dir / "assets").exists()


def test_export_service_ignores_process_global_tight_bbox(render_plan, tmp_path):
    with matplotlib.rc_context({"savefig.bbox": "tight"}):
        result = FigureArtifactExportService().export_initial(
            plan=render_plan,
            figure_dir=tmp_path / "figure",
            profile=get_figure_output_profile("paper_complete"),
        )

    assert result.inspection.complete is True
    assert result.inspection.dimensions["png"][0:2] == (1200, 600)


def test_export_service_owns_working_preview_output(render_plan, tmp_path):
    profile = get_figure_output_profile("paper_complete")
    preview_path = tmp_path / "revisions" / "r0002" / profile.preview_filename

    result = FigureArtifactExportService().export_preview(
        plan=render_plan,
        path=preview_path,
        profile=profile,
    )

    assert result == preview_path.resolve()
    assert read_figure_asset_dimensions(result) == (300, 150, 150)
    assert [item.name for item in result.parent.iterdir()] == [
        profile.preview_filename
    ]
