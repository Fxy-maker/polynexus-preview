from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from polynexus.core import get_engine
from polynexus.core.saxs_engine.saxs_quality_contracts import (
    build_saxs_scientific_acceptance_audit,
)


def test_diagnostic_existing_evidence_is_not_publication_acceptance() -> None:
    parameters = {
        "paper_figure_candidate": False,
        "paper_conclusion_candidate": False,
        "paper_conclusion_ready": False,
        "strain_reliability_status": "diagnostic_only",
        "strain_reliability_reason": "low_q_void_dominant|phase_ambiguous",
        "raw_detector_quality_report": {
            "level": "Unusable",
            "source_kinds": ["raw_detector"],
            "reason_codes": ["nonpositive_pixels"],
        },
        "_batch_data": [
            {
                "raw_detector_quality_report": {
                    "geometry_provenance": {"validity": "not_assessed"},
                    "mask_provenance": {"validity": "not_assessed"},
                },
            },
        ],
    }
    before = copy.deepcopy(parameters)

    audit = build_saxs_scientific_acceptance_audit(True, parameters)

    assert audit["status"] == "diagnostic_only"
    assert audit["automated_validation_passed"] is True
    assert audit["publication_decision_changed"] is False
    assert "existing_publication_gate_not_ready" in audit["reason_codes"]
    assert "raw_geometry_validity_not_assessed" in audit["reason_codes"]
    assert parameters == before
    json.dumps(audit, allow_nan=False)

def test_missing_acceptance_evidence_is_not_assessed() -> None:
    audit = build_saxs_scientific_acceptance_audit(None, {})

    assert audit["status"] == "not_assessed"
    assert audit["reason_codes"] == ["acceptance_evidence_missing"]
    assert audit["existing_publication_gate"] == {
        "paper_figure_candidate": None,
        "paper_conclusion_candidate": None,
        "paper_conclusion_ready": None,
    }


def test_existing_unblocked_evidence_still_requires_human_review() -> None:
    parameters = {
        "paper_figure_candidate": True,
        "paper_conclusion_candidate": True,
        "paper_conclusion_ready": True,
        "strain_reliability_status": "usable",
        "raw_detector_quality_report": {"level": "Trend"},
        "detector_quality_report": {"level": "Trend"},
        "orientation_evidence": {"level": "Trend"},
    }

    audit = build_saxs_scientific_acceptance_audit(True, parameters)

    assert audit["status"] == "review_required"
    assert "human_scientific_review_required" in audit["reason_codes"]
    assert audit["publication_decision_changed"] is False


def test_real_pad8_strain_exposes_diagnostic_acceptance_boundary(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    source = project_root / "\u6d4b\u8bd5\u6570\u636e" / "saxs" / "PAD8\u539f\u4f4d\u62c9\u4f38"
    if not source.exists():
        pytest.skip(f"real PAD8 fixture unavailable: {source}")

    engine = get_engine(
        "saxs",
        config={"fig_format": "png"},
        submodule_id="saxs.strain",
    )
    result = engine.run_pipeline(str(source), str(tmp_path / "output"))

    assert result.validation_passed is True
    audit = result.parameters["scientific_acceptance_audit"]
    assert audit["status"] == "diagnostic_only"
    assert audit["automated_validation_passed"] is True
    assert audit["existing_publication_gate"]["paper_conclusion_ready"] is False
    assert audit["publication_decision_changed"] is False
    json.dumps(audit, allow_nan=False)
