from __future__ import annotations
import logging
logger = logging.getLogger(__name__)


import json
import math
import inspect
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

import numpy as np

from polynexus.config_bridge import apply_changes
from polynexus.core import get_engine
from polynexus.core.dsc_engine import aggregate_dsc_result_metrics
from polynexus.core.dsc_residual_analyzer import DSCResidualAnalyzer, DSCResidualPattern
from polynexus.core.ir_residual_analyzer import IRResidualAnalyzer, IRResidualPattern
from polynexus.core.residual_analyzer import ResidualAnalyzer, ResidualPattern
from polynexus.core.saxs_residual_analyzer import SAXSResidualAnalyzer, SAXSResidualPattern
from polynexus.core.waxs_residual_analyzer import WAXSResidualAnalyzer, WAXSResidualPattern
from llm.config import create_llm_client
from rag.advisor import Advisor
from rag.polymer_knowledge import load_polymer_knowledge
from polynexus.orchestrator_lifecycle import __init__ as _shared_init
from polynexus.orchestrator_lifecycle import _emit_progress as _shared_emit_progress
from polynexus.orchestrator_models import RoundRecord
from polynexus.orchestrator_submodules import (
    _agent_state_submodule as _shared_agent_state_submodule,
)
from polynexus.orchestrator_submodules import _public_submodule as _shared_public_submodule
from polynexus.orchestrator_submodules import _submodule_id as _shared_submodule_id
from polynexus.orchestrator_submodules import _submodule_name as _shared_submodule_name
from polynexus.orchestrator_actions import _allowed_actions as _shared_allowed_actions
from polynexus.orchestrator_actions import _allowed_changes as _shared_allowed_changes
from polynexus.orchestrator_cross_validation import _dsc_cross_validation as _shared_dsc_cross_validation
from polynexus.orchestrator_cross_validation import _saxs_cross_validation as _shared_saxs_cross_validation
from polynexus.orchestrator_run import run as _shared_run
from polynexus.orchestrator_reporting import _benchmark_summary as _shared_benchmark_summary
from polynexus.orchestrator_reporting import _component_drop_tolerance as _shared_component_drop_tolerance
from polynexus.orchestrator_reporting import _decision_summary as _shared_decision_summary
from polynexus.orchestrator_reporting import _objective_gain_threshold as _shared_objective_gain_threshold
from polynexus.orchestrator_reporting import _quality_guard as _shared_quality_guard
from polynexus.orchestrator_reporting import _r_squared_drop_tolerance as _shared_r_squared_drop_tolerance
from polynexus.orchestrator_reporting import _round_symptom_hit as _shared_round_symptom_hit
from polynexus.orchestrator_reporting import _symptom_target_params as _shared_symptom_target_params
from polynexus.orchestrator_regressions import _dsc_regression_reason as _shared_dsc_regression_reason
from polynexus.orchestrator_regressions import _ir_regression_reason as _shared_ir_regression_reason
from polynexus.orchestrator_regressions import _regression_reason as _shared_regression_reason
from polynexus.orchestrator_regressions import _residual_score as _shared_residual_score
from polynexus.orchestrator_regressions import _saxs_low_q_priority_reason as _shared_saxs_low_q_priority_reason
from polynexus.orchestrator_regressions import _stability_regression_reason as _shared_stability_regression_reason
from polynexus.orchestrator_regressions import _waxs_regression_reason as _shared_waxs_regression_reason
from polynexus.orchestrator_regressions import (
    _waxs_temperature_regression_reason as _shared_waxs_temperature_regression_reason,
)
from polynexus.orchestrator_decisions import _decision_metrics as _shared_decision_metrics
from polynexus.orchestrator_decisions import _evaluate_candidate as _shared_evaluate_candidate
from polynexus.orchestrator_preprocess import (
    _commit_preprocess_candidate as _shared_commit_preprocess_candidate,
    _execute_preprocess_candidate as _shared_execute_preprocess_candidate,
    _run_preprocess_intent as _shared_run_preprocess_intent,
    _snapshot_for_preprocess as _shared_snapshot_for_preprocess,
    run_preprocess_intent as _shared_public_run_preprocess_intent,
)
from polynexus.orchestrator_scoring import _dsc_support_snapshot as _shared_dsc_support_snapshot
from polynexus.orchestrator_scoring import _first_text as _shared_first_text
from polynexus.orchestrator_scoring import _ir_support_snapshot as _shared_ir_support_snapshot
from polynexus.orchestrator_scoring import _joint_ai_context as _shared_joint_ai_context
from polynexus.orchestrator_scoring import _mean_or_none as _shared_mean_or_none
from polynexus.orchestrator_scoring import _saxs_evidence_snapshot as _shared_saxs_evidence_snapshot
from polynexus.orchestrator_scoring import _score_snapshot as _shared_score_snapshot
from polynexus.orchestrator_scoring import _stability_snapshot as _shared_stability_snapshot
from polynexus.orchestrator_scoring import _waxs_support_snapshot as _shared_waxs_support_snapshot
from polynexus.orchestrator_outputs import _dsc_output_parameters as _shared_dsc_output_parameters
from polynexus.orchestrator_outputs import _dsc_residual_pattern as _shared_dsc_residual_pattern
from polynexus.orchestrator_outputs import _empty_residual_pattern as _shared_empty_residual_pattern
from polynexus.orchestrator_outputs import _ir_output_parameters as _shared_ir_output_parameters
from polynexus.orchestrator_outputs import _ir_residual_pattern as _shared_ir_residual_pattern
from polynexus.orchestrator_outputs import _nmr_output_parameters as _shared_nmr_output_parameters
from polynexus.orchestrator_outputs import _nmr_residual_pattern as _shared_nmr_residual_pattern
from polynexus.orchestrator_outputs import _output_parameters as _shared_output_parameters
from polynexus.orchestrator_outputs import _residual_pattern as _shared_residual_pattern
from polynexus.orchestrator_outputs import _saxs_output_parameters as _shared_saxs_output_parameters
from polynexus.orchestrator_outputs import _saxs_residual_pattern as _shared_saxs_residual_pattern
from polynexus.orchestrator_outputs import _saxs_score as _shared_saxs_score
from polynexus.orchestrator_outputs import _select_dsc_residual_result as _shared_select_dsc_residual_result
from polynexus.orchestrator_parameter_actions import (
    _candidate_plans_for_action as _shared_candidate_plans_for_action,
)
from polynexus.orchestrator_parameter_actions import (
    _candidate_plans_for_dsc_action as _shared_candidate_plans_for_dsc_action,
)
from polynexus.orchestrator_parameter_actions import (
    _candidate_plans_for_ir_action as _shared_candidate_plans_for_ir_action,
)
from polynexus.orchestrator_parameter_actions import (
    _candidate_plans_for_waxs_action as _shared_candidate_plans_for_waxs_action,
)
from polynexus.orchestrator_parameter_actions import (
    _candidate_plans_from_raw_candidates as _shared_candidate_plans_from_raw_candidates,
)
from polynexus.orchestrator_parameter_actions import (
    _candidate_values_equal as _shared_candidate_values_equal,
)
from polynexus.orchestrator_parameter_actions import (
    _current_config_value as _shared_current_config_value,
)
from polynexus.orchestrator_parameter_actions import (
    _dsc_action_candidates as _shared_dsc_action_candidates,
)
from polynexus.orchestrator_parameter_actions import (
    _guard_saxs_direct_changes as _shared_guard_saxs_direct_changes,
)
from polynexus.orchestrator_parameter_actions import (
    _guard_technique_direct_changes as _shared_guard_technique_direct_changes,
)
from polynexus.orchestrator_parameter_actions import (
    _ir_2dcos_denoise_candidates as _shared_ir_2dcos_denoise_candidates,
)
from polynexus.orchestrator_parameter_actions import (
    _ir_band_tracking_candidates as _shared_ir_band_tracking_candidates,
)
from polynexus.orchestrator_parameter_actions import (
    _ir_band_window_candidates as _shared_ir_band_window_candidates,
)
from polynexus.orchestrator_parameter_actions import (
    _ir_baseline_candidates as _shared_ir_baseline_candidates,
)
from polynexus.orchestrator_parameter_actions import (
    _ir_cross_peak_assignment_candidates as _shared_ir_cross_peak_assignment_candidates,
)
from polynexus.orchestrator_parameter_actions import (
    _ir_crowded_band_candidates as _shared_ir_crowded_band_candidates,
)
from polynexus.orchestrator_parameter_actions import (
    _ir_dynamic_signal_candidates as _shared_ir_dynamic_signal_candidates,
)
from polynexus.orchestrator_parameter_actions import (
    _ir_key_band_candidates as _shared_ir_key_band_candidates,
)
from polynexus.orchestrator_parameter_actions import (
    _ir_noise_candidates as _shared_ir_noise_candidates,
)
from polynexus.orchestrator_parameter_actions import (
    _ir_weak_support_candidates as _shared_ir_weak_support_candidates,
)
from polynexus.orchestrator_parameter_actions import (
    _normalize_candidate_value as _shared_normalize_candidate_value,
)
from polynexus.orchestrator_parameter_actions import (
    _normalize_saxs_candidate_value as _shared_normalize_saxs_candidate_value,
)
from polynexus.orchestrator_parameter_actions import (
    _saxs_crop_action_candidates as _shared_saxs_crop_action_candidates,
)
from polynexus.orchestrator_parameter_actions import (
    _saxs_idf_smoothing_candidates as _shared_saxs_idf_smoothing_candidates,
)
from polynexus.orchestrator_parameter_actions import (
    _saxs_range_action_candidates as _shared_saxs_range_action_candidates,
)
from polynexus.orchestrator_parameter_actions import (
    _saxs_recovery_context as _shared_saxs_recovery_context,
)
from polynexus.orchestrator_parameter_actions import (
    _waxs_action_candidates as _shared_waxs_action_candidates,
)
from polynexus.orchestrator_parameter_actions import (
    _waxs_background_candidates as _shared_waxs_background_candidates,
)
from polynexus.orchestrator_parameter_actions import (
    _waxs_low_angle_candidates as _shared_waxs_low_angle_candidates,
)
from polynexus.orchestrator_parameter_actions import (
    _waxs_peak_capacity_candidates as _shared_waxs_peak_capacity_candidates,
)
from polynexus.orchestrator_parameter_actions import (
    _waxs_peak_position_candidates as _shared_waxs_peak_position_candidates,
)
from polynexus.orchestrator_parameter_actions import (
    _waxs_peak_shape_candidates as _shared_waxs_peak_shape_candidates,
)
from polynexus.orchestrator_parameter_actions import (
    _waxs_temperature_action_candidates as _shared_waxs_temperature_action_candidates,
)
from polynexus.orchestrator_session import (
    _can_converge_after_rollback as _shared_can_converge_after_rollback,
)
from polynexus.orchestrator_session import (
    _can_converge_on_small_delta as _shared_can_converge_on_small_delta,
)
from polynexus.orchestrator_session import (
    _candidate_rank as _shared_candidate_rank,
)
from polynexus.orchestrator_session import (
    _candidate_trial_summary as _shared_candidate_trial_summary,
)
from polynexus.orchestrator_session import (
    _execute_candidate_trial as _shared_execute_candidate_trial,
)
from polynexus.orchestrator_session import _final_report as _shared_final_report
from polynexus.orchestrator_session import _record_round as _shared_record_round
from polynexus.orchestrator_session import _restore_best as _shared_restore_best
from polynexus.orchestrator_session import (
    _restore_best_with_refresh as _shared_restore_best_with_refresh,
)
from polynexus.orchestrator_session import (
    _run_saxs_candidate_round as _shared_run_saxs_candidate_round,
)
from polynexus.orchestrator_state import _advice_rollback_detail as _shared_advice_rollback_detail
from polynexus.orchestrator_state import _advice_target_symptom as _shared_advice_target_symptom
from polynexus.orchestrator_state import _analysis_evidence as _shared_analysis_evidence
from polynexus.orchestrator_state import _analysis_symptoms as _shared_analysis_symptoms
from polynexus.orchestrator_state import (
    _attach_analysis_evidence as _shared_attach_analysis_evidence,
)
from polynexus.orchestrator_state import _build_agent_state as _shared_build_agent_state
from polynexus.orchestrator_state import _clean_advice as _shared_clean_advice
from polynexus.orchestrator_state import (
    _expand_saxs_candidates as _shared_expand_saxs_candidates,
)
from polynexus.orchestrator_state import (
    _expand_technique_candidates as _shared_expand_technique_candidates,
)
from polynexus.orchestrator_state import _symptom_names as _shared_symptom_names
from polynexus.orchestrator_state import _symptom_summary as _shared_symptom_summary
from polynexus.orchestrator_utils import (
    _canonical_submodule_id as _shared_canonical_submodule_id,
)
from polynexus.orchestrator_utils import _config_snapshot as _shared_config_snapshot
from polynexus.orchestrator_utils import _config_to_dict as _shared_config_to_dict
from polynexus.orchestrator_utils import _engine_config as _shared_engine_config
from polynexus.orchestrator_utils import (
    _flatten_dsc_parameters as _shared_flatten_dsc_parameters,
)
from polynexus.orchestrator_utils import (
    _flatten_ir_parameters as _shared_flatten_ir_parameters,
)
from polynexus.orchestrator_utils import (
    _flatten_nmr_parameters as _shared_flatten_nmr_parameters,
)
from polynexus.orchestrator_utils import (
    _goal_tuning_focus as _shared_goal_tuning_focus,
)
from polynexus.orchestrator_utils import _ir_reference_bands as _shared_ir_reference_bands
from polynexus.orchestrator_utils import _is_nan as _shared_is_nan
from polynexus.orchestrator_utils import (
    _joint_tuning_focus as _shared_joint_tuning_focus,
)
from polynexus.orchestrator_utils import _nmr_submodule_id as _shared_nmr_submodule_id
from polynexus.orchestrator_utils import _resolve_data_file as _shared_resolve_data_file
from polynexus.orchestrator_utils import _safe_float as _shared_safe_float
from polynexus.orchestrator_utils import _stable_signature as _shared_stable_signature
from polynexus.orchestrator_utils import _to_plain_value as _shared_to_plain_value
from polynexus.orchestrator_utils import _tunable_params as _shared_tunable_params
from polynexus.orchestrator_utils import _waxs_submodule_id as _shared_waxs_submodule_id
from llm.llm_client import LLMCancelledError

