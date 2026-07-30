"""NMR data input module.

Experimental formats:
    - Liquid-state Bruker-compatible raw ``fid`` files
    - Bruker TopSpin processed spectra (``pdata/1/1r``)
    - JEOL ``JEOL.NMR`` containers (``.jdf`` / ``.jdf.bin``)
    - JEOL or generic CSV tables (ppm, intensity)

Computational output parsing:
    - CASTEP .magres (NMR tensors)
    - Generic (shift_ppm, relative_intensity) CSV
"""
from __future__ import annotations

import logging

import os
import re
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from ...readers.unified_io import load_table

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
#  Data containers
# ---------------------------------------------------------------------------

@dataclass
class NMRSpectrum:
    """One 1D NMR spectrum."""

    label: str = ""
    nucleus: str = "13C"
    ppm: np.ndarray = field(default_factory=lambda: np.array([]))
    intensity: np.ndarray = field(default_factory=lambda: np.array([]))
    source: str = "experiment"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_data(self) -> bool:
        return len(self.ppm) > 0 and len(self.intensity) > 0


@dataclass
class NMRRelaxation:
    """T1/T2 relaxation data."""

    label: str = ""
    relaxation_type: str = "T1"  # 'T1', 'T2', 'T1rho'
    delay_values: np.ndarray = field(default_factory=lambda: np.array([]))
    intensities: Dict[float, np.ndarray] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComputedShift:
    """One computed NMR chemical shift from quantum chemistry."""

    index: int = 0
    nucleus: str = "13C"
    shift_ppm: float = 0.0
    shielding_ppm: float = 0.0
    reference_shielding: float = 0.0
    assignment: str = ""
    sigma_iso: float = 0.0
    span_ppm: float = 0.0
    skew: float = 0.0
    anisotropy_ppm: float = 0.0
    asymmetry: float = 0.0


# Public constants shared across NMR modules
TABLE_EXTS = {".csv", ".txt", ".dat", ".asc"}
NMR_EXTS = TABLE_EXTS | {".jdf", ".bin"}
NMR_OUTPUT_DIRS = {"nmr_results", "nmr_solid_results", "polynexus_output", "__pycache__"}


# ---------------------------------------------------------------------------
#  Experiment inference helpers
# ---------------------------------------------------------------------------

TABLE_EXTS = {".csv", ".txt", ".dat", ".asc"}
NMR_EXTS = TABLE_EXTS | {".jdf", ".bin"}


def _path_text(path: str | os.PathLike[str]) -> str:
    return str(path).lower().replace("\\", "/")


def infer_nucleus(path: str | os.PathLike[str], fallback: str = "13C") -> str:
    """Infer nucleus from directory names, file names, or JEOL labels."""

    text = _path_text(path)
    carbon_markers = (
        "c\u8c31", "\u78b3\u8c31", "carbon", "carbon13", "13c", "cpmas", "_c_", "-c_",
        " c ", "/c", "\\c",
    )
    proton_markers = (
        "h\u8c31", "\u6c22\u8c31", "proton", "hydrogen", "1h", "single_pulse", "_h_", "-h_",
        " h ", "/h", "\\h",
    )
    if any(m in text for m in carbon_markers):
        return "13C"
    if any(m in text for m in proton_markers):
        return "1H"
    return fallback


def infer_sample_state(path: str | os.PathLike[str], fallback: str = "solid") -> str:
    text = _path_text(path)
    if "\u6db2\u4f53" in text or "\u6eb6\u6db2" in text or "liquid" in text or "solution" in text:
        return "liquid"
    if "\u56fa\u4f53" in text or "solid" in text or "cpmas" in text or " mas" in text or "_mas" in text:
        return "solid"
    return fallback


def default_ppm_range(nucleus: str, sample_state: str) -> Tuple[float, float]:
    nucleus = (nucleus or "13C").upper()
    sample_state = (sample_state or "solid").lower()
    if nucleus in {"1H", "H"}:
        return (12.5, -0.5) if sample_state == "liquid" else (60.0, -20.0)
    return (220.0, -10.0) if sample_state == "liquid" else (240.0, -20.0)


