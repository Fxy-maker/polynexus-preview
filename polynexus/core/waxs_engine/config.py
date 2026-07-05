"""WAXS configuration module."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class WAXSConfig:
    """Configuration for WAXS analysis engine.

    Attributes
    ----------
    wavelength_A : float
        X-ray wavelength in Angstrom.  Cu Kα = 1.5406, Mo Kα = 0.7107.
    polarisation_factor : float
        Synchrotron polarisation factor (0-1).  0 = unpolarised lab source.
    peak_function : str
        'gaussian', 'lorentzian', 'pseudo_voigt', 'voigt', 'pearson_vii'.
    background_method : str
        'linear', 'polynomial', 'spline', 'chebyshev'.
    amorphous_subtraction : str
        'manual', 'spline', 'polynomial', 'copy_quenched'.
    crystallinity_method : str
        'peak_area', 'ruland', 'hermans_weidinger'.
    scherrer_K : float
        Scherrer shape factor: 0.9 for spheres, 0.94 for cubes.
    output_dir : str
    fig_format : str
        'svg', 'png', 'pdf'.
    fig_dpi : int
    """

    # --- Instrument ---
    wavelength_A: float = 1.5406  # Cu Kα
    polarisation_factor: float = 0.0  # lab source

    # --- Preprocessing ---
    background_method: str = "linear"
    background_order: int = 1
    smooth_method: str = "savgol"
    smooth_window: int = 5
    smooth_order: int = 3

    # --- Peak fitting ---
    peak_function: str = "pseudo_voigt"
    peak_height_min: float = 0.01  # minimum relative peak height (1% of max — was 2%, needed for PA6 2nd peak)
    peak_distance: float = 0.8
    max_peaks: int = 8               # absolute maximum number of peaks to fit
    min_two_theta: float = 8.0     # ignore 2theta below this for peak detection
    crystallinity_min_two_theta: float = 15.0  # main WAXS window for 2D in-situ crystallinity
    crystallinity_max_two_theta: float = 35.0
    # was: peak_distance=2.0

    # --- Amorphous subtraction ---
    amorphous_subtraction: str = "polynomial"
    amorphous_anchors: Optional[List[float]] = None  # manual anchor 2θ values

    # --- arPLS baseline (pybaselines) ---
    arpls_lam: float = 1e5       # smoothness: 1e4–1e8, higher = flatter baseline (was 1e6 — too aggressive for PA6)
    arpls_diff_order: int = 2    # difference order: 1=stiff, 2=smooth (default)

    # --- Crystallinity ---
    crystallinity_method: str = "peak_deconvolution"
    polymer_type: str = ""   # e.g. "PA6_alpha", "PA66_alpha", "iPP_alpha" — uses known peaks from DB

    # --- Amorphous halo fitting (multi-peak deconvolution) ---
    amorphous_n_peaks: int = 2  # number of broad Gaussians for amorphous halo (1 or 2; 2 recommended for PA6/PET/PP)

    # --- Sector integration (anisotropic samples, e.g. in-situ strain) ---
    do_sector_integration: bool = False   # enable meridional/equatorial sector I(2θ)
    chi_merid_center: float = 90.0        # azimuthal centre of meridional sector (°)
    chi_equat_center: float = 0.0         # azimuthal centre of equatorial sector (°)
    chi_halfwidth: float = 15.0           # half-width of each sector (°)

    fiber_axis_deg: float = 90.0          # tensile/fibre axis azimuth for Herman f
    strain_constrain_crystallinity: bool = True
    strain_xc_from_2d_sum: bool = True

    # --- Crystallite size ---
    scherrer_K: float = 0.9

    # --- Calibration ---
    two_theta_offset: float = 0.0  # instrumental 2θ zero offset
    caglioti_U: float = 0.0
    caglioti_V: float = 0.0
    caglioti_W: float = 0.0

    # --- Output ---
    output_dir: str = ""
    fig_format: str = "svg"
    fig_dpi: int = 300

    # --- Polymer crystal database ---
    # Known diffraction peaks for common polymers
    # Format: {polymer: [(2θ, hkl, I_rel), ...]}
    polymer_peaks_db: Dict[str, List[tuple]] = field(default_factory=lambda: {
        "PE": [
            (21.5, "110", 100), (24.0, "200", 40),
            (30.1, "210", 5), (36.3, "020", 15),
        ],
        "iPP_alpha": [
            (14.1, "110", 100), (16.9, "040", 60),
            (18.6, "130", 40), (21.2, "111", 30),
            (21.9, "131/041", 20),
        ],
        "iPP_beta": [
            (16.0, "300", 100), (21.2, "301", 50),
        ],
        "PET": [
            (16.3, "011", 20), (17.6, "010", 25),
            (22.6, "110", 20), (25.7, "100", 100),
            (27.8, "111", 8), (32.2, "101", 6),
        ],
        "PA6_alpha": [
            (20.0, "200", 100), (24.0, "002/202", 80),
        ],
        "PA6_gamma": [
            (21.5, "001", 100), (11.0, "020", 3),
        ],
        "PA66_alpha": [
            (20.3, "100", 100), (24.0, "010/110", 80),
        ],
        "PEEK": [
            (18.7, "110", 100), (20.6, "111", 50),
            (22.8, "200", 40), (28.8, "211", 25),
        ],
        "PTFE": [
            (18.1, "100", 100), (31.6, "110", 10),
            (36.7, "200", 5),
        ],
        "PVDF_alpha": [
            (17.7, "100", 30), (18.4, "020", 45),
            (20.0, "110", 100), (26.6, "021", 40),
        ],
        "PVDF_beta": [
            (20.6, "110/200", 100),
        ],
        "POM": [
            (23.0, "100", 100), (34.6, "105", 15),
            (48.6, "115", 8),
        ],
        "PCL": [
            (21.4, "110", 100), (22.0, "111", 30),
            (23.8, "200", 60),
        ],
        "PLLA_alpha": [
            (14.8, "010", 30), (16.7, "110/200", 100),
            (19.1, "203", 20), (22.4, "015", 15),
        ],
    })

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        for fld in self.__dataclass_fields__:
            if fld == "polymer_peaks_db":
                continue
            d[fld] = getattr(self, fld)
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WAXSConfig":
        return cls(**{k: v for k, v in d.items()
                      if k in cls.__dataclass_fields__})
