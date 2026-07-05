"""WAXS in-situ strain analysis (W4B).

Strain-dependent WAXS: tracks crystal orientation, polymorph transitions,
stress-induced crystallisation, and lattice strain evolution.

Compliance (per v4.0 scheme):
    L1: lmfit multi-peak fitting   (via core.analyze_scan)
    L2: scipy/numpy + Herman       (via waxs_orientation)
    L3_SELFBUILT: four-phase strain detection, polymorph transition detection
"""

import logging
logger = logging.getLogger(__name__)

import sys
import numpy as np
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional

from .core import analyze_scan, WAXSResult, detect_peaks
# Verify import
if analyze_scan is None:
    raise ImportError("analyze_scan is None!")
from .config import WAXSConfig
from .waxs_orientation import herman_from_2d_waxs


# ======================================================================
#  Phase enum
# ======================================================================

class WAXSStrainPhase(Enum):
    """Four-phase tensile deformation model — WAXS signals."""
    ELASTIC = auto()               # I:   Xc stable, slight orientation
    PLASTIC_REFINEMENT = auto()    # II:  peak broadening, D_hkl drops
    STRESS_INDUCED_CRYST = auto()  # III: Xc rises, new peaks / polymorph change
    FRACTURE_SATURATION = auto()   # IV:  orientation plateau, fit quality drops


# ======================================================================
#  Result dataclasses
# ======================================================================

@dataclass
class WAXSStrainPointResult:
    """Single strain-point WAXS analysis."""
    strain_pct: float = 0.0
    phase: WAXSStrainPhase = WAXSStrainPhase.ELASTIC

    # Core WAXS parameters
    Xc_pct: float = np.nan
    D_Scherrer_nm: float = np.nan
    D_WH_nm: float = np.nan
    epsilon_WH_pct: float = np.nan
    crystal_system: str = ""
    n_peaks: int = 0
    r_squared: float = np.nan

    # Peak details
    peak_positions: List[float] = field(default_factory=list)
    peak_fwhms: List[float] = field(default_factory=list)

    # Herman orientation (per hkl)
    f_Herman_per_peak: Dict[str, float] = field(default_factory=dict)
    f_Herman_avg: float = np.nan

    # Lattice strain Δd/d₀ relative to first frame
    lattice_strain_per_peak: Dict[str, float] = field(default_factory=dict)

    # Full WAXSResult reference
    waxs_result: Optional[WAXSResult] = None


@dataclass
class WAXSStrainSeriesResult:
    """Complete in-situ strain WAXS series."""
    label: str = ""
    strains: List[float] = field(default_factory=list)
    point_results: List[WAXSStrainPointResult] = field(default_factory=list)

    phase_boundaries: Dict[WAXSStrainPhase, float] = field(default_factory=dict)

    # Convenience tracking arrays
    Xc_array: Optional[np.ndarray] = None
    D_array: Optional[np.ndarray] = None
    f_Herman_array: Optional[np.ndarray] = None
    epsilon_WH_array: Optional[np.ndarray] = None

    # Special events
    stress_induced_cryst: bool = False
    polymorph_transition: Optional[str] = None  # e.g. "orthorhombic→monoclinic"

    @property
    def parameters(self) -> Dict:
        return {
            "n_strains": len(self.strains),
            "stress_induced_crystallisation": self.stress_induced_cryst,
            "polymorph_transition": self.polymorph_transition or "none",
        }

    def get_phase_transitions(self) -> Dict:
        return {
            "elastic_to_plastic":
                self.phase_boundaries.get(WAXSStrainPhase.PLASTIC_REFINEMENT, np.nan),
            "plastic_to_cryst":
                self.phase_boundaries.get(WAXSStrainPhase.STRESS_INDUCED_CRYST, np.nan),
            "cryst_to_fracture":
                self.phase_boundaries.get(WAXSStrainPhase.FRACTURE_SATURATION, np.nan),
        }

    def to_dataframe(self):
        """Export as pandas DataFrame for CSV."""
        import pandas as pd

        rows = []
        for sp in self.point_results:
            row = {
                "Strain(%)": sp.strain_pct,
                "Phase": sp.phase.name,
                "Xc(%)": round(sp.Xc_pct, 2) if np.isfinite(sp.Xc_pct) else None,
                "D_Scherrer(nm)": round(sp.D_Scherrer_nm, 2)
                if np.isfinite(sp.D_Scherrer_nm)
                else None,
                "D_WH(nm)": round(sp.D_WH_nm, 2) if np.isfinite(sp.D_WH_nm) else None,
                "epsilon_WH(%)": round(sp.epsilon_WH_pct, 3)
                if np.isfinite(sp.epsilon_WH_pct)
                else None,
                "f_Herman_avg": round(sp.f_Herman_avg, 3)
                if np.isfinite(sp.f_Herman_avg)
                else None,
                "n_peaks": sp.n_peaks,
                "crystal_system": sp.crystal_system,
                "r_squared": round(sp.r_squared, 4)
                if np.isfinite(sp.r_squared)
                else None,
            }
            for hkl, f_val in sp.f_Herman_per_peak.items():
                row[f"f_Herman_{hkl}"] = (
                    round(f_val, 3) if np.isfinite(f_val) else None
                )
            for hkl, ls_val in sp.lattice_strain_per_peak.items():
                row[f"lattice_strain_{hkl}"] = (
                    round(ls_val, 4) if np.isfinite(ls_val) else None
                )
            rows.append(row)
        return pd.DataFrame(rows)


