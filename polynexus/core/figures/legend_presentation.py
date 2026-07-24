"""Responsive, document-safe presentation rules for Matplotlib legends."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .legend_geometry import import_legend_geometry


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
    labels: tuple[str, ...] | list[str] = (),
) -> LegendPresentation:
    """Choose compact rendering only for narrow automatic multi-series legends."""

    figure_object = figure_object if isinstance(figure_object, dict) else {}
    style = figure_object.get("style", {})
    style = style if isinstance(style, dict) else {}
    explicit_fontsize = _positive_finite_float(style.get("font_size"))
    effective_fontsize = explicit_fontsize or default_fontsize
    layout_width_px = float(available_width_px)
    geometry = import_legend_geometry(style)
    if geometry.rect_axes is not None:
        layout_width_px *= geometry.rect_axes[2]
    elif geometry.size_axes is not None:
        layout_width_px *= geometry.size_axes[0]
    count = max(0, int(handle_count or 0))
    automatic = figure_object.get("auto_generated") is True
    compact = (
        automatic
        and count > 3
        and layout_width_px < _COMPACT_LEGEND_WIDTH_PX
    )
    try:
        requested_columns = max(1, int(style.get("ncol") or (2 if count > 3 else 1)))
    except (TypeError, ValueError):
        requested_columns = 2 if count > 3 else 1
    columns = 1 if compact else requested_columns
    if automatic and columns > 1 and labels and effective_fontsize is not None:
        longest_label = max(len(str(label or "")) for label in labels)
        entry_width = max(72.0, longest_label * float(effective_fontsize) * 0.78 + 54.0)
        column_budget = max(1, int(layout_width_px * 0.42 // entry_width))
        columns = min(columns, column_budget)
        compact = compact or columns < requested_columns
    fontsize = (
        float(default_fontsize) * _COMPACT_FONT_SCALE
        if compact and explicit_fontsize is None and default_fontsize is not None
        else effective_fontsize
    )
    return LegendPresentation(ncol=columns, fontsize=fontsize)


def _positive_finite_float(value: object) -> float | None:
    try:
        candidate = float(value)
    except (TypeError, ValueError):
        return None
    return candidate if isfinite(candidate) and candidate > 0.0 else None
