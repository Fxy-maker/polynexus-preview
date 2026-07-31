from __future__ import annotations

import copy
import json
from types import SimpleNamespace

from polynexus.core.saxs_engine.saxs_ai_rescue import (
    build_saxs_ai_summary_context,
    sanitize_saxs_ai_summary_context,
)


def _audit() -> dict[str, object]:
    return {
        "status": "diagnostic_only",
        "automated_validation_passed": False,
        "existing_publication_gate": {"paper_figure_candidate": None},
        "evidence_levels": {"metric:guinier": ["Diagnostic"]},
        "provenance_validity": {},
        "physical_gate_evidence": {"metric:guinier": [{"qrg_gate": True}]},
        "method_gate_status": {"metric:guinier": [None]},
        "reliability": {"status": "diagnostic_only", "reason": "review"},
        "reason_codes": ["method_gate_not_assessed"],
        "audit_scope": "existing_gates_only",
        "publication_decision_changed": False,
    }


def _frame() -> SimpleNamespace:
    return SimpleNamespace(
        source_index=2,
        temperature_C=170.0,
        data_quality_report={"level": "Trend"},
        metric_evidence={"guinier": {"level": "Trend"}},
    )


def test_direct_existing_acceptance_audit_is_projected_detached_and_strict_json() -> None:
    audit = _audit()
    result = SimpleNamespace(
        parameters={"scientific_acceptance_audit": audit},
        data_quality_report={"level": "Trend"},
    )

    context = build_saxs_ai_summary_context(result, mode="static")

    assert context["scientific_acceptance_audit"] == audit
    audit["status"] = "review_required"
    assert context["scientific_acceptance_audit"]["status"] == "diagnostic_only"
    json.dumps(context, allow_nan=False)


def test_engine_wrapper_projects_existing_temperature_audit_with_series_evidence() -> None:
    audit = _audit()
    engine = SimpleNamespace(
        result=SimpleNamespace(parameters={"scientific_acceptance_audit": audit}),
        _temperature_result=SimpleNamespace(
            temp_points=[_frame()],
            guinier_sequence_evidence={"level": "Trend", "valid_frame_count": 1},
        ),
        _strain_result=None,
    )

    context = build_saxs_ai_summary_context(engine, mode="temperature")

    assert context["scientific_acceptance_audit"]["status"] == "diagnostic_only"
    assert context["series"]["guinier_sequence_evidence"]["level"] == "Trend"
    assert context["frames"][0]["source_index"] == 2


def test_prompt_sanitizer_keeps_audit_whitelist_and_excludes_raw_fields() -> None:
    audit = _audit()
    audit["raw_q"] = [0.01]
    audit["source_path"] = "secret/raw.edf"
    audit["unknown_prompt_instruction"] = "apply this candidate"
    payload = {
        "technique": "SAXS",
        "mode": "static",
        "scientific_acceptance_audit": audit,
        "frames": [],
    }
    before = copy.deepcopy(payload)

    context = sanitize_saxs_ai_summary_context(payload)

    assert context["scientific_acceptance_audit"] == _audit()
    serialized = json.dumps(context, allow_nan=False)
    assert "raw_q" not in serialized
    assert "source_path" not in serialized
    assert "unknown_prompt_instruction" not in serialized
    assert payload == before
