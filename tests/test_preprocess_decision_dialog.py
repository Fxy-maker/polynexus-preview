from __future__ import annotations

import os
from collections import UserDict
from types import SimpleNamespace

import pytest
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QDialogButtonBox

from polynexus.core.preprocess_optimization import stable_config_hash
from polynexus.gui.main_window import SideTuningReportDialog
from polynexus.gui import main_window as main_window_module


def report_with(decision: str, confidence: str, simulated: str | None = None):
    return {
        "preprocess_decision": {
            "decision": decision,
            "simulated_decision": simulated or decision,
            "confidence_band": confidence,
            "reason_codes": ["noise_reduced"],
        },
        "selected_preprocess_config": {"smooth_window": 15},
        "preprocess_evidence": [
            {"candidate_id": "c1", "weak_peak_retention": 1.0, "peak_shift": 0.01}
        ],
    }


def saxs_stability_report(*, decision: str, complete_contract: bool):
    candidate_id = "saxs-stability-1"
    original_config = {"q_min": 0.01}
    selected_config = {"q_min": 0.02} if decision == "request_confirmation" else {}
    report = {
        "technique": "SAXS",
        "mode": "strain",
        "preprocess_decision": {
            "decision": decision,
            "simulated_decision": decision,
            "confidence_band": "medium" if decision == "request_confirmation" else "low",
            "reason_codes": [] if decision == "request_confirmation" else ["quality_gate_failed"],
            "hard_guard_results": {
                "stability_plateau": True,
                "physical_gate": True,
                "quality_gate": decision == "request_confirmation",
                "cross_frame_continuity": True,
            },
        },
        "selected_candidate_id": candidate_id if complete_contract else "",
        "original_preprocess_config": original_config if selected_config else {},
        "selected_preprocess_config": selected_config,
        "preprocess_candidates": [
            {
                "candidate_id": candidate_id,
                "base_config_hash": stable_config_hash(original_config),
                "config_delta": selected_config,
            }
        ] if complete_contract else [],
        "stability_report": {
            "mode": "strain",
            "decision": decision,
            "complete": True,
            "plateau": {
                "connected": True,
                "trial_indices": [0, 1, 2, 3],
                "coverage_fraction": 0.8,
                "parameter_bounds": {"q_min": [0.01, 0.03]},
            },
            "active_dimensions": ["q_min"],
            "excluded_dimensions": {},
            "continuity": {"status": "passed", "passed": True, "frame_count": 5},
            "physics_gate_passed": True,
            "quality_gate_passed": decision == "request_confirmation",
            "reason_codes": [] if decision == "request_confirmation" else ["quality_gate_failed"],
            "perturbation_intervals": {},
            "trials": [],
        },
    }
    return report


def test_confirm_dialog_enables_apply_and_uses_selected_config() -> None:
    app = QApplication.instance() or QApplication([])
    dialog = SideTuningReportDialog(report_with("request_confirmation", "medium"))

    assert dialog.best_config() == {"smooth_window": 15}
    assert dialog._buttons.button(QDialogButtonBox.Ok).isEnabled() is True
    assert "weak_peak_retention" in dialog._preprocess_metrics_label.text()

    dialog.deleteLater()
    app.processEvents()


def test_shadow_disables_apply_and_auto_accept_offers_undo() -> None:
    app = QApplication.instance() or QApplication([])
    shadow = SideTuningReportDialog(
        report_with("keep_original", "high", simulated="auto_accept")
    )
    auto = SideTuningReportDialog(report_with("auto_accept", "high"))

    assert shadow._buttons.button(QDialogButtonBox.Ok).isEnabled() is False
    assert "Undo" in auto._buttons.button(QDialogButtonBox.Ok).text()

    shadow.deleteLater()
    auto.deleteLater()
    app.processEvents()


