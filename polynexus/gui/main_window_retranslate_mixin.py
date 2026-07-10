from __future__ import annotations

import os

from PySide6.QtWidgets import QWidget

from .i18n import get_language, set_language, tr
from .theme import ThemeEngine
from .window_text_helpers import is_default_project_label as _is_default_project_label
from ..core.engine import logger


class MainWindowRetranslateMixin:
    def _retranslate_ui(self):

        """Refresh all UI text after language change.

        Each widget access is wrapped in a try/except to survive
        C++ object deletion (e.g. tabs being removed by Qt).
        """

        def _safe_set(widget, text):

            try:

                widget.setText(text)

            except Exception:

                logger.warning("Failed to update widget text during retranslate.", exc_info=True)

        def _safe_set_title(w, title):

            try:

                w.setWindowTitle(title)

            except Exception:

                logger.warning("Failed to update window title during retranslate.", exc_info=True)

        _safe_set_title(self, tr("WINDOW_TITLE"))

        # Menu bar
        try:

            for action, key in [
                (self._act_open, "ACTION_OPEN"),
                (self._act_export, "ACTION_EXPORT"),
                (self._act_settings, "ACTION_SETTINGS"),
                (self._act_quit, "ACTION_QUIT"),
                (self._act_toggle_sidebar, "ACTION_TOGGLE_SIDEBAR"),
                (self._act_toggle_theme, "ACTION_TOGGLE_THEME"),
                (self._act_toggle_lang, "ACTION_TOGGLE_LANG"),
                (self._act_about, "ACTION_ABOUT"),
            ]:

                _safe_set(action, tr(key))

            self._menu_file.setTitle(tr("MENU_FILE"))
            self._menu_edit.setTitle(tr("MENU_EDIT"))
            self._menu_view.setTitle(tr("MENU_VIEW"))
            self._menu_help.setTitle(tr("MENU_HELP"))

        except Exception:
            logger.warning("Failed to update menu bar labels during retranslate.", exc_info=True)

        try:

            self._statusbar.showMessage(tr("STATUSBAR_READY"))

        except Exception:
            logger.warning("Failed to update ready status message during retranslate.", exc_info=True)

        # Topbar buttons (these always exist)
        for w, key in [
            (self._btn_run, "BTN_RUN"),
            (self._btn_replot, "BTN_REPLOT"),
            (self._btn_export, "BTN_EXPORT"),
        ]:

            _safe_set(w, tr(key))

        try:

            self._btn_replot.setToolTip(tr("REPLOT_TOOLTIP"))

        except Exception:
            logger.warning("Failed to update top-level action labels during retranslate.", exc_info=True)

        try:

            self._btn_lang.setText("\u4e2d" if get_language() != "zh" else "EN")
            self._btn_lang.setToolTip(tr("LANG_TOGGLE_TOOLTIP"))

        except Exception:
            logger.warning("Failed to retranslate optional child widgets.", exc_info=True)

        try:

            self._btn_theme.setText("\u263e" if ThemeEngine.instance().is_dark else "\u2600")

            self._btn_theme.setToolTip(tr("THEME_TOGGLE_TOOLTIP"))
            self._btn_ai_tune.setText(tr("AI_TUNING_BUTTON"))
            self._btn_results_export.setText(tr("RESULTS_EXPORT_TABLE"))
            self._btn_results_copy.setText(tr("RESULTS_COPY_TABLE"))
            self._btn_results_default_order.setText(tr("RESULTS_DEFAULT_ORDER"))
            self._btn_view_current_figure.setText(tr("PLOTS_BTN_VIEW_CURRENT"))
            self._btn_legacy_recovery.setText(tr("PLOTS_BTN_RECOVER_LEGACY"))
            self._drop_label.setText(tr("DROP_HINT"))
            self._history_tech_label.setText(tr("HISTORY_TECHNIQUE"))
            self._history_refresh_btn.setText(tr("HISTORY_REFRESH"))
            self._history_export_btn.setText(tr("HISTORY_EXPORT"))
            self._history_copy_summary_btn.setText(tr("HISTORY_COPY_SUMMARY"))
            self._history_restore_btn.setText(tr("HISTORY_RESTORE"))
            self._history_rerun_btn.setText(tr("HISTORY_RERUN"))
            self._history_confirm_btn.setText(tr("RESULTS_CONFIRM_MARK"))
            self._history_compare_btn.setText(tr("HISTORY_COMPARE"))

        except Exception:
            logger.warning("Failed to update default workspace labels during retranslate.", exc_info=True)

        try:

            if hasattr(self, "_joint_hub"):

                self._joint_hub.retranslate()

            if hasattr(self, "_sample_browser"):

                self._sample_browser.retranslate()

            if hasattr(self, "_figure_preview"):

                self._figure_preview.retranslate()

            if hasattr(self, "_figure_viewer") and self._figure_viewer is not None:

                self._figure_viewer.retranslate()

            if hasattr(self, "_chart_editor") and self._chart_editor is not None:

                self._chart_editor.retranslate()

            if hasattr(self, "action_convergence_viewer"):
                self.action_convergence_viewer.setText(tr("CONVERGENCE_DASHBOARD"))

            if hasattr(self, "_btn_convergence_viewer"):
                self._btn_convergence_viewer.setText(tr("CONVERGENCE_DASHBOARD"))

            if self._current_technique == "joint":

                self._btn_run.setText(tr("BTN_GENERATE_OVERVIEW"))

        except Exception:
            logger.warning("Failed to refresh translated group titles and history filter.", exc_info=True)

        try:

            current_label = self._project_label.text().strip() if hasattr(self, "_project_label") else ""
            project_label = tr("NO_PROJECT")
            if self._current_filepath:
                if current_label and not _is_default_project_label(current_label):
                    project_label = current_label
                else:
                    project_label = os.path.basename(self._current_filepath.rstrip("/\\")) or self._current_filepath
            self._project_label.setText(project_label)
            self._workspace_title.setText(tr("WORKSPACE_TITLE_DEFAULT"))
            self._workspace_subtitle.setText(tr("WORKSPACE_SUBTITLE_DEFAULT"))
            self._workflow_metric_data.setText(tr("WORKFLOW_NO_DATA"))
            self._workflow_metric_state.setText(tr("WORKFLOW_READY"))
            self._update_workflow_task_card()

        except Exception:
            logger.warning("Failed to update translated tab labels.", exc_info=True)

        try:

            self._log_group.setTitle(tr("GROUP_LOG"))

            self._data_source_group.setTitle(tr("GROUP_DATA_SOURCE"))

            self._output_group.setTitle(tr("GROUP_OUTPUT"))

            if hasattr(self, "_joint_diagnostics_group"):

                self._joint_diagnostics_group.setTitle(tr("GROUP_JOINT_DIAGNOSTICS"))

            self._refresh_sidebar_texts()
            if hasattr(self, "_history_filter_combo"):
                self._refresh_history()

            self._update_workspace_context()

        except Exception:
            logger.warning("Failed to refresh translated group titles and history filter.", exc_info=True)

        # Tabs
        try:

            for i, key in enumerate(["TAB_DATA", "TAB_CONFIG", "TAB_RESULTS", "TAB_PLOTS", "TAB_HISTORY"]):

                if i < self._tabs.count():

                    self._tabs.setTabText(i, tr(key))

        except Exception:
            logger.warning("Failed to update translated tab labels.", exc_info=True)

        # Optional child widgets
        for attr, key in [
            ("_sidebar_tech_label", "SIDEBAR_TECHNIQUES"),
            ("_sidebar_recent_label", "SIDEBAR_RECENT"),
            ("_data_file_label", "DATA_FILE_LABEL"),
            ("_data_btn_browse", "DATA_BTN_BROWSE"),
            ("_data_output_label", "DATA_OUTPUT_DIR"),
            ("_config_preset_label", "CONFIG_PRESET_LABEL"),
            ("_config_placeholder", "CONFIG_PLACEHOLDER"),
            ("_plots_label", "PLOTS_EMPTY"),
        ]:

            w = getattr(self, attr, None)

            if w is not None:

                _safe_set(w, tr(key))

        for attr, key in [
            ("_btn_config_preset_save", "CONFIG_PRESET_SAVE"),
            ("_btn_config_preset_load", "CONFIG_PRESET_LOAD"),
            ("_btn_config_preset_delete", "CONFIG_PRESET_DELETE"),
            ("_btn_config_recent_calibration_save", "CONFIG_RECENT_CALIBRATION_SAVE"),
            ("_btn_config_recent_calibration", "CONFIG_RECENT_CALIBRATION_APPLY"),
        ]:
            w = getattr(self, attr, None)
            if w is not None:
                _safe_set(w, tr(key))

        try:
            self._refresh_config_preset_controls()
        except Exception:
            logger.warning("Failed to refresh config preset controls during retranslate.", exc_info=True)

        try:
            technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
            if technique in {"dsc", "waxs", "saxs"}:
                self._build_config_for_technique(technique)
        except Exception:
            logger.warning("Failed to rebuild translated manual config form during retranslate.", exc_info=True)

        # Results table header
        try:

            if hasattr(self, "_results_table"):

                self._results_table.setHorizontalHeaderLabels([tr("RESULTS_PARAM"), tr("RESULTS_VALUE")])
            if hasattr(self, "_history_table"):
                self._history_table.setHorizontalHeaderLabels(
                    [
                        tr("HISTORY_COL_TIME"),
                        tr("HISTORY_COL_TECHNIQUE"),
                        tr("HISTORY_COL_SUBMODULE"),
                        tr("HISTORY_COL_SCORE"),
                        tr("HISTORY_COL_STATUS"),
                    ]
                )

        except Exception:
            logger.warning("Failed to update translated table headers.", exc_info=True)

    def _toggle_language(self):

        new_lang = "zh" if get_language() != "zh" else "en"

        set_language(new_lang)

        self._retranslate_ui()

        # Re-polish the sidebar after translated labels change.
        sb = self.findChild(QWidget, "sidebar")

        if sb:

            sb.setVisible(True)

        self.log(tr("LOG_LANGUAGE_CHANGED", new_lang))
