from __future__ import annotations

from typing import Dict, Tuple

import numpy as np

from ..engine import logger
from .config import SAXSConfig
from .saxs_quality_contracts import sanitize_1d_profile


def _tangent_lc(corr_result: Dict, L: float, cfg: SAXSConfig) -> float:
    """Extract crystalline thickness lc from correlation function via tangent method."""
    r = corr_result.get("r", None)
    gamma = corr_result.get("gamma", None)

    if r is None or gamma is None or len(r) < 10:
        return np.nan

    r_ub = int(np.searchsorted(r, L * 0.7)) if np.isfinite(L) and L > 0 else len(gamma) - 1
    r_ub = max(10, min(r_ub, len(gamma) - 2))
    min_idx = None
    for i in range(5, r_ub):
        if gamma[i] < gamma[i - 1] and gamma[i] < gamma[i + 1]:
            if gamma[i] < 0.5:
                min_idx = i
                break

    if min_idx is None:
        for i in range(5, r_ub):
            if gamma[i] <= 0:
                min_idx = i
                break

    if min_idx is None and L > 0 and np.isfinite(L):
        r_search_end = min(2.0 * L, r[r_ub])
        r_mask = (r >= 2.0) & (r <= r_search_end)
        if np.sum(r_mask) > 3:
            min_idx = int(np.argmin(gamma[r_mask])) + int(np.argmax(r_mask))

    if min_idx is None or min_idx < 5:
        return np.nan

    r_start = max(r[5], r[min_idx] * 0.20)
    start_idx = int(np.searchsorted(r, r_start))
    end_idx = min_idx
    if end_idx - start_idx < 3:
        return np.nan

    r_fit = r[start_idx:end_idx]
    gamma_fit = gamma[start_idx:end_idx]

    try:
        w = r_fit**0.5
        p, _cov = np.polyfit(r_fit, gamma_fit, 1, w=w, cov=True)
        a, b = p
        gamma_pred = a * r_fit + b
        ss_res = np.sum((gamma_fit - gamma_pred) ** 2)
        ss_tot = np.sum((gamma_fit - np.mean(gamma_fit)) ** 2)
        r2 = 1 - ss_res / (ss_tot + 1e-12)
        if r2 < 0.70:
            a, b = np.polyfit(r_fit, gamma_fit, 1)
    except Exception:
        logger.warning("SAXS tangent lc fit failed.", exc_info=True)
        return np.nan

    tail_start = int(len(r) * 0.70)
    if tail_start < len(gamma):
        baseline = float(np.median(gamma[tail_start:]))
        baseline = min(baseline, 0.0)
        baseline = max(baseline, -0.05 * gamma[0])
    else:
        baseline = 0.0

    if abs(a) < 1e-12:
        return np.nan
    lc = (baseline - b) / a

    if np.isfinite(lc) and 0 < lc < L * 0.7:
        return float(lc)
    return np.nan


def _crystallinity_invariant(L: float, Q_invariant: float, Kp: float) -> float:
    """Estimate linear crystallinity from the Porod invariant."""
    if not (np.isfinite(L) and np.isfinite(Q_invariant) and np.isfinite(Kp)):
        return np.nan
    if L <= 0 or Q_invariant <= 0 or Kp <= 0:
        return np.nan

    denom = 4.0 * np.pi**4 * Kp
    c_term = Q_invariant * L / denom

    disc = 1.0 - 4.0 * c_term
    if disc < 0:
        return np.nan

    phi_c = (1.0 - np.sqrt(disc)) / 2.0
    if 0.0 < phi_c <= 0.5:
        return float(phi_c)
    phi_c = (1.0 + np.sqrt(disc)) / 2.0
    if 0.5 < phi_c < 1.0:
        return float(phi_c)
    return np.nan


def guinier_analysis(
    q: np.ndarray,
    I: np.ndarray,  # noqa: E741 - preserve the legacy public parameter name
    q_min: float | None = None,
    q_max_factor: float = 1.3,
) -> Tuple[float, float, np.ndarray, np.ndarray]:
    """Guinier analysis: ln(I) vs q^2 in the low-q region."""
    del q_max_factor

    mask = np.isfinite(q) & np.isfinite(I)
    if q_min is not None:
        mask &= q >= float(q_min)
    q_valid = q[mask]
    I_valid = I[mask]

    if len(q_valid) < 10:
        return np.nan, np.nan, np.array([]), np.array([])

    n_lowq = max(10, len(q_valid) // 5)
    q_low = q_valid[:n_lowq]
    I_low = I_valid[:n_lowq]

    pos = I_low > 0
    if np.sum(pos) < 5:
        return np.nan, np.nan, np.array([]), np.array([])

    q_sel = q_low[pos]
    I_sel = I_low[pos]
    lnI = np.log(I_sel)
    q2 = q_sel**2

    from numpy.polynomial.polynomial import Polynomial

    p = Polynomial.fit(q2, lnI, 1)
    a, b = p.convert().coef

    rg = np.sqrt(-3 * b) if b < 0 else np.nan
    i0 = np.exp(a) if a < 100 else np.nan
    return rg, i0, q_sel, lnI


def porod_analysis(q: np.ndarray, I: np.ndarray, cfg: SAXSConfig) -> Dict:  # noqa: E741 - preserve the legacy public parameter name
    """Porod analysis: I(q) ~ Kp / q^4 at high q."""
    sanitized = sanitize_1d_profile(q, I)
    q = sanitized.q
    intensity = sanitized.intensity
    mask = (q >= cfg.q_porod_min) & (q <= cfg.q_porod_max)
    if np.sum(mask) < 10:
        return {"Kp": np.nan, "Sv": np.nan}

    q_sel = q[mask]
    I_sel = intensity[mask]
    iq4 = I_sel * q_sel**4

    kp = np.median(iq4)
    slope = np.nan
    pos = (q_sel > 0) & (I_sel > 0) & np.isfinite(q_sel) & np.isfinite(I_sel)
    if np.sum(pos) >= 5:
        try:
            slope = float(np.polyfit(np.log(q_sel[pos]), np.log(I_sel[pos]), 1)[0])
        except Exception:
            slope = np.nan
            logger.warning("SAXS Porod slope fit failed.", exc_info=True)

    return {
        "Kp": kp,
        "slope": slope,
        "q_porod": q_sel,
        "Iq4_porod": iq4,
        "Iq4": iq4,
        "Sv": np.nan,
    }


def _porod_constant(q_ext, I_ext, q_raw=None, I_raw=None) -> float:
    """Estimate Porod constant Kp via Porod-plot linear regression."""
    if q_raw is not None and I_raw is not None and len(q_raw) >= 20:
        q_use, I_use = q_raw, I_raw
    elif q_ext is not None and I_ext is not None and len(q_ext) >= 20:
        q_use, I_use = q_ext, I_ext
    else:
        return np.nan

    n_total = len(q_use)
    n_porod = max(10, n_total // 3)
    q_p = q_use[-n_porod:]
    I_p = I_use[-n_porod:]

    iq4 = I_p * q_p**4
    q4 = q_p**4

    try:
        p = np.polyfit(q4, iq4, 1)
        kp = float(p[1])
        if kp <= 0:
            return np.nan
        return kp
    except Exception:
        logger.warning("SAXS Porod constant fit failed.", exc_info=True)
        return np.nan
