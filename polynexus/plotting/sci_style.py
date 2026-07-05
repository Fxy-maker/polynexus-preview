"""
Global SCI publication-quality output specification for PolyNexus.

Unified from per-technique output specifications (SAXS/DSC/WAXS design docs).
All engines share this single source of truth for:

- Color palettes (Wong colorblind-friendly + grayscale)
- Figure sizes (single-column / double-column, per-journal presets)
- Font specifications
- Axis styling
- Export formats (PDF / TIFF / PNG / SVG)
- Heatmap / diverging colormaps
- LaTeX axis labels
- Panel label helpers (a/b/c for multi-panel figures)
- Composite figure builder
- Quality flag system (cross-technique)

Usage:
    from polynexus.plotting.sci_style import set_sci_style, WONG_COLORS, FIG_SIZES
    set_sci_style()
"""

from __future__ import annotations
import logging
logger = logging.getLogger(__name__)


import matplotlib as mpl
import matplotlib.pyplot as plt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

# ═══════════════════════════════════════════════════════════════════════════════
# 1. Color Palettes
# ═══════════════════════════════════════════════════════════════════════════════

# Wong colorblind-friendly palette (Nature Methods, 2011)
# Suitable for sequential multi-curve plots
WONG_COLORS: List[str] = [
    "#000000",  # Black
    "#E69F00",  # Orange
    "#56B4E9",  # Sky blue
    "#009E73",  # Green
    "#F0E442",  # Yellow
    "#0072B2",  # Blue
    "#D55E00",  # Red-orange
    "#CC79A7",  # Magenta
]

# Grayscale palette — for journals that forbid colour (e.g. some print editions)
GRAYSCALE_PALETTE: List[str] = [
    "#000000",  # Black (solid)
    "#333333",  # Dark gray
    "#666666",  # Mid gray
    "#999999",  # Light gray
    "#BBBBBB",  # Lighter gray
    "#DDDDDD",  # Very light gray (use with dashed line)
]

# Annotation colors
ANNOTATION_COLORS = {
    "peak_line":     "#E63946",   # Red - peak position markers
    "reference":     "#457B9D",   # Blue - reference lines / baselines
    "phase_divider": "#2D6A4F",   # Dark green - phase boundary (dashed)
    "fit_curve":     "#F4A261",   # Warm orange - fitted curve
    "residual":      "#999999",   # Gray - residual difference
}

# Colormaps for different data types
CMAP_INTENSITY  = "viridis"   # Scattering / diffraction intensity
CMAP_DIVERGE    = "RdBu_r"    # Parameters with positive/negative variation
CMAP_FRACTION   = "plasma"    # Crystallinity / order parameter (0 to 1)
CMAP_DEFAULT    = "viridis"

# Technique-specific accent colors (for GUI / plot branding)
TECHNIQUE_ACCENT: Dict[str, str] = {
    "dsc":  "#E69F00",  # orange - heat
    "saxs": "#56B4E9",  # sky blue - nanoscale
    "waxs": "#0072B2",  # blue - crystal
    "nmr":  "#CC79A7",  # magenta - spin
    "ir":   "#D55E00",  # red-orange - vibration
}

# ═══════════════════════════════════════════════════════════════════════════════
# 2. Figure Sizes (inches)
# ═══════════════════════════════════════════════════════════════════════════════

FIG_SIZES: Dict[str, Tuple[float, float]] = {
    # Single-column (8.5 cm wide, ~3.35 in)
    "single_col":       (3.35, 2.56),
    "single_col_sq":    (3.35, 3.35),
    "single_col_2x1":   (3.35, 5.12),
    # Double-column (17.5 cm wide, ~6.89 in)
    "double_col":       (6.89, 2.56),
    "double_col_2x2":   (6.89, 5.12),
    "double_col_2x3":   (6.89, 7.68),
    "double_col_sq":    (6.89, 6.89),
    "double_col_hmap":  (6.89, 3.94),
    "wide_waterfall":   (8.0, 5.0),
}

