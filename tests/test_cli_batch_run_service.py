from types import SimpleNamespace

from polynexus.cli.batch_run_service import allowed_extensions, extract_result_r2


def test_allowed_extensions_uses_engine_specific_formats():
    extensions = allowed_extensions("saxs")
    assert {".dat", ".edf", ".txt", ".nxs", ".h5"}.issubset(extensions)
    assert ".csv" in extensions


def test_extract_result_r2_reads_common_result_shapes():
    assert extract_result_r2(SimpleNamespace(r_squared=0.98)) == 0.98
    assert extract_result_r2({"r_squared": "0.97"}) == 0.97
    assert extract_result_r2({"parameters": {"r2": 0.96}}) == 0.96
