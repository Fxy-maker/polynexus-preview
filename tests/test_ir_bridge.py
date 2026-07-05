from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any

import numpy as np

from polynexus.config_bridge import IR_PARAM_MAP, apply_changes
from polynexus.core.ir_engine import IRConfig, analyze_spectrum, load_spectrum, preprocess_pipeline
from polynexus.core.ir_residual_analyzer import IRResidualAnalyzer
from polynexus.orchestrator import ParameterOrchestrator


class NoopAdvisor:
    last_prompt = ""

    def advise(self, state: dict[str, Any]) -> dict[str, Any]:
        self.last_prompt = "IR noop prompt"
        return {
            "assessment": "PASS",
            "confidence": 1.0,
            "reasoning": "No change needed for test.",
            "changes": {},
            "expected_improvement": {},
            "risk": "low",
            "suggestions": [],
            "reference_cases": [],
            "converge": True,
            "llm_used": False,
        }


def _local_tmp_dir() -> Path:
    path = Path(__file__).resolve().parent / "_tmp_ir_bridge" / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def _gaussian(x: np.ndarray, mu: float, sigma: float, amp: float) -> np.ndarray:
    return amp * np.exp(-0.5 * ((x - mu) / sigma) ** 2)


def _write_ir_file(path: Path) -> None:
    wn = np.linspace(4000.0, 550.0, 2200)
    rng = np.random.default_rng(42)
    absorbance = (
        0.03
        + 0.000015 * (wn - wn.mean())
        + _gaussian(wn, 3298.0, 24.0, 0.35)
        + _gaussian(wn, 2931.0, 18.0, 0.22)
        + _gaussian(wn, 1637.0, 20.0, 0.82)
        + _gaussian(wn, 1541.0, 18.0, 0.65)
        + _gaussian(wn, 1263.0, 16.0, 0.30)
        + 0.004 * np.sin(wn / 13.0)
        + rng.normal(0.0, 0.008, size=wn.shape)
    )
    np.savetxt(path, np.column_stack([wn, absorbance]), fmt="%.8f", delimiter=",")


def test_ir_param_map_and_apply_changes_update_config() -> None:
    config = IRConfig(smooth_window=7, peak_height_min=0.02, wavenumber_range=(400.0, 4000.0))

    ok, error = apply_changes(
        config,
        {
            "peak_threshold": 0.04,
            "smooth_window": 11,
            "wavenumber_min": 600.0,
            "normalization_method": "peak",
        },
        technique="ir",
    )

    assert ok is True
    assert error == ""
    assert config.peak_height_min == 0.04
    assert config.smooth_window == 11
    assert config.wavenumber_range == (600.0, 4000.0)
    assert config.normalization_method == "peak"
    assert {
        "baseline_method",
        "smooth_window",
        "peak_threshold",
        "wavenumber_min",
        "wavenumber_max",
        "normalization_method",
    } <= set(IR_PARAM_MAP)


def test_ir_residual_analyzer_identifies_peak_mismatch() -> None:
    wn = np.linspace(4000.0, 550.0, 1200)
    fit = _gaussian(wn, 1637.0, 18.0, 0.8)
    obs = fit + _gaussian(wn, 1637.0, 10.0, 0.2)

    pattern = IRResidualAnalyzer.analyze(wn, obs, fit)

    assert pattern.residual_type == "key_band_mismatch"
    assert "cm^-1" in pattern.max_residual_region
    assert pattern.summary


def test_ir_action_registry_maps_key_band_mismatch_to_tighten_key_band_fit() -> None:
    from polynexus.core.ir_action_registry import actions_for_symptoms, allowed_changes_for_actions

    actions = actions_for_symptoms([
        {"name": "key_band_mismatch"},
        {"name": "assignment_without_characteristic_bands"},
    ], technique="IR")
    names = [item["name"] for item in actions]

    assert "tighten_key_band_fit" in names
    assert "expand_band_window" in names

    allowed_changes = allowed_changes_for_actions(actions, technique="IR")
    assert "peak_fit_window_cm1" in allowed_changes
    assert "peak_prominence_min" in allowed_changes
    assert "peak_height_min" in allowed_changes


def test_ir_action_registry_maps_temperature_2d_symptoms_to_controlled_actions() -> None:
    from polynexus.core.ir_action_registry import actions_for_symptoms, allowed_changes_for_actions

    actions = actions_for_symptoms(
        [
            {"name": "negative_matrix_fraction_high"},
            {"name": "band_index_jump_single_frame"},
            {"name": "temperature_trend_not_reproducible"},
            {"name": "cross_peak_without_band_assignment"},
            {"name": "async_peak_without_sync_support"},
        ],
        technique="IR",
    )
    names = [item["name"] for item in actions]

    assert "stabilize_matrix_baseline" in names
    assert "stabilize_band_tracking" in names
    assert "tighten_cross_peak_assignment" in names

    allowed_changes = allowed_changes_for_actions(actions, technique="IR")
    assert "baseline_method" in allowed_changes
    assert "normalization_method" in allowed_changes
    assert "peak_fit_window_cm1" in allowed_changes
    assert "peak_distance" in allowed_changes
    assert "assignment_tolerance_cm1" in allowed_changes
    assert "cross_peak_exclusion_cm1" in allowed_changes


def test_ir_orchestrator_runs_noop_round() -> None:
    tmp_path = _local_tmp_dir()
    try:
        data_path = tmp_path / "pa6_ir.csv"
        _write_ir_file(data_path)

        report = ParameterOrchestrator(
            technique="ir",
            data_file=str(data_path),
            polymer_name="PA6",
            max_rounds=1,
            advisor=NoopAdvisor(),
        ).run()

        assert report["technique"] == "ir"
        assert report["submodule"] == "standard"
        assert report["history"][0]["output_parameters"]["n_peaks"] >= 4
        assert report["history"][0]["residuals_pattern"]["summary"]
        assert report["best_r_squared"] >= report["baseline_r_squared"]
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_ir_r_squared_changes_with_smooth_window() -> None:
    tmp_path = _local_tmp_dir()
    try:
        data_path = tmp_path / "pa6_ir.csv"
        _write_ir_file(data_path)
        spec = load_spectrum(str(data_path))

        scores = []
        for smooth_window in (3, 15):
            cfg = IRConfig(polymer_name="PA6", smooth_window=smooth_window)
            processed = preprocess_pipeline(spec, cfg)
            result = analyze_spectrum(processed, cfg, label=spec.label, polymer_name="PA6")
            scores.append(result.r_squared)

        assert all(np.isfinite(score) for score in scores)
        assert abs(scores[0] - scores[1]) > 1e-5
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)
