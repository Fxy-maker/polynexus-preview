from __future__ import annotations

from typing import Any

from .analysis_evidence_common import _common_summary_details
from .analysis_evidence_dsc import _dsc_summary_details
from .analysis_evidence_ir import _ir_summary_details, _ir_temperature_2d_summary_details
from .analysis_evidence_nmr import _nmr_summary_details
from .analysis_evidence_physical import _ir_temperature_2d_metrics
from .analysis_evidence_saxs import _saxs_summary_details
from .analysis_evidence_waxs import _waxs_summary_details


def build_analysis_summary(
    technique_key: str,
    *,
    is_ir_temperature_2d: bool,
    output: dict[str, Any],
    validation: dict[str, Any],
    quality_flag: str,
    residual_type: str,
    risk_flags: list[str],
    constraints: list[dict[str, Any]],
    constraint_summary: dict[str, Any],
    signal_evidence: dict[str, Any],
    peak_evidence: dict[str, Any],
    assignment_evidence: dict[str, Any],
    reference_evidence: dict[str, Any],
    structure_evidence: dict[str, Any],
    batch_evidence: dict[str, Any],
    condition_evidence: dict[str, Any],
    stability_evidence: dict[str, Any],
    raw_structure_evidence: dict[str, Any],
    confidence_signals: list[dict[str, Any]],
) -> dict[str, Any]:
    updated_confidence_signals = list(confidence_signals)

    common_summary = _common_summary_details(
        quality_flag=quality_flag,
        residual_type=residual_type,
        risk_flags=risk_flags,
        constraints=constraints,
        constraint_summary=constraint_summary,
    )
    summary_bits = list(common_summary.get("summary_bits", []))

    if technique_key == "NMR":
        nmr_summary = _nmr_summary_details(signal_evidence, peak_evidence, structure_evidence)
        summary_bits.extend(nmr_summary.get("summary_bits", []))

    if technique_key == "SAXS":
        saxs_summary = _saxs_summary_details(
            batch_evidence,
            condition_evidence,
            structure_evidence,
            stability_evidence,
            raw_structure_evidence,
        )
        summary_bits.extend(saxs_summary.get("summary_bits", []))

    if technique_key == "DSC":
        dsc_summary = _dsc_summary_details(structure_evidence)
        summary_bits.extend(dsc_summary.get("summary_bits", []))

    if technique_key == "WAXS":
        waxs_summary = _waxs_summary_details(output, peak_evidence, structure_evidence, condition_evidence)
        summary_bits.extend(waxs_summary.get("summary_bits", []))
        updated_confidence_signals.extend(waxs_summary.get("confidence_signals", []))

    if is_ir_temperature_2d:
        temp_metrics = _ir_temperature_2d_metrics(output, validation)
        ir_2d_summary = _ir_temperature_2d_summary_details(temp_metrics)
        summary_bits.extend(ir_2d_summary.get("summary_bits", []))
    elif technique_key == "IR":
        ir_summary = _ir_summary_details(
            peak_evidence,
            assignment_evidence,
            reference_evidence,
            structure_evidence,
        )
        summary_bits.extend(ir_summary.get("summary_bits", []))

    return {
        "summary": "; ".join(summary_bits),
        "confidence_signals": updated_confidence_signals,
    }
