from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


@dataclass
class DSCResidualPattern:
    rmse: float
    r_squared: float
    residual_type: str
    max_residual_region: str
    peak_regions: list[dict]
    summary: str

    def to_dict(self) -> dict:
        return asdict(self)


class DSCResidualAnalyzer:
    VALID_T_MIN = 100.0
    VALID_T_MAX = 300.0

    @classmethod
    def analyze(
        cls,
        temperature: np.ndarray,
        heat_flow: np.ndarray,
        fit: np.ndarray | None = None,
    ) -> DSCResidualPattern:
        t = np.asarray(temperature, dtype=float)
        y = np.asarray(heat_flow, dtype=float)
        if fit is None:
            y_fit = cls._baseline_fit(t, y)
        else:
            y_fit = np.asarray(fit, dtype=float)
            if len(y_fit) == len(y):
                baseline = cls._baseline_fit(t, y)
                y_fit = np.where(np.isfinite(y_fit), y_fit, baseline)

        valid = (
            np.isfinite(t)
            & np.isfinite(y)
            & np.isfinite(y_fit)
            & (t >= cls.VALID_T_MIN)
            & (t <= cls.VALID_T_MAX)
        )
        if np.count_nonzero(valid) < 8:
            return DSCResidualPattern(
                rmse=0.0,
                r_squared=0.0,
                residual_type="random",
                max_residual_region="unknown",
                peak_regions=[],
                summary="DSC residual data is too sparse to classify reliably.",
            )

        t = t[valid]
        y = y[valid]
        y_fit = y_fit[valid]
        residuals = y - y_fit
        rmse = float(np.sqrt(np.mean(residuals**2)))
        ss_res = float(np.sum(residuals**2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0

        abs_res = np.abs(residuals)
        max_idx = int(np.argmax(abs_res))
        max_temp = float(t[max_idx])
        peak_regions = cls._peak_regions(t, residuals, rmse)
        residual_type = cls._classify(t, residuals, rmse, peak_regions)
        direction = "positive" if residuals[max_idx] > 0 else "negative"

        summary = cls._summary_text(residual_type, max_temp, rmse, direction, peak_regions)
        return DSCResidualPattern(
            rmse=rmse,
            r_squared=float(r_squared),
            residual_type=residual_type,
            max_residual_region=f"T={max_temp:.1f}C",
            peak_regions=peak_regions,
            summary=summary,
        )

    @staticmethod
    def _baseline_fit(t: np.ndarray, y: np.ndarray) -> np.ndarray:
        valid = np.isfinite(t) & np.isfinite(y)
        if np.count_nonzero(valid) < 3:
            return np.zeros_like(y, dtype=float)
        t_valid = t[valid]
        y_valid = y[valid]
        order = 2 if len(t_valid) > 20 else 1
        coeff = np.polyfit(t_valid, y_valid, order)
        return np.polyval(coeff, t)

    @staticmethod
    def _peak_regions(t: np.ndarray, residuals: np.ndarray, rmse: float) -> list[dict]:
        if rmse <= 0:
            return []
        threshold = rmse * 1.5
        mask = np.abs(residuals) >= threshold
        regions: list[tuple[int, int]] = []
        start = None
        for idx, is_hot in enumerate(mask):
            if is_hot and start is None:
                start = idx
            elif not is_hot and start is not None:
                regions.append((start, idx - 1))
                start = None
        if start is not None:
            regions.append((start, len(mask) - 1))

        out: list[dict] = []
        for left, right in regions[:6]:
            local = residuals[left : right + 1]
            local_t = t[left : right + 1]
            strong_local = local[np.abs(local) >= max(rmse * 0.25, 1e-12)]
            if strong_local.size >= 2:
                sign_changes = int(np.count_nonzero(np.diff(np.sign(strong_local)) != 0))
            else:
                sign_changes = 0
            out.append(
                {
                    "temperature_start": float(local_t[0]),
                    "temperature_end": float(local_t[-1]),
                    "center_temperature": float(np.mean(local_t)),
                    "width_C": float(abs(local_t[-1] - local_t[0])),
                    "sample_count": int(right - left + 1),
                    "mean_residual": float(np.mean(local)),
                    "signed_mean": float(np.mean(local)),
                    "max_abs_residual": float(np.max(np.abs(local))),
                    "positive_fraction": float(np.mean(local > rmse * 0.25)),
                    "negative_fraction": float(np.mean(local < -rmse * 0.25)),
                    "sign_changes": sign_changes,
                    "sign": "positive" if float(np.mean(local)) >= 0 else "negative",
                }
            )
        return out

    @classmethod
    def _classify(cls, t: np.ndarray, residuals: np.ndarray, rmse: float, peak_regions: list[dict]) -> str:
        if rmse <= 0:
            return "random"

        low_mask = t < 130.0
        high_mask = t > 270.0
        low_count = int(np.count_nonzero(low_mask))
        high_count = int(np.count_nonzero(high_mask))
        low_mean = float(np.mean(residuals[low_mask])) if low_count > 5 else None
        high_mean = float(np.mean(residuals[high_mask])) if high_count > 5 else None
        low_cover = (
            float(np.mean(np.abs(residuals[low_mask]) >= rmse * 0.75))
            if low_count > 5
            else 0.0
        )
        high_cover = (
            float(np.mean(np.abs(residuals[high_mask]) >= rmse * 0.75))
            if high_count > 5
            else 0.0
        )
        low_strength = low_mean is not None and abs(low_mean) > rmse * 1.2 and low_cover >= 0.7
        high_strength = high_mean is not None and abs(high_mean) > rmse * 1.2 and high_cover >= 0.7

        if low_strength or high_strength:
            if low_strength and high_strength:
                return "baseline_drift"
            return "baseline_drift_low_t" if low_strength else "baseline_drift_high_t"

        if not peak_regions:
            return "noise_dominant" if cls._sign_change_ratio(residuals) >= 0.18 else "random"

        dominant = max(peak_regions, key=lambda region: float(region.get("max_abs_residual", 0.0)))
        center = float(dominant.get("center_temperature", float(np.mean(t))))
        width = float(dominant.get("width_C", abs(float(dominant["temperature_end"]) - float(dominant["temperature_start"]))))
        sample_count = int(dominant.get("sample_count", 0))
        mean_residual = abs(float(dominant.get("mean_residual", 0.0)))
        max_abs = float(dominant.get("max_abs_residual", 0.0))
        sign_changes = int(dominant.get("sign_changes", 0))
        positive_fraction = float(dominant.get("positive_fraction", 0.0))
        negative_fraction = float(dominant.get("negative_fraction", 0.0))

        if sign_changes >= 1 and positive_fraction >= 0.30 and negative_fraction >= 0.30 and max_abs > rmse * 1.8:
            return "exo_up_down_confusion"
        strong_regions = [
            region
            for region in peak_regions
            if float(region.get("max_abs_residual", 0.0)) > rmse * 1.8
            and int(region.get("sample_count", 0)) >= 4
        ]
        if len(strong_regions) >= 2:
            centers = [float(region.get("center_temperature", 0.0)) for region in strong_regions]
            widths = [float(region.get("width_C", 0.0)) for region in strong_regions]
            signs = {str(region.get("sign", "")) for region in strong_regions}
            center_span = max(centers) - min(centers)
            if len(signs) == 1:
                if min(centers) < 140.0 and max(centers) > 220.0:
                    return "segment_split_issue"
                close_centers = [
                    abs(a - b)
                    for idx, a in enumerate(centers)
                    for b in centers[idx + 1 :]
                ]
                if close_centers and min(close_centers) <= 22.0:
                    return "cold_crystallization_overlap"
                return "multi_event_underfit"
            if min(centers) < 140.0 and max(centers) > 220.0:
                return "segment_split_issue"
            if center_span <= 8.0 and max(widths) <= 6.0:
                return "event_window_too_narrow"
            if center_span >= 24.0 and max(widths) >= 12.0:
                return "event_window_too_wide"
            if center_span >= 12.0 and max(widths) >= 8.0:
                return "melting_peak_shift"
            return "multi_event_underfit"
        if 35.0 <= center <= 130.0 and width >= 8.0 and sample_count >= 5 and mean_residual > rmse * 0.8:
            return "tg_step_missing"
        if 150.0 <= center <= 240.0:
            if width <= 8.0 and sample_count >= 4 and max_abs > rmse * 1.8:
                return "event_window_too_narrow"
            if width >= 28.0 and sample_count >= 4 and max_abs > rmse * 1.4:
                return "event_window_too_wide"
            return "melting_peak_shift"
        if width <= 8.0 and sample_count >= 4 and max_abs > rmse * 1.8:
            return "event_window_too_narrow"
        if width >= 28.0 and sample_count >= 4 and max_abs > rmse * 1.4:
            return "event_window_too_wide"
        if cls._sign_change_ratio(residuals) >= 0.24:
            return "noise_dominant"
        return "peak_shift"

    @staticmethod
    def _sign_change_ratio(values: np.ndarray) -> float:
        arr = np.asarray(values, dtype=float)
        arr = arr[np.isfinite(arr)]
        if arr.size < 2:
            return 0.0
        threshold = max(float(np.nanstd(arr)) * 0.12, 1e-9)
        signs = np.sign(np.where(np.abs(arr) >= threshold, arr, 0.0))
        signs = signs[signs != 0]
        if signs.size < 2:
            return 0.0
        changes = np.count_nonzero(np.diff(signs) != 0)
        return float(changes) / float(signs.size - 1)

    @staticmethod
    def _summary_text(
        residual_type: str,
        max_temp: float,
        rmse: float,
        direction: str,
        peak_regions: list[dict],
    ) -> str:
        region_count = len(peak_regions)
        summary = (
            f"Dominant {direction} residual near T={max_temp:.1f}C; "
            f"type={residual_type}; RMSE={rmse:.4g}; regions={region_count}."
        )
        if residual_type in {"baseline_drift", "baseline_drift_low_t", "baseline_drift_high_t"}:
            summary += " Check baseline handling before re-tuning event thresholds."
        elif residual_type in {"peak_shift", "melting_peak_shift"}:
            summary += " Re-center the thermal event window before accepting the peak location."
        elif residual_type == "tg_step_missing":
            summary += " Re-check Tg support and Cp-step visibility."
        elif residual_type == "cold_crystallization_overlap":
            summary += " Separate cold crystallization from the melting window."
        elif residual_type == "event_window_too_narrow":
            summary += " Widen the event window before re-reading the event."
        elif residual_type == "event_window_too_wide":
            summary += " Narrow the event window before trusting the fit."
        elif residual_type == "exo_up_down_confusion":
            summary += " Verify the exo-up convention and signed enthalpy."
        elif residual_type == "multi_event_underfit":
            summary += " Allow multiple thermal events before forcing a single peak."
        elif residual_type == "segment_split_issue":
            summary += " Check whether scan segmentation is splitting one thermal event."
        elif residual_type in {"noise", "noise_dominant"}:
            summary += " Stabilize preprocessing and smoothing before another attempt."
        return summary
