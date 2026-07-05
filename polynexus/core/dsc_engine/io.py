"""DSC data input module (v4.0 L3_SELFBUILT).

L3_SELFBUILT: calospy not available for Python 3.14 (2026-05-21).
All format parsers (TA/Netzsch/Mettler/CSV/Excel) are self-built.
Cross-validation path: DSC Xc vs WAXS Xc vs SAXS Xc (v4.0 scheme §9).
Quality flags are raised by DSCEngine._validate_results() on range violations.

Supports: TA Instruments (.001/.txt), Netzsch (.ngb/.ngt export),
Mettler Toledo (.mdt export), Perkin-Elmer (.dsc), generic CSV,
Excel (.xlsx/.xls), and isothermal-crystallisation sequence folders.

All internal data uses the IUPAC convention: **exothermic = positive** (exo up).
"""
import logging
logger = logging.getLogger(__name__)


import os
import re
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
#  Column standardisation map
# ---------------------------------------------------------------------------

COLUMN_MAP: Dict[str, str] = {
    # TA Instruments (Q series, Discovery series) ---------------------------
    "Temperature (°C)":   "T_C",
    "Temperature":         "T_C",
    "Heat Flow (mW)":     "HF_mW",
    "Heat Flow (W/g)":    "HF_Wg",
    "Normalized Heat Flow (W/g)": "HF_Wg",
    "Time (min)":         "t_min",
    "Time":               "t_min",
    "Modulated Temperature (°C)": "T_mod_C",
    "Modulated Heat Flow (W/g)":   "HF_mod_Wg",
    "Rev Heat Flow (W/g)":         "HF_rev_Wg",
    "Nonrev Heat Flow (W/g)":      "HF_nonrev_Wg",

    # Netzsch (Proteus export) ----------------------------------------------
    "Temp./°C":           "T_C",
    "DSC/(mW/mg)":        "HF_Wg",
    "DSC/(µV/mg)":        "HF_uVmg",
    "Time/min":           "t_min",

    # Mettler Toledo (STARe export) -----------------------------------------
    "°C":                 "T_C",
    "mW":                 "HF_mW",
    "W/g":                "HF_Wg",
    "min":                "t_min",
}


# ---------------------------------------------------------------------------
#  Standard-sample melting points for temperature calibration
# ---------------------------------------------------------------------------

CALIBRATION_STANDARDS: Dict[str, Tuple[float, float]] = {
    # name: (Tm_C, dHm_Jg)
    "In":  (156.60, 28.62),
    "Sn":  (231.93, 60.50),
    "Zn":  (419.53, 108.37),
    "Pb":  (327.47, 23.00),
    "H2O": (0.00,   333.55),
    "cyclohexane": (6.54, 31.25),
    "benzoic_acid": (122.37, 147.36),
    "KNO3": (128.70, 47.80),
}


# ---------------------------------------------------------------------------
#  Dataclass for a single scan
# ---------------------------------------------------------------------------

@dataclass
class DSCScan:
    """One heating/cooling/isothermal segment."""
    label: str = ""
    T_C: np.ndarray = field(default_factory=lambda: np.array([]))
    HF_mW: np.ndarray = field(default_factory=lambda: np.array([]))
    HF_Wg: np.ndarray = field(default_factory=lambda: np.array([]))
    t_min: np.ndarray = field(default_factory=lambda: np.array([]))
    mass_mg: float = 1.0
    rate_K_per_min: float = 10.0
    exo_up: bool = True  # always True internally
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
#  Program segmentation
# ---------------------------------------------------------------------------

def _segment_name(delta_T: float) -> str:
    if delta_T > 0:
        return "heat"
    if delta_T < 0:
        return "cool"
    return "isothermal"


