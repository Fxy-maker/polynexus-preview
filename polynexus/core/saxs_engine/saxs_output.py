
import logging
logger = logging.getLogger(__name__)

"""
saxs_output.py 閳?Module 7 + 9: SCI-grade visualization & data export.

Covers all figure types from the SAXS Design Document:
  Universal: Fig-U1 (1D curve), Fig-U2 (correlation), Fig-U3 (IDF), Fig-U4 (Porod)
  Tensile:   Fig-T1 (2D sequence), Fig-T2 (waterfall), Fig-T3 (parameters),
             Fig-T4 (invariant conservation)
  Temperature: Fig-V1 (curve sequence), Fig-V2 (parameters), Fig-V3 (heatmap),
               Fig-V4 (Avrami)
  Joint:     Kratky, Guinier, multi-technique cross-validation

All figures follow SCI publication standards: Arial 8pt, 300 DPI,
single/double column layouts, consistent color schemes.
"""

import csv
import os
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['svg.fonttype'] = 'none'  # Qt SVG compatibility: embed text, not font refs
from matplotlib.ticker import ScalarFormatter, LogFormatter
from scipy.ndimage import gaussian_filter

from .config import SAXSConfig
from .saxs_output_runtime_helpers import (
    _downsample_plot as _helper_downsample_plot,
    _ensure_non_gui_backend as _helper_ensure_non_gui_backend,
    _make_output_dirs as _helper_make_output_dirs,
    _remove_stale_variant as _helper_remove_stale_variant,
    _safe_legend as _helper_safe_legend,
)
from .saxs_output_helpers import (
    _csv_number,
    _finite_csv,
    _json_number,
    _result_to_params_dict as _helper_result_to_params_dict,
    _result_effective_lc_value,
    export_1d_profile as _helper_export_1d_profile,
    export_parameters_csv as _helper_export_parameters_csv,
    export_strain_series_csv as _helper_export_strain_series_csv,
    export_temp_series_csv as _helper_export_temp_series_csv,
)
from .saxs_output_data_writers import (
    _write_condition_overview_profile_data as _helper_write_condition_overview_profile_data,
    _write_condition_overview_summary_data as _helper_write_condition_overview_summary_data,
    _write_guinier_data as _helper_write_guinier_data,
    _write_joint_crystallinity_data as _helper_write_joint_crystallinity_data,
    _write_kratky_data as _helper_write_kratky_data,
    _write_series_waterfall_data as _helper_write_series_waterfall_data,
    _write_static_overview_profile_data as _helper_write_static_overview_profile_data,
    _write_static_overview_summary_data as _helper_write_static_overview_summary_data,
    _write_t3_structure_data as _helper_write_t3_structure_data,
    _write_t4_invariant_data as _helper_write_t4_invariant_data,
    _write_v2_temperature_parameters_data as _helper_write_v2_temperature_parameters_data,
    _write_v3_heatmap_data as _helper_write_v3_heatmap_data,
    _write_v3_qstar_data as _helper_write_v3_qstar_data,
    _write_v4_avrami_data as _helper_write_v4_avrami_data,
    _write_u1_scattering_data as _helper_write_u1_scattering_data,
    _write_u2_correlation_data as _helper_write_u2_correlation_data,
    _write_u3_idf_data as _helper_write_u3_idf_data,
    _write_u4_porod_data as _helper_write_u4_porod_data,
)
from .saxs_output_documents import (
    _save_condition_overview_document as _helper_save_condition_overview_document,
    _save_guinier_document as _helper_save_guinier_document,
    _save_joint_crystallinity_document as _helper_save_joint_crystallinity_document,
    _save_kratky_document as _helper_save_kratky_document,
    _save_series_waterfall_document as _helper_save_series_waterfall_document,
    _save_static_overview_document as _helper_save_static_overview_document,
    _save_t3_structure_document as _helper_save_t3_structure_document,
    _save_t4_invariant_document as _helper_save_t4_invariant_document,
    _save_u1_scattering_document as _helper_save_u1_scattering_document,
    _save_u2_correlation_document as _helper_save_u2_correlation_document,
    _save_u3_idf_document as _helper_save_u3_idf_document,
    _save_u4_porod_document as _helper_save_u4_porod_document,
    _save_v2_temperature_parameters_document as _helper_save_v2_temperature_parameters_document,
    _save_v3_heatmap_document as _helper_save_v3_heatmap_document,
    _save_v4_avrami_document as _helper_save_v4_avrami_document,
)
from ..figure_document import save_generated_figure_document
from ..plot_edits import savefig_with_edits
from ...plotting.sci_style import (
    set_sci_style as _set_sci_style,
    apply_panel_label as _saxs_panel,
    WONG_COLORS, ANNOTATION_COLORS,
    FIG_SIZES as _CENTRAL_FIG_SIZES,
    AXIS_LABELS,
    save_figure_sci,
)
try:
    from ..generated_figure_document_builder import save_generated_figure_bundle
except Exception:  # pragma: no cover - compatibility for branches without Phase 3 builder
    save_generated_figure_bundle = None

_downsample_plot = _helper_downsample_plot
_remove_stale_variant = _helper_remove_stale_variant
_ensure_non_gui_backend = _helper_ensure_non_gui_backend
_safe_legend = _helper_safe_legend
export_parameters_csv = _helper_export_parameters_csv
export_1d_profile = _helper_export_1d_profile
export_strain_series_csv = _helper_export_strain_series_csv
export_temp_series_csv = _helper_export_temp_series_csv
_result_to_params_dict = _helper_result_to_params_dict
_write_u1_scattering_data = _helper_write_u1_scattering_data
_write_u2_correlation_data = _helper_write_u2_correlation_data
_write_u3_idf_data = _helper_write_u3_idf_data
_write_u4_porod_data = _helper_write_u4_porod_data
_write_guinier_data = _helper_write_guinier_data
_write_kratky_data = _helper_write_kratky_data
_write_joint_crystallinity_data = _helper_write_joint_crystallinity_data
_write_series_waterfall_data = _helper_write_series_waterfall_data
_write_t3_structure_data = _helper_write_t3_structure_data
_write_t4_invariant_data = _helper_write_t4_invariant_data
_write_v2_temperature_parameters_data = _helper_write_v2_temperature_parameters_data
_write_v3_heatmap_data = _helper_write_v3_heatmap_data
_write_v3_qstar_data = _helper_write_v3_qstar_data
_write_v4_avrami_data = _helper_write_v4_avrami_data
_write_static_overview_profile_data = _helper_write_static_overview_profile_data
_write_static_overview_summary_data = _helper_write_static_overview_summary_data
_write_condition_overview_profile_data = _helper_write_condition_overview_profile_data
_write_condition_overview_summary_data = _helper_write_condition_overview_summary_data
_save_u1_scattering_document = _helper_save_u1_scattering_document
_save_u2_correlation_document = _helper_save_u2_correlation_document
_save_u3_idf_document = _helper_save_u3_idf_document
_save_u4_porod_document = _helper_save_u4_porod_document
_save_guinier_document = _helper_save_guinier_document
_save_kratky_document = _helper_save_kratky_document
_save_joint_crystallinity_document = _helper_save_joint_crystallinity_document
_save_series_waterfall_document = _helper_save_series_waterfall_document
_save_t3_structure_document = _helper_save_t3_structure_document
_save_t4_invariant_document = _helper_save_t4_invariant_document
_save_v2_temperature_parameters_document = _helper_save_v2_temperature_parameters_document
_save_v4_avrami_document = _helper_save_v4_avrami_document
_save_v3_heatmap_document = _helper_save_v3_heatmap_document
_save_static_overview_document = _helper_save_static_overview_document
_save_condition_overview_document = _helper_save_condition_overview_document


def _save_generated_figure_bundle_compat(path: str, **document_kwargs) -> None:
    if callable(save_generated_figure_bundle):
        try:
            save_generated_figure_bundle(path, **document_kwargs)
            return
        except TypeError:
            payload = {"figure_path": path, **document_kwargs}
            save_generated_figure_bundle(**payload)
            return
    save_generated_figure_document(path, **document_kwargs)


