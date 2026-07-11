from __future__ import annotations

from typing import Any

import numpy as np

from .analysis_evidence_utils import (
    _clean_float,
    _relative_spread,
    _safe_int,
    _extract_nested_mapping,
    _non_empty_mapping,
)


def _numeric_distribution(values: list[Any], *, source: str = "") -> dict[str, Any] | None:
    finite = [float(value) for value in values if _clean_float(value) is not None]
    if not finite:
        return None
    arr = np.asarray(finite, dtype=float)
    p25, p50, p75 = np.percentile(arr, [25, 50, 75])
    summary: dict[str, Any] = {
        "count": int(arr.size),
        "min": float(np.min(arr)),
        "p25": float(p25),
        "median": float(p50),
        "mean": float(np.mean(arr)),
        "p75": float(p75),
        "max": float(np.max(arr)),
        "std": float(np.std(arr)),
    }
    spread = _relative_spread(finite)
    if spread is not None:
        summary["spread"] = float(spread)
    if source:
        summary["source"] = source
    return summary


def _ir_peak_records(output: dict[str, Any]) -> list[dict[str, Any]]:
    raw_peaks = output.get("peaks")
    peaks: list[dict[str, Any]] = []

    if isinstance(raw_peaks, list) and raw_peaks:
        for peak in raw_peaks:
            if not isinstance(peak, dict):
                continue
            peaks.append(
                {
                    "wavenumber": _clean_float(peak.get("wavenumber")),
                    "height": _clean_float(peak.get("height")),
                    "prominence": _clean_float(peak.get("prominence")),
                    "fwhm_cm1": _clean_float(peak.get("fwhm_cm1", peak.get("fwhm"))),
                    "area": _clean_float(peak.get("area")),
                    "assignment": str(peak.get("assignment", "") or "").strip(),
                    "ref_wavenumber": _clean_float(peak.get("ref_wavenumber")),
                }
            )
        return peaks

    for index in range(1, 21):
        prefix = f"peak_{index}_"
        found_any = False
        wavenumber = _clean_float(output.get(f"{prefix}cm1"))
        height = _clean_float(output.get(f"{prefix}height"))
        area = _clean_float(output.get(f"{prefix}area"))
        width = _clean_float(output.get(f"{prefix}fwhm_cm1"))
        prominence = _clean_float(
            output.get(f"{prefix}prominence", output.get(f"{prefix}peak_prominence"))
        )
        assignment = str(output.get(f"{prefix}assignment", "") or "").strip()
        ref_wavenumber = _clean_float(
            output.get(f"{prefix}ref_wavenumber", output.get(f"{prefix}ref_cm1"))
        )
        if wavenumber is not None:
            found_any = True
        if height is not None:
            found_any = True
        if prominence is not None:
            found_any = True
        if area is not None:
            found_any = True
        if width is not None:
            found_any = True
        if assignment:
            found_any = True
        if ref_wavenumber is not None:
            found_any = True
        if not found_any:
            continue
        peaks.append(
            {
                "wavenumber": wavenumber,
                "height": height,
                "prominence": prominence,
                "fwhm_cm1": width,
                "area": area,
                "assignment": assignment,
                "ref_wavenumber": ref_wavenumber,
            }
        )

    if not peaks:
        centers = output.get("peak_centers")
        if isinstance(centers, list):
            for center in centers:
                peaks.append(
                    {
                        "wavenumber": _clean_float(center),
                        "height": None,
                        "prominence": None,
                        "fwhm_cm1": None,
                        "area": None,
                        "assignment": "",
                        "ref_wavenumber": None,
                    }
                )

    return peaks


