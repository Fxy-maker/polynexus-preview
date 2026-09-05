from __future__ import annotations

from pathlib import Path

from polynexus.cli.parser import parse_args
from polynexus.cli.batch_run_service import allowed_extensions
from polynexus.core.ai_platform import default_descriptor_registry
from polynexus.core.canonical_experiments import default_converter_registry
from polynexus.core.compute import ComputeRunService, RawArtifact
from polynexus.core.engine import get_engine


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_rheology_steady_table_preserves_every_explicit_signal(tmp_path: Path) -> None:
    source = _write(
        tmp_path / "steady.csv",
        "Shear Rate (1/s),Shear Stress (kPa),Viscosity (Pa s)\n"
        "1,0.01,10\n10,0.05,5\n100,0.2,2\n",
    )

    outcome = default_converter_registry().convert_path(
        source, technique="rheology", source_artifact_id="rheology-steady"
    )

    assert outcome.status == "ready"
    assert outcome.template is not None
    assert outcome.template.template_id == "rheology_curve_1d.v1"
    assert len(outcome.template.measurements) == 2
    by_kind = {
        item.acquisition_metadata["signal_kind"]: item
        for item in outcome.template.measurements
    }
    assert set(by_kind) == {"shear_stress", "viscosity"}
    assert by_kind["shear_stress"].units == {"x": "s^-1", "intensity": "kPa"}
    assert by_kind["viscosity"].units["intensity"] == "Pa*s"


def test_rheology_oscillatory_table_preserves_g_prime_and_g_double_prime(
    tmp_path: Path,
) -> None:
    source = _write(
        tmp_path / "oscillation.tsv",
        "Frequency (Hz)\tG′ (kPa)\tG″ (Pa)\n"
        "1\t1\t100\n10\t2\t500\n100\t3\t600\n",
    )

    outcome = default_converter_registry().convert_path(
        source, technique="rheology", source_artifact_id="rheology-oscillation"
    )

    assert outcome.status == "ready"
    assert outcome.template is not None
    by_kind = {
        item.acquisition_metadata["signal_kind"]: item
        for item in outcome.template.measurements
    }
    assert set(by_kind) == {"storage_modulus", "loss_modulus"}
    assert all(
        item.acquisition_metadata["modulus_basis"] == "shear"
        for item in by_kind.values()
    )


def test_rheology_frequency_with_radians_per_second_is_angular_frequency(
    tmp_path: Path,
) -> None:
    source = _write(
        tmp_path / "angular-frequency.csv",
        "Frequency (rad/s),G' (Pa),G'' (Pa)\n1,10,1\n10,20,2\n",
    )

    outcome = default_converter_registry().convert_path(
        source, technique="rheology", source_artifact_id="rheology-angular"
    )

    assert outcome.status == "ready"
    assert outcome.template is not None
    measurement = outcome.template.measurements[0]
    assert measurement.mapping is not None
    assert measurement.mapping.x_kind == "angular_frequency"
    assert measurement.units["x"] == "rad/s"


def test_rheology_greek_gamma_distinguishes_rate_from_strain(tmp_path: Path) -> None:
    rate_source = _write(
        tmp_path / "gamma-dot.csv",
        "γ̇ (1/s),Shear Stress (Pa)\n1,10\n10,50\n",
    )
    strain_source = _write(
        tmp_path / "gamma-strain.csv",
        "γ (%),G' (Pa),G'' (Pa)\n0.1,100,10\n1,90,20\n",
    )

    rate = default_converter_registry().convert_path(
        rate_source, technique="rheology", source_artifact_id="rheology-rate"
    )
    strain = default_converter_registry().convert_path(
        strain_source, technique="rheology", source_artifact_id="rheology-strain"
    )

    assert rate.status == "ready"
    assert rate.template is not None
    assert {item.mapping.x_kind for item in rate.template.measurements} == {
        "shear_rate"
    }
    assert strain.status == "ready"
    assert strain.template is not None
    assert {item.mapping.x_kind for item in strain.template.measurements} == {
        "strain"
    }


def test_rheology_greek_eta_viscosity_header_is_supported(tmp_path: Path) -> None:
    source = _write(
        tmp_path / "eta-viscosity.csv",
        "Shear Rate (1/s),η (cP)\n1,1000\n10,500\n",
    )

    outcome = default_converter_registry().convert_path(
        source, technique="rheology", source_artifact_id="rheology-eta"
    )

    assert outcome.status == "ready"
    assert outcome.template is not None
    measurement = outcome.template.measurements[0]
    assert measurement.acquisition_metadata["signal_kind"] == "viscosity"
    assert measurement.units["intensity"] == "cP"


