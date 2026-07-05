"""PolyNexus CLI entry point."""

import logging
logger = logging.getLogger(__name__)

import argparse, json, os, sys, time
from pathlib import Path

from polynexus.utils import (
    delete_batch_preset,
    detect_polymer_type,
    list_batch_presets,
    load_batch_last_run,
    load_batch_preset,
    load_defaults,
    save_batch_preset,
    save_batch_last_run,
)
from polynexus.core.engine import SUPPORTED_FORMATS, get_engine

FALLBACK_EXTS = {".dat", ".csv", ".txt", ".edf", ".raw", ".fio", ".nxs", ".h5"}

def main():
    _configure_console_encoding()
    p = argparse.ArgumentParser(
        prog='polynexus',
        description='PolyNexus -- Multi-Technique Polymer Characterization Platform'
    )
    p.add_argument('--gui', action='store_true', help='Launch GUI')
    sub = p.add_subparsers(dest='cmd', help='Technique')
    ps = sub.add_parser('saxs', help='SAXS'); ps.add_argument('input'); ps.add_argument('-o', '--output', default=''); ps.add_argument('--skip-to', default=None, choices=['preprocess','analyze','plot']); ps.add_argument('--type', default='temperature', choices=['static', 'strain', 'temperature'])
    pd = sub.add_parser('dsc', help='DSC'); pd.add_argument('input'); pd.add_argument('-o', '--output', default=''); pd.add_argument('--skip-to', default=None, choices=['preprocess','analyze','plot'])
    pi = sub.add_parser('ir', help='IR'); pi.add_argument('input'); pi.add_argument('-o', '--output', default=''); pi.add_argument('--skip-to', default=None, choices=['preprocess','analyze','plot'])
    pw = sub.add_parser('waxs', help='WAXS'); pw.add_argument('input'); pw.add_argument('-o', '--output', default=''); pw.add_argument('--skip-to', default=None, choices=['preprocess','analyze','plot'])
    pn = sub.add_parser('nmr', help='NMR'); pn.add_argument('input'); pn.add_argument('-o', '--output', default=''); pn.add_argument('--skip-to', default=None, choices=['preprocess','analyze','plot'])
    pg = sub.add_parser('gui', help='AI tuning convergence viewer')
    pg.add_argument('--dry-run', action='store_true', help='Print AI tuning counts without opening a window')
    pg.add_argument('--db', default=None, help='Path to polynexus_samples.db')
    pa = sub.add_parser('ai-tune', help='AI-assisted parameter tuning')
    pa.add_argument('--technique', default='waxs', choices=['waxs', 'dsc', 'saxs', 'ir', 'nmr'], help='Technique to tune')
    pa.add_argument('--file', '--input', dest='file', required=True, help='Input data file')
    pa.add_argument('--polymer', required=True, help='Polymer name, e.g. PA6')
    pa.add_argument('--submodule', default=None, help='Optional technique submodule override')
    pa.add_argument('--rounds', '--max-rounds', dest='rounds', type=int, default=5, help='Max tuning rounds')
    pa.add_argument('--model', default='gpt-5.4-mini', help='LLM model name for reporting/compatibility')
    pa.add_argument('--reasoning', default='low', help='Reasoning effort label for reporting/compatibility')
    pa.add_argument('--output', default='ai_tune_report.json', help='Output JSON report path')
    pb = sub.add_parser('batch', help='Batch-analyze all supported files in a directory')
    pb.add_argument('input_dir', nargs='?', help='Input directory path')
    pb.add_argument('--technique', choices=['saxs', 'waxs', 'dsc', 'ir', 'nmr'], help='Technique to analyze')
    pb.add_argument('--pattern', default='*', metavar='GLOB', help='Filename glob filter, default *')
    pb.add_argument('--workers', type=int, default=1, metavar='N', help='Parallel worker count, default 1')
    pb.add_argument('--output-dir', metavar='DIR', help='Batch output directory, default same as input directory')
    pb.add_argument('--preset', metavar='NAME', help='Load a saved batch preset by name')
    pb.add_argument('--save-preset', metavar='NAME', help='Save current batch arguments as a preset, then exit')
    pb.add_argument('--delete-preset', metavar='NAME', help='Delete a saved batch preset, then exit')
    pb.add_argument('--list-presets', action='store_true', help='List saved batch presets, then exit')
    pb.add_argument('--rerun-last', action='store_true', help='Rerun the most recent batch task snapshot')
    args = p.parse_args()

    if args.gui or not args.cmd:
        from polynexus.app import main as gui_main
        gui_main()
        return 0

    if args.cmd == 'ai-tune':
        return _run_ai_tune(args)
    if args.cmd == 'batch':
        return run_batch(args)
    if args.cmd == 'gui':
        # Launch the AI tuning convergence viewer.
        from polynexus.app import main as gui_main
        gui_main()
        return 0

    # Import all technique engines to populate registry
    import polynexus.core.dsc as _dsc
    import polynexus.core.ir as _ir
    import polynexus.core.waxs as _waxs
    import polynexus.core.saxs as _saxs
    import polynexus.core.nmr as _nmr

    engine = get_engine(args.cmd)
    if engine is None:
        print(f"Unknown technique: {args.cmd}")
        return 1

    # Pass --type to engine config (SAXS, WAXS, ...)
    if hasattr(args, 'type') and hasattr(engine, 'cfg'):
        engine.cfg.experiment_type = args.type

    output = args.output or os.path.join(os.path.dirname(args.input) or '.', args.cmd + '_results')
    result = engine.run_pipeline(args.input, output, skip_to=args.skip_to)

    print()
    print("=" * 50)
    print(f"{args.cmd.upper()} Results:")
    for k, v in result.parameters.items():
        print(f"  {k}: {v}")
    print(f"Output: {output}")
    return 0


