"""Legacy DSC figure helpers, disabled from formal production rendering.

Import this module explicitly only for legacy recovery or tests. Production
figures are published by the shared FigureDefinition pipeline.
"""

import logging
logger = logging.getLogger(__name__)

import csv
import os
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter, MultipleLocator
from typing import Dict, List, Optional, Tuple, Any

from .core import DSCResult
from .dsc_kinetics import AvramiResult, NonIsothermalResult
from .config import DSCConfig
from ..figure_document import save_generated_figure_document
from ..plot_edits import savefig_with_edits
from ...plotting.sci_style import (
    set_sci_style as _global_set_sci_style,
    apply_axis_sci_style,
    apply_panel_label as _panel,
    WONG_COLORS, ANNOTATION_COLORS,
    FIG_SIZES, AXIS_LABELS,
    save_figure_sci,
)



# ---------------------------------------------------------------------------
#  Global style (SCI paper ready)
# ---------------------------------------------------------------------------

SCI_COLORS = {
    'blue':   WONG_COLORS[5],  # '#0072B2'
    'red':    WONG_COLORS[6],  # '#D55E00'
    'green':  WONG_COLORS[3],  # '#009E73'
    'orange': WONG_COLORS[1],  # '#E69F00'
    'purple': WONG_COLORS[7],  # '#CC79A7'
    'cyan':   '#00A896',
    'grey':   '#666666',
    'dark':   '#222222',
}

SCI_PALETTE = [WONG_COLORS[i] for i in (5, 6, 3, 1, 7)]


def set_sci_style(fig, ax, xlabel='', ylabel='', title='',
                  fontsize: int = 10):
    """Apply consistent SCI paper style — delegates to central sci_style."""
    _global_set_sci_style(font_size=fontsize - 1)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=fontsize)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=fontsize)
    if title:
        ax.set_title(title, fontsize=fontsize + 1, fontweight='bold')
    ax.tick_params(labelsize=fontsize - 1, direction='in', top=True, right=True)
    for spine in ax.spines.values():
        spine.set_linewidth(0.8)
        spine.set_color('#333333')
    ax.grid(True, alpha=0.2, linestyle='--', linewidth=0.5)


def _make_output_dirs(output_dir: str) -> Tuple[str, str]:
    """Create figures and data directories."""
    fig_dir = os.path.join(output_dir, 'figures')
    data_dir = os.path.join(output_dir, 'data')
    os.makedirs(fig_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)
    return fig_dir, data_dir


def _save_figure(fig, name: str, fig_dir: str, fmt: str = 'svg', dpi: int = 300):
    """Save figure — uses central SCI spec + plot_edits integration."""
    path = os.path.join(fig_dir, f'{name}.{fmt}')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    savefig_with_edits(fig, path, dpi=dpi, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
    plt.close(fig)
    return path


def _save_d1_full_curve_document(path: str, result: DSCResult, figure_id: str) -> None:
    figure_id = Path(path).stem
    data_path = _write_d1_full_curve_data(path, result)
    data_ref = "dsc-full-curve-data"
    t_max = float(np.max(result.T)) if len(result.T) else 0.0
    hf_max = float(np.max(result.HF)) if len(result.HF) else 0.0
    objects = [
        {
            "id": "series-heat-flow",
            "type": "plot_series",
            "name": "Heat Flow",
            "data_ref": data_ref,
            "x_column": "temperature_C",
            "y_column": "heat_flow_W_g",
            "style": {"color": SCI_COLORS["blue"], "line_width": 1.2},
        }
    ]
    event_specs = [
        ("Tg", result.Tg_C, SCI_COLORS["red"], "--", 10, 10),
        ("Tm", result.Tm_peak_C, SCI_COLORS["green"], "--", 10, -15),
        ("Tm2", result.Tm2_peak_C, SCI_COLORS["cyan"], "-.", 10, -25),
        ("Tc", result.Tc_peak_C, SCI_COLORS["green"], "--", 10, -15),
        ("Tcc", result.Tcc_peak_C, SCI_COLORS["orange"], "--", 10, 10),
    ]
    for event_name, value, color, line_style, x_offset, y_offset in event_specs:
        event_value = _json_number(value)
        if event_value is None:
            continue
        y_value = float(np.interp(event_value, result.T, result.HF))
        objects.append(
            {
                "id": f"line-{event_name}",
                "type": "line",
                "name": event_name,
                "orientation": "vertical",
                "x": event_value,
                "label": f"{event_name} = {event_value:.1f} C",
                "style": {"color": color, "line_width": 0.8, "line_style": line_style, "alpha": 0.7},
            }
        )
        objects.append(
            {
                "id": f"text-{event_name}",
                "type": "text",
                "name": "Annotation",
                "text": f"{event_name} = {event_value:.1f} C",
                "x": float(event_value + (x_offset * 0.1)),
                "y": float(y_value + (y_offset * 0.01 * (hf_max if hf_max else 1.0))),
                "rotation": 0.0,
                "anchor": "center",
                "style": {"color": color, "font_size": 8 if event_name != "Tm2" else 7},
            }
        )
    if np.isfinite(result.Xc_pct):
        objects.append(
            {
                "id": "text-Xc",
                "type": "text",
                "name": "Annotation",
                "text": f"Xc = {result.Xc_pct:.1f}%",
                "x": float(t_max),
                "y": float(hf_max),
                "rotation": 0.0,
                "anchor": "right",
                "style": {"color": SCI_COLORS["dark"], "font_size": 9},
            }
        )
    objects.extend(
        [
            {
                "id": "axis-x",
                "type": "axis",
                "name": "Horizontal Axis",
                "orientation": "horizontal",
                "label": "Temperature (deg C)",
                "reversed": False,
                "scale": "linear",
                "style": {"color": SCI_COLORS["dark"], "line_width": 0.8},
            },
            {
                "id": "axis-y",
                "type": "axis",
                "name": "Vertical Axis",
                "orientation": "vertical",
                "label": "Heat Flow (W/g) exo up",
                "reversed": False,
                "scale": "linear",
                "style": {"color": SCI_COLORS["dark"], "line_width": 0.8},
            },
        ]
    )
    save_generated_figure_document(
        path,
        technique="dsc",
        figure_id=figure_id,
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
            "function": "fig_d1_full_curve",
            "inputs": {"result_label": str(result.label or "")},
            "parameters": {"fname": figure_id},
        },
        style={
            "xlabel": "Temperature (deg C)",
            "ylabel": "Heat Flow (W/g) exo up",
        },
        objects=objects,
    )


