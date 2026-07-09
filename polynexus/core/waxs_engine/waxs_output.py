"""WAXS output module: SCI-quality figure generation."""

import csv
import sys
import os
from pathlib import Path
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
plt.rcParams['svg.fonttype'] = 'none'  # Qt SVG compatibility: embed text, not font refs

# If the GUI thread already imported pyplot with a GUI backend,
# matplotlib.use('Agg') has no effect.  Switch at runtime in each
# figure function via the _ensure_agg helper below.
def _ensure_agg():
    """Switch to non-interactive Agg backend (safe to call repeatedly)."""
    matplotlib.use('Agg')

from typing import Dict, List, Optional, Tuple, Any

from .core import WAXSResult
from .config import WAXSConfig
from ..figure_document import save_generated_figure_document
from ..plot_edits import savefig_with_edits
from ...plotting.sci_style import (
    set_sci_style as _global_set_sci_style,
    apply_axis_sci_style,
    WONG_COLORS, ANNOTATION_COLORS,
    FIG_SIZES, AXIS_LABELS,
    save_figure_sci,
)
try:
    from ..generated_figure_document_builder import save_generated_figure_bundle
except Exception:  # pragma: no cover - compatibility for branches without Phase 3 builder
    save_generated_figure_bundle = None


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


def _downsample_plot(x, y, max_pts=800):
    """Downsample data for plotting to keep SVG path sizes manageable."""
    if len(x) <= max_pts:
        return x, y
    indices = np.linspace(0, len(x) - 1, max_pts, dtype=int)
    return x[indices], y[indices]


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
        spine.set_linewidth(0.8)
        spine.set_color('#333333')
    ax.grid(True, alpha=0.2, linestyle='--', linewidth=0.5)


def _make_output_dirs(output_dir):
    _ensure_agg()
    fig_dir = os.path.join(output_dir, 'figures')
    data_dir = os.path.join(output_dir, 'data')
    os.makedirs(fig_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)
    return fig_dir, data_dir


