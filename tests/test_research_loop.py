from __future__ import annotations

import json
import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from polynexus.core.project_workflow.research_loop import (
    ResearchAction,
    ResearchLoopService,
    ResearchTask,
    ResearchTaskStore,
)
from polynexus.core.project_workflow.workspace import ProjectWorkspace
from polynexus.core.project_workflow import ProjectWorkflowService
from polynexus.core.project_workflow.models import canonical_json


def test_research_task_round_trips_and_has_stable_identity(tmp_path: Path) -> None:
    task = ResearchTask.create(
        project_id="demo",
        research_question="Why does crystallization differ?",
        data_scope=("raw/DSC", "raw/IR"),
        target_journal="Polymer",
    )

    restored = ResearchTask.from_dict(task.to_dict())

    assert restored == task
    assert task.task_id
    assert task.revision == 0
    assert task.status == "draft"
    assert task.content_hash


def test_project_workflow_exposes_the_same_research_loop_service(tmp_path: Path) -> None:
    workflow = ProjectWorkflowService.open(tmp_path)

    loop = workflow.research_loop()

    assert isinstance(loop, ResearchLoopService)
    assert loop.project_service is workflow


def test_store_appends_revisions_without_overwriting_previous_snapshot(tmp_path: Path) -> None:
    store = ResearchTaskStore(ProjectWorkspace.open(tmp_path))
    first = store.create_task(project_id="demo", research_question="q")
    second = store.transition(first.task_id, "awaiting_mapping_confirmation")

    revision_dir = tmp_path / ".polynexus" / "research" / "tasks" / first.task_id / "revisions"
    files = sorted(revision_dir.glob("task-*.json"))
    assert [path.name for path in files] == ["task-000001.json", "task-000002.json"]
    assert json.loads(files[0].read_text(encoding="utf-8"))["status"] == "draft"
    assert second.revision == 2
    assert store.load(first.task_id) == second


def test_store_rejects_invalid_transition_and_tampered_revision(tmp_path: Path) -> None:
    store = ResearchTaskStore(ProjectWorkspace.open(tmp_path))
    task = store.create_task(project_id="demo", research_question="q")

    with pytest.raises(ValueError, match="transition"):
        store.transition(task.task_id, "completed")

    latest = tmp_path / ".polynexus" / "research" / "tasks" / task.task_id / "revisions" / "task-000001.json"
    payload = json.loads(latest.read_text(encoding="utf-8"))
    payload["research_question"] = "tampered"
    latest.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="hash|revision"):
        store.load(task.task_id)


def test_store_ignores_an_incomplete_revision_beyond_latest_pointer(tmp_path: Path) -> None:
    store = ResearchTaskStore(ProjectWorkspace.open(tmp_path))
    task = store.create_task(project_id="demo", research_question="q")
    revision_dir = tmp_path / ".polynexus" / "research" / "tasks" / task.task_id / "revisions"
    (revision_dir / "task-000002.json").write_text("{", encoding="utf-8")

    assert store.load(task.task_id).revision == 1


def test_store_rejects_tampered_index_pointer_hash(tmp_path: Path) -> None:
    store = ResearchTaskStore(ProjectWorkspace.open(tmp_path))
    task = store.create_task(project_id="demo", research_question="q")
    index = tmp_path / ".polynexus" / "research" / "index.json"
    payload = json.loads(index.read_text(encoding="utf-8"))
    payload["tasks"][task.task_id]["content_hash"] = "0" * 64
    index.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="pointer"):
        store.load(task.task_id)


def test_store_rejects_path_traversal_task_ids(tmp_path: Path) -> None:
    store = ResearchTaskStore(ProjectWorkspace.open(tmp_path))
    with pytest.raises(ValueError, match="task id"):
        store._task_dir("../escape")


def test_store_rejects_transition_lineage_overrides(tmp_path: Path) -> None:
    """A transition may only derive the next revision from the loaded head."""
    store = ResearchTaskStore(ProjectWorkspace.open(tmp_path))
    task = store.create_task(project_id="demo", research_question="q")

    with pytest.raises(ValueError, match="immutable"):
        store.transition(
            task.task_id,
            "awaiting_mapping_confirmation",
            revision=99,
        )


