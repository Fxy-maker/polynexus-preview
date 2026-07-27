"""
saxs.core — Module 3: Core calculation engine.

Long period via Bragg / correlation function / IDF / Lorentz fitting.
Multi-method voting with confidence-weighted ensemble.
Structure parameters: lc, la, crystallinity, specific surface.
Guinier, Porod, Kratky analyses.
sasmodels interface for model fitting.

All numerical methods are designed for accuracy, not just speed.
"""
# Legacy public intensity parameters intentionally use ``I`` throughout this
# module; keep Ruff's ambiguous-name warning local to this compatibility file.
# ruff: noqa: E741
from typing import Tuple, Dict, Optional, List, Any
from dataclasses import dataclass, field
import numpy as np
from scipy.signal import find_peaks, savgol_filter
from scipy.integrate import trapezoid

from ..engine import logger
from .config import SAXSConfig
from . import saxs_quality_helpers as _saxs_quality_helpers
from . import saxs_physical_helpers as _saxs_physical_helpers
from . import saxs_extrapolation_helpers as _saxs_extrapolation_helpers
from .saxs_quality_contracts import (
    MetricEvidence,
    QualityLevel,
    build_data_quality_report,
    build_guinier_evidence,
    build_porod_evidence,
    build_kratky_evidence,
    build_invariant_evidence,
    build_lamellar_evidence,
)


# ======================================================================
#  Result dataclasses
# ======================================================================

@dataclass
class LongPeriodResult:
    """Ensemble long period estimate with per-method results."""
    L_best: float = np.nan           # weighted ensemble (nm)
    L_confidence: float = 0.0        # 0-1 confidence score
    L_bragg: float = np.nan          # Bragg peak position
    L_lorentz: float = np.nan        # Lorentz-corrected peak
    L_corr_peak: float = np.nan      # correlation function first maximum
    L_guinier: float = np.nan        # Guinier extrapolation
    method_used: str = "none"

@dataclass
class StructureParams:
    """Structure parameters derived from SAXS."""
    L: float = np.nan              # long period (nm)
    lc: float = np.nan             # crystalline thickness (nm)
    la: float = np.nan             # amorphous thickness (nm)
    phi_c: float = np.nan           # linear crystallinity (lc/L)
    phi_c_invariant: float = np.nan # Porod-invariant crystallinity
    phi_c_vol: float = np.nan       # volumetric crystallinity
    Sv: float = np.nan              # specific surface (nm^-1)
    Q_invariant: float = np.nan     # scattering invariant
    lc_porod_nm: float = np.nan     # lc from invariant (diagnostic)
    lc_tangent_nm: float = np.nan   # lc from tangent method (diagnostic)
    lc_idf_nm: float = np.nan       # lc from IDF (diagnostic)
    lc_gamma_min_nm: float = np.nan # gamma(r) first minimum (diagnostic)
    confidence_lc: float = np.nan    # 0-1 confidence in lc estimate
    Rg: float = np.nan              # radius of gyration (nm)

@dataclass
class SAXSResult:
    """Complete SAXS analysis result for one sample/condition."""
    label: str = ""
    condition_value: float = np.nan   # temperature/strain/etc. for series
    q: np.ndarray = None
    I: np.ndarray = None  # noqa: E741
    I_smooth: np.ndarray = None
    long_period: LongPeriodResult = None
    structure: StructureParams = None
    raw_long_period: LongPeriodResult = None
    raw_structure: StructureParams = None
    raw_parameters: Dict[str, Any] = field(default_factory=dict)
    final_parameters: Dict[str, Any] = field(default_factory=dict)
    correlation: Dict = None       # gamma(r) data
    idf: Dict = None               # IDF data
    porod: Dict = None
    kratky: Dict = None
    # pyFAI shadow channel (cross-validation, never affects main results)
    q_pyfai: np.ndarray = None
    I_pyfai: np.ndarray = None
    L_bragg_pyfai: float = np.nan
    q_peak_pyfai: float = np.nan
    pyfai_q_peak_diff_pct: float = np.nan
    # Quality & validation fields
    quality_flag: str = ""               # e.g. "OK", "WARN:low_snr", "ERROR:qstar"
    validation_summary: str = ""         # human-readable diagnostic summary
    q_peak_snr: float = np.nan           # SNR of the lamellar peak region
    r_squared: float = np.nan            # curve-fit R² over effective peak/Guinier regions
    fit_rmse: float = np.nan             # normalized fit RMSE for the regions above
    fit_regions: List[Dict] = None       # per-region residual diagnostics
    r_squared_method: str = ""           # describes the scoring window
    quality_score: float = np.nan        # PHYS score; distinct from curve-fit R²
    data_quality_report: Dict[str, Any] = None
    guinier_evidence: Dict[str, Any] = None
    metric_evidence: Dict[str, Any] = None
    detector_quality_report: Dict[str, Any] = None
    orientation_evidence: Dict[str, Any] = None
    beam_stop_contaminated: bool = False # direct-beam pollution detected
    effective_q_min: float = 0.01        # q_min after beamstop-edge correction
    mask_truncated: bool = False         # effective q_min > 0.1 nm⁻¹
    Q_star_valid: bool = True            # False if beam-stop contaminates Q*
    sasmodels_model_used: str = ""       # which sasmodels model produced the fit


# ======================================================================
#  Long period: Bragg method
# ======================================================================

def bragg_long_period(
    q: np.ndarray, I: np.ndarray,
    q_min: float = 0.30, q_max: float = 1.0,
    prominence: float = 0.02,
    q_anchor: float | None = None,
    anchor_width: float = 0.08,
) -> Tuple[float, float, dict]:
    """Long period from Bragg peak: L = 2*pi / q_peak.

    Enhanced: q_anchor for series tracking, harmonic rejection, melting detection.
    Returns (L_nm, q_peak, info_dict).
    """
    info = {
        "melt_flag": False,
        "peak_count": 0,
        "snr": 0.0,
        "peak_q_list": [],
        "selected_reason": "none",
        "candidate_peaks": [],
    }

    mask = (q >= q_min) & (q <= q_max) & np.isfinite(q) & np.isfinite(I) & (I > 0)
    if np.sum(mask) < 5:
        return np.nan, np.nan, info

    q_sel = q[mask]
    I_sel = I[mask]
    I_lorentz = I_sel * q_sel ** 2

    I_range = np.max(I_lorentz) - np.min(I_lorentz)
    if I_range < 1e-12:
        return np.nan, np.nan, info

    # SNR for melting detection
    bg_region = q_sel >= q_sel[-1] * 0.8
    noise_rms = float(np.std(I_lorentz[bg_region])) if np.any(bg_region) else float(np.std(I_lorentz[-20:]))
    info["snr"] = (float(np.max(I_lorentz)) - float(np.min(I_lorentz))) / max(noise_rms, 1e-12)

    if info["snr"] < 3.0:
        info["melt_flag"] = True
        if q_anchor is not None:
            anchor_mask = np.abs(q_sel - q_anchor) <= anchor_width
            if np.sum(anchor_mask) > 3:
                best = np.argmax(I_lorentz[anchor_mask])
                q_peak = float(q_sel[anchor_mask][best])
                return 2 * np.pi / q_peak, q_peak, info
        return np.nan, np.nan, info

    I_norm = (I_lorentz - np.min(I_lorentz)) / I_range
    peaks, props = find_peaks(I_norm, prominence=prominence)

    if len(peaks) == 0:
        peaks, props = find_peaks(I_norm, prominence=prominence * 0.3)

    info["peak_count"] = len(peaks)
    info["peak_q_list"] = [float(q_sel[p]) for p in peaks]

    if len(peaks) == 0:
        # Avoid choosing the beam-stop / void upturn when no formal peak is found.
        upper = q_sel >= max(0.25, np.median(q_sel))
        if np.sum(upper) > 2:
            idx = np.argmax(I_lorentz[upper])
            q_peak = float(q_sel[upper][idx])
        else:
            idx = np.argmax(I_lorentz)
            q_peak = float(q_sel[idx])
        L = 2 * np.pi / q_peak if q_peak > 0 else np.nan
        info["selected_reason"] = "max_no_peak"
        return L, q_peak, info

    candidates = []
    prominences = props.get("prominences", np.ones(len(peaks)))
    max_prom = float(np.max(prominences)) if len(prominences) else 1.0
    for i, p in enumerate(peaks):
        qp = float(q_sel[p])
        Lp = 2 * np.pi / qp if qp > 0 else np.nan
        prom = float(prominences[i])
        height = float(I_norm[p])
        low_q_penalty = 0.0
        if qp < 0.18:
            low_q_penalty = 3.0
        elif qp < 0.25:
            low_q_penalty = 1.5
        candidates.append({
            "idx": int(p),
            "q": qp,
            "L": float(Lp),
            "prominence": prom,
            "height": height,
            "relative_prominence": prom / max(max_prom, 1e-12),
            "low_q_penalty": low_q_penalty,
        })
    info["candidate_peaks"] = [
        {k: v for k, v in c.items() if k != "idx"} for c in candidates
    ]

    # Anchor-aware selection with harmonic rejection.
    if q_anchor is not None and q_anchor > 0:
        best_peak, best_score = None, -np.inf
        for c in candidates:
            qp = c["q"]
            dist = abs(qp - q_anchor) / q_anchor
            harmonic_penalty = 1.0 if abs(qp / q_anchor - 2.0) < 0.25 else 0.0
            low_q_penalty = 0.0 if dist < 0.30 else c["low_q_penalty"]
            score = (
                c["relative_prominence"] / (dist + 0.03)
                + 0.25 * c["height"]
                - harmonic_penalty * 10
                - low_q_penalty
            )
            if score > best_score:
                best_score, best_peak = score, qp
        if best_peak is not None and best_score > -5:
            info["selected_reason"] = "anchor_score"
            return 2 * np.pi / best_peak, best_peak, info

    # Default: choose the best credible lamellar peak.  Very-low-q peaks are
    # penalized because they often come from void/upturn scattering, not the
    # lamellar repeat.  q_anchor above handles true long-period tracking in
    # ordered series.
    credible = [
        c for c in candidates
        if c["q"] >= 0.25
        and 4.0 <= c["L"] <= 30.0
        and c["relative_prominence"] >= 0.25
    ]
    if credible:
        def _candidate_score(c):
            low_q_soft_penalty = 0.0
            if c["q"] < 0.35:
                low_q_soft_penalty = 0.55
            elif c["q"] < 0.45:
                low_q_soft_penalty = 0.20
            return c["relative_prominence"] + 0.25 * c["height"] - low_q_soft_penalty

        credible.sort(key=lambda c: (_candidate_score(c), -c["q"]), reverse=True)
        q_peak = float(credible[0]["q"])
        info["selected_reason"] = "best_credible_lamellar"
    else:
        scored = []
        for c in candidates:
            score = c["relative_prominence"] + 0.25 * c["height"] - c["low_q_penalty"]
            scored.append((score, c))
        scored.sort(key=lambda x: x[0], reverse=True)
        q_peak = float(scored[0][1]["q"])
        info["selected_reason"] = "best_score"

    L = 2 * np.pi / q_peak if q_peak > 0 else np.nan
    return L, q_peak, info




