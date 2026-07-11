from __future__ import annotations

from typing import Any

from .analysis_evidence_utils import _clean_float, _extract_nested_mapping, _non_empty_mapping


def _saxs_context_bundle(
    output: dict[str, Any],
    *,
    batch_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    batch_rows = batch_rows if isinstance(batch_rows, list) else []
    feature_evidence: dict[str, Any] = {}
    raw_structure_evidence: dict[str, Any] = {}
    batch_evidence: dict[str, Any] = {}

    raw_snapshot = output.get("raw_snapshot")
    if isinstance(raw_snapshot, dict) and raw_snapshot:
        raw_long_period = _extract_nested_mapping(raw_snapshot, "long_period")
        raw_structure = _extract_nested_mapping(raw_snapshot, "structure")
        raw_structure_evidence = _non_empty_mapping(
            [
                ("L_nm_raw", _clean_float(raw_structure.get("L"))),
                ("lc_nm_raw", _clean_float(raw_structure.get("lc"))),
                ("la_nm_raw", _clean_float(raw_structure.get("la"))),
                ("Xc_raw", _clean_float(raw_structure.get("phi_c"))),
                ("lc_confidence_raw", _clean_float(raw_structure.get("confidence_lc"))),
                ("Q_star_raw", _clean_float(raw_structure.get("Q_invariant"))),
                ("L_best_raw", _clean_float(raw_long_period.get("L_best"))),
                ("raw_structure_available", True),
            ]
        )
        if raw_structure_evidence:
            feature_evidence["raw_structure_evidence"] = raw_structure_evidence

    if batch_rows:
        batch_evidence = _non_empty_mapping(
            [
                (
                    "batch_frames",
                    int(output.get("batch_frames")) if output.get("batch_frames") is not None else None,
                ),
                ("condition_label", str(output.get("condition_label", "") or "").strip() or None),
                ("condition_range", str(output.get("condition_range", "") or "").strip() or None),
                (
                    "batch_calibration_summary",
                    output.get("batch_calibration_summary")
                    if isinstance(output.get("batch_calibration_summary"), dict)
                    else None,
                ),
                (
                    "batch_structure_summary",
                    output.get("batch_structure_summary")
                    if isinstance(output.get("batch_structure_summary"), dict)
                    else None,
                ),
                (
                    "sample_files",
                    [
                        str(row.get("file"))
                        for row in batch_rows[:6]
                        if isinstance(row, dict) and str(row.get("file", "")).strip()
                    ],
                ),
                (
                    "frame_condition_values",
                    [
                        {
                            "file": str(row.get("file", "") or "").strip(),
                            "condition_value": _clean_float(row.get("condition_value")),
                            "temperature_C": _clean_float(row.get("temperature_C")),
                            "strain_pct": _clean_float(row.get("strain_pct")),
                            "melting_window_status": str(row.get("melting_window_status", "") or "").strip() or None,
                            "lc_reliability_status": str(row.get("lc_reliability_status", "") or "").strip() or None,
                        }
                        for row in batch_rows[:8]
                        if isinstance(row, dict)
                    ],
                ),
            ]
        )

    return {
        "feature_evidence": feature_evidence,
        "raw_structure_evidence": raw_structure_evidence,
        "batch_evidence": batch_evidence,
    }


__all__ = ["_saxs_context_bundle"]
