"""IR data input module.

Supports experimental formats:
    - Thermo Omnic .spa (single spectrum)
    - Generic .csv / .txt / .dat (two-column: wavenumber, absorbance/transmittance)
    - .dpt (Thermo data point table)

Computational output parsing:
    - Gaussian .log frequency output
    - ORCA .out frequency output
    - Generic (freq, IR_intensity) CSV
"""

import logging
logger = logging.getLogger(__name__)

import os
import re
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
#  Data containers
# ---------------------------------------------------------------------------

@dataclass
class IRSpectrum:
    """One IR spectrum (experimental or simulated)."""
    label: str = ""
    wavenumber: np.ndarray = field(default_factory=lambda: np.array([]))
    absorbance: np.ndarray = field(default_factory=lambda: np.array([]))
    transmittance: np.ndarray = field(default_factory=lambda: np.array([]))
    raw_absorbance: np.ndarray = field(default_factory=lambda: np.array([]))
    source: str = "experiment"  # 'experiment', 'computation'
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_data(self) -> bool:
        return len(self.wavenumber) > 0 and (
            len(self.absorbance) > 0 or len(self.transmittance) > 0
        )


@dataclass
class ComputedMode:
    """One computed vibrational mode."""
    index: int = 0
    frequency_cm1: float = 0.0
    ir_intensity_km_mol: float = 0.0
    symmetry: str = ""
    assignment: str = ""


def _decode_null_terminated(raw: bytes, start: int, end: int) -> str:
    chunk = raw[start:end].split(b'\x00', 1)[0].strip()
    if not chunk:
        return ""
    for enc in ("utf-8", "latin1"):
        try:
            return chunk.decode(enc, errors="ignore").strip()
        except Exception:
            logger.warning("静默异常", exc_info=True)
    return ""


def _looks_like_transmittance(values: np.ndarray,
                              column_names: Optional[List[str]] = None,
                              ) -> bool:
    """Heuristic unit detection for table/SPA spectra.

    Plain absorbance values often live between 0 and 1, so a unitless
    0..1 column is treated as absorbance unless the header says otherwise.
    """
    names = " ".join(column_names or []).lower()
    if any(token in names for token in ("abs", "absorbance")):
        return False
    if any(token in names for token in ("trans", "%t", "percent t", "透过")):
        return True

    y = np.asarray(values, dtype=float)
    y = y[np.isfinite(y)]
    if y.size == 0 or np.nanmin(y) < 0:
        return False

    ymax = float(np.nanmax(y))
    ymin = float(np.nanmin(y))
    if 1.5 < ymax <= 120.0 and ymin >= 0.0:
        return True
    return False


def _select_wavenumber_column(data: np.ndarray) -> int:
    """Pick the column most likely to be wavenumber in cm^-1."""
    best_idx, best_score = 0, -np.inf
    for i in range(data.shape[1]):
        col = data[:, i].astype(float)
        finite = col[np.isfinite(col)]
        if finite.size < 2:
            continue
        in_mid_ir = np.mean((finite >= 300.0) & (finite <= 4500.0))
        span = float(np.nanmax(finite) - np.nanmin(finite))
        diffs = np.diff(finite)
        monotonic = max(np.mean(diffs >= 0), np.mean(diffs <= 0))
        score = in_mid_ir * 3.0 + min(span / 3500.0, 1.5) + monotonic
        if score > best_score:
            best_score = score
            best_idx = i
    return best_idx


# ---------------------------------------------------------------------------
#  Experimental spectrum readers
# ---------------------------------------------------------------------------

def load_spectrum(filepath: str,
                  wavenumber_range: Optional[Tuple[float, float]] = None,
                  ) -> IRSpectrum:
    """Load an experimental IR spectrum from file. Auto-detects format."""
    ext = os.path.splitext(filepath)[1].lower()

    if ext in ('.csv', '.txt', '.dat', '.asc', '.prn'):
        return _load_csv(filepath, wavenumber_range)
    elif ext == '.spa':
        return _load_spa(filepath, wavenumber_range)
    elif ext == '.dpt':
        return _load_dpt(filepath, wavenumber_range)
    else:
        # Try CSV as fallback
        return _load_csv(filepath, wavenumber_range)


