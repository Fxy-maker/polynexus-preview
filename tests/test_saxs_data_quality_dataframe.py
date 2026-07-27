from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd

from polynexus.core.saxs_engine.saxs_output_helpers import (
    _result_to_params_dict,
    export_parameters_csv,
)
from polynexus.core.saxs_engine.saxs_strain import (
    StrainPhase,
    StrainPointResult,
    StrainSeriesResult,
)
from polynexus.core.saxs_engine.saxs_temperature import (
    TempPhase,
    TempSeriesResult,
    TemperaturePointResult,
)


_REPORT = {
    "source_id": "frame-7",
    "raw_data_ref": "raw/frame-7.edf",
    "processed_data_ref": "saxs_result:I_smooth",
    "processing_config_ref": "SAXSConfig",
    "level": "Trend",
    "reason_codes": ["q_duplicate", "low_q_truncated"],
    "actions": ["drop_nonfinite", "truncate_low_q"],
    "low_q_truncated": True,
    "original_point_count": 24,
    "finite_point_count": 22,
    "usable_point_count": 18,
    "invalid_point_count": 6,
    "nonfinite_q_count": 1,
    "nonpositive_q_count": 1,
    "nonfinite_intensity_count": 1,
    "nonpositive_intensity_count": 1,
    "duplicate_q_count": 2,
    "nonmonotonic_q": True,
}


def _expected_columns() -> set[str]:
    return {
        "Data_quality_source_id",
        "Data_quality_raw_data_ref",
        "Data_quality_processed_data_ref",
        "Data_quality_processing_config_ref",
        "Data_quality_level",
        "Data_quality_reason_codes",
        "Data_quality_actions",
        "Data_quality_low_q_truncated",
        "Data_quality_original_point_count",
        "Data_quality_finite_point_count",
        "Data_quality_usable_point_count",
        "Data_quality_invalid_point_count",
        "Data_quality_nonfinite_q_count",
        "Data_quality_nonpositive_q_count",
        "Data_quality_nonfinite_intensity_count",
        "Data_quality_nonpositive_intensity_count",
        "Data_quality_duplicate_q_count",
        "Data_quality_nonmonotonic_q",
    }


def _assert_report_fields(row) -> None:
    assert row["Data_quality_source_id"] == "frame-7"
    assert row["Data_quality_raw_data_ref"] == "raw/frame-7.edf"
    assert row["Data_quality_processed_data_ref"] == "saxs_result:I_smooth"
    assert row["Data_quality_processing_config_ref"] == "SAXSConfig"
    assert row["Data_quality_level"] == "Trend"
    assert row["Data_quality_reason_codes"] == "q_duplicate|low_q_truncated"
    assert row["Data_quality_actions"] == "drop_nonfinite|truncate_low_q"
    assert bool(row["Data_quality_low_q_truncated"]) is True
    assert row["Data_quality_original_point_count"] == 24
    assert row["Data_quality_finite_point_count"] == 22
    assert row["Data_quality_usable_point_count"] == 18
    assert row["Data_quality_invalid_point_count"] == 6
    assert row["Data_quality_duplicate_q_count"] == 2
    assert bool(row["Data_quality_nonmonotonic_q"]) is True


def test_temperature_and_strain_rows_export_existing_data_quality_report() -> None:
    temperature = TempSeriesResult(
        temp_points=[
            TemperaturePointResult(
                source_index=7,
                temperature_C=210.0,
                phase=TempPhase.MELT,
                data_quality_report=_REPORT,
            )
        ]
    )
    strain = StrainSeriesResult(
        strain_points=[
            StrainPointResult(
                strain_pct=8.0,
                phase=StrainPhase.PLASTIC_VOIDING,
                data_quality_report=_REPORT,
            )
        ]
    )

    temperature_table = temperature.to_dataframe()
    strain_table = strain.to_dataframe()

    assert _expected_columns() <= set(temperature_table.columns)
    assert _expected_columns() <= set(strain_table.columns)
    _assert_report_fields(temperature_table.iloc[0])
    _assert_report_fields(strain_table.iloc[0])
    assert temperature_table.iloc[0]["source_index"] == 7
    assert strain_table.iloc[0]["Strain(%)"] == 8.0


def test_missing_reports_keep_series_rows_and_empty_quality_fields() -> None:
    temperature_table = TempSeriesResult(
        temp_points=[
            TemperaturePointResult(
                source_index=3,
                temperature_C=190.0,
                data_quality_report=_REPORT,
            ),
            TemperaturePointResult(
                source_index=9,
                temperature_C=200.0,
            ),
        ]
    ).to_dataframe()
    strain_table = StrainSeriesResult(
        strain_points=[
            StrainPointResult(strain_pct=1.0),
            StrainPointResult(strain_pct=2.0, data_quality_report=_REPORT),
        ]
    ).to_dataframe()

    assert len(temperature_table) == 2
    assert list(temperature_table["source_index"]) == [3, 9]
    assert len(strain_table) == 2
    assert list(strain_table["Strain(%)"]) == [1.0, 2.0]
    for column in _expected_columns():
        assert pd.isna(temperature_table.iloc[1][column])
        assert pd.isna(strain_table.iloc[0][column])


def test_static_parameter_and_csv_exports_flatten_existing_report(tmp_path) -> None:
    result = SimpleNamespace(
        label="static-frame",
        structure=SimpleNamespace(
            L=12.0,
            lc=3.0,
            la=9.0,
            phi_c=0.4,
            phi_c_invariant=np.nan,
            Sv=np.nan,
            confidence_lc=np.nan,
            lc_tangent_nm=np.nan,
            lc_gamma_min_nm=np.nan,
            Q_invariant=np.nan,
        ),
        long_period=SimpleNamespace(
            L_bragg=np.nan,
            L_lorentz=np.nan,
            L_confidence=np.nan,
            method_used="",
        ),
        final_parameters={},
        data_quality_report=_REPORT,
        Q_star_valid=False,
        quality_flag="WARN",
        validation_summary="dirty input review required",
    )

    params = _result_to_params_dict(result)
    output_path = export_parameters_csv(result, str(tmp_path), filename="params.csv")
    csv_text = open(output_path, encoding="utf-8").read()

    assert _expected_columns() <= set(params)
    _assert_report_fields(params)
    assert "Data_quality_reason_codes" in csv_text
    assert "q_duplicate|low_q_truncated" in csv_text
