from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from .saxs_output_helpers import _csv_number, _finite_csv


def _figure_source_dir(path: str) -> tuple[Path, Path]:
    figure_path = Path(path).resolve()
    output_root = figure_path.parent.parent
    data_dir = output_root / "data" / "figure_sources"
    data_dir.mkdir(parents=True, exist_ok=True)
    return figure_path, data_dir


def _write_u1_scattering_data(path: str, q: np.ndarray, intensity: np.ndarray) -> Path:
    figure_path, data_dir = _figure_source_dir(path)
    data_path = data_dir / f"{figure_path.stem}_data.csv"
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["q_nm_inv", "intensity", "iq2"])
        writer.writeheader()
        for q_value, intensity_value in zip(q, intensity):
            writer.writerow(
                {
                    "q_nm_inv": _csv_number(q_value),
                    "intensity": _csv_number(intensity_value),
                    "iq2": _csv_number(float(intensity_value) * float(q_value) ** 2),
                }
            )
    return data_path


def _write_u2_correlation_data(path: str, r: np.ndarray, gamma: np.ndarray) -> Path:
    figure_path, data_dir = _figure_source_dir(path)
    data_path = data_dir / f"{figure_path.stem}_data.csv"
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["r_nm", "gamma"])
        writer.writeheader()
        for r_value, gamma_value in zip(r, gamma):
            writer.writerow({"r_nm": _csv_number(r_value), "gamma": _csv_number(gamma_value)})
    return data_path


def _write_u3_idf_data(path: str, r_idf: np.ndarray, idf: np.ndarray) -> Path:
    figure_path, data_dir = _figure_source_dir(path)
    data_path = data_dir / f"{figure_path.stem}_data.csv"
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["r_nm", "idf"])
        writer.writeheader()
        for r_value, idf_value in zip(r_idf, idf):
            writer.writerow({"r_nm": _csv_number(r_value), "idf": _csv_number(idf_value)})
    return data_path


def _write_u4_porod_data(
    path: str,
    q_porod: np.ndarray,
    Iq4: np.ndarray,
    *,
    slope: Optional[float] = None,
) -> Path:
    figure_path, data_dir = _figure_source_dir(path)
    data_path = data_dir / f"{figure_path.stem}_data.csv"
    q4 = q_porod**4
    intercept = None
    if slope is not None and len(Iq4) > 0 and len(q_porod) > 0:
        intercept = float(np.mean(Iq4[-10:]) - slope * np.mean(q_porod[-10:] ** 4))
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["q_nm_inv", "q4_nm_minus4", "Iq4", "fit"])
        writer.writeheader()
        for q_value, q4_value, iq4_value in zip(q_porod, q4, Iq4):
            fit_value = "" if intercept is None else _csv_number(slope * float(q4_value) + intercept)
            writer.writerow(
                {
                    "q_nm_inv": _csv_number(q_value),
                    "q4_nm_minus4": _csv_number(q4_value),
                    "Iq4": _csv_number(iq4_value),
                    "fit": fit_value,
                }
            )
    return data_path


def _write_guinier_data(
    path: str,
    q: np.ndarray,
    intensity: np.ndarray,
    slope: Optional[float],
    intercept: Optional[float],
) -> Path:
    figure_path, data_dir = _figure_source_dir(path)
    data_path = data_dir / f"{figure_path.stem}_data.csv"
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["q_nm_inv", "q2_nm_minus2", "ln_intensity", "fit"])
        writer.writeheader()
        for q_value, intensity_value in zip(q, intensity):
            q2 = float(q_value) ** 2
            fit = "" if slope is None or intercept is None else _csv_number(slope * q2 + intercept)
            writer.writerow(
                {
                    "q_nm_inv": _csv_number(q_value),
                    "q2_nm_minus2": _csv_number(q2),
                    "ln_intensity": _csv_number(np.log(float(intensity_value))),
                    "fit": fit,
                }
            )
    return data_path


def _write_kratky_data(path: str, q: np.ndarray, intensity: np.ndarray) -> Path:
    figure_path, data_dir = _figure_source_dir(path)
    data_path = data_dir / f"{figure_path.stem}_data.csv"
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["q_nm_inv", "intensity", "iq2"])
        writer.writeheader()
        for q_value, intensity_value in zip(q, intensity):
            writer.writerow(
                {
                    "q_nm_inv": _csv_number(q_value),
                    "intensity": _csv_number(intensity_value),
                    "iq2": _csv_number(float(intensity_value) * float(q_value) ** 2),
                }
            )
    return data_path


