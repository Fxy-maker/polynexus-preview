from __future__ import annotations

JOINT_TUNING_PRIORITY_RULES_NMR: dict[str, list[tuple[str, str]]] = {
    "phi_c inconsistency": [
        ("baseline_method", "stabilize the baseline before re-reading crystallinity"),
        ("peak_distance_ppm", "separate crowded resonances before adjusting the assignment"),
        ("deconvolution_method", "revisit the deconvolution before changing thresholds again"),
        ("lb_Hz", "sharpen the lineshape before comparing across techniques"),
    ],
}

GOAL_TUNING_PRIORITY_RULES_NMR: dict[str, list[tuple[str, str]]] = {
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
}