# Per-journal figure size presets (width x height, inches)
# Based on each journal's guide for authors
JOURNAL_PRESETS: Dict[str, Dict[str, Tuple[float, float]]] = {
    "acs": {
        "single_full":      (3.33, 2.50),   # ACS: 1-col = 8.47 cm
        "single_tall":      (3.33, 5.00),
        "double_full":      (6.85, 2.50),   # ACS: 2-col = 17.40 cm
        "double_2x2":       (6.85, 5.00),
        "double_2x3":       (6.85, 7.50),
    },
    "rsc": {
        "single_full":      (3.35, 2.56),   # RSC: 1-col = 8.5 cm
        "single_tall":      (3.35, 5.12),
        "double_full":      (6.89, 2.56),   # RSC: 2-col = 17.5 cm
        "double_2x2":       (6.89, 5.12),
        "double_2x3":       (6.89, 7.68),
    },
    "wiley": {
        "single_full":      (3.54, 2.56),   # Wiley: 1-col = 9.0 cm
        "single_tall":      (3.54, 5.12),
        "double_full":      (7.09, 2.56),   # Wiley: 2-col = 18.0 cm
        "double_2x2":       (7.09, 5.12),
        "double_2x3":       (7.09, 7.68),
    },
    "nature": {
        "single_full":      (3.35, 2.50),   # Nature: 1-col = 8.5 cm
        "single_tall":      (3.35, 5.00),
        "double_full":      (6.89, 2.50),   # Nature: 2-col = 17.5 cm
        "double_2x2":       (6.89, 5.00),
        "double_2x3":       (6.89, 7.50),
    },
}

# Export format recommendations per journal
JOURNAL_EXPORT: Dict[str, List[str]] = {
    "acs":      ["pdf", "tiff"],
    "rsc":      ["pdf", "png"],
    "wiley":    ["pdf", "tiff"],
    "nature":   ["pdf", "png"],
}


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Font Specification
# ═══════════════════════════════════════════════════════════════════════════════

def set_sci_style(font_size: float = 8.0, dpi: int = 150) -> None:
    """Configure matplotlib global rcParams for SCI publication quality.

    All PolyNexus plotting code should call this once at module init,
    or per-figure before any plotting commands.

    Parameters
    ----------
    font_size : float
        Base font size in pt (default 8 for SCI journals).
    dpi : int
        Screen DPI for interactive display (saved figures always 300 DPI).
    """
    mpl.rcParams.update({
        # Font
        "font.family":          "Arial",
        "font.size":            font_size,
        "axes.labelsize":       font_size + 1,
        "axes.labelweight":     "bold",
        "axes.titlesize":       font_size + 1,
        "xtick.labelsize":      font_size,
        "ytick.labelsize":      font_size,
        "legend.fontsize":      font_size,
        # Lines
        "lines.linewidth":      1.2,
        "lines.markersize":     4,
        "axes.linewidth":       0.8,
        # Ticks
        "xtick.major.width":    0.8,
        "ytick.major.width":    0.8,
        "xtick.minor.width":    0.6,
        "ytick.minor.width":    0.6,
        "xtick.major.size":     3.5,
        "ytick.major.size":     3.5,
        "xtick.minor.size":     2.0,
        "ytick.minor.size":     2.0,
        "xtick.direction":      "in",
        "ytick.direction":      "in",
        # Legend
        "legend.frameon":       False,
        "legend.handlelength":  1.5,
        # Output
        "figure.dpi":           dpi,
        "savefig.dpi":          300,
        "savefig.bbox":         "tight",
        "savefig.facecolor":    "white",
        # SVG: keep text as editable <text> elements (not paths)
        "svg.fonttype":         "none",
        # Math
        "mathtext.fontset":     "stix",
    })


def apply_axis_sci_style(ax: mpl.axes.Axes) -> None:
    """Apply SCI axis styling to an existing Axes object.

    Call this after creating any new axes to ensure consistent tick direction,
    spine width, etc.
    """
    ax.tick_params(
        direction="in", top=True, right=True,
        length=3, width=0.8,
    )
    for spine in ax.spines.values():
        spine.set_linewidth(0.8)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Panel Labels — for multi-panel composite figures
# ═══════════════════════════════════════════════════════════════════════════════

