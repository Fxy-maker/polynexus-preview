"""Create and validate durable PolyNexus agent-memory entries."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path


KINDS = {
    "decision": "docs/agent/memory/decisions",
    "lesson": "docs/agent/memory/lessons",
}
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
REQUIRED_MEMORY_FILES = (
    "docs/agent/memory/README.md",
    "docs/agent/memory/current-state.md",
    "docs/agent/memory/active-work.md",
    "docs/agent/memory/known-issues.md",
)


def _memory_root(root: Path) -> Path:
    return root / "docs" / "agent" / "memory"


def _create(root: Path, kind: str, slug: str, title: str) -> int:
    if kind not in KINDS:
        print(f"[memory] unsupported kind: {kind}", file=sys.stderr)
        return 2
    if not SLUG_RE.fullmatch(slug):
        print(
            "[memory] slug must contain lowercase letters, numbers, and hyphens",
            file=sys.stderr,
        )
        return 2

    target_dir = root / KINDS[kind]
    target_dir.mkdir(parents=True, exist_ok=True)
    prefix = len(list(target_dir.glob("*.md"))) + 1
    path = target_dir / f"{prefix:04d}-{slug}.md"
    if path.exists():
        print(f"[memory] target already exists: {path}", file=sys.stderr)
        return 1

    content = (
        "---\n"
        f"kind: {kind}\n"
        "status: active\n"
        f"date: {date.today().isoformat()}\n"
        f"title: {title}\n"
        "---\n\n"
        f"# {title}\n\n"
        "## Context\n\n"
        "## Decision or lesson\n\n"
        "## Consequences\n\n"
        "## Evidence\n"
    )
    path.write_text(content, encoding="utf-8")
    print(f"[memory] created {path}")
    return 0


def _check(root: Path) -> int:
    missing = [path for path in REQUIRED_MEMORY_FILES if not (root / path).is_file()]
    if missing:
        for path in missing:
            print(f"[memory] missing required file: {path}", file=sys.stderr)
        return 1

    errors: list[str] = []
    memory_root = _memory_root(root)
    for kind, relative_dir in KINDS.items():
        directory = root / relative_dir
        for path in sorted(directory.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            if not text.startswith("---\n") or "\n---\n" not in text[4:]:
                errors.append(f"{path}: missing YAML front matter")
                continue
            header = text[4 : text.index("\n---\n", 4)]
            for field in ("kind:", "status:", "date:", "title:"):
                if not any(line.startswith(field) for line in header.splitlines()):
                    errors.append(f"{path}: missing front-matter field {field}")
            if not any(line == f"kind: {kind}" for line in header.splitlines()):
                errors.append(f"{path}: kind does not match directory {kind}")

    if errors:
        for error in errors:
            print(f"[memory] {error}", file=sys.stderr)
        return 1

    entry_count = sum(
        len(list((root / relative_dir).glob("*.md")))
        for relative_dir in KINDS.values()
    )
    print(f"[memory] checked {memory_root} ({entry_count} durable entries)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="Create a decision or lesson template.")
    create.add_argument("--root", default=".", help="Repository root.")
    create.add_argument("--kind", choices=sorted(KINDS), required=True)
    create.add_argument("--slug", required=True)
    create.add_argument("--title", required=True)
    check = subparsers.add_parser("check", help="Validate the memory layout and entry metadata.")
    check.add_argument("--root", default=".", help="Repository root.")

    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if args.command == "create":
        return _create(root, args.kind, args.slug, args.title)
    return _check(root)


if __name__ == "__main__":
    raise SystemExit(main())