def _save_figure(fig, name, fig_dir, fmt='svg', dpi=300):
    path = os.path.join(fig_dir, f'{name}.{fmt}')
    savefig_with_edits(fig, path, dpi=dpi, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
    plt.close(fig)
    return path


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


def _save_w1_profile_document(path: str, result: WAXSResult) -> None:
    data_path = _write_w1_profile_data(path, result)
    data_ref = "waxs-profile-data"
    objects = [
        {
            "id": "series-measured",
            "type": "plot_series",
            "name": "Measured",
            "data_ref": data_ref,
            "x_column": "two_theta",
            "y_column": "intensity",
            "style": {"color": SCI_COLORS["dark"], "line_width": 1.0},
        }
    ]
    if len(result.I_fit) > 0:
        objects.append(
            {
                "id": "series-fitted",
                "type": "plot_series",
                "name": "Fitted",
                "data_ref": data_ref,
                "x_column": "two_theta",
                "y_column": "fit",
                "style": {"color": SCI_COLORS["red"], "line_width": 1.2},
            }
        )
    save_generated_figure_document(
        path,
        technique="waxs",
        figure_id="Fig-W1_profile",
        data_sources=[
            {
                "id": data_ref,
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": "polynexus.core.waxs_engine.waxs_output",
            "function": "fig_w1_profile",
            "inputs": {"result_label": str(result.label or "")},
        },
        style={
            "xlabel": "2theta (deg)",
            "ylabel": "Intensity (a.u.)",
            "residual_ylabel": "Residual",
        },
        objects=objects,
    )


def _save_w2_amorphous_document(path: str, result: WAXSResult) -> None:
    data_path = _write_w2_amorphous_data(path, result)
    data_ref = "waxs-amorphous-data"
    objects = [
        {
            "id": "series-total",
            "type": "plot_series",
            "name": "Total",
            "data_ref": data_ref,
            "x_column": "two_theta",
            "y_column": "intensity",
            "style": {"color": SCI_COLORS["dark"], "line_width": 1.0},
        }
    ]
    if len(result.I_amorphous) > 0:
        objects.append(
            {
                "id": "series-amorphous",
                "type": "plot_series",
                "name": "Amorphous",
                "data_ref": data_ref,
                "x_column": "two_theta",
                "y_column": "amorphous",
                "style": {
                    "color": SCI_COLORS["orange"],
                    "line_width": 1.0,
                    "alpha": 0.3,
                    "fill": SCI_COLORS["orange"],
                },
            }
        )
    if len(result.I_crystalline) > 0:
        objects.append(
            {
                "id": "series-crystalline",
                "type": "plot_series",
                "name": "Crystalline",
                "data_ref": data_ref,
                "x_column": "two_theta",
                "y_column": "crystalline",
                "style": {
                    "color": SCI_COLORS["blue"],
                    "line_width": 1.0,
                    "alpha": 0.3,
                    "fill": SCI_COLORS["blue"],
                },
            }
        )
    save_generated_figure_document(
        path,
        technique="waxs",
        figure_id="Fig-W2_amorphous",
        data_sources=[
            {
                "id": data_ref,
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": "polynexus.core.waxs_engine.waxs_output",
            "function": "fig_w2_amorphous",
            "inputs": {"result_label": str(result.label or "")},
            "parameters": {
                "Xc_pct": _json_number(result.Xc_pct),
                "Xc_method": str(result.Xc_method or ""),
            },
        },
        style={
            "xlabel": "2theta (deg)",
            "ylabel": "Intensity (a.u.)",
            "fill_components": True,
        },
        objects=objects,
    )


def _save_w3_williamson_hall_document(
    path: str,
    result: WAXSResult,
    *,
    x_values: np.ndarray,
    y_values: np.ndarray,
    fit_x: np.ndarray,
    fit_y: np.ndarray,
    slope: float,
    intercept: float,
    r_squared: float,
    wavelength_A: float,
) -> None:
    data_path = _write_w3_williamson_hall_data(path, x_values, y_values, fit_x, fit_y)
    data_ref = "waxs-williamson-hall-data"
    _save_generated_figure_bundle_compat(
        path,
        technique="waxs",
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
            "function": "fig_w3_williamson_hall",
            "inputs": {"result_label": str(result.label or "")},
            "parameters": {
                "slope": _json_number(slope),
                "intercept": _json_number(intercept),
                "r_squared": _json_number(r_squared),
                "wavelength_A": _json_number(wavelength_A),
                "D_WH_nm": _json_number(result.D_WH_nm),
                "epsilon_WH_pct": _json_number(result.epsilon_WH_pct),
            },
        },
        style={
            "xlabel": "4 sin(theta)",
            "ylabel": "beta cos(theta) (rad)",
        },
        objects=[
            {
                "id": "series-wh-points",
                "type": "plot_series",
                "name": "Williamson-Hall Points",
                "data_ref": data_ref,
                "x_column": "four_sin_theta",
                "y_column": "beta_cos_theta",
                "style": {"color": SCI_COLORS["blue"], "marker": "o", "line_width": 0.0},
            },
            {
                "id": "series-wh-fit",
                "type": "plot_series",
                "name": "Williamson-Hall Fit",
                "data_ref": data_ref,
                "x_column": "fit_x",
                "y_column": "fit",
                "style": {"color": SCI_COLORS["red"], "line_width": 1.2},
            },
        ],
    )


def _save_w4_crystallinity_document(path: str, results: List[WAXSResult]) -> None:
    data_path = _write_w4_crystallinity_data(path, results)
    data_ref = "waxs-crystallinity-data"
    save_generated_figure_document(
        path,
        technique="waxs",
        figure_id="Fig-W4_crystallinity",
        data_sources=[
            {
                "id": data_ref,
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": "polynexus.core.waxs_engine.waxs_output",
            "function": "fig_w4_crystallinity",
            "inputs": {"result_labels": [str(result.label or "") for result in results]},
            "parameters": {"sample_count": len(results)},
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


def _save_w5_scherrer_document(
    path: str,
    result: WAXSResult,
    *,
    labels: List[str],
    sizes: List[float],
    wavelength_A: float,
    scherrer_K: float,
) -> None:
    data_path = _write_w5_scherrer_data(path, result, labels, sizes)
    data_ref = "waxs-scherrer-data"
    mean_size = float(np.mean(sizes)) if sizes else np.nan
    save_generated_figure_document(
        path,
        technique="waxs",
        figure_id="Fig-W5_scherrer",
        data_sources=[
            {
                "id": data_ref,
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": "polynexus.core.waxs_engine.waxs_output",
            "function": "fig_w5_scherrer",
            "inputs": {"result_label": str(result.label or "")},
            "parameters": {
                "peak_count": len(sizes),
                "mean_D_nm": _json_number(mean_size),
                "wavelength_A": _json_number(wavelength_A),
                "scherrer_K": _json_number(scherrer_K),
                "D_Scherrer_nm": _json_number(result.D_Scherrer_nm),
            },
        },
        style={
            "xlabel": "Peak position 2theta (deg)",
            "ylabel": "Crystallite size (nm)",
            "show_mean_line": True,
        },
        objects=[
            {
                "id": "series-scherrer-size",
                "type": "plot_series",
                "chart_kind": "bar",
                "name": "Scherrer Size",
                "data_ref": data_ref,
                "x_column": "label",
                "y_column": "D_nm",
                "style": {"palette": SCI_PALETTE, "line_width": 0.5, "stroke": "#FFFFFF"},
            },
            {
                "id": "line-mean-size",
                "type": "line",
                "name": "Mean Scherrer Size",
                "orientation": "horizontal",
                "y": _json_number(mean_size),
                "label": f"Mean = {mean_size:.1f} nm" if np.isfinite(mean_size) else "",
                "style": {"color": SCI_COLORS["red"], "line_width": 1.0},
            },
        ],
    )


def _save_strain_waterfall_document(path: str, strain_result, *, indices: List[int]) -> None:
    data_path = _write_strain_waterfall_data(path, strain_result, indices)
    data_ref = "waxs-strain-waterfall-data"
    objects = []
    for index in indices:
        if index >= len(strain_result.point_results):
            continue
        point = strain_result.point_results[index]
        waxs_result = point.waxs_result
        if waxs_result is None or len(waxs_result.two_theta) == 0:
            continue
        objects.append(
            {
                "id": f"series-strain-{index}",
                "type": "plot_series",
                "name": f"Strain {point.strain_pct:.0f}%",
                "data_ref": data_ref,
                "x_column": "two_theta",
                "y_column": "intensity_offset",
                "filter": {"frame_index": index},
                "style": {"line_width": 0.7},
            }
        )
    save_generated_figure_document(
        path,
        technique="waxs",
        figure_id="Fig-S2_waterfall",
        data_sources=[
            {
                "id": data_ref,
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": "polynexus.core.waxs_engine.waxs_output",
            "function": "fig_strain_waterfall",
            "inputs": {"result_label": str(strain_result.label or "")},
            "parameters": {
                "strain_count": len(strain_result.point_results),
                "selected_count": len(objects),
            },
        },
        style={
            "xlabel": "2theta (deg)",
            "ylabel": "Intensity (offset, a.u.)",
            "panels": ["waterfall", "key strains overlay"],
        },
        objects=objects,
    )


def _save_strain_parameters_document(path: str, strain_result) -> None:
    data_path = _write_strain_parameters_data(path, strain_result)
    data_ref = "waxs-strain-parameters-data"
    objects = [
        {
            "id": "series-xc",
            "type": "plot_series",
            "name": "Crystallinity Xc",
            "data_ref": data_ref,
            "x_column": "strain_pct",
            "y_column": "Xc_pct",
            "style": {"color": SCI_COLORS["blue"], "line_width": 1.2},
        },
        {
            "id": "series-scherrer-size",
            "type": "plot_series",
            "name": "Scherrer Size",
            "data_ref": data_ref,
            "x_column": "strain_pct",
            "y_column": "D_Scherrer_nm",
            "style": {"color": SCI_COLORS["red"], "line_width": 1.2},
        },
        {
            "id": "series-herman-mean",
            "type": "plot_series",
            "name": "Herman Mean",
            "data_ref": data_ref,
            "x_column": "strain_pct",
            "y_column": "f_Herman_avg",
            "style": {"color": SCI_COLORS["dark"], "line_width": 1.2},
        },
        {
            "id": "series-microstrain",
            "type": "plot_series",
            "name": "W-H Micro-strain",
            "data_ref": data_ref,
            "x_column": "strain_pct",
            "y_column": "epsilon_WH_pct",
            "style": {"color": SCI_COLORS["green"], "line_width": 1.2},
        },
    ]
    if any(np.isfinite(getattr(point, "D_WH_nm", np.nan)) for point in strain_result.point_results):
        objects.append(
            {
                "id": "series-wh-size",
                "type": "plot_series",
                "name": "Williamson-Hall Size",
                "data_ref": data_ref,
                "x_column": "strain_pct",
                "y_column": "D_WH_nm",
                "style": {"color": SCI_COLORS["purple"], "line_width": 1.0, "line_style": "--"},
            }
        )
    save_generated_figure_document(
        path,
        technique="waxs",
        figure_id="Fig-S3_parameters",
        data_sources=[
            {
                "id": data_ref,
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": "polynexus.core.waxs_engine.waxs_output",
            "function": "fig_strain_parameters",
            "inputs": {"result_label": str(strain_result.label or "")},
            "parameters": {"strain_count": len(strain_result.point_results)},
        },
        style={
            "xlabel": "Strain (%)",
            "panels": ["crystallinity", "crystallite size", "orientation", "micro-strain"],
        },
        objects=objects,
    )


def _save_strain_lattice_document(path: str, strain_result, *, key_indices: List[int]) -> None:
    lattice_path = _write_strain_lattice_data(path, strain_result)
    wh_path = _write_strain_wh_data(path, strain_result, key_indices)
    lattice_ref = "waxs-strain-lattice-data"
    wh_ref = "waxs-strain-wh-data"
    objects = [
        {
            "id": "series-lattice-strain",
            "type": "plot_series",
            "name": "Lattice Strain",
            "data_ref": lattice_ref,
            "x_column": "strain_pct",
            "y_column": "lattice_strain_pct",
            "group_column": "hkl",
            "style": {"palette": SCI_PALETTE, "line_width": 1.0},
        },
        {
            "id": "series-wh-points",
            "type": "plot_series",
            "chart_kind": "scatter",
            "name": "Williamson-Hall Points",
            "data_ref": wh_ref,
            "x_column": "four_sin_theta",
            "y_column": "beta_cos_theta",
            "group_column": "strain_pct",
            "style": {"palette": SCI_PALETTE, "marker_size": 25},
        },
    ]
    save_generated_figure_document(
        path,
        technique="waxs",
        figure_id="Fig-S4_lattice_strain",
        data_sources=[
            {
                "id": lattice_ref,
                "kind": "csv",
                "path": str(lattice_path),
                "role": "plot_data",
            },
            {
                "id": wh_ref,
                "kind": "csv",
                "path": str(wh_path),
                "role": "plot_data",
            },
        ],
        recipe={
            "module": "polynexus.core.waxs_engine.waxs_output",
            "function": "fig_strain_lattice",
            "inputs": {"result_label": str(strain_result.label or "")},
            "parameters": {
                "strain_count": len(strain_result.point_results),
                "selected_wh_count": len(key_indices),
            },
        },
        style={
            "xlabel": "Strain (%)",
            "ylabel": "Delta d/d0 (%)",
            "panels": ["lattice strain", "Williamson-Hall evolution"],
        },
        objects=objects,
    )


def _save_strain_2d_patterns_document(
    path: str,
    selected: list,
    *,
    n_rows: int,
    n_cols: int,
) -> None:
    metadata_path, image_paths = _write_strain_2d_patterns_data(path, selected, n_cols=n_cols)
    metadata_ref = "waxs-strain-2d-patterns-metadata"
    data_sources = [
        {
            "id": metadata_ref,
            "kind": "csv",
            "path": str(metadata_path),
            "role": "plot_data",
        }
    ]
    for index, image_path in enumerate(image_paths):
        data_sources.append(
            {
                "id": f"pattern-image-{index + 1}",
                "kind": "npy",
                "path": str(image_path),
                "role": "image_data",
            }
        )
    save_generated_figure_document(
        path,
        technique="waxs",
        figure_id=Path(path).resolve().stem,
        data_sources=data_sources,
        recipe={
            "module": "polynexus.core.waxs_engine.waxs_output",
            "function": "fig_strain_2d_patterns_from_scans",
            "inputs": {},
            "parameters": {
                "selected_count": len(selected),
                "n_rows": n_rows,
                "n_cols": n_cols,
            },
        },
        style={
            "layout": "image_grid",
            "colormap": "inferno",
            "origin": "lower",
        },
        objects=[
            {
                "id": "series-pattern-grid",
                "type": "plot_series",
                "chart_kind": "image_grid",
                "name": "2D WAXS Pattern Grid",
                "data_ref": metadata_ref,
                "row_column": "grid_row",
                "column_column": "grid_col",
                "image_path_column": "image_path",
                "label_column": "strain_pct",
                "style": {"colormap": "inferno"},
            }
        ],
    )


def _write_w1_profile_data(path: str, result: WAXSResult) -> Path:
    figure_path = Path(path).resolve()
    output_root = figure_path.parent.parent
    data_dir = output_root / "data" / "figure_sources"
    data_dir.mkdir(parents=True, exist_ok=True)
    data_path = data_dir / f"{figure_path.stem}_data.csv"
    fit = result.I_fit if len(result.I_fit) == len(result.two_theta) else []
    amorphous = result.I_amorphous if len(result.I_amorphous) == len(result.two_theta) else []
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["two_theta", "intensity", "fit", "amorphous"],
        )
        writer.writeheader()
        for index, two_theta in enumerate(result.two_theta):
            writer.writerow(
                {
                    "two_theta": _csv_number(two_theta),
                    "intensity": _csv_number(result.I[index]),
                    "fit": _csv_number(fit[index]) if len(fit) else "",
                    "amorphous": _csv_number(amorphous[index]) if len(amorphous) else "",
                }
            )
    return data_path


def _write_w2_amorphous_data(path: str, result: WAXSResult) -> Path:
    figure_path = Path(path).resolve()
    output_root = figure_path.parent.parent
    data_dir = output_root / "data" / "figure_sources"
    data_dir.mkdir(parents=True, exist_ok=True)
    data_path = data_dir / f"{figure_path.stem}_data.csv"
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["two_theta", "intensity", "amorphous", "crystalline"],
        )
        writer.writeheader()
        for index, two_theta in enumerate(result.two_theta):
            writer.writerow(
                {
                    "two_theta": _csv_number(two_theta),
                    "intensity": _csv_number(result.I[index]),
                    "amorphous": _csv_number(result.I_amorphous[index])
                    if len(result.I_amorphous)
                    else "",
                    "crystalline": _csv_number(result.I_crystalline[index])
                    if len(result.I_crystalline)
                    else "",
                }
            )
    return data_path


def _write_w3_williamson_hall_data(
    path: str,
    x_values: np.ndarray,
    y_values: np.ndarray,
    fit_x: np.ndarray,
    fit_y: np.ndarray,
) -> Path:
    figure_path = Path(path).resolve()
    output_root = figure_path.parent.parent
    data_dir = output_root / "data" / "figure_sources"
    data_dir.mkdir(parents=True, exist_ok=True)
    data_path = data_dir / f"{figure_path.stem}_data.csv"
    rows = max(len(x_values), len(fit_x))
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["four_sin_theta", "beta_cos_theta", "fit_x", "fit"],
        )
        writer.writeheader()
        for index in range(rows):
            writer.writerow(
                {
                    "four_sin_theta": _csv_number(x_values[index])
                    if index < len(x_values)
                    else "",
                    "beta_cos_theta": _csv_number(y_values[index])
                    if index < len(y_values)
                    else "",
                    "fit_x": _csv_number(fit_x[index]) if index < len(fit_x) else "",
                    "fit": _csv_number(fit_y[index]) if index < len(fit_y) else "",
                }
            )
    return data_path


def _write_w4_crystallinity_data(path: str, results: List[WAXSResult]) -> Path:
    figure_path = Path(path).resolve()
    output_root = figure_path.parent.parent
    data_dir = output_root / "data" / "figure_sources"
    data_dir.mkdir(parents=True, exist_ok=True)
    data_path = data_dir / f"{figure_path.stem}_data.csv"
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["label", "Xc_pct", "Xc_method"])
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "label": str(result.label or ""),
                    "Xc_pct": _csv_number(result.Xc_pct) if np.isfinite(result.Xc_pct) else "",
                    "Xc_method": str(result.Xc_method or ""),
                }
            )
    return data_path


def _write_w5_scherrer_data(
    path: str,
    result: WAXSResult,
    labels: List[str],
    sizes: List[float],
) -> Path:
    figure_path = Path(path).resolve()
    output_root = figure_path.parent.parent
    data_dir = output_root / "data" / "figure_sources"
    data_dir.mkdir(parents=True, exist_ok=True)
    data_path = data_dir / f"{figure_path.stem}_data.csv"
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["label", "two_theta", "fwhm_deg", "D_nm"],
        )
        writer.writeheader()
        for index, size in enumerate(sizes):
            peak = result.peaks[index] if index < len(result.peaks) else {}
            writer.writerow(
                {
                    "label": labels[index] if index < len(labels) else "",
                    "two_theta": _csv_number(peak.get("two_theta", np.nan)),
                    "fwhm_deg": _csv_number(peak.get("fwhm_deg", np.nan)),
                    "D_nm": _csv_number(size),
                }
            )
    return data_path


def _write_strain_2d_patterns_data(path: str, selected: list, *, n_cols: int) -> tuple[Path, List[Path]]:
    figure_path = Path(path).resolve()
    output_root = figure_path.parent.parent
    data_dir = output_root / "data" / "figure_sources"
    image_dir = data_dir / f"{figure_path.stem}_images"
    image_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = data_dir / f"{figure_path.stem}_data.csv"
    image_paths: List[Path] = []
    with metadata_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "grid_index",
                "grid_row",
                "grid_col",
                "source_index",
                "strain_pct",
                "image_path",
                "height_px",
                "width_px",
            ],
        )
        writer.writeheader()
        for grid_index, (source_index, scan, strain_pct) in enumerate(selected):
            image = np.asarray(scan.image)
            image_path = image_dir / f"pattern_{grid_index + 1:03d}.npy"
            np.save(image_path, image)
            image_paths.append(image_path)
            writer.writerow(
                {
                    "grid_index": grid_index,
                    "grid_row": grid_index // max(int(n_cols), 1),
                    "grid_col": grid_index % max(int(n_cols), 1),
                    "source_index": source_index,
                    "strain_pct": _csv_number(strain_pct),
                    "image_path": str(image_path),
                    "height_px": int(image.shape[0]) if image.ndim >= 2 else 0,
                    "width_px": int(image.shape[1]) if image.ndim >= 2 else 0,
                }
            )
    return metadata_path, image_paths


