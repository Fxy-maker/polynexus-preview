"""DSC data preprocessing module.

Pipeline: calibration → baseline correction → smoothing → normalisation.

Baseline correction is the most critical step.  Supported methods:
    - 'linear':          straight line between user-specified limits
    - 'polynomial':      polynomial fit to baseline region
    - 'spline':          cubic spline interpolation through anchor points
    - 'blank_subtract':  subtract a separate blank-pan measurement
    - 'tangential':      tangential sigmoid baseline (best for melting peaks)
    - 'auto':            auto-detect baseline region and use linear/sigmoid

Temperature / enthalpy / heat-capacity calibration from standard references.
"""
import logging
logger = logging.getLogger(__name__)


import numpy as np
from scipy import interpolate, signal, optimize
from typing import Optional, Tuple, List, Callable

from .io import DSCScan
from .config import DSCConfig


def _safe_derivative(y: np.ndarray, x: np.ndarray) -> np.ndarray:
    """dy/dx with protection against repeated x values."""
    y_arr = np.asarray(y, dtype=float)
    x_arr = np.asarray(x, dtype=float)
    if len(y_arr) < 2 or len(y_arr) != len(x_arr):
        return np.zeros_like(y_arr)
    dx = np.gradient(x_arr)
    dy = np.gradient(y_arr)
    step = np.nanmedian(np.abs(np.diff(x_arr)))
    if not np.isfinite(step) or step <= 1e-12:
        step = 1.0
    dx_safe = np.where(np.abs(dx) < 1e-12, np.sign(dx) * step, dx)
    dx_safe = np.where(np.abs(dx_safe) < 1e-12, step, dx_safe)
    out = dy / dx_safe
    return np.where(np.isfinite(out), out, 0.0)


# ---------------------------------------------------------------------------
#  Temperature calibration
# ---------------------------------------------------------------------------

def calibrate_temperature(T: np.ndarray, a: float = 1.0, b: float = 0.0) -> np.ndarray:
    """Apply linear temperature calibration: T_true = a * T + b."""
    return a * np.asarray(T, dtype=float) + b


def calibrate_from_standards(T_measured: np.ndarray,
                             standards: List[Tuple[float, float]],
                             ) -> Tuple[np.ndarray, float, float]:
    """Fit linear calibration from standard melting points.

    Parameters
    ----------
    T_measured : ndarray
        Measured temperatures (at least 2 points).
    standards : list of (T_true, T_measured)

    Returns
    -------
    T_calibrated, a, b
    """
    T_true = np.array([s[0] for s in standards])
    T_meas = np.array([s[1] for s in standards])
    coeffs = np.polyfit(T_meas, T_true, 1)
    a, b = coeffs[0], coeffs[1]
    return a * T_measured + b, a, b


# ---------------------------------------------------------------------------
#  Enthalpy calibration
# ---------------------------------------------------------------------------

def calibrate_enthalpy(HF: np.ndarray, K: float = 1.0) -> np.ndarray:
    """Apply calorimetric constant: HF_corr = HF * K.

    K = DH_ref / DH_measured  (indium: 28.62 J/g).
    """
    return np.asarray(HF, dtype=float) * K


# ---------------------------------------------------------------------------
#  Heat capacity calibration
# ---------------------------------------------------------------------------

def calibrate_heat_capacity(HF: np.ndarray, T: np.ndarray,
                            rate_K_per_min: float,
                            K_Cp: Optional[Callable] = None,
                            ) -> np.ndarray:
    """Convert heat flow to absolute heat capacity.

    Cp(T) = HF(T) / beta * K_Cp(T)

    If K_Cp is None, assumes perfect calibration (K_Cp = 1).
    """
    beta_K_per_s = rate_K_per_min / 60.0  # convert to K/s
    if beta_K_per_s == 0:
        return np.zeros_like(HF)

    Cp = HF / beta_K_per_s  # mJ/K → mJ/(K*s) = mW
    if K_Cp is not None:
        Cp = Cp * K_Cp(T)
    return Cp


