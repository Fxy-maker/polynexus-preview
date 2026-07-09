import csv
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np

from polynexus.core.figure_document import load_figure_document
from polynexus.core.plot_edits import load_figure_document_path
from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.core import LongPeriodResult, SAXSResult, StructureParams
from polynexus.core.saxs_engine.saxs_output import (
    fig_guinier,
    fig_joint_crystallinity,
    fig_kratky,
    fig_static_overview,
    fig_strain_overview,
    fig_t2_scattering_waterfall,
    fig_t3_structure_evolution,
    fig_t4_invariant_conservation,
    fig_u1_scattering_profile,
    fig_u2_correlation_function,
    fig_u3_idf,
    fig_u4_porod,
    fig_v1_temperature_waterfall,
    fig_v2_temperature_parameters,
    fig_v3_scattering_heatmap,
    fig_v4_avrami,
    fig_temperature_overview,
    generate_all_figures,
)


def test_saxs_scattering_profile_writes_editable_document(tmp_path):
    figure_path = tmp_path / "figures" / "01_scattering_profile.pdf"
    figure_path.parent.mkdir()
    q = np.array([0.1, 0.2, 0.4, 0.8])
    intensity = np.array([100.0, 80.0, 35.0, 12.0])

    path = fig_u1_scattering_profile(
        q,
        intensity,
        q_star=0.4,
        L=15.7,
        label="sample-saxs",
        output_path=str(figure_path),
    )
    document = load_figure_document(path)

    assert path == str(figure_path)
    assert document["mode"] == "object"
    assert document["technique"] == "saxs"
    assert document["figure_id"] == "01_scattering_profile"
    assert document["recipe"]["module"] == "polynexus.core.saxs_engine.saxs_output"
    assert document["recipe"]["function"] == "fig_u1_scattering_profile"
    assert document["recipe"]["inputs"]["label"] == "sample-saxs"
    assert document["recipe"]["parameters"]["q_star"] == 0.4
    assert document["data_sources"][0]["role"] == "plot_data"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert [obj["type"] for obj in document["objects"]] == ["plot_series", "plot_series"]
    assert document["objects"][0]["data_ref"] == document["data_sources"][0]["id"]
    assert load_figure_document_path(path).endswith(".pnfig.json")


def test_saxs_correlation_function_writes_editable_document(tmp_path):
    figure_path = tmp_path / "figures" / "02_correlation.pdf"
    figure_path.parent.mkdir()
    r = np.array([0.0, 5.0, 10.0, 15.0, 20.0, 25.0])
    gamma = np.array([1.0, 0.4, -0.1, 0.2, 0.05, 0.01])

    path = fig_u2_correlation_function(
        r,
        gamma,
        L=15.0,
        lc=8.5,
        output_path=str(figure_path),
    )
    document = load_figure_document(path)

    assert path == str(figure_path)
    assert document["mode"] == "object"
    assert document["technique"] == "saxs"
    assert document["figure_id"] == "02_correlation"
    assert document["recipe"]["function"] == "fig_u2_correlation_function"
    assert document["recipe"]["parameters"]["L"] == 15.0
    assert document["recipe"]["parameters"]["lc"] == 8.5
    assert document["data_sources"][0]["role"] == "plot_data"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert [obj["type"] for obj in document["objects"]] == [
        "plot_series",
        "line",
        "line",
    ]
    assert document["objects"][0]["data_ref"] == document["data_sources"][0]["id"]
    assert load_figure_document_path(path).endswith(".pnfig.json")