def _save_d2_tg_zoom_document(
    path: str,
    result: DSCResult,
    figure_id: str,
    T_zoom: np.ndarray,
    HF_zoom: np.ndarray,
) -> None:
    data_path = _write_d2_tg_zoom_data(path, T_zoom, HF_zoom)
    data_ref = "dsc-tg-zoom-data"
    tg_value = _json_number(result.Tg_C)
    objects = [
        {
            "id": "series-tg-zoom",
            "type": "plot_series",
            "name": "Tg Zoom",
            "data_ref": data_ref,
            "x_column": "temperature_C",
            "y_column": "heat_flow_W_g",
            "style": {"color": SCI_COLORS["blue"], "line_width": 1.5},
        }
    ]
    if tg_value is not None:
        objects.append(
            {
                "id": "marker-Tg",
                "type": "line",
                "name": "Glass Transition Tg",
                "orientation": "vertical",
                "x": tg_value,
                "label": f"Tg = {tg_value:.1f} C",
                "style": {"color": SCI_COLORS["red"], "line_width": 1.0, "alpha": 0.8},
            }
        )
    save_generated_figure_document(
        path,
        technique="dsc",
        figure_id=figure_id,
        data_sources=[
            {
                "id": data_ref,
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": "polynexus.core.dsc_engine.dsc_output",
            "function": "fig_d2_tg_zoom",
            "inputs": {"result_label": str(result.label or "")},
            "parameters": {
                "fname": figure_id,
                "Tg_C": tg_value,
                "Tg_method": str(result.Tg_method or ""),
                "DTg_C": _json_number(result.DTg_C),
                "zoom_margin_C": 30.0,
            },
        },
        style={
            "xlabel": "Temperature (deg C)",
            "ylabel": "Heat Flow (W/g) exo up",
        },
        objects=objects,
    )


def _save_d3_crystallinity_document(
    path: str,
    valid_results: List[tuple[DSCResult, float]],
    labels: List[str],
    figure_id: str,
) -> None:
    data_path = _write_d3_crystallinity_data(path, valid_results, labels)
    data_ref = "dsc-crystallinity-data"
    save_generated_figure_document(
        path,
        technique="dsc",
        figure_id=figure_id,
        data_sources=[
            {
                "id": data_ref,
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": "polynexus.core.dsc_engine.dsc_output",
            "function": "fig_d3_crystallinity",
            "inputs": {"result_labels": [str(result.label or "") for result, _ in valid_results]},
            "parameters": {
                "fname": figure_id,
                "sample_count": len(valid_results),
            },
        },
        style={
            "xlabel": "Sample",
            "ylabel": "Crystallinity Xc (%)",
            "x_tick_rotation": 30,
        },
        objects=[
            {
                "id": "series-crystallinity",
                "type": "plot_series",
                "chart_kind": "bar",
                "name": "Crystallinity",
                "data_ref": data_ref,
                "x_column": "label",
                "y_column": "Xc_pct",
                "style": {"palette": SCI_PALETTE, "line_width": 0.5, "stroke": "#FFFFFF"},
            }
        ],
    )


def _save_d4_avrami_document(
    path: str,
    avrami: AvramiResult,
    *,
    ln_t: np.ndarray,
    avrami_y: np.ndarray,
    fit_ln_t: np.ndarray,
    avrami_fit: np.ndarray,
) -> None:
    data_path = _write_d4_avrami_data(path, avrami, ln_t, avrami_y, fit_ln_t, avrami_fit)
    data_ref = "dsc-avrami-data"
    objects = [
        {
            "id": "series-xt-data",
            "type": "plot_series",
            "name": "Experimental Xt",
            "data_ref": data_ref,
            "x_column": "time_min",
            "y_column": "Xt_pct",
            "style": {"color": SCI_COLORS["blue"], "marker": "o", "line_width": 0.0, "alpha": 0.6},
        }
    ]
    if len(avrami.Xt_fit) > 0:
        objects.append(
            {
                "id": "series-xt-fit",
                "type": "plot_series",
                "name": "Avrami Xt Fit",
                "data_ref": data_ref,
                "x_column": "time_min",
                "y_column": "Xt_fit_pct",
                "style": {"color": SCI_COLORS["red"], "line_width": 1.5},
            }
        )
    objects.extend(
        [
            {
                "id": "series-avrami-linear",
                "type": "plot_series",
                "name": "Avrami Linearized Data",
                "data_ref": data_ref,
                "x_column": "ln_t",
                "y_column": "avrami_y",
                "style": {"color": SCI_COLORS["blue"], "marker": "o", "line_width": 0.0, "alpha": 0.7},
            },
            {
                "id": "series-avrami-linear-fit",
                "type": "plot_series",
                "name": "Avrami Linear Fit",
                "data_ref": data_ref,
                "x_column": "fit_ln_t",
                "y_column": "avrami_fit",
                "style": {"color": SCI_COLORS["red"], "line_width": 1.5},
            },
        ]
    )
    save_generated_figure_document(
        path,
        technique="dsc",
        figure_id="Fig-D4_avrami",
        data_sources=[
            {
                "id": data_ref,
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": "polynexus.core.dsc_engine.dsc_output",
            "function": "fig_d4_avrami",
            "inputs": {"label": str(avrami.label or "")},
            "parameters": {
                "n": _json_number(avrami.n),
                "log_k": _json_number(avrami.log_k),
                "k": _json_number(avrami.k),
                "t_half_min": _json_number(avrami.t_half_min),
                "r_squared": _json_number(avrami.r_squared),
                "temperature_C": _json_number(avrami.temperature_C),
            },
        },
        style={
            "panels": ["Xt", "Avrami linear fit"],
            "xt_xlabel": "Time (min)",
            "xt_ylabel": "X(t) (%)",
            "linear_xlabel": "ln(t / min)",
            "linear_ylabel": "ln[-ln(1-X(t))]",
        },
        objects=objects,
    )


def _save_d5_kissinger_document(
    path: str,
    kissinger: NonIsothermalResult,
    *,
    Tp_C: np.ndarray,
    rates: np.ndarray,
    x: np.ndarray,
    y: np.ndarray,
    fit_x: np.ndarray,
    fit_y: np.ndarray,
    slope: float | None,
    intercept: float | None,
    r_squared: float | None,
    Ea_kJmol: float | None,
) -> None:
    data_path = _write_d5_kissinger_data(path, Tp_C, rates, x, y, fit_x, fit_y)
    data_ref = "dsc-kissinger-data"
    objects = [
        {
            "id": "series-kissinger-points",
            "type": "plot_series",
            "name": "Kissinger Points",
            "data_ref": data_ref,
            "x_column": "inv_Tp_K_1000",
            "y_column": "ln_beta_over_Tp2",
            "style": {"color": SCI_COLORS["blue"], "marker": "o", "line_width": 0.0},
        }
    ]
    if len(fit_x) > 0:
        objects.append(
            {
                "id": "series-kissinger-fit",
                "type": "plot_series",
                "name": "Kissinger Fit",
                "data_ref": data_ref,
                "x_column": "fit_x",
                "y_column": "fit",
                "style": {"color": SCI_COLORS["red"], "line_width": 1.2},
            }
        )
    save_generated_figure_document(
        path,
        technique="dsc",
        figure_id="Fig-D5_kissinger",
        data_sources=[
            {
                "id": data_ref,
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": "polynexus.core.dsc_engine.dsc_output",
            "function": "fig_d5_kissinger",
            "inputs": {"method": str(kissinger.method or "")},
            "parameters": {
                "point_count": len(Tp_C),
                "slope": _json_number(slope),
                "intercept": _json_number(intercept),
                "r_squared": _json_number(r_squared),
                "Ea_kJmol": _json_number(Ea_kJmol),
                "reported_Ea_kJmol": _json_number(kissinger.kissinger_Ea_kJmol),
            },
        },
        style={
            "xlabel": "1000 / Tp (K^-1)",
            "ylabel": "ln(beta / Tp^2)",
        },
        objects=objects,
    )


def _save_d6_deconvolution_document(
    path: str,
    result: DSCResult,
    figure_id: str,
    melt_peaks: List[dict],
    component_curves: List[np.ndarray],
) -> None:
    data_path = _write_d6_deconvolution_data(path, result, component_curves)
    data_ref = "dsc-deconvolution-data"
    objects = [
        {
            "id": "series-experimental",
            "type": "plot_series",
            "name": "Experimental",
            "data_ref": data_ref,
            "x_column": "temperature_C",
            "y_column": "heat_flow_W_g",
            "style": {"color": SCI_COLORS["dark"], "line_width": 1.2},
        }
    ]
    for index, peak in enumerate(melt_peaks):
        mu = _peak_mu(peak)
        objects.append(
            {
                "id": f"series-component-{index + 1}",
                "type": "plot_series",
                "name": f"Peak {index + 1}",
                "data_ref": data_ref,
                "x_column": "temperature_C",
                "y_column": f"component_{index + 1}",
                "peak_C": _json_number(mu),
                "fraction": _json_number(peak.get("fraction")),
                "style": {
                    "color": SCI_PALETTE[index % len(SCI_PALETTE)],
                    "line_width": 1.0,
                    "alpha": 0.25,
                    "fill": SCI_PALETTE[index % len(SCI_PALETTE)],
                },
            }
        )
    save_generated_figure_document(
        path,
        technique="dsc",
        figure_id=figure_id,
        data_sources=[
            {
                "id": data_ref,
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": "polynexus.core.dsc_engine.dsc_output",
            "function": "fig_d6_deconvolution",
            "inputs": {"result_label": str(result.label or "")},
            "parameters": {
                "fname": figure_id,
                "component_count": len(melt_peaks),
            },
        },
        style={
            "xlabel": "Temperature (deg C)",
            "ylabel": "Heat Flow (W/g) exo up",
            "fill_components": True,
        },
        objects=objects,
    )


def _save_batch_overlay_document(
    path: str,
    results: List[DSCResult],
    *,
    figure_id: str,
    function_name: str,
    scan_type: str,
) -> None:
    data_path = _write_batch_overlay_data(path, results)
    data_ref = f"dsc-{scan_type}-overlay-data"
    objects = [
        {
            "id": f"series-{scan_type}-{index + 1}",
            "type": "plot_series",
            "name": _short_sample_name(result.label),
            "data_ref": data_ref,
            "x_column": "temperature_C",
            "y_column": "heat_flow_offset",
            "filter": {"scan_index": index},
            "style": {"color": SCI_PALETTE[index % len(SCI_PALETTE)], "line_width": 1.2},
        }
        for index, result in enumerate(results)
    ]
    save_generated_figure_document(
        path,
        technique="dsc",
        figure_id=figure_id,
        data_sources=[
            {
                "id": data_ref,
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": "polynexus.core.dsc_engine.dsc_output",
            "function": function_name,
            "inputs": {"result_labels": [str(result.label or "") for result in results]},
            "parameters": {
                "sample_count": len(results),
                "scan_type": scan_type,
            },
        },
        style={
            "xlabel": "Temperature (deg C)",
            "ylabel": "Heat Flow (offset) exo up",
            "offset_curves": True,
        },
        objects=objects,
    )


def _save_batch_crystallinity_document(
    path: str,
    valid_results: List[tuple[DSCResult, float]],
    labels: List[str],
    figure_id: str,
) -> None:
    data_path = _write_d3_crystallinity_data(path, valid_results, labels)
    data_ref = "dsc-batch-crystallinity-data"
    save_generated_figure_document(
        path,
        technique="dsc",
        figure_id=figure_id,
        data_sources=[
            {
                "id": data_ref,
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": "polynexus.core.dsc_engine.dsc_output",
            "function": "fig_batch_crystallinity",
            "inputs": {"result_labels": [str(result.label or "") for result, _ in valid_results]},
            "parameters": {
                "sample_count": len(valid_results),
                "fname": figure_id,
            },
        },
        style={
            "xlabel": "Sample",
            "ylabel": "Crystallinity Xc (%)",
            "x_tick_rotation": 30,
        },
        objects=[
            {
                "id": "series-batch-crystallinity",
                "type": "plot_series",
                "chart_kind": "bar",
                "name": "Batch Crystallinity",
                "data_ref": data_ref,
                "x_column": "label",
                "y_column": "Xc_pct",
                "style": {"palette": SCI_PALETTE, "line_width": 0.5, "stroke": "#FFFFFF"},
            }
        ],
    )


def _write_d1_full_curve_data(path: str, result: DSCResult) -> Path:
    figure_path = Path(path).resolve()
    output_root = figure_path.parent.parent
    data_dir = output_root / "data" / "figure_sources"
    data_dir.mkdir(parents=True, exist_ok=True)
    data_path = data_dir / f"{figure_path.stem}_data.csv"
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["temperature_C", "heat_flow_W_g"],
        )
        writer.writeheader()
        for index, temperature in enumerate(result.T):
            writer.writerow(
                {
                    "temperature_C": _csv_number(temperature),
                    "heat_flow_W_g": _csv_number(result.HF[index]),
                }
            )
    return data_path


def _write_d6_deconvolution_data(
    path: str,
    result: DSCResult,
    component_curves: List[np.ndarray],
) -> Path:
    figure_path = Path(path).resolve()
    output_root = figure_path.parent.parent
    data_dir = output_root / "data" / "figure_sources"
    data_dir.mkdir(parents=True, exist_ok=True)
    data_path = data_dir / f"{figure_path.stem}_data.csv"
    fieldnames = ["temperature_C", "heat_flow_W_g"]
    fieldnames.extend(f"component_{index + 1}" for index in range(len(component_curves)))
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for index, temperature in enumerate(result.T):
            row = {
                "temperature_C": _csv_number(temperature),
                "heat_flow_W_g": _csv_number(result.HF[index]),
            }
            for component_index, curve in enumerate(component_curves):
                row[f"component_{component_index + 1}"] = _csv_number(curve[index])
            writer.writerow(row)
    return data_path


def _write_d5_kissinger_data(
    path: str,
    Tp_C: np.ndarray,
    rates: np.ndarray,
    x: np.ndarray,
    y: np.ndarray,
    fit_x: np.ndarray,
    fit_y: np.ndarray,
) -> Path:
    figure_path = Path(path).resolve()
    output_root = figure_path.parent.parent
    data_dir = output_root / "data" / "figure_sources"
    data_dir.mkdir(parents=True, exist_ok=True)
    data_path = data_dir / f"{figure_path.stem}_data.csv"
    rows = max(len(Tp_C), len(fit_x))
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "Tp_C",
                "rate_K_min",
                "inv_Tp_K_1000",
                "ln_beta_over_Tp2",
                "fit_x",
                "fit",
            ],
        )
        writer.writeheader()
        for index in range(rows):
            writer.writerow(
                {
                    "Tp_C": _csv_number(Tp_C[index]) if index < len(Tp_C) else "",
                    "rate_K_min": _csv_number(rates[index]) if index < len(rates) else "",
                    "inv_Tp_K_1000": _csv_number(x[index]) if index < len(x) else "",
                    "ln_beta_over_Tp2": _csv_number(y[index]) if index < len(y) else "",
                    "fit_x": _csv_number(fit_x[index]) if index < len(fit_x) else "",
                    "fit": _csv_number(fit_y[index]) if index < len(fit_y) else "",
                }
            )
    return data_path


def _write_d4_avrami_data(
    path: str,
    avrami: AvramiResult,
    ln_t: np.ndarray,
    avrami_y: np.ndarray,
    fit_ln_t: np.ndarray,
    avrami_fit: np.ndarray,
) -> Path:
    figure_path = Path(path).resolve()
    output_root = figure_path.parent.parent
    data_dir = output_root / "data" / "figure_sources"
    data_dir.mkdir(parents=True, exist_ok=True)
    data_path = data_dir / f"{figure_path.stem}_data.csv"
    rows = max(len(avrami.t_data), len(ln_t), len(fit_ln_t))
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "time_min",
                "Xt_pct",
                "Xt_fit_pct",
                "ln_t",
                "avrami_y",
                "fit_ln_t",
                "avrami_fit",
            ],
        )
        writer.writeheader()
        for index in range(rows):
            writer.writerow(
                {
                    "time_min": _csv_number(avrami.t_data[index])
                    if index < len(avrami.t_data)
                    else "",
                    "Xt_pct": _csv_number(avrami.Xt_data[index] * 100.0)
                    if index < len(avrami.Xt_data)
                    else "",
                    "Xt_fit_pct": _csv_number(avrami.Xt_fit[index] * 100.0)
                    if index < len(avrami.Xt_fit)
                    else "",
                    "ln_t": _csv_number(ln_t[index]) if index < len(ln_t) else "",
                    "avrami_y": _csv_number(avrami_y[index]) if index < len(avrami_y) else "",
                    "fit_ln_t": _csv_number(fit_ln_t[index]) if index < len(fit_ln_t) else "",
                    "avrami_fit": _csv_number(avrami_fit[index]) if index < len(avrami_fit) else "",
                }
            )
    return data_path


def _write_d3_crystallinity_data(
    path: str,
    valid_results: List[tuple[DSCResult, float]],
    labels: List[str],
) -> Path:
    figure_path = Path(path).resolve()
    output_root = figure_path.parent.parent
    data_dir = output_root / "data" / "figure_sources"
    data_dir.mkdir(parents=True, exist_ok=True)
    data_path = data_dir / f"{figure_path.stem}_data.csv"
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["label", "result_label", "Xc_pct", "Xc_method"],
        )
        writer.writeheader()
        for index, (result, xc_value) in enumerate(valid_results):
            writer.writerow(
                {
                    "label": labels[index] if index < len(labels) else str(result.label or ""),
                    "result_label": str(result.label or ""),
                    "Xc_pct": _csv_number(xc_value),
                    "Xc_method": str(result.Xc_method or ""),
                }
            )
    return data_path


def _write_d2_tg_zoom_data(path: str, T_zoom: np.ndarray, HF_zoom: np.ndarray) -> Path:
    figure_path = Path(path).resolve()
    output_root = figure_path.parent.parent
    data_dir = output_root / "data" / "figure_sources"
    data_dir.mkdir(parents=True, exist_ok=True)
    data_path = data_dir / f"{figure_path.stem}_data.csv"
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["temperature_C", "heat_flow_W_g"])
        writer.writeheader()
        for index, temperature in enumerate(T_zoom):
            writer.writerow(
                {
                    "temperature_C": _csv_number(temperature),
                    "heat_flow_W_g": _csv_number(HF_zoom[index]),
                }
            )
    return data_path


