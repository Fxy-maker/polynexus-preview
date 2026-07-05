"""
PolyNexus SCI plotting module.

Publication-quality matplotlib configuration.

v2.0: Adds sci_style module with unified cross-technique SCI output spec.
v3.0: Added GRAYSCALE_PALETTE, JOURNAL_PRESETS, apply_panel_label,
      make_composite_figure — all techniques import from sci_style.
"""

import matplotlib
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Optional, Tuple

from .sci_style import (
    set_sci_style, apply_axis_sci_style, save_figure_sci,
    WONG_COLORS, GRAYSCALE_PALETTE, ANNOTATION_COLORS,
    CMAP_INTENSITY, CMAP_DIVERGE, CMAP_FRACTION,
    TECHNIQUE_ACCENT,
    FIG_SIZES, JOURNAL_PRESETS, JOURNAL_EXPORT,
    AXIS_LABELS,
    apply_panel_label, make_composite_figure,
    QUALITY_FLAGS, TECHNIQUE_QUALITY_FLAGS, get_quality_label,
    OUTPUT_DIR_TEMPLATE, create_output_structure,
)


COLORS = {
    'raw': '#b0b8c4', 'smooth': '#2563eb', 'baseline': '#ef4444',
    'corrected': '#0d9488', 'peak': '#dc2626',
    'crystal': '#f97316', 'amorph': '#60a5fa',
    'palette': ['#2563eb', '#ef4444', '#22c55e', '#f97316', '#a855f7',
                '#ec4899', '#0d9488', '#eab308', '#6366f1', '#14b8a6'],
}

FIG_SIZES_LEGACY = {
    'single': (3.35, 2.56),
    'double': (6.89, 2.56),
    'double_2x2': (6.89, 5.12),
}


def set_sci_style_legacy(font_size: float = 8.0, dpi: int = 150):
    """Configure matplotlib for SCI publication quality (legacy API).

    Prefer set_sci_style() from sci_style module for new code.
    """
    set_sci_style(font_size=font_size, dpi=dpi)


def save_figure(fig, filepath: str, formats=None, dpi: int = 300):
    """Save figure in multiple formats (legacy API).

    Prefer save_figure_sci() from sci_style module for new code.
    """
    return save_figure_sci(fig, filepath, formats=formats, dpi=dpi)
