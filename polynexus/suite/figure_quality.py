"""Static checks for FigurePlan SVG artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .paper_contracts import FigurePlan


def check_figure_quality(plan: FigurePlan, svg_path: str | Path) -> dict[str, object]:
    labels = tuple(v for v in (plan.x_label, plan.y_label) if v)
    missing = [name for name, value in (("x_label", plan.x_label), ("y_label", plan.y_label)) if not value]
    required = labels + ((f"[{plan.unit}]",) if plan.unit else ())
    result = check_svg_quality(svg_path, required_labels=required, require_source=bool(plan.source_ids))
    if missing:
        result["issues"] = [*result["issues"], *(f"{name}_missing" for name in missing)]
        result["status"] = "review_required"
    return result


def check_svg_quality(svg_path: str | Path, *, required_labels: Iterable[str] = (), require_source: bool = False) -> dict[str, object]:
    path = Path(svg_path)
    issues: list[str] = []
    if not path.is_file():
        issues.append("svg_missing")
    else:
        text = path.read_text(encoding="utf-8", errors="replace")
        if "<svg" not in text or "width=" not in text or "height=" not in text:
            issues.append("dimensions_invalid")
        for label in required_labels:
            if str(label) not in text:
                issues.append(f"label_missing:{label}")
        if "clipPath" in text and "clip-path" in text:
            issues.append("clipping_possible")
    return {"status": "review_required" if issues else "passed", "issues": issues, "svg": str(path)}


__all__ = ["check_figure_quality", "check_svg_quality"]
