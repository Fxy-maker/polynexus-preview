"""WAXS orientation analysis.

Computes Herman orientation factors from azimuthal intensity profiles on
2D WAXS images.
"""

import numpy as np
from typing import List


def extract_azimuthal_profile(image, center_x, center_y, radius_px, width_px=5):
    """Extract I(chi) around a WAXS ring.

    Empty azimuth bins are ignored rather than treated as zero intensity; this
    avoids bias when a ring is partly outside the detector.
    """
    ny, nx = image.shape
    y, x = np.indices((ny, nx))
    r = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)

    mask = np.abs(r - radius_px) <= width_px / 2.0
    if not np.any(mask):
        return np.array([]), np.array([])

    chi = np.degrees(np.arctan2(y - center_y, x - center_x))
    chi = np.where(chi < 0, chi + 360.0, chi)

    n_bins = 360
    chi_bins = np.linspace(0, 360, n_bins + 1)
    I_chi = np.full(n_bins, np.nan, dtype=float)
    for i in range(n_bins):
        bin_mask = mask & (chi >= chi_bins[i]) & (chi < chi_bins[i + 1])
        if np.any(bin_mask):
            I_chi[i] = np.nanmean(image[bin_mask])

    chi_center = (chi_bins[:-1] + chi_bins[1:]) / 2.0
    valid = np.isfinite(I_chi) & (I_chi > 0)
    return chi_center[valid], I_chi[valid]


def herman_orientation_factor(chi_deg, I_chi, fiber_axis_deg=90.0):
    """Compute the Herman orientation factor.

    f = (3 <cos^2(phi)> - 1) / 2

    ``phi`` is the azimuth relative to the tensile/fibre axis.  The
    normalization is the azimuthal intensity integral, so <cos^2(phi)> is
    constrained to [0, 1] and f to [-0.5, 1].
    """
    chi = np.asarray(chi_deg, dtype=float)
    intensity = np.asarray(I_chi, dtype=float)
    valid = np.isfinite(chi) & np.isfinite(intensity) & (intensity > 0)
    chi = chi[valid]
    intensity = intensity[valid]
    if len(chi) < 5:
        return np.nan

    order = np.argsort(chi)
    chi = chi[order]
    intensity = intensity[order]

    floor = np.nanpercentile(intensity, 10)
    weights = np.clip(intensity - floor, 0, None)
    if np.nansum(weights) <= 0:
        weights = intensity

    phi = ((chi - fiber_axis_deg + 180.0) % 360.0) - 180.0
    phi_rad = np.radians(phi)
    chi_rad = np.radians(chi)
    cos2 = np.cos(phi_rad) ** 2

    denominator = np.trapezoid(weights, chi_rad)
    if denominator <= 1e-12:
        return np.nan

    cos2_avg = float(np.trapezoid(weights * cos2, chi_rad) / denominator)
    cos2_avg = float(np.clip(cos2_avg, 0.0, 1.0))
    f = (3.0 * cos2_avg - 1.0) / 2.0
    return float(np.clip(f, -0.5, 1.0))


def _two_theta_to_radius_px(two_theta_deg, sample_detector_mm, pixel_size_um):
    """Convert detector 2theta coordinate to ring radius in pixels."""
    return (
        np.tan(np.radians(two_theta_deg))
        * sample_detector_mm * 1000.0
        / pixel_size_um
    )


def herman_from_2d_waxs(image, peaks, center_x, center_y,
                        sample_detector_mm=100.0,
                        pixel_size_um=75.0,
                        fiber_axis_deg=90.0):
    """Compute Herman factor for each fitted WAXS peak."""
    results = []
    for pk in peaks:
        tth = pk.get('two_theta', np.nan)
        if not np.isfinite(tth):
            continue

        radius_px = _two_theta_to_radius_px(
            tth, sample_detector_mm, pixel_size_um)
        if not np.isfinite(radius_px) or radius_px <= 0:
            continue

        fwhm = pk.get('fwhm_deg', 1.0)
        width_px = float(np.clip(radius_px * np.radians(max(fwhm, 0.5)), 6.0, 24.0))
        chi, I_chi = extract_azimuthal_profile(
            image, center_x, center_y, radius_px, width_px=width_px)
        if len(chi) > 10:
            f = herman_orientation_factor(
                chi, I_chi, fiber_axis_deg=fiber_axis_deg)
            results.append({
                'hkl': pk.get('hkl', '') or f"{tth:.1f}",
                'two_theta': tth,
                'f_Herman': float(f),
            })
    return results


def classify_waxs_texture(f_Herman):
    """Classify texture based on Herman factor."""
    if f_Herman > 0.7:
        return "strongly oriented"
    if f_Herman > 0.3:
        return "moderately oriented"
    if f_Herman > -0.3:
        return "random / weakly oriented"
    if f_Herman >= -0.5:
        return "perpendicular orientation"
    return "unknown"
