"""Consistency inspection for complete figure artifact groups."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from polynexus.core.figure_assets import read_figure_asset_dimensions

from .profiles import FigureOutputProfile
from .render_plan import FigureRenderPlan


@dataclass(frozen=True)
class FigureArtifactInspection:
    complete: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    dimensions: dict[str, tuple[int, int, int]]
    png_dpi: int


class FigureArtifactInspector:
    """Verify required roles and format-independent canvas geometry."""

    _FORMAL_GEOMETRY_ROLES = ("svg", "png", "pdf", "tiff")
    _ASPECT_RATIO_TOLERANCE = 0.01

    def inspect(
        self,
        *,
        plan: FigureRenderPlan,
        assets: dict[str, Path],
        profile: FigureOutputProfile,
    ) -> FigureArtifactInspection:
        errors: list[str] = []
        dimensions: dict[str, tuple[int, int, int]] = {}
        required_roles = tuple(profile.formal_assets)
        if profile.preview_filename:
            required_roles = ("preview", *required_roles)

        for role in required_roles:
            path = assets.get(role)
            if path is None or not path.is_file() or path.stat().st_size <= 0:
                errors.append(f"missing or empty asset: {role}")
                continue
            dimensions[role] = read_figure_asset_dimensions(path)

        png_dpi = dimensions.get("png", (0, 0, 0))[2]
        if "png" in profile.formal_assets and png_dpi != profile.publication_png_dpi:
            errors.append(
                f"publication PNG DPI is {png_dpi}, "
                f"expected {profile.publication_png_dpi}"
            )

        if "tiff" in profile.formal_assets:
            tiff_dpi = dimensions.get("tiff", (0, 0, 0))[2]
            if tiff_dpi != profile.publication_png_dpi:
                errors.append(
                    f"publication TIFF DPI is {tiff_dpi}, "
                    f"expected {profile.publication_png_dpi}"
                )

        expected_ratio = plan.width_in / plan.height_in
        for role in self._FORMAL_GEOMETRY_ROLES:
            if role not in dimensions:
                continue
            width, height, _dpi = dimensions[role]
            if width <= 0 or height <= 0:
                errors.append(f"could not read asset dimensions: {role}")
                continue
            actual_ratio = width / height
            relative_error = abs(actual_ratio - expected_ratio) / expected_ratio
            if relative_error > self._ASPECT_RATIO_TOLERANCE:
                errors.append(
                    f"{role} aspect ratio {actual_ratio:.6g} does not match "
                    f"render plan {expected_ratio:.6g}"
                )

        return FigureArtifactInspection(
            complete=not errors,
            errors=tuple(errors),
            warnings=(),
            dimensions=dimensions,
            png_dpi=png_dpi,
        )
