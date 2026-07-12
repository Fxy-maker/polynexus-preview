import csv
import importlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent, QSettings, Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QApplication, QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QMessageBox, QSpinBox, QVBoxLayout

from polynexus.gui.main_window import AITuneWorker, AnalysisWorker, MainWindow, JointHubWorker, SideTuningReportDialog, _data_file_dialog_filter
from polynexus.gui.i18n import get_language, set_language, tr
from polynexus.gui.widgets.chart_editor import ChartEditor
from polynexus.core.figure_document import save_generated_figure_document
from polynexus.data.sample_db import SampleDB
from rag.prompt_builder import PromptBuilder


@pytest.fixture(autouse=True)
def _cleanup_qt_widgets_between_tests():
    yield
    app = QApplication.instance()
    if app is None:
        return
    for widget in QApplication.topLevelWidgets():
        widget.close()
        widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()


def _config_widget(window, key):
    for row in range(window._config_form.rowCount()):
        item = window._config_form.itemAt(row, QFormLayout.FieldRole)
        if item is None:
            item = window._config_form.itemAt(row, QFormLayout.SpanningRole)
        widget = item.widget() if item is not None else None
        if widget is not None and widget.property("config_key") == key:
            return widget
    raise AssertionError(f"Missing config widget: {key}")


def _config_label_for_field(window, field_widget):
    label = window._config_form.labelForField(field_widget)
    if label is None:
        raise AssertionError("Missing form label")
    return label.text()


def _config_hint_widget(window, hint_key):
    for row in range(window._config_form.rowCount()):
        item = window._config_form.itemAt(row, QFormLayout.SpanningRole)
        widget = item.widget() if item is not None else None
        if widget is not None and widget.property("config_hint_key") == hint_key:
            return widget
    raise AssertionError(f"Missing config hint widget: {hint_key}")


def _table_headers(table):
    return [table.horizontalHeaderItem(index).text() for index in range(table.columnCount())]


def test_persist_analysis_run_reuses_existing_sample_and_batch(tmp_path):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "pa6_run.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    window = MainWindow()
    window._sample_db = SampleDB(tmp_path / "samples.db")
    window._current_filepath = str(data_file)
    window._current_technique = "saxs"
    window._current_submodule_id = "saxs.static"
    window._output_dir = str(tmp_path / "output")
    window._project_label.setText("PA6")

    result = {
        "technique": "saxs",
        "metadata": {"polymer_name": "PA6"},
        "parameters": {"L_nm": 12.0},
    }

    window._persist_analysis_run(result)
    window._persist_analysis_run(result)

    assert window._last_persisted_run_id

    db = window._ensure_sample_db()
    samples = db.list_samples(limit=100)

    assert len(samples) == 1

    sample_id = samples[0]["id"]
    batches = db.get_batches(sample_id)

    assert len(batches) == 1


def test_persist_analysis_run_stores_analysis_evidence(tmp_path):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "pa6_run.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    window = MainWindow()
    window._sample_db = SampleDB(tmp_path / "samples.db")
    window._current_filepath = str(data_file)
    window._current_technique = "saxs"
    window._current_submodule_id = "saxs.static"
    window._output_dir = str(tmp_path / "output")
    window._project_label.setText("PA6")
    evidence = {
        "technique": "SAXS",
        "constraint_summary": {"status": "soft_warn"},
        "structure_evidence": {"lc_reliability_status": "diagnostic_only"},
    }

    result = {
        "technique": "saxs",
        "metadata": {"polymer_name": "PA6"},
        "parameters": {"L_nm": 12.0},
        "analysis_evidence": evidence,
    }

    window._persist_analysis_run(result)

    db = window._ensure_sample_db()
    sample_id = db.list_samples(limit=10)[0]["id"]
    batch_id = db.get_batches(sample_id)[0]["id"]
    run = db.get_analysis_runs(batch_id)[0]

    assert run["analysis_evidence"] == evidence

    db.close()
    window.deleteLater()
    app.processEvents()


def test_populate_plots_ignores_historical_variants_without_active_manifest(tmp_path):
    app = QApplication.instance() or QApplication([])

    frame_dir = tmp_path / "per_frame" / "frame_001"
    frame_dir.mkdir(parents=True)

    stale_low = frame_dir / "03_IDF_LOW.pdf"
    refreshed = frame_dir / "03_IDF.pdf"
    stale_low.write_bytes(b"%PDF-1.4 stale")
    refreshed.write_bytes(b"%PDF-1.4 refreshed")
    os.utime(stale_low, (1_700_000_000, 1_700_000_000))
    os.utime(refreshed, (1_700_000_100, 1_700_000_100))

    window = MainWindow()
    window._output_dir = str(tmp_path)
    window._current_figure_path = str(stale_low)
    window._figure_preview.setVisible(True)

    window._populate_plots()
    app.processEvents()

    assert window._current_figure_path == ""
    assert window._chart_gallery.current_file() == ""

    window.deleteLater()
    app.processEvents()


def test_populate_plots_does_not_discover_initial_file_without_active_manifest(tmp_path):
    app = QApplication.instance() or QApplication([])

    figure_dir = tmp_path / "figures"
    figure_dir.mkdir()
    figure_path = figure_dir / "initial.png"
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    window = MainWindow()
    window._output_dir = str(tmp_path)
    window._current_figure_path = ""
    window._figure_preview.setVisible(False)

    window._populate_plots()
    app.processEvents()

    assert window._chart_gallery.current_file() == ""
    assert window._current_figure_path == ""
    assert window._figure_preview.isHidden() is True

    window.deleteLater()
    app.processEvents()


def test_populate_plots_does_not_group_unmanifested_related_exports(tmp_path):
    app = QApplication.instance() or QApplication([])

    figure_dir = tmp_path / "figures"
    figure_dir.mkdir()
    png_path = figure_dir / "temperature_overview.png"
    svg_path = figure_dir / "temperature_overview.svg"
    pdf_path = figure_dir / "temperature_overview.pdf"
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(png_path))
    svg_path.write_text("<svg width='80' height='40'></svg>", encoding="utf-8")
    pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj\n<< /Type /Page /MediaBox [0 0 80 40] >>\nendobj\n")

    save_generated_figure_document(str(svg_path), figure_id="temperature_overview", objects=[])

    window = MainWindow()
    window._output_dir = str(tmp_path)
    window._current_figure_path = str(pdf_path)
    window._figure_preview.setVisible(True)

    window._populate_plots()
    app.processEvents()

    assert window._chart_gallery._thumbnails == []
    assert window._chart_gallery.current_file() == ""
    assert window._current_figure_path == ""

    window.deleteLater()
    app.processEvents()


def test_static_chart_editor_save_does_not_trigger_replot(tmp_path):
    app = QApplication.instance() or QApplication([])

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    window = MainWindow()
    window._current_technique = "saxs"
    window._current_filepath = str(tmp_path / "input.csv")
    window._output_dir = str(tmp_path / "output")
    window._engine_cache["saxs"] = object()
    window._current_figure_path = str(figure_path)
    window._chart_gallery.load_files([str(figure_path)])
    window._chart_gallery.select_figure(str(figure_path), emit=False)

    replot_calls = []
    window._replot = lambda: replot_calls.append(True)

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor.figure_saved.connect(window._on_chart_editor_saved)
    editor.figure_saved.emit(str(figure_path))

    assert replot_calls == []
    assert window._current_figure_path == str(figure_path)
    assert window._chart_gallery.current_file() == str(figure_path)

    editor.deleteLater()
    window.deleteLater()
    app.processEvents()


def test_chart_editor_save_as_adds_new_figure_to_gallery(tmp_path):
    app = QApplication.instance() or QApplication([])

    figure_dir = tmp_path / "figures"
    figure_dir.mkdir()
    source_path = figure_dir / "source.png"
    copy_path = figure_dir / "source_edited.png"
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(source_path))
    pixmap.fill(QColor("yellow"))
    assert pixmap.save(str(copy_path))

    window = MainWindow()
    window._current_technique = "saxs"
    window._current_filepath = str(tmp_path / "input.csv")
    window._output_dir = str(tmp_path / "output")
    window._current_figure_path = str(source_path)
    window._chart_gallery.load_files([str(source_path)])
    window._chart_gallery.select_figure(str(source_path), emit=False)

    editor = ChartEditor()
    editor.set_source_figure(str(source_path))
    editor.figure_saved.connect(window._on_chart_editor_saved)
    editor.figure_saved.emit(str(copy_path))

    assert str(copy_path) in window._chart_gallery.figure_paths()
    assert window._chart_gallery.current_file() == str(copy_path)
    assert window._current_figure_path == str(copy_path)

    editor.deleteLater()
    window.deleteLater()
    app.processEvents()


def test_open_selected_chart_editor_routes_gallery_entry_context(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    figure_path = tmp_path / "summary" / "Fig_1_overview.svg"
    figure_path.parent.mkdir(parents=True)
    figure_path.write_text("<svg width='80' height='40'></svg>", encoding="utf-8")

    entry = SimpleNamespace(
        figure_id="Fig_1_overview",
        title="Series Overview",
        preview_path=str(figure_path),
        primary_path=str(figure_path),
        editable_path=str(figure_path),
        category="series_overview",
        state="object_editing",
    )

    captured = {}

    def _fake_open_chart_editor(figure_path, **kwargs):
        captured["figure_path"] = figure_path
        captured["kwargs"] = kwargs
        return SimpleNamespace()

    monkeypatch.setattr(
        "polynexus.gui.main_window_figure_mixin.open_chart_editor",
        _fake_open_chart_editor,
    )

    window = MainWindow()
    window._current_figure_path = ""
    window._chart_gallery = SimpleNamespace(current_entry=lambda: entry)

    window._open_selected_chart_editor()

    assert captured["figure_path"] == str(figure_path)
    assert captured["kwargs"]["entry"] is entry

    window.deleteLater()
    app.processEvents()


def test_populate_plots_ignores_result_paths_and_unmanifested_categories(tmp_path):
    app = QApplication.instance() or QApplication([])

    summary_dir = tmp_path / "summary"
    per_frame_dir = tmp_path / "per_frame" / "T170C"
    summary_dir.mkdir(parents=True)
    per_frame_dir.mkdir(parents=True)

    overview_path = summary_dir / "Fig_1_overview.png"
    frame_path = per_frame_dir / "01_scattering.png"
    root_path = tmp_path / "temperature_overview.png"

    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(overview_path))
    assert pixmap.save(str(frame_path))
    assert pixmap.save(str(root_path))

    window = MainWindow()
    window._current_technique = "saxs"
    window._output_dir = str(tmp_path)
    window._results["saxs"] = {
        "figures": {
            "temperature_overview": str(root_path),
        }
    }

    window._populate_plots()
    app.processEvents()

    assert window._chart_gallery._all_entries == []
    assert window._chart_gallery._thumbnails == []
    assert window._current_figure_path == ""

    window.deleteLater()
    app.processEvents()


def test_persist_analysis_run_marks_ai_tuned_rerun(tmp_path):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "pa6_run.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    window = MainWindow()
    window._sample_db = SampleDB(tmp_path / "samples.db")
    window._current_filepath = str(data_file)
    window._current_technique = "saxs"
    window._current_submodule_id = "saxs.static"
    window._output_dir = str(tmp_path / "output")
    window._project_label.setText("PA6")
    window._last_ai_tuned_run = True

    result = {
        "technique": "saxs",
        "metadata": {"polymer_name": "PA6"},
        "parameters": {"L_nm": 12.0},
    }

    window._persist_analysis_run(result)

    db = window._ensure_sample_db()
    sample_id = db.list_samples(limit=10)[0]["id"]
    batch_id = db.get_batches(sample_id)[0]["id"]
    run = db.get_analysis_runs(batch_id)[0]

    assert run["ai_tuned"] == 1
    assert run["results_summary"]["ai_tuned"] is True
    assert run["results_summary"]["result_origin"] == "controlled_optimization_rerun"

    db.close()
    window.deleteLater()
    app.processEvents()


def test_persist_analysis_run_marks_confirmed_result(tmp_path):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "pa6_run.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    window = MainWindow()
    window._sample_db = SampleDB(tmp_path / "samples.db")
    window._current_filepath = str(data_file)
    window._current_technique = "saxs"
    window._current_submodule_id = "saxs.static"
    window._output_dir = str(tmp_path / "output")
    window._project_label.setText("PA6")
    window._current_result_confirmed_flag = True

    result = {
        "technique": "saxs",
        "metadata": {"polymer_name": "PA6"},
        "parameters": {"L_nm": 12.0},
    }

    window._persist_analysis_run(result)

    db = window._ensure_sample_db()
    sample_id = db.list_samples(limit=10)[0]["id"]
    batch_id = db.get_batches(sample_id)[0]["id"]
    run = db.get_analysis_runs(batch_id)[0]

    assert run["confirmed"] == 1
    assert run["results_summary"]["confirmed"] is True

    db.close()
    window.deleteLater()
    app.processEvents()


def test_persist_analysis_run_stores_history_context_snapshot(tmp_path):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "pa6_run.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    window = MainWindow()
    window._sample_db = SampleDB(tmp_path / "samples.db")
    window._current_filepath = str(data_file)
    window._current_technique = "saxs"
    window._current_submodule_id = "saxs.static"
    window._output_dir = str(tmp_path / "output")
    window._project_label.setText("PA6")
    window._current_result_confirmed_flag = True
    window._last_ai_tuned_run = True
    window._results["saxs"] = {
        "dummy": True,
        "results_summary": {
            "project_label": "PA6",
            "confirmed": True,
            "result_origin": "controlled_optimization_rerun",
            "ai_tuned": True,
        },
    }
    window._last_ai_tuning_context = {
        "summary": "Previous round summary: accepted 3 rounds",
        "accepted_summary": "accepted 3 rounds",
        "benchmark_text": "Benchmark: objective delta +0.018, accept 50.0%, rollback 50.0%, constraint hit 33.3%, symptom hit 75.0%.",
        "stop_reason": "quality guard reached",
        "remaining_risks": "low-q coverage limited",
        "next_goal": "keep q_bragg_min stable",
    }

    result = {
        "technique": "saxs",
        "metadata": {"polymer_name": "PA6"},
        "parameters": {"L_nm": 12.0},
    }

    window._persist_analysis_run(result)

    db = window._ensure_sample_db()
    sample_id = db.list_samples(limit=10)[0]["id"]
    batch_id = db.get_batches(sample_id)[0]["id"]
    run = db.get_analysis_runs(batch_id)[0]

    history_context = run["results_summary"]["history_context"]
    assert isinstance(history_context, dict)
    assert history_context["review_summary"]
    assert "Benchmark: objective delta +0.018" in history_context["benchmark_text"]
    assert ("Current result:" in history_context["work_memory_summary"]) or ("当前结果" in history_context["work_memory_summary"])
    assert history_context["tuning_context"]["benchmark_text"].startswith("Benchmark: objective delta +0.018")
    assert "Boundary" in history_context["responsibility_boundary"]

    db.close()
    window.deleteLater()
    app.processEvents()


def test_persist_analysis_run_does_not_merge_same_stem_from_different_files(tmp_path):
    app = QApplication.instance() or QApplication([])

    first_dir = tmp_path / "run_a"
    second_dir = tmp_path / "run_b"
    first_dir.mkdir()
    second_dir.mkdir()
    first_file = first_dir / "shared.csv"
    second_file = second_dir / "shared.csv"
    first_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")
    second_file.write_text("q,I\n0.2,2.0\n", encoding="utf-8")

    window = MainWindow()
    window._sample_db = SampleDB(tmp_path / "samples.db")
    window._current_technique = "saxs"
    window._current_submodule_id = "saxs.static"
    window._output_dir = str(tmp_path / "output")
    window._project_label.setText("PA6")

    result = {
        "technique": "saxs",
        "metadata": {"polymer_name": "PA6"},
        "parameters": {"L_nm": 12.0},
    }

    window._current_filepath = str(first_file)
    window._persist_analysis_run(result)

    window._current_filepath = str(second_file)
    window._persist_analysis_run(result)

    db = window._ensure_sample_db()
    sample_id = db.list_samples(limit=10)[0]["id"]
    batches = db.get_batches(sample_id)

    assert len(batches) == 2
    stored_paths = {
        db.get_data_files(batch["id"])[0]["file_path"]
        for batch in batches
    }
    assert stored_paths == {str(first_file.resolve()), str(second_file.resolve())}

    db.close()
    window.deleteLater()
    app.processEvents()