# ======================================================================
#  Scattering invariant
# ======================================================================

def scattering_invariant(
    q: np.ndarray, I: np.ndarray,
    q_min: float | None = None, q_max: float | None = None,
    cfg: Optional[SAXSConfig] = None,
) -> float:
    """Compute the scattering invariant Q* = integral(q^2 * I(q), dq).

    The invariant is proportional to the mean-square electron density
    fluctuation and is conserved during phase transitions (when no
    density change occurs).

    For two-phase systems: Q* = 2*pi^2 * (delta_rho)^2 * phi * (1-phi)

    Parameters
    ----------
    q : ndarray, I : ndarray
    q_min, q_max : float, optional
        Integration bounds. If None, use full q range.

    Returns
    -------
    float : Scattering invariant Q*.
    """
    if cfg is not None:
        if q_min is None:
            q_min = getattr(cfg, "q_min", None)
        if q_max is None:
            q_max = getattr(cfg, "q_max", None)

    if q_min is not None:
        mask = (q >= q_min)
    else:
        mask = np.ones_like(q, dtype=bool)
    if q_max is not None:
        mask &= (q <= q_max)

    q_int = q[mask]
    I_int = I[mask]

    if len(q_int) < 2:
        return np.nan

    # Q* = integral of q^2 * I(q) dq  (trapezoidal integration)
    integrand = q_int ** 2 * I_int
    return float(np.trapezoid(integrand, q_int))



