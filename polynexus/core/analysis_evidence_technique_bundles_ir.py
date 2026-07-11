from __future__ import annotations

from typing import Any

from .analysis_evidence_ir import (
    _ir_static_analysis_bundle,
    _ir_temperature_2d_feature_bundle,
)
from .analysis_evidence_physical import _ir_temperature_2d_metrics


def build_ir_technique_bundle(
    output: dict[str, Any],
    validation: dict[str, Any],
    *,
    is_temperature_2d: bool,
    feature_evidence: dict[str, Any],
) -> dict[str, Any]:
    feature_evidence = dict(feature_evidence)
    if is_temperature_2d:
        temperature_2d_metrics = _ir_temperature_2d_metrics(output, validation)
        temperature_2d_bundle = _ir_temperature_2d_feature_bundle(temperature_2d_metrics)
        signal_evidence = temperature_2d_bundle.get("signal_evidence", {})
        peak_evidence = temperature_2d_bundle.get("peak_evidence", {})
        transform_evidence = temperature_2d_bundle.get("transform_evidence", {})
        structure_evidence = temperature_2d_bundle.get("structure_evidence", {})
        feature_evidence.update(temperature_2d_bundle.get("feature_evidence", {}))
        confidence_signals = list(temperature_2d_bundle.get("confidence_signals", []))
        return {
            "feature_evidence": feature_evidence,
            "signal_evidence": signal_evidence,
            "peak_evidence": peak_evidence,
            "transform_evidence": transform_evidence,
            "structure_evidence": structure_evidence,
            "confidence_signals": confidence_signals,
        }

    ir_static_bundle = _ir_static_analysis_bundle(output, validation)
    signal_evidence = ir_static_bundle.get("signal_evidence", {})
    peak_evidence = ir_static_bundle.get("peak_evidence", {})
    background_evidence = ir_static_bundle.get("background_evidence", {})
    assignment_evidence = ir_static_bundle.get("assignment_evidence", {})
    reference_evidence = ir_static_bundle.get("reference_evidence", {})
    phase_evidence = ir_static_bundle.get("phase_evidence", {})
    structure_evidence = ir_static_bundle.get("structure_evidence", {})
    feature_evidence.update(ir_static_bundle.get("feature_evidence", {}))
    confidence_signals = list(ir_static_bundle.get("confidence_signals", []))
    return {
        "feature_evidence": feature_evidence,
        "signal_evidence": signal_evidence,
        "peak_evidence": peak_evidence,
        "background_evidence": background_evidence,
        "assignment_evidence": assignment_evidence,
        "reference_evidence": reference_evidence,
        "phase_evidence": phase_evidence,
        "structure_evidence": structure_evidence,
        "confidence_signals": confidence_signals,
    }