def _write_batch_overlay_data(path: str, results: List[DSCResult]) -> Path:
    figure_path = Path(path).resolve()
    output_root = figure_path.parent.parent
    data_dir = output_root / "data" / "figure_sources"
    data_dir.mkdir(parents=True, exist_ok=True)
    data_path = data_dir / f"{figure_path.stem}_data.csv"
    hf_ranges = [float(np.ptp(result.HF)) for result in results if len(result.HF) > 0]
    max_range = max(hf_ranges) if hf_ranges else 1.0
    offset_step = max_range * 1.2
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "scan_index",
                "label",
                "temperature_C",
                "heat_flow_W_g",
                "heat_flow_offset",
            ],
        )
        writer.writeheader()
        for index, result in enumerate(results):
            offset = (len(results) - 1 - index) * offset_step
            for temperature, heat_flow in zip(result.T, result.HF):
                writer.writerow(
                    {
                        "scan_index": index,
                        "label": _short_sample_name(result.label),
                        "temperature_C": _csv_number(temperature),
                        "heat_flow_W_g": _csv_number(heat_flow),
                        "heat_flow_offset": _csv_number(float(heat_flow) + offset),
                    }
                )
    return data_path


def _csv_number(value) -> float:
    return round(float(value), 10)


def _json_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(number):
        return None
    return number


