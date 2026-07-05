"""IR output module: SCI-quality figure generation."""

import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from typing import Dict, List, Optional, Tuple, Any

from .core import IRResult
from .config import IRConfig
from ..plot_edits import savefig_with_edits
from ...plotting.sci_style import (
    set_sci_style as _global_set_sci_style,
    apply_axis_sci_style,
    WONG_COLORS, ANNOTATION_COLORS,
    FIG_SIZES, AXIS_LABELS,
    save_figure_sci,
)


SCI_COLORS = {
    'blue':   WONG_COLORS[5], 'red':    WONG_COLORS[6], 'green':  WONG_COLORS[3],
    'orange': WONG_COLORS[1], 'purple': WONG_COLORS[7], 'cyan':   '#00A896',
    'grey':   '#666666', 'dark': '#222222',
}

SCI_PALETTE = [WONG_COLORS[i] for i in (5, 6, 3, 1, 7)]


def set_sci_style(fig, ax, xlabel='', ylabel='', title='', fontsize=10):
    _global_set_sci_style(font_size=fontsize - 1)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=fontsize)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=fontsize)
    if title:
        ax.set_title(title, fontsize=fontsize + 1, fontweight='bold')
    ax.tick_params(labelsize=fontsize - 1, direction='in', top=True, right=True)
    for spine in ax.spines.values():
        spine.set_linewidth(0.8); spine.set_color('#333333')
    ax.grid(True, alpha=0.2, linestyle='--', linewidth=0.5)


def _make_output_dirs(d): 
    fd, dd = os.path.join(d, 'figures'), os.path.join(d, 'data')
    os.makedirs(fd, exist_ok=True); os.makedirs(dd, exist_ok=True)
    return fd, dd


