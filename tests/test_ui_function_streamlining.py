from __future__ import annotations

import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from polynexus.gui.main_window import MainWindow
from polynexus.gui.main_window_navigation_mixin import MainWindowNavigationMixin
from polynexus.gui.main_window_sample_hub_mixin import MainWindowSampleHubMixin
from polynexus.gui.main_window_workspace_mixin import MainWindowWorkspaceMixin
from polynexus.gui.shortcuts import SHORTCUTS
from polynexus.gui.workspace_mode import WorkspaceMode


class _FakeTabs:
    def __init__(self):
        self.current_index = None

    def setCurrentIndex(self, index):
        self.current_index = index


class _NavigationHarness(MainWindowNavigationMixin, MainWindowSampleHubMixin):
    def __init__(self):
        self._current_technique = ""
        self._current_submodule_id = ""
        self._workspace_mode = WorkspaceMode.ANALYSIS
        self._tabs = _FakeTabs()
        self.events = []

    def _set_nav_visual_state(self, *args):
        self.events.append(("nav", args))

    def _set_sample_browser_visible(self, visible):
        self.events.append(("samples", visible))

    def _set_joint_hub_visible(self, visible):
        self.events.append(("joint", visible))

    def _update_workspace_context(self):
        self.events.append(("context", self._workspace_mode))

    def _refresh_config_preset_controls(self):
        self.events.append(("presets", None))

    def log(self, message):
        self.events.append(("log", message))


def test_joint_alias_enters_one_canonical_joint_workspace():
    harness = _NavigationHarness()

    harness._on_joint_selected("joint.compare")

    assert harness._workspace_mode is WorkspaceMode.JOINT
    assert harness._current_technique == "joint"
    assert harness._current_submodule_id == "joint.compare"
    assert harness._tabs.current_index == 0


def test_samples_route_enters_samples_workspace_without_joint_state():
    harness = _NavigationHarness()

    harness._on_samples_selected()

    assert harness._workspace_mode is WorkspaceMode.SAMPLES
    assert harness._current_technique == "samples"
    assert harness._current_submodule_id == ""
    assert harness._tabs.current_index == 0


def test_technique_selection_returns_to_analysis_workspace():
    harness = _NavigationHarness()

    harness._set_workspace_mode(WorkspaceMode.SAMPLES)
    harness._set_workspace_mode(WorkspaceMode.ANALYSIS)

    assert harness._workspace_mode is WorkspaceMode.ANALYSIS


def test_workspace_context_uses_explicit_mode_over_legacy_technique_value():
    class _WorkspaceHarness(MainWindowWorkspaceMixin):
        def __init__(self):
            self._workspace_mode = WorkspaceMode.JOINT
            self._current_technique = "saxs"
            self._current_submodule_id = ""
            self._current_filepath = ""
            self._workspace_title = SimpleNamespace(setText=self._set_title)
            self._workspace_subtitle = SimpleNamespace(setText=self._set_subtitle)
            self.titles = []

        def _set_title(self, value):
            self.titles.append(value)

        def _set_subtitle(self, value):
            self.titles.append(value)

        def _history_submodule_text(self, _value):
            return ""

        def _workspace_input_mode_text(self):
            return ""

        def _idle_workflow_state_text(self):
            return "Ready"

        def _update_workflow_task_card(self):
            pass

        def _update_context_suggestions(self):
            pass

        def _update_work_memory_panel(self):
            pass

        def _update_results_compare_panel(self):
            pass

    harness = _WorkspaceHarness()

    harness._update_workspace_context()

    assert harness._workspace_mode is WorkspaceMode.JOINT
    assert len(harness.titles) == 2


def test_plot_workspace_uses_preview_view_action_as_canonical_owner():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()

    assert not hasattr(window, "_btn_view_current_figure")
    assert not hasattr(window, "_btn_convergence_viewer")
    assert hasattr(window, "action_convergence_viewer")
    assert window._figure_preview._btn_view is not None

    window.deleteLater()
    app.processEvents()


def test_primary_shortcuts_target_canonical_main_window_actions():
    shortcut_targets = {keys: method for keys, method, _description in SHORTCUTS}

    assert shortcut_targets["Ctrl+R"] == "_run_analysis"
    assert shortcut_targets["Ctrl+Shift+R"] == "_replot"
    assert shortcut_targets["Ctrl+E"] == "_export_results"


def test_main_window_keeps_minimum_supported_size():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()

    assert window.minimumSize().width() >= 960
    assert window.minimumSize().height() >= 600

    window.deleteLater()
    app.processEvents()
