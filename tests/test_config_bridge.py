from __future__ import annotations

from polynexus.config_bridge import DSC_PARAM_MAP, SAXS_PARAM_MAP, WAXS_PARAM_MAP, apply_changes
from polynexus.core.dsc_engine.config import DSCConfig
from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.waxs_engine.config import WAXSConfig


def test_apply_changes_updates_waxs_peak_function() -> None:
    config = WAXSConfig(peak_function="gaussian")

    ok, error = apply_changes(config, {"peak_function": "pseudo_voigt"})

    assert ok is True
    assert error == ""
    assert config.peak_function == "pseudo_voigt"


def test_waxs_param_map_covers_phase13_waxs_parameters() -> None:
    assert set(WAXS_PARAM_MAP) == {
        "peak_function",
        "smooth_window",
        "background_method",
        "arpls_lam",
        "amorphous_subtraction",
        "amorphous_n_peaks",
        "peak_distance",
        "two_theta_offset",
        "max_peaks",
    }


def test_apply_changes_rejects_unknown_parameter_without_mutation() -> None:
    config = WAXSConfig(peak_function="gaussian")

    ok, error = apply_changes(config, {"not_a_param": 1})

    assert ok is False
    assert "Unknown WAXS parameter" in error
    assert config.peak_function == "gaussian"


def test_apply_changes_rejects_out_of_range_without_mutation() -> None:
    config = WAXSConfig(max_peaks=8)

    ok, error = apply_changes(config, {"max_peaks": 99})

    assert ok is False
    assert "out of range" in error
    assert config.max_peaks == 8


def test_apply_changes_rejects_even_smooth_window() -> None:
    config = WAXSConfig(smooth_window=5)

    ok, error = apply_changes(config, {"smooth_window": 4})

    assert ok is False
    assert "smooth_window must be odd" in error
    assert config.smooth_window == 5


def test_apply_changes_rejects_peak_group_dependency() -> None:
    config = WAXSConfig(peak_distance=0.8, max_peaks=8)

    ok, error = apply_changes(config, {"peak_distance": 0.6, "max_peaks": 10})

    assert ok is False
    assert "peak_distance before changing max_peaks" in error
    assert config.peak_distance == 0.8
    assert config.max_peaks == 8


def test_apply_changes_updates_dsc_baseline_alias() -> None:
    config = DSCConfig(baseline_corr="auto")

    ok, error = apply_changes(config, {"baseline_type": "linear"})

    assert ok is True
    assert error == ""
    assert config.baseline_corr == "linear"


def test_dsc_param_map_contains_b1_whitelist() -> None:
    assert {
        "baseline_type",
        "peak_function",
        "tm_search_low_C",
        "tm_search_high_C",
    } <= set(DSC_PARAM_MAP)


def test_apply_changes_rejects_invalid_dsc_tm_range_without_mutation() -> None:
    config = DSCConfig(Tm_search_low_C=100.0, Tm_search_high_C=300.0)

    ok, error = apply_changes(config, {"tm_search_low_C": 250.0, "tm_search_high_C": 200.0})

    assert ok is False
    assert "tm_search_low_C" in error
    assert config.Tm_search_low_C == 100.0
    assert config.Tm_search_high_C == 300.0


def test_apply_changes_updates_saxs_q_bragg_min() -> None:
    config = SAXSConfig(q_bragg_min=0.15)

    ok, error = apply_changes(config, {"q_bragg_min": 0.2}, technique="saxs")

    assert ok is True
    assert error == ""
    assert config.q_bragg_min == 0.2


def test_saxs_param_map_contains_static_analyze_whitelist() -> None:
    assert {
        "q_bragg_min",
        "q_bragg_max",
        "q_corr_min",
        "q_corr_max",
        "idf_peak_rel_thresh",
        "idf_valley_rel_thresh",
        "tangent_lc_min_nm",
        "T_melt_expected",
        "savgol_window",
        "savgol_order",
        "lorentz_fit_method",
    } <= set(SAXS_PARAM_MAP)


def test_apply_changes_rejects_invalid_saxs_range_without_mutation() -> None:
    config = SAXSConfig(q_bragg_min=0.15, q_bragg_max=0.9)

    ok, error = apply_changes(config, {"q_bragg_min": 1.0, "q_bragg_max": 0.8}, technique="saxs")

    assert ok is False
    assert "q_bragg_min" in error
    assert config.q_bragg_min == 0.15
    assert config.q_bragg_max == 0.9


def test_apply_changes_rejects_invalid_saxs_savgol_dependency() -> None:
    config = SAXSConfig(savgol_window=7, savgol_order=2)

    ok, error = apply_changes(config, {"savgol_window": 3, "savgol_order": 3}, technique="saxs")

    assert ok is False
    assert "savgol_window must be greater than savgol_order" in error
    assert config.savgol_window == 7
    assert config.savgol_order == 2


def test_apply_changes_updates_saxs_expected_melt_temperature() -> None:
    config = SAXSConfig(T_melt_expected=None)

    ok, error = apply_changes(config, {"T_melt_expected": 221.5}, technique="saxs")

    assert ok is True
    assert error == ""
    assert config.T_melt_expected == 221.5
