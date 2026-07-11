"""Single production entry point for manifest-backed figure publication."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from .contracts import FigureDefinition
from .manifest import RunFigureManifest
from .pipeline import FigurePipeline


@dataclass(frozen=True)
class FigureProductionResult:
    run_id: str
    manifest: RunFigureManifest
    primary_assets: dict[str, str]


class FigureProductionPublisher:
    def __init__(self, *, pipeline: FigurePipeline | None = None) -> None:
        self.pipeline = pipeline or FigurePipeline()

    def publish(
        self,
        *,
        output_root: str | Path,
        technique: str,
        definitions: Iterable[FigureDefinition],
        profile_id: str = "paper_complete",
        run_id: str | None = None,
    ) -> FigureProductionResult:
        definitions = tuple(definitions)
        if not definitions:
            raise ValueError("production figure publication requires definitions")
        output_root = Path(output_root).resolve()
        resolved_run_id = str(run_id or new_immutable_run_id(technique))
        manifest = self.pipeline.run(
            output_root=output_root,
            run_id=resolved_run_id,
            technique=str(technique),
            definitions=definitions,
            profile_id=profile_id,
        )
        run_root = output_root / "runs" / resolved_run_id
        primary_assets = {}
        for entry in manifest.figures:
            if entry.status != "ready":
                continue
            relative_path = next(
                (
                    entry.assets[role]
                    for role in ("svg", "png", "pdf", "preview")
                    if entry.assets.get(role)
                ),
                "",
            )
            if relative_path:
                primary_assets[entry.figure_id] = str(
                    (run_root / relative_path).resolve()
                )
        return FigureProductionResult(
            run_id=resolved_run_id,
            manifest=manifest,
            primary_assets=primary_assets,
        )


def new_immutable_run_id(technique: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "-", str(technique or "figure").lower())
    token = token.strip("-") or "figure"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{token}-{timestamp}-{uuid4().hex[:8]}"
