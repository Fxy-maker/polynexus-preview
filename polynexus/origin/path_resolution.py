"""Resolve figure data paths for Origin export adapters."""

from __future__ import annotations

from pathlib import Path

from .contracts import ExportRequest


def resolve_source_path(raw_path: str, request: ExportRequest) -> Path:
    """Resolve a data-source path using the figure's run root when available."""

    raw = Path(raw_path)
    if raw.is_absolute():
        return raw.resolve()

    candidates: list[Path] = []
    if request.source_root is not None:
        candidates.append(request.source_root / raw)
    if request.figure_path is not None:
        candidates.extend(
            [
                request.figure_path.parent / raw,
                request.figure_path.parent.parent / raw,
            ]
        )
    candidates.append(Path.cwd() / raw)
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve() if candidates else raw.resolve()