def _save_phase3_guinier_bundle(
    path: str,
    q: np.ndarray,
    intensity: np.ndarray,
    *,
    Rg: Optional[float] = None,
    q_min: float = 0.04,
    q_max: float = 0.15,
) -> None:
    mask = (q >= q_min) & (q <= q_max)
    q_sel = q[mask]
    intensity_sel = intensity[mask]
    positive = intensity_sel > 0
    slope = intercept = None
    if np.sum(positive) > 4:
        slope, intercept = np.polyfit(q_sel[positive] ** 2, np.log(intensity_sel[positive]), 1)
    data_path = _write_guinier_data(path, q_sel[positive], intensity_sel[positive], slope, intercept)
    data_ref = "saxs-guinier-data"
    objects = [
        {
            "id": "series-guinier-points",
            "type": "plot_series",
            "chart_kind": "scatter",
            "name": "Guinier Points",
            "data_ref": data_ref,
            "x_column": "q2_nm_minus2",
            "y_column": "ln_intensity",
            "style": {"color": COLOR_SCHEMES["main"], "marker_size": 8, "alpha": 0.7},
        },
    ]
    if slope is not None:
        objects.append(
            {
                "id": "series-guinier-fit",
                "type": "plot_series",
                "name": "Guinier Fit",
                "data_ref": data_ref,
                "x_column": "q2_nm_minus2",
                "y_column": "fit",
                "style": {"color": COLOR_SCHEMES["secondary"], "line_width": 1.0},
            }
        )
    _save_generated_figure_bundle_compat(
        path,
        technique="saxs",
        figure_id=Path(path).stem,
        data_sources=[
            {
                "id": data_ref,
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": __name__,
            "function": "fig_guinier",
            "inputs": {},
            "parameters": {
                "Rg": _json_number(Rg),
                "q_min": _json_number(q_min),
                "q_max": _json_number(q_max),
                "slope": _json_number(slope),
                "intercept": _json_number(intercept),
            },
        },
        style={
            "xlabel": "q^2 (nm^-2)",
            "ylabel": "ln I(q)",
        },
        objects=objects,
    )


def _save_phase3_kratky_bundle(
    path: str,
    q: np.ndarray,
    intensity: np.ndarray,
    *,
    L: Optional[float] = None,
) -> None:
    data_path = _write_kratky_data(path, q, intensity)
    data_ref = "saxs-kratky-data"
    q_star = 2 * np.pi / L if L is not None and np.isfinite(L) and L > 0 else None
    objects = [
        {
            "id": "series-kratky",
            "type": "plot_series",
            "name": "Kratky Plot",
            "data_ref": data_ref,
            "x_column": "q_nm_inv",
            "y_column": "iq2",
            "style": {"color": COLOR_SCHEMES["main"], "line_width": 1.0},
        },
    ]
    if q_star is not None:
        objects.extend(
            [
                {
                    "id": "marker-q-star",
                    "type": "line",
                    "name": "Lamellar q*",
                    "orientation": "vertical",
                    "x": _json_number(q_star),
                    "label": f"q*={q_star:.3f} nm^-1",
                    "style": {"color": COLOR_SCHEMES["secondary"], "line_width": 0.8, "alpha": 0.7},
                },
            ]
        )
    _save_generated_figure_bundle_compat(
        path,
        technique="saxs",
        figure_id=Path(path).stem,
        data_sources=[
            {
                "id": data_ref,
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": __name__,
            "function": "fig_kratky",
            "inputs": {},
            "parameters": {
                "L": _json_number(L),
                "q_star": _json_number(q_star),
            },
        },
        style={
            "xlabel": "q (nm^-1)",
            "ylabel": "I(q) * q^2 (a.u.)",
        },
        objects=objects,
    )


# ======================================================================
#  Local SCI style 閳?references central sci_style
# ======================================================================

# Use central figure sizes + add SAXS-specific waterfall size
FIG_SIZES = dict(_CENTRAL_FIG_SIZES)
FIG_SIZES['wide_waterfall'] = (8.0, 5.0)

# SCI color schemes
COLOR_SCHEMES = {
    'main':          '#2563eb',  # primary blue
    'secondary':     '#dc2626',  # red
    'tertiary':      '#16a34a',  # green
    'highlight':     '#9333ea',  # purple
    'grey':          '#6b7280',
    'heatmap':       'viridis',
    'heatmap_div':   'RdBu_r',
    'heatmap_seq':   'YlOrRd',
}

# DPI settings
SCI_DPI = 300
PREVIEW_DPI = 150

def set_sci_style():
    """Apply SCI publication-grade matplotlib style via central module."""
    _helper_ensure_non_gui_backend()
    _set_sci_style(font_size=8.0, dpi=PREVIEW_DPI)


def _make_output_dirs(output_dir: str):
    return _helper_make_output_dirs(output_dir)


# ======================================================================
#  Universal figures (all experiment types)
# ======================================================================

def fig_u1_scattering_profile(
    q: np.ndarray, I: np.ndarray,
    q_star: Optional[float] = None,
    L: Optional[float] = None,
    label: str = "",
    output_path: Optional[str] = None,
    is_low_conf: bool = False,
    log_scale: bool = True,
    figsize: str = 'single_col',
) -> str:
    """Fig-U1: 1D scattering curve I(q). P1 priority.

    Dual-axis: linear + Lorentz-corrected (I*q^2).
    Marks Bragg peak position.
    When is_low_conf=True, left axis auto-crops the beamstop spike
    to a maximum q where I drops below 50x the lamellar-region median.
    """
    set_sci_style()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=FIG_SIZES.get(figsize, FIG_SIZES['double_col']))

    # Left: I(q)
    q_plot, I_plot = _downsample_plot(q, I)

    # ---- Beamstop-spike cropping for low-confidence data ----
    q_crop_min = 0.0
    if is_low_conf and len(q_plot) > 20:
        # Find the lamellar-region median I (q=0.4-1.0 nm-1)
        lam_mask = (q_plot >= 0.4) & (q_plot <= 1.0)
        if np.sum(lam_mask) > 5:
            I_lam_median = float(np.median(I_plot[lam_mask]))
            if I_lam_median > 0:
                # Find first q where I < 50x the lamellar median
                for qi, Ii in zip(q_plot, I_plot):
                    if Ii > 0 and Ii < 50.0 * I_lam_median:
                        q_crop_min = float(qi)
                        break
        if q_crop_min > 0:
            crop_mask = q_plot >= q_crop_min * 0.95
            q_plot_v = q_plot[crop_mask]
            I_plot_v = I_plot[crop_mask]
        else:
            q_plot_v, I_plot_v = q_plot, I_plot
    else:
        q_plot_v, I_plot_v = q_plot, I_plot

    if log_scale:
        ax1.loglog(q_plot_v, I_plot_v, color=COLOR_SCHEMES['main'], linewidth=1.0)
    else:
        ax1.semilogy(q_plot_v, I_plot_v, color=COLOR_SCHEMES['main'], linewidth=1.0)

    if is_low_conf and q_crop_min > 0:
        ax1.axvline(q_crop_min, color='#D55E00', linestyle=':', alpha=0.5, linewidth=0.6)
        ax1.annotate(f'Beamstop\ncut={q_crop_min:.3f}', xy=(q_crop_min, np.interp(q_crop_min, q_plot_v, I_plot_v) if len(q_plot_v) > 0 else 1),
                     fontsize=5, color='#D55E00', alpha=0.6)
    
    if q_star is not None and np.isfinite(q_star):
        ax1.axvline(q_star, color=COLOR_SCHEMES['secondary'], linestyle='--', 
                     alpha=0.7, linewidth=0.8)
        if L and np.isfinite(L):
            ax1.annotate(f'$q^*$={q_star:.3f}\n$L$={L:.1f} nm',
                        xy=(q_star, np.interp(q_star, q_plot_v, I_plot_v)),
                        fontsize=7, color=COLOR_SCHEMES['secondary'])
    
    ax1.set_xlabel(r'$q$ (nm$^{-1}$)')
    ax1.set_ylabel(r'$I(q)$ (a.u.)')
    pass  # title removed for SCI (caption-only)

    # Right: Lorentz-corrected I*q^2
    # For low-conf data, zoom to lamellar region (q=0.15-1.5) to reveal peak
    if is_low_conf:
        zoom_mask = (q_plot >= 0.15) & (q_plot <= 1.5)
        qz, Iz = q_plot[zoom_mask], I_plot[zoom_mask]
    else:
        qz, Iz = q_plot, I_plot
    Iq2 = Iz * qz**2
    ax2.plot(qz, Iq2, color=COLOR_SCHEMES['main'], linewidth=1.0)
    if q_star is not None and np.isfinite(q_star):
        ax2.axvline(q_star, color=COLOR_SCHEMES['secondary'], linestyle='--',
                     alpha=0.7, linewidth=0.8, label=f'$q^*$={q_star:.3f}')
        # Auto-scale y-axis: focus on region around the Lorentz peak
        peak_half_width = 0.3  # nm-1 around q_star
        mask_peak = (qz >= q_star - peak_half_width) & (qz <= q_star + peak_half_width)
        if np.sum(mask_peak) > 5:
            Iq2_peak = Iq2[mask_peak]
            y_max = np.max(Iq2_peak) * 1.3
            y_min = max(0, np.min(Iq2_peak) * 0.5)
            if y_max > y_min * 2:
                ax2.set_ylim(y_min, y_max)
    ax2.set_xlabel(r'$q$ (nm$^{-1}$)')
    ax2.set_ylabel(r'$I(q) \cdot q^2$ (a.u.)')
    pass

    plt.tight_layout()
    # output_path always treated as a full file path
    path = output_path if output_path else 'Fig_U1_scattering.pdf'
    savefig_with_edits(fig, path, dpi=SCI_DPI)
    plt.close(fig)
    _save_u1_scattering_document(
        path,
        q,
        I,
        q_star=q_star,
        L=L,
        label=label,
        log_scale=log_scale,
        is_low_conf=is_low_conf,
    )
    return path


def fig_u2_correlation_function(
    r: np.ndarray, gamma: np.ndarray,
    L: Optional[float] = None,
    lc: Optional[float] = None,
    output_path: Optional[str] = None,
    figsize: str = 'single_col',
    is_low_conf: bool = False,
) -> str:
    """Fig-U2: Electron density correlation function gamma(r). P1 priority.

    Marks L (first maximum) and lc (tangent method intersection).
    """
    set_sci_style()
    fig, ax = plt.subplots(figsize=FIG_SIZES.get(figsize, FIG_SIZES['single_col']))

    ax.plot(r, gamma, color=COLOR_SCHEMES['main'], linewidth=1.2)
    ax.axhline(0, color='black', linewidth=0.5, linestyle=':')

    # Mark L (first maximum)
    if L is not None and np.isfinite(L):
        ax.axvline(L, color=COLOR_SCHEMES['secondary'], linestyle='--',
                   alpha=0.7, linewidth=0.8, label=f'$L$={L:.1f} nm')

    # Mark lc via tangent method
    if lc is not None and np.isfinite(lc) and len(r) > 5:
        # Draw tangent from first minimum
        idx_min = np.argmin(gamma) if np.any(gamma < 0) else 0
        if idx_min > 1:
            # Draw baseline and tangent intersection
            ax.plot([0, lc], [gamma[0], 0], color=COLOR_SCHEMES['tertiary'],
                    linestyle=':', linewidth=0.8)
            ax.axvline(lc, color=COLOR_SCHEMES['tertiary'], linestyle='--',
                       alpha=0.7, linewidth=0.5, label=f'$l_c$={lc:.1f} nm')

    ax.set_xlabel(r'$r$ (nm)')
    ax.set_ylabel(r'$\gamma(r)$')
    pass
    if L is not None or lc is not None:
        _safe_legend(ax, fontsize=7)

    # Auto-crop x-axis: find where gamma oscillations decay below 1% amplitude
    gamma_abs = np.abs(gamma)
    # Find last index where |gamma| > 1% of max (but at least 2*L or 30nm)
    threshold = max(0.01, 0.005 * np.max(gamma_abs))
    visible_idx = np.where(gamma_abs > threshold)[0]
    if len(visible_idx) > 0:
        clip_r = r[visible_idx[-1]] * 1.1  # add 10% margin
    else:
        clip_r = max(L * 3 if L else 0, 30)
    ax.set_xlim(0, max(clip_r, L * 2.5 if L else 20))

    plt.tight_layout()
    out = output_path or 'Fig_U2_correlation.pdf'
    savefig_with_edits(fig, out, dpi=SCI_DPI)
    plt.close(fig)
    _save_u2_correlation_document(
        out,
        r,
        gamma,
        L=L,
        lc=lc,
        is_low_conf=is_low_conf,
    )
    return out


def fig_u3_idf(
    r_idf: np.ndarray, idf: np.ndarray,
    L_idf: Optional[float] = None,
    lc_idf: Optional[float] = None,
    output_path: Optional[str] = None,
    figsize: str = 'single_col',
    is_low_conf: bool = False,
) -> str:
    """Fig-U3: Interface Distribution Function (IDF). P1 priority.

    Peaks indicate characteristic thicknesses.
    """
    set_sci_style()
    fig, ax = plt.subplots(figsize=FIG_SIZES.get(figsize, FIG_SIZES['single_col']))

    ax.plot(r_idf, idf, color=COLOR_SCHEMES['main'], linewidth=1.2)
    ax.axhline(0, color='black', linewidth=0.5, linestyle=':')
    ax.fill_between(r_idf, 0, idf, alpha=0.15, color=COLOR_SCHEMES['main'])

    if lc_idf is not None and np.isfinite(lc_idf):
        ax.axvline(lc_idf, color=COLOR_SCHEMES['tertiary'], linestyle='--',
                   alpha=0.7, linewidth=0.8, label=f'$l_c$={lc_idf:.1f} nm')
    if L_idf is not None and np.isfinite(L_idf):
        ax.axvline(L_idf, color=COLOR_SCHEMES['secondary'], linestyle='--',
                   alpha=0.7, linewidth=0.8, label=f'$L$={L_idf:.1f} nm')

    ax.set_xlabel(r'$r$ (nm)')
    ax.set_ylabel(r'$g_1(r)$ (a.u.)')
    pass
    if L_idf is not None or lc_idf is not None:
        _safe_legend(ax, fontsize=7)

    plt.tight_layout()
    out = output_path or 'Fig_U3_IDF.pdf'
    savefig_with_edits(fig, out, dpi=SCI_DPI)
    plt.close(fig)
    _save_u3_idf_document(
        out,
        r_idf,
        idf,
        L_idf=L_idf,
        lc_idf=lc_idf,
        is_low_conf=is_low_conf,
    )
    return out


def fig_u4_porod(
    q_porod: np.ndarray, Iq4: np.ndarray,
    slope: Optional[float] = None,
    Kp: Optional[float] = None,
    output_path: Optional[str] = None,
    figsize: str = 'single_col',
    is_low_conf: bool = False,
) -> str:
    """Fig-U4: Porod plot I*q^4 vs q^4. P2 priority.

    For ideal two-phase system: constant plateau.
    """
    set_sci_style()
    fig, ax = plt.subplots(figsize=FIG_SIZES.get(figsize, FIG_SIZES['single_col']))

    ax.plot(q_porod**4, Iq4, 'o', color=COLOR_SCHEMES['main'], markersize=2, alpha=0.5)
    
    # Linear fit in high-q region
    if slope is not None:
        x_fit = np.linspace(np.min(q_porod**4), np.max(q_porod**4), 100)
        intercept = np.mean(Iq4[-10:]) - slope * np.mean(q_porod[-10:]**4)
        ax.plot(x_fit, slope * x_fit + intercept, color=COLOR_SCHEMES['secondary'],
                linewidth=1.0, label=f'K$_p$={Kp:.2e}' if Kp else '')

    ax.set_xlabel(r'$q^4$ (nm$^{-4}$)')
    ax.set_ylabel(r'$I(q) \cdot q^4$ (a.u.)')
    pass
    if ax.get_legend_handles_labels()[0]:
        _safe_legend(ax, fontsize=7)

    plt.tight_layout()
    out = output_path or 'Fig_U4_Porod.pdf'
    savefig_with_edits(fig, out, dpi=SCI_DPI)
    plt.close(fig)
    _save_u4_porod_document(
        out,
        q_porod,
        Iq4,
        slope=slope,
        Kp=Kp,
        is_low_conf=is_low_conf,
    )
    return out


# ======================================================================
#  Tensile-specific figures
# ======================================================================

def fig_t2_scattering_waterfall(
    strains: np.ndarray,
    q_list: List[np.ndarray],
    I_list: List[np.ndarray],
    output_path: Optional[str] = None,
    n_curves: int = 12,
    figsize: str = 'double_col',
) -> str:
    """Fig-T2: 1D scattering curve waterfall (strain sequence). P1 priority.

    Offset curves for visual evolution.
    """
    set_sci_style()
    fig, ax = plt.subplots(figsize=FIG_SIZES.get(figsize, FIG_SIZES['double_col']))

    total = len(strains)
    if total <= n_curves:
        indices = list(range(total))
    else:
        step = total // n_curves
        indices = list(range(0, total, max(1, step)))

    offset = 0
    colors = plt.cm.viridis(np.linspace(0.1, 0.9, len(indices)))

    for i, idx in enumerate(indices):
        q = q_list[idx]
        I = I_list[idx]
        I_shifted = I + offset * 0.3
        label = f'{strains[idx]:.0f}%' if i % 2 == 0 else ''
        ax.loglog(q, I_shifted, color=colors[i], linewidth=0.8, label=label)
        offset += max(I) * 0.3

    ax.set_xlabel(r'$q$ (nm$^{-1}$)')
    ax.set_ylabel(r'$I(q)$ offset (a.u.)')
    pass
    _safe_legend(ax, fontsize=6, ncol=2, loc='upper right')

    plt.tight_layout()
    out = output_path or 'Fig_T2_waterfall.pdf'
    savefig_with_edits(fig, out, dpi=SCI_DPI)
    plt.close(fig)
    _save_series_waterfall_document(
        out,
        strains,
        q_list,
        I_list,
        indices=indices,
        condition_axis="strain_pct",
        function_name="fig_t2_scattering_waterfall",
    )
    return out


def fig_t3_structure_evolution(
    strains: np.ndarray,
    L_array: np.ndarray,
    lc_array: np.ndarray,
    phi_c_array: Optional[np.ndarray] = None,
    f_herman_array: Optional[np.ndarray] = None,
    Q_star_array: Optional[np.ndarray] = None,
    phase_boundaries: Optional[Dict] = None,
    output_path: Optional[str] = None,
    figsize: str = 'double_col_2x2',
) -> str:
    """Fig-T3: Structure parameter evolution with strain (core finding). P1 priority.

    4-panel: L, lc, phi_c (or Q*), f_Herman.
    Phase backgrounds for context.
    """
    set_sci_style()
    
    # Determine which panels to show
    has_herman = f_herman_array is not None and np.any(np.isfinite(f_herman_array))
    has_qstar = Q_star_array is not None and np.any(np.isfinite(Q_star_array))
    has_phic = phi_c_array is not None and np.any(np.isfinite(phi_c_array))

    n_panels = 2 + (1 if has_herman else 0) + (1 if has_qstar or has_phic else 0)
    nrows = (n_panels + 1) // 2
    ncols = min(n_panels, 2)
    
    if n_panels <= 2:
        figsize = FIG_SIZES['double_col']
    else:
        figsize = FIG_SIZES['double_col_2x2']

    fig, axes = plt.subplots(nrows, ncols, figsize=figsize)
    if n_panels == 1:
        axes = [axes]
    else:
        axes = axes.flatten()

    # Phase backgrounds
    phase_colors = {
        'ELASTIC': '#e0f2fe',
        'PLASTIC_VOIDING': '#fef3c7',
        'MICROFIBRILLATION': '#fce7f3',
        'FRACTURE': '#fee2e2',
    }

    def _add_phase_bg(ax, phase_boundaries, x_max):
        """Add colored phase backgrounds to axes."""
        if phase_boundaries is None:
            return
        pb_sorted = sorted([(v, k.name) for k, v in phase_boundaries.items() 
                           if np.isfinite(v)], key=lambda x: x[0])
        prev_x = 0
        for x, phase_name in pb_sorted:
            color = phase_colors.get(phase_name, '#f0f0f0')
            ax.axvspan(prev_x, x, alpha=0.2, color=color)
            prev_x = x
        if x_max > prev_x:
            ax.axvspan(prev_x, x_max, alpha=0.2, color=list(phase_colors.values())[-1])

    x_max = np.nanmax(strains) * 1.05

    # Panel (a): Long period L
    ax = axes[0]
    ax.plot(strains, L_array, 'o-', color=COLOR_SCHEMES['main'], markersize=4, linewidth=1.2)
    _add_phase_bg(ax, phase_boundaries, x_max)
    ax.set_xlabel(r'$\varepsilon$ (%)')
    ax.set_ylabel(r'$L$ (nm)')
    ax.set_title('(a) Long Period')

    # Panel (b): lc and la
    ax = axes[1]
    ax.plot(strains, lc_array, 'o-', color=COLOR_SCHEMES['secondary'], markersize=4, 
            linewidth=1.2, label=r'$l_c$')
    if L_array is not None and lc_array is not None:
        la = L_array - lc_array
        ax.plot(strains, la, 's--', color=COLOR_SCHEMES['tertiary'], markersize=3,
                linewidth=1.0, label=r'$l_a$')
    _add_phase_bg(ax, phase_boundaries, x_max)
    ax.set_xlabel(r'$\varepsilon$ (%)')
    ax.set_ylabel('Thickness (nm)')
    ax.set_title('(b) Lamellar Thickness')
    _safe_legend(ax, fontsize=7)

    panel_idx = 2

    # Panel (c): Crystallinity or Q*
    if has_qstar or has_phic or panel_idx < n_panels:
        ax = axes[panel_idx] if panel_idx < len(axes) else axes[-1]
        plot_data = phi_c_array if has_phic else Q_star_array
        ylabel = r'$\phi_c$' if has_phic else r'$Q^*$ (a.u.)'
        title = '(c) Crystallinity' if has_phic else '(c) Invariant'
        ax.plot(strains, plot_data, 'o-', color=COLOR_SCHEMES['highlight'], 
                markersize=4, linewidth=1.2)
        _add_phase_bg(ax, phase_boundaries, x_max)
        ax.set_xlabel(r'$\varepsilon$ (%)')
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        panel_idx += 1

    # Panel (d): Herman factor
    if has_herman and panel_idx < n_panels:
        ax = axes[panel_idx] if panel_idx < len(axes) else axes[-1]
        ax.plot(strains, f_herman_array, 'o-', color=COLOR_SCHEMES['highlight'],
                markersize=4, linewidth=1.2)
        ax.axhline(0, color='black', linewidth=0.5, linestyle=':')
        ax.axhline(1, color='grey', linewidth=0.5, linestyle=':')
        ax.axhline(-0.5, color='grey', linewidth=0.5, linestyle=':')
        _add_phase_bg(ax, phase_boundaries, x_max)
        ax.set_xlabel(r'$\varepsilon$ (%)')
        ax.set_ylabel(r'$f_{\mathrm{Herman}}$')
        ax.set_title('(d) Orientation Factor')

    # Hide unused axes
    for j in range(panel_idx, len(axes)):
        axes[j].set_visible(False)

    plt.tight_layout()
    out = output_path or 'Fig_T3_parameters.pdf'
    savefig_with_edits(fig, out, dpi=SCI_DPI)
    plt.close(fig)
    _save_t3_structure_document(
        out,
        strains,
        L_array,
        lc_array,
        phi_c_array=phi_c_array,
        f_herman_array=f_herman_array,
        Q_star_array=Q_star_array,
    )
    return out


def fig_t4_invariant_conservation(
    strains: np.ndarray,
    Q_star_array: np.ndarray,
    Q_ref: Optional[float] = None,
    tolerance: float = 0.05,
    output_path: Optional[str] = None,
    figsize: str = 'single_col',
) -> str:
    """Fig-T4: Invariant conservation verification. P2 priority."""
    set_sci_style()
    fig, ax = plt.subplots(figsize=FIG_SIZES.get(figsize, FIG_SIZES['single_col']))

    Q_norm = Q_star_array / Q_ref if Q_ref and Q_ref > 0 else Q_star_array

    ax.plot(strains, Q_norm, 'o-', color=COLOR_SCHEMES['main'], markersize=4, linewidth=1.2)
    ax.axhline(1.0, color='black', linewidth=0.5, linestyle=':')
    ax.axhspan(1 - tolerance, 1 + tolerance, alpha=0.1, color=COLOR_SCHEMES['tertiary'],
               label=f'+-{tolerance*100:.0f}%')

    ax.set_xlabel(r'$\varepsilon$ (%)')
    ax.set_ylabel(r'$Q^* / Q^*_0$')
    pass
    _safe_legend(ax, fontsize=7)

    plt.tight_layout()
    out = output_path or 'Fig_T4_invariant.pdf'
    savefig_with_edits(fig, out, dpi=SCI_DPI)
    plt.close(fig)
    _save_t4_invariant_document(
        out,
        strains,
        Q_star_array,
        Q_ref=Q_ref,
        tolerance=tolerance,
    )
    return out


# ======================================================================
#  Temperature-specific figures
# ======================================================================

def fig_v1_temperature_waterfall(
    temperatures: np.ndarray,
    q_list: List[np.ndarray],
    I_list: List[np.ndarray],
    output_path: Optional[str] = None,
    n_curves: int = 10,
    figsize: str = 'double_col',
) -> str:
    """Fig-V1: 1D scattering curve sequence with temperature. P1 priority."""
    set_sci_style()
    fig, ax = plt.subplots(figsize=FIG_SIZES.get(figsize, FIG_SIZES['double_col']))

    total = len(temperatures)
    step = max(1, total // n_curves)
    indices = list(range(0, total, step))

    # Blue-to-red colormap for cold-to-hot
    colors = plt.cm.coolwarm(np.linspace(0.1, 0.9, len(indices)))
    offset = 0

    for i, idx in enumerate(indices):
        q = q_list[idx]
        I = I_list[idx]
        offset_factor = max(I) * 0.5
        ax.loglog(q, I + offset, color=colors[i], linewidth=0.8,
                  label=f'{temperatures[idx]:.0f} C')
        offset += offset_factor

    ax.set_xlabel(r'$q$ (nm$^{-1}$)')
    ax.set_ylabel(r'$I(q)$ offset (a.u.)')
    pass
    _safe_legend(ax, fontsize=6, ncol=2)

    plt.tight_layout()
    out = output_path or 'Fig_V1_temperature_waterfall.pdf'
    savefig_with_edits(fig, out, dpi=SCI_DPI)
    plt.close(fig)
    _save_series_waterfall_document(
        out,
        temperatures,
        q_list,
        I_list,
        indices=indices,
        condition_axis="temperature_C",
        function_name="fig_v1_temperature_waterfall",
    )
    return out


def fig_v2_temperature_parameters(
    temperatures: np.ndarray,
    L_array: np.ndarray,
    lc_array: np.ndarray,
    Q_star_array: Optional[np.ndarray] = None,
    Xc_array: Optional[np.ndarray] = None,
    Tm_values: Optional[Dict] = None,
    output_path: Optional[str] = None,
    figsize: str = 'double_col_2x2',
) -> str:
    """Fig-V2: Structure parameter evolution with temperature. P1 priority.

    Four panels: L(T), lc(T), Q*(T), Xc(T).
    """
    set_sci_style()
    fig, axes = plt.subplots(2, 2, figsize=FIG_SIZES.get(figsize, FIG_SIZES['double_col_2x2']))

    # (a) Long period
    ax = axes[0, 0]
    ax.plot(temperatures, L_array, 'o-', color=COLOR_SCHEMES['main'], markersize=3, linewidth=1.0)
    ax.set_xlabel('Temperature (C)')
    ax.set_ylabel(r'$L$ (nm)')
    ax.set_title('(a) Long Period')

    # (b) Lamellar thickness
    ax = axes[0, 1]
    ax.plot(temperatures, lc_array, 'o-', color=COLOR_SCHEMES['secondary'], markersize=3, linewidth=1.0,
            label=r'$l_c$')
    if L_array is not None and lc_array is not None:
        la = L_array - lc_array
        ax.plot(temperatures, la, 's--', color=COLOR_SCHEMES['tertiary'], markersize=2,
                linewidth=0.8, label=r'$l_a$')
    ax.set_xlabel('Temperature (C)')
    ax.set_ylabel('Thickness (nm)')
    ax.set_title('(b) Lamellar Thickness')
    _safe_legend(ax, fontsize=7)

    # (c) Invariant Q*
    ax = axes[1, 0]
    if Q_star_array is not None:
        ax.plot(temperatures, Q_star_array, 'o-', color=COLOR_SCHEMES['highlight'],
                markersize=3, linewidth=1.0)
    ax.set_xlabel('Temperature (C)')
    ax.set_ylabel(r'$Q^*$ (a.u.)')
    ax.set_title('(c) Scattering Invariant')

    # (d) Relative crystallinity
    ax = axes[1, 1]
    if Xc_array is not None:
        ax.plot(temperatures, Xc_array, 'o-', color=COLOR_SCHEMES['tertiary'],
                markersize=3, linewidth=1.0)
        # Mark melting range
        if Tm_values:
            for key, T_val in Tm_values.items():
                if np.isfinite(T_val):
                    ax.axvline(T_val, linestyle='--', linewidth=0.5, alpha=0.5)
    ax.set_xlabel('Temperature (C)')
    ax.set_ylabel(r'$X_c$ (rel.)')
    ax.set_title('(d) Relative Crystallinity')

    # Melting zone shading for all panels
    if Tm_values:
        T_onset = Tm_values.get('Tm_onset_C', np.nan)
        T_end = Tm_values.get('Tm_end_C', np.nan)
        if np.isfinite(T_onset) and np.isfinite(T_end):
            for ax_row in axes:
                for ax in ax_row:
                    ax.axvspan(T_onset, T_end, alpha=0.08, color=COLOR_SCHEMES['secondary'])

    plt.tight_layout()
    out = output_path or 'Fig_V2_temperature_params.pdf'
    savefig_with_edits(fig, out, dpi=SCI_DPI)
    plt.close(fig)
    _save_v2_temperature_parameters_document(
        out,
        temperatures,
        L_array,
        lc_array,
        Q_star_array=Q_star_array,
        Xc_array=Xc_array,
        Tm_values=Tm_values,
    )
    return out


def fig_v3_scattering_heatmap(
    q: np.ndarray,
    temperatures: np.ndarray,
    I_matrix: np.ndarray,  # shape (n_T, n_q)
    q_star_array: Optional[np.ndarray] = None,
    output_path: Optional[str] = None,
    figsize: str = 'double_col_hmap',
    beamstop_q_min: float = 0.0,
) -> str:
    """Fig-V3: Scattering intensity heatmap vs temperature. P2 priority.

    Overlay Bragg peak position if available.
    When beamstop_q_min > 0, the region q < beamstop_q_min is greyed out
    with a hatch pattern to indicate beamstop/direct-beam contamination.
    """
    set_sci_style()
    fig, ax = plt.subplots(figsize=FIG_SIZES.get(figsize, FIG_SIZES['double_col_hmap']))

    # Mask beamstop-contaminated region: replace with NaN for pcolormesh
    I_data = np.log10(I_matrix + 1e-12)
    if beamstop_q_min > 0:
        q_mask = q >= beamstop_q_min
        if np.sum(q_mask) > 5:
            q_plot = q[q_mask]
            I_data = I_data[:, q_mask]
        else:
            q_plot = q
    else:
        q_plot = q

    # 2D heatmap
    im = ax.pcolormesh(q_plot, temperatures, I_data,
                        cmap=COLOR_SCHEMES['heatmap'], shading='auto', rasterized=True)

    # Grey-out bar for contaminated region
    if beamstop_q_min > 0 and beamstop_q_min > q[0]:
        ax.axvspan(q[0], beamstop_q_min, color='grey', alpha=0.25, hatch='///', linewidth=0)
        ax.annotate(f'Beamstop\nq<{beamstop_q_min:.3f}', xy=(q[0] * 1.1, temperatures[-1] * 0.95),
                    fontsize=5, color='grey', alpha=0.8, va='top')

    # Overlay q* line
    if q_star_array is not None and np.any(np.isfinite(q_star_array)):
        valid = np.isfinite(q_star_array)
        if np.sum(valid) > 2:
            ax.plot(q_star_array[valid], temperatures[valid], 'w--', linewidth=0.8, alpha=0.7)

    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label(r'$\log_{10} I(q)$', fontsize=8)

    ax.set_xlabel(r'$q$ (nm$^{-1}$)')
    ax.set_ylabel(r'Temperature ($^\circ$C)')
    pass

    plt.tight_layout()
    out = output_path or 'Fig_V3_heatmap.pdf'
    savefig_with_edits(fig, out, dpi=SCI_DPI)
    plt.close(fig)
    _save_v3_heatmap_document(
        out,
        q,
        temperatures,
        I_matrix,
        q_star_array=q_star_array,
        beamstop_q_min=beamstop_q_min,
    )
    return out


def fig_v4_avrami(
    times: np.ndarray,
    Xc_array: np.ndarray,
    avrami_result: Optional[Dict] = None,
    output_path: Optional[str] = None,
    figsize: str = 'double_col',
) -> str:
    """Fig-V4: Avrami crystallization kinetics. P2 priority.

    Dual panel: Xc(t) + Avrami plot ln(-ln(1-Xc)) vs ln(t).
    """
    set_sci_style()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=FIG_SIZES.get(figsize, FIG_SIZES['double_col']))

    # Left: Xc vs t
    ax1.plot(times, Xc_array, 'o-', color=COLOR_SCHEMES['main'], markersize=3, linewidth=1.0)
    if avrami_result and avrami_result.get('valid'):
        t_half = avrami_result.get('t_half_s', np.nan)
        if np.isfinite(t_half):
            ax1.axvline(t_half, color=COLOR_SCHEMES['secondary'], linestyle='--',
                        linewidth=0.8, label=f'$t_{{1/2}}$={t_half:.0f} s')
            ax1.axhline(0.5, color='grey', linestyle=':', linewidth=0.5)
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel(r'$X_c$ (rel.)')
    ax1.set_title('Crystallization Kinetics')
    _safe_legend(ax1, fontsize=7)

    # Right: Avrami plot
    mask = (Xc_array > 0.01) & (Xc_array < 0.99) & (times > 0)
    if np.sum(mask) > 3:
        y = np.log(-np.log(1 - Xc_array[mask]))
        x = np.log(times[mask])
        ax2.scatter(x, y, s=10, color=COLOR_SCHEMES['main'], alpha=0.7)

        if avrami_result and avrami_result.get('valid'):
            n = avrami_result.get('n', np.nan)
            ln_k = np.log(avrami_result.get('k_sn', np.nan)) if np.isfinite(avrami_result.get('k_sn', np.nan)) else np.nan
            x_fit = np.linspace(np.min(x), np.max(x), 50)
            ax2.plot(x_fit, ln_k + n * x_fit, color=COLOR_SCHEMES['secondary'],
                     linewidth=1.0, label=f'$n$={n:.2f}')
            _safe_legend(ax2, fontsize=7)

    ax2.set_xlabel(r'$\ln(t)$')
    ax2.set_ylabel(r'$\ln(-\ln(1-X_c))$')
    ax2.set_title('Avrami Plot')

    plt.tight_layout()
    out = output_path or 'Fig_V4_avrami.pdf'
    savefig_with_edits(fig, out, dpi=SCI_DPI)
    plt.close(fig)
    _save_v4_avrami_document(out, times, Xc_array, avrami_result=avrami_result)
    return out


def fig_guinier(
    q: np.ndarray, I: np.ndarray,
    Rg: Optional[float] = None,
    q_min: float = 0.04, q_max: float = 0.15,
    output_path: Optional[str] = None,
    figsize: str = 'single_col',
) -> str:
    """Guinier plot: ln(I) vs q^2 for Rg determination."""
    set_sci_style()
    fig, ax = plt.subplots(figsize=FIG_SIZES.get(figsize, FIG_SIZES['single_col']))

    mask = (q >= q_min) & (q <= q_max)
    q_sel = q[mask]
    I_sel = I[mask]
    pos = I_sel > 0

    if np.sum(pos) > 4:
        ax.scatter(q_sel[pos]**2, np.log(I_sel[pos]), s=8, color=COLOR_SCHEMES['main'], alpha=0.7)
        p = np.polyfit(q_sel[pos]**2, np.log(I_sel[pos]), 1)
        q2_fit = np.linspace(np.min(q_sel**2), np.max(q_sel**2), 50)
        ax.plot(q2_fit, np.polyval(p, q2_fit), color=COLOR_SCHEMES['secondary'],
                linewidth=1.0, label=f'$R_g$={Rg:.1f} nm' if Rg else '')

    ax.set_xlabel(r'$q^2$ (nm$^{-2}$)')
    ax.set_ylabel(r'$\ln I(q)$')
    pass
    _safe_legend(ax, fontsize=7)

    plt.tight_layout()
    out = output_path or 'Fig_SI_Guinier.pdf'
    savefig_with_edits(fig, out, dpi=SCI_DPI)
    plt.close(fig)
    _save_phase3_guinier_bundle(out, q, I, Rg=Rg, q_min=q_min, q_max=q_max)
    return out


def fig_kratky(
    q: np.ndarray, I: np.ndarray,
    L: Optional[float] = None,
    output_path: Optional[str] = None,
    figsize: str = 'single_col',
) -> str:
    """Kratky plot: q^2*I vs q for chain conformation assessment."""
    set_sci_style()
    fig, ax = plt.subplots(figsize=FIG_SIZES.get(figsize, FIG_SIZES['single_col']))

    ax.plot(q, I * q**2, color=COLOR_SCHEMES['main'], linewidth=1.0)
    if L is not None and np.isfinite(L) and L > 0:
        q_star = 2 * np.pi / L
        ax.axvline(q_star, color=COLOR_SCHEMES['secondary'], linestyle='--',
                    linewidth=0.8, alpha=0.7)

    ax.set_xlabel(r'$q$ (nm$^{-1}$)')
    ax.set_ylabel(r'$I(q) \cdot q^2$ (a.u.)')
    pass

    plt.tight_layout()
    out = output_path or 'Fig_SI_Kratky.pdf'
    savefig_with_edits(fig, out, dpi=SCI_DPI)
    plt.close(fig)
    _save_phase3_kratky_bundle(out, q, I, L=L)
    return out


# ======================================================================
#  Multi-technique cross-validation figure
# ======================================================================

def fig_joint_crystallinity(
    saxs_phi_c: float,
    waxs_phi_c: Optional[float] = None,
    dsc_phi_c: Optional[float] = None,
    output_path: Optional[str] = None,
    figsize: str = 'single_col',
) -> str:
    """Joint crystallinity cross-validation bar chart."""
    set_sci_style()
    fig, ax = plt.subplots(figsize=FIG_SIZES.get(figsize, FIG_SIZES['single_col']))

    techniques = ['SAXS']
    values = [saxs_phi_c]
    colors = [COLOR_SCHEMES['main']]

    if waxs_phi_c is not None and np.isfinite(waxs_phi_c):
        techniques.append('WAXS')
        values.append(waxs_phi_c)
        colors.append(COLOR_SCHEMES['secondary'])
    if dsc_phi_c is not None and np.isfinite(dsc_phi_c):
        techniques.append('DSC')
        values.append(dsc_phi_c)
        colors.append(COLOR_SCHEMES['tertiary'])

    bars = ax.bar(techniques, values, color=colors, width=0.5, alpha=0.85)
    
    # Add value labels
    # phi_c is stored as a fraction (0-1); display as percentage
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f'{val*100:.1f}%', ha='center', va='bottom', fontsize=8)

    ax.set_ylabel(r'Crystallinity $\phi_c$')
    pass
    ax.set_ylim(0, max(values) * 1.2 if values else 1)

    plt.tight_layout()
    out = output_path or 'Fig_Joint_crystallinity.pdf'
    savefig_with_edits(fig, out, dpi=SCI_DPI)
    plt.close(fig)
    _save_joint_crystallinity_document(out, techniques, values)
    return out


