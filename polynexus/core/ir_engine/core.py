"""IR core analysis module.

Computes:
    - Peak detection & fitting (Lorentzian / Gaussian)
    - Spectrum simulation from computed vibrational modes
    - Experimental-computational comparison & assignment
    - Crystallinity quantification (band ratio method)
    - Peak assignment matching against database
"""
import logging
import numpy as np
from scipy import signal, optimize
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

from .io import IRSpectrum, ComputedMode, simulate_spectrum
from .config import IRConfig
from .names import normalize_ir_polymer_name
from .names import normalize_ir_polymer_database

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
#  Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class IRResult:
    """Container for IR analysis results."""
    label: str = ""

    # Peaks
    n_peaks: int = 0
    peaks: List[Dict[str, Any]] = field(default_factory=list)

    # Crystallinity
    Xc_pct: float = np.nan
    Xc_method: str = ""
    Xc_calibration_status: str = "unavailable"
    Xc_band: str = ""
    Xc_ref_band: str = ""
    band_indices: Dict[str, float] = field(default_factory=dict)

    # Polymer / functional assignment
    polymer_name: str = ""
    polymer_score: float = np.nan

    # Computational comparison
    computed_modes: List[ComputedMode] = field(default_factory=list)
    simulated_spectrum: Optional[IRSpectrum] = None
    matches: List[Dict[str, Any]] = field(default_factory=list)

    # Fit quality
    r_squared: float = np.nan

    # Raw data references
    wavenumber: np.ndarray = field(default_factory=lambda: np.array([]))
    absorbance: np.ndarray = field(default_factory=lambda: np.array([]))
    absorbance_fit: np.ndarray = field(default_factory=lambda: np.array([]))
    baseline: np.ndarray = field(default_factory=lambda: np.array([]))

    @property
    def parameters(self) -> Dict[str, Any]:
        p = {
            'n_peaks': self.n_peaks,
            'polymer': self.polymer_name,
            'polymer_score': self.polymer_score,
            'Xc_pct': self.Xc_pct, 'Xc_method': self.Xc_method,
            'Xc_calibration_status': self.Xc_calibration_status,
            'Xc_band': self.Xc_band, 'Xc_ref_band': self.Xc_ref_band,
            'n_matches': len(self.matches),
            'r_squared': self.r_squared,
            'wavenumber_min_cm1': float(np.nanmin(self.wavenumber)) if len(self.wavenumber) else np.nan,
            'wavenumber_max_cm1': float(np.nanmax(self.wavenumber)) if len(self.wavenumber) else np.nan,
        }
        for key, val in self.band_indices.items():
            p[f'band_index_{key}'] = val
        for i, pk in enumerate(self.peaks[:10]):
            j = i + 1
            p[f'peak_{j}_cm1'] = pk.get('wavenumber', np.nan)
            p[f'peak_{j}_height'] = pk.get('height', np.nan)
            p[f'peak_{j}_area'] = pk.get('area', np.nan)
            p[f'peak_{j}_fwhm_cm1'] = pk.get('fwhm_cm1', np.nan)
            p[f'peak_{j}_assignment'] = pk.get('assignment', '')
        return {k: v for k, v in p.items()
                if not (isinstance(v, float) and np.isnan(v))}


# ---------------------------------------------------------------------------
#  Peak detection
# ---------------------------------------------------------------------------

