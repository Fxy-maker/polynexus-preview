from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


@dataclass
class IRResidualPattern:
    rmse: float
    r_squared: float
    residual_type: str
    max_residual_region: str
    peak_regions: list[dict]
    summary: str

    def to_dict(self) -> dict:
        return asdict(self)


class IRResidualAnalyzer:
    VALID_WN_MIN = 550.0
    VALID_WN_MAX = 4000.0

    @classmethod
    def analyze(
        cls,
        wavenumber: np.ndarray,
        absorbance: np.ndarray,
        fit: np.ndarray | None = None,
    ) -> IRResidualPattern:
        wn = np.asarray(wavenumber, dtype=float)
        obs = np.asarray(absorbance, dtype=float)
        if fit is None:
            pred = cls._baseline_fit(wn, obs)
        else:
            pred = np.asarray(fit, dtype=float)
            if len(pred) == len(obs):
                baseline = cls._baseline_fit(wn, obs)
                pred = np.where(np.isfinite(pred), pred, baseline)
            else:
                pred = cls._baseline_fit(wn, obs)

        valid = (
            np.isfinite(wn)
            & np.isfinite(obs)
            & np.isfinite(pred)
            & (wn >= cls.VALID_WN_MIN)
            & (wn <= cls.VALID_WN_MAX)
        )
        if np.count_nonzero(valid) < 8:
            return IRResidualPattern(
                rmse=0.0,
                r_squared=0.0,
                residual_type="random",
                max_residual_region="unknown",
                peak_regions=[],
                summary="IR residual data is insufficient for pattern classification.",
            )

        wn_valid = wn[valid]
        obs_valid = obs[valid]
        pred_valid = pred[valid]
        residuals = obs_valid - pred_valid
        rmse = float(np.sqrt(np.mean(residuals**2)))
        ss_res = float(np.sum(residuals**2))
        ss_tot = float(np.sum((obs_valid - np.mean(obs_valid)) ** 2))
        r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0

        max_idx = int(np.argmax(np.abs(residuals)))
        max_wn = float(wn_valid[max_idx])
        peak_regions = cls._peak_regions(wn_valid, residuals, rmse)
        residual_type = cls._classify(wn_valid, residuals, rmse, peak_regions)
        direction = "positive residual (fit too low)" if residuals[max_idx] > 0 else "negative residual (fit too high)"
        summary = (
            f"IR residual maximum near {max_wn:.1f} cm^-1 with {direction}; "
            f"RMSE={rmse:.4g}, residual_type={residual_type}."
        )
        if residual_type in {"key_band_mismatch", "crowded_band_underfit"}:
            summary += " Prefer tuning peak_fit_window_cm1, peak_prominence_min, peak_height_min, or peak_distance."
        elif residual_type == "over_smoothed_weak_bands":
            summary += " Prefer reducing smooth_window and then re-checking weak bands before raising confidence."
        elif residual_type in {"baseline_drift_low_wn", "baseline_drift_high_wn", "normalization_bias"}:
            summary += " Prefer tuning baseline_method or normalization_method before peak parameters."
        elif residual_type == "peak_mismatch":
            summary += " Prefer tuning peak_threshold, peak_distance, lineshape, or peak_fit_window_cm1."
        elif residual_type in {"noise", "noise_dominant"}:
            summary += " Prefer increasing smooth_window, keeping it odd and greater than smooth_order."

        return IRResidualPattern(
            rmse=rmse,
            r_squared=float(r_squared),
            residual_type=residual_type,
            max_residual_region=f"{max_wn:.1f} cm^-1",
            peak_regions=peak_regions,
            summary=summary,
        )

    @staticmethod
    def _baseline_fit(wn: np.ndarray, y: np.ndarray) -> np.ndarray:
        valid = np.isfinite(wn) & np.isfinite(y)
        if np.count_nonzero(valid) < 3:
            return np.zeros_like(y, dtype=float)
        x = wn[valid]
        obs = y[valid]
        order = 2 if len(obs) > 20 else 1
        coeff = np.polyfit(x, obs, order)
        return np.polyval(coeff, wn)

    @staticmethod
    def _peak_regions(wn: np.ndarray, residuals: np.ndarray, rmse: float) -> list[dict]:
        if rmse <= 0:
            return []
        threshold = rmse * 1.5
        mask = np.abs(residuals) >= threshold
        regions = []
        start = None
        for idx, hot in enumerate(mask):
            if hot and start is None:
                start = idx
            elif not hot and start is not None:
                regions.append((start, idx - 1))
                start = None
        if start is not None:
            regions.append((start, len(mask) - 1))

        out = []
        for left, right in regions[:6]:
            local = residuals[left : right + 1]
            out.append(
                {
                    "wavenumber_start": float(wn[left]),
                    "wavenumber_end": float(wn[right]),
                    "sample_count": int(right - left + 1),
                    "mean_residual": float(np.mean(local)),
                    "max_abs_residual": float(np.max(np.abs(local))),
                    "sign": "positive" if float(np.mean(local)) >= 0 else "negative",
                }
            )
        return out

    @staticmethod
    def _classify(wn: np.ndarray, residuals: np.ndarray, rmse: float, peak_regions: list[dict]) -> str:
        if rmse <= 0:
            return "random"

        low_edge = wn < 700.0
        high_edge = wn > 3600.0
        low_mean = float(np.mean(residuals[low_edge])) if np.count_nonzero(low_edge) > 8 else None
        high_mean = float(np.mean(residuals[high_edge])) if np.count_nonzero(high_edge) > 8 else None
        if low_mean is not None or high_mean is not None:
            low_abs = abs(low_mean) if low_mean is not None else 0.0
            high_abs = abs(high_mean) if high_mean is not None else 0.0
            if low_mean is not None and high_mean is not None:
                if low_abs > rmse * 1.15 and high_abs > rmse * 1.15 and np.sign(low_mean) != np.sign(high_mean):
                    return "normalization_bias"
                if low_abs > high_abs * 1.35 and low_abs > rmse * 1.15:
                    return "baseline_drift_low_wn"
                if high_abs > low_abs * 1.35 and high_abs > rmse * 1.15:
                    return "baseline_drift_high_wn"
            elif low_mean is not None and low_abs > rmse * 1.15:
                return "baseline_drift_low_wn"
            elif high_mean is not None and high_abs > rmse * 1.15:
                return "baseline_drift_high_wn"

        signs = np.sign(residuals)
        sign_changes = np.count_nonzero(np.diff(signs) != 0)
        sign_change_ratio = sign_changes / max(len(residuals) - 1, 1)
        if sign_change_ratio > 0.58 and np.std(residuals) > rmse * 0.8:
            return "noise_dominant"

        region_widths = [
            abs(float(region["wavenumber_end"]) - float(region["wavenumber_start"]))
            for region in peak_regions
            if isinstance(region, dict) and region.get("wavenumber_start") is not None and region.get("wavenumber_end") is not None
        ]
        if len(peak_regions) >= 3 and region_widths:
            median_width = float(np.median(region_widths))
            if median_width <= 70.0 or sign_change_ratio < 0.42:
                return "crowded_band_underfit"

        if peak_regions:
            strongest = max(
                peak_regions,
                key=lambda region: float(region.get("max_abs_residual", 0.0) or 0.0),
            )
            width = abs(float(strongest["wavenumber_end"]) - float(strongest["wavenumber_start"]))
            sample_count = int(strongest.get("sample_count", 0))
            mean_residual = abs(float(strongest.get("mean_residual", 0.0)))
            max_abs = float(strongest.get("max_abs_residual", 0.0))
            if (
                12.0 <= width <= 140.0
                and sample_count >= 4
                and max_abs > rmse * 1.8
                and mean_residual > rmse * 0.7
            ):
                return "key_band_mismatch"
            if (
                len(peak_regions) <= 2
                and width >= 25.0
                and sign_change_ratio < 0.32
                and max_abs <= rmse * 1.8
            ):
                return "over_smoothed_weak_bands"
            if (
                3.0 <= width <= 180.0
                and sample_count >= 4
                and max_abs > rmse * 2.0
                and mean_residual > rmse * 0.8
            ):
                return "key_band_mismatch"
        return "random"
