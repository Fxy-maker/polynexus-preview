from __future__ import annotations

from typing import Any, Dict, List

import numpy as np

from ..engine import logger
from .config import SAXSConfig


def _finite_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def classify_single_frame_lc_reliability(params: Dict[str, Any]) -> tuple[str, str]:
    """Classify lc reliability when no series-level status is available."""
    reasons: list[str] = []
    lc_conf = _finite_float(params.get("lc_confidence", params.get("lc_confidence_calibrated")))
    if lc_conf is None:
        reasons.append("missing_lc_confidence")
    elif lc_conf < 0.2:
        reasons.append("low_lc_confidence")
    elif lc_conf < 0.5:
        reasons.append("limited_lc_confidence")

    method = str(params.get("lc_method") or "").strip().lower()
    if method in {"", "tangent", "idf", "gamma_min"}:
        reasons.append("single_method_fragile")

    q_star = _finite_float(params.get("Q_star", params.get("Q_star_abs")))
    if params.get("Q_star_valid") is False:
        reasons.append("q_invariant_invalid")
    elif q_star is not None and (q_star > 50.0 or 0 < q_star < 0.5):
        reasons.append("q_invariant_anomaly")

    reason = "|".join(dict.fromkeys(reasons)) if reasons else "stable_structure_support"
    if "low_lc_confidence" in reasons or "q_invariant_invalid" in reasons:
        return "diagnostic_only", reason
    if reasons:
        return "low_confidence", reason
    return "usable", reason


def _saxs_peak_region_fit_quality(
    q: np.ndarray,
    I: np.ndarray,
    cfg: SAXSConfig,
    q_bragg_min: float,
    q_bragg_max: float,
    q_guinier: np.ndarray | None = None,
    lnI_guinier: np.ndarray | None = None,
) -> Dict:
    """Compute curve-fit R^2 only in SAXS information-bearing regions."""
    regions: List[Dict] = []

    bragg = _fit_bragg_region(q, I, q_bragg_min, q_bragg_max)
    if bragg:
        regions.append(bragg)

    guinier = _fit_guinier_region(q_guinier, lnI_guinier)
    if guinier:
        regions.append(guinier)

    ss_tot = float(sum(region["ss_tot"] for region in regions))
    if ss_tot <= 1e-12:
        return {
            "r_squared": 0.0,
            "fit_rmse": np.nan,
            "fit_regions": regions,
            "method": "saxs_peak_region_fit_r2",
        }

    ss_res = float(sum(region["ss_res"] for region in regions))
    n_points = int(sum(region["n_points"] for region in regions))
    r_squared = 1.0 - ss_res / ss_tot
    fit_rmse = float(np.sqrt(ss_res / max(n_points, 1)))
    return {
        "r_squared": float(r_squared),
        "fit_rmse": fit_rmse,
        "fit_regions": [
            {key: value for key, value in region.items() if key not in {"ss_res", "ss_tot"}}
            for region in regions
        ],
        "method": "saxs_peak_region_fit_r2",
    }


def _fit_bragg_region(q: np.ndarray, I: np.ndarray, q_min: float, q_max: float) -> Dict | None:
    mask = (
        np.isfinite(q)
        & np.isfinite(I)
        & (q >= q_min)
        & (q <= q_max)
        & (q > 0)
        & (I > 0)
    )
    if np.sum(mask) < 12:
        return None

    x = q[mask].astype(float)
    y_raw = (I[mask] * x**2).astype(float)
    y_min = float(np.min(y_raw))
    y_span = float(np.max(y_raw) - y_min)
    if y_span <= 1e-12:
        return None
    y = (y_raw - y_min) / y_span

    x_mid = float(x[np.argmax(y)])
    width = max(float(x[-1] - x[0]), 1e-3)
    sigma0 = max(width / 12.0, 0.005)

    def model(xv, bg0, bg1, amp, center, sigma):
        return bg0 + bg1 * (xv - center) + amp * np.exp(-0.5 * ((xv - center) / sigma) ** 2)

    p0 = [float(np.percentile(y, 10)), 0.0, max(float(np.max(y) - np.percentile(y, 10)), 0.05), x_mid, sigma0]
    bounds = (
        [-1.0, -20.0, 0.0, float(x[0]), max(width / len(x), 1e-4)],
        [2.0, 20.0, 5.0, float(x[-1]), width],
    )
    try:
        from scipy.optimize import curve_fit

        popt, _ = curve_fit(model, x, y, p0=p0, bounds=bounds, maxfev=10000, method="trf")
        y_pred = model(x, *popt)
        center = float(popt[3])
        sigma = float(abs(popt[4]))
    except Exception:
        coeff = np.polyfit(x, y, 2)
        y_pred = np.polyval(coeff, x)
        center = x_mid
        sigma = np.nan
        logger.warning("SAXS Bragg-region fit failed; using polynomial fallback.", exc_info=True)

    stats = _standardized_region_stats(y, y_pred)
    if stats is None:
        return None
    stats.update(
        {
            "kind": "bragg_peak",
            "q_start": float(x[0]),
            "q_end": float(x[-1]),
            "q_peak_fit": center,
            "sigma_q": sigma,
        }
    )
    return stats


def _fit_guinier_region(q_guinier: np.ndarray | None, lnI_guinier: np.ndarray | None) -> Dict | None:
    if q_guinier is None or lnI_guinier is None:
        return None
    qg = np.asarray(q_guinier, dtype=float)
    yg = np.asarray(lnI_guinier, dtype=float)
    mask = np.isfinite(qg) & np.isfinite(yg)
    if np.sum(mask) < 5:
        return None

    x = qg[mask]
    y = yg[mask]
    try:
        coeff = np.polyfit(x**2, y, 1)
        y_pred = np.polyval(coeff, x**2)
    except Exception:
        logger.warning("SAXS Guinier-region fit failed.", exc_info=True)
        return None
    stats = _standardized_region_stats(y, y_pred)
    if stats is None:
        return None
    stats.update(
        {
            "kind": "guinier",
            "q_start": float(x[0]),
            "q_end": float(x[-1]),
        }
    )
    return stats


def _standardized_region_stats(y: np.ndarray, y_pred: np.ndarray) -> Dict | None:
    obs = np.asarray(y, dtype=float)
    pred = np.asarray(y_pred, dtype=float)
    mask = np.isfinite(obs) & np.isfinite(pred)
    if np.sum(mask) < 3:
        return None
    obs = obs[mask]
    pred = pred[mask]
    scale = float(np.std(obs))
    if scale <= 1e-12:
        return None
    obs_z = (obs - float(np.mean(obs))) / scale
    pred_z = (pred - float(np.mean(obs))) / scale
    residual = obs_z - pred_z
    ss_res = float(np.sum(residual**2))
    ss_tot = float(np.sum((obs_z - float(np.mean(obs_z))) ** 2))
    return {
        "ss_res": ss_res,
        "ss_tot": ss_tot,
        "n_points": int(len(obs_z)),
        "rmse": float(np.sqrt(np.mean(residual**2))),
    }
