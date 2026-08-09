"""Pure helpers for GUI work-memory composition."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from .analysis_history_service import format_history_timestamp as format_history_timestamp_value
from .i18n import tr
from .workspace_context_service import (
    work_memory_summary_text,  # noqa: F401
    workspace_context_summary_text,  # noqa: F401
)


@dataclass(frozen=True)
class WorkMemoryDbSnapshot:
    sample_count: int = 0
    batch_count: int = 0
    recent_run: dict[str, Any] | None = None
    recent_sample: dict[str, Any] | None = None
    recent_batch: dict[str, Any] | None = None


def build_work_memory_slice(label, detail, action_key="", callback=None, accent=""):
    return {
        "label": str(label or "").strip(),
        "detail": str(detail or "").strip(),
        "action_key": str(action_key or "").strip(),
        "callback": callback,
        "accent": str(accent or "").strip(),
    }


def collect_work_memory_db_snapshot(db, *, sample_limit: int = 1000) -> WorkMemoryDbSnapshot:
    get_compact_snapshot = getattr(db, "get_work_memory_snapshot", None)
    if callable(get_compact_snapshot):
        try:
            compact_snapshot = get_compact_snapshot()
        except Exception:
            compact_snapshot = None
        if isinstance(compact_snapshot, dict):
            return WorkMemoryDbSnapshot(
                sample_count=int(compact_snapshot.get("sample_count") or 0),
                batch_count=int(compact_snapshot.get("batch_count") or 0),
                recent_run=(
                    compact_snapshot.get("recent_run")
                    if isinstance(compact_snapshot.get("recent_run"), dict)
                    else None
                ),
                recent_sample=(
                    compact_snapshot.get("recent_sample")
                    if isinstance(compact_snapshot.get("recent_sample"), dict)
                    else None
                ),
                recent_batch=(
                    compact_snapshot.get("recent_batch")
                    if isinstance(compact_snapshot.get("recent_batch"), dict)
                    else None
                ),
            )

    try:
        samples = db.list_samples(limit=sample_limit)
    except Exception:
        samples = []

    sample_count = len(samples)
    batch_count = 0
    recent_run = None
    recent_sample = None
    recent_batch = None

    for sample in samples:
        sample_id = str(sample.get("id") or "")
        if not sample_id:
            continue
        batches = db.get_batches(sample_id)
        batch_count += len(batches)
        if recent_sample is None:
            recent_sample = sample
        for batch in batches:
            if recent_batch is None:
                recent_batch = batch
            runs = db.get_analysis_runs(batch.get("id", ""))
            if runs and recent_run is None:
                recent_run = runs[0]

    return WorkMemoryDbSnapshot(
        sample_count=sample_count,
        batch_count=batch_count,
        recent_run=recent_run,
        recent_sample=recent_sample,
        recent_batch=recent_batch,
    )


def compose_current_work_memory_detail(
    *,
    summary_text: str = "",
    context_text: str = "",
    origin_text: str = "",
    confirmed_text: str = "",
    benchmark_text: str = "",
    chain_text: str = "",
    review_summary: str = "",
) -> str:
    detail = " | ".join(
        part
        for part in [
            str(summary_text or "").strip(),
            str(context_text or "").strip(),
            str(origin_text or "").strip(),
            str(confirmed_text or "").strip(),
            str(benchmark_text or "").strip(),
            str(chain_text or "").strip(),
        ]
        if part
    )
    review_text = str(review_summary or "").strip()
    if review_text and review_text not in detail:
        detail = " | ".join(part for part in [detail, review_text] if part)
    return detail


def compose_calibration_work_memory_detail(*, scope_label: str, has_recent_calibration: bool) -> str:
    scope_text = str(scope_label or "").strip() or tr("WORKFLOW_SUBMODULE_NONE")
    if has_recent_calibration:
        return tr("WORK_MEMORY_CALIBRATION_READY", scope_text)
    return tr("WORK_MEMORY_CALIBRATION_EMPTY", scope_text)


def compose_recent_history_work_memory_detail(
    *,
    context_text: str = "",
    created_text: str = "",
    origin_text: str = "",
    confirmed_text: str = "",
    summary_text: str = "",
    output_dir: str = "",
) -> str:
    detail = " | ".join(
        part
        for part in [
            str(context_text or "").strip(),
            str(created_text or "").strip(),
            str(origin_text or "").strip(),
            str(confirmed_text or "").strip(),
            str(summary_text or "").strip(),
        ]
        if part
    )
    output_path = str(output_dir or "").strip()
    if output_path:
        output_name = os.path.basename(output_path.rstrip("/\\")) or output_path
        detail = " | ".join(part for part in [detail, output_name] if part)
    return detail


def compose_sample_work_memory_detail(sample, recent_batch=None) -> str:
    current = sample if isinstance(sample, dict) else {}
    batch = recent_batch if isinstance(recent_batch, dict) else {}
    sample_name = str(current.get("polymer_name") or "").strip()
    family = str(current.get("family") or "").strip()
    aliases = current.get("aliases") if isinstance(current.get("aliases"), list) else []
    alias_text = ", ".join(str(item) for item in aliases[:2] if str(item).strip())
    batch_text = str(batch.get("label") or "").strip()
    detail = " | ".join(part for part in [sample_name, family, alias_text, batch_text] if part)
    return detail


def compose_joint_work_memory_detail(
    *,
    summary_text: str = "",
    reminder_text: str = "",
    compare_hint_text: str = "",
) -> str:
    detail_parts = [str(summary_text or "").strip() or tr("WORK_MEMORY_JOINT_READY")]
    reminder = str(reminder_text or "").strip()
    compare_hint = str(compare_hint_text or "").strip()
    if reminder:
        detail_parts.append(reminder)
    if compare_hint:
        detail_parts.append(compare_hint)
    return " | ".join(part for part in detail_parts if part)


def compose_work_memory_meta_detail(*, sample_count: int = 0, batch_count: int = 0) -> str:
    meta = []
    if sample_count:
        meta.append(tr("WORK_MEMORY_SAMPLE_COUNT", sample_count))
    if batch_count:
        meta.append(tr("WORK_MEMORY_BATCH_COUNT", batch_count))
    if meta:
        return "  |  ".join(meta)
    return tr("WORK_MEMORY_DEFAULT_DETAIL")


def build_work_memory_payload(window) -> dict:
    db = window._ensure_sample_db()
    current_result = window._results.get(str(getattr(window, "_current_technique", "") or "").strip().lower())
    db_snapshot = collect_work_memory_db_snapshot(db)
    slices = []

    if current_result is not None:
        current_detail = ""
        if hasattr(window, "_results_summary_label"):
            current_detail = str(window._results_summary_label.text() or "").strip()
        current_context = str(window._current_result_label_for_confirmation() or "").strip()
        current_origin = window._current_result_origin_label()
        current_confirmed = window._results_confirm_state_text()
        current_benchmark = ""
        tuning_context = getattr(window, "_last_ai_tuning_context", {})
        history_context = window._current_result_history_context(current_result)
        if (
            window._current_result_origin() == "controlled_optimization_rerun"
            and isinstance(tuning_context, dict)
        ):
            current_benchmark = str(tuning_context.get("benchmark_text") or "").strip()
        if (
            not current_benchmark
            and window._current_result_origin() == "controlled_optimization_rerun"
            and isinstance(history_context, dict)
        ):
            current_benchmark = str(history_context.get("benchmark_text") or "").strip()
            if not current_benchmark:
                benchmark_summary = history_context.get("benchmark_summary") if isinstance(history_context.get("benchmark_summary"), dict) else {}
                if isinstance(benchmark_summary, dict) and benchmark_summary:
                    current_benchmark = window._benchmark_summary_text(benchmark_summary)
        current_chain = ""
        if isinstance(tuning_context, dict) and tuning_context:
            current_chain = window._ai_tuning_chain_summary(
                {
                    "benchmark_summary": tuning_context.get("benchmark_summary"),
                    "history": tuning_context.get("history") if isinstance(tuning_context.get("history"), list) else [],
                }
            )
        if not current_detail and isinstance(current_result, dict):
            current_detail = window._history_metrics_tooltip(
                {
                    "parameters": current_result.get("parameters", {}) if isinstance(current_result.get("parameters"), dict) else {},
                    "results_summary": current_result.get("results_summary", {}) if isinstance(current_result.get("results_summary"), dict) else {},
                },
                limit=3,
            )
        current_review_summary = str(window._result_review_summary() or "").strip()
        current_detail = compose_current_work_memory_detail(
            summary_text=current_detail,
            context_text=current_context,
            origin_text=current_origin,
            confirmed_text=current_confirmed,
            benchmark_text=current_benchmark,
            chain_text=current_chain,
            review_summary=current_review_summary,
        )
        slices.append(build_work_memory_slice(
            tr("WORK_MEMORY_CURRENT"),
            current_detail or tr("WORK_MEMORY_CURRENT_DETAIL"),
            "results",
            window._jump_to_results,
        ))

    tech = str(getattr(window, "_current_technique", "") or "").strip().lower()
    if tech in {"saxs", "waxs"} and hasattr(window, "_current_submodule_id"):
        calibration_values = window._load_recent_calibration()
        scope_label = window._current_calibration_scope_label() or tr("WORKFLOW_SUBMODULE_NONE")
        calibration_detail = compose_calibration_work_memory_detail(
            scope_label=scope_label,
            has_recent_calibration=bool(calibration_values),
        )
        calibration_callback = window._on_apply_recent_calibration if calibration_values else window._on_save_recent_calibration
        slices.append(build_work_memory_slice(
            tr("WORK_MEMORY_CALIBRATION"),
            calibration_detail,
            "config",
            calibration_callback,
        ))

    recent_run = db_snapshot.recent_run
    if recent_run:
        get_analysis_run = getattr(db, "get_analysis_run", None)
        if (
            callable(get_analysis_run)
            and "parameters" not in recent_run
            and "results_summary" not in recent_run
        ):
            loaded_run = get_analysis_run(str(recent_run.get("id") or ""))
            if isinstance(loaded_run, dict):
                recent_run = loaded_run
        technique = window._history_technique_text(str(recent_run.get("technique") or ""))
        context = window._history_record_context_text(recent_run) or technique
        created = format_history_timestamp_value(recent_run.get("created_at"))
        output_dir = str(recent_run.get("output_dir") or "").strip()
        summary = window._history_metrics_tooltip(recent_run, limit=3)
        origin = window._history_result_origin_label(recent_run)
        confirmed = window._history_confirmation_label(recent_run)
        detail = compose_recent_history_work_memory_detail(
            context_text=context,
            created_text=created,
            origin_text=origin,
            confirmed_text=confirmed,
            summary_text=summary,
            output_dir=output_dir,
        )
        slices.append(build_work_memory_slice(
            tr("WORK_MEMORY_HISTORY"),
            detail or tr("WORK_MEMORY_EMPTY_DETAIL"),
            "history",
            window._jump_to_history,
        ))

    recent_sample = db_snapshot.recent_sample
    recent_batch = db_snapshot.recent_batch
    if recent_sample:
        detail = compose_sample_work_memory_detail(recent_sample, recent_batch)
        slices.append(build_work_memory_slice(
            tr("WORK_MEMORY_SAMPLE"),
            detail or tr("WORK_MEMORY_EMPTY_DETAIL"),
            "samples",
            window._jump_to_sample_library,
        ))

    if getattr(window, "_joint_report", None):
        joint_context = window._joint_ai_context()
        summary = str(joint_context.get("summary", "") or "").strip() if isinstance(joint_context, dict) else ""
        reminder = window._joint_ai_reminder_text(joint_context)
        compare_hint = window._joint_compare_hint_text(joint_context)
        detail = compose_joint_work_memory_detail(
            summary_text=summary,
            reminder_text=reminder,
            compare_hint_text=compare_hint,
        )
        slices.append(build_work_memory_slice(
            tr("WORK_MEMORY_JOINT"),
            detail,
            "joint.compare",
            window._jump_to_joint_hub,
        ))

    if window._last_export_bundle or window._output_dir:
        bundle = window._last_export_bundle or window._output_dir
        label = tr("WORK_MEMORY_EXPORT")
        detail = os.path.basename(bundle.rstrip("/\\")) or bundle
        slices.append(build_work_memory_slice(
            label,
            detail,
            "export",
            window._open_last_export_bundle,
        ))

    if not slices:
        slices.append(build_work_memory_slice(
            tr("WORK_MEMORY_EMPTY_TITLE"),
            tr("WORK_MEMORY_EMPTY_DETAIL"),
            "",
            None,
        ))

    return {
        "title": tr("WORK_MEMORY_TITLE"),
        "detail": compose_work_memory_meta_detail(
            sample_count=db_snapshot.sample_count,
            batch_count=db_snapshot.batch_count,
        ),
        "slices": slices[:6],
    }
