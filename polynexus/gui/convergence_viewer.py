from __future__ import annotations
import logging
logger = logging.getLogger(__name__)


import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.font_manager as fm

from .i18n import tr


def _set_chinese_font() -> None:
    candidates = [
        "Microsoft YaHei",
        "SimHei",
        "PingFang SC",
        "Noto Sans CJK SC",
        "WenQuanYi Micro Hei",
    ]
    available = {font.name for font in fm.fontManager.ttflist}
    for font in candidates:
        if font in available:
            matplotlib.rcParams["font.family"] = font
            matplotlib.rcParams["axes.unicode_minus"] = False
            return
    matplotlib.rcParams["axes.unicode_minus"] = False


_set_chinese_font()


DB_PATH = Path(__file__).resolve().parents[1] / "data" / "polynexus_samples.db"
ALL_TOKEN = "__all__"
AXIS_LABELS = {
    "waxs": "2θ (°)",
    "saxs": "q (nm⁻¹)",
    "ir": "Wavenumber (cm⁻¹)",
    "nmr": "ppm",
    "dsc": "T (°C)",
}


def _load_qt():
    if "PySide6.QtWidgets" in sys.modules:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (
            QApplication,
            QAbstractItemView,
            QComboBox,
            QFrame,
            QGridLayout,
            QHBoxLayout,
            QGroupBox,
            QHeaderView,
            QLabel,
            QMainWindow,
            QPushButton,
            QSplitter,
            QTableWidget,
            QTableWidgetItem,
            QVBoxLayout,
            QWidget,
        )

        return {
            "Qt": Qt,
            "QApplication": QApplication,
            "QAbstractItemView": QAbstractItemView,
            "QComboBox": QComboBox,
            "QFrame": QFrame,
            "QGridLayout": QGridLayout,
            "QHBoxLayout": QHBoxLayout,
            "QGroupBox": QGroupBox,
            "QHeaderView": QHeaderView,
            "QLabel": QLabel,
            "QMainWindow": QMainWindow,
            "QPushButton": QPushButton,
            "QSplitter": QSplitter,
            "QTableWidget": QTableWidget,
            "QTableWidgetItem": QTableWidgetItem,
            "QVBoxLayout": QVBoxLayout,
            "QWidget": QWidget,
        }

    try:
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import (
            QApplication,
            QAbstractItemView,
            QComboBox,
            QFrame,
            QGridLayout,
            QHBoxLayout,
            QGroupBox,
            QHeaderView,
            QLabel,
            QMainWindow,
            QPushButton,
            QSplitter,
            QTableWidget,
            QTableWidgetItem,
            QVBoxLayout,
            QWidget,
        )
    except ModuleNotFoundError:
        try:
            from PySide6.QtCore import Qt
            from PySide6.QtWidgets import (
                QApplication,
                QAbstractItemView,
                QComboBox,
                QFrame,
                QGridLayout,
                QHBoxLayout,
                QGroupBox,
                QHeaderView,
                QLabel,
                QMainWindow,
                QPushButton,
                QSplitter,
                QTableWidget,
                QTableWidgetItem,
                QVBoxLayout,
                QWidget,
            )
        except ModuleNotFoundError as exc:
            raise SystemExit(
                "PyQt6 is required for this view. Install it with: pip install PyQt6"
            ) from exc

    return {
        "Qt": Qt,
        "QApplication": QApplication,
        "QAbstractItemView": QAbstractItemView,
        "QComboBox": QComboBox,
        "QFrame": QFrame,
        "QGridLayout": QGridLayout,
        "QHBoxLayout": QHBoxLayout,
        "QGroupBox": QGroupBox,
        "QHeaderView": QHeaderView,
        "QLabel": QLabel,
        "QMainWindow": QMainWindow,
        "QPushButton": QPushButton,
        "QSplitter": QSplitter,
        "QTableWidget": QTableWidget,
        "QTableWidgetItem": QTableWidgetItem,
        "QVBoxLayout": QVBoxLayout,
        "QWidget": QWidget,
    }


QT = _load_qt()
Qt = QT["Qt"]
QApplication = QT["QApplication"]
QAbstractItemView = QT["QAbstractItemView"]
QComboBox = QT["QComboBox"]
QFrame = QT["QFrame"]
QGridLayout = QT["QGridLayout"]
QHBoxLayout = QT["QHBoxLayout"]
QGroupBox = QT["QGroupBox"]
QHeaderView = QT["QHeaderView"]
QLabel = QT["QLabel"]
QMainWindow = QT["QMainWindow"]
QPushButton = QT["QPushButton"]
QSplitter = QT["QSplitter"]
QTableWidget = QT["QTableWidget"]
QTableWidgetItem = QT["QTableWidgetItem"]
QVBoxLayout = QT["QVBoxLayout"]
QWidget = QT["QWidget"]


