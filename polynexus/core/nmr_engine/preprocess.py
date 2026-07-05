"""NMR data preprocessing module.

Pipeline:
    1. Left-shift (remove dead time / group delay)
    2. Apodization (exponential / Gaussian window)
    3. Phase correction (zero-order / first-order)
    4. Baseline correction (polynomial / spline)
    5. Reference shift (calibrate to known reference peak)
    6. Normalisation
"""

import logging
logger = logging.getLogger(__name__)

import numpy as np
from scipy import signal, interpolate, optimize
from typing import Optional, Tuple

from .io import NMRSpectrum
from .config import NMRConfig


# ---------------------------------------------------------------------------
#  Left shift
# ---------------------------------------------------------------------------

def left_shift(ppm, intensity, n_points=0):
    """Remove first n_points (digital filter / group delay)."""
    if n_points <= 0:
        return ppm, intensity
    return ppm[n_points:], intensity[n_points:]


# ---------------------------------------------------------------------------
#  Apodization (window functions)
# ---------------------------------------------------------------------------

def apodization_exponential(fid, lb_hz, sweep_width_hz):
    """Apply exponential line broadening: exp(-pi * lb * t)."""
    n = len(fid)
    t = np.arange(n) / sweep_width_hz
    window = np.exp(-np.pi * lb_hz * t)
    return fid * window


def apodization_gaussian(fid, lb_hz, gb, sweep_width_hz):
    """Apply Gaussian window: exp(-pi*lb*t - a*t^2) where a = pi*lb/(2*gb)."""
    n = len(fid)
    t = np.arange(n) / sweep_width_hz
    a = np.pi * lb_hz / (2.0 * gb) if gb > 0 else 0
    window = np.exp(-np.pi * lb_hz * t - a * t**2)
    return fid * window


# ---------------------------------------------------------------------------
#  Phase correction
# ---------------------------------------------------------------------------

def phase_correct(ppm, intensity, zero_order_deg=0.0, first_order_deg=0.0):
    """Apply zero- and first-order phase correction in frequency domain.

    phase(ω) = φ0 + φ1 * (ω - ω0) / Δω

    Simplified: we work in the time domain approach — apply phase rotation
    to the complex spectrum.
    For real-only data: this is an approximation using Hilbert transform.
    """
    if abs(zero_order_deg) < 0.01 and abs(first_order_deg) < 0.01:
        return intensity

    try:
        from scipy.signal import hilbert
        # Hilbert transform to get analytic signal
        analytic = hilbert(intensity)
        # Phase rotation
        n = len(ppm)
        phase_rad = np.radians(zero_order_deg) + np.radians(first_order_deg) * np.linspace(-1, 1, n)
        rotated = analytic * np.exp(1j * phase_rad)
        return rotated.real
    except Exception:
        return intensity


def auto_phase(intensity, max_iterations=20):
    """Automatic zero-order phase correction by minimising negative signal."""
    from scipy.optimize import minimize_scalar

    n = len(intensity)
    x = np.arange(n)

    def neg_signal(deg):
        corr = phase_correct(x, intensity, zero_order_deg=float(deg))
        return float(np.sum(np.abs(corr[corr < 0]))) if np.any(corr < 0) else 0.0

    res = minimize_scalar(
        neg_signal, bounds=(-180, 180), method='bounded',
        options={'maxiter': max_iterations, 'xatol': 0.5}
    )
    best_phase = float(res.x)
    return phase_correct(x, intensity, zero_order_deg=best_phase)


# ---------------------------------------------------------------------------
#  Baseline correction
# ---------------------------------------------------------------------------

