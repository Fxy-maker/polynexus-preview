"""NMR configuration module.

Defines NMRConfig with polymer chemical shift databases and reference data.
"""

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, Any


@dataclass
class NMRConfig:
    """Configuration for solid-state NMR analysis engine.

    Attributes
    ----------
    nucleus : str
        '13C', '1H', '15N', '19F', '29Si', '31P'.
    frequency_MHz : float
        Larmor frequency.
    reference_ppm : float
        Chemical shift reference (0 ppm = TMS for 1H/13C).
    reference_compound : str
        e.g. 'TMS', 'adamantane', 'glycine'.
    baseline_method : str
        'polynomial', 'linear', 'spline'.
    baseline_order : int
    apodization : str
        'exponential' (LB), 'gaussian' (GB), 'none'.
    lb_Hz : float
        Line broadening in Hz.
    gb : float
        Gaussian broadening factor.
    peak_distance_ppm : float
        Minimum distance between peaks in ppm.
    peak_height_min : float
        Minimum relative peak height.
    deconvolution_method : str
        'lorentzian', 'gaussian', 'mixed'.
    crystallinity_peak : float
        Chemical shift of crystalline-sensitive peak for crystallinity quantification.
    crystallinity_ref_peak : float
        Reference peak chemical shift.
    output_dir : str
    fig_format : str
    fig_dpi : int
    """

    # --- Experiment class ---
    sample_state: str = "solid"    # "liquid" or "solid"
    spectrum_mode: str = "auto"    # "auto", "fid", or "processed"

    # --- Nucleus ---
    nucleus: str = "13C"
    frequency_MHz: float = 100.6   # 13C at 9.4T
    reference_ppm: float = 0.0     # TMS
    reference_compound: str = "TMS"

    # --- Preprocessing ---
    baseline_method: str = "polynomial"
    baseline_order: int = 5
    apodization: str = "exponential"
    lb_Hz: float = 10.0
    gb: float = 0.1
    phase_correction: bool = True
    left_shift_points: int = 0
    fid_zero_fill_factor: int = 2
    fid_exponential_decay: float = 3.0

    # --- Peak detection ---
    peak_distance_ppm: float = 1.0
    peak_height_min: float = 0.03
    max_peaks: int = 18

    # --- Optional explicit regions for sensitivity/reproducibility ---
    # ``None`` keeps the nucleus/state-specific generic windows.  When set,
    # callers provide named ``{label: (low_ppm, high_ppm)}`` windows; no
    # material-specific defaults are inferred by the engine.
    region_windows_ppm: Optional[Dict[str, Tuple[float, float]]] = None

    # --- Default ppm axes used when vendor metadata is incomplete ---
    liquid_1h_range: Tuple[float, float] = (12.5, -0.5)
    liquid_13c_range: Tuple[float, float] = (220.0, -10.0)
    solid_1h_range: Tuple[float, float] = (60.0, -20.0)
    solid_13c_range: Tuple[float, float] = (240.0, -20.0)

    # --- Deconvolution ---
    deconvolution_method: str = "mixed"   # 50:50 Gaussian:Lorentzian

    # --- Crystallinity ---
    crystallinity_peak: float = 0.0
    crystallinity_ref_peak: float = 0.0
    polymer_name: str = ""
    allow_unscoped_polymer_db_match: bool = False
    crystalline_phase_labels: Tuple[str, ...] = ("c",)
    amorphous_phase_labels: Tuple[str, ...] = ("a", "i")

    # --- Relaxation ---
    t1_analysis: bool = False
    t2_analysis: bool = False

    # --- Output ---
    output_dir: str = ""
    fig_format: str = "svg"
    fig_dpi: int = 300

    # --- 13C chemical shift database for polymers (ppm from TMS) ---
    # Format: {polymer: {group: (shift_ppm, phase, notes)}}
    # phase: 'c'=crystalline, 'a'=amorphous, 'i'=intermediate
    polymer_13c_db: Dict[str, Dict[str, Tuple[float, str, str]]] = field(default_factory=lambda: {
        "PE": {
            "CH2": (32.9, "c", "orthorhombic crystalline"),
            "CH2_am": (30.6, "a", "amorphous"),
            "CH2_mono": (34.0, "c", "monoclinic crystalline"),
        },
        "iPP": {
            "CH2": (44.0, "c", "alpha-form backbone CH2"),
            "CH":  (26.5, "c", "alpha-form backbone CH"),
            "CH3": (21.8, "c", "alpha-form methyl"),
            "CH2_am": (43.5, "a", "amorphous CH2"),
            "CH_am":  (26.0, "a", "amorphous CH"),
            "CH3_am": (21.0, "a", "amorphous CH3"),
        },
        "sPP": {
            "CH2": (47.2, "c", "backbone CH2"),
            "CH":  (27.8, "c", "backbone CH"),
            "CH3": (20.2, "c", "methyl"),
        },
        "PET": {
            "C=O":     (164.5, "c", "ester carbonyl"),
            "C1_ring": (133.5, "c", "aromatic quaternary"),
            "C2_ring": (129.8, "c", "aromatic CH"),
            "CH2":     (62.8,  "c", "glycol CH2"),
            "C=O_am":  (164.0, "a", "amorphous carbonyl"),
            "CH2_am":  (62.0,  "a", "amorphous glycol"),
        },
        "PA6": {
            "C=O":  (173.5, "c", "amide carbonyl alpha"),
            "C=O_g": (172.5, "c", "amide carbonyl gamma"),
            "Calpha": (43.0, "c", "CH2 adjacent to NH"),
            "Cdelta": (36.5, "c", "CH2 adjacent to CO"),
            "Cbeta":  (30.0, "c", "middle CH2"),
            "Cgamma": (26.5, "c", "middle CH2"),
            "Calpha_am": (42.0, "a", "amorphous Calpha"),
        },
        "PCL": {
            "C=O":  (173.5, "c", "ester carbonyl"),
            "Ca":   (64.0,  "c", "CH2-O"),
            "Ce":   (34.0,  "c", "CH2-CO"),
            "Cb":   (28.3,  "c", "middle CH2"),
            "Cc":   (25.5,  "c", "middle CH2"),
            "Cd":   (24.5,  "c", "middle CH2"),
        },
        "PVDF": {
            "CH2_alpha":  (43.0, "c", "alpha phase CH2"),
            "CF2_alpha":  (120.0, "c", "alpha phase CF2"),
            "CH2_beta":   (42.0, "c", "beta phase CH2"),
            "CF2_beta":   (121.0, "c", "beta phase CF2"),
        },
        "PLLA": {
            "C=O":  (169.5, "c", "ester carbonyl"),
            "CH":   (68.5,  "c", "backbone CH"),
            "CH3":  (16.5,  "c", "methyl"),
            "C=O_am": (169.0, "a", "amorphous carbonyl"),
        },
        "POM": {
            "CH2": (88.5, "c", "oxymethylene"),
        },
        "PTFE": {
            "CF2": (112.0, "c", "fluoromethylene"),
        },
    })

    # --- Sub-module default overrides (applied per active_submodule) ---
    SUBMODULE_DEFAULTS: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "nmr.liquid_h": {
            "sample_state": "liquid", "nucleus": "1H",
            "peak_distance_ppm": 0.08, "deconvolution_method": "lorentzian",
            "peak_height_min": 0.04, "max_peaks": 12,
            "baseline_method": "simple_polynomial",
        },
        "nmr.liquid_c": {
            "sample_state": "liquid", "nucleus": "13C",
            "peak_distance_ppm": 1.0, "deconvolution_method": "lorentzian",
            "peak_height_min": 0.03, "max_peaks": 18,
            "baseline_method": "simple_polynomial",
        },
        "nmr.solid_h": {
            "sample_state": "solid", "nucleus": "1H",
            "peak_distance_ppm": 0.25, "deconvolution_method": "mixed",
            "peak_height_min": 0.04, "max_peaks": 24,
        },
        "nmr.solid_c": {
            "sample_state": "solid", "nucleus": "13C",
            "peak_distance_ppm": 1.0, "deconvolution_method": "mixed",
            "peak_height_min": 0.03, "max_peaks": 18,
        },
    })

    @classmethod
    def load_defaults_json(cls) -> dict:
        """Load NMR-specific defaults from ``config/defaults.json``."""
        path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "config", "defaults.json")
        try:
            with open(os.path.normpath(path), encoding="utf-8") as f:
                data = json.load(f)
            return data.get("nmr", {})
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return {}

    @classmethod
    def with_defaults(cls, **overrides) -> "NMRConfig":
        """Create an NMRConfig with defaults.json as the base, then override."""
        raw = cls.load_defaults_json()
        # map JSON keys to dataclass field names
        field_map = {
            "lb_hz": "lb_Hz",
            "baseline_method": "baseline_method",
            "baseline_order": "baseline_order",
            "fig_format": "fig_format",
            "fig_dpi": "fig_dpi",
        }
        kwargs = {}
        for k, v in raw.items():
            target = field_map.get(k, k)
            if target in cls.__dataclass_fields__:
                kwargs[target] = v
        kwargs.update(overrides)
        return cls(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        for fld in self.__dataclass_fields__:
            if fld == "polymer_13c_db":
                continue
            value = getattr(self, fld)
            if fld == "region_windows_ppm" and isinstance(value, Mapping):
                value = {
                    str(label): [float(bounds[0]), float(bounds[1])]
                    for label, bounds in value.items()
                }
            d[fld] = value
        return d
