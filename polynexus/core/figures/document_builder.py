"""Build portable editable documents from validated figure definitions."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ..figure_document import normalize_figure_document
from ..figure_objects import normalize_figure_object
from .contracts import FigureDefinition


class FigureDocumentBuilder:
    def write(
        self,
        *,
        definition: FigureDefinition,
        run_id: str,
        revision: int,
        figure_dir: Path,
        data_sources: list[dict[str, object]],
    ) -> tuple[Path, dict[str, object]]:
        now = datetime.now().isoformat(timespec="seconds")
        objects = [
            normalize_figure_object(dict(figure_object))
            for figure_object in definition.objects
        ]
        layout = definition.layout.to_payload()
        document = normalize_figure_document(
            {
                "version": 2,
                "run_id": str(run_id),
                "figure_id": definition.figure_id,
                "revision": int(revision),
                "mode": "object",
                "technique": definition.technique,
                "scope": definition.scope,
                "category": definition.category,
                "title": definition.title,
                "created_at": now,
                "updated_at": now,
                "layout": layout,
                "canvas": layout["canvas"],
                "style": {"profile": definition.style_profile},
                "layers": [
                    {
                        "id": "layer-1",
                        "name": "Layer 1",
                        "visible": True,
                        "locked": False,
                        "object_ids": [item["id"] for item in objects],
                    }
                ],
                "objects": objects,
                "data_sources": data_sources,
                "recipe": dict(definition.recipe),
                "export": {
                    "profile": "",
                    "published_revision": 0,
                    "assets": {},
                },
            }
        )
        path = Path(figure_dir) / "figure.pnfig.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(document, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path, document
