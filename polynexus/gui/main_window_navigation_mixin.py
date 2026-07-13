from __future__ import annotations

from .i18n import tr
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
        self._on_joint_selected("joint.compare")

    def _jump_to_results(self):
        self._jump_to_tab(2)

    def _jump_to_history(self):
        self._jump_to_tab(4)

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
