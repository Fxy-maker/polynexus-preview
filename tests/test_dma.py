from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from polynexus.cli.parser import parse_args
from polynexus.core.canonical_experiments import MappingProposal, default_converter_registry
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


def test_dma_explicit_multisignal_table_preserves_every_signal(tmp_path: Path) -> None:
    source = _write(
        tmp_path / "blend-b.tsv",
        "Temperature (C)\tE' (MPa)\tE'' (MPa)\ttan delta\n"
        "20\t10\t2\t0.2\n40\t8\t3\t0.375\n",
    )
    outcome = default_converter_registry().convert_path(
        source, technique="dma", source_artifact_id="dma-b"
    )

    assert outcome.status == "ready"
    assert outcome.template is not None
    assert len(outcome.template.measurements) == 3
    assert len({item.measurement_id for item in outcome.template.measurements}) == 3
    by_kind = {
        item.acquisition_metadata["signal_kind"]: item
        for item in outcome.template.measurements
    }
    assert set(by_kind) == {"storage_modulus", "loss_modulus", "tan_delta"}
    assert by_kind["storage_modulus"].acquisition_metadata["modulus_basis"] == "tensile"
    assert by_kind["loss_modulus"].acquisition_metadata["modulus_basis"] == "tensile"
    assert by_kind["tan_delta"].units["intensity"] == "1"


def test_dma_duplicate_semantic_signals_still_require_mapping(tmp_path: Path) -> None:
    source = _write(
        tmp_path / "duplicate-storage.csv",
        "Temperature (C),Storage Modulus (MPa),Storage Modulus (GPa)\n"
        "20,10,0.01\n40,8,0.008\n",
    )
    outcome = default_converter_registry().convert_path(
        source, technique="dma", source_artifact_id="dma-duplicate"
    )

    assert outcome.status == "needs_input"
    assert "conversion_mapping_ambiguous" in outcome.reason_codes


def test_dma_unicode_tensile_and_shear_signals_keep_separate_bases(
    tmp_path: Path,
) -> None:
    source = _write(
        tmp_path / "dual-basis.csv",
        "Temperature (C),E′ (GPa),E″ (MPa),G′ (MPa),G″ (kPa),tan δ\n"
        "20,1.0,100,0.4,40,0.1\n40,0.8,120,0.3,45,0.15\n",
    )

    outcome = default_converter_registry().convert_path(
        source, technique="dma", source_artifact_id="dma-dual-basis"
    )

    assert outcome.status == "ready"
    assert outcome.template is not None
    descriptors = {
        (
            item.acquisition_metadata["signal_kind"],
            item.acquisition_metadata["modulus_basis"],
        )
        for item in outcome.template.measurements
    }
    assert descriptors == {
        ("storage_modulus", "tensile"),
        ("loss_modulus", "tensile"),
        ("storage_modulus", "shear"),
        ("loss_modulus", "shear"),
        ("tan_delta", "unspecified"),
    }


def test_dma_multisignal_table_rejects_single_signal_mapping_proposal(
    tmp_path: Path,
) -> None:
    source = _write(
        tmp_path / "proposal-cannot-express-multisignal.csv",
        "Temperature (C),E' (MPa),E'' (MPa)\n20,10,2\n40,8,3\n",
    )
    observed = default_converter_registry().convert_path(
        source, technique="dma", source_artifact_id="dma-proposal"
    )
    assert observed.template is not None
    observed_mapping = observed.template.measurements[0].mapping
    assert observed_mapping is not None
    proposal = MappingProposal.create(
        source_artifact_id="dma-proposal",
        technique="DMA",
        source="user",
        selections=(
            replace(
                observed_mapping,
                measurement_id="sheet-0-table-0",
                source="user",
            ),
        ),
    )

    outcome = default_converter_registry().convert_path(
        source,
        technique="dma",
        source_artifact_id="dma-proposal",
        mapping_proposal=proposal,
    )

    assert outcome.status == "needs_input"
    assert outcome.reason_codes == ("conversion_mapping_proposal_invalid",)


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


def test_dma_compute_run_derives_tan_delta_and_temperature_peak_candidate(
    tmp_path: Path,
) -> None:
    temperature = np.linspace(20.0, 120.0, 51)
    storage = 1000.0 - 3.0 * temperature
    expected_tan_delta = 0.08 + 0.55 * np.exp(-((temperature - 70.0) / 10.0) ** 2)
    loss_kpa = storage * expected_tan_delta * 1000.0
    rows = ["Temperature (C),E' (MPa),E'' (kPa)"]
    rows.extend(
        f"{x:.10g},{e_storage:.10g},{e_loss:.10g}"
        for x, e_storage, e_loss in zip(temperature, storage, loss_kpa, strict=True)
    )
    source = _write(tmp_path / "derived-tan-delta.csv", "\n".join(rows) + "\n")
    source_bytes = source.read_bytes()

    run = ComputeRunService().run_direct(
        technique="dma", path=source, output_dir=""
    )

    assert run.status == "completed"
    assert run.result is not None
    assert source.read_bytes() == source_bytes
    groups = run.result.metrics["dma_groups"]
    assert len(groups) == 1
    group = next(iter(groups.values()))
    derived = group["derived_tan_delta"]["tensile"]
    assert derived["status"] == "computed"
    assert derived["unit"] == "1"
    assert derived["parameters"]["loss_to_storage_unit_factor"] == pytest.approx(0.001)
    np.testing.assert_allclose(derived["values"], expected_tan_delta, rtol=1e-8)
    candidates = group["transition_candidates"]["derived_tan_delta_tensile"]
    assert candidates["status"] == "computed"
    assert candidates["candidate_count"] == 1
    candidate = candidates["candidate_001"]
    assert candidate["peak_x"] == pytest.approx(70.0, abs=2.1)
    assert candidate["interpretation"] == "response_peak_candidate_not_tg"

    manifest = {
        item["path"]: item
        for item in run.result.metric_manifest(source=str(source))
    }
    derived_path = next(
        path
        for path in manifest
        if path.endswith("derived_tan_delta.tensile.values")
    )
    assert manifest[derived_path]["kind"] == "series"
    assert manifest[derived_path]["unit"] == "1"
    assert manifest[derived_path]["method"] == "loss_modulus_divided_by_storage_modulus"


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
