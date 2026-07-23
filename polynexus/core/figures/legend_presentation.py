"""Responsive, document-safe presentation rules for Matplotlib legends."""

from __future__ import annotations

from dataclasses import dataclass


_COMPACT_LEGEND_WIDTH_PX = 560.0
_COMPACT_FONT_SCALE = 0.85


@dataclass(frozen=True)
class LegendPresentation:
    """Transient rendering choices that must not mutate figure documents."""

    ncol: int
    fontsize: float | None


def legend_presentation(
    figure_object: dict | None,
    *,
    handle_count: int,
    available_width_px: float,
    default_fontsize: float | None,
) -> LegendPresentation:
    """Choose compact rendering only for narrow automatic multi-series legends."""

    figure_object = figure_object if isinstance(figure_object, dict) else {}
    style = figure_object.get("style", {})
    style = style if isinstance(style, dict) else {}
    count = max(0, int(handle_count or 0))
    automatic = figure_object.get("auto_generated") is True
    compact = (
        automatic
        and count > 3
        and float(available_width_px or 0.0) < _COMPACT_LEGEND_WIDTH_PX
    )
    if compact:
        columns = 1
    else:
        try:
            columns = max(1, int(style.get("ncol") or (2 if count > 3 else 1)))
        except (TypeError, ValueError):
            columns = 2 if count > 3 else 1
    fontsize = (
        float(default_fontsize) * _COMPACT_FONT_SCALE
        if compact and default_fontsize is not None
        else default_fontsize
    )
    return LegendPresentation(ncol=columns, fontsize=fontsize)
