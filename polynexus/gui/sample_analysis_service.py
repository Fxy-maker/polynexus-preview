"""Helpers for launching sample-library batch analysis from the GUI."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QMessageBox

from .i18n import tr


def request_sample_batch_analysis(window, batch_id: str) -> None:
    db = window._ensure_sample_db()
    batch = db.get_batch(batch_id)
    if not batch:
        return

    batch_sample_id = str(batch.get("sample_id", "") or "").strip()
    sample = db.get_sample(batch_sample_id) if batch_sample_id else None
    window._set_sample_batch_context(
        sample_id=batch_sample_id,
        batch_id=batch_id,
        sample_name=(sample or {}).get("polymer_name", ""),
        batch_label=batch.get("label", ""),
    )

    files = db.get_data_files(batch_id)
    if not files:
        QMessageBox.warning(
            window,
            tr("SAMPLE_BATCH_ANALYZE"),
            tr("SAMPLE_BATCH_ANALYZE_NO_FILE"),
        )
        return

    runs = db.get_analysis_runs(batch_id)
    latest_run = runs[0] if runs else {}
    latest_technique = str(latest_run.get("technique", "") or "").strip().lower()
    latest_submodule = str(latest_run.get("submodule", "") or "").strip()

    selected_file = None
    if latest_technique:
        for file_row in files:
            if str(file_row.get("technique", "") or "").strip().lower() == latest_technique:
                selected_file = file_row
                break
    if selected_file is None:
        selected_file = files[0]

    file_path = str(selected_file.get("file_path", "") or "").strip()
    if not file_path or not Path(file_path).exists():
        QMessageBox.warning(
            window,
            tr("SAMPLE_BATCH_ANALYZE"),
            tr("SAMPLE_BATCH_ANALYZE_FILE_MISSING", file_path or "-"),
        )
        return

    technique = (
        latest_technique
        or str(selected_file.get("technique", "") or "").strip().lower()
    )
    if not technique:
        return

    window._current_submodule_id = ""
    window._on_technique_selected(technique)
    btn = window._nav_buttons.get(technique)
    if btn:
        btn.setChecked(True)

    if latest_submodule and latest_submodule in window._nav_buttons:
        sub_btn = window._nav_buttons.get(latest_submodule)
        if sub_btn:
            sub_btn.setChecked(True)
        window._on_submodule_selected(technique, latest_submodule)
    else:
        window._current_submodule_id = ""
        window._update_workspace_context()

    window._set_input_path(file_path, clear_sample_context=False)
    window._save_last_dir(file_path)

    output_dir = str(latest_run.get("output_dir", "") or "").strip()
    if output_dir:
        window._output_dir = output_dir
        if hasattr(window, "_output_input"):
            window._output_input.setText(output_dir)

    if hasattr(window, "_tabs"):
        window._tabs.setCurrentIndex(0)

    window._update_workspace_context()
    window.log(tr("LOG_SAMPLE_BATCH_ANALYSIS_READY", batch.get("label", "") or batch_id))
