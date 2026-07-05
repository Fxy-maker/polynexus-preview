"""
saxs.preprocess — Module 2: Preprocessing.

pyFAI-based azimuthal integration (2D -> 1D),
background subtraction, transmission/thickness normalization,
smoothing, and geometric correction.
"""
import logging
logger = logging.getLogger(__name__)


from pathlib import Path
from typing import Tuple, Optional, Callable, Dict, List
from dataclasses import replace
import numpy as np
from scipy.signal import savgol_filter

from .config import SAXSConfig


# ---------------------------------------------------------------------------
#  pyFAI azimuthal integration
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
#  Polarisation correction
# ---------------------------------------------------------------------------

def apply_polarisation_correction(
    q: np.ndarray, I: np.ndarray, cfg,
) -> np.ndarray:
    """Apply synchrotron polarisation correction to 1D intensity.

    For horizontally polarised synchrotron radiation:
        I_corr = I_raw / (1 - P/2 * cos^2(2theta))

    For lab sources (unpolarised), set polarisation_degree=0 to skip.

    Reference: ESRF SAXS standard data reduction protocol.
    """
    if not getattr(cfg, 'do_polarisation_correction', False):
        return I
    P = getattr(cfg, 'polarisation_degree', 0.0)
    if P <= 0:
        return I

    q_m_inv = q * 1e9  # q is stored as nm^-1; wavelength is stored in metres.
    theta = np.arcsin(np.clip(q_m_inv * cfg.wavelength_m / (4 * np.pi), -1, 1))
    cos2_2theta = np.cos(2 * theta) ** 2
    correction = 1.0 - P * 0.5 * cos2_2theta
    correction = np.clip(correction, 0.01, None)
    return I / correction


def build_integrator(cfg: SAXSConfig):
    """Build an integrator (pyFAI if available, else None for manual fallback).

    Priority: poni_file > pyFAI manual geometry > manual numpy (default).
    """
    if cfg.poni_file and Path(cfg.poni_file).exists():
        try:
            import pyFAI
            return pyFAI.load(cfg.poni_file)
        except Exception:
            logger.warning("静默异常", exc_info=True)

    if cfg.use_pyfai_integration:
        try:
            import pyFAI as _pyfai_check  # force import check
            from pyFAI.detectors import Detector

            det = Detector(pixel1=cfg.pixel_size_m, pixel2=cfg.pixel_size_m)
            ai = pyFAI.AzimuthalIntegrator(
                dist=cfg.sdd_m,
                poni1=cfg.beam_center_y * cfg.pixel_size_m,
                poni2=cfg.beam_center_x * cfg.pixel_size_m,
                detector=det,
                wavelength=cfg.wavelength_m,
            )
            # Verify it works
            test_q = ai.qFunction((100, 100))
            if test_q is not None and np.max(test_q) > 0:
                return ai
        except Exception:
            logger.warning("静默异常", exc_info=True)

    # Fallback: no pyFAI, use manual numpy integration
    return None

