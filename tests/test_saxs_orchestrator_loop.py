from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from polynexus.orchestrator import ParameterOrchestrator


class _FakeResult:
    def __init__(self, params: dict[str, Any]) -> None:
        self.parameters = dict(params)
        self.analysis_evidence = {}

    def set_analysis_evidence(self, evidence: dict[str, Any]) -> None:
        self.analysis_evidence = dict(evidence)


class _FakeSAXSConfig:
    def __init__(self) -> None:
        self.q_bragg_min = 0.15
        self.q_bragg_max = 0.90
        self.q_corr_min = 0.15
        self.q_corr_max = 1.20
        self.idf_peak_rel_thresh = 0.05
        self.idf_valley_rel_thresh = 0.05
        self.tangent_lc_min_nm = 2.0
        self.savgol_window = 7
        self.savgol_order = 3
        self.lorentz_fit_method = "lmfit"
        self.condition_context: dict[str, Any] = {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "q_bragg_min": self.q_bragg_min,
            "q_bragg_max": self.q_bragg_max,
            "q_corr_min": self.q_corr_min,
            "q_corr_max": self.q_corr_max,
            "idf_peak_rel_thresh": self.idf_peak_rel_thresh,
            "idf_valley_rel_thresh": self.idf_valley_rel_thresh,
            "tangent_lc_min_nm": self.tangent_lc_min_nm,
            "savgol_window": self.savgol_window,
            "savgol_order": self.savgol_order,
            "lorentz_fit_method": self.lorentz_fit_method,
            "condition_context": dict(self.condition_context),
        }


class _FakeSAXSLongPeriod:
    def __init__(self, *, l_bragg: float, l_corr_peak: float, l_confidence: float) -> None:
        self.L_bragg = l_bragg
        self.L_lorentz = l_bragg
        self.L_corr_peak = l_corr_peak
        self.L_confidence = l_confidence


class _FakeSAXSAnalysis:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.q = [0.10, 0.20, 0.30, 0.40]
        self.I = [1.0, 1.2, 1.1, 0.9]
        self.I_smooth = [1.0, 1.18, 1.08, 0.88]
        self.r_squared = payload["r_squared"]
        self.quality_score = payload["quality_score"]
        self.r_squared_method = "saxs_peak_region_fit_r2"
        self.fit_rmse = payload["fit_rmse"]
        self.fit_regions = payload["fit_regions"]
        self.q_peak_snr = payload["q_peak_snr"]
        self.quality_flag = payload["quality_flag"]
        self.validation_summary = payload["validation_summary"]
        self.condition_value = 25.0
        self.long_period = _FakeSAXSLongPeriod(
            l_bragg=payload["L_bragg"],
            l_corr_peak=payload["L_corr_peak"],
            l_confidence=payload["L_confidence"],
        )


class _ScriptedSAXSEngine:
    def __init__(self, profile_fn: Callable[[_FakeSAXSConfig], dict[str, Any] | None]) -> None:
        self.cfg = _FakeSAXSConfig()
        self.result = _FakeResult({})
        self._profile_fn = profile_fn
        self._analysis = None
        self._batch_results: list[Any] = []
        self.analyze_calls = 0
        self._apply_profile()

    def _apply_profile(self) -> None:
        payload = self._profile_fn(self.cfg)
        if payload is None:
            raise RuntimeError("Baseline SAXS profile must be available.")
        self.result.parameters = dict(payload)
        self._analysis = _FakeSAXSAnalysis(payload)

    def run_pipeline(self, *args: Any, **kwargs: Any) -> _FakeResult:
        self._apply_profile()
        return self.result

    def analyze(self) -> bool:
        self.analyze_calls += 1
        payload = self._profile_fn(self.cfg)
        if payload is None:
            return False
        self.result.parameters = dict(payload)
        self._analysis = _FakeSAXSAnalysis(payload)
        return True

    def get_parameters(self) -> dict[str, Any]:
        return dict(self.result.parameters)