def detect_peaks(wavenumber: np.ndarray, absorbance: np.ndarray,
                 height_frac: float = 0.02,
                 distance: float = 10.0,
                 prominence_frac: float = 0.015,
                 max_peaks: int = 40,
                 ) -> List[Dict[str, Any]]:
    """Detect absorption peaks in an IR spectrum.

    IR peaks are positive (absorbance maxima).

    Parameters
    ----------
    height_frac : float
        Minimum peak height as fraction of maximum absorbance.
    distance : float
        Minimum distance between peaks in cm^-1.

    Returns
    -------
    List of {index, idx, wavenumber, height, prominence}
    """
    if len(absorbance) < 10:
        return []

    y = np.asarray(absorbance, dtype=float)
    x = np.asarray(wavenumber, dtype=float)

    y_range = float(np.max(y) - np.min(y))
    if y_range <= 0:
        return []
    min_height = np.min(y) + height_frac * y_range
    min_prominence = prominence_frac * y_range
    dx = float(np.nanmedian(np.abs(np.diff(x))))
    if not np.isfinite(dx) or dx <= 0:
        dx = 1.0

    peak_indices, props = signal.find_peaks(
        y, height=min_height, prominence=min_prominence,
        distance=max(1, int(distance / dx)),
    )
    if len(peak_indices) == 0:
        return []

    widths, width_heights, left_ips, right_ips = signal.peak_widths(
        y, peak_indices, rel_height=0.5)

    peaks = []
    for i, idx in enumerate(peak_indices):
        left_x = np.interp(left_ips[i], np.arange(len(x)), x)
        right_x = np.interp(right_ips[i], np.arange(len(x)), x)
        peaks.append({
            'index': i,
            'idx': int(idx),
            'wavenumber': float(x[idx]),
            'height': float(y[idx]),
            'prominence': float(props['prominences'][i]) if 'prominences' in props else 0.0,
            'fwhm_cm1': float(abs(right_x - left_x)),
        })

    peaks.sort(key=lambda p: p.get('prominence', 0.0), reverse=True)
    if max_peaks and len(peaks) > max_peaks:
        peaks = peaks[:max_peaks]
    peaks.sort(key=lambda p: p['wavenumber'], reverse=True)
    for i, pk in enumerate(peaks):
        pk['index'] = i
    return peaks


# ---------------------------------------------------------------------------
#  Peak fitting
# ---------------------------------------------------------------------------

def _lorentzian(x, amp, mu, gamma):
    return amp * gamma**2 / ((x - mu)**2 + gamma**2)


def _gaussian(x, amp, mu, sigma):
    return amp * np.exp(-0.5 * ((x - mu) / sigma)**2)


