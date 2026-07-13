from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from .policy import ParameterRule, PolicyValidationError, PreprocessPolicy


_COMMON_REQUIRED_EVIDENCE = (
    "evidence_coverage",
    "noise_reduction",
    "negative_fraction",
    "peak_shift",
    "fwhm_change",
    "integrated_area_change",
    "weak_peak_retention",
    "physical_parameter_drift",
)

_COMMON_HARD_LIMITS = {
    "evidence_coverage_min": 0.90,
    "negative_fraction_max": 0.05,
    "fwhm_change_max": 0.10,
    "integrated_area_change_max": 0.10,
    "weak_peak_retention_min": 0.90,
    "physical_parameter_drift_max": 0.10,
}

_COMMON_SCORE_WEIGHTS = {
    "noise_improvement": 0.25,
    "baseline_improvement": 0.15,
    "signal_preservation": 0.25,
    "physical_preservation": 0.15,
    "stability": 0.10,
    "candidate_margin": 0.10,
}


def _policy(
    technique: str,
    *,
    parameters: dict[str, ParameterRule],
    protected_features: tuple[str, ...],
    peak_shift_max: float,
) -> PreprocessPolicy:
    return PreprocessPolicy(
        policy_version=f"{technique.lower()}-preprocess-v1",
        technique=technique,
        allowed_targets=("baseline", "smoothing", "both"),
        allowed_directions=("weaken", "strengthen", "change_method"),
        allowed_effects=("light", "medium", "strong"),
        allowed_protected_features=protected_features,
        parameters=parameters,
        required_evidence=_COMMON_REQUIRED_EVIDENCE,
        hard_limits={**_COMMON_HARD_LIMITS, "peak_shift_max": peak_shift_max},
        score_weights=dict(_COMMON_SCORE_WEIGHTS),
        medium_threshold=0.60,
        high_threshold=0.82,
        min_candidate_margin=0.03,
        max_candidates=6,
        candidate_timeout_s=120.0,
        automation_state="shadow",
        calibrated=False,
    )


_POLICIES = {
    "DSC": _policy(
        "DSC",
        parameters={
            "baseline_type": ParameterRule(
                "baseline_type",
                str,
                choices=("auto", "linear", "polynomial", "spline", "tangential"),
            ),
            "smooth_window": ParameterRule("smooth_window", int, minimum=3, maximum=31),
            "smooth_order": ParameterRule("smooth_order", int, minimum=1, maximum=5),
        },
        protected_features=(
            "weak_peaks",
            "integrated_area",
            "thermal_events",
            "peak_position",
            "peak_width",
            "physical_parameters",
        ),
        peak_shift_max=1.0,
    ),
    "IR": _policy(
        "IR",
        parameters={
            "baseline_method": ParameterRule(
                "baseline_method",
                str,
                choices=("rubberband", "linear", "polynomial", "als", "mute_zone", "none"),
            ),
            "baseline_lam": ParameterRule("baseline_lam", float, minimum=1e2, maximum=1e10),
            "baseline_p": ParameterRule("baseline_p", float, minimum=1e-6, maximum=0.5),
            "smooth_window": ParameterRule("smooth_window", int, minimum=3, maximum=31),
            "smooth_order": ParameterRule("smooth_order", int, minimum=1, maximum=5),
        },
        protected_features=(
            "weak_peaks",
            "integrated_area",
            "peak_position",
            "peak_width",
            "physical_parameters",
        ),
        peak_shift_max=2.0,
    ),
    "WAXS": _policy(
        "WAXS",
        parameters={
            "instrument_background_method": ParameterRule(
                "instrument_background_method",
                str,
                choices=("arpls", "none", "linear", "polynomial", "spline", "chebyshev"),
            ),
            "arpls_lam": ParameterRule("arpls_lam", float, minimum=1e4, maximum=1e8),
            "arpls_diff_order": ParameterRule("arpls_diff_order", int, minimum=1, maximum=2),
            "smooth_window": ParameterRule("smooth_window", int, minimum=3, maximum=15),
            "smooth_order": ParameterRule("smooth_order", int, minimum=1, maximum=5),
        },
        protected_features=(
            "weak_peaks",
            "integrated_area",
            "broad_halo",
            "peak_position",
            "peak_width",
            "physical_parameters",
        ),
        peak_shift_max=0.10,
    ),
    "SAXS": _policy(
        "SAXS",
        parameters={
            "bg_scale_value": ParameterRule("bg_scale_value", float, minimum=0.5, maximum=1.5),
            "smooth_method": ParameterRule(
                "smooth_method", str, choices=("none", "savgol", "moving_average")
            ),
            "smooth_span": ParameterRule("smooth_span", int, minimum=3, maximum=31),
            "savgol_window": ParameterRule("savgol_window", int, minimum=3, maximum=31),
            "savgol_order": ParameterRule("savgol_order", int, minimum=1, maximum=5),
        },
        protected_features=(
            "weak_peaks",
            "integrated_area",
            "guinier_region",
            "beamstop_boundaries",
            "peak_position",
            "peak_width",
            "physical_parameters",
        ),
        peak_shift_max=0.01,
    ),
    "NMR": _policy(
        "NMR",
        parameters={
            "baseline_method": ParameterRule(
                "baseline_method",
                str,
                choices=("polynomial", "linear", "spline", "simple_polynomial"),
            ),
            "baseline_order": ParameterRule("baseline_order", int, minimum=1, maximum=9),
            "apodization": ParameterRule(
                "apodization", str, choices=("exponential", "gaussian", "none")
            ),
            "lb_Hz": ParameterRule("lb_Hz", float, minimum=0.1, maximum=40.0),
            "gb": ParameterRule("gb", float, minimum=0.0, maximum=1.0),
        },
        protected_features=(
            "weak_peaks",
            "integrated_area",
            "chemical_shift",
            "peak_width",
            "physical_parameters",
        ),
        peak_shift_max=0.02,
    ),
}


def get_preprocess_policy(technique: str) -> PreprocessPolicy:
    key = str(technique or "").strip().upper()
    policy = _POLICIES.get(key)
    if policy is None:
        raise PolicyValidationError(f"Unknown preprocessing technique: {technique}")
    return deepcopy(policy)


def load_configured_preprocess_policies(
    path: str | Path | None = None,
) -> dict[str, PreprocessPolicy]:
    from .calibration import load_policy_config

    config_path = Path(path) if path is not None else (
        Path(__file__).resolve().parents[3] / "config" / "preprocess_policies.json"
    )
    return load_policy_config(config_path, base_policies=_POLICIES)


def load_configured_preprocess_policy(
    technique: str,
    path: str | Path | None = None,
) -> PreprocessPolicy:
    key = str(technique or "").strip().upper()
    policies = load_configured_preprocess_policies(path)
    if key not in policies:
        raise PolicyValidationError(f"Unknown preprocessing technique: {technique}")
    return deepcopy(policies[key])
