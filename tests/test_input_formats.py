from __future__ import annotations

import json
from pathlib import Path
import zipfile

from polynexus.core.compute import ComputeRunService
from polynexus.core.input_formats import (
    FormatInspection,
    FormatPluginDescriptor,
    default_format_registry,
    inspect_format,
)


def test_portable_table_inspection_is_deterministic_and_json_safe(tmp_path: Path) -> None:
    source = tmp_path / "curve.csv"
    source.write_text("temperature,mass\n25,100\n100,98\n", encoding="utf-8")

    first = inspect_format(source, technique="tga")
    second = inspect_format(source, technique="tga")

    assert first == second
    assert first.status == "ready"
    assert first.container_kind == "delimited_table"
    assert first.plugin_id == "portable.table.v1"
    assert first.canonical_conversion == "candidate"
    assert first.scientific_mapping == "unassessed"
    assert json.loads(json.dumps(first.to_dict(), sort_keys=True)) == first.to_dict()
    assert FormatInspection.from_dict(first.to_dict()) == first


def test_plugin_descriptor_round_trips() -> None:
    descriptor = default_format_registry().descriptor("portable.table.v1")

    assert descriptor is not None
    assert FormatPluginDescriptor.from_dict(descriptor.to_dict()) == descriptor


def test_registry_extension_is_explicit_and_never_loads_code() -> None:
    base = default_format_registry()
    extension = FormatPluginDescriptor(
        plugin_id="acme.reader.v1",
        version="1",
        container_kind="acme_binary",
        techniques=("tga",),
        extensions=(".acme",),
        reader_availability="missing",
        canonical_conversion="unavailable",
        next_actions=("install_or_enable_reader:acme.reader.v1",),
    )

    extended = base.with_plugin(extension)

    assert base.descriptor("acme.reader.v1") is None
    assert extended.descriptor("acme.reader.v1") == extension


def test_netzsch_vendor_inputs_report_missing_decoder_without_execution(
    tmp_path: Path,
) -> None:
    source = tmp_path / "sample.ngb-ds1"
    source.write_bytes(b"\x00\x00Netzsch TA file\x00_db_format_1\x00" + b"\x00" * 80)

    inspection = inspect_format(source, technique="tga")

    assert inspection.status == "needs_reader"
    assert inspection.plugin_id == "netzsch.ta.v1"
    assert inspection.container_kind == "netzsch_ta_binary"
    assert inspection.reader_availability == "missing"
    assert inspection.reason_codes == ("format_reader_missing",)
    assert inspection.next_actions == (
        "install_or_enable_reader:netzsch.ta.v1",
        "export_portable_table",
    )

    class ExplodingEngine:
        def run_pipeline(self, *args, **kwargs):  # pragma: no cover - must not run
            raise AssertionError("opaque vendor input reached provider execution")

    run = ComputeRunService().run_direct(
        technique="tga",
        path=source,
        output_dir=tmp_path / "out",
        engine=ExplodingEngine(),
    )

    assert run.status == "needs_input"
    assert run.reasons == ("format_reader_missing",)
    assert run.input_inspection == inspection


def test_origin_project_and_vendor_dma_are_actionable(tmp_path: Path) -> None:
    origin = tmp_path / "chromatogram.opju"
    origin.write_bytes(b"CPYUA 4.3551 171\n" + b"\x00" * 80)
    dma = tmp_path / "sweep.001"
    dma.write_bytes("CLOSED\r\nVERSION 2.0\r\nLanguage English\r\n".encode("utf-16"))

    origin_inspection = inspect_format(origin, technique="sec")
    dma_inspection = inspect_format(dma, technique="dma")

    assert origin_inspection.plugin_id == "origin.project.v1"
    assert origin_inspection.status == "needs_reader"
    assert origin_inspection.next_actions[-1] == "export_portable_table"
    assert dma_inspection.plugin_id == "vendor.dma.001.v1"
    assert dma_inspection.status == "needs_reader"


