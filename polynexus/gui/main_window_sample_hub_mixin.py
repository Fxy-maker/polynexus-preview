from __future__ import annotations

import os

from .i18n import tr
from .sample_analysis_service import request_sample_batch_analysis
from ..data.sample_db import SampleDB


class MainWindowSampleHubMixin:
    def _ensure_sample_db(self):
        if self._sample_db is None:
            self._sample_db = SampleDB()
        return self._sample_db

    def _set_sample_browser_visible(self, visible):
        browser = getattr(self, "_sample_browser", None)
        if browser is None:
            return
        browser.setVisible(visible)
        if visible:
            if hasattr(self, "_data_source_group"):
                self._data_source_group.setVisible(False)
            if hasattr(self, "_output_group"):
                self._output_group.setVisible(False)
            browser.set_db(self._ensure_sample_db())
            self._btn_run.setEnabled(False)
        else:
            if hasattr(self, "_data_source_group"):
                self._data_source_group.setVisible(True)
            if hasattr(self, "_output_group"):
                self._output_group.setVisible(True)

    def _set_joint_hub_visible(self, visible):
        hub = getattr(self, "_joint_hub", None)
        if hub is None:
            return
        if hasattr(self, "_data_source_group"):
            self._data_source_group.setVisible(not visible)
        if hasattr(self, "_output_group"):
            self._output_group.setVisible(True)
        hub.setVisible(visible)
        if visible:
            self._btn_run.setText(tr("BTN_GENERATE_OVERVIEW"))
            if not self._output_dir:
                self._output_dir = os.path.join(os.getcwd(), "polynexus_joint_output")
                if hasattr(self, "_output_input"):
                    self._output_input.setText(self._output_dir)
            hub.set_db(self._ensure_sample_db())
            self._btn_replot.setEnabled(False)
            self._btn_run.setEnabled(hub.has_selection())
        else:
            self._hide_joint_diagnostics()
            self._btn_run.setText(tr("BTN_RUN"))
            self._btn_run.setEnabled(
                bool(self._current_technique and self._current_technique != "samples")
            )

    def _on_joint_hub_selection_changed(self, count):
        if self._current_technique != "joint":
            return
        self._btn_run.setEnabled(count > 0)
        if hasattr(self, "_workflow_metric_data"):
            self._workflow_metric_data.setText(tr("WORKFLOW_SELECTED_BATCHES", count))

    def _on_joint_selected(self, mode):
        self._current_technique = "joint"
        self._current_submodule_id = mode
        self._set_nav_visual_state(mode, "joint")
        self._set_sample_browser_visible(False)
        self._set_joint_hub_visible(True)
        if hasattr(self, "_tabs"):
            self._tabs.setCurrentIndex(0)
        self._update_workspace_context()
        self._refresh_config_preset_controls()
        self.log(tr("LOG_JOINT_MODE", mode))

    def _on_samples_selected(self):
        self._current_technique = "samples"
        self._current_submodule_id = ""
        self._set_joint_hub_visible(False)
        self._set_sample_browser_visible(True)
        self._tabs.setCurrentIndex(0)
        self._set_nav_visual_state("samples", "samples")
        self._update_workspace_context()
        self._refresh_config_preset_controls()
        self.log(tr("LOG_SAMPLE_LIBRARY_OPENED"))

    def _on_sample_created(self, sample_name):
        self.log(tr("LOG_SAMPLE_CREATED", sample_name))

    def _on_sample_updated(self, sample_name):
        self.log(tr("LOG_SAMPLE_UPDATED", sample_name))

    def _clear_sample_batch_context(self):
        self._current_sample_id = ""
        self._current_batch_id = ""
        self._current_sample_name = ""
        self._current_batch_label = ""

    def _set_sample_batch_context(
        self,
        *,
        sample_id="",
        batch_id="",
        sample_name="",
        batch_label="",
    ):
        self._current_sample_id = str(sample_id or "").strip()
        self._current_batch_id = str(batch_id or "").strip()
        self._current_sample_name = str(sample_name or "").strip()
        self._current_batch_label = str(batch_label or "").strip()

    def _on_sample_selected(self, sample_id):
        db = self._ensure_sample_db()
        sample = db.get_sample(sample_id)
        self._set_sample_batch_context(
            sample_id=sample_id,
            sample_name=(sample or {}).get("polymer_name", ""),
        )
        self._update_workspace_context()
        self._refresh_config_preset_controls()

    def _on_sample_batch_created(self, batch_label, file_path):
        self.log(tr("LOG_SAMPLE_BATCH_CREATED", batch_label))
        self.log(tr("LOG_SAMPLE_FILE_ATTACHED", file_path))

    def _on_sample_batch_updated(self, batch_label):
        self.log(tr("LOG_SAMPLE_BATCH_UPDATED", batch_label))

    def _on_sample_batch_analysis_requested(self, batch_id):
        request_sample_batch_analysis(self, batch_id)

    def _on_sample_joint_requested(self, batch_ids):
        self._on_joint_selected("joint.compare")
        hub = getattr(self, "_joint_hub", None)
        if hub is not None:
            hub.select_batch_ids(batch_ids)
