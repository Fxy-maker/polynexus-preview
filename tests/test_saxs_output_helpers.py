from types import SimpleNamespace

import importlib
from pathlib import Path

import numpy as np

from polynexus.core.saxs_engine.saxs_output_helpers import (
    _csv_number,
    _finite_csv,
    _json_number,
    _result_to_params_dict,
    _result_effective_lc_value,
    export_1d_profile,
    export_parameters_csv,
    export_strain_series_csv,
    export_temp_series_csv,
)
from polynexus.core.saxs_engine.saxs_output_data_writers import (
    _write_condition_overview_profile_data,
    _write_condition_overview_summary_data,
    _write_guinier_data,
    _write_joint_crystallinity_data,
    _write_kratky_data,
    _write_series_waterfall_data,
    _write_static_overview_profile_data,
    _write_static_overview_summary_data,
    _write_t3_structure_data,
    _write_t4_invariant_data,
    _write_v2_temperature_parameters_data,
    _write_v3_heatmap_data,
    _write_v3_qstar_data,
    _write_v4_avrami_data,
    _write_u1_scattering_data,
    _write_u2_correlation_data,
    _write_u3_idf_data,
    _write_u4_porod_data,
)
from polynexus.core.saxs_engine.saxs_output_documents import (
    _save_condition_overview_document,
    _save_guinier_document,
    _save_joint_crystallinity_document,
    _save_kratky_document,
    _save_series_waterfall_document,
    _save_static_overview_document,
    _save_t3_structure_document,
    _save_t4_invariant_document,
    _save_u1_scattering_document,
    _save_u2_correlation_document,
    _save_u3_idf_document,
    _save_u4_porod_document,
    _save_v2_temperature_parameters_document,
    _save_v3_heatmap_document,
    _save_v4_avrami_document,
)


def test_json_number_returns_none_for_non_finite_values() -> None:
    assert _json_number(None) is None
    assert _json_number("not-a-number") is None
    assert _json_number(float("inf")) is None


def test_csv_number_rounds_to_a_stable_precision() -> None:
    assert _csv_number(1.234567890123) == 1.2345678901


def test_finite_csv_omits_non_numeric_values() -> None:
    assert _finite_csv("bad") == ""
    assert _finite_csv(float("nan")) == ""
    assert _finite_csv(2.5) == 2.5


def test_result_effective_lc_value_prefers_effective_metadata_then_structure() -> None:
    batch_result = SimpleNamespace(
        final_parameters={"lc_nm_effective": "4.2"},
        structure=SimpleNamespace(lc=7.7),
    )
    structural_result = SimpleNamespace(
        final_parameters={},
        structure=SimpleNamespace(lc=6.1),
    )
    missing_result = SimpleNamespace(final_parameters={}, structure=SimpleNamespace(lc=np.nan))

    assert _result_effective_lc_value(batch_result) == 4.2
    assert _result_effective_lc_value(structural_result) == 6.1
    assert np.isnan(_result_effective_lc_value(missing_result))


def test_saxs_output_reuses_helper_module_functions() -> None:
    saxs_output = importlib.import_module("polynexus.core.saxs_engine.saxs_output")

    assert saxs_output._csv_number is _csv_number
    assert saxs_output._finite_csv is _finite_csv
    assert saxs_output._json_number is _json_number
    assert saxs_output._result_effective_lc_value is _result_effective_lc_value
    assert saxs_output._result_to_params_dict is _result_to_params_dict
    assert saxs_output.export_parameters_csv is export_parameters_csv
    assert saxs_output.export_1d_profile is export_1d_profile
    assert saxs_output.export_strain_series_csv is export_strain_series_csv
    assert saxs_output.export_temp_series_csv is export_temp_series_csv


def test_result_to_params_dict_keeps_final_parameters_and_status_fields() -> None:
    result = SimpleNamespace(
        label="sample-1",
        structure=SimpleNamespace(lc=6.1, la=3.2, phi_c=0.41, phi_c_invariant=0.38, Sv=0.0123, confidence_lc=0.77, lc_tangent_nm=5.4, lc_gamma_min_nm=4.9),
        long_period=SimpleNamespace(L_bragg=12.4, L_lorentz=12.2, L_confidence=0.84, method_used="lorentz"),
        final_parameters={"lc_nm_effective": 4.2, "custom_value": "keep"},
        lc_method="calibrated",
        calibrated_fallback_active=True,
        calibration_skipped_reason="missing_reference",
        melting_window_status="near_onset",
        melting_window_reason="expected_melt_prior_hint",
        lc_reliability_status="usable",
        lc_reliability_reason="stable_structure_support",
        q_peak_snr=8.5,
        effective_q_min=0.125,
        quality_flag="WARN",
        validation_summary="Validation note",
    )

    params = _result_to_params_dict(result)

    assert params["label"] == "sample-1"
    assert params["lc_method"] == "calibrated"
    assert params["calibrated_fallback_active"] is True
    assert params["calibration_skipped_reason"] == "missing_reference"
    assert params["melting_window_status"] == "near_onset"
    assert params["lc_reliability_status"] == "usable"
    assert params["L_bragg"] == 12.4
    assert params["L_lorentz"] == 12.2
    assert params["L_confidence"] == 0.84
    assert params["lc_tangent_nm"] == 5.4
    assert params["lc_gamma_min_nm"] == 4.9
    assert params["q_peak_snr"] == 8.5
    assert params["effective_q_min"] == 0.125
    assert params["custom_value"] == "keep"