def _write_strain_waterfall_data(path: str, strain_result, indices: List[int]) -> Path:
    figure_path = Path(path).resolve()
    output_root = figure_path.parent.parent
    data_dir = output_root / "data" / "figure_sources"
    data_dir.mkdir(parents=True, exist_ok=True)
    data_path = data_dir / f"{figure_path.stem}_data.csv"
    max_intensity = 0.0
    for index in indices:
        point = strain_result.point_results[index]
        waxs_result = point.waxs_result
        if waxs_result is not None and len(waxs_result.I) > 0:
            max_intensity = max(max_intensity, float(np.nanmax(waxs_result.I)))
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "frame_index",
                "strain_pct",
                "two_theta",
                "intensity",
                "intensity_offset",
            ],
        )
        writer.writeheader()
        offset_step = 0.0
        for index in indices:
            point = strain_result.point_results[index]
            waxs_result = point.waxs_result
            if waxs_result is None or len(waxs_result.two_theta) == 0:
                continue
            for two_theta, intensity in zip(waxs_result.two_theta, waxs_result.I):
                writer.writerow(
                    {
                        "frame_index": index,
                        "strain_pct": _csv_number(point.strain_pct),
                        "two_theta": _csv_number(two_theta),
                        "intensity": _csv_number(intensity),
                        "intensity_offset": _csv_number(
                            float(intensity) + offset_step * max_intensity * 0.25
                        ),
                    }
                )
            offset_step += 1.0
    return data_path


