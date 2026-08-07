"""Canonical SAXS analysis-mode aliases shared across orchestration boundaries."""

from __future__ import annotations

from typing import Any


_SAXS_MODE_ALIASES = {
    "static": "static",
    "strain": "strain",
    "temperature": "temperature",
    "heating": "temperature",
    "cooling": "temperature",
    "isothermal": "temperature",
}


def canonical_saxs_mode(value: Any) -> str | None:
    """Return the canonical scientific mode, or ``None`` when unsupported."""
    raw = str(value or "").strip().lower()
    if raw.startswith("saxs."):
        raw = raw.split(".", 1)[1]
    return _SAXS_MODE_ALIASES.get(raw)


__all__ = ["canonical_saxs_mode"]
