"""Single-technique CLI runtime helpers."""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
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
    import polynexus.core.tga as _tga
    import polynexus.core.dma as _dma
    import polynexus.core.rheology as _rheology
    import polynexus.core.mechanics as _mechanics
    import polynexus.core.sec as _sec

    del _dsc, _ir, _waxs, _saxs, _nmr, _tga, _dma, _rheology, _mechanics, _sec

    canonical_technique = "sec" if args.cmd == "gpc" else args.cmd
    engine = get_engine_fn(canonical_technique)
    if engine is not None and hasattr(args, "type") and hasattr(engine, "cfg"):
        engine.cfg.experiment_type = args.type

    output = args.output or os.path.join(
        os.path.dirname(args.input) or ".", canonical_technique + "_results"
    )
    pipeline_options: dict[str, Any] = {"skip_to": args.skip_to}
    analysis_spec_path = getattr(args, "analysis_spec", None)
    if analysis_spec_path:
        try:
            analysis_spec = json.loads(
                Path(str(analysis_spec_path)).expanduser().read_text(encoding="utf-8")
            )
        except (OSError, UnicodeError, TypeError, ValueError, json.JSONDecodeError):
            print("needs_input: analysis_spec_invalid", file=sys.stderr)
            return 2
        if not isinstance(analysis_spec, dict):
            print("needs_input: analysis_spec_invalid", file=sys.stderr)
            return 2
        option_key = {
            "sec": "sec_analysis",
            "rheology": "rheology_analysis",
            "tga": "tga_kinetics",
            "dma": "dma_tts",
            "mechanics": "mechanics_analysis",
        }.get(canonical_technique)
        if option_key is None:
            print("needs_input: analysis_spec_unsupported", file=sys.stderr)
            return 2
        if canonical_technique == "mechanics" and "advanced" in analysis_spec and not any(
            key in analysis_spec
            for key in ("test_mode", "stress_measurement_id", "geometry")
        ):
            pipeline_options["mechanics_advanced"] = analysis_spec["advanced"]
        elif canonical_technique == "rheology" and "advanced" in analysis_spec and not any(
            key in analysis_spec for key in ("yield_stress", "lve")
        ):
            pipeline_options["rheology_advanced"] = analysis_spec["advanced"]
        else:
            pipeline_options[option_key] = analysis_spec
    service = compute_run_service_factory(
        lambda technique, config=None, submodule_id=None: engine
    )
    run_arguments = {
        "technique": canonical_technique,
        "path": args.input,
        "output_dir": output,
        "engine": engine,
        "pipeline_options": pipeline_options,
    }
    if bool(getattr(args, "json", False)):
        with redirect_stdout(io.StringIO()):
            run = service.run_direct(**run_arguments)
    else:
        run = service.run_direct(**run_arguments)
    if run.status != "completed":
        reason = ", ".join(run.reasons) or run.status
        print(f"{run.status}: {reason}", file=sys.stderr)
        return 1

    if bool(getattr(args, "json", False)):
        print(json.dumps(run.to_dict(), ensure_ascii=False, sort_keys=True))
        return 0

    assert run.result is not None
    for line in format_technique_result_lines_fn(
        canonical_technique, output, run.result.metrics
    ):
        print(line)
    return 0