def _write_strain_parameters_data(path: str, strain_result) -> Path:
    figure_path = Path(path).resolve()
    output_root = figure_path.parent.parent
    data_dir = output_root / "data" / "figure_sources"
    data_dir.mkdir(parents=True, exist_ok=True)
    data_path = data_dir / f"{figure_path.stem}_data.csv"
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "strain_pct",
                "phase",
                "Xc_pct",
                "D_Scherrer_nm",
                "D_WH_nm",
                "f_Herman_avg",
                "epsilon_WH_pct",
            ],
        )
        writer.writeheader()
        for index, point in enumerate(strain_result.point_results):
            writer.writerow(
                {
                    "strain_pct": _csv_number(point.strain_pct),
                    "phase": point.phase.name if hasattr(point.phase, "name") else str(point.phase or ""),
                    "Xc_pct": _finite_csv(point.Xc_pct),
                    "D_Scherrer_nm": _finite_csv(point.D_Scherrer_nm),
                    "D_WH_nm": _finite_csv(point.D_WH_nm),
                    "f_Herman_avg": _finite_csv(point.f_Herman_avg),
                    "epsilon_WH_pct": _finite_csv(point.epsilon_WH_pct),
                }
            )
    return data_path


def _write_strain_lattice_data(path: str, strain_result) -> Path:
    figure_path = Path(path).resolve()
    output_root = figure_path.parent.parent
    data_dir = output_root / "data" / "figure_sources"
    data_dir.mkdir(parents=True, exist_ok=True)
    data_path = data_dir / f"{figure_path.stem}_lattice_data.csv"
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["strain_pct", "hkl", "lattice_strain", "lattice_strain_pct"],
        )
        writer.writeheader()
        for point in strain_result.point_results:
            for hkl, value in point.lattice_strain_per_peak.items():
                writer.writerow(
                    {
                        "strain_pct": _csv_number(point.strain_pct),
                        "hkl": str(hkl or ""),
                        "lattice_strain": _finite_csv(value),
                        "lattice_strain_pct": _finite_csv(float(value) * 100.0),
                    }
                )
    return data_path


def _write_strain_wh_data(path: str, strain_result, key_indices: List[int]) -> Path:
    figure_path = Path(path).resolve()
    output_root = figure_path.parent.parent
    data_dir = output_root / "data" / "figure_sources"
    data_dir.mkdir(parents=True, exist_ok=True)
    data_path = data_dir / f"{figure_path.stem}_wh_data.csv"
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "frame_index",
                "strain_pct",
                "four_sin_theta",
                "beta_cos_theta",
                "two_theta",
                "fwhm_deg",
            ],
        )
        writer.writeheader()
        for index in key_indices:
            if index >= len(strain_result.point_results):
                continue
            point = strain_result.point_results[index]
            waxs_result = point.waxs_result
            if waxs_result is None:
                continue
            for peak in waxs_result.peaks:
                fwhm = peak.get("fwhm_deg", np.nan)
                two_theta = peak.get("two_theta", np.nan)
                if np.isnan(fwhm) or np.isnan(two_theta) or fwhm <= 0:
                    continue
                beta_rad = np.radians(fwhm)
                theta = np.radians(two_theta / 2.0)
                writer.writerow(
                    {
                        "frame_index": index,
                        "strain_pct": _csv_number(point.strain_pct),
                        "four_sin_theta": _csv_number(4.0 * np.sin(theta)),
                        "beta_cos_theta": _csv_number(beta_rad * np.cos(theta)),
                        "two_theta": _csv_number(two_theta),
                        "fwhm_deg": _csv_number(fwhm),
                    }
                )
    return data_path


def _csv_number(value) -> float:
    return round(float(value), 10)


def _finite_csv(value):
    return _csv_number(value) if np.isfinite(value) else ""


def _json_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(number):
        return None
    return number


# ---------------------------------------------------------------------------
#  Fig-W1: Full WAXS profile with peak fitting
# ---------------------------------------------------------------------------

def fig_w1_profile(result: WAXSResult, output_dir: str,
                   config: Optional[WAXSConfig] = None) -> str:
    """Fig-W1: 1D WAXS profile with fitted peaks and residual."""
    fmt = config.fig_format if config else 'svg'
    dpi = config.fig_dpi if config else 300
    fig_dir, _ = _make_output_dirs(output_dir)

    if len(result.two_theta) == 0:
        print(f"[WAXS] Fig-W1 skipped: no two_theta data for '{result.label}'", file=sys.stderr)
        return ""

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6.8, 5.5),
                                    gridspec_kw={'height_ratios': [3, 1]})

    tth = result.two_theta
    I = result.I

    # Top: profile
    tth_plot, I_plot = _downsample_plot(tth, I)
    ax1.plot(tth_plot, I_plot, color=SCI_COLORS['dark'], linewidth=1.0, label='Measured')

    if len(result.I_fit) > 0:
        I_fit_plot = _downsample_plot(tth, result.I_fit)[1]
        ax1.plot(tth_plot, I_fit_plot, color=SCI_COLORS['red'], linewidth=1.2,
                 linestyle='--', label=f'Fitted ($R^2$={result.r_squared:.3f})')

    # Individual peaks
    for i, pk in enumerate(result.peaks):
        color = SCI_PALETTE[i % len(SCI_PALETTE)]
        mu = pk['two_theta']
        amp = pk['height']
        ax1.axvline(mu, color=color, linestyle=':', linewidth=0.6, alpha=0.5)
        hkl = pk.get('hkl', '')
        ax1.annotate(f"{mu:.1f}°\n{hkl}" if hkl else f"{mu:.1f}°",
                     xy=(mu, amp), xytext=(0, 5), textcoords='offset points',
                     fontsize=6, color=color, ha='center')

    # Amorphous halo
    if len(result.I_amorphous) > 0:
        am_plot = _downsample_plot(tth, result.I_amorphous)[1]
        ax1.fill_between(tth_plot, 0, am_plot, alpha=0.15,
                         color=SCI_COLORS['grey'], label='Amorphous')

    ax1.legend(fontsize=7, framealpha=0.9, loc='upper right')
    set_sci_style(fig, ax1, ylabel='Intensity (a.u.)')

    # Bottom: residual
    if len(result.I_fit) > 0:
        residual = I_plot - I_fit_plot
        ax2.plot(tth_plot, residual, color=SCI_COLORS['grey'], linewidth=0.8)
        ax2.axhline(0, color=SCI_COLORS['dark'], linewidth=0.5, linestyle='--')

    set_sci_style(fig, ax2, xlabel='2θ (°)', ylabel='Residual')

    pass  # suptitle removed for SCI (goes in caption)

    path = _save_figure(fig, 'Fig-W1_profile', fig_dir, fmt, dpi)
    _save_w1_profile_document(path, result)
    return path


