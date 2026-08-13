from __future__ import annotations

from .i18n import tr


class MainWindowShellMixin:
    _COMPACT_CONTENT_WIDTH = 1500

    def _responsive_content_width(self):
        content = getattr(self, "_content", None)
        width_getter = getattr(content, "width", None)
        if callable(width_getter):
            try:
                return int(width_getter())
            except (TypeError, ValueError):
                pass
        width_getter = getattr(self, "width", None)
        return int(width_getter()) if callable(width_getter) else 0

    def _apply_responsive_shell(self):
        compact = self._responsive_content_width() < self._COMPACT_CONTENT_WIDTH
        for attr in (
            "_workflow_metric_tech",
            "_workflow_metric_data",
            "_workflow_metric_state",
        ):
            widget = getattr(self, attr, None)
            if widget is not None:
                widget.setVisible(not compact)
        for attr in ("_btn_replot", "_btn_export_current"):
            widget = getattr(self, attr, None)
            if widget is not None:
                widget.setVisible(not compact)
        project_export = getattr(self, "_btn_export", None)
        if project_export is not None:
            project_export.setVisible(not compact)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_responsive_shell()

    def _set_log_drawer_expanded(self, expanded: bool):
        """Collapse diagnostics to keep the primary workflow compact."""
        group = getattr(self, "_log_group", None)
        if group is None:
            return
        layout = group.layout()
        if layout is None:
            return
        for index in range(layout.count()):
            item = layout.itemAt(index)
            widget = item.widget()
            if widget is not None:
                widget.setVisible(bool(expanded))
            elif item.layout() is not None:
                for child_index in range(item.layout().count()):
                    child = item.layout().itemAt(child_index).widget()
                    if child is not None:
                        child.setVisible(bool(expanded))

    @staticmethod
    def _main_window_module():
        from . import main_window as main_window_module

        return main_window_module

    def _toggle_theme(self):
        """Toggle between dark and light theme."""
        main_window_module = self._main_window_module()

        self._theme_engine.toggle()
        self._apply_theme()

        new_name = tr("THEME_DARK") if self._theme_engine.is_dark else tr("THEME_LIGHT")
        self.log(tr("LOG_THEME_CHANGED", new_name))

        try:
            self._btn_theme.setText("\u263e" if self._theme_engine.is_dark else "\u2600")
        except Exception:
            main_window_module.logger.warning(
                "Failed to update re-plot tooltip during retranslate.",
                exc_info=True,
            )

        try:
            self._statusbar.showMessage(tr("STATUSBAR_THEME", new_name))
        except Exception:
            main_window_module.logger.warning(
                "Failed to update language toggle text during retranslate.",
                exc_info=True,
            )

    def _build_menubar(self):
        """Create menu bar with File/Edit/View/Help menus."""
        main_window_module = self._main_window_module()
        menubar = self.menuBar()

        self._menu_file = menubar.addMenu(tr("MENU_FILE"))
        self._act_open = self._menu_file.addAction(tr("ACTION_OPEN"))
        self._act_open.triggered.connect(self._browse_file)
        self._act_export = self._menu_file.addAction(tr("ACTION_EXPORT"))
        self._act_export.triggered.connect(self._export_results)
        self._menu_file.addSeparator()
        self._act_quit = self._menu_file.addAction(tr("ACTION_QUIT"))
        self._act_quit.triggered.connect(self.close)

        self._menu_edit = menubar.addMenu(tr("MENU_EDIT"))
        self._act_settings = self._menu_edit.addAction(tr("ACTION_SETTINGS"))
        self._act_settings.triggered.connect(self._on_settings)

        self._menu_view = menubar.addMenu(tr("MENU_VIEW"))
        self._act_toggle_sidebar = self._menu_view.addAction(tr("ACTION_TOGGLE_SIDEBAR"))
        self._act_toggle_sidebar.triggered.connect(self._toggle_sidebar)
        self._act_toggle_theme = self._menu_view.addAction(tr("ACTION_TOGGLE_THEME"))
        self._act_toggle_theme.triggered.connect(self._toggle_theme)
        self._act_toggle_lang = self._menu_view.addAction(tr("ACTION_TOGGLE_LANG"))
        self._act_toggle_lang.triggered.connect(self._toggle_language)

        self.action_convergence_viewer = main_window_module.QAction(tr("CONVERGENCE_DASHBOARD"), self)
        self.action_convergence_viewer.setObjectName("action_convergence_viewer")
        self.action_convergence_viewer.triggered.connect(self._open_convergence_viewer)
        self._menu_view.addAction(self.action_convergence_viewer)

        self._act_view_analysis_plan_evaluation = main_window_module.QAction(
            tr("ACTION_VIEW_ANALYSIS_PLAN_EVALUATION"), self
        )
        self._act_view_analysis_plan_evaluation.setObjectName("action_view_analysis_plan_evaluation")
        self._act_view_analysis_plan_evaluation.setEnabled(False)
        self._act_view_analysis_plan_evaluation.triggered.connect(self._show_analysis_plan_evaluation)
        self._menu_view.addAction(self._act_view_analysis_plan_evaluation)

        self._act_attach_quick_run = main_window_module.QAction(tr("ACTION_ATTACH_QUICK_RUN"), self)
        self._act_attach_quick_run.setObjectName("action_attach_quick_run")
        self._act_attach_quick_run.setEnabled(False)
        self._act_attach_quick_run.triggered.connect(self._attach_current_quick_run_to_project)
        self._menu_view.addAction(self._act_attach_quick_run)

        self._menu_help = menubar.addMenu(tr("MENU_HELP"))
        self._act_about = self._menu_help.addAction(tr("ACTION_ABOUT"))
        self._act_about.triggered.connect(self._on_help)

    def _build_statusbar(self):
        """Create status bar with technique indicator."""
        main_window_module = self._main_window_module()

        self._statusbar = self.statusBar()
        self._statusbar.setObjectName("statusbar")

        self._status_tech_label = main_window_module.QLabel(f" {tr('WORKSPACE_TITLE_DEFAULT')} ")
        self._status_tech_label.setObjectName("status_tech")
        self._statusbar.addWidget(self._status_tech_label)

        spacer = main_window_module.QWidget()
        spacer.setSizePolicy(
            main_window_module.QSizePolicy.Expanding,
            main_window_module.QSizePolicy.Preferred,
        )
        self._statusbar.addWidget(spacer, 1)
        self._statusbar.showMessage(tr("STATUSBAR_READY"))

    def _toggle_sidebar(self):
        """Toggle sidebar visibility."""
        main_window_module = self._main_window_module()

        sidebar = getattr(self, "_sidebar", None) or self.findChild(main_window_module.QWidget, "sidebar")
        if sidebar:
            if sidebar.isVisible():
                def anim_done():
                    sidebar.setVisible(False)

                main_window_module.animate_width(sidebar, 0)
                getattr(sidebar, "_pn_width_anim", None).finished.connect(anim_done)
            else:
                sidebar.setVisible(True)
                sidebar.setMinimumWidth(0)
                sidebar.setMaximumWidth(0)
                main_window_module.animate_width(sidebar, self._sidebar_expanded_width)

    def _on_settings(self):
        """Open settings dialog."""
        main_window_module = self._main_window_module()
        dialog = main_window_module.SettingsDialog(self)
        dialog.exec()

    def _on_help(self):
        """Show about dialog."""
        self._main_window_module().QMessageBox.about(self, tr("ACTION_ABOUT"), tr("ABOUT_TEXT"))

    def _show_analysis_plan_evaluation(self):
        state = self._contextual_tool_state()
        robustness = state["robustness"]
        if not robustness["available"]:
            return False
        from .analysis_plan_view_service import analysis_plan_evaluation_summary

        report = getattr(self, "_last_ai_tuning_context", {})
        try:
            summary = analysis_plan_evaluation_summary(report["analysis_plan_evaluation"])
        except (KeyError, TypeError, ValueError):
            return False
        review_limits = ", ".join(summary["review_limits"]) or tr("COMMON_NONE")
        message = tr(
            "ANALYSIS_PLAN_EVALUATION_SUMMARY",
            summary["plan_id"],
            summary["candidate_count"],
            summary["stable_candidate_count"],
            summary["replay_status"],
            review_limits,
        )
        self._main_window_module().QMessageBox.information(
            self,
            tr("ACTION_VIEW_ANALYSIS_PLAN_EVALUATION"),
            message,
        )
        return True

    def _attach_current_quick_run_to_project(self):
        state = self._contextual_tool_state()
        attachment_state = state["project_attachment"]
        if not attachment_state["available"]:
            return False
        main_window_module = self._main_window_module()
        project_root = main_window_module.QFileDialog.getExistingDirectory(
            self,
            tr("FILE_DIALOG_PROJECT_DIRECTORY"),
            self._get_last_dir(),
        )
        if not project_root:
            return False
        try:
            from .quick_run_attachment_service import attach_current_run_to_project

            attachment = attach_current_run_to_project(self._workspace_context, project_root)
        except (OSError, TypeError, ValueError, UnicodeError) as exc:
            main_window_module.QMessageBox.warning(
                self,
                tr("ACTION_ATTACH_QUICK_RUN"),
                tr("QUICK_RUN_ATTACHMENT_FAILED", str(exc)),
            )
            return False
        self.log(tr("LOG_QUICK_RUN_ATTACHED", attachment.manifest_path))
        main_window_module.QMessageBox.information(
            self,
            tr("ACTION_ATTACH_QUICK_RUN"),
            tr("QUICK_RUN_ATTACHMENT_DONE", attachment.manifest_path),
        )
        return True

    def _on_quit(self):
        """Quit application."""
        self.close()
