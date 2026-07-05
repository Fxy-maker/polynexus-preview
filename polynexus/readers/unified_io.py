"""
Unified I/O utilities for PolyNexus.
Shared table loader replacing duplicated logic in saxs/ir/nmr/dsc io.py.
"""

import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_EXT_MAP = {
    ".csv": "csv",
    ".tsv": "csv",
    ".txt": "text",
    ".dat": "text",
    ".asc": "text",
    ".xy": "text",
    ".chi": "text",
    ".xlsx": "excel",
    ".xls": "excel",
    ".xlsm": "excel",
    ".edf": "edf",
    ".edf.gz": "edf",
    ".cbf": "cbf",
    ".tif": "image",
    ".tiff": "image",
    ".spa": "text",
    ".spc": "text",
    ".fid": "text",
    ".ta": "text",
    ".tai": "text",
    ".001": "text",
    ".h5": "hdf5",
    ".hdf5": "hdf5",
    ".nxs": "hdf5",
}


def detect_format(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    fmt = _EXT_MAP.get(ext, "text")
    if fmt == "text" and os.path.getsize(filepath) < 50_000_000:
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                head = f.read(4096)
            commas, tabs = head.count(","), head.count("\t")
            if commas > tabs and commas > 3:
                return "csv"
            if tabs > commas and tabs > 3:
                return "csv"
        except Exception:
            logger.warning("Unified reader delimiter sniff failed; keeping detected format.", exc_info=True)
    return fmt


def load_table(
    filepath: str,
    has_header: Optional[bool] = None,
    delimiter: Optional[str] = None,
    skip_rows: int = 0,
) -> Tuple[List[str], np.ndarray]:
    fmt = detect_format(filepath)
    if fmt in ("csv", "excel"):
        try:
            if fmt == "excel":
                df = pd.read_excel(filepath, header=None if has_header is False else "infer")
            else:
                df = pd.read_csv(
                    filepath,
                    sep=delimiter or ",",
                    header=None if has_header is False else "infer",
                    skiprows=skip_rows,
                    comment="#",
                    on_bad_lines="skip",
                )
            df = df.apply(pd.to_numeric, errors="coerce")
            df = df.dropna(axis=1, how="all").dropna(axis=0, how="all")
            if not df.empty:
                return list(df.columns.astype(str)), df.values.astype(np.float64)
        except Exception:
            logger.warning("Unified reader pandas table load failed; trying numpy loader.", exc_info=True)

    try:
        data = np.genfromtxt(
            filepath,
            comments=["#", "%", "!"],
            delimiter=delimiter,
            skip_header=skip_rows,
            invalid_raise=False,
        )
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        if data.size > 0:
            cols = [f"col_{i}" for i in range(data.shape[1])]
            return cols, data.astype(np.float64)
    except Exception:
        logger.warning("Unified reader numpy table load failed; trying line-by-line parser.", exc_info=True)

    return _line_by_line(filepath, skip_rows)


def _line_by_line(filepath: str, skip_rows: int = 0) -> Tuple[List[str], np.ndarray]:
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    lines = lines[skip_rows:]
    if not lines:
        raise ValueError("Empty file")

    delims = [",", "\t", ";"]
    dc = {d: sum(l.count(d) for l in lines[:10]) for d in delims}
    best = max(dc, key=dc.get)
    if dc[best] < 2 and best == ",":
        best = None

    num_re = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")
    data_start = 0
    for i, line in enumerate(lines):
        if len(num_re.findall(line)) >= 2:
            data_start = i
            break

    header: List[str] = []
    if data_start > 0:
        hdr = lines[data_start - 1].strip()
        if len(num_re.findall(hdr)) < 2:
            header = [h.strip() for h in (hdr.split(best) if best else hdr.split()) if h.strip()]

    rows = []
    for line in lines[data_start:]:
        parts = re.split(best or r"\s+", line.strip())
        nums = []
        for part in parts:
            try:
                nums.append(float(part))
            except ValueError:
                nums.append(np.nan)
        if sum(1 for value in nums if not np.isnan(value)) >= 2:
            rows.append(nums)

    if not rows:
        raise ValueError("No numeric data")

    arr = np.array(rows, dtype=np.float64)
    ncols = arr.shape[1]
    if not header:
        header = [f"col_{i}" for i in range(ncols)]
    elif len(header) < ncols:
        header += [f"col_{i}" for i in range(len(header), ncols)]
    return header[:ncols], arr