def _run_ai_tune(args) -> int:
    from polynexus.orchestrator import ParameterOrchestrator

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
        report = ParameterOrchestrator(
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
        run_id = _persist_ai_tune_run(args, report, output_path)
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
            analysis_evidence=_analysis_evidence_from_ai_report(report),
            output_dir=str(output_path.resolve().parent),
            ai_tuned=True,
        )
    finally:
        db.close()


def _allowed_extensions(technique: str) -> set[str]:
    technique = str(technique or "").lower()
    allowed = set(SUPPORTED_FORMATS.get(technique, []))
    return {ext.lower() for ext in (allowed or FALLBACK_EXTS)}


def _extract_result_r2(result) -> float | None:
    if result is None:
        return None
    value = getattr(result, "r_squared", None)
    if value is None and isinstance(result, dict):
        value = result.get("r_squared")
    if value is None and hasattr(result, "parameters"):
        params = getattr(result, "parameters", {}) or {}
        if isinstance(params, dict):
            value = params.get("r_squared") or params.get("r2")
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _analysis_evidence_from_result(result) -> dict:
    if result is None:
        return {}
    if isinstance(result, dict):
        evidence = result.get("analysis_evidence")
    else:
        evidence = getattr(result, "analysis_evidence", {})
    return dict(evidence) if isinstance(evidence, dict) else {}


def _analysis_evidence_from_ai_report(report: dict) -> dict:
    best_record = report.get("best_record", {}) if isinstance(report, dict) else {}
    if isinstance(best_record, dict) and isinstance(best_record.get("analysis_evidence"), dict):
        return dict(best_record["analysis_evidence"])
    evidence = report.get("analysis_evidence", {}) if isinstance(report, dict) else {}
    return dict(evidence) if isinstance(evidence, dict) else {}


def _persist_batch_run(file_path: str, technique: str, result, elapsed: float) -> None:
    try:
        from polynexus.data.sample_db import SampleDB

        data_file = Path(file_path)
        polymer_name = detect_polymer_type(data_file.stem) or "unknown"
        db = SampleDB()
        try:
            parameters = {}
            result_params = getattr(result, "parameters", {}) or {}
            if isinstance(result_params, dict):
                parameters = dict(result_params)
            parameters.update(
                {
                    "source": "batch_cli",
                    "technique": technique,
                    "r_squared": _extract_result_r2(result),
                    "elapsed_s": round(elapsed, 3),
                    "polymer_type": polymer_name,
                }
            )

            sample_id = db.create_sample(
                polymer_name,
                tags=["batch_cli", technique],
                metadata={"source": "batch_cli", "data_file": str(data_file.resolve())},
                temp=False,
            )
            batch_id = db.create_batch(
                sample_id,
                label=data_file.stem,
                instrument="PolyNexus batch",
                condition_type="batch_cli",
                condition_values={"technique": technique},
            )
            db.add_data_file(
                batch_id,
                str(data_file.resolve()),
                technique,
                submodule=f"{technique}.batch",
                file_type=data_file.suffix.lower().lstrip("."),
                import_order=0,
            )
            db.create_analysis_run(
                batch_id,
                technique,
                submodule=f"{technique}.batch",
                parameters=parameters,
                results_summary={
                    "source": "batch_cli",
                    "technique": technique,
                    "data_file": str(data_file.resolve()),
                    "elapsed_s": round(elapsed, 3),
                    "r_squared": _extract_result_r2(result),
                },
                analysis_evidence=_analysis_evidence_from_result(result),
                output_dir=str(data_file.parent.resolve()),
                ai_tuned=False,
            )
        finally:
            db.close()
    except Exception:
        logger.warning("Failed to persist batch run metadata: %s", file_path, exc_info=True)


