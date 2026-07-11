import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np

from polynexus.core.dsc_engine.core import DSCResult
from polynexus.core.dsc_engine.dsc_kinetics import AvramiResult, NonIsothermalResult
from polynexus.core.dsc_engine.dsc_output import (
    fig_d1_full_curve,
    fig_d2_tg_zoom,
    fig_d3_crystallinity,
    fig_d4_avrami,
    fig_d5_kissinger,
    fig_d6_deconvolution,
    fig_batch_cooling_overlay,
    fig_batch_crystallinity,
    fig_batch_heating_overlay,
)
from polynexus.core.figure_document import load_figure_document
from polynexus.core.plot_edits import load_figure_document_path


def test_dsc_full_curve_writes_editable_document(tmp_path):
    result = DSCResult(
        label="sample-dsc",
        T=np.array([25.0, 50.0, 75.0, 100.0]),
        HF=np.array([0.1, 0.2, 0.15, 0.05]),
        Tg_C=55.0,
        Tm_peak_C=82.0,
    )

    figure_path = fig_d1_full_curve(result, str(tmp_path))
    document = load_figure_document(figure_path)

    assert figure_path
    assert document["mode"] == "object"
    assert document["technique"] == "dsc"
    assert document["figure_id"] == "Fig-D1_full_curve"
    assert document["recipe"]["module"] == "polynexus.core.dsc_engine.dsc_output"
    assert document["recipe"]["function"] == "fig_d1_full_curve"
    assert document["recipe"]["inputs"]["result_label"] == "sample-dsc"
    assert document["data_sources"][0]["role"] == "plot_data"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert document["objects"][0]["type"] == "plot_series"
    assert document["objects"][0]["data_ref"] == document["data_sources"][0]["id"]
    assert load_figure_document_path(figure_path).endswith(".pnfig.json")


def test_dsc_tg_zoom_writes_editable_document(tmp_path):
    result = DSCResult(
        label="sample-dsc-tg",
        T=np.array([20.0, 35.0, 50.0, 65.0, 80.0, 95.0]),
        HF=np.array([0.05, 0.08, 0.14, 0.19, 0.17, 0.12]),
        Tg_C=62.0,
        Tg_method="midpoint",
        DTg_C=12.5,
    )

    figure_path = fig_d2_tg_zoom(result, str(tmp_path))
    document = load_figure_document(figure_path)

    assert figure_path
    assert document["mode"] == "object"
    assert document["technique"] == "dsc"
    assert document["figure_id"] == "Fig-D2_Tg_zoom"
    assert document["recipe"]["module"] == "polynexus.core.dsc_engine.dsc_output"
    assert document["recipe"]["function"] == "fig_d2_tg_zoom"
    assert document["recipe"]["inputs"]["result_label"] == "sample-dsc-tg"
    assert document["recipe"]["parameters"]["Tg_C"] == 62.0
    assert document["recipe"]["parameters"]["Tg_method"] == "midpoint"
    assert document["recipe"]["parameters"]["DTg_C"] == 12.5
    assert document["data_sources"][0]["role"] == "plot_data"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert [obj["type"] for obj in document["objects"]] == ["plot_series", "line"]
    assert document["objects"][0]["data_ref"] == document["data_sources"][0]["id"]
    assert document["objects"][1]["orientation"] == "vertical"
    assert load_figure_document_path(figure_path).endswith(".pnfig.json")


def test_dsc_crystallinity_writes_editable_document(tmp_path):
    results = [
        DSCResult(label="sample-a/heat 30-220C", Xc_pct=28.0, Xc_method="enthalpy"),
        DSCResult(label="sample-b/cool 220-30C", Xc_pct=34.5, Xc_method="enthalpy"),
    ]

    figure_path = fig_d3_crystallinity(results, str(tmp_path))
    document = load_figure_document(figure_path)

    assert figure_path
    assert document["mode"] == "object"
    assert document["technique"] == "dsc"
    assert document["figure_id"] == "Fig-D3_crystallinity"
    assert document["recipe"]["module"] == "polynexus.core.dsc_engine.dsc_output"
    assert document["recipe"]["function"] == "fig_d3_crystallinity"
    assert document["recipe"]["inputs"]["result_labels"] == [
        "sample-a/heat 30-220C",
        "sample-b/cool 220-30C",
    ]
    assert document["recipe"]["parameters"]["sample_count"] == 2
    assert document["data_sources"][0]["role"] == "plot_data"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert [obj["type"] for obj in document["objects"]] == ["plot_series"]
    assert document["objects"][0]["chart_kind"] == "bar"
    assert document["objects"][0]["x_column"] == "label"
    assert document["objects"][0]["y_column"] == "Xc_pct"
    assert load_figure_document_path(figure_path).endswith(".pnfig.json")


