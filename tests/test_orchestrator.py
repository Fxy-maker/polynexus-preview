from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any

from polynexus.core.analysis_evidence import build_analysis_evidence
from polynexus.orchestrator import ParameterOrchestrator, RoundRecord


class FakeAdvisor:
    def __init__(self) -> None:
        self.calls = 0

    def advise(self, state: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        return {
            "assessment": "WARN",
            "confidence": 0.8,
            "reasoning": "Increase max_peaks once to test the orchestration loop.",
            "changes": {"max_peaks": 10},
            "expected_improvement": {"r_squared": "non-decreasing"},
            "risk": "low",
            "suggestions": ["test-only advisor"],
            "reference_cases": [],
            "llm_used": False,
        }


class _FakeConfig:
    def __init__(self) -> None:
        self.peak_function = "gaussian"
        self.smooth_window = 5

    def to_dict(self) -> dict[str, float]:
        return {"peak_function": self.peak_function, "smooth_window": self.smooth_window}


class _FakeResult:
    def __init__(self, params: dict[str, Any]) -> None:
        self.parameters = dict(params)
        self.analysis_evidence = {}

    def set_analysis_evidence(self, evidence: dict[str, Any]) -> None:
        self.analysis_evidence = dict(evidence)


class _FakeEngine:
    def __init__(self) -> None:
        self._waxs_config = _FakeConfig()
        self.result = _FakeResult(
            {
                "r_squared": 0.80,
                "quality_score": 0.85,
                "quality_flag": "OK",
                "validation_summary": "All checks passed",
                "peak_centers": [19.2, 22.4],
                "Xc_pct": 45.0,
            }
        )
        self._results = [
            type(
                "WaxsResult",
                (),
                {
                    "peaks": [{"two_theta": 19.2, "fwhm_deg": 0.4, "area": 1.0, "hkl": "110"}],
                    "two_theta": [10.0, 20.0, 30.0],
                    "I": [1.0, 2.0, 1.2],
                    "I_fit": [1.0, 1.9, 1.1],
                    "r_squared": 0.80,
                },
            )()
        ]

    def run_pipeline(self, *args: Any, **kwargs: Any) -> _FakeResult:
        return self.result

    def analyze(self) -> bool:
        self._waxs_config.smooth_window = 7
        self.result.parameters = {
            "r_squared": 0.84,
            "quality_score": 0.40,
            "quality_flag": "WARN:low_confidence",
            "validation_summary": "WARN: synthetic cross-check drift",
            "peak_centers": [19.2, 22.4],
            "Xc_pct": 45.0,
        }
        self._results = [
            type(
                "WaxsResult",
                (),
                {
                    "peaks": [{"two_theta": 19.2, "fwhm_deg": 0.5, "area": 1.0, "hkl": "110"}],
                    "two_theta": [10.0, 20.0, 30.0],
                    "I": [1.0, 2.2, 1.1],
                    "I_fit": [0.9, 1.4, 1.0],
                    "r_squared": 0.84,
                },
            )()
        ]
        return True

    def get_parameters(self) -> dict[str, Any]:
        return dict(self.result.parameters)


class _JointAwareFakeEngine(_FakeEngine):
    def analyze(self) -> bool:
        self._waxs_config.smooth_window = 7
        self.result.parameters = {
            "r_squared": 0.826,
            "quality_score": 0.85,
            "quality_flag": "OK",
            "validation_summary": "All checks passed",
            "peak_centers": [19.2, 22.4],
            "Xc_pct": 45.0,
        }
        self._results = [
            type(
                "WaxsResult",
                (),
                {
                    "peaks": [{"two_theta": 19.2, "fwhm_deg": 0.5, "area": 1.0, "hkl": "110"}],
                    "two_theta": [10.0, 20.0, 30.0],
                    "I": [1.0, 2.2, 1.1],
                    "I_fit": [0.9, 1.4, 1.0],
                    "r_squared": 0.826,
                },
            )()
        ]
        return True


class _IRFakeConfig:
    def __init__(self) -> None:
        self.baseline_method = "rubberband"
        self.normalization_method = "minmax"
        self.smooth_window = 7
        self.peak_distance = 18.0
        self.peak_fit_window_cm1 = 45.0
        self.assignment_tolerance_cm1 = 18.0
        self.polymer_peaks_db = {
            "pa6": [
                [3298, "N-H stretch", "strong", False],
                [1637, "amide I", "strong", False],
                [1541, "amide II", "medium", False],
            ]
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_method": self.baseline_method,
            "normalization_method": self.normalization_method,
            "smooth_window": self.smooth_window,
            "peak_distance": self.peak_distance,
            "peak_fit_window_cm1": self.peak_fit_window_cm1,
            "assignment_tolerance_cm1": self.assignment_tolerance_cm1,
            "polymer_peaks_db": self.polymer_peaks_db,
        }


class _IRFakeResult:
    def __init__(self, params: dict[str, Any], peaks: list[dict[str, Any]]) -> None:
        self.parameters = dict(params)
        self.analysis_evidence = {}
        self.peaks = peaks

    def set_analysis_evidence(self, evidence: dict[str, Any]) -> None:
        self.analysis_evidence = dict(evidence)


class _IRFakeEngine:
    def __init__(self) -> None:
        self._ir_config = _IRFakeConfig()
        self.result = _IRFakeResult(
            {
                "r_squared": 0.89,
                "quality_score": 0.74,
                "quality_flag": "OK",
                "validation_summary": "All checks passed",
                "polymer_name": "PA6",
                "polymer_score": 0.68,
                "assignment_confidence": 0.68,
                "Xc_pct": 13.7,
                "Xc_method": "PA6_A1200_A1637_uncalibrated",
            },
            [
                {"wavenumber": 3298, "height": 1.2, "prominence": 0.9, "fwhm_cm1": 18.0, "assignment": "N-H stretch"},
                {"wavenumber": 1637, "height": 1.0, "prominence": 0.7, "fwhm_cm1": 14.0, "assignment": "amide I"},
                {"wavenumber": 1541, "height": 0.8, "prominence": 0.5, "fwhm_cm1": 16.0, "assignment": "amide II"},
                {"wavenumber": 1461, "height": 0.6, "prominence": 0.4, "fwhm_cm1": 12.0, "assignment": "CH2 bend"},
            ],
        )
        self._results = [
            type(
                "IRResult",
                (),
                {
                    "peaks": self.result.peaks,
                    "wavenumber": [3298, 1637, 1541, 1461],
                    "absorbance": [0.2, 0.6, 0.5, 0.3],
                    "absorbance_fit": [0.19, 0.58, 0.49, 0.31],
                    "r_squared": 0.89,
                    "polymer_score": 0.68,
                    "polymer_name": "PA6",
                },
            )()
        ]

    def run_pipeline(self, *args: Any, **kwargs: Any) -> _IRFakeResult:
        return self.result

    def analyze(self) -> bool:
        self._ir_config.smooth_window = 9
        self.result.parameters = {
            "r_squared": 0.90,
            "quality_score": 0.62,
            "quality_flag": "WARN:baseline_sensitive",
            "validation_summary": "WARN: synthetic IR drift",
            "polymer_name": "PA6",
            "polymer_score": 0.55,
            "assignment_confidence": 0.55,
            "Xc_pct": 13.7,
            "Xc_method": "PA6_A1200_A1637_uncalibrated",
        }
        self._results = [
            type(
                "IRResult",
                (),
                {
                    "peaks": [
                        {"wavenumber": 3298, "height": 1.2, "prominence": 0.9, "fwhm_cm1": 18.0, "assignment": "N-H stretch"},
                        {"wavenumber": 1637, "height": 1.0, "prominence": 0.7, "fwhm_cm1": 14.0, "assignment": "amide I"},
                    ],
                    "wavenumber": [3298, 1637, 1541, 1461],
                    "absorbance": [0.2, 0.6, 0.5, 0.3],
                    "absorbance_fit": [0.18, 0.50, 0.55, 0.34],
                    "r_squared": 0.90,
                    "polymer_score": 0.55,
                    "polymer_name": "PA6",
                },
            )()
        ]
        return True

    def get_parameters(self) -> dict[str, Any]:
        return dict(self.result.parameters)


def test_ir_orchestrator_rolls_back_when_key_band_support_collapses() -> None:
    orchestrator = ParameterOrchestrator(
        technique="ir",
        data_file="dummy.spa",
        polymer_name="PA6",
        project_root=Path("."),
    )

    validation_context = {
        "config_snapshot": _IRFakeConfig().to_dict(),
        "ir_reference_bands": {
            "polymer_name": "PA6",
            "band_count": 3,
            "source": "IRConfig.polymer_peaks_db",
            "bands": [
                {"wavenumber": 3298, "assignment": "N-H stretch", "crystallinity_sensitive": False},
                {"wavenumber": 1637, "assignment": "amide I", "crystallinity_sensitive": False},
                {"wavenumber": 1541, "assignment": "amide II", "crystallinity_sensitive": False},
            ],
        },
    }

    previous_output = {
        "r_squared": 0.89,
        "quality_score": 0.74,
        "quality_flag": "OK",
        "validation_summary": "All checks passed",
        "polymer_name": "PA6",
        "polymer_score": 0.68,
        "assignment_confidence": 0.68,
        "Xc_pct": 13.7,
        "Xc_method": "PA6_A1200_A1637_uncalibrated",
        "peaks": [
            {"wavenumber": 3298, "height": 1.2, "prominence": 0.9, "fwhm_cm1": 18.0, "assignment": "N-H stretch"},
            {"wavenumber": 1637, "height": 1.0, "prominence": 0.7, "fwhm_cm1": 14.0, "assignment": "amide I"},
            {"wavenumber": 1541, "height": 0.8, "prominence": 0.5, "fwhm_cm1": 16.0, "assignment": "amide II"},
            {"wavenumber": 1461, "height": 0.6, "prominence": 0.4, "fwhm_cm1": 12.0, "assignment": "CH2 bend"},
        ],
    }
    previous_residuals = {"residual_type": "random", "summary": "baseline is steady"}
    previous_evidence = build_analysis_evidence(
        "IR",
        output_parameters=previous_output,
        residual_pattern=previous_residuals,
        validation_context=validation_context,
    ).to_dict()
    previous_metrics = orchestrator._score_snapshot(previous_output, previous_residuals, previous_evidence)

    candidate_output = {
        "r_squared": 0.96,
        "quality_score": 0.82,
        "quality_flag": "OK",
        "validation_summary": "All checks passed",
        "polymer_name": "PA6",
        "polymer_score": 0.66,
        "assignment_confidence": 0.66,
        "Xc_pct": 13.7,
        "Xc_method": "PA6_A1200_A1637_uncalibrated",
        "peaks": [
            {"wavenumber": 3298, "height": 1.2, "prominence": 0.9, "fwhm_cm1": 18.0, "assignment": "N-H stretch"},
            {"wavenumber": 1637, "height": 1.0, "prominence": 0.7, "fwhm_cm1": 14.0, "assignment": "amide I"},
        ],
    }
    candidate_residuals = {"residual_type": "peak_mismatch", "summary": "key band support weakened"}
    candidate_evidence = build_analysis_evidence(
        "IR",
        output_parameters=candidate_output,
        residual_pattern=candidate_residuals,
        validation_context=validation_context,
    ).to_dict()
    candidate_metrics = orchestrator._score_snapshot(candidate_output, candidate_residuals, candidate_evidence)

    candidate = RoundRecord(
        round_num=1,
        config_snapshot=validation_context["config_snapshot"],
        output_parameters=candidate_output,
        residuals_pattern=candidate_residuals,
        analysis_evidence=candidate_evidence,
        polymer_knowledge={},
        r_squared=candidate_output["r_squared"],
        eval_score=candidate_metrics["objective_score"],
        llm_advice=None,
    )
    previous = RoundRecord(
        round_num=0,
        config_snapshot=validation_context["config_snapshot"],
        output_parameters=previous_output,
        residuals_pattern=previous_residuals,
        analysis_evidence=previous_evidence,
        polymer_knowledge={},
        r_squared=previous_output["r_squared"],
        eval_score=previous_metrics["objective_score"],
        llm_advice=None,
    )

    accepted, reason, decision_metrics = orchestrator._evaluate_candidate(candidate, previous)

    assert accepted is False
    assert reason in {"key_band_support_collapsed", "assignment_support_weakened", "classification_basis_became_weaker"}
    assert candidate_metrics["ir_support_score"] < previous_metrics["ir_support_score"]
    assert decision_metrics["delta"]["key_band_support_score"] < 0


def test_ir_residual_score_penalizes_specialized_ir_residuals() -> None:
    orchestrator = ParameterOrchestrator(
        technique="ir",
        data_file="dummy.spa",
        polymer_name="PA6",
        project_root=Path("."),
    )

    assert orchestrator._residual_score({"residual_type": "key_band_mismatch"}) < 0.60
    assert orchestrator._residual_score({"residual_type": "crowded_band_underfit"}) < 0.60
    assert orchestrator._residual_score({"residual_type": "normalization_bias"}) < 0.60
    assert orchestrator._residual_score({"residual_type": "baseline_drift_low_wn"}) < 0.65
    assert orchestrator._residual_score({"residual_type": "random"}) == 1.0


def test_dsc_regression_reason_prefers_support_drop_over_fit_only() -> None:
    orchestrator = ParameterOrchestrator(
        technique="dsc",
        data_file="dummy.dsc",
        polymer_name="PA6",
        project_root=Path("."),
    )

    previous = {
        "event_support_score": 0.76,
        "baseline_stability_score": 0.74,
        "thermodynamic_consistency_score": 0.72,
        "crystallinity_support_score": 0.70,
        "dsc_support_score": 0.75,
        "validation_score": 0.94,
        "triggered_constraint_count": 1.0,
    }
    candidate = {
        "event_support_score": 0.63,
        "baseline_stability_score": 0.73,
        "thermodynamic_consistency_score": 0.71,
        "crystallinity_support_score": 0.69,
        "dsc_support_score": 0.66,
        "validation_score": 0.93,
        "triggered_constraint_count": 1.0,
    }

    assert orchestrator._dsc_regression_reason(candidate, previous) == "event_support_weakened"


def test_ir_temperature_2d_submodule_surfaces_in_agent_state() -> None:
    orchestrator = ParameterOrchestrator(
        technique="ir",
        data_file="dummy.spa",
        polymer_name="PA6",
        submodule_override="ir.temperature_2d",
        project_root=Path("."),
    )

    assert orchestrator._submodule_id() == "ir.temperature_2d"
    assert orchestrator._public_submodule() == "ir.temperature_2d"
    assert orchestrator._agent_state_submodule() == "ir.temperature_2d"
    assert orchestrator._submodule_name() == "temperature_2d"


def test_orchestrator_reuses_submodule_helpers_from_submodules_module() -> None:
    spec = importlib.util.find_spec("polynexus.orchestrator_submodules")
    assert spec is not None

    orchestrator_submodules = importlib.import_module("polynexus.orchestrator_submodules")

    assert ParameterOrchestrator._submodule_id is orchestrator_submodules._submodule_id
    assert ParameterOrchestrator._submodule_name is orchestrator_submodules._submodule_name
    assert ParameterOrchestrator._public_submodule is orchestrator_submodules._public_submodule
    assert (
        ParameterOrchestrator._agent_state_submodule
        is orchestrator_submodules._agent_state_submodule
    )


def test_orchestrator_reuses_action_helpers_from_actions_module() -> None:
    spec = importlib.util.find_spec("polynexus.orchestrator_actions")
    assert spec is not None

    orchestrator_actions = importlib.import_module("polynexus.orchestrator_actions")

    assert ParameterOrchestrator._allowed_actions is orchestrator_actions._allowed_actions
    assert ParameterOrchestrator._allowed_changes is orchestrator_actions._allowed_changes


def test_orchestrator_reuses_reporting_helpers_from_reporting_module() -> None:
    spec = importlib.util.find_spec("polynexus.orchestrator_reporting")
    assert spec is not None

    orchestrator_reporting = importlib.import_module("polynexus.orchestrator_reporting")

    assert ParameterOrchestrator._decision_summary is orchestrator_reporting._decision_summary
    assert ParameterOrchestrator._benchmark_summary is orchestrator_reporting._benchmark_summary
    assert ParameterOrchestrator._round_symptom_hit is orchestrator_reporting._round_symptom_hit
    assert ParameterOrchestrator._symptom_target_params is orchestrator_reporting._symptom_target_params
    assert ParameterOrchestrator._quality_guard is orchestrator_reporting._quality_guard
    assert (
        ParameterOrchestrator._objective_gain_threshold
        is orchestrator_reporting._objective_gain_threshold
    )
    assert ParameterOrchestrator._r_squared_drop_tolerance is orchestrator_reporting._r_squared_drop_tolerance
    assert ParameterOrchestrator._component_drop_tolerance is orchestrator_reporting._component_drop_tolerance


def test_orchestrator_reuses_regression_helpers_from_regressions_module() -> None:
    spec = importlib.util.find_spec("polynexus.orchestrator_regressions")
    assert spec is not None

    orchestrator_regressions = importlib.import_module("polynexus.orchestrator_regressions")

    assert ParameterOrchestrator._regression_reason is orchestrator_regressions._regression_reason
    assert ParameterOrchestrator._dsc_regression_reason is orchestrator_regressions._dsc_regression_reason
    assert ParameterOrchestrator._waxs_regression_reason is orchestrator_regressions._waxs_regression_reason
    assert (
        ParameterOrchestrator._waxs_temperature_regression_reason
        is orchestrator_regressions._waxs_temperature_regression_reason
    )
    assert ParameterOrchestrator._ir_regression_reason is orchestrator_regressions._ir_regression_reason
    assert ParameterOrchestrator._stability_regression_reason is orchestrator_regressions._stability_regression_reason
    assert ParameterOrchestrator._saxs_low_q_priority_reason is orchestrator_regressions._saxs_low_q_priority_reason
    assert ParameterOrchestrator._residual_score is orchestrator_regressions._residual_score


def test_orchestrator_reuses_decision_helpers_from_decisions_module() -> None:
    spec = importlib.util.find_spec("polynexus.orchestrator_decisions")
    assert spec is not None

    orchestrator_decisions = importlib.import_module("polynexus.orchestrator_decisions")

    assert ParameterOrchestrator._decision_metrics is orchestrator_decisions._decision_metrics
    assert ParameterOrchestrator._evaluate_candidate is orchestrator_decisions._evaluate_candidate


def test_orchestrator_reuses_scoring_helpers_from_scoring_module() -> None:
    spec = importlib.util.find_spec("polynexus.orchestrator_scoring")
    assert spec is not None

    orchestrator_scoring = importlib.import_module("polynexus.orchestrator_scoring")

    assert ParameterOrchestrator._score_snapshot is orchestrator_scoring._score_snapshot
    assert ParameterOrchestrator._saxs_evidence_snapshot is orchestrator_scoring._saxs_evidence_snapshot
    assert ParameterOrchestrator._ir_support_snapshot is orchestrator_scoring._ir_support_snapshot
    assert ParameterOrchestrator._stability_snapshot is orchestrator_scoring._stability_snapshot
    assert ParameterOrchestrator._dsc_support_snapshot is orchestrator_scoring._dsc_support_snapshot
    assert ParameterOrchestrator._waxs_support_snapshot is orchestrator_scoring._waxs_support_snapshot
    assert ParameterOrchestrator._joint_ai_context is orchestrator_scoring._joint_ai_context
    assert ParameterOrchestrator._first_text is orchestrator_scoring._first_text
    assert ParameterOrchestrator._mean_or_none is orchestrator_scoring._mean_or_none


def test_orchestrator_reuses_output_helpers_from_outputs_module() -> None:
    spec = importlib.util.find_spec("polynexus.orchestrator_outputs")
    assert spec is not None

    orchestrator_outputs = importlib.import_module("polynexus.orchestrator_outputs")

    assert ParameterOrchestrator._output_parameters is orchestrator_outputs._output_parameters
    assert ParameterOrchestrator._dsc_output_parameters is orchestrator_outputs._dsc_output_parameters
    assert ParameterOrchestrator._nmr_output_parameters is orchestrator_outputs._nmr_output_parameters
    assert ParameterOrchestrator._ir_output_parameters is orchestrator_outputs._ir_output_parameters
    assert ParameterOrchestrator._saxs_output_parameters is orchestrator_outputs._saxs_output_parameters
    assert ParameterOrchestrator._saxs_score is orchestrator_outputs._saxs_score
    assert ParameterOrchestrator._residual_pattern is orchestrator_outputs._residual_pattern
    assert ParameterOrchestrator._dsc_residual_pattern is orchestrator_outputs._dsc_residual_pattern
    assert ParameterOrchestrator._saxs_residual_pattern is orchestrator_outputs._saxs_residual_pattern
    assert ParameterOrchestrator._ir_residual_pattern is orchestrator_outputs._ir_residual_pattern
    assert ParameterOrchestrator._nmr_residual_pattern is orchestrator_outputs._nmr_residual_pattern
    assert (
        ParameterOrchestrator._select_dsc_residual_result
        is orchestrator_outputs._select_dsc_residual_result
    )
    assert ParameterOrchestrator._empty_residual_pattern is orchestrator_outputs._empty_residual_pattern


def test_orchestrator_reuses_parameter_action_helpers_from_parameter_actions_module() -> None:
    spec = importlib.util.find_spec("polynexus.orchestrator_parameter_actions")
    assert spec is not None

    orchestrator_parameter_actions = importlib.import_module(
        "polynexus.orchestrator_parameter_actions"
    )

    assert (
        ParameterOrchestrator._guard_technique_direct_changes
        is orchestrator_parameter_actions._guard_technique_direct_changes
    )
    assert (
        ParameterOrchestrator._guard_saxs_direct_changes
        is orchestrator_parameter_actions._guard_saxs_direct_changes
    )
    assert (
        ParameterOrchestrator._candidate_plans_for_action
        is orchestrator_parameter_actions._candidate_plans_for_action
    )
    assert (
        ParameterOrchestrator._saxs_recovery_context
        is orchestrator_parameter_actions._saxs_recovery_context
    )
    assert (
        ParameterOrchestrator._candidate_plans_for_ir_action
        is orchestrator_parameter_actions._candidate_plans_for_ir_action
    )
    assert (
        ParameterOrchestrator._candidate_plans_for_waxs_action
        is orchestrator_parameter_actions._candidate_plans_for_waxs_action
    )
    assert (
        ParameterOrchestrator._candidate_plans_for_dsc_action
        is orchestrator_parameter_actions._candidate_plans_for_dsc_action
    )
    assert (
        ParameterOrchestrator._candidate_plans_from_raw_candidates
        is orchestrator_parameter_actions._candidate_plans_from_raw_candidates
    )
    assert (
        ParameterOrchestrator._current_config_value
        is orchestrator_parameter_actions._current_config_value
    )
    assert (
        ParameterOrchestrator._dsc_action_candidates
        is orchestrator_parameter_actions._dsc_action_candidates
    )
    assert (
        ParameterOrchestrator._waxs_action_candidates
        is orchestrator_parameter_actions._waxs_action_candidates
    )
    assert (
        ParameterOrchestrator._waxs_temperature_action_candidates
        is orchestrator_parameter_actions._waxs_temperature_action_candidates
    )
    assert (
        ParameterOrchestrator._waxs_peak_position_candidates
        is orchestrator_parameter_actions._waxs_peak_position_candidates
    )
    assert (
        ParameterOrchestrator._waxs_peak_capacity_candidates
        is orchestrator_parameter_actions._waxs_peak_capacity_candidates
    )
    assert (
        ParameterOrchestrator._waxs_background_candidates
        is orchestrator_parameter_actions._waxs_background_candidates
    )
    assert (
        ParameterOrchestrator._waxs_peak_shape_candidates
        is orchestrator_parameter_actions._waxs_peak_shape_candidates
    )
    assert (
        ParameterOrchestrator._waxs_low_angle_candidates
        is orchestrator_parameter_actions._waxs_low_angle_candidates
    )
    assert (
        ParameterOrchestrator._ir_baseline_candidates
        is orchestrator_parameter_actions._ir_baseline_candidates
    )
    assert (
        ParameterOrchestrator._ir_noise_candidates
        is orchestrator_parameter_actions._ir_noise_candidates
    )
    assert (
        ParameterOrchestrator._ir_key_band_candidates
        is orchestrator_parameter_actions._ir_key_band_candidates
    )
    assert (
        ParameterOrchestrator._ir_crowded_band_candidates
        is orchestrator_parameter_actions._ir_crowded_band_candidates
    )
    assert (
        ParameterOrchestrator._ir_weak_support_candidates
        is orchestrator_parameter_actions._ir_weak_support_candidates
    )
    assert (
        ParameterOrchestrator._ir_band_window_candidates
        is orchestrator_parameter_actions._ir_band_window_candidates
    )
    assert (
        ParameterOrchestrator._ir_dynamic_signal_candidates
        is orchestrator_parameter_actions._ir_dynamic_signal_candidates
    )
    assert (
        ParameterOrchestrator._ir_2dcos_denoise_candidates
        is orchestrator_parameter_actions._ir_2dcos_denoise_candidates
    )
    assert (
        ParameterOrchestrator._ir_band_tracking_candidates
        is orchestrator_parameter_actions._ir_band_tracking_candidates
    )
    assert (
        ParameterOrchestrator._ir_cross_peak_assignment_candidates
        is orchestrator_parameter_actions._ir_cross_peak_assignment_candidates
    )
    assert (
        ParameterOrchestrator._saxs_range_action_candidates
        is orchestrator_parameter_actions._saxs_range_action_candidates
    )
    assert (
        ParameterOrchestrator._saxs_crop_action_candidates
        is orchestrator_parameter_actions._saxs_crop_action_candidates
    )
    assert (
        ParameterOrchestrator._saxs_idf_smoothing_candidates
        is orchestrator_parameter_actions._saxs_idf_smoothing_candidates
    )
    assert (
        ParameterOrchestrator._normalize_candidate_value
        is orchestrator_parameter_actions._normalize_candidate_value
    )
    assert (
        ParameterOrchestrator._normalize_saxs_candidate_value
        is orchestrator_parameter_actions._normalize_saxs_candidate_value
    )
    assert (
        ParameterOrchestrator._candidate_values_equal
        is orchestrator_parameter_actions._candidate_values_equal
    )


def test_orchestrator_reuses_session_helpers_from_session_module() -> None:
    spec = importlib.util.find_spec("polynexus.orchestrator_session")
    assert spec is not None

    orchestrator_session = importlib.import_module("polynexus.orchestrator_session")

    assert ParameterOrchestrator._restore_best is orchestrator_session._restore_best
    assert ParameterOrchestrator._record_round is orchestrator_session._record_round
    assert (
        ParameterOrchestrator._execute_candidate_trial
        is orchestrator_session._execute_candidate_trial
    )
    assert (
        ParameterOrchestrator._candidate_trial_summary
        is orchestrator_session._candidate_trial_summary
    )
    assert ParameterOrchestrator._candidate_rank is orchestrator_session._candidate_rank
    assert (
        ParameterOrchestrator._restore_best_with_refresh
        is orchestrator_session._restore_best_with_refresh
    )
    assert (
        ParameterOrchestrator._run_saxs_candidate_round
        is orchestrator_session._run_saxs_candidate_round
    )
    assert ParameterOrchestrator._final_report is orchestrator_session._final_report
    assert (
        ParameterOrchestrator._can_converge_on_small_delta
        is orchestrator_session._can_converge_on_small_delta
    )
    assert (
        ParameterOrchestrator._can_converge_after_rollback
        is orchestrator_session._can_converge_after_rollback
    )


def test_orchestrator_reuses_state_helpers_from_state_module() -> None:
    spec = importlib.util.find_spec("polynexus.orchestrator_state")
    assert spec is not None

    orchestrator_state = importlib.import_module("polynexus.orchestrator_state")

    assert ParameterOrchestrator._build_agent_state is orchestrator_state._build_agent_state
    assert ParameterOrchestrator._clean_advice is orchestrator_state._clean_advice
    assert ParameterOrchestrator._analysis_evidence is orchestrator_state._analysis_evidence
    assert (
        ParameterOrchestrator._attach_analysis_evidence
        is orchestrator_state._attach_analysis_evidence
    )
    assert ParameterOrchestrator._analysis_symptoms is orchestrator_state._analysis_symptoms
    assert ParameterOrchestrator._symptom_names is orchestrator_state._symptom_names
    assert ParameterOrchestrator._symptom_summary is orchestrator_state._symptom_summary
    assert (
        ParameterOrchestrator._advice_target_symptom
        is orchestrator_state._advice_target_symptom
    )
    assert (
        ParameterOrchestrator._advice_rollback_detail
        is orchestrator_state._advice_rollback_detail
    )
    assert (
        ParameterOrchestrator._expand_technique_candidates
        is orchestrator_state._expand_technique_candidates
    )
    assert (
        ParameterOrchestrator._expand_saxs_candidates
        is orchestrator_state._expand_saxs_candidates
    )


def test_orchestrator_reuses_utility_helpers_from_utils_module() -> None:
    spec = importlib.util.find_spec("polynexus.orchestrator_utils")
    assert spec is not None

    orchestrator_utils = importlib.import_module("polynexus.orchestrator_utils")

    assert ParameterOrchestrator._resolve_data_file is orchestrator_utils._resolve_data_file
    assert ParameterOrchestrator._config_snapshot is orchestrator_utils._config_snapshot
    assert ParameterOrchestrator._config_to_dict is orchestrator_utils._config_to_dict
    assert ParameterOrchestrator._ir_reference_bands is orchestrator_utils._ir_reference_bands
    assert ParameterOrchestrator._tunable_params is orchestrator_utils._tunable_params
    assert ParameterOrchestrator._goal_tuning_focus is orchestrator_utils._goal_tuning_focus
    assert ParameterOrchestrator._joint_tuning_focus is orchestrator_utils._joint_tuning_focus
    assert ParameterOrchestrator._engine_config is orchestrator_utils._engine_config
    assert (
        ParameterOrchestrator._canonical_submodule_id
        is orchestrator_utils._canonical_submodule_id
    )
    assert ParameterOrchestrator._waxs_submodule_id is orchestrator_utils._waxs_submodule_id
    assert ParameterOrchestrator._nmr_submodule_id is orchestrator_utils._nmr_submodule_id
    assert (
        ParameterOrchestrator._flatten_dsc_parameters
        is orchestrator_utils._flatten_dsc_parameters
    )
    assert (
        ParameterOrchestrator._flatten_ir_parameters
        is orchestrator_utils._flatten_ir_parameters
    )
    assert (
        ParameterOrchestrator._flatten_nmr_parameters
        is orchestrator_utils._flatten_nmr_parameters
    )
    assert ParameterOrchestrator._is_nan is orchestrator_utils._is_nan
    assert ParameterOrchestrator._safe_float is orchestrator_utils._safe_float
    assert ParameterOrchestrator._to_plain_value is orchestrator_utils._to_plain_value
    assert ParameterOrchestrator._stable_signature is orchestrator_utils._stable_signature


def test_orchestrator_reuses_cross_validation_helpers_from_cross_validation_module() -> None:
    spec = importlib.util.find_spec("polynexus.orchestrator_cross_validation")
    assert spec is not None

    orchestrator_cross_validation = importlib.import_module(
        "polynexus.orchestrator_cross_validation"
    )

    assert (
        ParameterOrchestrator._saxs_cross_validation
        is orchestrator_cross_validation._saxs_cross_validation
    )
    assert (
        ParameterOrchestrator._dsc_cross_validation
        is orchestrator_cross_validation._dsc_cross_validation
    )


def test_orchestrator_reuses_run_helper_from_run_module() -> None:
    spec = importlib.util.find_spec("polynexus.orchestrator_run")
    assert spec is not None

    orchestrator_run = importlib.import_module("polynexus.orchestrator_run")

    assert ParameterOrchestrator.run is orchestrator_run.run


def test_orchestrator_run_reuses_bootstrap_and_round_helpers_from_dedicated_modules() -> None:
    bootstrap_spec = importlib.util.find_spec("polynexus.orchestrator_run_bootstrap")
    round_spec = importlib.util.find_spec("polynexus.orchestrator_run_round")
    assert bootstrap_spec is not None
    assert round_spec is not None

    orchestrator_run = importlib.import_module("polynexus.orchestrator_run")
    orchestrator_run_bootstrap = importlib.import_module(
        "polynexus.orchestrator_run_bootstrap"
    )
    orchestrator_run_round = importlib.import_module(
        "polynexus.orchestrator_run_round"
    )

    assert (
        orchestrator_run._initialize_run_session
        is orchestrator_run_bootstrap._initialize_run_session
    )
    assert (
        orchestrator_run._execute_round_iteration
        is orchestrator_run_round._execute_round_iteration
    )


def test_orchestrator_run_round_reuses_branch_handlers_from_handlers_module() -> None:
    spec = importlib.util.find_spec("polynexus.orchestrator_run_round_handlers")
    assert spec is not None

    orchestrator_run_round = importlib.import_module("polynexus.orchestrator_run_round")
    orchestrator_run_round_handlers = importlib.import_module(
        "polynexus.orchestrator_run_round_handlers"
    )

    assert (
        orchestrator_run_round._handle_invalid_changes_round
        is orchestrator_run_round_handlers._handle_invalid_changes_round
    )
    assert (
        orchestrator_run_round._handle_noop_converged_round
        is orchestrator_run_round_handlers._handle_noop_converged_round
    )
    assert (
        orchestrator_run_round._handle_candidate_plan_round
        is orchestrator_run_round_handlers._handle_candidate_plan_round
    )
    assert (
        orchestrator_run_round._handle_direct_change_round
        is orchestrator_run_round_handlers._handle_direct_change_round
    )


def test_orchestrator_run_round_handlers_reuse_candidate_and_direct_modules() -> None:
    candidate_spec = importlib.util.find_spec(
        "polynexus.orchestrator_run_round_candidate_handler"
    )
    direct_spec = importlib.util.find_spec(
        "polynexus.orchestrator_run_round_direct_handler"
    )
    assert candidate_spec is not None
    assert direct_spec is not None

    orchestrator_run_round_handlers = importlib.import_module(
        "polynexus.orchestrator_run_round_handlers"
    )
    orchestrator_run_round_candidate_handler = importlib.import_module(
        "polynexus.orchestrator_run_round_candidate_handler"
    )
    orchestrator_run_round_direct_handler = importlib.import_module(
        "polynexus.orchestrator_run_round_direct_handler"
    )

    assert (
        orchestrator_run_round_handlers._handle_candidate_plan_round
        is orchestrator_run_round_candidate_handler._handle_candidate_plan_round
    )
    assert (
        orchestrator_run_round_handlers._handle_direct_change_round
        is orchestrator_run_round_direct_handler._handle_direct_change_round
    )


def test_orchestrator_run_round_direct_handler_reuses_execution_and_finalize_helpers() -> None:
    flow_spec = importlib.util.find_spec("polynexus.orchestrator_run_round_direct_flow")
    assert flow_spec is not None

    direct_handler = importlib.import_module(
        "polynexus.orchestrator_run_round_direct_handler"
    )
    direct_flow = importlib.import_module("polynexus.orchestrator_run_round_direct_flow")

    assert (
        direct_handler._execute_direct_change_attempt
        is direct_flow._execute_direct_change_attempt
    )
    assert (
        direct_handler._finalize_direct_change_candidate
        is direct_flow._finalize_direct_change_candidate
    )


def test_orchestrator_run_round_direct_flow_reuses_execution_and_finalize_modules() -> None:
    execution_spec = importlib.util.find_spec(
        "polynexus.orchestrator_run_round_direct_execution"
    )
    finalize_spec = importlib.util.find_spec(
        "polynexus.orchestrator_run_round_direct_finalize"
    )
    assert execution_spec is not None
    assert finalize_spec is not None

    direct_flow = importlib.import_module("polynexus.orchestrator_run_round_direct_flow")
    direct_execution = importlib.import_module(
        "polynexus.orchestrator_run_round_direct_execution"
    )
    direct_finalize = importlib.import_module(
        "polynexus.orchestrator_run_round_direct_finalize"
    )

    assert (
        direct_flow._execute_direct_change_attempt
        is direct_execution._execute_direct_change_attempt
    )
    assert (
        direct_flow._finalize_direct_change_candidate
        is direct_finalize._finalize_direct_change_candidate
    )


def test_orchestrator_run_round_direct_finalize_reuses_resolution_and_completion_helpers() -> None:
    resolution_spec = importlib.util.find_spec(
        "polynexus.orchestrator_run_round_direct_resolution"
    )
    completion_spec = importlib.util.find_spec(
        "polynexus.orchestrator_run_round_direct_completion"
    )
    assert resolution_spec is not None
    assert completion_spec is not None

    direct_finalize = importlib.import_module(
        "polynexus.orchestrator_run_round_direct_finalize"
    )
    direct_resolution = importlib.import_module(
        "polynexus.orchestrator_run_round_direct_resolution"
    )
    direct_completion = importlib.import_module(
        "polynexus.orchestrator_run_round_direct_completion"
    )

    assert (
        direct_finalize._resolve_direct_change_candidate
        is direct_resolution._resolve_direct_change_candidate
    )
    assert (
        direct_finalize._complete_direct_change_candidate
        is direct_completion._complete_direct_change_candidate
    )


def test_orchestrator_run_round_direct_resolution_reuses_acceptance_and_rejection_helpers() -> None:
    helpers_spec = importlib.util.find_spec(
        "polynexus.orchestrator_run_round_direct_resolution_helpers"
    )
    assert helpers_spec is not None

    direct_resolution = importlib.import_module(
        "polynexus.orchestrator_run_round_direct_resolution"
    )
    direct_resolution_helpers = importlib.import_module(
        "polynexus.orchestrator_run_round_direct_resolution_helpers"
    )

    assert (
        direct_resolution._accept_direct_change_candidate
        is direct_resolution_helpers._accept_direct_change_candidate
    )
    assert (
        direct_resolution._reject_direct_change_candidate
        is direct_resolution_helpers._reject_direct_change_candidate
    )


def test_orchestrator_run_round_direct_execution_reuses_failure_and_success_helpers() -> None:
    failure_spec = importlib.util.find_spec(
        "polynexus.orchestrator_run_round_direct_failures"
    )
    success_spec = importlib.util.find_spec(
        "polynexus.orchestrator_run_round_direct_success"
    )
    assert failure_spec is not None
    assert success_spec is not None

    direct_execution = importlib.import_module(
        "polynexus.orchestrator_run_round_direct_execution"
    )
    direct_failures = importlib.import_module(
        "polynexus.orchestrator_run_round_direct_failures"
    )
    direct_success = importlib.import_module(
        "polynexus.orchestrator_run_round_direct_success"
    )

    assert (
        direct_execution._reject_direct_change_attempt
        is direct_failures._reject_direct_change_attempt
    )
    assert (
        direct_execution._record_direct_change_candidate
        is direct_success._record_direct_change_candidate
    )


def test_orchestrator_reuses_models_from_models_module() -> None:
    spec = importlib.util.find_spec("polynexus.orchestrator_models")
    assert spec is not None

    orchestrator_models = importlib.import_module("polynexus.orchestrator_models")

    assert RoundRecord is orchestrator_models.RoundRecord


def test_orchestrator_reuses_lifecycle_helpers_from_lifecycle_module() -> None:
    spec = importlib.util.find_spec("polynexus.orchestrator_lifecycle")
    assert spec is not None

    orchestrator_lifecycle = importlib.import_module("polynexus.orchestrator_lifecycle")

    assert ParameterOrchestrator.__init__ is orchestrator_lifecycle.__init__
    assert ParameterOrchestrator._emit_progress is orchestrator_lifecycle._emit_progress


def test_orchestrator_reuses_priority_rules_from_priority_rules_module() -> None:
    spec = importlib.util.find_spec("polynexus.orchestrator_priority_rules")
    assert spec is not None

    orchestrator_module = importlib.import_module("polynexus.orchestrator")
    orchestrator_priority_rules = importlib.import_module(
        "polynexus.orchestrator_priority_rules"
    )

    assert (
        orchestrator_module.JOINT_TUNING_PRIORITY_RULES
        is orchestrator_priority_rules.JOINT_TUNING_PRIORITY_RULES
    )
    assert (
        orchestrator_module.GOAL_TUNING_PRIORITY_RULES
        is orchestrator_priority_rules.GOAL_TUNING_PRIORITY_RULES
    )


def test_orchestrator_priority_rules_reuse_technique_modules() -> None:
    waxs_spec = importlib.util.find_spec("polynexus.orchestrator_priority_rules_waxs")
    saxs_spec = importlib.util.find_spec("polynexus.orchestrator_priority_rules_saxs")
    dsc_spec = importlib.util.find_spec("polynexus.orchestrator_priority_rules_dsc")
    ir_spec = importlib.util.find_spec("polynexus.orchestrator_priority_rules_ir")
    nmr_spec = importlib.util.find_spec("polynexus.orchestrator_priority_rules_nmr")
    assert waxs_spec is not None
    assert saxs_spec is not None
    assert dsc_spec is not None
    assert ir_spec is not None
    assert nmr_spec is not None

    rules_module = importlib.import_module("polynexus.orchestrator_priority_rules")
    waxs_module = importlib.import_module("polynexus.orchestrator_priority_rules_waxs")
    saxs_module = importlib.import_module("polynexus.orchestrator_priority_rules_saxs")
    dsc_module = importlib.import_module("polynexus.orchestrator_priority_rules_dsc")
    ir_module = importlib.import_module("polynexus.orchestrator_priority_rules_ir")
    nmr_module = importlib.import_module("polynexus.orchestrator_priority_rules_nmr")

    assert (
        rules_module.JOINT_TUNING_PRIORITY_RULES["WAXS"]
        is waxs_module.JOINT_TUNING_PRIORITY_RULES_WAXS
    )
    assert (
        rules_module.JOINT_TUNING_PRIORITY_RULES["SAXS"]
        is saxs_module.JOINT_TUNING_PRIORITY_RULES_SAXS
    )
    assert (
        rules_module.JOINT_TUNING_PRIORITY_RULES["DSC"]
        is dsc_module.JOINT_TUNING_PRIORITY_RULES_DSC
    )
    assert (
        rules_module.JOINT_TUNING_PRIORITY_RULES["IR"]
        is ir_module.JOINT_TUNING_PRIORITY_RULES_IR
    )
    assert (
        rules_module.JOINT_TUNING_PRIORITY_RULES["NMR"]
        is nmr_module.JOINT_TUNING_PRIORITY_RULES_NMR
    )
    assert (
        rules_module.GOAL_TUNING_PRIORITY_RULES["WAXS"]
        is waxs_module.GOAL_TUNING_PRIORITY_RULES_WAXS
    )
    assert (
        rules_module.GOAL_TUNING_PRIORITY_RULES["SAXS"]
        is saxs_module.GOAL_TUNING_PRIORITY_RULES_SAXS
    )
    assert (
        rules_module.GOAL_TUNING_PRIORITY_RULES["DSC"]
        is dsc_module.GOAL_TUNING_PRIORITY_RULES_DSC
    )
    assert (
        rules_module.GOAL_TUNING_PRIORITY_RULES["IR"]
        is ir_module.GOAL_TUNING_PRIORITY_RULES_IR
    )
    assert (
        rules_module.GOAL_TUNING_PRIORITY_RULES["NMR"]
        is nmr_module.GOAL_TUNING_PRIORITY_RULES_NMR
    )


def test_ir_temperature_2d_symptoms_map_to_cross_peak_and_matrix_actions() -> None:
    orchestrator = ParameterOrchestrator(
        technique="ir",
        data_file="dummy.spa",
        polymer_name="PA6",
        submodule_override="ir.temperature_2d",
        project_root=Path("."),
    )

    symptoms = [
        {"name": "negative_matrix_fraction_high"},
        {"name": "band_index_jump_single_frame"},
        {"name": "temperature_trend_not_reproducible"},
        {"name": "cross_peak_without_band_assignment"},
        {"name": "async_peak_without_sync_support"},
    ]
    actions = orchestrator._allowed_actions(symptoms)
    names = [item["name"] for item in actions]
    allowed_changes = orchestrator._allowed_changes(actions)

    assert "stabilize_matrix_baseline" in names
    assert "stabilize_band_tracking" in names
    assert "tighten_cross_peak_assignment" in names
    assert "baseline_method" in allowed_changes
    assert "peak_fit_window_cm1" in allowed_changes
    assert "peak_distance" in allowed_changes
    assert "assignment_tolerance_cm1" in allowed_changes
    assert "cross_peak_exclusion_cm1" in allowed_changes


class _WAXSPositionConfig:
    def __init__(self) -> None:
        self.two_theta_offset = 0.08
        self.peak_function = "pseudo_voigt"
        self.peak_distance = 0.8
        self.max_peaks = 8
        self.smooth_window = 5
        self.background_method = "linear"
        self.amorphous_subtraction = "polynomial"
        self.amorphous_n_peaks = 2
        self.arpls_lam = 1e5
        self.arpls_diff_order = 2

    def to_dict(self) -> dict[str, Any]:
        return {
            "two_theta_offset": self.two_theta_offset,
            "peak_function": self.peak_function,
            "peak_distance": self.peak_distance,
            "max_peaks": self.max_peaks,
            "smooth_window": self.smooth_window,
            "background_method": self.background_method,
            "amorphous_subtraction": self.amorphous_subtraction,
            "amorphous_n_peaks": self.amorphous_n_peaks,
            "arpls_lam": self.arpls_lam,
            "arpls_diff_order": self.arpls_diff_order,
        }


def _waxs_result(r_squared: float, two_theta_offset: float) -> object:
    peaks = [
        {"two_theta": 17.8781, "fwhm_deg": 0.8549, "area": 2442.34, "hkl": "200"},
        {"two_theta": 21.7529, "fwhm_deg": 1.1242, "area": 1811.02, "hkl": "002/202"},
    ]
    return type(
        "WaxsResult",
        (),
        {
            "peaks": peaks,
            "two_theta": [10.0, 18.0, 22.0, 30.0],
            "I": [1.0, 2.4, 1.6, 1.1],
            "I_fit": [0.95, 2.0, 1.4, 1.0],
            "r_squared": r_squared,
            "two_theta_offset": two_theta_offset,
        },
    )()


class _WAXSPeakPositionEngine:
    def __init__(self) -> None:
        self._waxs_config = _WAXSPositionConfig()
        self.result = _FakeResult(
            {
                "r_squared": 0.862,
                "quality_score": 0.821,
                "quality_flag": "WARN:offset_sensitive_solution",
                "validation_summary": "WARN: offset still visible",
                "peak_centers": [17.8781, 21.7529],
                "Xc_pct": 69.6,
                "two_theta_offset": self._waxs_config.two_theta_offset,
                "peak_function": self._waxs_config.peak_function,
                "background_method": self._waxs_config.background_method,
                "amorphous_subtraction": self._waxs_config.amorphous_subtraction,
                "amorphous_n_peaks": self._waxs_config.amorphous_n_peaks,
                "peak_distance": self._waxs_config.peak_distance,
                "max_peaks": self._waxs_config.max_peaks,
                "smooth_window": self._waxs_config.smooth_window,
                "n_peaks": 2,
                "Xc_method": "peak_deconvolution",
                "D_Scherrer_nm": 8.3,
            }
        )
        self._results = [_waxs_result(0.862, self._waxs_config.two_theta_offset)]
        self.analyze_calls = 0

    def run_pipeline(self, *args: Any, **kwargs: Any) -> _FakeResult:
        return self.result

    def analyze(self) -> bool:
        self.analyze_calls += 1
        offset = float(self._waxs_config.two_theta_offset)
        improved = abs(offset) < 0.05
        r_squared = 0.948 if improved else 0.862
        quality_score = 0.931 if improved else 0.821
        self.result.parameters = {
            "r_squared": r_squared,
            "quality_score": quality_score,
            "quality_flag": "OK" if improved else "WARN:offset_sensitive_solution",
            "validation_summary": "All checks passed" if improved else "WARN: offset still visible",
            "peak_centers": [17.8781, 21.7529],
            "Xc_pct": 69.6,
            "two_theta_offset": offset,
            "peak_function": self._waxs_config.peak_function,
            "background_method": self._waxs_config.background_method,
            "amorphous_subtraction": self._waxs_config.amorphous_subtraction,
            "amorphous_n_peaks": self._waxs_config.amorphous_n_peaks,
            "peak_distance": self._waxs_config.peak_distance,
            "max_peaks": self._waxs_config.max_peaks,
            "smooth_window": self._waxs_config.smooth_window,
            "n_peaks": 2,
            "Xc_method": "peak_deconvolution",
            "D_Scherrer_nm": 8.3,
        }
        self._results = [_waxs_result(r_squared, offset)]
        return True

    def get_parameters(self) -> dict[str, Any]:
        return dict(self.result.parameters)


class _WAXSSupportEngine:
    def __init__(self) -> None:
        self._waxs_config = _WAXSPositionConfig()
        self.result = _FakeResult(
            {
                "r_squared": 0.932,
                "quality_score": 0.91,
                "quality_flag": "OK",
                "validation_summary": "All checks passed",
                "peak_centers": [17.9, 21.8],
                "Xc_pct": 69.6,
                "D_Scherrer_nm": 8.3,
                "Xc_method": "peak_deconvolution",
                "n_peaks": 2,
                "two_theta_offset": 0.02,
                "background_method": "linear",
                "amorphous_subtraction": "polynomial",
                "amorphous_n_peaks": 2,
                "peak_function": "pseudo_voigt",
                "peak_distance": 0.8,
                "max_peaks": 8,
                "smooth_window": 5,
            }
        )
        self._results = [_waxs_result(0.932, 0.02)]

    def run_pipeline(self, *args: Any, **kwargs: Any) -> _FakeResult:
        return self.result

    def analyze(self) -> bool:
        return True

    def get_parameters(self) -> dict[str, Any]:
        return dict(self.result.parameters)


class _WAXSDegenerateSupportEngine(_WAXSSupportEngine):
    def analyze(self) -> bool:
        self.result.parameters = {
            "r_squared": 0.948,
            "quality_score": 0.93,
            "quality_flag": "OK",
            "validation_summary": "All checks passed",
            "peak_centers": [17.9],
            "Xc_pct": 69.6,
            "D_Scherrer_nm": 8.3,
            "Xc_method": "peak_deconvolution",
            "n_peaks": 1,
            "two_theta_offset": 0.10,
            "background_method": "linear",
            "amorphous_subtraction": "polynomial",
            "amorphous_n_peaks": 1,
            "peak_function": "pseudo_voigt",
            "peak_distance": 0.8,
            "max_peaks": 8,
            "smooth_window": 5,
        }
        self._results = [
            type(
                "WaxsResult",
                (object,),
                {
                    "peaks": [{"two_theta": 17.9, "fwhm_deg": 0.5, "area": 1.0, "hkl": "110"}],
                    "two_theta": [10.0, 18.0, 22.0, 30.0],
                    "I": [1.0, 2.0, 1.5, 1.0],
                    "I_fit": [0.95, 1.8, 1.3, 1.0],
                    "r_squared": 0.948,
                },
            )()
        ]
        return True


def test_score_snapshot_includes_waxs_support_scores() -> None:
    orchestrator = ParameterOrchestrator(
        technique="waxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        project_root=Path("."),
    )

    output = {
        "r_squared": 0.93,
        "quality_score": 0.91,
        "quality_flag": "OK",
        "validation_summary": "All checks passed",
        "peak_centers": [17.9, 21.8],
        "peaks": [
            {"two_theta": 17.9, "fwhm_deg": 0.5, "area": 1.0},
            {"two_theta": 21.8, "fwhm_deg": 0.6, "area": 0.8},
        ],
        "n_peaks": 2,
        "Xc_pct": 69.6,
        "Xc_method": "peak_deconvolution",
        "D_Scherrer_nm": 8.3,
        "two_theta_offset": 0.02,
        "background_method": "linear",
        "amorphous_subtraction": "polynomial",
        "amorphous_n_peaks": 2,
    }
    residuals = {"residual_type": "random", "summary": "baseline is calm"}
    analysis_evidence = orchestrator._analysis_evidence(output, residuals)
    metrics = orchestrator._score_snapshot(output, residuals, analysis_evidence)

    assert metrics["peak_support_score"] > 0.5
    assert metrics["background_stability_score"] > 0.5
    assert metrics["phase_support_score"] > 0.5
    assert metrics["size_support_score"] > 0.5
    assert metrics["waxs_support_score"] > 0.5


def test_orchestrator_rejects_waxs_trials_when_support_collapses() -> None:
    orchestrator = ParameterOrchestrator(
        technique="waxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        project_root=Path("."),
    )

    previous_output = {
        "r_squared": 0.932,
        "quality_score": 0.91,
        "quality_flag": "OK",
        "validation_summary": "All checks passed",
        "peak_centers": [17.9, 21.8],
        "peaks": [
            {"two_theta": 17.9, "fwhm_deg": 0.5, "area": 1.0},
            {"two_theta": 21.8, "fwhm_deg": 0.6, "area": 0.8},
        ],
        "n_peaks": 2,
        "Xc_pct": 69.6,
        "Xc_method": "peak_deconvolution",
        "D_Scherrer_nm": 8.3,
        "two_theta_offset": 0.02,
        "background_method": "linear",
        "amorphous_subtraction": "polynomial",
        "amorphous_n_peaks": 2,
    }
    previous_residuals = {"residual_type": "random", "summary": "baseline is calm"}
    previous_evidence = orchestrator._analysis_evidence(previous_output, previous_residuals)
    previous_metrics = orchestrator._score_snapshot(previous_output, previous_residuals, previous_evidence)

    candidate_output = dict(previous_output, n_peaks=1, peak_centers=[17.9], two_theta_offset=0.10, amorphous_n_peaks=1)
    candidate_residuals = {"residual_type": "peak_count_underfit", "summary": "peak family is now too thin"}
    candidate_evidence = orchestrator._analysis_evidence(candidate_output, candidate_residuals)
    candidate_metrics = orchestrator._score_snapshot(candidate_output, candidate_residuals, candidate_evidence)

    candidate = RoundRecord(
        round_num=1,
        config_snapshot={},
        output_parameters=candidate_output,
        residuals_pattern=candidate_residuals,
        analysis_evidence=candidate_evidence,
        polymer_knowledge={},
        r_squared=candidate_output["r_squared"],
        eval_score=candidate_metrics["objective_score"],
        llm_advice=None,
    )
    previous = RoundRecord(
        round_num=0,
        config_snapshot={},
        output_parameters=previous_output,
        residuals_pattern=previous_residuals,
        analysis_evidence=previous_evidence,
        polymer_knowledge={},
        r_squared=previous_output["r_squared"],
        eval_score=previous_metrics["objective_score"],
        llm_advice=None,
    )

    assert candidate_metrics["peak_support_score"] < previous_metrics["peak_support_score"]
    assert candidate_metrics["background_stability_score"] < previous_metrics["background_stability_score"]
    assert candidate_metrics["phase_support_score"] < previous_metrics["phase_support_score"]
    assert candidate_metrics["waxs_support_score"] < previous_metrics["waxs_support_score"]
    accepted, reason, decision_metrics = orchestrator._evaluate_candidate(candidate, previous)
    assert accepted is False
    assert reason in {"peak_family_became_less_stable", "background_partition_worsened", "crystallinity_support_collapsed", "physical_support_weakened"}
    assert decision_metrics["delta"]["waxs_support_score"] < 0


def test_waxs_static_orchestrator_keeps_best_r_squared() -> None:
    case_path = Path("tests/eval/cases/real/waxs_real_static_pa6.json")
    payload = json.loads(case_path.read_text(encoding="utf-8"))
    data_file = payload["config_overrides"]["source_file"]

    report = ParameterOrchestrator(
        technique="waxs",
        data_file=data_file,
        polymer_name=payload["polymer_name"],
        max_rounds=2,
        advisor=FakeAdvisor(),
    ).run()

    r2_history = [round(item["r_squared"], 6) for item in report["history"]]
    print("r2_history=", r2_history)

    assert report["technique"] == "waxs"
    assert report["history"][0]["round_num"] == 0
    assert "Xc_pct" in report["history"][0]["output_parameters"]
    assert "peak_centers" in report["history"][0]["output_parameters"]
    assert report["history"][0]["residuals_pattern"]["summary"]
    assert report["history"][0]["polymer_knowledge"]["waxs"]["xc_range"]
    assert report["best_r_squared"] >= report["baseline_r_squared"]
    assert report["best_r_squared"] >= min(item["r_squared"] for item in report["history"])
    json.dumps(report, ensure_ascii=False)


def test_orchestrator_rolls_back_when_fit_improves_but_evidence_worsens(monkeypatch) -> None:
    fake_engine = _FakeEngine()
    monkeypatch.setattr("polynexus.orchestrator.get_engine", lambda *args, **kwargs: fake_engine)

    class _Advisor:
        def advise(self, state: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
            return {
                "assessment": "WARN",
                "confidence": 0.7,
                "reasoning": "Probe a larger change.",
                "changes": {"smooth_window": 7},
                "expected_improvement": {"r_squared": "increase"},
                "risk": "low",
                "suggestions": [],
                "reference_cases": [],
                "llm_used": False,
            }

    report = ParameterOrchestrator(
        technique="waxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        max_rounds=1,
        advisor=_Advisor(),
        project_root=Path("."),
    ).run()

    history = report["history"]
    assert history[1]["accepted"] is False
    assert history[1]["llm_advice"]["rollback_reason"] == "quality_score_dropped"
    assert "decision_metrics" in history[1]["llm_advice"]
    assert report["best_eval_score"] == report["baseline_eval_score"]
    assert report["best_r_squared"] == report["baseline_r_squared"]
    benchmark = report["benchmark_summary"]
    assert benchmark["rounds"] == 1
    assert benchmark["rejected_rounds"] == 1
    assert benchmark["objective_gain_rounds"] == 0
    assert benchmark["objective_loss_rounds"] == 1
    assert benchmark["objective_delta_average"] < 0
    assert benchmark["rollback_reasons"]["quality_score_dropped"] == 1


def test_orchestrator_keeps_existing_acceptance_when_joint_context_is_absent(monkeypatch) -> None:
    fake_engine = _JointAwareFakeEngine()
    monkeypatch.setattr("polynexus.orchestrator.get_engine", lambda *args, **kwargs: fake_engine)

    class _Advisor:
        def advise(self, state: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
            return {
                "assessment": "WARN",
                "confidence": 0.7,
                "reasoning": "Probe a larger change.",
                "changes": {"smooth_window": 7},
                "expected_improvement": {"r_squared": "increase"},
                "risk": "low",
                "suggestions": [],
                "reference_cases": [],
                "llm_used": False,
            }

    report = ParameterOrchestrator(
        technique="waxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        max_rounds=1,
        advisor=_Advisor(),
        project_root=Path("."),
    ).run()

    history = report["history"]
    assert history[1]["accepted"] is True
    assert "rollback_reason" not in (history[1]["llm_advice"] or {})
    assert report["best_eval_score"] > report["baseline_eval_score"]
    assert report["best_r_squared"] > report["baseline_r_squared"]


def test_orchestrator_issue_free_joint_context_stays_score_neutral() -> None:
    output = {
        "r_squared": 0.826,
        "quality_score": 0.85,
        "quality_flag": "OK",
        "validation_summary": "All checks passed",
        "Xc_pct": 45.0,
    }
    residuals = {"residual_type": "random", "summary": "random residuals"}
    analysis_evidence = {
        "fit_evidence": {"quality_score": 0.85},
        "physical_evidence": {
            "quality_flag": "OK",
            "validation_summary": "All checks passed",
        },
        "residual_evidence": {"residual_type": "random"},
        "constraints": [],
        "cross_validation": {},
    }

    baseline = ParameterOrchestrator(
        technique="waxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        project_root=Path("."),
    )
    neutral = ParameterOrchestrator(
        technique="waxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        project_root=Path("."),
        workspace_context={
            "joint_ai_context": {
                "summary": "Cross-tech checks passed for PA6",
                "scope": "PA6",
                "issue_count": 0,
                "warning_count": 0,
                "error_count": 0,
                "issue_families": [],
                "highlights": [],
            }
        },
    )

    baseline_metrics = baseline._score_snapshot(output, residuals, analysis_evidence)
    neutral_metrics = neutral._score_snapshot(output, residuals, analysis_evidence)

    assert baseline._objective_gain_threshold() == 0.01
    assert neutral._objective_gain_threshold() == 0.01
    assert neutral_metrics["joint_context_penalty"] == 0.0
    assert neutral_metrics["validation_score"] == baseline_metrics["validation_score"]
    assert neutral_metrics["objective_score"] == baseline_metrics["objective_score"]


def test_orchestrator_uses_constraint_summary_when_raw_constraints_are_missing() -> None:
    output = {
        "r_squared": 0.81,
        "quality_score": 0.78,
        "quality_flag": "WARN:low_confidence",
        "validation_summary": "WARN: synthetic drift",
        "Xc_pct": 45.0,
    }
    residuals = {"residual_type": "background_drift", "summary": "background drift"}
    analysis_evidence = {
        "fit_evidence": {"quality_score": 0.78},
        "physical_evidence": {
            "quality_flag": "WARN:low_confidence",
            "validation_summary": "WARN: synthetic drift",
        },
        "residual_evidence": {"residual_type": "background_drift"},
        "constraint_summary": {
            "status": "hard_fail",
            "inventory": {"hard_fail": 1, "soft_warn": 1, "evidence_only": 0},
            "triggered_total": 2,
            "triggered_counts": {"hard_fail": 1, "soft_warn": 1, "evidence_only": 0},
            "triggered_names": {
                "hard_fail": ["beamstop_contamination"],
                "soft_warn": ["mask_truncated"],
                "evidence_only": [],
            },
        },
        "constraints": [],
        "cross_validation": {},
    }

    orchestrator = ParameterOrchestrator(
        technique="saxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        project_root=Path("."),
    )
    metrics = orchestrator._score_snapshot(output, residuals, analysis_evidence)

    assert metrics["hard_fail_names"] == ["beamstop_contamination"]
    assert metrics["soft_warn_count"] == 1
    assert metrics["validation_score"] < 1.0
    assert metrics["objective_score"] < 1.0


def test_orchestrator_penalizes_saxs_series_axis_and_oscillation_failures() -> None:
    output = {
        "r_squared": 0.74,
        "quality_score": 0.41,
        "quality_flag": "WARN:low_confidence",
        "validation_summary": "WARN: correlation curve is over-oscillating",
        "condition_label": "Temperature",
        "file": "Check-20260618_0_00002.edf",
    }
    residuals = {"residual_type": "noise", "summary": "correlation curve oscillates too densely"}
    analysis_evidence = {
        "fit_evidence": {"quality_score": 0.41},
        "physical_evidence": {
            "quality_flag": "WARN:low_confidence",
            "validation_summary": "WARN: correlation curve is over-oscillating",
            "condition_label": "Temperature",
        },
        "residual_evidence": {"residual_type": "noise"},
        "constraint_summary": {
            "status": "hard_fail",
            "inventory": {"hard_fail": 1, "soft_warn": 2, "evidence_only": 0},
            "triggered_total": 3,
            "triggered_counts": {"hard_fail": 1, "soft_warn": 2, "evidence_only": 0},
            "triggered_names": {
                "hard_fail": ["missing_condition_axis"],
                "soft_warn": ["fit_regions_unstable", "correlation_over_oscillation"],
                "evidence_only": [],
            },
        },
        "constraints": [],
        "cross_validation": {},
    }

    orchestrator = ParameterOrchestrator(
        technique="saxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        project_root=Path("."),
    )
    metrics = orchestrator._score_snapshot(output, residuals, analysis_evidence)

    assert metrics["hard_fail_names"] == ["missing_condition_axis"]
    assert metrics["soft_warn_count"] == 2
    assert metrics["physical_score"] < 0.8
    assert metrics["objective_score"] < 0.8


def test_score_snapshot_includes_saxs_stability_scores() -> None:
    output = {
        "r_squared": 0.82,
        "quality_score": 0.79,
        "quality_flag": "OK",
        "validation_summary": "All checks passed",
        "condition_label": "Temperature",
        "condition_confidence": 0.92,
        "condition_continuity_score": 0.95,
        "condition_missing_frames": 0,
        "batch_frames": 3,
        "q_peak_snr": 4.3,
        "L_confidence": 0.83,
        "lc_confidence": 0.82,
        "L_bragg": 12.0,
        "L_corr_peak": 11.9,
        "L_nm": 12.0,
        "phi_c": 0.36,
        "phi_c_invariant": 0.35,
        "_batch_data": [
            {"file": "frame_001.edf", "temperature_C": 100.0, "condition_value": 100.0},
            {"file": "frame_002.edf", "temperature_C": 110.0, "condition_value": 110.0},
            {"file": "frame_003.edf", "temperature_C": 120.0, "condition_value": 120.0},
        ],
    }
    residuals = {"residual_type": "random", "summary": "random residuals"}
    orchestrator = ParameterOrchestrator(
        technique="saxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        project_root=Path("."),
    )
    evidence = orchestrator._analysis_evidence(output, residuals)
    metrics = orchestrator._score_snapshot(output, residuals, evidence)

    assert metrics["stability_score"] > 0.7
    assert metrics["parameter_stability_score"] > 0.7
    assert metrics["method_agreement_score"] > 0.7
    assert metrics["batch_continuity_score"] > 0.7


def test_score_snapshot_includes_saxs_batch_evidence_metrics() -> None:
    output = {
        "r_squared": 0.78,
        "quality_score": 0.72,
        "quality_flag": "WARN:low_confidence",
        "validation_summary": "WARN: fallback still active",
        "condition_label": "Temperature",
        "batch_frames": 4,
        "qstar_contaminated_frame_count": 3,
        "mask_truncated_frame_count": 2,
        "low_conf_frame_count": 3,
    }
    residuals = {"residual_type": "noise", "summary": "residuals still noisy"}
    analysis_evidence = {
        "fit_evidence": {"quality_score": 0.72},
        "physical_evidence": {
            "quality_flag": "WARN:low_confidence",
            "validation_summary": "WARN: fallback still active",
        },
        "residual_evidence": {"residual_type": "noise"},
        "batch_evidence": {
            "batch_frames": 4,
            "qstar_contaminated_frame_count": 3,
            "mask_truncated_frame_count": 2,
            "low_conf_frame_count": 3,
            "batch_calibration_summary": {
                "batch_rows": 4,
                "fallback_rows": 3,
                "raw_snapshot_rows": 4,
                "fallback_ratio": 0.75,
                "lc_gap_mean": 0.18,
                "L_gap_mean": 0.06,
                "Xc_gap_mean": 0.12,
            },
        },
        "stability_evidence": {
            "parameter_stability_score": 0.70,
            "method_agreement_score": 0.58,
            "batch_continuity_score": 0.76,
            "stability_score": 0.67,
            "stability_flags": ["thickness_chain_unreliable"],
        },
        "symptoms": [{"name": "thickness_chain_unreliable", "summary": "low-q path still unstable"}],
        "constraints": [],
        "cross_validation": {},
    }

    orchestrator = ParameterOrchestrator(
        technique="saxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        project_root=Path("."),
    )
    metrics = orchestrator._score_snapshot(output, residuals, analysis_evidence)

    assert metrics["fallback_ratio"] == 0.75
    assert metrics["raw_snapshot_rows"] == 4.0
    assert round(metrics["raw_vs_calibrated_gap"], 3) == 0.12
    assert metrics["thickness_chain_risk"] >= 0.75
    assert metrics["q_contamination_frame_ratio"] == 0.75
    assert metrics["mask_truncated_frame_ratio"] == 0.5
    assert metrics["low_conf_frame_ratio"] == 0.75


def test_saxs_stability_regression_reason_detects_batch_evidence_regressions() -> None:
    orchestrator = ParameterOrchestrator(
        technique="saxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        project_root=Path("."),
    )

    previous = {
        "batch_continuity_score": 0.82,
        "method_agreement_score": 0.78,
        "stability_score": 0.76,
        "stability_flags": [],
        "fallback_ratio": 0.48,
        "raw_vs_calibrated_gap": 0.10,
        "thickness_chain_risk": 0.44,
    }

    candidate_fallback = dict(previous, fallback_ratio=0.63)
    assert orchestrator._stability_regression_reason(candidate_fallback, previous) == "fallback_still_dominant"

    candidate_gap = dict(previous, fallback_ratio=0.48, raw_vs_calibrated_gap=0.16)
    assert orchestrator._stability_regression_reason(candidate_gap, previous) == "raw_calibrated_conflict_worsened"

    candidate_thickness = dict(previous, raw_vs_calibrated_gap=0.10, thickness_chain_risk=0.61)
    assert orchestrator._stability_regression_reason(candidate_thickness, previous) == "thickness_chain_still_unreliable"

    previous_strain = dict(previous, strain_reliability_status="usable", phase_ambiguous_frame_count=0, void_dominant_frame_count=0, paper_conclusion_candidate=True)
    candidate_strain = dict(previous_strain, strain_reliability_status="low_confidence")
    assert orchestrator._stability_regression_reason(candidate_strain, previous_strain) == "strain_reliability_degraded"

    candidate_phase = dict(previous_strain, phase_ambiguous_frame_count=2)
    assert orchestrator._stability_regression_reason(candidate_phase, previous_strain) == "phase_ambiguity_increased"

    candidate_void = dict(previous_strain, void_dominant_frame_count=2)
    assert orchestrator._stability_regression_reason(candidate_void, previous_strain) == "void_dominance_increased"

    candidate_paper = dict(previous_strain, paper_conclusion_candidate=False)
    assert orchestrator._stability_regression_reason(candidate_paper, previous_strain) == "paper_candidate_lost"


def test_symptom_target_params_reads_structured_symptoms() -> None:
    orchestrator = ParameterOrchestrator(
        technique="saxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        project_root=Path("."),
    )

    targets = orchestrator._symptom_target_params(
        {
            "symptoms": [
                {
                    "name": "beamstop_or_low_q_contamination",
                    "target_params": ["q_bragg_min", "q_corr_min", "savgol_window"],
                }
            ]
        }
    )

    assert "q_bragg_min" in targets
    assert "q_corr_min" in targets
    assert "savgol_window" in targets


def test_saxs_evidence_snapshot_uses_batch_summary_gaps_and_frame_ratios() -> None:
    orchestrator = ParameterOrchestrator(
        technique="saxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        project_root=Path("."),
    )

    snapshot = orchestrator._saxs_evidence_snapshot(
        {
            "batch_frames": 4,
            "guinier_lost_frame_count": 1,
            "mask_truncated_frame_count": 2,
            "low_conf_frame_count": 1,
        },
        {
            "batch_evidence": {
                "batch_calibration_summary": {
                    "fallback_ratio": 0.5,
                    "raw_snapshot_rows": 4,
                    "lc_gap_mean": 0.2,
                    "L_gap_mean": 0.1,
                }
            },
            "stability_evidence": {"method_agreement_score": 0.4},
            "symptoms": [{"name": "thickness_chain_unreliable"}],
        },
    )

    assert snapshot["fallback_ratio"] == 0.5
    assert snapshot["raw_snapshot_rows"] == 4.0
    assert snapshot["raw_vs_calibrated_gap"] == 0.15000000000000002
    assert snapshot["thickness_chain_risk"] == 0.7
    assert snapshot["q_contamination_frame_ratio"] == 0.25
    assert snapshot["mask_truncated_frame_ratio"] == 0.5
    assert snapshot["low_conf_frame_ratio"] == 0.25


def test_ir_support_snapshot_derives_support_scores_from_assignment_and_reference_data() -> None:
    orchestrator = ParameterOrchestrator(
        technique="ir",
        data_file="dummy.dat",
        polymer_name="PA6",
        project_root=Path("."),
    )

    snapshot = orchestrator._ir_support_snapshot(
        {
            "n_peaks": 8,
            "polymer_score": 0.6,
        },
        {
            "feature_evidence": {
                "peak_evidence": {"assigned_peak_count": 6},
                "assignment_evidence": {
                    "assigned_peak_count": 6,
                    "key_band_hit_count": 3,
                    "key_band_missing_count": 1,
                    "assignment_confidence_score": 0.8,
                },
                "reference_evidence": {"band_count": 4},
                "structure_evidence": {
                    "baseline_stability_score": 0.5,
                    "classification_basis": "peak_assignment",
                },
            },
            "constraint_summary": {"triggered_total": 2},
        },
    )

    assert snapshot["peak_count"] == 8.0
    assert snapshot["assigned_peak_count"] == 6.0
    assert snapshot["reference_band_hit_count"] == 3.0
    assert snapshot["reference_band_missing_count"] == 1.0
    assert snapshot["assignment_confidence_score"] == 0.8
    assert snapshot["key_band_support_score"] == 0.75
    assert snapshot["baseline_stability_score"] == 0.5
    assert snapshot["peak_coverage_score"] == 0.75
    assert snapshot["triggered_constraint_count"] == 2.0
    assert snapshot["unassigned_key_band_count"] == 1.0
    assert snapshot["classification_basis"] == "peak_assignment"
    assert round(snapshot["ir_support_score"], 3) == 0.734


def test_waxs_support_snapshot_surfaces_peak_background_phase_and_size_scores() -> None:
    orchestrator = ParameterOrchestrator(
        technique="waxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        project_root=Path("."),
    )

    snapshot = orchestrator._waxs_support_snapshot(
        {
            "n_peaks": 2,
            "two_theta_offset": 0.02,
            "background_method": "linear",
            "amorphous_subtraction": "polynomial",
            "amorphous_n_peaks": 2,
            "Xc_pct": 69.6,
            "Xc_method": "peak_deconvolution",
            "D_Scherrer_nm": 8.3,
            "peaks": [
                {"two_theta": 17.9, "fwhm_deg": 0.5, "area": 1.0},
                {"two_theta": 21.8, "fwhm_deg": 0.6, "area": 0.8},
            ],
        },
        {"residual_type": "random"},
        {
            "peak_evidence": {"peak_count": 2, "peak_gap_spread": 0.1, "peak_width_spread": 0.08},
            "background_evidence": {"two_theta_offset": 0.02, "background_method": "linear"},
            "phase_evidence": {"Xc_pct": 69.6, "crystallinity_method": "peak_deconvolution", "D_Scherrer_nm": 8.3},
            "constraint_summary": {"triggered_names": {}},
            "residual_evidence": {"residual_type": "random"},
        },
    )

    assert snapshot["peak_support_score"] > 0.5
    assert snapshot["background_stability_score"] > 0.5
    assert snapshot["phase_support_score"] > 0.5
    assert snapshot["size_support_score"] > 0.5
    assert snapshot["waxs_support_score"] > 0.5


def test_dsc_support_snapshot_derives_support_scores_and_validation_counts() -> None:
    orchestrator = ParameterOrchestrator(
        technique="dsc",
        data_file="dummy.dat",
        polymer_name="PA6",
        project_root=Path("."),
    )

    snapshot = orchestrator._dsc_support_snapshot(
        {
            "quality_score": 0.8,
            "Xc_pct": 45.0,
            "DHm_Jg": 12.0,
        },
        {
            "feature_evidence": {
                "event_support_evidence": {
                    "event_support_score": 0.76,
                    "baseline_stability_score": 0.74,
                    "thermodynamic_consistency_score": 0.72,
                    "supported_event_fraction": 0.67,
                    "supported_component_count": 2,
                    "scan_r_squared_median": 0.93,
                    "scan_r_squared_spread": 0.04,
                }
            },
            "constraint_summary": {"triggered_total": 1},
            "cross_validation": {
                "thermal": {"passed": True},
                "baseline": {"passed": False},
            },
        },
    )

    assert snapshot["event_support_score"] == 0.76
    assert snapshot["baseline_stability_score"] == 0.74
    assert snapshot["thermodynamic_consistency_score"] == 0.72
    assert snapshot["supported_event_fraction"] == 0.67
    assert snapshot["supported_component_count"] == 2.0
    assert snapshot["scan_r_squared_median"] == 0.93
    assert snapshot["scan_r_squared_spread"] == 0.04
    assert snapshot["triggered_constraint_count"] == 1.0
    assert snapshot["validation_passed_count"] == 1.0
    assert snapshot["validation_total_count"] == 2.0
    assert snapshot["crystallinity_support_score"] > 0.0
    assert snapshot["dsc_support_score"] > 0.0


def test_build_agent_state_surfaces_symptoms_from_analysis_evidence(monkeypatch) -> None:
    fake_engine = _FakeEngine()
    monkeypatch.setattr("polynexus.orchestrator.get_engine", lambda *args, **kwargs: fake_engine)

    orchestrator = ParameterOrchestrator(
        technique="saxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        project_root=Path("."),
    )

    orchestrator._output_parameters = lambda engine: {  # type: ignore[method-assign]
        "r_squared": 0.74,
        "quality_score": 0.41,
        "quality_flag": "WARN:low_confidence",
        "validation_summary": "WARN: correlation curve is over-oscillating",
        "condition_label": "Temperature",
        "file": "Check-20260618_0_00002.edf",
        "fit_regions": [
            {"region": "correlation", "peak_count": 12, "zero_crossings": 14},
        ],
    }
    orchestrator._residual_pattern = lambda engine: {  # type: ignore[method-assign]
        "residual_type": "noise",
        "summary": "correlation curve oscillates too densely",
    }

    state = orchestrator._build_agent_state(fake_engine, 1)

    assert state["symptoms"]
    assert "condition_axis_missing" in state["symptom_names"]
    assert "condition_axis_missing" in state["symptom_summary"]
    assert state["allowed_actions"]
    assert state["allowed_changes"]
    assert "rerun_condition_recovery" in {item["name"] for item in state["allowed_actions"]}


def test_build_agent_state_surfaces_temperature_fallback_actions(monkeypatch) -> None:
    fake_engine = _FakeEngine()
    monkeypatch.setattr("polynexus.orchestrator.get_engine", lambda *args, **kwargs: fake_engine)

    orchestrator = ParameterOrchestrator(
        technique="saxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        project_root=Path("."),
    )

    orchestrator._output_parameters = lambda engine: {  # type: ignore[method-assign]
        "batch_frames": 3,
        "condition_label": "Temperature",
        "condition_source": "header",
        "condition_confidence": 0.9,
        "calibrated_fallback_active": True,
        "calibrated_fallback_reason": "temperature_batch_lc_calibration",
        "batch_calibration_summary": {
            "batch_rows": 3,
            "fallback_rows": 3,
            "raw_snapshot_rows": 3,
            "fallback_ratio": 1.0,
            "raw_structure_available": True,
            "calibrated_fallback_active": True,
            "calibrated_fallback_reason": "temperature_batch_lc_calibration",
        },
        "_batch_data": [
            {
                "file": "frame_001.edf",
                "temperature_C": 100.0,
                "lc_nm": 3.07,
                "lc_nm_raw": 2.8,
                "Xc": 0.36,
                "Xc_raw": 0.32,
                "raw_snapshot": {"structure": {"lc": 2.8, "phi_c": 0.32, "L": 8.0}},
                "calibrated_fallback_active": True,
                "calibrated_fallback_reason": "temperature_batch_lc_calibration",
            },
            {
                "file": "frame_002.edf",
                "temperature_C": 110.0,
                "lc_nm": 3.07,
                "lc_nm_raw": 2.7,
                "Xc": 0.35,
                "Xc_raw": 0.31,
                "raw_snapshot": {"structure": {"lc": 2.7, "phi_c": 0.31, "L": 8.1}},
                "calibrated_fallback_active": True,
                "calibrated_fallback_reason": "temperature_batch_lc_calibration",
            },
            {
                "file": "frame_003.edf",
                "temperature_C": 120.0,
                "lc_nm": 3.07,
                "lc_nm_raw": 2.6,
                "Xc": 0.34,
                "Xc_raw": 0.30,
                "raw_snapshot": {"structure": {"lc": 2.6, "phi_c": 0.30, "L": 8.2}},
                "calibrated_fallback_active": True,
                "calibrated_fallback_reason": "temperature_batch_lc_calibration",
            },
        ],
    }
    orchestrator._residual_pattern = lambda engine: {  # type: ignore[method-assign]
        "residual_type": "noise",
        "summary": "fallback summary should remain visible",
    }

    state = orchestrator._build_agent_state(fake_engine, 1)

    assert "temperature_calibration_fallback_active" in state["symptom_names"]
    assert "batch_summary_conflicts_with_frame_evidence" in state["symptom_names"]
    assert "thickness_chain_unreliable" in state["symptom_names"]
    action_names = {item["name"] for item in state["allowed_actions"]}
    assert "adjust_q_crop" in action_names
    assert "adjust_corr_window" in action_names
    assert "rerun_condition_recovery" in action_names
    ordered = [item["name"] for item in state["allowed_actions"]]
    assert ordered.index("adjust_q_crop") < ordered.index("rerun_condition_recovery")
    assert ordered.index("adjust_corr_window") < ordered.index("rerun_condition_recovery")


def test_orchestrator_low_q_priority_filters_deferred_thickness_actions() -> None:
    orchestrator = ParameterOrchestrator(
        technique="saxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        project_root=Path("."),
    )

    actions = orchestrator._allowed_actions(
        [
            {"name": "beamstop_or_low_q_contamination"},
            {"name": "temperature_calibration_fallback_active"},
            {"name": "batch_summary_conflicts_with_frame_evidence"},
            {"name": "thickness_chain_unreliable"},
            {"name": "gamma_tangent_unstable"},
            {"name": "multi_method_disagreement"},
        ]
    )

    names = [item["name"] for item in actions]
    assert names[:3] == ["adjust_q_crop", "adjust_corr_window", "adjust_idf_smoothing"]
    assert "switch_lorentz_method" not in names
    assert "raise_tangent_floor" not in names


def test_orchestrator_rollback_detail_surfaces_target_symptom(monkeypatch) -> None:
    fake_engine = _JointAwareFakeEngine()
    monkeypatch.setattr("polynexus.orchestrator.get_engine", lambda *args, **kwargs: fake_engine)

    class _Advisor:
        def advise(self, state: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
            return {
                "assessment": "WARN",
                "confidence": 0.7,
                "reasoning": "Probe a larger change.",
                "target_symptom": "peak_window_mismatch",
                "changes": {"smooth_window": 7},
                "expected_improvement": {"r_squared": "increase"},
                "risk": "low",
                "suggestions": [],
                "reference_cases": [],
                "llm_used": False,
            }

    report = ParameterOrchestrator(
        technique="waxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        max_rounds=1,
        advisor=_Advisor(),
        project_root=Path("."),
        workspace_context={
            "joint_ai_context": {
                "summary": "Cross-tech consistency for PA6: 2 errors, 1 warnings; focus on phi_c inconsistency",
                "issue_count": 3,
                "warning_count": 1,
                "error_count": 2,
                "issue_families": ["phi_c inconsistency", "L consistency unstable"],
            }
        },
    ).run()

    history = report["history"]
    assert history[1]["accepted"] is False
    assert history[1]["target_symptom"] == "peak_window_mismatch"
    assert "peak_window_mismatch" in history[1]["rollback_detail"]
    assert history[1]["decision_summary"]


def test_waxs_orchestrator_runs_guarded_peak_position_candidates(monkeypatch) -> None:
    fake_engine = _WAXSPeakPositionEngine()
    monkeypatch.setattr("polynexus.orchestrator.get_engine", lambda *args, **kwargs: fake_engine)

    class _Advisor:
        def advise(self, state: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
            allowed_actions = state.get("allowed_actions", [])
            assert any(item.get("name") == "adjust_peak_position" for item in allowed_actions)
            return {
                "assessment": "WARN",
                "confidence": 0.74,
                "reasoning": "Peak family is shifted; try a smaller offset first.",
                "target_symptom": "peak_position_bias",
                "recommended_actions": [{"name": "adjust_peak_position"}],
                "changes": {},
                "expected_improvement": {"r_squared": "increase"},
                "risk": "low",
                "suggestions": [],
                "reference_cases": [],
                "llm_used": False,
            }

    orchestrator = ParameterOrchestrator(
        technique="waxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        max_rounds=1,
        advisor=_Advisor(),
        project_root=Path("."),
    )

    report = orchestrator.run()

    history = report["history"]
    assert len(history) == 2
    assert history[1]["accepted"] is True
    selected = history[1]["llm_advice"]["selected_candidate"]
    assert selected["action_name"] == "adjust_peak_position"
    assert abs(report["best_config"]["two_theta_offset"]) < 0.08
    assert report["best_eval_score"] >= report["baseline_eval_score"]


def test_tunable_params_mark_saxs_action_guardrails() -> None:
    orchestrator = ParameterOrchestrator(
        technique="saxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        project_root=Path("."),
    )

    params = orchestrator._tunable_params(
        {"q_bragg_min": 0.15, "q_bragg_max": 0.9, "savgol_window": 7},
        allowed_actions=[
            {
                "name": "adjust_peak_window",
                "allowed_params": ["q_bragg_min", "q_bragg_max", "savgol_window"],
            }
        ],
    )

    q_bragg_min = next(item for item in params if item["name"] == "q_bragg_min")
    assert q_bragg_min["action_guarded"] is True
    assert "adjust_peak_window" in q_bragg_min["allowed_actions"]


def test_saxs_output_parameters_include_condition_axis_fields() -> None:
    orchestrator = ParameterOrchestrator(
        technique="saxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        project_root=Path("."),
    )

    class _Analysis:
        q = [0.1, 0.2, 0.3]
        r_squared = 0.62
        quality_score = 0.58
        r_squared_method = "saxs_peak_region_fit_r2"
        fit_rmse = 0.14
        fit_regions = [{"region": "peak", "r_squared": 0.62, "rmse": 0.14}]
        q_peak_snr = 2.1
        quality_flag = "WARN:low_confidence"
        validation_summary = "WARN: synthetic condition axis issue"
        condition_value = float("nan")
        long_period = type("LP", (), {"L_confidence": 0.58, "L_bragg": 12.0, "L_lorentz": 11.8, "L_corr_peak": 11.4})()

    class _Engine:
        def __init__(self) -> None:
            self.result = type("Result", (), {"parameters": {"file": "Check-20260618_0_00002.edf", "condition_label": "Temperature", "temperature_C": None}})()
            self._analysis = _Analysis()

        def get_parameters(self) -> dict[str, Any]:
            return {"file": "Check-20260618_0_00002.edf", "condition_label": "Temperature", "temperature_C": None}

    output = orchestrator._saxs_output_parameters(_Engine())
    assert output["condition_label"] == "Temperature"
    assert "condition_value" in output


def test_orchestrator_penalizes_dsc_validation_summary() -> None:
    baseline = ParameterOrchestrator(
        technique="dsc",
        data_file="dummy.dat",
        polymer_name="PA6",
        project_root=Path("."),
    )
    clean_output = {
        "r_squared": 0.91,
        "quality_score": 0.88,
        "quality_flag": "OK",
        "validation_summary": "All checks passed",
        "Tm_peak_C": 221.0,
        "Xc_pct": 45.0,
    }
    warn_output = {
        "r_squared": 0.91,
        "quality_score": 0.88,
        "quality_flag": "OK",
        "validation_summary": "WARN: 2 issue(s): scan1/Tg, scan1/DHm",
        "quality_flags": {
            "scan1/Tg": "WARN",
            "scan1/DHm": "WARN",
            "scan1/validation": "WARN",
        },
        "validation_warnings": ["scan1/Tg", "scan1/DHm", "scan1/validation"],
        "Tm_peak_C": 221.0,
        "Xc_pct": 45.0,
    }
    residuals = {"residual_type": "random", "summary": "random residuals"}
    clean_evidence = baseline._analysis_evidence(clean_output, residuals)
    warn_evidence = baseline._analysis_evidence(warn_output, residuals)

    clean_metrics = baseline._score_snapshot(clean_output, residuals, clean_evidence)
    warn_metrics = baseline._score_snapshot(warn_output, residuals, warn_evidence)

    assert clean_evidence["physical_evidence"]["validation_summary"] == "All checks passed"
    assert warn_metrics["physical_score"] < clean_metrics["physical_score"]
    assert warn_metrics["validation_score"] < clean_metrics["validation_score"]
    assert warn_metrics["objective_score"] < clean_metrics["objective_score"]


def test_orchestrator_penalizes_joint_consistency_conflicts(monkeypatch) -> None:
    fake_engine = _JointAwareFakeEngine()
    monkeypatch.setattr("polynexus.orchestrator.get_engine", lambda *args, **kwargs: fake_engine)

    class _Advisor:
        def advise(self, state: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
            return {
                "assessment": "WARN",
                "confidence": 0.7,
                "reasoning": "Probe a larger change.",
                "changes": {"smooth_window": 7},
                "expected_improvement": {"r_squared": "increase"},
                "risk": "low",
                "suggestions": [],
                "reference_cases": [],
                "llm_used": False,
            }

    report = ParameterOrchestrator(
        technique="waxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        max_rounds=1,
        advisor=_Advisor(),
        project_root=Path("."),
        workspace_context={
            "joint_ai_context": {
                "summary": "Cross-tech consistency for PA6: 2 errors, 1 warnings; focus on phi_c inconsistency",
                "issue_count": 3,
                "warning_count": 1,
                "error_count": 2,
                "issue_families": ["phi_c inconsistency", "L consistency unstable"],
            }
        },
    ).run()

    history = report["history"]
    assert history[1]["accepted"] is False
    assert history[1]["llm_advice"]["rollback_reason"] == "no_meaningful_gain"
    assert history[1]["llm_advice"]["decision_metrics"]["candidate"]["joint_context_penalty"] > 0
    assert report["best_eval_score"] == report["baseline_eval_score"]
    assert report["best_r_squared"] == report["baseline_r_squared"]


def test_orchestrator_prioritizes_tunables_from_joint_context() -> None:
    orchestrator = ParameterOrchestrator(
        technique="waxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        project_root=Path("."),
        workspace_context={
            "joint_ai_context": {
                "summary": "Cross-tech consistency for PA6: 2 errors, 1 warnings; focus on phi_c inconsistency",
                "issue_count": 3,
                "warning_count": 1,
                "error_count": 2,
                "issue_families": ["phi_c inconsistency", "L consistency unstable"],
            }
        },
    )

    params = orchestrator._tunable_params({"peak_function": "gaussian", "peak_distance": 0.2})
    priorities = [int(item.get("joint_priority", 0) or 0) for item in params]
    focused = [item for item in params if int(item.get("joint_priority", 0) or 0) > 0]

    assert priorities == sorted(priorities, reverse=True)
    assert focused
    assert focused[0]["joint_priority_reason"]
    assert focused[0]["joint_priority_families"]


def test_orchestrator_prioritizes_tunables_from_goal_context() -> None:
    orchestrator = ParameterOrchestrator(
        technique="waxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        project_root=Path("."),
        workspace_context={
            "tuning_goal": "risk",
            "tuning_goal_label": "Reduce constraint risk",
        },
    )

    params = orchestrator._tunable_params(
        {
            "peak_function": "gaussian",
            "smooth_window": 7,
            "background_method": "linear",
            "amorphous_subtraction": "spline",
            "amorphous_n_peaks": 1,
            "peak_distance": 1.0,
            "two_theta_offset": 0.0,
            "max_peaks": 8,
        }
    )

    priorities = [int(item.get("goal_priority", 0) or 0) for item in params]
    focused = [item for item in params if int(item.get("goal_priority", 0) or 0) > 0]

    assert priorities == sorted(priorities, reverse=True)
    assert focused
    assert params[0]["name"] == "background_method"
    assert params[0]["goal_priority_reason"]
    assert params[0]["goal_priority_goals"] == ["risk"]


def test_goal_priority_does_not_override_joint_priority() -> None:
    orchestrator = ParameterOrchestrator(
        technique="waxs",
        data_file="dummy.dat",
        polymer_name="PA6",
        project_root=Path("."),
        workspace_context={
            "tuning_goal": "symptom",
            "joint_ai_context": {
                "summary": "Cross-tech consistency for PA6: 1 errors, 1 warnings; focus on phi_c inconsistency",
                "issue_count": 2,
                "warning_count": 1,
                "error_count": 1,
                "issue_families": ["phi_c inconsistency"],
            },
        },
    )

    params = orchestrator._tunable_params({"peak_function": "gaussian", "amorphous_subtraction": "spline"})
    top = params[0]

    assert top["name"] == "amorphous_subtraction"
    assert int(top["joint_priority"]) > int(top["goal_priority"])