def apply_panel_label(
    ax: mpl.axes.Axes,
    label: str,
    x: float = 0.02,
    y: float = 0.98,
    fontsize: float = 10,
    fontweight: str = "bold",
    **kwargs,
) -> None:
    """Place a panel label (a, b, c, ...) in the corner of an axes.

    SCI convention: panel labels appear at top-left, bold, same size as
    axis labels, without any box. The label should *not* be part of the
    figure's data area (no set_title / suptitle).

    Parameters
    ----------
    ax : Axes
        Matplotlib axes to label.
    label : str
        Panel label text, e.g. '(a)' or 'a'.
    x, y : float
        Normalised axes coordinates (default top-left: 0.02, 0.98).
    fontsize : float
        Font size in pt (default 10, same as axis label).
    fontweight : str
        Font weight (default 'bold').
    """
    ax.text(
        x, y, label,
        transform=ax.transAxes,
        fontsize=fontsize,
        fontweight=fontweight,
        va="top", ha="left",
        **kwargs,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Export Formats
# ═══════════════════════════════════════════════════════════════════════════════

def save_figure_sci(
    fig: mpl.figure.Figure,
    filepath: str | Path,
    formats: List[str] | None = None,
    dpi: int = 300,
    close: bool = True,
) -> Dict[str, str]:
    """Save figure in SCI publication formats.

    Parameters
    ----------
    fig : Figure
        Matplotlib figure to save.
    filepath : str or Path
        Base path (without extension). Extensions are appended per format.
    formats : list of str, optional
        Formats to export. Default: ["pdf", "png"]. Recommended for submission:
        ["pdf", "tiff"].
    dpi : int
        Resolution for raster formats (PNG/TIFF). Default 300 for submission,
        use 600 for high-res TIFF.
    close : bool
        If True, close the figure after saving.

    Returns
    -------
    dict : {format: saved_filepath}
    """
    if formats is None:
        formats = ["pdf", "png"]

    base = Path(filepath)
    base.parent.mkdir(parents=True, exist_ok=True)

    saved = {}
    for fmt in formats:
        out_path = base.with_suffix(f".{fmt}")
        kwargs = dict(bbox_inches="tight", facecolor="white", edgecolor="none")
        if fmt in ("png", "tiff", "tif"):
            kwargs["dpi"] = dpi
        if fmt == "svg":
            kwargs["metadata"] = {"Creator": "PolyNexus v1.0"}
        fig.savefig(out_path, **kwargs)
        saved[fmt] = str(out_path)

    if close:
        plt.close(fig)

    return saved


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Composite Figure Builder
# ═══════════════════════════════════════════════════════════════════════════════

def make_composite_figure(
    panels: List[Tuple[mpl.figure.Figure, str, Optional[str]]],
    layout: str = "double_col_2x2",
    panel_labels: bool = True,
    label_start: str = "a",
    share_x: bool = False,
    share_y: bool = False,
    suptitle: Optional[str] = None,
) -> mpl.figure.Figure:
    """Build a composite multi-panel figure from individual figures.

    Each panel figure is embedded into a new master figure arranged
    in a grid. Panel labels (a, b, c, ...) are added automatically.

    Parameters
    ----------
    panels : list of (fig, label_suffix, optional_title)
        Each tuple is (matplotlib Figure, label text like 'Crystallinity',
        or None for no title). The label_suffix is placed after the
        panel letter, e.g. '(a) Crystallinity'.
    layout : str
        Figure size key from FIG_SIZES (default 'double_col_2x2').
    panel_labels : bool
        Whether to add (a), (b), ... labels (default True).
    label_start : str
        Starting letter for labels (default 'a').
    share_x, share_y : bool
        Whether subplots share axes (default False).
    suptitle : str, optional
        Optional overall figure title (use only for SI, not main text).

    Returns
    -------
    Figure
        The new composite figure.
    """
    n = len(panels)
    if n == 0:
        raise ValueError("At least one panel required")

    # Determine grid layout
    if n <= 2:
        nrows, ncols = 1, n
    elif n <= 4:
        nrows, ncols = 2, 2
    elif n <= 6:
        nrows, ncols = 2, 3
    else:
        nrows, ncols = (n + 2) // 3, min(n, 3)

    size = FIG_SIZES.get(layout, FIG_SIZES["double_col_2x2"])
    fig_width = size[0]
    fig_height = size[1]

    new_fig, axes = plt.subplots(
        nrows, ncols,
        figsize=(fig_width, fig_height),
        sharex=share_x, sharey=share_y,
        squeeze=False,
    )

    letters = [chr(ord(label_start) + i) for i in range(n)]

    for idx, (orig_fig, suffix, _) in enumerate(panels):
        row, col = divmod(idx, ncols)
        ax = axes[row][col]

        # Copy the content from the original figure's first axes
        orig_ax = orig_fig.axes[0]
        for line in orig_ax.get_lines():
            ax.plot(line.get_xdata(), line.get_ydata(),
                    color=line.get_color(), linestyle=line.get_linestyle(),
                    linewidth=line.get_linewidth(), marker=line.get_marker(),
                    markersize=line.get_markersize(),
                    label=line.get_label())

        # Copy fills
        for coll in orig_ax.collections:
            try:
                ax.add_collection(coll)
            except Exception:
                logger.warning("静默异常", exc_info=True)

        # Copy axis properties
        ax.set_xlim(orig_ax.get_xlim())
        ax.set_ylim(orig_ax.get_ylim())
        ax.set_xlabel(orig_ax.get_xlabel())
        ax.set_ylabel(orig_ax.get_ylabel())
        ax.set_xscale(orig_ax.get_xscale())
        ax.set_yscale(orig_ax.get_yscale())

        # Copy legend
        leg = orig_ax.get_legend()
        if leg is not None:
            ax.legend(fontsize=leg.get_fontsize(), frameon=False)

        # Apply SCI axis style
        apply_axis_sci_style(ax)

        # Add panel label
        if panel_labels:
            label_text = f"({letters[idx]})"
            if suffix:
                label_text += f" {suffix}"
            apply_panel_label(ax, label_text)

        # Hide unused subplots
        for j in range(idx + 1, nrows * ncols):
            axes[row][j].set_visible(False) if j < ncols else None

    plt.subplots_adjust(
        left=0.1, right=0.95, bottom=0.1, top=0.95,
        wspace=0.3, hspace=0.3,
    )

    if suptitle:
        new_fig.suptitle(suptitle, fontsize=11, fontweight="bold", y=0.98)

    plt.close("all")  # Close originals to free memory
    return new_fig


# ═══════════════════════════════════════════════════════════════════════════════
# 7. LaTeX Axis Labels (shared across all techniques)
# ═══════════════════════════════════════════════════════════════════════════════

AXIS_LABELS: Dict[str, str] = {
    # Common
    "T":            r"Temperature ($^\circ$C)",
    "time":         r"Time $t$ (s)",
    "strain":       r"Strain $\varepsilon$ (\%)",
    "ln_t":         r"$\ln(t)$",

    # DSC
    "HF_Wg":        r"Heat Flow (W/g)",
    "HF_mW":        r"Heat Flow (mW)",
    "Tg":           r"$T_{\mathrm{g}}$ ($^\circ$C)",
    "Tm":           r"$T_{\mathrm{m}}$ ($^\circ$C)",
    "Tc":           r"$T_{\mathrm{c}}$ ($^\circ$C)",
    "Cp":           r"$C_p$ (J/(g$\cdot$K))",
    "Xc_dsc":       r"Crystallinity $\phi_c^{\mathrm{DSC}}$ (\%)",
    "avrami_y":     r"$\ln[-\ln(1-X_c)]$",
    "beta":         r"Heating rate $\beta$ ($^\circ$C/min)",

    # SAXS
    "q":            r"$q$ (nm$^{-1}$)",
    "I_saxs":       r"$I$ (a.u.)",
    "I_abs":        r"$I$ (cm$^{-1}$)",
    "r":            r"$r$ (nm)",
    "gamma":        r"$\gamma(r)$",
    "g1":           r"$g_1(r)$ (a.u.)",
    "L":            r"Long period $L$ (nm)",
    "lc":           r"Crystal thickness $l_{\mathrm{c}}$ (nm)",
    "la":           r"Amorphous thickness $l_{\mathrm{a}}$ (nm)",
    "phi_c_saxs":   r"Crystallinity $\phi_c$",
    "phi_v":        r"Void fraction $\phi_v$",
    "Q_star":       r"Invariant $Q^*$ (a.u.)",
    "f_herman":     r"Herman orientation factor $f$",

    # WAXS
    "two_theta":    r"$2\theta$ ($^\circ$)",
    "d_spacing":    r"$d$-spacing (nm)",
    "I_waxs":       r"Intensity (a.u.)",
    "D_scherrer":   r"Crystallite size $D$ (nm)",
    "phi_c_waxs":   r"Crystallinity $\phi_c^{\mathrm{WAXS}}$ (\%)",
    "epsilon_micro": r"Microstrain $\varepsilon$ (\%)",
    "a_lattice":    r"$a$ (nm)",
    "b_lattice":    r"$b$ (nm)",
    "c_lattice":    r"$c$ (nm)",
    "FWHM":         r"FWHM ($^\circ$)",

    # NMR
    "ppm":          r"Chemical shift $\delta$ (ppm)",
    "I_nmr":        r"Intensity (a.u.)",
    "T1":           r"$T_1$ relaxation time (s)",
    "phi_c_nmr":    r"Crystallinity $\phi_c^{\mathrm{NMR}}$ (\%)",

    # IR
    "wavenumber":   r"Wavenumber (cm$^{-1}$)",
    "absorbance":   r"Absorbance (a.u.)",
    "transmittance": r"Transmittance (\%)",
    "cryst_index":  r"Crystallinity index",
}


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Quality Flag System (cross-technique)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class QualityFlag:
    """Cross-technique quality flag for analysis results."""
    code: int
    label: str
    description: str


# Universal quality flags
QUALITY_FLAGS: Dict[int, QualityFlag] = {
    0:  QualityFlag(0,  "OK",           "Normal"),
    1:  QualityFlag(1,  "LOW_SNR",      "Low signal-to-noise ratio"),
    2:  QualityFlag(2,  "PEAK_OVERLAP", "Severe peak overlap, manual review needed"),
    3:  QualityFlag(3,  "UNSTABLE_BL",  "Unstable baseline"),
    4:  QualityFlag(4,  "UNCALIBRATED", "Calibration not applied"),
    5:  QualityFlag(5,  "CROSS_CHECK_FAIL", "Cross-technique validation deviation too large"),
    99: QualityFlag(99, "FAILED",       "Computation failed, manual processing required"),
}

# Technique-specific quality flags (merged with universal)
TECHNIQUE_QUALITY_FLAGS: Dict[str, Dict[int, QualityFlag]] = {
    "dsc": {
        3: QualityFlag(3, "MASS_OUTLIER",   "Sample mass outlier (<0.5 mg or >15 mg)"),
        6: QualityFlag(6, "THERMAL_LAG",    "Thermal lag artifact (heating rate too high)"),
    },
    "waxs": {
        3: QualityFlag(3, "AMORPH_UNCERTAIN", "Amorphous separation uncertainty high"),
    },
    "saxs": {},
    "nmr":  {},
    "ir":   {},
}


def get_quality_label(code: int, technique: str = "") -> str:
    """Return human-readable quality flag label.

    Parameters
    ----------
    code : int
        Quality flag code.
    technique : str
        Technique name for technique-specific flags.

    Returns
    -------
    str
        Human-readable label.
    """
    # Check technique-specific first
    if technique and technique in TECHNIQUE_QUALITY_FLAGS:
        tf = TECHNIQUE_QUALITY_FLAGS[technique]
        if code in tf:
            return tf[code].label
    # Fall back to universal
    qf = QUALITY_FLAGS.get(code)
    return qf.label if qf else f"UNKNOWN_{code}"


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Output Directory Structure (cross-technique)
# ═══════════════════════════════════════════════════════════════════════════════

OUTPUT_DIR_TEMPLATE: Dict[str, str] = {
    "raw_data":     "raw_{technique}/",     # Preprocessed 1D curves
    "parameters":   "parameters/",          # Extracted parameters CSV
    "figures_main": "figures/main/",        # Vector + raster for manuscript
    "figures_si":   "figures/SI/",          # Supporting Information
    "report":       "report/",              # Auto-generated HTML report
}


def create_output_structure(
    output_root: str | Path,
    technique: str,
) -> Dict[str, Path]:
    """Create SCI-standard output directory structure.

    Parameters
    ----------
    output_root : str or Path
        Root output directory.
    technique : str
        Technique name (e.g. "saxs", "dsc").

    Returns
    -------
    dict : {dir_key: Path}
    """
    root = Path(output_root)
    dirs = {}
    for key, template in OUTPUT_DIR_TEMPLATE.items():
        name = template.replace("{technique}", technique)
        path = root / name
        path.mkdir(parents=True, exist_ok=True)
        dirs[key] = path
    return dirs
