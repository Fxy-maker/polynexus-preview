"""
saxs.io - Module 1: Data input.

Uses fabio for multi-format 2D detector image reading,
xarray for multi-dimensional in-situ data management.
"""

import logging
logger = logging.getLogger(__name__)

import os as _os
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import numpy as np
import xarray as xr
import pandas as pd

from .config import SAXSConfig, ExperimentCondition


# ---------------------------------------------------------------------------
#  Image I/O via fabio
# ---------------------------------------------------------------------------

SUPPORTED_2D_EXTENSIONS = {'.edf', '.cbf', '.tif', '.tiff', '.h5', '.hdf5', '.nxs'}
SUPPORTED_1D_EXTENSIONS = {'.dat', '.txt', '.csv', '.xy'}


def read_image(filepath: str) -> Tuple[np.ndarray, dict]:
    """Read a 2D detector image. Returns (image_array, header_dict).

    Uses fabio for .edf/.cbf/.tif; falls back to PIL for .tif if fabio fails.
    """
    path = Path(filepath)
    ext = path.suffix.lower()

    try:
        import fabio
        img = fabio.open(str(path))
        data = img.data.astype(np.float64)
        header = dict(img.header) if hasattr(img, 'header') else {}
        return data, header
    except ImportError:
        pass
    except Exception:
        # fabio failed, try fallbacks
        logger.warning("EDF reader fabio image load failed; trying fallback readers.", exc_info=True)

    # Fallback readers
    if ext in ('.tif', '.tiff'):
        from PIL import Image
        data = np.array(Image.open(filepath), dtype=np.float64)
        return data, {}

    if ext in ('.edf',):
        # Minimal EDF fallback (if fabio unavailable)
        return _read_edf_fallback(filepath)

    raise ValueError(f"Unsupported 2D image format: {ext}")


def read_1d_profile(filepath: str) -> Tuple[np.ndarray, np.ndarray, dict]:
    """Read a 1D scattering profile. Returns (q, I, meta)."""
    path = Path(filepath)
    ext = path.suffix.lower()

    if ext == '.csv':
        df = pd.read_csv(filepath)
        cols = df.columns
        q = df[cols[0]].values.astype(np.float64)
        I = df[cols[1]].values.astype(np.float64)
        return q, I, {}

    # Generic text (dat, txt, xy)
    try:
        data = np.genfromtxt(filepath, comments=['#', '%', '!'])
        if data.ndim == 2 and data.shape[1] >= 2:
            return data[:, 0].astype(np.float64), data[:, 1].astype(np.float64), {}
    except Exception:
        logger.warning("EDF reader generic text profile load failed; trying line-by-line parser.", exc_info=True)

    # Fallback: line-by-line
    x_list, y_list = [], []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line[0] in '#%;!':
                continue
            parts = line.replace(',', ' ').split()
            if len(parts) >= 2:
                try:
                    x_list.append(float(parts[0]))
                    y_list.append(float(parts[1]))
                except ValueError:
                    continue
    if len(x_list) < 2:
        raise ValueError(f"Could not parse 1D data from {filepath}")
    return np.array(x_list), np.array(y_list), {}


