"""Rigaku .raw XRD reader for PolyNexus.

Supports RAW1.01 format (SmartLab / Ultima series).

Layout:
    Bytes   0-  7: magic "RAW1.01\0"
    Bytes   8- 11: flags (uint32_le)
    Bytes  12- 15: measurement count (uint32_le)
    Bytes  16- 23: date (8 bytes, "MM/DD/YY")
    Bytes  24- 25: padding
    Bytes  26- 33: time (8 bytes, "HH:MM:SS")
    Bytes  34- 35: padding
    Bytes  36- ~ :  operator name (null-terminated)
    Padding to 512
    Bytes 512-1027: condition block
    Bytes 1028- :    float32_le intensity data
"""
import logging
logger = logging.getLogger(__name__)

import struct
import numpy as np
from typing import Tuple, Dict


def read_raw_rigaku(filepath: str) -> Tuple[np.ndarray, np.ndarray, Dict]:
    """Read a Rigaku .raw XRD file (RAW1.01).

    Returns (two_theta_deg, intensity, metadata).
    """
    with open(filepath, "rb") as fh:
        data = fh.read()

    if len(data) < 520:
        raise ValueError("File too small for .raw format")

    magic = data[:8]
    if magic != b"RAW1.01\x00":
        raise ValueError(f"Not RAW1.01 (magic={magic!r})")

    meta = {}

    # Date: bytes 16-23 (8 bytes fixed)
    meta["date"] = data[16:24].decode("latin-1", errors="replace").strip("\x00").strip()
    # Time: bytes 26-33 (8 bytes fixed)
    meta["time"] = data[26:34].decode("latin-1", errors="replace").strip("\x00").strip()
    # Operator: starts at byte 36, null-terminated
    end = data.find(b"\x00", 36)
    meta["operator"] = data[36:end].decode("latin-1", errors="replace").strip() if end > 36 else ""

    # Intensity data at offset 1028 (float32_le)
    data_start = 1028
    if len(data) <= data_start + 8:
        return _generic_scan(data, meta)

    n_floats = (len(data) - data_start) // 4
    if n_floats < 30:
        return _generic_scan(data, meta)

    raw = struct.unpack(f"<{n_floats}f", data[data_start:])
    I_all = np.array(raw, dtype=float)
    valid = np.isfinite(I_all) & (I_all >= 0)
    I = I_all[valid]
    n_points = len(I)

    if n_points < 30:
        return _generic_scan(data, meta)

    # Reconstruct 2theta: Rigaku SmartLab default 5-80deg, 0.02deg step
    # Verified: PA6 alpha1 at idx~760 => 5+760*0.02=20.2deg
    start_deg, step_deg = _extract_scan_params(data, n_points)

    two_theta = np.arange(start_deg, start_deg + n_points * step_deg, step_deg)
    two_theta = two_theta[:n_points]

    return two_theta, I, meta


def _extract_scan_params(data: bytes, n_points: int) -> Tuple[float, float]:
    """Extract scan start/step from condition block, or use validated defaults."""
    start_deg = 5.0
    step_deg = 0.02

    if len(data) < 1024:
        return start_deg, step_deg

    candidates = []
    for i in range(512, min(1024, len(data) - 3), 4):
        try:
            v = struct.unpack("<f", data[i:i + 4])[0]
            if 1.0 < abs(v) < 130.0:
                candidates.append(v)
        except Exception:
            logger.warning("RAW reader metadata candidate parse failed.", exc_info=True)

    starts = [v for v in candidates if 2.0 <= v <= 15.0]
    ends = [v for v in candidates if 50.0 <= v <= 120.0]

    if starts and ends:
        s = min(starts)
        e = max(ends)
        if e > s and n_points > 1:
            step_deg = (e - s) / (n_points - 1)
            start_deg = s

    return start_deg, step_deg


def _generic_scan(data: bytes, meta: Dict) -> Tuple[np.ndarray, np.ndarray, Dict]:
    """Fallback: scan for 2theta/I float pairs."""
    scan_start = max(len(meta) + 30, 512)
    for fmt, sz in [("f", 4), ("d", 8)]:
        try:
            aligned = scan_start + (sz - scan_start % sz) % sz
            n_vals = (len(data) - aligned) // sz
            if n_vals < 10:
                continue
            raw = struct.unpack(f"<{n_vals}{fmt}", data[aligned:])
            tth = np.array(raw[::2])
            I_arr = np.array(raw[1::2])
            if np.all(np.diff(tth[:5]) > 0) and 0 < tth[0] < 180:
                mask = (I_arr > 0) & np.isfinite(I_arr)
                return tth[mask], I_arr[mask], meta
        except Exception:
            logger.warning("RAW reader numeric payload parse attempt failed.", exc_info=True)
    raise ValueError("Cannot parse .raw file")
