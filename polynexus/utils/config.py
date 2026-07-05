"""
Central configuration system for PolyNexus.

All technique-specific defaults live here.
Supports JSON config file loading and runtime override.
"""

import copy
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Tuple, Optional, List
import numpy as np


DEFAULTS_PATH = Path(__file__).resolve().parents[2] / "config" / "defaults.json"
KNOWN_POLYMERS = ["PA66", "PEEK", "PVDF", "PEK", "PET", "PLA", "PA6", "PE", "PP"]
CONFIG_PRESETS_FILENAME = "config_presets.json"
BATCH_PRESETS_FILENAME = "batch_presets.json"
BATCH_LAST_RUN_FILENAME = "batch_last_run.json"


def detect_polymer_type(sample_name: str) -> str:
    """
    Detect a polymer type from the sample name.

    Returns ``unknown`` when no known polymer token is present.
    """
    name_upper = str(sample_name or "").upper()
    for polymer in KNOWN_POLYMERS:
        if polymer in name_upper:
            return polymer
    return "unknown"


def load_defaults(polymer_type: str = "unknown") -> Dict[str, Dict]:
    """
    Load polymer-scoped defaults from ``config/defaults.json``.

    Falls back to the ``unknown`` profile when the polymer is not configured.
    """
    try:
        with DEFAULTS_PATH.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

    profiles = data.get("polymers", {})
    polymer_key = str(polymer_type or "unknown").upper()
    selected = profiles.get(polymer_key) or profiles.get("unknown") or {}
    return copy.deepcopy(selected)


def get_user_config_dir() -> Path:
    """Return the user-scoped configuration directory for PolyNexus."""
    override = os.getenv("POLYNEXUS_USER_CONFIG_DIR", "").strip()
    if override:
        return Path(override).expanduser()

    appdata = os.getenv("APPDATA", "").strip()
    if appdata:
        return Path(appdata) / "PolyNexus"

    xdg = os.getenv("XDG_CONFIG_HOME", "").strip()
    if xdg:
        return Path(xdg) / "PolyNexus"

    return Path.home() / ".polynexus"


def _config_presets_path() -> Path:
    return get_user_config_dir() / CONFIG_PRESETS_FILENAME


def _read_config_preset_store() -> dict:
    path = _config_presets_path()
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"version": 1, "config_presets": {}}

    if not isinstance(data, dict):
        return {"version": 1, "config_presets": {}}

    presets = data.get("config_presets")
    if not isinstance(presets, dict):
        data["config_presets"] = {}
    data.setdefault("version", 1)
    return data


def _write_config_preset_store(data: dict) -> None:
    path = _config_presets_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def list_config_presets(technique: str, submodule: str) -> List[str]:
    """List saved preset names for the given technique/submodule scope."""
    store = _read_config_preset_store()
    scoped = (
        store.get("config_presets", {})
        .get(str(technique or ""), {})
        .get(str(submodule or ""), {})
    )
    if not isinstance(scoped, dict):
        return []
    return sorted(
        [name for name, payload in scoped.items() if isinstance(payload, dict)],
        key=lambda value: value.lower(),
    )


def load_config_preset(technique: str, submodule: str, name: str) -> Optional[Dict]:
    """Load a saved config preset and return a detached copy of its values."""
    preset_name = str(name or "").strip()
    if not preset_name:
        return None

    store = _read_config_preset_store()
    payload = (
        store.get("config_presets", {})
        .get(str(technique or ""), {})
        .get(str(submodule or ""), {})
        .get(preset_name)
    )
    if not isinstance(payload, dict):
        return None

    values = payload.get("values", payload)
    if not isinstance(values, dict):
        return None
    return copy.deepcopy(values)


def save_config_preset(technique: str, submodule: str, name: str, values: Dict) -> None:
    """Persist a named config preset for the given technique/submodule scope."""
    preset_name = str(name or "").strip()
    if not preset_name:
        raise ValueError("Preset name is required.")
    if not isinstance(values, dict) or not values:
        raise ValueError("Preset values are required.")

    store = _read_config_preset_store()
    presets = store.setdefault("config_presets", {})
    tech_bucket = presets.setdefault(str(technique or ""), {})
    submodule_bucket = tech_bucket.setdefault(str(submodule or ""), {})
    submodule_bucket[preset_name] = {
        "name": preset_name,
        "values": copy.deepcopy(values),
    }
    _write_config_preset_store(store)


