"""Immutable, fail-closed contracts for human scientific review records."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field, is_dataclass
import json
import math
from numbers import Real
from pathlib import Path
from types import MappingProxyType
from typing import Any


REVIEW_SCOPES = frozenset(
    {"ir.mapping", "nmr.solid_c", "joint", "release", "saxs.1d", "saxs.2d"}
)
REVIEW_STATUSES = frozenset({"pending", "accepted", "conditional", "rejected", "stale"})

_REQUIRED_DECISION_KEYS: dict[str, tuple[str, ...]] = {
    "ir.mapping": (
        "coordinate_convention",
        "roi_inclusion_policy",
        "invalid_pixel_policy",
        "promotion_rule",
    ),
    "nmr.solid_c": (
        "assignment_source",
        "ambiguity_label_policy",
        "xc_promotion_conditions",
    ),
    "joint": (
        "conflict_precedence",
        "minimum_evidence",
        "unresolved_conflict_policy",
    ),
    "release": ("release_decision", "conditions_or_followups"),
    "saxs.1d": (
        "sequence_axis_policy",
        "frame_identity_policy",
        "missing_repeat_policy",
        "metric_claim_scope",
        "promotion_rule",
    ),
    "saxs.2d": (
        "geometry_reference",
        "beam_center_policy",
        "mask_policy",
        "saturation_policy",
        "orientation_applicability",
        "promotion_rule",
    ),
}


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return tuple(_freeze(item) for item in sorted(value, key=repr))
    return value


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("scientific review record must be JSON-safe")
        return value
    if isinstance(value, Real):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("scientific review record must be JSON-safe")
        return number
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return _json_safe(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_safe(item) for item in value]
    raise ValueError("scientific review record must be JSON-safe")


def _is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (Mapping, Sequence)) and not isinstance(value, (str, bytes, bytearray)):
        return bool(value)
    return True


def required_decision_keys(scope: str) -> tuple[str, ...]:
    """Return the immutable decision schema for one supported review scope."""

    return tuple(_REQUIRED_DECISION_KEYS.get(str(scope or "").strip().lower(), ()))


def review_scope_for_context(technique: str, submodule: str) -> str | None:
    """Resolve only the non-SAXS Workbench review scopes."""

    technique_key = str(technique or "").strip().lower()
    submodule_key = str(submodule or "").strip().lower()
    if technique_key == "joint":
        return "joint"
    if technique_key == "ir" and submodule_key in {"mapping", "ir.mapping"}:
        return "ir.mapping"
    if technique_key == "nmr" and submodule_key in {"solid_c", "nmr.solid_c"}:
        return "nmr.solid_c"
    return None


@dataclass(frozen=True)
class ScientificReviewRecord:
    """One reviewer-owned, scope-specific scientific decision record."""

    record_id: str
    scope: str
    reviewer: str = ""
    reviewed_at: str = ""
    policy_version: str = ""
    source_refs: tuple[str, ...] = ()
    decisions: Mapping[str, Any] = field(default_factory=dict)
    status: str = "pending"
    conditions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_refs", tuple(str(item).strip() for item in self.source_refs))
        object.__setattr__(self, "conditions", tuple(str(item).strip() for item in self.conditions))
        object.__setattr__(self, "decisions", _freeze(self.decisions))

    @classmethod
    def pending(
        cls,
        *,
        record_id: str,
        scope: str,
        source_refs: tuple[str, ...] = (),
    ) -> ScientificReviewRecord:
        return cls(record_id=record_id, scope=scope, source_refs=source_refs)

    def to_dict(self) -> dict[str, Any]:
        validate_review_record(self)
        return _json_safe(
            {
                "record_id": self.record_id,
                "scope": self.scope,
                "reviewer": self.reviewer,
                "reviewed_at": self.reviewed_at,
                "policy_version": self.policy_version,
                "source_refs": self.source_refs,
                "decisions": self.decisions,
                "status": self.status,
                "conditions": self.conditions,
            }
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)


@dataclass(frozen=True)
class ReviewPromotionDecision:
    """One immutable result of checking whether a record permits promotion."""

    allowed: bool
    reason: str
    record_id: str = ""
    scope: str = ""


def validate_review_record(record: ScientificReviewRecord) -> ScientificReviewRecord:
    """Validate and return one immutable review record."""

    if not isinstance(record, ScientificReviewRecord):
        raise TypeError("scientific review record must be a ScientificReviewRecord")
    if not str(record.record_id).strip():
        raise ValueError("review record_id must be non-empty")
    if record.scope not in REVIEW_SCOPES:
        raise ValueError(f"unsupported review scope: {record.scope}")
    if record.status not in REVIEW_STATUSES:
        raise ValueError(f"unsupported review status: {record.status}")
    if not isinstance(record.decisions, Mapping):
        raise ValueError("review decisions must be a mapping")
    if any(not ref for ref in record.source_refs):
        raise ValueError("review source_refs must be non-empty strings")
    if len(set(record.source_refs)) != len(record.source_refs):
        raise ValueError("review source_refs must be unique")

    if record.status == "pending":
        return record

    for field_name, value in (
        ("reviewer", record.reviewer),
        ("reviewed_at", record.reviewed_at),
        ("policy_version", record.policy_version),
    ):
        if not str(value).strip():
            raise ValueError(f"non-pending review requires {field_name}")
    if not record.source_refs:
        raise ValueError("non-pending review requires source_refs")

    required = _REQUIRED_DECISION_KEYS[record.scope]
    missing = [key for key in required if not _is_present(record.decisions.get(key))]
    if missing:
        raise ValueError(f"missing required decisions: {', '.join(missing)}")
    return record


def promotion_decision(
    record: ScientificReviewRecord | None,
    *,
    expected_scope: str,
    source_ref: str = "",
) -> ReviewPromotionDecision:
    """Return the immutable, fail-closed promotion decision for one source."""

    if expected_scope not in REVIEW_SCOPES:
        raise ValueError(f"unsupported expected review scope: {expected_scope}")
    if record is None:
        return ReviewPromotionDecision(False, "review_missing", scope=expected_scope)
    try:
        validate_review_record(record)
        record.to_dict()
    except (TypeError, ValueError):
        return ReviewPromotionDecision(False, "review_invalid", record.record_id, expected_scope)
    if record.scope != expected_scope:
        return ReviewPromotionDecision(False, "scope_mismatch", record.record_id, record.scope)
    normalized_source = str(source_ref).strip()
    if normalized_source and normalized_source not in record.source_refs:
        return ReviewPromotionDecision(False, "source_mismatch", record.record_id, record.scope)
    if record.status == "accepted":
        return ReviewPromotionDecision(True, "review_accepted", record.record_id, record.scope)
    return ReviewPromotionDecision(False, f"review_{record.status}", record.record_id, record.scope)


def review_record_from_payload(value: Any) -> ScientificReviewRecord | None:
    """Restore one serialized review record without weakening validation.

    A missing payload is represented by ``None`` so callers can use the
    shared fail-closed ``promotion_decision`` contract.  Structurally present
    but incomplete payloads are retained as invalid records, allowing the
    decision reason to remain ``review_invalid``.
    """

    if isinstance(value, ScientificReviewRecord):
        return value
    if not isinstance(value, Mapping):
        return None

    source_refs = value.get("source_refs", ())
    if isinstance(source_refs, str):
        source_refs = (source_refs,)
    conditions = value.get("conditions", ())
    if isinstance(conditions, str):
        conditions = (conditions,)
    decisions = value.get("decisions", {})
    try:
        return ScientificReviewRecord(
            record_id=str(value.get("record_id", "")),
            scope=str(value.get("scope", "")),
            reviewer=str(value.get("reviewer", "")),
            reviewed_at=str(value.get("reviewed_at", "")),
            policy_version=str(value.get("policy_version", "")),
            source_refs=tuple(str(item) for item in source_refs),
            decisions=decisions,
            status=str(value.get("status", "pending")),
            conditions=tuple(str(item) for item in conditions),
        )
    except (TypeError, ValueError):
        return None


def review_decision_snapshot(
    record: ScientificReviewRecord | None,
    *,
    expected_scope: str,
    source_ref: str = "",
) -> dict[str, Any]:
    """Serialize one promotion decision for evidence and figure recipes."""

    decision = promotion_decision(
        record,
        expected_scope=expected_scope,
        source_ref=source_ref,
    )
    policy_version = ""
    if record is not None and decision.reason != "review_invalid":
        policy_version = str(record.policy_version or "").strip()
    return {
        "allowed": bool(decision.allowed),
        "reason": decision.reason,
        "record_id": decision.record_id,
        "scope": decision.scope or expected_scope,
        "policy_version": policy_version,
        "source_ref": str(source_ref).strip(),
    }


__all__ = [
    "REVIEW_SCOPES",
    "REVIEW_STATUSES",
    "ReviewPromotionDecision",
    "ScientificReviewRecord",
    "promotion_decision",
    "required_decision_keys",
    "review_decision_snapshot",
    "review_record_from_payload",
    "review_scope_for_context",
    "validate_review_record",
]