def _peak_mu(peak: dict) -> float:
    return peak.get("mu_C", peak.get("peak_C", np.nan))


# ---------------------------------------------------------------------------
#  Fig-D1: Full DSC curve
# ---------------------------------------------------------------------------

def fig_d1_full_curve(result: DSCResult, output_dir: str,
                      config: Optional[DSCConfig] = None,
                      fname: str = 'Fig-D1_full_curve',
                      ) -> str:
    """Fig-D1: Complete DSC thermogram with thermal event annotations.

    ⭐⭐⭐ Essential figure for all DSC papers.
    """
    fmt = config.fig_format if config else 'svg'
    dpi = config.fig_dpi if config else 300

    fig_dir, _ = _make_output_dirs(output_dir)

    fig, ax = plt.subplots(figsize=(6.8, 4.2))  # double-column width

    T = result.T
    HF = result.HF

    if len(T) == 0:
        plt.close(fig)
        return ""

    # Main curve
    ax.plot(T, HF, color=SCI_COLORS['blue'], linewidth=1.2, label='Heat Flow')

    # Annotate Tg
    if not np.isnan(result.Tg_C):
        ax.axvline(result.Tg_C, color=SCI_COLORS['red'], linestyle='--',
                   linewidth=0.8, alpha=0.7)
        ax.annotate(f"$T_g$ = {result.Tg_C:.1f} °C",
                    xy=(result.Tg_C, np.interp(result.Tg_C, T, HF)),
                    xytext=(10, 10), textcoords='offset points',
                    fontsize=8, color=SCI_COLORS['red'],
                    arrowprops=dict(arrowstyle='->', color=SCI_COLORS['red'], lw=0.8))

    # Annotate Tm
    if not np.isnan(result.Tm_peak_C):
        ax.axvline(result.Tm_peak_C, color=SCI_COLORS['green'], linestyle='--',
                   linewidth=0.8, alpha=0.7)
        ax.annotate(f"$T_m$ = {result.Tm_peak_C:.1f} °C",
                    xy=(result.Tm_peak_C, np.interp(result.Tm_peak_C, T, HF)),
                    xytext=(10, -15), textcoords='offset points',
                    fontsize=8, color=SCI_COLORS['green'],
                    arrowprops=dict(arrowstyle='->', color=SCI_COLORS['green'], lw=0.8))

    # Annotate Tm2 (secondary melting peak)
    if not np.isnan(result.Tm2_peak_C):
        ax.axvline(result.Tm2_peak_C, color=SCI_COLORS['cyan'], linestyle='-.',
                   linewidth=0.8, alpha=0.6)
        ax.annotate(f"$T_{{m2}}$ = {result.Tm2_peak_C:.1f} °C",
                    xy=(result.Tm2_peak_C, np.interp(result.Tm2_peak_C, T, HF)),
                    xytext=(10, -25), textcoords='offset points',
                    fontsize=7, color=SCI_COLORS['cyan'],
                    arrowprops=dict(arrowstyle='->', color=SCI_COLORS['cyan'], lw=0.7))

    # Annotate Tc (cooling crystallisation) — cooling scans only
    if not np.isnan(result.Tc_peak_C):
        ax.axvline(result.Tc_peak_C, color=SCI_COLORS['green'], linestyle='--',
                   linewidth=0.8, alpha=0.7)
        label = f"$T_c$ = {result.Tc_peak_C:.1f} °C"
        if not np.isnan(result.DHc_Jg):
            label += f"\n$\\Delta H_c$ = {result.DHc_Jg:.2f} J/g"
        ax.annotate(label,
                    xy=(result.Tc_peak_C, np.interp(result.Tc_peak_C, T, HF)),
                    xytext=(10, -15), textcoords='offset points',
                    fontsize=8, color=SCI_COLORS['green'],
                    arrowprops=dict(arrowstyle='->', color=SCI_COLORS['green'], lw=0.8))

    # Annotate Tcc (cold crystallisation) — heating scans only
    if not np.isnan(result.Tcc_peak_C):
        ax.axvline(result.Tcc_peak_C, color=SCI_COLORS['orange'], linestyle='--',
                   linewidth=0.8, alpha=0.7)
        ax.annotate(f"$T_{{cc}}$ = {result.Tcc_peak_C:.1f} °C",
                    xy=(result.Tcc_peak_C, np.interp(result.Tcc_peak_C, T, HF)),
                    xytext=(10, 10), textcoords='offset points',
                    fontsize=8, color=SCI_COLORS['orange'],
                    arrowprops=dict(arrowstyle='->', color=SCI_COLORS['orange'], lw=0.8))

    # Crystallinity annotation
    if not np.isnan(result.Xc_pct):
        ax.text(0.98, 0.05, f"$X_c$ = {result.Xc_pct:.1f}%",
                transform=ax.transAxes, ha='right', va='bottom',
                fontsize=9, bbox=dict(boxstyle='round,pad=0.3',
                                      facecolor='white', alpha=0.8))

    set_sci_style(fig, ax,
                  xlabel='Temperature (°C)',
                  ylabel='Heat Flow (W/g) exo ↑',
                  title='')

    path = _save_figure(fig, fname, fig_dir, fmt, dpi)
    _save_d1_full_curve_document(path, result, fname)
    return path


