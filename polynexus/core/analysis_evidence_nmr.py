from __future__ import annotations

from typing import Any

from .analysis_evidence_nmr_constraints import (
    _NMR_CONSTRAINT_NAMES,
    _evaluate_nmr_constraint,
    _nmr_symptom_bridge_lines,
    _nmr_symptoms_from_constraints,
)
from .analysis_evidence_utils import _clean_float, _non_empty_mapping, _safe_int


def _nmr_peak_rows(output: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx in range(10):
        ppm = _clean_float(output.get(f"peak_{idx}_ppm"))
        assignment = str(output.get(f"peak_{idx}_assignment") or "").strip()
        phase = str(output.get(f"peak_{idx}_phase") or "").strip().lower()
        if ppm is None and not assignment and not phase:
            continue
        rows.append(
            _non_empty_mapping(
                [
                    ("index", idx),
                    ("ppm", ppm),
                    ("assignment", assignment or None),
                    ("phase", phase or None),
                    ("snr", _clean_float(output.get(f"peak_{idx}_snr"))),
                    ("fwhm_ppm", _clean_float(output.get(f"peak_{idx}_fwhm_ppm"))),
                    ("area", _clean_float(output.get(f"peak_{idx}_area"))),
                    ("delta_ppm", _clean_float(output.get(f"peak_{idx}_delta_ppm"))),
                    ("possible_solvent", str(output.get(f"peak_{idx}_possible_solvent") or "").strip() or None),
                ]
            )
        )
    return rows


def _nmr_analysis_bundle(output: dict[str, Any]) -> dict[str, Any]:
    feature_evidence: dict[str, Any] = {}
    for key in ("n_peaks", "Xc_pct", "Xc_method", "dominant_peak_ppm", "mean_fwhm_ppm", "median_snr", "quality_metrics"):
        if key in output:
            feature_evidence[key] = output.get(key)

    peak_rows = _nmr_peak_rows(output)
    peak_count = _clean_float(output.get("n_peaks"))
    assigned_count = sum(1 for row in peak_rows if row.get("assignment"))
    phase_assigned_count = sum(1 for row in peak_rows if row.get("phase"))
    crystalline_count = sum(1 for row in peak_rows if str(row.get("phase", "")).lower() in {"c", "crystalline"})
    amorphous_count = sum(1 for row in peak_rows if str(row.get("phase", "")).lower() in {"a", "amorphous"})
    assignment_denominator = peak_count if peak_count and peak_count > 0 else len(peak_rows)
    assigned_fraction = assigned_count / assignment_denominator if assignment_denominator else None
    xc_method = str(output.get("Xc_method") or "").strip()
    explicit_xc_assignment_status = str(output.get("Xc_assignment_status") or "").strip()
    assignment_confidence = _clean_float(output.get("assignment_confidence"))
    library_match_fraction = _clean_float(output.get("library_match_fraction"))
    solvent_overlap_penalty = _clean_float(output.get("solvent_overlap_penalty"))
    phase_pair_support = bool(output.get("phase_pair_support")) if output.get("phase_pair_support") is not None else False
    matched_library_count = _safe_int(output.get("matched_library_count"), 0)

    xc_assignment_status = ""
    if explicit_xc_assignment_status:
        xc_assignment_status = explicit_xc_assignment_status
    elif (
        phase_pair_support
        and assignment_confidence is not None
        and assignment_confidence >= 0.7
        and (solvent_overlap_penalty is None or solvent_overlap_penalty <= 0.25)
    ):
        xc_assignment_status = "supported"
    elif output.get("Xc_pct") is not None or xc_method:
        if crystalline_count > 0 and amorphous_count > 0:
            xc_assignment_status = "supported"
        elif (
            assigned_count > 0
            or phase_assigned_count > 0
            or output.get("n_matches") is not None
            or xc_method == "requires_crystalline_amorphous_assignment"
        ):
            xc_assignment_status = "assignment_limited"
        else:
            xc_assignment_status = "missing_assignment"

    signal_evidence = _non_empty_mapping(
        [
            ("nucleus", str(output.get("nucleus") or "").strip() or None),
            ("sample_state", str(output.get("sample_state") or "").strip() or None),
            ("median_snr", _clean_float(output.get("median_snr"))),
            ("mean_fwhm_ppm", _clean_float(output.get("mean_fwhm_ppm"))),
            ("noise_mad", _clean_float(output.get("quality_noise_mad"))),
            ("fit_quality", _clean_float(output.get("quality_fit_quality"))),
        ]
    )
    peak_evidence = _non_empty_mapping(
        [
            ("peak_count", int(peak_count) if peak_count is not None and float(peak_count).is_integer() else peak_count),
            ("dominant_peak_ppm", _clean_float(output.get("dominant_peak_ppm"))),
            ("peak_area_total", _clean_float(output.get("peak_area_total"))),
            ("peaks", peak_rows),
        ]
    )
    assignment_evidence = _non_empty_mapping(
        [
            ("assigned_peak_count", assigned_count),
            ("phase_assignment_count", phase_assigned_count),
            ("assigned_peak_fraction", assigned_fraction),
            ("n_matches", _clean_float(output.get("n_matches"))),
            ("library_match_fraction", library_match_fraction),
            ("assignment_confidence", assignment_confidence),
            ("phase_pair_support", phase_pair_support if output.get("phase_pair_support") is not None else None),
            ("solvent_overlap_penalty", solvent_overlap_penalty),
            ("matched_library_count", matched_library_count if matched_library_count > 0 else None),
            ("assignment_library_source", str(output.get("assignment_library_source", "") or "").strip() or None),
        ]
    )
    phase_evidence = _non_empty_mapping(
        [
            ("crystalline_peak_count", crystalline_count),
            ("amorphous_peak_count", amorphous_count),
            ("phase_assignment_count", phase_assigned_count),
        ]
    )
    structure_evidence = _non_empty_mapping(
        [
            ("Xc_pct", _clean_float(output.get("Xc_pct"))),
            ("Xc_method", xc_method or None),
            ("Xc_assignment_status", xc_assignment_status or None),
            ("assignment_confidence", assignment_confidence),
            ("library_match_fraction", library_match_fraction),
            ("phase_pair_support", phase_pair_support if output.get("phase_pair_support") is not None else None),
            ("solvent_overlap_penalty", solvent_overlap_penalty),
            ("paper_conclusion_ready", xc_assignment_status == "supported"),
        ]
    )

    feature_evidence["signal_evidence"] = signal_evidence
    feature_evidence["peak_evidence"] = peak_evidence
    feature_evidence["assignment_evidence"] = assignment_evidence
    feature_evidence["phase_evidence"] = phase_evidence
    feature_evidence["structure_evidence"] = structure_evidence

    confidence_signals: list[dict[str, Any]] = []
    if output.get("median_snr") is not None:
        confidence_signals.append({"name": "median_snr", "value": _clean_float(output.get("median_snr")), "source": "NMR"})
    if assignment_confidence is not None:
        confidence_signals.append({"name": "assignment_confidence", "value": assignment_confidence, "source": "NMR"})

    return {
        "signal_evidence": signal_evidence,
        "peak_evidence": peak_evidence,
        "assignment_evidence": assignment_evidence,
        "phase_evidence": phase_evidence,
        "structure_evidence": structure_evidence,
        "feature_evidence": feature_evidence,
        "confidence_signals": confidence_signals,
    }


def _nmr_summary_details(
    signal_evidence: dict[str, Any],
    peak_evidence: dict[str, Any],
    structure_evidence: dict[str, Any],
) -> dict[str, Any]:
    summary_bits: list[str] = []
    if signal_evidence.get("median_snr") is not None:
        summary_bits.append(f"nmr_snr={signal_evidence.get('median_snr')}")
    if peak_evidence.get("peak_count") is not None:
        summary_bits.append(f"nmr_peaks={peak_evidence.get('peak_count')}")
    if structure_evidence.get("Xc_assignment_status"):
        summary_bits.append(f"nmr_xc={structure_evidence.get('Xc_assignment_status')}")
    return {"summary_bits": summary_bits}