def test_dsc_avrami_writes_editable_document(tmp_path):
    avrami = AvramiResult(
        label="iso-120C",
        n=2.1,
        log_k=-1.3,
        k=0.05,
        t_half_min=8.4,
        r_squared=0.97,
        temperature_C=120.0,
        t_data=np.array([1.0, 2.0, 4.0, 8.0]),
        Xt_data=np.array([0.05, 0.18, 0.55, 0.86]),
        Xt_fit=np.array([0.04, 0.20, 0.52, 0.88]),
    )

    figure_path = fig_d4_avrami(avrami, str(tmp_path))
    document = load_figure_document(figure_path)

    assert figure_path
    assert document["mode"] == "object"
    assert document["technique"] == "dsc"
    assert document["figure_id"] == "Fig-D4_avrami"
    assert document["recipe"]["module"] == "polynexus.core.dsc_engine.dsc_output"
    assert document["recipe"]["function"] == "fig_d4_avrami"
    assert document["recipe"]["inputs"]["label"] == "iso-120C"
    assert document["recipe"]["parameters"]["n"] == 2.1
    assert document["recipe"]["parameters"]["k"] == 0.05
    assert document["recipe"]["parameters"]["t_half_min"] == 8.4
    assert document["data_sources"][0]["role"] == "plot_data"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert [obj["type"] for obj in document["objects"]] == [
        "plot_series",
        "plot_series",
        "plot_series",
        "plot_series",
    ]
    assert document["objects"][0]["y_column"] == "Xt_pct"
    assert document["objects"][1]["y_column"] == "Xt_fit_pct"
    assert document["objects"][2]["x_column"] == "ln_t"
    assert document["objects"][3]["y_column"] == "avrami_fit"
    assert load_figure_document_path(figure_path).endswith(".pnfig.json")


def test_dsc_kissinger_writes_editable_document(tmp_path):
    kissinger = NonIsothermalResult(
        method="Kissinger",
        kissinger_Ea_kJmol=82.0,
        r_squared=0.94,
    )

    figure_path = fig_d5_kissinger(
        kissinger,
        Tp_C_list=[145.0, 152.0, 160.0],
        rates=[5.0, 10.0, 20.0],
        output_dir=str(tmp_path),
    )
    document = load_figure_document(figure_path)

    assert figure_path
    assert document["mode"] == "object"
    assert document["technique"] == "dsc"
    assert document["figure_id"] == "Fig-D5_kissinger"
    assert document["recipe"]["module"] == "polynexus.core.dsc_engine.dsc_output"
    assert document["recipe"]["function"] == "fig_d5_kissinger"
    assert document["recipe"]["inputs"]["method"] == "Kissinger"
    assert document["recipe"]["parameters"]["point_count"] == 3
    assert "slope" in document["recipe"]["parameters"]
    assert "Ea_kJmol" in document["recipe"]["parameters"]
    assert document["data_sources"][0]["role"] == "plot_data"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert [obj["type"] for obj in document["objects"]] == ["plot_series", "plot_series"]
    assert document["objects"][0]["x_column"] == "inv_Tp_K_1000"
    assert document["objects"][1]["y_column"] == "fit"
    assert load_figure_document_path(figure_path).endswith(".pnfig.json")


def test_dsc_deconvolution_writes_editable_document(tmp_path):
    result = DSCResult(
        label="sample-deconv",
        T=np.array([100.0, 120.0, 140.0, 160.0, 180.0]),
        HF=np.array([0.1, 0.4, 0.9, 0.5, 0.2]),
        peak_components=[
            {
                "type": "deconv_melting",
                "mu_C": 130.0,
                "sigma_C": 8.0,
                "amp": 0.7,
                "fraction": 0.55,
            },
            {
                "type": "deconv_melting",
                "mu_C": 160.0,
                "sigma_C": 10.0,
                "amp": 0.5,
                "fraction": 0.45,
            },
        ],
    )

    figure_path = fig_d6_deconvolution(result, str(tmp_path))
    document = load_figure_document(figure_path)

    assert figure_path
    assert document["mode"] == "object"
    assert document["technique"] == "dsc"
    assert document["figure_id"] == "Fig-D6_deconvolution"
    assert document["recipe"]["module"] == "polynexus.core.dsc_engine.dsc_output"
    assert document["recipe"]["function"] == "fig_d6_deconvolution"
    assert document["recipe"]["inputs"]["result_label"] == "sample-deconv"
    assert document["recipe"]["parameters"]["component_count"] == 2
    assert document["data_sources"][0]["role"] == "plot_data"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert [obj["type"] for obj in document["objects"]] == [
        "plot_series",
        "plot_series",
        "plot_series",
    ]
    assert document["objects"][0]["y_column"] == "heat_flow_W_g"
    assert document["objects"][1]["y_column"] == "component_1"
    assert document["objects"][2]["y_column"] == "component_2"
    assert load_figure_document_path(figure_path).endswith(".pnfig.json")


