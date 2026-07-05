from polynexus.data.sample_db import SampleDB


def test_find_sample_by_name_matches_case_insensitively(tmp_path):
    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6", aliases=["nylon-6"])

    sample = db.find_sample_by_name("pa6")

    assert sample is not None
    assert sample["id"] == sample_id
    assert sample["polymer_name"] == "PA6"


def test_analysis_run_persists_analysis_evidence(tmp_path):
    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(sample_id, "annealed")
    evidence = {
        "technique": "SAXS",
        "constraint_summary": {"status": "soft_warn"},
        "structure_evidence": {
            "lc_reliability_status": "diagnostic_only",
            "lc_reliability_reason": "within_melting_window|peak_tracking_lost",
        },
    }

    run_id = db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.temperature",
        results_summary={"L_nm": 12.0, "lc_nm": 3.0},
        analysis_evidence=evidence,
    )

    runs = db.get_analysis_runs(batch_id)
    saved = next(run for run in runs if run["id"] == run_id)
    assert saved["analysis_evidence"] == evidence
