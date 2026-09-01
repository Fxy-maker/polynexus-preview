from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from polynexus.suite import handoff
from polynexus.suite.handoff import (
    build_suite_handoff,
    validate_ars_action,
    validate_ars_actions,
)
from polynexus.suite.preflight import preflight_manuscript, submission_preflight
from polynexus.cli import run_suite_service


def test_ars_action_validation_is_typed_and_task_bound() -> None:
    value = validate_ars_action(
        {"kind": "recompute", "payload": {"reason": "fit window"}},
        task_id="task-1",
    )
    assert value == {
        "kind": "recompute",
        "payload": {"reason": "fit window"},
        "task_id": "task-1",
    }

    values = validate_ars_actions(
        (
            {"task_id": "task-1", "kind": "edit", "payload": {"section": "Methods"}},
            {"task_id": "task-1", "kind": "ask_human", "payload": {"question": "choose"}},
        ),
        task_id="task-1",
    )
    assert [item["kind"] for item in values] == ["edit", "ask_human"]

    with pytest.raises(ValueError, match="action kind"):
        validate_ars_action({"kind": "publish", "payload": {}}, task_id="task-1")
    with pytest.raises(ValueError, match="task"):
        validate_ars_action({"task_id": "task-2", "kind": "edit", "payload": {}}, task_id="task-1")
    with pytest.raises(ValueError, match="payload"):
        validate_ars_action({"kind": "edit", "payload": []}, task_id="task-1")


def test_suite_handoff_can_carry_validated_task_actions_without_copying_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in (
        "manifest.json",
        "ars-writing-input.json",
        "result-tables.json",
        "writing-evidence.json",
        "evidence.json",
        "citation-metrics.json",
        "figure-index.json",
    ):
        (tmp_path / name).write_text("{}", encoding="utf-8")
    view = SimpleNamespace(
        package_id="demo",
        version=1,
        status="review_required",
        human_review=(),
        techniques=(),
        run_ids=(),
        metrics=(),
    )
    monkeypatch.setattr(handoff, "load_evidence_package_view", lambda root: view)

    result = build_suite_handoff(
        tmp_path,
        task_id="task-1",
        actions=({"kind": "edit", "payload": {"section": "Results"}},),
    )

    assert result["status"] == "ready"
    assert result["task_id"] == "task-1"
    assert result["actions"][0]["task_id"] == "task-1"
    assert result["handoff_id"].startswith("handoff-")
    assert not (tmp_path / "handoff-copy.json").exists()


def _submission_manuscript() -> dict[str, object]:
    return {
        "source_id": "source-1",
        "sections": [{"name": "Results", "claim_ids": ["claim-1"]}],
        "claims": [
            {
                "claim_id": "claim-1",
                "evidence_ids": ["evidence-1"],
                "metric_ids": ["metric-1"],
                "citation_keys": ["ref-1"],
            }
        ],
        "evidence": [{"evidence_id": "evidence-1"}],
        "metrics": [{"metric_id": "metric-1"}],
        "figures": [{"figure_id": "figure-1"}],
        "citations": [{"key": "ref-1", "verified": True}],
        "formulas": [],
        "ars_workflow": {"status": "completed", "integrity": "passed"},
        "methods": {"status": "complete", "missing": []},
        "zotero": {"status": "verified", "connected": True},
        "format_report": {"status": "passed"},
        "human_review": [],
        "visible_text": "Results show a reproducible trend.",
    }


def test_submission_preflight_passes_only_when_formal_gates_are_complete() -> None:
    report = submission_preflight(_submission_manuscript())
    assert report.status == "passed"
    assert report.errors == ()
    assert report.checks["submission"] == "passed"


def test_submission_preflight_does_not_treat_ars_ready_as_completed() -> None:
    manuscript = _submission_manuscript()
    manuscript["ars_workflow"] = {"status": "ready", "integrity": "passed"}

    report = submission_preflight(manuscript)

    assert report.status == "failed"
    assert "ars_workflow_incomplete" in report.errors


@pytest.mark.parametrize("verified", ("false", "true", 0, 1, None))
def test_submission_preflight_requires_boolean_citation_verification(verified) -> None:
    manuscript = _submission_manuscript()
    manuscript["citations"] = [{"key": "ref-1", "verified": verified}]

    report = submission_preflight(manuscript)

    assert report.status == "failed"
    assert "citations_unverified" in report.errors


