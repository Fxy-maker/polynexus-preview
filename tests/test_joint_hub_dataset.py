import pytest

from polynexus.core.joint.dataset import (
    build_joint_hub_report,
    collect_joint_dataset,
    detect_joint_opportunities,
)
from polynexus.data.sample_db import SampleDB


def test_joint_hub_dataset_collects_latest_runs_and_reports(tmp_path):
    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(
        sample_id,
        "annealed",
        instrument="multi",
        condition_type="temperature",
        condition_values={"temperature_C": 180},
    )
    db.create_analysis_run(
        batch_id,
        "dsc",
        results_summary={"Xc_pct": 42.0, "Tm_peak_C": 218.0},
    )
    db.create_analysis_run(
        batch_id,
        "saxs",
        results_summary={"L_nm": 12.0, "lc_nm": 5.0, "L_corr_nm": 12.0},
    )
    db.create_analysis_run(
        batch_id,
        "waxs",
        results_summary={"Xc_pct": 42.0, "D_Scherrer_nm": 7.5},
    )

    rows = collect_joint_dataset(db)

    assert len(rows) == 1
    assert rows[0].technique_count == 3
    assert rows[0].condition_values == {"temperature_C": 180}
    assert rows[0].technique_cell("dsc").startswith("Xc 42.0%")
    assert "crystallinity consistency" in detect_joint_opportunities(rows[0])
    assert "SAXS-WAXS multiscale" in detect_joint_opportunities(rows[0])

    report = build_joint_hub_report(rows)

    assert report["name"] == "joint_analysis_hub"
    assert len(report["rows"]) == 1
    assert report["rows"][0]["saxs_Xc_pct"] == pytest.approx(100 * 5.0 / 12.0)
    assert report["rows"][0]["condition_values"] == {"temperature_C": 180}
    assert report["validations"]
    assert report["ai_context"]["issue_count"] == 0
    assert "Cross-tech checks passed" in report["ai_context"]["summary"]
    assert report["ai_context"]["ai_boundary"] == {
        "mode": "off",
        "provider_status": "not_configured",
        "fallback": "rule_based_report",
        "failure_policy": "preserve_source_evidence_and_diagnostic_status",
    }


def test_joint_hub_report_builds_cross_tech_ai_context(tmp_path):
    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(
        sample_id,
        "annealed",
        instrument="multi",
        condition_type="temperature",
        condition_values={"temperature_C": 180},
    )
    db.create_analysis_run(
        batch_id,
        "dsc",
        results_summary={"Xc_pct": 42.0, "Tm_peak_C": 221.0},
    )
    db.create_analysis_run(
        batch_id,
        "saxs",
        results_summary={"L_nm": 12.0, "lc_nm": 5.0},
    )
    db.create_analysis_run(
        batch_id,
        "waxs",
        results_summary={"Xc_pct": 30.0, "D_Scherrer_nm": 7.5},
    )

    rows = collect_joint_dataset(db)
    report = build_joint_hub_report(rows)

    context = report["ai_context"]
    assert context["issue_count"] > 0
    assert context["error_count"] >= 0
    assert context["scope"]
    assert context["highlights"]
    assert any("phi_c" in item or "L_consistency" in item or "Tm" in item for item in context["highlights"])
    assert context["ai_boundary"] == {
        "mode": "off",
        "provider_status": "not_configured",
        "fallback": "rule_based_report",
        "failure_policy": "preserve_source_evidence_and_diagnostic_status",
    }


def test_joint_conflict_rows_keep_source_run_and_evidence_provenance(tmp_path):
    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(sample_id, "conflict")
    db.create_analysis_run(
        batch_id,
        "dsc",
        results_summary={"Xc_pct": 80.0},
        analysis_evidence={"constraint_summary": {"status": "ok"}},
    )
    db.create_analysis_run(
        batch_id,
        "waxs",
        results_summary={"Xc_pct": 20.0},
        analysis_evidence={"constraint_summary": {"status": "soft_warn"}},
    )
    db.create_analysis_run(
        batch_id,
        "saxs",
        results_summary={"L_nm": 12.0, "lc_nm": 6.0},
        analysis_evidence={"constraint_summary": {"status": "ok"}},
    )

    rows = collect_joint_dataset(db)
    report = build_joint_hub_report(rows)
    conflict = next(item for item in report["validations"] if "phi_c" in item["check"])
    sources = conflict["provenance"]["sources"]

    assert sources["dsc"]["run_id"] == rows[0].run("dsc").run_id
    assert sources["dsc"]["evidence_status"] == "ok"
    assert sources["waxs"]["run_id"] == rows[0].run("waxs").run_id
    assert sources["waxs"]["evidence_weight"] == pytest.approx(0.45)
    assert sources["saxs"]["run_id"] == rows[0].run("saxs").run_id


