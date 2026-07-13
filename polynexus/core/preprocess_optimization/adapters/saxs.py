from __future__ import annotations

import math
from dataclasses import replace
from typing import Any

from ..contracts import PreprocessEvidence, PreprocessIntent
from .base import TechniquePreprocessAdapter, WINDOW_STEPS, bounded_odd_windows, normalized_peak


BACKGROUND_STEPS = {"light": 0.02, "medium": 0.05, "strong": 0.10}


class SAXSPreprocessAdapter(TechniquePreprocessAdapter):
    technique = "SAXS"
    name = "saxs-preprocess"
    peak_tolerance = 0.01
    physical_keys = (
        "L_bragg",
        "L_corr_peak",
        "L_nm",
        "lc_nm",
        "Rg",
        "Q_invariant",
    )
    integrated_area_keys = ("Q_invariant",)
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
        if not str(base_config.get("background_file", "") or "").strip():
            return []
        if str(base_config.get("bg_scale_method", "") or "").strip() != "manual":
            return []
        current = float(base_config.get("bg_scale_value", 1.0) or 1.0)
        step = BACKGROUND_STEPS[intent.desired_effect]
        return [
            {"bg_scale_value": round(max(0.5, current - step), 12)},
            {"bg_scale_value": round(min(1.5, current + step), 12)},
        ]

    def smoothing_deltas(
        self,
        intent: PreprocessIntent,
        base_config: dict[str, Any],
    ) -> list[dict[str, Any]]:
        method = str(base_config.get("smooth_method", "savgol") or "savgol")
        if method == "moving_average":
            current = int(base_config.get("smooth_span", 5) or 5)
            step = WINDOW_STEPS[intent.desired_effect]
            return [
                {"smooth_span": value}
                for value in (
                    max(3, current - step),
                    min(31, current + step),
                )
                if value != current
            ]
        current = int(base_config.get("savgol_window", 7) or 7)
        order = int(base_config.get("savgol_order", 2) or 2)
        return [
            {"savgol_window": value}
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
        if isinstance(peaks, list) and peaks:
            return [
                normalized_peak(
                    peak,
                    center_keys=("q_peak", "q", "center"),
                    fwhm_keys=("q_peak_fwhm", "fwhm_q", "fwhm"),
                )
                for peak in peaks
                if isinstance(peak, dict)
            ]
        q_peak = output.get("q_peak")
        if q_peak is None:
            try:
                length = float(output.get("L_bragg"))
                q_peak = 2.0 * math.pi / length if length > 0 else None
            except (TypeError, ValueError):
                q_peak = None
        if q_peak is None:
            return []
        return [
            normalized_peak(
                {
                    "q_peak": q_peak,
                    "q_peak_fwhm": output.get("q_peak_fwhm"),
                    "area": output.get("q_peak_area", output.get("Q_invariant")),
                    "height": output.get("q_peak_height", output.get("q_peak_snr")),
                },
                center_keys=("q_peak",),
                fwhm_keys=("q_peak_fwhm",),
            )
        ]

    def build_evidence(
        self,
        candidate_id: str,
        control: Any,
        candidate: Any,
    ) -> PreprocessEvidence:
        evidence = super().build_evidence(candidate_id, control, candidate)
        specific = dict(evidence.technique_specific)
        # Core smooth_profile splits at detected intensity discontinuities,
        # so candidates never convolve across beamstop/mask boundaries.
        specific["cross_boundary_smoothing"] = False
        specific["background_file_present"] = bool(
            str(candidate.config.get("background_file", "") or "").strip()
        )
        return replace(evidence, technique_specific=specific)
