"""Global output profiles shared by every figure provider."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FigureOutputProfile:
    profile_id: str
    preview_filename: str
    preview_dpi: int
    publication_png_dpi: int
    formal_assets: dict[str, str]
    background: str = "white"
    svg_font_policy: str = "editable_text"
    pdf_font_policy: str = "embedded"


_PROFILES = {
    "paper_complete": FigureOutputProfile(
        profile_id="paper_complete",
        preview_filename="preview.png",
        preview_dpi=150,
        publication_png_dpi=600,
        formal_assets={
            "svg": "figure.svg",
            "png": "figure.png",
            "pdf": "figure.pdf",
        },
    ),
    "dsc_publication": FigureOutputProfile(
        profile_id="dsc_publication",
        preview_filename="preview.png",
        preview_dpi=150,
        publication_png_dpi=600,
        formal_assets={
            "svg": "figure.svg",
            "png": "figure.png",
            "pdf": "figure.pdf",
            "tiff": "figure.tiff",
        },
    ),
}


def get_figure_output_profile(profile_id: str) -> FigureOutputProfile:
    try:
        return _PROFILES[str(profile_id)]
    except KeyError as exc:
        raise ValueError(f"Unknown figure output profile: {profile_id}") from exc