# ============================================================================
#  Unified figure generator (for BaseEngine interface)
# ============================================================================

def fig_static_overview(
    labels: list, q_list: list, I_list: list,
    L_list: list, lc_list: list, Xc_list: list,
    Q_rel_list: list = None,
    output_path: str = None,
) -> str:
    """Static SAXS overview: multi-sample comparison (SCI composite).

    4-panel: (A) I(q) overlay, (B) I*q^2 lamellar peak,
             (C) L bar chart, (D) lc/Xc/Q* bar chart.
    """
    set_sci_style()
    fig, axes = plt.subplots(2, 2, figsize=(8, 7))

    n = len(labels)
    colors = plt.cm.tab10(np.linspace(0, 1, max(n, 3)))[:n]

    # Panel A: I(q) log-log overlay
    ax = axes[0, 0]
    for i in range(n):
        ax.loglog(q_list[i], I_list[i], color=colors[i], linewidth=0.8, label=labels[i])
    ax.set_xlabel(r'$q$ (nm$^{-1}$)')
    ax.set_ylabel(r'$I(q)$ (a.u.)')
    ax.set_title('A: Scattering Profiles')
    _safe_legend(ax, fontsize=6, ncol=2)

    # Panel B: I*q^2 zoom on lamellar peak
    ax = axes[0, 1]
    for i in range(n):
        Iq2 = I_list[i] * q_list[i]**2
        ax.plot(q_list[i], Iq2, color=colors[i], linewidth=0.8)
    ax.set_xlim(0.2, 1.2)
    ax.set_xlabel(r'$q$ (nm$^{-1}$)')
    ax.set_ylabel(r'$I(q)\cdot q^2$ (a.u.)')
    ax.set_title('B: Lorentz-corrected (Lamellar Peak)')

    # Panel C: L bar chart
    ax = axes[1, 0]
    bars = ax.bar(range(n), [L or 0 for L in L_list], color=colors, edgecolor='white')
    ax.set_xticks(range(n))
    ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=7)
    ax.set_ylabel('$L$ (nm)')
    ax.set_title('C: Long Period')

    # Panel D: lc, Xc, Q*_rel
    ax = axes[1, 1]
    x = np.arange(n)
    w = 0.25
    ax.bar(x - w, [lc or 0 for lc in lc_list], w, label='$l_c$ (nm)', color='steelblue')
    ax_twin = ax.twinx()
    ax_twin.plot(x, [Xc or 0 for Xc in Xc_list], 'o-', color='firebrick', linewidth=1.2, markersize=6, label='$X_c$')
    if Q_rel_list:
        ax_twin.plot(x, Q_rel_list, 's--', color='darkorange', linewidth=1, markersize=5, label=r'$Q^*_{rel}$')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=7)
    ax.set_ylabel('$l_c$ (nm)')
    ax_twin.set_ylabel('$X_c$ / $Q^*_{rel}$')
    ax.set_title('D: Crystallinity')
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax_twin.get_legend_handles_labels()
    _safe_legend(ax_twin, lines1 + lines2, labels1 + labels2, fontsize=6, loc='upper right')

    plt.tight_layout()
    out = output_path or 'Fig_Static_Overview.pdf'
    savefig_with_edits(fig, out, dpi=SCI_DPI)
    plt.close(fig)
    _save_static_overview_document(
        out,
        labels,
        q_list,
        I_list,
        L_list,
        lc_list,
        Xc_list,
        Q_rel_list=Q_rel_list,
    )
    return out


