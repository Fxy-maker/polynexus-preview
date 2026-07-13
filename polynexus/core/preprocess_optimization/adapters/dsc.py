from __future__ import annotations

from typing import Any

from ..contracts import PreprocessIntent
from .base import TechniquePreprocessAdapter, WINDOW_STEPS, bounded_odd_windows, normalized_peak


class DSCPreprocessAdapter(TechniquePreprocessAdapter):
    technique = "DSC"
    name = "dsc-preprocess"
    peak_tolerance = 1.0
    physical_keys = ("Tg_C", "Tm_peak_C", "Tc_peak_C", "Xc_pct")
    integrated_area_keys = ("DHm_Jg", "DHc_Jg", "DHcc_Jg")
    baseline_score_paths = (
        ("baseline_evidence", "baseline_stability_score"),
        ("feature_evidence", "baseline_evidence", "baseline_stability_score"),
        ("dsc_baseline_stability_score",),
    )

    def baseline_deltas(
        self,
        intent: PreprocessIntent,
        base_config: dict[str, Any],
    ) -> list[dict[str, Any]]:
        current = str(
            base_config.get("baseline_type", base_config.get("baseline_corr", "auto")) or "auto"
        )
        return [
            {"baseline_type": method}
            for method in ("auto", "linear", "polynomial", "spline", "tangential")
            if method != current
        ][:3]

    def smoothing_deltas(
        self,
        intent: PreprocessIntent,
        base_config: dict[str, Any],
    ) -> list[dict[str, Any]]:
        current = int(base_config.get("smooth_window", 11) or 11)
        order = int(base_config.get("smooth_order", 3) or 3)
        step = WINDOW_STEPS[intent.desired_effect]
        return [
            {"smooth_window": value}
            for value in bounded_odd_windows(
                current,
                step,
                minimum=3,
                maximum=31,
                order=order,
            )
        ]

    def normalize_peaks(self, output: dict[str, Any]) -> list[dict[str, Any]]:
        peaks = output.get("peak_components", output.get("peaks", []))
        if not isinstance(peaks, list):
            return []
        return [
            normalized_peak(
                peak,
                center_keys=("temperature", "center", "T_peak_C", "peak_C"),
                fwhm_keys=("fwhm_C", "fwhm", "width_C"),
            )
            for peak in peaks
            if isinstance(peak, dict)
        ]
