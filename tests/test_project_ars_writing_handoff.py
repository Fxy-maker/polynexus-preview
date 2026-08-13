from __future__ import annotations

import pytest

from polynexus.core.project_workflow.ars_handoff import build_ars_writing_input, validate_ars_writing_input


def _inputs():
    metrics = {"records": [
        {"metric_id": "metric-results", "evidence_id": "run:dsc", "writing_eligibility": "results_candidate"},
        {"metric_id": "metric-diagnostic", "evidence_id": "run:dsc", "writing_eligibility": "diagnostic_only"},
    ]}
    writing = {"techniques": {"dsc": {"run_ids": ["run"], "statuses": ["review_required"], "evidence": [{
        "evidence_id": "run:dsc", "status": "review_required", "source_runs": ["run"], "raw_sources": ["raw"],
        "figures": ["figures/dsc.svg"], "tables": [], "citation_metric_ids": ["metric-results", "metric-diagnostic"],
        "supported_interpretations": ["observed"], "disallowed_conclusions": ["human_review_required"], "limitations": [],
    }]}}}
    return {"package_id": "demo", "version": 1, "status": "review_required", "run_ids": ["run"]}, writing, metrics, {"limitations": ["provider_limit"]}


def test_handoff_separates_results_and_discussion_metrics() -> None:
    manifest, writing, metrics, limitations = _inputs()
    payload = build_ars_writing_input(package_manifest=manifest, writing_evidence=writing, citation_metrics=metrics, limitations=limitations)
    item = payload["techniques"]["dsc"]["evidence"][0]
    assert item["results_metric_ids"] == ["metric-results"]
    assert item["discussion_metric_ids"] == ["metric-diagnostic"]
    assert payload["human_review"]
    validate_ars_writing_input(payload, citation_metrics=metrics)


def test_handoff_rejects_diagnostic_metric_promoted_to_results() -> None:
    manifest, writing, metrics, limitations = _inputs()
    payload = build_ars_writing_input(package_manifest=manifest, writing_evidence=writing, citation_metrics=metrics, limitations=limitations)
    payload["allowed_results"].append("metric-diagnostic")
    with pytest.raises(ValueError, match="eligibility"):
        validate_ars_writing_input(payload, citation_metrics=metrics)
