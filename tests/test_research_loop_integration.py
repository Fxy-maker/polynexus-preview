from __future__ import annotations

import json
from pathlib import Path
import shutil

from polynexus.core.canonical_experiments import MappingProposal, MappingSelection
from polynexus.core.project_workflow import ProjectWorkflowService


_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "research_loop"


def _copy_fixture(project_root: Path) -> Path:
    """Copy the tiny raw fixture into an isolated project workspace."""
    shutil.copytree(_FIXTURE_ROOT / "raw", project_root / "raw")
    return project_root / "raw" / "IR" / "spectrum.csv"


def _manuscript_from_package(package_path: Path) -> dict[str, object]:
    """Build a submission-shaped manuscript from package projections only."""
    evidence = json.loads((package_path / "evidence.json").read_text(encoding="utf-8"))["items"]
    metrics = json.loads((package_path / "citation-metrics.json").read_text(encoding="utf-8"))["records"]
    figures = json.loads((package_path / "figure-index.json").read_text(encoding="utf-8"))["figures"]
    assert evidence, "the real ProjectWorkflow run must produce evidence"
    assert figures, "the real ProjectWorkflow run must produce at least one figure"
    evidence_id = str(evidence[0]["evidence_id"])
    metric_ids = [str(metrics[0]["metric_id"])] if metrics else []
    figure_id = str(figures[0]["id"])
    claim: dict[str, object] = {
        "claim_id": "claim-1",
        "evidence_ids": [evidence_id],
        "figure_ids": [figure_id],
        "citation_keys": ["ref-1"],
        "text": "The fixture spectrum is observed and reproducible.",
    }
    if metric_ids:
        claim["metric_ids"] = metric_ids
    return {
        "source_id": "research-loop-fixture",
        "sections": [
            {
                "section_id": "results",
                "name": "Results",
                "claim_ids": ["claim-1"],
                "content": "The fixture spectrum is observed and reproducible.",
            }
        ],
        "claims": [claim],
        "evidence": [{"evidence_id": evidence_id}],
        "metrics": ([{"metric_id": metric_ids[0]}] if metric_ids else []),
        "figures": [{"figure_id": figure_id}],
        "citations": [{"key": "ref-1", "verified": True}],
        "formulas": [],
        "ars_workflow": {"status": "completed", "integrity": "passed"},
        "methods": {"status": "complete", "missing": []},
        "zotero": {"status": "verified", "connected": True},
        "format_report": {"status": "passed"},
        "human_review": [],
        "visible_text": "The fixture spectrum is observed and reproducible.",
    }


def test_real_project_workflow_research_loop_round_trips_full_lifecycle(tmp_path: Path) -> None:
    """Exercise the resumable loop against the real project workflow service."""
    source = _copy_fixture(tmp_path)
    relative_source = source.relative_to(tmp_path).as_posix()
    workflow = ProjectWorkflowService.open(tmp_path)
    loop = workflow.research_loop()

    task = loop.create_task(
        task_id="fixture-full-loop",
        project_id="fixture-project",
        research_question="What does the fixture IR spectrum show?",
        data_scope=(relative_source,),
    )
    assert task.status == "draft"

    inspected = loop.inspect(task.task_id)
    assert inspected.status == "awaiting_mapping_confirmation"
    assert inspected.metadata["discovered_paths"] == (relative_source,)

    graph = workflow.inspect((relative_source,))
    artifact = graph.artifacts[0]
    mapping = MappingProposal.create(
        source_artifact_id=artifact.artifact_id,
        technique="IR",
        source="user",
        selections=(
            MappingSelection(
                "sheet-0-table-0",
                None,
                None,
                0,
                0,
                1,
                3,
                "Wavenumber",
                "Absorbance",
                "wavenumber",
                "unknown",
                "unknown",
                "user",
            ),
        ),
    )
    proposed = loop.propose_mapping(task.task_id, mapping.to_dict())
    assert proposed.mapping_proposal["proposal_id"] == mapping.proposal_id
    confirmed = loop.confirm_mapping(task.task_id, approved=True, approver="fixture-user")
    assert confirmed.status == "ready"

    ran = loop.run(task.task_id)
    assert ran.status == "checkpointed", ran.to_dict()
    assert len(ran.run_ids) == 1

    checkpointed = loop.checkpoint(task.task_id)
    package_path = Path(checkpointed.package_paths[-1])
    assert package_path.is_dir()
    manifest = json.loads((package_path / "manifest.json").read_text(encoding="utf-8"))
    assert ran.run_ids[0] in manifest["run_ids"]
    assert (package_path / "ars-writing-input.json").is_file()

    handed_off = loop.handoff_to_ars(task.task_id, package_path)
    assert handed_off.status == "ars_in_progress"
    assert handed_off.handoff_ids

    actions = loop.record_ars_actions(
        task.task_id,
        (
            {"kind": "edit", "payload": {"section": "Methods"}},
            {"kind": "recompute", "payload": {"reason": "fit window"}},
            {"kind": "ask_human", "payload": {"question": "confirm interpretation"}},
        ),
    )
    assert {action.kind for action in actions} == {"edit", "recompute", "ask_human"}
    assert loop.resume(task.task_id).status == "awaiting_human"

    by_kind = {action.kind: action for action in actions}
    loop.resolve_action(task.task_id, by_kind["edit"].action_id, approved=True, note="edited")
    loop.resolve_action(task.task_id, by_kind["ask_human"].action_id, approved=True, note="confirmed")
    assert loop.resume(task.task_id).status == "revision_required"

    recomputed = loop.recompute(task.task_id, requested_outputs=("figures",))
    assert recomputed.status == "checkpointed"
    assert len(recomputed.run_ids) == 2
    assert len(set(recomputed.run_ids)) == 2
    assert loop.store.load_action(task.task_id, by_kind["recompute"].action_id).status == "resolved"

    recompute_checkpoint = loop.checkpoint(task.task_id)
    recompute_package_path = Path(recompute_checkpoint.package_paths[-1])
    assert recompute_package_path != package_path
    recompute_manifest = json.loads(
        (recompute_package_path / "manifest.json").read_text(encoding="utf-8")
    )
    assert recomputed.run_ids[-1] in recompute_manifest["run_ids"]
    rehanded_off = loop.handoff_to_ars(task.task_id, recompute_package_path)
    assert rehanded_off.status == "ars_in_progress"
    assert len(rehanded_off.handoff_ids) == 2
    loop.record_ars_completion(
        task.task_id, {"status": "completed", "integrity": "passed"}
    )

    report = loop.submission_preflight(
        task.task_id,
        _manuscript_from_package(recompute_package_path),
    )
    assert report.status == "passed"
    assert loop.resume(task.task_id).status == "export_ready"

    export_docx = tmp_path / "manuscript.docx"
    export_pdf = tmp_path / "manuscript.pdf"
    export_docx.write_bytes(b"fixture-docx")
    export_pdf.write_bytes(b"fixture-pdf")
    completed = loop.complete_export(task.task_id, (export_docx, export_pdf))
    assert completed.status == "completed"
    assert completed.metadata["export_paths"] == (
        str(export_docx.resolve()),
        str(export_pdf.resolve()),
    )

    reloaded = ProjectWorkflowService.open(tmp_path).research_loop().resume(task.task_id)
    assert reloaded.status == "completed"
    assert reloaded.run_ids == completed.run_ids
    assert reloaded.package_paths == completed.package_paths
    assert reloaded.action_ids == completed.action_ids
