from __future__ import annotations

import logging
import threading
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

logger = logging.getLogger(__name__)

_GUI_BACKEND_MARKERS = ("qt", "tk", "wx", "gtk", "macosx")


def _downsample_plot(x, y, max_pts=800):
    """Downsample data for plotting to keep SVG path sizes manageable."""
    x_arr = np.asarray(x)
    y_arr = np.asarray(y)
    if len(x_arr) <= max_pts:
        return x_arr, y_arr
    indices = np.linspace(0, len(x_arr) - 1, max_pts, dtype=int)
    return x_arr[indices], y_arr[indices]


def _remove_stale_variant(path: Path) -> None:
    """Remove the opposite LOW/non-LOW variant before writing a refreshed figure."""
    stem = path.stem
    suffix = path.suffix
    if stem.endswith("_LOW"):
        counterpart = path.with_name(f"{stem[:-4]}{suffix}")
    else:
        counterpart = path.with_name(f"{stem}_LOW{suffix}")
    if counterpart == path:
        return
    try:
        if counterpart.exists():
            counterpart.unlink()
    except Exception:
        logger.warning("Failed to remove stale SAXS figure variant: %s", counterpart, exc_info=True)


def _ensure_non_gui_backend() -> None:
    """Force a non-GUI backend when plotting from a worker thread."""
    try:
        backend = str(matplotlib.get_backend() or "").lower()
    except Exception:
        backend = ""
    if threading.current_thread() is threading.main_thread():
        return
    if backend == "agg":
        return
    if any(marker in backend for marker in _GUI_BACKEND_MARKERS):
        try:
            plt.switch_backend("Agg")
        except Exception:
            logger.warning("Failed to switch Matplotlib backend to Agg in SAXS worker thread.", exc_info=True)


def _safe_legend(ax, *args, **kwargs):
    """Only draw a legend when there is something meaningful to show."""
    if args:
        if len(args) >= 2 and hasattr(args[1], "__iter__"):
            labels = [str(label).strip() for label in args[1] if str(label).strip()]
            if not labels:
                return None
        return ax.legend(*args, **kwargs)
    handles, labels = ax.get_legend_handles_labels()
    visible = [
        (handle, label)
        for handle, label in zip(handles, labels)
        if str(label).strip() and not str(label).startswith("_")
    ]
    if not visible:
        return None
    handles, labels = zip(*visible)
    return ax.legend(handles, labels, **kwargs)


def _make_output_dirs(output_dir: str):
    """Create SCI-standard output directory structure."""
    root = Path(output_dir).resolve()
    dirs = [
        "summary",
        "figures/SI",
        "data/parameters",
        "data/raw_1d",
        "data/fit_results",
        "report",
    ]
    for directory in dirs:
        (root / directory).mkdir(parents=True, exist_ok=True)
    return root