def fig_temperature_overview(
    temps: np.ndarray, q_list: list, I_list: list,
    L_arr: np.ndarray, lc_arr: np.ndarray, Xc_arr: np.ndarray,
    Q_arr: np.ndarray = None, output_path: str = None,
) -> str:
    """Temperature SAXS overview: 4-panel SCI composite.

    (A) Waterfall, (B) L & lc(T), (C) Xc(T), (D) Heatmap.
    """
    set_sci_style()
    fig, axes = plt.subplots(2, 2, figsize=(8, 7))
    n = len(temps)
    colors = plt.cm.plasma(np.linspace(0.1, 0.9, n))

    # Panel A: Waterfall I*q^2
    ax = axes[0, 0]
    offset = 0
    for i in range(n):
        Iq2 = I_list[i] * q_list[i]**2
        ax.plot(q_list[i], Iq2 + offset*0.3, color=colors[i], linewidth=0.6)
        offset += np.max(Iq2[(q_list[i]>=0.2)&(q_list[i]<=1.2)]) * 0.4
    ax.set_xlim(0.2, 1.2)
    ax.set_xlabel(r'$q$ (nm$^{-1}$)')
    ax.set_ylabel(r'$I\cdot q^2$ offset')
    ax.set_title(f'A: Lamellar Peak Evolution ($n$={n})')

    # Panel B: L & lc vs T
    ax = axes[0, 1]
    valid_L = np.isfinite(L_arr)
    valid_lc = np.isfinite(lc_arr)
    ax.plot(temps[valid_L], L_arr[valid_L], 'o-', color='steelblue', linewidth=1.2, markersize=5, label='$L$')
    ax.plot(temps[valid_lc], lc_arr[valid_lc], 's--', color='firebrick', linewidth=1, markersize=5, label='$l_c$')
    ax.set_xlabel('Temperature (鎺矯)')
    ax.set_ylabel('Thickness (nm)')
    ax.set_title('B: Long Period & Crystal Thickness')
    _safe_legend(ax, fontsize=7)

    # Panel C: Xc vs T
    ax = axes[1, 0]
    valid_Xc = np.isfinite(Xc_arr)
    ax.plot(temps[valid_Xc], Xc_arr[valid_Xc], 'o-', color='darkgreen', linewidth=1.5, markersize=6)
    ax.fill_between(temps[valid_Xc], 0, Xc_arr[valid_Xc], alpha=0.15, color='darkgreen')
    ax.set_xlabel('Temperature (鎺矯)')
    ax.set_ylabel(r'$X_c$ (SAXS)')
    ax.set_title('C: Crystallinity')

    # Panel D: Heatmap
    ax = axes[1, 1]
    if Q_arr is not None:
        ax.plot(temps[np.isfinite(Q_arr)], Q_arr[np.isfinite(Q_arr)] / np.nanmax(Q_arr),
                'o-', color='purple', linewidth=1.2, markersize=5)
        ax.set_ylabel(r'$Q^*_{rel}$')
        ax.set_title('D: Invariant $Q^*$')
    else:
        # Show I*q^2 heatmap approximation
        q0 = q_list[0]
        I_mat = np.zeros((n, len(q0)))
        for i in range(n):
            I_mat[i] = I_list[i] if len(I_list[i])==len(q0) else np.interp(q0, q_list[i], I_list[i])
        im = ax.pcolormesh(q0, temps, np.log1p(I_mat*q0**2), shading='auto', cmap='plasma')
        plt.colorbar(im, ax=ax, label=r'$\log(1+I\cdot q^2)$')
        ax.set_xlim(0.2, 1.5)
        ax.set_xlabel(r'$q$ (nm$^{-1}$)')
        ax.set_ylabel('T (鎺矯)')
        ax.set_title('D: Scattering Heatmap')

    plt.tight_layout()
    out = output_path or 'Fig_Temperature_Overview.pdf'
    savefig_with_edits(fig, out, dpi=SCI_DPI)
    plt.close(fig)
    _save_condition_overview_document(
        out,
        temps,
        q_list,
        I_list,
        condition_axis="temperature_C",
        function_name="fig_temperature_overview",
        L_arr=L_arr,
        lc_arr=lc_arr,
        Xc_arr=Xc_arr,
        Q_arr=Q_arr,
    )
    return out


