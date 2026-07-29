"""Publish SAXS internal status through the generic result contract."""

from __future__ import annotations

import json
from collections.abc import MutableMapping
from typing import Any, Mapping

import numpy as np

from .analysis_evidence import build_analysis_evidence
from .saxs_engine.figure_common import frame_views_from_engine
from .saxs_engine.figure_evidence import configured_saxs_review_evidence


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if np.isfinite(number) else None


def _analyses(engine: Any) -> list[Any]:
    batch = getattr(engine, "_batch_results", ()) or ()
    if batch:
        return [item for item in batch if item is not None]
    analysis = getattr(engine, "_analysis", None)
    return [analysis] if analysis is not None else []


def _unique_text(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _severity(flags: list[str]) -> str:
    if any(flag.startswith("ERROR:") for flag in flags):
        return "ERROR"
    if any(flag.startswith("WARN:") for flag in flags):
        return "WARN"
    return "OK"


def _fallback_frame(
    index: int,
    analysis: Any,
    parameters: Mapping[str, Any] | None,
) -> dict[str, Any]:
    source = dict(parameters or {})
    internal = getattr(analysis, "final_parameters", {})
    merged = {**internal, **source} if isinstance(internal, Mapping) else source
    method = str(merged.get("lc_method", "") or "").strip()
    reason = str(
        merged.get("calibrated_fallback_reason")
        or merged.get("fallback_reason")
        or ""
    ).strip()
    fields = merged.get("fallback_applied_fields", [])
    if not isinstance(fields, list):
        fields = [str(fields)] if fields else []
    return {
        "index": index,
        "file": str(merged.get("file", "") or ""),
        "method": method or "unknown",
        "reason": reason or "unknown",
        "applied_fields": [str(item) for item in fields],
    }


def _record_write_failure(
    diagnostics: dict[str, str], field: str, exc: Exception
) -> None:
    diagnostics[field] = f"{type(exc).__name__}:{exc}"


def _safe_setattr(
    target: Any,
    field: str,
    value: Any,
    diagnostics: dict[str, str],
) -> None:
    try:
        setattr(target, field, value)
    except Exception as exc:
        _record_write_failure(diagnostics, field, exc)


def publish_saxs_result_contract(engine: Any) -> dict[str, Any]:
    """Map SAXS internal results into ``engine.result`` and return the payload."""
    result = getattr(engine, "result", None)
    if result is None:
        return {}

    analyses = _analyses(engine)
    write_diagnostics: dict[str, str] = {}
    frame_parameters = getattr(engine, "_batch_params", ()) or ()
    quality_flags = _unique_text([
        str(getattr(item, "quality_flag", "") or "").strip()
        for item in analyses
    ])
    summaries = _unique_text([
        str(getattr(item, "validation_summary", "") or "").strip()
        for item in analyses
        if str(getattr(item, "validation_summary", "") or "").strip()
        != "All checks passed"
    ])
    severity = _severity(quality_flags)
    if not analyses and not bool(getattr(result, "validation_passed", True)):
        severity = "ERROR"
    existing_summary = str(getattr(result, "validation_summary", "") or "").strip()
    summary = "; ".join(summaries) or existing_summary

    effective_q_values = [
        value
        for value in (_finite(getattr(item, "effective_q_min", np.nan)) for item in analyses)
        if value is not None
    ]
    # Each frame contributes a lower-bound constraint; the common range uses
    # the most restrictive (largest) finite lower bound.
    effective_q_min = max(effective_q_values) if effective_q_values else _finite(
        getattr(result, "effective_q_min", np.nan)
    )
    qstar_values = [
        bool(value)
        for item in analyses
        for value in (getattr(item, "Q_star_valid", None),)
        if value is not None
    ]
    q_star_valid = all(qstar_values) if qstar_values else None
    q_star_statuses = _unique_text([
        str(getattr(item, "Q_star_status", "") or "").strip()
        for item in analyses
    ])
    q_star_reasons = _unique_text([
        str(reason).strip()
        for item in analyses
        for reason in (getattr(item, "Q_star_reasons", []) or [])
    ])

    fallback_frames = [
        _fallback_frame(
            index,
            analysis,
            frame_parameters[index] if index < len(frame_parameters) else None,
        )
        for index, analysis in enumerate(analyses)
    ]
    fallback_provenance: dict[str, Any] = {
        "mode": "single" if len(fallback_frames) == 1 else "sequence",
        "frames": fallback_frames,
    }

    parameters = dict(getattr(result, "parameters", {}) or {})
    # Preserve the empty-analysis OK convention for compatibility; a failed
    # generic validation is still promoted to ERROR above.
    quality_flag = ";".join(quality_flags) or ("OK" if not analyses else "unknown")
    parameters.update(
        {
            "quality_flag": quality_flag,
            "validation_summary": summary,
            "effective_q_min": effective_q_min,
            "Q_star_valid": q_star_valid,
            "Q_star_status": ";".join(q_star_statuses) or "unknown",
            "Q_star_reasons": q_star_reasons,
            "fallback_provenance": fallback_provenance,
        }
    )
    review_evidence = configured_saxs_review_evidence(
        engine,
        frame_views_from_engine(engine),
    )
    if review_evidence is not None:
        parameters["scientific_review"] = review_evidence
    _safe_setattr(result, "parameters", parameters, write_diagnostics)
    try:
        existing_quality_flags = getattr(result, "quality_flags", None)
        if isinstance(existing_quality_flags, MutableMapping):
            existing_quality_flags["saxs"] = severity
        else:
            quality_flags_payload = dict(existing_quality_flags or {})
            quality_flags_payload["saxs"] = severity
            _safe_setattr(result, "quality_flags", quality_flags_payload, write_diagnostics)
    except Exception as exc:
        _record_write_failure(write_diagnostics, "quality_flags", exc)
    if summary:
        _safe_setattr(result, "validation_summary", summary, write_diagnostics)
    if effective_q_min is not None:
        _safe_setattr(result, "effective_q_min", effective_q_min, write_diagnostics)
    if severity == "ERROR":
        _safe_setattr(result, "validation_passed", False, write_diagnostics)

    evidence_reasons = _unique_text(quality_flags + summaries)
    validation_context = {
        "saxs_contract": {
            "effective_q_min": effective_q_min,
            "Q_star_valid": q_star_valid,
            "fallback_provenance": fallback_provenance,
            "frame_count": len(analyses),
        },
    }
    evidence = build_analysis_evidence(
        "SAXS",
        output_parameters=parameters,
        residual_pattern={},
        validation_context=validation_context,
    ).to_dict()
    existing_evidence = getattr(result, "analysis_evidence", {})
    if isinstance(existing_evidence, dict) and "sequence_qa" in existing_evidence:
        evidence["sequence_qa"] = existing_evidence["sequence_qa"]
    evidence["contract"] = {
        "quality_flag": parameters["quality_flag"],
        "validation_summary": summary,
        "evidence_reasons": evidence_reasons,
        "effective_q_min": effective_q_min,
        "Q_star_valid": q_star_valid,
        "Q_star_status": ";".join(q_star_statuses) or "unknown",
        "Q_star_reasons": q_star_reasons,
        "fallback_provenance": fallback_provenance,
        "frame_count": len(analyses),
    }
    if "sequence_qa" in evidence:
        evidence["contract"]["sequence_qa"] = evidence["sequence_qa"]

    metadata = getattr(result, "metadata", None)
    metadata_updated = False
    metadata_payload = {
        "saxs_contract_version": "1",
        "saxs_quality_flag": parameters["quality_flag"],
        "saxs_fallback_provenance": json.dumps(
            fallback_provenance, ensure_ascii=False, default=str
        ),
        "saxs_evidence_reasons": json.dumps(evidence_reasons, ensure_ascii=False),
    }
    if isinstance(metadata, MutableMapping):
        try:
            metadata.update(metadata_payload)
            metadata_updated = True
        except Exception as exc:
            _record_write_failure(write_diagnostics, "metadata", exc)
    else:
        write_diagnostics["metadata"] = "metadata_not_dict"

    evidence["contract"]["metadata_updated"] = metadata_updated
    evidence["contract"]["write_diagnostics"] = dict(write_diagnostics)
    setter = getattr(result, "set_analysis_evidence", None)
    try:
        if callable(setter):
            setter(evidence)
        else:
            setattr(result, "analysis_evidence", evidence)
    except Exception as exc:
        _record_write_failure(write_diagnostics, "analysis_evidence", exc)
        evidence["contract"]["write_diagnostics"] = dict(write_diagnostics)

    return evidence["contract"]


__all__ = ["publish_saxs_result_contract"]
