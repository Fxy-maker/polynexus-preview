from __future__ import annotations

import json

from polynexus.core.saxs_engine.saxs_quality_contracts import (
    build_saxs_scientific_acceptance_audit,
)


_GEOMETRY_FIELDS = {
    "wavelength_m": "header",
    "pixel_size_m": "header",
    "sdd_m": "header",
    "beam_center_x": "header",
    "beam_center_y": "header",
}


def _raw_report(*, validity: str, mask_shape: list[int] | None = None) -> dict:
    return {
        "source_kind": "raw_detector",
        "shape": [2, 2],
        "pixel_count": 4,
        "finite_pixel_count": 4,
        "nonfinite_pixel_count": 0,
        "nonpositive_pixel_count": 0,
        "masked_pixel_count": 1,
        "saturated_pixel_count": 0,
        "valid_pixel_count": 3,
        "geometry_provenance": {
            "source": "header",
            "field_sources": dict(_GEOMETRY_FIELDS),
            "validity": validity,
        },
        "mask_provenance": {
            "source": "saxs_config.dummy_value",
            "configured": True,
            "shape": list(mask_shape or [2, 2]),
            "validity": validity,
        },
    }


def test_validated_raw_detector_provenance_is_structurally_consistent() -> None:
    report = _raw_report(validity="validated")

    audit = build_saxs_scientific_acceptance_audit(
        True, {"raw_detector_quality_report": report}
    )

    record = audit["detector_provenance_audit"]["raw_detector_quality_report"][0]
    assert record["status"] == "structurally_consistent"
    assert record["level"] == "Trend"
    assert record["geometry"]["missing_field_sources"] == []
    assert record["mask"]["shape_matches_detector"] is True


def test_unassessed_provenance_stays_review_required() -> None:
    audit = build_saxs_scientific_acceptance_audit(
        True,
        {"raw_detector_quality_report": _raw_report(validity="not_assessed")},
    )

    record = audit["detector_provenance_audit"]["raw_detector_quality_report"][0]
    assert record["status"] == "review_required"
    assert record["level"] == "Diagnostic"
    assert "geometry_validity_not_assessed" in record["reason_codes"]


def test_invalid_or_mismatched_provenance_fails_closed() -> None:
    audit = build_saxs_scientific_acceptance_audit(
        True,
        {
            "raw_detector_quality_report": _raw_report(
                validity="invalid", mask_shape=[3, 3]
            )
        },
    )

    record = audit["detector_provenance_audit"]["raw_detector_quality_report"][0]
    assert record["status"] == "unusable"
    assert record["level"] == "Unusable"
    assert "mask_shape_mismatch" in record["reason_codes"]


def test_sector_map_does_not_receive_raw_detector_provenance() -> None:
    audit = build_saxs_scientific_acceptance_audit(
        True,
        {"detector_quality_report": {"source_kind": "sector_map"}},
    )

    assert "detector_provenance_audit" not in audit


def test_structural_audit_is_detached_and_strict_json_safe() -> None:
    report = _raw_report(validity="validated")
    audit = build_saxs_scientific_acceptance_audit(
        True, {"raw_detector_quality_report": report}
    )

    report["geometry_provenance"]["field_sources"]["sdd_m"] = "mutated"

    record = audit["detector_provenance_audit"]["raw_detector_quality_report"][0]
    assert record["geometry"]["field_sources"]["sdd_m"] == "header"
    json.dumps(audit, allow_nan=False)
