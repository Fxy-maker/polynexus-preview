"""WAXS multi-scale correlation module (W6).

Correlates WAXS crystallite size with SAXS long period to provide
a complete picture of the hierarchical structure.
"""

import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from typing import Dict, List, Optional, Tuple
from ..plot_edits import savefig_with_edits


C = {'blue':'#2166AC','red':'#B2182B','green':'#1B7837','orange':'#E69F00',
     'purple':'#762A83','cyan':'#00A896','grey':'#666666','dark':'#222222'}


def multiscale_correlation(waxs_results, saxs_results):
    """Compute multi-scale correlation between SAXS and WAXS.

    Returns list of {label, L_nm, D_nm, lc_nm, la_nm, L_over_D, Xc_saxs, Xc_waxs}
    """
    correlations = []
    n = max(len(waxs_results or []), len(saxs_results or []))

    for i in range(n):
        row = {'label': f'Sample_{i+1}', 'L_nm': np.nan, 'D_nm': np.nan,
               'lc_nm': np.nan, 'la_nm': np.nan, 'L_over_D': np.nan,
               'Xc_saxs_pct': np.nan, 'Xc_waxs_pct': np.nan}

        if saxs_results and i < len(saxs_results):
            sr = saxs_results[i]
            params = getattr(sr, 'parameters', {})
            row['L_nm'] = params.get('L_nm', np.nan)
            row['lc_nm'] = params.get('lc_nm', np.nan)
            row['la_nm'] = params.get('la_nm', np.nan)
            if not np.isnan(row['lc_nm']) and not np.isnan(row['L_nm']) and row['L_nm'] > 0:
                row['Xc_saxs_pct'] = row['lc_nm'] / row['L_nm'] * 100.0
            row['label'] = getattr(sr, 'label', row['label'])

        if waxs_results and i < len(waxs_results):
            wr = waxs_results[i]
            row['D_nm'] = getattr(wr, 'D_Scherrer_nm', np.nan)
            row['Xc_waxs_pct'] = getattr(wr, 'Xc_pct', np.nan)
            row['label'] = getattr(wr, 'label', row['label'])

        if not np.isnan(row['L_nm']) and not np.isnan(row['D_nm']) and row['D_nm'] > 0:
            row['L_over_D'] = row['L_nm'] / row['D_nm']

        correlations.append(row)

    return correlations


def fig_multiscale(correlations, output_dir):
    """Generate multi-scale correlation figure."""
    import os
    fd = os.path.join(output_dir, 'figures')
    os.makedirs(fd, exist_ok=True)

    valid = [c for c in correlations
             if not np.isnan(c['L_nm']) and not np.isnan(c['D_nm'])]
    if len(valid) < 2:
        return ""

    L_vals = [c['L_nm'] for c in valid]
    D_vals = [c['D_nm'] for c in valid]
    labels = [c['label'] for c in valid]

    fig, ax = plt.subplots(figsize=(5, 4))
    PAL = [C['blue'],C['red'],C['green'],C['orange'],C['purple'],C['cyan']]

    for i, (L, D) in enumerate(zip(L_vals, D_vals)):
        ax.scatter(L, D, c=PAL[i % len(PAL)], s=60, edgecolors='white',
                   linewidth=0.8, zorder=5)
        ax.annotate(labels[i], (L, D), textcoords='offset points',
                    xytext=(5, 5), fontsize=7)

    ax.set_xlabel('SAXS Long Period L (nm)', fontsize=10)
    ax.set_ylabel('WAXS Crystallite Size D (nm)', fontsize=10)
    ax.set_title('SAXS-WAXS Multi-Scale Correlation', fontsize=11, fontweight='bold')
    ax.tick_params(labelsize=9, direction='in', top=True, right=True)
    ax.grid(True, alpha=0.2, linestyle='--', linewidth=0.5)

    path = os.path.join(fd, 'Fig-WAXS_multiscale.svg')
    savefig_with_edits(fig, path, dpi=300, bbox_inches='tight',
                       facecolor='white')
    plt.close(fig)
    return path