def _save(fig, name, fd, fmt='svg', dpi=300):
    p = os.path.join(fd, f'{name}.{fmt}')
    savefig_with_edits(fig, p, dpi=dpi, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
    plt.close(fig); return p


def _safe_label(label: str) -> str:
    safe = ''.join(ch if ch.isalnum() or ch in ('-', '_') else '_' for ch in str(label))
    return safe.strip('_') or 'spectrum'


def _top_annotation_peaks(peaks, limit=16):
    ranked = sorted(peaks, key=lambda p: p.get('prominence', p.get('height', 0.0)), reverse=True)
    keep = {id(p) for p in ranked[:limit]}
    return [p for p in peaks if id(p) in keep]


# ---------------------------------------------------------------------------
#  Fig-IR1: Full IR spectrum with peak annotations
# ---------------------------------------------------------------------------

def fig_ir1_spectrum(result: IRResult, output_dir: str,
                     config: Optional[IRConfig] = None) -> str:
    """Fig-IR1: Full IR spectrum with detected peaks labelled."""
    fmt = config.fig_format if config else 'svg'
    dpi = config.fig_dpi if config else 300
    fig_dir, _ = _make_output_dirs(output_dir)

    if len(result.wavenumber) == 0:
        return ""

    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    wn = result.wavenumber
    A = result.absorbance

    ax.plot(wn, A, color=SCI_COLORS['dark'], linewidth=0.8)

    # Annotate peaks
    for i, pk in enumerate(_top_annotation_peaks(result.peaks)):
        color = SCI_PALETTE[i % len(SCI_PALETTE)]
        mu = pk['wavenumber']
        amp = pk['height']
        ax.axvline(mu, color=color, linestyle=':', linewidth=0.5, alpha=0.5)

        label = f"{mu:.0f}"
        assignment = pk.get('assignment', '')
        if assignment and assignment != 'unknown':
            label += f"\n{assignment[:15]}"
        ax.annotate(label, xy=(mu, amp), xytext=(0, 5),
                    textcoords='offset points', fontsize=5, color=color,
                    ha='center', rotation=90)

    # IR convention: high wavenumber on left, decreasing
    ax.invert_xaxis()
    set_sci_style(fig, ax, xlabel='Wavenumber (cm^-1)',
                  ylabel='Absorbance (a.u.)',
                  title=f'IR Spectrum - {result.label}')

    return _save(fig, f'Fig-IR1_{_safe_label(result.label)}_spectrum', fig_dir, fmt, dpi)


# ---------------------------------------------------------------------------
#  Fig-IR2: Peak fitting detail
# ---------------------------------------------------------------------------

def fig_ir2_peak_fit(result: IRResult, output_dir: str,
                     wavenumber_range: Optional[Tuple[float, float]] = None,
                     config: Optional[IRConfig] = None) -> str:
    """Fig-IR2: Magnified region with peak fitting components."""
    fmt = config.fig_format if config else 'svg'
    dpi = config.fig_dpi if config else 300
    fig_dir, _ = _make_output_dirs(output_dir)

    if len(result.absorbance_fit) == 0 or not result.peaks:
        return ""

    fig, ax = plt.subplots(figsize=(5.5, 3.8))
    wn = result.wavenumber
    A = result.absorbance
    A_fit = result.absorbance_fit

    # Zoom if range specified
    if wavenumber_range:
        mask = (wn >= wavenumber_range[0]) & (wn <= wavenumber_range[1])
    else:
        # Auto-zoom around peaks
        peak_wns = [p['wavenumber'] for p in result.peaks]
        mask = np.ones(len(wn), dtype=bool)
        if peak_wns:
            margin = 80
            mask = (wn >= min(peak_wns) - margin) & (wn <= max(peak_wns) + margin)

    wn_z = wn[mask]
    A_z = A[mask]
    A_fit_z = A_fit[mask]

    ax.plot(wn_z, A_z, color=SCI_COLORS['dark'], linewidth=1.0, label='Data')
    ax.plot(wn_z, A_fit_z, color=SCI_COLORS['red'], linewidth=1.2,
            linestyle='--', label=f'Fit ($R^2$={result.r_squared:.3f})')

    for pk in _top_annotation_peaks(result.peaks):
        mu = pk['wavenumber']
        assignment = pk.get('assignment', '')
        ax.axvline(mu, color=SCI_COLORS['blue'], linestyle=':', linewidth=0.5, alpha=0.4)
        if assignment and assignment != 'unknown':
            ax.annotate(assignment, xy=(mu, np.interp(mu, wn, A)),
                        xytext=(0, 8), textcoords='offset points',
                        fontsize=6, ha='center', rotation=90, color=SCI_COLORS['blue'])

    ax.invert_xaxis()
    ax.legend(fontsize=8, framealpha=0.9)
    set_sci_style(fig, ax, xlabel='Wavenumber (cm^-1)',
                  ylabel='Absorbance (a.u.)',
                  title=f'Peak Fitting - {result.label}')

    return _save(fig, f'Fig-IR2_{_safe_label(result.label)}_peak_fit', fig_dir, fmt, dpi)


# ---------------------------------------------------------------------------
#  Fig-IR3: Experimental vs Computed comparison
# ---------------------------------------------------------------------------

def fig_ir3_comparison(result: IRResult, output_dir: str,
                       config: Optional[IRConfig] = None) -> str:
    """Fig-IR3: Experimental vs computed IR spectrum overlay."""
    fmt = config.fig_format if config else 'svg'
    dpi = config.fig_dpi if config else 300
    fig_dir, _ = _make_output_dirs(output_dir)

    if result.simulated_spectrum is None or not result.simulated_spectrum.has_data:
        return ""

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7.0, 5.0),
                                     gridspec_kw={'height_ratios': [2, 1]})

    wn_exp = result.wavenumber
    A_exp = result.absorbance

    # Top: Overlay
    ax1.plot(wn_exp, A_exp, color=SCI_COLORS['dark'], linewidth=1.0,
             label='Experimental')
    ax1.plot(result.simulated_spectrum.wavenumber,
             result.simulated_spectrum.absorbance,
             color=SCI_COLORS['red'], linewidth=1.0, alpha=0.7,
             label='Computed')

    # Stick spectrum for computed modes
    if result.computed_modes:
        for mode in result.computed_modes:
            if mode.ir_intensity_km_mol > 2.0:
                ax1.axvline(mode.frequency_cm1, ymin=0.9, ymax=1.0,
                           color=SCI_COLORS['blue'], linewidth=0.5, alpha=0.6)

    ax1.invert_xaxis()
    ax1.legend(fontsize=8, framealpha=0.9)
    set_sci_style(fig, ax1, ylabel='Absorbance (a.u.)')

    # Bottom: Delta bar chart
    if result.matches:
        matches_with_exp = [m for m in result.matches if not np.isnan(m.get('delta_cm1', np.nan))]
        if matches_with_exp:
            labels = [f"{m['exp_cm1']:.0f}" for m in matches_with_exp]
            deltas = [m['delta_cm1'] for m in matches_with_exp]
            colors = [SCI_COLORS['green'] if d < 10 else SCI_COLORS['orange']
                      for d in deltas]
            ax2.bar(range(len(deltas)), deltas, color=colors, edgecolor='white', linewidth=0.5)
            ax2.axhline(10, color=SCI_COLORS['red'], linestyle='--', linewidth=0.8,
                        label='+/-10 cm^-1')
            ax2.set_xticks(range(len(labels)))
            ax2.set_xticklabels(labels, fontsize=7, rotation=45)
            ax2.legend(fontsize=7)

    set_sci_style(fig, ax2, xlabel='Experimental peak (cm^-1)',
                  ylabel='|Delta nu| (cm^-1)',
                  title='Exp-Calc Frequency Differences')

    fig.suptitle(f'Exp vs Computed - {result.label}', fontsize=11,
                 fontweight='bold', y=1.01)

    return _save(fig, f'Fig-IR3_{_safe_label(result.label)}_comparison', fig_dir, fmt, dpi)


