"""Read-only boundary audit for large PolyNexus Python files."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


DEFAULT_INCLUDE_DIRS: tuple[str, ...] = ("polynexus", "tests", "scripts", "llm", "rag")
DEFAULT_EXCLUDE_PARTS: tuple[str, ...] = ("__pycache__", ".pytest_tmp", ".tmp_pytest")
BROAD_EXCEPTION_RE = re.compile(r"\bexcept\s+Exception\b")


@dataclass(frozen=True)
class FileMetric:
    path: Path
    line_count: int
    broad_exception_count: int


def count_lines(text: str) -> int:
    if not text:
        return 0
    return len(text.splitlines())


def count_broad_exceptions(text: str) -> int:
    return len(BROAD_EXCEPTION_RE.findall(text))


def _is_excluded(path: Path, exclude_parts: Iterable[str]) -> bool:
    return any(part in path.parts for part in exclude_parts)


def collect_file_metrics(
    root: Path,
    include_dirs: Iterable[str] = DEFAULT_INCLUDE_DIRS,
    min_lines: int = 1000,
    exclude_parts: Iterable[str] = DEFAULT_EXCLUDE_PARTS,
) -> list[FileMetric]:
    root = root.resolve()
    metrics: list[FileMetric] = []

    for include_dir in include_dirs:
        base = root / include_dir
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            relative_path = path.relative_to(root)
            if _is_excluded(relative_path, exclude_parts):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            line_count = count_lines(text)
            if line_count < min_lines:
                continue
            metrics.append(
                FileMetric(
                    path=relative_path,
                    line_count=line_count,
                    broad_exception_count=count_broad_exceptions(text),
                )
            )

    return sorted(metrics, key=lambda metric: (-metric.line_count, metric.path.as_posix()))


def format_boundary_report(metrics: list[FileMetric], top: int = 15, min_lines: int = 1000) -> str:
    large_files = metrics[:top]
    exception_hotspots = sorted(
        [metric for metric in metrics if metric.broad_exception_count > 0],
        key=lambda metric: (-metric.broad_exception_count, -metric.line_count, metric.path.as_posix()),
    )[:top]

    lines = [
        "PolyNexus boundary audit",
        f"Large Python files: top {top} above {min_lines} lines",
    ]
    if large_files:
        for metric in large_files:
            lines.append(
                f"- {metric.path.as_posix()}: {metric.line_count} lines, "
                f"broad exceptions={metric.broad_exception_count}"
            )
    else:
        lines.append("- none found")

    lines.extend(["", f"Broad exception hotspots: top {top}"])
    if exception_hotspots:
        for metric in exception_hotspots:
            lines.append(
                f"- {metric.path.as_posix()}: broad exceptions={metric.broad_exception_count}, "
                f"lines={metric.line_count}"
            )
    else:
        lines.append("- none found")

    lines.extend(
        [
            "",
            "This command is read-only. Use the report to choose scoped refactors; it does not edit files.",
        ]
    )
    return "\n".join(lines)


def _metric_to_dict(metric: FileMetric) -> dict[str, int | str]:
    return {
        "path": metric.path.as_posix(),
        "line_count": metric.line_count,
        "broad_exception_count": metric.broad_exception_count,
    }


def to_report_dict(metrics: list[FileMetric], top: int = 15, min_lines: int = 1000) -> dict[str, object]:
    large_files = metrics[:top]
    exception_hotspots = sorted(
        [metric for metric in metrics if metric.broad_exception_count > 0],
        key=lambda metric: (-metric.broad_exception_count, -metric.line_count, metric.path.as_posix()),
    )[:top]
    return {
        "min_lines": min_lines,
        "top": top,
        "large_files": [_metric_to_dict(metric) for metric in large_files],
        "broad_exception_hotspots": [_metric_to_dict(metric) for metric in exception_hotspots],
    }


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

    parser = argparse.ArgumentParser(description="Report large files and broad exception hotspots.")
    parser.add_argument("--root", default=".", help="Repository root. Defaults to current directory.")
    parser.add_argument("--min-lines", type=int, default=1000, help="Minimum line count to report.")
    parser.add_argument("--top", type=int, default=15, help="Maximum items per section.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of text.")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    metrics = collect_file_metrics(root, min_lines=args.min_lines)
    if args.json:
        print(json.dumps(to_report_dict(metrics, top=args.top, min_lines=args.min_lines), ensure_ascii=False, indent=2))
    else:
        print(format_boundary_report(metrics, top=args.top, min_lines=args.min_lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