def _load_canvas():
    matplotlib.use("QtAgg", force=False)
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure

    return Figure, FigureCanvas


Figure, FigureCanvas = _load_canvas()


@dataclass
class TuneRun:
    run_id: str
    technique: str
    submodule: str
    polymer_name: str
    baseline_r2: float | None
    best_r2: float | None
    delta_r2: float | None
    round_history: list[float] = field(default_factory=list)
    residuals: dict[str, Any] = field(default_factory=dict)
    report_path: str = ""
    data_file: str = ""
    created_at: str = ""
    ai_tuned: bool = False
    confirmed: bool = False
    review_context: dict[str, Any] = field(default_factory=dict)


def _json_loads(value: Any, default: Any) -> Any:
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except Exception:
        logger.warning("Convergence viewer JSON field parse failed; returning default.", exc_info=True)
        return default


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_round_history(value: Any) -> list[float]:
    payload = _json_loads(value, value)
    if payload in (None, ""):
        return []
    if isinstance(payload, list):
        values: list[float] = []
        for item in payload:
            if isinstance(item, dict):
                candidate = (
                    item.get("r_squared_after")
                    or item.get("r_squared")
                    or item.get("eval_score")
                    or item.get("score")
                )
            else:
                candidate = item
            number = _safe_float(candidate)
            if number is not None:
                values.append(number)
        return values
    if isinstance(payload, dict):
        for key in ("r2", "r_squared", "scores", "eval_score", "history"):
            if key in payload:
                return parse_round_history(payload[key])
    return []


