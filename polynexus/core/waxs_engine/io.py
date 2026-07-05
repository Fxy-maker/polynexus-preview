"""WAXS data input module.

Supports: EDF images (synchrotron), 1D profiles (.dat/.txt/.chi),
generic CSV, experiment directories with condition parsing.

Reuses the SAXS engine's EDF reader for 2D image loading.
"""
import logging
logger = logging.getLogger(__name__)


import os
import re
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

from ..saxs_engine.io import (
    read_image,
    read_1d_profile,
    scan_experiment_dir,
    assemble_dataset,
    _parse_condition,
)


# ---------------------------------------------------------------------------
#  Data containers
# ---------------------------------------------------------------------------

@dataclass
class WAXSScan:
    """One WAXS measurement (single frame or integrated 1D)."""
    label: str = ""
    # 1D data (full azimuthal average)
    q_Ainv: np.ndarray = field(default_factory=lambda: np.array([]))
    I_arb: np.ndarray = field(default_factory=lambda: np.array([]))
    two_theta_deg: np.ndarray = field(default_factory=lambda: np.array([]))
    # Sector data (for anisotropic / oriented samples)
    I_merid: Optional[np.ndarray] = None          # meridional sector I(2θ)
    I_equat: Optional[np.ndarray] = None          # equatorial sector I(2θ)
    I_sector_data: Optional[Dict[str, Any]] = None # full sector dict for downstream
    # 2D raw (optional)
    image: Optional[np.ndarray] = None
    # Metadata
    wavelength_A: float = 1.5406
    sample_detector_mm: float = 100.0
    pixel_size_um: float = 75.0
    center_x: float = 0.0
    center_y: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WAXSDataset:
    """Collection of WAXS scans with conditions."""
    scans: List[WAXSScan] = field(default_factory=list)
    conditions: List[Dict[str, Any]] = field(default_factory=list)

    def __len__(self):
        return len(self.scans)


# ---------------------------------------------------------------------------
#  Public API
# ---------------------------------------------------------------------------

def load_scan(filepath: str,
              wavelength_A: float = 1.5406,
              ) -> WAXSScan:
    """Load a single WAXS scan from file."""
    ext = os.path.splitext(filepath)[1].lower()

    if ext in ('.edf', '.edf.gz', '.tif', '.tiff', '.cbf'):
        return _load_edf(filepath, wavelength_A)

    if ext == '.raw':
        return _load_raw(filepath)

    return _load_1d(filepath)


def _load_edf(filepath: str, wavelength_A: float) -> WAXSScan:
    """Load WAXS data from an EDF (or TIFF/CBF) 2D image."""
    from ..saxs_engine.io import read_image

    img, header = read_image(filepath)
    if img is None:
        return WAXSScan()

    scan = WAXSScan(
        label=os.path.splitext(os.path.basename(filepath))[0],
        image=img,
        wavelength_A=wavelength_A,
        metadata=header,
    )

    # Try to extract geometry from header
    from ..saxs_engine.io import extract_geometry_from_header
    from ..saxs_engine.config import SAXSConfig
    try:
        geo_cfg = extract_geometry_from_header(header, SAXSConfig())
        scan.sample_detector_mm = geo_cfg.sdd_m * 1000.0
        scan.pixel_size_um = geo_cfg.pixel_size_m * 1e6
        scan.center_x = geo_cfg.beam_center_x if geo_cfg.beam_center_x > 0 else img.shape[1] / 2
        scan.center_y = geo_cfg.beam_center_y if geo_cfg.beam_center_y > 0 else img.shape[0] / 2

        # Validate SDD — reject values < 30 mm (unphysical for any common WAXS setup).
        # Was < 80 mm, but synchrotron WAXS with EIGER2 can go down to ~50–60 mm.
        if scan.sample_detector_mm < 30:
            scan.sample_detector_mm = 100.0
    except Exception:
        logger.warning("静默异常", exc_info=True)

    # Auto-detect beam center only when header lacks valid values
    if scan.center_x <= 0 or scan.center_y <= 0:
        _auto_beam_center(scan, img)

    return scan


