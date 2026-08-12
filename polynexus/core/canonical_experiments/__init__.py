"""Canonical data templates and deterministic conversion boundaries."""

from .dsc_isothermal import convert_mettler_isothermal_text
from .models import CanonicalExperiment, ConversionOutcome, ConversionRecord

__all__ = [
    "CanonicalExperiment",
    "ConversionOutcome",
    "ConversionRecord",
    "convert_mettler_isothermal_text",
]