def test_rheology_strain_sweep_preserves_auxiliary_signals_without_interpretation(
    tmp_path: Path,
) -> None:
    source = _write(
        tmp_path / "strain-sweep.csv",
        "Strain (%),G' (Pa),G'' (Pa),|eta*| (Pa s),tan delta,"
        "Normal Force (mN),Torque (mN m)\n"
        "0.1,100,10,16,0.1,2,3\n1,90,20,15,0.22,2.5,3.5\n",
    )

    outcome = default_converter_registry().convert_path(
        source, technique="rheology", source_artifact_id="rheology-strain"
    )

    assert outcome.status == "ready"
    assert outcome.template is not None
    by_kind = {
        item.acquisition_metadata["signal_kind"]: item
        for item in outcome.template.measurements
    }
    assert set(by_kind) == {
        "storage_modulus",
        "loss_modulus",
        "complex_viscosity",
        "tan_delta",
        "normal_force",
        "torque",
    }
    assert {item.mapping.x_kind for item in by_kind.values()} == {"strain"}
    assert by_kind["complex_viscosity"].units["intensity"] == "Pa*s"
    assert by_kind["normal_force"].units["intensity"] == "mN"
    assert by_kind["torque"].units["intensity"] == "mN*m"


def test_rheology_duplicate_semantic_signals_require_input(tmp_path: Path) -> None:
    source = _write(
        tmp_path / "duplicate.csv",
        "Shear Rate (1/s),Viscosity (Pa s),Viscosity (mPa s)\n"
        "1,10,11\n10,5,6\n",
    )

    outcome = default_converter_registry().convert_path(
        source, technique="rheology", source_artifact_id="rheology-duplicate"
    )

    assert outcome.status == "needs_input"
    assert "conversion_mapping_ambiguous" in outcome.reason_codes


def test_rheology_compute_run_exposes_oscillatory_metrics_and_manifest(
    tmp_path: Path,
) -> None:
    frequency = (1.0, 10.0, 100.0)
    storage = (1000.0, 2000.0, 3000.0)
    loss = (100.0, 500.0, 600.0)
    rows = ["Frequency (Hz),G' (Pa),G'' (Pa)"]
    rows.extend(
        f"{x},{g_storage},{g_loss}"
        for x, g_storage, g_loss in zip(frequency, storage, loss, strict=True)
    )
    source = _write(tmp_path / "oscillation.csv", "\n".join(rows) + "\n")
    source_bytes = source.read_bytes()

    run = ComputeRunService().run_direct(
        technique="rheology", path=source, output_dir=""
    )

    assert run.status == "completed"
    assert run.canonical_template is not None
    assert run.canonical_template.template_id == "rheology_curve_1d.v1"
    assert run.result is not None
    assert source.read_bytes() == source_bytes
    group = next(iter(run.result.metrics["rheology_groups"].values()))
    assert group["oscillatory"]["tan_delta"]["values"] == (0.1, 0.25, 0.2)
    manifest = {
        item["path"]: item
        for item in run.result.metric_manifest(source=str(source))
    }
    tan_delta_path = next(
        path for path in manifest if path.endswith("oscillatory.tan_delta.values")
    )
    assert manifest[tan_delta_path]["kind"] == "series"
    assert manifest[tan_delta_path]["unit"] == "1"
    assert manifest[tan_delta_path]["method"] == "loss_modulus_divided_by_storage_modulus"
    assert any(
        item.capability_id == "curve.summary.v1" and item.status == "completed"
        for item in run.capability_items
    )


def test_rheology_prevalidated_template_does_not_reparse_source(tmp_path: Path) -> None:
    source = _write(
        tmp_path / "steady-prevalidated.csv",
        "Shear Rate (1/s),Shear Stress (Pa)\n1,10\n10,50\n100,200\n",
    )
    artifact = RawArtifact.from_path(source, technique="rheology")
    outcome = default_converter_registry().convert_path(
        source, technique="rheology", source_artifact_id=artifact.artifact_id
    )
    assert outcome.template is not None
    engine = get_engine("rheology")
    assert engine is not None

    def fail_reload(_path: str) -> bool:
        raise AssertionError("prevalidated rheology template must not reparse raw data")

    engine.load = fail_reload
    run = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="rheology",
        path=source,
        output_dir="",
        engine=engine,
        canonical_template=outcome.template,
    )

    assert run.status == "completed"
    assert run.canonical_template is not None
    assert run.canonical_template.content_hash == outcome.template.content_hash


def test_rheology_is_available_in_single_and_batch_cli_parsers() -> None:
    assert parse_args(["rheology", "curve.csv"]).cmd == "rheology"
    assert (
        parse_args(["batch", "data", "--technique", "rheology"]).technique
        == "rheology"
    )
    assert {".csv", ".tsv", ".xlsx"}.issubset(allowed_extensions("rheology"))


def test_ai_catalog_exposes_generic_curve_work_but_not_promoted_rheology_claims() -> None:
    registry = default_descriptor_registry()

    assert "rheology" in registry.get("curve.summary.v1").techniques
    assert registry.get("rheology.viscosity.v1").status == "unsupported"
