from __future__ import annotations

import time
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

import math
import numpy as np

from polynexus import __version__

from polynexus.config_bridge import apply_changes
from polynexus.core.preprocess_optimization import (
    AnalysisSnapshot,
    ContractValidationError,
    DecisionRecord,
    ExperienceKey,
    PreprocessCandidate,
    PreprocessEvidence,
    build_preprocess_replay_audit,
    decide_preprocess_candidate,
    generate_preprocess_candidates,
    get_preprocess_adapter,
    get_preprocess_policy,
    parse_preprocess_intent,
    stable_config_hash,
)
from polynexus.core.preprocess_optimization.contracts import SCHEMA_VERSION
from polynexus.core.preprocess_optimization.policy import PolicyValidationError
from polynexus.core.saxs_engine.saxs_ai_rescue import (
    SAXSAIRescueDecision,
    SAXSAIRescuePlan,
    assess_saxs_ai_candidate,
    validate_saxs_ai_intent,
)


def _metadata_complete(self: Any) -> bool:
    context = self.workspace_context if isinstance(self.workspace_context, dict) else {}
    return bool(
        str(context.get("instrument_fingerprint", "") or "").strip()
        and str(context.get("sample_family", "") or "").strip()
    )


def _saxs_replay_mode(engine: Any) -> str:
    if getattr(engine, "_temperature_result", None) is not None:
        return "temperature"
    if getattr(engine, "_strain_result", None) is not None:
        return "strain"
    experiment_type = str(
        getattr(getattr(engine, "cfg", None), "experiment_type", "") or ""
    ).strip().lower()
    if experiment_type in {"temperature", "cooling", "heating", "isothermal"}:
        return "temperature"
    if experiment_type == "strain":
        return "strain"
    return "static"


def _saxs_replay_context(self: Any) -> dict[str, Any]:
    workspace = self.workspace_context if isinstance(self.workspace_context, dict) else {}
    allowed = ("condition_context", "condition_values", "sample", "batch")
    return {
        key: deepcopy(workspace[key])
        for key in allowed
        if key in workspace and workspace[key] not in (None, "", {}, [])
    }


def _core_major_version() -> str:
    return str(__version__).split(".", 1)[0]


def _experience_context(self: Any, technique: str) -> tuple[dict[str, Any], list[Any]]:
    result = {
        "metadata_complete": _metadata_complete(self),
        "retrieval_used": False,
        "matched_ids": [],
        "scope": {},
        "error": "",
    }
    if not result["metadata_complete"]:
        return result, []
    context = self.workspace_context if isinstance(self.workspace_context, dict) else {}
    key = ExperienceKey(
        technique=technique,
        instrument_fingerprint=str(context["instrument_fingerprint"]),
        sample_family=str(context["sample_family"]),
        schema_version=SCHEMA_VERSION,
        core_major_version=_core_major_version(),
    )
    result["scope"] = {
        "technique": key.technique,
        "instrument_fingerprint": key.instrument_fingerprint,
        "sample_family": key.sample_family,
        "schema_version": key.schema_version,
        "core_major_version": key.core_major_version,
    }
    store = getattr(self, "preprocess_experience_store", None)
    if store is None:
        return result, []
    try:
        records = list(store.retrieve(key))
    except Exception as exc:
        result["error"] = str(exc)
        return result, []
    result["retrieval_used"] = bool(records)
    result["matched_ids"] = [record.experience_id for record in records]
    return result, records


