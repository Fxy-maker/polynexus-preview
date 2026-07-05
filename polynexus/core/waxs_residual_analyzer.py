from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
import math

import numpy as np


@dataclass
class WAXSResidualPattern:
    rmse: float
    r_squared: float
    residual_type: str
    max_residual_region: str
    peak_regions: list[dict]
    summary: str

    def to_dict(self) -> dict:
        return asdict(self)


class WAXSResidualAnalyzer:
    VALID_TWO_THETA_MIN = 5.0
    VALID_TWO_THETA_MAX = 40.0
    DEFAULT_PEAK_HALF_WIDTH = 0.75
    MIN_VALID_POINTS = 12

    @classmethod
    def analyze(
        cls,
        y_obs: np.ndarray,
        y_fit: np.ndarray,
        two_theta: np.ndarray,
        context: dict[str, Any] | None = None,
    ) -> WAXSResidualPattern:
        obs, fit, theta = cls._prepare_arrays(y_obs, y_fit, two_theta)
        if len(obs) == 0:
            return WAXSResidualPattern(
                rmse=0.0,
                r_squared=0.0,
                residual_type="random",
                max_residual_region="unknown",
                peak_regions=[],
                summary="WAXS residual data is insufficient for pattern classification.",
            )

        residuals = obs - fit
        rmse = float(np.sqrt(np.mean(residuals**2)))
        r_squared = cls._r_squared(obs, fit)
        max_index = int(np.argmax(np.abs(residuals)))
        max_region = cls._max_residual_region(theta, residuals, max_index, rmse)
        peak_regions = cls._peak_regions(theta, residuals, rmse)
        meta = cls._context_metadata(context)
        residual_type = cls._classify(theta, residuals, rmse, peak_regions, meta)
        summary = cls._summary(residual_type, max_region, theta, residuals, max_index, rmse, r_squared, meta)
        return WAXSResidualPattern(
            rmse=round(rmse, 6),
            r_squared=round(r_squared, 6),
            residual_type=residual_type,
            max_residual_region=max_region,
            peak_regions=peak_regions,
            summary=summary,
        )

    @classmethod
    def _prepare_arrays(
        cls,
        y_obs: np.ndarray,
        y_fit: np.ndarray,
        two_theta: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        obs = np.asarray(y_obs, dtype=float).ravel()
        fit = np.asarray(y_fit, dtype=float).ravel()
        theta = np.asarray(two_theta, dtype=float).ravel()
        n = min(len(obs), len(fit), len(theta))
        if n <= 0:
            return np.array([]), np.array([]), np.array([])
        obs, fit, theta = obs[:n], fit[:n], theta[:n]
        mask = (
            np.isfinite(obs)
            & np.isfinite(fit)
            & np.isfinite(theta)
            & (theta >= cls.VALID_TWO_THETA_MIN)
            & (theta <= cls.VALID_TWO_THETA_MAX)
        )
        obs, fit, theta = obs[mask], fit[mask], theta[mask]
        if len(obs) < cls.MIN_VALID_POINTS:
            return np.array([]), np.array([]), np.array([])
        return obs, fit, theta

    @staticmethod
    def _r_squared(obs: np.ndarray, fit: np.ndarray) -> float:
        ss_res = float(np.sum((obs - fit) ** 2))
        ss_tot = float(np.sum((obs - np.mean(obs)) ** 2))
        if ss_tot <= 0:
            return 1.0 if ss_res <= 1e-12 else 0.0
        value = 1.0 - ss_res / ss_tot
        return value if math.isfinite(value) else 0.0

    @classmethod
    def _context_metadata(cls, context: dict[str, Any] | None) -> dict[str, Any]:
        context = dict(context or {})
        output = context.get("output_parameters")
        if not isinstance(output, dict):
            output = context.get("output")
        if not isinstance(output, dict):
            output = {}
        config = context.get("config_snapshot")
        if not isinstance(config, dict):
            config = {}

        peaks = cls._extract_peaks(output)
        peak_centers = [peak["center"] for peak in peaks if peak.get("center") is not None]
        peak_widths = [peak["width"] for peak in peaks if peak.get("width") is not None]
        peak_areas = [peak["area"] for peak in peaks if peak.get("area") is not None]
        peak_gap_spread = cls._relative_spread(cls._sorted_differences(peak_centers))
        peak_width_spread = cls._relative_spread(peak_widths)
        area_values = [value for value in peak_areas if value is not None and value > 0]
        peak_area_ratio = None
        if len(area_values) >= 2:
            peak_area_ratio = max(area_values) / max(min(area_values), 1e-9)

        return {
            "output": output,
            "config": config,
            "peaks": peaks,
            "peak_count": len(peaks),
            "peak_centers": peak_centers,
            "peak_widths": peak_widths,
            "peak_areas": peak_areas,
            "peak_gap_spread": peak_gap_spread,
            "peak_width_spread": peak_width_spread,
            "peak_area_ratio": peak_area_ratio,
            "two_theta_offset": cls._safe_float(
                output.get("two_theta_offset", config.get("two_theta_offset"))
            ),
            "background_method": str(
                output.get("background_method", config.get("background_method", "")) or ""
            ).strip().lower(),
            "amorphous_subtraction": str(
                output.get("amorphous_subtraction", config.get("amorphous_subtraction", "")) or ""
            ).strip().lower(),
            "amorphous_n_peaks": cls._safe_int(
                output.get("amorphous_n_peaks", config.get("amorphous_n_peaks"))
            ),
            "crystallinity_method": str(
                output.get(
                    "crystallinity_method",
                    output.get("Xc_method", config.get("crystallinity_method", "")),
                )
                or ""
            ).strip().lower(),
            "max_peaks": cls._safe_int(config.get("max_peaks")),
            "peak_distance": cls._safe_float(config.get("peak_distance")),
        }

    @staticmethod
    def _extract_peaks(output: dict[str, Any]) -> list[dict[str, Any]]:
        peaks: list[dict[str, Any]] = []
        raw_peaks = output.get("peaks")
        if isinstance(raw_peaks, list):
            for item in raw_peaks:
                if not isinstance(item, dict):
                    continue
                center = WAXSResidualAnalyzer._safe_float(item.get("center", item.get("two_theta")))
                if center is None:
                    continue
                peaks.append(
                    {
                        "center": center,
                        "width": WAXSResidualAnalyzer._safe_float(item.get("width", item.get("fwhm", item.get("fwhm_deg")))),
                        "area": WAXSResidualAnalyzer._safe_float(item.get("area")),
                    }
                )
        if peaks:
            return peaks

        centers = output.get("peak_centers")
        widths = output.get("peak_widths")
        areas = output.get("peak_areas")
        if isinstance(centers, list):
            for index, center in enumerate(centers):
                center_value = WAXSResidualAnalyzer._safe_float(center)
                if center_value is None:
                    continue
                peaks.append(
                    {
                        "center": center_value,
                        "width": WAXSResidualAnalyzer._safe_float(widths[index]) if isinstance(widths, list) and index < len(widths) else None,
                        "area": WAXSResidualAnalyzer._safe_float(areas[index]) if isinstance(areas, list) and index < len(areas) else None,
                    }
                )
        return peaks

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) else None

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        number = WAXSResidualAnalyzer._safe_float(value)
        if number is None:
            return None
        return int(round(number))

    @staticmethod
    def _relative_spread(values: list[float | None]) -> float | None:
        clean = [float(value) for value in values if value is not None and math.isfinite(float(value))]
        if len(clean) < 2:
            return None
        mean = float(np.mean(clean))
        if abs(mean) <= 1e-12:
            return float(np.std(clean))
        return float(np.std(clean) / abs(mean))

    @staticmethod
    def _sorted_differences(values: list[float]) -> list[float]:
        if len(values) < 2:
            return []
        ordered = sorted(float(value) for value in values)
        return [b - a for a, b in zip(ordered, ordered[1:]) if b > a]

    @classmethod
    def _max_residual_region(cls, theta: np.ndarray, residuals: np.ndarray, center_index: int, rmse: float) -> str:
        window = max(5, min(len(residuals) // 36, 28))
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
        return f"2theta={center:.2f} deg"

    @classmethod
    def _peak_regions(cls, theta: np.ndarray, residuals: np.ndarray, rmse: float) -> list[dict]:
        if rmse <= 0:
            return []
        threshold = max(rmse * 1.45, float(np.nanstd(residuals)) * 0.75 if len(residuals) > 5 else rmse)
        mask = np.abs(residuals) >= threshold
        regions: list[tuple[int, int]] = []
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
                    "center_two_theta": round(float(np.average(theta[left : right + 1], weights=np.abs(local) + 1e-12)), 4),
                    "two_theta_start": round(float(theta[left]), 4),
                    "two_theta_end": round(float(theta[right]), 4),
                    "sample_count": int(right - left + 1),
                    "mean_residual": round(float(np.mean(local)), 6),
                    "max_abs_residual": round(float(np.max(np.abs(local))), 6),
                    "sign": "positive" if float(np.mean(local)) >= 0 else "negative",
                }
            )
        return out

    @classmethod
    def _classify(
        cls,
        theta: np.ndarray,
        residuals: np.ndarray,
        rmse: float,
        peak_regions: list[dict],
        meta: dict[str, Any],
    ) -> str:
        if rmse <= 0:
            return "random"

        scores = [
            ("low_angle_background_drift", *cls._score_low_angle_background_drift(theta, residuals, rmse, meta)),
            ("amorphous_background_bias", *cls._score_amorphous_background_bias(theta, residuals, rmse, peak_regions, meta)),
            ("peak_count_underfit", *cls._score_peak_count_underfit(theta, residuals, rmse, peak_regions, meta)),
            ("peak_count_overfit", *cls._score_peak_count_overfit(theta, residuals, rmse, peak_regions, meta)),
            ("peak_position_bias", *cls._score_peak_position_bias(theta, residuals, rmse, meta)),
            ("peak_width_mismatch", *cls._score_peak_width_mismatch(theta, residuals, rmse, meta)),
        ]
        best_name = "random"
        best_score = 0.0
        best_detail: dict[str, Any] = {}
        for name, score, detail in scores:
            if score > best_score:
                best_name = name
                best_score = score
                best_detail = detail

        if best_score >= 0.45:
            return best_name

        fallback = cls._fallback_classify(theta, residuals, rmse, peak_regions)
        if fallback != "random":
            return fallback
        if best_name != "random" and best_detail.get("support", 0) >= 1 and best_score >= 0.35:
            return best_name
        return "random"

    @classmethod
    def _score_low_angle_background_drift(
        cls,
        theta: np.ndarray,
        residuals: np.ndarray,
        rmse: float,
        meta: dict[str, Any],
    ) -> tuple[float, dict[str, Any]]:
        mask = theta < 10.0
        if np.count_nonzero(mask) < 6 or rmse <= 0:
            return 0.0, {}
        local = residuals[mask]
        mean_residual = float(np.mean(local))
        if abs(mean_residual) <= rmse * 1.15:
            return 0.0, {}
        significant = np.abs(local) > rmse * 0.45
        same_sign_ratio = float(np.mean(np.sign(local[significant]) == np.sign(mean_residual))) if np.count_nonzero(significant) else 0.0
        coverage = float(np.mean(significant)) if len(local) else 0.0
        score = min(1.0, abs(mean_residual) / (rmse * 2.0))
        score = 0.72 * score + 0.18 * same_sign_ratio + 0.10 * coverage
        if meta.get("background_method"):
            score += 0.03
        return min(1.0, score), {
            "support": int(np.count_nonzero(mask)),
            "mean_residual": mean_residual,
            "coverage": coverage,
        }

    @classmethod
    def _score_amorphous_background_bias(
        cls,
        theta: np.ndarray,
        residuals: np.ndarray,
        rmse: float,
        peak_regions: list[dict],
        meta: dict[str, Any],
    ) -> tuple[float, dict[str, Any]]:
        mask = (theta >= 10.0) & (theta <= 25.0)
        if np.count_nonzero(mask) < 8 or rmse <= 0:
            return 0.0, {}

        exclusion = np.zeros_like(mask, dtype=bool)
        for peak in meta.get("peaks", []):
            center = peak.get("center")
            if center is None:
                continue
            width = peak.get("width")
            half = max(0.6, float(width) * 1.4 if width is not None else cls.DEFAULT_PEAK_HALF_WIDTH)
            exclusion |= np.abs(theta - float(center)) <= half
        local_mask = mask & ~exclusion
        if np.count_nonzero(local_mask) < 8:
            local_mask = mask
        local = residuals[local_mask]
        mean_residual = float(np.mean(local))
        if abs(mean_residual) <= rmse * 1.08:
            return 0.0, {}
        significant = np.abs(local) > rmse * 0.5
        same_sign_ratio = float(np.mean(np.sign(local[significant]) == np.sign(mean_residual))) if np.count_nonzero(significant) else 0.0
        coverage = float(np.mean(significant)) if len(local) else 0.0
        score = min(1.0, abs(mean_residual) / (rmse * 1.8))
        score = 0.68 * score + 0.22 * same_sign_ratio + 0.10 * coverage
        if meta.get("amorphous_subtraction") in {"polynomial", "spline", "manual"}:
            score += 0.04
        if meta.get("peak_count", 0) >= 2 and len(peak_regions) <= 2:
            score += 0.02
        return min(1.0, score), {
            "support": int(np.count_nonzero(local_mask)),
            "mean_residual": mean_residual,
            "coverage": coverage,
        }

    @classmethod
    def _score_peak_position_bias(
        cls,
        theta: np.ndarray,
        residuals: np.ndarray,
        rmse: float,
        meta: dict[str, Any],
    ) -> tuple[float, dict[str, Any]]:
        peaks = meta.get("peaks", [])
        best_score = 0.0
        best_detail: dict[str, Any] = {}
        two_theta_offset = meta.get("two_theta_offset")
        for peak in peaks:
            center = peak.get("center")
            if center is None:
                continue
            width = peak.get("width")
            base_half = float(width) * 0.8 if width is not None and width > 0 else cls.DEFAULT_PEAK_HALF_WIDTH
            half = max(0.35, min(1.25, base_half))
            left_mask = (theta >= center - 1.8 * half) & (theta < center - 0.35 * half)
            right_mask = (theta > center + 0.35 * half) & (theta <= center + 1.8 * half)
            center_mask = np.abs(theta - center) <= 0.35 * half
            if np.count_nonzero(left_mask) < 4 or np.count_nonzero(right_mask) < 4 or np.count_nonzero(center_mask) < 3:
                continue
            left_mean = float(np.mean(residuals[left_mask]))
            right_mean = float(np.mean(residuals[right_mask]))
            center_mean = float(np.mean(residuals[center_mask]))
            opposite_sides = np.sign(left_mean) != 0 and np.sign(right_mean) != 0 and np.sign(left_mean) != np.sign(right_mean)
            if not opposite_sides:
                continue
            amplitude = abs(left_mean) + abs(right_mean)
            if amplitude <= rmse * 1.0:
                continue
            center_small = abs(center_mean) <= max(abs(left_mean), abs(right_mean)) * 0.95
            score = min(1.0, amplitude / (rmse * 3.0))
            if center_small:
                score += 0.08
            if two_theta_offset is not None and abs(float(two_theta_offset)) > 0.03:
                score += 0.10
            if width is not None and width > 0:
                score += min(0.05, abs(float(width) - cls.DEFAULT_PEAK_HALF_WIDTH) * 0.04)
            if score > best_score:
                best_score = score
                best_detail = {
                    "support": 1,
                    "center": float(center),
                    "left_mean": left_mean,
                    "center_mean": center_mean,
                    "right_mean": right_mean,
                    "width": float(width) if width is not None else None,
                }
        return best_score, best_detail

    @classmethod
    def _score_peak_width_mismatch(
        cls,
        theta: np.ndarray,
        residuals: np.ndarray,
        rmse: float,
        meta: dict[str, Any],
    ) -> tuple[float, dict[str, Any]]:
        peaks = meta.get("peaks", [])
        best_score = 0.0
        best_detail: dict[str, Any] = {}
        width_spread = meta.get("peak_width_spread")
        peak_widths = meta.get("peak_widths", [])
        for peak in peaks:
            center = peak.get("center")
            if center is None:
                continue
            width = peak.get("width")
            base_half = float(width) * 0.8 if width is not None and width > 0 else cls.DEFAULT_PEAK_HALF_WIDTH
            half = max(0.35, min(1.25, base_half))
            shoulder_left = (theta >= center - 1.8 * half) & (theta < center - 0.55 * half)
            shoulder_right = (theta > center + 0.55 * half) & (theta <= center + 1.8 * half)
            core = np.abs(theta - center) <= 0.35 * half
            if np.count_nonzero(shoulder_left) < 4 or np.count_nonzero(shoulder_right) < 4 or np.count_nonzero(core) < 3:
                continue
            left_mean = float(np.mean(residuals[shoulder_left]))
            right_mean = float(np.mean(residuals[shoulder_right]))
            core_mean = float(np.mean(residuals[core]))
            if np.sign(left_mean) == 0 or np.sign(right_mean) == 0:
                continue
            shoulders_same = np.sign(left_mean) == np.sign(right_mean)
            core_opposite = np.sign(core_mean) != 0 and np.sign(core_mean) != np.sign(left_mean)
            if not (shoulders_same and core_opposite):
                continue
            amplitude = abs(left_mean) + abs(right_mean) + abs(core_mean)
            if amplitude <= rmse * 1.2:
                continue
            score = min(1.0, amplitude / (rmse * 3.2))
            if isinstance(width_spread, (int, float)) and math.isfinite(float(width_spread)) and float(width_spread) > 0.35:
                score += 0.08
            if width is not None and (float(width) < 0.15 or float(width) > 2.5):
                score += 0.10
            if peak_widths and len(peak_widths) >= 2 and cls._relative_spread(peak_widths) and cls._relative_spread(peak_widths) > 0.45:
                score += 0.05
            if score > best_score:
                best_score = score
                best_detail = {
                    "support": 1,
                    "center": float(center),
                    "left_mean": left_mean,
                    "core_mean": core_mean,
                    "right_mean": right_mean,
                    "width": float(width) if width is not None else None,
                }
        return best_score, best_detail

    @classmethod
    def _score_peak_count_underfit(
        cls,
        theta: np.ndarray,
        residuals: np.ndarray,
        rmse: float,
        peak_regions: list[dict],
        meta: dict[str, Any],
    ) -> tuple[float, dict[str, Any]]:
        peak_count = int(meta.get("peak_count", 0) or 0)
        if rmse <= 0:
            return 0.0, {}
        if not peak_regions:
            return 0.0, {}

        peaks = meta.get("peaks", [])
        uncovered_regions = 0
        region_centers = []
        for region in peak_regions:
            center = float(region.get("center_two_theta", region.get("two_theta_start", 0.0)))
            region_centers.append(center)
            if not peaks:
                uncovered_regions += 1
                continue
            nearest = min(abs(center - float(peak.get("center"))) for peak in peaks if peak.get("center") is not None)
            peak_half = max(0.9, cls._median_peak_half_width(peaks))
            if nearest > peak_half * 1.4:
                uncovered_regions += 1

        if uncovered_regions == 0:
            return 0.0, {}

        strong_region_count = len(peak_regions)
        support_gap = max(0, strong_region_count - peak_count)
        score = 0.42 + 0.18 * uncovered_regions + 0.12 * support_gap
        if peak_count <= 1 and strong_region_count >= 2:
            score += 0.18
        if peak_count == 0 and strong_region_count >= 1:
            score += 0.12
        if float(np.mean(np.abs(residuals))) > rmse * 1.2:
            score += 0.05
        return min(1.0, score), {
            "support": uncovered_regions,
            "region_centers": region_centers,
            "peak_count": peak_count,
            "strong_region_count": strong_region_count,
        }

    @staticmethod
    def _median_peak_half_width(peaks: list[dict[str, Any]]) -> float:
        widths: list[float] = []
        for peak in peaks:
            width = peak.get("width")
            try:
                value = float(width)
            except (TypeError, ValueError):
                continue
            if math.isfinite(value) and value > 0:
                widths.append(value)
        if not widths:
            return WAXSResidualAnalyzer.DEFAULT_PEAK_HALF_WIDTH
        return float(np.median(widths)) * 0.5

    @classmethod
    def _score_peak_count_overfit(
        cls,
        theta: np.ndarray,
        residuals: np.ndarray,
        rmse: float,
        peak_regions: list[dict],
        meta: dict[str, Any],
    ) -> tuple[float, dict[str, Any]]:
        peak_count = int(meta.get("peak_count", 0) or 0)
        if peak_count < 4:
            return 0.0, {}
        strong_region_count = len(peak_regions)
        widths = [float(value) for value in meta.get("peak_widths", []) if value is not None]
        width_spread = cls._relative_spread(widths) if widths else None
        score = 0.35
        if strong_region_count <= 1:
            score += 0.28
        if strong_region_count == 0:
            score += 0.12
        if widths:
            median_width = float(np.median(widths))
            if median_width < 0.35:
                score += 0.10
            if median_width > 1.6:
                score += 0.05
        if isinstance(width_spread, float) and math.isfinite(width_spread) and width_spread > 0.35:
            score += 0.08
        if meta.get("peak_area_ratio") is not None and float(meta["peak_area_ratio"]) > 8.0:
            score += 0.05
        if rmse <= 0:
            score += 0.10
        elif np.nanmax(np.abs(residuals)) <= rmse * 1.2:
            score += 0.10
        return min(1.0, score), {
            "support": max(0, peak_count - strong_region_count),
            "peak_count": peak_count,
            "strong_region_count": strong_region_count,
        }

    @classmethod
    def _fallback_classify(
        cls,
        theta: np.ndarray,
        residuals: np.ndarray,
        rmse: float,
        peak_regions: list[dict],
    ) -> str:
        low_mask = theta < 10.0
        if np.count_nonzero(low_mask) > 5 and abs(float(np.mean(residuals[low_mask]))) > rmse * 1.25:
            return "background_drift"
        if not peak_regions:
            return "random"
        for region in peak_regions:
            width = abs(float(region["two_theta_end"]) - float(region["two_theta_start"]))
            if (
                0.10 <= width <= 2.5
                and int(region.get("sample_count", 0)) >= 4
                and float(region["max_abs_residual"]) > rmse * 1.8
            ):
                return "systematic_peak"
        return "random"

    @classmethod
    def _summary(
        cls,
        residual_type: str,
        max_region: str,
        theta: np.ndarray,
        residuals: np.ndarray,
        max_index: int,
        rmse: float,
        r_squared: float,
        meta: dict[str, Any],
    ) -> str:
        max_residual = float(residuals[max_index]) if len(residuals) else 0.0
        sign_text = "positive residual" if max_residual > 0 else "negative residual"
        if residual_type == "low_angle_background_drift":
            return (
                f"Low-angle background drift remains near {max_region}; "
                f"RMSE={rmse:.4g}, R2={r_squared:.4f}. "
                "Check background_method, amorphous_subtraction, or two_theta_offset first."
            )
        if residual_type == "amorphous_background_bias":
            return (
                f"Broad amorphous/background bias remains near {max_region}; "
                f"RMSE={rmse:.4g}, R2={r_squared:.4f}. "
                "Check background_method, amorphous_subtraction, and amorphous_n_peaks."
            )
        if residual_type == "peak_count_underfit":
            return (
                f"Peak count looks underfit near {max_region}; "
                f"RMSE={rmse:.4g}, R2={r_squared:.4f}. "
                "The current peak family likely misses supported structure."
            )
        if residual_type == "peak_count_overfit":
            return (
                f"Peak count looks overfit near {max_region}; "
                f"RMSE={rmse:.4g}, R2={r_squared:.4f}. "
                "Too many fitted peaks may be chasing noise or halo detail."
            )
        if residual_type == "peak_position_bias":
            return (
                f"Peak-position bias is visible near {max_region}; "
                f"RMSE={rmse:.4g}, R2={r_squared:.4f}. "
                "The residual changes sign across the peak, suggesting a small theta shift."
            )
        if residual_type == "peak_width_mismatch":
            return (
                f"Peak-width mismatch is visible near {max_region}; "
                f"RMSE={rmse:.4g}, R2={r_squared:.4f}. "
                "Shoulders and peak core disagree, so peak_function or smoothing likely needs attention."
            )
        if residual_type == "background_drift":
            return (
                f"Low-angle background drift remains near {max_region}; "
                f"RMSE={rmse:.4g}, R2={r_squared:.4f}. "
                "Check background subtraction before trusting the fit."
            )
        if residual_type == "systematic_peak":
            return (
                f"Systematic peak residual remains near {max_region}; "
                f"RMSE={rmse:.4g}, R2={r_squared:.4f}. "
                "Check peak shape, peak position constraints, or peak_distance."
            )
        return (
            f"WAXS residuals are mostly random, with the largest deviation near {max_region}; "
            f"RMSE={rmse:.4g}, R2={r_squared:.4f}. "
            f"Max residual is a {sign_text}."
        )


def analyze(
    y_obs: np.ndarray,
    y_fit: np.ndarray,
    two_theta: np.ndarray,
    context: dict[str, Any] | None = None,
) -> WAXSResidualPattern:
    return WAXSResidualAnalyzer.analyze(y_obs, y_fit, two_theta, context=context)
