"""IR data preprocessing module.

Pipeline:
    1. Transmittance → Absorbance conversion
    2. ATR penetration depth correction
    3. Baseline correction (rubberband, ALS, polynomial, linear)
    4. Smoothing (Savitzky-Golay)
    5. Normalisation (min-max or area)
"""

import logging
logger = logging.getLogger(__name__)

import numpy as np
from scipy import signal, sparse
from scipy.sparse.linalg import spsolve
from scipy.ndimage import uniform_filter1d
from typing import List, Optional, Tuple

from .io import IRSpectrum
from .config import IRConfig


# ---------------------------------------------------------------------------
#  Transmittance ↔ Absorbance
# ---------------------------------------------------------------------------

def transmittance_to_absorbance(T: np.ndarray) -> np.ndarray:
    """Convert transmittance (0-1 or 0-100) to absorbance.

    A = -log10(T)  for T in (0, 1]
    A = -log10(T/100) for T in (0, 100]
    """
    T = np.asarray(T, dtype=float)
    if np.max(T) > 1.1:
        T = T / 100.0
    T = np.clip(T, 1e-6, 1.0)
    return -np.log10(T)


def absorbance_to_transmittance(A: np.ndarray) -> np.ndarray:
    return 10.0 ** (-np.asarray(A))


# ---------------------------------------------------------------------------
#  ATR correction (penetration depth)
# ---------------------------------------------------------------------------

ATR_CRYSTAL_RI = {
    'diamond': 2.42,
    'ZnSe': 2.43,
    'Ge': 4.00,
    'Si': 3.42,
    'KRS-5': 2.37,
}


def atr_correction(wavenumber: np.ndarray, absorbance: np.ndarray,
                   crystal: str = 'diamond',
                   angle_deg: float = 45.0,
                   sample_ri: float = 1.5,
                   ) -> np.ndarray:
    """Apply ATR penetration depth correction.

    The evanescent wave penetration depth depends on wavelength:
        dp = λ / (2π * n_crystal * √(sin²θ - (n_sample/n_crystal)²))

    Longer wavelengths (lower wavenumber) penetrate deeper, so low-wavenumber
    bands are disproportionately stronger. This correction compensates.

    Parameters
    ----------
    crystal : str
        ATR crystal material.
    angle_deg : float
        Incidence angle.
    sample_ri : float
        Refractive index of sample (~1.5 for polymers).
    """
    n_crystal = ATR_CRYSTAL_RI.get(crystal, 2.42)
    theta_rad = np.radians(angle_deg)
    sin2_theta = np.sin(theta_rad) ** 2
    ratio_sq = (sample_ri / n_crystal) ** 2

    if sin2_theta <= ratio_sq:
        return np.asarray(absorbance)  # total internal reflection not satisfied

    denominator = np.sqrt(sin2_theta - ratio_sq)

    # Wavelength in cm (1 / wavenumber_cm1)
    # dp ∝ λ ∝ 1 / wavenumber
    # Correction factor ∝ 1 / dp ∝ wavenumber
    dp_factor = np.asarray(wavenumber, dtype=float)
    dp_factor = dp_factor / np.median(dp_factor)  # normalise around 1

    # Apply: A_corrected = A * correction
    correction = dp_factor
    correction = np.clip(correction, 0.1, 10.0)  # safety bounds

    return np.asarray(absorbance) * correction


# ---------------------------------------------------------------------------
#  Baseline correction
# ---------------------------------------------------------------------------

