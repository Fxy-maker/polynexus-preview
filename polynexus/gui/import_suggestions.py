"""Lightweight import suggestion helpers for the GUI."""

from __future__ import annotations

import fnmatch
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from ..core import detect_submodule, get_submodule_registry
from ..core.nmr import _has_nmr_files, _nucleus_hint_from_file, _strong_state_hint


@dataclass(frozen=True)
class ImportSuggestion:
    path: str
    is_dir: bool
    technique: str = ""
    submodule: str = ""
    input_mode: str = ""
    reason: str = ""

    @property
    def is_meaningful(self) -> bool:
        return bool(self.technique or self.submodule or self.input_mode)


_FILE_TECHNIQUE_HINTS = {
    ".edf": ("saxs", "saxs.static", "single", "extension:.edf"),
    ".raw": ("waxs", "waxs.static", "single", "extension:.raw"),
    ".001": ("dsc", "dsc.standard", "single", "extension:.001"),
    ".spa": ("ir", "ir.standard", "single", "extension:.spa"),
    ".dpt": ("ir", "ir.standard", "single", "extension:.dpt"),
}


def suggest_import(path: str, is_dir: Optional[bool] = None) -> Optional[ImportSuggestion]:
    candidate = str(path or "").strip()
    if not candidate:
        return None

    resolved_is_dir = os.path.isdir(candidate) if is_dir is None else bool(is_dir)
    if resolved_is_dir:
        return _suggest_directory(candidate)
    return _suggest_file(candidate)


def _suggest_file(path: str) -> Optional[ImportSuggestion]:
    name = os.path.basename(path).lower()
    ext = Path(path).suffix.lower()
    if name == "fid":
        return _suggest_nmr(path, is_dir=False, reason="filename:fid")

    hinted = _FILE_TECHNIQUE_HINTS.get(ext)
    if hinted is not None:
        technique, submodule, input_mode, reason = hinted
        return ImportSuggestion(
            path=path,
            is_dir=False,
            technique=technique,
            submodule=submodule,
            input_mode=input_mode,
            reason=reason,
        )

    if ext in {".jdf", ".bin"}:
        return _suggest_nmr(path, is_dir=False, reason=f"extension:{ext}") or ImportSuggestion(
            path=path,
            is_dir=False,
            technique="nmr",
            submodule="",
            input_mode="single",
            reason=f"extension:{ext}",
        )

    return None


def _suggest_directory(path: str) -> Optional[ImportSuggestion]:
    detected = _detect_registry_submodule(path)
    if detected is not None:
        return detected

    nmr = _suggest_nmr(path, is_dir=True, reason="directory:nmr")
    if nmr is not None:
        return nmr

    file_names = _list_files(path)
    if not file_names:
        return None

    lower_names = [name.lower() for name in file_names]
    ext_counts = _count_extensions(lower_names)

    if _looks_like_saxs_temperature_series(path, lower_names):
        return ImportSuggestion(
            path=path,
            is_dir=True,
            technique="saxs",
            submodule="saxs.temperature",
            input_mode="sequence",
            reason="pattern:saxs_temperature",
        )

    if _looks_like_saxs_strain_series(lower_names):
        return ImportSuggestion(
            path=path,
            is_dir=True,
            technique="saxs",
            submodule="saxs.strain",
            input_mode="sequence",
            reason="pattern:saxs_strain",
        )

    if ext_counts.get(".raw", 0) >= 2:
        return ImportSuggestion(
            path=path,
            is_dir=True,
            technique="waxs",
            submodule="",
            input_mode="directory",
            reason="directory:.raw",
        )

    if ext_counts.get(".001", 0) >= 2:
        return ImportSuggestion(
            path=path,
            is_dir=True,
            technique="dsc",
            submodule="",
            input_mode="directory",
            reason="directory:.001",
        )

    ir_hits = ext_counts.get(".spa", 0) + ext_counts.get(".dpt", 0)
    if ir_hits >= 2:
        return ImportSuggestion(
            path=path,
            is_dir=True,
            technique="ir",
            submodule="",
            input_mode="directory",
            reason="directory:ir_spectra",
        )

    return None