# ======================================================================
#  Phase detection  (L3_SELFBUILT)
# ======================================================================

def detect_strain_phase_waxs(
    strain_pct: float,
    Xc: float,
    Xc_ref: float,
    D: float,
    D_ref: float,
    f_Herman: float,
    fwhm_change_frac: float,
    r_squared: float,
    n_peaks: int,
    n_peaks_ref: int,
) -> WAXSStrainPhase:
    """Auto-detect deformation phase from WAXS parameters.

    L3_SELFBUILT: WAXS-specific four-phase detection.
    Adapted from SAXS phase model but using crystal-scale signals.

    Detection hierarchy (first match wins):

        IV  FRACTURE_SATURATION
            r² < 0.85 after 50% strain, or f_Herman > 0.7 after 100%
        III STRESS_INDUCED_CRYST
            ΔXc > 5% (absolute), or ≥ 2 new peaks
        II  PLASTIC_REFINEMENT
            mean FWHM increase > 15%, or D_hkl drops > 15%
        I   ELASTIC
            fallback
    """
    delta_Xc = Xc - Xc_ref if np.isfinite(Xc) and np.isfinite(Xc_ref) else 0.0
    delta_D = D / D_ref if (
        np.isfinite(D) and np.isfinite(D_ref) and D_ref > 0
    ) else 1.0

    # ── Phase IV: fracture / saturation ──
    if r_squared < 0.85 and strain_pct > 50:
        return WAXSStrainPhase.FRACTURE_SATURATION
    if np.isfinite(f_Herman) and f_Herman > 0.7 and strain_pct > 100:
        return WAXSStrainPhase.FRACTURE_SATURATION

    # ── Phase III: stress-induced crystallisation / polymorph ──
    if delta_Xc > 5.0:
        return WAXSStrainPhase.STRESS_INDUCED_CRYST
    if n_peaks >= n_peaks_ref + 2 and n_peaks_ref > 0:
        return WAXSStrainPhase.STRESS_INDUCED_CRYST

    # ── Phase II: plastic refinement ──
    if fwhm_change_frac > 0.15:
        return WAXSStrainPhase.PLASTIC_REFINEMENT
    if delta_D < 0.85:
        return WAXSStrainPhase.PLASTIC_REFINEMENT

    # ── Phase I: elastic ──
    return WAXSStrainPhase.ELASTIC


# ======================================================================
#  Polymorph transition  (L3_SELFBUILT)
# ======================================================================

def detect_polymorph_transition(crystal_systems: List[str]) -> Optional[str]:
    """Detect crystal-system change across a strain series.

    L3_SELFBUILT: WAXS polymorph-transition detection.

    Returns e.g. ``"orthorhombic→monoclinic"`` or ``None``.
    """
    if len(crystal_systems) < 2:
        return None

    unique: List[str] = []
    for cs in crystal_systems:
        if cs and cs not in unique:
            unique.append(cs)

    if len(unique) >= 2:
        return "\u2192".join(unique)
    return None


