"""
saxs.io — Module 1: Data input.

Uses fabio for multi-format 2D detector image reading,
xarray for multi-dimensional in-situ data management.
"""
import logging
import os as _os
from pathlib import Path
from typing import Any, List, Tuple, Optional, Dict, Mapping
import numpy as np
import xarray as xr
import pandas as pd

from .config import SAXSConfig, ExperimentCondition

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
#  Image I/O via fabio
# ---------------------------------------------------------------------------

SUPPORTED_2D_EXTENSIONS = {'.edf', '.cbf', '.tif', '.tiff', '.h5', '.hdf5', '.nxs'}
SUPPORTED_1D_EXTENSIONS = {'.dat', '.txt', '.csv', '.xy'}
SUPPORTED_HDF5_EXTENSIONS = {'.h5', '.hdf5', '.nxs'}


class SAXSIOError(ValueError):
    """Actionable input error for a declared but unreadable dataset."""


class UnsupportedDatasetError(SAXSIOError):
    """Raised when a container has no unambiguous numeric SAXS dataset."""


def read_hdf5_dataset(filepath: str) -> Tuple[np.ndarray, dict]:
    """Read the first unambiguous numeric HDF5/Nexus dataset.

    The reader intentionally does not infer a calibration from arbitrary
    attributes.  It selects a numeric dataset with at least two points and
    reports a typed error when the container is ambiguous or empty.
    """
    try:
        import h5py
    except ImportError as exc:
        raise SAXSIOError("hdf5_reader_unavailable: install h5py") from exc

    candidates: list[tuple[str, np.ndarray]] = []
    try:
        with h5py.File(filepath, "r") as handle:
            def visit(name, node):
                if not hasattr(node, "shape") or not hasattr(node, "dtype"):
                    return
                if not np.issubdtype(node.dtype, np.number):
                    return
                if int(np.prod(node.shape)) < 2 or len(node.shape) > 2:
                    return
                candidates.append((str(name), np.asarray(node[()])))

            handle.visititems(visit)
    except OSError as exc:
        raise SAXSIOError(f"hdf5_open_failed: {exc}") from exc

    if not candidates:
        raise UnsupportedDatasetError(
            "hdf5_dataset_missing: expected a numeric 1D/2D SAXS dataset"
        )
    candidates.sort(key=lambda item: (0 if item[1].ndim == 2 else 1, item[0]))
    dataset_name, data = candidates[0]
    return np.asarray(data, dtype=np.float64), {
        "dataset_path": dataset_name,
        "container_format": "nexus" if Path(filepath).suffix.lower() == ".nxs" else "hdf5",
    }