def test_export_1d_profile_writes_expected_columns(tmp_path) -> None:
    output_path = export_1d_profile(
        np.asarray([0.1, 0.2, 0.3], dtype=float),
        np.asarray([10.0, 20.0, 30.0], dtype=float),
        str(tmp_path),
    )

    assert Path(output_path).read_text(encoding="utf-8").splitlines() == [
        "q_nm1,I_au",
        "0.1,10.0",
        "0.2,20.0",
        "0.3,30.0",
    ]


def test_export_parameters_csv_accepts_flat_result_objects(tmp_path) -> None:
    result = SimpleNamespace(
        label="sample-1",
        structure=SimpleNamespace(lc=6.1, la=3.2, phi_c=0.41, phi_c_invariant=0.38, Sv=0.0123, confidence_lc=0.77, lc_tangent_nm=5.4, lc_gamma_min_nm=4.9),
        long_period=SimpleNamespace(L_bragg=12.4, L_lorentz=12.2, L_confidence=0.84, method_used="lorentz"),
        final_parameters={"lc_nm_effective": 4.2, "custom_value": "keep"},
        lc_method="calibrated",
        calibrated_fallback_active=True,
        calibration_skipped_reason="missing_reference",
        melting_window_status="near_onset",
        melting_window_reason="expected_melt_prior_hint",
        lc_reliability_status="usable",
        lc_reliability_reason="stable_structure_support",
        q_peak_snr=8.5,
        effective_q_min=0.125,
        quality_flag="WARN",
        validation_summary="Validation note",
    )

    output_path = export_parameters_csv(result, str(tmp_path), filename="params.csv")
    text = Path(output_path).read_text(encoding="utf-8")

    assert "custom_value" in text
    assert "calibrated_fallback_active" in text
    assert "melting_window_status" in text


def test_export_strain_and_temp_series_csv_use_dataframe_export(tmp_path, monkeypatch) -> None:
    class _SeriesResult:
        def __init__(self, rows):
            self._rows = rows

        def to_dataframe(self):
            import pandas as pd

            return pd.DataFrame(self._rows)

    strain_path = export_strain_series_csv(
        _SeriesResult([{"strain": 1, "value": 2}]),
        str(tmp_path),
        filename="strain.csv",
    )
    temp_path = export_temp_series_csv(
        _SeriesResult([{"temperature_C": 200, "value": 3}]),
        str(tmp_path),
        filename="temp.csv",
    )

    assert "strain" in Path(strain_path).read_text(encoding="utf-8")
    assert "temperature_C" in Path(temp_path).read_text(encoding="utf-8")


def test_saxs_output_reuses_data_writer_module_functions() -> None:
    saxs_output = importlib.import_module("polynexus.core.saxs_engine.saxs_output")

    assert saxs_output._write_condition_overview_profile_data is _write_condition_overview_profile_data
    assert saxs_output._write_condition_overview_summary_data is _write_condition_overview_summary_data
    assert saxs_output._write_u1_scattering_data is _write_u1_scattering_data
    assert saxs_output._write_u2_correlation_data is _write_u2_correlation_data
    assert saxs_output._write_u3_idf_data is _write_u3_idf_data
    assert saxs_output._write_u4_porod_data is _write_u4_porod_data
    assert saxs_output._write_guinier_data is _write_guinier_data
    assert saxs_output._write_kratky_data is _write_kratky_data
    assert saxs_output._write_joint_crystallinity_data is _write_joint_crystallinity_data
    assert saxs_output._write_series_waterfall_data is _write_series_waterfall_data
    assert saxs_output._write_t3_structure_data is _write_t3_structure_data
    assert saxs_output._write_t4_invariant_data is _write_t4_invariant_data
    assert saxs_output._write_v2_temperature_parameters_data is _write_v2_temperature_parameters_data
    assert saxs_output._write_v3_heatmap_data is _write_v3_heatmap_data
    assert saxs_output._write_v3_qstar_data is _write_v3_qstar_data
    assert saxs_output._write_v4_avrami_data is _write_v4_avrami_data