def fit_peaks(wavenumber: np.ndarray, absorbance: np.ndarray,
              peaks: List[Dict[str, Any]],
              peak_type: str = 'lorentzian',
              fixed_fwhm: Optional[float] = None,
              window_cm1: float = 35.0,
              ) -> Tuple[List[Dict[str, Any]], float, np.ndarray]:
    """Local Lorentzian/Gaussian fitting for detected IR bands.

    Returns (fitted_peaks, r_squared, fitted_absorbance).
    """
    if not peaks or len(wavenumber) < 10:
        return [], np.nan, np.array([])

    x = np.asarray(wavenumber, dtype=float)
    y = np.asarray(absorbance, dtype=float)

    peak_func = _lorentzian if peak_type == 'lorentzian' else _gaussian
    y_fit = np.full_like(y, np.nan, dtype=float)
    fitted_peaks = []

    for i, pk in enumerate(peaks):
        mu0 = float(pk['wavenumber'])
        mask = np.abs(x - mu0) <= window_cm1
        if np.sum(mask) < 8:
            mask = np.abs(x - mu0) <= max(window_cm1, 60.0)
        xw = x[mask]
        yw = y[mask]
        if len(xw) < 8:
            continue

        local_min = float(np.nanmin(yw))
        amp0 = max(float(pk.get('height', np.nan)) - local_min,
                   float(pk.get('prominence', 0.0)), 1e-4)
        width0 = fixed_fwhm / 2.0 if fixed_fwhm else max(pk.get('fwhm_cm1', 12.0) / 2.0, 2.0)

        def local_model(xv, amp, mu, width, c0, c1):
            return peak_func(xv, amp, mu, abs(width)) + c0 + c1 * (xv - mu0)

        p0 = [amp0, mu0, width0, local_min, 0.0]
        bounds_l = [0.0, mu0 - 18.0, 0.5, -0.5, -np.inf]
        bounds_u = [max(np.nanmax(yw) * 2.5, amp0 * 3.0), mu0 + 18.0, 80.0, np.nanmax(yw), np.inf]
        try:
            popt, _ = optimize.curve_fit(
                local_model, xw, yw, p0=p0, bounds=(bounds_l, bounds_u),
                maxfev=5000,
            )
        except Exception:
            popt = np.array(p0, dtype=float)
            logger.warning("IR peak fit failed; using initial parameters.", exc_info=True)

        amp, mu, width, c0, c1 = popt
        width = abs(width)
        if peak_type == 'gaussian':
            fwhm = 2.355 * width
            area = amp * width * np.sqrt(2.0 * np.pi)
        else:
            fwhm = 2.0 * width
            area = np.pi * amp * width

        model_vals = local_model(xw, *popt)
        existing = y_fit[mask]
        if np.any(np.isfinite(existing)):
            y_fit[mask] = np.where(np.isfinite(existing), np.maximum(existing, model_vals), model_vals)
        else:
            y_fit[mask] = model_vals

        fitted_peaks.append({
            'index': i,
            'wavenumber': float(mu),
            'height': float(amp),
            'fwhm_cm1': float(fwhm),
            'area': float(area),
            'prominence': float(pk.get('prominence', np.nan)),
            'assignment': peaks[i].get('assignment', ''),
            'idx': pk.get('idx'),
        })

    fit_mask = np.isfinite(y_fit)
    if np.sum(fit_mask) >= 3:
        ss_res = np.sum((y[fit_mask] - y_fit[fit_mask])**2)
        ss_tot = np.sum((y[fit_mask] - np.mean(y[fit_mask]))**2)
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
        y_plot = np.where(fit_mask, y_fit, y)
    else:
        r2 = np.nan
        y_plot = np.array([])

    fitted_peaks.sort(key=lambda p: p['wavenumber'], reverse=True)
    for i, pk in enumerate(fitted_peaks):
        pk['index'] = i
    return fitted_peaks, float(r2), y_plot


# ---------------------------------------------------------------------------
#  Peak assignment against database
# ---------------------------------------------------------------------------

def assign_peaks(peaks: List[Dict[str, Any]],
                 polymer_db: Dict[str, List[Tuple[float, str, str, bool]]],
                 tolerance_cm1: float = 10.0,
                 polymer_name: str = "",
                 ) -> List[Dict[str, Any]]:
    """Match detected peaks against polymer IR database.

    Returns peaks with 'assignment', 'intensity', 'crystalline' added.
    """
    polymer_db = normalize_ir_polymer_database(polymer_db)
    polymer_key = normalize_ir_polymer_name(polymer_name)

    # Material assignments are opt-in.  An empty hint must remain generic;
    # searching the complete built-in database would silently invent identity.
    if polymer_key and polymer_key in polymer_db:
        dbs = {polymer_key: polymer_db[polymer_key]}
    else:
        dbs = {}

    for pk in peaks:
        wn = pk['wavenumber']
        best_match = None
        best_dist = tolerance_cm1

        for poly, entries in dbs.items():
            for ref_wn, assignment, intensity, is_cryst in entries:
                dist = abs(wn - ref_wn)
                if dist < best_dist:
                    best_dist = dist
                    best_match = {
                        'assignment': assignment,
                        'intensity': intensity,
                        'crystalline': is_cryst,
                        'ref_wavenumber': ref_wn,
                        'delta_cm1': dist,
                        'polymer': poly,
                    }

        if best_match:
            pk['assignment'] = best_match['assignment']
            pk['intensity'] = best_match['intensity']
            pk['crystalline'] = best_match['crystalline']
            pk['ref_wavenumber'] = best_match['ref_wavenumber']
            pk['delta_cm1'] = best_match['delta_cm1']
            pk['polymer'] = best_match['polymer']
        else:
            pk['assignment'] = 'unknown'
            pk['crystalline'] = False

    return peaks


