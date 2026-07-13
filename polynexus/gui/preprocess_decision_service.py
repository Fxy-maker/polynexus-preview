from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


PROTECTED_METRICS = (
    "noise_reduction",
    "baseline_flatness",
    "peak_shift",
    "fwhm_change",
    "integrated_area_change",
    "weak_peak_retention",
    "physical_parameter_drift",
)


@dataclass(frozen=True)
class PreprocessUIDecision:
    mode: str
    title: str
    summary: str
    metric_rows: dict[str, Any] = field(default_factory=dict)
    reason_codes: tuple[str, ...] = ()
    apply_enabled: bool = False
    undo_enabled: bool = False
    selected_config: dict[str, Any] = field(default_factory=dict)


def _selected_evidence(report: dict[str, Any]) -> dict[str, Any]:
    rows = report.get("preprocess_evidence", [])
    if not isinstance(rows, list):
        return {}
    selected_id = str(report.get("selected_candidate_id", "") or "")
    if selected_id:
        for item in rows:
            if isinstance(item, dict) and str(item.get("candidate_id", "")) == selected_id:
                return item
    for item in reversed(rows):
        if isinstance(item, dict):
            return item
    return {}


def build_preprocess_ui_decision(report: object) -> PreprocessUIDecision:
    payload = report if isinstance(report, dict) else {}
    raw_decision = payload.get("preprocess_decision", {})
    decision = raw_decision if isinstance(raw_decision, dict) else {}
    decision_name = str(decision.get("decision", "keep_original") or "keep_original")
    simulated = str(decision.get("simulated_decision", decision_name) or decision_name)
    confidence = str(decision.get("confidence_band", "low") or "low")

    if decision_name == "auto_accept":
        mode = "auto_apply"
        title = "Preprocessing automatically selected"
        apply_enabled = False
        undo_enabled = True
    elif decision_name == "request_confirmation":
        mode = "confirm"
        title = "Confirm preprocessing change"
        apply_enabled = True
        undo_enabled = False
    elif simulated != "keep_original":
        mode = "shadow"
        title = "Preprocessing shadow result"
        apply_enabled = False
        undo_enabled = False
    else:
        mode = "keep_original"
        title = "Original preprocessing retained"
        apply_enabled = False
        undo_enabled = False

    evidence = _selected_evidence(payload)
    metric_rows = {
        name: evidence[name]
        for name in PROTECTED_METRICS
        if name in evidence and evidence[name] is not None
    }
    reason_codes = tuple(str(item) for item in decision.get("reason_codes", []))
    summary = (
        f"Decision: {decision_name}; confidence: {confidence}; "
        f"protected metrics available: {len(metric_rows)}."
    )
    selected_config = payload.get("selected_preprocess_config", {})
    if not isinstance(selected_config, dict):
        selected_config = {}
    return PreprocessUIDecision(
        mode=mode,
        title=title,
        summary=summary,
        metric_rows=deepcopy(metric_rows),
        reason_codes=reason_codes,
        apply_enabled=apply_enabled,
        undo_enabled=undo_enabled,
        selected_config=deepcopy(selected_config),
    )
