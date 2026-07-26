"""

PolyNexus main GUI window.



Layout (matching the PolyNexus interface design):

+--------------------------------------------------------------+

|  Topbar (44px): [Logo] [Project badge]  ...  [Run] [Export]  |

+----------+---------------------------------------------------+

| Sidebar  |  Main content area                               |

| 200px    |  Tabs: Data | Config | Results | Plots           |

|          |                                                   |

| SAXS     |  (content per tab)                               |

| WAXS     |                                                   |

| DSC      |  Log panel                                       |

| IR       |  [13:45:22] Starting analysis...                 |

| NMR      |                                                   |

|          |                                                   |

| Recent:  |                                                   |

|  proj1   |                                                   |

|  proj2   |                                                   |

+----------+---------------------------------------------------+

"""



import logging
logger = logging.getLogger(__name__)

import os, sys, json, threading, traceback
import math

from datetime import datetime
import csv

from pathlib import Path

from typing import Dict, Any, List, Optional



from PySide6.QtWidgets import (

    QSizePolicy,

    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,

    QLabel, QLineEdit, QPushButton, QComboBox, QTextEdit,

    QSplitter, QApplication, QGroupBox,

    QFrame, QSizePolicy, QButtonGroup, QProgressBar,

    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,

    QMessageBox, QScrollArea, QListWidget, QListWidgetItem,

    QCheckBox, QSpinBox, QDoubleSpinBox, QFormLayout, QLayout,

    QToolButton, QMenu, QGridLayout, QAbstractItemView,
    QDialog, QDialogButtonBox, QProgressDialog, QRadioButton,
    QFileDialog,

)

from PySide6.QtCore import QObject, QRunnable, Qt, QThread, QThreadPool, Signal, QSettings, QTimer

from PySide6.QtGui import (

    QAction, QColor, QFont, QDragEnterEvent, QDropEvent, QIcon, QKeySequence, QShortcut,

)



from .styles import C_BG_CARD
from .styles import C_BORDER_LIGHT
from .styles import C_TEXT_MUTED
from .styles import C_TEXT_PRIMARY

from .theme import (
    ThemeEngine, build_qss, technique_accent,
    TECHNIQUE_ICONS, TECHNIQUE_LABELS,
)

from .effects import (
    ScientificBackdrop,
    animate_width,
    fade_in,
    start_busy_pulse,
    start_progress_animation,
    stop_busy_pulse,
    stop_progress_animation,
)

from .shortcuts import bind_shortcuts
from .figure_window_service import open_convergence_viewer

from .widgets.settings_dialog import SettingsDialog
from .analysis_run_service import (
    AnalysisRunPersistenceContext,
    persist_analysis_run as persist_gui_analysis_run,
    result_payload as analysis_run_result_payload,
    extract_result_r2 as analysis_run_result_r2,
)
from .analysis_history_service import (
    ai_tuning_change_summary_text,
    ai_tuning_chain_summary,
    ai_tuning_benchmark_delta_text,
    ai_tuning_benchmark_rate_text,
    ai_tuning_goal_recommendation,
    ai_tuning_previous_round_summary_text,
    ai_tuning_chain_stats,
    ai_tuning_remaining_risks_text,
    ai_tuning_report_context as build_ai_tuning_report_context,
    ai_tuning_tunable_summary_text,
    batch_fallback_summary_parts,
    current_result_history_context as resolve_current_result_history_context,
    current_result_origin as resolve_current_result_origin,
    current_result_tuning_context as resolve_current_result_tuning_context,
    current_results_payload as build_current_results_payload,
    current_results_record as build_current_results_record,
    find_analysis_evidence,
    format_history_timestamp as format_history_timestamp_value,
    gui_coerce_summary_float,
    gui_display_text,
    gui_display_text_value,
    gui_format_score_value,
    has_condition_axis_risk as build_has_condition_axis_risk,
    has_fallback_conflict_risk as build_has_fallback_conflict_risk,
    history_compare_state_translation_key,
    history_context_line_parts,
    build_history_context_snapshot_from_window,
    history_record_analysis_evidence,
    history_record_confirmed,
    history_result_origin,
    history_result_metrics,
    history_validation_summary_text,
    measured_result_metric_parts,
    result_origin_translation_key,
    result_review_metric_summary,
    result_source_summary_text as build_result_source_summary_text,
    result_to_jsonable,
    saxs_lc_status_summary_parts,
    saxs_lc_status_text as build_saxs_lc_status_text,
    saxs_strain_evidence_snapshot as build_saxs_strain_evidence_snapshot,
    saxs_strain_next_step_text as build_saxs_strain_next_step_text,
    saxs_strain_risk_summary_text as build_saxs_strain_risk_summary_text,
    saxs_strain_summary_text as build_saxs_strain_summary_text,
    result_mask_summary_text as build_result_mask_summary_text,
)
from .window_text_helpers import read_warning_count
from .results_review_service import (
    ai_tuning_report_benchmark_text as build_ai_tuning_report_benchmark_text,
    ai_tuning_report_decision_text as build_ai_tuning_report_decision_text,
    ai_tuning_report_summary_text as build_ai_tuning_report_summary_text,
    build_result_review_summary_text_from_window,
    result_review_analysis_evidence_card_text as build_result_review_analysis_evidence_card_text,
    result_review_constraint_summary_text as build_result_review_constraint_summary_text,
    result_review_dsc_support_block_text as build_result_review_dsc_support_block_text,
    result_review_ir_support_block_text as build_result_review_ir_support_block_text,
    result_review_round_core_summary_text as build_result_review_round_core_summary_text,
    result_review_round_support_summary_text as build_result_review_round_support_summary_text,
    result_review_stability_summary_text as build_result_review_stability_summary_text,
    result_review_saxs_semantic_lines as build_result_review_saxs_semantic_lines,
    result_review_waxs_core_text,
    result_review_waxs_support_text,
)
from .results_table_service import build_batch_results_table_model
from .table_export_service import write_table_export
from .preprocess_decision_service import build_preprocess_ui_decision

from .i18n import tr, set_language, get_language
from .workspace_mode import WorkspaceMode
from .workspace_context import WorkspaceContext
from .run_state_service import RunState
from .window_text_helpers import (
    data_file_dialog_filter as _data_file_dialog_filter,
    format_import_suggestion_reason as _shared_format_import_suggestion_reason,
    ir_conclusion_state_display as _ir_conclusion_state_display,
    is_default_project_label as _is_default_project_label,
    lang_text as _lang_text,
)
from .main_window_summary_mixin import MainWindowSummaryMixin
from .main_window_import_mixin import MainWindowImportMixin
from .main_window_run_mixin import MainWindowRunMixin
from .main_window_workspace_mixin import MainWindowWorkspaceMixin
from .main_window_figure_mixin import MainWindowFigureMixin
from .main_window_output_mixin import MainWindowOutputMixin
from .main_window_settings_mixin import MainWindowSettingsMixin
from .main_window_history_mixin import MainWindowHistoryMixin
from .main_window_results_mixin import MainWindowResultsMixin
from .main_window_guidance_panels_mixin import MainWindowGuidancePanelsMixin
from .main_window_retranslate_mixin import MainWindowRetranslateMixin
from .main_window_shell_mixin import MainWindowShellMixin
from .main_window_ai_tuning_mixin import MainWindowAITuningMixin
from .main_window_calibration_mixin import MainWindowCalibrationMixin
from .main_window_config_panel_mixin import MainWindowConfigPanelMixin
from .main_window_joint_diagnostics_mixin import MainWindowJointDiagnosticsMixin
from .main_window_navigation_mixin import MainWindowNavigationMixin
from .main_window_result_semantics_mixin import MainWindowResultSemanticsMixin
from .main_window_sample_hub_mixin import MainWindowSampleHubMixin
from .main_window_workers import (
    AITuneSignals,
    AITuneWorker,
    AnalysisWorker,
    BatchWorker,
    JointHubWorker,
)

from ..utils import (
    delete_config_preset,
    detect_polymer_type,
    list_config_presets,
    load_config_preset,
    load_defaults,
    save_config_preset,
)
from ..utils.logger import PolyNexusLogger
from llm.config import load_ai_settings


def get_engine(*args, **kwargs):
    """Resolve an analysis engine only when a run actually starts."""
    from ..core.engine import get_engine as _get_engine

    return _get_engine(*args, **kwargs)


def check_file_format(*args, **kwargs):
    """Resolve file-format validation only when an input is being run."""
    from ..core.engine import check_file_format as _check_file_format

    return _check_file_format(*args, **kwargs)


def list_techniques(*args, **kwargs):
    """Keep the historical module-level hook without eager core imports."""
    from ..core.engine import list_techniques as _list_techniques

    return _list_techniques(*args, **kwargs)


def build_joint_hub_report(*args, **kwargs):
    """Resolve joint-analysis reporting only when requested."""
    from ..core.joint.dataset import build_joint_hub_report as _build_report

    return _build_report(*args, **kwargs)


SIDEBAR_SECTIONS = {
    "experiment": {"zh": "\u5b9e\u9a8c\u5206\u6790", "en": "Experimental"},
    "compute": {"zh": "\u7406\u8bba\u8ba1\u7b97", "en": "Computational"},
    "joint": {"zh": "\u8054\u5408\u5206\u6790", "en": "Joint analysis"},
    "samples": {"zh": "\u6837\u54c1", "en": "Samples"},
    "recent": {"zh": "\u6700\u8fd1\u9879\u76ee", "en": "Recent projects"},
}

SIDEBAR_MODULE_TEXT = {
    "saxs.temperature": {"zh": "\u539f\u4f4d\u53d8\u6e29 SAXS", "en": "Temperature SAXS"},
    "saxs.strain": {"zh": "\u539f\u4f4d\u62c9\u4f38 SAXS", "en": "Tensile SAXS"},
    "saxs.static": {"zh": "\u9759\u6001 SAXS", "en": "Static SAXS"},
    "waxs.strain": {"zh": "\u539f\u4f4d\u62c9\u4f38 WAXS", "en": "Tensile WAXS"},
    "waxs.temperature": {"zh": "\u539f\u4f4d\u53d8\u6e29 WAXS", "en": "Temperature WAXS"},
    "waxs.static": {"zh": "\u9759\u6001 WAXS", "en": "Static WAXS"},
    "dsc.nonisothermal": {"zh": "\u975e\u7b49\u6e29\u52a8\u529b\u5b66", "en": "Non-isothermal kinetics"},
    "dsc.isothermal": {"zh": "\u7b49\u6e29\u52a8\u529b\u5b66", "en": "Isothermal kinetics"},
    "dsc.standard": {"zh": "\u6807\u51c6 DSC", "en": "Standard DSC"},
    "ir.temperature_2d": {"zh": "\u539f\u4f4d\u53d8\u6e29\u4e8c\u7ef4 IR", "en": "Temperature 2D IR"},
    "ir.mapping": {"zh": "IR \u9762\u626b", "en": "IR mapping"},
    "ir.standard": {"zh": "\u6807\u51c6 IR", "en": "Standard IR"},
    "nmr.standard": {"zh": "\u56fa\u6001 NMR", "en": "Solid-state NMR"},
    "nmr.liquid_h": {"zh": "\u6db2\u4f53 H \u8c31", "en": "Liquid 1H"},
    "nmr.liquid_c": {"zh": "\u6db2\u4f53 C \u8c31", "en": "Liquid 13C"},
    "nmr.solid_h": {"zh": "\u56fa\u4f53 H \u8c31", "en": "Solid 1H"},
    "nmr.solid_c": {"zh": "\u56fa\u4f53 C \u8c31", "en": "Solid 13C"},
    "joint.quick": {"zh": "\u5feb\u901f\u8054\u5408", "en": "Quick joint"},
    "joint.compare": {"zh": "\u6837\u54c1\u5bf9\u6bd4", "en": "Sample compare"},
    "samples": {"zh": "\u6837\u54c1\u5e93", "en": "Sample library"},
}

