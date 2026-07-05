"""Joint analysis plot generation functions."""

from io import BytesIO

import matplotlib

matplotlib.use("Agg")

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _fig_to_bytes(fig) -> BytesIO:
    buf = BytesIO()
    fig.savefig(
        buf,
        format="png",
        dpi=150,
        bbox_inches="tight",
        facecolor=fig.get_facecolor(),
    )
    plt.close(fig)
    buf.seek(0)
    return buf


def plot_crystallinity_comparison(df: pd.DataFrame) -> BytesIO:
    """Three-way crystallinity bar chart with deviation analysis."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    cols = [c for c in ["dsc_Xc", "waxs_Xc", "saxs_Xc"] if c in df.columns]
    x = np.arange(len(df))
    width = 0.25
    colors = ["#ff7f0e", "#2ca02c", "#1f77b4"]
    for i, col in enumerate(cols):
        ax1.bar(x + i * width, df[col], width, label=col, color=colors[i % len(colors)])
    ax1.set_xticks(x + width if cols else x)
    ax1.set_xticklabels([f"#{j+1}" for j in range(len(df))])
    ax1.set_ylabel("Crystallinity (%)")
    ax1.legend()
    ax1.set_title("Crystallinity by Technique")

    diff_cols = [c for c in df.columns if "_diff" in c]
    if diff_cols:
        for i, dc in enumerate(diff_cols):
            ax2.scatter([i + 1] * len(df), df[dc], label=dc)
        ax2.axhline(0, color="gray", linestyle="--")
        ax2.set_ylabel("Difference (%)")
        ax2.set_title("Pairwise Deviations")
        ax2.legend()
    else:
        ax2.axis("off")

    plt.tight_layout()
    return _fig_to_bytes(fig)


def plot_tm_vs_long_period(df: pd.DataFrame) -> BytesIO | None:
    """Tm (DSC) vs L (SAXS) scatter."""
    clean = df[["Tm_C", "L_nm"]].dropna() if {"Tm_C", "L_nm"}.issubset(df.columns) else pd.DataFrame()
    if clean.empty:
        return None

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(clean["Tm_C"], clean["L_nm"], color="#d62728", s=60, edgecolors="white")
    ax.set_xlabel("Melting Temperature Tm (°C)")
    ax.set_ylabel("Long Period L (nm)")
    if len(clean) >= 3:
        z = np.polyfit(clean["Tm_C"], clean["L_nm"], 1)
        x_fit = np.linspace(clean["Tm_C"].min(), clean["Tm_C"].max(), 50)
        ax.plot(x_fit, np.polyval(z, x_fit), "--", color="gray", alpha=0.6)
    plt.tight_layout()
    return _fig_to_bytes(fig)


def plot_xc_vs_crystallite_size(df: pd.DataFrame) -> BytesIO | None:
    """Xc (DSC) vs D (WAXS) scatter."""
    clean = df[["Xc_pct", "D_Scherrer_nm"]].dropna() if {"Xc_pct", "D_Scherrer_nm"}.issubset(df.columns) else pd.DataFrame()
    if clean.empty:
        return None

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(clean["Xc_pct"], clean["D_Scherrer_nm"], color="#2ca02c", s=60, edgecolors="white")
    ax.set_xlabel("Crystallinity Xc (%)")
    ax.set_ylabel("Crystallite Size D (nm)")
    plt.tight_layout()
    return _fig_to_bytes(fig)


def plot_ir_vs_dsc_xc(df: pd.DataFrame) -> BytesIO | None:
    """IR CI vs DSC Xc scatter."""
    clean = df[["IR_CI", "DSC_Xc"]].dropna() if {"IR_CI", "DSC_Xc"}.issubset(df.columns) else pd.DataFrame()
    if clean.empty:
        return None

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(clean["IR_CI"], clean["DSC_Xc"], color="#9467bd", s=60, edgecolors="white")
    ax.set_xlabel("IR Crystallinity Index")
    ax.set_ylabel("DSC Crystallinity Xc (%)")
    plt.tight_layout()
    return _fig_to_bytes(fig)


def plot_correlation_matrix(result: dict, min_n: int = 5) -> BytesIO | None:
    """Parameter correlation matrix heatmap with significance annotations."""
    mat = result.get("correlation")
    pvals = result.get("p_values")
    counts = result.get("sample_sizes")

    if mat is None or mat.empty:
        return None

    params = list(mat.columns)
    n = len(params)
    if n < 2:
        return None

    fig, ax = plt.subplots(figsize=(max(6, n * 1.2), max(5, n * 1.0)))
    display = mat.values.copy().astype(float)
    annot = np.empty_like(display, dtype=object)

    for i, pi in enumerate(params):
        for j, pj in enumerate(params):
            r = mat.iloc[i, j]
            p = pvals.iloc[i, j] if pvals is not None else np.nan
            cnt = int(counts.iloc[i, j]) if counts is not None else 0

            if cnt < 2:
                display[i, j] = np.nan
                annot[i, j] = f"n={cnt}"
            else:
                display[i, j] = r if not np.isnan(r) else 0
                sig = "*" if p is not None and not np.isnan(p) and p < 0.05 else ""
                annot[i, j] = f"{r:.2f}{sig}\nn={cnt}"

    cmap = plt.cm.RdBu_r
    norm = mcolors.TwoSlopeNorm(vcenter=0)
    im = ax.imshow(display, cmap=cmap, norm=norm, aspect="auto")

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(params, rotation=45, ha="right")
    ax.set_yticklabels(params)

    for i in range(n):
        for j in range(n):
            cnt = int(counts.iloc[i, j]) if counts is not None else 0
            if np.isnan(display[i, j]):
                continue
            color = "white" if abs(display[i, j]) > 0.5 else "black"
            if cnt < min_n and i != j:
                color = "#666666"
            ax.text(j, i, annot[i, j], ha="center", va="center", fontsize=9, color=color)

    plt.colorbar(im, ax=ax, label="r")
    plt.tight_layout()
    return _fig_to_bytes(fig)


def plot_heatmap_overview(summaries: list) -> BytesIO | None:
    """Comprehensive heatmap: rows=samples, columns=parameters."""
    if not summaries:
        return None

    df = pd.DataFrame(summaries)
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not num_cols:
        return None

    fig, ax = plt.subplots(figsize=(max(6, len(num_cols) * 1.5), max(4, len(df) * 0.5)))
    data = df[num_cols].values
    im = ax.imshow(data.T, cmap="viridis", aspect="auto")

    labels = [s.get("_sample_name", f"#{i+1}") for i, s in enumerate(summaries)]
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_yticks(range(len(num_cols)))
    ax.set_yticklabels(num_cols)

    for i in range(len(labels)):
        for j in range(len(num_cols)):
            val = data[i, j]
            if not np.isnan(val):
                ax.text(i, j, f"{val:.1f}", ha="center", va="center", fontsize=7, color="white")

    plt.colorbar(im, ax=ax)
    plt.tight_layout()
    return _fig_to_bytes(fig)


def plot_timeline_alignment(df: pd.DataFrame) -> BytesIO | None:
    """Plot aligned timeline points by parameter on a shared condition axis."""
    if df is None or df.empty:
        return None

    required = {"shared_condition_value", "param_key", "value"}
    if not required.issubset(df.columns):
        return None

    clean = df.dropna(subset=["shared_condition_value", "value", "param_key"])
    if clean.empty:
        return None

    params = list(dict.fromkeys(clean["param_key"].astype(str).tolist()))
    if not params:
        return None

    fig, ax = plt.subplots(figsize=(10, max(4, 1.6 * len(params))))
    palette = plt.cm.tab10(np.linspace(0, 1, max(1, len(params))))

    for idx, param in enumerate(params):
        subset = clean[clean["param_key"].astype(str) == param].copy()
        subset = subset.sort_values("shared_condition_value")
        if subset.empty:
            continue
        x = subset["shared_condition_value"].astype(float).to_numpy()
        y = subset["value"].astype(float).to_numpy()
        color = palette[idx % len(palette)]
        ax.plot(x, y, marker="o", linewidth=1.8, color=color, label=param)

    ax.set_xlabel("Shared condition axis")
    ax.set_ylabel("Value")
    ax.set_title("Aligned timeline overview")
    ax.legend(loc="best", frameon=False)
    ax.grid(True, alpha=0.2)
    plt.tight_layout()
    return _fig_to_bytes(fig)
