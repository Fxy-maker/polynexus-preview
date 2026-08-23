from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from polynexus.core.project_workflow.manuscript_plan import PaperBrief, build_manuscript_plan
from polynexus.core.project_workflow.models import canonical_json


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _package(tmp_path: Path) -> Path:
    package = tmp_path / "package"
    package.mkdir()
    (package / "figures").mkdir()
    (package / "figures" / "dsc.svg").write_text("<svg/>", encoding="utf-8")
    manifest = {
        "package_id": "pa6",
        "version": 1,
        "status": "review_required",
        "run_ids": ["run-dsc"],
        "limitations": ["background_review"],
        "citation_metrics": "citation-metrics.json",
        "ars_writing_input": "ars-writing-input.json",
    }
    manifest["package_hash"] = hashlib.sha256(canonical_json(manifest).encode("utf-8")).hexdigest()
    _write_json(package / "manifest.json", manifest)
    _write_json(package / "techniques.json", {"techniques": {
        "dsc": {"run_ids": ["run-dsc"], "statuses": ["review_required"], "evidence_count": 1},
    }})
    _write_json(package / "writing-evidence.json", {"techniques": {"dsc": {
        "run_ids": ["run-dsc"],
        "statuses": ["review_required"],
        "evidence": [{
            "evidence_id": "run-dsc:step",
            "status": "review_required",
            "source_runs": ["run-dsc"],
            "raw_sources": ["raw-dsc"],
            "figures": ["figures/dsc.svg"],
            "tables": [],
            "citation_metric_ids": ["metric-dsc", "metric-diagnostic"],
            "supported_interpretations": ["observed"],
            "disallowed_conclusions": ["human_review_required"],
            "limitations": [],
        }],
    }}})
    _write_json(package / "citation-metrics.json", {"version": 1, "records": [{
        "metric_id": "metric-dsc",
        "technique": "dsc",
        "metric_key": "t_half_min",
        "value": 1.2,
        "unit": "min",
        "method": "dsc.isothermal_avrami_fit",
        "source_locator": "parameters.segment_01.t_half_min",
        "evidence_id": "run-dsc:step",
        "run_id": "run-dsc",
        "raw_source_hashes": ["raw-dsc"],
        "status": "review_required",
        "writing_eligibility": "results_candidate",
        "reason_codes": [],
        "figures": ["figures/dsc.svg"],
        "tables": [],
    }, {
        "metric_id": "metric-diagnostic",
        "technique": "dsc",
        "metric_key": "diagnostic",
        "value": 2.0,
        "unit": "index",
        "method": "provider",
        "source_locator": "parameters.diagnostic",
        "evidence_id": "run-dsc:step",
        "run_id": "run-dsc",
        "raw_source_hashes": ["raw-dsc"],
        "status": "review_required",
        "writing_eligibility": "diagnostic_only",
        "reason_codes": ["review"],
        "figures": [],
        "tables": [],
    }]})
    _write_json(package / "ars-writing-input.json", {
        "version": 1,
        "techniques": {"dsc": {"evidence": [{
            "evidence_id": "run-dsc:step",
            "results_metric_ids": ["metric-dsc"],
            "discussion_metric_ids": ["metric-diagnostic"],
        }]}},
        "allowed_results": ["metric-dsc"],
        "discussion_only": ["metric-diagnostic"],
        "human_review": [{
            "evidence_id": "run-dsc:step",
            "action": "human_scientific_review",
            "reason": "human_review_required",
        }],
    })
    _write_json(package / "limitations.json", {"limitations": ["background_review"]})
    _write_json(package / "figure-index.json", {"version": 1, "figures": [{
        "id": "dsc",
        "role": "supporting",
        "technique": "DSC",
        "group": None,
        "writing_eligibility": "Results",
        "svg": "figures/dsc.svg",
        "document": None,
        "data": None,
        "metadata": "figures/dsc.metadata.json",
    }]})
    return package


def test_build_manuscript_plan_pins_package_and_inherits_boundaries(tmp_path: Path) -> None:
    plan = build_manuscript_plan(
        _package(tmp_path),
        PaperBrief.from_dict({
            "version": 1,
            "research_question": "Compare PA6 crystallization kinetics.",
            "comparison_scope": {
                "selected_techniques": ["dsc"],
                "selected_evidence_ids": ["run-dsc:step"],
                "selected_metric_ids": ["metric-dsc", "metric-diagnostic"],
            },
            "figure_budget": {"main_max": 1, "supporting_max": 1},
            "figure_intent": {"dsc": "main"},
            "technique_roles": {"dsc": "observed_result"},
        }),
    )

    assert plan.status == "draft"
    assert plan.package["package_id"] == "pa6"
    assert plan.selection["results_metric_ids"] == ("metric-dsc",)
    assert plan.selection["discussion_metric_ids"] == ("metric-diagnostic",)
    assert plan.selection["main_figure_ids"] == ("dsc",)
    assert plan.writing_boundaries["limitations"] == ("background_review",)
    assert plan.writing_boundaries["human_review"][0]["action"] == "human_scientific_review"


def _brief(**updates: object) -> PaperBrief:
    payload: dict[str, object] = {
        "version": 1,
        "research_question": "Compare PA6 crystallization kinetics.",
        "comparison_scope": {
            "selected_techniques": ["dsc"],
            "selected_evidence_ids": ["run-dsc:step"],
            "selected_metric_ids": ["metric-dsc", "metric-diagnostic"],
        },
        "figure_budget": {"main_max": 1, "supporting_max": 1},
        "figure_intent": {"dsc": "main"},
        "technique_roles": {"dsc": "observed_result"},
    }
    payload.update(updates)
    return PaperBrief.from_dict(payload)


def test_builder_rejects_a_tampered_package_hash(tmp_path: Path) -> None:
    package = _package(tmp_path)
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    manifest["package_hash"] = "tampered"
    _write_json(package / "manifest.json", manifest)

    with pytest.raises(ValueError, match="package hash"):
        build_manuscript_plan(package, _brief())


def test_builder_rejects_unknown_metric_references(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="metric"):
        build_manuscript_plan(
            _package(tmp_path),
            _brief(comparison_scope={"selected_metric_ids": ["missing"]}),
        )


def test_builder_rejects_unknown_figure_and_figure_budget_overflow(tmp_path: Path) -> None:
    package = _package(tmp_path)
    with pytest.raises(ValueError, match="figure"):
        build_manuscript_plan(package, _brief(figure_intent={"missing": "main"}))
    with pytest.raises(ValueError, match="budget"):
        build_manuscript_plan(package, _brief(figure_budget={"main_max": 0, "supporting_max": 1}))
