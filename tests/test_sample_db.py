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


def test_update_analysis_parameters_preserves_detached_orientation_advisory(tmp_path):
    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(sample_id, "orientation")
    run_id = db.create_analysis_run(
        batch_id,
        "saxs",
        parameters={"existing": "value"},
        results_summary={"confirmed": False},
    )
    parameters = {
        "existing": "value",
        "saxs_orientation_advisory_report": {
            "schema_version": "saxs-orientation-advisory-report-v1",
            "status": "limited",
            "source_evidence_digest": "abc",
        },
    }

    assert db.update_analysis_parameters(run_id, parameters) is True
    saved = db.get_analysis_run(run_id)

    assert saved is not None
    assert saved["parameters"] == parameters
    assert saved["confirmed"] == 0
    assert db.update_analysis_parameters("missing-run", parameters) is False
    db.close()
