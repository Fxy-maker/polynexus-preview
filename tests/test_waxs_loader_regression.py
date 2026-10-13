from __future__ import annotations

from pathlib import Path

from polynexus.core.waxs_engine.io import load_scan


def test_waxs_load_scan_accepts_shared_profile_reader_metadata(tmp_path: Path) -> None:
    source = tmp_path / "sample.dat"
    source.write_text("0.05 10\n0.10 20\n0.15 15\n", encoding="utf-8")

    scan = load_scan(str(source))

    assert scan.label == "sample"
    assert len(scan.q_Ainv) == 3
    assert len(scan.I_arb) == 3
    assert scan.metadata["q_unit_reason"] == "q_unit_required"