def test_history_confirmation_button_updates_record_state(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "history.csv"
        data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

        window = MainWindow()
        window._sample_db = SampleDB(tmp_path / "samples.db")
        db = window._ensure_sample_db()

        sample_id = db.create_sample("PA6")
        batch_id = db.create_batch(
            sample_id,
            "annealed-01",
            instrument="SAXS",
            condition_type="analysis",
            condition_values={"technique": "saxs"},
        )
        db.add_data_file(
            batch_id,
            str(data_file.resolve()),
            "saxs",
            file_type="csv",
            import_order=0,
        )
        db.create_analysis_run(
            batch_id,
            "saxs",
            submodule="saxs.static",
            parameters={"baseline_method": "subtract"},
            results_summary={"data_file": str(data_file.resolve())},
            output_dir=str(tmp_path / "output_b"),
        )

        window._refresh_history()
        window._history_table.selectRow(0)
        window._on_history_confirm_requested()

        run = db.get_analysis_runs(batch_id)[0]
        assert run["confirmed"] == 1
        assert run["results_summary"]["confirmed"] is True
        assert window._history_confirm_btn.text() == "Clear confirmation"
        assert "Marked as confirmed result" in window._log_panel.toPlainText()

        window._on_history_confirm_requested()
        run = db.get_analysis_runs(batch_id)[0]
        assert run["confirmed"] == 0
        assert run["results_summary"]["confirmed"] is False
        assert window._history_confirm_btn.text() == "Confirm result"

        db.close()
        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_current_result_confirmation_toggles_state(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_technique = "saxs"
        window._current_submodule_id = "saxs.static"
        window._current_filepath = str(tmp_path / "input.csv")
        window._results["saxs"] = {
            "parameters": {"L_nm": 11.2},
            "results_summary": {"project_label": "PA6"},
        }

        window._toggle_current_result_confirmation()
        assert window._current_result_confirmed_flag is True
        assert window._results_confirm_status.text() == "Confirmed"
        assert window._results_confirm_btn.text() == "Clear confirmation"

        window._toggle_current_result_confirmation()
        assert window._current_result_confirmed_flag is False
        assert window._results_confirm_status.text() == "Not confirmed"
        assert window._results_confirm_btn.text() == "Confirm result"

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_current_results_record_carries_validation_context(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        tmp_path.mkdir(parents=True, exist_ok=True)
        data_file = tmp_path / "current.csv"
        data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

        window = MainWindow()
        window._current_technique = "saxs"
        window._current_submodule_id = "saxs.static"
        window._current_filepath = str(data_file)
        window._output_dir = str(tmp_path / "output")
        window._project_label.setText("PA6")
        window._current_result_confirmed_flag = True
        window._results["saxs"] = {
            "parameters": {"L_nm": 12.0},
            "validation_passed": False,
            "validation_summary": "WARN: synthetic drift",
            "validation_warnings": ["scan1/Tg", "scan1/DHm"],
            "quality_flags": {"scan1/Tg": "WARN"},
            "results_summary": {"project_label": "PA6"},
        }

        record = window._current_results_record()
        context = window._export_context_payload(report_path=str(tmp_path / "report.html"))

        assert record["validation_passed"] is False
        assert record["validation_summary"] == "WARN: synthetic drift"
        assert record["validation_warnings"] == ["scan1/Tg", "scan1/DHm"]
        assert record["quality_flags"] == {"scan1/Tg": "WARN"}
        assert record["results_summary"]["validation_summary"] == "WARN: synthetic drift"
        assert record["results_summary"]["validation_warnings"] == ["scan1/Tg", "scan1/DHm"]
        assert record["results_summary"]["validation_passed"] is False
        assert context["validation_summary"] == "WARN: synthetic drift | scan1/Tg, scan1/DHm"

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_sample_batch_analysis_request_loads_workspace_context(tmp_path):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "pa6_run.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    window = MainWindow()
    window._sample_db = SampleDB(tmp_path / "samples.db")
    db = window._ensure_sample_db()

    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(
        sample_id,
        "annealed-01",
        instrument="SAXS",
        condition_type="raw_data",
        condition_values={"technique": "saxs"},
    )
    db.add_data_file(
        batch_id,
        str(data_file.resolve()),
        "saxs",
        file_type="csv",
        import_order=0,
    )
    db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        output_dir=str(output_dir),
        results_summary={"L_nm": 12.0},
    )

    window._on_sample_batch_analysis_requested(batch_id)

    assert window._current_technique == "saxs"
    assert window._current_submodule_id == "saxs.static"
    assert window._current_filepath == str(data_file.resolve())
    assert window._output_dir == str(output_dir)
    assert window._path_input.text() == str(data_file.resolve())

    db.close()
    window.deleteLater()
    app.processEvents()


def test_build_run_config_includes_sample_batch_condition_context(tmp_path):
    app = QApplication.instance() or QApplication([])

    window = MainWindow()
    window._current_technique = "saxs"
    window._current_submodule_id = "saxs.temperature"
    window._current_filepath = str(tmp_path / "Check-20260618_0_00002.edf")
    window._current_input_mode = "sequence"
    window._current_sample_id = "sample-1"
    window._current_batch_id = "batch-1"
    window._current_sample_name = "PA6"
    window._current_batch_label = "temp-series"
    window._sample_db = SampleDB(tmp_path / "samples.db")
    db = window._ensure_sample_db()

    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(
        sample_id,
        "temp-series",
        instrument="SAXS",
        condition_type="analysis",
        condition_values={
            "technique": "saxs",
            "temperature": -20,
            "sample_id": sample_id,
        },
    )
    db.update_batch(
        batch_id,
        condition_values={
            "technique": "saxs",
            "temperature": -20,
            "sample_id": sample_id,
            "batch_id": batch_id,
            "sample_name": "PA6",
            "batch_label": "temp-series",
        },
    )
    window._current_sample_id = sample_id
    window._current_batch_id = batch_id
    window._current_sample_name = "PA6"
    window._current_batch_label = "temp-series"

    config = window._build_run_config()

    assert config is not None
    assert config.condition_context["sample_id"] == sample_id
    assert config.condition_context["batch_id"] == batch_id
    assert config.condition_context["sample_name"] == "PA6"
    assert config.condition_context["batch_label"] == "temp-series"
    assert config.condition_context["condition_values"]["temperature"] == -20
    assert config.condition_context["batch"]["condition_values"]["temperature"] == -20

    db.close()
    window.deleteLater()
    app.processEvents()


def test_persist_analysis_run_prefers_current_sample_context(tmp_path):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "temp-series.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    window = MainWindow()
    window._sample_db = SampleDB(tmp_path / "samples.db")
    db = window._ensure_sample_db()

    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(
        sample_id,
        "temp-series",
        instrument="SAXS",
        condition_type="analysis",
        condition_values={"technique": "saxs", "temperature": -20},
    )

    window._current_filepath = str(data_file)
    window._current_technique = "saxs"
    window._current_submodule_id = "saxs.temperature"
    window._current_sample_id = sample_id
    window._current_batch_id = batch_id
    window._current_sample_name = "PA6"
    window._current_batch_label = "temp-series"
    window._output_dir = str(tmp_path / "output")
    window._project_label.setText("Different title")

    result = {
        "technique": "saxs",
        "metadata": {"polymer_name": "Should be replaced"},
        "parameters": {"L_nm": 12.0},
    }

    window._persist_analysis_run(result)

    stored_sample = db.get_sample(sample_id)
    assert stored_sample is not None
    batches = db.get_batches(sample_id)
    assert len(batches) == 1
    runs = db.get_analysis_runs(batch_id)
    assert len(runs) == 1
    assert runs[0]["results_summary"]["sample_name"] == "PA6"
    assert runs[0]["results_summary"]["batch_label"] == "temp-series"

    db.close()
    window.deleteLater()
    app.processEvents()


def test_config_preset_round_trip_restores_submodule_values(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    window = MainWindow()
    window._on_technique_selected("saxs")
    window._on_submodule_selected("saxs", "saxs.static")

    baseline = _config_widget(window, "baseline_method")
    smooth_window = _config_widget(window, "smooth_window")
    q_range_min = _config_widget(window, "q_range_min")
    wavelength = _config_widget(window, "wavelength_m")
    sdd = _config_widget(window, "sdd_m")

    assert isinstance(baseline, QComboBox)
    assert isinstance(smooth_window, QSpinBox)
    assert isinstance(q_range_min, QDoubleSpinBox)
    assert isinstance(wavelength, QDoubleSpinBox)
    assert isinstance(sdd, QDoubleSpinBox)

    baseline.setCurrentText("subtract")
    smooth_window.setValue(11)
    q_range_min.setValue(0.1234)
    wavelength.setValue(1.23e-10)
    sdd.setValue(0.789)

    window._config_preset_combo.setEditText("Static Lab")
    window._on_save_config_preset()

    baseline.setCurrentText("none")
    smooth_window.setValue(5)
    q_range_min.setValue(0.5)
    wavelength.setValue(2.000e-10)
    sdd.setValue(0.450)

    window._config_preset_combo.setEditText("Static Lab")
    window._on_load_config_preset()

    assert baseline.currentText() == "subtract"
    assert smooth_window.value() == 11
    assert q_range_min.value() == 0.1234
    assert wavelength.value() == 1.23e-10
    assert sdd.value() == 0.789

    window_reopened = MainWindow()
    window_reopened._on_technique_selected("saxs")
    window_reopened._on_submodule_selected("saxs", "saxs.static")

    reopened_wavelength = _config_widget(window_reopened, "wavelength_m")
    reopened_sdd = _config_widget(window_reopened, "sdd_m")

    preset_names = [
        window_reopened._config_preset_combo.itemText(i)
        for i in range(window_reopened._config_preset_combo.count())
    ]
    assert "Static Lab" in preset_names
    assert isinstance(reopened_wavelength, QDoubleSpinBox)
    assert isinstance(reopened_sdd, QDoubleSpinBox)

    window.deleteLater()
    window_reopened.deleteLater()
    app.processEvents()


def test_dsc_dhm0_tooltip_uses_translation():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._on_technique_selected("dsc")

        dhm0 = window._dsc_dhm0_input
        assert isinstance(dhm0, QDoubleSpinBox)
        assert dhm0.toolTip() == tr("DSC_DHM0_TOOLTIP")

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_build_run_config_includes_saxs_calibration_fields():
    app = QApplication.instance() or QApplication([])

    window = MainWindow()
    window._current_technique = "saxs"
    window._on_submodule_selected("saxs", "saxs.static")

    wavelength = _config_widget(window, "wavelength_m")
    crystallinity = _config_widget(window, "crystallinity")
    expected_melt = _config_widget(window, "T_melt_expected")
    pixel_size = _config_widget(window, "pixel_size_m")
    sdd = _config_widget(window, "sdd_m")
    beam_center_x = _config_widget(window, "beam_center_x")
    beam_center_y = _config_widget(window, "beam_center_y")
    poni_file = _config_widget(window, "poni_file")

    wavelength.setValue(1.23e-10)
    crystallinity.setText("0.35")
    expected_melt.setText("220.0")
    pixel_size.setValue(88e-6)
    sdd.setValue(0.6789)
    beam_center_x.setValue(321.0)
    beam_center_y.setValue(654.0)
    poni_file.setText("C:/lab/test.poni")

    config = window._build_run_config()

    assert config is not None
    assert config.wavelength_m == 1.23e-10
    assert config.crystallinity == 0.35
    assert config.T_melt_expected == 220.0
    assert config.pixel_size_m == 88e-6
    assert config.sdd_m == 0.6789
    assert config.beam_center_x == 321.0
    assert config.beam_center_y == 654.0
    assert config.poni_file == "C:/lab/test.poni"

    window.deleteLater()
    app.processEvents()


def test_build_run_config_includes_saxs_mask_fields():
    app = QApplication.instance() or QApplication([])

    window = MainWindow()
    window._current_technique = "saxs"
    window._on_submodule_selected("saxs", "saxs.static")

    auto_detect = _config_widget(window, "auto_detect_beamstop")
    threshold = _config_widget(window, "beamstop_pollution_threshold")
    dummy_val = _config_widget(window, "dummy_val")
    ddummy = _config_widget(window, "ddummy")

    auto_detect.setChecked(False)
    threshold.setValue(42.5)
    dummy_val.setValue(-3.2)
    ddummy.setValue(1.1)

    config = window._build_run_config()

    assert config is not None
    assert config.auto_detect_beamstop is False
    assert config.beamstop_pollution_threshold == 42.5
    assert config.dummy_val == -3.2
    assert config.ddummy == 1.1

    window.deleteLater()
    app.processEvents()


def test_build_run_config_includes_waxs_calibration_fields():
    app = QApplication.instance() or QApplication([])

    window = MainWindow()
    window._current_technique = "waxs"
    window._on_submodule_selected("waxs", "waxs.static")

    wavelength = _config_widget(window, "wavelength_A")
    two_theta_offset = _config_widget(window, "two_theta_offset")

    wavelength.setValue(0.7107)
    two_theta_offset.setValue(0.1234)

    config = window._build_run_config()

    assert config is not None
    assert config.wavelength_A == 0.7107
    assert config.two_theta_offset == 0.1234

    window.deleteLater()
    app.processEvents()


def test_saxs_calibration_hint_uses_translation():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_technique = "saxs"
        window._on_submodule_selected("saxs", "saxs.static")

        hint = _config_hint_widget(window, "saxs_calibration")

        assert hint.text() == tr("CONFIG_CALIBRATION_HINT_SAXS")

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_saxs_mask_hint_uses_translation():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_technique = "saxs"
        window._on_submodule_selected("saxs", "saxs.static")

        hint = _config_hint_widget(window, "saxs_mask")

        assert hint.text() == tr("CONFIG_MASK_HINT_SAXS")

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_saxs_mask_summary_updates_with_current_values():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_technique = "saxs"
        window._on_submodule_selected("saxs", "saxs.static")

        summary = _config_hint_widget(window, "saxs_mask_summary")
        auto_detect = _config_widget(window, "auto_detect_beamstop")
        threshold = _config_widget(window, "beamstop_pollution_threshold")
        dummy_val = _config_widget(window, "dummy_val")
        ddummy = _config_widget(window, "ddummy")

        assert summary.text() == tr(
            "CONFIG_MASK_SUMMARY_SAXS",
            tr("COMMON_ON"),
            "100.0",
            "-1.500",
            "0.600",
        )

        auto_detect.setChecked(False)
        threshold.setValue(42.5)
        dummy_val.setValue(-3.2)
        ddummy.setValue(1.1)
        app.processEvents()

        assert summary.text() == tr(
            "CONFIG_MASK_SUMMARY_SAXS",
            tr("COMMON_OFF"),
            "42.5",
            "-3.200",
            "1.100",
        )

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_waxs_mask_hint_uses_translation():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_technique = "waxs"
        window._on_submodule_selected("waxs", "waxs.static")

        hint = _config_hint_widget(window, "waxs_mask")

        assert hint.text() == tr("CONFIG_MASK_HINT_WAXS")

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_run_analysis_warns_when_saxs_poni_file_missing(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "sample.dat"
        data_file.write_text("q I\n0.1 1.0\n", encoding="utf-8")

        window = MainWindow()
        window._current_technique = "saxs"
        window._on_submodule_selected("saxs", "saxs.static")
        window._current_filepath = str(data_file)

        poni_file = _config_widget(window, "poni_file")
        poni_file.setText(str(tmp_path / "missing.poni"))

        run_single_called = {"value": False}

        def fake_run_single():
            run_single_called["value"] = True

        window._run_single = fake_run_single

        with patch("polynexus.gui.main_window.QMessageBox.warning") as warning:
            window._run_analysis()

        warning.assert_called_once_with(
            window,
            tr("CALIBRATION_PONI_MISSING_TITLE"),
            tr("CALIBRATION_PONI_MISSING_DETAIL", str(tmp_path / "missing.poni")),
        )
        assert run_single_called["value"] is False
        assert window._btn_run.isEnabled() is True

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_run_analysis_warns_when_saxs_beamstop_threshold_too_low(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "sample.dat"
        data_file.write_text("q I\n0.1 1.0\n", encoding="utf-8")

        window = MainWindow()
        window._current_technique = "saxs"
        window._on_submodule_selected("saxs", "saxs.static")
        window._current_filepath = str(data_file)

        threshold = _config_widget(window, "beamstop_pollution_threshold")
        threshold.setValue(10.0)

        run_single_called = {"value": False}

        def fake_run_single():
            run_single_called["value"] = True

        window._run_single = fake_run_single

        with patch("polynexus.gui.main_window.QMessageBox.warning") as warning:
            window._run_analysis()

        warning.assert_called_once_with(
            window,
            tr("MASK_CONFIG_WARNING_TITLE"),
            tr("MASK_BEAMSTOP_THRESHOLD_TOO_LOW", "10.0"),
        )
        assert run_single_called["value"] is False

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_run_single_logs_single_file_mode(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "sample.dat"
        data_file.write_text("q I\n0.1 1.0\n", encoding="utf-8")

        window = MainWindow()
        window._current_technique = "saxs"
        window._current_filepath = str(data_file)

        with patch("polynexus.gui.main_window.get_engine", return_value=None):
            with patch("polynexus.gui.main_window.AnalysisWorker") as worker_cls:
                worker = worker_cls.return_value
                worker.log_msg = type("SignalStub", (), {"connect": lambda self, fn: None})()
                worker.finished = type("SignalStub", (), {"connect": lambda self, fn: None})()
                worker.error_msg = type("SignalStub", (), {"connect": lambda self, fn: None})()
                worker.start = lambda: None
                window._run_single()

        assert window._log_panel.toPlainText().splitlines()[-1].endswith("Starting single-file analysis: sample.dat")

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_run_batch_logs_native_directory_sequence_mode(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_dir = tmp_path / "ir_temp"
        data_dir.mkdir()

        window = MainWindow()
        window._current_technique = "ir"
        window._current_submodule_id = "ir.temperature_2d"
        window._current_filepath = str(data_dir)
        window._current_input_mode = "sequence"

        with patch("polynexus.gui.main_window.AnalysisWorker") as worker_cls:
            worker = worker_cls.return_value
            worker.log_msg = type("SignalStub", (), {"connect": lambda self, fn: None})()
            worker.finished = type("SignalStub", (), {"connect": lambda self, fn: None})()
            worker.error_msg = type("SignalStub", (), {"connect": lambda self, fn: None})()
            worker.start = lambda: None
            window._run_batch()

        assert window._log_panel.toPlainText().splitlines()[-1].endswith("Starting Sequence run: ir_temp")

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_run_batch_logs_standard_batch_mode(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_dir = tmp_path / "generic_batch"
        data_dir.mkdir()
        (data_dir / "a.csv").write_text("q,I\n0.1,1.0\n", encoding="utf-8")
        (data_dir / "b.csv").write_text("q,I\n0.2,2.0\n", encoding="utf-8")

        window = MainWindow()
        window._current_technique = "ir"
        window._current_filepath = str(data_dir)
        window._current_input_mode = "directory"

        with patch("polynexus.gui.main_window.BatchWorker") as worker_cls:
            worker = worker_cls.return_value
            worker.log_msg = type("SignalStub", (), {"connect": lambda self, fn: None})()
            worker.progress = type("SignalStub", (), {"connect": lambda self, fn: None})()
            worker.file_done = type("SignalStub", (), {"connect": lambda self, fn: None})()
            worker.batch_finished = type("SignalStub", (), {"connect": lambda self, fn: None})()
            worker.error_msg = type("SignalStub", (), {"connect": lambda self, fn: None})()
            worker.start = lambda: None
            window._run_batch()

        assert window._log_panel.toPlainText().splitlines()[-1].endswith("Starting batch processing: 2 files @ generic_batch")

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_run_analysis_warns_when_saxs_ddummy_too_large(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "sample.dat"
        data_file.write_text("q I\n0.1 1.0\n", encoding="utf-8")

        window = MainWindow()
        window._current_technique = "saxs"
        window._on_submodule_selected("saxs", "saxs.static")
        window._current_filepath = str(data_file)

        ddummy = _config_widget(window, "ddummy")
        ddummy.setValue(6.5)

        run_single_called = {"value": False}

        def fake_run_single():
            run_single_called["value"] = True

        window._run_single = fake_run_single

        with patch("polynexus.gui.main_window.QMessageBox.warning") as warning:
            window._run_analysis()

        warning.assert_called_once_with(
            window,
            tr("MASK_CONFIG_WARNING_TITLE"),
            tr("MASK_DDUMMY_TOO_LARGE", "6.500"),
        )
        assert run_single_called["value"] is False

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_recent_calibration_button_uses_translation():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        assert window._btn_config_recent_calibration_save.text() == tr("CONFIG_RECENT_CALIBRATION_SAVE")
        assert window._btn_config_recent_calibration.text() == tr("CONFIG_RECENT_CALIBRATION_APPLY")

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_recent_projects_item_activation_opens_path(tmp_path):
    app = QApplication.instance() or QApplication([])

    window = MainWindow()
    path = tmp_path / "project.poly"
    path.write_text("demo", encoding="utf-8")
    window._recent_projects = [str(path)]
    window._refresh_recent_list()

    opened = []
    window._set_input_path = lambda current_path, is_dir=False, input_mode="": opened.append((current_path, is_dir, input_mode))
    window.log = lambda message: opened.append(("log", message))

    item = window._recent_list.item(0)
    window._recent_list.itemActivated.emit(item)

    assert opened[0] == (str(path), False, "")
    assert opened[1][0] == "log"

    window.deleteLater()
    app.processEvents()


def test_recent_projects_copy_button_copies_selected_path(tmp_path):
    app = QApplication.instance() or QApplication([])

    window = MainWindow()
    path = tmp_path / "project.poly"
    path.write_text("demo", encoding="utf-8")
    window._recent_projects = [str(path)]
    window._refresh_recent_list()

    item = window._recent_list.item(0)
    item.setSelected(True)
    app.processEvents()
    assert window._recent_list_copy_button.isEnabled()
    window._recent_list_copy_button.click()

    assert QApplication.clipboard().text().splitlines() == [str(path)]

    window.deleteLater()
    app.processEvents()


def test_running_batch_list_copy_button_copies_selected_item():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()

        window._batch_list.setVisible(True)
        window._batch_list.addItem("file_a.csv")
        window._batch_list.addItem("file_b.csv")
        window._batch_list.setCurrentRow(1)
        window._batch_list.item(1).setSelected(True)
        app.processEvents()
        window._batch_list_copy_shortcut.activated.emit()

        assert QApplication.clipboard().text().splitlines() == ["file_b.csv"]

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_recent_calibration_button_tooltip_tracks_scope_and_availability(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        settings_path = tmp_path / "recent_calibration_tooltip.ini"

        def make_settings(*_args, **_kwargs):
            return QSettings(str(settings_path), QSettings.IniFormat)

        with patch("polynexus.gui.main_window.QSettings", side_effect=make_settings):
            window = MainWindow()

            assert window._btn_config_recent_calibration.toolTip() == tr(
                "CONFIG_RECENT_CALIBRATION_TOOLTIP_DISABLED"
            )
            assert window._btn_config_recent_calibration_save.toolTip() == tr(
                "CONFIG_RECENT_CALIBRATION_TOOLTIP_DISABLED"
            )

            window._current_technique = "saxs"
            window._on_submodule_selected("saxs", "saxs.static")

            assert window._btn_config_recent_calibration.toolTip() == tr(
                "CONFIG_RECENT_CALIBRATION_TOOLTIP_MISSING",
                "SAXS / Static SAXS",
            )
            assert window._btn_config_recent_calibration_save.toolTip() == tr(
                "CONFIG_RECENT_CALIBRATION_SAVE_TOOLTIP",
                "SAXS / Static SAXS",
            )

            window.deleteLater()
            app.processEvents()
    finally:
        set_language(previous)


def test_recent_calibration_round_trip_restores_saxs_values(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        settings_path = tmp_path / "recent_calibration.ini"

        def make_settings(*_args, **_kwargs):
            return QSettings(str(settings_path), QSettings.IniFormat)

        data_file = tmp_path / "sample.dat"
        data_file.write_text("q I\n0.1 1.0\n", encoding="utf-8")
        poni_path = tmp_path / "beamline.poni"
        poni_path.write_text("poni", encoding="utf-8")

        with patch("polynexus.gui.main_window.QSettings", side_effect=make_settings):
            window = MainWindow()
            window._current_technique = "saxs"
            window._on_submodule_selected("saxs", "saxs.static")
            window._current_filepath = str(data_file)

            wavelength = _config_widget(window, "wavelength_m")
            sdd = _config_widget(window, "sdd_m")
            poni_file = _config_widget(window, "poni_file")

            wavelength.setValue(1.23e-10)
            sdd.setValue(0.6789)
            poni_file.setText(str(poni_path))

            run_single_called = {"value": False}

            def fake_run_single():
                run_single_called["value"] = True

            window._run_single = fake_run_single
            window._run_analysis()

            assert run_single_called["value"] is True
            window.deleteLater()
            app.processEvents()

            window_reopened = MainWindow()
            window_reopened._current_technique = "saxs"
            window_reopened._on_submodule_selected("saxs", "saxs.static")

            reopened_wavelength = _config_widget(window_reopened, "wavelength_m")
            reopened_sdd = _config_widget(window_reopened, "sdd_m")
            reopened_poni_file = _config_widget(window_reopened, "poni_file")

            reopened_wavelength.setValue(2.0e-10)
            reopened_sdd.setValue(0.4500)
            reopened_poni_file.setText("")

            window_reopened._on_apply_recent_calibration()

            assert reopened_wavelength.value() == 1.23e-10
            assert reopened_sdd.value() == 0.6789
            assert reopened_poni_file.text() == str(poni_path)

            window_reopened.deleteLater()
            app.processEvents()
    finally:
        set_language(previous)


def test_recent_calibration_round_trip_restores_waxs_values(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        settings_path = tmp_path / "recent_calibration_waxs.ini"

        def make_settings(*_args, **_kwargs):
            return QSettings(str(settings_path), QSettings.IniFormat)

        data_file = tmp_path / "sample.raw"
        data_file.write_text("two_theta intensity\n10 100\n", encoding="utf-8")

        with patch("polynexus.gui.main_window.QSettings", side_effect=make_settings):
            window = MainWindow()
            window._current_technique = "waxs"
            window._on_submodule_selected("waxs", "waxs.static")
            window._current_filepath = str(data_file)

            wavelength = _config_widget(window, "wavelength_A")
            two_theta_offset = _config_widget(window, "two_theta_offset")

            wavelength.setValue(0.7107)
            two_theta_offset.setValue(0.1234)

            run_single_called = {"value": False}

            def fake_run_single():
                run_single_called["value"] = True

            window._run_single = fake_run_single
            window._run_analysis()

            assert run_single_called["value"] is True
            window.deleteLater()
            app.processEvents()

            window_reopened = MainWindow()
            window_reopened._current_technique = "waxs"
            window_reopened._on_submodule_selected("waxs", "waxs.static")

            reopened_wavelength = _config_widget(window_reopened, "wavelength_A")
            reopened_two_theta_offset = _config_widget(window_reopened, "two_theta_offset")

            reopened_wavelength.setValue(1.5406)
            reopened_two_theta_offset.setValue(0.0)

            window_reopened._on_apply_recent_calibration()

            assert reopened_wavelength.value() == 0.7107
            assert reopened_two_theta_offset.value() == 0.1234
            assert window_reopened._btn_config_recent_calibration.toolTip() == tr(
                "CONFIG_RECENT_CALIBRATION_TOOLTIP_READY",
                "WAXS / Static WAXS",
            )

            window_reopened.deleteLater()
            app.processEvents()
    finally:
        set_language(previous)


def test_save_recent_calibration_persists_without_running(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        settings_path = tmp_path / "recent_calibration_save_only.ini"

        def make_settings(*_args, **_kwargs):
            return QSettings(str(settings_path), QSettings.IniFormat)

        with patch("polynexus.gui.main_window.QSettings", side_effect=make_settings):
            window = MainWindow()
            window._current_technique = "saxs"
            window._on_submodule_selected("saxs", "saxs.static")

            wavelength = _config_widget(window, "wavelength_m")
            sdd = _config_widget(window, "sdd_m")
            wavelength.setValue(1.11e-10)
            sdd.setValue(0.4321)

            lines = []
            with patch.object(window, "log", side_effect=lines.append):
                window._on_save_recent_calibration()

            assert lines[-1] == tr("LOG_RECENT_CALIBRATION_SAVED", "SAXS / Static SAXS")

            window_reopened = MainWindow()
            window_reopened._current_technique = "saxs"
            window_reopened._on_submodule_selected("saxs", "saxs.static")
            reopened_wavelength = _config_widget(window_reopened, "wavelength_m")
            reopened_sdd = _config_widget(window_reopened, "sdd_m")
            reopened_wavelength.setValue(2.0e-10)
            reopened_sdd.setValue(0.9)

            window_reopened._on_apply_recent_calibration()

            assert reopened_wavelength.value() == 1.11e-10
            assert reopened_sdd.value() == 0.4321

            window.deleteLater()
            window_reopened.deleteLater()
            app.processEvents()
    finally:
        set_language(previous)


def test_recent_calibration_warns_when_missing(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        settings_path = tmp_path / "recent_calibration_missing.ini"

        def make_settings(*_args, **_kwargs):
            return QSettings(str(settings_path), QSettings.IniFormat)

        with patch("polynexus.gui.main_window.QSettings", side_effect=make_settings):
            window = MainWindow()
            window._current_technique = "waxs"
            window._on_submodule_selected("waxs", "waxs.static")

            with patch("polynexus.gui.main_window.QMessageBox.warning") as warning:
                window._on_apply_recent_calibration()

            warning.assert_called_once_with(
                window,
                tr("CONFIG_RECENT_CALIBRATION_TITLE"),
                tr("CONFIG_RECENT_CALIBRATION_MISSING"),
            )

            window.deleteLater()
            app.processEvents()
    finally:
        set_language(previous)


def test_save_recent_calibration_warns_when_scope_missing():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()

        with patch("polynexus.gui.main_window.QMessageBox.warning") as warning:
            window._on_save_recent_calibration()

        warning.assert_called_once_with(
            window,
            tr("CONFIG_RECENT_CALIBRATION_TITLE"),
            tr("CONFIG_RECENT_CALIBRATION_SCOPE_REQUIRED"),
        )

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_recent_calibration_warns_when_scope_has_no_compatible_fields(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        settings_path = tmp_path / "recent_calibration_incompatible.ini"

        def make_settings(*_args, **_kwargs):
            return QSettings(str(settings_path), QSettings.IniFormat)

        with patch("polynexus.gui.main_window.QSettings", side_effect=make_settings):
            window = MainWindow()
            window._current_technique = "waxs"
            window._on_submodule_selected("waxs", "waxs.static")
            window._settings.setValue(
                window._calibration_settings_key("waxs", "waxs.static"),
                '{"poni_file": "C:/lab/test.poni"}',
            )

            lines = []
            with patch("polynexus.gui.main_window.QMessageBox.warning") as warning:
                with patch.object(window, "log", side_effect=lines.append):
                    window._on_apply_recent_calibration()

            warning.assert_called_once_with(
                window,
                tr("CONFIG_RECENT_CALIBRATION_TITLE"),
                tr("CONFIG_RECENT_CALIBRATION_INCOMPATIBLE"),
            )
            assert lines[-1] == tr(
                "LOG_RECENT_CALIBRATION_INCOMPATIBLE",
                "WAXS / Static WAXS",
            )

            window.deleteLater()
            app.processEvents()
    finally:
        set_language(previous)


def test_manual_config_form_labels_use_translation_keys():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()

        window._on_technique_selected("dsc")
        assert _config_label_for_field(window, window._dsc_dhm0_input) == tr("CONFIG_DSC_HM0")

        window._on_technique_selected("waxs")
        waxs_peak = window._config_form.itemAt(0, QFormLayout.FieldRole).widget()
        assert _config_label_for_field(window, waxs_peak) == tr("CONFIG_WAXS_PEAK_FUNCTION")

        window._on_technique_selected("saxs")
        saxs_integration = window._config_form.itemAt(0, QFormLayout.FieldRole).widget()
        assert _config_label_for_field(window, saxs_integration) == tr("CONFIG_SAXS_INTEGRATION")

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_retranslate_rebuilds_manual_config_form_labels():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._on_technique_selected("dsc")
        assert _config_label_for_field(window, window._dsc_dhm0_input) == "Hm0:"

        set_language("zh")
        window._retranslate_ui()

        assert _config_label_for_field(window, window._dsc_dhm0_input) == tr("CONFIG_DSC_HM0")
        assert window._dsc_dhm0_input.toolTip() == tr("DSC_DHM0_TOOLTIP")

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_retranslate_preserves_loaded_project_label(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "pa66.csv"
        data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

        window = MainWindow()
        window._set_input_path(str(data_file.resolve()))
        assert window._project_label.text() == "pa66.csv"

        set_language("zh")
        window._retranslate_ui()

        assert window._project_label.text() == "pa66.csv"

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_help_dialog_uses_translated_about_text():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()

        with patch("polynexus.gui.main_window.QMessageBox.about") as about:
            window._on_help()

        about.assert_called_once_with(window, tr("ACTION_ABOUT"), tr("ABOUT_TEXT"))

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_data_file_dialog_filter_uses_translation_keys():
    previous = get_language()
    try:
        set_language("en")
        assert _data_file_dialog_filter().startswith("All Supported (")
        assert _data_file_dialog_filter().endswith(";;All Files (*)")
    finally:
        set_language(previous)


def test_ai_tuning_report_headers_use_translation_keys():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        dialog = SideTuningReportDialog({"history": []})

        assert dialog._candidate_table.horizontalHeaderItem(0).text() == tr("AI_TUNING_COL_ACTION")
        assert dialog._candidate_table.horizontalHeaderItem(1).text() == tr("AI_TUNING_COL_STATUS")
        assert dialog._candidate_table.horizontalHeaderItem(2).text() == tr("AI_TUNING_COL_OBJECTIVE_DELTA")
        assert dialog._candidate_table.horizontalHeaderItem(3).text() == tr("AI_TUNING_COL_R2_DELTA")
        assert dialog._candidate_table.horizontalHeaderItem(4).text() == tr("AI_TUNING_COL_NOTE")
        assert dialog._score_table.horizontalHeaderItem(0).text() == tr("AI_TUNING_COL_ROUND")
        assert dialog._score_table.horizontalHeaderItem(1).text() == tr("AI_TUNING_COL_CORE")
        assert dialog._score_table.horizontalHeaderItem(2).text() == tr("AI_TUNING_COL_SUPPORT")
        assert dialog._score_table.horizontalHeaderItem(3).text() == tr("AI_TUNING_COL_R2")
        assert dialog._score_table.horizontalHeaderItem(4).text() == tr("AI_TUNING_COL_EVAL")
        assert dialog._change_table.horizontalHeaderItem(0).text() == tr("AI_TUNING_COL_PARAM")
        assert dialog._change_table.horizontalHeaderItem(1).text() == tr("AI_TUNING_COL_BEFORE")
        assert dialog._change_table.horizontalHeaderItem(2).text() == tr("AI_TUNING_COL_AFTER")
        assert dialog._change_table.horizontalHeaderItem(3).text() == tr("AI_TUNING_COL_REASON")

        dialog.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_ai_tuning_report_candidate_table_copy_shortcut_copies_selected_row():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        dialog = SideTuningReportDialog(
            {
                "history": [
                    {"round_num": 0, "accepted": True, "r_squared_after": 0.88, "eval_score": 0.88},
                    {
                        "round_num": 1,
                        "accepted": True,
                        "r_squared_after": 0.91,
                        "eval_score": 0.94,
                        "decision_summary": "accepted target=peak_window_mismatch objective=0.940",
                        "llm_advice": {
                            "candidate_trials": [
                                {
                                    "action_name": "adjust_peak_window",
                                    "label": "Tighten peak window",
                                    "status": "accepted",
                                    "objective_delta": 0.06,
                                    "r_squared_delta": 0.03,
                                    "decision_summary": "accepted target=peak_window_mismatch objective=0.940",
                                    "expected_evidence_change": "q_peak_diff_pct should shrink",
                                }
                            ]
                        },
                    },
                ]
            }
        )

        dialog._candidate_table.selectRow(0)
        app.processEvents()
        dialog._candidate_copy_shortcut.activated.emit()

        text = QApplication.clipboard().text()
        assert text.splitlines()[0] == (
            f"{tr('AI_TUNING_COL_ACTION')}\t{tr('AI_TUNING_COL_STATUS')}\t"
            f"{tr('AI_TUNING_COL_OBJECTIVE_DELTA')}\t{tr('AI_TUNING_COL_R2_DELTA')}\t{tr('AI_TUNING_COL_NOTE')}"
        )
        assert "Tighten peak window (adjust_peak_window)" in text
        assert tr("AI_TUNING_TRIAL_STATUS_ACCEPTED") in text
        assert "+0.060" in text
        assert "+0.030" in text

        dialog.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_ai_tuning_report_score_table_copy_shortcut_copies_selected_row():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        dialog = SideTuningReportDialog(
            {
                "history": [
                    {
                        "round_num": 3,
                        "r_squared_after": 0.912,
                        "eval_score": "good",
                        "changes": {"alpha": 1.2},
                        "config_snapshot": {"alpha": 1.0},
                    }
                ]
            }
        )

        dialog._score_table.selectRow(0)
        app.processEvents()
        dialog._score_copy_shortcut.activated.emit()

        text = QApplication.clipboard().text()
        assert text.splitlines()[0] == (
            f"{tr('AI_TUNING_COL_ROUND')}\t{tr('AI_TUNING_COL_CORE')}\t"
            f"{tr('AI_TUNING_COL_SUPPORT')}\t{tr('AI_TUNING_COL_R2')}\t"
            f"{tr('AI_TUNING_COL_EVAL')}"
        )
        assert text.splitlines()[1] == (
            f"{tr('AI_TUNING_ROUND_ACCEPTED', 3)}\t{tr('AI_TUNING_EMPTY_VALUE')}\t"
            f"{tr('AI_TUNING_EMPTY_VALUE')}\t0.912\tgood"
        )
        assert len(text.splitlines()) == 2

        dialog.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_ai_tuning_report_change_table_copy_shortcut_copies_selected_row():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        dialog = SideTuningReportDialog(
            {
                "history": [
                    {
                        "round_num": 3,
                        "r_squared_after": 0.912,
                        "eval_score": "good",
                        "changes": {"alpha": 1.2},
                        "config_snapshot": {"alpha": 1.0},
                        "llm_advice": {"reasoning": "increase alpha"},
                    }
                ]
            }
        )

        dialog._change_table.selectRow(0)
        app.processEvents()
        dialog._change_copy_shortcut.activated.emit()

        text = QApplication.clipboard().text()
        assert text.splitlines()[0] == (
            f"{tr('AI_TUNING_COL_PARAM')}\t{tr('AI_TUNING_COL_BEFORE')}\t{tr('AI_TUNING_COL_AFTER')}\t{tr('AI_TUNING_COL_REASON')}"
        )
        assert "alpha\t1.0\t1.2\tincrease alpha" in text
        assert len(text.splitlines()) == 2

        dialog.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_convergence_system_exit_uses_translated_warning():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()

        with patch("polynexus.gui.main_window.QMessageBox.warning") as warning:
            with patch(
                "polynexus.gui.convergence_viewer.ConvergenceViewer",
                side_effect=SystemExit("boom"),
            ):
                window._open_convergence_viewer()

        warning.assert_called_once_with(
            window,
            tr("CONVERGENCE_DASHBOARD"),
            tr("CONVERGENCE_OPEN_FAILED", "boom"),
        )

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_convergence_viewer_uses_review_copy_and_summary_cards():
    from polynexus.gui.convergence_viewer import ConvergenceViewer, TuneRun

    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        assert tr("CONVERGENCE_DASHBOARD") == "Result Review"
        assert tr("REVIEW_VIEWER_TITLE") == "Result Review"
        assert tr("REVIEW_SUMMARY_TITLE") == "Technique summary"
        assert tr("REVIEW_RUNS_TITLE") == "Review records"
        assert tr("REVIEW_CHARTS_TITLE") == "Charts and trends"
        assert tr("REVIEW_SELECTED_CONTEXT") == "Problem summary | {}"
        assert tr("REVIEW_SELECTED_CONTEXT_EMPTY") == "No problem summary is available yet."
        assert tr("REVIEW_SELECTED_TRIALS") == "Tried fixes | {}"
        assert tr("REVIEW_SELECTED_TRIALS_EMPTY") == "No attempted fixes are available yet."
        assert tr("REVIEW_SELECTED_BOUNDARY") == "Evidence boundary | {}"
        assert tr("REVIEW_SELECTED_BOUNDARY_EMPTY") == "No evidence boundary is available yet."
        assert tr("REVIEW_SELECTED_NEXT") == "Current recommendation | {}"
        assert tr("REVIEW_SELECTED_NEXT_EMPTY") == "No current recommendation is available yet."
        assert tr("REVIEW_TABLE_TIME") == "Time"
        assert tr("AI_TUNING_COL_REASON") == "Reason"

        viewer = ConvergenceViewer(db_path="D:/PolyNexus/does-not-exist.db")
        assert viewer._cards_group.title() == tr("REVIEW_SUMMARY_TITLE")
        assert viewer._runs_group.title() == tr("REVIEW_RUNS_TITLE")
        assert viewer._chart_group.title() == tr("REVIEW_CHARTS_TITLE")
        assert viewer._runs_table.horizontalHeaderItem(0).text() == tr("REVIEW_TABLE_TIME")
        viewer._update_selected_detail(
            TuneRun(
                run_id="review-1",
                technique="saxs",
                submodule="saxs.static",
                polymer_name="PA6",
                baseline_r2=0.61,
                best_r2=0.66,
                delta_r2=0.05,
                review_context={
                    "review_summary": "low-q coverage is unstable",
                    "benchmark_text": "attempted q_min lift",
                    "comparison_summary": "candidate improved by 0.02",
                    "responsibility_boundary": "core evidence still needs review",
                    "remaining_risks": "beamstop contamination persists",
                    "tuning_goal_label": "focus low-q window",
                    "next_goal": "rerun with tighter crop",
                },
            )
        )
        assert "Problem summary" in viewer._selected_context.text()
        assert "Tried fixes" in viewer._selected_trials.text()
        assert "Current recommendation" in viewer._selected_next.text()
        assert "Remaining risk" in viewer._selected_risk.text()
        card = viewer._make_card(
            {
                "technique": "saxs",
                "count": 1,
                "avg_baseline_r2": 0.61,
                "avg_best_r2": 0.66,
                "avg_delta_r2": 0.05,
                "submodules": {"saxs.static": 1, "saxs.temperature": 2},
            }
        )

        assert card is not None

        viewer.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_run_single_file_format_warning_uses_translation(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "bad.csv"
        data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

        class CompatibleEngine:
            def check_file_compatibility(self, filepath):
                return True, ""

        window = MainWindow()
        window._current_technique = "saxs"
        window._current_submodule_id = "saxs.static"
        window._current_filepath = str(data_file)

        with patch("polynexus.gui.main_window.get_engine", return_value=CompatibleEngine()):
            with patch("polynexus.gui.main_window.check_file_format", side_effect=ValueError("need .dat")):
                with patch("polynexus.gui.main_window.QMessageBox.warning") as warning:
                    window._run_single()

        warning.assert_called_once_with(
            window,
            tr("FILE_FORMAT_UNSUPPORTED"),
            tr("FILE_FORMAT_UNSUPPORTED_DETAIL", "need .dat"),
        )

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_sidebar_parent_tooltip_and_group_titles_use_translation_keys():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()

        assert window._nav_parent_buttons["saxs"].toolTip() == tr("SIDEBAR_SUBMODULE_COUNT", 3)
        assert window._data_source_group.title() == tr("GROUP_DATA_SOURCE")
        assert window._joint_diagnostics_group.title() == tr("GROUP_JOINT_DIAGNOSTICS")

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_joint_selection_summary_uses_translation_key():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._on_joint_selected("joint.quick")
        window._on_joint_hub_selection_changed(2)

        assert window._workflow_metric_data.text() == tr("WORKFLOW_SELECTED_BATCHES", 2)

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_joint_diagnostics_copy_shortcut_copies_selected_row():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()

        window._update_joint_diagnostics(
            {
                "rows": [{"sample": "PA6"}],
                "validations": [
                    {
                        "severity": "WARN",
                        "sample": "PA6",
                        "batch": "batch-01",
                        "check": "range",
                        "message": "Needs review",
                    }
                ],
            }
        )

        window._joint_diagnostics_table.selectRow(0)
        app.processEvents()
        window._joint_diagnostics_copy_shortcut.activated.emit()

        lines = QApplication.clipboard().text().splitlines()
        assert lines[0] == (
            f"{tr('JOINT_DIAG_SEVERITY')}\t{tr('JOINT_DIAG_SAMPLE')}\t"
            f"{tr('JOINT_DIAG_BATCH')}\t{tr('JOINT_DIAG_CHECK')}\t{tr('JOINT_DIAG_MESSAGE')}"
        )
        assert lines[1] == "WARN\tPA6\tbatch-01\trange\tNeeds review"
        assert len(lines) == 2

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_running_batch_list_copy_shortcut_copies_selected_item():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()

        window._batch_list.setVisible(True)
        window._batch_list.addItem("file_a.csv")
        window._batch_list.addItem("file_b.csv")
        window._batch_list.setCurrentRow(1)
        window._update_batch_list_copy_button()
        app.processEvents()
        assert not window._batch_list_copy_button.isHidden()
        assert window._batch_list_copy_button.isEnabled()
        window._batch_list_copy_button.click()

        assert QApplication.clipboard().text().splitlines() == ["file_b.csv"]

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_history_restore_loads_saved_data_file_and_parameters(tmp_path):
    app = QApplication.instance() or QApplication([])
    previous = get_language()
    set_language("en")
    tmp_path.mkdir(parents=True, exist_ok=True)

    data_file = tmp_path / "history.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    window = MainWindow()
    db_path = tmp_path / "samples.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    window._sample_db = SampleDB(db_path)
    db = window._ensure_sample_db()

    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(
        sample_id,
        "annealed-01",
        instrument="SAXS",
        condition_type="analysis",
        condition_values={"technique": "saxs"},
    )
    db.add_data_file(
        batch_id,
        str(data_file.resolve()),
        "saxs",
        file_type="csv",
        import_order=0,
    )
    db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        parameters={"baseline_method": "subtract", "smooth_window": 11},
        results_summary={
            "data_file": str(data_file.resolve()),
            "project_label": "PA6",
            "r2": 0.95,
        },
        output_dir=str(output_dir),
    )

    all_filter = window._history_filter_combo.findData("")
    if all_filter >= 0:
        window._history_filter_combo.setCurrentIndex(all_filter)
    window._refresh_history()
    window._on_history_row_activated(0, 0)

    baseline = _config_widget(window, "baseline_method")
    smooth_window = _config_widget(window, "smooth_window")

    assert window._current_filepath == str(data_file.resolve())
    assert window._path_input.text() == str(data_file.resolve())
    assert window._current_technique == "saxs"
    assert window._current_submodule_id == "saxs.static"
    assert baseline.currentText() == "subtract"
    assert smooth_window.value() == 11
    assert window._output_input.text() == str(output_dir)
    assert "Static SAXS" in window._workspace_subtitle.text()
    assert "saxs.static" not in window._workspace_subtitle.text()
    latest_log_line = window._log_panel.toPlainText().splitlines()[-1]
    assert "Static SAXS" in latest_log_line
    assert "saxs.static" not in latest_log_line
    db.close()
    window.deleteLater()
    app.processEvents()
    set_language(previous)


def test_history_restore_rehydrates_result_review_context(tmp_path):
    app = QApplication.instance() or QApplication([])
    previous = get_language()
    set_language("en")
    tmp_path.mkdir(parents=True, exist_ok=True)

    data_file = tmp_path / "history_ai.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")
    output_dir = tmp_path / "output_ai"
    output_dir.mkdir()

    window = MainWindow()
    db_path = tmp_path / "samples.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    window._sample_db = SampleDB(db_path)
    db = window._ensure_sample_db()

    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(
        sample_id,
        "annealed-01",
        instrument="SAXS",
        condition_type="analysis",
        condition_values={"technique": "saxs"},
    )
    db.add_data_file(
        batch_id,
        str(data_file.resolve()),
        "saxs",
        file_type="csv",
        import_order=0,
    )
    db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        parameters={"baseline_method": "subtract"},
        results_summary={
            "data_file": str(data_file.resolve()),
            "project_label": "PA6",
            "result_origin": "controlled_optimization_rerun",
            "confirmed": True,
            "history_context": {
                "review_summary": "Evidence review snapshot",
                "benchmark_text": "Benchmark: objective delta +0.018",
                "tuning_context": {
                    "benchmark_text": "Benchmark: objective delta +0.018",
                    "stop_reason": "quality guard reached",
                    "remaining_risks": "low-q coverage limited",
                    "next_goal": "keep q_bragg_min stable",
                    "history": [
                        {"round_num": 1, "accepted": True, "r_squared_after": 0.91},
                        {"round_num": 2, "accepted": False, "r_squared_after": 0.93, "llm_advice": {"rollback_reason": "symptom mismatch"}},
                    ],
                },
                "joint_ai_context": {
                    "summary": "Cross-tech consistency for PA6: 1 errors, 1 warnings",
                    "issue_count": 2,
                    "issue_families": ["phi_c inconsistency"],
                },
            },
        },
        output_dir=str(output_dir),
    )

    window._refresh_history()
    window._history_table.selectRow(0)
    window._on_history_restore_requested()
    window._update_results_review_panel()
    review_text = window._result_review_summary()

    assert "Benchmark: objective delta +0.018" in window._results_review_benchmark.text()
    assert "Run trace" in window._results_review_chain.text()
    assert "Cross-tech consistency for PA6" in window._results_review_joint.text()
    assert "quality guard reached" in review_text
    assert "keep q_bragg_min stable" in review_text

    db.close()
    window.deleteLater()
    app.processEvents()
    set_language(previous)


def test_results_review_panel_restores_benchmark_from_history_context(tmp_path):
    app = QApplication.instance() or QApplication([])
    previous = get_language()
    set_language("en")
    tmp_path.mkdir(parents=True, exist_ok=True)

    data_file = tmp_path / "history_ai.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    window = MainWindow()
    window._current_technique = "saxs"
    window._current_submodule_id = "saxs.static"
    window._current_filepath = str(data_file)
    window._results["saxs"] = {
        "parameters": {"L_nm": 12.0},
        "results_summary": {
            "project_label": "PA6",
            "result_origin": "controlled_optimization_rerun",
            "confirmed": True,
            "history_context": {
                "benchmark_text": "Benchmark: objective delta +0.018, accept 50.0%, rollback 50.0%, constraint hit 33.3%, symptom hit 75.0%.",
                "benchmark_summary": {
                    "average_objective_delta": 0.018,
                    "acceptance_rate": 0.5,
                    "rejection_rate": 0.5,
                    "constraint_hit_rate": 1 / 3,
                    "symptom_fix_rate": 0.75,
                },
                "next_goal": "keep q_bragg_min stable",
                "remaining_risks": "low-q coverage limited",
                "stop_reason": "quality guard reached",
                "joint_ai_context": {
                    "summary": "Cross-tech consistency for PA6: 1 errors, 1 warnings",
                },
            },
        },
    }

    window._update_results_review_panel()
    review_text = window._result_review_summary()

    assert "Evidence basis" in window._results_review_benchmark.text()
    assert "Benchmark: objective delta +0.018" in window._results_review_benchmark.text()
    assert "quality guard reached" in window._results_review_risk.text()
    assert "keep q_bragg_min stable" in window._results_review_next.text()
    assert "Cross-tech consistency for PA6" in window._results_review_joint.text()
    assert "Benchmark: objective delta +0.018" in review_text
    assert "low-q coverage limited" in review_text

    window.deleteLater()
    app.processEvents()


def test_build_run_config_keeps_expected_melt_blank_as_none():
    app = QApplication.instance() or QApplication([])

    window = MainWindow()
    window._current_technique = "saxs"
    window._on_submodule_selected("saxs", "saxs.static")

    expected_melt = _config_widget(window, "T_melt_expected")
    expected_melt.setText("")

    config = window._build_run_config()

    assert config is not None
    assert config.T_melt_expected is None

    window.deleteLater()
    app.processEvents()


def test_history_rerun_uses_selected_record_context(tmp_path):
    app = QApplication.instance() or QApplication([])
    previous = get_language()
    set_language("en")

    data_file = tmp_path / "history.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    window = MainWindow()
    window._sample_db = SampleDB(tmp_path / "samples.db")
    db = window._ensure_sample_db()

    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(
        sample_id,
        "annealed-01",
        instrument="SAXS",
        condition_type="analysis",
        condition_values={"technique": "saxs"},
    )
    db.add_data_file(
        batch_id,
        str(data_file.resolve()),
        "saxs",
        file_type="csv",
        import_order=0,
    )
    db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        parameters={"baseline_method": "normalize"},
        results_summary={"data_file": str(data_file.resolve())},
        output_dir=str(tmp_path / "output"),
    )

    captured = {}

    def fake_run_analysis():
        captured["filepath"] = window._current_filepath
        captured["technique"] = window._current_technique
        captured["submodule"] = window._current_submodule_id

    window._run_analysis = fake_run_analysis
    all_filter = window._history_filter_combo.findData("")
    if all_filter >= 0:
        window._history_filter_combo.setCurrentIndex(all_filter)
    window._refresh_history()
    window._history_table.selectRow(0)
    window._on_history_rerun_requested()

    assert captured == {
        "filepath": str(data_file.resolve()),
        "technique": "saxs",
        "submodule": "saxs.static",
    }
    latest_log_line = window._log_panel.toPlainText().splitlines()[-1]
    assert "Static SAXS" in latest_log_line

    db.close()
    window.deleteLater()
    app.processEvents()
    set_language(previous)


def test_set_running_ui_restores_translated_ready_label():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("zh")
        window = MainWindow()
        window._set_running_ui(True)
        window._set_running_ui(False)

        assert window._workflow_metric_state.text() == tr("WORKFLOW_READY")

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_set_running_ui_restores_directory_ready_label_for_native_directory(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_dir = tmp_path / "waxs_dir"
        data_dir.mkdir()

        window = MainWindow()
        window._current_technique = "waxs"
        window._set_input_path(str(data_dir), is_dir=True, input_mode="directory")
        window._set_running_ui(True)
        window._set_running_ui(False)

        assert window._workflow_metric_state.text() == "Directory ready"

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_set_running_ui_restores_batch_ready_label_for_non_native_directory(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_dir = tmp_path / "generic_batch"
        data_dir.mkdir()

        window = MainWindow()
        window._current_technique = "ir"
        window._set_input_path(str(data_dir), is_dir=True, input_mode="directory")
        window._set_running_ui(True)
        window._set_running_ui(False)

        assert window._workflow_metric_state.text() == "Batch ready"

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_set_running_ui_accepts_translated_joint_running_label():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._set_running_ui(True, tr("WORKFLOW_RUNNING_JOINT"))

        assert window._workflow_metric_state.text() == "Joint overview"

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_run_single_sets_specific_running_state(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "sample.dat"
        data_file.write_text("q I\n0.1 1.0\n", encoding="utf-8")

        window = MainWindow()
        window._current_technique = "saxs"
        window._current_filepath = str(data_file)

        with patch("polynexus.gui.main_window.AnalysisWorker") as worker_cls:
            worker = worker_cls.return_value
            worker.log_msg = type("SignalStub", (), {"connect": lambda self, fn: None})()
            worker.finished = type("SignalStub", (), {"connect": lambda self, fn: None})()
            worker.error_msg = type("SignalStub", (), {"connect": lambda self, fn: None})()
            worker.start = lambda: None
            with patch.object(window, "_build_run_config", return_value=None):
                with patch("polynexus.gui.main_window.QMessageBox.question", return_value=QMessageBox.Yes):
                    window._run_single()

        assert window._workflow_metric_state.text() == tr("WORKFLOW_RUNNING_SINGLE")

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_run_batch_sets_sequence_running_state_for_native_sequence(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_dir = tmp_path / "ir_temp"
        data_dir.mkdir()

        window = MainWindow()
        window._current_technique = "ir"
        window._current_submodule_id = "ir.temperature_2d"
        window._current_filepath = str(data_dir)
        window._current_input_mode = "sequence"

        with patch("polynexus.gui.main_window.AnalysisWorker") as worker_cls:
            worker = worker_cls.return_value
            worker.log_msg = type("SignalStub", (), {"connect": lambda self, fn: None})()
            worker.finished = type("SignalStub", (), {"connect": lambda self, fn: None})()
            worker.error_msg = type("SignalStub", (), {"connect": lambda self, fn: None})()
            worker.start = lambda: None
            with patch.object(window, "_build_run_config", return_value=None):
                window._run_batch()

        assert window._workflow_metric_state.text() == tr("WORKFLOW_RUNNING_SEQUENCE")

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_run_batch_sets_batch_running_state_for_generic_batch(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_dir = tmp_path / "generic_batch"
        data_dir.mkdir()
        (data_dir / "a.csv").write_text("q,I\n0.1,1.0\n", encoding="utf-8")
        (data_dir / "b.csv").write_text("q,I\n0.2,2.0\n", encoding="utf-8")

        window = MainWindow()
        window._current_technique = "ir"
        window._current_filepath = str(data_dir)
        window._current_input_mode = "directory"

        with patch("polynexus.gui.main_window.BatchWorker") as worker_cls:
            worker = worker_cls.return_value
            worker.log_msg = type("SignalStub", (), {"connect": lambda self, fn: None})()
            worker.progress = type("SignalStub", (), {"connect": lambda self, fn: None})()
            worker.file_done = type("SignalStub", (), {"connect": lambda self, fn: None})()
            worker.batch_finished = type("SignalStub", (), {"connect": lambda self, fn: None})()
            worker.error_msg = type("SignalStub", (), {"connect": lambda self, fn: None})()
            worker.start = lambda: None
            window._run_batch()

        assert window._workflow_metric_state.text() == tr("WORKFLOW_RUNNING_BATCH")

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_joint_overview_failure_message_uses_translation():
    previous = get_language()
    try:
        set_language("en")
        worker = JointHubWorker([], "")

        captured = []
        worker.error_msg.connect(captured.append)
        worker.run = JointHubWorker.run.__get__(worker, JointHubWorker)

        from unittest.mock import patch

        with patch("polynexus.gui.main_window.build_joint_hub_report", side_effect=RuntimeError("boom")):
            worker.run()

        assert captured == ["Joint overview failed: boom"]
    finally:
        set_language(previous)


def test_analysis_worker_unknown_technique_message_uses_translation(tmp_path):
    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "sample.csv"
        data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")
        worker = AnalysisWorker("mystery", str(data_file), str(tmp_path), engine=None)

        captured = []
        worker.error_msg.connect(captured.append)

        with patch("polynexus.gui.main_window.get_engine", return_value=None):
            worker.run()

        assert captured == ["Unknown technique: mystery"]
    finally:
        set_language(previous)


def test_analysis_worker_exception_message_uses_translation(tmp_path):
    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "sample.csv"
        data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

        class BrokenEngine:
            def run_pipeline(self, filepath, output_dir, skip_to=None):
                raise RuntimeError("boom")

        worker = AnalysisWorker("saxs", str(data_file), str(tmp_path), engine=BrokenEngine())
        captured = []
        worker.error_msg.connect(captured.append)
        worker.run()

        assert captured
        assert captured[0].startswith("Analysis failed: boom\n")
        assert "RuntimeError: boom" in captured[0]
    finally:
        set_language(previous)


def test_ai_tuning_progress_message_uses_translation():
    previous = get_language()
    try:
        set_language("en")
        worker = AITuneWorker("saxs", "sample.csv", "PA6")
        captured = []
        worker.signals.progress_msg.connect(captured.append)

        worker.signals.progress_msg.emit(tr("AI_TUNING_PROGRESS_ROUND", 3, "0.912"))

        assert captured == ["Round 3: EvalScore=0.912"]
    finally:
        set_language(previous)


def test_ai_tuning_failure_message_uses_translation():
    previous = get_language()
    try:
        set_language("en")
        worker = AITuneWorker("saxs", "sample.csv", "PA6")
        captured = []
        worker.signals.error_msg.connect(captured.append)

        worker.signals.error_msg.emit(tr("AI_TUNING_FAILED", "boom", "traceback"))

        assert captured == ["AI tune failed: boom\ntraceback"]
    finally:
        set_language(previous)


def test_joint_hub_error_log_uses_translation_prefix():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._on_joint_hub_error("boom")

        assert window._log_panel.toPlainText().splitlines()[-1].endswith("ERROR: boom")

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_ai_tune_error_log_uses_translation_prefix():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        with patch("polynexus.gui.main_window.QMessageBox.critical"):
            window._on_ai_tune_error("boom")

        assert window._log_panel.toPlainText().splitlines()[-1].endswith("ERROR: boom")

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_ai_tuning_context_summary_uses_current_workspace_state(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "sample.dat"
        data_file.write_text("q I\n0.1 1.0\n", encoding="utf-8")

        window = MainWindow()
        window._current_technique = "saxs"
        window._current_submodule_id = "saxs.static"
        window._current_filepath = str(data_file)
        window._current_input_mode = "sequence"
        window._set_results_summary("Single-file results | 1 metrics", "Risk note | low-q coverage limited", "")
        window._last_ai_tuning_context = {
            "summary": "Previous round summary: accepted 3 rounds; best R2 = 0.942; improvement = 0.021; total rounds = 4",
            "benchmark_text": "Benchmark: objective delta +0.018, accept 50.0%, rollback 50.0%, constraint hit 33.3%, symptom hit 75.0%.",
            "stop_reason": "quality guard reached",
            "remaining_risks": "low-q coverage limited",
            "next_goal": "The next round should keep the current gains and focus on q_bragg_min while still watching low-q coverage limited",
        }

        summary = window._ai_tuning_context_summary()

        assert "Technique: SAXS" in summary
        assert "Sub-module: Static SAXS" in summary
        assert "Input mode: Sequence" in summary
        assert f"Data source: {data_file.name}" in summary
        assert "Current result note: Risk note | low-q coverage limited" in summary
        assert "Previous round context:" in summary
        assert "Previous round summary: accepted 3 rounds" in summary
        assert "Benchmark: objective delta +0.018" in summary
        assert "Stop reason: quality guard reached" in summary
        assert "Remaining risks: low-q coverage limited" in summary
        assert "Next goal:" in summary
        assert "Current focus:" in summary
        assert "Planned tuning parameters:" in summary
        assert "- " in summary and "| current=" in summary

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_ai_tune_clicked_passes_selected_goal_to_worker(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "sample.dat"
        data_file.write_text("q I\n0.1 1.0\n", encoding="utf-8")

        window = MainWindow()
        window._current_technique = "saxs"
        window._current_submodule_id = "saxs.static"
        window._current_filepath = str(data_file)
        window._current_input_mode = "single"
        window._current_polymer_type = "PA6"
        window._results["saxs"] = {
            "parameters": {"L_nm": 12.0},
            "results_summary": {
                "project_label": "PA6",
                "result_origin": "controlled_optimization_rerun",
                "confirmed": True,
                "ai_tuned": True,
            },
        }
        window._last_ai_tuning_context = {
            "summary": "Previous round summary: accepted 3 rounds",
            "accepted_summary": "accepted 3 rounds",
            "benchmark_text": "Benchmark: objective delta +0.018, accept 50.0%, rollback 50.0%, constraint hit 33.3%, symptom hit 75.0%.",
            "benchmark_summary": {
                "average_objective_delta": 0.018,
            },
            "stop_reason": "quality guard reached",
            "remaining_risks": "low-q coverage limited",
            "next_goal": "keep q_bragg_min stable",
            "history": [
                {"round_num": 1, "accepted": True, "r_squared_after": 0.91},
                {
                    "round_num": 2,
                    "accepted": False,
                    "r_squared_after": 0.93,
                    "llm_advice": {"rollback_reason": "symptom mismatch"},
                },
                {"round_num": 3, "accepted": True, "r_squared_after": 0.95},
            ],
        }

        with patch("polynexus.gui.main_window.AITuningGoalDialog") as goal_dialog_cls:
            goal_dialog = goal_dialog_cls.return_value
            goal_dialog.exec.return_value = QDialog.Accepted
            goal_dialog.selected_goal.return_value = "joint"
            with patch("polynexus.gui.main_window.QMessageBox.question", return_value=QMessageBox.Yes):
                with patch("polynexus.gui.main_window.QProgressDialog") as progress_cls:
                    progress = progress_cls.return_value
                    progress.canceled.connect = lambda *args, **kwargs: None
                    progress.show = lambda *args, **kwargs: None
                    captured = {}

                    class FakeSignals:
                        def __init__(self):
                            self.progress_msg = type("Sig", (), {"connect": lambda self, fn: None})()
                            self.finished = type("Sig", (), {"connect": lambda self, fn: None})()
                            self.error_msg = type("Sig", (), {"connect": lambda self, fn: None})()

                    class FakeWorker:
                        def __init__(self, *args, **kwargs):
                            captured["workspace_context"] = kwargs.get("workspace_context")
                            self.signals = FakeSignals()
                        def cancel(self):
                            pass

                    with patch("polynexus.gui.main_window.AITuneWorker", FakeWorker):
                        with patch("polynexus.gui.main_window.QThreadPool.globalInstance") as pool_fn:
                            pool_fn.return_value.start = lambda worker: None
                            window.on_ai_tune_clicked()

        context = captured["workspace_context"]
        assert context["tuning_goal"] == "joint"
        assert context["tuning_goal_label"] == tr("AI_TUNING_GOAL_JOINT")
        assert window._current_ai_tuning_goal == "joint"

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_ai_tune_finished_surfaces_goal_in_workspace_and_review(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "sample.dat"
        data_file.write_text("q I\n0.1 1.0\n", encoding="utf-8")

        window = MainWindow()
        window._current_technique = "saxs"
        window._current_submodule_id = "saxs.static"
        window._current_filepath = str(data_file)
        window._current_input_mode = "single"
        window._current_ai_tuning_goal = "risk"
        window._results["saxs"] = {
            "parameters": {"L_nm": 12.0},
            "results_summary": {
                "project_label": "PA6",
                "result_origin": "controlled_optimization_rerun",
                "confirmed": True,
                "ai_tuned": True,
            },
        }

        class FakeDialog:
            def __init__(self, report, parent=None):
                self._report = report

            def exec(self):
                return QDialog.Rejected

            def best_config(self):
                return {}

        with patch("polynexus.gui.main_window.SideTuningReportDialog", FakeDialog):
            window._on_ai_tune_finished(
                {
                    "rounds": 2,
                    "best_r_squared": 0.942,
                    "improvement": {"r_squared_abs": 0.018},
                    "convergence_reason": "quality guard reached",
                    "history": [
                        {"round_num": 0, "accepted": True, "r_squared_after": 0.90},
                        {"round_num": 1, "accepted": True, "r_squared_after": 0.912},
                        {
                            "round_num": 2,
                            "accepted": False,
                            "r_squared_after": 0.908,
                            "llm_advice": {"rollback_reason": "quality guard reached"},
                        },
                    ],
                    "benchmark_summary": {
                        "average_objective_delta": 0.018,
                        "acceptance_rate": 0.5,
                        "rejection_rate": 0.5,
                        "constraint_hit_rate": 0.25,
                        "symptom_fix_rate": 0.5,
                    },
                }
            )

        review_text = window._result_review_summary()
        memory_text = window._work_memory_summary()

        assert window._last_ai_tuning_context["tuning_goal"] == "risk"
        assert window._last_ai_tuning_context["tuning_goal_label"] == tr("AI_TUNING_GOAL_RISK")
        assert "Risk" in review_text or "risk" in review_text.lower()
        assert "Risk" in memory_text or "risk" in memory_text.lower()
        assert "accepted" in review_text.lower()
        assert "baseline" in memory_text.lower() or "基线" in memory_text
        assert "baseline delta +0.018" in review_text or "baseline delta +0.018" in memory_text
        assert "rolled back 1 rounds" in review_text or "rolled back 1 rounds" in memory_text

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_ai_tuning_workspace_context_carries_previous_round_details(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "sample.dat"
        data_file.write_text("q I\n0.1 1.0\n", encoding="utf-8")

        window = MainWindow()
        window._current_technique = "saxs"
        window._current_submodule_id = "saxs.static"
        window._current_filepath = str(data_file)
        window._current_input_mode = "single"
        window._current_result_confirmed_flag = True
        window._results["saxs"] = {
            "parameters": {"L_nm": 12.0},
            "results_summary": {
                "project_label": "PA6",
                "result_origin": "controlled_optimization_rerun",
                "confirmed": True,
                "ai_tuned": True,
            },
        }
        window._last_ai_tuning_context = {
            "summary": "Previous round summary: accepted 3 rounds",
            "accepted_summary": "accepted 3 rounds",
            "benchmark_text": "Benchmark: objective delta +0.018, accept 50.0%, rollback 50.0%, constraint hit 33.3%, symptom hit 75.0%.",
            "benchmark_summary": {
                "average_objective_delta": 0.018,
            },
            "stop_reason": "quality guard reached",
            "remaining_risks": "low-q coverage limited",
            "next_goal": "keep q_bragg_min stable",
            "history": [
                {"round_num": 1, "accepted": True, "r_squared_after": 0.91},
                {
                    "round_num": 2,
                    "accepted": False,
                    "r_squared_after": 0.93,
                    "llm_advice": {"rollback_reason": "symptom mismatch"},
                },
                {"round_num": 3, "accepted": True, "r_squared_after": 0.95},
            ],
        }

        workspace_context = window._ai_tuning_workspace_context()
        from rag.prompt_builder import PromptBuilder
        prompt_text = PromptBuilder()._format_workspace_context(workspace_context)

        assert "Tuning context:" in prompt_text
        assert "stop_reason=quality guard reached" in prompt_text
        assert "remaining_risks=low-q coverage limited" in prompt_text
        assert "chain=baseline delta +0.018" in prompt_text
        assert "accepted 2 rounds, rolled back 1 rounds" in prompt_text
        assert "confirmed=True" in prompt_text
        assert "ai_tuned=True" in prompt_text
        assert workspace_context["tuning_context"]["benchmark_text"].startswith("Benchmark: objective delta +0.018")

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_ai_tuning_report_context_builds_benchmark_text_from_report():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()

        context = window._ai_tuning_report_context(
            {
                "rounds": 4,
                "best_r_squared": 0.945,
                "improvement": {"r_squared_abs": 0.021},
                "convergence_reason": "quality guard reached",
                "history": [
                    {"round_num": 0, "accepted": True, "r_squared_after": 0.90},
                    {"round_num": 1, "accepted": True, "r_squared_after": 0.912},
                    {
                        "round_num": 2,
                        "accepted": False,
                        "r_squared_after": 0.908,
                        "llm_advice": {"rollback_reason": "quality guard reached"},
                    },
                    {"round_num": 3, "accepted": True, "r_squared_after": 0.915},
                ],
                "benchmark_summary": {
                    "average_objective_delta": 0.018,
                    "acceptance_rate": 0.5,
                    "rejection_rate": 0.5,
                    "constraint_hit_rate": 1 / 3,
                    "symptom_fix_rate": 0.75,
                },
            }
        )

        assert context["benchmark_summary"]["acceptance_rate"] == 0.5
        assert len(context["history"]) == 4
        assert context["benchmark_text"] == (
            "Benchmark: objective delta +0.018, accept 50.0%, rollback 50.0%, "
            "constraint hit 33.3%, symptom hit 75.0%."
        )
        assert "Benchmark: objective delta +0.018" in context["summary"]

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_ai_tune_clicked_passes_previous_tuning_context_to_worker(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "sample.dat"
        data_file.write_text("q I\n0.1 1.0\n", encoding="utf-8")

        window = MainWindow()
        window._current_technique = "saxs"
        window._current_submodule_id = "saxs.static"
        window._current_filepath = str(data_file)
        window._current_input_mode = "single"
        window._current_polymer_type = "PA6"
        window._current_result_confirmed_flag = True
        window._results["saxs"] = {
            "parameters": {"L_nm": 12.0},
            "results_summary": {
                "project_label": "PA6",
                "result_origin": "controlled_optimization_rerun",
                "confirmed": True,
                "ai_tuned": True,
            },
        }
        window._last_ai_tuning_context = {
            "summary": "Previous round summary: accepted 3 rounds",
            "accepted_summary": "accepted 3 rounds",
            "benchmark_text": "Benchmark: objective delta +0.018, accept 50.0%, rollback 50.0%, constraint hit 33.3%, symptom hit 75.0%.",
            "stop_reason": "quality guard reached",
            "remaining_risks": "low-q coverage limited",
            "next_goal": "keep q_bragg_min stable",
        }

        with patch("polynexus.gui.main_window.AITuningGoalDialog") as goal_dialog_cls:
            goal_dialog = goal_dialog_cls.return_value
            goal_dialog.exec.return_value = QDialog.Accepted
            goal_dialog.selected_goal.return_value = "symptom"
            with patch("polynexus.gui.main_window.QMessageBox.question", return_value=QMessageBox.Yes):
                with patch("polynexus.gui.main_window.QProgressDialog") as progress_cls:
                    progress = progress_cls.return_value
                    progress.canceled.connect = lambda *args, **kwargs: None
                    progress.show = lambda *args, **kwargs: None
                    captured = {}

                    class FakeSignals:
                        def __init__(self):
                            self.progress_msg = type("Sig", (), {"connect": lambda self, fn: None})()
                            self.finished = type("Sig", (), {"connect": lambda self, fn: None})()
                            self.error_msg = type("Sig", (), {"connect": lambda self, fn: None})()

                    class FakeWorker:
                        def __init__(self, *args, **kwargs):
                            captured["workspace_context"] = kwargs.get("workspace_context")
                            self.signals = FakeSignals()
                        def cancel(self):
                            pass

                    with patch("polynexus.gui.main_window.AITuneWorker", FakeWorker):
                        with patch("polynexus.gui.main_window.QThreadPool.globalInstance") as pool_fn:
                            pool_fn.return_value.start = lambda worker: None
                            window.on_ai_tune_clicked()

        context = captured["workspace_context"]
        assert isinstance(context, dict)
        assert "tuning_context" in context
        assert context["tuning_context"]["stop_reason"] == "quality guard reached"
        assert context["tuning_context"]["remaining_risks"] == "low-q coverage limited"
        assert context["current_result"]["results_summary"]["confirmed"] is True

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_ai_tuning_workspace_context_carries_joint_ai_context(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "sample.dat"
        data_file.write_text("q I\n0.1 1.0\n", encoding="utf-8")

        window = MainWindow()
        window._current_technique = "waxs"
        window._current_submodule_id = "waxs.static"
        window._current_filepath = str(data_file)
        window._current_input_mode = "single"
        window._joint_report = {
            "summary": "1 batch rows, 3 validation checks, 1 errors, 2 warnings.",
            "rows": [
                {
                    "sample": "PA6",
                    "batch": "annealed",
                    "condition": "temperature=180",
                    "techniques": "DSC, SAXS, WAXS",
                    "opportunities": "crystallinity consistency",
                    "alerts": 2,
                }
            ],
            "validations": [
                {
                    "sample": "PA6",
                    "batch": "annealed",
                    "check": "PA6/annealed/phi_c_DSC_vs_WAXS",
                    "severity": "ERROR",
                    "passed": False,
                    "message": "phi_c(DSC)=0.420 vs phi_c(WAXS)=0.100 diff=0.320 (55.2%)",
                    "details": {},
                },
            ],
            "ai_context": {
                "summary": "Cross-tech consistency for PA6: 1 errors, 2 warnings; focus on phi_c inconsistency",
                "scope": "PA6",
                "sample_count": 1,
                "batch_count": 1,
                "issue_count": 1,
                "warning_count": 0,
                "error_count": 1,
                "issue_families": ["phi_c inconsistency"],
                "highlights": [
                    "ERROR | PA6 | annealed | phi_c_DSC_vs_WAXS | phi_c(DSC)=0.420 vs phi_c(WAXS)=0.100 diff=0.320 (55.2%)",
                ],
                "samples": ["PA6"],
                "batches": ["annealed"],
                "row_count": 1,
            },
        }

        workspace_context = window._ai_tuning_workspace_context()
        from rag.prompt_builder import PromptBuilder
        prompt_text = PromptBuilder()._format_workspace_context(workspace_context)

        assert "Cross-tech context:" in prompt_text
        assert "issue_families=phi_c inconsistency" in prompt_text
        assert "Cross-tech highlights:" in prompt_text

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_ai_tuning_workspace_context_builds_joint_ai_context_from_report_fallback(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "sample.dat"
        data_file.write_text("q I\n0.1 1.0\n", encoding="utf-8")

        window = MainWindow()
        window._current_technique = "waxs"
        window._current_submodule_id = "waxs.static"
        window._current_filepath = str(data_file)
        window._current_input_mode = "single"
        window._joint_report = {
            "summary": "1 batch rows, 2 validation checks, 1 errors, 1 warnings.",
            "rows": [
                {
                    "sample": "PA6",
                    "batch": "annealed",
                    "condition": "temperature=180",
                    "techniques": "DSC, SAXS, WAXS",
                    "opportunities": "crystallinity consistency",
                    "alerts": 2,
                }
            ],
            "validations": [
                {
                    "sample": "PA6",
                    "batch": "annealed",
                    "check": "PA6/annealed/phi_c_DSC_vs_WAXS",
                    "severity": "ERROR",
                    "passed": False,
                    "message": "phi_c(DSC)=0.420 vs phi_c(WAXS)=0.100 diff=0.320 (55.2%)",
                    "details": {},
                },
                {
                    "sample": "PA6",
                    "batch": "annealed",
                    "check": "PA6/annealed/L_consistency_SAXS_vs_WAXS",
                    "severity": "WARN",
                    "passed": False,
                    "message": "L(SAXS)=12.0 nm vs inferred WAXS spacing mismatch",
                    "details": {},
                },
            ],
        }

        workspace_context = window._ai_tuning_workspace_context()
        prompt_text = PromptBuilder()._format_workspace_context(workspace_context)

        joint_ai_context = workspace_context.get("joint_ai_context")
        assert isinstance(joint_ai_context, dict)
        assert joint_ai_context["issue_count"] == 2
        assert joint_ai_context["error_count"] == 1
        assert joint_ai_context["warning_count"] == 1
        assert "phi_c inconsistency" in joint_ai_context["issue_families"]
        assert "L consistency unstable" in joint_ai_context["issue_families"]
        assert "Cross-tech context:" in prompt_text
        assert "issue_families=phi_c inconsistency, L consistency unstable" in prompt_text

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_work_memory_payload_includes_current_confirmation_state(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "sample.dat"
        data_file.write_text("q I\n0.1 1.0\n", encoding="utf-8")

        window = MainWindow()
        window._current_technique = "saxs"
        window._current_submodule_id = "saxs.static"
        window._current_filepath = str(data_file)
        window._current_result_confirmed_flag = True
        window._results["saxs"] = {
            "parameters": {"L_nm": 12.0},
            "results_summary": {
                "project_label": "PA6",
                "result_origin": "controlled_optimization_rerun",
                "ai_tuned": True,
            },
        }
        window._last_ai_tuning_context = {
            "benchmark_text": "Benchmark: objective delta +0.018, accept 50.0%, rollback 50.0%, constraint hit 33.3%, symptom hit 75.0%.",
        }

        payload = window._work_memory_payload()
        current_slice = next(
            item for item in payload["slices"]
            if item["label"] == tr("WORK_MEMORY_CURRENT")
        )

        assert "Confirmed" in current_slice["detail"]
        assert "PA6" in current_slice["detail"]
        assert "Benchmark: objective delta +0.018" in current_slice["detail"]

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_work_memory_payload_includes_review_summary(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "sample.dat"
        data_file.write_text("q I\n0.1 1.0\n", encoding="utf-8")

        window = MainWindow()
        window._current_technique = "saxs"
        window._current_submodule_id = "saxs.static"
        window._current_filepath = str(data_file)
        window._results["saxs"] = {
            "parameters": {"L_nm": 12.0},
            "results_summary": {
                "project_label": "PA6",
                "result_origin": "controlled_optimization_rerun",
                "ai_tuned": True,
            },
        }
        window._last_ai_tuning_context = {
            "benchmark_text": "Benchmark: objective delta +0.018, accept 50.0%, rollback 50.0%, constraint hit 33.3%, symptom hit 75.0%.",
            "remaining_risks": "low-q coverage limited",
            "stop_reason": "quality guard reached",
            "tuning_goal": "risk",
            "tuning_goal_label": tr("AI_TUNING_GOAL_RISK"),
            "next_goal": "keep q_bragg_min stable",
        }
        window._joint_report = {
            "summary": "Cross-tech consistency for PA6: 1 errors, 2 warnings",
            "rows": [{"sample": "PA6", "batch": "batch-01"}],
            "validations": [
                {"severity": "WARN", "sample": "PA6", "batch": "batch-01", "check": "phi_c", "message": "needs review"}
            ],
        }

        payload = window._work_memory_payload()
        current_slice = next(
            item for item in payload["slices"]
            if item["label"] == tr("WORK_MEMORY_CURRENT")
        )

        assert "Recommended-parameter rerun" in current_slice["detail"]
        assert "Cross-tech consistency for PA6" in current_slice["detail"]
        assert "phi_c inconsistency" in current_slice["detail"]
        assert "quality guard reached" in current_slice["detail"]

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_ai_tuning_report_summary_prefers_stop_reason():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        dialog = SideTuningReportDialog(
            {
                "rounds": 4,
                "best_r_squared": 0.945,
                "improvement": {"r_squared_abs": 0.021},
                "convergence_reason": "quality guard reached",
                "history": [],
            }
        )

        assert dialog._summary_label.text() == tr(
            "AI_TUNING_REPORT_SUMMARY_WITH_REASON",
            4,
            0.945,
            0.021,
            "quality guard reached",
        )

        dialog.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_ai_tuning_report_decision_summary_surfaces_rollback_reason():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        dialog = SideTuningReportDialog(
            {
                "history": [
                    {
                        "round_num": 1,
                        "accepted": True,
                        "r_squared_after": 0.88,
                        "eval_score": 0.88,
                        "changes": {"alpha": 1.1},
                        "config_snapshot": {"alpha": 1.0},
                    },
                    {
                        "round_num": 2,
                        "accepted": False,
                        "r_squared_after": 0.86,
                        "eval_score": 0.86,
                        "changes": {"alpha": 1.4},
                        "config_snapshot": {"alpha": 1.1},
                        "llm_advice": {"rollback_reason": "quality guard reached"},
                    },
                ]
            }
        )

        assert dialog._decision_label.text() == tr(
            "AI_TUNING_REPORT_DECISION_WITH_ROLLBACK",
            1,
            1,
            "quality guard reached",
        )

        dialog.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_ai_tuning_report_surfaces_ir_reference_summary():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        dialog = SideTuningReportDialog(
            {
                "technique": "ir",
                "history": [
                    {
                        "round_num": 0,
                        "accepted": True,
                        "r_squared_after": 0.89,
                        "eval_score": 0.89,
                        "output_parameters": {
                            "n_peaks": 5,
                            "polymer_score": 0.74,
                            "assignment_confidence": 0.68,
                            "Xc_pct": 0.41,
                        },
                        "analysis_evidence": {
                            "feature_evidence": {
                                "reference_evidence": {
                                    "band_count": 3,
                                    "hit_count": 2,
                                    "missing_count": 1,
                                },
                                "assignment_evidence": {
                                    "assignment_confidence": 0.68,
                                },
                                "structure_evidence": {
                                    "paper_conclusion_ready": False,
                                },
                            }
                        },
                    }
                ],
            }
        )

        history_item = dialog.report["history"][0]
        summary_text = dialog._round_support_summary_text(history_item)
        assert "Reference bands" in summary_text
        assert "Assignment confidence" in summary_text
        assert "Conclusion state" in summary_text

        dialog.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_ai_tuning_report_uses_result_language_for_ir_summary():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        dialog = SideTuningReportDialog(
            {
                "technique": "ir",
                "history": [
                    {
                        "round_num": 0,
                        "accepted": True,
                        "r_squared_after": 0.89,
                        "eval_score": 0.89,
                        "output_parameters": {
                            "n_peaks": 5,
                            "polymer_score": 0.74,
                            "assignment_confidence": 0.68,
                            "Xc_pct": 0.41,
                        },
                        "analysis_evidence": {
                            "feature_evidence": {
                                "reference_evidence": {
                                    "band_count": 3,
                                    "hit_count": 2,
                                    "missing_count": 1,
                                },
                                "assignment_evidence": {
                                    "assignment_confidence": 0.68,
                                },
                                "structure_evidence": {
                                    "classification_basis": "peak_assignment",
                                    "characteristic_band_support_ok": False,
                                    "paper_conclusion_ready": False,
                                },
                            }
                        },
                    }
                ],
            }
        )

        history_item = dialog.report["history"][0]
        summary_text = dialog._round_support_summary_text(history_item)
        assert "Reference bands" in summary_text
        assert "Decision basis" in summary_text
        assert "Support chain" in summary_text
        assert "Conclusion state" in summary_text

        dialog.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_ir_result_review_summary_surfaces_detected_bands_assignment_and_paper_state(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_technique = "ir"
        window._current_submodule_id = "ir.standard"
        window._current_filepath = str(tmp_path / "ir.csv")
        window._results["ir"] = {
            "parameters": {"n_peaks": 5, "assignment_confidence": 0.68, "polymer_score": 0.74},
            "analysis_evidence": {
                "feature_evidence": {
                    "peak_evidence": {
                        "peak_count": 5,
                        "assigned_peak_count": 4,
                        "unassigned_peak_count": 1,
                    },
                    "reference_evidence": {
                        "band_count": 3,
                        "hit_count": 2,
                        "missing_count": 1,
                    },
                    "assignment_evidence": {
                        "assignment_confidence": 0.68,
                        "key_band_support_score": 0.67,
                        "peak_coverage_score": 0.80,
                        "baseline_stability_score": 0.75,
                        "ir_support_score": 0.73,
                    },
                    "band_tracking_evidence": {
                        "band_index_series_count": 3,
                        "band_index_transition_support_band_count": 3,
                        "band_index_transition_support_ratio": 1.0,
                        "band_index_transition_reproducible": True,
                        "band_tracking_missing_key_band": False,
                    },
                    "temperature_2d_evidence": {
                        "sequence_axis_score": 0.91,
                        "matrix_quality_score": 0.72,
                        "cos_signal_score": 0.76,
                        "band_tracking_score": 0.88,
                        "paper_conclusion_ready": False,
                    },
                    "structure_evidence": {
                        "classification_basis": "peak_assignment",
                        "characteristic_band_support_ok": False,
                        "paper_conclusion_ready": False,
                    },
                }
            },
            "results_summary": {
                "project_label": "PA6",
                "result_origin": "manual_run",
                "result": {
                    "parameters": {"n_peaks": 5, "assignment_confidence": 0.68, "polymer_score": 0.74},
                    "analysis_evidence": {
                        "feature_evidence": {
                            "peak_evidence": {
                                "peak_count": 5,
                                "assigned_peak_count": 4,
                                "unassigned_peak_count": 1,
                            },
                            "reference_evidence": {
                                "band_count": 3,
                                "hit_count": 2,
                                "missing_count": 1,
                            },
                            "assignment_evidence": {
                                "assignment_confidence": 0.68,
                                "key_band_support_score": 0.67,
                                "peak_coverage_score": 0.80,
                                "baseline_stability_score": 0.75,
                                "ir_support_score": 0.73,
                            },
                            "band_tracking_evidence": {
                                "band_index_series_count": 3,
                                "band_index_transition_support_band_count": 3,
                                "band_index_transition_support_ratio": 1.0,
                                "band_index_transition_reproducible": True,
                                "band_tracking_missing_key_band": False,
                            },
                            "temperature_2d_evidence": {
                                "sequence_axis_score": 0.91,
                                "matrix_quality_score": 0.72,
                                "cos_signal_score": 0.76,
                                "band_tracking_score": 0.88,
                                "paper_conclusion_ready": False,
                            },
                            "structure_evidence": {
                                "classification_basis": "peak_assignment",
                                "characteristic_band_support_ok": False,
                                "paper_conclusion_ready": False,
                            },
                        }
                    },
                },
            },
        }

        summary = window._result_review_summary()
        source_summary = window._result_source_summary_text()

        assert "Detected bands" in summary
        assert "Assignment confidence" in summary
        assert "Support detail" in summary
        assert "Conclusion state" in summary
        assert "Main risk" in summary
        assert "Conclusion state" in source_summary
        assert "peak_assignment" in source_summary or "peak assignment" in source_summary.lower()

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_ir_support_block_text_surfaces_temperature_2d_semantics():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        analysis_evidence = {
            "feature_evidence": {
                "peak_evidence": {
                    "peak_count": 5,
                    "assigned_peak_count": 4,
                    "unassigned_peak_count": 1,
                },
                "reference_evidence": {
                    "band_count": 3,
                    "hit_count": 2,
                    "missing_count": 1,
                },
                "assignment_evidence": {
                    "assignment_confidence": 0.68,
                    "key_band_support_score": 0.67,
                    "peak_coverage_score": 0.80,
                    "baseline_stability_score": 0.75,
                    "ir_support_score": 0.73,
                },
                "band_tracking_evidence": {
                    "band_index_series_count": 3,
                    "band_index_transition_support_band_count": 3,
                    "band_index_transition_support_ratio": 1.0,
                    "band_index_transition_reproducible": True,
                    "band_tracking_missing_key_band": False,
                },
                "temperature_2d_evidence": {
                    "sequence_axis_score": 0.91,
                    "matrix_quality_score": 0.72,
                    "cos_signal_score": 0.76,
                    "band_tracking_score": 0.88,
                    "paper_conclusion_ready": False,
                },
                "structure_evidence": {
                    "classification_basis": "peak_assignment",
                    "characteristic_band_support_ok": False,
                    "paper_conclusion_ready": False,
                },
            }
        }

        block = window._ir_support_block_text(analysis_evidence)
        assert "Band tracking" in block
        assert "Sequence trust" in block
        assert "Matrix trust" in block
        assert "Transition trust" in block

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_ir_support_block_text_surfaces_real_temperature_2d_semantics():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        from polynexus.core.ir_engine import IRConfig, analyze_temperature_2d_series, load_project, preprocess_pipeline
        from polynexus.core.analysis_evidence import build_analysis_evidence

        set_language("en")
        cfg = IRConfig(
            peak_height_min=0.03,
            peak_prominence_min=0.02,
            peak_distance=18.0,
            polymer_name="PA6",
        )
        spectra = load_project(str(Path(__file__).resolve().parents[1] / "娴嬭瘯鏁版嵁" / "IR" / "鍘熶綅鍙樻俯绾㈠"), cfg.wavenumber_range)
        processed = [preprocess_pipeline(s, cfg) for s in spectra]
        result = analyze_temperature_2d_series(processed, cfg)
        evidence = build_analysis_evidence(
            "IR",
            output_parameters=result.parameters,
            residual_pattern={"residual_type": "random", "summary": "2D sequence is stable enough for review"},
            validation_context={"config_snapshot": cfg.to_dict(), "submodule_id": "ir.temperature_2d"},
        ).to_dict()

        window = MainWindow()
        block = window._ir_support_block_text(evidence)
        assert "Band tracking" in block
        assert "Sequence trust" in block
        assert "Matrix trust" in block
        assert "Transition trust" in block

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_ir_temperature_2d_result_summary_surfaces_user_semantics_and_export_context(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_technique = "ir"
        window._current_submodule_id = "ir.temperature_2d"
        window._current_filepath = str(tmp_path / "ir_temperature_2d")
        window._results["ir"] = {
            "parameters": {
                "n_frames": 48,
                "T_range_C": "30-250",
                "sync_cross_peak_count": 12,
                "async_cross_peak_count": 12,
                "low_confidence_frame_ratio": 0.25,
                "low_confidence_frame_count": 12,
            },
            "analysis_evidence": {
                "feature_evidence": {
                    "sequence_evidence": {"stage_counts": {"heating": 23, "hold": 3, "cooling": 22}},
                    "single_frame_evidence": {
                        "low_confidence_frame_ratio": 0.25,
                        "frame_assignment_confidence_mean": 0.82,
                        "frame_key_band_support_mean": 0.79,
                    },
                    "temperature_2d_evidence": {
                        "sequence_axis_score": 0.89,
                        "matrix_quality_score": 0.72,
                        "cos_signal_score": 0.76,
                        "interpretation_ready": True,
                        "paper_conclusion_ready": False,
                    },
                    "structure_evidence": {
                        "classification_basis": "peak_assignment",
                        "characteristic_band_support_ok": False,
                        "paper_conclusion_ready": False,
                    },
                }
            },
            "results_summary": {"result_origin": "manual_run", "result": {"parameters": {"n_frames": 48}}},
        }

        review_text = window._result_review_summary()
        assert "Sequence axis" in review_text
        assert "Figure status" in review_text
        assert "Interpretation status" in review_text
        assert "Frame quality" in review_text

        export_context = window._export_context_payload(report_path=str(tmp_path / "report.html"))
        assert "paper_figures" not in export_context
        assert "Figure status" in export_context["review_summary"]
        assert "Sequence axis" in export_context["review_summary"]
        assert export_context["paper_figure_status"]

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_ai_tuning_report_benchmark_summary_surfaces_accuracy_signals():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        dialog = SideTuningReportDialog(
            {
                "benchmark_summary": {
                    "average_objective_delta": 0.018,
                    "acceptance_rate": 0.5,
                    "rejection_rate": 0.5,
                    "constraint_hit_rate": 1 / 3,
                    "symptom_fix_rate": 0.75,
                },
                "history": [],
            }
        )

        assert dialog._benchmark_label is not None
        assert dialog._benchmark_label.text() == tr(
            "AI_TUNING_REPORT_BENCHMARK",
            "+0.018",
            "50.0%",
            "50.0%",
            "33.3%",
            "75.0%",
        )

        dialog.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_ai_tuning_report_review_panels_surface_symptom_trials_and_guards():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        dialog = SideTuningReportDialog(
            {
                "convergence_reason": "quality guard reached",
                "history": [
                    {"round_num": 0, "accepted": True, "r_squared_after": 0.88, "eval_score": 0.88},
                    {
                        "round_num": 1,
                        "accepted": False,
                        "r_squared_after": 0.87,
                        "eval_score": 0.87,
                        "target_symptom": "peak_window_mismatch",
                        "symptom_summary": "peak_window_mismatch: Bragg peak window is unstable.",
                        "rollback_detail": "symptom unresolved after candidate trial",
                        "decision_summary": "rolled back target=peak_window_mismatch because symptom unresolved",
                        "analysis_evidence": {
                            "constraint_summary": {
                                "status": "soft_warn",
                                "triggered_counts": {
                                    "hard_fail": 0,
                                    "soft_warn": 1,
                                    "evidence_only": 0,
                                },
                                "triggered_names": {
                                    "soft_warn": ["peak_window_overlap"],
                                },
                            },
                            "stability_evidence": {
                                "stability_score": 0.82,
                                "parameter_stability_score": 0.91,
                                "method_agreement_score": 0.76,
                                "batch_continuity_score": 0.88,
                                "stability_flags": ["peak_window_mismatch"],
                            },
                        },
                        "llm_advice": {
                            "rollback_reason": "symptom unresolved",
                            "rollback_condition": "rollback if q_peak_diff_pct widens again",
                            "recommended_actions": [
                                {
                                    "name": "adjust_peak_window",
                                    "expected_evidence_change": "q_peak_diff_pct should shrink",
                                }
                            ],
                            "candidate_trials": [
                                {
                                    "action_name": "adjust_peak_window",
                                    "label": "Tighten peak window",
                                    "target_symptom": "peak_window_mismatch",
                                    "status": "rolled_back",
                                    "objective_delta": -0.01,
                                    "r_squared_delta": -0.01,
                                    "rollback_reason": "symptom unresolved",
                                    "decision_summary": "rolled back target=peak_window_mismatch because symptom unresolved",
                                    "expected_evidence_change": "q_peak_diff_pct should shrink",
                                    "changes": {"q_bragg_min": 0.18, "q_bragg_max": 0.82},
                                }
                            ],
                        },
                    },
                    {
                        "round_num": 2,
                        "accepted": True,
                        "r_squared_after": 0.92,
                        "eval_score": 0.95,
                        "target_symptom": "peak_window_mismatch",
                        "symptom_summary": "peak_window_mismatch: Bragg peak window is unstable.",
                        "decision_summary": "accepted target=peak_window_mismatch objective=0.950",
                        "analysis_evidence": {
                            "constraint_summary": {
                                "status": "ok",
                                "triggered_counts": {
                                    "hard_fail": 0,
                                    "soft_warn": 0,
                                    "evidence_only": 0,
                                },
                            },
                            "stability_evidence": {
                                "stability_score": 0.93,
                                "parameter_stability_score": 0.94,
                                "method_agreement_score": 0.90,
                                "batch_continuity_score": 0.92,
                                "stability_flags": [],
                            },
                        },
                        "llm_advice": {
                            "rollback_condition": "rollback if q_peak_diff_pct widens again",
                            "selected_candidate": {
                                "action_name": "adjust_peak_window",
                                "label": "Tighten peak window",
                                "changes": {"q_bragg_min": 0.19, "q_bragg_max": 0.80},
                                "target_symptom": "peak_window_mismatch",
                                "objective_score": 0.95,
                                "r_squared": 0.92,
                            },
                            "candidate_trials": [
                                {
                                    "action_name": "adjust_peak_window",
                                    "label": "Tighten peak window",
                                    "target_symptom": "peak_window_mismatch",
                                    "status": "accepted",
                                    "objective_delta": 0.07,
                                    "r_squared_delta": 0.04,
                                    "decision_summary": "accepted target=peak_window_mismatch objective=0.950",
                                    "expected_evidence_change": "q_peak_diff_pct should shrink",
                                    "changes": {"q_bragg_min": 0.19, "q_bragg_max": 0.80},
                                }
                            ],
                        },
                    },
                ],
            }
        )

        assert "peak_window_mismatch" in dialog._issue_target_label.text()
        assert "Bragg peak window is unstable" in dialog._issue_symptom_label.text()
        assert "symptom unresolved" in dialog._issue_risk_label.text()
        assert "score=0.930" in dialog._issue_stability_label.text()
        assert "Tighten peak window (adjust_peak_window)" in dialog._recommendation_label.text()
        assert "q_bragg_min -> 0.19" in dialog._recommendation_changes_label.text()
        assert "q_peak_diff_pct should shrink" in dialog._recommendation_decision_label.text()
        assert "status=ok" in dialog._evidence_constraints_label.text()
        assert "rollback if q_peak_diff_pct widens again" in dialog._rollback_boundary_label.text()
        assert dialog._candidate_table.rowCount() == 1
        assert dialog._candidate_table.item(0, 0).text() == "Tighten peak window (adjust_peak_window)"
        assert dialog._candidate_table.item(0, 1).text() == tr("AI_TUNING_TRIAL_STATUS_ACCEPTED")

        dialog.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_ai_tuning_chain_summary_surfaces_acceptance_and_best_round():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        chain = window._ai_tuning_chain_summary(
            {
                "benchmark_summary": {"average_objective_delta": 0.018},
                "history": [
                    {"round_num": 0, "accepted": True, "r_squared_after": 0.90},
                    {"round_num": 1, "accepted": True, "r_squared_after": 0.912},
                    {
                        "round_num": 2,
                        "accepted": False,
                        "r_squared_after": 0.908,
                        "llm_advice": {"rollback_reason": "quality guard reached"},
                    },
                    {"round_num": 3, "accepted": True, "r_squared_after": 0.915},
                ],
            }
        )

        assert "baseline delta +0.018" in chain
        assert "accepted 2 rounds, rolled back 1 rounds" in chain
        assert "best candidate round 3" in chain
        assert "latest accepted round 3" in chain
        assert "remaining risks: quality guard reached" in chain

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_ai_tuning_report_score_table_marks_rolled_back_round():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        dialog = SideTuningReportDialog(
            {
                "history": [
                    {"round_num": 1, "accepted": True, "r_squared_after": 0.90, "eval_score": 0.90},
                    {"round_num": 2, "accepted": False, "r_squared_after": 0.87, "eval_score": 0.87},
                ]
            }
        )

        assert dialog._score_table.item(0, 0).text() == tr("AI_TUNING_ROUND_ACCEPTED", 1)
        assert dialog._score_table.item(1, 0).text() == tr("AI_TUNING_ROUND_ROLLED_BACK", 2)
        assert dialog._score_table.item(0, 1).text() != ""
        assert dialog._score_table.item(0, 2).text() == tr("AI_TUNING_EMPTY_VALUE")

        dialog.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_ai_tune_finished_returns_to_config_before_rerun():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        captured = {"ran": False}

        class AcceptedDialog:
            def __init__(self, report, parent=None):
                self.report = report
            def exec(self):
                return QDialog.Accepted
            def best_config(self):
                return {"smooth_window": 9}

        window._run_analysis = lambda: captured.__setitem__("ran", True)

        with patch("polynexus.gui.main_window.SideTuningReportDialog", AcceptedDialog):
            window._on_ai_tune_finished({"best_config": {"smooth_window": 9}})

        assert window._tabs.currentIndex() == 1
        assert captured["ran"] is True
        assert "returned to Config" in window._log_panel.toPlainText()

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_worker_error_log_uses_translation_prefix():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        with patch("polynexus.gui.main_window.QMessageBox.critical"):
            window._on_error("boom")

        assert window._log_panel.toPlainText().splitlines()[-1].endswith("ERROR: boom")

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_joint_validation_log_uses_translation_prefix():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._joint_hub = type("Hub", (), {"has_selection": lambda self: True})()

        report = {
            "summary": "ok",
            "rows": [],
            "validations": [
                {"severity": "WARN", "message": "missing waxs"},
                {"severity": "ERROR", "message": "missing dsc"},
            ],
        }

        with patch.object(window, "_save_joint_hub_artifacts"):
            with patch.object(window, "_display_joint_report"):
                with patch.object(window, "_populate_plots"):
                    window._on_joint_hub_finished(report)

        lines = window._log_panel.toPlainText().splitlines()
        assert any(line.endswith("WARNING: missing waxs") for line in lines)
        assert any(line.endswith("ERROR: missing dsc") for line in lines)

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_joint_hub_artifacts_include_condition_values_and_timeline(tmp_path):
    app = QApplication.instance() or QApplication([])

    window = MainWindow()
    window._output_dir = str(tmp_path / "joint_output")
    report = {
        "summary": "ok",
        "rows": [
            {
                "sample": "PA6",
                "batch": "annealed-01",
                "condition": "temperature_C=180",
                "condition_values": {"temperature_C": 180},
                "techniques": "DSC, SAXS",
                "dsc_Xc_pct": 42.0,
                "waxs_Xc_pct": 40.0,
                "saxs_Xc_pct": 41.0,
                "Tm_C": 221.0,
                "L_nm": 12.0,
                "lc_nm": 5.0,
                "D_Scherrer_nm": 7.5,
                "opportunities": "crystallinity consistency",
                "alerts": 0,
            }
        ],
        "validations": [],
    }

    window._save_joint_hub_artifacts(report)

    summary_csv = tmp_path / "joint_output" / "data" / "joint_hub_summary.csv"
    timeline_png = tmp_path / "joint_output" / "figures" / "Fig-JointHub_timeline_alignment.png"

    assert summary_csv.exists()
    assert timeline_png.exists()

    summary_text = summary_csv.read_text(encoding="utf-8")
    assert "temperature_C" in summary_text
    assert "180" in summary_text

    window.deleteLater()
    app.processEvents()


def test_finished_logs_saxs_mask_diagnostics():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_technique = "saxs"

        result = type(
            "Result",
            (),
            {
                "parameters": {"L_nm": 12.0},
                "validation_summary": "Effective q_min > 0.10 nm^-1; Guinier region lost",
                "mask_truncated": True,
                "beam_stop_contaminated": True,
                "effective_q_min": 0.1234,
            },
        )()

        with patch.object(window, "_display_results"):
            with patch.object(window, "_populate_plots"):
                with patch.object(window, "_persist_analysis_run"):
                    window._on_finished(result)

        lines = window._log_panel.toPlainText().splitlines()
        assert any(line.endswith("Analysis diagnostics: Effective q_min > 0.10 nm^-1; Guinier region lost") for line in lines)
        assert any(line.endswith("SAXS mask note: effective q_min was pushed to 0.123 nm^-1, so the low-q Guinier region may be truncated.") for line in lines)
        assert any(line.endswith("SAXS beamstop note: low-q contamination was detected; use q_min >= 0.123 nm^-1 for this run.") for line in lines)

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_finished_shows_saxs_mask_summary_in_results_label():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_technique = "saxs"
        window._on_submodule_selected("saxs", "saxs.static")

        result = type(
            "Result",
            (),
            {
                "parameters": {"L_nm": 12.0},
                "validation_summary": "",
                "mask_truncated": True,
                "beam_stop_contaminated": True,
                "effective_q_min": 0.1234,
            },
        )()

        with patch.object(window, "_populate_plots"):
            with patch.object(window, "_persist_analysis_run"):
                window._on_finished(result)

        assert not window._results_summary_group.isHidden()
        assert window._results_summary_label.text() == "Single-file results | 1 metrics"
        assert window._results_summary_risk_label.text() == tr(
            "RESULTS_SUMMARY_RISK_MASK_AND_BEAMSTOP",
            "0.123",
        )
        assert window._results_summary_next_label.text() == tr("RESULTS_SUMMARY_NEXT_SAXS_RISK")

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_finished_shows_saxs_quality_flag_summary_when_only_quality_flag_is_present():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_technique = "saxs"
        window._on_submodule_selected("saxs", "saxs.static")

        result = type(
            "Result",
            (),
            {
                "parameters": {"L_nm": 12.0},
                "validation_summary": "",
                "quality_flag": "WARN:low_snr",
                "mask_truncated": False,
                "beam_stop_contaminated": False,
                "effective_q_min": 0.0,
            },
        )()

        with patch.object(window, "_populate_plots"):
            with patch.object(window, "_persist_analysis_run"):
                window._on_finished(result)

        assert not window._results_summary_group.isHidden()
        assert window._results_summary_risk_label.text() == tr("RESULTS_SUMMARY_RISK_VALIDATION", "low peak SNR")

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_saxs_strain_review_summary_surfaces_tensile_specific_signals():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_technique = "saxs"
        window._current_submodule_id = "saxs.strain"
        window._current_filepath = "C:/data/tensile_series.dat"
        strain_evidence = {
            "feature_evidence": {
                "condition_evidence": {
                    "condition_label": "strain",
                    "strain_axis_confidence": 0.68,
                    "strain_monotonic": True,
                    "strain_missing_count": 0,
                    "strain_duplicate_count": 0,
                    "strain_min_pct": 0.0,
                    "strain_max_pct": 12.0,
                },
                "strain_structure_evidence": {
                    "Q_star_rel_mean": 1.032,
                    "Q_star_rel_span": 0.018,
                    "phi_void_mean": 0.028,
                    "phi_void_span": 0.011,
                    "void_detected_frames": 4,
                    "f_Herman_mean": 0.41,
                    "f_Herman_span": 0.19,
                    "porod_slope_mean": -3.2,
                    "porod_slope_span": 0.32,
                    "strain_reliability_status": "low_confidence",
                    "strain_reliability_reason": "strain_axis_low_confidence|low_q_void_dominant",
                    "paper_figure_candidate": True,
                    "paper_conclusion_candidate": False,
                    "paper_conclusion_ready": False,
                },
            },
        }
        window._results["saxs"] = {
            "parameters": {
                "Q_star_rel_mean": 1.032,
                "phi_void_mean": 0.028,
                "f_Herman_mean": 0.41,
                "porod_slope_mean": -3.2,
                "void_detected_frames": 4,
                "strain_reliability_status": "low_confidence",
                "paper_figure_candidate": True,
                "paper_conclusion_candidate": False,
            },
            "analysis_evidence": strain_evidence,
            "results_summary": {
                "project_label": "PA6",
                "result_origin": "manual_run",
                "result": {
                    "parameters": {
                        "Q_star_rel_mean": 1.032,
                        "phi_void_mean": 0.028,
                        "f_Herman_mean": 0.41,
                        "porod_slope_mean": -3.2,
                        "void_detected_frames": 4,
                        "strain_reliability_status": "low_confidence",
                    },
                    "analysis_evidence": strain_evidence,
                },
            },
        }

        summary = window._result_review_summary()
        risk = window._results_risk_summary_text(window._results["saxs"]["parameters"])
        next_step = window._results_next_step_text(window._results["saxs"]["parameters"])
        metrics = window._history_result_metrics(window._results["saxs"])

        assert "Strain" in summary or "strain" in summary.lower()
        assert "Q_star_rel_mean=1.032" in summary
        assert "phi_void_mean=0.028" in summary
        assert "status=low_confidence" in summary.lower()
        assert "paper_figure_candidate=true" in summary.lower()
        assert "Risk note" in risk
        assert "status=low_confidence" in risk.lower()
        assert "Next step" in next_step
        assert "strain axis" in next_step.lower() or "strain 轴" in next_step
        assert metrics["Q_star_rel_mean"] == "1.032"
        assert metrics["phi_void_mean"] == "0.028"
        assert metrics["void_detected_frames"] == "4"

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_temperature_saxs_review_summary_surfaces_lc_status_and_window():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_technique = "saxs"
        window._current_submodule_id = "saxs.temperature"
        window._current_filepath = "C:/data/temp_series.dat"
        temp_evidence = {
            "structure_evidence": {
                "melting_window_status": "within_window",
                "lc_reliability_status": "diagnostic_only",
                "lc_reliability_reason": "low_lc_confidence|within_melting_window",
            },
            "feature_evidence": {
                "structure_evidence": {
                    "melting_window_status": "within_window",
                    "lc_reliability_status": "diagnostic_only",
                    "lc_reliability_reason": "low_lc_confidence|within_melting_window",
                },
            },
        }
        window._results["saxs"] = {
            "parameters": {
                "lc_nm": 1.23,
                "lc_method": "raw",
                "lc_reliability_status": "diagnostic_only",
                "lc_reliability_reason": "low_lc_confidence|within_melting_window",
                "melting_window_status": "within_window",
                "Tm_onset_C": 195.0,
                "Tm_peak_C": 205.0,
                "Tm_end_C": 220.0,
            },
            "analysis_evidence": temp_evidence,
            "results_summary": {
                "project_label": "PA6",
                "result_origin": "manual_run",
                "result": {
                    "parameters": {
                        "lc_nm": 1.23,
                        "lc_method": "raw",
                        "lc_reliability_status": "diagnostic_only",
                        "lc_reliability_reason": "low_lc_confidence|within_melting_window",
                        "melting_window_status": "within_window",
                        "Tm_onset_C": 195.0,
                        "Tm_peak_C": 205.0,
                        "Tm_end_C": 220.0,
                    },
                    "analysis_evidence": temp_evidence,
                },
            },
        }

        summary = window._result_review_summary()
        risk = window._results_risk_summary_text(window._results["saxs"]["parameters"])
        next_step = window._results_next_step_text(window._results["saxs"]["parameters"])

        assert "lc_nm=1.23" in summary
        assert "lc_method=raw" in summary
        assert "lc_reliability_status=diagnostic_only" in summary
        assert "melting_window_status=within_window" in summary
        assert "Risk note" in risk
        assert "diagnostic-only" in risk.lower()
        assert "Next step" in next_step
        assert "lc" in next_step.lower()

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_finished_shows_saxs_no_extra_risk_summary_when_only_status_is_present():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_technique = "saxs"
        window._on_submodule_selected("saxs", "saxs.static")
        window._current_filepath = "C:/data/sample_a.dat"

        result = type(
            "Result",
            (),
            {
                "parameters": {"L_nm": 12.0},
                "validation_summary": "",
                "mask_truncated": False,
                "beam_stop_contaminated": False,
                "effective_q_min": 0.0,
            },
        )()

        with patch.object(window, "_populate_plots"):
            with patch.object(window, "_persist_analysis_run"):
                window._on_finished(result)

        assert not window._results_summary_group.isHidden()
        assert window._results_summary_label.text() == tr("RESULTS_SUMMARY_SINGLE", 1, "sample_a.dat")
        assert window._results_summary_risk_label.text() == ""
        assert window._results_summary_next_label.text() == tr("RESULTS_SUMMARY_NEXT_SINGLE")

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_display_results_surfaces_saxs_condition_axis_risk_summary():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_technique = "saxs"
        window._current_input_mode = "directory"
        window._current_filepath = "C:/data/check_series"

        window._display_results(
            {
                "batch_frames": 3,
                "condition_source": "path_directory",
                "condition_confidence": 0.68,
                "condition_missing_frames": 1,
                "condition_continuity_score": 0.74,
                "_batch_data": [
                    {
                        "file": "Check-20260618_0_00002.edf",
                        "temperature_C": 100.0,
                        "condition_source": "path_directory",
                        "condition_confidence": 0.72,
                    },
                    {
                        "file": "Check-20260618_0_00003.edf",
                        "temperature_C": None,
                        "condition_source": "path_directory",
                        "condition_confidence": 0.64,
                    },
                    {
                        "file": "Check-20260618_0_00004.edf",
                        "temperature_C": 120.0,
                        "condition_source": "header",
                        "condition_confidence": 0.68,
                    },
                ],
            }
        )

        assert window._results_summary_label.text() == "Directory results | 1 sample / 3 frames | check_series"
        assert window._results_summary_risk_label.text() == tr(
            "RESULTS_SUMMARY_RISK_CONDITION_AXIS",
            "path_directory",
            "0.68",
            "1",
            "0.74",
        )
        assert window._results_summary_next_label.text() == tr("RESULTS_SUMMARY_NEXT_CONDITION_AXIS")

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_finished_updates_result_review_panel_with_context():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_technique = "saxs"
        window._current_submodule_id = "saxs.static"
        window._current_filepath = "C:/data/sample_a.dat"
        window._results["saxs"] = {
            "parameters": {"L_nm": 12.0},
            "validation_summary": "WARN: low-q coverage limited",
            "results_summary": {
                "project_label": "PA6",
                "result_origin": "controlled_optimization_rerun",
            },
        }
        window._current_result_confirmed_flag = True
        window._last_ai_tuning_context = {
            "benchmark_text": "Benchmark: objective delta +0.018, accept 50.0%, rollback 50.0%, constraint hit 33.3%, symptom hit 75.0%.",
            "remaining_risks": "low-q coverage limited",
            "stop_reason": "quality guard reached",
            "next_goal": "keep q_bragg_min stable",
        }
        window._joint_report = {
            "summary": "Cross-tech consistency for PA6: 1 errors, 2 warnings",
            "rows": [{"sample": "PA6", "batch": "batch-01"}],
            "validations": [
                {"severity": "WARN", "sample": "PA6", "batch": "batch-01", "check": "phi_c", "message": "needs review"}
            ],
        }

        window._update_results_review_panel()

        assert not window._results_review_group.isHidden()
        assert "confirmed" in window._results_review_title.text().lower()
        assert "PA6" in window._results_review_meta.text()
        assert "Recommended-parameter rerun" in window._results_review_meta.text()
        assert "Evidence basis" in window._results_review_benchmark.text()
        assert "benchmark" in window._results_review_benchmark.text().lower()
        assert "Run trace" in window._results_review_chain.text()
        assert "Boundary" in window._results_review_boundary.text()
        assert "Cross-tech consistency" in window._results_review_joint.text()
        assert "phi_c inconsistency" in window._results_review_joint.text()
        assert "joint.compare" in window._results_review_joint.text()
        assert "WARN" in window._results_review_risk.text()
        assert "keep q_bragg_min stable" in window._results_review_next.text()

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_finished_results_review_panel_surfaces_temperature_fallback_evidence():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_technique = "saxs"
        window._current_submodule_id = "saxs.temperature"
        window._current_filepath = "C:/data/check_series"
        window._results["saxs"] = {
            "parameters": {
                "batch_frames": 17,
                "condition_label": "Temperature",
                "condition_source": "header",
                "condition_confidence": 0.9,
                "calibrated_fallback_active": True,
                "calibrated_fallback_reason": "temperature_batch_lc_calibration",
                "batch_calibration_summary": {
                    "fallback_rows": 17,
                    "raw_snapshot_rows": 17,
                    "fallback_ratio": 1.0,
                    "raw_structure_available": True,
                    "calibrated_fallback_reason": "temperature_batch_lc_calibration",
                },
            },
            "analysis_evidence": {
                "batch_evidence": {
                    "batch_frames": 17,
                    "batch_calibration_summary": {
                        "fallback_rows": 17,
                        "raw_snapshot_rows": 17,
                        "fallback_ratio": 1.0,
                        "raw_structure_available": True,
                        "calibrated_fallback_reason": "temperature_batch_lc_calibration",
                    },
                },
                "structure_evidence": {
                    "calibrated_fallback_active": True,
                    "calibrated_fallback_reason": "temperature_batch_lc_calibration",
                },
                "symptoms": [
                    {"name": "temperature_calibration_fallback_active"},
                    {"name": "batch_summary_conflicts_with_frame_evidence"},
                    {"name": "thickness_chain_unreliable"},
                ],
            },
            "validation_passed": True,
            "validation_summary": "All checks passed",
            "results_summary": {
                "project_label": "PA6",
                "result_origin": "manual_run",
                "validation_passed": True,
            },
        }

        window._display_results(window._results["saxs"]["parameters"], window._results["saxs"])
        window._update_results_review_panel()
        review_text = window._result_review_summary()

        assert "Batch evidence" in window._results_review_boundary.text()
        assert "fallback ratio=100%" in window._results_review_boundary.text()
        assert "raw frame evidence=17 frames" in window._results_review_boundary.text()
        assert "conflicts with raw frame evidence" in window._results_review_boundary.text()
        assert "thickness-chain outputs" in window._results_review_boundary.text()
        assert "temperature_batch_lc_calibration" in window._results_review_boundary.text()
        assert "calibration state:" in window._results_review_trend.text()
        assert "calibrated_fallback_active=True" in window._results_review_trend.text()
        assert "Batch evidence" in window._results_summary_risk_label.text()
        assert "fallback ratio=100%" in window._results_summary_risk_label.text()
        assert window._results_summary_next_label.text() == tr("RESULTS_SUMMARY_NEXT_FALLBACK_CONFLICT")
        assert "Batch evidence" in review_text
        assert "raw frame evidence=17 frames" in review_text

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_finished_results_summary_surfaces_saxs_lc_status_risk():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_technique = "saxs"
        window._current_submodule_id = "saxs.temperature"
        window._current_input_mode = "directory"
        window._current_filepath = "C:/data/pa6_series"
        window._results["saxs"] = {
            "parameters": {
                "batch_frames": 2,
                "batch_structure_summary": {
                    "diagnostic_only_rows": 1,
                    "within_window_rows": 1,
                    "dominant_lc_reliability_status": "diagnostic_only",
                    "dominant_lc_reliability_reason": "low_lc_confidence|within_melting_window",
                },
                "_batch_data": [
                    {
                        "file": "frame_170.edf",
                        "temperature_C": 170.0,
                        "melting_window_status": "outside_window",
                        "lc_reliability_status": "usable",
                    },
                    {
                        "file": "frame_195.edf",
                        "temperature_C": 195.0,
                        "melting_window_status": "within_window",
                        "lc_reliability_status": "diagnostic_only",
                    },
                ],
            },
            "analysis_evidence": {
                "batch_evidence": {
                    "batch_structure_summary": {
                        "diagnostic_only_rows": 1,
                        "within_window_rows": 1,
                        "dominant_lc_reliability_status": "diagnostic_only",
                        "dominant_lc_reliability_reason": "low_lc_confidence|within_melting_window",
                    }
                }
            },
            "validation_summary": "All checks passed",
            "results_summary": {"project_label": "PA6", "result_origin": "manual_run"},
        }

        window._display_results(window._results["saxs"]["parameters"], window._results["saxs"])

        expected_risk = tr(
            "RESULTS_SUMMARY_RISK_SAXS_LC_STATUS",
            "diagnostic_only",
            1,
            1,
            "low_lc_confidence|within_melting_window",
        ).replace("diagnostic_only", "diagnostic-only")
        assert window._results_summary_risk_label.text() == expected_risk
        assert window._results_summary_next_label.text() == tr("RESULTS_SUMMARY_NEXT_SAXS_LC_STATUS")

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_finished_result_review_panel_surfaces_saxs_lc_semantic_boundary():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_technique = "saxs"
        window._current_submodule_id = "saxs.temperature"
        window._current_input_mode = "directory"
        window._current_filepath = "C:/data/pa6_series"
        window._results["saxs"] = {
            "parameters": {
                "batch_frames": 3,
                "batch_structure_summary": {
                    "batch_rows": 3,
                    "diagnostic_only_rows": 1,
                    "low_confidence_rows": 1,
                    "usable_rows": 1,
                    "near_onset_rows": 1,
                    "within_window_rows": 0,
                    "post_end_rows": 0,
                    "dominant_lc_reliability_status": "diagnostic_only",
                    "dominant_lc_reliability_reason": "low_lc_confidence|near_melting_onset",
                    "dominant_melting_window_status": "near_onset",
                },
            },
            "analysis_evidence": {
                "batch_evidence": {
                    "batch_structure_summary": {
                        "batch_rows": 3,
                        "diagnostic_only_rows": 1,
                        "low_confidence_rows": 1,
                        "usable_rows": 1,
                        "near_onset_rows": 1,
                        "within_window_rows": 0,
                        "post_end_rows": 0,
                        "dominant_lc_reliability_status": "diagnostic_only",
                        "dominant_lc_reliability_reason": "low_lc_confidence|near_melting_onset",
                        "dominant_melting_window_status": "near_onset",
                    }
                },
                "symptoms": [
                    {"name": "diagnostic_lc_frames_present"},
                    {"name": "temperature_sequence_near_melting_window"},
                    {"name": "lc_unreliable_without_melting_proof"},
                ],
            },
            "validation_summary": "All checks passed",
            "results_summary": {"project_label": "PA6", "result_origin": "manual_run"},
        }

        window._display_results(window._results["saxs"]["parameters"], window._results["saxs"])
        window._update_results_review_panel()
        review_text = window._result_review_summary()

        assert "Interpretation status" in review_text
        assert "diagnostic-only for lc" in review_text
        assert "Melting-window status" in review_text
        assert "near the SAXS-derived melting onset" in review_text
        assert "Decision boundary" in review_text
        assert "do not call this melting yet" in review_text
        assert not window._results_review_trend.isHidden()
        assert "SAXS structure status" in window._results_review_trend.text()
        assert "transition-sensitive" in window._results_review_trend.text() or "do not call this melting yet" in window._results_review_trend.text()

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_finished_result_review_panel_hides_ai_trace_for_manual_results():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_technique = "saxs"
        window._current_submodule_id = "saxs.static"
        window._current_filepath = "C:/data/sample_a.dat"
        window._results["saxs"] = {
            "parameters": {"L_nm": 12.0},
            "validation_summary": "All checks passed",
            "results_summary": {"project_label": "PA6", "result_origin": "manual_run"},
        }
        window._last_ai_tuning_context = {
            "benchmark_text": "Benchmark: objective delta +0.018",
            "stop_reason": "quality guard reached",
            "remaining_risks": "low-q coverage limited",
        }

        window._update_results_review_panel()
        review_text = window._result_review_summary()

        assert "PA6" in review_text
        assert "Manual run" in review_text
        assert "Benchmark:" not in review_text
        assert "quality guard reached" not in review_text

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_result_comparison_summary_uses_translated_fallbacks():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_technique = "saxs"
        window._current_submodule_id = "saxs.static"
        window._current_filepath = "C:/data/sample_a.dat"
        window._results["saxs"] = {
            "parameters": {"L_nm": 12.0, "Xc_pct": 0.31},
            "results_summary": {
                "project_label": "PA6",
                "result": {"parameters": {"L_nm": 12.0, "Xc_pct": 0.31}},
            },
        }
        window._sample_db = SampleDB(tmp_path := Path(window._get_last_dir()) / "temp_compare.db")
        db = window._ensure_sample_db()
        sample_id = db.create_sample("PA6")
        batch_id = db.create_batch(
            sample_id,
            "batch-01",
            instrument="SAXS",
            condition_type="analysis",
            condition_values={"technique": "saxs"},
        )
        db.create_analysis_run(
            batch_id,
            "saxs",
            submodule="saxs.static",
            parameters={"L_nm": 10.0, "Xc_pct": 0.25},
            results_summary={
                "data_file": str(tmp_path / "sample_a.dat"),
                "project_label": "PA6",
                "result": {"parameters": {"L_nm": 10.0, "Xc_pct": 0.25}},
            },
            output_dir=str(tmp_path / "output_a"),
        )

        text = window._result_comparison_summary()

        assert "Current:" in text
        assert "Baseline:" in text

        db.close()
        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_joint_ai_context_summary_surfaces_example_issue():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._joint_report = {
            "rows": [{"sample": "PA6", "batch": "batch-01"}],
            "validations": [
                {"severity": "WARN", "sample": "PA6", "batch": "batch-01", "check": "phi_c", "message": "needs review"},
                {"severity": "ERROR", "sample": "PA6", "batch": "batch-01", "check": "L_consistency", "message": "unstable"},
            ],
        }

        context = window._joint_ai_context()

        assert "Cross-tech consistency for PA6" in context["summary"]
        assert "example WARN · PA6 / batch-01 · phi_c · needs review" in context["summary"]
        assert "phi_c inconsistency" in context["summary"]
        assert "L consistency unstable" in context["summary"]

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_single_results_summary_prefers_persisted_ai_tuned_origin():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_technique = "saxs"
        window._current_filepath = "C:/data/sample_a.dat"
        window._results["saxs"] = {
            "results_summary": {
                "ai_tuned": True,
                "result_origin": "controlled_optimization_rerun",
            }
        }

        text = window._single_results_summary_text({"L_nm": 12.0})

        assert text == tr("RESULTS_SUMMARY_SINGLE_AI_TUNED", 1, "sample_a.dat")

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_finished_logs_sequence_completion_summary():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_technique = "ir"
        window._current_input_mode = "sequence"
        window._current_filepath = "C:/data/ir_temp"

        result = type(
            "Result",
            (),
            {
                "parameters": {"batch_frames": 12},
                "validation_summary": "",
                "mask_truncated": False,
                "beam_stop_contaminated": False,
            },
        )()

        with patch.object(window, "_display_results"):
            with patch.object(window, "_populate_plots"):
                with patch.object(window, "_persist_analysis_run"):
                    window._on_finished(result)

        lines = window._log_panel.toPlainText().splitlines()
        assert any(line.endswith("Sequence run complete: 12 frames @ ir_temp") for line in lines)

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_finished_logs_directory_completion_fallback_summary():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_technique = "nmr"
        window._current_input_mode = "directory"
        window._current_filepath = "C:/data/nmr_dir"

        result = type(
            "Result",
            (),
            {
                "parameters": {},
                "validation_summary": "",
                "mask_truncated": False,
                "beam_stop_contaminated": False,
            },
        )()

        with patch.object(window, "_display_results"):
            with patch.object(window, "_populate_plots"):
                with patch.object(window, "_persist_analysis_run"):
                    window._on_finished(result)

        lines = window._log_panel.toPlainText().splitlines()
        assert any(line.endswith("Directory run complete: nmr_dir") for line in lines)

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_display_results_sets_sequence_summary_for_multi_frame_results():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_input_mode = "sequence"
        window._current_filepath = "C:/data/ir_temp"

        window._display_results(
            {
                "batch_frames": 3,
                "_batch_data": [
                    {"extra_tag": "A", "Xc_pct": 31.2, "file": "frame_001.csv", "L_nm": 10.1234},
                    {"extra_tag": "B", "Xc_pct": 32.8, "file": "frame_002.csv", "L_nm": 10.4567},
                    {"extra_tag": "C", "Xc_pct": 34.1, "file": "frame_003.csv", "L_nm": 10.7891},
                ],
            }
        )

        assert not window._results_summary_label.isHidden()
        assert window._results_summary_label.text() == "Sequence results | 1 sample / 3 frames | ir_temp"
        assert window._results_table.rowCount() == 3
        assert _table_headers(window._results_table)[:4] == ["file", "L_nm", "Xc_pct", "extra_tag"]
        assert window._results_table.isSortingEnabled()
        assert not window._btn_results_default_order.isHidden()

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_display_results_clears_summary_for_single_frame_results():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_input_mode = "sequence"

        window._display_results(
            {
                "batch_frames": 2,
                "_batch_data": [
                    {"file": "frame_001.csv", "L_nm": 10.1234},
                    {"file": "frame_002.csv", "L_nm": 10.4567},
                ],
            }
        )
        assert not window._results_summary_label.isHidden()

        window._display_results({"L_nm": 12.0, "Xc": 0.31})

        assert window._results_summary_label.isHidden()
        assert window._results_summary_label.text() == ""
        assert window._results_table.columnCount() == 2
        assert not window._results_table.isSortingEnabled()
        assert not window._btn_results_export.isHidden()
        assert not window._btn_results_copy.isHidden()
        assert window._btn_results_default_order.isHidden()

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_copy_results_table_copies_single_frame_table_to_clipboard():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()

        window._display_results({"L_nm": 12.0, "Xc": 0.31})
        window._copy_results_table_to_clipboard()

        text = QApplication.clipboard().text()
        assert text.splitlines()[0] == "Parameter\tValue"
        assert "L_nm\t12.0000" in text
        assert "Xc\t0.3100" in text
        assert not window._btn_results_copy.isHidden()
        assert "Copied results table: 2 rows x 2 columns" in window._log_panel.toPlainText()

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_export_results_table_writes_single_frame_tsv(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()

        export_path = tmp_path / "single_frame.tsv"
        window._display_results({"L_nm": 12.0, "Xc": 0.31})

        with patch("polynexus.gui.main_window.QFileDialog.getSaveFileName", return_value=(str(export_path), "TSV (*.tsv)")):
            window._export_results_table()

        text = export_path.read_text(encoding="utf-8")
        assert text.splitlines()[0] == "Parameter\tValue"
        assert "L_nm\t12.0000" in text
        assert "Xc\t0.3100" in text
        assert not window._btn_results_export.isHidden()
        assert "Exported results table: 2 rows x 2 columns" in window._log_panel.toPlainText()

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_export_results_table_uses_table_export_service(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()

        export_calls = {}

        def fake_write_table_export(path, headers, matrix, *, selected_filter=""):
            export_calls["path"] = path
            export_calls["headers"] = list(headers)
            export_calls["matrix"] = [list(row) for row in matrix]
            export_calls["selected_filter"] = selected_filter
            return str(path)

        window._display_results({"L_nm": 12.0, "Xc": 0.31})
        with patch("polynexus.gui.main_window.write_table_export", side_effect=fake_write_table_export, create=True), patch(
            "polynexus.gui.main_window.QFileDialog.getSaveFileName",
            return_value=(str(tmp_path / "results_table.tsv"), "TSV (*.tsv)"),
        ):
            window._export_results_table()

        assert export_calls["path"] == str(tmp_path / "results_table.tsv")
        assert export_calls["headers"] == ["Parameter", "Value"]
        assert export_calls["matrix"] == [["L_nm", "12.0000"], ["Xc", "0.3100"]]
        assert export_calls["selected_filter"] == "TSV (*.tsv)"

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_display_results_enables_sorting_for_multi_sample_results():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()

        window._display_results(
            {
                "sample_b": {"custom_note": "annealed", "Xc_pct": 43.5, "L_nm": 12.3},
                "sample_a": {"custom_note": "quenched", "Xc_pct": 39.2, "L_nm": 10.8},
            }
        )

        assert not window._results_summary_label.isHidden()
        assert window._results_summary_label.text() == "Multi-sample results | 2 rows"
        assert _table_headers(window._results_table)[:4] == ["sample", "L_nm", "Xc_pct", "custom_note"]
        assert window._results_table.isSortingEnabled()
        assert not window._btn_results_export.isHidden()
        assert not window._btn_results_copy.isHidden()
        assert not window._btn_results_default_order.isHidden()

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_results_default_order_restores_original_batch_row_order():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()

        window._on_batch_finished(
            [
                {"file": "a.csv", "params": {"custom_note": "annealed", "Xc_pct": 43.5, "L_nm": 12.3}},
                {"file": "b.csv", "params": {"custom_note": "quenched", "Xc_pct": 39.2, "L_nm": 10.8}},
            ]
        )

        assert window._results_table.item(0, 0).text() == "a.csv"

        window._results_table.sortItems(1, Qt.AscendingOrder)
        app.processEvents()

        assert window._results_table.item(0, 0).text() == "b.csv"

        window._restore_results_table_default_order()

        assert window._results_table.item(0, 0).text() == "a.csv"
        assert window._results_table.isSortingEnabled()
        assert not window._btn_results_default_order.isHidden()

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_copy_results_table_uses_current_sorted_batch_order():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()

        window._on_batch_finished(
            [
                {"file": "a.csv", "params": {"custom_note": "annealed", "Xc_pct": 43.5, "L_nm": 12.3}},
                {"file": "b.csv", "params": {"custom_note": "quenched", "Xc_pct": 39.2, "L_nm": 10.8}},
            ]
        )

        window._results_table.sortItems(1, Qt.AscendingOrder)
        app.processEvents()
        window._copy_results_table_to_clipboard()

        lines = QApplication.clipboard().text().splitlines()
        assert lines[0] == "file\tL_nm\tXc_pct\tcustom_note"
        assert lines[1] == "b.csv\t10.8000\t39.2000\tquenched"
        assert lines[2] == "a.csv\t12.3000\t43.5000\tannealed"

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_copy_results_table_prefers_selected_rows_over_full_table():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()

        window._on_batch_finished(
            [
                {"file": "a.csv", "params": {"custom_note": "annealed", "Xc_pct": 43.5, "L_nm": 12.3}},
                {"file": "b.csv", "params": {"custom_note": "quenched", "Xc_pct": 39.2, "L_nm": 10.8}},
            ]
        )

        window._results_table.selectRow(1)
        app.processEvents()
        window._copy_results_table_to_clipboard()

        lines = QApplication.clipboard().text().splitlines()
        assert lines[0] == "file\tL_nm\tXc_pct\tcustom_note"
        assert lines[1] == "b.csv\t10.8000\t39.2000\tquenched"
        assert len(lines) == 2
        assert "Copied results table: 1 rows x 4 columns" in window._log_panel.toPlainText()

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_results_table_copy_shortcut_copies_selected_rows():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()

        window._on_batch_finished(
            [
                {"file": "a.csv", "params": {"custom_note": "annealed", "Xc_pct": 43.5, "L_nm": 12.3}},
                {"file": "b.csv", "params": {"custom_note": "quenched", "Xc_pct": 39.2, "L_nm": 10.8}},
            ]
        )

        window._results_table.selectRow(1)
        app.processEvents()
        window._results_copy_shortcut.activated.emit()

        lines = QApplication.clipboard().text().splitlines()
        assert lines[0] == "file\tL_nm\tXc_pct\tcustom_note"
        assert lines[1] == "b.csv\t10.8000\t39.2000\tquenched"
        assert len(lines) == 2

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_export_results_table_uses_current_selected_sorted_batch_rows(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()

        export_path = tmp_path / "selected_rows.csv"
        window._on_batch_finished(
            [
                {"file": "a.csv", "params": {"custom_note": "annealed", "Xc_pct": 43.5, "L_nm": 12.3}},
                {"file": "b.csv", "params": {"custom_note": "quenched", "Xc_pct": 39.2, "L_nm": 10.8}},
            ]
        )

        window._results_table.sortItems(1, Qt.AscendingOrder)
        app.processEvents()
        window._results_table.selectRow(0)
        app.processEvents()

        with patch("polynexus.gui.main_window.QFileDialog.getSaveFileName", return_value=(str(export_path), "CSV (*.csv)")):
            window._export_results_table()

        text = export_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        assert lines[0] == "file,L_nm,Xc_pct,custom_note"
        assert lines[1] == "b.csv,10.8000,39.2000,quenched"
        assert len(lines) == 2

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_on_batch_finished_sets_batch_results_summary():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_filepath = "C:/data/generic_batch"

        window._on_batch_finished(
            [
                {"file": "a.csv", "params": {"custom_note": "annealed", "Xc_pct": 43.5, "L_nm": 12.3}},
                {"file": "b.csv", "params": {"custom_note": "quenched", "Xc_pct": 39.2, "L_nm": 10.8}},
            ]
        )

        assert not window._results_summary_label.isHidden()
        assert window._results_summary_label.text() == "Batch results | 2 files | generic_batch"
        assert window._results_table.rowCount() == 2
        assert _table_headers(window._results_table)[:4] == ["file", "L_nm", "Xc_pct", "custom_note"]
        assert window._results_table.isSortingEnabled()
        assert not window._btn_results_export.isHidden()
        assert not window._btn_results_copy.isHidden()
        assert not window._btn_results_default_order.isHidden()

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_display_results_sets_directory_summary_with_source_name():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_input_mode = "directory"
        window._current_filepath = "C:/data/waxs_runs"

        window._display_results(
            {
                "batch_frames": 2,
                "_batch_data": [
                    {"file": "run_001.raw", "Xc_pct": 31.2},
                    {"file": "run_002.raw", "Xc_pct": 32.8},
                ],
            }
        )

        assert not window._results_summary_label.isHidden()
        assert window._results_summary_label.text() == "Directory results | 1 sample / 2 frames | waxs_runs"

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_export_results_creates_structured_bundle_with_manifest(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        output_dir = tmp_path / "analysis_output"
        figures_dir = output_dir / "figures"
        data_dir = output_dir / "data"
        report_dir = output_dir / "report"
        figures_dir.mkdir(parents=True)
        data_dir.mkdir()
        report_dir.mkdir()
        (figures_dir / "Fig-1.png").write_text("figure", encoding="utf-8")
        (data_dir / "results.csv").write_text("a,b\n1,2\n", encoding="utf-8")
        (report_dir / "analysis_report.md").write_text("# Report\n", encoding="utf-8")

        export_parent = tmp_path / "export_target"
        export_parent.mkdir()

        window = MainWindow()
        window._output_dir = str(output_dir)
        window._current_filepath = str(tmp_path / "sample.dat")
        window._current_technique = "saxs"
        window._current_submodule_id = "saxs.static"
        window._current_input_mode = "single"
        window._project_label.setText("PA6")
        window._results["saxs"] = {
            "dummy": True,
            "results_summary": {
                "ai_tuned": True,
                "result_origin": "controlled_optimization_rerun",
                "project_label": "PA6",
                "confirmed": True,
            },
        }
        window._current_result_confirmed_flag = True
        window._last_ai_tuning_context = {
            "summary": "Previous round summary: accepted 3 rounds",
            "accepted_summary": "accepted 3 rounds",
            "benchmark_text": "Benchmark: objective delta +0.018, accept 50.0%, rollback 50.0%, constraint hit 33.3%, symptom hit 75.0%.",
            "stop_reason": "quality guard reached",
            "remaining_risks": "low-q coverage limited",
            "next_goal": "keep q_bragg_min stable",
        }
        window._joint_report = {
            "summary": "Cross-tech consistency for PA6: 1 errors, 1 warnings",
            "rows": [{"sample": "PA6", "batch": "batch-01"}],
            "validations": [
                {"severity": "WARN", "sample": "PA6", "batch": "batch-01", "check": "phi_c", "message": "needs review"},
            ],
        }
        db = SampleDB(tmp_path / "samples.db")
        sample_id = db.create_sample("PA6")
        batch_id = db.create_batch(
            sample_id,
            "batch-01",
            instrument="SAXS",
            condition_type="analysis",
            condition_values={"technique": "saxs"},
        )
        db.add_data_file(
            batch_id,
            str((tmp_path / "sample.dat").resolve()),
            "saxs",
            file_type="dat",
            import_order=0,
        )
        db.create_analysis_run(
            batch_id,
            "saxs",
            submodule="saxs.static",
            parameters={"L_nm": 11.2},
            results_summary={
                "data_file": str((tmp_path / "sample.dat").resolve()),
                "project_label": "PA6",
                "confirmed": True,
                "result_origin": "controlled_optimization_rerun",
            },
            output_dir=str(output_dir),
            ai_tuned=True,
            confirmed=True,
        )
        window._sample_db = db

        with patch("polynexus.gui.main_window.QFileDialog.getExistingDirectory", return_value=str(export_parent)):
            with patch("polynexus.core.report.generate_report", return_value="<html></html>"):
                with patch("polynexus.core.report.save_report", side_effect=lambda html, out: str(Path(out) / "polynexus_report.html")):
                    window._export_results()

        bundle_root = export_parent / "PolyNexus_Export"
        assert (bundle_root / "figures" / "Fig-1.png").exists()
        assert (bundle_root / "data" / "results.csv").exists()
        assert (bundle_root / "report" / "analysis_report.md").exists()
        assert (bundle_root / "metadata" / "export_manifest.json").exists()
        assert (bundle_root / "README.txt").exists()

        manifest = json.loads((bundle_root / "metadata" / "export_manifest.json").read_text(encoding="utf-8"))
        assert manifest["directories"] == {
            "figures": "figures",
            "data": "data",
            "report": "report",
            "metadata": "metadata",
        }
        assert manifest["current_technique"] == "saxs"
        assert manifest["current_submodule"] == "saxs.static"
        assert manifest["input_mode"] == "single"
        assert manifest["task_context"]["task_type"] == "Single-file analysis"
        assert manifest["task_context"]["technique_label"] == "SAXS"
        assert manifest["task_context"]["submodule_label"]
        assert manifest["task_context"]["result_origin"] == "controlled_optimization_rerun"
        assert manifest["task_context"]["result_origin_label"] == "Recommended-parameter rerun"
        assert manifest["task_context"]["used_controlled_optimization"] is True
        assert manifest["task_context"]["confirmed_result"] is True
        assert manifest["task_context"]["decision_owner"] == "user"
        assert manifest["task_context"]["decision_owner_label"] == "User"
        assert manifest["task_context"]["review_priority"][0] == "report/"
        assert manifest["task_context"]["recommended_reading_order"][0] == "report/polynexus_report.html"
        assert manifest["task_context"]["recommended_reading_order"][1] == "metadata/export_manifest.json"
        assert "Current:" in manifest["task_context"]["comparison_summary"]
        assert "Confirmed reference" in manifest["task_context"]["review_summary"]
        assert "Benchmark: objective delta +0.018" in manifest["task_context"]["review_summary"]
        assert "quality guard reached" in manifest["task_context"]["review_summary"]
        assert "Benchmark: objective delta +0.018" in manifest["task_context"]["validation_chain"]
        assert "Cross-tech consistency for PA6" in manifest["task_context"]["joint_summary"]
        assert "Boundary" in manifest["task_context"]["responsibility_boundary"]
        assert "Current result:" in manifest["task_context"]["work_memory_summary"]

        readme = (bundle_root / "README.txt").read_text(encoding="utf-8")
        assert "PolyNexus Export Package" in readme
        assert "report/" in readme
        assert "metadata/" in readme
        assert "Task type: Single-file analysis" in readme
        assert "Result origin: Recommended-parameter rerun" in readme
        assert "Confirmed result: Yes" in readme
        assert "Decision owner: User" in readme
        assert "Controlled optimization used: Yes" in readme
        assert "Comparison summary: Current:" in readme
        assert "Review summary: Confirmed reference" in readme
        assert "Validation chain:" in readme
        assert "Joint summary:" in readme
        assert "Cross-tech consistency for PA6" in readme
        assert "Responsibility boundary: Boundary" in readme
        assert "Benchmark: objective delta +0.018" in readme
        assert "Work memory:" in readme
        assert "Current result:" in readme
        assert "Review priority:" in readme
        assert "Recommended reading order:" in readme
        assert "1. report/polynexus_report.html" in readme

        db.close()

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_export_results_writes_html_report_into_report_directory(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        output_dir = tmp_path / "analysis_output"
        output_dir.mkdir()
        export_parent = tmp_path / "export_target"
        export_parent.mkdir()

        window = MainWindow()
        window._output_dir = str(output_dir)
        window._current_filepath = str(tmp_path / "sample.dat")
        window._project_label.setText("PA6")
        window._results["saxs"] = {"dummy": True}

        report_calls = []

        def fake_save_report(html, out):
            report_calls.append(out)
            Path(out).mkdir(parents=True, exist_ok=True)
            report_path = Path(out) / "polynexus_report.html"
            report_path.write_text(html, encoding="utf-8")
            return str(report_path)

        with patch("polynexus.gui.main_window.QFileDialog.getExistingDirectory", return_value=str(export_parent)):
            with patch("polynexus.core.report.generate_report", return_value="<html>report</html>"):
                with patch("polynexus.core.report.save_report", side_effect=fake_save_report):
                    window._export_results()

        bundle_root = export_parent / "PolyNexus_Export"
        log_text = window._log_panel.toPlainText()
        assert report_calls == [str(bundle_root / "report")]
        assert "Report generation skipped:" not in log_text
        assert f"Report: {bundle_root / 'report' / 'polynexus_report.html'}" in log_text

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_work_memory_panel_shows_current_result_and_recent_context(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._sample_db = SampleDB(tmp_path / "samples.db")
        db = window._ensure_sample_db()
        sample_id = db.create_sample("PA6")
        batch_id = db.create_batch(
            sample_id,
            "batch-01",
            instrument="SAXS",
            condition_type="analysis",
            condition_values={"technique": "saxs"},
        )
        db.add_data_file(
            batch_id,
            str((tmp_path / "input.csv")),
            "saxs",
            file_type="csv",
            import_order=0,
        )
        db.create_analysis_run(
            batch_id,
            "saxs",
            submodule="saxs.static",
            parameters={"baseline_method": "subtract"},
            results_summary={
                "data_file": str((tmp_path / "input.csv")),
                "ai_tuned": True,
                "result_origin": "controlled_optimization_rerun",
                "result": {"parameters": {"Xc_pct": 0.31}},
            },
            output_dir=str(tmp_path / "output_b"),
            ai_tuned=True,
        )
        window._current_technique = "saxs"
        window._current_submodule_id = "saxs.static"
        window._current_filepath = str(tmp_path / "input.csv")
        window._results["saxs"] = {
            "parameters": {"L_nm": 11.2},
            "results_summary": {"result": {"parameters": {"Xc_pct": 0.31}}, "ai_tuned": True},
        }
        window._last_export_bundle = str(tmp_path / "export_pkg")
        payload = window._work_memory_payload()
        window._update_work_memory_panel()

        panel = window._work_memory_panels
        assert panel["title"].text() == "Work memory"
        assert any(str(item.get("label") or "") == "Recent history" for item in payload["slices"])
        assert any("Recommended-parameter rerun" in str(item.get("detail") or "") for item in payload["slices"])

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_export_results_remembers_last_export_bundle(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        output_dir = tmp_path / "analysis_output"
        output_dir.mkdir()
        export_parent = tmp_path / "export_target"
        export_parent.mkdir()

        window = MainWindow()
        window._output_dir = str(output_dir)
        window._current_filepath = str(tmp_path / "sample.dat")
        window._project_label.setText("PA6")
        window._results["saxs"] = {"dummy": True}

        with patch("polynexus.gui.main_window.QFileDialog.getExistingDirectory", return_value=str(export_parent)):
            with patch("polynexus.core.report.generate_report", return_value="<html></html>"):
                with patch("polynexus.core.report.save_report", side_effect=lambda html, out: str(Path(out) / "polynexus_report.html")):
                    window._export_results()

        assert window._last_export_bundle == str(export_parent / "PolyNexus_Export")

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_sidebar_labels_and_joint_tooltips_use_language_tables():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()

        assert window._sidebar_section_labels["recent"].text() == "Recent projects"
        assert window._sidebar_section_labels["joint"].text() == "Joint analysis"
        assert window._sidebar_section_labels["samples"].text() == "Samples"
        assert window._nav_buttons["joint.quick"].text() == "Quick joint"
        assert window._nav_buttons["joint.quick"].toolTip() == "Use current in-memory results"
        assert window._nav_buttons["joint.compare"].text() == "Sample compare"
        assert window._nav_buttons["joint.compare"].toolTip() == "Compare selected samples from the database"

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_infer_sample_name_ignores_translated_placeholder_label(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("zh")
        data_file = tmp_path / "pa66.csv"
        data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

        window = MainWindow()
        window._project_label.setText(tr("NO_PROJECT"))
        window._current_filepath = str(data_file.resolve())

        assert window._infer_sample_name() == "pa66"

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_workspace_titles_use_translated_samples_and_joint_labels():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("zh")
        window = MainWindow()

        window._on_samples_selected()
        assert window._workspace_title.text() == "样品库"
        assert window._workflow_metric_tech.text() == "样品"
        assert window._status_tech_label.text() == " 样品 "

        window._on_joint_selected("joint.quick")
        assert window._workspace_title.text() == "联合分析"
        assert window._workflow_metric_tech.text() == "联合"
        assert window._status_tech_label.text() == " 联合 "

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_default_workspace_metric_tech_matches_default_selected_technique():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()

        assert window._workspace_title.text() == "SAXS Analysis"
        assert window._workflow_metric_tech.text() == "SAXS"
        assert window._status_tech_label.text() == " SAXS "
        assert window._workflow_task_label.text() == "Current Task"
        assert window._workflow_task_title.text() == "Analysis workspace with input"
        assert "Waiting for input" in window._workflow_task_detail.text()
        assert "No data loaded" in window._workflow_task_detail.text()

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_workflow_task_card_shows_running_state_for_active_single_run(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "single.dat"
        data_file.write_text("q I\n0.1 1.0\n", encoding="utf-8")

        window = MainWindow()
        window._current_technique = "saxs"
        window._set_input_path(str(data_file), is_dir=False, input_mode="single")
        window._set_running_ui(True, tr("WORKFLOW_RUNNING_SINGLE"))

        assert window._workflow_task_title.text() == "Single-file analysis"
        assert "Running" in window._workflow_task_detail.text()
        assert "single.dat" in window._workflow_task_detail.text()
        assert "No sub-module selected" in window._workflow_task_detail.text()

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_workflow_task_card_shows_controlled_optimization_state(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "single.dat"
        data_file.write_text("q I\n0.1 1.0\n", encoding="utf-8")

        window = MainWindow()
        window._current_technique = "saxs"
        window._current_submodule_id = "saxs.static"
        window._set_input_path(str(data_file), is_dir=False, input_mode="single")
        window._ai_tuning_active = True
        window._update_workflow_task_card()

        assert window._workflow_task_title.text() == "Controlled optimization in progress"
        assert "Controlled optimization" in window._workflow_task_detail.text()
        assert "Static SAXS" in window._workflow_task_detail.text()
        assert "single.dat" in window._workflow_task_detail.text()

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_context_suggestions_prompt_for_input_when_no_data_loaded():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()

        data_panel = window._context_suggestion_panels["data"]
        config_panel = window._context_suggestion_panels["config"]

        assert "No input is loaded yet" in data_panel["detail"].text()
        assert data_panel["buttons"][0].text() == "Choose file"
        assert data_panel["buttons"][1].text() == "Choose folder"

        assert "Go back to Data first" in config_panel["detail"].text()
        assert config_panel["buttons"][0].text() == "Back to Data"
        assert config_panel["buttons"][1].text() == "Go to History"

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_context_suggestions_offer_calibration_actions_for_saxs_scope(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "sample.dat"
        data_file.write_text("q I\n0.1 1.0\n", encoding="utf-8")

        window = MainWindow()
        window._current_technique = "saxs"
        window._set_input_path(str(data_file), is_dir=False, input_mode="single")
        window._build_config_for_technique("saxs")
        window._update_context_suggestions()

        config_panel = window._context_suggestion_panels["config"]
        assert "Current config scope" in config_panel["detail"].text()
        assert (
            config_panel["buttons"][0].text() == "Save recent calibration"
            or config_panel["buttons"][0].text() == "Apply recent calibration"
        )
        assert config_panel["buttons"][1].text() == "Go to Results" or config_panel["buttons"][1].text() == "Go to History"

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_context_suggestions_prioritize_ai_tuned_follow_up(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "sample.dat"
        data_file.write_text("q I\n0.1 1.0\n", encoding="utf-8")

        window = MainWindow()
        window._current_technique = "saxs"
        window._current_submodule_id = "saxs.static"
        window._set_input_path(str(data_file), is_dir=False, input_mode="single")
        window._results["saxs"] = {
            "parameters": {"L_nm": 11.2},
            "results_summary": {
                "ai_tuned": True,
                "result_origin": "controlled_optimization_rerun",
            },
        }
        window._update_context_suggestions()

        config_panel = window._context_suggestion_panels["config"]
        assert "recommended-parameter rerun result" in config_panel["detail"].text()
        assert config_panel["buttons"][0].text() == tr("CONTEXT_HINT_ACTION_REVIEW_AI_RESULT")
        assert config_panel["buttons"][1].text() == tr("CONTEXT_HINT_ACTION_RUN_CONTROLLED_OPTIMIZATION")

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_history_compare_finds_previous_same_technique_run(tmp_path):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "history.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    window = MainWindow()
    window._sample_db = SampleDB(tmp_path / "samples.db")
    db = window._ensure_sample_db()

    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(
        sample_id,
        "annealed-01",
        instrument="SAXS",
        condition_type="analysis",
        condition_values={"technique": "saxs"},
    )
    db.add_data_file(
        batch_id,
        str(data_file.resolve()),
        "saxs",
        file_type="csv",
        import_order=0,
    )
    older_run = db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        parameters={"baseline_method": "normalize"},
        results_summary={
            "data_file": str(data_file.resolve()),
            "result": {"parameters": {"L_nm": 10.0, "Xc_pct": 0.31}},
        },
        output_dir=str(tmp_path / "output_a"),
    )
    newer_run = db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        parameters={"baseline_method": "subtract"},
        results_summary={
            "data_file": str(data_file.resolve()),
            "result": {"parameters": {"L_nm": 12.0, "Xc_pct": 0.35}},
        },
        output_dir=str(tmp_path / "output_b"),
    )

    runs = db.get_analysis_runs(batch_id)
    current = next(run for run in runs if run["id"] == newer_run)
    baseline = window._history_compare_record(current)

    assert baseline is not None
    assert baseline["id"] == older_run

    metrics = window._history_result_metrics(current)
    assert metrics["L_nm"] == "12.0"
    assert metrics["Xc_pct"] == "0.35"

    db.close()
    window.deleteLater()
    app.processEvents()


def test_history_compare_prefers_same_submodule(tmp_path):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "history.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    window = MainWindow()
    window._sample_db = SampleDB(tmp_path / "samples.db")
    db = window._ensure_sample_db()

    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(
        sample_id,
        "annealed-01",
        instrument="SAXS",
        condition_type="analysis",
        condition_values={"technique": "saxs"},
    )
    db.add_data_file(
        batch_id,
        str(data_file.resolve()),
        "saxs",
        file_type="csv",
        import_order=0,
    )
    other_submodule_run = db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.temperature",
        parameters={"baseline_method": "normalize"},
        results_summary={"data_file": str(data_file.resolve())},
        output_dir=str(tmp_path / "output_temp"),
    )
    older_same_submodule = db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        parameters={"baseline_method": "normalize"},
        results_summary={"data_file": str(data_file.resolve())},
        output_dir=str(tmp_path / "output_a"),
    )
    newer_same_submodule = db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        parameters={"baseline_method": "subtract"},
        results_summary={"data_file": str(data_file.resolve())},
        output_dir=str(tmp_path / "output_b"),
    )

    runs = db.get_analysis_runs(batch_id)
    current = next(run for run in runs if run["id"] == newer_same_submodule)
    baseline = window._history_compare_record(current)

    assert baseline is not None
    assert baseline["id"] == older_same_submodule
    assert baseline["id"] != other_submodule_run

    db.close()
    window.deleteLater()
    app.processEvents()


def test_history_compare_uses_strain_specific_metrics_for_tensile_saxs(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "history.csv"
        data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

        window = MainWindow()
        window._sample_db = SampleDB(tmp_path / "samples.db")
        db = window._ensure_sample_db()

        sample_id = db.create_sample("PA6")
        batch_id = db.create_batch(
            sample_id,
            "strain-01",
            instrument="SAXS",
            condition_type="analysis",
            condition_values={"technique": "saxs"},
        )
        db.add_data_file(
            batch_id,
            str(data_file.resolve()),
            "saxs",
            file_type="csv",
            import_order=0,
        )
        baseline_run = db.create_analysis_run(
            batch_id,
            "saxs",
            submodule="saxs.strain",
            parameters={"Q_star_rel_mean": 1.012, "phi_void_mean": 0.012, "void_detected_frames": 1},
            results_summary={
                "data_file": str(data_file.resolve()),
                "result": {
                    "parameters": {"Q_star_rel_mean": 1.012, "phi_void_mean": 0.012, "void_detected_frames": 1},
                    "analysis_evidence": {
                        "feature_evidence": {
                            "condition_evidence": {"condition_label": "strain", "strain_axis_confidence": 0.72},
                            "strain_structure_evidence": {
                                "Q_star_rel_mean": 1.012,
                                "phi_void_mean": 0.012,
                                "void_detected_frames": 1,
                            },
                        }
                    },
                },
            },
            output_dir=str(tmp_path / "output_a"),
        )
        current_run = db.create_analysis_run(
            batch_id,
            "saxs",
            submodule="saxs.strain",
            parameters={"Q_star_rel_mean": 1.032, "phi_void_mean": 0.028, "void_detected_frames": 4},
            results_summary={
                "data_file": str(data_file.resolve()),
                "result": {
                    "parameters": {"Q_star_rel_mean": 1.032, "phi_void_mean": 0.028, "void_detected_frames": 4},
                    "analysis_evidence": {
                        "feature_evidence": {
                            "condition_evidence": {"condition_label": "strain", "strain_axis_confidence": 0.68},
                            "strain_structure_evidence": {
                                "Q_star_rel_mean": 1.032,
                                "phi_void_mean": 0.028,
                                "void_detected_frames": 4,
                            },
                        }
                    },
                },
            },
            output_dir=str(tmp_path / "output_b"),
        )

        runs = db.get_analysis_runs(batch_id)
        current = next(run for run in runs if run["id"] == current_run)
        window._current_technique = "saxs"
        window._current_submodule_id = "saxs.strain"
        window._current_filepath = str(data_file.resolve())
        window._results["saxs"] = {
            "parameters": {"Q_star_rel_mean": 1.032, "phi_void_mean": 0.028, "void_detected_frames": 4},
            "analysis_evidence": current["results_summary"]["result"]["analysis_evidence"],
            "results_summary": current["results_summary"],
            "technique": "saxs",
            "submodule": "saxs.strain",
        }
        summary = window._result_comparison_summary()

        assert baseline_run != current_run
        assert "Q_star_rel_mean" in summary
        assert "phi_void_mean" in summary
        assert "void_detected_frames" in summary
        assert "r_squared" not in summary

        db.close()
        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_history_compare_uses_temperature_saxs_lc_fields(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "temp_history.csv"
        data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

        window = MainWindow()
        window._sample_db = SampleDB(tmp_path / "samples.db")
        db = window._ensure_sample_db()

        sample_id = db.create_sample("PA6")
        batch_id = db.create_batch(
            sample_id,
            "temp-01",
            instrument="SAXS",
            condition_type="analysis",
            condition_values={"technique": "saxs"},
        )
        db.add_data_file(
            batch_id,
            str(data_file.resolve()),
            "saxs",
            file_type="csv",
            import_order=0,
        )
        baseline_run = db.create_analysis_run(
            batch_id,
            "saxs",
            submodule="saxs.temperature",
            parameters={
                "lc_nm": 1.45,
                "lc_reliability_status": "usable",
                "melting_window_status": "outside_window",
                "Tm_onset_C": 195.0,
                "Tm_peak_C": 205.0,
                "Tm_end_C": 220.0,
            },
            results_summary={
                "data_file": str(data_file.resolve()),
                "result": {
                    "parameters": {
                        "lc_nm": 1.45,
                        "lc_reliability_status": "usable",
                        "melting_window_status": "outside_window",
                        "Tm_onset_C": 195.0,
                        "Tm_peak_C": 205.0,
                        "Tm_end_C": 220.0,
                    }
                },
            },
            output_dir=str(tmp_path / "output_a"),
        )
        current_run = db.create_analysis_run(
            batch_id,
            "saxs",
            submodule="saxs.temperature",
            parameters={
                "lc_nm": 1.23,
                "lc_reliability_status": "diagnostic_only",
                "melting_window_status": "within_window",
                "Tm_onset_C": 195.0,
                "Tm_peak_C": 205.0,
                "Tm_end_C": 220.0,
            },
            results_summary={
                "data_file": str(data_file.resolve()),
                "result": {
                    "parameters": {
                        "lc_nm": 1.23,
                        "lc_reliability_status": "diagnostic_only",
                        "melting_window_status": "within_window",
                        "Tm_onset_C": 195.0,
                        "Tm_peak_C": 205.0,
                        "Tm_end_C": 220.0,
                    }
                },
            },
            output_dir=str(tmp_path / "output_b"),
        )

        runs = db.get_analysis_runs(batch_id)
        current = next(run for run in runs if run["id"] == current_run)
        window._current_technique = "saxs"
        window._current_submodule_id = "saxs.temperature"
        window._current_filepath = str(data_file.resolve())
        window._results["saxs"] = {
            "parameters": {
                "lc_nm": 1.23,
                "lc_reliability_status": "diagnostic_only",
                "melting_window_status": "within_window",
                "Tm_onset_C": 195.0,
                "Tm_peak_C": 205.0,
                "Tm_end_C": 220.0,
            },
            "analysis_evidence": current["results_summary"]["result"].get("analysis_evidence", {}),
            "results_summary": current["results_summary"],
            "technique": "saxs",
            "submodule": "saxs.temperature",
        }

        summary = window._result_comparison_summary()
        assert baseline_run != current_run
        assert "lc_nm" in summary
        assert "lc_reliability_status" in summary
        assert "melting_window_status" in summary
        assert "r_squared" not in summary

        db.close()
        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_history_table_shows_metric_summary_in_tooltips(tmp_path):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "history.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    window = MainWindow()
    window._sample_db = SampleDB(tmp_path / "samples.db")
    db = window._ensure_sample_db()

    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(
        sample_id,
        "annealed-01",
        instrument="SAXS",
        condition_type="analysis",
        condition_values={"technique": "saxs"},
    )
    db.add_data_file(
        batch_id,
        str(data_file.resolve()),
        "saxs",
        file_type="csv",
        import_order=0,
    )
    db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        parameters={"baseline_method": "subtract"},
        results_summary={
            "data_file": str(data_file.resolve()),
            "result": {"parameters": {"extra_tag": "A", "Xc_pct": 0.35, "lc_nm": 5.8, "L_nm": 12.0}},
        },
        output_dir=str(tmp_path / "output_b"),
    )

    window._refresh_history()

    tooltip_time = window._history_table.item(0, 0).toolTip()
    tooltip_r2 = window._history_table.item(0, 3).toolTip()
    assert tooltip_time == "lc_nm=5.8 | Xc_pct=0.35 | L_nm=12.0 | extra_tag=A"
    assert tooltip_r2 == tooltip_time

    db.close()
    window.deleteLater()
    app.processEvents()


def test_history_table_metric_summary_ignores_validation_fields(tmp_path):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "history.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    window = MainWindow()
    window._sample_db = SampleDB(tmp_path / "samples.db")
    db = window._ensure_sample_db()

    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(
        sample_id,
        "annealed-01",
        instrument="SAXS",
        condition_type="analysis",
        condition_values={"technique": "saxs"},
    )
    db.add_data_file(
        batch_id,
        str(data_file.resolve()),
        "saxs",
        file_type="csv",
        import_order=0,
    )
    db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        parameters={
            "baseline_method": "subtract",
            "validation_summary": "WARN: synthetic drift",
            "validation_warnings": ["scan1/Tg"],
            "quality_flags": {"scan1/Tg": "WARN"},
        },
        results_summary={
            "data_file": str(data_file.resolve()),
            "result": {
                "parameters": {
                    "extra_tag": "A",
                    "Xc_pct": 0.35,
                    "lc_nm": 5.8,
                    "L_nm": 12.0,
                    "validation_summary": "WARN: synthetic drift",
                    "validation_warnings": ["scan1/Tg"],
                    "quality_flags": {"scan1/Tg": "WARN"},
                }
            },
        },
        output_dir=str(tmp_path / "output_b"),
    )

    window._refresh_history()

    tooltip_time = window._history_table.item(0, 0).toolTip()
    assert tooltip_time == "lc_nm=5.8 | Xc_pct=0.35 | L_nm=12.0 | extra_tag=A"
    assert "validation_summary" not in tooltip_time.lower()

    db.close()
    window.deleteLater()
    app.processEvents()


def test_waxs_history_tooltip_surfaces_core_and_support_scores(tmp_path):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "waxs.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    window = MainWindow()
    window._sample_db = SampleDB(tmp_path / "samples.db")
    db = window._ensure_sample_db()

    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(
        sample_id,
        "waxs-01",
        instrument="WAXS",
        condition_type="analysis",
        condition_values={"technique": "waxs"},
    )
    db.add_data_file(
        batch_id,
        str(data_file.resolve()),
        "waxs",
        file_type="csv",
        import_order=0,
    )
    db.create_analysis_run(
        batch_id,
        "waxs",
        submodule="waxs.static",
        parameters={},
        results_summary={
            "data_file": str(data_file.resolve()),
            "result": {
                "parameters": {"n_peaks": 2, "Xc_pct": 69.6, "D_Scherrer_nm": 8.3},
                "analysis_evidence": {
                    "peak_support_score": 0.82,
                    "background_stability_score": 0.74,
                    "phase_support_score": 0.88,
                    "size_support_score": 0.79,
                    "waxs_support_score": 0.81,
                },
            },
        },
        output_dir=str(tmp_path / "output_waxs"),
    )

    window._refresh_history()
    tooltip = window._history_table.item(0, 0).toolTip()

    assert "n_peaks=2" in tooltip
    assert "Xc_pct=69.6" in tooltip
    assert "D_Scherrer_nm=8.3" in tooltip
    assert "peak_support_score=0.82" in tooltip
    assert "waxs_support_score=0.81" in tooltip

    db.close()
    window.deleteLater()
    app.processEvents()


def test_waxs_temperature_history_tooltip_surfaces_sequence_scores(tmp_path):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "waxs_temp.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    window = MainWindow()
    window._sample_db = SampleDB(tmp_path / "samples.db")
    db = window._ensure_sample_db()

    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(
        sample_id,
        "waxs-temp-01",
        instrument="WAXS",
        condition_type="analysis",
        condition_values={"technique": "waxs"},
    )
    db.add_data_file(
        batch_id,
        str(data_file.resolve()),
        "waxs",
        file_type="csv",
        import_order=0,
    )
    db.create_analysis_run(
        batch_id,
        "waxs",
        submodule="waxs.temperature",
        parameters={},
        results_summary={
            "data_file": str(data_file.resolve()),
            "result": {
                "parameters": {"n_peaks": 2, "Xc_pct": 69.6, "D_Scherrer_nm": 8.3},
                "analysis_evidence": {
                    "peak_support_score": 0.82,
                    "background_stability_score": 0.74,
                    "phase_support_score": 0.88,
                    "size_support_score": 0.79,
                    "waxs_support_score": 0.81,
                    "temperature_axis_confidence": 0.94,
                    "peak_family_continuity_score": 0.83,
                    "transition_support_score": 0.68,
                    "Xc_trend_support_score": 0.76,
                    "D_trend_support_score": 0.77,
                },
            },
        },
        output_dir=str(tmp_path / "output_waxs_temp"),
    )

    window._refresh_history()
    tooltip = window._history_table.item(0, 0).toolTip()

    assert "temperature_axis_confidence=0.94" in tooltip
    assert "peak_family_continuity_score=0.83" in tooltip
    assert "transition_support_score=0.68" in tooltip
    assert "Xc_trend_support_score=0.76" in tooltip

    db.close()
    window.deleteLater()
    app.processEvents()


def test_waxs_result_review_summary_surfaces_core_and_support(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_technique = "waxs"
        window._current_submodule_id = "waxs.static"
        window._current_filepath = str(tmp_path / "waxs.csv")
        window._results["waxs"] = {
            "parameters": {"n_peaks": 2, "Xc_pct": 69.6, "D_Scherrer_nm": 8.3},
            "results_summary": {
                "project_label": "PA6",
                "result_origin": "manual_run",
                "result": {
                    "parameters": {"n_peaks": 2, "Xc_pct": 69.6, "D_Scherrer_nm": 8.3},
                    "analysis_evidence": {
                        "peak_support_score": 0.82,
                        "background_stability_score": 0.74,
                        "phase_support_score": 0.88,
                        "size_support_score": 0.79,
                        "feature_evidence": {
                            "scherrer_trend_evidence": {
                                "D_trend_support_score": 0.77,
                                "D_trend_monotonicity": "decreasing",
                                "D_support_peak_count": 4,
                                "instrument_broadening_present": True,
                            }
                        },
                        "waxs_support_score": 0.81,
                        "structure_evidence": {
                            "fit_only_pass": True,
                            "physical_support_pass": True,
                            "paper_ready_candidate": True,
                            "structure_support_score": 0.84,
                        },
                    },
                },
            },
        }

        summary = window._result_review_summary()
        source_summary = window._result_source_summary_text()
        window._update_results_review_panel()

        assert "WAXS core" in summary
        assert "WAXS support" in summary
        assert "Measured peak support" in summary
        assert "Crystallinity estimate" in summary
        assert "Crystallite size trend" in summary
        assert "paper-ready candidate" in summary.lower()
        assert "waxs_support_score=0.81" in source_summary
        assert "D_trend=0.770" in source_summary
        assert not window._results_review_trend.isHidden()
        assert "WAXS trend" in window._results_review_trend.text()
        assert "score=0.770" in window._results_review_trend.text()
        assert "mode=decreasing" in window._results_review_trend.text()

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_waxs_temperature_result_review_summary_surfaces_sequence_support(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_technique = "waxs"
        window._current_submodule_id = "waxs.temperature"
        window._current_filepath = str(tmp_path / "waxs_temp.csv")
        window._results["waxs"] = {
            "parameters": {"n_peaks": 2, "Xc_pct": 69.6, "D_Scherrer_nm": 8.3},
            "results_summary": {
                "project_label": "PA6",
                "result_origin": "manual_run",
                "result": {
                    "parameters": {"n_peaks": 2, "Xc_pct": 69.6, "D_Scherrer_nm": 8.3},
                    "analysis_evidence": {
                        "peak_support_score": 0.82,
                        "background_stability_score": 0.74,
                        "phase_support_score": 0.88,
                        "size_support_score": 0.79,
                        "waxs_support_score": 0.81,
                        "feature_evidence": {
                            "sequence_evidence": {"temperature_axis_confidence": 0.94},
                            "peak_family_evidence": {"peak_family_continuity_score": 0.83},
                            "trend_evidence": {"Xc_trend_support_score": 0.76},
                            "scherrer_trend_evidence": {
                                "D_trend_support_score": 0.77,
                                "D_trend_monotonicity": "decreasing",
                                "D_support_peak_count": 4,
                                "instrument_broadening_present": True,
                            },
                            "transition_evidence": {
                                "transition_support_score": 0.68,
                                "transition_candidate_count": 2,
                            },
                        },
                        "structure_evidence": {
                            "fit_only_pass": True,
                            "physical_support_pass": True,
                            "paper_ready_candidate": True,
                            "structure_support_score": 0.84,
                        },
                    },
                },
            },
        }

        window._update_results_review_panel()
        review_text = window._result_review_summary()

        assert "Temperature sequence" in review_text
        assert "axis=0.940" in review_text
        assert "family=0.830" in review_text
        assert "Xc=0.760" in review_text
        assert "transition=0.680" in review_text
        assert "WAXS trend" in window._results_review_trend.text()
        assert "axis=0.940" in window._results_review_trend.text()
        assert "transition=0.680" in window._results_review_trend.text()

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_waxs_result_risk_summary_respects_d_trend_support(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_technique = "waxs"
        window._current_submodule_id = "waxs.temperature"
        window._current_filepath = str(tmp_path / "waxs_temp.csv")
        window._results["waxs"] = {
            "parameters": {"n_peaks": 2, "Xc_pct": 52.1, "D_Scherrer_nm": 8.7},
            "results_summary": {
                "project_label": "PA6",
                "result_origin": "manual_run",
                "result": {
                    "parameters": {"n_peaks": 2, "Xc_pct": 52.1, "D_Scherrer_nm": 8.7},
                    "analysis_evidence": {
                        "peak_support_score": 0.82,
                        "background_stability_score": 0.74,
                        "phase_support_score": 0.88,
                        "size_support_score": 0.79,
                        "D_trend_support_score": 0.42,
                        "waxs_support_score": 0.81,
                        "structure_evidence": {
                            "fit_only_pass": True,
                            "physical_support_pass": True,
                            "paper_ready_candidate": True,
                            "structure_support_score": 0.84,
                        },
                    },
                },
            },
        }

        risk_text = window._results_risk_summary_text(window._results["waxs"]["parameters"])
        assert risk_text == tr("RESULTS_SUMMARY_RISK_WAXS_LIMITED")

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_dsc_result_review_summary_surfaces_measured_support_and_paper_state(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_technique = "dsc"
        window._current_submodule_id = "dsc.standard"
        window._current_filepath = str(tmp_path / "dsc.csv")
        dsc_evidence = {
            "feature_evidence": {
                "thermal_event_evidence": {
                    "scan_mode": "heating",
                    "exo_up": True,
                    "Tg_C": 50.0,
                    "Tm_peak_C": 222.4,
                    "Tcc_peak_C": 177.0,
                    "DHm_Jg": 52.0,
                    "Xc_pct": 32.0,
                },
                "event_support_evidence": {
                    "event_support_score": 0.84,
                    "baseline_stability_score": 0.76,
                    "thermodynamic_consistency_score": 0.81,
                    "supported_event_fraction": 0.67,
                    "scan_r_squared_median": 0.93,
                },
                "baseline_evidence": {
                    "baseline_corr": "poly",
                    "residual_type": "random",
                },
                "structure_evidence": {
                    "paper_conclusion_candidate": True,
                    "paper_conclusion_ready": False,
                },
            }
        }
        window._results["dsc"] = {
            "parameters": {
                "Tg_C": 50.0,
                "Tm_peak_C": 222.4,
                "Tcc_peak_C": 177.0,
                "DHm_Jg": 52.0,
                "Xc_pct": 32.0,
            },
            "analysis_evidence": dsc_evidence,
            "results_summary": {
                "project_label": "PA6",
                "result_origin": "manual_run",
                "result": {
                    "parameters": {
                        "Tg_C": 50.0,
                        "Tm_peak_C": 222.4,
                        "Tcc_peak_C": 177.0,
                        "DHm_Jg": 52.0,
                        "Xc_pct": 32.0,
                    },
                    "analysis_evidence": dsc_evidence,
                },
            },
        }

        summary = window._result_review_summary()
        source_summary = window._result_source_summary_text()
        measured_text = window._measured_result_summary_text()

        assert "Measured result" in summary
        assert "Tg_C=50.0" in summary
        assert "Measured result" in measured_text
        assert "Tg_C=50.0" in measured_text
        assert "Support chain" in summary
        assert "paper-ready candidate" in summary.lower()
        assert "core=Tg_C=50.0" in source_summary
        assert "Support chain" in source_summary
        assert "Conclusion state" in source_summary
        assert "paper-ready candidate" in source_summary.lower()

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_dsc_risk_summary_and_next_step_surface_support_gap(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_technique = "dsc"
        window._current_submodule_id = "dsc.standard"
        window._current_filepath = str(tmp_path / "dsc.csv")
        low_support_evidence = {
            "feature_evidence": {
                "event_support_evidence": {
                    "event_support_score": 0.61,
                    "baseline_stability_score": 0.58,
                    "thermodynamic_consistency_score": 0.63,
                },
                "structure_evidence": {
                    "paper_conclusion_candidate": False,
                    "paper_conclusion_ready": False,
                },
            }
        }
        window._results["dsc"] = {
            "parameters": {"Tg_C": 50.0, "Tm_peak_C": 222.4},
            "analysis_evidence": low_support_evidence,
            "results_summary": {
                "project_label": "PA6",
                "result_origin": "manual_run",
                "result": {"parameters": {"Tg_C": 50.0, "Tm_peak_C": 222.4}, "analysis_evidence": low_support_evidence},
            },
        }

        result = type("Result", (), {"validation_summary": ""})()
        risk = window._results_risk_summary_text({"Tg_C": 50.0}, result)
        next_step = window._results_next_step_text({"Tg_C": 50.0}, result)

        assert risk == tr("RESULTS_SUMMARY_RISK_DSC_LIMITED")
        assert next_step == tr("RESULTS_SUMMARY_NEXT_DSC_RISK")

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_finished_shows_waxs_risk_summary_when_physical_support_is_limited():
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._current_technique = "waxs"
        window._on_submodule_selected("waxs", "waxs.static")

        result = type(
            "Result",
            (),
            {
                "parameters": {
                    "n_peaks": 1,
                    "Xc_pct": 63.5,
                    "D_Scherrer_nm": 8.3,
                    "validation_summary": "",
                    "analysis_evidence": {
                        "peak_support_score": 0.52,
                        "background_stability_score": 0.66,
                        "phase_support_score": 0.58,
                        "size_support_score": 0.44,
                        "waxs_support_score": 0.57,
                        "constraint_summary": {"status": "soft_warn"},
                        "structure_evidence": {
                            "fit_only_pass": True,
                            "physical_support_pass": False,
                            "paper_ready_candidate": False,
                            "structure_support_score": 0.49,
                        },
                    },
                },
                "validation_summary": "",
                "validation_warnings": [],
                "quality_flags": {},
            },
        )()

        with patch.object(window, "_populate_plots"):
            with patch.object(window, "_persist_analysis_run"):
                window._on_finished(result)

        assert window._results_summary_risk_label.text() == tr("RESULTS_SUMMARY_RISK_WAXS_LIMITED")
        assert window._results_summary_next_label.text() == tr("RESULTS_SUMMARY_NEXT_WAXS_RISK")
        assert "Physical support still limited" in window._result_review_summary()
        assert "Figure usable, conclusion pending" in window._result_review_summary()

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_history_copy_summary_copies_selected_record_summary(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "history.csv"
        data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

        window = MainWindow()
        window._sample_db = SampleDB(tmp_path / "samples.db")
        db = window._ensure_sample_db()

        sample_id = db.create_sample("PA6")
        batch_id = db.create_batch(
            sample_id,
            "annealed-01",
            instrument="SAXS",
            condition_type="analysis",
            condition_values={"technique": "saxs"},
        )
        db.add_data_file(
            batch_id,
            str(data_file.resolve()),
            "saxs",
            file_type="csv",
            import_order=0,
        )
        db.create_analysis_run(
            batch_id,
            "saxs",
            submodule="saxs.static",
            parameters={"baseline_method": "subtract"},
            results_summary={
                "data_file": str(data_file.resolve()),
                "ai_tuned": True,
                "result_origin": "controlled_optimization_rerun",
                "result": {"parameters": {"extra_tag": "A", "Xc_pct": 0.35, "lc_nm": 5.8, "L_nm": 12.0}},
            },
            output_dir=str(tmp_path / "output_b"),
        )

        window._refresh_history()
        window._history_table.selectRow(0)
        app.processEvents()

        assert window._history_copy_summary_btn.isEnabled()
        window._copy_history_summary()

        text = QApplication.clipboard().text()
        assert "Static SAXS" in text
        assert "Recommended-parameter rerun" in text
        assert "Run trace" in text or "运行轨迹" in text
        assert "lc_nm=5.8 | Xc_pct=0.35 | L_nm=12.0 | extra_tag=A | baseline_method=subtract" in text
        assert "Boundary" in text
        assert "Copied history summary: Static SAXS" in window._log_panel.toPlainText()

        db.close()
        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_export_history_table_writes_current_history_rows(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "history.csv"
        data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

        window = MainWindow()
        window._sample_db = SampleDB(tmp_path / "samples.db")
        db = window._ensure_sample_db()

        sample_id = db.create_sample("PA6")
        batch_id = db.create_batch(
            sample_id,
            "annealed-01",
            instrument="SAXS",
            condition_type="analysis",
            condition_values={"technique": "saxs"},
        )
        db.add_data_file(
            batch_id,
            str(data_file.resolve()),
            "saxs",
            file_type="csv",
            import_order=0,
        )
        db.create_analysis_run(
            batch_id,
            "saxs",
            submodule="saxs.static",
            parameters={"baseline_method": "subtract"},
            results_summary={
                "data_file": str(data_file.resolve()),
                "ai_tuned": True,
                "result_origin": "controlled_optimization_rerun",
            },
            output_dir=str(tmp_path / "output_b"),
            ai_tuned=True,
        )

        export_path = tmp_path / "history_all.tsv"
        with patch("polynexus.gui.main_window.QFileDialog.getSaveFileName", return_value=(str(export_path), "TSV (*.tsv)")):
            window._export_history_table()

        text = export_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        assert lines[0] == "Time\tTechnique\tSubmodule\tR2\tStatus\tValidation\tConfirmed\tResult origin\tAI tuned\tSource data\tOutput dir"
        assert any("\tSAXS\t" in line and ("\tStatic SAXS\t" in line or "\tstatic\t" in line) for line in lines[1:])
        assert any("Recommended-parameter rerun\tYes\t" in line for line in lines[1:])
        with export_path.open("r", encoding="utf-8", newline="") as fh:
            rows = list(csv.reader(fh, delimiter="\t"))
        assert rows[1][6] == "Not confirmed"
        assert rows[1][7] == "Recommended-parameter rerun"
        assert rows[1][8] == "Yes"
        assert rows[1][9] == str(data_file.resolve())
        assert rows[1][10] == str(tmp_path / "output_b")
        assert f"Exported history list: {len(lines) - 1} rows ->" in window._log_panel.toPlainText()

        db.close()
        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_export_history_table_uses_history_export_service(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "history.csv"
        data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

        window = MainWindow()
        window._sample_db = SampleDB(tmp_path / "samples.db")
        db = window._ensure_sample_db()

        sample_id = db.create_sample("PA6")
        batch_id = db.create_batch(
            sample_id,
            "annealed-01",
            instrument="SAXS",
            condition_type="analysis",
            condition_values={"technique": "saxs"},
        )
        db.add_data_file(
            batch_id,
            str(data_file.resolve()),
            "saxs",
            file_type="csv",
            import_order=0,
        )
        db.create_analysis_run(
            batch_id,
            "saxs",
            submodule="saxs.static",
            parameters={"baseline_method": "subtract"},
            results_summary={"data_file": str(data_file.resolve())},
            output_dir=str(tmp_path / "output_b"),
        )

        export_calls = {}

        def fake_write_history_export_table(path, headers, matrix, *, selected_filter=""):
            export_calls["path"] = path
            export_calls["headers"] = list(headers)
            export_calls["matrix"] = [list(row) for row in matrix]
            export_calls["selected_filter"] = selected_filter
            return str(path)

        with patch("polynexus.gui.main_window.write_history_export_table", side_effect=fake_write_history_export_table, create=True), patch(
            "polynexus.gui.main_window.QFileDialog.getSaveFileName",
            return_value=(str(tmp_path / "history_all.tsv"), "TSV (*.tsv)"),
        ):
            window._export_history_table()

        assert export_calls["path"] == str(tmp_path / "history_all.tsv")
        assert export_calls["headers"][0] == "Time"
        assert export_calls["matrix"]
        assert export_calls["selected_filter"] == "TSV (*.tsv)"

        db.close()
        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_export_history_table_respects_active_filter(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "history.csv"
        data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

        window = MainWindow()
        window._sample_db = SampleDB(tmp_path / "samples.db")
        db = window._ensure_sample_db()

        sample_id = db.create_sample("PA6")
        batch_id = db.create_batch(
            sample_id,
            "annealed-01",
            instrument="Mixed",
            condition_type="analysis",
            condition_values={"technique": "mixed"},
        )
        db.add_data_file(
            batch_id,
            str(data_file.resolve()),
            "saxs",
            file_type="csv",
            import_order=0,
        )
        db.create_analysis_run(
            batch_id,
            "saxs",
            submodule="saxs.static",
            parameters={"baseline_method": "normalize"},
            results_summary={"data_file": str(data_file.resolve())},
            output_dir=str(tmp_path / "output_saxs"),
        )
        db.create_analysis_run(
            batch_id,
            "waxs",
            submodule="waxs.static",
            parameters={"baseline_method": "subtract"},
            results_summary={
                "data_file": str(data_file.resolve()),
                "ai_tuned": True,
                "result_origin": "controlled_optimization_rerun",
            },
            output_dir=str(tmp_path / "output_waxs"),
            ai_tuned=True,
        )

        window._refresh_history()
        idx = window._history_filter_combo.findData("waxs")
        window._history_filter_combo.setCurrentIndex(idx)
        app.processEvents()

        export_path = tmp_path / "history_waxs.csv"
        with patch("polynexus.gui.main_window.QFileDialog.getSaveFileName", return_value=(str(export_path), "CSV (*.csv)")):
            window._export_history_table()

        text = export_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        assert lines[0] == "Time,Technique,Submodule,R2,Status,Validation,Confirmed,Result origin,AI tuned,Source data,Output dir"
        assert len(lines) == 2
        assert ",WAXS,Static WAXS," in lines[1]
        assert ",Recommended-parameter rerun,Yes," in lines[1]
        with export_path.open("r", encoding="utf-8", newline="") as fh:
            rows = list(csv.reader(fh))
        assert rows[1][1] == "WAXS"
        assert rows[1][5] == ""
        assert rows[1][6] == "Not confirmed"
        assert rows[1][7] == "Recommended-parameter rerun"
        assert rows[1][8] == "Yes"
        assert rows[1][10] == str(tmp_path / "output_waxs")

        db.close()
        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_history_compare_button_requires_comparable_run(tmp_path):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "history.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    window = MainWindow()
    window._sample_db = SampleDB(tmp_path / "samples.db")
    db = window._ensure_sample_db()

    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(
        sample_id,
        "annealed-01",
        instrument="SAXS",
        condition_type="analysis",
        condition_values={"technique": "saxs"},
    )
    db.add_data_file(
        batch_id,
        str(data_file.resolve()),
        "saxs",
        file_type="csv",
        import_order=0,
    )
    db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        parameters={"baseline_method": "normalize"},
        results_summary={"data_file": str(data_file.resolve())},
        output_dir=str(tmp_path / "output_a"),
    )

    window._refresh_history()
    window._history_table.selectRow(0)
    window._update_history_action_state()
    assert not window._history_compare_btn.isEnabled()

    db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        parameters={"baseline_method": "subtract"},
        results_summary={"data_file": str(data_file.resolve())},
        output_dir=str(tmp_path / "output_b"),
    )

    window._refresh_history()
    window._history_table.selectRow(0)
    window._update_history_action_state()
    assert window._history_compare_btn.isEnabled()

    db.close()
    window.deleteLater()
    app.processEvents()


def test_history_compare_button_requires_same_submodule(tmp_path):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "history.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    window = MainWindow()
    window._sample_db = SampleDB(tmp_path / "samples.db")
    db = window._ensure_sample_db()

    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(
        sample_id,
        "annealed-01",
        instrument="SAXS",
        condition_type="analysis",
        condition_values={"technique": "saxs"},
    )
    db.add_data_file(
        batch_id,
        str(data_file.resolve()),
        "saxs",
        file_type="csv",
        import_order=0,
    )
    db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        parameters={"baseline_method": "normalize"},
        results_summary={"data_file": str(data_file.resolve())},
        output_dir=str(tmp_path / "output_a"),
    )
    db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.temperature",
        parameters={"baseline_method": "subtract"},
        results_summary={"data_file": str(data_file.resolve())},
        output_dir=str(tmp_path / "output_b"),
    )

    window._refresh_history()
    window._history_table.selectRow(0)
    window._update_history_action_state()

    assert not window._history_compare_btn.isEnabled()

    db.close()
    window.deleteLater()
    app.processEvents()


def test_history_action_tooltips_without_selection(tmp_path):
    app = QApplication.instance() or QApplication([])

    window = MainWindow()
    window._sample_db = SampleDB(tmp_path / "samples.db")
    window._refresh_history()
    window._update_history_action_state()

    assert not window._history_copy_summary_btn.isEnabled()
    assert window._history_copy_summary_btn.toolTip() == tr("HISTORY_TOOLTIP_SELECT")
    assert window._history_restore_btn.toolTip() == tr("HISTORY_TOOLTIP_SELECT")
    assert window._history_rerun_btn.toolTip() == tr("HISTORY_TOOLTIP_SELECT")
    assert window._history_compare_btn.toolTip() == tr("HISTORY_TOOLTIP_SELECT")

    window.deleteLater()
    app.processEvents()


def test_history_refresh_preserves_selected_run(tmp_path):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "history.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    window = MainWindow()
    window._sample_db = SampleDB(tmp_path / "samples.db")
    db = window._ensure_sample_db()

    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(
        sample_id,
        "annealed-01",
        instrument="SAXS",
        condition_type="analysis",
        condition_values={"technique": "saxs"},
    )
    db.add_data_file(
        batch_id,
        str(data_file.resolve()),
        "saxs",
        file_type="csv",
        import_order=0,
    )
    first_run = db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        parameters={"baseline_method": "normalize"},
        results_summary={"data_file": str(data_file.resolve())},
        output_dir=str(tmp_path / "output_a"),
    )
    second_run = db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        parameters={"baseline_method": "subtract"},
        results_summary={"data_file": str(data_file.resolve())},
        output_dir=str(tmp_path / "output_b"),
    )

    window._refresh_history()
    rows = getattr(window, "_history_cache", [])
    target_row = next(i for i, run in enumerate(rows) if run["id"] == first_run)
    window._history_table.selectRow(target_row)

    window._refresh_history()

    selected = window._selected_history_record()
    assert selected is not None
    assert selected["id"] == first_run
    assert second_run != first_run

    db.close()
    window.deleteLater()
    app.processEvents()


def test_history_restore_and_rerun_disable_when_source_file_missing(tmp_path):
    app = QApplication.instance() or QApplication([])

    missing_file = tmp_path / "missing.csv"

    window = MainWindow()
    window._sample_db = SampleDB(tmp_path / "samples.db")
    db = window._ensure_sample_db()

    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(
        sample_id,
        "annealed-01",
        instrument="SAXS",
        condition_type="analysis",
        condition_values={"technique": "saxs"},
    )
    db.add_data_file(
        batch_id,
        str(missing_file.resolve()),
        "saxs",
        file_type="csv",
        import_order=0,
    )
    db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        parameters={"baseline_method": "normalize"},
        results_summary={"data_file": str(missing_file.resolve())},
        output_dir=str(tmp_path / "output_a"),
    )

    window._refresh_history()
    window._history_table.selectRow(0)
    window._update_history_action_state()

    assert not window._history_restore_btn.isEnabled()
    assert not window._history_rerun_btn.isEnabled()
    assert tr("HISTORY_STATUS_SOURCE_MISSING") in window._history_table.item(0, 4).text()
    assert tr("HISTORY_STATUS_SOURCE_MISSING") in window._history_table.item(0, 4).toolTip()
    assert window._history_restore_btn.toolTip() == tr("HISTORY_TOOLTIP_SOURCE_MISSING")
    assert window._history_rerun_btn.toolTip() == tr("HISTORY_TOOLTIP_SOURCE_MISSING")

    db.close()
    window.deleteLater()
    app.processEvents()


def test_history_compare_tooltip_explains_missing_baseline(tmp_path):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "history.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    window = MainWindow()
    window._sample_db = SampleDB(tmp_path / "samples.db")
    db = window._ensure_sample_db()

    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(
        sample_id,
        "annealed-01",
        instrument="SAXS",
        condition_type="analysis",
        condition_values={"technique": "saxs"},
    )
    db.add_data_file(
        batch_id,
        str(data_file.resolve()),
        "saxs",
        file_type="csv",
        import_order=0,
    )
    db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        parameters={"baseline_method": "normalize"},
        results_summary={"data_file": str(data_file.resolve())},
        output_dir=str(tmp_path / "output_a"),
    )

    window._refresh_history()
    window._history_table.selectRow(0)
    window._update_history_action_state()

    assert not window._history_compare_btn.isEnabled()
    assert window._history_compare_btn.toolTip() == tr("HISTORY_TOOLTIP_COMPARE_UNAVAILABLE")

    db.close()
    window.deleteLater()
    app.processEvents()


def test_history_table_formats_timestamp_for_display(tmp_path):
    app = QApplication.instance() or QApplication([])

    tmp_path.mkdir(parents=True, exist_ok=True)
    data_file = tmp_path / "history.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    window = MainWindow()
    db_path = tmp_path / "samples.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    window._sample_db = SampleDB(db_path)
    db = window._ensure_sample_db()

    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(
        sample_id,
        "annealed-01",
        instrument="SAXS",
        condition_type="analysis",
        condition_values={"technique": "saxs"},
    )
    db.add_data_file(
        batch_id,
        str(data_file.resolve()),
        "saxs",
        file_type="csv",
        import_order=0,
    )
    run_id = db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        parameters={"baseline_method": "normalize"},
        results_summary={"data_file": str(data_file.resolve())},
        output_dir=str(tmp_path / "output_a"),
    )
    db._conn.execute(
        "UPDATE analysis_runs SET created_at=? WHERE id=?",
        ("2026-06-24 14:32:45", run_id),
    )
    db._conn.commit()

    window._refresh_history()

    assert window._history_table.item(0, 0).text() == "2026-06-24 14:32"

    db.close()
    window.deleteLater()
    app.processEvents()


def test_history_table_formats_submodule_for_display(tmp_path):
    app = QApplication.instance() or QApplication([])
    previous = get_language()

    try:
        set_language("en")
        data_file = tmp_path / "history.csv"
        data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

        window = MainWindow()
        window._sample_db = SampleDB(tmp_path / "samples.db")
        db = window._ensure_sample_db()

        sample_id = db.create_sample("PA6")
        batch_id = db.create_batch(
            sample_id,
            "annealed-01",
            instrument="SAXS",
            condition_type="analysis",
            condition_values={"technique": "saxs"},
        )
        db.add_data_file(
            batch_id,
            str(data_file.resolve()),
            "saxs",
            file_type="csv",
            import_order=0,
        )
        db.create_analysis_run(
            batch_id,
            "saxs",
            submodule="saxs.static",
            parameters={"baseline_method": "normalize"},
            results_summary={"data_file": str(data_file.resolve())},
            output_dir=str(tmp_path / "output_a"),
        )

        window._refresh_history()

        assert window._history_table.item(0, 2).text() == "Static SAXS"
        assert window._history_table.item(0, 2).toolTip() == "saxs.static"

        db.close()
        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_history_table_formats_technique_for_display(tmp_path):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "history.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    window = MainWindow()
    window._sample_db = SampleDB(tmp_path / "samples.db")
    db = window._ensure_sample_db()

    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(
        sample_id,
        "annealed-01",
        instrument="SAXS",
        condition_type="analysis",
        condition_values={"technique": "saxs"},
    )
    db.add_data_file(
        batch_id,
        str(data_file.resolve()),
        "saxs",
        file_type="csv",
        import_order=0,
    )
    db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        parameters={"baseline_method": "normalize"},
        results_summary={"data_file": str(data_file.resolve())},
        output_dir=str(tmp_path / "output_a"),
    )

    window._refresh_history()

    assert window._history_table.item(0, 1).text() == "SAXS"
    assert window._history_table.item(0, 1).toolTip() == "saxs"

    db.close()
    window.deleteLater()
    app.processEvents()


def test_history_table_formats_status_for_display(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "history.csv"
        data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

        window = MainWindow()
        window._sample_db = SampleDB(tmp_path / "samples.db")
        db = window._ensure_sample_db()

        sample_id = db.create_sample("PA6")
        batch_id = db.create_batch(
            sample_id,
            "annealed-01",
            instrument="SAXS",
            condition_type="analysis",
            condition_values={"technique": "saxs"},
        )
        db.add_data_file(
            batch_id,
            str(data_file.resolve()),
            "saxs",
            file_type="csv",
            import_order=0,
        )
        run_id = db.create_analysis_run(
            batch_id,
            "saxs",
            submodule="saxs.static",
            parameters={"baseline_method": "normalize"},
            results_summary={
                "data_file": str(data_file.resolve()),
                "ai_tuned": True,
                "result_origin": "controlled_optimization_rerun",
            },
            output_dir=str(tmp_path / "output_a"),
        )
        db.update_analysis_status(run_id, "pending")

        window._refresh_history()

        assert window._history_table.item(0, 4).text() == "Pending | Recommended-parameter rerun"
        assert window._history_table.item(0, 4).toolTip().startswith("pending")
        assert "baseline_method=normalize" in window._history_table.item(0, 4).toolTip()

        db.close()
        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_history_table_surfaces_saxs_lc_state_in_completed_rows(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "history_saxs.csv"
        data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

        window = MainWindow()
        window._sample_db = SampleDB(tmp_path / "samples_saxs.db")
        db = window._ensure_sample_db()

        sample_id = db.create_sample("PA6")
        batch_id = db.create_batch(
            sample_id,
            "temp-series",
            instrument="SAXS",
            condition_type="analysis",
            condition_values={"technique": "saxs"},
        )
        db.add_data_file(
            batch_id,
            str(data_file.resolve()),
            "saxs",
            file_type="csv",
            import_order=0,
        )
        db.create_analysis_run(
            batch_id,
            "saxs",
            submodule="saxs.temperature",
            parameters={
                "lc_nm": 1.23,
                "lc_method": "raw",
                "lc_reliability_status": "diagnostic_only",
                "lc_reliability_reason": "low_lc_confidence|within_melting_window",
                "calibration_skipped_reason": "missing_reference_crystallinity",
                "melting_window_status": "within_window",
            },
            results_summary={
                "data_file": str(data_file.resolve()),
                "project_label": "PA6",
                "result": {
                    "parameters": {
                        "lc_nm": 1.23,
                        "lc_method": "raw",
                        "lc_reliability_status": "diagnostic_only",
                        "lc_reliability_reason": "low_lc_confidence|within_melting_window",
                        "calibration_skipped_reason": "missing_reference_crystallinity",
                        "melting_window_status": "within_window",
                    }
                },
            },
            output_dir=str(tmp_path / "output_saxs"),
        )

        window._refresh_history()

        status_text = window._history_table.item(0, 4).text()
        status_tip = window._history_table.item(0, 4).toolTip()
        metrics_tip = window._history_table.item(0, 0).toolTip()

        assert "Completed" in status_text
        assert "diagnostic-only" in status_text
        assert "raw" in status_text
        assert "lc_method=raw" in status_tip
        assert "lc_reliability_status=diagnostic_only" in status_tip
        assert "calibration_skipped_reason=missing_reference_crystallinity" in status_tip
        assert "lc_method=raw" in metrics_tip

        db.close()
        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_history_table_item_activation_restores_record(tmp_path):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "history.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    window = MainWindow()
    window._sample_db = SampleDB(tmp_path / "samples.db")
    db = window._ensure_sample_db()

    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(
        sample_id,
        "annealed-01",
        instrument="SAXS",
        condition_type="analysis",
        condition_values={"technique": "saxs"},
    )
    db.add_data_file(
        batch_id,
        str(data_file.resolve()),
        "saxs",
        file_type="csv",
        import_order=0,
    )
    db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        parameters={"baseline_method": "subtract", "smooth_window": 11},
        results_summary={
            "data_file": str(data_file.resolve()),
            "project_label": "PA6",
            "r2": 0.95,
        },
        output_dir=str(tmp_path / "output"),
    )

    window._refresh_history()
    item = window._history_table.item(0, 0)
    window._history_table.itemActivated.emit(item)

    assert window._current_filepath == str(data_file.resolve())
    assert window._current_technique == "saxs"
    assert window._current_submodule_id == "saxs.static"

    db.close()
    window.deleteLater()
    app.processEvents()


def test_history_table_copy_shortcut_copies_selected_summary(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "history.csv"
        data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

        window = MainWindow()
        window._sample_db = SampleDB(tmp_path / "samples.db")
        db = window._ensure_sample_db()

        sample_id = db.create_sample("PA6")
        batch_id = db.create_batch(
            sample_id,
            "annealed-01",
            instrument="SAXS",
            condition_type="analysis",
            condition_values={"technique": "saxs"},
        )
        db.add_data_file(
            batch_id,
            str(data_file.resolve()),
            "saxs",
            file_type="csv",
            import_order=0,
        )
        db.create_analysis_run(
            batch_id,
            "saxs",
            submodule="saxs.static",
            parameters={"baseline_method": "subtract", "smooth_window": 11},
            results_summary={
                "data_file": str(data_file.resolve()),
                "project_label": "PA6",
                "r2": 0.95,
            },
            output_dir=str(tmp_path / "output"),
        )

        window._refresh_history()
        window._history_table.selectRow(0)
        window._history_copy_shortcut.activated.emit()

        text = QApplication.clipboard().text()
        assert "Static SAXS" in text
        assert "SAXS" in text
        assert "r2=0.95" in text

        db.close()
        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_history_filter_uses_display_name_and_filters_by_technique(tmp_path):
    app = QApplication.instance() or QApplication([])

    data_file = tmp_path / "history.csv"
    data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

    window = MainWindow()
    window._sample_db = SampleDB(tmp_path / "samples.db")
    db = window._ensure_sample_db()

    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(
        sample_id,
        "annealed-01",
        instrument="Mixed",
        condition_type="analysis",
        condition_values={"technique": "mixed"},
    )
    db.add_data_file(
        batch_id,
        str(data_file.resolve()),
        "saxs",
        file_type="csv",
        import_order=0,
    )
    db.create_analysis_run(
        batch_id,
        "saxs",
        submodule="saxs.static",
        parameters={"baseline_method": "normalize"},
        results_summary={"data_file": str(data_file.resolve())},
        output_dir=str(tmp_path / "output_saxs"),
    )
    db.create_analysis_run(
        batch_id,
        "waxs",
        submodule="waxs.static",
        parameters={"baseline_method": "subtract"},
        results_summary={"data_file": str(data_file.resolve())},
        output_dir=str(tmp_path / "output_waxs"),
    )

    window._refresh_history()

    assert window._history_filter_combo.itemText(1) == "SAXS"
    idx = window._history_filter_combo.findData("waxs")
    assert idx >= 0

    window._history_filter_combo.setCurrentIndex(idx)
    app.processEvents()

    assert window._history_filter_combo.currentText() == "WAXS"
    assert len(window._history_cache) == 1
    assert window._history_table.item(0, 1).text() == "WAXS"

    db.close()
    window.deleteLater()
    app.processEvents()


def test_history_table_shows_empty_state_without_records(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()
        window._sample_db = SampleDB(tmp_path / "samples.db")

        window._refresh_history()

        assert window._history_table.rowCount() == 1
        assert window._history_table.item(0, 0).text() == "No analysis history yet."
        assert not window._history_restore_btn.isEnabled()
        assert not window._history_rerun_btn.isEnabled()
        assert not window._history_compare_btn.isEnabled()

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_history_tab_and_score_header_use_translated_labels(tmp_path):
    app = QApplication.instance() or QApplication([])

    window = MainWindow()
    window._sample_db = SampleDB(tmp_path / "samples.db")

    assert window._tabs.tabText(window._tabs.count() - 1) == tr("TAB_HISTORY")
    assert window._history_table.horizontalHeaderItem(3).text() == "R2"
    assert window._log_group.title() == tr("GROUP_LOG")

    window.deleteLater()
    app.processEvents()


def test_history_table_shows_empty_state_for_active_filter(tmp_path):
    app = QApplication.instance() or QApplication([])
    previous = get_language()

    try:
        set_language("en")
        data_file = tmp_path / "history.csv"
        data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

        window = MainWindow()
        window._sample_db = SampleDB(tmp_path / "samples.db")
        db = window._ensure_sample_db()

        sample_id = db.create_sample("PA6")
        batch_id = db.create_batch(
            sample_id,
            "annealed-01",
            instrument="SAXS",
            condition_type="analysis",
            condition_values={"technique": "saxs"},
        )
        db.add_data_file(
            batch_id,
            str(data_file.resolve()),
            "saxs",
            file_type="csv",
            import_order=0,
        )
        db.create_analysis_run(
            batch_id,
            "saxs",
            submodule="saxs.static",
            parameters={"baseline_method": "normalize"},
            results_summary={"data_file": str(data_file.resolve())},
            output_dir=str(tmp_path / "output_a"),
        )

        window._refresh_history()
        idx = window._history_filter_combo.findData("waxs")
        assert idx >= 0
        window._history_filter_combo.setCurrentIndex(idx)
        app.processEvents()

        assert window._history_table.rowCount() == 1
        assert window._history_table.item(0, 0).text() == "No history records for WAXS."

        db.close()
        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_history_compare_summary_uses_formatted_timestamp(tmp_path):
    app = QApplication.instance() or QApplication([])

    window = MainWindow()

    captured = {}

    original_exec = QDialog.exec

    def fake_exec(dialog):
        layout = dialog.layout()
        captured["summary"] = layout.itemAt(0).widget().text()
        captured["counts"] = layout.itemAt(1).widget().text()
        return 0

    QDialog.exec = fake_exec
    try:
        window._show_history_comparison(
            {
                "created_at": "2026-06-24 14:32:45",
                "technique": "saxs",
                "submodule": "saxs.static",
                "results_summary": {"result": {"parameters": {}}},
            },
            {
                "created_at": "2026-06-23 09:05:01",
                "technique": "waxs",
                "submodule": "",
                "results_summary": {"result": {"parameters": {}}},
            },
        )
    finally:
        QDialog.exec = original_exec

    assert "2026-06-24 14:32" in captured["summary"]
    assert "2026-06-23 09:05" in captured["summary"]
    assert window._history_submodule_text("saxs.static") in captured["summary"]
    assert window._history_technique_text("waxs") in captured["summary"]
    assert captured["counts"] == tr("HISTORY_COMPARE_COUNTS", 0, 0, 0, 0)

    window.deleteLater()
    app.processEvents()


def test_main_window_reuses_history_compare_helpers_from_dedicated_service(tmp_path):
    compare_spec = importlib.util.find_spec("polynexus.gui.history_compare_service")
    assert compare_spec is not None

    history_compare_service = importlib.import_module("polynexus.gui.history_compare_service")
    window = MainWindow()

    assert window._history_compare_counts_text({}) == history_compare_service.history_compare_counts_text(window, {})
    assert window._history_compare_state_label("changed") == history_compare_service.history_compare_state_label(window, "changed")
    assert window._history_compare_state_color("same").name() == history_compare_service.history_compare_state_color(window, "same").name()

    window.deleteLater()


def test_main_window_reuses_result_review_summary_builder_from_service(tmp_path):
    review_service = importlib.import_module("polynexus.gui.results_review_service")

    assert (
        MainWindow._result_review_summary
        is review_service.build_result_review_summary_text_from_window
    )


def test_history_compare_dialog_sorts_changes_before_same(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()

        captured = {}

        original_exec = QDialog.exec

        def fake_exec(dialog):
            layout = dialog.layout()
            captured["counts"] = layout.itemAt(1).widget().text()
            table = layout.itemAt(2).widget()
            captured["rows"] = [
                (
                    table.item(row, 0).text(),
                    table.item(row, 1).toolTip(),
                    table.item(row, 2).toolTip(),
                    table.item(row, 3).text(),
                    table.item(row, 3).foreground().color().name(),
                    table.item(row, 3).toolTip(),
                )
                for row in range(table.rowCount())
            ]
            return 0

        QDialog.exec = fake_exec
        try:
            window._show_history_comparison(
                {
                    "created_at": "2026-06-24 14:32:45",
                    "results_summary": {
                        "result": {
                            "parameters": {
                                "same_metric": 1,
                                "changed_metric": 2,
                                "new_metric": 3,
                            }
                        }
                    },
                },
                {
                    "created_at": "2026-06-23 09:05:01",
                    "results_summary": {
                        "result": {
                            "parameters": {
                                "same_metric": 1,
                                "changed_metric": 5,
                                "removed_metric": 9,
                            }
                        }
                    },
                },
            )
        finally:
            QDialog.exec = original_exec

        assert captured["counts"] == "Changed 1 | New 1 | Removed 1 | Same 1"
        assert captured["rows"][0] == ("changed_metric", "2", "5", "Changed", "#2563eb", "Changed")
        assert captured["rows"][1] == ("new_metric", "3", "", "New", "#16a34a", "New")
        assert captured["rows"][2] == ("removed_metric", "", "9", "Removed", "#dc2626", "Removed")
        assert captured["rows"][3] == ("same_metric", "1", "1", "Same", "#555d7a", "Same")

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_history_compare_dialog_copy_button_copies_selected_row(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        window = MainWindow()

        captured = {}

        original_exec = QDialog.exec

        def fake_exec(dialog):
            layout = dialog.layout()
            table = layout.itemAt(2).widget()
            table.selectRow(0)
            assert dialog._history_compare_copy_button.text() == tr("COMMON_COPY")
            dialog._history_compare_copy_button.click()
            captured["text"] = QApplication.clipboard().text()
            return 0

        QDialog.exec = fake_exec
        try:
            window._show_history_comparison(
                {
                    "created_at": "2026-06-24 14:32:45",
                    "results_summary": {
                        "result": {
                            "parameters": {
                                "same_metric": 1,
                                "changed_metric": 2,
                                "new_metric": 3,
                            }
                        }
                    },
                },
                {
                    "created_at": "2026-06-23 09:05:01",
                    "results_summary": {
                        "result": {
                            "parameters": {
                                "same_metric": 1,
                                "changed_metric": 5,
                                "removed_metric": 9,
                            }
                        }
                    },
                },
            )
        finally:
            QDialog.exec = original_exec

        lines = captured["text"].splitlines()
        assert lines[0] == (
            f"{tr('HISTORY_COMPARE_COL_METRIC')}\t{tr('HISTORY_COMPARE_COL_CURRENT')}\t"
            f"{tr('HISTORY_COMPARE_COL_BASELINE')}\t{tr('HISTORY_COMPARE_COL_STATE')}"
        )
        assert lines[1] == "changed_metric\t2\t5\tChanged"
        assert len(lines) == 2

        window.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_results_compare_panel_prefers_same_sample_candidate(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "pa6_run.csv"
        data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

        window = MainWindow()
        db_path = tmp_path / "samples.db"
        if db_path.exists():
            db_path.unlink()
        window._sample_db = SampleDB(db_path)
        db = window._ensure_sample_db()

        sample_id = db.create_sample("PA6")
        same_batch = db.create_batch(
            sample_id,
            "same-sample",
            instrument="SAXS",
            condition_type="analysis",
            condition_values={"technique": "saxs"},
        )
        other_batch = db.create_batch(
            sample_id,
            "older-same-sample",
            instrument="SAXS",
            condition_type="analysis",
            condition_values={"technique": "saxs"},
        )
        other_sample_id = db.create_sample("PET")
        other_sample_batch = db.create_batch(
            other_sample_id,
            "other-sample",
            instrument="SAXS",
            condition_type="analysis",
            condition_values={"technique": "saxs"},
        )

        db.create_analysis_run(
            other_sample_batch,
            "saxs",
            submodule="saxs.static",
            parameters={"L_nm": 9.0},
            results_summary={"data_file": str(tmp_path / "pet.csv"), "project_label": "PET"},
            output_dir=str(tmp_path / "output_pet"),
        )
        db.create_analysis_run(
            other_batch,
            "saxs",
            submodule="saxs.static",
            parameters={"L_nm": 11.0},
            results_summary={"data_file": str(tmp_path / "pa6_old.csv"), "project_label": "PA6"},
            output_dir=str(tmp_path / "output_old"),
        )
        db.create_analysis_run(
            same_batch,
            "saxs",
            submodule="saxs.static",
            parameters={"L_nm": 12.0},
            results_summary={"data_file": str(data_file.resolve()), "project_label": "PA6"},
            output_dir=str(tmp_path / "output_same"),
        )

        window._current_technique = "saxs"
        window._current_submodule_id = "saxs.static"
        window._current_filepath = str(data_file)
        window._results["saxs"] = {
            "parameters": {"L_nm": 12.5},
            "results_summary": {"project_label": "PA6"},
        }
        window._joint_report = {
            "summary": "Cross-tech consistency for PA6: 1 errors, 2 warnings",
            "rows": [{"sample": "PA6", "batch": "batch-01"}],
            "validations": [
                {"severity": "WARN", "sample": "PA6", "batch": "batch-01", "check": "phi_c", "message": "needs review"},
                {"severity": "ERROR", "sample": "PA6", "batch": "batch-01", "check": "L_consistency", "message": "unstable"},
            ],
        }

        window._update_results_compare_panel()

        assert window._results_compare_group.isHidden() is False
        assert "PA6" in window._results_compare_baseline.text()
        assert "Static SAXS" in window._results_compare_current.text()
        assert window._results_compare_open_btn.isEnabled() is True
        assert window._results_compare_joint_btn.isHidden() is False
        assert "phi_c inconsistency" in window._results_compare_hint.text()
        assert "L consistency unstable" in window._results_compare_hint.text()
        assert "joint.compare" in window._results_compare_joint_btn.toolTip()

        baseline = window._current_result_comparison_baseline()
        assert baseline is not None
        assert baseline["output_dir"].endswith("output_same")

        window.deleteLater()
        db.close()
        app.processEvents()
    finally:
        set_language(previous)


def test_results_compare_panel_can_switch_selected_candidate(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "pa6_run.csv"
        data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

        window = MainWindow()
        db_path = tmp_path / "samples.db"
        if db_path.exists():
            db_path.unlink()
        window._sample_db = SampleDB(db_path)
        db = window._ensure_sample_db()

        sample_id = db.create_sample("PA6")
        first_batch = db.create_batch(
            sample_id,
            "first",
            instrument="SAXS",
            condition_type="analysis",
            condition_values={"technique": "saxs"},
        )
        second_batch = db.create_batch(
            sample_id,
            "second",
            instrument="SAXS",
            condition_type="analysis",
            condition_values={"technique": "saxs"},
        )
        first_run = db.create_analysis_run(
            first_batch,
            "saxs",
            submodule="saxs.static",
            parameters={"L_nm": 10.0},
            results_summary={"data_file": str(tmp_path / "pa6_a.csv"), "project_label": "PA6"},
            output_dir=str(tmp_path / "output_a"),
        )
        second_run = db.create_analysis_run(
            second_batch,
            "saxs",
            submodule="saxs.static",
            parameters={"L_nm": 13.0},
            results_summary={"data_file": str(tmp_path / "pa6_b.csv"), "project_label": "PA6"},
            output_dir=str(tmp_path / "output_b"),
        )

        window._current_technique = "saxs"
        window._current_submodule_id = "saxs.static"
        window._current_filepath = str(data_file)
        window._results["saxs"] = {
            "parameters": {"L_nm": 12.5},
            "results_summary": {"project_label": "PA6"},
        }

        window._update_results_compare_panel()
        assert window._results_compare_selector.count() == 2
        assert window._results_compare_selector.currentData() == first_run
        assert window._current_result_comparison_baseline()["id"] == first_run

        window._results_compare_selector.setCurrentIndex(1)
        assert window._results_compare_selector.currentData() == second_run
        assert window._current_result_comparison_baseline()["id"] == second_run

        window.deleteLater()
        db.close()
        app.processEvents()
    finally:
        set_language(previous)


def test_results_compare_selection_does_not_mutate_current_result(tmp_path):
    app = QApplication.instance() or QApplication([])

    previous = get_language()
    try:
        set_language("en")
        data_file = tmp_path / "pa6_run.csv"
        data_file.write_text("q,I\n0.1,1.0\n", encoding="utf-8")

        window = MainWindow()
        db_path = tmp_path / "samples.db"
        if db_path.exists():
            db_path.unlink()
        window._sample_db = SampleDB(db_path)
        db = window._ensure_sample_db()

        sample_id = db.create_sample("PA6")
        first_batch = db.create_batch(
            sample_id,
            "first",
            instrument="SAXS",
            condition_type="analysis",
            condition_values={"technique": "saxs"},
        )
        second_batch = db.create_batch(
            sample_id,
            "second",
            instrument="SAXS",
            condition_type="analysis",
            condition_values={"technique": "saxs"},
        )
        first_run = db.create_analysis_run(
            first_batch,
            "saxs",
            submodule="saxs.static",
            parameters={"L_nm": 10.0},
            results_summary={"data_file": str(tmp_path / "pa6_a.csv"), "project_label": "PA6"},
            output_dir=str(tmp_path / "output_a"),
        )
        second_run = db.create_analysis_run(
            second_batch,
            "saxs",
            submodule="saxs.static",
            parameters={"L_nm": 13.0},
            results_summary={"data_file": str(tmp_path / "pa6_b.csv"), "project_label": "PA6"},
            output_dir=str(tmp_path / "output_b"),
        )

        window._current_technique = "saxs"
        window._current_submodule_id = "saxs.static"
        window._current_filepath = str(data_file)
        window._current_result_confirmed_flag = True
        window._results["saxs"] = {
            "parameters": {"L_nm": 12.5},
            "results_summary": {"project_label": "PA6"},
        }
        current_snapshot = json.loads(json.dumps(window._results["saxs"]))

        window._update_results_compare_panel()
        assert window._current_result_comparison_baseline()["id"] == first_run

        window._results_compare_selector.setCurrentIndex(1)

        assert window._results_compare_selector.currentData() == second_run
        assert window._current_result_comparison_baseline()["id"] == second_run
        assert window._current_result_confirmed_flag is True
        assert window._results["saxs"] == current_snapshot

        window.deleteLater()
        db.close()
        app.processEvents()
    finally:
        set_language(previous)
