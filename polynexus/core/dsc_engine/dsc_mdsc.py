"""Modulated DSC analysis module (D4B).

Deconvolves MDSC signals into reversing (heat capacity) and
non-reversing (kinetic) components using Fourier transform.

MDSC principle:
    T(t) = T0 + beta*t + A_T * sin(omega*t)
    HF(t) = HF_rev(t) + HF_nonrev(t)

    The reversing component is in-phase with the temperature modulation
    and represents the sample heat capacity:  Cp = HF_rev_amp / (A_T * omega)

    The non-reversing component captures kinetic events (crystallisation,
    curing, enthalpic relaxation) that do not follow the modulation.
"""

import numpy as np
from scipy import signal
from typing import Dict, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class MDSCResult:
    """MDSC deconvolution result."""
    label: str = ""
    # Raw data
    T: np.ndarray = field(default_factory=lambda: np.array([]))
    t: np.ndarray = field(default_factory=lambda: np.array([]))
    HF_total: np.ndarray = field(default_factory=lambda: np.array([]))

    # Deconvolved
    HF_reversing: np.ndarray = field(default_factory=lambda: np.array([]))
    HF_nonreversing: np.ndarray = field(default_factory=lambda: np.array([]))
    Cp_JgK: np.ndarray = field(default_factory=lambda: np.array([]))

    # Modulation parameters
    amplitude_K: float = 1.0
    period_s: float = 60.0
    underlying_rate: float = 2.0  # K/min

    # Phase lag
    phase_lag_deg: float = 0.0

    @property
    def parameters(self) -> dict:
        return {
            'amplitude_K': self.amplitude_K,
            'period_s': self.period_s,
            'underlying_rate_K_min': self.underlying_rate,
            'phase_lag_deg': self.phase_lag_deg,
            'Cp_avg_JgK': float(np.mean(self.Cp_JgK)) if len(self.Cp_JgK) > 0 else np.nan,
        }


