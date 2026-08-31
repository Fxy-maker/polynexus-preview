"""Canonical data templates and deterministic conversion boundaries."""

from .dsc_isothermal import convert_mettler_isothermal_text
from .detector_image import convert_detector_image
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
from .ir_temperature_series import build_ir_temperature_series_template
from .nd_adapters import (
    DataBlockAdapterResult,
    NDAdapterResult,
    adapt_conversion_outcome,
    adapt_detector_image,
    adapt_ir_temperature_series,
    adapt_ir_temperature_template,
    adapt_nmr_fid,
    convert_detector_image_to_data_block,
    convert_ir_temperature_series_to_data_block,
    convert_nmr_fid_to_data_block,
)
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
    "convert_detector_image",
    "convert_one_dimensional_table",
    "build_ir_temperature_series_template",
    "DataBlockAdapterResult",
    "NDAdapterResult",
    "adapt_conversion_outcome",
    "adapt_detector_image",
    "adapt_ir_temperature_series",
    "adapt_ir_temperature_template",
    "adapt_nmr_fid",
    "convert_detector_image_to_data_block",
    "convert_ir_temperature_series_to_data_block",
    "convert_nmr_fid_to_data_block",
    "default_converter_registry",
    "CapabilityExecutor",
    "CapabilityRegistry",
    "CapabilitySpec",
    "ProviderCapabilitySpec",
    "ProviderCapabilityRegistry",
    "default_capability_registry",
    "default_provider_capability_registry",
]
