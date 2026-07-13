from __future__ import annotations

from dataclasses import replace
from typing import Any

from ..contracts import PreprocessEvidence, PreprocessIntent
from .base import TechniquePreprocessAdapter, normalized_peak, relative_change


ORDER_STEPS = {"light": 1, "medium": 2, "strong": 3}
LB_STEPS = {"light": 1.0, "medium": 2.5, "strong": 5.0}
GB_STEPS = {"light": 0.05, "medium": 0.10, "strong": 0.20}


class NMRPreprocessAdapter(TechniquePreprocessAdapter):
    technique = "NMR"
    name = "nmr-preprocess"
    peak_tolerance = 0.02
    physical_keys = ("Xc_pct", "dominant_peak_ppm")
    integrated_area_keys = ("peak_area_total",)
    baseline_score_paths = (
        ("baseline_evidence", "baseline_stability_score"),
        ("feature_evidence", "baseline_evidence", "baseline_stability_score"),
        ("baseline_stability_score",),
    )

    def baseline_deltas(
        self,
        intent: PreprocessIntent,
        base_config: dict[str, Any],
    ) -> list[dict[str, Any]]:
        order = int(base_config.get("baseline_order", 5) or 5)
        step = ORDER_STEPS[intent.desired_effect]
        deltas = [
            {"baseline_order": value}
            for value in (max(1, order - step), min(9, order + step))
            if value != order
        ]
        if intent.direction == "change_method":
            current = str(base_config.get("baseline_method", "polynomial") or "polynomial")
            deltas.extend(
                {"baseline_method": method}
                for method in ("polynomial", "linear", "spline", "simple_polynomial")
                if method != current
            )
        return deltas[:4]

    def smoothing_deltas(
        self,
        intent: PreprocessIntent,
        base_config: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if str(base_config.get("spectrum_mode", "") or "").strip().lower() != "fid":
            return []
        lb = float(base_config.get("lb_Hz", 10.0) or 10.0)
        lb_step = LB_STEPS[intent.desired_effect]
        deltas = [
            {"lb_Hz": round(max(0.1, lb - lb_step), 12)},
            {"lb_Hz": round(min(40.0, lb + lb_step), 12)},
        ]
        if str(base_config.get("apodization", "exponential")) == "gaussian":
            gb = float(base_config.get("gb", 0.1) or 0.1)
            gb_step = GB_STEPS[intent.desired_effect]
            deltas.extend(
                [
                    {"gb": round(max(0.0, gb - gb_step), 12)},
                    {"gb": round(min(1.0, gb + gb_step), 12)},
                ]
            )
        return deltas

    def normalize_peaks(self, output: dict[str, Any]) -> list[dict[str, Any]]:
        peaks = output.get("peaks", [])
        if not isinstance(peaks, list):
            return []
        return [
            normalized_peak(
                peak,
                center_keys=("ppm", "center"),
                fwhm_keys=("fwhm_ppm", "fwhm"),
            )
            for peak in peaks
            if isinstance(peak, dict)
        ]

    def build_evidence(
        self,
        candidate_id: str,
        control: Any,
        candidate: Any,
    ) -> PreprocessEvidence:
        evidence = super().build_evidence(candidate_id, control, candidate)
        specific = dict(evidence.technique_specific)
        for key in ("mean_fwhm_ppm", "median_snr"):
            change = relative_change(
                control.output_parameters.get(key),
                candidate.output_parameters.get(key),
            )
            if change is not None:
                specific[f"{key}_change"] = change
        specific["zero_fill_unchanged"] = (
            control.config.get("fid_zero_fill_factor")
            == candidate.config.get("fid_zero_fill_factor")
        )
        return replace(evidence, technique_specific=specific)
