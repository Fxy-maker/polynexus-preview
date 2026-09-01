from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from polynexus.core.agent_workflow import AgentWorkflowService
from polynexus.core.engine import AnalysisResult
from polynexus.core.project_workflow import ProjectWorkflowService
from polynexus.core.project_workflow.models import AnalysisRequest
from polynexus.core.project_workflow.research_loop import ResearchLoopService


def _service(tmp_path: Path) -> ProjectWorkflowService:
    service = ProjectWorkflowService.open(tmp_path)
    service.agent_service = AgentWorkflowService(
        provider_runner=lambda step, artifact, output: AnalysisResult(
            technique=step.technique, validation_passed=True
        )
    )
    return service


def _run(service: ProjectWorkflowService, tmp_path: Path, source_name: str, question: str):
    source = tmp_path / "raw" / "NMR" / f"{source_name}.csv"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("ppm,intensity\n1.0,2\n1.5,3\n", encoding="utf-8")
    relative_source = source.relative_to(tmp_path).as_posix()
    service.inspect((relative_source,))
    request = AnalysisRequest.create(
        question=question,
        data_scope=(relative_source,),
        parameters={"submodule_id": "nmr.liquid_h"},
    )
    return service, service.run(request)


def test_freeze_selected_run_ids_only_packages_the_selected_working_entries(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    _, first = _run(service, tmp_path, "PA11-H", "first")
    _, second = _run(service, tmp_path, "PA12-H", "second")
    service.upsert_working_run(first)
    service.upsert_working_run(second)

    package = service.freeze_working_evidence(
        package_id="selected-evidence",
        selected_run_ids=(second.run_id,),
    )

    manifest = json.loads((package.path / "manifest.json").read_text(encoding="utf-8"))
    assert tuple(manifest["run_ids"]) == (second.run_id,)


@pytest.mark.parametrize(
    ("selected_run_ids", "message"),
    [
        ((), "empty"),
        (("run-does-not-exist",), "unknown"),
    ],
)
def test_freeze_selected_run_ids_fails_closed_for_empty_or_unknown_selection(
    tmp_path: Path,
    selected_run_ids: tuple[str, ...],
    message: str,
) -> None:
    service = _service(tmp_path)
    _, run = _run(service, tmp_path, "PA11-H", "only")
    service.upsert_working_run(run)

    with pytest.raises(ValueError, match=message):
        service.freeze_working_evidence(
            package_id="selected-evidence",
            selected_run_ids=selected_run_ids,
        )


class _ScopedWorkflow:
    """Small public-contract fake used to inspect checkpoint selection."""

    def __init__(self, *, include_task_run: bool = True) -> None:
        self.run_count = 0
        self.working_run_ids = {"foreign-task-run"}
        self.include_task_run = include_task_run
        self.freeze_calls: list[dict[str, object]] = []

    def inspect(self, paths):
        return SimpleNamespace(graph_hash="graph-1", artifacts=())

    def run(self, request):
        self.run_count += 1
        return SimpleNamespace(
            run_id=f"task-run-{self.run_count}",
            status="review_required",
            reason_codes=(),
            manifest_path=None,
        )

    def upsert_working_run(self, run):
        if self.include_task_run:
            self.working_run_ids.add(str(run.run_id))

    def working_evidence_status(self):
        return SimpleNamespace(run_ids=tuple(sorted(self.working_run_ids)))

    def freeze_working_evidence(self, **kwargs):
        self.freeze_calls.append(dict(kwargs))
        return SimpleNamespace(path=Path("selected-package"), package_hash="hash")


def _ready_loop(tmp_path: Path, workflow: _ScopedWorkflow) -> ResearchLoopService:
    loop = ResearchLoopService.open(tmp_path, project_service=workflow)
    task = loop.create_task(
        task_id="scoped-task",
        project_id="demo",
        research_question="q",
    )
    loop.propose_mapping(task.task_id, {"raw/a.csv": {"sample_id": "A"}})
    loop.confirm_mapping(task.task_id, approved=True, approver="user")
    loop.run(task.task_id)
    return loop


def test_checkpoint_freezes_only_current_task_runs_not_other_task_runs(tmp_path: Path) -> None:
    workflow = _ScopedWorkflow()
    loop = _ready_loop(tmp_path, workflow)

    loop.checkpoint("scoped-task")

    assert workflow.freeze_calls
    assert workflow.freeze_calls[-1]["selected_run_ids"] == ("task-run-1",)
    assert "foreign-task-run" not in workflow.freeze_calls[-1]["selected_run_ids"]


def test_checkpoint_fails_closed_when_no_current_task_run_remains(tmp_path: Path) -> None:
    workflow = _ScopedWorkflow(include_task_run=False)
    loop = _ready_loop(tmp_path, workflow)

    with pytest.raises(ValueError, match="current task run"):
        loop.checkpoint("scoped-task")

    assert workflow.freeze_calls == []