# ---------------------------------------------------------------------------
#  Fig-W2: Amorphous subtraction + crystallinity
# ---------------------------------------------------------------------------

def fig_w2_amorphous(result: WAXSResult, output_dir: str,
                     config: Optional[WAXSConfig] = None) -> str:
    """Fig-W2: Amorphous subtraction showing crystalline + amorphous components."""
    fmt = config.fig_format if config else 'svg'
    dpi = config.fig_dpi if config else 300
    fig_dir, _ = _make_output_dirs(output_dir)

    if len(result.two_theta) == 0:
        print(f"[WAXS] Fig-W2 skipped: no two_theta data for '{result.label}'", file=sys.stderr)
        return ""

    fig, ax = plt.subplots(figsize=(5.5, 3.8))

    tth = result.two_theta
    tth_plot, I_plot = _downsample_plot(tth, result.I)

    ax.plot(tth_plot, I_plot, color=SCI_COLORS['dark'], linewidth=1.0,
            label='Total')

    if len(result.I_amorphous) > 0:
        am_plot = _downsample_plot(tth, result.I_amorphous)[1]
        ax.fill_between(tth_plot, 0, am_plot, alpha=0.3,
                        color=SCI_COLORS['orange'], label='Amorphous')

    if len(result.I_crystalline) > 0:
        cr_plot = _downsample_plot(tth, result.I_crystalline)[1]
        ax.fill_between(tth_plot, am_plot if len(result.I_amorphous) > 0 else 0,
                        am_plot + cr_plot if len(result.I_amorphous) > 0 else cr_plot,
                        alpha=0.3, color=SCI_COLORS['blue'],
                        label='Crystalline')

    if not np.isnan(result.Xc_pct):
        ax.text(0.98, 0.95, f"$X_c$ = {result.Xc_pct:.1f}%",
                transform=ax.transAxes, ha='right', va='top',
                fontsize=10, fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    ax.legend(fontsize=8, framealpha=0.9)
    set_sci_style(fig, ax, xlabel='2θ (°)', ylabel='Intensity (a.u.)',
                  title=f'Amorphous Subtraction — {result.label}')

    path = _save_figure(fig, 'Fig-W2_amorphous', fig_dir, fmt, dpi)
    _save_w2_amorphous_document(path, result)
    return path


# ---------------------------------------------------------------------------
#  Fig-W3: Williamson-Hall plot
# ---------------------------------------------------------------------------

def fig_w3_williamson_hall(result: WAXSResult, output_dir: str,
                           config: Optional[WAXSConfig] = None) -> str:
    """Fig-W3: Williamson-Hall plot."""
    fmt = config.fig_format if config else 'svg'
    dpi = config.fig_dpi if config else 300
    fig_dir, _ = _make_output_dirs(output_dir)

    if len(result.peaks) < 2:
        print(f"[WAXS] Fig-W3 skipped: need >=2 peaks, got {len(result.peaks)} for '{result.label}'", file=sys.stderr)
        return ""

    fig, ax = plt.subplots(figsize=(4.5, 3.5))

    wavelength = config.wavelength_A if config else 1.5406

    x_vals, y_vals, labels = [], [], []
    for i, pk in enumerate(result.peaks):
        fwhm = pk.get('fwhm_deg', np.nan)
        tth = pk.get('two_theta', np.nan)
        if np.isnan(fwhm) or np.isnan(tth) or fwhm <= 0:
            continue
        beta_rad = np.radians(fwhm)
        theta = np.radians(tth / 2.0)
        x_vals.append(4.0 * np.sin(theta))
        y_vals.append(beta_rad * np.cos(theta))
        labels.append(f"{tth:.1f}°")

    if len(x_vals) < 2:
        print(f"[WAXS] Fig-W3 skipped: only {len(x_vals)} valid FWHM values for '{result.label}'", file=sys.stderr)
        return ""

    x_arr = np.array(x_vals)
    y_arr = np.array(y_vals)

    if np.allclose(x_arr, x_arr[0]) or np.allclose(y_arr, y_arr[0]):
        return ""

    colors = [SCI_PALETTE[i % len(SCI_PALETTE)] for i in range(len(x_arr))]
    ax.scatter(x_arr, y_arr, c=colors, s=40,
                edgecolors='white', linewidth=0.8, zorder=5)

    for xi, yi, lbl in zip(x_arr, y_arr, labels):
        ax.annotate(lbl, (xi, yi), textcoords='offset points',
                    xytext=(5, 5), fontsize=7)

    # Linear fit
    import scipy.stats
    slope, intercept, r, _, _ = scipy.stats.linregress(x_arr, y_arr)
    x_fit = np.linspace(x_arr.min() * 0.9, x_arr.max() * 1.1, 100)
    y_fit = slope * x_fit + intercept
    ax.plot(x_fit, y_fit, '--', color=SCI_COLORS['red'], linewidth=1.2)

    D_nm = 0.9 * wavelength / (intercept * 10.0) if intercept > 0 else np.nan
    eps_pct = slope * 100.0

    ax.text(0.95, 0.05,
            f"$D$ = {D_nm:.1f} nm\n$\\varepsilon$ = {eps_pct:.2f}%\n$R^2$ = {r**2:.4f}",
            transform=ax.transAxes, ha='right', va='bottom',
            fontsize=8, bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    set_sci_style(fig, ax,
                  xlabel='4 sin(θ)',
                  ylabel='β cos(θ) (rad)',
                  title='Williamson-Hall Plot')

    path = _save_figure(fig, 'Fig-W3_williamson_hall', fig_dir, fmt, dpi)
    _save_w3_williamson_hall_document(
        path,
        result,
        x_values=x_arr,
        y_values=y_arr,
        fit_x=x_fit,
        fit_y=y_fit,
        slope=slope,
        intercept=intercept,
        r_squared=r**2,
        wavelength_A=wavelength,
    )
    return path


# ---------------------------------------------------------------------------
#  Fig-W4: Crystallinity comparison bar chart
# ---------------------------------------------------------------------------

def fig_w4_crystallinity(results: List[WAXSResult], output_dir: str,
                         config: Optional[WAXSConfig] = None) -> str:
    """Fig-W4: Crystallinity comparison across samples."""
    fmt = config.fig_format if config else 'svg'
    dpi = config.fig_dpi if config else 300
    fig_dir, _ = _make_output_dirs(output_dir)

    labels = [r.label for r in results]
    xc = [r.Xc_pct for r in results]

    fig, ax = plt.subplots(figsize=(5.5, 3.5))

    colors = [SCI_PALETTE[i % len(SCI_PALETTE)] for i in range(len(labels))]
    bars = ax.bar(range(len(labels)), xc, color=colors, edgecolor='white',
                  linewidth=0.5)

    for bar, val in zip(bars, xc):
        if not np.isnan(val):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                    f'{val:.1f}%', ha='center', va='bottom', fontsize=8,
                    fontweight='bold')

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha='right', fontsize=8)
    ax.set_ylim(0, max([v for v in xc if not np.isnan(v)] + [50]) * 1.15)

    set_sci_style(fig, ax, ylabel='Crystallinity $X_c$ (%)',
                  title='WAXS Crystallinity Comparison')

    path = _save_figure(fig, 'Fig-W4_crystallinity', fig_dir, fmt, dpi)
    _save_w4_crystallinity_document(path, results)
    return path


