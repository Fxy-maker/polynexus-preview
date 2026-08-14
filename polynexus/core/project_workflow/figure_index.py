"""Logical figure index shared by evidence-package readers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class FigureIndexEntry:
    id: str
    role: str
    technique: str
    group: str | None
    writing_eligibility: str
    svg: str
    document: str | None
    data: str | None
    metadata: str

    @classmethod
    def from_payload(cls, value: Mapping[str, Any]) -> "FigureIndexEntry":
        required = ("id", "role", "technique", "writing_eligibility", "svg", "metadata")
        if any(not str(value.get(key) or "").strip() for key in required):
            raise ValueError("figure index entry is invalid")
        for key in ("svg", "metadata"):
            path = str(value[key])
            if Path(path).is_absolute() or "\\" in path or ".." in Path(path).parts:
                raise ValueError("figure index path is invalid")
        document = value.get("document")
        data = value.get("data")
        for path in (document, data):
            if path is not None and (Path(str(path)).is_absolute() or "\\" in str(path) or ".." in Path(str(path)).parts):
                raise ValueError("figure index path is invalid")
        return cls(
            id=str(value["id"]), role=str(value["role"]), technique=str(value["technique"]),
            group=str(value["group"]) if value.get("group") is not None else None,
            writing_eligibility=str(value["writing_eligibility"]), svg=str(value["svg"]),
            document=str(document) if document is not None else None,
            data=str(data) if data is not None else None, metadata=str(value["metadata"]),
        )


def load_figure_index(root: Path) -> tuple[FigureIndexEntry, ...]:
    import json

    path = Path(root) / "figure-index.json"
    if path.is_file():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("figure index is invalid") from exc
        if not isinstance(payload, Mapping) or int(payload.get("version", 0)) != 1:
            raise ValueError("figure index is invalid")
        values = payload.get("figures")
        if not isinstance(values, list):
            raise ValueError("figure index is invalid")
        return tuple(FigureIndexEntry.from_payload(value) for value in values if isinstance(value, Mapping))
    figures = Path(root) / "figures"
    if not figures.is_dir():
        return ()
    result = []
    for svg in sorted(figures.glob("*.svg")):
        result.append(FigureIndexEntry(
            id=svg.stem, role="diagnostic", technique="unknown", group=None,
            writing_eligibility="review_only", svg=f"figures/{svg.name}",
            document=None, data=None, metadata="",
        ))
    return tuple(result)


__all__ = ["FigureIndexEntry", "load_figure_index"]
