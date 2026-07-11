from __future__ import annotations

JOINT_TUNING_PRIORITY_RULES_SAXS: dict[str, list[tuple[str, str]]] = {
    "l consistency unstable": [
        ("savgol_window", "stabilize the low-q signal before touching the window edges"),
        ("q_bragg_min", "move the Bragg region toward the consistent signal"),
        ("q_bragg_max", "move the Bragg region toward the consistent signal"),
        ("q_corr_min", "tighten the correlation region before reusing the L estimate"),
        ("q_corr_max", "tighten the correlation region before reusing the L estimate"),
        ("lorentz_fit_method", "revisit the long-period fit backend when L keeps drifting"),
    ],
    "phi_c inconsistency": [
        ("savgol_window", "remove small-scale noise before re-evaluating crystallinity"),
        ("q_corr_min", "keep the crystallinity estimate away from unstable low-q data"),
        ("q_corr_max", "keep the crystallinity estimate away from unstable high-q data"),
        ("idf_peak_rel_thresh", "treat weak secondary peaks more conservatively"),
    ],
    "tm bidirectional gap": [
        ("tangent_lc_min_nm", "protect the SAXS thickness estimate before linking it to DSC"),
        ("lorentz_fit_method", "revisit the fit method before re-deriving the thermal bridge"),
    ],
}

GOAL_TUNING_PRIORITY_RULES_SAXS: dict[str, list[tuple[str, str]]] = {
    "symptom": [
        ("savgol_window", "repair the noisy low-q signal before changing the windows"),
        ("q_bragg_min", "re-center the Bragg window around the active peak"),
        ("q_bragg_max", "keep the Bragg window wide enough to capture the peak cleanly"),
        ("q_corr_min", "stabilize the correlation floor before reusing L"),
    ],
    "risk": [
        ("q_corr_min", "keep the thickness chain away from unstable low-q data"),
        ("q_corr_max", "tighten the correlation ceiling before the next rerun"),
        ("tangent_lc_min_nm", "protect the tangent-derived thickness from implausible values"),
        ("lorentz_fit_method", "switch the backend only when the risk remains after preprocessing"),
    ],
    "joint": [
        ("q_corr_min", "align the SAXS thickness chain with the joint consistency check"),
        ("q_corr_max", "keep the thickness chain comparable across techniques"),
        ("tangent_lc_min_nm", "protect the joint-aware thickness estimate"),
        ("savgol_window", "stabilize the low-q shape before comparing across techniques"),
    ],
    "stability": [
        ("savgol_window", "keep the next round conservative by smoothing first"),
        ("q_corr_min", "avoid unnecessary lower-bound drift"),
        ("q_corr_max", "avoid unnecessary upper-bound drift"),
        ("tangent_lc_min_nm", "keep the thickness floor conservative"),
    ],
}
