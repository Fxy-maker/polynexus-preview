"""IR polymer naming helpers.

Keeps IR polymer identifiers aligned across the core engine, evidence
layer, and RAG-facing reference text.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


_IR_POLYMER_ALIAS_MAP: dict[str, str] = {
    "pe": "PE",
    "polyethylene": "PE",
    "hdpe": "PE",
    "ldpe": "PE",
    "lldpe": "PE",
    "pp": "PP",
    "ipp": "PP",
    "polypropylene": "PP",
    "isotacticpp": "PP",
    "isotacticpolypropylene": "PP",
    "pet": "PET",
    "polyethyleneterephthalate": "PET",
    "pvdf": "PVDF",
    "polyvinylidenefluoride": "PVDF",
    "pa6": "PA6",
    "nylon6": "PA6",
    "polyamide6": "PA6",
    "pa66": "PA66",
    "nylon66": "PA66",
    "polyamide66": "PA66",
    "pom": "POM",
    "polyoxymethylene": "POM",
    "acetal": "POM",
    "peek": "PEEK",
    "polyetheretherketone": "PEEK",
    "pcl": "PCL",
    "polycaprolactone": "PCL",
    "plla": "PLLA",
    "polylacticacid": "PLLA",
}


def _ir_name_candidates(polymer_name: str) -> list[str]:
    raw = str(polymer_name or "").strip().lower()
    if not raw:
        return []

    compact = re.sub(r"[^a-z0-9]+", "", raw)
    split_tokens = [token for token in re.sub(r"[^a-z0-9]+", " ", raw).split() if token]

    candidates: list[str] = []
    if compact:
        candidates.append(compact)
    if split_tokens:
        candidates.append(split_tokens[0])
        for size in range(2, min(len(split_tokens), 4) + 1):
            candidates.append("".join(split_tokens[:size]))
        candidates.append("".join(split_tokens))

    return list(dict.fromkeys(candidate for candidate in candidates if candidate))


def normalize_ir_polymer_name(polymer_name: str) -> str:
    """Return the canonical IR polymer key for a user or engine label."""
    text = str(polymer_name or "").strip()
    if not text:
        return ""

    for candidate in _ir_name_candidates(text):
        canonical = _IR_POLYMER_ALIAS_MAP.get(candidate)
        if canonical:
            return canonical

    return text.upper()


def normalize_ir_polymer_database(polymer_db: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a canonical-key copy of an IR polymer peak database."""
    if not isinstance(polymer_db, Mapping):
        return {}

    normalized: dict[str, Any] = {}
    for key, bands in polymer_db.items():
        canonical_key = normalize_ir_polymer_name(str(key))
        if not canonical_key:
            continue
        if canonical_key not in normalized or str(key).strip().upper() == canonical_key:
            normalized[canonical_key] = bands
    return normalized
