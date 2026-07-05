"""WAXS core analysis module.

Computes:
    - Peak detection & multi-peak fitting (Voigt/Pseudo-Voigt/Gaussian/Lorentzian)
    - Amorphous halo subtraction
    - Crystallinity (peak area ratio)
    - Crystallite size (Scherrer, Williamson-Hall, Warren-Averbach)
    - Crystal system identification from peak positions
    - Unit cell parameters (cubic, tetragonal, orthorhombic)
"""
import logging
logger = logging.getLogger(__name__)


import numpy as np
from scipy import signal, optimize, interpolate
from scipy.ndimage import uniform_filter1d
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

from .io import WAXSScan
from .config import WAXSConfig


# ---------------------------------------------------------------------------
#  Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class WAXSResult:
    """Container for WAXS analysis results."""
    label: str = ""

    # Crystallinity
    Xc_pct: float = np.nan
    Xc_method: str = ""

    # Peak information
    n_peaks: int = 0
    peaks: List[Dict[str, Any]] = field(default_factory=list)

    # Crystallite size
    D_Scherrer_nm: float = np.nan
    D_uncertainty_nm: float = np.nan
    instrument_broadening_applied: bool = False
    D_WH_nm: float = np.nan        # Williamson-Hall size
    epsilon_WH_pct: float = np.nan  # Williamson-Hall strain (%)

    # Crystal system
    crystal_system: str = ""
    unit_cell_params: Dict[str, float] = field(default_factory=dict)

    # Amorphous halo
    I_amorphous: np.ndarray = field(default_factory=lambda: np.array([]))
    I_crystalline: np.ndarray = field(default_factory=lambda: np.array([]))

    # Fit quality
    r_squared: float = np.nan

    # Raw data references
    two_theta: np.ndarray = field(default_factory=lambda: np.array([]))
    I: np.ndarray = field(default_factory=lambda: np.array([]))
    I_fit: np.ndarray = field(default_factory=lambda: np.array([]))
    sector_used: str = "full"  # "full", "meridional", or "equatorial"

    @property
    def parameters(self) -> Dict[str, Any]:
        p = {
            'Xc_pct': self.Xc_pct, 'Xc_method': self.Xc_method,
            'n_peaks': self.n_peaks,
            'D_Scherrer_nm': self.D_Scherrer_nm,
            'D_uncertainty_nm': self.D_uncertainty_nm,
            'instrument_broadening_applied': self.instrument_broadening_applied,
            'D_WH_nm': self.D_WH_nm,
            'epsilon_WH_pct': self.epsilon_WH_pct,
            'crystal_system': self.crystal_system,
            'r_squared': self.r_squared,
        }
        for i, pk in enumerate(self.peaks):
            p[f'peak_{i}_2theta'] = pk.get('two_theta', np.nan)
            p[f'peak_{i}_d_A'] = pk.get('d_spacing_A', np.nan)
            p[f'peak_{i}_FWHM'] = pk.get('fwhm_deg', np.nan)
            p[f'peak_{i}_hkl'] = pk.get('hkl', '')
            p[f'peak_{i}_area'] = pk.get('area', np.nan)
        return {k: v for k, v in p.items()
                if not (isinstance(v, float) and np.isnan(v))}


# ---------------------------------------------------------------------------
#  Peak shape functions
# ---------------------------------------------------------------------------

def gaussian(x, amp, mu, sigma):
    return amp * np.exp(-0.5 * ((x - mu) / sigma) ** 2)

def lorentzian(x, amp, mu, gamma):
    return amp * gamma ** 2 / ((x - mu) ** 2 + gamma ** 2)

def pseudo_voigt(x, amp, mu, sigma, eta):
    """Pseudo-Voigt: η·Lorentzian + (1-η)·Gaussian."""
    g = gaussian(x, 1.0, mu, sigma)
    l = lorentzian(x, 1.0, mu, sigma)  # use sigma as gamma approx
    return amp * (eta * l + (1.0 - eta) * g)

def pearson_vii(x, amp, mu, sigma, m):
    """Pearson VII function."""
    return amp / (1.0 + ((x - mu) / sigma) ** 2) ** m


PEAK_FUNCTIONS = {
    'gaussian':     (gaussian, 3),
    'lorentzian':   (lorentzian, 3),
    'pseudo_voigt': (pseudo_voigt, 4),
    'pearson_vii':  (pearson_vii, 4),
}


# ---------------------------------------------------------------------------
#  Peak detection
# ---------------------------------------------------------------------------

def detect_peaks(two_theta: np.ndarray, I: np.ndarray,
                 height_frac: float = 0.05,
                 distance: float = 0.5,
                 max_peaks: int = 8,
                 ) -> List[Dict[str, Any]]:
    """Detect crystalline peaks in a WAXS profile.

    Parameters
    ----------
    height_frac : float
        Minimum peak height as fraction of maximum intensity.
    distance : float
        Minimum distance between peaks in °2θ.
    max_peaks : int
        Maximum number of peaks to return (keeps the most prominent ones).

    Returns
    -------
    List of dicts with keys: index, two_theta, height, prominence
    """
    if len(I) < 10:
        return []

    # Smooth derivative for peak detection
    dI = uniform_filter1d(np.gradient(I), size=3)
    noise = np.std(dI)

    min_height = height_frac * np.max(I)
    peak_indices, props = signal.find_peaks(
        I, height=min_height, prominence=max(noise * 5, min_height * 0.5),
        distance=int(distance / np.mean(np.diff(two_theta))),
    )

    peaks = []
    for i, idx in enumerate(peak_indices):
        peaks.append({
            'index': i,
            'idx': int(idx),
            'two_theta': float(two_theta[idx]),
            'height': float(I[idx]),
            'prominence': float(props['prominences'][i]) if 'prominences' in props else 0.0,
        })

    # Cap to max_peaks: keep the most prominent ones
    if len(peaks) > max_peaks:
        peaks.sort(key=lambda p: p['prominence'], reverse=True)
        peaks = peaks[:max_peaks]
        peaks.sort(key=lambda p: p['two_theta'])  # re-sort by 2θ
        for i, p in enumerate(peaks):
            p['index'] = i

    return peaks


