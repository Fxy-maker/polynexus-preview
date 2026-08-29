"""Citation adapters with Zotero dynamic and dependency-free CSL fallback."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .paper_contracts import CitationRequest


def detect_zotero() -> bool:
    try:
        import zotero  # type: ignore[import-not-found]  # noqa: F401
        return True
    except Exception:
        return False


def render_citations(requests: Iterable[CitationRequest], *, zotero_available: bool | None = None) -> dict[str, object]:
    values = tuple(requests)
    dynamic = detect_zotero() if zotero_available is None else bool(zotero_available)
    mode = "dynamic" if dynamic and all(r.mode != "static" for r in values) else "static"
    inline = " ".join(f"{{{{ZOTERO:{r.key}}}}}" if mode == "dynamic" else f"[{r.key}]" for r in values)
    bibliography = [_format_static(r) for r in values]
    unresolved = [r.key for r in values if not r.metadata.get("title") and mode == "static"]
    return {"version": 1, "mode": mode, "inline": inline, "bibliography": bibliography, "unresolved_keys": unresolved, "keys": [r.key for r in values]}


def export_bibliography(output_dir: str | Path, requests: Iterable[CitationRequest], rendered: dict[str, object] | None = None) -> dict[str, str]:
    root = Path(output_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    values = tuple(requests)
    rendered = rendered or render_citations(values, zotero_available=False)
    bib = root / "references.bib"
    bib.write_text("\n\n".join(_bibtex(r) for r in values), encoding="utf-8")
    data = root / "references.json"
    data.write_text(json.dumps({"version": 1, "requests": [r.to_dict() for r in values], "rendered": rendered}, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    return {"bib": str(bib), "json": str(data)}


def _format_static(req: CitationRequest) -> str:
    md = req.metadata
    author = str(md.get("author", ""))
    year = str(md.get("year", "n.d."))
    title = str(md.get("title", req.locator))
    journal = str(md.get("journal", ""))
    return f"{author} ({year}). {title}. {journal}".strip()


def _bibtex(req: CitationRequest) -> str:
    md = req.metadata
    return "@article{" + req.key + ",\n" + "\n".join(f"  {k} = {{{md[k]}}}," for k in ("author", "title", "journal", "year") if k in md) + "\n}"


__all__ = ["detect_zotero", "render_citations", "export_bibliography"]
