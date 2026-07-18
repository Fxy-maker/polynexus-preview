"""Priority-ordered responsibility chain for Origin export adapters."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from .adapter_base import OriginAdapter
from .contracts import ExportRequest, ExportResult
from .registry import order_adapters

logger = logging.getLogger(__name__)


class OriginExportService:
    """Select and execute the first capable adapter without version branches."""

    def __init__(self, adapters: Sequence[OriginAdapter] | None = None) -> None:
        self._adapters = order_adapters(adapters or ())

    @property
    def adapters(self) -> tuple[OriginAdapter, ...]:
        return self._adapters

    def export(self, request: ExportRequest) -> ExportResult:
        for adapter in self._adapters:
            if request.preferred_adapter and adapter.adapter_id != request.preferred_adapter:
                continue
            try:
                can_handle = bool(adapter.can_handle(request))
            except Exception:
                logger.warning(
                    "Origin adapter capability probe failed: %s",
                    adapter.adapter_id,
                    exc_info=True,
                )
                continue
            if not can_handle:
                continue

            try:
                result = adapter.export(request)
            except Exception as exc:
                logger.warning(
                    "Origin adapter export failed: %s",
                    adapter.adapter_id,
                    exc_info=True,
                )
                return ExportResult(
                    status="failed",
                    adapter_id=adapter.adapter_id,
                    message=str(exc),
                    recoverable=True,
                )

            if result.status == "success":
                return result
            if result.status == "unavailable":
                continue
            return result

        return ExportResult(
            status="failed",
            adapter_id="service",
            message="No Origin export adapter can handle this request",
            recoverable=True,
        )


def default_origin_export_service() -> OriginExportService:
    from .registry import build_default_adapters

    return OriginExportService(build_default_adapters())
