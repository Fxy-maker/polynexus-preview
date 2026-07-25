"""Pure helpers for GUI export-context metadata."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from .i18n import tr


def create_export_bundle_dirs(save_root) -> dict[str, Path]:
    root = Path(save_root)
    dirs = {
        "figures": root / "figures",
        "data": root / "data",
        "report": root / "report",
        "metadata": root / "metadata",
    }
    for directory in dirs.values():
        directory.mkdir(parents=True, exist_ok=True)
    return dirs


def task_type_label(input_mode: str) -> str:
    key = str(input_mode or "").strip().lower()
    mapping = {
        "single": "Single-file analysis",
        "batch": "Batch analysis",
        "directory": "Directory analysis",
        "multi_sample": "Multi-sample analysis",
        "joint": "Joint analysis",
    }
    return mapping.get(key, "Analysis run")


def export_primary_report(report_path: str) -> str:
    if not report_path:
        return ""
    try:
        report_file = Path(report_path)
        report_parent = report_file.parent.name or "report"
        return Path(report_parent, report_file.name).as_posix()
    except ValueError:
        return str(report_path)


def export_relative_report_path(report_path: str, save_root: str) -> str:
    if not report_path:
        return ""
    try:
        return str(Path(report_path).resolve().relative_to(Path(save_root).resolve()))
    except ValueError:
        try:
            import os

            return os.path.relpath(report_path, save_root)
        except ValueError:
            return str(report_path)


def export_review_priority(result_origin: str) -> list[str]:
    if str(result_origin or "").strip() == "controlled_optimization_rerun":
        return [
            "report/",
            "metadata/export_manifest.json",
            "data/",
        ]
    return [
        "report/",
        "data/",
        "metadata/export_manifest.json",
    ]


def export_recommended_reading_order(primary_report: str) -> list[str]:
    return [
        primary_report or "report/ (no HTML report generated)",
        "metadata/export_manifest.json",
        "data/",
    ]


def compose_joint_export_detail(*, joint_summary: str = "", joint_reminder: str = "", joint_compare_hint: str = "") -> str:
    return " | ".join(
        part
        for part in [
            str(joint_summary or "").strip(),
            str(joint_reminder or "").strip(),
            str(joint_compare_hint or "").strip(),
        ]
        if part
    )


def copy_export_bundle_sections(source_root, bundle_dirs: dict[str, Path]) -> list[str]:
    copied_sections: list[str] = []
    out_src = Path(source_root) if source_root else None
    if out_src is None or not out_src.exists() or not out_src.is_dir():
        return copied_sections

    for sub in ["figures", "data", "report", "metadata"]:
        src = out_src / sub
        dst = bundle_dirs.get(sub)
        if dst is None:
            continue
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
            copied_sections.append(sub)

    runs_src = out_src / "runs"
    metadata_dst = bundle_dirs.get("metadata")
    if runs_src.is_dir() and metadata_dst is not None:
        shutil.copytree(runs_src, Path(metadata_dst) / "runs", dirs_exist_ok=True)
    return copied_sections


def build_export_context_payload(window, *, report_path: str = "", ir_summary_fn=None) -> dict:
    current_technique = str(getattr(window, "_current_technique", "") or "").strip()
    current_submodule = str(getattr(window, "_current_submodule_id", "") or "").strip()
    input_mode = str(getattr(window, "_current_input_mode", "") or "").strip()
    current_result = window._current_results_record()
    tuning_context = window._current_result_tuning_context(current_result)
    if not isinstance(tuning_context, dict):
        tuning_context = {}
    joint_context = window._joint_ai_context()
    if not isinstance(joint_context, dict):
        joint_context = {}
    history_context = window._history_context_snapshot(
        tuning_context=tuning_context,
        joint_context=joint_context,
    )
    if not isinstance(history_context, dict):
        history_context = {}

    primary_report = export_primary_report(report_path)
    result_origin = window._current_result_origin()
    recommended = export_recommended_reading_order(primary_report)
    analysis_evidence = window._current_analysis_evidence()

    ir_export_semantics = ""
    if current_technique == "ir" and callable(ir_summary_fn):
        ir_export_semantics = _join_text_parts(ir_summary_fn(analysis_evidence))

    review_summary = str(window._result_review_summary() or "").strip()
    if ir_export_semantics:
        review_summary = " | ".join(
            part for part in [ir_export_semantics, review_summary] if str(part).strip()
        )

    validation_summary = str(window._history_validation_summary(current_result) or "").strip()
    benchmark_text = str(history_context.get("benchmark_text") or "").strip()
    validation_chain = " | ".join(
        part
        for part in [
            benchmark_text,
            str(window._ai_tuning_chain_snapshot(tuning_context) or "").strip(),
        ]
        if part
    )

    return {
        "task_type": task_type_label(input_mode),
        "technique_id": current_technique,
        "technique_label": window._history_technique_text(current_technique),
        "submodule_id": current_submodule,
        "submodule_label": window._history_submodule_text(current_submodule) or current_submodule,
        "input_mode": input_mode,
        "source_data_path": str(getattr(window, "_current_filepath", "") or ""),
        "result_origin": result_origin,
        "result_origin_label": window._result_origin_label(result_origin),
        "used_controlled_optimization": result_origin == "controlled_optimization_rerun",
        "confirmed_result": bool(getattr(window, "_current_result_confirmed_flag", False)),
        "decision_owner": "user",
        "decision_owner_label": tr("EXPORT_DECISION_OWNER_USER"),
        "review_priority": export_review_priority(result_origin),
        "recommended_reading_order": recommended,
        "comparison_summary": window._result_comparison_summary(),
        "review_summary": review_summary,
        "validation_summary": validation_summary,
        "validation_chain": validation_chain,
        "benchmark_text": benchmark_text,
        "joint_summary": str(history_context.get("joint_summary") or "").strip(),
        "history_context": history_context,
        "work_memory_summary": str(window._work_memory_summary() or "").strip(),
        "responsibility_boundary": str(window._responsibility_boundary_summary() or "").strip(),
        "paper_figure_status": ir_export_semantics,
    }


def export_readme_text(
    *,
    project_name: str,
    generated_at: str,
    techniques: str,
    source_data_path: str,
    primary_report: str,
    export_context: dict,
    joint_detail: str,
    confirmed_review_label: str,
) -> str:
    context = export_context if isinstance(export_context, dict) else {}
    project = str(project_name or "").strip() or "Unnamed"
    technique_text = str(techniques or "").strip() or "None"
    source_data = str(source_data_path or "").strip() or "-"
    review_summary = str(context.get("review_summary") or "-").strip()
    if context.get("confirmed_result") and review_summary not in {"", "-"}:
        confirmed_text = str(confirmed_review_label or "").strip()
        if confirmed_text and not review_summary.startswith(confirmed_text):
            review_summary = f"{confirmed_text} | {review_summary}"

    validation_chain = str(context.get("validation_chain") or "").strip()
    benchmark_text = str(context.get("benchmark_text") or "").strip()
    review_priority = _list_or_default(
        context.get("review_priority"),
        ["report/", "metadata/export_manifest.json", "data/"],
    )
    reading_order = _list_or_default(
        context.get("recommended_reading_order"),
        ["report/", "metadata/export_manifest.json", "data/"],
    )

    lines = [
        "PolyNexus Export Package",
        "",
        f"Project: {project}",
        f"Generated: {generated_at}",
        f"Techniques: {technique_text}",
        f"Source data: {source_data}",
        f"Task type: {context.get('task_type') or '-'}",
        f"Technique / module: {context.get('technique_label') or '-'} / {context.get('submodule_label') or '-'}",
        f"Input mode: {context.get('input_mode') or '-'}",
        f"Confirmed result: {'Yes' if context.get('confirmed_result') else 'No'}",
        f"Result origin: {context.get('result_origin_label') or '-'}",
        f"Decision owner: {context.get('decision_owner_label') or 'User'}",
        f"Controlled optimization used: {'Yes' if context.get('used_controlled_optimization') else 'No'}",
        f"Comparison summary: {context.get('comparison_summary') or '-'}",
        f"Review summary: {review_summary}",
        f"Validation chain: {validation_chain or benchmark_text or '-'}",
        f"Joint summary: {joint_detail or '-'}",
        f"Responsibility boundary: {context.get('responsibility_boundary') or '-'}",
        f"Work memory: {context.get('work_memory_summary') or '-'}",
        "",
        "Main folders:",
        "- report/    HTML and markdown reports",
        "- figures/   Exported plots and images",
        "- data/      Parameter tables and derived CSV files",
        "- metadata/  Export manifest and package notes",
        "",
        "Review priority:",
        f"1. {review_priority[0]}",
        f"2. {review_priority[1] if len(review_priority) > 1 else 'metadata/export_manifest.json'}",
        f"3. {review_priority[2] if len(review_priority) > 2 else 'data/'}",
        "",
        "Recommended reading order:",
        f"1. {reading_order[0]}",
        f"2. {reading_order[1] if len(reading_order) > 1 else 'metadata/export_manifest.json'}",
        f"3. {reading_order[2] if len(reading_order) > 2 else 'data/'}",
        "",
        f"Open first: {primary_report or 'report/ (no HTML report generated)'}",
    ]
    return "\n".join(lines)


def export_manifest_payload(
    *,
    project_name: str,
    exported_at: str,
    bundle_root: str,
    source_output_dir: str,
    source_data_path: str,
    current_technique: str,
    current_submodule: str,
    input_mode: str,
    included_techniques,
    copied_sections,
    primary_report: str,
    task_context: dict,
) -> dict:
    return {
        "project_name": str(project_name or "").strip(),
        "exported_at": str(exported_at or "").strip(),
        "bundle_root": str(bundle_root or ""),
        "source_output_dir": str(source_output_dir or ""),
        "source_data_path": str(source_data_path or ""),
        "current_technique": str(current_technique or ""),
        "current_submodule": str(current_submodule or ""),
        "input_mode": str(input_mode or ""),
        "included_techniques": sorted(str(key) for key in (included_techniques or [])),
        "copied_sections": [str(section) for section in (copied_sections or [])],
        "directories": {
            "figures": "figures",
            "data": "data",
            "report": "report",
            "metadata": "metadata",
        },
        "primary_report": str(primary_report or ""),
        "task_context": task_context if isinstance(task_context, dict) else {},
    }


def write_export_manifest(
    save_root,
    *,
    project_name: str,
    exported_at: str,
    bundle_root: str,
    source_output_dir: str,
    source_data_path: str,
    current_technique: str,
    current_submodule: str,
    input_mode: str,
    included_techniques,
    copied_sections,
    primary_report: str,
    task_context: dict,
) -> Path:
    root = Path(save_root)
    metadata_dir = root / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)

    payload = export_manifest_payload(
        project_name=project_name,
        exported_at=exported_at,
        bundle_root=bundle_root,
        source_output_dir=source_output_dir,
        source_data_path=source_data_path,
        current_technique=current_technique,
        current_submodule=current_submodule,
        input_mode=input_mode,
        included_techniques=included_techniques,
        copied_sections=copied_sections,
        primary_report=primary_report,
        task_context=task_context,
    )

    manifest_path = metadata_dir / "export_manifest.json"
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path


def write_export_readme(
    save_root,
    *,
    project_name: str,
    generated_at: str,
    techniques: str,
    source_data_path: str,
    primary_report: str,
    export_context: dict,
    joint_detail: str,
    confirmed_review_label: str,
) -> Path:
    root = Path(save_root)
    root.mkdir(parents=True, exist_ok=True)

    readme_path = root / "README.txt"
    readme_path.write_text(
        export_readme_text(
            project_name=project_name,
            generated_at=generated_at,
            techniques=techniques,
            source_data_path=source_data_path,
            primary_report=primary_report,
            export_context=export_context,
            joint_detail=joint_detail,
            confirmed_review_label=confirmed_review_label,
        ),
        encoding="utf-8",
    )
    return readme_path


def _join_text_parts(parts) -> str:
    if parts is None:
        return ""
    if isinstance(parts, str):
        values = [parts]
    elif isinstance(parts, (list, tuple)):
        values = list(parts)
    else:
        values = [parts]
    return " | ".join(str(part).strip() for part in values if str(part).strip())


def _list_or_default(value, default: list[str]) -> list[str]:
    if not isinstance(value, list) or not value:
        return list(default)
    return [str(item) for item in value]
