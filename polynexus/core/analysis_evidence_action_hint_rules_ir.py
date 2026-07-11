from __future__ import annotations

ACTION_HINT_RULES_IR: dict[str, tuple[list[str], list[str]]] = {
    "baseline_drift_low_wn": (
        ["baseline_method", "smooth_window"],
        ["low-wavenumber residuals should weaken", "baseline method should settle first"],
    ),
    "baseline_drift_high_wn": (
        ["baseline_method", "normalization_method"],
        ["high-wavenumber residuals should weaken", "normalization should stop steering the conclusion"],
    ),
    "key_band_mismatch": (
        ["peak_fit_window_cm1", "peak_prominence_min", "peak_height_min"],
        ["key-band hits should rise", "assignment confidence should better match band support"],
    ),
    "crowded_band_underfit": (
        ["peak_distance", "lineshape"],
        ["crowded bands should separate more cleanly", "peak widths should become easier to compare"],
    ),
    "over_smoothed_weak_bands": (
        ["smooth_window", "peak_height_min"],
        ["weak bands should reappear", "peak count should stay useful without over-promoting noise"],
    ),
    "normalization_bias": (
        ["normalization_method", "baseline_method"],
        ["band balance should become more stable", "assignment confidence should stop jumping"],
    ),
    "noise_dominant": (
        ["smooth_window"],
        ["sign flips should drop", "weak-band recovery should become more stable"],
    ),
    "peak_mismatch": (
        ["peak_height_min", "peak_prominence_min", "peak_fit_window_cm1"],
        ["peak identity should stabilize", "residual summary should lose mismatch wording"],
    ),
    "background_drift": (
        ["baseline_method", "normalization_method"],
        ["baseline-related warnings should weaken", "residual summary should lose drift wording"],
    ),
    "noise": (
        ["smooth_window", "peak_distance"],
        ["residual_type should move toward random", "peak count should stay stable"],
    ),
}
