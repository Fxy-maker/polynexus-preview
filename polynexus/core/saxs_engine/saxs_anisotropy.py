
"""
saxs_anisotropy.py — Module 5: Anisotropy analysis.

Azimuthal intensity profiles, full Herman orientation factor,
2D pattern classification, orientation distribution functions.

Reference: SAXS Design Document v1.0, Module 5.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Tuple
import numpy as np
from scipy.integrate import trapezoid
from scipy.signal import find_peaks

from .config import SAXSConfig
from .saxs_quality_contracts import (
    AnnulusQualityReport,
    DetectorQualityReport,
    QualityLevel,
    SectorMapQualityReport,
    build_annulus_quality_report,
    build_orientation_evidence,
    build_sector_map_quality_report,
)
from .saxs_orientation_reliability import (
    QResolvedOrientationEvidence,
    build_q_resolved_orientation,
)

logger = logging.getLogger(__name__)


def _unavailable_raw_detector_quality() -> DetectorQualityReport:
    return DetectorQualityReport(
        source_kind="raw_detector",
        reason_codes=("raw_detector_quality_unavailable",),
        level=QualityLevel.DIAGNOSTIC,
    )


@dataclass
class AnisotropyResult:
    """Comprehensive anisotropy analysis result."""
    # Herman orientation factors
    f_herman: float = np.nan
    f_herman_raw: float = np.nan
    f_herman_sub: float = np.nan     # sub-tropical (meridional)
    f_herman_eq: float = np.nan      # equatorial
    f_herman_diag: float = np.nan    # diagonal
    
    # Order parameters
    P2: float = np.nan              # <P2(cos(theta))>
    P4: float = np.nan              # <P4(cos(theta))>
    
    # Azimuthal profile analysis
    azimuthal_chi: np.ndarray = None
    azimuthal_I: np.ndarray = None
    azimuthal_q: float = np.nan     # q value used for azimuthal scan
    
    # Peak analysis
    peak_angles_deg: List[float] = None
    peak_intensities: List[float] = None
    peak_fwhm_deg: List[float] = None  # full width at half maximum
    
    # 2D pattern classification
    pattern_type: str = "unknown"    # isotropic | two_point | four_point | 
                                     #   fiber | microfocus | equatorial_streak
    
    # Anisotropy degree
    anisotropy_ratio: float = np.nan  # I_meridian_max/I_equator_max
    anisotropy_index: float = np.nan  # (I_par - I_perp) / (I_par + I_perp)
    
    # Quality
    confidence: float = 0.0

    # Detector-plane reference-axis provenance
    orientation_axis_deg: float = np.nan
    orientation_axis_source: str = "unavailable"
    orientation_axis_strength: float = np.nan
    orientation_axis_confidence: float = 0.0
    orientation_axis_reason: str = ""
    orientation_reliability_status: str = "unavailable"
    orientation_reliability_reason_codes: List[str] = None
    orientation_harmonic_significance: float = np.nan
    orientation_effective_bins: float = np.nan
    orientation_azimuthal_coverage: float = np.nan
    orientation_axis_drift_deg: float = np.nan

    # Explicit physical-axis semantics.  The legacy orientation axis remains a
    # principal-scattering diagnostic; final Herman values require a tensile
    # reference supplied independently of the observed scattering pattern.
    principal_scattering_axis_deg: float = np.nan
    tensile_axis_deg: float = np.nan
    reference_axis_deg: float = np.nan
    reference_axis_kind: str = "unknown"
    orientation_vector_kind: str = "unknown"
    herman_convention: str = "detector_plane_2d_v1"
    isotropic_baseline: float = 0.25
    q_star_candidate: float = np.nan
    selected_q_range_nm1: tuple[float, float] | None = None

    # JSON-safe 2D evidence contracts.  Legacy numeric fields above remain
    # authoritative for backwards-compatible callers.
    detector_quality_report: dict = None
    orientation_evidence: dict = None
    q_resolved_orientation_evidence: QResolvedOrientationEvidence | None = None


def _attach_orientation_evidence(
    result: AnisotropyResult,
    I_2d: np.ndarray,
    *,
    invalid_reason: str | None = None,
    detector_quality: DetectorQualityReport | None = None,
    sector_map_quality: SectorMapQualityReport | None = None,
    annulus_quality: AnnulusQualityReport | None = None,
) -> None:
    """Attach evidence for the sector-map input consumed by this module."""

    detector = detector_quality or _unavailable_raw_detector_quality()
    payload = (
        {}
        if invalid_reason
        else {
            "f_herman": result.f_herman,
            "f_herman_raw": result.f_herman_raw,
            "P2": result.P2,
            "P4": result.P4,
            "pattern_type": result.pattern_type,
            "anisotropy_ratio": result.anisotropy_ratio,
            "anisotropy_index": result.anisotropy_index,
            "confidence": result.confidence,
            "orientation_axis_deg": result.orientation_axis_deg,
            "orientation_axis_source": result.orientation_axis_source,
            "orientation_axis_strength": result.orientation_axis_strength,
            "orientation_axis_confidence": result.orientation_axis_confidence,
            "orientation_axis_reason": result.orientation_axis_reason,
            "orientation_reliability_status": result.orientation_reliability_status,
            "orientation_reliability_reason_codes": (
                result.orientation_reliability_reason_codes or []
            ),
            "orientation_harmonic_significance": result.orientation_harmonic_significance,
            "orientation_effective_bins": result.orientation_effective_bins,
            "orientation_azimuthal_coverage": result.orientation_azimuthal_coverage,
            "orientation_axis_drift_deg": result.orientation_axis_drift_deg,
            "principal_scattering_axis_deg": result.principal_scattering_axis_deg,
            "tensile_axis_deg": result.tensile_axis_deg,
            "reference_axis_deg": result.reference_axis_deg,
            "reference_axis_kind": result.reference_axis_kind,
            "orientation_vector_kind": result.orientation_vector_kind,
            "herman_convention": result.herman_convention,
            "isotropic_baseline": result.isotropic_baseline,
            "q_star_candidate": result.q_star_candidate,
        }
    )
    evidence = build_orientation_evidence(
        payload,
        detector,
        applicability="unknown" if invalid_reason else "supported",
        source_ref="saxs_anisotropy.analyze_anisotropy",
        sector_map_quality=sector_map_quality,
        annulus_quality=annulus_quality,
    )
    result.detector_quality_report = detector.to_dict()
    evidence_dict = evidence.to_dict()
    axis_evidence = evidence_dict.setdefault("fit_evidence", {})
    axis_evidence.update(
        {
            "orientation_axis_deg": (
                float(result.orientation_axis_deg)
                if np.isfinite(result.orientation_axis_deg)
                else None
            ),
            "orientation_axis_source": result.orientation_axis_source,
            "orientation_axis_strength": (
                float(result.orientation_axis_strength)
                if np.isfinite(result.orientation_axis_strength)
                else None
            ),
            "orientation_axis_confidence": float(result.orientation_axis_confidence),
            "orientation_axis_reason": result.orientation_axis_reason or None,
            "orientation_reliability_status": result.orientation_reliability_status,
            "orientation_reliability_reason_codes": (
                result.orientation_reliability_reason_codes or []
            ),
            "feature_kind": "q_star_candidate",
            "q_star_candidate": (
                float(result.q_star_candidate)
                if np.isfinite(result.q_star_candidate)
                else None
            ),
            "selected_q_range_nm1": (
                list(result.selected_q_range_nm1)
                if result.selected_q_range_nm1 is not None
                else None
            ),
            "principal_scattering_axis_deg": (
                float(result.principal_scattering_axis_deg)
                if np.isfinite(result.principal_scattering_axis_deg)
                else None
            ),
            "tensile_axis_deg": (
                float(result.tensile_axis_deg)
                if np.isfinite(result.tensile_axis_deg)
                else None
            ),
            "reference_axis_deg": (
                float(result.reference_axis_deg)
                if np.isfinite(result.reference_axis_deg)
                else None
            ),
            "reference_axis_kind": result.reference_axis_kind,
            "raw_reference_axis_deg": (
                float(result.orientation_axis_deg)
                if np.isfinite(result.orientation_axis_deg)
                else None
            ),
            "raw_reference_axis_kind": (
                "legacy_configured_axis"
                if result.orientation_axis_source == "configured"
                else "legacy_principal_axis"
            ),
            "legacy_reference_axis_deg": (
                float(result.orientation_axis_deg)
                if np.isfinite(result.orientation_axis_deg)
                else None
            ),
            "legacy_reference_axis_kind": (
                "legacy_configured_axis"
                if result.orientation_axis_source == "configured"
                else "legacy_principal_axis"
            ),
            "orientation_vector_kind": result.orientation_vector_kind,
            "herman_convention": result.herman_convention,
            "isotropic_baseline": float(result.isotropic_baseline),
        }
    )
    evidence_reasons = list(evidence_dict.get("reason_codes", ()))
    if result.orientation_axis_reason:
        evidence_reasons.append(result.orientation_axis_reason)
    evidence_reasons.extend(result.orientation_reliability_reason_codes or [])
    if invalid_reason:
        evidence_reasons.append(invalid_reason)
        evidence_dict.setdefault("physical_checks", {})[
            "input_validation_reason"
        ] = invalid_reason
    evidence_dict["reason_codes"] = tuple(dict.fromkeys(evidence_reasons))
    result.orientation_evidence = evidence_dict


def _normalize_anisotropy_inputs(
    I_2d: object,
    q: object,
    chi: object,
    q_1d: object,
    I_1d: object,
) -> tuple[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None, str | None]:
    """Return detached numeric inputs or an explicit structural failure reason."""

    try:
        image = np.asarray(I_2d, dtype=float)
        q_axis = np.asarray(q, dtype=float)
        chi_axis = np.asarray(chi, dtype=float)
        q_1d_axis = np.asarray(q_1d, dtype=float)
        intensity_1d = np.asarray(I_1d, dtype=float)
    except (TypeError, ValueError):
        return None, "orientation_input_invalid"

    if any(array.ndim != 1 for array in (q_axis, chi_axis, q_1d_axis, intensity_1d)):
        return None, "orientation_input_shape_mismatch"
    if image.ndim != 2:
        return None, "orientation_input_shape_mismatch"
    if image.size == 0 or chi_axis.size < 5:
        return None, "orientation_input_shape_mismatch"
    if image.shape != (chi_axis.size, q_axis.size):
        return None, "orientation_input_shape_mismatch"
    if q_1d_axis.size != intensity_1d.size:
        return None, "orientation_input_shape_mismatch"
    if q_1d_axis.size == 0:
        return None, "orientation_input_shape_mismatch"
    if any(not np.all(np.isfinite(array)) for array in (
        image, q_axis, chi_axis, q_1d_axis, intensity_1d
    )):
        return None, "orientation_input_nonfinite"
    return (image, q_axis, chi_axis, q_1d_axis, intensity_1d), None


# ======================================================================
#  Azimuthal profile extraction
# ======================================================================

def extract_azimuthal_profile(
    I_2d: np.ndarray,
    q: np.ndarray,
    chi: np.ndarray,
    q_target: float,
    q_width: float = 0.01,
    support_count: np.ndarray | None = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """Extract azimuthal intensity profile I(chi) at a given q value.

    Parameters
    ----------
    I_2d : np.ndarray, shape (n_chi, n_q)
        2D intensity map from sector integration.
    q : np.ndarray
        q-axis values.
    chi : np.ndarray
        Azimuthal angle axis (radians).
    q_target : float
        Target q value for azimuthal profile.
    q_width : float
        q-range width for averaging around q_target.

    Returns
    -------
    chi_profile, I_profile
    """
    # Find q indices around target
    mask = np.abs(q - q_target) <= q_width
    if np.sum(mask) < 2:
        # Broaden search
        mask = np.abs(q - q_target) <= q_width * 5
    
    if np.sum(mask) < 1:
        return np.array([]), np.array([])

    # Average only measured bins.  Sector support is a source-pixel weight,
    # not an intensity proxy, so unsupported q bins never enter the profile.
    if I_2d.ndim == 2 and support_count is not None:
        try:
            support = np.asarray(support_count, dtype=float)
        except (TypeError, ValueError):
            support = np.asarray([], dtype=float)
        if (
            support.shape != I_2d.shape
            or not np.all(np.isfinite(support))
            or np.any(support < 0)
        ):
            return chi, np.full(chi.shape, np.nan, dtype=float)
        selected_support = support[:, mask]
        valid_weight = selected_support > 0
        denominator = np.sum(
            np.where(valid_weight, selected_support, 0.0), axis=1
        )
        numerator = np.sum(
            np.where(valid_weight, I_2d[:, mask] * selected_support, 0.0),
            axis=1,
        )
        I_profile = np.full(I_2d.shape[0], np.nan, dtype=float)
        supported_rows = denominator > 0
        I_profile[supported_rows] = (
            numerator[supported_rows] / denominator[supported_rows]
        )
    elif I_2d.ndim == 2:
        I_profile = np.mean(I_2d[:, mask], axis=1)
    else:
        I_profile = I_2d

    return chi, I_profile


def extract_azimuthal_at_peaks(
    q: np.ndarray,
    I: np.ndarray,  # noqa: E741  # 1D azimuthally-averaged
    I_2d: np.ndarray,
    chi: np.ndarray,
    min_peaks: int = 1,
    max_peaks: int = 4,
    prominence: float = 0.1,
) -> List[Dict]:
    """Extract azimuthal profiles at all detected Bragg peak positions.

    Returns list of dicts with {'q_peak', 'chi', 'I_chi', 'herman_f'}.
    """
    results = []

    # Find peaks in 1D profile
    Iq2 = I * q**2
    Iq2_norm = (Iq2 - np.min(Iq2)) / (np.max(Iq2) - np.min(Iq2) + 1e-12)
    peaks, props = find_peaks(Iq2_norm, prominence=prominence)

    if len(peaks) < min_peaks:
        # Fallback: use top N maxima
        peak_indices = np.argsort(Iq2)[-max_peaks:]
        peaks = peak_indices[Iq2[peak_indices] > 0]
    
    if len(peaks) > max_peaks:
        # Keep highest intensity peaks
        best = np.argsort(Iq2[peaks])[-max_peaks:]
        peaks = peaks[best]

    for peak_idx in peaks:
        q_peak = q[peak_idx]
        chi_p, I_chi = extract_azimuthal_profile(I_2d, q, chi, q_peak)

        if len(chi_p) < 5:
            continue

        # Herman factor at this q
        herman = herman_from_azimuthal(chi_p, I_chi)

        results.append({
            'q_peak': float(q_peak),
            'chi': chi_p,
            'I_chi': I_chi,
            'herman_f': herman.get('f', np.nan),
            'peak_intensity': float(I_chi.max()) if len(I_chi) > 0 else np.nan,
        })

    return results


# ======================================================================
#  Herman orientation factor (full implementation)
# ======================================================================


def _azimuthal_weights(
    chi: np.ndarray,
    I_chi: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """Return sorted finite azimuths and baseline-subtracted weights."""

    chi_arr = np.asarray(chi, dtype=float)
    intensity = np.asarray(I_chi, dtype=float)
    valid = np.isfinite(chi_arr) & np.isfinite(intensity) & (intensity >= 0)
    if np.sum(valid) < 1:
        return np.array([]), np.array([])

    order = np.argsort(chi_arr[valid])
    chi_arr = chi_arr[valid][order]
    intensity = intensity[valid][order]
    floor = float(np.nanpercentile(intensity, 10))
    weights = np.clip(intensity - floor, 0.0, None)
    if not np.isfinite(np.trapezoid(weights, chi_arr)) or np.sum(weights) <= 1e-12:
        weights = intensity
    return chi_arr, weights


def _axis_difference_deg(first: float, second: float) -> float:
    """Return the smallest difference between two 180-degree axes."""

    return float(abs((float(first) - float(second) + 90.0) % 180.0 - 90.0))


def _harmonic_diagnostics(
    chi: np.ndarray,
    weights: np.ndarray,
) -> Dict[str, float]:
    """Measure second-harmonic strength and sampling stability."""

    if len(chi) < 2 or len(weights) != len(chi):
        return {
            "strength": np.nan,
            "axis_deg": np.nan,
            "effective_bins": 0.0,
            "coverage": 0.0,
            "significance": 0.0,
            "axis_drift_deg": np.nan,
        }

    denominator = float(np.trapezoid(weights, chi))
    weight_sum = float(np.sum(weights))
    weight_square_sum = float(np.sum(np.square(weights)))
    if denominator <= 1e-12 or weight_sum <= 1e-12 or weight_square_sum <= 0:
        return {
            "strength": np.nan,
            "axis_deg": np.nan,
            "effective_bins": 0.0,
            "coverage": 0.0,
            "significance": 0.0,
            "axis_drift_deg": np.nan,
        }

    z2 = np.trapezoid(weights * np.exp(2j * chi), chi) / denominator
    strength = float(np.abs(z2))
    axis_deg = float((np.degrees(0.5 * np.angle(z2)) + 180.0) % 180.0)
    effective_bins = float(weight_sum**2 / weight_square_sum)

    wrapped = np.sort(np.mod(chi, 2.0 * np.pi))
    gaps = np.diff(np.r_[wrapped, wrapped[0] + 2.0 * np.pi])
    coverage = float(np.clip(1.0 - np.max(gaps) / (2.0 * np.pi), 0.0, 1.0))

    split_axes: list[float] = []
    for split in (0, 1):
        split_chi = chi[split::2]
        split_weights = weights[split::2]
        if len(split_chi) < 3:
            continue
        split_denominator = float(np.trapezoid(split_weights, split_chi))
        if split_denominator <= 1e-12:
            continue
        split_z2 = np.trapezoid(
            split_weights * np.exp(2j * split_chi), split_chi
        ) / split_denominator
        if np.isfinite(split_z2.real) and np.isfinite(split_z2.imag):
            split_axes.append(
                float((np.degrees(0.5 * np.angle(split_z2)) + 180.0) % 180.0)
            )
    axis_drift = (
        _axis_difference_deg(split_axes[0], split_axes[1])
        if len(split_axes) == 2
        else np.nan
    )

    return {
        "strength": strength,
        "axis_deg": axis_deg,
        "effective_bins": effective_bins,
        "coverage": coverage,
        "significance": float(strength * np.sqrt(max(effective_bins, 0.0))),
        "axis_drift_deg": float(axis_drift) if np.isfinite(axis_drift) else np.nan,
    }


def detect_in_plane_orientation_axis(
    chi: np.ndarray,
    I_chi: np.ndarray,
    *,
    min_strength: float = 0.08,
    min_bins: int = 12,
    min_significance: float = 2.5,
    min_coverage: float = 0.75,
    min_effective_bins: float = 8.0,
    max_axis_drift_deg: float = 20.0,
) -> Dict:
    """Detect the dominant 180-degree-periodic detector-plane axis.

    The second harmonic is invariant under the detector's 180-degree axis
    ambiguity.  It reports a principal scattering axis only; it does not
    identify a three-dimensional tensile or chain direction.
    """

    result = {
        "axis_deg": np.nan,
        "strength": np.nan,
        "confidence": 0.0,
        "source": "unavailable",
        "reason": "orientation_axis_insufficient_bins",
        "reason_codes": ["orientation_axis_insufficient_bins"],
        "quality_status": "unavailable",
        "effective_bins": 0.0,
        "coverage": 0.0,
        "significance": 0.0,
        "axis_drift_deg": np.nan,
    }
    chi_arr, weights = _azimuthal_weights(chi, I_chi)
    if len(chi_arr) < max(int(min_bins), 5):
        return result

    diagnostics = _harmonic_diagnostics(chi_arr, weights)
    result.update(
        {
            "strength": diagnostics["strength"],
            "effective_bins": diagnostics["effective_bins"],
            "coverage": diagnostics["coverage"],
            "significance": diagnostics["significance"],
            "axis_drift_deg": diagnostics["axis_drift_deg"],
        }
    )
    if not np.isfinite(diagnostics["strength"]):
        result["reason"] = "orientation_axis_zero_weight"
        result["reason_codes"] = [result["reason"]]
        return result

    strength = diagnostics["strength"]
    if strength < float(min_strength):
        result["reason"] = "orientation_axis_low_strength"
        result["reason_codes"] = [result["reason"]]
        return result

    result["axis_deg"] = diagnostics["axis_deg"]
    result["confidence"] = float(np.clip(strength, 0.0, 1.0))
    result["source"] = "auto_detected"
    reasons: list[str] = []
    if diagnostics["effective_bins"] < float(min_effective_bins):
        reasons.append("orientation_effective_bins_insufficient")
    if diagnostics["coverage"] < float(min_coverage):
        reasons.append("orientation_azimuth_coverage_insufficient")
    if diagnostics["significance"] < float(min_significance):
        reasons.append("orientation_harmonic_insignificant")
    if (
        not np.isfinite(diagnostics["axis_drift_deg"])
        or diagnostics["axis_drift_deg"] > float(max_axis_drift_deg)
    ):
        reasons.append("orientation_axis_unstable")
    result["reason_codes"] = reasons
    result["quality_status"] = "blocked" if reasons else "usable"
    result["reason"] = reasons[0] if reasons else ""
    return result

def herman_from_azimuthal(
    chi: np.ndarray,
    I_chi: np.ndarray,
    chi_range: Tuple[float, float] = None,
    reference_axis_deg: float = 0.0,
) -> Dict:
    """Compute Herman orientation factor from azimuthal I(chi) profile.

    f = (3<cos^2(chi)> - 1) / 2

    For lamellar stacks in stretched polymers:
    - f → 1: lamellae perfectly aligned along stretch
    - f → 0.25: uniform random orientation in a 2D detector azimuth
    - f → -0.5: lamellae perpendicular to stretch

    The detector-plane profile is integrated directly over azimuth.  The
    polar-angle ``sin(chi)`` factor is intentionally not applied here because
    ``chi`` is an in-plane detector azimuth, not a 3D polar angle.
    """
    result = {
        'f': np.nan,
        'metric_name': 'projected_order_parameter_2d',
        'convention': 'detector_plane_2d_v1',
        'cos2_avg': np.nan,
        'sin2_avg': np.nan,
        'P2': np.nan,
        'P4': np.nan,
    }

    if len(chi) < 5 or len(I_chi) < 5:
        return result

    # Select chi range
    if chi_range is not None:
        mask = (chi >= chi_range[0]) & (chi <= chi_range[1])
        chi_sel = chi[mask]
        I_sel = I_chi[mask]
    else:
        chi_sel = chi
        I_sel = I_chi

    if len(chi_sel) < 5:
        return result

    chi_sel, weights = _azimuthal_weights(chi_sel, I_sel)
    if len(chi_sel) < 5:
        return result

    phi = np.angle(np.exp(1j * (chi_sel - np.deg2rad(reference_axis_deg))))
    cos2_phi = np.cos(phi) ** 2
    num = trapezoid(weights * cos2_phi, chi_sel)
    den = trapezoid(weights, chi_sel)

    if den <= 0:
        return result

    cos2_avg = num / den
    f = float(np.clip((3 * cos2_avg - 1) / 2, -0.5, 1.0))
    result['cos2_avg'] = float(cos2_avg)
    result['f'] = float(f)

    # P2 order parameter = f
    result['P2'] = float(f)

    # P4: <P4> = (35<cos^4> - 30<cos^2> + 3) / 8
    cos4_phi = np.cos(phi) ** 4
    num4 = trapezoid(weights * cos4_phi, chi_sel)
    cos4_avg = num4 / den if den > 0 else np.nan
    result['P4'] = float((35 * cos4_avg - 30 * cos2_avg + 3) / 8) if np.isfinite(cos4_avg) else np.nan

    return result


def detector_plane_sector_mask(
    chi_rad: np.ndarray,
    *,
    axis_deg: float,
    halfwidth_deg: float,
) -> np.ndarray:
    """Select a pi-periodic detector-plane sector around an axis."""
    chi_array = np.asarray(chi_rad, dtype=float)
    axis_rad = np.deg2rad(float(axis_deg))
    halfwidth_rad = np.deg2rad(abs(float(halfwidth_deg)))
    delta = (chi_array - axis_rad + np.pi / 2.0) % np.pi - np.pi / 2.0
    return np.abs(delta) <= halfwidth_rad


def herman_multi_q(
    q_peaks: List[float],
    I_2d: np.ndarray,
    q: np.ndarray,
    chi: np.ndarray,
) -> Dict:
    """Compute Herman factor at multiple q values and ensemble-average.

    Returns dict with per-q and ensemble results.
    """
    results = {'per_q': {}, 'ensemble_f': np.nan, 'ensemble_std': np.nan}

    f_values = []
    for qp in q_peaks:
        chi_p, I_chi = extract_azimuthal_profile(I_2d, q, chi, qp)
        if len(chi_p) > 5:
            herman = herman_from_azimuthal(chi_p, I_chi)
            f = herman.get('f', np.nan)
            if np.isfinite(f):
                f_values.append(f)
                results['per_q'][float(qp)] = {
                    'f': f, 'P2': herman.get('P2', np.nan),
                }

    if f_values:
        results['ensemble_f'] = float(np.mean(f_values))
        results['ensemble_std'] = float(np.std(f_values))

    return results


# ======================================================================
#  2D pattern classification
# ======================================================================

def classify_2d_pattern(
    chi: np.ndarray,
    I_chi: np.ndarray,
    I_chi_2: np.ndarray = None,  # second azimuthal profile at different q
) -> str:
    """Classify 2D SAXS pattern based on azimuthal intensity profile.

    Pattern types:
    - "isotropic": flat I(chi), no orientation
    - "two_point": two symmetric peaks at chi ~ 0, 180 (meridian)
    - "four_point": four peaks, off-meridian (lamellar rotation)
    - "fiber": strong equatorial streak
    - "microfocus": single central peak with streak
    - "equatorial_streak": intensity concentrated at equator

    Returns pattern type string.
    """
    if len(chi) < 10 or len(I_chi) < 10:
        return "unknown"

    # Normalize
    I_norm = (I_chi - np.min(I_chi)) / (np.max(I_chi) - np.min(I_chi) + 1e-12)
    I_std = np.std(I_norm)

    # Check for peaks
    peaks, props = find_peaks(I_norm, prominence=0.1, distance=3)

    if len(peaks) == 0 or I_std < 0.15:
        return "isotropic"

    # Get peak angles
    peak_angles = chi[peaks]

    if len(peaks) == 2:
        # Check if diametrically opposite (~180 deg apart)
        d_chi = np.abs(np.diff(peak_angles))
        if np.any(np.abs(d_chi - np.pi) < 0.3):
            # Two-point pattern
            # Determine if meridional or equatorial
            chi_center = (peak_angles[0] + peak_angles[1]) / 2
            if np.abs(np.cos(chi_center)) > 0.7:
                return "two_point_meridional"
            else:
                return "two_point_equatorial"
        return "two_point"

    elif len(peaks) == 4:
        return "four_point"

    # Check equatorial concentration
    eq_mask = (np.abs(chi - np.pi/2) < np.pi/6)
    I_eq = np.mean(I_norm[eq_mask])
    I_total = np.mean(I_norm)
    if I_eq > I_total * 1.5:
        return "equatorial_streak"

    if I_std > 0.5:
        return "fiber"

    return "oriented"


def analyze_peak_widths(
    chi: np.ndarray,
    I_chi: np.ndarray,
) -> Dict:
    """Analyze azimuthal peak widths (FWHM) for orientation quantification.

    Narrower peaks = higher orientation.
    Returns azimuthal peak data.
    """
    result = {
        'peaks_found': 0,
        'peak_angles_deg': [],
        'peak_fwhm_deg': [],
        'peak_intensities': [],
        'dominant_orientation_deg': np.nan,
    }

    if len(chi) < 10:
        return result

    I_norm = (I_chi - np.min(I_chi)) / (np.max(I_chi) - np.min(I_chi) + 1e-12)
    peaks, props = find_peaks(I_norm, prominence=0.05, width=2)
    
    if len(peaks) == 0:
        return result

    result['peaks_found'] = len(peaks)

    for pk in peaks:
        angle = float(np.degrees(chi[pk]))
        result['peak_angles_deg'].append(angle)
        result['peak_intensities'].append(float(I_norm[pk]))

        # Estimate FWHM
        half_max = I_norm[pk] / 2
        # Search left
        left = pk
        while left > 0 and I_norm[left] > half_max:
            left -= 1
        # Search right
        right = pk
        while right < len(I_norm) - 1 and I_norm[right] > half_max:
            right += 1
        
        fwhm = np.degrees(chi[right] - chi[left]) if right > left else np.nan
        result['peak_fwhm_deg'].append(float(fwhm) if np.isfinite(fwhm) else None)

    # Dominant orientation: highest intensity peak
    if result['peak_intensities']:
        max_idx = np.argmax(result['peak_intensities'])
        result['dominant_orientation_deg'] = result['peak_angles_deg'][max_idx]

    return result


# ======================================================================
#  Full anisotropy analysis pipeline
# ======================================================================

def _raw_detector_mapping_is_coherent(payload: Mapping[str, Any]) -> bool:
    """Accept only a complete, internally consistent raw-detector inventory."""

    required = (
        "shape",
        "pixel_count",
        "finite_pixel_count",
        "nonfinite_pixel_count",
        "valid_pixel_count",
        "coverage_fraction",
        "source_kind",
    )
    if any(key not in payload for key in required):
        return False
    if str(payload.get("source_kind") or "").strip().lower() != "raw_detector":
        return False

    shape = payload.get("shape")
    if not isinstance(shape, (list, tuple)) or len(shape) != 2:
        return False
    counts = [*shape]
    counts.extend(
        payload.get(key)
        for key in (
            "pixel_count",
            "finite_pixel_count",
            "nonfinite_pixel_count",
            "valid_pixel_count",
        )
    )
    if any(
        isinstance(value, (bool, np.bool_))
        or not isinstance(value, (int, np.integer))
        or value < 0
        for value in counts
    ):
        return False

    pixel_count = int(payload["pixel_count"])
    finite_count = int(payload["finite_pixel_count"])
    nonfinite_count = int(payload["nonfinite_pixel_count"])
    valid_count = int(payload["valid_pixel_count"])
    if (
        int(shape[0]) * int(shape[1]) != pixel_count
        or finite_count + nonfinite_count != pixel_count
        or valid_count > finite_count
        or pixel_count == 0
    ):
        return False

    coverage = payload.get("coverage_fraction")
    if isinstance(coverage, (bool, np.bool_)):
        return False
    try:
        coverage_value = float(coverage)
    except (TypeError, ValueError):
        return False
    return bool(
        np.isfinite(coverage_value)
        and 0.0 <= coverage_value <= 1.0
        and np.isclose(coverage_value, valid_count / pixel_count)
    )


def _normalized_detector_quality(
    raw_detector_quality: DetectorQualityReport | Mapping[str, Any] | None,
) -> DetectorQualityReport:
    """Prefer supplied raw-detector provenance over the derived sector map."""

    if isinstance(raw_detector_quality, DetectorQualityReport):
        payload = raw_detector_quality.to_dict()
        source_kind = str(payload.get("source_kind") or "").strip().lower()
        if (
            source_kind == "raw_detector"
            and raw_detector_quality.level is QualityLevel.UNUSABLE
        ):
            return DetectorQualityReport.from_dict(payload)
        if _raw_detector_mapping_is_coherent(payload):
            return DetectorQualityReport.from_dict(payload)
        return _unavailable_raw_detector_quality()
    if isinstance(raw_detector_quality, Mapping):
        if _raw_detector_mapping_is_coherent(raw_detector_quality):
            return DetectorQualityReport.from_dict(raw_detector_quality)
        source_kind = str(
            raw_detector_quality.get("source_kind") or ""
        ).strip().lower()
        raw_level = raw_detector_quality.get("level")
        if (
            source_kind == "raw_detector"
            and raw_level in {QualityLevel.UNUSABLE, QualityLevel.UNUSABLE.value}
        ):
            return DetectorQualityReport.from_dict(raw_detector_quality)
        return _unavailable_raw_detector_quality()
    return _unavailable_raw_detector_quality()


def _finite_axis_deg(value: Any) -> float:
    try:
        axis = float(value)
    except (TypeError, ValueError):
        return np.nan
    return float(axis % 180.0) if np.isfinite(axis) else np.nan


def analyze_anisotropy(
    I_2d: np.ndarray,
    q: np.ndarray,
    chi: np.ndarray,
    q_1d: np.ndarray,
    I_1d: np.ndarray,
    cfg: Optional[SAXSConfig] = None,
    *,
    support_count: np.ndarray | None = None,
    raw_detector_quality: DetectorQualityReport | Mapping[str, Any] | None = None,
) -> AnisotropyResult:
    """Complete anisotropy analysis of a 2D SAXS pattern.

    Parameters
    ----------
    I_2d : np.ndarray, shape (n_chi, n_q)
        2D intensity from sector integration.
    q : np.ndarray
        q-axis for 2D data.
    chi : np.ndarray
        Azimuthal angles (radians).
    q_1d : np.ndarray
        q-axis for azimuthally-averaged 1D profile.
    I_1d : np.ndarray
        Azimuthally-averaged intensity.
    cfg : SAXSConfig, optional

    Returns
    -------
    AnisotropyResult
    """
    result = AnisotropyResult()
    if cfg is None:
        cfg = SAXSConfig()
    result.tensile_axis_deg = _finite_axis_deg(
        getattr(cfg, "tensile_axis_deg", None)
    )
    if np.isfinite(result.tensile_axis_deg):
        result.reference_axis_deg = result.tensile_axis_deg
        result.reference_axis_kind = "tensile_axis"

    normalized, invalid_reason = _normalize_anisotropy_inputs(
        I_2d, q, chi, q_1d, I_1d
    )
    detector = _normalized_detector_quality(raw_detector_quality)
    sector_quality = build_sector_map_quality_report(I_2d, support_count)
    if invalid_reason:
        result.confidence = 0.0
        _attach_orientation_evidence(
            result,
            I_2d,
            invalid_reason=invalid_reason,
            detector_quality=detector,
            sector_map_quality=sector_quality,
        )
        return result
    I_2d, q, chi, q_1d, I_1d = normalized
    result.q_resolved_orientation_evidence = build_q_resolved_orientation(
        I_2d,
        q,
        chi,
        support_count=support_count,
        cfg=cfg,
        reference_axis_deg=(
            result.tensile_axis_deg
            if np.isfinite(result.tensile_axis_deg)
            else None
        ),
        reference_axis_kind=(
            "tensile_axis" if np.isfinite(result.tensile_axis_deg) else "unknown"
        ),
    )

    # 1. Azimuthal profile at Bragg peak position
    from .core import bragg_long_period
    try:
        _, q_star, _ = bragg_long_period(q_1d, I_1d)
    except Exception:
        q_star = q_1d[np.argmax(I_1d * q_1d**2)]
        logger.warning("SAXS anisotropy Bragg period estimate failed; using maximum Iq2.", exc_info=True)

    q_window = 0.01
    annulus_quality = build_annulus_quality_report(
        support_count,
        q,
        q_target=q_star,
        q_width=q_window,
    )
    try:
        annulus_min_coverage = float(
            getattr(cfg, "orientation_min_coverage", 0.75)
        )
    except (TypeError, ValueError):
        annulus_min_coverage = 0.75
    annulus_support_reason = ""
    if (
        annulus_quality.support_available
        and annulus_quality.support_fraction is not None
        and annulus_quality.support_fraction < annulus_min_coverage
    ):
        annulus_support_reason = "annulus_support_insufficient"
    if np.isfinite(q_star) and q_star > 0:
        result.q_star_candidate = float(q_star)
        selected_q = np.abs(q - q_star) <= q_window
        if int(np.count_nonzero(selected_q)) < 2:
            selected_q = np.abs(q - q_star) <= q_window * 5
        if np.any(selected_q):
            result.selected_q_range_nm1 = (
                float(np.min(q[selected_q])),
                float(np.max(q[selected_q])),
            )

    if np.isfinite(q_star) and q_star > 0:
        chi_prof, I_prof = extract_azimuthal_profile(
            I_2d,
            q,
            chi,
            q_star,
            q_width=q_window,
            support_count=support_count,
        )
        result.azimuthal_chi = chi_prof
        result.azimuthal_I = I_prof
        result.azimuthal_q = float(q_star)

        # 2. Resolve the detector-plane reference axis and Herman factor.
        configured_axis = _finite_axis_deg(
            getattr(cfg, "orientation_axis_deg", None)
        )
        if np.isfinite(configured_axis):
            axis_info = detect_in_plane_orientation_axis(
                chi_prof,
                I_prof,
                min_strength=0.0,
                min_bins=getattr(cfg, "orientation_auto_min_bins", 12),
                min_significance=getattr(cfg, "orientation_auto_min_significance", 2.0),
                min_coverage=getattr(cfg, "orientation_min_coverage", 0.75),
                min_effective_bins=getattr(cfg, "orientation_min_effective_bins", 8.0),
                max_axis_drift_deg=getattr(cfg, "orientation_max_axis_drift_deg", 20.0),
            )
            result.orientation_axis_deg = configured_axis
            result.orientation_axis_source = "configured"
            result.orientation_axis_strength = axis_info.get("strength", np.nan)
            result.orientation_axis_confidence = 1.0
            result.orientation_axis_reason = ""
        else:
            axis_info = detect_in_plane_orientation_axis(
                chi_prof,
                I_prof,
                min_strength=getattr(cfg, "orientation_auto_min_strength", 0.08),
                min_bins=getattr(cfg, "orientation_auto_min_bins", 12),
                min_significance=getattr(cfg, "orientation_auto_min_significance", 2.0),
                min_coverage=getattr(cfg, "orientation_min_coverage", 0.75),
                min_effective_bins=getattr(cfg, "orientation_min_effective_bins", 8.0),
                max_axis_drift_deg=getattr(cfg, "orientation_max_axis_drift_deg", 20.0),
            )
            result.orientation_axis_deg = axis_info.get("axis_deg", np.nan)
            result.orientation_axis_source = axis_info.get("source", "unavailable")
            result.orientation_axis_strength = axis_info.get("strength", np.nan)
            result.orientation_axis_confidence = axis_info.get("confidence", 0.0)
            result.orientation_axis_reason = axis_info.get("reason", "")

        result.orientation_harmonic_significance = axis_info.get("significance", np.nan)
        result.orientation_effective_bins = axis_info.get("effective_bins", np.nan)
        result.orientation_azimuthal_coverage = axis_info.get("coverage", np.nan)
        result.orientation_axis_drift_deg = axis_info.get("axis_drift_deg", np.nan)
        result.principal_scattering_axis_deg = axis_info.get("axis_deg", np.nan)
        reliability_reasons = list(axis_info.get("reason_codes", ()))
        if detector.level is QualityLevel.UNUSABLE:
            reliability_reasons.append("raw_detector_quality_unusable")
        if (
            not annulus_quality.support_available
            or annulus_quality.level is not QualityLevel.TREND
        ):
            reliability_reasons.extend(annulus_quality.reason_codes)
            if not annulus_quality.reason_codes:
                reliability_reasons.append("annulus_support_unusable")
        if annulus_support_reason:
            reliability_reasons.append(annulus_support_reason)
        if not np.isfinite(result.orientation_axis_deg):
            result.orientation_reliability_status = "unavailable"
        elif reliability_reasons:
            result.orientation_reliability_status = "blocked"
        else:
            result.orientation_reliability_status = "usable"

        if np.isfinite(result.orientation_axis_deg):
            raw_herman = herman_from_azimuthal(
                chi_prof,
                I_prof,
                reference_axis_deg=result.orientation_axis_deg,
            )
            result.f_herman_raw = raw_herman.get('f', np.nan)

        if np.isfinite(result.tensile_axis_deg):
            result.reference_axis_deg = result.tensile_axis_deg
            result.reference_axis_kind = "tensile_axis"
        else:
            reliability_reasons.append("tensile_axis_unknown")
            if result.orientation_reliability_status == "usable":
                result.orientation_reliability_status = "unavailable"

        result.orientation_reliability_reason_codes = list(
            dict.fromkeys(reliability_reasons)
        )
        if (
            result.orientation_reliability_status == "usable"
            and np.isfinite(result.reference_axis_deg)
        ):
            tensile_herman = herman_from_azimuthal(
                chi_prof,
                I_prof,
                reference_axis_deg=result.reference_axis_deg,
            )
            result.f_herman = tensile_herman.get('f', np.nan)
            result.P2 = tensile_herman.get('P2', np.nan)
            result.P4 = tensile_herman.get('P4', np.nan)

        # 3. Herman from sector regions
        # Meridional: chi ~ 0
        mer_mask = detector_plane_sector_mask(
            chi_prof, axis_deg=0.0, halfwidth_deg=15.0
        )
        eq_mask = detector_plane_sector_mask(
            chi_prof, axis_deg=90.0, halfwidth_deg=15.0
        )
        result.f_herman_sub = np.nan
        result.f_herman_eq = np.nan

        if np.sum(mer_mask) > 3 and np.isfinite(result.orientation_axis_deg):
            h_mer = herman_from_azimuthal(
                chi_prof[mer_mask],
                I_prof[mer_mask],
                reference_axis_deg=result.orientation_axis_deg,
            )
            result.f_herman_sub = h_mer.get('f', np.nan)
        if np.sum(eq_mask) > 3 and np.isfinite(result.orientation_axis_deg):
            h_eq = herman_from_azimuthal(
                chi_prof[eq_mask],
                I_prof[eq_mask],
                reference_axis_deg=result.orientation_axis_deg,
            )
            result.f_herman_eq = h_eq.get('f', np.nan)

        # 4. Pattern classification
        result.pattern_type = classify_2d_pattern(chi_prof, I_prof)

        # 5. Peak width analysis
        peak_info = analyze_peak_widths(chi_prof, I_prof)
        result.peak_angles_deg = peak_info['peak_angles_deg']
        result.peak_fwhm_deg = peak_info['peak_fwhm_deg']
        result.peak_intensities = peak_info['peak_intensities']

        # 6. Anisotropy metrics
        if len(I_prof) > 0:
            I_max = np.max(I_prof)
            I_min = np.min(I_prof)
            if I_min > 0:
                result.anisotropy_ratio = float(I_max / I_min)

            # Parallel vs perpendicular
            par_mask = detector_plane_sector_mask(
                chi_prof, axis_deg=0.0, halfwidth_deg=30.0
            )
            perp_mask = detector_plane_sector_mask(
                chi_prof, axis_deg=90.0, halfwidth_deg=30.0
            )
            I_par = np.mean(I_prof[par_mask]) if np.sum(par_mask) > 0 else 0
            I_perp = np.mean(I_prof[perp_mask]) if np.sum(perp_mask) > 0 else 0
            if I_par + I_perp > 0:
                result.anisotropy_index = float((I_par - I_perp) / (I_par + I_perp))

    # Confidence estimate
    if np.isfinite(result.f_herman):
        result.confidence = 0.7
        if np.isfinite(result.P4):
            result.confidence += 0.15
        if result.pattern_type != "unknown":
            result.confidence += 0.15

    _attach_orientation_evidence(
        result,
        I_2d,
        detector_quality=detector,
        sector_map_quality=sector_quality,
        annulus_quality=annulus_quality,
    )
    return result
