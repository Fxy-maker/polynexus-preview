"""DSC core analysis module.

Computes:
    - Glass transition temperature Tg (4 methods)
    - Melting temperature Tm (onset, peak, end)
    - Melting enthalpy DHm
    - Crystallisation temperature Tc and enthalpy DHc
    - Cold-crystallisation analysis
    - Crystallinity Xc
    - Multi-peak deconvolution (Gaussian / Lorentzian / Voigt)
    - Data quality metrics
"""
import logging
logger = logging.getLogger(__name__)


import numpy as np
from scipy import signal, optimize
from scipy.ndimage import uniform_filter1d
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

from ..engine import logger
from .io import DSCScan
from .config import DSCConfig


# ---------------------------------------------------------------------------
#  Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class DSCResult:
    """Container for DSC analysis results."""
    label: str = ""
    technique: str = "static"

    # Glass transition
    Tg_C: float = np.nan
    Tg_method: str = ""
    DTg_C: float = np.nan
    DCp_JgK: float = np.nan

    # Primary melting (strongest endotherm)
    Tm_onset_C: float = np.nan
    Tm_peak_C: float = np.nan
    Tm_end_C: float = np.nan
    DHm_Jg: float = np.nan

    # Secondary melting peaks
    Tm2_peak_C: float = np.nan
    DHm2_Jg: float = np.nan
    Tm3_peak_C: float = np.nan
    DHm3_Jg: float = np.nan

    # Primary crystallisation (strongest exotherm)
    Tc_onset_C: float = np.nan
    Tc_peak_C: float = np.nan
    Tc_end_C: float = np.nan
    DHc_Jg: float = np.nan

    # Secondary crystallisation peaks
    Tc2_peak_C: float = np.nan
    DHc2_Jg: float = np.nan

    # Cold crystallisation (exotherm below Tm on heating)
    Tcc_onset_C: float = np.nan
    Tcc_peak_C: float = np.nan
    DHcc_Jg: float = np.nan

    # Crystallinity
    Xc_pct: float = np.nan
    Xc_method: str = ""
    DHm0_Jg: float = np.nan
    DHm0_source: str = ""
    baseline_sensitivity_pct: float = np.nan
    integration_boundary_sensitivity_pct: float = np.nan
    DHm_Jg_mean: float = np.nan
    DHm_Jg_std: float = np.nan
    DHcc_Jg_mean: float = np.nan
    DHcc_Jg_std: float = np.nan
    Xc_pct_mean: float = np.nan
    Xc_pct_std: float = np.nan
    Xc_pct_ci95: float = np.nan
    baseline_variant_count: int = 0
    integration_variant_count: int = 0

    # All detected peaks (for deconvolution / detailed reporting)
    peak_components: List[Dict[str, Any]] = field(default_factory=list)

    # Quality metrics
    quality_score: float = 1.0
    quality_flags: List[str] = field(default_factory=list)
    r_squared: float = np.nan
    fit_rmse: float = np.nan
    fit_regions: List[Dict[str, Any]] = field(default_factory=list)

    # Raw data references (for plotting)
    T: np.ndarray = field(default_factory=lambda: np.array([]))
    HF: np.ndarray = field(default_factory=lambda: np.array([]))
    HF_fit: np.ndarray = field(default_factory=lambda: np.array([]))

    @property
    def parameters(self) -> Dict[str, Any]:
        """Return a flat dict of key parameters (always all columns)."""
        return {
            'scan_label': self.label,
            'Tg_C': self.Tg_C, 'Tg_method': self.Tg_method,
            'DTg_C': self.DTg_C, 'DCp_JgK': self.DCp_JgK,
            'Tm_onset_C': self.Tm_onset_C, 'Tm_peak_C': self.Tm_peak_C,
            'Tm_end_C': self.Tm_end_C, 'DHm_Jg': self.DHm_Jg,
            'Tm2_peak_C': self.Tm2_peak_C, 'DHm2_Jg': self.DHm2_Jg,
            'Tm3_peak_C': self.Tm3_peak_C, 'DHm3_Jg': self.DHm3_Jg,
            'Tc_onset_C': self.Tc_onset_C, 'Tc_peak_C': self.Tc_peak_C,
            'DHc_Jg': self.DHc_Jg,
            'Tc2_peak_C': self.Tc2_peak_C, 'DHc2_Jg': self.DHc2_Jg,
            'Tcc_onset_C': self.Tcc_onset_C, 'Tcc_peak_C': self.Tcc_peak_C,
            'DHcc_Jg': self.DHcc_Jg,
            'Xc_pct': self.Xc_pct, 'Xc_method': self.Xc_method,
            'DHm0_Jg': self.DHm0_Jg,
            'DHm0_source': self.DHm0_source,
            'baseline_sensitivity_pct': self.baseline_sensitivity_pct,
            'integration_boundary_sensitivity_pct': self.integration_boundary_sensitivity_pct,
            'DHm_Jg_mean': self.DHm_Jg_mean,
            'DHm_Jg_std': self.DHm_Jg_std,
            'DHcc_Jg_mean': self.DHcc_Jg_mean,
            'DHcc_Jg_std': self.DHcc_Jg_std,
            'Xc_pct_mean': self.Xc_pct_mean,
            'Xc_pct_std': self.Xc_pct_std,
            'Xc_pct_ci95': self.Xc_pct_ci95,
            'baseline_variant_count': self.baseline_variant_count,
            'integration_variant_count': self.integration_variant_count,
            'quality_score': self.quality_score,
            'r_squared': self.r_squared,
            'fit_rmse': self.fit_rmse,
            'n_peaks': len(self.peak_components),
        }


# ---------------------------------------------------------------------------
#  Glass transition temperature Tg
# ---------------------------------------------------------------------------

def _safe_derivative(y: np.ndarray, x: np.ndarray) -> np.ndarray:
    """dy/dx with protection against repeated or nearly repeated x values."""
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


def _compute_Tg_inflection(T: np.ndarray, HF: np.ndarray) -> Tuple[float, float]:
    """Tg by inflection point (max derivative)."""
    dHF = _safe_derivative(HF, T)
    idx = np.argmax(dHF)
    return float(T[idx]), float(dHF[idx])


