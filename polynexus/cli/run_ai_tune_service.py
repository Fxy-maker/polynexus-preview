"""AI tuning CLI runtime helpers."""

from __future__ import annotations

import json
import logging
import sys
import hashlib
from pathlib import Path
from typing import Any, Callable, Mapping

from polynexus.cli.batch_run_service import analysis_evidence_from_ai_report
from polynexus.core.compute.projection import read_compute_run_projection
from polynexus.core.project_workflow import AnalysisPlan, AnalysisPlanEvaluation, CandidateEvaluation, project_analysis_plan_evaluation
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

    try:
        _attach_compatibility_plan(args, report)
    except (TypeError, ValueError) as exc:
        logger.warning("AI tune report contract validation failed.", exc_info=True)
        print(f"AI tune report error: {exc}", file=sys.stderr)
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


def _attach_compatibility_plan(args: Any, report: dict) -> None:
    """Wrap legacy tuning output in the public immutable plan/evaluation DTOs."""
    source_path = Path(args.file).resolve()
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    technique = str(args.technique or "unknown").strip().lower()
    default_config = dict(report.get("baseline_config") or {})
    best_config = dict(report.get("best_config") or {})
    candidate_configs = ({"id": "legacy_best", "config": best_config, "generation_rule": "legacy_ai_tune_compatibility"},)
    canonical_template = _canonical_template_for_plan(report, technique)
    if canonical_template is None:
        canonical_template = {
            "template_id": f"{technique}.legacy-input",
            "conversion_version": "legacy-v1",
        }
    plan = AnalysisPlan.create(
        source_files=({"path": str(source_path), "sha256": source_hash, "byte_size": source_path.stat().st_size, "source_order": 0},),
        canonical_template=canonical_template,
        algorithm={"algorithm_id": f"{technique}.legacy-ai-tune", "algorithm_version": "legacy-v1"},
        default_config=default_config,
        candidate_configs=candidate_configs,
        protected_metrics=("source_integrity",),
        scientific_constraints=("human_scientific_review",),
        review_thresholds={"legacy_report": True},
        selected_candidate_id="legacy_best",
        approval={"state": "pending_human_review"},
        replay={"status": "not_replayed", "source_manifest_hash": source_hash, "replayed_from_run_id": None},
    )
    improvement = _finite_float(report.get("improvement", {}).get("absolute") if isinstance(report.get("improvement"), dict) else None)
    score = max(0.0, 1.0 - improvement) if improvement is not None else 0.0
    status = "stable" if bool(report.get("converged")) else "sensitive"
    evaluation = AnalysisPlanEvaluation.create(
        plan_id=plan.plan_id,
        plan_hash=plan.plan_hash,
        plan_version=plan.plan_version,
        candidates=(CandidateEvaluation("legacy_best", status, score, ("source_integrity",), ("legacy_ai_tune_compatibility",)),),
        selected_candidate_id="legacy_best",
        review_required=True,
        review_limits=("human_scientific_review", "legacy_single_score_not_scientific_acceptance"),
        replay=dict(plan.replay),
    )
    report["analysis_plan"] = plan.to_dict()
    report["analysis_plan_evaluation"] = project_analysis_plan_evaluation(plan, evaluation)


def _canonical_template_for_plan(report: Mapping[str, Any], technique: str) -> dict[str, Any] | None:
    """Project the shared run's canonical input identity into the plan DTO.

    The adaptive plan has its own candidate/configuration fields, but its input
    template must describe the same source-bound conversion as the shared run.
    A completely absent projection retains the historical compatibility plan;
    a present malformed projection is rejected before persistence.
    """
    projection = read_compute_run_projection(report)
    if projection.present and not projection.valid:
        raise ValueError(
            "AI tune compute_run projection is invalid: "
            + ",".join(projection.reason_codes)
        )
    if not projection.present:
        return None
    compute_run = projection.payload
    if not isinstance(compute_run, Mapping):
        raise ValueError("AI tune compute_run projection is invalid: payload missing")
    template = compute_run.get("canonical_template")
    if not isinstance(template, Mapping):
        raise ValueError(
            "AI tune compute_run projection is invalid: canonical_template missing"
        )
    template_id = str(template.get("template_id") or "").strip()
    record = template.get("conversion_record")
    if not isinstance(record, Mapping):
        raise ValueError(
            "AI tune compute_run projection is invalid: canonical_template conversion_record missing"
        )
    conversion_version = str(
        template.get("conversion_version")
        or record.get("conversion_id")
        or ""
    ).strip()
    if not template_id or not conversion_version:
        raise ValueError(
            "AI tune compute_run projection is invalid: canonical_template identity missing"
        )
    projected: dict[str, Any] = {
        "template_id": template_id,
        "conversion_version": conversion_version,
    }
    for key in ("source_artifact_id", "content_hash"):
        value = template.get(key)
        if value is not None and str(value).strip():
            projected[key] = str(value)
    conversion_hash = record.get("conversion_hash")
    if conversion_hash is not None and str(conversion_hash).strip():
        projected["conversion_hash"] = str(conversion_hash)
    return projected


def _finite_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and abs(number) != float("inf") else None


def _persist_ai_tune_run(args, report: dict, output_path: Path) -> str:
    shared_projection = read_compute_run_projection(report)
    if shared_projection.present and not shared_projection.valid:
        raise ValueError(
            "AI tune compute_run projection is invalid: "
            + ",".join(shared_projection.reason_codes)
        )
    shared_compute_run = shared_projection.payload if shared_projection.present else None

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
        results_summary = {
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
        }
        # Preserve the strict absence-versus-present distinction.  Writing a
        # ``compute_run: null`` key would turn a legacy report into an
        # explicitly malformed shared projection for every downstream reader.
        if shared_projection.present:
            results_summary["compute_run"] = shared_compute_run
        return db.create_analysis_run(
            batch_id,
            args.technique,
            submodule=submodule,
            parameters=best_config,
            results_summary=results_summary,
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
