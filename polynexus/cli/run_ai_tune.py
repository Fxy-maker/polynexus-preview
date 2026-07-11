"""Compatibility wrapper for AI tuning CLI helpers."""

from __future__ import annotations

from typing import Any


def run_ai_tune(args: Any) -> int:
    from polynexus.__main__ import _run_ai_tune as main_run_ai_tune

    return main_run_ai_tune(args)