from polynexus.orchestrator_priority_rules import (
    GOAL_TUNING_PRIORITY_RULES,
    JOINT_TUNING_PRIORITY_RULES,
)


class ParameterOrchestrator:
    __init__ = _shared_init

    run = _shared_run
    run_preprocess_intent = _shared_public_run_preprocess_intent
    _run_preprocess_intent = _shared_run_preprocess_intent
    _snapshot_for_preprocess = _shared_snapshot_for_preprocess
    _execute_preprocess_candidate = _shared_execute_preprocess_candidate
    _commit_preprocess_candidate = _shared_commit_preprocess_candidate
    _emit_progress = _shared_emit_progress

    _restore_best = _shared_restore_best
    _record_round = _shared_record_round

    _build_agent_state = _shared_build_agent_state
    _clean_advice = _shared_clean_advice
    _analysis_evidence = _shared_analysis_evidence
    _attach_analysis_evidence = _shared_attach_analysis_evidence
    _analysis_symptoms = _shared_analysis_symptoms
    _symptom_names = _shared_symptom_names
    _symptom_summary = _shared_symptom_summary
    _advice_target_symptom = _shared_advice_target_symptom
    _advice_rollback_detail = _shared_advice_rollback_detail

    _decision_summary = _shared_decision_summary

    _allowed_actions = _shared_allowed_actions
    _allowed_changes = _shared_allowed_changes
    _expand_technique_candidates = _shared_expand_technique_candidates
    _expand_saxs_candidates = _shared_expand_saxs_candidates

    _guard_technique_direct_changes = _shared_guard_technique_direct_changes
    _guard_saxs_direct_changes = _shared_guard_saxs_direct_changes
    _candidate_plans_for_action = _shared_candidate_plans_for_action
    _saxs_recovery_context = _shared_saxs_recovery_context
    _candidate_plans_for_ir_action = _shared_candidate_plans_for_ir_action
    _candidate_plans_for_waxs_action = _shared_candidate_plans_for_waxs_action
    _candidate_plans_for_dsc_action = _shared_candidate_plans_for_dsc_action
    _candidate_plans_from_raw_candidates = _shared_candidate_plans_from_raw_candidates
    _current_config_value = _shared_current_config_value
    _dsc_action_candidates = _shared_dsc_action_candidates
    _waxs_action_candidates = _shared_waxs_action_candidates
    _waxs_temperature_action_candidates = _shared_waxs_temperature_action_candidates
    _waxs_peak_position_candidates = _shared_waxs_peak_position_candidates
    _waxs_peak_capacity_candidates = _shared_waxs_peak_capacity_candidates
    _waxs_background_candidates = _shared_waxs_background_candidates
    _waxs_peak_shape_candidates = _shared_waxs_peak_shape_candidates
    _waxs_low_angle_candidates = _shared_waxs_low_angle_candidates
    _ir_baseline_candidates = _shared_ir_baseline_candidates
    _ir_noise_candidates = _shared_ir_noise_candidates
    _ir_key_band_candidates = _shared_ir_key_band_candidates
    _ir_crowded_band_candidates = _shared_ir_crowded_band_candidates
    _ir_weak_support_candidates = _shared_ir_weak_support_candidates
    _ir_band_window_candidates = _shared_ir_band_window_candidates
    _ir_dynamic_signal_candidates = _shared_ir_dynamic_signal_candidates
    _ir_2dcos_denoise_candidates = _shared_ir_2dcos_denoise_candidates
    _ir_band_tracking_candidates = _shared_ir_band_tracking_candidates
    _ir_cross_peak_assignment_candidates = _shared_ir_cross_peak_assignment_candidates
    _saxs_range_action_candidates = _shared_saxs_range_action_candidates
    _saxs_crop_action_candidates = _shared_saxs_crop_action_candidates
    _saxs_idf_smoothing_candidates = _shared_saxs_idf_smoothing_candidates
    _normalize_candidate_value = _shared_normalize_candidate_value
    _normalize_saxs_candidate_value = _shared_normalize_saxs_candidate_value
    _candidate_values_equal = _shared_candidate_values_equal
    _execute_candidate_trial = _shared_execute_candidate_trial
    _candidate_trial_summary = _shared_candidate_trial_summary
    _candidate_rank = _shared_candidate_rank
    _restore_best_with_refresh = _shared_restore_best_with_refresh
    _run_saxs_candidate_round = _shared_run_saxs_candidate_round
    _final_report = _shared_final_report

    _benchmark_summary = _shared_benchmark_summary

    _round_symptom_hit = _shared_round_symptom_hit
    _symptom_target_params = _shared_symptom_target_params
    _can_converge_on_small_delta = _shared_can_converge_on_small_delta
    _can_converge_after_rollback = _shared_can_converge_after_rollback

    _quality_guard = _shared_quality_guard

    _decision_metrics = _shared_decision_metrics
    _evaluate_candidate = _shared_evaluate_candidate

    _saxs_low_q_priority_reason = _shared_saxs_low_q_priority_reason
    _stability_regression_reason = _shared_stability_regression_reason

    _score_snapshot = _shared_score_snapshot
    _saxs_evidence_snapshot = _shared_saxs_evidence_snapshot
    _ir_support_snapshot = _shared_ir_support_snapshot
    _stability_snapshot = _shared_stability_snapshot
    _dsc_support_snapshot = _shared_dsc_support_snapshot
    _waxs_support_snapshot = _shared_waxs_support_snapshot

    _regression_reason = _shared_regression_reason
    _dsc_regression_reason = _shared_dsc_regression_reason
    _waxs_regression_reason = _shared_waxs_regression_reason
    _waxs_temperature_regression_reason = _shared_waxs_temperature_regression_reason
    _ir_regression_reason = _shared_ir_regression_reason

    _joint_ai_context = _shared_joint_ai_context

    _residual_score = _shared_residual_score

    _first_text = _shared_first_text
    _mean_or_none = _shared_mean_or_none

    _objective_gain_threshold = _shared_objective_gain_threshold
    _r_squared_drop_tolerance = _shared_r_squared_drop_tolerance
    _component_drop_tolerance = _shared_component_drop_tolerance

    _saxs_cross_validation = _shared_saxs_cross_validation
    _dsc_cross_validation = _shared_dsc_cross_validation

    _resolve_data_file = _shared_resolve_data_file
    _config_snapshot = _shared_config_snapshot
    _config_to_dict = _shared_config_to_dict
    _ir_reference_bands = _shared_ir_reference_bands

    _output_parameters = _shared_output_parameters
    _dsc_output_parameters = _shared_dsc_output_parameters
    _nmr_output_parameters = _shared_nmr_output_parameters
    _ir_output_parameters = _shared_ir_output_parameters
    _saxs_output_parameters = _shared_saxs_output_parameters
    _saxs_score = _shared_saxs_score
    _residual_pattern = _shared_residual_pattern
    _dsc_residual_pattern = _shared_dsc_residual_pattern
    _saxs_residual_pattern = _shared_saxs_residual_pattern
    _ir_residual_pattern = _shared_ir_residual_pattern
    _nmr_residual_pattern = _shared_nmr_residual_pattern
    _select_dsc_residual_result = _shared_select_dsc_residual_result
    _empty_residual_pattern = _shared_empty_residual_pattern

    _tunable_params = _shared_tunable_params
    _goal_tuning_focus = _shared_goal_tuning_focus
    _joint_tuning_focus = _shared_joint_tuning_focus
    _engine_config = _shared_engine_config

    _submodule_id = _shared_submodule_id
    _submodule_name = _shared_submodule_name
    _public_submodule = _shared_public_submodule
    _agent_state_submodule = _shared_agent_state_submodule
    _canonical_submodule_id = _shared_canonical_submodule_id
    _waxs_submodule_id = _shared_waxs_submodule_id
    _nmr_submodule_id = _shared_nmr_submodule_id
    _flatten_dsc_parameters = _shared_flatten_dsc_parameters
    _flatten_ir_parameters = _shared_flatten_ir_parameters
    _flatten_nmr_parameters = _shared_flatten_nmr_parameters
    _is_nan = _shared_is_nan
    _safe_float = _shared_safe_float
    _to_plain_value = _shared_to_plain_value
    _stable_signature = _shared_stable_signature


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run WAXS static AI parameter orchestration.")
    parser.add_argument("--data-file", required=True)
    parser.add_argument("--polymer", required=True)
    parser.add_argument("--max-rounds", type=int, default=5)
    args = parser.parse_args(argv)

    report = ParameterOrchestrator(
        technique="waxs",
        data_file=args.data_file,
        polymer_name=args.polymer,
        max_rounds=args.max_rounds,
    ).run()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
