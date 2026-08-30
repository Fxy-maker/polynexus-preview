from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from polynexus.core.engine import AnalysisResult
from polynexus.core.agent_workflow import AgentWorkflowService
from polynexus.core.project_workflow import (
    ProjectWorkflowService,
    WorkingEvidenceIndex,
)
from polynexus.core.project_workflow.models import AnalysisRequest


def _run(tmp_path: Path, question: str, *, write_source: bool = True):
    source = tmp_path / "raw" / "NMR" / "PA11-H.csv"
    source.parent.mkdir(parents=True, exist_ok=True)
    if write_source:
        source.write_text("ppm,intensity\n1.0,2\n1.5,3\n", encoding="utf-8")
    service = ProjectWorkflowService.open(tmp_path)
    service.agent_service = AgentWorkflowService(
        provider_runner=lambda step, artifact, output: AnalysisResult(
            technique=step.technique, validation_passed=True
        )
    )
    request = AnalysisRequest.create(
        question=question,
        data_scope=(source.relative_to(tmp_path).as_posix(),),
        parameters={"submodule_id": "nmr.liquid_h"},
    )
    return service, service.run(request)


def test_working_evidence_upsert_replaces_same_source_and_reports_status(tmp_path: Path) -> None:
    service, first = _run(tmp_path, "first")
    service.upsert_working_run(first)
    assert service.working_evidence_status().to_dict()["total"] == 1

    _, second = _run(tmp_path, "second")
    service.upsert_working_run(second)
    status = service.working_evidence_status()
    assert status.total == 1
    assert status.run_ids == (second.run_id,)
    assert status.techniques == ("nmr",)


def test_working_evidence_replaces_same_path_after_source_content_changes(tmp_path: Path) -> None:
    service, first = _run(tmp_path, "first")
    first_entry = service.upsert_working_run(first)
    second_entry = replace(
        first_entry,
        run_id="run-after-content-change",
        source_artifact_ids=("artifact-after-content-change",),
        source_hashes=("hash-after-content-change",),
    )
    index = WorkingEvidenceIndex((first_entry,))
    index.upsert(second_entry)
    status = index.status()
    assert status.total == 1
    assert status.run_ids == (second_entry.run_id,)


def test_freeze_working_evidence_creates_immutable_package_on_demand(tmp_path: Path) -> None:
    service, run = _run(tmp_path, "freeze")
    service.upsert_working_run(run)
    assert not (tmp_path / ".polynexus" / "evidence" / "research-evidence-v001").exists()
    package = service.freeze_working_evidence(package_id="research-evidence")
    assert package.status == "review_required"
    assert package.path.name == "research-evidence-v001"
    assert (package.path / "manifest.json").is_file()


def test_freeze_rejects_tampered_working_entry(tmp_path: Path) -> None:
    service, run = _run(tmp_path, "tamper")
    service.upsert_working_run(run)
    working_path = tmp_path / ".polynexus" / "evidence" / "working.json"
    payload = json.loads(working_path.read_text(encoding="utf-8"))
    payload["entries"][0]["source_hashes"] = ["tampered"]
    working_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="does not match"):
        service.freeze_working_evidence(package_id="research-evidence")
