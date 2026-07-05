"""IR configuration module.

Defines IRConfig with polymer IR peak databases and frequency correction factors.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any


@dataclass
class IRConfig:
    """Configuration for IR analysis engine.

    Attributes
    ----------
    wavenumber_range : tuple
        (min, max) in cm^-1.  Typical mid-IR: (400, 4000).
    baseline_method : str
        'rubberband', 'linear', 'polynomial', 'als' (asymmetric least squares).
    atr_correction : bool
        Apply ATR penetration depth correction.
    atr_crystal : str
        ATR crystal material: 'diamond', 'ZnSe', 'Ge'.
    atr_angle_deg : float
        ATR incidence angle.
    smooth_method : str
        'savgol', 'none'.
    smooth_window : int
    smooth_order : int
    peak_height_min : float
        Minimum peak height (fraction of max absorbance).
    peak_prominence_min : float
        Minimum peak prominence (fraction of signal range).
    peak_distance : float
        Minimum wavenumber distance between peaks (cm^-1).
    crystallinity_band : str
        Band used for crystallinity: name of the crystalline-sensitive band.
    crystallinity_ref_band : str
        Reference band (internal standard).
    freq_correction_factor : float
        Global frequency scaling factor for DFT-computed frequencies.
        Typical: 0.9613 (B3LYP/6-31G*), 0.950 (B3LYP/def2-TZVP).
    lineshape : str
        'lorentzian', 'gaussian', 'pseudo_voigt'.
    fwhm_default : float
        Default FWHM for simulated spectra (cm^-1).
    """

    # --- Spectral range ---
    wavenumber_range: Tuple[float, float] = (400.0, 4000.0)

    # --- Preprocessing ---
    baseline_method: str = "rubberband"
    baseline_lam: float = 1e6       # ALS smoothness parameter
    baseline_p: float = 0.001       # ALS asymmetry parameter
    atr_correction: bool = False
    atr_crystal: str = "diamond"    # n = 2.42
    atr_angle_deg: float = 45.0
    smooth_method: str = "savgol"
    smooth_window: int = 7
    smooth_order: int = 3
    normalise: bool = True
    normalization_method: str = "minmax"  # 'minmax', 'area', 'peak', 'none'

    # --- Peak detection ---
    peak_height_min: float = 0.02
    peak_prominence_min: float = 0.015
    peak_distance: float = 12.0    # cm^-1
    peak_max_count: int = 40
    peak_fit_window_cm1: float = 35.0
    assignment_tolerance_cm1: float = 18.0
    band_tolerance_cm1: float = 10.0
    cross_peak_exclusion_cm1: float = 35.0
    sequence_axis_metadata_path: str = ""
    sequence_axis_mode: str = "auto"  # 'auto', 'filename', 'metadata'
    polymer_name: str = ""         # optional user hint, e.g. "PA6"

    # --- Crystallinity ---
    crystallinity_band: str = ""    # e.g. "1896" for PET
    crystallinity_ref_band: str = "" # e.g. "1410" for PET

    # --- Spectrum simulation ---
    freq_correction_factor: float = 0.9613
    lineshape: str = "lorentzian"
    fwhm_default: float = 8.0      # cm^-1

    # --- Output ---
    output_dir: str = ""
    fig_format: str = "svg"
    fig_dpi: int = 300

    # --- Polymer IR peak assignment database ---
    # Format: {polymer: [(wavenumber_cm-1, assignment, intensity, crystallinity_sensitive)]}
    polymer_peaks_db: Dict[str, List[Tuple[float, str, str, bool]]] = field(default_factory=lambda: {
        "PE": [
            (2918, "vas(CH2)", "vs", False),
            (2850, "vs(CH2)", "vs", False),
            (1472, "δ(CH2) scissoring", "s", False),
            (1463, "δ(CH2) crystalline", "m", True),
            (730, "ρ(CH2) crystalline", "m", True),
            (720, "ρ(CH2) amorphous", "m", False),
        ],
        "PP": [
            (2950, "vas(CH3)", "s", False),
            (2918, "vas(CH2)", "s", False),
            (2868, "vs(CH3)", "s", False),
            (2840, "vs(CH2)", "s", False),
            (1458, "deltaas(CH3)", "m", False),
            (1377, "deltas(CH3)", "m", False),
            (1167, "nu(C-C) + rho(CH3)", "m", True),
            (998, "rho(CH3) + nu(C-CH3)", "m", True),
            (973, "rho(CH3) + nu(C-C)", "m", True),
            (841, "rho(CH2) + nu(C-CH3)", "m", True),
        ],
        "iPP": [
            (2950, "vas(CH3)", "s", False),
            (2918, "vas(CH2)", "s", False),
            (2868, "vs(CH3)", "s", False),
            (2840, "vs(CH2)", "s", False),
            (1458, "δas(CH3)", "m", False),
            (1377, "δs(CH3)", "m", False),
            (1167, "ν(C-C) + ρ(CH3)", "m", True),
            (998, "ρ(CH3) + ν(C-CH3)", "m", True),
            (973, "ρ(CH3) + ν(C-C)", "m", True),
            (841, "ρ(CH2) + ν(C-CH3)", "m", True),
        ],
        "PET": [
            (1715, "ν(C=O)", "vs", False),
            (1505, "ν(C-C) ring", "w", False),
            (1471, "δ(CH2)", "w", False),
            (1410, "δ(CH2) + ν(C-C) ring", "m", False),
            (1340, "ω(CH2) trans", "m", True),
            (1243, "ν(C-O) + δ(O-H)", "vs", False),
            (1120, "ν(C-O)", "s", False),
            (1098, "ν(C-O)", "s", False),
            (972, "ω(CH2) gauche", "w", True),
            (896, "γ(C-H) ring", "w", False),
            (872, "γ(C-H) ring", "m", True),
            (793, "γ(C-H) ring", "w", False),
            (725, "γ(C=O) + δ(ring)", "s", False),
        ],
        "PA6": [
            (3298, "ν(N-H)", "m", False),
            (2931, "vas(CH2)", "s", False),
            (2860, "vs(CH2)", "s", False),
            (1637, "amide I ν(C=O)", "vs", False),
            (1541, "amide II δ(N-H)+ν(C-N)", "s", False),
            (1463, "δ(CH2)", "m", False),
            (1418, "δ(CH2) adjacent to NH", "w", False),
            (1263, "amide III ν(C-N)+δ(N-H)", "m", False),
            (1200, "amide III + ω(CH2)", "m", True),
            (1120, "ν(C-C) skeletal", "w", True),
            (1027, "amide IV", "w", False),
            (929, "amide V γ(N-H)", "w", True),
            (685, "amide V γ(N-H)", "m", False),
        ],
        "PA66": [
            (3300, "N-H hydrogen bonded", "m", False),
            (2935, "vas(CH2)", "s", False),
            (2860, "vs(CH2)", "s", False),
            (1635, "amide I nu(C=O)", "vs", False),
            (1540, "amide II delta(N-H)+nu(C-N)", "s", False),
            (1470, "delta(CH2)", "m", False),
            (1418, "delta(CH2) adjacent to NH", "w", False),
            (1275, "amide III nu(C-N)+delta(N-H)", "m", True),
            (1202, "amide III + omega(CH2) crystalline", "m", True),
            (1145, "nu(C-C) skeletal", "w", False),
            (935, "amide V gamma(N-H) crystalline", "w", True),
            (690, "amide V gamma(N-H)", "m", True),
            (580, "amide VI delta(C=O)", "w", False),
        ],
        "POM": [
            (2975, "vas(CH2)", "m", False),
            (2910, "vs(CH2)", "m", False),
            (1470, "delta(CH2)", "m", False),
            (1435, "delta(CH2)", "m", False),
            (1238, "nu(C-O-C) + omega(CH2)", "s", True),
            (1095, "nuas(C-O-C)", "vs", True),
            (935, "nus(C-O-C) + rho(CH2)", "vs", True),
            (895, "nu(C-O-C) + rho(CH2)", "m", True),
            (630, "delta(O-C-O)", "m", False),
        ],
        "PEEK": [
            (1652, "nu(C=O) diaryl ketone", "vs", True),
            (1595, "nu(C=C) aromatic ring", "s", True),
            (1490, "nu(C=C) aromatic ring", "vs", True),
            (1310, "nu(C-O) diaryl ether", "m", False),
            (1225, "nuas(C-O-C) diphenyl ether", "vs", True),
            (1188, "delta(C-H) in-plane", "m", False),
            (1165, "nuas(C-O-C)", "s", False),
            (929, "nu(C-O) + delta(ring)", "w", False),
            (841, "gamma(C-H) 1,4-disubstituted", "s", True),
            (766, "gamma(C-H)", "m", True),
        ],
        "PCL": [
            (2944, "vas(CH2)", "s", False),
            (2865, "vs(CH2)", "s", False),
            (1724, "ν(C=O) ester", "vs", False),
            (1471, "δ(CH2)", "m", False),
            (1418, "δ(CH2)", "w", False),
            (1366, "ω(CH2)", "w", False),
            (1294, "ν(C-O)+ν(C-C) crystalline", "m", True),
            (1240, "νas(C-O-C)", "s", False),
            (1190, "ν(C-O-C)", "m", False),
            (1165, "ν(C-O)", "s", False),
            (1107, "ν(C-O)", "m", False),
            (1045, "ν(C-O)", "m", False),
            (960, "ν(C-C) skeletal", "w", False),
            (732, "ρ(CH2)", "w", False),
        ],
        "PVDF": [
            (3025, "vas(CH2)", "w", False),
            (2985, "vs(CH2)", "w", False),
            (1402, "δ(CH2) + ω(CH2)", "m", False),
            (1275, "ν(C-F) + δ(CCC)", "m", True),    # beta phase
            (1234, "ν(C-F) + δ(CCC)", "m", False),   # gamma phase
            (1182, "νas(CF2)", "vs", False),
            (1073, "ν(C-C) skeletal", "m", False),
            (976, "ω(CH2)", "w", True),               # alpha phase
            (879, "νs(CF2) + ν(C-C)", "m", False),
            (840, "ρ(CH2) + νas(CF2)", "s", True),    # beta phase
            (796, "ρ(CH2)", "m", True),               # alpha phase
            (763, "δ(CF2) + ω(CH2)", "w", True),
            (614, "δ(CF2) + δ(CCC)", "m", True),
            (532, "δ(CF2)", "w", True),
            (489, "ω(CF2)", "w", True),
        ],
        "PLLA": [
            (2997, "vas(CH3)", "w", False),
            (2946, "vas(CH3)", "w", False),
            (2881, "vs(CH3)", "w", False),
            (1757, "ν(C=O) ester", "vs", False),
            (1454, "δas(CH3)", "m", False),
            (1383, "δs(CH3)", "m", False),
            (1360, "δ(CH) + δs(CH3)", "m", False),
            (1268, "ν(C-O) + δ(CH)", "m", True),
            (1212, "νas(C-O-C) + ras(CH3)", "s", True),
            (1185, "νas(C-O-C) + ras(CH3)", "s", False),
            (1130, "ras(CH3)", "m", False),
            (1085, "νs(C-O-C)", "s", False),
            (1045, "ν(C-CH3)", "m", False),
            (956, "ν(C-C) + ρ(CH3)", "w", True),
            (921, "ν(C-C) + ρ(CH3)", "w", True),
            (871, "ν(C-C) skeletal", "m", False),
            (756, "δ(C=O)", "w", False),
        ],
    })

    # --- Frequency correction factors (DFT level → factor) ---
    freq_correction_db: Dict[str, float] = field(default_factory=lambda: {
        "B3LYP/6-31G(d)":    0.9613,
        "B3LYP/6-31G(d,p)":  0.9614,
        "B3LYP/6-311+G(d,p)": 0.9679,
        "B3LYP/def2-TZVP":   0.9650,
        "B3LYP/def2-SVP":    0.9700,
        "B3LYP-D3/6-31G(d)": 0.9610,
        "wB97XD/6-31G(d)":   0.9520,
        "M06-2X/6-31G(d)":   0.9500,
        "PBE0/6-31G(d)":     0.9540,
        "HF/6-31G(d)":       0.8953,
        "MP2/6-31G(d)":      0.9430,
    })

    def get_correction_factor(self, level: str = "") -> float:
        """Return frequency correction factor for a DFT level."""
        if level and level in self.freq_correction_db:
            return self.freq_correction_db[level]
        return self.freq_correction_factor

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        for fld in self.__dataclass_fields__:
            if fld in ("polymer_peaks_db", "freq_correction_db"):
                continue
            d[fld] = getattr(self, fld)
        return d