def fig_strain_overview(
    strains: np.ndarray, q_list: list, I_list: list,
    L_arr: np.ndarray, lc_arr: np.ndarray, la_arr: np.ndarray,
    Xc_arr: np.ndarray, Q_arr: np.ndarray = None,
    Q_rel_arr: np.ndarray = None, output_path: str = None,
) -> str:
    """Strain SAXS overview: 4-panel SCI composite.

    (A) Waterfall, (B) L/lc/la vs strain, (C) Q*/Q*_rel vs strain, (D) Xc vs strain.
    """
    set_sci_style()
    fig, axes = plt.subplots(2, 2, figsize=(8, 7))
    n = len(strains)
    colors = plt.cm.viridis(np.linspace(0.1, 0.9, n))

    # Panel A: Waterfall
    ax = axes[0, 0]
    offset = 0
    for i in range(n):
        Iq2 = I_list[i] * q_list[i]**2
        ax.plot(q_list[i], Iq2 + offset*0.3, color=colors[i], linewidth=0.6)
        offset += np.max(Iq2[(q_list[i]>=0.2)&(q_list[i]<=1.2)]) * 0.4
    ax.set_xlim(0.2, 1.5)
    ax.set_xlabel(r'$q$ (nm$^{-1}$)')
    ax.set_ylabel(r'$I\cdot q^2$ offset')
    ax.set_title(f'A: Lamellar Peak Evolution')

    # Panel B: L, lc, la vs strain
    ax = axes[0, 1]
    for arr, label, color, style in [
        (L_arr, '$L$', 'steelblue', 'o-'),
        (la_arr, '$l_a$', 'darkorange', 's--'),
        (lc_arr, '$l_c$', 'firebrick', '^:'),
    ]:
        valid = np.isfinite(arr)
        if np.any(valid):
            ax.plot(strains[valid], arr[valid], style, color=color, linewidth=1.2, markersize=5, label=label)
    ax.set_xlabel('Strain (%)')
    ax.set_ylabel('Thickness (nm)')
    ax.set_title('B: Structure Parameters')
    _safe_legend(ax, fontsize=7)

    # Panel C: Q* and Q*_rel
    ax = axes[1, 0]
    if Q_arr is not None and np.any(np.isfinite(Q_arr)):
        valid = np.isfinite(Q_arr)
        ax.bar(strains[valid], Q_arr[valid], width=max(strains)*0.04, color='steelblue', alpha=0.6, label='$Q^*$')
    if Q_rel_arr is not None and np.any(np.isfinite(Q_rel_arr)):
        ax_twin = ax.twinx()
        valid_r = np.isfinite(Q_rel_arr)
        ax_twin.plot(strains[valid_r], Q_rel_arr[valid_r], 'o-', color='firebrick', linewidth=1.5, markersize=6, label=r'$Q^*_{rel}$')
        ax_twin.set_ylabel(r'$Q^*_{rel}$')
        _safe_legend(ax_twin, fontsize=7, loc='upper right')
    ax.set_xlabel('Strain (%)')
    ax.set_ylabel('$Q^*$')
    ax.set_title('C: Scattering Invariant')
    _safe_legend(ax, fontsize=7, loc='upper left')

    # Panel D: Xc vs strain
    ax = axes[1, 1]
    valid = np.isfinite(Xc_arr)
    ax.plot(strains[valid], Xc_arr[valid], 'o-', color='darkgreen', linewidth=1.5, markersize=6)
    ax.fill_between(strains[valid], 0, Xc_arr[valid], alpha=0.15, color='darkgreen')
    ax.set_xlabel('Strain (%)')
    ax.set_ylabel(r'$X_c$ (SAXS)')
    ax.set_title('D: Crystallinity')
    ax.set_ylim(bottom=0)

    plt.tight_layout()
    out = output_path or 'Fig_Strain_Overview.pdf'
    savefig_with_edits(fig, out, dpi=SCI_DPI)
    plt.close(fig)
    _save_condition_overview_document(
        out,
        strains,
        q_list,
        I_list,
        condition_axis="strain_pct",
        function_name="fig_strain_overview",
        L_arr=L_arr,
        lc_arr=lc_arr,
        Xc_arr=Xc_arr,
        la_arr=la_arr,
        Q_arr=Q_arr,
        Q_rel_arr=Q_rel_arr,
    )
    return out


