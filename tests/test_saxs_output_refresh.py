from __future__ import annotations

from pathlib import Path

from polynexus.core.saxs_engine.saxs_output import _remove_stale_variant


def test_remove_stale_variant_drops_low_counterpart(tmp_path):
    refreshed = tmp_path / "03_IDF.pdf"
    stale_low = tmp_path / "03_IDF_LOW.pdf"
    refreshed.write_bytes(b"new")
    stale_low.write_bytes(b"old")

    _remove_stale_variant(refreshed)

    assert refreshed.exists()
    assert not stale_low.exists()


def test_remove_stale_variant_drops_non_low_counterpart(tmp_path):
    refreshed_low = tmp_path / "02_correlation_function_LOW.pdf"
    stale_plain = tmp_path / "02_correlation_function.pdf"
    refreshed_low.write_bytes(b"new")
    stale_plain.write_bytes(b"old")

    _remove_stale_variant(refreshed_low)

    assert refreshed_low.exists()
    assert not stale_plain.exists()
