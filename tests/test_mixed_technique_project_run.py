from __future__ import annotations

import json
from pathlib import Path

from polynexus.core.agent_workflow import AgentWorkflowService
from polynexus.core.engine import AnalysisResult
from polynexus.core.project_workflow import ProjectWorkflowService


def _write(root: Path, technique: str, name: str) -> Path:
    path = root / "raw" / technique.upper() / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if technique == "ir":
        path.write_text(
            "XLabel,Wavenumber\nYLabel,Absorbance\n1000,1\n900,2\n",
            encoding="utf-8",
        )
    elif technique == "nmr":
        path.write_text("ppm,intensity\n1.0,2\n1.5,3\n", encoding="utf-8")
    else:
        path.write_text("q,I\n0.1,1\n0.2,2\n", encoding="utf-8")
    return path


def test_mixed_project_request_produces_one_composite_run(tmp_path: Path) -> None:
    ir = _write(tmp_path, "ir", "sample-ir.csv")
    waxs = _write(tmp_path, "waxs", "sample-waxs.dat")
    calls: list[str] = []
    service = ProjectWorkflowService.open(tmp_path)
    service.agent_service = AgentWorkflowService(
        provider_runner=lambda step, artifact, output: (
            calls.append(step.technique)
            or AnalysisResult(technique=step.technique, validation_passed=True)
        )
    )

    summary = service.analyze_project(
        question="Prepare cross-technique evidence",
        data_scope=(
            ir.relative_to(tmp_path).as_posix(),
            waxs.relative_to(tmp_path).as_posix(),
        ),
    )

    assert summary.computation == "passed"
    assert len(summary.runs) == 1
    run = summary.runs[0]
    assert {step.technique for step in run.analysis_run.steps} == {"ir", "waxs"}
    assert calls == ["ir", "waxs"]
    package_path = Path(summary.package["path"])
    manifest = json.loads((package_path / "relations.json").read_text(encoding="utf-8"))
    assert any(item["type"] == "cross_technique_evidence_set" for item in manifest["relations"])


def test_mixed_project_request_preserves_explicit_nmr_submodule(tmp_path: Path) -> None:
    nmr = _write(tmp_path, "nmr", "liquid-h.csv")
    waxs = _write(tmp_path, "waxs", "sample-waxs.dat")
    calls: list[str] = []
    service = ProjectWorkflowService.open(tmp_path)
    service.agent_service = AgentWorkflowService(
        provider_runner=lambda step, artifact, output: (
            calls.append(str(step.parameters.get("submodule_id", "")))
            or AnalysisResult(technique=step.technique, validation_passed=True)
        )
    )

    summary = service.analyze_project(
        question="Prepare NMR and WAXS evidence",
        data_scope=(nmr.relative_to(tmp_path).as_posix(), waxs.relative_to(tmp_path).as_posix()),
        nmr_submodule="nmr.liquid_h",
    )

    assert summary.computation == "passed"
    assert calls == ["nmr.liquid_h", "waxs.static"]
