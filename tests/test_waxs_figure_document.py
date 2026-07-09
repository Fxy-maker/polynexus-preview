import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np

from polynexus.core.figure_document import load_figure_document
from polynexus.core.waxs_engine.core import WAXSResult
from polynexus.core.waxs_engine.waxs_strain import (
    WAXSStrainPhase,
    WAXSStrainPointResult,
    WAXSStrainSeriesResult,
)
from polynexus.core.waxs_engine.waxs_output import (
    fig_strain_lattice,
    fig_strain_2d_patterns_from_scans,
    fig_strain_parameters,
    fig_strain_waterfall,
    fig_w1_profile,
    fig_w2_amorphous,
    fig_w3_williamson_hall,
    fig_w4_crystallinity,
    fig_w5_scherrer,
)


def test_waxs_profile_figure_writes_editable_document(tmp_path):
    result = WAXSResult(
        label="sample-a",
        two_theta=np.array([10.0, 11.0, 12.0, 13.0]),
        I=np.array([100.0, 120.0, 115.0, 90.0]),
        I_fit=np.array([98.0, 118.0, 112.0, 92.0]),
        r_squared=0.95,
    )

    figure_path = fig_w1_profile(result, str(tmp_path))
    document = load_figure_document(figure_path)

    assert figure_path
    assert document["mode"] == "object"
    assert document["technique"] == "waxs"
    assert document["figure_id"] == "Fig-W1_profile"
    assert document["recipe"]["module"] == "polynexus.core.waxs_engine.waxs_output"
    assert document["recipe"]["function"] == "fig_w1_profile"
    assert document["recipe"]["inputs"]["result_label"] == "sample-a"
    assert document["data_sources"][0]["role"] == "plot_data"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert [obj["type"] for obj in document["objects"]] == ["plot_series", "plot_series"]
    assert document["objects"][0]["data_ref"] == document["data_sources"][0]["id"]


def test_waxs_amorphous_figure_writes_editable_document(tmp_path):
    result = WAXSResult(
        label="sample-b",
        two_theta=np.array([10.0, 11.0, 12.0, 13.0]),
        I=np.array([100.0, 120.0, 115.0, 90.0]),
        I_amorphous=np.array([60.0, 62.0, 58.0, 55.0]),
        I_crystalline=np.array([40.0, 58.0, 57.0, 35.0]),
        Xc_pct=42.5,
        Xc_method="area_ratio",
    )

    figure_path = fig_w2_amorphous(result, str(tmp_path))
    document = load_figure_document(figure_path)

    assert figure_path
    assert document["mode"] == "object"
    assert document["technique"] == "waxs"
    assert document["figure_id"] == "Fig-W2_amorphous"
    assert document["recipe"]["module"] == "polynexus.core.waxs_engine.waxs_output"
    assert document["recipe"]["function"] == "fig_w2_amorphous"
    assert document["recipe"]["inputs"]["result_label"] == "sample-b"
    assert document["recipe"]["parameters"]["Xc_pct"] == 42.5
    assert document["data_sources"][0]["role"] == "plot_data"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert [obj["type"] for obj in document["objects"]] == [
        "plot_series",
        "plot_series",
        "plot_series",
    ]
    assert document["objects"][1]["y_column"] == "amorphous"
    assert document["objects"][2]["y_column"] == "crystalline"


def test_waxs_williamson_hall_figure_writes_editable_document(tmp_path):
    result = WAXSResult(
        label="sample-wh",
        peaks=[
            {"two_theta": 15.0, "fwhm_deg": 0.32},
            {"two_theta": 22.0, "fwhm_deg": 0.44},
            {"two_theta": 30.0, "fwhm_deg": 0.63},
        ],
        D_WH_nm=12.3,
        epsilon_WH_pct=0.42,
        WH_fit_r_squared=0.91,
    )

    figure_path = fig_w3_williamson_hall(result, str(tmp_path))
    document = load_figure_document(figure_path)

    assert figure_path
    assert document["mode"] == "object"
    assert document["technique"] == "waxs"
    assert document["figure_id"] == "Fig-W3_williamson_hall"
    assert document["recipe"]["module"] == "polynexus.core.waxs_engine.waxs_output"
    assert document["recipe"]["function"] == "fig_w3_williamson_hall"
    assert document["recipe"]["inputs"]["result_label"] == "sample-wh"
    assert "slope" in document["recipe"]["parameters"]
    assert "intercept" in document["recipe"]["parameters"]
    assert document["data_sources"][0]["role"] == "plot_data"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert [obj["type"] for obj in document["objects"]] == [
        "plot_series",
        "plot_series",
    ]
    assert document["objects"][0]["x_column"] == "four_sin_theta"
    assert document["objects"][1]["y_column"] == "fit"