# ---------------------------------------------------------------------------
#  Baseline correction  (the core of DSC preprocessing)
# ---------------------------------------------------------------------------

def _detect_baseline_limits(T: np.ndarray, HF: np.ndarray,
                            method: str = 'auto',
                            ) -> Tuple[float, float]:
    """Auto-detect suitable baseline region limits.

    Strategy: find the first and last points where the derivative is small
    (i.e. outside transition regions).
    """
    dHF = _safe_derivative(HF, T)
    noise = np.std(dHF)
    quiet = np.abs(dHF) < 2 * noise

    # Find the first and last "quiet" segments of sufficient length
    min_len = max(5, len(T) // 10)

    # From start
    start_idx = 0
    run = 0
    for i in range(len(quiet)):
        if quiet[i]:
            run += 1
            if run >= min_len:
                start_idx = i - min_len // 2
                break
        else:
            run = 0

    # From end
    end_idx = len(T) - 1
    run = 0
    for i in range(len(quiet) - 1, -1, -1):
        if quiet[i]:
            run += 1
            if run >= min_len:
                end_idx = i + min_len // 2
                break
        else:
            run = 0

    start_idx = max(0, start_idx)
    end_idx = min(len(T) - 1, end_idx)
    return T[start_idx], T[end_idx]


def baseline_linear(T: np.ndarray, HF: np.ndarray,
                    limits: Optional[Tuple[float, float]] = None,
                    ) -> np.ndarray:
    """Linear baseline between two temperature limits."""
    if limits is None:
        limits = _detect_baseline_limits(T, HF)
    T1, T2 = limits

    # Find indices
    i1 = np.argmin(np.abs(T - T1))
    i2 = np.argmin(np.abs(T - T2))
    if i1 == i2:
        return np.zeros_like(HF)

    HF1, HF2 = HF[i1], HF[i2]
    slope = (HF2 - HF1) / (T[i2] - T[i1])
    baseline = HF1 + slope * (T - T1)
    return baseline


def baseline_polynomial(T: np.ndarray, HF: np.ndarray,
                        limits: Optional[Tuple[float, float]] = None,
                        order: int = 3,
                        ) -> np.ndarray:
    """Polynomial baseline fit to the baseline region."""
    if limits is None:
        limits = _detect_baseline_limits(T, HF)
    T1, T2 = limits

    # Use points outside transition region
    mask = (T < T1 - 5) | (T > T2 + 5)
    if np.sum(mask) < order + 2:
        mask = np.ones_like(T, dtype=bool)  # fallback: use all

    coeffs = np.polyfit(T[mask], HF[mask], order)
    return np.polyval(coeffs, T)


def baseline_spline(T: np.ndarray, HF: np.ndarray,
                    n_anchors: int = 5,
                    limits: Optional[Tuple[float, float]] = None,
                    ) -> np.ndarray:
    """Cubic spline baseline through anchor points in quiet regions."""
    if limits is None:
        limits = _detect_baseline_limits(T, HF)
    T1, T2 = limits

    # Select anchor points in quiet regions
    dHF = _safe_derivative(HF, T)
    quiet = np.abs(dHF) < np.std(dHF)

    # Evenly spaced anchors
    anchor_idx = np.linspace(0, len(T) - 1, n_anchors + 2, dtype=int)[1:-1]
    # Filter to quiet regions
    quiet_idx = np.where(quiet)[0]
    if len(quiet_idx) < n_anchors:
        # Not enough quiet points; use linear
        return baseline_linear(T, HF, limits)

    anchors = []
    for ai in anchor_idx:
        # Nearest quiet point
        dist = np.abs(quiet_idx - ai)
        qi = quiet_idx[np.argmin(dist)]
        anchors.append((T[qi], HF[qi]))

    anchors_arr = np.array(anchors)
    spl = interpolate.CubicSpline(anchors_arr[:, 0], anchors_arr[:, 1],
                                   extrapolate=True)
    return spl(T)


def baseline_blank_subtract(HF_sample: np.ndarray, HF_blank: np.ndarray,
                            ) -> np.ndarray:
    """Subtract a separately measured blank-pan baseline."""
    blank = np.asarray(HF_blank, dtype=float)
    if len(blank) != len(HF_sample):
        # Resample blank to match sample
        x_old = np.linspace(0, 1, len(blank))
        x_new = np.linspace(0, 1, len(HF_sample))
        blank = np.interp(x_new, x_old, blank)
    return blank


def baseline_tangential(T: np.ndarray, HF: np.ndarray,
                        peak_limits: Optional[Tuple[float, float]] = None,
                        ) -> np.ndarray:
    """Tangential sigmoid baseline — best for melting endotherms.

    Fits an asymmetric sigmoid through the onset and end of the transition,
    producing a smooth S-shaped baseline that connects the pre- and
    post-melt heat capacity levels.
    """
    if peak_limits is None:
        peak_limits = _detect_baseline_limits(T, HF)

    T1, T2 = peak_limits
    i1 = np.argmin(np.abs(T - T1))
    i2 = np.argmin(np.abs(T - T2))

    # Fit a sigmoid:  y = a + b / (1 + exp((c - T) / d))
    def sigmoid(x, a, b, c, d):
        return a + b / (1.0 + np.exp((c - x) / max(abs(d), 1e-6)))

    try:
        # Initial guess
        a0 = HF[:i1].mean() if i1 > 0 else HF[0]
        b0 = HF[i2:].mean() - a0 if i2 < len(HF) - 1 else HF[-1] - a0
        c0 = (T1 + T2) / 2
        d0 = (T2 - T1) / 4
        popt, _ = optimize.curve_fit(sigmoid, T, HF,
                                     p0=[a0, b0, c0, d0],
                                     maxfev=5000)
        return sigmoid(T, *popt)
    except Exception:
        # Fallback to linear
        return baseline_linear(T, HF, peak_limits)
        logger.warning("异常已处理", exc_info=True)


def correct_baseline(T: np.ndarray, HF: np.ndarray,
                     method: str = 'auto',
                     limits: Optional[Tuple[float, float]] = None,
                     HF_blank: Optional[np.ndarray] = None,
                     ) -> Tuple[np.ndarray, np.ndarray]:
    """Apply baseline correction and return (HF_corrected, baseline).

    Parameters
    ----------
    method : str
        'linear', 'polynomial', 'spline', 'blank_subtract',
        'tangential', 'auto'.
    limits : (T_start, T_end), optional
    HF_blank : ndarray, optional
        Blank measurement for 'blank_subtract' method.

    Returns
    -------
    HF_corrected, baseline
    """
    T = np.asarray(T, dtype=float)
    HF = np.asarray(HF, dtype=float)

    n = len(T)

    if method == 'blank_subtract' and HF_blank is not None:
        bl = baseline_blank_subtract(HF, HF_blank)
    elif method == 'linear':
        bl = baseline_linear(T, HF, limits)
    elif method == 'polynomial':
        bl = baseline_polynomial(T, HF, limits)
    elif method == 'spline':
        bl = baseline_spline(T, HF, limits=limits)
    elif method == 'tangential':
        bl = baseline_tangential(T, HF, limits)
    elif method == 'auto':
        # Auto: try tangential first, fall back to linear
        try:
            bl = baseline_tangential(T, HF, limits)
        except Exception:
            bl = baseline_linear(T, HF, limits)
            logger.warning("异常已处理", exc_info=True)
    else:
        bl = np.zeros(n)

    return HF - bl, bl


# ---------------------------------------------------------------------------
#  Smoothing
# ---------------------------------------------------------------------------

def smooth_savgol(data: np.ndarray, window: int = 11, order: int = 3,
                  ) -> np.ndarray:
    """Savitzky-Golay filter."""
    if window % 2 == 0:
        window += 1
    if window < 3:
        return data
    if len(data) < window:
        return data
    order = min(order, window - 1)
    return signal.savgol_filter(data, window, order)


def smooth_moving_average(data: np.ndarray, window: int = 5,
                          ) -> np.ndarray:
    """Simple moving average."""
    if window < 2 or len(data) < window:
        return data
    kernel = np.ones(window) / window
    return np.convolve(data, kernel, mode='same')


def smooth_profile(data: np.ndarray, method: str = 'savgol',
                   window: int = 11, order: int = 3,
                   ) -> np.ndarray:
    """Apply smoothing to DSC heat flow data."""
    if method == 'none':
        return np.asarray(data)
    elif method == 'savgol':
        return smooth_savgol(data, window, order)
    elif method == 'moving_average':
        return smooth_moving_average(data, window)
    else:
        return np.asarray(data)


# ---------------------------------------------------------------------------
#  Rate normalisation
# ---------------------------------------------------------------------------

def normalise_rate(HF_Wg: np.ndarray, rate_K_per_min: float,
                   reference_rate: float = 10.0,
                   ) -> np.ndarray:
    """Normalise heat flow to a reference heating rate.

    HF_norm = HF * (ref_rate / actual_rate)

    Useful for comparing data acquired at different rates.
    """
    if abs(rate_K_per_min) < 0.01:
        return np.asarray(HF_Wg)
    return np.asarray(HF_Wg) * (reference_rate / abs(rate_K_per_min))


# ---------------------------------------------------------------------------
#  Full preprocessing pipeline
# ---------------------------------------------------------------------------

def preprocess_pipeline(scan: DSCScan, config: DSCConfig,
                        HF_blank: Optional[np.ndarray] = None,
                        ) -> DSCScan:
    """Run the full DSC preprocessing pipeline on a scan.

    Steps:
        1. Temperature calibration
        2. Enthalpy calibration
        3. Baseline correction
        4. Smoothing
        5. Rate normalisation (optional)

    Parameters
    ----------
    scan : DSCScan
        Raw scan data.
    config : DSCConfig
        Configuration with method choices and parameters.
    HF_blank : ndarray, optional
        Blank-pan measurement for blank_subtract baseline method.

    Returns
    -------
    DSCScan with corrected T, HF, and smoothed data.
    """
    T = scan.T_C.copy()
    HF = scan.HF_Wg.copy()

    # 1. Temperature calibration
    cal = config.temperature_calibration
    T = calibrate_temperature(T, cal.get('a', 1.0), cal.get('b', 0.0))

    # 2. Enthalpy calibration
    HF = calibrate_enthalpy(HF, config.enthalpy_calibration)

    # 3. Baseline correction (skip if data already baseline-corrected)
    # Detect whether the signal already sits on a flat zero baseline:
    # if the mean of the first and last 10 % of the scan is near zero
    # the data was pre-corrected by the instrument software.
    _n10 = max(10, len(T) // 10)
    _hf_head = HF[:_n10]
    _hf_tail = HF[-_n10:]
    _hf_range = float(np.ptp(HF))
    _needs_bl = True
    if _hf_range > 1e-6:
        _head_offset = abs(float(np.mean(_hf_head))) / _hf_range
        _tail_offset = abs(float(np.mean(_hf_tail))) / _hf_range
        if _head_offset < 0.15 and _tail_offset < 0.15:
            _needs_bl = False

    if _needs_bl:
        HF, baseline = correct_baseline(
            T, HF,
            method=config.baseline_corr,
            limits=config.baseline_limits,
            HF_blank=HF_blank,
        )
    else:
        baseline = np.zeros_like(T)

    # Store baseline for later reference
    scan.metadata['baseline'] = baseline
    scan.metadata['HF_pre_smooth'] = HF.copy()

    # 4. Smoothing
    if config.smooth_method != 'none':
        HF = smooth_profile(HF, method=config.smooth_method,
                            window=config.smooth_window,
                            order=config.smooth_order)

    # Store processed arrays
    scan.T_C = T
    scan.HF_Wg = HF
    scan.HF_mW = HF * scan.mass_mg  # reverse-normalise

    return scan