def test_saxs_idf_writes_editable_document(tmp_path):
    figure_path = tmp_path / "figures" / "03_idf.pdf"
    figure_path.parent.mkdir()
    r_idf = np.array([0.0, 4.0, 8.0, 12.0, 16.0, 20.0])
    idf = np.array([0.0, 0.3, 0.9, 0.4, -0.1, 0.02])

    path = fig_u3_idf(
        r_idf,
        idf,
        L_idf=12.0,
        lc_idf=7.5,
        output_path=str(figure_path),
    )
    document = load_figure_document(path)

    assert path == str(figure_path)
    assert document["mode"] == "object"
    assert document["technique"] == "saxs"
    assert document["figure_id"] == "03_idf"
    assert document["recipe"]["function"] == "fig_u3_idf"
    assert document["recipe"]["parameters"]["L_idf"] == 12.0
    assert document["recipe"]["parameters"]["lc_idf"] == 7.5
    assert document["data_sources"][0]["role"] == "plot_data"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert [obj["type"] for obj in document["objects"]] == [
        "plot_series",
        "line",
        "line",
    ]
    assert document["objects"][0]["data_ref"] == document["data_sources"][0]["id"]
    assert load_figure_document_path(path).endswith(".pnfig.json")


def test_saxs_porod_writes_editable_document(tmp_path):
    figure_path = tmp_path / "figures" / "04_porod.pdf"
    figure_path.parent.mkdir()
    q_porod = np.array([0.2, 0.3, 0.4, 0.5])
    iq4 = np.array([1.2, 1.35, 1.5, 1.7])

    path = fig_u4_porod(
        q_porod,
        iq4,
        slope=0.25,
        Kp=1.6,
        output_path=str(figure_path),
    )
    document = load_figure_document(path)

    assert path == str(figure_path)
    assert document["mode"] == "object"
    assert document["technique"] == "saxs"
    assert document["figure_id"] == "04_porod"
    assert document["recipe"]["function"] == "fig_u4_porod"
    assert document["recipe"]["parameters"]["slope"] == 0.25
    assert document["recipe"]["parameters"]["Kp"] == 1.6
    assert document["data_sources"][0]["role"] == "plot_data"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert [obj["type"] for obj in document["objects"]] == [
        "plot_series",
        "plot_series",
    ]
    assert document["objects"][0]["x_column"] == "q4_nm_minus4"
    assert document["objects"][1]["y_column"] == "fit"
    assert load_figure_document_path(path).endswith(".pnfig.json")


def test_saxs_guinier_writes_editable_document(tmp_path):
    figure_path = tmp_path / "figures" / "05_guinier.pdf"
    figure_path.parent.mkdir()
    q = np.array([0.04, 0.06, 0.08, 0.1, 0.12, 0.14])
    intensity = np.array([100.0, 95.0, 88.0, 80.0, 71.0, 65.0])

    path = fig_guinier(q, intensity, Rg=12.5, output_path=str(figure_path))
    document = load_figure_document(path)

    assert document["mode"] == "object"
    assert document["technique"] == "saxs"
    assert document["figure_id"] == "05_guinier"
    assert document["recipe"]["function"] == "fig_guinier"
    assert document["recipe"]["parameters"]["Rg"] == 12.5
    assert document["data_sources"][0]["role"] == "plot_data"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert [obj["type"] for obj in document["objects"]] == ["plot_series", "plot_series"]
    assert document["objects"][0]["x_column"] == "q2_nm_minus2"
    assert document["objects"][0]["y_column"] == "ln_intensity"
    assert document["objects"][1]["y_column"] == "fit"
    assert load_figure_document_path(path).endswith(".pnfig.json")


def test_saxs_kratky_writes_editable_document(tmp_path):
    figure_path = tmp_path / "figures" / "06_kratky.pdf"
    figure_path.parent.mkdir()
    q = np.array([0.1, 0.2, 0.4, 0.8])
    intensity = np.array([100.0, 80.0, 35.0, 12.0])

    path = fig_kratky(q, intensity, L=15.0, output_path=str(figure_path))
    document = load_figure_document(path)

    assert document["mode"] == "object"
    assert document["technique"] == "saxs"
    assert document["figure_id"] == "06_kratky"
    assert document["recipe"]["function"] == "fig_kratky"
    assert document["recipe"]["parameters"]["L"] == 15.0
    assert document["data_sources"][0]["role"] == "plot_data"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert [obj["type"] for obj in document["objects"]] == ["plot_series", "line"]
    assert document["objects"][0]["x_column"] == "q_nm_inv"
    assert document["objects"][0]["y_column"] == "iq2"
    assert document["objects"][1]["orientation"] == "vertical"
    assert load_figure_document_path(path).endswith(".pnfig.json")


