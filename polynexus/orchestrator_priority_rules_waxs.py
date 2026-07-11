from __future__ import annotations

JOINT_TUNING_PRIORITY_RULES_WAXS: dict[str, list[tuple[str, str]]] = {
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
}

GOAL_TUNING_PRIORITY_RULES_WAXS: dict[str, list[tuple[str, str]]] = {
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
}