def test_waxs_crystallinity_figure_writes_editable_document(tmp_path):
    results = [
        WAXSResult(label="sample-a", Xc_pct=35.0, Xc_method="area_ratio"),
        WAXSResult(label="sample-b", Xc_pct=48.5, Xc_method="area_ratio"),
    ]

    figure_path = fig_w4_crystallinity(results, str(tmp_path))
    document = load_figure_document(figure_path)

    assert figure_path
    assert document["mode"] == "object"
    assert document["technique"] == "waxs"
    assert document["figure_id"] == "Fig-W4_crystallinity"
    assert document["recipe"]["module"] == "polynexus.core.waxs_engine.waxs_output"
    assert document["recipe"]["function"] == "fig_w4_crystallinity"
    assert document["recipe"]["inputs"]["result_labels"] == ["sample-a", "sample-b"]
    assert document["recipe"]["parameters"]["sample_count"] == 2
    assert document["data_sources"][0]["role"] == "plot_data"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert [obj["type"] for obj in document["objects"]] == ["plot_series"]
    assert document["objects"][0]["chart_kind"] == "bar"
    assert document["objects"][0]["x_column"] == "label"
    assert document["objects"][0]["y_column"] == "Xc_pct"


def test_waxs_scherrer_figure_writes_editable_document(tmp_path):
    result = WAXSResult(
        label="sample-scherrer",
        peaks=[
            {"two_theta": 15.0, "fwhm_deg": 0.32},
            {"two_theta": 22.0, "fwhm_deg": 0.44},
        ],
        D_Scherrer_nm=28.4,
    )

    figure_path = fig_w5_scherrer(result, str(tmp_path))
    document = load_figure_document(figure_path)

    assert figure_path
    assert document["mode"] == "object"
    assert document["technique"] == "waxs"
    assert document["figure_id"] == "Fig-W5_scherrer"
    assert document["recipe"]["module"] == "polynexus.core.waxs_engine.waxs_output"
    assert document["recipe"]["function"] == "fig_w5_scherrer"
    assert document["recipe"]["inputs"]["result_label"] == "sample-scherrer"
    assert document["recipe"]["parameters"]["peak_count"] == 2
    assert "mean_D_nm" in document["recipe"]["parameters"]
    assert document["data_sources"][0]["role"] == "plot_data"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert [obj["type"] for obj in document["objects"]] == [
        "plot_series",
        "line",
    ]
    assert document["objects"][0]["chart_kind"] == "bar"
    assert document["objects"][0]["x_column"] == "label"
    assert document["objects"][0]["y_column"] == "D_nm"


def _strain_series_result():
    strains = [0.0, 50.0, 100.0]
    point_results = []
    for index, strain in enumerate(strains):
        waxs_result = WAXSResult(
            label=f"strain-{strain:g}",
            two_theta=np.array([10.0, 12.0, 14.0]),
            I=np.array([100.0 + index, 130.0 + index * 2, 95.0 + index]),
            peaks=[
                {"two_theta": 12.0, "fwhm_deg": 0.35 + index * 0.02},
                {"two_theta": 18.0, "fwhm_deg": 0.42 + index * 0.02},
            ],
            D_WH_nm=20.0 - index,
        )
        point_results.append(
            WAXSStrainPointResult(
                strain_pct=strain,
                phase=WAXSStrainPhase.ELASTIC,
                Xc_pct=35.0 + index,
                D_Scherrer_nm=22.0 - index,
                D_WH_nm=20.0 - index,
                epsilon_WH_pct=0.2 + index * 0.05,
                f_Herman_avg=0.1 + index * 0.1,
                f_Herman_per_peak={"110": 0.1 + index * 0.08},
                lattice_strain_per_peak={"110": index * 0.01},
                waxs_result=waxs_result,
            )
        )
    return WAXSStrainSeriesResult(
        label="strain-series",
        strains=strains,
        point_results=point_results,
        Xc_array=np.array([35.0, 36.0, 37.0]),
        D_array=np.array([22.0, 21.0, 20.0]),
        f_Herman_array=np.array([0.1, 0.2, 0.3]),
        epsilon_WH_array=np.array([0.2, 0.25, 0.3]),
    )


