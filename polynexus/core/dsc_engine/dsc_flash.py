"""DSC Flash DSC module (D4C).

Handles ultra-fast scanning calorimetry (Flash DSC, chip calorimetry).
Key differences from conventional DSC:
    - Extremely high heating/cooling rates (>1000 K/s)
    - Thermal lag correction is critical
    - Sample masses in nanograms
    - Analyses crystallisation suppression and reorganisation
"""

import numpy as np
from .core import analyze_scan, compute_Tg, find_thermal_events
from .config import DSCConfig
from .io import DSCScan


def correct_thermal_lag(T_measured, HF, rate_K_per_s, tau_s=0.001):
    """Correct for thermal lag in Flash DSC.

    T_true = T_measured - tau * dT/dt

    For Flash DSC with rates > 1000 K/s, the thermal lag time constant
    tau is typically 0.1–5 ms.

    Parameters
    ----------
    tau_s : float
        Thermal lag time constant in seconds.
    """
    beta_K_s = abs(rate_K_per_s)
    dT = tau_s * beta_K_s
    return np.asarray(T_measured) - dT, HF


def analyze_flash_heating(scan, config, tau_s=0.001):
    """Analyze a Flash DSC heating curve with thermal lag correction.

    Flash DSC heating reveals:
        - True melting point (minimal reorganisation)
        - Zero-entropy-production melting temperature
        - Crystallinity without cold crystallisation interference
    """
    T = scan.T_C.copy()
    HF = scan.HF_Wg.copy()
    rate = abs(scan.rate_K_per_min) / 60.0  # K/s

    # Thermal lag correction
    T_corr, _ = correct_thermal_lag(T, HF, rate, tau_s)

    scan_corr = DSCScan(
        label=scan.label,
        T_C=T_corr, HF_Wg=HF,
        mass_mg=scan.mass_mg,
        rate_K_per_min=scan.rate_K_per_min,
    )

    return analyze_scan(scan_corr.T_C, scan_corr.HF_Wg, config, label=scan.label)


def analyze_flash_cooling(scan, config, tau_s=0.001):
    """Analyze a Flash DSC cooling curve.

    Ultra-fast cooling can completely suppress crystallisation.
    The critical cooling rate to suppress crystallisation is a key parameter.
    """
    T = scan.T_C.copy()
    HF = scan.HF_Wg.copy()
    rate = abs(scan.rate_K_per_min) / 60.0

    # Thermal lag correction
    T_corr, _ = correct_thermal_lag(T, HF, rate, tau_s)

    # Find crystallisation exotherm
    events = find_thermal_events(T_corr, HF, event_type='crystallisation')

    result = {
        'T_onset_C': np.nan, 'T_peak_C': np.nan,
        'DHc_Jg': np.nan, 'cooling_rate_K_s': rate,
        'crystallisation_suppressed': False,
    }

    if events['crystallisation']:
        main = events['crystallisation'][0]
        result['T_onset_C'] = main['onset_C']
        result['T_peak_C'] = main['peak_C']
        result['DHc_Jg'] = main['enthalpy_Jg']
    else:
        result['crystallisation_suppressed'] = True

    return result


def critical_cooling_rate(rates_K_per_min, has_crystallisation):
    """Determine critical cooling rate to suppress crystallisation.

    The critical rate is the minimum rate at which no crystallisation is observed.
    """
    for rate, has_cryst in sorted(zip(rates_K_per_min, has_crystallisation)):
        if not has_cryst:
            return rate
    return np.nan