def _compute_Tg_half_height(T: np.ndarray, HF: np.ndarray,
                            search_range: Optional[Tuple[float, float]] = None,
                            ) -> Tuple[float, float, float]:
    """Tg by half-height method.

    Fit linear baselines before and after the transition;
    Tg = temperature at the midpoint between extrapolated baselines.

    Returns (Tg, DCp, width).
    """
    dHF = _safe_derivative(HF, T)
    noise = np.std(dHF)

    if search_range is not None:
        mask = (T >= search_range[0]) & (T <= search_range[1])
        dHF_roi = dHF.copy()
        dHF_roi[~mask] = 0
    else:
        dHF_roi = dHF

    # Find transition region (high derivative)
    peak_idx = np.argmax(dHF_roi)
    threshold = max(0.3 * dHF_roi[peak_idx], 3 * noise)

    # Extend outward until derivative drops below threshold
    left = peak_idx
    while left > 0 and dHF[left] > threshold:
        left -= 1
    right = peak_idx
    while right < len(T) - 1 and dHF[right] > threshold:
        right += 1

    # Extrapolated baselines
    pre_region = slice(max(0, left - 30), max(1, left - 5))
    post_region = slice(min(len(T) - 1, right + 5), min(len(T), right + 30))

    if pre_region.stop - pre_region.start < 3 or post_region.stop - post_region.start < 3:
        # Fallback: use ends
        pre_fit = np.polyfit(T[:max(1, left - 5)], HF[:max(1, left - 5)], 1)
        post_fit = np.polyfit(T[min(len(T) - 1, right + 5):], HF[min(len(T) - 1, right + 5):], 1)
    else:
        pre_fit = np.polyfit(T[pre_region], HF[pre_region], 1)
        post_fit = np.polyfit(T[post_region], HF[post_region], 1)

    pre_line = np.polyval(pre_fit, T)
    post_line = np.polyval(post_fit, T)

    # Midpoint between extrapolated lines
    mid_line = (pre_line + post_line) / 2.0
    actual_mid = (np.polyval(pre_fit, T[peak_idx]) + np.polyval(post_fit, T[peak_idx])) / 2.0

    # Find where actual HF crosses actual_mid
    diff = HF - actual_mid
    crossings = np.where(np.diff(np.sign(diff)))[0]
    if len(crossings) == 0:
        return float(T[peak_idx]), 0.0, 0.0

    # Use crossing nearest to peak
    best = crossings[np.argmin(np.abs(crossings - peak_idx))]
    Tg_val = float(T[best])
    DCp_raw = float(post_fit[0] - pre_fit[0])
    DCp = DCp_raw * (T[right] - T[left])
    width = float(T[right] - T[left])

    # Validity gate: Tg must be within search range (if specified)
    # and the Cp step must be significant
    if search_range is not None:
        if Tg_val < search_range[0] or Tg_val > search_range[1]:
            return np.nan, DCp, width
    # Require detectable Cp step (> 0.01 J/gK and width > 2°C)
    hf_range = float(np.ptp(HF))
    min_dcp = max(0.01, hf_range * 0.01)
    if abs(DCp_raw) < min_dcp or width < 2.0:
        return np.nan, DCp, width
    return Tg_val, DCp, width


def _compute_Tg_onset(T: np.ndarray, HF: np.ndarray) -> Tuple[float, float]:
    """Tg by onset method: intersection of pre-transition baseline
    and tangent at inflection point."""
    dHF = _safe_derivative(HF, T)
    peak_idx = np.argmax(dHF)
    slope = dHF[peak_idx]
    intercept = HF[peak_idx] - slope * T[peak_idx]

    # Fit pre-transition baseline
    left = max(0, peak_idx - 40)
    pre_fit = np.polyfit(T[left:max(1, peak_idx - 10)],
                         HF[left:max(1, peak_idx - 10)], 1)
    # Intersection
    a1, b1 = pre_fit
    a2, b2 = slope, intercept
    if abs(a1 - a2) < 1e-12:
        return float(T[peak_idx]), dHF[peak_idx]
    T_onset = (b2 - b1) / (a1 - a2)
    return float(T_onset), float(slope)


def compute_Tg(T: np.ndarray, HF: np.ndarray,
               method: str = 'half_height',
               search_range: Optional[Tuple[float, float]] = None,
               ) -> Dict[str, Any]:
    """Compute glass transition temperature.

    Parameters
    ----------
    method : str
        'inflection' — peak of derivative
        'half_height' — midpoint between extrapolated pre/post baselines
        'onset' — intersection of pre-baseline and inflection tangent
    search_range : (T_low, T_high), optional

    Returns
    -------
    dict with keys: Tg_C, method, DTg_C, DCp_JgK
    """
    result = {'Tg_C': np.nan, 'method': method, 'DTg_C': np.nan, 'DCp_JgK': np.nan}

    if len(T) < 20:
        return result

    try:
        if method == 'inflection':
            tg, _ = _compute_Tg_inflection(T, HF)
            result['Tg_C'] = tg
        elif method == 'half_height':
            tg, dCp, width = _compute_Tg_half_height(T, HF, search_range)
            result['Tg_C'] = tg
            result['DCp_JgK'] = dCp
            result['DTg_C'] = width
        elif method == 'onset':
            tg, _ = _compute_Tg_onset(T, HF)
            result['Tg_C'] = tg
        elif method == 'fictive':
            # Fictive temperature: enthalpy method
            # Approximated as half-height for now
            tg, dCp, width = _compute_Tg_half_height(T, HF, search_range)
            result['Tg_C'] = tg
            result['DTg_C'] = width
    except Exception as e:
        logger.warning("DSC Tg 检测失败: %s", e, exc_info=True)
        logger.warning("异常已处理", exc_info=True)

    return result


# ---------------------------------------------------------------------------
#  Melting / crystallisation peak detection
# ---------------------------------------------------------------------------

def _integrate_abs_temperature(T: np.ndarray, y: np.ndarray) -> float:
    """Integrate a peak over absolute temperature increments."""
    if len(T) < 2 or len(y) < 2:
        return 0.0
    dx = np.abs(np.diff(T))
    yy = np.asarray(y, dtype=float)
    return float(np.sum(0.5 * (yy[:-1] + yy[1:]) * dx))


def _local_linear_baseline(T: np.ndarray, HF: np.ndarray,
                           left: int, right: int) -> np.ndarray:
    """Linear baseline connecting event endpoints."""
    left = int(np.clip(left, 0, len(T) - 1))
    right = int(np.clip(right, 0, len(T) - 1))
    if right <= left:
        return np.zeros(1, dtype=float)
    denom = T[right] - T[left]
    if abs(float(denom)) < 1e-12:
        return np.full(right - left + 1, HF[left], dtype=float)
    x = T[left:right + 1]
    return HF[left] + (HF[right] - HF[left]) * (x - T[left]) / denom


