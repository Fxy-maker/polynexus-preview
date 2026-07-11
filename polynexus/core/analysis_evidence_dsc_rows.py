from __future__ import annotations

from typing import Any

from .analysis_evidence_utils import _clean_float, _non_empty_mapping


def _dsc_scan_rows(scan_r_squared: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(scan_r_squared, dict):
        scan_r_squared = [scan_r_squared]
    if not isinstance(scan_r_squared, list):
        return rows
    for item in scan_r_squared:
        if not isinstance(item, dict):
            continue
        row = _non_empty_mapping(
            [
                ("scan", item.get("scan")),
                ("label", str(item.get("label", "") or "").strip() or None),
                ("r_squared", _clean_float(item.get("r_squared"))),
                ("fit_rmse", _clean_float(item.get("fit_rmse"))),
                ("quality_score", _clean_float(item.get("quality_score"))),
                ("n_fit_regions", item.get("n_fit_regions")),
            ]
        )
        if row:
            rows.append(row)
    return rows


def _dsc_peak_component_rows(peak_components: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not isinstance(peak_components, list):
        return rows
    for item in peak_components:
        if not isinstance(item, dict):
            continue
        row = _non_empty_mapping(
            [
                ("type", str(item.get("type", "") or "").strip() or None),
                ("peak_C", _clean_float(item.get("peak_C"))),
                ("onset_C", _clean_float(item.get("onset_C"))),
                ("end_C", _clean_float(item.get("end_C"))),
                ("enthalpy_Jg", _clean_float(item.get("enthalpy_Jg"))),
                ("fraction", _clean_float(item.get("fraction"))),
                ("sigma_C", _clean_float(item.get("sigma_C", item.get("sigma")))),
                ("amplitude", _clean_float(item.get("amplitude", item.get("amp")))),
            ]
        )
        if row:
            rows.append(row)
    return rows


__all__ = [
    "_dsc_scan_rows",
    "_dsc_peak_component_rows",
]