def _load_csv(filepath: str,
              wavenumber_range: Optional[Tuple[float, float]] = None,
              ) -> IRSpectrum:
    """Load a two-column IR spectrum from CSV/dat/txt.

    Uses the unified table loader for robust parsing, then applies
    IR-specific logic (wavenumber detection, transmittance check).
    """
    from ...readers.unified_io import load_table

    label = os.path.splitext(os.path.basename(filepath))[0]

    try:
        cols, data = load_table(filepath)
    except Exception:
        return IRSpectrum(label=label)
        logger.warning("异常已处理", exc_info=True)

    if data.shape[1] < 2:
        return IRSpectrum(label=label)

    wn_col = _select_wavenumber_column(data[:, :2])
    y_col = 1 - wn_col
    wn_raw = data[:, wn_col]
    y_raw = data[:, y_col]
    valid = np.isfinite(wn_raw) & np.isfinite(y_raw)
    wn, y = wn_raw[valid], y_raw[valid]

    if len(wn) < 2:
        return IRSpectrum(label=label)

    # Ensure decreasing wavenumber (standard IR convention)
    if len(wn) > 1 and wn[0] < wn[-1]:
        wn, y = wn[::-1], y[::-1]

    if wavenumber_range:
        mask = (wn >= wavenumber_range[0]) & (wn <= wavenumber_range[1])
        wn, y = wn[mask], y[mask]

    y_header = [cols[y_col]] if y_col < len(cols) else []
    if _looks_like_transmittance(y, y_header):
        return IRSpectrum(
            label=label, wavenumber=wn, transmittance=y,
            metadata={'format': 'table', 'y_unit': 'transmittance'},
        )

    return IRSpectrum(
        label=label, wavenumber=wn, absorbance=y,
        metadata={'format': 'table', 'y_unit': 'absorbance'},
    )

def _load_spa(filepath: str,
              wavenumber_range: Optional[Tuple[float, float]] = None,
              ) -> IRSpectrum:
    """Load a Thermo Omnic .spa file (binary format).

    Falls back to reading as raw binary and extracting float arrays.
    For production use, consider `specio` or `brukeropusreader` packages.
    """
    label = os.path.splitext(os.path.basename(filepath))[0]

    try:
        from specio import specread
        spectra = specread(filepath)
        if len(spectra) > 0:
            spec = spectra[0]
            wn = spec.spectral_axis
            ab = spec.intensities
            return IRSpectrum(label=label, wavenumber=wn, absorbance=ab)
    except ImportError:
        pass

    try:
        with open(filepath, 'rb') as f:
            raw = f.read()

        parsed = _parse_thermo_spa_binary(raw)
        if parsed is not None:
            wn, y, meta = parsed
            file_label = _decode_null_terminated(raw, 30, 286)
            if file_label:
                label = file_label

            if wavenumber_range:
                mask = (wn >= wavenumber_range[0]) & (wn <= wavenumber_range[1])
                wn, y = wn[mask], y[mask]

            if _looks_like_transmittance(y):
                return IRSpectrum(label=label, wavenumber=wn, transmittance=y,
                                  metadata=meta | {'y_unit': 'transmittance'})
            return IRSpectrum(label=label, wavenumber=wn, absorbance=y,
                              metadata=meta | {'y_unit': 'absorbance'})
    except Exception:
        logger.warning("静默异常", exc_info=True)

    # Fallback: attempt binary parse
    try:
        with open(filepath, 'rb') as f:
            raw = f.read()

        # SPA files contain float32 arrays — try to extract
        # Header contains metadata, data starts at known offset
        # Simplified: find the largest contiguous float32 block
        data = np.frombuffer(raw, dtype=np.float32)
        # Remove extreme values
        data = data[np.abs(data) < 1e10]
        if len(data) < 20:
            return IRSpectrum(label=label)

        # SPA typically has data in blocks — try to find spectral data
        # Heuristic: take second half as intensity, first half as wavenumber
        mid = len(data) // 2
        ab = data[mid:]
        wn = np.arange(len(ab), dtype=np.float32) * 2.0 + 600.0  # approximate

        return IRSpectrum(
            label=label, wavenumber=wn, absorbance=ab,
            metadata={'format': 'spa_binary_fallback'},
        )
    except Exception:
        return IRSpectrum(label=label, metadata={'error': 'spa_load_failed'})
        logger.warning("异常已处理", exc_info=True)