def _ppm_axis(n_points: int, nucleus: str, sample_state: str,
              ppm_range: Optional[Tuple[float, float]] = None) -> np.ndarray:
    hi, lo = ppm_range or default_ppm_range(nucleus, sample_state)
    return np.linspace(float(hi), float(lo), int(n_points))


def _normalise_intensity(y: np.ndarray) -> np.ndarray:
    y = np.asarray(y, dtype=float)
    finite = np.isfinite(y)
    if not finite.any():
        return np.array([])
    y = np.where(finite, y, np.nanmedian(y[finite]))
    span = float(np.nanmax(y) - np.nanmin(y))
    if span <= 1e-12:
        return y
    return (y - np.nanmin(y)) / span


def _is_jeol_file(filepath: str) -> bool:
    try:
        with open(filepath, "rb") as f:
            return f.read(8) == b"JEOL.NMR"
    except OSError:
        return False


# ---------------------------------------------------------------------------
#  Experimental readers
# ---------------------------------------------------------------------------

def load_spectrum(filepath: str, sample_state: Optional[str] = None,
                  nucleus: Optional[str] = None) -> NMRSpectrum:
    """Load an NMR spectrum with format auto-detection."""

    if os.path.isdir(filepath):
        spectra = load_project(filepath, sample_state=sample_state, nucleus=nucleus)
        return spectra[0] if spectra else NMRSpectrum(label=os.path.basename(filepath))

    label = Path(filepath).stem or Path(filepath).name
    state = sample_state or infer_sample_state(filepath)
    nuc = nucleus or infer_nucleus(filepath)
    basename = os.path.basename(filepath).lower()
    ext = os.path.splitext(filepath)[1].lower()

    if basename == "fid":
        return _load_raw_fid(filepath, sample_state=state, nucleus=nuc)
    if ext in {".jdf", ".bin"} or _is_jeol_file(filepath):
        return _load_jeol_jdf(filepath, sample_state=state, nucleus=nuc)
    if ext in TABLE_EXTS:
        return _load_csv(filepath, sample_state=state, nucleus=nuc)
    return NMRSpectrum(label=label, nucleus=nuc, metadata={"error": "unsupported_format"})


def _load_csv(filepath: str, sample_state: Optional[str] = None,
              nucleus: Optional[str] = None) -> NMRSpectrum:
    """Load a two-column CSV/TXT/DAT table as (ppm, intensity)."""

    label = os.path.splitext(os.path.basename(filepath))[0]
    state = sample_state or infer_sample_state(filepath)
    nuc = nucleus or infer_nucleus(filepath)
    try:
        data = load_table(filepath)[1]
    except Exception:
        logger.warning("NMR CSV table load failed.", exc_info=True)
        return NMRSpectrum(label=label, nucleus=nuc, metadata={"error": "table_load_failed"})

    if data.ndim == 1:
        data = data.reshape(-1, 1)
    if data.shape[1] < 2:
        return NMRSpectrum(label=label, nucleus=nuc, metadata={"error": "not_two_column"})

    valid = np.isfinite(data[:, 0]) & np.isfinite(data[:, 1])
    ppm = np.asarray(data[valid, 0], dtype=float)
    intensity = np.asarray(data[valid, 1], dtype=float)
    if len(ppm) > 1 and ppm[0] < ppm[-1]:
        ppm = ppm[::-1]
        intensity = intensity[::-1]

    return NMRSpectrum(
        label=label,
        nucleus=nuc,
        ppm=ppm,
        intensity=intensity,
        metadata={"format": "table", "sample_state": state, "filename": filepath},
    )


