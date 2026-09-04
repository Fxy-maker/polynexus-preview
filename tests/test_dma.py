from __future__ import annotations

from pathlib import Path

from polynexus.cli.parser import parse_args
from polynexus.core.canonical_experiments import default_converter_registry
from polynexus.core.compute import ComputeRunService, RawArtifact
from polynexus.core.engine import get_engine


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_dma_frequency_modulus_table_is_sample_neutral(tmp_path: Path) -> None:
    source = _write(
        tmp_path / "blend-a.csv",
        "Frequency (Hz),Storage Modulus (MPa)\n1,10\n10,12\n100,18\n",
    )
    outcome = default_converter_registry().convert_path(
        source, technique="dma", source_artifact_id="dma-a"
    )

    assert outcome.status == "ready"
    assert outcome.template is not None
    assert outcome.template.template_id == "dma_curve_1d.v1"
    measurement = outcome.template.measurements[0]
    assert measurement.family == "viscoelastic_1d"
    assert measurement.mapping is not None
    assert measurement.mapping.x_kind == "frequency"
    assert measurement.units == {"x": "Hz", "intensity": "MPa"}


def test_dma_multiple_signals_require_explicit_mapping(tmp_path: Path) -> None:
    source = _write(
        tmp_path / "blend-b.tsv",
        "Temperature (C)\tStorage Modulus (MPa)\tLoss Modulus (MPa)\n20\t10\t2\n40\t8\t3\n",
    )
    outcome = default_converter_registry().convert_path(
        source, technique="dma", source_artifact_id="dma-b"
    )

    assert outcome.status == "needs_input"
    assert "conversion_mapping_ambiguous" in outcome.reason_codes


def test_dma_compute_run_and_shared_curve_capability(tmp_path: Path) -> None:
    source = _write(
        tmp_path / "blend-c.csv",
        "Temperature (C),tan delta\n20,0.20\n40,0.35\n60,0.50\n",
    )
    engine = get_engine("dma")
    assert engine is not None
    run = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="dma", path=source, output_dir="", engine=engine
    )
    assert run.status == "completed"
    assert run.canonical_template is not None
    assert run.canonical_template.template_id == "dma_curve_1d.v1"
    assert run.result is not None
    assert run.result.metrics["point_count"] == 3
    assert any(item.capability_id == "curve.extrema.v1" and item.status == "completed" for item in run.capability_items)


def test_dma_compute_run_executes_prevalidated_template_without_reloading(tmp_path: Path) -> None:
    source = _write(
        tmp_path / "blend-d.csv",
        "Frequency (Hz),Storage Modulus (MPa)\n1,10\n10,12\n100,18\n",
    )
    artifact = RawArtifact.from_path(source, technique="dma")
    outcome = default_converter_registry().convert_path(
        source, technique="dma", source_artifact_id=artifact.artifact_id
    )
    assert outcome.template is not None
    engine = get_engine("dma")
    assert engine is not None

    def fail_reload(_path: str) -> bool:
        raise AssertionError("prevalidated DMA template must not reparse raw data")

    engine.load = fail_reload
    run = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="dma",
        path=source,
        output_dir="",
        engine=engine,
        canonical_template=outcome.template,
    )
    assert run.status == "completed"
    assert run.canonical_template is not None
    assert run.canonical_template.content_hash == outcome.template.content_hash


def test_dma_is_available_in_single_and_batch_cli_parsers() -> None:
    assert parse_args(["dma", "curve.csv"]).cmd == "dma"
    assert parse_args(["batch", "data", "--technique", "dma"]).technique == "dma"
