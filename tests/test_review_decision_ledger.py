from __future__ import annotations

import json
from pathlib import Path

from polynexus.core.agent_workflow import AgentWorkflowService
from polynexus.core.engine import AnalysisResult
from polynexus.core.project_workflow import ProjectWorkflowService


def test_package_writes_pending_review_decision_ledger_for_ars(tmp_path: Path) -> None:
    source = tmp_path / "raw" / "IR" / "sample.csv"
    source.parent.mkdir(parents=True)
    source.write_text(
        "XLabel,Wavenumber\nYLabel,Absorbance\n1000,1\n900,2\n",
        encoding="utf-8",
    )
    service = ProjectWorkflowService.open(tmp_path)
    service.agent_service = AgentWorkflowService(
        provider_runner=lambda step, artifact, output: AnalysisResult(
            technique=step.technique,
            validation_passed=True,
        )
    )

    summary = service.analyze_project(
        question="Prepare reviewable IR evidence",
        data_scope=(source.relative_to(tmp_path).as_posix(),),
    )

    package_path = Path(summary.package["path"])
    ledger = json.loads((package_path / "review-decision.json").read_text(encoding="utf-8"))
    ars = json.loads((package_path / "ars-writing-input.json").read_text(encoding="utf-8"))
    evidence = json.loads((package_path / "evidence.json").read_text(encoding="utf-8"))["items"]
    assert ledger["version"] == 1
    assert ledger["status"] == "pending"
    assert ledger["decisions"]
    assert all(item["decision"] == "pending" for item in ledger["decisions"])
    assert {item["evidence_id"] for item in ledger["decisions"]} <= {
        item["evidence_id"] for item in evidence
    }
    assert ars["review_decisions"] == "review-decision.json"
    assert ars["review_status"] == "pending"
