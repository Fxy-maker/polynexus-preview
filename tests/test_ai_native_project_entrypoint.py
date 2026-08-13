from __future__ import annotations

from pathlib import Path

from polynexus.core.agent_workflow import AgentWorkflowService
from polynexus.core.engine import AnalysisResult
from polynexus.core.project_workflow import ProjectWorkflowService
from polynexus.cli.parser import build_parser
from polynexus.cli.run_project_workflow_service import run_project_workflow
import json


def _source(root: Path, technique: str, name: str) -> Path:
    path = root / "raw" / technique.upper() / name
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "XLabel,Wavenumber\nYLabel,Absorbance\n1000,1\n900,2\n" if technique == "ir" else "q,I\n0.1,1\n0.2,2\n"
    path.write_text(content, encoding="utf-8")
    return path


def test_analyze_project_is_one_call_with_three_status_layers(tmp_path: Path) -> None:
    _source(tmp_path, "waxs", "a.dat")
    _source(tmp_path, "waxs", "b.dat")

    service = ProjectWorkflowService.open(tmp_path)
    service.agent_service = AgentWorkflowService(
        provider_runner=lambda step, artifact, output: AnalysisResult(
            technique=step.technique,
            validation_passed=True,
        )
    )
    summary = service.analyze_project(question="Compare the PA6 WAXS sequence")

    payload = summary.to_dict()
    assert payload["computation"] == "passed"
    assert payload["data_quality"] == "warning"
    assert payload["publication"] == "review_required"
    assert payload["package"]["path"]
    assert payload["evidence_count"] == 2
    assert payload["runs"]


def test_analyze_project_packages_explicit_cross_technique_evidence_index(tmp_path: Path) -> None:
    ir = _source(tmp_path, "ir", "PA6-JW-180.csv")
    ir.write_text("XLabel,Wavenumber\nYLabel,Absorbance\n1000,1\n900,2\n", encoding="utf-8")
    waxs = _source(tmp_path, "waxs", "PA6.raw")
    calls: list[str] = []

    service = ProjectWorkflowService.open(tmp_path)
    service.agent_service = AgentWorkflowService(
        provider_runner=lambda step, artifact, output: (
            calls.append(step.technique)
            or AnalysisResult(technique=step.technique, validation_passed=True)
        )
    )
    summary = service.analyze_project(
        question="Prepare cross-technique PA6 evidence",
        data_scope=(ir.relative_to(tmp_path).as_posix(), waxs.relative_to(tmp_path).as_posix()),
    )

    assert summary.computation == "passed"
    assert calls == ["ir", "waxs"]
    package_path = Path(summary.to_dict()["package"]["path"])
    index = json.loads((package_path / "techniques.json").read_text(encoding="utf-8"))
    assert set(index["techniques"]) == {"ir", "waxs"}
    assert all(value["run_ids"] for value in index["techniques"].values())
    assert index["techniques"]["ir"]["evidence_count"] >= 1
    assert index["techniques"]["waxs"]["evidence_count"] == 1
    writing_evidence = json.loads((package_path / "writing-evidence.json").read_text(encoding="utf-8"))
    assert set(writing_evidence["techniques"]) == {"ir", "waxs"}
    assert all(group["evidence"] for group in writing_evidence["techniques"].values())
    assert all(item["source_runs"] for group in writing_evidence["techniques"].values() for item in group["evidence"])


def test_analyze_project_reports_actionable_blocker_without_fake_package(tmp_path: Path) -> None:
    service = ProjectWorkflowService.open(tmp_path)
    summary = service.analyze_project(question="Analyze the project")

    payload = summary.to_dict()
    assert payload["computation"] == "blocked"
    assert payload["publication"] == "blocked"
    assert payload["package"] is None
    assert payload["reason_codes"]
    assert payload["messages"]


def test_analyze_project_cli_emits_single_ai_facing_envelope(capsys, tmp_path: Path) -> None:
    _source(tmp_path, "waxs", "sample.dat")
    args = build_parser().parse_args([
        "project-workflow", "analyze-project", "--project-root", str(tmp_path),
        "--question", "Analyze this project",
    ])

    service = ProjectWorkflowService.open(tmp_path)
    service.agent_service = AgentWorkflowService(
        provider_runner=lambda step, artifact, output: AnalysisResult(technique=step.technique, validation_passed=True)
    )
    code = run_project_workflow(args, service=service)

    payload = __import__("json").loads(capsys.readouterr().out)
    assert code == 0
    assert payload["operation"] == "analyze-project"
    assert payload["analysis"]["computation"] == "passed"
    assert payload["analysis"]["publication"] == "review_required"


def test_analyze_project_discovers_ftir_from_file_header_without_ir_path(tmp_path: Path) -> None:
    source = _source(tmp_path, "samples", "PA6-JW-180.csv")
    source.write_text("XLabel,Wavenumber\nYLabel,Absorbance\n1000,1\n900,2\n", encoding="utf-8")
    summary = ProjectWorkflowService.open(tmp_path).analyze_project(question="Prepare FTIR evidence")

    payload = summary.to_dict()
    assert payload["computation"] == "passed"
    assert payload["evidence_count"] == 1


def test_analyze_project_skips_same_stem_spc_companion(tmp_path: Path) -> None:
    csv_path = _source(tmp_path, "samples", "PA6-JW-180.csv")
    csv_path.write_text("XLabel,Wavenumber\nYLabel,Absorbance\n1000,1\n900,2\n", encoding="utf-8")
    csv_path.with_suffix(".spc").write_bytes(b"instrument companion")
    summary = ProjectWorkflowService.open(tmp_path).analyze_project(question="Prepare FTIR evidence")

    payload = summary.to_dict()
    assert payload["evidence_count"] == 1
    assert "duplicate_format_skipped" in payload["reason_codes"]
