from __future__ import annotations

import numpy as np


def clean_guinier_case() -> tuple[np.ndarray, np.ndarray]:
    q = np.linspace(0.01, 0.24, 32)
    intensity = 120.0 * np.exp(-(q**2) * 4.5**2 / 3.0)
    return q, intensity


def dirty_guinier_case() -> tuple[np.ndarray, np.ndarray]:
    q, intensity = clean_guinier_case()
    q = q.copy()
    intensity = intensity.copy()
    q[5] = np.nan
    q[6] = q[7]
    intensity[8] = np.nan
    intensity[9] = -1.0
    return q, intensity


def low_q_truncated_case() -> tuple[np.ndarray, np.ndarray]:
    q = np.linspace(0.12, 0.24, 24)
    intensity = 120.0 * np.exp(-(q**2) * 4.5**2 / 3.0)
    return q, intensity
