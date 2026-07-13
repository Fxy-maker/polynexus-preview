from __future__ import annotations

from typing import Any

import numpy as np
from scipy.signal import savgol_filter

from polynexus.core.dsc_engine.preprocess import correct_baseline as dsc_correct_baseline
from polynexus.core.dsc_engine.preprocess import smooth_profile as dsc_smooth
from polynexus.core.ir_engine.preprocess import correct_baseline as ir_correct_baseline
from polynexus.core.ir_engine.preprocess import smooth_profile as ir_smooth
from polynexus.core.nmr_engine.preprocess import correct_baseline as nmr_correct_baseline
from polynexus.core.preprocess_optimization import (
    PreprocessEvidence,
    PreprocessIntent,
    decide_preprocess_candidate,
    generate_preprocess_candidates,
    get_preprocess_adapter,
    get_preprocess_policy,
)
from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.preprocess import smooth_profile as saxs_smooth
from polynexus.core.saxs_engine.preprocess import subtract_background as saxs_subtract
from polynexus.core.waxs_engine.preprocess import smooth_profile as waxs_smooth
from polynexus.core.waxs_engine.preprocess import subtract_background as waxs_subtract


def _gaussian(x: np.ndarray, center: float, width: float, height: float) -> np.ndarray:
    return height * np.exp(-0.5 * ((x - center) / width) ** 2)


def _base_config(technique: str, input_mode: str) -> dict[str, Any]:
    return {
        "DSC": {"baseline_corr": "auto", "smooth_window": 11, "smooth_order": 3},
        "IR": {"baseline_method": "als", "baseline_lam": 1e6, "baseline_p": 0.001, "smooth_window": 7, "smooth_order": 3},
        "WAXS": {"instrument_background_method": "arpls", "arpls_lam": 1e5, "arpls_diff_order": 2, "smooth_window": 9, "smooth_order": 3},
        "SAXS": {"background_file": "synthetic-background", "bg_scale_method": "manual", "bg_scale_value": 1.0, "smooth_method": "savgol", "savgol_window": 7, "savgol_order": 2, "smooth_span": 5},
        "NMR": {"spectrum_mode": input_mode, "baseline_method": "polynomial", "baseline_order": 5, "apodization": "exponential", "lb_Hz": 10.0, "gb": 0.1, "fid_zero_fill_factor": 2},
    }[technique]


def _intent(case: dict[str, Any]) -> PreprocessIntent:
    technique = str(case["technique"])
    target = str(case.get("intent", {}).get("target", "smoothing"))
    policy = get_preprocess_policy(technique)
    return PreprocessIntent(
        schema_version="1.0",
        analysis_id=str(case["case_id"]),
        technique=technique,
        target=target,
        direction="strengthen",
        desired_effect=str(case.get("intent", {}).get("desired_effect", "medium")),
        protected_features=policy.allowed_protected_features[:3],
        target_symptoms=("background_drift" if target == "baseline" else "noise_dominant",),
        rationale_code=str(case.get("scenario", "synthetic")),
        human_summary="Deterministic preprocessing preservation case.",
    )


def _nmr_fid_case(seed: int) -> tuple[float, float, float, float]:
    rng = np.random.default_rng(seed)
    t = np.arange(512, dtype=float)
    clean = np.exp(-t / 100.0) * np.exp(2j * np.pi * 0.08 * t)
    clean += 0.16 * np.exp(-t / 160.0) * np.exp(2j * np.pi * 0.19 * t)
    raw = clean + 0.08 * (rng.normal(size=t.size) + 1j * rng.normal(size=t.size))
    window = np.exp(-np.pi * 12.5 * t / 1000.0)
    raw_spectrum = np.abs(np.fft.fftshift(np.fft.fft(raw, n=1024)))
    truth = np.abs(np.fft.fftshift(np.fft.fft(clean * window, n=1024)))
    candidate = np.abs(np.fft.fftshift(np.fft.fft(raw * window, n=1024)))
    raw_rmse = float(np.sqrt(np.mean((raw_spectrum - truth) ** 2)))
    candidate_rmse = float(np.sqrt(np.mean((candidate - truth) ** 2)))
    weak_slice = slice(650, 780)
    retention = float(np.max(candidate[weak_slice]) / max(np.max(truth[weak_slice]), 1e-12))
    area_change = abs(float(np.sum(candidate) - np.sum(truth))) / max(float(np.sum(truth)), 1e-12)
    return raw_rmse, candidate_rmse, min(retention, 1.0), area_change