class _PeakWindowAdvisor:
    def advise(self, state: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        return {
            "assessment": "WARN",
            "confidence": 0.78,
            "diagnosis": "peak_window_mismatch",
            "target_symptom": "peak_window_mismatch",
            "reasoning": "Probe two guarded Bragg window moves and keep the better evidence path.",
            "recommended_actions": [
                {
                    "name": "adjust_peak_window",
                    "reason": "Bragg peak placement is drifting.",
                    "expected_evidence_change": "q_peak_diff_pct should shrink",
                }
            ],
            "changes": {},
            "expected_improvement": {"objective_score": "increase"},
            "risk": "low",
            "suggestions": [],
            "reference_cases": [],
            "llm_used": False,
        }


def _peak_window_state(orchestrator: ParameterOrchestrator, engine: Any, round_num: int) -> dict[str, Any]:
    return {
        "case_id": "fake_saxs_round",
        "technique": "SAXS",
        "submodule": "saxs.static",
        "data_file": "dummy.dat",
        "polymer_name": "PA6",
        "round": round_num,
        "current_config": orchestrator._config_snapshot(engine),
        "params": orchestrator._output_parameters(engine),
        "output_parameters": orchestrator._output_parameters(engine),
        "r_squared": 0.0,
        "residuals_pattern": "peak window mismatch",
        "residual_pattern": {"residual_type": "peak_mismatch", "summary": "peak window mismatch"},
        "analysis_evidence": {},
        "symptoms": [
            {
                "name": "peak_window_mismatch",
                "summary": "Bragg peak window is unstable.",
                "target_params": ["q_bragg_min", "q_bragg_max"],
            }
        ],
        "symptom_names": ["peak_window_mismatch"],
        "symptom_summary": "peak_window_mismatch: Bragg peak window is unstable.",
        "allowed_actions": [
            {
                "name": "adjust_peak_window",
                "label": "Adjust peak window",
                "allowed_params": ["q_bragg_min", "q_bragg_max", "savgol_window"],
                "expected_evidence_change": ["q_peak_diff_pct should shrink"],
            }
        ],
        "allowed_changes": {
            "q_bragg_min": [0.05, 0.6],
            "q_bragg_max": [0.3, 2.0],
            "savgol_window": [3, 31],
        },
        "polymer_knowledge": orchestrator.polymer_knowledge,
        "workspace_context": {},
        "history": [record for record in orchestrator.history if record.round_num > 0],
        "previous_score": orchestrator._best_eval_score,
        "objective_score": orchestrator._best_eval_score,
        "tunable_params": [],
    }


def _scripted_residual(engine: Any) -> dict[str, Any]:
    q_bragg_min = round(float(getattr(engine.cfg, "q_bragg_min", 0.15)), 2)
    q_bragg_max = round(float(getattr(engine.cfg, "q_bragg_max", 0.90)), 2)
    if q_bragg_min > 0.15 and q_bragg_max < 0.90:
        return {
            "residual_type": "random",
            "summary": "Bragg residuals are now close to random.",
        }
    if q_bragg_min < 0.15 and q_bragg_max > 0.90:
        return {
            "residual_type": "peak_mismatch",
            "summary": "Bragg residual mismatch became worse.",
        }
    return {
        "residual_type": "peak_mismatch",
        "summary": "Baseline Bragg peak mismatch remains.",
    }


def _peak_window_profile(cfg: _FakeSAXSConfig) -> dict[str, Any]:
    q_bragg_min = round(float(cfg.q_bragg_min), 2)
    q_bragg_max = round(float(cfg.q_bragg_max), 2)
    if q_bragg_min > 0.15 and q_bragg_max < 0.90:
        return {
            "file": "fake_saxs.edf",
            "q_peak_diff_pct": 0.8,
            "pyfai_q_peak_diff_pct": 0.8,
            "beam_stop_contaminated": False,
            "condition_label": "Temperature",
            "r_squared": 0.83,
            "quality_score": 0.80,
            "quality_flag": "OK",
            "validation_summary": "All checks passed",
            "fit_rmse": 0.08,
            "fit_regions": [{"region": "peak", "r_squared": 0.83, "rmse": 0.08, "peak_count": 1, "zero_crossings": 2}],
            "q_peak_snr": 4.6,
            "L_bragg": 12.0,
            "L_corr_peak": 11.9,
            "L_confidence": 0.84,
            "L_nm": 12.0,
            "Xc_pct": 45.0,
        }
    if q_bragg_min < 0.15 and q_bragg_max > 0.90:
        return {
            "file": "fake_saxs.edf",
            "q_peak_diff_pct": 5.2,
            "pyfai_q_peak_diff_pct": 5.2,
            "beam_stop_contaminated": False,
            "condition_label": "Temperature",
            "r_squared": 0.76,
            "quality_score": 0.69,
            "quality_flag": "WARN:low_confidence",
            "validation_summary": "WARN: peak window still unstable",
            "fit_rmse": 0.22,
            "fit_regions": [{"region": "peak", "r_squared": 0.76, "rmse": 0.22, "peak_count": 1, "zero_crossings": 6}],
            "q_peak_snr": 2.1,
            "L_bragg": 12.0,
            "L_corr_peak": 10.8,
            "L_confidence": 0.52,
            "L_nm": 12.0,
            "Xc_pct": 45.0,
        }
    return {
        "file": "fake_saxs.edf",
        "q_peak_diff_pct": 3.9,
        "pyfai_q_peak_diff_pct": 3.9,
        "beam_stop_contaminated": False,
        "condition_label": "Temperature",
        "r_squared": 0.75,
        "quality_score": 0.70,
        "quality_flag": "WARN:low_confidence",
        "validation_summary": "WARN: peak window unstable",
        "fit_rmse": 0.18,
        "fit_regions": [{"region": "peak", "r_squared": 0.75, "rmse": 0.18, "peak_count": 1, "zero_crossings": 4}],
        "q_peak_snr": 2.6,
        "L_bragg": 12.0,
        "L_corr_peak": 11.1,
        "L_confidence": 0.58,
        "L_nm": 12.0,
        "Xc_pct": 45.0,
    }


def _failing_peak_window_profile(cfg: _FakeSAXSConfig) -> dict[str, Any] | None:
    q_bragg_min = round(float(cfg.q_bragg_min), 2)
    q_bragg_max = round(float(cfg.q_bragg_max), 2)
    if q_bragg_min == 0.15 and q_bragg_max == 0.90:
        return _peak_window_profile(cfg)
    return None


def _stability_trap_profile(cfg: _FakeSAXSConfig) -> dict[str, Any]:
    q_bragg_min = round(float(cfg.q_bragg_min), 2)
    q_bragg_max = round(float(cfg.q_bragg_max), 2)
    if q_bragg_min > 0.15 and q_bragg_max < 0.90:
        return {
            "file": "fake_saxs.edf",
            "q_peak_diff_pct": 0.5,
            "pyfai_q_peak_diff_pct": 0.5,
            "beam_stop_contaminated": False,
            "condition_label": "Temperature",
            "batch_frames": 4,
            "condition_confidence": 0.38,
            "condition_continuity_score": 0.42,
            "condition_missing_frames": 2,
            "_batch_data": [
                {"file": "frame_001.edf", "temperature_C": 100.0, "condition_value": 100.0},
                {"file": "frame_002.edf", "temperature_C": None, "condition_value": None},
                {"file": "frame_003.edf", "temperature_C": 120.0, "condition_value": 120.0},
                {"file": "frame_004.edf", "temperature_C": None, "condition_value": None},
            ],
            "r_squared": 0.86,
            "quality_score": 0.83,
            "quality_flag": "WARN: axis still unstable",
            "validation_summary": "WARN: recovered condition axis is discontinuous",
            "fit_rmse": 0.07,
            "fit_regions": [{"region": "peak", "r_squared": 0.86, "rmse": 0.07, "peak_count": 1, "zero_crossings": 2}],
            "q_peak_snr": 4.8,
            "L_bragg": 12.0,
            "L_corr_peak": 11.9,
            "L_confidence": 0.87,
            "L_nm": 12.0,
            "Xc_pct": 45.0,
        }
    if q_bragg_min < 0.15 and q_bragg_max > 0.90:
        return {
            "file": "fake_saxs.edf",
            "q_peak_diff_pct": 4.7,
            "pyfai_q_peak_diff_pct": 4.7,
            "beam_stop_contaminated": False,
            "condition_label": "Temperature",
            "batch_frames": 4,
            "condition_confidence": 0.92,
            "condition_continuity_score": 0.95,
            "condition_missing_frames": 0,
            "_batch_data": [
                {"file": "frame_001.edf", "temperature_C": 100.0, "condition_value": 100.0},
                {"file": "frame_002.edf", "temperature_C": 110.0, "condition_value": 110.0},
                {"file": "frame_003.edf", "temperature_C": 120.0, "condition_value": 120.0},
                {"file": "frame_004.edf", "temperature_C": 130.0, "condition_value": 130.0},
            ],
            "r_squared": 0.77,
            "quality_score": 0.71,
            "quality_flag": "WARN: peak window unstable",
            "validation_summary": "WARN: peak window still unstable",
            "fit_rmse": 0.21,
            "fit_regions": [{"region": "peak", "r_squared": 0.77, "rmse": 0.21, "peak_count": 1, "zero_crossings": 5}],
            "q_peak_snr": 2.1,
            "L_bragg": 12.0,
            "L_corr_peak": 10.8,
            "L_confidence": 0.52,
            "L_nm": 12.0,
            "Xc_pct": 45.0,
        }
    baseline = _peak_window_profile(cfg)
    baseline["batch_frames"] = 4
    baseline["condition_confidence"] = 0.93
    baseline["condition_continuity_score"] = 0.96
    baseline["condition_missing_frames"] = 0
    baseline["_batch_data"] = [
        {"file": "frame_001.edf", "temperature_C": 100.0, "condition_value": 100.0},
        {"file": "frame_002.edf", "temperature_C": 110.0, "condition_value": 110.0},
        {"file": "frame_003.edf", "temperature_C": 120.0, "condition_value": 120.0},
        {"file": "frame_004.edf", "temperature_C": 130.0, "condition_value": 130.0},
    ]
    return baseline


def _fallback_gap_trap_profile(cfg: _FakeSAXSConfig) -> dict[str, Any]:
    q_bragg_min = round(float(cfg.q_bragg_min), 2)
    q_bragg_max = round(float(cfg.q_bragg_max), 2)
    if q_bragg_min > 0.15 and q_bragg_max < 0.90:
        return {
            "file": "fake_saxs.edf",
            "q_peak_diff_pct": 0.9,
            "pyfai_q_peak_diff_pct": 0.9,
            "beam_stop_contaminated": False,
            "condition_label": "Temperature",
            "batch_frames": 4,
            "condition_confidence": 0.91,
            "condition_continuity_score": 0.95,
            "condition_missing_frames": 0,
            "qstar_contaminated_frame_count": 1,
            "mask_truncated_frame_count": 1,
            "low_conf_frame_count": 1,
            "calibrated_fallback_active": True,
            "calibrated_fallback_reason": "temperature_batch_lc_calibration",
            "batch_calibration_summary": {
                "batch_rows": 4,
                "fallback_rows": 4,
                "raw_snapshot_rows": 4,
                "fallback_ratio": 1.0,
                "raw_structure_available": True,
                "calibrated_fallback_active": True,
                "calibrated_fallback_reason": "temperature_batch_lc_calibration",
                "lc_gap_mean": 0.24,
                "L_gap_mean": 0.10,
                "Xc_gap_mean": 0.15,
            },
            "_batch_data": [
                {
                    "file": "frame_001.edf",
                    "temperature_C": 100.0,
                    "condition_value": 100.0,
                    "lc_nm": 3.07,
                    "L_nm": 12.0,
                    "Xc": 0.36,
                    "raw_snapshot": {"structure": {"lc": 2.35, "L": 10.8, "phi_c": 0.30}},
                    "calibrated_fallback_active": True,
                    "lc_method": "calibrated",
                },
                {
                    "file": "frame_002.edf",
                    "temperature_C": 110.0,
                    "condition_value": 110.0,
                    "lc_nm": 3.07,
                    "L_nm": 12.0,
                    "Xc": 0.35,
                    "raw_snapshot": {"structure": {"lc": 2.30, "L": 10.7, "phi_c": 0.29}},
                    "calibrated_fallback_active": True,
                    "lc_method": "calibrated",
                },
                {
                    "file": "frame_003.edf",
                    "temperature_C": 120.0,
                    "condition_value": 120.0,
                    "lc_nm": 3.07,
                    "L_nm": 12.0,
                    "Xc": 0.34,
                    "raw_snapshot": {"structure": {"lc": 2.25, "L": 10.6, "phi_c": 0.28}},
                    "calibrated_fallback_active": True,
                    "lc_method": "calibrated",
                },
                {
                    "file": "frame_004.edf",
                    "temperature_C": 130.0,
                    "condition_value": 130.0,
                    "lc_nm": 3.07,
                    "L_nm": 12.0,
                    "Xc": 0.33,
                    "raw_snapshot": {"structure": {"lc": 2.20, "L": 10.5, "phi_c": 0.27}},
                    "calibrated_fallback_active": True,
                    "lc_method": "calibrated",
                },
            ],
            "r_squared": 0.87,
            "quality_score": 0.85,
            "quality_flag": "WARN: fallback smoothed the thickness chain",
            "validation_summary": "WARN: calibrated batch summary diverges from raw frame structure",
            "fit_rmse": 0.06,
            "fit_regions": [{"region": "peak", "r_squared": 0.87, "rmse": 0.06, "peak_count": 1, "zero_crossings": 2}],
            "q_peak_snr": 4.9,
            "L_bragg": 12.0,
            "L_corr_peak": 11.9,
            "L_confidence": 0.88,
            "lc_confidence": 0.82,
            "L_nm": 12.0,
            "Xc_pct": 45.0,
        }
    baseline = _peak_window_profile(cfg)
    baseline["batch_frames"] = 4
    baseline["condition_confidence"] = 0.93
    baseline["condition_continuity_score"] = 0.96
    baseline["condition_missing_frames"] = 0
    baseline["qstar_contaminated_frame_count"] = 3
    baseline["mask_truncated_frame_count"] = 2
    baseline["low_conf_frame_count"] = 3
    baseline["calibrated_fallback_active"] = True
    baseline["calibrated_fallback_reason"] = "temperature_batch_lc_calibration"
    baseline["batch_calibration_summary"] = {
        "batch_rows": 4,
        "fallback_rows": 2,
        "raw_snapshot_rows": 4,
        "fallback_ratio": 0.5,
        "raw_structure_available": True,
        "calibrated_fallback_active": True,
        "calibrated_fallback_reason": "temperature_batch_lc_calibration",
        "lc_gap_mean": 0.10,
        "L_gap_mean": 0.04,
        "Xc_gap_mean": 0.06,
    }
    baseline["_batch_data"] = [
        {
            "file": "frame_001.edf",
            "temperature_C": 100.0,
            "condition_value": 100.0,
            "lc_nm": 2.70,
            "L_nm": 11.9,
            "Xc": 0.34,
            "raw_snapshot": {"structure": {"lc": 2.55, "L": 11.4, "phi_c": 0.31}},
            "calibrated_fallback_active": False,
            "lc_method": "raw",
        },
        {
            "file": "frame_002.edf",
            "temperature_C": 110.0,
            "condition_value": 110.0,
            "lc_nm": 2.72,
            "L_nm": 12.0,
            "Xc": 0.35,
            "raw_snapshot": {"structure": {"lc": 2.56, "L": 11.5, "phi_c": 0.31}},
            "calibrated_fallback_active": False,
            "lc_method": "raw",
        },
        {
            "file": "frame_003.edf",
            "temperature_C": 120.0,
            "condition_value": 120.0,
            "lc_nm": 2.74,
            "L_nm": 12.1,
            "Xc": 0.35,
            "raw_snapshot": {"structure": {"lc": 2.58, "L": 11.6, "phi_c": 0.32}},
            "calibrated_fallback_active": True,
            "lc_method": "calibrated",
        },
        {
            "file": "frame_004.edf",
            "temperature_C": 130.0,
            "condition_value": 130.0,
            "lc_nm": 2.75,
            "L_nm": 12.1,
            "Xc": 0.36,
            "raw_snapshot": {"structure": {"lc": 2.59, "L": 11.7, "phi_c": 0.32}},
            "calibrated_fallback_active": True,
            "lc_method": "calibrated",
        },
    ]
    return baseline


def test_expand_saxs_candidates_builds_multiple_guarded_peak_window_plans() -> None:
    orchestrator = ParameterOrchestrator(
        technique="saxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        project_root=Path("."),
    )

    plans = orchestrator._expand_saxs_candidates(
        {
            "target_symptom": "peak_window_mismatch",
            "recommended_actions": [{"name": "adjust_peak_window"}],
        },
        {
            "current_config": {
                "q_bragg_min": 0.15,
                "q_bragg_max": 0.90,
                "savgol_window": 7,
            },
            "allowed_actions": [
                {
                    "name": "adjust_peak_window",
                    "label": "Adjust peak window",
                    "allowed_params": ["q_bragg_min", "q_bragg_max", "savgol_window"],
                }
            ],
            "allowed_changes": {
                "q_bragg_min": [0.05, 0.6],
                "q_bragg_max": [0.3, 2.0],
                "savgol_window": [3, 31],
            },
            "symptom_names": ["peak_window_mismatch"],
        },
    )

    executable = [item for item in plans if item["executable"]]
    assert len(executable) == 2
    assert all(item["action_name"] == "adjust_peak_window" for item in executable)
    assert all(sorted(item["changes"].keys()) == ["q_bragg_max", "q_bragg_min"] for item in executable)


def test_expand_saxs_candidates_marks_non_executable_actions() -> None:
    orchestrator = ParameterOrchestrator(
        technique="saxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        project_root=Path("."),
    )

    plans = orchestrator._expand_saxs_candidates(
        {
            "target_symptom": "batch_mixed_samples",
            "recommended_actions": [{"name": "split_batch_by_sample"}],
        },
        {
            "current_config": {"q_bragg_min": 0.15, "q_bragg_max": 0.90},
            "allowed_actions": [
                {
                    "name": "split_batch_by_sample",
                    "label": "Split mixed batch",
                    "allowed_params": [],
                }
            ],
            "allowed_changes": {},
            "symptom_names": ["batch_mixed_samples"],
        },
    )

    assert plans[0]["executable"] is False
    assert "cannot execute" in plans[0]["skip_reason"]


def test_expand_saxs_candidates_injects_low_q_first_actions() -> None:
    orchestrator = ParameterOrchestrator(
        technique="saxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        project_root=Path("."),
    )

    plans = orchestrator._expand_saxs_candidates(
        {
            "target_symptom": "thickness_chain_unreliable",
            "recommended_actions": [{"name": "switch_lorentz_method"}],
        },
        {
            "current_config": {
                "q_bragg_min": 0.15,
                "q_bragg_max": 0.90,
                "q_corr_min": 0.15,
                "q_corr_max": 1.20,
                "savgol_window": 7,
                "savgol_order": 3,
                "idf_peak_rel_thresh": 0.05,
                "idf_valley_rel_thresh": 0.05,
                "lorentz_fit_method": "lmfit",
            },
            "allowed_actions": [
                {
                    "name": "adjust_q_crop",
                    "label": "Adjust q crop",
                    "allowed_params": ["q_bragg_min", "q_bragg_max", "q_corr_min", "q_corr_max"],
                },
                {
                    "name": "adjust_corr_window",
                    "label": "Adjust correlation window",
                    "allowed_params": ["q_corr_min", "q_corr_max", "savgol_window"],
                },
                {
                    "name": "adjust_idf_smoothing",
                    "label": "Adjust IDF smoothing",
                    "allowed_params": ["savgol_window", "savgol_order", "idf_peak_rel_thresh", "idf_valley_rel_thresh"],
                },
                {
                    "name": "rerun_condition_recovery",
                    "label": "Recover condition axis",
                    "allowed_params": [],
                },
            ],
            "allowed_changes": {
                "q_bragg_min": [0.05, 0.6],
                "q_bragg_max": [0.3, 2.0],
                "q_corr_min": [0.05, 0.8],
                "q_corr_max": [0.3, 3.0],
                "savgol_window": [3, 31],
                "savgol_order": [1, 5],
                "idf_peak_rel_thresh": [0.01, 0.2],
                "idf_valley_rel_thresh": [0.01, 0.2],
            },
            "symptom_names": [
                "beamstop_or_low_q_contamination",
                "temperature_calibration_fallback_active",
                "batch_summary_conflicts_with_frame_evidence",
                "thickness_chain_unreliable",
            ],
        },
    )

    executable_names = [item["action_name"] for item in plans if item["executable"]]
    assert executable_names[:3] == ["adjust_q_crop", "adjust_q_crop", "adjust_corr_window"] or executable_names[:3] == ["adjust_q_crop", "adjust_corr_window", "adjust_corr_window"]
    assert "adjust_idf_smoothing" in executable_names
    assert "switch_lorentz_method" not in executable_names


def test_saxs_orchestrator_runs_guarded_candidates_and_keeps_best(monkeypatch) -> None:
    fake_engine = _ScriptedSAXSEngine(_peak_window_profile)
    monkeypatch.setattr("polynexus.orchestrator.get_engine", lambda *args, **kwargs: fake_engine)

    orchestrator = ParameterOrchestrator(
        technique="saxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        max_rounds=1,
        advisor=_PeakWindowAdvisor(),
        project_root=Path("."),
    )
    orchestrator._build_agent_state = lambda engine, round_num: _peak_window_state(orchestrator, engine, round_num)  # type: ignore[method-assign]
    orchestrator._residual_pattern = lambda engine: _scripted_residual(engine)  # type: ignore[method-assign]

    report = orchestrator.run()

    history = report["history"]
    assert len(history) == 2
    assert history[1]["accepted"] is True
    assert history[1]["llm_advice"]["selected_candidate"]["action_name"] == "adjust_peak_window"
    assert len(history[1]["llm_advice"]["candidate_trials"]) == 2
    statuses = {item["status"] for item in history[1]["llm_advice"]["candidate_trials"]}
    assert "accepted" in statuses
    assert report["best_r_squared"] > report["baseline_r_squared"]
    assert report["best_config"]["q_bragg_min"] > 0.15
    assert report["best_config"]["q_bragg_max"] < 0.90
    assert fake_engine.analyze_calls >= 3


def test_saxs_orchestrator_attaches_ai_reference_resolution_diagnostic(monkeypatch) -> None:
    fake_engine = _ScriptedSAXSEngine(_peak_window_profile)
    monkeypatch.setattr("polynexus.orchestrator.get_engine", lambda *args, **kwargs: fake_engine)

    orchestrator = ParameterOrchestrator(
        technique="saxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        max_rounds=1,
        advisor=_PeakWindowAdvisor(),
        project_root=Path("."),
    )
    orchestrator._build_agent_state = lambda engine, round_num: _peak_window_state(orchestrator, engine, round_num)  # type: ignore[method-assign]
    orchestrator._residual_pattern = lambda engine: _scripted_residual(engine)  # type: ignore[method-assign]

    report = orchestrator.run()

    resolution = report["history"][1]["llm_advice"]["saxs_candidate_reference_resolution"]
    assert resolution["status"] == "unavailable"
    assert "unsupported_mode" in resolution["reason_codes"]
    assert fake_engine.saxs_candidate_reference_resolution == resolution
    assert fake_engine.result.saxs_candidate_reference_resolution == resolution
    assert fake_engine.analyze_calls >= 1


def test_saxs_orchestrator_records_candidate_trial_failures_when_all_candidates_fail(monkeypatch) -> None:
    fake_engine = _ScriptedSAXSEngine(_failing_peak_window_profile)
    monkeypatch.setattr("polynexus.orchestrator.get_engine", lambda *args, **kwargs: fake_engine)

    orchestrator = ParameterOrchestrator(
        technique="saxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        max_rounds=1,
        advisor=_PeakWindowAdvisor(),
        project_root=Path("."),
    )
    orchestrator._build_agent_state = lambda engine, round_num: _peak_window_state(orchestrator, engine, round_num)  # type: ignore[method-assign]
    orchestrator._residual_pattern = lambda engine: _scripted_residual(engine)  # type: ignore[method-assign]

    report = orchestrator.run()

    history = report["history"]
    assert len(history) == 2
    assert history[1]["accepted"] is False
    assert history[1]["llm_advice"]["rollback_reason"] == "engine.analyze() failed"
    assert len(history[1]["llm_advice"]["candidate_trials"]) == 2
    assert all(item["status"] == "rejected" for item in history[1]["llm_advice"]["candidate_trials"])
    assert report["best_r_squared"] == report["baseline_r_squared"]


def test_saxs_orchestrator_can_rerun_condition_recovery_with_context(monkeypatch) -> None:
    def _recovery_profile(cfg: _FakeSAXSConfig) -> dict[str, Any] | None:
        context = getattr(cfg, "condition_context", {})
        if isinstance(context, dict) and context.get("batch", {}).get("condition_values", {}).get("temperature") == 120.0:
            return {
                "file": "fake_saxs.edf",
                "q_peak_diff_pct": 0.6,
                "pyfai_q_peak_diff_pct": 0.6,
                "beam_stop_contaminated": False,
                "condition_label": "Temperature",
                "batch_frames": 4,
                "condition_confidence": 0.94,
                "condition_continuity_score": 0.98,
                "condition_missing_frames": 0,
                "_batch_data": [
                    {"file": "frame_001.edf", "temperature_C": 100.0, "condition_value": 100.0},
                    {"file": "frame_002.edf", "temperature_C": 110.0, "condition_value": 110.0},
                    {"file": "frame_003.edf", "temperature_C": 120.0, "condition_value": 120.0},
                    {"file": "frame_004.edf", "temperature_C": 130.0, "condition_value": 130.0},
                ],
                "r_squared": 0.88,
                "quality_score": 0.89,
                "quality_flag": "OK",
                "validation_summary": "All checks passed",
                "fit_rmse": 0.06,
                "fit_regions": [{"region": "peak", "r_squared": 0.88, "rmse": 0.06, "peak_count": 1, "zero_crossings": 1}],
                "q_peak_snr": 5.1,
                "L_bragg": 12.0,
                "L_corr_peak": 12.0,
                "L_confidence": 0.91,
                "L_nm": 12.0,
                "Xc_pct": 45.0,
            }
        return _stability_trap_profile(cfg)

    fake_engine = _ScriptedSAXSEngine(_recovery_profile)
    monkeypatch.setattr("polynexus.orchestrator.get_engine", lambda *args, **kwargs: fake_engine)

    class _RecoveryAdvisor:
        def advise(self, state: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
            return {
                "assessment": "WARN",
                "confidence": 0.76,
                "diagnosis": "condition_axis_missing",
                "target_symptom": "condition_axis_missing",
                "reasoning": "Recover the axis before another sequence round.",
                "recommended_actions": [
                    {
                        "name": "rerun_condition_recovery",
                        "reason": "Condition context is missing or weak.",
                        "expected_evidence_change": "condition_missing_frames should drop",
                    }
                ],
                "changes": {},
                "expected_improvement": {"objective_score": "increase"},
                "risk": "low",
                "suggestions": [],
                "reference_cases": [],
                "llm_used": False,
            }

    orchestrator = ParameterOrchestrator(
        technique="saxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        max_rounds=1,
        advisor=_RecoveryAdvisor(),
        project_root=Path("."),
        workspace_context={
            "condition_context": {
                "sample_id": "S-01",
                "batch_id": "B-01",
                "batch": {
                    "condition_values": {"temperature": 120.0},
                },
            }
        },
    )

    def _recovery_state(orchestrator: ParameterOrchestrator, engine: Any, round_num: int) -> dict[str, Any]:
        state = _peak_window_state(orchestrator, engine, round_num)
        state["symptoms"] = [{"name": "condition_axis_missing", "summary": "missing condition axis"}]
        state["symptom_names"] = ["condition_axis_missing"]
        state["symptom_summary"] = "condition_axis_missing: missing condition axis"
        state["allowed_actions"] = [
            {
                "name": "rerun_condition_recovery",
                "label": "Recover condition axis",
                "allowed_params": [],
                "expected_evidence_change": ["condition_missing_frames should drop"],
            }
        ]
        state["allowed_changes"] = {}
        state["workspace_context"] = orchestrator.workspace_context
        return state

    orchestrator._build_agent_state = lambda engine, round_num: _recovery_state(orchestrator, engine, round_num)  # type: ignore[method-assign]
    orchestrator._residual_pattern = lambda engine: _scripted_residual(engine)  # type: ignore[method-assign]

    report = orchestrator.run()

    history = report["history"]
    assert len(history) == 2
    assert history[1]["llm_advice"]["candidate_plan"]["action_name"] == "rerun_condition_recovery"
    assert history[1]["llm_advice"]["candidate_plan"]["recovery_context"]["batch"]["condition_values"]["temperature"] == 120.0
    assert fake_engine.analyze_calls >= 1
    assert report["best_r_squared"] > report["baseline_r_squared"]


def test_saxs_orchestrator_rolls_back_higher_r2_candidate_when_stability_drops(monkeypatch) -> None:
    fake_engine = _ScriptedSAXSEngine(_stability_trap_profile)
    monkeypatch.setattr("polynexus.orchestrator.get_engine", lambda *args, **kwargs: fake_engine)

    orchestrator = ParameterOrchestrator(
        technique="saxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        max_rounds=1,
        advisor=_PeakWindowAdvisor(),
        project_root=Path("."),
    )
    orchestrator._build_agent_state = lambda engine, round_num: _peak_window_state(orchestrator, engine, round_num)  # type: ignore[method-assign]
    orchestrator._residual_pattern = lambda engine: _scripted_residual(engine)  # type: ignore[method-assign]

    report = orchestrator.run()

    history = report["history"]
    assert len(history) == 2
    assert history[1]["accepted"] is False
    assert history[1]["llm_advice"]["rollback_reason"] == "condition_continuity_worsened"
    assert len(history[1]["llm_advice"]["candidate_trials"]) == 2
    accepted_trials = [item for item in history[1]["llm_advice"]["candidate_trials"] if item["status"] == "accepted"]
    assert not accepted_trials
    assert report["best_r_squared"] == report["baseline_r_squared"]


def test_saxs_orchestrator_rolls_back_candidate_when_fallback_conflict_worsens(monkeypatch) -> None:
    fake_engine = _ScriptedSAXSEngine(_fallback_gap_trap_profile)
    monkeypatch.setattr("polynexus.orchestrator.get_engine", lambda *args, **kwargs: fake_engine)

    orchestrator = ParameterOrchestrator(
        technique="saxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        max_rounds=1,
        advisor=_PeakWindowAdvisor(),
        project_root=Path("."),
    )
    orchestrator._build_agent_state = lambda engine, round_num: _peak_window_state(orchestrator, engine, round_num)  # type: ignore[method-assign]
    orchestrator._residual_pattern = lambda engine: _scripted_residual(engine)  # type: ignore[method-assign]

    report = orchestrator.run()

    history = report["history"]
    assert len(history) == 2
    assert history[1]["accepted"] is False
    assert history[1]["llm_advice"]["rollback_reason"] == "fallback_still_dominant"
    accepted_trials = [item for item in history[1]["llm_advice"]["candidate_trials"] if item["status"] == "accepted"]
    assert not accepted_trials
    assert report["best_r_squared"] == report["baseline_r_squared"]