def _reintegrate_event_variants(
    T: np.ndarray,
    HF: np.ndarray,
    event: Optional[Dict[str, Any]],
    is_endotherm: bool,
) -> Dict[str, Any]:
    """Reintegrate one event with simple baseline and boundary variants."""
    if not isinstance(event, dict) or "index_range" not in event:
        return {"enthalpies": [], "baseline_variant_count": 0, "integration_variant_count": 0}

    T_arr = np.asarray(T, dtype=float)
    HF_arr = np.asarray(HF, dtype=float)
    if len(T_arr) < 5 or len(T_arr) != len(HF_arr):
        return {"enthalpies": [], "baseline_variant_count": 0, "integration_variant_count": 0}

    try:
        base_left, base_right = event["index_range"]
        base_left = int(base_left)
        base_right = int(base_right)
    except Exception:
        return {"enthalpies": [], "baseline_variant_count": 0, "integration_variant_count": 0}

    signed = -1.0 if is_endotherm else 1.0
    boundary_shifts = (-1, 0, 1)
    enthalpies: list[float] = []
    baseline_names = {"endpoint_linear", "constant_endpoint_mean", "edge_mean_linear"}

    for left_shift in boundary_shifts:
        for right_shift in boundary_shifts:
            left = int(np.clip(base_left + left_shift, 0, len(T_arr) - 2))
            right = int(np.clip(base_right + right_shift, left + 2, len(T_arr) - 1))
            if right - left < 3:
                continue

            x = T_arr[left:right + 1]
            y = HF_arr[left:right + 1]
            if len(x) < 3 or not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
                continue

            endpoint_linear = _local_linear_baseline(T_arr, HF_arr, left, right)
            constant_endpoint_mean = np.full_like(y, float((HF_arr[left] + HF_arr[right]) / 2.0), dtype=float)

            edge_width = max(1, min(5, len(y) // 5))
            left_mean = float(np.nanmean(y[:edge_width]))
            right_mean = float(np.nanmean(y[-edge_width:]))
            denom = x[-1] - x[0]
            if abs(float(denom)) < 1e-12:
                edge_mean_linear = np.full_like(y, left_mean, dtype=float)
            else:
                edge_mean_linear = left_mean + (right_mean - left_mean) * (x - x[0]) / denom

            for baseline in (endpoint_linear, constant_endpoint_mean, edge_mean_linear):
                signal_pos = np.clip(signed * (y - baseline), 0.0, None)
                enthalpy = _integrate_abs_temperature(x, signal_pos)
                if np.isfinite(enthalpy):
                    enthalpies.append(float(enthalpy))

    return {
        "enthalpies": enthalpies,
        "baseline_variant_count": len(baseline_names),
        "integration_variant_count": len(enthalpies),
    }


def _find_thermal_events_physical(T: np.ndarray, HF: np.ndarray,
                                  event_type: str = 'all',
                                  prominence_ratio: float = 0.03,
                                  min_enthalpy_Jg: float = 0.05,
                                  ) -> Dict[str, List[Dict[str, Any]]]:
    events: Dict[str, list] = {'melting': [], 'crystallisation': []}

    T_arr = np.asarray(T, dtype=float)
    HF_arr = np.asarray(HF, dtype=float)
    if len(T_arr) < 5 or len(T_arr) != len(HF_arr):
        return events

    valid = np.isfinite(T_arr) & np.isfinite(HF_arr)
    T_work = T_arr[valid]
    HF_work = HF_arr[valid]
    if len(T_work) < 5:
        return events

    keep = np.ones(len(T_work), dtype=bool)
    keep[1:] = np.abs(np.diff(T_work)) > 1e-10
    T_work = T_work[keep]
    HF_work = HF_work[keep]
    if len(T_work) < 5:
        return events

    hf_range = float(np.ptp(HF_work))
    if hf_range < 1e-12:
        return events

    smooth_win = max(3, min(51, len(HF_work) // 35))
    if smooth_win % 2 == 0:
        smooth_win += 1
    HF_smooth = uniform_filter1d(HF_work, size=smooth_win, mode='nearest')

    resid = HF_work - HF_smooth
    noise = float(1.4826 * np.median(np.abs(resid - np.median(resid))))
    if not np.isfinite(noise) or noise <= 1e-12:
        noise = float(np.std(np.diff(HF_smooth))) if len(HF_smooth) > 2 else 0.0
    if not np.isfinite(noise) or noise <= 1e-12:
        noise = hf_range * 0.005

    prominence = max(hf_range * float(prominence_ratio), noise * 5.0, 1e-6)
    distance = max(5, len(T_work) // 50)

    def _extract_event(peak_idx: int, is_endotherm: bool,
                       left_base: int, right_base: int) -> Optional[Dict[str, Any]]:
        n = len(T_work)
        left = int(np.clip(left_base, 0, n - 1))
        right = int(np.clip(right_base, 0, n - 1))

        if left >= peak_idx:
            left = max(0, peak_idx - 3)
        if right <= peak_idx:
            right = min(n - 1, peak_idx + 3)

        max_width = max(20, n // 3)
        left = max(left, peak_idx - max_width)
        right = min(right, peak_idx + max_width)

        signed = -1.0 if is_endotherm else 1.0
        for _ in range(2):
            if right - left < 4:
                break
            baseline = _local_linear_baseline(T_work, HF_work, left, right)
            sig = signed * (HF_work[left:right + 1] - baseline)
            peak_rel = peak_idx - left
            if peak_rel <= 0 or peak_rel >= len(sig):
                break
            peak_height = float(sig[peak_rel])
            if not np.isfinite(peak_height) or peak_height <= 0:
                return None
            threshold = max(peak_height * 0.02, noise * 2.0)

            l_candidates = np.where(sig[:peak_rel] <= threshold)[0]
            r_candidates = np.where(sig[peak_rel:] <= threshold)[0]
            new_left = left + int(l_candidates[-1]) if len(l_candidates) else left
            new_right = left + peak_rel + int(r_candidates[0]) if len(r_candidates) else right

            left = max(0, min(new_left - 1, peak_idx - 2))
            right = min(n - 1, max(new_right + 1, peak_idx + 2))

        baseline = _local_linear_baseline(T_work, HF_work, left, right)
        signal_pos = signed * (HF_work[left:right + 1] - baseline)
        signal_pos = np.clip(signal_pos, 0.0, None)
        enthalpy = _integrate_abs_temperature(T_work[left:right + 1], signal_pos)
        width_C = abs(float(T_work[right] - T_work[left]))

        if enthalpy < min_enthalpy_Jg or width_C < 0.05:
            return None

        return {
            'onset_C': float(T_work[left]),
            'peak_C': float(T_work[peak_idx]),
            'end_C': float(T_work[right]),
            'enthalpy_Jg': float(enthalpy),
            'signed_enthalpy_Jg': float(-enthalpy if is_endotherm else enthalpy),
            'height_Wg': float(np.max(signal_pos)) if len(signal_pos) else np.nan,
            'width_C': width_C,
            'is_endotherm': is_endotherm,
            'index_range': (int(left), int(right)),
        }

    def _detect_one_polarity(is_endotherm: bool) -> List[Dict[str, Any]]:
        y = -HF_smooth if is_endotherm else HF_smooth
        try:
            peaks, props = signal.find_peaks(
                y,
                prominence=prominence,
                distance=distance,
            )
        except Exception:
            return []

        out: List[Dict[str, Any]] = []
        try:
            _, _, left_ips, right_ips = signal.peak_widths(y, peaks, rel_height=0.55)
            left_bases = np.floor(left_ips).astype(int)
            right_bases = np.ceil(right_ips).astype(int)
        except Exception:
            left_bases = props.get('left_bases', np.maximum(0, peaks - distance))
            right_bases = props.get('right_bases', np.minimum(len(T_work) - 1, peaks + distance))
            logger.warning("异常已处理", exc_info=True)
        prominences = props.get('prominences', np.full(len(peaks), np.nan))
        for i, peak_idx in enumerate(peaks):
            if peak_idx < 2 or peak_idx > len(T_work) - 3:
                continue
            event = _extract_event(
                int(peak_idx),
                is_endotherm,
                int(left_bases[i]),
                int(right_bases[i]),
            )
            if event is not None:
                event['prominence_Wg'] = float(prominences[i])
                out.append(event)
        return out

    if event_type in ('all', 'melting'):
        events['melting'] = _detect_one_polarity(True)
    if event_type in ('all', 'crystallisation'):
        events['crystallisation'] = _detect_one_polarity(False)

    events['melting'].sort(key=lambda e: e['peak_C'])
    events['crystallisation'].sort(key=lambda e: e['peak_C'])
    return events


def find_thermal_events(T: np.ndarray, HF: np.ndarray,
                        event_type: str = 'all',
                        prominence_ratio: float = 0.03,
                        min_enthalpy_Jg: float = 0.05,
                        ) -> Dict[str, List[Dict[str, Any]]]:
    """Detect endothermic (melting) and exothermic (crystallisation) events.

    Exo-up convention: endotherms = negative peaks, exotherms = positive peaks.

    Peaks are detected on smoothed heat flow and integrated against a
    local baseline.  Cooling scans use absolute temperature increments.

    Parameters
    ----------
    event_type : 'melting', 'crystallisation', 'all'

    Returns
    -------
    {'melting': [...], 'crystallisation': [...]}
    Each event: {onset_C, peak_C, end_C, enthalpy_Jg, is_endotherm, index_range}
    """
    return _find_thermal_events_physical(
        T, HF,
        event_type=event_type,
        prominence_ratio=prominence_ratio,
        min_enthalpy_Jg=min_enthalpy_Jg,
    )

def compute_crystallinity(DHm_Jg: float, DHc_Jg: float,
                          DHm0_Jg: float = 293.0,
                          ) -> float:
    """Compute crystallinity from melting and crystallisation enthalpies.

    Xc = (DHm - DHc) / DHm0 * 100

    DHc is subtracted to account for cold crystallisation during heating.
    If there is no cold crystallisation, DHc = 0.
    """
    if np.isnan(DHm_Jg) or DHm0_Jg <= 0:
        return np.nan
    DHc = DHc_Jg if not np.isnan(DHc_Jg) else 0.0
    Xc = (DHm_Jg - DHc) / DHm0_Jg * 100.0
    return max(0.0, min(100.0, Xc))


# ---------------------------------------------------------------------------
#  Multi-peak deconvolution
# ---------------------------------------------------------------------------

def gaussian(x: np.ndarray, amp: float, mu: float, sigma: float) -> np.ndarray:
    """Gaussian peak."""
    return amp * np.exp(-0.5 * ((x - mu) / sigma) ** 2)


def lorentzian(x: np.ndarray, amp: float, mu: float, gamma: float) -> np.ndarray:
    """Lorentzian peak."""
    return amp * gamma ** 2 / ((x - mu) ** 2 + gamma ** 2)


def voigt(x: np.ndarray, amp: float, mu: float, sigma: float, gamma: float) -> np.ndarray:
    """Pseudo-Voigt (linear combination of Gaussian and Lorentzian)."""
    return amp * (0.5 * gaussian(x, 1.0, mu, sigma) +
                  0.5 * lorentzian(x, 1.0, mu, gamma))


def deconvolve_peaks(T: np.ndarray, HF: np.ndarray,
                     n_peaks: int = 2,
                     peak_type: str = 'gaussian',
                     initial_guesses: Optional[List[Dict[str, float]]] = None,
                     baseline: str = 'linear',
                     ) -> Dict[str, Any]:
    """Deconvolve overlapping melting/crystallisation peaks.

    Parameters
    ----------
    n_peaks : int
        Number of component peaks.
    peak_type : str
        'gaussian', 'lorentzian', 'voigt'.
    initial_guesses : list of dict, optional
        Each dict with keys: 'amp', 'mu', 'sigma' (and 'gamma' for voigt).
    baseline : str
        'linear', 'quadratic', 'none'.

    Returns
    -------
    dict with keys: components, baseline, residuals, r_squared
    """
    result: Dict[str, Any] = {'components': [], 'baseline': np.array([]),
                               'residuals': np.array([]), 'r_squared': np.nan}

    if len(T) < 10 or n_peaks < 1:
        return result
    peak_type = _normalise_peak_type(peak_type)

    # Auto-generate initial guesses if not provided
    if initial_guesses is None:
        initial_guesses = _auto_guess_peaks(T, HF, n_peaks)

    # Build model function
    def model(x, *params):
        # Baseline
        n_base = 0 if baseline == 'none' else (1 if baseline == 'constant' else 2)
        y = np.zeros_like(x, dtype=float)
        if baseline == 'linear':
            y = params[0] * x + params[1]
        elif baseline == 'quadratic':
            y = params[0] * x ** 2 + params[1] * x + params[2]
        elif baseline == 'constant':
            y = params[0]

        idx = n_base
        if peak_type == 'gaussian':
            for _ in range(n_peaks):
                y += gaussian(x, params[idx], params[idx + 1], params[idx + 2])
                idx += 3
        elif peak_type == 'lorentzian':
            for _ in range(n_peaks):
                y += lorentzian(x, params[idx], params[idx + 1], params[idx + 2])
                idx += 3
        elif peak_type == 'voigt':
            for _ in range(n_peaks):
                y += voigt(x, params[idx], params[idx + 1], params[idx + 2], params[idx + 3])
                idx += 4
        return y

    # Build initial parameter vector
    p0 = []
    if baseline == 'linear':
        p0.extend([0.0, np.mean(HF[:5]) if len(HF) > 5 else 0.0])
    elif baseline == 'quadratic':
        p0.extend([0.0, 0.0, np.mean(HF)])
    elif baseline == 'constant':
        p0.append(np.mean(HF))

    for g in initial_guesses:
        p0.append(g.get('amp', 1.0))
        p0.append(g.get('mu', np.mean(T)))
        p0.append(g.get('sigma', 5.0))
        if peak_type == 'voigt':
            p0.append(g.get('gamma', 2.0))

    p0 = np.array(p0)

    # Construct parameter bounds: keep peak centres within data range
    T_min, T_max = float(np.min(T)), float(np.max(T))
    T_range = max(T_max - T_min, 10.0)
    n_base = 0 if baseline == 'none' else (1 if baseline == 'constant' else 2)
    lower_bounds = []
    upper_bounds = []
    if baseline == 'linear':
        lower_bounds.extend([-np.inf, -np.inf])
        upper_bounds.extend([np.inf, np.inf])
    elif baseline == 'quadratic':
        lower_bounds.extend([-np.inf, -np.inf, -np.inf])
        upper_bounds.extend([np.inf, np.inf, np.inf])
    elif baseline == 'constant':
        lower_bounds.append(-np.inf)
        upper_bounds.append(np.inf)
    for _ in range(n_peaks):
        lower_bounds.extend([0.0, T_min - 10.0, 1.0])  # amp≥0, μ in [T_min-10, T_max+10], σ≥1
        upper_bounds.extend([np.inf, T_max + 10.0, T_range])
        if peak_type == 'voigt':
            lower_bounds.append(0.5)
            upper_bounds.append(T_range)
    bounds = (np.array(lower_bounds), np.array(upper_bounds))

    try:
        popt, _ = optimize.curve_fit(model, T, HF, p0=p0,
                                     bounds=bounds,
                                     maxfev=10000, method='trf')
    except Exception:
        # Fallback: use initial guesses as-is
        popt = p0
        logger.warning("异常已处理", exc_info=True)

    # Extract components
    n_base = 0 if baseline == 'none' else (1 if baseline == 'constant' else 2)
    base_params = popt[:n_base]

    if baseline == 'linear':
        base_y = base_params[0] * T + base_params[1]
    elif baseline == 'quadratic':
        base_y = base_params[0] * T ** 2 + base_params[1] * T + base_params[2]
    elif baseline == 'constant':
        base_y = np.full_like(T, base_params[0])
    else:
        base_y = np.zeros_like(T)

    result['baseline'] = base_y

    idx = n_base
    step = 3 if peak_type in ('gaussian', 'lorentzian') else 4
    for i in range(n_peaks):
        comp = {'index': i}
        if peak_type in ('gaussian', 'lorentzian'):
            comp['amp'] = float(popt[idx])
            comp['mu_C'] = float(popt[idx + 1])
            comp['sigma_C'] = float(abs(popt[idx + 2]))
        else:
            comp['amp'] = float(popt[idx])
            comp['mu_C'] = float(popt[idx + 1])
            comp['sigma_C'] = float(abs(popt[idx + 2]))
            comp['gamma_C'] = float(abs(popt[idx + 3]))
        # Area (approximate)
        if peak_type == 'gaussian':
            comp['area'] = float(comp['amp'] * comp['sigma_C'] * np.sqrt(2 * np.pi))
        elif peak_type == 'lorentzian':
            comp['area'] = float(comp['amp'] * np.pi * comp['sigma_C'])
        else:
            comp['area'] = float(comp['amp'] * comp['sigma_C'] * np.sqrt(2 * np.pi))
        # Fraction
        comp['fraction'] = 0.0
        idx += step
        result['components'].append(comp)

    # Compute fractions
    total_area = sum(c['area'] for c in result['components'])
    if total_area > 0:
        for c in result['components']:
            c['fraction'] = c['area'] / total_area

    # R-squared
    y_pred = model(T, *popt)
    ss_res = np.sum((HF - y_pred) ** 2)
    ss_tot = np.sum((HF - np.mean(HF)) ** 2)
    result['r_squared'] = float(1.0 - ss_res / ss_tot) if ss_tot > 0 else 1.0
    result['residuals'] = HF - y_pred

    return result


def _auto_guess_peaks(T: np.ndarray, HF: np.ndarray, n_peaks: int,
                      ) -> List[Dict[str, float]]:
    """Auto-generate peak initial guesses from negative derivative minima."""
    dHF = _safe_derivative(HF, T)
    neg = -dHF
    noise = np.std(neg) if np.std(neg) > 0 else 1e-6

    peaks, props = signal.find_peaks(neg, prominence=noise * 1.5)
    if len(peaks) < n_peaks:
        # Force n_peaks evenly spaced
        indices = np.linspace(len(T) // 4, 3 * len(T) // 4, n_peaks, dtype=int)
    else:
        # Take the n_peaks most prominent
        order = np.argsort(props['prominences'])[::-1]
        indices = peaks[order[:n_peaks]]

    guesses = []
    for idx in indices:
        idx = min(idx, len(T) - 1)
        guesses.append({
            'amp': float(abs(HF[idx]) * 2) if abs(HF[idx]) > noise else 1.0,
            'mu': float(T[idx]),
            'sigma': float(np.std(T) / n_peaks),
        })
    return guesses


def _normalise_peak_type(peak_type: str) -> str:
    key = str(peak_type or "gaussian").lower().replace("-", "_")
    if key in {"pseudo_voigt", "pseudovoigt"}:
        return "voigt"
    if key not in {"gaussian", "lorentzian", "voigt"}:
        return "gaussian"
    return key


# ---------------------------------------------------------------------------
#  Data quality assessment
# ---------------------------------------------------------------------------

def assess_quality(T: np.ndarray, HF: np.ndarray) -> Tuple[float, List[str]]:
    """Automated data quality assessment.

    Returns (score 0-1, flags).
    """
    flags = []
    score = 1.0

    # Check minimum data points
    if len(T) < 20:
        flags.append('too_few_points')
        score -= 0.3

    # Check for NaN/inf
    if np.any(~np.isfinite(T)) or np.any(~np.isfinite(HF)):
        flags.append('contains_nan_inf')
        score -= 0.3

    # Check signal-to-noise ratio
    noise = np.std(np.diff(HF))
    signal_range = np.ptp(HF)
    if noise > 0 and signal_range / noise < 5:
        flags.append('low_snr')
        score -= 0.2

    # Check for monotonic temperature
    if not (np.all(np.diff(T) > 0) or np.all(np.diff(T) < 0)):
        flags.append('non_monotonic_temperature')
        score -= 0.15

    # Check for flat signal (no transitions detected)
    if np.ptp(HF) < 0.01:
        flags.append('flat_signal')
        score -= 0.2

    return max(0.0, score), flags


def _finite_number(value: Any) -> bool:
    try:
        return bool(np.isfinite(float(value)))
    except (TypeError, ValueError):
        return False


def _peak_fit_centres(result: DSCResult) -> List[Dict[str, float]]:
    centres: List[Dict[str, float]] = []
    if _finite_number(result.Tm_peak_C):
        centres.append({"kind": "Tm", "center": float(result.Tm_peak_C), "sign": -1.0})
    if _finite_number(result.Tc_peak_C):
        centres.append({"kind": "Tc", "center": float(result.Tc_peak_C), "sign": 1.0})
    if _finite_number(result.Tcc_peak_C):
        centres.append({"kind": "Tcc", "center": float(result.Tcc_peak_C), "sign": 1.0})
    return centres


def _peak_model_value(x: np.ndarray, amp: float, mu: float, sigma: float, peak_type: str) -> np.ndarray:
    sigma = max(abs(float(sigma)), 1e-6)
    if peak_type == "lorentzian":
        return lorentzian(x, amp, mu, sigma)
    if peak_type == "voigt":
        return voigt(x, amp, mu, sigma, sigma)
    return gaussian(x, amp, mu, sigma)


def compute_peak_fit_quality(
    T: np.ndarray,
    HF: np.ndarray,
    result: DSCResult,
    config: DSCConfig,
    score_HF: np.ndarray | None = None,
    window_C: float = 30.0,
) -> Dict[str, Any]:
    """Fit detected DSC peak regions and return a local, parameter-sensitive R2."""
    t = np.asarray(T, dtype=float)
    y = np.asarray(HF, dtype=float)
    score_y = np.asarray(score_HF, dtype=float) if score_HF is not None else y
    centres = _peak_fit_centres(result)
    fit_full = np.full_like(y, np.nan, dtype=float)
    if len(t) < 12 or len(t) != len(y) or len(score_y) != len(y) or not centres:
        return {"r_squared": 0.0, "rmse": 0.0, "fit": fit_full, "regions": []}

    finite = np.isfinite(t) & np.isfinite(y) & np.isfinite(score_y)
    if np.count_nonzero(finite) < 12:
        return {"r_squared": 0.0, "rmse": 0.0, "fit": fit_full, "regions": []}

    t_min = float(np.nanmin(t[finite]))
    t_max = float(np.nanmax(t[finite]))
    usable = []
    mask = np.zeros_like(finite, dtype=bool)
    for centre in centres:
        c = float(centre["center"])
        if not (t_min - window_C <= c <= t_max + window_C):
            continue
        local = finite & (np.abs(t - c) <= window_C)
        if np.count_nonzero(local) >= 8:
            usable.append(centre)
            mask |= local

    if np.count_nonzero(mask) < 12 or not usable:
        return {"r_squared": 0.0, "rmse": 0.0, "fit": fit_full, "regions": []}

    x = t[mask]
    obs = y[mask]
    score_obs = score_y[mask]
    x_ref = float(np.mean(x))
    y_ref = float(np.median(obs))
    y_range = max(float(np.ptp(obs)), 1e-6)
    peak_type = _normalise_peak_type(getattr(config, "peak_function", "gaussian"))

    p0: List[float] = [y_ref, 0.0]
    lower: List[float] = [-np.inf, -np.inf]
    upper: List[float] = [np.inf, np.inf]

    for centre in usable:
        c = float(centre["center"])
        sign = float(centre["sign"])
        local = np.abs(x - c) <= min(window_C, 12.0)
        local_y = obs[local] if np.any(local) else obs
        if sign < 0:
            amp0 = float(np.min(local_y) - np.median(local_y))
            if abs(amp0) < y_range * 0.03:
                amp0 = -0.2 * y_range
            lower_amp, upper_amp = -np.inf, 0.0
        else:
            amp0 = float(np.max(local_y) - np.median(local_y))
            if abs(amp0) < y_range * 0.03:
                amp0 = 0.2 * y_range
            lower_amp, upper_amp = 0.0, np.inf
        p0.extend([amp0, c, 6.0])
        lower.extend([lower_amp, max(t_min, c - window_C), 0.5])
        upper.extend([upper_amp, min(t_max, c + window_C), 40.0])

    def model(x_vals: np.ndarray, *params: float) -> np.ndarray:
        baseline = params[0] + params[1] * (x_vals - x_ref)
        y_fit = np.asarray(baseline, dtype=float)
        idx = 2
        for _ in usable:
            y_fit = y_fit + _peak_model_value(x_vals, params[idx], params[idx + 1], params[idx + 2], peak_type)
            idx += 3
        return y_fit

    try:
        popt, _ = optimize.curve_fit(
            model,
            x,
            obs,
            p0=np.asarray(p0, dtype=float),
            bounds=(np.asarray(lower, dtype=float), np.asarray(upper, dtype=float)),
            method="trf",
            maxfev=20000,
        )
    except Exception:
        popt = np.asarray(p0, dtype=float)
        logger.warning("异常已处理", exc_info=True)

    y_fit = model(x, *popt)
    fit_full[mask] = y_fit
    residuals = score_obs - y_fit
    ss_res = float(np.sum(residuals**2))
    ss_tot = float(np.sum((score_obs - np.mean(score_obs)) ** 2))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 1.0
    rmse = float(np.sqrt(np.mean(residuals**2))) if len(residuals) else 0.0
    regions = [
        {
            "kind": centre["kind"],
            "center_C": float(centre["center"]),
            "start_C": max(t_min, float(centre["center"]) - window_C),
            "end_C": min(t_max, float(centre["center"]) + window_C),
        }
        for centre in usable
    ]
    return {
        "r_squared": float(r_squared) if np.isfinite(r_squared) else 0.0,
        "rmse": rmse,
        "fit": fit_full,
        "regions": regions,
    }


def aggregate_dsc_result_metrics(results: List[DSCResult]) -> Dict[str, Any]:
    """Return file-level DSC fit metrics from per-scan peak-fit results.

    Each scan-level ``DSCResult.r_squared`` is still a standard local peak
    fit R2.  For multi-segment DSC files, the AI tuning objective should see
    the whole file instead of only the first scan, while ignoring no-event
    segments that carry the sentinel 0.0 score.  The median keeps the score
    robust against a single extreme segment but still reacts when a parameter
    improves or degrades meaningful peak fits.
    """
    scan_rows: List[Dict[str, Any]] = []
    valid_r2: List[float] = []
    valid_rmse: List[float] = []
    valid_quality: List[float] = []

    for result in results or []:
        r2 = getattr(result, "r_squared", np.nan)
        rmse = getattr(result, "fit_rmse", np.nan)
        quality = getattr(result, "quality_score", np.nan)
        n_regions = len(getattr(result, "fit_regions", []) or [])
        row = {
            "label": getattr(result, "label", ""),
            "r_squared": float(r2) if _finite_number(r2) else None,
            "fit_rmse": float(rmse) if _finite_number(rmse) else None,
            "quality_score": float(quality) if _finite_number(quality) else None,
            "n_fit_regions": n_regions,
        }
        scan_rows.append(row)

        if _finite_number(r2) and n_regions > 0 and abs(float(r2)) > 1e-12:
            valid_r2.append(float(r2))
            if _finite_number(rmse):
                valid_rmse.append(float(rmse))
        if _finite_number(quality):
            valid_quality.append(float(quality))

    all_finite_r2 = [
        float(getattr(result, "r_squared"))
        for result in results or []
        if _finite_number(getattr(result, "r_squared", np.nan))
    ]
    aggregate_r2 = float(np.median(valid_r2)) if valid_r2 else (
        float(all_finite_r2[0]) if all_finite_r2 else 0.0
    )
    aggregate_rmse = float(np.median(valid_rmse)) if valid_rmse else np.nan
    aggregate_quality = float(np.median(valid_quality)) if valid_quality else np.nan

    return {
        "r_squared": aggregate_r2,
        "fit_rmse": aggregate_rmse,
        "quality_score": aggregate_quality,
        "scan_r_squared": scan_rows,
        "r_squared_method": "median_valid_scan_peak_fit_r2",
    }


# ---------------------------------------------------------------------------
#  Full analysis pipeline
# ---------------------------------------------------------------------------

def analyze_scan(T: np.ndarray, HF: np.ndarray, config: DSCConfig,
                 label: str = "", DHm0_override: Optional[float] = None,
                 fit_observed_HF: Optional[np.ndarray] = None,
                 ) -> DSCResult:
    """Run full DSC analysis on one scan.

    Parameters
    ----------
    T : ndarray
        Temperature in Celsius.
    HF : ndarray
        Heat flow in W/g, exo-up convention, baseline-corrected.
    config : DSCConfig
    label : str
    DHm0_override : float, optional
        Override reference enthalpy for crystallinity.

    Returns
    -------
    DSCResult
    """
    result = DSCResult(label=label)
    result.T = T
    result.HF = HF

    # ---- Determine scan direction ----
    dT_total = float(T[-1] - T[0])
    if abs(dT_total) < 5.0:
        result.technique = "isothermal"
    elif dT_total > 0:
        result.technique = "heating"
    else:
        result.technique = "cooling"

    # ---- Quality check ----
    result.quality_score, result.quality_flags = assess_quality(T, HF)

    # ---- Glass transition (heating scans only, skip isothermal / cooling) ----
    t_range = float(np.ptp(T))
    if t_range > 10.0 and result.technique == 'heating':
        # Narrow Tg search to typical polymer range: 20-120 °C
        tg = compute_Tg(T, HF, method=config.Tg_method,
                        search_range=(config.Tg_search_low_C, config.Tg_search_high_C))
        result.Tg_C = tg['Tg_C']
        result.Tg_method = config.Tg_method
        result.DTg_C = tg['DTg_C']
        result.DCp_JgK = tg['DCp_JgK']

    # ---- Thermal events ----
    is_heating = result.technique == "heating"
    is_cooling = result.technique == "cooling"

    min_event_dh = float(getattr(config, 'min_event_enthalpy_Jg', 0.05))
    prom_ratio = float(getattr(config, 'peak_prominence_ratio', 0.03))
    if is_cooling:
        # Cooling crystallisation peaks are often broader and less prominent
        prom_ratio = max(prom_ratio * 0.5, 0.01)
    events = find_thermal_events(
        T, HF,
        prominence_ratio=prom_ratio,
        min_enthalpy_Jg=min_event_dh,
    )

    melt_events = events['melting']
    cryst_events = events['crystallisation']
    primary_melt_event: Optional[Dict[str, Any]] = None
    primary_cold_cryst_event: Optional[Dict[str, Any]] = None

    if is_heating:
        # ---- Auto-fix convention: if strongest high-T peak is positive,
        #      the data is exo-down and needs flipping ----
        t_high = T > 150.0
        if np.sum(t_high) > 10:
            hf_high = HF[t_high]
            max_pos_ht = float(np.max(hf_high))
            max_neg_ht = float(np.abs(np.min(hf_high)))
            if max_pos_ht > max_neg_ht * 0.8 and max_pos_ht > 0.1:
                # Strong positive peak in melting region = exo-down
                # Flip the events classification
                melt_events, cryst_events = cryst_events, melt_events
                for e in melt_events:
                    e['is_endotherm'] = True
                for e in cryst_events:
                    e['is_endotherm'] = False

        # ---- Heating: melt events ----
        if melt_events:
            tm_low = float(getattr(config, 'Tm_search_low_C', 100.0))
            tm_high = float(getattr(config, 'Tm_search_high_C', 300.0))
            melt_events = [
                e for e in melt_events
                if tm_low <= float(e['peak_C']) <= tm_high
            ]
        if melt_events:
            # Filter: polymer melting peaks at typical rates should be narrow
            max_peak_width = float(getattr(config, 'max_melting_peak_width_C', 50.0))
            melt_events = [
                e for e in melt_events
                if (e['end_C'] - e['onset_C']) <= max_peak_width
            ]
        if melt_events:
            # Sort by enthalpy descending
            sorted_melt = sorted(melt_events, key=lambda e: e['enthalpy_Jg'], reverse=True)
            # Primary peak
            main = sorted_melt[0]
            primary_melt_event = main
            result.Tm_onset_C = main['onset_C']
            result.Tm_peak_C  = main['peak_C']
            result.Tm_end_C   = main['end_C']
            result.DHm_Jg     = main['enthalpy_Jg']
            # Secondary peaks
            if len(sorted_melt) >= 2:
                result.Tm2_peak_C = sorted_melt[1]['peak_C']
                result.DHm2_Jg    = sorted_melt[1]['enthalpy_Jg']
            if len(sorted_melt) >= 3:
                result.Tm3_peak_C = sorted_melt[2]['peak_C']
                result.DHm3_Jg    = sorted_melt[2]['enthalpy_Jg']
            # Store all in peak_components
            for e in melt_events:
                result.peak_components.append({
                    'type': 'melting',
                    'peak_C': e['peak_C'],
                    'onset_C': e['onset_C'],
                    'end_C': e['end_C'],
                    'enthalpy_Jg': e['enthalpy_Jg'],
                })

        # ---- Heating: cold crystallisation / recrystallisation events ----
        if cryst_events:
            tc_low = float(getattr(config, 'Tc_search_low_C', 50.0))
            tc_high = float(getattr(config, 'Tc_search_high_C', 250.0))
            cryst_events = [
                e for e in cryst_events
                if tc_low <= float(e['peak_C']) <= tc_high
            ]
        if cryst_events:
            edge_margin = float(getattr(config, 'edge_event_margin_C', 5.0))
            t_start = float(T[0])
            t_end = float(T[-1])
            cryst_events = [
                e for e in cryst_events
                if (abs(e['peak_C'] - t_start) >= edge_margin
                    and abs(e['peak_C'] - t_end) >= edge_margin)
            ]
            if not np.isnan(result.Tm_onset_C):
                margin = float(getattr(config, 'cold_cryst_max_margin_C', 5.0))
                cold_candidates = [
                    e for e in cryst_events
                    if e['peak_C'] < result.Tm_onset_C - margin
                ]
            else:
                cold_candidates = cryst_events

            sorted_cryst = sorted(
                cold_candidates,
                key=lambda e: abs(e['enthalpy_Jg']),
                reverse=True,
            )
            if sorted_cryst:
                main_cryst = sorted_cryst[0]
                primary_cold_cryst_event = main_cryst
                result.Tcc_onset_C = main_cryst['onset_C']
                result.Tcc_peak_C  = main_cryst['peak_C']
                result.DHcc_Jg     = main_cryst['enthalpy_Jg']
                if len(sorted_cryst) >= 2:
                    result.Tc2_peak_C = sorted_cryst[1]['peak_C']
                    result.DHc2_Jg    = sorted_cryst[1]['enthalpy_Jg']

            for e in cryst_events:
                peak_type = 'cold_crystallisation'
                if (not np.isnan(result.Tm_onset_C)
                        and e['peak_C'] >= result.Tm_onset_C - float(getattr(config, 'cold_cryst_max_margin_C', 5.0))):
                    peak_type = 'recrystallisation'
                result.peak_components.append({
                    'type': peak_type,
                    'peak_C': e['peak_C'],
                    'onset_C': e['onset_C'],
                    'end_C': e['end_C'],
                    'enthalpy_Jg': e['enthalpy_Jg'],
                })

    elif is_cooling:
        # ---- Cooling: cryst events (primary), require |DH| > 0.1 J/g ----
        min_dh_cool = max(0.1, min_event_dh)

        # Auto-detect: if the main feature on cooling is classified as
        # "melting" (endotherm), the exo-up convention is likely inverted.
        # Swap melt ↔ cryst event lists.
        best_melt_dh = max([abs(e['enthalpy_Jg']) for e in melt_events]) if melt_events else 0
        best_cryst_dh = max([abs(e['enthalpy_Jg']) for e in cryst_events]) if cryst_events else 0
        if best_melt_dh > 2.0 * best_cryst_dh and best_melt_dh > 1.0:
            # Polarity flipped: treat melt_events as crystallisation
            melt_events, cryst_events = cryst_events, melt_events

        if cryst_events:
            tc_low = float(getattr(config, 'Tc_search_low_C', 50.0))
            tc_high = float(getattr(config, 'Tc_search_high_C', 250.0))
            cryst_events = [
                e for e in cryst_events
                if tc_low <= float(e['peak_C']) <= tc_high
            ]
        if cryst_events:
            sorted_cryst = sorted(cryst_events, key=lambda e: abs(e['enthalpy_Jg']), reverse=True)
            significant = [e for e in sorted_cryst if abs(e['enthalpy_Jg']) > min_dh_cool]
            if significant:
                main_cryst = significant[0]
                result.Tc_onset_C = main_cryst['onset_C']
                result.Tc_peak_C  = main_cryst['peak_C']
                result.DHc_Jg     = main_cryst['enthalpy_Jg']
                if len(significant) >= 2:
                    result.Tc2_peak_C = significant[1]['peak_C']
                    result.DHc2_Jg    = significant[1]['enthalpy_Jg']
                for e in significant:
                    result.peak_components.append({
                        'type': 'crystallisation', 'peak_C': e['peak_C'],
                        'onset_C': e['onset_C'], 'end_C': e['end_C'],
                        'enthalpy_Jg': e['enthalpy_Jg'],
                    })

        # Cooling: melt events are noise/reorganisation — ignore entirely

    else:
        # ---- Isothermal: require minimum enthalpy (0.05 J/g) to avoid noise ----
        min_dh = min_event_dh
        if melt_events:
            sorted_melt = sorted(melt_events, key=lambda e: e['enthalpy_Jg'], reverse=True)
            significant = [e for e in sorted_melt if e['enthalpy_Jg'] > min_dh]
            if significant:
                main = significant[0]
                result.Tm_onset_C = main['onset_C']
                result.Tm_peak_C  = main['peak_C']
                result.DHm_Jg     = main['enthalpy_Jg']
                for e in significant:
                    result.peak_components.append({
                        'type': 'melting', 'peak_C': e['peak_C'],
                        'onset_C': e['onset_C'], 'end_C': e['end_C'],
                        'enthalpy_Jg': e['enthalpy_Jg'],
                    })
        if cryst_events:
            sorted_cryst = sorted(cryst_events, key=lambda e: abs(e['enthalpy_Jg']), reverse=True)
            significant = [e for e in sorted_cryst if abs(e['enthalpy_Jg']) > min_dh]
            if significant:
                main_cryst = significant[0]
                result.Tc_onset_C = main_cryst['onset_C']
                result.Tc_peak_C  = main_cryst['peak_C']
                result.DHc_Jg     = main_cryst['enthalpy_Jg']
                for e in significant:
                    result.peak_components.append({
                        'type': 'crystallisation', 'peak_C': e['peak_C'],
                        'onset_C': e['onset_C'], 'end_C': e['end_C'],
                        'enthalpy_Jg': e['enthalpy_Jg'],
                    })

    # ---- Crystallinity ----
    DHm0 = DHm0_override if DHm0_override is not None else config.get_crystallinity_ref()
    result.DHm0_Jg = DHm0
    result.DHm0_source = "polymer_reference" if np.isfinite(DHm0) and DHm0 > 0 else "missing"
    result.Xc_pct = compute_crystallinity(result.DHm_Jg, result.DHcc_Jg, DHm0)
    result.Xc_method = "enthalpy_method"
    melt_variants = _reintegrate_event_variants(T, HF, primary_melt_event, is_endotherm=True)
    cold_variants = _reintegrate_event_variants(T, HF, primary_cold_cryst_event, is_endotherm=False)
    melt_enthalpies = np.asarray(melt_variants.get("enthalpies", []), dtype=float)
    cold_enthalpies = np.asarray(cold_variants.get("enthalpies", []), dtype=float)
    melt_enthalpies = melt_enthalpies[np.isfinite(melt_enthalpies)]
    cold_enthalpies = cold_enthalpies[np.isfinite(cold_enthalpies)]

    if melt_enthalpies.size:
        result.DHm_Jg_mean = float(np.mean(melt_enthalpies))
        result.DHm_Jg_std = float(np.std(melt_enthalpies))
    if cold_enthalpies.size:
        result.DHcc_Jg_mean = float(np.mean(cold_enthalpies))
        result.DHcc_Jg_std = float(np.std(cold_enthalpies))
    elif melt_enthalpies.size:
        result.DHcc_Jg_mean = 0.0
        result.DHcc_Jg_std = 0.0

    result.baseline_variant_count = int(max(
        melt_variants.get("baseline_variant_count", 0) or 0,
        cold_variants.get("baseline_variant_count", 0) or 0,
    ))
    result.integration_variant_count = int(
        (melt_variants.get("integration_variant_count", 0) or 0)
        + (cold_variants.get("integration_variant_count", 0) or 0)
    )

    if melt_enthalpies.size and np.isfinite(DHm0) and DHm0 > 0:
        if cold_enthalpies.size:
            count = min(melt_enthalpies.size, cold_enthalpies.size)
            xc_values = (melt_enthalpies[:count] - cold_enthalpies[:count]) / DHm0 * 100.0
        else:
            xc_values = melt_enthalpies / DHm0 * 100.0
        xc_values = xc_values[np.isfinite(xc_values)]
        if xc_values.size:
            result.Xc_pct_mean = float(np.mean(xc_values))
            result.Xc_pct_std = float(np.std(xc_values))
            result.Xc_pct_ci95 = float(1.96 * result.Xc_pct_std)

    if np.isfinite(result.Xc_pct_mean) and abs(float(result.Xc_pct_mean)) > 1e-9:
        result.baseline_sensitivity_pct = float(
            np.clip(abs(result.Xc_pct_ci95) / max(abs(result.Xc_pct_mean), 1e-9) * 100.0, 0.0, 100.0)
        )
        result.integration_boundary_sensitivity_pct = float(
            np.clip(result.Xc_pct_std / max(abs(result.Xc_pct_mean), 1e-9) * 100.0, 0.0, 100.0)
        )
    elif result.quality_score >= 0.8:
        result.baseline_sensitivity_pct = 0.0
        result.integration_boundary_sensitivity_pct = 0.0
    else:
        result.baseline_sensitivity_pct = 12.0
        result.integration_boundary_sensitivity_pct = 8.0

    # ---- Multi-peak Gaussian deconvolution (optional, for SCI figures) ----
    # Only on heating scans: cooling crystallisation peaks should not be deconvolved
    if is_heating and len(melt_events) > 1:
        try:
            peak_function = getattr(config, 'peak_function', 'gaussian')
            deconv = deconvolve_peaks(T, HF, n_peaks=len(melt_events),
                                       peak_type=peak_function)
            T_min_ok = float(np.min(T)) - 20.0
            T_max_ok = float(np.max(T)) + 20.0
            # Merge deconv components into peak_components (add fit info)
            for dc in deconv.get('components', []):
                mu_val = dc.get('mu_C', dc.get('mu', np.nan))
                if mu_val is None or (isinstance(mu_val, float) and np.isnan(mu_val)):
                    continue
                if mu_val < T_min_ok or mu_val > T_max_ok:
                    continue
                frac = dc.get('fraction', 0)
                if frac < 0.01:
                    continue
                # Must be near a genuine melt peak (±30°C)
                melt_peak_positions = [e['peak_C'] for e in melt_events]
                if melt_peak_positions:
                    min_dist = min(abs(mu_val - p) for p in melt_peak_positions)
                    if min_dist > 30.0:
                        continue
                result.peak_components.append({
                    'type': 'deconv_melting',
                    'peak_C': mu_val,
                    'amplitude': dc.get('amp', np.nan),
                    'sigma': dc.get('sigma_C', dc.get('sigma', np.nan)),
                    'fraction': frac,
                })
        except Exception:
            logger.warning("静默异常", exc_info=True)

    # ---- Local peak fit score (AI tuning objective) ----
    fit_quality = compute_peak_fit_quality(T, HF, result, config, score_HF=fit_observed_HF)
    result.r_squared = fit_quality["r_squared"]
    result.fit_rmse = fit_quality["rmse"]
    result.HF_fit = fit_quality["fit"]
    result.fit_regions = fit_quality["regions"]

    return result
