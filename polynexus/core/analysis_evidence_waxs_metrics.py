from __future__ import annotations

from typing import Any

from .analysis_evidence_utils import (
    _clean_float,
    _clamp_unit,
    _inverse_ratio_score,
    _mean_finite,
    _non_empty_mapping,
    _relative_spread,
)


def _waxs_peak_metrics(output: dict[str, Any]) -> dict[str, Any]:
    raw_peaks = output.get("peaks")
    peaks: list[dict[str, Any]] = []

    if isinstance(raw_peaks, list):
        for peak in raw_peaks:
            if not isinstance(peak, dict):
                continue
            center = _clean_float(peak.get("two_theta", peak.get("center")))
            width = _clean_float(peak.get("fwhm_deg", peak.get("fwhm")))
            area = _clean_float(peak.get("area"))
            peaks.append(
                {
                    "center": center,
                    "width": width,
                    "area": area,
                    "hkl": str(peak.get("hkl", "") or "").strip(),
                }
            )

    if not peaks:
        centers = output.get("peak_centers")
        if isinstance(centers, list):
            for center in centers:
                peaks.append(
                    {
                        "center": _clean_float(center),
                        "width": None,
                        "area": None,
                        "hkl": "",
                    }
                )

    centers = [item["center"] for item in peaks if item.get("center") is not None]
    widths = [item["width"] for item in peaks if item.get("width") is not None]
    areas = [item["area"] for item in peaks if item.get("area") is not None]
    sorted_centers = sorted(centers)
    gaps = [b - a for a, b in zip(sorted_centers, sorted_centers[1:]) if b > a]
    peak_gap_spread = _relative_spread(gaps)
    peak_width_spread = _relative_spread(widths)
    area_ratio = None
    positive_areas = [float(value) for value in areas if value is not None and float(value) > 0]
    if len(positive_areas) >= 2:
        area_ratio = max(positive_areas) / max(min(positive_areas), 1e-9)

    return {
        "peaks": peaks,
        "peak_count": len(centers),
        "peak_positions": centers,
        "peak_widths": widths,
        "peak_areas": areas,
        "peak_gap_spread": peak_gap_spread,
        "peak_width_spread": peak_width_spread,
        "peak_area_ratio": area_ratio,
    }


def _waxs_structure_metrics(
    output: dict[str, Any],
    *,
    peak_metrics: dict[str, Any] | None = None,
    config_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    peak_metrics = peak_metrics if isinstance(peak_metrics, dict) else _waxs_peak_metrics(output)
    config_snapshot = config_snapshot if isinstance(config_snapshot, dict) else {}

    peak_count = _clean_float(peak_metrics.get("peak_count"))
    peak_width_spread = _clean_float(peak_metrics.get("peak_width_spread"))
    peak_area_ratio = _clean_float(peak_metrics.get("peak_area_ratio"))
    width_values = [
        value for value in peak_metrics.get("peak_widths", []) if _clean_float(value) is not None
    ]
    mean_peak_width = _mean_finite([_clean_float(value) for value in width_values])

    x_pct = _clean_float(output.get("Xc_pct"))
    scherrer = _clean_float(output.get("D_Scherrer_nm"))
    scherrer_uncertainty = _clean_float(output.get("D_uncertainty_nm"))
    wh_size = _clean_float(output.get("D_WH_nm"))
    wh_size_uncertainty = _clean_float(output.get("D_WH_uncertainty_nm"))
    wh_strain = _clean_float(output.get("epsilon_WH_pct"))
    wh_strain_uncertainty = _clean_float(output.get("epsilon_WH_uncertainty_pct"))
    wh_fit_r_squared = _clean_float(output.get("WH_fit_r_squared"))
    size_reliability_status = str(output.get("size_reliability_status", "") or "").strip() or None
    instrument_broadening_model = str(output.get("instrument_broadening_model", "") or "").strip() or None
    scherrer_peak_records = output.get("scherrer_peak_records")
    if not isinstance(scherrer_peak_records, list):
        scherrer_peak_records = []
    offset = _clean_float(output.get("two_theta_offset"))
    if offset is None:
        offset = _clean_float(config_snapshot.get("two_theta_offset"))

    crystal_system = str(output.get("crystal_system", "") or "").strip()
    unit_cell_params = output.get("unit_cell_params", config_snapshot.get("unit_cell_params", {}))
    unit_cell_present = bool(unit_cell_params)
    crystallinity_method = str(
        output.get(
            "crystallinity_method",
            output.get("Xc_method", config_snapshot.get("crystallinity_method", "")),
        )
        or ""
    ).strip()

    peak_support_ok = peak_count is not None and peak_count >= 2
    offset_ok = offset is None or abs(offset) <= 0.05
    width_ok = peak_width_spread is None or peak_width_spread <= 0.45
    offset_score = _inverse_ratio_score(abs(offset), 0.08) if offset is not None else 1.0
    structure_support_score = _clamp_unit(
        0.40 * (1.0 if peak_support_ok else 0.28)
        + 0.20 * (offset_score if offset_score is not None else 0.0)
        + 0.20 * (1.0 if width_ok else 0.42)
        + 0.20 * (1.0 if unit_cell_present or crystal_system else 0.45),
        default=0.0,
    )
    fit_only_pass = bool(x_pct is not None and x_pct > 0)
    physical_support_pass = bool(
        peak_support_ok
        and offset_ok
        and width_ok
        and (scherrer is None or scherrer > 0)
    )
    paper_ready_candidate = bool(
        fit_only_pass
        and physical_support_pass
        and structure_support_score >= 0.72
        and peak_area_ratio is not None
        and peak_area_ratio <= 6.0
    )

    return _non_empty_mapping(
        [
            ("peak_count_detected", peak_count),
            ("peak_count_fitted", peak_count),
            (
                "dominant_peak_positions",
                peak_metrics.get("peak_positions") if peak_metrics.get("peak_positions") else None,
            ),
            ("mean_peak_width_deg", mean_peak_width),
            ("peak_width_spread", peak_width_spread),
            ("peak_area_ratio", peak_area_ratio),
            ("crystallinity_method", crystallinity_method or None),
            ("crystallinity_estimate_pct", x_pct),
            ("crystal_system", crystal_system or None),
            ("unit_cell_params_present", unit_cell_present or None),
            ("scherrer_size_nm", scherrer),
            ("scherrer_size_uncertainty_nm", scherrer_uncertainty),
            ("williamson_hall_size_nm", wh_size),
            ("williamson_hall_size_uncertainty_nm", wh_size_uncertainty),
            ("williamson_hall_strain_pct", wh_strain),
            ("williamson_hall_strain_uncertainty_pct", wh_strain_uncertainty),
            ("WH_fit_r_squared", wh_fit_r_squared),
            ("size_reliability_status", size_reliability_status),
            ("instrument_broadening_model", instrument_broadening_model),
            (
                "scherrer_peak_record_count",
                len(scherrer_peak_records) if scherrer_peak_records else None,
            ),
            ("two_theta_offset", offset),
            ("structure_support_score", round(structure_support_score, 3)),
            ("fit_only_pass", fit_only_pass),
            ("physical_support_pass", physical_support_pass),
            ("paper_ready_candidate", paper_ready_candidate),
        ]
    )


__all__ = [
    "_waxs_peak_metrics",
    "_waxs_structure_metrics",
]