def _load_bruker_pdata(dirpath: str, sample_state: Optional[str] = None,
                       nucleus: Optional[str] = None) -> NMRSpectrum:
    """Load Bruker TopSpin processed data (``pdata/1/1r``)."""

    path = Path(dirpath)
    label = path.name
    state = sample_state or infer_sample_state(dirpath)
    nuc = nucleus or infer_nucleus(dirpath)
    pdata_dir = path / "pdata" / "1"
    if not pdata_dir.is_dir():
        pdata_dir = path

    procs_path = pdata_dir / "procs"
    real_path = pdata_dir / "1r"
    if not real_path.is_file():
        return NMRSpectrum(label=label, nucleus=nuc)

    try:
        params: Dict[str, str] = {}
        if procs_path.is_file():
            with open(procs_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("##$"):
                        key, _, val = line[3:].partition("=")
                        params[key.strip()] = val.strip()

        offset_ppm = float(params.get("OFFSET", default_ppm_range(nuc, state)[0]))
        sw_ppm = float(params.get("SW_p", abs(np.diff(default_ppm_range(nuc, state))[0])))
        si = int(float(params.get("SI", "32768")))

        raw = real_path.read_bytes()
        dtype = np.dtype(">i4")
        n_points = min(len(raw) // 4, si)
        data = np.frombuffer(raw[:n_points * 4], dtype=dtype).astype(float)
        ppm = np.linspace(offset_ppm, offset_ppm - sw_ppm, len(data))
        intensity = _normalise_intensity(data)

        return NMRSpectrum(
            label=label,
            nucleus=nuc,
            ppm=ppm,
            intensity=intensity,
            metadata={
                "format": "bruker_pdata",
                "sample_state": state,
                "params": params,
                "filename": str(real_path),
            },
        )
    except Exception as exc:
        logger.warning("NMR Bruker processed spectrum load failed.", exc_info=True)
        return NMRSpectrum(
            label=label,
            nucleus=nuc,
            metadata={"error": "bruker_load_failed", "detail": str(exc)},
        )


def _next_power_of_two(n: int) -> int:
    return 1 << max(1, int(n - 1).bit_length())


def _auto_phase_spectrum(spec: np.ndarray) -> Tuple[np.ndarray, float]:
    """Brute-force zero-order phase correction for a complex spectrum."""

    best_score = -np.inf
    best_phase = 0.0
    best_y = spec.real
    for phase in np.linspace(-180.0, 180.0, 181):
        y = (spec * np.exp(1j * np.deg2rad(phase))).real
        pos = y[y > 0.0]
        neg = y[y < 0.0]
        score = float(np.sum(pos * pos) - 2.0 * np.sum(neg * neg))
        if score > best_score:
            best_score = score
            best_phase = float(phase)
            best_y = y
    return best_y, best_phase


def _load_raw_fid(filepath: str, sample_state: Optional[str] = None,
                  nucleus: Optional[str] = None) -> NMRSpectrum:
    """Transform a raw Bruker-compatible FID into a 1D spectrum.

    The real test data contains only ``fid`` without ``acqus`` metadata.  The
    reader therefore uses physically standard steps (complex integer FID,
    dead-time removal, exponential apodization, zero filling, FFT, zero-order
    phasing) and creates a nucleus-specific default ppm axis.
    """

    label = os.path.basename(os.path.dirname(filepath)) or "fid"
    state = sample_state or infer_sample_state(filepath, "liquid")
    nuc = nucleus or infer_nucleus(filepath)
    try:
        raw = np.fromfile(filepath, dtype="<i4")
        if raw.size < 4:
            return NMRSpectrum(label=label, nucleus=nuc)
        if raw.size % 2:
            raw = raw[:-1]
        fid = raw[0::2].astype(float) + 1j * raw[1::2].astype(float)
        nz = np.flatnonzero(np.abs(fid) > 0)
        leading_points = int(nz[0]) if nz.size else 0
        if leading_points:
            fid = fid[leading_points:]
        if fid.size < 16:
            return NMRSpectrum(label=label, nucleus=nuc)

        tail = fid[-max(16, min(512, fid.size // 20)):]
        fid = fid - np.nanmean(tail)
        window = np.exp(-np.linspace(0.0, 3.0, fid.size))
        n_fft = _next_power_of_two(fid.size * 2)
        spec = np.fft.fftshift(np.fft.fft(fid * window, n=n_fft))
        phased, phase_deg = _auto_phase_spectrum(spec)

        # If automatic phasing is unstable, magnitude mode is still a valid
        # inspection spectrum and is much safer than returning empty data.
        real_span = float(np.nanmax(phased) - np.nanmin(phased))
        mag = np.abs(spec)
        if real_span <= 1e-12:
            intensity = mag
            mode = "magnitude"
        else:
            intensity = phased
            mode = "phased_real"

        # After zero-order phasing, check whether first-order phase error
        # left a broad dispersion-mode hump in the downfield (empty) region.
        # For 1H liquid, 9–12.5 ppm should be nearly flat; a high floor
        # indicates poor phasing → fall back to magnitude mode.
        if mode == "phased_real":
            _n = len(intensity)
            _check_start = max(0, int(_n * 0.10))
            _check_end = min(_n, int(_n * 0.30))
            _check = intensity[_check_start:_check_end]
            if _check.size > 20:
                _check_norm = (_check - np.nanmin(intensity)) / max(real_span, 1e-12)
                _floor = float(np.nanmin(_check_norm))
                if _floor > 0.12:
                    intensity = mag
                    mode = "magnitude"
                    phase_deg = 0.0

        if abs(float(np.nanmin(intensity))) > 1.2 * abs(float(np.nanmax(intensity))):
            intensity = -intensity
        intensity = _normalise_intensity(intensity)
        ppm = _ppm_axis(len(intensity), nuc, state)

        return NMRSpectrum(
            label=label,
            nucleus=nuc,
            ppm=ppm,
            intensity=intensity,
            metadata={
                "format": "raw_fid",
                "sample_state": state,
                "filename": filepath,
                "raw_points": int(raw.size // 2),
                "fid_points": int(fid.size),
                "leading_zero_complex_points": leading_points,
                "fft_points": int(n_fft),
                "phase0_deg": phase_deg,
                "display_mode": mode,
                "ppm_range": default_ppm_range(nuc, state),
            },
        )
    except Exception as exc:
        logger.warning("NMR raw FID load failed.", exc_info=True)
        return NMRSpectrum(
            label=label,
            nucleus=nuc,
            metadata={"error": "raw_fid_load_failed", "detail": str(exc)},
        )


def _safe_float_jeol(value: Any) -> Optional[float]:
    """Convert a JEOL record value to float, returning None on failure."""
    if value is None:
        return None
    try:
        f = float(value)
        return f if np.isfinite(f) else None
    except (ValueError, TypeError):
        return None


def _read_jeol_record_value(blob: bytes, label: str) -> Optional[Any]:
    """Read a value from a JEOL.NMR record by its 8-byte label.

    JEOL records are 64-byte blocks.  The first 8 bytes hold the label,
    byte 29 is the type code, and bytes 44-51 hold the value.
    This function scans only on 64-byte boundaries so it never
    accidentally matches a substring inside a data payload.
    """
    key = label.encode("ascii")
    key_len = len(key)

    # Current JEOL exports use a four-byte record marker followed by a
    # 28-byte field name. Integer values are stored at +44 and floating-point
    # values at +48. Keep these values raw; their physical units are handled
    # by the axis provenance guard below.
    for offset in range(0, len(blob) - 63, 64):
        field = blob[offset + 4:offset + 32].rstrip(b"\x00 ")
        if field != key:
            continue
        try:
            if label in {"SCANS", "TOTAL_SCANS", "X_POINTS"}:
                int_value = struct.unpack("<i", blob[offset + 44:offset + 48])[0]
                if int_value:
                    return int(int_value)
                return int(struct.unpack("<i", blob[offset + 48:offset + 52])[0])
            return float(struct.unpack("<d", blob[offset + 48:offset + 56])[0])
        except (struct.error, ValueError, TypeError):
            logger.warning("NMR JEOL record value read failed.", exc_info=True)
            return None

    for offset in range(0, len(blob) - 63, 64):
        record_label = blob[offset:offset + 8]
        # match either the exact padded key or the raw key (older JEOL variants)
        if record_label[:key_len] != key:
            continue
        if record_label[key_len:].rstrip(b"\x00"):
            continue  # extra non-null chars after the label → different record

        type_code = blob[offset + 29]
        val_bytes = blob[offset + 44:offset + 52]

        try:
            if type_code in {0x01, 0x03}:
                return float(struct.unpack("<d", val_bytes)[0])
            if type_code in {0x20, 0x13}:
                return int(struct.unpack("<i", val_bytes[:4])[0])
            text = val_bytes.rstrip(b"\x00 ").decode("ascii", errors="ignore")
            return text or None
        except Exception:
            logger.warning("NMR JEOL record value read failed.", exc_info=True)
            return None

    return None


def _shannon_entropy(block: bytes) -> float:
    if not block:
        return 0.0
    counts = np.bincount(np.frombuffer(block, dtype=np.uint8), minlength=256)
    p = counts[counts > 0] / len(block)
    return float(-np.sum(p * np.log2(p)))


def _find_jeol_data_region(blob: bytes) -> Tuple[int, int]:
    """Find the high-entropy float64 payload inside a JEOL.NMR container."""

    block_size = 1024
    candidate_blocks: List[int] = []
    for off in range(0, len(blob), block_size):
        block = blob[off:off + block_size]
        if len(block) < block_size:
            continue
        nonzero = sum(c != 0 for c in block) / block_size
        printable = sum(32 <= c < 127 for c in block) / block_size
        unique = len(set(block))
        entropy = _shannon_entropy(block)
        if off >= 8192 and nonzero > 0.95 and unique >= 180 and entropy > 6.0 and printable < 0.6:
            candidate_blocks.append(off)

    if not candidate_blocks:
        return 0, 0

    groups: List[List[int]] = []
    for off in candidate_blocks:
        if not groups or off != groups[-1][-1] + block_size:
            groups.append([off])
        else:
            groups[-1].append(off)
    best = max(groups, key=len)
    start = best[0]
    end = best[-1] + block_size
    start = (start // 8) * 8
    end = (end // 8) * 8
    return start, end


def _replace_bad_float_values(values: np.ndarray) -> tuple[np.ndarray, int]:
    """Replace non-finite or absurdly large JEOL payload values."""
    y = np.asarray(values, dtype=float).copy()
    good = np.isfinite(y) & (np.abs(y) < 1e9)
    n_bad = int((~good).sum())
    if not good.any():
        return np.zeros_like(y), len(y)
    fill = float(np.nanmedian(y[good]))
    y[~good] = fill
    return y, n_bad


def _jeol_liquid_fid_layout(data: np.ndarray, nucleus: str) -> tuple[np.ndarray, str, int]:
    """Build a complex FID from a JEOL liquid-state payload.

    The liquid JEOL files observed in the test set store time-domain data,
    not a processed spectrum.  13C is best represented by two consecutive
    blocks (imaginary then real), while 1H uses the opposite orientation.
    """
    clean, n_bad = _replace_bad_float_values(data)
    nucleus = (nucleus or "13C").upper()
    if clean.size >= 4 and clean.size % 2 == 0:
        half = clean.size // 2
        if nucleus in {"1H", "H"}:
            return clean[:half] + 1j * clean[half:], "split_real_imag", n_bad
        return clean[half:] + 1j * clean[:half], "split_imag_real", n_bad
    if clean.size >= 4:
        if clean.size % 2:
            clean = clean[:-1]
        return clean[0::2] + 1j * clean[1::2], "interleaved_real_imag", n_bad
    return clean.astype(complex), "real_only", n_bad


def _spectrum_from_complex_fid(fid: np.ndarray) -> tuple[np.ndarray, float, int]:
    """Convert a complex FID to a display spectrum."""
    if fid.size < 8:
        return np.array([]), 0.0, 0
    tail = fid[-max(16, min(512, fid.size // 20)):]
    fid = fid - np.nanmean(tail)
    window = np.exp(-np.linspace(0.0, 3.0, fid.size))
    n_fft = _next_power_of_two(fid.size * 2)
    spec = np.fft.fftshift(np.fft.fft(fid * window, n=n_fft))
    phased, phase_deg = _auto_phase_spectrum(spec)
    intensity = phased
    if abs(float(np.nanmin(intensity))) > 1.2 * abs(float(np.nanmax(intensity))):
        intensity = -intensity
    return _normalise_intensity(intensity), phase_deg, n_fft


def _jeol_ppm_axis(n_points: int, nucleus: str, state: str,
                   params: Dict[str, Any]) -> np.ndarray:
    offset = _safe_float_jeol(params.get("X_OFFSET"))
    sweep = _safe_float_jeol(params.get("X_SWEEP_CLIPPED")) or _safe_float_jeol(params.get("X_SWEEP"))
    res = _safe_float_jeol(params.get("X_RESOLUTION"))
    x_points_raw = _safe_float_jeol(params.get("X_POINTS"))
    actual_n = int(x_points_raw) if x_points_raw == int(n_points) else int(n_points)

    params["_ppm_axis_units"] = "ppm"
    params["_ppm_axis_calibrated"] = False

    # Frequency-like JEOL values can be numerically valid but are not ppm.
    # Require a plausible ppm span before using them as a chemical-shift axis.
    if (
        offset is not None
        and sweep is not None
        and sweep > 0
        and abs(offset) <= 1000.0
        and sweep <= 1000.0
    ):
        params["_ppm_axis_source"] = "jeol_metadata"
        params["_ppm_axis_reason"] = "jeol_metadata_ppm_range"
        params["_ppm_axis_calibrated"] = True
        return np.linspace(offset, offset - sweep, actual_n)[:n_points]
    if (
        offset is not None
        and res is not None
        and res > 0
        and abs(offset) <= 1000.0
        and res * actual_n <= 1000.0
        and actual_n
    ):
        params["_ppm_axis_source"] = "jeol_resolution"
        params["_ppm_axis_reason"] = "jeol_metadata_ppm_resolution"
        params["_ppm_axis_calibrated"] = True
        return np.linspace(offset, offset - res * actual_n, actual_n)[:n_points]
    params["_ppm_axis_source"] = "default_range"
    params["_ppm_axis_reason"] = (
        "jeol_metadata_units_unconfirmed"
        if any(params.get(key) is not None for key in ("X_OFFSET", "X_SWEEP", "X_SWEEP_CLIPPED", "X_RESOLUTION"))
        else "jeol_metadata_missing"
    )
    return _ppm_axis(n_points, nucleus, state)


def _load_jeol_jdf(filepath: str, sample_state: Optional[str] = None,
                   nucleus: Optional[str] = None) -> NMRSpectrum:
    """Load a JEOL.NMR container with a float64 processed spectrum payload."""

    label = Path(filepath).name
    blob = Path(filepath).read_bytes()
    state = sample_state or infer_sample_state(filepath, "solid")

    ascii_head = blob[:4096].decode("latin1", errors="ignore").lower()
    nuc = nucleus or infer_nucleus(filepath)
    if "carbon13" in ascii_head:
        nuc = "13C"
    elif "proton" in ascii_head:
        nuc = "1H"

    start, end = _find_jeol_data_region(blob)
    if end <= start:
        return NMRSpectrum(
            label=label,
            nucleus=nuc,
            metadata={"format": "jeol_jdf", "error": "data_region_not_found"},
        )

    # --- read JEOL metadata records before building ppm axis ---
    params = {
        key: _read_jeol_record_value(blob, key)
        for key in (
            "SCANS", "TOTAL_SCANS", "X_POINTS", "X_OFFSET", "X_FREQ",
            "X_SWEEP", "X_SWEEP_CLIPPED", "X_RESOLUTION",
            "X_ACQ_DURATION", "FILTER_FACTOR",
        )
    }

    data = np.frombuffer(blob[start:end], dtype="<f8").astype(float)
    finite = np.isfinite(data)
    data = data[finite]
    if data.size == 0:
        return NMRSpectrum(label=label, nucleus=nuc, metadata={"format": "jeol_jdf"})

    if str(state).lower() == "liquid" and data.size >= 8192:
        fid, layout, n_bad = _jeol_liquid_fid_layout(data, nuc)
        intensity, phase_deg, n_fft = _spectrum_from_complex_fid(fid)
        ppm = _jeol_ppm_axis(len(intensity), nuc, state, params)
        params["_data_mode"] = "liquid_fid_fft"
        params["_fid_layout"] = layout
        params["_sanitized_float_points"] = int(n_bad)
        return NMRSpectrum(
            label=label,
            nucleus=nuc,
            ppm=ppm,
            intensity=intensity,
            metadata={
                "format": "jeol_jdf",
                "sample_state": state,
                "filename": filepath,
                "data_offset": int(start),
                "data_end": int(end),
                "data_points": int(data.size),
                "fid_points": int(fid.size),
                "fft_points": int(n_fft),
                "phase0_deg": float(phase_deg),
                "display_mode": "jeol_fid_fft",
                "params": params,
                "ppm_axis_source": params.get("_ppm_axis_source", "default_range"),
                "ppm_axis_reason": params.get("_ppm_axis_reason", "jeol_metadata_missing"),
                "ppm_axis_units": params.get("_ppm_axis_units", "ppm"),
                "ppm_axis_calibrated": bool(params.get("_ppm_axis_calibrated", False)),
                "ppm_range": (float(ppm[0]), float(ppm[-1])) if len(ppm) else default_ppm_range(nuc, state),
            },
        )

    data, n_bad = _replace_bad_float_values(data)
    if abs(float(np.nanmin(data))) > 1.2 * abs(float(np.nanmax(data))):
        data = -data
    ppm = _jeol_ppm_axis(len(data), nuc, state, params)
    if n_bad:
        params["_sanitized_float_points"] = int(n_bad)
    else:
        params["_sanitized_float_points"] = 0

    return NMRSpectrum(
        label=label,
        nucleus=nuc,
        ppm=ppm,
        intensity=data,
        metadata={
            "format": "jeol_jdf",
            "sample_state": state,
            "filename": filepath,
            "data_offset": int(start),
            "data_end": int(end),
            "data_points": int(data.size),
            "params": params,
            "ppm_axis_source": params.get("_ppm_axis_source", "default_range"),
            "ppm_axis_reason": params.get("_ppm_axis_reason", "jeol_metadata_missing"),
            "ppm_axis_units": params.get("_ppm_axis_units", "ppm"),
            "ppm_axis_calibrated": bool(params.get("_ppm_axis_calibrated", False)),
            "ppm_range": (float(ppm[0]), float(ppm[-1])) if len(ppm) else default_ppm_range(nuc, state),
        },
    )


def _supported_project_file(path: Path) -> bool:
    return path.name.lower() == "fid" or path.suffix.lower() in NMR_EXTS


def load_project(filepath: str, sample_state: Optional[str] = None,
                 nucleus: Optional[str] = None) -> List[NMRSpectrum]:
    """Load NMR spectra from a file or directory.

    Directories may contain a single Bruker/JEOL experiment or a collection of
    liquid/solid H/C subfolders.  Output folders are skipped during recursion.
    """

    path = Path(filepath)
    if not path.is_dir():
        spec = load_spectrum(str(path), sample_state=sample_state, nucleus=nucleus)
        return [spec] if spec.has_data else []

    state = sample_state or infer_sample_state(path)
    nuc = nucleus or infer_nucleus(path)

    processed = _load_bruker_pdata(str(path), sample_state=state, nucleus=nuc)
    if processed.has_data:
        return [processed]

    direct_fid = path / "fid"
    if direct_fid.is_file():
        spec = _load_raw_fid(str(direct_fid), sample_state=state, nucleus=nuc)
        return [spec] if spec.has_data else []

    spectra: List[NMRSpectrum] = []
    skip_dirs = NMR_OUTPUT_DIRS
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d.lower() not in skip_dirs]
        for filename in sorted(files):
            fp = Path(root) / filename
            if not _supported_project_file(fp):
                continue
            spec = load_spectrum(str(fp), sample_state=sample_state, nucleus=nucleus)
            if spec.has_data:
                spectra.append(spec)
    return spectra


# ---------------------------------------------------------------------------
#  Relaxation data
# ---------------------------------------------------------------------------

def load_relaxation(directory: str, relaxation_type: str = "T1") -> NMRRelaxation:
    """Load inversion-recovery (T1) or CPMG (T2) data series."""

    label = os.path.basename(directory.rstrip("/\\"))
    rel = NMRRelaxation(label=label, relaxation_type=relaxation_type)

    files = sorted(
        f for f in os.listdir(directory)
        if os.path.splitext(f)[1].lower() in TABLE_EXTS
    )

    for fn in files:
        fp = os.path.join(directory, fn)
        try:
            delay = _extract_delay(fn)
            spec = _load_csv(fp)
            if spec.has_data:
                rel.delay_values = np.append(rel.delay_values, delay)
                rel.intensities[delay] = spec.intensity
        except Exception:
            logger.warning("NMR relaxation spectrum load failed; skipping file.", exc_info=True)

    return rel


def _extract_delay(filename: str) -> float:
    match = re.search(r"([\d.]+)\s*s", filename)
    if match:
        return float(match.group(1))
    match = re.search(r"_([\d.]+)", filename)
    if match:
        val = float(match.group(1))
        return val / 1000.0 if val > 100 else val
    return 0.0


# ---------------------------------------------------------------------------
#  Computational output parsers
# ---------------------------------------------------------------------------

def parse_castep_magres(filepath: str,
                        reference_shielding: float = 170.0) -> List[ComputedShift]:
    """Parse CASTEP ``.magres`` NMR output."""

    shifts: List[ComputedShift] = []
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    blocks = re.split(r"<ms>", content)
    for block in blocks[1:]:
        atom_match = re.search(r'<atom\s+index="(\d+)"\s+label="(\w+)"', block)
        if not atom_match:
            continue
        idx = int(atom_match.group(1))
        label = atom_match.group(2)
        iso_match = re.search(r"sigma_iso\s*=\s*([\d.\-eE]+)", block)
        if not iso_match:
            continue

        sigma_iso = float(iso_match.group(1))
        shift_ppm = reference_shielding - sigma_iso
        span_match = re.search(r"span\s*=\s*([\d.\-eE]+)", block)
        skew_match = re.search(r"skew\s*=\s*([\d.\-eE]+)", block)
        shifts.append(ComputedShift(
            index=idx,
            nucleus=label,
            shift_ppm=shift_ppm,
            shielding_ppm=sigma_iso,
            reference_shielding=reference_shielding,
            sigma_iso=sigma_iso,
            span_ppm=float(span_match.group(1)) if span_match else 0.0,
            skew=float(skew_match.group(1)) if skew_match else 0.0,
            assignment=label,
        ))

    return shifts


def load_computed_shifts(filepath: str,
                         reference_shielding: float = 170.0) -> List[ComputedShift]:
    """Auto-detect and parse computational NMR output."""

    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".magres":
        return parse_castep_magres(filepath, reference_shielding)
    if ext in TABLE_EXTS:
        try:
            data = load_table(filepath)[1]
            if data.ndim == 1:
                data = data.reshape(-1, 1)
            shifts = []
            for i, row in enumerate(data):
                shift = row[0]
                shifts.append(ComputedShift(
                    index=i + 1,
                    shift_ppm=float(shift),
                    assignment=f"C{i + 1}",
                ))
            return shifts
        except Exception:
            logger.warning("NMR computed shift file load failed; trying next file.", exc_info=True)
    return []