def _manual_sector_integrate(img: np.ndarray, cfg: SAXSConfig, sector: str) -> np.ndarray:
    """Manual sector integration for meridional or equatorial regions.

    Uses azimuthal masking in polar coordinates.
    """
    ny, nx = img.shape
    y_idx, x_idx = np.ogrid[:ny, :nx]
    y_m = (y_idx - cfg.beam_center_y) * cfg.pixel_size_m
    x_m = (x_idx - cfg.beam_center_x) * cfg.pixel_size_m
    r_m = np.sqrt(x_m**2 + y_m**2)
    chi = np.degrees(np.arctan2(y_m, x_m))  # azimuthal angle in degrees

    two_theta = np.arctan2(r_m, cfg.sdd_m)
    q_map = 4 * np.pi * np.sin(two_theta / 2) / cfg.wavelength_m * 1e-9

    if sector == 'meridional':
        chi_mask = (chi >= cfg.chi_merid_range[0]) & (chi <= cfg.chi_merid_range[1])
        # Also include opposite side (chi + 180)
        chi_mask |= ((chi + 180 >= cfg.chi_merid_range[0]) & (chi + 180 <= cfg.chi_merid_range[1]))
        chi_mask |= ((chi - 180 >= cfg.chi_merid_range[0]) & (chi - 180 <= cfg.chi_merid_range[1]))
    else:  # equatorial
        chi_mask = (chi >= cfg.chi_equat_range[0]) & (chi <= cfg.chi_equat_range[1])
        chi_mask |= ((chi + 180 >= cfg.chi_equat_range[0]) & (chi + 180 <= cfg.chi_equat_range[1]))
        chi_mask |= ((chi - 180 >= cfg.chi_equat_range[0]) & (chi - 180 <= cfg.chi_equat_range[1]))

    # Exclude dummy / masked pixels (beam stop, dead pixels, etc.)
    dummy_mask = _build_mask(img, cfg)
    if dummy_mask is not None:
        valid = np.isfinite(img) & (img > 0) & chi_mask & ~dummy_mask
    else:
        valid = np.isfinite(img) & (img > 0) & chi_mask
    q_v = q_map[valid].flatten()
    I_v = img[valid].flatten()

    n_bins = cfg.n_pt
    q_bins = np.linspace(max(cfg.q_min, 0.01), min(cfg.q_max, q_map.max()), n_bins + 1)
    q_center = (q_bins[:-1] + q_bins[1:]) / 2
    I_radial = np.zeros(n_bins)

    for i in range(n_bins):
        mask = (q_v >= q_bins[i]) & (q_v < q_bins[i + 1])
        if np.sum(mask) > 0:
            I_radial[i] = np.mean(I_v[mask])

    return I_radial


def _manual_integrate(img: np.ndarray, cfg: SAXSConfig) -> Tuple[np.ndarray, np.ndarray]:
    """Manual radial integration fallback (no pyFAI dependency for core functionality)."""
    # Guard against invalid geometry configuration
    if cfg.wavelength_m <= 0 or cfg.sdd_m <= 0:
        raise ValueError(
            f"Invalid geometry: wavelength={cfg.wavelength_m}m, SDD={cfg.sdd_m}m. "
            f"Set valid values in SAXSConfig."
        )
    ny, nx = img.shape
    y_idx, x_idx = np.ogrid[:ny, :nx]
    y_m = (y_idx - cfg.beam_center_y) * cfg.pixel_size_m
    x_m = (x_idx - cfg.beam_center_x) * cfg.pixel_size_m
    r_m = np.sqrt(x_m**2 + y_m**2)
    two_theta = np.arctan2(r_m, cfg.sdd_m)
    q_map = 4 * np.pi * np.sin(two_theta / 2) / cfg.wavelength_m * 1e-9

    q_flat = q_map.flatten()
    I_flat = img.flatten()
    # Exclude dummy / masked pixels (beam stop, dead pixels, etc.)
    dummy_mask = _build_mask(img, cfg)
    if dummy_mask is not None:
        valid = np.isfinite(I_flat) & (I_flat > 0) & np.isfinite(q_flat) & ~dummy_mask.flatten()
    else:
        valid = np.isfinite(I_flat) & (I_flat > 0) & np.isfinite(q_flat)
    q_v = q_flat[valid]
    I_v = I_flat[valid]

    n_bins = cfg.n_pt
    q_bins = np.linspace(max(cfg.q_min, 0.01), min(cfg.q_max, q_map.max()), n_bins + 1)
    q_center = (q_bins[:-1] + q_bins[1:]) / 2
    I_radial = np.zeros(n_bins)

    for i in range(n_bins):
        mask = (q_v >= q_bins[i]) & (q_v < q_bins[i + 1])
        if np.sum(mask) > 0:
            I_radial[i] = np.mean(I_v[mask])

    return q_center, I_radial