def _write_joint_crystallinity_data(
    path: str,
    techniques: list[str],
    values: list[float],
) -> Path:
    figure_path, data_dir = _figure_source_dir(path)
    data_path = data_dir / f"{figure_path.stem}_data.csv"
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["technique", "phi_c", "phi_c_pct"])
        writer.writeheader()
        for technique, value in zip(techniques, values):
            writer.writerow(
                {
                    "technique": str(technique or ""),
                    "phi_c": _csv_number(value),
                    "phi_c_pct": _csv_number(value * 100.0),
                }
            )
    return data_path


def _write_condition_overview_profile_data(
    path: str,
    conditions: np.ndarray,
    q_list: list,
    I_list: list,
) -> Path:
    figure_path, data_dir = _figure_source_dir(path)
    data_path = data_dir / f"{figure_path.stem}_profile_data.csv"
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "condition_index",
                "condition_value",
                "q_nm_inv",
                "intensity",
                "iq2",
                "iq2_offset",
            ],
        )
        writer.writeheader()
        offset = 0.0
        for index, condition in enumerate(conditions):
            q = q_list[index]
            intensity = I_list[index]
            iq2 = intensity * q**2
            for q_value, intensity_value, iq2_value in zip(q, intensity, iq2):
                writer.writerow(
                    {
                        "condition_index": index,
                        "condition_value": _csv_number(condition),
                        "q_nm_inv": _csv_number(q_value),
                        "intensity": _csv_number(intensity_value),
                        "iq2": _csv_number(iq2_value),
                        "iq2_offset": _csv_number(float(iq2_value) + offset * 0.3),
                    }
                )
            mask = (q >= 0.2) & (q <= 1.2)
            window = iq2[mask]
            offset += float(np.nanmax(window)) * 0.4 if len(window) else 0.0
    return data_path


def _write_condition_overview_summary_data(
    path: str,
    conditions: np.ndarray,
    L_arr: np.ndarray,
    lc_arr: np.ndarray,
    Xc_arr: np.ndarray,
    *,
    la_arr: Optional[np.ndarray] = None,
    Q_arr: Optional[np.ndarray] = None,
    Q_rel_arr: Optional[np.ndarray] = None,
) -> Path:
    figure_path, data_dir = _figure_source_dir(path)
    data_path = data_dir / f"{figure_path.stem}_summary_data.csv"
    q_rel = Q_rel_arr
    if q_rel is None and Q_arr is not None and np.any(np.isfinite(Q_arr)):
        q_max = np.nanmax(Q_arr)
        q_rel = Q_arr / q_max if np.isfinite(q_max) and q_max > 0 else None
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "condition_index",
                "temperature_C",
                "strain_pct",
                "L_nm",
                "lc_nm",
                "la_nm",
                "Xc",
                "Q_star",
                "Q_rel",
            ],
        )
        writer.writeheader()
        for index, condition in enumerate(conditions):
            writer.writerow(
                {
                    "condition_index": index,
                    "temperature_C": _csv_number(condition),
                    "strain_pct": _csv_number(condition),
                    "L_nm": _finite_csv(L_arr[index]) if index < len(L_arr) else "",
                    "lc_nm": _finite_csv(lc_arr[index]) if index < len(lc_arr) else "",
                    "la_nm": _finite_csv(la_arr[index]) if la_arr is not None and index < len(la_arr) else "",
                    "Xc": _finite_csv(Xc_arr[index]) if index < len(Xc_arr) else "",
                    "Q_star": _finite_csv(Q_arr[index]) if Q_arr is not None and index < len(Q_arr) else "",
                    "Q_rel": _finite_csv(q_rel[index]) if q_rel is not None and index < len(q_rel) else "",
                }
            )
    return data_path


def _write_static_overview_profile_data(
    path: str,
    labels: list,
    q_list: list,
    I_list: list,
) -> Path:
    figure_path, data_dir = _figure_source_dir(path)
    data_path = data_dir / f"{figure_path.stem}_profile_data.csv"
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["sample_index", "label", "q_nm_inv", "intensity", "iq2"],
        )
        writer.writeheader()
        for sample_index, label in enumerate(labels):
            q = q_list[sample_index]
            intensity = I_list[sample_index]
            for q_value, intensity_value in zip(q, intensity):
                writer.writerow(
                    {
                        "sample_index": sample_index,
                        "label": str(label or ""),
                        "q_nm_inv": _csv_number(q_value),
                        "intensity": _csv_number(intensity_value),
                        "iq2": _csv_number(float(intensity_value) * float(q_value) ** 2),
                    }
                )
    return data_path


