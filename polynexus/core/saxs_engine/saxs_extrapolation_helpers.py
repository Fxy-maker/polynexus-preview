from __future__ import annotations

from typing import Tuple

import numpy as np

from ..engine import logger


def _extrapolate_guinier(
    q: np.ndarray, I: np.ndarray, dq: float, n_extra: int = 15,
) -> Tuple[np.ndarray, np.ndarray]:
    """Extrapolate I(q) to q=0 via linear I*q^2 interpolation."""
    if len(q) < 5:
        return q, I

    n_fit = min(8, len(q))
    q_fit = q[:n_fit]
    Iq2_fit = I[:n_fit] * q_fit ** 2

    pos = (q_fit > 0) & (Iq2_fit > 0)
    if np.sum(pos) < 3:
        return q, I

    try:
        p = np.polyfit(q_fit[pos], Iq2_fit[pos], 1)
        slope, intercept = float(p[0]), float(p[1])
    except Exception:
        logger.warning("SAXS Guinier extrapolation fit failed; returning original data.", exc_info=True)
        return q, I

    if abs(intercept) > max(1e-6, abs(slope * q_fit[0]) * 0.5):
        slope = float(np.sum(q_fit[pos] * Iq2_fit[pos]) / max(np.sum(q_fit[pos] ** 2), 1e-15))

    q_new = np.linspace(0, q[0] - dq, n_extra)
    Iq2_new = slope * q_new
    Iq2_new = np.clip(Iq2_new, 0, None)

    if q_new[-1] > 0 and Iq2_new[-1] > 0 and q[0] > 0 and I[0] > 0:
        Iq2_target = I[0] * q[0] ** 2
        bm_scale = Iq2_target / Iq2_new[-1]
        bm_scale = max(0.01, min(bm_scale, 100.0))
        Iq2_new = Iq2_new * bm_scale

    I_new = np.zeros(n_extra)
    pos_q = q_new > 1e-15
    I_new[pos_q] = Iq2_new[pos_q] / (q_new[pos_q] ** 2)
    if not pos_q[0] and slope > 0:
        I_new[0] = float(slope / (q_new[1] if len(q_new) > 1 else dq))

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