@pytest.mark.parametrize(
    "zotero",
    (
        {"status": "verified", "verified": "false", "connected": True},
        {"status": "verified", "verified": True, "connected": 1},
        {"status": "verified", "verified": True, "connected": "true"},
    ),
)
def test_submission_preflight_rejects_malformed_zotero_booleans(zotero) -> None:
    manuscript = _submission_manuscript()
    manuscript["zotero"] = zotero

    report = submission_preflight(manuscript)

    assert report.status == "failed"
    assert "zotero_unverified" in report.errors


@pytest.mark.parametrize("field", ("body", "results", "discussion"))
def test_submission_preflight_scans_all_visible_manuscript_sections(field: str) -> None:
    manuscript = _submission_manuscript()
    manuscript[field] = "The evidence package remains review_required."

    report = submission_preflight(manuscript)

    assert report.status == "failed"
    assert "internal_term_leak" in report.errors


@pytest.mark.parametrize(
    ("change", "reason"),
    (
        ({"ars_workflow": {"status": "draft"}}, "ars_workflow_incomplete"),
        ({"methods": {"status": "incomplete", "missing": ["instrument"]}}, "methods_incomplete"),
        ({"citations": [{"key": "ref-1", "verified": False}]}, "citations_unverified"),
        ({"citations": [{"key": "ref-1", "status": "static"}]}, "citations_unverified"),
        ({"zotero": {"status": "unavailable", "connected": False}}, "zotero_unverified"),
        ({"zotero": {"connected": True}}, "zotero_unverified"),
        ({"format_report": {"status": "failed"}}, "format_invalid"),
        ({"human_review": [{"id": "claim-1", "status": "pending"}]}, "human_review_pending"),
        ({"visible_text": "Internal evidence package review_required run hash"}, "internal_term_leak"),
    ),
)
def test_submission_preflight_reports_hard_gate_failures(
    change: dict[str, object], reason: str
) -> None:
    manuscript = _submission_manuscript()
    manuscript.update(change)
    report = submission_preflight(manuscript)
    assert report.status == "failed"
    assert reason in report.errors
    assert report.checks["submission"] == "failed"


def test_submission_preflight_keeps_legacy_internal_preflight_advisory() -> None:
    manuscript = {"source_id": "source-1", "claims": [], "figures": [], "citations": [], "formulas": []}
    legacy = preflight_manuscript(manuscript)
    assert legacy.status == "review_required"
    strict = submission_preflight(manuscript)
    assert strict.status == "failed"
    assert "ars_workflow_incomplete" in strict.errors


@pytest.mark.parametrize("review", ({"status": "pending"}, {"state": "pending"}, {"verdict": "pending"}, {"status": "passed", "verdict": "pending"}))
def test_review_gate_reads_top_level_mapping_state(review: dict[str, str]) -> None:
    manuscript = _submission_manuscript()
    manuscript["human_review"] = review
    report = submission_preflight(manuscript)
    assert report.status == "failed"
    assert "human_review_pending" in report.errors


def test_submission_preflight_rejects_forged_claim_reference_ids() -> None:
    manuscript = _submission_manuscript()
    manuscript["claims"][0]["metric_ids"] = ["metric-not-in-manuscript"]
    report = submission_preflight(manuscript)
    assert report.status == "failed"
    assert "metric_unbound:metric-not-in-manuscript" in report.errors


def test_submission_preflight_accepts_ids_from_source_projection() -> None:
    manuscript = _submission_manuscript()
    manuscript.pop("evidence")
    manuscript.pop("metrics")
    manuscript["evidence_projection"] = {
        "evidence": [{"id": "evidence-1"}],
        "metric_manifest": [{"id": "metric-1"}],
    }
    report = submission_preflight(manuscript)
    assert report.status == "passed"


def test_handoff_action_payload_rejects_non_json_values() -> None:
    with pytest.raises(ValueError, match="payload"):
        validate_ars_action(
            {"kind": "edit", "payload": {"bad": float("nan")}},
            task_id="task-1",
        )


@pytest.mark.parametrize("action_id", ("../escape", "..\\escape", ".", ""))
def test_handoff_action_rejects_unsafe_action_ids(action_id: str) -> None:
    with pytest.raises(ValueError, match="action id"):
        validate_ars_action(
            {"kind": "edit", "action_id": action_id, "payload": {}},
            task_id="task-1",
        )


def test_submission_preflight_scans_actual_text_even_with_clean_projection() -> None:
    manuscript = _submission_manuscript()
    manuscript["sections"][0]["content"] = "The evidence package is ready."

    report = submission_preflight(manuscript, visible_text="Clean projected text.")

    assert report.status == "failed"
    assert "internal_term_leak" in report.errors


