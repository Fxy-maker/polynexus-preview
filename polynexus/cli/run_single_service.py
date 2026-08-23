"""Single-technique CLI runtime helpers."""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Callable

from polynexus.cli.output import format_technique_result_lines
from polynexus.core.compute import ComputeRunService
from polynexus.core.engine import get_engine


def run_single(
    args: Any,
    *,
    get_engine_fn: Callable[[str], Any] = get_engine,
    format_technique_result_lines_fn: Callable[[str, str, dict], list[str]] = format_technique_result_lines,
    compute_run_service_factory: Callable[..., ComputeRunService] = ComputeRunService,
) -> int:
    # Import all technique engines so the registry is populated before lookup.
    import polynexus.core.dsc as _dsc
    import polynexus.core.ir as _ir
    import polynexus.core.waxs as _waxs
    import polynexus.core.saxs as _saxs
    import polynexus.core.nmr as _nmr

    del _dsc, _ir, _waxs, _saxs, _nmr

    engine = get_engine_fn(args.cmd)
    if engine is not None and hasattr(args, "type") and hasattr(engine, "cfg"):
        engine.cfg.experiment_type = args.type

    output = args.output or os.path.join(os.path.dirname(args.input) or ".", args.cmd + "_results")
    service = compute_run_service_factory(
        lambda technique, config=None, submodule_id=None: engine
    )
    run = service.run_direct(
        technique=args.cmd,
        path=args.input,
        output_dir=output,
        engine=engine,
        pipeline_options={"skip_to": args.skip_to},
    )
    if run.status != "completed":
        reason = ", ".join(run.reasons) or run.status
        print(f"{run.status}: {reason}", file=sys.stderr)
        return 1

    if bool(getattr(args, "json", False)):
        print(json.dumps(run.to_dict(), ensure_ascii=False, sort_keys=True))
        return 0

    assert run.result is not None
    for line in format_technique_result_lines_fn(args.cmd, output, run.result.metrics):
        print(line)
    return 0