def identify_polymer_from_peaks(peaks: List[Dict[str, Any]],
                                polymer_db: Dict[str, List[Tuple[float, str, str, bool]]],
                                tolerance_cm1: float = 15.0,
                                ) -> Tuple[str, float]:
    """Return the best polymer database match and a 0..1 confidence score."""
    if not peaks:
        return "", np.nan

    polymer_db = normalize_ir_polymer_database(polymer_db)
    intensity_weight = {'vs': 3.0, 's': 2.0, 'm': 1.2, 'w': 0.6}
    max_prom = max((float(p.get('prominence', 0.0)) for p in peaks), default=0.0)
    if max_prom <= 0:
        max_prom = max((float(p.get('height', 0.0)) for p in peaks), default=1.0)
    max_prom = max(max_prom, 1e-12)
    best_polymer = ""
    best_score = 0.0
    for polymer, entries in polymer_db.items():
        evidence = 0.0
        possible = 0.0
        for pk in peaks[:25]:
            peak_weight = float(pk.get('prominence', pk.get('height', 0.0))) / max_prom
            peak_weight = max(peak_weight, 0.05)
            possible += peak_weight * max(intensity_weight.values())
            best_dist = tolerance_cm1
            best_intensity = ""
            for ref_wn, _assignment, intensity, _is_cryst in entries:
                dist = abs(float(pk['wavenumber']) - float(ref_wn))
                if dist < best_dist:
                    best_dist = dist
                    best_intensity = intensity
            if best_intensity:
                evidence += (
                    peak_weight
                    * intensity_weight.get(str(best_intensity).lower(), 1.0)
                    * (1.0 - best_dist / tolerance_cm1)
                )
            elif peak_weight > 0.12:
                evidence -= 0.6 * peak_weight
        score = max(evidence, 0.0) / possible if possible > 0 else 0.0
        if score > best_score:
            best_score = score
            best_polymer = polymer

    if best_score < 0.08:
        return "", best_score
    return best_polymer, best_score


# ---------------------------------------------------------------------------
#  Experimental-computational comparison
# ---------------------------------------------------------------------------

def match_computed_to_experiment(peaks: List[Dict[str, Any]],
                                  modes: List[ComputedMode],
                                  tolerance_cm1: float = 20.0,
                                  ) -> List[Dict[str, Any]]:
    """Match computed vibrational modes to experimental peaks.

    Returns list of matches with delta, assignment.
    """
    matches = []
    used_modes = set()

    for pk in peaks:
        wn_exp = pk['wavenumber']
        best_mode = None
        best_dist = tolerance_cm1

        for i, mode in enumerate(modes):
            if i in used_modes:
                continue
            dist = abs(wn_exp - mode.frequency_cm1)
            if dist < best_dist:
                best_dist = dist
                best_mode = mode

        if best_mode:
            used_modes.add(best_mode.index - 1)
            matches.append({
                'exp_cm1': wn_exp,
                'calc_cm1': best_mode.frequency_cm1,
                'delta_cm1': best_dist,
                'ir_intensity': best_mode.ir_intensity_km_mol,
                'assignment': pk.get('assignment', ''),
            })

    # Add unmatched computed modes
    for i, mode in enumerate(modes):
        if i not in used_modes and mode.ir_intensity_km_mol > 1.0:
            matches.append({
                'exp_cm1': np.nan,
                'calc_cm1': mode.frequency_cm1,
                'delta_cm1': np.nan,
                'ir_intensity': mode.ir_intensity_km_mol,
                'assignment': 'unmatched',
            })

    return matches


# ---------------------------------------------------------------------------
#  Crystallinity quantification
# ---------------------------------------------------------------------------

