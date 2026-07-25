"""Shared deterministic handoff from engine results to AnalysisEvidence."""

from __future__ import annotations

from typing import Any

from .analysis_evidence import build_analysis_evidence


def refresh_analysis_evidence(engine: Any) -> dict[str, Any]:
    """Attach shared evidence without replacing a richer existing payload."""
    result = engine.result
    if result.analysis_evidence:
        return dict(result.analysis_evidence)

    params = dict(result.parameters or {})
    results = getattr(engine, "_results", ())
    first = results[0] if isinstance(results, (list, tuple)) and results else None
    first_params = getattr(first, "parameters", None)
    if callable(first_params):
        first_params = first_params()
    if isinstance(first_params, dict):
        merged = dict(first_params)
        merged.update(
            {
                key: value
                for key, value in params.items()
                if not isinstance(value, dict)
            }
        )
        params = merged
    if not params:
        return {}

    evidence = build_analysis_evidence(
        str(getattr(engine, "name", "") or "").upper(),
        output_parameters=params,
        residual_pattern={},
        validation_context={
            "submodule_id": str(getattr(engine, "active_submodule", "") or ""),
            "quality_flags": dict(result.quality_flags or {}),
            "validation_warnings": list(result.validation_warnings or []),
            "validation_summary": str(result.validation_summary or ""),
        },
    ).to_dict()
    result.set_analysis_evidence(evidence)
    return evidence
