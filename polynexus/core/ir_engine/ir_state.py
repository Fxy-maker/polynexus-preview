"""IR state judgment module (IR-B).

Determines polymer state (crystalline / amorphous / semi-crystalline)
from IR spectral features, DSC data, or user specification.
"""

import numpy as np
from typing import Dict, List, Optional

from .names import normalize_ir_polymer_name


def judge_from_dsc(dsc_result):
    """Judge polymer state from DSC crystallinity.

    Returns 'crystalline', 'semi_crystalline', 'amorphous', or 'unknown'.
    """
    xc = getattr(dsc_result, 'Xc_pct', np.nan)
    if np.isnan(xc):
        return 'unknown'
    if xc > 50:
        return 'crystalline'
    elif xc > 5:
        return 'semi_crystalline'
    else:
        return 'amorphous'


def judge_from_ir_crystallinity_bands(spectrum, polymer_name="",
                                       crystalline_bands=None,
                                       amorphous_bands=None):
    """Judge polymer state from IR crystallinity-sensitive bands.

    Compares absorbance of crystalline vs amorphous bands.
    """
    if crystalline_bands is None or amorphous_bands is None:
        return 'unknown', 0.0

    wn = spectrum.wavenumber
    A = spectrum.absorbance

    def band_intensity(target, tol=5):
        idx = np.argmin(np.abs(wn - target))
        mask = np.abs(wn - target) <= tol
        if np.sum(mask) > 0:
            return np.max(A[mask])
        return A[idx] if 0 <= idx < len(A) else 0.0

    A_cryst = np.mean([band_intensity(b) for b in crystalline_bands])
    A_am = np.mean([band_intensity(b) for b in amorphous_bands])

    if A_cryst < 1e-6 and A_am < 1e-6:
        return 'unknown', 0.0

    ratio = A_cryst / (A_cryst + A_am) if (A_cryst + A_am) > 0 else 0.0

    if ratio > 0.7:
        return 'crystalline', ratio
    elif ratio > 0.3:
        return 'semi_crystalline', ratio
    else:
        return 'amorphous', ratio


# Polymer-specific crystalline/amorphous band pairs
IR_CRYSTALLINITY_BANDS = {
    "PE": {
        "crystalline": [730, 1463],
        "amorphous": [720, 1468],
    },
    "PP": {
        "crystalline": [998, 841, 1167],
        "amorphous": [973, 1153],
    },
    "PET": {
        "crystalline": [1340, 972, 872],
        "amorphous": [1370, 1042, 898],
    },
    "PA6": {
        "crystalline": [1200, 929, 1120],
        "amorphous": [1170, 1124],
    },
    "PA66": {
        "crystalline": [1202, 935, 1275],
        "amorphous": [1145, 1418],
    },
    "POM": {
        "crystalline": [1095, 935, 895],
        "amorphous": [1238, 1470],
    },
    "PEEK": {
        "crystalline": [1652, 1225, 841],
        "amorphous": [1310, 1165, 929],
    },
    "PVDF": {
        "crystalline_alpha": [976, 796, 614],
        "crystalline_beta": [1275, 840],
        "amorphous": [880, 740],
    },
}


def judge_polymer_state(spectrum=None, dsc_result=None,
                        polymer_name="", user_override=""):
    """Unified polymer state judgment.

    Priority: user_override > DSC > IR > unknown

    Parameters
    ----------
    spectrum : IRSpectrum or None
    dsc_result : DSCResult or None
    polymer_name : str
    user_override : str
        'crystalline', 'semi_crystalline', 'amorphous', or ''.

    Returns
    -------
    dict with {state, confidence, method}
    """
    if user_override:
        return {'state': user_override, 'confidence': 1.0, 'method': 'user'}

    if dsc_result is not None:
        state = judge_from_dsc(dsc_result)
        if state != 'unknown':
            return {'state': state, 'confidence': 0.8, 'method': 'dsc'}

    polymer_key = normalize_ir_polymer_name(polymer_name)
    if spectrum is not None and polymer_key in IR_CRYSTALLINITY_BANDS:
        bands = IR_CRYSTALLINITY_BANDS[polymer_key]
        state, ratio = judge_from_ir_crystallinity_bands(
            spectrum, polymer_key, bands.get('crystalline'), bands.get('amorphous'))
        if state != 'unknown':
            return {'state': state, 'confidence': ratio, 'method': 'ir'}

    return {'state': 'unknown', 'confidence': 0.0, 'method': 'none'}
