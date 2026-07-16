"""Canonical processed SAXS profile projection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np


def _array_or_none(value: Any) -> np.ndarray | None:
    if value is None:
        return None
    array = np.asarray(value, dtype=float).copy()
    array.setflags(write=False)
    return array


@dataclass(frozen=True)
class ProcessedProfile:
    """Read-only raw and processed layers for one SAXS frame."""

    q: np.ndarray
    raw: np.ndarray
    corrected: np.ndarray | None = None
    normalized: np.ndarray | None = None
    smoothed: np.ndarray | None = None
    meridional_raw: np.ndarray | None = None
    meridional_corrected: np.ndarray | None = None
    meridional_normalized: np.ndarray | None = None
    meridional_smoothed: np.ndarray | None = None
    equatorial_raw: np.ndarray | None = None
    equatorial_corrected: np.ndarray | None = None
    equatorial_normalized: np.ndarray | None = None
    equatorial_smoothed: np.ndarray | None = None
    provenance: Mapping[str, Any] = field(default_factory=dict)
    quality_status: str = "OK"
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "q", "raw", "corrected", "normalized", "smoothed",
            "meridional_raw", "meridional_corrected", "meridional_normalized",
            "meridional_smoothed", "equatorial_raw", "equatorial_corrected",
            "equatorial_normalized", "equatorial_smoothed",
        ):
            value = _array_or_none(getattr(self, name))
            if value is not None:
                object.__setattr__(self, name, value)
        object.__setattr__(self, "provenance", dict(self.provenance))
        object.__setattr__(self, "diagnostics", dict(self.diagnostics))

    @property
    def analysis_intensity(self) -> np.ndarray:
        return next(
            value for value in (self.smoothed, self.normalized, self.corrected, self.raw)
            if value is not None
        )

    def to_legacy_payload(self) -> dict[str, Any]:
        return {
            "q": self.q,
            "I": self.raw,
            "Iq": self.raw,
            "Iq_corrected": self.corrected,
            "Iq_norm": self.normalized,
            "I_smooth": self.smoothed,
            "Iq_smooth": self.smoothed,
            "Iq_merid": self.meridional_raw,
            "Iq_merid_corrected": self.meridional_corrected,
            "Iq_merid_norm": self.meridional_normalized,
            "Iq_merid_smooth": self.meridional_smoothed,
            "Iq_equat": self.equatorial_raw,
            "Iq_equat_corrected": self.equatorial_corrected,
            "Iq_equat_norm": self.equatorial_normalized,
            "Iq_equat_smooth": self.equatorial_smoothed,
            "provenance": dict(self.provenance),
            "quality_status": self.quality_status,
            "diagnostics": dict(self.diagnostics),
        }


__all__ = ["ProcessedProfile"]