SIDEBAR_MODULE_TOOLTIPS = {
    "ir.temperature_2d": {"zh": "\u53d8\u6e29\u7ea2\u5916\u5e8f\u5217\u30012D-COS \u540c\u6b65/\u5f02\u6b65\u76f8\u5173\u8c31\u548c\u7279\u5f81\u5e26\u8ffd\u8e2a", "en": "Variable-temperature IR sequence, 2D-COS synchronous/asynchronous maps, and band tracking"},
    "joint.quick": {"zh": "\u57fa\u4e8e\u5f53\u524d\u7ed3\u679c", "en": "Use current in-memory results"},
    "joint.compare": {"zh": "\u57fa\u4e8e\u6570\u636e\u5e93\u6837\u54c1", "en": "Compare selected samples from the database"},
    "samples": {"zh": "\u6253\u5f00\u6837\u54c1\u5e93", "en": "Open sample library"},
}


def _format_import_suggestion_reason(reason: str) -> str:
    return _shared_format_import_suggestion_reason(
        reason,
        registry_lookup=SIDEBAR_MODULE_TEXT.get,
    )


class AITuningGoalDialog(QDialog):
    def __init__(self, parent=None, *, current_goal: str = ""):
        super().__init__(parent)
        self.setWindowTitle(tr("AI_TUNING_GOAL_DIALOG_TITLE"))
        self.setModal(True)
        self.resize(640, 380)
        self._recommended_goal, self._recommended_reason = self._recommend_goal()
        current_goal = str(current_goal or "").strip().lower() or "symptom"
        if current_goal not in {"symptom", "risk", "joint", "stability"}:
            current_goal = "symptom"
        self._selected_goal = self._recommended_goal if current_goal == "symptom" else current_goal

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel(tr("AI_TUNING_GOAL_DIALOG_TITLE"))
        title.setWordWrap(True)
        title.setStyleSheet(f"color: {C_TEXT_PRIMARY}; font-weight: 600;")
        layout.addWidget(title)

        desc = QLabel(tr("AI_TUNING_GOAL_DIALOG_DESC"))
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {C_TEXT_MUTED};")
        layout.addWidget(desc)

        recommendation_card = QFrame()
        recommendation_card.setObjectName("goal_recommendation_card")
        recommendation_card.setStyleSheet(
            f"QFrame#goal_recommendation_card {{ background-color: {C_BG_CARD}; border: 1px solid {C_BORDER_LIGHT}; border-radius: 6px; }}"
        )
        recommendation_layout = QVBoxLayout(recommendation_card)
        recommendation_layout.setContentsMargins(10, 8, 10, 8)
        recommendation_layout.setSpacing(4)
        self._recommendation = QLabel(tr("AI_TUNING_GOAL_RECOMMENDED", self._goal_label(self._recommended_goal)))
        self._recommendation.setWordWrap(True)
        self._recommendation.setStyleSheet(f"color: {C_TEXT_PRIMARY}; font-weight: 600;")
        recommendation_layout.addWidget(self._recommendation)
        self._recommendation_reason = QLabel(self._recommended_reason)
        self._recommendation_reason.setWordWrap(True)
        self._recommendation_reason.setStyleSheet(f"color: {C_TEXT_MUTED};")
        recommendation_layout.addWidget(self._recommendation_reason)
        layout.addWidget(recommendation_card)

        self._choices = QButtonGroup(self)
        self._choices.setExclusive(True)

        choice_map = [
            ("symptom", tr("AI_TUNING_GOAL_SYMPTOM"), tr("AI_TUNING_GOAL_HINT_SYMPTOM")),
            ("risk", tr("AI_TUNING_GOAL_RISK"), tr("AI_TUNING_GOAL_HINT_RISK")),
            ("joint", tr("AI_TUNING_GOAL_JOINT"), tr("AI_TUNING_GOAL_HINT_JOINT")),
            ("stability", tr("AI_TUNING_GOAL_STABILITY"), tr("AI_TUNING_GOAL_HINT_STABILITY")),
        ]
        for goal_key, label_text, hint_text in choice_map:
            row = QFrame()
            row.setObjectName("goal_choice_row")
            if goal_key == self._recommended_goal:
                row.setStyleSheet(
                    f"QFrame#goal_choice_row {{ background-color: {C_BG_CARD}; border: 1px solid {C_BORDER_LIGHT}; border-radius: 6px; }}"
                )
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(10, 8, 10, 8)
            row_layout.setSpacing(4)
            radio = QRadioButton(label_text)
            radio.setProperty("goal_key", goal_key)
            radio.setChecked(goal_key == self._selected_goal)
            self._choices.addButton(radio)
            row_layout.addWidget(radio)
            hint = QLabel(hint_text)
            hint.setWordWrap(True)
            hint.setStyleSheet(f"color: {C_TEXT_MUTED};")
            row_layout.addWidget(hint)
            layout.addWidget(row)

        self._hint = QLabel()
        self._hint.setWordWrap(True)
        self._hint.setStyleSheet(f"color: {C_TEXT_MUTED};")
        layout.addWidget(self._hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText(tr("COMMON_APPLY"))
        buttons.button(QDialogButtonBox.Cancel).setText(tr("COMMON_CANCEL"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._choices.buttonClicked.connect(self._update_hint)
        self._update_hint()

    def _recommend_goal(self) -> tuple[str, str]:
        goal = "symptom"
        reason = tr("AI_TUNING_GOAL_REASON_SYMPTOM")
        parent = self.parent()
        if parent is None:
            return goal, reason

        joint_context = {}
        joint_context_fn = getattr(parent, "_joint_ai_context", None)
        if callable(joint_context_fn):
            try:
                joint_context = joint_context_fn()
            except (AttributeError, RuntimeError):
                joint_context = {}

        tuning_context = getattr(parent, "_last_ai_tuning_context", {})
        validation_text = ""
        if hasattr(parent, "_results_summary_risk_label"):
            validation_text = str(parent._results_summary_risk_label.text() or "")
        goal, reason_key = ai_tuning_goal_recommendation(
            joint_context=joint_context,
            tuning_context=tuning_context,
            validation_text=validation_text,
        )
        return goal, tr(reason_key)

    def _update_hint(self, *_args):
        selected = self.selected_goal()
        self._hint.setText(tr("AI_TUNING_GOAL_SELECTED", self._goal_label(selected)))

    def _goal_label(self, key: str) -> str:
        return {
            "symptom": tr("AI_TUNING_GOAL_SYMPTOM"),
            "risk": tr("AI_TUNING_GOAL_RISK"),
            "joint": tr("AI_TUNING_GOAL_JOINT"),
            "stability": tr("AI_TUNING_GOAL_STABILITY"),
        }.get(key, tr("AI_TUNING_GOAL_SYMPTOM"))

    def selected_goal(self) -> str:
        for button in self._choices.buttons():
            if button.isChecked():
                return str(button.property("goal_key") or "symptom")
        return self._selected_goal or "symptom"


class SideTuningReportDialog(QDialog):
    def __init__(self, report, parent=None):
        super().__init__(parent)
        self.report = report if isinstance(report, dict) else {}
        self.setWindowTitle(tr("AI_TUNING_REPORT_TITLE"))
        self.resize(1080, 760)
        layout = QVBoxLayout(self)
        self._summary_label = QLabel(self._report_summary_text())
        self._summary_label.setWordWrap(True)
        self._summary_label.setStyleSheet(f"color: {C_TEXT_MUTED}; padding: 0 0 6px 0;")
        layout.addWidget(self._summary_label)
        self._decision_label = QLabel(self._report_decision_text())
        self._decision_label.setWordWrap(True)
        self._decision_label.setStyleSheet(f"color: {C_TEXT_MUTED}; padding: 0 0 10px 0;")
        layout.addWidget(self._decision_label)
        self._preprocess_ui_decision = None
        self._preprocess_metrics_label = QLabel("")
        self._preprocess_metrics_label.setWordWrap(True)
        self._preprocess_metrics_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
        if "preprocess_decision" in self.report:
            self._preprocess_ui_decision = build_preprocess_ui_decision(self.report)
            view = self._preprocess_ui_decision
            metric_text = "\n".join(
                f"{name}: {value}" for name, value in view.metric_rows.items()
            )
            reason_text = ", ".join(view.reason_codes)
            self._preprocess_metrics_label.setText(
                "\n".join(
                    part
                    for part in (
                        view.title,
                        view.summary,
                        metric_text,
                        f"Reasons: {reason_text}" if reason_text else "",
                    )
                    if part
                )
            )
            self._preprocess_metrics_label.setStyleSheet(
                f"color: {C_TEXT_PRIMARY}; padding: 6px 0 10px 0;"
            )
            layout.addWidget(self._preprocess_metrics_label)
        benchmark = self._report_benchmark_text()
        self._benchmark_label = None
        if benchmark:
            self._benchmark_label = QLabel(benchmark)
            self._benchmark_label.setWordWrap(True)
            self._benchmark_label.setStyleSheet(f"color: {C_TEXT_MUTED}; padding: 0 0 10px 0;")
            layout.addWidget(self._benchmark_label)

        review_splitter = QSplitter(Qt.Horizontal)
        review_splitter.setChildrenCollapsible(False)
        review_splitter.setHandleWidth(8)
        layout.addWidget(review_splitter, 1)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        review_splitter.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        review_splitter.addWidget(right_panel)
        review_splitter.setSizes([360, 700])

        issues_group = QGroupBox(tr("AI_TUNING_REVIEW_ISSUES"))
        issues_layout = QVBoxLayout(issues_group)
        self._issue_target_label = self._build_review_label()
        self._issue_symptom_label = self._build_review_label()
        self._issue_risk_label = self._build_review_label()
        self._issue_stability_label = self._build_review_label()
        issues_layout.addWidget(self._issue_target_label)
        issues_layout.addWidget(self._issue_symptom_label)
        issues_layout.addWidget(self._issue_risk_label)
        issues_layout.addWidget(self._issue_stability_label)
        left_layout.addWidget(issues_group)

        recommendation_group = QGroupBox(tr("AI_TUNING_REVIEW_RECOMMENDATION"))
        recommendation_layout = QVBoxLayout(recommendation_group)
        self._recommendation_label = self._build_review_label()
        self._recommendation_changes_label = self._build_review_label()
        self._recommendation_decision_label = self._build_review_label()
        recommendation_layout.addWidget(self._recommendation_label)
        recommendation_layout.addWidget(self._recommendation_changes_label)
        recommendation_layout.addWidget(self._recommendation_decision_label)
        left_layout.addWidget(recommendation_group)

        evidence_group = QGroupBox(tr("AI_TUNING_REVIEW_GUARDS"))
        evidence_layout = QVBoxLayout(evidence_group)
        self._evidence_constraints_label = self._build_review_label()
        self._evidence_stability_label = self._build_review_label()
        self._rollback_boundary_label = self._build_review_label()
        evidence_layout.addWidget(self._evidence_constraints_label)
        evidence_layout.addWidget(self._evidence_stability_label)
        evidence_layout.addWidget(self._rollback_boundary_label)
        left_layout.addWidget(evidence_group)

        evidence_card_group = QGroupBox(tr("AI_TUNING_LABEL_EVIDENCE_CARD"))
        evidence_card_layout = QVBoxLayout(evidence_card_group)
        self._evidence_card_label = self._build_review_label()
        evidence_card_layout.addWidget(self._evidence_card_label)
        left_layout.addWidget(evidence_card_group)
        left_layout.addStretch(1)

        trials_group = QGroupBox(tr("AI_TUNING_REVIEW_TRIALS"))
        trials_layout = QVBoxLayout(trials_group)
        self._candidate_table = QTableWidget()
        self._candidate_table.setColumnCount(5)
        self._candidate_table.setHorizontalHeaderLabels([
            tr("AI_TUNING_COL_ACTION"),
            tr("AI_TUNING_COL_STATUS"),
            tr("AI_TUNING_COL_OBJECTIVE_DELTA"),
            tr("AI_TUNING_COL_R2_DELTA"),
            tr("AI_TUNING_COL_NOTE"),
        ])
        self._candidate_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._candidate_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._candidate_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._candidate_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._candidate_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._candidate_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._candidate_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._candidate_table.horizontalHeader().setStretchLastSection(True)
        self._candidate_copy_shortcut = QShortcut(QKeySequence.Copy, self._candidate_table)
        self._candidate_copy_shortcut.activated.connect(
            lambda: self._copy_selected_table_to_clipboard(self._candidate_table)
        )
        trials_layout.addWidget(self._candidate_table)
        right_layout.addWidget(trials_group, 2)

        score_group = QGroupBox(tr("AI_TUNING_REVIEW_ROUNDS"))
        score_layout = QVBoxLayout(score_group)
        self._score_table = QTableWidget()
        self._score_table.setColumnCount(5)
        self._score_table.setHorizontalHeaderLabels([
            tr("AI_TUNING_COL_ROUND"),
            tr("AI_TUNING_COL_CORE"),
            tr("AI_TUNING_COL_SUPPORT"),
            tr("AI_TUNING_COL_R2"),
            tr("AI_TUNING_COL_EVAL"),
        ])
        self._score_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._score_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._score_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        score_header = self._score_table.horizontalHeader()
        score_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        score_header.setSectionResizeMode(1, QHeaderView.Stretch)
        score_header.setSectionResizeMode(2, QHeaderView.Stretch)
        score_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        score_header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._score_copy_shortcut = QShortcut(QKeySequence.Copy, self._score_table)
        self._score_copy_shortcut.activated.connect(
            lambda: self._copy_selected_table_to_clipboard(self._score_table)
        )
        score_layout.addWidget(self._score_table)
        right_layout.addWidget(score_group, 1)

        change_group = QGroupBox(tr("AI_TUNING_REVIEW_CHANGES"))
        change_layout = QVBoxLayout(change_group)
        self._change_table = QTableWidget()
        self._change_table.setColumnCount(4)
        self._change_table.setHorizontalHeaderLabels([
            tr("AI_TUNING_COL_PARAM"),
            tr("AI_TUNING_COL_BEFORE"),
            tr("AI_TUNING_COL_AFTER"),
            tr("AI_TUNING_COL_REASON"),
        ])
        self._change_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._change_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._change_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._change_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._change_copy_shortcut = QShortcut(QKeySequence.Copy, self._change_table)
        self._change_copy_shortcut.activated.connect(
            lambda: self._copy_selected_table_to_clipboard(self._change_table)
        )
        change_layout.addWidget(self._change_table)
        right_layout.addWidget(change_group, 1)
        self._buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._buttons.button(QDialogButtonBox.Ok).setText(tr("AI_TUNING_APPLY"))
        self._buttons.button(QDialogButtonBox.Cancel).setText(tr("COMMON_CANCEL"))
        if self._preprocess_ui_decision is not None:
            view = self._preprocess_ui_decision
            self._buttons.button(QDialogButtonBox.Ok).setEnabled(
                view.apply_enabled or view.undo_enabled
            )
            if view.undo_enabled:
                self._buttons.button(QDialogButtonBox.Ok).setText("Undo")
            elif view.mode in {"shadow", "keep_original"}:
                self._buttons.button(QDialogButtonBox.Cancel).setText("Close")
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)
        self._populate_review_panels()
        self._fill_candidate_trials()
        self._fill_scores()
        self._fill_changes()

    def _build_review_label(self):
        label = QLabel()
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        return label

    def _report_technique(self):
        return str(self.report.get("technique") or getattr(self, "_current_technique", "") or "").strip().lower()

    def _report_summary_text(self):
        return build_ai_tuning_report_summary_text(self.report)

    def _report_decision_text(self):
        return build_ai_tuning_report_decision_text(self.report)

    def _report_benchmark_text(self):
        return build_ai_tuning_report_benchmark_text(
            self.report,
            delta_text_fn=self._format_benchmark_delta,
            rate_text_fn=self._format_benchmark_rate,
        )

    def best_config(self):
        if self._preprocess_ui_decision is not None:
            return dict(self._preprocess_ui_decision.selected_config)
        config = self.report.get("best_config") or {}
        return config if isinstance(config, dict) else {}

    def _format_benchmark_delta(self, value):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return "N/A"
        sign = "+" if number > 0 else ""
        return f"{sign}{number:.3f}"

    def _format_benchmark_rate(self, value):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return "0.0%"
        return f"{number * 100:.1f}%"

    def _ir_label_text(self, value: str) -> str:
        key = str(value or "").strip().lower()
        mapping = {
            "peak_assignment": tr("IR_BASIS_PEAK_ASSIGNMENT"),
            "peak_detection": tr("IR_BASIS_PEAK_DETECTION"),
        }
        return mapping.get(key, tr("IR_BASIS_UNKNOWN"))

    def _ir_bool_text(self, value: Any) -> str:
        if value is True:
            return tr("COMMON_YES")
        if value is False:
            return tr("COMMON_NO")
        return tr("AI_TUNING_EMPTY_VALUE")

    def _ir_conclusion_state_text(self, value: Any) -> str:
        return _ir_conclusion_state_display(value)

    def _ir_support_block_text(self, analysis_evidence: dict[str, Any] | None = None) -> str:
        analysis_evidence = analysis_evidence if isinstance(analysis_evidence, dict) else self._current_analysis_evidence()
        return build_result_review_ir_support_block_text(
            analysis_evidence,
            include_reference_summary=False,
        )

    def _constraint_summary_text(self, analysis_evidence):
        return build_result_review_constraint_summary_text(analysis_evidence)

    def _stability_summary_text(self, analysis_evidence):
        return build_result_review_stability_summary_text(analysis_evidence)

    def _fill_scores(self):
        history = self.report.get("history") or []
        rows = []
        if isinstance(history, list):
            for item in history:
                if not isinstance(item, dict):
                    continue
                rows.append([
                    self._round_status_text(item),
                    self._round_core_summary_text(item),
                    self._round_support_summary_text(item),
                    item.get("r_squared_after", item.get("r_squared", "")),
                    item.get("eval_score", ""),
                ])
        self._score_table.setRowCount(len(rows))
        for row, values in enumerate(rows):
            for col, value in enumerate(values):
                item = QTableWidgetItem("" if value is None else str(value))
                item.setToolTip(item.text())
                self._score_table.setItem(row, col, item)

    def _fill_changes(self):
        rows = []
        history = self.report.get("history") or []
        if isinstance(history, list):
            for item in history:
                if not isinstance(item, dict):
                    continue
                changes = item.get("changes") or {}
                advice = item.get("llm_advice") if isinstance(item.get("llm_advice"), dict) else {}
                reason = str(advice.get("reasoning", "") or "").strip()
                if not bool(item.get("accepted", True)):
                    rollback_reason = str(advice.get("rollback_reason", "") or "").strip()
                    if rollback_reason:
                        reason = tr("AI_TUNING_REASON_ROLLED_BACK", rollback_reason)
                config = item.get("config_snapshot") if isinstance(item.get("config_snapshot"), dict) else {}
                if isinstance(changes, dict):
                    for key, new_value in changes.items():
                        rows.append([key, config.get(key, ""), new_value, reason])
        self._change_table.setRowCount(len(rows))
        for row, values in enumerate(rows):
            for col, value in enumerate(values):
                if isinstance(value, (dict, list)):
                    text = json.dumps(value, ensure_ascii=False)
                else:
                    text = "" if value is None else str(value)
                self._change_table.setItem(row, col, QTableWidgetItem(text))

    def _round_status_text(self, item):
        round_num = item.get("round_num", item.get("round_idx", ""))
        if bool(item.get("accepted", True)):
            return tr("AI_TUNING_ROUND_ACCEPTED", round_num)
        return tr("AI_TUNING_ROUND_ROLLED_BACK", round_num)

    def _candidate_history(self):
        history = self.report.get("history") or []
        rows = []
        if not isinstance(history, list):
            return rows
        for item in history:
            if not isinstance(item, dict):
                continue
            round_num = int(item.get("round_num", item.get("round_idx", 0)) or 0)
            if round_num <= 0:
                continue
            rows.append(item)
        return rows

    def _latest_review_round(self):
        history = self._candidate_history()
        for item in reversed(history):
            advice = item.get("llm_advice") if isinstance(item.get("llm_advice"), dict) else {}
            if advice.get("candidate_trials") or advice.get("selected_candidate") or item.get("decision_summary"):
                return item
        return history[-1] if history else {}

    def _recommendation_round(self):
        history = self._candidate_history()
        for item in reversed(history):
            advice = item.get("llm_advice") if isinstance(item.get("llm_advice"), dict) else {}
            selected = advice.get("selected_candidate")
            if isinstance(selected, dict) and selected:
                return item

        best_item = None
        best_r2 = None
        for item in history:
            if not bool(item.get("accepted", True)):
                continue
            try:
                r2_value = float(item.get("r_squared_after", item.get("r_squared", "")))
            except (TypeError, ValueError):
                continue
            if best_r2 is None or r2_value > best_r2:
                best_r2 = r2_value
                best_item = item
        return best_item or self._latest_review_round()

    def _selected_candidate(self):
        round_item = self._recommendation_round()
        advice = round_item.get("llm_advice") if isinstance(round_item.get("llm_advice"), dict) else {}
        selected = advice.get("selected_candidate")
        return selected if isinstance(selected, dict) else {}

    def _candidate_trials(self):
        round_item = self._latest_review_round()
        advice = round_item.get("llm_advice") if isinstance(round_item.get("llm_advice"), dict) else {}
        trials = advice.get("candidate_trials")
        return trials if isinstance(trials, list) else []

    def _review_analysis_evidence(self):
        for item in (self._recommendation_round(), self._latest_review_round()):
            evidence = item.get("analysis_evidence")
            if isinstance(evidence, dict) and evidence:
                return evidence
        return {}

    def _analysis_evidence_card_text(self, analysis_evidence):
        return build_result_review_analysis_evidence_card_text(
            analysis_evidence,
            technique=self._report_technique(),
            language=get_language(),
        )

    def _round_core_summary_text(self, item):
        if not isinstance(item, dict):
            return tr("AI_TUNING_EMPTY_VALUE")
        output = item.get("output_parameters") if isinstance(item.get("output_parameters"), dict) else {}
        return build_result_review_round_core_summary_text(
            output,
            technique=self._report_technique(),
        )

    def _round_support_summary_text(self, item):
        if not isinstance(item, dict):
            return tr("AI_TUNING_EMPTY_VALUE")
        evidence = self._round_history_analysis_evidence(item)
        return build_result_review_round_support_summary_text(
            evidence,
            technique=self._report_technique(),
            language=get_language(),
        )

    def _display_text(self, value):
        return gui_display_text(value, empty_text=tr("AI_TUNING_EMPTY_VALUE"))

    def _format_score_value(self, value, signed=False):
        return gui_format_score_value(value, empty_text=tr("AI_TUNING_EMPTY_VALUE"), signed=signed)

    def _format_change_summary(self, changes):
        return ai_tuning_change_summary_text(
            changes,
            empty_text=tr("AI_TUNING_EMPTY_VALUE"),
            display_text_fn=self._display_text,
            more_text_fn=lambda remaining: tr("AI_TUNING_CHANGESET_MORE", remaining),
        )


    def _remaining_risks_text(self):
        return ai_tuning_remaining_risks_text(
            self._candidate_history(),
            empty_text=tr("AI_TUNING_EMPTY_VALUE"),
        )

    def _round_history_analysis_evidence(self, item):
        if not isinstance(item, dict):
            return {}
        evidence = item.get("analysis_evidence")
        if isinstance(evidence, dict) and evidence:
            return evidence
        payload = item.get("results_summary") if isinstance(item.get("results_summary"), dict) else {}
        result_payload = payload.get("result") if isinstance(payload.get("result"), dict) else {}
        if isinstance(result_payload, dict):
            evidence = result_payload.get("analysis_evidence")
            if isinstance(evidence, dict) and evidence:
                return evidence
        return {}

    def _candidate_status_text(self, status):
        key = {
            "accepted": "AI_TUNING_TRIAL_STATUS_ACCEPTED",
            "rejected": "AI_TUNING_TRIAL_STATUS_REJECTED",
            "rolled_back": "AI_TUNING_TRIAL_STATUS_ROLLED_BACK",
            "skipped": "AI_TUNING_TRIAL_STATUS_SKIPPED",
        }.get(str(status or "").strip().lower())
        if key:
            return tr(key)
        return self._display_text(status)

    def _candidate_action_text(self, item):
        label = str(item.get("label", "") or "").strip()
        action = str(item.get("action_name", "") or "").strip()
        if label and action and label.lower() != action.lower():
            return f"{label} ({action})"
        return label or action or tr("AI_TUNING_EMPTY_VALUE")

    def _candidate_note_text(self, item):
        note_parts = []
        decision = str(item.get("decision_summary", "") or "").strip()
        reason = str(item.get("reason", "") or item.get("rollback_reason", "") or "").strip()
        expected = str(item.get("expected_evidence_change", "") or "").strip()
        if decision:
            note_parts.append(decision)
        elif reason:
            note_parts.append(reason)
        if expected:
            note_parts.append(tr("AI_TUNING_EXPECTED_SUMMARY", expected))
        return " | ".join(note_parts) if note_parts else tr("AI_TUNING_EMPTY_VALUE")

    def _selected_expected_evidence(self):
        selected = self._selected_candidate()
        action_name = str(selected.get("action_name", "") or "").strip()
        round_item = self._recommendation_round()
        advice = round_item.get("llm_advice") if isinstance(round_item.get("llm_advice"), dict) else {}

        candidate_trials = advice.get("candidate_trials")
        if isinstance(candidate_trials, list):
            for item in candidate_trials:
                if not isinstance(item, dict):
                    continue
                trial_action = str(item.get("action_name", "") or "").strip()
                if action_name and trial_action and trial_action != action_name:
                    continue
                expected = str(item.get("expected_evidence_change", "") or "").strip()
                if expected:
                    return expected

        recommended_actions = advice.get("recommended_actions")
        if isinstance(recommended_actions, list):
            for item in recommended_actions:
                if not isinstance(item, dict):
                    continue
                trial_action = str(item.get("name", item.get("action_name", "")) or "").strip()
                if action_name and trial_action and trial_action != action_name:
                    continue
                expected = str(item.get("expected_evidence_change", "") or "").strip()
                if expected:
                    return expected

        return str(advice.get("expected_evidence_change", "") or "").strip()

    def _rollback_boundary_text(self):
        round_item = self._recommendation_round()
        advice = round_item.get("llm_advice") if isinstance(round_item.get("llm_advice"), dict) else {}
        boundary = str(advice.get("rollback_condition", "") or "").strip()
        if boundary:
            return boundary
        detail = str(round_item.get("rollback_detail", "") or "").strip()
        if detail:
            return detail
        return str(self.report.get("convergence_reason", "") or "").strip() or tr("AI_TUNING_EMPTY_VALUE")

    def _populate_review_panels(self):
        latest_round = self._latest_review_round()
        recommendation_round = self._recommendation_round()
        selected = self._selected_candidate()
        analysis_evidence = self._review_analysis_evidence()

        target_symptom = (
            str(recommendation_round.get("target_symptom", "") or "").strip()
            or str(latest_round.get("target_symptom", "") or "").strip()
        )
        symptom_summary = (
            str(recommendation_round.get("symptom_summary", "") or "").strip()
            or str(latest_round.get("symptom_summary", "") or "").strip()
        )
        decision_summary = (
            str(recommendation_round.get("decision_summary", "") or "").strip()
            or str(latest_round.get("decision_summary", "") or "").strip()
        )

        recommendation_parts = [self._candidate_action_text(selected)]
        selected_target = str(selected.get("target_symptom", "") or "").strip()
        if selected_target:
            recommendation_parts.append(f"{tr('AI_TUNING_LABEL_TARGET')}: {selected_target}")
        objective_score = self._format_score_value(selected.get("objective_score"))
        if objective_score != tr("AI_TUNING_EMPTY_VALUE"):
            recommendation_parts.append(f"objective={objective_score}")
        r_squared = self._format_score_value(selected.get("r_squared"))
        if r_squared != tr("AI_TUNING_EMPTY_VALUE"):
            recommendation_parts.append(f"R2={r_squared}")

        decision_parts = [decision_summary] if decision_summary else []
        expected_evidence = self._selected_expected_evidence()
        if expected_evidence:
            decision_parts.append(tr("AI_TUNING_EXPECTED_SUMMARY", expected_evidence))

        self._issue_target_label.setText(f"{tr('AI_TUNING_LABEL_TARGET')}: {self._display_text(target_symptom)}")
        self._issue_symptom_label.setText(f"{tr('AI_TUNING_LABEL_SYMPTOMS')}: {self._display_text(symptom_summary)}")
        self._issue_risk_label.setText(f"{tr('AI_TUNING_LABEL_REMAINING_RISKS')}: {self._remaining_risks_text()}")
        self._issue_stability_label.setText(
            f"{tr('AI_TUNING_LABEL_STABILITY')}: {self._stability_summary_text(analysis_evidence)}"
        )

        self._recommendation_label.setText(
            f"{tr('AI_TUNING_LABEL_SELECTED')}: {' | '.join(recommendation_parts) if recommendation_parts else tr('AI_TUNING_EMPTY_VALUE')}"
        )
        self._recommendation_changes_label.setText(
            f"{tr('AI_TUNING_LABEL_CHANGESET')}: {self._format_change_summary(selected.get('changes', {}))}"
        )
        self._recommendation_decision_label.setText(
            f"{tr('AI_TUNING_LABEL_DECISION_DETAIL')}: {' | '.join(decision_parts) if decision_parts else tr('AI_TUNING_EMPTY_VALUE')}"
        )

        self._evidence_constraints_label.setText(
            f"{tr('AI_TUNING_LABEL_CONSTRAINT_GUARDS')}: {self._constraint_summary_text(analysis_evidence)}"
        )
        self._evidence_stability_label.setText(
            f"{tr('AI_TUNING_LABEL_STABILITY')}: {self._stability_summary_text(analysis_evidence)}"
        )
        self._rollback_boundary_label.setText(
            f"{tr('AI_TUNING_LABEL_ROLLBACK_BOUNDARY')}: {self._display_text(self._rollback_boundary_text())}"
        )
        if hasattr(self, "_evidence_card_label"):
            self._evidence_card_label.setText(self._analysis_evidence_card_text(analysis_evidence))

    def _fill_candidate_trials(self):
        trials = self._candidate_trials()
        rows = []
        if isinstance(trials, list):
            for item in trials:
                if not isinstance(item, dict):
                    continue
                rows.append([
                    self._candidate_action_text(item),
                    self._candidate_status_text(item.get("status")),
                    self._format_score_value(item.get("objective_delta"), signed=True),
                    self._format_score_value(item.get("r_squared_delta"), signed=True),
                    self._candidate_note_text(item),
                ])
        self._candidate_table.setRowCount(len(rows))
        for row, values in enumerate(rows):
            for col, value in enumerate(values):
                item = QTableWidgetItem("" if value is None else str(value))
                item.setToolTip(item.text())
                self._candidate_table.setItem(row, col, item)

    def _copy_selected_table_to_clipboard(self, table):
        if table not in (self._candidate_table, self._score_table, self._change_table):
            return
        cols = table.columnCount()
        rows = table.rowCount()
        if cols <= 0 or rows <= 0:
            return

        headers = []
        for col in range(cols):
            header_item = table.horizontalHeaderItem(col)
            headers.append(header_item.text() if header_item is not None else "")

        selection = table.selectionModel()
        selected_rows = []
        if selection is not None:
            selected_rows = sorted(index.row() for index in selection.selectedRows())
        row_indexes = selected_rows if selected_rows else list(range(rows))

        lines = ["\t".join(headers)]
        for row in row_indexes:
            values = []
            for col in range(cols):
                item = table.item(row, col)
                values.append(item.text() if item is not None else "")
            lines.append("\t".join(values))

        QApplication.clipboard().setText("\n".join(lines))



class ImportSuggestionDialog(QDialog):

    def __init__(self, path, is_dir, suggestion, submodule_options, parent=None):

        super().__init__(parent)
        self._path = str(path or "")
        self._is_dir = bool(is_dir)
        self._suggestion = suggestion
        self._submodule_options = submodule_options
        self._selected_submodule = str(getattr(suggestion, "submodule", "") or "").strip()
        self._default_mode = str(getattr(suggestion, "input_mode", "") or "").strip()
        self._is_manual_choice = str(getattr(suggestion, "reason", "") or "").strip() == "manual"
        self._ok_button = None

        self.setWindowTitle(tr("IMPORT_SETUP_TITLE") if self._is_manual_choice else tr("IMPORT_SUGGESTION_TITLE"))
        self.resize(540, 240)

        layout = QVBoxLayout(self)

        self._intro_label = QLabel(
            tr("IMPORT_SETUP_MESSAGE") if self._is_manual_choice else tr("IMPORT_SUGGESTION_MESSAGE")
        )
        self._intro_label.setWordWrap(True)
        layout.addWidget(self._intro_label)

        form = QFormLayout()

        path_row = QWidget()
        path_row_layout = QHBoxLayout(path_row)
        path_row_layout.setContentsMargins(0, 0, 0, 0)
        path_row_layout.setSpacing(8)
        self._path_label = QLabel(self._path)
        self._path_label.setWordWrap(True)
        self._path_label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        path_row_layout.addWidget(self._path_label, 1)
        self._copy_path_button = QToolButton()
        self._copy_path_button.setText(tr("COMMON_COPY"))
        self._copy_path_button.setToolTip(tr("IMPORT_SUGGESTION_COPY_PATH_TOOLTIP"))
        self._copy_path_button.clicked.connect(self._copy_path_to_clipboard)
        path_row_layout.addWidget(self._copy_path_button, 0)
        self._copy_summary_button = QToolButton()
        self._copy_summary_button.setText(tr("IMPORT_SUGGESTION_COPY_SUMMARY"))
        self._copy_summary_button.setToolTip(tr("IMPORT_SUGGESTION_COPY_SUMMARY_TOOLTIP"))
        self._copy_summary_button.clicked.connect(self._copy_summary_to_clipboard)
        path_row_layout.addWidget(self._copy_summary_button, 0)
        self._open_folder_button = QToolButton()
        self._open_folder_button.setText(tr("IMPORT_SUGGESTION_OPEN_FOLDER"))
        self._open_folder_button.setToolTip(tr("IMPORT_SUGGESTION_OPEN_FOLDER_TOOLTIP"))
        self._open_folder_button.clicked.connect(self._open_path_folder)
        path_row_layout.addWidget(self._open_folder_button, 0)
        form.addRow(tr("IMPORT_SUGGESTION_PATH"), path_row)

        self._reason_label = QLabel(_format_import_suggestion_reason(getattr(suggestion, "reason", "")))
        self._reason_label.setWordWrap(True)
        form.addRow(tr("IMPORT_SUGGESTION_REASON"), self._reason_label)

        self._technique_combo = QComboBox()
        self._technique_combo.addItem(tr("IMPORT_SUGGESTION_TECHNIQUE_EMPTY"), "")
        for technique in ["saxs", "waxs", "dsc", "ir", "nmr"]:
            self._technique_combo.addItem(
                TECHNIQUE_LABELS.get(technique, technique.upper()),
                technique,
            )
        technique_value = str(getattr(suggestion, "technique", "") or "").strip().lower()
        idx = self._technique_combo.findData(technique_value)
        self._technique_combo.setCurrentIndex(idx if idx >= 0 else 0)
        form.addRow(tr("IMPORT_SUGGESTION_TECHNIQUE"), self._technique_combo)
        self._technique_hint = QLabel(tr("IMPORT_SETUP_TECHNIQUE_HINT"))
        self._technique_hint.setWordWrap(True)
        self._technique_hint.setVisible(False)
        form.addRow("", self._technique_hint)

        self._submodule_combo = QComboBox()
        form.addRow(tr("IMPORT_SUGGESTION_SUBMODULE"), self._submodule_combo)
        self._submodule_hint = QLabel(tr("IMPORT_SUGGESTION_SUBMODULE_EMPTY"))
        self._submodule_hint.setWordWrap(True)
        self._submodule_hint.setVisible(False)
        form.addRow("", self._submodule_hint)

        self._mode_combo = QComboBox()
        self._mode_combo.addItem(tr("IMPORT_MODE_SINGLE"), "single")
        self._mode_combo.addItem(tr("IMPORT_MODE_SEQUENCE"), "sequence")
        self._mode_combo.addItem(tr("IMPORT_MODE_DIRECTORY"), "directory")
        form.addRow(tr("IMPORT_SUGGESTION_MODE"), self._mode_combo)

        layout.addLayout(form)

        self._apply_label = QLabel(tr("IMPORT_SETUP_APPLY") if self._is_manual_choice else tr("IMPORT_SUGGESTION_APPLY"))
        self._apply_label.setWordWrap(True)
        layout.addWidget(self._apply_label)

        self._button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_button = self._button_box.button(QDialogButtonBox.Ok)
        if ok_button is not None:
            ok_button.setText(tr("COMMON_APPLY"))
            self._ok_button = ok_button
        cancel_button = self._button_box.button(QDialogButtonBox.Cancel)
        if cancel_button is not None:
            cancel_button.setText(tr("COMMON_CANCEL") if self._is_manual_choice else tr("IMPORT_SUGGESTION_KEEP_CURRENT"))
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)
        layout.addWidget(self._button_box)

        self._technique_combo.currentIndexChanged.connect(self._refresh_submodules)
        self._submodule_combo.currentIndexChanged.connect(self._submodule_changed)
        self._refresh_submodules()
        self._update_accept_state()


    def _refresh_submodules(self):

        technique = self.selected_technique()
        previous = self._selected_submodule
        options = self._submodule_options.get(technique, [])

        self._submodule_combo.blockSignals(True)
        self._submodule_combo.clear()
        self._submodule_combo.addItem(tr("IMPORT_SUGGESTION_NO_SUBMODULE"), ("", ""))
        for submodule_id, label, input_mode in options:
            self._submodule_combo.addItem(label, (submodule_id, input_mode))
        has_options = bool(options)
        self._submodule_combo.setEnabled(has_options)
        self._submodule_hint.setVisible(not has_options)

        idx = 0
        for row, (submodule_id, _label, _mode) in enumerate(options, start=1):
            if submodule_id == previous:
                idx = row
                break
        self._submodule_combo.setCurrentIndex(idx)
        self._submodule_combo.blockSignals(False)
        self._submodule_changed()


    def _submodule_changed(self):

        data = self._submodule_combo.currentData()
        if isinstance(data, tuple) and len(data) == 2:
            submodule_id, input_mode = data
        else:
            submodule_id, input_mode = "", ""
        self._selected_submodule = str(submodule_id or "")
        mode = str(input_mode or "").strip() or self._default_mode or ("directory" if self._is_dir else "single")
        idx = self._mode_combo.findData(mode)
        if idx >= 0:
            self._mode_combo.setCurrentIndex(idx)
        self._update_accept_state()


    def _update_accept_state(self):

        needs_technique = self._is_manual_choice
        technique_selected = bool(self.selected_technique())
        if self._ok_button is not None:
            self._ok_button.setEnabled((not needs_technique) or technique_selected)
        if hasattr(self, "_technique_hint"):
            self._technique_hint.setVisible(needs_technique and not technique_selected)


    def selected_technique(self) -> str:

        return str(self._technique_combo.currentData() or "").strip().lower()


    def selected_submodule(self) -> str:

        return self._selected_submodule


    def selected_mode(self) -> str:

        return str(self._mode_combo.currentData() or "").strip() or self._default_mode or ("directory" if self._is_dir else "single")


    def _copy_path_to_clipboard(self):

        QApplication.clipboard().setText(self._path)


    def _copy_summary_to_clipboard(self):

        summary = [
            tr("IMPORT_SUGGESTION_TITLE") if not self._is_manual_choice else tr("IMPORT_SETUP_TITLE"),
            f"{tr('IMPORT_SUGGESTION_PATH')}: {self._path}",
            f"{tr('IMPORT_SUGGESTION_REASON')}: {self._reason_label.text()}",
            f"{tr('IMPORT_SUGGESTION_TECHNIQUE')}: {self._technique_combo.currentText()}",
            f"{tr('IMPORT_SUGGESTION_SUBMODULE')}: {self._submodule_combo.currentText()}",
            f"{tr('IMPORT_SUGGESTION_MODE')}: {self._mode_combo.currentText()}",
        ]
        QApplication.clipboard().setText(" | ".join(summary))


    def _open_path_folder(self):

        folder = self._path if self._is_dir else os.path.dirname(self._path)
        if not folder:
            folder = self._path
        try:
            os.startfile(folder)
        except OSError:
            pass


class MainWindow(
    MainWindowSummaryMixin,
    MainWindowImportMixin,
    MainWindowRunMixin,
    MainWindowGuidancePanelsMixin,
    MainWindowRetranslateMixin,
    MainWindowShellMixin,
    MainWindowSettingsMixin,
    MainWindowWorkspaceMixin,
    MainWindowFigureMixin,
    MainWindowOutputMixin,
    MainWindowHistoryMixin,
    MainWindowResultsMixin,
    MainWindowAITuningMixin,
    MainWindowCalibrationMixin,
    MainWindowConfigPanelMixin,
    MainWindowJointDiagnosticsMixin,
    MainWindowNavigationMixin,
    MainWindowResultSemanticsMixin,
    MainWindowSampleHubMixin,
    QMainWindow,
):

    def __init__(self, *, defer_optional_ui: bool = False):

        super().__init__()

        self._startup_deferred = bool(defer_optional_ui)
        self._deferred_startup_scheduled = False
        self._deferred_startup_finished = not self._startup_deferred
        self._deferred_startup_failed = False

        self.setWindowTitle(tr("WINDOW_TITLE"))

        self.resize(1280, 820)

        self.setMinimumSize(960, 600)

        self.setAcceptDrops(True)



        # Theme engine

        self._theme_engine = ThemeEngine.instance()



        self._workspace_mode = WorkspaceMode.ANALYSIS
        self._current_technique = ""
        self._current_submodule_id = ""

        self._current_filepath = ""
        self._current_input_mode = ""
        self._current_sample_id = ""
        self._current_batch_id = ""
        self._current_sample_name = ""
        self._current_batch_label = ""

        self._output_dir = ""

        self._results = {}

        self._batch_results = []

        self._current_figure_path = ""

        self._engine_cache = {}

        self._worker = None

        self._batch_worker = None

        self._recent_projects = []

        self._sidebar_expanded_width = 232
        self._sample_db = None
        self._joint_report = None
        self._context_suggestion_panels = {}
        self._context_suggestion_action_map = {}
        self._work_memory_panels = {}
        self._work_memory_action_map = {}
        self._last_export_bundle = ""
        self._ai_tuning_active = False
        self._last_ai_tuning_context = {}
        self._current_ai_tuning_goal = "symptom"
        self._last_persisted_run_id = ""
        self._run_state = RunState()
        self._run_stage_key = ""
        self._workspace_context = WorkspaceContext.empty()
        self._result_contexts = {}
        self._current_result_confirmed_flag = False
        self._results_compare_selected_run_id = ""



        self._settings = QSettings("PolyNexus", "PolyNexus")

        self._load_settings()

        self._build_ui()

        self._apply_theme()



        # ---- v1.1: Connect PolyNexusLogger to the GUI log panel ----

        self._log_signal = None  # placeholder, signals wired in _build_ui

        self._connect_logger()

        self._retranslate_ui()

        self._update_workspace_context()



        # Re-polish the sidebar after the first retranslate/theme pass.

        sb = self.findChild(QWidget, "sidebar")

        if sb:

            sb.setVisible(True)



        # Bind keyboard shortcuts

        bind_shortcuts(self)

    def schedule_deferred_startup(self) -> None:
        """Build non-critical widgets after the first window paint."""
        if (
            not self._startup_deferred
            or self._deferred_startup_finished
            or self._deferred_startup_scheduled
            or self._deferred_startup_failed
        ):
            return
        self._deferred_startup_scheduled = True
        QTimer.singleShot(0, self.finish_deferred_startup)

    def finish_deferred_startup(self) -> None:
        """Complete optional GUI construction exactly once."""
        if (
            not self._startup_deferred
            or self._deferred_startup_finished
            or self._deferred_startup_failed
        ):
            return

        self._deferred_startup_scheduled = False
        try:
            self._build_data_optional_widgets()
            deferred_tabs = (
                (1, self._build_config_tab, "TAB_CONFIG"),
                (2, self._build_results_tab, "TAB_RESULTS"),
                (3, self._build_plots_tab, "TAB_PLOTS"),
                (4, self._build_history_panel, "TAB_HISTORY"),
            )
            for index, builder, title_key in deferred_tabs:
                self._replace_deferred_tab(index, builder(), tr(title_key))
            self._retranslate_ui()
            self._update_workspace_context()
            self.setup_convergence_action()
            self._deferred_startup_finished = True
        except Exception as exc:
            self._deferred_startup_failed = True
            logger.exception("Deferred GUI startup failed")
            self._show_deferred_startup_error(exc)

    def _replace_deferred_tab(self, index, widget, title) -> None:
        current_index = self._tabs.currentIndex()
        self._tabs.removeTab(index)
        self._tabs.insertTab(index, widget, title)
        if current_index == index:
            self._tabs.setCurrentIndex(index)

    def _show_deferred_startup_error(self, exc: Exception) -> None:
        message = QLabel(
            tr("WORKFLOW_TASK_DEFAULT_DETAIL")
            + f"\n\nOptional workspace initialization failed: {exc}"
        )
        message.setWordWrap(True)
        message.setObjectName("deferred_startup_error")
        self._replace_deferred_tab(1, message, tr("TAB_CONFIG"))



    def _connect_logger(self):

        """Suppress console output in GUI mode.



        Analysis-run logging is handled by AnalysisWorker / BatchWorker,

        which attach the QtLogHandler to their log_msg Signal internally.

        """

        from ..utils.logger import PolyNexusLogger

        PolyNexusLogger.get().disable_console()



    def _build_ui(self):

        self._build_menubar()

        self._build_statusbar()



        central = QWidget()

        self.setCentralWidget(central)

        root = QVBoxLayout(central)

        root.setContentsMargins(0, 0, 0, 0)

        root.setSpacing(0)

        root.addWidget(self._build_topbar())

        self._main_splitter = QSplitter(Qt.Horizontal)

        self._main_splitter.setHandleWidth(1)

        self._sidebar = self._build_sidebar()

        self._content = self._build_content()

        self._main_splitter.addWidget(self._sidebar)

        self._main_splitter.addWidget(self._content)

        self._main_splitter.setSizes([self._sidebar_expanded_width, 1080])

        self._main_splitter.setStretchFactor(0, 0)

        self._main_splitter.setStretchFactor(1, 1)

        self._main_splitter.setCollapsible(0, False)

        self._main_splitter.setCollapsible(1, False)

        root.addWidget(self._main_splitter, 1)



    def _build_topbar(self):

        bar = QWidget()

        bar.setObjectName("topbar")

        layout = QHBoxLayout(bar)
        self._topbar_layout = layout

        layout.setContentsMargins(24, 0, 18, 0)

        layout.setSpacing(12)



        icon_lbl = QLabel(tr("WINDOW_TITLE").split()[0])

        icon_lbl.setStyleSheet(

            "font-size: 18px; font-weight: 700; letter-spacing: 0; "

            "background: transparent; border: none; padding: 0;"

        )

        layout.addWidget(icon_lbl)

        layout.addWidget(QFrame())



        self._project_badge = QWidget()

        self._project_badge.setObjectName("project_badge")

        bl = QHBoxLayout(self._project_badge)

        bl.setContentsMargins(8, 0, 8, 0)

        self._project_label = QLabel(tr("NO_PROJECT"))

        self._project_label.setStyleSheet(

            "color: #168e9f; font-weight: 600; font-size: 12px; "

            "background: transparent; border: none;"

        )

        bl.addWidget(self._project_label)

        layout.addWidget(self._project_badge)



        layout.addStretch()



        self._btn_run = QPushButton(tr("BTN_RUN"))
        self._btn_cancel = QPushButton(tr("BTN_CANCEL"))
        self._btn_cancel.setObjectName("secondary_btn")
        self._btn_cancel.setVisible(False)
        self._btn_cancel.clicked.connect(self._cancel_run)
        self._btn_retry = QPushButton(tr("BTN_RETRY"))
        self._btn_retry.setObjectName("secondary_btn")
        self._btn_retry.setVisible(False)
        self._btn_retry.clicked.connect(self._run_analysis)
        self._btn_copy_diagnostics = QPushButton(tr("BTN_COPY_DIAGNOSTICS"))
        self._btn_copy_diagnostics.setObjectName("secondary_btn")
        self._btn_copy_diagnostics.setVisible(False)
        self._btn_copy_diagnostics.clicked.connect(self._copy_error_diagnostics)

        self._btn_replot = QPushButton(tr("BTN_REPLOT"))

        self._btn_replot.setObjectName("secondary_btn")

        self._btn_replot.setEnabled(False)

        self._btn_replot.clicked.connect(self._replot)

        self._btn_replot.setToolTip(tr("REPLOT_TOOLTIP"))



        # Theme toggle

        self._btn_theme = QPushButton("\u263e" if ThemeEngine.instance().is_dark else "\u2600")

        self._btn_theme.setObjectName("theme_btn")

        self._btn_theme.setFixedWidth(36)

        self._btn_theme.clicked.connect(self._toggle_theme)

        self._btn_theme.setToolTip(tr("THEME_TOGGLE_TOOLTIP"))

        layout.addWidget(self._btn_theme)



        # Language switch

        self._btn_lang = QPushButton("\u4e2d" if get_language() != "zh" else "EN")

        self._btn_lang.setObjectName("lang_btn")

        self._btn_lang.setFixedWidth(36)

        self._btn_lang.clicked.connect(self._toggle_language)
        self._btn_lang.setToolTip(tr("LANG_TOGGLE_TOOLTIP"))


        layout.addWidget(self._btn_lang)

        self._btn_run.setObjectName("primary_btn")

        self._btn_run.clicked.connect(self._run_analysis)

        self._btn_run.setEnabled(False)

        layout.addWidget(self._btn_replot)

        layout.addWidget(self._btn_run)
        layout.addWidget(self._btn_cancel)
        layout.addWidget(self._btn_retry)
        layout.addWidget(self._btn_copy_diagnostics)



        self._btn_export_current = QPushButton(tr("BTN_EXPORT_CURRENT"))
        self._btn_export_current.setObjectName("secondary_btn")
        self._btn_export_current.clicked.connect(lambda: self._export_results(scope="current"))
        layout.addWidget(self._btn_export_current)

        self._btn_export = QPushButton(tr("BTN_EXPORT_PROJECT"))

        self._btn_export.setObjectName("secondary_btn")

        self._btn_export.clicked.connect(self._export_results)

        layout.addWidget(self._btn_export)

        return bar


    def setup_convergence_action(self):
        """Keep the View-menu review action as the compatibility route."""
        return getattr(self, "action_convergence_viewer", None)


    def _open_convergence_viewer(self):

        """Open the result review window in a separate window."""

        if hasattr(self, "_convergence_win") and self._convergence_win is not None:
            self._convergence_win = open_convergence_viewer(
                self._convergence_win,
                viewer_factory=lambda parent=None: self._convergence_win,
            )
            return

        from polynexus.gui.convergence_viewer import ConvergenceViewer

        self._convergence_win = open_convergence_viewer(
            None,
            viewer_factory=ConvergenceViewer,
            closed_handler=self._on_convergence_closed,
            warning_handler=lambda exc: QMessageBox.warning(
                self,
                tr("CONVERGENCE_DASHBOARD"),
                tr("CONVERGENCE_OPEN_FAILED", exc),
            ),
            critical_handler=lambda exc: QMessageBox.critical(
                self,
                tr("CONVERGENCE_DASHBOARD"),
                tr("CONVERGENCE_OPEN_FAILED", exc),
            ),
            logger=logger,
        )


    def _on_convergence_closed(self):

        self._convergence_win = None



    def _build_sidebar(self):

        sidebar = QWidget()

        sidebar.setObjectName("sidebar")

        sidebar.setMinimumWidth(self._sidebar_expanded_width)

        outer_layout = QVBoxLayout(sidebar)

        outer_layout.setContentsMargins(0, 0, 0, 0)

        outer_layout.setSpacing(0)

        self._sidebar_scroll = QScrollArea()

        self._sidebar_scroll.setObjectName("sidebar_scroll")

        self._sidebar_scroll.setWidgetResizable(True)

        self._sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._sidebar_scroll.setFrameShape(QFrame.NoFrame)

        outer_layout.addWidget(self._sidebar_scroll, 1)

        self._sidebar_section_labels = {}

        # Fixed recent projects panel (pinned at the bottom, outside the scroll area).
        self._recent_panel = QWidget()
        self._recent_panel.setObjectName("sidebar_recent_panel")
        panel_layout = QVBoxLayout(self._recent_panel)
        panel_layout.setContentsMargins(0, 0, 0, 8)
        panel_layout.setSpacing(0)

        recent_title = QLabel(_lang_text(SIDEBAR_SECTIONS["recent"]))
        recent_title.setObjectName("sidebar_title")
        recent_title.setMinimumHeight(28)
        recent_title.setMaximumHeight(28)
        self._sidebar_section_labels["recent"] = recent_title
        panel_layout.addWidget(recent_title)

        recent_actions = QWidget()
        recent_actions_layout = QHBoxLayout(recent_actions)
        recent_actions_layout.setContentsMargins(0, 0, 0, 0)
        recent_actions_layout.setSpacing(6)
        recent_actions_layout.addStretch(1)
        self._recent_list_copy_button = QPushButton(tr("COMMON_COPY"))
        self._recent_list_copy_button.clicked.connect(self._copy_recent_projects_to_clipboard)
        recent_actions_layout.addWidget(self._recent_list_copy_button)
        panel_layout.addWidget(recent_actions)

        self._recent_list = QListWidget()
        self._recent_list.setMaximumHeight(120)
        self._recent_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._recent_list.itemDoubleClicked.connect(self._open_recent)
        self._recent_list.itemActivated.connect(self._open_recent)
        self._recent_list_copy_shortcut = QShortcut(QKeySequence.Copy, self._recent_list)
        self._recent_list_copy_shortcut.activated.connect(self._copy_recent_projects_to_clipboard)
        self._refresh_recent_list()
        panel_layout.addWidget(self._recent_list)

        outer_layout.addWidget(self._recent_panel)

        nav_host = QWidget()

        nav_host.setObjectName("sidebar_content")

        nav_host.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        layout = QVBoxLayout(nav_host)

        layout.setContentsMargins(0, 10, 0, 10)

        layout.setSpacing(0)

        layout.setSizeConstraint(QLayout.SetMinimumSize)

        self._sidebar_scroll.setWidget(nav_host)



        # Experimental techniques.
        exp_lbl = QLabel(_lang_text(SIDEBAR_SECTIONS["experiment"]))
        exp_lbl.setObjectName("sidebar_title")
        exp_lbl.setMinimumHeight(28)
        exp_lbl.setMaximumHeight(28)
        self._sidebar_section_labels["experiment"] = exp_lbl
        layout.addWidget(exp_lbl)



        self._nav_buttons = {}

        self._nav_parent_buttons = {}

        self._nav_group = QButtonGroup(self)

        self._nav_group.setExclusive(True)



        # Registry-driven two-level tree.

        from ..core.submodule_registry import list_all_submodules

        all_mods = list_all_submodules()

        tech_groups = {}

        for mod in all_mods:

            tech = mod['technique']

            if tech == 'joint':

                continue

            if tech not in tech_groups:

                tech_groups[tech] = []

            tech_groups[tech].append(mod)



        tech_order = ['saxs', 'waxs', 'dsc', 'ir', 'nmr']

        for tech in tech_order:
            # Insert computational section header before first computational tech
            if tech == 'ir':
                layout.addSpacing(12)
                comp_lbl = QLabel(_lang_text(SIDEBAR_SECTIONS["compute"]))
                comp_lbl.setObjectName("sidebar_title")
                comp_lbl.setMinimumHeight(28)
                comp_lbl.setMaximumHeight(28)
                self._sidebar_section_labels["compute"] = comp_lbl
                comp_lbl.setText(_lang_text(SIDEBAR_SECTIONS["compute"]))
                layout.addWidget(comp_lbl)

            if tech not in tech_groups:

                continue

            mods = tech_groups[tech]

            icon = TECHNIQUE_ICONS.get(tech, '')

            label = TECHNIQUE_LABELS.get(tech, tech.upper())

            parent_btn = QPushButton(f"{icon}  {label}")

            parent_btn.setObjectName("nav_parent_btn")
            parent_btn.setMinimumHeight(28)
            parent_btn.setMaximumHeight(28)

            parent_btn.setCheckable(False)

            parent_btn.setCursor(Qt.PointingHandCursor)

            parent_btn.setToolTip(tr("SIDEBAR_SUBMODULE_COUNT", len(mods)))

            parent_btn.setProperty("technique", tech)

            parent_btn.setStyleSheet(self._nav_parent_style(tech))

            self._nav_parent_buttons[tech] = parent_btn

            layout.addWidget(parent_btn)



            for mod in mods:

                btn = QPushButton(_lang_text(
                    SIDEBAR_MODULE_TEXT.get(mod['id'], {}),
                    mod['label'],
                ))

                btn.setObjectName("nav_sub_btn")
                btn.setMinimumHeight(32)
                btn.setMaximumHeight(32)

                btn.setCheckable(True)

                btn.setCursor(Qt.PointingHandCursor)

                btn.setToolTip(mod.get('description', ''))

                btn.setProperty("technique", tech)

                btn.setProperty("nav_id", mod['id'])

                btn.setStyleSheet(self._nav_sub_style(tech, False))

                btn.clicked.connect(

                    lambda checked, t=tech, mid=mod['id']:

                        self._on_submodule_selected(t, mid)

                )

                self._nav_group.addButton(btn)

                self._nav_buttons[mod['id']] = btn

                layout.addWidget(btn)



        layout.addSpacing(12)



        # Joint analysis section.

        joint_title = QLabel(_lang_text(SIDEBAR_SECTIONS["joint"]))

        joint_title.setObjectName("sidebar_title")
        joint_title.setMinimumHeight(28)
        joint_title.setMaximumHeight(28)
        self._sidebar_section_labels["joint"] = joint_title

        layout.addWidget(joint_title)



        for jid in ["joint.quick", "joint.compare"]:

            btn = QPushButton(_lang_text(SIDEBAR_MODULE_TEXT[jid]))

            btn.setObjectName("nav_sub_btn")
            btn.setMinimumHeight(32)
            btn.setMaximumHeight(32)

            btn.setCheckable(True)

            btn.setCursor(Qt.PointingHandCursor)

            btn.setToolTip(_lang_text(SIDEBAR_MODULE_TOOLTIPS.get(jid, {})))

            btn.setProperty("technique", "joint")

            btn.setProperty("nav_id", jid)

            btn.setStyleSheet(self._nav_sub_style("joint", False))

            btn.clicked.connect(

                lambda checked, mid=jid: self._on_joint_selected(mid)

            )

            self._nav_group.addButton(btn)

            self._nav_buttons[jid] = btn

            layout.addWidget(btn)



        layout.addSpacing(12)



        # Sample library section.

        samples_title = QLabel(_lang_text(SIDEBAR_SECTIONS["samples"]))

        samples_title.setObjectName("sidebar_title")
        samples_title.setMinimumHeight(28)
        samples_title.setMaximumHeight(28)
        self._sidebar_section_labels["samples"] = samples_title

        layout.addWidget(samples_title)



        btn_samples = QPushButton(_lang_text(SIDEBAR_MODULE_TEXT["samples"]))

        btn_samples.setObjectName("nav_sub_btn")
        btn_samples.setMinimumHeight(32)
        btn_samples.setMaximumHeight(32)

        btn_samples.setCheckable(True)

        btn_samples.setCursor(Qt.PointingHandCursor)



        btn_samples.setProperty("technique", "samples")

        btn_samples.setProperty("nav_id", "samples")

        btn_samples.setStyleSheet(self._nav_sub_style("joint", False))

        btn_samples.clicked.connect(lambda checked: self._on_samples_selected())

        self._nav_group.addButton(btn_samples)

        self._nav_buttons["samples"] = btn_samples
        btn_samples.setToolTip(tr("SAMPLE_LIBRARY_TOOLTIP"))

        layout.addWidget(btn_samples)

        self._nav_indicator = QFrame(sidebar)

        self._nav_indicator.setObjectName("nav_indicator")

        self._nav_indicator.hide()

        self._refresh_sidebar_texts()

        return sidebar


    def _nav_parent_style(self, technique):

        t = self._theme_engine.tokens

        accent = technique_accent(technique, t)

        return (
            "QPushButton {"
            "  background: transparent; border: none;"
            "  text-align: left; padding: 6px 24px; margin: 1px 10px;"
            f"  color: {accent}; font-weight: 650; font-size: 13px;"
            "  min-height: 26px; max-height: 26px;"
            "}"
            "QPushButton:hover {"
            f"  background-color: {t.bg_hover}; color: {t.text_primary};"
            "}"
        )


    def _nav_sub_style(self, technique, active=False):

        t = self._theme_engine.tokens

        accent = technique_accent(technique if technique != "samples" else "joint", t)

        bg = t.bg_card if active else "transparent"

        border = "transparent"

        left_border = accent if active else "transparent"

        text = accent if active else t.text_secondary

        weight = 650 if active else 450

        return (
            "QPushButton {"
            f"  background-color: {bg};"
            f"  border: 1px solid {border};"
            f"  border-left: 3px solid {left_border};"
            f"  border-radius: {t.radius_sm}px;"
            "  text-align: left;"
            "  padding: 5px 12px 5px 40px;"
            "  margin: 1px 10px;"
            f"  color: {text};"
            f"  font-size: {t.font_size_base}px;"
            f"  font-weight: {weight};"
            "  min-height: 30px; max-height: 30px;"
            "}"
            "QPushButton:checked {"
            f"  background-color: {bg};"
            f"  border: 1px solid {border};"
            f"  border-left: 3px solid {left_border};"
            f"  color: {text};"
            f"  font-weight: {weight};"
            "}"
            "QPushButton:hover {"
            f"  background-color: {t.bg_hover};"
            f"  color: {t.text_primary};"
            "}"
            "QPushButton:checked:hover {"
            f"  background-color: {bg};"
            f"  border-left: 3px solid {left_border};"
            f"  color: {text};"
            "}"
        )


    def _is_native_directory_run_context(self):

        if not self._current_filepath or not os.path.isdir(self._current_filepath):
            return False

        submodule_id = str(getattr(self, "_current_submodule_id", "") or "").strip()
        return (
            self._current_technique in ("saxs", "waxs")
            or self._current_technique == "nmr"
            or submodule_id in ("dsc.isothermal", "dsc.nonisothermal", "ir.temperature_2d")
        )


    def _idle_workflow_state_text(self):

        if not self._current_filepath or not os.path.isdir(self._current_filepath):
            return tr("WORKFLOW_READY")

        if self._is_native_directory_run_context():
            if str(getattr(self, "_current_input_mode", "") or "").strip().lower() == "sequence":
                return tr("WORKFLOW_SEQUENCE_READY")
            return tr("WORKFLOW_DIRECTORY_READY")

        return tr("WORKFLOW_BATCH_READY")


    def _set_drop_banner_visible(self, visible):

        if not hasattr(self, "_drop_banner"):

            return

        if visible:

            self._drop_banner.setVisible(True)

            fade_in(self._drop_banner, duration=140, start=0.2)

        else:

            self._drop_banner.setVisible(False)


    def _on_tab_changed(self, index):

        widget = self._tabs.widget(index) if hasattr(self, "_tabs") else None

        if widget is not None:

            fade_in(widget, duration=170, start=0.35)
        self._update_context_suggestions()


    def _set_running_ui(self, running, label=None):

        self._btn_run.setProperty("busy", running)

        self._btn_run.style().unpolish(self._btn_run)

        self._btn_run.style().polish(self._btn_run)

        if running:

            if hasattr(self, "_log_group"):
                self._log_group.setChecked(True)

            start_busy_pulse(self._btn_run)

            if hasattr(self, "_workflow_metric_state"):

                self._workflow_metric_state.setText(label or tr("BTN_RUNNING"))

        else:

            stop_busy_pulse(self._btn_run)

            if hasattr(self, "_workflow_metric_state"):

                self._workflow_metric_state.setText(self._idle_workflow_state_text())

        self._update_workflow_task_card()


    def _copy_batch_list_to_clipboard(self):

        batch_list = getattr(self, "_batch_list", None)
        if batch_list is None:
            return

        selected = [
            item.text()
            for item in batch_list.selectedItems()
            if str(item.text() or "").strip()
        ]
        if not selected:
            selected = [
                batch_list.item(index).text()
                for index in range(batch_list.count())
                if batch_list.item(index) is not None and str(batch_list.item(index).text() or "").strip()
        ]
        if selected:
            QApplication.clipboard().setText("\n".join(selected))

    def _update_batch_list_copy_button(self):

        batch_list = getattr(self, "_batch_list", None)
        button = getattr(self, "_batch_list_copy_button", None)
        if batch_list is None or button is None:
            return

        visible = not batch_list.isHidden()
        has_items = batch_list.count() > 0
        button.setVisible(visible)
        button.setEnabled(visible and has_items)


    def _build_content(self):

        content_scroll = QScrollArea()

        content_scroll.setObjectName("workspace_scroll")

        content_scroll.setWidgetResizable(True)

        content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content_scroll.setFrameShape(QFrame.NoFrame)

        content = ScientificBackdrop()

        content.setObjectName("workspace")

        content.setMinimumHeight(720)

        content_scroll.setWidget(content)

        layout = QVBoxLayout(content)

        layout.setContentsMargins(16, 14, 16, 0)

        layout.setSpacing(10)


        header = QWidget()

        header.setObjectName("workflow_header")

        header_layout = QHBoxLayout(header)

        header_layout.setContentsMargins(14, 10, 14, 10)

        header_layout.setSpacing(12)

        title_box = QVBoxLayout()

        title_box.setSpacing(2)

        self._workspace_title = QLabel(tr("WORKSPACE_TITLE_DEFAULT"))

        self._workspace_title.setObjectName("workspace_title")

        self._workspace_subtitle = QLabel(tr("WORKSPACE_SUBTITLE_DEFAULT"))

        self._workspace_subtitle.setObjectName("workspace_subtitle")

        self._workspace_context_summary_label = QLabel()

        self._workspace_context_summary_label.setObjectName("workspace_context_summary")

        self._workspace_context_summary_label.setWordWrap(True)

        title_box.addWidget(self._workspace_title)

        title_box.addWidget(self._workspace_subtitle)

        title_box.addWidget(self._workspace_context_summary_label)

        header_layout.addLayout(title_box, 1)

        self._workflow_task_box = QFrame()
        self._workflow_task_box.setObjectName("workflow_task_box")
        task_layout = QVBoxLayout(self._workflow_task_box)
        task_layout.setContentsMargins(12, 8, 12, 8)
        task_layout.setSpacing(2)

        self._workflow_task_label = QLabel(tr("WORKFLOW_TASK_LABEL"))
        self._workflow_task_label.setObjectName("workflow_task_label")
        task_layout.addWidget(self._workflow_task_label)

        self._workflow_task_title = QLabel(tr("WORKFLOW_TASK_DEFAULT_TITLE"))
        self._workflow_task_title.setObjectName("workflow_task_title")
        task_layout.addWidget(self._workflow_task_title)

        self._workflow_task_detail = QLabel(tr("WORKFLOW_TASK_DEFAULT_DETAIL"))
        self._workflow_task_detail.setObjectName("workflow_task_detail")
        self._workflow_task_detail.setWordWrap(True)
        task_layout.addWidget(self._workflow_task_detail)

        header_layout.addWidget(self._workflow_task_box, 1)

        self._workflow_metric_tech = QLabel(tr("WORKSPACE_TITLE_DEFAULT"))

        self._workflow_metric_tech.setObjectName("workflow_metric")

        header_layout.addWidget(self._workflow_metric_tech)

        self._workflow_metric_data = QLabel(tr("WORKFLOW_NO_DATA"))

        self._workflow_metric_data.setObjectName("workflow_metric")

        header_layout.addWidget(self._workflow_metric_data)

        self._workflow_metric_state = QLabel(tr("WORKFLOW_READY"))

        self._workflow_metric_state.setObjectName("workflow_metric")

        header_layout.addWidget(self._workflow_metric_state)

        layout.addWidget(header)


        self._drop_banner = QFrame()

        self._drop_banner.setObjectName("drop_banner")

        drop_layout = QHBoxLayout(self._drop_banner)

        drop_layout.setContentsMargins(14, 0, 14, 0)

        self._drop_label = QLabel(tr("DROP_HINT"))

        self._drop_label.setAlignment(Qt.AlignCenter)

        drop_layout.addWidget(self._drop_label)

        self._drop_banner.setVisible(False)

        layout.addWidget(self._drop_banner)



        self._tabs = QTabWidget()

        self._tabs.addTab(self._build_data_tab(), tr("TAB_DATA"))

        if self._startup_deferred:
            for title_key in ("TAB_CONFIG", "TAB_RESULTS", "TAB_PLOTS", "TAB_HISTORY"):
                self._tabs.addTab(self._build_deferred_tab_placeholder(title_key), tr(title_key))
        else:
            self._tabs.addTab(self._build_config_tab(), tr("TAB_CONFIG"))
            self._tabs.addTab(self._build_results_tab(), tr("TAB_RESULTS"))
            self._tabs.addTab(self._build_plots_tab(), tr("TAB_PLOTS"))
            history_widget = self._build_history_panel()
            self._tabs.addTab(history_widget, tr("TAB_HISTORY"))

        self._tabs.currentChanged.connect(self._on_tab_changed)

        layout.addWidget(self._tabs, 2)



        self._log_group = QGroupBox(tr("GROUP_LOG"))
        self._log_group.setCheckable(True)
        self._log_group.setChecked(False)
        self._log_group.toggled.connect(self._set_log_drawer_expanded)

        log_glayout = QVBoxLayout(self._log_group)

        log_glayout.setContentsMargins(8, 16, 8, 8)



        self._log_panel = QTextEdit()

        self._log_panel.setReadOnly(True)

        self._log_panel.setMaximumHeight(150)

        self._log_panel.setMinimumHeight(80)

        log_glayout.addWidget(self._log_panel)



        self._progress = QProgressBar()

        self._progress.setVisible(False)

        self._progress.setMaximumHeight(6)

        self._progress.setTextVisible(False)

        log_glayout.addWidget(self._progress)

        batch_actions = QHBoxLayout()
        batch_actions.setContentsMargins(0, 0, 0, 0)
        batch_actions.setSpacing(6)
        batch_actions.addStretch(1)
        self._batch_list_copy_button = QPushButton(tr("COMMON_COPY"))
        self._batch_list_copy_button.clicked.connect(self._copy_batch_list_to_clipboard)
        self._batch_list_copy_button.setVisible(False)
        batch_actions.addWidget(self._batch_list_copy_button)
        log_glayout.addLayout(batch_actions)



        self._batch_list = QListWidget()

        self._batch_list.setVisible(False)

        self._batch_list.setMaximumHeight(60)
        self._batch_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._batch_list_copy_shortcut = QShortcut(QKeySequence.Copy, self._batch_list)
        self._batch_list_copy_shortcut.activated.connect(self._copy_batch_list_to_clipboard)

        log_glayout.addWidget(self._batch_list)

        self._set_log_drawer_expanded(False)



        layout.addWidget(self._log_group, 1)

        return content_scroll

    def _build_deferred_tab_placeholder(self, title_key):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        label = QLabel(tr("WORKFLOW_TASK_DEFAULT_DETAIL"))
        label.setObjectName(f"deferred_{title_key.lower()}_placeholder")
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)
        layout.addWidget(label)
        return widget



    def _build_data_tab(self):

        w = QWidget()

        layout = QVBoxLayout(w)

        layout.setSpacing(12)



        input_group = self._data_source_group = QGroupBox(tr("GROUP_DATA_SOURCE"))

        ig = QVBoxLayout(input_group)
        self._data_context_hint = self._build_context_suggestion_panel("data")
        ig.addWidget(self._data_context_hint)

        fl = QHBoxLayout()

        self._data_file_label = QLabel(tr("DATA_FILE_LABEL"))

        fl.addWidget(self._data_file_label)

        self._path_input = QLineEdit()

        self._path_input.setObjectName("path_input")

        self._path_input.setPlaceholderText(tr("DATA_DROP_HINT"))

        fl.addWidget(self._path_input, 1)

        btn_file = QPushButton(tr("DATA_FILE_TYPE"))

        btn_file.clicked.connect(self._browse_file)

        fl.addWidget(btn_file)

        btn_folder = QPushButton(tr("DATA_FOLDER_TYPE"))

        btn_folder.clicked.connect(self._browse_folder)

        fl.addWidget(btn_folder)

        ig.addLayout(fl)

        layout.addWidget(input_group)



        batch_group = self._output_group = QGroupBox(
            "\u8f93\u51fa" if get_language() == "zh" else "Output"
        )

        bg = QVBoxLayout(batch_group)

        bh = QHBoxLayout()

        self._data_output_label = QLabel(tr("DATA_OUTPUT_DIR"))

        bh.addWidget(self._data_output_label)

        self._output_input = QLineEdit()

        self._output_input.setPlaceholderText(tr("DATA_BTN_OUTPUT"))

        self._output_input.setText(self._output_dir)

        bh.addWidget(self._output_input, 1)

        self._data_btn_browse = QPushButton(tr("DATA_BTN_BROWSE"))

        btn_out = self._data_btn_browse

        btn_out.clicked.connect(self._browse_output)

        bh.addWidget(btn_out)

        bg.addLayout(bh)

        layout.addWidget(batch_group)

        self._data_optional_host = QWidget()
        self._data_optional_layout = QVBoxLayout(self._data_optional_host)
        self._data_optional_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._data_optional_host, 1)

        self._joint_hub = None
        self._sample_browser = None
        if self._startup_deferred:
            self._data_optional_placeholder = QLabel(tr("WORKFLOW_TASK_DEFAULT_DETAIL"))
            self._data_optional_placeholder.setAlignment(Qt.AlignCenter)
            self._data_optional_layout.addWidget(self._data_optional_placeholder)
        else:
            self._build_data_optional_widgets()

        layout.addStretch()

        return w

    def _build_data_optional_widgets(self) -> None:
        if self._joint_hub is not None or self._sample_browser is not None:
            return

        from .widgets.joint_analysis_hub import JointAnalysisHub
        from .widgets.sample_browser import SampleBrowser

        placeholder = getattr(self, "_data_optional_placeholder", None)
        if placeholder is not None:
            self._data_optional_layout.removeWidget(placeholder)
            placeholder.deleteLater()
            self._data_optional_placeholder = None

        self._joint_hub = JointAnalysisHub()
        self._joint_hub.selection_changed.connect(self._on_joint_hub_selection_changed)
        self._joint_hub.run_requested.connect(self._run_joint_hub)
        self._joint_hub.setVisible(False)
        self._data_optional_layout.addWidget(self._joint_hub, 1)

        self._sample_browser = SampleBrowser()
        self._sample_browser.sample_created.connect(self._on_sample_created)
        self._sample_browser.sample_updated.connect(self._on_sample_updated)
        self._sample_browser.sample_selected.connect(self._on_sample_selected)
        self._sample_browser.batch_created.connect(self._on_sample_batch_created)
        self._sample_browser.batch_updated.connect(self._on_sample_batch_updated)
        self._sample_browser.batch_analysis_requested.connect(
            self._on_sample_batch_analysis_requested
        )
        self._sample_browser.joint_analysis_requested.connect(self._on_sample_joint_requested)
        self._sample_browser.setVisible(False)
        self._data_optional_layout.addWidget(self._sample_browser, 1)



    def _build_config_tab(self):

        w = QWidget()

        layout = QVBoxLayout(w)

        preset_row = QHBoxLayout()
        preset_row.setSpacing(6)

        self._config_preset_label = QLabel()
        preset_row.addWidget(self._config_preset_label)

        self._config_preset_combo = QComboBox()
        self._config_preset_combo.setEditable(True)
        self._config_preset_combo.setInsertPolicy(QComboBox.NoInsert)
        self._config_preset_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._config_preset_combo.editTextChanged.connect(self._on_config_preset_name_changed)
        preset_row.addWidget(self._config_preset_combo, 1)

        self._btn_config_preset_save = QPushButton()
        self._btn_config_preset_save.setObjectName("secondary_btn")
        self._btn_config_preset_save.clicked.connect(self._on_save_config_preset)
        preset_row.addWidget(self._btn_config_preset_save)

        self._btn_config_preset_load = QPushButton()
        self._btn_config_preset_load.setObjectName("secondary_btn")
        self._btn_config_preset_load.clicked.connect(self._on_load_config_preset)
        preset_row.addWidget(self._btn_config_preset_load)

        self._btn_config_preset_delete = QPushButton()
        self._btn_config_preset_delete.setObjectName("secondary_btn")
        self._btn_config_preset_delete.clicked.connect(self._on_delete_config_preset)
        preset_row.addWidget(self._btn_config_preset_delete)

        self._btn_config_recent_calibration_save = QPushButton()
        self._btn_config_recent_calibration_save.setObjectName("secondary_btn")
        self._btn_config_recent_calibration_save.clicked.connect(self._on_save_recent_calibration)
        preset_row.addWidget(self._btn_config_recent_calibration_save)

        self._btn_config_recent_calibration = QPushButton()
        self._btn_config_recent_calibration.setObjectName("secondary_btn")
        self._btn_config_recent_calibration.clicked.connect(self._on_apply_recent_calibration)
        preset_row.addWidget(self._btn_config_recent_calibration)

        layout.addLayout(preset_row)

        self._config_context_hint = self._build_context_suggestion_panel("config")
        layout.addWidget(self._config_context_hint)

        scroll = QScrollArea()

        scroll.setWidgetResizable(True)

        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self._config_widget = QWidget()

        self._config_form = QFormLayout(self._config_widget)

        self._config_form.setSpacing(8)

        placeholder = self._config_placeholder = QLabel(tr("CONFIG_PLACEHOLDER"))

        placeholder.setStyleSheet(f"color: {C_TEXT_MUTED}; padding: 20px;")

        self._config_form.addRow(placeholder)

        scroll.setWidget(self._config_widget)

        layout.addWidget(scroll)

        layout.addStretch()

        self._refresh_config_preset_controls()

        return w



    def _build_plots_tab(self):

        """Plots tab: exported figure gallery and focused figure preview."""

        from .widgets.chart_viewer import ChartGallery, FigureFilePreview

        w = QWidget()

        layout = QVBoxLayout(w)

        layout.setSpacing(8)

        gallery_header = QWidget()
        gallery_header.setObjectName("gallery_page_header")
        gallery_header_layout = QHBoxLayout(gallery_header)
        gallery_header_layout.setContentsMargins(4, 4, 4, 0)
        gallery_header_layout.setSpacing(10)
        self._gallery_title_label = QLabel(tr("CHART_GALLERY_TITLE"))
        self._gallery_title_label.setObjectName("gallery_title_label")
        self._gallery_summary_label = QLabel(tr("CHART_GALLERY_SUMMARY", 0))
        self._gallery_summary_label.setObjectName("gallery_summary_label")
        gallery_header_layout.addWidget(self._gallery_title_label)
        gallery_header_layout.addWidget(self._gallery_summary_label)
        gallery_header_layout.addStretch()
        layout.addWidget(gallery_header)



        # Figure library is the default Plots view. The large preview stays
        # hidden until a user clicks a figure card.

        self._plots_label = QLabel(tr("PLOTS_EMPTY"))

        self._plots_label.setAlignment(Qt.AlignCenter)

        self._plots_label.setStyleSheet(

            f"color: {C_TEXT_MUTED}; font-size: 13px; padding: 20px;"

        )

        layout.addWidget(self._plots_label)



        # Toolbar

        action_bar = QWidget()
        action_bar.setObjectName("plots_action_bar")
        toolbar = QHBoxLayout(action_bar)
        toolbar.setContentsMargins(0, 0, 0, 0)

        self._btn_legacy_recovery = QPushButton(tr("PLOTS_BTN_RECOVER_LEGACY"))

        self._btn_legacy_recovery.setObjectName("secondary_btn")

        self._btn_legacy_recovery.clicked.connect(self._open_legacy_recovery_view)

        toolbar.addWidget(self._btn_legacy_recovery)

        toolbar.addStretch()

        layout.addWidget(action_bar)

        self._figure_preview = FigureFilePreview(
            show_edit_button=True,
            show_close_button=True,
            show_view_button=True,
        )

        self._figure_preview.edit_requested.connect(self._open_selected_chart_editor)
        self._figure_preview.view_requested.connect(self._open_current_figure_viewer)
        self._figure_preview.close_requested.connect(self._close_figure_preview)

        self._figure_preview.setVisible(False)
        self._figure_preview.setMinimumHeight(460)

        layout.addWidget(self._figure_preview, 5)

        self._chart_gallery = ChartGallery()

        self._chart_gallery.figure_selected.connect(self._on_chart_selected)

        self._chart_gallery.summary_changed.connect(self._refresh_gallery_summary)

        self._chart_gallery.edit_requested.connect(self._open_selected_chart_editor)

        self._chart_gallery.setVisible(False)

        self._chart_gallery.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout.addWidget(self._chart_gallery, 4)

        self._apply_gallery_header_style()



        return w

    def _apply_gallery_header_style(self):
        """Apply theme-aware emphasis to the figure gallery page header."""
        if not hasattr(self, "_gallery_title_label"):
            return
        tokens = self._theme_engine.tokens
        self._gallery_title_label.setStyleSheet(
            f"color: {tokens.text_primary}; font-size: {tokens.font_size_xl}px; "
            "font-weight: 700; background: transparent;"
        )
        self._gallery_summary_label.setStyleSheet(
            f"color: {tokens.text_muted}; font-size: {tokens.font_size_sm}px; "
            "background: transparent;"
        )


    def _apply_theme(self):

        # Rebuild and apply the global QSS theme, then repolish the app.
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()

        if app:

            app.setStyleSheet(build_qss(self._theme_engine.tokens))

        self._theme_engine.switch(self._theme_engine.current)
        self._apply_gallery_header_style()

        for btn in getattr(self, "_nav_buttons", {}).values():

            btn_tech = btn.property("technique") or self._current_technique or "waxs"

            btn.setStyleSheet(self._nav_sub_style(btn_tech, btn.isChecked()))

        self._update_workspace_context()



    def _result_mask_summary_text(self, result):
        return build_result_mask_summary_text(
            result,
            current_technique=str(getattr(self, "_current_technique", "") or "").strip().lower(),
            language=get_language(),
        )


    def _responsibility_boundary_summary(self) -> str:

        if get_language() == "zh":
            return "Boundary | 边界 | core 负责证据，AI 只给有限建议，orchestrator 负责受控试验与回滚，用户负责最终判断"
        return "Boundary | core provides evidence, AI only suggests, orchestrator guards trials and rollback, user makes the final judgment"

    def log(self, msg):

        # UI-only log sink for status and export messages.
        # Per-run file logging is handled by worker log handlers.

        ts = datetime.now().strftime("%H:%M:%S")

        line = f"[{ts}] {msg}"

        self._log_panel.append(line)

        sb = self._log_panel.verticalScrollBar()

        sb.setValue(sb.maximum())


    def _read_warning_count(self):
        return read_warning_count(Path("polynexus.log"), warning_fn=lambda message: logger.warning(message, exc_info=True))


    def _append_analysis_warning_summary(self):

        previous = getattr(self, "_analysis_warning_count_before", None)
        if previous is None:
            return
        current = self._read_warning_count()
        warning_count = max(0, current - previous)
        self._analysis_warning_count_before = current
        if warning_count <= 0:
            return

        ts = datetime.now().strftime("%H:%M:%S")
        line = (
            f'[{ts}] <span style="color:#dc2626;">'
            f'! {tr("LOG_ANALYSIS_WARNINGS_SUMMARY", warning_count)}'
            f"</span>"
        )
        self._log_panel.append(line)
        sb = self._log_panel.verticalScrollBar()
        sb.setValue(sb.maximum())


    def _infer_sample_name(self) -> str:
        current_sample_name = str(getattr(self, "_current_sample_name", "") or "").strip()
        if current_sample_name and not _is_default_project_label(current_sample_name):
            return current_sample_name
        label = ""
        if hasattr(self, "_project_label"):
            label = self._project_label.text().strip()
        if label and not _is_default_project_label(label) and label != tr("WORKFLOW_NO_DATA"):
            return label
        if self._current_filepath:
            return Path(self._current_filepath).stem
        return ""



    def dragEnterEvent(self, event):

        if event.mimeData().hasUrls():

            self._set_drop_banner_visible(True)

            event.acceptProposedAction()


    def dragMoveEvent(self, event):

        if event.mimeData().hasUrls():

            event.acceptProposedAction()


    def dragLeaveEvent(self, event):

        self._set_drop_banner_visible(False)

        event.accept()



    def dropEvent(self, event):

        self._set_drop_banner_visible(False)

        urls = event.mimeData().urls()

        if not urls:

            return

        loaded_any = False
        for url in urls:
            path = url.toLocalFile()
            if not path:
                continue

            is_dir = os.path.isdir(path)
            if not is_dir and not os.path.isfile(path):
                continue

            self._handle_import_candidate(path, is_dir=is_dir, source="drop")
            self.log(tr("LOG_OPENED_PATH", path))
            loaded_any = True

        if not loaded_any:
            return


MainWindow._result_review_summary = build_result_review_summary_text_from_window
