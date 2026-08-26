from __future__ import annotations

from polynexus.core.canonical_experiments import default_converter_registry


def test_registry_converts_supported_static_artifact_to_replayable_template(tmp_path) -> None:
    source = tmp_path / "sample.csv"
    source.write_text("Wavenumber,Absorbance\n1700,0.4\n1600,0.8\n", encoding="utf-8")

    outcome = default_converter_registry().convert_path(
        source,
        technique="ir",
        source_artifact_id="source-sha256",
    )

    assert outcome.status == "ready"
    assert outcome.template is not None
    assert outcome.template.template_id == "spectrum_1d.v1"
    assert outcome.template.source_artifact_id == "source-sha256"
    assert outcome.template.measurements[0].family == "spectrum_1d"
    assert outcome.template.conversion_record.conversion_id == "generic.one-dimensional.v1"


def test_registry_replay_reflects_different_source_content(tmp_path) -> None:
    source = tmp_path / "sample.csv"
    source.write_text("Wavenumber,Absorbance\n1700,0.4\n1600,0.8\n", encoding="utf-8")
    registry = default_converter_registry()
    original = registry.convert_path(source, technique="ir", source_artifact_id="source-sha256")
    source.write_text("Wavenumber,Absorbance\n1700,0.8\n1600,0.2\n", encoding="utf-8")

    replayed = registry.replay_path(source, technique="ir", source_artifact_id="source-sha256")

    assert original.template is not None
    assert replayed.template is not None
    assert replayed.template.content_hash != original.template.content_hash


def test_registry_preserves_generic_mapping_ambiguity(tmp_path) -> None:
    source = tmp_path / "ambiguous.csv"
    source.write_text("A,B,C\n1,2,3\n4,5,6\n", encoding="utf-8")

    outcome = default_converter_registry().convert_path(
        source,
        technique="ir",
        source_artifact_id="source-sha256",
    )

    assert outcome.status == "needs_input"
    assert outcome.template is None
    assert outcome.reason_codes == ("conversion_mapping_ambiguous",)


def test_registry_keeps_vendor_and_directory_compatibility_fallback(tmp_path) -> None:
    vendor_file = tmp_path / "sample.spa"
    vendor_file.write_bytes(b"vendor-bytes")
    vendor_dir = tmp_path / "vendor-export"
    vendor_dir.mkdir()
    (vendor_dir / "frame.bin").write_bytes(b"vendor-frame")

    registry = default_converter_registry()
    vendor = registry.convert_path(vendor_file, technique="ir", source_artifact_id="vendor-file")
    directory = registry.convert_path(vendor_dir, technique="saxs", source_artifact_id="vendor-dir")

    assert vendor.status == "ready"
    assert vendor.template is not None
    assert vendor.template.template_id == "ir.spectrum.v1"
    assert directory.status == "ready"
    assert directory.template is not None
    assert directory.template.template_id == "saxs.profile.v1"


def test_registry_blocks_an_unregistered_technique(tmp_path) -> None:
    source = tmp_path / "sample.nmr"
    source.write_text("raw", encoding="utf-8")

    outcome = default_converter_registry().convert_path(
        source,
        technique="nmr",
        source_artifact_id="source-sha256",
    )

    assert outcome.status == "blocked"
    assert outcome.template is None
    assert outcome.reason_codes == ("canonical_converter_unregistered",)
