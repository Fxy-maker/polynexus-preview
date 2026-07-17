"""Adapter registration and priority ordering."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .adapter_base import OriginAdapter


def order_adapters(adapters: Iterable["OriginAdapter"]) -> tuple["OriginAdapter", ...]:
    return tuple(sorted(adapters, key=lambda adapter: adapter.priority, reverse=True))


def build_default_adapters() -> tuple["OriginAdapter", ...]:
    """Build the default chain without importing optional runtime packages."""

    from .com_labtalk_adapter import ComLabTalkAdapter
    from .originpro_adapter import OriginProAdapter
    from .package_exporter import PackageExporter

    return order_adapters(
        (OriginProAdapter(), ComLabTalkAdapter(), PackageExporter())
    )
