from __future__ import annotations

import copy

import pandas as pd

from polynexus.core.saxs_engine.saxs_strain import (
    StrainPointResult,
    StrainSeriesResult,
)
from polynexus.core.saxs_engine.saxs_temperature import (
    TempSeriesResult,
    TemperaturePointResult,
)


_METRIC_LABELS = ("Porod", "Kratky", "Invariant", "Lamellar")


def _assert_metric_columns(table: pd.DataFrame) -> None:
    for label in _METRIC_LABELS:
        assert f"{label}_level" in table.columns
        assert f"{label}_coverage" in table.columns
        assert f"{label}_reason_codes" in table.columns


def test_temperature_dataframe_projects_existing_metric_evidence_without_mutation():
    metric_evidence = {
        "porod": {
            "level": "Diagnostic",
            "coverage_fraction": 0.5,
            "reason_codes": ["series_metric_missing_frames"],
        },
        "kratky": {
            "level": "Trend",
            "coverage_fraction": 1.0,
            "reason_codes": [],
        },
    }
    before = copy.deepcopy(metric_evidence)

    table = TempSeriesResult(
        temp_points=[
            TemperaturePointResult(
                source_index=4,
                temperature_C=180.0,
                metric_evidence=metric_evidence,
            )
        ]
    ).to_dataframe()

    _assert_metric_columns(table)
    row = table.iloc[0]
    assert row["Porod_level"] == "Diagnostic"
    assert row["Porod_coverage"] == 0.5
    assert row["Porod_reason_codes"] == "series_metric_missing_frames"
    assert row["Kratky_level"] == "Trend"
    assert row["Kratky_coverage"] == 1.0
    assert pd.isna(row["Invariant_level"])
    assert pd.isna(row["Lamellar_reason_codes"])
    assert metric_evidence == before


def test_strain_dataframe_projects_unusable_and_complete_metric_evidence():
    table = StrainSeriesResult(
        strain_points=[
            StrainPointResult(
                strain_pct=12.0,
                metric_evidence={
                    "invariant": {
                        "level": "Unusable",
                        "coverage_fraction": 0.0,
                        "reason_codes": ("invariant_value_invalid",),
                    },
                    "lamellar": {
                        "level": "Trend",
                        "coverage_fraction": 1.0,
                        "reason_codes": ("series_level_capped_at_trend",),
                    },
                },
            )
        ]
    ).to_dataframe()

    _assert_metric_columns(table)
    row = table.iloc[0]
    assert row["Invariant_level"] == "Unusable"
    assert row["Invariant_coverage"] == 0.0
    assert row["Invariant_reason_codes"] == "invariant_value_invalid"
    assert row["Lamellar_level"] == "Trend"
    assert row["Lamellar_reason_codes"] == "series_level_capped_at_trend"
    assert "Metric_evidence_levels" in table.columns


def test_dataframe_metric_projection_fails_closed_for_malformed_payload():
    table = TempSeriesResult(
        temp_points=[
            TemperaturePointResult(
                metric_evidence={
                    "porod": {
                        "level": "Diagnostic",
                        "coverage_fraction": "not-a-number",
                        "reason_codes": "raw_reason",
                    },
                    "kratky": "malformed",
                }
            )
        ]
    ).to_dataframe()

    assert pd.isna(table.iloc[0]["Porod_coverage"])
    assert table.iloc[0]["Porod_reason_codes"] == "raw_reason"
    assert pd.isna(table.iloc[0]["Kratky_level"])
