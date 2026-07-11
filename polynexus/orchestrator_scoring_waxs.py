from __future__ import annotations

from typing import Any


def _waxs_support_snapshot(
    self: Any,
    output: dict[str, Any],
    residuals_pattern: dict[str, Any],
    analysis_evidence: dict[str, Any],
) -> dict[str, float]:
    if self.technique != "waxs":
        return {
            "peak_support_score": 1.0,
            "background_stability_score": 1.0,
            "phase_support_score": 1.0,
            "size_support_score": 1.0,
            "waxs_support_score": 1.0,
        }

    output = dict(output or {})
    residuals_pattern = dict(residuals_pattern or {})
    analysis_evidence = dict(analysis_evidence or {})
    peak_evidence = analysis_evidence.get("peak_evidence", {})
    if not isinstance(peak_evidence, dict):
        peak_evidence = {}
    background_evidence = analysis_evidence.get("background_evidence", {})
    if not isinstance(background_evidence, dict):
        background_evidence = {}
    phase_evidence = analysis_evidence.get("phase_evidence", {})
    if not isinstance(phase_evidence, dict):
        phase_evidence = {}

    constraint_summary = analysis_evidence.get("constraint_summary", {})
    triggered_names: set[str] = set()
    if isinstance(constraint_summary, dict):
        nested = constraint_summary.get("triggered_names", {})
        if isinstance(nested, dict):
            for names in nested.values():
                if not isinstance(names, list):
                    continue
                triggered_names.update(
                    str(item).strip() for item in names if str(item).strip()
                )

    symptom_names = {
        str(item.get("name", "")).strip()
        for item in self._analysis_symptoms(analysis_evidence)
        if isinstance(item, dict) and str(item.get("name", "")).strip()
    }
    residual_type = str(
        residuals_pattern.get("residual_type", "")
        or analysis_evidence.get("residual_evidence", {}).get("residual_type", "")
        or ""
    ).strip().lower()

    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))

    def _spread_score(
        spread: float | None,
        limit: float,
        default: float = 0.72,
    ) -> float:
        if spread is None:
            return default
        return _clamp(1.0 - max(0.0, float(spread)) / max(limit, 1e-9))

    peak_count = self._safe_float(peak_evidence.get("peak_count", output.get("n_peaks")))
    peak_gap_spread = self._safe_float(peak_evidence.get("peak_gap_spread"))
    peak_width_spread = self._safe_float(peak_evidence.get("peak_width_spread"))

    count_score = 0.0
    if peak_count > 0:
        count_score = min(1.0, peak_count / 2.0)
    gap_score = _spread_score(peak_gap_spread, 0.45)
    width_score = _spread_score(peak_width_spread, 0.55)
    peak_support_score = _clamp(0.56 * count_score + 0.24 * gap_score + 0.20 * width_score)
    if peak_count and peak_count < 2:
        peak_support_score -= 0.16
    if "peak_visibility" in triggered_names or "peak_count_insufficient" in triggered_names:
        peak_support_score -= 0.15
    if "peak_family_unstable" in triggered_names:
        peak_support_score -= 0.12
    if "peak_width_nonphysical" in triggered_names:
        peak_support_score -= 0.12
    if residual_type in {
        "peak_position_bias",
        "peak_width_mismatch",
        "peak_count_underfit",
        "peak_count_overfit",
    }:
        peak_support_score -= 0.08
    peak_support_score = _clamp(peak_support_score)

    offset = self._safe_float(
        background_evidence.get("two_theta_offset", output.get("two_theta_offset"))
    )
    offset_score = _clamp(1.0 - abs(offset) / 0.08)
    background_method = str(
        background_evidence.get("background_method", output.get("background_method", ""))
        or ""
    ).strip()
    background_support = _spread_score(
        self._safe_float(background_evidence.get("background_stability_spread")),
        0.40,
        default=0.80,
    )
    if background_method:
        background_support = max(background_support, 0.60)
    if "background_drift" in triggered_names:
        background_support -= 0.18
    if "two_theta_offset" in symptom_names:
        background_support -= 0.08
    if residual_type in {"baseline_drift", "background_bias", "peak_position_bias"}:
        background_support -= 0.08
    background_stability_score = _clamp(0.55 * offset_score + 0.45 * background_support)

    peak_count = int(round(peak_count))
    peak_positions = [
        self._safe_float(item.get("two_theta"))
        for item in output.get("peaks", [])
        if isinstance(item, dict)
    ]
    peak_widths = [
        self._safe_float(item.get("fwhm_deg"))
        for item in output.get("peaks", [])
        if isinstance(item, dict)
    ]
    peak_width_spread = max(
        (self._safe_float(value) for value in peak_widths if value is not None),
        default=0.0,
    ) if peak_widths else 0.0
    phase_evidence = phase_evidence if isinstance(phase_evidence, dict) else {}
    x_pct = self._safe_float(phase_evidence.get("Xc_pct", output.get("Xc_pct")))
    crystallinity_method = (
        phase_evidence.get(
            "crystallinity_method",
            output.get("crystallinity_method", output.get("Xc_method", "")),
        )
        or ""
    ).strip().lower()
    method_support = 0.55
    if crystallinity_method:
        method_support = 0.72
    if crystallinity_method in {"peak_deconvolution", "peak_area"}:
        method_support = 1.0
    elif crystallinity_method in {"no_sharp_peak", "amorphous"}:
        method_support = 0.35
    x_support = 1.0 if x_pct > 0 else 0.0
    peak_link = (
        0.35 + 0.65 * peak_support_score
        if peak_count >= 2
        else 0.18 + 0.45 * peak_support_score
    )
    phase_support_score = _clamp(
        0.30 * x_support + 0.30 * method_support + 0.40 * peak_link
    )
    if "crystallinity_without_peak_support" in triggered_names:
        phase_support_score -= 0.25
    if residual_type in {
        "amorphous_background_bias",
        "peak_count_underfit",
        "peak_position_bias",
    }:
        phase_support_score -= 0.05
    if peak_count and peak_count < 2:
        phase_support_score -= 0.10
    phase_support_score = _clamp(phase_support_score)

    size_value = self._safe_float(
        phase_evidence.get("D_Scherrer_nm", output.get("D_Scherrer_nm"))
    )
    size_support = 1.0 if size_value > 0 else 0.0
    width_health = _spread_score(peak_width_spread, 0.60, default=0.70)
    if peak_count >= 2:
        peak_size_link = 1.0
    elif peak_count > 0:
        peak_size_link = 0.25
    else:
        peak_size_link = 0.0
    size_support_score = _clamp(
        0.35 * size_support + 0.35 * peak_size_link + 0.30 * width_health
    )
    if "size_without_multi_peak_support" in triggered_names:
        size_support_score -= 0.25
    if "peak_width_nonphysical" in triggered_names:
        size_support_score -= 0.10
    if residual_type in {"peak_width_mismatch", "peak_count_underfit"}:
        size_support_score -= 0.05
    size_support_score = _clamp(size_support_score)

    waxs_support_score = _clamp(
        0.35 * peak_support_score
        + 0.25 * background_stability_score
        + 0.25 * phase_support_score
        + 0.15 * size_support_score
    )

    return {
        "peak_support_score": round(peak_support_score, 3),
        "background_stability_score": round(background_stability_score, 3),
        "phase_support_score": round(phase_support_score, 3),
        "size_support_score": round(size_support_score, 3),
        "waxs_support_score": round(waxs_support_score, 3),
    }
