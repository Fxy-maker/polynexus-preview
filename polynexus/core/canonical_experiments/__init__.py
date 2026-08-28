"""Canonical data templates and deterministic conversion boundaries."""

from .dsc_isothermal import convert_mettler_isothermal_text
from .capabilities import (
    CapabilityExecutor,
    CapabilityRegistry,
    CapabilitySpec,
    ProviderCapabilityRegistry,
    ProviderCapabilitySpec,
    default_capability_registry,
    default_provider_capability_registry,
)
from .one_dimensional import convert_one_dimensional_table
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
    "convert_one_dimensional_table",
    "default_converter_registry",
    "CapabilityExecutor",
    "CapabilityRegistry",
    "CapabilitySpec",
    "ProviderCapabilitySpec",
    "ProviderCapabilityRegistry",
    "default_capability_registry",
    "default_provider_capability_registry",
]