def _ir_peak_observation_bundle(raw_peaks: list[dict[str, Any]]) -> dict[str, Any]:
    peak_positions: list[float] = []
    peak_heights: list[float] = []
    peak_prominences: list[float] = []
    peak_widths: list[float] = []
    peak_assignments: list[str] = []
    assigned_peaks: list[dict[str, Any]] = []
    unassigned_peaks: list[dict[str, Any]] = []
    peak_support_count = 0
    assigned_peak_count = 0
    matched_peak_count = 0

    for peak in raw_peaks:
        wn = _clean_float(peak.get("wavenumber"))
        height = _clean_float(peak.get("height"))
        prominence = _clean_float(peak.get("prominence"))
        width = _clean_float(peak.get("fwhm_cm1"))
        assignment = str(peak.get("assignment", "") or "").strip()
        ref_wn = _clean_float(peak.get("ref_wavenumber"))
        if wn is not None:
            peak_positions.append(wn)
        if height is not None:
            peak_heights.append(height)
        if prominence is not None:
            peak_prominences.append(prominence)
        if width is not None:
            peak_widths.append(width)
        if assignment:
            peak_assignments.append(assignment)
        peak_record = _non_empty_mapping(
            [
                ("wavenumber", wn),
                ("height", height),
                ("prominence", prominence),
                ("fwhm_cm1", width),
                ("area", _clean_float(peak.get("area"))),
                ("assignment", assignment or None),
                ("ref_wavenumber", ref_wn),
            ]
        )
        if assignment and assignment.lower() != "unknown":
            assigned_peak_count += 1
            if peak_record:
                assigned_peaks.append(peak_record)
        elif peak_record:
            unassigned_peaks.append(peak_record)
        if ref_wn is not None or (assignment and assignment.lower() != "unknown"):
            matched_peak_count += 1
        if height is not None and height > 0:
            peak_support_count += 1

    return {
        "peak_positions": peak_positions,
        "peak_heights": peak_heights,
        "peak_prominences": peak_prominences,
        "peak_widths": peak_widths,
        "peak_assignments": peak_assignments,
        "assigned_peaks": assigned_peaks,
        "unassigned_peaks": unassigned_peaks,
        "peak_support_count": peak_support_count,
        "assigned_peak_count": assigned_peak_count,
        "matched_peak_count": matched_peak_count,
    }


def _ir_xc_calibration_status(output: dict[str, Any]) -> str | None:
    status = str(output.get("Xc_calibration_status") or "").strip()
    if status:
        return status

    method = str(output.get("Xc_method") or "").strip().lower()
    if method.endswith("_uncalibrated") or method == "band_ratio":
        return "uncalibrated_index"
    if output.get("Xc_pct") is None and not method:
        return "unavailable"
    return None


def _ir_processing_context(
    output: dict[str, Any],
    validation: dict[str, Any] | None = None,
    *,
    peak_positions: list[float],
    peak_prominences: list[float],
    peak_heights: list[float],
) -> dict[str, Any]:
    validation = dict(validation or {})
    config_snapshot = validation.get("config_snapshot", {})
    if not isinstance(config_snapshot, dict):
        config_snapshot = {}

    baseline_method = str(
        output.get("baseline_method", config_snapshot.get("baseline_method", "")) or ""
    ).strip()
    normalization_method = str(
        output.get("normalization_method", config_snapshot.get("normalization_method", ""))
        or ""
    ).strip()
    smooth_window = _clean_float(
        output.get("smooth_window", config_snapshot.get("smooth_window"))
    )
    peak_distance = _clean_float(
        output.get("peak_distance", config_snapshot.get("peak_distance"))
    )
    peak_fit_window = _clean_float(
        output.get("peak_fit_window_cm1", config_snapshot.get("peak_fit_window_cm1"))
    )
    assignment_tolerance = _clean_float(
        output.get("assignment_tolerance_cm1", config_snapshot.get("assignment_tolerance_cm1"))
    )
    wn_min = _clean_float(output.get("wavenumber_min_cm1"))
    wn_max = _clean_float(output.get("wavenumber_max_cm1"))
    wn_span = None
    if wn_min is not None and wn_max is not None:
        wn_span = abs(wn_max - wn_min)
    x_calibration_status = _ir_xc_calibration_status(output)
    peak_prominence_distribution = None
    if peak_positions:
        peak_prominence_distribution = _numeric_distribution(
            peak_prominences,
            source="prominence",
        )
        if peak_prominence_distribution is None and peak_heights:
            peak_prominence_distribution = _numeric_distribution(
                peak_heights,
                source="height_proxy",
            )

    return {
        "baseline_method": baseline_method,
        "normalization_method": normalization_method,
        "smooth_window": smooth_window,
        "peak_distance": peak_distance,
        "peak_fit_window": peak_fit_window,
        "assignment_tolerance": assignment_tolerance,
        "wn_min": wn_min,
        "wn_max": wn_max,
        "wn_span": wn_span,
        "x_calibration_status": x_calibration_status,
        "peak_prominence_distribution": peak_prominence_distribution,
    }


__all__ = [
    "_numeric_distribution",
    "_ir_peak_records",
    "_ir_peak_observation_bundle",
    "_ir_xc_calibration_status",
    "_ir_processing_context",
]
