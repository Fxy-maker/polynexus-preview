from __future__ import annotations

from pathlib import Path

from polynexus.cli.batch_run_service import allowed_extensions
from polynexus.cli.parser import parse_args
from polynexus.core.ai_platform import default_descriptor_registry
from polynexus.core.canonical_experiments import default_converter_registry
from polynexus.core.compute import ComputeRunService, RawArtifact
from polynexus.core.engine import get_engine, list_techniques
from polynexus.core.project_workflow.adapters import SingleInputTechniqueAdapter


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_sec_multidetector_table_preserves_distinct_source_signals(
    tmp_path: Path,
) -> None:
    source = _write(
        tmp_path / "multidetector.csv",
        "Elution Volume (mL),RI (mV),UV (mAU),MALS (mV),Molar Mass (g/mol)\n"
        "1,0,0,1,100000\n2,2,3,4,50000\n3,1,2,3,10000\n",
    )

    outcome = default_converter_registry().convert_path(
        source, technique="gpc", source_artifact_id="sec-multi"
    )

    assert outcome.status == "ready"
    assert outcome.template is not None
    assert outcome.template.template_id == "sec_chromatogram_1d.v1"
    assert outcome.template.payload["technique"] == "SEC"
    by_kind = {
        item.acquisition_metadata["signal_kind"]: item
        for item in outcome.template.measurements
    }
    assert set(by_kind) == {
        "refractive_index_response",
        "uv_response",
        "light_scattering_response",
        "molar_mass",
    }
    assert by_kind["molar_mass"].units["intensity"] == "g/mol"
    assert all(item.mapping.x_kind == "elution_volume" for item in by_kind.values())


def test_sec_duplicate_detector_semantics_require_input(tmp_path: Path) -> None:
    source = _write(
        tmp_path / "duplicate.csv",
        "Retention Time (min),RI (mV),Refractive Index (mV)\n"
        "1,0,0\n2,2,3\n3,1,2\n",
    )

    outcome = default_converter_registry().convert_path(
        source, technique="sec", source_artifact_id="sec-duplicate"
    )

    assert outcome.status == "needs_input"
    assert "conversion_mapping_ambiguous" in outcome.reason_codes


def test_sec_preserves_other_explicit_detector_and_distribution_columns(
    tmp_path: Path,
) -> None:
    source = _write(
        tmp_path / "other-signals.csv",
        "Retention Time (min),RALS (mV),LALS (mV),Differential Pressure (kPa),"
        "Concentration (mg/mL),Log M,Cumulative Weight Distribution (%)\n"
        "1,1,2,3,4,5,10\n2,2,3,4,5,4,50\n3,1,2,3,4,3,100\n",
    )

    outcome = default_converter_registry().convert_path(
        source, technique="sec", source_artifact_id="sec-other-signals"
    )

    assert outcome.status == "ready"
    assert outcome.template is not None
    by_semantics = {
        (
            item.acquisition_metadata["signal_kind"],
            item.acquisition_metadata["detector_kind"],
        ): item
        for item in outcome.template.measurements
    }
    assert set(by_semantics) == {
        ("light_scattering_response", "rals"),
        ("light_scattering_response", "lals"),
        ("viscometer_response", "viscometer"),
        ("concentration_response", "concentration"),
        ("log_molar_mass", "vendor_derived"),
        ("cumulative_weight_distribution", "vendor_derived"),
    }
    assert all(
        item.mapping.x_kind == "retention_time" for item in by_semantics.values()
    )
    assert by_semantics[("viscometer_response", "viscometer")].units[
        "intensity"
    ] == "kPa"
    assert by_semantics[("concentration_response", "concentration")].units[
        "intensity"
    ] == "mg/mL"
    assert by_semantics[("log_molar_mass", "vendor_derived")].units[
        "intensity"
    ] == "log10(g/mol)"


def test_sec_compute_run_and_manifest_use_shared_contract(tmp_path: Path) -> None:
    source = _write(
        tmp_path / "ri.csv",
        "Elution Volume (mL),RI (mV)\n1,0\n2,2\n3,1\n4,0\n",
    )

    run = ComputeRunService().run_direct(technique="sec", path=source, output_dir="")

    assert run.status == "completed"
    assert run.canonical_template is not None
    assert run.canonical_template.template_id == "sec_chromatogram_1d.v1"
    assert run.result is not None
    group = next(iter(run.result.metrics["sec_groups"].values()))
    assert group["response_descriptors"]
    manifest = {item["path"]: item for item in run.result.metric_manifest(source=str(source))}
    integral_path = next(path for path in manifest if path.endswith("raw_integral.value"))
    assert manifest[integral_path]["method"] == "baseline_uncorrected_trapezoid_integral"
    assert manifest[integral_path]["unit"] == "mV*mL"


def test_sec_prevalidated_template_does_not_reparse_source(tmp_path: Path) -> None:
    source = _write(
        tmp_path / "prevalidated.csv",
        "Retention Time (min),RI (mV)\n1,0\n2,2\n3,1\n",
    )
    artifact = RawArtifact.from_path(source, technique="sec")
    outcome = default_converter_registry().convert_path(
        source, technique="sec", source_artifact_id=artifact.artifact_id
    )
    assert outcome.template is not None
    engine = get_engine("sec")
    assert engine is not None

    def fail_reload(_path: str) -> bool:
        raise AssertionError("prevalidated SEC template must not reparse raw data")

    engine.load = fail_reload
    run = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="sec",
        path=source,
        output_dir="",
        engine=engine,
        canonical_template=outcome.template,
    )

    assert run.status == "completed"
    assert run.canonical_template is not None
    assert run.canonical_template.content_hash == outcome.template.content_hash


def test_sec_gpc_entries_and_project_adapter_share_canonical_name(tmp_path: Path) -> None:
    source = _write(
        tmp_path / "project.csv",
        "Elution Volume (mL),RI (mV)\n1,0\n2,2\n3,1\n",
    )

    assert parse_args(["sec", str(source)]).cmd == "sec"
    assert parse_args(["gpc", str(source)]).cmd == "gpc"
    assert parse_args(["batch", str(tmp_path), "--technique", "gpc"]).technique == "gpc"
    assert ".csv" in allowed_extensions("gpc")
    assert [item["name"] for item in list_techniques()].count("sec") == 1
    assert all(item["name"] != "gpc" for item in list_techniques())
    alias_run = ComputeRunService().run_direct(
        technique="gpc", path=source, output_dir=""
    )
    assert alias_run.status == "completed"
    assert alias_run.artifact.technique == "sec"
    proposal = SingleInputTechniqueAdapter().propose_recipe(
        {
            "workflow_id": SingleInputTechniqueAdapter.workflow_id,
            "technique": "sec",
            "path": str(source),
        }
    )
    assert proposal.status == "ready"
    assert proposal.recipe is not None
    assert proposal.recipe.steps[0].parameters["canonical_template"]["template_id"] == (
        "sec_chromatogram_1d.v1"
    )
    registry = default_descriptor_registry()
    assert "sec" in registry.get("curve.summary.v1").techniques
    assert registry.get("sec.molecular_weight.v1").status == "unsupported"