def test_saxs_output_reuses_document_module_functions() -> None:
    saxs_output = importlib.import_module("polynexus.core.saxs_engine.saxs_output")

    assert saxs_output._save_u1_scattering_document is _save_u1_scattering_document
    assert saxs_output._save_u2_correlation_document is _save_u2_correlation_document
    assert saxs_output._save_u3_idf_document is _save_u3_idf_document
    assert saxs_output._save_u4_porod_document is _save_u4_porod_document
    assert saxs_output._save_guinier_document is _save_guinier_document
    assert saxs_output._save_kratky_document is _save_kratky_document
    assert saxs_output._save_joint_crystallinity_document is _save_joint_crystallinity_document
    assert saxs_output._save_series_waterfall_document is _save_series_waterfall_document
    assert saxs_output._save_t3_structure_document is _save_t3_structure_document
    assert saxs_output._save_t4_invariant_document is _save_t4_invariant_document
    assert saxs_output._save_v2_temperature_parameters_document is _save_v2_temperature_parameters_document
    assert saxs_output._save_v3_heatmap_document is _save_v3_heatmap_document
    assert saxs_output._save_v4_avrami_document is _save_v4_avrami_document
    assert saxs_output._save_static_overview_document is _save_static_overview_document
    assert saxs_output._save_condition_overview_document is _save_condition_overview_document


def test_write_condition_overview_profile_data_writes_expected_rows(tmp_path) -> None:
    figure_path = tmp_path / "figures" / "overview.pdf"
    figure_path.parent.mkdir(parents=True, exist_ok=True)

    data_path = _write_condition_overview_profile_data(
        str(figure_path),
        np.asarray([100.0, 110.0], dtype=float),
        [np.asarray([0.1, 0.2], dtype=float), np.asarray([0.1, 0.2], dtype=float)],
        [np.asarray([10.0, 20.0], dtype=float), np.asarray([11.0, 21.0], dtype=float)],
    )

    lines = data_path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "condition_index,condition_value,q_nm_inv,intensity,iq2,iq2_offset"
    assert "condition_index,condition_value" not in lines[1]
    assert "100.0" in lines[1]


def test_write_static_overview_summary_data_writes_expected_columns(tmp_path) -> None:
    figure_path = tmp_path / "figures" / "static.pdf"
    figure_path.parent.mkdir(parents=True, exist_ok=True)

    data_path = _write_static_overview_summary_data(
        str(figure_path),
        ["A", "B"],
        [12.3, 13.4],
        [4.5, 5.6],
        [0.41, 0.42],
        [0.9, 0.8],
    )

    lines = data_path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "sample_index,label,L_nm,lc_nm,Xc,Q_rel"
    assert "A" in lines[1]
    assert "12.3" in lines[1]


def test_write_v2_temperature_parameters_data_writes_q_and_xc_columns(tmp_path) -> None:
    figure_path = tmp_path / "figures" / "temp.pdf"
    figure_path.parent.mkdir(parents=True, exist_ok=True)

    data_path = _write_v2_temperature_parameters_data(
        str(figure_path),
        np.asarray([30.0, 80.0], dtype=float),
        np.asarray([15.0, 16.0], dtype=float),
        np.asarray([8.0, 8.4], dtype=float),
        np.asarray([100.0, 105.0], dtype=float),
        np.asarray([0.4, 0.38], dtype=float),
    )

    lines = data_path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "temperature_C,L_nm,lc_nm,la_nm,Q_star,Xc"
    assert "30.0" in lines[1]
    assert "0.4" in lines[1]


def test_write_u1_scattering_data_writes_expected_plot_columns(tmp_path) -> None:
    figure_path = tmp_path / "figures" / "u1.pdf"
    figure_path.parent.mkdir(parents=True, exist_ok=True)

    data_path = _write_u1_scattering_data(
        str(figure_path),
        np.asarray([0.1, 0.2], dtype=float),
        np.asarray([10.0, 20.0], dtype=float),
    )

    assert data_path.name == "u1_data.csv"
    assert data_path.read_text(encoding="utf-8").splitlines() == [
        "q_nm_inv,intensity,iq2",
        "0.1,10.0,0.1",
        "0.2,20.0,0.8",
    ]


def test_write_u4_porod_data_writes_fit_column_when_slope_is_available(tmp_path) -> None:
    figure_path = tmp_path / "figures" / "u4.pdf"
    figure_path.parent.mkdir(parents=True, exist_ok=True)

    data_path = _write_u4_porod_data(
        str(figure_path),
        np.asarray([0.2, 0.3], dtype=float),
        np.asarray([1.2, 1.35], dtype=float),
        slope=0.25,
    )

    lines = data_path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "q_nm_inv,q4_nm_minus4,Iq4,fit"
    assert ",1.2," in lines[1]
    assert ",1.35," in lines[2]
