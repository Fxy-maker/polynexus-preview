from polynexus.data.sample_db import SampleDB


def test_list_analysis_run_headers_omits_large_json_payloads_and_uses_indexes(tmp_path):
    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(sample_id, "header-query")
    run_id = db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        parameters={"large": "x" * 10_000},
        results_summary={"large": "x" * 10_000},
        analysis_evidence={"large": "x" * 10_000},
    )

    headers = db.list_analysis_run_headers()
    index_names = {
        row["name"]
        for row in db._conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
    }

    assert headers == [
        {
            "id": run_id,
            "batch_id": batch_id,
            "technique": "saxs",
            "submodule": "saxs.static",
            "output_dir": "",
            "status": "completed",
            "ai_tuned": 0,
            "confirmed": 0,
            "created_at": headers[0]["created_at"],
        }
    ]
    assert {"parameters", "results_summary", "analysis_evidence", "plot_edits"}.isdisjoint(headers[0])
    assert {"idx_batches_sample_id", "idx_analysis_runs_batch_created_at"}.issubset(index_names)
    db.close()


def test_list_analysis_run_headers_returns_newest_runs_with_limit(tmp_path):
    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(sample_id, "header-limit")
    old_id = db.create_analysis_run(batch_id, "saxs")
    new_id = db.create_analysis_run(batch_id, "waxs")
    db._conn.execute("UPDATE analysis_runs SET created_at=? WHERE id=?", ("2026-01-01 00:00:00", old_id))
    db._conn.execute("UPDATE analysis_runs SET created_at=? WHERE id=?", ("2026-01-02 00:00:00", new_id))
    db._conn.commit()

    headers = db.list_analysis_run_headers(limit=1)

    assert [header["id"] for header in headers] == [new_id]
    db.close()


def test_list_analysis_run_headers_for_batch_filters_before_limit(tmp_path):
    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    target_batch = db.create_batch(sample_id, "target")
    other_batch = db.create_batch(sample_id, "other")
    target_id = db.create_analysis_run(target_batch, "saxs")
    other_id = db.create_analysis_run(other_batch, "saxs")
    db._conn.execute(
        "UPDATE analysis_runs SET created_at=? WHERE id=?",
        ("2026-01-01 00:00:00", target_id),
    )
    db._conn.execute(
        "UPDATE analysis_runs SET created_at=? WHERE id=?",
        ("2026-01-02 00:00:00", other_id),
    )
    db._conn.commit()

    headers = db.list_analysis_run_headers_for_batch(target_batch, limit=1)

    assert [header["id"] for header in headers] == [target_id]
    db.close()


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