def test_store_rejects_append_with_changed_task_identity(tmp_path: Path) -> None:
    """An append cannot turn a task lineage into another project/question."""
    store = ResearchTaskStore(ProjectWorkspace.open(tmp_path))
    task = store.create_task(project_id="demo", research_question="q")
    candidate = replace(
        task,
        status="awaiting_mapping_confirmation",
        project_id="other-project",
        research_question="different question",
        revision=task.revision + 1,
        parent_revision=task.revision,
        parent_hash=task.content_hash,
        content_hash="",
    )

    with pytest.raises(ValueError, match="identity"):
        store.append(candidate)


def test_store_rejects_resolution_file_with_mismatched_revision_name(tmp_path: Path) -> None:
    """A resolution sibling's filename must identify its serialized revision."""
    store = ResearchTaskStore(ProjectWorkspace.open(tmp_path))
    task = store.create_task(project_id="demo", research_question="q")
    action = ResearchAction.create(task_id=task.task_id, kind="ask_human", payload={"question": "q"})
    store.save_action(action)
    resolution = replace(
        action,
        status="resolved",
        resolution={"approved": True, "note": "ok"},
        revision=2,
        parent_hash=action.content_hash,
        content_hash="",
    )
    action_dir = tmp_path / ".polynexus" / "research" / "tasks" / task.task_id / "actions"
    (action_dir / f"{action.action_id}-r0003.json").write_text(
        json.dumps(resolution.to_dict()), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="invalid"):
        store.load_action(task.task_id, action.action_id)


def test_store_rejects_malformed_resolution_sibling_name(tmp_path: Path) -> None:
    """A valid resolution payload cannot hide behind an unparseable sibling name."""
    store = ResearchTaskStore(ProjectWorkspace.open(tmp_path))
    task = store.create_task(project_id="demo", research_question="q")
    action = ResearchAction.create(task_id=task.task_id, kind="ask_human", payload={"question": "q"})
    store.save_action(action)
    resolution = replace(
        action,
        status="resolved",
        resolution={"approved": True, "note": "ok"},
        revision=2,
        parent_hash=action.content_hash,
        content_hash="",
    )
    action_dir = tmp_path / ".polynexus" / "research" / "tasks" / task.task_id / "actions"
    (action_dir / f"{action.action_id}-rfoo.json").write_text(
        json.dumps(resolution.to_dict()), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="invalid"):
        store.load_action(task.task_id, action.action_id)


def test_tasks_are_isolated_and_actions_are_typed(tmp_path: Path) -> None:
    store = ResearchTaskStore(ProjectWorkspace.open(tmp_path))
    one = store.create_task(project_id="demo", research_question="one")
    two = store.create_task(project_id="demo", research_question="two")
    action = ResearchAction.create(task_id=one.task_id, kind="ask_human", payload={"question": "confirm"})

    assert {item.task_id for item in store.list_tasks()} == {one.task_id, two.task_id}
    assert action.kind == "ask_human"
    with pytest.raises(ValueError, match="action kind"):
        ResearchAction.create(task_id=one.task_id, kind="publish", payload={})
    with pytest.raises(ValueError, match="payload"):
        ResearchAction.create(task_id=one.task_id, kind="edit", payload=[])  # type: ignore[arg-type]


class _FakeProjectWorkflow:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.run_count = 0
        self.requests = []

    def inspect(self, paths):
        self.calls.append("inspect")
        return type("Graph", (), {"graph_hash": "graph-1", "artifacts": ()})()

    def run(self, request):
        self.calls.append("run")
        self.requests.append(request)
        self.run_count += 1
        return type("Run", (), {"run_id": f"run-{self.run_count}", "status": "review_required", "reason_codes": ()})()


