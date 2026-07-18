from __future__ import annotations

import json

from polynexus.core.saxs_config_binding import (
    apply_saxs_config_panel_values,
    saxs_config_snapshot,
)
from polynexus.core.saxs_engine.config import SAXSConfig


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