# ---------------------------------------------------------------------------
#  Fig-D2: Tg region zoom
# ---------------------------------------------------------------------------

def fig_d2_tg_zoom(result: DSCResult, output_dir: str,
                   config: Optional[DSCConfig] = None,
                   fname: str = 'Fig-D2_Tg_zoom',
                   ) -> str:
    """Fig-D2: Magnified glass transition region.

    ⭐⭐ Supplementary figure.
    """
    fmt = config.fig_format if config else 'svg'
    dpi = config.fig_dpi if config else 300

    fig_dir, _ = _make_output_dirs(output_dir)

    T = result.T
    HF = result.HF

    if len(T) == 0 or np.isnan(result.Tg_C):
        return ""

    fig, ax = plt.subplots(figsize=(4.2, 3.5))  # single-column width

    # Zoom around Tg ± 30 K
    margin = 30.0
    mask = (T >= result.Tg_C - margin) & (T <= result.Tg_C + margin)
    if np.sum(mask) < 10:
        mask = np.ones_like(T, dtype=bool)

    T_zoom = T[mask]
    HF_zoom = HF[mask]

    ax.plot(T_zoom, HF_zoom, color=SCI_COLORS['blue'], linewidth=1.5)

    # Tg line
    tg_hf = np.interp(result.Tg_C, T, HF)
    ax.axvline(result.Tg_C, color=SCI_COLORS['red'], linestyle='--',
               linewidth=1.0, alpha=0.8)
    ax.annotate(f"$T_g$ = {result.Tg_C:.1f} °C\n({result.Tg_method})",
                xy=(result.Tg_C, tg_hf),
                xytext=(15, 15), textcoords='offset points',
                fontsize=8, color=SCI_COLORS['red'],
                arrowprops=dict(arrowstyle='->', color=SCI_COLORS['red'], lw=0.8))

    # Width annotation
    if not np.isnan(result.DTg_C):
        ax.annotate(f"Δ$T_g$ = {result.DTg_C:.1f} K",
                    xy=(0.5, 0.02), xycoords='axes fraction',
                    fontsize=8, color=SCI_COLORS['grey'], ha='center')

    set_sci_style(fig, ax,
                  xlabel='Temperature (°C)',
                  ylabel='Heat Flow (W/g) exo ↑',
                  title='')

    path = _save_figure(fig, fname, fig_dir, fmt, dpi)
    _save_d2_tg_zoom_document(path, result, fname, T_zoom, HF_zoom)
    return path


# ---------------------------------------------------------------------------
#  Fig-D3: Crystallinity comparison
# ---------------------------------------------------------------------------

def fig_d3_crystallinity(results: List[DSCResult], output_dir: str,
                         config: Optional[DSCConfig] = None,
                         fname: str = 'Fig-D3_crystallinity',
                         ) -> str:
    """Fig-D3: Bar chart comparing crystallinity across samples.

    ⭐⭐ Supplementary figure.
    """
    fmt = config.fig_format if config else 'svg'
    dpi = config.fig_dpi if config else 300

    fig_dir, _ = _make_output_dirs(output_dir)

    # Filter to scans with valid crystallinity
    valid = [(r, r.Xc_pct) for r in results
             if not np.isnan(r.Xc_pct)]
    if not valid:
        return ""

    # Shorten labels: use segment type + temperature range
    def _short_label(r: DSCResult) -> str:
        lbl = r.label or ""
        parts = lbl.split('/')
        if len(parts) >= 3:
            seg = parts[-1]  # e.g. "heat 30-239C"
        elif len(parts) >= 2:
            seg = parts[-1]
        else:
            seg = lbl
        return seg

    labels = [_short_label(r) for r, _ in valid]
    xc = [v for _, v in valid]

    fig, ax = plt.subplots(figsize=(5.5, 3.5))
    colors = [SCI_PALETTE[i % len(SCI_PALETTE)] for i in range(len(labels))]
    bars = ax.bar(range(len(labels)), xc, color=colors, edgecolor='white',
                  linewidth=0.5)

    for bar, val in zip(bars, xc):
        ax.text(bar.get_x() + bar.get_width() / 2.0,
                bar.get_height() + max(xc) * 0.02,
                f'{val:.1f}%', ha='center', va='bottom',
                fontsize=8, fontweight='bold')

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha='right', fontsize=8)
    ymax = max(xc) * 1.15 if max(xc) > 0 else 1.0
    ax.set_ylim(0, ymax)

    set_sci_style(fig, ax,
                  ylabel='Crystallinity $X_c$ (%)',
                  title='')

    path = _save_figure(fig, fname, fig_dir, fmt, dpi)
    _save_d3_crystallinity_document(path, valid, labels, fname)
    return path


# ---------------------------------------------------------------------------
#  Fig-D4: Avrami plot
# ---------------------------------------------------------------------------