def _load_report(path: str) -> dict[str, Any]:
    if not path:
        return {}
    report_path = Path(path)
    if not report_path.exists():
        return {}
    try:
        return json.loads(report_path.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("Convergence viewer report load failed; returning empty report.", exc_info=True)
        return {}


def _extract_residuals(report: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    residuals = summary.get("residuals") or report.get("residuals") or {}
    if residuals:
        return residuals if isinstance(residuals, dict) else {}
    history = report.get("history") or []
    if isinstance(history, list):
        for item in reversed(history):
            if isinstance(item, dict) and item.get("residuals_pattern"):
                residual = item.get("residuals_pattern")
                return residual if isinstance(residual, dict) else {}
    return {}


def _review_context_from_summary(summary: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    summary = summary if isinstance(summary, dict) else {}
    report = report if isinstance(report, dict) else {}
    history_context = summary.get("history_context") if isinstance(summary.get("history_context"), dict) else {}
    history_context = history_context if isinstance(history_context, dict) else {}

    review_context = {
        "result_origin": str(summary.get("result_origin") or "").strip(),
        "result_origin_label": str(summary.get("result_origin_label") or "").strip(),
        "review_summary": str(history_context.get("review_summary") or summary.get("review_summary") or "").strip(),
        "work_memory_summary": str(history_context.get("work_memory_summary") or summary.get("work_memory_summary") or "").strip(),
        "comparison_summary": str(history_context.get("comparison_summary") or summary.get("comparison_summary") or "").strip(),
        "benchmark_text": str(history_context.get("benchmark_text") or summary.get("benchmark_text") or "").strip(),
        "validation_summary": str(history_context.get("validation_summary") or summary.get("validation_summary") or "").strip(),
        "joint_summary": str(history_context.get("joint_summary") or summary.get("joint_summary") or "").strip(),
        "responsibility_boundary": str(history_context.get("responsibility_boundary") or summary.get("responsibility_boundary") or "").strip(),
        "next_goal": str(history_context.get("next_goal") or summary.get("next_goal") or "").strip(),
        "remaining_risks": str(history_context.get("remaining_risks") or summary.get("remaining_risks") or "").strip(),
        "stop_reason": str(history_context.get("stop_reason") or summary.get("stop_reason") or "").strip(),
        "tuning_goal_label": str(history_context.get("tuning_goal_label") or summary.get("tuning_goal_label") or "").strip(),
        "reported_at": str(summary.get("reported_at") or report.get("reported_at") or "").strip(),
    }
    return {key: value for key, value in review_context.items() if value}


def _run_from_row(row: sqlite3.Row) -> TuneRun:
    summary = _json_loads(row["results_summary"], {})
    report_path = str(summary.get("report_path", ""))
    report = _load_report(report_path)
    polymer = str(summary.get("polymer_name") or report.get("polymer_name") or "unknown")
    baseline = _safe_float(
        summary.get("baseline_r_squared")
        or summary.get("baseline_r2")
        or report.get("baseline_r_squared")
    )
    best = _safe_float(
        summary.get("best_r_squared")
        or summary.get("best_r2")
        or report.get("best_r_squared")
    )
    delta = _safe_float(summary.get("delta_r2"))
    if delta is None and baseline is not None and best is not None:
        delta = best - baseline
    history = parse_round_history(summary.get("round_history"))
    if not history:
        history = parse_round_history(report.get("history"))
    if not history and baseline is not None:
        history = [baseline]
        if best is not None and best != baseline:
            history.append(best)
    submodule = str(summary.get("submodule") or report.get("submodule") or row["submodule"] or "")
    return TuneRun(
        run_id=str(row["id"]),
        technique=str(row["technique"] or ""),
        submodule=submodule,
        polymer_name=polymer,
        baseline_r2=baseline,
        best_r2=best,
        delta_r2=delta,
        round_history=history,
        residuals=_extract_residuals(report, summary),
        report_path=report_path,
        data_file=str(summary.get("data_file") or report.get("data_file") or ""),
        created_at=str(row["created_at"] or ""),
        ai_tuned=bool(row["ai_tuned"]),
        confirmed=bool(row["confirmed"]),
        review_context=_review_context_from_summary(summary, report),
    )


def load_ai_tune_runs(db_path: str | Path = DB_PATH) -> list[TuneRun]:
    path = Path(db_path)
    if not path.exists():
        return []
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM analysis_runs WHERE ai_tuned=1 ORDER BY created_at ASC"
        ).fetchall()
        return [_run_from_row(row) for row in rows]
    finally:
        conn.close()


def summarize_by_technique(runs: list[TuneRun]) -> list[dict[str, Any]]:
    grouped: dict[str, list[TuneRun]] = {}
    for run in runs:
        grouped.setdefault(run.technique, []).append(run)
    rows: list[dict[str, Any]] = []
    for technique, items in sorted(grouped.items()):
        baselines = [r.baseline_r2 for r in items if r.baseline_r2 is not None]
        bests = [r.best_r2 for r in items if r.best_r2 is not None]
        deltas = [r.delta_r2 for r in items if r.delta_r2 is not None]
        rows.append(
            {
                "technique": technique,
                "count": len(items),
                "avg_baseline_r2": sum(baselines) / len(baselines) if baselines else None,
                "avg_best_r2": sum(bests) / len(bests) if bests else None,
                "avg_delta_r2": sum(deltas) / len(deltas) if deltas else None,
                "submodules": _count_by_submodule(items),
            }
        )
    return rows


def _count_by_submodule(runs: list[TuneRun]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for run in runs:
        key = run.submodule or "unknown"
        counts[key] = counts.get(key, 0) + 1
    return counts


def _display_submodule_label(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "unknown"
    tail = text.split(".")[-1]
    return tail.replace("_", " ").replace("-", " ").strip() or "unknown"


def print_dry_run(db_path: str | Path = DB_PATH) -> None:
    runs = load_ai_tune_runs(db_path)
    print(f"ai_tuned_records={len(runs)}")
    for row in summarize_by_technique(runs):
        print(
            "{technique}: count={count}, avg_baseline_r2={base}, "
            "avg_best_r2={best}, avg_delta_r2={delta}, submodules={submodules}".format(
                technique=row["technique"],
                count=row["count"],
                base=_fmt(row["avg_baseline_r2"]),
                best=_fmt(row["avg_best_r2"]),
                delta=_fmt(row["avg_delta_r2"]),
                submodules=json.dumps(row["submodules"], ensure_ascii=False, sort_keys=True),
            )
        )


def _fmt(value: Any) -> str:
    if value is None:
        return "nan"
    try:
        return f"{float(value):.4f}"
    except Exception:
        logger.warning("Convergence viewer numeric formatting failed; using string fallback.", exc_info=True)
        return str(value)


class ConvergenceViewer(QMainWindow):
    def __init__(self, db_path: str | Path = DB_PATH, parent: Any = None):
        super().__init__(parent)
        self.db_path = Path(db_path)
        self.runs: list[TuneRun] = []
        self.filtered: list[TuneRun] = []
        self._selected_run_id = ""
        self._build()
        self.refresh_data()

    def _build(self) -> None:
        self.setWindowTitle(f"PolyNexus {tr('REVIEW_VIEWER_TITLE')}")
        self.resize(1280, 820)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(8)

        self._tech_label = QLabel(tr("REVIEW_FILTER_TECH"))
        self.tech_combo = QComboBox()
        self._sample_label = QLabel(tr("REVIEW_FILTER_SAMPLE"))
        self.polymer_combo = QComboBox()
        self._scope_label = QLabel(tr("REVIEW_FILTER_SCOPE"))
        self.submodule_combo = QComboBox()
        self.refresh_button = QPushButton(tr("REVIEW_REFRESH"))

        for label, combo in (
            (self._tech_label, self.tech_combo),
            (self._sample_label, self.polymer_combo),
            (self._scope_label, self.submodule_combo),
        ):
            toolbar.addWidget(label)
            toolbar.addWidget(combo, 1)
        toolbar.addWidget(self.refresh_button)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        self._overview_group = QGroupBox(tr("REVIEW_OVERVIEW_TITLE"))
        overview_layout = QGridLayout(self._overview_group)
        overview_layout.setContentsMargins(12, 10, 12, 10)
        overview_layout.setHorizontalSpacing(16)
        overview_layout.setVerticalSpacing(4)
        self._overview_total = QLabel("")
        self._overview_filtered = QLabel("")
        self._overview_confirmed = QLabel("")
        self._overview_ai = QLabel("")
        self._overview_best = QLabel("")
        for label in (self._overview_total, self._overview_filtered, self._overview_confirmed, self._overview_ai, self._overview_best):
            label.setWordWrap(True)
            label.setStyleSheet("color: #64748b;")
        overview_layout.addWidget(self._overview_total, 0, 0)
        overview_layout.addWidget(self._overview_filtered, 0, 1)
        overview_layout.addWidget(self._overview_confirmed, 0, 2)
        overview_layout.addWidget(self._overview_ai, 1, 0)
        overview_layout.addWidget(self._overview_best, 1, 1)
        layout.addWidget(self._overview_group)

        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setChildrenCollapsible(False)
        layout.addWidget(main_splitter, 2)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        self._selection_group = QGroupBox(tr("REVIEW_SELECTED_TITLE"))
        selection_layout = QVBoxLayout(self._selection_group)
        selection_layout.setContentsMargins(12, 10, 12, 10)
        selection_layout.setSpacing(6)
        self._selected_meta = QLabel(tr("REVIEW_SELECTED_EMPTY"))
        self._selected_meta.setWordWrap(True)
        self._selected_meta.setStyleSheet("color: #334155;")
        self._selected_metrics = QLabel("")
        self._selected_metrics.setWordWrap(True)
        self._selected_metrics.setStyleSheet("color: #64748b;")
        self._selected_context = QLabel("")
        self._selected_context.setWordWrap(True)
        self._selected_context.setStyleSheet("color: #64748b;")
        self._selected_trials = QLabel("")
        self._selected_trials.setWordWrap(True)
        self._selected_trials.setStyleSheet("color: #64748b;")
        self._selected_boundary = QLabel("")
        self._selected_boundary.setWordWrap(True)
        self._selected_boundary.setStyleSheet("color: #64748b;")
        self._selected_next = QLabel("")
        self._selected_next.setWordWrap(True)
        self._selected_next.setStyleSheet("color: #64748b;")
        self._selected_risk = QLabel("")
        self._selected_risk.setWordWrap(True)
        self._selected_risk.setStyleSheet("color: #64748b;")
        for widget in (
            self._selected_meta,
            self._selected_metrics,
            self._selected_context,
            self._selected_trials,
            self._selected_boundary,
            self._selected_risk,
            self._selected_next,
        ):
            selection_layout.addWidget(widget)
        left_layout.addWidget(self._selection_group)

        self._runs_group = QGroupBox(tr("REVIEW_RUNS_TITLE"))
        runs_layout = QVBoxLayout(self._runs_group)
        runs_layout.setContentsMargins(12, 10, 12, 10)
        runs_layout.setSpacing(6)
        self._runs_table = QTableWidget()
        self._runs_table.setColumnCount(8)
        self._runs_table.setHorizontalHeaderLabels([
            tr("REVIEW_TABLE_TIME"),
            tr("REVIEW_TABLE_SAMPLE"),
            tr("REVIEW_TABLE_SUBMODULE"),
            tr("REVIEW_TABLE_BASELINE"),
            tr("REVIEW_TABLE_BEST"),
            tr("REVIEW_TABLE_DELTA"),
            tr("REVIEW_TABLE_ORIGIN"),
            tr("REVIEW_TABLE_CONFIRMED"),
        ])
        self._runs_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._runs_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._runs_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._runs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self._runs_table.horizontalHeader().setStretchLastSection(True)
        self._runs_table.verticalHeader().setVisible(False)
        self._runs_table.setAlternatingRowColors(True)
        self._runs_table.itemSelectionChanged.connect(self._on_table_selection_changed)
        runs_layout.addWidget(self._runs_table)
        left_layout.addWidget(self._runs_group, 2)

        self._chart_group = QGroupBox(tr("REVIEW_CHARTS_TITLE"))
        chart_layout = QVBoxLayout(self._chart_group)
        chart_layout.setContentsMargins(12, 10, 12, 10)
        chart_layout.setSpacing(8)
        self.conv_fig = Figure(figsize=(6, 3.8), tight_layout=True)
        self.conv_canvas = FigureCanvas(self.conv_fig)
        self.resid_fig = Figure(figsize=(6, 3.8), tight_layout=True)
        self.resid_canvas = FigureCanvas(self.resid_fig)
        chart_layout.addWidget(self.conv_canvas, 1)
        chart_layout.addWidget(self.resid_canvas, 1)
        left_layout.addWidget(self._chart_group, 2)

        main_splitter.addWidget(left_panel)

        self._cards_group = QGroupBox(tr("REVIEW_SUMMARY_TITLE"))
        cards_layout = QVBoxLayout(self._cards_group)
        cards_layout.setContentsMargins(12, 10, 12, 10)
        cards_layout.setSpacing(8)
        self.cards = QWidget()
        self.cards_layout = QGridLayout(self.cards)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setHorizontalSpacing(12)
        self.cards_layout.setVerticalSpacing(12)
        cards_layout.addWidget(self.cards)
        main_splitter.addWidget(self._cards_group)
        main_splitter.setSizes([820, 320])

        self.tech_combo.currentTextChanged.connect(self._on_technique_changed)
        self.polymer_combo.currentTextChanged.connect(self.apply_filters)
        self.submodule_combo.currentTextChanged.connect(self.apply_filters)
        self.refresh_button.clicked.connect(self.refresh_data)
        self.conv_canvas.mpl_connect("pick_event", self._on_pick)
        self._refresh_static_labels()

    def retranslate(self) -> None:
        self.setWindowTitle(f"PolyNexus {tr('REVIEW_VIEWER_TITLE')}")
        if hasattr(self, "_tech_label"):
            self._tech_label.setText(tr("REVIEW_FILTER_TECH"))
        if hasattr(self, "_sample_label"):
            self._sample_label.setText(tr("REVIEW_FILTER_SAMPLE"))
        if hasattr(self, "_scope_label"):
            self._scope_label.setText(tr("REVIEW_FILTER_SCOPE"))
        if hasattr(self, "refresh_button"):
            self.refresh_button.setText(tr("REVIEW_REFRESH"))
        if hasattr(self, "tech_combo") and self.tech_combo.count():
            self.tech_combo.setItemText(0, tr("HISTORY_FILTER_ALL"))
        if hasattr(self, "polymer_combo") and self.polymer_combo.count():
            self.polymer_combo.setItemText(0, tr("HISTORY_FILTER_ALL"))
        if hasattr(self, "submodule_combo") and self.submodule_combo.count():
            self.submodule_combo.setItemText(0, tr("HISTORY_FILTER_ALL"))
        self._refresh_static_labels()
        self.apply_filters()

    def _refresh_static_labels(self) -> None:
        if hasattr(self, "_overview_group"):
            self._overview_group.setTitle(tr("REVIEW_OVERVIEW_TITLE"))
        if hasattr(self, "_selection_group"):
            self._selection_group.setTitle(tr("REVIEW_SELECTED_TITLE"))
        if hasattr(self, "_runs_group"):
            self._runs_group.setTitle(tr("REVIEW_RUNS_TITLE"))
        if hasattr(self, "_chart_group"):
            self._chart_group.setTitle(tr("REVIEW_CHARTS_TITLE"))
        if hasattr(self, "_cards_group"):
            self._cards_group.setTitle(tr("REVIEW_SUMMARY_TITLE"))
        if hasattr(self, "_runs_table"):
            self._runs_table.setHorizontalHeaderLabels([
                tr("REVIEW_TABLE_TIME"),
                tr("REVIEW_TABLE_SAMPLE"),
                tr("REVIEW_TABLE_SUBMODULE"),
                tr("REVIEW_TABLE_BASELINE"),
                tr("REVIEW_TABLE_BEST"),
                tr("REVIEW_TABLE_DELTA"),
                tr("REVIEW_TABLE_ORIGIN"),
                tr("REVIEW_TABLE_CONFIRMED"),
            ])

    def refresh_data(self, *_args) -> None:
        self.runs = load_ai_tune_runs(self.db_path)
        self._populate_filters()
        self._populate_overview()

    def _populate_filters(self) -> None:
        current_tech = self.tech_combo.currentData() if self.tech_combo.count() else ALL_TOKEN
        self.tech_combo.blockSignals(True)
        self.tech_combo.clear()
        self.tech_combo.addItem(tr("HISTORY_FILTER_ALL"), ALL_TOKEN)
        for value in sorted({r.technique for r in self.runs if r.technique}):
            self.tech_combo.addItem(value, value)
        idx = self.tech_combo.findData(current_tech)
        if idx < 0:
            idx = 0
        self.tech_combo.setCurrentIndex(idx)
        self.tech_combo.blockSignals(False)
        self._on_technique_changed()

    def _on_technique_changed(self, *_args) -> None:
        tech = str(self.tech_combo.currentData() or ALL_TOKEN)
        scoped = self.runs if tech in ("", ALL_TOKEN) else [r for r in self.runs if r.technique == tech]
        self._replace_combo(self.polymer_combo, sorted({r.polymer_name for r in scoped if r.polymer_name}))
        self._replace_combo(self.submodule_combo, sorted({r.submodule for r in scoped if r.submodule}))
        self.apply_filters()

    def _replace_combo(self, combo: Any, values: list[str]) -> None:
        current = combo.currentData() if combo.count() else ALL_TOKEN
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(tr("HISTORY_FILTER_ALL"), ALL_TOKEN)
        for value in values:
            combo.addItem(value, value)
        idx = combo.findData(current)
        if idx < 0:
            idx = 0
        combo.setCurrentIndex(idx)
        combo.blockSignals(False)

    def apply_filters(self, *_args) -> None:
        tech = str(self.tech_combo.currentData() or ALL_TOKEN)
        polymer = str(self.polymer_combo.currentData() or ALL_TOKEN)
        submodule = str(self.submodule_combo.currentData() or ALL_TOKEN)
        self.filtered = [
            run
            for run in self.runs
            if (tech in ("", ALL_TOKEN) or run.technique == tech)
            and (polymer in ("", ALL_TOKEN) or run.polymer_name == polymer)
            and (submodule in ("", ALL_TOKEN) or run.submodule == submodule)
        ]
        if self._selected_run_id and not any(run.run_id == self._selected_run_id for run in self.filtered):
            self._selected_run_id = ""
        self._plot_convergence()
        self._plot_residual(self._current_run())
        self._update_cards()
        self._populate_overview()
        self._populate_runs_table()
        self._sync_selection_from_filters()

    def _populate_overview(self) -> None:
        total = len(self.runs)
        filtered = len(self.filtered)
        confirmed = sum(1 for run in self.filtered if run.confirmed)
        ai_reruns = sum(1 for run in self.filtered if run.ai_tuned)
        best_delta = None
        for run in self.filtered:
            if run.delta_r2 is None:
                continue
            if best_delta is None or run.delta_r2 > best_delta:
                best_delta = run.delta_r2
        if hasattr(self, "_overview_total"):
            self._overview_total.setText(f"{tr('REVIEW_OVERVIEW_TOTAL')}: {total}")
        if hasattr(self, "_overview_filtered"):
            self._overview_filtered.setText(f"{tr('REVIEW_OVERVIEW_FILTERED')}: {filtered}")
        if hasattr(self, "_overview_confirmed"):
            self._overview_confirmed.setText(f"{tr('REVIEW_OVERVIEW_CONFIRMED')}: {confirmed}")
        if hasattr(self, "_overview_ai"):
            self._overview_ai.setText(f"{tr('REVIEW_OVERVIEW_AI')}: {ai_reruns}")
        if hasattr(self, "_overview_best"):
            self._overview_best.setText(f"{tr('REVIEW_OVERVIEW_BEST')}: {_fmt(best_delta)}")

    def _current_run(self) -> TuneRun | None:
        for run in self.filtered:
            if run.run_id == self._selected_run_id:
                return run
        return None

    def _sync_selection_from_filters(self) -> None:
        current = self._current_run()
        if current is None and self.filtered:
            current = self.filtered[0]
            self._selected_run_id = current.run_id
        if current is not None:
            self._select_run(current)
        else:
            self._update_selected_detail(None)

    def _populate_runs_table(self) -> None:
        if not hasattr(self, "_runs_table"):
            return
        rows = list(self.filtered)
        self._runs_table.blockSignals(True)
        self._runs_table.setRowCount(len(rows))
        for row_index, run in enumerate(rows):
            values = [
                run.created_at,
                run.polymer_name,
                _display_submodule_label(run.submodule),
                _fmt(run.baseline_r2),
                _fmt(run.best_r2),
                _fmt(run.delta_r2),
                str(run.review_context.get("result_origin_label") or run.review_context.get("result_origin") or ("AI rerun" if run.ai_tuned else "manual")).strip(),
                tr("REVIEW_OVERVIEW_CONFIRMED") if run.confirmed else tr("RESULTS_REVIEW_PENDING"),
            ]
            for col_index, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setToolTip(str(value))
                if col_index in (3, 4, 5):
                    item.setTextAlignment(int(Qt.AlignVCenter | Qt.AlignRight))
                self._runs_table.setItem(row_index, col_index, item)
        self._runs_table.blockSignals(False)
        if rows:
            self._runs_table.selectRow(0 if not self._selected_run_id else next((i for i, run in enumerate(rows) if run.run_id == self._selected_run_id), 0))

    def _on_table_selection_changed(self) -> None:
        if not hasattr(self, "_runs_table"):
            return
        row = self._runs_table.currentRow()
        if row < 0 or row >= len(self.filtered):
            self._update_selected_detail(None)
            return
        run = self.filtered[row]
        self._select_run(run)

    def _select_run(self, run: TuneRun) -> None:
        self._selected_run_id = run.run_id
        if hasattr(self, "_runs_table"):
            self._runs_table.blockSignals(True)
            rows = self._runs_table.rowCount()
            for idx in range(rows):
                run_id = self.filtered[idx].run_id if idx < len(self.filtered) else ""
                if run_id == run.run_id:
                    self._runs_table.selectRow(idx)
                    break
            self._runs_table.blockSignals(False)
        self._plot_residual(run)
        self._update_selected_detail(run)

    def _update_selected_detail(self, run: TuneRun | None) -> None:
        if not hasattr(self, "_selected_meta"):
            return
        if run is None:
            self._selected_meta.setText(tr("REVIEW_SELECTED_EMPTY"))
            self._selected_metrics.setText("")
            self._selected_context.setText("")
            self._selected_trials.setText("")
            self._selected_boundary.setText("")
            self._selected_risk.setText("")
            self._selected_next.setText("")
            return

        origin = run.review_context.get("result_origin_label") or run.review_context.get("result_origin") or ("AI rerun" if run.ai_tuned else "manual")
        status = tr("REVIEW_OVERVIEW_CONFIRMED") if run.confirmed else tr("RESULTS_REVIEW_PENDING")
        self._selected_meta.setText(f"{run.polymer_name} | {_display_submodule_label(run.submodule)} | {status} | {origin}")
        self._selected_metrics.setText(tr(
            "REVIEW_SELECTED_METRICS",
            "baseline={} | best={} | delta={}".format(_fmt(run.baseline_r2), _fmt(run.best_r2), _fmt(run.delta_r2)),
        ))
        issue_bits = [run.review_context.get("review_summary"), run.review_context.get("validation_summary")]
        issue_bits = [str(item).strip() for item in issue_bits if str(item).strip()]
        self._selected_context.setText(tr("REVIEW_SELECTED_CONTEXT", " | ".join(issue_bits) if issue_bits else tr("REVIEW_SELECTED_CONTEXT_EMPTY")))
        trial_bits = [run.review_context.get("benchmark_text"), run.review_context.get("comparison_summary")]
        trial_bits = [str(item).strip() for item in trial_bits if str(item).strip()]
        self._selected_trials.setText(tr("REVIEW_SELECTED_TRIALS", " | ".join(trial_bits) if trial_bits else tr("REVIEW_SELECTED_TRIALS_EMPTY")))
        boundary_bits = [run.review_context.get("responsibility_boundary"), run.review_context.get("joint_summary")]
        boundary_bits = [str(item).strip() for item in boundary_bits if str(item).strip()]
        self._selected_boundary.setText(tr("REVIEW_SELECTED_BOUNDARY", " | ".join(boundary_bits) if boundary_bits else tr("REVIEW_SELECTED_BOUNDARY_EMPTY")))
        risk_bits = [run.review_context.get("stop_reason"), run.review_context.get("remaining_risks")]
        risk_bits = [str(item).strip() for item in risk_bits if str(item).strip()]
        self._selected_risk.setText(tr("REVIEW_SELECTED_RISK", " | ".join(risk_bits) if risk_bits else tr("RESULTS_REVIEW_NO_RISK")))
        next_bits = [run.review_context.get("tuning_goal_label"), run.review_context.get("next_goal")]
        next_bits = [str(item).strip() for item in next_bits if str(item).strip()]
        self._selected_next.setText(tr("REVIEW_SELECTED_NEXT", " | ".join(next_bits) if next_bits else tr("REVIEW_SELECTED_NEXT_EMPTY")))

    def _select_run_by_id(self, run_id: str) -> None:
        if not run_id:
            return
        for idx, run in enumerate(self.filtered):
            if run.run_id == run_id:
                if hasattr(self, "_runs_table"):
                    self._runs_table.selectRow(idx)
                self._select_run(run)
                return

    def _run_label(self, run: TuneRun) -> str:
        submodule = _display_submodule_label(run.submodule)
        stem = Path(run.data_file).stem or Path(run.data_file).name or run.run_id
        return f"{submodule} · {stem}"

    def _plot_convergence(self) -> None:
        self.conv_fig.clear()
        ax = self.conv_fig.add_subplot(111)
        colors: dict[str, str] = {}
        palette = ["#2563eb", "#0f766e", "#d97706", "#dc2626", "#7c3aed", "#334155"]
        for run in self.filtered:
            color_key = run.submodule or run.technique or "unknown"
            colors.setdefault(color_key, palette[len(colors) % len(palette)])
            y = run.round_history or [v for v in [run.baseline_r2, run.best_r2] if v is not None]
            if not y:
                continue
            x = list(range(len(y)))
            label = self._run_label(run)
            if len(y) == 1:
                artist = ax.scatter(x, y, color=colors[color_key], label=label, picker=True)
            else:
                (artist,) = ax.plot(x, y, marker="o", color=colors[color_key], label=label, picker=5)
            artist._tune_run = run
        ax.set_title(tr("REVIEW_CONVERGENCE_TITLE"))
        ax.set_xlabel(tr("REVIEW_CONVERGENCE_X"))
        ax.set_ylabel(tr("REVIEW_CONVERGENCE_Y"))
        ax.grid(True, alpha=0.25)
        handles, labels = ax.get_legend_handles_labels()
        if labels and len(labels) <= 6:
            ax.legend(loc="upper left", fontsize=7, frameon=False)
        self.conv_canvas.draw_idle()

    def _on_pick(self, event: Any) -> None:
        run = getattr(event.artist, "_tune_run", None)
        if run is not None:
            self._select_run(run)

    def _plot_residual(self, run: TuneRun | None) -> None:
        self.resid_fig.clear()
        ax = self.resid_fig.add_subplot(111)
        if run is None:
            ax.set_title(tr("REVIEW_RESIDUAL_TITLE"))
            ax.text(0.5, 0.5, tr("REVIEW_RESIDUAL_HINT"), ha="center", va="center", transform=ax.transAxes)
            ax.axhline(0, color="#dc2626", linestyle="--", linewidth=1)
            self.resid_canvas.draw_idle()
            return
        x, y = self._residual_xy(run)
        if x and y:
            ax.plot(x, y, color="#475569", linewidth=1.5)
        ax.axhline(0, color="#dc2626", linestyle="--", linewidth=1)
        ax.set_title(f"{tr('REVIEW_RESIDUAL_TITLE')} · {Path(run.data_file).name}")
        ax.set_xlabel(AXIS_LABELS.get(run.technique, "x"))
        ax.set_ylabel(tr("REVIEW_RESIDUAL_Y"))
        ax.grid(True, alpha=0.25)
        self.resid_canvas.draw_idle()

    def _residual_xy(self, run: TuneRun) -> tuple[list[float], list[float]]:
        residuals = run.residuals or {}
        for x_key in ("x", "two_theta", "two_theta_deg", "q", "wavenumber", "ppm", "temperature"):
            for y_key in ("residuals", "residual", "y"):
                x = residuals.get(x_key)
                y = residuals.get(y_key)
                if isinstance(x, list) and isinstance(y, list):
                    return x, y
        regions = residuals.get("peak_regions")
        if isinstance(regions, list):
            x_values = []
            y_values = []
            for index, item in enumerate(regions):
                if not isinstance(item, dict):
                    continue
                x_values.append(float(item.get("center", item.get("ppm", item.get("two_theta", index)))))
                y_values.append(float(item.get("mean_residual", item.get("max_residual", 0.0))))
            return x_values, y_values
        return [], []

    def _update_cards(self) -> None:
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        rows = summarize_by_technique(self.filtered)
        if not rows:
            empty = QLabel(tr("RESULTS_EMPTY"))
            empty.setStyleSheet("color: #6b7280; padding: 8px 2px;")
            self.cards_layout.addWidget(empty, 0, 0)
            return
        for idx, row in enumerate(rows):
            card = self._make_card(row)
            self.cards_layout.addWidget(card, idx // 3, idx % 3)

    def _make_card(self, row: dict[str, Any]) -> Any:
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setObjectName("review_card")
        card.setMinimumHeight(112)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        title = QLabel(f"{row['technique'].upper()} {tr('REVIEW_CARD_COUNT', row['count'])}")
        title.setStyleSheet("font-weight: 600;")
        layout.addWidget(title)

        metrics = QLabel(
            tr(
                "REVIEW_CARD_METRICS",
                _fmt(row["avg_baseline_r2"]),
                _fmt(row["avg_best_r2"]),
                _fmt(row["avg_delta_r2"]),
            )
        )
        metrics.setWordWrap(True)
        layout.addWidget(metrics)

        detail = QLabel()
        detail.setWordWrap(True)
        submodules = row["submodules"]
        if submodules:
            ordered = sorted(submodules.items(), key=lambda item: (-item[1], item[0]))
            lines = [f"{_display_submodule_label(key)} {value}" for key, value in ordered[:4]]
            if len(ordered) > 4:
                lines.append(tr("REVIEW_CARD_MORE", len(ordered) - 4))
            detail.setText(" | ".join(lines))
        else:
            detail.setText(tr("REVIEW_CARD_NO_DETAILS"))
        detail.setStyleSheet("color: #6b7280;")
        layout.addWidget(detail)
        return card


def run_gui(db_path: str | Path = DB_PATH) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    viewer = ConvergenceViewer(db_path=db_path)
    viewer.show()
    return app.exec()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PolyNexus result review viewer")
    parser.add_argument("--db", default=str(DB_PATH), help="Path to polynexus_samples.db")
    parser.add_argument("--dry-run", action="store_true", help="Print review counts without opening a window")
    args = parser.parse_args(argv)
    if args.dry_run:
        print_dry_run(args.db)
        return 0
    return run_gui(args.db)


if __name__ == "__main__":
    raise SystemExit(main())
