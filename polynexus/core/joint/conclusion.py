"""Reviewer-owned, fail-closed Joint conclusion classification."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..scientific_review import validate_review_record, review_record_from_payload


_POLICY_KEYS = (
    "conflict_precedence",
    "minimum_evidence",
    "unresolved_conflict_policy",
)
_REVIEW_REQUIRED_REASONS = {
    "review_missing",
    "review_invalid",
    "scope_mismatch",
    "source_mismatch",
    "review_pending",
    "review_stale",
}


def _review_projection(value: Any) -> dict[str, Any] | None:
    record = review_record_from_payload(value)
    if record is None or record.scope != "joint":
        return None
    try:
        validate_review_record(record)
        payload = record.to_dict()
    except (TypeError, ValueError):
        return None
    decisions = payload.get("decisions", {})
    return {
        "record_id": payload["record_id"],
        "scope": payload["scope"],
        "status": payload["status"],
        "policy_version": payload["policy_version"],
        "source_refs": list(payload["source_refs"]),
        "decisions": {
            key: decisions[key]
            for key in _POLICY_KEYS
            if key in decisions
        },
    }


def _issue_counts(
    validation_rows: Sequence[Mapping[str, Any]],
    technique_issue_rows: Sequence[Mapping[str, Any]],
) -> tuple[int, int]:
    error_count = 0
    warning_count = 0
    for item in (*validation_rows, *technique_issue_rows):
        if str(item.get("status") or "").strip().upper() == "SKIP":
            continue
        severity = str(item.get("severity") or "").strip().upper()
        if severity == "ERROR":
            error_count += 1
        elif severity == "WARN":
            warning_count += 1
    return error_count, warning_count


def classify_joint_conclusion(
    *,
    review_records: Sequence[Any],
    review_snapshot: Mapping[str, Any],
    validation_rows: Sequence[Mapping[str, Any]],
    technique_issue_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Classify Joint readiness without interpreting reviewer policy text."""

    projections = [_review_projection(value) for value in review_records]
    valid_projections = [item for item in projections if item is not None]
    snapshot_reason = str(review_snapshot.get("reason") or "review_invalid").strip()
    statuses = [str(item["status"]) for item in valid_projections]
    error_count, warning_count = _issue_counts(validation_rows, technique_issue_rows)

    conclusion_class = "review_required"
    reason = snapshot_reason if snapshot_reason in _REVIEW_REQUIRED_REASONS else "review_invalid"
    if not projections or len(valid_projections) != len(projections):
        conclusion_class = "review_required"
    elif any(status == "rejected" for status in statuses):
        conclusion_class = "rejected"
        reason = "review_rejected"
    elif any(status == "conditional" for status in statuses):
        conclusion_class = "conditional"
        reason = "review_conditional"
    elif any(status in {"pending", "stale"} for status in statuses):
        conclusion_class = "review_required"
        reason = f"review_{statuses[0]}"
    elif not bool(review_snapshot.get("allowed")):
        conclusion_class = "review_required"
    elif error_count:
        conclusion_class = "blocked"
        reason = "conflict_error"
    elif warning_count:
        conclusion_class = "conditional"
        reason = "conflict_warning"
    else:
        conclusion_class = "accepted"
        reason = "review_accepted"

    review_status = ""
    if statuses:
        review_status = statuses[0] if len(set(statuses)) == 1 else "mixed"
    return {
        "class": conclusion_class,
        "allowed": conclusion_class == "accepted",
        "reason": reason,
        "scope": "joint",
        "review_status": review_status,
        "review_records": valid_projections,
        "validation": {
            "issue_count": error_count + warning_count,
            "error_count": error_count,
            "warning_count": warning_count,
        },
    }


__all__ = ["classify_joint_conclusion"]
