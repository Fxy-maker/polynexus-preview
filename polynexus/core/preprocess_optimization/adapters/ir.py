from __future__ import annotations

from typing import Any

from ..contracts import PreprocessIntent
from .base import (
    STRENGTH_MULTIPLIERS,
    TechniquePreprocessAdapter,
    WINDOW_STEPS,
    bounded_odd_windows,
    normalized_peak,
)


class IRPreprocessAdapter(TechniquePreprocessAdapter):
    technique = "IR"
    name = "ir-preprocess"
    peak_tolerance = 2.0
    physical_keys = ("Xc_pct", "polymer_score")
    baseline_score_paths = (
        ("background_evidence", "baseline_stability_score"),
        ("feature_evidence", "background_evidence", "baseline_stability_score"),
        ("baseline_stability_score",),
    )

    def baseline_deltas(
        self,
        intent: PreprocessIntent,
        base_config: dict[str, Any],
    ) -> list[dict[str, Any]]:
        current = str(base_config.get("baseline_method", "rubberband") or "rubberband")
        if current == "als":
            low, high = STRENGTH_MULTIPLIERS[intent.desired_effect]
            lam = float(base_config.get("baseline_lam", 1e6) or 1e6)
            asymmetry = float(base_config.get("baseline_p", 0.001) or 0.001)
            return [
                {"baseline_lam": lam * low},
                {"baseline_lam": lam * high},
                {"baseline_p": max(1e-6, asymmetry * low)},
                {"baseline_p": min(0.5, asymmetry * high)},
            ]
        return [
            {"baseline_method": method}
            for method in ("rubberband", "als", "linear", "polynomial", "mute_zone", "none")
            if method != current
        ][:3]

    def smoothing_deltas(
        self,
        intent: PreprocessIntent,
        base_config: dict[str, Any],
    ) -> list[dict[str, Any]]:
        current = int(base_config.get("smooth_window", 7) or 7)
        order = int(base_config.get("smooth_order", 3) or 3)
        return [
            {"smooth_window": value}
            for value in bounded_odd_windows(
                current,
                WINDOW_STEPS[intent.desired_effect],
                minimum=3,
                maximum=31,
                order=order,
            )
        ]

    def normalize_peaks(self, output: dict[str, Any]) -> list[dict[str, Any]]:
        peaks = output.get("peaks", [])
        if not isinstance(peaks, list):
            return []
        return [
            normalized_peak(
                peak,
                center_keys=("wavenumber", "center"),
                fwhm_keys=("fwhm_cm1", "fwhm"),
            )
            for peak in peaks
            if isinstance(peak, dict)
        ]
