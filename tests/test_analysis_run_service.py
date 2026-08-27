from polynexus.data.sample_db import SampleDB
from polynexus.gui.analysis_run_service import (
    AnalysisRunPersistenceContext,
    persist_analysis_run,
    persist_batch_analysis_runs,
)
from polynexus.core.saxs_engine.saxs_quality_contracts import MetricEvidenceSummary
from polynexus.core.compute import ComputeRunService


class _LegacyResult:
    def __init__(self):
        self.parameters = {"peak": 1.0}
        self.figures = {}
        self.metadata = {}


class _Engine:
    def run_pipeline(self, path, output_dir, **options):
        return _LegacyResult()


def test_persist_analysis_run_reuses_existing_sample_and_batch(tmp_path):
    db = SampleDB(tmp_path / "samples.db")
    data_file = tmp_path / "pa6.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")
    context = AnalysisRunPersistenceContext(
        technique="saxs",
        submodule="saxs.static",
        data_file=str(data_file),
        output_dir=str(tmp_path / "output"),
        project_label="PA6",
        history_context={},
    )
    result = {
        "technique": "saxs",
        "metadata": {"polymer_name": "PA6"},
        "parameters": {"L_nm": 12.0},
    }

    first_run_id = persist_analysis_run(db, result, context)
    second_run_id = persist_analysis_run(db, result, context)

    samples = db.list_samples(limit=10)
    assert len(samples) == 1
    batches = db.get_batches(samples[0]["id"])
    assert len(batches) == 1
    runs = db.get_analysis_runs(batches[0]["id"])
    assert {run["id"] for run in runs} == {first_run_id, second_run_id}
    db.close()


def test_persist_analysis_run_stores_evidence_flags_and_history_context(tmp_path):
    db = SampleDB(tmp_path / "samples.db")
    data_file = tmp_path / "pa6.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")
    evidence = {"technique": "SAXS", "constraint_summary": {"status": "ok"}}
    history_context = {"review_summary": "Looks stable", "benchmark_text": "Benchmark: +0.018"}
    context = AnalysisRunPersistenceContext(
        technique="saxs",
        submodule="saxs.static",
        data_file=str(data_file),
        output_dir=str(tmp_path / "output"),
        project_label="PA6",
        current_sample_name="PA6 sample",
        current_sample_id="sample-source",
        current_batch_id="batch-source",
        current_batch_label="batch label",
        ai_tuned=True,
        confirmed=True,
        history_context=history_context,
    )
    result = {
        "technique": "saxs",
        "metadata": {"polymer_name": "metadata name"},
        "parameters": {"r_squared": 0.9876},
        "analysis_evidence": evidence,
    }

    run_id = persist_analysis_run(db, result, context)

    run = db.get_analysis_run(run_id)
    assert run["analysis_evidence"] == evidence
    assert run["ai_tuned"] == 1
    assert run["confirmed"] == 1
    assert run["parameters"]["polymer_type"] == "PA6"
    assert run["results_summary"]["sample_name"] == "PA6 sample"
    assert run["results_summary"]["result_origin"] == "controlled_optimization_rerun"
    assert run["results_summary"]["history_context"] == history_context
    assert run["results_summary"]["r2"] == 0.9876
    db.close()


def test_persist_analysis_run_keeps_public_saxs_quality_dto_condition_axis(tmp_path):
    db = SampleDB(tmp_path / "samples.db")
    data_file = tmp_path / "temperature.csv"
    data_file.write_text("temperature_C,L_nm\n20,12\n", encoding="utf-8")
    axis = {
        "condition_name": "temperature_C",
        "condition_values": [20.0, None, 40.0],
        "status": "diagnostic",
        "invalid_positions": [1],
        "duplicate_positions": [],
        "non_monotonic_positions": [2],
    }
    summary = MetricEvidenceSummary(
        metric_name="Porod",
        frame_count=3,
        level="Diagnostic",
        condition_axis=axis,
    )
    params = {"metric_evidence": {"porod": summary}}
    context = AnalysisRunPersistenceContext(
        technique="saxs",
        submodule="saxs.temperature",
        data_file=str(data_file),
        output_dir=str(tmp_path / "output"),
        project_label="PA6",
    )

    run_id = persist_analysis_run(
        db,
        {"technique": "saxs", "parameters": params},
        context,
    )

    run = db.get_analysis_run(run_id)
    expected = summary.to_dict()
    assert run["parameters"]["metric_evidence"]["porod"] == expected
    assert run["results_summary"]["result"]["parameters"]["metric_evidence"]["porod"] == expected
    db.close()


def test_persisted_run_history_context_can_be_rebound_to_its_own_run_id(tmp_path):
    db = SampleDB(tmp_path / "samples.db")
    data_file = tmp_path / "pa6.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")
    run_id = persist_analysis_run(
        db,
        {"technique": "saxs", "parameters": {}},
        AnalysisRunPersistenceContext(
            technique="saxs",
            data_file=str(data_file),
            history_context={"tuning_context": {"analysis_plan_evaluation": {"version": 1}}},
        ),
    )
    bound_context = {
        "tuning_context": {
            "analysis_plan_evaluation": {"version": 1},
            "analysis_plan_evaluation_run_id": run_id,
        }
    }

    assert db.update_analysis_history_context(run_id, bound_context) is True

    assert db.get_analysis_run(run_id)["results_summary"]["history_context"] == bound_context
    db.close()


def test_persist_analysis_run_stores_shared_compute_run_projection(tmp_path):
    db = SampleDB(tmp_path / "samples.db")
    data_file = tmp_path / "pa6.csv"
    data_file.write_text("Wavenumber,Absorbance\n1700,0.4\n1600,0.8\n", encoding="utf-8")
    compute_run = ComputeRunService(lambda *args, **kwargs: _Engine()).run_direct(
        technique="ir", path=data_file, output_dir=tmp_path / "output"
    )

    run_id = persist_analysis_run(
        db,
        compute_run.legacy_result,
        AnalysisRunPersistenceContext(
            technique="ir",
            data_file=str(data_file),
            compute_run=compute_run,
        ),
    )

    summary = db.get_analysis_run(run_id)["results_summary"]
    assert summary["compute_run"]["canonical_template"]["template_id"] == "spectrum_1d.v1"
    assert len(summary["compute_run"]["capability_items"]) == 2
    assert summary["result"]["parameters"] == {"peak": 1.0}
    db.close()


def test_persist_batch_analysis_runs_keeps_one_compute_run_per_row(tmp_path):
    db = SampleDB(tmp_path / "samples.db")
    rows = []
    for name in ("first.csv", "second.csv"):
        data_file = tmp_path / name
        data_file.write_text("Wavenumber,Absorbance\n1700,0.4\n1600,0.8\n", encoding="utf-8")
        compute_run = ComputeRunService(lambda *args, **kwargs: _Engine()).run_direct(
            technique="ir", path=data_file, output_dir=tmp_path / name.removesuffix(".csv")
        )
        rows.append({
            "file": name,
            "path": str(data_file),
            "output_dir": str(tmp_path / name.removesuffix(".csv")),
            "compute_run": compute_run,
        })

    run_ids = persist_batch_analysis_runs(
        db,
        rows,
        AnalysisRunPersistenceContext(technique="ir", submodule="ir.batch"),
    )

    assert len(run_ids) == 2
    persisted = [db.get_analysis_run(run_id) for run_id in run_ids]
    assert all(run["results_summary"]["compute_run"]["canonical_template"]["template_id"] == "spectrum_1d.v1" for run in persisted)
    db.close()
