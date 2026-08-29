"""Deterministic FigurePlan renderer (SVG is the canonical artifact)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .paper_contracts import FigurePlan


def render_figure_plan(plan: FigurePlan, output_dir: str | Path) -> dict[str, str]:
    if not isinstance(plan, FigurePlan):
        raise TypeError("plan must be FigurePlan")
    root = Path(output_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    stem = plan.figure_id
    svg_path = root / f"{stem}.svg"
    json_path = root / f"{stem}.json"
    svg_path.write_text(_svg(plan), encoding="utf-8")
    json_path.write_text(json.dumps(plan.to_dict(), ensure_ascii=False, sort_keys=True), encoding="utf-8")
    result = {"svg": str(svg_path), "json": str(json_path)}
    if "png" in plan.outputs or "pdf" in plan.outputs:
        try:
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(6.4, 4.8), dpi=160)
            if plan.data:
                ax.plot([p[0] for p in plan.data], [p[1] for p in plan.data], marker="o")
            ax.set_title(plan.title)
            ax.set_xlabel(plan.x_label)
            ax.set_ylabel(plan.y_label or "Signal")
            fig.tight_layout()
            for ext in ("png", "pdf"):
                if ext in plan.outputs:
                    path = root / f"{stem}.{ext}"
                    fig.savefig(path, format=ext)
                    result[ext] = str(path)
            plt.close(fig)
        except Exception:
            # SVG/JSON remain authoritative when optional raster/PDF backends are unavailable.
            pass
    return result


def _svg(plan: FigurePlan) -> str:
    points = plan.data or ((0.0, 0.0), (1.0, 1.0))
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    dx, dy = (xmax - xmin) or 1.0, (ymax - ymin) or 1.0
    coords = " ".join(f"{50 + 500*(x-xmin)/dx:.2f},{350 - 280*(y-ymin)/dy:.2f}" for x, y in points)
    unit = f" [{plan.unit}]" if plan.unit else ""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="600" height="420" viewBox="0 0 600 420">
<title>{_esc(plan.title)}</title><rect width="600" height="420" fill="white"/>
<line x1="50" y1="350" x2="550" y2="350" stroke="black"/><line x1="50" y1="70" x2="50" y2="350" stroke="black"/>
<polyline points="{coords}" fill="none" stroke="#1f77b4" stroke-width="2"/>
<text x="300" y="405" text-anchor="middle">{_esc(plan.x_label)}{_esc(unit)}</text>
<text x="15" y="210" transform="rotate(-90 15 210)" text-anchor="middle">{_esc(plan.y_label)}</text>
<text x="300" y="30" text-anchor="middle">{_esc(plan.title)}</text></svg>'''


def _esc(value: Any) -> str:
    import html
    return html.escape(str(value or ""))


__all__ = ["render_figure_plan"]
