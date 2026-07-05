"""WAXS data preprocessing module.

Pipeline:
    1. 2D → 1D integration (pyFAI or manual)
    2. Polarisation correction (synchrotron)
    3. Air scattering subtraction
    4. Background subtraction (SKIPPED — now handled by arPLS in analyze_scan)
    5. Smoothing
    6. Instrument broadening correction (Caglioti)
"""
import logging
logger = logging.getLogger(__name__)


import numpy as np
from scipy import signal, interpolate, optimize
from typing import Optional, Tuple, Callable

from .io import WAXSScan, q_to_two_theta, two_theta_to_q, ensure_two_theta, ensure_q
from .config import WAXSConfig


# ---------------------------------------------------------------------------
#  2D → 1D integration (delegates to SAXS engine)
# ---------------------------------------------------------------------------

def integrate_2d_to_1d(scan: WAXSScan,
                       n_points: int = 1000,
                       mask: Optional[np.ndarray] = None,
                       ) -> WAXSScan:
    """Integrate a 2D WAXS image to a 1D profile using pyFAI-style azimuthal averaging.

    Delegates to the SAXS engine's integrator, but with WAXS-specific
    q-range (typically 0.5 – 6 Å⁻¹ / 5° – 60° 2θ).
    """
    if scan.image is None:
        return scan

    try:
        from ..saxs_engine.preprocess import build_integrator
        from ..saxs_engine.config import SAXSConfig

        # Build SAXSConfig from WAXS scan geometry
        saxs_cfg = SAXSConfig()
        saxs_cfg.pixel_size_m = scan.pixel_size_um * 1e-6
        saxs_cfg.sdd_m = scan.sample_detector_mm * 1e-3
        saxs_cfg.beam_center_x = scan.center_x
        saxs_cfg.beam_center_y = scan.center_y
        saxs_cfg.wavelength_m = scan.wavelength_A * 1e-10

        ai = build_integrator(saxs_cfg)

        if ai is not None:
            # pyFAI available: use SAXS integration
            from ..saxs_engine.preprocess import integrate_full
            saxs_cfg.n_pt = n_points
            saxs_cfg.q_min = 5.0  # nm⁻¹
            saxs_cfg.q_max = 60.0  # nm⁻¹
            q, I = integrate_full(ai, scan.image, saxs_cfg)
            # SAXS integrator returns q in nm⁻¹; WAXS expects q in Å⁻¹
            scan.q_Ainv = q / 10.0
        else:
            # No pyFAI: use WAXS-native manual integration (computes 2θ directly)
            q_A, I = _manual_radial_integration(
                scan.image, scan.center_x, scan.center_y,
                scan.pixel_size_um, scan.sample_detector_mm,
                scan.wavelength_A, n_points,
            )
            scan.q_Ainv = q_A  # already in Å⁻¹
    except ImportError:
        # Fallback: manual radial integration (already in Å⁻¹)
        q_A, I = _manual_radial_integration(
            scan.image, scan.center_x, scan.center_y,
            scan.pixel_size_um, scan.sample_detector_mm,
            scan.wavelength_A, n_points,
        )
        scan.q_Ainv = q_A

    scan.I_arb = I
    scan = ensure_two_theta(scan)
    return scan


