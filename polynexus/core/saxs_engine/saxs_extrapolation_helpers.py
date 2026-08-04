from __future__ import annotations

from typing import Tuple

import numpy as np

from ..engine import logger


def _extrapolate_guinier(
    q: np.ndarray, I: np.ndarray, dq: float, n_extra: int = 15,
) -> Tuple[np.ndarray, np.ndarray]:
    """Extrapolate finite low-q intensity with the Guinier relation.

    For a valid low-q region, ``ln(I) = ln(I0) - Rg^2*q^2/3``.  The old
    implementation fitted ``q^2 I`` through the origin, which creates an
    artificial ``1/q`` singularity at the origin and is not a Guinier
    extrapolation.
    """
    if len(q) < 5:
        return q, I

    n_fit = min(8, len(q))
    q_fit = q[:n_fit]
    I_fit = I[:n_fit]
    pos = (q_fit > 0) & np.isfinite(q_fit) & np.isfinite(I_fit) & (I_fit > 0)
    if np.sum(pos) < 3:
        return q, I

    try:
        p = np.polyfit(q_fit[pos] ** 2, np.log(I_fit[pos]), 1)
        slope, intercept = float(p[0]), float(p[1])
    except Exception:
        logger.warning("SAXS Guinier extrapolation fit failed; returning original data.", exc_info=True)
        return q, I

    if not np.isfinite(intercept) or not np.isfinite(slope):
        return q, I

    I0 = float(np.exp(intercept))
    if not np.isfinite(I0) or I0 <= 0:
        return q, I

    rg2 = max(0.0, -3.0 * slope)

    q_new = np.linspace(0, q[0] - dq, n_extra)
    I_new = I0 * np.exp(-(rg2 / 3.0) * q_new ** 2)

    q_full = np.concatenate([q_new, q])
    I_full = np.concatenate([I_new, I])
    return q_full, I_full


def _extrapolate_porod(
    q: np.ndarray, I: np.ndarray, dq: float, n_extra: int = 30,
) -> Tuple[np.ndarray, np.ndarray]:
    """Extrapolate I(q) to q->inf using Porod law."""
    if len(q) < 10:
        return q, I

    n_porod = max(8, len(q) // 3)
    q_p = q[-n_porod:]
    I_p = I[-n_porod:]

    try:
        p = np.polyfit(q_p ** 4, I_p * q_p ** 4, 1)
        Kp = float(p[1])
        slope = float(p[0])
        if Kp <= 0:
            Kp = np.median(I_p * q_p ** 4)
            slope = 0.0
    except Exception:
        Kp = np.median(I_p * q_p ** 4)
        slope = 0.0
        logger.warning("SAXS Porod extrapolation fit failed; using median fallback.", exc_info=True)

    q_max = q[-1]
    Iq4_boundary = float(np.median(I[-5:] * q[-5:] ** 4))
    Iq4_fit_at_max = slope * q_max**4 + Kp
    if Iq4_boundary <= 0:
        Iq4_boundary = max(Iq4_fit_at_max, 1e-30)
    else:
        Iq4_boundary = 0.70 * Iq4_boundary + 0.30 * Iq4_fit_at_max

    q_new = np.linspace(q_max + dq, q_max + n_extra * dq, n_extra)
    I_new = Iq4_boundary / q_new ** 4

    q_full = np.concatenate([q, q_new[1:]])
    I_full = np.concatenate([I, I_new[1:]])
    return q_full, I_full
