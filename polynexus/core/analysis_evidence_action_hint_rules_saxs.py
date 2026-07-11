from __future__ import annotations

ACTION_HINT_RULES_SAXS: dict[str, tuple[list[str], list[str]]] = {
    "peak_mismatch": (
        ["savgol_window", "q_bragg_min", "q_bragg_max"],
        ["residual_type should move toward random", "Bragg-region fit should stabilize"],
    ),
    "background_drift": (
        ["savgol_window", "q_corr_min", "q_corr_max"],
        ["L_bragg and L_corr should move closer", "validation_summary should calm down"],
    ),
    "noise": (
        ["savgol_window", "savgol_order"],
        ["residual_type should move toward random", "q_peak_snr should stabilize"],
    ),
}
