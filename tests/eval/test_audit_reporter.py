from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

from tests.eval.audit_reporter import AuditReporter
from tests.eval.models import EvalCase, EvalResult, GroundTruth
from tests.eval.runner import EvalRunner
from tests.eval.synth_generator import SynthGenerator


def _local_tmp_dir() -> Path:
    root = Path(__file__).resolve().parent / "_tmp"
    path = root / uuid.uuid4().hex
    path.mkdir(parents=True)
    return path


def _reporter(eval_root: Path, project_root: Path) -> AuditReporter:
    return AuditReporter(EvalRunner(eval_root=eval_root, project_root=project_root))


def _write_case(path: Path, *, case_id: str = "real_case", data_file: str = "sample.xy") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "case_id": case_id,
        "technique": "waxs",
        "submodule": "static",
        "data_file": data_file,
        "polymer_name": "PA6",
        "polymer_phase": "alpha",
        "config_overrides": {"polymer_type": "PA6_alpha"},
        "ground_truth": {"Xc_pct": [40.0, 50.0], "peak_centers": [[19.8, 20.2]]},
        "source": "expert_review",
        "notes": "test case",
        "existing_field": "keep me",
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_batch_run_returns_eval_results() -> None:
    tmp_dir = _local_tmp_dir()
    try:
        eval_root = tmp_dir / "eval"
        SynthGenerator(output_dir=eval_root, seed=42).generate_all()
        reporter = _reporter(eval_root, tmp_dir)

        results = reporter.batch_run(str(eval_root / "cases"), str(eval_root / "reports"))

        assert len(results) == len(SynthGenerator.CASE_IDS)
        assert all(isinstance(result, EvalResult) for result in results)
        assert reporter.last_results_path is not None
        assert reporter.last_results_path.exists()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_generate_report_outputs_html() -> None:
    tmp_dir = _local_tmp_dir()
    try:
        eval_root = tmp_dir / "eval"
        SynthGenerator(output_dir=eval_root, seed=42).generate_all()
        reporter = _reporter(eval_root, tmp_dir)
        results = reporter.batch_run(str(eval_root / "cases"), str(eval_root / "reports"))
        report_path = eval_root / "reports" / "report.html"

        returned = reporter.generate_report(results, reporter.last_cases, str(report_path))
        html = Path(returned).read_text(encoding="utf-8")

        assert "<html" in html
        assert "Ground Truth" in html
        assert "Agent Output" in html
        assert "Benchmark" in html
        assert "Objective delta" in html
        assert "polynexus.audit.annotations" in html
        assert "Average composite" in html
        assert "Quality mix" in html
        assert "Boundary" in html
        assert "Evidence pack drives the result" in html
        assert "Final scientific judgment stays with the user." in html
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_generate_report_surfaces_temperature_2d_ir_section() -> None:
    tmp_dir = _local_tmp_dir()
    try:
        from polynexus.core.report import generate_report

        result = type(
            "IRTemp2DReportResult",
            (),
            {
                "label": "PA6 temperature sweep",
                "parameters": {
                    "n_peaks": 4,
                    "Xc_pct": 38.6,
                    "n_matches": 3,
                    "r_squared": 0.91,
                },
                "analysis_evidence": {
                    "feature_evidence": {
                        "temperature_2d_evidence": {
                            "sequence_axis_score": 0.88,
                            "matrix_quality_score": 0.81,
                            "cos_signal_score": 0.79,
                            "interpretation_ready": True,
                            "paper_conclusion_ready": True,
                        }
                    }
                },
            },
        )()

        html = generate_report(project_name="Eval", ir_results=[result])

        assert "IR Temperature 2D" in html
        assert "PA6 temperature sweep" in html
        assert "paper-ready" in html
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_generate_report_surfaces_dsc_section() -> None:
    tmp_dir = _local_tmp_dir()
    try:
        from polynexus.core.report import generate_report

        result = type(
            "DSCReportResult",
            (object,),
            {
                "label": "PA6 standard heating",
                "parameters": {
                    "Tg_C": 50.0,
                    "Tm_peak_C": 222.4,
                    "DHm_Jg": 33.8,
                    "Xc_pct": 11.9,
                    "quality_score": 0.85,
                },
            },
        )()

        html = generate_report(project_name="Eval", dsc_results=[result])

        assert "Differential Scanning Calorimetry" in html
        assert "PA6 standard heating" in html
        assert "222.4" in html
        assert "11.9" in html
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_write_annotations_updates_real_json_without_dropping_fields() -> None:
    tmp_dir = _local_tmp_dir()
    try:
        cases_dir = tmp_dir / "cases"
        target = cases_dir / "real" / "real_case.json"
        _write_case(target)
        reporter = AuditReporter()

        reporter.write_annotations({"real_case": "WARN"}, str(cases_dir))

        payload = json.loads(target.read_text(encoding="utf-8"))
        assert payload["human_annotation"] == "WARN"
        assert "annotated_at" in payload
        assert payload["existing_field"] == "keep me"
        assert payload["ground_truth"]["Xc_pct"] == [40.0, 50.0]
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_diff_marks_out_of_range_values_as_fail() -> None:
    tmp_dir = _local_tmp_dir()
    try:
        case = EvalCase(
            case_id="waxs_out_of_range",
            technique="waxs",
            submodule="static",
            data_file="synth:waxs_out_of_range",
            polymer_name="PA6",
            polymer_phase="alpha",
            config_overrides={},
            ground_truth=GroundTruth(Xc_pct=(40.0, 50.0)),
            source="synthetic",
            notes="out of range",
        )
        result = EvalResult(
            case_id=case.case_id,
            technique=case.technique,
            phys_score=1.0,
            peak_score=1.0,
            cross_score=None,
            human_score=None,
            composite=1.0,
            details={},
            parameters_used={},
            output_parameters={"Xc_pct": 55.0},
        )
        report_path = tmp_dir / "report.html"

        AuditReporter().generate_report([result], [case], str(report_path))

        html = report_path.read_text(encoding="utf-8")
        assert "Xc_pct" in html
        assert "55 ❌" in html
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_real_data_root_is_applied_to_relative_case_paths() -> None:
    tmp_dir = _local_tmp_dir()
    try:
        eval_root = tmp_dir / "eval"
        cases_dir = eval_root / "cases"
        _write_case(cases_dir / "real" / "real_case.json", data_file="waxs/sample.xy")
        reporter = _reporter(eval_root, tmp_dir)
        real_root = tmp_dir / "real_data"

        reporter.batch_run(str(cases_dir), str(eval_root / "reports"), real_data_root=str(real_root))

        expected = str((real_root / "waxs" / "sample.xy").resolve())
        assert reporter.last_cases[0].data_file == expected
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_results_bundle_includes_summary_block() -> None:
    tmp_dir = _local_tmp_dir()
    try:
        eval_root = tmp_dir / "eval"
        SynthGenerator(output_dir=eval_root, seed=42).generate_all()
        reporter = _reporter(eval_root, tmp_dir)

        reporter.batch_run(str(eval_root / "cases"), str(eval_root / "reports"))
        bundle = json.loads(reporter.last_results_path.read_text(encoding="utf-8"))

        assert "summary" in bundle
        assert "status_counts" in bundle["summary"]
        assert "average_composite" in bundle["summary"]
        assert "benchmark" in bundle["summary"]
        assert "constraint_hit_counts" in bundle["summary"]["benchmark"]
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_benchmark_summary_keeps_stage8_accuracy_signals_stable() -> None:
    reporter = AuditReporter()
    results = [
        EvalResult(
            case_id="case_1",
            technique="waxs",
            phys_score=0.92,
            peak_score=0.88,
            cross_score=None,
            human_score=None,
            composite=0.90,
            details={
                "benchmark": {
                    "accepted": True,
                    "symptom_hit": True,
                    "baseline": {"composite": 0.80},
                    "tuned": {"composite": 0.92},
                },
                "phys": {
                    "checks": [
                        {"name": "mask_truncated", "passed": True},
                        {"name": "beamstop_contamination", "passed": False},
                    ]
                },
            },
            parameters_used={},
            output_parameters={},
        ),
        EvalResult(
            case_id="case_2",
            technique="waxs",
            phys_score=0.83,
            peak_score=0.79,
            cross_score=None,
            human_score=None,
            composite=0.82,
            details={
                "benchmark": {
                    "objective_delta": -0.04,
                    "accepted": False,
                    "symptom_hit": False,
                    "rollback_reason": "quality_score_dropped",
                },
                "phys": {
                    "checks": [
                        {"name": "mask_truncated", "passed": True},
                    ]
                },
            },
            parameters_used={},
            output_parameters={},
        ),
    ]

    summary = reporter._benchmark_summary(results)

    assert summary["total_cases"] == 2
    assert round(summary["average_objective_delta"], 6) == 0.04
    assert summary["objective_gain_cases"] == 1
    assert summary["objective_loss_cases"] == 1
    assert summary["acceptance_rate"] == 0.5
    assert summary["rejection_rate"] == 0.5
    assert summary["rollback_reasons"]["quality_score_dropped"] == 1
    assert summary["constraint_hit_counts"] == {
        "passed_checks": 2,
        "failed_checks": 1,
        "total_checks": 3,
    }
    assert round(summary["constraint_hit_rate"], 6) == round(1 / 3, 6)
    assert summary["symptom_hit_counts"] == {"hit": 1, "miss": 1, "total": 2}
    assert summary["symptom_fix_rate"] == 0.5


def test_boundary_summary_exposes_role_split() -> None:
    reporter = AuditReporter()
    boundary = reporter._boundary_summary()

    assert boundary["core"].startswith("Evidence pack drives")
    assert boundary["AI"].startswith("AI only proposes")
    assert boundary["orchestrator"].startswith("Accept / rollback")
    assert boundary["user"].startswith("Final scientific judgment")
