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
