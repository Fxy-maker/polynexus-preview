"""Atomic export of complete figure artifact groups."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

import matplotlib
from matplotlib.figure import Figure

from .inspector import FigureArtifactInspection, FigureArtifactInspector
from .profiles import FigureOutputProfile
from .render_plan import FigureRenderPlan
from .renderer import MatplotlibFigureRenderer


@dataclass(frozen=True)
class FigureArtifactExportResult:
    assets: dict[str, Path]
    inspection: FigureArtifactInspection


class FigureArtifactExportService:
    """Render, inspect, and atomically commit an initial artifact group."""

    def __init__(
        self,
        *,
        renderer: MatplotlibFigureRenderer | None = None,
        inspector: FigureArtifactInspector | None = None,
    ) -> None:
        self._renderer = renderer or MatplotlibFigureRenderer()
        self._inspector = inspector or FigureArtifactInspector()

    def export_preview(
        self,
        *,
        plan: FigureRenderPlan,
        path: Path,
        profile: FigureOutputProfile,
    ) -> Path:
        path = Path(path).resolve()
        if path.exists():
            raise FileExistsError(f"figure preview already exists: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        with matplotlib.rc_context(
            {
                "svg.fonttype": "none",
                "pdf.fonttype": 42,
                "ps.fonttype": 42,
                "savefig.bbox": None,
            }
        ):
            self._save_preview(plan, path, profile)
        return path

    def export_initial(
        self,
        *,
        plan: FigureRenderPlan,
        figure_dir: Path,
        profile: FigureOutputProfile,
    ) -> FigureArtifactExportResult:
        figure_dir = Path(figure_dir).resolve()
        final_dir = figure_dir / "assets"
        if final_dir.exists():
            raise FileExistsError(f"figure asset group already exists: {final_dir}")

        figure_dir.mkdir(parents=True, exist_ok=True)
        staging_dir = Path(
            tempfile.mkdtemp(prefix=".assets.staging-", dir=figure_dir)
        )
        staged_assets = {
            "preview": staging_dir / profile.preview_filename,
            **{
                role: staging_dir / filename
                for role, filename in profile.formal_assets.items()
            },
        }

        try:
            with matplotlib.rc_context(
                {
                    "svg.fonttype": "none",
                    "pdf.fonttype": 42,
                    "ps.fonttype": 42,
                    "savefig.bbox": None,
                }
            ):
                self._save_preview(plan, staged_assets["preview"], profile)
                self._save_svg(plan, staged_assets["svg"], profile)
                self._save_png(plan, staged_assets["png"], profile)
                self._save_pdf(plan, staged_assets["pdf"], profile)

            inspection = self._inspector.inspect(
                plan=plan,
                assets=staged_assets,
                profile=profile,
            )
            if not inspection.complete:
                raise ValueError(
                    "figure artifact inspection failed: "
                    + "; ".join(inspection.errors)
                )
            staging_dir.rename(final_dir)
        except BaseException:
            shutil.rmtree(staging_dir, ignore_errors=True)
            raise

        final_assets = {
            role: final_dir / path.name for role, path in staged_assets.items()
        }
        return FigureArtifactExportResult(
            assets=final_assets,
            inspection=inspection,
        )

    def _save_preview(
        self,
        plan: FigureRenderPlan,
        path: Path,
        profile: FigureOutputProfile,
    ) -> None:
        figure = self._renderer.render(plan, dpi=profile.preview_dpi)
        self._save_figure(
            figure,
            path,
            file_format="png",
            dpi=profile.preview_dpi,
            background=profile.background,
        )

    def _save_svg(
        self,
        plan: FigureRenderPlan,
        path: Path,
        profile: FigureOutputProfile,
    ) -> None:
        figure = self._renderer.render(plan, dpi=profile.preview_dpi)
        self._save_figure(
            figure,
            path,
            file_format="svg",
            background=profile.background,
        )

    def _save_png(
        self,
        plan: FigureRenderPlan,
        path: Path,
        profile: FigureOutputProfile,
    ) -> None:
        figure = self._renderer.render(plan, dpi=profile.publication_png_dpi)
        self._save_figure(
            figure,
            path,
            file_format="png",
            dpi=profile.publication_png_dpi,
            background=profile.background,
        )

    def _save_pdf(
        self,
        plan: FigureRenderPlan,
        path: Path,
        profile: FigureOutputProfile,
    ) -> None:
        figure = self._renderer.render(plan, dpi=profile.preview_dpi)
        self._save_figure(
            figure,
            path,
            file_format="pdf",
            background=profile.background,
        )

    @staticmethod
    def _save_figure(
        figure: Figure,
        path: Path,
        *,
        file_format: str,
        background: str,
        dpi: int | None = None,
    ) -> None:
        try:
            save_options = {
                "format": file_format,
                "facecolor": background,
            }
            if dpi is not None:
                save_options["dpi"] = dpi
            figure.savefig(path, **save_options)
        finally:
            figure.clear()