# ---------------------------------------------------------------------------
#  Fig-IR4: Crystallinity band ratio
# ---------------------------------------------------------------------------

def fig_ir4_crystallinity(spectra_results: List[IRResult], output_dir: str,
                          config: Optional[IRConfig] = None) -> str:
    """Fig-IR4: Crystallinity index comparison across samples."""
    fmt = config.fig_format if config else 'svg'
    dpi = config.fig_dpi if config else 300
    fig_dir, _ = _make_output_dirs(output_dir)

    labels = [r.label for r in spectra_results]
    xc = [r.Xc_pct for r in spectra_results]

    if all(np.isnan(v) for v in xc):
        return ""

    fig, ax = plt.subplots(figsize=(5.5, 3.5))
    colors = [SCI_PALETTE[i % len(SCI_PALETTE)] for i in range(len(labels))]
    bars = ax.bar(range(len(labels)), xc, color=colors, edgecolor='white', linewidth=0.5)

    for bar, val in zip(bars, xc):
        if not np.isnan(val):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                    f'{val:.1f}', ha='center', va='bottom', fontsize=8, fontweight='bold')

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha='right', fontsize=8)
    ax.set_ylabel('IR band index')

    set_sci_style(fig, ax)
    return _save(fig, 'Fig-IR4_crystallinity', fig_dir, fmt, dpi)


# ---------------------------------------------------------------------------
#  Export
# ---------------------------------------------------------------------------

def export_parameters_csv(results: List[IRResult], output_dir: str) -> str:
    import pandas as pd
    _, data_dir = _make_output_dirs(output_dir)
    rows = [r.parameters for r in results]
    df = pd.DataFrame(rows)
    path = os.path.join(data_dir, 'ir_parameters.csv')
    df.to_csv(path, index=False)

    peak_rows = []
    band_rows = []
    for r in results:
        for pk in r.peaks:
            peak_rows.append({
                'sample': r.label,
                'polymer': r.polymer_name,
                'wavenumber_cm1': pk.get('wavenumber', np.nan),
                'height': pk.get('height', np.nan),
                'prominence': pk.get('prominence', np.nan),
                'fwhm_cm1': pk.get('fwhm_cm1', np.nan),
                'area': pk.get('area', np.nan),
                'assignment': pk.get('assignment', ''),
                'ref_wavenumber_cm1': pk.get('ref_wavenumber', np.nan),
                'delta_cm1': pk.get('delta_cm1', np.nan),
                'crystalline_band': pk.get('crystalline', False),
            })
        for key, val in r.band_indices.items():
            band_rows.append({
                'sample': r.label,
                'polymer': r.polymer_name,
                'index': key,
                'value': val,
                'method': r.Xc_method if key == r.Xc_band else '',
            })
    if peak_rows:
        pd.DataFrame(peak_rows).to_csv(os.path.join(data_dir, 'ir_peaks.csv'), index=False)
    if band_rows:
        pd.DataFrame(band_rows).to_csv(os.path.join(data_dir, 'ir_band_indices.csv'), index=False)
    return path


def generate_all_figures(results: List[IRResult], output_dir: str,
                         config: Optional[IRConfig] = None) -> Dict[str, str]:
    figures = {}
    for result in results:
        prefix = result.label.replace(' ', '_').replace('/', '_')
        p = fig_ir1_spectrum(result, output_dir, config)
        if p: figures[f'{prefix}_spectrum'] = p
        p = fig_ir2_peak_fit(result, output_dir, config=config)
        if p: figures[f'{prefix}_peak_fit'] = p
        p = fig_ir3_comparison(result, output_dir, config)
        if p: figures[f'{prefix}_comparison'] = p

    if len(results) > 1:
        p = fig_ir4_crystallinity(results, output_dir, config)
        if p: figures['crystallinity'] = p

    export_parameters_csv(results, output_dir)
    return figures
