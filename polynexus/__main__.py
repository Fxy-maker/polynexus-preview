"""PolyNexus CLI entry point."""

import logging
logger = logging.getLogger(__name__)

import sys

from polynexus.cli.output import (
    format_batch_progress_line,
    format_batch_summary_lines,
    format_technique_result_lines,
)
from polynexus.cli.batch_preset_service import (
    apply_batch_preset_actions as _apply_batch_preset_actions_impl,
    apply_loaded_batch_preset as _apply_loaded_batch_preset_impl,
    batch_cli_overrides_from_args as _batch_cli_overrides_from_args_impl,
    batch_preset_values_from_args as _batch_preset_values_from_args_impl,
    describe_batch_task as _describe_batch_task_impl,
)
from polynexus.cli.batch_run_service import (
    analysis_evidence_from_ai_report as _analysis_evidence_from_ai_report_impl,
    analysis_evidence_from_result as _analysis_evidence_from_result_impl,
    allowed_extensions as _allowed_extensions_impl,
    extract_result_r2 as _extract_result_r2_impl,
    _persist_batch_run as _persist_batch_run_impl,
    run_batch as _run_batch_impl,
    run_batch_one as _run_batch_one_impl,
)
from polynexus.cli.run_ai_tune_service import run_ai_tune as _run_ai_tune_impl
from polynexus.cli.run_single_service import run_single as _run_single_impl
from polynexus.cli.parser import build_parser
from polynexus.utils import (
    delete_batch_preset,
    list_batch_presets,
    load_batch_last_run,
    load_batch_preset,
    save_batch_preset,
    save_batch_last_run,
)
from polynexus.core.engine import get_engine

def main():
    _configure_console_encoding()
    args = build_parser().parse_args()

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
    return _run_single(args)


def _run_single(args) -> int:
    return _run_single_impl(
        args,
        get_engine_fn=get_engine,
        format_technique_result_lines_fn=format_technique_result_lines,
    )


def _run_ai_tune(args) -> int:
    return _run_ai_tune_impl(args)


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
    return _persist_batch_run_impl(file_path, technique, result, elapsed)


def _run_batch_one(task: tuple[str, str, str]) -> dict:
    return _run_batch_one_impl(
        task,
        get_engine_fn=get_engine,
        persist_batch_run_fn=_persist_batch_run,
        logger=logger,
    )


def run_batch(args) -> int:
    return _run_batch_impl(
        args,
        apply_batch_preset_actions_fn=_apply_batch_preset_actions,
        save_batch_last_run_fn=save_batch_last_run,
        batch_preset_values_from_args_fn=_batch_preset_values_from_args,
        format_batch_progress_line_fn=format_batch_progress_line,
        format_batch_summary_lines_fn=format_batch_summary_lines,
        get_engine_fn=get_engine,
        persist_batch_run_fn=_persist_batch_run,
        logger=logger,
        run_batch_one_fn=_run_batch_one,
    )

def _batch_preset_values_from_args(args) -> dict:
    return _batch_preset_values_from_args_impl(args)


def _apply_loaded_batch_preset(args, values: dict) -> None:
    _apply_loaded_batch_preset_impl(args, values)


def _batch_cli_overrides_from_args(args) -> dict:
    return _batch_cli_overrides_from_args_impl(args)


def _describe_batch_task(values: dict) -> str:
    return _describe_batch_task_impl(values)


def _apply_batch_preset_actions(args) -> int | None:
    return _apply_batch_preset_actions_impl(args)


def _allowed_extensions(technique: str) -> set[str]:
    return _allowed_extensions_impl(technique)


def _extract_result_r2(result) -> float | None:
    return _extract_result_r2_impl(result)


def _analysis_evidence_from_result(result) -> dict:
    return _analysis_evidence_from_result_impl(result)


def _analysis_evidence_from_ai_report(report: dict) -> dict:
    return _analysis_evidence_from_ai_report_impl(report)


def _configure_console_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            logger.warning("Failed to reconfigure console encoding.", exc_info=True)


if __name__ == '__main__':
    raise SystemExit(main())
