from __future__ import annotations

from typing import Any

from .analysis_evidence_waxs_feature_bundle_core import _waxs_core_feature_evidence
from .analysis_evidence_waxs_feature_bundle_temperature import (
    _waxs_temperature_feature_evidence,
)


def _waxs_feature_bundle(
    output: dict[str, Any],
    *,
    config_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config_snapshot = config_snapshot if isinstance(config_snapshot, dict) else {}
    waxs_core = _waxs_core_feature_evidence(output, config_snapshot=config_snapshot)
    waxs_temperature = _waxs_temperature_feature_evidence(output)

    peak_evidence = waxs_core.get("peak_evidence", {})
    background_evidence = waxs_core.get("background_evidence", {})
    phase_evidence = waxs_core.get("phase_evidence", {})
    structure_evidence = waxs_core.get("structure_evidence", {})
    condition_evidence = waxs_temperature.get("condition_evidence", {})

    feature_evidence: dict[str, Any] = {}
    if peak_evidence:
        feature_evidence["peak_evidence"] = peak_evidence
    if background_evidence:
        feature_evidence["background_evidence"] = background_evidence
    if phase_evidence:
        feature_evidence["phase_evidence"] = phase_evidence
    if structure_evidence:
        feature_evidence["structure_evidence"] = structure_evidence
    if condition_evidence:
        feature_evidence["sequence_evidence"] = condition_evidence
        feature_evidence["condition_evidence"] = condition_evidence

    frame_evidence_records = waxs_temperature.get("frame_evidence", [])
    if isinstance(frame_evidence_records, list) and frame_evidence_records:
        feature_evidence["frame_evidence"] = frame_evidence_records

    for key in (
        "frame_summary_evidence",
        "peak_family_evidence",
        "scherrer_trend_evidence",
        "transition_evidence",
    ):
        section = waxs_temperature.get(key, {})
        if section:
            feature_evidence[key] = section

    crystallinity_trend_evidence = waxs_temperature.get("crystallinity_trend_evidence", {})
    if crystallinity_trend_evidence:
        feature_evidence["trend_evidence"] = crystallinity_trend_evidence
        feature_evidence["crystallinity_trend_evidence"] = crystallinity_trend_evidence

    confidence_signals: list[dict[str, Any]] = []
    peak_count = waxs_core.get("peak_count")
    if peak_evidence and peak_count is not None:
        confidence_signals.append({"name": "peak_count", "value": peak_count, "source": "WAXS"})
    structure_support = waxs_core.get("structure_support_score")
    if structure_evidence and structure_support is not None:
        confidence_signals.append(
            {
                "name": "structure_support_score",
                "value": structure_support,
                "source": "WAXS",
            }
        )
    confidence_signals.extend(waxs_temperature.get("confidence_signals", []))

    return {
        "peak_evidence": peak_evidence,
        "background_evidence": background_evidence,
        "phase_evidence": phase_evidence,
        "structure_evidence": structure_evidence,
        "condition_evidence": condition_evidence,
        "feature_evidence": feature_evidence,
        "confidence_signals": confidence_signals,
    }


__all__ = [
    "_waxs_core_feature_evidence",
    "_waxs_temperature_feature_evidence",
    "_waxs_feature_bundle",
]
