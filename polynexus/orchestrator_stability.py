"""SAXS stability-study bridge used by the AI orchestrator."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from typing import Any

from polynexus.core.preprocess_optimization import ParameterDomain, StabilityStudyRequest, run_stability_study
from polynexus.core.saxs_mode import canonical_saxs_mode
from polynexus.core.saxs_engine.saxs_ai_rescue import assess_saxs_confirmed_rerun


def _normalise_saxs_stability_mode(value: Any) -> str | None:
    return canonical_saxs_mode(value)


def _saxs_stability_mode(self: Any, engine: Any, config: Any) -> tuple[str | None, str | None]:
    inputs: list[Any] = []
    experiment_type = getattr(config, "experiment_type", "")
    if str(experiment_type or "").strip():
        inputs.append(experiment_type)

    submodule_override = getattr(self, "submodule_override", None)
    active_submodule = getattr(engine, "active_submodule", None)
    for value in (submodule_override, active_submodule):
        if str(value or "").strip():
            inputs.append(value)

    if not inputs:
        public_submodule = getattr(self, "_public_submodule", None)
        if callable(public_submodule):
            inputs.append(public_submodule())

    modes = [_normalise_saxs_stability_mode(value) for value in inputs]
    if not modes or any(mode is None for mode in modes):
        return None, "unsupported_saxs_stability_mode"
    if len(set(modes)) != 1:
        return None, "conflicting_saxs_stability_mode"
    return modes[0], None


def _failed_saxs_stability_report(
    baseline_config: dict[str, Any],
    reason_code: str,
) -> dict[str, Any]:
    return {
        "schema_version": "saxs-stability-v1",
        "mode": None,
        "decision": "keep_original",
        "complete": False,
        "baseline_config": deepcopy(baseline_config),
        "selected_config": {},
        "trials": [],
        "plateau": {"connected": False},
        "bootstrap": {},
        "continuity": {"passed": False},
        "physics_gate_passed": False,
        "quality_gate_passed": False,
        "reason_codes": [reason_code],
    }


def _numeric_domain(config: dict[str, Any], name: str, *, relative: float, minimum: float, maximum: float):
    value = config.get(name)
    try:
        current = float(value)
    except (TypeError, ValueError):
        return None
    if current != current:
        return None
    low = max(minimum, current * (1.0 - relative))
    high = min(maximum, current * (1.0 + relative))
    if low > high:
        low, high = high, low
    return ParameterDomain(name, low, high)


def _saxs_stability_domains(config: dict[str, Any]) -> tuple[ParameterDomain, ...]:
    specs = (
        ("q_min", 0.20, 0.001, 2.0),
        ("q_max", 0.15, 0.2, 8.0),
        ("q_corr_min", 0.20, 0.01, 2.0),
        ("q_corr_max", 0.15, 0.3, 8.0),
        ("q_porod_min", 0.20, 0.2, 8.0),
        ("q_porod_max", 0.15, 0.5, 12.0),
        ("guinier_q_max_factor", 0.30, 0.5, 2.5),
        ("bg_scale_value", 0.20, 0.5, 1.5),
        ("beam_center_x", 0.02, -100000.0, 100000.0),
        ("beam_center_y", 0.02, -100000.0, 100000.0),
        ("chi_halfwidth", 0.35, 1.0, 90.0),
    )
    domains = [
        domain
        for name, relative, minimum, maximum in specs
        if (domain := _numeric_domain(config, name, relative=relative, minimum=minimum, maximum=maximum)) is not None
    ]
    dilation = config.get("orientation_mask_dilation_px")
    if isinstance(dilation, (list, tuple)) and dilation:
        values = tuple(sorted({int(item) for item in dilation if int(item) > 0}))
        if values:
            domains.append(ParameterDomain("orientation_mask_dilation_px", values=values))
    return tuple(domains)


def _frame_values(engine: Any, output: dict[str, Any]) -> dict[str, list[float]]:
    values: dict[str, list[float]] = {}
    for name, aliases in {
        "L_nm": ("L_nm",),
        "invariant_Q": ("invariant_Q", "Q_star"),
        "phi_c": ("phi_c",),
        "Kp": ("Kp",),
        "Rg": ("Rg",),
    }.items():
        raw = next((output.get(alias) for alias in aliases if output.get(alias) is not None), None)
        if isinstance(raw, (int, float)):
            values[name] = [float(raw)]
    for owner_name, point_name in (("_temperature_result", "temp_points"), ("_strain_result", "strain_points")):
        owner = getattr(engine, owner_name, None)
        points = getattr(owner, point_name, None) if owner is not None else None
        if not isinstance(points, (list, tuple)):
            continue
        for name, aliases in {
            "L_nm": ("L_nm",),
            "invariant_Q": (
                "invariant_Q",
                "invariant_Q_rel",
                "Q_star",
                "Q_star_rel",
            ),
            "phi_c": ("phi_c",),
        }.items():
            sequence = []
            for point in points:
                for alias in aliases:
                    try:
                        value = float(getattr(point, alias))
                    except (AttributeError, TypeError, ValueError):
                        continue
                    if value == value:
                        sequence.append(value)
                        break
            if sequence:
                values[name] = sequence
    return values


def _run_saxs_stability_study(self: Any, engine: Any) -> dict[str, Any]:
    if self.technique != "saxs":
        return {}
    config = self._engine_config(engine)
    base_config = self._config_to_dict(config)
    scientific_mode, mode_error = _saxs_stability_mode(self, engine, config)
    if scientific_mode is None:
        report = _failed_saxs_stability_report(
            base_config,
            mode_error or "unsupported_saxs_stability_mode",
        )
        self._last_stability_report = deepcopy(report)
        return report
    domains = _saxs_stability_domains(base_config)
    if not domains:
        report = _failed_saxs_stability_report(base_config, "stability_domains_unavailable")
        report["mode"] = scientific_mode
        self._last_stability_report = deepcopy(report)
        return report

    from polynexus.orchestrator_preprocess import _new_trial_engine, _run_trial_pipeline

    def evaluate(candidate_config: dict[str, Any]) -> dict[str, Any]:
        # Candidate configs are JSON-like snapshots; the engine requires a
        # typed SAXSConfig instance.  Clone the baseline object and apply only
        # known candidate fields so every trial really uses its perturbation.
        trial_config = deepcopy(config)
        for name, value in candidate_config.items():
            if hasattr(trial_config, name):
                setattr(trial_config, name, deepcopy(value))
        trial_engine = _new_trial_engine(self, engine, trial_config)
        ok, error = _run_trial_pipeline(self, trial_engine)
        if not ok:
            return {"physical_passed": False, "quality_passed": False, "reason_codes": [error]}
        output = self._output_parameters(trial_engine)
        residuals = self._residual_pattern(trial_engine)
        evidence = self._analysis_evidence(output, residuals)
        score = self._score_snapshot(output, residuals, evidence).get("objective_score", 0.0)
        assessment = assess_saxs_confirmed_rerun(trial_engine, mode=scientific_mode)
        return {
            "score": score,
            "physical_passed": assessment.get("physical_gate_status") == "passed",
            "quality_passed": assessment.get("quality_gate_status") == "passed",
            "metrics": {
                name: values[0]
                for name, values in _frame_values(trial_engine, output).items()
                if values and name in {"L_nm", "invariant_Q", "phi_c", "Kp", "Rg"}
            },
            "frame_values": _frame_values(trial_engine, output),
            "reason_codes": assessment.get("reason_codes", []),
        }

    decision_mode = str(
        (self.workspace_context or {}).get("stability_mode", "strict") or "strict"
    ).lower()
    request = StabilityStudyRequest(
        baseline_config=deepcopy(base_config),
        domains=domains,
        seed=17,
        global_trials=12 if decision_mode == "strict" else 6,
        active_trials=8 if decision_mode == "strict" else 3,
        confirmation_trials=9 if decision_mode == "strict" else 3,
        min_plateau_points=3,
        decision_mode="strict" if decision_mode == "strict" else "quick",
        # SAXS physical semantics require an explicit user confirmation even
        # when the numerical stability score reaches the auto-accept band.
        allow_auto_accept=False,
    )
    report = replace(
        run_stability_study(request, evaluate),
        mode=scientific_mode,
    ).to_dict()
    self._last_stability_report = deepcopy(report)
    return report