def baseline_rubberband(wavenumber: np.ndarray, absorbance: np.ndarray,
                        ) -> Tuple[np.ndarray, np.ndarray]:
    """Rubberband baseline correction (standard in IR spectroscopy).

    Finds the convex hull of the spectrum and uses its lower envelope
    as the baseline. Works well for IR spectra with broad backgrounds.
    """
    # IR spectra: high wavenumber on left, decreasing
    x = np.asarray(wavenumber, dtype=float)
    y = np.asarray(absorbance, dtype=float)

    if len(x) < 3:
        return y, np.zeros_like(y)

    try:
        from pybaselines import Baseline
        if x[0] > x[-1]:
            x_fit, y_fit = x[::-1], y[::-1]
            reverse = True
        else:
            x_fit, y_fit = x, y
            reverse = False
        baseline_fit, _ = Baseline(x_data=x_fit, assume_sorted=True).rubberband(y_fit)
        baseline = baseline_fit[::-1] if reverse else baseline_fit
        return y - baseline, baseline
    except Exception:
        logger.warning("静默异常", exc_info=True)

    # Use every Nth point for the convex hull to speed up
    n = max(3, len(x) // 50)
    idx = np.arange(0, len(x), n, dtype=int)
    x_sub = x[idx]
    y_sub = y[idx]

    # Build convex hull (lower envelope for IR where peaks go up)
    from scipy.spatial import ConvexHull
    points = np.column_stack([x_sub, y_sub])
    try:
        hull = ConvexHull(points)
    except Exception:
        return y, np.zeros_like(y)

    # Extract lower envelope
    hull_vertices = hull.vertices
    # Sort by x
    vx = x_sub[hull_vertices]
    vy = y_sub[hull_vertices]
    sort_idx = np.argsort(vx)
    vx = vx[sort_idx]
    vy = vy[sort_idx]

    # Find the lower boundary: walk from left to right, keep minimum
    lower_x, lower_y = [], []
    current_min = vy[0]
    for i in range(len(vx)):
        if vy[i] <= current_min + 0.001:
            lower_x.append(vx[i])
            lower_y.append(vy[i])
            current_min = vy[i]

    if len(lower_x) < 2:
        return y, np.zeros_like(y)

    # Interpolate to full x range
    baseline = np.interp(x, lower_x, lower_y)

    # Shift baseline so minimum is at zero
    baseline = baseline - np.min(baseline)

    return y - baseline, baseline


def baseline_mute_zone(wavenumber: np.ndarray, absorbance: np.ndarray,
                       mute_windows: Optional[List[Tuple[float, float]]] = None,
                       ) -> Tuple[np.ndarray, np.ndarray]:
    """Mute-zone linear baseline correction for in-situ temperature IR.

    Identifies anchor points in spectral regions without absorption
    ("mute zones"), then subtracts a piecewise-linear baseline
    interpolated through the absorbance minima in those windows.

    This is intentionally conservative — it removes only the broad
    instrumental drift while preserving all chemically meaningful
    temperature-induced changes for 2D-COS analysis.

    Parameters
    ----------
    wavenumber : np.ndarray (cm⁻¹)
    absorbance : np.ndarray
    mute_windows : list of (low_cm1, high_cm1) windows with no absorption.
        Defaults are tuned for PA6/polyamide IR.

    Returns
    -------
    corrected : np.ndarray
    baseline : np.ndarray
    """
    x = np.asarray(wavenumber, dtype=float)
    y = np.asarray(absorbance, dtype=float)

    if mute_windows is None:
        mute_windows = [
            (3990.0, 4005.0),   # far high-wavenumber tail
            (1900.0, 2000.0),   # gap between amide and CH bending
            (450.0, 480.0),     # low-wavenumber tail
        ]

    anchor_x: List[float] = []
    anchor_y: List[float] = []

    for wlo, whi in mute_windows:
        lo, hi = (min(wlo, whi), max(wlo, whi))
        mask = (x >= lo) & (x <= hi)
        if np.sum(mask) >= 3:
            # Use median of the lowest 40% of points in the window
            vals = y[mask]
            threshold = np.percentile(vals, 40)
            low_vals = vals[vals <= threshold]
            if len(low_vals) >= 2:
                anchor_x.append(float(np.median(x[mask][vals <= threshold])))
                anchor_y.append(float(np.median(low_vals)))
            else:
                anchor_x.append(float(np.median(x[mask])))
                anchor_y.append(float(np.median(vals)))

    if len(anchor_x) < 2:
        return y.copy(), np.zeros_like(y)

    # Sort anchors by wavenumber (which is decreasing for IR)
    order = np.argsort(anchor_x)
    anchor_x_arr = np.array(anchor_x, dtype=float)[order]
    anchor_y_arr = np.array(anchor_y, dtype=float)[order]

    # Interpolate baseline across full x range
    baseline = np.interp(x, anchor_x_arr, anchor_y_arr)

    return y - baseline, baseline


def baseline_als(y: np.ndarray, lam: float = 1e6, p: float = 0.001,
                 n_iter: int = 10) -> np.ndarray:
    """Asymmetric Least Squares baseline correction.

    Parameters
    ----------
    lam : float
        Smoothness parameter (larger = smoother).
    p : float
        Asymmetry parameter (0.001 = positive peaks).
    n_iter : int
        Number of iterations.
    """
    try:
        from pybaselines import Baseline
        baseline, _ = Baseline().asls(np.asarray(y, dtype=float),
                                      lam=lam, p=p, max_iter=n_iter)
        return baseline
    except Exception:
        logger.warning("静默异常", exc_info=True)

    L = len(y)
    D = sparse.diags([1, -2, 1], [0, -1, -2], shape=(L, L - 2))
    D = D.dot(D.T)
    w = np.ones(L)
    z = np.zeros(L)

    for i in range(n_iter):
        W = sparse.diags(w, 0, shape=(L, L))
        Z = W + lam * D
        z = spsolve(Z, w * y)
        w = p * (y > z) + (1 - p) * (y < z)

    return z


def correct_baseline(wavenumber: np.ndarray, absorbance: np.ndarray,
                     method: str = 'rubberband',
                     lam: float = 1e6, p: float = 0.001,
                     ) -> Tuple[np.ndarray, np.ndarray]:
    """Apply baseline correction.

    Returns (corrected_absorbance, baseline).
    """
    y = np.asarray(absorbance, dtype=float)
    x = np.asarray(wavenumber, dtype=float)

    if method == 'rubberband':
        return baseline_rubberband(x, y)
    elif method == 'mute_zone':
        return baseline_mute_zone(x, y)
    elif method == 'als':
        bl = baseline_als(y, lam=lam, p=p)
        return y - bl, bl
    elif method == 'linear':
        xp = np.array([x[0], x[-1]], dtype=float)
        yp = np.array([y[0], y[-1]], dtype=float)
        order = np.argsort(xp)
        bl = np.interp(x, xp[order], yp[order])
        return y - bl, bl
    elif method == 'polynomial':
        coeffs = np.polyfit(x, y, 3)
        bl = np.polyval(coeffs, x)
        return y - bl, bl
    else:
        return y, np.zeros_like(y)


# ---------------------------------------------------------------------------
#  Smoothing
# ---------------------------------------------------------------------------

def smooth_profile(absorbance: np.ndarray, method: str = 'savgol',
                   window: int = 7, order: int = 3,
                   ) -> np.ndarray:
    """Smooth IR absorbance spectrum."""
    if method == 'none':
        return np.asarray(absorbance)
    elif method == 'savgol':
        if window % 2 == 0:
            window += 1
        if len(absorbance) < window:
            return np.asarray(absorbance)
        order = min(order, window - 1)
        return signal.savgol_filter(absorbance, window, order)
    else:
        return np.asarray(absorbance)


# ---------------------------------------------------------------------------
#  Normalisation
# ---------------------------------------------------------------------------

def normalise_spectrum(absorbance: np.ndarray, method: str = 'minmax',
                       ) -> np.ndarray:
    """Normalise absorbance spectrum.

    'minmax': to [0, 1]
    'area': divide by total area
    'peak': divide by max
    """
    y = np.asarray(absorbance, dtype=float)
    if method == 'minmax':
        y_min, y_max = np.min(y), np.max(y)
        if y_max - y_min > 1e-12:
            return (y - y_min) / (y_max - y_min)
        return y
    elif method == 'area':
        total = np.trapezoid(y)
        return y / total if abs(total) > 1e-12 else y
    elif method == 'peak':
        return y / np.max(y) if np.max(y) > 1e-12 else y
    return y


# ---------------------------------------------------------------------------
#  Full preprocessing pipeline
# ---------------------------------------------------------------------------

def preprocess_pipeline(spectrum: IRSpectrum, config: IRConfig,
                        ) -> IRSpectrum:
    """Run full IR preprocessing on one spectrum.

    Steps:
        1. Convert transmittance to absorbance if needed
        2. ATR correction
        3. Baseline correction
        4. Smoothing
        5. Normalisation
    """
    if not spectrum.has_data:
        return spectrum

    wn = spectrum.wavenumber.copy()

    # 1. Get absorbance
    if len(spectrum.transmittance) > 0 and len(spectrum.absorbance) == 0:
        A = transmittance_to_absorbance(spectrum.transmittance)
    else:
        A = spectrum.absorbance.copy()

    # 2. ATR correction
    if config.atr_correction:
        A = atr_correction(wn, A, config.atr_crystal, config.atr_angle_deg)

    # Save raw absorbance (post-ATR, pre-baseline) for temperature 2D analysis
    spectrum.raw_absorbance = A.copy()

    # 3. Baseline correction
    A, bg = correct_baseline(
        wn, A,
        method=config.baseline_method,
        lam=config.baseline_lam,
        p=config.baseline_p,
    )
    spectrum.metadata['baseline'] = bg

    # 4. Smoothing
    if config.smooth_method != 'none':
        A = smooth_profile(A, method=config.smooth_method,
                           window=config.smooth_window,
                           order=config.smooth_order)

    # 5. Normalisation
    normalization_method = getattr(config, "normalization_method", "minmax")
    if config.normalise and normalization_method != "none":
        A = normalise_spectrum(A, method=normalization_method)

    spectrum.wavenumber = wn
    spectrum.absorbance = A
    return spectrum
