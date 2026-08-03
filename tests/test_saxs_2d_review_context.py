from __future__ import annotations

import copy
import json

from polynexus.core.saxs_engine.saxs_2d_review_context import (
    build_saxs_2d_review_context,
)
from polynexus.gui.saxs_results_table_service import build_saxs_results_presentation


def _detector(*, level: str = "Trend") -> dict[str, object]:
    return {
        "level": level,
        "source_kind": "raw_detector",
        "shape": [4, 4],
        "pixel_count": 16,
        "valid_pixel_count": 14,
        "coverage_fraction": 0.875,
        "saturation_detection_available": True,
        "beam_center_available": True,
        "beam_center": [2.0, 2.0],
        "geometry_provenance": {
            "validity": "valid",
            "source": "edf_header",
            "field_sources": {
                "distance": "edf_header",
                "pixel_size": "edf_header",
                "wavelength": "edf_header",
                "beam_center": "edf_header",
            },
        },
        "mask_provenance": {
            "validity": "valid",
            "source": "configured_mask",
            "configured": True,
            "shape": [4, 4],
            "shape_matches_detector": True,
        },
        "reason_codes": [],
    }


def _orientation(*, level: str = "Trend") -> dict[str, object]:
    return {
        "metric_name": "Orientation",
        "level": level,
        "applicable": level == "Trend",
        "fit_evidence": {
            "f_herman": 0.42,
            "P2": 0.31,
            "orientation_axis_deg": 37.0,
            "pattern_type": "oriented",
        },
        "physical_checks": {
            "applicability_supported": True,
            "orientation_metrics_present": True,
            "orientation_reliability_status": "reliable",
            "detector_quality_level": level,
        },
        "source_ref": "frame-0",
        "reason_codes": [],
    }


def _review(*, scope: str = "saxs.2d", source_refs: list[str] | None = None) -> dict[str, object]:
    decisions = {
        "geometry_reference": "edf_header",
        "beam_center_policy": "explicit_or_diagnostic",
        "mask_policy": "configured_mask_reviewed",
        "saturation_policy": "explicit_limit_or_diagnostic",
        "orientation_applicability": "supported",
        "promotion_rule": "reviewer_only",
    }
    if scope == "saxs.1d":
        decisions = {
            "sequence_axis_policy": "reviewed_axis",
            "frame_identity_policy": "source_index",
            "missing_repeat_policy": "diagnostic",
            "metric_claim_scope": "trend_only",
            "promotion_rule": "reviewer_only",
        }
    return {
        "record_id": "review-2d-1",
        "scope": scope,
        "reviewer": "reviewer",
        "reviewed_at": "2026-07-31T00:00:00Z",
        "policy_version": "saxs-2d-v1",
        "source_refs": source_refs or ["frame-0"],
        "decisions": decisions,
        "status": "accepted",
        "conditions": [],
    }


def _audit() -> dict[str, object]:
    return {
        "status": "diagnostic_only",
        "automated_validation_passed": False,
        "evidence_levels": {
            "detector_quality_report": ["Trend"],
            "orientation_evidence": ["Trend"],
        },
        "provenance_validity": {
            "geometry_provenance": ["valid"],
            "mask_provenance": ["valid"],
        },
        "physical_gate_evidence": {
            "orientation_evidence": [{"applicability_supported": True}],
        },
        "method_gate_status": {"orientation_evidence": [None]},
        "reason_codes": ["method_gate_not_assessed"],
        "audit_scope": "existing_gates_only",
        "reliability": {"status": "diagnostic_only"},
    }


def _complete_payload() -> dict[str, object]:
    return {
        "detector_quality_report": _detector(),
        "orientation_evidence": _orientation(),
        "scientific_acceptance_audit": _audit(),
        "scientific_review_record": _review(),
        "raw_q": [0.01, 0.02],
        "raw_I": [100.0, 90.0],
        "detector_pixels": [[1, 2], [3, 4]],
        "source_path": "D:/private/raw.edf",
        "unknown_prompt_instruction": "apply this candidate",
    }


