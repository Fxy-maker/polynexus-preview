"""Cross-technique joint analysis: SAXS + WAXS + DSC.

Provides unified crystallinity comparison, multi-scale correlation,
and combined reporting across all polymer characterisation techniques.
"""

import os
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from .plot_edits import savefig_with_edits


C = {'blue':'#2166AC','red':'#B2182B','green':'#1B7837','orange':'#E69F00',
     'purple':'#762A83','cyan':'#00A896','grey':'#666666','dark':'#222222'}
PAL = [C['blue'],C['red'],C['green'],C['orange'],C['purple'],C['cyan']]

# ---------------------------------------------------------------------------
#  Joint result container
# ---------------------------------------------------------------------------

@dataclass
class JointResult:
    """Aggregated results from multiple techniques."""
    label: str = ""

    # Crystallinity from each technique
    Xc_dsc_pct: float = np.nan
    Xc_waxs_pct: float = np.nan
    Xc_saxs_pct: float = np.nan   # from lc/L ratio

    # DSC parameters
    Tg_C: float = np.nan
    Tm_C: float = np.nan
    DHm_Jg: float = np.nan

    # SAXS parameters
    long_period_nm: float = np.nan
    lc_nm: float = np.nan
    la_nm: float = np.nan

    # WAXS parameters
    D_Scherrer_nm: float = np.nan
    n_waxs_peaks: int = 0

    # Correlation
    L_vs_D: float = np.nan       # long period / crystallite size
    Xc_consensus: float = np.nan  # mean crystallinity

    @property
    def parameters(self) -> Dict[str, Any]:
        p = {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        return {k: v for k, v in p.items()
                if not (isinstance(v, float) and np.isnan(v))}


# ---------------------------------------------------------------------------
#  Cross-technique crystallinity comparison
# ---------------------------------------------------------------------------

def compare_crystallinity(dsc_results=None, waxs_results=None, saxs_results=None):
    """Compare crystallinity from all available techniques.

    Parameters
    ----------
    dsc_results : list of DSCResult or similar with Xc_pct
    waxs_results : list of WAXSResult
    saxs_results : list of SAXSResult
    """
    joint = []
    n = max(len(dsc_results or []), len(waxs_results or []), len(saxs_results or []))

    for i in range(n):
        jr = JointResult(label=f"Sample_{i+1}")

        if dsc_results and i < len(dsc_results):
            r = dsc_results[i]
            jr.Xc_dsc_pct = getattr(r, 'Xc_pct', np.nan)
            jr.Tg_C = getattr(r, 'Tg_C', np.nan)
            jr.Tm_C = getattr(r, 'Tm_peak_C', getattr(r, 'Tm_C', np.nan))
            jr.DHm_Jg = getattr(r, 'DHm_Jg', np.nan)

        if waxs_results and i < len(waxs_results):
            r = waxs_results[i]
            jr.Xc_waxs_pct = getattr(r, 'Xc_pct', np.nan)
            jr.D_Scherrer_nm = getattr(r, 'D_Scherrer_nm', np.nan)
            jr.n_waxs_peaks = getattr(r, 'n_peaks', 0)

        if saxs_results and i < len(saxs_results):
            r = saxs_results[i]
            params = getattr(r, 'parameters', {})
            jr.long_period_nm = params.get('L_nm', np.nan)
            jr.lc_nm = params.get('lc_nm', np.nan)
            jr.la_nm = params.get('la_nm', np.nan)
            # Crystallinity from SAXS: lc / L
            if not np.isnan(jr.lc_nm) and not np.isnan(jr.long_period_nm) and jr.long_period_nm > 0:
                jr.Xc_saxs_pct = jr.lc_nm / jr.long_period_nm * 100.0

        # Correlation: long period vs crystallite size
        if not np.isnan(jr.long_period_nm) and not np.isnan(jr.D_Scherrer_nm) and jr.D_Scherrer_nm > 0:
            jr.L_vs_D = jr.long_period_nm / jr.D_Scherrer_nm

        # Consensus crystallinity
        vals = [v for v in [jr.Xc_dsc_pct, jr.Xc_waxs_pct, jr.Xc_saxs_pct]
                if not np.isnan(v)]
        if vals:
            jr.Xc_consensus = float(np.mean(vals))

        joint.append(jr)

    return joint


# ---------------------------------------------------------------------------
#  Joint figures
# ---------------------------------------------------------------------------

def _set_style(fig, ax, xl='', yl='', title='', fs=10):
    ax.set_xlabel(xl,fontsize=fs); ax.set_ylabel(yl,fontsize=fs)
    if title: ax.set_title(title,fontsize=fs+1,fontweight='bold')
    ax.tick_params(labelsize=fs-1,direction='in',top=True,right=True)
    for s in ax.spines.values(): s.set_linewidth(0.8); s.set_color('#333')
    ax.grid(True,alpha=0.2,linestyle='--',linewidth=0.5)

def _save(fig, name, fd, fmt='svg', dpi=300):
    p = os.path.join(fd, f'{name}.{fmt}')
    savefig_with_edits(fig, p, dpi=dpi, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
    plt.close(fig); return p


def fig_joint_crystallinity(joint_results, output_dir):
    """Bar chart comparing Xc from DSC / WAXS / SAXS."""
    fd = os.path.join(output_dir, 'figures')
    os.makedirs(fd, exist_ok=True)

    if not joint_results:
        return ""

    labels = [r.label for r in joint_results]
    n = len(labels)
    x = np.arange(n)
    w = 0.25

    fig, ax = plt.subplots(figsize=(6 + n * 0.5, 4))

    dsc_vals = [r.Xc_dsc_pct for r in joint_results]
    waxs_vals = [r.Xc_waxs_pct for r in joint_results]
    saxs_vals = [r.Xc_saxs_pct for r in joint_results]

    ax.bar(x - w, dsc_vals, w, color=C['red'], edgecolor='white', linewidth=0.5, label='DSC')
    ax.bar(x, waxs_vals, w, color=C['blue'], edgecolor='white', linewidth=0.5, label='WAXS')
    ax.bar(x + w, saxs_vals, w, color=C['green'], edgecolor='white', linewidth=0.5, label='SAXS')

    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9)
    ax.legend(fontsize=9, framealpha=0.9)
    _set_style(fig, ax, yl='Crystallinity Xc (%)', title='Cross-Technique Crystallinity Comparison')

    return _save(fig, 'Fig-Joint_crystallinity', fd)


def fig_joint_multiscale(joint_results, output_dir):
    """Scatter plot: SAXS long period vs WAXS crystallite size."""
    fd = os.path.join(output_dir, 'figures')
    os.makedirs(fd, exist_ok=True)

    L_vals = [r.long_period_nm for r in joint_results if not np.isnan(r.long_period_nm) and not np.isnan(r.D_Scherrer_nm)]
    D_vals = [r.D_Scherrer_nm for r in joint_results if not np.isnan(r.long_period_nm) and not np.isnan(r.D_Scherrer_nm)]

    if len(L_vals) < 2:
        return ""

    fig, ax = plt.subplots(figsize=(5, 4))
    labels = [r.label for r in joint_results if not np.isnan(r.long_period_nm) and not np.isnan(r.D_Scherrer_nm)]
    for i, (L, D) in enumerate(zip(L_vals, D_vals)):
        ax.scatter(L, D, c=PAL[i % len(PAL)], s=60, edgecolors='white', linewidth=0.8, zorder=5)
        ax.annotate(labels[i], (L, D), textcoords='offset points', xytext=(5, 5), fontsize=7)

    ax.set_xlabel('SAXS Long Period L (nm)', fontsize=10)
    ax.set_ylabel('WAXS Crystallite Size D (nm)', fontsize=10)
    _set_style(fig, ax, title='SAXS-WAXS Multi-Scale Correlation')

    return _save(fig, 'Fig-Joint_multiscale', fd)


def fig_joint_phase_diagram(dsc_results=None, saxs_results=None, output_dir=""):
    """Temperature-phase diagram: Tm from DSC vs L from SAXS."""
    fd = os.path.join(output_dir, 'figures')
    os.makedirs(fd, exist_ok=True)

    Tm_vals, L_vals, labels = [], [], []
    if dsc_results and saxs_results:
        for i, (d, s) in enumerate(zip(dsc_results, saxs_results)):
            tm = getattr(d, 'Tm_peak_C', getattr(d, 'Tm_C', np.nan))
            params = getattr(s, 'parameters', {})
            L = params.get('L_nm', np.nan)
            if not np.isnan(tm) and not np.isnan(L):
                Tm_vals.append(tm); L_vals.append(L)
                labels.append(getattr(d, 'label', f'S{i+1}'))

    if len(Tm_vals) < 2:
        return ""

    fig, ax = plt.subplots(figsize=(5, 4))
    for i, (tm, L) in enumerate(zip(Tm_vals, L_vals)):
        ax.scatter(tm, L, c=PAL[i % len(PAL)], s=60, edgecolors='white', linewidth=0.8, zorder=5)
        ax.annotate(labels[i], (tm, L), textcoords='offset points', xytext=(5, 5), fontsize=7)

    _set_style(fig, ax, xl='DSC Tm (°C)', yl='SAXS Long Period L (nm)',
               title='Structure-Thermodynamics Correlation')
    return _save(fig, 'Fig-Joint_phase_diagram', fd)


# ---------------------------------------------------------------------------
#  Export
# ---------------------------------------------------------------------------

def export_joint_csv(joint_results, output_dir):
    import pandas as pd
    dd = os.path.join(output_dir, 'data')
    os.makedirs(dd, exist_ok=True)
    rows = [r.parameters for r in joint_results]
    df = pd.DataFrame(rows)
    p = os.path.join(dd, 'joint_parameters.csv')
    df.to_csv(p, index=False)
    return p


def generate_joint_figures(joint_results, output_dir,
                           dsc_results=None, saxs_results=None):
    """Generate all joint analysis figures."""
    figs = {}
    p = fig_joint_crystallinity(joint_results, output_dir)
    if p: figs['crystallinity'] = p
    p = fig_joint_multiscale(joint_results, output_dir)
    if p: figs['multiscale'] = p
    p = fig_joint_phase_diagram(dsc_results, saxs_results, output_dir)
    if p: figs['phase_diagram'] = p
    export_joint_csv(joint_results, output_dir)
    return figs
