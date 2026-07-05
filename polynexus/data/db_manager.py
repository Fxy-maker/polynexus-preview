"""Unified polymer database manager.

Loads polymers.json and provides typed access to all properties.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_DATA_DIR = Path(__file__).parent


class PolymerDB:
    def __init__(self, db_path=None):
        self._path = Path(db_path) if db_path else _DATA_DIR / "polymers.json"
        self._data = None

    @property
    def data(self):
        if self._data is None:
            with open(self._path, 'r', encoding='utf-8') as f:
                self._data = json.load(f)
        return self._data

    def list_polymers(self):
        return sorted(self.data.get("polymers", {}).keys())

    def get_polymer(self, name):
        return self.data.get("polymers", {}).get(name, {})

    def get_dHm0(self, name):
        return self.get_polymer(name).get("dHm0_Jg", 293.0)

    def get_Tg(self, name):
        return self.get_polymer(name).get("dsc_transitions", {}).get("Tg_C", float('nan'))

    def get_Tm(self, name):
        return self.get_polymer(name).get("dsc_transitions", {}).get("Tm_C", float('nan'))

    def get_ir_peaks(self, name, phase=None):
        p = self.get_polymer(name)
        if phase:
            pd = p.get(f"{phase}_form", p.get(f"{phase}_phase", {}))
            return pd.get("ir_peaks", p.get("ir_peaks", []))
        return p.get("ir_peaks", [])

    def get_nmr_shifts(self, name, phase=None):
        p = self.get_polymer(name)
        if phase:
            pd = p.get(f"{phase}_form", p.get(f"{phase}_phase", {}))
            s = pd.get("nmr_13c", [])
            if s: return s
            return p.get(f"{phase}_nmr_13c", [])
        return p.get("nmr_13c", [])

    def get_waxs_peaks(self, name, phase=None):
        p = self.get_polymer(name)
        if phase:
            pd = p.get(f"{phase}_form", p.get(f"{phase}_phase", {}))
            return pd.get("waxs_peaks", p.get("waxs_peaks", []))
        return p.get("waxs_peaks", [])

    def find_polymer(self, query):
        q = query.strip().lower()
        for key, info in self.data.get("polymers", {}).items():
            if q == key.lower() or q in info.get("name", "").lower():
                return key
        for key, info in self.data.get("polymers", {}).items():
            if q in key.lower() or key.lower() in q:
                return key
        return None

_db = None

def get_db():
    global _db
    if _db is None:
        _db = PolymerDB()
    return _db


# ── MultiFamilyDB (v2.0) ──
from collections import namedtuple
import re

PeakEntry = namedtuple("PeakEntry", ["position", "assignment", "intensity"])


class PolymerEntry:
    """Standardised polymer entry from any family file."""
    def __init__(self, key, data, source_family):
        self.key = key
        self.name = data.get("name", key)
        self.family = data.get("family", source_family)
        self.tags = data.get("tags", [])
        self.phases = data.get("phases", {})
        self.common = data.get("common", {})
        self.source_family = source_family

    def get_phase_data(self, phase=None):
        if phase and phase in self.phases:
            return self.phases[phase]
        return self.common


class MultiFamilyDB:
    """Aggregates multiple family .json files with lazy loading and caching."""

    FAMILY_DIR = Path(__file__).parent / "polymers"
    FAMILY_FILES = {
        "polyolefin": "polyolefins.json",
        "polyamide": "polyamides.json",
        "polyester": "polyesters.json",
        "fluoropolymer": "fluoropolymers.json",
        "engineering_plastic": "engineering_plastics.json",
        "elastomer": "elastomers.json",
        "specialty": "specialty.json",
    }

    def __init__(self, families: list[str] = None):
        self._families = families
        self._cache: dict[str, dict] = {}
        self._entries: dict[str, PolymerEntry] = {}
        self._loaded = False

    def _ensure_loaded(self):
        if self._loaded:
            return
        targets = self._families if self._families else list(self.FAMILY_FILES.keys())
        for family in targets:
            filename = self.FAMILY_FILES.get(family)
            if not filename:
                continue
            filepath = self.FAMILY_DIR / filename
            if not filepath.exists():
                continue
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._cache[family] = data
            for key, pdata in data.items():
                self._entries[key] = PolymerEntry(key, pdata, family)
        self._loaded = True

    def find(self, name: str):
        self._ensure_loaded()
        q = name.strip()
        # Level 1: exact match
        if q in self._entries:
            return self._entries[q]
        # Level 2: normalise (remove hyphens, underscores, spaces; case-insensitive)
        def norm(s):
            return re.sub(r'[-_\s]', '', s).lower()
        nq = norm(q)
        matches = [(k, v) for k, v in self._entries.items() if norm(k) == nq]
        if len(matches) == 1:
            return matches[0][1]
        if len(matches) > 1:
            import logging
            logging.warning(
                f"MultiFamilyDB.find('{name}'): multiple matches "
                f"{[m[0] for m in matches]}, using first"
            )
            return matches[0][1]
        # Level 3: substring in name field
        nq_lower = q.lower()
        for key, entry in self._entries.items():
            if nq_lower in entry.name.lower():
                return entry
        return None

    def get_scalar(self, polymer: str, key: str, phase: str = None):
        self._ensure_loaded()
        entry = self.find(polymer)
        if not entry:
            return None
        data = entry.get_phase_data(phase)
        val = data.get(key)
        if isinstance(val, (int, float)):
            return float(val)
        return None

    def get_peaks(self, polymer: str, technique: str, phase: str = None):
        self._ensure_loaded()
        entry = self.find(polymer)
        if not entry:
            return []
        data = entry.get_phase_data(phase)
        raw = data.get(f"{technique}_peaks", [])
        peaks = []
        for item in raw:
            if len(item) >= 2:
                pos = float(item[0]) if item[0] is not None else 0.0
                assign = str(item[1]) if len(item) > 1 else ""
                intens = 0.0
                if len(item) > 2 and item[2] is not None:
                    try:
                        intens = float(item[2])
                    except (ValueError, TypeError):
                        intens = 0.0  # non-numeric intensity labels (e.g. "m"="medium") → 0.0
                peaks.append(PeakEntry(position=pos, assignment=assign, intensity=intens))
        return peaks

    def get_phase_list(self, polymer: str):
        self._ensure_loaded()
        entry = self.find(polymer)
        return list(entry.phases.keys()) if entry else []

    def list_polymers(self):
        self._ensure_loaded()
        return sorted(self._entries.keys())