# ======================================================================
#  Peak matching helper (by 2θ position, tolerance 1.5°)
# ======================================================================

def _match_peaks_by_position(
    peaks_a: List[Dict],
    peaks_b: List[Dict],
    tol_deg: float = 1.5,
) -> List[tuple]:
    """Match peaks between two frames by 2θ proximity.

    Returns list of (peak_a, peak_b) tuples for matched pairs.
    Unmatched peaks are omitted.
    """
    if not peaks_a or not peaks_b:
        return []

    pos_a = np.array([p.get('two_theta', np.nan) for p in peaks_a])
    pos_b = np.array([p.get('two_theta', np.nan) for p in peaks_b])
    valid_a = np.isfinite(pos_a)
    valid_b = np.isfinite(pos_b)

    if not valid_a.any() or not valid_b.any():
        return []

    matched = []
    used_b = set()
    for i in np.where(valid_a)[0]:
        dists = np.abs(pos_b - pos_a[i])
        dists[list(used_b)] = np.inf  # exclude already-matched peaks
        if len(dists) == 0:
            continue
        j = int(np.argmin(dists))
        if j < len(peaks_b) and dists[j] <= tol_deg and j not in used_b:
            matched.append((peaks_a[i], peaks_b[j]))
            used_b.add(j)

    return matched


# ======================================================================
#  Main analysis entry-point
# ======================================================================