def compute_crystallinity_ratio(spectrum: IRSpectrum,
                                 cryst_band: float,
                                 ref_band: float,
                                 tolerance: float = 10.0,
                                 ) -> float:
    """Compute crystallinity index from band ratio.

    Xc ∝ A_crystalline / A_reference

    Returns ratio (not percentage — needs calibration curve).
    """
    wn = spectrum.wavenumber
    A = spectrum.absorbance

    if len(wn) == 0:
        return np.nan

    # Find band intensities at specified wavenumbers
    def band_intensity(target):
        idx = np.argmin(np.abs(wn - target))
        # Use peak height in a ±tolerance window
        window_mask = np.abs(wn - target) <= tolerance
        if np.sum(window_mask) > 0:
            return np.max(A[window_mask])
        return A[idx] if idx < len(A) else 0.0

    A_cryst = band_intensity(cryst_band)
    A_ref = band_intensity(ref_band)

    if A_ref < 1e-6:
        return np.nan

    return A_cryst / A_ref


def measure_band_height(wavenumber: np.ndarray, absorbance: np.ndarray,
                        target: float, tolerance: float = 10.0,
                        ) -> float:
    """Peak height near a target band after local minimum subtraction."""
    wn = np.asarray(wavenumber, dtype=float)
    A = np.asarray(absorbance, dtype=float)
    if len(wn) == 0:
        return np.nan
    mask = np.abs(wn - target) <= tolerance
    if not np.any(mask):
        idx = int(np.argmin(np.abs(wn - target)))
        lo = max(0, idx - 3)
        hi = min(len(A), idx + 4)
        mask = np.zeros(len(A), dtype=bool)
        mask[lo:hi] = True
    local = A[mask]
    if local.size == 0:
        return np.nan
    return float(np.nanmax(local) - np.nanmin(local))


def measure_band_area(wavenumber: np.ndarray, absorbance: np.ndarray,
                      target: float, tolerance: float = 10.0,
                      ) -> float:
    """Positive area near a target band after local minimum subtraction."""
    wn = np.asarray(wavenumber, dtype=float)
    A = np.asarray(absorbance, dtype=float)
    mask = np.abs(wn - target) <= tolerance
    if np.sum(mask) < 2:
        return np.nan
    x = wn[mask]
    y = A[mask] - np.nanmin(A[mask])
    order = np.argsort(x)
    return float(np.trapezoid(np.clip(y[order], 0.0, None), x[order]))


def compute_polymer_band_indices(spectrum: IRSpectrum, polymer_name: str,
                                 tolerance: float = 10.0,
                                 ) -> Dict[str, float]:
    """Compute common ordinary-FTIR band indices for polymer families."""
    polymer_key = normalize_ir_polymer_name(polymer_name)
    if not polymer_key:
        return {}
    wn, A = spectrum.wavenumber, spectrum.absorbance
    def b(target: float) -> float:
        return measure_band_height(wn, A, target, tolerance=tolerance)
    indices: Dict[str, float] = {}

    def frac(name: str, numerator: float, denominator_terms: List[float]):
        vals = [b(v) for v in denominator_terms]
        num = b(numerator)
        den = float(np.nansum(vals))
        if np.isfinite(num) and den > 1e-9:
            indices[name] = float(100.0 * num / den)

    if polymer_key == "PE":
        frac("PE_crystalline_730", 730.0, [730.0, 720.0])
    elif polymer_key == "PP":
        frac("PP_crystalline_998", 998.0, [998.0, 973.0])
    elif polymer_key == "PET":
        frac("PET_trans_1340", 1340.0, [1340.0, 1370.0])
    elif polymer_key == "PVDF":
        a840 = b(840.0)
        a763 = b(763.0)
        den = a840 + 1.26 * a763
        if np.isfinite(a840) and den > 1e-9:
            indices["PVDF_beta_fraction"] = float(100.0 * a840 / den)
    elif polymer_key == "PA6":
        a1637 = b(1637.0)
        for band in (1200.0, 1120.0, 929.0):
            aval = b(band)
            if np.isfinite(aval) and np.isfinite(a1637) and a1637 > 1e-9:
                indices[f"PA6_A{int(band)}_A1637"] = float(100.0 * aval / a1637)

    return indices


