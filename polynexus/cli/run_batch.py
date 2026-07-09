"""Compatibility wrapper for batch CLI helpers."""

from __future__ import annotations

from typing import Any


def run_batch(args: Any) -> int:
    from polynexus.__main__ import run_batch as main_run_batch

    return main_run_batch(args)

