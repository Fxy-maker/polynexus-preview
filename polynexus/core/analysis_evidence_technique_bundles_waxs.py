from __future__ import annotations

from typing import Any

from .analysis_evidence_waxs import _waxs_feature_bundle


def build_waxs_technique_bundle(
    output: dict[str, Any],
    validation: dict[str, Any],
    *,
    feature_evidence: dict[str, Any],
) -> dict[str, Any]:
    feature_evidence = dict(feature_evidence)
    config_snapshot = validation.get("config_snapshot", {}) if isinstance(validation.get("config_snapshot", {}), dict) else {}
    waxs_bundle = _waxs_feature_bundle(output, config_snapshot=config_snapshot)
    peak_evidence = waxs_bundle.get("peak_evidence", {})
    background_evidence = waxs_bundle.get("background_evidence", {})
    phase_evidence = waxs_bundle.get("phase_evidence", {})
    structure_evidence = waxs_bundle.get("structure_evidence", {})
    condition_evidence = waxs_bundle.get("condition_evidence", {})
    feature_evidence.update(waxs_bundle.get("feature_evidence", {}))
    confidence_signals = list(waxs_bundle.get("confidence_signals", []))
    return {
        "feature_evidence": feature_evidence,
        "peak_evidence": peak_evidence,
        "background_evidence": background_evidence,
        "phase_evidence": phase_evidence,
        "structure_evidence": structure_evidence,
        "condition_evidence": condition_evidence,
        "confidence_signals": confidence_signals,
    }
