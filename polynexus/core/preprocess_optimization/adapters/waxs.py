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


class WAXSPreprocessAdapter(TechniquePreprocessAdapter):
    technique = "WAXS"
    name = "waxs-preprocess"
    peak_tolerance = 0.10
    physical_keys = ("Xc_pct", "D_Scherrer_nm", "D_WH_nm")
    baseline_score_paths = (
        ("background_evidence", "instrument_background_stability_score"),
        (
            "feature_evidence",
            "background_evidence",
            "instrument_background_stability_score",
        ),
        ("instrument_background_stability_score",),
        ("background_stability_score",),
    )

    def baseline_deltas(
        self,
        intent: PreprocessIntent,
        base_config: dict[str, Any],
    ) -> list[dict[str, Any]]:
        current = str(base_config.get("instrument_background_method", "arpls") or "arpls")
        candidates: list[dict[str, Any]] = []
        if current == "arpls":
            low, high = STRENGTH_MULTIPLIERS[intent.desired_effect]
            lam = float(base_config.get("arpls_lam", 1e5) or 1e5)
            candidates.extend(
                [
                    {"arpls_lam": max(1e4, min(1e8, lam * low))},
                    {"arpls_lam": max(1e4, min(1e8, lam * high))},
                    {
                        "arpls_diff_order": 1
                        if int(base_config.get("arpls_diff_order", 2) or 2) == 2
                        else 2
                    },
                ]
            )
        for method in ("arpls", "polynomial", "spline", "linear", "none"):
            if method != current:
                candidates.append({"instrument_background_method": method})
                break
        return candidates

    def smoothing_deltas(
        self,
        intent: PreprocessIntent,
        base_config: dict[str, Any],
    ) -> list[dict[str, Any]]:
        current = int(base_config.get("smooth_window", 5) or 5)
        order = int(base_config.get("smooth_order", 3) or 3)
        return [
            {"smooth_window": value}
            for value in bounded_odd_windows(
                current,
                WINDOW_STEPS[intent.desired_effect],
                minimum=3,
                maximum=15,
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
                center_keys=("center", "two_theta"),
                fwhm_keys=("fwhm", "fwhm_deg", "FWHM"),
            )
            for peak in peaks
            if isinstance(peak, dict)
        ]
