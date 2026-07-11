from __future__ import annotations

from typing import Any

from .analysis_evidence_saxs import (
    _saxs_condition_feature_bundle,
    _saxs_context_bundle,
    _saxs_core_feature_bundle,
)


def build_saxs_technique_bundle(
    output: dict[str, Any],
    *,
    quality_flag: str,
    validation_summary: str,
    feature_evidence: dict[str, Any],
) -> dict[str, Any]:
    feature_evidence = dict(feature_evidence)

    saxs_core_bundle = _saxs_core_feature_bundle(
        output,
        quality_flag=quality_flag,
        validation_summary=validation_summary,
    )
    signal_evidence = saxs_core_bundle.get("signal_evidence", {})
    peak_evidence = saxs_core_bundle.get("peak_evidence", {})
    transform_evidence = saxs_core_bundle.get("transform_evidence", {})
    structure_evidence = saxs_core_bundle.get("structure_evidence", {})

    batch_rows = output.get("_batch_data")
    saxs_context_bundle = _saxs_context_bundle(
        output,
        batch_rows=batch_rows if isinstance(batch_rows, list) else [],
    )
    feature_evidence.update(saxs_context_bundle.get("feature_evidence", {}))
    raw_structure_evidence = saxs_context_bundle.get("raw_structure_evidence", {})
    batch_evidence = saxs_context_bundle.get("batch_evidence", {})

    saxs_condition_bundle = _saxs_condition_feature_bundle(
        output,
        batch_rows=batch_rows if isinstance(batch_rows, list) else [],
        structure_evidence=structure_evidence,
    )
    condition_evidence = saxs_condition_bundle.get("condition_evidence", {})
    feature_evidence.update(saxs_condition_bundle.get("feature_evidence", {}))
    structure_evidence = saxs_condition_bundle.get("structure_evidence", structure_evidence)
    confidence_signals = list(saxs_condition_bundle.get("confidence_signals", []))

    if signal_evidence:
        feature_evidence.setdefault("signal_evidence", signal_evidence)
    if peak_evidence:
        feature_evidence.setdefault("peak_evidence", peak_evidence)
    if transform_evidence:
        feature_evidence.setdefault("transform_evidence", transform_evidence)
    if structure_evidence:
        feature_evidence.setdefault("structure_evidence", structure_evidence)
    if raw_structure_evidence:
        feature_evidence.setdefault("raw_structure_evidence", raw_structure_evidence)
    if batch_evidence:
        feature_evidence.setdefault("batch_evidence", batch_evidence)
    if condition_evidence:
        feature_evidence.setdefault("condition_evidence", condition_evidence)

    return {
        "feature_evidence": feature_evidence,
        "signal_evidence": signal_evidence,
        "peak_evidence": peak_evidence,
        "transform_evidence": transform_evidence,
        "structure_evidence": structure_evidence,
        "raw_structure_evidence": raw_structure_evidence,
        "batch_evidence": batch_evidence,
        "condition_evidence": condition_evidence,
        "confidence_signals": confidence_signals,
    }
