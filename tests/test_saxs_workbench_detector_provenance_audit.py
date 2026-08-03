from __future__ import annotations

from copy import deepcopy

from polynexus.gui.saxs_results_table_service import build_saxs_results_presentation


def _presentation(audit: object):
    return build_saxs_results_presentation(
        {"scientific_acceptance_audit": {"detector_provenance_audit": audit}},
        submodule="static",
        language="en",
    )


def test_review_required_detector_provenance_is_visible_as_risk() -> None:
    presentation = _presentation(
        {
            "raw_detector_quality_report": [
                {
                    "status": "review_required",
                    "level": "Diagnostic",
                    "geometry": {"validity": "not_assessed"},
                    "mask": {"validity": "invalid"},
                    "reason_codes": [
                        "geometry_validity_not_assessed",
                        "mask_validity_invalid",
                    ],
                }
            ]
        }
    )

    assert "Detector provenance audit" in presentation.risk_text
    assert "status=review_required" in presentation.risk_text
    assert "level=Diagnostic" in presentation.risk_text
    assert "geometry=not_assessed" in presentation.risk_text
    assert "mask=invalid" in presentation.risk_text
    assert "geometry_validity_not_assessed" in presentation.risk_text
    assert "calibration" in presentation.next_text.lower()
    assert "physical acceptance" in presentation.next_text.lower()


def test_structurally_consistent_detector_provenance_is_advisory_only() -> None:
    presentation = _presentation(
        {
            "raw_detector_quality_report": [
                {
                    "status": "structurally_consistent",
                    "level": "Trend",
                    "geometry": {"validity": "validated"},
                    "mask": {"validity": "validated"},
                    "reason_codes": [],
                }
            ]
        }
    )

    assert "Detector provenance audit" not in presentation.risk_text
    assert "Detector provenance audit" in presentation.next_text
    assert "structural evidence" in presentation.next_text


def test_unusable_detector_provenance_is_visible_as_risk() -> None:
    presentation = _presentation(
        {
            "raw_detector_quality_report": [
                {
                    "status": "unusable",
                    "level": "Unusable",
                    "geometry": {"validity": "invalid"},
                    "mask": {"validity": "invalid"},
                    "reason_codes": ["detector_payload_invalid"],
                }
            ]
        }
    )

    assert "Detector provenance audit" in presentation.risk_text
    assert "status=unusable" in presentation.risk_text
    assert "detector_payload_invalid" in presentation.risk_text


def test_malformed_detector_provenance_is_ignored_without_mutating_input() -> None:
    params = {
        "metric_evidence": {"porod": {"level": "Trend", "frame_count": 1}},
        "scientific_acceptance_audit": {
            "detector_provenance_audit": {
                "raw_detector_quality_report": [
                    "bad",
                    {"status": "review_required", "geometry": []},
                    {"status": "", "mask": {"validity": "invalid"}},
                ]
            }
        },
    }
    before = deepcopy(params)

    presentation = build_saxs_results_presentation(params, submodule="static", language="en")

    assert "Detector provenance audit" not in presentation.risk_text
    assert "Detector provenance audit" not in presentation.next_text
    assert "Porod" not in presentation.risk_text
    assert params == before


def test_detector_provenance_reasons_are_bounded_and_non_string_values_ignored() -> None:
    presentation = _presentation(
        {
            "raw_detector_quality_report": [
                {
                    "status": "review_required",
                    "level": "Diagnostic",
                    "geometry": {"validity": "validated"},
                    "mask": {"validity": "validated"},
                    "reason_codes": [
                        "reason_1",
                        "reason_2",
                        "reason_3",
                        "reason_4",
                        "reason_5",
                        "reason_6",
                        99,
                    ],
                }
            ]
        }
    )

    assert "reason_1" in presentation.risk_text
    assert "reason_5" in presentation.risk_text
    assert "reason_6" not in presentation.risk_text
    assert "99" not in presentation.risk_text


def test_identical_detector_audits_are_rendered_once_per_presentation_field() -> None:
    audit = {
        "raw_detector_quality_report": [
            {
                "status": "review_required",
                "level": "Diagnostic",
                "geometry": {"validity": "metadata_complete"},
                "mask": {"validity": "configured_shape_match"},
                "reason_codes": ["detector_saturation_unknown"],
            }
        ] * 4,
    }

    presentation = _presentation(audit)

    assert presentation.risk_text.count("Detector provenance audit") == 1
    assert presentation.next_text.count("Detector provenance audit") == 1
