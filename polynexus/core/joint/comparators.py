"""Comparison computation functions for cross-technique analysis."""

import numpy as np
import pandas as pd
from scipy import stats


def compare_crystallinity_three_way(by_technique: dict) -> pd.DataFrame:
    """Compute crystallinity from DSC, WAXS, SAXS and compare."""
    rows = []
    max_len = max(
        (len(v) for v in by_technique.values()),
        default=0
    )
    if max_len == 0:
        return None

    for i in range(max_len):
        row = {}
        for tech in ['dsc', 'waxs', 'saxs']:
            items = by_technique.get(tech, [])
            if i < len(items) and items[i]:
                row[f'{tech}_Xc'] = items[i].get('Xc_pct', np.nan)
            else:
                row[f'{tech}_Xc'] = np.nan
        rows.append(row)

    df = pd.DataFrame(rows)
    # Compute pairwise deviations
    for t1, t2 in [('dsc','waxs'), ('dsc','saxs'), ('waxs','saxs')]:
        col = f'{t1}_{t2}_diff'
        if f'{t1}_Xc' in df and f'{t2}_Xc' in df:
            df[col] = df[f'{t1}_Xc'] - df[f'{t2}_Xc']
    return df


def compute_tm_vs_long_period(dsc_summaries: list,
                               saxs_summaries: list) -> pd.DataFrame:
    """Extract Tm (DSC) vs L (SAXS) for coupling analysis."""
    rows = []
    for d, s in zip(dsc_summaries, saxs_summaries):
        l_nm = s.get('L_nm', np.nan) if s else np.nan
        tm = d.get('Tm_C') or d.get('Tm_peak_C', np.nan) if d else np.nan
        if not (np.isnan(l_nm) and np.isnan(tm)):
            rows.append({'L_nm': l_nm, 'Tm_C': tm})
    return pd.DataFrame(rows) if rows else None


def compute_xc_vs_crystallite_size(dsc_summaries: list,
                                    waxs_summaries: list) -> pd.DataFrame:
    """Extract Xc (DSC) vs D (WAXS) for correlation analysis."""
    rows = []
    for d, w in zip(dsc_summaries, waxs_summaries):
        xc = d.get('Xc_pct', np.nan) if d else np.nan
        d_val = w.get('D_Scherrer_nm', np.nan) if w else np.nan
        if not (np.isnan(xc) and np.isnan(d_val)):
            rows.append({'Xc_pct': xc, 'D_Scherrer_nm': d_val})
    return pd.DataFrame(rows) if rows else None


def compute_ir_vs_dsc_crystallinity(ir_summaries: list,
                                     dsc_summaries: list) -> pd.DataFrame:
    """Compare IR crystallinity index vs DSC Xc."""
    rows = []
    for ir_s, dsc_s in zip(ir_summaries, dsc_summaries):
        ir_ci = ir_s.get('crystallinity_index', np.nan) if ir_s else np.nan
        dsc_xc = dsc_s.get('Xc_pct', np.nan) if dsc_s else np.nan
        if not (np.isnan(ir_ci) and np.isnan(dsc_xc)):
            rows.append({'IR_CI': ir_ci, 'DSC_Xc': dsc_xc})
    return pd.DataFrame(rows) if rows else None


def compute_correlation_matrix(df: pd.DataFrame, parameters: list[str],
                                method: str = "pearson") -> pd.DataFrame:
    """Compute n x n correlation matrix with p-values and sample sizes."""
    n = len(parameters)
    available = [p for p in parameters if p in df.columns]
    if len(available) < 2:
        return pd.DataFrame()

    mat = pd.DataFrame(index=available, columns=available, dtype=float)
    pvals = pd.DataFrame(index=available, columns=available, dtype=float)
    counts = pd.DataFrame(index=available, columns=available, dtype=int)

    for pi in available:
        for pj in available:
            subset = df[[pi, pj]].dropna()
            n_val = len(subset)
            counts.loc[pi, pj] = n_val
            if n_val >= 3:
                if method == "pearson":
                    r, p = stats.pearsonr(subset[pi], subset[pj])
                else:
                    r, p = stats.spearmanr(subset[pi], subset[pj])
                mat.loc[pi, pj] = r
                pvals.loc[pi, pj] = p
            else:
                mat.loc[pi, pj] = np.nan
                pvals.loc[pi, pj] = np.nan

    # Return as structured dict
    return {
        'correlation': mat,
        'p_values': pvals,
        'sample_sizes': counts,
        'parameters': available,
        'method': method,
    }