def _write_static_overview_summary_data(
    path: str,
    labels: list,
    L_list: list,
    lc_list: list,
    Xc_list: list,
    Q_rel_list: list = None,
) -> Path:
    figure_path, data_dir = _figure_source_dir(path)
    data_path = data_dir / f"{figure_path.stem}_summary_data.csv"
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["sample_index", "label", "L_nm", "lc_nm", "Xc", "Q_rel"],
        )
        writer.writeheader()
        for index, label in enumerate(labels):
            writer.writerow(
                {
                    "sample_index": index,
                    "label": str(label or ""),
                    "L_nm": _finite_csv(L_list[index]) if index < len(L_list) else "",
                    "lc_nm": _finite_csv(lc_list[index]) if index < len(lc_list) else "",
                    "Xc": _finite_csv(Xc_list[index]) if index < len(Xc_list) else "",
                    "Q_rel": _finite_csv(Q_rel_list[index]) if Q_rel_list is not None and index < len(Q_rel_list) else "",
                }
            )
    return data_path


def _write_v3_heatmap_data(
    path: str,
    q: np.ndarray,
    temperatures: np.ndarray,
    I_matrix: np.ndarray,
    beamstop_q_min: float,
) -> Path:
    figure_path, data_dir = _figure_source_dir(path)
    data_path = data_dir / f"{figure_path.stem}_heatmap_data.csv"
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "temperature_index",
                "temperature_C",
                "q_index",
                "q_nm_inv",
                "intensity",
                "log_intensity",
                "beamstop_masked",
            ],
        )
        writer.writeheader()
        for temp_index, temperature in enumerate(temperatures):
            if temp_index >= I_matrix.shape[0]:
                continue
            for q_index, q_value in enumerate(q):
                if q_index >= I_matrix.shape[1]:
                    continue
                intensity = float(I_matrix[temp_index, q_index])
                writer.writerow(
                    {
                        "temperature_index": temp_index,
                        "temperature_C": _csv_number(temperature),
                        "q_index": q_index,
                        "q_nm_inv": _csv_number(q_value),
                        "intensity": _csv_number(intensity),
                        "log_intensity": _csv_number(np.log10(intensity + 1e-12)),
                        "beamstop_masked": bool(beamstop_q_min > 0 and q_value < beamstop_q_min),
                    }
                )
    return data_path


def _write_v3_qstar_data(
    path: str,
    temperatures: np.ndarray,
    q_star_array: Optional[np.ndarray],
) -> Path:
    figure_path, data_dir = _figure_source_dir(path)
    data_path = data_dir / f"{figure_path.stem}_qstar_data.csv"
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["temperature_C", "q_star_nm_inv"])
        writer.writeheader()
        if q_star_array is None:
            return data_path
        for index, temperature in enumerate(temperatures):
            writer.writerow(
                {
                    "temperature_C": _csv_number(temperature),
                    "q_star_nm_inv": _finite_csv(q_star_array[index]) if index < len(q_star_array) else "",
                }
            )
    return data_path


def _write_v2_temperature_parameters_data(
    path: str,
    temperatures: np.ndarray,
    L_array: np.ndarray,
    lc_array: np.ndarray,
    Q_star_array: Optional[np.ndarray],
    Xc_array: Optional[np.ndarray],
) -> Path:
    figure_path, data_dir = _figure_source_dir(path)
    data_path = data_dir / f"{figure_path.stem}_data.csv"
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["temperature_C", "L_nm", "lc_nm", "la_nm", "Q_star", "Xc"])
        writer.writeheader()
        for index, temperature in enumerate(temperatures):
            L_value = L_array[index] if index < len(L_array) else np.nan
            lc_value = lc_array[index] if index < len(lc_array) else np.nan
            writer.writerow(
                {
                    "temperature_C": _csv_number(temperature),
                    "L_nm": _finite_csv(L_value),
                    "lc_nm": _finite_csv(lc_value),
                    "la_nm": _finite_csv(L_value - lc_value),
                    "Q_star": _finite_csv(Q_star_array[index]) if Q_star_array is not None and index < len(Q_star_array) else "",
                    "Xc": _finite_csv(Xc_array[index]) if Xc_array is not None and index < len(Xc_array) else "",
                }
            )
    return data_path


