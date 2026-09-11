from __future__ import annotations

from pathlib import Path
import struct
import zipfile

import pytest

from polynexus.core.canonical_experiments import default_converter_registry
from polynexus.core.compute.service import ComputeRunService
from polynexus.core.input_formats import inspect_format
from polynexus.readers.netzsch_ngb_reader import read_netzsch_dsc, read_netzsch_tga


def _block(marker: bytes, values: list[float], fmt: str) -> bytes:
    payload = struct.pack(f"<{len(values)}{fmt}", *values)
    return marker + struct.pack("<I", len(values)) + payload


def _dsc_fixture(path: Path) -> None:
    lengths = (4, 3, 5)
    stream = bytearray(b"\x00\x00Netzsch TA file\x00CDbTable\x00")
    for index, count in enumerate(lengths):
        stream.extend(_block(bytes.fromhex("05a001"), [float(index * 10 + n) / 3 for n in range(count)], "d"))
    for channel in range(4):
        for index, count in enumerate(lengths):
            if channel == 0:
                values = [100.0 + index * 10 + n for n in range(count)]
            elif channel == 1:
                values = [float(n) for n in range(count)]
            else:
                values = [30.0] * count
            stream.extend(_block(bytes.fromhex("04a001"), values, "f"))
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("Streams/stream_2.table", stream)
        archive.writestr("Streams/stream_6.table", "time /min, all segments\x00Temperature /°C\x00DSC /(mW/mg) exo+\x00Gas /ml/min\x00")


def _tga_fixture(path: Path) -> None:
    count = 120
    time = [float(n) for n in range(count)]
    temperature = [35.0 + n * 8.0 for n in range(count)]
    mass = [100.0 - n * 0.2 for n in range(count)]
    payload = bytearray(
        b"\x00\x00Netzsch TA file\x00_db_format_1\x00CDbTable\x00TG /mg\x00"
    )
    payload.extend(_block(bytes.fromhex("04a001"), time, "f"))
    payload.extend(_block(bytes.fromhex("04a001"), temperature, "f"))
    payload.extend(_block(bytes.fromhex("05a001"), mass, "d"))
    path.write_bytes(payload)


def test_observed_dsc_reader_preserves_segments_and_units(tmp_path: Path) -> None:
    source = tmp_path / "sample.ngb-sd7"
    _dsc_fixture(source)

    decoded = read_netzsch_dsc(source)

    assert [len(segment.time_min) for segment in decoded.segments] == [4, 3, 5]
    assert decoded.segments[0].dsc_mw_per_mg == (0.0, 1.0, 2.0, 3.0)
    assert "DSC /(mW/mg) exo+" in decoded.labels

    outcome = default_converter_registry().convert_path(
        source, technique="dsc", source_artifact_id="raw-dsc"
    )
    assert outcome.status == "ready"
    assert outcome.template is not None
    assert outcome.template.payload["heat_flow_unit"] == "mW/mg"
    assert outcome.template.payload["sample"]["mass_mg"] is None


def test_observed_tga_reader_replays_through_compute(tmp_path: Path) -> None:
    source = tmp_path / "sample.ngb-ds1"
    _tga_fixture(source)

    decoded = read_netzsch_tga(source)
    assert len(decoded.segments) == 1
    assert decoded.segments[0].temperature_c[-1] > 900.0
    assert decoded.segments[0].tg_mg[0] == 100.0
    assert decoded.segments[0].mass_mg == decoded.segments[0].tg_mg

    inspection = inspect_format(source, technique="tga")
    assert inspection.status == "ready"
    outcome = default_converter_registry().convert_path(
        source, technique="tga", source_artifact_id="raw-tga"
    )
    assert outcome.status == "ready"
    assert outcome.template is not None
    assert outcome.template.conversion_record is not None
    assert outcome.template.conversion_record.warnings == (
        "unassigned_channels_retained_in_acquisition_metadata",
        "tg_channel_may_be_signed_or_zero_referenced",
    )
    measurement = outcome.template.measurements[0]
    assert measurement.acquisition_metadata["signal_kind"] == "tg_reported_mass"
    assert measurement.acquisition_metadata["absolute_mass_available"] is False
    run = ComputeRunService().run_direct(
        technique="tga",
        path=source,
        output_dir="",
        canonical_template=outcome.template,
        source_artifact_id="raw-tga",
    )
    assert run.status == "completed"


def test_observed_tga_requires_declared_tg_channel(tmp_path: Path) -> None:
    source = tmp_path / "missing-label.ngb-ds1"
    _tga_fixture(source)
    source.write_bytes(source.read_bytes().replace(b"TG /mg\x00", b"unassigned\x00"))

    with pytest.raises(ValueError, match="does not declare a TG /mg channel"):
        read_netzsch_tga(source)


def test_ngb_reader_fails_closed_on_truncated_source(tmp_path: Path) -> None:
    source = tmp_path / "truncated.ngb-ds1"
    source.write_bytes(b"\x00\x00Netzsch TA file\x00_db_format_1\x00CDbTable\x00")

    with pytest.raises(ValueError, match="recognized NETZSCH TGA|observed time/temperature/mass"):
        read_netzsch_tga(source)

    inspection = inspect_format(source, technique="tga")
    assert inspection.status == "needs_reader"
    assert inspection.reason_codes == ("format_signature_unrecognized",)
