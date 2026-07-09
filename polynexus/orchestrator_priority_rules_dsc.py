from __future__ import annotations

JOINT_TUNING_PRIORITY_RULES_DSC: dict[str, list[tuple[str, str]]] = {
    "tm bidirectional gap": [
        ("Tm_search_low_C", "re-center the melting search window around the joint check"),
        ("Tm_search_high_C", "widen the melting search window only after the center is stable"),
        ("peak_function", "refit the endotherm before pushing the search window again"),
        ("baseline_type", "stabilize baseline handling before trusting the temperature shift"),
    ],
    "phi_c inconsistency": [
        ("peak_prominence_ratio", "tighten DSC event selection before comparing phi_c"),
        ("baseline_type", "reduce baseline bias before updating crystallinity"),
        ("smooth_window", "reduce noise before reading crystallinity-related events"),
    ],
}

GOAL_TUNING_PRIORITY_RULES_DSC: dict[str, list[tuple[str, str]]] = {
    "symptom": [
        ("peak_function", "repair the peak shape before nudging the search window again"),
        ("smooth_window", "suppress small oscillations before re-reading the peak"),
        ("tm_search_low_C", "re-center the melting search window around the active event"),
        ("tm_search_high_C", "keep the melting search window wide enough to capture the event"),
    ],
    "risk": [
        ("baseline_type", "reduce baseline risk before trusting the crystallinity path"),
        ("smooth_window", "stabilize the noisy edge before pushing the fit further"),
        ("peak_prominence_ratio", "avoid weak-event overfitting while lowering risk"),
        ("min_event_enthalpy_Jg", "keep marginal events from driving the next rerun"),
    ],
    "joint": [
        ("baseline_type", "align the thermal baseline before comparing across techniques"),
        ("peak_function", "make the thermal peak family easier to compare"),
        ("tm_search_low_C", "re-center the temperature bridge before accepting it"),
        ("tm_search_high_C", "keep the temperature bridge wide enough to be robust"),
    ],
    "stability": [
        ("baseline_type", "keep the next round conservative by stabilizing the baseline"),
        ("smooth_window", "prefer a smaller change when the curve is already close"),
        ("peak_function", "avoid unnecessary changes to the peak family"),
    ],
}
