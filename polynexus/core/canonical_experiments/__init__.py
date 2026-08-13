"""Canonical data templates and deterministic conversion boundaries."""

from .dsc_isothermal import convert_mettler_isothermal_text
from .models import CanonicalExperiment, ConversionOutcome, ConversionRecord
from .registry import CanonicalConverterRegistry, default_converter_registry

__all__ = [
    "CanonicalExperiment",
    "ConversionOutcome",
    "ConversionRecord",
    "CanonicalConverterRegistry",
    "convert_mettler_isothermal_text",
    "default_converter_registry",
]