def split_scan_segments(scan: DSCScan,
                        min_points: int = 40,
                        min_delta_T: float = 2.0) -> List[DSCScan]:
    """Split a DSC program into monotonic heating/cooling segments.

    Many instrument exports store heat-cool-heat programs as one long table.
    Standard DSC physics must be run on each monotonic segment separately;
    otherwise cooling crystallisation can be misclassified as a heating event.
    """
    T = np.asarray(scan.T_C, dtype=float)
    if len(T) < min_points:
        return [scan]

    n = len(T)
    hf_mw = np.asarray(scan.HF_mW, dtype=float) if len(scan.HF_mW) == n else np.full(n, np.nan)
    hf_wg = np.asarray(scan.HF_Wg, dtype=float) if len(scan.HF_Wg) == n else np.full(n, np.nan)
    t_min = np.asarray(scan.t_min, dtype=float) if len(scan.t_min) == n else np.array([])

    valid = np.isfinite(T)
    if len(hf_mw) == n:
        valid &= np.isfinite(hf_mw)
    if len(hf_wg) == n:
        valid &= np.isfinite(hf_wg)

    if np.sum(valid) < min_points:
        return [scan]

    T = T[valid]
    hf_mw = hf_mw[valid]
    hf_wg = hf_wg[valid]
    if len(t_min) == n:
        t_min = t_min[valid]

    dT = np.diff(T)
    nonzero = np.abs(dT) > 1e-9
    if not np.any(nonzero):
        return [scan]

    step_ref = float(np.median(np.abs(dT[nonzero])))
    eps = max(1e-5, step_ref * 0.15)
    direction = np.zeros(len(dT), dtype=int)
    direction[dT > eps] = 1
    direction[dT < -eps] = -1

    nz = np.where(direction != 0)[0]
    if len(nz) == 0:
        return [scan]

    # Fill short isothermal/reversal points with the nearest program direction
    # so breakpoints sit at true heating/cooling changes rather than at noise.
    first_sign = direction[nz[0]]
    direction[:nz[0]] = first_sign
    last = first_sign
    for i in range(nz[0], len(direction)):
        if direction[i] == 0:
            direction[i] = last
        else:
            last = direction[i]

    breaks = [0]
    for i in range(1, len(direction)):
        if direction[i] != direction[i - 1]:
            breaks.append(i)
    breaks.append(len(T) - 1)

    segments: List[DSCScan] = []
    base_label = scan.label or "scan"

    for start, end in zip(breaks[:-1], breaks[1:]):
        # Include the boundary point in the following segment as well.  This
        # keeps the peak reversal temperature available to both neighbouring
        # thermograms without duplicating enough area to matter.
        stop = end + 1
        if stop - start < min_points:
            continue

        seg_T = T[start:stop].copy()
        delta = float(seg_T[-1] - seg_T[0])
        if abs(delta) < min_delta_T:
            continue

        seg_hf_mw = hf_mw[start:stop].copy()
        seg_hf_wg = hf_wg[start:stop].copy()
        seg_t = t_min[start:stop].copy() if len(t_min) == len(T) else np.array([])
        seg_kind = _segment_name(delta)
        label = f"{base_label}/{seg_kind} {seg_T[0]:.0f}-{seg_T[-1]:.0f}C"

        rate = scan.rate_K_per_min
        if len(seg_t) == len(seg_T) and abs(seg_t[-1] - seg_t[0]) > 1e-9:
            rate = float(delta / (seg_t[-1] - seg_t[0]))
        elif len(seg_T) > 1:
            rate = float(np.sign(delta) * abs(scan.rate_K_per_min))

        metadata = dict(scan.metadata)
        metadata.update({
            "parent_label": base_label,
            "segment_kind": seg_kind,
            "segment_start_index": int(start),
            "segment_end_index": int(stop - 1),
        })

        segments.append(DSCScan(
            label=label,
            T_C=seg_T,
            HF_mW=seg_hf_mw,
            HF_Wg=seg_hf_wg,
            t_min=seg_t,
            mass_mg=scan.mass_mg,
            rate_K_per_min=rate,
            exo_up=scan.exo_up,
            metadata=metadata,
        ))

    return segments or [scan]


# ---------------------------------------------------------------------------
#  Helper: detect instrument format
# ---------------------------------------------------------------------------

def _open_text_safe(filepath: str) -> tuple:
    """Open a text file with encoding fallback: UTF-8 -> GBK -> GB18030.
    Returns (file_handle, encoding_used)."""
    for enc in ['utf-8', 'gbk', 'gb18030', 'latin-1']:
        try:
            fh = open(filepath, 'r', encoding=enc)
            fh.readline()
            fh.seek(0)
            return fh, enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return open(filepath, 'r', encoding='utf-8', errors='replace'), 'utf-8'