def test_saxs_joint_crystallinity_writes_editable_document(tmp_path):
    figure_path = tmp_path / "figures" / "joint_crystallinity.pdf"
    figure_path.parent.mkdir()

    path = fig_joint_crystallinity(
        saxs_phi_c=0.42,
        waxs_phi_c=0.39,
        dsc_phi_c=0.45,
        output_path=str(figure_path),
    )
    document = load_figure_document(path)

    assert document["mode"] == "object"
    assert document["technique"] == "saxs"
    assert document["figure_id"] == "joint_crystallinity"
    assert document["recipe"]["function"] == "fig_joint_crystallinity"
    assert document["recipe"]["parameters"]["technique_count"] == 3
    assert document["data_sources"][0]["role"] == "plot_data"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert [obj["type"] for obj in document["objects"]] == ["plot_series"]
    assert document["objects"][0]["chart_kind"] == "bar"
    assert document["objects"][0]["x_column"] == "technique"
    assert document["objects"][0]["y_column"] == "phi_c"
    assert load_figure_document_path(path).endswith(".pnfig.json")


def test_saxs_strain_waterfall_writes_editable_document(tmp_path):
    figure_path = tmp_path / "figures" / "t2_waterfall.pdf"
    figure_path.parent.mkdir()
    strains = np.array([0.0, 50.0, 100.0])
    q_list = [np.array([0.1, 0.2, 0.4]) for _ in strains]
    I_list = [
        np.array([100.0, 70.0, 30.0]),
        np.array([95.0, 65.0, 28.0]),
        np.array([90.0, 60.0, 25.0]),
    ]

    path = fig_t2_scattering_waterfall(strains, q_list, I_list, output_path=str(figure_path))
    document = load_figure_document(path)

    assert document["mode"] == "object"
    assert document["technique"] == "saxs"
    assert document["figure_id"] == "t2_waterfall"
    assert document["recipe"]["function"] == "fig_t2_scattering_waterfall"
    assert document["recipe"]["parameters"]["condition_count"] == 3
    assert os.path.exists(document["data_sources"][0]["path"])
    assert document["objects"][0]["x_column"] == "q_nm_inv"
    assert document["objects"][0]["y_column"] == "intensity_offset"


def test_saxs_strain_structure_evolution_writes_editable_document(tmp_path):
    figure_path = tmp_path / "figures" / "t3_structure.pdf"
    figure_path.parent.mkdir()
    strains = np.array([0.0, 50.0, 100.0])
    L = np.array([15.0, 16.0, 17.0])
    lc = np.array([8.0, 8.5, 9.0])
    phi = np.array([0.35, 0.38, 0.42])

    path = fig_t3_structure_evolution(strains, L, lc, phi_c_array=phi, output_path=str(figure_path))
    document = load_figure_document(path)

    assert document["mode"] == "object"
    assert document["technique"] == "saxs"
    assert document["figure_id"] == "t3_structure"
    assert document["recipe"]["function"] == "fig_t3_structure_evolution"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert [obj["type"] for obj in document["objects"][:3]] == [
        "plot_series",
        "plot_series",
        "plot_series",
    ]
    assert document["objects"][0]["y_column"] == "L_nm"
    assert document["objects"][1]["y_column"] == "lc_nm"
    assert document["objects"][2]["y_column"] == "phi_c"


def test_saxs_invariant_conservation_writes_editable_document(tmp_path):
    figure_path = tmp_path / "figures" / "t4_invariant.pdf"
    figure_path.parent.mkdir()
    strains = np.array([0.0, 50.0, 100.0])
    q_star = np.array([10.0, 10.2, 9.9])

    path = fig_t4_invariant_conservation(strains, q_star, Q_ref=10.0, output_path=str(figure_path))
    document = load_figure_document(path)

    assert document["mode"] == "object"
    assert document["technique"] == "saxs"
    assert document["figure_id"] == "t4_invariant"
    assert document["recipe"]["function"] == "fig_t4_invariant_conservation"
    assert document["recipe"]["parameters"]["Q_ref"] == 10.0
    assert os.path.exists(document["data_sources"][0]["path"])
    assert [obj["type"] for obj in document["objects"]] == ["highlight", "plot_series", "line"]
    assert document["objects"][1]["y_column"] == "Q_norm"


