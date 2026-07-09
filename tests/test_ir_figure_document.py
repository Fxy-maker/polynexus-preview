import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np

from polynexus.core.figure_document import load_figure_document
from polynexus.core.ir_engine.core import IRResult
from polynexus.core.ir_engine.io import ComputedMode, IRSpectrum
from polynexus.core.ir_engine.ir_output import (
    fig_ir1_spectrum,
    fig_ir2_peak_fit,
    fig_ir3_comparison,
    fig_ir4_crystallinity,
)
from polynexus.core.plot_edits import load_figure_document_path


def test_ir_spectrum_writes_editable_document(tmp_path):
    result = IRResult(
        label="sample-ir",
        wavenumber=np.array([1800.0, 1700.0, 1600.0, 1500.0]),
        absorbance=np.array([0.1, 0.4, 0.25, 0.15]),
        peaks=[
            {
                "wavenumber": 1700.0,
                "height": 0.4,
                "prominence": 0.3,
                "assignment": "amide I",
            }
        ],
    )

    figure_path = fig_ir1_spectrum(result, str(tmp_path))
    document = load_figure_document(figure_path)

    assert figure_path
    assert document["mode"] == "object"
    assert document["technique"] == "ir"
    assert document["figure_id"] == "Fig-IR1_sample-ir_spectrum"
    assert document["recipe"]["module"] == "polynexus.core.ir_engine.ir_output"
    assert document["recipe"]["function"] == "fig_ir1_spectrum"
    assert document["recipe"]["inputs"]["result_label"] == "sample-ir"
    assert document["data_sources"][0]["role"] == "plot_data"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert document["objects"][0]["type"] == "plot_series"
    assert document["objects"][0]["data_ref"] == document["data_sources"][0]["id"]
    assert load_figure_document_path(figure_path).endswith(".pnfig.json")


def test_ir_peak_fit_writes_editable_document(tmp_path):
    result = IRResult(
        label="sample-ir-fit",
        wavenumber=np.array([1800.0, 1720.0, 1680.0, 1600.0, 1520.0]),
        absorbance=np.array([0.08, 0.38, 0.42, 0.24, 0.12]),
        absorbance_fit=np.array([0.07, 0.36, 0.40, 0.22, 0.11]),
        r_squared=0.96,
        peaks=[
            {
                "wavenumber": 1680.0,
                "height": 0.42,
                "prominence": 0.3,
                "assignment": "amide I",
            },
            {
                "wavenumber": 1720.0,
                "height": 0.38,
                "prominence": 0.2,
                "assignment": "C=O",
            },
        ],
    )

    figure_path = fig_ir2_peak_fit(result, str(tmp_path), wavenumber_range=(1600.0, 1750.0))
    document = load_figure_document(figure_path)

    assert figure_path
    assert document["mode"] == "object"
    assert document["technique"] == "ir"
    assert document["figure_id"] == "Fig-IR2_sample-ir-fit_peak_fit"
    assert document["recipe"]["module"] == "polynexus.core.ir_engine.ir_output"
    assert document["recipe"]["function"] == "fig_ir2_peak_fit"
    assert document["recipe"]["inputs"]["result_label"] == "sample-ir-fit"
    assert document["recipe"]["parameters"]["wavenumber_range"] == [1600.0, 1750.0]
    assert document["recipe"]["parameters"]["r_squared"] == 0.96
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
    assert document["objects"][0]["y_column"] == "absorbance"
    assert document["objects"][1]["y_column"] == "fit"
    assert document["objects"][2]["orientation"] == "vertical"
    assert load_figure_document_path(figure_path).endswith(".pnfig.json")


def test_ir_comparison_writes_editable_document(tmp_path):
    result = IRResult(
        label="sample-ir-compare",
        wavenumber=np.array([1800.0, 1700.0, 1600.0, 1500.0]),
        absorbance=np.array([0.1, 0.4, 0.25, 0.15]),
        simulated_spectrum=IRSpectrum(
            label="computed",
            wavenumber=np.array([1800.0, 1700.0, 1600.0, 1500.0]),
            absorbance=np.array([0.08, 0.35, 0.28, 0.13]),
            source="computation",
        ),
        computed_modes=[
            ComputedMode(index=1, frequency_cm1=1692.0, ir_intensity_km_mol=5.0),
            ComputedMode(index=2, frequency_cm1=1510.0, ir_intensity_km_mol=4.0),
        ],
        matches=[
            {"exp_cm1": 1700.0, "delta_cm1": 8.0},
            {"exp_cm1": 1500.0, "delta_cm1": 12.0},
        ],
    )

    figure_path = fig_ir3_comparison(result, str(tmp_path))
    document = load_figure_document(figure_path)

    assert figure_path
    assert document["mode"] == "object"
    assert document["technique"] == "ir"
    assert document["figure_id"] == "Fig-IR3_sample-ir-compare_comparison"
    assert document["recipe"]["module"] == "polynexus.core.ir_engine.ir_output"
    assert document["recipe"]["function"] == "fig_ir3_comparison"
    assert document["recipe"]["inputs"]["result_label"] == "sample-ir-compare"
    assert document["recipe"]["parameters"]["mode_count"] == 2
    assert document["recipe"]["parameters"]["match_count"] == 2
    assert document["data_sources"][0]["role"] == "plot_data"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert [obj["type"] for obj in document["objects"]] == [
        "plot_series",
        "plot_series",
        "line",
        "line",
        "plot_series",
    ]
    assert document["objects"][0]["y_column"] == "experimental_absorbance"
    assert document["objects"][1]["y_column"] == "computed_absorbance"
    assert document["objects"][4]["chart_kind"] == "bar"
    assert document["objects"][4]["y_column"] == "delta_cm1"
    assert load_figure_document_path(figure_path).endswith(".pnfig.json")


def test_ir_crystallinity_writes_editable_document(tmp_path):
    results = [
        IRResult(
            label="ir-a",
            Xc_pct=31.0,
            Xc_method="band_ratio",
            Xc_band="1470",
            Xc_ref_band="1450",
        ),
        IRResult(
            label="ir-b",
            Xc_pct=46.5,
            Xc_method="band_ratio",
            Xc_band="1470",
            Xc_ref_band="1450",
        ),
    ]

    figure_path = fig_ir4_crystallinity(results, str(tmp_path))
    document = load_figure_document(figure_path)

    assert figure_path
    assert document["mode"] == "object"
    assert document["technique"] == "ir"
    assert document["figure_id"] == "Fig-IR4_crystallinity"
    assert document["recipe"]["module"] == "polynexus.core.ir_engine.ir_output"
    assert document["recipe"]["function"] == "fig_ir4_crystallinity"
    assert document["recipe"]["inputs"]["result_labels"] == ["ir-a", "ir-b"]
    assert document["recipe"]["parameters"]["sample_count"] == 2
    assert document["data_sources"][0]["role"] == "plot_data"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert [obj["type"] for obj in document["objects"]] == ["plot_series"]
    assert document["objects"][0]["chart_kind"] == "bar"
    assert document["objects"][0]["x_column"] == "label"
    assert document["objects"][0]["y_column"] == "Xc_pct"
    assert load_figure_document_path(figure_path).endswith(".pnfig.json")
