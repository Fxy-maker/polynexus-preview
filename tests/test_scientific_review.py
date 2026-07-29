from __future__ import annotations

from dataclasses import replace
import json

import pytest

from polynexus.core.scientific_review import (
    ScientificReviewRecord,
    promotion_decision,
    review_decision_snapshot,
    review_record_from_payload,
    validate_review_record,
)


def _accepted_ir_record() -> ScientificReviewRecord:
    return ScientificReviewRecord(
        record_id="review-ir-1",
        scope="ir.mapping",
        reviewer="reviewer-a",
        reviewed_at="2026-07-29",
        policy_version="ir-map-v1",
        source_refs=("map-a.json",),
        decisions={
            "coordinate_convention": "row/column supplied by vendor",
            "roi_inclusion_policy": "explicit mask",
            "invalid_pixel_policy": "masked",
            "promotion_rule": "reviewed source",
        },
        status="accepted",
    )


def test_pending_record_is_json_safe_but_not_promotable() -> None:
    record = ScientificReviewRecord.pending(
        record_id="review-ir-1",
        scope="ir.mapping",
        source_refs=("map-a.json",),
    )

    assert json.loads(record.to_json())["status"] == "pending"
    decision = promotion_decision(
        record,
        expected_scope="ir.mapping",
        source_ref="map-a.json",
    )
    assert decision.allowed is False
    assert decision.reason == "review_pending"


def test_accepted_record_requires_scope_fields_reviewer_and_source() -> None:
    record = _accepted_ir_record()

    assert validate_review_record(record) == record
    decision = promotion_decision(
        record,
        expected_scope="ir.mapping",
        source_ref="map-a.json",
    )
    assert decision.allowed is True
    assert decision.reason == "review_accepted"


def test_promotion_is_denied_for_scope_source_or_status_mismatch() -> None:
    record = _accepted_ir_record()

    assert promotion_decision(record, expected_scope="joint", source_ref="map-a.json").reason == "scope_mismatch"
    assert promotion_decision(record, expected_scope="ir.mapping", source_ref="other.json").reason == "source_mismatch"
    conditional = replace(record, status="conditional")
    assert promotion_decision(conditional, expected_scope="ir.mapping", source_ref="map-a.json").reason == "review_conditional"


def test_non_finite_decision_values_fail_json_validation() -> None:
    record = replace(
        _accepted_ir_record(),
        decisions={
            **_accepted_ir_record().decisions,
            "coordinate_convention": float("nan"),
        },
    )

    with pytest.raises(ValueError, match="JSON-safe"):
        record.to_json()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("scope", "ir.unknown", "unsupported review scope"),
        ("status", "promoted", "unsupported review status"),
    ),
)
def test_record_rejects_unknown_scope_or_status(field: str, value: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        validate_review_record(replace(_accepted_ir_record(), **{field: value}))


def test_non_pending_record_rejects_missing_required_decision_fields() -> None:
    incomplete = replace(_accepted_ir_record(), decisions={"coordinate_convention": "vendor rows"})

    with pytest.raises(ValueError, match="missing required decisions"):
        validate_review_record(incomplete)


def test_review_payload_restores_and_serializes_a_decision_snapshot() -> None:
    restored = review_record_from_payload(_accepted_ir_record().to_dict())

    assert restored == _accepted_ir_record()
    assert review_decision_snapshot(
        restored,
        expected_scope="ir.mapping",
        source_ref="map-a.json",
    ) == {
        "allowed": True,
        "reason": "review_accepted",
        "record_id": "review-ir-1",
        "scope": "ir.mapping",
        "policy_version": "ir-map-v1",
        "source_ref": "map-a.json",
    }


def test_invalid_present_review_payload_fails_closed_as_invalid() -> None:
    restored = review_record_from_payload({"record_id": "broken", "scope": "ir.mapping", "status": "accepted"})

    assert review_decision_snapshot(
        restored,
        expected_scope="ir.mapping",
        source_ref="map-a.json",
    )["reason"] == "review_invalid"


def test_non_finite_review_payload_cannot_promote() -> None:
    invalid = replace(
        _accepted_ir_record(),
        decisions={
            **_accepted_ir_record().decisions,
            "promotion_rule": float("nan"),
        },
    )

    assert promotion_decision(
        invalid,
        expected_scope="ir.mapping",
        source_ref="map-a.json",
    ).reason == "review_invalid"
