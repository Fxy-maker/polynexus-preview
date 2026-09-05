from __future__ import annotations

from pathlib import Path

from polynexus.cli.batch_run_service import allowed_extensions
from polynexus.cli.parser import parse_args
from polynexus.core.ai_platform import default_descriptor_registry
from polynexus.core.canonical_experiments import CanonicalExperiment, default_converter_registry
from polynexus.core.compute import ComputeRunService, RawArtifact
from polynexus.core.engine import get_engine
from polynexus.core.project_workflow.adapters import SingleInputTechniqueAdapter


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_mechanics_table_preserves_explicit_response_signals(tmp_path: Path) -> None:
    source = _write(
        tmp_path / "tensile.csv",
        "Strain (%),Tensile Stress (MPa),Force (N),Vendor Modulus (MPa)\n"
        "0,0,0,1000\n1,10,20,900\n2,7,18,800\n",
    )

    outcome = default_converter_registry().convert_path(
        source, technique="mechanics", source_artifact_id="mechanics-tensile"
    )

    assert outcome.status == "ready"
    assert outcome.template is not None
    assert outcome.template.template_id == "mechanics_curve_1d.v1"
    assert outcome.template.payload["technique"] == "MECHANICS"
    by_kind = {
        item.acquisition_metadata["signal_kind"]: item
        for item in outcome.template.measurements
    }
    assert set(by_kind) == {"tensile_stress", "force", "vendor_modulus"}
    assert by_kind["tensile_stress"].units["intensity"] == "MPa"
    assert all(item.mapping.x_kind == "strain" for item in by_kind.values())


def test_mechanics_duplicate_semantics_require_input(tmp_path: Path) -> None:
    source = _write(
        tmp_path / "duplicate.csv",
        "Strain (%),Stress (MPa),Tensile Stress (MPa)\n"
        "0,0,0\n1,10,11\n2,7,8\n",
    )

    outcome = default_converter_registry().convert_path(
        source, technique="mechanics", source_artifact_id="mechanics-duplicate"
    )

    assert outcome.status == "needs_input"
    assert "conversion_mapping_ambiguous" in outcome.reason_codes


def test_mechanics_compute_run_and_manifest_use_shared_contract(tmp_path: Path) -> None:
    source = _write(
        tmp_path / "curve.csv",
        "Strain (%),Tensile Stress (MPa)\n0,0\n1,10\n2,7\n",
    )

    run = ComputeRunService().run_direct(
        technique="mechanics", path=source, output_dir=""
    )

    assert run.status == "completed"
    assert run.canonical_template is not None
    assert run.canonical_template.template_id == "mechanics_curve_1d.v1"
    assert run.result is not None
    group = next(iter(run.result.metrics["mechanics_groups"].values()))
    assert group["response_descriptors"]
    manifest = {
        item["path"]: item
        for item in run.result.metric_manifest(source=str(source))
    }
    integral_path = next(
        path for path in manifest if path.endswith("raw_integral.value")
    )
    assert manifest[integral_path]["method"] == (
        "baseline_uncorrected_trapezoid_integral"
    )
    assert manifest[integral_path]["unit"] == "MPa*%"


def test_mechanics_prevalidated_template_does_not_reparse_source(tmp_path: Path) -> None:
    source = _write(
        tmp_path / "prevalidated.csv",
        "Strain (%),Tensile Stress (MPa)\n0,0\n1,10\n2,7\n",
    )
    artifact = RawArtifact.from_path(source, technique="mechanics")
    outcome = default_converter_registry().convert_path(
        source,
        technique="mechanics",
        source_artifact_id=artifact.artifact_id,
    )
    assert outcome.template is not None
    engine = get_engine("mechanics")
    assert engine is not None

    def fail_reload(_path: str) -> bool:
        raise AssertionError("prevalidated mechanics template must not reparse raw data")

    engine.load = fail_reload
    run = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="mechanics",
        path=source,
        output_dir="",
        engine=engine,
        canonical_template=outcome.template,
    )

    assert run.status == "completed"
    assert run.canonical_template is not None
    assert run.canonical_template.content_hash == outcome.template.content_hash


def test_mechanics_compute_run_uses_canonical_analysis_spec(tmp_path: Path) -> None:
    source = _write(
        tmp_path / "advanced.csv",
        "Strain,Stress (MPa)\n"
        "0,0\n"
        "0.001,2\n"
        "0.002,4\n"
        "0.003,6\n"
        "0.01,5\n",
    )
    artifact = RawArtifact.from_path(source, technique="mechanics")
    outcome = default_converter_registry().convert_path(
        source, technique="mechanics", source_artifact_id=artifact.artifact_id
    )
    assert outcome.template is not None
    payload = dict(outcome.template.payload)
    payload["mechanics_analysis"] = {
        "test_mode": "tensile",
        "stress_measurement_id": outcome.template.measurements[0].measurement_id,
        "geometry": {"gauge_length_mm": 10.0},
        "stress_unit": "MPa",
        "strain_unit": "1",
        "modulus_window": [0.0, 0.002],
        "yield_offset": 0.001,
        "toughness_endpoint": "last_valid",
    }
    configured = CanonicalExperiment.create(
        template_id=outcome.template.template_id,
        source_artifact_id=outcome.template.source_artifact_id,
        payload=payload,
        conversion_record=outcome.template.conversion_record,
        measurements=outcome.template.measurements,
    )

    run = ComputeRunService().run_direct(
        technique="mechanics",
        path=source,
        output_dir="",
        canonical_template=configured,
    )

    assert run.status == "completed"
    summary = next(iter(run.result.metrics["mechanics_groups"].values()))[
        "mechanics_property_summary"
    ]
    assert summary["tensile_modulus"]["status"] == "computed"
    assert summary["toughness"]["status"] == "computed"
    manifest = {
        item["path"]: item
        for item in run.result.metric_manifest(source=str(source))
    }
    yield_metric = manifest["mechanics_groups.sheet-0-table-0.mechanics_property_summary.yield_stress.value"]
    assert yield_metric["method"] == "offset_line_intersection"
    assert yield_metric["parameters"]["geometry"] == {"gauge_length_mm": 10.0}
    toughness_metric = manifest[
        "mechanics_groups.sheet-0-table-0.mechanics_property_summary.toughness.value"
    ]
    assert toughness_metric["method"] == "stress_strain_trapezoid_to_last_valid"


def test_mechanics_cli_batch_and_project_routes_share_canonical_name(
    tmp_path: Path,
) -> None:
    source = _write(
        tmp_path / "project.csv",
        "Strain (%),Tensile Stress (MPa)\n0,0\n1,10\n2,7\n",
    )

    assert parse_args(["mechanics", str(source)]).cmd == "mechanics"
    assert parse_args(["batch", str(tmp_path), "--technique", "mechanics"]).technique == (
        "mechanics"
    )
    assert ".csv" in allowed_extensions("mechanics")
    proposal = SingleInputTechniqueAdapter().propose_recipe(
        {
            "workflow_id": SingleInputTechniqueAdapter.workflow_id,
            "technique": "mechanics",
            "path": str(source),
        }
    )
    assert proposal.status == "ready"
    assert proposal.recipe is not None
    assert proposal.recipe.steps[0].parameters["canonical_template"]["template_id"] == (
        "mechanics_curve_1d.v1"
    )
    registry = default_descriptor_registry()
    assert "mechanics" in registry.get("curve.summary.v1").techniques
    assert registry.get("mechanics.tensile.v1").status == "unsupported"
