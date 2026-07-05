"""NMR core analysis module.

Computes:
    - Peak detection & deconvolution (Gaussian / Lorentzian / mixed)
    - Chemical shift assignment against polymer database
    - Crystallinity quantification (crystalline/amorphous peak area ratio)
    - T1 / T2 relaxation fitting
    - CSA (Chemical Shift Anisotropy) analysis
    - Exp-Calc comparison (DFT shifts vs experiment)
"""
import logging
logger = logging.getLogger(__name__)


import numpy as np
from scipy import signal, optimize, stats
from scipy.ndimage import uniform_filter1d
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

from .io import NMRSpectrum, ComputedShift, NMRRelaxation
from .config import NMRConfig


# ---------------------------------------------------------------------------
#  Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class NMRResult:
    label: str = ""
    nucleus: str = "13C"
    sample_state: str = "solid"
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Peaks
    n_peaks: int = 0
    peaks: List[Dict[str, Any]] = field(default_factory=list)

    # Crystallinity
    Xc_pct: float = np.nan
    Xc_method: str = ""

    # Physical peak/region metrics
    peak_area_total: float = np.nan
    dominant_peak_ppm: float = np.nan
    mean_fwhm_ppm: float = np.nan
    median_snr: float = np.nan
    region_integrals: Dict[str, float] = field(default_factory=dict)
    quality_metrics: Dict[str, float] = field(default_factory=dict)

    # Relaxation
    relaxation: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Computational comparison
    computed_shifts: List[ComputedShift] = field(default_factory=list)
    matches: List[Dict[str, Any]] = field(default_factory=list)

    # Fit quality
    r_squared: float = np.nan

    # Raw data
    ppm: np.ndarray = field(default_factory=lambda: np.array([]))
    intensity: np.ndarray = field(default_factory=lambda: np.array([]))
    intensity_fit: np.ndarray = field(default_factory=lambda: np.array([]))

    @property
    def parameters(self) -> Dict[str, Any]:
        p = {'nucleus': self.nucleus, 'sample_state': self.sample_state,
             'n_peaks': self.n_peaks, 'Xc_pct': self.Xc_pct,
             'Xc_method': self.Xc_method,
             'peak_area_total': self.peak_area_total,
             'dominant_peak_ppm': self.dominant_peak_ppm,
             'mean_fwhm_ppm': self.mean_fwhm_ppm,
             'median_snr': self.median_snr,
             'r_squared': self.r_squared, 'n_matches': len(self.matches)}
        for key, val in self.region_integrals.items():
            p[f'region_{_slug_key(key)}_pct'] = val
        for key, val in self.quality_metrics.items():
            p[f'quality_{_slug_key(key)}'] = val
        peak_total = max(len(self.peaks), 1)
        phase_assigned = [
            pk for pk in self.peaks
            if str(pk.get('phase', '') or '').strip().lower() not in {'', 'unknown', 'none'}
        ]
        generic_assigned = [
            pk for pk in self.peaks
            if str(pk.get('assignment', '') or '').strip().endswith(('C', 'H'))
            or 'region' in str(pk.get('assignment', '') or '').strip().lower()
        ]
        solvent_peaks = [pk for pk in self.peaks if pk.get('possible_solvent')]
        p['assigned_peak_fraction'] = len(phase_assigned) / peak_total
        p['generic_assignment_fraction'] = len(generic_assigned) / peak_total
        p['solvent_peak_count'] = len(solvent_peaks)
        p['phase_assignment_count'] = len(phase_assigned)
        p['assignment_source'] = 'polymer_db' if phase_assigned else ('generic_region' if self.peaks else '')
        for i, pk in enumerate(self.peaks[:10]):
            p[f'peak_{i}_ppm'] = pk.get('ppm', np.nan)
            p[f'peak_{i}_assignment'] = pk.get('assignment', '')
            p[f'peak_{i}_phase'] = pk.get('phase', '')
            p[f'peak_{i}_delta_ppm'] = pk.get('delta_ppm', np.nan)
            p[f'peak_{i}_fwhm_ppm'] = pk.get('fwhm_ppm', np.nan)
            p[f'peak_{i}_area'] = pk.get('area', np.nan)
            p[f'peak_{i}_integral_norm'] = pk.get('integral_norm', np.nan)
            p[f'peak_{i}_snr'] = pk.get('snr', np.nan)
            p[f'peak_{i}_region'] = pk.get('region', '')
            p[f'peak_{i}_possible_solvent'] = pk.get('possible_solvent', '')
        for key, val in self.relaxation.items():
            p[f'{key}_value'] = val.get('fitted_value', np.nan)
            p[f'{key}_r2'] = val.get('r_squared', np.nan)
        return {k: v for k, v in p.items()
                if not (isinstance(v, float) and np.isnan(v))}


