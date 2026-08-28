"""Transparent inventory of deterministic provider outputs.

The catalog describes exposure, not scientific eligibility or manuscript use.
Actual values continue to come from the provider and shared ComputeRun result.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CapabilityCoverage:
    technique: str
    capability_id: str
    status: str = "provider_result"
    shared_projection: str = "result.metric_manifest"

    def to_dict(self) -> dict[str, str]:
        return {
            "technique": self.technique,
            "capability_id": self.capability_id,
            "status": self.status,
            "shared_projection": self.shared_projection,
        }


class CapabilityCatalog:
    def __init__(self, entries: tuple[CapabilityCoverage, ...]) -> None:
        self._entries = tuple(entries)

    def for_technique(self, technique: str) -> tuple[CapabilityCoverage, ...]:
        normalized = str(technique).strip().lower()
        return tuple(item for item in self._entries if item.technique == normalized)

    def to_dict(self) -> dict[str, Any]:
        return {
            "techniques": {
                technique: [item.to_dict() for item in self.for_technique(technique)]
                for technique in sorted({item.technique for item in self._entries})
            }
        }


_CAPABILITY_NAMES = {
    "dsc": ("Tg", "Tm", "Tc", "enthalpy", "multi_peak", "Avrami", "nonisothermal_kinetics"),
    "ftir": ("peak_position", "peak_height", "peak_area", "FWHM", "peak_ratio", "temperature_tracking"),
    "saxs": ("long_period", "crystalline_layer", "amorphous_layer", "Porod", "Kratky", "Guinier", "Invariant", "temperature_strain"),
    "waxs": ("peak_decomposition", "crystallinity", "crystallite_size", "lattice_parameters", "williamson_hall"),
    "nmr": ("peak_position", "area", "FWHM", "SNR", "region_integral", "relaxation", "solid_13C_phase"),
}
_DEFAULT_CATALOG = CapabilityCatalog(tuple(
    CapabilityCoverage(technique, capability_id)
    for technique, names in _CAPABILITY_NAMES.items()
    for capability_id in names
))


def default_capability_catalog() -> CapabilityCatalog:
    return _DEFAULT_CATALOG


__all__ = ["CapabilityCatalog", "CapabilityCoverage", "default_capability_catalog"]