def test_submission_preflight_does_not_let_external_citation_gate_override_failure() -> None:
    manuscript = _submission_manuscript()
    manuscript["citations"] = [{"key": "ref-1", "verified": False}]

    report = submission_preflight(
        manuscript,
        citations=[{"key": "ref-1", "verified": True}],
    )

    assert report.status == "failed"
    assert "citations_unverified" in report.errors


def test_submission_preflight_does_not_treat_nested_run_id_as_evidence_id() -> None:
    manuscript = _submission_manuscript()
    manuscript["evidence"] = [
        {"evidence_id": "evidence-1", "run_id": "run-1"}
    ]
    manuscript["claims"][0]["evidence_ids"] = ["run-1"]

    report = submission_preflight(manuscript)

    assert report.status == "failed"
    assert "evidence_unbound:run-1" in report.errors


def test_suite_paper_draft_does_not_export_when_submission_gate_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    source = {
        "version": 1,
        "source_id": "source-1",
        "package_id": "package-1",
        "claim_ids": [],
        "figure_plan_ids": [],
        "table_ids": [],
        "citation_ids": [],
        "limitations": [],
        "status": "draft",
        "needs_input": [],
        "projection": {"claims": [], "figures": []},
        "formula_ids": [],
    }
    monkeypatch.setattr(run_suite_service, "build_paper_bundle", lambda *args, **kwargs: {"source": source})
    monkeypatch.setattr(
        run_suite_service,
        "assemble_manuscript",
        lambda **kwargs: {"source_id": "source-1", "claims": [], "figures": [], "citations": [], "formulas": [], "sections": [], "visible_text": "draft"},
    )
    monkeypatch.setattr(
        run_suite_service,
        "submission_preflight",
        lambda manuscript: preflight_manuscript({"source_id": "source-1", "claims": [], "figures": [], "citations": [], "formulas": []}),
    )
    exported = False

    def _export(*args, **kwargs):
        nonlocal exported
        exported = True
        return {}

    monkeypatch.setattr(run_suite_service, "export_manuscript", _export)
    args = SimpleNamespace(
        operation="paper-draft",
        manifest=None,
        codex_skills_dir=None,
        lock=None,
        package=str(tmp_path / "package"),
        output=str(tmp_path / "output"),
        brief=None,
        citations=None,
        formulas=None,
    )

    code = run_suite_service.run_suite(args)

    assert code != 0
    assert exported is False
    assert json.loads(capsys.readouterr().out)["status"] != "passed"


def test_suite_paper_draft_passes_explicit_bundle_gates_and_returns_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    source = {
        "version": 1,
        "source_id": "source-1",
        "package_id": "package-1",
        "claim_ids": [],
        "figure_plan_ids": [],
        "table_ids": [],
        "citation_ids": [],
        "limitations": [],
        "status": "draft",
        "needs_input": [],
        "projection": {"claims": [], "figures": []},
        "formula_ids": [],
    }
    gates = {
        "ars_state": {"status": "completed", "integrity": "passed"},
        "methods": {"status": "complete", "missing": []},
        "citations": [{"key": "ref-1", "verified": True}],
        "zotero": {"status": "verified", "connected": True},
        "format_report": {"status": "passed"},
        "human_review": [],
        "visible_text": "A scientific result.",
    }
    monkeypatch.setattr(
        run_suite_service,
        "build_paper_bundle",
        lambda *args, **kwargs: {"source": source, "gate_projections": gates},
    )
    manuscript = _submission_manuscript()
    for key in ("ars_workflow", "methods", "zotero", "format_report", "human_review", "visible_text"):
        manuscript.pop(key)
    monkeypatch.setattr(run_suite_service, "assemble_manuscript", lambda **kwargs: manuscript)
    monkeypatch.setattr(
        run_suite_service,
        "export_manuscript",
        lambda manuscript, output: {"docx": str(Path(output) / "manuscript.docx")},
    )
    args = SimpleNamespace(
        operation="paper-draft",
        manifest=None,
        codex_skills_dir=None,
        lock=None,
        package=str(tmp_path / "package"),
        output=str(tmp_path / "output"),
        brief=None,
        citations=None,
        formulas=None,
        gates=None,
    )

    code = run_suite_service.run_suite(args)

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["status"] == "passed"
    assert payload["exports"]["docx"].endswith("manuscript.docx")
