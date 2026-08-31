from types import SimpleNamespace

import pytest

from polynexus.cli.run_ai_tune_service import (
    _attach_compatibility_plan,
    _persist_ai_tune_run,
    run_ai_tune,
)


def _completed_state() -> dict[str, object]:
    return {
        "data_availability": "canonical",
        "computability": "computed",
        "validity": "not_assessed",
        "promotion": "diagnostic_only",
        "missing_inputs": [],
        "reason_codes": [],
        "preconditions": [],
        "next_actions": [],
    }


def test_run_ai_tune_writes_report_and_formats_progress(tmp_path, capsys):
    class FakeOrchestrator:
        init_kwargs = None

        def __init__(self, **kwargs):
            FakeOrchestrator.init_kwargs = kwargs

        def run(self):
            FakeOrchestrator.init_kwargs["progress_callback"](
                {
                    "round_num": 1,
                    "max_rounds": 3,
                    "before_r_squared": 0.1,
                    "after_r_squared": 0.2,
                    "changes": {"alpha": 1},
                    "status": "converged",
                }
            )
            return {
                "best_r_squared": 0.9,
                "baseline_r_squared": 0.8,
                "converged": True,
                "best_config": {"alpha": 1},
                "analysis_evidence": {"note": "ok"},
                "history": [{"round_num": 1, "accepted": True, "changes": {"alpha": 1}}],
            }

    def fake_persist(args, report, output_path):
        assert args.polymer == "PA6"
        assert output_path.exists()
        assert report["best_r_squared"] == 0.9
        assert report["analysis_plan"]["plan_id"] == report["analysis_plan_evaluation"]["plan_id"]
        assert report["analysis_plan"]["plan_hash"] == report["analysis_plan_evaluation"]["plan_hash"]
        assert report["analysis_plan_evaluation"]["candidates"][0]["status"] == "stable"
        return "run-42"

    report_path = tmp_path / "ai_tune_report.json"
    data_file = tmp_path / "sample.dat"
    data_file.write_text("data", encoding="utf-8")
    args = SimpleNamespace(
        technique="waxs",
        file=str(data_file),
        polymer="PA6",
        rounds=3,
        submodule=None,
        output=str(report_path),
    )

    assert (
        run_ai_tune(
            args,
            parameter_orchestrator_cls=FakeOrchestrator,
            persist_ai_tune_run_fn=fake_persist,
        )
        == 0
    )

    captured = capsys.readouterr()
    assert "[Round 1/3] r2 0.100 -> 0.200 changes: {alpha: 1} converged" in captured.out
    assert "Analysis run: run-42" in captured.out
    assert "Report:" in captured.out
    assert report_path.exists()


def test_run_ai_tune_reports_engine_errors(tmp_path, capsys):
    class BoomOrchestrator:
        def __init__(self, **kwargs):
            pass

        def run(self):
            raise RuntimeError("boom")

    args = SimpleNamespace(
        technique="waxs",
        file=str(tmp_path / "sample.dat"),
        polymer="PA6",
        rounds=3,
        submodule=None,
        output=str(tmp_path / "ai_tune_report.json"),
    )

    assert run_ai_tune(args, parameter_orchestrator_cls=BoomOrchestrator) == 1
    captured = capsys.readouterr()
    assert "AI tune engine error: boom" in captured.err


def test_ai_tune_plan_reuses_shared_compute_template(tmp_path) -> None:
    source = tmp_path / "sample.csv"
    source.write_text("x,y\n1,2\n", encoding="utf-8")
    args = SimpleNamespace(
        technique="waxs",
        file=str(source),
        polymer="PA6",
    )
    report = {
        "baseline_config": {},
        "best_config": {},
        "compute_run": {
            "status": "completed",
            "computation_state": _completed_state(),
            "canonical_template": {
                "template_id": "scattering_1d.v1",
                "source_artifact_id": "artifact-1",
                "content_hash": "template-hash",
                "conversion_record": {
                    "conversion_id": "generic.one-dimensional.v1",
                    "conversion_hash": "conversion-hash",
                },
            },
        },
    }

    _attach_compatibility_plan(args, report)

    assert report["analysis_plan"]["canonical_template"] == {
        "template_id": "scattering_1d.v1",
        "conversion_version": "generic.one-dimensional.v1",
        "source_artifact_id": "artifact-1",
        "content_hash": "template-hash",
        "conversion_hash": "conversion-hash",
    }