def _integrate_pyfai_shadow(img: np.ndarray, cfg: SAXSConfig) -> Tuple[np.ndarray, np.ndarray]:
    """Standalone pyFAI integration for cross-validation (shadow channel).

    Only activates when pyFAI is installed AND geometry is valid.
    Returns (q, I) on success, (empty, empty) on any failure.
    This function is intentionally isolated from the main integration path
    so that pyFAI failures never affect the core pipeline.
    """
    try:
        import pyFAI, warnings
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        # Try modern pyFAI import first (>=0.20), fall back to legacy
        try:
            from pyFAI.integrator.azimuthal import AzimuthalIntegrator
            from pyFAI.detectors import Detector

            det = Detector(pixel1=cfg.pixel_size_m, pixel2=cfg.pixel_size_m)
            ai = AzimuthalIntegrator(
                dist=cfg.sdd_m,
                poni1=cfg.beam_center_y * cfg.pixel_size_m,
                poni2=cfg.beam_center_x * cfg.pixel_size_m,
                detector=det,
                wavelength=cfg.wavelength_m,
            )
        except (ImportError, AttributeError):
            from pyFAI.detectors import Detector

            det = Detector(pixel1=cfg.pixel_size_m, pixel2=cfg.pixel_size_m)
            ai = pyFAI.AzimuthalIntegrator(
                dist=cfg.sdd_m,
                poni1=cfg.beam_center_y * cfg.pixel_size_m,
                poni2=cfg.beam_center_x * cfg.pixel_size_m,
                detector=det,
                wavelength=cfg.wavelength_m,
            )

        result = ai.integrate1d(
            img, cfg.n_pt,
            radial_range=(cfg.q_min, cfg.q_max),
            unit="q_nm^-1",
            method="csr",
            error_model="poisson",
        )
        # Handle both 2-tuple (old pyFAI) and 3-tuple (new pyFAI) returns
        if len(result) == 3:
            q, I, _sigma = result
        else:
            q, I = result

        valid = np.isfinite(I) & (I > 0) & (q > 0) & (q <= cfg.q_max)
        if np.sum(valid) >= 20:
            q = q[valid]
            I = I[valid]
            # Normalize to match manual integration amplitude range
            I_max = np.max(I)
            if I_max > 0:
                I = I / I_max
            return q, I
    except Exception:
        logger.warning("静默异常", exc_info=True)
    return np.array([]), np.array([])


def integrate_full(ai, img: np.ndarray, cfg: SAXSConfig) -> Tuple[np.ndarray, np.ndarray]:
    """Full azimuthal integration -> I(q).

    If ai is None (no pyFAI), uses manual numpy integration.
    If ai is provided but produces empty results, falls back to manual.
    """
    if ai is not None:
        try:
            mask = _build_mask(img, cfg)
            q, I = ai.integrate1d(
                img, cfg.n_pt,
                radial_range=(cfg.q_min, cfg.q_max),
                mask=mask,
                unit="q_nm^-1",
                method="csr",
                error_model="poisson",
            )
            valid = np.isfinite(I) & (I > 0) & (q > 0)
            if np.sum(valid) > 10 and q[valid][-1] > q[valid][0]:
                return q[valid], I[valid]
        except Exception:
            logger.warning("静默异常", exc_info=True)

    # Manual numpy fallback
    return _manual_integrate(img, cfg)