def _parse_thermo_spa_binary(raw: bytes
                             ) -> Optional[Tuple[np.ndarray, np.ndarray, Dict[str, Any]]]:
    """Parse the common Thermo OMNIC SPA float32 spectrum block."""
    if len(raw) < 2048:
        return None

    usable = (len(raw) // 4) * 4
    floats = np.frombuffer(raw[:usable], dtype='<f4')
    ints = np.frombuffer(raw[:usable], dtype='<i4')

    descriptors = []
    max_scan = min(len(raw) - 32, 8192)
    for off in range(0, max_scan, 4):
        idx = off // 4
        marker = int(ints[idx])
        n_points = int(ints[idx + 1])
        axis_count = int(ints[idx + 2])
        axis_type = int(ints[idx + 3])
        x_start = float(floats[idx + 4])
        x_end = float(floats[idx + 5])
        if marker not in (1, 2, 3, 4):
            continue
        if axis_count not in (1, 2, 3) or axis_type <= 0:
            continue
        if not (128 <= n_points <= 200000):
            continue
        if not (300.0 <= x_start <= 5000.0 and 300.0 <= x_end <= 5000.0):
            continue
        if abs(x_start - x_end) < 100.0:
            continue
        descriptors.append((n_points, x_start, x_end, off))

    if not descriptors:
        return None

    n_points, x_start, x_end, descriptor_offset = max(descriptors, key=lambda d: d[0])
    y_start = _find_spa_data_start(floats, n_points)
    if y_start is None:
        return None

    y = np.array(floats[y_start:y_start + n_points], dtype=float)
    wn = np.linspace(x_start, x_end, n_points, dtype=float)

    if wn[0] < wn[-1]:
        wn = wn[::-1]
        y = y[::-1]

    meta = {
        'format': 'thermo_spa',
        'spa_points': int(n_points),
        'spa_x_start': float(x_start),
        'spa_x_end': float(x_end),
        'spa_descriptor_offset': int(descriptor_offset),
        'spa_data_offset': int(y_start * 4),
    }
    return wn, y, meta


def _find_spa_data_start(floats: np.ndarray, n_points: int) -> Optional[int]:
    finite = np.isfinite(floats)
    plausible = finite & (floats > -5.0) & (floats < 150.0)

    runs = []
    start = None
    for i, ok in enumerate(plausible):
        if ok and start is None:
            start = i
        if (not ok or i == len(plausible) - 1) and start is not None:
            end = i if not ok else i + 1
            if end - start >= n_points:
                runs.append((start, end))
            start = None

    best = None
    best_score = -np.inf
    for run_start, run_end in runs:
        first = run_start
        while first < run_end and abs(float(floats[first])) < 1e-5:
            first += 1

        candidates = {run_start, first, max(run_start, run_end - n_points)}
        for cand in sorted(candidates):
            if cand < run_start or cand + n_points > run_end:
                continue
            y = np.asarray(floats[cand:cand + n_points], dtype=float)
            if not np.all(np.isfinite(y)):
                continue
            dyn = float(np.nanmax(y) - np.nanmin(y))
            if dyn < 1e-4:
                continue
            dy = np.abs(np.diff(y))
            median_step = float(np.nanmedian(dy)) if len(dy) else 0.0
            max_step = float(np.nanmax(dy)) if len(dy) else 0.0
            roughness = median_step / max(dyn, 1e-12)
            jump_penalty = max_step / max(dyn, 1e-12)
            early_penalty = cand / max(len(floats), 1) * 0.02
            score = dyn / (1.0 + 8.0 * roughness + 0.1 * jump_penalty) - early_penalty
            if score > best_score:
                best_score = score
                best = cand

    return best


def _load_dpt(filepath: str,
              wavenumber_range: Optional[Tuple[float, float]] = None,
              ) -> IRSpectrum:
    """Load a Thermo .dpt (data point table) file."""
    return _load_csv(filepath, wavenumber_range)


# ---------------------------------------------------------------------------
#  Computational output parsers
# ---------------------------------------------------------------------------

def parse_gaussian_frequencies(filepath: str,
                               correction_factor: float = 0.9613,
                               ) -> List[ComputedMode]:
    """Parse harmonic frequencies and IR intensities from Gaussian .log file.

    Looks for lines like:
         1         2         3
         A         A         A
     Frequencies --   450.1234            680.5678            720.9012
     IR Inten    --     0.1234             45.6789             0.0012
    """
    modes = []
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    # Find frequency blocks
    freq_blocks = re.findall(
        r'Frequencies --\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)?',
        content
    )
    ir_blocks = re.findall(
        r'IR Inten\s+--\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)?',
        content
    )

    idx = 1
    for fb, ib in zip(freq_blocks, ir_blocks):
        for j in range(3):
            try:
                freq = float(fb[j]) * correction_factor
                ir_int = float(ib[j]) if ib[j] else 0.0
                modes.append(ComputedMode(
                    index=idx,
                    frequency_cm1=freq,
                    ir_intensity_km_mol=ir_int,
                ))
                idx += 1
            except (IndexError, ValueError):
                pass

    return modes


def parse_orca_frequencies(filepath: str,
                           correction_factor: float = 0.9613,
                           ) -> List[ComputedMode]:
    """Parse harmonic frequencies and IR intensities from ORCA .out file.

    Looks for the 'VIBRATIONAL FREQUENCIES' section.
    """
    modes = []
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

    in_freq_section = False
    idx = 1
    for line in lines:
        if 'VIBRATIONAL FREQUENCIES' in line:
            in_freq_section = True
            continue
        if in_freq_section and line.strip().startswith('---'):
            continue
        if in_freq_section and not line.strip():
            in_freq_section = False
            continue

        if in_freq_section:
            parts = line.strip().split()
            if len(parts) >= 2:
                try:
                    mode_num = int(parts[0].rstrip(':'))
                    freq = float(parts[1]) * correction_factor
                    # IR intensity is typically column 8 or after 'IR'
                    ir_int = 0.0
                    for i, p in enumerate(parts):
                        if p.lower() == 'ir' and i + 1 < len(parts):
                            ir_int = float(parts[i + 1])
                            break
                    modes.append(ComputedMode(
                        index=mode_num,
                        frequency_cm1=freq,
                        ir_intensity_km_mol=ir_int,
                    ))
                except (ValueError, IndexError):
                    pass

    return modes


def load_computed_modes(filepath: str,
                        correction_factor: float = 0.9613,
                        ) -> List[ComputedMode]:
    """Auto-detect and parse computational frequency output."""
    ext = os.path.splitext(filepath)[1].lower()

    if ext in ('.log', '.out', '.g16', '.g09'):
        # Try Gaussian first, then ORCA
        modes = parse_gaussian_frequencies(filepath, correction_factor)
        if not modes:
            modes = parse_orca_frequencies(filepath, correction_factor)
        return modes
    elif ext in ('.csv', '.txt', '.dat'):
        # Generic: freq, IR_intensity
        try:
            data = np.genfromtxt(filepath, delimiter=',', invalid_raise=False)
            if data.ndim == 1:
                data = data.reshape(-1, 1)
            modes = []
            for i, row in enumerate(data):
                freq = row[0] * correction_factor
                ir_int = row[1] if data.shape[1] > 1 else 1.0
                modes.append(ComputedMode(
                    index=i + 1,
                    frequency_cm1=float(freq),
                    ir_intensity_km_mol=float(ir_int),
                ))
            return modes
        except Exception:
            logger.warning("静默异常", exc_info=True)

    return []


# ---------------------------------------------------------------------------
#  Spectrum simulation from computed modes
# ---------------------------------------------------------------------------

def simulate_spectrum(modes: List[ComputedMode],
                      wavenumber_range: Tuple[float, float] = (400.0, 4000.0),
                      resolution: float = 1.0,
                      lineshape: str = 'lorentzian',
                      fwhm: float = 8.0,
                      ) -> IRSpectrum:
    """Generate a simulated IR spectrum from computed vibrational modes.

    Parameters
    ----------
    modes : list of ComputedMode
    wavenumber_range : (min, max) in cm^-1
    resolution : float
        Sampling interval in cm^-1.
    lineshape : str
        'lorentzian', 'gaussian', 'pseudo_voigt'.
    fwhm : float
        Full width at half maximum in cm^-1.

    Returns
    -------
    IRSpectrum with simulated absorbance.
    """
    wn = np.arange(wavenumber_range[1], wavenumber_range[0] - resolution, -resolution)

    if not modes:
        return IRSpectrum(wavenumber=wn, absorbance=np.zeros_like(wn),
                         source='computation')

    spectrum = np.zeros_like(wn)

    for mode in modes:
        if mode.ir_intensity_km_mol <= 0:
            continue
        freq = mode.frequency_cm1

        if lineshape == 'lorentzian':
            gamma = fwhm / 2.0
            peak = mode.ir_intensity_km_mol * gamma**2 / ((wn - freq)**2 + gamma**2)
        elif lineshape == 'gaussian':
            sigma = fwhm / 2.355
            peak = mode.ir_intensity_km_mol * np.exp(-0.5 * ((wn - freq) / sigma)**2)
        elif lineshape == 'pseudo_voigt':
            # 50:50 Gaussian:Lorentzian
            sigma = fwhm / 2.355
            gamma = fwhm / 2.0
            g = np.exp(-0.5 * ((wn - freq) / sigma)**2)
            l = gamma**2 / ((wn - freq)**2 + gamma**2)
            peak = mode.ir_intensity_km_mol * (0.5 * g + 0.5 * l)
        else:
            gamma = fwhm / 2.0
            peak = mode.ir_intensity_km_mol * gamma**2 / ((wn - freq)**2 + gamma**2)

        spectrum += peak

    # Normalize to [0, 1]
    if np.max(spectrum) > 0:
        spectrum /= np.max(spectrum)

    return IRSpectrum(
        label=f"Simulated ({lineshape}, fwhm={fwhm:.0f})",
        wavenumber=wn,
        absorbance=spectrum,
        source='computation',
    )


def load_project(filepath: str,
                 wavenumber_range: Optional[Tuple[float, float]] = None,
                 ) -> List[IRSpectrum]:
    """Load one or more IR spectra from file or directory."""
    if os.path.isdir(filepath):
        spectra = []
        exts = {'.csv', '.txt', '.dat', '.spa', '.dpt', '.asc'}
        for fn in sorted(os.listdir(filepath)):
            fp = os.path.join(filepath, fn)
            if os.path.isfile(fp) and os.path.splitext(fn)[1].lower() in exts:
                spec = load_spectrum(fp, wavenumber_range)
                if spec.has_data:
                    spec.metadata.setdefault('filepath', fp)
                    spec.metadata.setdefault('filename', fn)
                    spectra.append(spec)
        return spectra
    else:
        spec = load_spectrum(filepath, wavenumber_range)
        spec.metadata.setdefault('filepath', filepath)
        spec.metadata.setdefault('filename', os.path.basename(filepath))
        return [spec] if spec.has_data else []
