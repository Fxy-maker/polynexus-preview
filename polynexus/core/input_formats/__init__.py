"""Shared raw-format inspection and reader-plugin contracts."""

from .models import FormatInspection, FormatPluginDescriptor
from .registry import FormatPluginRegistry, default_format_registry, inspect_format

__all__ = [
    "FormatInspection",
    "FormatPluginDescriptor",
    "FormatPluginRegistry",
    "default_format_registry",
    "inspect_format",
]