def _prepare_validated_handoff(
    service: ResearchLoopService,
    task_id: str,
    package: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    handoff_id: str = "handoff-minimal",
) -> None:
    """Install a minimal Suite handoff that satisfies the strict ARS boundary."""
    import polynexus.suite.handoff as suite_handoff

    files = {
        "ars_writing_input": "ars-writing-input.json",
        "result_tables": "result-tables.json",
        "writing_evidence": "writing-evidence.json",
        "evidence": "evidence.json",
        "citation_metrics": "citation-metrics.json",
        "figure_index": "figure-index.json",
    }
    package.mkdir(parents=True, exist_ok=True)
    payloads = {
        "ars-writing-input.json": {},
        "result-tables.json": {},
        "writing-evidence.json": {
            "techniques": {"nmr": {"evidence": [{"evidence_id": "evidence-1"}]}}
        },
        "evidence.json": {"items": [{"evidence_id": "evidence-1"}]},
        "citation-metrics.json": {
            "records": [{"metric_id": "metric-1", "evidence_id": "evidence-1"}]
        },
        "figure-index.json": {"figures": [{"id": "figure-1"}]},
    }
    for relative in files.values():
        (package / relative).write_text(
            json.dumps(payloads[relative]), encoding="utf-8"
        )
    current = service.store.load(task_id)
    run_id = current.run_ids[-1]
    runs_dir = package / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / f"{run_id}.json").write_text(
        canonical_json(
            {"run_id": run_id, "request_parameters": {"research_task_id": task_id}}
        ),
        encoding="utf-8",
    )
    unsigned_manifest = {
        "package_id": "minimal",
        "version": 1,
        "status": "completed",
        "run_ids": [run_id],
        "run_manifests": [f"runs/{run_id}.json"],
        "artifact_hashes": [],
    }
    package_hash = hashlib.sha256(
        canonical_json(unsigned_manifest).encode("utf-8")
    ).hexdigest()
    (package / "manifest.json").write_text(
        canonical_json({**unsigned_manifest, "package_hash": package_hash}),
        encoding="utf-8",
    )

    def fake_build_suite_handoff(package_path: str | Path, **kwargs: object) -> dict[str, object]:
        bound_task_id = str(kwargs.get("task_id") or task_id)
        return {
            "status": "ready",
            "handoff_id": handoff_id,
            "task_id": bound_task_id,
            "package": {
                "path": str(Path(package_path).expanduser().resolve()),
                "package_hash": package_hash,
            },
            "files": files,
            "run_ids": [run_id],
        }

    monkeypatch.setattr(suite_handoff, "build_suite_handoff", fake_build_suite_handoff)
    service.handoff_to_ars(task_id, package)


def _formal_submission() -> dict[str, object]:
    return {
        "source_id": "source",
        "sections": [{"section_id": "results", "claim_ids": ["claim-1"]}],
        "claims": [{
            "claim_id": "claim-1",
            "text": "A measured result is reported.",
            "evidence_ids": ["evidence-1"],
            "metric_ids": ["metric-1"],
            "figure_ids": ["figure-1"],
            "citation_keys": ["r"],
        }],
        "evidence": [{"evidence_id": "evidence-1"}],
        "metrics": [{"metric_id": "metric-1"}],
        "figures": [{"figure_id": "figure-1"}],
        "citations": [{"key": "r", "verified": True}],
        "formulas": [],
        "methods": {"status": "complete"},
        "zotero": {"status": "verified", "connected": True},
        "format_report": {"status": "passed"},
        "human_review": [],
        "visible_text": "A measured result is reported.",
    }


def test_explicit_stages_require_mapping_confirmation_before_run(tmp_path: Path) -> None:
    workflow = _FakeProjectWorkflow()
    service = ResearchLoopService.open(tmp_path, project_service=workflow)
    task = service.create_task(
        project_id="demo",
        research_question="q",
        data_scope=("raw/sample.csv",),
    )

    inspected = service.inspect(task.task_id)
    proposed = service.propose_mapping(task.task_id, {"raw/sample.csv": {"sample_id": "A"}})
    assert inspected.status == "awaiting_mapping_confirmation"
    assert proposed.status == "awaiting_mapping_confirmation"
    with pytest.raises(ValueError, match="confirmation"):
        service.run(task.task_id)

    ready = service.confirm_mapping(task.task_id, approved=True, approver="user")
    result = service.run(task.task_id)
    assert ready.status == "ready"
    assert result.status == "checkpointed"
    assert workflow.calls == ["inspect", "run"]
    assert workflow.requests[0].parameters["mapping_proposal"]["raw/sample.csv"]["sample_id"] == "A"