def _write_v4_avrami_data(
    path: str,
    times: np.ndarray,
    Xc_array: np.ndarray,
    avrami_result: Optional[Dict],
) -> Path:
    figure_path, data_dir = _figure_source_dir(path)
    data_path = data_dir / f"{figure_path.stem}_data.csv"
    mask = (Xc_array > 0.01) & (Xc_array < 0.99) & (times > 0)
    ln_times = np.log(times[mask])
    avrami_y = np.log(-np.log(1 - Xc_array[mask]))
    n_value = avrami_result.get("n", np.nan) if avrami_result else np.nan
    k_value = avrami_result.get("k_sn", np.nan) if avrami_result else np.nan
    fit_ln_times = np.array([])
    fit_values = np.array([])
    if avrami_result and avrami_result.get("valid") and np.isfinite(n_value) and np.isfinite(k_value) and len(ln_times) > 0:
        fit_ln_times = np.linspace(np.min(ln_times), np.max(ln_times), 50)
        fit_values = np.log(k_value) + n_value * fit_ln_times
    rows = max(len(times), len(ln_times), len(fit_ln_times))
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["time_s", "Xc", "ln_time_s", "avrami_y", "fit_ln_time_s", "fit"],
        )
        writer.writeheader()
        for index in range(rows):
            writer.writerow(
                {
                    "time_s": _csv_number(times[index]) if index < len(times) else "",
                    "Xc": _csv_number(Xc_array[index]) if index < len(Xc_array) else "",
                    "ln_time_s": _csv_number(ln_times[index]) if index < len(ln_times) else "",
                    "avrami_y": _csv_number(avrami_y[index]) if index < len(avrami_y) else "",
                    "fit_ln_time_s": _csv_number(fit_ln_times[index]) if index < len(fit_ln_times) else "",
                    "fit": _csv_number(fit_values[index]) if index < len(fit_values) else "",
                }
            )
    return data_path


def _write_series_waterfall_data(
    path: str,
    conditions: np.ndarray,
    q_list: List[np.ndarray],
    I_list: List[np.ndarray],
    indices: List[int],
) -> Path:
    figure_path, data_dir = _figure_source_dir(path)
    data_path = data_dir / f"{figure_path.stem}_data.csv"
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["condition_index", "condition_value", "q_nm_inv", "intensity", "intensity_offset"],
        )
        writer.writeheader()
        offset = 0.0
        for index in indices:
            if index >= len(conditions):
                continue
            q = q_list[index]
            intensity = I_list[index]
            for q_value, intensity_value in zip(q, intensity):
                writer.writerow(
                    {
                        "condition_index": index,
                        "condition_value": _csv_number(conditions[index]),
                        "q_nm_inv": _csv_number(q_value),
                        "intensity": _csv_number(intensity_value),
                        "intensity_offset": _csv_number(float(intensity_value) + offset),
                    }
                )
            offset += float(np.nanmax(intensity)) * 0.3 if len(intensity) else 0.0
    return data_path


def _write_t3_structure_data(
    path: str,
    strains: np.ndarray,
    L_array: np.ndarray,
    lc_array: np.ndarray,
    phi_c_array: Optional[np.ndarray],
    f_herman_array: Optional[np.ndarray],
    Q_star_array: Optional[np.ndarray],
) -> Path:
    figure_path, data_dir = _figure_source_dir(path)
    data_path = data_dir / f"{figure_path.stem}_data.csv"
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["strain_pct", "L_nm", "lc_nm", "la_nm", "phi_c", "Q_star", "f_Herman"],
        )
        writer.writeheader()
        for index, strain in enumerate(strains):
            L_value = L_array[index] if index < len(L_array) else np.nan
            lc_value = lc_array[index] if index < len(lc_array) else np.nan
            writer.writerow(
                {
                    "strain_pct": _csv_number(strain),
                    "L_nm": _finite_csv(L_value),
                    "lc_nm": _finite_csv(lc_value),
                    "la_nm": _finite_csv(L_value - lc_value),
                    "phi_c": _finite_csv(phi_c_array[index]) if phi_c_array is not None and index < len(phi_c_array) else "",
                    "Q_star": _finite_csv(Q_star_array[index]) if Q_star_array is not None and index < len(Q_star_array) else "",
                    "f_Herman": _finite_csv(f_herman_array[index]) if f_herman_array is not None and index < len(f_herman_array) else "",
                }
            )
    return data_path


def _write_t4_invariant_data(
    path: str,
    strains: np.ndarray,
    Q_star_array: np.ndarray,
    Q_norm: np.ndarray,
    tolerance: float,
) -> Path:
    figure_path, data_dir = _figure_source_dir(path)
    data_path = data_dir / f"{figure_path.stem}_data.csv"
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["strain_pct", "Q_star", "Q_norm", "band_lower", "band_upper"],
        )
        writer.writeheader()
        for index, strain in enumerate(strains):
            writer.writerow(
                {
                    "strain_pct": _csv_number(strain),
                    "Q_star": _finite_csv(Q_star_array[index]) if index < len(Q_star_array) else "",
                    "Q_norm": _finite_csv(Q_norm[index]) if index < len(Q_norm) else "",
                    "band_lower": _csv_number(1.0 - tolerance),
                    "band_upper": _csv_number(1.0 + tolerance),
                }
            )
    return data_path
