from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd

from polynexus.core.saxs_engine.saxs_output_helpers import _result_to_params_dict
from polynexus.core.saxs_engine.saxs_strain import (
    StrainPhase,
    StrainPointResult,
    StrainSeriesResult,
)
from polynexus.core.saxs_engine.saxs_temperature import (
    TemperaturePointResult,
    TempPhase,
    TempSeriesResult,
)


_REPORT = {
    "source_kind": "raw_detector",
    "level": "Diagnostic",
    "reason_codes": ["detector_saturation_unknown", "beam_center_missing"],
    "geometry_provenance": {
        "source": "mixed",
        "field_sources": {
            "sdd_m": "header",
            "beam_center_x": "config_default",
        },
        "validity": "not_assessed",
    },
    "mask_provenance": {
        "source": "saxs_config.dummy_value",
        "configured": True,
        "shape": [128, 256],
        "validity": "not_assessed",
    },
}


def _expected_columns() -> set[str]:
    return {
        "Detector_source_kind",
        "Detector_quality_level",
        "Detector_reason_codes",
        "Geometry_provenance_source",
        "Geometry_field_sources",
        "Geometry_provenance_validity",
        "Mask_provenance_source",
        "Mask_configured",
        "Mask_shape",
        "Mask_provenance_validity",
    }


def test_temperature_dataframe_exports_aligned_detector_provenance() -> None:
    point = TemperaturePointResult(
        source_index=7,
        temperature_C=210.0,
        phase=TempPhase.MELT,
        raw_detector_quality_report=_REPORT,
    )

    table = TempSeriesResult(temp_points=[point]).to_dataframe()

    assert _expected_columns() <= set(table.columns)
    row = table.iloc[0]
    assert row["source_index"] == 7
    assert row["Detector_source_kind"] == "raw_detector"
    assert row["Detector_quality_level"] == "Diagnostic"
    assert row["Detector_reason_codes"] == "detector_saturation_unknown|beam_center_missing"
    assert row["Geometry_provenance_source"] == "mixed"
    assert row["Geometry_field_sources"] == "beam_center_x:config_default|sdd_m:header"
    assert row["Geometry_provenance_validity"] == "not_assessed"
    assert row["Mask_provenance_source"] == "saxs_config.dummy_value"
    assert bool(row["Mask_configured"]) is True
    assert row["Mask_shape"] == "128x256"
    assert row["Mask_provenance_validity"] == "not_assessed"


def test_strain_dataframe_keeps_missing_detector_report_as_missing_row_fields() -> None:
    point = StrainPointResult(strain_pct=8.0, phase=StrainPhase.PLASTIC_VOIDING)

    table = StrainSeriesResult(strain_points=[point]).to_dataframe()

    assert _expected_columns() <= set(table.columns)
    assert len(table) == 1
    assert table.iloc[0]["Strain(%)"] == 8.0
    for column in _expected_columns():
        assert pd.isna(table.iloc[0][column])


def test_static_parameter_projection_exports_the_same_detector_provenance_fields() -> None:
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
        raw_detector_quality_report=_REPORT,
        Q_star_valid=False,
        quality_flag="WARN",
        validation_summary="detector review required",
    )

    params = _result_to_params_dict(result)

    assert _expected_columns() <= set(params)
    assert params["Geometry_field_sources"] == "beam_center_x:config_default|sdd_m:header"
    assert params["Mask_shape"] == "128x256"
    assert params["Geometry_provenance_validity"] == "not_assessed"
    assert params["Mask_provenance_validity"] == "not_assessed"
