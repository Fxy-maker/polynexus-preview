"""Stable contracts for optional OriginLab export adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Mapping


ExportMode = Literal["editable_origin", "visual_fidelity", "package"]
ExportStatus = Literal["success", "unavailable", "failed", "partial"]

_EXPORT_MODES = frozenset({"editable_origin", "visual_fidelity", "package"})


@dataclass(frozen=True)
class ExportRequest:
    """Immutable input passed from the GUI or CLI to an adapter chain."""

    document: Mapping[str, Any]
    output_root: Path
    figure_path: Path | None = None
    mode: ExportMode = "editable_origin"
    allow_open_origin: bool = True
    preferred_adapter: str | None = None

    def __post_init__(self) -> None:
        if self.mode not in _EXPORT_MODES:
            raise ValueError(f"unsupported Origin export mode: {self.mode}")
        object.__setattr__(self, "output_root", Path(self.output_root).resolve())
        if self.figure_path is not None:
            object.__setattr__(self, "figure_path", Path(self.figure_path).resolve())


@dataclass(frozen=True)
class CapabilityReport:
    """Optional adapter capability details suitable for UI diagnostics."""

    adapter_id: str
    available: bool
    reason: str = ""
    origin_version: str = ""
    supported_modes: tuple[str, ...] = ()
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExportResult:
    """Normalized result returned by every adapter and the service."""

    status: ExportStatus
    adapter_id: str
    artifacts: tuple[Path, ...] = ()
    warnings: tuple[str, ...] = ()
    message: str = ""
    capability: CapabilityReport | None = None
    recoverable: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifacts", tuple(Path(path) for path in self.artifacts))
        object.__setattr__(self, "warnings", tuple(str(warning) for warning in self.warnings))

    @property
    def success(self) -> bool:
        return self.status == "success"

    @classmethod
    def success_result(
        cls,
        adapter_id: str,
        *artifacts: Path,
        warnings: tuple[str, ...] = (),
        message: str = "",
    ) -> "ExportResult":
        return cls(
            status="success",
            adapter_id=adapter_id,
            artifacts=tuple(artifacts),
            warnings=warnings,
            message=message,
        )