def _auto_beam_center(scan: WAXSScan, img: np.ndarray) -> None:
    """Auto-detect beam center from brightest region (beamstop/direct beam)."""
    try:
        flat = img.ravel()
        thresh = np.percentile(flat, 99)
        bright = img > thresh
        if bright.sum() > 10:
            y_idx, x_idx = np.where(bright)
            scan.center_x = float(np.mean(x_idx))
            scan.center_y = float(np.mean(y_idx))
        else:
            scan.center_x = img.shape[1] / 2
            scan.center_y = img.shape[0] / 2
    except Exception:
        scan.center_x = img.shape[1] / 2
        scan.center_y = img.shape[0] / 2
        logger.warning("异常已处理", exc_info=True)


def _load_1d(filepath: str) -> WAXSScan:
    """Load a 1D WAXS profile from text file."""
    q, I = read_1d_profile(filepath)
    if q is None or len(q) == 0:
        return WAXSScan()

    # Detect if data is in q (Å⁻¹) or 2θ (°)
    # If max < ~15, likely q-space
    is_q_space = np.max(q) < 15.0

    scan = WAXSScan(
        label=os.path.splitext(os.path.basename(filepath))[0],
    )

    if is_q_space:
        scan.q_Ainv = q
        scan.I_arb = I
    else:
        scan.two_theta_deg = q
        scan.I_arb = I

    return scan


def _load_raw(filepath: str) -> WAXSScan:
    """Load a Rigaku .raw binary XRD file."""
    from ...readers.raw_reader import read_raw_rigaku
    two_theta, intensity, meta = read_raw_rigaku(filepath)
    scan = WAXSScan(
        label=os.path.splitext(os.path.basename(filepath))[0],
        two_theta_deg=two_theta,
        I_arb=intensity,
        metadata=meta,
    )
    # Also compute q
    scan = ensure_q(scan)
    return scan


def load_project(filepath: str,
                 wavelength_A: float = 1.5406,
                 ) -> WAXSDataset:
    """Load a WAXS experiment (single file or directory of frames).

    Returns a WAXSDataset with scans and parsed conditions.
    """
    if os.path.isdir(filepath):
        return _load_directory(filepath, wavelength_A)
    else:
        scan = load_scan(filepath, wavelength_A)
        ds = WAXSDataset()
        ds.scans = [scan]
        return ds


def _load_directory(dirpath: str, wavelength_A: float) -> WAXSDataset:
    """Load a directory of WAXS frames.

    Scans for supported image formats (*.edf, *.tif, *.tiff, *.cbf)
    and loads each frame individually.  Falls back to SAXS engine
    directory scanner when available.
    """
    ds = WAXSDataset()

    # Direct scan for supported files (images + 1D profiles)
    supported_exts = {".edf", ".tif", ".tiff", ".cbf", ".raw",
                      ".dat", ".txt", ".csv", ".xlsx", ".chi", ".xy"}
    data_files: List[str] = []
    exclude_dirs = {"polynexus_output", "_test_output", "figures", "data"}
    for root, _dirs, files in os.walk(dirpath):
        _dirs[:] = [d for d in _dirs if d not in exclude_dirs]
        for f in sorted(files):
            ext = os.path.splitext(f)[1].lower()
            if ext in supported_exts:
                data_files.append(os.path.join(root, f))

    if data_files:
        # Load all frames first, auto-detect centers independently,
        # then use the median center for all (beam doesn't move during ramp)
        scans_temp = []
        conditions_temp = []
        centers_x, centers_y, sdds = [], [], []
        for fpath in data_files:
            scan = load_scan(fpath, wavelength_A)
            if scan.label and (len(scan.two_theta_deg) > 0 or scan.image is not None):
                scan.metadata["filepath"] = fpath
                scan.metadata["filename"] = os.path.basename(fpath)
                scans_temp.append(scan)
                conditions_temp.append(_parse_waxs_condition(fpath, dirpath))
                if scan.center_x > 0 and scan.center_y > 0:
                    centers_x.append(scan.center_x)
                    centers_y.append(scan.center_y)
                    sdds.append(scan.sample_detector_mm)

        sortable = [
            (scan, cond) for scan, cond in zip(scans_temp, conditions_temp)
            if cond.get("type") in ("temperature", "strain")
            and np.isfinite(cond.get("value", np.nan))
        ]
        if len(sortable) == len(scans_temp) and len(sortable) > 1:
            sortable.sort(key=lambda item: item[1]["value"])
            scans_temp = [item[0] for item in sortable]
            conditions_temp = [item[1] for item in sortable]

        if centers_x and centers_y:
            shared_cx = float(np.median(centers_x))
            shared_cy = float(np.median(centers_y))
            shared_sdd = float(np.median(sdds)) if sdds else 100.0
        else:
            shared_cx, shared_cy, shared_sdd = None, None, 100.0

        for scan in scans_temp:
            if shared_cx is not None:
                scan.center_x = shared_cx
                scan.center_y = shared_cy
                scan.sample_detector_mm = shared_sdd
            ds.scans.append(scan)
        ds.conditions = conditions_temp
        return ds

    # Fallback: use SAXS engine directory scanner for 1D data
    try:
        raw_dataset = scan_experiment_dir(dirpath)
        if raw_dataset:
            dataset = assemble_dataset(raw_dataset, wavelength_A)
            for entry in dataset:
                scan = WAXSScan(
                    label=entry.get("label", ""),
                    q_Ainv=entry.get("q", np.array([])),
                    I_arb=entry.get("I", np.array([])),
                    two_theta_deg=entry.get("two_theta", np.array([])),
                    image=entry.get("image"),
                    wavelength_A=wavelength_A,
                    metadata=entry.get("metadata", {}),
                )
                ds.scans.append(scan)
                if "condition" in entry:
                    ds.conditions.append(entry["condition"])
    except Exception:
        logger.warning("静默异常", exc_info=True)

    return ds


