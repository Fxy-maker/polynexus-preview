from polynexus.gui.results_table_service import build_batch_results_table_model, build_results_table_model


def _flatten(params):
    if not isinstance(params, dict):
        return []
    return [(key, value) for key, value in params.items() if not str(key).startswith("_")]


def test_build_results_table_model_preserves_generic_single_and_batch_rows():
    single = build_results_table_model(
        {"L_nm": 12.0, "Xc": 0.31, "batch_frames": 1, "_private": 9},
        ordered_columns_fn=lambda columns: list(columns),
        flatten_params_fn=_flatten,
    )
    batch = build_batch_results_table_model(
        [{"file": "a.csv", "params": {"L_nm": 12.3}}, {"file": "b.csv", "params": {"Xc": 0.4}}],
        ordered_columns_fn=lambda columns: list(columns),
    )

    assert single.kind == "single"
    assert single.stored_rows == [["L_nm", 12.0], ["Xc", 0.31], ["batch_frames", 1]]
    assert batch.kind == "batch"
    assert batch.columns == ["file", "L_nm", "Xc"]
    assert batch.stored_rows == [["a.csv", 12.3, ""], ["b.csv", "", 0.4]]


def test_build_results_table_model_dispatches_structured_saxs_presentation():
    model = build_results_table_model(
        {"L_nm": 12.0},
        ordered_columns_fn=lambda columns: list(columns),
        flatten_params_fn=_flatten,
        technique="saxs",
        submodule="static",
    )

    assert model.kind == "saxs.static"
    assert model.primary_section is not None
    assert model.detail_section is not None
    assert model.diagnostic_section is not None


def test_build_results_table_model_dispatches_structured_analysis_presentation():
    model = build_results_table_model(
        {"scan": "s1", "Tg_C": 72.0},
        ordered_columns_fn=lambda columns: list(columns),
        flatten_params_fn=_flatten,
        technique="dsc",
        submodule="dsc.standard",
    )

    assert model.kind == "dsc.standard"
    assert model.primary_section is not None
    assert model.diagnostic_section is not None
