"""Presentation-only adapter for persisted scientific-review decisions."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

from .i18n import tr_for_language


_GATED_SUBMODULES = {"ir.mapping", "nmr.solid_c", "joint"}
_REASON_STATUS = {
    "review_accepted": "accepted",
    "review_pending": "pending",
    "review_conditional": "conditional",
    "review_rejected": "rejected",
    "review_stale": "stale",
    "review_missing": "required",
    "review_invalid": "invalid",
    "scope_mismatch": "blocked",
    "source_mismatch": "blocked",
}


@dataclass(frozen=True)
class ScientificReviewDisplay:
    """Detached, JSON-safe review state consumed by GUI surfaces."""

    status: str = "not_applicable"
    allowed: bool = False
    reason: str = "not_applicable"
    record_id: str = ""
    scope: str = ""
    source_ref: str = ""
    policy_version: str = ""
    text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _qualified_submodule(technique: str, submodule: str) -> str:
    tech = str(technique or "").strip().lower()
    normalized = str(submodule or "").strip().lower()
    if normalized == "joint" or tech == "joint":
        return "joint"
    if not normalized:
        return normalized
    return normalized if "." in normalized else f"{tech}.{normalized}"


def _review_mapping(value: Any, *, max_depth: int = 8) -> dict[str, Any] | None:
    """Find the first serialized decision without inspecting technique internals."""

    if max_depth < 0 or not isinstance(value, Mapping):
        return None
    for key in ("scientific_review", "scientific_review_decision"):
        candidate = value.get(key)
        if isinstance(candidate, Mapping):
            return dict(candidate)
    for key in ("analysis_evidence", "results_summary", "result", "report", "metadata"):
        candidate = value.get(key)
        found = _review_mapping(candidate, max_depth=max_depth - 1)
        if found is not None:
            return found
    for candidate in value.values():
        if isinstance(candidate, Mapping):
            found = _review_mapping(candidate, max_depth=max_depth - 1)
            if found is not None:
                return found
    return None


def _source_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    payload: dict[str, Any] = {}
    for name in ("analysis_evidence", "metadata", "parameters"):
        candidate = getattr(value, name, None)
        if isinstance(candidate, Mapping):
            payload[name] = dict(candidate)
    return payload


def _label(status: str, language: str) -> str:
    key = {
        "accepted": "SCIENTIFIC_REVIEW_ACCEPTED",
        "pending": "SCIENTIFIC_REVIEW_PENDING",
        "conditional": "SCIENTIFIC_REVIEW_CONDITIONAL",
        "rejected": "SCIENTIFIC_REVIEW_REJECTED",
        "stale": "SCIENTIFIC_REVIEW_STALE",
        "required": "SCIENTIFIC_REVIEW_REQUIRED",
        "invalid": "SCIENTIFIC_REVIEW_INVALID",
        "blocked": "SCIENTIFIC_REVIEW_BLOCKED",
        "not_applicable": "SCIENTIFIC_REVIEW_NOT_APPLICABLE",
    }.get(status, "SCIENTIFIC_REVIEW_REQUIRED")
    return tr_for_language(key, language)


def scientific_review_display(
    value: Any,
    *,
    technique: str = "",
    submodule: str = "",
    language: str = "en",
) -> ScientificReviewDisplay:
    """Normalize one existing review snapshot for all GUI consumers."""

    qualified = _qualified_submodule(technique, submodule)
    review = _review_mapping(_source_mapping(value))
    if review is None:
        status = "required" if qualified in _GATED_SUBMODULES else "not_applicable"
        reason = "review_missing" if status == "required" else "not_applicable"
        return ScientificReviewDisplay(
            status=status,
            reason=reason,
            text=f"{tr_for_language('SCIENTIFIC_REVIEW_LABEL', language)}: {_label(status, language)} | reason={reason}",
        )

    reason = str(review.get("reason") or "").strip().lower()
    allowed = review.get("allowed") is True and reason == "review_accepted"
    record_id = str(review.get("record_id") or "").strip()
    scope = str(review.get("scope") or "").strip()
    source_ref = str(review.get("source_ref") or "").strip()
    policy_version = str(review.get("policy_version") or "").strip()
    if reason == "review_missing":
        status = "required"
        allowed = False
    elif not reason or not record_id or not scope:
        status = "invalid"
        reason = "review_invalid"
        allowed = False
    else:
        status = _REASON_STATUS.get(reason, "invalid")
        if status == "invalid":
            reason = "review_invalid"
            allowed = False

    parts = [
        f"{tr_for_language('SCIENTIFIC_REVIEW_LABEL', language)}: {_label(status, language)}",
        f"reason={reason}",
    ]
    if record_id:
        parts.append(f"record={record_id}")
    if scope:
        parts.append(f"scope={scope}")
    if source_ref:
        parts.append(f"source={source_ref}")
    if policy_version:
        parts.append(f"policy={policy_version}")
    return ScientificReviewDisplay(
        status=status,
        allowed=bool(allowed),
        reason=reason,
        record_id=record_id,
        scope=scope,
        source_ref=source_ref,
        policy_version=policy_version,
        text=" | ".join(parts),
    )


__all__ = ["ScientificReviewDisplay", "scientific_review_display"]