def delete_config_preset(technique: str, submodule: str, name: str) -> bool:
    """Delete a saved config preset. Returns True when a preset was removed."""
    preset_name = str(name or "").strip()
    if not preset_name:
        return False

    store = _read_config_preset_store()
    presets = store.get("config_presets", {})
    tech_key = str(technique or "")
    submodule_key = str(submodule or "")
    tech_bucket = presets.get(tech_key)
    if not isinstance(tech_bucket, dict):
        return False
    submodule_bucket = tech_bucket.get(submodule_key)
    if not isinstance(submodule_bucket, dict):
        return False
    if preset_name not in submodule_bucket:
        return False

    del submodule_bucket[preset_name]
    if not submodule_bucket:
        tech_bucket.pop(submodule_key, None)
    if not tech_bucket:
        presets.pop(tech_key, None)
    _write_config_preset_store(store)
    return True


def _batch_presets_path() -> Path:
    return get_user_config_dir() / BATCH_PRESETS_FILENAME


def _read_batch_preset_store() -> dict:
    path = _batch_presets_path()
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"version": 1, "batch_presets": {}}

    if not isinstance(data, dict):
        return {"version": 1, "batch_presets": {}}

    presets = data.get("batch_presets")
    if not isinstance(presets, dict):
        data["batch_presets"] = {}
    data.setdefault("version", 1)
    return data


def _write_batch_preset_store(data: dict) -> None:
    path = _batch_presets_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def list_batch_presets() -> List[str]:
    """List saved batch preset names."""
    store = _read_batch_preset_store()
    presets = store.get("batch_presets", {})
    if not isinstance(presets, dict):
        return []
    return sorted(
        [name for name, payload in presets.items() if isinstance(payload, dict)],
        key=lambda value: value.lower(),
    )


def load_batch_preset(name: str) -> Optional[Dict]:
    """Load a saved batch preset by name."""
    preset_name = str(name or "").strip()
    if not preset_name:
        return None

    store = _read_batch_preset_store()
    payload = store.get("batch_presets", {}).get(preset_name)
    if not isinstance(payload, dict):
        return None

    values = payload.get("values", payload)
    if not isinstance(values, dict):
        return None
    return copy.deepcopy(values)


def save_batch_preset(name: str, values: Dict) -> None:
    """Persist a named batch preset."""
    preset_name = str(name or "").strip()
    if not preset_name:
        raise ValueError("Preset name is required.")
    if not isinstance(values, dict) or not values:
        raise ValueError("Preset values are required.")

    store = _read_batch_preset_store()
    presets = store.setdefault("batch_presets", {})
    presets[preset_name] = {
        "name": preset_name,
        "values": copy.deepcopy(values),
    }
    _write_batch_preset_store(store)


def delete_batch_preset(name: str) -> bool:
    """Delete a saved batch preset. Returns True when deleted."""
    preset_name = str(name or "").strip()
    if not preset_name:
        return False

    store = _read_batch_preset_store()
    presets = store.get("batch_presets", {})
    if not isinstance(presets, dict) or preset_name not in presets:
        return False

    del presets[preset_name]
    _write_batch_preset_store(store)
    return True


def _batch_last_run_path() -> Path:
    return get_user_config_dir() / BATCH_LAST_RUN_FILENAME


def load_batch_last_run() -> Optional[Dict]:
    """Load the most recent batch run snapshot."""
    path = _batch_last_run_path()
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

    if not isinstance(data, dict):
        return None

    values = data.get("values", data)
    if not isinstance(values, dict):
        return None
    return copy.deepcopy(values)


def save_batch_last_run(values: Dict) -> None:
    """Persist the most recent batch run snapshot."""
    if not isinstance(values, dict) or not values:
        raise ValueError("Last-run values are required.")

    path = _batch_last_run_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "values": copy.deepcopy(values)}
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