def test_confirmed_mapping_envelope_carries_explicit_request_parameters(tmp_path: Path) -> None:
    workflow = _FakeProjectWorkflow()
    service = ResearchLoopService.open(tmp_path, project_service=workflow)
    task = service.create_task(
        project_id="demo",
        research_question="Analyze the confirmed liquid-state proton NMR mapping",
        data_scope=("raw/NMR/sample.csv",),
    )
    canonical_mapping = {
        "proposal_id": "proposal-1",
        "source_artifact_id": "artifact-1",
        "technique": "NMR",
        "source": "user",
        "selections": [],
        "warnings": [],
        "alternatives": [],
    }
    service.propose_mapping(
        task.task_id,
        {
            "mapping_proposal": canonical_mapping,
            "request_parameters": {"submodule_id": "nmr.liquid_h"},
        },
    )
    service.confirm_mapping(task.task_id, approved=True, approver="user")

    result = service.run(task.task_id)

    assert result.status == "checkpointed"
    assert workflow.requests[0].parameters["submodule_id"] == "nmr.liquid_h"
    request_payload = workflow.requests[0].to_dict()["parameters"]
    assert request_payload["mapping_proposal"] == canonical_mapping
    assert request_payload["confirmed_mapping"]["request_parameters"] == {
        "submodule_id": "nmr.liquid_h"
    }


def test_mapping_confirmation_requires_an_approver(tmp_path: Path) -> None:
    service = ResearchLoopService.open(tmp_path, project_service=_FakeProjectWorkflow())
    task = service.create_task(project_id="demo", research_question="q")
    service.propose_mapping(task.task_id, {"raw/a.csv": {"sample_id": "A"}})

    with pytest.raises(ValueError, match="approver"):
        service.confirm_mapping(task.task_id, approved=True, approver="")


def test_quick_run_attachments_are_not_discovered_by_research_task(tmp_path: Path) -> None:
    workspace = ProjectWorkspace.open(tmp_path)
    (workspace.evidence_dir / "quick-runs.json").write_text(
        json.dumps({"quick_run_id": "gui-1", "source_file": "raw/quick.csv"}),
        encoding="utf-8",
    )
    service = ResearchLoopService.open(tmp_path, project_service=_FakeProjectWorkflow())
    task = service.create_task(project_id="demo", research_question="q")

    inspected = service.inspect(task.task_id)

    assert "quick-runs.json" not in inspected.metadata.get("discovered_paths", ())


def test_ars_actions_route_and_resume_from_latest_revision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = ResearchLoopService.open(tmp_path, project_service=_FakeProjectWorkflow())
    task = service.create_task(project_id="demo", research_question="q")
    task = service.propose_mapping(task.task_id, {"raw/a.csv": {"sample_id": "A"}})
    service.confirm_mapping(task.task_id, approved=True, approver="user")
    service.run(task.task_id)
    package = tmp_path / "package"
    service.checkpoint(task.task_id, package_path=package)
    _prepare_validated_handoff(service, task.task_id, package, monkeypatch)

    actions = service.record_ars_actions(
        task.task_id,
        (
            {"kind": "edit", "payload": {"section": "Methods"}},
            {"kind": "recompute", "payload": {"reason": "fit window"}},
            {"kind": "ask_human", "payload": {"question": "select mechanism"}},
        ),
    )

    assert [action.kind for action in actions] == ["edit", "recompute", "ask_human"]
    assert service.resume(task.task_id).status == "awaiting_human"
    assert service.resume(task.task_id).action_ids == tuple(action.action_id for action in actions)