def generate_all_figures(results, output_dir, config=None):
    """Generate all standard SAXS figures and CSV exports for the given results.

    Parameters
    ----------
    results : SAXSResult or list of SAXSResult
    output_dir : str
    config : SAXSConfig, optional
    """
    import os as _os

    if not isinstance(results, (list, tuple)):
        results = [results]

    root = Path(output_dir).resolve()
    figs_dir = root / 'summary'
    data_dir = root / 'data' / 'parameters'
    _os.makedirs(figs_dir, exist_ok=True)
    _os.makedirs(data_dir, exist_ok=True)

    set_sci_style()
    figures = {}
    all_params = []  # accumulate parameter dicts for batch CSV

    is_batch = len(results) > 1
    series_kind = ""
    if config is not None:
        experiment_type = str(getattr(config, "experiment_type", "") or "").strip().lower()
        condition_label = str(getattr(config, "condition_label", "") or "").strip().lower()
        if experiment_type in {"temperature", "cooling", "isothermal"} or "temperature" in condition_label:
            series_kind = "temperature"
        elif experiment_type == "strain" or "strain" in condition_label:
            series_kind = "strain"
    if not series_kind and is_batch:
        finite_conditions = np.array([r.condition_value for r in results if np.isfinite(r.condition_value)], dtype=float)
        if finite_conditions.size >= 2:
            condition_span = float(np.max(finite_conditions) - np.min(finite_conditions))
            if condition_span >= 50:
                series_kind = "temperature"
            elif np.any(finite_conditions >= 100):
                series_kind = "strain"

    for i, result in enumerate(results):
        if result.q is None or result.I is None:
            continue
        # Per-frame directory: T{temp}C / S{strain}pct / frame_NNN
        if result.label:
            frame_label = result.label.replace(" ", "_").replace("/", "_")
        elif np.isfinite(result.condition_value):
            cond = result.condition_value
            # Detect if all conditions are identical (e.g., static samples)
            all_conds = [r.condition_value for r in results if np.isfinite(r.condition_value)]
            all_same = len(set(round(c, 0) for c in all_conds)) <= 1 if all_conds else True
            if not all_same:
                frame_label = f"T{cond:.0f}C" if cond > 50 else f"S{cond:.0f}pct"
            else:
                frame_label = f"frame_{i:03d}"
        else:
            frame_label = f"frame_{i:03d}"

        # Per-frame output: per_frame/{label}/NN_description.pdf
        frame_dir = root / 'per_frame' / frame_label
        _os.makedirs(frame_dir, exist_ok=True)

        # Low-confidence flag: triggered by lc_confidence < 0.40 OR
        # quality_flag contains any WARN/ERROR about qstar/sasmodels/low_snr.
        sp = result.structure
        qf = getattr(result, 'quality_flag', '') or ''
        is_low_conf = (sp and np.isfinite(sp.confidence_lc) and sp.confidence_lc < 0.40)
        has_qf_warn = bool(qf) and qf != 'OK'
        is_low = is_low_conf or has_qf_warn
        low_suffix = "_LOW" if is_low else ""

        q = result.q
        I = result.I_smooth if result.I_smooth is not None else result.I

        # Common derived values
        lp = result.long_period
        L_best = lp.L_best if lp and np.isfinite(lp.L_best) else None
        q_star = 2 * np.pi / L_best if L_best and L_best > 0 else None

        # ----------------------------------------------------------------
        # Fig-U1: 1D scattering profile
        # ----------------------------------------------------------------
        try:
            p = str(frame_dir / f"01_scattering_profile.pdf")
            fig_u1_scattering_profile(q, I, q_star=q_star, L=L_best,
                                       label=result.label, output_path=p,
                                       is_low_conf=is_low)
            figures[f"{frame_label}/01_scattering"] = p
        except Exception:
            logger.warning("SAXS scattering profile figure generation failed.", exc_info=True)

        # ----------------------------------------------------------------
        # Fig-U2: Correlation function
        # ----------------------------------------------------------------
        try:
            corr = result.correlation
            if corr and corr.get('r') is not None and len(corr['r']) > 5:
                p = str(frame_dir / f"02_correlation_function{low_suffix}.pdf")
                _remove_stale_variant(Path(p))
                fig_u2_correlation_function(corr['r'], corr['gamma'],
                                             L=(sp.L if sp else None),
                                             lc=(sp.lc if sp else None),
                                             output_path=p,
                                             is_low_conf=is_low)
                figures[f"{frame_label}/02_correlation"] = p
        except Exception:
            logger.warning("SAXS correlation figure generation failed.", exc_info=True)

        # ----------------------------------------------------------------
        # Fig-U3: IDF
        # ----------------------------------------------------------------
        try:
            idf_data = result.idf
            if idf_data and idf_data.get('r_idf') is not None and len(idf_data['r_idf']) > 5:
                p = str(frame_dir / f"03_IDF{low_suffix}.pdf")
                _remove_stale_variant(Path(p))
                fig_u3_idf(idf_data['r_idf'], idf_data['idf'],
                            L_idf=idf_data.get('L_idf'),
                            lc_idf=idf_data.get('lc_idf'),
                            output_path=p,
                            is_low_conf=is_low)
                figures[f"{frame_label}/03_IDF"] = p
        except Exception:
            logger.warning("SAXS IDF figure generation failed.", exc_info=True)

        # ----------------------------------------------------------------
        # Fig-U4: Porod
        # ----------------------------------------------------------------
        try:
            porod_data = result.porod
            if porod_data and porod_data.get('q_porod') is not None:
                p = str(frame_dir / f"04_porod_analysis{low_suffix}.pdf")
                _remove_stale_variant(Path(p))
                fig_u4_porod(porod_data['q_porod'], porod_data.get('Iq4', porod_data['q_porod']**0),
                              slope=porod_data.get('slope'),
                              Kp=porod_data.get('Kp'),
                              output_path=p,
                              is_low_conf=is_low)
                figures[f"{frame_label}/04_porod"] = p
        except Exception:
            logger.warning("SAXS Porod figure generation failed.", exc_info=True)

        # ----------------------------------------------------------------
        # Guinier
        # ----------------------------------------------------------------
        try:
            Rg = sp.Rg if sp and np.isfinite(sp.Rg) else None
            p = str(frame_dir / f"05_guinier_plot.pdf")
            fig_guinier(q, I, Rg=Rg, output_path=p)
            figures[f"{frame_label}/05_guinier"] = p
        except Exception:
            logger.warning("SAXS Guinier figure generation failed.", exc_info=True)

        # ----------------------------------------------------------------
        # Kratky
        # ----------------------------------------------------------------
        try:
            p = str(frame_dir / f"06_kratky_plot.pdf")
            fig_kratky(q, I, L=L_best, output_path=p)
            figures[f"{frame_label}/06_kratky"] = p
        except Exception:
            logger.warning("SAXS Kratky figure generation failed.", exc_info=True)

        # ----------------------------------------------------------------
        # 1D profile export
        # ----------------------------------------------------------------
        try:
            prefix = frame_label.replace(" ", "_").replace("/", "_").replace("\\", "_")
            p = export_1d_profile(result.q, result.I,
                                   str(root / 'data' / 'raw_1d'),
                                   f"{prefix}_1d_profile.csv",
                                   I_smooth=(result.I_smooth if result.I_smooth is not None else None))
            if p:
                figures[f"{frame_label}/1d_profile"] = p
        except Exception:
            logger.warning("SAXS 1D profile CSV export failed.", exc_info=True)

        # Accumulate parameters for batch CSV
        all_params.append(_result_to_params_dict(result))

    # ----------------------------------------------------------------
    # Batch CSV: one row per result
    # ----------------------------------------------------------------
    if all_params:
        try:
            import pandas as pd
            csv_path = str(data_dir / "saxs_parameters.csv")
            df = pd.DataFrame(all_params)
            df.to_csv(csv_path, index=False)
            figures["parameters_csv"] = csv_path
        except Exception:
            logger.warning("SAXS parameters CSV export failed.", exc_info=True)

    # ----------------------------------------------------------------
    # Temperature series figures (multi-frame with valid condition values)
    # ----------------------------------------------------------------
    if len(results) > 1 and series_kind == "temperature":
        sorted_results = sorted(
            [r for r in results if np.isfinite(r.condition_value)],
            key=lambda r: r.condition_value,
        )
        if len(sorted_results) >= 3:
            try:
                temps = np.array([r.condition_value for r in sorted_results])
                L_arr = np.array([r.structure.L if r.structure and np.isfinite(r.structure.L) else np.nan for r in sorted_results])
                lc_arr = np.array([_result_effective_lc_value(r) for r in sorted_results], dtype=float)

                # V1: Waterfall
                try:
                    q_list = [r.q for r in sorted_results]
                    I_list = [(r.I_smooth if r.I_smooth is not None else r.I) for r in sorted_results]
                    p = str(figs_dir / "Fig_2_waterfall.pdf")
                    fig_v1_temperature_waterfall(temps, q_list, I_list, output_path=p)
                    figures["Fig_2_waterfall"] = p
                except Exception:
                    logger.warning("SAXS temperature waterfall figure generation failed.", exc_info=True)

                # V2: Structure parameters vs temperature
                try:
                    Q_arr = np.array([r.structure.Q_invariant if r.structure and np.isfinite(r.structure.Q_invariant) else np.nan for r in sorted_results])
                    Xc_arr = np.array([r.structure.phi_c if r.structure and np.isfinite(r.structure.phi_c) else np.nan for r in sorted_results])
                    p = str(figs_dir / "Fig_3_structure_parameters.pdf")
                    fig_v2_temperature_parameters(temps, L_arr, lc_arr, Q_star_array=Q_arr, Xc_array=Xc_arr, output_path=p)
                    figures["Fig_3_structure_params"] = p
                except Exception:
                    logger.warning("SAXS temperature structure-parameters figure generation failed.", exc_info=True)

                # V3: Scattering heatmap
                try:
                    # Detect beamstop contamination across all sorted results
                    bsq_min = 0.0
                    for r in sorted_results:
                        if getattr(r, 'beam_stop_contaminated', False):
                            eff_q = getattr(r, 'effective_q_min', 0.0)
                            if eff_q > bsq_min:
                                bsq_min = eff_q
                    q_common = sorted_results[0].q
                    I_matrix = np.zeros((len(sorted_results), len(q_common)))
                    for i, r in enumerate(sorted_results):
                        I_use = r.I_smooth if r.I_smooth is not None else r.I
                        if len(I_use) == len(q_common):
                            I_matrix[i, :] = I_use
                        else:
                            I_matrix[i, :] = np.interp(q_common, r.q, I_use)
                    p = str(figs_dir / "Fig_4_heatmap.pdf")
                    fig_v3_scattering_heatmap(q_common, temps, I_matrix,
                                               output_path=p, beamstop_q_min=bsq_min)
                    figures["Fig_4_heatmap"] = p
                except Exception:
                    logger.warning("SAXS temperature heatmap figure generation failed.", exc_info=True)
            except Exception:
                logger.warning("SAXS temperature-series figure generation failed.", exc_info=True)

    # ----------------------------------------------------------------
    # Tensile series figures (multi-frame)
    # ----------------------------------------------------------------
    if len(results) > 1 and series_kind == "strain":
        sorted_strain = sorted(
            [r for r in results if np.isfinite(r.condition_value)],
            key=lambda r: r.condition_value,
        )
        if len(sorted_strain) >= 3:
            try:
                strains = np.array([r.condition_value for r in sorted_strain])
                L_arr = np.array([r.structure.L if r.structure and np.isfinite(r.structure.L) else np.nan for r in sorted_strain])
                lc_arr = np.array([r.structure.lc if r.structure and np.isfinite(r.structure.lc) else np.nan for r in sorted_strain])
                Q_arr = np.array([r.structure.Q_invariant if r.structure and np.isfinite(r.structure.Q_invariant) else np.nan for r in sorted_strain])
                Xc_arr = np.array([r.structure.phi_c if r.structure and np.isfinite(r.structure.phi_c) else np.nan for r in sorted_strain])

                # T2: Strain waterfall
                try:
                    q_list_s = [r.q for r in sorted_strain]
                    I_list_s = [(r.I_smooth if r.I_smooth is not None else r.I) for r in sorted_strain]
                    p = str(figs_dir / "Fig_2_waterfall.pdf")
                    fig_t2_scattering_waterfall(strains, q_list_s, I_list_s, output_path=p)
                    figures["Fig_2_waterfall"] = p
                except Exception:
                    logger.warning("SAXS strain waterfall figure generation failed.", exc_info=True)

                # T3: Structure evolution
                try:
                    p = str(figs_dir / "Fig_3_structure_parameters.pdf")
                    fig_t3_structure_evolution(strains, L_arr, lc_arr,
                                                phi_c_array=Xc_arr,
                                                Q_star_array=Q_arr,
                                                output_path=p)
                    figures["Fig_3_structure_params"] = p
                except Exception:
                    logger.warning("SAXS strain structure-parameters figure generation failed.", exc_info=True)

                # T4: Invariant conservation
                try:
                    p = str(figs_dir / "Fig_S1_invariant.pdf")
                    fig_t4_invariant_conservation(strains, Q_arr, output_path=p)
                    figures["Fig_S1_invariant"] = p
                except Exception:
                    logger.warning("SAXS strain invariant figure generation failed.", exc_info=True)
            except Exception:
                logger.warning("SAXS strain-series figure generation failed.", exc_info=True)

    # 閳光偓閳光偓 Overview composite figures 閳光偓閳光偓
    if len(results) > 1:
        sorted_all = sorted(
            [r for r in results if np.isfinite(r.condition_value)],
            key=lambda r: r.condition_value,
        )
        if len(sorted_all) >= 2:
            labels = [r.label or f"#{i}" for i, r in enumerate(sorted_all)]
            q_list = [r.q for r in sorted_all]
            I_list = [(r.I_smooth if r.I_smooth is not None else r.I) for r in sorted_all]
            L_list = [r.structure.L if r.structure and np.isfinite(r.structure.L) else None for r in sorted_all]
            lc_list = [value if np.isfinite(value) else None for value in (_result_effective_lc_value(r) for r in sorted_all)]
            Xc_list = [r.structure.phi_c if r.structure and np.isfinite(r.structure.phi_c) else None for r in sorted_all]
            Q_list = [r.structure.Q_invariant if r.structure and np.isfinite(r.structure.Q_invariant) else None for r in sorted_all]
            la_list = [r.structure.la if r.structure and np.isfinite(r.structure.la) else None for r in sorted_all]
            cond_vals = np.array([r.condition_value for r in sorted_all])
            Q_arr = np.array(Q_list)
            Q_rel = Q_arr / Q_arr[0] if Q_arr[0] and Q_arr[0] > 0 else None

            try:
                p = str(figs_dir / "Fig_1_overview.pdf")
                if series_kind == "temperature":
                    fig_temperature_overview(cond_vals, q_list, I_list,
                        np.array(L_list), np.array(lc_list), np.array(Xc_list),
                        Q_arr=Q_arr, output_path=p)
                elif series_kind == "strain":
                    fig_strain_overview(cond_vals, q_list, I_list,
                        np.array(L_list), np.array(lc_list), np.array(la_list),
                        np.array(Xc_list), Q_arr=Q_arr, Q_rel_arr=Q_rel,
                        output_path=p)
                else:
                    labels_short = [lbl[:15] for lbl in labels]
                    fig_static_overview(labels_short, q_list, I_list,
                        L_list, lc_list, Xc_list, Q_rel_list=Q_rel.tolist() if Q_rel is not None else None,
                        output_path=p)
                figures["Fig_1_overview"] = p
            except Exception:
                logger.warning("SAXS static overview figure generation failed.", exc_info=True)

    return figures