def analyze_strain_series(
    scans: List,
    strains: List[float],
    config: WAXSConfig,
    label: str = "",
) -> WAXSStrainSeriesResult:
    """Analyze a strain-dependent WAXS series.

    L1: lmfit multi-peak fitting   -> ``core.analyze_scan``
    L2: Herman orientation factor  -> ``waxs_orientation.herman_from_2d_waxs``
    L3: phase detection            -> ``detect_strain_phase_waxs``
    """
    result = WAXSStrainSeriesResult(label=label)
    result.strains = list(strains)

    # Reference values from first valid frame
    ref_Xc: float = 0.0
    ref_D: float = 1.0
    ref_n_peaks: int = 0
    ref_d_spacings: Dict[str, float] = {}  # 2θ → d0 (Å), keyed by position
    ref_peaks: List = []  # for position-based matching
    ref_captured: bool = False

    for i, (scan, eps) in enumerate(zip(scans, strains)):

        # -- L1: per-frame WAXS analysis --
        try:
            r: WAXSResult = analyze_scan(scan, config,
                                          label=f"{label}_e{eps:.1f}")
        except Exception as e:
            print(f"[strain] analyze_scan failed for {label}_e{eps:.1f}: {e}", file=sys.stderr)
            r = WAXSResult(label=f"{label}_e{eps:.1f}")
            logger.warning("异常已处理", exc_info=True)
        if r is None:
            r = WAXSResult(label=f"{label}_e{eps:.1f}")

        sp = WAXSStrainPointResult(strain_pct=eps)
        sp.waxs_result = r
        sp.Xc_pct = r.Xc_pct
        sp.D_Scherrer_nm = r.D_Scherrer_nm
        sp.D_WH_nm = r.D_WH_nm
        sp.epsilon_WH_pct = r.epsilon_WH_pct
        sp.crystal_system = r.crystal_system
        sp.n_peaks = r.n_peaks
        sp.r_squared = r.r_squared

        for pk in r.peaks:
            sp.peak_positions.append(pk.get("two_theta", np.nan))
            sp.peak_fwhms.append(pk.get("fwhm_deg", np.nan))

        # -- Capture reference frame (first frame with valid data) --
        if not ref_captured and r.n_peaks > 0:
            ref_Xc = r.Xc_pct if np.isfinite(r.Xc_pct) else 0.0
            ref_D = r.D_Scherrer_nm if np.isfinite(r.D_Scherrer_nm) else 1.0
            ref_n_peaks = r.n_peaks
            ref_peaks = r.peaks
            for pk in r.peaks:
                tth = pk.get("two_theta", np.nan)
                d = pk.get("d_spacing_A", np.nan)
                if np.isfinite(tth):
                    ref_d_spacings[f"{tth:.1f}"] = d
            ref_captured = True

        # -- L2: Herman orientation (needs 2D image) --
        if scan.image is not None and len(r.peaks) > 0:
            try:
                h_results = herman_from_2d_waxs(
                    scan.image, r.peaks,
                    scan.center_x, scan.center_y,
                    sample_detector_mm=scan.sample_detector_mm,
                    pixel_size_um=scan.pixel_size_um,
                    fiber_axis_deg=getattr(config, 'fiber_axis_deg', 90.0),
                )
                f_values: List[float] = []
                for hr in h_results:
                    hkl = hr.get("hkl", "?")
                    f_val = hr.get("f_Herman", np.nan)
                    sp.f_Herman_per_peak[hkl] = float(f_val)
                    if np.isfinite(f_val):
                        f_values.append(float(f_val))
                if f_values:
                    sp.f_Herman_avg = float(np.mean(f_values))
            except Exception:
                logger.warning("静默异常", exc_info=True)

        # -- Lattice strain (position-matched peaks) --
        if i > 0 and ref_d_spacings and r.peaks:
            matched = _match_peaks_by_position(r.peaks, ref_peaks, tol_deg=1.5)
            for pk_curr, pk_ref in matched:
                tth = pk_curr.get("two_theta", np.nan)
                d = pk_curr.get("d_spacing_A", np.nan)
                d0 = pk_ref.get("d_spacing_A", np.nan)
                if np.isfinite(d) and np.isfinite(d0) and d0 > 0:
                    sp.lattice_strain_per_peak[f"{tth:.1f}"] = (d - d0) / d0

        # -- Mean FWHM change (position-matched, relative to previous frame) --
        fwhm_change = 0.0
        if i > 0 and result.point_results:
            prev_peaks = result.point_results[-1].waxs_result
            if prev_peaks is not None and prev_peaks.peaks and r.peaks:
                matched_fwhm = _match_peaks_by_position(
                    r.peaks, prev_peaks.peaks, tol_deg=1.5)
                ratios = []
                for pk_curr, pk_prev in matched_fwhm:
                    pf = pk_prev.get('fwhm_deg', np.nan)
                    cf = pk_curr.get('fwhm_deg', np.nan)
                    if np.isfinite(pf) and np.isfinite(cf) and pf > 0:
                        ratios.append((cf - pf) / pf)
                if ratios:
                    fwhm_change = float(np.mean(ratios))

        # -- L3: phase detection --
        sp.phase = detect_strain_phase_waxs(
            eps, sp.Xc_pct, ref_Xc,
            sp.D_Scherrer_nm, ref_D,
            sp.f_Herman_avg,
            fwhm_change,
            sp.r_squared,
            sp.n_peaks, ref_n_peaks,
        )

        result.point_results.append(sp)

    if getattr(config, 'strain_xc_from_2d_sum', True):
        _apply_2d_sum_crystallinity(result, scans, config)

    # -- Post-series aggregation --
    result.Xc_array = np.array([p.Xc_pct for p in result.point_results])
    result.D_array = np.array([p.D_Scherrer_nm for p in result.point_results])
    result.f_Herman_array = np.array([p.f_Herman_avg for p in result.point_results])
    result.epsilon_WH_array = np.array(
        [p.epsilon_WH_pct for p in result.point_results]
    )

    # Phase boundaries
    _detect_phase_boundaries(result)

    # Stress-induced crystallisation
    Xc_arr = result.Xc_array
    valid = np.isfinite(Xc_arr)
    if valid.sum() >= 2:
        Xc_valid = Xc_arr[valid]
        if Xc_valid[-1] - Xc_valid[0] > 5:
            result.stress_induced_cryst = True

    # Polymorph transition
    crystal_systems = [
        p.crystal_system for p in result.point_results if p.crystal_system
    ]
    result.polymorph_transition = detect_polymorph_transition(crystal_systems)

    return result


# ======================================================================
#  Helpers
# ======================================================================

def _detect_phase_boundaries(result: WAXSStrainSeriesResult) -> None:
    """Record the first strain value where each phase appears."""
    boundaries: Dict[WAXSStrainPhase, float] = {}
    for sp in result.point_results:
        if sp.phase not in boundaries:
            boundaries[sp.phase] = sp.strain_pct
    result.phase_boundaries = boundaries


