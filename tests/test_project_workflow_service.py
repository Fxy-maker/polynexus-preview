from __future__ import annotations

from pathlib import Path

from polynexus.core.project_workflow.models import AnalysisRequest
from polynexus.core.project_workflow.service import ProjectWorkflowService


def _write_mettler_fixture(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = ["Sample Weight: 5.95 mg"]
    index = 0
    for setpoint, duration in ((255.0, 70), (180.0, 80), (255.0, 70), (181.0, 85)):
        for second in range(duration + 1):
            sample_temperature = setpoint + 0.05 if setpoint < 200 else setpoint + 0.02
            heat_flow = 1.0 + (20.0 / (second + 5) if setpoint < 200 else 0.0)
            rows.append(
                f"{index} {index} {sample_temperature:.3f} {setpoint:.3f} {heat_flow:.6f}"
            )
            index += 1
    path.write_text("\n".join(rows), encoding="utf-8")
    return path


def test_plan_resolves_dsc_request_without_requiring_batch_metadata(tmp_path: Path) -> None:
    service = ProjectWorkflowService.open(tmp_path)
    request = AnalysisRequest.create(
        question="Compare PA6 kinetics",
        requested_outputs=("avrami_parameter_table",),
        data_scope=("raw/DSC-isothermal",),
    )

    plan = service.plan(request)

    assert plan.status in {"ready", "review_required"}
    assert plan.required_context == ()
    assert plan.reason_codes == ()
    assert plan.steps
    assert plan.steps[0]["technique"] == "dsc"


def test_plan_reports_missing_converter_as_blocker_without_fabrication(tmp_path: Path) -> None:
    service = ProjectWorkflowService.open(tmp_path)
    request = AnalysisRequest.create(
        question="Analyze WAXS",
        requested_outputs=("waxs_profile_figure",),
        data_scope=("raw/WAXS",),
    )

    plan = service.plan(request)

    assert plan.status == "blocked"
    assert "converter_unregistered" in plan.reason_codes
    assert all(step["technique"] != "waxs" or step["status"] == "blocked" for step in plan.steps)


def test_run_dsc_request_writes_derived_outputs_only(tmp_path: Path) -> None:
    source = _write_mettler_fixture(tmp_path / "raw" / "PA6-DWJJ.txt")
    service = ProjectWorkflowService.open(tmp_path)
    request = AnalysisRequest.create(
        question="Compare PA6 kinetics",
        requested_outputs=("avrami_parameter_table",),
        data_scope=(str(source.relative_to(tmp_path)),),
    )

    result = service.run(request)

    assert result.status == "review_required"
    assert source.exists()
    assert result.outputs
    assert all(Path(path).is_relative_to(tmp_path / ".polynexus") for path in result.outputs)
