from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from ..figure_document import save_generated_figure_document
from .saxs_output_helpers import _json_number
from .saxs_output_data_writers import (
    _write_condition_overview_profile_data,
    _write_condition_overview_summary_data,
    _write_guinier_data,
    _write_joint_crystallinity_data,
    _write_kratky_data,
    _write_series_waterfall_data,
    _write_static_overview_profile_data,
    _write_static_overview_summary_data,
    _write_t3_structure_data,
    _write_t4_invariant_data,
    _write_v2_temperature_parameters_data,
    _write_v3_heatmap_data,
    _write_v3_qstar_data,
    _write_v4_avrami_data,
    _write_u1_scattering_data,
    _write_u2_correlation_data,
    _write_u3_idf_data,
    _write_u4_porod_data,
)


COLOR_SCHEMES = {
    "main": "#2563eb",
    "secondary": "#dc2626",
    "tertiary": "#16a34a",
    "highlight": "#9333ea",
    "grey": "#6b7280",
    "heatmap": "viridis",
    "heatmap_div": "RdBu_r",
    "heatmap_seq": "YlOrRd",
}


def _save_u1_scattering_document(
    path: str,
    q: np.ndarray,
    intensity: np.ndarray,
    *,
    q_star: Optional[float] = None,
    L: Optional[float] = None,
    label: str = "",
    log_scale: bool = True,
    is_low_conf: bool = False,
) -> None:
    data_path = _write_u1_scattering_data(path, q, intensity)
    data_ref = "saxs-scattering-data"
    save_generated_figure_document(
        path,
        technique="saxs",
        figure_id=Path(path).resolve().stem,
        data_sources=[
            {
                "id": data_ref,
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": "polynexus.core.saxs_engine.saxs_output",
            "function": "fig_u1_scattering_profile",
            "inputs": {"label": str(label or "")},
            "parameters": {
                "q_star": _json_number(q_star),
                "L": _json_number(L),
                "log_scale": bool(log_scale),
                "is_low_conf": bool(is_low_conf),
            },
        },
        style={
            "xlabel": "q (nm^-1)",
            "ylabel": "I(q) (a.u.)",
            "secondary_ylabel": "I(q) * q^2 (a.u.)",
            "x_scale": "log" if log_scale else "linear",
            "y_scale": "log",
        },
        objects=[
            {
                "id": "series-intensity",
                "type": "plot_series",
                "name": "I(q)",
                "data_ref": data_ref,
                "x_column": "q_nm_inv",
                "y_column": "intensity",
                "style": {"color": COLOR_SCHEMES["main"], "line_width": 1.0},
            },
            {
                "id": "series-lorentz",
                "type": "plot_series",
                "name": "I(q) q^2",
                "data_ref": data_ref,
                "x_column": "q_nm_inv",
                "y_column": "iq2",
                "style": {"color": COLOR_SCHEMES["main"], "line_width": 1.0},
            },
        ],
    )


def _save_u2_correlation_document(
    path: str,
    r: np.ndarray,
    gamma: np.ndarray,
    *,
    L: Optional[float] = None,
    lc: Optional[float] = None,
    is_low_conf: bool = False,
) -> None:
    data_path = _write_u2_correlation_data(path, r, gamma)
    data_ref = "saxs-correlation-data"
    objects = [
        {
            "id": "series-correlation",
            "type": "plot_series",
            "name": "Correlation Function",
            "data_ref": data_ref,
            "x_column": "r_nm",
            "y_column": "gamma",
            "style": {"color": COLOR_SCHEMES["main"], "line_width": 1.2},
        }
    ]
    L_value = _json_number(L)
    if L_value is not None:
        objects.append(
            {
                "id": "marker-L",
                "type": "line",
                "name": "Long Period L",
                "orientation": "vertical",
                "x": L_value,
                "label": f"L={L_value:.1f} nm",
                "style": {
                    "color": COLOR_SCHEMES["secondary"],
                    "line_width": 0.8,
                    "alpha": 0.7,
                },
            }
        )
    lc_value = _json_number(lc)
    if lc_value is not None:
        objects.append(
            {
                "id": "marker-lc",
                "type": "line",
                "name": "Correlation Length lc",
                "orientation": "vertical",
                "x": lc_value,
                "label": f"lc={lc_value:.1f} nm",
                "style": {
                    "color": COLOR_SCHEMES["tertiary"],
                    "line_width": 0.5,
                    "alpha": 0.7,
                },
            }
        )
    save_generated_figure_document(
        path,
        technique="saxs",
        figure_id=Path(path).resolve().stem,
        data_sources=[
            {
                "id": data_ref,
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": "polynexus.core.saxs_engine.saxs_output",
            "function": "fig_u2_correlation_function",
            "inputs": {},
            "parameters": {
                "L": L_value,
                "lc": lc_value,
                "is_low_conf": bool(is_low_conf),
            },
        },
        style={
            "xlabel": "r (nm)",
            "ylabel": "gamma(r)",
            "baseline_y": 0.0,
        },
        objects=objects,
    )


def _save_u3_idf_document(
    path: str,
    r_idf: np.ndarray,
    idf: np.ndarray,
    *,
    L_idf: Optional[float] = None,
    lc_idf: Optional[float] = None,
    is_low_conf: bool = False,
) -> None:
    data_path = _write_u3_idf_data(path, r_idf, idf)
    data_ref = "saxs-idf-data"
    objects = [
        {
            "id": "series-idf",
            "type": "plot_series",
            "name": "Interface Distribution Function",
            "data_ref": data_ref,
            "x_column": "r_nm",
            "y_column": "idf",
            "style": {"color": COLOR_SCHEMES["main"], "line_width": 1.2},
        }
    ]
    lc_value = _json_number(lc_idf)
    if lc_value is not None:
        objects.append(
            {
                "id": "marker-lc-idf",
                "type": "line",
                "name": "IDF Correlation Length lc",
                "orientation": "vertical",
                "x": lc_value,
                "label": f"lc={lc_value:.1f} nm",
                "style": {
                    "color": COLOR_SCHEMES["tertiary"],
                    "line_width": 0.8,
                    "alpha": 0.7,
                },
            }
        )
    L_value = _json_number(L_idf)
    if L_value is not None:
        objects.append(
            {
                "id": "marker-L-idf",
                "type": "line",
                "name": "IDF Long Period L",
                "orientation": "vertical",
                "x": L_value,
                "label": f"L={L_value:.1f} nm",
                "style": {
                    "color": COLOR_SCHEMES["secondary"],
                    "line_width": 0.8,
                    "alpha": 0.7,
                },
            }
        )
    save_generated_figure_document(
        path,
        technique="saxs",
        figure_id=Path(path).resolve().stem,
        data_sources=[
            {
                "id": data_ref,
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": "polynexus.core.saxs_engine.saxs_output",
            "function": "fig_u3_idf",
            "inputs": {},
            "parameters": {
                "L_idf": L_value,
                "lc_idf": lc_value,
                "is_low_conf": bool(is_low_conf),
            },
        },
        style={
            "xlabel": "r (nm)",
            "ylabel": "g1(r) (a.u.)",
            "baseline_y": 0.0,
            "fill_to_baseline": True,
        },
        objects=objects,
    )


def _save_u4_porod_document(
    path: str,
    q_porod: np.ndarray,
    Iq4: np.ndarray,
    *,
    slope: Optional[float] = None,
    Kp: Optional[float] = None,
    is_low_conf: bool = False,
) -> None:
    slope_value = _json_number(slope)
    Kp_value = _json_number(Kp)
    data_path = _write_u4_porod_data(path, q_porod, Iq4, slope=slope_value)
    data_ref = "saxs-porod-data"
    objects = [
        {
            "id": "series-porod",
            "type": "plot_series",
            "name": "Porod Plot",
            "data_ref": data_ref,
            "x_column": "q4_nm_minus4",
            "y_column": "Iq4",
            "style": {
                "color": COLOR_SCHEMES["main"],
                "marker": "o",
                "line_width": 0.0,
                "alpha": 0.5,
            },
        }
    ]
    if slope_value is not None:
        objects.append(
            {
                "id": "series-porod-fit",
                "type": "plot_series",
                "name": "Porod Fit",
                "data_ref": data_ref,
                "x_column": "q4_nm_minus4",
                "y_column": "fit",
                "style": {"color": COLOR_SCHEMES["secondary"], "line_width": 1.0},
            }
        )
    save_generated_figure_document(
        path,
        technique="saxs",
        figure_id=Path(path).resolve().stem,
        data_sources=[
            {
                "id": data_ref,
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": "polynexus.core.saxs_engine.saxs_output",
            "function": "fig_u4_porod",
            "inputs": {},
            "parameters": {
                "slope": slope_value,
                "Kp": Kp_value,
                "is_low_conf": bool(is_low_conf),
            },
        },
        style={
            "xlabel": "q^4 (nm^-4)",
            "ylabel": "I(q) * q^4 (a.u.)",
        },
        objects=objects,
    )


def _save_guinier_document(
    path: str,
    q: np.ndarray,
    intensity: np.ndarray,
    *,
    Rg: Optional[float] = None,
    q_min: float = 0.04,
    q_max: float = 0.15,
) -> None:
    q_sel = q[(q >= q_min) & (q <= q_max)]
    I_sel = intensity[(q >= q_min) & (q <= q_max)]
    pos = I_sel > 0
    slope = intercept = None
    if np.sum(pos) > 4:
        slope, intercept = np.polyfit(q_sel[pos] ** 2, np.log(I_sel[pos]), 1)
    data_path = _write_guinier_data(path, q_sel[pos], I_sel[pos], slope, intercept)
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
        }
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
    save_generated_figure_document(
        path,
        technique="saxs",
        figure_id=Path(path).resolve().stem,
        data_sources=[
            {
                "id": data_ref,
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": "polynexus.core.saxs_engine.saxs_output",
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


def _save_kratky_document(
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
        }
    ]
    if q_star is not None:
        objects.append(
            {
                "id": "marker-q-star",
                "type": "line",
                "name": "Lamellar q*",
                "orientation": "vertical",
                "x": _json_number(q_star),
                "label": f"q*={q_star:.3f} nm^-1",
                "style": {"color": COLOR_SCHEMES["secondary"], "line_width": 0.8, "alpha": 0.7},
            }
        )
    save_generated_figure_document(
        path,
        technique="saxs",
        figure_id=Path(path).resolve().stem,
        data_sources=[
            {
                "id": data_ref,
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": "polynexus.core.saxs_engine.saxs_output",
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


def _save_joint_crystallinity_document(
    path: str,
    techniques: List[str],
    values: List[float],
) -> None:
    data_path = _write_joint_crystallinity_data(path, techniques, values)
    data_ref = "saxs-joint-crystallinity-data"
    save_generated_figure_document(
        path,
        technique="saxs",
        figure_id=Path(path).resolve().stem,
        data_sources=[
            {
                "id": data_ref,
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": "polynexus.core.saxs_engine.saxs_output",
            "function": "fig_joint_crystallinity",
            "inputs": {},
            "parameters": {"technique_count": len(techniques)},
        },
        style={
            "xlabel": "Technique",
            "ylabel": "Crystallinity phi_c",
            "value_scale": "fraction",
        },
        objects=[
            {
                "id": "series-joint-crystallinity",
                "type": "plot_series",
                "chart_kind": "bar",
                "name": "Joint Crystallinity",
                "data_ref": data_ref,
                "x_column": "technique",
                "y_column": "phi_c",
                "style": {
                    "palette": [
                        COLOR_SCHEMES["main"],
                        COLOR_SCHEMES["secondary"],
                        COLOR_SCHEMES["tertiary"],
                    ],
                    "alpha": 0.85,
                },
            }
        ],
    )


def _save_series_waterfall_document(
    path: str,
    conditions: np.ndarray,
    q_list: List[np.ndarray],
    I_list: List[np.ndarray],
    *,
    indices: List[int],
    condition_axis: str,
    function_name: str,
) -> None:
    data_path = _write_series_waterfall_data(path, conditions, q_list, I_list, indices)
    data_ref = f"saxs-{condition_axis}-waterfall-data"
    objects = []
    for index in indices:
        if index >= len(conditions):
            continue
        objects.append(
            {
                "id": f"series-{condition_axis}-{index}",
                "type": "plot_series",
                "name": f"{conditions[index]:.0f}",
                "data_ref": data_ref,
                "x_column": "q_nm_inv",
                "y_column": "intensity_offset",
                "filter": {"condition_index": index},
                "style": {"line_width": 0.8},
            }
        )
    save_generated_figure_document(
        path,
        technique="saxs",
        figure_id=Path(path).resolve().stem,
        data_sources=[
            {
                "id": data_ref,
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": "polynexus.core.saxs_engine.saxs_output",
            "function": function_name,
            "inputs": {},
            "parameters": {
                "condition_axis": condition_axis,
                "condition_count": len(conditions),
                "selected_count": len(indices),
            },
        },
        style={
            "xlabel": "q (nm^-1)",
            "ylabel": "I(q) offset (a.u.)",
            "x_scale": "log",
            "y_scale": "log",
        },
        objects=objects,
    )


def _save_t3_structure_document(
    path: str,
    strains: np.ndarray,
    L_array: np.ndarray,
    lc_array: np.ndarray,
    *,
    phi_c_array: Optional[np.ndarray] = None,
    f_herman_array: Optional[np.ndarray] = None,
    Q_star_array: Optional[np.ndarray] = None,
) -> None:
    data_path = _write_t3_structure_data(path, strains, L_array, lc_array, phi_c_array, f_herman_array, Q_star_array)
    data_ref = "saxs-strain-structure-data"
    objects = [
        {
            "id": "series-L",
            "type": "plot_series",
            "name": "Long Period",
            "data_ref": data_ref,
            "x_column": "strain_pct",
            "y_column": "L_nm",
            "style": {"color": COLOR_SCHEMES["main"], "line_width": 1.2},
        },
        {
            "id": "series-lc",
            "type": "plot_series",
            "name": "Crystalline Thickness",
            "data_ref": data_ref,
            "x_column": "strain_pct",
            "y_column": "lc_nm",
            "style": {"color": COLOR_SCHEMES["secondary"], "line_width": 1.2},
        },
    ]
    if phi_c_array is not None and np.any(np.isfinite(phi_c_array)):
        objects.append(
            {
                "id": "series-phi-c",
                "type": "plot_series",
                "name": "Crystallinity",
                "data_ref": data_ref,
                "x_column": "strain_pct",
                "y_column": "phi_c",
                "style": {"color": COLOR_SCHEMES["highlight"], "line_width": 1.2},
            }
        )
    if Q_star_array is not None and np.any(np.isfinite(Q_star_array)):
        objects.append(
            {
                "id": "series-Q-star",
                "type": "plot_series",
                "name": "Scattering Invariant",
                "data_ref": data_ref,
                "x_column": "strain_pct",
                "y_column": "Q_star",
                "style": {"color": COLOR_SCHEMES["highlight"], "line_width": 1.2},
            }
        )
    if f_herman_array is not None and np.any(np.isfinite(f_herman_array)):
        objects.append(
            {
                "id": "series-herman",
                "type": "plot_series",
                "name": "Herman Factor",
                "data_ref": data_ref,
                "x_column": "strain_pct",
                "y_column": "f_Herman",
                "style": {"color": COLOR_SCHEMES["highlight"], "line_width": 1.2},
            }
        )
    if L_array is not None and lc_array is not None:
        objects.append(
            {
                "id": "series-la",
                "type": "plot_series",
                "name": "Amorphous Thickness",
                "data_ref": data_ref,
                "x_column": "strain_pct",
                "y_column": "la_nm",
                "style": {"color": COLOR_SCHEMES["tertiary"], "line_width": 1.0, "line_style": "--"},
            }
        )
    save_generated_figure_document(
        path,
        technique="saxs",
        figure_id=Path(path).resolve().stem,
        data_sources=[
            {
                "id": data_ref,
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": "polynexus.core.saxs_engine.saxs_output",
            "function": "fig_t3_structure_evolution",
            "inputs": {},
            "parameters": {"condition_count": len(strains)},
        },
        style={
            "xlabel": "Strain (%)",
            "panels": ["long period", "lamellar thickness", "crystallinity or invariant", "orientation"],
        },
        objects=objects,
    )


def _save_t4_invariant_document(
    path: str,
    strains: np.ndarray,
    Q_star_array: np.ndarray,
    *,
    Q_ref: Optional[float] = None,
    tolerance: float = 0.05,
) -> None:
    Q_norm = Q_star_array / Q_ref if Q_ref and Q_ref > 0 else Q_star_array
    data_path = _write_t4_invariant_data(path, strains, Q_star_array, Q_norm, tolerance)
    data_ref = "saxs-strain-invariant-data"
    save_generated_figure_document(
        path,
        technique="saxs",
        figure_id=Path(path).resolve().stem,
        data_sources=[
            {
                "id": data_ref,
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": "polynexus.core.saxs_engine.saxs_output",
            "function": "fig_t4_invariant_conservation",
            "inputs": {},
            "parameters": {
                "Q_ref": _json_number(Q_ref),
                "tolerance": _json_number(tolerance),
                "condition_count": len(strains),
            },
        },
        style={
            "xlabel": "Strain (%)",
            "ylabel": "Q* / Q*_0",
        },
        objects=[
            {
                "id": "tolerance-band",
                "type": "highlight",
                "name": "Invariant Tolerance",
                "data_ref": data_ref,
                "x_column": "strain_pct",
                "lower_y_column": "band_lower",
                "upper_y_column": "band_upper",
                "style": {"fill": COLOR_SCHEMES["tertiary"], "alpha": 0.1},
            },
            {
                "id": "series-Q-norm",
                "type": "plot_series",
                "name": "Normalized Invariant",
                "data_ref": data_ref,
                "x_column": "strain_pct",
                "y_column": "Q_norm",
                "style": {"color": COLOR_SCHEMES["main"], "line_width": 1.2},
            },
            {
                "id": "line-reference",
                "type": "line",
                "name": "Reference",
                "orientation": "horizontal",
                "y": 1.0,
                "style": {"color": "#000000", "line_width": 0.5, "line_style": ":"},
            },
        ],
    )


def _save_v2_temperature_parameters_document(
    path: str,
    temperatures: np.ndarray,
    L_array: np.ndarray,
    lc_array: np.ndarray,
    *,
    Q_star_array: Optional[np.ndarray] = None,
    Xc_array: Optional[np.ndarray] = None,
    Tm_values: Optional[Dict] = None,
) -> None:
    data_path = _write_v2_temperature_parameters_data(path, temperatures, L_array, lc_array, Q_star_array, Xc_array)
    data_ref = "saxs-temperature-parameters-data"
    objects = [
        {
            "id": "series-L",
            "type": "plot_series",
            "name": "Long Period",
            "data_ref": data_ref,
            "x_column": "temperature_C",
            "y_column": "L_nm",
            "style": {"color": COLOR_SCHEMES["main"], "line_width": 1.0},
        },
        {
            "id": "series-lc",
            "type": "plot_series",
            "name": "Crystalline Thickness",
            "data_ref": data_ref,
            "x_column": "temperature_C",
            "y_column": "lc_nm",
            "style": {"color": COLOR_SCHEMES["secondary"], "line_width": 1.0},
        },
    ]
    if Q_star_array is not None and np.any(np.isfinite(Q_star_array)):
        objects.append(
            {
                "id": "series-Q-star",
                "type": "plot_series",
                "name": "Scattering Invariant",
                "data_ref": data_ref,
                "x_column": "temperature_C",
                "y_column": "Q_star",
                "style": {"color": COLOR_SCHEMES["highlight"], "line_width": 1.0},
            }
        )
    if Xc_array is not None and np.any(np.isfinite(Xc_array)):
        objects.append(
            {
                "id": "series-Xc",
                "type": "plot_series",
                "name": "Relative Crystallinity",
                "data_ref": data_ref,
                "x_column": "temperature_C",
                "y_column": "Xc",
                "style": {"color": COLOR_SCHEMES["tertiary"], "line_width": 1.0},
            }
        )
    if L_array is not None and lc_array is not None:
        objects.append(
            {
                "id": "series-la",
                "type": "plot_series",
                "name": "Amorphous Thickness",
                "data_ref": data_ref,
                "x_column": "temperature_C",
                "y_column": "la_nm",
                "style": {"color": COLOR_SCHEMES["tertiary"], "line_width": 0.8, "line_style": "--"},
            }
        )
    if Tm_values:
        for key, value in Tm_values.items():
            if np.isfinite(value):
                objects.append(
                    {
                        "id": f"marker-{key}",
                        "type": "line",
                        "name": str(key),
                        "orientation": "vertical",
                        "x": _json_number(value),
                        "style": {"color": COLOR_SCHEMES["secondary"], "line_width": 0.5, "alpha": 0.5},
                    }
                )
    save_generated_figure_document(
        path,
        technique="saxs",
        figure_id=Path(path).resolve().stem,
        data_sources=[
            {
                "id": data_ref,
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": "polynexus.core.saxs_engine.saxs_output",
            "function": "fig_v2_temperature_parameters",
            "inputs": {},
            "parameters": {"condition_count": len(temperatures)},
        },
        style={
            "xlabel": "Temperature (C)",
            "panels": ["long period", "lamellar thickness", "invariant", "crystallinity"],
        },
        objects=objects,
    )


def _save_v4_avrami_document(
    path: str,
    times: np.ndarray,
    Xc_array: np.ndarray,
    *,
    avrami_result: Optional[Dict] = None,
) -> None:
    data_path = _write_v4_avrami_data(path, times, Xc_array, avrami_result)
    data_ref = "saxs-avrami-data"
    t_half = avrami_result.get("t_half_s", np.nan) if avrami_result else np.nan
    n_value = avrami_result.get("n", np.nan) if avrami_result else np.nan
    k_value = avrami_result.get("k_sn", np.nan) if avrami_result else np.nan
    objects = [
        {
            "id": "series-Xc",
            "type": "plot_series",
            "name": "Crystallinity",
            "data_ref": data_ref,
            "x_column": "time_s",
            "y_column": "Xc",
            "style": {"color": COLOR_SCHEMES["main"], "line_width": 1.0},
        }
    ]
    if np.isfinite(t_half):
        objects.append(
            {
                "id": "marker-t-half",
                "type": "line",
                "name": "Half crystallization time",
                "orientation": "vertical",
                "x": _json_number(t_half),
                "label": f"t1/2={t_half:.0f} s",
                "style": {"color": COLOR_SCHEMES["secondary"], "line_width": 0.8, "line_style": "--"},
            }
        )
    objects.append(
        {
            "id": "series-avrami-linear",
            "type": "plot_series",
            "chart_kind": "scatter",
            "name": "Avrami Linearized Data",
            "data_ref": data_ref,
            "x_column": "ln_time_s",
            "y_column": "avrami_y",
            "style": {"color": COLOR_SCHEMES["main"], "marker_size": 10, "alpha": 0.7},
        }
    )
    if avrami_result and avrami_result.get("valid") and np.isfinite(n_value) and np.isfinite(k_value):
        objects.append(
            {
                "id": "series-avrami-fit",
                "type": "plot_series",
                "name": "Avrami Fit",
                "data_ref": data_ref,
                "x_column": "fit_ln_time_s",
                "y_column": "fit",
                "style": {"color": COLOR_SCHEMES["secondary"], "line_width": 1.0},
            }
        )
    save_generated_figure_document(
        path,
        technique="saxs",
        figure_id=Path(path).resolve().stem,
        data_sources=[
            {
                "id": data_ref,
                "kind": "csv",
                "path": str(data_path),
                "role": "plot_data",
            }
        ],
        recipe={
            "module": "polynexus.core.saxs_engine.saxs_output",
            "function": "fig_v4_avrami",
            "inputs": {},
            "parameters": {
                "n": _json_number(n_value),
                "k_sn": _json_number(k_value),
                "t_half_s": _json_number(t_half),
                "valid": bool(avrami_result.get("valid")) if avrami_result else False,
            },
        },
        style={
            "panels": ["crystallization kinetics", "Avrami plot"],
            "time_unit": "s",
        },
        objects=objects,
    )


def _save_v3_heatmap_document(
    path: str,
    q: np.ndarray,
    temperatures: np.ndarray,
    I_matrix: np.ndarray,
    *,
    q_star_array: Optional[np.ndarray] = None,
    beamstop_q_min: float = 0.0,
) -> None:
    heatmap_path = _write_v3_heatmap_data(path, q, temperatures, I_matrix, beamstop_q_min)
    qstar_path = _write_v3_qstar_data(path, temperatures, q_star_array)
    heatmap_ref = "saxs-temperature-heatmap-data"
    qstar_ref = "saxs-temperature-qstar-data"
    data_sources = [
        {
            "id": heatmap_ref,
            "kind": "csv",
            "path": str(heatmap_path),
            "role": "plot_data",
        },
        {
            "id": qstar_ref,
            "kind": "csv",
            "path": str(qstar_path),
            "role": "plot_data",
        },
    ]
    objects = [
        {
            "id": "series-heatmap",
            "type": "plot_series",
            "chart_kind": "heatmap",
            "name": "Scattering Heatmap",
            "data_ref": heatmap_ref,
            "x_column": "q_nm_inv",
            "y_column": "temperature_C",
            "value_column": "log_intensity",
            "style": {"colormap": COLOR_SCHEMES["heatmap"]},
        }
    ]
    if q_star_array is not None and np.any(np.isfinite(q_star_array)):
        objects.append(
            {
                "id": "series-q-star",
                "type": "plot_series",
                "name": "q*",
                "data_ref": qstar_ref,
                "x_column": "q_star_nm_inv",
                "y_column": "temperature_C",
                "style": {"color": "#FFFFFF", "line_width": 0.8, "line_style": "--"},
            }
        )
    save_generated_figure_document(
        path,
        technique="saxs",
        figure_id=Path(path).resolve().stem,
        data_sources=data_sources,
        recipe={
            "module": "polynexus.core.saxs_engine.saxs_output",
            "function": "fig_v3_scattering_heatmap",
            "inputs": {},
            "parameters": {
                "temperature_count": len(temperatures),
                "q_count": len(q),
                "beamstop_q_min": _json_number(beamstop_q_min),
            },
        },
        style={
            "xlabel": "q (nm^-1)",
            "ylabel": "Temperature (C)",
            "value_label": "log10 I(q)",
        },
        objects=objects,
    )


def _save_static_overview_document(
    path: str,
    labels: list,
    q_list: list,
    I_list: list,
    L_list: list,
    lc_list: list,
    Xc_list: list,
    Q_rel_list: list = None,
) -> None:
    profile_path = _write_static_overview_profile_data(path, labels, q_list, I_list)
    summary_path = _write_static_overview_summary_data(path, labels, L_list, lc_list, Xc_list, Q_rel_list)
    profile_ref = "saxs-static-overview-profile-data"
    summary_ref = "saxs-static-overview-summary-data"
    save_generated_figure_document(
        path,
        technique="saxs",
        figure_id=Path(path).resolve().stem,
        data_sources=[
            {
                "id": profile_ref,
                "kind": "csv",
                "path": str(profile_path),
                "role": "plot_data",
            },
            {
                "id": summary_ref,
                "kind": "csv",
                "path": str(summary_path),
                "role": "plot_data",
            },
        ],
        recipe={
            "module": "polynexus.core.saxs_engine.saxs_output",
            "function": "fig_static_overview",
            "inputs": {"labels": [str(label or "") for label in labels]},
            "parameters": {"sample_count": len(labels)},
        },
        style={
            "panels": ["I(q)", "I(q)q^2", "L", "lc/Xc/Qrel"],
            "x_scale": "log",
            "y_scale": "log",
        },
        objects=[
            {
                "id": "series-intensity",
                "type": "plot_series",
                "name": "I(q)",
                "data_ref": profile_ref,
                "x_column": "q_nm_inv",
                "y_column": "intensity",
                "group_column": "label",
                "style": {"palette": "tab10", "line_width": 0.8},
            },
            {
                "id": "series-iq2",
                "type": "plot_series",
                "name": "I(q) q^2",
                "data_ref": profile_ref,
                "x_column": "q_nm_inv",
                "y_column": "iq2",
                "group_column": "label",
                "style": {"palette": "tab10", "line_width": 0.8},
            },
            {
                "id": "series-L",
                "type": "plot_series",
                "chart_kind": "bar",
                "name": "Long Period",
                "data_ref": summary_ref,
                "x_column": "label",
                "y_column": "L_nm",
                "style": {"palette": "tab10"},
            },
            {
                "id": "series-lc",
                "type": "plot_series",
                "chart_kind": "bar",
                "name": "Crystalline Thickness",
                "data_ref": summary_ref,
                "x_column": "label",
                "y_column": "lc_nm",
                "style": {"color": "steelblue"},
            },
            {
                "id": "series-Xc",
                "type": "plot_series",
                "name": "Crystallinity",
                "data_ref": summary_ref,
                "x_column": "label",
                "y_column": "Xc",
                "style": {"color": "firebrick", "line_width": 1.2},
            },
            {
                "id": "series-Q-rel",
                "type": "plot_series",
                "name": "Relative Invariant",
                "data_ref": summary_ref,
                "x_column": "label",
                "y_column": "Q_rel",
                "style": {"color": "darkorange", "line_width": 1.0, "line_style": "--"},
            },
        ],
    )


def _save_condition_overview_document(
    path: str,
    conditions: np.ndarray,
    q_list: list,
    I_list: list,
    *,
    condition_axis: str,
    function_name: str,
    L_arr: np.ndarray,
    lc_arr: np.ndarray,
    Xc_arr: np.ndarray,
    la_arr: Optional[np.ndarray] = None,
    Q_arr: Optional[np.ndarray] = None,
    Q_rel_arr: Optional[np.ndarray] = None,
) -> None:
    profile_path = _write_condition_overview_profile_data(path, conditions, q_list, I_list)
    summary_path = _write_condition_overview_summary_data(
        path,
        conditions,
        L_arr,
        lc_arr,
        Xc_arr,
        la_arr=la_arr,
        Q_arr=Q_arr,
        Q_rel_arr=Q_rel_arr,
    )
    profile_ref = f"saxs-{condition_axis}-overview-profile-data"
    summary_ref = f"saxs-{condition_axis}-overview-summary-data"
    objects = [
        {
            "id": "series-iq2-waterfall",
            "type": "plot_series",
            "name": "I(q) q^2 Waterfall",
            "data_ref": profile_ref,
            "x_column": "q_nm_inv",
            "y_column": "iq2_offset",
            "group_column": "condition_value",
            "style": {"palette": "plasma" if condition_axis == "temperature_C" else "viridis", "line_width": 0.6},
        },
        {
            "id": "series-L",
            "type": "plot_series",
            "name": "Long Period",
            "data_ref": summary_ref,
            "x_column": condition_axis,
            "y_column": "L_nm",
            "style": {"color": "steelblue", "line_width": 1.2},
        },
        {
            "id": "series-lc",
            "type": "plot_series",
            "name": "Crystalline Thickness",
            "data_ref": summary_ref,
            "x_column": condition_axis,
            "y_column": "lc_nm",
            "style": {"color": "firebrick", "line_width": 1.0},
        },
    ]
    if condition_axis == "strain_pct":
        objects.append(
            {
                "id": "series-la",
                "type": "plot_series",
                "name": "Amorphous Thickness",
                "data_ref": summary_ref,
                "x_column": condition_axis,
                "y_column": "la_nm",
                "style": {"color": "darkorange", "line_width": 1.2, "line_style": "--"},
            }
        )
        objects.append(
            {
                "id": "series-Q-star",
                "type": "plot_series",
                "chart_kind": "bar",
                "name": "Scattering Invariant",
                "data_ref": summary_ref,
                "x_column": condition_axis,
                "y_column": "Q_star",
                "style": {"color": "steelblue", "alpha": 0.6},
            }
        )
    objects.append(
        {
            "id": "series-Xc",
            "type": "plot_series",
            "name": "Crystallinity",
            "data_ref": summary_ref,
            "x_column": condition_axis,
            "y_column": "Xc",
            "style": {"color": "darkgreen", "line_width": 1.5},
        }
    )
    objects.append(
        {
            "id": "series-Q-rel",
            "type": "plot_series",
            "name": "Relative Invariant",
            "data_ref": summary_ref,
            "x_column": condition_axis,
            "y_column": "Q_rel",
            "style": {"color": "purple" if condition_axis == "temperature_C" else "firebrick", "line_width": 1.2},
        }
    )
    save_generated_figure_document(
        path,
        technique="saxs",
        figure_id=Path(path).resolve().stem,
        data_sources=[
            {
                "id": profile_ref,
                "kind": "csv",
                "path": str(profile_path),
                "role": "plot_data",
            },
            {
                "id": summary_ref,
                "kind": "csv",
                "path": str(summary_path),
                "role": "plot_data",
            },
        ],
        recipe={
            "module": "polynexus.core.saxs_engine.saxs_output",
            "function": function_name,
            "inputs": {},
            "parameters": {
                "condition_axis": condition_axis,
                "condition_count": len(conditions),
            },
        },
        style={
            "panels": ["Iq2 waterfall", "structure parameters", "invariant", "crystallinity"],
        },
        objects=objects,
    )
