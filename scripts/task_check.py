"""Validate an agent task card before implementation or handoff."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REQUIRED_SECTIONS = (
    "Goal",
    "Non-goals",
    "Acceptance criteria",
    "Affected boundaries",
    "Implementation plan",
    "Verification",
)
SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def _sections(text: str) -> dict[str, str]:
    matches = list(SECTION_RE.finditer(text))
    result: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        result[match.group(1).strip()] = text[match.end() : end].strip()
    return result


def _has_content(value: str) -> bool:
    without_comments = re.sub(r"<!--.*?-->", "", value, flags=re.DOTALL)
    return bool(without_comments.strip())


def validate_task_text(text: str) -> list[str]:
    """Return actionable validation errors for a task-card document."""

    sections = _sections(text)
    errors: list[str] = []
    for section in REQUIRED_SECTIONS:
        if section not in sections:
            errors.append(f"missing required section: {section}")
        elif not _has_content(sections[section]):
            errors.append(f"section is empty: {section}")

    acceptance = sections.get("Acceptance criteria", "")
    if not re.search(r"^\s*-\s*\[[ xX]\]\s+\S+", acceptance, re.MULTILINE):
        errors.append("Acceptance criteria must contain at least one non-empty checkbox item")

    plan = sections.get("Implementation plan", "")
    if not re.search(r"^\s*\d+[.)]\s+\S+", plan, re.MULTILINE):
        errors.append("Implementation plan must contain numbered steps")

    verification = sections.get("Verification", "")
    if "python scripts/verify.py" not in verification:
        errors.append("Verification must include python scripts/verify.py")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True, help="Path to a task-card Markdown file.")
    args = parser.parse_args(argv)

    path = Path(args.task).resolve()
    if not path.is_file():
        print(f"[task-check] task file not found: {path}", file=sys.stderr)
        return 2

    errors = validate_task_text(path.read_text(encoding="utf-8"))
    if errors:
        for error in errors:
            print(f"[task-check] {error}", file=sys.stderr)
        return 1

    print(f"[task-check] valid task card: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