# ---------------------------------------------------------------------------
#  Fig-W5: Scherrer size per peak
# ---------------------------------------------------------------------------

def fig_w5_scherrer(result: WAXSResult, output_dir: str,
                    config: Optional[WAXSConfig] = None) -> str:
    """Fig-W5: Crystallite size from each peak (Scherrer)."""
    fmt = config.fig_format if config else 'svg'
    dpi = config.fig_dpi if config else 300
    fig_dir, _ = _make_output_dirs(output_dir)

    if not result.peaks:
        print(f"[WAXS] Fig-W5 skipped: no peaks for '{result.label}'", file=sys.stderr)
        return ""

    wavelength = config.wavelength_A if config else 1.5406
    K = config.scherrer_K if config else 0.9

    labels, sizes = [], []
    for pk in result.peaks:
        fwhm = pk.get('fwhm_deg', np.nan)
        tth = pk.get('two_theta', np.nan)
        if np.isnan(fwhm) or np.isnan(tth) or fwhm <= 0:
            continue
        beta_rad = np.radians(fwhm)
        theta = np.radians(tth / 2.0)
        D = K * wavelength / (beta_rad * np.cos(theta)) / 10.0
        if not np.isnan(D):
            labels.append(f"{tth:.1f}°")
            sizes.append(D)

    if not sizes:
        return ""

    fig, ax = plt.subplots(figsize=(5.0, 3.2))
    colors = [SCI_PALETTE[i % len(SCI_PALETTE)] for i in range(len(labels))]
    ax.bar(range(len(labels)), sizes, color=colors, edgecolor='white',
           linewidth=0.5)

    for i, (lbl, sz) in enumerate(zip(labels, sizes)):
        ax.text(i, sz + max(sizes) * 0.02, f'{sz:.1f}',
                ha='center', fontsize=8)

    ax.axhline(np.mean(sizes), color=SCI_COLORS['red'], linestyle='--',
               linewidth=1.0, label=f'Mean = {np.mean(sizes):.1f} nm')
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels)
    ax.legend(fontsize=8)

    set_sci_style(fig, ax, xlabel='Peak position 2θ (°)',
                  ylabel='Crystallite size (nm)',
                  title=f'Scherrer Size — {result.label}')

    path = _save_figure(fig, 'Fig-W5_scherrer', fig_dir, fmt, dpi)
    _save_w5_scherrer_document(
        path,
        result,
        labels=labels,
        sizes=sizes,
        wavelength_A=wavelength,
        scherrer_K=K,
    )
    return path


# ---------------------------------------------------------------------------
#  Export
# ---------------------------------------------------------------------------

def export_parameters_csv(results: List[WAXSResult], output_dir: str) -> str:
    import pandas as pd
    import time
    _, data_dir = _make_output_dirs(output_dir)
    rows = [r.parameters for r in results]
    df = pd.DataFrame(rows)
    path = os.path.join(data_dir, 'waxs_parameters.csv')
    try:
        df.to_csv(path, index=False)
    except PermissionError:
        # File locked (e.g. open in Excel) — write to a timestamped copy
        ts = time.strftime('%Y%m%d_%H%M%S')
        alt_path = os.path.join(data_dir, f'waxs_parameters_{ts}.csv')
        df.to_csv(alt_path, index=False)
        print(f"[waxs] CSV saved to {alt_path} (original was locked)", flush=True)
        return alt_path
    return path


def generate_all_figures(results: List[WAXSResult], output_dir: str,
                         config: Optional[WAXSConfig] = None,
                         ) -> Dict[str, str]:
    """Generate all WAXS figures."""
    figures = {}

    for result in results:
        prefix = result.label.replace(' ', '_').replace('/', '_')

        p = fig_w1_profile(result, output_dir, config)
        if p:
            figures[f'{prefix}_profile'] = p

        p = fig_w2_amorphous(result, output_dir, config)
        if p:
            figures[f'{prefix}_amorphous'] = p

        p = fig_w3_williamson_hall(result, output_dir, config)
        if p:
            figures[f'{prefix}_wh'] = p

        p = fig_w5_scherrer(result, output_dir, config)
        if p:
            figures[f'{prefix}_scherrer'] = p

    if len(results) > 1:
        p = fig_w4_crystallinity(results, output_dir, config)
        if p:
            figures['crystallinity_comparison'] = p

    export_parameters_csv(results, output_dir)

    return figures


# ======================================================================
#  In-situ strain figures  —  SCI publication quality
# ======================================================================

# Phase -> display metadata
STRAIN_PHASE_META = {
    "ELASTIC":                {"label": "I  Elastic",        "color": "#e0f2fe"},
    "PLASTIC_REFINEMENT":     {"label": "II Plastic Refine", "color": "#fef3c7"},
    "STRESS_INDUCED_CRYST":   {"label": "III Stress-Cryst",  "color": "#fce7f3"},
    "FRACTURE_SATURATION":    {"label": "IV Fracture/Sat.",  "color": "#fee2e2"},
}


def _add_phase_background(ax, strain_result, x_max):
    """Paint phase-coloured vertical spans behind data."""
    if strain_result is None or not strain_result.point_results:
        return
    boundaries = strain_result.phase_boundaries
    if not boundaries:
        return
    sorted_bnd = sorted(
        [(v, k.name) for k, v in boundaries.items() if np.isfinite(v)],
        key=lambda x: x[0],
    )
    prev_x = 0.0
    for x_val, phase_name in sorted_bnd:
        color = STRAIN_PHASE_META.get(phase_name, {}).get("color", "#f0f0f0")
        ax.axvspan(prev_x, x_val, alpha=0.18, color=color, linewidth=0)
        prev_x = x_val
    if x_max > prev_x:
        last_color = list(STRAIN_PHASE_META.values())[-1]["color"]
        ax.axvspan(prev_x, x_max, alpha=0.18, color=last_color, linewidth=0)


# ------------------------------------------------------------------
#  Fig-S1: 2D WAXS pattern sequence
# ------------------------------------------------------------------

