from types import SimpleNamespace

from polynexus.cli.parser import parse_args
from polynexus.cli.run_project_workflow_service import run_analysis_plan_evaluation
from polynexus.core.project_workflow import AnalysisPlan, AnalysisPlanEvaluation, CandidateEvaluation
from polynexus.core.project_workflow.analysis_plan_evaluation import project_analysis_plan_evaluation
from polynexus.core.project_workflow.ars_handoff import analysis_plan_evaluation_for_ars
from polynexus.gui.analysis_plan_view_service import analysis_plan_evaluation_view, analysis_plan_evaluation_context


def _plan():
    return AnalysisPlan.create(
        source_files=({"path": "raw/sample.csv", "sha256": "a" * 64, "byte_size": 4, "source_order": 0},),
        canonical_template={"template_id": "ir.canonical", "conversion_version": "1"},
        algorithm={"algorithm_id": "ir.standard", "algorithm_version": "2"},
        analysis_intent="compare baseline stability",
        replay={"status": "frozen", "source_manifest_hash": "manifest-1", "replayed_from_run_id": "run-7"},
    )


def _evaluation(plan):
    return AnalysisPlanEvaluation.create(
        plan_id=plan.plan_id,
        plan_hash=plan.plan_hash,
        plan_version=plan.plan_version,
        candidates=(CandidateEvaluation("base", "stable", 0.2, ("peak_area",)),),
        review_limits=("human_scientific_review",),
    )


def test_gui_cli_and_ars_projection_share_plan_identity_and_review_boundary():
    plan = _plan()
    evaluation = _evaluation(plan)

    projection = project_analysis_plan_evaluation(plan, evaluation)
    assert analysis_plan_evaluation_view(projection) == projection
    assert analysis_plan_evaluation_for_ars(plan, evaluation) == projection
    assert projection["plan_id"] == plan.plan_id
    assert projection["plan_hash"] == plan.plan_hash
    assert projection["candidates"][0]["status"] == "stable"
    assert projection["review_limits"] == ["human_scientific_review"]
    assert projection["replay"] == dict(plan.replay)


def test_evaluate_analysis_plans_cli_emits_shared_projection(tmp_path, capsys):
    plan = _plan()
    evaluation = _evaluation(plan)
    plan_path = tmp_path / "plan.json"
    evaluation_path = tmp_path / "evaluation.json"
    plan_path.write_text(__import__("json").dumps(plan.to_dict()), encoding="utf-8")
    evaluation_path.write_text(__import__("json").dumps(evaluation.to_dict()), encoding="utf-8")

    args = SimpleNamespace(plan=str(plan_path), evaluation=str(evaluation_path))
    assert run_analysis_plan_evaluation(args) == 0
    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["analysis_plan_evaluation"] == project_analysis_plan_evaluation(plan, evaluation)


def test_cli_parser_exposes_shared_evaluation_route():
    args = parse_args(["evaluate-analysis-plans", "--plan", "plan.json", "--evaluation", "evaluation.json"])
    assert args.cmd == "evaluate-analysis-plans"
    assert args.plan == "plan.json"


def test_gui_context_keeps_the_shared_projection_without_legacy_inference():
    plan = _plan()
    projection = project_analysis_plan_evaluation(plan, _evaluation(plan))
    context = analysis_plan_evaluation_context({"analysis_plan_evaluation": projection, "best_r_squared": 0.99})
    assert context == {"analysis_plan_evaluation": projection}