def _run_batch_one(task: tuple[str, str, str]) -> dict:
    file_path_str, technique, output_dir_str = task
    file_path = Path(file_path_str)
    output_dir = Path(output_dir_str)
    started = time.time()
    status = "OK"
    result = None
    try:
        engine = get_engine(technique)
        if engine is None:
            raise RuntimeError(f"Unknown technique: {technique}")
        out_path = output_dir / file_path.stem
        result = engine.run_pipeline(str(file_path), str(out_path))
        elapsed = time.time() - started
        _persist_batch_run(str(file_path), technique, result, elapsed)
    except Exception as exc:
        elapsed = time.time() - started
        logger.warning("Batch analysis failed: %s %s", file_path.name, exc, exc_info=True)
        status = f"FAIL: {exc}"
    return {
        "file": file_path.name,
        "technique": technique,
        "status": status,
        "r2": _extract_result_r2(result),
        "elapsed": round(time.time() - started, 2),
    }


def run_batch(args) -> int:
    preset_result = _apply_batch_preset_actions(args)
    if preset_result is not None:
        return preset_result

    if not getattr(args, "input_dir", None):
        print("Batch input directory is required.", file=sys.stderr)
        return 2
    if not getattr(args, "technique", None):
        print("Batch technique is required.", file=sys.stderr)
        return 2

    input_dir = Path(args.input_dir)
    if not input_dir.is_dir():
        print(f"Error: {input_dir} is not a valid directory.", file=sys.stderr)
        return 2

    allowed = _allowed_extensions(args.technique)
    files = [
        path for path in input_dir.glob(args.pattern)
        if path.is_file() and path.suffix.lower() in allowed
    ]
    if not files:
        print("No supported files found. Check the directory and --pattern.", file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir) if args.output_dir else input_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Found {len(files)} file(s). Starting batch analysis [{args.technique.upper()}]...")
    save_batch_last_run(_batch_preset_values_from_args(args))

    tasks = [(str(path), args.technique, str(output_dir)) for path in files]
    results_summary = []
    workers = max(1, int(getattr(args, "workers", 1) or 1))

    if workers > 1:
        print(
            "Warning: requested workers="
            f"{workers}; running sequentially to avoid multiprocessing pickling issues."
        )

    for task in tasks:
        row = _run_batch_one(task)
        results_summary.append(row)
        tag = "OK" if row["status"] == "OK" else "FAIL"
        print(f"  [{tag}] {row['file']}  {row['elapsed']}s")

    ok_rows = [row for row in results_summary if row["status"] == "OK"]
    bad_rows = [row for row in results_summary if row["status"] != "OK"]
    print()
    print(f"{'File':<40} {'Technique':<10} {'Status':<12} {'R2':<10} {'Elapsed(s)'}")
    print("-" * 90)
    for row in results_summary:
        r2 = row.get("r2")
        r2_str = f"{r2:.4f}" if isinstance(r2, (int, float)) else "-"
        print(f"{row['file']:<40} {row['technique']:<10} {row['status']:<12} {r2_str:<10} {row['elapsed']}")
    print("-" * 90)
    print(
        f"Completed: {len(ok_rows)} succeeded, {len(bad_rows)} failed, "
        f"{len(results_summary)} total."
    )

    if bad_rows:
        print("\nFailed files:")
        for row in bad_rows:
            print(f"  {row['file']} -> {row['status']}")
        return 1
    return 0

def _batch_preset_values_from_args(args) -> dict:
    return {
        "input_dir": str(getattr(args, "input_dir", "") or ""),
        "technique": str(getattr(args, "technique", "") or ""),
        "pattern": str(getattr(args, "pattern", "*") or "*"),
        "workers": int(getattr(args, "workers", 1) or 1),
        "output_dir": str(getattr(args, "output_dir", "") or ""),
    }