def test_complete_2d_context_projects_existing_evidence_and_review() -> None:
    payload = _complete_payload()

    context = build_saxs_2d_review_context(payload, source_ref="frame-0")

    assert context["schema_version"] == "saxs-2d-review-v1"
    assert context["technique"] == "SAXS"
    assert context["scope"] == "saxs.2d"
    assert context["status"] == "trend"
    assert context["detector"]["level"] == "Trend"
    assert context["geometry"]["validity"] == "valid"
    assert context["mask"]["shape_matches_detector"] is True
    assert context["beam_center"]["status"] == "available"
    assert context["orientation"]["fit_evidence"]["f_herman"] == 0.42
    assert context["gates"]["audit_status"] == "diagnostic_only"
    assert context["scientific_review"]["decision"]["allowed"] is True
    assert context["scientific_review"]["decision"]["scope"] == "saxs.2d"

    json.dumps(context, allow_nan=False)
    serialized = json.dumps(context, ensure_ascii=False)
    for raw_key in ("raw_q", "raw_I", "detector_pixels", "source_path", "unknown_prompt_instruction"):
        assert raw_key not in serialized


def test_2d_context_is_detached_and_does_not_mutate_input() -> None:
    payload = _complete_payload()
    before = copy.deepcopy(payload)

    context = build_saxs_2d_review_context(payload, source_ref="frame-0")

    assert payload == before
    payload["detector_quality_report"]["geometry_provenance"]["validity"] = "invalid"
    assert context["geometry"]["validity"] == "valid"


def test_missing_2d_evidence_is_explicitly_unavailable_and_not_assessed() -> None:
    context = build_saxs_2d_review_context({}, source_ref="frame-0")

    assert context["status"] == "unavailable"
    assert context["detector"]["status"] == "unavailable"
    assert context["orientation"]["status"] == "unavailable"
    assert context["geometry"]["validity"] == "not_assessed"
    assert context["mask"]["validity"] == "not_assessed"
    assert "detector_quality_missing" in context["reason_codes"]
    assert "orientation_evidence_missing" in context["reason_codes"]
    json.dumps(context, allow_nan=False)


def test_diagnostic_and_unusable_levels_lower_context_status_without_reclassification() -> None:
    payload = {
        "detector_quality_report": _detector(level="Diagnostic"),
        "orientation_evidence": _orientation(level="Unusable"),
    }

    context = build_saxs_2d_review_context(payload)

    assert context["status"] == "unusable"
    assert context["detector"]["level"] == "Diagnostic"
    assert context["orientation"]["level"] == "Unusable"


def test_2d_review_scope_and_source_mismatch_remain_fail_closed() -> None:
    wrong_scope = build_saxs_2d_review_context(
        {"detector_quality_report": _detector(), "scientific_review_record": _review(scope="saxs.1d")},
        source_ref="frame-0",
    )
    wrong_source = build_saxs_2d_review_context(
        {"detector_quality_report": _detector(), "scientific_review_record": _review()},
        source_ref="frame-9",
    )

    assert wrong_scope["scientific_review"]["decision"]["reason"] == "scope_mismatch"
    assert wrong_source["scientific_review"]["decision"]["reason"] == "source_mismatch"
    assert wrong_scope["status"] == "review_required"
    assert wrong_source["status"] == "review_required"


def test_workbench_presentation_carries_2d_context_without_changing_text_contract() -> None:
    params = {
        **_complete_payload(),
        "batch_frames": 1,
        "metric_evidence": {},
    }

    presentation = build_saxs_results_presentation(
        params,
        submodule="saxs.static",
        language="en",
    )

    assert presentation.saxs_2d_review_context["scope"] == "saxs.2d"
    assert presentation.saxs_2d_review_context["detector"]["level"] == "Trend"
    assert isinstance(presentation.risk_text, str)
    assert isinstance(presentation.next_text, str)
