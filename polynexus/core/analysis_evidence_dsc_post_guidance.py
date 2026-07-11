from __future__ import annotations

from typing import Any


def _dsc_actionable_lines(soft_warn_names: set[str]) -> list[str]:
    names = {str(name).strip() for name in soft_warn_names if str(name).strip()}
    lines: list[str] = []
    if "baseline_sensitive_result" in names:
        lines.append("baseline_sensitive_result -> stabilize baseline_corr and smooth_window before trusting Tg/Tm")
    if "Tg_without_DCp_step" in names or "Tg_outside_supported_window" in names:
        lines.append("Tg support is weak -> re-center the Tg window before promoting Tg as stable")
    if "melting_without_supported_event" in names:
        lines.append("melting_without_supported_event -> check Tm onset/end and peak_components before accepting Tm")
    if "cold_crystallization_conflicts_with_melting" in names:
        lines.append(
            "cold_crystallization_conflicts_with_melting -> separate Tcc from the melting window before re-using the result"
        )
    if "event_polarity_conflict" in names:
        lines.append("event_polarity_conflict -> verify exo_up and signed enthalpy before writing conclusions")
    if "multi_scan_inconsistent" in names:
        lines.append("multi_scan_inconsistent -> stabilize the scan-to-scan evidence before accepting the file-level result")
    if "dsc_baseline_sensitive_xc" in names:
        lines.append(
            "dsc_baseline_sensitive_xc -> keep Xc low-confidence until baseline and integration sensitivity settle"
        )
    return lines


def _dsc_summary_details(structure_evidence: dict[str, Any]) -> dict[str, Any]:
    summary_bits: list[str] = []
    if structure_evidence.get("structure_support_score") is not None:
        summary_bits.append(f"structure_support={structure_evidence.get('structure_support_score')}")
    if structure_evidence.get("event_support_score") is not None:
        summary_bits.append(f"event_support={structure_evidence.get('event_support_score')}")
    if structure_evidence.get("baseline_stability_score") is not None:
        summary_bits.append(f"baseline_stability={structure_evidence.get('baseline_stability_score')}")
    if structure_evidence.get("thermodynamic_consistency_score") is not None:
        summary_bits.append(f"thermo_consistency={structure_evidence.get('thermodynamic_consistency_score')}")
    if structure_evidence.get("paper_conclusion_candidate") is not None:
        summary_bits.append(f"paper_candidate={bool(structure_evidence.get('paper_conclusion_candidate'))}")
    if structure_evidence.get("paper_conclusion_ready") is not None:
        summary_bits.append(f"paper_ready={bool(structure_evidence.get('paper_conclusion_ready'))}")
    return {"summary_bits": summary_bits}


__all__ = [
    "_dsc_actionable_lines",
    "_dsc_summary_details",
]
