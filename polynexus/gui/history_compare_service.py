"""Pure helpers for presenting history-comparison dialog content."""

from __future__ import annotations

from typing import Any, Callable

from PySide6.QtGui import QColor

from .analysis_history_service import history_compare_state_translation_key
from .i18n import tr
from .styles import C_TEXT_MUTED


def history_compare_summary_text(
    current_record: dict[str, Any],
    baseline_record: dict[str, Any],
    *,
    timestamp_text_fn: Callable[[Any], str],
    context_text_fn: Callable[[dict[str, Any]], str],
) -> str:
    current_time = timestamp_text_fn(current_record.get("created_at"))
    baseline_time = timestamp_text_fn(baseline_record.get("created_at"))
    current_label = context_text_fn(current_record)
    baseline_label = context_text_fn(baseline_record)
    return tr(
        "HISTORY_COMPARE_SUMMARY",
        current_time,
        current_label,
        baseline_time,
        baseline_label,
    )


def history_compare_state_label(self, state: str) -> str:
    del self
    return tr(history_compare_state_translation_key(state))


def history_compare_counts_text(self, counts: dict[str, int] | None) -> str:
    del self
    resolved_counts = counts if isinstance(counts, dict) else {}
    return tr(
        "HISTORY_COMPARE_COUNTS",
        resolved_counts.get("changed", 0),
        resolved_counts.get("new", 0),
        resolved_counts.get("removed", 0),
        resolved_counts.get("same", 0),
    )


def history_compare_state_color(self, state: str) -> QColor:
    del self
    colors = {
        "changed": QColor("#2563eb"),
        "new": QColor("#16a34a"),
        "removed": QColor("#dc2626"),
        "same": QColor(C_TEXT_MUTED),
    }
    return colors.get(state, QColor(C_TEXT_MUTED))
