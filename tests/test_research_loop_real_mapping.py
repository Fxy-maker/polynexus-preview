from __future__ import annotations

from pathlib import Path

from polynexus.core.canonical_experiments import MappingProposal, MappingSelection
from polynexus.core.project_workflow import ProjectWorkflowService


def test_research_loop_accepts_mapping_bound_to_project_inventory_artifact(
    tmp_path: Path,
) -> None:
    """A mapping confirmed from ProjectWorkflow.inspect must survive the run boundary."""
    source = tmp_path / "raw" / "NMR" / "headerless.csv"
    source.parent.mkdir(parents=True)
    source.write_text(
        "-4.0\t1.0\n-3.9\t2.0\n-3.8\t3.0\n-3.7\t4.0\n",
        encoding="utf-8",
    )

    workflow = ProjectWorkflowService.open(tmp_path)
    loop = workflow.research_loop()
    task = loop.create_task(
        task_id="inventory-mapping-task",
        project_id="demo",
        research_question="Validate the headerless NMR mapping",
        data_scope=(source.relative_to(tmp_path).as_posix(),),
    )
    loop.inspect(task.task_id)
    artifact = workflow.inspect((source.relative_to(tmp_path).as_posix(),)).artifacts[0]
    mapping = MappingProposal.create(
        source_artifact_id=artifact.artifact_id,
        technique="NMR",
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
                "-4.0",
                "1.0",
                "chemical_shift",
                "unknown",
                "unknown",
                "user",
            ),
        ),
    )
    loop.propose_mapping(
        task.task_id,
        {
            "mapping_proposal": mapping.to_dict(),
            "request_parameters": {"submodule_id": "nmr.liquid_h"},
        },
    )
    loop.confirm_mapping(task.task_id, approved=True, approver="user")

    result = loop.run(task.task_id, requested_outputs=("tables",))

    assert result.status == "checkpointed", result.to_dict()
    assert result.metadata["run_status"] in {"completed", "review_required"}