def _manual_radial_integration(image: np.ndarray,
                                cx: float, cy: float,
                                pixel_size_um: float,
                                sample_detector_mm: float,
                                wavelength_A: float,
                                n_bins: int = 1000,
                                ) -> Tuple[np.ndarray, np.ndarray]:
    """Manual radial integration fallback (no pyFAI dependency)."""
    ny, nx = image.shape
    y, x = np.indices((ny, nx))

    # Pixel coordinates relative to beam center
    dx_um = (x - cx) * pixel_size_um
    dy_um = (y - cy) * pixel_size_um
    r_um = np.sqrt(dx_um ** 2 + dy_um ** 2)

    # Convert to 2θ
    two_theta = np.degrees(np.arctan(r_um / (sample_detector_mm * 1000.0)))
    two_theta_flat = two_theta.ravel()
    I_flat = image.ravel().astype(float)

    # Remove NaN/inf/negative and clip hot pixels
    valid = np.isfinite(I_flat) & (I_flat > 0) & (two_theta_flat > 0)
    two_theta_flat = two_theta_flat[valid]
    I_flat = I_flat[valid]

    if len(two_theta_flat) < 10:
        return np.array([]), np.array([])

    # Clip extreme values (hot pixels / beamstop saturation) to 99.9th percentile
    I_clip_val = float(np.percentile(I_flat, 99.9))
    I_flat = np.clip(I_flat, 0, I_clip_val)

    # Bin by 2θ
    tth_bins = np.linspace(two_theta_flat.min(), two_theta_flat.max(), n_bins + 1)
    digitized = np.digitize(two_theta_flat, tth_bins)
    I_mean = np.array([I_flat[digitized == i].mean()
                       if np.sum(digitized == i) > 0 else np.nan
                       for i in range(1, n_bins + 1)])
    tth_center = (tth_bins[:-1] + tth_bins[1:]) / 2

    valid = np.isfinite(I_mean)
    tth_center = tth_center[valid]
    I_mean = I_mean[valid]

    # Convert 2θ → q
    q = two_theta_to_q(tth_center, wavelength_A)

    return q, I_mean


# ---------------------------------------------------------------------------
#  Sector integration (meridional / equatorial) for anisotropic samples
# ---------------------------------------------------------------------------

def sector_integrate(image: np.ndarray,
                     cx: float, cy: float,
                     pixel_size_um: float,
                     sample_detector_mm: float,
                     wavelength_A: float,
                     chi_center: float,
                     chi_halfwidth: float = 15.0,
                     n_bins: int = 500,
                     two_theta_min: float = 3.0,
                     ) -> Tuple[np.ndarray, np.ndarray]:
    """Integrate over an azimuthal sector centred at *chi_center* ± *chi_halfwidth*.

    Returns (two_theta_deg, I_mean) — 1D profile for that sector.

    Parameters
    ----------
    chi_center : float
        Centre of the sector in degrees.  0° = right, 90° = top (meridional).
    chi_halfwidth : float
        Half-width of the sector; the integration covers
        [chi_center - chi_halfwidth, chi_center + chi_halfwidth] on both sides
        of the pattern (0–180° and 180–360° are treated as equivalent).
    """
    ny, nx = image.shape
    y, x = np.indices((ny, nx))

    # Pixel coordinates relative to beam centre (in µm)
    dx_um = (x - cx) * pixel_size_um
    dy_um = (y - cy) * pixel_size_um
    r_um = np.sqrt(dx_um ** 2 + dy_um ** 2)

    # Azimuthal angle χ in degrees — 0° = +x (right), +90° = +y (top)
    chi = np.degrees(np.arctan2(dy_um, dx_um))  # range (-180, 180]

    # Convert to 2θ
    two_theta = np.degrees(np.arctan(r_um / (sample_detector_mm * 1000.0)))

    # ---- Build sector mask ----
    # Include both χ and χ±180° (the opposite side of the pattern)
    chi_lo = chi_center - chi_halfwidth
    chi_hi = chi_center + chi_halfwidth
    mask = (chi >= chi_lo) & (chi <= chi_hi)
    # Opposite side
    opp_lo = chi_lo - 180.0
    opp_hi = chi_hi - 180.0
    mask |= (chi >= opp_lo) & (chi <= opp_hi)
    opp_lo2 = chi_lo + 180.0
    opp_hi2 = chi_hi + 180.0
    mask |= (chi >= opp_lo2) & (chi <= opp_hi2)

    # Apply valid-data mask
    valid = mask & np.isfinite(image) & (image > 0) & (two_theta >= two_theta_min)
    tth_flat = two_theta[valid].ravel()
    I_flat = image[valid].ravel().astype(float)

    if len(tth_flat) < 10:
        return np.array([]), np.array([])

    # Clip extreme values
    I_clip_val = float(np.percentile(I_flat, 99.9))
    I_flat = np.clip(I_flat, 0, I_clip_val)

    # Bin by 2θ
    tth_min = max(two_theta_min, tth_flat.min())
    tth_max = tth_flat.max()
    tth_bins = np.linspace(tth_min, tth_max, n_bins + 1)
    digitized = np.digitize(tth_flat, tth_bins)
    I_mean = np.array([I_flat[digitized == i].mean()
                       if np.sum(digitized == i) > 0 else np.nan
                       for i in range(1, n_bins + 1)])
    tth_center = (tth_bins[:-1] + tth_bins[1:]) / 2

    valid = np.isfinite(I_mean)
    return tth_center[valid], I_mean[valid]


