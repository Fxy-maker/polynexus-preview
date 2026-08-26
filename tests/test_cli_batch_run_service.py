from types import SimpleNamespace

from polynexus.cli.batch_run_service import allowed_extensions, extract_result_r2, run_batch_one


def test_allowed_extensions_uses_engine_specific_formats():
    extensions = allowed_extensions("saxs")
    assert {".dat", ".edf", ".txt", ".nxs", ".h5"}.issubset(extensions)
    assert ".csv" in extensions


def test_extract_result_r2_reads_common_result_shapes():
    assert extract_result_r2(SimpleNamespace(r_squared=0.98)) == 0.98
    assert extract_result_r2({"r_squared": "0.97"}) == 0.97
    assert extract_result_r2({"parameters": {"r2": 0.96}}) == 0.96


class _LegacyResult:
    parameters = {"r_squared": 0.98}
    figures = {}
    metadata = {}


class _Engine:
    def __init__(self):
        self.calls = []

    def run_pipeline(self, path, output_dir, **options):
        self.calls.append((path, output_dir, options))
        return _LegacyResult()


def test_batch_one_uses_shared_compute_run_and_exposes_canonical_items(tmp_path):
    source = tmp_path / "curve.csv"
    source.write_text("Wavenumber,Absorbance\n1700,0.4\n1600,0.8\n", encoding="utf-8")
    output = tmp_path / "out"
    engine = _Engine()
    persisted = []

    row = run_batch_one(
        (str(source), "ir", str(output)),
        get_engine_fn=lambda technique: engine,
        persist_batch_run_fn=lambda *args: persisted.append(args),
        logger=SimpleNamespace(warning=lambda *args, **kwargs: None),
    )

    assert row["status"] == "OK"
    assert row["r2"] == 0.98
    assert row["compute_run"].canonical_template.template_id == "spectrum_1d.v1"
    assert len(row["compute_run"].capability_items) == 2
    assert persisted[0][2] is row["compute_run"]


def test_batch_one_blocks_ambiguous_generic_input_before_provider(tmp_path):
    source = tmp_path / "ambiguous.csv"
    source.write_text("A,B,C\n1,2,3\n4,5,6\n", encoding="utf-8")
    engine = _Engine()

    row = run_batch_one(
        (str(source), "ir", str(tmp_path / "out")),
        get_engine_fn=lambda technique: engine,
        persist_batch_run_fn=lambda *args: None,
        logger=SimpleNamespace(warning=lambda *args, **kwargs: None),
    )

    assert row["status"].startswith("FAIL:")
    assert "conversion_mapping_ambiguous" in row["status"]
    assert row["compute_run"].status == "needs_input"
    assert engine.calls == []
