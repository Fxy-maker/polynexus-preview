"""Single-technique CLI runtime helpers."""

from __future__ import annotations

import os
from typing import Any, Callable

from polynexus.cli.output import format_technique_result_lines
from polynexus.core.engine import get_engine


def run_single(
    args: Any,
    *,
    get_engine_fn: Callable[[str], Any] = get_engine,
    format_technique_result_lines_fn: Callable[[str, str, dict], list[str]] = format_technique_result_lines,
) -> int:
    # Import all technique engines so the registry is populated before lookup.
    import polynexus.core.dsc as _dsc
    import polynexus.core.ir as _ir
    import polynexus.core.waxs as _waxs
    import polynexus.core.saxs as _saxs
    import polynexus.core.nmr as _nmr

    del _dsc, _ir, _waxs, _saxs, _nmr

    engine = get_engine_fn(args.cmd)
    if engine is None:
        print(f"Unknown technique: {args.cmd}")
        return 1

    if hasattr(args, "type") and hasattr(engine, "cfg"):
        engine.cfg.experiment_type = args.type

    output = args.output or os.path.join(os.path.dirname(args.input) or ".", args.cmd + "_results")
    result = engine.run_pipeline(args.input, output, skip_to=args.skip_to)

    for line in format_technique_result_lines_fn(args.cmd, output, result.parameters):
        print(line)
    return 0
