from pathlib import Path

from polynexus.data.sample_db import SampleDB
from polynexus.gui.analysis_run_service import AnalysisRunPersistenceContext, persist_analysis_run


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