def test_saxs_temperature_waterfall_writes_editable_document(tmp_path):
    figure_path = tmp_path / "figures" / "v1_waterfall.pdf"
    figure_path.parent.mkdir()
    temperatures = np.array([30.0, 80.0, 130.0])
    q_list = [np.array([0.1, 0.2, 0.4]) for _ in temperatures]
    I_list = [
        np.array([100.0, 70.0, 30.0]),
        np.array([90.0, 62.0, 27.0]),
        np.array([82.0, 55.0, 23.0]),
    ]

    path = fig_v1_temperature_waterfall(temperatures, q_list, I_list, output_path=str(figure_path))
    document = load_figure_document(path)

    assert document["mode"] == "object"
    assert document["technique"] == "saxs"
    assert document["figure_id"] == "v1_waterfall"
    assert document["recipe"]["function"] == "fig_v1_temperature_waterfall"
    assert document["recipe"]["parameters"]["condition_axis"] == "temperature_C"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert document["objects"][0]["x_column"] == "q_nm_inv"
    assert document["objects"][0]["y_column"] == "intensity_offset"


def test_saxs_temperature_parameters_writes_editable_document(tmp_path):
    figure_path = tmp_path / "figures" / "v2_temperature_parameters.pdf"
    figure_path.parent.mkdir()
    temperatures = np.array([30.0, 80.0, 130.0])
    L = np.array([15.0, 16.0, 17.0])
    lc = np.array([8.0, 8.4, 8.8])
    q_star = np.array([100.0, 105.0, 98.0])
    xc = np.array([0.4, 0.38, 0.2])

    path = fig_v2_temperature_parameters(
        temperatures,
        L,
        lc,
        Q_star_array=q_star,
        Xc_array=xc,
        output_path=str(figure_path),
    )
    document = load_figure_document(path)

    assert document["mode"] == "object"
    assert document["technique"] == "saxs"
    assert document["figure_id"] == "v2_temperature_parameters"
    assert document["recipe"]["function"] == "fig_v2_temperature_parameters"
    assert os.path.exists(document["data_sources"][0]["path"])
    assert [obj["type"] for obj in document["objects"][:4]] == [
        "plot_series",
        "plot_series",
        "plot_series",
        "plot_series",
    ]
    assert document["objects"][0]["y_column"] == "L_nm"
    assert document["objects"][1]["y_column"] == "lc_nm"
    assert document["objects"][2]["y_column"] == "Q_star"
    assert document["objects"][3]["y_column"] == "Xc"


def test_saxs_avrami_writes_editable_document(tmp_path):
    figure_path = tmp_path / "figures" / "v4_avrami.pdf"
    figure_path.parent.mkdir()
    times = np.array([10.0, 20.0, 40.0, 80.0, 160.0])
    xc = np.array([0.05, 0.18, 0.42, 0.7, 0.9])
    avrami = {"valid": True, "n": 2.0, "k_sn": 0.001, "t_half_s": 75.0}

    path = fig_v4_avrami(times, xc, avrami_result=avrami, output_path=str(figure_path))
    document = load_figure_document(path)

    assert document["mode"] == "object"
    assert document["technique"] == "saxs"
    assert document["figure_id"] == "v4_avrami"
    assert document["recipe"]["function"] == "fig_v4_avrami"
    assert document["recipe"]["parameters"]["n"] == 2.0
    assert os.path.exists(document["data_sources"][0]["path"])
    assert [obj["type"] for obj in document["objects"][:3]] == [
        "plot_series",
        "line",
        "plot_series",
    ]
    assert document["objects"][0]["y_column"] == "Xc"
    assert document["objects"][2]["x_column"] == "ln_time_s"
    assert document["objects"][2]["y_column"] == "avrami_y"


