from __future__ import annotations

ACTION_HINT_RULES_NMR: dict[str, tuple[list[str], list[str]]] = {
    "peak_mismatch": (
        ["baseline_method", "peak_distance_ppm", "peak_height_min"],
        ["peak assignment should stabilize", "residual summary should lose mismatch wording"],
    ),
    "background_drift": (
        ["baseline_method", "apodization"],
        ["baseline-related warnings should weaken", "residual summary should lose drift wording"],
    ),
    "noise": (
        ["baseline_method", "peak_height_min"],
        ["residual_type should move toward random", "median_snr should stay stable"],
    ),
}
