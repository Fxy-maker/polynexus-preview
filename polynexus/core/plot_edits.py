"""Persistent figure edit state and matplotlib application helpers."""

from __future__ import annotations
import logging
logger = logging.getLogger(__name__)


import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple

from ..utils.config import get_user_config_dir


STATE_FILENAME = "plot_edits.json"
STYLE_PRESETS_FILENAME = "chart_style_presets.json"

COLOUR_SCHEMES = {
    "Default Blue": ("#2166AC", "#B2182B", "#1B7837", "#E69F00", "#762A83"),
    "Viridis": ("#440154", "#3B528B", "#21918C", "#5EC962", "#FDE725"),
    "Warm": ("#8B0000", "#CD5C5C", "#F4A460", "#FFD700", "#FF6347"),
    "Cool": ("#0D3B66", "#1A659E", "#4A9EC8", "#7FC8F8", "#BFDFFF"),
    "Mono": ("#222222", "#555555", "#888888", "#BBBBBB", "#DDDDDD"),
    "Nature": ("#1B4332", "#40916C", "#52B788", "#95D5B2", "#D8F3DC"),
    "Sunset": ("#FF6B35", "#F7931E", "#FDC830", "#F37335", "#C02425"),
    "Ocean": ("#003049", "#005F73", "#0A9396", "#94D2BD", "#E9D8A5"),
    "Wong (SCI)": ("#0072B2", "#D55E00", "#009E73", "#E69F00", "#CC79A7", "#000000", "#56B4E9", "#F0E442"),
}

FONT_SIZES = {"Small": 8, "Normal": 10, "Medium": 12, "Large": 14, "XL": 16}
LINE_WIDTHS = {
    "Thin": 0.5,
    "Normal": 1.0,
    "Medium": 1.5,
    "Thick": 2.0,
    "Heavy": 3.0,
}
FIGURE_SIZES = {
    "Small (4in)": (4, 3),
    "Medium (6in)": (6, 4),
    "Large (8in)": (8, 5),
    "Wide (10in)": (10, 5),
    "Square": (5, 5),
}

_FIGURE_ROOT_DIRS = {"figures", "summary", "per_frame"}


def style_presets_path() -> Path:
    return get_user_config_dir() / STYLE_PRESETS_FILENAME


def load_style_presets() -> Dict[str, Any]:
    path = style_presets_path()
    if not path.exists():
        return {"version": 1, "presets": {}}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {"version": 1, "presets": {}}
    if not isinstance(data, dict):
        return {"version": 1, "presets": {}}
    presets = data.get("presets")
    if not isinstance(presets, dict):
        data["presets"] = {}
    data.setdefault("version", 1)
    return data


def list_style_presets() -> list[str]:
    data = load_style_presets()
    presets = data.get("presets", {})
    if not isinstance(presets, dict):
        return []
    return sorted(
        [name for name, payload in presets.items() if isinstance(payload, dict)],
        key=lambda value: value.lower(),
    )


def load_style_preset(name: str) -> Dict[str, Any]:
    preset_name = str(name or "").strip()
    if not preset_name:
        return {}
    data = load_style_presets()
    payload = data.get("presets", {}).get(preset_name, {})
    if not isinstance(payload, dict):
        return {}
    style = payload.get("style", payload)
    return style if isinstance(style, dict) else {}


def save_style_preset(name: str, style: Dict[str, Any]) -> Tuple[Path, str]:
    preset_name = str(name or "").strip()
    if not preset_name:
        raise ValueError("Preset name is required.")
    if not isinstance(style, dict) or not style:
        raise ValueError("Style payload is required.")

    data = load_style_presets()
    presets = data.setdefault("presets", {})
    presets[preset_name] = {
        "name": preset_name,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "style": style,
    }
    path = style_presets_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path, preset_name


def delete_style_preset(name: str) -> bool:
    preset_name = str(name or "").strip()
    if not preset_name:
        return False

    data = load_style_presets()
    presets = data.get("presets", {})
    if not isinstance(presets, dict) or preset_name not in presets:
        return False

    del presets[preset_name]
    path = style_presets_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return True


