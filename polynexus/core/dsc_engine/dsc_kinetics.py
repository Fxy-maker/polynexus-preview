"""DSC crystallisation kinetics module.

Supports:
    Isothermal:      Avrami equation
    Non-isothermal:  Ozawa, Mo (Mo Zhishen), Kissinger, Friedman

All methods follow the IUPAC convention: exothermic = positive.
"""

import logging
logger = logging.getLogger(__name__)

import os
import re

import numpy as np
from scipy import optimize, stats, signal
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

from .io import DSCScan


# ---------------------------------------------------------------------------
#  Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class AvramiResult:
    """Avrami analysis result for isothermal crystallisation."""
    n: float = np.nan          # Avrami exponent
    log_k: float = np.nan      # log10(k)  (k in min^{-n})
    k: float = np.nan          # rate constant
    t_half_min: float = np.nan # half-crystallisation time
    r_squared: float = np.nan  # fit quality
    temperature_C: float = np.nan
    induction_time_min: float = np.nan
    start_time_min: float = np.nan
    end_time_min: float = np.nan
    crystallisation_enthalpy_Jg: float = np.nan
    label: str = ""
    quality_flags: List[str] = field(default_factory=list)
    Xt_data: np.ndarray = field(default_factory=lambda: np.array([]))
    t_data: np.ndarray = field(default_factory=lambda: np.array([]))
    Xt_fit: np.ndarray = field(default_factory=lambda: np.array([]))


@dataclass
class IsothermalSegment:
    """Detected quasi-isothermal hold inside a DSC program."""
    label: str = ""
    temperature_C: float = np.nan
    start_index: int = 0
    end_index: int = 0
    start_time_min: float = np.nan
    end_time_min: float = np.nan
    duration_min: float = np.nan
    T_C: np.ndarray = field(default_factory=lambda: np.array([]))
    HF_Wg: np.ndarray = field(default_factory=lambda: np.array([]))
    t_min: np.ndarray = field(default_factory=lambda: np.array([]))


@dataclass
class IsothermalKineticsResult:
    """Collection of Avrami fits from one heat-cool-hold program."""
    segments: List[IsothermalSegment] = field(default_factory=list)
    avrami_results: List[AvramiResult] = field(default_factory=list)
    best: AvramiResult = field(default_factory=AvramiResult)
    quality_flags: List[str] = field(default_factory=list)


@dataclass
class NonIsothermalResult:
    """Non-isothermal crystallisation kinetics results."""
    method: str = ""
    # Ozawa
    ozawa_n: float = np.nan
    ozawa_K_T: float = np.nan
    # Mo (combined Avrami-Ozawa)
    mo_F_T: float = np.nan
    mo_a: float = np.nan
    # Kissinger activation energy
    kissinger_Ea_kJmol: float = np.nan
    # Friedman isoconversional
    friedman_Ea: Dict[float, float] = field(default_factory=dict)
    # Data
    rates: List[float] = field(default_factory=list)
    r_squared: float = np.nan
    quality_flags: List[str] = field(default_factory=list)


@dataclass
class NonIsothermalCurve:
    """One cooling-rate crystallisation curve extracted from a DSC program."""
    label: str = ""
    rate_K_per_min: float = np.nan
    T_C: np.ndarray = field(default_factory=lambda: np.array([]))
    HF_Wg: np.ndarray = field(default_factory=lambda: np.array([]))
    t_min: np.ndarray = field(default_factory=lambda: np.array([]))
    Xt: np.ndarray = field(default_factory=lambda: np.array([]))
    T_xt_C: np.ndarray = field(default_factory=lambda: np.array([]))
    t_xt_min: np.ndarray = field(default_factory=lambda: np.array([]))
    Tp_C: float = np.nan
    T_onset_C: float = np.nan
    T_end_C: float = np.nan
    crystallisation_enthalpy_Jg: float = np.nan
    quality_flags: List[str] = field(default_factory=list)


@dataclass
class NonIsothermalKineticsSeries:
    """Full non-isothermal crystallisation kinetics result for a rate series."""
    curves: List[NonIsothermalCurve] = field(default_factory=list)
    ozawa: NonIsothermalResult = field(default_factory=lambda: NonIsothermalResult(method="Ozawa"))
    mo: NonIsothermalResult = field(default_factory=lambda: NonIsothermalResult(method="Mo"))
    kissinger: NonIsothermalResult = field(default_factory=lambda: NonIsothermalResult(method="Kissinger"))
    friedman: NonIsothermalResult = field(default_factory=lambda: NonIsothermalResult(method="Friedman"))
    quality_flags: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
#  Isothermal: Avrami analysis
# ---------------------------------------------------------------------------

def _cumulative_trapezoid(y: np.ndarray, x: np.ndarray) -> np.ndarray:
    out = np.zeros(len(y), dtype=float)
    if len(y) < 2:
        return out
    dx = np.diff(x)
    area = 0.5 * (y[:-1] + y[1:]) * dx
    out[1:] = np.cumsum(area)
    return out


