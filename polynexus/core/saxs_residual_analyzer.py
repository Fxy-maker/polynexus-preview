from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


@dataclass
class SAXSResidualPattern:
    rmse: float
    r_squared: float
    residual_type: str
    max_residual_region: str
    peak_regions: list[dict]
    summary: str

    def to_dict(self) -> dict:
        return asdict(self)


class SAXSResidualAnalyzer:
    VALID_Q_MIN = 0.03
    VALID_Q_MAX = 3.0

    @classmethod
    def analyze(
        cls,
        q: np.ndarray,
        intensity: np.ndarray,
        fit: np.ndarray | None = None,
    ) -> SAXSResidualPattern:
        q_arr = np.asarray(q, dtype=float)
        obs = np.asarray(intensity, dtype=float)
        if fit is None:
            pred = cls._smooth_baseline(q_arr, obs)
        else:
            pred = np.asarray(fit, dtype=float)
            if len(pred) == len(obs):
                fallback = cls._smooth_baseline(q_arr, obs)
                pred = np.where(np.isfinite(pred), pred, fallback)
            else:
                pred = cls._smooth_baseline(q_arr, obs)

        valid = (
            np.isfinite(q_arr)
            & np.isfinite(obs)
            & np.isfinite(pred)
            & (q_arr >= cls.VALID_Q_MIN)
            & (q_arr <= cls.VALID_Q_MAX)
            & (obs > 0)
        )
        if np.count_nonzero(valid) < 8:
            return SAXSResidualPattern(
                rmse=0.0,
                r_squared=0.0,
                residual_type="random",
                max_residual_region="unknown",
                peak_regions=[],
                summary="SAXS 残差数据不足，无法判断残差模式。",
            )

        q_valid = q_arr[valid]
        obs_valid = obs[valid]
        pred_valid = pred[valid]
        residuals = obs_valid - pred_valid
        rmse = float(np.sqrt(np.mean(residuals**2)))
        ss_res = float(np.sum(residuals**2))
        ss_tot = float(np.sum((obs_valid - np.mean(obs_valid)) ** 2))
        r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0

        max_idx = int(np.argmax(np.abs(residuals)))
        max_q = float(q_valid[max_idx])
        peak_regions = cls._peak_regions(q_valid, residuals, rmse)
        residual_type = cls._classify(q_valid, residuals, rmse, peak_regions)
        direction = "正残差（拟合偏低）" if residuals[max_idx] > 0 else "负残差（拟合偏高）"
        summary = (
            f"在 q={max_q:.3f} nm^-1 附近存在最大{direction}，"
            f"RMSE={rmse:.4g}，残差类型={residual_type}。"
        )
        if residual_type == "peak_mismatch":
            summary += " 建议优先检查 q_bragg/q_corr 搜索区间或 IDF 阈值。"
        elif residual_type == "background_drift":
            summary += " 建议优先检查低 q 背景、beamstop 污染或 q_corr_min。"

        return SAXSResidualPattern(
            rmse=rmse,
            r_squared=float(r_squared),
            residual_type=residual_type,
            max_residual_region=f"q={max_q:.3f} nm^-1",
            peak_regions=peak_regions,
            summary=summary,
        )

    @staticmethod
    def _smooth_baseline(q: np.ndarray, y: np.ndarray) -> np.ndarray:
        valid = np.isfinite(q) & np.isfinite(y)
        if np.count_nonzero(valid) < 5:
            return np.zeros_like(y, dtype=float)
        x = q[valid]
        obs = y[valid]
        order = 2 if len(obs) > 20 else 1
        coeff = np.polyfit(x, np.log(np.maximum(obs, 1e-12)), order)
        pred = np.exp(np.polyval(coeff, q))
        return np.where(np.isfinite(pred), pred, np.nanmedian(obs))

    @staticmethod
    def _peak_regions(q: np.ndarray, residuals: np.ndarray, rmse: float) -> list[dict]:
        if rmse <= 0:
            return []
        mask = np.abs(residuals) >= rmse * 1.5
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
        for left, right in regions[:5]:
            local = residuals[left : right + 1]
            out.append(
                {
                    "q_start": float(q[left]),
                    "q_end": float(q[right]),
                    "sample_count": int(right - left + 1),
                    "mean_residual": float(np.mean(local)),
                    "max_abs_residual": float(np.max(np.abs(local))),
                    "sign": "positive" if float(np.mean(local)) >= 0 else "negative",
                }
            )
        return out

    @staticmethod
    def _classify(q: np.ndarray, residuals: np.ndarray, rmse: float, peak_regions: list[dict]) -> str:
        if rmse <= 0:
            return "random"
        low_q = q < 0.12
        if np.count_nonzero(low_q) > 5 and abs(float(np.mean(residuals[low_q]))) > rmse * 1.2:
            return "background_drift"
        for region in peak_regions:
            width = abs(float(region["q_end"]) - float(region["q_start"]))
            if (
                0.01 <= width <= 0.5
                and int(region.get("sample_count", 0)) >= 5
                and float(region["max_abs_residual"]) > rmse * 2.0
            ):
                return "peak_mismatch"
        return "random"
