from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtWidgets import QApplication, QDialog

from polynexus.gui.main_window import MainWindow
from polynexus.gui import main_window_ai_tuning_mixin as ai_tuning_mixin_module
from polynexus.gui.main_window_ai_tuning_mixin import MainWindowAITuningMixin
from polynexus.core.preprocess_optimization.candidates import stable_config_hash


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


class _FinishedDialog:
    def __init__(self, _report, _parent):
        pass

    def exec(self):
        return QDialog.Accepted


class _FinishedWindow(MainWindowAITuningMixin):
    def __init__(self, technique="saxs"):
        self._current_technique = technique
        self._ai_progress = None
        self.begin_calls = 0
        self.register_calls = 0
        self.logs = []

    @classmethod
    def _side_tuning_report_dialog_class(cls):
        return _FinishedDialog

    def _update_workflow_task_card(self):
        pass

    def _ai_tuning_report_context(self, _report):
        return {}

    def _current_tuning_goal(self):
        return "quality"

    def _ai_tuning_goal_label(self, goal):
        return goal

    def _update_workspace_context(self):
        pass

    def _update_work_memory_panel(self):
        pass

    def _update_results_review_panel(self):
        pass

    def _begin_preprocess_confirmation(self, _report, *, accepted_by):
        assert accepted_by == "user_confirmed"
        self.begin_calls += 1
        return True

    def _register_preprocess_auto_accept(self, _report):
        self.register_calls += 1
        return True

    def _undo_last_preprocess_apply(self):
        return True

    def log(self, message):
        self.logs.append(message)


def _saxs_stability_auto_report(*, complete=True, quality=True):
    original = {"q_min": 0.01}
    selected = {"q_min": 0.02}
    candidate_id = "saxs-auto-1"
    return {
        "technique": "SAXS",
        "mode": "strain",
        "preprocess_decision": {
            "decision": "auto_accept",
            "simulated_decision": "auto_accept",
            "confidence_band": "high",
            "hard_guard_results": {
                "stability_plateau": True,
                "physical_gate": True,
                "quality_gate": quality,
                "cross_frame_continuity": True,
            },
        },
        "selected_candidate_id": candidate_id if complete else "",
        "original_preprocess_config": original,
        "selected_preprocess_config": selected,
        "preprocess_candidates": [
            {
                "candidate_id": candidate_id,
                "base_config_hash": stable_config_hash(original),
                "config_delta": selected,
            }
        ] if complete else [],
        "stability_report": {
            "mode": "strain",
            "decision": "auto_accept",
            "complete": True,
            "plateau": {"connected": True, "trial_indices": [0]},
            "continuity": {"passed": True, "status": "passed", "frame_count": 5},
            "physics_gate_passed": True,
            "quality_gate_passed": quality,
            "reason_codes": [],
        },
    }


def test_finished_saxs_stability_auto_accept_never_registers_unattended_apply():
    for report in (
        _saxs_stability_auto_report(),
        _saxs_stability_auto_report(complete=False),
        _saxs_stability_auto_report(quality=False),
    ):
        window = _FinishedWindow("saxs")

        window._on_ai_tune_finished(report)

        assert window.register_calls == 0
        assert window.begin_calls <= 1


def test_finished_generic_auto_accept_keeps_existing_registration_path():
    window = _FinishedWindow("dsc")

    window._on_ai_tune_finished(_preprocess_report("auto_accept"))

    assert window.register_calls == 1


def test_finished_mixin_defense_blocks_stale_saxs_auto_apply(monkeypatch):
    window = _FinishedWindow("dsc")
    report = _preprocess_report("auto_accept")
    report["technique"] = "SAXS"
    report["stability_report"] = "malformed-stale-report"
    monkeypatch.setattr(
        ai_tuning_mixin_module,
        "build_preprocess_ui_decision",
        lambda _report: SimpleNamespace(mode="auto_apply"),
    )

    window._on_ai_tune_finished(report)

    assert window.register_calls == 0


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
                "orientation_mask_dilation_px": (2, 4),
                "chi_halfwidth": 22.5,
                "chi_halfwidth_authoritative": True,
            }
        )
        config = window._build_run_config()

        assert config.beam_center_offset_x_px == 1.23456789
        assert config.beam_center_offset_y_px == -0.87654321
        assert config.mask_dilation_px == 2
        assert config.orientation_mask_dilation_px == (2, 4)
        assert config.chi_halfwidth == 22.5
        assert config.chi_halfwidth_authoritative is True

        selected = {
            "chi_halfwidth": 22.5,
            "chi_halfwidth_authoritative": True,
        }
        captured = window._capture_preprocess_config(selected)
        assert stable_config_hash(captured) == stable_config_hash(selected)
    finally:
        window.deleteLater()
        app.processEvents()
