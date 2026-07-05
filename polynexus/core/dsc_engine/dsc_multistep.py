"""DSC multi-step transition analysis (D6).

Handles:
    - Multiple melting peaks (polymorphs, recrystallisation)
    - Polymorph identification (alpha, beta, gamma forms)
    - Mesophase / liquid crystal transitions
    - Multi-step glass transitions
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from .core import deconvolve_peaks


# Polymer polymorph database: (Tm_range, dHm_range, identifying features)
POLYMORPH_DB = {
    "iPP": {
        "alpha":  {"Tm_range": (155, 170), "dHm_Jg": 207, "notes": "Most common, monoclinic"},
        "beta":   {"Tm_range": (145, 155), "dHm_Jg": 170, "notes": "Hexagonal, lower Tm"},
        "gamma":  {"Tm_range": (150, 160), "dHm_Jg": 175, "notes": "Orthorhombic, rare in homopolymer"},
        "meso":   {"Tm_range": (40,  80),  "dHm_Jg": 30,  "notes": "Smectic mesophase"},
    },
    "PA6": {
        "alpha":  {"Tm_range": (215, 225), "dHm_Jg": 230, "notes": "Monoclinic, most stable"},
        "gamma":  {"Tm_range": (210, 218), "dHm_Jg": 210, "notes": "Pseudo-hexagonal, less stable"},
        "alpha_prime": {"Tm_range": (200, 210), "dHm_Jg": 200, "notes": "Disordered alpha, intermediate"},
    },
    "PVDF": {
        "alpha":  {"Tm_range": (165, 175), "dHm_Jg": 104.7, "notes": "Non-polar TGTG, most common"},
        "beta":   {"Tm_range": (168, 178), "dHm_Jg": 108,   "notes": "Ferroelectric all-trans"},
        "gamma":  {"Tm_range": (170, 180), "dHm_Jg": 106,   "notes": "T3GT3G polar"},
        "delta":  {"Tm_range": (165, 175), "dHm_Jg": 102,   "notes": "Polar form of alpha"},
    },
    "PET": {
        "alpha":  {"Tm_range": (250, 265), "dHm_Jg": 140, "notes": "Triclinic, standard crystalline"},
        "beta":   {"Tm_range": (240, 255), "dHm_Jg": 120, "notes": "Strain-induced, less perfect"},
    },
    "PLLA": {
        "alpha":  {"Tm_range": (170, 185), "dHm_Jg": 93,  "notes": "Orthorhombic 10_3 helix"},
        "alpha_prime": {"Tm_range": (150, 165), "dHm_Jg": 80, "notes": "Disordered alpha, lower T_c"},
        "beta":   {"Tm_range": (175, 185), "dHm_Jg": 124, "notes": "Trigonal 3_1 helix, high-T fibre"},
        "gamma":  {"Tm_range": (170, 180), "dHm_Jg": 90,  "notes": "Orthorhombic, epitaxial"},
        "stereocomplex": {"Tm_range": (220, 230), "dHm_Jg": 142, "notes": "PLLA/PDLA co-crystal"},
    },
    "PE": {
        "orthorhombic": {"Tm_range": (125, 140), "dHm_Jg": 293, "notes": "Standard PE crystal"},
        "monoclinic":   {"Tm_range": (130, 138), "dHm_Jg": 280, "notes": "Stress-induced, metastable"},
        "hexagonal":    {"Tm_range": (145, 155), "dHm_Jg": 250, "notes": "High-pressure phase"},
    },
}


TRANSITION_TYPES = {
    "melting":       "First-order: crystalline -> liquid",
    "crystallisation":"First-order: liquid -> crystalline (on cooling)",
    "cold_cryst":    "First-order: amorphous -> crystalline (on heating)",
    "recrystallisation": "First-order: metastable crystal -> stable crystal",
    "polymorph_transition": "Solid-solid: one crystal form -> another",
    "mesophase":     "First-order or continuous: crystal -> liquid crystal",
    "glass":         "Second-order: glass -> supercooled liquid",
    "enthalpic_relaxation": "Non-equilibrium: physical ageing recovery",
}


def classify_transition(T_onset, T_peak, dH_Jg, polymer_name="",
                        total_dHm=None, heating=True):
    """Classify a DSC thermal event.

    Returns dict: {type, polymorph, confidence, description}
    """
    result = {'type': 'unknown', 'polymorph': '', 'confidence': 0.0}

    if polymer_name in POLYMORPH_DB:
        db = POLYMORPH_DB[polymer_name]
        best_match = None
        best_score = 0

        for form_name, info in db.items():
            t_low, t_high = info['Tm_range']
            dHm_ref = info['dHm_Jg']

            # Score based on temperature match
            if t_low <= T_peak <= t_high:
                t_score = 1.0 - abs(T_peak - (t_low + t_high) / 2) / ((t_high - t_low) / 2)
            else:
                dist = min(abs(T_peak - t_low), abs(T_peak - t_high))
                t_score = max(0, 1.0 - dist / 20)

            # Score based on enthalpy match
            if dHm_ref > 0 and not np.isnan(dH_Jg):
                h_score = 1.0 - min(1.0, abs(dH_Jg - dHm_ref) / dHm_ref)
            else:
                h_score = 0.5

            score = 0.6 * t_score + 0.4 * h_score
            if score > best_score:
                best_score = score
                best_match = form_name

        if best_match and best_score > 0.3:
            result['polymorph'] = best_match
            result['confidence'] = best_score

    # Classify transition type
    if heating:
        if dH_Jg < -1:  # endothermic (exo-up: negative)
            if T_peak > 200 and abs(dH_Jg) > 20:
                result['type'] = 'melting'
            elif abs(dH_Jg) < 5:
                result['type'] = 'glass' if 30 < T_peak < 200 else 'mesophase'
            else:
                result['type'] = 'melting'
        elif dH_Jg > 1:  # exothermic
            if T_onset < 180:
                result['type'] = 'cold_cryst'
            else:
                result['type'] = 'recrystallisation'
        else:
            result['type'] = 'glass'
    else:
        if dH_Jg > 1:
            result['type'] = 'crystallisation'

    return result


def detect_multistep_events(T, HF, config, polymer_name=""):
    """Full multi-step analysis: detect, fit, classify all events.

    Returns list of {peak_params, classification}
    """
    from .core import find_thermal_events

    events = find_thermal_events(T, HF)

    results = []
    for event_type in ['melting', 'crystallisation']:
        for evt in events[event_type]:
            classification = classify_transition(
                evt['onset_C'], evt['peak_C'], evt['enthalpy_Jg'],
                polymer_name=polymer_name,
            )

            if len(events['melting']) > 1:
                # Deconvolve overlapping peaks
                fitted, r2, _ = deconvolve_peaks(
                    T, HF, len(events['melting']), peak_type='gaussian')

            results.append({
                'T_onset_C': evt['onset_C'],
                'T_peak_C': evt['peak_C'],
                'T_end_C': evt['end_C'],
                'dH_Jg': evt['enthalpy_Jg'],
                'is_endotherm': evt['is_endotherm'],
                'classification': classification,
            })

    return results
