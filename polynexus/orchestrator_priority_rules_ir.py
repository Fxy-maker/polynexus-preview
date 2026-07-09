from __future__ import annotations

JOINT_TUNING_PRIORITY_RULES_IR: dict[str, list[tuple[str, str]]] = {
    "phi_c inconsistency": [
        ("baseline_method", "remove baseline bias before comparing crystallinity across techniques"),
        ("normalization_method", "re-scale the bands before updating the crystallinity path"),
        ("peak_fit_window_cm1", "tighten the local window before reassigning bands"),
        ("peak_height_min", "drop weak band noise before comparing crystallinity"),
    ],
}

GOAL_TUNING_PRIORITY_RULES_IR: dict[str, list[tuple[str, str]]] = {
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
}