def _apply_loaded_batch_preset(args, values: dict) -> None:
    if not isinstance(values, dict):
        return
    for key in ("input_dir", "technique", "pattern", "workers", "output_dir"):
        if key in values:
            setattr(args, key, values.get(key))


def _batch_cli_overrides_from_args(args) -> dict:
    overrides = {}
    if getattr(args, "input_dir", None):
        overrides["input_dir"] = getattr(args, "input_dir")
    if getattr(args, "technique", None):
        overrides["technique"] = getattr(args, "technique")
    pattern = getattr(args, "pattern", "*")
    if pattern not in (None, "", "*"):
        overrides["pattern"] = pattern
    workers = getattr(args, "workers", 1)
    if workers not in (None, 1):
        overrides["workers"] = workers
    if getattr(args, "output_dir", None):
        overrides["output_dir"] = getattr(args, "output_dir")
    return overrides


def _describe_batch_task(values: dict) -> str:
    if not isinstance(values, dict):
        return ""
    parts = []
    technique = str(values.get("technique") or "").strip()
    input_dir = str(values.get("input_dir") or "").strip()
    pattern = str(values.get("pattern") or "").strip()
    output_dir = str(values.get("output_dir") or "").strip()
    workers = values.get("workers")
    if technique:
        parts.append(f"technique={technique}")
    if input_dir:
        parts.append(f"input_dir={input_dir}")
    if pattern:
        parts.append(f"pattern={pattern}")
    if output_dir:
        parts.append(f"output_dir={output_dir}")
    if workers not in (None, ""):
        parts.append(f"workers={workers}")
    return ", ".join(parts)


def _apply_batch_preset_actions(args) -> int | None:
    preset_name = str(getattr(args, "preset", "") or "").strip()
    overrides = _batch_cli_overrides_from_args(args)
    if preset_name and getattr(args, "rerun_last", False):
        print("Use either --preset or --rerun-last, not both.", file=sys.stderr)
        return 2

    if preset_name:
        values = load_batch_preset(preset_name)
        if values is None:
            print(f"Batch preset not found: {preset_name}", file=sys.stderr)
            return 2
        _apply_loaded_batch_preset(args, values)
        _apply_loaded_batch_preset(args, overrides)
        details = _describe_batch_task(_batch_preset_values_from_args(args))
        if details:
            print(f"Loaded batch preset: {preset_name} ({details})")
        else:
            print(f"Loaded batch preset: {preset_name}")

    if getattr(args, "rerun_last", False):
        values = load_batch_last_run()
        if values is None:
            print("No previous batch task snapshot found.", file=sys.stderr)
            return 2
        _apply_loaded_batch_preset(args, values)
        _apply_loaded_batch_preset(args, overrides)
        details = _describe_batch_task(_batch_preset_values_from_args(args))
        if details:
            print(f"Loaded last batch task snapshot. ({details})")
        else:
            print("Loaded last batch task snapshot.")

    if getattr(args, "list_presets", False):
        names = list_batch_presets()
        if not names:
            print("No batch presets saved.")
        else:
            print("Batch presets:")
            for name in names:
                values = load_batch_preset(name)
                details = _describe_batch_task(values or {})
                if details:
                    print(f"  {name} ({details})")
                else:
                    print(f"  {name}")
        return 0

    delete_name = str(getattr(args, "delete_preset", "") or "").strip()
    if delete_name:
        values = load_batch_preset(delete_name)
        if delete_batch_preset(delete_name):
            details = _describe_batch_task(values or {})
            if details:
                print(f"Deleted batch preset: {delete_name} ({details})")
            else:
                print(f"Deleted batch preset: {delete_name}")
            return 0
        print(f"Batch preset not found: {delete_name}", file=sys.stderr)
        return 2

    save_name = str(getattr(args, "save_preset", "") or "").strip()
    if save_name:
        if not getattr(args, "input_dir", None):
            print("Batch input directory is required to save a preset.", file=sys.stderr)
            return 2
        if not getattr(args, "technique", None):
            print("Batch technique is required to save a preset.", file=sys.stderr)
            return 2
        values = _batch_preset_values_from_args(args)
        save_batch_preset(save_name, values)
        details = _describe_batch_task(values)
        if details:
            print(f"Saved batch preset: {save_name} ({details})")
        else:
            print(f"Saved batch preset: {save_name}")
        return 0

    return None


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


def _configure_console_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            logger.warning("Failed to reconfigure console encoding.", exc_info=True)


if __name__ == '__main__':
    raise SystemExit(main())
