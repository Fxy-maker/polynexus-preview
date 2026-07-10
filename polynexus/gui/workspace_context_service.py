"""Pure helpers for compact workspace / work-memory summaries."""

from __future__ import annotations

from typing import Callable, Iterable


def work_memory_summary_text(slices, *, extra_lines: Iterable[str] = ()) -> str:
    items = slices if isinstance(slices, list) else []
    parts = []
    for item in items[:3]:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        detail = str(item.get("detail") or "").strip()
        if label or detail:
            parts.append(f"{label}: {detail}" if label and detail else (label or detail))
    for line in extra_lines:
        text = str(line or "").strip()
        if text and text not in parts:
            parts.append(text)
    return " | ".join(parts)


def workspace_context_summary_text(
    current_result,
    *,
    confirm_state_text: str,
    origin_label: str,
    current_note: str,
    joint_report,
    joint_context,
    joint_label: str,
    joint_count_text_fn: Callable[[int, int], str],
    work_memory,
    empty_text: str,
    current_label: str = "Current result",
) -> str:
    summary_parts = []

    current = current_result if isinstance(current_result, dict) else {}
    if current:
        current_bits = []
        current_summary = current.get("results_summary") if isinstance(current.get("results_summary"), dict) else {}
        project_label = str(current_summary.get("project_label") or "").strip()
        if project_label:
            current_bits.append(project_label)
        confirm_text = str(confirm_state_text or "").strip()
        if confirm_text:
            current_bits.append(confirm_text)
        confirmed_flag = bool(current.get("confirmed") or current_summary.get("confirmed"))
        ai_tuned_flag = bool(current.get("ai_tuned") or current_summary.get("ai_tuned"))
        current_bits.append(f"confirmed={confirmed_flag}")
        current_bits.append(f"ai_tuned={ai_tuned_flag}")
        origin_text = str(origin_label or "").strip()
        if origin_text:
            current_bits.append(origin_text)
        note_text = str(current_note or "").strip()
        if note_text:
            current_bits.append(note_text)
        if current_bits:
            summary_parts.append(f"{str(current_label or 'Current result')}: " + " | ".join(current_bits))

    report = joint_report if isinstance(joint_report, dict) else None
    joint = joint_context if isinstance(joint_context, dict) else {}
    joint_label_text = str(joint_label or "").strip()
    if isinstance(report, dict):
        joint_summary = str(report.get("summary") or "").strip()
        if not joint_summary:
            joint_summary = str(joint.get("summary") or "").strip()
        if joint_summary:
            summary_parts.append(f"{joint_label_text}: {joint_summary}" if joint_label_text else joint_summary)
        rows = report.get("rows") if isinstance(report.get("rows"), list) else []
        validations = report.get("validations") if isinstance(report.get("validations"), list) else []
        if rows or validations:
            count_text = str(joint_count_text_fn(len(rows), len(validations)) or "").strip()
            if count_text:
                summary_parts.append(count_text)
    elif joint:
        joint_summary = str(joint.get("summary") or "").strip()
        if joint_summary:
            summary_parts.append(f"{joint_label_text}: {joint_summary}" if joint_label_text else joint_summary)

    memory = work_memory if isinstance(work_memory, dict) else {}
    slices = memory.get("slices") if isinstance(memory.get("slices"), list) else []
    for item in slices[:3]:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        detail = str(item.get("detail") or "").strip()
        if label or detail:
            summary_parts.append(f"{label}: {detail}" if label and detail else (label or detail))

    if not summary_parts:
        return str(empty_text or "")
    return "\n".join(summary_parts[:5])
