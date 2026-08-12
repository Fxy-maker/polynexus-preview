from __future__ import annotations

from pathlib import Path

from polynexus.core.project_workflow.models import AnalysisRequest
from polynexus.core.project_workflow.service import ProjectWorkflowService


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