def fig_d4_avrami(avrami: AvramiResult, output_dir: str,
                  config: Optional[DSCConfig] = None,
                  ) -> str:
    """Fig-D4: Avrami analysis (isothermal crystallisation).

    Shows: (a) X(t) evolution, (b) Avrami linear fit.

    ⭐⭐⭐ Essential for isothermal crystallisation papers.
    """
    fmt = config.fig_format if config else 'svg'
    dpi = config.fig_dpi if config else 300

    fig_dir, _ = _make_output_dirs(output_dir)

    if len(avrami.Xt_data) == 0:
        return ""

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.0, 3.5))

    # (a) Relative crystallinity vs time
    ax1.plot(avrami.t_data, avrami.Xt_data * 100, 'o',
             color=SCI_COLORS['blue'], markersize=3, alpha=0.6,
             label='Experimental')
    if len(avrami.Xt_fit) > 0:
        ax1.plot(avrami.t_data, avrami.Xt_fit * 100, '-',
                 color=SCI_COLORS['red'], linewidth=1.5,
                 label=f'Avrami fit ($n$={avrami.n:.2f})')
    ax1.axhline(50, color=SCI_COLORS['grey'], linestyle=':', linewidth=0.8)
    ax1.legend(fontsize=8, framealpha=0.9)
    set_sci_style(fig, ax1,
                  xlabel='Time (min)',
                  ylabel='$X(t)$ (%)')
    _panel(ax1, '(a)')

    # (b) Avrami linear fit
    X_clip = np.clip(avrami.Xt_data, 1e-6, 1 - 1e-6)
    y = np.log(-np.log(1 - X_clip))
    x = np.log(np.maximum(avrami.t_data, 1e-9))

    mask = (avrami.Xt_data >= 0.01) & (avrami.Xt_data <= 0.99)
    ax2.plot(x[mask], y[mask], 'o', color=SCI_COLORS['blue'],
             markersize=4, alpha=0.7)

    # Fitted line
    intercept = avrami.log_k * np.log(10)
    x_fit = np.linspace(x[mask].min(), x[mask].max(), 100)
    y_fit = avrami.n * x_fit + intercept
    ax2.plot(x_fit, y_fit, '-', color=SCI_COLORS['red'], linewidth=1.5)

    ax2.text(0.95, 0.05,
             f"$n$ = {avrami.n:.2f}\n"
             f"$k$ = {avrami.k:.2e} min$^{{-n}}$\n"
             f"$t_{{1/2}}$ = {avrami.t_half_min:.2f} min\n"
             f"$R^2$ = {avrami.r_squared:.3f}",
             transform=ax2.transAxes, ha='right', va='bottom',
             fontsize=8, bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    set_sci_style(fig, ax2,
                  xlabel='ln($t$ / min)',
                  ylabel='ln[-ln(1-$X(t)$)]')
    _panel(ax2, '(b)')

    path = _save_figure(fig, 'Fig-D4_avrami', fig_dir, fmt, dpi)
    _save_d4_avrami_document(
        path,
        avrami,
        ln_t=x[mask],
        avrami_y=y[mask],
        fit_ln_t=x_fit,
        avrami_fit=y_fit,
    )
    return path


# ---------------------------------------------------------------------------
#  Fig-D5: Kissinger / Ozawa plot
# ---------------------------------------------------------------------------

def fig_d5_kissinger(kissinger: NonIsothermalResult,
                     Tp_C_list: List[float],
                     rates: List[float],
                     output_dir: str,
                     config: Optional[DSCConfig] = None,
                     ) -> str:
    """Fig-D5: Kissinger plot for activation energy.

    ⭐⭐ Supplementary for non-isothermal kinetics.
    """
    fmt = config.fig_format if config else 'svg'
    dpi = config.fig_dpi if config else 300

    fig_dir, _ = _make_output_dirs(output_dir)

    if len(Tp_C_list) < 2:
        return ""

    fig, ax = plt.subplots(figsize=(4.5, 3.5))

    Tp_K = np.array(Tp_C_list) + 273.15
    beta = np.array(rates)

    x = 1000.0 / Tp_K
    y = np.log(beta / Tp_K ** 2)

    ax.plot(x, y, 'o', color=SCI_COLORS['blue'], markersize=8,
            markeredgewidth=1, markeredgecolor='white')

    slope = intercept = r = Ea = None
    x_fit = np.array([])
    y_fit = np.array([])
    if len(x) >= 3:
        slope, intercept, _, _, _ = plt.matplotlib.mlab if False else (0, 0, 0, 0, 0)
        import scipy.stats
        slope, intercept, r, _, _ = scipy.stats.linregress(x, y)
        x_fit = np.linspace(x.min(), x.max(), 100)
        y_fit = slope * x_fit + intercept
        ax.plot(x_fit, y_fit, '-', color=SCI_COLORS['red'], linewidth=1.2)

        Ea = -slope * 8.314
        ax.text(0.95, 0.95,
                f"$E_a$ = {Ea:.1f} kJ/mol\n$R^2$ = {r ** 2:.4f}",
                transform=ax.transAxes, ha='right', va='top',
                fontsize=9, bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    set_sci_style(fig, ax,
                  xlabel='1000 / $T_p$ (K$^{-1}$)',
                  ylabel='ln($\\beta$ / $T_p^2$)',
                  title='')

    path = _save_figure(fig, 'Fig-D5_kissinger', fig_dir, fmt, dpi)
    _save_d5_kissinger_document(
        path,
        kissinger,
        Tp_C=np.array(Tp_C_list),
        rates=beta,
        x=x,
        y=y,
        fit_x=x_fit,
        fit_y=y_fit,
        slope=slope,
        intercept=intercept,
        r_squared=r**2 if r is not None else None,
        Ea_kJmol=Ea,
    )
    return path


# ---------------------------------------------------------------------------
#  Fig-D6: Multi-peak deconvolution
# ---------------------------------------------------------------------------

def fig_d6_deconvolution(result: DSCResult, output_dir: str,
                         config: Optional[DSCConfig] = None,
                         fname: str = 'Fig-D6_deconvolution',
                         ) -> str:
    """Fig-D6: Multi-peak deconvolution of overlapping melting peaks.

    ⭐⭐ Supplementary for complex melting behaviour.
    """
    fmt = config.fig_format if config else 'svg'
    dpi = config.fig_dpi if config else 300

    fig_dir, _ = _make_output_dirs(output_dir)

    # Filter: only use melting peaks for deconv plot
    T_min, T_max = float(np.min(result.T)), float(np.max(result.T))
    melt_peaks = []
    for pc in result.peak_components:
        if pc.get('type', '') not in ('melting', 'deconv_melting'):
            continue
        # Filter ghosts: deconv peaks with out-of-range centre or zero fraction
        if pc.get('type') == 'deconv_melting':
            mu = pc.get('mu_C', pc.get('peak_C', np.nan))
            if np.isnan(mu) or mu < T_min or mu > T_max:
                continue
            if pc.get('fraction', 0) < 0.01:
                continue
        melt_peaks.append(pc)
    if len(melt_peaks) < 2 or len(result.T) == 0:
        return ""

    fig, ax = plt.subplots(figsize=(5.5, 3.8))

    T = result.T
    ax.plot(T, result.HF, color=SCI_COLORS['dark'], linewidth=1.2,
            label='Experimental')

    total_enthalpy = sum(abs(pc.get('enthalpy_Jg', 0))
                         for pc in melt_peaks
                         if pc.get('type') == 'melting')
    if total_enthalpy == 0:
        total_enthalpy = 1.0

    # Individual components
    colors = SCI_PALETTE
    component_curves = []
    for i, comp in enumerate(melt_peaks):
        color = colors[i % len(colors)]

        # Support both deconv format (mu_C/sigma_C) and raw peak format (peak_C)
        if 'mu_C' in comp:
            mu = comp['mu_C']
            sigma = comp.get('sigma_C', 5.0)
            amp = comp.get('amp', 1.0)
            fraction = comp.get('fraction', 1.0 / len(melt_peaks))
        else:
            mu = comp.get('peak_C', 0)
            sigma = 4.0  # default width for DSC melting peaks
            enthalpy = abs(comp.get('enthalpy_Jg', 0))
            amp = enthalpy / (sigma * np.sqrt(2 * np.pi)) if sigma > 0 else 0
            fraction = enthalpy / total_enthalpy if total_enthalpy > 0 else 1.0 / len(melt_peaks)

        gauss = amp * np.exp(-0.5 * ((T - mu) / sigma) ** 2)
        component_curves.append(gauss)
        ax.fill_between(T, 0, gauss, alpha=0.25, color=color,
                        label=f"Peak {i + 1} ({mu:.1f} C, {fraction:.0%})")

    ax.legend(fontsize=7, framealpha=0.9, loc='upper right')

    set_sci_style(fig, ax,
                  xlabel='Temperature (°C)',
                  ylabel='Heat Flow (W/g) exo ↑',
                  title=f'Multi-Peak Deconvolution — {result.label}')

    path = _save_figure(fig, fname, fig_dir, fmt, dpi)
    _save_d6_deconvolution_document(path, result, fname, melt_peaks, component_curves)
    return path


# ---------------------------------------------------------------------------
#  Export data
# ---------------------------------------------------------------------------

def export_parameters_csv(results: List[DSCResult], output_dir: str) -> str:
    """Export DSC parameters to CSV (one row per scan)."""
    import pandas as pd
    _, data_dir = _make_output_dirs(output_dir)
    rows = []
    for r in results:
        rows.append(r.parameters)
    df = pd.DataFrame(rows)
    # Filter out rows with no thermal events detected (all key params NaN)
    key_cols = ['Tm_peak_C', 'DHm_Jg', 'Tg_C', 'Tc_peak_C', 'Tcc_peak_C']
    mask = df[key_cols].notna().any(axis=1)
    df = df[mask]
    if df.empty:
        return ""
    path = os.path.join(data_dir, 'dsc_parameters.csv')
    df.to_csv(path, index=False, encoding='utf-8-sig')
    return path


def export_detailed_peaks_csv(results: List[DSCResult], output_dir: str) -> str:
    """Export ALL detected peaks (multi-peak detail) to a separate CSV.

    One row per peak, including peak type, temperature, enthalpy,
    onset, and end temperature.
    """
    import pandas as pd
    _, data_dir = _make_output_dirs(output_dir)
    rows = []
    for i, r in enumerate(results):
        scan_label = r.label or f"scan_{i}"
        technique = r.technique or "unknown"
        for pc in r.peak_components:
            rows.append({
                'scan_index': i,
                'scan_label': scan_label,
                'technique': technique,
                'peak_type': pc.get('type', ''),
                'peak_C': pc.get('peak_C', np.nan),
                'onset_C': pc.get('onset_C', np.nan),
                'end_C': pc.get('end_C', np.nan),
                'enthalpy_Jg': pc.get('enthalpy_Jg', np.nan),
            })
    if not rows:
        return ""
    df = pd.DataFrame(rows)
    path = os.path.join(data_dir, 'dsc_detailed_peaks.csv')
    df.to_csv(path, index=False, encoding='utf-8-sig')
    return path


def export_all_results_csv(results: List[DSCResult], output_dir: str) -> str:
    """Export a cross-sample summary table (Table-1 ready).

    One row per scan segment; columns are the key SCI-reportable parameters
    with short display names.  Also writes a LaTeX-friendly variant.
    """
    import pandas as pd
    _, data_dir = _make_output_dirs(output_dir)

    rows = []
    for r in results:
        # Only include scans with thermal events
        if (np.isnan(r.Tm_peak_C) and np.isnan(r.Tc_peak_C)
                and np.isnan(r.Tcc_peak_C) and np.isnan(r.Tg_C)):
            continue
        rows.append({
            'Sample': _short_sample_name(r.label),
            'Segment': r.technique,
            'Tg (°C)': round(r.Tg_C, 1) if not np.isnan(r.Tg_C) else '',
            'Tm (°C)': round(r.Tm_peak_C, 1) if not np.isnan(r.Tm_peak_C) else '',
            'Tm2 (°C)': round(r.Tm2_peak_C, 1) if not np.isnan(r.Tm2_peak_C) else '',
            'ΔHm (J/g)': round(r.DHm_Jg, 2) if not np.isnan(r.DHm_Jg) else '',
            'Tcc (°C)': round(r.Tcc_peak_C, 1) if not np.isnan(r.Tcc_peak_C) else '',
            'ΔHcc (J/g)': round(r.DHcc_Jg, 2) if not np.isnan(r.DHcc_Jg) else '',
            'Tc (°C)': round(r.Tc_peak_C, 1) if not np.isnan(r.Tc_peak_C) else '',
            'ΔHc (J/g)': round(r.DHc_Jg, 2) if not np.isnan(r.DHc_Jg) else '',
            'Xc (%)': round(r.Xc_pct, 2) if not np.isnan(r.Xc_pct) else '',
            'Quality': ', '.join(r.quality_flags) if r.quality_flags else 'OK',
        })
    if not rows:
        return ""
    df = pd.DataFrame(rows)

    # Standard CSV
    path = os.path.join(data_dir, 'dsc_all_results.csv')
    df.to_csv(path, index=False, encoding='utf-8-sig')

    return path


# ---------------------------------------------------------------------------
#  Fig-D7: Multi-sample heating curve overlay
# ---------------------------------------------------------------------------

def _short_sample_name(label: str) -> str:
    """Extract a short, human-readable sample name from a scan label."""
    # e.g. "30.xls/斜坡 10.00 °Cmin 到 240.00 °C/heat 30-239C" → "30 (heat 30-239C)"
    # e.g. "默认(42).xls/斜坡 .../heat 30-229C" → "默认(42) (heat 30-229C)"
    parts = label.split('/')
    basename = parts[0].replace('.xls', '').replace('.XLS', '')
    if len(parts) >= 3:
        return f"{basename} ({parts[-1]})"
    return basename


def fig_batch_heating_overlay(results: List[DSCResult], output_dir: str,
                               config: Optional[DSCConfig] = None,
                               fname: str = 'Fig-D7_heating_overlay',
                               ) -> str:
    """Fig-D7: Overlay of all heating scans with vertical offset.

    ⭐⭐⭐ Essential for multi-sample DSC papers.
    """
    fmt = config.fig_format if config else 'svg'
    dpi = config.fig_dpi if config else 300
    fig_dir, _ = _make_output_dirs(output_dir)

    # Filter to heating scans with real data
    heating = [r for r in results
               if r.technique == 'heating' and len(r.T) > 0]
    if len(heating) < 2:
        return ""

    fig, ax = plt.subplots(figsize=(7.2, 4.5))

    # Calculate vertical offset
    hf_ranges = [float(np.ptp(r.HF)) for r in heating]
    max_range = max(hf_ranges) if hf_ranges else 1.0
    offset_step = max_range * 1.2

    colors_used = [SCI_PALETTE[i % len(SCI_PALETTE)] for i in range(len(heating))]
    for i, r in enumerate(heating):
        offset = (len(heating) - 1 - i) * offset_step
        color = colors_used[i]
        label = _short_sample_name(r.label)
        ax.plot(r.T, r.HF + offset, color=color, linewidth=1.2, label=label)

        # Annotate Tm on each curve
        if not np.isnan(r.Tm_peak_C):
            hf_at_peak = np.interp(r.Tm_peak_C, r.T, r.HF) + offset
            ax.annotate(f"{r.Tm_peak_C:.0f}°C",
                        xy=(r.Tm_peak_C, hf_at_peak),
                        xytext=(5, 8), textcoords='offset points',
                        fontsize=7, color=color,
                        arrowprops=dict(arrowstyle='->', color=color, lw=0.7))

    ax.legend(fontsize=8, framealpha=0.9, loc='upper left',
              bbox_to_anchor=(1.01, 1), borderaxespad=0)
    ax.set_yticks([])  # offset makes y-axis meaningless

    set_sci_style(fig, ax,
                  xlabel='Temperature (°C)',
                  ylabel='Heat Flow (offset)  exo ↑',
                  title='')

    path = _save_figure(fig, fname, fig_dir, fmt, dpi)
    _save_batch_overlay_document(
        path,
        heating,
        figure_id=Path(path).resolve().stem,
        function_name="fig_batch_heating_overlay",
        scan_type="heating",
    )
    return path


def fig_batch_cooling_overlay(results: List[DSCResult], output_dir: str,
                               config: Optional[DSCConfig] = None,
                               fname: str = 'Fig-D8_cooling_overlay',
                               ) -> str:
    """Fig-D8: Overlay of all cooling scans with vertical offset."""
    fmt = config.fig_format if config else 'svg'
    dpi = config.fig_dpi if config else 300
    fig_dir, _ = _make_output_dirs(output_dir)

    cooling = [r for r in results
               if r.technique == 'cooling' and len(r.T) > 0]
    if len(cooling) < 2:
        return ""

    fig, ax = plt.subplots(figsize=(7.2, 4.5))

    hf_ranges = [float(np.ptp(r.HF)) for r in cooling]
    max_range = max(hf_ranges) if hf_ranges else 1.0
    offset_step = max_range * 1.2

    colors_used = [SCI_PALETTE[i % len(SCI_PALETTE)] for i in range(len(cooling))]
    for i, r in enumerate(cooling):
        offset = (len(cooling) - 1 - i) * offset_step
        color = colors_used[i]
        label = _short_sample_name(r.label)
        ax.plot(r.T, r.HF + offset, color=color, linewidth=1.2, label=label)

        if not np.isnan(r.Tc_peak_C):
            hf_at_peak = np.interp(r.Tc_peak_C, r.T, r.HF) + offset
            ax.annotate(f"{r.Tc_peak_C:.0f}°C",
                        xy=(r.Tc_peak_C, hf_at_peak),
                        xytext=(5, 8), textcoords='offset points',
                        fontsize=7, color=color,
                        arrowprops=dict(arrowstyle='->', color=color, lw=0.7))

    ax.legend(fontsize=8, framealpha=0.9, loc='upper left',
              bbox_to_anchor=(1.01, 1), borderaxespad=0)
    ax.set_yticks([])

    set_sci_style(fig, ax,
                  xlabel='Temperature (°C)',
                  ylabel='Heat Flow (offset)  exo ↑',
                  title='')

    path = _save_figure(fig, fname, fig_dir, fmt, dpi)
    _save_batch_overlay_document(
        path,
        cooling,
        figure_id=Path(path).resolve().stem,
        function_name="fig_batch_cooling_overlay",
        scan_type="cooling",
    )
    return path


def fig_batch_crystallinity(results: List[DSCResult], output_dir: str,
                             config: Optional[DSCConfig] = None,
                             fname: str = 'Fig-D3_crystallinity_comparison',
                             ) -> str:
    """Cross-sample crystallinity comparison bar chart (batch mode).

    Groups scans by sample, showing first-heat and second-heat Xc side by side.
    """
    fmt = config.fig_format if config else 'svg'
    dpi = config.fig_dpi if config else 300
    fig_dir, _ = _make_output_dirs(output_dir)

    # Collect scans with valid Xc
    valid = [(r, r.Xc_pct) for r in results
             if not np.isnan(r.Xc_pct) and r.Xc_pct > 0]
    if not valid:
        return ""

    labels = [_short_sample_name(r.label) for r, _ in valid]
    xc = [v for _, v in valid]

    fig, ax = plt.subplots(figsize=(5.5, 3.5))
    colors = [SCI_PALETTE[i % len(SCI_PALETTE)] for i in range(len(labels))]
    bars = ax.bar(range(len(labels)), xc, color=colors, edgecolor='white',
                  linewidth=0.5)

    for bar, val in zip(bars, xc):
        ax.text(bar.get_x() + bar.get_width() / 2.0,
                bar.get_height() + max(xc) * 0.03,
                f'{val:.1f}%', ha='center', va='bottom',
                fontsize=8, fontweight='bold')

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha='right', fontsize=8)
    ymax = max(xc) * 1.2 if max(xc) > 0 else 1.0
    ax.set_ylim(0, ymax)

    set_sci_style(fig, ax,
                  ylabel='Crystallinity $X_c$ (%)',
                  title='')

    path = _save_figure(fig, fname, fig_dir, fmt, dpi)
    _save_batch_crystallinity_document(path, valid, labels, Path(path).resolve().stem)
    return path


# ---------------------------------------------------------------------------
#  Full figure generation
# ---------------------------------------------------------------------------

def generate_all_figures(results: List[DSCResult],
                         output_dir: str,
                         config: Optional[DSCConfig] = None,
                         kinetics_data: Optional[Dict[str, Any]] = None,
                         ) -> Dict[str, str]:
    """Generate all DSC figures and export data.

    Organizes output into:
        figures/main/  — batch overlay comparisons, crystallinity (P1)
        figures/SI/    — per-scan thermograms, Tg zoom, deconvolution (P2/P3)

    Returns dict mapping figure name → filepath.
    """
    figures: Dict[str, str] = {}
    base_fig_dir, data_dir = _make_output_dirs(output_dir)
    main_dir = os.path.join(base_fig_dir, 'main')
    si_dir = os.path.join(base_fig_dir, 'SI')
    os.makedirs(main_dir, exist_ok=True)
    os.makedirs(si_dir, exist_ok=True)

    def _safe_fig(fn, *args):
        try:
            return fn(*args)
        except Exception as exc:
            import sys as _sys
            _sys.stderr.write(f"DSC figure {fn.__name__} failed: {exc}\n")
            logger.warning("DSC figure generation failed.", exc_info=True)
            return ""

    # ── Per-scan figures → SI/ ──────────────────────────────────────────
    for result in results:
        prefix = result.label.replace(' ', '_').replace('/', '_')

        p = _safe_fig(fig_d1_full_curve, result, output_dir, config,
                      f'SI/{prefix}_Fig-D1_full_curve')
        if p:
            figures[f'{prefix}_full_curve'] = p

        p = _safe_fig(fig_d2_tg_zoom, result, output_dir, config,
                      f'SI/{prefix}_Fig-D2_Tg_zoom')
        if p:
            figures[f'{prefix}_tg_zoom'] = p

        p = _safe_fig(fig_d6_deconvolution, result, output_dir, config,
                      f'SI/{prefix}_Fig-D6_deconvolution')
        if p:
            figures[f'{prefix}_deconvolution'] = p

    # ── Batch / comparison figures → main/ ──────────────────────────────
    if len(results) > 1:
        # Crystallinity comparison
        p = _safe_fig(fig_batch_crystallinity, results, output_dir, config,
                      'main/Fig-D3_crystallinity_comparison')
        if p:
            figures['crystallinity_comparison'] = p

        # Heating curve overlay
        p = _safe_fig(fig_batch_heating_overlay, results, output_dir, config,
                      'main/Fig-D7_heating_overlay')
        if p:
            figures['heating_overlay'] = p

        # Cooling curve overlay
        p = _safe_fig(fig_batch_cooling_overlay, results, output_dir, config,
                      'main/Fig-D8_cooling_overlay')
        if p:
            figures['cooling_overlay'] = p

    # ── Kinetics figures → main/ ────────────────────────────────────────
    if kinetics_data:
        if 'avrami' in kinetics_data:
            p = _safe_fig(fig_d4_avrami, kinetics_data['avrami'], main_dir, config)
            if p:
                figures['avrami'] = p
        if 'kissinger' in kinetics_data:
            p = _safe_fig(fig_d5_kissinger, kinetics_data['kissinger'], [], [], main_dir, config)
            if p:
                figures['kissinger'] = p

    # Export CSV (always, even if figures failed)
    try:
        export_parameters_csv(results, output_dir)
    except Exception as exc:
        import sys as _sys
        _sys.stderr.write(f"CSV export failed: {exc}\n")
        logger.warning("DSC parameters CSV export failed.", exc_info=True)
    try:
        export_detailed_peaks_csv(results, output_dir)
    except Exception as exc:
        import sys as _sys
        _sys.stderr.write(f"Peaks CSV export failed: {exc}\n")
        logger.warning("DSC detailed peaks CSV export failed.", exc_info=True)
    # Cross-sample summary table (batch mode)
    if len(results) > 1:
        try:
            export_all_results_csv(results, output_dir)
        except Exception as exc:
            import sys as _sys
            _sys.stderr.write(f"Summary CSV export failed: {exc}\n")
            logger.warning("DSC summary CSV export failed.", exc_info=True)

    # ── Generate analysis report ─────────────────────────────────────────
    try:
        from polynexus.core.report import generate_report
        report_dir = os.path.join(output_dir, 'report')
        os.makedirs(report_dir, exist_ok=True)
        html = generate_report(
            project_name="DSC Analysis",
            output_dir=output_dir,
            dsc_results=results,
        )
        if html:
            with open(os.path.join(report_dir, 'analysis_report.html'),
                      'w', encoding='utf-8') as f:
                f.write(html)
    except Exception as exc:
        import sys as _sys
        _sys.stderr.write(f"Report generation failed: {exc}\n")
        logger.warning("DSC analysis report generation failed.", exc_info=True)

    return figures
