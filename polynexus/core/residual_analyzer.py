from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class ResidualPattern:
    rmse: float
    r_squared: float
    residual_type: str
    max_residual_region: str
    peak_regions: list[dict[str, Any]]
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ResidualAnalyzer:
    @staticmethod
    def analyze(y_obs: np.ndarray, y_fit: np.ndarray, two_theta: np.ndarray) -> ResidualPattern:
        obs, fit, theta = ResidualAnalyzer._prepare_arrays(y_obs, y_fit, two_theta)
        if len(obs) == 0:
            return ResidualPattern(
                rmse=0.0,
                r_squared=0.0,
                residual_type="random",
                max_residual_region="unknown",
                peak_regions=[],
                summary="残差数据不足，无法判断残差模式。",
            )

        residuals = obs - fit
        rmse = float(np.sqrt(np.mean(residuals**2)))
        r_squared = ResidualAnalyzer._r_squared(obs, fit)
        max_index = int(np.argmax(np.abs(residuals)))
        max_region = ResidualAnalyzer._max_residual_region(theta, residuals, max_index, rmse)
        peak_regions = ResidualAnalyzer._peak_regions(theta, residuals)

        residual_type = "random"
        if ResidualAnalyzer._has_background_drift(theta, residuals, rmse):
            residual_type = "background_drift"
        elif ResidualAnalyzer._has_systematic_peak(residuals, max_index, rmse):
            residual_type = "systematic_peak"

        summary = ResidualAnalyzer._summary(residual_type, max_region, residuals, max_index, rmse, r_squared)
        return ResidualPattern(
            rmse=round(rmse, 6),
            r_squared=round(r_squared, 6),
            residual_type=residual_type,
            max_residual_region=max_region,
            peak_regions=peak_regions,
            summary=summary,
        )

    @staticmethod
    def _prepare_arrays(y_obs: np.ndarray, y_fit: np.ndarray, two_theta: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        obs = np.asarray(y_obs, dtype=float).ravel()
        fit = np.asarray(y_fit, dtype=float).ravel()
        theta = np.asarray(two_theta, dtype=float).ravel()
        n = min(len(obs), len(fit), len(theta))
        if n <= 0:
            return np.array([]), np.array([]), np.array([])
        obs, fit, theta = obs[:n], fit[:n], theta[:n]
        mask = np.isfinite(obs) & np.isfinite(fit) & np.isfinite(theta) & (theta >= 5.0) & (theta <= 40.0)
        return obs[mask], fit[mask], theta[mask]

    @staticmethod
    def _r_squared(obs: np.ndarray, fit: np.ndarray) -> float:
        ss_res = float(np.sum((obs - fit) ** 2))
        ss_tot = float(np.sum((obs - np.mean(obs)) ** 2))
        if ss_tot <= 0:
            return 1.0 if ss_res <= 1e-12 else 0.0
        value = 1.0 - ss_res / ss_tot
        return value if math.isfinite(value) else 0.0

    @staticmethod
    def _has_background_drift(theta: np.ndarray, residuals: np.ndarray, rmse: float) -> bool:
        low_mask = theta < 10.0
        if np.count_nonzero(low_mask) < 5 or rmse <= 0:
            return False
        low_mean = float(np.mean(residuals[low_mask]))
        return low_mean > rmse * 1.5

    @staticmethod
    def _max_residual_region(theta: np.ndarray, residuals: np.ndarray, center_index: int, rmse: float) -> str:
        window = max(5, min(len(residuals) // 40, 30))
        lo = max(0, center_index - window)
        hi = min(len(residuals), center_index + window + 1)
        local_res = residuals[lo:hi]
        local_theta = theta[lo:hi]
        threshold = max(rmse * 0.25, 1e-12)
        significant = np.abs(local_res) > threshold
        if np.count_nonzero(significant) >= 3:
            weights = np.abs(local_res[significant])
            center = float(np.average(local_theta[significant], weights=weights))
        else:
            center = float(theta[center_index])
        return f"2θ={center:.1f}°"

    @staticmethod
    def _has_systematic_peak(residuals: np.ndarray, center_index: int, rmse: float) -> bool:
        if len(residuals) < 10 or rmse <= 0:
            return False
        window = max(5, min(len(residuals) // 40, 30))
        lo = max(0, center_index - window)
        hi = min(len(residuals), center_index + window + 1)
        local = residuals[lo:hi]
        if len(local) < 5:
            return False
        mean_residual = float(np.mean(local))
        if abs(mean_residual) < rmse * 0.75:
            return False
        sign = 1 if mean_residual > 0 else -1
        significant = np.abs(local) > rmse * 0.25
        if np.count_nonzero(significant) < 3:
            return False
        same_sign_ratio = float(np.mean(np.sign(local[significant]) == sign))
        coverage = float(np.mean(significant))
        return same_sign_ratio >= 0.75 and coverage >= 0.20

    @staticmethod
    def _peak_regions(theta: np.ndarray, residuals: np.ndarray) -> list[dict[str, Any]]:
        if len(residuals) == 0:
            return []
        abs_res = np.abs(residuals)
        min_distance = max(5, len(residuals) // 30)
        selected: list[int] = []
        for index in np.argsort(abs_res)[::-1]:
            idx = int(index)
            if all(abs(idx - existing) >= min_distance for existing in selected):
                selected.append(idx)
            if len(selected) >= 3:
                break

        regions = []
        half_window = max(3, min(len(residuals) // 80, 20))
        for idx in selected:
            lo = max(0, idx - half_window)
            hi = min(len(residuals), idx + half_window + 1)
            local = residuals[lo:hi]
            mean_residual = float(np.mean(local)) if len(local) else 0.0
            regions.append(
                {
                    "center_two_theta": round(float(theta[idx]), 4),
                    "mean_residual": round(mean_residual, 6),
                    "max_abs_residual": round(float(abs_res[idx]), 6),
                    "sign": "positive" if mean_residual > 0 else "negative" if mean_residual < 0 else "neutral",
                    "n_points": int(len(local)),
                }
            )
        return regions

    @staticmethod
    def _summary(residual_type: str, max_region: str, residuals: np.ndarray, max_index: int, rmse: float, r_squared: float) -> str:
        max_residual = float(residuals[max_index]) if len(residuals) else 0.0
        sign_text = "正残差（拟合强度偏低）" if max_residual > 0 else "负残差（拟合强度偏高）"
        if residual_type == "background_drift":
            return (
                f"低角度区存在背景漂移，最大残差位于{max_region}附近，"
                f"RMSE={rmse:.3g}，r²={r_squared:.4f}；建议检查背景扣除方法或 arPLS 参数。"
            )
        if residual_type == "systematic_peak":
            return (
                f"在{max_region}附近存在系统性{sign_text}，RMSE={rmse:.3g}，r²={r_squared:.4f}；"
                "建议检查峰形函数、峰位约束或 peak_distance。"
            )
        return (
            f"残差主要呈随机分布，最大残差位于{max_region}附近，"
            f"RMSE={rmse:.3g}，r²={r_squared:.4f}；当前拟合未显示明显系统性偏差。"
        )


def analyze(y_obs: np.ndarray, y_fit: np.ndarray, two_theta: np.ndarray) -> ResidualPattern:
    return ResidualAnalyzer.analyze(y_obs, y_fit, two_theta)
