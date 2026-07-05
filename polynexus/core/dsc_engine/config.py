"""DSC configuration module.

Defines DSCConfig with per-technique parameters and defaults.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class DSCConfig:
    """Configuration for DSC analysis engine.

    Attributes
    ----------
    technique : str
        One of 'static', 'mdsc', 'flash', 'auto'.
    exo_up : bool
        True = exothermic peaks upward (IUPAC convention). Internally all
        data is converted to exo-up before analysis.
    mass_mg : float
        Sample mass in milligrams.  Used for normalisation.
    rate_K_per_min : float
        Heating / cooling rate in K/min.  Positive = heating.
    baseline_corr : str
        Baseline correction method: 'linear', 'polynomial', 'spline',
        'blank_subtract', 'tangential', 'auto'.
    baseline_limits : tuple | None
        (T_start, T_end) for baseline region.  None = auto-detect.
    smooth_method : str
        'savgol', 'moving_average', 'none'.
    smooth_window : int
        Window width for smoothing (must be odd for Savitzky-Golay).
    smooth_order : int
        Polynomial order for Savitzky-Golay.
    Tg_method : str
        'inflection', 'half_height', 'onset', 'fictive'.
    Tm_method : str
        'onset', 'peak', 'end'.
    crystallinity_std : float
        Reference enthalpy of fusion for 100% crystalline polymer, J/g.
        If None, auto-select from database.
    crystallinity_db : Dict[str, float]
        Known reference values (can be extended).
    temperature_calibration : Dict[str, float]
        a, b for T_true = a*T_measured + b.
    enthalpy_calibration : float
        K_calorimetric from indium standard.
    Cp_calibration : Optional[str]
        Path to sapphire calibration file.

    output_dir : str
        Default output directory for figures and reports.
    fig_format : str
        'svg', 'png', 'pdf', 'tiff'.
    fig_dpi : int
        DPI for raster formats.
    """

    # --- Experiment type ---
    technique: str = "static"

    # --- Conventions ---
    exo_up: bool = True

    # --- Sample info ---
    mass_mg: float = 1.0
    rate_K_per_min: float = 10.0

    # --- Preprocessing ---
    baseline_corr: str = "auto"
    baseline_limits: Optional[tuple] = None
    smooth_method: str = "savgol"
    smooth_window: int = 11
    smooth_order: int = 3

    # --- Core analysis ---
    Tg_method: str = "half_height"
    Tg_search_low_C: float = 20.0
    Tg_search_high_C: float = 120.0
    Tm_method: str = "peak"
    peak_function: str = "gaussian"
    Tm_search_low_C: float = 100.0
    Tm_search_high_C: float = 300.0
    Tc_search_low_C: float = 50.0
    Tc_search_high_C: float = 250.0
    crystallinity_std: Optional[float] = None  # None = auto from DB; set to override
    # Alias for GUI clarity
    user_DHm0: Optional[float] = None  # User-specified 100%% crystalline enthalpy (J/g)

    # --- Standard DSC physics engine ---
    auto_segment_program: bool = True
    min_segment_points: int = 40
    min_segment_delta_T: float = 2.0
    peak_prominence_ratio: float = 0.03
    min_event_enthalpy_Jg: float = 0.05
    cold_cryst_max_margin_C: float = 5.0
    edge_event_margin_C: float = 5.0
    max_melting_peak_width_C: float = 50.0

    # --- Isothermal crystallisation kinetics ---
    isothermal_min_duration_min: float = 1.0
    isothermal_temp_tolerance_C: float = 0.35
    isothermal_max_drift_C_per_min: float = 0.12
    isothermal_min_enthalpy_Jg: float = 0.01

    # --- Non-isothermal crystallisation kinetics ---
    nonisothermal_min_delta_T_C: float = 20.0
    nonisothermal_min_points: int = 80
    nonisothermal_min_enthalpy_Jg: float = 0.01

    # --- Calibration ---
    temperature_calibration: Dict[str, float] = field(default_factory=lambda: {"a": 1.0, "b": 0.0})
    enthalpy_calibration: float = 1.0
    Cp_calibration: Optional[str] = None

    # --- Output ---
    output_dir: str = ""
    fig_format: str = "svg"
    fig_dpi: int = 300

    # --- Crystallinity reference database (J/g for 100% crystalline) ---
    crystallinity_db: Dict[str, float] = field(default_factory=lambda: {
        "PE": 293.0,
        "polyethylene": 293.0,
        "HDPE": 293.0,
        "LDPE": 293.0,
        "LLDPE": 293.0,
        "UHMWPE": 293.0,
        "PP": 207.0,
        "polypropylene": 207.0,
        "iPP": 207.0,
        "sPP": 196.0,
        "PET": 140.0,
        "polyethylene terephthalate": 140.0,
        "PBT": 142.0,
        "polybutylene terephthalate": 142.0,
        "PA6": 230.0,
        "nylon6": 230.0,
        "PA66": 255.0,
        "nylon66": 255.0,
        "PA11": 226.0,
        "PA12": 209.0,
        "POM": 326.0,
        "polyoxymethylene": 326.0,
        "PEO": 188.0,
        "polyethylene oxide": 188.0,
        "PCL": 139.0,
        "polycaprolactone": 139.0,
        "PLLA": 93.0,
        "PLA": 93.0,
        "polylactic acid": 93.0,
        "PEEK": 130.0,
        "PPS": 80.0,
        "PTFE": 82.0,
        "PVDF": 104.7,
        "PS": 86.0,  # syndiotactic
        "iPS": 86.0,
        "PMMA": 61.0,
        "PC": 134.0,
        "polycarbonate": 134.0,
        "PEN": 103.0,
        "PAN": 96.0,
    })

    def get_crystallinity_ref(self, polymer_name: str = "") -> float:
        """Return reference enthalpy for the given polymer, or default."""
        # User override takes highest priority
        override = self.user_DHm0 or self.crystallinity_std
        if override is not None:
            return override
        key = polymer_name.strip().lower()
        if key in self.crystallinity_db:
            return self.crystallinity_db[key]
        # fuzzy match (case-insensitive)
        key_lower = key.lower()
        for dbk, v in self.crystallinity_db.items():
            if dbk.lower() in key_lower or key_lower in dbk.lower():
                return v
        return 293.0  # fallback: PE (user should set crystallinity_std for accuracy)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict (excluding large DB for brevity)."""
        d = {}
        for fld in self.__dataclass_fields__:
            if fld == "crystallinity_db":
                continue
            d[fld] = getattr(self, fld)
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DSCConfig":
        """Create from dict."""
        return cls(**{k: v for k, v in d.items()
                      if k in cls.__dataclass_fields__})