# ---------------------------------------------------------------------------
#  Polarisation correction
# ---------------------------------------------------------------------------

def polarisation_correction(two_theta_deg: np.ndarray, I: np.ndarray,
                            P: float = 0.0,
                            ) -> np.ndarray:
    if abs(P) < 1e-6:
        return np.asarray(I)

    tth_rad = np.radians(two_theta_deg)
    cos2 = np.cos(tth_rad) ** 2
    factor = (1.0 - P) + P * cos2
    factor = np.maximum(factor, 0.01)
    return np.asarray(I) / factor


# ---------------------------------------------------------------------------
#  Air scattering subtraction
# ---------------------------------------------------------------------------

def subtract_air_scattering(I_sample: np.ndarray, I_air: np.ndarray,
                            scale: float = 1.0,
                            ) -> np.ndarray:
    air = np.asarray(I_air, dtype=float)
    if len(air) != len(I_sample):
        x_old = np.linspace(0, 1, len(air))
        x_new = np.linspace(0, 1, len(I_sample))
        air = np.interp(x_new, x_old, air)
    return np.asarray(I_sample) - scale * air


# ---------------------------------------------------------------------------
#  Background subtraction  (kept for backwards compatibility; not used in
#  default pipeline — arPLS in analyze_scan handles baseline removal)
# ---------------------------------------------------------------------------

def subtract_background(two_theta: np.ndarray, I: np.ndarray,
                        method: str = 'polynomial',
                        order: int = 3,
                        n_anchors: int = 10,
                        ) -> Tuple[np.ndarray, np.ndarray]:
    x = np.asarray(two_theta, dtype=float)
    y = np.asarray(I, dtype=float)

    if method == 'linear':
        bg = np.polyval(np.polyfit(x[[0, -1]], y[[0, -1]], 1), x)

    elif method == 'polynomial':
        coeffs = np.polyfit(x, y, order)
        bg = np.polyval(coeffs, x)

    elif method == 'spline':
        anchor_idx = np.linspace(0, len(x) - 1, n_anchors, dtype=int)
        anchor_idx = np.unique(np.clip(anchor_idx, 0, len(x) - 1))
        try:
            spl = interpolate.CubicSpline(x[anchor_idx], y[anchor_idx],
                                          extrapolate=True)
            bg = spl(x)
        except Exception:
            bg = np.polyval(np.polyfit(x, y, 1), x)
            logger.warning("异常已处理", exc_info=True)

    elif method == 'chebyshev':
        from numpy.polynomial import Chebyshev
        cheb = Chebyshev.fit(x, y, deg=order)
        bg = cheb(x)

    else:
        bg = np.zeros_like(y)

    return np.maximum(y - bg, 0), bg


# ---------------------------------------------------------------------------
#  Smoothing
# ---------------------------------------------------------------------------

def smooth_profile(I: np.ndarray,
                   method: str = 'savgol',
                   window: int = 9,
                   order: int = 3,
                   ) -> np.ndarray:
    I = np.asarray(I, dtype=float)
    if method == 'none' or len(I) < window or window < 3:
        return I

    if method == 'savgol':
        if window % 2 == 0:
            window += 1
        return signal.savgol_filter(I, min(window, len(I)), order)

    elif method == 'gaussian':
        from scipy.ndimage import gaussian_filter1d
        return gaussian_filter1d(I, sigma=window / 4.0)

    elif method == 'median':
        from scipy.ndimage import median_filter
        return median_filter(I, size=min(window, len(I)))

    elif method == 'boxcar':
        from scipy.ndimage import uniform_filter1d
        return uniform_filter1d(I, size=min(window, len(I)))

    return I


# ---------------------------------------------------------------------------
#  Caglioti instrumental broadening
# ---------------------------------------------------------------------------