def normalize_edf_detector_metadata(header: Mapping[str, Any] | None) -> dict[str, Any]:
    """Normalize known EDF detector fields without asserting calibration validity."""
    if not isinstance(header, Mapping):
        return {
            "metadata_status": "missing",
            "metadata_source": "none",
        }

    normalized = {
        str(key).strip().lower().replace("-", "_").replace(" ", "_"): value
        for key, value in header.items()
    }

    def _text(*names: str) -> str | None:
        for name in names:
            value = normalized.get(name.lower().replace("-", "_").replace(" ", "_"))
            if value is not None and str(value).strip():
                return str(value).strip()
        return None

    def _number(*names: str) -> float | None:
        for name in names:
            value = normalized.get(name.lower().replace("-", "_").replace(" ", "_"))
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue
            if np.isfinite(number):
                return float(number)
        return None

    detector_model = _text("detectormodel", "detector_model")
    serial_number = None
    if detector_model:
        import re

        match = re.search(r"(?:s/n|serial(?:_number)?|sn)\s*[:=]?\s*([A-Za-z0-9._-]+)", detector_model, re.I)
        if match:
            serial_number = match.group(1)
    serial_number = serial_number or _text(
        "detectorsn", "detector_serial", "detector_serial_number", "serialnumber"
    )

    values: dict[str, Any] = {
        "detector_model": detector_model,
        "detector_serial_number": serial_number,
        "exposure_time_s": _number("exposuretime", "exposure_time"),
        "threshold_setting": _number("thresholdsetting", "threshold_setting"),
        "count_cutoff": _number("countcutoff", "count_cutoff"),
        "saturation_field": _number("saturation"),
        "flat_field_status": _text("flatfield", "flat_field"),
        "dark_correction_status": _text(
            "dark", "dark_correction", "dark_correction_status"
        ),
        "detector_background_status": _text(
            "detectorbackground", "detector_background", "background_correction_status"
        ),
        "polarization_correction_status": _text(
            "polarizationcorrection", "polarization_correction",
            "polarisationcorrection", "polarisation_correction",
        ),
        "solid_angle_correction_status": _text(
            "solidanglecorrection", "solid_angle_correction"
        ),
        "correction_owner": _text("correctionowner", "correction_owner"),
        "dummy_value": _number("dummy"),
        "dummy_tolerance": _number("ddummy"),
        "background_correction_constant": _number(
            "backgroundcorrectionconstant", "background_correction_constant"
        ),
    }
    values.update(
        {
            "wavelength_m": _number("wavelength", "wave_length"),
            "pixel_size_m": _number("psize_1", "pixelsize", "pixel_size"),
            "sample_distance_m": _number(
                "sampledistance", "sample_distance", "detector_distance"
            ),
            "beam_center_x_px": _number("center_1", "center_x", "beam_center_x"),
            "beam_center_y_px": _number("center_2", "center_y", "beam_center_y"),
        }
    )
    required = (
        "detector_model",
        "detector_serial_number",
        "wavelength_m",
        "pixel_size_m",
        "sample_distance_m",
        "beam_center_x_px",
        "beam_center_y_px",
    )
    values["metadata_status"] = (
        "complete" if all(values.get(key) is not None for key in required) else "partial"
    )
    values["metadata_source"] = "edf_header"
    # Header claims are provenance facts only. They never constitute a
    # reviewed calibration record or authorize a correction backend.
    values["calibration_reviewed"] = False
    values["calibration_review_scope"] = "saxs.detector_calibration"
    return values


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
        logger.warning("SAXS image read via fabio failed; trying fallback readers.", exc_info=True)

    # Fallback readers
    if ext in ('.tif', '.tiff'):
        from PIL import Image
        data = np.array(Image.open(filepath), dtype=np.float64)
        return data, {}

    if ext in ('.edf',):
        # Minimal EDF fallback (if fabio unavailable)
        return _read_edf_fallback(filepath)

    if ext in ('.h5', '.hdf5', '.nxs', '.cbf'):
        data, header = read_hdf5_dataset(filepath) if ext in ('.h5', '.hdf5', '.nxs') else (None, None)
        if ext == '.cbf' and data is None:
            raise SAXSIOError("cbf_reader_unavailable: install fabio")
        return data, header or {}

    raise ValueError(f"Unsupported 2D image format: {ext}")


def read_edf_header(filepath: str) -> dict:
    """Read EDF metadata without forcing the caller to parse pixel data."""
    path = Path(filepath)
    if path.suffix.lower() != '.edf':
        return {}

    try:
        import fabio
        img = fabio.open(str(path))
        return dict(img.header) if hasattr(img, 'header') else {}
    except ImportError:
        pass
    except Exception:
        logger.warning("EDF header read failed", exc_info=True)

    return _read_edf_header_fallback(filepath)


