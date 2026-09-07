from __future__ import annotations

import struct
from pathlib import Path

import pytest

from polynexus.core.canonical_experiments import default_converter_registry
from polynexus.core.compute import ComputeRunService
from polynexus.core.input_formats import inspect_format
from polynexus.readers.ta_dma_reader import read_ta_dma


def _write_q800(path: Path, *, rows: tuple[tuple[float, ...], ...]) -> Path:
    header = (
        "CLOSED\r\n"
        "Instrument DMA Q800 V7.5 Build 127\r\n"
        "Nsig 5\r\n"
        "Sig1 Time (min)\r\n"
        "Sig2 Temperature (°C)\r\n"
        "Sig3 Storage Modulus (MPa)\r\n"
        "Sig4 Loss Modulus (MPa)\r\n"
        "Sig5 Tan Delta\r\n"
    ).encode("utf-16") + "\x0c".encode("utf-16")
    payload = bytes([5]) + b"".join(struct.pack("<5f", *row) for row in rows)
    path.write_bytes(header + payload + struct.pack("<5f", -1.0, -100.0, -100.0, -100.0, -100.0))
    return path


def test_ta_dma_reader_decodes_all_declared_channels_and_excludes_sentinel(tmp_path: Path) -> None:
    source = _write_q800(
        tmp_path / "sample.001",
        rows=((0.0, 25.0, 10.0, 2.0, 0.2), (1.0, 40.0, 8.0, 3.0, 0.375)),
    )

    decoded = read_ta_dma(source)

    assert decoded.headers == (
        "Time (min)",
        "Temperature (°C)",
        "Storage Modulus (MPa)",
        "Loss Modulus (MPa)",
        "Tan Delta",
    )
    assert decoded.rows[0] == pytest.approx((0.0, 25.0, 10.0, 2.0, 0.2))
    assert decoded.rows[1] == pytest.approx((1.0, 40.0, 8.0, 3.0, 0.375))


def test_ta_dma_binary_routes_to_canonical_and_compute_run(tmp_path: Path) -> None:
    source = _write_q800(
        tmp_path / "sample.001",
        rows=((0.0, 25.0, 10.0, 2.0, 0.2), (1.0, 40.0, 8.0, 3.0, 0.375)),
    )

    inspection = inspect_format(source, technique="dma")
    outcome = default_converter_registry().convert_path(
        source, technique="dma", source_artifact_id="dma-artifact"
    )

    assert inspection.status == "ready"
    assert inspection.plugin_id == "vendor.dma.001.v1"
    assert outcome.status == "ready"
    assert outcome.template is not None
    assert outcome.template.template_id == "dma_curve_1d.v1"
    assert len(outcome.template.measurements) == 4
    assert {item.acquisition_metadata["signal_kind"] for item in outcome.template.measurements} == {
        "temperature",
        "storage_modulus",
        "loss_modulus",
        "tan_delta",
    }

    run = ComputeRunService().run_direct(
        technique="dma",
        path=source,
        output_dir="",
    )
    assert run.status == "completed"
    assert run.canonical_template is not None
    assert run.canonical_template.template_id == "dma_curve_1d.v1"


def test_ta_dma_malformed_binary_fails_closed_before_engine(tmp_path: Path) -> None:
    source = tmp_path / "broken.001"
    source.write_bytes(
        "CLOSED\r\nInstrument DMA Q800\r\nNsig 1\r\nSig1 Time (min)\r\n".encode("utf-16")
        + "\x0c".encode("utf-16")
        + b"\x01\x00"
    )

    class ExplodingEngine:
        def load(self, *_args, **_kwargs):
            raise AssertionError("malformed TA DMA must not reach provider execution")

    run = ComputeRunService().run_direct(
        technique="dma", path=source, output_dir="", engine=ExplodingEngine()
    )
    assert run.status == "needs_input"
    assert "ta_dma" in " ".join(run.reasons)