def test_waxs_strain_waterfall_writes_editable_document(tmp_path):
    result = _strain_series_result()

    figure_path = fig_strain_waterfall(result, str(tmp_path))
    document = load_figure_document(figure_path)

    assert document["mode"] == "object"
    assert document["technique"] == "waxs"
    assert document["figure_id"] == "Fig-S2_waterfall"
    assert document["recipe"]["function"] == "fig_strain_waterfall"
    assert document["recipe"]["inputs"]["result_label"] == "strain-series"
    assert document["recipe"]["parameters"]["strain_count"] == 3
    assert document["data_sources"][0]["role"] == "plot_data"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert document["objects"][0]["type"] == "plot_series"
    assert document["objects"][0]["x_column"] == "two_theta"
    assert document["objects"][0]["y_column"] == "intensity_offset"


def test_waxs_strain_parameters_writes_editable_document(tmp_path):
    result = _strain_series_result()

    figure_path = fig_strain_parameters(result, str(tmp_path))
    document = load_figure_document(figure_path)

    assert document["mode"] == "object"
    assert document["technique"] == "waxs"
    assert document["figure_id"] == "Fig-S3_parameters"
    assert document["recipe"]["function"] == "fig_strain_parameters"
    assert document["recipe"]["inputs"]["result_label"] == "strain-series"
    assert document["data_sources"][0]["role"] == "plot_data"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert [obj["type"] for obj in document["objects"][:4]] == [
        "plot_series",
        "plot_series",
        "plot_series",
        "plot_series",
    ]
    assert document["objects"][0]["y_column"] == "Xc_pct"
    assert document["objects"][1]["y_column"] == "D_Scherrer_nm"
    assert document["objects"][2]["y_column"] == "f_Herman_avg"
    assert document["objects"][3]["y_column"] == "epsilon_WH_pct"


def test_waxs_strain_lattice_writes_editable_document(tmp_path):
    result = _strain_series_result()

    figure_path = fig_strain_lattice(result, str(tmp_path))
    document = load_figure_document(figure_path)

    assert document["mode"] == "object"
    assert document["technique"] == "waxs"
    assert document["figure_id"] == "Fig-S4_lattice_strain"
    assert document["recipe"]["function"] == "fig_strain_lattice"
    assert document["recipe"]["inputs"]["result_label"] == "strain-series"
    assert len(document["data_sources"]) == 2
    assert all(os.path.exists(source["path"]) for source in document["data_sources"])
    assert [obj["type"] for obj in document["objects"][:2]] == [
        "plot_series",
        "plot_series",
    ]
    assert document["objects"][0]["y_column"] == "lattice_strain_pct"
    assert document["objects"][1]["y_column"] == "beta_cos_theta"


def test_waxs_strain_2d_patterns_writes_editable_document(tmp_path):
    scans = [
        SimpleNamespace(image=np.array([[1.0, 2.0], [3.0, 4.0]])),
        SimpleNamespace(image=np.array([[2.0, 3.0], [4.0, 5.0]])),
    ]
    strains = [0.0, 100.0]

    figure_path = fig_strain_2d_patterns_from_scans(
        scans,
        strains,
        str(tmp_path),
        n_cols=2,
        n_rows=1,
    )
    document = load_figure_document(figure_path)

    assert document["mode"] == "object"
    assert document["technique"] == "waxs"
    assert document["figure_id"] == "Fig-S1_2D_patterns"
    assert document["recipe"]["function"] == "fig_strain_2d_patterns_from_scans"
    assert document["recipe"]["parameters"]["selected_count"] == 2
    assert document["data_sources"][0]["role"] == "plot_data"
    assert document["data_sources"][1]["role"] == "image_data"
    assert all(os.path.exists(source["path"]) for source in document["data_sources"])
    assert [obj["type"] for obj in document["objects"]] == ["plot_series"]
    assert document["objects"][0]["chart_kind"] == "image_grid"
    assert document["objects"][0]["image_path_column"] == "image_path"