def fig_strain_2d_patterns_from_scans(
    scans,
    strains,
    output_dir: str,
    config=None,
    n_cols: int = 4,
    n_rows: int = 2,
) -> str:
    """Fig-S1: 2D pattern grid from scan list.

    Selects evenly-spaced frames and renders 2D diffraction images
    as a grid (default 2 rows x 4 cols).  Log-scale intensity colormap.
    """
    fmt = config.fig_format if config else "pdf"
    dpi = config.fig_dpi if config else 300
    fig_dir, _ = _make_output_dirs(output_dir)

    indexed = [(i, s, e) for i, (s, e) in enumerate(zip(scans, strains))
               if s.image is not None]
    if len(indexed) < 2:
        return ""

    n_cells = n_rows * n_cols
    if len(indexed) <= n_cells:
        selected = indexed
    else:
        step = len(indexed) / n_cells
        selected = [indexed[int(i * step)] for i in range(n_cells)]

    fig, axes = plt.subplots(n_rows, n_cols,
                             figsize=(8.0, 4.5),
                             gridspec_kw={"wspace": 0.08, "hspace": 0.15})
    axes = axes.flatten()

    for ax, (_orig_idx, scan, eps) in zip(axes, selected):
        img = scan.image
        vmin = np.percentile(img[img > 0], 5) if np.any(img > 0) else 1
        vmax = np.percentile(img, 99.5)
        ax.imshow(img, cmap="inferno", vmin=vmin, vmax=vmax,
                  origin="lower", aspect="equal")
        ax.set_title(f"ε = {eps:.0f}%", fontsize=7)
        ax.set_xticks([])
        ax.set_yticks([])

    for j in range(len(selected), len(axes)):
        axes[j].set_visible(False)

    fig.suptitle("2D WAXS Pattern Evolution with Strain",
                 fontsize=10, fontweight="bold", y=1.01)

    path = _save_figure(fig, "Fig-S1_2D_patterns", fig_dir, fmt, dpi)
    _save_strain_2d_patterns_document(path, selected, n_rows=n_rows, n_cols=n_cols)
    return path


# ------------------------------------------------------------------
#  Fig-S2: 1D diffraction waterfall
# ------------------------------------------------------------------

def fig_strain_waterfall(
    strain_result,
    output_dir: str,
    config=None,
    n_curves: int = 12,
) -> str:
    """Fig-S2: 1D WAXS profile waterfall.

    Two-panel layout:
        (a) Full waterfall with offset curves, colour-coded by strain
        (b) First / mid / last strain overlay
    """
    fmt = config.fig_format if config else "pdf"
    dpi = config.fig_dpi if config else 300
    fig_dir, _ = _make_output_dirs(output_dir)

    if not strain_result.point_results:
        return ""

    strains_arr = np.array(strain_result.strains)
    n_total = len(strain_result.point_results)

    if n_total <= n_curves:
        indices = list(range(n_total))
    else:
        step = max(1, n_total // n_curves)
        indices = list(range(0, n_total, step))
        if indices[-1] != n_total - 1:
            indices.append(n_total - 1)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.0, 4.0))

    cmap = plt.cm.plasma
    norm = plt.Normalize(strains_arr[indices[0]], strains_arr[indices[-1]])

    # ---- (a) Waterfall ----
    offset_step = 0.0
    max_I = 0.0
    for idx in indices:
        wr = strain_result.point_results[idx].waxs_result
        if wr is None or len(wr.two_theta) == 0:
            continue
        max_I = max(max_I, np.nanmax(wr.I))

    for idx in indices:
        sp = strain_result.point_results[idx]
        wr = sp.waxs_result
        if wr is None or len(wr.two_theta) == 0:
            continue
        I_off = wr.I + offset_step * max_I * 0.25
        ax1.plot(wr.two_theta, I_off, color=cmap(norm(sp.strain_pct)),
                 linewidth=0.7,
                 label=f"{sp.strain_pct:.0f}%" if idx % 2 == 0 else "")
        offset_step += 1.0

    ax1.set_xlabel("2θ (°)")
    ax1.set_ylabel("Intensity (offset, a.u.)")
    ax1.set_title("(a) Diffraction Waterfall")
    ax1.legend(fontsize=6, ncol=2, loc="upper right", framealpha=0.6)

    # ---- (b) Key strains overlay ----
    key_idx = [0, n_total // 2, n_total - 1] if n_total >= 3 else list(range(n_total))
    key_colors = [SCI_COLORS["blue"], SCI_COLORS["orange"], SCI_COLORS["red"]]
    for ki, (idx, c) in enumerate(zip(key_idx, key_colors[:len(key_idx)])):
        sp = strain_result.point_results[idx]
        wr = sp.waxs_result
        if wr is None or len(wr.two_theta) == 0:
            continue
        ax2.plot(wr.two_theta, wr.I, color=c, linewidth=1.0,
                 label=f"ε = {sp.strain_pct:.0f}%")
    ax2.set_xlabel("2θ (°)")
    ax2.set_ylabel("Intensity (a.u.)")
    ax2.set_title("(b) Key Strains Overlay")
    ax2.legend(fontsize=7, framealpha=0.8)

    for ax in (ax1, ax2):
        ax.tick_params(direction="in", top=True, right=True, labelsize=7)
        for spine in ax.spines.values():
            spine.set_linewidth(0.6)

    fig.suptitle(f"WAXS Strain Evolution — {strain_result.label}",
                 fontsize=10, fontweight="bold", y=1.02)
    plt.tight_layout()

    path = _save_figure(fig, "Fig-S2_waterfall", fig_dir, fmt, dpi)
    _save_strain_waterfall_document(path, strain_result, indices=indices)
    return path


# ------------------------------------------------------------------
#  Fig-S3: Structural parameter evolution  (core figure)
# ------------------------------------------------------------------

def fig_strain_parameters(
    strain_result,
    output_dir: str,
    config=None,
) -> str:
    """Fig-S3: Multi-panel structural parameter evolution vs strain.

    2x2 layout:
        (a) Crystallinity Xc vs ε
        (b) Crystallite size D vs ε  (Scherrer + W-H)
        (c) Herman orientation factor vs ε  (per-hkl curves + mean)
        (d) Williamson-Hall micro-strain ε_WH vs ε

    Phase backgrounds behind each panel.
    """
    fmt = config.fig_format if config else "pdf"
    dpi = config.fig_dpi if config else 300
    fig_dir, _ = _make_output_dirs(output_dir)

    if not strain_result.point_results:
        return ""

    strains = np.array(strain_result.strains)
    Xc = strain_result.Xc_array
    D = strain_result.D_array
    fH = strain_result.f_Herman_array
    eWH = strain_result.epsilon_WH_array
    x_max = np.nanmax(strains) * 1.05 if len(strains) > 0 else 100

    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.6))
    axes = axes.flatten()

    # -- (a) Crystallinity --
    ax = axes[0]
    ax.plot(strains, Xc, "o-", color=SCI_COLORS["blue"],
            markersize=4, linewidth=1.2)
    _add_phase_background(ax, strain_result, x_max)
    ax.set_xlabel("ε (%)")
    ax.set_ylabel("Xc (%)")
    ax.set_title("(a) Crystallinity")
    ax.tick_params(direction="in", top=True, right=True, labelsize=7)

    # -- (b) Crystallite size --
    ax = axes[1]
    ax.plot(strains, D, "s-", color=SCI_COLORS["red"],
            markersize=4, linewidth=1.2, label="Scherrer")
    D_WH_arr = np.array([p.D_WH_nm for p in strain_result.point_results])
    if np.any(np.isfinite(D_WH_arr)):
        ax.plot(strains, D_WH_arr, "^--", color=SCI_COLORS["purple"],
                markersize=3, linewidth=1.0, label="W-H")
    _add_phase_background(ax, strain_result, x_max)
    ax.set_xlabel("ε (%)")
    ax.set_ylabel("D (nm)")
    ax.set_title("(b) Crystallite Size")
    ax.legend(fontsize=6, framealpha=0.7)
    ax.tick_params(direction="in", top=True, right=True, labelsize=7)

    # -- (c) Herman orientation factor --
    ax = axes[2]
    hkl_series = {}
    for sp in strain_result.point_results:
        for hkl, f_val in sp.f_Herman_per_peak.items():
            hkl_series.setdefault(hkl, []).append(f_val)
    n_curves = len(hkl_series)
    palette = SCI_PALETTE[:max(n_curves, 1)]
    for (hkl, vals), color in zip(hkl_series.items(), palette):
        ax.plot(strains[:len(vals)], vals, "o-", color=color,
                markersize=3, linewidth=1.0, label=hkl)
    if np.any(np.isfinite(fH)):
        ax.plot(strains, fH, "D-", color=SCI_COLORS["dark"],
                markersize=3, linewidth=1.2, label="mean")
    ax.axhline(0, color="grey", linewidth=0.5, linestyle=":")
    _add_phase_background(ax, strain_result, x_max)
    ax.set_xlabel("ε (%)")
    ax.set_ylabel("f  Herman")
    ax.set_title("(c) Orientation Factor")
    ax.legend(fontsize=5, ncol=2, framealpha=0.6)
    ax.tick_params(direction="in", top=True, right=True, labelsize=7)

    # -- (d) Williamson-Hall micro-strain --
    ax = axes[3]
    ax.plot(strains, eWH, "o-", color=SCI_COLORS["green"],
            markersize=4, linewidth=1.2)
    _add_phase_background(ax, strain_result, x_max)
    ax.set_xlabel("ε (%)")
    ax.set_ylabel("ε_WH (%)")
    ax.set_title("(d) Micro-strain (W-H)")
    ax.tick_params(direction="in", top=True, right=True, labelsize=7)

    fig.suptitle(f"Structural Parameter Evolution — {strain_result.label}",
                 fontsize=10, fontweight="bold", y=1.02)

    # Phase legend at bottom
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=m["color"], alpha=0.35, label=m["label"])
        for m in STRAIN_PHASE_META.values()
    ]
    fig.legend(handles=legend_elements, loc="lower center",
               ncol=4, fontsize=6, framealpha=0.7)

    plt.tight_layout(rect=[0, 0.06, 1, 0.97])

    path = _save_figure(fig, "Fig-S3_parameters", fig_dir, fmt, dpi)
    _save_strain_parameters_document(path, strain_result)
    return path