def read_1d_profile(filepath: str) -> Tuple[np.ndarray, np.ndarray, dict]:
    """Read a 1D scattering profile. Returns (q, I, meta)."""
    path = Path(filepath)
    ext = path.suffix.lower()

    if ext == '.csv':
        df = pd.read_csv(filepath)
        cols = df.columns
        q = df[cols[0]].values.astype(np.float64)
        intensity = df[cols[1]].values.astype(np.float64)
        return q, intensity, {}

    # Generic text (dat, txt, xy)
    try:
        data = np.genfromtxt(filepath, comments=['#', '%', '!'])
        if data.ndim == 2 and data.shape[1] >= 2:
            return data[:, 0].astype(np.float64), data[:, 1].astype(np.float64), {}
    except Exception:
        logger.warning("SAXS 1D profile text load failed; trying line-by-line parser.", exc_info=True)

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
    Emits warnings when key parameters are missing (falling back to config defaults).
    Returns a (possibly modified) copy of the config.
    """
    import re
    import warnings

    def _get(key_variants, default):
        for k in key_variants:
            k_safe = re.sub(r'[^a-zA-Z0-9_]', '_', k)
            if k_safe in header:
                try:
                    return float(header[k_safe])
                except (ValueError, TypeError):
                    pass
        return default

    missing = []

    # Wavelength: ESRF headers typically store in meters
    wl = _get(['WaveLength', 'Wavelength', 'wavelength', 'Wave_length'], -1)
    if wl > 0:
        if 1e-11 <= wl <= 1e-9:
            cfg.wavelength_m = wl           # already meters (e.g. 1.54e-10)
        elif 0.01 <= wl <= 10:
            cfg.wavelength_m = wl * 1e-10   # Angstrom -> meters
        else:
            cfg.wavelength_m = wl           # assume meters
    else:
        missing.append("wavelength")

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
    else:
        missing.append("pixel_size")

    # SDD
    sd = _get(['SampleDistance', 'Sample_distance', 'sample_distance', 'Detector_distance'], -1)
    if sd > 0:
        if sd > 10:
            cfg.sdd_m = sd * 1e-3          # mm -> m
        else:
            cfg.sdd_m = sd
    else:
        missing.append("sample-detector distance (SDD)")

    # Beam center
    cx = _get(['Center_1', 'Center_x', 'center_x', 'Beam_xy', 'beam_center_x'], -1)
    cy = _get(['Center_2', 'Center_y', 'center_y', 'Beam_xy', 'beam_center_y'], -1)
    if cx > 0:
        cfg.beam_center_x = cx
    if cy > 0:
        cfg.beam_center_y = cy
    if cx <= 0 and cy <= 0:
        missing.append("beam center")

    if missing:
        warnings.warn(
            f"SAXS geometry not found in EDF header ({', '.join(missing)}). "
            f"Using config defaults which may not match the instrument."
        )

    return cfg


# ---------------------------------------------------------------------------
#  Dataset assembly (xarray)
# ---------------------------------------------------------------------------

def scan_experiment_dir(root_dir: str, cfg: SAXSConfig) -> List[ExperimentCondition]:
    """Scan a directory tree for 2D images, group by experiment condition.

    The grouping key is recovered from explicit context, EDF header metadata,
    directory / filename signals, and only falls back to an unresolved bucket
    if the condition axis cannot be determined.
    """
    conditions: Dict[Any, ExperimentCondition] = {}
    root = Path(root_dir)
    exts = SUPPORTED_2D_EXTENSIONS | SUPPORTED_1D_EXTENSIONS

    entries: list[Path] = []
    for dirpath, dirnames, filenames in _os.walk(root):
        dirnames[:] = sorted(
            name
            for name in dirnames
            if not name.startswith('.')
            and name.lower() != "polynexus_output"
            and not name.startswith('results')
        )
        for filename in filenames:
            if filename.startswith('.') or filename.startswith('results'):
                continue
            entry = Path(dirpath) / filename
            if entry.suffix.lower() in exts:
                entries.append(entry)

    for entry in sorted(entries):

        header = {}
        if entry.suffix.lower() == ".edf":
            try:
                header = read_edf_header(str(entry))
            except Exception:
                logger.debug("EDF header read failed for %s", entry, exc_info=True)

        recovered = recover_condition_axis(entry, cfg, header=header)
        key = recovered["condition_key"]
        value = recovered["value"]

        if key not in conditions:
            conditions[key] = ExperimentCondition(
                label=recovered["label"],
                value=value,
                condition_key=key,
                metadata={
                    "condition_source": recovered["source"],
                    "condition_source_key": recovered["source_key"],
                    "condition_source_text": recovered["source_text"],
                    "condition_confidence": recovered["confidence"],
                },
                param_type=cfg.experiment_type,
            )
        conditions[key].files.append(str(entry))

    return sorted(
        conditions.values(),
        key=lambda c: (
            0 if np.isfinite(c.value) else 1,
            float(c.value) if np.isfinite(c.value) else str(c.condition_key if c.condition_key is not None else c.label),
        ),
    )


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
            q, intensity, intensity_meridional, intensity_equatorial = integration_fn(img, cfg)
            if q_data is None:
                q_data = q
            cond_key = cond.condition_key if cond.condition_key is not None else (
                cond.value if np.isfinite(cond.value) else f"condition::{len(all_Iq)}"
            )
            all_Iq[cond_key] = intensity
            if intensity_meridional is not None:
                all_Iq_merid[cond_key] = intensity_meridional
            if intensity_equatorial is not None:
                all_Iq_equat[cond_key] = intensity_equatorial
        else:
            # Store raw image; q is just pixel index
            if q_data is None:
                q_data = np.arange(img.shape[1])
            cond_key = cond.condition_key if cond.condition_key is not None else (
                cond.value if np.isfinite(cond.value) else f"condition::{len(all_Iq)}"
            )
            all_Iq[cond_key] = img

    # Build xarray Dataset
    ds = xr.Dataset()

    if len(condition_values) > 1 and integration_fn is not None:
        # In-situ: 2D (condition, q)
        Iq_arr = np.array([
            all_Iq.get(
                cond.condition_key if cond.condition_key is not None else (
                    cond.value if np.isfinite(cond.value) else f"condition::{idx}"
                ),
                np.full_like(q_data, np.nan),
            )
            for idx, cond in enumerate(conditions)
        ])
        ds["Iq"] = xr.DataArray(Iq_arr, dims=("condition", "q"),
                                coords={"condition": condition_values, "q": q_data})

        if all_Iq_merid:
            Im_arr = np.array([
                all_Iq_merid.get(
                    cond.condition_key if cond.condition_key is not None else (
                        cond.value if np.isfinite(cond.value) else f"condition::{idx}"
                    ),
                    np.full_like(q_data, np.nan),
                )
                for idx, cond in enumerate(conditions)
            ])
            ds["Iq_merid"] = xr.DataArray(Im_arr, dims=("condition", "q"),
                                          coords={"condition": condition_values, "q": q_data})

        if all_Iq_equat:
            Ie_arr = np.array([
                all_Iq_equat.get(
                    cond.condition_key if cond.condition_key is not None else (
                        cond.value if np.isfinite(cond.value) else f"condition::{idx}"
                    ),
                    np.full_like(q_data, np.nan),
                )
                for idx, cond in enumerate(conditions)
            ])
            ds["Iq_equat"] = xr.DataArray(Ie_arr, dims=("condition", "q"),
                                          coords={"condition": condition_values, "q": q_data})

        ds.attrs["condition_label"] = cfg.condition_label
        ds.attrs["condition_unit"] = cfg.condition_unit
        ds.attrs["condition_labels"] = condition_labels
    else:
        # Single or static
        first_cond = conditions[0]
        first_key = first_cond.condition_key if first_cond.condition_key is not None else (
            first_cond.value if np.isfinite(first_cond.value) else "condition::0"
        )
        Iq_arr = all_Iq.get(first_key, np.array([]))
        if Iq_arr.ndim == 2:
            ds["image"] = xr.DataArray(Iq_arr, dims=("y", "x"))
        else:
            ds["Iq"] = xr.DataArray(Iq_arr, dims=("q",), coords={"q": q_data})

    ds.attrs["experiment_type"] = cfg.experiment_type
    return ds


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _parse_condition(entry: Path, cfg: "SAXSConfig") -> float:
    """Extract experimental condition value from a file path.

    Iterates over ``cfg.condition_patterns`` in order.  The first pattern
    whose regex matches and (optionally) passes validation wins.

    Returns
    -------
    float
        The extracted value, or ``float('nan')`` if no pattern matched.
        (Previously returned 0.0, which silently corrupted data.)

    Notes
    -----
    When ``cfg.warn_on_parse_failure`` is True (default), a warning is
    logged for unrecognised filenames so the user can add custom patterns.
    """
    import re
    import warnings
    import logging

    _log = logging.getLogger("polynexus.saxs.io")

    patterns = cfg.condition_patterns
    if not patterns:
        # No patterns configured — fall back to old hardcoded behaviour
        # for strain_map / temperature_map compatibility
        return _parse_condition_legacy(entry, cfg)

    # ---- Filter patterns by experiment type ----
    # Patterns whose name starts with "strain_" are only tried for
    # experiment_type="strain"; "temp_" for "temperature"; others always.
    exp_type = cfg.experiment_type

    for p in patterns:
        # ---- Skip if pattern doesn't match experiment type ----
        if p.name.startswith("strain_") and exp_type != "strain":
            continue
        if p.name.startswith("temp_") and exp_type != "temperature":
            continue

        # ---- Search ----
        regex = p.regex

        if p.search_path:
            # Search each path component individually
            match = None
            for part in entry.parts:
                match = re.search(regex, part, re.IGNORECASE)
                if match:
                    break
        else:
            match = re.search(regex, entry.stem, re.IGNORECASE)
        if not match:
            continue

        captured = match.group(1)

        # ---- Lookup map ----
        if p.lookup_map:
            lookup = getattr(cfg, p.lookup_map, {})
            if captured in lookup:
                value = lookup[captured]
            else:
                try:
                    value = float(captured) if p.value_transform == "float" else int(captured)
                except ValueError:
                    continue
        else:
            try:
                value = float(captured) if p.value_transform == "float" else int(captured)
            except ValueError:
                _log.debug("Pattern %r matched but cannot convert %r", p.name, captured)
                continue

        # ---- Validation ----
        if p.validator_expr:
            try:
                x = value
                if not eval(p.validator_expr, {"x": x, "__builtins__": {}}):
                    _log.debug(
                        "Pattern %r matched (%s=%s) but failed validation %r",
                        p.name, captured, value, p.validator_expr,
                    )
                    continue
            except Exception:
                _log.debug("Validator eval error for pattern %r", p.name)
                continue

        _log.debug("Condition extracted: %s=%s %s (pattern %r)",
                    cfg.condition_label, value, cfg.condition_unit, p.name)
        return float(value)

    # ---- No pattern matched ----
    if cfg.warn_on_parse_failure:
        msg = (
            f"No condition pattern matched file: {entry.name!r}. "
            f"Add a pattern to SAXSConfig.condition_patterns or "
            f"set warn_on_parse_failure=False to suppress this warning."
        )
        warnings.warn(msg, UserWarning, stacklevel=2)
        _log.warning(msg)

    return float('nan')


def _parse_condition_legacy(entry: Path, cfg: "SAXSConfig") -> float:
    """Fallback: original hardcoded logic for backward compatibility.

    Used only when ``cfg.condition_patterns`` is empty.
    """
    import re

    if cfg.experiment_type == "strain":
        for part in entry.parts:
            match = re.match(r'^(\d{3})$', part)
            if match:
                code = match.group(1)
                return cfg.strain_map.get(code, float(code))
        match = re.search(r'-(\d+)-[Ss]_', entry.stem)
        if match:
            code = match.group(1)
            return cfg.strain_map.get(code, float(code))
        match = re.search(r'(\d{3})', entry.stem)
        if match:
            code = match.group(1)
            return cfg.strain_map.get(code, float(code))

    elif cfg.experiment_type == "temperature":
        match = re.search(r'-(\d{2,4})-[A-Z_]', entry.stem)
        if match:
            val = float(match.group(1))
            if 20 < val < 500:
                return val
        match = re.search(r'[Tt]_(\d+\.?\d*)\s*C', entry.stem)
        if match:
            return float(match.group(1))
        match = re.search(r'_(\d+)C', entry.stem)
        if match:
            return float(match.group(1))
        match = re.search(r'_(\d{2,3})(?:_[A-Z]|\.)', entry.stem)
        if match:
            val = float(match.group(1))
            if 20 < val < 500:
                return val

    return float('nan')


def _parse_condition_detail(entry: Path, cfg: "SAXSConfig") -> dict[str, Any]:
    """Extract condition value from a file path together with source provenance."""
    import re

    patterns = cfg.condition_patterns
    if not patterns:
        legacy_value = _parse_condition_legacy(entry, cfg)
        if np.isfinite(legacy_value):
            return {
                "value": float(legacy_value),
                "source": "path_legacy",
                "source_key": entry.name,
                "source_text": entry.name,
                "confidence": 0.55,
            }
        return {
            "value": float("nan"),
            "source": "unresolved",
            "source_key": "",
            "source_text": entry.name,
            "confidence": 0.0,
        }

    exp_type = cfg.experiment_type
    for pattern in patterns:
        if pattern.name.startswith("strain_") and exp_type != "strain":
            continue
        if pattern.name.startswith("temp_") and exp_type != "temperature":
            continue

        regex = pattern.regex
        path_parts = entry.parts if pattern.search_path else (entry.stem,)
        for part in path_parts:
            match = re.search(regex, part, re.IGNORECASE)
            if not match:
                continue

            captured = match.group(1)
            if pattern.lookup_map:
                lookup = getattr(cfg, pattern.lookup_map, {})
                if captured in lookup:
                    value = lookup[captured]
                else:
                    try:
                        value = float(captured) if pattern.value_transform == "float" else int(captured)
                    except ValueError:
                        continue
            else:
                try:
                    value = float(captured) if pattern.value_transform == "float" else int(captured)
                except ValueError:
                    continue

            if pattern.validator_expr:
                try:
                    x = value
                    if not eval(pattern.validator_expr, {"x": x, "__builtins__": {}}):
                        continue
                except Exception:
                    continue

            return {
                "value": float(value),
                "source": "path_directory" if pattern.search_path else "path_filename",
                "source_key": pattern.name,
                "source_text": entry.name,
                "confidence": 0.72 if pattern.search_path else 0.64,
            }

    return {
        "value": float("nan"),
        "source": "unresolved",
        "source_key": "",
        "source_text": entry.name,
        "confidence": 0.0,
    }


def recover_condition_axis(
    entry: Path | str,
    cfg: SAXSConfig,
    header: Optional[dict] = None,
    context: Optional[dict] = None,
) -> Dict[str, Any]:
    """Recover the experimental condition axis from context, header, or path."""
    entry = Path(entry)
    context = context if isinstance(context, dict) else getattr(cfg, "condition_context", {})
    if not isinstance(context, dict):
        context = {}
    header = header if isinstance(header, dict) else {}

    kind = _infer_condition_kind(cfg, context=context, header=header)

    for source_name, source in (("context", context), ("header", header)):
        value, source_key, source_text = _extract_condition_from_mapping(source, kind)
        if np.isfinite(value):
            return {
                "value": float(value),
                "source": source_name,
                "source_key": source_key,
                "source_text": source_text,
                "confidence": 0.95 if source_name == "context" else 0.9,
                "label": _format_condition_label(value, cfg, source_text=source_text),
                "condition_key": float(value),
            }

    parsed = _parse_condition_detail(entry, cfg)
    value = float(parsed.get("value", float("nan")))
    if np.isfinite(value):
        return {
            "value": float(value),
            "source": str(parsed.get("source", "path") or "path"),
            "source_key": str(parsed.get("source_key", "") or entry.name),
            "source_text": str(parsed.get("source_text", "") or entry.name),
            "confidence": float(parsed.get("confidence", 0.6) or 0.6),
            "label": _format_condition_label(value, cfg, source_text=str(parsed.get("source_text", "") or entry.name)),
            "condition_key": float(value),
        }

    unresolved_key = f"unresolved::{entry.as_posix()}"
    return {
        "value": float("nan"),
        "source": "unresolved",
        "source_key": "",
        "source_text": entry.name,
        "confidence": 0.0,
        "label": _format_condition_label(np.nan, cfg, source_text=entry.name),
        "condition_key": unresolved_key,
    }


def _normalize_condition_key(key: Any) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "_", str(key).strip().lower()).strip("_")


def _coerce_condition_float(value: Any) -> float:
    if value is None:
        return float("nan")
    if isinstance(value, np.ndarray):
        if value.size == 0:
            return float("nan")
        return _coerce_condition_float(value.flat[0])
    if isinstance(value, (list, tuple)):
        if not value:
            return float("nan")
        return _coerce_condition_float(value[0])
    try:
        if isinstance(value, (np.floating, float, int, np.integer)):
            numeric = float(value)
            return numeric if np.isfinite(numeric) else float("nan")
    except Exception:
        pass
    text = str(value).strip()
    if not text:
        return float("nan")
    try:
        numeric = float(text)
        return numeric if np.isfinite(numeric) else float("nan")
    except Exception:
        import re

        match = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", text)
        if match:
            try:
                numeric = float(match.group(0))
                return numeric if np.isfinite(numeric) else float("nan")
            except Exception:
                return float("nan")
    return float("nan")


def _infer_condition_kind(cfg: SAXSConfig, *, context: Optional[dict] = None, header: Optional[dict] = None) -> str:
    parts: list[str] = [
        str(getattr(cfg, "experiment_type", "") or ""),
        str(getattr(cfg, "condition_label", "") or ""),
        str(getattr(cfg, "condition_unit", "") or ""),
    ]
    for blob in (context, header):
        if isinstance(blob, dict):
            for key, value in blob.items():
                parts.append(str(key))
                if isinstance(value, (str, int, float, np.integer, np.floating)):
                    parts.append(str(value))
    haystack = " ".join(parts).lower()
    if any(token in haystack for token in ("temperature", "temp", "thermal", "melt")):
        return "temperature"
    if any(token in haystack for token in ("strain", "epsilon", "stretch", "tensile")):
        return "strain"
    return "generic"


def _condition_candidate_keys(kind: str) -> tuple[str, ...]:
    kind = str(kind or "").strip().lower()
    if kind == "temperature":
        return (
            "temperature_c",
            "temperature",
            "temp_c",
            "temp",
            "stage_temperature",
            "sample_temperature",
            "heater_temperature",
            "setpoint_temperature",
            "condition_value",
            "condition",
            "value",
        )
    if kind == "strain":
        return (
            "strain_pct",
            "strain",
            "epsilon",
            "deformation",
            "extension_pct",
            "extension",
            "condition_value",
            "condition",
            "value",
        )
    return (
        "condition_value",
        "condition",
        "value",
        "temperature_c",
        "temperature",
        "temp_c",
        "temp",
        "strain_pct",
        "strain",
        "epsilon",
    )


def _lookup_condition_value(source: dict, kind: str) -> tuple[float, str, str]:
    if not isinstance(source, dict) or not source:
        return float("nan"), "", ""

    normalized = {
        _normalize_condition_key(key): value
        for key, value in source.items()
    }
    candidates = _condition_candidate_keys(kind)
    for key in candidates:
        if key not in normalized:
            continue
        value = _coerce_condition_float(normalized[key])
        if not np.isfinite(value):
            continue
        if kind == "temperature" and not (-150.0 <= value <= 800.0):
            continue
        if kind == "strain" and not (-50.0 <= value <= 2000.0):
            continue
        return float(value), key, f"{key}={value:g}"
    return float("nan"), "", ""


def _extract_condition_from_mapping(source: Optional[dict], kind: str) -> tuple[float, str, str]:
    if not isinstance(source, dict) or not source:
        return float("nan"), "", ""

    nested_keys = ("condition_values", "batch", "import_record", "import_context", "analysis_context", "metadata", "sample", "series", "context")
    for nested_key in nested_keys:
        nested = source.get(nested_key)
        if isinstance(nested, dict) and nested:
            value, key, text = _lookup_condition_value(nested, kind)
            if np.isfinite(value):
                return value, key, text

    return _lookup_condition_value(source, kind)


def _format_condition_label(value: float, cfg: SAXSConfig, *, source_text: str = "") -> str:
    label = str(getattr(cfg, "condition_label", "") or "Condition").strip() or "Condition"
    unit = str(getattr(cfg, "condition_unit", "") or "").strip()
    if np.isfinite(value):
        suffix = f"{float(value):g}{unit}" if unit else f"{float(value):g}"
        return f"{label}={suffix}"
    if source_text:
        return f"{label}=unresolved ({source_text})"
    return f"{label}=unresolved"

def _read_edf_fallback(filepath: str) -> Tuple[np.ndarray, dict]:
    """Minimal EDF reader (no fabio dependency).

    EDF format: ASCII header delimited by ``{`` … ``}``, followed by binary
    data.  The closing brace may be followed by ``\\n``, ``\\r\\n``, or
    nothing.  This reader handles byte-order via the ``ByteOrder`` header key
    and supports all common pixel data types.
    """
    with open(filepath, 'rb') as f:
        raw = f.read()

    # ------------------------------------------------------------------
    #  Robust header terminator: find the closing '}' then skip any
    #  whitespace that follows it to locate the binary data start.
    # ------------------------------------------------------------------
    header = {}

    # Search for the brace pair: EDF header starts with '{' (often after an
    # optional magic line) and ends with '}'.
    brace_open = raw.find(b'{')
    if brace_open == -1:
        raise ValueError(f"Invalid EDF: no '{{' found in {filepath}")

    # Find the matching '}' — scan forward from the open brace.
    # EDF headers are pure ASCII between { and }, so searching for b'}'
    # is safe.
    brace_close = raw.find(b'}', brace_open)
    if brace_close == -1:
        raise ValueError(f"Invalid EDF: no '}}' found in {filepath}")

    header_text = raw[brace_open + 1:brace_close].decode(
        'latin-1', errors='replace')

    # Parse header key=value pairs.  Lines may be delimited by \\n or \\r\\n.
    # Multi-line values are rare in EDF but some writers use them; we handle
    # continuation lines (no '=').
    for line in header_text.replace('\r', '').split('\n'):
        line = line.strip()
        if not line or line.startswith(('#', '//')):
            continue
        if '=' in line:
            key, val = line.split('=', 1)
            key = key.strip()
            val = val.strip().rstrip(';')
            header[key] = val

    # ------------------------------------------------------------------
    #  Determine data start (skip '}' + any trailing whitespace)
    # ------------------------------------------------------------------
    data_start = brace_close + 1
    while data_start < len(raw) and raw[data_start:data_start + 1] in (
            b'\n', b'\r', b' ', b'\t'):
        data_start += 1

    # ------------------------------------------------------------------
    #  Parse dimensions
    # ------------------------------------------------------------------
    dim1 = int(header.get('Dim_1', 0))
    dim2 = int(header.get('Dim_2', 0))
    if dim1 <= 0 or dim2 <= 0:
        raise ValueError(
            f"Invalid EDF dimensions: Dim_1={dim1}, Dim_2={dim2}")

    # ------------------------------------------------------------------
    #  Data type mapping (complete set)
    # ------------------------------------------------------------------
    dtype_str = header.get('DataType', 'UnsignedShort')
    dtype_map = {
        'SignedByte':       np.int8,
        'UnsignedByte':     np.uint8,
        'SignedShort':      np.int16,
        'UnsignedShort':    np.uint16,
        'SignedInteger':    np.int32,
        'SignedLong':       np.int32,
        'UnsignedInteger':  np.uint32,
        'UnsignedLong':     np.uint32,
        'Signed64':         np.int64,
        'FloatValue':       np.float32,
        'Float':            np.float32,
        'DoubleValue':      np.float64,
        'Double':           np.float64,
    }
    dtype = dtype_map.get(dtype_str, np.uint16)
    dtype = np.dtype(dtype)

    # ------------------------------------------------------------------
    #  Byte order
    # ------------------------------------------------------------------
    byte_order = header.get('ByteOrder', 'LowByteFirst')
    if 'High' in byte_order:
        dtype = dtype.newbyteorder('>')
    else:
        dtype = dtype.newbyteorder('<')

    # ------------------------------------------------------------------
    #  Read binary data
    # ------------------------------------------------------------------
    expected_bytes = dim1 * dim2 * np.dtype(dtype).itemsize
    available_bytes = len(raw) - data_start
    if available_bytes < expected_bytes:
        raise ValueError(
            f"EDF data truncated: need {expected_bytes} bytes, "
            f"only {available_bytes} available after header")

    data = np.frombuffer(raw[data_start:data_start + expected_bytes],
                         dtype=dtype)
    # EDF stores data in row-major order: Dim_1 = width (fast), Dim_2 = height
    data = data.reshape(dim2, dim1).astype(np.float64)

    return data, header


def _read_edf_header_fallback(filepath: str) -> dict:
    """Parse only the EDF header from a file."""
    with open(filepath, 'rb') as f:
        raw = f.read()

    brace_open = raw.find(b'{')
    if brace_open == -1:
        raise ValueError(f"Invalid EDF: no '{{' found in {filepath}")

    brace_close = raw.find(b'}', brace_open)
    if brace_close == -1:
        raise ValueError(f"Invalid EDF: no '}}' found in {filepath}")

    header_text = raw[brace_open + 1:brace_close].decode('latin-1', errors='replace')
    header: Dict[str, str] = {}

    for line in header_text.replace('\r', '').split('\n'):
        line = line.strip()
        if not line or line.startswith(('#', '//')):
            continue
        if '=' in line:
            key, val = line.split('=', 1)
            header[key.strip()] = val.strip().rstrip(';')

    return header
