"""Backward-compatible import shim for the technique-neutral V2 adapter."""

from polynexus.core.figures.v2_adapter import (
    TemperatureV2AdapterDiagnostic,
    TemperatureV2AdapterResult,
    adapt_figure_definition,
    adapt_temperature_figure_definition,
)

__all__ = [
    "TemperatureV2AdapterDiagnostic",
    "TemperatureV2AdapterResult",
    "adapt_figure_definition",
    "adapt_temperature_figure_definition",
]