def test_opaque_reader_boundary_survives_a_wrong_declared_technique(
    tmp_path: Path,
) -> None:
    source = tmp_path / "chromatogram.opju"
    source.write_bytes(b"CPYUA 4.3551 171\n" + b"\x00" * 80)

    inspection = inspect_format(source, technique="tga")

    assert inspection.status == "needs_reader"
    assert inspection.reason_codes == (
        "external_reader_required",
        "technique_confirmation_required",
    )

    class ExplodingEngine:
        def run_pipeline(self, *args, **kwargs):  # pragma: no cover - must not run
            raise AssertionError("opaque project input reached provider execution")

    run = ComputeRunService().run_direct(
        technique="tga",
        path=source,
        output_dir=tmp_path / "out",
        engine=ExplodingEngine(),
    )

    assert run.status == "needs_input"
    assert run.reasons == inspection.reason_codes
    assert run.input_inspection == inspection


def test_dsc_vendor_zip_is_not_misclassified_as_generic_zip(tmp_path: Path) -> None:
    source = tmp_path / "sample.ngb-sd7"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("Streams/stream_1.table", b"binary table bytes")
        archive.writestr("Streams/Props.xml", "<Properties />")

    inspection = inspect_format(source, technique="dsc")

    assert inspection.plugin_id == "netzsch.dsc.container.v1"
    assert inspection.container_kind == "netzsch_dsc_container"
    assert inspection.observed_facts["archive_member_count"] == 2
    assert inspection.observed_facts["stream_table_count"] == 1
    assert inspection.status == "needs_reader"


def test_rigaku_route_requires_the_supported_binary_signature(tmp_path: Path) -> None:
    unrecognized = tmp_path / "other_vendor.raw"
    unrecognized.write_bytes(b"OTHER-RAW\x00" + b"\x00" * 64)
    rigaku = tmp_path / "rigaku.raw"
    rigaku.write_bytes(b"RAW1.01\x00" + b"\x00" * 1024)

    assert inspect_format(unrecognized, technique="waxs").plugin_id is None
    inspection = inspect_format(rigaku, technique="waxs")
    assert inspection.plugin_id == "rigaku.raw.v1"
    assert inspection.status == "ready"


def test_detector_image_and_bruker_directory_have_registered_routes(tmp_path: Path) -> None:
    image = tmp_path / "frame.tif"
    image.write_bytes(b"II*\x00" + b"\x00" * 64)
    bruker = tmp_path / "bruker"
    bruker.mkdir()
    (bruker / "acqus").write_text("##$NUC1= <13C>\n", encoding="latin-1")
    (bruker / "fid").write_bytes(b"\x00" * 128)

    image_inspection = inspect_format(image, technique="saxs")
    bruker_inspection = inspect_format(bruker, technique="nmr")

    assert image_inspection.plugin_id == "detector.image.v1"
    assert image_inspection.status == "ready"
    assert bruker_inspection.plugin_id == "bruker.nmr.v1"
    assert bruker_inspection.status == "ready"
    assert bruker_inspection.observed_facts["fid_present"] is True
    assert bruker_inspection.observed_facts["acquisition_metadata_present"] is True


def test_unknown_binary_remains_compatible_but_uninterpreted(tmp_path: Path) -> None:
    source = tmp_path / "mystery.bin"
    source.write_bytes(b"\x00\xff\x13\x99" * 32)

    inspection = default_format_registry().inspect(source, technique="ir")

    assert inspection.status == "unknown"
    assert inspection.plugin_id is None
    assert inspection.reader_availability == "unknown"
    assert inspection.canonical_conversion == "unavailable"
    assert inspection.next_actions == ("select_reader_plugin", "export_portable_table")


def test_gpc_alias_produces_the_same_origin_inspection_as_sec(tmp_path: Path) -> None:
    source = tmp_path / "chromatogram.opju"
    source.write_bytes(b"CPYUA 4.3551 171\n" + b"\x00" * 80)

    assert inspect_format(source, technique="gpc") == inspect_format(source, technique="sec")


def test_wrong_technique_spreadsheet_requires_semantic_confirmation(tmp_path: Path) -> None:
    source = tmp_path / "ellipsometry.ods"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("mimetype", "application/vnd.oasis.opendocument.spreadsheet")
        archive.writestr("content.xml", "<office:document-content />")

    inspection = inspect_format(source, technique="mechanics")

    assert inspection.plugin_id == "portable.ods.v1"
    assert inspection.status == "needs_mapping"
    assert inspection.reader_availability == "available"
    assert "technique_confirmation_required" in inspection.reason_codes
    assert inspection.scientific_mapping == "unassessed"
