from __future__ import annotations

import json
from pathlib import Path

from polynexus.core.agent_workflow import AgentWorkflowService
from polynexus.core.engine import AnalysisResult
from polynexus.core.project_workflow import ProjectWorkflowService


def test_project_package_cites_completed_canonical_capabilities(tmp_path: Path) -> None:
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
        question="Summarize this IR curve",
        data_scope=(source.relative_to(tmp_path).as_posix(),),
    )

    assert summary.computation == "passed"
    step = summary.runs[0].analysis_run.steps[0]
    capability_items = step.result_summary["capability_items"]
    assert capability_items
    assert all(item["status"] == "completed" for item in capability_items)
    package_path = Path(summary.package["path"])
    records = json.loads((package_path / "citation-metrics.json").read_text(encoding="utf-8"))["records"]
    capability_records = [record for record in records if record["method"].startswith("canonical.")]
    assert capability_records
    assert all(record["writing_eligibility"] == "diagnostic_only" for record in capability_records)
    assert all("capability_item_id" in record["source_locator"] for record in capability_records)