def extract_geometry_from_header(header: dict, cfg: SAXSConfig) -> SAXSConfig:
    """Update SAXSConfig geometry from image header.

    Extracts wavelength, pixel size, sample-detector distance, and beam center.
    Returns a (possibly modified) copy of the config.
    """
    import re

    def _get(key_variants, default):
        for k in key_variants:
            k_safe = re.sub(r'[^a-zA-Z0-9_]', '_', k)
            if k_safe in header:
                try:
                    return float(header[k_safe])
                except (ValueError, TypeError):
                    pass
        return default

    # Wavelength: ESRF headers typically store in meters
    wl = _get(['WaveLength', 'Wavelength', 'wavelength', 'Wave_length'], -1)
    if wl > 0:
        if 1e-11 <= wl <= 1e-9:
            cfg.wavelength_m = wl           # already meters (e.g. 1.54e-10)
        elif 0.01 <= wl <= 10:
            cfg.wavelength_m = wl * 1e-10   # Angstrom -> meters
        else:
            cfg.wavelength_m = wl           # assume meters

    # Pixel size (ESRF headers typically store in meters)
    ps = _get(['PixelSize', 'Pixel_size', 'pixel_size', 'PSize_1'], -1)
    if ps > 0:
        if 1e-6 <= ps <= 1e-3:
            cfg.pixel_size_m = ps           # already in meters (e.g. 7.5e-05)
        elif 1 <= ps <= 1000:
            cfg.pixel_size_m = ps * 1e-6    # microns -> meters (e.g. 75)
        elif 0.001 <= ps <= 1:
            cfg.pixel_size_m = ps * 1e-3    # mm -> meters (e.g. 0.075)
        else:
            cfg.pixel_size_m = ps           # assume meters

    # SDD
    sd = _get(['SampleDistance', 'Sample_distance', 'sample_distance', 'Detector_distance'], -1)
    if sd > 0:
        if sd > 10:
            cfg.sdd_m = sd * 1e-3          # mm -> m
        else:
            cfg.sdd_m = sd

    # Beam center
    cx = _get(['Center_1', 'Center_x', 'center_x', 'Beam_xy', 'beam_center_x'], -1)
    cy = _get(['Center_2', 'Center_y', 'center_y', 'Beam_xy', 'beam_center_y'], -1)
    if cx > 0:
        cfg.beam_center_x = cx
    if cy > 0:
        cfg.beam_center_y = cy

    return cfg


# ---------------------------------------------------------------------------
#  Dataset assembly (xarray)
# ---------------------------------------------------------------------------

def scan_experiment_dir(root_dir: str, cfg: SAXSConfig) -> List[ExperimentCondition]:
    """Scan a directory tree for 2D images, group by experiment condition.

    For strain experiments: each subfolder corresponds to a strain value.
    For temperature experiments: files are named with temperature in the filename.
    For static: all files in root_dir.
    """
    conditions: Dict[float, ExperimentCondition] = {}
    root = Path(root_dir)
    exts = SUPPORTED_2D_EXTENSIONS

    for entry in sorted(root.rglob("*")):
        if entry.is_dir() or entry.name.startswith('.') or entry.name.startswith('results'):
            continue
        if entry.suffix.lower() not in exts:
            continue

        # Determine condition value
        value = _parse_condition(entry, cfg)

        if value not in conditions:
            conditions[value] = ExperimentCondition(
                label=f"{cfg.condition_label}={value}{cfg.condition_unit}",
                value=value,
            )
        conditions[value].files.append(str(entry))

    return sorted(conditions.values(), key=lambda c: c.value)


