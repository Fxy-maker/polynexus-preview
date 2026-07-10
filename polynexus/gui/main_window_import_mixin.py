from __future__ import annotations

import os

from PySide6.QtWidgets import QDialog, QFileDialog

from .import_suggestions import ImportSuggestion, suggest_import
from .i18n import tr
from .theme import TECHNIQUE_LABELS
from .window_text_helpers import data_file_dialog_filter as _data_file_dialog_filter
from .window_text_helpers import import_mode_text as _import_mode_text


class MainWindowImportMixin:
    @staticmethod
    def _import_suggestion_dialog_class():
        from . import main_window as main_window_module

        return main_window_module.ImportSuggestionDialog

    @staticmethod
    def _format_import_suggestion_reason(reason: str) -> str:
        from . import main_window as main_window_module

        return main_window_module._format_import_suggestion_reason(reason)

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("FILE_DIALOG_DATA"),
            self._get_last_dir(),
            _data_file_dialog_filter(),
        )
        if path:
            self._handle_import_candidate(path, is_dir=False, source="browse")

    def _browse_folder(self):
        path = QFileDialog.getExistingDirectory(
            self,
            tr("FILE_DIALOG_FOLDER"),
            self._get_last_dir(),
        )
        if path:
            self._handle_import_candidate(path, is_dir=True, source="browse")

    def _set_input_path(self, path, is_dir=False, input_mode=None, *, clear_sample_context=True):
        self._current_filepath = path
        mode = str(input_mode or "").strip().lower()
        self._current_input_mode = mode or ("directory" if is_dir else "")

        if clear_sample_context:
            self._clear_sample_batch_context()

        self._path_input.setText(path)

        name = os.path.basename(path.rstrip("/\\"))

        self._project_label.setText(name if name else path)

        self._add_recent(path)

        self._update_workspace_context()

    def _apply_import_selection(
        self,
        path,
        *,
        is_dir=False,
        input_mode="",
        technique="",
        submodule="",
        update_last_dir=True,
    ):
        if update_last_dir:
            self._save_last_dir(path)

        self._set_input_path(path, is_dir=is_dir, input_mode=input_mode, clear_sample_context=True)

        technique_key = str(technique or "").strip().lower()
        submodule_key = str(submodule or "").strip()

        if not technique_key and submodule_key:
            technique_key = submodule_key.split(".", 1)[0].lower()

        self._current_submodule_id = ""

        if technique_key:
            self._on_technique_selected(technique_key)
            btn = self._nav_buttons.get(technique_key)
            if btn:
                btn.setChecked(True)

        if submodule_key:
            sub_btn = self._nav_buttons.get(submodule_key)
            if sub_btn:
                sub_btn.setChecked(True)
            self._on_submodule_selected(technique_key or self._current_technique, submodule_key)
        else:
            self._update_workspace_context()

    def _import_target_summary(self, path, *, input_mode=""):
        mode = str(input_mode or "").strip().lower()
        parts = []
        mode_text = _import_mode_text(mode)
        if mode_text:
            parts.append(mode_text)
        name = os.path.basename(str(path or "").rstrip("/\\"))
        parts.append(name or str(path or ""))
        return " | ".join(part for part in parts if part)

    def _apply_import_suggestion(self, suggestion: ImportSuggestion):
        self._apply_import_selection(
            suggestion.path,
            is_dir=suggestion.is_dir,
            input_mode=suggestion.input_mode,
            technique=suggestion.technique,
            submodule=suggestion.submodule,
        )

        summary = []
        if suggestion.technique:
            summary.append(TECHNIQUE_LABELS.get(suggestion.technique, suggestion.technique.upper()))
        if suggestion.submodule:
            summary.append(self._history_submodule_text(suggestion.submodule) or suggestion.submodule)
        if suggestion.input_mode:
            summary.append(_import_mode_text(suggestion.input_mode))
        reason = self._format_import_suggestion_reason(suggestion.reason)
        if reason and reason != tr("IMPORT_SUGGESTION_AUTO"):
            summary.append(reason)
        message_key = "LOG_IMPORT_SETUP_APPLIED" if suggestion.reason == "manual" else "LOG_IMPORT_SUGGESTION_APPLIED"
        self.log(tr(message_key, " | ".join(summary) or suggestion.path))

    def _import_submodule_options(self):
        from ..core.submodule_registry import get_submodule_registry

        options = {}
        for technique, specs in get_submodule_registry().items():
            technique_key = str(technique or "").strip().lower()
            if not technique_key or technique_key == "joint":
                continue
            for spec in specs:
                submodule_id = str(getattr(spec, "id", "") or "").strip()
                if not submodule_id:
                    continue
                label = self._history_submodule_text(submodule_id) or str(getattr(spec, "label", "") or submodule_id)
                input_mode = str(getattr(spec, "input_mode", "") or "").strip()
                options.setdefault(technique_key, []).append((submodule_id, label, input_mode))
        return options

    def _confirm_import_suggestion(self, suggestion: ImportSuggestion):
        dialog = self._import_suggestion_dialog_class()(
            suggestion.path,
            suggestion.is_dir,
            suggestion,
            self._import_submodule_options(),
            parent=self,
        )
        if dialog.exec() != QDialog.Accepted:
            return None

        technique = dialog.selected_technique()
        submodule = dialog.selected_submodule()
        mode = dialog.selected_mode()
        return ImportSuggestion(
            path=suggestion.path,
            is_dir=suggestion.is_dir,
            technique=technique,
            submodule=submodule,
            input_mode=mode,
            reason=suggestion.reason,
        )

    def _choose_import_manually(self, path, *, is_dir=False):
        suggestion = ImportSuggestion(
            path=path,
            is_dir=is_dir,
            technique="",
            submodule="",
            input_mode="directory" if is_dir else "single",
            reason="manual",
        )
        return self._confirm_import_suggestion(suggestion)

    def _handle_import_candidate(self, path, *, is_dir=False, source="browse"):
        suggestion = suggest_import(path, is_dir=is_dir)
        if suggestion and suggestion.is_meaningful and source in {"browse", "drop"}:
            confirmed = self._confirm_import_suggestion(suggestion)
            if confirmed is not None:
                self._apply_import_suggestion(confirmed)
                return
        elif source in {"browse", "drop"}:
            manual = self._choose_import_manually(path, is_dir=is_dir)
            if manual is not None:
                self._apply_import_suggestion(manual)
                return

        fallback_mode = "directory" if is_dir else "single"
        self._apply_import_selection(
            path,
            is_dir=is_dir,
            input_mode=fallback_mode,
        )
        if source in {"browse", "drop"}:
            self.log(tr("LOG_IMPORT_BASIC_APPLIED", self._import_target_summary(path, input_mode=fallback_mode)))
