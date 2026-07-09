"""Shared helpers for maintenance audit and cleanup scripts."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, TypeVar


T = TypeVar("T")


def split_display_items(items: Iterable[T], *, max_items: int = 40, list_all: bool = False) -> tuple[list[T], int]:
    values = list(items)
    if list_all:
        return values, 0
    capped = values[:max(0, max_items)]
    return capped, max(0, len(values) - len(capped))


def relative_posix(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()