# ---------------------------------------------------------------------------
#  Physical helper functions
# ---------------------------------------------------------------------------

def _slug_key(value: str) -> str:
    text = str(value or "").strip().lower()
    out = []
    for ch in text:
        out.append(ch if ch.isalnum() else "_")
    return "_".join("".join(out).split("_")).strip("_") or "unknown"


def _safe_float(value: Any, default: float = np.nan) -> float:
    try:
        val = float(value)
        return val if np.isfinite(val) else default
    except Exception:
        return default
        logger.warning("异常已处理", exc_info=True)


def _robust_noise(intensity: np.ndarray) -> float:
    y = np.asarray(intensity, dtype=float)
    y = y[np.isfinite(y)]
    if y.size < 8:
        return np.nan
    smooth = uniform_filter1d(y, size=max(5, min(101, y.size // 40)), mode="nearest")
    resid = y - smooth
    mad = np.nanmedian(np.abs(resid - np.nanmedian(resid)))
    noise = 1.4826 * mad
    if not np.isfinite(noise) or noise <= 1e-12:
        noise = np.nanstd(resid)
    return float(noise) if np.isfinite(noise) and noise > 1e-12 else np.nan


def _positive_area(ppm: np.ndarray, intensity: np.ndarray) -> float:
    x = np.asarray(ppm, dtype=float)
    y = np.asarray(intensity, dtype=float)
    valid = np.isfinite(x) & np.isfinite(y)
    if valid.sum() < 2:
        return 0.0
    x = x[valid]
    y = np.clip(y[valid], 0.0, None)
    order = np.argsort(x)
    return abs(float(np.trapezoid(y[order], x[order])))


def _peak_windows(nucleus: str, sample_state: str) -> List[Tuple[str, float, float]]:
    nuc = (nucleus or "13C").upper()
    state = (sample_state or "solid").lower()
    if nuc in {"1H", "H"}:
        if state == "liquid":
            return [
                ("aldehyde_acid_H", 9.0, 12.5),
                ("aromatic_amide_H", 6.5, 9.0),
                ("alkenyl_H", 5.2, 6.5),
                ("O_N_adjacent_H", 3.2, 5.2),
                ("allylic_alpha_H", 2.0, 3.2),
                ("aliphatic_H", -0.5, 2.0),
            ]
        return [
            ("broad_downfield_H", 10.0, 20.0),
            ("aromatic_alkenyl_H", 5.0, 10.0),
            ("O_N_adjacent_H", 2.8, 5.0),
            ("aliphatic_H", -5.0, 2.8),
        ]
    if state == "liquid":
        return [
            ("aldehyde_ketone_C", 185.0, 220.0),
            ("ester_amide_carbonyl_C", 160.0, 185.0),
            ("aromatic_C", 120.0, 160.0),
            ("alkenyl_acetal_C", 90.0, 120.0),
            ("O_N_adjacent_C", 50.0, 90.0),
            ("aliphatic_C", -10.0, 50.0),
        ]
    return [
        ("carbonyl_C", 155.0, 240.0),
        ("aromatic_alkenyl_C", 90.0, 155.0),
        ("O_N_adjacent_C", 45.0, 90.0),
        ("aliphatic_C", -20.0, 45.0),
    ]


def _region_for_peak(ppm: float, nucleus: str, sample_state: str) -> str:
    for label, lo, hi in _peak_windows(nucleus, sample_state):
        if lo <= ppm <= hi:
            return label
    return "outside_default_range"


def _region_integral_percentages(ppm: np.ndarray, intensity: np.ndarray,
                                 nucleus: str, sample_state: str) -> Dict[str, float]:
    x = np.asarray(ppm, dtype=float)
    y = np.asarray(intensity, dtype=float)
    valid = np.isfinite(x) & np.isfinite(y)
    if valid.sum() < 2:
        return {}
    x = x[valid]
    y = y[valid]
    # After preprocess_pipeline baseline correction the spectrum baseline
    # should be near zero.  Estimate any residual offset from the lowest
    # 10 % of points rather than clipping at the 5th percentile.
    low_pts = y[y < np.nanpercentile(y, 10)]
    offset = float(np.nanmedian(low_pts)) if len(low_pts) > 0 else 0.0
    offset = max(offset, 0.0)  # only correct upward drift
    positive = np.clip(y - offset, 0.0, None)
    total = _positive_area(x, positive)
    if total <= 1e-12:
        return {}
    regions: Dict[str, float] = {}
    for label, lo, hi in _peak_windows(nucleus, sample_state):
        mask = (x >= lo) & (x <= hi)
        area = _positive_area(x[mask], positive[mask])
        if area > 0:
            regions[label] = float(area / total * 100.0)
    return regions


_SOLVENT_REFS = {
    "1H": [
        (7.26, "CDCl3_residual"),
        (2.50, "DMSO_d6_residual"),
        (3.31, "CD3OD_residual"),
        (4.87, "H2O_in_CD3OD"),
        (2.05, "acetone_d6_residual"),
        (1.94, "acetonitrile_d3_residual"),
    ],
    "13C": [
        (77.16, "CDCl3_residual"),
        (39.52, "DMSO_d6_residual"),
        (49.00, "CD3OD_residual"),
        (29.84, "acetone_d6_methyl"),
        (206.26, "acetone_d6_carbonyl"),
        (1.32, "acetonitrile_d3_methyl"),
        (118.26, "acetonitrile_d3_nitrile"),
    ],
}


def _possible_solvent(ppm: float, nucleus: str) -> str:
    nuc = "1H" if (nucleus or "").upper() in {"1H", "H"} else "13C"
    tol = 0.08 if nuc == "1H" else 0.6
    best = ""
    best_delta = tol
    for ref, label in _SOLVENT_REFS[nuc]:
        delta = abs(float(ppm) - ref)
        if delta <= best_delta:
            best = f"{label}@{ref:g}"
            best_delta = delta
    return best


def _finalise_peak_metrics(result: NMRResult) -> None:
    """Compute per-peak metrics, filter implausible peaks, and derive
    physical summary statistics (SNR, FWHM, region integrals from fit)."""

    noise = _robust_noise(result.intensity)
    nucleus = str(result.nucleus).upper()
    state = str(result.sample_state).lower()

    # --- physics-based bounds for the current experiment -------------------
    if nucleus in {"1H", "H"}:
        min_fwhm = 0.005 if state == "liquid" else 0.3
        max_fwhm = 5.0 if state == "liquid" else 60.0
    else:
        min_fwhm = 0.005 if state == "liquid" else 0.3
        max_fwhm = 20.0 if state == "liquid" else 40.0
    min_snr = 2.0  # SNR floor
    # -----------------------------------------------------------------------

    # ---- filter implausible peaks -----------------------------------------
    sane_peaks = []
    for pk in result.peaks:
        fwhm = _safe_float(pk.get("fwhm_ppm"))
        snr = _safe_float(pk.get("snr"))
        # Reject peaks with physically impossible FWHM
        if np.isfinite(fwhm) and (fwhm < min_fwhm or fwhm > max_fwhm):
            continue
        # Reject if SNR is too low (and noise is available)
        if np.isfinite(noise) and noise > 0 and np.isfinite(snr) and snr < min_snr:
            continue
        sane_peaks.append(pk)

    if sane_peaks:
        result.peaks = sane_peaks
        result.n_peaks = len(sane_peaks)
    else:
        # Keep original peaks if filtering removed everything
        pass
    # -----------------------------------------------------------------------

    total = 0.0
    for pk in result.peaks:
        area = _safe_float(pk.get("area_observed"), 0.0)
        if area <= 0:
            area = _safe_float(pk.get("area"), 0.0)
        area = max(area, 0.0)
        pk["area"] = area
        total += area
        pk["region"] = _region_for_peak(
            float(pk.get("ppm", np.nan)), result.nucleus, result.sample_state
        )
        solvent = _possible_solvent(float(pk.get("ppm", np.nan)), result.nucleus)
        if result.sample_state == "liquid" and solvent:
            pk["possible_solvent"] = solvent
        if not np.isfinite(_safe_float(pk.get("snr"))) and np.isfinite(noise) and noise > 0:
            pk["snr"] = _safe_float(pk.get("prominence"), 0.0) / noise

    if total > 0:
        for pk in result.peaks:
            pk["integral_norm"] = float(
                max(_safe_float(pk.get("area"), 0.0), 0.0) / total)
        result.peak_area_total = float(total)
        dominant = max(result.peaks,
                       key=lambda p: _safe_float(p.get("area"), 0.0))
        result.dominant_peak_ppm = _safe_float(dominant.get("ppm"))

    # --- region integrals from fitted peak areas (fallback: raw spectrum) --
    region_total: Dict[str, float] = {}
    for pk in result.peaks:
        reg = pk.get("region", "")
        if reg:
            region_total[reg] = region_total.get(reg, 0.0) + _safe_float(pk.get("area"), 0.0)
    if region_total and total > 1e-12:
        result.region_integrals = {
            k: float(v / total * 100.0) for k, v in region_total.items()
        }
    else:
        result.region_integrals = _region_integral_percentages(
            result.ppm, result.intensity, result.nucleus, result.sample_state
        )
    # -----------------------------------------------------------------------

    fwhm_values = [
        _safe_float(pk.get("fwhm_ppm"))
        for pk in result.peaks
        if np.isfinite(_safe_float(pk.get("fwhm_ppm")))
        and _safe_float(pk.get("fwhm_ppm")) > 0
    ]
    snr_values = [
        _safe_float(pk.get("snr"))
        for pk in result.peaks
        if np.isfinite(_safe_float(pk.get("snr")))
        and _safe_float(pk.get("snr")) > 0
    ]
    if fwhm_values:
        result.mean_fwhm_ppm = float(np.nanmean(fwhm_values))
    if snr_values:
        result.median_snr = float(np.nanmedian(snr_values))

    if np.isfinite(noise):
        result.quality_metrics["noise_mad"] = float(noise)
    if np.isfinite(result.r_squared):
        result.quality_metrics["r_squared"] = float(result.r_squared)
        if result.r_squared < 0.0:
            result.quality_metrics["fit_quality"] = -1.0  # error
        elif result.r_squared < 0.5:
            result.quality_metrics["fit_quality"] = 0.0   # poor
        elif result.r_squared < 0.9:
            result.quality_metrics["fit_quality"] = 1.0   # acceptable
        else:
            result.quality_metrics["fit_quality"] = 2.0   # good


# ---------------------------------------------------------------------------
#  Peak detection
# ---------------------------------------------------------------------------

def detect_peaks(ppm, intensity, height_frac=0.03, distance_ppm=1.0,
                 max_peaks=24, nucleus="13C", sample_state="liquid"):
    """Detect peaks in NMR spectrum.

    NMR convention: peaks are positive, ppm decreasing (high→low).

    Improvements over the naive find_peaks-only approach:
    - Adaptive height floor: ``noise * 3`` added so noise ripples are not
      mistaken for real peaks even when the dynamic range is small.
    - Physics-based width filter: candidates whose observed FWHM falls below
      the nucleus/state minimum are discarded before deconvolution.
    """
    if len(intensity) < 10:
        return []
    y = np.asarray(intensity, dtype=float)
    x = np.asarray(ppm, dtype=float)
    dynamic = np.nanmax(y) - np.nanmin(y)
    if not np.isfinite(dynamic) or dynamic <= 1e-12:
        return []
    noise = _robust_noise(y)
    dx = np.abs(np.mean(np.diff(x)))
    if not np.isfinite(dx) or dx <= 0:
        return []

    # --- physics-based minimum FWHM (in ppm) -------------------------------
    _nuc = str(nucleus).upper()
    _state = str(sample_state).lower()
    if _nuc in {"1H", "H"}:
        _min_fwhm = 0.005 if _state == "liquid" else 0.3
    else:
        _min_fwhm = 0.005 if _state == "liquid" else 0.3
    # ----------------------------------------------------------------------

    # adaptive height floor — never trust peaks barely above noise
    noise_floor = noise * 2.0 if np.isfinite(noise) and noise > 0 else 0.0
    min_h = np.nanmin(y) + max(height_frac * dynamic, noise_floor)
    min_prominence = max(height_frac * dynamic * 0.3, noise_floor * 0.3, 1e-12)
    peak_idx, props = signal.find_peaks(
        y, height=min_h, prominence=min_prominence,
        distance=max(1, int(distance_ppm / dx)),
    )
    if len(peak_idx) == 0:
        return []

    # ---- width pre-filter (discard before we even rank) -------------------
    try:
        widths, _, left_ips, right_ips = signal.peak_widths(
            y, peak_idx, rel_height=0.5)
    except Exception:
        widths = np.full(len(peak_idx), np.nan)
        left_ips = np.asarray(peak_idx, dtype=float)
        right_ips = np.asarray(peak_idx, dtype=float)
        logger.warning("异常已处理", exc_info=True)

    fwhm_candidates = np.array([
        float(widths[i] * dx) if np.isfinite(widths[i]) else np.nan
        for i in range(len(peak_idx))
    ])
    width_mask = np.isnan(fwhm_candidates) | (fwhm_candidates >= _min_fwhm)
    peak_idx = peak_idx[width_mask]
    fwhm_candidates = fwhm_candidates[width_mask]
    props = {k: np.asarray(v)[width_mask] for k, v in props.items()
             if len(np.asarray(v)) == len(width_mask)}
    if len(peak_idx) == 0:
        return []
    # -----------------------------------------------------------------------

    if len(peak_idx) > max_peaks:
        prominences = props.get('prominences', np.ones_like(peak_idx, dtype=float))
        keep = np.argsort(prominences)[-max_peaks:]
        keep = keep[np.argsort(peak_idx[keep])]
        peak_idx = peak_idx[keep]
        fwhm_candidates = fwhm_candidates[keep]
        props = {k: np.asarray(v)[keep] for k, v in props.items()
                 if len(np.asarray(v)) == len(prominences)}

    peaks = []
    for i, idx in enumerate(peak_idx):
        left = max(0, int(idx) - 2)
        right = min(len(y), int(idx) + 3)
        local_y = y[left:right]
        local_x = x[left:right]
        local_floor = np.nanpercentile(local_y, 10) if len(local_y) else 0.0
        prominence = float(props['prominences'][i]) if 'prominences' in props else 0.0
        obs_fwhm = float(fwhm_candidates[i]) if i < len(fwhm_candidates) else np.nan
        peaks.append({
            'index': i, 'idx': int(idx),
            'ppm': float(x[idx]), 'height': float(y[idx]),
            'prominence': prominence,
            'fwhm_ppm_observed': obs_fwhm,
            'area_observed': _positive_area(local_x, local_y - local_floor),
            'snr': float(prominence / noise) if np.isfinite(noise) and noise > 0 else np.nan,
        })
    return peaks


# ---------------------------------------------------------------------------
#  Peak deconvolution
# ---------------------------------------------------------------------------

def deconvolve_peaks(ppm, intensity, peaks, method='mixed',
                     nucleus="13C", sample_state="liquid"):
    """Multi-peak deconvolution using lmfit (L1-compliant).

    Wraps :func:`_fit_region_peaks` for backward compatibility.
    """
    return _fit_region_peaks(ppm, intensity, peaks, method, nucleus, sample_state)


def _fit_region_peaks(ppm, intensity, peaks, method='mixed',
                       nucleus="13C", sample_state="liquid"):
    """Fit peaks within one chemical-shift region using lmfit directly.

    L1-compliant (v4.0 §1.2): uses lmfit GaussianModel / LorentzianModel /
    PseudoVoigtModel.  Per-peak sigma initial guesses come from the
    observed FWHM of each detected peak, not from the global span.

    Returns ``(fitted_peaks, r_squared, y_pred)``.
    """
    if not peaks or len(ppm) < 10:
        return [], np.nan, np.array([])

    import lmfit
    from lmfit.models import GaussianModel, LorentzianModel, PseudoVoigtModel, ConstantModel

    x = np.asarray(ppm, dtype=float)
    y = np.asarray(intensity, dtype=float)

    _nuc = str(nucleus).upper()
    _state = str(sample_state).lower()
    if _nuc in {"1H", "H"}:
        sigma_min = 0.002 if _state == "liquid" else 0.15
    else:
        sigma_min = 0.05 if _state == "liquid" else 0.15

    span = abs(float(np.nanmax(x) - np.nanmin(x)))
    sigma_max = max(span, sigma_min * 20.0)

    if method == 'gaussian':
        peak_cls = GaussianModel
    elif method == 'lorentzian':
        peak_cls = LorentzianModel
    else:
        peak_cls = PseudoVoigtModel

    # Build composite model: constant baseline + N peaks
    composite = ConstantModel(prefix="bl_")
    for i, pk in enumerate(peaks):
        composite += peak_cls(prefix=f"p{i}_")

    params = composite.make_params()
    params["bl_c"].set(value=float(np.percentile(y, 5)))

    for i, pk in enumerate(peaks):
        center = float(pk['ppm'])
        amp = max(float(pk['height']), 0.001)
        obs_fwhm = _safe_float(pk.get('fwhm_ppm_observed'))
        # use observed FWHM if available and physically plausible;
        # otherwise start from a reasonable guess (1 ppm for 13C, 0.05 for 1H)
        if np.isfinite(obs_fwhm) and obs_fwhm > sigma_min:
            sigma = obs_fwhm / 2.355
        else:
            sigma = max(sigma_min * 3, 0.5 if _nuc not in {"1H", "H"} else 0.02)
        sigma = min(max(sigma, sigma_min), sigma_max)

        params[f"p{i}_center"].set(value=center, min=float(np.nanmin(x)),
                                   max=float(np.nanmax(x)))
        params[f"p{i}_amplitude"].set(value=amp, min=0)
        params[f"p{i}_sigma"].set(value=sigma, min=sigma_min, max=sigma_max)
        if method == 'mixed':
            params[f"p{i}_fraction"].set(value=0.5, min=0, max=1)

    try:
        fit_result = composite.fit(y, params, x=x, method="leastsq",
                                   max_nfev=10000)
    except Exception:
        fit_result = None
        logger.warning("异常已处理", exc_info=True)

    if fit_result is None:
        # fallback: use detected peaks as-is
        fitted = []
        for i, pk in enumerate(peaks):
            fitted.append({
                'index': i, 'ppm': float(pk['ppm']),
                'height': float(pk['height']),
                'fwhm_ppm': _safe_float(pk.get('fwhm_ppm_observed'), 0.5),
                'area': _safe_float(pk.get('area_observed'), 0.0),
                'fit_area': 0.0,
                'area_observed': _safe_float(pk.get('area_observed'), 0.0),
                'fwhm_ppm_observed': pk.get('fwhm_ppm_observed', np.nan),
                'snr': pk.get('snr', np.nan),
                'prominence': pk.get('prominence', np.nan),
                'frac_lorentz': 0.5, 'assignment': '',
                'fit_failed': True,
            })
        return fitted, np.nan, np.array([])

    y_pred = fit_result.best_fit
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0

    fitted = []
    for i, pk in enumerate(peaks):
        c = float(fit_result.params[f"p{i}_center"].value)
        a = float(fit_result.params[f"p{i}_amplitude"].value)
        s = float(fit_result.params[f"p{i}_sigma"].value)
        fwhm = float(fit_result.params[f"p{i}_fwhm"].value)
        frac = (float(fit_result.params[f"p{i}_fraction"].value)
                if method == 'mixed' else 0.5)
        # lmfit reports area for pseudo-voigt; for gauss/lorentz compute
        if method == 'gaussian':
            area = a * s * np.sqrt(2 * np.pi)
        elif method == 'lorentzian':
            area = np.pi * a * s
        else:
            # lmfit PseudoVoigtModel: area ≈ amplitude * sigma * sqrt(pi)
            # (approximation; exact depends on fraction)
            try:
                area = float(a * s * np.sqrt(np.pi))
            except Exception:
                area = a * s * 1.77
                logger.warning("异常已处理", exc_info=True)

        fitted.append({
            'index': i, 'ppm': c, 'height': a,
            'fwhm_ppm': fwhm, 'area': float(area),
            'fit_area': float(area),
            'area_observed': _safe_float(pk.get('area_observed'), 0.0),
            'fwhm_ppm_observed': pk.get('fwhm_ppm_observed', np.nan),
            'snr': pk.get('snr', np.nan),
            'prominence': pk.get('prominence', np.nan),
            'frac_lorentz': frac, 'assignment': '',
            'fit_failed': False,
        })

    return fitted, float(r2), y_pred



# ---------------------------------------------------------------------------

def _generic_region_assignment(ppm: float, nucleus: str) -> str:
    nucleus = (nucleus or "13C").upper()
    if nucleus in {"1H", "H"}:
        regions = [
            (-0.5, 2.0, "aliphatic H"),
            (2.0, 3.2, "allylic/alpha hetero H"),
            (3.2, 5.2, "O/N-adjacent H"),
            (5.2, 6.5, "alkenyl H"),
            (6.5, 9.0, "aromatic/amide H"),
            (9.0, 12.5, "aldehyde/acid H"),
        ]
    else:
        regions = [
            (-10.0, 50.0, "aliphatic C"),
            (50.0, 90.0, "O/N-adjacent C"),
            (90.0, 120.0, "alkenyl/acetal C"),
            (120.0, 160.0, "aromatic C"),
            (160.0, 185.0, "ester/amide carbonyl C"),
            (185.0, 220.0, "aldehyde/ketone carbonyl C"),
        ]
    for lo, hi, label in regions:
        if lo <= ppm <= hi:
            return label
    return "unassigned region"


def assign_peaks(peaks, polymer_db, polymer_name="", tolerance_ppm=2.0,
                 nucleus="13C", use_polymer_db: bool = True):
    """Match peaks to polymer 13C database or generic NMR regions."""
    use_polymer_db = use_polymer_db and (nucleus or "13C").upper() in {"13C", "C"}
    if polymer_name and polymer_name in polymer_db:
        dbs = {polymer_name: polymer_db[polymer_name]}
    else:
        dbs = polymer_db if use_polymer_db else {}

    for pk in peaks:
        wn = pk['ppm']
        best_match = None; best_dist = tolerance_ppm
        if use_polymer_db:
            for poly, entries in dbs.items():
                for group, (ref_ppm, phase, notes) in entries.items():
                    dist = abs(wn - ref_ppm)
                    if dist < best_dist:
                        best_dist = dist
                        best_match = {'assignment': f"{group} ({phase})", 'delta_ppm': dist,
                                       'ref_ppm': ref_ppm, 'phase': phase, 'polymer': poly, 'notes': notes}
        if best_match:
            for k, v in best_match.items():
                pk[k] = v
        else:
            pk['assignment'] = _generic_region_assignment(float(wn), nucleus)
            pk['phase'] = 'unknown'
    return peaks


# ---------------------------------------------------------------------------
#  Crystallinity
# ---------------------------------------------------------------------------

def compute_crystallinity_nmr(peaks, crystalline_peaks, amorphous_peaks):
    """Crystallinity from peak area ratio.

    Xc = sum(area_crystalline) / sum(area_total) * 100
    """
    cryst_area = sum(pk.get('area', 0) for pk in peaks
                     if pk.get('phase') in crystalline_peaks)
    am_area = sum(pk.get('area', 0) for pk in peaks
                  if pk.get('phase') in amorphous_peaks)
    if cryst_area > 0 and am_area > 0:
        return cryst_area / (cryst_area + am_area) * 100.0
    return np.nan


# ---------------------------------------------------------------------------
#  Relaxation analysis
# ---------------------------------------------------------------------------

def fit_t1_recovery(delays, intensities):
    """Fit T1 inversion-recovery: I(t) = I0 * (1 - 2*exp(-t/T1))."""
    if len(delays) < 3:
        return {'T1_s': np.nan, 'I0': np.nan, 'r_squared': np.nan}

    delays = np.asarray(delays)
    intensities = np.asarray(intensities)
    valid = np.isfinite(delays) & np.isfinite(intensities)
    delays = delays[valid]; intensities = intensities[valid]

    def model(t, I0, T1):
        return I0 * (1.0 - 2.0 * np.exp(-t / max(T1, 1e-9)))

    try:
        popt, _ = optimize.curve_fit(model, delays, intensities,
                                      p0=[np.max(intensities), 1.0], maxfev=5000)
        y_pred = model(delays, *popt)
        ss_res = np.sum((intensities - y_pred)**2)
        ss_tot = np.sum((intensities - np.mean(intensities))**2)
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
        return {'T1_s': float(abs(popt[1])), 'I0': float(popt[0]), 'r_squared': float(r2)}
    except Exception:
        return {'T1_s': np.nan, 'I0': np.nan, 'r_squared': np.nan}
        logger.warning("异常已处理", exc_info=True)


def fit_t2_decay(delays, intensities):
    """Fit T2 CPMG decay: I(t) = I0 * exp(-t/T2)."""
    if len(delays) < 3:
        return {'T2_s': np.nan, 'I0': np.nan, 'r_squared': np.nan}

    delays = np.asarray(delays)
    intensities = np.asarray(intensities)

    def model(t, I0, T2):
        return I0 * np.exp(-t / max(T2, 1e-9))

    try:
        popt, _ = optimize.curve_fit(model, delays, intensities,
                                      p0=[np.max(intensities), 0.1], maxfev=5000)
        y_pred = model(delays, *popt)
        ss_res = np.sum((intensities - y_pred)**2)
        ss_tot = np.sum((intensities - np.mean(intensities))**2)
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
        return {'T2_s': float(abs(popt[1])), 'I0': float(popt[0]), 'r_squared': float(r2)}
    except Exception:
        return {'T2_s': np.nan, 'I0': np.nan, 'r_squared': np.nan}
        logger.warning("异常已处理", exc_info=True)


# ---------------------------------------------------------------------------
#  Exp-Calc comparison
# ---------------------------------------------------------------------------

def match_computed_shifts(peaks, computed_shifts, tolerance_ppm=3.0):
    """Match DFT-computed shifts to experimental peaks."""
    matches = []
    used = set()
    for pk in peaks:
        best = None; best_dist = tolerance_ppm
        for cs in computed_shifts:
            if cs.index in used:
                continue
            dist = abs(pk['ppm'] - cs.shift_ppm)
            if dist < best_dist:
                best_dist = dist; best = cs
        if best:
            used.add(best.index)
            matches.append({
                'exp_ppm': pk['ppm'], 'calc_ppm': best.shift_ppm,
                'delta_ppm': best_dist,
                'exp_assignment': pk.get('assignment', ''),
                'calc_assignment': best.assignment,
                'span_ppm': best.span_ppm, 'skew': best.skew,
            })
    return matches


# ---------------------------------------------------------------------------
#  Full analysis
# ---------------------------------------------------------------------------

def analyze_spectrum(spectrum, config, label="",
                     computed_shifts=None, polymer_name="",
                     relaxation_data=None):
    """Run full NMR analysis."""
    nucleus = getattr(spectrum, 'nucleus', None) or config.nucleus
    sample_state = spectrum.metadata.get('sample_state', config.sample_state)
    polymer_name = polymer_name or getattr(config, "polymer_name", "")
    result = NMRResult(label=label, nucleus=nucleus, sample_state=sample_state,
                       metadata=dict(getattr(spectrum, 'metadata', {}) or {}))
    if not spectrum.has_data:
        return result

    ppm = spectrum.ppm; I = spectrum.intensity
    result.ppm = ppm; result.intensity = I

    # 1. Peak detection
    peak_distance = config.peak_distance_ppm
    if str(nucleus).upper() in {"1H", "H"} and peak_distance > 0.25:
        peak_distance = 0.08 if sample_state == "liquid" else 0.25
    peaks = detect_peaks(ppm, I, config.peak_height_min, peak_distance,
                         config.max_peaks, nucleus=nucleus,
                         sample_state=sample_state)

    # 2. Deconvolution
    if peaks:
        fitted, r2, I_fit = deconvolve_peaks(ppm, I, peaks, config.deconvolution_method,
                                            nucleus=nucleus,
                                            sample_state=sample_state)
        result.peaks = fitted; result.n_peaks = len(fitted)
        result.r_squared = r2; result.intensity_fit = I_fit

        # 3. Assignment
        scoped_polymer = bool(polymer_name)
        allow_unscoped = bool(getattr(config, "allow_unscoped_polymer_db_match", False))
        assign_peaks(
            result.peaks, config.polymer_13c_db, polymer_name,
            nucleus=nucleus,
            use_polymer_db=scoped_polymer or allow_unscoped,
        )
        _finalise_peak_metrics(result)

        # 4. Crystallinity
        if sample_state == "solid" and str(nucleus).upper() in {"13C", "C"}:
            result.Xc_pct = compute_crystallinity_nmr(
                result.peaks,
                list(getattr(config, "crystalline_phase_labels", ("c",))),
                list(getattr(config, "amorphous_phase_labels", ("a", "i"))),
            )
            if np.isfinite(result.Xc_pct):
                result.Xc_method = 'solid_13c_peak_area'
            else:
                result.Xc_method = 'requires_crystalline_amorphous_assignment'
    else:
        result.region_integrals = _region_integral_percentages(
            result.ppm, result.intensity, result.nucleus, result.sample_state
        )
        noise = _robust_noise(result.intensity)
        if np.isfinite(noise):
            result.quality_metrics["noise_mad"] = float(noise)

    # 5. Relaxation
    if relaxation_data and relaxation_data.delay_values is not None:
        for pk_ppm, pk_intensities in relaxation_data.intensities.items():
            delays = relaxation_data.delay_values
            if relaxation_data.relaxation_type == 'T1':
                fit = fit_t1_recovery(delays, pk_intensities)
                result.relaxation[f'{pk_ppm}_T1'] = fit
            else:
                fit = fit_t2_decay(delays, pk_intensities)
                result.relaxation[f'{pk_ppm}_T2'] = fit

    # 6. Computational comparison
    if computed_shifts:
        result.computed_shifts = computed_shifts
        if result.peaks:
            result.matches = match_computed_shifts(result.peaks, computed_shifts)

    return result