def _parse_waxs_condition(filepath: str, dirpath: str = "") -> Dict[str, Any]:
    """Parse in-situ condition from a WAXS filename.

    Temperature EDF names from the PA6 test set look like
    ``PA6-250-170-W_0_00002.edf`` and ``PA6-250-W_0_00000.edf``.  The
    condition is the last numeric token before ``-W``; this avoids confusing
    the polymer name ``PA6`` and frame counters with the furnace temperature.
    """
    name = os.path.splitext(os.path.basename(filepath))[0]
    parent = os.path.basename(dirpath or os.path.dirname(filepath)).lower()
    is_temp = any(key in parent for key in ("变温", "temperature", "temp"))
    is_strain = any(key in parent for key in ("拉伸", "strain", "tensile"))

    head = re.split(r"-W(?:_|-|$)", name, maxsplit=1, flags=re.IGNORECASE)[0]
    tokens = re.split(r"[-_\s]+", head)
    numeric_tokens: List[float] = []
    for tok in tokens:
        if re.fullmatch(r"\d+(?:\.\d+)?", tok):
            try:
                numeric_tokens.append(float(tok))
            except ValueError:
                pass

    if not numeric_tokens:
        return {"type": "", "value": np.nan, "unit": "", "label": name}

    value = numeric_tokens[-1]
    if is_temp:
        return {"type": "temperature", "value": value, "unit": "C", "label": f"{value:g}C"}
    if is_strain:
        return {"type": "strain", "value": value, "unit": "%", "label": f"{value:g}%"}
    return {"type": "condition", "value": value, "unit": "", "label": f"{value:g}"}


def q_to_two_theta(q_Ainv: np.ndarray, wavelength_A: float) -> np.ndarray:
    """Convert q (Å⁻¹) to 2θ (degrees).

    2θ = 2 * arcsin(q * λ / 4π)
    """
    theta = np.arcsin(np.clip(q_Ainv * wavelength_A / (4.0 * np.pi), -1.0, 1.0))
    return np.degrees(2.0 * theta)


def two_theta_to_q(two_theta_deg: np.ndarray, wavelength_A: float) -> np.ndarray:
    """Convert 2θ (degrees) to q (Å⁻¹).

    q = 4π * sin(θ) / λ
    """
    theta = np.radians(two_theta_deg / 2.0)
    return 4.0 * np.pi * np.sin(theta) / wavelength_A


def ensure_two_theta(scan: WAXSScan) -> WAXSScan:
    """Ensure scan has two_theta_deg computed from q if needed."""
    if len(scan.two_theta_deg) == 0 and len(scan.q_Ainv) > 0:
        scan.two_theta_deg = q_to_two_theta(scan.q_Ainv, scan.wavelength_A)
    return scan


def ensure_q(scan: WAXSScan) -> WAXSScan:
    """Ensure scan has q_Ainv computed from 2θ if needed."""
    if len(scan.q_Ainv) == 0 and len(scan.two_theta_deg) > 0:
        scan.q_Ainv = two_theta_to_q(scan.two_theta_deg, scan.wavelength_A)
    return scan
