import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np

from polynexus.core.figure_document import load_figure_document
from polynexus.core.nmr_engine.core import NMRResult
from polynexus.core.nmr_engine.nmr_output import (
    fig_nmr1_spectrum,
    fig_nmr2_deconvolution,
    fig_nmr3_comparison,
    fig_nmr4_crystallinity,
    fig_nmr5_region_integrals,
)
from polynexus.core.plot_edits import load_figure_document_path


def test_nmr_spectrum_writes_editable_document(tmp_path):
    result = NMRResult(
        label="sample-nmr",
        nucleus="13C",
        ppm=np.array([180.0, 160.0, 140.0, 120.0]),
        intensity=np.array([0.1, 0.4, 1.0, 0.3]),
        peaks=[
            {"ppm": 140.0, "height": 1.0, "assignment": "aromatic C"},
            {"ppm": 160.0, "height": 0.4, "assignment": "carbonyl C"},
        ],
    )

    path = fig_nmr1_spectrum(result, str(tmp_path), tag="sample")
    document = load_figure_document(path)

    assert document["mode"] == "object"
    assert document["technique"] == "nmr"
    assert document["figure_id"] == "Fig-NMR1_spectrum_sample"
    assert document["recipe"]["module"] == "polynexus.core.nmr_engine.nmr_output"
    assert document["recipe"]["function"] == "fig_nmr1_spectrum"
    assert document["recipe"]["inputs"]["result_label"] == "sample-nmr"
    assert document["recipe"]["parameters"]["tag"] == "sample"
    assert document["data_sources"][0]["role"] == "plot_data"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert [obj["type"] for obj in document["objects"]] == [
        "plot_series",
        "line",
        "text",
        "line",
        "text",
        "axis",
        "axis",
    ]
    assert document["objects"][0]["data_ref"] == document["data_sources"][0]["id"]
    assert load_figure_document_path(path).endswith(".pnfig.json")


def test_nmr_deconvolution_writes_editable_document(tmp_path):
    result = NMRResult(
        label="fit-nmr",
        nucleus="13C",
        ppm=np.array([180.0, 160.0, 140.0, 120.0]),
        intensity=np.array([0.1, 0.4, 1.0, 0.3]),
        intensity_fit=np.array([0.12, 0.38, 0.95, 0.28]),
        r_squared=0.92,
        peaks=[
            {"ppm": 140.0, "height": 1.0, "assignment": "aromatic C"},
            {"ppm": 160.0, "height": 0.4, "assignment": "carbonyl C"},
        ],
    )

    path = fig_nmr2_deconvolution(result, str(tmp_path), tag="fit")
    document = load_figure_document(path)

    assert document["mode"] == "object"
    assert document["technique"] == "nmr"
    assert document["figure_id"] == "Fig-NMR2_deconv_fit"
    assert document["recipe"]["function"] == "fig_nmr2_deconvolution"
    assert document["recipe"]["inputs"]["result_label"] == "fit-nmr"
    assert document["recipe"]["parameters"]["tag"] == "fit"
    assert document["recipe"]["parameters"]["r_squared"] == 0.92
    assert document["data_sources"][0]["role"] == "plot_data"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert [obj["type"] for obj in document["objects"]] == [
        "plot_series",
        "plot_series",
        "line",
        "text",
        "line",
        "text",
        "axis",
        "axis",
    ]
    assert document["objects"][0]["y_column"] == "intensity"
    assert document["objects"][1]["y_column"] == "fit"
    assert load_figure_document_path(path).endswith(".pnfig.json")


def test_nmr_comparison_writes_editable_document(tmp_path):
    result = NMRResult(
        label="compare-nmr",
        matches=[
            {
                "exp_ppm": 140.0,
                "calc_ppm": 141.2,
                "exp_assignment": "aromatic C",
            },
            {
                "exp_ppm": 160.0,
                "calc_ppm": 158.5,
                "exp_assignment": "carbonyl C",
            },
        ],
    )

    path = fig_nmr3_comparison(result, str(tmp_path), tag="cmp")
    document = load_figure_document(path)

    assert document["mode"] == "object"
    assert document["technique"] == "nmr"
    assert document["figure_id"] == "Fig-NMR3_comparison_cmp"
    assert document["recipe"]["function"] == "fig_nmr3_comparison"
    assert document["recipe"]["inputs"]["result_label"] == "compare-nmr"
    assert document["recipe"]["parameters"]["tag"] == "cmp"
    assert document["recipe"]["parameters"]["match_count"] == 2
    assert document["recipe"]["parameters"]["tolerance_ppm"] == 2.0
    assert document["data_sources"][0]["role"] == "plot_data"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert [obj["type"] for obj in document["objects"]] == [
        "highlight",
        "plot_series",
        "plot_series",
    ]
    assert document["objects"][1]["x_column"] == "exp_ppm"
    assert document["objects"][1]["y_column"] == "calc_ppm"
    assert document["objects"][2]["x_column"] == "reference_exp_ppm"
    assert document["objects"][2]["y_column"] == "reference_calc_ppm"
    assert load_figure_document_path(path).endswith(".pnfig.json")


def test_nmr_crystallinity_writes_editable_document(tmp_path):
    results = [
        NMRResult(
            label="solid-a",
            Xc_pct=36.5,
            Xc_method="solid_13c_peak_area",
            Xc_assignment_status="supported",
        ),
        NMRResult(
            label="solid-b",
            Xc_pct=48.0,
            Xc_method="solid_13c_peak_area",
            Xc_assignment_status="supported",
        ),
    ]

    path = fig_nmr4_crystallinity(results, str(tmp_path))
    document = load_figure_document(path)

    assert document["mode"] == "object"
    assert document["technique"] == "nmr"
    assert document["figure_id"] == "Fig-NMR4_crystallinity"
    assert document["recipe"]["function"] == "fig_nmr4_crystallinity"
    assert document["recipe"]["inputs"]["result_labels"] == ["solid-a", "solid-b"]
    assert document["recipe"]["parameters"]["sample_count"] == 2
    assert document["data_sources"][0]["role"] == "plot_data"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert [obj["type"] for obj in document["objects"]] == ["plot_series"]
    assert document["objects"][0]["chart_kind"] == "bar"
    assert document["objects"][0]["x_column"] == "label"
    assert document["objects"][0]["y_column"] == "Xc_pct"
    assert load_figure_document_path(path).endswith(".pnfig.json")


def test_nmr_region_integrals_writes_editable_document(tmp_path):
    result = NMRResult(
        label="regions-nmr",
        region_integrals={
            "aromatic_alkenyl_C": 62.5,
            "aliphatic_C": 37.5,
        },
    )

    path = fig_nmr5_region_integrals(result, str(tmp_path), tag="regions")
    document = load_figure_document(path)

    assert document["mode"] == "object"
    assert document["technique"] == "nmr"
    assert document["figure_id"] == "Fig-NMR5_region_integrals_regions"
    assert document["recipe"]["function"] == "fig_nmr5_region_integrals"
    assert document["recipe"]["inputs"]["result_label"] == "regions-nmr"
    assert document["recipe"]["parameters"]["tag"] == "regions"
    assert document["recipe"]["parameters"]["region_count"] == 2
    assert document["data_sources"][0]["role"] == "plot_data"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert [obj["type"] for obj in document["objects"]] == ["plot_series"]
    assert document["objects"][0]["chart_kind"] == "barh"
    assert document["objects"][0]["x_column"] == "fraction_pct"
    assert document["objects"][0]["y_column"] == "region"
    assert load_figure_document_path(path).endswith(".pnfig.json")