def _smooth_signal(y: np.ndarray, max_window: int = 41) -> np.ndarray:
    y = np.asarray(y, dtype=float)
    if len(y) < 7:
        return y
    window = min(max_window, max(5, len(y) // 25))
    if window % 2 == 0:
        window += 1
    if window >= len(y):
        window = len(y) - 1 if len(y) % 2 == 0 else len(y)
    if window < 5:
        return y
    try:
        return signal.savgol_filter(y, window, min(3, window - 2), mode='interp')
    except Exception:
        return y
        logger.warning("异常已处理", exc_info=True)


def detect_isothermal_segments(scan: DSCScan,
                               min_duration_min: float = 1.0,
                               temp_tolerance_C: float = 0.35,
                               max_drift_C_per_min: float = 0.12,
                               min_points: int = 30,
                               ) -> List[IsothermalSegment]:
    """Detect quasi-isothermal holds embedded in a DSC program.

    Instrument exports often contain repeated melt-cool-hold-heat cycles.  This
    finds the temperature-stable hold portions that can support Avrami analysis.
    """
    T = np.asarray(scan.T_C, dtype=float)
    HF = np.asarray(scan.HF_Wg, dtype=float)
    if len(scan.t_min) == len(T):
        t = np.asarray(scan.t_min, dtype=float)
    else:
        t = np.arange(len(T), dtype=float) / 60.0

    valid = np.isfinite(T) & np.isfinite(HF) & np.isfinite(t)
    T, HF, t = T[valid], HF[valid], t[valid]
    if len(T) < min_points:
        return []

    order = np.argsort(t)
    T, HF, t = T[order], HF[order], t[order]
    dt = np.diff(t)
    dT = np.diff(T)
    good_dt = np.abs(dt) > 1e-9
    if not np.any(good_dt):
        return []

    drift = np.full(len(dT), np.inf)
    drift[good_dt] = np.abs(dT[good_dt] / dt[good_dt])
    stable = drift <= max_drift_C_per_min

    segments: List[IsothermalSegment] = []
    start = None
    for i, is_stable in enumerate(stable):
        if is_stable and start is None:
            start = i
        at_end = i == len(stable) - 1
        if start is not None and ((not is_stable) or at_end):
            end = i if not is_stable else i + 1
            n_pts = end - start + 1
            if n_pts >= min_points:
                T_seg = T[start:end + 1]
                span = float(np.nanmax(T_seg) - np.nanmin(T_seg))
                duration = float(t[end] - t[start])
                if duration >= min_duration_min and span <= temp_tolerance_C:
                    temp = float(np.nanmedian(T_seg))
                    label = f"{scan.label}/iso {temp:.1f}C"
                    segments.append(IsothermalSegment(
                        label=label,
                        temperature_C=temp,
                        start_index=int(start),
                        end_index=int(end),
                        start_time_min=float(t[start]),
                        end_time_min=float(t[end]),
                        duration_min=duration,
                        T_C=T_seg.copy(),
                        HF_Wg=HF[start:end + 1].copy(),
                        t_min=t[start:end + 1].copy(),
                    ))
            start = None

    return segments


def relative_crystallinity_isothermal(time_min: np.ndarray,
                                      HF_Wg: np.ndarray,
                                      tail_fraction: float = 0.15,
                                      threshold_ratio: float = 0.01,
                                      ) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """Compute baseline-corrected isothermal relative crystallinity.

    Returns X(t), relative time, and metadata.  Heat flow is auto-oriented so
    the crystallisation exotherm is positive before integration.
    """
    t = np.asarray(time_min, dtype=float)
    HF = np.asarray(HF_Wg, dtype=float)
    valid = np.isfinite(t) & np.isfinite(HF)
    t, HF = t[valid], HF[valid]
    if len(t) < 5:
        return np.array([]), np.array([]), {'quality_flags': ['too_few_points']}

    order = np.argsort(t)
    t, HF = t[order], HF[order]
    keep = np.ones(len(t), dtype=bool)
    keep[1:] = np.diff(t) > 1e-9
    t, HF = t[keep], HF[keep]
    if len(t) < 5:
        return np.array([]), np.array([]), {'quality_flags': ['too_few_points']}

    tail_n = max(5, int(len(HF) * tail_fraction))
    tail = HF[-tail_n:]
    baseline = float(np.nanmedian(tail))
    centered = HF - baseline

    pos_area = np.trapezoid(np.clip(centered, 0.0, None), t)
    neg_area = np.trapezoid(np.clip(-centered, 0.0, None), t)
    polarity = -1.0 if neg_area > pos_area else 1.0
    exo = polarity * centered
    exo_smooth = _smooth_signal(exo)

    noise = float(1.4826 * np.nanmedian(np.abs(exo_smooth[-tail_n:] - np.nanmedian(exo_smooth[-tail_n:]))))
    peak = float(np.nanmax(exo_smooth)) if len(exo_smooth) else 0.0
    if not np.isfinite(peak) or peak <= 0:
        return np.array([]), np.array([]), {'quality_flags': ['no_positive_exotherm']}

    threshold = max(noise * 3.0, peak * threshold_ratio)
    peak_idx = int(np.nanargmax(exo_smooth))
    above = exo_smooth > threshold

    left_candidates = np.where(~above[:peak_idx + 1])[0]
    onset = int(left_candidates[-1] + 1) if len(left_candidates) else 0
    start = 0
    right_candidates = np.where(~above[peak_idx:])[0]
    end = int(peak_idx + right_candidates[0]) if len(right_candidates) else len(t) - 1
    end = max(end, start + 3)
    end = min(end, len(t) - 1)

    signal_pos = np.clip(exo[start:end + 1], 0.0, None)
    t_roi_abs = t[start:end + 1]
    t_roi = t_roi_abs - t_roi_abs[0]
    integral = _cumulative_trapezoid(signal_pos, t_roi)
    total = float(integral[-1])
    if total <= 1e-12:
        return np.array([]), np.array([]), {'quality_flags': ['zero_exotherm_area']}

    Xt = np.clip(integral / total, 0.0, 1.0)
    meta = {
        'baseline_Wg': baseline,
        'polarity': polarity,
        'start_time_min': float(t_roi_abs[0]),
        'end_time_min': float(t_roi_abs[-1]),
        'induction_time_min': float(t[onset] - t[0]) if onset < len(t) else np.nan,
        'crystallisation_enthalpy_Jg': total * 60.0,
        'peak_time_min': float(t[peak_idx] - t_roi_abs[0]),
        'quality_flags': [],
    }
    if onset == 0:
        meta['quality_flags'].append('event_starts_at_segment_boundary')
    if end == len(t) - 1:
        meta['quality_flags'].append('event_ends_at_segment_boundary')
    return Xt, t_roi, meta


def relative_crystallinity(time_min: np.ndarray, HF_Wg: np.ndarray,
                           t_start: float | None = None,
                           t_end: float | None = None,
                           ) -> Tuple[np.ndarray, np.ndarray]:
    """Compute relative crystallinity X(t) from isothermal DSC exotherm.

    X(t) = integral(HF, 0..t) / integral(HF, 0..inf)

    With exo-up convention, crystallisation peaks are positive.

    Parameters
    ----------
    time_min : ndarray
    HF_Wg : ndarray
    t_start, t_end : float, optional
        Integration limits. If None, use entire range.

    Returns
    -------
    Xt : ndarray  (0 → 1)
    t  : ndarray
    """
    t = np.asarray(time_min, dtype=float)
    HF = np.asarray(HF_Wg, dtype=float)

    if len(t) == 0:
        return np.array([]), np.array([])
    if t_start is None:
        t_start = float(np.nanmin(t))
    if t_end is None:
        t_end = float(np.nanmax(t))

    mask = (t >= t_start) & (t <= t_end)
    Xt, t_roi, _ = relative_crystallinity_isothermal(t[mask], HF[mask])
    return Xt, t_roi


def avrami_fit(time_min: np.ndarray, Xt: np.ndarray,
               X_range: Tuple[float, float] = (0.01, 0.99),
               ) -> AvramiResult:
    """Fit Avrami equation:  X(t) = 1 - exp(-k * t^n)

    Linearised:  log(-ln(1 - X)) = log(k) + n * log(t)

    Parameters
    ----------
    time_min, Xt : ndarray
    X_range : (X_min, X_max)
        Fit range for relative crystallinity.

    Returns
    -------
    AvramiResult
    """
    result = AvramiResult()
    result.t_data = time_min
    result.Xt_data = Xt

    if len(Xt) < 5:
        return result

    # Select data in the linear range.  t=0 is physically useful for X(t)
    # but not for the log-log linearisation.
    mask = (Xt >= X_range[0]) & (Xt <= X_range[1]) & (time_min > 0)
    if np.sum(mask) < 4:
        mask = (time_min > 0) & (Xt > 0) & (Xt < 1)

    t_fit = time_min[mask]
    X_fit = Xt[mask]
    if len(t_fit) < 4:
        result.quality_flags.append('too_few_fit_points')
        return result

    # Avoid log(0) and log(1)
    X_clipped = np.clip(X_fit, 1e-6, 1 - 1e-6)
    y = np.log(-np.log(1 - X_clipped))
    x = np.log(np.maximum(t_fit, 1e-9))

    # Linear regression
    slope, intercept, r, _, _ = stats.linregress(x, y)
    n = slope
    log_k = intercept / np.log(10)  # convert ln to log10
    k = 10 ** log_k

    if k > 0 and n > 0:
        t_half = (np.log(2) / k) ** (1.0 / n)
    else:
        t_half = np.nan
    try:
        t_half_data = float(np.interp(0.5, Xt, time_min))
        if np.isfinite(t_half_data):
            t_half = t_half_data
    except Exception:
        logger.warning("静默异常", exc_info=True)

    result.n = n
    result.log_k = log_k
    result.k = k
    result.t_half_min = t_half
    result.r_squared = r ** 2

    # Compute fitted curve
    result.Xt_fit = 1 - np.exp(-k * time_min ** n)
    if result.r_squared < 0.95:
        result.quality_flags.append('low_avrami_r_squared')

    return result


def avrami_from_dsc(time_min: np.ndarray, HF_Wg: np.ndarray,
                    ) -> AvramiResult:
    """Full Avrami analysis from isothermal DSC data."""
    Xt, t, meta = relative_crystallinity_isothermal(time_min, HF_Wg)
    if len(Xt) == 0:
        result = AvramiResult()
        result.quality_flags.extend(meta.get('quality_flags', []))
        return result
    result = avrami_fit(t, Xt)
    result.induction_time_min = meta.get('induction_time_min', np.nan)
    result.start_time_min = meta.get('start_time_min', np.nan)
    result.end_time_min = meta.get('end_time_min', np.nan)
    result.crystallisation_enthalpy_Jg = meta.get('crystallisation_enthalpy_Jg', np.nan)
    result.quality_flags.extend(meta.get('quality_flags', []))
    return result


def analyze_isothermal_scan(scan: DSCScan,
                            min_duration_min: float = 1.0,
                            temp_tolerance_C: float = 0.35,
                            max_drift_C_per_min: float = 0.12,
                            min_enthalpy_Jg: float = 0.01,
                            ) -> IsothermalKineticsResult:
    """Extract isothermal holds from one scan and fit Avrami kinetics."""
    result = IsothermalKineticsResult()
    segments = detect_isothermal_segments(
        scan,
        min_duration_min=min_duration_min,
        temp_tolerance_C=temp_tolerance_C,
        max_drift_C_per_min=max_drift_C_per_min,
    )
    result.segments = segments
    if not segments:
        result.quality_flags.append('no_isothermal_segments')
        return result

    for seg in segments:
        av = avrami_from_dsc(seg.t_min, seg.HF_Wg)
        av.label = seg.label
        av.temperature_C = seg.temperature_C
        if np.isnan(av.start_time_min):
            av.start_time_min = seg.start_time_min
        if np.isnan(av.end_time_min):
            av.end_time_min = seg.end_time_min
        if (not np.isnan(av.crystallisation_enthalpy_Jg)
                and av.crystallisation_enthalpy_Jg < min_enthalpy_Jg):
            av.quality_flags.append('low_crystallisation_enthalpy')
        result.avrami_results.append(av)

    valid = [
        av for av in result.avrami_results
        if np.isfinite(av.n) and np.isfinite(av.r_squared)
        and 'low_crystallisation_enthalpy' not in av.quality_flags
    ]
    if valid:
        result.best = sorted(
            valid,
            key=lambda av: (
                len(av.quality_flags) == 0,
                av.r_squared,
                av.crystallisation_enthalpy_Jg if np.isfinite(av.crystallisation_enthalpy_Jg) else 0.0,
            ),
            reverse=True,
        )[0]
    else:
        result.quality_flags.append('no_valid_avrami_fit')
    return result


def analyze_isothermal_scans(scans: List[DSCScan], **kwargs) -> IsothermalKineticsResult:
    """Run isothermal kinetics over all scans in a DSC program/folder."""
    combined = IsothermalKineticsResult()
    candidate_scans = [
        scan for scan in scans
        if scan.rate_K_per_min < -0.01 or '/cool ' in scan.label.lower()
    ]
    if not candidate_scans:
        candidate_scans = scans

    for scan in candidate_scans:
        one = analyze_isothermal_scan(scan, **kwargs)
        combined.segments.extend(one.segments)
        combined.avrami_results.extend(one.avrami_results)
        combined.quality_flags.extend(one.quality_flags)

    valid = [
        av for av in combined.avrami_results
        if np.isfinite(av.n) and np.isfinite(av.r_squared)
        and 'low_crystallisation_enthalpy' not in av.quality_flags
    ]
    if valid:
        combined.best = sorted(
            valid,
            key=lambda av: (
                len(av.quality_flags) == 0,
                av.r_squared,
                av.crystallisation_enthalpy_Jg if np.isfinite(av.crystallisation_enthalpy_Jg) else 0.0,
            ),
            reverse=True,
        )[0]
    elif not combined.quality_flags:
        combined.quality_flags.append('no_valid_avrami_fit')
    return combined


# ---------------------------------------------------------------------------
#  Non-isothermal: Ozawa method
# ---------------------------------------------------------------------------

def ozawa_analysis(T_C_list: List[np.ndarray],
                   HF_Wg_list: List[np.ndarray],
                   rates_K_per_min: List[float],
                   X_levels: List[float] = None,
                   ) -> NonIsothermalResult:
    """Ozawa method for non-isothermal crystallisation.

    log(beta) = log(K_T) - n * log(t)  at constant X

    Parameters
    ----------
    T_C_list : list of ndarray
        Temperature arrays for each cooling rate.
    HF_Wg_list : list of ndarray
        Heat flow arrays for each cooling rate.
    rates_K_per_min : list of float
        Cooling rates (positive = cooling).
    X_levels : list of float, optional
        Relative crystallinity levels to evaluate. Default: [0.2, 0.4, 0.6, 0.8].

    Returns
    -------
    NonIsothermalResult
    """
    result = NonIsothermalResult(method="Ozawa")
    result.rates = rates_K_per_min

    if X_levels is None:
        X_levels = [0.2, 0.4, 0.5, 0.6, 0.8]

    n_vals = []
    for X_target in X_levels:
        beta_vals = []
        t_vals = []

        for T, HF, beta in zip(T_C_list, HF_Wg_list, rates_K_per_min):
            Xt, _ = relative_crystallinity_from_T(T, HF, beta)
            if len(Xt) < 3:
                continue

            # Find time at target X
            idx = np.argmin(np.abs(Xt - X_target))
            t_vals.append(idx * np.mean(np.diff(T)) / abs(beta) * 60.0)  # convert to min
            beta_vals.append(beta)

        if len(beta_vals) >= 3:
            log_beta = np.log10(beta_vals)
            log_t = np.log10(np.maximum(t_vals, 1e-9))
            slope, _, _, _, _ = stats.linregress(log_t, log_beta)
            n_vals.append(-slope)

    if n_vals:
        result.ozawa_n = float(np.mean(n_vals))

    return result


def relative_crystallinity_from_T(T_C: np.ndarray, HF_Wg: np.ndarray,
                                   rate_K_per_min: float,
                                   ) -> Tuple[np.ndarray, np.ndarray]:
    """Compute X(T) from non-isothermal data.

    Converts temperature to time: t = (T - T0) / beta.
    """
    T = np.asarray(T_C, dtype=float)
    HF = np.asarray(HF_Wg, dtype=float)

    if abs(rate_K_per_min) < 0.01:
        return np.array([]), np.array([])

    # Find crystallisation exotherm
    # With exo-up, crystallisation = positive peaks on cooling
    dHF = np.gradient(HF, np.gradient(T))

    # Detect peak region
    peak_idx = np.argmax(HF)
    left = peak_idx
    right = peak_idx

    threshold = 0.1 * np.max(HF)
    while left > 0 and HF[left] > threshold:
        left -= 1
    while right < len(T) - 1 and HF[right] > threshold:
        right += 1

    left = max(0, left - 5)
    right = min(len(T) - 1, right + 5)

    T_roi = T[left:right + 1]
    HF_roi = HF[left:right + 1]

    # Convert to time
    t_min = (T_roi - T_roi[0]) / abs(rate_K_per_min)

    return relative_crystallinity(t_min, HF_roi)


# ---------------------------------------------------------------------------
#  Kissinger method (activation energy)
# ---------------------------------------------------------------------------

def kissinger_analysis(Tp_C_list: List[float],
                       rates_K_per_min: List[float],
                       ) -> NonIsothermalResult:
    """Kissinger method for crystallisation activation energy.

    ln(beta / Tp^2) = -Ea / (R * Tp) + const

    Parameters
    ----------
    Tp_C_list : list of float
        Peak crystallisation temperatures (in Celsius) for each rate.
    rates_K_per_min : list of float

    Returns
    -------
    NonIsothermalResult
    """
    result = NonIsothermalResult(method="Kissinger")

    if len(Tp_C_list) < 3:
        return result

    Tp_K = np.array(Tp_C_list) + 273.15
    beta = np.array(rates_K_per_min)

    x = 1000.0 / Tp_K  # 1000/T for numerical stability
    y = np.log(beta / Tp_K ** 2)

    slope, _, r, _, _ = stats.linregress(x, y)
    R = 8.314  # J/(mol·K)
    Ea = -slope * R * 1000.0  # kJ/mol

    result.kissinger_Ea_kJmol = float(Ea)
    result.r_squared = r ** 2

    return result


# ---------------------------------------------------------------------------
#  Friedman isoconversional method
# ---------------------------------------------------------------------------

def friedman_analysis(T_C_list: List[np.ndarray],
                      HF_Wg_list: List[np.ndarray],
                      rates_K_per_min: List[float],
                      X_levels: List[float] = None,
                      ) -> NonIsothermalResult:
    """Friedman isoconversional method.

    ln(dX/dt) = -Ea(X) / (R * T) + ln(A * f(X))

    At each conversion level X, plot ln(dX/dt) vs 1/T across rates;
    slope gives Ea(X).

    Returns
    -------
    NonIsothermalResult with friedman_Ea dict.
    """
    result = NonIsothermalResult(method="Friedman")
    result.rates = rates_K_per_min

    if X_levels is None:
        X_levels = np.linspace(0.1, 0.9, 9).tolist()

    R = 8.314  # J/(mol·K)

    for X_target in X_levels:
        inv_T_vals = []
        ln_dXdt_vals = []

        for T, HF, beta in zip(T_C_list, HF_Wg_list, rates_K_per_min):
            if abs(beta) < 0.01:
                continue

            Xt, t_min = relative_crystallinity_from_T(T, HF, beta)
            if len(Xt) < 3:
                continue

            idx = np.argmin(np.abs(Xt - X_target))
            if idx < 1 or idx >= len(T) - 1:
                continue

            T_K = T[idx] + 273.15
            inv_T_vals.append(1000.0 / T_K)

            dXdt = (Xt[min(idx + 1, len(Xt) - 1)] - Xt[max(0, idx - 1)]) / (
                t_min[min(idx + 1, len(Xt) - 1)] - t_min[max(0, idx - 1)])
            ln_dXdt_vals.append(np.log(max(abs(dXdt), 1e-12)))

        if len(inv_T_vals) >= 3:
            slope, _, _, _, _ = stats.linregress(inv_T_vals, ln_dXdt_vals)
            result.friedman_Ea[X_target] = float(-slope * R * 1000.0)

    return result


# ---------------------------------------------------------------------------
#  Mo method (combined Avrami-Ozawa)
# ---------------------------------------------------------------------------

def mo_analysis(T_C_list: List[np.ndarray],
                HF_Wg_list: List[np.ndarray],
                rates_K_per_min: List[float],
                X_levels: List[float] = None,
                ) -> NonIsothermalResult:
    """Mo Zhishen method: log(beta) = log(F(T)) - a * log(t).

    F(T) is the cooling rate required to reach a given X in unit time;
    a = n / m  (ratio of Avrami to Ozawa exponents).

    Returns
    -------
    NonIsothermalResult
    """
    result = NonIsothermalResult(method="Mo")

    if X_levels is None:
        X_levels = [0.2, 0.4, 0.5, 0.6, 0.8]

    beta_arr = np.array(rates_K_per_min)
    log_beta = np.log10(beta_arr)

    t_matrix = []
    for T, HF, beta in zip(T_C_list, HF_Wg_list, rates_K_per_min):
        Xt, t_min = relative_crystallinity_from_T(T, HF, beta)
        if len(Xt) < 3:
            continue
        t_row = []
        for X_target in X_levels:
            idx = np.argmin(np.abs(Xt - X_target))
            t_row.append(t_min[idx])
        t_matrix.append(t_row)

    if len(t_matrix) < 3:
        return result

    t_matrix = np.array(t_matrix)
    a_vals = []

    for j, X_target in enumerate(X_levels):
        log_t = np.log10(np.maximum(t_matrix[:, j], 1e-9))
        if np.std(log_t) < 1e-6:
            continue
        slope, intercept, _, _, _ = stats.linregress(log_t, log_beta)
        a_vals.append(-slope)
        result.mo_F_T = float(10 ** intercept)

    if a_vals:
        result.mo_a = float(np.mean(a_vals))

    return result


# ---------------------------------------------------------------------------
#  Non-isothermal crystallisation curve extraction (robust implementation)
# ---------------------------------------------------------------------------

def extract_nonisothermal_rate(label: str,
                               default: Optional[float] = None,
                               ) -> float:
    """Extract the cooling rate encoded at the end of a filename.

    Examples
    --------
    ``FDW-SLM-80%-30-2.5.xls`` -> ``2.5``.
    """
    text = str(label or "")
    first_part = re.split(r"[\\/]", text, maxsplit=1)[0]
    name = os.path.basename(first_part)
    match = re.search(
        r"-(\d+(?:\.\d+)?)\s*(?:\.(?:xls|xlsx|csv|txt|dat|001|asc)|$)",
        name,
        flags=re.IGNORECASE,
    )
    if match:
        return float(match.group(1))

    if default is not None and np.isfinite(default):
        return float(default)

    values = re.findall(r"(\d+(?:\.\d+)?)", name)
    if values:
        return float(values[-1])
    return np.nan


def _time_from_temperature(T: np.ndarray, beta: float) -> np.ndarray:
    if len(T) == 0 or abs(beta) < 1e-9:
        return np.array([])
    dt = np.zeros(len(T), dtype=float)
    if len(T) > 1:
        dt[1:] = np.cumsum(np.abs(np.diff(T)) / abs(beta))
    return dt


def _clean_curve_arrays(T_C: np.ndarray,
                        HF_Wg: np.ndarray,
                        time_min: Optional[np.ndarray],
                        beta: float,
                        ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    T = np.asarray(T_C, dtype=float)
    HF = np.asarray(HF_Wg, dtype=float)
    if time_min is not None and len(time_min) == len(T):
        t = np.asarray(time_min, dtype=float)
    else:
        t = _time_from_temperature(T, beta)

    valid = np.isfinite(T) & np.isfinite(HF) & np.isfinite(t)
    T, HF, t = T[valid], HF[valid], t[valid]
    if len(T) < 5:
        return T, HF, t

    order = np.argsort(t)
    T, HF, t = T[order], HF[order], t[order]
    keep = np.ones(len(t), dtype=bool)
    keep[1:] = np.diff(t) > 1e-10
    return T[keep], HF[keep], t[keep]


def relative_crystallinity_nonisothermal(T_C: np.ndarray,
                                         HF_Wg: np.ndarray,
                                         rate_K_per_min: float,
                                         time_min: Optional[np.ndarray] = None,
                                         edge_fraction: float = 0.08,
                                         threshold_ratio: float = 0.01,
                                         ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict[str, Any]]:
    """Compute non-isothermal relative crystallinity from a cooling scan.

    The returned arrays are aligned to the crystallisation event window:
    ``X(T)``, ``T_event``, and relative ``t_event``.
    """
    beta = abs(float(rate_K_per_min)) if np.isfinite(rate_K_per_min) else np.nan
    if not np.isfinite(beta) or beta < 0.01:
        return np.array([]), np.array([]), np.array([]), {
            'quality_flags': ['invalid_cooling_rate']
        }

    T, HF, t = _clean_curve_arrays(T_C, HF_Wg, time_min, beta)
    if len(T) < 20:
        return np.array([]), np.array([]), np.array([]), {
            'quality_flags': ['too_few_points']
        }

    edge_n = max(8, int(len(T) * edge_fraction))
    edge_n = min(edge_n, max(8, len(T) // 4))
    edge_signal = np.concatenate([HF[:edge_n], HF[-edge_n:]])
    coarse_baseline = float(np.nanmedian(edge_signal))

    centered = HF - coarse_baseline
    pos_area = np.trapezoid(np.clip(centered, 0.0, None), t)
    neg_area = np.trapezoid(np.clip(-centered, 0.0, None), t)
    polarity = -1.0 if neg_area > pos_area else 1.0
    oriented = polarity * HF
    oriented_smooth = _smooth_signal(oriented)

    if len(oriented_smooth) == 0 or not np.isfinite(np.nanmax(oriented_smooth)):
        return np.array([]), np.array([]), np.array([]), {
            'quality_flags': ['no_positive_exotherm']
        }

    peak_idx = int(np.nanargmax(oriented_smooth))
    peak = float(oriented_smooth[peak_idx])
    edge_resid = np.concatenate([oriented_smooth[:edge_n], oriented_smooth[-edge_n:]])
    noise = float(1.4826 * np.nanmedian(np.abs(edge_resid - np.nanmedian(edge_resid))))
    prominence = float(signal.peak_prominences(oriented_smooth, [peak_idx])[0][0])
    if (not np.isfinite(peak)
            or not np.isfinite(prominence)
            or prominence <= max(noise * 3.0, abs(peak) * threshold_ratio)):
        return np.array([]), np.array([]), np.array([]), {
            'quality_flags': ['no_positive_exotherm']
        }

    max_width_C = min(80.0, max(10.0, 0.65 * float(np.nanmax(T) - np.nanmin(T))))
    start = 0
    end = len(T) - 1
    for rel_height in (0.8, 0.65, 0.5):
        widths, _, left_ips, right_ips = signal.peak_widths(
            oriented_smooth, [peak_idx], rel_height=rel_height
        )
        left = int(max(0, np.floor(left_ips[0])))
        right = int(min(len(T) - 1, np.ceil(right_ips[0])))
        width_C = abs(float(T[left] - T[right])) if right > left else np.inf
        if right > left and width_C <= max_width_C:
            start, end = left, right
            break

    pad = max(3, int((end - start + 1) * 0.20))
    start = max(0, start - pad)
    end = min(len(T) - 1, end + pad)
    if end - start < 5:
        return np.array([]), np.array([]), np.array([]), {
            'quality_flags': ['event_window_too_short']
        }

    base_window = max(5, min(200, int((end - start + 1) * 0.12)))
    left_slice = slice(max(0, start - base_window), start)
    right_slice = slice(end + 1, min(len(T), end + 1 + base_window))
    x_base = np.concatenate([t[left_slice], t[right_slice]])
    y_base = np.concatenate([HF[left_slice], HF[right_slice]])
    if len(x_base) < 4:
        x_base = np.array([t[start], t[end]])
        y_base = np.array([HF[start], HF[end]])

    if len(x_base) >= 2 and np.nanstd(x_base) > 1e-12:
        coef = np.polyfit(x_base, y_base, 1)
        baseline = np.polyval(coef, t)
    else:
        baseline = np.full(len(HF), float(np.nanmedian(y_base)))

    exo = polarity * (HF - baseline)
    signal_pos = np.clip(exo[start:end + 1], 0.0, None)
    t_abs = t[start:end + 1]
    t_roi = t_abs - t_abs[0]
    T_roi = T[start:end + 1]
    integral = _cumulative_trapezoid(signal_pos, t_roi)
    total = float(integral[-1])
    if total <= 1e-12:
        return np.array([]), np.array([]), np.array([]), {
            'quality_flags': ['zero_exotherm_area']
        }

    Xt = np.clip(integral / total, 0.0, 1.0)
    flags: List[str] = []
    if start == 0:
        flags.append('event_starts_at_segment_boundary')
    if end == len(T) - 1:
        flags.append('event_ends_at_segment_boundary')

    meta = {
        'baseline_Wg': baseline,
        'polarity': polarity,
        'start_index': start,
        'end_index': end,
        'peak_index': peak_idx,
        'Tp_C': float(T[peak_idx]),
        'T_onset_C': float(T[start]),
        'T_end_C': float(T[end]),
        'start_time_min': float(t_abs[0]),
        'end_time_min': float(t_abs[-1]),
        'crystallisation_enthalpy_Jg': total * 60.0,
        'quality_flags': flags,
    }
    return Xt, T_roi, t_roi, meta


def relative_crystallinity_from_T(T_C: np.ndarray, HF_Wg: np.ndarray,
                                  rate_K_per_min: float,
                                  ) -> Tuple[np.ndarray, np.ndarray]:
    """Backward-compatible wrapper returning X and relative time."""
    Xt, _, t_roi, _ = relative_crystallinity_nonisothermal(
        T_C, HF_Wg, rate_K_per_min
    )
    return Xt, t_roi


def _curve_from_arrays(T_C: np.ndarray,
                       HF_Wg: np.ndarray,
                       rate_K_per_min: float,
                       time_min: Optional[np.ndarray] = None,
                       label: str = "",
                       min_enthalpy_Jg: float = 0.01,
                       ) -> NonIsothermalCurve:
    beta = abs(float(rate_K_per_min)) if np.isfinite(rate_K_per_min) else np.nan
    T, HF, t = _clean_curve_arrays(T_C, HF_Wg, time_min, beta)
    curve = NonIsothermalCurve(
        label=label,
        rate_K_per_min=beta,
        T_C=T,
        HF_Wg=HF,
        t_min=t,
    )
    Xt, T_xt, t_xt, meta = relative_crystallinity_nonisothermal(
        T, HF, beta, time_min=t
    )
    curve.Xt = Xt
    curve.T_xt_C = T_xt
    curve.t_xt_min = t_xt
    curve.Tp_C = meta.get('Tp_C', np.nan)
    curve.T_onset_C = meta.get('T_onset_C', np.nan)
    curve.T_end_C = meta.get('T_end_C', np.nan)
    curve.crystallisation_enthalpy_Jg = meta.get('crystallisation_enthalpy_Jg', np.nan)
    curve.quality_flags.extend(meta.get('quality_flags', []))
    if len(Xt) == 0:
        curve.quality_flags.append('no_crystallisation_curve')
    if (np.isfinite(curve.crystallisation_enthalpy_Jg)
            and curve.crystallisation_enthalpy_Jg < min_enthalpy_Jg):
        curve.quality_flags.append('low_crystallisation_enthalpy')
    return curve


def build_nonisothermal_curves(T_C_list: List[np.ndarray],
                               HF_Wg_list: List[np.ndarray],
                               rates_K_per_min: List[float],
                               time_min_list: Optional[List[np.ndarray]] = None,
                               labels: Optional[List[str]] = None,
                               min_enthalpy_Jg: float = 0.01,
                               ) -> List[NonIsothermalCurve]:
    """Build analysed non-isothermal curves from raw arrays."""
    curves: List[NonIsothermalCurve] = []
    time_min_list = time_min_list or [None] * len(T_C_list)
    labels = labels or [""] * len(T_C_list)
    for T, HF, beta, t, label in zip(T_C_list, HF_Wg_list, rates_K_per_min,
                                     time_min_list, labels):
        curve = _curve_from_arrays(
            T, HF, beta, time_min=t, label=label,
            min_enthalpy_Jg=min_enthalpy_Jg,
        )
        if len(curve.Xt) > 0 and np.isfinite(curve.rate_K_per_min):
            curves.append(curve)
    return sorted(curves, key=lambda c: c.rate_K_per_min)


def _is_cooling_scan(scan: DSCScan) -> bool:
    kind = str(scan.metadata.get('segment_kind', '')).lower()
    label = str(scan.label).lower()
    return (
        kind == 'cool'
        or getattr(scan, 'rate_K_per_min', 0.0) < -0.01
        or '/cool' in label
        or '\\cool' in label
    )


def _rate_for_scan(scan: DSCScan) -> float:
    measured = abs(float(getattr(scan, 'rate_K_per_min', np.nan)))
    from_name = extract_nonisothermal_rate(getattr(scan, 'label', ''), default=np.nan)
    if np.isfinite(from_name) and from_name > 0:
        return from_name
    return measured


def extract_nonisothermal_curves(scans: List[DSCScan],
                                 min_delta_T_C: float = 20.0,
                                 min_points: int = 80,
                                 min_enthalpy_Jg: float = 0.01,
                                 ) -> List[NonIsothermalCurve]:
    """Extract major cooling crystallisation curves from loaded DSC scans."""
    curves: List[NonIsothermalCurve] = []
    for scan in scans:
        T = np.asarray(scan.T_C, dtype=float)
        if len(T) < min_points or not _is_cooling_scan(scan):
            continue
        span = float(np.nanmax(T) - np.nanmin(T)) if len(T) else 0.0
        if span < min_delta_T_C:
            continue
        beta = _rate_for_scan(scan)
        if not np.isfinite(beta) or beta < 0.01:
            continue
        t = np.asarray(scan.t_min, dtype=float) if len(scan.t_min) == len(T) else None
        curve = _curve_from_arrays(
            scan.T_C, scan.HF_Wg, beta, time_min=t, label=scan.label,
            min_enthalpy_Jg=min_enthalpy_Jg,
        )
        if len(curve.Xt) > 0:
            curves.append(curve)

    by_rate: Dict[float, NonIsothermalCurve] = {}
    for curve in curves:
        key = round(curve.rate_K_per_min, 4)
        old = by_rate.get(key)
        if old is None or (
            np.nan_to_num(curve.crystallisation_enthalpy_Jg)
            > np.nan_to_num(old.crystallisation_enthalpy_Jg)
        ):
            by_rate[key] = curve
    return sorted(by_rate.values(), key=lambda c: c.rate_K_per_min)


def _interp_at_conversion(curve: NonIsothermalCurve,
                          X_target: float,
                          values: np.ndarray,
                          ) -> float:
    X = np.asarray(curve.Xt, dtype=float)
    y = np.asarray(values, dtype=float)
    valid = np.isfinite(X) & np.isfinite(y)
    X, y = X[valid], y[valid]
    if len(X) < 3:
        return np.nan
    order = np.argsort(X)
    X, y = X[order], y[order]
    unique_X, idx = np.unique(X, return_index=True)
    if len(unique_X) < 3 or X_target < unique_X[0] or X_target > unique_X[-1]:
        return np.nan
    return float(np.interp(X_target, unique_X, y[idx]))


def _interp_X_at_temperature(curve: NonIsothermalCurve, T_target: float) -> float:
    T = np.asarray(curve.T_xt_C, dtype=float)
    X = np.asarray(curve.Xt, dtype=float)
    valid = np.isfinite(T) & np.isfinite(X)
    T, X = T[valid], X[valid]
    if len(T) < 3:
        return np.nan
    order = np.argsort(T)
    T, X = T[order], X[order]
    unique_T, idx = np.unique(T, return_index=True)
    if len(unique_T) < 3 or T_target < unique_T[0] or T_target > unique_T[-1]:
        return np.nan
    return float(np.interp(T_target, unique_T, X[idx]))


def _as_curves(T_C_list: List[np.ndarray],
               HF_Wg_list: List[np.ndarray],
               rates_K_per_min: List[float],
               curves: Optional[List[NonIsothermalCurve]] = None,
               ) -> List[NonIsothermalCurve]:
    if curves is not None:
        return curves
    return build_nonisothermal_curves(T_C_list, HF_Wg_list, rates_K_per_min)


def ozawa_analysis(T_C_list: List[np.ndarray],
                   HF_Wg_list: List[np.ndarray],
                   rates_K_per_min: List[float],
                   X_levels: List[float] = None,
                   curves: Optional[List[NonIsothermalCurve]] = None,
                   ) -> NonIsothermalResult:
    """Ozawa analysis at fixed temperature."""
    result = NonIsothermalResult(method="Ozawa")
    curves = _as_curves(T_C_list, HF_Wg_list, rates_K_per_min, curves)
    result.rates = [c.rate_K_per_min for c in curves]
    if len(curves) < 3:
        result.quality_flags.append('too_few_rates')
        return result

    lo = max(float(np.nanmin(c.T_xt_C)) for c in curves if len(c.T_xt_C) > 0)
    hi = min(float(np.nanmax(c.T_xt_C)) for c in curves if len(c.T_xt_C) > 0)
    if not np.isfinite(lo) or not np.isfinite(hi) or hi - lo < 1.0:
        result.quality_flags.append('no_common_temperature_window')
        return result

    T_levels = np.linspace(lo + 0.05 * (hi - lo), hi - 0.05 * (hi - lo), 12)
    m_vals = []
    intercept_vals = []
    r2_vals = []
    for T_target in T_levels:
        beta_vals = []
        y_vals = []
        for curve in curves:
            X = _interp_X_at_temperature(curve, float(T_target))
            if not np.isfinite(X) or X <= 0.03 or X >= 0.97:
                continue
            beta_vals.append(curve.rate_K_per_min)
            y_vals.append(np.log(-np.log(1.0 - X)))
        if len(beta_vals) >= 3 and np.nanstd(beta_vals) > 1e-12:
            x = np.log(np.asarray(beta_vals, dtype=float))
            y = np.asarray(y_vals, dtype=float)
            slope, intercept, r, _, _ = stats.linregress(x, y)
            m_vals.append(-slope)
            intercept_vals.append(intercept)
            r2_vals.append(r ** 2)

    if m_vals:
        result.ozawa_n = float(np.mean(m_vals))
        result.ozawa_K_T = float(np.exp(np.mean(intercept_vals)))
        result.r_squared = float(np.mean(r2_vals))
    else:
        result.quality_flags.append('no_valid_ozawa_regression')
    return result


def kissinger_analysis(Tp_C_list: List[float],
                       rates_K_per_min: List[float],
                       ) -> NonIsothermalResult:
    """Kissinger method for crystallisation activation energy."""
    result = NonIsothermalResult(method="Kissinger")
    Tp = np.asarray(Tp_C_list, dtype=float)
    beta = np.abs(np.asarray(rates_K_per_min, dtype=float))
    valid = np.isfinite(Tp) & np.isfinite(beta) & (beta > 0)
    Tp, beta = Tp[valid], beta[valid]
    result.rates = beta.tolist()

    if len(Tp) < 3:
        result.quality_flags.append('too_few_rates')
        return result

    Tp_K = Tp + 273.15
    x = 1.0 / Tp_K
    y = np.log(beta / Tp_K ** 2)

    slope, _, r, _, _ = stats.linregress(x, y)
    R = 8.314462618
    result.kissinger_Ea_kJmol = float(-slope * R / 1000.0)
    result.r_squared = float(r ** 2)
    return result


def friedman_analysis(T_C_list: List[np.ndarray],
                      HF_Wg_list: List[np.ndarray],
                      rates_K_per_min: List[float],
                      X_levels: List[float] = None,
                      curves: Optional[List[NonIsothermalCurve]] = None,
                      ) -> NonIsothermalResult:
    """Friedman isoconversional method."""
    result = NonIsothermalResult(method="Friedman")
    curves = _as_curves(T_C_list, HF_Wg_list, rates_K_per_min, curves)
    result.rates = [c.rate_K_per_min for c in curves]
    if X_levels is None:
        X_levels = np.linspace(0.1, 0.9, 9).tolist()

    if len(curves) < 3:
        result.quality_flags.append('too_few_rates')
        return result

    R = 8.314462618
    r2_vals = []
    for X_target in X_levels:
        inv_T_vals = []
        ln_dXdt_vals = []
        for curve in curves:
            if len(curve.Xt) < 5 or len(curve.t_xt_min) != len(curve.Xt):
                continue
            T_at_X = _interp_at_conversion(curve, X_target, curve.T_xt_C)
            if not np.isfinite(T_at_X):
                continue
            dXdt = np.gradient(curve.Xt, curve.t_xt_min, edge_order=1)
            rate_at_X = _interp_at_conversion(curve, X_target, np.abs(dXdt))
            if not np.isfinite(rate_at_X) or rate_at_X <= 0:
                continue
            inv_T_vals.append(1.0 / (T_at_X + 273.15))
            ln_dXdt_vals.append(np.log(rate_at_X))

        if len(inv_T_vals) >= 3 and np.nanstd(inv_T_vals) > 1e-12:
            slope, _, r, _, _ = stats.linregress(inv_T_vals, ln_dXdt_vals)
            result.friedman_Ea[float(X_target)] = float(-slope * R / 1000.0)
            r2_vals.append(r ** 2)

    if r2_vals:
        result.r_squared = float(np.mean(r2_vals))
    else:
        result.quality_flags.append('no_valid_friedman_regression')
    return result


def mo_analysis(T_C_list: List[np.ndarray],
                HF_Wg_list: List[np.ndarray],
                rates_K_per_min: List[float],
                X_levels: List[float] = None,
                curves: Optional[List[NonIsothermalCurve]] = None,
                ) -> NonIsothermalResult:
    """Mo Zhishen method: log(beta) = log(F(T)) - a log(t)."""
    result = NonIsothermalResult(method="Mo")
    curves = _as_curves(T_C_list, HF_Wg_list, rates_K_per_min, curves)
    result.rates = [c.rate_K_per_min for c in curves]
    if X_levels is None:
        X_levels = [0.2, 0.4, 0.5, 0.6, 0.8]

    if len(curves) < 3:
        result.quality_flags.append('too_few_rates')
        return result

    a_vals = []
    f_vals = []
    r2_vals = []
    for X_target in X_levels:
        beta_vals = []
        t_vals = []
        for curve in curves:
            t_at_X = _interp_at_conversion(curve, X_target, curve.t_xt_min)
            if np.isfinite(t_at_X) and t_at_X > 0:
                beta_vals.append(curve.rate_K_per_min)
                t_vals.append(t_at_X)
        if len(beta_vals) >= 3 and np.nanstd(t_vals) > 1e-12:
            x = np.log10(np.asarray(t_vals, dtype=float))
            y = np.log10(np.asarray(beta_vals, dtype=float))
            slope, intercept, r, _, _ = stats.linregress(x, y)
            a_vals.append(-slope)
            f_vals.append(10 ** intercept)
            r2_vals.append(r ** 2)

    if a_vals:
        result.mo_a = float(np.mean(a_vals))
        result.mo_F_T = float(np.mean(f_vals))
        result.r_squared = float(np.mean(r2_vals))
    else:
        result.quality_flags.append('no_valid_mo_regression')
    return result


def analyze_nonisothermal_scans(scans: List[DSCScan], **kwargs) -> NonIsothermalKineticsSeries:
    """Run non-isothermal crystallisation kinetics over a DSC rate series."""
    series = NonIsothermalKineticsSeries()
    curves = extract_nonisothermal_curves(scans, **kwargs)
    series.curves = curves
    if len(curves) < 3:
        series.quality_flags.append('too_few_cooling_rates')
        return series

    T_list = [c.T_C for c in curves]
    HF_list = [c.HF_Wg for c in curves]
    rates = [c.rate_K_per_min for c in curves]
    Tp = [c.Tp_C for c in curves]

    series.kissinger = kissinger_analysis(Tp, rates)
    series.ozawa = ozawa_analysis(T_list, HF_list, rates, curves=curves)
    series.mo = mo_analysis(T_list, HF_list, rates, curves=curves)
    series.friedman = friedman_analysis(T_list, HF_list, rates, curves=curves)
    return series


# ---------------------------------------------------------------------------
#  Convenience: full kinetics analysis
# ---------------------------------------------------------------------------

def analyze_kinetics(data: Dict[str, Any], mode: str = 'auto') -> Dict[str, Any]:
    """Run all applicable kinetics analyses.

    Parameters
    ----------
    data : dict
        Must contain keys for the chosen mode:
        - isothermal: 'time_min', 'HF_Wg'
        - non_isothermal: 'T_C_list', 'HF_Wg_list', 'rates_K_per_min',
          'Tp_C_list' (for Kissinger)
    mode : str
        'isothermal', 'non_isothermal', 'auto'

    Returns
    -------
    dict with keys: avrami, ozawa, kissinger, friedman, mo
    """
    results = {}

    if mode in ('isothermal', 'auto'):
        if 'scans' in data:
            iso = analyze_isothermal_scans(
                data['scans'],
                **data.get('isothermal_kwargs', {}),
            )
            results['isothermal'] = iso
            if np.isfinite(iso.best.n):
                results['avrami'] = iso.best
            results['avrami_series'] = iso.avrami_results
        elif 'time_min' in data:
            results['avrami'] = avrami_from_dsc(data['time_min'], data['HF_Wg'])

    if mode in ('non_isothermal', 'auto'):
        if 'scans' in data:
            series = analyze_nonisothermal_scans(
                data['scans'],
                **data.get('nonisothermal_kwargs', {}),
            )
            results['non_isothermal'] = series
            results['ozawa'] = series.ozawa
            results['mo'] = series.mo
            results['friedman'] = series.friedman
            results['kissinger'] = series.kissinger
        elif 'T_C_list' in data:
            T_list = data['T_C_list']
            HF_list = data['HF_Wg_list']
            rates = data['rates_K_per_min']
            curves = build_nonisothermal_curves(T_list, HF_list, rates)

            results['non_isothermal'] = NonIsothermalKineticsSeries(curves=curves)
            results['ozawa'] = ozawa_analysis(T_list, HF_list, rates, curves=curves)
            results['mo'] = mo_analysis(T_list, HF_list, rates, curves=curves)
            results['friedman'] = friedman_analysis(T_list, HF_list, rates, curves=curves)

            if 'Tp_C_list' in data:
                results['kissinger'] = kissinger_analysis(data['Tp_C_list'], rates)
            else:
                results['kissinger'] = kissinger_analysis(
                    [c.Tp_C for c in curves],
                    [c.rate_K_per_min for c in curves],
                )

    return results