# ------------------------------------------------------------------
#  Fig-S4: Lattice strain analysis
# ------------------------------------------------------------------

def fig_strain_lattice(
    strain_result,
    output_dir: str,
    config=None,
) -> str:
    """Fig-S4: Lattice strain and Williamson-Hall evolution.

    Two-panel:
        (a) Lattice strain Δd/d₀ vs macroscopic strain ε  (per hkl)
        (b) Williamson-Hall parameters across selected strains
    """
    fmt = config.fig_format if config else "pdf"
    dpi = config.fig_dpi if config else 300
    fig_dir, _ = _make_output_dirs(output_dir)

    if not strain_result.point_results:
        return ""

    strains = np.array(strain_result.strains)
    x_max = np.nanmax(strains) * 1.05 if len(strains) > 0 else 100

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.5))

    # -- (a) Lattice strain vs macro strain --
    lattice_series = {}
    for sp in strain_result.point_results:
        for hkl, ls in sp.lattice_strain_per_peak.items():
            lattice_series.setdefault(hkl, []).append(ls)

    n_curves = len(lattice_series)
    palette = SCI_PALETTE[:max(n_curves, 1)]
    for (hkl, vals), color in zip(lattice_series.items(), palette):
        s_arr = strains[:len(vals)]
        v_arr = np.array(vals)
        valid = np.isfinite(v_arr)
        if valid.sum() > 1:
            ax1.plot(s_arr[valid], v_arr[valid] * 100, "o-",
                     color=color, markersize=3, linewidth=1.0,
                     label=hkl)
    # Elastic reference line
    ax1.plot([0, x_max], [0, x_max], "--", color="grey",
             linewidth=0.7, alpha=0.5, label="elastic (Δd/d₀ = ε)")
    ax1.set_xlabel("ε  (%)")
    ax1.set_ylabel("Δd/d₀  (%)")
    ax1.set_title("(a) Lattice vs Macro Strain")
    ax1.legend(fontsize=6, framealpha=0.7)
    ax1.tick_params(direction="in", top=True, right=True, labelsize=7)

    # -- (b) W-H parameter evolution --
    n_total = len(strain_result.point_results)
    key_idx = (
        [0, n_total // 3, 2 * n_total // 3, n_total - 1]
        if n_total >= 4
        else list(range(n_total))
    )
    key_idx = [i for i in key_idx if i < n_total]
    cmap = plt.cm.plasma
    norm = (plt.Normalize(strains[key_idx[0]], strains[key_idx[-1]])
            if key_idx else None)
    wavelength = config.wavelength_A if config else 1.5406

    for idx in key_idx:
        sp = strain_result.point_results[idx]
        wr = sp.waxs_result
        if wr is None or len(wr.peaks) < 2:
            continue
        x_vals, y_vals = [], []
        for pk in wr.peaks:
            fwhm = pk.get("fwhm_deg", np.nan)
            tth = pk.get("two_theta", np.nan)
            if np.isnan(fwhm) or np.isnan(tth) or fwhm <= 0:
                continue
            beta_rad = np.radians(fwhm)
            theta = np.radians(tth / 2.0)
            x_vals.append(4.0 * np.sin(theta))
            y_vals.append(beta_rad * np.cos(theta))
        if len(x_vals) < 2:
            continue
        color = cmap(norm(sp.strain_pct)) if norm else SCI_COLORS["dark"]
        ax2.scatter(x_vals, y_vals, color=color, s=25,
                    edgecolors="white", linewidth=0.5, zorder=5)
        ax2.plot(x_vals, y_vals, "--", color=color, linewidth=0.5, alpha=0.4)
        ax2.annotate(f"{sp.strain_pct:.0f}%",
                     (x_vals[-1], y_vals[-1]),
                     textcoords="offset points", xytext=(3, 3),
                     fontsize=5, color=color)

    ax2.set_xlabel("4 sin θ")
    ax2.set_ylabel("β cos θ  (rad)")
    ax2.set_title("(b) W-H Evolution")
    ax2.tick_params(direction="in", top=True, right=True, labelsize=7)

    fig.suptitle(f"Lattice Strain Analysis — {strain_result.label}",
                 fontsize=10, fontweight="bold", y=1.03)
    plt.tight_layout()

    path = _save_figure(fig, "Fig-S4_lattice_strain", fig_dir, fmt, dpi)
    _save_strain_lattice_document(path, strain_result, key_indices=key_idx)
    return path


# ------------------------------------------------------------------
#  Batch strain figure generator
# ------------------------------------------------------------------

def generate_strain_figures(
    strain_result,
    scans=None,
    output_dir: str = "",
    config=None,
) -> Dict[str, str]:
    """Generate all strain-series SCI figures.

    Parameters
    ----------
    strain_result : WAXSStrainSeriesResult
    scans : list of WAXSScan, optional  (needed for S1 2D patterns)
    output_dir : str
    config : WAXSConfig, optional

    Returns
    -------
    dict : {figure_key: saved_path}
    """
    figures = {}

    if scans:
        p = fig_strain_2d_patterns_from_scans(
            scans, strain_result.strains, output_dir, config,
        )
        if p:
            figures["S1_2d_patterns"] = p

    p = fig_strain_waterfall(strain_result, output_dir, config)
    if p:
        figures["S2_waterfall"] = p

    p = fig_strain_parameters(strain_result, output_dir, config)
    if p:
        figures["S3_parameters"] = p

    p = fig_strain_lattice(strain_result, output_dir, config)
    if p:
        figures["S4_lattice_strain"] = p

    export_strain_csv(strain_result, output_dir)

    return figures


def export_strain_csv(strain_result, output_dir: str) -> str:
    """Export strain-series parameters as CSV."""
    import pandas as pd
    _, data_dir = _make_output_dirs(output_dir)
    df = strain_result.to_dataframe()
    path = os.path.join(data_dir, "waxs_strain_parameters.csv")
    df.to_csv(path, index=False)
    return path