def test_ai_tune_does_not_fallback_when_present_compute_run_is_malformed(tmp_path) -> None:
    source = tmp_path / "sample.csv"
    source.write_text("x,y\n1,2\n", encoding="utf-8")
    args = SimpleNamespace(
        technique="waxs",
        file=str(source),
        polymer="PA6",
    )
    report = {
        "baseline_config": {},
        "best_config": {},
        "compute_run": {
            "status": "completed",
            "computation_state": _completed_state(),
            "canonical_template": {"template_id": "scattering_1d.v1"},
        },
    }

    with pytest.raises(ValueError, match="compute_run projection is invalid"):
        _attach_compatibility_plan(args, report)

    assert "analysis_plan" not in report


def test_ai_tune_does_not_fallback_when_present_compute_run_lacks_template(tmp_path) -> None:
    source = tmp_path / "sample.csv"
    source.write_text("x,y\n1,2\n", encoding="utf-8")
    args = SimpleNamespace(
        technique="waxs",
        file=str(source),
        polymer="PA6",
    )
    report = {
        "baseline_config": {},
        "best_config": {},
        "compute_run": {
            "status": "completed",
            "computation_state": _completed_state(),
        },
    }

    with pytest.raises(ValueError, match="canonical_template"):
        _attach_compatibility_plan(args, report)

    assert "analysis_plan" not in report


def test_persist_ai_tune_run_keeps_shared_compute_run_projection(tmp_path, monkeypatch):
    captured = {}

    class _DB:
        def __init__(self):
            pass

        def create_sample(self, *args, **kwargs):
            return "sample-1"

        def create_batch(self, *args, **kwargs):
            return "batch-1"

        def add_data_file(self, *args, **kwargs):
            return None

        def create_analysis_run(self, *args, **kwargs):
            captured["summary"] = kwargs["results_summary"]
            return "run-1"

        def close(self):
            pass

    monkeypatch.setattr("polynexus.data.sample_db.SampleDB", _DB)
    source = tmp_path / "sample.dat"
    source.write_text("data", encoding="utf-8")
    args = SimpleNamespace(
        technique="waxs",
        file=str(source),
        polymer="PA6",
        rounds=1,
        submodule=None,
    )
    report = {
        "best_config": {},
        "compute_run": {
            "status": "completed",
            "computation_state": _completed_state(),
            "canonical_template": {"template_id": "scattering_1d.v1"},
        },
    }

    assert _persist_ai_tune_run(args, report, tmp_path / "report.json") == "run-1"
    assert captured["summary"]["compute_run"]["canonical_template"]["template_id"] == "scattering_1d.v1"


def test_persist_ai_tune_run_rejects_malformed_present_compute_run(tmp_path, monkeypatch):
    class _DB:
        def __init__(self):
            raise AssertionError("malformed reports must fail before opening the database")

    monkeypatch.setattr("polynexus.data.sample_db.SampleDB", _DB)
    source = tmp_path / "sample.dat"
    source.write_text("data", encoding="utf-8")
    args = SimpleNamespace(
        technique="waxs",
        file=str(source),
        polymer="PA6",
        rounds=1,
        submodule=None,
    )
    report = {
        "best_config": {},
        "compute_run": {"status": "completed"},
    }

    with pytest.raises(ValueError, match="compute_run projection is invalid"):
        _persist_ai_tune_run(args, report, tmp_path / "report.json")


def test_persist_ai_tune_run_omits_absent_compute_run_key(tmp_path, monkeypatch):
    captured = {}

    class _DB:
        def __init__(self):
            pass

        def create_sample(self, *args, **kwargs):
            return "sample-1"

        def create_batch(self, *args, **kwargs):
            return "batch-1"

        def add_data_file(self, *args, **kwargs):
            return None

        def create_analysis_run(self, *args, **kwargs):
            captured["summary"] = kwargs["results_summary"]
            return "run-1"

        def close(self):
            pass

    monkeypatch.setattr("polynexus.data.sample_db.SampleDB", _DB)
    source = tmp_path / "sample.dat"
    source.write_text("data", encoding="utf-8")
    args = SimpleNamespace(
        technique="waxs",
        file=str(source),
        polymer="PA6",
        rounds=1,
        submodule=None,
    )

    assert _persist_ai_tune_run(args, {"best_config": {}}, tmp_path / "report.json") == "run-1"
    assert "compute_run" not in captured["summary"]