def lorentz_fit_long_period(
    q: np.ndarray, I: np.ndarray,
    cfg: SAXSConfig,
    q_min: float | None = None,
    q_max: float | None = None,
) -> Tuple[float, float, dict]:
    """Fit Lorentz-corrected I*q^2 vs q with one Lorentzian.

    Uses lmfit for constrained fitting with error estimates.
    Smart initial guess based on Bragg peak position to avoid spurious fits.

    Returns (L_nm, fit_quality_r2, fit_result_dict).
    """
    try:
        from lmfit.models import LorentzianModel, ConstantModel
    except ImportError:
        return _lorentz_fallback(q, I, cfg, q_min=q_min, q_max=q_max)

    q_corr_min = cfg.q_corr_min
    if q_min is not None:
        q_corr_min = max(q_corr_min, float(q_min))
    q_corr_max = min(cfg.q_corr_max, q[-1])
    if q_max is not None:
        q_corr_max = min(q_corr_max, float(q_max))

    mask = (q >= q_corr_min) & (q <= q_corr_max)
    if np.sum(mask) < 10:
        return np.nan, 0.0, {'q_corr_min': q_corr_min, 'q_corr_max': q_corr_max}

    q_sel = q[mask]
    I_sel = I[mask]
    Iq2 = I_sel * q_sel ** 2

    # First find Bragg peak to narrow search range
    from scipy.signal import find_peaks
    Iq2_smooth = savgol_filter(Iq2, min(11, len(q_sel)//4*2+1), 2)
    peaks, props = find_peaks(Iq2_smooth, prominence=0.02 * np.max(Iq2_smooth))

    if len(peaks) > 0:
        best_peak = peaks[np.argmax(Iq2_smooth[peaks])]
        q_bragg = q_sel[best_peak]
        # Narrow search to +/-30% around Bragg peak
        search_min = max(q_corr_min, q_bragg * 0.7)
        search_max = min(q_corr_max, q_bragg * 1.3)
    else:
        search_min = q_corr_min
        search_max = q_corr_max
        q_bragg = (search_min + search_max) / 2

    # Fit Lorentzian in narrow window
    fit_mask = (q_sel >= search_min) & (q_sel <= search_max)
    if np.sum(fit_mask) < 5:
        return np.nan, 0.0, {'q_corr_min': q_corr_min, 'q_corr_max': q_corr_max}

    q_fit = q_sel[fit_mask]
    I_fit = Iq2_smooth[fit_mask] if len(Iq2_smooth) == len(q_sel) else Iq2[fit_mask]
    I_max = np.max(I_fit)

    mod = ConstantModel(prefix='bg_') + LorentzianModel(prefix='l1_')
    params = mod.make_params(
        bg_c=np.min(I_fit),
        l1_center=q_bragg,
        l1_sigma=0.03,
        l1_amplitude=I_max * 0.03 * np.pi,
    )
    params['l1_center'].set(min=search_min, max=search_max)
    params['l1_sigma'].set(min=0.005, max=0.3)
    params['l1_amplitude'].set(min=0)

    result = mod.fit(I_fit, params, x=q_fit)

    q_peak = result.params['l1_center'].value
    L = 2 * np.pi / q_peak if q_peak > 0 else np.nan

    ss_res = np.sum((result.residual) ** 2)
    ss_tot = np.sum((I_fit - np.mean(I_fit)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

    # Quality gate: reject poor fits (R² < 0.7 indicates fit is not reliable)
    if r2 < 0.70:
        fit_info = {
            'r2': r2, 'n_points': np.sum(fit_mask),
            'rejected': True, 'reason': 'R2 < 0.70'
        }
        return np.nan, r2, fit_info

    fit_info = {
        'q_peak': q_peak, 'q_peak_stderr': result.params['l1_center'].stderr,
        'r2': r2, 'n_points': np.sum(fit_mask), 'rejected': False,
        'sigma': result.params['l1_sigma'].value,
        'amplitude': result.params['l1_amplitude'].value,
        'q_corr_min': q_corr_min,
        'q_corr_max': q_corr_max,
    }

    return L, r2, fit_info


def _lorentz_fallback(
    q: np.ndarray,
    I: np.ndarray,
    cfg: SAXSConfig,
    q_min: float | None = None,
    q_max: float | None = None,
) -> Tuple[float, float, dict]:
    """Fallback Lorentz fitting without lmfit (scipy curve_fit)."""
    from scipy.optimize import curve_fit

    q_corr_min = cfg.q_corr_min
    if q_min is not None:
        q_corr_min = max(q_corr_min, float(q_min))
    q_corr_max = min(cfg.q_corr_max, q[-1])
    if q_max is not None:
        q_corr_max = min(q_corr_max, float(q_max))

    mask = (q >= q_corr_min) & (q <= q_corr_max)
    if np.sum(mask) < 10:
        return np.nan, 0.0, {}

    q_sel = q[mask]
    I_sel = I[mask]
    Iq2 = I_sel * q_sel ** 2

    def lorentz(x, amp, cen, sigma, bg):
        return amp / (1 + ((x - cen) / sigma) ** 2) + bg

    q_guess = q_sel[np.argmax(Iq2)]
    p0 = [np.max(Iq2) * 0.05 * np.pi, q_guess, 0.05, np.min(Iq2)]

    try:
        popt, _ = curve_fit(lorentz, q_sel, Iq2, p0=p0,
                           bounds=([0, q_corr_min, 0.005, -np.inf],
                                   [np.inf, q_corr_max, 0.5, np.inf]),
                           maxfev=2000)
        L = 2 * np.pi / popt[1] if popt[1] > 0 else np.nan
        Iq2_pred = lorentz(q_sel, *popt)
        ss_res = np.sum((Iq2 - Iq2_pred) ** 2)
        ss_tot = np.sum((Iq2 - np.mean(Iq2)) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

        # Quality gate: reject poor fits (R² < 0.7 indicates fit is not reliable)
        if r2 < 0.70:
            return np.nan, r2, {'q_peak': popt[1], 'r2': r2,
                                'rejected': True, 'reason': 'R2 < 0.70'}
        return L, r2, {
            'q_peak': popt[1],
            'q_corr_min': q_corr_min,
            'q_corr_max': q_corr_max,
        }
    except Exception:
        logger.warning("SAXS Lorentz fallback fit failed.", exc_info=True)
        return np.nan, 0.0, {}


def _saxs_peak_region_fit_quality(
    q: np.ndarray,
    I: np.ndarray,
    cfg: SAXSConfig,
    q_bragg_min: float,
    q_bragg_max: float,
    q_guinier: np.ndarray | None = None,
    lnI_guinier: np.ndarray | None = None,
) -> Dict:
    """Compute curve-fit R² only in SAXS information-bearing regions.

    The Bragg peak is fitted in Lorentz-corrected space (I*q²) over the
    configured lamellar peak window.  Optional Guinier residuals are added in
    log-intensity space.  Porod/high-q tails are intentionally excluded.
    """
    regions: List[Dict] = []

    bragg = _fit_bragg_region(q, I, q_bragg_min, q_bragg_max)
    if bragg:
        regions.append(bragg)

    guinier = _fit_guinier_region(q_guinier, lnI_guinier)
    if guinier:
        regions.append(guinier)

    ss_tot = float(sum(region["ss_tot"] for region in regions))
    if ss_tot <= 1e-12:
        return {
            "r_squared": 0.0,
            "fit_rmse": np.nan,
            "fit_regions": regions,
            "method": "saxs_peak_region_fit_r2",
        }

    ss_res = float(sum(region["ss_res"] for region in regions))
    n_points = int(sum(region["n_points"] for region in regions))
    r_squared = 1.0 - ss_res / ss_tot
    fit_rmse = float(np.sqrt(ss_res / max(n_points, 1)))
    return {
        "r_squared": float(r_squared),
        "fit_rmse": fit_rmse,
        "fit_regions": [
            {key: value for key, value in region.items() if key not in {"ss_res", "ss_tot"}}
            for region in regions
        ],
        "method": "saxs_peak_region_fit_r2",
    }


def _fit_bragg_region(q: np.ndarray, I: np.ndarray, q_min: float, q_max: float) -> Dict | None:
    mask = (
        np.isfinite(q)
        & np.isfinite(I)
        & (q >= q_min)
        & (q <= q_max)
        & (q > 0)
        & (I > 0)
    )
    if np.sum(mask) < 12:
        return None

    x = q[mask].astype(float)
    y_raw = (I[mask] * x**2).astype(float)
    y_min = float(np.min(y_raw))
    y_span = float(np.max(y_raw) - y_min)
    if y_span <= 1e-12:
        return None
    y = (y_raw - y_min) / y_span

    x_mid = float(x[np.argmax(y)])
    width = max(float(x[-1] - x[0]), 1e-3)
    sigma0 = max(width / 12.0, 0.005)

    def model(xv, bg0, bg1, amp, center, sigma):
        return bg0 + bg1 * (xv - center) + amp * np.exp(-0.5 * ((xv - center) / sigma) ** 2)

    p0 = [float(np.percentile(y, 10)), 0.0, max(float(np.max(y) - np.percentile(y, 10)), 0.05), x_mid, sigma0]
    bounds = (
        [-1.0, -20.0, 0.0, float(x[0]), max(width / len(x), 1e-4)],
        [2.0, 20.0, 5.0, float(x[-1]), width],
    )
    try:
        from scipy.optimize import curve_fit

        popt, _ = curve_fit(model, x, y, p0=p0, bounds=bounds, maxfev=10000, method="trf")
        y_pred = model(x, *popt)
        center = float(popt[3])
        sigma = float(abs(popt[4]))
    except Exception:
        coeff = np.polyfit(x, y, 2)
        y_pred = np.polyval(coeff, x)
        center = x_mid
        sigma = np.nan
        logger.warning("SAXS Bragg-region fit failed; using polynomial fallback.", exc_info=True)

    stats = _standardized_region_stats(y, y_pred)
    if stats is None:
        return None
    stats.update(
        {
            "kind": "bragg_peak",
            "q_start": float(x[0]),
            "q_end": float(x[-1]),
            "q_peak_fit": center,
            "sigma_q": sigma,
        }
    )
    return stats


def _fit_guinier_region(q_guinier: np.ndarray | None, lnI_guinier: np.ndarray | None) -> Dict | None:
    if q_guinier is None or lnI_guinier is None:
        return None
    qg = np.asarray(q_guinier, dtype=float)
    yg = np.asarray(lnI_guinier, dtype=float)
    mask = np.isfinite(qg) & np.isfinite(yg)
    if np.sum(mask) < 5:
        return None

    x = qg[mask]
    y = yg[mask]
    try:
        coeff = np.polyfit(x**2, y, 1)
        y_pred = np.polyval(coeff, x**2)
    except Exception:
        logger.warning("SAXS Guinier-region fit failed.", exc_info=True)
        return None
    stats = _standardized_region_stats(y, y_pred)
    if stats is None:
        return None
    stats.update(
        {
            "kind": "guinier",
            "q_start": float(x[0]),
            "q_end": float(x[-1]),
        }
    )
    return stats


def _standardized_region_stats(y: np.ndarray, y_pred: np.ndarray) -> Dict | None:
    obs = np.asarray(y, dtype=float)
    pred = np.asarray(y_pred, dtype=float)
    mask = np.isfinite(obs) & np.isfinite(pred)
    if np.sum(mask) < 3:
        return None
    obs = obs[mask]
    pred = pred[mask]
    scale = float(np.std(obs))
    if scale <= 1e-12:
        return None
    obs_z = (obs - float(np.mean(obs))) / scale
    pred_z = (pred - float(np.mean(obs))) / scale
    residual = obs_z - pred_z
    ss_res = float(np.sum(residual**2))
    ss_tot = float(np.sum((obs_z - float(np.mean(obs_z))) ** 2))
    return {
        "ss_res": ss_res,
        "ss_tot": ss_tot,
        "n_points": int(len(obs_z)),
        "rmse": float(np.sqrt(np.mean(residual**2))),
    }


# ======================================================================
#  Correlation function gamma(r) and IDF
# ======================================================================

def correlation_function(
    q: np.ndarray, I: np.ndarray,
    cfg: SAXSConfig,
    q_min: float | None = None,
    q_max: float | None = None,
    extrapolate_q0: bool = True,
    extrapolate_qinf: bool = True,
) -> Dict:
    """Compute 1D electron density correlation function gamma(r).

    gamma(r) = integral(I*q^2*cos(q*r) dq) / Q*

    Uses Porod extrapolation to q->inf + Gaussian decay for clean truncation.
    No Guinier extrapolation to q=0 — the experimental q_min (typically
    0.05-0.15 nm^-1) is low enough for lamellar systems (q* ~ 0.5-1.0 nm^-1).

    Returns dict with keys: r, gamma, Q_invariant, r_first_max, L_corr
    """
    # 1. Select q range
    q_corr_min = cfg.q_corr_min
    if q_min is not None:
        q_corr_min = max(q_corr_min, float(q_min))
    q_corr_max = min(cfg.q_corr_max, q[-1])
    if q_max is not None:
        q_corr_max = min(q_corr_max, float(q_max))
    mask = (q >= q_corr_min) & (q <= q_corr_max)
    q_sel = q[mask]
    I_sel = I[mask]

    if len(q_sel) < 20:
        return {
            'r': np.array([]),
            'gamma': np.array([]),
            'Q_invariant': np.nan,
            'q_corr_min': q_corr_min,
            'q_corr_max': q_corr_max,
        }

    # 2. Estimate and subtract thermal fluctuation background Ib.
    #    I(q) = I_lamellar(q) + Ib.  Ib*q^2 diverges at high q and causes
    #    Gibbs oscillations at the truncation boundary.
    n_ib = max(10, len(q_sel) // 5)
    q_ib = q_sel[-n_ib:]
    I_ib = I_sel[-n_ib:]
    Ib = 0.0
    try:
        p_ib = np.polyfit(q_ib**4, I_ib * q_ib**4, 1)
        Ib_raw = float(p_ib[0])
        if Ib_raw > 0.1 * I_sel[-1]:
            Ib = Ib_raw
    except Exception as e:
        logger.warning("SAXS 积分背景校正失败: %s", e, exc_info=True)
    if Ib > 1e-12:
        I_sel = np.maximum(I_sel - Ib, 1e-30)

    dq = q_sel[1] - q_sel[0]

    # 3. Porod extrapolation to q->inf
    r_max = cfg.L_search_max * 2
    n_r = cfg.n_z_points
    q_target = max(5.0, q_sel[-1] * 2.0)
    n_extra = int((q_target - q_sel[-1]) / dq) + 50
    q_ext, I_ext = _extrapolate_porod(q_sel, I_sel, dq, n_extra=max(n_extra, 200))

    # 4. Cosine-blend transition at Porod boundary
    porod_boundary_idx = int(np.searchsorted(q_ext, q_sel[-1]))
    n_blend = min(32, porod_boundary_idx // 2, len(q_ext) - porod_boundary_idx - 2)
    if n_blend >= 3:
        Iq2 = I_ext * q_ext ** 2
        for k in range(1, n_blend + 1):
            idx_data  = porod_boundary_idx - n_blend + k - 1
            idx_porod = porod_boundary_idx + k - 1
            if 0 <= idx_data < len(Iq2) and 0 <= idx_porod < len(Iq2):
                w = 0.5 * (1.0 - np.cos(np.pi * k / (n_blend + 1)))
                Iq2[idx_porod] = (1.0 - w) * Iq2[idx_porod - 1] + w * Iq2[idx_porod]
        I_ext = Iq2 / (q_ext ** 2 + 1e-30)

    # 5. Compute integrand and apply Gaussian decay at high-q
    integrand = I_ext * q_ext ** 2
    q_max_actual = q_ext[-1]
    q_tail_start = 0.75 * q_max_actual
    tail_mask = q_ext >= q_tail_start
    if np.sum(tail_mask) > 10:
        q_tail = q_ext[tail_mask]
        sigma_gauss = (q_max_actual - q_tail_start) / 3.0
        gauss_window = np.exp(-0.5 * ((q_tail - q_tail_start) / sigma_gauss) ** 2)
        integrand[tail_mask] = integrand[tail_mask] * gauss_window

    Q = trapezoid(integrand, q_ext)
    if Q <= 0:
        return {
            'r': np.array([]),
            'gamma': np.array([]),
            'Q_invariant': Q,
            'q_corr_min': q_corr_min,
            'q_corr_max': q_corr_max,
        }

    # 6. Cosine transform
    r = np.linspace(0, r_max, n_r)
    gamma = np.zeros(n_r)
    for i, ri in enumerate(r):
        gamma[i] = trapezoid(integrand * np.cos(q_ext * ri), q_ext) / Q

    # Normalize
    if gamma[0] > 1e-12:
        gamma = gamma / gamma[0]

    # 7. Find first maximum -> L_corr (bounded by physical range)
    try:
        # Estimate L from Bragg peak in I*q^2 within the lamellar q-range
        Iq2_sel = I_sel * q_sel ** 2
        q_bragg_min = getattr(cfg, 'q_bragg_min', 0.15)
        q_bragg_max = getattr(cfg, 'q_bragg_max', 0.9)
        bm = (q_sel >= q_bragg_min) & (q_sel <= q_bragg_max)
        if np.sum(bm) > 3:
            L_est = 2 * np.pi / q_sel[bm][np.argmax(Iq2_sel[bm])]
            # Sanity: L must be in [3, 40] nm
            if not (3 < L_est < 40):
                L_est = np.nan
        else:
            L_est = np.nan
    except Exception:
        L_est = np.nan
        logger.warning("SAXS correlation-function long-period estimate failed.", exc_info=True)
    if np.isfinite(L_est):
        r_min_peak = max(1.5, L_est * 0.30)
        r_max_peak = min(L_est * 2.0, r[-1])
    else:
        r_min_peak = 3.0
        r_max_peak = min(30.0, r[-1])
    search_mask = (r >= r_min_peak) & (r <= r_max_peak)
    if np.sum(search_mask) > 5:
        gamma_search = gamma.copy()
        gamma_search[~search_mask] = -np.inf
        peaks, _ = find_peaks(gamma_search, height=0.01)
    else:
        peaks = []
    L_corr = np.nan
    r_first_max = np.nan
    if len(peaks) > 0:
        r_first_max = r[peaks[0]]
        L_corr = r_first_max

    return {
        'r': r, 'gamma': gamma,
        'Q_invariant': Q,
        'r_first_max': r_first_max,
        'L_corr': L_corr,
        'q_corr_min': q_corr_min,
        'q_corr_max': q_corr_max,
        'q_ext': q_ext, 'I_ext': I_ext,
        'q_raw': q, 'I_raw': I,
    }


def idf_analysis(
    r: np.ndarray, gamma: np.ndarray, cfg: SAXSConfig,
    L_estimate: float | None = None,
) -> Dict:
    """Interface Distribution Function (IDF) from correlation function.

    IDF is derived from the second derivative of gamma(r):
    IDF(r) features peaks at lc (crystalline thickness) and L (long period).

    When L_estimate is provided, the search range is narrowed to the
    physically relevant region [0.5, L * 2.0] to suppress Fourier artifacts.

    Returns dict with keys: r_idf, idf, L_idf, lc_idf, peaks_info
    """
    if len(r) < 10 or len(gamma) < 10:
        return {'r_idf': np.array([]), 'idf': np.array([])}

    # Compute second derivative of gamma
    # Pre-smooth gamma with a gentle Hanning gate on long-range tail
    # to suppress inherited oscillations from Fourier truncation
    r_max = r[-1]
    r_gate_start = r_max * 0.5
    gate = np.ones(len(gamma))
    for i, ri in enumerate(r):
        if ri > r_gate_start:
            frac = (ri - r_gate_start) / (r_max - r_gate_start)
            gate[i] = 0.5 * (1.0 + np.cos(np.pi * frac))
    gamma_gated = gamma * gate
    
    # Use Savitzky-Golay for noise-robust derivative
    from scipy.signal import savgol_filter
    dr = r[1] - r[0]
    window = min(21, len(gamma) // 4 * 2 + 1)
    if window < 5:
        window = 5
    d2gamma = savgol_filter(gamma_gated, window, 3, deriv=2, delta=dr)

    # IDF = -d^2(gamma)/dr^2 in the region of interest
    # Narrow search to physically meaningful range when L is known
    if L_estimate is not None and np.isfinite(L_estimate) and L_estimate > 0:
        r_min = max(0.3, L_estimate * 0.03)
        r_max = L_estimate * 2.0
    else:
        r_min = cfg.l1_min_ratio * cfg.L_search_max
        r_max = cfg.l1_max_ratio * cfg.L_search_max
    mask = (r >= r_min) & (r <= r_max)
    r_idf = r[mask]
    idf = -d2gamma[mask]

    if len(r_idf) < 5:
        return {'r_idf': r_idf, 'idf': idf, 'L_idf': np.nan, 'lc_idf': np.nan,
                'n_peaks': 0, 'peak_positions': []}

    # Positive peaks in IDF indicate characteristic thicknesses
    idf_norm = (idf - np.min(idf)) / (np.max(idf) - np.min(idf) + 1e-12)
    peaks, props = find_peaks(idf_norm, prominence=cfg.idf_peak_rel_thresh)

    # First peak in [0.3, L*0.7] -> thinner phase thickness
    # First peak in [L*0.7, L*1.5] -> L
    L_idf = np.nan
    lc_idf = np.nan

    # Filter peaks: only keep those in physically plausible ranges
    for p in peaks:
        r_peak = r_idf[p]
        if r_peak < L_estimate * 0.7 if L_estimate and np.isfinite(L_estimate) else r_peak < 20:
            if np.isnan(lc_idf):
                lc_idf = r_peak
        elif not np.isnan(lc_idf) and np.isnan(L_idf):
            L_idf = r_peak

    # Fallback: if no filtering, use first two peaks
    if np.isnan(lc_idf) and len(peaks) >= 1:
        lc_idf = r_idf[peaks[0]]
    if np.isnan(L_idf) and len(peaks) >= 2:
        L_idf = r_idf[peaks[1]]

    return {
        'r_idf': r_idf, 'idf': idf,
        'L_idf': L_idf, 'lc_idf': lc_idf,
        'n_peaks': len(peaks),
        'peak_positions': r_idf[peaks].tolist() if len(peaks) > 0 else [],
    }


# ======================================================================
#  Multi-method ensemble
# ======================================================================

def _compute_weighted_confidence(
    bragg_snr: float,
    lorentz_r2: float,
    sasmodels_r2: float,
    method_used: str = "",
) -> float:
    """Compute L_confidence as a weighted composite of signal-quality indicators.

    Phase 5: Weighted composite scoring:
        snr_ratio * 0.4 + lorentz_r2 * 0.3 + sasmodels_r2 * 0.3

    Caps:
      - SNR < 3     → conf ≤ 0.3  (Phase 2)
      - sasmodels R² ≤ 0 → conf ≤ 0.5
      - bragg_dominant (single method) → conf ≤ 0.5
    """
    # Convert SNR to a 0-1 ratio: SNR=3 → 0.0, SNR=15 → 1.0
    snr_ratio = min(1.0, max(0.0, (np.isfinite(bragg_snr) and bragg_snr > 0) * min(bragg_snr / 15.0, 1.0) if np.isfinite(bragg_snr) else 0.0))

    l_r2 = max(0.0, lorentz_r2) if np.isfinite(lorentz_r2) else 0.0
    s_r2 = max(0.0, sasmodels_r2) if np.isfinite(sasmodels_r2) else 0.0

    conf = round(min(1.0, snr_ratio * 0.4 + l_r2 * 0.3 + s_r2 * 0.3), 2)

    # Phase 2: low-SNR cap
    if np.isfinite(bragg_snr) and bragg_snr < 3.0:
        conf = min(conf, 0.3)

    # Phase 5: sasmodels failure cap
    if s_r2 <= 0:
        conf = min(conf, 0.5)

    # Single-method penalty
    if method_used in ('bragg_dominant', 'mean', 'bragg', 'none', ''):
        conf = min(conf, 0.5)

    return conf


def ensemble_long_period(
    L_bragg: float, L_lorentz: float, L_corr: float,
    L_guinier: float, r2_lorentz: float,
    cfg: SAXSConfig,
    bragg_snr: float = np.nan,
    sasmodels_r2: float = np.nan,
) -> LongPeriodResult:
    """Combine multiple long period estimates with confidence-weighted voting.

    Weights from cfg.multi_method_weights; methods with NaN values are excluded
    and their weight redistributed proportionally.

    L_confidence is computed as a weighted composite:
       min(1.0, snr_ratio*0.4 + lorentz_r2*0.3 + sasmodels_r2*0.3)

    When sasmodels fit failed (R² ≤ 0), L_confidence is capped at 0.5.
    When lamellar peak SNR < 3, L_confidence is capped at 0.3.
    """
    estimates = {
        'bragg': L_bragg,
        'lorentz': L_lorentz,
        'corr_peak': L_corr,
        'guinier': L_guinier,
    }

    # Filter valid estimates
    valid = {k: v for k, v in estimates.items() if np.isfinite(v)}

    # Physical plausibility: lamellar long period for typical polymers
    # is rarely below 4 nm. Values below this are likely artifacts from
    # fitting to background noise or Fourier truncation oscillations.
    MIN_PHYSICAL_L_NM = 4.0
    valid = {k: v for k, v in valid.items()
             if v >= MIN_PHYSICAL_L_NM or k == 'guinier'}
    if not valid:
        return LongPeriodResult()

    # If the direct lamellar Bragg peak exists and all transform/fit-based
    # methods disagree strongly, prefer Bragg.  This is common in real SAXS
    # data where low-q upturns, truncation ripples, or a broad background make
    # Lorentz/correlation estimates collapse to a shorter apparent period.
    if 'bragg' in valid and np.isfinite(valid['bragg']):
        L_b = valid['bragg']
        companions = [
            v for k, v in valid.items()
            if k != 'bragg' and np.isfinite(v) and v >= MIN_PHYSICAL_L_NM
        ]
        if companions and all(abs(v - L_b) / max(L_b, 1e-12) > 0.35 for v in companions):
            # Compute weighted composite confidence (Phase 5)
            conf = _compute_weighted_confidence(bragg_snr, r2_lorentz, sasmodels_r2, method_used='bragg_dominant')
            return LongPeriodResult(
                L_best=L_b,
                L_confidence=conf,
                L_bragg=L_bragg,
                L_lorentz=L_lorentz,
                L_corr_peak=L_corr,
                L_guinier=L_guinier,
                method_used='bragg_dominant',
            )

    # Redistribute weights
    total_weight = sum(cfg.multi_method_weights.get(k, 0.0) for k in valid)
    if total_weight <= 0:
        # Equal weights fallback
        L_best = np.mean(list(valid.values()))
        conf = _compute_weighted_confidence(bragg_snr, r2_lorentz, sasmodels_r2, method_used='mean')
        return LongPeriodResult(L_best=L_best, L_confidence=conf, method_used='mean')

    weights = {k: cfg.multi_method_weights.get(k, 0.0) / total_weight for k in valid}

    # Lorentz confidence bonus based on R2
    if 'lorentz' in weights and r2_lorentz > 0.9:
        weights['lorentz'] *= 1.2
        # Renormalize
        wsum = sum(weights.values())
        weights = {k: v / wsum for k, v in weights.items()}

    # Remove outliers (values > 3x median)
    L_values = list(valid.values())
    if len(L_values) >= 3:
        # Use geometric mean for outlier detection (more robust than median
        # when one method gives a physically implausible value)
        median = np.median(L_values)
        # Tight threshold: exclude values > 2.5x median or < 0.4x median
        filtered = {k: v for k, v in valid.items() if 0.4 < v / median < 2.5}
        if filtered:
            valid = filtered
            total_weight = sum(cfg.multi_method_weights.get(k, 0.0) for k in valid)
            if total_weight > 0:
                weights = {k: cfg.multi_method_weights.get(k, 0.0) / total_weight for k in valid}

        # Safety: if Bragg exists but was filtered out as outlier,
        # verify remaining methods are trustworthy.
        # If Lorentz or correlation value is < 5 nm while Bragg > 7 nm,
        # the fragile methods are likely fitting to noise/background,
        # not a real lamellar peak.
        if ('bragg' in estimates and np.isfinite(estimates['bragg'])
            and 'bragg' not in valid):
            L_b = estimates['bragg']
            remaining_Ls = [v for k, v in valid.items()]
            if L_b > 7.0 and all(v < L_b * 0.5 for v in remaining_Ls):
                valid = {'bragg': L_b}
                weights = {'bragg': 1.0}
        

    # Weighted average
    L_best = sum(v * weights[k] for k, v in valid.items())

    # Confidence: fraction of methods agreeing within 20%
    L_values = list(valid.values())
    if len(L_values) >= 2:
        L_mean = np.mean(L_values)
        within_tol = sum(1 for v in L_values if abs(v - L_mean) / L_mean < 0.20)
        agreement_conf = within_tol / len(L_values)
    else:
        agreement_conf = 0.3 if r2_lorentz > 0.8 else 0.1

    # Combine agreement confidence with signal-quality weighted composite (Phase 5)
    signal_conf = _compute_weighted_confidence(bragg_snr, r2_lorentz, sasmodels_r2, method_used='+'.join(valid.keys()))
    confidence = min(agreement_conf, signal_conf)  # conservative: take the lower

    result = LongPeriodResult(
        L_best=L_best, L_confidence=confidence,
        L_bragg=L_bragg, L_lorentz=L_lorentz,
        L_corr_peak=L_corr, L_guinier=L_guinier,
        method_used='+'.join(valid.keys()),
    )
    return result


# ======================================================================
#  Structure parameters
# ======================================================================

def compute_structure_params(
    corr_result: Dict, idf_result: Dict, cfg: SAXSConfig,
    L_ensemble: Optional[float] = None,
) -> StructureParams:
    """Compute structure parameters from correlation function and IDF.

    Key parameters: lc (crystalline thickness), la (amorphous thickness),
    phi_c (linear crystallinity), phi_c_vol (volumetric),
    Sv (specific surface).

    Uses L_ensemble (Bragg+Lorentz) as primary long period when available;
    falls back to correlation function L_corr.
    """
    sp = StructureParams()

    # Long period: prefer ensemble (Bragg+Lorentz), fallback to correlation
    if L_ensemble is not None and np.isfinite(L_ensemble):
        sp.L = L_ensemble
    else:
        sp.L = corr_result.get('L_corr', np.nan)

    L = sp.L

    # ── lc extraction: Tangent-first strategy ──
    # The tangent method on gamma(r) is more robust than IDF (second derivative)
    # because IDF amplifies Fourier truncation artifacts.
    # IDF is used as a cross-check when tangent fails.
    lc = np.nan

    # Method 1 (primary): Tangent method from gamma(r) linear decay
    tangent_thickness = _tangent_lc(corr_result, L, cfg)

    # Method 2 (fallback): IDF peak analysis
    idf_thickness = np.nan
    if idf_result and 'lc_idf' in idf_result:
        raw_idf_val = idf_result.get('lc_idf', np.nan)
        if np.isfinite(raw_idf_val) and np.isfinite(L) and 0 < raw_idf_val < L * 0.7:
            idf_thickness = raw_idf_val

    # Diagnostic: gamma(r) first minimum as third constraint
    r = corr_result.get('r', None)
    gamma = corr_result.get('gamma', None)
    gamma_first_min = np.nan
    if r is not None and gamma is not None and len(gamma) > 10:
        from scipy.signal import argrelextrema
        mins = argrelextrema(gamma[5:], np.less)[0]
        if len(mins) > 0:
            gamma_first_min = r[5:][mins[0]]

    # ── Decision logic: pick the most reliable thickness estimate ──
    thickness = np.nan  # raw thickness (may be lc or la depending on flag)

    if np.isfinite(tangent_thickness) and tangent_thickness > 0.3:
        # Tangent method succeeded — use as primary.
        # Tangent always measures the thinner phase; idf_first_peak_is_la
        # determines whether that thinner phase is la (True) or lc (False).

        # Quality gate: if tangent is below the plausible minimum while
        # IDF is above it, the short gamma(r) linear region makes tangent
        # unreliable — UNLESS the IDF peaks themselves are artifacts.
        min_plausible = getattr(cfg, 'tangent_lc_min_nm', 2.0)
        
        # Detect IDF artifact: peaks at perfectly regular intervals indicate
        # Fourier / SG-filter artifacts, not real structural peaks.
        idf_is_artifact = False
        if idf_result and 'peak_positions' in idf_result:
            pp = idf_result['peak_positions']
            if isinstance(pp, list) and len(pp) >= 3:
                spacings = np.diff(pp)
                if len(spacings) >= 2:
                    spacing_std = np.std(spacings)
                    spacing_mean = np.mean(spacings)
                    if spacing_mean > 0 and spacing_std / spacing_mean < 0.05:
                        idf_is_artifact = True
        
        if (np.isfinite(idf_thickness) and idf_thickness > min_plausible
            and tangent_thickness < min_plausible
            and not idf_is_artifact):
            # Tangent likely unreliable (linear region too short)
            thickness = idf_thickness
        elif np.isfinite(idf_thickness):
            rel_diff = abs(tangent_thickness - idf_thickness) / max(idf_thickness, 0.1)
            if rel_diff < 0.30:
                thickness = (tangent_thickness + idf_thickness) / 2
            else:
                thickness = tangent_thickness
        else:
            thickness = tangent_thickness

    elif np.isfinite(idf_thickness):
        # Tangent failed, use IDF
        thickness = idf_thickness
    elif np.isfinite(gamma_first_min) and 0 < gamma_first_min < L * 0.7:
        # Both tangent and IDF failed — use gamma first minimum
        thickness = gamma_first_min

    # ── Assign lc and la based on idf_first_peak_is_la flag ──
    if np.isfinite(thickness) and np.isfinite(L) and thickness > 0:
        if getattr(cfg, 'idf_first_peak_is_la', False):
            # thickness = la (amorphous), lc = L - la
            sp.la = thickness
            lc = L - thickness
        else:
            # thickness = lc (crystalline), la = L - lc
            lc = thickness
            sp.la = L - lc
    else:
        sp.la = np.nan

    # Save diagnostic values
    sp.lc_tangent_nm = float(tangent_thickness) if np.isfinite(tangent_thickness) else np.nan
    sp.lc_idf_nm = float(idf_thickness) if np.isfinite(idf_thickness) else np.nan
    sp.lc_gamma_min_nm = float(gamma_first_min) if np.isfinite(gamma_first_min) else np.nan

    method_estimates = [
        float(value)
        for value in (sp.lc_tangent_nm, sp.lc_idf_nm, sp.lc_gamma_min_nm)
        if np.isfinite(value) and value > 0
    ]
    method_count = len(method_estimates)
    method_spread = np.nan
    if method_count >= 2:
        method_mean = float(np.mean(method_estimates))
        if method_mean > 0:
            method_spread = float((max(method_estimates) - min(method_estimates)) / method_mean)

    # ── Auto-correct: physical sanity checks ──
    # (a) If lc < 0.05 * L (physically implausible), trust the other estimate
    # (b) If la > L * 0.85, the minority phase might be misassigned
    if np.isfinite(L) and np.isfinite(lc) and np.isfinite(sp.la) and L > 0:
        if lc < L * 0.05 and np.isfinite(idf_thickness) and idf_thickness > L * 0.05:
            # Tangent gave too-thin lc; override with IDF
            if getattr(cfg, 'idf_first_peak_is_la', False):
                sp.la = idf_thickness
                lc = L - idf_thickness
            else:
                lc = idf_thickness
                sp.la = L - lc

        # Physical sanity: if the majority phase is > 85% of L,
        # the minority phase measurement is likely unreliable.
        # Flag via low confidence rather than swapping (the tangent
        # method may underestimate the thin phase, but the assignment
        # of which phase is thin/thick is determined by the config flag).

    sp.lc = lc  # set after potential swaps

    # ── Confidence in lc estimate ──
    # Based on agreement between available methods, plus data quality heuristics.
    estimates = []
    if np.isfinite(tangent_thickness):
        estimates.append(tangent_thickness)
    if np.isfinite(idf_thickness):
        # Down-weight IDF if detected as systematic artifact
        if not idf_is_artifact:
            estimates.append(idf_thickness)
    if np.isfinite(gamma_first_min):
        estimates.append(gamma_first_min)
    
    if len(estimates) >= 2:
        spread = max(estimates) - min(estimates)
        mean_val = np.mean(estimates)
        rel_spread = spread / max(mean_val, 0.1)
        if rel_spread < 0.2:
            sp.confidence_lc = 0.9
        elif rel_spread < 0.5:
            sp.confidence_lc = 0.6
        else:
            sp.confidence_lc = 0.3
    elif len(estimates) == 1:
        # Single method — reduce confidence further if tangent is very small
        # (gamma(r) likely distorted by limited q-range)
        if np.isfinite(tangent_thickness) and tangent_thickness < 2.0:
            sp.confidence_lc = 0.15  # tangent likely unreliable
        else:
            sp.confidence_lc = 0.4
    else:
        sp.confidence_lc = 0.0
    
    # Extra penalty: IDF artifact was detected → reduce confidence
    if idf_is_artifact and len(estimates) <= 1:
        sp.confidence_lc = max(0.05, sp.confidence_lc * 0.5)
    
    # Physical plausibility: for semi-crystalline polymers, if the thinner
    # phase is < 15 % of L, the gamma(r) is likely distorted and the
    # resulting lc/la/phi_c should be treated as low confidence.
    if np.isfinite(L) and np.isfinite(lc) and np.isfinite(sp.la) and L > 0:
        minority_fraction = min(lc, sp.la) / L
        if minority_fraction < 0.15:
            sp.confidence_lc = min(sp.confidence_lc, 0.15)

    # Phase 5: Q* anomaly penalty (beamstop-contaminated / no-mask data)
    # When Q_invariant exceeds ~50 (likely direct-beam or mask-edge pollution),
    # the Porod/invariant analyses are unreliable → cap lc confidence at 0.5.
    if np.isfinite(sp.Q_invariant) and sp.Q_invariant > 50.0:
        sp.confidence_lc = min(sp.confidence_lc, 0.5)

    # Also: if Q_invariant is abnormally low after mask truncation (< 0.5),
    # the correlation function may be distorted too.
    if np.isfinite(sp.Q_invariant) and sp.Q_invariant > 0 and sp.Q_invariant < 0.5:
        sp.confidence_lc = min(sp.confidence_lc, 0.4)

    if method_count == 1:
        sp.confidence_lc = min(sp.confidence_lc, 0.5)
    elif np.isfinite(method_spread) and method_spread > 0.35:
        sp.confidence_lc = min(sp.confidence_lc, 0.6)

    # Linear crystallinity phi_c = lc / L
    if np.isfinite(L) and np.isfinite(lc) and L > 0:
        sp.phi_c = lc / L

    # Volumetric crystallinity (if known from WAXS)
    if np.isfinite(cfg.crystallinity):
        sp.phi_c_vol = cfg.crystallinity

    # Specific surface Sv = pi * Kp / Q*
    Q = corr_result.get('Q_invariant', np.nan)
    Kp_guess = _porod_constant(corr_result.get('q_ext', None),
                                corr_result.get('I_ext', None),
                                q_raw=corr_result.get('q_raw', None),
                                I_raw=corr_result.get('I_raw', None))
    if np.isfinite(Q) and np.isfinite(Kp_guess) and Q > 0:
        sp.Sv = np.pi * Kp_guess / Q

    sp.Q_invariant = Q

    # Porod-invariant crystallinity (independent cross-check)
    if np.isfinite(L) and np.isfinite(Q) and np.isfinite(Kp_guess) and Q > 0 and Kp_guess > 0:
        phi_c_inv = _crystallinity_invariant(L, Q, Kp_guess)
        sp.phi_c_invariant = phi_c_inv
        # Diagnostic: lc from invariant (for comparison with tangent/IDF)
        if np.isfinite(phi_c_inv):
            sp.lc_porod_nm = phi_c_inv * L

    return sp


def _tangent_lc(corr_result: Dict, L: float, cfg: SAXSConfig) -> float:
    return _saxs_physical_helpers._tangent_lc(corr_result, L, cfg)


def _crystallinity_invariant(L: float, Q_invariant: float, Kp: float) -> float:
    return _saxs_physical_helpers._crystallinity_invariant(L, Q_invariant, Kp)


# ======================================================================
#  Guinier analysis
# ======================================================================

def guinier_analysis(
    q: np.ndarray, I: np.ndarray,
    q_min: float | None = None,
    q_max_factor: float = 1.3,
) -> Tuple[float, float, np.ndarray, np.ndarray]:
    """Guinier analysis: ln(I) vs q^2 in the low-q region.

    I(q) ≈ I(0) * exp(-q^2 * Rg^2 / 3)
    ln(I) = ln(I0) - (Rg^2/3) * q^2

    Valid when q_max * Rg < 1.3
    Returns (Rg_nm, I0, q_guinier, lnI_guinier).
    """
    mask = np.isfinite(q) & np.isfinite(I)
    if q_min is not None:
        mask &= q >= float(q_min)
    q_valid = q[mask]
    I_valid = I[mask]

    if len(q_valid) < 10:
        return np.nan, np.nan, np.array([]), np.array([])

    # Use the lowest-q slice after beamstop truncation as the Guinier window.
    n_lowq = max(10, len(q_valid) // 5)
    q_low = q_valid[:n_lowq]
    I_low = I_valid[:n_lowq]

    # Filter positive intensities
    pos = I_low > 0
    if np.sum(pos) < 5:
        return np.nan, np.nan, np.array([]), np.array([])

    q_sel = q_low[pos]
    I_sel = I_low[pos]
    lnI = np.log(I_sel)
    q2 = q_sel ** 2

    # Linear fit: ln(I) = a + b * q^2
    from numpy.polynomial.polynomial import Polynomial
    p = Polynomial.fit(q2, lnI, 1)
    a, b = p.convert().coef

    # Rg = sqrt(-3 * b)
    if b < 0:
        Rg = np.sqrt(-3 * b)
    else:
        Rg = np.nan

    I0 = np.exp(a) if a < 100 else np.nan  # guard against overflow

    return Rg, I0, q_sel, lnI


# ======================================================================
#  Porod analysis
# ======================================================================

def porod_analysis(
    q: np.ndarray, I: np.ndarray, cfg: SAXSConfig,
) -> Dict:
    """Porod analysis: I(q) ~ Kp / q^4 at high q.

    Specific surface Sv = pi * Kp / Q*.
    Returns dict with Kp, Sv, q_porod, Iq4_porod.
    """
    mask = (q >= cfg.q_porod_min) & (q <= cfg.q_porod_max)
    if np.sum(mask) < 10:
        return {'Kp': np.nan, 'Sv': np.nan}

    q_sel = q[mask]
    I_sel = I[mask]
    Iq4 = I_sel * q_sel ** 4

    # Porod constant = plateau value of I*q^4
    Kp = np.median(Iq4)
    slope = np.nan
    pos = (q_sel > 0) & (I_sel > 0) & np.isfinite(q_sel) & np.isfinite(I_sel)
    if np.sum(pos) >= 5:
        try:
            slope = float(np.polyfit(np.log(q_sel[pos]), np.log(I_sel[pos]), 1)[0])
        except Exception:
            slope = np.nan
            logger.warning("SAXS Porod slope fit failed.", exc_info=True)

    return {
        'Kp': Kp,
        'slope': slope,
        'q_porod': q_sel,
        'Iq4_porod': Iq4,
        'Iq4': Iq4,
        'Sv': np.nan,  # needs Q* from elsewhere
    }

# ======================================================================
#  Kratky analysis
# ======================================================================

def kratky_analysis(
    q: np.ndarray, I: np.ndarray, cfg: SAXSConfig,
) -> Dict:
    """Kratky plot: I*q^2 vs q.

    Shape reveals: folded chain (Gaussian peak), unfolded (plateau),
    compact globule (bell at low q).
    """
    kratky = I * q ** 2
    # Normalize by maximum
    kratky_norm = kratky / np.max(kratky) if np.max(kratky) > 0 else kratky

    # Peak position (if folded chain)
    mask = (q >= 0.1) & (q <= 2.0)
    if np.sum(mask) > 5:
        idx_peak = np.argmax(kratky[mask])
        q_peak = q[mask][idx_peak]
    else:
        q_peak = np.nan

    return {
        'q': q, 'kratky': kratky, 'kratky_norm': kratky_norm,
        'q_peak_kratky': q_peak,
    }


# ======================================================================
#  sasmodels interface
# ======================================================================

def sasmodels_fit(
    q: np.ndarray, I: np.ndarray,
    model_name: str = "lamellar_stack_caille",
    dI: Optional[np.ndarray] = None,
    L_bragg_guess: Optional[float] = None,
) -> Dict:
    """Fit a sasmodels lamellar model to I(q).

    Uses lamellar_stack_caille (Caille-disordered lamellar stack) by default.
    Initializes from Bragg L if provided. Returns dict with fitted L, lc, la,
    Xc, and R² quality metric. Falls back gracefully if sasmodels unavailable
    or fit fails.

    Parameters
    ----------
    q : q vector (nm^-1) — converted internally to A^-1 for sasmodels.
    I : intensity (arbitrary units, auto-normalized).
    model_name : sasmodels model name.
    dI : optional error on I.
    L_bragg_guess : initial guess for long period (nm) from Bragg peak.

    Returns dict with keys: L_nm, lc_nm, la_nm, Xc, R2, converged, model_name.
    """
    result = {
        'model_name': model_name,
        'L_nm': np.nan, 'lc_nm': np.nan, 'la_nm': np.nan,
        'Xc': np.nan, 'R2': np.nan, 'converged': False,
    }

    # ---- Check sasmodels availability ----
    try:
        from sasmodels.core import load_model
        from sasmodels.data import Data1D
        from sasmodels.direct_model import DirectModel
    except ImportError:
        result['error'] = 'sasmodels not installed'
        return result

    # ---- Prepare data ----
    I_max = float(np.max(I))
    if I_max <= 0:
        result['error'] = 'No valid intensity'
        return result

    # Focus on lamellar peak region (q ~ 0.08–1.8 nm^-1)
    mask = (q >= 0.08) & (q <= 1.8)
    if np.sum(mask) < 30:
        result['error'] = 'Insufficient q range'
        return result

    q_fit_nm = q[mask]
    I_fit_norm = I[mask] / I_max
    q_fit_A = q_fit_nm * 10.0  # nm^-1 -> A^-1

    if dI is None:
        dI_fit = np.ones_like(I_fit_norm) * 0.03
    else:
        dI_fit = dI[mask] / I_max

    # ---- Build model ----
    try:
        data = Data1D(x=q_fit_A, y=I_fit_norm, dy=dI_fit)
        model = load_model(model_name)
        dm = DirectModel(data, model)
    except Exception as e:
        result['error'] = f'sasmodels setup failed: {e}'
        logger.warning("SAXS sasmodels setup failed.", exc_info=True)
        return result

    # ---- Initial guess from Bragg ----
    if L_bragg_guess is not None and np.isfinite(L_bragg_guess) and L_bragg_guess > 0:
        d_init = L_bragg_guess * 10.0  # nm -> A
    else:
        # Fallback: find peak in I*q^2
        Iq2 = I_fit_norm * q_fit_nm ** 2
        q_peak = q_fit_nm[np.argmax(Iq2)]
        d_init = 2 * np.pi / q_peak * 10.0 if q_peak > 0 else 80.0

    thick_init = min(d_init * 0.35, 40.0)  # ~35% of L, cap at 4 nm
    p0 = [1.0, 0.001, thick_init, d_init, 3.0, 0.1]
    bounds = ([0.01, 0, 5, 20, 1, 0.01], [100, 0.5, 80, 300, 15, 0.5])
    fixed = {'sld': 1.0, 'sld_solvent': 6.0}

    # ---- Fit ----
    try:
        from scipy.optimize import curve_fit

        def _model_fn(q_A_ignored, scale, bg, thick_A, d_A, nlayers, caille):
            return dm(scale=scale, background=bg,
                      thickness=thick_A, Nlayers=nlayers,
                      d_spacing=d_A, Caille_parameter=caille,
                      **fixed)

        popt, _ = curve_fit(
            _model_fn, q_fit_A, I_fit_norm,
            p0=p0, bounds=bounds,
            maxfev=400, xtol=1e-4,
        )
        scale, bg, thick_A, d_A, nlayers, caille = popt

        # Quality check
        I_pred = _model_fn(q_fit_A, *popt)
        ss_res = float(np.sum((I_fit_norm - I_pred) ** 2))
        ss_tot = float(np.sum((I_fit_norm - np.mean(I_fit_norm)) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

        L_fit = d_A / 10.0          # A -> nm
        lc_fit = thick_A / 10.0     # A -> nm
        la_fit = L_fit - lc_fit

        result.update({
            'L_nm': round(L_fit, 2),
            'lc_nm': round(lc_fit, 2),
            'la_nm': round(la_fit, 2),
            'Xc': round(lc_fit / L_fit, 3) if L_fit > 0 else np.nan,
            'R2': round(r2, 4),
            'converged': r2 > 0.85,
            'scale': round(float(scale), 2),
            'Nlayers': round(float(nlayers), 1),
            'Caille': round(float(caille), 4),
        })
    except Exception as e:
        result['error'] = f'Fit failed: {e}'
        logger.warning("SAXS sasmodels fit failed.", exc_info=True)

    return result


# ======================================================================
#  Validation & quality marking (§10)
# ======================================================================

def validate_saxs_results(result: "SAXSResult", cfg: SAXSConfig,
                          prev_Q_star: float | None = None) -> "SAXSResult":
    """Run automated quality checks on a SAXS analysis result.

    Implements §10.3 of the PolyNexus v4.0 framework:
      - L in (5, 100) nm  → out of range = ERROR
      - lc < L             → violated  = ERROR
      - lamellar SNR ≥ 3   → below     = WARN
      - sasmodels R² ≥ 0.5 → below     = WARN; R² ≤ 0 = ERROR
      - Q* contaminated    → beamstop  = ERROR, Q_star_valid=False
      - Q* adjacent-frame change > 30% → WARN (pass prev_Q_star for series)
      - Mask truncated     → q_start > 0.1 → WARN

    Returns the modified result with quality_flag and validation_summary populated.
    """
    sp = result.structure
    lp = result.long_period
    flags: List[str] = []
    summaries: List[str] = []

    # --- L physical range ---
    L_val = sp.L if sp and np.isfinite(sp.L) else (lp.L_best if lp and np.isfinite(lp.L_best) else np.nan)
    if np.isfinite(L_val):
        if L_val < 5.0 or L_val > 100.0:
            flags.append("ERROR:L_out_of_range")
            summaries.append(f"L={L_val:.1f}nm outside [5,100]")
    else:
        flags.append("ERROR:L_not_computed")
        summaries.append("Long period not computable")

    # --- lc < L ---
    if sp and np.isfinite(sp.lc) and np.isfinite(sp.L) and sp.L > 0:
        if sp.lc >= sp.L:
            flags.append("ERROR:lc_ge_L")
            summaries.append(f"lc={sp.lc:.2f} >= L={sp.L:.2f}")

    # --- Lamellar peak SNR ---
    if np.isfinite(result.q_peak_snr) and result.q_peak_snr < 3.0:
        flags.append("WARN:low_snr")
        summaries.append(f"Lamellar SNR={result.q_peak_snr:.1f} (<3)")

    # --- Sasmodels R² ---
    sas_r2 = None
    if isinstance(getattr(result, 'final_parameters', None), dict):
        sas_r2 = result.final_parameters.get('sasmodels_R2')
    if sas_r2 is not None and np.isfinite(sas_r2):
        if sas_r2 <= 0:
            flags.append("ERROR:sasmodels_failed")
            summaries.append(f"sasmodels R²={sas_r2:.4f} <= 0")
        elif sas_r2 < 0.5:
            flags.append("WARN:sasmodels_low_r2")
            summaries.append(f"sasmodels R²={sas_r2:.4f} < 0.5")

    # --- Q* contamination (beamstop) ---
    if result.beam_stop_contaminated:
        flags.append("ERROR:qstar_contaminated")
        eff_q = getattr(result, 'effective_q_min', 0.0)
        summaries.append(f"Q* contaminated below q={eff_q:.3f}nm-1; use q_min>={eff_q:.3f} for invariant")
        result.Q_star_valid = False

    # --- Mask truncation ---
    if result.mask_truncated:
        flags.append("WARN:mask_truncated")
        summaries.append("Effective q_min > 0.10 nm⁻¹ — Guinier region lost")

    # --- No-mask Q* magnitude check ---
    if sp and np.isfinite(sp.Q_invariant) and sp.Q_invariant > 50.0:
        flags.append("WARN:qstar_anomalous")
        summaries.append(f"Q*={sp.Q_invariant:.1f} abnormally large (no-mask?)")

    # --- Phase 4: Series Q* consistency (adjacent frame) ---
    if prev_Q_star is not None and sp and np.isfinite(sp.Q_invariant) and sp.Q_invariant > 0:
        rel_change = abs(sp.Q_invariant - prev_Q_star) / max(prev_Q_star, 1e-12)
        if rel_change > 0.30:
            flags.append("WARN:qstar_series_jump")
            summaries.append(f"Q* changed {rel_change*100:.0f}% from previous frame ({prev_Q_star:.1f}->{sp.Q_invariant:.1f})")

    # Assemble
    if not flags:
        result.quality_flag = "OK"
        result.validation_summary = "All checks passed"
    else:
        result.quality_flag = ";".join(flags)
        result.validation_summary = "; ".join(summaries)

    return result


def sasmodels_fit_with_fallback(
    q: np.ndarray, I: np.ndarray,
    L_bragg_guess: Optional[float] = None,
    candidate_models: Optional[List[str]] = None,
) -> Dict:
    """Fit sasmodels lamellar models with automatic fallback.

    Phase 3: Tries models in order: lamellar → lamellar_hg →
    lamellar_stack_caille → lamellar_stack_pca.
    Only results with R² ≥ 0.5 are accepted into final parameters.
    R² ≤ 0 is treated as a hard failure.

    Returns dict with keys: L_nm, lc_nm, la_nm, Xc, R2, converged,
    model_name_tried, model_used.
    """
    if candidate_models is None:
        candidate_models = [
            "lamellar",
            "lamellar_hg",
            "lamellar_stack_caille",
            "lamellar_stack_pca",
        ]

    models_tried: List[Dict] = []
    for model_name in candidate_models:
        r = sasmodels_fit(q, I, model_name=model_name, L_bragg_guess=L_bragg_guess)
        models_tried.append({
            'model': model_name,
            'R2': r.get('R2', np.nan),
            'converged': r.get('converged', False),
            'L_nm': r.get('L_nm', np.nan),
            'lc_nm': r.get('lc_nm', np.nan),
            'Xc': r.get('Xc', np.nan),
        })
        r2 = r.get('R2', np.nan)
        if np.isfinite(r2) and r2 >= 0.5:
            r['model_name_tried'] = [m['model'] for m in models_tried]
            r['model_used'] = model_name
            return r

    # All models failed → return best-effort result with diagnostics
    best = max(models_tried, key=lambda m: m.get('R2', -999.0))
    return {
        'model_name': best['model'],
        'L_nm': best['L_nm'],
        'lc_nm': best['lc_nm'],
        'la_nm': np.nan,
        'Xc': best['Xc'],
        'R2': best['R2'],
        'converged': False,
        'model_name_tried': [m['model'] for m in models_tried],
        'model_used': f"{best['model']}(best_of_fallback)",
        'error': f"All {len(candidate_models)} models failed; best R²={best['R2']:.4f}",
    }


# ======================================================================
#  Full analysis pipeline
# ======================================================================

def analyze_single(
    q: np.ndarray, I: np.ndarray, cfg: SAXSConfig,
    q_anchor: float | None = None,
    q_pyfai: np.ndarray | None = None,
    I_pyfai: np.ndarray | None = None,
) -> SAXSResult:
    """Run complete SAXS analysis for a single I(q) profile.

    This is the main entry point for core analysis.  Phases 1-5 are integrated:
      - Phase 1: beamstop detection after smoothing
      - Phase 2: lamellar SNR gating
      - Phase 3: sasmodels fallback (deferred to caller)
      - Phase 4: automated validation
      - Phase 5: weighted composite confidence
    """
    result = SAXSResult(q=q, I=I)

    # Smooth
    from .preprocess import smooth_profile
    I_smooth = smooth_profile(q, I, cfg)
    result.I_smooth = I_smooth

    # ---- Phase 1: Beamstop detection ----
    from .preprocess import detect_beamstop_edge
    eff_q_min, beam_contaminated, beam_diag = detect_beamstop_edge(q, I_smooth, cfg)
    result.beam_stop_contaminated = beam_contaminated
    result.effective_q_min = eff_q_min
    if eff_q_min > getattr(cfg, 'mask_truncated_q_thresh', 0.10):
        result.mask_truncated = True  # mask / beamstop cuts into useful q range

    # Bragg long period: use cfg range, fallback to 0.15-0.9
    q_bmin = getattr(cfg, 'q_bragg_min', 0.15)
    # If beamstop edge pushes beyond q_bmin, use it as floor
    if beam_contaminated and eff_q_min > q_bmin:
        q_bmin = eff_q_min
    q_bmax = getattr(cfg, 'q_bragg_max', 0.9)
    q_analysis_min = max(float(getattr(cfg, 'q_corr_min', 0.05)), float(eff_q_min))
    L_bragg, q_peak, bragg_info = bragg_long_period(
        q, I_smooth,
        q_min=q_bmin,
        q_max=q_bmax,
        q_anchor=q_anchor,
    )

    # Store lamellar SNR (Phase 2)
    result.q_peak_snr = float(bragg_info.get("snr", np.nan))

    # Lorentz fitting
    L_lorentz, r2_lorentz, lorentz_info = lorentz_fit_long_period(
        q, I_smooth, cfg,
        q_min=q_analysis_min,
        q_max=getattr(cfg, 'q_corr_max', None),
    )

    # Correlation function
    corr = correlation_function(
        q, I_smooth, cfg,
        q_min=q_analysis_min,
        q_max=getattr(cfg, 'q_corr_max', None),
    )
    result.correlation = corr

    # IDF (pass Bragg L as estimate to narrow search range)
    L_guess = L_bragg if np.isfinite(L_bragg) and L_bragg > 0 else None
    idf = idf_analysis(corr['r'], corr['gamma'], cfg, L_estimate=L_guess)
    result.idf = idf

    # Guinier
    Rg, I0, q_guinier, lnI_guinier = guinier_analysis(q, I_smooth, q_min=q_analysis_min)
    quality_report = build_data_quality_report(
        q,
        I,
        processed_data_ref="saxs_result:I_smooth",
        processing_config_ref="SAXSConfig",
        low_q_truncated=bool(result.mask_truncated),
    )
    condition_context = getattr(cfg, "condition_context", {}) or {}
    applicability = (
        condition_context.get("guinier_applicability", "unknown")
        if isinstance(condition_context, dict)
        else "unknown"
    )
    guinier_evidence = build_guinier_evidence(
        q_guinier,
        lnI_guinier,
        rg_nm=Rg,
        i0=I0,
        quality_report=quality_report,
        applicability=str(applicability or "unknown"),
        source_ref="saxs_engine.guinier_analysis",
    )
    result.data_quality_report = quality_report.to_dict()
    result.guinier_evidence = guinier_evidence.to_dict()

    # Multi-method ensemble long period (Bragg + Lorentz + correlation)
    # Guinier Rg measures different physics (particle size), not used here
    # Phase 2+5: pass SNR and sasmodels_R2 for weighted composite confidence
    sasmodels_r2_for_conf = np.nan  # will be set by caller; placeholder
    lp = ensemble_long_period(
        L_bragg=L_bragg,
        L_lorentz=L_lorentz,
        L_corr=corr.get('L_corr', np.nan),
        L_guinier=np.nan,  # Rg ≠ L — different physics, excluded from vote
        r2_lorentz=r2_lorentz,
        cfg=cfg,
        bragg_snr=result.q_peak_snr,
        sasmodels_r2=sasmodels_r2_for_conf,
    )
    result.long_period = lp
    fit_quality = _saxs_peak_region_fit_quality(
        q,
        I_smooth,
        cfg,
        q_bragg_min=q_bmin,
        q_bragg_max=q_bmax,
        q_guinier=q_guinier,
        lnI_guinier=lnI_guinier,
    )
    result.r_squared = fit_quality["r_squared"]
    result.fit_rmse = fit_quality["fit_rmse"]
    result.fit_regions = fit_quality["fit_regions"]
    result.r_squared_method = fit_quality["method"]
    result.quality_score = float(lp.L_confidence) if lp and np.isfinite(lp.L_confidence) else 0.0

    # Structure parameters
    sp = compute_structure_params(corr, idf, cfg, L_ensemble=lp.L_best)
    sp.Rg = Rg
    result.structure = sp

    # Porod
    result.porod = porod_analysis(q, I_smooth, cfg)

    # Kratky
    result.kratky = kratky_analysis(q, I_smooth, cfg)

    # ---- Phase 4: Automated validation ----
    result = validate_saxs_results(result, cfg)

    # Unified 1D method evidence.  These builders are observational and are
    # deliberately isolated from the legacy numeric result payloads.
    metric_context = condition_context if isinstance(condition_context, dict) else {}
    metric_builders = {
        "porod": (
            build_porod_evidence,
            (result.porod,),
            "porod_applicability",
            "Porod",
        ),
        "kratky": (
            build_kratky_evidence,
            (result.kratky,),
            "kratky_applicability",
            "Kratky",
        ),
        "invariant": (
            build_invariant_evidence,
            (getattr(result.structure, "Q_invariant", np.nan),),
            "invariant_applicability",
            "Q_star",
        ),
        "lamellar": (
            build_lamellar_evidence,
            (result.long_period, result.structure),
            "lamellar_applicability",
            "Lamellar",
        ),
    }
    result.metric_evidence = {}
    for key, (builder, args, applicability_key, metric_name) in metric_builders.items():
        try:
            evidence = builder(
                *args,
                quality_report=quality_report,
                applicability=str(metric_context.get(applicability_key, "unknown") or "unknown"),
                valid=bool(result.Q_star_valid),
                beam_stop_contaminated=bool(result.beam_stop_contaminated),
                source_ref=f"saxs_engine.{key}",
            ) if key == "invariant" else builder(
                *args,
                quality_report=quality_report,
                applicability=str(metric_context.get(applicability_key, "unknown") or "unknown"),
                source_ref=f"saxs_engine.{key}",
            )
        except Exception:
            logger.warning("SAXS %s evidence construction failed.", key, exc_info=True)
            evidence = MetricEvidence(
                metric_name=metric_name,
                level=QualityLevel.DIAGNOSTIC,
                applicable=False,
                reason_codes=("metric_evidence_build_failed",),
                source_ref=f"saxs_engine.{key}",
                data_quality_ref=str(quality_report.source_id or ""),
            )
        result.metric_evidence[key] = evidence.to_dict()

    # ---- pyFAI shadow channel (cross-validation only) ----
    if q_pyfai is not None and len(q_pyfai) >= 20 and I_pyfai is not None:
        result.q_pyfai = q_pyfai
        result.I_pyfai = I_pyfai
        I_pyfai_smooth = smooth_profile(q_pyfai, I_pyfai, cfg)
        L_bragg_pf, q_peak_pf, _ = bragg_long_period(
            q_pyfai, I_pyfai_smooth,
            q_min=getattr(cfg, "q_bragg_min", 0.15),
            q_max=getattr(cfg, "q_bragg_max", 0.9),
        )
        result.L_bragg_pyfai = L_bragg_pf
        result.q_peak_pyfai = q_peak_pf
        # Compare q* positions
        q_star_manual = 2 * np.pi / lp.L_best if lp and np.isfinite(lp.L_best) and lp.L_best > 0 else None
        if q_star_manual and np.isfinite(q_peak_pf) and q_peak_pf > 0:
            result.pyfai_q_peak_diff_pct = round(float((q_peak_pf - q_star_manual) / q_star_manual * 100), 2)

    return result


# ======================================================================
#  Extrapolation helpers
# ======================================================================

def _extrapolate_guinier(
    q: np.ndarray, I: np.ndarray, dq: float, n_extra: int = 15,
) -> Tuple[np.ndarray, np.ndarray]:
    return _saxs_extrapolation_helpers._extrapolate_guinier(q, I, dq, n_extra=n_extra)


def _extrapolate_porod(
    q: np.ndarray, I: np.ndarray, dq: float, n_extra: int = 30,
) -> Tuple[np.ndarray, np.ndarray]:
    return _saxs_extrapolation_helpers._extrapolate_porod(q, I, dq, n_extra=n_extra)


# Keep legacy core-level helper names bound to the dedicated quality-helper
# module so existing imports continue to work while the implementation lives
# in one place.
_finite_float = _saxs_quality_helpers._finite_float
classify_single_frame_lc_reliability = _saxs_quality_helpers.classify_single_frame_lc_reliability
_standardized_region_stats = _saxs_quality_helpers._standardized_region_stats
_fit_bragg_region = _saxs_quality_helpers._fit_bragg_region
_fit_guinier_region = _saxs_quality_helpers._fit_guinier_region
_saxs_peak_region_fit_quality = _saxs_quality_helpers._saxs_peak_region_fit_quality
_tangent_lc = _saxs_physical_helpers._tangent_lc
_crystallinity_invariant = _saxs_physical_helpers._crystallinity_invariant
_porod_constant = _saxs_physical_helpers._porod_constant
guinier_analysis = _saxs_physical_helpers.guinier_analysis  # noqa: F811
porod_analysis = _saxs_physical_helpers.porod_analysis  # noqa: F811
_extrapolate_guinier = _saxs_extrapolation_helpers._extrapolate_guinier
_extrapolate_porod = _saxs_extrapolation_helpers._extrapolate_porod
