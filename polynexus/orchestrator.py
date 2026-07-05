from __future__ import annotations
import logging
logger = logging.getLogger(__name__)


import json
import math
import re
import inspect
import threading
from copy import deepcopy
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np

from polynexus.config_bridge import DSC_PARAM_MAP, IR_PARAM_MAP, NMR_PARAM_MAP, SAXS_PARAM_MAP, WAXS_PARAM_MAP, apply_changes
from polynexus.core import get_engine
from polynexus.core.analysis_evidence import build_analysis_evidence
from polynexus.core.dsc_action_registry import actions_for_symptoms as dsc_actions_for_symptoms
from polynexus.core.dsc_action_registry import allowed_changes_for_actions as dsc_allowed_changes_for_actions
from polynexus.core.saxs_action_registry import actions_for_symptoms as saxs_actions_for_symptoms
from polynexus.core.saxs_action_registry import allowed_changes_for_actions as saxs_allowed_changes_for_actions
from polynexus.core.ir_action_registry import actions_for_symptoms as ir_actions_for_symptoms
from polynexus.core.ir_action_registry import allowed_changes_for_actions as ir_allowed_changes_for_actions
from polynexus.core.waxs_temperature_action_registry import actions_for_symptoms as waxs_temperature_actions_for_symptoms
from polynexus.core.waxs_temperature_action_registry import allowed_changes_for_actions as waxs_temperature_allowed_changes_for_actions
from polynexus.core.dsc_engine import aggregate_dsc_result_metrics
from polynexus.core.dsc_residual_analyzer import DSCResidualAnalyzer, DSCResidualPattern
from polynexus.core.ir_residual_analyzer import IRResidualAnalyzer, IRResidualPattern
from polynexus.core.residual_analyzer import ResidualAnalyzer, ResidualPattern
from polynexus.core.saxs_residual_analyzer import SAXSResidualAnalyzer, SAXSResidualPattern
from polynexus.core.waxs_residual_analyzer import WAXSResidualAnalyzer, WAXSResidualPattern
from llm.config import create_llm_client
from rag.advisor import Advisor
from rag.polymer_knowledge import load_polymer_knowledge
from polynexus.core.ir_engine.names import normalize_ir_polymer_name
from llm.llm_client import LLMCancelledError


JOINT_TUNING_PRIORITY_RULES: dict[str, dict[str, list[tuple[str, str]]]] = {
    "WAXS": {
        "phi_c inconsistency": [
            ("amorphous_subtraction", "tighten crystallinity partitioning before trusting phi_c"),
            ("crystallinity_method", "align crystallinity estimation with the joint cross-tech signal"),
            ("peak_function", "stabilize peak separation so crystallinity is less shape-sensitive"),
        ],
        "L consistency unstable": [
            ("peak_function", "stabilize peak separation feeding the WAXS-derived structure signal"),
            ("peak_distance", "separate overlapping peaks before re-reading the structure"),
            ("two_theta_offset", "correct a position bias before accepting the current fit"),
            ("amorphous_n_peaks", "revisit halo modeling when the peak family keeps moving"),
        ],
    },
    "DSC": {
        "tm bidirectional gap": [
            ("Tm_search_low_C", "re-center the melting search window around the joint check"),
            ("Tm_search_high_C", "widen the melting search window only after the center is stable"),
            ("peak_function", "refit the endotherm before pushing the search window again"),
            ("baseline_type", "stabilize baseline handling before trusting the temperature shift"),
        ],
        "phi_c inconsistency": [
            ("peak_prominence_ratio", "tighten DSC event selection before comparing phi_c"),
            ("baseline_type", "reduce baseline bias before updating crystallinity"),
            ("smooth_window", "reduce noise before reading crystallinity-related events"),
        ],
    },
    "SAXS": {
        "l consistency unstable": [
            ("savgol_window", "stabilize the low-q signal before touching the window edges"),
            ("q_bragg_min", "move the Bragg region toward the consistent signal"),
            ("q_bragg_max", "move the Bragg region toward the consistent signal"),
            ("q_corr_min", "tighten the correlation region before reusing the L estimate"),
            ("q_corr_max", "tighten the correlation region before reusing the L estimate"),
            ("lorentz_fit_method", "revisit the long-period fit backend when L keeps drifting"),
        ],
        "phi_c inconsistency": [
            ("savgol_window", "remove small-scale noise before re-evaluating crystallinity"),
            ("q_corr_min", "keep the crystallinity estimate away from unstable low-q data"),
            ("q_corr_max", "keep the crystallinity estimate away from unstable high-q data"),
            ("idf_peak_rel_thresh", "treat weak secondary peaks more conservatively"),
        ],
        "tm bidirectional gap": [
            ("tangent_lc_min_nm", "protect the SAXS thickness estimate before linking it to DSC"),
            ("lorentz_fit_method", "revisit the fit method before re-deriving the thermal bridge"),
        ],
    },
    "IR": {
        "phi_c inconsistency": [
            ("baseline_method", "remove baseline bias before comparing crystallinity across techniques"),
            ("normalization_method", "re-scale the bands before updating the crystallinity path"),
            ("peak_fit_window_cm1", "tighten the local window before reassigning bands"),
            ("peak_height_min", "drop weak band noise before comparing crystallinity"),
        ],
    },
    "NMR": {
        "phi_c inconsistency": [
            ("baseline_method", "stabilize the baseline before re-reading crystallinity"),
            ("peak_distance_ppm", "separate crowded resonances before adjusting the assignment"),
            ("deconvolution_method", "revisit the deconvolution before changing thresholds again"),
            ("lb_Hz", "sharpen the lineshape before comparing across techniques"),
        ],
    },
}


GOAL_TUNING_PRIORITY_RULES: dict[str, dict[str, list[tuple[str, str]]]] = {
    "WAXS": {
        "symptom": [
            ("peak_function", "repair the local peak shape before reading the residual again"),
            ("peak_distance", "separate the peak family when the fit is still crowded"),
            ("two_theta_offset", "correct the peak position bias before trusting the result"),
            ("smooth_window", "stabilize noisy peak neighborhoods first"),
        ],
        "risk": [
            ("background_method", "reduce background risk before widening the interpretation"),
            ("amorphous_subtraction", "stabilize the amorphous split before trusting Xc"),
            ("amorphous_n_peaks", "avoid over-complex halo modeling when the background is fragile"),
            ("two_theta_offset", "keep position drift under control while reducing risk"),
        ],
        "joint": [
            ("amorphous_subtraction", "align crystallinity support before comparing across techniques"),
            ("peak_function", "make the WAXS family shape more comparable across runs"),
            ("two_theta_offset", "remove the position bias before accepting the current family"),
            ("background_method", "keep the background path consistent with the cross-tech signal"),
        ],
        "stability": [
            ("smooth_window", "keep the next round conservative by tightening the smoothing first"),
            ("peak_function", "prefer a stable peak family before exploring wider changes"),
            ("peak_distance", "avoid unnecessary peak-family reshaping"),
            ("amorphous_n_peaks", "keep the background split simple and repeatable"),
        ],
    },
    "SAXS": {
        "symptom": [
            ("savgol_window", "repair the noisy low-q signal before changing the windows"),
            ("q_bragg_min", "re-center the Bragg window around the active peak"),
            ("q_bragg_max", "keep the Bragg window wide enough to capture the peak cleanly"),
            ("q_corr_min", "stabilize the correlation floor before reusing L"),
        ],
        "risk": [
            ("q_corr_min", "keep the thickness chain away from unstable low-q data"),
            ("q_corr_max", "tighten the correlation ceiling before the next rerun"),
            ("tangent_lc_min_nm", "protect the tangent-derived thickness from implausible values"),
            ("lorentz_fit_method", "switch the backend only when the risk remains after preprocessing"),
        ],
        "joint": [
            ("q_corr_min", "align the SAXS thickness chain with the joint consistency check"),
            ("q_corr_max", "keep the thickness chain comparable across techniques"),
            ("tangent_lc_min_nm", "protect the joint-aware thickness estimate"),
            ("savgol_window", "stabilize the low-q shape before comparing across techniques"),
        ],
        "stability": [
            ("savgol_window", "keep the next round conservative by smoothing first"),
            ("q_corr_min", "avoid unnecessary lower-bound drift"),
            ("q_corr_max", "avoid unnecessary upper-bound drift"),
            ("tangent_lc_min_nm", "keep the thickness floor conservative"),
        ],
    },
    "DSC": {
        "symptom": [
            ("peak_function", "repair the peak shape before nudging the search window again"),
            ("smooth_window", "suppress small oscillations before re-reading the peak"),
            ("tm_search_low_C", "re-center the melting search window around the active event"),
            ("tm_search_high_C", "keep the melting search window wide enough to capture the event"),
        ],
        "risk": [
            ("baseline_type", "reduce baseline risk before trusting the crystallinity path"),
            ("smooth_window", "stabilize the noisy edge before pushing the fit further"),
            ("peak_prominence_ratio", "avoid weak-event overfitting while lowering risk"),
            ("min_event_enthalpy_Jg", "keep marginal events from driving the next rerun"),
        ],
        "joint": [
            ("baseline_type", "align the thermal baseline before comparing across techniques"),
            ("peak_function", "make the thermal peak family easier to compare"),
            ("tm_search_low_C", "re-center the temperature bridge before accepting it"),
            ("tm_search_high_C", "keep the temperature bridge wide enough to be robust"),
        ],
        "stability": [
            ("baseline_type", "keep the next round conservative by stabilizing the baseline"),
            ("smooth_window", "prefer a smaller change when the curve is already close"),
            ("peak_function", "avoid unnecessary changes to the peak family"),
        ],
    },
    "IR": {
        "symptom": [
            ("peak_height_min", "repair weak peak visibility before changing more knobs"),
            ("peak_prominence_min", "separate the meaningful bands from the noise floor"),
            ("peak_distance", "resolve crowded bands before the next rerun"),
            ("peak_fit_window_cm1", "keep the local fit window focused on the active band"),
        ],
        "risk": [
            ("baseline_method", "reduce baseline risk before trusting the assignment"),
            ("normalization_method", "keep the amplitude scaling stable"),
            ("smooth_window", "stabilize the band shape before moving thresholds"),
        ],
        "joint": [
            ("baseline_method", "align the band baseline before comparing across techniques"),
            ("normalization_method", "keep the scaling comparable across techniques"),
            ("peak_fit_window_cm1", "keep the cross-tech band comparison focused"),
        ],
        "stability": [
            ("smooth_window", "keep the next round conservative by smoothing first"),
            ("peak_distance", "avoid unnecessary band reshaping"),
            ("baseline_method", "prefer a repeatable baseline path"),
        ],
    },
    "NMR": {
        "symptom": [
            ("peak_height_min", "repair weak resonance visibility before widening the search"),
            ("peak_distance_ppm", "separate crowded resonances before the next rerun"),
            ("deconvolution_method", "fix the peak family shape before changing thresholds again"),
            ("baseline_method", "stabilize the low-level drift before re-reading the spectrum"),
        ],
        "risk": [
            ("baseline_method", "reduce baseline risk before trusting the fit"),
            ("baseline_order", "keep the baseline model conservative"),
            ("lb_Hz", "avoid over-sharpening the lineshape while lowering risk"),
            ("deconvolution_method", "keep the decomposition stable before further exploration"),
        ],
        "joint": [
            ("baseline_method", "align the NMR baseline before comparing across techniques"),
            ("peak_distance_ppm", "keep crowded peaks comparable across techniques"),
            ("deconvolution_method", "make the decomposition path more consistent"),
        ],
        "stability": [
            ("baseline_method", "keep the next round conservative by stabilizing the baseline"),
            ("lb_Hz", "avoid unnecessary lineshape exploration"),
            ("max_peaks", "keep the candidate family size stable"),
        ],
    },
}


SAXS_LOW_Q_PRIORITY_SYMPTOMS = {
    "beamstop_or_low_q_contamination",
    "low_q_void_dominant",
    "strain_void_lamellar_conflict",
    "lamellar_anchor_lost_under_strain",
    "qstar_rel_without_lamellar_support",
    "orientation_shift_breaks_lamellar_comparison",
    "idf_artifact_regular_spacing",
    "gamma_tangent_unstable",
    "temperature_calibration_fallback_active",
    "batch_summary_conflicts_with_frame_evidence",
    "thickness_chain_unreliable",
}

SAXS_LOW_Q_FIRST_ACTION_ORDER = (
    "adjust_q_crop",
    "adjust_corr_window",
    "adjust_idf_smoothing",
)

SAXS_LOW_Q_SUPPORT_ACTION_ORDER = (
    "rerun_condition_recovery",
    "mark_frame_outlier",
    "split_batch_by_sample",
)


@dataclass
class RoundRecord:
    round_num: int
    config_snapshot: dict[str, Any]
    output_parameters: dict[str, Any]
    residuals_pattern: dict[str, Any]
    analysis_evidence: dict[str, Any]
    polymer_knowledge: dict[str, Any]
    r_squared: float
    eval_score: float
    llm_advice: dict[str, Any] | None
    round_idx: int = 0
    r_squared_before: float = 0.0
    r_squared_after: float = 0.0
    changes: dict[str, Any] | None = None
    accepted: bool = True
    prompt: str = ""
    symptoms: list[dict[str, Any]] = field(default_factory=list)
    symptom_names: list[str] = field(default_factory=list)
    symptom_summary: str = ""
    target_symptom: str = ""
    rollback_detail: str = ""
    decision_summary: str = ""


