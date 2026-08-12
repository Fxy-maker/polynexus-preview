from __future__ import annotations

from pathlib import Path
import json

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
    assert "artifact_missing" in plan.reason_codes
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


def test_plan_blocks_explicit_scope_outside_project(tmp_path: Path) -> None:
    service = ProjectWorkflowService.open(tmp_path)
    request = AnalysisRequest.create(
        question="Analyze DSC",
        data_scope=(str((tmp_path.parent / "outside.txt").resolve()),),
    )

    plan = service.plan(request)

    assert plan.status == "blocked"
    assert "scope_outside_project" in plan.reason_codes


def test_plan_blocks_parent_scope_and_missing_scope_after_index(tmp_path: Path) -> None:
    source = _write_mettler_fixture(tmp_path / "raw" / "PA6-DWJJ.txt")
    service = ProjectWorkflowService.open(tmp_path)
    service.inspect((source,))

    for scope, expected in (("../raw", "scope_outside_project"), ("raw/missing.txt", "scope_not_indexed")):
        request = AnalysisRequest.create(question="Analyze DSC", data_scope=(scope,))
        plan = service.plan(request)
        assert plan.status == "blocked"
        assert expected in plan.reason_codes


def test_plan_fails_closed_on_tampered_inventory(tmp_path: Path) -> None:
    source = _write_mettler_fixture(tmp_path / "raw" / "PA6-DWJJ.txt")
    service = ProjectWorkflowService.open(tmp_path)
    service.inspect((source,))
    index_path = tmp_path / ".polynexus" / "inventory" / "index.json"
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    payload["artifacts"][0]["sha256"] = "tampered"
    index_path.write_text(json.dumps(payload), encoding="utf-8")

    plan = service.plan(AnalysisRequest.create(question="Analyze DSC", data_scope=("raw",)))

    assert plan.status == "blocked"
    assert "inventory_invalid" in plan.reason_codes


def test_run_rejects_supplied_plan_that_differs_from_persisted_plan(tmp_path: Path) -> None:
    source = _write_mettler_fixture(tmp_path / "raw" / "PA6-DWJJ.txt")
    service = ProjectWorkflowService.open(tmp_path)
    request = AnalysisRequest.create(
        question="Compare PA6 kinetics",
        data_scope=(str(source.relative_to(tmp_path)),),
    )
    persisted = service.plan(request)
    supplied = type(persisted).create(
        request_hash=persisted.request_hash,
        steps=persisted.steps,
        status="blocked",
        reason_codes=("tampered",),
        required_context=persisted.required_context,
    )

    result = service.run(supplied)

    assert result.status == "blocked"
    assert "plan_manifest_mismatch" in result.reason_codes


def test_run_projects_provider_limits_into_evidence(tmp_path: Path) -> None:
    source = _write_mettler_fixture(tmp_path / "raw" / "PA6-DWJJ.txt")
    service = ProjectWorkflowService.open(tmp_path)
    request = AnalysisRequest.create(
        question="Compare PA6 kinetics",
        data_scope=(str(source.relative_to(tmp_path)),),
    )

    result = service.run(request)

    assert result.evidence_items
    assert any(
        "unique_hydrogen_bond_species" in item.disallowed_conclusions
        for item in result.evidence_items
    )