@dataclass
class GlobalConfig:
    """Global settings shared across all techniques."""
    # Output
    output_dir: str = ""
    save_figures: bool = True
    figure_format: str = "pdf"          # pdf | png | svg
    figure_dpi: int = 300

    # Data
    data_dir: str = ""
    background_file: str = ""

    # Smoothing
    smooth_method: str = "savgol"       # savgol | moving_average | none
    savgol_window: int = 7
    savgol_order: int = 2

    # Logging
    verbose: bool = True


@dataclass
class DSCConfig:
    """Differential Scanning Calorimetry."""
    standard_enthalpy: float = 293.0     # J/g (PE standard)
    smooth_span: int = 5
    min_prominence: float = 0.3
    tg_search_min: float = -50.0
    tg_search_max: float = 150.0
    heating_rate_k_min: float = 10.0


@dataclass
class IRConfig:
    """Infrared Spectroscopy."""
    baseline_method: str = "als"         # als | linear | rubberband | none
    wavenumber_min: float = 400.0
    wavenumber_max: float = 4000.0
    smooth_window: int = 11
    smooth_order: int = 3
    peak_min_prominence: float = 0.01
    normalize: bool = True
    absorbance_mode: bool = True


@dataclass
class WAXSConfig:
    """Wide-Angle X-ray Scattering (1D and 2D)."""
    wavelength_nm: float = 0.154056      # Cu K-alpha
    fit_type: str = "pvoigt"             # pvoigt | gauss | lorentz
    sdd_mm: float = 60.0                 # for 2D
    pixel_size_mm: float = 0.075
    crystallinity_model: str = "auto"    # auto | pa6 | generic


@dataclass
class SAXSConfig:
    """Small-Angle X-ray Scattering."""
    # Geometry (overridden by EDF header or poni file)
    wavelength_m: float = 1.541891e-10
    pixel_size_m: float = 75e-6
    sdd_m: float = 0.450
    beam_center_x: float = 255.43
    beam_center_y: float = 549.73
    poni_file: str = ""

    # Integration
    q_min: float = 0.02
    q_max: float = 2.5
    n_pt: int = 1000
    use_pyfai: bool = False              # manual numpy by default

    # Analysis
    q_bragg_min: float = 0.15
    q_bragg_max: float = 0.9
    q_corr_min: float = 0.05
    q_corr_max: float = 2.0
    L_search_min: float = 5.0
    L_search_max: float = 20.0

    # Porod / Kratky
    q_porod_min: float = 1.0
    q_porod_max: float = 2.2
    do_porod: bool = True
    do_kratky: bool = True

    # Experiment type
    experiment_type: str = "static"      # static | strain | temperature


@dataclass
class NMRConfig:
    """Solid-State NMR."""
    lb_hz: float = 5.0
    exp_type: str = "CPMAS"              # CPMAS | SinglePulse | Auto
    do_crystallinity: bool = True
    peak_thresh_ratio: float = 0.15
    min_dist_ppm: float = 2.0


@dataclass
class ProjectConfig:
    """Master configuration aggregating all technique configs."""
    global_cfg: GlobalConfig = field(default_factory=GlobalConfig)
    dsc: DSCConfig = field(default_factory=DSCConfig)
    ir: IRConfig = field(default_factory=IRConfig)
    waxs: WAXSConfig = field(default_factory=WAXSConfig)
    saxs: SAXSConfig = field(default_factory=SAXSConfig)
    nmr: NMRConfig = field(default_factory=NMRConfig)

    @classmethod
    def from_json(cls, path: str) -> "ProjectConfig":
        """Load from JSON config file."""
        import json
        with open(path, 'r') as f:
            data = json.load(f)
        cfg = cls()
        for section in ['global', 'dsc', 'ir', 'waxs', 'saxs', 'nmr']:
            if section in data:
                target = cfg.global_cfg if section == 'global' else getattr(cfg, section)
                for k, v in data[section].items():
                    if hasattr(target, k):
                        setattr(target, k, v)
        return cfg

# NOTE: This module is superseded by engine-specific configs
# (core/dsc_engine/config.py, core/saxs_engine/config.py, etc.).
# The central TECHNIQUE_REGISTRY lives in core/engine.py.
# This file is kept for backward-compatibility only.