def integrate_sectors(
    ai, img: np.ndarray, cfg: SAXSConfig
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Anisotropic integration: meridional + equatorial sectors.

    If ai is None, uses manual integration and approximates sectors.
    Returns (q, I_full, I_merid, I_equat).
    """
    if ai is None:
        q, I_full = _manual_integrate(img, cfg)
        # Approximate sectors from manual integration
        I_merid = _manual_sector_integrate(img, cfg, 'meridional')
        I_equat = _manual_sector_integrate(img, cfg, 'equatorial')
        return q, I_full, I_merid, I_equat

    mask = _build_mask(img, cfg)
    n_pt = cfg.n_pt

    # Full
    q, I_full = ai.integrate1d(
        img, n_pt,
        radial_range=(cfg.q_min, cfg.q_max),
        mask=mask, unit="q_nm^-1", method="csr",
    )

    # Meridional
    _, I_merid = ai.integrate1d(
        img, n_pt,
        radial_range=(cfg.q_min, cfg.q_max),
        azimuth_range=(cfg.chi_merid_range[0], cfg.chi_merid_range[1]),
        mask=mask, unit="q_nm^-1", method="csr",
    )

    # Equatorial
    _, I_equat = ai.integrate1d(
        img, n_pt,
        radial_range=(cfg.q_min, cfg.q_max),
        azimuth_range=(cfg.chi_equat_range[0], cfg.chi_equat_range[1]),
        mask=mask, unit="q_nm^-1", method="csr",
    )

    return q, I_full, I_merid, I_equat


def integrate_chi_sectors(
    ai, img: np.ndarray, cfg: SAXSConfig
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Azimuthal sector integration into n_chi_sectors bins.

    Returns (q, I_2d[n_chi, n_q], chi_center).
    """
    mask = _build_mask(img, cfg)
    n_chi = cfg.n_chi_sectors

    res = ai.integrate2d(
        img, cfg.n_pt, n_chi,
        radial_range=(cfg.q_min, cfg.q_max),
        mask=mask, unit="q_nm^-1", method="csr",
    )
    I_2d = res.intensity
    q = res.radial
    chi = res.azimuthal
    return q, I_2d, chi


def default_integration_fn(img, cfg):
    """Default integration pipeline for assemble_dataset().

    For isotropic: integrate_full only.
    For anisotropic: integrate_sectors.
    """
    ai = build_integrator(cfg)
    if cfg.is_isotropic or cfg.analysis_priority == "isotropic":
        q, I = integrate_full(ai, img, cfg)
        return q, I, None, None
    else:
        return integrate_sectors(ai, img, cfg)


# ---------------------------------------------------------------------------
#  Background subtraction
# ---------------------------------------------------------------------------

def subtract_background(
    q: np.ndarray,
    I_sample: np.ndarray,
    I_background: np.ndarray,
    cfg: SAXSConfig,
    q_background: Optional[np.ndarray] = None,
) -> np.ndarray:
    """Subtract background scattering: I_corr = I_sample - scale * I_bg.

    Scale determined by cfg.bg_scale_method:
        "transmission" -> T_bg / T_sample
        "thickness"     -> d_bg / d_sample
        "manual"        -> cfg.bg_scale_value
    """
    if cfg.bg_scale_method == "transmission":
        scale = cfg.transmission_background / max(cfg.transmission_sample, 1e-6)
    elif cfg.bg_scale_method == "thickness":
        scale = 1.0  # thickness normalized separately
    else:
        scale = cfg.bg_scale_value

    # Interpolate background to sample q grid if needed.
    if q_background is not None:
        q_bg = np.asarray(q_background, dtype=float)
        I_bg = np.asarray(I_background, dtype=float)
        valid = np.isfinite(q_bg) & np.isfinite(I_bg)
        if np.sum(valid) >= 2:
            order = np.argsort(q_bg[valid])
            I_bg_interp = np.interp(q, q_bg[valid][order], I_bg[valid][order])
        else:
            I_bg_interp = np.zeros_like(I_sample)
    elif len(I_background) == len(I_sample):
        I_bg_interp = I_background
    else:
        I_bg_interp = np.interp(
            np.linspace(0, 1, len(I_sample)),
            np.linspace(0, 1, len(I_background)),
            I_background,
        )

    I_corr = I_sample - scale * I_bg_interp
    return np.maximum(I_corr, 1e-12)


def normalize_intensity(I: np.ndarray, cfg: SAXSConfig) -> np.ndarray:
    """Apply transmission and thickness normalization.

    I_norm = I / (T_sample * d_sample)
    """
    T = max(cfg.transmission_sample, 1e-6)
    d = max(cfg.sample_thickness_m, 1e-9)
    return I / (T * d)


# ---------------------------------------------------------------------------
#  Smoothing
# ---------------------------------------------------------------------------

def smooth_profile(q: np.ndarray, I: np.ndarray, cfg: SAXSConfig) -> np.ndarray:
    """Apply smoothing to 1D scattering profile.

    Edge-safe: detects sharp transitions (e.g. beamstop edge, mask edge)
    and smooths each continuous segment independently to prevent
    artificial jumps at intensity discontinuities.
    """
    if cfg.smooth_method == "none":
        return I

    if cfg.smooth_method == "savgol":
        window = min(cfg.savgol_window, len(I) - 2)
        if window % 2 == 0:
            window += 1
        if window < 3:
            return I
        order = min(cfg.savgol_order, window - 1)

        # Detect sharp transitions in I(log scale) — beamstop edge / mask edge
        # A transition is a point-to-point ratio > 8x (intensity jump).
        # Lowered from 20x to 8x to catch beamstop edges where I drops ~16x
        # (e.g. 766 → 47 counts across q=0.099→0.102).
        transitions = _find_intensity_transitions(I, min_ratio=8.0)

        if len(transitions) == 0:
            result = savgol_filter(I, window, order)
            return np.maximum(result, 0)

        # Smooth each segment independently
        result = np.zeros_like(I)
        seg_start = 0
        for t_idx in transitions + [len(I)]:
            t_idx = min(t_idx, len(I))
            seg_len = t_idx - seg_start
            if seg_len >= window:
                seg_window = min(window, seg_len)
                if seg_window % 2 == 0:
                    seg_window -= 1
                seg_order = min(order, seg_window - 1)
                if seg_window >= 3 and seg_order < seg_window:
                    seg_smoothed = savgol_filter(I[seg_start:t_idx], seg_window, seg_order)
                else:
                    seg_smoothed = I[seg_start:t_idx]
                result[seg_start:t_idx] = seg_smoothed
            else:
                result[seg_start:t_idx] = I[seg_start:t_idx]  # too short; keep raw
            seg_start = t_idx
        # Clamp to non-negative and clip outliers that the savgol filter
        # may have created at segment boundaries (Gibbs-like overshoot)
        result = np.clip(result, 0, None)
        # Boundary blending: within 3 points of a segment edge, blend 50/50
        # with raw data to prevent artificial flat-lining
        for t_idx in transitions:
            lo = max(0, t_idx - 3)
            hi = min(len(I), t_idx + 3)
            blend_len = hi - lo
            if blend_len > 0:
                alpha = np.linspace(0.5, 0.5, blend_len)  # simple 50/50 blend
                result[lo:hi] = alpha * I[lo:hi] + (1 - alpha) * result[lo:hi]
        return np.maximum(result, 0)

    elif cfg.smooth_method == "moving_average":
        span = min(cfg.smooth_span, len(I) // 2)
        if span < 2:
            return I
        kernel = np.ones(span) / span
        result = np.convolve(I, kernel, mode='same')
        return np.maximum(result, 0)

    return I


def _find_intensity_transitions(I: np.ndarray, min_ratio: float = 20.0) -> List[int]:
    """Find indices where intensity changes by more than *min_ratio* between
    consecutive points (in either direction).  Returns sorted list of indices
    marking transition boundaries."""
    transitions: List[int] = []
    for i in range(1, len(I)):
        a, b = float(I[i - 1]), float(I[i])
        if a <= 0 or b <= 0:
            continue
        ratio = max(a, b) / min(a, b)
        if ratio >= min_ratio:
            transitions.append(i)
    return transitions


# ---------------------------------------------------------------------------
#  Geometric correction (in-situ temperature)
# ---------------------------------------------------------------------------

def apply_thermal_correction(cfg: SAXSConfig, temperature: float) -> SAXSConfig:
    """Correct SDD and beam center for thermal expansion.

    SDD(T) = SDD_0 * (1 + alpha * delta_T)
    Beam center drifts as configured.
    """
    corrected = replace(cfg)
    dT = temperature - 25.0  # reference 25C
    if corrected.sdd_drift_ppm_per_C != 0:
        corrected.sdd_m *= (1 + corrected.sdd_drift_ppm_per_C * 1e-6 * dT)
    if corrected.beam_center_drift_px_per_C != 0:
        corrected.beam_center_x += corrected.beam_center_drift_px_per_C * dT
        corrected.beam_center_y += corrected.beam_center_drift_px_per_C * dT
    if corrected.alpha_thermal_expansion != 0:
        corrected.sdd_m *= (1 + corrected.alpha_thermal_expansion * dT)
    return corrected


# ---------------------------------------------------------------------------
#  Full preprocessing pipeline
# ---------------------------------------------------------------------------

def preprocess_pipeline(
    img: np.ndarray,
    cfg: SAXSConfig,
    ai=None,
    I_background: Optional[np.ndarray] = None,
    q_background: Optional[np.ndarray] = None,
    temperature: float = 25.0,
) -> dict:
    """Run the full preprocessing pipeline on a single 2D image.

    Returns dict with keys:
        q, Iq, Iq_merid, Iq_equat, Iq_smooth, Iq_corrected
    """
    if ai is None:
        ai = build_integrator(cfg)

    # Thermal correction
    if cfg.experiment_type == "temperature":
        cfg = apply_thermal_correction(cfg, temperature)
        ai = build_integrator(cfg)

    # Integration
    if cfg.is_isotropic:
        q, Iq = integrate_full(ai, img, cfg)
        result = {"q": q, "Iq": Iq, "Iq_merid": None, "Iq_equat": None}
    else:
        q, I_full, I_merid, I_equat = integrate_sectors(ai, img, cfg)
        result = {"q": q, "Iq": I_full, "Iq_merid": I_merid, "Iq_equat": I_equat}

    # Background subtraction
    if I_background is not None and q_background is not None:
        result["Iq_corrected"] = subtract_background(
            q, result["Iq"],
            I_background, cfg, q_background=q_background,
        )
        if result["Iq_merid"] is not None:
            result["Iq_merid_corrected"] = subtract_background(
                q, result["Iq_merid"],
                I_background, cfg, q_background=q_background,
            )
        if result["Iq_equat"] is not None:
            result["Iq_equat_corrected"] = subtract_background(
                q, result["Iq_equat"],
                I_background, cfg, q_background=q_background,
            )
    else:
        result["Iq_corrected"] = result["Iq"]

    # Polarisation correction
    result["Iq_corrected"] = apply_polarisation_correction(
        q, result["Iq_corrected"], cfg)

    # Normalization
    result["Iq_norm"] = normalize_intensity(result["Iq_corrected"], cfg)

    # Smoothing
    result["Iq_smooth"] = smooth_profile(q, result["Iq_norm"], cfg)

    # Directional profiles (meridional / equatorial): same pipeline
    if result["Iq_merid"] is not None:
        # Use corrected if available, otherwise raw
        I_merid = result.get("Iq_merid_corrected", result["Iq_merid"])
        result["Iq_merid_corrected"] = I_merid
        result["Iq_merid_norm"] = normalize_intensity(I_merid, cfg)
        result["Iq_merid_smooth"] = smooth_profile(
            q, result["Iq_merid_norm"], cfg)
    if result["Iq_equat"] is not None:
        I_equat = result.get("Iq_equat_corrected", result["Iq_equat"])
        result["Iq_equat_corrected"] = I_equat
        result["Iq_equat_norm"] = normalize_intensity(I_equat, cfg)
        result["Iq_equat_smooth"] = smooth_profile(
            q, result["Iq_equat_norm"], cfg)

    # Sector data dict for downstream (e.g., strain analysis)
    result["sector_data"] = {
        "q": q,
        "I_full": result["Iq_smooth"],
        "I_merid": result.get("Iq_merid_smooth"),
        "I_equat": result.get("Iq_equat_smooth"),
    }

    return result


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _build_mask(img: np.ndarray, cfg: SAXSConfig) -> Optional[np.ndarray]:
    """Build a boolean mask for dummy pixels."""
    if np.isnan(cfg.dummy_val):
        return None
    return np.abs(img - cfg.dummy_val) < cfg.ddummy


def detect_beamstop_edge(
    q: np.ndarray, I: np.ndarray, cfg: SAXSConfig,
) -> Tuple[float, bool, Dict]:
    """Detect direct-beam pollution in the low-q region.

    Scans the low-q tail of I(q) for a characteristic power-law drop-off
    (I ∝ q^−α) that indicates the beamstop / direct-beam tail rather than
    genuine sample scattering.  When I(min_q) exceeds I(q_ref) by more than
    ``beamstop_pollution_threshold``, marks the data as contaminated and
    estimates the safe q-cutoff.

    Parameters
    ----------
    q, I : experimental scattering curve (smoothed).
    cfg  : SAXSConfig.

    Returns
    -------
    effective_q_min : float
        Recommended lower q bound for analysis (nm⁻¹).
    contaminated : bool
        True if beamstop pollution is detected.
    diag : dict
        Diagnostic fields: ``ratio``, ``method``, ``power_law_alpha``.
    """
    diag: Dict = {'ratio': 1.0, 'method': 'none', 'power_law_alpha': np.nan}
    if not cfg.auto_detect_beamstop or len(q) < 20 or not np.all(q > 0):
        return cfg.q_min, False, diag

    # Reference q ~0.2 nm⁻¹ where genuine lamellar scattering begins.
    q_ref_target = 0.20
    idx_ref = int(np.searchsorted(q, q_ref_target))
    if idx_ref >= len(q):
        idx_ref = len(q) - 1
    I_ref = float(I[idx_ref]) if I[idx_ref] > 0 else float(np.median(I[max(0, idx_ref-3):min(len(I), idx_ref+4)]))

    # Minimum-q region (first ~10 points above 0)
    n_low = min(15, len(q))
    q_low = q[:n_low]
    I_low = I[:n_low]

    I_min = float(np.max(I_low))  # worst-case pollution
    if I_ref <= 0:
        return cfg.q_min, False, diag

    ratio = I_min / I_ref
    diag['ratio'] = round(ratio, 1)

    if ratio < cfg.beamstop_pollution_threshold:
        # No pollution detected — keep configured q_min
        return cfg.q_min, False, diag

    # ---- Beamstop pollution detected ----
    # Fit a power law I ∝ q^−α in the low-q region to find the elbow
    valid = (I_low > 0) & (q_low > 0)
    if np.sum(valid) >= 5:
        log_q = np.log(q_low[valid])
        log_I = np.log(I_low[valid])
        try:
            p = np.polyfit(log_q, log_I, 1)
            alpha = -float(p[0])
            diag['power_law_alpha'] = round(alpha, 2)
        except Exception:
            alpha = np.nan
            logger.warning("异常已处理", exc_info=True)

    # Find the first q where I(q) drops below threshold * I_ref
    threshold_ratio = max(5.0, cfg.beamstop_pollution_threshold * 0.1)
    cutoff_idx = None
    for i in range(len(q)):
        if I[i] > 0 and I[i] < threshold_ratio * I_ref:
            cutoff_idx = i
            break

    if cutoff_idx is None:
        # Fallback: use q where ratio < 10
        for i in range(len(q)):
            if I[i] > 0 and I[i] < 10.0 * I_ref:
                cutoff_idx = i
                break

    if cutoff_idx is not None and cutoff_idx > 0:
        effective_q_min = float(q[cutoff_idx])
        # Safety: don't exceed 0.15 nm⁻¹ (too aggressive loses data)
        effective_q_min = min(effective_q_min, 0.15)
        diag['method'] = 'power_law_elbow'
    else:
        effective_q_min = 0.10
        diag['method'] = 'fallback'

    return effective_q_min, True, diag


def find_first_nonzero_q(q: np.ndarray, I: np.ndarray) -> float:
    """Return the smallest q value where I > 0 (simple mask-edge detection)."""
    for qi, Ii in zip(q, I):
        if Ii > 0:
            return float(qi)
    return float(q[0])
