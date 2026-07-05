from __future__ import annotations

import json
from typing import Any


def _require_pyqt6():
    try:
        from PyQt6.QtWidgets import (
            QDialog,
            QHBoxLayout,
            QHeaderView,
            QPushButton,
            QTableWidget,
            QTableWidgetItem,
            QVBoxLayout,
        )
        return {
            "QDialog": QDialog,
            "QHBoxLayout": QHBoxLayout,
            "QHeaderView": QHeaderView,
            "QPushButton": QPushButton,
            "QTableWidget": QTableWidget,
            "QTableWidgetItem": QTableWidgetItem,
            "QVBoxLayout": QVBoxLayout,
        }
    except ModuleNotFoundError as exc:
        raise SystemExit("PyQt6 is required for this dialog. Install it with: pip install PyQt6") from exc


def _require_canvas():
    import matplotlib

    matplotlib.use("QtAgg")
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure

    return Figure, FigureCanvas


class TuningReportDialog:
    def __init__(self, report: dict[str, Any], parent: Any = None):
        qt = _require_pyqt6()
        Figure, FigureCanvas = _require_canvas()
        self.qt = qt
        self.report = report
        self.dialog = qt["QDialog"](parent)
        self.dialog.setWindowTitle("AI 调参报告")
        self.dialog.resize(820, 640)
        layout = qt["QVBoxLayout"](self.dialog)

        self.figure = Figure(figsize=(7, 3), tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        self.table = qt["QTableWidget"]()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["参数名", "原值", "新值", "LLM 原因"])
        self.table.horizontalHeader().setSectionResizeMode(qt["QHeaderView"].ResizeMode.Stretch)
        layout.addWidget(self.table)

        buttons = qt["QHBoxLayout"]()
        buttons.addStretch(1)
        self.apply_button = qt["QPushButton"]("应用最优参数")
        self.cancel_button = qt["QPushButton"]("取消")
        buttons.addWidget(self.apply_button)
        buttons.addWidget(self.cancel_button)
        layout.addLayout(buttons)

        self.apply_button.clicked.connect(self.dialog.accept)
        self.cancel_button.clicked.connect(self.dialog.reject)
        self._plot_scores()
        self._fill_changes()

    def exec(self) -> int:
        return self.dialog.exec()

    def best_config(self) -> dict[str, Any]:
        value = self.report.get("best_config") or {}
        return value if isinstance(value, dict) else {}

    def _plot_scores(self) -> None:
        ax = self.figure.add_subplot(111)
        history = self.report.get("history") or []
        r2_values: list[float] = []
        eval_values: list[float] = []
        if isinstance(history, list):
            for item in history:
                if not isinstance(item, dict):
                    continue
                r2 = _safe_float(item.get("r_squared_after", item.get("r_squared")))
                score = _safe_float(item.get("eval_score"))
                if r2 is not None:
                    r2_values.append(r2)
                if score is not None:
                    eval_values.append(score)
        if not r2_values and self.report.get("baseline_r_squared") is not None:
            r2_values = [float(self.report.get("baseline_r_squared"))]
            if self.report.get("best_r_squared") is not None:
                r2_values.append(float(self.report.get("best_r_squared")))
        if r2_values:
            ax.plot(range(len(r2_values)), r2_values, marker="o", label="r²")
        if eval_values:
            ax.plot(range(len(eval_values)), eval_values, marker="s", label="EvalScore")
        ax.set_xlabel("Round")
        ax.set_ylabel("Score")
        ax.grid(True, alpha=0.25)
        ax.legend(loc="best")
        self.canvas.draw_idle()

    def _fill_changes(self) -> None:
        rows = []
        history = self.report.get("history") or []
        if isinstance(history, list):
            for item in history:
                if not isinstance(item, dict):
                    continue
                changes = item.get("changes") or {}
                advice = item.get("llm_advice") if isinstance(item.get("llm_advice"), dict) else {}
                reason = str(advice.get("reasoning", ""))
                config = item.get("config_snapshot") if isinstance(item.get("config_snapshot"), dict) else {}
                if isinstance(changes, dict):
                    for key, new_value in changes.items():
                        rows.append((key, config.get(key, ""), new_value, reason))
        self.table.setRowCount(len(rows))
        for row, values in enumerate(rows):
            for col, value in enumerate(values):
                self.table.setItem(row, col, self.qt["QTableWidgetItem"](_stringify(value)))


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _stringify(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return "" if value is None else str(value)
