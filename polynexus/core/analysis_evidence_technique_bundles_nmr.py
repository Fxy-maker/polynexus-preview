from __future__ import annotations

from typing import Any

from .analysis_evidence_nmr import _nmr_analysis_bundle


def build_nmr_technique_bundle(
    output: dict[str, Any],
    *,
    feature_evidence: dict[str, Any],
) -> dict[str, Any]:
    feature_evidence = dict(feature_evidence)
    nmr_bundle = _nmr_analysis_bundle(output)
    signal_evidence = nmr_bundle.get("signal_evidence", {})
    peak_evidence = nmr_bundle.get("peak_evidence", {})
    assignment_evidence = nmr_bundle.get("assignment_evidence", {})
    phase_evidence = nmr_bundle.get("phase_evidence", {})
    structure_evidence = nmr_bundle.get("structure_evidence", {})
    feature_evidence.update(nmr_bundle.get("feature_evidence", {}))
    confidence_signals = list(nmr_bundle.get("confidence_signals", []))
    return {
        "feature_evidence": feature_evidence,
        "signal_evidence": signal_evidence,
        "peak_evidence": peak_evidence,
        "assignment_evidence": assignment_evidence,
        "phase_evidence": phase_evidence,
        "structure_evidence": structure_evidence,
        "confidence_signals": confidence_signals,
    }
