"""Structural adapter interface for optional OriginLab integrations."""

from __future__ import annotations

from typing import Protocol

from .contracts import ExportRequest, ExportResult


class OriginAdapter(Protocol):
    """Common contract implemented by every Origin export strategy."""

    adapter_id: str
    priority: int

    def can_handle(self, request: ExportRequest) -> bool:
        """Return whether this adapter can attempt the requested export."""

    def export(self, request: ExportRequest) -> ExportResult:
        """Execute the export and return a normalized result."""