def _append_decision_audit(
    self: Any,
    report: dict[str, Any],
    *,
    original_hash: str,
    prompt: str,
) -> bool:
    decision = report["preprocess_decision"]
    policy = report["preprocess_policy"]
    model_settings = getattr(self, "llm_settings", {})
    model_id = ""
    if isinstance(model_settings, dict):
        model_id = str(model_settings.get("model", model_settings.get("model_id", "")) or "")
    record = DecisionRecord(
        schema_version=SCHEMA_VERSION,
        analysis_id=str(report.get("preprocess_intent", {}).get("analysis_id", "invalid")),
        original_config_hash=original_hash,
        selected_candidate_id=report.get("selected_candidate_id"),
        decision=str(decision.get("decision", "keep_original")),
        confidence_band=str(decision.get("confidence_band", "low")),
        score_components=dict(decision.get("score_components", {})),
        hard_guard_results=dict(decision.get("hard_guard_results", {})),
        evidence_refs=tuple(
            str(item.get("candidate_id", ""))
            for item in report.get("preprocess_evidence", [])
            if isinstance(item, dict) and item.get("candidate_id")
        ),
        policy_version=str(policy.get("version", "")),
        core_version=__version__,
        model_id=model_id,
        prompt_version="preprocess-intent-v1",
        reason_codes=tuple(str(item) for item in decision.get("reason_codes", [])),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    report["decision_record"] = record.to_dict()
    report["prompt_hash_source_present"] = bool(prompt)
    audit = getattr(self, "preprocess_audit_log", None)
    if audit is None:
        report["audit_status"] = "not_configured"
        return True
    try:
        audit.append(record)
    except Exception as exc:
        report["audit_status"] = "failed"
        report["audit_error"] = str(exc)
        reason_codes = list(decision.get("reason_codes", []))
        reason_codes.append("audit_write_failed")
        decision.update(
            {
                "decision": "keep_original",
                "confidence_band": "low",
                "reason_codes": list(dict.fromkeys(reason_codes)),
            }
        )
        failed_record = record.to_dict()
        failed_record.update(
            {
                "decision": "keep_original",
                "confidence_band": "low",
                "reason_codes": list(decision["reason_codes"]),
            }
        )
        report["decision_record"] = failed_record
        return False
    report["audit_status"] = "appended"
    return True


def _experience_proposal(
    report: dict[str, Any],
    selected: dict[str, Any],
) -> dict[str, Any]:
    scope = report.get("preprocess_experience", {}).get("scope", {})
    if not scope:
        return {}
    decision = report["preprocess_decision"]["decision"]
    if decision not in {"auto_accept", "request_confirmation"}:
        return {}
    candidate = selected["candidate"]
    return {
        "experience_id": f"preprocess-{candidate.candidate_id}",
        "key": deepcopy(scope),
        "config_delta": deepcopy(candidate.config_delta),
        "accepted_by": "auto_accept" if decision == "auto_accept" else "pending_user",
        "evidence_summary": selected["evidence"].to_dict(),
        "intent_summary": deepcopy(report["preprocess_intent"]),
        "symptom_names": list(report["preprocess_intent"].get("target_symptoms", [])),
    }


def _replace_engine_config(self: Any, engine: Any, config: Any) -> None:
    if self.technique == "dsc":
        engine._dsc_config = deepcopy(config)
    elif self.technique == "saxs":
        engine.cfg = deepcopy(config)
    elif self.technique == "ir":
        engine._ir_config = deepcopy(config)
    elif self.technique == "nmr":
        engine._cfg = deepcopy(config)
    else:
        engine._waxs_config = deepcopy(config)


def _new_trial_engine(self: Any, source_engine: Any, config: Any) -> Any:
    factory = getattr(self, "_create_preprocess_engine", None)
    if callable(factory):
        return factory(deepcopy(config))

    from polynexus.core import get_engine

    submodule_id = None
    resolver = getattr(self, "_submodule_id", None)
    if callable(resolver):
        submodule_id = resolver()
    trial = get_engine(
        self.technique,
        config=deepcopy(config),
        submodule_id=submodule_id,
    )
    if trial is not None:
        return trial

    trial = deepcopy(source_engine)
    _replace_engine_config(self, trial, config)
    return trial


def _run_trial_pipeline(self: Any, engine: Any) -> tuple[bool, str]:
    started = time.monotonic()
    try:
        runner = getattr(engine, "run_pipeline", None)
        if callable(runner):
            runner(str(self.data_file), output_dir="")
        else:
            preprocess = getattr(engine, "preprocess", None)
            if callable(preprocess) and not preprocess():
                return False, "engine.preprocess() failed"
            analyze = getattr(engine, "analyze", None)
            if not callable(analyze) or not analyze():
                return False, "engine.analyze() failed"
            result = getattr(engine, "result", None)
            get_parameters = getattr(engine, "get_parameters", None)
            if result is not None and callable(get_parameters):
                result.parameters = get_parameters()
    except Exception as exc:
        return False, f"Core rerun failed: {exc}"

    policy = getattr(self, "preprocess_policy", None)
    timeout = float(getattr(policy, "candidate_timeout_s", 120.0) or 120.0)
    if time.monotonic() - started > timeout:
        return False, "candidate_timeout"
    try:
        output = self._output_parameters(engine)
    except Exception as exc:
        return False, f"Core output extraction failed: {exc}"
    if not isinstance(output, dict) or not output:
        return False, "Core rerun produced no output"
    return True, ""


def _saxs_peak_shape(
    q_values: Any,
    intensity_values: Any,
    q_peak: float,
) -> tuple[float | None, float | None]:
    try:
        q = np.asarray(q_values, dtype=float).reshape(-1)
        intensity = np.asarray(intensity_values, dtype=float).reshape(-1)
    except (TypeError, ValueError):
        return None, None
    if q.size != intensity.size or q.size < 5:
        return None, None
    finite = np.isfinite(q) & np.isfinite(intensity)
    q = q[finite]
    intensity = intensity[finite]
    if q.size < 5:
        return None, None
    order = np.argsort(q)
    q = q[order]
    intensity = intensity[order]
    center_index = int(np.argmin(np.abs(q - q_peak)))
    baseline = float(np.quantile(intensity, 0.10))
    peak_height = float(intensity[center_index] - baseline)
    if not math.isfinite(peak_height) or peak_height <= 0.0:
        return None, None
    half_height = baseline + 0.5 * peak_height
    left = center_index
    while left > 0 and intensity[left] > half_height:
        left -= 1
    right = center_index
    while right < q.size - 1 and intensity[right] > half_height:
        right += 1
    if left >= center_index or right <= center_index:
        return None, None
    fwhm = float(q[right] - q[left])
    area = float(
        np.trapezoid(
            np.maximum(intensity[left : right + 1] - baseline, 0.0),
            q[left : right + 1],
        )
    )
    return fwhm, area


def _enrich_preprocess_output(self: Any, engine: Any, output: dict[str, Any]) -> dict[str, Any]:
    if str(getattr(self, "technique", "") or "").strip().lower() != "saxs":
        return output
    enriched = deepcopy(output)
    analysis = getattr(engine, "_analysis", None)
    structure = getattr(analysis, "structure", None) if analysis is not None else None
    if "Q_invariant" not in enriched:
        invariant = enriched.get("Q_star")
        if invariant is None and structure is not None:
            invariant = getattr(structure, "Q_invariant", None)
        if invariant is not None:
            enriched["Q_invariant"] = invariant
    if "Rg" not in enriched and structure is not None:
        rg = getattr(structure, "Rg", None)
        if rg is not None:
            enriched["Rg"] = rg
    q_peak = enriched.get("q_peak")
    if q_peak is None:
        try:
            length = float(enriched.get("L_bragg"))
            q_peak = 2.0 * math.pi / length if length > 0.0 else None
        except (TypeError, ValueError):
            q_peak = None
    try:
        q_peak_number = float(q_peak)
    except (TypeError, ValueError):
        q_peak_number = math.nan
    if math.isfinite(q_peak_number):
        enriched["q_peak"] = q_peak_number
        q = getattr(analysis, "q", None) if analysis is not None else None
        intensity = getattr(analysis, "I_smooth", None) if analysis is not None else None
        if intensity is None and analysis is not None:
            intensity = getattr(analysis, "I", None)
        fwhm, area = _saxs_peak_shape(q, intensity, q_peak_number)
        if fwhm is not None:
            enriched["q_peak_fwhm"] = fwhm
        if area is not None:
            enriched["q_peak_area"] = area
    return enriched


def _processed_signal_negative_fraction(self: Any, engine: Any) -> float | None:
    technique = str(getattr(self, "technique", "") or "").strip().lower()
    if technique == "dsc":
        return 0.0
    values: Any = None
    if technique == "saxs":
        values = getattr(engine, "_I_smooth", None)
        if values is None:
            values = getattr(engine, "_I", None)
    else:
        results = getattr(engine, "_results", []) or []
        if results:
            first = results[0]
            attribute = {"ir": "absorbance", "nmr": "intensity", "waxs": "I"}.get(
                technique, ""
            )
            if attribute:
                values = getattr(first, attribute, None)
    if values is None:
        return None
    try:
        signal = np.asarray(values, dtype=float).reshape(-1)
    except (TypeError, ValueError):
        return None
    signal = signal[np.isfinite(signal)]
    if signal.size == 0:
        return None
    scale = float(np.max(np.abs(signal)))
    if scale <= 0.0:
        return 0.0
    return float(np.mean(signal < (-0.05 * scale)))


def _snapshot_for_preprocess(self: Any, engine: Any) -> AnalysisSnapshot:
    output = _enrich_preprocess_output(self, engine, self._output_parameters(engine))
    residual = self._residual_pattern(engine)
    evidence = self._analysis_evidence(output, residual)
    result = getattr(engine, "result", None)
    metadata = getattr(result, "metadata", {})
    if isinstance(metadata, dict):
        runtime_keys = (
            "background_status",
            "background_source",
            "background_scale_method",
            "background_scale_applied",
            "background_negative_fraction_before",
            "background_negative_fraction_after_raw",
        )
        runtime = {key: deepcopy(metadata[key]) for key in runtime_keys if key in metadata}
        if runtime:
            evidence = deepcopy(evidence)
            evidence["preprocess_runtime"] = runtime
        if "negative_fraction" not in output:
            try:
                negative_fraction = float(metadata["background_negative_fraction_after_raw"])
            except (KeyError, TypeError, ValueError):
                negative_fraction = math.nan
            if math.isfinite(negative_fraction):
                output = deepcopy(output)
                output["negative_fraction"] = negative_fraction
    if "negative_fraction" not in output:
        derived_negative_fraction = _processed_signal_negative_fraction(self, engine)
        if derived_negative_fraction is not None:
            output = deepcopy(output)
            output["negative_fraction"] = derived_negative_fraction
    return AnalysisSnapshot.from_parts(
        config=self._config_to_dict(self._engine_config(engine)),
        output_parameters=output,
        residual_pattern=residual,
        analysis_evidence=evidence,
    )


def _failed_evidence(candidate_id: str, error: str) -> PreprocessEvidence:
    return PreprocessEvidence(
        schema_version=SCHEMA_VERSION,
        candidate_id=candidate_id,
        run_status="failed",
        evidence_coverage=0.0,
        warnings=(error,),
    )


def _execute_preprocess_candidate(
    self: Any,
    engine: Any,
    candidate: PreprocessCandidate,
    previous_record: Any = None,
    prompt: str = "",
) -> dict[str, Any]:
    del previous_record, prompt
    policy = getattr(self, "preprocess_policy", None) or get_preprocess_policy(
        candidate.technique
    )
    adapter = get_preprocess_adapter(candidate.technique)
    base_config_object = deepcopy(self._engine_config(engine))
    base_config = self._config_to_dict(base_config_object)
    if stable_config_hash(base_config) != candidate.base_config_hash:
        evidence = _failed_evidence(candidate.candidate_id, "config_hash_changed")
        decision = decide_preprocess_candidate(
            evidence,
            policy,
            candidate_margin=0.0,
            metadata_complete=_metadata_complete(self),
        )
        return {
            "candidate": candidate,
            "snapshot": None,
            "evidence": evidence,
            "decision": decision,
            "effective_config": {},
            "effective_config_object": None,
            "engine": None,
            "error": "config_hash_changed",
        }

    effective_config_object = deepcopy(base_config_object)
    ok, error = apply_changes(
        effective_config_object,
        candidate.config_delta,
        technique=self.technique,
    )
    if not ok:
        evidence = _failed_evidence(candidate.candidate_id, error)
        decision = decide_preprocess_candidate(
            evidence,
            policy,
            candidate_margin=0.0,
            metadata_complete=_metadata_complete(self),
        )
        return {
            "candidate": candidate,
            "snapshot": None,
            "evidence": evidence,
            "decision": decision,
            "effective_config": {},
            "effective_config_object": None,
            "engine": None,
            "error": error,
        }

    trial_engine = _new_trial_engine(self, engine, effective_config_object)
    ok, error = _run_trial_pipeline(self, trial_engine)
    if not ok:
        evidence = _failed_evidence(candidate.candidate_id, error)
        decision = decide_preprocess_candidate(
            evidence,
            policy,
            candidate_margin=0.0,
            metadata_complete=_metadata_complete(self),
        )
        return {
            "candidate": candidate,
            "snapshot": None,
            "evidence": evidence,
            "decision": decision,
            "effective_config": self._config_to_dict(effective_config_object),
            "effective_config_object": effective_config_object,
            "engine": trial_engine,
            "error": error,
        }

    control = _snapshot_for_preprocess(self, engine)
    snapshot = _snapshot_for_preprocess(self, trial_engine)
    evidence = adapter.build_evidence(candidate.candidate_id, control, snapshot)
    decision = decide_preprocess_candidate(
        evidence,
        policy,
        candidate_margin=0.0,
        metadata_complete=_metadata_complete(self),
    )
    return {
        "candidate": candidate,
        "snapshot": snapshot,
        "evidence": evidence,
        "decision": decision,
        "effective_config": self._config_to_dict(effective_config_object),
        "effective_config_object": effective_config_object,
        "engine": trial_engine,
        "error": "",
    }


def _outcome_rank(trial: dict[str, Any]) -> tuple[int, float, str]:
    decision = trial["decision"]
    guards_pass = bool(decision.hard_guard_results) and all(
        decision.hard_guard_results.values()
    )
    return (
        1 if guards_pass else 0,
        float(decision.confidence_score),
        str(trial["candidate"].candidate_id),
    )


def _invalid_report(payload: object, error: str, policy: Any) -> dict[str, Any]:
    return {
        "preprocess_intent": payload if isinstance(payload, dict) else {},
        "preprocess_policy": {
            "version": policy.policy_version,
            "automation_state": policy.automation_state,
            "calibrated": policy.calibrated,
        },
        "preprocess_candidates": [],
        "preprocess_evidence": [],
        "preprocess_decision": {
            "decision": "keep_original",
            "simulated_decision": "keep_original",
            "confidence_band": "low",
            "confidence_score": 0.0,
            "score_components": {},
            "hard_guard_results": {"intent_valid": False},
            "reason_codes": [f"invalid_intent:{error}"],
        },
        "selected_preprocess_config": {},
        "pending_preprocess_config": {},
        "best_config": {},
        "original_preprocess_config": {},
        "preprocess_experience": {
            "metadata_complete": False,
            "retrieval_used": False,
            "matched_ids": [],
            "scope": {},
            "error": "",
        },
        "error": error,
    }


def _stage_intent(intent: Any, target: str) -> Any:
    return replace(intent, target=target)


def _run_preprocess_intent(
    self: Any,
    engine: Any,
    intent_payload: object,
    previous_record: Any = None,
    prompt: str = "",
) -> dict[str, Any]:
    technique = str(getattr(self, "technique", "") or "").upper()
    policy = getattr(self, "preprocess_policy", None) or get_preprocess_policy(technique)
    self.preprocess_policy = policy
    control_config_object = deepcopy(self._engine_config(engine))
    control_config = self._config_to_dict(control_config_object)
    original_hash = stable_config_hash(control_config)
    saxs_intent = None
    try:
        if technique == "SAXS":
            saxs_intent = validate_saxs_ai_intent(intent_payload, policy=policy)
            intent = saxs_intent
        else:
            intent = parse_preprocess_intent(intent_payload)
            policy.validate_intent(intent)
    except (ContractValidationError, PolicyValidationError) as exc:
        report = _invalid_report(intent_payload, str(exc), policy)
        if technique == "SAXS":
            report["saxs_ai_rescue_replay"] = []
            engine.saxs_ai_rescue_replay = []
        report["best_config"] = control_config
        report["original_preprocess_config"] = deepcopy(control_config)
        report["preprocess_experience"], _ = _experience_context(self, technique)
        _append_decision_audit(self, report, original_hash=original_hash, prompt=prompt)
        return report

    adapter = get_preprocess_adapter(intent.technique)
    experience_context, experience_records = _experience_context(self, intent.technique)
    candidate_rows: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []
    trials: list[dict[str, Any]] = []
    saxs_candidates: list[PreprocessCandidate] = []
    replay_inputs: list[dict[str, Any]] = []
    control_recorded = False

    def run_stage(stage_target: str, stage_engine: Any) -> list[dict[str, Any]]:
        nonlocal control_recorded
        stage_payload = _stage_intent(intent, stage_target)
        stage_config = self._config_to_dict(self._engine_config(stage_engine))
        generated = generate_preprocess_candidates(
            stage_payload,
            stage_config,
            policy,
            adapter,
            experience_deltas=tuple(
                deepcopy(record.config_delta) for record in experience_records
            ),
        )
        if saxs_intent is not None:
            saxs_candidates.extend(generated)
        stage_trials: list[dict[str, Any]] = []
        for candidate in generated:
            stage = candidate.generation_reason
            if not candidate.config_delta:
                if not control_recorded:
                    row = candidate.to_dict()
                    row.update({"stage": "control", "run_status": "control"})
                    candidate_rows.append(row)
                    control_recorded = True
                continue
            trial = _execute_preprocess_candidate(
                self,
                stage_engine,
                candidate,
                previous_record,
                prompt,
            )
            stage_trials.append(trial)
            trials.append(trial)
            row = candidate.to_dict()
            row.update(
                {
                    "stage": stage,
                    "run_status": trial["evidence"].run_status,
                    "error": trial["error"],
                }
            )
            candidate_rows.append(row)
            evidence_rows.append(trial["evidence"].to_dict())
            if saxs_intent is not None:
                replay_inputs.append(
                    {
                        "candidate": candidate,
                        "source_config": deepcopy(stage_config),
                        "trial": trial,
                        "mode": _saxs_replay_mode(stage_engine),
                    }
                )
        return stage_trials

    if intent.target == "both":
        baseline_trials = run_stage("baseline", engine)
        passing_baselines = [
            item
            for item in baseline_trials
            if item["decision"].hard_guard_results
            and all(item["decision"].hard_guard_results.values())
        ]
        if passing_baselines:
            best_baseline = max(passing_baselines, key=_outcome_rank)
            run_stage("smoothing", best_baseline["engine"])
    else:
        run_stage(intent.target, engine)

    if not trials:
        report = _invalid_report(intent.to_dict(), "no_valid_candidates", policy)
        report["preprocess_candidates"] = candidate_rows
        if saxs_intent is not None:
            report["saxs_ai_rescue_replay"] = []
            engine.saxs_ai_rescue_replay = []
        report["best_config"] = control_config
        report["original_preprocess_config"] = deepcopy(control_config)
        report["preprocess_experience"] = experience_context
        _append_decision_audit(self, report, original_hash=original_hash, prompt=prompt)
        return report

    ranked = sorted(trials, key=_outcome_rank, reverse=True)
    selected = ranked[0]
    margin = float(selected["decision"].confidence_score)
    if len(ranked) > 1:
        margin -= float(ranked[1]["decision"].confidence_score)
    selected_decision = decide_preprocess_candidate(
        selected["evidence"],
        policy,
        candidate_margin=max(0.0, margin),
        metadata_complete=_metadata_complete(self),
    )
    selected["decision"] = selected_decision

    saxs_plan = None
    saxs_decision = None
    if saxs_intent is not None:
        saxs_plan = SAXSAIRescuePlan(
            intent=saxs_intent,
            candidates=tuple(saxs_candidates),
            policy_version=policy.policy_version,
            automation_state=policy.automation_state,
        )
        saxs_decision = assess_saxs_ai_candidate(
            selected["evidence"],
            candidate_margin=max(0.0, margin),
            metadata_complete=_metadata_complete(self),
            policy=policy,
        )

    self._preprocess_trials = {
        item["candidate"].candidate_id: item for item in trials
    }
    selected_config = deepcopy(selected["effective_config"])
    pending_config: dict[str, Any] = {}
    commit_error = ""
    best_config = self._config_to_dict(
        self._best_config if self._best_config is not None else control_config_object
    )
    report = {
        "preprocess_intent": intent.to_dict(),
        "preprocess_policy": {
            "version": policy.policy_version,
            "automation_state": policy.automation_state,
            "calibrated": policy.calibrated,
        },
        "preprocess_candidates": candidate_rows,
        "preprocess_evidence": evidence_rows,
        "preprocess_decision": (
            saxs_decision.to_dict() if saxs_decision is not None else selected_decision.to_dict()
        ),
        "selected_candidate_id": selected["candidate"].candidate_id,
        "selected_preprocess_config": selected_config,
        "pending_preprocess_config": pending_config,
        "best_config": best_config,
        "original_preprocess_config": deepcopy(control_config),
        "preprocess_experience": experience_context,
        "error": commit_error,
    }
    if saxs_plan is not None and saxs_decision is not None:
        report["saxs_ai_rescue_plan"] = saxs_plan.to_dict()
        report["saxs_ai_rescue_decision"] = saxs_decision.to_dict()
        engine.saxs_ai_rescue_plan = report["saxs_ai_rescue_plan"]
        engine.saxs_ai_rescue_decision = report["saxs_ai_rescue_decision"]
    audited = _append_decision_audit(
        self,
        report,
        original_hash=original_hash,
        prompt=prompt,
    )
    if saxs_intent is not None and not audited:
        report["saxs_ai_rescue_decision"] = deepcopy(report["preprocess_decision"])
        engine.saxs_ai_rescue_decision = report["saxs_ai_rescue_decision"]

    selected_apply_performed = False
    if audited and report["preprocess_decision"]["decision"] == "auto_accept":
        committed, commit_error = self._commit_preprocess_candidate(
            engine,
            selected["candidate"],
            original_hash,
        )
        selected_apply_performed = committed
        if not committed:
            selected_decision = replace(
                selected_decision,
                decision="keep_original",
                confidence_band="low",
                reason_codes=tuple(
                    dict.fromkeys((*selected_decision.reason_codes, commit_error))
                ),
            )
            if saxs_intent is not None:
                saxs_decision = SAXSAIRescueDecision(
                    outcome=selected_decision,
                    apply_allowed=False,
                )
                report["preprocess_decision"] = saxs_decision.to_dict()
                report["saxs_ai_rescue_decision"] = saxs_decision.to_dict()
                engine.saxs_ai_rescue_decision = report["saxs_ai_rescue_decision"]
            else:
                report["preprocess_decision"] = selected_decision.to_dict()
            report["error"] = commit_error
            _append_decision_audit(
                self,
                report,
                original_hash=original_hash,
                prompt=prompt,
            )
    elif report["preprocess_decision"]["decision"] == "request_confirmation":
        report["pending_preprocess_config"] = deepcopy(selected_config)

    if saxs_intent is not None:
        replay_rows: list[dict[str, Any]] = []
        for item in replay_inputs:
            trial = item["trial"]
            candidate = item["candidate"]
            is_selected = candidate.candidate_id == selected["candidate"].candidate_id
            decision_payload = (
                report["saxs_ai_rescue_decision"]
                if is_selected
                else trial["decision"].to_dict()
            )
            replay_rows.append(
                build_preprocess_replay_audit(
                    candidate=candidate,
                    source_config=item["source_config"],
                    effective_config=(
                        trial["effective_config"]
                        if trial.get("effective_config_object") is not None
                        else None
                    ),
                    mode=item["mode"],
                    source_context=_saxs_replay_context(self),
                    evidence=trial["evidence"],
                    decision=decision_payload,
                    trial_engine_created=trial.get("engine") is not None,
                    error=trial.get("error", ""),
                    apply_performed=is_selected and selected_apply_performed,
                ).to_dict()
            )
        report["saxs_ai_rescue_replay"] = replay_rows
        engine.saxs_ai_rescue_replay = replay_rows

    report["best_config"] = self._config_to_dict(
        self._best_config if self._best_config is not None else control_config_object
    )
    report["experience_proposal"] = _experience_proposal(report, selected)
    return report


def _commit_preprocess_candidate(
    self: Any,
    engine: Any,
    candidate: PreprocessCandidate,
    expected_base_hash: str,
) -> tuple[bool, str]:
    accepted_config = self._best_config
    if accepted_config is None:
        accepted_config = self._engine_config(engine)
    if stable_config_hash(self._config_to_dict(accepted_config)) != expected_base_hash:
        return False, "config_hash_changed"
    trial = getattr(self, "_preprocess_trials", {}).get(candidate.candidate_id)
    if not isinstance(trial, dict) or trial.get("effective_config_object") is None:
        return False, "candidate_state_missing"
    commit_engine = _new_trial_engine(self, engine, trial["effective_config_object"])
    ok, error = _run_trial_pipeline(self, commit_engine)
    if not ok:
        return False, error
    snapshot = _snapshot_for_preprocess(self, commit_engine)
    self._engine = commit_engine
    self._best_config = deepcopy(self._engine_config(commit_engine))
    self._best_output = deepcopy(snapshot.output_parameters)
    return True, ""


def run_preprocess_intent(
    self: Any,
    intent_payload: object,
    *,
    engine: Any = None,
    previous_record: Any = None,
    prompt: str = "",
) -> dict[str, Any]:
    target_engine = engine if engine is not None else getattr(self, "_engine", None)
    if target_engine is None:
        policy = getattr(self, "preprocess_policy", None) or get_preprocess_policy(
            str(getattr(self, "technique", "") or "").upper()
        )
        return _invalid_report(intent_payload, "engine_unavailable", policy)
    return _run_preprocess_intent(
        self,
        target_engine,
        intent_payload,
        previous_record,
        prompt,
    )
