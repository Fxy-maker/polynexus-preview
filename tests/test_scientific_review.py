from __future__ import annotations

from dataclasses import replace
import json

import pytest

from polynexus.core.scientific_review import (
    REVIEW_SCOPES,
    ScientificReviewRecord,
    promotion_decision,
    required_decision_keys,
    review_decision_snapshot,
    review_record_from_payload,
    review_scope_for_context,
    review_scope_options_for_context,
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


def test_required_decision_keys_are_public_and_immutable() -> None:
    keys = required_decision_keys("ir.mapping")

    assert keys == (
        "coordinate_convention",
        "roi_inclusion_policy",
        "invalid_pixel_policy",
        "promotion_rule",
    )
    assert isinstance(keys, tuple)


@pytest.mark.parametrize(
    ("technique", "submodule", "expected"),
    [
        ("ir", "ir.mapping", "ir.mapping"),
        ("ir", "mapping", "ir.mapping"),
        ("nmr", "nmr.solid_c", "nmr.solid_c"),
        ("joint", "", "joint"),
        ("saxs", "saxs.1d", None),
        ("dsc", "dsc.standard", None),
    ],
)
def test_review_scope_for_context_is_fail_closed(technique, submodule, expected) -> None:
    assert review_scope_for_context(technique, submodule) == expected


@pytest.mark.parametrize(
    ("technique", "submodule", "expected"),
    [
        ("saxs", "saxs.static", ("saxs.1d", "saxs.2d")),
        ("saxs", "saxs.temperature", ("saxs.1d", "saxs.2d")),
        ("ir", "ir.mapping", ("ir.mapping",)),
        ("nmr", "nmr.solid_c", ("nmr.solid_c",)),
        ("joint", "", ("joint",)),
        ("dsc", "dsc.standard", ()),
    ],
)
def test_review_scope_options_are_explicit_and_ordered(technique, submodule, expected) -> None:
    assert review_scope_options_for_context(technique, submodule) == expected


def _accepted_saxs_1d_record() -> ScientificReviewRecord:
    return ScientificReviewRecord(
        record_id="review-saxs-1d-1",
        scope="saxs.1d",
        reviewer="reviewer-saxs",
        reviewed_at="2026-07-29",
        policy_version="saxs-1d-v1",
        source_refs=("saxs-run-1",),
        decisions={
            "sequence_axis_policy": "review supplied temperature axis",
            "frame_identity_policy": "source_index is authoritative",
            "missing_repeat_policy": "retain missing status",
            "metric_claim_scope": ["Rg", "Porod"],
            "promotion_rule": "reviewed source and existing gates",
        },
        status="accepted",
    )


def _accepted_saxs_2d_record() -> ScientificReviewRecord:
    return ScientificReviewRecord(
        record_id="review-saxs-2d-1",
        scope="saxs.2d",
        reviewer="reviewer-saxs",
        reviewed_at="2026-07-29",
        policy_version="saxs-2d-v1",
        source_refs=("pad8-run-1",),
        decisions={
            "geometry_reference": "reviewed calibration record",
            "beam_center_policy": "reviewed detector coordinates",
            "mask_policy": "reviewed beamstop mask",
            "saturation_policy": "saturation status retained",
            "orientation_applicability": "orientation evidence applicable",
            "promotion_rule": "reviewed source and existing gates",
        },
        status="accepted",
    )


def _release_record(*, status: str = "accepted", decision: str = "approve") -> ScientificReviewRecord:
    return ScientificReviewRecord(
        record_id=f"release-{status}-{decision}",
        scope="release",
        reviewer="reviewer-release",
        reviewed_at="2026-07-30",
        policy_version="release-v1",
        source_refs=("ir-run", "nmr-run", "joint-run"),
        decisions={
            "release_decision": decision,
            "conditions_or_followups": "none",
        },
        status=status,
    )


@pytest.mark.parametrize(
    ("status", "decision"),
    (("accepted", "approve"), ("conditional", "conditional"), ("rejected", "reject")),
)
def test_release_record_accepts_matching_status_and_decision(status: str, decision: str) -> None:
    assert validate_review_record(_release_record(status=status, decision=decision)).scope == "release"


def test_release_record_rejects_status_and_decision_mismatch() -> None:
    with pytest.raises(ValueError, match="release status requires decision"):
        validate_review_record(_release_record(status="accepted", decision="conditional"))


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


def test_saxs_review_scopes_are_registered_and_complete_records_promote() -> None:
    assert {"saxs.1d", "saxs.2d"}.issubset(REVIEW_SCOPES)

    saxs_1d = _accepted_saxs_1d_record()
    saxs_2d = _accepted_saxs_2d_record()

    assert validate_review_record(saxs_1d) == saxs_1d
    assert validate_review_record(saxs_2d) == saxs_2d
    assert promotion_decision(
        saxs_1d,
        expected_scope="saxs.1d",
        source_ref="saxs-run-1",
    ).reason == "review_accepted"
    assert promotion_decision(
        saxs_2d,
        expected_scope="saxs.2d",
        source_ref="pad8-run-1",
    ).reason == "review_accepted"


def test_saxs_pending_records_can_omit_reviewer_decisions() -> None:
    for scope, source_ref in (("saxs.1d", "saxs-run-1"), ("saxs.2d", "pad8-run-1")):
        record = ScientificReviewRecord.pending(
            record_id=f"pending-{scope}",
            scope=scope,
            source_refs=(source_ref,),
        )

        assert validate_review_record(record) == record
        assert promotion_decision(
            record,
            expected_scope=scope,
            source_ref=source_ref,
        ).reason == "review_pending"


@pytest.mark.parametrize(
    ("scope", "record", "missing_key"),
    (
        ("saxs.1d", _accepted_saxs_1d_record(), "frame_identity_policy"),
        ("saxs.2d", _accepted_saxs_2d_record(), "mask_policy"),
    ),
)
def test_saxs_non_pending_records_require_every_scope_decision(
    scope: str,
    record: ScientificReviewRecord,
    missing_key: str,
) -> None:
    del scope
    incomplete = replace(record, decisions={key: value for key, value in record.decisions.items() if key != missing_key})

    with pytest.raises(ValueError, match=f"missing required decisions: {missing_key}"):
        validate_review_record(incomplete)


def test_saxs_review_scopes_cannot_promote_each_other() -> None:
    saxs_1d = _accepted_saxs_1d_record()
    saxs_2d = _accepted_saxs_2d_record()

    assert promotion_decision(
        saxs_1d,
        expected_scope="saxs.2d",
        source_ref="saxs-run-1",
    ).reason == "scope_mismatch"
    assert promotion_decision(
        saxs_2d,
        expected_scope="saxs.1d",
        source_ref="pad8-run-1",
    ).reason == "scope_mismatch"