def deconvolve_mdsc(T, HF_total, time_min, period_s=60.0, amplitude_K=1.0):
    """Deconvolve MDSC data into reversing and non-reversing components.

    Uses a sliding-window discrete Fourier transform (DFT) at the modulation
    frequency. This is the standard approach (TA Instruments "Fourier" method).

    Parameters
    ----------
    T : ndarray
        Temperature in Celsius.
    HF_total : ndarray
        Total heat flow in W/g (exo-up convention).
    time_min : ndarray
        Time in minutes.
    period_s : float
        Modulation period in seconds.
    amplitude_K : float
        Temperature modulation amplitude in Kelvin.

    Returns
    -------
    MDSCResult
    """
    result = MDSCResult(
        T=T, t=time_min, HF_total=HF_total,
        period_s=period_s, amplitude_K=amplitude_K,
    )

    if len(T) < 100 or period_s <= 0:
        return result

    # Sampling interval
    dt_min = np.mean(np.diff(time_min))
    dt_s = dt_min * 60.0

    # Number of points per modulation period
    points_per_period = int(period_s / dt_s)
    if points_per_period < 4:
        return result

    # Use at least 2 full periods for the sliding window
    window_points = 2 * points_per_period
    if window_points > len(T) // 2:
        window_points = max(points_per_period, len(T) // 4)

    n = len(T)
    HF_rev = np.zeros(n)
    HF_nonrev = np.zeros(n)
    Cp = np.zeros(n)
    phase_lags = []

    # Underlying heating rate (K/s)
    beta_K_s = np.polyfit(time_min, T, 1)[0] / 60.0  # K/s

    # Sliding window DFT
    half = window_points // 2

    for i in range(half, n - half):
        window_T = T[i - half:i + half]
        window_HF = HF_total[i - half:i + half]
        window_t = time_min[i - half:i + half] * 60.0  # seconds

        # Modulation frequency
        omega = 2.0 * np.pi / period_s

        # DFT at modulation frequency (single-frequency analysis)
        # Use the in-phase (sine) and quadrature (cosine) components
        n_pts = len(window_t)
        t_rel = window_t - window_t[0]

        # Compute Fourier coefficients at omega
        sin_sum = np.sum(window_HF * np.sin(omega * t_rel))
        cos_sum = np.sum(window_HF * np.cos(omega * t_rel))

        # Amplitude and phase of heat flow response
        HF_amp = (2.0 / n_pts) * np.sqrt(sin_sum**2 + cos_sum**2)

        # Phase lag of HF relative to temperature modulation
        phase = np.arctan2(cos_sum, sin_sum)
        phase_lags.append(np.degrees(phase))

        # Reversing heat flow = in-phase component
        HF_rev_amp = (2.0 / n_pts) * sin_sum

        # Heat capacity from reversing amplitude
        # Cp = HF_rev_amp / (A_T * omega)  [J/(g*K)]
        Cp_val = HF_rev_amp / (amplitude_K * omega) if amplitude_K * omega > 0 else 0

        HF_rev[i] = HF_rev_amp
        HF_nonrev[i] = HF_total[i] - HF_rev_amp
        Cp[i] = Cp_val

    # Fill ends with nearest values
    HF_rev[:half] = HF_rev[half]
    HF_rev[-half:] = HF_rev[-half - 1]
    HF_nonrev[:half] = HF_nonrev[half]
    HF_nonrev[-half:] = HF_nonrev[-half - 1]
    Cp[:half] = Cp[half]
    Cp[-half:] = Cp[-half - 1]

    result.HF_reversing = HF_rev
    result.HF_nonreversing = HF_nonrev
    result.Cp_JgK = Cp
    result.phase_lag_deg = float(np.mean(phase_lags)) if phase_lags else 0.0
    result.underlying_rate = abs(beta_K_s) * 60.0

    return result


def deconvolve_mdsc_simple(T, HF_total, time_min, period_s=60.0):
    """Simplified MDSC deconvolution: moving-average separation.

    The total signal is the sum of a slowly-varying (reversing) component
    and a rapidly-changing (non-reversing) component.

    Reversing ≈ low-pass filtered HF_total with cutoff just below modulation freq
    Non-reversing = HF_total - reversing

    This method requires no FFT and is more robust for noisy data.
    """
    dt_min = np.mean(np.diff(time_min))
    dt_s = dt_min * 60.0
    points_per_period = int(period_s / dt_s)
    window = max(points_per_period, 5)

    # Smoothing over ~1 period gives the reversing (averaged) signal
    HF_rev = _moving_average(HF_total, window)
    HF_nonrev = HF_total - HF_rev

    # Cp estimate: HF_rev / beta_underlying
    beta = np.abs(np.polyfit(time_min, T, 1)[0])
    Cp = HF_rev / beta if beta > 0 else np.zeros_like(HF_rev)

    return MDSCResult(
        T=T, t=time_min, HF_total=HF_total,
        HF_reversing=HF_rev, HF_nonreversing=HF_nonrev,
        Cp_JgK=Cp, period_s=period_s,
        phase_lag_deg=0.0,
    )


def _detrend_linear(y, x):
    """Remove linear trend."""
    coeffs = np.polyfit(x, y, 1)
    trend = np.polyval(coeffs, x)
    return y - trend


def _moving_average(data, window):
    """Simple moving average."""
    if window < 2:
        return np.asarray(data)
    kernel = np.ones(window) / window
    return np.convolve(data, kernel, mode='same')


def analyse_glass_transition_mdsc(mdsc_result):
    """Extract Tg from MDSC reversing Cp signal.

    The step change in reversing Cp gives the true thermodynamic Tg,
    free from enthalpic relaxation (which appears in non-reversing).
    """
    T = mdsc_result.T
    Cp = mdsc_result.Cp_JgK

    if len(T) < 20 or np.all(Cp == 0):
        return {'Tg_C': np.nan, 'DCp_JgK': np.nan}

    dCp = np.gradient(Cp, np.gradient(T))
    peak_idx = np.argmax(dCp)

    # Half-height method on Cp step
    left = max(0, peak_idx - 40)
    right = min(len(T) - 1, peak_idx + 40)

    pre_fit = np.polyfit(T[left:max(1, peak_idx - 10)],
                         Cp[left:max(1, peak_idx - 10)], 1)
    post_fit = np.polyfit(T[min(len(T) - 1, peak_idx + 10):right],
                          Cp[min(len(T) - 1, peak_idx + 10):right], 1)

    pre_line = np.polyval(pre_fit, T)
    post_line = np.polyval(post_fit, T)
    mid = (np.polyval(pre_fit, T[peak_idx]) + np.polyval(post_fit, T[peak_idx])) / 2

    # Find crossing
    diff = Cp - mid
    crossings = np.where(np.diff(np.sign(diff)))[0]
    if len(crossings) > 0:
        best = crossings[np.argmin(np.abs(crossings - peak_idx))]
        Tg = float(T[best])
    else:
        Tg = float(T[peak_idx])

    DCp = float(post_fit[0] - pre_fit[0])

    return {'Tg_C': Tg, 'DCp_JgK': DCp}


def detect_enthalpic_relaxation(mdsc_result, threshold=0.05):
    """Detect enthalpic relaxation peak in non-reversing signal.

    Enthalpic relaxation appears as an endothermic peak in the
    non-reversing signal near Tg, which is absent in the reversing signal.
    """
    T = mdsc_result.T
    HF_nonrev = mdsc_result.HF_nonreversing
    HF_rev = mdsc_result.HF_reversing

    # Look for negative peak in non-reversing (endothermic with exo-up)
    noise = np.std(HF_nonrev)
    peaks, props = signal.find_peaks(-HF_nonrev, prominence=noise * 2)

    relaxations = []
    for idx in peaks:
        relaxations.append({
            'T_C': float(T[idx]),
            'enthalpy_Jg': float(abs(np.trapezoid(
                HF_nonrev[max(0,idx-20):min(len(T),idx+20)],
                T[max(0,idx-20):min(len(T),idx+20)]
            ))),
            'peak_height_Wg': float(abs(HF_nonrev[idx])),
        })

    return relaxations