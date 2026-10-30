from __future__ import annotations

from pathlib import Path

import pytest

from polynexus.core.canonical_experiments import PortableExportBinding, default_converter_registry
from polynexus.core.compute import ComputeRunService, RawArtifact


def test_portable_export_binds_raw_hash_and_keeps_one_canonical_template(tmp_path: Path) -> None:
    raw = tmp_path / "sample.ngb-ds1"
    raw.write_bytes(b"Netzsch TA file\x00_db_format_1\x00opaque")
    exported = tmp_path / "sample.csv"
    exported.write_text("Temperature (C),Mass (%)\n25,100\n100,98\n", encoding="utf-8")
    artifact = RawArtifact.from_path(raw, technique="tga")

    outcome = default_converter_registry().convert_portable_export(
        raw,
        exported,
        technique="tga",
        source_artifact_id=artifact.artifact_id,
        exporter="Proteus portable CSV",
    )

    assert outcome.status == "ready"
    assert outcome.template is not None
    binding = outcome.template.payload["portable_export_binding"]
    assert binding["raw_source_sha256"] == artifact.sha256
    assert binding["export_format"] == "csv"
    assert outcome.record.conversion_id.endswith("+portable-export.v1")
    assert outcome.template.source_artifact_id == artifact.artifact_id

    run = ComputeRunService().run_direct(
        technique="tga",
        path=exported,
        output_dir="",
        source_artifact_id=artifact.artifact_id,
        canonical_template=outcome.template,
    )
    assert run.status == "completed"
    assert run.canonical_template is not None
    assert run.canonical_template.payload["portable_export_binding"]["raw_source_sha256"] == artifact.sha256


def test_portable_export_binding_rejects_symlinks_and_private_exports(tmp_path: Path) -> None:
    raw = tmp_path / "sample.opju"
    raw.write_bytes(b"CPYUA opaque")
    exported = tmp_path / "sample.csv"
    exported.write_text("Temperature (C),Mass (%)\n25,100\n100,98\n", encoding="utf-8")

    with pytest.raises(ValueError, match="supported"):
        PortableExportBinding.create(raw, tmp_path / "sample.opju", exporter="Origin")
    with pytest.raises(ValueError, match="exporter"):
        PortableExportBinding.create(raw, exported, exporter=" ")

    symlink = tmp_path / "link.csv"
    try:
        symlink.symlink_to(exported)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable on this Windows runner")
    with pytest.raises(ValueError, match="symlink"):
        PortableExportBinding.create(raw, symlink, exporter="Origin")