class ParameterOrchestrator:
    def __init__(
        self,
        technique: str,
        data_file: str,
        polymer_name: str,
        max_rounds: int = 5,
        advisor: Advisor | None = None,
        llm_settings: dict[str, Any] | None = None,
        project_root: str | Path | None = None,
        workspace_context: dict[str, Any] | None = None,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
        submodule_override: str | None = None,
        cancel_event: "threading.Event | None" = None,
    ):
        if technique.lower() not in {"waxs", "dsc", "saxs", "ir", "nmr"}:
            raise ValueError("ParameterOrchestrator currently supports WAXS static, DSC standard, SAXS static, IR standard, and NMR partitions only.")
        self.technique = technique.lower()
        self.data_file = str(data_file)
        self.polymer_name = polymer_name
        self.max_rounds = max_rounds
        self.llm_settings = dict(llm_settings or {})
        self.advisor = advisor or Advisor(llm_client=create_llm_client(self.llm_settings))
        self.project_root = Path(project_root).resolve() if project_root else Path.cwd()
        self.workspace_context = self._to_plain_value(workspace_context or {})
        self.progress_callback = progress_callback
        self.submodule_override = submodule_override
        self._cancel_event = cancel_event
        self.polymer_knowledge = load_polymer_knowledge(polymer_name)
        self.history: list[RoundRecord] = []

        self._engine = None
        self._best_config = None
        self._best_output: dict[str, Any] = {}
        self._best_record: RoundRecord | None = None
        self._best_r_squared = -math.inf
        self._best_eval_score = -math.inf
        self._baseline_r_squared = 0.0
        self._baseline_eval_score = 0.0

    def run(self) -> dict[str, Any]:
        data_path = self._resolve_data_file(self.data_file)
        submodule_id = self._submodule_id()
        engine = get_engine(self.technique, submodule_id=submodule_id)
        if engine is None:
            raise RuntimeError(f"{self.technique.upper()} engine is not registered.")
        self._engine = engine

        engine.run_pipeline(str(data_path), output_dir="")
        baseline = self._record_round(engine, 0, None, changes={}, accepted=True)
        self.history.append(baseline)
        self._baseline_r_squared = baseline.r_squared
        self._best_r_squared = baseline.r_squared
        self._baseline_eval_score = baseline.eval_score
        self._best_eval_score = baseline.eval_score
        self._best_config = deepcopy(self._engine_config(engine))
        self._best_output = dict(baseline.output_parameters)
        self._best_record = baseline

        converged = False
        convergence_reason = "max_rounds"

        for round_num in range(1, self.max_rounds + 1):
            if self._cancel_event and self._cancel_event.is_set():
                convergence_reason = "cancelled"
                break
            self._restore_best(engine)
            state = self._build_agent_state(engine, round_num)
            try:
                advise_kwargs: dict[str, Any] = {}
                if "workspace_context" in inspect.signature(self.advisor.advise).parameters:
                    advise_kwargs["workspace_context"] = self.workspace_context
                if self._cancel_event is not None and "cancel_event" in inspect.signature(self.advisor.advise).parameters:
                    advise_kwargs["cancel_event"] = self._cancel_event
                advice = self.advisor.advise(state, **advise_kwargs)
            except LLMCancelledError:
                convergence_reason = "cancelled"
                break
            prompt = str(getattr(self.advisor, "last_prompt", ""))
            changes = advice.get("changes", {})
            previous_record = self._best_record or baseline
            previous_r_squared = previous_record.r_squared
            if not isinstance(changes, dict):
                advice = dict(advice)
                invalid_changes = changes
                changes = {}
                advice["changes"] = {}
                advice["rejected"] = True
                advice["rollback_reason"] = f"changes must be a dict, got {type(invalid_changes).__name__}"
                advice["rollback_detail"] = "The advisor returned an invalid changes payload, so this round was rejected before execution."
                self.history.append(
                    self._record_round(
                        engine,
                        round_num,
                        advice,
                        before_r_squared=previous_r_squared,
                        changes=changes,
                        accepted=False,
                        prompt=prompt,
                    )
                )
                self._emit_progress(round_num, previous_r_squared, previous_r_squared, changes, "rejected", advice["rollback_reason"])
                continue

            candidate_plans: list[dict[str, Any]] = []
            if self.technique in {"dsc", "ir", "saxs", "waxs"}:
                candidate_plans = self._expand_technique_candidates(advice if isinstance(advice, dict) else {}, state)

            if not changes and not candidate_plans:
                target_symptom = self._advice_target_symptom(advice if isinstance(advice, dict) else None, state.get("analysis_evidence", {}))
                symptom_summary = self._symptom_summary(state.get("symptoms", []))
                self.history.append(
                    self._record_round(
                        engine,
                        round_num,
                        advice,
                        before_r_squared=previous_r_squared,
                        changes=changes,
                        accepted=True,
                        prompt=prompt,
                    )
                )
                self._emit_progress(
                    round_num,
                    previous_r_squared,
                    previous_r_squared,
                    changes,
                    "converged",
                    converged=True,
                    target_symptom=target_symptom,
                    symptom_summary=symptom_summary,
                )
                converged = True
                convergence_reason = "optimal"
                break

            if candidate_plans:
                candidate_outcome = self._run_saxs_candidate_round(
                    engine,
                    round_num,
                    advice if isinstance(advice, dict) else {},
                    previous_record,
                    candidate_plans,
                    prompt,
                )
                candidate = candidate_outcome["record"]
                status = str(candidate_outcome.get("status", "rejected") or "rejected")
                changes = dict(candidate_outcome.get("changes", {}) or {})
                delta = candidate.r_squared - previous_r_squared

                self.history.append(candidate)
                if candidate.accepted and delta < 0.001 and self._can_converge_on_small_delta(candidate, round_num):
                    converged = True
                    convergence_reason = "delta_r_squared<0.001"
                    if status == "improved":
                        status = "converged"
                elif status == "rolled_back" and self._can_converge_after_rollback(round_num):
                    converged = True
                    convergence_reason = "no_improvement_after_history"
                current_advice = candidate.llm_advice if isinstance(candidate.llm_advice, dict) else {}
                self._emit_progress(
                    round_num,
                    previous_r_squared,
                    candidate.r_squared,
                    changes,
                    status,
                    error=str(current_advice.get("rollback_reason", "") or ""),
                    converged=converged,
                    target_symptom=candidate.target_symptom,
                    symptom_summary=candidate.symptom_summary,
                )
                if converged:
                    break
                continue

            ok, error = apply_changes(self._engine_config(engine), changes, technique=self.technique)
            if not ok:
                rejected = dict(advice)
                rejected["rejected"] = True
                rejected["rollback_reason"] = error
                rejected["rollback_detail"] = "The proposed parameter change violates the local config constraints, so the run was skipped."
                self._restore_best(engine)
                self.history.append(
                    self._record_round(
                        engine,
                        round_num,
                        rejected,
                        before_r_squared=previous_r_squared,
                        changes=changes,
                        accepted=False,
                        prompt=prompt,
                    )
                )
                self._emit_progress(round_num, previous_r_squared, previous_r_squared, changes, "rejected", error)
                continue

            if not engine.analyze():
                rejected = dict(advice)
                rejected["rejected"] = True
                rejected["rollback_reason"] = "engine.analyze() failed"
                rejected["rollback_detail"] = "The core analysis failed to finish, so the candidate was rolled back immediately."
                self._restore_best(engine)
                self.history.append(
                    self._record_round(
                        engine,
                        round_num,
                        rejected,
                        before_r_squared=previous_r_squared,
                        changes=changes,
                        accepted=False,
                        prompt=prompt,
                    )
                )
                self._emit_progress(round_num, previous_r_squared, previous_r_squared, changes, "rejected", "engine.analyze() failed")
                continue
            engine.result.parameters = engine.get_parameters()

            candidate = self._record_round(
                engine,
                round_num,
                advice,
                before_r_squared=previous_r_squared,
                changes=changes,
                accepted=True,
                prompt=prompt,
            )
            delta = candidate.r_squared - previous_r_squared
            status = "improved"
            quality_ok, quality_error = self._quality_guard(candidate)
            if not quality_ok:
                rejected = dict(advice)
                rejected["rejected"] = True
                rejected["rollback_reason"] = quality_error
                rejected["decision_metrics"] = self._decision_metrics(candidate, previous_record)
                rejected["rollback_detail"] = self._advice_rollback_detail(rejected)
                candidate.llm_advice = rejected
                candidate.accepted = False
                candidate.target_symptom = self._advice_target_symptom(rejected, candidate.analysis_evidence)
                candidate.rollback_detail = rejected["rollback_detail"]
                candidate.decision_summary = self._decision_summary(False, candidate.target_symptom, candidate.rollback_detail, {"objective_score": candidate.eval_score})
                self._restore_best(engine)
                status = "rolled_back"
            else:
                accepted, rollback_reason, decision_metrics = self._evaluate_candidate(candidate, previous_record)
                if accepted:
                    self._best_r_squared = candidate.r_squared
                    self._best_eval_score = candidate.eval_score
                    self._best_record = candidate
                    self._best_config = deepcopy(self._engine_config(engine))
                    self._best_output = dict(candidate.output_parameters)
                else:
                    rejected = dict(advice)
                    rejected["rejected"] = True
                    rejected["rollback_reason"] = rollback_reason
                    rejected["decision_metrics"] = decision_metrics
                    rejected["rollback_detail"] = self._advice_rollback_detail(rejected)
                    candidate.llm_advice = rejected
                    candidate.accepted = False
                    candidate.target_symptom = self._advice_target_symptom(rejected, candidate.analysis_evidence)
                    candidate.rollback_detail = rejected["rollback_detail"]
                    candidate.decision_summary = self._decision_summary(False, candidate.target_symptom, candidate.rollback_detail, {"objective_score": candidate.eval_score})
                    self._restore_best(engine)
                    status = "rolled_back"

            self.history.append(candidate)
            if status != "rolled_back" and delta < 0.001 and self._can_converge_on_small_delta(candidate, round_num):
                converged = True
                convergence_reason = "delta_r_squared<0.001"
                if status == "improved":
                    status = "converged"
            elif status == "rolled_back" and self._can_converge_after_rollback(round_num):
                converged = True
                convergence_reason = "no_improvement_after_history"
            current_advice = candidate.llm_advice if isinstance(candidate.llm_advice, dict) else {}
            self._emit_progress(
                round_num,
                previous_r_squared,
                candidate.r_squared,
                changes,
                status,
                error=str(current_advice.get("rollback_reason", "") or ""),
                converged=converged,
                target_symptom=candidate.target_symptom,
                symptom_summary=candidate.symptom_summary,
            )
            if converged:
                break

        return self._final_report(data_path, converged, convergence_reason)

    def _emit_progress(
        self,
        round_num: int,
        before_r_squared: float,
        after_r_squared: float,
        changes: dict[str, Any],
        status: str,
        error: str = "",
        converged: bool = False,
        target_symptom: str = "",
        symptom_summary: str = "",
    ) -> None:
        if self.progress_callback is None:
            return
        self.progress_callback(
            {
                "round_num": round_num,
                "max_rounds": self.max_rounds,
                "before_r_squared": before_r_squared,
                "after_r_squared": after_r_squared,
                "changes": self._to_plain_value(changes),
                "status": status,
                "error": error,
                "converged": converged,
                "target_symptom": target_symptom,
                "symptom_summary": symptom_summary,
            }
        )

    def _restore_best(self, engine: Any) -> None:
        if self._best_config is not None:
            if self.technique == "dsc":
                engine._dsc_config = deepcopy(self._best_config)
            elif self.technique == "saxs":
                engine.cfg = deepcopy(self._best_config)
            elif self.technique == "ir":
                engine._ir_config = deepcopy(self._best_config)
            elif self.technique == "nmr":
                engine._cfg = deepcopy(self._best_config)
            else:
                engine._waxs_config = deepcopy(self._best_config)

    def _record_round(
        self,
        engine: Any,
        round_num: int,
        advice: dict[str, Any] | None,
        before_r_squared: float | None = None,
        changes: dict[str, Any] | None = None,
        accepted: bool = True,
        prompt: str = "",
    ) -> RoundRecord:
        output = self._output_parameters(engine)
        residuals_pattern = self._residual_pattern(engine)
        analysis_evidence = self._analysis_evidence(output, residuals_pattern)
        score_snapshot = self._score_snapshot(output, residuals_pattern, analysis_evidence)
        self._attach_analysis_evidence(engine, analysis_evidence)
        r_squared = self._safe_float(output.get("r_squared", 0.0))
        config_snapshot = self._config_snapshot(engine)
        clean_advice = self._clean_advice(advice)
        round_changes = changes
        if round_changes is None and isinstance(clean_advice, dict):
            maybe_changes = clean_advice.get("changes", {})
            round_changes = maybe_changes if isinstance(maybe_changes, dict) else {}
        round_changes = round_changes or {}
        before = r_squared if before_r_squared is None else self._safe_float(before_r_squared)
        symptoms = self._analysis_symptoms(analysis_evidence)
        clean_advice_dict = self._to_plain_value(clean_advice) if clean_advice is not None else None
        target_symptom = self._advice_target_symptom(clean_advice_dict, analysis_evidence)
        rollback_detail = self._advice_rollback_detail(clean_advice_dict)
        decision_summary = self._decision_summary(accepted, target_symptom, rollback_detail, score_snapshot)
        return RoundRecord(
            round_num=round_num,
            config_snapshot=config_snapshot,
            output_parameters=output,
            residuals_pattern=residuals_pattern,
            analysis_evidence=analysis_evidence,
            polymer_knowledge=self._to_plain_value(self.polymer_knowledge),
            r_squared=r_squared,
            eval_score=score_snapshot["objective_score"],
            llm_advice=clean_advice_dict,
            round_idx=round_num,
            r_squared_before=before,
            r_squared_after=r_squared,
            changes=self._to_plain_value(round_changes),
            accepted=accepted,
            prompt=prompt,
            symptoms=symptoms,
            symptom_names=self._symptom_names(symptoms),
            symptom_summary=self._symptom_summary(symptoms),
            target_symptom=target_symptom,
            rollback_detail=rollback_detail,
            decision_summary=decision_summary,
        )

    def _build_agent_state(self, engine: Any, round_num: int) -> dict[str, Any]:
        output = self._output_parameters(engine)
        config = self._config_snapshot(engine)
        residuals_pattern = self._residual_pattern(engine)
        analysis_evidence = self._analysis_evidence(output, residuals_pattern)
        ir_reference_bands = self._ir_reference_bands(engine)
        score_snapshot = self._score_snapshot(output, residuals_pattern, analysis_evidence)
        symptoms = self._analysis_symptoms(analysis_evidence)
        allowed_actions = self._allowed_actions(symptoms)
        allowed_changes = self._allowed_changes(allowed_actions)
        return {
            "case_id": f"live_{self.polymer_name}_{self.technique}",
            "technique": self.technique.upper(),
            "submodule": self._agent_state_submodule(),
            "data_file": self.data_file,
            "polymer_name": self.polymer_name,
            "round": round_num,
            "current_config": config,
            "params": output,
            "output_parameters": output,
            "r_squared": self._safe_float(output.get("r_squared", 0.0)),
            "residuals_pattern": residuals_pattern.get("summary", ""),
            "residual_pattern": residuals_pattern,
            "analysis_evidence": analysis_evidence,
            "ir_reference_bands": ir_reference_bands,
            "symptoms": symptoms,
            "symptom_names": self._symptom_names(symptoms),
            "symptom_summary": self._symptom_summary(symptoms),
            "allowed_actions": allowed_actions,
            "allowed_changes": allowed_changes,
            "polymer_knowledge": self._to_plain_value(self.polymer_knowledge),
            "workspace_context": self._to_plain_value(self.workspace_context) if self.workspace_context else {},
            "history": [record for record in self.history if record.round_num > 0],
            "previous_score": self._best_eval_score if math.isfinite(self._best_eval_score) else None,
            "objective_score": score_snapshot["objective_score"],
            "tunable_params": self._tunable_params(config, allowed_actions=allowed_actions),
        }

    def _clean_advice(self, advice: dict[str, Any] | None) -> dict[str, Any] | None:
        if advice is None:
            return None
        return {key: value for key, value in advice.items() if not str(key).startswith("_")}

    def _analysis_evidence(self, output: dict[str, Any], residuals_pattern: dict[str, Any]) -> dict[str, Any]:
        validation_context: dict[str, Any] = {}
        if self._engine is not None:
            validation_context["config_snapshot"] = self._config_to_dict(self._engine_config(self._engine))
            validation_context["submodule_id"] = self._submodule_id()
            if self.technique == "ir":
                validation_context["ir_reference_bands"] = self._ir_reference_bands(self._engine)
        if self.technique == "saxs":
            validation_context["cross_validation"] = self._saxs_cross_validation(output)
        elif self.technique == "dsc":
            validation_context["cross_validation"] = self._dsc_cross_validation(output)
        return build_analysis_evidence(
            self.technique,
            output_parameters=output,
            residual_pattern=residuals_pattern,
            validation_context=validation_context,
        ).to_dict()

    def _attach_analysis_evidence(self, engine: Any, analysis_evidence: dict[str, Any]) -> None:
        if engine is None:
            return
        result = getattr(engine, "result", None)
        if result is None:
            return
        setter = getattr(result, "set_analysis_evidence", None)
        if callable(setter):
            setter(analysis_evidence)
            return
        try:
            result.analysis_evidence = dict(analysis_evidence)
        except Exception:
            pass

    def _analysis_symptoms(self, analysis_evidence: dict[str, Any]) -> list[dict[str, Any]]:
        if not isinstance(analysis_evidence, dict):
            return []
        symptoms = analysis_evidence.get("symptoms", [])
        if not isinstance(symptoms, list):
            return []
        out: list[dict[str, Any]] = []
        for symptom in symptoms:
            if not isinstance(symptom, dict):
                continue
            name = str(symptom.get("name", "") or "").strip()
            if not name:
                continue
            out.append(self._to_plain_value(symptom))
        return out

    def _symptom_names(self, symptoms: list[dict[str, Any]] | None) -> list[str]:
        names: list[str] = []
        for symptom in symptoms or []:
            if not isinstance(symptom, dict):
                continue
            name = str(symptom.get("name", "") or "").strip()
            if name and name not in names:
                names.append(name)
        return names

    def _symptom_summary(self, symptoms: list[dict[str, Any]] | None) -> str:
        parts: list[str] = []
        for symptom in symptoms or []:
            if not isinstance(symptom, dict):
                continue
            name = str(symptom.get("name", "") or "").strip()
            summary = str(symptom.get("summary", "") or "").strip()
            if not name:
                continue
            if summary:
                parts.append(f"{name}: {summary}")
            else:
                parts.append(name)
        return " | ".join(parts[:3])

    def _advice_target_symptom(self, advice: dict[str, Any] | None, analysis_evidence: dict[str, Any]) -> str:
        if isinstance(advice, dict):
            target = str(advice.get("target_symptom", "") or "").strip()
            if target:
                return target
        names = self._symptom_names(self._analysis_symptoms(analysis_evidence))
        return names[0] if names else ""

    def _advice_rollback_detail(self, advice: dict[str, Any] | None) -> str:
        if not isinstance(advice, dict):
            return ""
        detail = str(advice.get("rollback_detail", "") or "").strip()
        if detail:
            return detail
        reason = str(advice.get("rollback_reason", "") or "").strip()
        decision = advice.get("decision_metrics", {}) if isinstance(advice.get("decision_metrics"), dict) else {}
        candidate = decision.get("candidate", {}) if isinstance(decision.get("candidate"), dict) else {}
        previous = decision.get("previous", {}) if isinstance(decision.get("previous"), dict) else {}
        target = str(advice.get("target_symptom", "") or "").strip()

        if not reason:
            return ""
        if reason.startswith("new_hard_fail_introduced:"):
            hard_names = reason.split(":", 1)[1]
            return f"New hard-fail evidence appeared: {hard_names}."
        if reason == "no_meaningful_gain":
            return f"Target symptom {target or 'current symptom'} did not improve enough to keep the change."
        if reason == "fit_score_dropped":
            return "The fit score regressed after the trial change."
        if reason == "quality_score_dropped":
            return "The quality score dropped after the trial change."
        if reason == "validation_risk_increased":
            return "Validation risk increased after the trial change."
        if reason == "residual_risk_increased":
            return "Residual structure became less trustworthy after the trial change."
        if reason == "fit_improved_but_phys_worse":
            return "The fit looked better, but the physical evidence became weaker."
        if reason == "condition_continuity_worsened":
            return "The recovered series axis became less continuous after the trial change."
        if reason == "structure_jump_too_large":
            return "Cross-method structure agreement drifted too far after the trial change."
        if reason == "symptom_unresolved":
            return "The targeted SAXS symptom stayed unresolved, so the result still needs manual review."
        if reason == "stability_score_dropped":
            return "Overall SAXS stability dropped after the trial change."
        if reason == "low_q_contamination_unresolved":
            return "Low-q contamination is still the dominant problem, so this round should keep repairing the low-q evidence chain first."
        if reason == "fallback_still_dominant":
            return "Fallback-derived thickness values are still dominating the batch summary, so the system will not keep this result before the low-q evidence stabilizes."
        if reason == "raw_calibrated_conflict_worsened":
            return "The calibrated batch summary moved further away from the raw frame structure evidence after the trial change."
        if reason == "thickness_chain_still_unreliable":
            return "Thickness-chain evidence is still not trustworthy enough to keep this trial result."
        if reason == "peak_family_became_less_stable":
            return "The WAXS peak family became less stable after the trial change."
        if reason == "background_partition_worsened":
            return "The WAXS background and amorphous partition became less trustworthy after the trial change."
        if reason == "crystallinity_support_collapsed":
            return "Crystallinity or size support weakened too much after the trial change."
        if reason == "physical_support_weakened":
            return "The overall WAXS physical support weakened too much after the trial change."
        if reason.startswith("quality_score below"):
            return reason
        if candidate or previous:
            candidate_score = self._safe_float(candidate.get("objective_score", 0.0))
            previous_score = self._safe_float(previous.get("objective_score", 0.0))
            return f"Objective score did not justify keeping the change ({previous_score:.3f} -> {candidate_score:.3f})."
        return reason

    def _decision_summary(
        self,
        accepted: bool,
        target_symptom: str,
        rollback_detail: str,
        score_snapshot: dict[str, Any],
    ) -> str:
        symptom_part = f"target={target_symptom}" if target_symptom else ""
        objective_part = f"objective={self._safe_float(score_snapshot.get('objective_score', 0.0)):.3f}"
        if accepted:
            parts = [part for part in (symptom_part, objective_part) if part]
            return "accepted" + (f" | {' | '.join(parts)}" if parts else "")
        detail = rollback_detail or "rolled back"
        parts = [part for part in (symptom_part, objective_part) if part]
        return detail + (f" | {' | '.join(parts)}" if parts else "")

    def _allowed_actions(self, symptoms: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
        if self.technique not in {"dsc", "ir", "saxs", "waxs"}:
            return []
        if self.technique == "dsc":
            return dsc_actions_for_symptoms(symptoms, technique="DSC")
        if self.technique == "ir":
            return ir_actions_for_symptoms(symptoms, technique="IR")
        if self.technique == "waxs" and self._submodule_id() in {"waxs.temperature", "waxs.in_situ_temp"}:
            return waxs_temperature_actions_for_symptoms(symptoms, technique="WAXS.TEMPERATURE")
        actions = saxs_actions_for_symptoms(symptoms, technique=self.technique.upper())
        if not actions:
            return []

        if self.technique != "saxs":
            return actions

        symptom_names = set(self._symptom_names(symptoms))
        low_q_first = bool(symptom_names & SAXS_LOW_Q_PRIORITY_SYMPTOMS)
        fallback_conflict_active = bool(
            "temperature_calibration_fallback_active" in symptom_names
            and (
                "batch_summary_conflicts_with_frame_evidence" in symptom_names
                or "thickness_chain_unreliable" in symptom_names
            )
        )

        prioritized_names = set(SAXS_LOW_Q_FIRST_ACTION_ORDER)
        support_names = set(SAXS_LOW_Q_SUPPORT_ACTION_ORDER)
        deferred_names = {"switch_lorentz_method", "raise_tangent_floor"}

        if fallback_conflict_active:
            actions = [
                action for action in actions
                if str(action.get("name", "") or "").strip() not in deferred_names
            ]

        if not low_q_first:
            return actions

        def _rank(action: dict[str, Any]) -> tuple[int, int, int, str]:
            name = str(action.get("name", "") or "").strip()
            if name in SAXS_LOW_Q_FIRST_ACTION_ORDER:
                lane = 0
                slot = SAXS_LOW_Q_FIRST_ACTION_ORDER.index(name)
            elif name in SAXS_LOW_Q_SUPPORT_ACTION_ORDER:
                lane = 1
                slot = SAXS_LOW_Q_SUPPORT_ACTION_ORDER.index(name)
            elif name in prioritized_names:
                lane = 0
                slot = 99
            elif name in support_names:
                lane = 1
                slot = 99
            else:
                lane = 2
                slot = 99
            return (
                lane,
                slot,
                -int(action.get("priority", 0) or 0),
                name,
            )

        actions.sort(key=_rank)
        return actions

    def _allowed_changes(self, allowed_actions: list[dict[str, Any]] | None) -> dict[str, list[Any]]:
        if self.technique not in {"dsc", "ir", "saxs", "waxs"}:
            return {}
        if self.technique == "dsc":
            return dsc_allowed_changes_for_actions(allowed_actions, technique="DSC")
        if self.technique == "ir":
            return ir_allowed_changes_for_actions(allowed_actions, technique="IR")
        if self.technique == "waxs" and self._submodule_id() in {"waxs.temperature", "waxs.in_situ_temp"}:
            return waxs_temperature_allowed_changes_for_actions(allowed_actions, technique="WAXS.TEMPERATURE")
        return saxs_allowed_changes_for_actions(allowed_actions, technique=self.technique.upper())

    def _expand_technique_candidates(self, advice: dict[str, Any] | None, state: dict[str, Any] | None) -> list[dict[str, Any]]:
        if self.technique not in {"dsc", "ir", "saxs", "waxs"}:
            return []

        advice_dict = advice if isinstance(advice, dict) else {}
        state_dict = state if isinstance(state, dict) else {}
        current_config = state_dict.get("current_config", {}) if isinstance(state_dict.get("current_config"), dict) else {}
        allowed_actions = state_dict.get("allowed_actions", []) if isinstance(state_dict.get("allowed_actions"), list) else []
        allowed_changes = state_dict.get("allowed_changes", {}) if isinstance(state_dict.get("allowed_changes"), dict) else {}
        symptom_names = state_dict.get("symptom_names", [])
        symptom_names = symptom_names if isinstance(symptom_names, list) else []
        target_symptom = str(advice_dict.get("target_symptom", "") or "").strip()
        if not target_symptom:
            if symptom_names:
                target_symptom = str(symptom_names[0] or "").strip()

        action_specs: dict[str, dict[str, Any]] = {}
        for action in allowed_actions:
            if not isinstance(action, dict):
                continue
            name = str(action.get("name", "") or "").strip()
            if name:
                action_specs[name] = action

        plans: list[dict[str, Any]] = []
        direct_changes = advice_dict.get("changes", {})
        if self.technique == "dsc":
            param_map = DSC_PARAM_MAP
        if self.technique == "ir":
            param_map = IR_PARAM_MAP
        elif self.technique == "saxs":
            param_map = SAXS_PARAM_MAP
        elif self.technique == "waxs":
            param_map = WAXS_PARAM_MAP
        technique_label = self.technique.upper()

        if isinstance(direct_changes, dict) and direct_changes:
            guarded_changes, guard_error = self._guard_technique_direct_changes(
                direct_changes,
                allowed_changes,
                current_config,
                param_map,
                technique_label,
            )
            if guarded_changes:
                plans.append(
                    {
                        "action_name": "advisor_changes",
                        "label": "Advisor changes",
                        "reason": str(advice_dict.get("reasoning", "") or "").strip(),
                        "target_symptom": target_symptom,
                        "expected_evidence_change": "",
                        "changes": guarded_changes,
                        "executable": True,
                    }
                )
            elif guard_error:
                plans.append(
                    {
                        "action_name": "advisor_changes",
                        "label": "Advisor changes",
                        "reason": str(advice_dict.get("reasoning", "") or "").strip(),
                        "target_symptom": target_symptom,
                        "expected_evidence_change": "",
                        "changes": {},
                        "executable": False,
                        "skip_reason": guard_error,
                    }
                )

        recommended_actions = advice_dict.get("recommended_actions", [])
        if not isinstance(recommended_actions, list):
            recommended_actions = [recommended_actions] if recommended_actions else []

        low_q_first = self.technique == "saxs" and bool(set(str(item or "").strip() for item in symptom_names) & SAXS_LOW_Q_PRIORITY_SYMPTOMS)
        requested_action_names = {
            (
                str(item.get("name", "") or "").strip()
                if isinstance(item, dict)
                else str(item or "").strip()
            )
            for item in recommended_actions
        }
        requested_action_names = {name for name in requested_action_names if name}

        if low_q_first:
            prioritized_actions: list[dict[str, Any]] = []
            for action_name in SAXS_LOW_Q_FIRST_ACTION_ORDER:
                spec = action_specs.get(action_name)
                if not isinstance(spec, dict):
                    continue
                prioritized_actions.append(
                    {
                        "name": action_name,
                        "reason": "Low-q evidence is still unstable, so this round must repair the low-q / correlation chain first.",
                        "expected_evidence_change": "",
                    }
                )
            for action_name in SAXS_LOW_Q_SUPPORT_ACTION_ORDER:
                if action_name in requested_action_names:
                    continue
                spec = action_specs.get(action_name)
                if not isinstance(spec, dict):
                    continue
                prioritized_actions.append(
                    {
                        "name": action_name,
                        "reason": "Support the low-q recovery path before trusting the thickness chain.",
                        "expected_evidence_change": "",
                    }
                )
            existing = list(recommended_actions)
            recommended_actions = prioritized_actions + existing

        for item in recommended_actions:
            if isinstance(item, dict):
                action_name = str(item.get("name", "") or "").strip()
                reason = str(item.get("reason", "") or "").strip()
                expected = str(item.get("expected_evidence_change", "") or "").strip()
            else:
                action_name = str(item or "").strip()
                reason = ""
                expected = ""
            if not action_name:
                continue
            spec = action_specs.get(action_name, {"name": action_name, "allowed_params": []})
            plans.extend(
                self._candidate_plans_for_action(
                    action_name=action_name,
                    current_config=current_config,
                    allowed_changes=allowed_changes,
                    action_spec=spec,
                    target_symptom=target_symptom,
                    reason=reason,
                    expected_evidence_change=expected,
                )
            )

        unique: list[dict[str, Any]] = []
        seen: set[tuple[Any, ...]] = set()
        executable_count = 0
        for plan in plans:
            if not isinstance(plan, dict):
                continue
            changes = plan.get("changes", {})
            executable = bool(plan.get("executable", False))
            if executable and isinstance(changes, dict):
                key = (
                    "plan",
                    str(plan.get("action_name", "") or "").strip(),
                    tuple(sorted((str(name), self._stable_signature(value)) for name, value in changes.items())),
                    self._stable_signature(plan.get("recovery_context", {})),
                )
            else:
                key = (
                    "skip",
                    str(plan.get("action_name", "") or "").strip(),
                    str(plan.get("skip_reason", "") or "").strip(),
                )
            if key in seen:
                continue
            seen.add(key)
            if executable:
                if executable_count >= 5:
                    continue
                executable_count += 1
            unique.append(self._to_plain_value(plan))
        return unique

    def _expand_saxs_candidates(self, advice: dict[str, Any] | None, state: dict[str, Any] | None) -> list[dict[str, Any]]:
        return self._expand_technique_candidates(advice, state)

    def _guard_technique_direct_changes(
        self,
        changes: dict[str, Any],
        allowed_changes: dict[str, list[Any]],
        current_config: dict[str, Any],
        param_map: dict[str, Any],
        technique_label: str,
    ) -> tuple[dict[str, Any], str]:
        if not isinstance(changes, dict) or not changes:
            return {}, ""

        # Keep SAXS tightly action-gated, but let WAXS direct tuning explore
        # any known config field and rely on scoring / rollback to veto bad trials.
        if allowed_changes and technique_label == "SAXS":
            disallowed = [str(name) for name in changes.keys() if str(name) not in allowed_changes]
            if disallowed:
                joined = ", ".join(disallowed)
                return {}, f"Advisor changes are outside the current {technique_label} action whitelist: {joined}."

        normalized: dict[str, Any] = {}
        for name, value in changes.items():
            param_name = str(name or "").strip()
            if not param_name or param_name not in param_map:
                return {}, f"Advisor changes include an unknown {technique_label} parameter: {param_name or name}."
            candidate_value = self._normalize_candidate_value(param_name, value, param_map)
            current_value = self._current_config_value(current_config, param_name, param_map)
            if self._candidate_values_equal(candidate_value, current_value):
                continue
            normalized[param_name] = candidate_value
        return normalized, ""

    def _guard_saxs_direct_changes(
        self,
        changes: dict[str, Any],
        allowed_changes: dict[str, list[Any]],
        current_config: dict[str, Any],
    ) -> tuple[dict[str, Any], str]:
        return self._guard_technique_direct_changes(changes, allowed_changes, current_config, SAXS_PARAM_MAP, "SAXS")

    def _candidate_plans_for_action(
        self,
        *,
        action_name: str,
        current_config: dict[str, Any],
        allowed_changes: dict[str, list[Any]],
        action_spec: dict[str, Any],
        target_symptom: str,
        reason: str,
        expected_evidence_change: str,
    ) -> list[dict[str, Any]]:
        if self.technique == "saxs" and action_name == "rerun_condition_recovery":
            recovery_context = self._saxs_recovery_context(current_config)
            expected = expected_evidence_change.strip() if expected_evidence_change else ""
            if not expected:
                expected_items = action_spec.get("expected_evidence_change", [])
                if isinstance(expected_items, list) and expected_items:
                    expected = " | ".join(str(item or "").strip() for item in expected_items if str(item or "").strip())
            if recovery_context:
                return [
                    {
                        "action_name": action_name,
                        "label": str(action_spec.get("label", action_name.replace("_", " ").title()) or "").strip(),
                        "reason": reason,
                        "target_symptom": target_symptom,
                        "expected_evidence_change": expected,
                        "changes": {},
                        "recovery_context": recovery_context,
                        "executable": True,
                    }
                ]
            return [
                {
                    "action_name": action_name,
                    "label": str(action_spec.get("label", action_name.replace("_", " ").title()) or "").strip(),
                    "reason": reason,
                    "target_symptom": target_symptom,
                    "expected_evidence_change": expected,
                    "changes": {},
                    "recovery_context": {},
                    "executable": False,
                    "skip_reason": "Action 'rerun_condition_recovery' did not find a recoverable condition_context in the current SAXS config.",
                }
            ]
        if self.technique == "waxs" and self._submodule_id() in {"waxs.temperature", "waxs.in_situ_temp"}:
            raw_candidates = self._waxs_temperature_action_candidates(action_name, current_config)
            if raw_candidates:
                return self._candidate_plans_from_raw_candidates(
                    action_name=action_name,
                    current_config=current_config,
                    allowed_changes=allowed_changes,
                    allowed_params=[
                        str(item or "").strip()
                        for item in action_spec.get("allowed_params", [])
                        if str(item or "").strip()
                    ],
                    action_spec=action_spec,
                    target_symptom=target_symptom,
                    reason=reason,
                    expected=expected_evidence_change.strip() if expected_evidence_change else "",
                    raw_candidates=raw_candidates,
                    param_map=WAXS_PARAM_MAP,
                    technique_label="WAXS temperature",
                )
            return [
                {
                    "action_name": action_name,
                    "label": str(action_spec.get("label", action_name.replace("_", " ").title()) or "").strip(),
                    "reason": reason,
                    "target_symptom": target_symptom,
                    "expected_evidence_change": expected_evidence_change.strip() if expected_evidence_change else "",
                    "changes": {},
                    "executable": False,
                    "skip_reason": f"Action '{action_name}' is advisory-only for WAXS temperature and has no direct config edit in the current engine.",
                }
            ]
        if self.technique == "waxs":
            return self._candidate_plans_for_waxs_action(
                action_name=action_name,
                current_config=current_config,
                allowed_changes=allowed_changes,
                action_spec=action_spec,
                target_symptom=target_symptom,
                reason=reason,
                expected_evidence_change=expected_evidence_change,
            )
        if self.technique == "ir":
            return self._candidate_plans_for_ir_action(
                action_name=action_name,
                current_config=current_config,
                allowed_changes=allowed_changes,
                action_spec=action_spec,
                target_symptom=target_symptom,
                reason=reason,
                expected_evidence_change=expected_evidence_change,
            )
        if self.technique == "dsc":
            return self._candidate_plans_for_dsc_action(
                action_name=action_name,
                current_config=current_config,
                allowed_changes=allowed_changes,
                action_spec=action_spec,
                target_symptom=target_symptom,
                reason=reason,
                expected_evidence_change=expected_evidence_change,
            )

        allowed_params = [
            str(item or "").strip()
            for item in action_spec.get("allowed_params", [])
            if str(item or "").strip()
        ]
        label = str(action_spec.get("label", action_name.replace("_", " ").title()) or "").strip()
        expected = expected_evidence_change.strip() if expected_evidence_change else ""
        if not expected:
            expected_items = action_spec.get("expected_evidence_change", [])
            if isinstance(expected_items, list) and expected_items:
                expected = " | ".join(str(item or "").strip() for item in expected_items if str(item or "").strip())

        if not allowed_params:
            return [
                {
                    "action_name": action_name,
                    "label": label,
                    "reason": reason,
                    "target_symptom": target_symptom,
                    "expected_evidence_change": expected,
                    "changes": {},
                    "executable": False,
                    "skip_reason": f"Action '{action_name}' is recognized, but this orchestrator pass cannot execute it automatically yet.",
                }
            ]

        raw_candidates: list[dict[str, Any]] = []
        if action_name == "adjust_peak_window":
            raw_candidates = self._saxs_range_action_candidates(
                current_config,
                "q_bragg_min",
                "q_bragg_max",
                inward_first=True,
            )
        elif action_name == "adjust_corr_window":
            raw_candidates = self._saxs_range_action_candidates(
                current_config,
                "q_corr_min",
                "q_corr_max",
                inward_first=True,
            )
        elif action_name == "adjust_q_crop":
            raw_candidates = self._saxs_crop_action_candidates(current_config)
        elif action_name == "adjust_idf_smoothing":
            raw_candidates = self._saxs_idf_smoothing_candidates(current_config)
        elif action_name == "switch_lorentz_method":
            current_method = str(current_config.get("lorentz_fit_method", "") or "").strip()
            choices = SAXS_PARAM_MAP["lorentz_fit_method"].constraint
            for choice in choices:
                if str(choice) == current_method:
                    continue
                raw_candidates.append({"lorentz_fit_method": str(choice)})
        elif action_name == "raise_tangent_floor":
            current_value = self._safe_float(current_config.get("tangent_lc_min_nm", 2.0))
            raw_candidates.append({"tangent_lc_min_nm": current_value + 0.5})
            raw_candidates.append({"tangent_lc_min_nm": current_value + 1.0})

        return self._candidate_plans_from_raw_candidates(
            action_name=action_name,
            current_config=current_config,
            allowed_changes=allowed_changes,
            allowed_params=allowed_params,
            action_spec=action_spec,
            target_symptom=target_symptom,
            reason=reason,
            expected=expected,
            raw_candidates=raw_candidates,
            param_map=SAXS_PARAM_MAP,
            technique_label="SAXS",
        )

    def _saxs_recovery_context(self, current_config: dict[str, Any]) -> dict[str, Any]:
        context: dict[str, Any] = {}
        if isinstance(current_config, dict):
            cfg_context = current_config.get("condition_context", {})
            if isinstance(cfg_context, dict) and cfg_context:
                context = deepcopy(cfg_context)
        workspace_context = self.workspace_context if isinstance(self.workspace_context, dict) else {}
        if isinstance(workspace_context, dict) and workspace_context:
            for key in ("condition_context", "sample", "batch", "condition_values"):
                value = workspace_context.get(key)
                if not value:
                    continue
                if key == "condition_context" and isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if sub_key not in context or context[sub_key] in (None, "", {}, []):
                            context[sub_key] = deepcopy(sub_value)
                    continue
                if key not in context or context[key] in (None, "", {}, []):
                    context[key] = deepcopy(value)
        return context

    def _candidate_plans_for_ir_action(
        self,
        *,
        action_name: str,
        current_config: dict[str, Any],
        allowed_changes: dict[str, list[Any]],
        action_spec: dict[str, Any],
        target_symptom: str,
        reason: str,
        expected_evidence_change: str,
    ) -> list[dict[str, Any]]:
        allowed_params = [
            str(item or "").strip()
            for item in action_spec.get("allowed_params", [])
            if str(item or "").strip()
        ]
        label = str(action_spec.get("label", action_name.replace("_", " ").title()) or "").strip()
        expected = expected_evidence_change.strip() if expected_evidence_change else ""
        if not expected:
            expected_items = action_spec.get("expected_evidence_change", [])
            if isinstance(expected_items, list) and expected_items:
                expected = " | ".join(str(item or "").strip() for item in expected_items if str(item or "").strip())

        raw_candidates: list[dict[str, Any]] = []
        if action_name == "rebalance_baseline":
            raw_candidates = self._ir_baseline_candidates(current_config)
        elif action_name == "reduce_noise":
            raw_candidates = self._ir_noise_candidates(current_config)
        elif action_name == "tighten_key_band_fit":
            raw_candidates = self._ir_key_band_candidates(current_config)
        elif action_name == "separate_crowded_bands":
            raw_candidates = self._ir_crowded_band_candidates(current_config)
        elif action_name == "lift_weak_band_support":
            raw_candidates = self._ir_weak_support_candidates(current_config)
        elif action_name == "expand_band_window":
            raw_candidates = self._ir_band_window_candidates(current_config)
        elif action_name == "repair_sequence_axis":
            raw_candidates = self._ir_band_window_candidates(current_config)
        elif action_name == "stabilize_matrix_baseline":
            raw_candidates = self._ir_baseline_candidates(current_config)
        elif action_name == "recover_dynamic_signal":
            raw_candidates = self._ir_dynamic_signal_candidates(current_config)
        elif action_name == "denoise_2dcos":
            raw_candidates = self._ir_2dcos_denoise_candidates(current_config)
        elif action_name == "stabilize_band_tracking":
            raw_candidates = self._ir_band_tracking_candidates(current_config)
        elif action_name == "tighten_cross_peak_assignment":
            raw_candidates = self._ir_cross_peak_assignment_candidates(current_config)

        return self._candidate_plans_from_raw_candidates(
            action_name=action_name,
            current_config=current_config,
            allowed_changes=allowed_changes,
            allowed_params=allowed_params,
            action_spec=action_spec,
            target_symptom=target_symptom,
            reason=reason,
            expected=expected,
            raw_candidates=raw_candidates,
            param_map=IR_PARAM_MAP,
            technique_label="IR",
        )

    def _candidate_plans_for_waxs_action(
        self,
        *,
        action_name: str,
        current_config: dict[str, Any],
        allowed_changes: dict[str, list[Any]],
        action_spec: dict[str, Any],
        target_symptom: str,
        reason: str,
        expected_evidence_change: str,
    ) -> list[dict[str, Any]]:
        allowed_params = [
            str(item or "").strip()
            for item in action_spec.get("allowed_params", [])
            if str(item or "").strip()
        ]
        label = str(action_spec.get("label", action_name.replace("_", " ").title()) or "").strip()
        expected = expected_evidence_change.strip() if expected_evidence_change else ""
        if not expected:
            expected_items = action_spec.get("expected_evidence_change", [])
            if isinstance(expected_items, list) and expected_items:
                expected = " | ".join(str(item or "").strip() for item in expected_items if str(item or "").strip())

        raw_candidates = self._waxs_action_candidates(action_name, current_config)
        return self._candidate_plans_from_raw_candidates(
            action_name=action_name,
            current_config=current_config,
            allowed_changes=allowed_changes,
            allowed_params=allowed_params,
            action_spec=action_spec,
            target_symptom=target_symptom,
            reason=reason,
            expected=expected,
            raw_candidates=raw_candidates,
            param_map=WAXS_PARAM_MAP,
            technique_label="WAXS",
        )

    def _candidate_plans_for_dsc_action(
        self,
        *,
        action_name: str,
        current_config: dict[str, Any],
        allowed_changes: dict[str, list[Any]],
        action_spec: dict[str, Any],
        target_symptom: str,
        reason: str,
        expected_evidence_change: str,
    ) -> list[dict[str, Any]]:
        allowed_params = [
            str(item or "").strip()
            for item in action_spec.get("allowed_params", [])
            if str(item or "").strip()
        ]
        label = str(action_spec.get("label", action_name.replace("_", " ").title()) or "").strip()
        expected = expected_evidence_change.strip() if expected_evidence_change else ""
        if not expected:
            expected_items = action_spec.get("expected_evidence_change", [])
            if isinstance(expected_items, list) and expected_items:
                expected = " | ".join(str(item or "").strip() for item in expected_items if str(item or "").strip())

        raw_candidates = self._dsc_action_candidates(action_name, current_config)
        return self._candidate_plans_from_raw_candidates(
            action_name=action_name,
            current_config=current_config,
            allowed_changes=allowed_changes,
            allowed_params=allowed_params,
            action_spec=action_spec,
            target_symptom=target_symptom,
            reason=reason,
            expected=expected,
            raw_candidates=raw_candidates,
            param_map=DSC_PARAM_MAP,
            technique_label="DSC",
        )

    def _candidate_plans_from_raw_candidates(
        self,
        *,
        action_name: str,
        current_config: dict[str, Any],
        allowed_changes: dict[str, list[Any]],
        allowed_params: list[str],
        action_spec: dict[str, Any],
        target_symptom: str,
        reason: str,
        expected: str,
        raw_candidates: list[dict[str, Any]],
        param_map: dict[str, Any],
        technique_label: str,
    ) -> list[dict[str, Any]]:
        label = str(action_spec.get("label", action_name.replace("_", " ").title()) or "").strip()
        plans: list[dict[str, Any]] = []
        for raw_changes in raw_candidates:
            candidate_changes: dict[str, Any] = {}
            skip_reason = ""
            for param_name, value in raw_changes.items():
                if allowed_changes and param_name not in allowed_changes:
                    skip_reason = f"Action '{action_name}' proposed '{param_name}', which is outside the current {technique_label} action whitelist."
                    break
                if allowed_params and param_name not in allowed_params:
                    skip_reason = f"Action '{action_name}' proposed '{param_name}', which is outside the registry spec."
                    break
                candidate_value = self._normalize_candidate_value(param_name, value, param_map)
                current_value = self._current_config_value(current_config, param_name, param_map)
                if self._candidate_values_equal(candidate_value, current_value):
                    continue
                candidate_changes[param_name] = candidate_value
            if skip_reason:
                plans.append(
                    {
                        "action_name": action_name,
                        "label": label,
                        "reason": reason,
                        "target_symptom": target_symptom,
                        "expected_evidence_change": expected,
                        "changes": {},
                        "executable": False,
                        "skip_reason": skip_reason,
                    }
                )
                continue
            if not candidate_changes:
                continue
            plans.append(
                {
                    "action_name": action_name,
                    "label": label,
                    "reason": reason,
                    "target_symptom": target_symptom,
                    "expected_evidence_change": expected,
                    "changes": candidate_changes,
                    "executable": True,
                }
            )

        if not plans:
            plans.append(
                {
                    "action_name": action_name,
                    "label": label,
                    "reason": reason,
                    "target_symptom": target_symptom,
                    "expected_evidence_change": expected,
                    "changes": {},
                    "executable": False,
                    "skip_reason": f"Action '{action_name}' did not produce a valid guarded {technique_label} candidate from the current config.",
                }
            )
        return plans

    def _current_config_value(
        self,
        current_config: dict[str, Any],
        param_name: str,
        param_map: dict[str, Any],
    ) -> Any:
        if not isinstance(current_config, dict):
            return None
        if param_name in current_config:
            return current_config.get(param_name)
        rule = param_map.get(param_name)
        if rule is not None:
            field_name = getattr(rule, "field_name", "")
            if field_name and field_name in current_config:
                return current_config.get(field_name)
        return current_config.get(param_name)

    def _dsc_action_candidates(self, action_name: str, current_config: dict[str, Any]) -> list[dict[str, Any]]:
        baseline_choices = [choice for choice in DSC_PARAM_MAP["baseline_type"].constraint if isinstance(choice, str)]
        peak_choices = [choice for choice in DSC_PARAM_MAP["peak_function"].constraint if isinstance(choice, str)]
        tg_method_choices = [choice for choice in DSC_PARAM_MAP["Tg_method"].constraint if isinstance(choice, str)]
        baseline = str(current_config.get("baseline_type", current_config.get("baseline_corr", "")) or "").strip()
        peak_function = str(current_config.get("peak_function", "") or "").strip()
        exo_up = bool(current_config.get("exo_up", True))
        smooth_window = int(round(self._safe_float(current_config.get("smooth_window", 11)) or 11))
        tg_low = self._safe_float(current_config.get("tg_search_low_C", current_config.get("Tg_search_low_C", 20.0))) or 20.0
        tg_high = self._safe_float(current_config.get("tg_search_high_C", current_config.get("Tg_search_high_C", 120.0))) or 120.0
        tm_low = self._safe_float(current_config.get("tm_search_low_C", current_config.get("Tm_search_low_C", 100.0))) or 100.0
        tm_high = self._safe_float(current_config.get("tm_search_high_C", current_config.get("Tm_search_high_C", 300.0))) or 300.0
        tc_low = self._safe_float(current_config.get("tc_search_low_C", current_config.get("Tc_search_low_C", 50.0))) or 50.0
        tc_high = self._safe_float(current_config.get("tc_search_high_C", current_config.get("Tc_search_high_C", 250.0))) or 250.0
        prom = self._safe_float(current_config.get("peak_prominence_ratio", 0.03)) or 0.03
        enthalpy = self._safe_float(current_config.get("min_event_enthalpy_Jg", 0.05)) or 0.05
        max_width = self._safe_float(current_config.get("max_melting_peak_width_C", 50.0)) or 50.0

        candidates: list[dict[str, Any]] = []
        if action_name == "stabilize_baseline":
            for choice in baseline_choices:
                if choice != baseline:
                    candidates.append({"baseline_type": choice})
                    break
            candidates.append({"smooth_window": smooth_window + 2 if smooth_window < 31 else max(3, smooth_window - 2)})
        elif action_name == "align_polarity":
            candidates.append({"exo_up": not exo_up})
            for choice in baseline_choices:
                if choice != baseline:
                    candidates.append({"baseline_type": choice})
                    break
        elif action_name == "restore_tg_support":
            width = max(10.0, min(35.0, (tg_high - tg_low) * 0.2))
            center = (tg_low + tg_high) / 2.0
            candidates.append({"tg_search_low_C": max(0.0, center - width)})
            candidates.append({"tg_search_high_C": min(240.0, center + width)})
            for choice in tg_method_choices:
                if choice != str(current_config.get("Tg_method", "") or "").strip():
                    candidates.append({"Tg_method": choice})
                    break
        elif action_name == "tighten_melting_window":
            center = (tm_low + tm_high) / 2.0
            span = max(25.0, min(80.0, (tm_high - tm_low) * 0.75))
            candidates.append({"tm_search_low_C": max(50.0, center - span / 2.0)})
            candidates.append({"tm_search_high_C": min(380.0, center + span / 2.0)})
            for choice in peak_choices:
                if choice != peak_function:
                    candidates.append({"peak_function": choice})
                    break
        elif action_name == "separate_cold_crystallization":
            candidates.append({"tc_search_low_C": max(0.0, tc_low - 10.0)})
            candidates.append({"tc_search_high_C": min(320.0, tc_high + 10.0)})
            candidates.append({"tm_search_low_C": max(50.0, tm_low + 5.0)})
        elif action_name == "strengthen_event_detection":
            candidates.append({"peak_prominence_ratio": min(0.2, prom * 1.2)})
            candidates.append({"min_event_enthalpy_Jg": min(5.0, enthalpy * 1.2)})
            candidates.append({"max_melting_peak_width_C": max(5.0, max_width * 0.85)})
            candidates.append({"smooth_window": smooth_window + 2 if smooth_window < 31 else max(3, smooth_window - 2)})
        elif action_name == "stabilize_scan_consistency":
            candidates.append({"smooth_window": smooth_window + 2 if smooth_window < 31 else max(3, smooth_window - 2)})
            candidates.append({"peak_prominence_ratio": min(0.2, prom * 1.15)})
            candidates.append({"baseline_type": baseline_choices[0] if baseline_choices and baseline != baseline_choices[0] else baseline_choices[1] if len(baseline_choices) > 1 else baseline})
        return candidates[:4]

    def _waxs_action_candidates(self, action_name: str, current_config: dict[str, Any]) -> list[dict[str, Any]]:
        if action_name == "adjust_peak_position":
            return self._waxs_peak_position_candidates(current_config)
        if action_name == "increase_peak_capacity":
            return self._waxs_peak_capacity_candidates(current_config, expand=True)
        if action_name == "reduce_peak_capacity":
            return self._waxs_peak_capacity_candidates(current_config, expand=False)
        if action_name == "rebalance_background_partition":
            return self._waxs_background_candidates(current_config)
        if action_name == "stabilize_peak_shape":
            return self._waxs_peak_shape_candidates(current_config)
        if action_name == "trim_low_angle_drift":
            return self._waxs_low_angle_candidates(current_config)
        return []

    def _waxs_temperature_action_candidates(self, action_name: str, current_config: dict[str, Any]) -> list[dict[str, Any]]:
        if action_name == "stabilize_peak_family_tracking":
            return self._waxs_peak_shape_candidates(current_config)
        if action_name == "rebalance_temperature_background":
            return self._waxs_background_candidates(current_config)
        if action_name == "stabilize_temperature_peak_shape":
            return self._waxs_peak_shape_candidates(current_config)
        if action_name == "recover_temperature_axis":
            return []
        if action_name == "split_temperature_series":
            return []
        if action_name == "mark_temperature_frame_outlier":
            return []
        if action_name == "promote_transition_candidate":
            return []
        return []

    def _waxs_peak_position_candidates(self, current_config: dict[str, Any]) -> list[dict[str, Any]]:
        offset = self._safe_float(current_config.get("two_theta_offset", 0.0))
        step = max(0.01, min(abs(offset) * 0.5 if offset else 0.04, 0.12))
        if offset > 0:
            toward_zero = {"two_theta_offset": offset - step}
            away_from_zero = {"two_theta_offset": offset + step}
        elif offset < 0:
            toward_zero = {"two_theta_offset": offset + step}
            away_from_zero = {"two_theta_offset": offset - step}
        else:
            toward_zero = {"two_theta_offset": step}
            away_from_zero = {"two_theta_offset": -step}
        return [toward_zero, away_from_zero]

    def _waxs_peak_capacity_candidates(self, current_config: dict[str, Any], *, expand: bool) -> list[dict[str, Any]]:
        max_peaks = int(round(self._safe_float(current_config.get("max_peaks", 8)) or 8))
        peak_distance = self._safe_float(current_config.get("peak_distance", 0.8))
        if expand:
            return [
                {"max_peaks": max_peaks + 1},
                {"max_peaks": max_peaks + 2},
                {"peak_distance": max(0.5, peak_distance - 0.08)},
            ]
        return [
            {"max_peaks": max(4, max_peaks - 1)},
            {"max_peaks": max(4, max_peaks - 2)},
            {"peak_distance": min(2.0, peak_distance + 0.08)},
        ]

    def _waxs_background_candidates(self, current_config: dict[str, Any]) -> list[dict[str, Any]]:
        background_choices = [choice for choice in WAXS_PARAM_MAP["background_method"].constraint if isinstance(choice, str)]
        amorphous_choices = [choice for choice in WAXS_PARAM_MAP["amorphous_subtraction"].constraint if isinstance(choice, str)]
        current_background = str(current_config.get("background_method", "") or "").strip()
        current_amorphous = str(current_config.get("amorphous_subtraction", "") or "").strip()
        current_n_peaks = int(round(self._safe_float(current_config.get("amorphous_n_peaks", 2)) or 2))

        candidates: list[dict[str, Any]] = []
        for choice in background_choices:
            if choice != current_background:
                candidates.append({"background_method": choice})
                break
        for choice in amorphous_choices:
            if choice != current_amorphous:
                candidates.append({"amorphous_subtraction": choice})
                break
        candidates.append({"amorphous_n_peaks": 1 if current_n_peaks > 1 else 2})
        return candidates

    def _waxs_peak_shape_candidates(self, current_config: dict[str, Any]) -> list[dict[str, Any]]:
        peak_choices = [choice for choice in WAXS_PARAM_MAP["peak_function"].constraint if isinstance(choice, str)]
        current_peak = str(current_config.get("peak_function", "") or "").strip()
        current_window = int(round(self._safe_float(current_config.get("smooth_window", 5)) or 5))
        candidates: list[dict[str, Any]] = []
        for choice in peak_choices:
            if choice != current_peak:
                candidates.append({"peak_function": choice})
        candidates.append({"smooth_window": current_window + 2 if current_window < 13 else max(3, current_window - 2)})
        return candidates[:3]

    def _waxs_low_angle_candidates(self, current_config: dict[str, Any]) -> list[dict[str, Any]]:
        offset = self._safe_float(current_config.get("two_theta_offset", 0.0))
        background_choices = [choice for choice in WAXS_PARAM_MAP["background_method"].constraint if isinstance(choice, str)]
        amorphous_choices = [choice for choice in WAXS_PARAM_MAP["amorphous_subtraction"].constraint if isinstance(choice, str)]
        current_background = str(current_config.get("background_method", "") or "").strip()
        current_amorphous = str(current_config.get("amorphous_subtraction", "") or "").strip()
        candidates: list[dict[str, Any]] = []
        if abs(offset) > 0.005:
            candidates.append({"two_theta_offset": offset - (offset * 0.5)})
        else:
            candidates.append({"two_theta_offset": 0.02})
        for choice in background_choices:
            if choice != current_background:
                candidates.append({"background_method": choice})
                break
        for choice in amorphous_choices:
            if choice != current_amorphous:
                candidates.append({"amorphous_subtraction": choice})
                break
        return candidates

    def _ir_baseline_candidates(self, current_config: dict[str, Any]) -> list[dict[str, Any]]:
        baseline = str(current_config.get("baseline_method", "") or "").strip()
        normalization = str(current_config.get("normalization_method", "") or "").strip()
        smooth_window = int(round(self._safe_float(current_config.get("smooth_window", 7)) or 7))
        baseline_choices = [choice for choice in IR_PARAM_MAP["baseline_method"].constraint if isinstance(choice, str)]
        normalization_choices = [choice for choice in IR_PARAM_MAP["normalization_method"].constraint if isinstance(choice, str)]
        candidates: list[dict[str, Any]] = []
        for choice in baseline_choices:
            if choice != baseline:
                candidates.append({"baseline_method": choice})
                break
        for choice in normalization_choices:
            if choice != normalization:
                candidates.append({"normalization_method": choice})
                break
        if smooth_window % 2 == 0:
            smooth_window += 1
        candidates.append({"smooth_window": min(15, max(5, smooth_window + 2))})
        return candidates[:3]

    def _ir_noise_candidates(self, current_config: dict[str, Any]) -> list[dict[str, Any]]:
        smooth_window = int(round(self._safe_float(current_config.get("smooth_window", 7)) or 7))
        if smooth_window % 2 == 0:
            smooth_window += 1
        larger = min(31, smooth_window + 2)
        if larger % 2 == 0:
            larger += 1
        return [
            {"smooth_window": larger},
            {"smooth_window": min(31, larger + 2 if larger < 31 else larger)},
        ]

    def _ir_key_band_candidates(self, current_config: dict[str, Any]) -> list[dict[str, Any]]:
        fit_window = self._safe_float(current_config.get("peak_fit_window_cm1", 35.0)) or 35.0
        prominence = self._safe_float(current_config.get("peak_prominence_min", 0.015)) or 0.015
        height = self._safe_float(current_config.get("peak_height_min", 0.02)) or 0.02
        return [
            {"peak_fit_window_cm1": max(8.0, fit_window - 8.0)},
            {"peak_prominence_min": max(0.001, prominence * 0.8)},
            {"peak_height_min": max(0.001, height * 0.85)},
        ]

    def _ir_crowded_band_candidates(self, current_config: dict[str, Any]) -> list[dict[str, Any]]:
        peak_distance = self._safe_float(current_config.get("peak_distance", 12.0)) or 12.0
        lineshape = str(current_config.get("lineshape", "") or "").strip()
        choices = [choice for choice in IR_PARAM_MAP["lineshape"].constraint if isinstance(choice, str)]
        candidates: list[dict[str, Any]] = []
        candidates.append({"peak_distance": min(80.0, peak_distance + 4.0)})
        for choice in choices:
            if choice != lineshape:
                candidates.append({"lineshape": choice})
                break
        return candidates[:3]

    def _ir_weak_support_candidates(self, current_config: dict[str, Any]) -> list[dict[str, Any]]:
        height = self._safe_float(current_config.get("peak_height_min", 0.02)) or 0.02
        prominence = self._safe_float(current_config.get("peak_prominence_min", 0.015)) or 0.015
        normalization = str(current_config.get("normalization_method", "") or "").strip()
        choices = [choice for choice in IR_PARAM_MAP["normalization_method"].constraint if isinstance(choice, str)]
        candidates: list[dict[str, Any]] = [
            {"peak_height_min": max(0.001, height * 0.9)},
            {"peak_prominence_min": max(0.001, prominence * 0.85)},
        ]
        for choice in choices:
            if choice != normalization:
                candidates.append({"normalization_method": choice})
                break
        return candidates[:3]

    def _ir_band_window_candidates(self, current_config: dict[str, Any]) -> list[dict[str, Any]]:
        wn_min = self._safe_float(current_config.get("wavenumber_min", 400.0)) or 400.0
        wn_max = self._safe_float(current_config.get("wavenumber_max", 4000.0)) or 4000.0
        span = max(wn_max - wn_min, 100.0)
        step = max(25.0, min(span * 0.08, 150.0))
        return [
            {"wavenumber_min": max(350.0, wn_min - step)},
            {"wavenumber_max": min(4500.0, wn_max + step)},
        ]

    def _ir_dynamic_signal_candidates(self, current_config: dict[str, Any]) -> list[dict[str, Any]]:
        baseline = str(current_config.get("baseline_method", "") or "").strip()
        normalization = str(current_config.get("normalization_method", "") or "").strip()
        smooth_window = int(round(self._safe_float(current_config.get("smooth_window", 7)) or 7))
        candidates: list[dict[str, Any]] = []
        if baseline != "mute_zone":
            candidates.append({"baseline_method": "mute_zone"})
        if normalization != "none":
            candidates.append({"normalization_method": "none"})
        smaller = max(3, smooth_window - 2)
        if smaller % 2 == 0:
            smaller += 1
        if smaller != smooth_window:
            candidates.append({"smooth_window": smaller})
        return candidates[:3]

    def _ir_2dcos_denoise_candidates(self, current_config: dict[str, Any]) -> list[dict[str, Any]]:
        smooth_window = int(round(self._safe_float(current_config.get("smooth_window", 7)) or 7))
        exclusion = self._safe_float(current_config.get("cross_peak_exclusion_cm1", 35.0)) or 35.0
        larger = min(31, smooth_window + 2)
        if larger % 2 == 0:
            larger += 1
        return [
            {"smooth_window": larger},
            {"cross_peak_exclusion_cm1": min(80.0, exclusion + 5.0)},
        ]

    def _ir_band_tracking_candidates(self, current_config: dict[str, Any]) -> list[dict[str, Any]]:
        peak_fit_window = self._safe_float(current_config.get("peak_fit_window_cm1", 18.0)) or 18.0
        peak_distance = self._safe_float(current_config.get("peak_distance", 18.0)) or 18.0
        smooth_window = int(round(self._safe_float(current_config.get("smooth_window", 7)) or 7))
        wider = min(31, smooth_window + 2)
        if wider % 2 == 0:
            wider += 1
        tighter_fit = max(8.0, peak_fit_window - 2.0)
        tighter_distance = max(8.0, peak_distance - 2.0)
        return [
            {"smooth_window": wider},
            {"peak_fit_window_cm1": tighter_fit},
            {"peak_distance": tighter_distance},
        ]

    def _ir_cross_peak_assignment_candidates(self, current_config: dict[str, Any]) -> list[dict[str, Any]]:
        tolerance = self._safe_float(current_config.get("assignment_tolerance_cm1", 18.0)) or 18.0
        exclusion = self._safe_float(current_config.get("cross_peak_exclusion_cm1", 35.0)) or 35.0
        return [
            {"assignment_tolerance_cm1": min(30.0, tolerance + 2.0)},
            {"cross_peak_exclusion_cm1": min(80.0, exclusion + 5.0)},
            {"assignment_tolerance_cm1": max(5.0, tolerance - 2.0)},
        ]

    def _saxs_range_action_candidates(
        self,
        current_config: dict[str, Any],
        low_name: str,
        high_name: str,
        *,
        inward_first: bool,
    ) -> list[dict[str, Any]]:
        low_value = self._safe_float(current_config.get(low_name))
        high_value = self._safe_float(current_config.get(high_name))
        if high_value <= low_value:
            rule_low = SAXS_PARAM_MAP[low_name].constraint
            rule_high = SAXS_PARAM_MAP[high_name].constraint
            low_value = float(rule_low[0])
            high_value = float(rule_high[1])
        span = max(high_value - low_value, 0.04)
        step = max(0.01, min(span * 0.15, 0.08))
        inward = {
            low_name: low_value + step,
            high_name: high_value - step,
        }
        outward = {
            low_name: low_value - step,
            high_name: high_value + step,
        }
        return [inward, outward] if inward_first else [outward, inward]

    def _saxs_crop_action_candidates(self, current_config: dict[str, Any]) -> list[dict[str, Any]]:
        q_bragg_min = self._safe_float(current_config.get("q_bragg_min", 0.15))
        q_bragg_max = self._safe_float(current_config.get("q_bragg_max", 0.9))
        q_corr_min = self._safe_float(current_config.get("q_corr_min", 0.15))
        q_corr_max = self._safe_float(current_config.get("q_corr_max", 1.2))
        low_step = max(0.01, min((q_bragg_max - q_bragg_min) * 0.12, 0.06))
        corr_step = max(0.01, min((q_corr_max - q_corr_min) * 0.12, 0.08))
        return [
            {
                "q_bragg_min": q_bragg_min + low_step,
                "q_corr_min": q_corr_min + corr_step,
            },
            {
                "q_bragg_max": q_bragg_max - low_step,
                "q_corr_max": q_corr_max - corr_step,
            },
        ]

    def _saxs_idf_smoothing_candidates(self, current_config: dict[str, Any]) -> list[dict[str, Any]]:
        window = int(round(self._safe_float(current_config.get("savgol_window", 7)) or 7))
        peak_thresh = self._safe_float(current_config.get("idf_peak_rel_thresh", 0.05)) or 0.05
        valley_thresh = self._safe_float(current_config.get("idf_valley_rel_thresh", 0.05)) or 0.05
        return [
            {"savgol_window": window + 2},
            {
                "idf_peak_rel_thresh": peak_thresh * 1.2,
                "idf_valley_rel_thresh": valley_thresh * 1.2,
            },
        ]

    def _normalize_candidate_value(self, param_name: str, value: Any, param_map: dict[str, Any]) -> Any:
        rule = param_map.get(param_name)
        if rule is None:
            return value
        constraint = rule.constraint
        if constraint is None:
            if rule.value_type is bool:
                return bool(value)
            if rule.value_type is int:
                return int(round(self._safe_float(value)))
            if rule.value_type is float:
                return round(float(self._safe_float(value)), 6)
            return value
        if all(isinstance(item, str) for item in constraint):
            text = str(value or "").strip()
            if text in constraint:
                return text
            return str(constraint[0])

        lower = float(constraint[0])
        upper = float(constraint[1])
        if rule.value_type is int:
            number = int(round(self._safe_float(value)))
            number = max(int(lower), min(int(upper), number))
            if param_name == "savgol_window":
                if number % 2 == 0:
                    if number + 1 <= int(upper):
                        number += 1
                    else:
                        number -= 1
                number = max(number, 3)
            if param_name == "savgol_order":
                number = max(number, 1)
            return number

        number = self._safe_float(value)
        number = max(lower, min(upper, number))
        return round(float(number), 6)

    def _normalize_saxs_candidate_value(self, param_name: str, value: Any) -> Any:
        return self._normalize_candidate_value(param_name, value, SAXS_PARAM_MAP)

    def _candidate_values_equal(self, left: Any, right: Any) -> bool:
        if isinstance(left, str) or isinstance(right, str):
            return str(left) == str(right)
        try:
            return math.isclose(float(left), float(right), rel_tol=1e-9, abs_tol=1e-9)
        except (TypeError, ValueError):
            return left == right

    def _execute_candidate_trial(
        self,
        engine: Any,
        round_num: int,
        previous_record: RoundRecord,
        advice: dict[str, Any],
        changes: dict[str, Any],
        prompt: str,
    ) -> dict[str, Any]:
        candidate_plan = advice.get("candidate_plan", {}) if isinstance(advice.get("candidate_plan"), dict) else {}
        action_name = str(candidate_plan.get("action_name", "") or "").strip()
        if self.technique == "saxs" and action_name == "rerun_condition_recovery":
            recovery_context = candidate_plan.get("recovery_context", {})
            if not isinstance(recovery_context, dict) or not recovery_context:
                rejected = dict(advice)
                rejected["rejected"] = True
                rejected["rollback_reason"] = "No recoverable SAXS condition_context was available."
                rejected["rollback_detail"] = "Condition recovery needs a real context payload before the SAXS directory can be rescanned."
                return {
                    "status": "rejected",
                    "reason": rejected["rollback_reason"],
                    "record": None,
                    "advice": rejected,
                }

            config = self._engine_config(engine)
            if config is None or not hasattr(config, "condition_context"):
                rejected = dict(advice)
                rejected["rejected"] = True
                rejected["rollback_reason"] = "SAXS config does not expose condition_context."
                rejected["rollback_detail"] = "The current SAXS engine config cannot accept recovered condition context."
                return {
                    "status": "rejected",
                    "reason": rejected["rollback_reason"],
                    "record": None,
                    "advice": rejected,
                }

            merged_context = deepcopy(getattr(config, "condition_context", {}))
            if not isinstance(merged_context, dict):
                merged_context = {}
            for key, value in recovery_context.items():
                if key not in merged_context or merged_context[key] in (None, "", {}, []):
                    merged_context[key] = deepcopy(value)
            config.condition_context = merged_context

            data_path = str(self._resolve_data_file(self.data_file))
            try:
                run_result = engine.run_pipeline(data_path, output_dir="")
            except Exception as exc:
                rejected = dict(advice)
                rejected["rejected"] = True
                rejected["rollback_reason"] = f"engine.run_pipeline() failed: {exc}"
                rejected["rollback_detail"] = "Condition recovery could not rebuild the SAXS batch, so the trial was rolled back."
                return {
                    "status": "rejected",
                    "reason": rejected["rollback_reason"],
                    "record": None,
                    "advice": rejected,
                }

            if run_result is None:
                rejected = dict(advice)
                rejected["rejected"] = True
                rejected["rollback_reason"] = "engine.run_pipeline() returned no result"
                rejected["rollback_detail"] = "Condition recovery did not produce a usable SAXS rerun."
                return {
                    "status": "rejected",
                    "reason": rejected["rollback_reason"],
                    "record": None,
                    "advice": rejected,
                }

            engine.result.parameters = engine.get_parameters()
            candidate = self._record_round(
                engine,
                round_num,
                advice,
                before_r_squared=previous_record.r_squared,
                changes={},
                accepted=True,
                prompt=prompt,
            )
            if isinstance(candidate.llm_advice, dict):
                candidate.llm_advice["recovery_context"] = self._to_plain_value(recovery_context)

            quality_ok, quality_error = self._quality_guard(candidate)
            if not quality_ok:
                rejected = dict(candidate.llm_advice or advice)
                rejected["rejected"] = True
                rejected["rollback_reason"] = quality_error
                rejected["decision_metrics"] = self._decision_metrics(candidate, previous_record)
                rejected["rollback_detail"] = self._advice_rollback_detail(rejected)
                candidate.llm_advice = rejected
                candidate.accepted = False
                candidate.target_symptom = self._advice_target_symptom(rejected, candidate.analysis_evidence)
                candidate.rollback_detail = rejected["rollback_detail"]
                candidate.decision_summary = self._decision_summary(False, candidate.target_symptom, candidate.rollback_detail, {"objective_score": candidate.eval_score})
                return {
                    "status": "rolled_back",
                    "reason": quality_error,
                    "record": candidate,
                    "advice": rejected,
                }

            accepted, rollback_reason, decision_metrics = self._evaluate_candidate(candidate, previous_record)
            if accepted:
                return {
                    "status": "accepted",
                    "reason": "",
                    "record": candidate,
                    "advice": candidate.llm_advice if isinstance(candidate.llm_advice, dict) else dict(advice),
                }

            rejected = dict(candidate.llm_advice or advice)
            rejected["rejected"] = True
            rejected["rollback_reason"] = rollback_reason
            rejected["decision_metrics"] = decision_metrics
            rejected["rollback_detail"] = self._advice_rollback_detail(rejected)
            candidate.llm_advice = rejected
            candidate.accepted = False
            candidate.target_symptom = self._advice_target_symptom(rejected, candidate.analysis_evidence)
            candidate.rollback_detail = rejected["rollback_detail"]
            candidate.decision_summary = self._decision_summary(False, candidate.target_symptom, candidate.rollback_detail, {"objective_score": candidate.eval_score})
            return {
                "status": "rolled_back",
                "reason": rollback_reason,
                "record": candidate,
                "advice": rejected,
            }

        ok, error = apply_changes(self._engine_config(engine), changes, technique=self.technique)
        if not ok:
            rejected = dict(advice)
            rejected["rejected"] = True
            rejected["rollback_reason"] = error
            rejected["rollback_detail"] = "The proposed parameter change violates the local config constraints, so the candidate was skipped."
            return {
                "status": "rejected",
                "reason": error,
                "record": None,
                "advice": rejected,
            }

        if not engine.analyze():
            rejected = dict(advice)
            rejected["rejected"] = True
            rejected["rollback_reason"] = "engine.analyze() failed"
            rejected["rollback_detail"] = "The core analysis failed to finish, so the candidate was rolled back immediately."
            return {
                "status": "rejected",
                "reason": "engine.analyze() failed",
                "record": None,
                "advice": rejected,
            }

        engine.result.parameters = engine.get_parameters()
        candidate = self._record_round(
            engine,
            round_num,
            advice,
            before_r_squared=previous_record.r_squared,
            changes=changes,
            accepted=True,
            prompt=prompt,
        )

        quality_ok, quality_error = self._quality_guard(candidate)
        if not quality_ok:
            rejected = dict(advice)
            rejected["rejected"] = True
            rejected["rollback_reason"] = quality_error
            rejected["decision_metrics"] = self._decision_metrics(candidate, previous_record)
            rejected["rollback_detail"] = self._advice_rollback_detail(rejected)
            candidate.llm_advice = rejected
            candidate.accepted = False
            candidate.target_symptom = self._advice_target_symptom(rejected, candidate.analysis_evidence)
            candidate.rollback_detail = rejected["rollback_detail"]
            candidate.decision_summary = self._decision_summary(False, candidate.target_symptom, candidate.rollback_detail, {"objective_score": candidate.eval_score})
            return {
                "status": "rolled_back",
                "reason": quality_error,
                "record": candidate,
                "advice": rejected,
            }

        accepted, rollback_reason, decision_metrics = self._evaluate_candidate(candidate, previous_record)
        if accepted:
            return {
                "status": "accepted",
                "reason": "",
                "record": candidate,
                "advice": candidate.llm_advice if isinstance(candidate.llm_advice, dict) else dict(advice),
            }

        rejected = dict(advice)
        rejected["rejected"] = True
        rejected["rollback_reason"] = rollback_reason
        rejected["decision_metrics"] = decision_metrics
        rejected["rollback_detail"] = self._advice_rollback_detail(rejected)
        candidate.llm_advice = rejected
        candidate.accepted = False
        candidate.target_symptom = self._advice_target_symptom(rejected, candidate.analysis_evidence)
        candidate.rollback_detail = rejected["rollback_detail"]
        candidate.decision_summary = self._decision_summary(False, candidate.target_symptom, candidate.rollback_detail, {"objective_score": candidate.eval_score})
        return {
            "status": "rolled_back",
            "reason": rollback_reason,
            "record": candidate,
            "advice": rejected,
        }

    def _candidate_trial_summary(
        self,
        plan: dict[str, Any],
        status: str,
        previous_record: RoundRecord,
        record: RoundRecord | None = None,
        reason: str = "",
    ) -> dict[str, Any]:
        summary = {
            "action_name": str(plan.get("action_name", "") or "").strip(),
            "label": str(plan.get("label", "") or "").strip(),
            "target_symptom": str(plan.get("target_symptom", "") or "").strip(),
            "changes": self._to_plain_value(plan.get("changes", {})),
            "status": status,
            "reason": reason,
            "expected_evidence_change": str(plan.get("expected_evidence_change", "") or "").strip(),
        }
        if record is None:
            return summary

        rollback_reason = ""
        if isinstance(record.llm_advice, dict):
            rollback_reason = str(record.llm_advice.get("rollback_reason", "") or "").strip()
        summary.update(
            {
                "accepted": bool(record.accepted),
                "r_squared": record.r_squared,
                "objective_score": record.eval_score,
                "r_squared_delta": record.r_squared - previous_record.r_squared,
                "objective_delta": record.eval_score - previous_record.eval_score,
                "rollback_reason": rollback_reason,
                "decision_summary": record.decision_summary,
            }
        )
        return self._to_plain_value(summary)

    def _candidate_rank(self, record: RoundRecord) -> tuple[float, float, float]:
        change_count = len(record.changes or {}) if isinstance(record.changes, dict) else 0
        return (record.eval_score, record.r_squared, -float(change_count))

    def _restore_best_with_refresh(self, engine: Any) -> None:
        self._restore_best(engine)
        if engine is None or self._best_record is None:
            return
        try:
            if engine.analyze():
                engine.result.parameters = engine.get_parameters()
        except Exception:
            logger.warning("Failed to refresh the best engine state after rollback.", exc_info=True)

    def _run_saxs_candidate_round(
        self,
        engine: Any,
        round_num: int,
        advice: dict[str, Any],
        previous_record: RoundRecord,
        candidate_plans: list[dict[str, Any]],
        prompt: str,
    ) -> dict[str, Any]:
        trial_summaries: list[dict[str, Any]] = []
        accepted_trials: list[dict[str, Any]] = []
        failed_trials: list[dict[str, Any]] = []
        attempted_execution = False

        for index, plan in enumerate(candidate_plans, start=1):
            plan_dict = dict(plan or {})
            plan_dict["candidate_index"] = index
            plan_dict["candidate_total"] = len(candidate_plans)
            executable = bool(plan_dict.get("executable", False))
            if not executable:
                trial_summaries.append(
                    self._candidate_trial_summary(
                        plan_dict,
                        "skipped",
                        previous_record,
                        reason=str(plan_dict.get("skip_reason", "") or "").strip(),
                    )
                )
                continue

            attempted_execution = True
            self._restore_best(engine)
            trial_advice = dict(advice)
            trial_advice["changes"] = dict(plan_dict.get("changes", {}))
            trial_advice["target_symptom"] = str(plan_dict.get("target_symptom", "") or "").strip() or str(advice.get("target_symptom", "") or "").strip()
            trial_advice["candidate_plan"] = {
                "action_name": str(plan_dict.get("action_name", "") or "").strip(),
                "label": str(plan_dict.get("label", "") or "").strip(),
                "reason": str(plan_dict.get("reason", "") or "").strip(),
                "expected_evidence_change": str(plan_dict.get("expected_evidence_change", "") or "").strip(),
                "changes": self._to_plain_value(plan_dict.get("changes", {})),
                "recovery_context": self._to_plain_value(plan_dict.get("recovery_context", {})),
            }
            if trial_advice["candidate_plan"]["action_name"] != "advisor_changes":
                trial_advice["recommended_actions"] = [
                    {
                        "name": trial_advice["candidate_plan"]["action_name"],
                        "reason": trial_advice["candidate_plan"]["reason"],
                        "expected_evidence_change": trial_advice["candidate_plan"]["expected_evidence_change"],
                    }
                ]

            outcome = self._execute_candidate_trial(
                engine,
                round_num,
                previous_record,
                trial_advice,
                dict(plan_dict.get("changes", {})),
                prompt,
            )
            trial_record = outcome.get("record")
            reason = str(outcome.get("reason", "") or "").strip()
            trial_summaries.append(
                self._candidate_trial_summary(
                    plan_dict,
                    str(outcome.get("status", "rejected") or "rejected"),
                    previous_record,
                    record=trial_record if isinstance(trial_record, RoundRecord) else None,
                    reason=reason,
                )
            )
            if isinstance(trial_record, RoundRecord) and str(outcome.get("status")) == "accepted":
                accepted_trials.append({"plan": plan_dict, "record": trial_record})
            elif isinstance(trial_record, RoundRecord):
                failed_trials.append({"plan": plan_dict, "record": trial_record})
            else:
                failed_trials.append({"plan": plan_dict, "advice": outcome.get("advice", {}), "reason": reason})

        if accepted_trials:
            best_trial = max(accepted_trials, key=lambda item: self._candidate_rank(item["record"]))
            best_plan = best_trial["plan"]
            best_record = best_trial["record"]
            selected_advice = dict(best_record.llm_advice or advice)
            selected_advice["candidate_trials"] = self._to_plain_value(trial_summaries)
            selected_advice["selected_candidate"] = self._to_plain_value(
                {
                    "action_name": str(best_plan.get("action_name", "") or "").strip(),
                    "label": str(best_plan.get("label", "") or "").strip(),
                    "changes": best_plan.get("changes", {}),
                    "target_symptom": str(best_plan.get("target_symptom", "") or "").strip(),
                    "objective_score": best_record.eval_score,
                    "r_squared": best_record.r_squared,
                }
            )
            best_record.llm_advice = selected_advice
            best_record.target_symptom = self._advice_target_symptom(selected_advice, best_record.analysis_evidence)
            best_record.rollback_detail = self._advice_rollback_detail(selected_advice)
            best_record.decision_summary = self._decision_summary(True, best_record.target_symptom, best_record.rollback_detail, {"objective_score": best_record.eval_score})

            self._restore_best(engine)
            ok, error = apply_changes(self._engine_config(engine), dict(best_plan.get("changes", {})), technique=self.technique)
            if ok and engine.analyze():
                engine.result.parameters = engine.get_parameters()
            else:
                logger.warning(
                    "Failed to replay the accepted %s candidate; restoring the previous best state. error=%s",
                    self.technique.upper(),
                    error or "engine.analyze() failed",
                )
                self._restore_best_with_refresh(engine)

            self._best_r_squared = best_record.r_squared
            self._best_eval_score = best_record.eval_score
            self._best_record = best_record
            self._best_config = deepcopy(self._engine_config(engine))
            self._best_output = dict(best_record.output_parameters)
            return {
                "record": best_record,
                "status": "improved",
                "changes": dict(best_plan.get("changes", {})),
            }

        rejected_reason = ""
        rejected_detail = ""
        rejected_changes: dict[str, Any] = {}
        if failed_trials:
            best_failed = max(
                failed_trials,
                key=lambda item: self._candidate_rank(item["record"]) if isinstance(item.get("record"), RoundRecord) else (-math.inf, -math.inf, 0.0),
            )
            failed_record = best_failed.get("record")
            if isinstance(failed_record, RoundRecord):
                final_advice = dict(failed_record.llm_advice or advice)
                final_advice["candidate_trials"] = self._to_plain_value(trial_summaries)
                failed_record.llm_advice = final_advice
                failed_record.accepted = False
                failed_record.target_symptom = self._advice_target_symptom(final_advice, failed_record.analysis_evidence)
                failed_record.rollback_detail = self._advice_rollback_detail(final_advice)
                failed_record.decision_summary = self._decision_summary(False, failed_record.target_symptom, failed_record.rollback_detail, {"objective_score": failed_record.eval_score})
                if attempted_execution:
                    self._restore_best_with_refresh(engine)
                return {
                    "record": failed_record,
                    "status": "rolled_back",
                    "changes": dict(failed_record.changes or {}),
                }
            rejected_reason = str(best_failed.get("reason", "") or "").strip()
            rejected_changes = dict(best_failed.get("plan", {}).get("changes", {}) or {})

        if not rejected_reason:
            for item in trial_summaries:
                if not isinstance(item, dict):
                    continue
                rejected_reason = str(item.get("reason", "") or item.get("rollback_reason", "") or "").strip()
                if rejected_reason:
                    break
        if not rejected_reason:
            rejected_reason = f"No executable {self.technique.upper()} candidate could be produced from the advisor action list."
        rejected_detail = f"The current action list did not yield a guarded {self.technique.upper()} re-run candidate that improved the objective score."

        rejected_advice = dict(advice)
        rejected_advice["rejected"] = True
        rejected_advice["rollback_reason"] = rejected_reason
        rejected_advice["rollback_detail"] = rejected_detail
        rejected_advice["candidate_trials"] = self._to_plain_value(trial_summaries)
        record = self._record_round(
            engine,
            round_num,
            rejected_advice,
            before_r_squared=previous_record.r_squared,
            changes=rejected_changes,
            accepted=False,
            prompt=prompt,
        )
        if attempted_execution:
            self._restore_best_with_refresh(engine)
        return {
            "record": record,
            "status": "rejected",
            "changes": rejected_changes,
        }

    def _final_report(self, data_path: Path, converged: bool, convergence_reason: str) -> dict[str, Any]:
        best_config = self._config_to_dict(self._best_config)
        report = {
            "technique": self.technique,
            "submodule": self._public_submodule(),
            "polymer_name": self.polymer_name,
            "data_file": str(data_path),
            "rounds": len(self.history) - 1,
            "converged": converged,
            "convergence_reason": convergence_reason,
            "baseline_r_squared": self._baseline_r_squared,
            "best_r_squared": self._best_r_squared,
            "baseline_eval_score": self._baseline_eval_score,
            "best_eval_score": self._best_eval_score,
            "improvement": {
                "r_squared_abs": self._best_r_squared - self._baseline_r_squared,
                "eval_score_abs": self._best_eval_score - self._baseline_eval_score,
            },
            "benchmark_summary": self._benchmark_summary(),
            "best_config": best_config,
            "best_output_parameters": self._to_plain_value(self._best_output),
            "history": [self._to_plain_value(asdict(record)) for record in self.history],
        }
        return self._to_plain_value(report)

    def _benchmark_summary(self) -> dict[str, Any]:
        candidate_history = [record for record in self.history if record.round_num > 0]
        if not candidate_history:
            return {
                "rounds": 0,
                "accepted_rounds": 0,
                "rejected_rounds": 0,
                "acceptance_rate": 0.0,
                "rollback_rate": 0.0,
                "objective_gain_rounds": 0,
                "objective_loss_rounds": 0,
                "objective_gain_rate": 0.0,
                "objective_delta_average": 0.0,
                "rollback_reasons": {},
                "constraint_hits": {
                    "rounds": 0,
                    "hard_fail_rounds": 0,
                    "soft_warn_rounds": 0,
                    "evidence_only_rounds": 0,
                    "hit_rate": 0.0,
                },
                "symptom_hits": {
                    "rounds": 0,
                    "hit_rounds": 0,
                    "hit_rate": 0.0,
                },
                "joint_context": {
                    "rounds": 0,
                    "penalty_total": 0.0,
                },
            }

        accepted_rounds = 0
        rejected_rounds = 0
        objective_gains = 0
        objective_losses = 0
        objective_deltas: list[float] = []
        rollback_reasons: dict[str, int] = {}
        constraint_rounds = 0
        hard_fail_rounds = 0
        soft_warn_rounds = 0
        evidence_only_rounds = 0
        symptom_hit_rounds = 0
        joint_context_rounds = 0
        joint_context_penalty_total = 0.0

        for index, record in enumerate(candidate_history, start=1):
            previous = self.history[index - 1] if index - 1 < len(self.history) else None
            if record.accepted:
                accepted_rounds += 1
            else:
                rejected_rounds += 1
                advice = record.llm_advice if isinstance(record.llm_advice, dict) else {}
                rollback_reason = str(advice.get("rollback_reason") or "").strip()
                if rollback_reason:
                    rollback_reasons[rollback_reason] = rollback_reasons.get(rollback_reason, 0) + 1

            if previous is not None:
                delta = record.eval_score - previous.eval_score
                objective_deltas.append(delta)
                if delta > max(0.0, self._objective_gain_threshold() - 0.001):
                    objective_gains += 1
                elif delta < -self._component_drop_tolerance():
                    objective_losses += 1

                if self._round_symptom_hit(record, previous):
                    symptom_hit_rounds += 1

            analysis_evidence = record.analysis_evidence if isinstance(record.analysis_evidence, dict) else {}
            constraint_summary = analysis_evidence.get("constraint_summary", {}) if isinstance(analysis_evidence, dict) else {}
            if isinstance(constraint_summary, dict):
                triggered_counts = constraint_summary.get("triggered_counts", {})
                if isinstance(triggered_counts, dict):
                    hard_fail = int(triggered_counts.get("hard_fail", 0) or 0)
                    soft_warn = int(triggered_counts.get("soft_warn", 0) or 0)
                    evidence_only = int(triggered_counts.get("evidence_only", 0) or 0)
                    if hard_fail or soft_warn or evidence_only:
                        constraint_rounds += 1
                    if hard_fail:
                        hard_fail_rounds += 1
                    if soft_warn:
                        soft_warn_rounds += 1
                    if evidence_only:
                        evidence_only_rounds += 1

            score_snapshot = self._score_snapshot(record.output_parameters, record.residuals_pattern, analysis_evidence)
            joint_context = score_snapshot.get("joint_ai_context", {})
            if isinstance(joint_context, dict) and joint_context:
                joint_context_rounds += 1
                joint_context_penalty_total += self._safe_float(score_snapshot.get("joint_context_penalty", 0.0)) or 0.0

        candidate_rounds = len(candidate_history)
        return {
            "rounds": candidate_rounds,
            "accepted_rounds": accepted_rounds,
            "rejected_rounds": rejected_rounds,
            "acceptance_rate": accepted_rounds / candidate_rounds,
            "rollback_rate": rejected_rounds / candidate_rounds,
            "objective_gain_rounds": objective_gains,
            "objective_loss_rounds": objective_losses,
            "objective_gain_rate": objective_gains / candidate_rounds,
            "objective_delta_average": self._mean_or_none(objective_deltas) or 0.0,
            "rollback_reasons": rollback_reasons,
            "constraint_hits": {
                "rounds": constraint_rounds,
                "hard_fail_rounds": hard_fail_rounds,
                "soft_warn_rounds": soft_warn_rounds,
                "evidence_only_rounds": evidence_only_rounds,
                "hit_rate": constraint_rounds / candidate_rounds,
            },
            "symptom_hits": {
                "rounds": candidate_rounds,
                "hit_rounds": symptom_hit_rounds,
                "hit_rate": symptom_hit_rounds / candidate_rounds,
            },
            "joint_context": {
                "rounds": joint_context_rounds,
                "penalty_total": joint_context_penalty_total,
            },
        }

    def _round_symptom_hit(self, record: RoundRecord, previous_record: RoundRecord | None) -> bool:
        if previous_record is None or not isinstance(record.changes, dict) or not record.changes:
            return False

        change_keys = {str(name).strip().lower() for name in record.changes.keys() if str(name).strip()}
        if not change_keys:
            return False

        target_keys = self._symptom_target_params(record.analysis_evidence)
        if not target_keys:
            return False

        if not (change_keys & target_keys):
            return False

        delta = record.eval_score - previous_record.eval_score
        if delta > max(0.0, self._objective_gain_threshold() - 0.001):
            return True
        return (record.r_squared - previous_record.r_squared) > self._r_squared_drop_tolerance()

    def _symptom_target_params(self, analysis_evidence: dict[str, Any]) -> set[str]:
        targets: set[str] = set()
        if isinstance(analysis_evidence, dict):
            structured = analysis_evidence.get("symptoms", [])
            if isinstance(structured, list):
                for symptom in structured:
                    if not isinstance(symptom, dict):
                        continue
                    for item in symptom.get("target_params", []):
                        param = str(item or "").strip().lower()
                        if param and " " not in param and len(param) <= 40:
                            targets.add(param)

            symptoms = analysis_evidence.get("actionable_symptoms", [])
            if isinstance(symptoms, list):
                for symptom in symptoms:
                    text = str(symptom or "").strip().lower()
                    if not text:
                        continue
                    if "->" in text:
                        text = text.split("->", 1)[1]
                    if "expected evidence change:" in text:
                        text = text.split("expected evidence change:", 1)[0]
                    for piece in re.split(r"[/,;|]", text):
                        param = piece.strip().strip(".")
                        if param and " " not in param and len(param) <= 40:
                            targets.add(param)

        focus = self._joint_tuning_focus()
        targets.update(name.lower() for name in focus.keys())
        return targets

    def _can_converge_on_small_delta(self, record: RoundRecord, round_num: int) -> bool:
        if round_num >= 3:
            return True
        if self.technique not in {"waxs", "dsc"}:
            return True
        section = "dsc" if self.technique == "dsc" else "waxs"
        knowledge = self.polymer_knowledge.get(section, {}) if isinstance(self.polymer_knowledge, dict) else {}
        xc_range = knowledge.get("xc_range")
        if not (isinstance(xc_range, list) and len(xc_range) == 2):
            return True
        current_xc = record.output_parameters.get("Xc_pct")
        try:
            value = float(current_xc)
            low, high = float(xc_range[0]), float(xc_range[1])
        except (TypeError, ValueError):
            return True
        return low <= value <= high

    def _can_converge_after_rollback(self, round_num: int) -> bool:
        if round_num < 3:
            return False
        return (self._best_r_squared - self._baseline_r_squared) >= 0.001

    def _quality_guard(self, candidate: RoundRecord) -> tuple[bool, str]:
        if self.technique == "dsc":
            quality = self._safe_float(candidate.output_parameters.get("quality_score", 1.0))
            if quality < 0.5:
                return False, f"quality_score below PHYS guard threshold: {quality:.3f}"
        elif self.technique == "saxs":
            quality = self._safe_float(candidate.output_parameters.get("quality_score", 1.0))
            if quality < 0.05:
                return False, f"quality_score below PHYS guard threshold: {quality:.3f}"
        elif self.technique == "ir":
            quality = self._safe_float(candidate.output_parameters.get("quality_score", 1.0))
            if quality < 0.05:
                return False, f"quality_score below IR assignment guard threshold: {quality:.3f}"
        elif self.technique == "nmr":
            quality = self._safe_float(candidate.output_parameters.get("quality_score", 1.0))
            if quality < -10.0:
                return False, f"quality_score below NMR fit guard threshold: {quality:.3f}"
        return True, ""

    def _decision_metrics(self, candidate: RoundRecord, previous_record: RoundRecord) -> dict[str, Any]:
        return {
            "candidate": self._score_snapshot(candidate.output_parameters, candidate.residuals_pattern, candidate.analysis_evidence),
            "previous": self._score_snapshot(previous_record.output_parameters, previous_record.residuals_pattern, previous_record.analysis_evidence),
        }

    def _evaluate_candidate(
        self,
        candidate: RoundRecord,
        previous_record: RoundRecord,
    ) -> tuple[bool, str, dict[str, Any]]:
        candidate_metrics = self._score_snapshot(candidate.output_parameters, candidate.residuals_pattern, candidate.analysis_evidence)
        previous_metrics = self._score_snapshot(previous_record.output_parameters, previous_record.residuals_pattern, previous_record.analysis_evidence)
        is_waxs_temperature = self.technique == "waxs" and self._submodule_id() in {"waxs.temperature", "waxs.in_situ_temp"}
        decision_metrics = {
            "candidate": candidate_metrics,
            "previous": previous_metrics,
            "delta": {
                key: candidate_metrics[key] - previous_metrics[key]
                for key in (
                    "objective_score",
                    "r_squared",
                    "quality_score",
                    "physical_score",
                    "validation_score",
                    "residual_score",
                    "stability_score",
                    "parameter_stability_score",
                    "method_agreement_score",
                    "batch_continuity_score",
                )
            },
        }
        if self.technique == "waxs":
            decision_metrics["delta"].update(
                {
                    key: candidate_metrics[key] - previous_metrics[key]
                    for key in (
                        "peak_support_score",
                        "background_stability_score",
                        "phase_support_score",
                        "size_support_score",
                        "waxs_support_score",
                    )
                }
            )
        if is_waxs_temperature:
            decision_metrics["delta"].update(
                {
                    key: candidate_metrics[key] - previous_metrics[key]
                    for key in (
                        "transition_support_score",
                        "transition_candidate_count",
                        "temperature_axis_confidence",
                        "peak_family_continuity_score",
                        "Xc_trend_support_score",
                        "D_trend_support_score",
                        "frame_low_conf_count",
                        "peak_family_identity_swap_count",
                    )
                }
            )
        if self.technique == "ir":
            decision_metrics["delta"].update(
                {
                    key: candidate_metrics[key] - previous_metrics[key]
                    for key in (
                        "peak_count",
                        "assigned_peak_count",
                        "reference_band_hit_count",
                        "reference_band_missing_count",
                        "assignment_confidence_score",
                        "key_band_support_score",
                        "baseline_stability_score",
                        "peak_coverage_score",
                        "ir_support_score",
                        "triggered_constraint_count",
                        "unassigned_key_band_count",
                    )
                }
            )
        if self.technique == "dsc":
            decision_metrics["delta"].update(
                {
                    key: candidate_metrics[key] - previous_metrics[key]
                    for key in (
                        "event_support_score",
                        "dsc_baseline_stability_score",
                        "thermodynamic_consistency_score",
                        "crystallinity_support_score",
                        "dsc_support_score",
                        "dsc_scan_r_squared_median",
                        "dsc_scan_r_squared_spread",
                        "dsc_supported_event_fraction",
                        "dsc_triggered_constraint_count",
                        "dsc_validation_passed_count",
                    )
                }
            )

        hard_fail_names = candidate_metrics.get("hard_fail_names", [])
        if hard_fail_names:
            return False, f"new_hard_fail_introduced:{','.join(hard_fail_names)}", decision_metrics

        regression_reason = self._regression_reason(candidate_metrics, previous_metrics)
        if regression_reason:
            return False, regression_reason, decision_metrics

        stability_reason = self._stability_regression_reason(candidate_metrics, previous_metrics)
        if stability_reason:
            return False, stability_reason, decision_metrics

        low_q_reason = self._saxs_low_q_priority_reason(candidate_metrics, previous_metrics, candidate, previous_record)
        if low_q_reason:
            return False, low_q_reason, decision_metrics

        objective_delta = candidate_metrics["objective_score"] - previous_metrics["objective_score"]
        r_squared_delta = candidate_metrics["r_squared"] - previous_metrics["r_squared"]

        if objective_delta <= max(0.0, self._objective_gain_threshold() - 0.001):
            return False, "no_meaningful_gain", decision_metrics

        if r_squared_delta < -self._r_squared_drop_tolerance():
            return False, "fit_score_dropped", decision_metrics

        return True, "", decision_metrics

    def _saxs_low_q_priority_reason(
        self,
        candidate_metrics: dict[str, Any],
        previous_metrics: dict[str, Any],
        candidate: RoundRecord,
        previous_record: RoundRecord,
    ) -> str:
        if self.technique != "saxs":
            return ""

        previous_symptoms = set(previous_record.symptom_names or [])
        candidate_symptoms = set(candidate.symptom_names or [])
        if not (previous_symptoms & SAXS_LOW_Q_PRIORITY_SYMPTOMS):
            return ""

        candidate_changes = set((candidate.changes or {}).keys()) if isinstance(candidate.changes, dict) else set()
        low_q_param_names = {
            "q_bragg_min",
            "q_bragg_max",
            "q_corr_min",
            "q_corr_max",
            "savgol_window",
            "savgol_order",
            "idf_peak_rel_thresh",
            "idf_valley_rel_thresh",
        }
        touched_low_q_path = bool(candidate_changes & low_q_param_names)
        low_q_problem_names = {
            "beamstop_or_low_q_contamination",
            "low_q_void_dominant",
            "strain_void_lamellar_conflict",
            "lamellar_anchor_lost_under_strain",
            "qstar_rel_without_lamellar_support",
            "orientation_shift_breaks_lamellar_comparison",
        }

        if (
            previous_symptoms & low_q_problem_names
            and candidate_symptoms & low_q_problem_names
            and not touched_low_q_path
        ):
            return "low_q_contamination_unresolved"

        if (
            "temperature_calibration_fallback_active" in previous_symptoms
            and (
                "batch_summary_conflicts_with_frame_evidence" in previous_symptoms
                or "thickness_chain_unreliable" in previous_symptoms
            )
            and (
                "temperature_calibration_fallback_active" in candidate_symptoms
                or "batch_summary_conflicts_with_frame_evidence" in candidate_symptoms
                or "thickness_chain_unreliable" in candidate_symptoms
            )
            and not touched_low_q_path
        ):
            return "fallback_still_dominant"

        prev_validation = self._safe_float(previous_metrics.get("validation_score", 0.0))
        cand_validation = self._safe_float(candidate_metrics.get("validation_score", 0.0))
        if prev_validation - cand_validation > 0.02:
            return "low_q_contamination_unresolved"

        return ""

    def _stability_regression_reason(self, candidate_metrics: dict[str, Any], previous_metrics: dict[str, Any]) -> str:
        if self.technique != "saxs":
            return ""

        candidate_strain_status = str(candidate_metrics.get("strain_reliability_status", "") or "").strip().lower()
        previous_strain_status = str(previous_metrics.get("strain_reliability_status", "") or "").strip().lower()
        if previous_strain_status == "usable" and candidate_strain_status in {"low_confidence", "diagnostic_only"}:
            return "strain_reliability_degraded"

        candidate_phase_ambiguous = self._safe_float(candidate_metrics.get("phase_ambiguous_frame_count", 0))
        previous_phase_ambiguous = self._safe_float(previous_metrics.get("phase_ambiguous_frame_count", 0))
        if candidate_phase_ambiguous > previous_phase_ambiguous and candidate_phase_ambiguous > 0:
            return "phase_ambiguity_increased"

        candidate_void_dominant = self._safe_float(candidate_metrics.get("void_dominant_frame_count", 0))
        previous_void_dominant = self._safe_float(previous_metrics.get("void_dominant_frame_count", 0))
        if candidate_void_dominant > previous_void_dominant and candidate_void_dominant > 0:
            return "void_dominance_increased"

        candidate_paper = bool(candidate_metrics.get("paper_conclusion_candidate"))
        previous_paper = bool(previous_metrics.get("paper_conclusion_candidate"))
        if previous_paper and not candidate_paper:
            return "paper_candidate_lost"

        candidate_fallback = self._safe_float(candidate_metrics.get("fallback_ratio", 0.0))
        previous_fallback = self._safe_float(previous_metrics.get("fallback_ratio", 0.0))
        if previous_fallback >= 0.4 and candidate_fallback - previous_fallback > 0.08:
            return "fallback_still_dominant"

        candidate_gap = self._safe_float(candidate_metrics.get("raw_vs_calibrated_gap", 0.0))
        previous_gap = self._safe_float(previous_metrics.get("raw_vs_calibrated_gap", 0.0))
        if previous_gap > 0.0 and candidate_gap - previous_gap > 0.035:
            return "raw_calibrated_conflict_worsened"

        candidate_thickness_risk = self._safe_float(candidate_metrics.get("thickness_chain_risk", 0.0))
        previous_thickness_risk = self._safe_float(previous_metrics.get("thickness_chain_risk", 0.0))
        if candidate_thickness_risk >= 0.55 and candidate_thickness_risk - previous_thickness_risk > 0.08:
            return "thickness_chain_still_unreliable"

        candidate_batch = self._safe_float(candidate_metrics.get("batch_continuity_score", 1.0))
        previous_batch = self._safe_float(previous_metrics.get("batch_continuity_score", 1.0))
        if previous_batch - candidate_batch > 0.08:
            return "condition_continuity_worsened"

        candidate_method = self._safe_float(candidate_metrics.get("method_agreement_score", 1.0))
        previous_method = self._safe_float(previous_metrics.get("method_agreement_score", 1.0))
        if previous_method - candidate_method > 0.12:
            return "structure_jump_too_large"

        candidate_stability = self._safe_float(candidate_metrics.get("stability_score", 1.0))
        previous_stability = self._safe_float(previous_metrics.get("stability_score", 1.0))
        if previous_stability - candidate_stability > 0.06:
            return "stability_score_dropped"

        candidate_flags = {str(item).strip() for item in candidate_metrics.get("stability_flags", []) if str(item).strip()}
        if "stability_low" in candidate_flags and candidate_stability < 0.60:
            return "symptom_unresolved"

        return ""

    def _score_snapshot(
        self,
        output: dict[str, Any],
        residuals_pattern: dict[str, Any],
        analysis_evidence: dict[str, Any],
    ) -> dict[str, Any]:
        output = dict(output or {})
        residuals_pattern = dict(residuals_pattern or {})
        analysis_evidence = dict(analysis_evidence or {})

        fit_score = self._safe_float(output.get("r_squared", 0.0))
        quality_score = output.get("quality_score")
        if quality_score is None and isinstance(analysis_evidence.get("fit_evidence"), dict):
            quality_score = analysis_evidence["fit_evidence"].get("quality_score")
        quality_score = self._safe_float(quality_score if quality_score is not None else fit_score)

        quality_flag = self._first_text(analysis_evidence.get("physical_evidence", {}), output, ("quality_flag",))
        validation_summary = self._first_text(analysis_evidence.get("physical_evidence", {}), output, ("validation_summary",))

        constraint_summary = analysis_evidence.get("constraint_summary", {})
        constraints = analysis_evidence.get("constraints", [])
        hard_fail_names: list[str] = []
        soft_warn_count = 0
        evidence_only_count = 0
        if isinstance(constraints, list):
            for item in constraints:
                if not isinstance(item, dict) or not item.get("triggered"):
                    continue
                kind = str(item.get("kind", "")).strip()
                name = str(item.get("name", "")).strip()
                if kind == "hard_fail" and name:
                    hard_fail_names.append(name)
                elif kind == "soft_warn":
                    soft_warn_count += 1
                elif kind == "evidence_only":
                    evidence_only_count += 1
        if isinstance(constraint_summary, dict):
            triggered_names = constraint_summary.get("triggered_names", {})
            if isinstance(triggered_names, dict):
                summary_hard = [
                    str(item).strip()
                    for item in triggered_names.get("hard_fail", [])
                    if str(item).strip()
                ]
                summary_soft = [
                    str(item).strip()
                    for item in triggered_names.get("soft_warn", [])
                    if str(item).strip()
                ]
                summary_evidence = [
                    str(item).strip()
                    for item in triggered_names.get("evidence_only", [])
                    if str(item).strip()
                ]
                if not hard_fail_names and summary_hard:
                    hard_fail_names.extend(summary_hard)
                soft_warn_count = max(soft_warn_count, len(summary_soft))
                evidence_only_count = max(evidence_only_count, len(summary_evidence))
            summary_status = str(constraint_summary.get("status", "") or "").strip().lower()
            if summary_status == "hard_fail" and not hard_fail_names:
                hard_fail_names.append("constraint_summary:hard_fail")
            elif summary_status == "soft_warn" and soft_warn_count == 0:
                soft_warn_count = 1
            elif summary_status == "evidence_only" and evidence_only_count == 0:
                evidence_only_count = 1

        physical_score = 1.0
        if quality_flag:
            upper = quality_flag.upper()
            if any(token in upper for token in ("ERROR", "FAIL", "INVALID")):
                physical_score -= 0.24
            elif any(token in upper for token in ("WARN", "LOW", "SKIP")):
                physical_score -= 0.10
            else:
                physical_score -= 0.05
        if validation_summary and validation_summary != "All checks passed":
            upper = validation_summary.upper()
            if any(token in upper for token in ("ERROR", "FAIL", "INVALID")):
                physical_score -= 0.18
            elif any(token in upper for token in ("WARN", "LOW", "SKIP")):
                physical_score -= 0.08
            else:
                physical_score -= 0.05
        physical_score -= 0.05 * min(soft_warn_count, 3)
        physical_score -= 0.02 * min(evidence_only_count, 3)
        physical_score = max(0.0, min(1.0, physical_score))

        validation_score = 1.0
        cross_validation = analysis_evidence.get("cross_validation", {})
        if isinstance(cross_validation, dict):
            total_checks = 0
            passed_checks = 0
            warn_checks = 0
            error_checks = 0

            def visit(node: Any) -> None:
                nonlocal total_checks, passed_checks, warn_checks, error_checks
                if isinstance(node, dict):
                    if "passed" in node:
                        total_checks += 1
                        if bool(node.get("passed")):
                            passed_checks += 1
                        severity = str(node.get("severity", "")).upper()
                        if severity == "WARN":
                            warn_checks += 1
                        elif severity == "ERROR":
                            error_checks += 1
                    else:
                        for value in node.values():
                            visit(value)
                elif isinstance(node, list):
                    for value in node:
                        visit(value)

            visit(cross_validation)
            if total_checks > 0:
                validation_score = passed_checks / total_checks
                validation_score -= 0.08 * min(warn_checks, 3)
                validation_score -= 0.16 * min(error_checks, 3)
        if validation_summary and validation_summary != "All checks passed":
            upper = validation_summary.upper()
            if any(token in upper for token in ("ERROR", "FAIL", "INVALID")):
                validation_score -= 0.10
            elif any(token in upper for token in ("WARN", "LOW", "SKIP")):
                validation_score -= 0.05

        joint_ai_context = self._joint_ai_context()
        joint_penalty = 0.0
        if joint_ai_context:
            issue_count = self._safe_float(joint_ai_context.get("issue_count"))
            warning_count = self._safe_float(joint_ai_context.get("warning_count"))
            error_count = self._safe_float(joint_ai_context.get("error_count"))
            issue_families = joint_ai_context.get("issue_families")

            if math.isfinite(issue_count) and issue_count > 0:
                validation_score -= 0.02 * min(issue_count, 4.0)
                joint_penalty += 0.004 * min(issue_count, 5.0)
            if math.isfinite(warning_count) and warning_count > 0:
                validation_score -= 0.01 * min(warning_count, 3.0)
            if math.isfinite(error_count) and error_count > 0:
                validation_score -= 0.04 * min(error_count, 3.0)
                joint_penalty += 0.008 * min(error_count, 3.0)

            families = set()
            if isinstance(issue_families, list):
                families = {str(item).strip().lower() for item in issue_families if str(item).strip()}
            if "phi_c inconsistency" in families:
                validation_score -= 0.03
                joint_penalty += 0.004
            if "tm bidirectional gap" in families:
                validation_score -= 0.03
                joint_penalty += 0.004
            if "l consistency unstable" in families:
                validation_score -= 0.025
                joint_penalty += 0.003
        validation_score = max(0.0, min(1.0, validation_score))

        residual_score = self._residual_score(residuals_pattern)
        stability_snapshot = self._stability_snapshot(output, analysis_evidence)
        stability_score = stability_snapshot["stability_score"]
        waxs_support_snapshot = self._waxs_support_snapshot(output, residuals_pattern, analysis_evidence)
        dsc_support_snapshot = self._dsc_support_snapshot(output, analysis_evidence)
        ir_support_snapshot = self._ir_support_snapshot(output, analysis_evidence)
        saxs_evidence_snapshot = self._saxs_evidence_snapshot(output, analysis_evidence)
        is_waxs_temperature = self.technique == "waxs" and self._submodule_id() in {"waxs.temperature", "waxs.in_situ_temp"}

        if self.technique == "saxs":
            objective_score = (
                0.37 * fit_score
                + 0.22 * quality_score
                + 0.14 * physical_score
                + 0.08 * validation_score
                + 0.07 * residual_score
                + 0.12 * stability_score
            )
        elif self.technique == "waxs":
            transition_support_score = self._safe_float(output.get("transition_support_score", 0.0)) if is_waxs_temperature else 0.0
            objective_score = (
                0.38 * fit_score
                + 0.16 * quality_score
                + 0.10 * physical_score
                + 0.07 * validation_score
                + 0.05 * residual_score
                + 0.08 * stability_score
                + 0.08 * waxs_support_snapshot["waxs_support_score"]
                + (0.08 * transition_support_score if is_waxs_temperature else 0.0)
            )
        elif self.technique == "ir":
            objective_score = (
                0.34 * fit_score
                + 0.18 * quality_score
                + 0.12 * physical_score
                + 0.08 * validation_score
                + 0.08 * residual_score
                + 0.20 * ir_support_snapshot["ir_support_score"]
            )
        elif self.technique == "dsc":
            stability_score = dsc_support_snapshot["baseline_stability_score"]
            objective_score = (
                0.34 * fit_score
                + 0.18 * quality_score
                + 0.14 * physical_score
                + 0.10 * validation_score
                + 0.10 * residual_score
                + 0.14 * dsc_support_snapshot["dsc_support_score"]
            )
        else:
            objective_score = (
                0.42 * fit_score
                + 0.24 * quality_score
                + 0.16 * physical_score
                + 0.09 * validation_score
                + 0.09 * residual_score
            )
        if joint_penalty > 0:
            objective_score -= joint_penalty
            objective_score = max(0.0, min(1.0, objective_score))

        return {
            "r_squared": fit_score,
            "fit_score": fit_score,
            "quality_score": quality_score,
            "physical_score": physical_score,
            "validation_score": validation_score,
            "residual_score": residual_score,
            "stability_score": stability_score,
            "parameter_stability_score": stability_snapshot["parameter_stability_score"],
            "method_agreement_score": stability_snapshot["method_agreement_score"],
            "batch_continuity_score": stability_snapshot["batch_continuity_score"],
            "stability_flags": stability_snapshot["stability_flags"],
            "peak_support_score": waxs_support_snapshot["peak_support_score"],
            "background_stability_score": waxs_support_snapshot["background_stability_score"],
            "phase_support_score": waxs_support_snapshot["phase_support_score"],
            "size_support_score": waxs_support_snapshot["size_support_score"],
            "waxs_support_score": waxs_support_snapshot["waxs_support_score"],
            "transition_support_score": self._safe_float(output.get("transition_support_score", 0.0)) if is_waxs_temperature else 0.0,
            "transition_candidate_count": self._safe_float(output.get("transition_candidate_count", 0.0)) if is_waxs_temperature else 0.0,
            "peak_count": ir_support_snapshot["peak_count"],
            "assigned_peak_count": ir_support_snapshot["assigned_peak_count"],
            "reference_band_hit_count": ir_support_snapshot["reference_band_hit_count"],
            "reference_band_missing_count": ir_support_snapshot["reference_band_missing_count"],
            "assignment_confidence_score": ir_support_snapshot["assignment_confidence_score"],
            "key_band_support_score": ir_support_snapshot["key_band_support_score"],
            "baseline_stability_score": ir_support_snapshot["baseline_stability_score"],
            "peak_coverage_score": ir_support_snapshot["peak_coverage_score"],
            "ir_support_score": ir_support_snapshot["ir_support_score"],
            "triggered_constraint_count": ir_support_snapshot["triggered_constraint_count"],
            "unassigned_key_band_count": ir_support_snapshot["unassigned_key_band_count"],
            "classification_basis": ir_support_snapshot["classification_basis"],
            "event_support_score": dsc_support_snapshot["event_support_score"],
            "dsc_baseline_stability_score": dsc_support_snapshot["baseline_stability_score"],
            "thermodynamic_consistency_score": dsc_support_snapshot["thermodynamic_consistency_score"],
            "crystallinity_support_score": dsc_support_snapshot["crystallinity_support_score"],
            "dsc_support_score": dsc_support_snapshot["dsc_support_score"],
            "dsc_scan_r_squared_median": dsc_support_snapshot["scan_r_squared_median"],
            "dsc_scan_r_squared_spread": dsc_support_snapshot["scan_r_squared_spread"],
            "dsc_supported_event_fraction": dsc_support_snapshot["supported_event_fraction"],
            "dsc_supported_component_count": dsc_support_snapshot["supported_component_count"],
            "dsc_triggered_constraint_count": dsc_support_snapshot["triggered_constraint_count"],
            "dsc_validation_passed_count": dsc_support_snapshot["validation_passed_count"],
            "dsc_validation_total_count": dsc_support_snapshot["validation_total_count"],
            "fallback_ratio": saxs_evidence_snapshot["fallback_ratio"],
            "raw_snapshot_rows": saxs_evidence_snapshot["raw_snapshot_rows"],
            "raw_vs_calibrated_gap": saxs_evidence_snapshot["raw_vs_calibrated_gap"],
            "thickness_chain_risk": saxs_evidence_snapshot["thickness_chain_risk"],
            "q_contamination_frame_ratio": saxs_evidence_snapshot["q_contamination_frame_ratio"],
            "mask_truncated_frame_ratio": saxs_evidence_snapshot["mask_truncated_frame_ratio"],
            "low_conf_frame_ratio": saxs_evidence_snapshot["low_conf_frame_ratio"],
            "objective_score": objective_score,
            "quality_flag": quality_flag,
            "validation_summary": validation_summary,
            "residual_type": str(residuals_pattern.get("residual_type", "") or analysis_evidence.get("residual_evidence", {}).get("residual_type", "") or "").strip(),
            "hard_fail_names": hard_fail_names,
            "soft_warn_count": soft_warn_count,
            "joint_ai_context": joint_ai_context,
            "joint_context_penalty": joint_penalty,
        }

    def _saxs_evidence_snapshot(self, output: dict[str, Any], analysis_evidence: dict[str, Any]) -> dict[str, float]:
        if self.technique != "saxs":
            return {
                "fallback_ratio": 0.0,
                "raw_snapshot_rows": 0.0,
                "raw_vs_calibrated_gap": 0.0,
                "thickness_chain_risk": 0.0,
                "q_contamination_frame_ratio": 0.0,
                "mask_truncated_frame_ratio": 0.0,
                "low_conf_frame_ratio": 0.0,
            }

        batch_evidence = analysis_evidence.get("batch_evidence", {}) if isinstance(analysis_evidence, dict) else {}
        if not isinstance(batch_evidence, dict):
            batch_evidence = {}
        batch_summary = batch_evidence.get("batch_calibration_summary", {})
        if not isinstance(batch_summary, dict):
            batch_summary = {}

        batch_frames = self._safe_float(output.get("batch_frames") or batch_evidence.get("batch_frames"))
        if batch_frames <= 0:
            batch_frames = self._safe_float(batch_summary.get("batch_rows"))

        fallback_ratio = self._safe_float(batch_summary.get("fallback_ratio"))
        raw_snapshot_rows = self._safe_float(batch_summary.get("raw_snapshot_rows"))
        gap_terms = [
            batch_summary.get("lc_gap_mean"),
            batch_summary.get("L_gap_mean"),
            batch_summary.get("Xc_gap_mean"),
            batch_summary.get("phi_gap_mean"),
        ]
        raw_vs_calibrated_gap = self._mean_or_none(gap_terms)
        if raw_vs_calibrated_gap is None:
            raw_vs_calibrated_gap = 0.0

        symptom_names = {
            str(item.get("name", "")).strip()
            for item in self._analysis_symptoms(analysis_evidence)
            if isinstance(item, dict)
        }

        thickness_chain_risk = max(
            fallback_ratio,
            raw_vs_calibrated_gap,
            1.0 - self._safe_float(analysis_evidence.get("stability_evidence", {}).get("method_agreement_score", 1.0))
            if isinstance(analysis_evidence.get("stability_evidence"), dict)
            else 0.0,
        )
        if "thickness_chain_unreliable" in symptom_names:
            thickness_chain_risk = max(thickness_chain_risk, 0.7)

        def ratio_from(summary_key: str, fallback_keys: tuple[str, ...]) -> float:
            count = self._safe_float(batch_evidence.get(summary_key))
            if count <= 0:
                for key in fallback_keys:
                    count = self._safe_float(output.get(key))
                    if count > 0:
                        break
            if batch_frames <= 0:
                return 0.0
            return max(0.0, min(1.0, count / max(batch_frames, 1.0)))

        return {
            "fallback_ratio": max(0.0, min(1.0, fallback_ratio)),
            "raw_snapshot_rows": max(0.0, raw_snapshot_rows),
            "raw_vs_calibrated_gap": max(0.0, float(raw_vs_calibrated_gap)),
            "thickness_chain_risk": max(0.0, min(1.0, thickness_chain_risk)),
            "q_contamination_frame_ratio": ratio_from(
                "qstar_contaminated_frame_count",
                ("qstar_contaminated_frame_count", "guinier_lost_frame_count"),
            ),
            "mask_truncated_frame_ratio": ratio_from(
                "mask_truncated_frame_count",
                ("mask_truncated_frame_count",),
            ),
            "low_conf_frame_ratio": ratio_from(
                "low_conf_frame_count",
                ("low_conf_frame_count",),
            ),
        }

    def _ir_support_snapshot(self, output: dict[str, Any], analysis_evidence: dict[str, Any]) -> dict[str, Any]:
        if self.technique != "ir":
            return {
                "peak_count": 0.0,
                "assigned_peak_count": 0.0,
                "reference_band_hit_count": 0.0,
                "reference_band_missing_count": 0.0,
                "assignment_confidence_score": 0.0,
                "key_band_support_score": 0.0,
                "baseline_stability_score": 0.0,
                "peak_coverage_score": 0.0,
                "ir_support_score": 0.0,
                "triggered_constraint_count": 0.0,
                "unassigned_key_band_count": 0.0,
                "classification_basis": "",
            }

        output = dict(output or {})
        analysis_evidence = dict(analysis_evidence or {})
        feature_evidence = analysis_evidence.get("feature_evidence", {})
        if not isinstance(feature_evidence, dict):
            feature_evidence = {}
        peak_evidence = feature_evidence.get("peak_evidence", {})
        if not isinstance(peak_evidence, dict):
            peak_evidence = {}
        assignment_evidence = feature_evidence.get("assignment_evidence", {})
        if not isinstance(assignment_evidence, dict):
            assignment_evidence = {}
        structure_evidence = feature_evidence.get("structure_evidence", {})
        if not isinstance(structure_evidence, dict):
            structure_evidence = {}
        ir_support_evidence = feature_evidence.get("ir_support_evidence", {})
        if not isinstance(ir_support_evidence, dict):
            ir_support_evidence = {}
        reference_evidence = feature_evidence.get("reference_evidence", {})
        if not isinstance(reference_evidence, dict):
            reference_evidence = {}
        constraint_summary = analysis_evidence.get("constraint_summary", {})
        if not isinstance(constraint_summary, dict):
            constraint_summary = {}

        peak_count = self._safe_float(peak_evidence.get("peak_count", output.get("n_peaks")))
        assigned_peak_count = self._safe_float(peak_evidence.get("assigned_peak_count", assignment_evidence.get("assigned_peak_count", 0.0)))
        reference_band_hit_count = self._safe_float(reference_evidence.get("hit_count", assignment_evidence.get("key_band_hit_count", 0.0)))
        reference_band_missing_count = self._safe_float(reference_evidence.get("missing_count", assignment_evidence.get("key_band_missing_count", 0.0)))
        reference_band_count = self._safe_float(reference_evidence.get("band_count", 0.0))
        if reference_band_count <= 0:
            reference_band_count = reference_band_hit_count + reference_band_missing_count
        assignment_confidence_score = self._safe_float(
            ir_support_evidence.get(
                "assignment_confidence_score",
                assignment_evidence.get("assignment_confidence_score", assignment_evidence.get("assignment_confidence", output.get("assignment_confidence", output.get("polymer_score", 0.0)))),
            )
        )
        key_band_support_score = self._safe_float(
            ir_support_evidence.get(
                "key_band_support_score",
                assignment_evidence.get("key_band_support_score", (reference_band_hit_count / reference_band_count) if reference_band_count > 0 else 0.0),
            )
        )
        baseline_stability_score = self._safe_float(
            ir_support_evidence.get(
                "baseline_stability_score",
                structure_evidence.get("baseline_stability_score", 0.0),
            )
        )
        peak_coverage_score = self._safe_float(
            ir_support_evidence.get(
                "peak_coverage_score",
                assignment_evidence.get("peak_coverage_score", (assigned_peak_count / peak_count) if peak_count > 0 else 0.0),
            )
        )
        triggered_constraint_count = self._safe_float(
            ir_support_evidence.get(
                "triggered_constraint_count",
                constraint_summary.get("triggered_total", 0.0),
            )
        )
        unassigned_key_band_count = self._safe_float(
            ir_support_evidence.get(
                "unassigned_key_band_count",
                assignment_evidence.get("unassigned_key_band_count", reference_band_missing_count),
            )
        )
        ir_support_score = self._safe_float(ir_support_evidence.get("ir_support_score", structure_evidence.get("ir_support_score", 0.0)))
        if ir_support_score <= 0.0 and any(value > 0.0 for value in (assignment_confidence_score, key_band_support_score, baseline_stability_score, peak_coverage_score)):
            ir_support_score = max(
                0.0,
                min(
                    1.0,
                    0.38 * assignment_confidence_score
                    + 0.30 * key_band_support_score
                    + 0.18 * peak_coverage_score
                    + 0.14 * baseline_stability_score,
                ),
            )
        classification_basis = str(structure_evidence.get("classification_basis", "") or "").strip()

        return {
            "peak_count": peak_count,
            "assigned_peak_count": assigned_peak_count,
            "reference_band_hit_count": reference_band_hit_count,
            "reference_band_missing_count": reference_band_missing_count,
            "assignment_confidence_score": assignment_confidence_score,
            "key_band_support_score": key_band_support_score,
            "baseline_stability_score": baseline_stability_score,
            "peak_coverage_score": peak_coverage_score,
            "ir_support_score": ir_support_score,
            "triggered_constraint_count": triggered_constraint_count,
            "unassigned_key_band_count": unassigned_key_band_count,
            "classification_basis": classification_basis,
        }

    def _stability_snapshot(self, output: dict[str, Any], analysis_evidence: dict[str, Any]) -> dict[str, Any]:
        if self.technique != "saxs":
            return {
                "stability_score": 1.0,
                "parameter_stability_score": 1.0,
                "method_agreement_score": 1.0,
                "batch_continuity_score": 1.0,
                "stability_flags": [],
            }

        evidence = analysis_evidence.get("stability_evidence", {}) if isinstance(analysis_evidence, dict) else {}
        if not isinstance(evidence, dict):
            evidence = {}

        batch_frames_raw = output.get("batch_frames")
        try:
            batch_frames = int(batch_frames_raw) if batch_frames_raw is not None else 0
        except (TypeError, ValueError):
            batch_frames = 0
        continuity = self._safe_float(output.get("condition_continuity_score"))
        condition_confidence = self._safe_float(output.get("condition_confidence"))
        missing_frames = output.get("condition_missing_frames")
        try:
            missing = int(missing_frames) if missing_frames is not None else 0
        except (TypeError, ValueError):
            missing = 0
        coverage = 1.0
        if batch_frames > 0:
            coverage = max(0.0, min(1.0, 1.0 - (missing / max(batch_frames, 1))))

        def pick(name: str, fallback: float) -> float:
            value = self._safe_float(evidence.get(name))
            return value if value != 0.0 or evidence.get(name) is not None else fallback

        parameter_stability = pick(
            "parameter_stability_score",
            max(
                0.0,
                min(
                    1.0,
                    (
                        0.45 * self._safe_float(output.get("quality_score", 0.0))
                        + 0.35 * self._safe_float(output.get("L_confidence", 0.0))
                        + 0.20 * self._safe_float(output.get("lc_confidence", 0.0))
                    ),
                ),
            ),
        )
        method_agreement = pick("method_agreement_score", 0.5)
        batch_continuity = pick(
            "batch_continuity_score",
            max(
                0.0,
                min(
                    1.0,
                    (
                        0.45 * continuity
                        + 0.35 * condition_confidence
                        + 0.20 * coverage
                    )
                    if batch_frames > 1 or continuity or condition_confidence
                    else 1.0
                ),
            ),
        )
        stability_score = pick(
            "stability_score",
            max(
                0.0,
                min(
                    1.0,
                    0.45 * parameter_stability + 0.35 * method_agreement + 0.20 * batch_continuity,
                ),
            ),
        )
        flags = evidence.get("stability_flags", [])
        if not isinstance(flags, list):
            flags = []
        return {
            "stability_score": stability_score,
            "parameter_stability_score": parameter_stability,
            "method_agreement_score": method_agreement,
            "batch_continuity_score": batch_continuity,
            "stability_flags": [str(item).strip() for item in flags if str(item).strip()],
        }

    def _dsc_support_snapshot(
        self,
        output: dict[str, Any],
        analysis_evidence: dict[str, Any],
    ) -> dict[str, Any]:
        if self.technique != "dsc":
            return {
                "event_support_score": 1.0,
                "baseline_stability_score": 1.0,
                "thermodynamic_consistency_score": 1.0,
                "crystallinity_support_score": 1.0,
                "dsc_support_score": 1.0,
                "scan_r_squared_median": 1.0,
                "scan_r_squared_spread": 0.0,
                "supported_event_fraction": 1.0,
                "supported_component_count": 0.0,
                "triggered_constraint_count": 0.0,
                "validation_passed_count": 0.0,
                "validation_total_count": 0.0,
            }

        output = dict(output or {})
        analysis_evidence = dict(analysis_evidence or {})
        feature_evidence = analysis_evidence.get("feature_evidence", {})
        if not isinstance(feature_evidence, dict):
            feature_evidence = {}
        event_evidence = feature_evidence.get("event_support_evidence", {})
        if not isinstance(event_evidence, dict):
            event_evidence = {}
        baseline_evidence = feature_evidence.get("baseline_evidence", {})
        if not isinstance(baseline_evidence, dict):
            baseline_evidence = {}
        crystallinity_evidence = feature_evidence.get("crystallinity_evidence", {})
        if not isinstance(crystallinity_evidence, dict):
            crystallinity_evidence = {}

        cross_validation = analysis_evidence.get("cross_validation", {})
        validation_passed_count = 0.0
        validation_total_count = 0.0
        if isinstance(cross_validation, dict):
            def _visit(node: Any) -> None:
                nonlocal validation_passed_count, validation_total_count
                if isinstance(node, dict):
                    if "passed" in node:
                        validation_total_count += 1.0
                        if bool(node.get("passed")):
                            validation_passed_count += 1.0
                    else:
                        for value in node.values():
                            _visit(value)
                elif isinstance(node, list):
                    for value in node:
                        _visit(value)

            _visit(cross_validation)

        event_support_score = self._safe_float(
            event_evidence.get(
                "event_support_score",
                output.get("event_support_score", 0.0),
            )
        )
        baseline_stability_score = self._safe_float(
            event_evidence.get(
                "baseline_stability_score",
                baseline_evidence.get("baseline_stability_score", output.get("baseline_stability_score", 0.0)),
            )
        )
        thermodynamic_consistency_score = self._safe_float(
            event_evidence.get(
                "thermodynamic_consistency_score",
                output.get("thermodynamic_consistency_score", 0.0),
            )
        )
        supported_event_fraction = self._safe_float(event_evidence.get("supported_event_fraction", 0.0))
        supported_component_count = self._safe_float(event_evidence.get("supported_component_count", 0.0))
        scan_r_squared_median = self._safe_float(event_evidence.get("scan_r_squared_median", output.get("scan_r_squared_median", output.get("scan_r_squared", 0.0))))
        scan_r_squared_spread = self._safe_float(event_evidence.get("scan_r_squared_spread", output.get("scan_r_squared_spread", 0.0)))
        quality_score = self._safe_float(output.get("quality_score", 0.0))
        crystallinity_support_score = self._safe_float(
            crystallinity_evidence.get(
                "crystallinity_support_score",
                output.get("crystallinity_support_score", 0.0),
            )
        )
        if crystallinity_support_score <= 0.0:
            crystallinity_support_score = max(
                0.0,
                min(
                    1.0,
                    0.45 * (1.0 if self._safe_float(output.get("Xc_pct")) > 0 else 0.0)
                    + 0.35 * (1.0 if self._safe_float(output.get("DHm_Jg")) not in {None, 0.0} else 0.0)
                    + 0.20 * event_support_score,
                ),
            )
        constraint_summary = analysis_evidence.get("constraint_summary", {})
        if not isinstance(constraint_summary, dict):
            constraint_summary = {}
        triggered_constraint_count = self._safe_float(constraint_summary.get("triggered_total", 0.0))

        dsc_support_score = max(
            0.0,
            min(
                1.0,
                0.30 * event_support_score
                + 0.22 * baseline_stability_score
                + 0.18 * thermodynamic_consistency_score
                + 0.18 * crystallinity_support_score
                + 0.12 * max(0.0, min(1.0, quality_score)),
            ),
        )
        if validation_total_count > 0:
            dsc_support_score = min(dsc_support_score, 0.85 + 0.15 * (validation_passed_count / validation_total_count))

        return {
            "event_support_score": event_support_score,
            "baseline_stability_score": baseline_stability_score,
            "thermodynamic_consistency_score": thermodynamic_consistency_score,
            "crystallinity_support_score": crystallinity_support_score,
            "dsc_support_score": dsc_support_score,
            "scan_r_squared_median": scan_r_squared_median,
            "scan_r_squared_spread": scan_r_squared_spread,
            "supported_event_fraction": supported_event_fraction,
            "supported_component_count": supported_component_count,
            "triggered_constraint_count": triggered_constraint_count,
            "validation_passed_count": validation_passed_count,
            "validation_total_count": validation_total_count,
        }

    def _waxs_support_snapshot(
        self,
        output: dict[str, Any],
        residuals_pattern: dict[str, Any],
        analysis_evidence: dict[str, Any],
    ) -> dict[str, float]:
        if self.technique != "waxs":
            return {
                "peak_support_score": 1.0,
                "background_stability_score": 1.0,
                "phase_support_score": 1.0,
                "size_support_score": 1.0,
                "waxs_support_score": 1.0,
            }

        output = dict(output or {})
        residuals_pattern = dict(residuals_pattern or {})
        analysis_evidence = dict(analysis_evidence or {})
        peak_evidence = analysis_evidence.get("peak_evidence", {})
        if not isinstance(peak_evidence, dict):
            peak_evidence = {}
        background_evidence = analysis_evidence.get("background_evidence", {})
        if not isinstance(background_evidence, dict):
            background_evidence = {}
        phase_evidence = analysis_evidence.get("phase_evidence", {})
        if not isinstance(phase_evidence, dict):
            phase_evidence = {}

        constraint_summary = analysis_evidence.get("constraint_summary", {})
        triggered_names: set[str] = set()
        if isinstance(constraint_summary, dict):
            nested = constraint_summary.get("triggered_names", {})
            if isinstance(nested, dict):
                for names in nested.values():
                    if not isinstance(names, list):
                        continue
                    triggered_names.update(
                        str(item).strip()
                        for item in names
                        if str(item).strip()
                    )

        symptom_names = {
            str(item.get("name", "")).strip()
            for item in self._analysis_symptoms(analysis_evidence)
            if isinstance(item, dict) and str(item.get("name", "")).strip()
        }
        residual_type = str(
            residuals_pattern.get("residual_type", "")
            or analysis_evidence.get("residual_evidence", {}).get("residual_type", "")
            or ""
        ).strip().lower()

        def _clamp(value: float) -> float:
            return max(0.0, min(1.0, value))

        def _spread_score(spread: float | None, limit: float, default: float = 0.72) -> float:
            if spread is None:
                return default
            return _clamp(1.0 - max(0.0, float(spread)) / max(limit, 1e-9))

        peak_count = self._safe_float(peak_evidence.get("peak_count", output.get("n_peaks")))
        peak_gap_spread = self._safe_float(peak_evidence.get("peak_gap_spread"))
        peak_width_spread = self._safe_float(peak_evidence.get("peak_width_spread"))

        count_score = 0.0
        if peak_count > 0:
            count_score = min(1.0, peak_count / 2.0)
        gap_score = _spread_score(peak_gap_spread, 0.45)
        width_score = _spread_score(peak_width_spread, 0.55)
        peak_support_score = _clamp(0.56 * count_score + 0.24 * gap_score + 0.20 * width_score)
        if peak_count and peak_count < 2:
            peak_support_score -= 0.16
        if "peak_visibility" in triggered_names or "peak_count_insufficient" in triggered_names:
            peak_support_score -= 0.15
        if "peak_family_unstable" in triggered_names:
            peak_support_score -= 0.12
        if "peak_width_nonphysical" in triggered_names:
            peak_support_score -= 0.12
        if residual_type in {"peak_position_bias", "peak_width_mismatch", "peak_count_underfit", "peak_count_overfit"}:
            peak_support_score -= 0.08
        peak_support_score = _clamp(peak_support_score)

        offset = self._safe_float(background_evidence.get("two_theta_offset", output.get("two_theta_offset")))
        offset_score = _clamp(1.0 - abs(offset) / 0.08)
        background_method = str(background_evidence.get("background_method", output.get("background_method", "")) or "").strip()
        amorphous_subtraction = str(background_evidence.get("amorphous_subtraction", output.get("amorphous_subtraction", "")) or "").strip()
        amorphous_n_peaks = self._safe_float(background_evidence.get("amorphous_n_peaks", output.get("amorphous_n_peaks")))
        method_score = 0.50
        if background_method:
            method_score += 0.20
        if amorphous_subtraction:
            method_score += 0.15
        if background_method and amorphous_subtraction:
            method_score += 0.05
        method_score = _clamp(method_score)
        if amorphous_n_peaks > 0:
            partition_score = _clamp(0.42 + min(amorphous_n_peaks, 3.0) * 0.18)
        else:
            partition_score = 0.58
        background_stability_score = _clamp(0.45 * offset_score + 0.30 * method_score + 0.25 * partition_score)
        if residual_type in {"amorphous_background_bias", "low_angle_background_drift"}:
            background_stability_score -= 0.15
        if "offset_sensitive_solution" in triggered_names or "amorphous_partition_unstable" in triggered_names:
            background_stability_score -= 0.15
        if "low_angle_background_drift" in symptom_names:
            background_stability_score -= 0.06
        background_stability_score = _clamp(background_stability_score)

        x_pct = self._safe_float(output.get("Xc_pct"))
        if x_pct <= 0 and self._safe_float(output.get("Xc")) > 0:
            x_pct = self._safe_float(output.get("Xc")) * 100.0
        crystallinity_method = str(
            phase_evidence.get(
                "crystallinity_method",
                output.get("crystallinity_method", output.get("Xc_method", "")),
            )
            or ""
        ).strip().lower()
        method_support = 0.55
        if crystallinity_method:
            method_support = 0.72
        if crystallinity_method in {"peak_deconvolution", "peak_area"}:
            method_support = 1.0
        elif crystallinity_method in {"no_sharp_peak", "amorphous"}:
            method_support = 0.35
        x_support = 1.0 if x_pct > 0 else 0.0
        peak_link = 0.35 + 0.65 * peak_support_score if peak_count >= 2 else 0.18 + 0.45 * peak_support_score
        phase_support_score = _clamp(0.30 * x_support + 0.30 * method_support + 0.40 * peak_link)
        if "crystallinity_without_peak_support" in triggered_names:
            phase_support_score -= 0.25
        if residual_type in {"amorphous_background_bias", "peak_count_underfit", "peak_position_bias"}:
            phase_support_score -= 0.05
        if peak_count and peak_count < 2:
            phase_support_score -= 0.10
        phase_support_score = _clamp(phase_support_score)

        size_value = self._safe_float(phase_evidence.get("D_Scherrer_nm", output.get("D_Scherrer_nm")))
        size_support = 1.0 if size_value > 0 else 0.0
        width_health = _spread_score(peak_width_spread, 0.60, default=0.70)
        if peak_count >= 2:
            peak_size_link = 1.0
        elif peak_count > 0:
            peak_size_link = 0.25
        else:
            peak_size_link = 0.0
        size_support_score = _clamp(0.35 * size_support + 0.35 * peak_size_link + 0.30 * width_health)
        if "size_without_multi_peak_support" in triggered_names:
            size_support_score -= 0.25
        if "peak_width_nonphysical" in triggered_names:
            size_support_score -= 0.10
        if residual_type in {"peak_width_mismatch", "peak_count_underfit"}:
            size_support_score -= 0.05
        size_support_score = _clamp(size_support_score)

        waxs_support_score = _clamp(
            0.35 * peak_support_score
            + 0.25 * background_stability_score
            + 0.25 * phase_support_score
            + 0.15 * size_support_score
        )

        return {
            "peak_support_score": round(peak_support_score, 3),
            "background_stability_score": round(background_stability_score, 3),
            "phase_support_score": round(phase_support_score, 3),
            "size_support_score": round(size_support_score, 3),
            "waxs_support_score": round(waxs_support_score, 3),
        }

    def _regression_reason(self, candidate_metrics: dict[str, Any], previous_metrics: dict[str, Any]) -> str:
        if self.technique == "dsc":
            dsc_reason = self._dsc_regression_reason(candidate_metrics, previous_metrics)
            if dsc_reason:
                return dsc_reason
        if self.technique == "waxs":
            if self._submodule_id() in {"waxs.temperature", "waxs.in_situ_temp"}:
                return self._waxs_temperature_regression_reason(candidate_metrics, previous_metrics)
            waxs_reason = self._waxs_regression_reason(candidate_metrics, previous_metrics)
            if waxs_reason:
                return waxs_reason
        if self.technique == "ir":
            ir_reason = self._ir_regression_reason(candidate_metrics, previous_metrics)
            if ir_reason:
                return ir_reason
        deltas = {
            "quality_score_dropped": candidate_metrics["quality_score"] - previous_metrics["quality_score"],
            "validation_risk_increased": candidate_metrics["validation_score"] - previous_metrics["validation_score"],
            "residual_risk_increased": candidate_metrics["residual_score"] - previous_metrics["residual_score"],
            "fit_improved_but_phys_worse": candidate_metrics["physical_score"] - previous_metrics["physical_score"],
        }
        for reason, delta in deltas.items():
            if delta < -self._component_drop_tolerance():
                return reason
        return ""

    def _dsc_regression_reason(self, candidate_metrics: dict[str, Any], previous_metrics: dict[str, Any]) -> str:
        if self.technique != "dsc":
            return ""

        candidate_event = self._safe_float(candidate_metrics.get("event_support_score", 0.0))
        previous_event = self._safe_float(previous_metrics.get("event_support_score", 0.0))
        candidate_baseline = self._safe_float(candidate_metrics.get("baseline_stability_score", 0.0))
        previous_baseline = self._safe_float(previous_metrics.get("baseline_stability_score", 0.0))
        candidate_thermal = self._safe_float(candidate_metrics.get("thermodynamic_consistency_score", 0.0))
        previous_thermal = self._safe_float(previous_metrics.get("thermodynamic_consistency_score", 0.0))
        candidate_cryst = self._safe_float(candidate_metrics.get("crystallinity_support_score", 0.0))
        previous_cryst = self._safe_float(previous_metrics.get("crystallinity_support_score", 0.0))
        candidate_validation = self._safe_float(candidate_metrics.get("validation_score", 0.0))
        previous_validation = self._safe_float(previous_metrics.get("validation_score", 0.0))
        candidate_triggered = self._safe_float(candidate_metrics.get("triggered_constraint_count", 0.0))
        previous_triggered = self._safe_float(previous_metrics.get("triggered_constraint_count", 0.0))
        candidate_support = self._safe_float(candidate_metrics.get("dsc_support_score", 0.0))
        previous_support = self._safe_float(previous_metrics.get("dsc_support_score", 0.0))

        if previous_event >= 0.55 and candidate_event < previous_event - 0.08:
            return "event_support_weakened"
        if previous_baseline >= 0.55 and candidate_baseline < previous_baseline - 0.08:
            return "baseline_became_less_stable"
        if previous_thermal >= 0.55 and candidate_thermal < previous_thermal - 0.08:
            return "thermal_consistency_worsened"
        if previous_cryst >= 0.55 and candidate_cryst < previous_cryst - 0.08:
            return "crystallinity_support_weakened"
        if previous_validation >= 0.55 and candidate_validation < previous_validation - 0.05:
            return "cross_validation_conflict_worsened"
        if candidate_triggered > previous_triggered + 0.5 and candidate_support <= previous_support + 0.01:
            return "triggered_constraint_pressure_increased"
        if candidate_support <= previous_support + 0.01:
            return "dsc_support_not_improving"
        return ""

    def _waxs_regression_reason(self, candidate_metrics: dict[str, Any], previous_metrics: dict[str, Any]) -> str:
        peak_delta = self._safe_float(candidate_metrics.get("peak_support_score", 1.0)) - self._safe_float(previous_metrics.get("peak_support_score", 1.0))
        background_delta = self._safe_float(candidate_metrics.get("background_stability_score", 1.0)) - self._safe_float(previous_metrics.get("background_stability_score", 1.0))
        phase_delta = self._safe_float(candidate_metrics.get("phase_support_score", 1.0)) - self._safe_float(previous_metrics.get("phase_support_score", 1.0))
        size_delta = self._safe_float(candidate_metrics.get("size_support_score", 1.0)) - self._safe_float(previous_metrics.get("size_support_score", 1.0))
        overall_delta = self._safe_float(candidate_metrics.get("waxs_support_score", 1.0)) - self._safe_float(previous_metrics.get("waxs_support_score", 1.0))

        if self._safe_float(previous_metrics.get("peak_support_score", 1.0)) >= 0.55 and peak_delta < -0.08:
            return "peak_family_became_less_stable"
        if self._safe_float(previous_metrics.get("background_stability_score", 1.0)) >= 0.55 and background_delta < -0.08:
            return "background_partition_worsened"
        if (
            self._safe_float(previous_metrics.get("phase_support_score", 1.0)) >= 0.55
            and phase_delta < -0.08
        ) or (
            self._safe_float(previous_metrics.get("size_support_score", 1.0)) >= 0.55
            and size_delta < -0.08
        ):
            return "crystallinity_support_collapsed"
        if self._safe_float(previous_metrics.get("waxs_support_score", 1.0)) >= 0.60 and overall_delta < -0.07:
            return "physical_support_weakened"
        return ""

    def _waxs_temperature_regression_reason(self, candidate_metrics: dict[str, Any], previous_metrics: dict[str, Any]) -> str:
        axis_delta = self._safe_float(candidate_metrics.get("temperature_axis_confidence", candidate_metrics.get("condition_confidence", 0.0))) - self._safe_float(previous_metrics.get("temperature_axis_confidence", previous_metrics.get("condition_confidence", 0.0)))
        family_delta = self._safe_float(candidate_metrics.get("peak_family_continuity_score", 0.0)) - self._safe_float(previous_metrics.get("peak_family_continuity_score", 0.0))
        xc_delta = self._safe_float(candidate_metrics.get("Xc_trend_support_score", 0.0)) - self._safe_float(previous_metrics.get("Xc_trend_support_score", 0.0))
        d_delta = self._safe_float(candidate_metrics.get("D_trend_support_score", 0.0)) - self._safe_float(previous_metrics.get("D_trend_support_score", 0.0))
        transition_delta = self._safe_float(candidate_metrics.get("transition_support_score", 0.0)) - self._safe_float(previous_metrics.get("transition_support_score", 0.0))
        low_conf_delta = self._safe_float(candidate_metrics.get("frame_low_conf_count", 0.0)) - self._safe_float(previous_metrics.get("frame_low_conf_count", 0.0))
        swap_delta = self._safe_float(candidate_metrics.get("peak_family_identity_swap_count", 0.0)) - self._safe_float(previous_metrics.get("peak_family_identity_swap_count", 0.0))

        if self._safe_float(previous_metrics.get("temperature_axis_confidence", previous_metrics.get("condition_confidence", 0.0))) >= 0.70 and axis_delta < -0.06:
            return "temperature_axis_confidence_worsened"
        if self._safe_float(previous_metrics.get("peak_family_continuity_score", 0.0)) >= 0.55 and family_delta < -0.06:
            return "peak_family_tracking_worsened"
        if self._safe_float(previous_metrics.get("Xc_trend_support_score", 0.0)) >= 0.55 and xc_delta < -0.07:
            return "Xc_trend_support_collapsed"
        if self._safe_float(previous_metrics.get("D_trend_support_score", 0.0)) >= 0.55 and d_delta < -0.07:
            return "D_trend_support_collapsed"
        if self._safe_float(previous_metrics.get("transition_support_score", 0.0)) >= 0.50 and transition_delta < -0.06:
            return "transition_support_weakened"
        if low_conf_delta > 0.5 and d_delta <= 0.01 and xc_delta <= 0.01:
            return "frame_fit_improved_but_sequence_worsened"
        if swap_delta > 0.5 and family_delta <= 0.01:
            return "peak_family_tracking_worsened"
        return ""

    def _ir_regression_reason(self, candidate_metrics: dict[str, Any], previous_metrics: dict[str, Any]) -> str:
        if self.technique != "ir":
            return ""

        candidate_support = self._safe_float(candidate_metrics.get("ir_support_score", 0.0))
        previous_support = self._safe_float(previous_metrics.get("ir_support_score", 0.0))
        candidate_assignment = self._safe_float(candidate_metrics.get("assignment_confidence_score", candidate_metrics.get("quality_score", 0.0)))
        previous_assignment = self._safe_float(previous_metrics.get("assignment_confidence_score", previous_metrics.get("quality_score", 0.0)))
        candidate_key_band = self._safe_float(candidate_metrics.get("key_band_support_score", 0.0))
        previous_key_band = self._safe_float(previous_metrics.get("key_band_support_score", 0.0))
        candidate_baseline = self._safe_float(candidate_metrics.get("baseline_stability_score", 0.0))
        previous_baseline = self._safe_float(previous_metrics.get("baseline_stability_score", 0.0))
        candidate_peak_coverage = self._safe_float(candidate_metrics.get("peak_coverage_score", 0.0))
        previous_peak_coverage = self._safe_float(previous_metrics.get("peak_coverage_score", 0.0))
        candidate_peak_count = self._safe_float(candidate_metrics.get("peak_count", 0.0))
        previous_peak_count = self._safe_float(previous_metrics.get("peak_count", 0.0))
        candidate_triggered = self._safe_float(candidate_metrics.get("triggered_constraint_count", 0.0))
        previous_triggered = self._safe_float(previous_metrics.get("triggered_constraint_count", 0.0))
        candidate_unassigned = self._safe_float(candidate_metrics.get("unassigned_key_band_count", 0.0))
        previous_unassigned = self._safe_float(previous_metrics.get("unassigned_key_band_count", 0.0))
        candidate_basis = str(candidate_metrics.get("classification_basis", "") or "").strip()
        previous_basis = str(previous_metrics.get("classification_basis", "") or "").strip()

        if previous_key_band >= 0.55 and candidate_key_band < previous_key_band - 0.08:
            return "key_band_support_collapsed"
        if previous_assignment >= 0.55 and candidate_assignment < previous_assignment - 0.08:
            return "assignment_support_weakened"
        if previous_baseline >= 0.55 and candidate_baseline < previous_baseline - 0.08:
            return "baseline_became_less_stable"
        if previous_peak_coverage >= 0.55 and candidate_peak_count > previous_peak_count and candidate_key_band < previous_key_band - 0.05:
            return "peak_count_increased_but_key_bands_lost"
        if previous_basis == "peak_assignment" and candidate_basis != "peak_assignment" and candidate_key_band <= previous_key_band:
            return "classification_basis_became_weaker"
        if candidate_support <= previous_support + 0.01:
            if candidate_key_band < previous_key_band - 0.01:
                return "key_band_support_collapsed"
            if candidate_assignment < previous_assignment - 0.01:
                return "assignment_support_weakened"
            if candidate_baseline < previous_baseline - 0.01:
                return "baseline_became_less_stable"
            if candidate_peak_count > previous_peak_count and candidate_unassigned > previous_unassigned:
                return "peak_count_increased_but_key_bands_lost"
            if candidate_triggered > previous_triggered:
                return "classification_basis_became_weaker"
            return "classification_basis_became_weaker"
        return ""

    def _joint_ai_context(self) -> dict[str, Any]:
        workspace_context = self.workspace_context if isinstance(self.workspace_context, dict) else {}
        joint_ai_context = workspace_context.get("joint_ai_context") if isinstance(workspace_context, dict) else {}
        return joint_ai_context if isinstance(joint_ai_context, dict) else {}

    def _residual_score(self, residuals_pattern: dict[str, Any]) -> float:
        residual_type = str(residuals_pattern.get("residual_type", "") or "").strip().lower()
        score_map = {
            "random": 1.0,
            "unknown": 0.76,
            "background_drift": 0.72,
            "baseline_drift": 0.64,
            "baseline_drift_low_t": 0.60,
            "baseline_drift_high_t": 0.60,
            "melting_peak_shift": 0.62,
            "tg_step_missing": 0.58,
            "cold_crystallization_overlap": 0.56,
            "event_window_too_narrow": 0.58,
            "event_window_too_wide": 0.59,
            "exo_up_down_confusion": 0.48,
            "multi_event_underfit": 0.55,
            "segment_split_issue": 0.54,
            "noise_dominant": 0.56,
            "low_angle_background_drift": 0.68,
            "key_band_mismatch": 0.58,
            "crowded_band_underfit": 0.57,
            "normalization_bias": 0.59,
            "baseline_drift_low_wn": 0.64,
            "baseline_drift_high_wn": 0.64,
        }
        score = score_map.get(residual_type, 0.72)
        summary = str(residuals_pattern.get("summary", "") or "").strip().lower()
        if "background" in summary:
            score = min(score, 0.72)
        if "systematic" in summary:
            score = min(score, 0.60)
        if "noise" in summary:
            score = min(score, 0.58)
        return max(0.0, min(1.0, score))

    def _first_text(self, primary: dict[str, Any], fallback: dict[str, Any], keys: tuple[str, ...]) -> str:
        for key in keys:
            value = primary.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            value = fallback.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    def _mean_or_none(self, values) -> float | None:
        items = []
        for value in values:
            if value is None:
                continue
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue
            if math.isfinite(number):
                items.append(number)
        if not items:
            return None
        return sum(items) / len(items)

    def _objective_gain_threshold(self) -> float:
        threshold = 0.01
        joint_ai_context = self._joint_ai_context()
        if not joint_ai_context:
            return threshold

        issue_count = self._safe_float(joint_ai_context.get("issue_count"))
        warning_count = self._safe_float(joint_ai_context.get("warning_count"))
        error_count = self._safe_float(joint_ai_context.get("error_count"))
        issue_families = joint_ai_context.get("issue_families")

        if math.isfinite(issue_count) and issue_count > 0:
            threshold += 0.004 * min(issue_count, 5.0)
        if math.isfinite(warning_count) and warning_count > 0:
            threshold += 0.001 * min(warning_count, 4.0)
        if math.isfinite(error_count) and error_count > 0:
            threshold += 0.008 * min(error_count, 3.0)
        if isinstance(issue_families, list):
            families = {str(item).strip().lower() for item in issue_families if str(item).strip()}
            if "phi_c inconsistency" in families:
                threshold += 0.002
            if "tm bidirectional gap" in families:
                threshold += 0.002
            if "l consistency unstable" in families:
                threshold += 0.0015
        return min(threshold, 0.05)

    def _r_squared_drop_tolerance(self) -> float:
        return 0.001

    def _component_drop_tolerance(self) -> float:
        return 0.06

    def _saxs_cross_validation(self, output: dict[str, Any]) -> dict[str, Any]:
        validations: list[dict[str, Any]] = []
        l_bragg = self._safe_float(output.get("L_bragg"))
        l_corr = self._safe_float(output.get("L_corr_peak", output.get("L_corr")))
        l_best = self._safe_float(output.get("L_nm", output.get("L_best")))
        if math.isfinite(l_bragg) and math.isfinite(l_best):
            diff = abs(l_bragg - l_best)
            rel = diff / max(abs(l_bragg), abs(l_best), 1e-9)
            validations.append(
                {
                    "check_name": f"{self.technique}/L_bragg_vs_L_best",
                    "passed": rel <= 0.03,
                    "severity": "OK" if rel <= 0.03 else "WARN",
                    "message": f"L(Bragg)={l_bragg:.3f} vs L(best)={l_best:.3f} nm",
                    "details": {"L_bragg_nm": l_bragg, "L_best_nm": l_best, "diff_nm": diff, "rel_diff": rel},
                }
            )
        if math.isfinite(l_bragg) and math.isfinite(l_corr):
            diff = abs(l_bragg - l_corr)
            rel = diff / max(abs(l_bragg), abs(l_corr), 1e-9)
            validations.append(
                {
                    "check_name": f"{self.technique}/L_bragg_vs_L_corr",
                    "passed": rel <= 0.03,
                    "severity": "OK" if rel <= 0.03 else "WARN",
                    "message": f"L(Bragg)={l_bragg:.3f} vs L(corr)={l_corr:.3f} nm",
                    "details": {"L_bragg_nm": l_bragg, "L_corr_nm": l_corr, "diff_nm": diff, "rel_diff": rel},
                }
            )
        if output.get("beam_stop_contaminated"):
            validations.append(
                {
                    "check_name": f"{self.technique}/beamstop",
                    "passed": False,
                    "severity": "ERROR",
                    "message": "beam_stop_contaminated",
                    "details": {"beam_stop_contaminated": True},
                }
            )
        return {"saxs": validations}

    def _dsc_cross_validation(self, output: dict[str, Any]) -> dict[str, Any]:
        validations: list[dict[str, Any]] = []
        tm = self._safe_float(output.get("Tm_peak_C"))
        xc = self._safe_float(output.get("Xc_pct"))
        if math.isfinite(tm):
            validations.append(
                {
                    "check_name": f"{self.technique}/tm_present",
                    "passed": True,
                    "severity": "OK",
                    "message": f"Tm_peak_C={tm:.2f}",
                    "details": {"Tm_peak_C": tm},
                }
            )
        if math.isfinite(xc):
            validations.append(
                {
                    "check_name": f"{self.technique}/xc_present",
                    "passed": True,
                    "severity": "OK",
                    "message": f"Xc_pct={xc:.2f}",
                    "details": {"Xc_pct": xc},
                }
            )
        return {"dsc": validations}

    def _resolve_data_file(self, data_file: str) -> Path:
        path = Path(data_file)
        if path.is_absolute():
            return path
        direct = (self.project_root / path).resolve()
        if direct.exists():
            return direct
        return (self.project_root / "测试数据" / path).resolve()

    def _config_snapshot(self, engine: Any) -> dict[str, Any]:
        config = self._engine_config(engine)
        return self._config_to_dict(config)

    def _config_to_dict(self, config: Any) -> dict[str, Any]:
        if config is None:
            return {}
        if hasattr(config, "to_dict"):
            return self._to_plain_value(config.to_dict())
        if is_dataclass(config):
            return self._to_plain_value(asdict(config))
        return {}

    def _ir_reference_bands(self, engine: Any) -> dict[str, Any]:
        if self.technique != "ir":
            return {}
        config = self._engine_config(engine)
        polymer_db = getattr(config, "polymer_peaks_db", {}) if config is not None else {}
        if not isinstance(polymer_db, dict):
            return {}

        polymer_key = normalize_ir_polymer_name(self.polymer_name or getattr(config, "polymer_name", ""))
        if not polymer_key:
            return {}

        bands = polymer_db.get(polymer_key, [])
        if not isinstance(bands, list) or not bands:
            return {}

        normalized: list[dict[str, Any]] = []
        for band in bands:
            if not isinstance(band, (list, tuple)) or not band:
                continue
            wavenumber = self._safe_float(band[0])
            if wavenumber is None:
                continue
            item = {
                "wavenumber": wavenumber,
                "assignment": str(band[1] if len(band) > 1 else "",).strip() or None,
                "intensity": str(band[2] if len(band) > 2 else "",).strip() or None,
                "crystallinity_sensitive": bool(band[3]) if len(band) > 3 else False,
            }
            normalized.append({key: value for key, value in item.items() if value not in (None, "")})

        if not normalized:
            return {}

        return self._to_plain_value(
            {
                "polymer_name": polymer_key,
                "band_count": len(normalized),
                "bands": normalized,
                "source": "IRConfig.polymer_peaks_db",
            }
        )

    def _output_parameters(self, engine: Any) -> dict[str, Any]:
        if self.technique == "dsc":
            return self._dsc_output_parameters(engine)
        if self.technique == "saxs":
            return self._saxs_output_parameters(engine)
        if self.technique == "ir":
            return self._ir_output_parameters(engine)
        if self.technique == "nmr":
            return self._nmr_output_parameters(engine)
        output = dict(getattr(engine.result, "parameters", {}) or {})
        waxs_results = getattr(engine, "_results", []) or []
        if waxs_results:
            first = waxs_results[0]
            peaks = []
            for peak in getattr(first, "peaks", []) or []:
                item = {
                    "center": peak.get("two_theta"),
                    "fwhm": peak.get("fwhm_deg"),
                    "area": peak.get("area"),
                    "hkl": peak.get("hkl", ""),
                }
                peaks.append({k: self._to_plain_value(v) for k, v in item.items() if v is not None})
            if peaks:
                output["peaks"] = peaks
                output["peak_centers"] = [peak["center"] for peak in peaks if "center" in peak]
            two_theta = getattr(first, "two_theta", [])
            if len(two_theta) > 0:
                output["x_min"] = float(two_theta[0])
                output["x_max"] = float(two_theta[-1])
            if hasattr(first, "r_squared"):
                output["r_squared"] = self._safe_float(getattr(first, "r_squared"))
        return self._to_plain_value(output)

    def _dsc_output_parameters(self, engine: Any) -> dict[str, Any]:
        output = self._flatten_dsc_parameters(dict(getattr(engine.result, "parameters", {}) or {}))
        dsc_results = getattr(engine, "_results", []) or []
        if dsc_results:
            first = dsc_results[0]
            aggregate = aggregate_dsc_result_metrics(dsc_results)
            output.update(
                {
                    "scan_mode": getattr(first, "technique", None),
                    "Tg_C": getattr(first, "Tg_C", None),
                    "Tg_method": getattr(first, "Tg_method", None),
                    "DTg_C": getattr(first, "DTg_C", None),
                    "DCp_JgK": getattr(first, "DCp_JgK", None),
                    "Tm_onset_C": getattr(first, "Tm_onset_C", None),
                    "Tm_peak_C": getattr(first, "Tm_peak_C", None),
                    "Tm_end_C": getattr(first, "Tm_end_C", None),
                    "Tc_onset_C": getattr(first, "Tc_onset_C", None),
                    "Tc_peak_C": getattr(first, "Tc_peak_C", None),
                    "Tc_end_C": getattr(first, "Tc_end_C", None),
                    "Tcc_onset_C": getattr(first, "Tcc_onset_C", None),
                    "Tcc_peak_C": getattr(first, "Tcc_peak_C", None),
                    "DHm_Jg": getattr(first, "DHm_Jg", None),
                    "DHc_Jg": getattr(first, "DHc_Jg", None),
                    "DHcc_Jg": getattr(first, "DHcc_Jg", None),
                    "Xc_pct": getattr(first, "Xc_pct", None),
                    "quality_score": aggregate.get("quality_score"),
                    "r_squared": aggregate.get("r_squared"),
                    "fit_rmse": aggregate.get("fit_rmse"),
                    "scan_r_squared": aggregate.get("scan_r_squared"),
                    "r_squared_method": aggregate.get("r_squared_method"),
                    "n_peaks": len(getattr(first, "peak_components", []) or []),
                    "peak_components": getattr(first, "peak_components", []),
                }
            )
            output["tm"] = output.get("Tm_peak_C")
            output["tc"] = output.get("Tc_peak_C")
            if output["tc"] is None or self._is_nan(output["tc"]):
                output["tc"] = output.get("Tcc_peak_C")
            output["delta_hm"] = output.get("DHm_Jg")
            output["xc"] = output.get("Xc_pct")
            output["raw_score"] = output.get("quality_score")
            if len(getattr(first, "T", [])) > 0:
                output["x_min"] = float(first.T[0])
                output["x_max"] = float(first.T[-1])
        return self._to_plain_value({key: value for key, value in output.items() if value is not None})

    def _nmr_output_parameters(self, engine: Any) -> dict[str, Any]:
        output = self._flatten_nmr_parameters(dict(getattr(engine.result, "parameters", {}) or {}))
        if not output:
            output = self._flatten_nmr_parameters(dict(engine.get_parameters() or {}))
        nmr_results = getattr(engine, "_results", []) or []
        if nmr_results:
            first = nmr_results[0]
            peaks = []
            for peak in getattr(first, "peaks", []) or []:
                item = {
                    "ppm": peak.get("ppm"),
                    "height": peak.get("height"),
                    "area": peak.get("area"),
                    "fwhm_ppm": peak.get("fwhm_ppm"),
                    "assignment": peak.get("assignment", ""),
                    "region": peak.get("region", ""),
                    "snr": peak.get("snr"),
                }
                peaks.append({k: self._to_plain_value(v) for k, v in item.items() if v is not None})
            r_squared = self._safe_float(getattr(first, "r_squared", output.get("r_squared", 0.0)))
            median_snr = self._safe_float(getattr(first, "median_snr", output.get("median_snr", 0.0)))
            quality_score = r_squared if r_squared != 0.0 else max(0.0, min(1.0, median_snr / 20.0))
            output.update(
                {
                    "nucleus": getattr(first, "nucleus", output.get("nucleus")),
                    "sample_state": getattr(first, "sample_state", output.get("sample_state")),
                    "n_peaks": getattr(first, "n_peaks", output.get("n_peaks")),
                    "Xc_pct": getattr(first, "Xc_pct", output.get("Xc_pct")),
                    "xc": getattr(first, "Xc_pct", output.get("Xc_pct")),
                    "Xc_method": getattr(first, "Xc_method", output.get("Xc_method", "")),
                    "peak_area_total": getattr(first, "peak_area_total", output.get("peak_area_total")),
                    "dominant_peak_ppm": getattr(first, "dominant_peak_ppm", output.get("dominant_peak_ppm")),
                    "mean_fwhm_ppm": getattr(first, "mean_fwhm_ppm", output.get("mean_fwhm_ppm")),
                    "median_snr": getattr(first, "median_snr", output.get("median_snr")),
                    "r_squared": r_squared,
                    "quality_score": quality_score,
                    "raw_score": quality_score,
                    "r_squared_method": "nmr_peak_deconvolution_r2",
                }
            )
            if peaks:
                output["peaks"] = peaks
                output["peak_centers"] = [peak["ppm"] for peak in peaks if "ppm" in peak]
            ppm = getattr(first, "ppm", [])
            if len(ppm) > 0:
                output["x_min"] = float(np.nanmin(ppm))
                output["x_max"] = float(np.nanmax(ppm))
        return self._to_plain_value({key: value for key, value in output.items() if value is not None})

    def _ir_output_parameters(self, engine: Any) -> dict[str, Any]:
        output = self._flatten_ir_parameters(dict(getattr(engine.result, "parameters", {}) or {}))
        if not output:
            output = self._flatten_ir_parameters(dict(engine.get_parameters() or {}))
        ir_results = getattr(engine, "_results", []) or []
        if ir_results:
            first = ir_results[0]
            peaks = []
            for peak in getattr(first, "peaks", []) or []:
                item = {
                    "wavenumber": peak.get("wavenumber"),
                    "height": peak.get("height"),
                    "prominence": peak.get("prominence"),
                    "area": peak.get("area"),
                    "fwhm_cm1": peak.get("fwhm_cm1"),
                    "assignment": peak.get("assignment", ""),
                    "ref_wavenumber": peak.get("ref_wavenumber"),
                }
                peaks.append({k: self._to_plain_value(v) for k, v in item.items() if v is not None})

            r_squared = self._safe_float(getattr(first, "r_squared", output.get("r_squared", 0.0)))
            polymer_score = self._safe_float(getattr(first, "polymer_score", output.get("polymer_score", 1.0)))
            if polymer_score == 0.0 and getattr(first, "polymer_name", ""):
                polymer_score = 1.0
            output.update(
                {
                    "n_peaks": getattr(first, "n_peaks", output.get("n_peaks")),
                    "polymer_name": getattr(first, "polymer_name", output.get("polymer")),
                    "polymer_score": polymer_score,
                    "quality_score": polymer_score,
                    "raw_score": polymer_score,
                    "Xc_pct": getattr(first, "Xc_pct", output.get("Xc_pct")),
                    "xc": getattr(first, "Xc_pct", output.get("Xc_pct")),
                    "Xc_method": getattr(first, "Xc_method", output.get("Xc_method", "")),
                    "r_squared": r_squared,
                    "r_squared_method": "ir_peak_region_fit_r2",
                }
            )
            if peaks:
                output["peaks"] = peaks
                output["peak_centers"] = [peak["wavenumber"] for peak in peaks if "wavenumber" in peak]
            wn = getattr(first, "wavenumber", [])
            if len(wn) > 0:
                output["x_min"] = float(np.nanmin(wn))
                output["x_max"] = float(np.nanmax(wn))
        return self._to_plain_value({key: value for key, value in output.items() if value is not None})

    def _saxs_output_parameters(self, engine: Any) -> dict[str, Any]:
        output = dict(getattr(engine.result, "parameters", {}) or {})
        if not output:
            output = dict(engine.get_parameters() or {})
        analysis = getattr(engine, "_analysis", None)
        batch_results = getattr(engine, "_batch_results", []) or []
        if analysis is None and batch_results:
            analysis = batch_results[0]

        quality_score = self._saxs_score(analysis, output)
        r_squared = self._safe_float(getattr(analysis, "r_squared", None)) if analysis is not None else 0.0
        if analysis is None or not math.isfinite(r_squared):
            r_squared = quality_score
        output["r_squared"] = r_squared
        output["quality_score"] = self._safe_float(getattr(analysis, "quality_score", quality_score)) if analysis is not None else quality_score
        output["raw_score"] = output["quality_score"]
        output["r_squared_method"] = getattr(analysis, "r_squared_method", "") or "saxs_peak_region_fit_r2"
        output["fit_rmse"] = getattr(analysis, "fit_rmse", None) if analysis is not None else None
        output["fit_regions"] = getattr(analysis, "fit_regions", None) if analysis is not None else None
        if "Xc" in output and "Xc_pct" not in output:
            xc = self._safe_float(output.get("Xc"))
            output["Xc_pct"] = xc * 100.0 if 0.0 <= xc <= 1.0 else xc
            output["xc"] = output["Xc_pct"]
        if analysis is not None:
            q = getattr(analysis, "q", [])
            if len(q) > 0:
                output["x_min"] = float(q[0])
                output["x_max"] = float(q[-1])
            condition_value = getattr(analysis, "condition_value", None)
            if condition_value is not None:
                output["condition_value"] = condition_value
            lp = getattr(analysis, "long_period", None)
            if lp is not None:
                output["L_confidence"] = getattr(lp, "L_confidence", None)
                output["L_bragg"] = getattr(lp, "L_bragg", None)
                output["L_lorentz"] = getattr(lp, "L_lorentz", None)
                output["L_corr_peak"] = getattr(lp, "L_corr_peak", None)
            output["q_peak_snr"] = getattr(analysis, "q_peak_snr", None)
            output["quality_flag"] = getattr(analysis, "quality_flag", "")
            output["validation_summary"] = getattr(analysis, "validation_summary", "")
        return self._to_plain_value({key: value for key, value in output.items() if value is not None})

    def _saxs_score(self, analysis: Any, output: dict[str, Any]) -> float:
        sas_r2 = self._safe_float(output.get("sasmodels_R2"))
        if math.isfinite(sas_r2) and sas_r2 > 0:
            return max(0.0, min(1.0, sas_r2))
        if analysis is not None:
            lp = getattr(analysis, "long_period", None)
            confidence = self._safe_float(getattr(lp, "L_confidence", 0.0)) if lp is not None else 0.0
            if confidence > 0:
                return max(0.0, min(1.0, confidence))
        snr = self._safe_float(output.get("q_peak_snr"))
        if snr > 0:
            return max(0.0, min(1.0, snr / 20.0))
        return 0.0

    def _residual_pattern(self, engine: Any) -> dict[str, Any]:
        if self.technique == "dsc":
            return self._dsc_residual_pattern(engine)
        if self.technique == "saxs":
            return self._saxs_residual_pattern(engine)
        if self.technique == "ir":
            return self._ir_residual_pattern(engine)
        if self.technique == "nmr":
            return self._nmr_residual_pattern(engine)
        waxs_results = getattr(engine, "_results", []) or []
        if not waxs_results:
            return self._empty_residual_pattern().to_dict()
        first = waxs_results[0]
        y_obs = getattr(first, "I", [])
        y_fit = getattr(first, "I_fit", [])
        two_theta = getattr(first, "two_theta", [])
        if len(y_obs) == 0 or len(y_fit) == 0 or len(two_theta) == 0:
            return self._empty_residual_pattern().to_dict()
        context = {
            "output_parameters": self._output_parameters(engine),
            "config_snapshot": self._config_snapshot(engine),
        }
        return WAXSResidualAnalyzer.analyze(y_obs, y_fit, two_theta, context=context).to_dict()

    def _dsc_residual_pattern(self, engine: Any) -> dict[str, Any]:
        dsc_results = getattr(engine, "_results", []) or []
        if not dsc_results:
            return DSCResidualPattern(
                rmse=0.0,
                r_squared=0.0,
                residual_type="random",
                max_residual_region="unknown",
                peak_regions=[],
                summary="DSC 残差数据不足，无法判断残差模式。",
            ).to_dict()
        result = self._select_dsc_residual_result(dsc_results)
        fit = getattr(result, "HF_fit", [])
        if len(fit) == len(getattr(result, "HF", [])):
            return DSCResidualAnalyzer.analyze(getattr(result, "T", []), getattr(result, "HF", []), fit).to_dict()
        return DSCResidualAnalyzer.analyze(getattr(result, "T", []), getattr(result, "HF", [])).to_dict()

    def _saxs_residual_pattern(self, engine: Any) -> dict[str, Any]:
        analysis = getattr(engine, "_analysis", None)
        batch_results = getattr(engine, "_batch_results", []) or []
        if analysis is None and batch_results:
            analysis = batch_results[0]
        if analysis is None:
            return SAXSResidualPattern(
                rmse=0.0,
                r_squared=0.0,
                residual_type="random",
                max_residual_region="unknown",
                peak_regions=[],
                summary="SAXS 残差数据不足，无法判断残差模式。",
            ).to_dict()
        q = getattr(analysis, "q", [])
        intensity = getattr(analysis, "I", [])
        fit = getattr(analysis, "I_smooth", None)
        return SAXSResidualAnalyzer.analyze(q, intensity, fit).to_dict()

    def _ir_residual_pattern(self, engine: Any) -> dict[str, Any]:
        ir_results = getattr(engine, "_results", []) or []
        if not ir_results:
            return IRResidualPattern(
                rmse=0.0,
                r_squared=0.0,
                residual_type="random",
                max_residual_region="unknown",
                peak_regions=[],
                summary="IR residual data is insufficient for pattern classification.",
            ).to_dict()
        first = ir_results[0]
        return IRResidualAnalyzer.analyze(
            getattr(first, "wavenumber", []),
            getattr(first, "absorbance", []),
            getattr(first, "absorbance_fit", None),
        ).to_dict()

    def _nmr_residual_pattern(self, engine: Any) -> dict[str, Any]:
        nmr_results = getattr(engine, "_results", []) or []
        if not nmr_results:
            return {
                "rmse": 0.0,
                "r_squared": 0.0,
                "residual_type": "random",
                "max_residual_region": "unknown",
                "peak_regions": [],
                "summary": "NMR residual data is insufficient for pattern classification.",
            }
        first = nmr_results[0]
        ppm = np.asarray(getattr(first, "ppm", []), dtype=float)
        y = np.asarray(getattr(first, "intensity", []), dtype=float)
        fit = np.asarray(getattr(first, "intensity_fit", []), dtype=float)
        if len(ppm) == 0 or len(y) == 0 or len(fit) != len(y):
            region = "unknown"
            residual_type = "random"
            rmse = 0.0
            r_squared = self._safe_float(getattr(first, "r_squared", 0.0))
            summary = "NMR fit residual array is unavailable; use peak metrics and SNR as the tuning context."
        else:
            residuals = y - fit
            rmse = float(np.sqrt(np.mean(residuals**2)))
            ss_res = float(np.sum(residuals**2))
            ss_tot = float(np.sum((y - np.mean(y)) ** 2))
            r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
            max_idx = int(np.argmax(np.abs(residuals)))
            region = f"{float(ppm[max_idx]):.2f} ppm"
            if rmse > 0 and np.nanmedian(np.abs(np.diff(residuals))) > rmse * 0.7:
                residual_type = "noise"
            elif rmse > 0 and abs(float(residuals[max_idx])) > rmse * 2.0:
                residual_type = "peak_mismatch"
            else:
                residual_type = "random"
            summary = (
                f"NMR residual maximum near {region}; RMSE={rmse:.4g}, "
                f"residual_type={residual_type}. Tune peak_height_min, peak_distance_ppm, "
                "deconvolution_method, baseline_method, or apodization parameters."
            )
        return {
            "rmse": rmse,
            "r_squared": float(r_squared),
            "residual_type": residual_type,
            "max_residual_region": region,
            "peak_regions": [],
            "summary": summary,
        }

    def _select_dsc_residual_result(self, dsc_results: list[Any]) -> Any:
        meaningful = []
        for result in dsc_results:
            r_squared = self._safe_float(getattr(result, "r_squared", 0.0))
            if len(getattr(result, "fit_regions", []) or []) > 0 and r_squared != 0.0:
                meaningful.append((r_squared, result))
        if meaningful:
            return min(meaningful, key=lambda item: item[0])[1]
        return dsc_results[0]

    def _empty_residual_pattern(self) -> ResidualPattern:
        return ResidualPattern(
            rmse=0.0,
            r_squared=0.0,
            residual_type="random",
            max_residual_region="unknown",
            peak_regions=[],
            summary="残差数据不足，无法判断残差模式。",
        )

    def _tunable_params(self, config: dict[str, Any], allowed_actions: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        if self.technique == "dsc":
            param_map = DSC_PARAM_MAP
        elif self.technique == "saxs":
            param_map = SAXS_PARAM_MAP
        elif self.technique == "ir":
            param_map = IR_PARAM_MAP
        elif self.technique == "nmr":
            param_map = NMR_PARAM_MAP
        else:
            param_map = WAXS_PARAM_MAP
        goal_focus = self._goal_tuning_focus()
        joint_focus = self._joint_tuning_focus()
        allowed_by_param: dict[str, list[str]] = {}
        for action in allowed_actions or []:
            if not isinstance(action, dict):
                continue
            action_name = str(action.get("name", "") or "").strip()
            for param_name in action.get("allowed_params", []):
                key = str(param_name or "").strip()
                if not key:
                    continue
                bucket = allowed_by_param.setdefault(key, [])
                if action_name and action_name not in bucket:
                    bucket.append(action_name)
        params = []
        for order, (name, rule) in enumerate(param_map.items()):
            goal = goal_focus.get(name, {})
            focus = joint_focus.get(name, {})
            goal_priority = int(goal.get("priority", 0) or 0)
            joint_priority = int(focus.get("priority", 0) or 0)
            params.append(
                {
                    "_order": order,
                    "name": name,
                    "config_field": rule.field_name,
                    "current_value": config.get(rule.field_name),
                    "constraint": list(rule.constraint),
                    "type": rule.value_type.__name__,
                    "goal_priority": goal_priority,
                    "goal_priority_reason": " | ".join(goal.get("reasons", [])),
                    "goal_priority_goals": list(goal.get("goals", [])),
                    "joint_priority": joint_priority,
                    "joint_priority_reason": " | ".join(focus.get("reasons", [])),
                    "joint_priority_families": list(focus.get("families", [])),
                    "allowed_actions": list(allowed_by_param.get(name, [])),
                    "action_guarded": bool(allowed_by_param.get(name)),
                }
            )
        params.sort(
            key=lambda item: (
                -int(item.get("joint_priority", 0) or 0),
                -int(item.get("goal_priority", 0) or 0),
                int(item.get("_order", 0) or 0),
            )
        )
        for item in params:
            item.pop("_order", None)
        return params

    def _goal_tuning_focus(self) -> dict[str, dict[str, Any]]:
        workspace_context = self.workspace_context if isinstance(self.workspace_context, dict) else {}
        goal_key = str(workspace_context.get("tuning_goal") or "").strip().lower()
        if goal_key not in {"symptom", "risk", "joint", "stability"}:
            goal_key = "symptom"
        technique_rules = GOAL_TUNING_PRIORITY_RULES.get(self.technique.upper(), {})
        goal_rules = technique_rules.get(goal_key, [])
        focus: dict[str, dict[str, Any]] = {}
        for rank, item in enumerate(goal_rules):
            if not isinstance(item, tuple) or len(item) != 2:
                continue
            param_name, reason = item
            param_name = str(param_name or "").strip()
            reason = str(reason or "").strip()
            if not param_name:
                continue
            entry = focus.setdefault(param_name, {"priority": 0, "reasons": [], "goals": []})
            entry["priority"] += max(1, 4 - rank)
            if reason and reason not in entry["reasons"]:
                entry["reasons"].append(reason)
            if goal_key and goal_key not in entry["goals"]:
                entry["goals"].append(goal_key)
        return focus

    def _joint_tuning_focus(self) -> dict[str, dict[str, Any]]:
        joint_ai_context = self._joint_ai_context()
        issue_families = joint_ai_context.get("issue_families")
        if not isinstance(issue_families, list) or not issue_families:
            return {}

        technique_rules = JOINT_TUNING_PRIORITY_RULES.get(self.technique.upper(), {})
        focus: dict[str, dict[str, Any]] = {}
        for family in issue_families:
            family_label = str(family or "").strip()
            family_key = family_label.lower()
            if not family_key:
                continue
            for rank, item in enumerate(technique_rules.get(family_key, [])):
                if not isinstance(item, tuple) or len(item) != 2:
                    continue
                param_name, reason = item
                param_name = str(param_name or "").strip()
                reason = str(reason or "").strip()
                if not param_name:
                    continue
                entry = focus.setdefault(param_name, {"priority": 0, "reasons": [], "families": []})
                entry["priority"] += max(1, 4 - rank)
                if reason and reason not in entry["reasons"]:
                    entry["reasons"].append(reason)
                if family_label and family_label not in entry["families"]:
                    entry["families"].append(family_label)
        return focus

    def _engine_config(self, engine: Any) -> Any:
        if self.technique == "dsc":
            return getattr(engine, "_dsc_config", None)
        if self.technique == "saxs":
            return getattr(engine, "cfg", None)
        if self.technique == "ir":
            return getattr(engine, "_ir_config", None)
        if self.technique == "nmr":
            return getattr(engine, "_cfg", None)
        return getattr(engine, "_waxs_config", None)

    def _submodule_id(self) -> str:
        if self.submodule_override:
            return self._canonical_submodule_id(self.submodule_override)
        if self.technique == "dsc":
            return "dsc.standard"
        if self.technique == "saxs":
            return "saxs.static"
        if self.technique == "ir":
            if self._engine is not None:
                active_submodule = str(getattr(self._engine, "active_submodule", "") or "").strip()
                if active_submodule:
                    return self._canonical_submodule_id(active_submodule)
            return "ir.standard"
        if self.technique == "nmr":
            return self._nmr_submodule_id()
        if self.technique == "waxs":
            return self._waxs_submodule_id()
        return "waxs.static"

    def _submodule_name(self) -> str:
        if self.technique == "ir":
            submodule_id = self._submodule_id()
            if submodule_id == "ir.temperature_2d":
                return "temperature_2d"
            return "standard"
        if self.technique == "dsc":
            return "standard"
        if self.technique == "nmr":
            return self._nmr_submodule_id().split(".", 1)[1]
        if self.technique == "waxs":
            return self._public_submodule().split(".", 1)[1]
        return "static"

    def _public_submodule(self) -> str:
        submodule_id = self._submodule_id()
        if self.technique == "waxs":
            mapping = {
                "waxs.temperature": "waxs.in_situ_temp",
                "waxs.strain": "waxs.in_situ_stretch",
                "waxs.static": "waxs.static",
            }
            return mapping.get(submodule_id, submodule_id)
        if self.technique == "nmr":
            return submodule_id
        if self.technique == "ir":
            if submodule_id == "ir.temperature_2d":
                return submodule_id
            return "standard"
        if self.technique == "dsc":
            return "standard"
        return submodule_id

    def _agent_state_submodule(self) -> str:
        if self.technique == "ir":
            submodule_id = self._submodule_id()
            if submodule_id == "ir.temperature_2d":
                return submodule_id
            return "standard"
        if self.technique == "dsc":
            return "standard"
        return self._public_submodule()

    def _canonical_submodule_id(self, submodule: str) -> str:
        if self.technique == "waxs":
            mapping = {
                "waxs.in_situ_temp": "waxs.temperature",
                "waxs.in_situ_stretch": "waxs.strain",
                "waxs.static": "waxs.static",
            }
            return mapping.get(submodule, submodule)
        return submodule

    def _waxs_submodule_id(self) -> str:
        text = self.data_file.replace("\\", "/")
        if "原位变温广角" in text:
            return "waxs.temperature"
        if "原位拉伸广角" in text:
            return "waxs.strain"
        return "waxs.static"

    def _nmr_submodule_id(self) -> str:
        text = self.data_file.lower().replace("\\", "/")
        if "液体" in text or "liquid" in text:
            return "nmr.liquid_h" if ("h谱" in text or "proton" in text) else "nmr.liquid_c"
        if "固体" in text or "solid" in text:
            return "nmr.solid_h" if ("氢谱" in text or "single_pulse" in text or "_h_" in text) else "nmr.solid_c"
        if "proton" in text or "_h_" in text or "-h_" in text:
            return "nmr.liquid_h"
        if "carbon" in text or "13c" in text or "_c_" in text or "-c_" in text:
            return "nmr.liquid_c"
        return "nmr.solid_c"

    def _flatten_dsc_parameters(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not payload:
            return {}
        preserved_keys = ("quality_flag", "quality_flags", "validation_summary", "validation_warnings")
        preserved = {key: payload[key] for key in preserved_keys if key in payload}
        if any(key in payload for key in ("Tm_peak_C", "Tc_peak_C", "Xc_pct")):
            if preserved:
                flat = dict(payload)
                flat.update(preserved)
                return flat
            return payload
        for value in payload.values():
            if isinstance(value, dict) and any(key in value for key in ("Tm_peak_C", "Tc_peak_C", "Xc_pct")):
                flat = dict(value)
                flat.update(preserved)
                return flat
        if preserved:
            merged = dict(payload)
            merged.update(preserved)
            return merged
        return payload

    def _flatten_ir_parameters(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not payload:
            return {}
        if any(key in payload for key in ("n_peaks", "polymer_score", "r_squared")):
            return payload
        for value in payload.values():
            if isinstance(value, dict) and any(key in value for key in ("n_peaks", "polymer_score", "r_squared")):
                return dict(value)
        return payload

    def _flatten_nmr_parameters(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not payload:
            return {}
        if any(key in payload for key in ("n_peaks", "dominant_peak_ppm", "r_squared")):
            return payload
        for value in payload.values():
            if isinstance(value, dict) and any(key in value for key in ("n_peaks", "dominant_peak_ppm", "r_squared")):
                return dict(value)
        return payload

    def _is_nan(self, value: Any) -> bool:
        try:
            return bool(value != value)
        except Exception:
            return False
            logger.warning("异常已处理", exc_info=True)

    def _safe_float(self, value: Any) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0.0
        return number if math.isfinite(number) else 0.0

    def _to_plain_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): self._to_plain_value(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._to_plain_value(item) for item in value]
        if hasattr(value, "item"):
            return value.item()
        return value

    def _stable_signature(self, value: Any) -> str:
        try:
            return json.dumps(self._to_plain_value(value), sort_keys=True, ensure_ascii=False, default=str)
        except Exception:
            return repr(self._to_plain_value(value))


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