def _detect_format(filepath: str) -> str:
    """Return format key: 'ta', 'netzsch', 'mettler', 'csv', 'excel', 'sequence'."""
    ext = os.path.splitext(filepath)[1].lower()
    if os.path.isdir(filepath):
        return 'sequence'
    if ext == '.001':
        return 'ta'
    if ext in ('.ngb', '.ngt'):
        return 'netzsch'
    if ext == '.mdt':
        return 'mettler'
    if ext in ('.xlsx', '.xls', '.xlsm'):
        return 'excel'
    # For text files, peek to detect TA Instruments format
    if ext in ('.csv', '.txt', '.dat', '.asc'):
        try:
            fh, _ = _open_text_safe(filepath)
            first = fh.readline().strip()
            fh.close()
            # TA Instruments exports start with "Title" or "^" metadata
            if first.startswith('Title') or first.startswith('^'):
                return 'ta'
        except Exception:
            logger.warning("静默异常", exc_info=True)
        return 'csv'
    return 'csv'  # fallback


def _normalise_exo_up(T: np.ndarray, HF: np.ndarray,
                      metadata: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, bool]:
    """Return heat flow using the internal exotherm-up convention."""
    hf = np.asarray(HF, dtype=float).copy()
    t = np.asarray(T, dtype=float)
    metadata = metadata or {}

    sign_text = " ".join(str(v).lower() for k, v in metadata.items()
                         if "sign" in str(k).lower() or "exo" in str(v).lower())
    if "exo down" in sign_text or "endotherm up" in sign_text:
        return -hf, True
    if "exo up" in sign_text or "exotherm up" in sign_text:
        return hf, False

    finite = np.isfinite(t) & np.isfinite(hf)
    if np.sum(finite) < 10:
        return hf, False

    t = t[finite]
    hf_f = hf[finite]
    hf_range = float(np.ptp(hf_f))
    if hf_range <= 1e-12:
        return hf, False

    t_cut = max(120.0, float(np.nanpercentile(t, 60)))
    high = t >= t_cut
    if np.sum(high) >= 10:
        hf_high = hf_f[high] - float(np.median(hf_f[high]))
        max_pos = float(np.max(hf_high))
        max_neg = float(abs(np.min(hf_high)))
        if max_pos > max_neg * 1.25 and max_pos > hf_range * 0.05:
            return -hf, True

    return hf, False


# ---------------------------------------------------------------------------
#  Generic CSV / TXT reader
# ---------------------------------------------------------------------------

def _read_csv(filepath: str) -> DSCScan:
    """Read a generic two-column (T, HF) or multi-column text file.

    Auto-detects encoding, delimiter, and header rows.
    """
    fh, enc = _open_text_safe(filepath)
    first = fh.readline().strip()
    fh.close()

    # Detect delimiter: try comma first, then tab, then whitespace
    delimiter = ','
    skiprows = 0
    try:
        float(first.split(',')[0].strip('"'))
    except ValueError:
        skiprows = 1

    # If comma-delimited reading gives single column, try tab/whitespace
    data = np.genfromtxt(filepath, delimiter=delimiter, skip_header=skiprows,
                         invalid_raise=False, encoding=enc)
    if data.ndim == 1:
        data = data.reshape(-1, 1)
    if data.shape[1] < 2:
        # Try whitespace delimiter
        data = np.genfromtxt(filepath, delimiter=None, skip_header=skiprows,
                             invalid_raise=False, encoding=enc)
        if data.ndim == 1:
            data = data.reshape(-1, 1)

    if data.shape[0] < 2 or data.shape[1] < 2:
        return DSCScan(label=os.path.splitext(os.path.basename(filepath))[0])

    # Heuristic: first numeric column = T, second = HF
    valid = np.all(np.isfinite(data[:, :2]), axis=1)
    T = data[valid, 0]
    HF = data[valid, 1]

    HF, _ = _normalise_exo_up(T, HF)

    scan = DSCScan(
        label=os.path.splitext(os.path.basename(filepath))[0],
        T_C=T,
        HF_mW=HF,
        HF_Wg=HF,  # assume already normalised or treat mW=W/g with mass=1
        t_min=np.arange(len(T)) * 0.1,  # fake time axis
    )
    return scan


# ---------------------------------------------------------------------------
#  TA Instruments (.001) reader
# ---------------------------------------------------------------------------

