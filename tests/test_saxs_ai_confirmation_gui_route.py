from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QDialogButtonBox

from polynexus.core.preprocess_optimization import stable_config_hash
from polynexus.gui.main_window import MainWindow, SideTuningReportDialog


def _static_result() -> SimpleNamespace:
    return SimpleNamespace(
        source_index=0,
        data_quality_report={"level": "Quantitative", "source_id": "frame-0"},
        guinier_evidence={"level": "Quantitative", "rg_nm": 4.0},
        metric_evidence={"porod": {"level": "Quantitative", "value": 1.2}},
        detector_quality_report={"level": "Quantitative", "source_kind": "sector_map"},
        orientation_evidence={"level": "Quantitative", "metric_name": "Herman"},
        quality_flag="OK",
        Q_star_valid=True,
    )


def _confirmation_report() -> dict[str, object]:
    current = {"smooth_window": 11}
    return {
        "technique": "saxs",
        "mode": "static",
        "preprocess_decision": {
            "decision": "request_confirmation",
            "hard_guard_results": {
                "negative_fraction": True,
                "physical_parameters": True,
            },
        },
        "selected_candidate_id": "candidate-1",
        "selected_preprocess_config": {"smooth_window": 15},
        "original_preprocess_config": current,
        "preprocess_candidates": [
            {
                "candidate_id": "candidate-1",
                "base_config_hash": stable_config_hash(current),
                "config_delta": {"smooth_window": 15},
            }
        ],
    }


def _click_apply(dialog: SideTuningReportDialog) -> int:
    button = dialog._buttons.button(QDialogButtonBox.Ok)
    assert button.isEnabled() is True
    button.click()
    return dialog.result()


def _click_cancel(dialog: SideTuningReportDialog) -> int:
    button = dialog._buttons.button(QDialogButtonBox.Cancel)
    button.click()
    return dialog.result()


def _window_with_saxs_state() -> tuple[MainWindow, SimpleNamespace, SimpleNamespace]:
    window = MainWindow()
    window._current_technique = "saxs"
    original_result = _static_result()
    engine = SimpleNamespace(
        cfg=SimpleNamespace(smooth_window=11, experiment_type="static"),
        _analysis=original_result,
    )
    window._results["saxs"] = original_result
    window._engine_cache["saxs"] = engine
    return window, engine, original_result


def test_real_saxs_confirmation_button_enters_guarded_transaction() -> None:
    app = QApplication.instance() or QApplication([])
    window, engine, _original_result = _window_with_saxs_state()
    applied: list[dict[str, object]] = []
    reruns: list[bool] = []

    def apply_config(config: dict[str, object]) -> None:
        applied.append(dict(config))
        engine.cfg.smooth_window = config["smooth_window"]

    window._apply_best_config = apply_config
    window._run_analysis = lambda: reruns.append(True)

    try:
        with patch.object(SideTuningReportDialog, "exec", new=_click_apply):
            window._on_ai_tune_finished(_confirmation_report())

        assert applied == [{"smooth_window": 15}]
        assert reruns == [True]
        assert window._preprocess_transaction.state.phase == "apply_pending"
        assert window._preprocess_transaction.state.technique == "SAXS"
    finally:
        window.deleteLater()
        app.processEvents()


def test_real_saxs_confirmation_rejection_does_not_start_transaction() -> None:
    app = QApplication.instance() or QApplication([])
    window, _engine, _original_result = _window_with_saxs_state()
    applied: list[dict[str, object]] = []

    window._apply_best_config = lambda config: applied.append(dict(config))
    window._run_analysis = lambda: applied.append({"rerun": True})

    try:
        with patch.object(SideTuningReportDialog, "exec", new=_click_cancel):
            window._on_ai_tune_finished(_confirmation_report())

        assert applied == []
        assert not hasattr(window, "_preprocess_transaction")
    finally:
        window.deleteLater()
        app.processEvents()