def test_dsc_batch_heating_overlay_writes_editable_document(tmp_path):
    results = [
        DSCResult(
            label="sample-a/heat",
            technique="heating",
            T=np.array([30.0, 80.0, 130.0]),
            HF=np.array([0.1, 0.5, 0.2]),
            Tm_peak_C=82.0,
        ),
        DSCResult(
            label="sample-b/heat",
            technique="heating",
            T=np.array([30.0, 80.0, 130.0]),
            HF=np.array([0.2, 0.6, 0.3]),
            Tm_peak_C=85.0,
        ),
    ]

    figure_path = fig_batch_heating_overlay(results, str(tmp_path))
    document = load_figure_document(figure_path)

    assert document["mode"] == "object"
    assert document["technique"] == "dsc"
    assert document["figure_id"] == "Fig-D7_heating_overlay"
    assert document["recipe"]["function"] == "fig_batch_heating_overlay"
    assert document["recipe"]["parameters"]["sample_count"] == 2
    assert document["data_sources"][0]["role"] == "plot_data"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert document["objects"][0]["type"] == "plot_series"
    assert document["objects"][0]["x_column"] == "temperature_C"
    assert document["objects"][0]["y_column"] == "heat_flow_offset"
    assert load_figure_document_path(figure_path).endswith(".pnfig.json")


def test_dsc_batch_cooling_overlay_writes_editable_document(tmp_path):
    results = [
        DSCResult(
            label="sample-a/cool",
            technique="cooling",
            T=np.array([180.0, 140.0, 100.0]),
            HF=np.array([0.1, -0.4, 0.0]),
            Tc_peak_C=142.0,
        ),
        DSCResult(
            label="sample-b/cool",
            technique="cooling",
            T=np.array([180.0, 140.0, 100.0]),
            HF=np.array([0.0, -0.5, -0.1]),
            Tc_peak_C=138.0,
        ),
    ]

    figure_path = fig_batch_cooling_overlay(results, str(tmp_path))
    document = load_figure_document(figure_path)

    assert document["mode"] == "object"
    assert document["technique"] == "dsc"
    assert document["figure_id"] == "Fig-D8_cooling_overlay"
    assert document["recipe"]["function"] == "fig_batch_cooling_overlay"
    assert document["recipe"]["parameters"]["sample_count"] == 2
    assert document["data_sources"][0]["role"] == "plot_data"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert document["objects"][0]["x_column"] == "temperature_C"
    assert document["objects"][0]["y_column"] == "heat_flow_offset"
    assert load_figure_document_path(figure_path).endswith(".pnfig.json")


def test_dsc_batch_crystallinity_writes_editable_document(tmp_path):
    results = [
        DSCResult(label="sample-a/heat", Xc_pct=29.0, Xc_method="enthalpy"),
        DSCResult(label="sample-b/heat", Xc_pct=41.5, Xc_method="enthalpy"),
    ]

    figure_path = fig_batch_crystallinity(results, str(tmp_path))
    document = load_figure_document(figure_path)

    assert document["mode"] == "object"
    assert document["technique"] == "dsc"
    assert document["figure_id"] == "Fig-D3_crystallinity_comparison"
    assert document["recipe"]["function"] == "fig_batch_crystallinity"
    assert document["recipe"]["parameters"]["sample_count"] == 2
    assert document["data_sources"][0]["role"] == "plot_data"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert [obj["type"] for obj in document["objects"]] == ["plot_series"]
    assert document["objects"][0]["chart_kind"] == "bar"
    assert document["objects"][0]["x_column"] == "label"
    assert document["objects"][0]["y_column"] == "Xc_pct"
    assert load_figure_document_path(figure_path).endswith(".pnfig.json")
