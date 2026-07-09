from __future__ import annotations

from typing import Any


def _saxs_summary_details(
    batch_evidence: dict[str, Any],
    condition_evidence: dict[str, Any],
    structure_evidence: dict[str, Any],
    stability_evidence: dict[str, Any],
    raw_structure_evidence: dict[str, Any],
) -> dict[str, Any]:
    summary_bits: list[str] = []

    if batch_evidence:
        summary_bits.append(f"batch_frames={batch_evidence.get('batch_frames')}")
    if condition_evidence.get("condition_source"):
        summary_bits.append(f"condition_source={condition_evidence.get('condition_source')}")
    if condition_evidence.get("condition_label") == "strain":
        strain_conf = condition_evidence.get("strain_axis_confidence")
        if strain_conf is not None:
            summary_bits.append(f"strain_axis={strain_conf}")
        if structure_evidence.get("Q_star_rel_mean") is not None:
            summary_bits.append(f"Q_star_rel={structure_evidence.get('Q_star_rel_mean')}")
        elif structure_evidence.get("Q_star_rel") is not None:
            summary_bits.append(f"Q_star_rel={structure_evidence.get('Q_star_rel')}")
        if structure_evidence.get("phi_void_mean") is not None:
            summary_bits.append(f"phi_void={structure_evidence.get('phi_void_mean')}")
        elif structure_evidence.get("phi_void") is not None:
            summary_bits.append(f"phi_void={structure_evidence.get('phi_void')}")
        if structure_evidence.get("f_Herman_mean") is not None:
            summary_bits.append(f"f_Herman={structure_evidence.get('f_Herman_mean')}")
        elif structure_evidence.get("f_Herman") is not None:
            summary_bits.append(f"f_Herman={structure_evidence.get('f_Herman')}")
        if structure_evidence.get("void_detected_frames") is not None:
            summary_bits.append(f"void_frames={structure_evidence.get('void_detected_frames')}")
        if structure_evidence.get("porod_slope_mean") is not None:
            summary_bits.append(f"porod_slope={structure_evidence.get('porod_slope_mean')}")
        if structure_evidence.get("strain_reliability_status"):
            summary_bits.append(f"strain_status={structure_evidence.get('strain_reliability_status')}")
        if structure_evidence.get("dominant_phase"):
            summary_bits.append(f"dominant_phase={structure_evidence.get('dominant_phase')}")
        if structure_evidence.get("paper_figure_candidate") is not None:
            summary_bits.append(f"paper_figure_candidate={bool(structure_evidence.get('paper_figure_candidate'))}")
        if structure_evidence.get("paper_conclusion_candidate") is not None:
            summary_bits.append(f"paper_candidate={bool(structure_evidence.get('paper_conclusion_candidate'))}")
        if structure_evidence.get("paper_conclusion_ready") is not None:
            summary_bits.append(f"paper_ready={bool(structure_evidence.get('paper_conclusion_ready'))}")

    if batch_evidence.get("batch_calibration_summary"):
        batch_calib = batch_evidence.get("batch_calibration_summary", {})
        if isinstance(batch_calib, dict) and batch_calib.get("fallback_ratio") is not None:
            summary_bits.append(f"fallback_ratio={batch_calib.get('fallback_ratio')}")
    if stability_evidence.get("stability_score") is not None:
        summary_bits.append(f"stability={stability_evidence.get('stability_score')}")
    if raw_structure_evidence.get("raw_structure_available"):
        summary_bits.append("raw_structure_available=True")
    if structure_evidence.get("lc_method"):
        summary_bits.append(f"lc_method={structure_evidence.get('lc_method')}")
    if structure_evidence.get("calibrated_fallback_active"):
        summary_bits.append(f"fallback={structure_evidence.get('calibrated_fallback_reason')}")
    if structure_evidence.get("calibration_skipped_reason"):
        summary_bits.append(f"calibration_skip={structure_evidence.get('calibration_skipped_reason')}")
    if structure_evidence.get("lamellar_interpretation_mode"):
        summary_bits.append(f"lamellar_mode={structure_evidence.get('lamellar_interpretation_mode')}")
    if structure_evidence.get("melting_window_status"):
        summary_bits.append(f"melting_window={structure_evidence.get('melting_window_status')}")
    if structure_evidence.get("lc_reliability_status"):
        summary_bits.append(f"lc_status={structure_evidence.get('lc_reliability_status')}")

    batch_structure = (
        batch_evidence.get("batch_structure_summary", {})
        if isinstance(batch_evidence.get("batch_structure_summary"), dict)
        else {}
    )
    if batch_structure.get("diagnostic_only_rows") is not None:
        summary_bits.append(f"diagnostic_lc_rows={batch_structure.get('diagnostic_only_rows')}")
    if batch_structure.get("within_window_rows") is not None:
        summary_bits.append(f"melting_window_rows={batch_structure.get('within_window_rows')}")

    return {"summary_bits": summary_bits}


__all__ = ["_saxs_summary_details"]