# ---------------------------------------------------------------------------
#  Multi-peak fitting
# ---------------------------------------------------------------------------

def fit_peaks(two_theta: np.ndarray, I: np.ndarray,
              peaks: List[Dict[str, Any]],
              peak_type: str = 'pseudo_voigt',
              fit_baseline: bool = True,
              ) -> Tuple[List[Dict[str, Any]], float, np.ndarray, np.ndarray]:
    """Fit multiple peaks simultaneously with baseline.

    Returns (fitted_peaks, r_squared, I_fitted, baseline).
    """
    if not peaks or len(two_theta) < 10:
        return [], np.nan, np.array([]), np.array([])

    x = np.asarray(two_theta, dtype=float)
    y = np.asarray(I, dtype=float)
    x_orig = x.copy()  # save original for interpolation back
    # Down-sample if too many points (prevents curve_fit timeout)
    if len(x) > 800:
        step = max(1, len(x) // 1000)
        x, y = x[::step].copy(), y[::step].copy()

    peak_func, n_params_per_peak = PEAK_FUNCTIONS.get(
        peak_type, PEAK_FUNCTIONS['pseudo_voigt'])

    # Baseline: 2nd order polynomial
    n_base = 3 if fit_baseline else 0  # a*x^2 + b*x + c
    n_total = n_base + n_params_per_peak * len(peaks)

    def model(x, *params):
        y_fit = np.zeros_like(x)
        idx = 0
        if fit_baseline:
            y_fit = params[0] * x ** 2 + params[1] * x + params[2]
            idx = 3
        for _ in range(len(peaks)):
            args = [x] + list(params[idx:idx + n_params_per_peak])
            y_fit += peak_func(*args)
            idx += n_params_per_peak
        return y_fit

    # Initial guesses
    p0 = []
    if fit_baseline:
        # Estimate baseline from low-intensity regions
        baseline_mask = np.ones(len(y), dtype=bool)
        for pk in peaks:
            idx_pk = pk.get('idx', int(np.argmin(np.abs(x - pk['two_theta']))))
            baseline_mask[max(0, idx_pk - 10):min(len(y), idx_pk + 10)] = False
        if np.sum(baseline_mask) > 10:
            coeffs = np.polyfit(x[baseline_mask], y[baseline_mask], 2)
            p0.extend(coeffs)
        else:
            p0.extend([0.0, 0.0, np.min(y)])

    for pk in peaks:
        idx = pk.get('idx', int(np.argmin(np.abs(x - pk['two_theta']))))
        tth = pk['two_theta']
        amp = max(pk['height'], 0.01)
        sigma = 0.5  # typical WAXS peak width ~0.5°
        p0.append(amp)
        p0.append(tth)
        p0.append(sigma)
        if peak_type in ('pseudo_voigt',):
            p0.append(0.5)  # η
        elif peak_type == 'pearson_vii':
            p0.append(1.5)  # m

    p0 = np.array(p0)

    try:
        lower, upper = _build_bounds(len(peaks), n_base, n_params_per_peak, x, y)
        def residual(params):
            return model(x, *params) - y
        from scipy.optimize import least_squares
        res = least_squares(residual, p0, bounds=(lower, upper),
                           method='trf', max_nfev=2000, ftol=1e-2, xtol=1e-2)
        popt = res.x
    except Exception:
        popt = p0

    # Extract fitted peaks
    fitted_peaks = []
    idx = n_base
    for i in range(len(peaks)):
        pars = popt[idx:idx + n_params_per_peak]
        amp_f, mu_f, sigma_f = pars[0], pars[1], abs(pars[2])

        # FWHM
        if peak_type == 'gaussian':
            fwhm = 2.355 * sigma_f
        elif peak_type == 'lorentzian':
            fwhm = 2.0 * sigma_f
        else:
            fwhm = 2.355 * sigma_f  # approximate

        # Area under peak
        if peak_type == 'gaussian':
            area = amp_f * sigma_f * np.sqrt(2 * np.pi)
        else:
            area = amp_f * fwhm * 0.94  # approximate

        # d-spacing
        wavelength = 1.5406  # Cu Kα default
        d = wavelength / (2.0 * np.sin(np.radians(mu_f / 2.0))) if mu_f > 0 else np.nan

        fitted_peaks.append({
            'index': i,
            'two_theta': float(mu_f),
            'd_spacing_A': float(d),
            'height': float(amp_f),
            'fwhm_deg': float(fwhm),
            'area': float(area),
            'eta': float(pars[3]) if len(pars) > 3 else 0.5,
        })
        idx += n_params_per_peak

    # Fit quality
    y_pred = model(x, *popt)
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0

    # Baseline
    if fit_baseline:
        baseline = popt[0] * x ** 2 + popt[1] * x + popt[2]
    else:
        baseline = np.zeros_like(x)

    # Interpolate back to original grid if downsampled
    if len(x_orig) != len(y_pred):
        y_pred = np.interp(x_orig, x, y_pred)
        baseline = np.interp(x_orig, x, baseline)
    return fitted_peaks, float(r2), y_pred, baseline


def _build_bounds(n_peaks, n_base, npp, x, y):
    """Build parameter bounds for curve_fit."""
    lower, upper = [], []
    if n_base > 0:
        lower.extend([-np.inf, -np.inf, 0])
        upper.extend([np.inf, np.inf, np.max(y)])
    x_range = x[-1] - x[0]
    for _ in range(n_peaks):
        lower.extend([0, x[0], 0.05])
        upper.extend([np.max(y) * 2, x[-1], x_range / 2])
        if npp > 3:
            lower.append(0.0)
            upper.append(1.0)
    return (lower, upper)


def _fit_peaks_with_halo(x, y, peaks, halo_indices=None, peak_type='pseudo_voigt'):
    """Fit peaks with halo peaks — halo sigma constrained to 5-25 deg.
    halo_indices: list of int (or single int), indices into `peaks` that are amorphous halos.
    """
    peak_func, npp = PEAK_FUNCTIONS.get(peak_type, PEAK_FUNCTIONS['pseudo_voigt'])
    n_base = 3

    # Normalise halo_indices to a set for O(1) lookup
    if halo_indices is None:
        halo_indices = set()
    elif isinstance(halo_indices, (int, float)):
        halo_indices = {int(halo_indices)}
    else:
        halo_indices = set(halo_indices)

    # Save original grid for interpolation back
    x_orig = x.copy()
    # Down-sample large arrays to prevent least_squares timeout
    if len(x) > 800:
        step = max(1, len(x) // 1000)
        x = x[::step].copy()
        y = y[::step].copy()

    n_total = n_base + npp * len(peaks)

    def model(xx, *params):
        yy = np.zeros_like(xx)
        idx_p = 0
        yy = params[0] * xx**2 + params[1] * xx + params[2]
        idx_p = 3
        for _ in range(len(peaks)):
            yy += peak_func(xx, *params[idx_p:idx_p + npp])
            idx_p += npp
        return yy

    # Initial guesses
    p0 = []
    # Baseline from low-intensity regions
    mask = np.ones(len(y), dtype=bool)
    for pk in peaks:
        idx_pk = pk.get('idx', int(np.argmin(np.abs(x - pk['two_theta']))))
        mask[max(0, idx_pk - 10):min(len(y), idx_pk + 10)] = False
    if mask.sum() > 10:
        coeffs = np.polyfit(x[mask], y[mask], 2)
        p0.extend(coeffs)
    else:
        p0.extend([0.0, 0.0, np.min(y)])

    for i, pk in enumerate(peaks):
        amp = max(pk['height'], 0.01)
        tth_c = pk['two_theta']
        if i in halo_indices:
            sigma = 8.0  # wide halo
        else:
            # Use measured width or estimate
            try:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    pw = signal.peak_widths(y, [pk.get('idx', idx_pk)], rel_height=0.5)
                if pw[0][0] > 0:
                    sigma = max(pw[0][0] * np.mean(np.diff(x)) / 2.355, 0.1)
                else:
                    sigma = max(pk['two_theta'] * 0.03, 0.1)
            except Exception:
                sigma = max(pk['two_theta'] * 0.03, 0.1)
                logger.warning("异常已处理", exc_info=True)
        p0.append(amp)
        p0.append(tth_c)
        p0.append(sigma)
        if npp > 3:
            p0.append(0.5)

    # Bounds
    lower, upper = [], []
    lower.extend([-np.inf, -np.inf, 0])
    upper.extend([np.inf, np.inf, np.max(y)])
    for i, pk in enumerate(peaks):
        if i in halo_indices:
            lower.extend([0, x[0], 5.0])       # sigma >= 5 deg
            upper.extend([np.max(y)*2, x[-1], 25.0])  # sigma <= 25 deg
        else:
            lower.extend([0, x[0], 0.05])
            upper.extend([np.max(y)*2, x[-1], (x[-1]-x[0])/2])
        if npp > 3:
            lower.append(0.0)
            upper.append(1.0)

    try:
        def residual(params):
            return model(x, *params) - y
        from scipy.optimize import least_squares
        res = least_squares(residual, np.array(p0), bounds=(lower, upper), 
                           method='trf', max_nfev=2000, ftol=1e-2, xtol=1e-2)
        popt = res.x
    except Exception:
        popt = np.array(p0)
        logger.warning("异常已处理", exc_info=True)

    # Extract fitted peaks
    fitted = []
    idx_p = n_base
    for i in range(len(peaks)):
        pars = popt[idx_p:idx_p + npp]
        amp_f, mu_f, sigma_f = abs(pars[0]), pars[1], abs(pars[2])
        fwhm = 2.355 * sigma_f
        area = amp_f * sigma_f * np.sqrt(2 * np.pi)
        wavelength = 1.5406
        d = wavelength / (2.0 * np.sin(np.radians(mu_f / 2.0))) if mu_f > 0 else np.nan
        fitted.append({
            'index': i, 'idx': int(np.argmin(np.abs(x - mu_f))),
            'two_theta': float(mu_f), 'd_spacing_A': float(d),
            'height': float(amp_f), 'fwhm_deg': float(fwhm),
            'area': float(area), 'eta': float(pars[3]) if len(pars) > 3 else 0.5,
        })
        idx_p += npp

    y_pred = model(x, *popt)
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    baseline = popt[0] * x**2 + popt[1] * x + popt[2]

    # Interpolate back to original grid if downsampled
    if len(x_orig) != len(y_pred):
        y_pred = np.interp(x_orig, x, y_pred)
        baseline = np.interp(x_orig, x, baseline)

    return fitted, float(r2), y_pred, baseline


# ---------------------------------------------------------------------------
#  Amorphous halo subtraction
# ---------------------------------------------------------------------------

def fit_amorphous_halo(two_theta: np.ndarray, I: np.ndarray,
                       peak_positions: List[float],
                       method: str = 'spline',
                       anchors: Optional[List[float]] = None,
                       ) -> np.ndarray:
    """Fit the amorphous halo by interpolating between crystalline peaks.

    Parameters
    ----------
    method : str
        'spline' — cubic spline through manually/anchor points between peaks
        'polynomial' — 4th order polynomial
        'copy_quenched' — user-supplied quenched sample profile
    anchors : list of 2θ values, optional
    """
    x_orig = np.asarray(two_theta, dtype=float)
    y_orig = np.asarray(I, dtype=float)

    # Ensure strictly increasing x (required for interpolation)
    valid = np.isfinite(x_orig) & np.isfinite(y_orig)
    x, y = x_orig[valid], y_orig[valid]
    order = np.argsort(x)
    x, y = x[order], y[order]
    # Remove duplicates
    unique_mask = np.concatenate(([True], np.diff(x) > 1e-10))
    x, y = x[unique_mask], y[unique_mask]
    if len(x) < 5:
        return np.zeros_like(two_theta)

    if method == 'spline':
        if anchors is None:
            anchors = _auto_amorphous_anchors(x, peak_positions)

        # Ensure anchors are sorted and deduplicated
        anchors = sorted(set(anchors))
        # Interpolate anchor y-values using cleaned x/y
        anchor_y = np.interp(anchors, x, y)
        # Fit smooth spline through anchors
        spl = interpolate.CubicSpline(anchors, anchor_y, extrapolate=True)
        # Evaluate spline on cleaned x, then map back to original shape
        I_smooth = spl(x)
        # Interpolate back to original x grid
        from scipy.interpolate import interp1d
        return interp1d(x, I_smooth, kind='linear', bounds_error=False,
                        fill_value=(I_smooth[0], I_smooth[-1]))(x_orig)

    elif method == 'polynomial':
        # Fit polynomial excluding peak regions
        mask = np.ones(len(y), dtype=bool)
        for pos in peak_positions:
            idx = np.argmin(np.abs(x - pos))
            mask[max(0, idx - 15):min(len(y), idx + 15)] = False
        if np.sum(mask) > 10:
            coeffs = np.polyfit(x[mask], y[mask], 4)
            return np.polyval(coeffs, x)

    # Fallback: linear interpolation of minima
    return _baseline_minima(x, y)


def _auto_amorphous_anchors(two_theta, peak_positions) -> np.ndarray:
    """Auto-select anchor points between peaks for amorphous halo."""
    x_min = two_theta[0]
    x_max = two_theta[-1]
    all_points = [x_min] + sorted(peak_positions) + [x_max]
    anchors = []
    for i in range(len(all_points) - 1):
        a, b = all_points[i], all_points[i + 1]
        anchors.append((a + b) / 2.0)
    return np.array(anchors)


def _baseline_minima(x, y):
    """Simple baseline from local minima."""
    from scipy.signal import argrelextrema
    min_idx = argrelextrema(y, np.less, order=max(3, len(y) // 20))[0]
    if len(min_idx) < 2:
        return np.full_like(y, np.min(y))
    return np.interp(x, x[min_idx], y[min_idx])


# ---------------------------------------------------------------------------
#  Crystallinity
# ---------------------------------------------------------------------------

def compute_crystallinity_peak_area(I_total: np.ndarray,
                                     I_amorphous: np.ndarray,
                                     two_theta: np.ndarray,
                                     two_theta_range: Optional[Tuple[float, float]] = None,
                                     ) -> float:
    """Compute crystallinity by peak area ratio.

    Xc = ∫(I_total - I_amorphous) d(2θ) / ∫I_total d(2θ) * 100%

    Parameters
    ----------
    I_total : total intensity
    I_amorphous : amorphous halo intensity
    two_theta_range : (min, max) integration range
    """
    mask = np.ones(len(two_theta), dtype=bool)
    if two_theta_range is not None:
        mask = (two_theta >= two_theta_range[0]) & (two_theta <= two_theta_range[1])

    total = np.trapezoid(I_total[mask], two_theta[mask])
    amorphous = np.trapezoid(I_amorphous[mask], two_theta[mask])
    crystalline = total - amorphous

    if total <= 0:
        return np.nan

    return max(0.0, min(100.0, crystalline / total * 100.0))


# ---------------------------------------------------------------------------
#  Scherrer crystallite size
# ---------------------------------------------------------------------------

def scherrer_size(fwhm_deg: float, two_theta_deg: float,
                  wavelength_A: float = 1.5406,
                  K: float = 0.9,
                  instrument_fwhm_deg: float = 0.0,
                  ) -> float:
    """Scherrer equation for crystallite size.

    D = K·λ / (β·cos θ)

    Parameters
    ----------
    fwhm_deg : float
        Full width at half maximum in degrees 2θ.
    two_theta_deg : float
        Peak position in degrees 2θ.
    wavelength_A : float
        X-ray wavelength in Angstrom.
    K : float
        Shape factor (0.9 for spheres).

    Returns
    -------
    D in nm.
    """
    beta_sample_deg = np.sqrt(max(float(fwhm_deg) ** 2 - float(instrument_fwhm_deg) ** 2, 0.0))
    if beta_sample_deg <= 1e-9:
        return np.nan

    beta_rad = np.radians(beta_sample_deg)
    theta_rad = np.radians(two_theta_deg / 2.0)
    cos_theta = np.cos(theta_rad)

    if cos_theta < 1e-6:
        return np.nan

    D_A = K * wavelength_A / (beta_rad * cos_theta)
    return D_A / 10.0  # Å → nm


def scherrer_peak_sizes(peaks: List[Dict[str, Any]],
                        wavelength_A: float = 1.5406,
                        K: float = 0.9,
                        instrument_fwhm_deg: float = 0.0,
                        ) -> List[float]:
    """Scherrer sizes for valid peaks."""
    sizes = []
    for pk in peaks:
        fwhm = pk.get('fwhm_deg', np.nan)
        tth = pk.get('two_theta', np.nan)
        if not np.isnan(fwhm) and not np.isnan(tth) and fwhm > 0:
            D = scherrer_size(fwhm, tth, wavelength_A, K, instrument_fwhm_deg)
            if not np.isnan(D):
                sizes.append(D)
    return sizes


def scherrer_from_peaks(peaks: List[Dict[str, Any]],
                        wavelength_A: float = 1.5406,
                        K: float = 0.9,
                        instrument_fwhm_deg: float = 0.0,
                        ) -> float:
    """Average Scherrer size from all peaks."""
    sizes = scherrer_peak_sizes(peaks, wavelength_A, K, instrument_fwhm_deg)
    return float(np.mean(sizes)) if sizes else np.nan


# ---------------------------------------------------------------------------
#  Williamson-Hall analysis
# ---------------------------------------------------------------------------

def williamson_hall(peaks: List[Dict[str, Any]],
                    wavelength_A: float = 1.5406,
                    ) -> Tuple[float, float, float]:
    """Williamson-Hall plot: β·cos(θ) vs 4·sin(θ).

    β·cos(θ) = K·λ / D + 4·ε·sin(θ)

    Returns (D_nm, epsilon_pct, r_squared).
    """
    if len(peaks) < 2:
        return np.nan, np.nan, np.nan

    x_vals, y_vals = [], []
    for pk in peaks:
        fwhm = pk.get('fwhm_deg', np.nan)
        tth = pk.get('two_theta', np.nan)
        if np.isnan(fwhm) or np.isnan(tth) or fwhm <= 0:
            continue
        beta_rad = np.radians(fwhm)
        theta = np.radians(tth / 2.0)
        x_vals.append(4.0 * np.sin(theta))
        y_vals.append(beta_rad * np.cos(theta))

    if len(x_vals) < 2:
        return np.nan, np.nan, np.nan

    x_arr = np.array(x_vals)
    y_arr = np.array(y_vals)

    if np.allclose(x_arr, x_arr[0]) or np.allclose(y_arr, y_arr[0]):
        return np.nan, np.nan, np.nan

    slope, intercept, r, _, _ = __import__('scipy.stats', fromlist=['linregress']).linregress(x_arr, y_arr)

    D_A = 0.9 * wavelength_A / intercept if intercept > 0 else np.nan
    D_nm = D_A / 10.0 if not np.isnan(D_A) else np.nan
    epsilon = slope * 100.0  # percent

    return float(D_nm) if not np.isnan(D_nm) else np.nan, float(epsilon), float(r ** 2)


# ---------------------------------------------------------------------------
#  Crystal system identification
# ---------------------------------------------------------------------------

# Bragg's law:  sin²θ = (λ²/4a²) * (h² + k² + l²)  for cubic
# For cubic:  sin²θ ratios for allowed reflections

CUBIC_RATIOS = {
    'simple':   np.array([1, 2, 3, 4, 5, 6, 8, 9, 10]),
    'bcc':      np.array([1, 2, 3, 4, 5, 6, 7, 8]),
    'fcc':      np.array([3, 4, 8, 11, 12, 16, 19, 20]),
}


def identify_crystal_system(peaks: List[Dict[str, Any]],
                            wavelength_A: float = 1.5406,
                            ) -> Dict[str, Any]:
    """Attempt to identify crystal system from peak positions.

    Returns dict with: system, params, confidence.
    """
    if len(peaks) < 3:
        return {'system': 'unknown', 'params': {}, 'confidence': 0.0}

    sin2_theta = []
    for pk in peaks[:min(8, len(peaks))]:
        tth = pk.get('two_theta', np.nan)
        if np.isnan(tth):
            continue
        sin2 = np.sin(np.radians(tth / 2.0)) ** 2
        sin2_theta.append(sin2)

    if len(sin2_theta) < 3:
        return {'system': 'unknown', 'params': {}, 'confidence': 0.0}

    sin2 = np.array(sin2_theta)
    ratios = sin2 / sin2[0]

    # Test cubic
    best_system = 'unknown'
    best_conf = 0.0
    best_params = {}

    for cubic_type, ref_ratios in CUBIC_RATIOS.items():
        ref = ref_ratios / ref_ratios[0]
        n_compare = min(len(ratios), len(ref))
        rms = np.sqrt(np.mean((ratios[:n_compare] - ref[:n_compare]) ** 2))
        conf = max(0.0, 1.0 - rms / 0.2)
        if conf > best_conf and conf > 0.5:
            best_conf = conf
            best_system = f'cubic_{cubic_type}'
            # Lattice parameter from first peak
            hkl_sq = ref_ratios[0]  # h²+k²+l² for 1st reflection
            a_A = wavelength_A * np.sqrt(hkl_sq) / (2.0 * np.sqrt(sin2[0]))
            best_params = {'a_A': float(a_A)}

    # Test hexagonal
    if best_conf < 0.6:
        hk0_ratios = [1, 3, 4, 7, 9, 12]  # hk0 hexagonal
        ref = np.array(hk0_ratios[:len(ratios)]) / hk0_ratios[0]
        n_cmp = min(len(ratios), len(ref))
        rms = np.sqrt(np.mean((ratios[:n_cmp] - ref[:n_cmp]) ** 2))
        conf = max(0.0, 1.0 - rms / 0.2)
        if conf > best_conf and len(peaks) >= 4:
            best_conf = conf
            best_system = 'hexagonal'
            a_A = wavelength_A / (np.sqrt(3) * np.sqrt(sin2[0]))
            best_params = {'a_A': float(a_A)}

    return {
        'system': best_system if best_conf > 0.5 else 'unknown',
        'params': best_params,
        'confidence': float(best_conf),
    }


# ---------------------------------------------------------------------------
#  Full analysis pipeline
# ---------------------------------------------------------------------------

def analyze_scan(scan: WAXSScan, config: WAXSConfig,
                 label: str = "",
                 ) -> WAXSResult:
    """Run full WAXS analysis on one scan — v4.1: arPLS + lmfit joint fit."""
    import sys
    result = WAXSResult(label=label)

    if len(scan.two_theta_deg) < 10:
        print(f"[WAXS] {label}: too few data points ({len(scan.two_theta_deg)}), skipping", file=sys.stderr)
        return result

    tth = scan.two_theta_deg.copy()
    I = scan.I_arb.copy()
    valid = np.isfinite(tth) & np.isfinite(I)
    tth, I = tth[valid], I[valid]
    if len(tth) >= 2 and np.any(np.diff(tth) <= 0):
        order = np.argsort(tth)
        tth, I = tth[order], I[order]

    # Xc is an azimuthally averaged quantity. Sector profiles are still
    # generated for orientation, but using one sector for Xc over-weights
    # oriented arcs in tensile data.
    result.sector_used = 'full'

    result.two_theta = tth
    result.I = I

    # === Step 1: arPLS baseline correction (instrumental background) ===
    try:
        from pybaselines import Baseline
        baseline_fitter = Baseline(x_data=tth)
        lam = getattr(config, 'arpls_lam', 1e5)
        diff_order = getattr(config, 'arpls_diff_order', 2)
        I_baseline, _ = baseline_fitter.arpls(I, lam=lam, diff_order=diff_order)
        I_corrected = np.maximum(I - I_baseline, 0)
    except Exception as e:
        print(f"[WAXS] {label}: arPLS failed ({e}), falling back to raw data", file=sys.stderr)
        I_corrected = I.copy()
        logger.warning("异常已处理", exc_info=True)

    # === Step 2: Detect crystalline peaks in the main WAXS window ===
    is_2d = scan.image is not None
    min_tth = (getattr(config, 'crystallinity_min_two_theta', 15.0)
               if is_2d else getattr(config, 'min_two_theta', 0.0))
    max_tth = (getattr(config, 'crystallinity_max_two_theta', 35.0)
               if is_2d else np.inf)
    fit_mask = (tth >= min_tth) & (tth <= max_tth)
    if np.sum(fit_mask) < 20:
        fit_mask = tth >= getattr(config, 'min_two_theta', 0.0)

    if is_2d:
        tth_fit = tth[fit_mask]
        I_fit_raw = I[fit_mask]
        I_fit_corrected = I_corrected[fit_mask]
        tth_detect = tth_fit
        I_detect = I_fit_raw
    else:
        tth_fit = tth
        I_fit_raw = I
        I_fit_corrected = I_corrected
        detect_mask = tth >= getattr(config, 'min_two_theta', 0.0)
        tth_detect = tth[detect_mask]
        I_detect = I_corrected[detect_mask]

    peaks = detect_peaks(
        tth_detect, I_detect,
        height_frac=config.peak_height_min,
        distance=config.peak_distance,
        max_peaks=getattr(config, 'max_peaks', 8),
    )

    if not peaks:
        print(f"[WAXS] {label}: no peaks detected", file=sys.stderr)
        return result

    crystal_centers = [p['two_theta'] for p in peaks]

    # === Step 2b: Inject known polymer peaks (semi-supervised) ===
    polymer_type = getattr(config, 'polymer_type', '')
    constraint_centers = None
    if polymer_type:
        known_peaks = config.polymer_peaks_db.get(polymer_type, [])
        if known_peaks:
            constraint_centers = [kp[0] for kp in known_peaks]
            # Add known peaks to crystal_centers if not already detected nearby
            for kp in known_peaks:
                pos = kp[0]
                if not any(abs(pos - cc) < 1.2 for cc in crystal_centers):
                    crystal_centers.append(pos)
            crystal_centers.sort()

    from ..lmfit_wrapper import fit_waxs_profile

    n_halos = 1 if is_2d else getattr(config, 'amorphous_n_peaks', 2)
    halo_range = ((float(tth_fit[0]), float(tth_fit[-1]))
                  if is_2d else (getattr(config, 'min_two_theta', 5.0), 35.0))

    fit_result = fit_waxs_profile(
        x=tth_fit,
        y=I_fit_raw if is_2d else I_fit_corrected,
        crystal_centers=crystal_centers,
        n_halos=n_halos,
        peak_type=config.peak_function,
        halo_range=halo_range,
        constraint_centers=constraint_centers,
        baseline='none',
    )

    if not fit_result or not fit_result.get('components'):
        print(f"[WAXS] {label}: joint fit produced no components", file=sys.stderr)
        return result

    # === Step 4: Classify components and compute crystallinity ===
    components = fit_result['components']
    cryst_raw = [c for c in components if c.get('is_crystal', True)]
    halo_peaks = [c for c in components if not c.get('is_crystal', True)]
    

    # Filter weak crystal peaks (area < 5% of max crystal area)
    if cryst_raw:
        max_area = max(p['area'] for p in cryst_raw)
        cryst_peaks = [p for p in cryst_raw if p['area'] >= max_area * 0.05]
    else:
        cryst_peaks = []

    # Filter out peaks below min_two_theta (low-angle SAXS/air-scatter artifacts)
    min_tth_cryst = min_tth
    if min_tth_cryst > 0:
        low_angle = [p for p in cryst_peaks if p['center'] < min_tth_cryst]
        if low_angle:
            halo_peaks.extend(low_angle)
            cryst_peaks = [p for p in cryst_peaks if p['center'] >= min_tth_cryst]

    cryst_area = sum(p['area'] for p in cryst_peaks)
    halo_area = sum(p['area'] for p in halo_peaks)
    total_area = cryst_area + halo_area

    if total_area > 0 and cryst_peaks:
        result.Xc_pct = cryst_area / total_area * 100.0
        result.Xc_method = 'peak_deconvolution'
        result.peaks = _convert_lmfit_to_waxs_peaks(cryst_peaks, config.wavelength_A)
        result.n_peaks = len(cryst_peaks)
        result.two_theta = tth_fit
        result.I = I_fit_raw if is_2d else I_fit_corrected
        result.I_fit = fit_result['fit_y']
        baseline_y = fit_result.get('baseline_y', np.zeros_like(tth_fit))
        if len(baseline_y) != len(tth_fit):
            baseline_y = np.zeros_like(tth_fit)
        result.I_amorphous = fit_result.get('halo_y', np.zeros_like(tth_fit)) + baseline_y
        result.I_crystalline = result.I - result.I_amorphous
        result.r_squared = fit_result.get('r_squared', np.nan)

        # Iterative refinement for low-R² fits
        if (not is_2d) and result.r_squared < 0.92:
            refined = _refit_low_r2_v2(tth, I_corrected, result, config)
            if refined is not None:
                result = refined
                # Re-apply min_two_theta filter on refined result
                min_tth_re = getattr(config, 'min_two_theta', 8.0)
                refined_peaks = []
                for p in result.peaks:
                    if p['two_theta'] >= min_tth_re:
                        refined_peaks.append(p)
                if refined_peaks and len(refined_peaks) < len(result.peaks):
                    result.peaks = refined_peaks
                    result.n_peaks = len(refined_peaks)

    # Fallback: if peak_deconvolution gave no crystallinity OR poor fit,
    # try spline-based amorphous subtraction (more robust for PA6-like patterns).
    if np.isnan(result.Xc_pct) or result.Xc_pct <= 0 or result.r_squared < 0.60:
        try:
            # Use original detection (crystal_centers) if joint fit lost peaks
            if result.peaks and len(result.peaks) >= len(crystal_centers):
                peak_positions = [p['two_theta'] for p in result.peaks]
            else:
                peak_positions = crystal_centers
            # Use original I (not I_corrected) — arPLS may be too aggressive
            sub_method = getattr(config, 'amorphous_subtraction', 'polynomial')
            I_src = I_fit_raw if is_2d else I
            x_src = tth_fit if is_2d else tth
            I_amorphous = fit_amorphous_halo(
                x_src, I_src, peak_positions,
                method=sub_method,
                anchors=config.amorphous_anchors,
            )
            result.I_amorphous = I_amorphous
            result.I_crystalline = I_src - I_amorphous
            result.Xc_pct = compute_crystallinity_peak_area(I_src, I_amorphous, x_src)
            result.Xc_method = 'peak_area'
            result.two_theta = x_src
            result.I = I_src
            # Rebuild peaks from detection if joint fit lost them
            if not result.peaks or len(result.peaks) < len(crystal_centers):
                result.peaks = _convert_lmfit_to_waxs_peaks(cryst_peaks, config.wavelength_A) if cryst_peaks else []
                if not result.peaks:
                    # Build minimal peak list from detected centers
                    for i, cx in enumerate(crystal_centers):
                        result.peaks.append({
                            'index': i, 'two_theta': float(cx),
                            'd_spacing_A': float(config.wavelength_A / (2.0 * np.sin(np.radians(cx / 2.0)))),
                            'fwhm_deg': 1.5, 'area': 0.0, 'hkl': '',
                        })
                result.n_peaks = len(result.peaks)
        except Exception:
            logger.warning("静默异常", exc_info=True)

    # Post-check: if no truly sharp peak (FWHM < 5.0 deg) exists,
    # the sample is likely fully amorphous → zero out crystallinity.
    # Threshold relaxed from 2.0° → 5.0° for PA6 strain-broadened peaks.
    # Skip this check when Xc came from amorphous subtraction (peak_area)
    # or when sector integration is active (meridional peaks are broad).
    if result.peaks and result.Xc_method != 'peak_area':
        sharp_thresh = 5.0 if getattr(result, 'sector_used', 'full') != 'full' else 3.5
        has_sharp = any(p.get('fwhm_deg', 99) < sharp_thresh for p in result.peaks)
        if not has_sharp and result.n_peaks > 0:
            result.Xc_pct = 0.0
            result.Xc_method = 'no_sharp_peak'

    # Sanity cap: Xc > 95% is implausible even for highly oriented polymers
    if np.isfinite(result.Xc_pct) and result.Xc_pct > 95.0:
        result.Xc_pct = 95.0

    # === Step 5: Scherrer, Williamson-Hall, Crystal system ===
    scherrer_sizes = scherrer_peak_sizes(
        result.peaks,
        config.wavelength_A,
        config.scherrer_K,
        instrument_fwhm_deg=getattr(config, "instrument_fwhm_deg", 0.0),
    )
    result.D_Scherrer_nm = float(np.mean(scherrer_sizes)) if scherrer_sizes else np.nan
    if scherrer_sizes:
        result.D_uncertainty_nm = float(np.std(scherrer_sizes)) if len(scherrer_sizes) > 1 else 0.0
    result.instrument_broadening_applied = bool(getattr(config, "instrument_fwhm_deg", 0.0) > 0)

    D_wh, eps_wh, _ = williamson_hall(result.peaks, config.wavelength_A)
    result.D_WH_nm = D_wh if not np.isnan(D_wh) else np.nan
    result.epsilon_WH_pct = eps_wh if not np.isnan(eps_wh) else np.nan

    crystal = identify_crystal_system(result.peaks, config.wavelength_A)
    result.crystal_system = crystal['system']
    result.unit_cell_params = crystal['params']

    return result


# ---------------------------------------------------------------------------
#  Helper: auto-detect amorphous halo positions
# ---------------------------------------------------------------------------

def _detect_amorphous_halos(two_theta, residual, I_total,
                            n_halos=1, halo_range=(10.0, 30.0),
                            min_width=3.0):
    """Detect broad amorphous halo features in the residual.

    Scans the residual (or total intensity) in *halo_range* for broad
    positive humps.  Returns a list of peak dicts suitable for
    ``_fit_peaks_with_halo``.

    Parameters
    ----------
    n_halos : int
        Desired number of halo peaks (1 or 2).
    halo_range : (float, float)
        Expected 2θ range for the amorphous halo(s).
    min_width : float
        Minimum candidate peak width in °2θ to be considered a halo.
    """
    tth = np.asarray(two_theta)
    y = np.asarray(residual if len(residual) > 0 else I_total)

    # Constrain to halo range
    mask = (tth >= halo_range[0]) & (tth <= halo_range[1])
    if mask.sum() < 3:
        # Fallback: centre of the full range
        cx = float(np.median(tth))
        return [{'index': 99, 'two_theta': cx, 'height': np.max(y) * 0.3,
                 'idx': int(np.argmin(np.abs(tth - cx))), 'prominence': 0.0}]

    tth_r = tth[mask]
    y_r = y[mask].copy()
    # Ensure y_r is non-negative
    y_r = np.maximum(y_r, 0)

    # Very broad smoothing to suppress crystalline peaks
    window = max(5, len(y_r) // 10)
    if window % 2 == 0:
        window += 1
    if len(y_r) > window:
        from scipy.ndimage import uniform_filter1d
        y_smooth = uniform_filter1d(y_r, size=window)
    else:
        y_smooth = y_r

    halos = []
    for _ in range(n_halos):
        if len(y_smooth) < 3:
            break

        # Find the highest point in the smoothed residual
        idx_max = int(np.argmax(y_smooth))
        height = float(y_smooth[idx_max])
        if height <= 0:
            break

        two_theta_val = float(tth_r[idx_max])

        # Estimate width at half-max
        half = height / 2.0
        left = idx_max
        while left > 0 and y_smooth[left] > half:
            left -= 1
        right = idx_max
        while right < len(y_smooth) - 1 and y_smooth[right] > half:
            right += 1
        est_width = float(tth_r[right] - tth_r[left]) if right > left else 8.0

        # Only accept if wide enough to be a plausible halo
        if est_width < min_width:
            y_smooth[idx_max] = 0  # suppress and try next
            continue

        halos.append({
            'index': 99 + len(halos),
            'two_theta': two_theta_val,
            'height': height,
            'idx': int(np.argmin(np.abs(tth - two_theta_val))),
            'prominence': 0.0,
        })

        # Suppress region around this halo for next iteration
        half_width = max(int(est_width * 2 / np.mean(np.diff(tth_r))), 3)
        lo = max(0, idx_max - half_width)
        hi = min(len(y_smooth), idx_max + half_width)
        y_smooth[lo:hi] = 0

    # Fallback: if no halo found, create one at centre of range
    if not halos:
        cx = float((halo_range[0] + halo_range[1]) / 2.0)
        idx_cx = int(np.argmin(np.abs(tth - cx)))
        halos = [{
            'index': 99, 'two_theta': cx,
            'height': float(np.max(y_r)) * 0.3 if np.max(y_r) > 0 else 1.0,
            'idx': idx_cx, 'prominence': 0.0,
        }]

    return halos[:n_halos]


def _convert_lmfit_to_waxs_peaks(lmfit_components: List[Dict[str, Any]],
                                  wavelength_A: float = 1.5406,
                                  ) -> List[Dict[str, Any]]:
    """Convert lmfit_wrapper component dicts to WAXS peak format."""
    peaks = []
    for i, c in enumerate(lmfit_components):
        mu = c.get('center', np.nan)
        d = (wavelength_A / (2.0 * np.sin(np.radians(mu / 2.0)))
             if mu > 0 and not np.isnan(mu) else np.nan)
        peaks.append({
            'index': i,
            'two_theta': float(mu),
            'd_spacing_A': float(d) if not np.isnan(d) else np.nan,
            'height': float(c.get('amplitude', 0)),
            'fwhm_deg': float(c.get('fwhm', 0)),
            'area': float(c.get('area', 0)),
            'eta': 0.5,
            'hkl': '',
        })
    return peaks


# ---------------------------------------------------------------------------
#  Helper: iterative re-fit for low R²
# ---------------------------------------------------------------------------

def _refit_low_r2_v2(tth, I_corrected, result, config):
    """Iterative refinement for low-R² fits — actually works now.

    Detects missed peaks in the residual, adds them, and re-runs
    the joint fit.  Returns an updated WAXSResult or None.
    """
    import sys
    try:
        max_peaks = getattr(config, 'max_peaks', 8)
        if result.n_peaks >= max_peaks:
            return None

        if len(result.I_fit) == 0:
            return None

        residual = I_corrected - result.I_fit
        max_resid = float(np.max(np.abs(residual)))
        y_max = float(np.max(I_corrected))
        if y_max > 0 and max_resid < y_max * 0.05:
            return None  # residual is already small

        extra_peaks = detect_peaks(
            tth, np.maximum(residual, 0),
            height_frac=config.peak_height_min * 0.5,  # was 0.3 — too sensitive
            distance=config.peak_distance * 0.7,
            max_peaks=min(max_peaks - result.n_peaks, 3),  # cap at 3 extra
        )
        if not extra_peaks:
            return None

        # Filter extra peaks by min_two_theta
        min_tth = getattr(config, 'min_two_theta', 8.0)
        extra_peaks = [p for p in extra_peaks if p['two_theta'] >= min_tth]
        if not extra_peaks:
            return None

        # Merge with existing peaks
        existing_centers = [p['two_theta'] for p in result.peaks]
        new_centers = [p['two_theta'] for p in extra_peaks]
        all_centers = sorted(existing_centers + new_centers)

        from copy import deepcopy
        from ..lmfit_wrapper import fit_waxs_profile

        n_halos = getattr(config, 'amorphous_n_peaks', 1)
        halo_range = (getattr(config, 'min_two_theta', 5.0), 35.0)

        fit_result = fit_waxs_profile(
            x=tth, y=I_corrected,
            crystal_centers=all_centers,
            n_halos=n_halos,
            peak_type=config.peak_function,
            halo_range=halo_range,
        )

        if not fit_result or not fit_result.get('components'):
            return None

        r2_new = fit_result.get('r_squared', 0)
        if r2_new <= result.r_squared + 0.01:
            return None  # no meaningful improvement

        # Build updated result
        new_result = deepcopy(result)
        components = fit_result['components']
        cryst_raw = [c for c in components if c.get('is_crystal', True)]
        if cryst_raw:
            max_a = max(p['area'] for p in cryst_raw)
            cryst_peaks_new = [p for p in cryst_raw if p['area'] >= max_a * 0.05]
        else:
            cryst_peaks_new = []
        halo_new = [c for c in components if not c.get('is_crystal', True)]

        cryst_area_new = sum(p['area'] for p in cryst_peaks_new)
        halo_area_new = sum(p['area'] for p in halo_new)
        total_new = cryst_area_new + halo_area_new

        if total_new > 0:
            new_result.Xc_pct = cryst_area_new / total_new * 100.0
            new_result.peaks = _convert_lmfit_to_waxs_peaks(
                cryst_peaks_new, config.wavelength_A)
            new_result.n_peaks = len(cryst_peaks_new)
            new_result.I_fit = fit_result['fit_y']
            new_result.I_amorphous = fit_result.get('halo_y', np.zeros_like(tth))
            new_result.I_crystalline = I_corrected - new_result.I_amorphous
            new_result.r_squared = r2_new

        print(f"[WAXS] {result.label}: R² {result.r_squared:.3f} → {r2_new:.3f} "
              f"(+{len(new_centers)} peak)", file=sys.stderr)
        return new_result
    except Exception:
        return None


# Backwards-compatible alias
def _refit_low_r2(tth, I, all_fitted, config, result, fitted_peaks):
    """Legacy wrapper — delegates to _refit_low_r2_v2."""
    I_corrected = I if I is not None else np.zeros_like(tth)
    return _refit_low_r2_v2(tth, I_corrected, result, config)