def figure_output_root(figure_path: str) -> Path:
    """Return the analysis output root for an exported figure."""
    path = Path(figure_path).resolve()
    parts = path.parts
    for idx in range(len(parts) - 1, -1, -1):
        if parts[idx].lower() in _FIGURE_ROOT_DIRS:
            return Path(*parts[:idx])
    return path.parent


def figure_state_path(figure_path: str) -> Path:
    return figure_output_root(figure_path) / STATE_FILENAME


def figure_state_key(figure_path: str) -> str:
    path = Path(figure_path).resolve()
    root = figure_output_root(str(path))
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def load_plot_edits(figure_path: str) -> Dict[str, Any]:
    state_path = figure_state_path(figure_path)
    if not state_path.exists():
        return {"version": 1, "files": {}}
    try:
        with state_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        logger.warning("Plot edit state load failed; using empty state.", exc_info=True)
        return {"version": 1, "files": {}}
    if not isinstance(data, dict):
        return {"version": 1, "files": {}}
    data.setdefault("version", 1)
    data.setdefault("files", {})
    return data


def load_figure_edit(figure_path: str) -> Dict[str, Any]:
    data = load_plot_edits(figure_path)
    entry = data.get("files", {}).get(figure_state_key(figure_path), {})
    style = entry.get("style", {})
    return style if isinstance(style, dict) else {}


def save_figure_edit(figure_path: str, style: Dict[str, Any]) -> Tuple[Path, str]:
    data = load_plot_edits(figure_path)
    key = figure_state_key(figure_path)
    files = data.setdefault("files", {})
    files[key] = {
        "relative_path": key,
        "source_path": str(Path(figure_path).resolve()),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "style": style,
    }
    state_path = figure_state_path(figure_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with state_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return state_path, key


def apply_figure_edit(fig, figure_path: str):
    """Apply saved edit style to a matplotlib Figure before export."""
    style = load_figure_edit(figure_path)
    if not style:
        return fig

    bg_color = style.get("bg_color")
    if bg_color:
        fig.set_facecolor(bg_color)

    fig_size = FIGURE_SIZES.get(style.get("figure_size", ""))
    if fig_size:
        fig.set_size_inches(*fig_size, forward=True)

    font_size = FONT_SIZES.get(style.get("font", ""))
    title_size = (font_size + 2) if font_size else None
    label_size = font_size
    tick_size = max(6, font_size - 1) if font_size else None

    palette = COLOUR_SCHEMES.get(style.get("colour_scheme", ""))
    line_width = LINE_WIDTHS.get(style.get("line_width", ""))
    grid_on = style.get("grid_on")
    grid_alpha = style.get("grid_alpha", 0.2)

    title = style.get("title")
    xlabel = style.get("xlabel")
    ylabel = style.get("ylabel")

    for ax_idx, ax in enumerate(fig.get_axes()):
        if bg_color:
            ax.set_facecolor(bg_color)

        if ax_idx == 0:
            if title:
                ax.set_title(title)
            if xlabel:
                ax.set_xlabel(xlabel)
            if ylabel:
                ax.set_ylabel(ylabel)

        if title_size and ax.get_title():
            ax.title.set_fontsize(title_size)
            ax.title.set_fontweight("bold")
        if label_size:
            ax.xaxis.label.set_fontsize(label_size)
            ax.yaxis.label.set_fontsize(label_size)
        if tick_size:
            ax.tick_params(labelsize=tick_size)

        if palette:
            for i, line in enumerate(ax.lines):
                line.set_color(palette[i % len(palette)])
        if line_width:
            for line in ax.lines:
                line.set_linewidth(line_width)

        if grid_on is not None:
            if bool(grid_on):
                ax.grid(True, alpha=float(grid_alpha or 0.2))
            else:
                ax.grid(False)

    return fig


def savefig_with_edits(fig, path: str, **savefig_kwargs):
    """Apply sidecar edits, then save a matplotlib figure."""
    style = load_figure_edit(path)
    apply_figure_edit(fig, path)
    if style.get("bg_color") and "facecolor" in savefig_kwargs:
        savefig_kwargs["facecolor"] = style["bg_color"]
    fig.savefig(path, **savefig_kwargs)