def test_joint_hub_report_surfaces_technique_evidence_status(tmp_path):
    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(sample_id, "annealed")
    db.create_analysis_run(
        batch_id,
        "dsc",
        results_summary={"Xc_pct": 42.0, "analysis_evidence": {"constraint_summary": {"status": "ok"}}},
    )
    db.create_analysis_run(
        batch_id,
        "nmr",
        results_summary={
            "Xc_pct": 45.0,
            "Xc_method": "requires_crystalline_amorphous_assignment",
            "analysis_evidence": {
                "constraint_summary": {"status": "soft_warn"},
                "structure_evidence": {"Xc_assignment_status": "assignment_limited"},
                "risk_flags": ["nmr_xc_assignment_missing"],
            },
        },
    )

    report = build_joint_hub_report(collect_joint_dataset(db))

    row = report["rows"][0]
    context = report["ai_context"]
    assert row["technique_confidence"]["nmr"]["status"] == "soft_warn"
    assert row["paper_conclusion_ready_by_technique"]["nmr"] is False
    assert "NMR assignment limited" in context["issue_families"]


def test_joint_context_downgrades_assignment_limited_nmr_xc(tmp_path):
    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(sample_id, "annealed")
    db.create_analysis_run(batch_id, "dsc", results_summary={"Xc_pct": 42.0})
    db.create_analysis_run(
        batch_id,
        "nmr",
        results_summary={
            "Xc_pct": 80.0,
            "Xc_method": "requires_crystalline_amorphous_assignment",
            "analysis_evidence": {
                "constraint_summary": {"status": "soft_warn"},
                "structure_evidence": {"Xc_assignment_status": "assignment_limited"},
            },
        },
    )

    report = build_joint_hub_report(collect_joint_dataset(db))

    assert report["ai_context"]["weak_xc_sources"]["nmr"] == "assignment_limited"
    assert "NMR assignment limited" in report["ai_context"]["issue_families"]
    assert "nmr" in report["ai_context"]["recommended_review_targets"]


def test_joint_low_confidence_saxs_xc_conflict_is_warn_not_error(tmp_path):
    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(sample_id, "melt-window", condition_values={"temperature_C": 225})
    db.create_analysis_run(batch_id, "dsc", results_summary={"Xc_pct": 44.0})
    db.create_analysis_run(
        batch_id,
        "saxs",
        results_summary={"L_nm": 12.0, "lc_nm": 1.2},
        analysis_evidence={
            "constraint_summary": {"status": "soft_warn"},
            "structure_evidence": {"lc_reliability_status": "diagnostic_only"},
        },
    )

    report = build_joint_hub_report(collect_joint_dataset(db))

    assert report["ai_context"]["error_count"] == 0
    assert report["ai_context"]["warning_count"] >= 1
    assert any(
        item["severity"] == "WARN" and "phi_c" in item["check"]
        for item in report["validations"]
    )


def test_joint_low_confidence_saxs_tm_conflict_is_warn_not_error(tmp_path):
    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(sample_id, "melt-window")
    db.create_analysis_run(
        batch_id,
        "dsc",
        results_summary={"Tm_peak_C": 220.0, "Xc_pct": 44.0},
    )
    db.create_analysis_run(
        batch_id,
        "saxs",
        results_summary={"L_nm": 12.0, "lc_nm": 1.0},
        analysis_evidence={
            "constraint_summary": {"status": "soft_warn"},
            "structure_evidence": {"lc_reliability_status": "diagnostic_only"},
        },
    )

    report = build_joint_hub_report(collect_joint_dataset(db))

    tm_conflict = next(item for item in report["validations"] if "Tm_GT" in item["check"])
    assert tm_conflict["passed"] is False
    assert tm_conflict["severity"] == "WARN"
    assert tm_conflict["details"]["evidence_weight"] == pytest.approx(0.25)
    assert report["ai_context"]["error_count"] == 0


def test_joint_hub_consumes_persisted_analysis_evidence(tmp_path):
    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(sample_id, "batch-a")
    db.create_analysis_run(batch_id, "dsc", results_summary={"Xc_pct": 42.0})
    db.create_analysis_run(
        batch_id,
        "nmr",
        results_summary={"Xc_pct": 45.0, "Xc_method": "requires_crystalline_amorphous_assignment"},
        analysis_evidence={
            "constraint_summary": {"status": "soft_warn"},
            "structure_evidence": {"Xc_assignment_status": "assignment_limited"},
        },
    )

    report = build_joint_hub_report(collect_joint_dataset(db))
    context = report["ai_context"]

    assert context["issue_count"] >= 1
    assert "NMR assignment limited" in context["issue_families"]
    assert context["weak_xc_sources"]["nmr"] == "assignment_limited"