def test_new_ars_actions_do_not_hide_existing_pending_actions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = ResearchLoopService.open(tmp_path, project_service=_FakeProjectWorkflow())
    task = service.create_task(project_id="demo", research_question="q")
    service.propose_mapping(task.task_id, {"raw/a.csv": {"sample_id": "A"}})
    service.confirm_mapping(task.task_id, approved=True, approver="user")
    service.run(task.task_id)
    package = tmp_path / "package"
    service.checkpoint(task.task_id, package_path=package)
    _prepare_validated_handoff(service, task.task_id, package, monkeypatch)
    first = service.record_ars_actions(task.task_id, ({"kind": "ask_human", "payload": {"question": "q"}},))[0]
    service.record_ars_actions(task.task_id, ({"kind": "edit", "payload": {}},))
    assert service.resume(task.task_id).status == "awaiting_human"
    assert first.action_id in service.resume(task.task_id).action_ids


def test_research_loop_uses_strict_suite_actions_and_submission_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = ResearchLoopService.open(tmp_path, project_service=_FakeProjectWorkflow())
    task = service.create_task(project_id="demo", research_question="q")
    service.propose_mapping(task.task_id, {"raw/a.csv": {"sample_id": "A"}})
    service.confirm_mapping(task.task_id, approved=True, approver="user")
    service.run(task.task_id)
    package = tmp_path / "package"
    service.checkpoint(task.task_id, package_path=package)
    _prepare_validated_handoff(service, task.task_id, package, monkeypatch)
    service.record_ars_actions(task.task_id, ({"kind": "edit", "payload": {}},))

    with pytest.raises(ValueError, match="another task"):
        service.record_ars_actions(
            task.task_id,
            ({"task_id": "other", "kind": "edit", "payload": {}},),
        )

    report = service.submission_preflight(
        task.task_id,
        {
            "source_id": "source",
            "sections": [],
            "claims": [],
            "figures": [],
            "citations": [],
            "formulas": [],
            "visible_text": "draft",
        },
    )

    assert report.status == "failed"
    assert service.resume(task.task_id).status == "revision_required"


def test_checkpointed_task_cannot_skip_ars_handoff_for_formal_preflight(
    tmp_path: Path,
) -> None:
    service = ResearchLoopService.open(tmp_path, project_service=_FakeProjectWorkflow())
    task = service.create_task(project_id="demo", research_question="q")
    service.propose_mapping(task.task_id, {"raw/a.csv": {"sample_id": "A"}})
    service.confirm_mapping(task.task_id, approved=True, approver="user")
    service.run(task.task_id)
    service.checkpoint(task.task_id, package_path=tmp_path / "package")

    with pytest.raises(ValueError, match="validated ARS handoff is required"):
        service.submission_preflight(
            task.task_id,
            {
                "source_id": "source",
                "sections": [],
                "claims": [],
                "figures": [{"figure_id": "f"}],
                "citations": [{"key": "r", "verified": True}],
                "formulas": [],
                "ars_workflow": {"status": "completed", "integrity": "passed"},
                "methods": {"status": "complete"},
                "zotero": {"status": "verified", "connected": True},
                "format_report": {"status": "passed"},
                "human_review": [],
                "visible_text": "A scientific result.",
            },
        )


def test_resolving_action_is_append_only_and_updates_latest_action_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = ResearchLoopService.open(tmp_path, project_service=_FakeProjectWorkflow())
    task = service.create_task(project_id="demo", research_question="q")
    service.propose_mapping(task.task_id, {"raw/a.csv": {"sample_id": "A"}})
    service.confirm_mapping(task.task_id, approved=True, approver="user")
    service.run(task.task_id)
    package = tmp_path / "package"
    service.checkpoint(task.task_id, package_path=package)
    _prepare_validated_handoff(service, task.task_id, package, monkeypatch)
    action = service.record_ars_actions(
        task.task_id,
        ({"kind": "ask_human", "payload": {"question": "choose"}},),
    )[0]

    resolved_task = service.resolve_action(task.task_id, action.action_id, approved=True, note="accepted")

    assert resolved_task.status == "ars_in_progress"
    latest_action = service.store.load_action(task.task_id, action.action_id)
    assert latest_action.status == "resolved"
    action_dir = tmp_path / ".polynexus" / "research" / "tasks" / task.task_id / "actions"
    assert (action_dir / f"{action.action_id}.json").is_file()
    assert (action_dir / f"{action.action_id}-r0002.json").is_file()