def caglioti_correction(two_theta_deg: np.ndarray, fwhm_deg: float,
                        U: float = 0.0, V: float = 0.0, W: float = 0.0,
                        ) -> float:
    H2 = U * np.tan(np.radians(two_theta_deg / 2)) ** 2 + \
         V * np.tan(np.radians(two_theta_deg / 2)) + W
    beta_inst = np.sqrt(max(H2, 0))
    beta_corr = np.sqrt(max(fwhm_deg ** 2 - beta_inst ** 2, 0))
    return float(beta_corr)


# ---------------------------------------------------------------------------
#  Full preprocessing pipeline
# ---------------------------------------------------------------------------

def preprocess_pipeline(scan: WAXSScan, config: WAXSConfig,
                        I_air: Optional[np.ndarray] = None,
                        ) -> WAXSScan:
    """Run full WAXS preprocessing pipeline.

    Steps:
        1. 2D → 1D integration (if image data exists)
        2. Ensure both q and 2θ coordinates
        3. Polarisation correction
        4. Air scattering subtraction
        5. Background subtraction (SKIPPED — arPLS handles this)
        6. Smoothing
    """
    # 1. Integrate if needed
    if scan.image is not None and len(scan.q_Ainv) == 0:
        scan = integrate_2d_to_1d(scan)

    # 1b. Sector integration (meridional / equatorial) for anisotropic samples
    if scan.image is not None and getattr(config, 'do_sector_integration', False):
        hw = getattr(config, 'chi_halfwidth', 15.0)
        tth_mer, I_mer = sector_integrate(
            scan.image, scan.center_x, scan.center_y,
            scan.pixel_size_um, scan.sample_detector_mm, scan.wavelength_A,
            chi_center=getattr(config, 'chi_merid_center', 90.0),
            chi_halfwidth=hw,
        )
        tth_eq, I_eq = sector_integrate(
            scan.image, scan.center_x, scan.center_y,
            scan.pixel_size_um, scan.sample_detector_mm, scan.wavelength_A,
            chi_center=getattr(config, 'chi_equat_center', 0.0),
            chi_halfwidth=hw,
        )
        # Interpolate to common 2θ grid (the full-average grid)
        if len(tth_mer) > 5 and len(scan.two_theta_deg) > 5:
            scan.I_merid = np.interp(scan.two_theta_deg, tth_mer, I_mer,
                                     left=np.nan, right=np.nan)
        else:
            scan.I_merid = I_mer if len(tth_mer) > 5 else None
        if len(tth_eq) > 5 and len(scan.two_theta_deg) > 5:
            scan.I_equat = np.interp(scan.two_theta_deg, tth_eq, I_eq,
                                     left=np.nan, right=np.nan)
        else:
            scan.I_equat = I_eq if len(tth_eq) > 5 else None
        # Build sector data dict for downstream (Herman factor, etc.)
        scan.I_sector_data = {
            "q": scan.q_Ainv,
            "two_theta": scan.two_theta_deg,
            "I_full": scan.I_arb,
            "I_merid": scan.I_merid,
            "I_equat": scan.I_equat,
        }

    # 2. Coordinate consistency
    scan = ensure_two_theta(scan)
    scan = ensure_q(scan)

    if len(scan.two_theta_deg) == 0:
        return scan

    I = scan.I_arb.copy()

    # 3. Polarisation correction
    if config.polarisation_factor > 0:
        I = polarisation_correction(scan.two_theta_deg, I,
                                     config.polarisation_factor)

    # 4. Air scattering subtraction
    if I_air is not None:
        I = subtract_air_scattering(I, I_air)

    # 5. Background subtraction — SKIPPED in v4.1
    #    Instrumental baseline is now handled by arPLS inside
    #    analyze_scan().  Keeping this call commented out to avoid
    #    double-subtraction conflicts.
    # I, bg = subtract_background(
    #     scan.two_theta_deg, I,
    #     method=config.background_method,
    #     order=config.background_order,
    # )
    scan.metadata['background'] = None  # arPLS handles baseline in analyze_scan()

    # 6. Smoothing
    if config.smooth_method != 'none':
        I = smooth_profile(I, method=config.smooth_method,
                           window=config.smooth_window,
                           order=config.smooth_order)

    scan.I_arb = I
    return scan