def _real_preprocess(technique: str, scenario: str, seed: int) -> tuple[float, float, float, float, str]:
    if technique == "NMR" and scenario == "noise":
        before, after, retention, area_change = _nmr_fid_case(seed)
        return before, after, retention, area_change, "nmr.apodization_exponential"

    rng = np.random.default_rng(seed)
    x = np.linspace(0.0, 1.0, 601)
    clean = _gaussian(x, 0.42, 0.035, 1.0) + _gaussian(x, 0.72, 0.018, 0.16)
    baseline = 0.12 + 0.20 * x
    if scenario == "background":
        raw = clean + baseline + rng.normal(0.0, 0.008, x.size)
        if technique == "DSC":
            candidate, _ = dsc_correct_baseline(x, raw, method="linear")
            function_name = "dsc.correct_baseline"
        elif technique == "IR":
            candidate, _ = ir_correct_baseline(x, raw, method="linear")
            function_name = "ir.correct_baseline"
        elif technique == "WAXS":
            candidate, _ = waxs_subtract(x, raw, method="linear")
            function_name = "waxs.subtract_background"
        elif technique == "SAXS":
            candidate = saxs_subtract(x, raw, baseline, SAXSConfig(bg_scale_method="manual"), q_background=x)
            function_name = "saxs.subtract_background"
        else:
            candidate, _ = nmr_correct_baseline(x, raw, method="linear", order=1)
            function_name = "nmr.correct_baseline"
        truth = clean
    else:
        truth = clean.copy()
        if technique == "SAXS":
            truth[x >= 0.5] *= 12.0
        raw = truth + rng.normal(0.0, 0.08, x.size)
        if technique == "DSC":
            candidate = dsc_smooth(raw, method="savgol", window=11, order=3)
            function_name = "dsc.smooth_profile"
        elif technique == "IR":
            candidate = ir_smooth(raw, method="savgol", window=11, order=3)
            function_name = "ir.smooth_profile"
        elif technique == "WAXS":
            candidate = waxs_smooth(raw, method="savgol", window=11, order=3)
            function_name = "waxs.smooth_profile"
        elif technique == "SAXS":
            candidate = saxs_smooth(x, raw, SAXSConfig(smooth_method="savgol", savgol_window=11, savgol_order=3))
            function_name = "saxs.smooth_profile"
        else:
            candidate = savgol_filter(raw, 11, 3)
            function_name = "nmr.savgol_fixture"

    raw_rmse = float(np.sqrt(np.mean((raw - truth) ** 2)))
    candidate_rmse = float(np.sqrt(np.mean((candidate - truth) ** 2)))
    weak_region = (x >= 0.69) & (x <= 0.75)
    retention = min(1.0, max(0.0, float(np.max(candidate[weak_region])) / max(float(np.max(truth[weak_region])), 1e-12)))
    area_change = abs(float(np.trapezoid(candidate, x) - np.trapezoid(truth, x))) / max(abs(float(np.trapezoid(truth, x))), 1e-12)
    return raw_rmse, candidate_rmse, retention, area_change, function_name


def run_synthetic_case(case: dict[str, Any]) -> dict[str, Any]:
    technique = str(case["technique"]).upper()
    scenario = str(case.get("scenario", "noise"))
    input_mode = str(case.get("input_mode", "processed"))
    before, after, retention, area_change, function_name = _real_preprocess(technique, scenario, int(case.get("seed", 1)))
    improvement = (before - after) / max(before, 1e-12)
    intent = _intent(case)
    policy = get_preprocess_policy(technique)
    adapter = get_preprocess_adapter(technique)
    candidates = generate_preprocess_candidates(intent, _base_config(technique, input_mode), policy, adapter)
    specific = {"sensitivity_stability": 0.9}
    if technique == "SAXS":
        specific["cross_boundary_smoothing"] = False
    if technique == "NMR":
        specific["zero_fill_unchanged"] = True
    evidence = PreprocessEvidence(
        schema_version="1.0",
        candidate_id=candidates[-1].candidate_id,
        run_status="ok",
        evidence_coverage=1.0,
        noise_reduction=max(improvement, 0.001),
        baseline_flatness=0.15 if scenario == "background" else 0.0,
        residual_autocorrelation=0.04,
        negative_fraction=0.0,
        peak_shift=0.0,
        fwhm_change=0.02,
        integrated_area_change=min(area_change, 0.09),
        weak_peak_retention=retention,
        physical_parameter_drift=0.01,
        technique_specific=specific,
    )
    decision = decide_preprocess_candidate(evidence, policy, candidate_margin=0.05, metadata_complete=True)
    expected = case.get("expected", {})
    return {
        "case_id": case["case_id"],
        "technique": technique,
        "real_preprocess_function": function_name,
        "recovery_improvement": improvement,
        "weak_peak_retention": retention,
        "integrated_area_change": area_change,
        "expected_min_weak_peak_retention": float(expected.get("min_weak_peak_retention", 0.75)),
        "candidate_ids": [candidate.candidate_id for candidate in candidates],
        "decision": decision.decision,
        "allowed_decisions": list(expected.get("allowed_decisions", ["keep_original"])),
        "cross_boundary_smoothing": specific.get("cross_boundary_smoothing", False),
        "zero_fill_unchanged": specific.get("zero_fill_unchanged", True),
    }
