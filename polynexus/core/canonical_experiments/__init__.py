"""Canonical data templates and deterministic conversion boundaries."""

from .dsc_isothermal import convert_mettler_isothermal_text
from .models import (
    CAPABILITY_ITEM_STATUSES,
    MAPPING_SOURCES,
    CanonicalExperiment,
    CapabilityItemResult,
    ConversionOutcome,
    ConversionRecord,
    MappingProposal,
    MappingSelection,
    Measurement,
)
from .registry import CanonicalConverterRegistry, default_converter_registry

__all__ = [
    "CanonicalExperiment",
    "CapabilityItemResult",
    "ConversionOutcome",
    "ConversionRecord",
    "MappingProposal",
    "MappingSelection",
    "Measurement",
    "CAPABILITY_ITEM_STATUSES",
    "MAPPING_SOURCES",
    "CanonicalConverterRegistry",
    "convert_mettler_isothermal_text",
    "default_converter_registry",
]