def assemble_dataset(
    conditions: List[ExperimentCondition],
    cfg: SAXSConfig,
    integration_fn=None,
) -> xr.Dataset:
    """Assemble an xarray Dataset from a list of ExperimentConditions.

    For in-situ experiments, the dataset has dimensions (condition, q).
    For static experiments, it's a single profile.

    Parameters
    ----------
    conditions : list of ExperimentCondition
    cfg : SAXSConfig
    integration_fn : callable or None
        If None, images are stored as 2D arrays. If provided, must be
        fn(img, cfg) -> (q, I, I_merid, I_equat).

    Returns
    -------
    xr.Dataset
    """
    condition_values = []
    condition_labels = []
    q_data = None

    all_Iq = {}
    all_Iq_merid = {}
    all_Iq_equat = {}

    for cond in conditions:
        condition_values.append(cond.value)
        condition_labels.append(cond.label)

        # Take the first file for this condition (or average multiple)
        if not cond.files:
            continue

        fpath = cond.files[0]
        img, header = read_image(fpath)

        if integration_fn is not None:
            q, I, I_m, I_e = integration_fn(img, cfg)
            if q_data is None:
                q_data = q
            all_Iq[cond.value] = I
            if I_m is not None:
                all_Iq_merid[cond.value] = I_m
            if I_e is not None:
                all_Iq_equat[cond.value] = I_e
        else:
            # Store raw image; q is just pixel index
            if q_data is None:
                q_data = np.arange(img.shape[1])
            all_Iq[cond.value] = img

    # Build xarray Dataset
    ds = xr.Dataset()

    if len(condition_values) > 1 and integration_fn is not None:
        # In-situ: 2D (condition, q)
        Iq_arr = np.array([all_Iq.get(v, np.full_like(q_data, np.nan))
                           for v in condition_values])
        ds["Iq"] = xr.DataArray(Iq_arr, dims=("condition", "q"),
                                coords={"condition": condition_values, "q": q_data})

        if all_Iq_merid:
            Im_arr = np.array([all_Iq_merid.get(v, np.full_like(q_data, np.nan))
                               for v in condition_values])
            ds["Iq_merid"] = xr.DataArray(Im_arr, dims=("condition", "q"),
                                          coords={"condition": condition_values, "q": q_data})

        if all_Iq_equat:
            Ie_arr = np.array([all_Iq_equat.get(v, np.full_like(q_data, np.nan))
                               for v in condition_values])
            ds["Iq_equat"] = xr.DataArray(Ie_arr, dims=("condition", "q"),
                                          coords={"condition": condition_values, "q": q_data})

        ds.attrs["condition_label"] = cfg.condition_label
        ds.attrs["condition_unit"] = cfg.condition_unit
        ds.attrs["condition_labels"] = condition_labels
    else:
        # Single or static
        Iq_arr = all_Iq.get(condition_values[0], np.array([]))
        if Iq_arr.ndim == 2:
            ds["image"] = xr.DataArray(Iq_arr, dims=("y", "x"))
        else:
            ds["Iq"] = xr.DataArray(Iq_arr, dims=("q",), coords={"q": q_data})

    ds.attrs["experiment_type"] = cfg.experiment_type
    return ds


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _parse_condition(entry: Path, cfg: SAXSConfig) -> float:
    """Extract condition value from file path or name."""
    import re

    if cfg.experiment_type == "strain":
        for part in entry.parts:
            match = re.match(r'^(\d{3})$', part)
            if match:
                code = match.group(1)
                if code in cfg.strain_map:
                    return cfg.strain_map[code]
                return float(code)
        match = re.search(r'(\d{3})', entry.stem)
        if match:
            code = match.group(1)
            return cfg.strain_map.get(code, float(code))

    elif cfg.experiment_type == "temperature":
        # Pattern 1: "PA6-250-170-S_..." -> extract 170
        match = re.search(r'-(\d{2,4})-[A-Z_]', entry.stem)
        if match:
            val = float(match.group(1))
            if 20 < val < 500:
                return val
        # Pattern 2: "sample_T120.edf" or "PA6_25C.edf"
        match = re.search(r'[T_](\d+\.?\d*)\s*C', entry.stem, re.IGNORECASE)
        if match:
            return float(match.group(1))
        # Pattern 3: "_25C"
        match = re.search(r'_(\d+)C', entry.stem)
        if match:
            return float(match.group(1))
        # Pattern 4: any 2-3 digit number that looks like temperature
        match = re.search(r'_(\d{2,3})(?:_[A-Z]|\.)', entry.stem)
        if match:
            val = float(match.group(1))
            if 20 < val < 500:
                return val

    # Generic: use file index
    return 0.0


def _read_edf_fallback(filepath: str) -> Tuple[np.ndarray, dict]:
    """Minimal EDF reader (no fabio dependency)."""
    with open(filepath, 'rb') as f:
        raw = f.read()

    header = {}
    header_end = raw.find(b'}\n')
    if header_end == -1:
        raise ValueError("Invalid EDF: no header terminator")

    header_text = raw[:header_end + 1].decode('latin-1', errors='replace')
    import re
    for line in header_text.split('\n'):
        line = line.strip()
        if '=' in line:
            key, val = line.split('=', 1)
            key = key.strip()
            val = val.strip().rstrip(';')
            header[key] = val

    # Parse dimensions
    dim1 = int(header.get('Dim_1', 0))
    dim2 = int(header.get('Dim_2', 0))
    dtype_str = header.get('DataType', 'UnsignedShort')

    dtype_map = {
        'UnsignedShort': np.uint16, 'UnsignedInteger': np.uint32,
        'SignedInteger': np.int32, 'FloatValue': np.float32,
        'Float': np.float32, 'DoubleValue': np.float64,
    }
    dtype = dtype_map.get(dtype_str, np.uint16)

    data_start = header_end + 2  # skip }\n
    data = np.frombuffer(raw[data_start:], dtype=dtype)
    data = data[:dim1 * dim2].reshape(dim2, dim1).astype(np.float64)

    return data, header
