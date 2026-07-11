"""Shared GUI text helpers used by the main window and review panels."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from .i18n import get_language, tr


def lang_text(mapping: Mapping[str, str] | None, fallback: str = "") -> str:
    lang = get_language()
    mapping = mapping or {}
    return mapping.get(lang) or mapping.get("en") or fallback


def is_default_project_label(text: str) -> bool:
    value = str(text or "").strip()
    if not value:
        return True
    return value in {"No project", "无项目"}


def data_file_dialog_filter() -> str:
    patterns = "*.edf *.csv *.txt *.dat *.xlsx *.xls *.001 *.raw *.spa *.jdf *.bin fid"
    return f"{tr('FILE_FILTER_SUPPORTED')} ({patterns});;{tr('FILE_FILTER_ALL')} (*)"


def read_warning_count(log_path: str | Path = "polynexus.log", *, warning_fn: Callable[[str], None] | None = None) -> int:
    path = Path(log_path)
    if not path.exists():
        return 0
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as fh:
            return sum(1 for line in fh if "[WARNING]" in line)
    except Exception:
        if warning_fn is not None:
            warning_fn("Failed to read warning count from log file.")
        return 0


def import_mode_text(mode: str) -> str:
    value = str(mode or "").strip().lower()
    mapping = {
        "single": tr("IMPORT_MODE_SINGLE"),
        "sequence": tr("IMPORT_MODE_SEQUENCE"),
        "directory": tr("IMPORT_MODE_DIRECTORY"),
    }
    return mapping.get(value, value or "-")


def ir_conclusion_state_display(value: Any) -> str:
    if value is True:
        return tr("IR_CONCLUSION_READY")
    if value is False:
        return tr("IR_CONCLUSION_PENDING")
    return tr("AI_TUNING_EMPTY_VALUE")


def format_import_suggestion_reason(
    reason: str,
    *,
    registry_lookup: Callable[[str], Any] | None = None,
) -> str:
    value = str(reason or "").strip()
    if not value:
        return tr("IMPORT_SUGGESTION_AUTO")
    if value.startswith("extension:"):
        suffix = value.split(":", 1)[1].strip() or "-"
        return tr("IMPORT_SUGGESTION_REASON_EXTENSION", suffix)
    if value.startswith("filename:"):
        name = value.split(":", 1)[1].strip() or "-"
        return tr("IMPORT_SUGGESTION_REASON_FILENAME", name)
    if value.startswith("registry:"):
        submodule_id = value.split(":", 1)[1].strip()
        label = registry_lookup(submodule_id) if registry_lookup is not None else None
        if isinstance(label, Mapping):
            label_text = lang_text(label, submodule_id or "-")
        else:
            label_text = str(label or submodule_id or "-")
        return tr("IMPORT_SUGGESTION_REASON_REGISTRY", label_text)
    if value == "directory:nmr":
        return tr("IMPORT_SUGGESTION_REASON_DIRECTORY_NMR")
    if value == "directory:ir_spectra":
        return tr("IMPORT_SUGGESTION_REASON_DIRECTORY_IR")
    if value.startswith("directory:."):
        suffix = value.split(":", 1)[1].strip() or "-"
        return tr("IMPORT_SUGGESTION_REASON_DIRECTORY_EXTENSION", suffix)
    if value == "pattern:saxs_strain":
        return tr("IMPORT_SUGGESTION_REASON_PATTERN_SAXS_STRAIN")
    if value == "manual":
        return tr("IMPORT_SUGGESTION_REASON_MANUAL")
    return value
