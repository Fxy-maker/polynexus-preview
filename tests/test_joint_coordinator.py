import pytest

from polynexus.core.joint.coordinator import JointCoordinator
from polynexus.core.joint.matchers import MultiTechniqueTimeline
from polynexus.data.sample_db import SampleDB


def test_joint_coordinator_lists_models_and_schema():
    coord = JointCoordinator()

    assert coord.list_models() == ["fibrillar", "lamellar"]

    schema = coord.get_model_schema("lamellar")
    assert schema["name"] == "lamellar"
    assert any(item["name"] == "Tm_DSC_C" for item in schema["parameters"])
    assert "L_nm" in schema["observations"]


def test_joint_coordinator_joint_fit_returns_minimal_result():
    coord = JointCoordinator()

    result = coord.joint_fit(
        "lamellar",
        "sample-01",
        ["batch-a"],
        {
            "Tm_DSC_C": {"value": 221.0, "uncertainty": 2.0},
            "L_nm": (12.4, 0.5),
            "Xc_pct": 41.5,
        },
    )

    assert result["name"] == "joint_fit"
    assert result["model"] == "lamellar"
    assert result["success"] is True
    assert result["parameters"]["Tm_DSC_C"] == pytest.approx(221.0)
    assert result["parameters"]["L_nm"] == pytest.approx(12.4)
    assert result["parameters"]["Xc_pct"] == pytest.approx(41.5)
    assert result["n_observations"] == 3


def test_joint_model_moves_parameters_toward_observations():
    from polynexus.core.joint.models import LamellarJointModel

    model = LamellarJointModel()
    model.add_observation("Tm_DSC_C", 240.0, 1.0)
    model.add_observation("L_nm", 18.0, 0.5)
    model.add_observation("Xc_pct", 35.0, 2.0)
    result = model.solve()

    assert result.success is True
    assert abs(result.parameters["Tm_DSC_C"] - 240.0) < 0.5
    assert abs(result.parameters["L_nm"] - 18.0) < 0.5
    assert abs(result.parameters["Xc_pct"] - 35.0) < 1.0
    assert result.message != "Solved with initial parameter vector"


def test_joint_coordinator_timeline_collects_rows(tmp_path):
    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(
        sample_id,
        "annealed-01",
        instrument="multi",
        condition_type="temperature",
        condition_values={"temperature_C": 180},
    )
    db.create_analysis_run(
        batch_id,
        "dsc",
        results_summary={"Tm_peak_C": 221.0, "Xc_pct": 42.0},
    )

    coord = JointCoordinator(sample_db=db)
    report = coord.build_timeline(sample_id, "temperature_C")

    assert report["name"] == "linked_timeline"
    assert report["tables"]
    timeline_df = report["tables"][0]
    assert list(timeline_df["condition_key"].unique()) == ["temperature_C"]
    assert list(timeline_df["condition_value"].unique()) == [180]

    db.close()


def test_multi_technique_timeline_aligns_shared_axis():
    timeline = MultiTechniqueTimeline("temperature_C")
    timeline.add_series(
        {
            "batch_id": "batch-a",
            "batch_label": "annealed-01",
            "sample_id": "sample-01",
            "sample_name": "PA6",
            "technique": "dsc",
        },
        "Tm_peak_C",
        [120, 140],
        [221.0, 223.5],
    )
    timeline.add_series(
        {
            "batch_id": "batch-a",
            "batch_label": "annealed-01",
            "sample_id": "sample-01",
            "sample_name": "PA6",
            "technique": "saxs",
        },
        "L_nm",
        [120, 140],
        [12.0, 11.5],
    )

    shared_axis = timeline.get_shared_axis()
    df = timeline.to_dataframe()

    assert shared_axis == [120.0, 140.0]
    assert set(df["param_key"]) == {"Tm_peak_C", "L_nm"}
    assert set(df["shared_condition_index"].dropna().astype(int)) == {0, 1}
    assert len(df) == 4


def test_joint_coordinator_timeline_report_includes_figure(tmp_path):
    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(
        sample_id,
        "annealed-01",
        instrument="multi",
        condition_type="temperature",
        condition_values={"temperature_C": 180},
    )
    db.create_analysis_run(
        batch_id,
        "dsc",
        results_summary={"Tm_peak_C": 221.0, "Xc_pct": 42.0},
    )
    db.create_analysis_run(
        batch_id,
        "saxs",
        results_summary={"L_nm": 12.0, "lc_nm": 5.0},
    )

    coord = JointCoordinator(sample_db=db)
    report = coord.build_timeline(sample_id, "temperature_C")

    assert "timeline_alignment" in report["figures"]
    assert len(report["tables"]) == 2

    db.close()


def test_joint_coordinator_same_sample_includes_ir_vs_dsc_figure(tmp_path):
    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(
        sample_id,
        "annealed-01",
        instrument="multi",
        condition_type="temperature",
        condition_values={"temperature_C": 180},
    )
    db.create_analysis_run(
        batch_id,
        "dsc",
        results_summary={"Xc_pct": 42.0},
    )
    db.create_analysis_run(
        batch_id,
        "ir",
        results_summary={"crystallinity_index": 0.63},
    )

    coord = JointCoordinator(sample_db=db)
    report = coord.compare_same_sample(sample_id, [batch_id])

    assert "ir_vs_dsc_xc" in report["figures"]
    assert report["tables"]

    db.close()
