"""Compatibility wrapper for single-technique CLI helpers."""

from __future__ import annotations

from typing import Any

def run_single(args: Any) -> int:
    from polynexus.__main__ import _run_single as main_run_single

    return main_run_single(args)