def test_saxs_stability_dialog_renders_evidence_and_preserves_apply_gate() -> None:
    app = QApplication.instance() or QApplication([])
    complete = SideTuningReportDialog(
        saxs_stability_report(decision="request_confirmation", complete_contract=True)
    )
    incomplete = SideTuningReportDialog(
        saxs_stability_report(decision="request_confirmation", complete_contract=False)
    )
    retained = SideTuningReportDialog(
        saxs_stability_report(decision="keep_original", complete_contract=False)
    )

    complete_text = complete._preprocess_metrics_label.text()
    assert "platform_points: 4" in complete_text
    assert "continuity_status: passed" in complete_text
    assert "protected metrics available" not in complete_text
    assert complete._buttons.button(QDialogButtonBox.Ok).isEnabled() is True
    assert incomplete._buttons.button(QDialogButtonBox.Ok).isEnabled() is False
    assert retained._buttons.button(QDialogButtonBox.Ok).isEnabled() is False
    assert "quality_gate_failed" in retained._preprocess_metrics_label.text()

    complete.deleteLater()
    incomplete.deleteLater()
    retained.deleteLater()
    app.processEvents()


def test_dialog_prefers_canonical_perturbation_intervals_over_bootstrap_alias() -> None:
    app = QApplication.instance() or QApplication([])
    report = saxs_stability_report(
        decision="request_confirmation",
        complete_contract=True,
    )
    report["stability_report"]["perturbation_intervals"] = {
        "score": {"lower": 0.71, "upper": 0.90}
    }
    report["stability_report"]["bootstrap"] = {
        "score": {"lower": -1.0, "upper": -0.5}
    }
    canonical = SideTuningReportDialog(report)

    report["stability_report"]["perturbation_intervals"] = {}
    empty_canonical = SideTuningReportDialog(report)

    assert "score95%=0.71..0.9" in canonical._issue_stability_label.text()
    assert "-1.0" not in canonical._issue_stability_label.text()
    assert "score95%=N/A..N/A" in empty_canonical._issue_stability_label.text()
    assert "-1.0" not in empty_canonical._issue_stability_label.text()

    canonical.deleteLater()
    empty_canonical.deleteLater()
    app.processEvents()


def test_dialog_malformed_interval_payloads_display_na_without_fallback() -> None:
    app = QApplication.instance() or QApplication([])
    report = saxs_stability_report(
        decision="request_confirmation",
        complete_contract=True,
    )
    report["stability_report"]["perturbation_intervals"] = {
        "score": ["malformed"]
    }
    report["stability_report"]["bootstrap"] = {
        "score": {"lower": -1.0, "upper": -0.5}
    }
    malformed_score = SideTuningReportDialog(report)

    report["stability_report"]["perturbation_intervals"] = {
        "score": {"lower": float("nan"), "upper": float("inf")}
    }
    nonfinite_bounds = SideTuningReportDialog(report)

    report["stability_report"].pop("perturbation_intervals")
    report["stability_report"]["bootstrap"] = {"score": "malformed"}
    malformed_alias = SideTuningReportDialog(report)

    for dialog in (malformed_score, nonfinite_bounds, malformed_alias):
        assert "score95%=N/A..N/A" in dialog._issue_stability_label.text()
        dialog.deleteLater()
    app.processEvents()


def test_dialog_accepts_mapping_perturbation_interval_payload() -> None:
    app = QApplication.instance() or QApplication([])
    report = saxs_stability_report(
        decision="request_confirmation",
        complete_contract=True,
    )
    report["stability_report"]["perturbation_intervals"] = UserDict(
        {"score": UserDict({"lower": 0.71, "upper": 0.90})}
    )

    dialog = SideTuningReportDialog(report)

    assert "score95%=0.71..0.9" in dialog._issue_stability_label.text()
    dialog.deleteLater()
    app.processEvents()


