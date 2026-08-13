from __future__ import annotations

from polynexus.core.canonical_experiments import default_converter_registry


def test_registry_converts_supported_static_artifact_to_replayable_template(tmp_path) -> None:
    source = tmp_path / "sample.csv"
    source.write_text("Wavenumber,Absorbance\n1700,0.4\n", encoding="utf-8")

    outcome = default_converter_registry().convert_path(
        source,
        technique="ir",
        source_artifact_id="source-sha256",
    )

    assert outcome.status == "ready"
    assert outcome.template is not None
    assert outcome.template.template_id == "ir.spectrum.v1"
    assert outcome.template.source_artifact_id == "source-sha256"
    assert outcome.template.conversion_record.conversion_id == "raw-file-envelope.ir.v1"


def test_registry_replay_reflects_different_source_content(tmp_path) -> None:
    source = tmp_path / "sample.csv"
    source.write_text("Wavenumber,Absorbance\n1700,0.4\n", encoding="utf-8")
    registry = default_converter_registry()
    original = registry.convert_path(source, technique="ir", source_artifact_id="source-sha256")
    source.write_text("Wavenumber,Absorbance\n1700,0.8\n", encoding="utf-8")

    replayed = registry.replay_path(source, technique="ir", source_artifact_id="source-sha256")

    assert original.template is not None
    assert replayed.template is not None
    assert replayed.template.content_hash != original.template.content_hash


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