def test_saxs_scattering_heatmap_writes_editable_document(tmp_path):
    figure_path = tmp_path / "figures" / "v3_heatmap.pdf"
    figure_path.parent.mkdir()
    q = np.array([0.1, 0.2, 0.4])
    temperatures = np.array([30.0, 80.0])
    intensity = np.array([
        [100.0, 60.0, 20.0],
        [90.0, 55.0, 18.0],
    ])
    q_star = np.array([0.2, 0.22])

    path = fig_v3_scattering_heatmap(
        q,
        temperatures,
        intensity,
        q_star_array=q_star,
        output_path=str(figure_path),
        beamstop_q_min=0.15,
    )
    document = load_figure_document(path)

    assert document["mode"] == "object"
    assert document["technique"] == "saxs"
    assert document["figure_id"] == "v3_heatmap"
    assert document["recipe"]["function"] == "fig_v3_scattering_heatmap"
    assert document["recipe"]["parameters"]["beamstop_q_min"] == 0.15
    assert len(document["data_sources"]) == 2
    assert all(os.path.exists(source["path"]) for source in document["data_sources"])
    assert [obj["type"] for obj in document["objects"]] == ["plot_series", "plot_series"]
    assert document["objects"][0]["chart_kind"] == "heatmap"
    assert document["objects"][0]["x_column"] == "q_nm_inv"
    assert document["objects"][0]["y_column"] == "temperature_C"
    assert document["objects"][0]["value_column"] == "log_intensity"
    assert document["objects"][1]["y_column"] == "temperature_C"


def test_saxs_static_overview_writes_editable_document(tmp_path):
    figure_path = tmp_path / "figures" / "static_overview.pdf"
    figure_path.parent.mkdir()
    labels = ["A", "B"]
    q_list = [np.array([0.1, 0.2, 0.4]), np.array([0.1, 0.2, 0.4])]
    I_list = [np.array([100.0, 70.0, 30.0]), np.array([90.0, 65.0, 28.0])]

    path = fig_static_overview(
        labels,
        q_list,
        I_list,
        L_list=[15.0, 16.5],
        lc_list=[8.0, 8.8],
        Xc_list=[0.35, 0.4],
        Q_rel_list=[1.0, 0.95],
        output_path=str(figure_path),
    )
    document = load_figure_document(path)

    assert document["mode"] == "object"
    assert document["technique"] == "saxs"
    assert document["figure_id"] == "static_overview"
    assert document["recipe"]["function"] == "fig_static_overview"
    assert document["recipe"]["parameters"]["sample_count"] == 2
    assert len(document["data_sources"]) == 2
    assert all(os.path.exists(source["path"]) for source in document["data_sources"])
    assert [obj["type"] for obj in document["objects"][:5]] == [
        "plot_series",
        "plot_series",
        "plot_series",
        "plot_series",
        "plot_series",
    ]
    assert document["objects"][0]["y_column"] == "intensity"
    assert document["objects"][1]["y_column"] == "iq2"
    assert document["objects"][2]["chart_kind"] == "bar"
    assert document["objects"][2]["y_column"] == "L_nm"
    assert document["objects"][4]["y_column"] == "Xc"


def test_saxs_temperature_overview_writes_editable_document(tmp_path):
    figure_path = tmp_path / "figures" / "temperature_overview.pdf"
    figure_path.parent.mkdir()
    temps = np.array([30.0, 80.0])
    q_list = [np.array([0.1, 0.2, 0.4]), np.array([0.1, 0.2, 0.4])]
    I_list = [np.array([100.0, 70.0, 30.0]), np.array([90.0, 65.0, 28.0])]

    path = fig_temperature_overview(
        temps,
        q_list,
        I_list,
        L_arr=np.array([15.0, 16.0]),
        lc_arr=np.array([8.0, 8.5]),
        Xc_arr=np.array([0.35, 0.3]),
        Q_arr=np.array([100.0, 95.0]),
        output_path=str(figure_path),
    )
    document = load_figure_document(path)

    assert document["mode"] == "object"
    assert document["technique"] == "saxs"
    assert document["figure_id"] == "temperature_overview"
    assert document["recipe"]["function"] == "fig_temperature_overview"
    assert document["recipe"]["parameters"]["condition_axis"] == "temperature_C"
    assert len(document["data_sources"]) == 2
    assert all(os.path.exists(source["path"]) for source in document["data_sources"])
    assert document["objects"][0]["y_column"] == "iq2_offset"
    assert document["objects"][1]["y_column"] == "L_nm"
    assert document["objects"][2]["y_column"] == "lc_nm"
    assert document["objects"][3]["y_column"] == "Xc"
    assert document["objects"][4]["y_column"] == "Q_rel"


