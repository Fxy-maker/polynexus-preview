from __future__ import annotations

ACTION_HINT_RULES_WAXS: dict[str, tuple[list[str], list[str]]] = {
    "peak_position_bias": (
        ["two_theta_offset", "peak_function", "peak_distance"],
        ["peak positions should converge", "residual_type should move toward random"],
    ),
    "peak_count_underfit": (
        ["peak_distance", "max_peaks"],
        ["peak count should rise", "supporting peak regions should narrow"],
    ),
    "peak_count_overfit": (
        ["max_peaks", "peak_distance"],
        ["peak count should fall", "peak family should simplify"],
    ),
    "amorphous_background_bias": (
        ["background_method", "amorphous_subtraction", "amorphous_n_peaks"],
        ["background-related residuals should weaken", "crystallinity should stop depending on halo shape"],
    ),
    "peak_width_mismatch": (
        ["peak_function", "smooth_window"],
        ["shoulders and peak core should agree better", "peak widths should stabilize"],
    ),
    "low_angle_background_drift": (
        ["background_method", "amorphous_subtraction", "two_theta_offset"],
        ["low-angle residuals should weaken", "max_residual_region should move away from beamstop"],
    ),
    "peak_mismatch": (
        ["peak_function", "peak_distance", "two_theta_offset"],
        ["residual_type should move toward random", "max_residual_region should shrink"],
    ),
    "background_drift": (
        ["background_method", "amorphous_subtraction", "smooth_window"],
        ["background-related residuals should weaken", "summary should lose drift wording"],
    ),
    "noise": (
        ["smooth_window", "max_peaks"],
        ["residual_type should move toward random", "peak positions should stay stable"],
    ),
}