def _detect_registry_submodule(path: str) -> Optional[ImportSuggestion]:
    registry = get_submodule_registry()
    for technique in sorted(registry):
        submodule = detect_submodule(technique, path)
        if not submodule:
            continue
        return ImportSuggestion(
            path=path,
            is_dir=True,
            technique=technique,
            submodule=submodule,
            input_mode=_submodule_input_mode(technique, submodule) or "sequence",
            reason=f"registry:{submodule}",
        )
    return None


def _suggest_nmr(path: str, *, is_dir: bool, reason: str) -> Optional[ImportSuggestion]:
    matches = _has_nmr_files(path)
    if not matches:
        return None
    if is_dir and not _has_strong_nmr_signature(path, matches):
        return None

    state = _strong_state_hint(path)
    nucleus = None
    for match in matches:
        nucleus = _nucleus_hint_from_file(match)
        if nucleus:
            break

    first_name = os.path.basename(matches[0]).lower()
    if state is None:
        if first_name == "fid":
            state = "liquid"
        elif Path(first_name).suffix.lower() in {".jdf", ".bin"}:
            state = "solid"

    submodule = ""
    if state == "liquid" and nucleus == "13C":
        submodule = "nmr.liquid_c"
    elif state == "liquid":
        submodule = "nmr.liquid_h"
    elif state == "solid" and nucleus == "13C":
        submodule = "nmr.solid_c"
    elif state == "solid":
        submodule = "nmr.solid_h"

    input_mode = _submodule_input_mode("nmr", submodule) if submodule else "single"
    return ImportSuggestion(
        path=path,
        is_dir=is_dir,
        technique="nmr",
        submodule=submodule,
        input_mode=input_mode or "single",
        reason=reason,
    )


def _has_strong_nmr_signature(path: str, matches: list[str]) -> bool:
    if _strong_state_hint(path):
        return True

    for candidate in [path, *matches]:
        name = os.path.basename(candidate).lower()
        ext = Path(name).suffix.lower()
        if name == "fid" or ext in {".jdf", ".bin"}:
            return True
        if _strong_state_hint(candidate) or _nucleus_hint_from_file(candidate):
            return True
        if any(token in name for token in ("nmr", "1h", "13c", "proton", "carbon", "solid", "liquid", "cpmas")):
            return True
    return False


def _submodule_input_mode(technique: str, submodule_id: str) -> str:
    for spec in get_submodule_registry().get(technique, []):
        if spec.id == submodule_id:
            return str(spec.input_mode or "").strip()
    return ""


def _list_files(path: str, limit: int = 64) -> list[str]:
    try:
        files = [
            entry.name
            for entry in os.scandir(path)
            if entry.is_file()
        ]
    except OSError:
        return []
    return files[:limit]


def _count_extensions(file_names: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name in file_names:
        ext = Path(name).suffix.lower()
        if not ext:
            continue
        counts[ext] = counts.get(ext, 0) + 1
    return counts


def _looks_like_saxs_strain_series(file_names: list[str]) -> bool:
    edf_names = [name for name in file_names if fnmatch.fnmatch(name, "*.edf")]
    if len(edf_names) < 2:
        return False
    hits = sum(1 for name in edf_names if re.search(r"-(\d+)-[sS]_", name))
    return hits >= max(2, len(edf_names) // 2)


def _looks_like_saxs_temperature_series(path: str, file_names: list[str]) -> bool:
    edf_names = [name for name in file_names if fnmatch.fnmatch(name, "*.edf")]
    if len(edf_names) < 2:
        return False

    path_text = str(Path(path).name or path).lower()
    if any(token in path_text for token in ("temp", "temperature", "thermal", "heat", "cool", "变温", "升温", "降温")):
        return True

    hits = 0
    for name in edf_names:
        if re.search(r"(?:^|[_-])(?:t|temp)[_-]?\d{2,4}(?:c|deg|k)?(?:[_-]|\.|$)", name, re.IGNORECASE):
            hits += 1
            continue
        if re.search(r"(?:^|[_-])\d{2,4}[cC](?:[_-]|\.|$)", name):
            hits += 1
    return hits >= max(2, len(edf_names) // 2)
