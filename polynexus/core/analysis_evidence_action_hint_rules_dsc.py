from __future__ import annotations

ACTION_HINT_RULES_DSC: dict[str, tuple[list[str], list[str]]] = {
    "peak_shift": (
        ["Tm_search_low_C", "Tm_search_high_C", "peak_function"],
        ["Tm_peak_C should align better", "validation_summary should calm down"],
    ),
    "baseline_drift": (
        ["baseline_type", "smooth_window"],
        ["baseline-related warnings should weaken", "residual summary should lose drift wording"],
    ),
    "baseline_drift_low_t": (
        ["baseline_type", "smooth_window"],
        ["low-temperature baseline support should stabilize", "residual summary should lose drift wording"],
    ),
    "baseline_drift_high_t": (
        ["baseline_type", "smooth_window"],
        ["high-temperature baseline support should stabilize", "residual summary should lose drift wording"],
    ),
    "melting_peak_shift": (
        ["Tm_search_low_C", "Tm_search_high_C", "peak_function"],
        ["Tm_peak_C should align better", "melting window should re-center"],
    ),
    "tg_step_missing": (
        ["Tg_search_low_C", "Tg_search_high_C", "baseline_type"],
        ["Tg support should become clearer", "DCp should stop looking flat"],
    ),
    "cold_crystallization_overlap": (
        ["Tc_search_low_C", "Tc_search_high_C", "Tm_search_low_C"],
        ["Tcc and Tm should separate more cleanly", "event windows should stop overlapping"],
    ),
    "event_window_too_narrow": (
        ["Tm_search_low_C", "Tm_search_high_C", "Tc_search_low_C", "Tc_search_high_C"],
        ["event support should widen", "edge truncation should weaken"],
    ),
    "event_window_too_wide": (
        ["Tm_search_low_C", "Tm_search_high_C", "Tc_search_low_C", "Tc_search_high_C"],
        ["event support should tighten", "broad windows should stop swallowing noise"],
    ),
    "exo_up_down_confusion": (
        ["exo_up", "baseline_type"],
        ["polarity should align with the scan convention", "signed enthalpy should stop contradicting the event"],
    ),
    "multi_event_underfit": (
        ["peak_function", "max_melting_peak_width_C"],
        ["multiple events should be represented explicitly", "single-peak forcing should weaken"],
    ),
    "segment_split_issue": (
        ["smooth_window", "peak_function"],
        ["scan segmentation should be checked", "the event should stop being split across fragments"],
    ),
    "noise": (
        ["smooth_window", "peak_prominence_ratio"],
        ["residual_type should move toward random", "scan_r_squared should stabilize"],
    ),
    "noise_dominant": (
        ["smooth_window", "peak_prominence_ratio"],
        ["residual_type should move toward random", "noise should stop dominating the event"],
    ),
}
