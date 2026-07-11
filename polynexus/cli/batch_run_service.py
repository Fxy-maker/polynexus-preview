"""Batch CLI runtime helpers."""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Any, Callable

from polynexus.core.engine import SUPPORTED_FORMATS
from polynexus.utils import detect_polymer_type

logger = logging.getLogger(__name__)


FALLBACK_EXTS = {".dat", ".csv", ".txt", ".edf", ".raw", ".fio", ".nxs", ".h5"}


def allowed_extensions(technique: str) -> set[str]:
    technique = str(technique or "").lower()
    allowed = set(SUPPORTED_FORMATS.get(technique, []))
    return {ext.lower() for ext in (allowed or FALLBACK_EXTS)}


def extract_result_r2(result) -> float | None:
    if result is None:
        return None
    value = getattr(result, "r_squared", None)
    if value is None and isinstance(result, dict):
        value = result.get("r_squared")
        if value is None:
            params = result.get("parameters", {})
            if isinstance(params, dict):
                value = params.get("r_squared") or params.get("r2")
    if value is None and hasattr(result, "parameters"):
        params = getattr(result, "parameters", {}) or {}
        if isinstance(params, dict):
            value = params.get("r_squared") or params.get("r2")
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def analysis_evidence_from_result(result) -> dict:
    if result is None:
        return {}
    if isinstance(result, dict):
        evidence = result.get("analysis_evidence")
    else:
        evidence = getattr(result, "analysis_evidence", {})
    return dict(evidence) if isinstance(evidence, dict) else {}


def analysis_evidence_from_ai_report(report: dict) -> dict:
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
                    "r_squared": extract_result_r2(result),
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
                    "r_squared": extract_result_r2(result),
                },
                analysis_evidence=analysis_evidence_from_result(result),
                output_dir=str(data_file.parent.resolve()),
                ai_tuned=False,
            )
        finally:
            db.close()
    except Exception:
        logger.warning("Failed to persist batch run metadata: %s", file_path, exc_info=True)


def run_batch_one(
    task: tuple[str, str, str],
    *,
    get_engine_fn: Callable[[str], Any],
    persist_batch_run_fn: Callable[[str, str, Any, float], None],
    logger,
    extract_result_r2_fn: Callable[[Any], float | None] = extract_result_r2,
) -> dict:
    file_path_str, technique, output_dir_str = task
    file_path = Path(file_path_str)
    output_dir = Path(output_dir_str)
    started = time.time()
    status = "OK"
    result = None
    try:
        engine = get_engine_fn(technique)
        if engine is None:
            raise RuntimeError(f"Unknown technique: {technique}")
        out_path = output_dir / file_path.stem
        result = engine.run_pipeline(str(file_path), str(out_path))
        elapsed = time.time() - started
        persist_batch_run_fn(str(file_path), technique, result, elapsed)
    except Exception as exc:
        logger.warning("Batch analysis failed: %s %s", file_path.name, exc, exc_info=True)
        status = f"FAIL: {exc}"
    return {
        "file": file_path.name,
        "technique": technique,
        "status": status,
        "r2": extract_result_r2_fn(result),
        "elapsed": round(time.time() - started, 2),
    }


def run_batch(
    args,
    *,
    apply_batch_preset_actions_fn: Callable[[Any], int | None],
    save_batch_last_run_fn: Callable[[dict], None],
    batch_preset_values_from_args_fn: Callable[[Any], dict],
    format_batch_progress_line_fn: Callable[[dict[str, Any]], str],
    format_batch_summary_lines_fn: Callable[[list[dict[str, Any]]], list[str]],
    get_engine_fn: Callable[[str], Any],
    logger=logger,
    persist_batch_run_fn: Callable[[str, str, Any, float], None] | None = None,
    run_batch_one_fn: Callable[[tuple[str, str, str]], dict] | None = None,
) -> int:
    preset_result = apply_batch_preset_actions_fn(args)
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

    files = [
        path for path in input_dir.glob(args.pattern)
        if path.is_file() and path.suffix.lower() in allowed_extensions(args.technique)
    ]
    if not files:
        print("No supported files found. Check the directory and --pattern.", file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir) if args.output_dir else input_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Found {len(files)} file(s). Starting batch analysis [{args.technique.upper()}]...")
    save_batch_last_run_fn(batch_preset_values_from_args_fn(args))

    tasks = [(str(path), args.technique, str(output_dir)) for path in files]
    results_summary = []
    workers = max(1, int(getattr(args, "workers", 1) or 1))
    persist_fn = persist_batch_run_fn or _persist_batch_run
    run_one = run_batch_one_fn or (
        lambda task: run_batch_one(
            task,
            get_engine_fn=get_engine_fn,
            persist_batch_run_fn=persist_fn,
            logger=logger,
        )
    )

    if workers > 1:
        print(
            "Warning: requested workers="
            f"{workers}; running sequentially to avoid multiprocessing pickling issues."
        )

    for task in tasks:
        row = run_one(task)
        results_summary.append(row)
        print(format_batch_progress_line_fn(row))

    for line in format_batch_summary_lines_fn(results_summary):
        print(line)

    if any(row.get("status") != "OK" for row in results_summary):
        return 1
    return 0
