from pathlib import Path

import pytest

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
