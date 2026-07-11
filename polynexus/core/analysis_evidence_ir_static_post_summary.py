from __future__ import annotations

from typing import Any


def _ir_summary_details(
    peak_evidence: dict[str, Any],
    assignment_evidence: dict[str, Any],
    reference_evidence: dict[str, Any],
    structure_evidence: dict[str, Any],
) -> dict[str, Any]:
    summary_bits: list[str] = []

    if peak_evidence.get("peak_count") is not None:
        summary_bits.append(f"peak_count={peak_evidence.get('peak_count')}")
    if assignment_evidence.get("assignment_confidence") is not None:
        summary_bits.append(
            f"assignment_confidence={assignment_evidence.get('assignment_confidence')}"
        )
    if assignment_evidence.get("key_band_support_score") is not None:
        summary_bits.append(
            f"key_band_support={assignment_evidence.get('key_band_support_score')}"
        )
    if assignment_evidence.get("peak_coverage_score") is not None:
        summary_bits.append(
            f"peak_coverage={assignment_evidence.get('peak_coverage_score')}"
        )
    if structure_evidence.get("baseline_stability_score") is not None:
        summary_bits.append(
            f"baseline_stability={structure_evidence.get('baseline_stability_score')}"
        )
    if reference_evidence.get("band_count") is not None:
        summary_bits.append(f"ref_bands={reference_evidence.get('band_count')}")
    if reference_evidence.get("hit_count") is not None:
        summary_bits.append(f"ref_hits={reference_evidence.get('hit_count')}")
    if structure_evidence.get("reference_band_missing_count") is not None:
        summary_bits.append(
            f"ref_missing={structure_evidence.get('reference_band_missing_count')}"
        )
    if structure_evidence.get("characteristic_band_support_ok") is not None:
        summary_bits.append(
            f"band_support={bool(structure_evidence.get('characteristic_band_support_ok'))}"
        )
    if structure_evidence.get("paper_conclusion_ready") is not None:
        summary_bits.append(
            f"paper_ready={bool(structure_evidence.get('paper_conclusion_ready'))}"
        )

    return {"summary_bits": summary_bits}


__all__ = ["_ir_summary_details"]
