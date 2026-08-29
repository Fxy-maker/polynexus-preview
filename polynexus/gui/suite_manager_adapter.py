"""Qt-free adapter exposing Suite Manager DTOs to GUI presenters."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from polynexus.suite.handoff import build_suite_handoff
from polynexus.suite.paper_source import build_manuscript_source
from polynexus.suite.manager import SuiteManager


class SuiteManagerAdapter:
    """Thin GUI boundary; all decisions remain in :class:`SuiteManager`."""

    def __init__(self, **manager_kwargs: Any) -> None:
        self.manager = SuiteManager(**manager_kwargs)

    def doctor(self) -> dict[str, Any]:
        return self.manager.doctor().to_dict()

    def install_ars(self, *, confirm: bool = False, source: str | Path | None = None) -> dict[str, Any]:
        return self.manager.install("ars", confirm=confirm, source_override=source).to_dict()

    def update(self, component: str | None = None, *, confirm: bool = False) -> dict[str, Any]:
        return self.manager.update(component, confirm=confirm).to_dict()

    def rollback(self, component: str | None = None) -> dict[str, Any]:
        return self.manager.rollback(component).to_dict()

    @staticmethod
    def handoff(package_path: str | Path) -> dict[str, Any]:
        return build_suite_handoff(package_path)

    @staticmethod
    def manuscript_source(package_path: str | Path, brief: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return the same manuscript-source DTO consumed by CLI and ARS."""
        return build_manuscript_source(package_path, brief).to_dict()


__all__ = ["SuiteManagerAdapter"]