def correct_baseline(ppm, intensity, method='polynomial', order=5):
    """Polynomial or spline baseline correction.

    Methods
    -------
    ``"polynomial"`` / ``"iterative_polynomial"``
        Iterative polynomial baseline (Dietrich-style): fits a polynomial,
        masks regions that deviate more than 2×MAD, refits, and repeats
        until convergence (max 10 iterations).
    ``"simple_polynomial"``
        Single-pass polynomial fit (the old default).
    ``"spline"``
        UnivariateSpline with anchor points.
    ``"linear"``
        Straight line through end-points.
    """
    x_all = np.asarray(ppm, dtype=float)
    y_all = np.asarray(intensity, dtype=float)
    finite = np.isfinite(x_all) & np.isfinite(y_all)
    if not finite.any():
        return y_all, np.zeros_like(y_all)
    x = x_all[finite]
    y = y_all[finite]

    if method in ('polynomial', 'iterative_polynomial'):
        bl = _iterative_poly_baseline(x, y, x_all, order=int(order))
    elif method == 'simple_polynomial':
        fit_order = min(int(order), max(1, len(x) - 1))
        coeffs = np.polyfit(x, y, fit_order)
        bl = np.polyval(coeffs, x_all)
    elif method == 'spline':
        n_anchors = max(5, len(x) // 20)
        anchors = np.linspace(0, len(x) - 1, n_anchors, dtype=int)
        xs = x[anchors]
        ys = y[anchors]
        order_idx = np.argsort(xs)
        spl = interpolate.UnivariateSpline(xs[order_idx], ys[order_idx], s=1e-3)
        bl = spl(x_all)
    elif method == 'linear':
        xp = np.array([x[0], x[-1]], dtype=float)
        yp = np.array([y[0], y[-1]], dtype=float)
        order_idx = np.argsort(xp)
        bl = np.interp(x_all, xp[order_idx], yp[order_idx])
    else:
        bl = np.zeros_like(y_all)

    corrected = np.where(np.isfinite(y_all), y_all - bl, 0.0)
    return corrected, bl


def _iterative_poly_baseline(x_finite, y_finite, x_all, order=5, max_iter=10,
                              threshold_mad=2.0):
    """Iterative polynomial baseline: mask peaks, refit, repeat.

    Fits a polynomial of degree *order* to the data.  After each fit,
    points whose residual exceeds ``threshold_mad * σ_MAD`` are masked
    as "peak" regions.  The fit is repeated on the remaining points
    until the mask stabilises or *max_iter* is reached.
    """
    n_finite = len(x_finite)
    if n_finite < order + 2:
        order = max(1, n_finite - 1)

    mask = np.ones(n_finite, dtype=bool)
    bl = None

    for _ in range(max_iter):
        if mask.sum() < order + 2:
            mask = np.ones(n_finite, dtype=bool)  # fall back to full fit
        coeffs = np.polyfit(x_finite[mask], y_finite[mask], int(order))
        bl = np.polyval(coeffs, x_all)

        # residuals on the *finite* subset
        bl_finite = np.polyval(coeffs, x_finite)
        residuals = y_finite - bl_finite

        mad = np.nanmedian(np.abs(residuals - np.nanmedian(residuals)))
        noise_est = 1.4826 * mad if np.isfinite(mad) and mad > 1e-12 else np.nanstd(residuals)
        if not np.isfinite(noise_est) or noise_est <= 1e-12:
            break

        new_mask = residuals <= threshold_mad * noise_est
        if np.array_equal(new_mask, mask):
            break
        mask = new_mask

    return bl if bl is not None else np.zeros_like(x_all)


# ---------------------------------------------------------------------------
#  Reference shift
# ---------------------------------------------------------------------------

def reference_shift(ppm, intensity, current_ref_ppm, target_ref_ppm=0.0):
    """Shift ppm scale so reference peak is at target_ref_ppm.

    δ_corrected = δ - (δ_ref_current - δ_ref_target)
    """
    offset = current_ref_ppm - target_ref_ppm
    return ppm - offset, intensity


# ---------------------------------------------------------------------------
#  Normalisation
# ---------------------------------------------------------------------------

def normalise(intensity):
    """Normalise to [0, 1]."""
    y = np.asarray(intensity, dtype=float)
    y_min, y_max = np.min(y), np.max(y)
    if y_max - y_min > 1e-12:
        return (y - y_min) / (y_max - y_min)
    return y


def orient_positive_peaks(intensity):
    """Make the dominant NMR peak polarity positive."""
    y = np.asarray(intensity, dtype=float)
    if len(y) == 0:
        return y, False
    y_max = float(np.nanmax(y))
    y_min = float(np.nanmin(y))
    if abs(y_min) > 1.15 * abs(y_max):
        return -y, True
    return y, False


# ---------------------------------------------------------------------------
#  Full pipeline
# ---------------------------------------------------------------------------

def preprocess_pipeline(spectrum: NMRSpectrum, config: NMRConfig) -> NMRSpectrum:
    """Run full NMR preprocessing."""
    if not spectrum.has_data:
        return spectrum

    ppm = spectrum.ppm.copy()
    intensity = spectrum.intensity.copy()

    # 1. Left shift
    if config.left_shift_points > 0:
        ppm, intensity = left_shift(ppm, intensity, config.left_shift_points)

    # 2. Phase correction — skip for liquid spectra (already phased during
    #    FID→FFT conversion in the loader) and for pre-processed spectrum
    #    formats (table/bruker_pdata).  Solid JEOL or raw FID-derived solid
    #    data may still benefit from automatic phasing.
    fmt = spectrum.metadata.get("format", "")
    skip_phase = (config.sample_state == "liquid"
                  or fmt in ("table", "bruker_pdata"))
    if config.phase_correction and not skip_phase:
        intensity = auto_phase(intensity)

    # 2b. Some vendor processed spectra are stored with inverted phase.
    intensity, inverted = orient_positive_peaks(intensity)
    if inverted:
        spectrum.metadata['polarity_inverted'] = True

    # 3. Baseline correction
    intensity, bg = correct_baseline(ppm, intensity,
                                      method=config.baseline_method,
                                      order=config.baseline_order)
    spectrum.metadata['baseline'] = bg

    # 4. Normalise
    intensity = normalise(intensity)

    spectrum.ppm = ppm
    spectrum.intensity = intensity
    return spectrum
