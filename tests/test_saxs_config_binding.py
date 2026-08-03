from __future__ import annotations

import json

from polynexus.core.saxs_config_binding import (
    apply_saxs_config_panel_values,
    saxs_config_snapshot,
)
from polynexus.core.saxs_engine.config import (
    SAXSConfig,
    TENSILE_AXIS_CONVENTION,
)


def test_saxs_panel_aliases_apply_with_explicit_conversion_and_report() -> None:
    config = SAXSConfig()

    report = apply_saxs_config_panel_values(
        config,
        {
            "smooth_window": "11",
            "q_range_min": "0.12",
            "q_range_max": 2.2,
            "integration_mode": "pyFAI",
            "baseline_method": "subtract",
        },
    )

    assert report["unavailable"] == {}
    assert config.savgol_window == 11
    assert config.q_min == 0.12
    assert config.q_max == 2.2
    assert config.use_pyfai_integration is True
    assert report["diagnostic_only"]["baseline_method"]


def test_saxs_panel_binding_preserves_zero_and_reports_unknown_keys() -> None:
    config = SAXSConfig()

    report = apply_saxs_config_panel_values(
        config,
        {"crystallinity": 0, "T_melt_expected": 0.0, "not_a_key": 1},
    )

    assert config.crystallinity == 0.0
    assert config.T_melt_expected == 0.0
    assert report["normalized_values"]["crystallinity"] == 0.0
    assert report["unavailable"]["not_a_key"] == "unknown_panel_key"


def test_saxs_config_snapshot_is_strict_json_safe() -> None:
    config = SAXSConfig(crystallinity=float("nan"), T_melt_expected=float("inf"))

    snapshot = saxs_config_snapshot(config)

    assert snapshot["crystallinity"] is None
    assert snapshot["T_melt_expected"] is None
    json.dumps(snapshot, allow_nan=False)


def test_tensile_axis_binding_keeps_none_distinct_from_zero_and_records_provenance() -> None:
    empty = SAXSConfig()
    empty_report = apply_saxs_config_panel_values(
        empty,
        {
            "tensile_axis_deg": None,
            "tensile_axis_convention": TENSILE_AXIS_CONVENTION,
        },
    )
    assert empty.tensile_axis_deg is None
    assert empty_report["normalized_values"]["tensile_axis_deg"] is None

    zero = SAXSConfig()
    zero_report = apply_saxs_config_panel_values(
        zero,
        {
            "tensile_axis_deg": 180.0,
            "tensile_axis_convention": TENSILE_AXIS_CONVENTION,
        },
    )
    assert zero.tensile_axis_deg == 0.0
    assert zero.tensile_axis_convention == TENSILE_AXIS_CONVENTION
    assert zero_report["normalized_values"]["tensile_axis_deg"] == 0.0
    assert zero_report["provenance"]["tensile_axis_deg"]["source"] == (
        "explicit_run_config"
    )


def test_tensile_axis_binding_rejects_unknown_convention_without_partial_apply() -> None:
    config = SAXSConfig()

    report = apply_saxs_config_panel_values(
        config,
        {
            "tensile_axis_deg": 45.0,
            "tensile_axis_convention": "screen_angle_v0",
        },
    )

    assert config.tensile_axis_deg is None
    assert config.tensile_axis_convention is None
    assert report["unavailable"]["tensile_axis_deg"] == (
        "unsupported_tensile_axis_convention"
    )