def compute_crystallinity_from_db(polymer_name: str,
                                   cryst_band: float,
                                   ref_band: float,
                                   ratio: float,
                                   ) -> float:
    """Convert band ratio to crystallinity percentage using known calibrations.

    Currently returns raw ratio — user should calibrate with DSC/XRD.
    """
    return ratio * 100.0  # Placeholder — needs calibration


# ---------------------------------------------------------------------------
#  Full analysis pipeline
# ---------------------------------------------------------------------------

def analyze_spectrum(spectrum: IRSpectrum, config: IRConfig,
                     label: str = "",
                     computed_modes: Optional[List[ComputedMode]] = None,
                     polymer_name: str = "",
                     ) -> IRResult:
    """Run full IR analysis on one spectrum.

    Parameters
    ----------
    spectrum : IRSpectrum
    config : IRConfig
    label : str
    computed_modes : list of ComputedMode, optional
        For experimental-computational comparison.
    polymer_name : str
        For peak assignment database lookup.
    """
    result = IRResult(label=label)

    if not spectrum.has_data:
        return result

    wn = spectrum.wavenumber
    A = spectrum.absorbance

    result.wavenumber = wn
    result.absorbance = A

    polymer_hint = normalize_ir_polymer_name(polymer_name or getattr(config, "polymer_name", ""))

    # 1. Detect peaks
    peaks = detect_peaks(wn, A,
                         height_frac=config.peak_height_min,
                         distance=config.peak_distance,
                         prominence_frac=getattr(config, "peak_prominence_min", 0.015),
                         max_peaks=getattr(config, "peak_max_count", 40))

    if polymer_hint:
        result.polymer_score = 1.0
    result.polymer_name = polymer_hint

    # 2. Fit peaks
    if peaks:
        assign_peaks(peaks, config.polymer_peaks_db,
                     tolerance_cm1=getattr(config, "assignment_tolerance_cm1", 15.0),
                     polymer_name=polymer_hint)
        fit_shape = config.lineshape if config.lineshape in ('lorentzian', 'gaussian') else 'lorentzian'
        fitted_peaks, r2, A_fit = fit_peaks(wn, A, peaks,
                                             peak_type=fit_shape,
                                             window_cm1=getattr(config, "peak_fit_window_cm1", 35.0))
        assign_peaks(fitted_peaks, config.polymer_peaks_db,
                     tolerance_cm1=getattr(config, "assignment_tolerance_cm1", 15.0),
                     polymer_name=polymer_hint)
        result.peaks = fitted_peaks
        result.n_peaks = len(fitted_peaks)
        result.r_squared = r2
        result.absorbance_fit = A_fit

    # 4. Crystallinity
    if config.crystallinity_band and config.crystallinity_ref_band:
        try:
            cryst_band = float(config.crystallinity_band)
            ref_band = float(config.crystallinity_ref_band)
            ratio = compute_crystallinity_ratio(
                spectrum, cryst_band, ref_band)
            result.Xc_pct = ratio * 100.0  # raw ratio × 100
            result.Xc_method = 'band_ratio'
            result.Xc_calibration_status = 'uncalibrated_index'
            result.Xc_band = config.crystallinity_band
            result.Xc_ref_band = config.crystallinity_ref_band
        except ValueError:
            pass
    else:
        result.band_indices = compute_polymer_band_indices(
            spectrum, result.polymer_name,
            tolerance=getattr(config, "band_tolerance_cm1", 10.0))
        if result.band_indices:
            first_key = next(iter(result.band_indices))
            result.Xc_pct = result.band_indices[first_key]
            result.Xc_method = f'{first_key}_uncalibrated'
            result.Xc_calibration_status = 'uncalibrated_index'
            result.Xc_band = first_key

    # 5. Computational comparison
    if computed_modes:
        result.computed_modes = computed_modes
        # Simulate spectrum
        result.simulated_spectrum = simulate_spectrum(
            computed_modes,
            lineshape=config.lineshape,
            fwhm=config.fwhm_default,
        )
        # Match
        if result.peaks:
            result.matches = match_computed_to_experiment(
                result.peaks, computed_modes)

    return result
