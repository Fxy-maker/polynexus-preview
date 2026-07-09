from __future__ import annotations

from typing import Any

from .analysis_evidence_saxs_condition_sequence import _saxs_strain_sequence_evidence
from .analysis_evidence_saxs_condition_structure import _saxs_strain_structure_layers
from .analysis_evidence_saxs_condition_values import _condition_values
from .analysis_evidence_utils import _clean_float, _non_empty_mapping


def _saxs_condition_feature_bundle(
    output: dict[str, Any],
    *,
    batch_rows: list[dict[str, Any]] | None = None,
    structure_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    batch_rows = batch_rows if isinstance(batch_rows, list) else []
    structure_evidence = dict(structure_evidence or {})
    feature_evidence: dict[str, Any] = {}
    confidence_signals: list[dict[str, Any]] = []

    condition_label = str(output.get("condition_label", "") or "").strip()
    condition_value = _clean_float(output.get("condition_value"))
    temperature_c = _clean_float(output.get("temperature_C"))
    strain_pct = _clean_float(output.get("strain_pct"))
    condition_source = str(output.get("condition_source", "") or "").strip()
    condition_source_key = str(output.get("condition_source_key", "") or "").strip()
    condition_source_text = str(output.get("condition_source_text", "") or "").strip()
    condition_confidence = _clean_float(output.get("condition_confidence"))
    condition_missing_frames = output.get("condition_missing_frames")
    condition_continuity_score = _clean_float(output.get("condition_continuity_score"))

    condition_evidence: dict[str, Any] = {}
    if (
        condition_label
        or condition_value is not None
        or temperature_c is not None
        or strain_pct is not None
        or condition_source
        or condition_source_key
        or condition_source_text
        or condition_confidence is not None
        or condition_missing_frames not in (None, [], {})
        or condition_continuity_score is not None
    ):
        condition_evidence = _non_empty_mapping(
            [
                ("condition_label", condition_label or None),
                ("condition_value", condition_value),
                ("temperature_C", temperature_c),
                ("strain_pct", strain_pct),
                ("condition_source", condition_source or None),
                ("condition_source_key", condition_source_key or None),
                ("condition_source_text", condition_source_text or None),
                ("condition_confidence", condition_confidence),
                ("condition_missing_frames", condition_missing_frames),
                ("condition_continuity_score", condition_continuity_score),
            ]
        )

        sequence_bundle = _saxs_strain_sequence_evidence(
            output,
            batch_rows,
            condition_label=condition_label,
            condition_source=condition_source,
            condition_source_key=condition_source_key,
            condition_source_text=condition_source_text,
            condition_confidence=condition_confidence,
            condition_missing_frames=condition_missing_frames,
            condition_continuity_score=condition_continuity_score,
        )
        if sequence_bundle:
            feature_evidence.update(sequence_bundle.get("feature_evidence", {}))
            condition_evidence = dict(sequence_bundle.get("condition_evidence", condition_evidence))
            confidence_signals.extend(sequence_bundle.get("confidence_signals", []))

    structure_bundle = _saxs_strain_structure_layers(output, structure_evidence)
    if structure_bundle:
        feature_evidence.update(structure_bundle.get("feature_evidence", {}))
        structure_evidence = dict(structure_bundle.get("structure_evidence", structure_evidence))

    return {
        "condition_evidence": condition_evidence,
        "feature_evidence": feature_evidence,
        "confidence_signals": confidence_signals,
        "structure_evidence": structure_evidence,
    }


__all__ = [
    "_condition_values",
    "_saxs_strain_sequence_evidence",
    "_saxs_strain_structure_layers",
    "_saxs_condition_feature_bundle",
]