@pytest.mark.parametrize("continuity", [None, [], "malformed"])
def test_dialog_malformed_continuity_displays_fail_without_raising(continuity) -> None:
    app = QApplication.instance() or QApplication([])
    report = saxs_stability_report(
        decision="request_confirmation",
        complete_contract=True,
    )
    report["stability_report"]["continuity"] = continuity

    dialog = SideTuningReportDialog(report)

    assert "continuity=fail" in dialog._issue_stability_label.text()
    dialog.deleteLater()
    app.processEvents()


def test_dialog_extreme_interval_bound_displays_na_without_raising() -> None:
    app = QApplication.instance() or QApplication([])
    report = saxs_stability_report(
        decision="request_confirmation",
        complete_contract=True,
    )
    report["stability_report"]["perturbation_intervals"] = {
        "score": {"lower": 10**400, "upper": 0.90}
    }

    dialog = SideTuningReportDialog(report)

    assert "score95%=N/A..0.9" in dialog._issue_stability_label.text()
    dialog.deleteLater()
    app.processEvents()


def test_dialog_metric_rows_handle_unprintable_values(monkeypatch) -> None:
    class Unprintable:
        str_calls = 0
        repr_calls = 0

        def __str__(self):
            type(self).str_calls += 1
            raise RuntimeError("no string")

        def __repr__(self):
            type(self).repr_calls += 1
            raise RuntimeError("no repr")

    monkeypatch.setattr(
        main_window_module,
        "build_preprocess_ui_decision",
        lambda _report: SimpleNamespace(
            mode="keep_original",
            title="Evidence",
            summary="Summary",
            metric_rows={"unsafe": Unprintable()},
            reason_codes=(),
            apply_enabled=False,
            undo_enabled=False,
            selected_config={},
        ),
    )
    app = QApplication.instance() or QApplication([])

    dialog = SideTuningReportDialog(
        {"preprocess_decision": {"decision": "keep_original"}}
    )

    assert "unsafe: N/A" in dialog._preprocess_metrics_label.text()
    assert Unprintable.str_calls == 0
    assert Unprintable.repr_calls == 0
    dialog.deleteLater()
    app.processEvents()


def test_dialog_standard_containers_and_huge_int_are_bounded(monkeypatch) -> None:
    monkeypatch.setattr(
        main_window_module,
        "build_preprocess_ui_decision",
        lambda _report: SimpleNamespace(
            mode="keep_original",
            title="Evidence",
            summary="Summary",
            metric_rows={
                "big_dict": {f"k{index}": index for index in range(100)},
                "big_list": list(range(100)),
                "huge_int": 10**400,
            },
            reason_codes=(),
            apply_enabled=False,
            undo_enabled=False,
            selected_config={},
        ),
    )
    app = QApplication.instance() or QApplication([])

    dialog = SideTuningReportDialog(
        {"preprocess_decision": {"decision": "keep_original"}}
    )

    text = dialog._preprocess_metrics_label.text()
    assert len(text) < 1400
    assert "k0" in text
    assert "k99" not in text
    assert "..." in text
    assert "huge_int: N/A" in text
    dialog.deleteLater()
    app.processEvents()


def test_dialog_ignores_unprintable_reason_objects_without_calling_them() -> None:
    class Unprintable:
        calls = 0

        def __str__(self):
            type(self).calls += 1
            raise RuntimeError("no string")

        def __repr__(self):
            type(self).calls += 1
            raise RuntimeError("no repr")

    report = saxs_stability_report(
        decision="keep_original",
        complete_contract=False,
    )
    report["preprocess_decision"]["reason_codes"] = [
        Unprintable(),
        " valid_reason ",
    ]
    report["stability_report"]["reason_codes"] = [Unprintable()]
    app = QApplication.instance() or QApplication([])

    dialog = SideTuningReportDialog(report)

    assert Unprintable.calls == 0
    assert "valid_reason" in dialog._preprocess_metrics_label.text()
    dialog.deleteLater()
    app.processEvents()
