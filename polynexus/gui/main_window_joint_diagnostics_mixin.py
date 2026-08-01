from __future__ import annotations

import json
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView, QTableWidgetItem

from .i18n import tr


class MainWindowJointDiagnosticsMixin:
    @staticmethod
    def _main_window_module():
        from . import main_window as main_window_module

        return main_window_module

    def _update_joint_diagnostics(self, report):
        group = getattr(self, "_joint_diagnostics_group", None)
        table = getattr(self, "_joint_diagnostics_table", None)

        if group is None or table is None:
            return

        rows = report.get("rows", [])
        validations = report.get("validations", [])
        warnings = [v for v in validations if v.get("severity") == "WARN"]
        errors = [v for v in validations if v.get("severity") == "ERROR"]
        issues = errors + warnings

        self._joint_metric_batches.setText(tr("JOINT_DIAG_BATCHES", len(rows)))
        self._joint_metric_checks.setText(tr("JOINT_DIAG_CHECKS", len(validations)))
        self._joint_metric_warnings.setText(tr("JOINT_DIAG_WARNINGS", len(warnings)))
        self._joint_metric_errors.setText(tr("JOINT_DIAG_ERRORS", len(errors)))

        headers = [
            tr("JOINT_DIAG_SEVERITY"),
            tr("JOINT_DIAG_SAMPLE"),
            tr("JOINT_DIAG_BATCH"),
            tr("JOINT_DIAG_CHECK"),
            tr("JOINT_DIAG_MESSAGE"),
        ]

        display_rows = issues[:12]
        if not display_rows and validations:
            display_rows = [
                {
                    "severity": "OK",
                    "sample": "-",
                    "batch": "-",
                    "check": "cross-technique",
                    "message": tr("JOINT_DIAG_NONE"),
                }
            ]

        table.setRowCount(len(display_rows))
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)

        for row_idx, item in enumerate(display_rows):
            values = [
                item.get("severity", ""),
                item.get("sample", ""),
                item.get("batch", ""),
                item.get("check", ""),
                item.get("message", ""),
            ]

            for col_idx, value in enumerate(values):
                cell = QTableWidgetItem(str(value))

                if col_idx == 0:
                    severity = str(value)
                    if severity == "ERROR":
                        cell.setForeground(Qt.red)
                    elif severity == "WARN":
                        cell.setForeground(Qt.darkYellow)
                    elif severity == "OK":
                        cell.setForeground(Qt.darkGreen)

                table.setItem(row_idx, col_idx, cell)

        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        table.horizontalHeader().setStretchLastSection(True)
        group.setVisible(True)

    def _hide_joint_diagnostics(self):
        group = getattr(self, "_joint_diagnostics_group", None)
        if group is not None:
            group.setVisible(False)

    def _save_joint_hub_artifacts(self, report):
        import csv
        import math

        main_window_module = self._main_window_module()

        data_dir = os.path.join(self._output_dir, "data")
        figures_dir = os.path.join(self._output_dir, "figures")

        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(figures_dir, exist_ok=True)

        def clean(value):
            if isinstance(value, float) and math.isnan(value):
                return ""
            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=False)
            return value

        def write_csv(path, rows):
            if not rows:
                return

            fieldnames = []
            for row in rows:
                for key in row.keys():
                    if key not in fieldnames:
                        fieldnames.append(key)

            with open(path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    writer.writerow({key: clean(row.get(key, "")) for key in fieldnames})

        write_csv(os.path.join(data_dir, "joint_hub_summary.csv"), report.get("rows", []))
        write_csv(
            os.path.join(data_dir, "joint_hub_source_preflight.csv"),
            report.get("source_preflight", []),
        )
        write_csv(
            os.path.join(data_dir, "joint_hub_validations.csv"),
            report.get("validations", []),
        )

        try:
            import pandas as pd

            from ..core.joint.plotters import (
                plot_crystallinity_comparison,
                plot_ir_vs_dsc_xc,
                plot_timeline_alignment,
                plot_tm_vs_long_period,
                plot_xc_vs_crystallite_size,
            )

            df = pd.DataFrame(report.get("rows", []))

            if not df.empty:
                cryst = pd.DataFrame(
                    {
                        "dsc_Xc": df.get("dsc_Xc_pct"),
                        "waxs_Xc": df.get("waxs_Xc_pct"),
                        "saxs_Xc": df.get("saxs_Xc_pct"),
                    }
                )

                for t1, t2 in [("dsc", "waxs"), ("dsc", "saxs"), ("waxs", "saxs")]:
                    if f"{t1}_Xc" in cryst and f"{t2}_Xc" in cryst:
                        cryst[f"{t1}_{t2}_diff"] = cryst[f"{t1}_Xc"] - cryst[f"{t2}_Xc"]

                if cryst.notna().any().any():
                    buf = plot_crystallinity_comparison(cryst)
                    with open(
                        os.path.join(figures_dir, "Fig-JointHub_crystallinity.png"),
                        "wb",
                    ) as fh:
                        fh.write(buf.getvalue())

                tm_l = (
                    df[["Tm_C", "L_nm"]].dropna()
                    if {"Tm_C", "L_nm"}.issubset(df.columns)
                    else pd.DataFrame()
                )
                if len(tm_l) >= 1:
                    buf = plot_tm_vs_long_period(tm_l)
                    with open(
                        os.path.join(figures_dir, "Fig-JointHub_tm_vs_long_period.png"),
                        "wb",
                    ) as fh:
                        fh.write(buf.getvalue())

                xc_d = (
                    df[["dsc_Xc_pct", "D_Scherrer_nm"]]
                    .rename(columns={"dsc_Xc_pct": "Xc_pct"})
                    .dropna()
                    if {"dsc_Xc_pct", "D_Scherrer_nm"}.issubset(df.columns)
                    else pd.DataFrame()
                )
                if len(xc_d) >= 1:
                    buf = plot_xc_vs_crystallite_size(xc_d)
                    with open(
                        os.path.join(
                            figures_dir,
                            "Fig-JointHub_xc_vs_crystallite_size.png",
                        ),
                        "wb",
                    ) as fh:
                        fh.write(buf.getvalue())

                ir_d = (
                    df[["IR_CI", "DSC_Xc"]].dropna()
                    if {"IR_CI", "DSC_Xc"}.issubset(df.columns)
                    else pd.DataFrame()
                )
                if len(ir_d) >= 1:
                    buf = plot_ir_vs_dsc_xc(ir_d)
                    if buf is not None:
                        with open(
                            os.path.join(figures_dir, "Fig-JointHub_ir_vs_dsc_xc.png"),
                            "wb",
                        ) as fh:
                            fh.write(buf.getvalue())

                timeline_df = None
                if {"shared_condition_value", "param_key", "value"}.issubset(df.columns):
                    timeline_df = df[
                        [
                            "shared_condition_value",
                            "param_key",
                            "value",
                            "batch_id",
                            "batch_label",
                            "sample_id",
                            "sample_name",
                            "technique",
                        ]
                    ].copy()
                elif "condition_values" in df.columns:
                    timeline_rows = []
                    for _, row in df.iterrows():
                        cond = row.get("condition_values", {})
                        if not isinstance(cond, dict):
                            continue
                        condition_value = None
                        for candidate in cond.values():
                            try:
                                numeric_candidate = float(candidate)
                            except Exception:
                                continue
                            if math.isfinite(numeric_candidate):
                                condition_value = numeric_candidate
                                break
                        if condition_value is None:
                            continue

                        technique = (
                            str(row.get("techniques", "") or "")
                            .split(",")[0]
                            .strip()
                            .lower()
                        )
                        for key in [
                            "Tm_C",
                            "L_nm",
                            "dsc_Xc_pct",
                            "waxs_Xc_pct",
                            "saxs_Xc_pct",
                            "lc_nm",
                            "D_Scherrer_nm",
                        ]:
                            value = row.get(key)
                            try:
                                numeric_value = float(value)
                            except Exception:
                                continue
                            if math.isnan(numeric_value):
                                continue
                            timeline_rows.append(
                                {
                                    "shared_condition_value": condition_value,
                                    "param_key": key,
                                    "value": numeric_value,
                                    "batch_id": row.get("batch_id", ""),
                                    "batch_label": row.get("batch", ""),
                                    "sample_id": row.get("sample_id", ""),
                                    "sample_name": row.get("sample", ""),
                                    "technique": technique,
                                }
                            )
                    timeline_df = pd.DataFrame(timeline_rows) if timeline_rows else pd.DataFrame()

                if timeline_df is not None and not timeline_df.empty:
                    buf = plot_timeline_alignment(timeline_df)
                    if buf is not None:
                        with open(
                            os.path.join(
                                figures_dir,
                                "Fig-JointHub_timeline_alignment.png",
                            ),
                            "wb",
                        ) as fh:
                            fh.write(buf.getvalue())

        except Exception as exc:
            self.log(tr("LOG_JOINT_FIG_SKIP", exc))
            main_window_module.logger.warning(
                "Failed to generate joint analysis figures.",
                exc_info=True,
            )