def _radial_sum_profile(scan, n_bins: int = 1000):
    """Integrate a 2D WAXS image by radial sum for oriented tensile data."""
    if scan.image is None:
        return np.array([]), np.array([])

    ny, nx = scan.image.shape
    y, x = np.indices((ny, nx))
    dx_um = (x - scan.center_x) * scan.pixel_size_um
    dy_um = (y - scan.center_y) * scan.pixel_size_um
    r_um = np.sqrt(dx_um ** 2 + dy_um ** 2)
    tth = np.degrees(np.arctan(r_um / (scan.sample_detector_mm * 1000.0)))
    intensity = scan.image.astype(float)

    valid = np.isfinite(intensity) & (intensity > 0) & (tth > 0)
    tth_flat = tth[valid].ravel()
    I_flat = intensity[valid].ravel()
    if len(tth_flat) < 10:
        return np.array([]), np.array([])

    I_flat = np.clip(I_flat, 0, np.percentile(I_flat, 99.9))
    bins = np.linspace(tth_flat.min(), tth_flat.max(), n_bins + 1)
    digitized = np.digitize(tth_flat, bins)
    I_sum = np.array([
        I_flat[digitized == i].sum() if np.any(digitized == i) else np.nan
        for i in range(1, n_bins + 1)
    ])
    tth_center = (bins[:-1] + bins[1:]) / 2.0
    good = np.isfinite(I_sum)
    return tth_center[good], I_sum[good]


def _estimate_xc_from_2d_sum(scan, config):
    """Estimate Xc from total 2D annular intensity, not radial mean."""
    tth, I = _radial_sum_profile(scan)
    if len(tth) < 20:
        return np.nan

    min_tth = getattr(config, 'crystallinity_min_two_theta', 15.0)
    max_tth = getattr(config, 'crystallinity_max_two_theta', 35.0)
    mask = (tth >= min_tth) & (tth <= max_tth)
    if mask.sum() < 20:
        return np.nan

    x = tth[mask]
    y = I[mask]
    peaks = detect_peaks(
        x, y,
        height_frac=getattr(config, 'peak_height_min', 0.01),
        distance=getattr(config, 'peak_distance', 0.8),
        max_peaks=getattr(config, 'max_peaks', 8),
    )
    centers = [
        p['two_theta'] for p in peaks
        if min_tth <= p['two_theta'] <= max_tth
    ]
    if not centers:
        return np.nan

    try:
        from ..lmfit_wrapper import fit_waxs_profile
        fit_result = fit_waxs_profile(
            x=x, y=y,
            crystal_centers=centers,
            n_halos=1,
            peak_type=getattr(config, 'peak_function', 'pseudo_voigt'),
            halo_range=(float(x[0]), float(x[-1])),
            constraint_centers=centers,
            baseline='none',
        )
    except Exception:
        return np.nan

    components = fit_result.get('components', [])
    crystals = [c for c in components if c.get('is_crystal', True)]
    halos = [c for c in components if not c.get('is_crystal', True)]
    if not crystals or not halos:
        return np.nan

    max_area = max(c.get('area', 0.0) for c in crystals)
    crystals = [c for c in crystals if c.get('area', 0.0) >= max_area * 0.05]
    crystal_area = sum(c.get('area', 0.0) for c in crystals)
    halo_area = sum(h.get('area', 0.0) for h in halos)
    total = crystal_area + halo_area
    if total <= 0:
        return np.nan
    return float(np.clip(crystal_area / total * 100.0, 0.0, 95.0))


def _apply_2d_sum_crystallinity(result: WAXSStrainSeriesResult, scans, config) -> None:
    """Replace tensile Xc with a 2D annular-sum estimate when available.

    Radial means can make oriented high-strain peaks appear to lose area.
    Radial sums preserve the total ring intensity and avoid the 60%+ lock/drop
    artefact without forcing a running maximum plateau.
    """
    for sp, scan in zip(result.point_results, scans):
        xc_2d = _estimate_xc_from_2d_sum(scan, config)
        if not np.isfinite(xc_2d):
            continue
        sp.Xc_pct = xc_2d
        if sp.waxs_result is not None:
            sp.waxs_result.Xc_pct = xc_2d
            sp.waxs_result.Xc_method = "2d_annular_sum_deconvolution"
