from __future__ import annotations

import importlib
import importlib.util

from polynexus.gui.main_window import MainWindow


def test_main_window_reuses_sample_and_joint_workspace_helpers_from_sample_hub_mixin() -> None:
    spec = importlib.util.find_spec("polynexus.gui.main_window_sample_hub_mixin")
    assert spec is not None

    module = importlib.import_module("polynexus.gui.main_window_sample_hub_mixin")
    mixin = module.MainWindowSampleHubMixin

    assert MainWindow._ensure_sample_db is mixin._ensure_sample_db
    assert (
        MainWindow._set_sample_browser_visible
        is mixin._set_sample_browser_visible
    )
    assert (
        MainWindow._set_joint_hub_visible
        is mixin._set_joint_hub_visible
    )
    assert (
        MainWindow._on_joint_hub_selection_changed
        is mixin._on_joint_hub_selection_changed
    )
    assert MainWindow._on_joint_selected is mixin._on_joint_selected
    assert MainWindow._on_samples_selected is mixin._on_samples_selected
    assert MainWindow._on_sample_created is mixin._on_sample_created
    assert MainWindow._on_sample_updated is mixin._on_sample_updated
    assert MainWindow._clear_sample_batch_context is mixin._clear_sample_batch_context
    assert MainWindow._set_sample_batch_context is mixin._set_sample_batch_context
    assert MainWindow._on_sample_selected is mixin._on_sample_selected
    assert (
        MainWindow._on_sample_batch_created
        is mixin._on_sample_batch_created
    )
    assert (
        MainWindow._on_sample_batch_updated
        is mixin._on_sample_batch_updated
    )
    assert (
        MainWindow._on_sample_batch_analysis_requested
        is mixin._on_sample_batch_analysis_requested
    )
    assert MainWindow._on_sample_joint_requested is mixin._on_sample_joint_requested
