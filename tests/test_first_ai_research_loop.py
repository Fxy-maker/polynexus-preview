from __future__ import annotations

import json
from pathlib import Path
import shutil

from polynexus.cli.parser import build_parser
from polynexus.cli.run_project_workflow_service import run_project_workflow
from polynexus.core.agent_workflow import AgentWorkflowService
from polynexus.core.engine import AnalysisResult
from polynexus.core.project_workflow import ProjectWorkflowService


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "first_ai_loop"


def copy_fixture(destination: Path, *, include_nmr: bool = False) -> Path:
    shutil.copytree(FIXTURE_ROOT, destination)
    if include_nmr:
        nmr = destination / "raw" / "NMR" / "PA6-JW-180.csv"
        nmr.parent.mkdir(parents=True)
        nmr.write_text("ppm,intensity\n1.0,2.0\n1.5,3.0\n", encoding="utf-8")
    return destination


def selected_paths(root: Path, techniques: set[str] | None = None) -> tuple[str, ...]:
    return tuple(
        str(path.relative_to(root).as_posix())
        for path in sorted((root / "raw").glob("*/*"))
        if path.is_file() and (techniques is None or path.parent.name.lower() in techniques)
    )


def fake_service(root: Path) -> ProjectWorkflowService:
    service = ProjectWorkflowService.open(root)

    def provider_runner(step, _artifact, _output_dir):
        # The fixture intentionally supplies no scientific values.  The real
        # AgentWorkflowService still builds the canonical ComputeRun envelope
        # consumed by project evidence and manuscript projections.
        return AnalysisResult(
            technique=step.technique,
            validation_passed=True,
            parameters={"fixture_metric": 1.0},
            metadata={
                "units": {"fixture_metric": "a.u."},
                "methods": {"fixture_metric": "public_fixture"},
            },
        )

    service.agent_service = AgentWorkflowService(provider_runner=provider_runner)
    return service


def test_close_loop_emits_package_writing_input_and_draft(tmp_path: Path, capsys) -> None:
    fixture = copy_fixture(tmp_path / "project")
    service = fake_service(fixture)
    args = build_parser().parse_args([
        "project-workflow", "close-loop",
        "--project-root", str(fixture),
        "--paths", *selected_paths(fixture, {"dsc", "ir", "saxs", "waxs"}),
        "--question", "Compare the thermal and structural response of PA6 JW.",
        "--package-id", "first-loop-fixture",
    ])

    code = run_project_workflow(args, service=service)
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["operation"] == "close-loop"
    assert payload["analysis"]["package"]["path"]
    assert payload["analysis"]["writing_input"]["package_id"] == "first-loop-fixture"
    assert payload["analysis"]["manuscript"]["package_id"] == "first-loop-fixture"
    analysis = payload["analysis"]
    package_path = Path(analysis["package"]["path"])
    package_manifest = json.loads((package_path / "manifest.json").read_text(encoding="utf-8"))
    assert package_manifest["run_ids"] == [run["run_id"] for run in analysis["runs"]]
    assert analysis["writing_input"]["projection"]["package"]["package_id"] == "first-loop-fixture"

    metric_ids = {
        item["metric_id"]
        for item in analysis["writing_input"]["projection"]["metrics"]
    }
    for claim in analysis["manuscript"]["claims"]:
        assert set(claim["metric_ids"]).issubset(metric_ids)
    assert all(
        table["rows"][0]["source"]
        for table in analysis["result_tables"]
    )


def test_close_loop_keeps_missing_technique_explicit(tmp_path: Path) -> None:
    fixture = copy_fixture(tmp_path / "project", include_nmr=False)
    summary = fake_service(fixture).close_first_loop(
        question="Prepare mixed evidence",
        data_scope=selected_paths(fixture, {"dsc", "ir", "saxs", "waxs"}),
    )

    assert summary.package is not None
    assert "nmr" in summary.missing_techniques
    assert summary.to_dict()["missing_techniques"] == ["nmr"]


def test_close_loop_does_not_create_package_without_source_data(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    summary = ProjectWorkflowService.open(empty).close_first_loop(
        question="Prepare evidence",
        data_scope=(),
    )

    assert summary.package is None
    assert summary.computation == "blocked"
