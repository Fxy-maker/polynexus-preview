from polynexus.gui.scientific_review_presentation import (
    ScientificReviewDisplay,
    scientific_review_display,
)


def test_accepted_nested_review_snapshot_preserves_audit_fields():
    display = scientific_review_display(
        {
            "results_summary": {
                "result": {
                    "analysis_evidence": {
                        "scientific_review": {
                            "allowed": True,
                            "reason": "review_accepted",
                            "record_id": "review-ir-map-1",
                            "scope": "ir.mapping",
                            "source_ref": "map-a.json",
                            "policy_version": "ir-map-v1",
                        }
                    }
                }
            }
        },
        technique="ir",
        submodule="ir.mapping",
        language="en",
    )

    assert isinstance(display, ScientificReviewDisplay)
    assert display.status == "accepted"
    assert display.allowed is True
    assert display.record_id == "review-ir-map-1"
    assert display.scope == "ir.mapping"
    assert display.source_ref == "map-a.json"
    assert display.policy_version == "ir-map-v1"
    assert "policy=ir-map-v1" in display.text
    assert "review_accepted" in display.text


def test_missing_review_is_required_only_for_review_gated_modes():
    gated = scientific_review_display({}, technique="nmr", submodule="nmr.solid_c")
    ordinary = scientific_review_display({}, technique="dsc", submodule="dsc.standard")

    assert gated.status == "required"
    assert gated.allowed is False
    assert gated.reason == "review_missing"
    assert ordinary.status == "not_applicable"
    assert ordinary.allowed is False


def test_source_mismatch_is_visible_and_never_accepted():
    display = scientific_review_display(
        {
            "scientific_review": {
                "allowed": False,
                "reason": "source_mismatch",
                "record_id": "review-joint-1",
                "scope": "joint",
                "source_ref": "batch-a",
            }
        },
        technique="joint",
        submodule="joint",
    )

    assert display.status == "blocked"
    assert display.allowed is False
    assert display.reason == "source_mismatch"
    assert "source_mismatch" in display.text


def test_malformed_review_payload_fails_closed():
    display = scientific_review_display(
        {"scientific_review": {"allowed": True, "reason": "review_accepted"}},
        technique="ir",
        submodule="ir.mapping",
    )

    assert display.status == "invalid"
    assert display.allowed is False
    assert display.reason == "review_invalid"
