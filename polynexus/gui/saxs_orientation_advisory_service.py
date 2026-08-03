"""Presentation and persistence helpers for the read-only SAXS advisory."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class OrientationAdvisoryActionState:
    visible: bool
    enabled: bool
    reason_codes: tuple[str, ...] = ()


_CODE_LABELS = {
    "stable_common_q_support": ("共同 q 支撑稳定", "stable common-q support"),
    "wide_stability_bound": ("稳定性区间较宽", "wide stability bound"),
    "artifact_sensitivity_present": ("存在伪影敏感性", "artifact sensitivity present"),
    "reference_axis_missing": ("缺少参考轴", "reference axis missing"),
    "calibration_unavailable": ("校准证据不可用", "calibration evidence unavailable"),
    "systematic_harmonic_suspected": ("疑似系统谐波", "suspected systematic harmonic"),
    "local_evidence_diagnostic": ("局部证据为诊断级", "local evidence is diagnostic"),
    "inspect_q_band": ("检查 q 区间", "inspect q band"),
    "verify_tensile_axis": ("核对拉伸轴", "verify tensile axis"),
    "acquire_background_standard": ("补充背景/标准样", "acquire background or standard"),
    "inspect_beam_center": ("检查光束中心", "inspect beam center"),
    "compare_mask_sensitivity": ("比较掩膜敏感性", "compare mask sensitivity"),
    "request_scientific_review": ("请求科学复核", "request scientific review"),
}


def _source_payload(result: Any) -> Mapping[str, Any]:
    if isinstance(result, Mapping):
        return result
    parameters = getattr(result, "parameters", None)
    return parameters if isinstance(parameters, Mapping) else {}


def orientation_advisory_action_context(result: Any) -> dict[str, Any]:
    """Build the detached advisory input from existing SAXS evidence only."""

    payload = _source_payload(result)
    existing = payload.get("orientation_advisory_context")
    if isinstance(existing, Mapping):
        return dict(existing)

    from ..core.saxs_engine.saxs_2d_review_context import build_saxs_2d_review_context
    from ..core.saxs_engine.saxs_orientation_advisory import build_orientation_advisory_context

    review = build_saxs_2d_review_context(payload)
    return build_orientation_advisory_context({"saxs_2d_review_context": review})


def orientation_advisory_action_state(result: Any) -> OrientationAdvisoryActionState:
    payload = _source_payload(result)
    technique = str(payload.get("technique", getattr(result, "technique", "")) or "").strip().lower()
    mode = str(payload.get("mode", payload.get("experiment_type", "")) or "").strip().lower()
    context = orientation_advisory_action_context(result)
    candidates = context.get("candidates", ())
    visible = technique == "saxs" and mode in {"strain", "tensile"} and bool(candidates)
    reasons = () if visible else ("orientation_advisory_context_ineligible",)
    return OrientationAdvisoryActionState(visible=visible, enabled=visible, reason_codes=reasons)


def persist_orientation_advisory_report(
    parameters: Mapping[str, Any],
    report: Any,
) -> dict[str, Any]:
    """Copy only the detached report; never mark tuning/review/publication state."""

    payload = dict(parameters) if isinstance(parameters, Mapping) else {}
    report_dict = report.to_dict() if hasattr(report, "to_dict") else dict(report or {})
    payload["saxs_orientation_advisory_report"] = report_dict
    return payload


def restore_orientation_advisory_report(parameters: Mapping[str, Any]) -> dict[str, Any]:
    value = parameters.get("saxs_orientation_advisory_report") if isinstance(parameters, Mapping) else None
    return dict(value) if isinstance(value, Mapping) else {}


def render_orientation_advisory_report(report: Any, *, language: str = "zh") -> dict[str, Any]:
    payload = report.to_dict() if hasattr(report, "to_dict") else dict(report or {})
    zh = str(language or "").lower().startswith("zh")

    def label(code: str) -> str:
        pair = _CODE_LABELS.get(code)
        return pair[0 if zh else 1] if pair else code

    observations = payload.get("candidate_observations", ())
    rows = []
    for item in observations if isinstance(observations, (list, tuple)) else ():
        if not isinstance(item, Mapping):
            continue
        rows.append({
            "candidate_id": str(item.get("candidate_id") or ""),
            "q_min_nm1": item.get("q_min_nm1"),
            "q_max_nm1": item.get("q_max_nm1"),
            "f_reference": item.get("f_reference"),
            "delta_f_from_zero": item.get("delta_f_from_zero"),
            "reliability_status": item.get("reliability_status"),
        })
    return {
        "status": str(payload.get("status") or "limited"),
        "ranked_candidate_ids": [str(item) for item in payload.get("ranked_candidate_ids", ())],
        "candidate_rows": rows,
        "comparison_summary": [label(str(item)) for item in payload.get("comparison_summary_codes", ())],
        "artifact_risks": [label(str(item)) for item in payload.get("artifact_risk_codes", ())],
        "limitations": [label(str(item)) for item in payload.get("limitation_codes", ())],
        "recommended_actions": [label(str(item)) for item in payload.get("recommended_review_action_codes", ())],
        "source_evidence_digest": str(payload.get("source_evidence_digest") or ""),
    }


__all__ = [
    "OrientationAdvisoryActionState",
    "orientation_advisory_action_context",
    "orientation_advisory_action_state",
    "persist_orientation_advisory_report",
    "restore_orientation_advisory_report",
    "render_orientation_advisory_report",
]
