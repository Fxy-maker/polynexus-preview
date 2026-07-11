"""AI tuning CLI runtime helpers."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Callable

from polynexus.cli.batch_run_service import analysis_evidence_from_ai_report
from polynexus.utils import detect_polymer_type, load_defaults

logger = logging.getLogger(__name__)


def run_ai_tune(
    args: Any,
    *,
    parameter_orchestrator_cls=None,
    persist_ai_tune_run_fn: Callable[[Any, dict, Path], str] | None = None,
) -> int:
    from polynexus.orchestrator import ParameterOrchestrator

    orchestrator_cls = parameter_orchestrator_cls or ParameterOrchestrator
    persist_fn = persist_ai_tune_run_fn or _persist_ai_tune_run

    def progress(event):
        before = _format_r_squared(event["before_r_squared"])
        after = _format_r_squared(event["after_r_squared"])
        changes = _format_changes(event.get("changes", {}))
        prefix = f"[Round {event['round_num']}/{event['max_rounds']}] r2 {before} -> {after}"
        status = event.get("status", "")
        if status == "rejected":
            print(f"{prefix} changes: {changes} rejected: {event.get('error', '')}")
        elif status == "rolled_back":
            suffix = " rolled back"
            if event.get("converged"):
                suffix += "; converged"
            print(f"{prefix} changes: {changes}{suffix}")
        elif status == "converged":
            if changes == "{}":
                print(f"{prefix} converged")
            else:
                print(f"{prefix} changes: {changes} converged")
        else:
            print(f"{prefix} changes: {changes}")

    try:
        report = orchestrator_cls(
            technique=args.technique,
            data_file=args.file,
            polymer_name=args.polymer,
            max_rounds=args.rounds,
            progress_callback=progress,
            submodule_override=args.submodule,
        ).run()
    except Exception as exc:
        logger.warning("AI tune execution failed.", exc_info=True)
        print(f"AI tune engine error: {exc}", file=sys.stderr)
        return 1

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        run_id = persist_fn(args, report, output_path)
        print(f"Analysis run: {run_id}")
    except Exception as exc:
        logger.warning("AI tune database persistence failed.", exc_info=True)
        print(f"AI tune database write error: {exc}", file=sys.stderr)
        return 1

    print(f"Report: {output_path.resolve()}")
    print(
        "Best r2 "
        f"{_format_r_squared(report['best_r_squared'])} "
        f"(baseline {_format_r_squared(report['baseline_r_squared'])})"
    )
    if report["best_r_squared"] < report["baseline_r_squared"]:
        return 2
    return 0 if report.get("converged") else 2


def _persist_ai_tune_run(args, report: dict, output_path: Path) -> str:
    from polynexus.data.sample_db import SampleDB

    data_file = Path(args.file)
    polymer_type = detect_polymer_type(args.polymer or data_file.stem)
    _defaults = load_defaults(polymer_type)
    best_config = report.get("best_config") or {}
    if isinstance(best_config, dict):
        best_config = dict(best_config)
    else:
        best_config = {}
    best_config.setdefault("polymer_type", polymer_type)
    submodule_map = {
        "waxs": "waxs.static",
        "dsc": "dsc.standard",
        "saxs": "saxs.static",
        "ir": "ir.standard",
    }
    submodule = args.submodule or report.get("submodule") or submodule_map.get(args.technique, f"{args.technique}.static")
    db = SampleDB()
    try:
        sample_id = db.create_sample(
            args.polymer,
            tags=["ai_tune", args.technique],
            metadata={
                "source": "ai-tune",
                "data_file": str(data_file),
            },
            temp=False,
        )
        batch_id = db.create_batch(
            sample_id,
            label=data_file.stem,
            instrument="PolyNexus ai-tune",
            condition_type="ai_tune",
            condition_values={
                "rounds": args.rounds,
                "report": str(output_path.resolve()),
            },
        )
        db.add_data_file(
            batch_id,
            str(data_file.resolve()),
            args.technique,
            submodule=submodule,
            file_type=data_file.suffix.lower().lstrip("."),
            import_order=0,
        )
        return db.create_analysis_run(
            batch_id,
            args.technique,
            submodule=submodule,
            parameters=best_config,
            results_summary={
                "ai_tuned": True,
                "polymer_name": args.polymer,
                "polymer_type": polymer_type,
                "data_file": str(data_file.resolve()),
                "report_path": str(output_path.resolve()),
                "baseline_r_squared": report.get("baseline_r_squared"),
                "best_r_squared": report.get("best_r_squared"),
                "improvement": report.get("improvement", {}),
                "converged": report.get("converged"),
                "convergence_reason": report.get("convergence_reason"),
                "rounds": report.get("rounds"),
            },
            analysis_evidence=analysis_evidence_from_ai_report(report),
            output_dir=str(output_path.resolve().parent),
            ai_tuned=True,
        )
    finally:
        db.close()


def _format_r_squared(value) -> str:
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return "nan"


def _format_changes(changes: dict) -> str:
    if not changes:
        return "{}"
    parts = [f"{key}: {value}" for key, value in changes.items()]
    return "{" + ", ".join(parts) + "}"