def test_rejecting_a_human_action_does_not_silently_resume_research(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = ResearchLoopService.open(tmp_path, project_service=_FakeProjectWorkflow())
    task = service.create_task(project_id="demo", research_question="q")
    service.propose_mapping(task.task_id, {"raw/a.csv": {"sample_id": "A"}})
    service.confirm_mapping(task.task_id, approved=True, approver="user")
    service.run(task.task_id)
    package = tmp_path / "package"
    service.checkpoint(task.task_id, package_path=package)
    _prepare_validated_handoff(service, task.task_id, package, monkeypatch)
    action = service.record_ars_actions(
        task.task_id,
        ({"kind": "ask_human", "payload": {"question": "choose"}},),
    )[0]

    rejected = service.resolve_action(task.task_id, action.action_id, approved=False, note="not enough context")

    assert rejected.status == "blocked"


def test_successful_submission_can_be_marked_completed_with_export_references(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = ResearchLoopService.open(tmp_path, project_service=_FakeProjectWorkflow())
    task = service.create_task(project_id="demo", research_question="q")
    service.propose_mapping(task.task_id, {"raw/a.csv": {"sample_id": "A"}})
    service.confirm_mapping(task.task_id, approved=True, approver="user")
    service.run(task.task_id)
    package = tmp_path / "package"
    service.checkpoint(task.task_id, package_path=package)
    _prepare_validated_handoff(service, task.task_id, package, monkeypatch)
    edit_action = service.record_ars_actions(task.task_id, ({"kind": "edit", "payload": {}},))[0]
    service.resolve_action(task.task_id, edit_action.action_id, approved=True, note="edited")
    service.record_ars_completion(
        task.task_id, {"status": "completed", "integrity": "passed"}
    )
    report = service.submission_preflight(task.task_id, _formal_submission())
    assert report.status == "passed"

    docx = tmp_path / "manuscript.docx"
    pdf = tmp_path / "manuscript.pdf"
    docx.write_bytes(b"docx")
    pdf.write_bytes(b"pdf")
    completed = service.complete_export(task.task_id, (docx, pdf))

    assert completed.status == "completed"
    assert completed.metadata["export_paths"] == (str(docx.resolve()), str(pdf.resolve()))


def test_export_completion_rejects_missing_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = ResearchLoopService.open(tmp_path, project_service=_FakeProjectWorkflow())
    task = service.create_task(project_id="demo", research_question="q")
    service.propose_mapping(task.task_id, {"raw/a.csv": {"sample_id": "A"}})
    service.confirm_mapping(task.task_id, approved=True, approver="user")
    service.run(task.task_id)
    package = tmp_path / "package"
    service.checkpoint(task.task_id, package_path=package)
    _prepare_validated_handoff(service, task.task_id, package, monkeypatch)
    service.store.transition(task.task_id, "ars_in_progress", stage="ars_complete")
    service.record_ars_completion(
        task.task_id, {"status": "completed", "integrity": "passed"}
    )
    service.submission_preflight(task.task_id, _formal_submission())

    with pytest.raises(ValueError, match="missing"):
        service.complete_export(task.task_id, (tmp_path / "missing.docx",))


def test_recompute_action_returns_to_run_stage_with_new_run_reference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow = _FakeProjectWorkflow()
    service = ResearchLoopService.open(tmp_path, project_service=workflow)
    task = service.create_task(project_id="demo", research_question="q")
    service.propose_mapping(task.task_id, {"raw/a.csv": {"sample_id": "A"}})
    service.confirm_mapping(task.task_id, approved=True, approver="user")
    first = service.run(task.task_id)
    package = tmp_path / "package"
    service.checkpoint(task.task_id, package_path=package)
    _prepare_validated_handoff(service, task.task_id, package, monkeypatch)
    service.record_ars_actions(task.task_id, ({"kind": "recompute", "payload": {"reason": "fit"}},))

    recomputed = service.recompute(task.task_id)

    assert recomputed.status == "checkpointed"
    assert recomputed.run_ids == ("run-1", "run-2")
    assert workflow.calls == ["run", "run"]
    assert first.run_ids == ("run-1",)
    assert workflow.requests[0].request_hash != workflow.requests[1].request_hash


def test_formal_preflight_rejects_pending_ars_action_even_if_task_status_is_active(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = ResearchLoopService.open(tmp_path, project_service=_FakeProjectWorkflow())
    task = service.create_task(project_id="demo", research_question="q")
    service.propose_mapping(task.task_id, {"raw/a.csv": {"sample_id": "A"}})
    service.confirm_mapping(task.task_id, approved=True, approver="user")
    service.run(task.task_id)
    package = tmp_path / "package"
    service.checkpoint(task.task_id, package_path=package)
    _prepare_validated_handoff(service, task.task_id, package, monkeypatch)
    service.record_ars_actions(task.task_id, ({"kind": "edit", "payload": {}},))

    report = service.submission_preflight(
        task.task_id,
        {
            "source_id": "source",
            "sections": [],
            "claims": [],
            "figures": [{"figure_id": "f"}],
            "citations": [{"key": "r", "verified": True}],
            "formulas": [],
            "ars_workflow": {"status": "completed", "integrity": "passed"},
            "methods": {"status": "complete"},
            "zotero": {"status": "verified", "connected": True},
            "format_report": {"status": "passed"},
            "human_review": [],
            "visible_text": "A scientific result.",
        },
    )

    assert report.status == "failed"
    assert "ars_actions_pending" in report.errors


def test_handoff_persists_task_bound_ars_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workflow = _FakeProjectWorkflow()
    service = ResearchLoopService.open(tmp_path, project_service=workflow)
    task = service.create_task(project_id="demo", research_question="q")
    service.propose_mapping(task.task_id, {"raw/a.csv": {"sample_id": "A"}})
    service.confirm_mapping(task.task_id, approved=True, approver="user")
    service.run(task.task_id)
    package = tmp_path / "package"
    service.checkpoint(task.task_id, package_path=package)
    _prepare_validated_handoff(service, task.task_id, package, monkeypatch, handoff_id="handoff-1")

    handed_off = service.store.load(task.task_id)

    assert handed_off.status == "ars_in_progress"
    assert handed_off.handoff_ids == ("handoff-1",)
    record = tmp_path / ".polynexus" / "research" / "tasks" / task.task_id / "handoffs" / "handoff-1.json"
    assert json.loads(record.read_text(encoding="utf-8"))["task_id"] == task.task_id


def test_handoff_rejects_package_without_the_latest_task_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import polynexus.suite.handoff as suite_handoff

    workflow = _FakeProjectWorkflow()
    service = ResearchLoopService.open(tmp_path, project_service=workflow)
    task = service.create_task(project_id="demo", research_question="q")
    service.propose_mapping(task.task_id, {"raw/a.csv": {"sample_id": "A"}})
    service.confirm_mapping(task.task_id, approved=True, approver="user")
    ran = service.run(task.task_id)
    package = tmp_path / "package"
    service.checkpoint(task.task_id, package_path=package)
    monkeypatch.setattr(
        suite_handoff,
        "build_suite_handoff",
        lambda package_path, **kwargs: {
            "status": "ready",
            "handoff_id": "handoff-wrong-run",
            "task_id": kwargs["task_id"],
            "package": {"path": str(package_path)},
            "run_ids": ["run-from-another-task"],
        },
    )

    with pytest.raises(ValueError, match="run"):
        service.handoff_to_ars(ran.task_id, package)
