from __future__ import annotations

from .i18n import tr
from .contextual_tools_service import contextual_tool_state
from .workspace_mode import WorkspaceMode, normalize_workspace_mode


class MainWindowNavigationMixin:
    @staticmethod
    def _main_window_module():
        from . import main_window as main_window_module

        return main_window_module

    def _set_nav_visual_state(self, active_id, technique):
        for key, btn in self._nav_buttons.items():
            btn_tech = btn.property("technique") or technique
            is_active = key == active_id
            btn.setStyleSheet(self._nav_sub_style(btn_tech, is_active))
            btn.setChecked(is_active)

        if hasattr(self, "_nav_indicator"):
            self._nav_indicator.hide()

    def _set_workspace_mode(self, mode):
        self._workspace_mode = normalize_workspace_mode(mode)
        return self._workspace_mode

    def _workspace_mode_value(self):
        current = getattr(self, "_workspace_mode", None)
        legacy_value = getattr(self, "_current_technique", "") or "analysis"
        if current not in (None, ""):
            try:
                normalized = normalize_workspace_mode(current)
                if normalized is not WorkspaceMode.ANALYSIS:
                    return normalized
                try:
                    legacy_mode = normalize_workspace_mode(legacy_value)
                except ValueError:
                    legacy_mode = WorkspaceMode.ANALYSIS
                if legacy_mode is not WorkspaceMode.ANALYSIS:
                    return legacy_mode
                return normalized
            except ValueError:
                pass
        try:
            return normalize_workspace_mode(legacy_value)
        except ValueError:
            return WorkspaceMode.ANALYSIS

    def _refresh_sidebar_texts(self):
        main_window_module = self._main_window_module()

        if not hasattr(self, "_nav_buttons"):
            return

        for key, label in getattr(self, "_sidebar_section_labels", {}).items():
            label.setText(
                main_window_module._lang_text(
                    main_window_module.SIDEBAR_SECTIONS.get(key, {}),
                    label.text(),
                )
            )

        for tech, btn in getattr(self, "_nav_parent_buttons", {}).items():
            icon = main_window_module.TECHNIQUE_ICONS.get(tech, "")
            label = main_window_module.TECHNIQUE_LABELS.get(tech, tech.upper())
            btn.setText(f"{icon}  {label}".strip())

            count = sum(
                1 for b in self._nav_buttons.values() if b.property("technique") == tech
            )
            btn.setToolTip(tr("SIDEBAR_SUBMODULE_COUNT", count))

        for nav_id, btn in self._nav_buttons.items():
            text = main_window_module._lang_text(
                main_window_module.SIDEBAR_MODULE_TEXT.get(nav_id, {}),
                btn.text().strip(),
            )
            btn.setText(text)

            if nav_id in main_window_module.SIDEBAR_MODULE_TOOLTIPS:
                btn.setToolTip(
                    main_window_module._lang_text(
                        main_window_module.SIDEBAR_MODULE_TOOLTIPS[nav_id]
                    )
                )

            tech = btn.property("technique") or self._current_technique or "waxs"
            btn.setStyleSheet(self._nav_sub_style(tech, btn.isChecked()))

    def _jump_to_tab(self, index: int):
        if hasattr(self, "_tabs") and 0 <= index < self._tabs.count():
            self._tabs.setCurrentIndex(index)

    def _jump_to_sample_library(self):
        self._on_samples_selected()

    def _jump_to_joint_hub(self):
        state = self._contextual_tool_state()
        if state["joint"]["available"]:
            self._on_joint_selected("joint.compare")

    def _jump_to_results(self):
        self._jump_to_tab(2)

    def _jump_to_history(self):
        self._jump_to_tab(4)

    def _contextual_tool_state(self):
        return contextual_tool_state(
            getattr(self, "_workspace_context", None),
            getattr(self, "_last_ai_tuning_context", {}),
        )

    def _update_contextual_tool_actions(self):
        state = self._contextual_tool_state()
        joint_available = bool(state["joint"]["available"])
        for key in ("joint.quick", "joint.compare"):
            button = getattr(self, "_nav_buttons", {}).get(key)
            if button is not None:
                button.setVisible(joint_available)
                button.setEnabled(joint_available)
        joint_title = getattr(self, "_sidebar_section_labels", {}).get("joint")
        if joint_title is not None:
            joint_title.setVisible(joint_available)
        convergence = getattr(self, "action_convergence_viewer", None)
        if convergence is not None:
            convergence.setEnabled(bool(state["convergence"]["available"]))
        return state

    def _on_quick_analysis_selected(self, *, announce=True):
        """Return to the standalone human-facing quick analysis entry."""
        cancel_workers = getattr(self, "_cancel_workers_for_context_switch", None)
        if callable(cancel_workers):
            cancel_workers()
        begin_request = getattr(self, "_begin_run_request", None)
        if callable(begin_request):
            begin_request()
        transition = getattr(self, "_transition_run_state", None)
        if hasattr(self, "_run_state") and callable(transition):
            transition("cancel")
        if hasattr(self, "_progress"):
            self._stop_progress_animation_fn()(self._progress)
            self._progress.setVisible(False)
        if hasattr(self, "_btn_cancel"):
            self._btn_cancel.setVisible(False)
        if hasattr(self, "_set_running_ui"):
            self._set_running_ui(False)
        cancel_ai = getattr(self, "_cancel_ai_tuning_for_context_switch", None)
        if callable(cancel_ai):
            cancel_ai()
        self._set_workspace_mode(WorkspaceMode.ANALYSIS)
        self._quick_analysis_active = True
        self._invalidate_context_bound_views()
        self._current_technique = ""
        self._current_submodule_id = ""
        self._current_filepath = ""
        self._current_input_mode = ""
        self._output_dir = ""
        self._last_persisted_run_id = ""
        if hasattr(self, "_results"):
            self._results = {}
        if hasattr(self, "_batch_results"):
            self._batch_results = []
        if hasattr(self, "_joint_report"):
            self._joint_report = None
        self._clear_sample_batch_context()
        if hasattr(self, "_path_input"):
            self._path_input.setText("")
        if hasattr(self, "_project_label"):
            self._project_label.setText(tr("NO_PROJECT"))
        if hasattr(self, "_output_input"):
            self._output_input.setText("")
        if hasattr(self, "_btn_replot"):
            self._btn_replot.setEnabled(False)
            self._btn_replot.setText(tr("BTN_REPLOT"))
        if hasattr(self, "_batch_list"):
            self._batch_list.clear()
            self._batch_list.setVisible(False)
        if hasattr(self, "_update_batch_list_copy_button"):
            self._update_batch_list_copy_button()
        if hasattr(self, "_set_results_summary"):
            self._set_results_summary("")
        if hasattr(self, "_set_results_export_control_visible"):
            self._set_results_export_control_visible(False)
        if hasattr(self, "_set_results_copy_control_visible"):
            self._set_results_copy_control_visible(False)
        if hasattr(self, "_clear_results_table_default_order"):
            self._clear_results_table_default_order()
        if hasattr(self, "_results_table"):
            self._results_table.clearContents()
            self._results_table.setRowCount(0)
        if hasattr(self, "_chart_gallery"):
            self._chart_gallery.clear()
            self._chart_gallery.setVisible(False)
        if hasattr(self, "_plots_label"):
            self._plots_label.setVisible(True)
        if hasattr(self, "_figure_preview"):
            self._figure_preview.clear()
            self._figure_preview.setVisible(False)
        self._current_figure_path = ""
        self._set_sample_browser_visible(False)
        self._set_joint_hub_visible(False)
        if hasattr(self, "_tabs"):
            self._tabs.setCurrentIndex(0)
        self._set_nav_visual_state("quick_analysis", "quick_analysis")
        if hasattr(self, "_btn_run"):
            self._btn_run.setText(tr("BTN_RUN"))
            self._btn_run.setEnabled(False)
        self._update_workspace_context()
        self._refresh_config_preset_controls()
        if announce:
            self.log(tr("LOG_QUICK_ANALYSIS_OPENED"))

    def _on_tech_saxs(self):
        self._on_technique_selected("saxs")

    def _on_tech_waxs(self):
        self._on_technique_selected("waxs")

    def _on_tech_dsc(self):
        self._on_technique_selected("dsc")

    def _on_tech_ir(self):
        self._on_technique_selected("ir")

    def _on_tech_nmr(self):
        self._on_technique_selected("nmr")

    def _on_technique_selected(self, technique):
        main_window_module = self._main_window_module()

        self._quick_analysis_active = False
        if technique != getattr(self, "_current_technique", ""):
            self._invalidate_context_bound_views()
        self._set_workspace_mode(WorkspaceMode.ANALYSIS)
        self._current_technique = technique
        self._current_submodule_id = ""
        self._set_sample_browser_visible(False)
        self._set_joint_hub_visible(False)
        self._btn_run.setEnabled(True)

        tokens = self._theme_engine.tokens
        accent = main_window_module.technique_accent(technique, tokens)
        active_id = technique if technique in self._nav_buttons else None

        if active_id is None:
            for key, btn in self._nav_buttons.items():
                if btn.property("technique") == technique:
                    active_id = key
                    break

        self._set_nav_visual_state(active_id, technique)
        self._project_label.setStyleSheet(
            f"color: {accent}; font-weight: 700; font-size: 11px; "
            f"background: transparent; border: none;"
        )

        self._build_config_for_technique(technique)
        self._refresh_config_preset_controls()
        self._update_workspace_context()
        self.log(
            tr(
                "LOG_TECHNIQUE_SELECTED",
                main_window_module.TECHNIQUE_LABELS.get(technique, technique),
            )
        )

    def _on_submodule_selected(self, technique, submodule_id):
        self._quick_analysis_active = False
        if (
            technique != getattr(self, "_current_technique", "")
            or submodule_id != getattr(self, "_current_submodule_id", "")
        ):
            self._invalidate_context_bound_views()
        self._set_workspace_mode(WorkspaceMode.ANALYSIS)
        self._current_technique = technique
        self._current_submodule_id = submodule_id
        self._set_sample_browser_visible(False)
        self._set_joint_hub_visible(False)
        self._btn_run.setEnabled(True)
        self._set_nav_visual_state(submodule_id, technique)
        self._update_workspace_context()
        self.log(tr("LOG_SUBMODULE_SELECTED", submodule_id))
        self._update_config_panel()
        self._refresh_config_preset_controls()
