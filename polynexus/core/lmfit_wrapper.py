"""
lmfit-based peak fitting wrapper for all PolyNexus engines.

v4.0 mandate: all peak fitting uses lmfit, not hand-rolled scipy.
This module provides drop-in replacements for common fitting tasks
across DSC, SAXS, WAXS, IR, and NMR engines.
"""

from __future__ import annotations
import logging
logger = logging.getLogger(__name__)


import numpy as np
import lmfit
from lmfit.models import (
    GaussianModel, LorentzianModel, PseudoVoigtModel,
    LinearModel, QuadraticModel, ConstantModel,
)
from typing import Dict, List, Optional, Tuple, Any

from .engine import logger


# ==========================================================================
#  Multi-peak fitting (DSC / WAXS / IR / NMR)
# ==========================================================================

def fit_multi_peak(
    x: np.ndarray,
    y: np.ndarray,
    n_peaks: int = 1,
    peak_type: str = "gaussian",
    centers: Optional[List[float]] = None,
    baseline: str = "none",
    x_range: Optional[Tuple[float, float]] = None,
    constraints: Optional[Dict[str, Any]] = None,
    sigma_min: float = 0.1,
) -> Dict[str, Any]:
    """Fit multi-peak model to data using lmfit.

    Returns dict with keys:
        components: list[dict] - per-peak {center, amplitude, sigma, fwhm, area}
        r_squared, redchi, fit_y, baseline_y, residuals
    """
    result: Dict[str, Any] = {
        "components": [], "r_squared": np.nan, "redchi": np.nan,
        "fit_y": np.array([]), "baseline_y": np.array([]),
        "residuals": np.array([]),
    }

    if x_range is not None:
        mask = (x >= x_range[0]) & (x <= x_range[1])
        if np.sum(mask) < 10:
            return result
        x_fit, y_fit = x[mask], y[mask]
    else:
        x_fit, y_fit = x, y.copy()

    if len(x_fit) < 10 or n_peaks < 1:
        return result

    # Auto-detect centers
    if centers is None:
        from scipy.signal import find_peaks
        y_range = float(np.max(y_fit) - np.min(y_fit))
        prom = y_range * 0.05 if y_range > 0 else 1e-9
        pk_idx, _ = find_peaks(
            y_fit, prominence=max(prom, 1e-9),
            distance=max(5, len(x_fit) // (n_peaks + 2)),
        )
        if len(pk_idx) == 0:
            centers = [float(np.median(x_fit))] * n_peaks
        else:
            sorted_idx = pk_idx[np.argsort(y_fit[pk_idx])[::-1]]
            centers = [float(x_fit[i]) for i in sorted_idx[:n_peaks]]
            while len(centers) < n_peaks:
                centers.append(float(np.linspace(
                    x_fit[0], x_fit[-1], n_peaks + 2)[len(centers) + 1]))

    # Model selection
    peak_cls = {
        "gaussian": GaussianModel,
        "lorentzian": LorentzianModel,
        "pseudo_voigt": PseudoVoigtModel,
    }.get(peak_type, GaussianModel)

    base_cls = {
        "linear": LinearModel, "quadratic": QuadraticModel,
        "constant": ConstantModel,
    }.get(baseline)

    # Build composite
    if base_cls is not None:
        composite = base_cls(prefix="base_")
    else:
        composite = None

    for i, center in enumerate(centers[:n_peaks]):
        p = peak_cls(prefix=f"p{i}_")
        composite = p if composite is None else composite + p

    if composite is None:
        return result

    params = composite.make_params()

    amp_guess = float(np.max(y_fit) - np.min(y_fit)) / max(n_peaks, 1)
    sigma_guess = float(x_fit[-1] - x_fit[0]) / (n_peaks * 4)

    for i, center in enumerate(centers[:n_peaks]):
        params[f"p{i}_center"].set(value=center)
        params[f"p{i}_amplitude"].set(value=amp_guess, min=0)
        if peak_type in ("gaussian", "lorentzian"):
            params[f"p{i}_sigma"].set(value=sigma_guess, min=sigma_min)

        if constraints:
            if "sigma_max" in constraints:
                params[f"p{i}_sigma"].set(max=constraints["sigma_max"])
            if "center_bounds" in constraints:
                lo, hi = constraints["center_bounds"]
                params[f"p{i}_center"].set(min=lo, max=hi)

    try:
        fit_result = composite.fit(y_fit, params, x=x_fit,
                                   method="leastsq", max_nfev=5000)
    except Exception as e:
        logger.warning("lmfit 峰拟合失败，返回初始猜测值: %s", e, exc_info=True)
        return result
        logger.warning("异常已处理", exc_info=True)

    result["r_squared"] = (1.0 - fit_result.residual.var() / y_fit.var()
                           if y_fit.var() > 0 else np.nan)
    result["redchi"] = fit_result.redchi
    result["fit_y"] = fit_result.best_fit
    result["residuals"] = fit_result.residual

    # Baseline extraction
    if baseline in ("linear", "quadratic", "constant"):
        b = "base_"
        if baseline == "linear":
            result["baseline_y"] = (
                fit_result.params[f"{b}slope"].value * x_fit +
                fit_result.params[f"{b}intercept"].value
            )
        elif baseline == "quadratic":
            result["baseline_y"] = (
                fit_result.params[f"{b}a"].value * x_fit**2 +
                fit_result.params[f"{b}b"].value * x_fit +
                fit_result.params[f"{b}c"].value
            )
        else:
            result["baseline_y"] = np.full_like(
                x_fit, fit_result.params[f"{b}c"].value)
    else:
        result["baseline_y"] = np.zeros_like(x_fit)

    # Per-peak results
    for i in range(n_peaks):
        p = f"p{i}_"
        c = float(fit_result.params[f"{p}center"].value)
        a = float(fit_result.params[f"{p}amplitude"].value)
        s = float(fit_result.params[f"{p}sigma"].value)
        f = float(fit_result.params[f"{p}fwhm"].value)
        area = (a * s * np.sqrt(2 * np.pi) if peak_type in ("gaussian", "pseudo_voigt")
                else a * np.pi * s)
        result["components"].append({
            "index": i, "center": c, "amplitude": a,
            "sigma": s, "fwhm": f, "area": area,
        })

    return result


# ==========================================================================
#  Linear regression with uncertainty
# ==========================================================================

def fit_linear(x: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
    """lmfit linear regression with stderr."""
    m = LinearModel()
    try:
        r = m.fit(y, m.guess(y, x=x), x=x)
        return {
            "slope": float(r.params["slope"].value),
            "intercept": float(r.params["intercept"].value),
            "slope_stderr": float(r.params["slope"].stderr or 0),
            "intercept_stderr": float(r.params["intercept"].stderr or 0),
            "r_squared": (1.0 - r.residual.var() / y.var()
                          if y.var() > 0 else np.nan),
        }
    except Exception:
        return dict(slope=np.nan, intercept=np.nan,
                    slope_stderr=0.0, intercept_stderr=0.0,
                    r_squared=np.nan)
        logger.warning("异常已处理", exc_info=True)


def fit_avrami(t: np.ndarray, Xc: np.ndarray) -> Dict[str, Any]:
    """Avrami: ln(-ln(1-Xc)) = n*ln(t) + ln(k)."""
    mask = (Xc > 0.01) & (Xc < 0.99)
    if np.sum(mask) < 5:
        return dict(n=np.nan, k=np.nan, n_stderr=0.0, r_squared=np.nan)
    r = fit_linear(np.log(t[mask]), np.log(-np.log(1 - Xc[mask])))
    return dict(n=r["slope"], k=np.exp(r["intercept"]),
                n_stderr=r["slope_stderr"], r_squared=r["r_squared"])


def fit_guinier(q: np.ndarray, I: np.ndarray) -> Dict[str, Any]:
    """Guinier: ln(I) vs q^2 -> Rg, I0."""
    mask = (q > 0) & (I > 0)
    if np.sum(mask) < 5:
        return dict(Rg=np.nan, I0=np.nan, Rg_stderr=0.0, r_squared=np.nan)
    n = min(len(q), max(5, len(q) // 5))
    r = fit_linear(q[mask][:n]**2, np.log(I[mask][:n]))
    Rg = np.sqrt(-3 * r["slope"]) if r["slope"] < 0 else np.nan
    return dict(
        Rg=Rg, I0=np.exp(r["intercept"]),
        Rg_stderr=(np.sqrt(abs(3*r["slope_stderr"]/(2*Rg)))
                   if not np.isnan(Rg) and r["slope_stderr"] > 0 else 0.0),
        r_squared=r["r_squared"],
    )


# ==========================================================================
#  WAXS joint profile fitting — crystal peaks + amorphous halo(s)
# ==========================================================================

def fit_waxs_profile(
    x: np.ndarray,
    y: np.ndarray,
    crystal_centers: List[float],
    n_halos: int = 1,
    peak_type: str = "pseudo_voigt",
    halo_range: Tuple[float, float] = (10.0, 35.0),
    constraint_centers: Optional[List[float]] = None,
    baseline: str = "linear",
) -> Dict[str, Any]:
    """Single-pass joint fit of crystalline peaks + amorphous halo(s).

    Parameters
    ----------
    constraint_centers : list of float, optional
        Known peak positions from polymer DB.  These get tight centre
        bounds (±0.8°) in the lmfit, preventing the optimizer from
        drifting to wrong positions.  Used for semi-supervised fitting.

    Correct model for polymer WAXS:

        I_measured = baseline(2θ) + Σ I_crystal_i(2θ) + Σ I_halo_j(2θ)

    Caller should subtract instrumental background (e.g. arPLS) before
    calling this function.  Halo peaks are modelled as broad Pseudo-Voigt
    components with sigma constrained to 3–25°; crystal peaks get
    tight sigma bounds (0.1–3°).

    Parameters
    ----------
    x : (N,) array
        2θ values in degrees.
    y : (N,) array
        Baseline-corrected intensity.
    crystal_centers : list of float
        Initial 2θ positions for crystalline peaks.
    n_halos : int
        Number of broad amorphous halo components (1 or 2).
    peak_type : str
        'gaussian', 'lorentzian', or 'pseudo_voigt'.
    halo_range : (float, float)
        2θ range where halo centroids are expected.

    Returns
    -------
    dict with keys:
        components  — per-peak dicts with is_crystal flag
        r_squared, fit_y, halo_y, residuals
    """
    result: Dict[str, Any] = {
        "components": [], "r_squared": np.nan,
        "fit_y": np.array([]), "halo_y": np.array([]),
        "baseline_y": np.array([]),
        "residuals": np.array([]),
    }

    if len(x) < 10 or len(crystal_centers) == 0:
        return result

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    y_max = float(np.max(y))
    x_range = float(x[-1] - x[0])

    # ---- Estimate halo centroid(s) from residual after crystal guess ----
    halo_centers = []
    if n_halos > 0:
        # Build rough crystal model to compute residual.
        # Use wider subtraction windows (sigma ~0.8°) to avoid leaving
        # crystal peak remnants that get mistaken for halos.
        y_resid = y.copy().astype(float)
        for cx in crystal_centers:
            idx = int(np.argmin(np.abs(x - cx)))
            half_w = max(5, int(2.5 / np.mean(np.diff(x))))      # was 1.5°
            lo, hi = max(0, idx - half_w), min(len(x), idx + half_w)
            if lo < hi:
                local_max = float(np.max(y[lo:hi]))
                # Wider sigma so crystal peaks are fully removed from residual
                sigma_est = 0.8                                    # was 0.5
                gauss = local_max * np.exp(-0.5 * ((x - cx) / sigma_est) ** 2)
                y_resid = np.maximum(y_resid - gauss, 0)

        # Build exclusion zones around crystal centres (±2°)
        exclusion = np.zeros(len(x), dtype=bool)
        for cx in crystal_centers:
            exclusion |= np.abs(x - cx) <= 2.0

        # Find halo positions in residual within halo_range,
        # but skip regions within 2° of any known crystal peak.
        mask_halo = (x >= halo_range[0]) & (x <= halo_range[1]) & ~exclusion
        if np.sum(mask_halo) > 10:
            x_hr, y_hr = x[mask_halo], y_resid[mask_halo]
            from scipy.signal import find_peaks
            pk_idx, props = find_peaks(
                y_hr,
                height=max(y_hr.max() * 0.05, 1e-9),
                prominence=max(y_hr.max() * 0.02, 1e-9),
                distance=max(3, len(y_hr) // (n_halos + 2)),
            )
            if len(pk_idx) > 0:
                sorted_idx = pk_idx[np.argsort(props['peak_heights'])[::-1]]
                halo_centers = [float(x_hr[i]) for i in sorted_idx[:n_halos]]

        # If exclusion removed all candidates, search without exclusion
        if len(halo_centers) == 0:
            mask_halo = (x >= halo_range[0]) & (x <= halo_range[1])
            if np.sum(mask_halo) > 10:
                x_hr, y_hr = x[mask_halo], y_resid[mask_halo]
                from scipy.signal import find_peaks
                pk_idx, props = find_peaks(
                    y_hr,
                    height=max(y_hr.max() * 0.05, 1e-9),
                    prominence=max(y_hr.max() * 0.02, 1e-9),
                    distance=max(3, len(y_hr) // (n_halos + 2)),
                )
                if len(pk_idx) > 0:
                    sorted_idx = pk_idx[np.argsort(props['peak_heights'])[::-1]]
                    halo_centers = [float(x_hr[i]) for i in sorted_idx[:n_halos]]

        # Fallback: evenly space halos across the range
        if len(halo_centers) < n_halos:
            if n_halos == 1:
                halo_centers = [float((halo_range[0] + halo_range[1]) / 2)]
            else:
                halo_centers = list(np.linspace(
                    halo_range[0] + 3, halo_range[1] - 3, n_halos))

    # ---- Build lmfit composite model ----
    n_crystal = len(crystal_centers)
    peak_cls = {
        "gaussian": GaussianModel,
        "lorentzian": LorentzianModel,
        "pseudo_voigt": PseudoVoigtModel,
    }.get(peak_type, GaussianModel)

    composite = None
    baseline_model = None
    if baseline == "linear":
        baseline_model = LinearModel(prefix="b_")
    elif baseline == "constant":
        baseline_model = ConstantModel(prefix="b_")
    elif baseline == "quadratic":
        baseline_model = QuadraticModel(prefix="b_")
    if baseline_model is not None:
        composite = baseline_model

    # Crystal peaks
    for i, cx in enumerate(crystal_centers):
        p = peak_cls(prefix=f"c{i}_")
        composite = p if composite is None else composite + p

    # Halo peaks
    for j, hx in enumerate(halo_centers):
        p = peak_cls(prefix=f"h{j}_")
        composite = p if composite is None else composite + p

    if composite is None:
        return result

    params = composite.make_params()

    if baseline_model is not None:
        edge_n = max(3, len(y) // 20)
        y_edge = np.r_[y[:edge_n], y[-edge_n:]]
        y_edge_med = float(np.nanmedian(y_edge)) if len(y_edge) else 0.0
        if baseline == "linear":
            slope, intercept = np.polyfit(x, y, 1)
            params["b_slope"].set(value=float(slope))
            params["b_intercept"].set(value=max(float(intercept), 0.0), min=0, max=max(y_max * 2, 1.0))
        elif baseline == "constant":
            params["b_c"].set(value=y_edge_med, min=0, max=max(y_max * 2, 1.0))
        elif baseline == "quadratic":
            coeffs = np.polyfit(x, y, 2)
            params["b_a"].set(value=float(coeffs[0]))
            params["b_b"].set(value=float(coeffs[1]))
            params["b_c"].set(value=max(float(coeffs[2]), 0.0), min=0, max=max(y_max * 2, 1.0))

    # Crystal peak initial guesses & bounds
    amp_guess = y_max / max(n_crystal + n_halos, 1)
    constraint_set = set(constraint_centers) if constraint_centers else set()
    for i, cx in enumerate(crystal_centers):
        # Tight bounds for known peaks (semi-supervised)
        is_constrained = any(abs(cx - cc) < 1.5 for cc in constraint_set)
        if is_constrained:
            params[f"c{i}_center"].set(value=cx, min=cx - 0.8, max=cx + 0.8)
        else:
            params[f"c{i}_center"].set(value=cx, min=x[0], max=x[-1])
        params[f"c{i}_amplitude"].set(value=amp_guess, min=0)
        params[f"c{i}_sigma"].set(value=0.5, min=0.05, max=1.5)
        if peak_type == "pseudo_voigt":
            params[f"c{i}_fraction"].set(value=0.5, min=0.0, max=1.0)

    # Halo peak initial guesses & bounds (broad)
    for j, hx in enumerate(halo_centers):
        params[f"h{j}_center"].set(value=hx, min=halo_range[0], max=halo_range[1])
        params[f"h{j}_amplitude"].set(value=amp_guess * 0.5, min=0)
        params[f"h{j}_sigma"].set(value=8.0, min=3.0, max=15.0)   # was max=25.0 — too wide, swallows crystal peaks
        if peak_type == "pseudo_voigt":
            # Halo closer to Lorentzian (eta near 0 gives Gaussian, near 1 gives Lorentzian)
            params[f"h{j}_fraction"].set(value=0.7, min=0.0, max=1.0)

    # ---- Fit ----
    try:
        fit_result = composite.fit(y, params, x=x,
                                    method="leastsq", max_nfev=8000)
    except Exception:
        try:
            # Fallback: nelder (simplex) for difficult cases
            fit_result = composite.fit(y, params, x=x,
                                        method="nelder", max_nfev=8000)
        except Exception:
            return result
        logger.warning("异常已处理", exc_info=True)

    # ---- Extract results ----
    y_fit = fit_result.best_fit
    result["r_squared"] = (1.0 - fit_result.residual.var() / y.var()
                           if y.var() > 0 else np.nan)
    result["fit_y"] = y_fit
    result["residuals"] = fit_result.residual
    if baseline_model is not None:
        try:
            result["baseline_y"] = fit_result.eval_components(x=x).get("b_", np.zeros_like(x))
        except Exception:
            result["baseline_y"] = np.zeros_like(x)
            logger.warning("异常已处理", exc_info=True)

    # Per-peak extraction
    for i in range(n_crystal):
        pfx = f"c{i}_"
        try:
            c = float(fit_result.params[f"{pfx}center"].value)
            a = float(fit_result.params[f"{pfx}amplitude"].value)
            s = float(fit_result.params[f"{pfx}sigma"].value)
            fwhm = float(fit_result.params[f"{pfx}fwhm"].value)
            # lmfit amplitude = integrated area for Gaussian/Lorentzian/PseudoVoigt
            area = float(a)
            result["components"].append({
                "index": i, "center": c, "amplitude": a,
                "sigma": s, "fwhm": fwhm, "area": area,
                "is_crystal": True,
            })
        except (KeyError, TypeError):
            continue

    for j in range(len(halo_centers)):
        pfx = f"h{j}_"
        try:
            c = float(fit_result.params[f"{pfx}center"].value)
            a = float(fit_result.params[f"{pfx}amplitude"].value)
            s = float(fit_result.params[f"{pfx}sigma"].value)
            fwhm = float(fit_result.params[f"{pfx}fwhm"].value)
            # lmfit amplitude = integrated area
            area = float(a)
            result["components"].append({
                "index": n_crystal + j, "center": c, "amplitude": a,
                "sigma": s, "fwhm": fwhm, "area": area,
                "is_crystal": False,
            })
        except (KeyError, TypeError):
            continue

    # Build halo-only intensity curve
    halo_y = np.zeros_like(x)
    if len(halo_centers) > 0:
        h_cls = peak_cls
        for j in range(len(halo_centers)):
            pfx = f"h{j}_"
            try:
                c = float(fit_result.params[f"{pfx}center"].value)
                a = float(fit_result.params[f"{pfx}amplitude"].value)
                s = float(fit_result.params[f"{pfx}sigma"].value)
                if peak_type == "pseudo_voigt":
                    frac = float(fit_result.params[f"{pfx}fraction"].value)
                    halo_y += h_cls().eval(
                        x=x, center=c, amplitude=a, sigma=s, fraction=frac)
                else:
                    halo_y += h_cls().eval(
                        x=x, center=c, amplitude=a, sigma=s)
            except (KeyError, TypeError, AttributeError):
                continue
    result["halo_y"] = halo_y

    return result