def test_saxs_generate_all_figures_prefers_effective_temperature_lc(tmp_path):
    q = np.array([0.1, 0.2, 0.4], dtype=float)
    output_dir = tmp_path
    results = []
    for index, (temperature, raw_lc, effective_lc) in enumerate(
        [(170.0, 1.2, 3.2), (195.0, 1.1, 3.1), (220.0, 1.0, 3.0)]
    ):
        result = SAXSResult(
            label=f"frame_{index:03d}",
            condition_value=temperature,
            q=q,
            I=np.array([100.0 - index * 5.0, 70.0 - index * 3.0, 30.0 - index * 2.0], dtype=float),
            long_period=LongPeriodResult(L_best=10.0 - index * 0.1, L_confidence=0.6, method_used="bragg"),
            structure=StructureParams(
                L=10.0 - index * 0.1,
                lc=raw_lc,
                la=8.8 - index * 0.1,
                phi_c=round(raw_lc / (10.0 - index * 0.1), 3),
                confidence_lc=0.55,
                Q_invariant=100.0 - index,
            ),
        )
        result.final_parameters = {
            "lc_nm_effective": effective_lc,
            "la_nm_effective": round((10.0 - index * 0.1) - effective_lc, 2),
            "Xc_effective": round(effective_lc / (10.0 - index * 0.1), 3),
            "lamellar_interpretation_mode": "sequence_path_usable",
            "effective_param_reason": "selected=primary",
        }
        results.append(result)

    figures = generate_all_figures(
        results,
        str(output_dir),
        config=SAXSConfig(experiment_type="temperature", condition_label="Temperature"),
    )
    data_path = output_dir / "data" / "figure_sources" / "Fig_3_structure_parameters_data.csv"

    assert "Fig_3_structure_params" in figures
    assert data_path.exists()
    with data_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert [float(row["lc_nm"]) for row in rows] == [3.2, 3.1, 3.0]


def test_saxs_strain_overview_writes_editable_document(tmp_path):
    figure_path = tmp_path / "figures" / "strain_overview.pdf"
    figure_path.parent.mkdir()
    strains = np.array([0.0, 100.0])
    q_list = [np.array([0.1, 0.2, 0.4]), np.array([0.1, 0.2, 0.4])]
    I_list = [np.array([100.0, 70.0, 30.0]), np.array([90.0, 65.0, 28.0])]

    path = fig_strain_overview(
        strains,
        q_list,
        I_list,
        L_arr=np.array([15.0, 16.0]),
        lc_arr=np.array([8.0, 8.5]),
        la_arr=np.array([7.0, 7.5]),
        Xc_arr=np.array([0.35, 0.4]),
        Q_arr=np.array([100.0, 105.0]),
        Q_rel_arr=np.array([1.0, 1.05]),
        output_path=str(figure_path),
    )
    document = load_figure_document(path)

    assert document["mode"] == "object"
    assert document["technique"] == "saxs"
    assert document["figure_id"] == "strain_overview"
    assert document["recipe"]["function"] == "fig_strain_overview"
    assert document["recipe"]["parameters"]["condition_axis"] == "strain_pct"
    assert len(document["data_sources"]) == 2
    assert all(os.path.exists(source["path"]) for source in document["data_sources"])
    assert document["objects"][0]["y_column"] == "iq2_offset"
    assert document["objects"][1]["y_column"] == "L_nm"
    assert document["objects"][2]["y_column"] == "lc_nm"
    assert document["objects"][3]["y_column"] == "la_nm"
    assert document["objects"][4]["y_column"] == "Q_star"
    assert document["objects"][5]["y_column"] == "Xc"