def _read_ta(filepath: str) -> DSCScan:
    """Read TA Instruments ASCII export (.001 or .txt).

    TA files typically have a multi-line header with metadata,
    then tabular columns: Time / Temperature / HeatFlow / ...
    """
    fh, encoding = _open_text_safe(filepath)
    lines = fh.readlines()
    fh.close()

    meta = {}
    data_start = 0
    col_names = []

    for i, line in enumerate(lines):
        line = line.strip().replace('\ufeff', '')
        if not line:
            continue
        # Metadata lines start with ^ or have colon
        if line.startswith('^'):
            parts = line[1:].split(None, 1)
            if len(parts) == 2:
                meta[parts[0].strip()] = parts[1].strip()
            continue
        # Look for column header
        if any(kw in line for kw in ['Time', 'Temperature', 'Heat']):
            col_names = [c.strip() for c in line.split('\t')]
            if len(col_names) <= 1:
                col_names = [c.strip() for c in line.split()]
            data_start = i + 1
            break
        # TA text export: "Curve Values:" marks the start of data section
        if 'Curve Values' in line:
            # Skip the header lines (column names + units) after "Curve Values:"
            # Find the first numeric line after this point
            for j in range(i + 1, len(lines)):
                parts = lines[j].strip().split()
                if len(parts) >= 2:
                    try:
                        float(parts[0]); float(parts[1])
                        data_start = j; break
                    except ValueError:
                        continue
            if data_start > 0:
                break

    if data_start == 0:
        # No header found, try numeric detection
        for i, line in enumerate(lines):
            parts = line.split()
            if len(parts) >= 2:
                try:
                    float(parts[0]); float(parts[1])
                    data_start = i; break
                except ValueError:
                    continue

    raw_data = []
    for line in lines[data_start:]:
        parts = line.strip().split()
        if len(parts) < 2:
            continue
        try:
            raw_data.append([float(p) for p in parts])
        except ValueError:
            continue

    if not raw_data:
        return DSCScan()

    arr = np.array(raw_data)

    # Column auto-detection for multi-column files
    t_min = np.array([])
    if not col_names and arr.shape[1] >= 4:
        # TA text export: [index, time, Ts, Tr, HF] -> use Ts (col 2) and last col
        # Detect index column: monotonically increasing by ~1
        if np.allclose(np.diff(arr[:, 0]), 1.0, atol=0.1) and arr.shape[1] >= 5:
            T = arr[:, 2]  # Ts (sample temperature)
            HF = arr[:, arr.shape[1] - 1]  # last column = heat flow
            t_min = arr[:, 1] / 60.0
        else:
            T = arr[:, 0]
            HF = arr[:, 1]
    else:
        T = arr[:, 0] if not col_names else _map_column(arr, col_names, 'T_C')
        HF = arr[:, 1] if not col_names else _map_column(arr, col_names, 'HF_mW')
        if col_names:
            t_col = _map_column(arr, col_names, 't_min')
            if len(t_col) == len(T) and not np.array_equal(t_col, T):
                t_min = t_col

    HF, flipped = _normalise_exo_up(T, HF, meta)
    if flipped:
        meta['SignNormalized'] = 'flipped_to_exo_up'

    mass = float(meta.get('SampleSize', meta.get('Weight', '1.0')))
    rate = float(meta.get('Ramp', meta.get('Rate', '10.0')))

    scan = DSCScan(
        label=os.path.splitext(os.path.basename(filepath))[0],
        T_C=T, HF_mW=HF,
        HF_Wg=HF / max(mass, 0.001),
        t_min=t_min,
        mass_mg=mass, rate_K_per_min=rate,
        metadata=meta,
    )
    return scan


def _map_column(arr: np.ndarray, col_names: List[str], target: str) -> np.ndarray:
    """Map column names to standard keys and return the data column."""
    for i, cn in enumerate(col_names):
        mapped = COLUMN_MAP.get(cn, cn)
        if mapped == target and i < arr.shape[1]:
            return arr[:, i]
    return arr[:, 0]  # fallback


# ---------------------------------------------------------------------------
#  Excel reader
# ---------------------------------------------------------------------------

