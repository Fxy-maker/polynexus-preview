from __future__ import annotations

from PySide6.QtWidgets import QApplication

from polynexus.gui.main_window import MainWindow
from polynexus.gui.main_window_ai_tuning_mixin import MainWindowAITuningMixin


class _PreprocessWindow(MainWindowAITuningMixin):
    def __init__(self):
        self._current_technique = "dsc"
        self._results = {"dsc": {"status": "original"}}
        self.original_result = self._results["dsc"]
        self.config = {"smooth_window": 11}
        self.run_count = 0
        self.persisted = []
        self.revoked = []

    def _config_value_by_key(self, key):
        return self.config.get(key)

    def _config_widget_by_key(self, key):
        return object() if key in self.config else None

    def _apply_best_config(self, best_config):
        self.config.update(best_config)

    def _run_analysis(self):
        self.run_count += 1

    def _persist_preprocess_experience_proposal(self, proposal, *, accepted_by):
        self.persisted.append((proposal["experience_id"], accepted_by))
        return proposal["experience_id"]

    def _revoke_preprocess_experience(self, experience_id):
        self.revoked.append(experience_id)
        return True


def _preprocess_report(decision="request_confirmation"):
    return {
        "preprocess_decision": {
            "decision": decision,
            "simulated_decision": decision,
            "confidence_band": "high" if decision == "auto_accept" else "medium",
        },
        "selected_preprocess_config": {"smooth_window": 15},
        "original_preprocess_config": {"smooth_window": 11},
        "experience_proposal": {
            "experience_id": "preprocess-c1",
            "key": {},
            "config_delta": {"smooth_window": 15},
        },
    }


def test_confirmation_starts_transaction_but_defers_experience_until_success():
    window = _PreprocessWindow()

    assert window._begin_preprocess_confirmation(
        _preprocess_report(), accepted_by="user_confirmed"
    ) is True
    assert window.config == {"smooth_window": 15}
    assert window.persisted == []

    window._finalize_preprocess_apply_success()

    assert window.persisted == [("preprocess-c1", "user_confirmed")]


def test_failed_rerun_restores_previous_result_and_config():
    window = _PreprocessWindow()
    window._begin_preprocess_confirmation(
        _preprocess_report(), accepted_by="user_confirmed"
    )
    window._results["dsc"] = {"status": "partial"}

    window._rollback_preprocess_apply_failure()

    assert window.config == {"smooth_window": 11}
    assert window._results["dsc"] is window.original_result


def test_auto_accept_path_registers_existing_commit_and_undoes_without_reapply():
    window = _PreprocessWindow()

    assert window._register_preprocess_auto_accept(_preprocess_report("auto_accept"))
    assert window.persisted == [("preprocess-c1", "auto_accept")]
    assert window._undo_last_preprocess_apply() is True
    assert window.config == {"smooth_window": 11}


def test_main_window_reuses_ai_tuning_helpers_from_ai_tuning_mixin():
    assert MainWindow.on_ai_tune_clicked is MainWindowAITuningMixin.on_ai_tune_clicked
    assert MainWindow._current_ai_settings is MainWindowAITuningMixin._current_ai_settings
    assert MainWindow._ai_tuning_workspace_context is MainWindowAITuningMixin._ai_tuning_workspace_context
    assert MainWindow._current_tuning_goal is MainWindowAITuningMixin._current_tuning_goal
    assert MainWindow._ai_tuning_goal_label is MainWindowAITuningMixin._ai_tuning_goal_label
    assert MainWindow._ai_tuning_context_summary is MainWindowAITuningMixin._ai_tuning_context_summary
    assert MainWindow._ai_tuning_previous_round_summary is MainWindowAITuningMixin._ai_tuning_previous_round_summary
    assert MainWindow._benchmark_delta_text is MainWindowAITuningMixin._benchmark_delta_text
    assert MainWindow._benchmark_rate_text is MainWindowAITuningMixin._benchmark_rate_text
    assert MainWindow._benchmark_summary_text is MainWindowAITuningMixin._benchmark_summary_text
    assert MainWindow._ai_tuning_report_context is MainWindowAITuningMixin._ai_tuning_report_context
    assert MainWindow._ai_tuning_previous_round_label is MainWindowAITuningMixin._ai_tuning_previous_round_label
    assert MainWindow._ai_tuning_previous_round_empty_text is MainWindowAITuningMixin._ai_tuning_previous_round_empty_text
    assert MainWindow._ai_tuning_previous_round_stop_text is MainWindowAITuningMixin._ai_tuning_previous_round_stop_text
    assert MainWindow._ai_tuning_previous_round_risks_text is MainWindowAITuningMixin._ai_tuning_previous_round_risks_text
    assert MainWindow._ai_tuning_previous_round_goal_text is MainWindowAITuningMixin._ai_tuning_previous_round_goal_text
    assert MainWindow._ai_tuning_previous_round_accepted_text is MainWindowAITuningMixin._ai_tuning_previous_round_accepted_text
    assert MainWindow._ai_tuning_previous_round_goal_body is MainWindowAITuningMixin._ai_tuning_previous_round_goal_body
    assert MainWindow._ai_tuning_chain_summary is MainWindowAITuningMixin._ai_tuning_chain_summary
    assert MainWindow._ai_tuning_tunable_summary is MainWindowAITuningMixin._ai_tuning_tunable_summary
    assert MainWindow._config_value_by_key is MainWindowAITuningMixin._config_value_by_key
    assert MainWindow._on_ai_tune_progress is MainWindowAITuningMixin._on_ai_tune_progress
    assert MainWindow._on_ai_tune_finished is MainWindowAITuningMixin._on_ai_tune_finished
    assert MainWindow._on_ai_tune_error is MainWindowAITuningMixin._on_ai_tune_error
    assert MainWindow._apply_best_config is MainWindowAITuningMixin._apply_best_config
    assert MainWindow._ai_tuning_chain_snapshot is MainWindowAITuningMixin._ai_tuning_chain_snapshot


def test_saxs_stability_geometry_and_mask_values_survive_panel_round_trip():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    try:
        window._current_technique = "saxs"
        window._on_submodule_selected("saxs", "saxs.strain")

        window._apply_best_config(
            {
                "beam_center_offset_x_px": 1.23456789,
                "beam_center_offset_y_px": -0.87654321,
                "mask_dilation_px": 2,
            }
        )
        config = window._build_run_config()

        assert config.beam_center_offset_x_px == 1.23456789
        assert config.beam_center_offset_y_px == -0.87654321
        assert config.mask_dilation_px == 2
    finally:
        window.deleteLater()
        app.processEvents()
