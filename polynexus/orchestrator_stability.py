"""SAXS stability-study bridge used by the AI orchestrator."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from typing import Any

import numpy as np

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
    domains: "SAXSStabilityDomains | None" = None,
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
        "active_dimensions": [
            domain.name for domain in domains.domains
        ] if domains is not None else [],
        "excluded_dimensions": (
            dict(domains.excluded_dimensions) if domains is not None else {}
        ),
    }


def _numeric_domain(config: dict[str, Any], name: str, *, relative: float, minimum: float, maximum: float):
    value = config.get(name)
    try:
        current = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not np.isfinite(current):
        return None
    low = max(minimum, current * (1.0 - relative))
    high = min(maximum, current * (1.0 + relative))
    if low > high:
        low, high = high, low
    return ParameterDomain(name, low, high)


@dataclass(frozen=True)
class SAXSStabilityDomains:
    """Active perturbations plus explicit exclusions, with tuple compatibility."""

    domains: tuple[ParameterDomain, ...]
    excluded_dimensions: dict[str, str]

    @property
    def excluded(self) -> dict[str, str]:
        return self.excluded_dimensions

    def __iter__(self):
        return iter(self.domains)

    def __len__(self) -> int:
        return len(self.domains)

    def __getitem__(self, index):
        return self.domains[index]


def _finite_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if np.isfinite(number) else None


def _valid_window(config: dict[str, Any], low: str, high: str) -> bool:
    low_value = _finite_float(config.get(low))
    high_value = _finite_float(config.get(high))
    return low_value is not None and high_value is not None and low_value < high_value


def _valid_saxs_windows(config: dict[str, Any]) -> bool:
    for low, high, consumer_active in (
        ("q_min", "q_max", True),
        ("q_corr_min", "q_corr_max", True),
        ("q_porod_min", "q_porod_max", config.get("do_porod", True) is not False),
    ):
        if (
            consumer_active
            and low in config
            and high in config
            and not _valid_window(config, low, high)
        ):
            return False
    return True


def _has_raw_2d_detector_evidence(engine: Any) -> bool:
    if engine is None:
        return False

    for image in (
        getattr(engine, "_img", None),
        getattr(getattr(engine, "result", None), "raw_data", {}).get("img")
        if isinstance(getattr(getattr(engine, "result", None), "raw_data", None), dict)
        else None,
    ):
        if image is None:
            continue
        try:
            if np.asarray(image).ndim == 2 and np.asarray(image).size > 0:
                return True
        except (TypeError, ValueError):
            continue
    return False


def _has_sector_evidence(engine: Any) -> bool:
    if engine is None:
        return False
    sector_candidates: list[Any] = [
        getattr(engine, "_sector_data", None),
        getattr(engine, "_sector_data_list", None),
    ]
    raw_data = getattr(getattr(engine, "result", None), "raw_data", None)
    if isinstance(raw_data, dict):
        sector_candidates.append(raw_data.get("sector_data"))
    for candidate in sector_candidates:
        values = candidate if isinstance(candidate, (list, tuple)) else (candidate,)
        if any(isinstance(value, dict) and bool(value) for value in values):
            return True
    return False


def _has_real_2d_detector_evidence(engine: Any) -> bool:
    return _has_raw_2d_detector_evidence(engine) or _has_sector_evidence(engine)


def _saxs_stability_domains(
    config: dict[str, Any],
    *,
    mode: str | None = None,
    engine: Any = None,
    context: Any = None,
) -> SAXSStabilityDomains:
    del mode, context  # reserved for compatible consumer-specific activity checks
    domains: list[ParameterDomain] = []
    excluded: dict[str, str] = {}

    pair_specs = (
        ("q_min", "q_max", (0.20, 0.001, 2.0), (0.15, 0.2, 8.0)),
        ("q_corr_min", "q_corr_max", (0.20, 0.01, 2.0), (0.15, 0.3, 8.0)),
        ("q_porod_min", "q_porod_max", (0.20, 0.2, 8.0), (0.15, 0.5, 12.0)),
    )
    for low, high, low_spec, high_spec in pair_specs:
        if low.startswith("q_porod") and config.get("do_porod", True) is False:
            excluded[low] = "porod_consumer_disabled"
            excluded[high] = "porod_consumer_disabled"
            continue
        if low not in config or high not in config:
            excluded[low] = "consumer_config_missing"
            excluded[high] = "consumer_config_missing"
            continue
        if not _valid_window(config, low, high):
            excluded[low] = "invalid_coupled_q_window"
            excluded[high] = "invalid_coupled_q_window"
            continue
        for name, spec in ((low, low_spec), (high, high_spec)):
            domain = _numeric_domain(
                config,
                name,
                relative=spec[0],
                minimum=spec[1],
                maximum=spec[2],
            )
            if domain is None:
                excluded[name] = "consumer_config_invalid"
            else:
                domains.append(domain)

    guinier = _finite_float(config.get("guinier_q_max_factor"))
    if guinier is None or guinier <= 0:
        excluded["guinier_q_max_factor"] = "consumer_config_invalid"
    else:
        domain = _numeric_domain(
            config,
            "guinier_q_max_factor",
            relative=0.30,
            minimum=0.5,
            maximum=2.5,
        )
        if domain is not None:
            domains.append(domain)

    if (
        str(config.get("bg_scale_method", "") or "").strip().lower() == "manual"
        and str(config.get("background_file", "") or "").strip()
    ):
        domain = _numeric_domain(
            config,
            "bg_scale_value",
            relative=0.20,
            minimum=0.5,
            maximum=1.5,
        )
        if domain is None:
            excluded["bg_scale_value"] = "consumer_config_invalid"
        else:
            domains.append(domain)
    else:
        excluded["bg_scale_value"] = "manual_background_inactive"

    excluded["orientation_mask_dilation_px"] = "reliability_sensitivity_only"
    detector_dimensions = (
        "beam_center_offset_x_px",
        "beam_center_offset_y_px",
        "chi_halfwidth",
        "mask_dilation_px",
    )
    raw_detector_evidence = _has_raw_2d_detector_evidence(engine)
    if not _has_real_2d_detector_evidence(engine):
        excluded.update(
            {name: "detector_2d_evidence_missing" for name in detector_dimensions}
        )
        return SAXSStabilityDomains(tuple(domains), excluded)

    if raw_detector_evidence:
        for name in ("beam_center_offset_x_px", "beam_center_offset_y_px"):
            current = _finite_float(config.get(name))
            if current is None:
                excluded[name] = "consumer_config_invalid"
            else:
                domains.append(ParameterDomain(name, current - 2.0, current + 2.0))
        mask_dilation = _finite_float(config.get("mask_dilation_px"))
        if (
            isinstance(config.get("mask_dilation_px"), bool)
            or mask_dilation is None
            or not mask_dilation.is_integer()
            or mask_dilation < 0
            or mask_dilation > 100
        ):
            excluded["mask_dilation_px"] = "consumer_config_invalid"
        else:
            current_dilation = int(mask_dilation)
            local_dilations = tuple(
                sorted(
                    {
                        max(0, current_dilation - 1),
                        current_dilation,
                        min(100, current_dilation + 1),
                    }
                )
            )
            domains.append(
                ParameterDomain("mask_dilation_px", values=local_dilations)
            )
    else:
        excluded["beam_center_offset_x_px"] = "raw_detector_2d_evidence_missing"
        excluded["beam_center_offset_y_px"] = "raw_detector_2d_evidence_missing"
        excluded["mask_dilation_px"] = "raw_detector_2d_evidence_missing"

    sector_integration_active = not bool(config.get("is_isotropic", False)) and (
        str(config.get("analysis_priority", "anisotropic") or "anisotropic")
        .strip()
        .lower()
        != "isotropic"
    )
    if not sector_integration_active:
        excluded["chi_halfwidth"] = "sector_integration_inactive"
    else:
        chi = _numeric_domain(
            config,
            "chi_halfwidth",
            relative=0.35,
            minimum=1.0,
            maximum=90.0,
        )
        if chi is None:
            excluded["chi_halfwidth"] = "consumer_config_invalid"
        else:
            domains.append(chi)

    return SAXSStabilityDomains(tuple(domains), excluded)


def _authoritative_saxs_candidate(
    candidate: dict[str, Any],
    baseline: dict[str, Any],
) -> dict[str, Any]:
    """Mark changed half-width candidates as explicit sector-range authority."""

    prepared = deepcopy(candidate)
    candidate_halfwidth = _finite_float(prepared.get("chi_halfwidth"))
    baseline_halfwidth = _finite_float(baseline.get("chi_halfwidth"))
    if (
        candidate_halfwidth is not None
        and baseline_halfwidth is not None
        and candidate_halfwidth != baseline_halfwidth
    ):
        prepared["chi_halfwidth_authoritative"] = True
    return prepared


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
    domain_result = _saxs_stability_domains(
        base_config,
        mode=scientific_mode,
        engine=engine,
        context=getattr(self, "workspace_context", None),
    )
    if scientific_mode is None:
        report = _failed_saxs_stability_report(
            base_config,
            mode_error or "unsupported_saxs_stability_mode",
            domain_result,
        )
        self._last_stability_report = deepcopy(report)
        return report
    domains = domain_result.domains
    if not domains:
        report = _failed_saxs_stability_report(
            base_config,
            "stability_domains_unavailable",
            domain_result,
        )
        report["mode"] = scientific_mode
        self._last_stability_report = deepcopy(report)
        return report

    from polynexus.orchestrator_preprocess import _new_trial_engine, _run_trial_pipeline

    def evaluate(candidate_config: dict[str, Any]) -> dict[str, Any]:
        effective_candidate = _authoritative_saxs_candidate(
            candidate_config,
            base_config,
        )
        if not _valid_saxs_windows(effective_candidate):
            return {
                "physical_passed": False,
                "quality_passed": False,
                "reason_codes": ["invalid_coupled_q_window"],
            }
        # Candidate configs are JSON-like snapshots; the engine requires a
        # typed SAXSConfig instance.  Clone the baseline object and apply only
        # known candidate fields so every trial really uses its perturbation.
        trial_config = deepcopy(config)
        for name, value in effective_candidate.items():
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
    raw_report = run_stability_study(request, evaluate)
    report = replace(
        raw_report,
        selected_config=_authoritative_saxs_candidate(
            raw_report.selected_config,
            base_config,
        ),
        trials=tuple(
            replace(
                trial,
                config=_authoritative_saxs_candidate(trial.config, base_config),
            )
            for trial in raw_report.trials
        ),
        mode=scientific_mode,
        active_dimensions=tuple(domain.name for domain in domains),
        excluded_dimensions=dict(domain_result.excluded_dimensions),
    ).to_dict()
    self._last_stability_report = deepcopy(report)
    return report