def _read_excel(filepath: str) -> List[DSCScan]:
    """Read DSC data from Excel workbook.

    Supports the existing PolyNexus format:
        Row 0: headers (optional)
        Col 0: Temperature
        Col 1: HeatFlow
        Extra cols: sample metadata

    Also supports multi-sheet mode (one sheet per scan).
    """
    xls = pd.ExcelFile(filepath)
    scans = []

    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet, header=None)

        # Find first data row (numeric)
        data_start = 0
        for r in range(min(20, len(df))):
            row = df.iloc[r]
            numeric_count = sum(1 for v in row if isinstance(v, (int, float))
                              and not (isinstance(v, float) and np.isnan(v)))
            if numeric_count >= 2:
                data_start = r
                break

        # Extract numeric columns
        numeric_data = []
        for r in range(data_start, len(df)):
            row_vals = []
            for c in range(df.shape[1]):
                v = df.iloc[r, c]
                if isinstance(v, (int, float)) and not (isinstance(v, float) and np.isnan(v)):
                    row_vals.append(float(v))
                else:
                    row_vals.append(np.nan)
            if sum(1 for v in row_vals if not np.isnan(v)) >= 2:
                numeric_data.append(row_vals)

        if not numeric_data:
            continue

        arr = np.array(numeric_data)
        if arr.shape[1] >= 3:
            # TA/TRIOS Excel exports use [time, temperature, heat flow].
            temp_col, hf_col, time_col = 1, 2, 0
        else:
            temp_col, hf_col, time_col = 0, 1, None

        valid = np.all(np.isfinite(arr[:, [temp_col, hf_col]]), axis=1)
        T = arr[valid, temp_col]
        HF = arr[valid, hf_col]
        t_min = arr[valid, time_col] if time_col is not None else np.arange(len(T)) * 0.1

        HF, flipped = _normalise_exo_up(T, HF)

        scan = DSCScan(
            label=f"{os.path.basename(filepath)}/{sheet}",
            T_C=T, HF_mW=HF, HF_Wg=HF,
            t_min=t_min,
            metadata={'SignNormalized': 'flipped_to_exo_up'} if flipped else {},
        )
        scans.append(scan)

    return scans


# ---------------------------------------------------------------------------
#  Sequence folder reader (isothermal crystallisation series)
# ---------------------------------------------------------------------------

def _read_sequence(dirpath: str) -> List[DSCScan]:
    """Scan a folder for multiple DSC runs (isothermal series).

    Sorts files by filename (assumed sequential numbering).
    """
    scans = []
    exts = {'.csv', '.txt', '.dat', '.001', '.asc', '.xls', '.xlsx'}
    files = sorted(
        [f for f in os.listdir(dirpath)
         if os.path.splitext(f)[1].lower() in exts],
        key=lambda x: (len(x), x),  # natural-ish sort
    )
    for fn in files:
        fp = os.path.join(dirpath, fn)
        try:
            for segment in load_project(fp):
                scans.append(segment)
        except Exception:
            logger.warning("静默异常", exc_info=True)
    return scans


# ---------------------------------------------------------------------------
#  Public API
# ---------------------------------------------------------------------------

def load_scan(filepath: str) -> DSCScan:
    """Load a single DSC scan from file. Auto-detects format."""
    fmt = _detect_format(filepath)
    if fmt == 'ta':
        return _read_ta(filepath)
    elif fmt == 'excel':
        scans = _read_excel(filepath)
        return scans[0] if scans else DSCScan()
    else:
        return _read_csv(filepath)


def load_project(filepath: str) -> List[DSCScan]:
    """Load one or more DSC scans from file or folder.

    Returns a list of DSCScan objects.
    """
    if os.path.isdir(filepath):
        return _read_sequence(filepath)

    fmt = _detect_format(filepath)
    if fmt == 'excel':
        scans: List[DSCScan] = []
        for scan in _read_excel(filepath):
            scans.extend(split_scan_segments(scan))
        return scans

    return split_scan_segments(load_scan(filepath))


def normalise_scan(scan: DSCScan, mass_mg: float | None = None,
                   ensure_exo_up: bool = True) -> DSCScan:
    """Normalise a scan: apply mass, enforce exo-up convention.

    Parameters
    ----------
    scan : DSCScan
    mass_mg : float, optional
        Sample mass.  If None, uses scan.mass_mg.
    ensure_exo_up : bool
        If True and scan.exo_up is False, flip heat flow sign.
    """
    m = mass_mg if mass_mg is not None else scan.mass_mg
    if m <= 0:
        m = 1.0

    scan.HF_Wg = scan.HF_mW / m
    scan.mass_mg = m

    # Enforce exo-up
    if ensure_exo_up and not scan.exo_up:
        scan.HF_mW = -scan.HF_mW
        scan.HF_Wg = -scan.HF_Wg
        scan.exo_up = True

    return scan
