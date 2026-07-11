from __future__ import annotations

from typing import Any

from .analysis_evidence_utils import (
    _clean_float,
    _extract_nested_mapping,
    _non_empty_mapping,
    _relative_spread,
)
from .analysis_evidence_ir_static_peak import (
    _ir_peak_records,
    _ir_xc_calibration_status,
)
from .ir_engine.names import normalize_ir_polymer_name


def _ir_reference_band_context(
    output: dict[str, Any],
    validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validation = dict(validation or {})
    config_snapshot = validation.get("config_snapshot", {})
    if not isinstance(config_snapshot, dict):
        config_snapshot = {}

    polymer_db = output.get("polymer_peaks_db")
    if not isinstance(polymer_db, dict):
        polymer_db = _extract_nested_mapping(config_snapshot, "polymer_peaks_db")
    polymer_name = str(output.get("polymer_name", output.get("polymer", "")) or "").strip()
    polymer_key = normalize_ir_polymer_name(polymer_name)
    characteristic_bands = polymer_db.get(polymer_key, []) if isinstance(polymer_db, dict) else []

    reference_band_records: list[dict[str, Any]] = []
    reference_bands_payload = validation.get("ir_reference_bands", {})
    if isinstance(reference_bands_payload, dict):
        payload_bands = reference_bands_payload.get("bands", [])
        if isinstance(payload_bands, list):
            for band in payload_bands:
                if not isinstance(band, dict):
                    continue
                ref_wn = _clean_float(band.get("wavenumber"))
                if ref_wn is None:
                    continue
                reference_band_records.append(
                    _non_empty_mapping(
                        [
                            ("ref_wavenumber", ref_wn),
                            ("assignment", str(band.get("assignment", "") or "").strip() or None),
                            ("intensity", str(band.get("intensity", "") or "").strip() or None),
                            ("crystallinity_sensitive", bool(band.get("crystallinity_sensitive", False))),
                        ]
                    )
                )

    if not reference_band_records and isinstance(characteristic_bands, list) and characteristic_bands:
        for band in characteristic_bands:
            if not isinstance(band, (list, tuple)) or not band:
                continue
            ref_wn = _clean_float(band[0])
            assignment = str(band[1] if len(band) > 1 else "",).strip()
            intensity = str(band[2] if len(band) > 2 else "",).strip()
            cryst = bool(band[3]) if len(band) > 3 else False
            if ref_wn is None:
                continue
            reference_band_records.append(
                _non_empty_mapping(
                    [
                        ("ref_wavenumber", ref_wn),
                        ("assignment", assignment or "unknown"),
                        ("intensity", intensity or None),
                        ("crystallinity_sensitive", cryst),
                    ]
                )
            )

    reference_band_source = str(
        reference_bands_payload.get("source", "IRConfig.polymer_peaks_db")
        if isinstance(reference_bands_payload, dict)
        else "IRConfig.polymer_peaks_db"
    ).strip() or None

    return {
        "polymer_name": polymer_name,
        "reference_band_records": reference_band_records,
        "reference_band_source": reference_band_source,
    }


def _ir_match_reference_bands(
    raw_peaks: list[dict[str, Any]],
    reference_band_records: list[dict[str, Any]],
    match_tolerance_cm1: float = 18.0,
) -> dict[str, Any]:
    key_band_hits: list[dict[str, Any]] = []
    key_band_missing: list[dict[str, Any]] = []

    for band in reference_band_records:
        ref_wn = _clean_float(band.get("ref_wavenumber"))
        if ref_wn is None:
            continue
        assignment = str(band.get("assignment", "") or "").strip()
        intensity = str(band.get("intensity", "") or "").strip()
        cryst = bool(band.get("crystallinity_sensitive", False))
        matched_peak = None
        for peak in raw_peaks:
            peak_wn = _clean_float(peak.get("wavenumber"))
            if peak_wn is None:
                continue
            if abs(peak_wn - ref_wn) <= match_tolerance_cm1:
                matched_peak = {
                    "ref_wavenumber": ref_wn,
                    "observed_wavenumber": peak_wn,
                    "assignment": assignment
                    or str(peak.get("assignment", "") or "").strip()
                    or "unknown",
                    "intensity": intensity or None,
                    "crystallinity_sensitive": cryst,
                    "delta_cm1": abs(peak_wn - ref_wn),
                }
                break
        if matched_peak is not None:
            key_band_hits.append(matched_peak)
        else:
            key_band_missing.append(
                {
                    "ref_wavenumber": ref_wn,
                    "assignment": assignment or "unknown",
                    "intensity": intensity or None,
                    "crystallinity_sensitive": cryst,
                }
            )

    return {
        "key_band_hits": key_band_hits,
        "key_band_missing": key_band_missing,
    }


def _ir_band_support_metrics(
    output: dict[str, Any],
    validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validation = dict(validation or {})
    config_snapshot = validation.get("config_snapshot", {})
    if not isinstance(config_snapshot, dict):
        config_snapshot = {}

    raw_peaks = _ir_peak_records(output)
    peak_widths = [
        _clean_float(peak.get("fwhm_cm1"))
        for peak in raw_peaks
        if _clean_float(peak.get("fwhm_cm1")) is not None
    ]
    assigned_peak_count = sum(
        1
        for peak in raw_peaks
        if str(peak.get("assignment", "") or "").strip().lower() not in {"", "unknown"}
    )
    reference_context = _ir_reference_band_context(output, validation)
    reference_band_records = reference_context.get("reference_band_records", [])
    band_matches = _ir_match_reference_bands(raw_peaks, reference_band_records)
    band_hit_count = len(band_matches.get("key_band_hits", []))
    band_missing_count = len(band_matches.get("key_band_missing", []))

    peak_width_spread = _relative_spread(peak_widths) if len(peak_widths) >= 2 else None
    baseline_method = str(
        output.get("baseline_method", config_snapshot.get("baseline_method", "")) or ""
    ).strip().lower()
    normalization_method = str(
        output.get("normalization_method", config_snapshot.get("normalization_method", "")) or ""
    ).strip().lower()
    peak_distance = _clean_float(
        output.get("peak_distance", config_snapshot.get("peak_distance"))
    )
    peak_fit_window = _clean_float(
        output.get("peak_fit_window_cm1", config_snapshot.get("peak_fit_window_cm1"))
    )
    assignment_confidence = _clean_float(
        output.get("assignment_confidence", output.get("polymer_score"))
    )
    polymer_score = _clean_float(output.get("polymer_score"))
    x_pct = _clean_float(output.get("Xc_pct"))
    x_method = str(output.get("Xc_method") or "").strip()
    x_calibration_status = _ir_xc_calibration_status(output)

    return {
        "peak_count": len(raw_peaks),
        "assigned_peak_count": assigned_peak_count,
        "peak_width_spread": peak_width_spread,
        "baseline_method": baseline_method,
        "normalization_method": normalization_method,
        "peak_distance": peak_distance,
        "peak_fit_window_cm1": peak_fit_window,
        "assignment_confidence": assignment_confidence,
        "polymer_score": polymer_score,
        "Xc_pct": x_pct,
        "Xc_method": x_method,
        "Xc_calibration_status": x_calibration_status,
        "reference_band_count": len(reference_band_records),
        "reference_band_hit_count": band_hit_count,
        "reference_band_missing_count": band_missing_count,
        "characteristic_band_support_ok": bool(
            reference_band_records and band_hit_count >= 3 and band_missing_count == 0
        ),
    }


__all__ = [
    "_ir_reference_band_context",
    "_ir_match_reference_bands",
    "_ir_band_support_metrics",
]
