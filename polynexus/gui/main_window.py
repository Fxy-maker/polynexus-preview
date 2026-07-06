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

    QFileDialog, QSplitter, QApplication, QGroupBox,

    QFrame, QSizePolicy, QButtonGroup, QProgressBar,

    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,

    QMessageBox, QScrollArea, QListWidget, QListWidgetItem,

    QCheckBox, QSpinBox, QDoubleSpinBox, QFormLayout, QLayout,

    QToolButton, QMenu, QGridLayout, QAbstractItemView,
    QDialog, QDialogButtonBox, QProgressDialog, QRadioButton,

)

from PySide6.QtCore import QObject, QRunnable, Qt, QThread, QThreadPool, Signal, QSettings

from PySide6.QtGui import (

    QAction, QColor, QFont, QDragEnterEvent, QDropEvent, QIcon, QKeySequence, QShortcut,

)



from .widgets.chart_viewer import ChartGallery, ChartViewer, FigureFilePreview

from .widgets.chart_editor import ChartEditor
from .widgets.joint_analysis_hub import JointAnalysisHub
from .widgets.sample_browser import SampleBrowser

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

from .widgets.settings_dialog import SettingsDialog
from .import_suggestions import ImportSuggestion, suggest_import

from ..core.engine import list_techniques, get_engine, logger, check_file_format
from ..core.joint.dataset import build_joint_hub_report

from .i18n import tr, set_language, get_language

from ..utils import (
    delete_config_preset,
    detect_polymer_type,
    list_config_presets,
    load_config_preset,
    load_defaults,
    save_config_preset,
)
from ..utils.logger import PolyNexusLogger
from ..data.sample_db import SampleDB
from llm.config import load_ai_settings


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


def _ir_conclusion_state_display(value: Any) -> str:
    if value is True:
        return tr("IR_CONCLUSION_READY")
    if value is False:
        return tr("IR_CONCLUSION_PENDING")
    return tr("AI_TUNING_EMPTY_VALUE")


def _build_ir_support_block_text(
    analysis_evidence: dict[str, Any] | None,
    *,
    display_text,
    format_score_value,
    ir_label_text,
    include_reference_summary: bool = False,
) -> str:
    feature = analysis_evidence.get("feature_evidence", {}) if isinstance(analysis_evidence, dict) else {}
    if not isinstance(feature, dict):
        feature = {}
    reference = feature.get("reference_evidence", {}) if isinstance(feature.get("reference_evidence"), dict) else {}
    assignment = feature.get("assignment_evidence", {}) if isinstance(feature.get("assignment_evidence"), dict) else {}
    structure = feature.get("structure_evidence", {}) if isinstance(feature.get("structure_evidence"), dict) else {}
    peak = feature.get("peak_evidence", {}) if isinstance(feature.get("peak_evidence"), dict) else {}
    baseline = feature.get("baseline_evidence", {}) if isinstance(feature.get("baseline_evidence"), dict) else {}

    sections: list[str] = []

    detected_bits: list[str] = []
    if isinstance(peak, dict) and peak:
        for key in ("peak_count", "assigned_peak_count", "unassigned_peak_count"):
            value = peak.get(key)
            if value is not None:
                detected_bits.append(f"{key}={display_text(value)}")
    if not detected_bits and isinstance(reference, dict):
        for key in ("band_count", "hit_count", "missing_count"):
            value = reference.get(key)
            if value is not None:
                detected_bits.append(f"{key}={display_text(value)}")
    if detected_bits:
        sections.append(tr("RESULTS_REVIEW_IR_DETECTED", ", ".join(detected_bits[:3])))

    if include_reference_summary and isinstance(reference, dict) and reference:
        sections.append(
            tr(
                "RESULTS_REVIEW_IR_REFERENCE",
                display_text(reference.get("band_count")),
                display_text(reference.get("hit_count")),
                display_text(reference.get("missing_count")),
            )
        )

    if isinstance(assignment, dict) and assignment.get("assignment_confidence") is not None:
        sections.append(tr("RESULTS_REVIEW_IR_ASSIGNMENT", format_score_value(assignment.get("assignment_confidence"))))

    support_bits: list[str] = []
    if isinstance(assignment, dict):
        for label, key in (
            ("key", "key_band_support_score"),
            ("peak", "peak_coverage_score"),
            ("baseline", "baseline_stability_score"),
            ("total", "ir_support_score"),
        ):
            value = assignment.get(key)
            if value is None and isinstance(structure, dict):
                value = structure.get(key)
            if value is not None:
                support_bits.append(f"{label}={format_score_value(value)}")
    if support_bits:
        sections.append(tr("RESULTS_REVIEW_IR_SUPPORT_DETAIL", " | ".join(support_bits[:4])))

    band_tracking = feature.get("band_tracking_evidence", {}) if isinstance(feature.get("band_tracking_evidence"), dict) else {}
    if isinstance(band_tracking, dict) and band_tracking:
        tracking_bits: list[str] = []
        for key in (
            "band_index_series_count",
            "band_index_transition_support_band_count",
            "band_index_transition_support_ratio",
            "band_index_transition_reproducible",
            "band_tracking_missing_key_band",
        ):
            value = band_tracking.get(key)
            if value is None:
                continue
            if isinstance(value, float):
                tracking_bits.append(f"{key}={format_score_value(value)}")
            else:
                tracking_bits.append(f"{key}={display_text(value)}")
        if tracking_bits:
            sections.append(tr("RESULTS_REVIEW_IR_BAND_TRACKING", " | ".join(tracking_bits[:5])))

    temp2d = feature.get("temperature_2d_evidence", {}) if isinstance(feature.get("temperature_2d_evidence"), dict) else {}
    if isinstance(temp2d, dict) and temp2d:
        trust_bits: list[str] = []
        for label, key in (
            ("sequence", "sequence_axis_score"),
            ("matrix", "matrix_quality_score"),
            ("cos", "cos_signal_score"),
            ("band", "band_tracking_score"),
        ):
            value = temp2d.get(key)
            if value is not None:
                trust_bits.append(f"{label}={format_score_value(value)}")
        if trust_bits:
            sections.append(tr("RESULTS_REVIEW_IR_SEQUENCE_TRUST", " | ".join(trust_bits[:4])))

    basis = str(structure.get("classification_basis", "") or "").strip() if isinstance(structure, dict) else ""
    if basis:
        sections.append(tr("RESULTS_REVIEW_IR_BASIS", ir_label_text(basis)))
    if isinstance(structure, dict) and structure.get("characteristic_band_support_ok") is not None:
        support_text = tr("IR_SUPPORT_COMPLETE") if bool(structure.get("characteristic_band_support_ok")) else tr("IR_SUPPORT_INCOMPLETE")
        sections.append(tr("RESULTS_REVIEW_IR_SUPPORT", support_text))
    if isinstance(structure, dict) and structure.get("paper_conclusion_ready") is not None:
        sections.append(
            tr(
                "RESULTS_REVIEW_IR_CONCLUSION_STATE",
                _ir_conclusion_state_display(structure.get("paper_conclusion_ready")),
            )
        )
    if isinstance(temp2d, dict) and temp2d:
        matrix_value = temp2d.get("matrix_quality_score")
        cos_value = temp2d.get("cos_signal_score")
        transition_value = temp2d.get("paper_conclusion_ready")
        matrix_bits = []
        if matrix_value is not None:
            matrix_bits.append(f"matrix={format_score_value(matrix_value)}")
        if cos_value is not None:
            matrix_bits.append(f"cos={format_score_value(cos_value)}")
        if matrix_bits:
            sections.append(tr("RESULTS_REVIEW_IR_MATRIX_TRUST", " | ".join(matrix_bits[:3])))
        if transition_value is not None:
            sections.append(
                tr(
                    "RESULTS_REVIEW_IR_TRANSITION_TRUST",
                    _ir_conclusion_state_display(transition_value),
                )
            )

    risk_bits: list[str] = []
    if isinstance(reference, dict) and reference.get("missing_count") is not None:
        risk_bits.append(f"missing={display_text(reference.get('missing_count'))}")
    if isinstance(baseline, dict):
        for key in ("baseline_method", "normalization_method"):
            value = baseline.get(key)
            if value:
                risk_bits.append(f"{key}={display_text(value)}")
    if risk_bits:
        sections.append(tr("RESULTS_REVIEW_IR_RISK_DETAIL", " | ".join(risk_bits[:3])))

    if not sections:
        return tr("AI_TUNING_EMPTY_VALUE")
    return " | ".join(sections)


def _dsc_conclusion_state_display(structure: dict[str, Any] | None) -> str:
    structure = structure if isinstance(structure, dict) else {}
    if structure.get("paper_conclusion_ready") is True:
        return tr("DSC_CONCLUSION_READY")
    if bool(structure.get("paper_conclusion_candidate")):
        return tr("DSC_CONCLUSION_CANDIDATE")
    if structure.get("paper_conclusion_ready") is False:
        return tr("DSC_CONCLUSION_PENDING")
    return tr("AI_TUNING_EMPTY_VALUE")


def _build_dsc_support_block_text(
    analysis_evidence: dict[str, Any] | None,
    *,
    display_text,
    format_score_value,
    include_measurement: bool = False,
) -> str:
    feature = analysis_evidence.get("feature_evidence", {}) if isinstance(analysis_evidence, dict) else {}
    if not isinstance(feature, dict):
        feature = {}
    thermal = feature.get("thermal_event_evidence", {}) if isinstance(feature.get("thermal_event_evidence"), dict) else {}
    event_support = feature.get("event_support_evidence", {}) if isinstance(feature.get("event_support_evidence"), dict) else {}
    baseline = feature.get("baseline_evidence", {}) if isinstance(feature.get("baseline_evidence"), dict) else {}
    structure = feature.get("structure_evidence", {}) if isinstance(feature.get("structure_evidence"), dict) else {}

    sections: list[str] = []

    if include_measurement:
        measured_bits: list[str] = []
        for key in ("Tg_C", "Tm_peak_C", "Tcc_peak_C", "DHm_Jg", "DHc_Jg", "DHcc_Jg", "Xc_pct"):
            value = thermal.get(key)
            if value is None:
                value = feature.get(key)
            text = display_text(value)
            if text != tr("AI_TUNING_EMPTY_VALUE"):
                measured_bits.append(f"{key}={text}")
        if measured_bits:
            sections.append(tr("RESULTS_REVIEW_DSC_MEASURED", ", ".join(measured_bits[:5])))

    support_bits: list[str] = []
    for label, key in (
        ("event", "event_support_score"),
        ("baseline", "baseline_stability_score"),
        ("thermo", "thermodynamic_consistency_score"),
        ("structure", "structure_support_score"),
        ("fraction", "supported_event_fraction"),
        ("scan", "scan_r_squared_median"),
    ):
        value = event_support.get(key)
        if value is None:
            value = feature.get(key)
        if value is None:
            continue
        if key == "supported_event_fraction":
            support_bits.append(f"{label}={display_text(value)}")
        else:
            support_bits.append(f"{label}={format_score_value(value)}")
    if support_bits:
        sections.append(tr("RESULTS_REVIEW_DSC_SUPPORT", " | ".join(support_bits[:5])))

    conclusion_state = _dsc_conclusion_state_display(structure)
    if conclusion_state != tr("AI_TUNING_EMPTY_VALUE"):
        sections.append(tr("RESULTS_REVIEW_DSC_CONCLUSION_STATE", conclusion_state))

    context_bits: list[str] = []
    if structure.get("paper_conclusion_candidate") is not None:
        context_bits.append(f"paper_candidate={display_text(structure.get('paper_conclusion_candidate'))}")
    if structure.get("paper_conclusion_ready") is not None:
        context_bits.append(f"paper_ready={display_text(structure.get('paper_conclusion_ready'))}")
    for label, source, key in (
        ("scan", thermal, "scan_mode"),
        ("exo", thermal, "exo_up"),
        ("baseline", baseline, "baseline_corr"),
        ("residual", baseline, "residual_type"),
    ):
        value = source.get(key) if isinstance(source, dict) else None
        if value is not None:
            context_bits.append(f"{label}={display_text(value)}")
    if context_bits:
        sections.append(tr("RESULTS_REVIEW_DSC_RISK_DETAIL", " | ".join(context_bits[:4])))

    if not sections:
        return tr("AI_TUNING_EMPTY_VALUE")
    return " | ".join(sections[:4])


def _build_ir_temperature_2d_user_summary(analysis_evidence: dict[str, Any] | None) -> list[str]:
    feature = analysis_evidence.get("feature_evidence", {}) if isinstance(analysis_evidence, dict) else {}
    if not isinstance(feature, dict):
        return []
    temp2d = feature.get("temperature_2d_evidence", {}) if isinstance(feature.get("temperature_2d_evidence"), dict) else {}
    sequence = feature.get("sequence_evidence", {}) if isinstance(feature.get("sequence_evidence"), dict) else {}
    transform = feature.get("transform_evidence", {}) if isinstance(feature.get("transform_evidence"), dict) else {}
    single_frame = feature.get("single_frame_evidence", {}) if isinstance(feature.get("single_frame_evidence"), dict) else {}
    if not isinstance(temp2d, dict) or not temp2d:
        return []

    lines: list[str] = []
    sequence_ready = bool(feature.get("sequence_axis_ready", temp2d.get("sequence_axis_score", 0.0) >= 0.75))
    if sequence_ready:
        lines.append(tr("RESULTS_REVIEW_IR_SEQUENCE_STATUS", tr("IR_SEQUENCE_RESOLVED")))
    else:
        lines.append(tr("RESULTS_REVIEW_IR_SEQUENCE_STATUS", tr("IR_SEQUENCE_UNRESOLVED")))

    paper_ready = bool(temp2d.get("paper_conclusion_ready"))
    interpretation_ready = bool(temp2d.get("interpretation_ready"))
    if paper_ready:
        lines.append(tr("RESULTS_REVIEW_IR_FIGURE_STATUS", tr("IR_FIGURE_PAPER_READY")))
    elif interpretation_ready:
        lines.append(tr("RESULTS_REVIEW_IR_FIGURE_STATUS", tr("IR_FIGURE_USABLE_PENDING")))
    else:
        lines.append(tr("RESULTS_REVIEW_IR_FIGURE_STATUS", tr("IR_FIGURE_DIAGNOSTIC_ONLY")))

    if interpretation_ready and bool(transform.get("noda_rule_interpretation_ready")):
        lines.append(tr("RESULTS_REVIEW_IR_INTERPRETATION_STATUS", tr("IR_INTERPRETATION_READY")))
    else:
        lines.append(tr("RESULTS_REVIEW_IR_INTERPRETATION_STATUS", tr("IR_INTERPRETATION_TENTATIVE")))

    if isinstance(single_frame, dict) and single_frame:
        low_ratio = single_frame.get("low_confidence_frame_ratio")
        assign_mean = single_frame.get("frame_assignment_confidence_mean")
        key_band_mean = single_frame.get("frame_key_band_support_mean")
        if low_ratio is not None or assign_mean is not None or key_band_mean is not None:
            try:
                low_text = f"{float(low_ratio):.2f}" if low_ratio is not None else tr("AI_TUNING_EMPTY_VALUE")
            except Exception:
                low_text = tr("AI_TUNING_EMPTY_VALUE")
            try:
                assign_text = f"{float(assign_mean):.2f}" if assign_mean is not None else tr("AI_TUNING_EMPTY_VALUE")
            except Exception:
                assign_text = tr("AI_TUNING_EMPTY_VALUE")
            try:
                key_text = f"{float(key_band_mean):.2f}" if key_band_mean is not None else tr("AI_TUNING_EMPTY_VALUE")
            except Exception:
                key_text = tr("AI_TUNING_EMPTY_VALUE")
            lines.append(
                tr(
                    "RESULTS_REVIEW_IR_FRAME_STATUS",
                    tr("IR_FRAME_STATUS_TEMPLATE", low_text, assign_text, key_text),
                )
            )
    if isinstance(sequence, dict):
        stage_counts = sequence.get("stage_counts")
        if isinstance(stage_counts, dict) and stage_counts:
            stage_bits = ", ".join(f"{key}={value}" for key, value in list(stage_counts.items())[:3])
            lines.append(tr("RESULTS_REVIEW_IR_SEQUENCE_TRUST", stage_bits))
    return [line for line in lines if str(line).strip()]


def _lang_text(mapping, fallback=""):
    lang = get_language()
    return mapping.get(lang) or mapping.get("en") or fallback


def _is_default_project_label(text: str) -> bool:
    value = str(text or "").strip()
    if not value:
        return True
    return value in {"No project", "\u65e0\u9879\u76ee"}


def _data_file_dialog_filter() -> str:
    patterns = "*.edf *.csv *.txt *.dat *.xlsx *.xls *.001 *.raw *.spa *.jdf *.bin fid"
    return f"{tr('FILE_FILTER_SUPPORTED')} ({patterns});;{tr('FILE_FILTER_ALL')} (*)"


def _import_mode_text(mode: str) -> str:
    value = str(mode or "").strip().lower()
    mapping = {
        "single": tr("IMPORT_MODE_SINGLE"),
        "sequence": tr("IMPORT_MODE_SEQUENCE"),
        "directory": tr("IMPORT_MODE_DIRECTORY"),
    }
    return mapping.get(value, value or "-")


def _format_import_suggestion_reason(reason: str) -> str:
    value = str(reason or "").strip()
    if not value:
        return tr("IMPORT_SUGGESTION_AUTO")
    if value.startswith("extension:"):
        suffix = value.split(":", 1)[1].strip() or "-"
        return tr("IMPORT_SUGGESTION_REASON_EXTENSION", suffix)
    if value.startswith("filename:"):
        name = value.split(":", 1)[1].strip() or "-"
        return tr("IMPORT_SUGGESTION_REASON_FILENAME", name)
    if value.startswith("registry:"):
        submodule_id = value.split(":", 1)[1].strip()
        label = SIDEBAR_MODULE_TEXT.get(submodule_id)
        return tr(
            "IMPORT_SUGGESTION_REASON_REGISTRY",
            _lang_text(label, submodule_id) if isinstance(label, dict) else (submodule_id or "-"),
        )
    if value == "directory:nmr":
        return tr("IMPORT_SUGGESTION_REASON_DIRECTORY_NMR")
    if value == "directory:ir_spectra":
        return tr("IMPORT_SUGGESTION_REASON_DIRECTORY_IR")
    if value.startswith("directory:."):
        suffix = value.split(":", 1)[1].strip() or "-"
        return tr("IMPORT_SUGGESTION_REASON_DIRECTORY_EXTENSION", suffix)
    if value == "pattern:saxs_strain":
        return tr("IMPORT_SUGGESTION_REASON_PATTERN_SAXS_STRAIN")
    if value == "manual":
        return tr("IMPORT_SUGGESTION_REASON_MANUAL")
    return value





class AnalysisWorker(QThread):

    """Background thread for a single-technique analysis run.



    v1.1: Integrated with PolyNexusLogger for structured, per-run file

    logging + live Qt signal output.

    """

    log_msg = Signal(str)

    progress = Signal(int, int)

    finished = Signal(object)

    error_msg = Signal(str)



    def __init__(self, technique, filepath, output_dir, config=None,
                 submodule_id=None, engine=None):

        super().__init__()

        self.technique = technique

        self.filepath = filepath

        self.output_dir = output_dir

        self.config = config

        self.submodule_id = submodule_id

        self.engine = engine

        self.skip_to = None  # for incremental pipeline



    def run(self):

        logger = PolyNexusLogger.get()

        logger.attach_qt_signal(self.log_msg)



        try:

            logger.info(f"AnalysisWorker: technique={self.technique}, "

                        f"file={os.path.basename(self.filepath)}")



            engine = self.engine or get_engine(
                self.technique, config=self.config,
                submodule_id=getattr(self, 'submodule_id', None))

            if engine is None:

                msg = tr("ANALYSIS_UNKNOWN_TECHNIQUE", self.technique)

                logger.error(msg)

                self.error_msg.emit(msg)

                return

            self.engine = engine



            # engine.run_pipeline() handles its own setup_run/teardown_run

            result = engine.run_pipeline(self.filepath, self.output_dir, skip_to=self.skip_to)

            self.finished.emit(result)



        except Exception as e:

            msg = tr("ANALYSIS_WORKER_ERROR", e, traceback.format_exc())

            logger.error(msg)

            self.error_msg.emit(msg)
            logger.warning("Single-file analysis worker failed.", exc_info=True)





class BatchWorker(QThread):

    """Background thread for batch (multi-file) analysis.



    v1.1: Integrated with PolyNexusLogger.  Each file's run gets its

    own log context so logs are written to the same per-run file.

    """

    log_msg = Signal(str)

    progress = Signal(int, int)

    file_done = Signal(str, dict)

    batch_finished = Signal(list)

    error_msg = Signal(str)



    def __init__(self, technique, file_list, output_dir, config=None,
                 submodule_id=None):

        super().__init__()

        self.technique = technique

        self.file_list = file_list

        self.output_dir = output_dir

        self.config = config

        self.submodule_id = submodule_id

        self.skip_to = None  # for incremental pipeline



    def run(self):

        logger = PolyNexusLogger.get()

        logger.attach_qt_signal(self.log_msg)

        all_results = []

        total = len(self.file_list)



        logger.info(f"BatchWorker: technique={self.technique}, "

                    f"files={total}, output={self.output_dir}")



        for i, fp in enumerate(self.file_list):

            self.progress.emit(i + 1, total)

            fname = os.path.basename(fp)

            try:

                engine = get_engine(self.technique, config=self.config, submodule_id=self.submodule_id)

                # Create per-file subdirectory to avoid overwrites

                file_out = os.path.join(self.output_dir, os.path.splitext(fname)[0])

                result = engine.run_pipeline(fp, file_out)

                params = engine.get_parameters()

                self.file_done.emit(fname, params)

                logger.info(f"[{i+1}/{total}] {fname} - OK")

                all_results.append({'file': fname, 'params': params})

            except Exception as e:

                logger.error(f"[{i+1}/{total}] {fname} - FAILED: {e}")
                logger.warning("Batch analysis worker failed for %s.", fname, exc_info=True)

        self.batch_finished.emit(all_results)






class JointHubWorker(QThread):
    """Background thread for Joint Analysis Hub report generation.

    Offloads build_joint_hub_report() to a worker thread so the main
    event loop stays responsive and progress-bar animations can run.
    """

    finished = Signal(object)
    error_msg = Signal(str)

    def __init__(self, rows, output_dir):
        super().__init__()
        self.rows = rows
        self.output_dir = output_dir

    def run(self):
        try:
            report = build_joint_hub_report(self.rows)
            self.finished.emit(report)
        except Exception as exc:
            self.error_msg.emit(tr("JOINT_OVERVIEW_FAILED", exc))
            logger.warning("Joint analysis worker failed.", exc_info=True)


class AITuneSignals(QObject):
    progress_msg = Signal(str)
    finished = Signal(object)
    error_msg = Signal(str)


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

        try:
            joint_context = parent._joint_ai_context() if hasattr(parent, "_joint_ai_context") else {}
        except Exception:
            joint_context = {}
        if isinstance(joint_context, dict) and joint_context:
            issue_count = 0
            try:
                issue_count = int(float(joint_context.get("issue_count") or 0))
            except Exception:
                issue_count = 0
            joint_summary = str(joint_context.get("summary") or "").lower()
            issue_families = joint_context.get("issue_families") if isinstance(joint_context.get("issue_families"), list) else []
            families = {str(item).strip().lower() for item in issue_families if str(item).strip()}
            if issue_count > 0 or families or any(token in joint_summary for token in ("inconsistency", "gap", "unstable", "conflict")):
                return "joint", tr("AI_TUNING_GOAL_REASON_JOINT")

        tuning_context = getattr(parent, "_last_ai_tuning_context", {})
        if isinstance(tuning_context, dict) and tuning_context:
            risk_text = " ".join(
                str(tuning_context.get(key) or "")
                for key in ("remaining_risks", "stop_reason", "summary", "benchmark_text")
            ).lower()
            validation_text = ""
            if hasattr(parent, "_results_summary_risk_label"):
                validation_text = str(parent._results_summary_risk_label.text() or "").lower()
            if any(token in risk_text for token in ("low-q", "beamstop", "constraint", "rollback", "warn", "risk")) or "warn" in validation_text or "risk" in validation_text:
                return "risk", tr("AI_TUNING_GOAL_REASON_RISK")
            benchmark_text = str(tuning_context.get("benchmark_text") or "").lower()
            if any(token in benchmark_text for token in ("quality guard", "small delta", "stable", "accepted")):
                return "stability", tr("AI_TUNING_GOAL_REASON_STABILITY")

        return goal, reason

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


class AITuneWorker(QRunnable):
    def __init__(
        self,
        technique,
        filepath,
        polymer,
        rounds=5,
        submodule_id=None,
        workspace_context=None,
        ai_settings=None,
    ):
        super().__init__()
        self.signals = AITuneSignals()
        self.technique = technique
        self.filepath = filepath
        self.polymer = polymer
        self.rounds = rounds
        self.submodule_id = submodule_id
        self.workspace_context = workspace_context or {}
        self.ai_settings = dict(ai_settings or {})
        self._cancel_event = threading.Event()

    def cancel(self):
        self._cancel_event.set()

    def run(self):
        try:
            from polynexus.orchestrator import ParameterOrchestrator

            def progress(event):
                if self._cancel_event.is_set():
                    return
                score = event.get("after_r_squared", event.get("before_r_squared", 0.0))
                try:
                    score_text = f"{float(score):.3f}"
                except Exception:
                    score_text = str(score)
                    logger.warning("Failed to format AI tuning score for progress update.", exc_info=True)
                self.signals.progress_msg.emit(
                    tr("AI_TUNING_PROGRESS_ROUND", event.get("round_num"), score_text)
                )

            report = ParameterOrchestrator(
                technique=self.technique,
                data_file=self.filepath,
                polymer_name=self.polymer,
                max_rounds=self.rounds,
                progress_callback=progress,
                submodule_override=self.submodule_id,
                workspace_context=self.workspace_context,
                llm_settings=self.ai_settings,
            ).run()
            if not self._cancel_event.is_set():
                self.signals.finished.emit(report)
        except Exception as exc:
            if not self._cancel_event.is_set():
                self.signals.error_msg.emit(
                    tr("AI_TUNING_FAILED", exc, traceback.format_exc())
                )
            logger.warning("AI tuning worker failed.", exc_info=True)


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
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText(tr("AI_TUNING_APPLY"))
        buttons.button(QDialogButtonBox.Cancel).setText(tr("COMMON_CANCEL"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
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
        rounds = self.report.get("rounds", 0)
        best_r2 = self.report.get("best_r_squared", "")
        improvement = self.report.get("improvement") if isinstance(self.report.get("improvement"), dict) else {}
        delta = improvement.get("r_squared_abs", "")
        reason = str(self.report.get("convergence_reason", "") or "").strip()
        if reason:
            return tr("AI_TUNING_REPORT_SUMMARY_WITH_REASON", rounds, best_r2, delta, reason)
        return tr("AI_TUNING_REPORT_SUMMARY", rounds, best_r2, delta)

    def _report_decision_text(self):
        history = self.report.get("history") or []
        accepted = 0
        rolled_back = 0
        rollback_reasons = []
        if isinstance(history, list):
            for item in history:
                if not isinstance(item, dict):
                    continue
                round_num = int(item.get("round_num", item.get("round_idx", 0)) or 0)
                if round_num <= 0:
                    continue
                if bool(item.get("accepted", True)):
                    accepted += 1
                else:
                    rolled_back += 1
                    advice = item.get("llm_advice") if isinstance(item.get("llm_advice"), dict) else {}
                    reason = str(advice.get("rollback_reason", "") or "").strip()
                    if reason:
                        rollback_reasons.append(reason)

        if rolled_back and rollback_reasons:
            return tr(
                "AI_TUNING_REPORT_DECISION_WITH_ROLLBACK",
                accepted,
                rolled_back,
                rollback_reasons[0],
            )
        return tr("AI_TUNING_REPORT_DECISION", accepted, rolled_back)

    def _report_benchmark_text(self):
        benchmark = self.report.get("benchmark_summary")
        if not isinstance(benchmark, dict) or not benchmark:
            return ""

        objective_delta = self._format_benchmark_delta(benchmark.get("average_objective_delta"))
        acceptance_rate = self._format_benchmark_rate(benchmark.get("acceptance_rate"))
        rollback_rate = self._format_benchmark_rate(benchmark.get("rejection_rate"))
        constraint_hit_rate = self._format_benchmark_rate(benchmark.get("constraint_hit_rate"))
        symptom_fix_rate = self._format_benchmark_rate(benchmark.get("symptom_fix_rate"))
        return tr(
            "AI_TUNING_REPORT_BENCHMARK",
            objective_delta,
            acceptance_rate,
            rollback_rate,
            constraint_hit_rate,
            symptom_fix_rate,
        )

    def best_config(self):
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
        return _build_ir_support_block_text(
            analysis_evidence,
            display_text=self._display_text,
            format_score_value=self._format_score_value,
            ir_label_text=self._ir_label_text,
            include_reference_summary=False,
        )

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
        if not isinstance(analysis_evidence, dict) or not analysis_evidence:
            return tr("AI_TUNING_EMPTY_VALUE")

        sections = []
        technique = self._report_technique()
        if technique == "waxs":
            peak = analysis_evidence.get("peak_evidence", {}) if isinstance(analysis_evidence.get("peak_evidence"), dict) else {}
            background = analysis_evidence.get("background_evidence", {}) if isinstance(analysis_evidence.get("background_evidence"), dict) else {}
            phase = analysis_evidence.get("phase_evidence", {}) if isinstance(analysis_evidence.get("phase_evidence"), dict) else {}
            trend = self._waxs_temperature_trend_evidence(analysis_evidence)
            parts = []

            peak_bits = []
            for label, value in (("n", peak.get("peak_count")), ("spread", peak.get("peak_gap_spread")), ("width", peak.get("peak_width_spread"))):
                text = self._display_text(value)
                if text != tr("AI_TUNING_EMPTY_VALUE"):
                    peak_bits.append(f"{label}={text}")
            if peak_bits:
                parts.append("peak=" + ", ".join(peak_bits))

            background_bits = []
            for label, value in (("offset", background.get("two_theta_offset")), ("method", background.get("background_method")), ("halo", background.get("amorphous_subtraction"))):
                text = self._display_text(value)
                if text != tr("AI_TUNING_EMPTY_VALUE"):
                    background_bits.append(f"{label}={text}")
            if background_bits:
                parts.append("background=" + ", ".join(background_bits))

            phase_bits = []
            for label, value in (("Xc", phase.get("Xc_pct")), ("method", phase.get("crystallinity_method")), ("D", phase.get("D_Scherrer_nm"))):
                text = self._display_text(value)
                if text != tr("AI_TUNING_EMPTY_VALUE"):
                    phase_bits.append(f"{label}={text}")
            if phase_bits:
                parts.append("phase=" + ", ".join(phase_bits))

            trend_bits = []
            for label, value in (
                ("score", trend.get("D_trend_support_score")),
                ("mode", trend.get("D_trend_monotonicity")),
                ("support", trend.get("D_support_peak_count")),
            ):
                text = self._display_text(value)
                if text != tr("AI_TUNING_EMPTY_VALUE"):
                    trend_bits.append(f"{label}={text}")
            if trend.get("instrument_broadening_present") is not None:
                trend_bits.append(f"instrument_broadening={bool(trend.get('instrument_broadening_present'))}")
            if trend_bits:
                parts.append("trend=" + ", ".join(trend_bits))

            if parts:
                sections.append("WAXS | " + " ; ".join(parts))

            support_bits = []
            for label, value in (
                ("peak", analysis_evidence.get("peak_support_score")),
                ("background", analysis_evidence.get("background_stability_score")),
                ("phase", analysis_evidence.get("phase_support_score")),
                ("size", analysis_evidence.get("size_support_score")),
                ("D_trend", trend.get("D_trend_support_score") if isinstance(trend, dict) else None),
                ("waxs_support_score", analysis_evidence.get("waxs_support_score")),
            ):
                text = self._format_score_value(value)
                if text != tr("AI_TUNING_EMPTY_VALUE"):
                    support_bits.append(f"{label}={text}")
            if support_bits:
                sections.append("Support | " + " | ".join(support_bits))
        elif technique == "saxs":
            strain_text = self._saxs_strain_summary_text(None, analysis_evidence)
            if strain_text:
                sections.append("SAXS | " + strain_text)
        elif technique == "ir":
            parts = []
            feature = analysis_evidence.get("feature_evidence", {}) if isinstance(analysis_evidence.get("feature_evidence"), dict) else {}
            reference = feature.get("reference_evidence", {}) if isinstance(feature, dict) else {}
            assignment = feature.get("assignment_evidence", {}) if isinstance(feature, dict) else {}
            structure = feature.get("structure_evidence", {}) if isinstance(feature, dict) else {}

            if isinstance(reference, dict) and reference:
                parts.append(
                    tr(
                        "RESULTS_REVIEW_IR_REFERENCE",
                        self._display_text(reference.get("band_count")),
                        self._display_text(reference.get("hit_count")),
                        self._display_text(reference.get("missing_count")),
                    )
                )

            if isinstance(assignment, dict) and assignment:
                confidence = self._format_score_value(assignment.get("assignment_confidence"))
                if confidence != tr("AI_TUNING_EMPTY_VALUE"):
                    parts.append(tr("RESULTS_REVIEW_IR_ASSIGNMENT", confidence))

            if isinstance(structure, dict):
                basis = str(structure.get("classification_basis", "") or "").strip()
                if basis:
                    parts.append(tr("RESULTS_REVIEW_IR_BASIS", self._ir_label_text(basis)))
                if structure.get("characteristic_band_support_ok") is not None:
                    support_text = tr("IR_SUPPORT_COMPLETE") if bool(structure.get("characteristic_band_support_ok")) else tr("IR_SUPPORT_INCOMPLETE")
                    parts.append(tr("RESULTS_REVIEW_IR_SUPPORT", support_text))
                if structure.get("paper_conclusion_ready") is not None:
                    parts.append(
                        tr(
                            "RESULTS_REVIEW_IR_CONCLUSION_STATE",
                            self._ir_conclusion_state_text(structure.get("paper_conclusion_ready")),
                        )
                    )

            if parts:
                sections.append("IR | " + " ; ".join(parts))
        elif technique == "dsc":
            dsc_text = _build_dsc_support_block_text(
                analysis_evidence,
                display_text=self._display_text,
                format_score_value=self._format_score_value,
                include_measurement=True,
            )
            if dsc_text != tr("AI_TUNING_EMPTY_VALUE"):
                sections.append("DSC | " + dsc_text)
        else:
            for label, key in (
                ("fit", "fit_evidence"),
                ("physical", "physical_evidence"),
                ("residual", "residual_evidence"),
                ("stability", "stability_evidence"),
            ):
                block = analysis_evidence.get(key, {})
                if isinstance(block, dict) and block:
                    preview_items = []
                    for item_key in list(block.keys())[:3]:
                        value = block.get(item_key)
                        text = self._display_text(value)
                        if text != tr("AI_TUNING_EMPTY_VALUE"):
                            preview_items.append(f"{item_key}={text}")
                    if preview_items:
                        sections.append(f"{label}: " + " | ".join(preview_items))

        constraint_summary = analysis_evidence.get("constraint_summary", {})
        if isinstance(constraint_summary, dict) and constraint_summary:
            sections.append(
                "constraints="
                + self._constraint_summary_text(analysis_evidence)
            )
        if not sections:
            return tr("AI_TUNING_EMPTY_VALUE")
        return " | ".join(sections[:4])

    def _round_core_summary_text(self, item):
        if not isinstance(item, dict):
            return tr("AI_TUNING_EMPTY_VALUE")
        output = item.get("output_parameters") if isinstance(item.get("output_parameters"), dict) else {}
        if not isinstance(output, dict):
            output = {}
        technique = self._report_technique()
        if technique == "waxs":
            keys = ("n_peaks", "Xc_pct", "D_Scherrer_nm")
        elif technique == "ir":
            keys = ("n_peaks", "polymer_score", "assignment_confidence", "Xc_pct")
        elif technique == "dsc":
            keys = ("Tg_C", "Tm_peak_C", "Tcc_peak_C", "DHm_Jg", "Xc_pct", "quality_score")
        else:
            keys = ("r_squared", "quality_score", "L_nm", "Xc_pct", "Tm_peak_C", "Tc_peak_C")
        parts = []
        for key in keys:
            text = self._display_text(output.get(key))
            if text != tr("AI_TUNING_EMPTY_VALUE"):
                parts.append(f"{key}={text}")
        if not parts:
            return tr("AI_TUNING_EMPTY_VALUE")
        return " | ".join(parts[:4])

    def _round_support_summary_text(self, item):
        if not isinstance(item, dict):
            return tr("AI_TUNING_EMPTY_VALUE")
        evidence = self._round_history_analysis_evidence(item)
        if not isinstance(evidence, dict) or not evidence:
            return tr("AI_TUNING_EMPTY_VALUE")
        technique = self._report_technique()
        if technique == "waxs":
            parts = []
            for label, key in (
                ("peak", "peak_support_score"),
                ("background", "background_stability_score"),
                ("phase", "phase_support_score"),
                ("size", "size_support_score"),
                ("waxs_support_score", "waxs_support_score"),
            ):
                text = self._format_score_value(evidence.get(key))
                if text != tr("AI_TUNING_EMPTY_VALUE"):
                    parts.append(f"{label}={text}")
            if parts:
                return " | ".join(parts)
            return tr("AI_TUNING_EMPTY_VALUE")
        if technique == "ir":
            parts = []
            feature = evidence.get("feature_evidence", {}) if isinstance(evidence.get("feature_evidence"), dict) else {}
            reference = feature.get("reference_evidence", {}) if isinstance(feature, dict) else {}
            assignment = feature.get("assignment_evidence", {}) if isinstance(feature, dict) else {}
            structure = feature.get("structure_evidence", {}) if isinstance(feature, dict) else {}

            if isinstance(reference, dict) and reference:
                parts.append(
                    tr(
                        "RESULTS_REVIEW_IR_REFERENCE",
                        self._display_text(reference.get("band_count")),
                        self._display_text(reference.get("hit_count")),
                        self._display_text(reference.get("missing_count")),
                    )
                )

            if isinstance(assignment, dict) and assignment:
                confidence = self._format_score_value(assignment.get("assignment_confidence"))
                if confidence != tr("AI_TUNING_EMPTY_VALUE"):
                    parts.append(tr("RESULTS_REVIEW_IR_ASSIGNMENT", confidence))

            if isinstance(structure, dict):
                basis = str(structure.get("classification_basis", "") or "").strip()
                if basis:
                    parts.append(tr("RESULTS_REVIEW_IR_BASIS", self._ir_label_text(basis)))
                if structure.get("characteristic_band_support_ok") is not None:
                    support_text = tr("IR_SUPPORT_COMPLETE") if bool(structure.get("characteristic_band_support_ok")) else tr("IR_SUPPORT_INCOMPLETE")
                    parts.append(tr("RESULTS_REVIEW_IR_SUPPORT", support_text))
                if structure.get("paper_conclusion_ready") is not None:
                    parts.append(
                        tr(
                            "RESULTS_REVIEW_IR_CONCLUSION_STATE",
                            self._ir_conclusion_state_text(structure.get("paper_conclusion_ready")),
                        )
                    )

            if parts:
                return " | ".join(parts)
            return tr("AI_TUNING_EMPTY_VALUE")
        if technique == "dsc":
            support_text = _build_dsc_support_block_text(
                evidence,
                display_text=self._display_text,
                format_score_value=self._format_score_value,
                include_measurement=False,
            )
            return support_text if support_text != tr("AI_TUNING_EMPTY_VALUE") else tr("AI_TUNING_EMPTY_VALUE")
        parts = []
        stability = self._stability_summary_text(evidence)
        if stability != tr("AI_TUNING_EMPTY_VALUE"):
            parts.append(stability)
        constraint = self._constraint_summary_text(evidence)
        if constraint != tr("AI_TUNING_EMPTY_VALUE"):
            parts.append(constraint)
        if not parts:
            return tr("AI_TUNING_EMPTY_VALUE")
        return " | ".join(parts[:2])

    def _display_text(self, value):
        if isinstance(value, (dict, list)):
            text = json.dumps(value, ensure_ascii=False)
        elif value is None:
            text = ""
        else:
            text = str(value)
        text = text.strip()
        return text or tr("AI_TUNING_EMPTY_VALUE")

    def _format_score_value(self, value, signed=False):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return tr("AI_TUNING_EMPTY_VALUE")
        sign = "+" if signed and number > 0 else ""
        return f"{sign}{number:.3f}"

    def _format_change_summary(self, changes):
        if not isinstance(changes, dict) or not changes:
            return tr("AI_TUNING_EMPTY_VALUE")
        parts = []
        items = list(changes.items())
        for key, value in items[:3]:
            parts.append(f"{key} -> {self._display_text(value)}")
        remaining = len(items) - len(parts)
        if remaining > 0:
            parts.append(tr("AI_TUNING_CHANGESET_MORE", remaining))
        return "; ".join(parts)


    def _remaining_risks_text(self):
        risks = []
        for item in self._candidate_history():
            if bool(item.get("accepted", True)):
                continue
            detail = str(item.get("rollback_detail", "") or "").strip()
            if detail and detail not in risks:
                risks.append(detail)
            advice = item.get("llm_advice") if isinstance(item.get("llm_advice"), dict) else {}
            rollback_reason = str(advice.get("rollback_reason", "") or "").strip()
            if rollback_reason and rollback_reason not in risks:
                risks.append(rollback_reason)
        return "; ".join(risks[:3]) if risks else tr("AI_TUNING_EMPTY_VALUE")

    def _stability_summary_text(self, analysis_evidence):
        evidence = analysis_evidence.get("stability_evidence", {}) if isinstance(analysis_evidence, dict) else {}
        if not isinstance(evidence, dict) or not evidence:
            return tr("AI_TUNING_EMPTY_VALUE")
        flags = evidence.get("stability_flags", [])
        if isinstance(flags, list):
            flag_values = [str(item).strip() for item in flags if str(item).strip()]
        else:
            flag_values = [str(flags).strip()] if str(flags).strip() else []
        return tr(
            "AI_TUNING_STABILITY_SUMMARY",
            self._format_score_value(evidence.get("stability_score")),
            self._format_score_value(evidence.get("parameter_stability_score")),
            self._format_score_value(evidence.get("method_agreement_score")),
            self._format_score_value(evidence.get("batch_continuity_score")),
            ", ".join(flag_values[:4]) if flag_values else tr("AI_TUNING_EMPTY_VALUE"),
        )

    def _constraint_summary_text(self, analysis_evidence):
        summary = analysis_evidence.get("constraint_summary", {}) if isinstance(analysis_evidence, dict) else {}
        if not isinstance(summary, dict) or not summary:
            return tr("AI_TUNING_EMPTY_VALUE")
        counts = summary.get("triggered_counts", {}) if isinstance(summary.get("triggered_counts"), dict) else {}
        base = tr(
            "AI_TUNING_CONSTRAINT_SUMMARY",
            self._display_text(summary.get("status")),
            int(counts.get("hard_fail", 0) or 0),
            int(counts.get("soft_warn", 0) or 0),
            int(counts.get("evidence_only", 0) or 0),
        )
        triggered_names = summary.get("triggered_names", {}) if isinstance(summary.get("triggered_names"), dict) else {}
        names = []
        for key in ("hard_fail", "soft_warn", "evidence_only"):
            value = triggered_names.get(key, [])
            if isinstance(value, list):
                for item in value:
                    text = str(item or "").strip()
                    if text and text not in names:
                        names.append(text)
        if names:
            return f"{base}; {tr('AI_TUNING_CONSTRAINT_NAMES', ', '.join(names[:4]))}"
        return base

    def _result_source_summary_text(self, record: dict[str, Any] | None = None) -> str:
        record = record if isinstance(record, dict) else self._current_results_record()
        if not isinstance(record, dict) or not record:
            return tr("AI_TUNING_EMPTY_VALUE")

        summary = record.get("results_summary") if isinstance(record.get("results_summary"), dict) else {}
        if not isinstance(summary, dict):
            summary = {}

        result_payload = summary.get("result") if isinstance(summary.get("result"), dict) else {}
        if not isinstance(result_payload, dict):
            result_payload = {}

        evidence = result_payload.get("analysis_evidence") if isinstance(result_payload.get("analysis_evidence"), dict) else {}
        if not isinstance(evidence, dict) or not evidence:
            if str(record.get("id") or "").strip() == "current":
                evidence = self._current_analysis_evidence()
        if not isinstance(evidence, dict):
            evidence = {}

        current_metrics = self._history_result_metrics(record)
        origin = self._history_result_origin_label(record) or self._current_result_origin_label()
        bits = [part for part in [origin] if part]
        if self._current_technique == "waxs":
            waxs_parts = []
            for key in ("n_peaks", "Xc_pct", "D_Scherrer_nm"):
                value = current_metrics.get(key, "")
                if value:
                    waxs_parts.append(f"{key}={value}")
            support_parts = []
            for label, key in (
                ("peak", "peak_support_score"),
                ("background", "background_stability_score"),
                ("phase", "phase_support_score"),
                ("size", "size_support_score"),
                ("waxs_support_score", "waxs_support_score"),
            ):
                value = evidence.get(key)
                if value is not None:
                    support_parts.append(f"{label}={self._format_score_value(value)}")
            if waxs_parts:
                bits.append("core=" + ", ".join(waxs_parts[:3]))
            if support_parts:
                bits.append("support=" + " | ".join(support_parts[:4]))
        else:
            metric_bits = []
            for key in ("r_squared", "quality_score", "L_nm", "Xc_pct", "D_Scherrer_nm"):
                value = current_metrics.get(key, "")
                if value:
                    metric_bits.append(f"{key}={value}")
            if metric_bits:
                bits.append("core=" + ", ".join(metric_bits[:4]))
            if technique == "ir":
                feature = evidence.get("feature_evidence", {}) if isinstance(evidence.get("feature_evidence"), dict) else {}
                reference = feature.get("reference_evidence", {}) if isinstance(feature, dict) else {}
                assignment = feature.get("assignment_evidence", {}) if isinstance(feature, dict) else {}
                structure = feature.get("structure_evidence", {}) if isinstance(feature, dict) else {}
                if isinstance(reference, dict) and reference:
                    bits.append(
                        tr(
                            "RESULTS_REVIEW_IR_REFERENCE",
                            self._display_text(reference.get("band_count")),
                            self._display_text(reference.get("hit_count")),
                            self._display_text(reference.get("missing_count")),
                        )
                    )
                if isinstance(assignment, dict) and assignment.get("assignment_confidence") is not None:
                    bits.append(tr("RESULTS_REVIEW_IR_ASSIGNMENT", self._format_score_value(assignment.get("assignment_confidence"))))
                if isinstance(structure, dict):
                    basis = str(structure.get("classification_basis", "") or "").strip()
                    if basis:
                        bits.append(tr("RESULTS_REVIEW_IR_BASIS", self._ir_label_text(basis)))
                    if structure.get("characteristic_band_support_ok") is not None:
                        support_text = tr("IR_SUPPORT_COMPLETE") if bool(structure.get("characteristic_band_support_ok")) else tr("IR_SUPPORT_INCOMPLETE")
                        bits.append(tr("RESULTS_REVIEW_IR_SUPPORT", support_text))
                    if structure.get("paper_conclusion_ready") is not None:
                        bits.append(
                            tr(
                                "RESULTS_REVIEW_IR_CONCLUSION_STATE",
                                self._ir_conclusion_state_text(structure.get("paper_conclusion_ready")),
                            )
                        )
        validation = str(summary.get("validation_summary") or record.get("validation_summary") or "").strip()
        if validation:
            bits.append(f"validation={validation}")
        constraint_text = self._constraint_summary_text(evidence)
        if constraint_text != tr("AI_TUNING_EMPTY_VALUE"):
            bits.append(constraint_text)
        return " | ".join(bits) if bits else tr("AI_TUNING_EMPTY_VALUE")

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


class MainWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle(tr("WINDOW_TITLE"))

        self.resize(1280, 820)

        self.setMinimumSize(960, 600)

        self.setAcceptDrops(True)



        # Theme engine

        self._theme_engine = ThemeEngine.instance()



        self._current_technique = ""

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



    def _load_settings(self):

        raw = self._settings.value("recent_projects", "")

        if raw:

            try:

                self._recent_projects = json.loads(raw)

            except Exception:

                self._recent_projects = []
                logger.warning("Failed to load recent projects from settings.", exc_info=True)

        out = self._settings.value("output_dir", "")

        if out:

            self._output_dir = out

        last_export = self._settings.value("last_export_bundle", "")
        if last_export:
            self._last_export_bundle = str(last_export)


    def _get_last_dir(self) -> str:

        from pathlib import Path

        return self._settings.value("last_browse_dir", str(Path.home()), type=str)


    def _save_last_dir(self, path: str):

        from pathlib import Path

        directory = path if Path(path).is_dir() else str(Path(path).parent)
        self._settings.setValue("last_browse_dir", directory)



    def _save_settings(self):

        self._settings.setValue("recent_projects",

                                json.dumps(self._recent_projects[-10:]))

        self._settings.setValue("output_dir", self._output_dir)
        self._settings.setValue("last_export_bundle", self._last_export_bundle)



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



        self._btn_export = QPushButton(tr("BTN_EXPORT"))

        self._btn_export.setObjectName("secondary_btn")

        self._btn_export.clicked.connect(self._export_results)

        layout.addWidget(self._btn_export)

        return bar


    def setup_convergence_action(self):

        """Add the result review entry to the main window."""

        if not hasattr(self, "action_convergence_viewer"):
            self.action_convergence_viewer = QAction(tr('CONVERGENCE_DASHBOARD'), self)
            self.action_convergence_viewer.setObjectName("action_convergence_viewer")
            self.action_convergence_viewer.setText(tr('CONVERGENCE_DASHBOARD'))
            self.action_convergence_viewer.triggered.connect(self._open_convergence_viewer)
            if hasattr(self, "_menu_view"):
                self._menu_view.addAction(self.action_convergence_viewer)

        if hasattr(self, "_btn_convergence_viewer"):
            return

        self._btn_convergence_viewer = QPushButton(tr('CONVERGENCE_DASHBOARD'))
        self._btn_convergence_viewer.setObjectName("secondary_btn")
        self._btn_convergence_viewer.setText(tr('CONVERGENCE_DASHBOARD'))
        self._btn_convergence_viewer.clicked.connect(lambda: self.action_convergence_viewer.trigger())

        layout = getattr(self, "_topbar_layout", None)
        if layout is not None:
            export_button = getattr(self, "_btn_export", None)
            index = layout.indexOf(export_button) if export_button is not None else -1
            if index >= 0:
                layout.insertWidget(index, self._btn_convergence_viewer)
            else:
                layout.addWidget(self._btn_convergence_viewer)


    def _open_convergence_viewer(self):

        """Open the result review window in a separate window."""

        if hasattr(self, "_convergence_win") and self._convergence_win is not None:
            try:
                self._convergence_win.raise_()
                self._convergence_win.activateWindow()
                return
            except RuntimeError:
                pass

        try:
            from polynexus.gui.convergence_viewer import ConvergenceViewer

            self._convergence_win = ConvergenceViewer(parent=None)
            self._convergence_win.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            self._convergence_win.destroyed.connect(self._on_convergence_closed)
            self._convergence_win.show()
        except SystemExit as exc:
            self._convergence_win = None
            QMessageBox.warning(self, tr("CONVERGENCE_DASHBOARD"), tr("CONVERGENCE_OPEN_FAILED", exc))
        except Exception as exc:
            self._convergence_win = None
            QMessageBox.critical(self, tr("CONVERGENCE_DASHBOARD"), tr("CONVERGENCE_OPEN_FAILED", exc))
            logger.warning("Failed to open convergence dashboard.", exc_info=True)


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


    def _set_nav_visual_state(self, active_id, technique):

        for key, btn in self._nav_buttons.items():

            btn_tech = btn.property("technique") or technique

            is_active = key == active_id

            btn.setStyleSheet(self._nav_sub_style(btn_tech, is_active))

            btn.setChecked(is_active)

        if hasattr(self, "_nav_indicator"):

            self._nav_indicator.hide()


    def _refresh_sidebar_texts(self):

        if not hasattr(self, "_nav_buttons"):

            return

        for key, label in getattr(self, "_sidebar_section_labels", {}).items():

            label.setText(_lang_text(SIDEBAR_SECTIONS.get(key, {}), label.text()))

        for tech, btn in getattr(self, "_nav_parent_buttons", {}).items():

            icon = TECHNIQUE_ICONS.get(tech, "")

            label = TECHNIQUE_LABELS.get(tech, tech.upper())

            btn.setText(f"{icon}  {label}".strip())

            count = sum(
                1 for b in self._nav_buttons.values()
                if b.property("technique") == tech
            )

            btn.setToolTip(tr("SIDEBAR_SUBMODULE_COUNT", count))

        for nav_id, btn in self._nav_buttons.items():

            text = _lang_text(SIDEBAR_MODULE_TEXT.get(nav_id, {}), btn.text().strip())

            btn.setText(text)

            if nav_id in SIDEBAR_MODULE_TOOLTIPS:

                btn.setToolTip(_lang_text(SIDEBAR_MODULE_TOOLTIPS[nav_id]))

            tech = btn.property("technique") or self._current_technique or "waxs"

            btn.setStyleSheet(self._nav_sub_style(tech, btn.isChecked()))


    def _update_workspace_context(self):

        if not hasattr(self, "_workspace_title"):

            return

        tech = self._current_technique or "saxs"

        label = TECHNIQUE_LABELS.get(tech, tech.upper())
        title_key = "WORKSPACE_TITLE_ANALYSIS"

        if tech == "samples":
            label = tr("WORKFLOW_TECH_SAMPLES")
            title_key = "WORKSPACE_TITLE_SAMPLES"

        if tech == "joint":
            label = tr("WORKFLOW_TECH_JOINT")
            title_key = "WORKSPACE_TITLE_JOINT"

        submodule = getattr(self, "_current_submodule_id", "")

        is_zh = get_language() == "zh"

        if tech == "joint":

            count = 0

            hub = getattr(self, "_joint_hub", None)

            if hub is not None:

                count = len(hub.selected_rows())

            filename = (
                tr("WORKFLOW_SELECTED_BATCHES", count)
                if count else tr("WORKFLOW_EXISTING_RUNS")
            )

        else:

            filename = (
                os.path.basename(self._current_filepath.rstrip("/\\"))
                if self._current_filepath else tr("WORKFLOW_NO_DATA")
            )
            mode_text = self._workspace_input_mode_text()
            if mode_text and self._current_filepath:
                filename = f"{mode_text} | {filename}"

        if title_key == "WORKSPACE_TITLE_ANALYSIS":
            self._workspace_title.setText(tr(title_key, label))
        else:
            self._workspace_title.setText(tr(title_key))

        detail = (
            self._history_submodule_text(submodule) or submodule.replace(".", " / ")
            if submodule else tr("WORKSPACE_SUBTITLE_DEFAULT")
        )

        if tech == "joint":

            detail = tr("WORKSPACE_DETAIL_JOINT")

        self._workspace_subtitle.setText(f"{detail}  |  {filename}")

        if hasattr(self, "_workflow_metric_tech"):

            self._workflow_metric_tech.setText(label)

        if hasattr(self, "_status_tech_label"):

            self._status_tech_label.setText(f" {label} ")

        if hasattr(self, "_workflow_metric_data"):

            self._workflow_metric_data.setText(filename)

        if hasattr(self, "_workflow_metric_state"):

            current_state = self._workflow_metric_state.text()

            if current_state in (
                "Ready",
                "\u5c31\u7eea",
                tr("WORKFLOW_READY"),
                tr("WORKFLOW_SEQUENCE_READY"),
                tr("WORKFLOW_DIRECTORY_READY"),
                tr("WORKFLOW_BATCH_READY"),
            ):

                self._workflow_metric_state.setText(self._idle_workflow_state_text())

        self._update_workflow_task_card()
        self._update_context_suggestions()
        self._update_work_memory_panel()
        self._update_results_compare_panel()

    def _set_workflow_task_default(self):

        if not hasattr(self, "_workflow_task_box"):
            return
        self._workflow_task_label.setText(tr("WORKFLOW_TASK_LABEL"))
        self._workflow_task_title.setText(tr("WORKFLOW_TASK_DEFAULT_TITLE"))
        self._workflow_task_detail.setText(tr("WORKFLOW_TASK_DEFAULT_DETAIL"))


    def _jump_to_tab(self, index: int):

        if hasattr(self, "_tabs") and 0 <= index < self._tabs.count():
            self._tabs.setCurrentIndex(index)

    def _jump_to_sample_library(self):
        self._on_samples_selected()

    def _jump_to_joint_hub(self):
        self._on_joint_selected("joint.compare")

    def _jump_to_results(self):
        self._jump_to_tab(2)

    def _jump_to_history(self):
        self._jump_to_tab(4)

    def _open_last_export_bundle(self):
        bundle = str(getattr(self, "_last_export_bundle", "") or "").strip()
        if bundle and os.path.isdir(bundle):
            try:
                os.startfile(bundle)
                return
            except OSError:
                pass
        if self._output_dir and os.path.isdir(self._output_dir):
            try:
                os.startfile(self._output_dir)
            except OSError:
                pass


    def _workspace_input_mode_text(self):

        mode = str(getattr(self, "_current_input_mode", "") or "").strip().lower()
        if mode not in {"sequence", "directory"}:
            return ""
        return _import_mode_text(mode)


    def _workflow_task_tech_label(self, tech: str) -> str:

        if tech == "samples":
            return tr("WORKFLOW_TECH_SAMPLES")
        if tech == "joint":
            return tr("WORKFLOW_TECH_JOINT")
        return TECHNIQUE_LABELS.get(tech, tech.upper() if tech else tr("WORKFLOW_TASK_NO_TECH"))


    def _workflow_task_context(self):

        tech = str(getattr(self, "_current_technique", "") or "").strip().lower()
        submodule = str(getattr(self, "_current_submodule_id", "") or "").strip()
        input_mode = str(getattr(self, "_current_input_mode", "") or "").strip().lower()
        filepath = str(getattr(self, "_current_filepath", "") or "").strip()
        running = bool(self._btn_run.property("busy")) if hasattr(self, "_btn_run") else False
        is_dir = bool(filepath and os.path.isdir(filepath))
        source_name = os.path.basename(filepath.rstrip("/\\")) if filepath else ""
        source_text = source_name or tr("WORKFLOW_NO_DATA")
        mode_text = _import_mode_text(input_mode) if input_mode in {"sequence", "directory"} else ""
        if mode_text and filepath:
            source_text = f"{mode_text} | {source_text}"

        if tech == "joint":
            title = tr("WORKFLOW_TASK_JOINT_TITLE")
            detail = tr("WORKFLOW_TASK_JOINT_DETAIL")
        elif tech == "samples":
            title = tr("WORKFLOW_TASK_SAMPLES_TITLE")
            detail = tr("WORKFLOW_TASK_SAMPLES_DETAIL")
        elif bool(getattr(self, "_ai_tuning_active", False)):
            title = tr("WORKFLOW_TASK_AI_TUNING_TITLE")
            detail = tr("WORKFLOW_TASK_AI_TUNING_DETAIL")
        elif filepath and is_dir:
            if self._is_native_directory_run_context():
                title = tr("WORKFLOW_TASK_SEQUENCE_TITLE") if input_mode == "sequence" else tr("WORKFLOW_TASK_DIRECTORY_TITLE")
                detail = tr("WORKFLOW_TASK_SEQUENCE_DETAIL") if input_mode == "sequence" else tr("WORKFLOW_TASK_DIRECTORY_DETAIL")
            else:
                title = tr("WORKFLOW_TASK_BATCH_TITLE")
                detail = tr("WORKFLOW_TASK_BATCH_DETAIL")
        elif filepath:
            title = tr("WORKFLOW_TASK_SINGLE_TITLE")
            detail = tr("WORKFLOW_TASK_SINGLE_DETAIL")
        else:
            title = tr("WORKFLOW_TASK_IDLE_TITLE")
            detail = tr("WORKFLOW_TASK_IDLE_DETAIL")

        if submodule:
            submodule_text = self._history_submodule_text(submodule) or submodule.replace(".", " / ")
        else:
            submodule_text = tr("WORKFLOW_SUBMODULE_NONE")

        if tech == "joint":
            status = tr("WORKFLOW_TASK_STATUS_JOINT")
        elif filepath and is_dir:
            status = tr("WORKFLOW_TASK_STATUS_DIRECTORY" if self._is_native_directory_run_context() else "WORKFLOW_TASK_STATUS_BATCH")
        elif filepath:
            status = tr("WORKFLOW_TASK_STATUS_SINGLE")
        else:
            status = tr("WORKFLOW_TASK_STATUS_IDLE")

        if bool(getattr(self, "_ai_tuning_active", False)):
            status = tr("WORKFLOW_TASK_STATUS_AI_TUNING")
        if running:
            status = tr("WORKFLOW_TASK_STATUS_RUNNING")

        return {
            "title": title,
            "detail": detail,
            "status": status,
            "technique": self._workflow_task_tech_label(tech),
            "submodule": submodule_text,
            "source": source_text,
        }


    def _update_workflow_task_card(self):

        if not hasattr(self, "_workflow_task_box"):
            return

        task = self._workflow_task_context()
        self._workflow_task_label.setText(tr("WORKFLOW_TASK_LABEL"))
        self._workflow_task_title.setText(task["title"])
        self._workflow_task_detail.setText(
            tr(
                "WORKFLOW_TASK_DETAIL_TEMPLATE",
                task["status"],
                task["technique"],
                task["submodule"],
                task["source"],
                task["detail"],
            )
        )


    def _build_context_suggestion_panel(self, slot: str):

        panel = QFrame()
        panel.setObjectName("context_suggestion_box")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(12, 8, 12, 8)
        panel_layout.setSpacing(4)

        title = QLabel(tr("CONTEXT_HINT_TITLE"))
        title.setObjectName("context_suggestion_title")
        panel_layout.addWidget(title)

        detail = QLabel(tr("CONTEXT_HINT_DEFAULT_DETAIL"))
        detail.setObjectName("context_suggestion_detail")
        detail.setWordWrap(True)
        panel_layout.addWidget(detail)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 2, 0, 0)
        button_row.setSpacing(8)
        button_row.addStretch(1)

        buttons = []
        for _ in range(2):
            btn = QPushButton()
            btn.setObjectName("secondary_btn")
            btn.setVisible(False)
            btn.clicked.connect(self._invoke_context_suggestion_action)
            buttons.append(btn)
            button_row.addWidget(btn)

        panel_layout.addLayout(button_row)
        self._context_suggestion_panels[slot] = {
            "widget": panel,
            "title": title,
            "detail": detail,
            "buttons": buttons,
        }
        return panel

    def _build_work_memory_panel(self):

        panel = QFrame()
        panel.setObjectName("work_memory_box")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(12, 8, 12, 8)
        panel_layout.setSpacing(6)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        title = QLabel(tr("WORK_MEMORY_TITLE"))
        title.setObjectName("work_memory_title")
        header.addWidget(title, 1)

        refresh_btn = QPushButton(tr("WORK_MEMORY_REFRESH"))
        refresh_btn.setObjectName("secondary_btn")
        refresh_btn.clicked.connect(self._update_work_memory_panel)
        header.addWidget(refresh_btn)
        panel_layout.addLayout(header)

        detail = QLabel(tr("WORK_MEMORY_DEFAULT_DETAIL"))
        detail.setObjectName("work_memory_detail")
        detail.setWordWrap(True)
        panel_layout.addWidget(detail)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(6)

        buttons = []
        for _ in range(6):
            btn = QPushButton()
            btn.setObjectName("secondary_btn")
            btn.setVisible(False)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(self._invoke_work_memory_action)
            buttons.append(btn)
        for idx, btn in enumerate(buttons):
            grid.addWidget(btn, idx // 3, idx % 3)
        panel_layout.addLayout(grid)

        self._work_memory_panels = {
            "widget": panel,
            "title": title,
            "detail": detail,
            "buttons": buttons,
            "refresh": refresh_btn,
        }
        return panel

    def _invoke_work_memory_action(self):

        button = self.sender()
        if button is None:
            return
        action_key = str(button.property("work_memory_action_key") or "").strip()
        action = self._work_memory_action_map.get(action_key)
        if callable(action):
            action()

    def _work_memory_slice(self, label, detail, action_key="", callback=None, accent=""):
        return {
            "label": str(label or "").strip(),
            "detail": str(detail or "").strip(),
            "action_key": str(action_key or "").strip(),
            "callback": callback,
            "accent": str(accent or "").strip(),
        }

    def _work_memory_payload(self):

        db = self._ensure_sample_db()
        sample_count = 0
        batch_count = 0
        current_result = self._results.get(str(getattr(self, "_current_technique", "") or "").strip().lower())
        recent_run = None
        recent_sample = None
        recent_batch = None

        try:
            samples = db.list_samples(limit=1000)
        except Exception:
            samples = []

        sample_count = len(samples)
        for sample in samples:
            sample_id = str(sample.get("id") or "")
            if not sample_id:
                continue
            batches = db.get_batches(sample_id)
            batch_count += len(batches)
            if recent_sample is None:
                recent_sample = sample
            for batch in batches:
                if recent_batch is None:
                    recent_batch = batch
                runs = db.get_analysis_runs(batch.get("id", ""))
                if runs and recent_run is None:
                    recent_run = runs[0]

        slices = []

        if current_result is not None:
            current_detail = ""
            if hasattr(self, "_results_summary_label"):
                current_detail = str(self._results_summary_label.text() or "").strip()
            current_context = str(self._current_result_label_for_confirmation() or "").strip()
            current_origin = self._current_result_origin_label()
            current_confirmed = self._results_confirm_state_text()
            current_benchmark = ""
            tuning_context = getattr(self, "_last_ai_tuning_context", {})
            history_context = self._current_result_history_context(current_result)
            if (
                self._current_result_origin() == "controlled_optimization_rerun"
                and isinstance(tuning_context, dict)
            ):
                current_benchmark = str(tuning_context.get("benchmark_text") or "").strip()
            if (
                not current_benchmark
                and self._current_result_origin() == "controlled_optimization_rerun"
                and isinstance(history_context, dict)
            ):
                current_benchmark = str(history_context.get("benchmark_text") or "").strip()
                if not current_benchmark:
                    benchmark_summary = history_context.get("benchmark_summary") if isinstance(history_context.get("benchmark_summary"), dict) else {}
                    if isinstance(benchmark_summary, dict) and benchmark_summary:
                        current_benchmark = self._benchmark_summary_text(benchmark_summary)
            current_chain = ""
            if isinstance(tuning_context, dict) and tuning_context:
                current_chain = self._ai_tuning_chain_summary(
                    {
                        "benchmark_summary": tuning_context.get("benchmark_summary"),
                        "history": tuning_context.get("history") if isinstance(tuning_context.get("history"), list) else [],
                    }
                )
            if not current_detail and isinstance(current_result, dict):
                current_detail = self._history_metrics_tooltip(
                    {
                        "parameters": current_result.get("parameters", {}) if isinstance(current_result.get("parameters"), dict) else {},
                        "results_summary": current_result.get("results_summary", {}) if isinstance(current_result.get("results_summary"), dict) else {},
                    },
                    limit=3,
                )
            current_detail = " | ".join(
                part
                for part in [current_detail, current_context, current_origin, current_confirmed, current_benchmark, current_chain]
                if part
            )
            current_review_summary = str(self._result_review_summary() or "").strip()
            if current_review_summary and current_review_summary not in current_detail:
                current_detail = " | ".join(part for part in [current_detail, current_review_summary] if part)
            slices.append(self._work_memory_slice(
                tr("WORK_MEMORY_CURRENT"),
                current_detail or tr("WORK_MEMORY_CURRENT_DETAIL"),
                "results",
                self._jump_to_results,
            ))

        tech = str(getattr(self, "_current_technique", "") or "").strip().lower()
        if tech in {"saxs", "waxs"} and hasattr(self, "_current_submodule_id"):
            calibration_values = self._load_recent_calibration()
            scope_label = self._current_calibration_scope_label() or tr("WORKFLOW_SUBMODULE_NONE")
            if calibration_values:
                calibration_detail = tr("WORK_MEMORY_CALIBRATION_READY", scope_label)
                calibration_callback = self._on_apply_recent_calibration
            else:
                calibration_detail = tr("WORK_MEMORY_CALIBRATION_EMPTY", scope_label)
                calibration_callback = self._on_save_recent_calibration
            slices.append(self._work_memory_slice(
                tr("WORK_MEMORY_CALIBRATION"),
                calibration_detail,
                "config",
                calibration_callback,
            ))

        if recent_run:
            technique = self._history_technique_text(str(recent_run.get("technique") or ""))
            context = self._history_record_context_text(recent_run) or technique
            created = self._format_history_timestamp(recent_run.get("created_at"))
            output_dir = str(recent_run.get("output_dir") or "").strip()
            summary = self._history_metrics_tooltip(recent_run, limit=3)
            origin = self._history_result_origin_label(recent_run)
            confirmed = self._history_confirmation_label(recent_run)
            detail = " | ".join(part for part in [context, created, origin, confirmed, summary] if part)
            if output_dir:
                detail = f"{detail} | {os.path.basename(output_dir.rstrip('/\\')) or output_dir}"
            slices.append(self._work_memory_slice(
                tr("WORK_MEMORY_HISTORY"),
                detail or tr("WORK_MEMORY_EMPTY_DETAIL"),
                "history",
                self._jump_to_history,
            ))

        if recent_sample:
            sample_name = str(recent_sample.get("polymer_name") or "").strip()
            family = str(recent_sample.get("family") or "").strip()
            aliases = recent_sample.get("aliases") if isinstance(recent_sample.get("aliases"), list) else []
            alias_text = ", ".join(str(item) for item in aliases[:2] if str(item).strip())
            batch_text = str(recent_batch.get("label") or "").strip() if recent_batch else ""
            detail = " | ".join(part for part in [sample_name, family, alias_text] if part)
            if batch_text:
                detail = " | ".join(part for part in [detail, batch_text] if part)
            slices.append(self._work_memory_slice(
                tr("WORK_MEMORY_SAMPLE"),
                detail or tr("WORK_MEMORY_EMPTY_DETAIL"),
                "samples",
                self._jump_to_sample_library,
            ))

        if getattr(self, "_joint_report", None):
            joint_context = self._joint_ai_context()
            summary = str(joint_context.get("summary", "") or "").strip() if isinstance(joint_context, dict) else ""
            reminder = self._joint_ai_reminder_text(joint_context)
            compare_hint = self._joint_compare_hint_text(joint_context)
            detail_parts = [summary or tr("WORK_MEMORY_JOINT_READY")]
            if reminder:
                detail_parts.append(reminder)
            if compare_hint:
                detail_parts.append(compare_hint)
            detail = " | ".join(part for part in detail_parts if part)
            slices.append(self._work_memory_slice(
                tr("WORK_MEMORY_JOINT"),
                detail,
                "joint.compare",
                self._jump_to_joint_hub,
            ))

        if self._last_export_bundle or self._output_dir:
            bundle = self._last_export_bundle or self._output_dir
            label = tr("WORK_MEMORY_EXPORT")
            detail = os.path.basename(bundle.rstrip("/\\")) or bundle
            slices.append(self._work_memory_slice(
                label,
                detail,
                "export",
                self._open_last_export_bundle,
            ))

        if not slices:
            slices.append(self._work_memory_slice(
                tr("WORK_MEMORY_EMPTY_TITLE"),
                tr("WORK_MEMORY_EMPTY_DETAIL"),
                "",
                None,
            ))

        meta = []
        if sample_count:
            meta.append(tr("WORK_MEMORY_SAMPLE_COUNT", sample_count))
        if batch_count:
            meta.append(tr("WORK_MEMORY_BATCH_COUNT", batch_count))

        return {
            "title": tr("WORK_MEMORY_TITLE"),
            "detail": "  |  ".join(meta) if meta else tr("WORK_MEMORY_DEFAULT_DETAIL"),
            "slices": slices[:6],
        }

    def _work_memory_summary(self) -> str:

        payload = self._work_memory_payload()
        slices = payload.get("slices") if isinstance(payload.get("slices"), list) else []
        parts = []
        for item in slices[:3]:
            label = str(item.get("label") or "").strip()
            detail = str(item.get("detail") or "").strip()
            if label or detail:
                parts.append(f"{label}: {detail}" if label and detail else (label or detail))
        tuning_context = getattr(self, "_last_ai_tuning_context", {})
        if isinstance(tuning_context, dict) and tuning_context:
            benchmark_text = str(tuning_context.get("benchmark_text") or "").strip()
            if benchmark_text:
                benchmark_line = tr("RESULTS_REVIEW_BENCHMARK", benchmark_text)
                if benchmark_line not in parts:
                    parts.append(benchmark_line)
            chain_text = self._ai_tuning_chain_snapshot(tuning_context)
            if chain_text:
                chain_line = tr("RESULTS_REVIEW_CHAIN", chain_text)
                if chain_line not in parts:
                    parts.append(chain_line)
        joint_context = self._joint_ai_context()
        if isinstance(joint_context, dict) and joint_context:
            joint_summary = str(joint_context.get("summary") or "").strip()
            joint_reminder = self._joint_ai_reminder_text(joint_context)
            joint_compare_hint = self._joint_compare_hint_text(joint_context)
            joint_parts = [part for part in [joint_summary, joint_reminder, joint_compare_hint] if part]
            if joint_parts:
                joint_line = tr("WORK_MEMORY_JOINT") + ": " + " | ".join(joint_parts)
                if joint_line not in parts:
                    parts.append(joint_line)
        return " | ".join(parts)

    def _update_work_memory_panel(self):

        panel = getattr(self, "_work_memory_panels", None)
        if not panel or "widget" not in panel:
            return

        payload = self._work_memory_payload()
        panel["widget"].setVisible(True)
        panel["title"].setText(payload["title"])
        panel["detail"].setText(payload["detail"])

        self._work_memory_action_map = {}
        slices = list(payload.get("slices") or [])
        for idx, button in enumerate(panel["buttons"]):
            if idx < len(slices):
                item = slices[idx]
                action_key = str(item.get("action_key") or f"memory_{idx}").strip()
                button.setText(f"{item.get('label', '')}")
                button.setToolTip(str(item.get("detail") or item.get("label") or "").strip())
                button.setVisible(True)
                button.setEnabled(True)
                button.setProperty("work_memory_action_key", action_key)
                self._work_memory_action_map[action_key] = item.get("callback")
            else:
                button.setVisible(False)
                button.setToolTip("")
                button.setProperty("work_memory_action_key", "")


    def _invoke_context_suggestion_action(self):

        button = self.sender()
        if button is None:
            return
        action_key = str(button.property("context_action_key") or "").strip()
        action = self._context_suggestion_action_map.get(action_key)
        if callable(action):
            action()


    def _context_suggestion_payload(self, slot: str):

        tech = str(getattr(self, "_current_technique", "") or "").strip().lower()
        filepath = str(getattr(self, "_current_filepath", "") or "").strip()
        has_file = bool(filepath)
        has_results = bool(self._results or self._batch_results or self._joint_report)
        has_config = bool(getattr(self, "_config_form", None) is not None and self._config_form.rowCount() > 0)

        if slot == "data":
            if not has_file:
                return {
                    "title": tr("CONTEXT_HINT_DATA_TITLE"),
                    "detail": tr("CONTEXT_HINT_DATA_NEED_INPUT"),
                    "items": [
                        {
                            "text": tr("CONTEXT_HINT_ACTION_BROWSE_FILE"),
                            "action_key": "browse_file",
                            "callback": self._browse_file,
                        },
                        {
                            "text": tr("CONTEXT_HINT_ACTION_BROWSE_FOLDER"),
                            "action_key": "browse_folder",
                            "callback": self._browse_folder,
                        },
                    ],
                }
            return {
                "title": tr("CONTEXT_HINT_DATA_TITLE"),
                "detail": tr("CONTEXT_HINT_DATA_READY", os.path.basename(filepath.rstrip("/\\")) or filepath),
                "items": [
                    {
                        "text": tr("CONTEXT_HINT_ACTION_OPEN_CONFIG"),
                        "action_key": "open_config",
                        "callback": lambda: self._jump_to_tab(1),
                    },
                    {
                        "text": tr("CONTEXT_HINT_ACTION_OPEN_RESULTS" if has_results else "CONTEXT_HINT_ACTION_OPEN_HISTORY"),
                        "action_key": "open_results" if has_results else "open_history",
                        "callback": (lambda: self._jump_to_tab(2)) if has_results else (lambda: self._jump_to_tab(4)),
                    },
                ],
            }

        if slot == "config":
            if not has_file:
                return {
                    "title": tr("CONTEXT_HINT_CONFIG_TITLE"),
                    "detail": tr("CONTEXT_HINT_CONFIG_NEED_INPUT"),
                    "items": [
                        {
                            "text": tr("CONTEXT_HINT_ACTION_BACK_TO_DATA"),
                            "action_key": "back_to_data",
                            "callback": lambda: self._jump_to_tab(0),
                        },
                        {
                            "text": tr("CONTEXT_HINT_ACTION_OPEN_HISTORY"),
                            "action_key": "open_history",
                            "callback": lambda: self._jump_to_tab(4),
                        },
                    ],
                }

            if self._current_result_origin() == "controlled_optimization_rerun":
                return {
                    "title": tr("CONTEXT_HINT_CONFIG_TITLE"),
                    "detail": tr("CONTEXT_HINT_CONFIG_AI_TUNED"),
                    "items": [
                        {
                            "text": tr("CONTEXT_HINT_ACTION_REVIEW_AI_RESULT"),
                            "action_key": "review_ai_result",
                            "callback": lambda: self._jump_to_tab(2),
                        },
                        {
                            "text": tr("CONTEXT_HINT_ACTION_RUN_CONTROLLED_OPTIMIZATION"),
                            "action_key": "run_controlled_optimization",
                            "callback": self.on_ai_tune_clicked,
                        },
                    ],
                }

            if tech in {"saxs", "waxs"} and has_config:
                recent_values = self._load_recent_calibration()
                if recent_values:
                    primary_text = tr("CONTEXT_HINT_ACTION_APPLY_RECENT_CALIBRATION")
                    primary_callback = self._on_apply_recent_calibration
                else:
                    primary_text = tr("CONTEXT_HINT_ACTION_SAVE_RECENT_CALIBRATION")
                    primary_callback = self._on_save_recent_calibration
                return {
                    "title": tr("CONTEXT_HINT_CONFIG_TITLE"),
                    "detail": tr("CONTEXT_HINT_CONFIG_READY", self._current_calibration_scope_label() or tr("WORKFLOW_SUBMODULE_NONE")),
                    "items": [
                        {
                            "text": primary_text,
                            "action_key": "recent_calibration",
                            "callback": primary_callback,
                        },
                        {
                            "text": tr("CONTEXT_HINT_ACTION_OPEN_RESULTS" if has_results else "CONTEXT_HINT_ACTION_OPEN_HISTORY"),
                            "action_key": "open_results" if has_results else "open_history",
                            "callback": (lambda: self._jump_to_tab(2)) if has_results else (lambda: self._jump_to_tab(4)),
                        },
                    ],
                }

            return {
                "title": tr("CONTEXT_HINT_CONFIG_TITLE"),
                "detail": tr("CONTEXT_HINT_CONFIG_GENERIC"),
                "items": [
                    {
                        "text": tr("CONTEXT_HINT_ACTION_BACK_TO_DATA"),
                        "action_key": "back_to_data",
                        "callback": lambda: self._jump_to_tab(0),
                    },
                    {
                        "text": tr("CONTEXT_HINT_ACTION_OPEN_RESULTS" if has_results else "CONTEXT_HINT_ACTION_OPEN_HISTORY"),
                        "action_key": "open_results" if has_results else "open_history",
                        "callback": (lambda: self._jump_to_tab(2)) if has_results else (lambda: self._jump_to_tab(4)),
                    },
                ],
            }

        return None


    def _update_context_suggestion_panel(self, slot: str, payload):

        panel = self._context_suggestion_panels.get(slot)
        if panel is None:
            return

        panel["widget"].setVisible(bool(payload))
        if not payload:
            return

        panel["title"].setText(payload["title"])
        panel["detail"].setText(payload["detail"])

        items = list(payload.get("items") or [])
        for idx, button in enumerate(panel["buttons"]):
            if idx < len(items):
                item = items[idx]
                action_key = str(item.get("action_key") or f"{slot}_{idx}").strip()
                button.setText(str(item.get("text") or ""))
                button.setVisible(True)
                button.setEnabled(True)
                button.setProperty("context_action_key", action_key)
                self._context_suggestion_action_map[action_key] = item.get("callback")
            else:
                button.setVisible(False)
                button.setProperty("context_action_key", "")


    def _update_context_suggestions(self):

        self._context_suggestion_action_map = {}
        self._update_context_suggestion_panel("data", self._context_suggestion_payload("data"))
        self._update_context_suggestion_panel("config", self._context_suggestion_payload("config"))


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

            self._btn_run.setEnabled(bool(self._current_technique and self._current_technique != "samples"))


    def _on_joint_hub_selection_changed(self, count):

        if self._current_technique != "joint":

            return

        self._btn_run.setEnabled(count > 0)

        if hasattr(self, "_workflow_metric_data"):

            self._workflow_metric_data.setText(tr("WORKFLOW_SELECTED_BATCHES", count))


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

        title_box.addWidget(self._workspace_title)

        title_box.addWidget(self._workspace_subtitle)

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

        self._tabs.addTab(self._build_config_tab(), tr("TAB_CONFIG"))

        self._tabs.addTab(self._build_results_tab(), tr("TAB_RESULTS"))

        self._tabs.addTab(self._build_plots_tab(), tr("TAB_PLOTS"))

        history_widget = self._build_history_panel()
        self._tabs.addTab(history_widget, tr("TAB_HISTORY"))

        self._tabs.currentChanged.connect(self._on_tab_changed)

        layout.addWidget(self._tabs, 2)



        self._log_group = QGroupBox(tr("GROUP_LOG"))

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



        layout.addWidget(self._log_group, 1)

        return content_scroll



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

        self._joint_hub = JointAnalysisHub()
        self._joint_hub.selection_changed.connect(
            self._on_joint_hub_selection_changed)
        self._joint_hub.run_requested.connect(self._run_joint_hub)
        self._joint_hub.setVisible(False)
        layout.addWidget(self._joint_hub, 1)

        self._sample_browser = SampleBrowser()
        self._sample_browser.sample_created.connect(self._on_sample_created)
        self._sample_browser.sample_updated.connect(self._on_sample_updated)
        self._sample_browser.sample_selected.connect(self._on_sample_selected)
        self._sample_browser.batch_created.connect(self._on_sample_batch_created)
        self._sample_browser.batch_updated.connect(self._on_sample_batch_updated)
        self._sample_browser.batch_analysis_requested.connect(
            self._on_sample_batch_analysis_requested
        )
        self._sample_browser.joint_analysis_requested.connect(
            self._on_sample_joint_requested
        )
        self._sample_browser.setVisible(False)
        layout.addWidget(self._sample_browser, 1)

        layout.addStretch()

        return w



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



    def _build_results_tab(self):

        w = QWidget()

        layout = QVBoxLayout(w)
        self._work_memory_panel = self._build_work_memory_panel()
        layout.addWidget(self._work_memory_panel)

        self._joint_diagnostics_group = QGroupBox(tr("GROUP_JOINT_DIAGNOSTICS"))

        diag_layout = QVBoxLayout(self._joint_diagnostics_group)

        diag_layout.setSpacing(8)

        metric_layout = QGridLayout()

        metric_layout.setHorizontalSpacing(8)

        metric_layout.setVerticalSpacing(6)

        self._joint_metric_batches = self._build_joint_metric_label()

        self._joint_metric_checks = self._build_joint_metric_label()

        self._joint_metric_warnings = self._build_joint_metric_label()

        self._joint_metric_errors = self._build_joint_metric_label()

        for col, widget in enumerate([
            self._joint_metric_batches,
            self._joint_metric_checks,
            self._joint_metric_warnings,
            self._joint_metric_errors,
        ]):

            metric_layout.addWidget(widget, 0, col)

        diag_layout.addLayout(metric_layout)

        self._joint_diagnostics_table = QTableWidget()

        self._joint_diagnostics_table.setAlternatingRowColors(True)

        self._joint_diagnostics_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._joint_diagnostics_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._joint_diagnostics_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._joint_diagnostics_copy_shortcut = QShortcut(QKeySequence.Copy, self._joint_diagnostics_table)
        self._joint_diagnostics_copy_shortcut.activated.connect(
            lambda: self._copy_table_selection_to_clipboard(self._joint_diagnostics_table)
        )

        self._joint_diagnostics_table.setMaximumHeight(190)

        diag_layout.addWidget(self._joint_diagnostics_table)

        self._joint_diagnostics_group.setVisible(False)

        layout.addWidget(self._joint_diagnostics_group)

        self._results_summary_group = QGroupBox(tr("GROUP_RESULTS_SUMMARY"))
        self._results_summary_group.setVisible(False)
        self._results_summary_group.setObjectName("results_summary_group")
        summary_layout = QVBoxLayout(self._results_summary_group)
        summary_layout.setContentsMargins(12, 10, 12, 10)
        summary_layout.setSpacing(4)

        self._results_summary_label = QLabel()
        self._results_summary_label.setWordWrap(True)
        self._results_summary_label.setStyleSheet(f"color: {C_TEXT_PRIMARY}; font-weight: 600;")
        summary_layout.addWidget(self._results_summary_label)

        self._results_summary_risk_label = QLabel()
        self._results_summary_risk_label.setWordWrap(True)
        self._results_summary_risk_label.setStyleSheet(f"color: {C_TEXT_MUTED};")
        summary_layout.addWidget(self._results_summary_risk_label)

        self._results_summary_next_label = QLabel()
        self._results_summary_next_label.setWordWrap(True)
        self._results_summary_next_label.setStyleSheet(f"color: {C_TEXT_MUTED};")
        summary_layout.addWidget(self._results_summary_next_label)

        layout.addWidget(self._results_summary_group)

        self._results_review_group = QGroupBox(tr("GROUP_RESULTS_REVIEW"))
        self._results_review_group.setObjectName("results_review_group")
        review_layout = QVBoxLayout(self._results_review_group)
        review_layout.setContentsMargins(12, 10, 12, 10)
        review_layout.setSpacing(6)

        self._results_review_title = QLabel(tr("RESULTS_REVIEW_TITLE"))
        self._results_review_title.setWordWrap(True)
        self._results_review_title.setStyleSheet(f"color: {C_TEXT_PRIMARY}; font-weight: 600;")
        review_layout.addWidget(self._results_review_title)

        self._results_review_meta = QLabel()
        self._results_review_meta.setWordWrap(True)
        self._results_review_meta.setStyleSheet(f"color: {C_TEXT_MUTED};")
        review_layout.addWidget(self._results_review_meta)

        self._results_review_benchmark = QLabel()
        self._results_review_benchmark.setWordWrap(True)
        self._results_review_benchmark.setStyleSheet(f"color: {C_TEXT_MUTED};")
        review_layout.addWidget(self._results_review_benchmark)

        self._results_review_chain = QLabel()
        self._results_review_chain.setWordWrap(True)
        self._results_review_chain.setStyleSheet(f"color: {C_TEXT_MUTED};")
        self._results_review_chain.setVisible(False)
        review_layout.addWidget(self._results_review_chain)

        self._results_review_trend = QLabel()
        self._results_review_trend.setWordWrap(True)
        self._results_review_trend.setStyleSheet(f"color: {C_TEXT_MUTED};")
        self._results_review_trend.setVisible(False)
        review_layout.addWidget(self._results_review_trend)

        self._results_review_boundary = QLabel()
        self._results_review_boundary.setWordWrap(True)
        self._results_review_boundary.setStyleSheet(f"color: {C_TEXT_MUTED};")
        self._results_review_boundary.setVisible(False)
        review_layout.addWidget(self._results_review_boundary)

        self._results_review_joint = QLabel()
        self._results_review_joint.setWordWrap(True)
        self._results_review_joint.setStyleSheet(f"color: {C_TEXT_MUTED};")
        review_layout.addWidget(self._results_review_joint)

        self._results_review_risk = QLabel()
        self._results_review_risk.setWordWrap(True)
        self._results_review_risk.setStyleSheet(f"color: {C_TEXT_MUTED};")
        review_layout.addWidget(self._results_review_risk)

        self._results_review_next = QLabel()
        self._results_review_next.setWordWrap(True)
        self._results_review_next.setStyleSheet(f"color: {C_TEXT_MUTED};")
        review_layout.addWidget(self._results_review_next)

        review_actions = QHBoxLayout()
        review_actions.setContentsMargins(0, 0, 0, 0)
        review_actions.setSpacing(8)
        review_actions.addStretch(1)
        self._results_review_joint_btn = QPushButton(tr("RESULTS_REVIEW_OPEN_JOINT"))
        self._results_review_joint_btn.setObjectName("secondary_btn")
        self._results_review_joint_btn.clicked.connect(self._jump_to_joint_hub)
        review_actions.addWidget(self._results_review_joint_btn)
        self._results_review_compare_btn = QPushButton(tr("RESULTS_REVIEW_OPEN_COMPARE"))
        self._results_review_compare_btn.setObjectName("secondary_btn")
        self._results_review_compare_btn.clicked.connect(self._open_current_result_comparison)
        review_actions.addWidget(self._results_review_compare_btn)
        review_layout.addLayout(review_actions)

        self._results_review_group.setVisible(False)
        layout.addWidget(self._results_review_group)

        self._results_compare_group = QGroupBox(tr("GROUP_RESULTS_COMPARE"))
        self._results_compare_group.setObjectName("results_compare_group")
        compare_layout = QVBoxLayout(self._results_compare_group)
        compare_layout.setContentsMargins(12, 10, 12, 10)
        compare_layout.setSpacing(6)

        self._results_compare_desc = QLabel(tr("RESULTS_COMPARE_DESC"))
        self._results_compare_desc.setWordWrap(True)
        self._results_compare_desc.setStyleSheet(f"color: {C_TEXT_PRIMARY}; font-weight: 600;")
        compare_layout.addWidget(self._results_compare_desc)

        selector_row = QHBoxLayout()
        selector_row.setContentsMargins(0, 0, 0, 0)
        selector_row.setSpacing(8)
        self._results_compare_selector_label = QLabel(tr("RESULTS_COMPARE_SELECT"))
        self._results_compare_selector_label.setStyleSheet(f"color: {C_TEXT_MUTED}; font-weight: 600;")
        selector_row.addWidget(self._results_compare_selector_label)
        self._results_compare_selector = QComboBox()
        self._results_compare_selector.setObjectName("results_compare_selector")
        self._results_compare_selector.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._results_compare_selector.setMinimumContentsLength(24)
        self._results_compare_selector.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self._results_compare_selector.currentIndexChanged.connect(self._on_results_compare_candidate_changed)
        selector_row.addWidget(self._results_compare_selector, 1)
        compare_layout.addLayout(selector_row)

        self._results_compare_current = QLabel(tr("RESULTS_COMPARE_CURRENT"))
        self._results_compare_current.setWordWrap(True)
        self._results_compare_current.setStyleSheet(f"color: {C_TEXT_MUTED};")
        compare_layout.addWidget(self._results_compare_current)

        self._results_compare_baseline = QLabel(tr("RESULTS_COMPARE_BASELINE"))
        self._results_compare_baseline.setWordWrap(True)
        self._results_compare_baseline.setStyleSheet(f"color: {C_TEXT_MUTED};")
        compare_layout.addWidget(self._results_compare_baseline)

        self._results_compare_hint = QLabel(tr("RESULTS_COMPARE_HINT"))
        self._results_compare_hint.setWordWrap(True)
        self._results_compare_hint.setStyleSheet(f"color: {C_TEXT_MUTED};")
        compare_layout.addWidget(self._results_compare_hint)

        compare_actions = QHBoxLayout()
        compare_actions.setContentsMargins(0, 0, 0, 0)
        compare_actions.addStretch(1)
        self._results_compare_joint_btn = QPushButton(tr("RESULTS_COMPARE_JOINT"))
        self._results_compare_joint_btn.setObjectName("secondary_btn")
        self._results_compare_joint_btn.clicked.connect(self._jump_to_joint_hub)
        self._results_compare_joint_btn.setVisible(False)
        compare_actions.addWidget(self._results_compare_joint_btn)
        self._results_compare_open_btn = QPushButton(tr("RESULTS_COMPARE_OPEN"))
        self._results_compare_open_btn.setObjectName("secondary_btn")
        self._results_compare_open_btn.clicked.connect(self._open_current_result_comparison)
        compare_actions.addWidget(self._results_compare_open_btn)
        compare_layout.addLayout(compare_actions)

        self._results_compare_group.setVisible(False)
        layout.addWidget(self._results_compare_group)

        self._results_confirm_group = QGroupBox(tr("RESULTS_CONFIRM_GROUP"))
        self._results_confirm_group.setObjectName("results_confirm_group")
        confirm_layout = QVBoxLayout(self._results_confirm_group)
        confirm_layout.setContentsMargins(12, 10, 12, 10)
        confirm_layout.setSpacing(6)

        self._results_confirm_desc = QLabel(tr("RESULTS_CONFIRM_DESC"))
        self._results_confirm_desc.setWordWrap(True)
        self._results_confirm_desc.setStyleSheet(f"color: {C_TEXT_PRIMARY}; font-weight: 600;")
        confirm_layout.addWidget(self._results_confirm_desc)

        self._results_confirm_status = QLabel(tr("RESULTS_CONFIRM_STATUS_PENDING"))
        self._results_confirm_status.setWordWrap(True)
        self._results_confirm_status.setStyleSheet(f"color: {C_TEXT_MUTED};")
        confirm_layout.addWidget(self._results_confirm_status)

        confirm_actions = QHBoxLayout()
        confirm_actions.setContentsMargins(0, 0, 0, 0)
        confirm_actions.addStretch(1)
        self._results_confirm_btn = QPushButton(tr("RESULTS_CONFIRM_MARK"))
        self._results_confirm_btn.setObjectName("secondary_btn")
        self._results_confirm_btn.clicked.connect(self._toggle_current_result_confirmation)
        confirm_actions.addWidget(self._results_confirm_btn)
        confirm_layout.addLayout(confirm_actions)

        self._results_confirm_group.setVisible(False)
        layout.addWidget(self._results_confirm_group)

        self._results_table = QTableWidget()

        self._results_table.setAlternatingRowColors(True)
        self._results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._results_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._results_table.setWordWrap(False)
        self._results_table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self._results_table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self._results_table.horizontalHeader().setStretchLastSection(False)
        self._results_copy_shortcut = QShortcut(QKeySequence.Copy, self._results_table)
        self._results_copy_shortcut.activated.connect(self._copy_results_table_to_clipboard)

        layout.addWidget(self._results_table)

        action_row = QHBoxLayout()
        self._btn_results_export = QPushButton()
        self._btn_results_export.setObjectName("secondary_btn")
        self._btn_results_export.setVisible(False)
        self._btn_results_export.clicked.connect(self._export_results_table)
        action_row.addWidget(self._btn_results_export)
        self._btn_results_copy = QPushButton()
        self._btn_results_copy.setObjectName("secondary_btn")
        self._btn_results_copy.setVisible(False)
        self._btn_results_copy.clicked.connect(self._copy_results_table_to_clipboard)
        action_row.addWidget(self._btn_results_copy)
        self._btn_results_default_order = QPushButton()
        self._btn_results_default_order.setObjectName("secondary_btn")
        self._btn_results_default_order.setVisible(False)
        self._btn_results_default_order.clicked.connect(self._restore_results_table_default_order)
        action_row.addWidget(self._btn_results_default_order)
        action_row.addStretch()
        self._btn_ai_tune = QPushButton(tr('AI_TUNING_BUTTON'))
        self._btn_ai_tune.setObjectName("secondary_btn")
        self._btn_ai_tune.clicked.connect(self.on_ai_tune_clicked)
        action_row.addWidget(self._btn_ai_tune)
        layout.addLayout(action_row)

        return w


    def _current_results_payload(self) -> dict:

        technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
        result = self._results.get(technique)
        if result is None:
            return {}
        if isinstance(result, dict):
            return self._result_to_jsonable(result)
        if hasattr(result, "to_dict"):
            return self._result_to_jsonable(result.to_dict())
        payload = getattr(result, "__dict__", {})
        if isinstance(payload, dict) and payload:
            return self._result_to_jsonable(payload)
        fallback = {}
        for key in (
            "parameters",
            "validation_summary",
            "validation_warnings",
            "validation_passed",
            "quality_flags",
            "results_summary",
            "analysis_evidence",
        ):
            if hasattr(result, key):
                fallback[key] = getattr(result, key)
        return self._result_to_jsonable(fallback)


    def _current_results_record(self) -> dict:

        technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
        payload = self._current_results_payload()
        if not isinstance(payload, dict) or not payload:
            return {}
        params = payload.get("parameters") if isinstance(payload.get("parameters"), dict) else {}
        summary_payload = payload.get("results_summary") if isinstance(payload.get("results_summary"), dict) else {}
        history_context = summary_payload.get("history_context") if isinstance(summary_payload.get("history_context"), dict) else {}
        if not isinstance(history_context, dict) or not history_context:
            history_context = payload.get("history_context") if isinstance(payload.get("history_context"), dict) else {}
        if not isinstance(history_context, dict):
            history_context = {}

        def _normalized_text_list(value) -> list[str]:
            value = self._result_to_jsonable(value)
            if isinstance(value, list):
                return [str(item).strip() for item in value if str(item).strip()]
            text = str(value or "").strip()
            return [text] if text else []

        project_label = str(summary_payload.get("project_label") or "").strip()
        if not project_label:
            project_label = self._project_label.text().strip()
        if not project_label or _is_default_project_label(project_label):
            project_label = self._infer_sample_name()
        validation_summary = str(
            payload.get("validation_summary")
            or summary_payload.get("validation_summary")
            or params.get("validation_summary")
            or ""
        ).strip()
        validation_warnings = _normalized_text_list(
            payload.get("validation_warnings")
            or summary_payload.get("validation_warnings")
            or params.get("validation_warnings")
            or []
        )
        quality_flags = payload.get("quality_flags")
        if not isinstance(quality_flags, dict):
            quality_flags = summary_payload.get("quality_flags")
        if not isinstance(quality_flags, dict):
            quality_flags = params.get("quality_flags")
        if not isinstance(quality_flags, dict):
            quality_flags = {}
        validation_passed = payload.get("validation_passed")
        if validation_passed is None:
            validation_passed = summary_payload.get("validation_passed")
        if validation_passed is None:
            validation_passed = params.get("validation_passed")
        if validation_passed is None:
            validation_passed = True
        result_payload = dict(payload)
        if validation_summary:
            result_payload["validation_summary"] = validation_summary
        if validation_warnings:
            result_payload["validation_warnings"] = validation_warnings
        if quality_flags:
            result_payload["quality_flags"] = quality_flags
        result_payload["validation_passed"] = bool(validation_passed)
        summary = {
            "result": result_payload,
            "data_file": str(self._current_filepath or ""),
            "project_label": project_label,
            "status": "completed",
            "technique": technique,
            "submodule": str(getattr(self, "_current_submodule_id", "") or ""),
            "result_origin": self._current_result_origin(),
            "ai_tuned": self._current_result_origin() == "controlled_optimization_rerun",
            "confirmed": bool(getattr(self, "_current_result_confirmed_flag", False)),
            "validation_summary": validation_summary,
            "validation_warnings": validation_warnings,
            "validation_passed": bool(validation_passed),
            "quality_flags": quality_flags,
            "history_context": history_context,
        }
        current_file = str(self._current_filepath or "").strip()
        return {
            "id": "current",
            "batch_id": "current",
            "technique": technique,
            "submodule": str(getattr(self, "_current_submodule_id", "") or ""),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "results_summary": summary,
            "parameters": params,
            "validation_summary": summary.get("validation_summary", ""),
            "validation_warnings": summary.get("validation_warnings", []),
            "validation_passed": summary.get("validation_passed", True),
            "quality_flags": summary.get("quality_flags", {}),
            "output_dir": str(self._output_dir or ""),
            "status": "completed",
            "source_data": current_file,
            "confirmed": bool(getattr(self, "_current_result_confirmed_flag", False)),
        }

    def _current_result_history_context(self, current=None) -> dict:

        current = current if isinstance(current, dict) else self._current_results_record()
        if not isinstance(current, dict) or not current:
            return {}
        summary = current.get("results_summary") if isinstance(current.get("results_summary"), dict) else {}
        if not isinstance(summary, dict) or not summary:
            return {}
        history_context = summary.get("history_context") if isinstance(summary.get("history_context"), dict) else {}
        return history_context if isinstance(history_context, dict) and history_context else {}

    def _current_result_tuning_context(self, current=None) -> dict:

        tuning_context = getattr(self, "_last_ai_tuning_context", {})
        if isinstance(tuning_context, dict) and tuning_context:
            return tuning_context
        history_context = self._current_result_history_context(current)
        if not isinstance(history_context, dict) or not history_context:
            return {}
        restored_context = history_context.get("tuning_context") if isinstance(history_context.get("tuning_context"), dict) else {}
        if not isinstance(restored_context, dict) or not restored_context:
            return {}
        restored_context = dict(restored_context)
        joint_context = history_context.get("joint_ai_context") if isinstance(history_context.get("joint_ai_context"), dict) else {}
        if isinstance(joint_context, dict) and joint_context and not isinstance(restored_context.get("joint_ai_context"), dict):
            restored_context["joint_ai_context"] = joint_context
        return restored_context

    def _current_analysis_evidence(self):
        current = self._current_results_record()
        if not isinstance(current, dict) or not current:
            return {}
        return self._find_analysis_evidence(current)

    def _find_analysis_evidence(self, node, *, max_depth: int = 5) -> dict:
        seen = set()
        stack = [(node, 0)]
        while stack:
            current, depth = stack.pop()
            if depth > max_depth or not isinstance(current, dict):
                continue
            marker = id(current)
            if marker in seen:
                continue
            seen.add(marker)

            evidence = current.get("analysis_evidence")
            if isinstance(evidence, dict) and evidence:
                return evidence

            if depth >= max_depth:
                continue

            for key in ("results_summary", "result"):
                child = current.get(key)
                if isinstance(child, dict):
                    stack.append((child, depth + 1))

            for value in current.values():
                if isinstance(value, dict):
                    stack.append((value, depth + 1))
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            stack.append((item, depth + 1))
        return {}

    def _waxs_support_snapshot(self, analysis_evidence=None) -> dict[str, float | None]:
        analysis_evidence = analysis_evidence if isinstance(analysis_evidence, dict) else self._current_analysis_evidence()
        if not isinstance(analysis_evidence, dict):
            analysis_evidence = {}
        snapshot = {}
        for key in (
            "peak_support_score",
            "background_stability_score",
            "phase_support_score",
            "size_support_score",
            "D_trend_support_score",
            "waxs_support_score",
        ):
            try:
                value = float(analysis_evidence.get(key))
            except (TypeError, ValueError):
                value = None
            snapshot[key] = value
        return snapshot

    def _waxs_structure_evidence(self, analysis_evidence=None) -> dict:
        analysis_evidence = analysis_evidence if isinstance(analysis_evidence, dict) else self._current_analysis_evidence()
        if not isinstance(analysis_evidence, dict):
            return {}
        structure = analysis_evidence.get("structure_evidence")
        return structure if isinstance(structure, dict) else {}

    def _waxs_temperature_trend_evidence(self, analysis_evidence=None) -> dict:
        analysis_evidence = analysis_evidence if isinstance(analysis_evidence, dict) else self._current_analysis_evidence()
        if not isinstance(analysis_evidence, dict):
            return {}
        feature = analysis_evidence.get("feature_evidence", {})
        if not isinstance(feature, dict):
            return {}
        trend = feature.get("scherrer_trend_evidence")
        return trend if isinstance(trend, dict) else {}

    def _waxs_temperature_trend_text(self, analysis_evidence=None) -> str:
        analysis_evidence = analysis_evidence if isinstance(analysis_evidence, dict) else self._current_analysis_evidence()
        if not isinstance(analysis_evidence, dict) or not analysis_evidence:
            return ""
        feature = analysis_evidence.get("feature_evidence", {})
        if not isinstance(feature, dict):
            feature = {}
        seq = feature.get("sequence_evidence", {})
        if not isinstance(seq, dict):
            seq = {}
        family = feature.get("peak_family_evidence", {})
        if not isinstance(family, dict):
            family = {}
        trend = feature.get("scherrer_trend_evidence", {})
        if not isinstance(trend, dict):
            trend = {}
        xc_trend = feature.get("crystallinity_trend_evidence", feature.get("trend_evidence", {}))
        if not isinstance(xc_trend, dict):
            xc_trend = {}
        transition = feature.get("transition_evidence", {})
        if not isinstance(transition, dict):
            transition = {}
        parts = []
        axis = seq.get("temperature_axis_confidence")
        if axis is not None:
            parts.append(f"axis={self._format_score_value(axis)}")
        family_score = family.get("peak_family_continuity_score")
        if family_score is not None:
            parts.append(f"family={self._format_score_value(family_score)}")
        xc_score = xc_trend.get("Xc_trend_support_score")
        if xc_score is not None:
            parts.append(f"Xc={self._format_score_value(xc_score)}")
        score = trend.get("D_trend_support_score")
        if score is not None:
            parts.append(f"score={self._format_score_value(score)}")
            parts.append(f"D={self._format_score_value(score)}")
        transition_score = transition.get("transition_support_score")
        if transition_score is not None:
            parts.append(f"transition={self._format_score_value(transition_score)}")
        mode = str(trend.get("D_trend_monotonicity", "") or "").strip()
        if mode:
            parts.append(f"mode={mode}")
        support = trend.get("D_support_peak_count")
        if support is not None:
            parts.append(f"support={self._display_text(support)}")
        candidate_count = transition.get("transition_candidate_count")
        if candidate_count is not None:
            parts.append(f"candidates={self._display_text(candidate_count)}")
        if trend.get("instrument_broadening_present") is not None:
            parts.append(f"instrument_broadening={bool(trend.get('instrument_broadening_present'))}")
        return ", ".join(parts)

    def _waxs_result_semantic_lines(self, current_metrics=None, analysis_evidence=None) -> list[str]:
        current_metrics = current_metrics if isinstance(current_metrics, dict) else {}
        analysis_evidence = analysis_evidence if isinstance(analysis_evidence, dict) else self._current_analysis_evidence()
        support = self._waxs_support_snapshot(analysis_evidence)
        structure = self._waxs_structure_evidence(analysis_evidence)
        trend = self._waxs_temperature_trend_evidence(analysis_evidence)

        peak_count = current_metrics.get("n_peaks", "")
        xc_pct = current_metrics.get("Xc_pct", "")
        size_nm = current_metrics.get("D_Scherrer_nm", "")
        peak_score = support.get("peak_support_score")
        phase_score = support.get("phase_support_score")
        size_score = support.get("size_support_score")
        overall_score = support.get("waxs_support_score")

        lines = []
        peak_text = f"n_peaks={peak_count}" if peak_count != "" else tr("AI_TUNING_EMPTY_VALUE")
        if peak_score is not None:
            peak_text += f", score={self._format_score_value(peak_score)}"
        lines.append(tr("WAXS_REVIEW_PEAK_SUPPORT", peak_text))

        crystallinity_text = f"Xc_pct={xc_pct}" if xc_pct != "" else tr("AI_TUNING_EMPTY_VALUE")
        if phase_score is not None:
            crystallinity_text += f", score={self._format_score_value(phase_score)}"
        lines.append(tr("WAXS_REVIEW_CRYSTALLINITY_ESTIMATE", crystallinity_text))

        size_text = f"D_Scherrer_nm={size_nm}" if size_nm != "" else tr("AI_TUNING_EMPTY_VALUE")
        if size_score is not None:
            size_text += f", score={self._format_score_value(size_score)}"
        lines.append(tr("WAXS_REVIEW_SIZE_ESTIMATE", size_text))

        if trend:
            trend_bits = []
            for label, value in (
                ("score", trend.get("D_trend_support_score")),
                ("mode", trend.get("D_trend_monotonicity")),
                ("support", trend.get("D_support_peak_count")),
            ):
                text = self._display_text(value)
                if text != tr("AI_TUNING_EMPTY_VALUE"):
                    trend_bits.append(f"{label}={text}")
            if trend.get("instrument_broadening_present") is not None:
                trend_bits.append(f"instrument_broadening={bool(trend.get('instrument_broadening_present'))}")
            if trend_bits:
                lines.append(tr("WAXS_REVIEW_D_TREND", ", ".join(trend_bits)))
        sequence_text = self._waxs_temperature_trend_text(analysis_evidence)
        if sequence_text:
            lines.append(tr("WAXS_REVIEW_TEMPERATURE_SEQUENCE", sequence_text))

        if structure.get("paper_ready_candidate"):
            lines.append(tr("WAXS_REVIEW_PAPER_READY"))
        else:
            if structure.get("physical_support_pass") is False or (overall_score is not None and overall_score < 0.72):
                lines.append(tr("WAXS_REVIEW_PHYSICAL_SUPPORT_LIMITED"))
            if structure.get("fit_only_pass") and not structure.get("physical_support_pass"):
                lines.append(tr("WAXS_REVIEW_FIGURE_USABLE_PENDING"))
            if peak_score is not None and peak_score < 0.75:
                lines.append(tr("WAXS_REVIEW_PEAK_FAMILY_NEEDS_REVIEW"))

        return [str(item).strip() for item in lines if str(item).strip()]

    def _history_record_analysis_evidence(self, record) -> dict:
        evidence = self._find_analysis_evidence(record)
        if not isinstance(evidence, dict) or not evidence:
            return {}
        submodule = str(record.get("submodule") or "").strip().lower() if isinstance(record, dict) else ""
        technique = str(record.get("technique") or "").strip().lower() if isinstance(record, dict) else ""
        if technique != "waxs" and submodule != "waxs.temperature":
            return evidence

        feature = evidence.get("feature_evidence") if isinstance(evidence.get("feature_evidence"), dict) else {}
        if not isinstance(feature, dict):
            feature = {}

        normalized_feature = dict(feature)
        sequence = dict(normalized_feature.get("sequence_evidence")) if isinstance(normalized_feature.get("sequence_evidence"), dict) else {}
        peak_family = dict(normalized_feature.get("peak_family_evidence")) if isinstance(normalized_feature.get("peak_family_evidence"), dict) else {}
        trend = dict(
            normalized_feature.get("crystallinity_trend_evidence")
            if isinstance(normalized_feature.get("crystallinity_trend_evidence"), dict)
            else normalized_feature.get("trend_evidence")
            if isinstance(normalized_feature.get("trend_evidence"), dict)
            else {}
        )
        scherrer_trend = dict(normalized_feature.get("scherrer_trend_evidence")) if isinstance(normalized_feature.get("scherrer_trend_evidence"), dict) else {}
        transition = dict(normalized_feature.get("transition_evidence")) if isinstance(normalized_feature.get("transition_evidence"), dict) else {}

        flat_sequence_keys = ("temperature_axis_confidence",)
        flat_peak_family_keys = ("peak_family_continuity_score",)
        flat_trend_keys = ("Xc_trend_support_score",)
        flat_scherrer_keys = ("D_trend_support_score", "D_trend_monotonicity", "D_support_peak_count", "instrument_broadening_present")
        flat_transition_keys = ("transition_support_score", "transition_candidate_count")

        for key in flat_sequence_keys:
            value = evidence.get(key)
            if value is not None and key not in sequence:
                sequence[key] = value
        for key in flat_peak_family_keys:
            value = evidence.get(key)
            if value is not None and key not in peak_family:
                peak_family[key] = value
        for key in flat_trend_keys:
            value = evidence.get(key)
            if value is not None and key not in trend:
                trend[key] = value
        for key in flat_scherrer_keys:
            value = evidence.get(key)
            if value is not None and key not in scherrer_trend:
                scherrer_trend[key] = value
        for key in flat_transition_keys:
            value = evidence.get(key)
            if value is not None and key not in transition:
                transition[key] = value

        if sequence:
            normalized_feature["sequence_evidence"] = sequence
        if peak_family:
            normalized_feature["peak_family_evidence"] = peak_family
        if trend:
            normalized_feature["crystallinity_trend_evidence"] = trend
            normalized_feature.setdefault("trend_evidence", trend)
        if scherrer_trend:
            normalized_feature["scherrer_trend_evidence"] = scherrer_trend
        if transition:
            normalized_feature["transition_evidence"] = transition

        normalized = dict(evidence)
        normalized["feature_evidence"] = normalized_feature
        return normalized

    def _format_score_value(self, value, signed=False):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return tr("AI_TUNING_EMPTY_VALUE")
        sign = "+" if signed and number > 0 else ""
        return f"{sign}{number:.3f}"

    def _constraint_summary_text(self, analysis_evidence):
        summary = analysis_evidence.get("constraint_summary", {}) if isinstance(analysis_evidence, dict) else {}
        if not isinstance(summary, dict) or not summary:
            return tr("AI_TUNING_EMPTY_VALUE")
        counts = summary.get("triggered_counts", {}) if isinstance(summary.get("triggered_counts"), dict) else {}
        base = tr(
            "AI_TUNING_CONSTRAINT_SUMMARY",
            self._display_text_value(summary.get("status")),
            int(counts.get("hard_fail", 0) or 0),
            int(counts.get("soft_warn", 0) or 0),
            int(counts.get("evidence_only", 0) or 0),
        )
        triggered_names = summary.get("triggered_names", {}) if isinstance(summary.get("triggered_names"), dict) else {}
        names = []
        for key in ("hard_fail", "soft_warn", "evidence_only"):
            value = triggered_names.get(key, [])
            if isinstance(value, list):
                for item in value:
                    text = str(item or "").strip()
                    if text and text not in names:
                        names.append(text)
        if names:
            return f"{base}; {tr('AI_TUNING_CONSTRAINT_NAMES', ', '.join(names[:4]))}"
        return base

    def _result_source_summary_text(self, record: dict[str, Any] | None = None) -> str:
        record = record if isinstance(record, dict) else self._current_results_record()
        if not isinstance(record, dict) or not record:
            return tr("AI_TUNING_EMPTY_VALUE")

        summary = record.get("results_summary") if isinstance(record.get("results_summary"), dict) else {}
        if not isinstance(summary, dict):
            summary = {}

        evidence = self._history_record_analysis_evidence(record)
        if not evidence and str(record.get("id") or "").strip() == "current":
            evidence = self._current_analysis_evidence()

        current_metrics = self._history_result_metrics(record)
        origin = self._history_result_origin_label(record) or self._current_result_origin_label()
        bits = [part for part in [origin] if part]
        technique = str(record.get("technique") or self._current_technique or "").strip().lower()
        if technique == "waxs":
            trend = self._waxs_temperature_trend_evidence(evidence)
            waxs_parts = []
            for key in ("n_peaks", "Xc_pct", "D_Scherrer_nm"):
                value = current_metrics.get(key, "")
                if value:
                    waxs_parts.append(f"{key}={value}")
            support_parts = []
            for label, key in (
                ("peak", "peak_support_score"),
                ("background", "background_stability_score"),
                ("phase", "phase_support_score"),
                ("size", "size_support_score"),
            ):
                value = evidence.get(key)
                if value is not None:
                    support_parts.append(f"{label}={self._format_score_value(value)}")
            if isinstance(trend, dict) and trend.get("D_trend_support_score") is not None:
                support_parts.append(f"D_trend={self._format_score_value(trend.get('D_trend_support_score'))}")
            waxs_support_value = evidence.get("waxs_support_score")
            if waxs_support_value is not None:
                support_parts.append(f"waxs_support_score={self._format_score_value(waxs_support_value)}")
            trend_bits = []
            for label, value in (
                ("score", trend.get("D_trend_support_score") if isinstance(trend, dict) else None),
                ("mode", trend.get("D_trend_monotonicity") if isinstance(trend, dict) else None),
            ):
                text = self._display_text(value)
                if text != tr("AI_TUNING_EMPTY_VALUE"):
                    trend_bits.append(f"{label}={text}")
            if trend.get("instrument_broadening_present") is not None:
                trend_bits.append(f"instrument_broadening={bool(trend.get('instrument_broadening_present'))}")
            if waxs_parts:
                bits.append("core=" + ", ".join(waxs_parts[:3]))
            if trend_bits:
                bits.append("trend=" + ", ".join(trend_bits))
            if support_parts:
                bits.append("support=" + " | ".join(support_parts[:6]))
        elif technique == "dsc":
            dsc_parts = []
            for key in ("Tg_C", "Tm_peak_C", "Tcc_peak_C", "DHm_Jg", "DHc_Jg", "DHcc_Jg", "Xc_pct"):
                value = current_metrics.get(key, "")
                if value:
                    dsc_parts.append(f"{key}={value}")
            if dsc_parts:
                bits.append("core=" + ", ".join(dsc_parts[:5]))
            dsc_support = _build_dsc_support_block_text(
                evidence,
                display_text=self._display_text,
                format_score_value=self._format_score_value,
                include_measurement=False,
            )
            if dsc_support and dsc_support != tr("AI_TUNING_EMPTY_VALUE"):
                bits.append(dsc_support)
        elif technique == "ir":
            bits.append(self._ir_support_block_text(evidence))
        else:
            metric_bits = []
            for key in ("r_squared", "quality_score", "L_nm", "Xc_pct", "D_Scherrer_nm"):
                value = current_metrics.get(key, "")
                if value:
                    metric_bits.append(f"{key}={value}")
            if metric_bits:
                bits.append("core=" + ", ".join(metric_bits[:4]))
        validation = str(summary.get("validation_summary") or record.get("validation_summary") or "").strip()
        if validation:
            bits.append(f"validation={validation}")
        constraint_text = self._constraint_summary_text(evidence)
        if constraint_text != tr("AI_TUNING_EMPTY_VALUE"):
            bits.append(constraint_text)
        return " | ".join(bits) if bits else tr("AI_TUNING_EMPTY_VALUE")

    def _evidence_symptom_names(self, analysis_evidence) -> set[str]:
        symptoms = analysis_evidence.get("symptoms", []) if isinstance(analysis_evidence, dict) else []
        names: set[str] = set()
        if not isinstance(symptoms, list):
            return names
        for item in symptoms:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "") or "").strip()
            if name:
                names.add(name)
        return names

    def _batch_fallback_summary_text(self, analysis_evidence):
        if not isinstance(analysis_evidence, dict) or not analysis_evidence:
            return ""
        batch = analysis_evidence.get("batch_evidence", {}) if isinstance(analysis_evidence.get("batch_evidence"), dict) else {}
        structure = analysis_evidence.get("structure_evidence", {}) if isinstance(analysis_evidence.get("structure_evidence"), dict) else {}
        batch_summary = batch.get("batch_calibration_summary") if isinstance(batch.get("batch_calibration_summary"), dict) else {}
        symptoms = self._evidence_symptom_names(analysis_evidence)

        if not batch_summary and "temperature_calibration_fallback_active" not in symptoms:
            return ""

        parts = []
        fallback_ratio = self._coerce_summary_float(batch_summary.get("fallback_ratio"))
        if fallback_ratio is not None and fallback_ratio > 0:
            parts.append(tr("RESULTS_REVIEW_FALLBACK_ACTIVE", f"{fallback_ratio * 100:.0f}"))

        raw_rows = batch_summary.get("raw_snapshot_rows")
        try:
            raw_rows_int = int(raw_rows)
        except (TypeError, ValueError):
            raw_rows_int = 0
        if raw_rows_int > 0:
            parts.append(tr("RESULTS_REVIEW_FALLBACK_RAW", raw_rows_int))

        if "batch_summary_conflicts_with_frame_evidence" in symptoms:
            parts.append(tr("RESULTS_REVIEW_FALLBACK_CONFLICT"))
        if "thickness_chain_unreliable" in symptoms:
            parts.append(tr("RESULTS_REVIEW_FALLBACK_THICKNESS"))

        reason = str(
            batch_summary.get("calibrated_fallback_reason")
            or structure.get("calibrated_fallback_reason")
            or ""
        ).strip()
        if reason:
            parts.append(tr("RESULTS_REVIEW_FALLBACK_REASON", reason))
        skip_reason = str(
            batch_summary.get("calibration_skipped_reason")
            or structure.get("calibration_skipped_reason")
            or ""
        ).strip()
        if skip_reason:
            parts.append(tr("RESULTS_REVIEW_FALLBACK_REASON", skip_reason))

        return " | ".join(part for part in parts if part)

    def _saxs_lc_status_summary_text(self, params, analysis_evidence=None) -> str:
        analysis_evidence = analysis_evidence if isinstance(analysis_evidence, dict) else self._current_analysis_evidence()
        batch_summary = {}
        if isinstance(analysis_evidence, dict):
            batch = analysis_evidence.get("batch_evidence", {}) if isinstance(analysis_evidence.get("batch_evidence"), dict) else {}
            batch_summary = batch.get("batch_structure_summary", {}) if isinstance(batch.get("batch_structure_summary"), dict) else {}
            if not batch_summary:
                structure = analysis_evidence.get("structure_evidence", {}) if isinstance(analysis_evidence.get("structure_evidence"), dict) else {}
                status = str(structure.get("lc_reliability_status") or "").strip()
                if status:
                    batch_summary = {
                        "dominant_lc_reliability_status": status,
                        "dominant_lc_reliability_reason": str(structure.get("lc_reliability_reason") or "").strip() or "",
                        "dominant_melting_window_status": str(structure.get("melting_window_status") or "").strip() or "",
                        "diagnostic_only_rows": 1 if status == "diagnostic_only" else 0,
                        "within_window_rows": 1 if str(structure.get("melting_window_status") or "").strip() == "within_window" else 0,
                    }

        if not batch_summary and isinstance(params, dict):
            batch_summary = params.get("batch_structure_summary", {}) if isinstance(params.get("batch_structure_summary"), dict) else {}

        if not isinstance(batch_summary, dict) or not batch_summary:
            return ""

        diagnostic_rows = batch_summary.get("diagnostic_only_rows")
        within_window_rows = batch_summary.get("within_window_rows")
        status = str(
            batch_summary.get("dominant_lc_reliability_status")
            or (params.get("lc_reliability_status") if isinstance(params, dict) else "")
            or ""
        ).strip()
        reason = str(
            batch_summary.get("dominant_lc_reliability_reason")
            or (params.get("lc_reliability_reason") if isinstance(params, dict) else "")
            or ""
        ).strip()

        try:
            diagnostic_rows_int = int(diagnostic_rows or 0)
        except (TypeError, ValueError):
            diagnostic_rows_int = 0
        try:
            within_window_rows_int = int(within_window_rows or 0)
        except (TypeError, ValueError):
            within_window_rows_int = 0

        if not status and diagnostic_rows_int <= 0 and within_window_rows_int <= 0:
            return ""

        return tr(
            "RESULTS_SUMMARY_RISK_SAXS_LC_STATUS",
            self._saxs_lc_status_text(status) or tr("AI_TUNING_EMPTY_VALUE"),
            diagnostic_rows_int,
            within_window_rows_int,
            reason or tr("AI_TUNING_EMPTY_VALUE"),
        )

    def _saxs_structure_status_snapshot(self, params=None, analysis_evidence=None) -> dict[str, Any]:
        params = params if isinstance(params, dict) else {}
        analysis_evidence = analysis_evidence if isinstance(analysis_evidence, dict) else self._current_analysis_evidence()
        structure = analysis_evidence.get("structure_evidence", {}) if isinstance(analysis_evidence, dict) and isinstance(analysis_evidence.get("structure_evidence"), dict) else {}
        batch = analysis_evidence.get("batch_evidence", {}) if isinstance(analysis_evidence, dict) and isinstance(analysis_evidence.get("batch_evidence"), dict) else {}
        batch_summary = batch.get("batch_structure_summary", {}) if isinstance(batch.get("batch_structure_summary"), dict) else {}
        if not batch_summary and isinstance(params.get("batch_structure_summary"), dict):
            batch_summary = params.get("batch_structure_summary", {})
        symptoms = self._evidence_symptom_names(analysis_evidence)

        def _as_int(value) -> int:
            try:
                return int(value or 0)
            except (TypeError, ValueError):
                return 0

        status = str(
            batch_summary.get("dominant_lc_reliability_status")
            or structure.get("lc_reliability_status")
            or params.get("lc_reliability_status")
            or ""
        ).strip()
        reason = str(
            batch_summary.get("dominant_lc_reliability_reason")
            or structure.get("lc_reliability_reason")
            or params.get("lc_reliability_reason")
            or ""
        ).strip()
        melting_status = str(
            batch_summary.get("dominant_melting_window_status")
            or structure.get("melting_window_status")
            or params.get("melting_window_status")
            or ""
        ).strip()
        melting_reason = str(
            batch_summary.get("dominant_melting_window_reason")
            or structure.get("melting_window_reason")
            or params.get("melting_window_reason")
            or ""
        ).strip()
        batch_rows = _as_int(batch_summary.get("batch_rows") or params.get("batch_frames"))
        diagnostic_rows = _as_int(batch_summary.get("diagnostic_only_rows"))
        low_conf_rows = _as_int(batch_summary.get("low_confidence_rows"))
        usable_rows = _as_int(batch_summary.get("usable_rows"))
        within_window_rows = _as_int(batch_summary.get("within_window_rows"))
        near_onset_rows = _as_int(batch_summary.get("near_onset_rows"))
        post_end_rows = _as_int(batch_summary.get("post_end_rows"))
        if batch_rows <= 0:
            batch_rows = max(
                diagnostic_rows + low_conf_rows + usable_rows,
                within_window_rows + near_onset_rows + post_end_rows,
                1 if any([status, reason, melting_status, melting_reason]) else 0,
            )

        return {
            "batch_rows": batch_rows,
            "lc_reliability_status": status,
            "lc_reliability_reason": reason,
            "melting_window_status": melting_status,
            "melting_window_reason": melting_reason,
            "diagnostic_only_rows": diagnostic_rows,
            "low_confidence_rows": low_conf_rows,
            "usable_rows": usable_rows,
            "within_window_rows": within_window_rows,
            "near_onset_rows": near_onset_rows,
            "post_end_rows": post_end_rows,
            "symptoms": symptoms,
        }

    def _saxs_reason_text(self, reason: Any) -> str:
        text = str(reason or "").strip()
        if not text:
            return ""
        zh = get_language() == "zh"
        mapping = {
            "stable_structure_support": "结构支撑稳定" if zh else "stable structure support",
            "structure_unresolved": "结构未稳定解析" if zh else "structure unresolved",
            "low_lc_confidence": "lc 置信度低" if zh else "low lc confidence",
            "limited_lc_confidence": "lc 置信度有限" if zh else "limited lc confidence",
            "within_melting_window": "位于熔融窗口内" if zh else "within the melting window",
            "near_melting_onset": "接近熔融起点" if zh else "near the melting onset",
            "post_melting_window": "已越过熔融窗口" if zh else "past the melting window",
            "minority_fraction_too_low": "少数相比例过低" if zh else "minority fraction too low",
            "q_invariant_anomaly": "Q* 异常" if zh else "Q* anomaly",
            "frame_analysis_warning": "帧级分析警告" if zh else "frame-level warning",
            "temperature_series_status_unavailable": "温度序列状态不可用" if zh else "temperature-series status unavailable",
            "temperature_unresolved": "温度未解析" if zh else "temperature unresolved",
            "below_sequence_melting_onset": "低于序列熔融起点" if zh else "below the sequence melting onset",
            "near_sequence_melting_onset": "接近序列熔融起点" if zh else "near the sequence melting onset",
            "between_sequence_melting_onset_and_end": "位于序列熔融起点到终点之间" if zh else "between the sequence melting onset and end",
            "between_sequence_melting_onset_and_peak": "位于序列熔融起点到峰值之间" if zh else "between the sequence melting onset and peak",
            "above_sequence_melting_onset_with_unresolved_end": "已高于序列熔融起点但终点未解析" if zh else "above the sequence melting onset with unresolved end",
            "past_sequence_melting_end": "已超过序列熔融终点" if zh else "past the sequence melting end",
            "melting_onset_unresolved": "熔融起点未解析" if zh else "melting onset unresolved",
            "melting_onset_unresolved_peak_only": "仅解析到熔融峰值，起点未定" if zh else "only the melting peak is resolved",
            "above_peak_with_unresolved_end": "已高于峰值但终点未解析" if zh else "above the peak with unresolved end",
        }
        parts = []
        seen = set()
        for token in text.split("|"):
            key = str(token or "").strip()
            if not key:
                continue
            label = mapping.get(key, key.replace("_", " "))
            if label not in seen:
                seen.add(label)
                parts.append(label)
        return ", ".join(parts)

    def _saxs_lc_status_text(self, status: Any) -> str:
        text = str(status or "").strip().lower()
        if not text:
            return ""
        zh = get_language() == "zh"
        mapping = {
            "usable": "可用" if zh else "usable",
            "low_confidence": "低置信" if zh else "low-confidence",
            "diagnostic_only": "仅作诊断" if zh else "diagnostic-only",
        }
        return mapping.get(text, text.replace("_", "-"))

    def _saxs_calibration_method_text(self, method: Any) -> str:
        text = str(method or "").strip().lower()
        if not text:
            return ""
        zh = get_language() == "zh"
        mapping = {
            "raw": "原始" if zh else "raw",
            "calibrated": "已校准" if zh else "calibrated",
            "qstar_calibrated": "已校准" if zh else "calibrated",
        }
        return mapping.get(text, text.replace("_", "-"))

    def _saxs_result_semantic_details(self, params=None, analysis_evidence=None) -> dict[str, str]:
        snapshot = self._saxs_structure_status_snapshot(params, analysis_evidence)
        status = str(snapshot.get("lc_reliability_status") or "").strip().lower()
        melting_status = str(snapshot.get("melting_window_status") or "").strip().lower()
        symptoms = snapshot.get("symptoms", [])
        params = params if isinstance(params, dict) else {}
        batch_rows = int(snapshot.get("batch_rows") or 0)
        diagnostic_rows = int(snapshot.get("diagnostic_only_rows") or 0)
        low_conf_rows = int(snapshot.get("low_confidence_rows") or 0)
        usable_rows = int(snapshot.get("usable_rows") or 0)
        within_window_rows = int(snapshot.get("within_window_rows") or 0)
        near_onset_rows = int(snapshot.get("near_onset_rows") or 0)
        post_end_rows = int(snapshot.get("post_end_rows") or 0)
        reason_text = self._saxs_reason_text(snapshot.get("lc_reliability_reason"))
        melting_reason_text = self._saxs_reason_text(snapshot.get("melting_window_reason"))
        zh = get_language() == "zh"

        details: dict[str, str] = {}

        if status or diagnostic_rows > 0 or low_conf_rows > 0 or usable_rows > 0:
            if status == "diagnostic_only" or diagnostic_rows > 0:
                affected = diagnostic_rows or 1
                if zh:
                    interpretation = f"{affected} 帧 lc 仅适合作诊断，不应直接当作最终层片厚度结果"
                else:
                    interpretation = f"{affected} frame(s) are diagnostic-only for lc, so those thickness values should not be treated as final"
            elif status == "low_confidence" or low_conf_rows > 0:
                affected = low_conf_rows or 1
                if zh:
                    interpretation = f"{affected} 帧 lc 仅适合低置信趋势判断，暂不宜写成稳定结构结论"
                else:
                    interpretation = f"{affected} frame(s) keep only low-confidence lc support, so use them for trend reading rather than a firm structure conclusion"
            else:
                affected = usable_rows or batch_rows or 1
                if zh:
                    interpretation = f"{affected} 帧 lc 具备可用结构支撑"
                else:
                    interpretation = f"{affected} frame(s) keep usable lc support for structure interpretation"
            if reason_text and status != "usable":
                suffix = f"；原因：{reason_text}" if zh else f"; reason: {reason_text}"
                interpretation += suffix
            details["interpretation"] = interpretation
            if status:
                details["status"] = (
                    f"strain status: {self._saxs_lc_status_text(status)}"
                    if not zh
                    else f"strain 状态：{self._saxs_lc_status_text(status)}"
                )
            paper_figure = snapshot.get("paper_figure_candidate")
            paper_candidate = snapshot.get("paper_conclusion_candidate")
            if paper_figure is not None or paper_candidate is not None:
                paper_figure_text = str(bool(paper_figure)).lower() if paper_figure is not None else ""
                paper_candidate_text = str(bool(paper_candidate)).lower() if paper_candidate is not None else ""
                details["candidate"] = (
                    f"paper figure={paper_figure_text}; paper conclusion={paper_candidate_text}"
                    if not zh
                    else f"论文图候选={paper_figure_text}；论文结论候选={paper_candidate_text}"
                )

        if melting_status or within_window_rows > 0 or near_onset_rows > 0 or post_end_rows > 0:
            if melting_status == "near_onset" or near_onset_rows > 0:
                if zh:
                    window_text = "当前序列已接近 SAXS 推导的熔融起点"
                else:
                    window_text = "the current sequence is near the SAXS-derived melting onset"
            elif melting_status == "within_window" or within_window_rows > 0:
                if zh:
                    window_text = "当前序列已有帧进入 SAXS 推导的熔融窗口"
                else:
                    window_text = "the current sequence has frames inside the SAXS-derived melting window"
            elif melting_status == "post_end" or post_end_rows > 0:
                if zh:
                    window_text = "当前序列已有帧越过 SAXS 推导的熔融终点"
                else:
                    window_text = "the current sequence has frames past the SAXS-derived melting end"
            elif melting_status == "outside_window":
                if zh:
                    window_text = "当前主导帧仍在 SAXS 熔融窗口之外"
                else:
                    window_text = "the dominant frames remain outside the SAXS melting window"
            else:
                if zh:
                    window_text = "SAXS 熔融窗口还未稳定解析"
                else:
                    window_text = "the SAXS melting window is not resolved yet"

            count_bits = []
            if near_onset_rows > 0:
                count_bits.append(f"near-onset={near_onset_rows}")
            if within_window_rows > 0:
                count_bits.append(f"within-window={within_window_rows}")
            if post_end_rows > 0:
                count_bits.append(f"post-end={post_end_rows}")
            if count_bits:
                window_text += f" ({', '.join(count_bits)})"
            if melting_reason_text and melting_status in {"", "undetermined"}:
                suffix = f"；依据：{melting_reason_text}" if zh else f"; basis: {melting_reason_text}"
                window_text += suffix
            details["window"] = window_text

        calibration_bits = []
        lc_method = str(params.get("lc_method") or "").strip()
        if lc_method:
            calibration_bits.append(f"lc_method={lc_method}")
        fallback_active = params.get("calibrated_fallback_active")
        if fallback_active is not None:
            calibration_bits.append(f"calibrated_fallback_active={bool(fallback_active)}")
        calibration_reason = str(params.get("calibration_skipped_reason") or "").strip()
        if calibration_reason:
            calibration_bits.append(f"calibration_skipped_reason={calibration_reason}")
        if calibration_bits:
            if zh:
                details["calibration"] = f"校准状态：{'；'.join(calibration_bits)}"
            else:
                details["calibration"] = f"calibration state: {'; '.join(calibration_bits)}"

        if "lc_unreliable_without_melting_proof" in symptoms:
            details["boundary"] = (
                "这还不能判作熔融，当前问题是熔融窗口尚未被证明前，lc 提取已经失稳"
                if zh
                else "do not call this melting yet; the problem is unstable lc extraction before the melting window is proven"
            )
        elif "temperature_sequence_near_melting_window" in symptoms:
            details["boundary"] = (
                "这些帧应按过渡敏感区解读，而不是按普通固态层片继续解释"
                if zh
                else "treat these frames as transition-sensitive rather than as ordinary solid-state lamellar evolution"
            )
        elif "diagnostic_lc_frames_present" in symptoms:
            details["boundary"] = (
                "在 2D 图、峰连续性和温度序列支撑恢复前，不要把这些 lc 当成最终结构参数"
                if zh
                else "do not treat those lc values as final structure parameters before the 2D pattern and sequence support recover"
            )

        return details

    def _saxs_result_semantic_lines(self, params=None, analysis_evidence=None) -> list[str]:
        details = self._saxs_result_semantic_details(params, analysis_evidence)
        lines = []
        interpretation = str(details.get("interpretation") or "").strip()
        if interpretation:
            lines.append(tr("RESULTS_REVIEW_SAXS_INTERPRETATION", interpretation))
        window_text = str(details.get("window") or "").strip()
        if window_text:
            lines.append(tr("RESULTS_REVIEW_SAXS_WINDOW", window_text))
        calibration_text = str(details.get("calibration") or "").strip()
        if calibration_text:
            lines.append(tr("RESULTS_REVIEW_SAXS_CALIBRATION", calibration_text))
        boundary = str(details.get("boundary") or "").strip()
        if boundary:
            lines.append(tr("RESULTS_REVIEW_SAXS_BOUNDARY", boundary))
        return lines

    def _saxs_strain_evidence_snapshot(self, params=None, analysis_evidence=None) -> dict[str, Any]:
        params = params if isinstance(params, dict) else {}
        analysis_evidence = analysis_evidence if isinstance(analysis_evidence, dict) else self._current_analysis_evidence()
        feature = analysis_evidence.get("feature_evidence", {}) if isinstance(analysis_evidence, dict) and isinstance(analysis_evidence.get("feature_evidence"), dict) else {}
        condition = feature.get("condition_evidence", {}) if isinstance(feature.get("condition_evidence"), dict) else {}
        structure = feature.get("strain_structure_evidence", {}) if isinstance(feature.get("strain_structure_evidence"), dict) else {}
        if not condition and isinstance(analysis_evidence.get("condition_evidence"), dict):
            condition = analysis_evidence.get("condition_evidence", {})
        if not condition and isinstance(params.get("condition_evidence"), dict):
            condition = params.get("condition_evidence", {})
        if not structure and isinstance(params.get("strain_structure_evidence"), dict):
            structure = params.get("strain_structure_evidence", {})

        symptoms = self._evidence_symptom_names(analysis_evidence)
        condition_label = str(
            condition.get("condition_label")
            or params.get("condition_label")
            or analysis_evidence.get("condition_label")
            or ""
        ).strip().lower()
        strain_structure_keys = {
            "Q_star_rel_mean",
            "Q_star_rel_span",
            "phi_void_mean",
            "phi_void_span",
            "void_detected_frames",
            "f_Herman_mean",
            "f_Herman_span",
            "porod_slope_mean",
            "porod_slope_span",
        }
        active = bool(
            condition_label == "strain"
            or any(key in structure for key in strain_structure_keys)
            or any(
                symptom in {
                    "low_q_void_dominant",
                    "strain_void_lamellar_conflict",
                    "lamellar_anchor_lost_under_strain",
                    "qstar_rel_without_lamellar_support",
                    "orientation_shift_breaks_lamellar_comparison",
                }
                for symptom in symptoms
            )
        )

        def _as_float(value):
            return self._coerce_summary_float(value)

        return {
            "active": active,
            "condition_label": condition_label,
            "strain_axis_confidence": _as_float(condition.get("strain_axis_confidence", condition.get("condition_confidence"))),
            "strain_monotonic": condition.get("strain_monotonic"),
            "strain_missing_count": condition.get("strain_missing_count"),
            "strain_duplicate_count": condition.get("strain_duplicate_count"),
            "strain_min_pct": _as_float(condition.get("strain_min_pct")),
            "strain_max_pct": _as_float(condition.get("strain_max_pct")),
            "Q_star_rel_mean": _as_float(structure.get("Q_star_rel_mean")),
            "Q_star_rel_span": _as_float(structure.get("Q_star_rel_span")),
            "phi_void_mean": _as_float(structure.get("phi_void_mean")),
            "phi_void_span": _as_float(structure.get("phi_void_span")),
            "void_detected_frames": structure.get("void_detected_frames"),
            "f_Herman_mean": _as_float(structure.get("f_Herman_mean")),
            "f_Herman_span": _as_float(structure.get("f_Herman_span")),
            "porod_slope_mean": _as_float(structure.get("porod_slope_mean")),
            "porod_slope_span": _as_float(structure.get("porod_slope_span")),
            "dominant_phase": str(structure.get("dominant_phase") or "").strip().lower(),
            "strain_reliability_status": str(structure.get("strain_reliability_status") or "").strip().lower(),
            "strain_reliability_reason": str(structure.get("strain_reliability_reason") or "").strip(),
            "paper_figure_candidate": bool(structure.get("paper_figure_candidate")) if structure.get("paper_figure_candidate") is not None else None,
            "paper_conclusion_candidate": bool(structure.get("paper_conclusion_candidate")) if structure.get("paper_conclusion_candidate") is not None else None,
            "paper_conclusion_ready": bool(structure.get("paper_conclusion_ready")) if structure.get("paper_conclusion_ready") is not None else None,
            "phase_support_mean": _as_float(structure.get("phase_support_mean")),
            "phase_support_span": _as_float(structure.get("phase_support_span")),
            "symptoms": symptoms,
        }

    def _saxs_strain_summary_text(self, params=None, analysis_evidence=None) -> str:
        snapshot = self._saxs_strain_evidence_snapshot(params, analysis_evidence)
        if not snapshot.get("active"):
            return ""

        zh = get_language() == "zh"
        axis_bits = []
        axis_conf = snapshot.get("strain_axis_confidence")
        if axis_conf is not None:
            axis_bits.append(f"{'置信度' if zh else 'confidence'}={axis_conf:.2f}")
        monotonic = snapshot.get("strain_monotonic")
        if monotonic is not None:
            if zh:
                axis_bits.append(f"单调={'是' if monotonic else '否'}")
            else:
                axis_bits.append(f"monotonic={'yes' if monotonic else 'no'}")
        for label, key in (
            ("缺失" if zh else "missing", "strain_missing_count"),
            ("重复" if zh else "duplicate", "strain_duplicate_count"),
        ):
            value = snapshot.get(key)
            if value not in (None, "", []):
                axis_bits.append(f"{label}={value}")
        if snapshot.get("strain_min_pct") is not None or snapshot.get("strain_max_pct") is not None:
            low = snapshot.get("strain_min_pct")
            high = snapshot.get("strain_max_pct")
            if low is not None and high is not None:
                axis_bits.append(f"{'范围' if zh else 'range'}={low:.2f}-{high:.2f}%")

        structure_bits = []
        status = snapshot.get("strain_reliability_status")
        if status:
            structure_bits.append(f"{'状态' if zh else 'status'}={status}")
        dominant_phase = snapshot.get("dominant_phase")
        if dominant_phase:
            structure_bits.append(f"{'阶段' if zh else 'phase'}={dominant_phase}")
        q_mean = snapshot.get("Q_star_rel_mean")
        q_span = snapshot.get("Q_star_rel_span")
        if q_mean is not None:
            text = f"Q*_rel={q_mean:.4f}"
            if q_span is not None:
                text += f"±{q_span / 2:.4f}" if q_span is not None else ""
            structure_bits.append(text)
        phi_mean = snapshot.get("phi_void_mean")
        phi_span = snapshot.get("phi_void_span")
        if phi_mean is not None:
            text = f"{'空穴' if zh else 'void'}={phi_mean:.4f}"
            if phi_span is not None:
                text += f" ({'span' if zh else 'span'}={phi_span:.4f})"
            structure_bits.append(text)
        void_frames = snapshot.get("void_detected_frames")
        if void_frames not in (None, ""):
            structure_bits.append(f"{'空穴帧' if zh else 'void frames'}={void_frames}")
        f_mean = snapshot.get("f_Herman_mean")
        f_span = snapshot.get("f_Herman_span")
        if f_mean is not None:
            text = f"f_Herman={f_mean:.4f}"
            if f_span is not None:
                text += f" ({'span' if zh else 'span'}={f_span:.4f})"
            structure_bits.append(text)
        porod_mean = snapshot.get("porod_slope_mean")
        porod_span = snapshot.get("porod_slope_span")
        if porod_mean is not None:
            text = f"Porod={porod_mean:.4f}"
            if porod_span is not None:
                text += f" ({'span' if zh else 'span'}={porod_span:.4f})"
            structure_bits.append(text)
        if snapshot.get("paper_figure_candidate") is not None:
            structure_bits.append(f"{'论文图候选' if zh else 'paper-figure'}={str(bool(snapshot.get('paper_figure_candidate'))).lower()}")
        if snapshot.get("paper_conclusion_candidate") is not None:
            structure_bits.append(f"{'论文结论候选' if zh else 'paper-conclusion'}={str(bool(snapshot.get('paper_conclusion_candidate'))).lower()}")
        if snapshot.get("paper_conclusion_ready") is not None:
            structure_bits.append(f"{'可直接结论' if zh else 'paper-ready'}={str(bool(snapshot.get('paper_conclusion_ready'))).lower()}")

        risk_bits = []
        for symptom in snapshot.get("symptoms", []):
            if symptom == "low_q_void_dominant":
                risk_bits.append("low-q / 空穴主导" if zh else "low-q / void dominant")
            elif symptom == "strain_void_lamellar_conflict":
                risk_bits.append("空穴与层片解释冲突" if zh else "void conflicts with lamellar reading")
            elif symptom == "lamellar_anchor_lost_under_strain":
                risk_bits.append("长周期锚点不稳" if zh else "long-period anchor lost")
            elif symptom == "qstar_rel_without_lamellar_support":
                risk_bits.append("Q*rel 缺少层片支撑" if zh else "Q*rel lacks lamellar support")
            elif symptom == "orientation_shift_breaks_lamellar_comparison":
                risk_bits.append("取向变化干扰比较" if zh else "orientation shift breaks comparison")

        parts = []
        if axis_bits:
            parts.append(("strain轴" if zh else "strain axis") + "=" + ", ".join(str(item) for item in axis_bits[:4]))
        if structure_bits:
            parts.append(("结构" if zh else "structure") + "=" + ", ".join(structure_bits[:4]))
        if risk_bits:
            parts.append(("主要问题" if zh else "main issues") + "=" + ", ".join(risk_bits[:3]))
        return " ; ".join(parts)

    def _saxs_strain_risk_summary_text(self, params=None, analysis_evidence=None) -> str:
        snapshot = self._saxs_strain_evidence_snapshot(params, analysis_evidence)
        if not snapshot.get("active"):
            return ""

        symptoms = set(snapshot.get("symptoms") or [])
        high_risk = bool(
            symptoms.intersection(
                {
                    "low_q_void_dominant",
                    "strain_void_lamellar_conflict",
                    "lamellar_anchor_lost_under_strain",
                    "qstar_rel_without_lamellar_support",
                    "orientation_shift_breaks_lamellar_comparison",
                }
            )
        )
        phi_void = snapshot.get("phi_void_mean")
        q_span = snapshot.get("Q_star_rel_span")
        f_span = snapshot.get("f_Herman_span")
        strain_conf = snapshot.get("strain_axis_confidence")
        status = str(snapshot.get("strain_reliability_status") or "").strip().lower()
        if not high_risk and not (
            (phi_void is not None and phi_void >= 0.02)
            or (q_span is not None and q_span >= 0.015)
            or (f_span is not None and f_span >= 0.20)
            or (strain_conf is not None and strain_conf < 0.75)
            or status in {"low_confidence", "diagnostic_only"}
        ):
            return ""

        if get_language() == "zh":
            return "风险提示 | 拉伸 SAXS 的 low-q / 空穴 / 取向链还没站稳，不要硬把结果抬成稳定结论"
        if status:
            return f"Risk note | tensile SAXS status={status}, so keep the result in diagnostic framing until the chain stabilizes"
        return "Risk note | the tensile SAXS low-q / void / orientation chain is still unstable, so do not force a stable conclusion yet"

    def _saxs_strain_next_step_text(self, params=None, analysis_evidence=None) -> str:
        snapshot = self._saxs_strain_evidence_snapshot(params, analysis_evidence)
        if not snapshot.get("active"):
            return ""
        if get_language() == "zh":
            return "下一步 | 先对齐 strain 轴、low-q 覆盖、空穴证据和长周期锚点，再决定是否继续调参"
        return "Next step | align the strain axis, low-q coverage, void evidence, and long-period anchor before deciding whether to tune again"

    def _measured_result_summary_text(self, record: dict[str, Any] | None = None) -> str:
        record = record if isinstance(record, dict) else self._current_results_record()
        if not isinstance(record, dict) or not record:
            return ""
        summary = record.get("results_summary") if isinstance(record.get("results_summary"), dict) else {}
        if not isinstance(summary, dict):
            summary = {}

        current_metrics = self._history_result_metrics(record)
        metric_parts = []
        technique = str(self._current_technique or "").strip().lower()
        if technique == "dsc":
            for key in ("Tg_C", "Tm_peak_C", "Tcc_peak_C", "DHm_Jg", "DHc_Jg", "DHcc_Jg", "Xc_pct"):
                value = current_metrics.get(key, "")
                if value:
                    metric_parts.append(f"{key}={value}")
        elif technique == "saxs":
            params = record.get("parameters") if isinstance(record.get("parameters"), dict) else {}
            strain_snapshot = self._saxs_strain_evidence_snapshot(
                params,
                record.get("analysis_evidence") if isinstance(record, dict) else {},
            )
            if strain_snapshot.get("active"):
                status = str(strain_snapshot.get("strain_reliability_status") or "").strip()
                if status:
                    metric_parts.append(f"strain_reliability_status={status}")
                dominant_phase = str(strain_snapshot.get("dominant_phase") or "").strip()
                if dominant_phase:
                    metric_parts.append(f"dominant_phase={dominant_phase}")
                if strain_snapshot.get("paper_figure_candidate") is not None:
                    metric_parts.append(f"paper_figure_candidate={str(bool(strain_snapshot.get('paper_figure_candidate'))).lower()}")
                if strain_snapshot.get("paper_conclusion_candidate") is not None:
                    metric_parts.append(f"paper_conclusion_candidate={str(bool(strain_snapshot.get('paper_conclusion_candidate'))).lower()}")
                for key in ("Q_star_rel_mean", "phi_void_mean", "f_Herman_mean", "porod_slope_mean", "void_detected_frames"):
                    value = current_metrics.get(key, "")
                    if value:
                        metric_parts.append(f"{key}={value}")
            else:
                lc_method = str(params.get("lc_method") or current_metrics.get("lc_method") or "").strip()
                if lc_method:
                    metric_parts.append(f"lc_method={lc_method}")
                skip_reason = str(params.get("calibration_skipped_reason") or current_metrics.get("calibration_skipped_reason") or "").strip()
                if skip_reason:
                    metric_parts.append(f"calibration_skipped_reason={skip_reason}")
                fallback_active = params.get("calibrated_fallback_active")
                if fallback_active is not None:
                    metric_parts.append(f"calibrated_fallback_active={bool(fallback_active)}")
                for key in ("lc_nm", "lc_reliability_status", "melting_window_status", "Tm_onset_C", "Tm_peak_C", "Tm_end_C"):
                    value = current_metrics.get(key, "")
                    if value:
                        metric_parts.append(f"{key}={value}")
        else:
            for key in ("r_squared", "L_nm", "Xc_pct", "Tm_peak_C", "Tc_peak_C", "quality_score"):
                value = current_metrics.get(key, "")
                if value:
                    metric_parts.append(f"{key}={value}")

        label = self._current_result_label_for_confirmation()
        parts = [part for part in [label, ", ".join(metric_parts[:4])] if part]
        if summary.get("result_origin") == "controlled_optimization_rerun" or bool(summary.get("ai_tuned")):
            parts.insert(0, tr("RESULT_ORIGIN_AI_TUNED"))
        elif get_language() == "zh":
            parts.insert(0, "原始结果")
        else:
            parts.insert(0, "Measured result")
        return " | ".join(part for part in parts if part)

    def _fallback_evidence_summary_text(self, analysis_evidence) -> str:
        fallback_text = self._batch_fallback_summary_text(analysis_evidence)
        if not fallback_text:
            return ""
        return tr("RESULTS_REVIEW_FALLBACK", fallback_text)

    def _has_condition_axis_risk(self, params, analysis_evidence=None) -> bool:
        if isinstance(analysis_evidence, dict) and analysis_evidence:
            symptoms = self._evidence_symptom_names(analysis_evidence)
            if "condition_axis_missing" in symptoms or "condition_axis_unstable" in symptoms:
                return True
            condition = analysis_evidence.get("condition_evidence", {}) if isinstance(analysis_evidence.get("condition_evidence"), dict) else {}
            missing_frames = condition.get("condition_missing_frames")
            continuity = self._coerce_summary_float(condition.get("condition_continuity_score"))
            confidence = self._coerce_summary_float(condition.get("condition_confidence"))
            try:
                if int(missing_frames or 0) > 0:
                    return True
            except (TypeError, ValueError):
                pass
            if continuity is not None and continuity < 0.85:
                return True
            if confidence is not None and confidence < 0.75:
                return True

        if not isinstance(params, dict):
            return False
        batch_frames = 0
        try:
            batch_frames = int(params.get("batch_frames", 0) or 0)
        except Exception:
            batch_frames = 0
        if batch_frames <= 1:
            return False
        missing_frames = params.get("condition_missing_frames")
        continuity = self._coerce_summary_float(params.get("condition_continuity_score"))
        confidence = self._coerce_summary_float(params.get("condition_confidence"))
        try:
            if int(missing_frames or 0) > 0:
                return True
        except (TypeError, ValueError):
            pass
        if continuity is not None and continuity < 0.85:
            return True
        if confidence is not None and confidence < 0.75:
            return True
        return False

    def _has_fallback_conflict_risk(self, analysis_evidence=None) -> bool:
        if not isinstance(analysis_evidence, dict) or not analysis_evidence:
            return False
        symptoms = self._evidence_symptom_names(analysis_evidence)
        return bool(
            "temperature_calibration_fallback_active" in symptoms
            and (
                "batch_summary_conflicts_with_frame_evidence" in symptoms
                or "thickness_chain_unreliable" in symptoms
            )
        )


    def _results_compare_candidates(self, *, create_db=True) -> list:

        current = self._current_results_record()
        if not current:
            return []
        summary = current.get("results_summary") if isinstance(current.get("results_summary"), dict) else {}
        sample_name = str(summary.get("project_label") or self._infer_sample_name() or "").strip().lower()
        current_technique = str(current.get("technique") or "").strip().lower()
        current_submodule = str(current.get("submodule") or "").strip().lower()
        db = self._ensure_sample_db() if create_db else getattr(self, "_sample_db", None)
        if db is None:
            return []
        try:
            def _created_score_text(value) -> float:
                text = str(value or "").replace("T", " ").strip()
                if not text:
                    return 0.0
                for pattern in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
                    try:
                        return datetime.strptime(text, pattern).timestamp()
                    except ValueError:
                        continue
                try:
                    return datetime.fromisoformat(text).timestamp()
                except ValueError:
                    return 0.0

            scored = []
            for sample in db.list_samples(limit=100):
                sample_score = 2
                candidate_name = str(sample.get("polymer_name") or "").strip().lower()
                if sample_name and candidate_name == sample_name:
                    sample_score = 0
                elif sample_name:
                    continue
                for batch in db.get_batches(sample.get("id", "")):
                    batch_score = 1 if sample_score == 0 else 2
                    for run in db.get_analysis_runs(batch.get("id", "")):
                        if str(run.get("technique") or "").strip().lower() != current_technique:
                            continue
                        if str(run.get("id") or "") == "current":
                            continue
                        run_submodule = str(run.get("submodule") or "").strip().lower()
                        if current_submodule and run_submodule not in {current_submodule, ""}:
                            continue
                        submodule_score = 0 if current_submodule and run_submodule == current_submodule else 1
                        scored.append((sample_score, batch_score, submodule_score, -_created_score_text(run.get("created_at")), run))
            if not scored:
                for sample in db.list_samples(limit=100):
                    for batch in db.get_batches(sample.get("id", "")):
                        for run in db.get_analysis_runs(batch.get("id", "")):
                            if str(run.get("technique") or "").strip().lower() != current_technique:
                                continue
                            run_submodule = str(run.get("submodule") or "").strip().lower()
                            if current_submodule and run_submodule not in {current_submodule, ""}:
                                continue
                            scored.append((3, 3, 1 if current_submodule and run_submodule == current_submodule else 2, -_created_score_text(run.get("created_at")), run))
            scored.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
            return [item[4] for item in scored]
        except Exception:
            logger.warning("Failed to collect result comparison candidates.", exc_info=True)
            return []


    def _results_compare_candidate_id(self, record) -> str:

        if not isinstance(record, dict):
            return ""
        return str(record.get("id") or "").strip()


    def _results_compare_candidate_label(self, record, index=None) -> str:

        label = self._result_comparison_record_label(record)
        if not label:
            label = tr("RESULTS_COMPARE_EMPTY")
        if index is None:
            return label
        return f"{int(index) + 1}. {label}"


    def _results_compare_selected_candidate_id(self) -> str:

        return str(getattr(self, "_results_compare_selected_run_id", "") or "").strip()


    def _current_result_comparison_baseline(self, candidates=None):

        if candidates is None:
            candidates = self._results_compare_candidates()
        candidates = list(candidates or [])
        if not candidates:
            return None
        selected_id = self._results_compare_selected_candidate_id()
        if selected_id:
            for candidate in candidates:
                if self._results_compare_candidate_id(candidate) == selected_id:
                    return candidate
        return candidates[0]


    def _on_results_compare_candidate_changed(self, index: int):

        combo = getattr(self, "_results_compare_selector", None)
        if combo is None:
            return
        if index < 0 or index >= combo.count():
            selected_id = ""
        else:
            selected_id = str(combo.itemData(index) or "").strip()
        if selected_id == self._results_compare_selected_candidate_id():
            return
        self._results_compare_selected_run_id = selected_id
        self._update_results_compare_panel()


    def _result_comparison_record_label(self, record) -> str:

        if not isinstance(record, dict):
            return ""
        summary = record.get("results_summary") if isinstance(record.get("results_summary"), dict) else {}
        origin = self._history_result_origin_label(record)
        context = self._history_record_context_text(record)
        created = self._format_history_timestamp(record.get("created_at"))
        sample = str(summary.get("project_label") or "").strip()
        parts = [part for part in [sample, context, created, origin] if part]
        return " | ".join(parts)


    def _update_results_compare_panel(self):

        current = self._current_results_record()
        if not current:
            self._results_compare_selected_run_id = ""
            if hasattr(self, "_results_compare_selector"):
                self._results_compare_selector.blockSignals(True)
                self._results_compare_selector.clear()
                self._results_compare_selector.setEnabled(False)
                self._results_compare_selector.blockSignals(False)
            if hasattr(self, "_results_compare_group"):
                self._results_compare_group.setVisible(False)
            return

        candidates = self._results_compare_candidates()
        baseline = self._current_result_comparison_baseline(candidates)
        selected_id = self._results_compare_candidate_id(baseline)
        candidate_ids = [self._results_compare_candidate_id(candidate) for candidate in candidates]
        if selected_id and selected_id not in candidate_ids:
            selected_id = candidate_ids[0] if candidate_ids else ""
        if not selected_id and candidate_ids:
            selected_id = candidate_ids[0]
        if selected_id:
            self._results_compare_selected_run_id = selected_id

        if hasattr(self, "_results_compare_selector"):
            selector = self._results_compare_selector
            selector.blockSignals(True)
            selector.clear()
            if candidates:
                for index, candidate in enumerate(candidates):
                    candidate_id = self._results_compare_candidate_id(candidate)
                    candidate_label = self._results_compare_candidate_label(candidate, index)
                    selector.addItem(candidate_label, candidate_id)
                    selector.setItemData(index, candidate_label, Qt.ToolTipRole)
                idx = selector.findData(self._results_compare_selected_candidate_id())
                if idx < 0:
                    idx = 0
                selector.setCurrentIndex(idx)
                self._results_compare_selected_run_id = str(selector.currentData() or "").strip()
                selector.setEnabled(True)
                selector.setToolTip(tr("RESULTS_COMPARE_SELECT_TOOLTIP"))
            else:
                selector.addItem(tr("RESULTS_COMPARE_EMPTY"), "")
                selector.setCurrentIndex(0)
                selector.setEnabled(False)
                selector.setToolTip(tr("RESULTS_COMPARE_EMPTY"))
                self._results_compare_selected_run_id = ""
            selector.blockSignals(False)

        current_label = self._result_comparison_record_label(current) or tr("RESULTS_COMPARE_CURRENT")
        baseline_label = self._result_comparison_record_label(baseline) if baseline else tr("RESULTS_COMPARE_EMPTY")
        joint_context = self._joint_ai_context()
        joint_reminder = self._joint_ai_reminder_text(joint_context)
        joint_compare_hint = self._joint_compare_hint_text(joint_context)

        if hasattr(self, "_results_compare_group"):
            self._results_compare_group.setTitle(tr("GROUP_RESULTS_COMPARE"))
        if hasattr(self, "_results_compare_desc"):
            self._results_compare_desc.setText(tr("RESULTS_COMPARE_DESC"))
        if hasattr(self, "_results_compare_selector_label"):
            self._results_compare_selector_label.setText(tr("RESULTS_COMPARE_SELECT"))
        if hasattr(self, "_results_compare_current"):
            self._results_compare_current.setText(tr("RESULTS_COMPARE_CURRENT") + f": {current_label}")
            self._results_compare_current.setToolTip(tr("RESULTS_COMPARE_CURRENT_TOOLTIP"))
        if hasattr(self, "_results_compare_baseline"):
            self._results_compare_baseline.setText(tr("RESULTS_COMPARE_BASELINE") + f": {baseline_label}")
            self._results_compare_baseline.setToolTip(baseline_label)
        if hasattr(self, "_results_compare_hint"):
            hint_parts = [tr("RESULTS_COMPARE_HINT")]
            if joint_reminder:
                hint_parts.append(joint_reminder)
            if joint_compare_hint:
                hint_parts.append(joint_compare_hint)
            self._results_compare_hint.setText("\n".join(part for part in hint_parts if part))
        if hasattr(self, "_results_compare_joint_btn"):
            has_joint_focus = bool(joint_compare_hint)
            self._results_compare_joint_btn.setVisible(has_joint_focus)
            self._results_compare_joint_btn.setEnabled(has_joint_focus)
            self._results_compare_joint_btn.setText(tr("RESULTS_COMPARE_JOINT"))
            self._results_compare_joint_btn.setToolTip(joint_compare_hint or (tr("RESULTS_COMPARE_JOINT_TOOLTIP") if has_joint_focus else ""))
        if hasattr(self, "_results_compare_open_btn"):
            self._results_compare_open_btn.setEnabled(baseline is not None)
            self._results_compare_open_btn.setToolTip(
                tr("RESULTS_COMPARE_OPEN_TOOLTIP") if baseline is not None else tr("HISTORY_TOOLTIP_COMPARE_UNAVAILABLE")
            )
            self._results_compare_open_btn.setText(tr("RESULTS_COMPARE_OPEN"))
        if hasattr(self, "_results_compare_group"):
            self._results_compare_group.setVisible(True if baseline or current else False)

        self._update_results_confirm_panel()
        self._update_results_review_panel()


    def _is_current_result_confirmed(self) -> bool:
        current = self._current_results_record()
        if not current:
            return False
        if bool(current.get("confirmed")):
            return True
        summary = current.get("results_summary") if isinstance(current.get("results_summary"), dict) else {}
        return bool(summary.get("confirmed"))


    def _update_results_confirm_panel(self):

        current = self._current_results_record()
        has_current = bool(current)
        confirmed = self._is_current_result_confirmed()
        if hasattr(self, "_results_confirm_group"):
            self._results_confirm_group.setTitle(tr("RESULTS_CONFIRM_GROUP"))
            self._results_confirm_group.setVisible(has_current)
        if hasattr(self, "_results_confirm_desc"):
            self._results_confirm_desc.setText(tr("RESULTS_CONFIRM_DESC"))
        if hasattr(self, "_results_confirm_status"):
            self._results_confirm_status.setText(
                tr("RESULTS_CONFIRM_STATUS_CONFIRMED") if confirmed else tr("RESULTS_CONFIRM_STATUS_PENDING")
            )
        if hasattr(self, "_results_confirm_btn"):
            self._results_confirm_btn.setText(tr("RESULTS_CONFIRM_CLEAR") if confirmed else tr("RESULTS_CONFIRM_MARK"))
            self._results_confirm_btn.setToolTip(
                tr("RESULTS_CONFIRM_TOOLTIP_CLEAR") if confirmed else tr("RESULTS_CONFIRM_TOOLTIP_SET")
            )
            self._results_confirm_btn.setEnabled(has_current)
        self._update_results_review_panel()


    def _results_confirm_state_text(self) -> str:
        return tr("RESULTS_CONFIRM_STATUS_CONFIRMED") if self._is_current_result_confirmed() else tr("RESULTS_CONFIRM_STATUS_PENDING")


    def _history_confirmation_label(self, record) -> str:

        confirmed = False
        if isinstance(record, dict):
            confirmed = bool(record.get("confirmed"))
            summary = record.get("results_summary") if isinstance(record.get("results_summary"), dict) else {}
            if isinstance(summary, dict):
                confirmed = confirmed or bool(summary.get("confirmed"))
        return tr("RESULTS_CONFIRM_STATUS_CONFIRMED") if confirmed else tr("RESULTS_CONFIRM_STATUS_PENDING")


    def _toggle_current_result_confirmation(self):

        current = self._current_results_record()
        if not current:
            self.log(tr("RESULTS_COMPARE_EMPTY"))
            return
        current_id = str(current.get("id") or "").strip()
        if not current_id or current_id == "current":
            self._current_result_confirmed_flag = not bool(getattr(self, "_current_result_confirmed_flag", False))
            self._update_results_confirm_panel()
            self._update_work_memory_panel()
            self.log(
                tr("LOG_HISTORY_CONFIRM_SET", self._current_result_label_for_confirmation())
                if self._current_result_confirmed_flag
                else tr("LOG_HISTORY_CONFIRM_CLEARED", self._current_result_label_for_confirmation())
            )
            return

        db = self._ensure_sample_db()
        try:
            next_state = not self._is_current_result_confirmed()
            db.update_analysis_confirmation(current_id, confirmed=next_state)
            self._current_result_confirmed_flag = next_state
            self._refresh_history()
            self._update_results_confirm_panel()
            self._update_work_memory_panel()
            self.log(
                tr("LOG_HISTORY_CONFIRM_SET", self._current_result_label_for_confirmation())
                if next_state
                else tr("LOG_HISTORY_CONFIRM_CLEARED", self._current_result_label_for_confirmation())
            )
        except Exception:
            logger.warning("Failed to toggle current result confirmation.", exc_info=True)


    def _on_history_confirm_requested(self):

        record = self._selected_history_record()
        if record is None:
            self.log(tr("LOG_HISTORY_SELECT_RUN"))
            return

        run_id = str(record.get("id") or "").strip()
        if not run_id:
            self.log(tr("LOG_HISTORY_SELECT_RUN"))
            return

        db = self._ensure_sample_db()
        try:
            next_state = not bool(record.get("confirmed") or (isinstance(record.get("results_summary"), dict) and record["results_summary"].get("confirmed")))
            db.update_analysis_confirmation(run_id, confirmed=next_state)
            self._refresh_history()
            self._update_results_confirm_panel()
            self._update_work_memory_panel()
            label = self._history_record_context_text(record) or self._history_technique_text(str(record.get("technique") or ""))
            self.log(tr("LOG_HISTORY_CONFIRM_SET", label) if next_state else tr("LOG_HISTORY_CONFIRM_CLEARED", label))
        except Exception:
            logger.warning("Failed to toggle history confirmation.", exc_info=True)


    def _current_result_label_for_confirmation(self) -> str:
        summary = self._current_results_record().get("results_summary") if self._current_results_record() else {}
        if isinstance(summary, dict):
            label = str(summary.get("project_label") or "").strip()
            if label:
                return label
        return self._infer_sample_name() or self._history_technique_text(str(self._current_technique or ""))


    def _open_current_result_comparison(self):

        current = self._current_results_record()
        if not current:
            self.log(tr("RESULTS_COMPARE_EMPTY"))
            return
        baseline = self._current_result_comparison_baseline()
        if baseline is None:
            self.log(tr("RESULTS_COMPARE_EMPTY"))
            return
        self._show_history_comparison(current, baseline)


    def _set_results_summary(self, text="", risk_text="", next_text=""):

        summary = str(text or "")
        risk = str(risk_text or "")
        next_step = str(next_text or "")

        if hasattr(self, "_results_summary_group"):
            self._results_summary_label.setText(summary)
            self._results_summary_label.setVisible(bool(summary))
            self._results_summary_risk_label.setText(risk)
            self._results_summary_risk_label.setVisible(bool(risk))
            self._results_summary_next_label.setText(next_step)
            self._results_summary_next_label.setVisible(bool(next_step))
            self._results_summary_group.setVisible(bool(summary or risk or next_step))
        elif hasattr(self, "_results_summary_label"):
            self._results_summary_label.setText(summary)
            self._results_summary_label.setVisible(bool(summary))
        self._update_results_review_panel()


    def _update_results_review_panel(self):

        current = self._current_results_record()
        has_current = bool(current)
        if not hasattr(self, "_results_review_group"):
            return
        if not has_current:
            self._results_review_group.setVisible(False)
            return

        summary = current.get("results_summary") if isinstance(current.get("results_summary"), dict) else {}
        history_context = self._current_result_history_context(current)
        current_origin_label = self._current_result_origin_label()
        is_controlled_rerun = self._current_result_origin() == "controlled_optimization_rerun"
        current_confirmed = tr("RESULTS_REVIEW_CONFIRMED") if self._is_current_result_confirmed() else tr("RESULTS_REVIEW_PENDING")
        validation_summary = str(
            summary.get("validation_summary")
            or current.get("validation_summary")
            or ""
        ).strip()
        if not validation_summary and hasattr(self, "_results_summary_risk_label"):
            validation_summary = str(self._results_summary_risk_label.text() or "").strip()
        risk_text = validation_summary or tr("RESULTS_REVIEW_NO_RISK")
        if is_controlled_rerun and isinstance(history_context, dict) and history_context:
            risk_bits = []
            stop_reason = str(history_context.get("stop_reason") or "").strip()
            remaining_risks = str(history_context.get("remaining_risks") or "").strip()
            if stop_reason:
                risk_bits.append(stop_reason)
            if remaining_risks:
                risk_bits.append(remaining_risks)
            if risk_bits:
                risk_text = " | ".join([risk_text] + risk_bits if risk_text != tr("RESULTS_REVIEW_NO_RISK") else risk_bits)
        benchmark_text = ""
        tuning_context = self._current_result_tuning_context(current)
        if is_controlled_rerun:
            if isinstance(tuning_context, dict) and tuning_context:
                benchmark_text = str(tuning_context.get("benchmark_text") or "").strip()
                if not benchmark_text and str(tuning_context.get("summary") or "").strip():
                    benchmark_text = str(tuning_context.get("summary") or "").strip()
            if not benchmark_text and isinstance(history_context, dict) and history_context:
                benchmark_text = str(history_context.get("benchmark_text") or "").strip()
                if not benchmark_text:
                    benchmark_summary = history_context.get("benchmark_summary") if isinstance(history_context.get("benchmark_summary"), dict) else {}
                    if isinstance(benchmark_summary, dict) and benchmark_summary:
                        benchmark_text = self._benchmark_summary_text(benchmark_summary)
            if not benchmark_text:
                benchmark_text = tr("RESULTS_REVIEW_NO_BENCHMARK")
        chain_text = self._ai_tuning_chain_summary(tuning_context) if is_controlled_rerun and isinstance(tuning_context, dict) and tuning_context else ""
        joint_context = self._joint_ai_context()
        joint_summary = ""
        if isinstance(joint_context, dict) and joint_context:
            joint_summary = str(joint_context.get("summary") or "").strip()
        joint_reminder = self._joint_ai_reminder_text(joint_context)
        joint_compare_hint = self._joint_compare_hint_text(joint_context)
        next_step = ""
        if is_controlled_rerun:
            if isinstance(tuning_context, dict) and tuning_context:
                next_step = str(tuning_context.get("next_goal") or "").strip()
            if not next_step and isinstance(history_context, dict) and history_context:
                next_step = str(history_context.get("next_goal") or "").strip()
        if hasattr(self, "_results_summary_next_label"):
            fallback_next_step = str(self._results_summary_next_label.text() or "").strip()
            if not next_step:
                next_step = fallback_next_step
        if not next_step:
            next_step = tr("RESULTS_REVIEW_NO_NEXT")
        analysis_evidence = self._current_analysis_evidence()
        fallback_text = self._batch_fallback_summary_text(analysis_evidence)

        current_label = self._current_result_label_for_confirmation()
        measured_text = self._measured_result_summary_text(current)
        tuning_goal_text = ""
        if is_controlled_rerun:
            if isinstance(tuning_context, dict) and tuning_context:
                tuning_goal_text = str(tuning_context.get("tuning_goal_label") or "").strip()
                if not tuning_goal_text:
                    tuning_goal_text = self._ai_tuning_goal_label(str(tuning_context.get("tuning_goal") or "").strip())
            if not tuning_goal_text and isinstance(history_context, dict) and history_context:
                tuning_goal_text = str(history_context.get("tuning_goal_label") or "").strip()
                if not tuning_goal_text:
                    tuning_goal_text = self._ai_tuning_goal_label(str(history_context.get("tuning_goal") or "").strip())
        meta_parts = [part for part in [current_label, current_origin_label, current_confirmed] if part]
        if tuning_goal_text:
            meta_parts.append(tr("RESULTS_REVIEW_TUNING_GOAL", tuning_goal_text))
        if hasattr(self, "_results_review_meta"):
            self._results_review_meta.setText(" | ".join(meta_parts))
            self._results_review_meta.setVisible(bool(meta_parts))
        if hasattr(self, "_results_review_benchmark"):
            benchmark_parts = [tr("RESULTS_REVIEW_BENCHMARK", measured_text or current_label)]
            if benchmark_text:
                benchmark_parts.append(benchmark_text)
            elif is_controlled_rerun:
                benchmark_parts.append(tr("RESULTS_REVIEW_NO_BENCHMARK"))
            self._results_review_benchmark.setText(" | ".join(part for part in benchmark_parts if part))
            self._results_review_benchmark.setVisible(bool(benchmark_parts))
        if hasattr(self, "_results_review_chain"):
            self._results_review_chain.setText(tr("RESULTS_REVIEW_CHAIN", chain_text))
            self._results_review_chain.setVisible(bool(chain_text))
        if hasattr(self, "_results_review_trend"):
            trend_text = ""
            trend_label = ""
            if self._current_technique == "waxs":
                trend_text = self._waxs_temperature_trend_text(analysis_evidence)
                trend_label = tr("RESULTS_REVIEW_WAXS_TREND", trend_text)
            elif self._current_technique == "saxs":
                params = current.get("parameters") if isinstance(current.get("parameters"), dict) else {}
                saxs_details = self._saxs_result_semantic_details(params, analysis_evidence)
                trend_text = " | ".join(
                    str(part).strip()
                    for part in (
                        saxs_details.get("interpretation"),
                        saxs_details.get("window"),
                        saxs_details.get("calibration"),
                        saxs_details.get("boundary"),
                    )
                    if part is not None and str(part).strip()
                )
                trend_label = tr("RESULTS_REVIEW_SAXS_STATUS", trend_text) if trend_text else ""
            self._results_review_trend.setText(trend_label)
            self._results_review_trend.setVisible(bool(trend_text))
        boundary_text = self._responsibility_boundary_summary() if is_controlled_rerun else ""
        fallback_block = self._fallback_evidence_summary_text(analysis_evidence)
        if fallback_block:
            boundary_text = " | ".join(part for part in [boundary_text, fallback_block] if part)
        if hasattr(self, "_results_review_boundary"):
            self._results_review_boundary.setText(boundary_text)
            self._results_review_boundary.setVisible(bool(boundary_text))
        if hasattr(self, "_results_review_joint"):
            joint_parts = [part for part in [joint_summary, joint_reminder, joint_compare_hint] if part]
            if joint_parts:
                self._results_review_joint.setText(tr("RESULTS_REVIEW_JOINT", " | ".join(joint_parts)))
                self._results_review_joint.setVisible(True)
            else:
                self._results_review_joint.setText(tr("RESULTS_REVIEW_NO_JOINT"))
                self._results_review_joint.setVisible(False)
        if hasattr(self, "_results_review_risk"):
            self._results_review_risk.setText(tr("RESULTS_REVIEW_RISK", risk_text))
            self._results_review_risk.setVisible(bool(risk_text))
        if hasattr(self, "_results_review_next"):
            self._results_review_next.setText(tr("RESULTS_REVIEW_NEXT", next_step))
            self._results_review_next.setVisible(bool(next_step))
        if hasattr(self, "_results_review_title"):
            title = tr("RESULTS_REVIEW_TITLE")
            if current_confirmed == tr("RESULTS_REVIEW_CONFIRMED"):
                title = tr("RESULTS_REVIEW_TITLE_CONFIRMED")
            self._results_review_title.setText(title)
        self._results_review_group.setVisible(True)


    def _set_results_default_order_control_visible(self, visible):

        if hasattr(self, "_btn_results_default_order"):
            self._btn_results_default_order.setVisible(bool(visible))
            self._btn_results_default_order.setEnabled(bool(visible))


    def _set_results_copy_control_visible(self, visible):

        if hasattr(self, "_btn_results_copy"):
            self._btn_results_copy.setVisible(bool(visible))
            self._btn_results_copy.setEnabled(bool(visible))


    def _set_results_export_control_visible(self, visible):

        if hasattr(self, "_btn_results_export"):
            self._btn_results_export.setVisible(bool(visible))
            self._btn_results_export.setEnabled(bool(visible))


    def _store_results_table_default_order(self, cols, rows, sortable=True):

        self._results_table_default_order = {
            "cols": [str(col) for col in cols],
            "rows": [[("" if value is None else str(value)) for value in row] for row in rows],
            "sortable": bool(sortable),
        }
        self._set_results_default_order_control_visible(sortable)


    def _clear_results_table_default_order(self):

        self._results_table_default_order = None
        self._set_results_default_order_control_visible(False)


    def _restore_results_table_default_order(self):

        snapshot = getattr(self, "_results_table_default_order", None)
        if not isinstance(snapshot, dict):
            return

        cols = snapshot.get("cols") or []
        rows = snapshot.get("rows") or []
        sortable = bool(snapshot.get("sortable"))

        self._results_table.setSortingEnabled(False)
        self._results_table.setRowCount(len(rows))
        self._results_table.setColumnCount(len(cols))
        self._results_table.setHorizontalHeaderLabels(cols)
        for row_index, row_values in enumerate(rows):
            for col_index, value in enumerate(row_values):
                self._set_results_item(row_index, col_index, value)
        self._apply_results_table_layout()
        self._results_table.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)
        self._results_table.setSortingEnabled(sortable)


    def _copy_results_table_to_clipboard(self):

        table = self._results_table
        cols = table.columnCount()
        rows = table.rowCount()
        if cols <= 0 or rows <= 0:
            return

        headers = []
        for col in range(cols):
            header_item = table.horizontalHeaderItem(col)
            headers.append(header_item.text() if header_item is not None else "")

        lines = ["\t".join(headers)]
        selection = table.selectionModel()
        selected_rows = []
        if selection is not None:
            selected_rows = sorted(index.row() for index in selection.selectedRows())
        row_indexes = selected_rows if selected_rows else list(range(rows))

        for row in row_indexes:
            values = []
            for col in range(cols):
                item = table.item(row, col)
                values.append(item.text() if item is not None else "")
            lines.append("\t".join(values))

        QApplication.clipboard().setText("\n".join(lines))
        self.log(tr("LOG_RESULTS_TABLE_COPIED", len(row_indexes), cols))


    def _results_table_text_matrix(self):

        table = self._results_table
        cols = table.columnCount()
        rows = table.rowCount()
        if cols <= 0 or rows <= 0:
            return [], []

        headers = []
        for col in range(cols):
            header_item = table.horizontalHeaderItem(col)
            headers.append(header_item.text() if header_item is not None else "")

        selection = table.selectionModel()
        selected_rows = []
        if selection is not None:
            selected_rows = sorted(index.row() for index in selection.selectedRows())
        row_indexes = selected_rows if selected_rows else list(range(rows))

        matrix = []
        for row in row_indexes:
            values = []
            for col in range(cols):
                item = table.item(row, col)
                values.append(item.text() if item is not None else "")
            matrix.append(values)
        return headers, matrix


    def _export_results_table(self):

        headers, matrix = self._results_table_text_matrix()
        if not headers or not matrix:
            return

        default_name = "results_table.tsv"
        start_dir = self._output_dir or self._get_last_dir()
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            tr("RESULTS_EXPORT_TABLE_TITLE"),
            os.path.join(start_dir, default_name),
            tr("RESULTS_EXPORT_TABLE_FILTER"),
        )
        if not path:
            return

        delimiter = "\t"
        lower_path = path.lower()
        if lower_path.endswith(".csv") or "csv" in str(selected_filter).lower():
            delimiter = ","
            if not lower_path.endswith(".csv"):
                path = f"{path}.csv"
        elif not lower_path.endswith(".tsv"):
            path = f"{path}.tsv"

        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh, delimiter=delimiter)
            writer.writerow(headers)
            writer.writerows(matrix)

        self._save_last_dir(os.path.dirname(path) or start_dir)
        self.log(tr("LOG_RESULTS_TABLE_EXPORTED", len(matrix), len(headers), path))


    def _series_scope_summary_text(self, frame_count):

        try:
            frame_count = int(frame_count)
        except Exception:
            frame_count = 0
        if frame_count <= 0:
            return ""
        if frame_count == 1:
            return tr("RESULTS_SUMMARY_SCOPE_SINGLE_SAMPLE_FRAME")
        return tr("RESULTS_SUMMARY_SCOPE_SINGLE_SAMPLE_FRAMES", frame_count)


    def _frame_results_summary_text(self, frame_count):

        mode = str(getattr(self, "_current_input_mode", "") or "").strip().lower()
        source_name = os.path.basename(str(self._current_filepath or "").rstrip("/\\")) or str(self._current_filepath or "")
        scope_text = self._series_scope_summary_text(frame_count)
        if mode == "sequence":
            return tr("RESULTS_SUMMARY_SEQUENCE", scope_text, source_name)
        return tr("RESULTS_SUMMARY_DIRECTORY", scope_text, source_name)

    def _batch_results_summary_text(self, file_count):

        source_name = os.path.basename(str(self._current_filepath or "").rstrip("/\\")) or str(self._current_filepath or "")
        return tr("RESULTS_SUMMARY_BATCH", file_count, source_name)


    def _single_results_summary_text(self, params):

        metric_count = 0
        if isinstance(params, dict):
            metric_count = len(self._flatten_params(params))
        source_name = os.path.basename(str(self._current_filepath or "").rstrip("/\\")) or str(self._current_filepath or "")
        if self._current_result_origin() == "controlled_optimization_rerun":
            if source_name:
                return tr("RESULTS_SUMMARY_SINGLE_AI_TUNED", metric_count, source_name)
            return tr("RESULTS_SUMMARY_SINGLE_AI_TUNED_NO_SOURCE", metric_count)
        if source_name:
            return tr("RESULTS_SUMMARY_SINGLE", metric_count, source_name)
        return tr("RESULTS_SUMMARY_SINGLE_NO_SOURCE", metric_count)


    def _results_risk_summary_text(self, params, result=None):

        technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
        validation_summary = ""
        validation_warnings = []
        quality_flags = {}
        if result is not None:
            validation_summary = str(getattr(result, "validation_summary", "") or "").strip()
            validation_warnings = list(getattr(result, "validation_warnings", []) or [])
            quality_flags = dict(getattr(result, "quality_flags", {}) or {})
            if validation_summary and validation_summary != "All checks passed":
                if validation_warnings:
                    detail = ", ".join(str(item) for item in validation_warnings[:4] if str(item).strip())
                    if detail:
                        validation_summary = f"{validation_summary} | {detail}"
                return tr("RESULTS_SUMMARY_RISK_VALIDATION", validation_summary)

        if technique == "saxs" and result is not None:
            mask_truncated = bool(getattr(result, "mask_truncated", False))
            beamstop_warning = bool(getattr(result, "beam_stop_contaminated", False))
            if mask_truncated or beamstop_warning:
                eff_q = getattr(result, "effective_q_min", 0.0)
                try:
                    eff_q_text = f"{float(eff_q):.3f}"
                except Exception:
                    eff_q_text = "0.000"
                if mask_truncated and beamstop_warning:
                    return tr("RESULTS_SUMMARY_RISK_MASK_AND_BEAMSTOP", eff_q_text)
                if mask_truncated:
                    return tr("RESULTS_SUMMARY_RISK_MASK_ONLY", eff_q_text)
                return tr("RESULTS_SUMMARY_RISK_BEAMSTOP_ONLY", eff_q_text)
            mask_summary = self._result_mask_summary_text(result)
            if mask_summary:
                return mask_summary

            evidence = self._current_analysis_evidence()
            fallback_text = self._batch_fallback_summary_text(evidence)
            if fallback_text:
                return tr("RESULTS_REVIEW_FALLBACK", fallback_text)

            strain_risk_text = self._saxs_strain_risk_summary_text(params, evidence)
            if strain_risk_text:
                return strain_risk_text

            lc_status_text = self._saxs_lc_status_summary_text(params, evidence)
            if lc_status_text:
                return lc_status_text

            quality_flag_text = self._quality_flag_summary_text(result)
            if quality_flag_text:
                return tr("RESULTS_SUMMARY_RISK_VALIDATION", quality_flag_text)

        if technique == "waxs":
            analysis_evidence = self._current_analysis_evidence()
            structure = self._waxs_structure_evidence(analysis_evidence)
            support = self._waxs_support_snapshot(analysis_evidence)
            constraint_summary = analysis_evidence.get("constraint_summary", {}) if isinstance(analysis_evidence, dict) else {}
            if validation_summary and validation_summary != "All checks passed":
                return tr("RESULTS_SUMMARY_RISK_VALIDATION", validation_summary)
            if (
                structure.get("physical_support_pass") is False
                or structure.get("paper_ready_candidate") is False
                or (support.get("waxs_support_score") is not None and float(support["waxs_support_score"]) < 0.72)
                or (support.get("D_trend_support_score") is not None and float(support["D_trend_support_score"]) < 0.60)
                or (isinstance(constraint_summary, dict) and str(constraint_summary.get("status") or "").strip() in {"soft_warn", "hard_fail"})
            ):
                return tr("RESULTS_SUMMARY_RISK_WAXS_LIMITED")

        if technique == "dsc":
            analysis_evidence = self._current_analysis_evidence()
            feature = analysis_evidence.get("feature_evidence", {}) if isinstance(analysis_evidence, dict) else {}
            structure = feature.get("structure_evidence", {}) if isinstance(feature.get("structure_evidence"), dict) else {}
            event_support = feature.get("event_support_evidence", {}) if isinstance(feature.get("event_support_evidence"), dict) else {}
            support_values = [
                self._coerce_summary_float(event_support.get("event_support_score")),
                self._coerce_summary_float(event_support.get("baseline_stability_score")),
                self._coerce_summary_float(event_support.get("thermodynamic_consistency_score")),
            ]
            if structure.get("paper_conclusion_ready") is False and any(value is not None and value < 0.72 for value in support_values):
                return tr("RESULTS_SUMMARY_RISK_DSC_LIMITED")

        if isinstance(params, dict):
            condition_source = ""
            condition_confidence = None
            condition_missing_frames = None
            condition_continuity_score = None
            batch_frames = 0
            if technique == "saxs":
                condition_source = str(params.get("condition_source") or "").strip()
                condition_confidence = self._coerce_summary_float(params.get("condition_confidence"))
                condition_missing_frames = params.get("condition_missing_frames")
                condition_continuity_score = self._coerce_summary_float(params.get("condition_continuity_score"))
                try:
                    batch_frames = int(params.get("batch_frames", 0) or 0)
                except Exception:
                    batch_frames = 0
            if (
                    batch_frames > 1
                    and (
                        condition_source
                        or condition_confidence is not None
                        or condition_missing_frames not in (None, [], {})
                        or condition_continuity_score is not None
                    )
                ):
                    confidence_text = (
                        f"{condition_confidence:.2f}"
                        if condition_confidence is not None
                        else tr("AI_TUNING_EMPTY_VALUE")
                    )
                    continuity_text = (
                        f"{condition_continuity_score:.2f}"
                        if condition_continuity_score is not None
                        else tr("AI_TUNING_EMPTY_VALUE")
                    )
                    missing_text = self._display_text_value(condition_missing_frames)
                    return tr(
                        "RESULTS_SUMMARY_RISK_CONDITION_AXIS",
                        condition_source or tr("AI_TUNING_EMPTY_VALUE"),
                        confidence_text,
                        missing_text,
                        continuity_text,
                    )
            strain_risk_text = self._saxs_strain_risk_summary_text(params, self._current_analysis_evidence())
            if strain_risk_text:
                return strain_risk_text
            if not validation_summary:
                lc_status_text = self._saxs_lc_status_summary_text(params, self._current_analysis_evidence())
                if lc_status_text:
                    return lc_status_text
                validation_summary = str(params.get("validation_summary") or "").strip()
            if not validation_warnings and isinstance(params.get("validation_warnings"), list):
                validation_warnings = [str(item) for item in params.get("validation_warnings") or [] if str(item).strip()]
            if not quality_flags and isinstance(params.get("quality_flags"), dict):
                quality_flags = dict(params.get("quality_flags") or {})
            if params.get("validation_summary"):
                display = str(params.get("validation_summary") or "").strip()
                if validation_warnings:
                    detail = ", ".join(validation_warnings[:4])
                    if detail:
                        display = f"{display} | {detail}"
                return tr("RESULTS_SUMMARY_RISK_VALIDATION", display)

        if validation_summary and validation_summary != "All checks passed":
            detail_items = validation_warnings or [
                str(key)
                for key, flag in quality_flags.items()
                if str(flag).upper() == "WARN"
            ]
            if detail_items:
                detail = ", ".join(detail_items[:4])
                validation_summary = f"{validation_summary} | {detail}"
            return tr("RESULTS_SUMMARY_RISK_VALIDATION", validation_summary)

        return ""

    def _quality_flag_summary_text(self, result) -> str:
        if result is None:
            return ""
        if isinstance(result, dict):
            quality_flag = str(result.get("quality_flag", "") or "").strip()
        else:
            quality_flag = str(getattr(result, "quality_flag", "") or "").strip()
        if not quality_flag or quality_flag == "OK":
            return ""

        flags = [item.strip() for item in quality_flag.split(";") if item.strip()]
        if not flags:
            return ""

        if get_language() == "zh":
            mapping = {
                "WARN:low_snr": "主峰信噪比偏低",
                "WARN:sasmodels_low_r2": "sasmodels 拟合偏弱",
                "ERROR:sasmodels_failed": "sasmodels 拟合失败",
                "WARN:qstar_series_jump": "相邻帧 Q* 跳变较大",
                "WARN:qstar_anomalous": "Q* 数值异常",
                "ERROR:lc_ge_L": "lc 与 L 的关系不成立",
                "ERROR:L_out_of_range": "长周期超出物理范围",
                "ERROR:L_not_computed": "长周期未能稳定计算",
            }
            parts = [mapping.get(flag, flag.replace("ERROR:", "").replace("WARN:", "").replace("_", " ")) for flag in flags[:4]]
            return "；".join(parts)

        mapping = {
            "WARN:low_snr": "low peak SNR",
            "WARN:sasmodels_low_r2": "weak sasmodels fit",
            "ERROR:sasmodels_failed": "sasmodels fit failed",
            "WARN:qstar_series_jump": "adjacent-frame Q* jump",
            "WARN:qstar_anomalous": "anomalous Q*",
            "ERROR:lc_ge_L": "lc >= L",
            "ERROR:L_out_of_range": "L outside the physical range",
            "ERROR:L_not_computed": "long period not computed",
        }
        parts = [mapping.get(flag, flag.replace("ERROR:", "").replace("WARN:", "").replace("_", " ")) for flag in flags[:4]]
        return "; ".join(parts)

    def _display_text_value(self, value):
        if value is None:
            return tr("AI_TUNING_EMPTY_VALUE")
        text = str(value).strip()
        return text or tr("AI_TUNING_EMPTY_VALUE")

    def _display_text(self, value):
        if isinstance(value, (dict, list)):
            text = json.dumps(value, ensure_ascii=False)
        elif value is None:
            text = ""
        else:
            text = str(value)
        text = text.strip()
        return text or tr("AI_TUNING_EMPTY_VALUE")

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
        return _build_ir_support_block_text(
            analysis_evidence,
            display_text=self._display_text,
            format_score_value=self._format_score_value,
            ir_label_text=self._ir_label_text,
            include_reference_summary=True,
        )

    def _coerce_summary_float(self, value):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if math.isfinite(number):
            return number
        return None


    def _results_has_critical_risk(self, params, result=None):

        analysis_evidence = self._current_analysis_evidence()
        if self._has_condition_axis_risk(params, analysis_evidence):
            return True
        if self._has_fallback_conflict_risk(analysis_evidence):
            return True
        if str(getattr(self, "_current_technique", "") or "").strip().lower() == "waxs":
            structure = self._waxs_structure_evidence(analysis_evidence)
            support = self._waxs_support_snapshot(analysis_evidence)
            if structure.get("physical_support_pass") is False:
                return True
            overall = support.get("waxs_support_score")
            if overall is not None and overall < 0.72:
                return True
        if str(getattr(self, "_current_technique", "") or "").strip().lower() == "dsc":
            feature = analysis_evidence.get("feature_evidence", {}) if isinstance(analysis_evidence, dict) else {}
            structure = feature.get("structure_evidence", {}) if isinstance(feature.get("structure_evidence"), dict) else {}
            event_support = feature.get("event_support_evidence", {}) if isinstance(feature.get("event_support_evidence"), dict) else {}
            support_values = [
                self._coerce_summary_float(event_support.get("event_support_score")),
                self._coerce_summary_float(event_support.get("baseline_stability_score")),
                self._coerce_summary_float(event_support.get("thermodynamic_consistency_score")),
            ]
            if structure.get("paper_conclusion_ready") is False and any(value is not None and value < 0.72 for value in support_values):
                return True
        if result is not None:
            validation_summary = str(getattr(result, "validation_summary", "") or "").strip()
            if validation_summary and validation_summary != "All checks passed":
                return True
            if bool(getattr(result, "mask_truncated", False)) or bool(getattr(result, "beam_stop_contaminated", False)):
                return True
        if isinstance(params, dict):
            validation_summary = str(params.get("validation_summary") or "").strip()
            if validation_summary and validation_summary != "All checks passed":
                return True
        return False


    def _results_next_step_text(self, params, result=None):

        mode = str(getattr(self, "_current_input_mode", "") or "").strip().lower()
        technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
        has_risk = self._results_has_critical_risk(params, result)
        analysis_evidence = self._current_analysis_evidence()

        if technique == "saxs":
            if self._has_fallback_conflict_risk(analysis_evidence):
                return tr("RESULTS_SUMMARY_NEXT_FALLBACK_CONFLICT")
            if self._has_condition_axis_risk(params, analysis_evidence):
                return tr("RESULTS_SUMMARY_NEXT_CONDITION_AXIS")
            strain_next_text = self._saxs_strain_next_step_text(params, analysis_evidence)
            if strain_next_text:
                return strain_next_text
            if self._saxs_lc_status_summary_text(params, analysis_evidence):
                return tr("RESULTS_SUMMARY_NEXT_SAXS_LC_STATUS")

        if mode == "sequence":
            return tr("RESULTS_SUMMARY_NEXT_SEQUENCE")
        if mode == "directory":
            return tr("RESULTS_SUMMARY_NEXT_DIRECTORY")
        if isinstance(params, dict) and len(params) > 1 and all(isinstance(v, dict) for v in params.values()) and not any(
            str(k).startswith("_") for k in params
        ):
            return tr("RESULTS_SUMMARY_NEXT_MULTI_SAMPLE")
        batch_frames = 0
        if isinstance(params, dict):
            try:
                batch_frames = int(params.get("batch_frames", 0) or 0)
            except Exception:
                batch_frames = 0
        if batch_frames > 1:
            return tr("RESULTS_SUMMARY_NEXT_BATCH")
        if technique == "saxs" and has_risk:
            return tr("RESULTS_SUMMARY_NEXT_SAXS_RISK")
        if technique == "waxs" and has_risk:
            return tr("RESULTS_SUMMARY_NEXT_WAXS_RISK")
        if technique == "dsc" and has_risk:
            return tr("RESULTS_SUMMARY_NEXT_DSC_RISK")
        if result is not None:
            return tr("RESULTS_SUMMARY_NEXT_SINGLE")
        return ""


    def _ordered_results_columns(self, columns):

        preferred = [
            "file",
            "sample",
            "batch",
            "condition",
            "stage",
            "frame",
            "index",
            "temperature_C",
            "temp_C",
            "T_C",
            "time_min",
            "t_min",
            "L_nm",
            "lc_nm",
            "melting_window_status",
            "lc_reliability_status",
            "lc_reliability_reason",
            "lc_nm_raw",
            "lc_nm_calibrated",
            "Xc",
            "Xc_raw",
            "Xc_calibrated",
            "calibration_skipped_reason",
            "Xc_pct",
            "D_Scherrer_nm",
            "Tm_C",
            "Tm_peak_C",
            "Tc_C",
            "Tc_peak_C",
            "Tg_C",
            "effective_q_min",
            "q_min",
        ]
        rank = {name.lower(): idx for idx, name in enumerate(preferred)}
        seen = set()
        unique_columns = []
        for col in columns:
            key = str(col)
            normalized = key.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            unique_columns.append(key)

        def sort_key(name):
            normalized = name.lower()
            return (rank.get(normalized, len(rank)), unique_columns.index(name))

        return sorted(unique_columns, key=sort_key)


    def _build_joint_metric_label(self):

        label = QLabel()

        label.setMinimumHeight(34)

        label.setAlignment(Qt.AlignCenter)

        label.setStyleSheet(
            "QLabel { padding: 6px 10px; border: 1px solid #3a4553; "
            "border-radius: 4px; font-weight: 600; }"
        )

        return label



    def _build_plots_tab(self):

        """Plots tab: exported figure gallery and focused figure preview."""

        w = QWidget()

        layout = QVBoxLayout(w)

        layout.setSpacing(8)



        # Figure library is the default Plots view. The large preview stays
        # hidden until a user clicks a figure card.

        self._plots_label = QLabel(tr("PLOTS_EMPTY"))

        self._plots_label.setAlignment(Qt.AlignCenter)

        self._plots_label.setStyleSheet(

            f"color: {C_TEXT_MUTED}; font-size: 13px; padding: 20px;"

        )

        layout.addWidget(self._plots_label)



        # Toolbar

        toolbar = QHBoxLayout()

        self._btn_view_current_figure = QPushButton(tr("PLOTS_BTN_VIEW_CURRENT"))

        self._btn_view_current_figure.setObjectName("secondary_btn")

        self._btn_view_current_figure.clicked.connect(self._open_current_figure_viewer)

        self._btn_view_current_figure.setEnabled(False)

        toolbar.addWidget(self._btn_view_current_figure)

        toolbar.addStretch()

        layout.addLayout(toolbar)

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

        self._chart_gallery.edit_requested.connect(self._open_selected_chart_editor)

        self._chart_gallery.setVisible(False)

        self._chart_gallery.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout.addWidget(self._chart_gallery, 4)



        return w


    def _build_history_panel(self):

        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(8)

        toolbar = QHBoxLayout()
        self._history_tech_label = QLabel(tr("HISTORY_TECHNIQUE"))
        toolbar.addWidget(self._history_tech_label)

        self._history_filter_combo = QComboBox()
        self._set_history_filter_items(["saxs", "waxs", "dsc", "ir", "nmr"])
        self._history_filter_combo.currentIndexChanged.connect(self._refresh_history)
        toolbar.addWidget(self._history_filter_combo)

        self._history_refresh_btn = QPushButton(tr("HISTORY_REFRESH"))
        self._history_refresh_btn.setObjectName("secondary_btn")
        self._history_refresh_btn.clicked.connect(self._refresh_history)
        toolbar.addWidget(self._history_refresh_btn)

        self._history_export_btn = QPushButton(tr("HISTORY_EXPORT"))
        self._history_export_btn.setObjectName("secondary_btn")
        self._history_export_btn.clicked.connect(self._export_history_table)
        toolbar.addWidget(self._history_export_btn)

        self._history_copy_summary_btn = QPushButton(tr("HISTORY_COPY_SUMMARY"))
        self._history_copy_summary_btn.setObjectName("secondary_btn")
        self._history_copy_summary_btn.clicked.connect(self._copy_history_summary)
        toolbar.addWidget(self._history_copy_summary_btn)

        self._history_restore_btn = QPushButton(tr("HISTORY_RESTORE"))
        self._history_restore_btn.setObjectName("secondary_btn")
        self._history_restore_btn.clicked.connect(self._on_history_restore_requested)
        toolbar.addWidget(self._history_restore_btn)

        self._history_rerun_btn = QPushButton(tr("HISTORY_RERUN"))
        self._history_rerun_btn.setObjectName("secondary_btn")
        self._history_rerun_btn.clicked.connect(self._on_history_rerun_requested)
        toolbar.addWidget(self._history_rerun_btn)

        self._history_confirm_btn = QPushButton(tr("RESULTS_CONFIRM_MARK"))
        self._history_confirm_btn.setObjectName("secondary_btn")
        self._history_confirm_btn.clicked.connect(self._on_history_confirm_requested)
        toolbar.addWidget(self._history_confirm_btn)

        self._history_compare_btn = QPushButton(tr("HISTORY_COMPARE"))
        self._history_compare_btn.setObjectName("secondary_btn")
        self._history_compare_btn.clicked.connect(self._on_history_compare_requested)
        toolbar.addWidget(self._history_compare_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        self._history_table = QTableWidget()
        self._history_table.setColumnCount(7)
        self._history_table.setHorizontalHeaderLabels([
            tr("HISTORY_COL_TIME"),
            tr("HISTORY_COL_TECHNIQUE"),
            tr("HISTORY_COL_SUBMODULE"),
            tr("HISTORY_COL_SCORE"),
            tr("HISTORY_COL_STATUS"),
            tr("HISTORY_COL_VALIDATION"),
            tr("HISTORY_COL_CONFIRMED"),
        ])
        self._history_table.setAlternatingRowColors(True)
        self._history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._history_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._history_table.setWordWrap(False)
        self._history_table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self._history_table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self._history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._history_table.cellDoubleClicked.connect(self._on_history_row_activated)
        self._history_table.itemActivated.connect(
            lambda item: self._on_history_row_activated(item.row(), item.column()) if item is not None else None
        )
        self._history_copy_shortcut = QShortcut(QKeySequence.Copy, self._history_table)
        self._history_copy_shortcut.activated.connect(self._copy_history_summary)
        self._history_table.itemSelectionChanged.connect(self._update_history_action_state)
        layout.addWidget(self._history_table, 1)

        self._refresh_history()
        self._update_history_action_state()
        return w

    def _apply_theme(self):

        # Rebuild and apply the global QSS theme, then repolish the app.
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()

        if app:

            app.setStyleSheet(build_qss(self._theme_engine.tokens))

        self._theme_engine.switch(self._theme_engine.current)

        for btn in getattr(self, "_nav_buttons", {}).values():

            btn_tech = btn.property("technique") or self._current_technique or "waxs"

            btn.setStyleSheet(self._nav_sub_style(btn_tech, btn.isChecked()))

        self._update_workspace_context()



    def _build_menubar(self):

        """Create menu bar with File/Edit/View/Help menus."""

        menubar = self.menuBar()



        self._menu_file = menubar.addMenu(tr("MENU_FILE"))

        self._act_open = self._menu_file.addAction(tr("ACTION_OPEN"))

        self._act_open.triggered.connect(self._browse_file)

        self._act_export = self._menu_file.addAction(tr("ACTION_EXPORT"))

        self._act_export.triggered.connect(self._export_results)

        self._menu_file.addSeparator()

        self._act_quit = self._menu_file.addAction(tr("ACTION_QUIT"))

        self._act_quit.triggered.connect(self.close)



        self._menu_edit = menubar.addMenu(tr("MENU_EDIT"))

        self._act_settings = self._menu_edit.addAction(tr("ACTION_SETTINGS"))

        self._act_settings.triggered.connect(self._on_settings)



        self._menu_view = menubar.addMenu(tr("MENU_VIEW"))

        self._act_toggle_sidebar = self._menu_view.addAction(tr("ACTION_TOGGLE_SIDEBAR"))

        self._act_toggle_sidebar.triggered.connect(self._toggle_sidebar)

        self._act_toggle_theme = self._menu_view.addAction(tr("ACTION_TOGGLE_THEME"))

        self._act_toggle_theme.triggered.connect(self._toggle_theme)

        self._act_toggle_lang = self._menu_view.addAction(tr("ACTION_TOGGLE_LANG"))

        self._act_toggle_lang.triggered.connect(self._toggle_language)

        self.action_convergence_viewer = QAction(tr('CONVERGENCE_DASHBOARD'), self)
        self.action_convergence_viewer.setObjectName("action_convergence_viewer")
        self.action_convergence_viewer.triggered.connect(self._open_convergence_viewer)
        self._menu_view.addAction(self.action_convergence_viewer)



        self._menu_help = menubar.addMenu(tr("MENU_HELP"))

        self._act_about = self._menu_help.addAction(tr("ACTION_ABOUT"))

        self._act_about.triggered.connect(self._on_help)



    def _build_statusbar(self):

        """Create status bar with technique indicator."""

        self._statusbar = self.statusBar()

        self._statusbar.setObjectName("statusbar")



        # Technique indicator pill

        self._status_tech_label = QLabel(f" {tr('WORKSPACE_TITLE_DEFAULT')} ")

        self._status_tech_label.setObjectName("status_tech")

        self._statusbar.addWidget(self._status_tech_label)



        # Spacer

        spacer = QWidget()

        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self._statusbar.addWidget(spacer, 1)



        self._statusbar.showMessage(tr("STATUSBAR_READY"))



    def _toggle_theme(self):

        """Toggle between dark and light theme."""

        self._theme_engine.toggle()

        self._apply_theme()

        new_name = tr("THEME_DARK") if self._theme_engine.is_dark else tr("THEME_LIGHT")

        self.log(tr("LOG_THEME_CHANGED", new_name))

        try:

            self._btn_theme.setText("\u263e" if self._theme_engine.is_dark else "\u2600")

        except Exception:
            logger.warning("Failed to update re-plot tooltip during retranslate.", exc_info=True)

        try:

            self._statusbar.showMessage(tr("STATUSBAR_THEME", new_name))

        except Exception:
            logger.warning("Failed to update language toggle text during retranslate.", exc_info=True)



    def _toggle_sidebar(self):

        """Toggle sidebar visibility."""

        sidebar = getattr(self, "_sidebar", None) or self.findChild(QWidget, "sidebar")

        if sidebar:

            if sidebar.isVisible():

                anim_done = lambda: sidebar.setVisible(False)

                animate_width(sidebar, 0)

                getattr(sidebar, "_pn_width_anim", None).finished.connect(anim_done)

            else:

                sidebar.setVisible(True)

                sidebar.setMinimumWidth(0)

                sidebar.setMaximumWidth(0)

                animate_width(sidebar, self._sidebar_expanded_width)



    def _on_settings(self):

        """Open settings dialog."""

        dlg = SettingsDialog(self)

        dlg.exec()



    def _on_help(self):

        """Show about dialog."""

        QMessageBox.about(self, tr("ACTION_ABOUT"), tr("ABOUT_TEXT"))



    def _on_quit(self):

        """Quit application."""

        self.close()



    def _on_tech_saxs(self): self._on_technique_selected("saxs")

    def _on_tech_waxs(self): self._on_technique_selected("waxs")

    def _on_tech_dsc(self):  self._on_technique_selected("dsc")

    def _on_tech_ir(self):   self._on_technique_selected("ir")

    def _on_tech_nmr(self):  self._on_technique_selected("nmr")



    def _on_technique_selected(self, technique):

        """Switch to *technique* and update nav button styles (theme-aware)."""

        self._current_technique = technique

        self._set_sample_browser_visible(False)

        self._set_joint_hub_visible(False)

        self._btn_run.setEnabled(True)



        tokens = self._theme_engine.tokens

        accent = technique_accent(technique, tokens)

        active_id = technique if technique in self._nav_buttons else None

        if active_id is None:

            for key, btn in self._nav_buttons.items():

                if btn.property("technique") == technique:

                    active_id = key

                    break

        self._set_nav_visual_state(active_id, technique)

        self._project_label.setStyleSheet(

            f"color: {accent}; font-weight: 700; font-size: 11px; "

            f"background: transparent; border: none;"

        )



        self._build_config_for_technique(technique)
        self._refresh_config_preset_controls()

        self._update_workspace_context()

        self.log(tr("LOG_TECHNIQUE_SELECTED", TECHNIQUE_LABELS.get(technique, technique)))



    def _on_submodule_selected(self, technique, submodule_id):

        self._current_technique = technique

        self._current_submodule_id = submodule_id

        self._set_sample_browser_visible(False)

        self._set_joint_hub_visible(False)

        self._btn_run.setEnabled(True)

        self._set_nav_visual_state(submodule_id, technique)

        self._update_workspace_context()

        self.log(tr("LOG_SUBMODULE_SELECTED", submodule_id))

        self._update_config_panel()
        self._refresh_config_preset_controls()



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


    def _set_sample_batch_context(self, *, sample_id="", batch_id="", sample_name="", batch_label=""):

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

        db = self._ensure_sample_db()
        batch = db.get_batch(batch_id)
        if not batch:
            return

        batch_sample_id = str(batch.get("sample_id", "") or "").strip()
        sample = db.get_sample(batch_sample_id) if batch_sample_id else None
        self._set_sample_batch_context(
            sample_id=batch_sample_id,
            batch_id=batch_id,
            sample_name=(sample or {}).get("polymer_name", ""),
            batch_label=batch.get("label", ""),
        )

        files = db.get_data_files(batch_id)
        if not files:
            QMessageBox.warning(
                self,
                tr("SAMPLE_BATCH_ANALYZE"),
                tr("SAMPLE_BATCH_ANALYZE_NO_FILE"),
            )
            return

        runs = db.get_analysis_runs(batch_id)
        latest_run = runs[0] if runs else {}
        latest_technique = str(latest_run.get("technique", "") or "").strip().lower()
        latest_submodule = str(latest_run.get("submodule", "") or "").strip()

        selected_file = None
        if latest_technique:
            for file_row in files:
                if str(file_row.get("technique", "") or "").strip().lower() == latest_technique:
                    selected_file = file_row
                    break
        if selected_file is None:
            selected_file = files[0]

        file_path = str(selected_file.get("file_path", "") or "").strip()
        if not file_path or not Path(file_path).exists():
            QMessageBox.warning(
                self,
                tr("SAMPLE_BATCH_ANALYZE"),
                tr("SAMPLE_BATCH_ANALYZE_FILE_MISSING", file_path or "-"),
            )
            return

        technique = (
            latest_technique
            or str(selected_file.get("technique", "") or "").strip().lower()
        )
        if not technique:
            return

        self._current_submodule_id = ""
        self._on_technique_selected(technique)
        btn = self._nav_buttons.get(technique)
        if btn:
            btn.setChecked(True)

        if latest_submodule and latest_submodule in self._nav_buttons:
            sub_btn = self._nav_buttons.get(latest_submodule)
            if sub_btn:
                sub_btn.setChecked(True)
            self._on_submodule_selected(technique, latest_submodule)
        else:
            self._current_submodule_id = ""
            self._update_workspace_context()

        self._set_input_path(file_path, clear_sample_context=False)
        self._save_last_dir(file_path)

        output_dir = str(latest_run.get("output_dir", "") or "").strip()
        if output_dir:
            self._output_dir = output_dir
            if hasattr(self, "_output_input"):
                self._output_input.setText(output_dir)

        if hasattr(self, "_tabs"):
            self._tabs.setCurrentIndex(0)

        self._update_workspace_context()

        self.log(tr("LOG_SAMPLE_BATCH_ANALYSIS_READY", batch.get("label", "") or batch_id))


    def _on_sample_joint_requested(self, batch_ids):

        self._on_joint_selected("joint.compare")

        hub = getattr(self, "_joint_hub", None)

        if hub is not None:

            hub.select_batch_ids(batch_ids)

        self._update_workspace_context()



    def _update_config_panel(self):

        while self._config_form.rowCount() > 0:

            self._config_form.removeRow(0)

        submodule_id = getattr(self, '_current_submodule_id', '')

        if not submodule_id:

            lbl = QLabel(tr("CONFIG_SELECT_SUBMODULE"))

            lbl.setStyleSheet(f"color: {C_TEXT_MUTED}; padding: 8px;")

            self._config_form.addRow(lbl)
            self._refresh_config_preset_controls()

            return

        from ..core.submodule_registry import list_all_submodules

        schema = {}

        for mod in list_all_submodules():

            if mod['id'] == submodule_id:

                schema = mod.get('config_schema', {})

                break

        if not schema:

            lbl = QLabel(tr("CONFIG_NO_SUBMODULE_CONFIG"))

            lbl.setStyleSheet(f"color: {C_TEXT_MUTED}; padding: 8px;")

            self._config_form.addRow(lbl)
            self._refresh_config_preset_controls()

            return

        for key, spec in schema.items():

            self._add_config_field(key, spec)

        calibration_schema = self._calibration_config_schema()
        calibration_hint = self._calibration_hint_text()
        if calibration_schema and calibration_hint:
            lbl = QLabel(calibration_hint)
            lbl.setWordWrap(True)
            lbl.setProperty("config_hint_key", f"{self._current_technique}_calibration")
            lbl.setStyleSheet(f"color: {C_TEXT_MUTED}; padding: 6px 0 10px 0;")
            self._config_form.addRow(lbl)

        for key, spec in calibration_schema.items():

            self._add_config_field(key, spec)

        mask_schema = self._mask_config_schema()
        mask_hint = self._mask_hint_text()
        if mask_hint and (mask_schema or str(getattr(self, "_current_technique", "") or "").strip().lower() == "waxs"):
            lbl = QLabel(mask_hint)
            lbl.setWordWrap(True)
            lbl.setProperty("config_hint_key", f"{self._current_technique}_mask")
            lbl.setStyleSheet(f"color: {C_TEXT_MUTED}; padding: 6px 0 10px 0;")
            self._config_form.addRow(lbl)

        for key, spec in mask_schema.items():

            self._add_config_field(key, spec)

        if mask_schema:
            summary_label = QLabel()
            summary_label.setWordWrap(True)
            summary_label.setProperty("config_hint_key", f"{self._current_technique}_mask_summary")
            summary_label.setStyleSheet(f"color: {C_TEXT_MUTED}; padding: 0 0 8px 0;")
            self._config_form.addRow(summary_label)
            self._refresh_mask_summary_label()

        self._refresh_config_preset_controls()


    def _add_config_field(self, key, spec):

        field_type = spec.get("type", "string")
        label = spec.get("label", key)

        if field_type == "choice":

            widget = QComboBox()

            widget.addItems(spec.get("options", []))

            default_value = spec.get("default", "")

            if default_value in spec.get("options", []):

                widget.setCurrentText(default_value)

        elif field_type == "int":

            widget = QSpinBox()

            widget.setRange(spec.get("min", 0), spec.get("max", 100))

            widget.setValue(spec.get("default", 0))

        elif field_type == "float":

            widget = QDoubleSpinBox()

            widget.setRange(spec.get("min", 0.0), spec.get("max", 1000.0))

            widget.setValue(spec.get("default", 1.0))

            widget.setDecimals(spec.get("decimals", 2))

            step = spec.get("step")
            if isinstance(step, (int, float)):
                widget.setSingleStep(float(step))

        elif field_type == "bool":

            widget = QCheckBox()

            widget.setChecked(spec.get("default", False))
            if label:
                widget.setText(label)

            label = ""

        else:

            widget = QLineEdit()

            widget.setText(str(spec.get("default", "")))

        if label:

            self._config_form.addRow(f"{label}:", widget)

        else:

            self._config_form.addRow(widget)

        widget.setProperty("config_key", key)
        self._connect_config_widget_signals(widget)
        return widget

    def _connect_config_widget_signals(self, widget):

        if isinstance(widget, QComboBox):
            widget.currentIndexChanged.connect(self._on_config_widget_changed)
        elif isinstance(widget, QDoubleSpinBox):
            widget.valueChanged.connect(self._on_config_widget_changed)
        elif isinstance(widget, QSpinBox):
            widget.valueChanged.connect(self._on_config_widget_changed)
        elif isinstance(widget, QCheckBox):
            widget.checkStateChanged.connect(self._on_config_widget_changed)
        elif isinstance(widget, QLineEdit):
            widget.textChanged.connect(self._on_config_widget_changed)

    def _on_config_widget_changed(self, *_args):

        self._refresh_mask_summary_label()


    def _calibration_config_schema(self):

        technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
        if technique == "saxs":
            return {
                "crystallinity": {"type": "string", "default": "", "label": tr("CONFIG_SAXS_REFERENCE_CRYSTALLINITY")},
                "T_melt_expected": {"type": "string", "default": "", "label": tr("CONFIG_SAXS_EXPECTED_MELT")},
                "wavelength_m": {"type": "float", "default": 1.541891e-10, "min": 1e-12, "max": 1e-8, "decimals": 12, "step": 1e-11, "label": tr("CONFIG_SAXS_WAVELENGTH")},
                "pixel_size_m": {"type": "float", "default": 75e-6, "min": 1e-7, "max": 1e-2, "decimals": 6, "step": 1e-6, "label": tr("CONFIG_SAXS_PIXEL_SIZE")},
                "sdd_m": {"type": "float", "default": 0.450, "min": 0.01, "max": 10.0, "decimals": 4, "step": 0.01, "label": tr("CONFIG_SAXS_SDD")},
                "beam_center_x": {"type": "float", "default": 255.43, "min": 0.0, "max": 10000.0, "decimals": 2, "step": 1.0, "label": tr("CONFIG_SAXS_BEAM_CENTER_X")},
                "beam_center_y": {"type": "float", "default": 549.73, "min": 0.0, "max": 10000.0, "decimals": 2, "step": 1.0, "label": tr("CONFIG_SAXS_BEAM_CENTER_Y")},
                "poni_file": {"type": "string", "default": "", "label": tr("CONFIG_SAXS_PONI_FILE")},
            }
        if technique == "waxs":
            return {
                "wavelength_A": {"type": "float", "default": 1.5406, "min": 0.1, "max": 5.0, "decimals": 4, "step": 0.0001, "label": tr("CONFIG_WAXS_WAVELENGTH")},
                "two_theta_offset": {"type": "float", "default": 0.0, "min": -1.0, "max": 1.0, "decimals": 4, "step": 0.01, "label": tr("CONFIG_WAXS_TWO_THETA_OFFSET")},
            }
        return {}


    def _mask_config_schema(self):

        technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
        if technique == "saxs":
            return {
                "auto_detect_beamstop": {"type": "bool", "default": True, "label": tr("CONFIG_SAXS_AUTO_DETECT_BEAMSTOP")},
                "beamstop_pollution_threshold": {"type": "float", "default": 100.0, "min": 5.0, "max": 5000.0, "decimals": 1, "step": 5.0, "label": tr("CONFIG_SAXS_BEAMSTOP_THRESHOLD")},
                "dummy_val": {"type": "float", "default": -1.5, "min": -1e6, "max": 1e6, "decimals": 3, "step": 0.1, "label": tr("CONFIG_SAXS_DUMMY_VALUE")},
                "ddummy": {"type": "float", "default": 0.6, "min": 0.0, "max": 1e4, "decimals": 3, "step": 0.1, "label": tr("CONFIG_SAXS_DDUMMY")},
            }
        return {}


    def _calibration_hint_text(self):

        technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
        if technique == "saxs":
            return tr("CONFIG_CALIBRATION_HINT_SAXS")
        if technique == "waxs":
            return tr("CONFIG_CALIBRATION_HINT_WAXS")
        return ""


    def _mask_hint_text(self):

        technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
        if technique == "saxs":
            return tr("CONFIG_MASK_HINT_SAXS")
        if technique == "waxs":
            return tr("CONFIG_MASK_HINT_WAXS")
        return ""

    def _current_mask_summary_text(self):

        technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
        if technique != "saxs":
            return ""

        auto_detect_widget = self._config_widget_by_key("auto_detect_beamstop")
        threshold_widget = self._config_widget_by_key("beamstop_pollution_threshold")
        dummy_widget = self._config_widget_by_key("dummy_val")
        ddummy_widget = self._config_widget_by_key("ddummy")
        if not all([auto_detect_widget, threshold_widget, dummy_widget, ddummy_widget]):
            return ""

        auto_detect = bool(auto_detect_widget.isChecked()) if hasattr(auto_detect_widget, "isChecked") else False
        try:
            threshold = float(threshold_widget.value())
        except Exception:
            threshold = 0.0
        try:
            dummy_val = float(dummy_widget.value())
        except Exception:
            dummy_val = 0.0
        try:
            ddummy = float(ddummy_widget.value())
        except Exception:
            ddummy = 0.0

        return tr(
            "CONFIG_MASK_SUMMARY_SAXS",
            tr("COMMON_ON") if auto_detect else tr("COMMON_OFF"),
            f"{threshold:.1f}",
            f"{dummy_val:.3f}",
            f"{ddummy:.3f}",
        )

    def _refresh_mask_summary_label(self):

        label = self._config_hint_widget_by_key(f"{self._current_technique}_mask_summary")
        if label is None:
            return
        summary = self._current_mask_summary_text()
        label.setText(summary)
        label.setVisible(bool(summary))


    def _current_calibration_scope(self):

        technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
        submodule = str(getattr(self, "_current_submodule_id", "") or "").strip()
        calibration_keys = set(self._calibration_config_schema().keys())
        if technique not in {"saxs", "waxs"}:
            return None
        if not submodule or not calibration_keys:
            return None
        return technique, submodule


    def _calibration_settings_key(self, technique, submodule):

        return f"recent_calibration/{technique}/{submodule}"

    def _current_calibration_scope_label(self):

        scope = self._current_calibration_scope()
        if scope is None:
            return ""
        technique, submodule = scope
        technique_label = self._history_technique_text(technique)
        submodule_label = self._history_submodule_text(submodule) or submodule
        return f"{technique_label} / {submodule_label}"


    def _collect_calibration_panel_values(self):

        calibration_keys = set(self._calibration_config_schema().keys())
        if not calibration_keys:
            return {}
        values = self._collect_config_panel_values()
        return {
            key: value for key, value in values.items()
            if key in calibration_keys
        }

    def _compatible_recent_calibration_values(self, values):

        if not isinstance(values, dict):
            return {}, []
        calibration_keys = set(self._calibration_config_schema().keys())
        compatible = {
            key: value for key, value in values.items()
            if key in calibration_keys
        }
        ignored = sorted(
            str(key) for key in values.keys()
            if key not in calibration_keys
        )
        return compatible, ignored

    def _refresh_recent_calibration_button(self):

        button = getattr(self, "_btn_config_recent_calibration", None)
        save_button = getattr(self, "_btn_config_recent_calibration_save", None)
        if button is None and save_button is None:
            return

        scope_label = self._current_calibration_scope_label()
        values = self._load_recent_calibration()
        has_scope = bool(scope_label)
        has_values = isinstance(values, dict) and bool(values)

        if save_button is not None:
            save_button.setEnabled(has_scope)
            if has_scope:
                save_button.setToolTip(tr("CONFIG_RECENT_CALIBRATION_SAVE_TOOLTIP", scope_label))
            else:
                save_button.setToolTip(tr("CONFIG_RECENT_CALIBRATION_TOOLTIP_DISABLED"))

        if button is not None:
            button.setEnabled(has_values)
            if has_values and scope_label:
                button.setToolTip(tr("CONFIG_RECENT_CALIBRATION_TOOLTIP_READY", scope_label))
            elif has_scope:
                button.setToolTip(tr("CONFIG_RECENT_CALIBRATION_TOOLTIP_MISSING", scope_label))
            else:
                button.setToolTip(tr("CONFIG_RECENT_CALIBRATION_TOOLTIP_DISABLED"))


    def _save_recent_calibration(self):

        scope = self._current_calibration_scope()
        if scope is None:
            return

        values = self._collect_calibration_panel_values()
        if not values:
            return
        self._settings.setValue(
            self._calibration_settings_key(scope[0], scope[1]),
            json.dumps(values, ensure_ascii=False),
        )
        self._refresh_recent_calibration_button()


    def _load_recent_calibration(self):

        scope = self._current_calibration_scope()
        if scope is None:
            return None

        raw = self._settings.value(self._calibration_settings_key(scope[0], scope[1]), "")
        if not raw:
            return None
        try:
            values = json.loads(raw)
        except Exception:
            logger.warning("Failed to load recent calibration values from settings.", exc_info=True)
            return None
        return values if isinstance(values, dict) else None


    def _validate_calibration_inputs(self):

        if str(getattr(self, "_current_technique", "") or "").strip().lower() != "saxs":
            return True

        config = self._build_run_config()
        poni_file = str(getattr(config, "poni_file", "") or "").strip()
        if not poni_file:
            return True

        if Path(poni_file).expanduser().exists():
            return True

        QMessageBox.warning(
            self,
            tr("CALIBRATION_PONI_MISSING_TITLE"),
            tr("CALIBRATION_PONI_MISSING_DETAIL", poni_file),
        )
        self.log(tr("CALIBRATION_PONI_MISSING_LOG", poni_file))
        return False


    def _validate_mask_inputs(self):

        if str(getattr(self, "_current_technique", "") or "").strip().lower() != "saxs":
            return True

        config = self._build_run_config()

        threshold = float(getattr(config, "beamstop_pollution_threshold", 100.0) or 0.0)
        if threshold < 20.0:
            QMessageBox.warning(
                self,
                tr("MASK_CONFIG_WARNING_TITLE"),
                tr("MASK_BEAMSTOP_THRESHOLD_TOO_LOW", f"{threshold:.1f}"),
            )
            self.log(tr("MASK_BEAMSTOP_THRESHOLD_TOO_LOW_LOG", f"{threshold:.1f}"))
            return False

        ddummy = float(getattr(config, "ddummy", 0.0) or 0.0)
        if ddummy > 5.0:
            QMessageBox.warning(
                self,
                tr("MASK_CONFIG_WARNING_TITLE"),
                tr("MASK_DDUMMY_TOO_LARGE", f"{ddummy:.3f}"),
            )
            self.log(tr("MASK_DDUMMY_TOO_LARGE_LOG", f"{ddummy:.3f}"))
            return False

        return True


    def _on_apply_recent_calibration(self):

        values = self._load_recent_calibration()
        if not values:
            QMessageBox.warning(
                self,
                tr("CONFIG_RECENT_CALIBRATION_TITLE"),
                tr("CONFIG_RECENT_CALIBRATION_MISSING"),
            )
            return

        compatible_values, ignored_keys = self._compatible_recent_calibration_values(values)
        if not compatible_values:
            QMessageBox.warning(
                self,
                tr("CONFIG_RECENT_CALIBRATION_TITLE"),
                tr("CONFIG_RECENT_CALIBRATION_INCOMPATIBLE"),
            )
            self.log(
                tr(
                    "LOG_RECENT_CALIBRATION_INCOMPATIBLE",
                    self._current_calibration_scope_label() or "-",
                )
            )
            return

        self._apply_best_config(compatible_values)
        self.log(tr("LOG_RECENT_CALIBRATION_APPLIED"))
        if ignored_keys:
            self.log(tr("LOG_RECENT_CALIBRATION_PARTIAL", ", ".join(ignored_keys)))

    def _on_save_recent_calibration(self):

        scope = self._current_calibration_scope()
        if scope is None:
            QMessageBox.warning(
                self,
                tr("CONFIG_RECENT_CALIBRATION_TITLE"),
                tr("CONFIG_RECENT_CALIBRATION_SCOPE_REQUIRED"),
            )
            return

        values = self._collect_calibration_panel_values()
        if not values:
            QMessageBox.warning(
                self,
                tr("CONFIG_RECENT_CALIBRATION_TITLE"),
                tr("CONFIG_RECENT_CALIBRATION_EMPTY"),
            )
            return

        self._save_recent_calibration()
        self.log(tr("LOG_RECENT_CALIBRATION_SAVED", self._current_calibration_scope_label() or "-"))


    def _current_config_widget_keys(self):

        keys = []

        for row in range(self._config_form.rowCount()):

            item = self._config_form.itemAt(row, QFormLayout.FieldRole)

            if item is None:

                item = self._config_form.itemAt(row, QFormLayout.SpanningRole)

            widget = item.widget() if item is not None else None

            if widget is None:

                continue

            key = widget.property("config_key")

            if key:

                keys.append(str(key))

        return keys

    def _config_widget_by_key(self, target_key):

        key = str(target_key or "").strip()
        if not key:
            return None

        for row in range(self._config_form.rowCount()):
            item = self._config_form.itemAt(row, QFormLayout.FieldRole)
            if item is None:
                item = self._config_form.itemAt(row, QFormLayout.SpanningRole)
            widget = item.widget() if item is not None else None
            if widget is not None and widget.property("config_key") == key:
                return widget
        return None

    def _config_hint_widget_by_key(self, hint_key):

        key = str(hint_key or "").strip()
        if not key:
            return None

        for row in range(self._config_form.rowCount()):
            item = self._config_form.itemAt(row, QFormLayout.SpanningRole)
            widget = item.widget() if item is not None else None
            if widget is not None and widget.property("config_hint_key") == key:
                return widget
        return None


    def _current_config_preset_scope(self):

        technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
        submodule = str(getattr(self, "_current_submodule_id", "") or "").strip()

        if not technique or not submodule:
            return None
        if technique in {"joint", "samples"}:
            return None
        if not self._current_config_widget_keys():
            return None
        return technique, submodule


    def _current_config_preset_name(self):

        combo = getattr(self, "_config_preset_combo", None)
        if combo is None:
            return ""
        return str(combo.currentText() or "").strip()


    def _set_config_preset_placeholder(self, text):

        combo = getattr(self, "_config_preset_combo", None)
        if combo is None:
            return
        line_edit = combo.lineEdit()
        if line_edit is not None:
            line_edit.setPlaceholderText(text)


    def _on_config_preset_name_changed(self, _text):

        self._update_config_preset_action_state()


    def _update_config_preset_action_state(self, names=None):

        combo = getattr(self, "_config_preset_combo", None)
        if combo is None:
            return

        scope = self._current_config_preset_scope()
        has_scope = scope is not None
        if names is None and has_scope:
            names = list_config_presets(*scope)
        elif names is None:
            names = []

        current_name = self._current_config_preset_name()
        has_existing = has_scope and bool(current_name) and current_name in names

        combo.setEnabled(has_scope)
        if hasattr(self, "_btn_config_preset_save"):
            self._btn_config_preset_save.setEnabled(has_scope)
        if hasattr(self, "_btn_config_preset_load"):
            self._btn_config_preset_load.setEnabled(has_existing)
        if hasattr(self, "_btn_config_preset_delete"):
            self._btn_config_preset_delete.setEnabled(has_existing)
        self._refresh_recent_calibration_button()


    def _refresh_config_preset_controls(self):

        combo = getattr(self, "_config_preset_combo", None)
        if combo is None:
            return

        scope = self._current_config_preset_scope()
        names = list_config_presets(*scope) if scope is not None else []
        current_text = self._current_config_preset_name()

        combo.blockSignals(True)
        combo.clear()
        if names:
            combo.addItems(names)
        if current_text:
            combo.setEditText(current_text)
        elif names:
            combo.setCurrentIndex(0)
        combo.blockSignals(False)

        self._update_config_preset_action_state(names=names)

        placeholder_key = (
            "CONFIG_PRESET_NAME_PLACEHOLDER"
            if scope is not None else "CONFIG_PRESET_DISABLED_HINT"
        )
        self._set_config_preset_placeholder(tr(placeholder_key))


    def _on_save_config_preset(self):

        scope = self._current_config_preset_scope()
        if scope is None:
            QMessageBox.warning(self, tr("CONFIG_PRESET_TITLE"), tr("CONFIG_PRESET_SCOPE_REQUIRED"))
            return

        preset_name = self._current_config_preset_name()
        if not preset_name:
            QMessageBox.warning(self, tr("CONFIG_PRESET_TITLE"), tr("CONFIG_PRESET_NAME_REQUIRED"))
            return

        values = self._collect_config_panel_values()
        if not values:
            QMessageBox.warning(self, tr("CONFIG_PRESET_TITLE"), tr("CONFIG_PRESET_EMPTY_PANEL"))
            return

        existing = load_config_preset(scope[0], scope[1], preset_name)
        if existing is not None:
            reply = QMessageBox.question(
                self,
                tr("CONFIG_PRESET_TITLE"),
                tr("CONFIG_PRESET_OVERWRITE", preset_name),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        save_config_preset(scope[0], scope[1], preset_name, values)
        self._save_recent_calibration()
        self._refresh_config_preset_controls()
        self._config_preset_combo.setEditText(preset_name)
        self.log(tr("LOG_CONFIG_PRESET_SAVED", preset_name))


    def _on_load_config_preset(self):

        scope = self._current_config_preset_scope()
        if scope is None:
            QMessageBox.warning(self, tr("CONFIG_PRESET_TITLE"), tr("CONFIG_PRESET_SCOPE_REQUIRED"))
            return

        preset_name = self._current_config_preset_name()
        if not preset_name:
            QMessageBox.warning(self, tr("CONFIG_PRESET_TITLE"), tr("CONFIG_PRESET_NAME_REQUIRED"))
            return

        values = load_config_preset(scope[0], scope[1], preset_name)
        if values is None:
            QMessageBox.warning(self, tr("CONFIG_PRESET_TITLE"), tr("CONFIG_PRESET_MISSING", preset_name))
            self._refresh_config_preset_controls()
            return

        current_keys = set(self._current_config_widget_keys())
        compatible_values = {
            key: value for key, value in values.items()
            if key in current_keys
        }
        if not compatible_values:
            QMessageBox.warning(self, tr("CONFIG_PRESET_TITLE"), tr("CONFIG_PRESET_INCOMPATIBLE", preset_name))
            return

        self._apply_best_config(compatible_values)
        self.log(tr("LOG_CONFIG_PRESET_LOADED", preset_name))


    def _on_delete_config_preset(self):

        scope = self._current_config_preset_scope()
        if scope is None:
            QMessageBox.warning(self, tr("CONFIG_PRESET_TITLE"), tr("CONFIG_PRESET_SCOPE_REQUIRED"))
            return

        preset_name = self._current_config_preset_name()
        if not preset_name:
            QMessageBox.warning(self, tr("CONFIG_PRESET_TITLE"), tr("CONFIG_PRESET_NAME_REQUIRED"))
            return

        existing = load_config_preset(scope[0], scope[1], preset_name)
        if existing is None:
            QMessageBox.warning(self, tr("CONFIG_PRESET_TITLE"), tr("CONFIG_PRESET_MISSING", preset_name))
            self._refresh_config_preset_controls()
            return

        reply = QMessageBox.question(
            self,
            tr("CONFIG_PRESET_TITLE"),
            tr("CONFIG_PRESET_DELETE_CONFIRM", preset_name),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        delete_config_preset(scope[0], scope[1], preset_name)
        self._refresh_config_preset_controls()
        self._config_preset_combo.setEditText("")
        self.log(tr("LOG_CONFIG_PRESET_DELETED", preset_name))


    def _collect_config_panel_values(self):

        values = {}

        for row in range(self._config_form.rowCount()):

            item = self._config_form.itemAt(row, QFormLayout.FieldRole)

            if item is None:

                item = self._config_form.itemAt(row, QFormLayout.SpanningRole)

            widget = item.widget() if item is not None else None

            if widget is None:

                continue

            key = widget.property("config_key")

            if not key:

                continue

            if isinstance(widget, QComboBox):

                values[key] = widget.currentText()

            elif isinstance(widget, QDoubleSpinBox):

                values[key] = widget.value()

            elif isinstance(widget, QSpinBox):

                values[key] = widget.value()

            elif isinstance(widget, QCheckBox):

                values[key] = widget.isChecked()

            elif isinstance(widget, QLineEdit):

                values[key] = widget.text()

        return values


    def _build_run_config(self):

        config = None

        if self._current_technique == "dsc":

            from polynexus.core.dsc_engine.config import DSCConfig

            config = DSCConfig()

            if hasattr(self, '_dsc_dhm0_input'):

                dhm0 = self._dsc_dhm0_input.value()

                if dhm0 > 0:

                    config.user_DHm0 = dhm0

            if hasattr(self, '_dsc_mass_input'):

                config.mass_mg = self._dsc_mass_input.value()

        elif self._current_technique == "saxs":

            from polynexus.core.saxs_engine.config import SAXSConfig

            config = SAXSConfig()
            current_file = str(self._current_filepath or "").strip()
            current_technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
            current_submodule = str(getattr(self, "_current_submodule_id", "") or "").strip()
            current_input_mode = str(getattr(self, "_current_input_mode", "") or "").strip().lower()
            sample_id = str(getattr(self, "_current_sample_id", "") or "").strip()
            batch_id = str(getattr(self, "_current_batch_id", "") or "").strip()
            batch_label = str(getattr(self, "_current_batch_label", "") or "").strip()
            sample_name = str(getattr(self, "_current_sample_name", "") or "").strip()
            context = {
                "file_path": current_file,
                "source_name": Path(current_file).name if current_file else "",
                "technique": current_technique,
                "submodule": current_submodule,
                "input_mode": current_input_mode,
                "sample_id": sample_id,
                "sample_name": sample_name,
                "batch_id": batch_id,
                "batch_label": batch_label,
            }
            if sample_id or batch_id:
                context["sample"] = {
                    "sample_id": sample_id,
                    "sample_name": sample_name,
                }
                context["batch"] = {
                    "batch_id": batch_id,
                    "batch_label": batch_label,
                    "file_path": current_file,
                }
            if batch_id:
                try:
                    db = self._ensure_sample_db()
                    batch = db.get_batch(batch_id)
                    if isinstance(batch, dict) and batch:
                        condition_values = batch.get("condition_values")
                        if isinstance(condition_values, dict) and condition_values:
                            context["condition_values"] = dict(condition_values)
                        context["batch"].update({
                            "condition_type": str(batch.get("condition_type", "") or ""),
                            "condition_values": dict(condition_values or {}) if isinstance(condition_values, dict) else {},
                        })
                except Exception:
                    logger.warning("Failed to load sample batch context for SAXS config.", exc_info=True)
            if sample_id:
                try:
                    db = self._ensure_sample_db()
                    sample = db.get_sample(sample_id)
                    if isinstance(sample, dict) and sample:
                        sample_meta = sample.get("metadata")
                        if isinstance(sample_meta, dict) and sample_meta:
                            context["sample"]["metadata"] = dict(sample_meta)
                except Exception:
                    logger.warning("Failed to load sample metadata for SAXS config.", exc_info=True)
            config.condition_context = context

        elif self._current_technique == "waxs":

            from polynexus.core.waxs_engine.config import WAXSConfig

            config = WAXSConfig()

        panel_values = self._collect_config_panel_values()

        if panel_values:

            if config is None:

                config = panel_values

            else:

                for key, value in panel_values.items():

                    if hasattr(config, key):
                        if key == "crystallinity":
                            try:
                                text_value = str(value).strip()
                                value = float(text_value) if text_value else float("nan")
                            except (TypeError, ValueError):
                                value = float("nan")
                        elif key == "T_melt_expected":
                            try:
                                text_value = str(value).strip()
                                value = float(text_value) if text_value else None
                            except (TypeError, ValueError):
                                value = None

                        setattr(config, key, value)

        return config



    def _build_config_for_technique(self, technique):

        while self._config_form.rowCount() > 0:

            self._config_form.removeRow(0)

        if technique == "dsc":

            tg = QComboBox()

            tg.addItems(["half_height", "inflection", "onset", "fictive"])

            self._config_form.addRow(tr("CONFIG_DSC_TG_METHOD"), tg)

            bl = QComboBox()

            bl.addItems(["auto", "linear", "tangential", "polynomial", "spline"])

            self._config_form.addRow(tr("CONFIG_DSC_BASELINE"), bl)

            from PySide6.QtWidgets import QDoubleSpinBox

            self._dsc_dhm0_input = QDoubleSpinBox()

            self._dsc_dhm0_input.setRange(0, 999)

            self._dsc_dhm0_input.setValue(230)

            self._dsc_dhm0_input.setSuffix(" J/g")

            self._dsc_dhm0_input.setToolTip(tr("DSC_DHM0_TOOLTIP"))

            self._config_form.addRow(tr("CONFIG_DSC_HM0"), self._dsc_dhm0_input)

            self._dsc_mass_input = QDoubleSpinBox()

            self._dsc_mass_input.setRange(0.01, 999)

            self._dsc_mass_input.setValue(1.0)

            self._dsc_mass_input.setSuffix(" mg")

            self._dsc_mass_input.setDecimals(3)

            self._config_form.addRow(tr("CONFIG_DSC_SAMPLE_MASS"), self._dsc_mass_input)

        elif technique == "waxs":

            pf = QComboBox()

            pf.addItems(["pseudo_voigt", "gaussian", "lorentzian", "pearson_vii"])

            self._config_form.addRow(tr("CONFIG_WAXS_PEAK_FUNCTION"), pf)

            bg = QComboBox()

            bg.addItems(["polynomial", "spline", "chebyshev", "linear"])

            self._config_form.addRow(tr("CONFIG_WAXS_BACKGROUND"), bg)

            am = QComboBox()

            am.addItems(["spline", "polynomial", "manual"])

            self._config_form.addRow(tr("CONFIG_WAXS_AMORPHOUS"), am)

        elif technique == "saxs":

            im = QComboBox()

            im.addItems(["pyFAI", "manual"])

            self._config_form.addRow(tr("CONFIG_SAXS_INTEGRATION"), im)

            bs = QComboBox()

            bs.addItems(["subtract", "normalize", "none"])

            self._config_form.addRow(tr("CONFIG_SAXS_BACKGROUND"), bs)

        else:

            lbl = QLabel(tr("CONFIG_BASIC_ONLY"))

            lbl.setStyleSheet(f"color: {C_TEXT_MUTED}; padding: 8px;")

            self._config_form.addRow(lbl)

        self._refresh_config_preset_controls()



    def _set_input_path(self, path, is_dir=False, input_mode=None, *, clear_sample_context=True):

        self._current_filepath = path
        mode = str(input_mode or "").strip().lower()
        self._current_input_mode = mode or ("directory" if is_dir else "")

        if clear_sample_context:
            self._clear_sample_batch_context()

        self._path_input.setText(path)

        name = os.path.basename(path.rstrip('/\\'))

        self._project_label.setText(name if name else path)

        self._add_recent(path)

        self._update_workspace_context()



    def _apply_import_selection(
        self,
        path,
        *,
        is_dir=False,
        input_mode="",
        technique="",
        submodule="",
        update_last_dir=True,
    ):

        if update_last_dir:
            self._save_last_dir(path)

        self._set_input_path(path, is_dir=is_dir, input_mode=input_mode, clear_sample_context=True)

        technique_key = str(technique or "").strip().lower()
        submodule_key = str(submodule or "").strip()

        if not technique_key and submodule_key:
            technique_key = submodule_key.split(".", 1)[0].lower()

        self._current_submodule_id = ""

        if technique_key:
            self._on_technique_selected(technique_key)
            btn = self._nav_buttons.get(technique_key)
            if btn:
                btn.setChecked(True)

        if submodule_key:
            sub_btn = self._nav_buttons.get(submodule_key)
            if sub_btn:
                sub_btn.setChecked(True)
            self._on_submodule_selected(technique_key or self._current_technique, submodule_key)
        else:
            self._update_workspace_context()

    def _import_target_summary(self, path, *, input_mode=""):

        mode = str(input_mode or "").strip().lower()
        parts = []
        mode_text = _import_mode_text(mode)
        if mode_text:
            parts.append(mode_text)
        name = os.path.basename(str(path or "").rstrip("/\\"))
        parts.append(name or str(path or ""))
        return " | ".join(part for part in parts if part)


    def _apply_import_suggestion(self, suggestion: ImportSuggestion):

        self._apply_import_selection(
            suggestion.path,
            is_dir=suggestion.is_dir,
            input_mode=suggestion.input_mode,
            technique=suggestion.technique,
            submodule=suggestion.submodule,
        )

        summary = []
        if suggestion.technique:
            summary.append(TECHNIQUE_LABELS.get(suggestion.technique, suggestion.technique.upper()))
        if suggestion.submodule:
            summary.append(self._history_submodule_text(suggestion.submodule) or suggestion.submodule)
        if suggestion.input_mode:
            summary.append(_import_mode_text(suggestion.input_mode))
        reason = _format_import_suggestion_reason(suggestion.reason)
        if reason and reason != tr("IMPORT_SUGGESTION_AUTO"):
            summary.append(reason)
        message_key = "LOG_IMPORT_SETUP_APPLIED" if suggestion.reason == "manual" else "LOG_IMPORT_SUGGESTION_APPLIED"
        self.log(tr(message_key, " | ".join(summary) or suggestion.path))


    def _import_submodule_options(self):

        from ..core.submodule_registry import get_submodule_registry

        options = {}
        for technique, specs in get_submodule_registry().items():
            technique_key = str(technique or "").strip().lower()
            if not technique_key or technique_key == "joint":
                continue
            for spec in specs:
                submodule_id = str(getattr(spec, "id", "") or "").strip()
                if not submodule_id:
                    continue
                label = self._history_submodule_text(submodule_id) or str(getattr(spec, "label", "") or submodule_id)
                input_mode = str(getattr(spec, "input_mode", "") or "").strip()
                options.setdefault(technique_key, []).append((submodule_id, label, input_mode))
        return options


    def _confirm_import_suggestion(self, suggestion: ImportSuggestion):

        dialog = ImportSuggestionDialog(
            suggestion.path,
            suggestion.is_dir,
            suggestion,
            self._import_submodule_options(),
            parent=self,
        )
        if dialog.exec() != QDialog.Accepted:
            return None

        technique = dialog.selected_technique()
        submodule = dialog.selected_submodule()
        mode = dialog.selected_mode()
        return ImportSuggestion(
            path=suggestion.path,
            is_dir=suggestion.is_dir,
            technique=technique,
            submodule=submodule,
            input_mode=mode,
            reason=suggestion.reason,
        )


    def _choose_import_manually(self, path, *, is_dir=False):

        suggestion = ImportSuggestion(
            path=path,
            is_dir=is_dir,
            technique="",
            submodule="",
            input_mode="directory" if is_dir else "single",
            reason="manual",
        )
        return self._confirm_import_suggestion(suggestion)


    def _handle_import_candidate(self, path, *, is_dir=False, source="browse"):

        suggestion = suggest_import(path, is_dir=is_dir)
        if suggestion and suggestion.is_meaningful and source in {"browse", "drop"}:
            confirmed = self._confirm_import_suggestion(suggestion)
            if confirmed is not None:
                self._apply_import_suggestion(confirmed)
                return
        elif source in {"browse", "drop"}:
            manual = self._choose_import_manually(path, is_dir=is_dir)
            if manual is not None:
                self._apply_import_suggestion(manual)
                return

        fallback_mode = "directory" if is_dir else "single"
        self._apply_import_selection(
            path,
            is_dir=is_dir,
            input_mode=fallback_mode,
        )
        if source in {"browse", "drop"}:
            self.log(tr("LOG_IMPORT_BASIC_APPLIED", self._import_target_summary(path, input_mode=fallback_mode)))


    def _browse_file(self):

        path, _ = QFileDialog.getOpenFileName(

            self, tr("FILE_DIALOG_DATA"), self._get_last_dir(),

            _data_file_dialog_filter()

        )

        if path:

            self._handle_import_candidate(path, is_dir=False, source="browse")



    def _browse_folder(self):

        path = QFileDialog.getExistingDirectory(self, tr("FILE_DIALOG_FOLDER"), self._get_last_dir())

        if path:

            self._handle_import_candidate(path, is_dir=True, source="browse")



    def _browse_output(self):

        path = QFileDialog.getExistingDirectory(self, tr("FILE_DIALOG_DIR"), self._get_last_dir())

        if path:

            self._save_last_dir(path)
            self._output_dir = path

            self._output_input.setText(path)

            self._save_settings()



    def _add_recent(self, path):

        if path in self._recent_projects:

            self._recent_projects.remove(path)

        self._recent_projects.insert(0, path)

        self._recent_projects = self._recent_projects[:10]

        self._save_settings()

        self._refresh_recent_list()



    def _refresh_recent_list(self):

        self._recent_list.clear()

        for p in self._recent_projects:

            item = QListWidgetItem(os.path.basename(p.rstrip('/\\')) or p)

            item.setToolTip(p)

            self._recent_list.addItem(item)

        self._recent_list_copy_button.setEnabled(bool(self._recent_projects))



    def _open_recent(self, item):

        idx = self._recent_list.row(item)

        if 0 <= idx < len(self._recent_projects):

            path = self._recent_projects[idx]

            if os.path.exists(path):

                is_dir = os.path.isdir(path)

                self._set_input_path(path, is_dir=is_dir, input_mode="directory" if is_dir else "")

                self.log(tr("LOG_OPENED_PATH", path))



    def _copy_recent_projects_to_clipboard(self):

        recent_list = getattr(self, "_recent_list", None)
        if recent_list is None:
            return

        selected = [item.toolTip() or item.text() for item in recent_list.selectedItems()]
        selected = [str(path).strip() for path in selected if str(path or "").strip()]
        if not selected:
            selected = [str(path).strip() for path in getattr(self, "_recent_projects", []) if str(path).strip()]
        if selected:
            QApplication.clipboard().setText("\n".join(selected))


    def _run_analysis(self):

        if not self._current_technique:

            self.log(tr("LOG_NO_TECHNIQUE")); return

        if self._current_technique == "joint":

            self._run_joint_hub()

            return

        if not self._current_filepath:

            self.log(tr("LOG_NO_DATA_FILE")); return



        # Always use a subdirectory for output to avoid mixing

        # results with raw data files.

        if os.path.isdir(self._current_filepath):

            # Batch: output goes to <folder>/polynexus_output/

            self._output_dir = os.path.join(

                self._current_filepath, "polynexus_output")

        else:

            # Single file: output goes next to the file

            self._output_dir = os.path.join(

                os.path.dirname(self._current_filepath),

                "polynexus_output")



        os.makedirs(self._output_dir, exist_ok=True)

        self._analysis_warning_count_before = self._read_warning_count()

        if not self._validate_calibration_inputs():
            return
        if not self._validate_mask_inputs():
            return

        self._save_recent_calibration()



        if os.path.isdir(self._current_filepath):

            self._run_batch()

        else:

            self._run_single()


    def _run_joint_hub(self):

        hub = getattr(self, "_joint_hub", None)

        if hub is None:

            self.log(tr("LOG_JOINT_HUB_UNAVAILABLE"))

            return

        rows = hub.selected_rows()

        if not rows:

            self.log(tr("LOG_JOINT_SELECT_BATCH"))

            return

        if hasattr(self, "_output_input") and self._output_input.text().strip():

            self._output_dir = self._output_input.text().strip()

        if not self._output_dir:

            self._output_dir = os.path.join(os.getcwd(), "polynexus_joint_output")

        os.makedirs(self._output_dir, exist_ok=True)

        self._btn_run.setEnabled(False)

        self._btn_run.setText(tr("BTN_RUNNING"))

        self._progress.setVisible(True)

        start_progress_animation(self._progress)

        self._set_running_ui(True, tr("WORKFLOW_RUNNING_JOINT"))

        self._joint_worker = JointHubWorker(rows, self._output_dir)
        self._joint_worker.finished.connect(self._on_joint_hub_finished)
        self._joint_worker.error_msg.connect(self._on_joint_hub_error)
        self._joint_worker.start()


    def _on_joint_hub_finished(self, report):
        stop_progress_animation(self._progress)
        self._progress.setVisible(False)

        self._set_running_ui(False)

        self._btn_run.setText(tr("BTN_GENERATE_OVERVIEW"))

        self._btn_run.setEnabled(True)

        hub = getattr(self, "_joint_hub", None)

        self._btn_run.setEnabled(hub is not None and hub.has_selection())

        self._joint_report = report
        self._results["joint"] = report
        self._save_joint_hub_artifacts(report)
        self._display_joint_report(report)
        self._populate_plots()
        self._tabs.setCurrentIndex(2)
        self._btn_replot.setEnabled(False)
        self._update_workspace_context()
        self.log(tr("LOG_JOINT_OVERVIEW_DONE", report.get("summary", "")))

        interesting = [
            v for v in report.get("validations", [])
            if v.get("severity") in {"WARN", "ERROR"}
        ]
        for item in interesting[:8]:
            severity = str(item.get("severity") or "")
            message = str(item.get("message") or "")
            if severity == "ERROR":
                self.log(tr("LOG_JOINT_VALIDATION_ERROR", message))
            else:
                self.log(tr("LOG_JOINT_VALIDATION_WARN", message))
        if len(interesting) > 8:
            self.log(tr("LOG_JOINT_VALIDATION_MORE", len(interesting) - 8))


    def _display_joint_report(self, report):

        self._update_joint_diagnostics(report)

        rows = report.get("rows", [])

        cols = [
            tr("JOINT_COL_SAMPLE"),
            tr("JOINT_COL_BATCH"),
            tr("JOINT_COL_CONDITION"),
            tr("JOINT_COL_TECHNIQUES"),
            tr("JOINT_COL_ANALYSIS"),
            tr("JOINT_COL_ALERTS"),
        ]

        self._results_table.setRowCount(len(rows))

        self._results_table.setColumnCount(len(cols))

        self._results_table.setHorizontalHeaderLabels(cols)

        for i, row in enumerate(rows):

            values = [
                row.get("sample", ""),
                row.get("batch", ""),
                row.get("condition", ""),
                row.get("techniques", ""),
                row.get("opportunities", ""),
                row.get("alerts", ""),
            ]

            for j, value in enumerate(values):

                self._set_results_item(i, j, value)

        self._apply_results_table_layout()


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

        write_csv(os.path.join(data_dir, "joint_hub_validations.csv"), report.get("validations", []))

        try:

            import pandas as pd

            from ..core.joint.plotters import (
                plot_crystallinity_comparison,
                plot_ir_vs_dsc_xc,
                plot_tm_vs_long_period,
                plot_timeline_alignment,
                plot_xc_vs_crystallite_size,
            )

            df = pd.DataFrame(report.get("rows", []))

            if not df.empty:

                cryst = pd.DataFrame({
                    "dsc_Xc": df.get("dsc_Xc_pct"),
                    "waxs_Xc": df.get("waxs_Xc_pct"),
                    "saxs_Xc": df.get("saxs_Xc_pct"),
                })

                for t1, t2 in [("dsc", "waxs"), ("dsc", "saxs"), ("waxs", "saxs")]:

                    if f"{t1}_Xc" in cryst and f"{t2}_Xc" in cryst:

                        cryst[f"{t1}_{t2}_diff"] = cryst[f"{t1}_Xc"] - cryst[f"{t2}_Xc"]

                if cryst.notna().any().any():

                    buf = plot_crystallinity_comparison(cryst)

                    with open(os.path.join(figures_dir, "Fig-JointHub_crystallinity.png"), "wb") as fh:

                        fh.write(buf.getvalue())

                tm_l = df[["Tm_C", "L_nm"]].dropna() if {"Tm_C", "L_nm"}.issubset(df.columns) else pd.DataFrame()

                if len(tm_l) >= 1:

                    buf = plot_tm_vs_long_period(tm_l)

                    with open(os.path.join(figures_dir, "Fig-JointHub_tm_vs_long_period.png"), "wb") as fh:

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

                    with open(os.path.join(figures_dir, "Fig-JointHub_xc_vs_crystallite_size.png"), "wb") as fh:

                        fh.write(buf.getvalue())

                ir_d = (
                    df[["IR_CI", "DSC_Xc"]]
                    .dropna()
                    if {"IR_CI", "DSC_Xc"}.issubset(df.columns)
                    else pd.DataFrame()
                )

                if len(ir_d) >= 1:

                    buf = plot_ir_vs_dsc_xc(ir_d)

                    if buf is not None:

                        with open(os.path.join(figures_dir, "Fig-JointHub_ir_vs_dsc_xc.png"), "wb") as fh:

                            fh.write(buf.getvalue())

                timeline_df = None
                if {"shared_condition_value", "param_key", "value"}.issubset(df.columns):
                    timeline_df = df[["shared_condition_value", "param_key", "value", "batch_id", "batch_label", "sample_id", "sample_name", "technique"]].copy()
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
                        technique = str(row.get("techniques", "") or "").split(",")[0].strip().lower()
                        for key in ["Tm_C", "L_nm", "dsc_Xc_pct", "waxs_Xc_pct", "saxs_Xc_pct", "lc_nm", "D_Scherrer_nm"]:
                            value = row.get(key)
                            try:
                                numeric_value = float(value)
                            except Exception:
                                continue
                            if math.isnan(numeric_value):
                                continue
                            timeline_rows.append({
                                "shared_condition_value": condition_value,
                                "param_key": key,
                                "value": numeric_value,
                                "batch_id": row.get("batch_id", ""),
                                "batch_label": row.get("batch", ""),
                                "sample_id": row.get("sample_id", ""),
                                "sample_name": row.get("sample", ""),
                                "technique": technique,
                            })
                    timeline_df = pd.DataFrame(timeline_rows) if timeline_rows else pd.DataFrame()

                if timeline_df is not None and not timeline_df.empty:
                    buf = plot_timeline_alignment(timeline_df)
                    if buf is not None:
                        with open(os.path.join(figures_dir, "Fig-JointHub_timeline_alignment.png"), "wb") as fh:
                            fh.write(buf.getvalue())

        except Exception as exc:

            self.log(tr("LOG_JOINT_FIG_SKIP", exc))
            logger.warning("Failed to generate joint analysis figures.", exc_info=True)



    def _run_single(self):

        # Check file-technique compatibility
        self._set_results_summary("")
        self._set_results_export_control_visible(False)
        self._set_results_copy_control_visible(False)
        self._clear_results_table_default_order()

        submodule_id = getattr(self, '_current_submodule_id', None)
        engine = get_engine(self._current_technique, submodule_id=submodule_id)

        if engine and self._current_filepath:
            try:
                check_file_format(self._current_technique, self._current_filepath)
            except ValueError as e:
                logger.warning("File format validation failed: %s", e)
                QMessageBox.warning(self, tr("FILE_FORMAT_UNSUPPORTED"), tr("FILE_FORMAT_UNSUPPORTED_DETAIL", e))
                return

        if engine and self._current_filepath:

            ok, msg = engine.check_file_compatibility(self._current_filepath)

            if not ok:

                self.log(tr("LOG_WARNING_DETAIL", msg))

                reply = QMessageBox.warning(

                    self, tr("DIALOG_MISMATCH_TITLE"),

                    tr("DIALOG_MISMATCH_MSG", msg),

                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No

                )

                if reply == QMessageBox.No:

                    return

        self.log(tr("LOG_RUN_MODE_SINGLE", os.path.basename(self._current_filepath)))


        self._btn_run.setEnabled(False)

        self._btn_run.setText(tr("BTN_RUNNING"))

        self._progress.setVisible(True)

        start_progress_animation(self._progress)

        self._set_running_ui(True, tr("WORKFLOW_RUNNING_SINGLE"))

        # Build technique-specific config from UI

        config = self._build_run_config()

        self._worker = AnalysisWorker(

            self._current_technique, self._current_filepath, self._output_dir,

            config=config, submodule_id=submodule_id)

        self._worker.log_msg.connect(self.log)

        self._worker.finished.connect(self._on_finished)

        self._worker.error_msg.connect(self._on_error)

        self._worker.start()



    def _run_batch(self):

        fp = self._current_filepath
        submodule_id = getattr(self, '_current_submodule_id', None)
        self._set_results_summary("")

        # Techniques that support directory-oriented runs.
        native_directory_run = (
            self._current_technique in ("saxs", "waxs")
            or self._current_technique == "nmr"
            or submodule_id in ("dsc.isothermal", "dsc.nonisothermal", "ir.temperature_2d")
        )
        if native_directory_run:
            mode_label = tr("IMPORT_MODE_SEQUENCE") if str(getattr(self, "_current_input_mode", "") or "").strip().lower() == "sequence" else tr("IMPORT_MODE_DIRECTORY")
            self.log(tr("LOG_RUN_MODE_NATIVE_DIRECTORY", mode_label, os.path.basename(fp.rstrip("/\\"))))
            self._batch_list.clear()
            self._batch_list.setVisible(False)
            self._update_batch_list_copy_button()
            self._btn_run.setEnabled(False)
            self._btn_run.setText(tr("BTN_RUNNING"))
            self._progress.setVisible(True)
            start_progress_animation(self._progress)
            running_label = (
                tr("WORKFLOW_RUNNING_SEQUENCE")
                if str(getattr(self, "_current_input_mode", "") or "").strip().lower() == "sequence"
                else tr("WORKFLOW_RUNNING_DIRECTORY")
            )
            self._set_running_ui(True, running_label)
            self._worker = AnalysisWorker(
                self._current_technique, fp, self._output_dir,
                config=self._build_run_config(), submodule_id=submodule_id)
            self._worker.log_msg.connect(self.log)
            self._worker.finished.connect(self._on_finished)
            self._worker.error_msg.connect(self._on_error)
            self._worker.start()
            return

        exts = {'.edf', '.csv', '.txt', '.dat', '.xlsx', '.xls', '.001', '.raw', '.spa', '.jdf', '.bin'}

        file_list = sorted([

            os.path.join(fp, f) for f in os.listdir(fp)

            if os.path.isfile(os.path.join(fp, f))

            and os.path.splitext(f)[1].lower() in exts

        ])

        if not file_list:

            self.log(tr("LOG_NO_SUPPORTED_FILES")); return

        self.log(tr("LOG_RUN_MODE_BATCH", len(file_list), os.path.basename(fp.rstrip("/\\"))))

        self._btn_run.setEnabled(False)

        self._btn_run.setText(tr("BTN_BATCH"))

        self._progress.setVisible(True)

        self._progress.setRange(0, len(file_list))

        self._progress.setValue(0)

        self._set_running_ui(True, tr("WORKFLOW_RUNNING_BATCH"))

        self._batch_list.clear()

        self._batch_list.setVisible(True)
        self._update_batch_list_copy_button()

        for f in file_list:

            self._batch_list.addItem(os.path.basename(f))

        self._batch_worker = BatchWorker(

            self._current_technique, file_list, self._output_dir,
            config=self._build_run_config(), submodule_id=submodule_id)

        self._batch_worker.log_msg.connect(self.log)

        self._batch_worker.progress.connect(lambda c, t: self._progress.setValue(c))

        self._batch_worker.file_done.connect(self._on_batch_file_done)

        self._batch_worker.batch_finished.connect(self._on_batch_finished)

        self._batch_worker.error_msg.connect(self._on_error)

        self._batch_worker.start()



    

    def _replot(self):

        """Re-generate figures only (skip load/preprocess/analyze)."""

        if not self._current_technique:

            self.log(tr("LOG_NO_TECHNIQUE")); return

        if not self._current_filepath:

            self.log(tr("LOG_NO_DATA_FILE")); return

        if not self._output_dir:

            self.log(tr("LOG_NO_OUTPUT_DIR")); return

        self._btn_replot.setEnabled(False)

        self._btn_replot.setText(tr("BTN_REPLOTTING"))

        if hasattr(self, "_workflow_metric_state"):

            self._workflow_metric_state.setText(tr("BTN_REPLOTTING"))

        # Build technique-specific config from UI

        config = self._build_run_config()

        submodule_id = getattr(self, '_current_submodule_id', None)

        cached_engine = self._engine_cache.get(self._current_technique)

        if cached_engine is None:

            self.log(tr("LOG_REPLOT_CACHE_MISS"))

        self._worker = AnalysisWorker(

            self._current_technique, self._current_filepath, self._output_dir,

            config=config, submodule_id=submodule_id, engine=cached_engine)

        self._worker.log_msg.connect(self.log)

        self._worker.finished.connect(self._on_replot_finished)

        self._worker.error_msg.connect(self._on_error)

        # Override: use skip_to="plot"

        self._worker.skip_to = "plot" if cached_engine is not None else None

        self._worker.start()

        if cached_engine is not None:

            self.log(tr("LOG_REPLOT_START_CACHED"))

        else:

            self.log(tr("LOG_REPLOT_START_FALLBACK"))



    def _on_replot_finished(self, result):

        self._btn_replot.setEnabled(True)

        self._btn_replot.setText(tr("BTN_REPLOT"))

        self._set_running_ui(False)

        self._results[self._current_technique] = result

        if self._worker is not None and getattr(self._worker, 'engine', None) is not None:

            self._engine_cache[self._current_technique] = self._worker.engine

        self._populate_plots()
        self._update_results_compare_panel()
        self._update_results_confirm_panel()

        self._tabs.setCurrentIndex(3)  # Switch to Plots tab

        self.log(tr("LOG_REPLOT_DONE"))



    

    def _retranslate_ui(self):

        """Refresh all UI text after language change.



        Each widget access is wrapped in a try/except to survive

        C++ object deletion (e.g. tabs being removed by Qt).

        """

        def _safe_set(widget, text):

            try:

                widget.setText(text)

            except Exception:

                logger.warning("Failed to update widget text during retranslate.", exc_info=True)



        def _safe_set_title(w, title):

            try:

                w.setWindowTitle(title)

            except Exception:

                logger.warning("Failed to update window title during retranslate.", exc_info=True)



        _safe_set_title(self, tr("WINDOW_TITLE"))



        # Menu bar

        try:

            for action, key in [

                (self._act_open, 'ACTION_OPEN'),

                (self._act_export, 'ACTION_EXPORT'),

                (self._act_settings, 'ACTION_SETTINGS'),

                (self._act_quit, 'ACTION_QUIT'),

                (self._act_toggle_sidebar, 'ACTION_TOGGLE_SIDEBAR'),

                (self._act_toggle_theme, 'ACTION_TOGGLE_THEME'),

                (self._act_toggle_lang, 'ACTION_TOGGLE_LANG'),

                (self._act_about, 'ACTION_ABOUT'),

            ]:

                _safe_set(action, tr(key))

            self._menu_file.setTitle(tr("MENU_FILE"))

            self._menu_edit.setTitle(tr("MENU_EDIT"))

            self._menu_view.setTitle(tr("MENU_VIEW"))

            self._menu_help.setTitle(tr("MENU_HELP"))

        except Exception:
            logger.warning("Failed to update menu bar labels during retranslate.", exc_info=True)

        try:

            self._statusbar.showMessage(tr("STATUSBAR_READY"))

        except Exception:
            logger.warning("Failed to update ready status message during retranslate.", exc_info=True)



        # Topbar buttons (these always exist)

        for w, key in [(self._btn_run, 'BTN_RUN'),

                       (self._btn_replot, 'BTN_REPLOT'),

                       (self._btn_export, 'BTN_EXPORT')]:

            _safe_set(w, tr(key))

        try:

            self._btn_replot.setToolTip(tr("REPLOT_TOOLTIP"))

        except Exception:
            logger.warning("Failed to update top-level action labels during retranslate.", exc_info=True)

        try:

            self._btn_lang.setText("\u4e2d" if get_language() != "zh" else "EN")
            self._btn_lang.setToolTip(tr("LANG_TOGGLE_TOOLTIP"))

        except Exception:
            logger.warning("Failed to retranslate optional child widgets.", exc_info=True)

        try:

            self._btn_theme.setText("\u263e" if ThemeEngine.instance().is_dark else "\u2600")

            self._btn_theme.setToolTip(tr("THEME_TOGGLE_TOOLTIP"))
            self._btn_ai_tune.setText(tr('AI_TUNING_BUTTON'))
            self._btn_results_export.setText(tr("RESULTS_EXPORT_TABLE"))
            self._btn_results_copy.setText(tr("RESULTS_COPY_TABLE"))
            self._btn_results_default_order.setText(tr("RESULTS_DEFAULT_ORDER"))
            self._btn_view_current_figure.setText(tr("PLOTS_BTN_VIEW_CURRENT"))
            self._drop_label.setText(tr("DROP_HINT"))
            self._history_tech_label.setText(tr("HISTORY_TECHNIQUE"))
            self._history_refresh_btn.setText(tr("HISTORY_REFRESH"))
            self._history_export_btn.setText(tr("HISTORY_EXPORT"))
            self._history_copy_summary_btn.setText(tr("HISTORY_COPY_SUMMARY"))
            self._history_restore_btn.setText(tr("HISTORY_RESTORE"))
            self._history_rerun_btn.setText(tr("HISTORY_RERUN"))
            self._history_confirm_btn.setText(tr("RESULTS_CONFIRM_MARK"))
            self._history_compare_btn.setText(tr("HISTORY_COMPARE"))

        except Exception:
            logger.warning("Failed to update default workspace labels during retranslate.", exc_info=True)

        try:

            if hasattr(self, "_joint_hub"):

                self._joint_hub.retranslate()

            if hasattr(self, "_sample_browser"):

                self._sample_browser.retranslate()

            if hasattr(self, "_figure_preview"):

                self._figure_preview.retranslate()

            if hasattr(self, "_figure_viewer") and self._figure_viewer is not None:

                self._figure_viewer.retranslate()

            if hasattr(self, "_chart_editor") and self._chart_editor is not None:

                self._chart_editor.retranslate()

            if hasattr(self, "action_convergence_viewer"):
                self.action_convergence_viewer.setText(tr('CONVERGENCE_DASHBOARD'))

            if hasattr(self, "_btn_convergence_viewer"):
                self._btn_convergence_viewer.setText(tr('CONVERGENCE_DASHBOARD'))

            if self._current_technique == "joint":

                self._btn_run.setText(tr("BTN_GENERATE_OVERVIEW"))

        except Exception:
            logger.warning("Failed to refresh translated group titles and history filter.", exc_info=True)

        try:

            current_label = self._project_label.text().strip() if hasattr(self, "_project_label") else ""
            project_label = tr("NO_PROJECT")
            if self._current_filepath:
                if current_label and not _is_default_project_label(current_label):
                    project_label = current_label
                else:
                    project_label = os.path.basename(self._current_filepath.rstrip("/\\")) or self._current_filepath
            self._project_label.setText(project_label)
            self._workspace_title.setText(tr("WORKSPACE_TITLE_DEFAULT"))
            self._workspace_subtitle.setText(tr("WORKSPACE_SUBTITLE_DEFAULT"))
            self._workflow_metric_data.setText(tr("WORKFLOW_NO_DATA"))
            self._workflow_metric_state.setText(tr("WORKFLOW_READY"))
            self._update_workflow_task_card()

        except Exception:
            logger.warning("Failed to update translated tab labels.", exc_info=True)

        try:

            is_zh = get_language() == "zh"

            self._log_group.setTitle(tr("GROUP_LOG"))

            self._data_source_group.setTitle(tr("GROUP_DATA_SOURCE"))

            self._output_group.setTitle(tr("GROUP_OUTPUT"))

            if hasattr(self, "_joint_diagnostics_group"):

                self._joint_diagnostics_group.setTitle(tr("GROUP_JOINT_DIAGNOSTICS"))

            self._refresh_sidebar_texts()
            if hasattr(self, "_history_filter_combo"):
                self._refresh_history()

            self._update_workspace_context()

        except Exception:
            logger.warning("Failed to refresh translated group titles and history filter.", exc_info=True)



        # Tabs

        try:

            for i, key in enumerate(["TAB_DATA", "TAB_CONFIG", "TAB_RESULTS", "TAB_PLOTS", "TAB_HISTORY"]):

                if i < self._tabs.count():

                    self._tabs.setTabText(i, tr(key))

        except Exception:
            logger.warning("Failed to update translated tab labels.", exc_info=True)



        # Optional child widgets

        for attr, key in [

            ('_sidebar_tech_label', 'SIDEBAR_TECHNIQUES'),

            ('_sidebar_recent_label', 'SIDEBAR_RECENT'),

            ('_data_file_label', 'DATA_FILE_LABEL'),

            ('_data_btn_browse', 'DATA_BTN_BROWSE'),

            ('_data_output_label', 'DATA_OUTPUT_DIR'),

            ('_config_preset_label', 'CONFIG_PRESET_LABEL'),

            ('_config_placeholder', 'CONFIG_PLACEHOLDER'),

            ('_plots_label', 'PLOTS_EMPTY'),

        ]:

            w = getattr(self, attr, None)

            if w is not None:

                _safe_set(w, tr(key))

        for attr, key in [
            ('_btn_config_preset_save', 'CONFIG_PRESET_SAVE'),
            ('_btn_config_preset_load', 'CONFIG_PRESET_LOAD'),
            ('_btn_config_preset_delete', 'CONFIG_PRESET_DELETE'),
            ('_btn_config_recent_calibration_save', 'CONFIG_RECENT_CALIBRATION_SAVE'),
            ('_btn_config_recent_calibration', 'CONFIG_RECENT_CALIBRATION_APPLY'),
        ]:
            w = getattr(self, attr, None)
            if w is not None:
                _safe_set(w, tr(key))

        try:
            self._refresh_config_preset_controls()
        except Exception:
            logger.warning("Failed to refresh config preset controls during retranslate.", exc_info=True)

        try:
            technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
            if technique in {"dsc", "waxs", "saxs"}:
                self._build_config_for_technique(technique)
        except Exception:
            logger.warning("Failed to rebuild translated manual config form during retranslate.", exc_info=True)



        # Results table header

        try:

            if hasattr(self, '_results_table'):

                self._results_table.setHorizontalHeaderLabels(

                    [tr("RESULTS_PARAM"), tr("RESULTS_VALUE")])
            if hasattr(self, "_history_table"):
                self._history_table.setHorizontalHeaderLabels(
                    [
                        tr("HISTORY_COL_TIME"),
                        tr("HISTORY_COL_TECHNIQUE"),
                        tr("HISTORY_COL_SUBMODULE"),
                        tr("HISTORY_COL_SCORE"),
                        tr("HISTORY_COL_STATUS"),
                    ]
                )

        except Exception:
            logger.warning("Failed to update translated table headers.", exc_info=True)



    def _toggle_language(self):

        new_lang = "zh" if get_language() != "zh" else "en"

        set_language(new_lang)

        self._retranslate_ui()



        # Re-polish the sidebar after translated labels change.

        sb = self.findChild(QWidget, "sidebar")

        if sb:

            sb.setVisible(True)

        self.log(tr("LOG_LANGUAGE_CHANGED", new_lang))


    def _log_analysis_diagnostics(self, result):

        technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
        validation_summary = str(getattr(result, "validation_summary", "") or "").strip()
        if validation_summary and validation_summary != "All checks passed":
            self.log(tr("LOG_ANALYSIS_VALIDATION_SUMMARY", validation_summary))

        if technique != "saxs":
            return

        if bool(getattr(result, "mask_truncated", False)):
            eff_q = getattr(result, "effective_q_min", 0.0)
            try:
                eff_q_text = f"{float(eff_q):.3f}"
            except Exception:
                eff_q_text = "0.000"
            self.log(tr("LOG_SAXS_MASK_TRUNCATED", eff_q_text))

        if bool(getattr(result, "beam_stop_contaminated", False)):
            eff_q = getattr(result, "effective_q_min", 0.0)
            try:
                eff_q_text = f"{float(eff_q):.3f}"
            except Exception:
                eff_q_text = "0.000"
            self.log(tr("LOG_SAXS_BEAMSTOP_WARNING", eff_q_text))

    def _result_mask_summary_text(self, result):

        if str(getattr(self, "_current_technique", "") or "").strip().lower() != "saxs":
            return ""

        mask_truncated = bool(getattr(result, "mask_truncated", False))
        beamstop_warning = bool(getattr(result, "beam_stop_contaminated", False))

        if not mask_truncated and not beamstop_warning:
            return ""

        eff_q = getattr(result, "effective_q_min", 0.0)
        try:
            eff_q_text = f"{float(eff_q):.3f}"
        except Exception:
            eff_q_text = "0.000"

        if mask_truncated and beamstop_warning:
            return tr("RESULTS_SUMMARY_MASK_TRUNCATED_AND_BEAMSTOP", eff_q_text)
        if mask_truncated:
            return tr("RESULTS_SUMMARY_MASK_TRUNCATED_ONLY", eff_q_text)
        return tr("RESULTS_SUMMARY_MASK_BEAMSTOP_ONLY", eff_q_text)


    def _log_run_completion_summary(self, result):

        mode = str(getattr(self, "_current_input_mode", "") or "").strip().lower()
        if mode not in {"sequence", "directory"}:
            return

        source_name = os.path.basename(str(self._current_filepath or "").rstrip("/\\")) or str(self._current_filepath or "")
        params = getattr(result, "parameters", None)
        batch_frames = 0
        if isinstance(params, dict):
            try:
                batch_frames = int(params.get("batch_frames", 0) or 0)
            except Exception:
                batch_frames = 0

        if mode == "sequence":
            if batch_frames > 1:
                self.log(tr("LOG_SEQUENCE_RUN_DONE", batch_frames, source_name))
            else:
                self.log(tr("LOG_SEQUENCE_RUN_DONE_FALLBACK", source_name))
            return

        if batch_frames > 1:
            self.log(tr("LOG_DIRECTORY_RUN_DONE", batch_frames, source_name))
        else:
            self.log(tr("LOG_DIRECTORY_RUN_DONE_FALLBACK", source_name))



    def _on_finished(self, result):

        self._btn_run.setEnabled(True)

        self._btn_run.setText(tr("BTN_RUN"))

        stop_progress_animation(self._progress)
        self._progress.setVisible(False)

        self._set_running_ui(False)

        self._results[self._current_technique] = result

        if self._worker is not None and getattr(self._worker, 'engine', None) is not None:

            self._engine_cache[self._current_technique] = self._worker.engine

        self.log(tr("LOG_ANALYSIS_DONE"))
        self._append_analysis_warning_summary()
        self._log_analysis_diagnostics(result)
        self._log_run_completion_summary(result)

        self._btn_replot.setEnabled(bool(self._output_dir))

        if hasattr(result, 'parameters') and result.parameters:

            self._display_results(result.parameters, result)

        self._populate_plots()

        self._tabs.setCurrentIndex(2)
        self._persist_analysis_run(result)
        self._update_workspace_context()
        self._update_results_compare_panel()
        self._last_ai_tuned_run = False



    def _on_joint_hub_error(self, msg):
        stop_progress_animation(self._progress)
        self._progress.setVisible(False)
        self._set_running_ui(False)
        self._btn_run.setEnabled(True)
        self._btn_run.setText(tr("BTN_GENERATE_OVERVIEW"))
        hub = getattr(self, "_joint_hub", None)
        if hub is not None:
            self._btn_run.setEnabled(hub.has_selection())
        self.log(tr("LOG_ERROR_DETAIL", msg))


    def on_ai_tune_clicked(self):
        if not self._current_technique or self._current_technique in {"joint", "samples"}:
            QMessageBox.warning(self, tr("AI_TUNING_TITLE"), tr("AI_TUNING_REQUIRE_TECH"))
            return
        if not self._current_filepath:
            QMessageBox.warning(self, tr("AI_TUNING_TITLE"), tr("AI_TUNING_REQUIRE_FILE"))
            return
        current_goal = self._current_tuning_goal()
        goal_dialog = AITuningGoalDialog(self, current_goal=current_goal)
        if goal_dialog.exec() != QDialog.Accepted:
            return
        current_goal = goal_dialog.selected_goal()
        self._current_ai_tuning_goal = current_goal
        context_summary = self._ai_tuning_context_summary()
        answer = QMessageBox.question(
            self,
            tr("AI_TUNING_TITLE"),
            tr("AI_TUNING_CONFIRM_MESSAGE", context_summary),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer != QMessageBox.Yes:
            return
        sample_name = self._infer_sample_name()
        polymer = detect_polymer_type(sample_name or "")
        defaults = load_defaults(polymer)
        self._current_polymer_type = polymer
        self._current_polymer_defaults = defaults
        logger.info(
            "AI tuning started: technique=%s sample=%s polymer_type=%s goal=%s",
            self._current_technique,
            sample_name,
            polymer,
            current_goal,
        )
        self._ai_tuning_active = True
        self._update_workflow_task_card()
        submodule_id = getattr(self, "_current_submodule_id", None)
        self._ai_progress = QProgressDialog(
            tr("AI_TUNING_PROGRESS"),
            tr("COMMON_CANCEL"),
            0,
            0,
            self,
        )
        self._ai_progress.setWindowTitle(tr("AI_TUNING_TITLE"))
        self._ai_progress.setMinimumDuration(0)
        self._ai_progress.setAutoClose(False)
        workspace_context = self._ai_tuning_workspace_context()
        workspace_context["tuning_goal"] = current_goal
        workspace_context["tuning_goal_label"] = self._ai_tuning_goal_label(current_goal)
        ai_settings = self._current_ai_settings()
        self._ai_worker = AITuneWorker(
            self._current_technique,
            self._current_filepath,
            polymer,
            rounds=5,
            submodule_id=submodule_id,
            workspace_context=workspace_context,
            ai_settings=ai_settings,
        )
        self._ai_progress.canceled.connect(self._ai_worker.cancel)
        self._ai_worker.signals.progress_msg.connect(self._on_ai_tune_progress)
        self._ai_worker.signals.finished.connect(self._on_ai_tune_finished)
        self._ai_worker.signals.error_msg.connect(self._on_ai_tune_error)
        self._ai_progress.show()
        QThreadPool.globalInstance().start(self._ai_worker)

    def _current_ai_settings(self):
        return load_ai_settings(self._settings)

    def _ai_tuning_workspace_context(self):
        current_key = str(self._current_technique or "").strip().lower()
        joint_report = self._joint_report if isinstance(self._joint_report, dict) else {}
        workspace_context = {
            "summary": self._workspace_context_summary(),
            "joint_report": joint_report,
            "current_result": self._results.get(current_key, {}) if isinstance(self._results, dict) else {},
            "work_memory": self._work_memory_payload(),
            "tuning_goal": self._current_tuning_goal(),
            "tuning_goal_label": self._ai_tuning_goal_label(self._current_tuning_goal()),
        }
        joint_ai_context = self._joint_ai_context()
        if joint_ai_context:
            workspace_context["joint_ai_context"] = joint_ai_context
        tuning_context = getattr(self, "_last_ai_tuning_context", {})
        if isinstance(tuning_context, dict) and tuning_context:
            workspace_context["tuning_context"] = tuning_context
        return workspace_context

    def _current_tuning_goal(self) -> str:
        goal = getattr(self, "_current_ai_tuning_goal", "")
        goal = str(goal or "").strip().lower()
        return goal if goal in {"symptom", "risk", "joint", "stability"} else "symptom"

    def _ai_tuning_goal_label(self, goal: str) -> str:
        goal = str(goal or "").strip().lower()
        return {
            "symptom": tr("AI_TUNING_GOAL_SYMPTOM"),
            "risk": tr("AI_TUNING_GOAL_RISK"),
            "joint": tr("AI_TUNING_GOAL_JOINT"),
            "stability": tr("AI_TUNING_GOAL_STABILITY"),
        }.get(goal, tr("AI_TUNING_GOAL_SYMPTOM"))

    def _ai_tuning_context_summary(self):
        technique = self._history_technique_text(str(self._current_technique or ""))
        submodule = self._history_submodule_text(str(getattr(self, "_current_submodule_id", "") or ""))
        source_name = os.path.basename(str(self._current_filepath or "").rstrip("/\\")) or str(self._current_filepath or "")
        mode = str(getattr(self, "_current_input_mode", "") or "").strip().lower()
        mode_text = {
            "sequence": tr("AI_TUNING_CONTEXT_SEQUENCE"),
            "directory": tr("AI_TUNING_CONTEXT_DIRECTORY"),
        }.get(mode, tr("AI_TUNING_CONTEXT_SINGLE"))
        result_summary = ""
        if hasattr(self, "_results_summary_risk_label"):
            result_summary = str(self._results_summary_risk_label.text() or "").strip()
        if not result_summary and hasattr(self, "_results_summary_label"):
            result_summary = str(self._results_summary_label.text() or "").strip()
        if not result_summary:
            result_summary = tr("AI_TUNING_CONTEXT_NO_RISK")
        goal_text = self._ai_tuning_goal_label(self._current_tuning_goal())
        previous_round = self._ai_tuning_previous_round_summary()
        tunable_summary = self._ai_tuning_tunable_summary()
        template = (
            "Technique: {}\nSub-module: {}\nInput mode: {}\nData source: {}\nCurrent result note: {}\nCurrent focus: {}\nPrevious round context:\n{}\nPlanned tuning parameters:\n{}"
            if get_language() != "zh"
            else "技术：{}\n子模块：{}\n输入模式：{}\n数据来源：{}\n当前结果提示：{}\n当前关注点：{}\n上一轮上下文：\n{}\n预定优化参数：\n{}"
        )
        return template.format(
            technique or tr("WORKFLOW_TASK_NO_TECH"),
            submodule or tr("WORKFLOW_SUBMODULE_NONE"),
            mode_text,
            source_name,
            result_summary,
            goal_text,
            previous_round,
            tunable_summary,
        )

    def _workspace_context_summary(self):
        summary_parts = []

        current_result = self._current_results_record()
        if isinstance(current_result, dict) and current_result:
            current_bits = []
            current_summary = current_result.get("results_summary") if isinstance(current_result.get("results_summary"), dict) else {}
            project_label = str(current_summary.get("project_label") or "").strip()
            if project_label:
                current_bits.append(project_label)
            current_bits.append(self._results_confirm_state_text())
            confirmed_flag = bool(current_result.get("confirmed") or current_summary.get("confirmed"))
            ai_tuned_flag = bool(current_result.get("ai_tuned") or current_summary.get("ai_tuned"))
            current_bits.append(f"confirmed={confirmed_flag}")
            current_bits.append(f"ai_tuned={ai_tuned_flag}")
            current_origin = self._current_result_origin_label()
            if current_origin:
                current_bits.append(current_origin)
            current_note = ""
            if hasattr(self, "_results_summary_risk_label"):
                current_note = str(self._results_summary_risk_label.text() or "").strip()
            if not current_note and hasattr(self, "_results_summary_label"):
                current_note = str(self._results_summary_label.text() or "").strip()
            if current_note:
                current_bits.append(current_note)
            if current_bits:
                summary_parts.append("Current result: " + " | ".join(current_bits))

        joint_report = getattr(self, "_joint_report", None)
        joint_context = self._joint_ai_context()
        if isinstance(joint_report, dict):
            joint_summary = str(joint_report.get("summary") or "").strip()
            if not joint_summary and isinstance(joint_context, dict):
                joint_summary = str(joint_context.get("summary") or "").strip()
            if joint_summary:
                summary_parts.append(tr("WORK_MEMORY_JOINT") + ": " + joint_summary)
            rows = joint_report.get("rows") if isinstance(joint_report.get("rows"), list) else []
            validations = joint_report.get("validations") if isinstance(joint_report.get("validations"), list) else []
            if rows or validations:
                if get_language() == "zh":
                    summary_parts.append(f"{len(rows)} 行，{len(validations)} 项校验")
                else:
                    summary_parts.append(f"{len(rows)} rows, {len(validations)} validations")
        elif isinstance(joint_context, dict) and joint_context:
            joint_summary = str(joint_context.get("summary") or "").strip()
            if joint_summary:
                summary_parts.append(tr("WORK_MEMORY_JOINT") + ": " + joint_summary)

        work_memory = self._work_memory_payload()
        slices = work_memory.get("slices") if isinstance(work_memory.get("slices"), list) else []
        for item in slices[:3]:
            label = str(item.get("label") or "").strip()
            detail = str(item.get("detail") or "").strip()
            if label or detail:
                summary_parts.append(f"{label}: {detail}" if label and detail else (label or detail))

        if not summary_parts:
            return tr("WORK_MEMORY_EMPTY_DETAIL")

        return "\n".join(summary_parts[:5])

    def _joint_ai_context(self):
        report = self._joint_report if isinstance(self._joint_report, dict) else {}
        context = report.get("ai_context") if isinstance(report.get("ai_context"), dict) else {}
        if context:
            return context
        tuning_context = getattr(self, "_last_ai_tuning_context", {})
        if isinstance(tuning_context, dict):
            restored_context = tuning_context.get("joint_ai_context")
            if isinstance(restored_context, dict) and restored_context:
                return restored_context
        history_context = self._current_result_history_context()
        if isinstance(history_context, dict) and history_context:
            restored_context = history_context.get("joint_ai_context") if isinstance(history_context.get("joint_ai_context"), dict) else {}
            if isinstance(restored_context, dict) and restored_context:
                return restored_context
        rows = report.get("rows") if isinstance(report.get("rows"), list) else []
        validations = report.get("validations") if isinstance(report.get("validations"), list) else []
        if not rows and not validations:
            return {}
        issue_rows = [
            item for item in validations
            if str(item.get("severity") or "").strip().upper() in {"WARN", "ERROR"}
        ]
        if not issue_rows:
            return {
                "summary": tr("JOINT_DIAG_NONE"),
                "scope": tr("WORKFLOW_TECH_JOINT"),
                "sample_count": len(rows),
                "batch_count": len(rows),
                "issue_count": 0,
                "warning_count": 0,
                "error_count": 0,
                "issue_families": [],
                "highlights": [],
                "samples": [],
                "batches": [],
                "row_count": len(rows),
            }

        family_order = []
        family_counts = {}
        for item in issue_rows:
            check = str(item.get("check") or "").strip().lower()
            if "phi_c" in check:
                family = "phi_c inconsistency"
            elif "tm_gt" in check or "/tm_" in check:
                family = "Tm bidirectional gap"
            elif "l_consistency" in check:
                family = "L consistency unstable"
            else:
                family = "cross-tech issue"
            family_counts[family] = family_counts.get(family, 0) + 1
            if family not in family_order:
                family_order.append(family)
        highlights = []
        for item in issue_rows[:3]:
            severity = str(item.get("severity") or "").strip().upper()
            sample = str(item.get("sample") or "").strip()
            batch = str(item.get("batch") or "").strip()
            check = str(item.get("check") or "").strip().rsplit("/", 1)[-1]
            message = str(item.get("message") or "").strip()
            highlight_parts = []
            if severity:
                highlight_parts.append(severity)
            sample_batch = " / ".join(part for part in [sample, batch] if part)
            if sample_batch:
                highlight_parts.append(sample_batch)
            if check:
                highlight_parts.append(check)
            if message:
                highlight_parts.append(message)
            highlights.append(
                " · ".join(highlight_parts)
            )
        sample_names = []
        batch_labels = []
        for row in rows:
            sample = str(row.get("sample") or "").strip()
            batch = str(row.get("batch") or "").strip()
            if sample and sample not in sample_names:
                sample_names.append(sample)
            if batch and batch not in batch_labels:
                batch_labels.append(batch)
        scope = "selected rows"
        if len(sample_names) == 1:
            scope = sample_names[0]
        elif sample_names:
            scope = " / ".join(sample_names[:2])
        summary = f"Cross-tech consistency for {scope}: {len([i for i in issue_rows if str(i.get('severity') or '').strip().upper() == 'ERROR'])} errors, {len([i for i in issue_rows if str(i.get('severity') or '').strip().upper() == 'WARN'])} warnings"
        if family_order:
            summary += "; focus on " + ", ".join(family_order[:3])
        if highlights:
            summary += "; example " + highlights[0]
        return {
            "summary": summary,
            "scope": scope,
            "sample_count": len(sample_names) or len(rows),
            "batch_count": len(batch_labels),
            "issue_count": len(issue_rows),
            "warning_count": len([i for i in issue_rows if str(i.get("severity") or "").strip().upper() == "WARN"]),
            "error_count": len([i for i in issue_rows if str(i.get("severity") or "").strip().upper() == "ERROR"]),
            "issue_families": family_order[:3],
            "highlights": highlights,
            "samples": sample_names[:3],
            "batches": batch_labels[:3],
            "row_count": len(rows),
        }

    def _history_context_snapshot(self, tuning_context=None, joint_context=None) -> dict:
        tuning_context = tuning_context if isinstance(tuning_context, dict) else getattr(self, "_last_ai_tuning_context", {})
        if not isinstance(tuning_context, dict):
            tuning_context = {}
        joint_context = joint_context if isinstance(joint_context, dict) else self._joint_ai_context()
        if not isinstance(joint_context, dict):
            joint_context = {}

        review_summary = str(self._result_review_summary() or "").strip()
        work_memory_summary = str(self._work_memory_summary() or "").strip()
        comparison_summary = str(self._result_comparison_summary() or "").strip()
        validation_summary = str(self._history_validation_summary(self._current_results_record()) or "").strip()

        snapshot = {
            "review_summary": review_summary,
            "work_memory_summary": work_memory_summary,
            "comparison_summary": comparison_summary,
            "validation_summary": validation_summary,
            "responsibility_boundary": self._responsibility_boundary_summary(),
            "benchmark_summary": tuning_context.get("benchmark_summary") if isinstance(tuning_context.get("benchmark_summary"), dict) else {},
            "benchmark_text": str(tuning_context.get("benchmark_text") or "").strip(),
            "tuning_goal": str(tuning_context.get("tuning_goal") or "").strip(),
            "tuning_goal_label": str(tuning_context.get("tuning_goal_label") or "").strip(),
            "stop_reason": str(tuning_context.get("stop_reason") or "").strip(),
            "remaining_risks": str(tuning_context.get("remaining_risks") or "").strip(),
            "next_goal": str(tuning_context.get("next_goal") or "").strip(),
            "tuning_context": tuning_context,
            "joint_ai_context": joint_context,
            "joint_summary": str(joint_context.get("summary") or "").strip(),
        }
        return snapshot

    def _history_context_lines(self, record) -> list[str]:
        if not isinstance(record, dict):
            return []

        summary = record.get("results_summary") if isinstance(record.get("results_summary"), dict) else {}
        if not isinstance(summary, dict):
            summary = {}

        snapshot = summary.get("history_context") if isinstance(summary.get("history_context"), dict) else {}
        if not isinstance(snapshot, dict):
            snapshot = {}

        current_lines = [
            str(snapshot.get("review_summary") or "").strip(),
            str(snapshot.get("comparison_summary") or "").strip(),
            str(snapshot.get("validation_summary") or "").strip(),
            str(snapshot.get("benchmark_text") or "").strip(),
            str(snapshot.get("work_memory_summary") or "").strip(),
            str(snapshot.get("joint_summary") or "").strip(),
            str(snapshot.get("responsibility_boundary") or "").strip(),
        ]
        tuning_context = snapshot.get("tuning_context") if isinstance(snapshot.get("tuning_context"), dict) else {}
        if isinstance(tuning_context, dict) and tuning_context:
            chain_text = self._ai_tuning_chain_snapshot(tuning_context)
            if chain_text:
                current_lines.append(tr("RESULTS_REVIEW_CHAIN", chain_text))
        current_lines = [line for line in current_lines if line]
        if current_lines:
            return current_lines

        fallback_lines = [
            self._history_validation_summary(record),
            self._history_result_origin_label(record),
        ]
        summary_origin = str(summary.get("result_origin") or "").strip()
        if not summary_origin and bool(summary.get("ai_tuned")):
            summary_origin = "controlled_optimization_rerun"
        if summary_origin == "controlled_optimization_rerun" or bool(summary.get("ai_tuned")):
            tuning_context = summary.get("history_context", {}).get("tuning_context") if isinstance(summary.get("history_context"), dict) else {}
            chain_text = self._ai_tuning_chain_snapshot(tuning_context if isinstance(tuning_context, dict) else {})
            if not chain_text:
                chain_text = self._history_result_origin_label(record) or summary_origin
            fallback_lines.append(tr("RESULTS_REVIEW_CHAIN", chain_text))
        boundary_text = str(self._responsibility_boundary_summary() or "").strip()
        if boundary_text and boundary_text not in fallback_lines:
            fallback_lines.append(boundary_text)
        fallback_lines = [line for line in fallback_lines if line]
        return fallback_lines

    def _joint_issue_family_label(self, family) -> str:
        key = str(family or "").strip().lower()
        mapping = {
            "phi_c inconsistency": tr("JOINT_ISSUE_FAMILY_PHI_C"),
            "tm bidirectional gap": tr("JOINT_ISSUE_FAMILY_TM_GAP"),
            "l consistency unstable": tr("JOINT_ISSUE_FAMILY_L_UNSTABLE"),
            "cross-tech issue": tr("JOINT_ISSUE_FAMILY_CROSS_TECH"),
        }
        return mapping.get(key, str(family or "").strip())

    def _joint_ai_reminder_text(self, joint_context=None) -> str:
        joint_context = joint_context if isinstance(joint_context, dict) else self._joint_ai_context()
        if not isinstance(joint_context, dict) or not joint_context:
            return ""
        issue_count = 0
        try:
            issue_count = int(float(joint_context.get("issue_count") or 0))
        except (TypeError, ValueError):
            issue_count = 0
        issue_families = joint_context.get("issue_families") if isinstance(joint_context.get("issue_families"), list) else []
        family_labels = []
        for family in issue_families:
            label = self._joint_issue_family_label(family)
            if label and label not in family_labels:
                family_labels.append(label)
            if len(family_labels) >= 3:
                break
        if not family_labels:
            return tr("JOINT_REMINDER_GENERIC") if issue_count > 0 else ""
        separator = "、" if get_language() == "zh" else ", "
        return tr("JOINT_REMINDER_FOCUS", separator.join(family_labels))

    def _joint_compare_hint_text(self, joint_context=None) -> str:
        joint_context = joint_context if isinstance(joint_context, dict) else self._joint_ai_context()
        if not isinstance(joint_context, dict) or not joint_context:
            return ""
        issue_count = 0
        try:
            issue_count = int(float(joint_context.get("issue_count") or 0))
        except (TypeError, ValueError):
            issue_count = 0
        if issue_count <= 0:
            return ""
        issue_families = joint_context.get("issue_families") if isinstance(joint_context.get("issue_families"), list) else []
        family_labels = []
        for family in issue_families:
            label = self._joint_issue_family_label(family)
            if label and label not in family_labels:
                family_labels.append(label)
            if len(family_labels) >= 3:
                break
        separator = "、" if get_language() == "zh" else ", "
        families_text = separator.join(family_labels)
        if families_text:
            return tr("JOINT_COMPARE_HINT_FAMILIES", families_text)
        return tr("JOINT_COMPARE_HINT_GENERIC")

    def _ai_tuning_previous_round_summary(self):
        context = getattr(self, "_last_ai_tuning_context", {})
        if not isinstance(context, dict) or not context:
            return self._ai_tuning_previous_round_empty_text()

        parts = []
        summary = str(context.get("summary") or "").strip()
        if summary:
            parts.append(summary)
        accepted = str(context.get("accepted_summary") or "").strip()
        benchmark_text = str(context.get("benchmark_text") or "").strip()
        stop_reason = str(context.get("stop_reason") or "").strip()
        remaining_risks = str(context.get("remaining_risks") or "").strip()
        next_goal = str(context.get("next_goal") or "").strip()

        if accepted:
            parts.append(accepted)
        if benchmark_text and benchmark_text not in parts:
            parts.append(benchmark_text)
        if stop_reason:
            parts.append(self._ai_tuning_previous_round_stop_text(stop_reason))
        if remaining_risks:
            parts.append(self._ai_tuning_previous_round_risks_text(remaining_risks))
        if next_goal:
            parts.append(self._ai_tuning_previous_round_goal_text(next_goal))
        if not parts:
            return self._ai_tuning_previous_round_empty_text()
        return "\n".join([self._ai_tuning_previous_round_label()] + parts)

    def _benchmark_delta_text(self, value) -> str:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return "N/A"
        sign = "+" if number > 0 else ""
        return f"{sign}{number:.3f}"

    def _benchmark_rate_text(self, value) -> str:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return "0.0%"
        return f"{number * 100:.1f}%"

    def _benchmark_summary_text(self, benchmark_summary) -> str:
        if not isinstance(benchmark_summary, dict) or not benchmark_summary:
            return ""
        return tr(
            "AI_TUNING_REPORT_BENCHMARK",
            self._benchmark_delta_text(benchmark_summary.get("average_objective_delta")),
            self._benchmark_rate_text(benchmark_summary.get("acceptance_rate")),
            self._benchmark_rate_text(benchmark_summary.get("rejection_rate")),
            self._benchmark_rate_text(benchmark_summary.get("constraint_hit_rate")),
            self._benchmark_rate_text(benchmark_summary.get("symptom_fix_rate")),
        )

    def _ai_tuning_report_context(self, report):
        report = report if isinstance(report, dict) else {}
        improvement = report.get("improvement") if isinstance(report.get("improvement"), dict) else {}
        best_r2 = report.get("best_r_squared", "")
        delta = improvement.get("r_squared_abs", "")
        rounds = report.get("rounds", 0)
        convergence_reason = str(report.get("convergence_reason", "") or "").strip()
        benchmark_summary = report.get("benchmark_summary") if isinstance(report.get("benchmark_summary"), dict) else {}
        benchmark_text = self._benchmark_summary_text(benchmark_summary)
        history = report.get("history") or []
        rollback_reasons = []
        accepted_rounds = 0
        if isinstance(history, list):
            for item in history:
                if not isinstance(item, dict):
                    continue
                if bool(item.get("accepted", True)):
                    accepted_rounds += 1
                    continue
                advice = item.get("llm_advice") if isinstance(item.get("llm_advice"), dict) else {}
                reason = str(advice.get("rollback_reason", "") or "").strip()
                if reason:
                    rollback_reasons.append(reason)

        remaining_risks = ""
        if rollback_reasons:
            unique_reasons = []
            for reason in rollback_reasons:
                if reason not in unique_reasons:
                    unique_reasons.append(reason)
            remaining_risks = "; ".join(unique_reasons[:3])

        accepted_summary = self._ai_tuning_previous_round_accepted_text(
            accepted_rounds,
            best_r2,
            delta,
            rounds,
        )
        next_goal = self._ai_tuning_previous_round_goal_body(
            convergence_reason or self._ai_tuning_previous_round_empty_text(),
            remaining_risks or self._ai_tuning_previous_round_empty_text(),
        )
        summary_parts = [accepted_summary]
        if benchmark_text:
            summary_parts.append(benchmark_text)
        if convergence_reason:
            summary_parts.append(self._ai_tuning_previous_round_stop_text(convergence_reason))
        if remaining_risks:
            summary_parts.append(self._ai_tuning_previous_round_risks_text(remaining_risks))
        summary_parts.append(self._ai_tuning_previous_round_goal_text(next_goal))
        return {
            "summary": "\n".join(part for part in summary_parts if part),
            "accepted_summary": accepted_summary,
            "benchmark_summary": benchmark_summary,
            "benchmark_text": benchmark_text,
            "history": history if isinstance(history, list) else [],
            "stop_reason": convergence_reason,
            "remaining_risks": remaining_risks,
            "next_goal": next_goal,
        }

    def _ai_tuning_previous_round_label(self):
        return "上一轮上下文：" if get_language() == "zh" else "Previous round context:"

    def _ai_tuning_previous_round_empty_text(self):
        return "当前还没有可用的上一轮调优上下文" if get_language() == "zh" else "No previous tuning context is available yet"

    def _ai_tuning_previous_round_stop_text(self, stop_reason: str) -> str:
        return f"停止原因：{stop_reason}" if get_language() == "zh" else f"Stop reason: {stop_reason}"

    def _ai_tuning_previous_round_risks_text(self, risks: str) -> str:
        return f"未消除风险：{risks}" if get_language() == "zh" else f"Remaining risks: {risks}"

    def _ai_tuning_previous_round_goal_text(self, goal: str) -> str:
        return f"下一轮目标：{goal}" if get_language() == "zh" else f"Next goal: {goal}"

    def _ai_tuning_previous_round_accepted_text(self, accepted_rounds, best_r2, delta, rounds) -> str:
        if get_language() == "zh":
            return f"上一轮摘要：接受了 {accepted_rounds} 轮；最佳 R2 = {best_r2}；提升 = {delta}；总轮数 = {rounds}"
        return f"Previous round summary: accepted {accepted_rounds} rounds; best R2 = {best_r2}; improvement = {delta}; total rounds = {rounds}"

    def _ai_tuning_previous_round_goal_body(self, focus: str, watch: str) -> str:
        if get_language() == "zh":
            return f"下一轮应尽量保留现有收益，并优先处理 {focus}。同时仍需关注 {watch}"
        return f"The next round should keep the current gains and focus on {focus} while still watching {watch}"

    def _ai_tuning_chain_summary(self, report: dict | None = None) -> str:
        report = report if isinstance(report, dict) else {}
        benchmark_summary = report.get("benchmark_summary") if isinstance(report.get("benchmark_summary"), dict) else {}
        history = report.get("history") if isinstance(report.get("history"), list) else []

        accepted_rounds = 0
        rolled_back_rounds = 0
        rollback_reasons = []
        best_round = None
        best_r2 = None
        last_accepted_round = None

        for item in history:
            if not isinstance(item, dict):
                continue
            round_num = int(item.get("round_num", item.get("round_idx", 0)) or 0)
            if round_num <= 0:
                continue
            accepted = bool(item.get("accepted", True))
            if accepted:
                accepted_rounds += 1
                last_accepted_round = round_num
            else:
                rolled_back_rounds += 1
                advice = item.get("llm_advice") if isinstance(item.get("llm_advice"), dict) else {}
                reason = str(advice.get("rollback_reason", "") or "").strip()
                if reason and reason not in rollback_reasons:
                    rollback_reasons.append(reason)
            r2 = item.get("r_squared_after", item.get("r_squared", None))
            try:
                r2_value = float(r2)
            except (TypeError, ValueError):
                continue
            if best_r2 is None or r2_value > best_r2:
                best_r2 = r2_value
                best_round = round_num

        baseline_hint = ""
        if isinstance(benchmark_summary, dict) and benchmark_summary:
            baseline_hint = self._benchmark_delta_text(benchmark_summary.get("average_objective_delta"))
        if get_language() == "zh":
            parts = [
                f"基线变化：{baseline_hint or 'N/A'}",
                f"接受 {accepted_rounds} 轮，回滚 {rolled_back_rounds} 轮",
            ]
            if best_round is not None:
                parts.append(f"当前最佳：第 {best_round} 轮")
            if last_accepted_round is not None:
                parts.append(f"最新接受：第 {last_accepted_round} 轮")
            if rollback_reasons:
                parts.append(f"保留风险：{'; '.join(rollback_reasons[:2])}")
            return " | ".join(parts)

        parts = [
            f"baseline delta {baseline_hint or 'N/A'}",
            f"accepted {accepted_rounds} rounds, rolled back {rolled_back_rounds} rounds",
        ]
        if best_round is not None:
            parts.append(f"best candidate round {best_round}")
        if last_accepted_round is not None:
            parts.append(f"latest accepted round {last_accepted_round}")
        if rollback_reasons:
            parts.append(f"remaining risks: {'; '.join(rollback_reasons[:2])}")
        return " | ".join(parts)

    def _ai_tuning_tunable_summary(self):
        from polynexus.config_bridge import (
            DSC_PARAM_MAP,
            IR_PARAM_MAP,
            NMR_PARAM_MAP,
            SAXS_PARAM_MAP,
            WAXS_PARAM_MAP,
        )

        technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
        param_map = {
            "dsc": DSC_PARAM_MAP,
            "ir": IR_PARAM_MAP,
            "nmr": NMR_PARAM_MAP,
            "saxs": SAXS_PARAM_MAP,
            "waxs": WAXS_PARAM_MAP,
        }.get(technique, {})
        if not isinstance(param_map, dict) or not param_map:
            return tr("AI_TUNING_CONTEXT_TUNABLE_NONE")

        rows = []
        for name, rule in list(param_map.items())[:4]:
            current = self._config_value_by_key(str(name))
            constraint = rule.constraint
            if all(isinstance(item, str) for item in constraint):
                constraint_text = ", ".join(str(item) for item in constraint[:3])
                if len(constraint) > 3:
                    constraint_text = f"{constraint_text}, ..."
            else:
                constraint_text = f"{constraint[0]} -> {constraint[1]}"
            rows.append(tr("AI_TUNING_CONTEXT_TUNABLE_ROW", name, current, constraint_text))
        remaining = max(0, len(param_map) - len(rows))
        if remaining:
            rows.append(tr("AI_TUNING_CONTEXT_TUNABLE_MORE", remaining))
        return "\n".join(rows)

    def _config_value_by_key(self, key):
        widget = self._config_widget_by_key(key)
        if widget is None:
            return "-"
        if isinstance(widget, QComboBox):
            return widget.currentText()
        if isinstance(widget, QDoubleSpinBox):
            return widget.value()
        if isinstance(widget, QSpinBox):
            return widget.value()
        if isinstance(widget, QCheckBox):
            return tr("COMMON_ON") if widget.isChecked() else tr("COMMON_OFF")
        if isinstance(widget, QLineEdit):
            return widget.text()
        if hasattr(widget, "text"):
            try:
                return widget.text()
            except Exception:
                return "-"
        return "-"


    def _on_ai_tune_progress(self, message):
        if hasattr(self, "_ai_progress") and self._ai_progress is not None:
            self._ai_progress.setLabelText(message)
        self.log(message)


    def _on_ai_tune_finished(self, report):
        if hasattr(self, "_ai_progress") and self._ai_progress is not None:
            self._ai_progress.close()
        self._ai_tuning_active = False
        self._update_workflow_task_card()
        tuning_context = self._ai_tuning_report_context(report)
        tuning_context["tuning_goal"] = self._current_tuning_goal()
        tuning_context["tuning_goal_label"] = self._ai_tuning_goal_label(self._current_tuning_goal())
        self._last_ai_tuning_context = tuning_context
        self._update_workspace_context()
        self._update_work_memory_panel()
        self._update_results_review_panel()
        dialog = SideTuningReportDialog(report, self)
        if dialog.exec() == QDialog.Accepted:
            self._apply_best_config(dialog.best_config())
            self._last_ai_tuned_run = True
            if hasattr(self, "_tabs"):
                self._tabs.setCurrentIndex(1)
            self.log(tr("LOG_AI_TUNING_APPLY_AND_RERUN"))
            self._run_analysis()
        self.log(tr("LOG_AI_TUNING_DONE"))
        try:
            from polynexus.gui.convergence_viewer import load_ai_tune_runs

            load_ai_tune_runs()
        except Exception:
            logger.warning("Failed to refresh AI tuning convergence runs.", exc_info=True)


    def _on_ai_tune_error(self, message):
        if hasattr(self, "_ai_progress") and self._ai_progress is not None:
            self._ai_progress.close()
        self._ai_tuning_active = False
        self._update_workflow_task_card()
        self.log(tr("LOG_ERROR_DETAIL", message))
        QMessageBox.critical(self, tr("AI_TUNING_TITLE"), message)


    def _apply_best_config(self, best_config):
        if not isinstance(best_config, dict):
            return
        for row in range(self._config_form.rowCount()):
            item = self._config_form.itemAt(row, QFormLayout.FieldRole)
            if item is None:
                item = self._config_form.itemAt(row, QFormLayout.SpanningRole)
            widget = item.widget() if item is not None else None
            if widget is None:
                continue
            key = widget.property("config_key")
            if not key or key not in best_config:
                continue
            value = best_config[key]
            if isinstance(widget, QComboBox):
                idx = widget.findText(str(value))
                if idx >= 0:
                    widget.setCurrentIndex(idx)
            elif isinstance(widget, QDoubleSpinBox):
                try:
                    widget.setValue(float(value))
                except Exception:
                    logger.warning("Failed to apply floating-point config value.", exc_info=True)
            elif isinstance(widget, QSpinBox):
                try:
                    widget.setValue(int(value))
                except Exception:
                    logger.warning("Failed to apply integer config value.", exc_info=True)
            elif isinstance(widget, QCheckBox):
                widget.setChecked(bool(value))
            elif isinstance(widget, QLineEdit):
                widget.setText(str(value))


    def _on_error(self, msg):

        self._btn_run.setEnabled(True)

        self._btn_run.setText(tr("BTN_RUN"))

        stop_progress_animation(self._progress)
        self._progress.setVisible(False)

        self._set_running_ui(False)

        self.log(tr("LOG_ERROR_DETAIL", msg))
        self._append_analysis_warning_summary()



    def _on_batch_file_done(self, filename, params):

        self._batch_results.append({'file': filename, 'params': params})


    def _set_results_item(self, row, col, value):

        """Set a result-table item with full-value tooltip."""

        text = "" if value is None else str(value)

        item = QTableWidgetItem(text)

        item.setToolTip(text)

        self._results_table.setItem(row, col, item)



    def _apply_results_table_layout(self):

        """Keep wide result tables readable instead of squeezing columns."""

        table = self._results_table

        cols = table.columnCount()

        rows = table.rowCount()

        header = table.horizontalHeader()

        header.setStretchLastSection(False)

        table.setWordWrap(False)

        table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)

        table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        if cols <= 2:

            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)

            if cols == 2:

                header.setSectionResizeMode(1, QHeaderView.Stretch)

            table.resizeRowsToContents()

            return

        if cols <= 6:

            header.setSectionResizeMode(QHeaderView.Stretch)

            table.resizeRowsToContents()

            return

        header.setSectionResizeMode(QHeaderView.Interactive)

        header.setMinimumSectionSize(96)

        header.setDefaultSectionSize(150)

        for col in range(cols):

            label_item = table.horizontalHeaderItem(col)

            label = label_item.text() if label_item is not None else ""

            width = 170 if col == 0 else 132

            if len(label) > 18:

                width = min(220, max(width, len(label) * 8))

            table.setColumnWidth(col, width)

        if rows > 0:

            table.resizeRowsToContents()



    def _on_batch_finished(self, all_results):

        self._btn_run.setEnabled(True)

        self._btn_run.setText(tr("BTN_RUN"))

        stop_progress_animation(self._progress)
        self._progress.setVisible(False)

        self._batch_list.setVisible(False)
        self._update_batch_list_copy_button()

        self._set_running_ui(False)

        self.log(tr("LOG_BATCH_DONE").format(len(all_results)))

        self._hide_joint_diagnostics()
        self._set_results_summary("")
        self._results_table.setSortingEnabled(False)
        self._set_results_export_control_visible(False)
        self._set_results_copy_control_visible(False)
        self._clear_results_table_default_order()

        # Display batch results in table

        if all_results:

            # Collect all parameter keys across files (handle nested params)

            all_keys = []

            flat_rows = []

            for row in all_results:

                fname = row.get('file', '')

                params = row.get('params', {})

                # Flatten nested params: {label: {k: v}} -> {k: v}

                flat = {}

                for key, val in params.items():

                    if isinstance(val, dict):

                        flat.update(val)

                    else:

                        flat[key] = val

                flat['file'] = fname

                for key in flat.keys():
                    if key not in all_keys:
                        all_keys.append(key)

                flat_rows.append(flat)

            cols = self._ordered_results_columns(all_keys)

            self._results_table.setRowCount(len(flat_rows))

            self._results_table.setColumnCount(len(cols))

            self._results_table.setHorizontalHeaderLabels(cols)

            for i, flat in enumerate(flat_rows):

                self._set_results_item(i, 0, flat.get('file', ''))

                for j, col in enumerate(cols[1:], 1):

                    val = flat.get(col, '')

                    val_str = f"{val:.4f}" if isinstance(val, float) else str(val)

                    self._set_results_item(i, j, val_str)

            self._store_results_table_default_order(
                cols,
                [[flat.get(col, '') for col in cols] for flat in flat_rows],
                sortable=True,
            )
            self._apply_results_table_layout()
            self._set_results_export_control_visible(True)
            self._set_results_copy_control_visible(True)
            self._results_table.setSortingEnabled(True)
            self._set_results_summary(self._batch_results_summary_text(len(flat_rows)))

            self._populate_plots()

            self._tabs.setCurrentIndex(2)



    def _display_results(self, params, result=None):

        self._hide_joint_diagnostics()
        self._set_results_summary("")
        self._results_table.setSortingEnabled(False)
        self._set_results_export_control_visible(False)
        self._set_results_copy_control_visible(False)
        self._clear_results_table_default_order()

        # Detect multi-sample: all values are dicts with scalar content
        is_multi = (
            isinstance(params, dict)
            and len(params) > 1
            and all(isinstance(v, dict) for v in params.values())
            and not any(k.startswith('_') for k in params)
        )

        if is_multi:
            # Multi-sample table: samples as rows, parameters as columns
            sample_labels = list(params.keys())
            all_keys = []
            for v in params.values():
                for k in v:
                    if k not in all_keys:
                        all_keys.append(k)
            cols = self._ordered_results_columns(['sample', *all_keys])
            self._results_table.setRowCount(len(sample_labels))
            self._results_table.setColumnCount(len(cols))
            self._results_table.setHorizontalHeaderLabels(cols)
            for i, label in enumerate(sample_labels):
                self._set_results_item(i, 0, label)
                for j, key in enumerate(cols[1:]):
                    val = params[label].get(key, '')
                    val_str = f"{val:.2f}" if isinstance(val, float) else str(val)
                    self._set_results_item(i, j + 1, val_str)
            self._store_results_table_default_order(
                cols,
                [[label] + [params[label].get(key, '') for key in cols[1:]] for label in sample_labels],
                sortable=True,
            )
            self._apply_results_table_layout()
            self._set_results_export_control_visible(True)
            self._set_results_copy_control_visible(True)
            self._results_table.setSortingEnabled(True)
            if result is not None:
                self._set_results_summary(
                    tr("RESULTS_SUMMARY_MULTI_SAMPLE", len(sample_labels)),
                    self._results_risk_summary_text(params, result),
                    self._results_next_step_text(params, result),
                )
            else:
                self._set_results_summary(tr("RESULTS_SUMMARY_MULTI_SAMPLE", len(sample_labels)))
            return

        # Detect batch: params has 'batch_frames' with nested data

        batch_frames = params.get('batch_frames', 0) if isinstance(params, dict) else 0



        if batch_frames > 1 and '_batch_data' in params:

            # Multi-frame: show one row per file

            batch_data = params['_batch_data']

            all_keys = []
            for row in batch_data:
                for key in row.keys():
                    if key not in all_keys:
                        all_keys.append(key)
            cols = self._ordered_results_columns(all_keys if all_keys else ['file', 'L_nm', 'lc_nm', 'Xc'])

            self._results_table.setRowCount(len(batch_data))

            self._results_table.setColumnCount(len(cols))

            self._results_table.setHorizontalHeaderLabels(cols)

            for i, row in enumerate(batch_data):

                for j, col in enumerate(cols):

                    val = row.get(col, '')

                    val_str = f"{val:.3f}" if isinstance(val, float) else str(val)

                    self._set_results_item(i, j, val_str)

            self._store_results_table_default_order(
                cols,
                [[row.get(col, '') for col in cols] for row in batch_data],
                sortable=True,
            )
            self._apply_results_table_layout()
            self._set_results_export_control_visible(True)
            self._set_results_copy_control_visible(True)
            self._results_table.setSortingEnabled(True)
            if result is not None:
                self._set_results_summary(
                    self._frame_results_summary_text(len(batch_data) or batch_frames),
                    self._results_risk_summary_text(params, result),
                    self._results_next_step_text(params, result),
                )
            else:
                self._set_results_summary(
                    self._frame_results_summary_text(len(batch_data) or batch_frames),
                    self._results_risk_summary_text(params),
                    self._results_next_step_text(params),
                )

        else:

            # Single frame: key-value table

            items = self._flatten_params(params)

            self._results_table.setRowCount(len(items))

            self._results_table.setColumnCount(2)

            self._results_table.setHorizontalHeaderLabels([tr("RESULTS_PARAM"), tr("RESULTS_VALUE")])

            for i, (k, v) in enumerate(items):

                self._set_results_item(i, 0, k)

                val_str = f"{v:.4f}" if isinstance(v, float) else str(v)

                self._set_results_item(i, 1, val_str)

            self._apply_results_table_layout()
            self._set_results_export_control_visible(bool(items))
            self._set_results_copy_control_visible(bool(items))

            if result is not None:
                self._set_results_summary(
                    self._single_results_summary_text(params),
                    self._results_risk_summary_text(params, result),
                    self._results_next_step_text(params, result),
                )
            return

        if result is not None:
            self._set_results_summary(
                self._frame_results_summary_text(len(batch_data) or batch_frames)
                if batch_frames > 1 and "_batch_data" in params
                else "",
                self._results_risk_summary_text(params, result),
                self._results_next_step_text(params, result),
            )



    def _flatten_params(self, params, prefix=''):

        """Flatten nested dict/list params into key-value pairs for display.



        Handles WAXS-style {scan_label: {param: val}} and

        IR-style {param: [list_of_peaks]}.

        """

        items = []

        if not isinstance(params, dict):

            return [(str(prefix) if prefix else 'value', str(params))]



        for k, v in params.items():

            if k.startswith('_') or k == 'batch_frames':

                continue

            full_key = f"{prefix}.{k}" if prefix else k



            if isinstance(v, dict) and any(isinstance(vv, (int, float)) for vv in v.values()):

                # Nested dict with scalar values: flatten one level

                # e.g. {"scan1": {"Xc": 45.2, "D_nm": 8.3}}

                #      -> [("scan1.Xc", 45.2), ("scan1.D_nm", 8.3)]

                for sk, sv in v.items():

                    if isinstance(sv, (int, float, str, bool)):

                        items.append((f"{full_key}.{sk}", sv))

                    elif isinstance(sv, (list, tuple)) and len(sv) <= 5:

                        items.append((f"{full_key}.{sk}", str(sv)))

                continue



            if isinstance(v, (list, tuple)):

                if len(v) == 0:

                    items.append((full_key, "[]"))

                elif all(isinstance(x, (list, tuple)) and len(x) == 2

                         and isinstance(x[0], (int, float))

                         and isinstance(x[1], (int, float)) for x in v):

                    # Show short previews for lists of (position, value) pairs.

                    items.append((full_key,

                                  ', '.join(f'{x[0]:.1f}:{x[1]:.2f}' for x in v[:8])

                                  + ('...' if len(v) > 8 else '')))

                elif len(v) <= 6 and all(isinstance(x, (int, float)) for x in v):

                    items.append((full_key, ', '.join(f'{x:.2f}' for x in v)))

                else:

                    items.append((full_key, f"[{len(v)} items]"))

            elif isinstance(v, (int, float, str, bool)):

                items.append((full_key, v))

            elif isinstance(v, dict):

                items.extend(self._flatten_params(v, full_key))

            else:

                items.append((full_key, str(v)))

        return items

    def _populate_plots(self):

        """Load analysis figures into the ChartGallery.



        Figures may be in output_dir, figures/, summary/, or per_frame/.

        """

        exts = {'.svg', '.png', '.pdf', '.jpg', '.jpeg'}

        figure_paths = []

        if self._output_dir and os.path.isdir(self._output_dir):

            root = Path(self._output_dir)

            figure_paths = sorted(

                str(p) for p in root.rglob("*")

                if p.is_file()

                and p.suffix.lower() in exts

                and any(part.lower() in {'figures', 'summary', 'per_frame'}

                        for part in p.parts)

            )

            if not figure_paths:

                figure_paths = sorted(

                    str(p) for p in root.iterdir()

                    if p.is_file() and p.suffix.lower() in exts

                )



        if not figure_paths:

            self._plots_label.setVisible(True)

            self._chart_gallery.setVisible(False)

            self._chart_gallery.clear()

            self._current_figure_path = ""

            if hasattr(self, '_btn_view_current_figure'):

                self._btn_view_current_figure.setEnabled(False)

            if hasattr(self, '_figure_preview'):

                self._figure_preview.clear()

                self._figure_preview.setVisible(False)

            return



        preferred_path = self._current_figure_path
        preview_was_visible = bool(
            hasattr(self, '_figure_preview') and self._figure_preview.isVisible()
        )

        self._plots_label.setVisible(False)

        self._chart_gallery.setVisible(True)

        self._chart_gallery.load_files(figure_paths)

        matched_preferred = False
        if preferred_path:
            preferred_norm = os.path.normcase(os.path.abspath(preferred_path))
            preferred_stem = Path(preferred_path).stem
            preferred_stem_base = preferred_stem[:-4] if preferred_stem.endswith("_LOW") else preferred_stem
            preferred_parent = os.path.normcase(os.path.abspath(os.path.dirname(preferred_path)))
            preferred_ext = Path(preferred_path).suffix.lower()
            fallback_match = None
            exact_match = None
            variant_match = None
            for path in figure_paths:
                path_norm = os.path.normcase(os.path.abspath(path))
                if path_norm == preferred_norm:
                    exact_match = path
                    continue
                candidate = Path(path)
                candidate_stem = candidate.stem
                candidate_stem_base = candidate_stem[:-4] if candidate_stem.endswith("_LOW") else candidate_stem
                candidate_parent = os.path.normcase(os.path.abspath(str(candidate.parent)))
                candidate_ext = candidate.suffix.lower()
                if (
                    candidate_parent == preferred_parent
                    and candidate_ext == preferred_ext
                    and candidate_stem_base == preferred_stem_base
                ):
                    fallback_match = path
                    variant_match = path
            if exact_match and variant_match:
                try:
                    exact_mtime = os.path.getmtime(exact_match)
                    variant_mtime = os.path.getmtime(variant_match)
                except OSError:
                    exact_mtime = variant_mtime = 0.0
                if variant_mtime > exact_mtime:
                    self._current_figure_path = variant_match
                    self._chart_gallery.select_figure(variant_match, emit=preview_was_visible)
                    matched_preferred = True
                else:
                    self._current_figure_path = exact_match
                    self._chart_gallery.select_figure(exact_match, emit=preview_was_visible)
                    matched_preferred = True
            elif exact_match:
                self._current_figure_path = exact_match
                self._chart_gallery.select_figure(exact_match, emit=preview_was_visible)
                matched_preferred = True
            if not matched_preferred and fallback_match:
                self._current_figure_path = fallback_match
                self._chart_gallery.select_figure(fallback_match, emit=preview_was_visible)
                matched_preferred = True
        if not matched_preferred and figure_paths:
            self._current_figure_path = figure_paths[0]
            self._chart_gallery.select_figure(figure_paths[0], emit=preview_was_visible)

    def _on_chart_selected(self, filepath):

        """Show the selected exported figure in the embedded preview."""

        self._current_figure_path = filepath or ""

        if not self._current_figure_path or not hasattr(self, '_figure_preview'):

            return

        if hasattr(self, '_btn_view_current_figure'):

            self._btn_view_current_figure.setEnabled(True)

        self._figure_preview.setVisible(True)

        self._figure_preview.load_figure(self._current_figure_path)



    def _close_figure_preview(self):

        """Hide the focused exported-figure preview."""

        if hasattr(self, '_figure_preview'):

            self._figure_preview.setVisible(False)



    def _open_current_figure_viewer(self, filepath=None):

        """Open a separate viewer for the selected exported figure."""

        if isinstance(filepath, bool):

            filepath = None

        figure_path = filepath or self._current_figure_path

        if not figure_path:

            self.log(tr("LOG_FIGURE_NOT_SELECTED"))

            return

        if not os.path.exists(figure_path):

            self.log(tr("LOG_FIGURE_MISSING", figure_path))

            return

        if not hasattr(self, "_figure_viewer") or self._figure_viewer is None:

            self._figure_viewer = ChartViewer()

            self._figure_viewer.edit_requested.connect(self._open_selected_chart_editor)
            self._figure_viewer.status_message.connect(self._on_chart_viewer_status)

        self._figure_viewer.setWindowTitle(
            tr("FIGURE_VIEWER_WINDOW", os.path.basename(figure_path))
        )

        self._figure_viewer.load_figure(figure_path, self._current_chart_raw_data())

        self._figure_viewer.resize(1180, 820)

        self._figure_viewer.show()

        self._figure_viewer.raise_()

        self._figure_viewer.activateWindow()


    def _current_chart_raw_data(self):
        result = self._results.get(self._current_technique)
        if result is None:
            return None
        if isinstance(result, dict):
            raw_data = result.get("raw_data")
            return raw_data if isinstance(raw_data, dict) else None
        raw_data = getattr(result, "raw_data", None)
        return raw_data if isinstance(raw_data, dict) else None


    def _on_chart_viewer_status(self, message, level="info"):
        ts = datetime.now().strftime("%H:%M:%S")
        color_map = {
            "success": "#16a34a",
            "warning": "#d97706",
            "error": "#dc2626",
            "info": "#2563eb",
        }
        color = color_map.get(level, color_map["info"])
        line = f'[{ts}] <span style="color:{color};">{message}</span>'
        self._log_panel.append(line)
        sb = self._log_panel.verticalScrollBar()
        sb.setValue(sb.maximum())



    def _open_selected_chart_editor(self, filepath=None):

        """Open settings for the selected exported figure file."""

        if isinstance(filepath, bool):

            filepath = None

        self._open_exported_figure_editor(filepath or self._current_figure_path)



    def _open_exported_figure_editor(self, figure_path=None):

        """Open an editor that is bound to the selected exported figure."""

        figure_path = figure_path or self._current_figure_path

        if not figure_path:

            self.log(tr("LOG_FIGURE_NOT_SELECTED"))

            return

        if not os.path.exists(figure_path):

            self.log(tr("LOG_FIGURE_MISSING", figure_path))

            return

        editor = ChartEditor()

        editor.figure_saved.connect(self._on_chart_editor_saved)

        editor.setWindowTitle(tr("FIGURE_SETTINGS_WINDOW", os.path.basename(figure_path)))

        editor.set_source_figure(figure_path)

        editor.resize(1000, 650)

        editor.show()

        self._chart_editor = editor



    def _open_figure(self, item):

        fig_path = os.path.join(self._output_dir, 'figures', item.text())

        if os.path.exists(fig_path):

            os.startfile(fig_path)

    def _export_bundle_dirs(self, save_root):

        root = Path(save_root)
        dirs = {
            "figures": root / "figures",
            "data": root / "data",
            "report": root / "report",
            "metadata": root / "metadata",
        }
        for directory in dirs.values():
            directory.mkdir(parents=True, exist_ok=True)
        return dirs

    def _write_export_manifest(self, save_root, *, report_path="", copied_sections=None):

        root = Path(save_root)
        metadata_dir = root / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        copied = [str(section) for section in (copied_sections or [])]
        export_context = self._export_context_payload(report_path=report_path)

        primary_report = ""
        if report_path:
            try:
                primary_report = os.path.relpath(report_path, save_root)
            except ValueError:
                primary_report = str(report_path)

        payload = {
            "project_name": self._project_label.text().strip(),
            "exported_at": datetime.now().isoformat(),
            "bundle_root": str(root),
            "source_output_dir": str(self._output_dir or ""),
            "source_data_path": str(self._current_filepath or ""),
            "current_technique": str(self._current_technique or ""),
            "current_submodule": str(getattr(self, "_current_submodule_id", "") or ""),
            "input_mode": str(getattr(self, "_current_input_mode", "") or ""),
            "included_techniques": sorted(str(key) for key in self._results.keys()),
            "copied_sections": copied,
            "directories": {
                "figures": "figures",
                "data": "data",
                "report": "report",
                "metadata": "metadata",
            },
            "primary_report": primary_report,
            "task_context": export_context,
        }

        manifest_path = metadata_dir / "export_manifest.json"
        manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return manifest_path

    def _write_export_readme(self, save_root, *, report_path=""):

        root = Path(save_root)
        export_context = self._export_context_payload(report_path=report_path)
        primary_report = ""
        if report_path:
            try:
                primary_report = os.path.relpath(report_path, save_root)
            except ValueError:
                primary_report = str(report_path)

        techniques = ", ".join(sorted(str(key).upper() for key in self._results.keys()))
        if not techniques:
            techniques = "None"
        review_summary = str(export_context.get("review_summary") or "-").strip()
        validation_chain = str(export_context.get("validation_chain") or "").strip()
        benchmark_text = str(export_context.get("benchmark_text") or "").strip()
        joint_summary = str(export_context.get("joint_summary") or "").strip()
        history_context = export_context.get("history_context") if isinstance(export_context.get("history_context"), dict) else {}
        joint_context = history_context.get("joint_ai_context") if isinstance(history_context.get("joint_ai_context"), dict) else {}
        if not joint_summary and isinstance(joint_context, dict):
            joint_summary = str(joint_context.get("summary") or "").strip()
        joint_reminder = self._joint_ai_reminder_text(joint_context) if isinstance(joint_context, dict) and joint_context else ""
        joint_compare_hint = self._joint_compare_hint_text(joint_context) if isinstance(joint_context, dict) and joint_context else ""
        joint_detail = " | ".join(part for part in [joint_summary, joint_reminder, joint_compare_hint] if part)
        if export_context.get("confirmed_result") and review_summary not in {"", "-"}:
            confirmed_text = tr("RESULTS_REVIEW_CONFIRMED")
            if not review_summary.startswith(confirmed_text):
                review_summary = f"{confirmed_text} | {review_summary}"

        lines = [
            "PolyNexus Export Package",
            "",
            f"Project: {self._project_label.text().strip() or 'Unnamed'}",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Techniques: {techniques}",
            f"Source data: {self._current_filepath or '-'}",
            f"Task type: {export_context.get('task_type') or '-'}",
            f"Technique / module: {export_context.get('technique_label') or '-'} / {export_context.get('submodule_label') or '-'}",
            f"Input mode: {export_context.get('input_mode') or '-'}",
            f"Confirmed result: {'Yes' if export_context.get('confirmed_result') else 'No'}",
            f"Result origin: {export_context.get('result_origin_label') or '-'}",
            f"Decision owner: {export_context.get('decision_owner_label') or 'User'}",
            f"Controlled optimization used: {'Yes' if export_context.get('used_controlled_optimization') else 'No'}",
            f"Comparison summary: {export_context.get('comparison_summary') or '-'}",
            f"Review summary: {review_summary}",
            f"Validation chain: {validation_chain or benchmark_text or '-'}",
            f"Joint summary: {joint_detail or '-'}",
            f"Responsibility boundary: {export_context.get('responsibility_boundary') or '-'}",
            f"Work memory: {export_context.get('work_memory_summary') or '-'}",
            "",
            "Main folders:",
            "- report/    HTML and markdown reports",
            "- figures/   Exported plots and images",
            "- data/      Parameter tables and derived CSV files",
            "- metadata/  Export manifest and package notes",
            "",
            "Review priority:",
            f"1. {export_context.get('review_priority', ['report/'])[0]}",
            f"2. {export_context.get('review_priority', ['report/', 'metadata/export_manifest.json'])[1] if len(export_context.get('review_priority', [])) > 1 else 'metadata/export_manifest.json'}",
            f"3. {export_context.get('review_priority', ['report/', 'metadata/export_manifest.json', 'data/'])[2] if len(export_context.get('review_priority', [])) > 2 else 'data/'}",
            "",
            "Recommended reading order:",
            f"1. {export_context.get('recommended_reading_order', ['report/'])[0]}",
            f"2. {export_context.get('recommended_reading_order', ['report/', 'metadata/export_manifest.json'])[1] if len(export_context.get('recommended_reading_order', [])) > 1 else 'metadata/export_manifest.json'}",
            f"3. {export_context.get('recommended_reading_order', ['report/', 'metadata/export_manifest.json', 'data/'])[2] if len(export_context.get('recommended_reading_order', [])) > 2 else 'data/'}",
            "",
            f"Open first: {primary_report or 'report/ (no HTML report generated)'}",
        ]

        readme_path = root / "README.txt"
        readme_path.write_text("\n".join(lines), encoding="utf-8")
        return readme_path

    def _current_result_origin(self) -> str:

        current_result = self._results.get(str(getattr(self, "_current_technique", "") or "").strip().lower())
        if isinstance(current_result, dict):
            summary = current_result.get("results_summary") if isinstance(current_result.get("results_summary"), dict) else {}
            if isinstance(summary, dict):
                origin = str(summary.get("result_origin") or "").strip()
                if origin:
                    return origin
                if bool(summary.get("ai_tuned")):
                    return "controlled_optimization_rerun"
        if bool(getattr(self, "_last_ai_tuned_run", False)):
            return "controlled_optimization_rerun"
        return "manual_run"

    def _current_result_origin_label(self) -> str:

        origin = self._current_result_origin()
        if not origin:
            return ""
        return self._result_origin_label(origin)

    def _result_origin_label(self, origin: str) -> str:

        key = str(origin or "").strip()
        if key == "controlled_optimization_rerun":
            return tr("RESULT_ORIGIN_AI_TUNED")
        if key == "manual_run":
            return tr("RESULT_ORIGIN_MANUAL")
        return key or "Unknown"

    def _history_result_origin_label(self, record) -> str:

        if not isinstance(record, dict):
            return ""
        summary = record.get("results_summary") if isinstance(record.get("results_summary"), dict) else {}
        if not isinstance(summary, dict):
            return ""
        origin = str(summary.get("result_origin") or "").strip()
        if not origin and bool(summary.get("ai_tuned")):
            origin = "controlled_optimization_rerun"
        if not origin:
            return ""
        return self._result_origin_label(origin)

    def _result_comparison_summary(self) -> str:

        current = self._current_results_record()
        if not isinstance(current, dict) or not current:
            return ""
        current_label = self._result_comparison_record_label(current) or self._current_result_label_for_confirmation()
        baseline = self._current_result_comparison_baseline(self._results_compare_candidates(create_db=False))
        baseline_label = self._result_comparison_record_label(baseline) if baseline else ""
        if not baseline_label:
            return f"Current: {current_label}"
        current_metrics = self._history_result_metrics(current)
        baseline_metrics = self._history_result_metrics(baseline)
        key_changes = []
        technique = str(current.get("technique") or "").strip().lower()
        current_evidence = self._history_record_analysis_evidence(current)
        strain_active = False
        if technique == "saxs":
            strain_active = bool(self._saxs_strain_evidence_snapshot(current.get("parameters"), current_evidence).get("active"))
        if strain_active:
            compare_keys = ["Q_star_rel_mean", "Q_star_rel_span", "phi_void_mean", "phi_void_span", "f_Herman_mean", "f_Herman_span", "porod_slope_mean", "void_detected_frames"]
        elif technique == "saxs":
            compare_keys = [
                "lc_nm",
                "lc_method",
                "calibrated_fallback_active",
                "calibration_skipped_reason",
                "lc_reliability_status",
                "melting_window_status",
                "Tm_onset_C",
                "Tm_peak_C",
                "Tm_end_C",
            ]
        else:
            compare_keys = ["r_squared", "L_nm", "Xc_pct", "Tm_peak_C", "Tc_peak_C", "quality_score"]
        for key in compare_keys:
            current_value = current_metrics.get(key, "")
            baseline_value = baseline_metrics.get(key, "")
            if current_value == baseline_value:
                continue
            if not current_value and not baseline_value:
                continue
            key_changes.append(f"{key}: {baseline_value or '-'} -> {current_value or '-'}")
        if key_changes:
            return f"Current: {current_label} | Baseline: {baseline_label} | Key changes: " + "; ".join(key_changes[:3])
        return f"Current: {current_label} | Baseline: {baseline_label}"

    def _ai_tuning_chain_snapshot(self, tuning_context: dict | None = None) -> str:
        tuning_context = tuning_context if isinstance(tuning_context, dict) else {}
        current_origin = self._current_result_origin()
        if current_origin != "controlled_optimization_rerun" and not tuning_context:
            return ""

        history = tuning_context.get("history") if isinstance(tuning_context.get("history"), list) else []
        benchmark_summary = tuning_context.get("benchmark_summary") if isinstance(tuning_context.get("benchmark_summary"), dict) else {}

        accepted_rounds = 0
        rolled_back_rounds = 0
        best_round = None
        best_r2 = None
        rollback_reasons = []

        for item in history:
            if not isinstance(item, dict):
                continue
            round_num = int(item.get("round_num", item.get("round_idx", 0)) or 0)
            if round_num <= 0:
                continue
            if bool(item.get("accepted", True)):
                accepted_rounds += 1
            else:
                rolled_back_rounds += 1
                advice = item.get("llm_advice") if isinstance(item.get("llm_advice"), dict) else {}
                rollback_reason = str(advice.get("rollback_reason") or "").strip()
                if rollback_reason and rollback_reason not in rollback_reasons:
                    rollback_reasons.append(rollback_reason)
            try:
                r2_value = float(item.get("r_squared_after", item.get("r_squared", "")))
            except (TypeError, ValueError):
                continue
            if best_r2 is None or r2_value > best_r2:
                best_r2 = r2_value
                best_round = round_num

        baseline_hint = ""
        if isinstance(benchmark_summary, dict) and benchmark_summary:
            baseline_hint = self._benchmark_delta_text(benchmark_summary.get("average_objective_delta"))

        if get_language() == "zh":
            parts = [
                f"基线变化：{baseline_hint or 'N/A'}",
                f"接受 {accepted_rounds} 轮，回滚 {rolled_back_rounds} 轮",
            ]
            if best_round is not None:
                parts.append(f"当前最佳：第 {best_round} 轮")
            if rollback_reasons:
                parts.append(f"保留风险：{'; '.join(rollback_reasons[:2])}")
            return " | ".join(parts)

        parts = [
            f"baseline delta {baseline_hint or 'N/A'}",
            f"accepted {accepted_rounds} rounds, rolled back {rolled_back_rounds} rounds",
        ]
        if best_round is not None:
            parts.append(f"best candidate round {best_round}")
        if rollback_reasons:
            parts.append(f"remaining risks: {'; '.join(rollback_reasons[:2])}")
        return " | ".join(parts)

    def _result_review_summary(self) -> str:
        parts: list[str] = []
        current = self._current_results_record()
        if not isinstance(current, dict) or not current:
            return ""

        summary = current.get("results_summary") if isinstance(current.get("results_summary"), dict) else {}
        analysis_evidence = self._current_analysis_evidence()
        measured_text = self._measured_result_summary_text(current)
        origin_label = self._current_result_origin_label()
        confirmed_label = tr("RESULTS_REVIEW_CONFIRMED") if self._is_current_result_confirmed() else tr("RESULTS_REVIEW_PENDING")

        if measured_text:
            parts.append(tr("RESULTS_REVIEW_MEASURED", measured_text))
        if origin_label:
            parts.append(origin_label)
        parts.append(confirmed_label)

        validation_summary = str(summary.get("validation_summary") or current.get("validation_summary") or "").strip()
        if not validation_summary and hasattr(self, "_results_summary_risk_label"):
            validation_summary = str(self._results_summary_risk_label.text() or "").strip()
        if validation_summary:
            parts.append(validation_summary)

        comparison_summary = str(self._result_comparison_summary() or "").strip()
        if comparison_summary:
            parts.append(comparison_summary)

        current_metrics = self._history_result_metrics(current)
        metric_parts = []
        strain_active = False
        if self._current_technique == "saxs":
            strain_active = bool(self._saxs_strain_evidence_snapshot(current.get("parameters"), analysis_evidence).get("active"))
        if strain_active:
            for key in ("Q_star_rel_mean", "phi_void_mean", "f_Herman_mean", "porod_slope_mean", "void_detected_frames"):
                value = current_metrics.get(key, "")
                if value:
                    metric_parts.append(f"{key}={value}")
        else:
            for key in ("r_squared", "L_nm", "Xc_pct", "Tm_peak_C", "Tc_peak_C", "quality_score"):
                value = current_metrics.get(key, "")
                if value:
                    metric_parts.append(f"{key}={value}")
        if metric_parts:
            parts.append(tr("RESULTS_REVIEW_METRICS", ", ".join(metric_parts[:4])))

        if self._current_technique == "ir":
            parts.extend(_build_ir_temperature_2d_user_summary(analysis_evidence))
            ir_support = self._ir_support_block_text(analysis_evidence)
            if ir_support:
                parts.append(ir_support)

        source_summary = self._result_source_summary_text(current)
        if source_summary:
            parts.append(source_summary)

        if self._current_technique == "waxs":
            waxs_metric_parts = []
            for key in ("n_peaks", "Xc_pct", "D_Scherrer_nm"):
                value = current_metrics.get(key, "")
                if value:
                    waxs_metric_parts.append(f"{key}={value}")
            support = []
            for label, key in (
                ("peak", "peak_support_score"),
                ("background", "background_stability_score"),
                ("phase", "phase_support_score"),
                ("size", "size_support_score"),
                ("waxs_support_score", "waxs_support_score"),
            ):
                value = analysis_evidence.get(key)
                if value is not None:
                    support.append(f"{label}={self._format_score_value(value)}")
            if waxs_metric_parts or support:
                parts.append(tr("WAXS_REVIEW_CORE", ", ".join(waxs_metric_parts[:3] or [tr("AI_TUNING_EMPTY_VALUE")])))
                if support:
                    parts.append(tr("WAXS_REVIEW_SUPPORT", " ".join(support[:5])))
            parts.extend(self._waxs_result_semantic_lines(current_metrics, analysis_evidence))
        if self._current_technique == "saxs":
            params = current.get("parameters") if isinstance(current.get("parameters"), dict) else {}
            parts.extend(self._saxs_result_semantic_lines(params, analysis_evidence))
            strain_text = self._saxs_strain_summary_text(params, analysis_evidence)
            if strain_text:
                parts.append(f"SAXS | {strain_text}")
            saxs_method_bits = []
            lc_method = str(params.get("lc_method") or current_metrics.get("lc_method") or "").strip()
            if lc_method:
                saxs_method_bits.append(f"lc_method={lc_method}")
            skip_reason = str(params.get("calibration_skipped_reason") or current_metrics.get("calibration_skipped_reason") or "").strip()
            if skip_reason:
                saxs_method_bits.append(f"calibration_skipped_reason={skip_reason}")
            fallback_active = params.get("calibrated_fallback_active")
            if fallback_active is not None:
                saxs_method_bits.append(f"calibrated_fallback_active={bool(fallback_active)}")
            if saxs_method_bits:
                parts.append("SAXS | " + ", ".join(saxs_method_bits[:3]))
        fallback_text = self._fallback_evidence_summary_text(analysis_evidence)
        if fallback_text:
            parts.append(fallback_text)

        history_context = self._current_result_history_context(current)
        tuning_context = self._current_result_tuning_context(current)
        if str(self._current_result_origin() or "").strip() == "controlled_optimization_rerun":
            tuning_goal = ""
            if isinstance(tuning_context, dict) and tuning_context:
                tuning_goal = str(tuning_context.get("tuning_goal_label") or "").strip()
                if not tuning_goal:
                    tuning_goal = self._ai_tuning_goal_label(str(tuning_context.get("tuning_goal") or "").strip())
            if not tuning_goal and isinstance(history_context, dict) and history_context:
                tuning_goal = str(history_context.get("tuning_goal_label") or "").strip()
                if not tuning_goal:
                    tuning_goal = self._ai_tuning_goal_label(str(history_context.get("tuning_goal") or "").strip())
            if tuning_goal:
                parts.append(tr("RESULTS_REVIEW_TUNING_GOAL", tuning_goal))

            benchmark_text = ""
            if isinstance(tuning_context, dict) and tuning_context:
                benchmark_text = str(tuning_context.get("benchmark_text") or "").strip()
                if not benchmark_text and str(tuning_context.get("summary") or "").strip():
                    benchmark_text = str(tuning_context.get("summary") or "").strip()
            if not benchmark_text and isinstance(history_context, dict) and history_context:
                benchmark_text = str(history_context.get("benchmark_text") or "").strip()
                if not benchmark_text:
                    benchmark_summary = history_context.get("benchmark_summary") if isinstance(history_context.get("benchmark_summary"), dict) else {}
                    if isinstance(benchmark_summary, dict) and benchmark_summary:
                        benchmark_text = self._benchmark_summary_text(benchmark_summary)
            if benchmark_text:
                parts.append(benchmark_text)

            stop_reason = ""
            remaining_risks = ""
            next_goal = ""
            if isinstance(tuning_context, dict) and tuning_context:
                stop_reason = str(tuning_context.get("stop_reason") or "").strip()
                remaining_risks = str(tuning_context.get("remaining_risks") or "").strip()
                next_goal = str(tuning_context.get("next_goal") or "").strip()
            if isinstance(history_context, dict) and history_context:
                if not stop_reason:
                    stop_reason = str(history_context.get("stop_reason") or "").strip()
                if not remaining_risks:
                    remaining_risks = str(history_context.get("remaining_risks") or "").strip()
                if not next_goal:
                    next_goal = str(history_context.get("next_goal") or "").strip()
            if stop_reason:
                parts.append(stop_reason)
            if remaining_risks:
                parts.append(remaining_risks)
            if next_goal:
                parts.append(next_goal)
            if not benchmark_text:
                parts.append(tr("RESULTS_REVIEW_NO_BENCHMARK"))
            if not stop_reason and not remaining_risks:
                parts.append(tr("RESULTS_REVIEW_NO_RISK"))

            if isinstance(tuning_context, dict) and tuning_context:
                chain_text = self._ai_tuning_chain_snapshot(tuning_context)
                if chain_text:
                    parts.append(chain_text)

            joint_context = self._joint_ai_context()
            if isinstance(joint_context, dict) and joint_context:
                joint_summary = str(joint_context.get("summary") or "").strip()
                joint_reminder = self._joint_ai_reminder_text(joint_context)
                joint_parts = [part for part in [joint_summary, joint_reminder] if part]
                if joint_parts:
                    parts.append(" | ".join(joint_parts))

        boundary_text = self._responsibility_boundary_summary()
        if boundary_text:
            parts.append(boundary_text)
        return " | ".join(parts)

    def _responsibility_boundary_summary(self) -> str:

        if get_language() == "zh":
            return "Boundary | 边界 | core 负责证据，AI 只给有限建议，orchestrator 负责受控试验与回滚，用户负责最终判断"
        return "Boundary | core provides evidence, AI only suggests, orchestrator guards trials and rollback, user makes the final judgment"

    def _task_type_label(self, input_mode: str) -> str:

        key = str(input_mode or "").strip().lower()
        mapping = {
            "single": "Single-file analysis",
            "batch": "Batch analysis",
            "directory": "Directory analysis",
            "multi_sample": "Multi-sample analysis",
            "joint": "Joint analysis",
        }
        return mapping.get(key, "Analysis run")

    def _export_context_payload(self, *, report_path="") -> dict:

        current_technique = str(self._current_technique or "").strip()
        current_submodule = str(getattr(self, "_current_submodule_id", "") or "").strip()
        input_mode = str(getattr(self, "_current_input_mode", "") or "").strip()
        current_result = self._current_results_record()
        tuning_context = self._current_result_tuning_context(current_result)
        if not isinstance(tuning_context, dict):
            tuning_context = {}
        joint_context = self._joint_ai_context()
        if not isinstance(joint_context, dict):
            joint_context = {}
        history_context = self._history_context_snapshot(tuning_context=tuning_context, joint_context=joint_context)
        primary_report = ""
        if report_path:
            try:
                report_file = Path(report_path)
                report_parent = report_file.parent.name or "report"
                primary_report = Path(report_parent, report_file.name).as_posix()
            except ValueError:
                primary_report = str(report_path)
        result_origin = self._current_result_origin()
        recommended = [primary_report or "report/ (no HTML report generated)", "metadata/export_manifest.json", "data/"]
        analysis_evidence = self._current_analysis_evidence()
        ir_export_semantics = ""
        if current_technique == "ir":
            ir_export_semantics = " | ".join(_build_ir_temperature_2d_user_summary(analysis_evidence))
        review_summary = self._result_review_summary()
        if ir_export_semantics:
            review_summary = " | ".join(part for part in [ir_export_semantics, review_summary] if str(part).strip())
        return {
            "task_type": self._task_type_label(input_mode),
            "technique_id": current_technique,
            "technique_label": self._history_technique_text(current_technique),
            "submodule_id": current_submodule,
            "submodule_label": self._history_submodule_text(current_submodule) or current_submodule,
            "input_mode": input_mode,
            "source_data_path": str(self._current_filepath or ""),
            "result_origin": result_origin,
            "result_origin_label": self._result_origin_label(result_origin),
            "used_controlled_optimization": result_origin == "controlled_optimization_rerun",
            "confirmed_result": bool(getattr(self, "_current_result_confirmed_flag", False)),
            "decision_owner": "user",
            "decision_owner_label": tr("EXPORT_DECISION_OWNER_USER"),
            "review_priority": [
                "report/",
                "metadata/export_manifest.json",
                "data/",
            ] if result_origin == "controlled_optimization_rerun" else [
                "report/",
                "data/",
                "metadata/export_manifest.json",
            ],
            "recommended_reading_order": recommended,
            "comparison_summary": self._result_comparison_summary(),
            "review_summary": review_summary,
            "validation_summary": self._history_validation_summary(self._current_results_record()),
            "validation_chain": " | ".join(
                part for part in [
                    str(history_context.get("benchmark_text") or "").strip(),
                    self._ai_tuning_chain_snapshot(tuning_context),
                ]
                if part
            ),
            "benchmark_text": str(history_context.get("benchmark_text") or "").strip(),
            "joint_summary": str(history_context.get("joint_summary") or "").strip(),
            "history_context": history_context,
            "work_memory_summary": self._work_memory_summary(),
            "responsibility_boundary": self._responsibility_boundary_summary(),
            "paper_figure_status": ir_export_semantics,
        }


    def _export_results(self):

        if not self._results and not self._batch_results:

            self.log(tr("LOG_NO_RESULTS")); return

        import shutil

        save_dir = QFileDialog.getExistingDirectory(self, tr("DIALOG_EXPORT_TITLE"), self._get_last_dir())

        if not save_dir:

            return

        self._save_last_dir(save_dir)

        save_root = os.path.join(save_dir, "PolyNexus_Export")
        bundle_dirs = self._export_bundle_dirs(save_root)

        out_src = self._output_dir
        copied_sections = []

        if out_src and os.path.isdir(out_src):

            for sub in ['figures', 'data', 'report', 'metadata']:

                src = os.path.join(out_src, sub)

                dst = str(bundle_dirs[sub])

                if os.path.isdir(src):

                    shutil.copytree(src, dst, dirs_exist_ok=True)

                    self.log(tr("LOG_COPIED").format(sub))
                    copied_sections.append(sub)



        # Generate HTML report

        report_path = ""
        try:

            from ..core.report import generate_report, save_report

            html = generate_report(

                project_name=self._project_label.text(),

                output_dir=self._output_dir,

                dsc_results=[self._results.get('dsc')] if 'dsc' in self._results else None,

                waxs_results=[self._results.get('waxs')] if 'waxs' in self._results else None,

                saxs_results=[self._results.get('saxs')] if 'saxs' in self._results else None,

                ir_results=[self._results.get('ir')] if 'ir' in self._results else None,

                nmr_results=[self._results.get('nmr')] if 'nmr' in self._results else None,

            )

            report_path = save_report(html, str(bundle_dirs["report"]))

            self.log(tr("LOG_REPORT_PATH", report_path))

        except Exception as e:

            self.log(tr("LOG_REPORT_SKIPPED").format(e))
            logger.warning("Failed to generate analysis report.", exc_info=True)

        self._write_export_manifest(save_root, report_path=report_path, copied_sections=copied_sections)
        self._write_export_readme(save_root, report_path=report_path)
        self._last_export_bundle = save_root
        self._save_settings()
        self._update_workspace_context()
        self.log(tr("LOG_EXPORT_DONE").format(save_root))



    def _on_chart_editor_saved(self, filepath):

        """Refresh gallery and preview after ChartEditor saves a figure."""

        if not filepath:

            return

        sender = self.sender()

        static_file_mode = False

        if sender is not None and hasattr(sender, "is_static_file_mode"):

            static_file_mode = bool(sender.is_static_file_mode())

        self._current_figure_path = filepath

        self._refresh_saved_figure_in_gallery(filepath)

        if hasattr(self, '_figure_preview') and self._figure_preview.isVisible():

            self._figure_preview.load_figure(filepath)

        if static_file_mode:

            self.log(tr("LOG_CHART_SAVED", filepath))
            return

        self.log(tr("LOG_CHART_SAVED", filepath))

    def _refresh_saved_figure_in_gallery(self, filepath):

        if not filepath or not hasattr(self, '_chart_gallery'):

            return

        existing_paths = self._chart_gallery.figure_paths()
        target = os.path.normcase(os.path.abspath(filepath))
        exists_in_gallery = any(
            os.path.normcase(os.path.abspath(path)) == target
            for path in existing_paths
        )

        if exists_in_gallery:

            self._chart_gallery.refresh_figure(filepath)

        else:

            self._chart_gallery.load_files(existing_paths + [filepath])

        self._chart_gallery.select_figure(filepath, emit=False)

    def log(self, msg):

        # UI-only log sink for status and export messages.
        # Per-run file logging is handled by worker log handlers.

        ts = datetime.now().strftime("%H:%M:%S")

        line = f"[{ts}] {msg}"

        self._log_panel.append(line)

        sb = self._log_panel.verticalScrollBar()

        sb.setValue(sb.maximum())


    def _read_warning_count(self):

        log_path = Path("polynexus.log")
        if not log_path.exists():
            return 0
        try:
            with log_path.open("r", encoding="utf-8", errors="ignore") as fh:
                return sum(1 for line in fh if "[WARNING]" in line)
        except Exception:
            logger.warning("Failed to read warning count from log file.", exc_info=True)
            return 0


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


    def _result_to_jsonable(self, value):

        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, dict):
            return {str(k): self._result_to_jsonable(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._result_to_jsonable(v) for v in value]
        if hasattr(value, "tolist"):
            try:
                return self._result_to_jsonable(value.tolist())
            except Exception:
                logger.warning("Failed to convert array-like value with tolist().", exc_info=True)
        if hasattr(value, "item"):
            try:
                return value.item()
            except Exception:
                logger.warning("Failed to unwrap scalar value with item().", exc_info=True)
        return str(value)


    def _extract_result_r2(self, payload):

        candidates = (
            payload.get("r2"),
            payload.get("r_squared"),
            payload.get("R2"),
        )
        parameters = payload.get("parameters")
        if isinstance(parameters, dict):
            candidates += (
                parameters.get("r2"),
                parameters.get("r_squared"),
                parameters.get("R2"),
            )
        for candidate in candidates:
            try:
                return float(candidate)
            except (TypeError, ValueError):
                continue
        return float("nan")


    def _history_run_r2(self, run):

        summary = run.get("results_summary") if isinstance(run, dict) else {}
        if not isinstance(summary, dict):
            summary = {}
        return self._extract_result_r2(summary)


    def _refresh_history(self):

        try:
            if not hasattr(self, "_history_table"):
                return

            selected_record = self._selected_history_record()
            selected_run_id = (
                str(selected_record.get("id") or "")
                if isinstance(selected_record, dict)
                else ""
            )

            db = self._ensure_sample_db()
            selected = (
                self._history_filter_combo.currentData()
                if hasattr(self, "_history_filter_combo")
                else ""
            )

            all_rows = []
            samples = db.list_samples(limit=10000)
            for sample in samples:
                sample_id = sample.get("id")
                if not sample_id:
                    continue
                for batch in db.get_batches(sample_id):
                    batch_id = batch.get("id")
                    if not batch_id:
                        continue
                    for run in db.get_analysis_runs(batch_id):
                        all_rows.append(run)

            all_rows.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)

            if hasattr(self, "_history_filter_combo"):
                current = str(self._history_filter_combo.currentData() or "")
                techniques = sorted({
                    str(run.get("technique") or "")
                    for run in all_rows
                    if str(run.get("technique") or "")
                })
                base = ["saxs", "waxs", "dsc", "ir", "nmr"]
                items = base + [tech for tech in techniques if tech not in base]
                self._set_history_filter_items(items, current)
                active_filter = str(self._history_filter_combo.currentData() or "")
            else:
                active_filter = selected

            if not active_filter:
                rows = all_rows
            else:
                rows = [
                    run for run in all_rows
                    if str(run.get("technique") or "") == active_filter
                ]

            self._history_cache = rows
            self._history_table.clearSpans()
            self._history_table.setRowCount(len(rows))
            if not rows:
                empty_text = (
                    tr("HISTORY_EMPTY_ALL")
                    if not active_filter
                    else tr("HISTORY_EMPTY_FILTER", self._history_technique_text(active_filter))
                )
                self._history_table.setRowCount(1)
                self._history_table.setSpan(0, 0, 1, self._history_table.columnCount())
                item = QTableWidgetItem(empty_text)
                item.setToolTip(empty_text)
                self._history_table.setItem(0, 0, item)
                self._history_table.clearSelection()
                self._update_history_action_state()
                return

            for row_index, run in enumerate(rows):
                submodule_id = str(run.get("submodule") or "")
                technique_id = str(run.get("technique") or "")
                status_value = str(run.get("status") or "")
                metrics_tooltip = self._history_metrics_tooltip(run)
                values = [
                    self._format_history_timestamp(run.get("created_at")),
                    self._history_technique_text(technique_id),
                    self._history_submodule_text(submodule_id),
                    self._format_r2_value(self._history_run_r2(run)),
                    self._history_status_text(run),
                    self._history_validation_summary(run),
                    self._history_confirmation_label(run),
                ]
                for col_index, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    item.setToolTip(value)
                    if col_index in {0, 3} and metrics_tooltip:
                        item.setToolTip(metrics_tooltip)
                    if col_index == 1 and technique_id:
                        item.setToolTip(technique_id)
                    if col_index == 2 and submodule_id:
                        item.setToolTip(submodule_id)
                    if col_index == 4:
                        tooltip_bits = []
                        if not self._history_has_available_source(run):
                            tooltip_bits.append(value)
                        elif status_value:
                            tooltip_bits.append(status_value)
                        if technique_id == "saxs" and metrics_tooltip:
                            tooltip_bits.append(metrics_tooltip)
                        item.setToolTip(" | ".join(part for part in tooltip_bits if part))
                    if col_index == 5:
                        item.setToolTip(value)
                    self._history_table.setItem(row_index, col_index, item)

            if selected_run_id:
                for row_index, run in enumerate(rows):
                    if str(run.get("id") or "") == selected_run_id:
                        self._history_table.selectRow(row_index)
                        break
            self._update_history_action_state()
        except Exception as e:
            logger.warning("Failed to refresh history records: %s", e)
            logger.warning("History refresh traceback follows.", exc_info=True)


    def _format_r2_value(self, value):

        try:
            return f"{float(value):.4f}"
        except (TypeError, ValueError):
            return "nan"


    def _format_history_timestamp(self, value) -> str:

        text = str(value or "").strip()
        if not text:
            return ""
        normalized = text.replace("T", " ")
        for pattern in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                dt = datetime.strptime(normalized, pattern)
                return dt.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                continue
        return normalized


    def _set_history_filter_items(self, techniques, current_value="") -> None:

        if not hasattr(self, "_history_filter_combo"):
            return

        combo = self._history_filter_combo
        current = str(current_value or "")
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(tr("HISTORY_FILTER_ALL"), "")
        for technique in techniques:
            tech = str(technique or "").strip()
            if not tech:
                continue
            combo.addItem(self._history_technique_text(tech), tech)
        idx = combo.findData(current)
        if idx < 0:
            idx = 0
        combo.setCurrentIndex(idx)
        combo.blockSignals(False)


    def _selected_history_row(self):

        table = getattr(self, "_history_table", None)
        if table is None:
            return -1
        selection = table.selectionModel()
        if selection is None or not selection.hasSelection():
            return -1
        rows = selection.selectedRows()
        if not rows:
            return -1
        return rows[0].row()


    def _selected_history_record(self):

        row = self._selected_history_row()
        cache = getattr(self, "_history_cache", [])
        if row < 0 or row >= len(cache):
            return None
        return cache[row]


    def _update_history_action_state(self):

        record = self._selected_history_record()
        has_record = record is not None
        has_source = self._history_has_available_source(record)
        has_compare = self._history_has_comparison_target(record)
        if hasattr(self, "_history_copy_summary_btn"):
            self._history_copy_summary_btn.setEnabled(has_record)
            self._history_copy_summary_btn.setToolTip(self._history_copy_summary_tooltip(record))
        if hasattr(self, "_history_restore_btn"):
            self._history_restore_btn.setEnabled(has_record and has_source)
            self._history_restore_btn.setToolTip(self._history_restore_tooltip(record))
        if hasattr(self, "_history_rerun_btn"):
            self._history_rerun_btn.setEnabled(has_record and has_source)
            self._history_rerun_btn.setToolTip(self._history_rerun_tooltip(record))
        if hasattr(self, "_history_compare_btn"):
            self._history_compare_btn.setEnabled(has_compare)
            self._history_compare_btn.setToolTip(self._history_compare_tooltip(record))
        if hasattr(self, "_history_confirm_btn"):
            self._history_confirm_btn.setEnabled(has_record)
            self._history_confirm_btn.setText(
                tr("RESULTS_CONFIRM_CLEAR") if self._history_confirmation_label(record) == tr("RESULTS_CONFIRM_STATUS_CONFIRMED") else tr("RESULTS_CONFIRM_MARK")
            )
            self._history_confirm_btn.setToolTip(
                self._history_confirmation_label(record) if has_record else tr("HISTORY_TOOLTIP_SELECT")
            )


    def _restore_history_record(self, record, log_key="LOG_HISTORY_RESTORED"):

        if not isinstance(record, dict):
            return False

        technique = str(record.get("technique") or "")
        submodule = str(record.get("submodule") or "")
        created_at = str(record.get("created_at") or "")
        output_dir = str(record.get("output_dir") or "").strip()
        parameters = record.get("parameters") if isinstance(record.get("parameters"), dict) else {}
        summary = record.get("results_summary") if isinstance(record.get("results_summary"), dict) else {}
        data_file = str(summary.get("data_file") or "").strip()

        if not technique:
            return False

        if technique:
            self._on_technique_selected(technique)
            btn = self._nav_buttons.get(technique)
            if btn:
                btn.setChecked(True)

        if submodule:
            btn = self._nav_buttons.get(submodule)
            if btn:
                btn.setChecked(True)
            self._on_submodule_selected(technique or self._current_technique, submodule)

        if data_file and Path(data_file).exists():
            self._set_input_path(data_file, is_dir=Path(data_file).is_dir())
            self._save_last_dir(data_file)
        elif data_file:
            self.log(tr("LOG_HISTORY_DATA_MISSING", data_file))
            return False

        if output_dir:
            self._output_dir = output_dir
            if hasattr(self, "_output_input"):
                self._output_input.setText(output_dir)

        if parameters:
            self._apply_best_config(parameters)

        confirmed = bool(record.get("confirmed"))
        if not confirmed and isinstance(summary, dict):
            confirmed = bool(summary.get("confirmed"))
        self._current_result_confirmed_flag = confirmed
        self._update_results_confirm_panel()

        history_context = summary.get("history_context") if isinstance(summary.get("history_context"), dict) else {}
        if isinstance(history_context, dict) and history_context:
            restored_tuning_context = history_context.get("tuning_context") if isinstance(history_context.get("tuning_context"), dict) else {}
            if isinstance(restored_tuning_context, dict):
                restored_tuning_context = dict(restored_tuning_context)
                joint_context = history_context.get("joint_ai_context") if isinstance(history_context.get("joint_ai_context"), dict) else {}
                if isinstance(joint_context, dict) and joint_context and not isinstance(restored_tuning_context.get("joint_ai_context"), dict):
                    restored_tuning_context["joint_ai_context"] = joint_context
                if restored_tuning_context:
                    self._last_ai_tuning_context = restored_tuning_context

        restored_payload = self._result_to_jsonable(record)
        if isinstance(restored_payload, dict) and restored_payload:
            self._results[str(technique).strip().lower()] = restored_payload

        self._update_workspace_context()
        self._update_work_memory_panel()
        self._update_results_review_panel()

        if hasattr(self, "_tabs"):
            self._tabs.setCurrentIndex(0)

        ts = datetime.now().strftime("%H:%M:%S")
        technique_label = self._history_technique_text(technique)
        submodule_label = self._history_record_context_text(record)
        created_label = self._format_history_timestamp(created_at)
        line = (
            f'[{ts}] <span style="color:#2563eb;">'
            f"{tr(log_key, technique_label, submodule_label, created_label)}"
            f"</span>"
        )
        self._log_panel.append(line)
        sb = self._log_panel.verticalScrollBar()
        sb.setValue(sb.maximum())
        return True


    def _on_history_restore_requested(self):

        record = self._selected_history_record()
        if record is None:
            self.log(tr("LOG_HISTORY_SELECT_RUN"))
            return
        self._restore_history_record(record)


    def _on_history_rerun_requested(self):

        record = self._selected_history_record()
        if record is None:
            self.log(tr("LOG_HISTORY_SELECT_RUN"))
            return
        if not self._restore_history_record(record, log_key="LOG_HISTORY_RERUN_READY"):
            return
        self._run_analysis()


    def _history_compare_record(self, record):

        if not isinstance(record, dict):
            return None
        batch_id = str(record.get("batch_id") or "")
        run_id = str(record.get("id") or "")
        technique = str(record.get("technique") or "")
        submodule = str(record.get("submodule") or "")
        if not batch_id or not run_id or not technique:
            return None

        db = self._ensure_sample_db()
        runs = db.get_analysis_runs(batch_id)
        comparable = [
            run for run in runs
            if str(run.get("technique") or "") == technique
        ]
        if submodule:
            comparable = [
                run for run in comparable
                if str(run.get("submodule") or "") == submodule
            ]
        for index, run in enumerate(comparable):
            if str(run.get("id") or "") == run_id:
                if index + 1 < len(comparable):
                    return comparable[index + 1]
                if index > 0:
                    return comparable[index - 1]
                break
        for run in comparable:
            if str(run.get("id") or "") != run_id:
                return run
        return None


    def _history_has_comparison_target(self, record) -> bool:

        return self._history_compare_record(record) is not None


    def _history_has_available_source(self, record) -> bool:

        if not isinstance(record, dict):
            return False
        summary = record.get("results_summary")
        if not isinstance(summary, dict):
            return True
        data_file = str(summary.get("data_file") or "").strip()
        if not data_file:
            return True
        return Path(data_file).exists()


    def _history_status_text(self, record) -> str:

        status = self._history_status_label(record)
        origin_label = self._history_result_origin_label(record)
        parts = [part for part in [status, origin_label] if part]
        base = " | ".join(parts)
        if self._history_has_available_source(record):
            return base
        if base:
            return f"{base} | {tr('HISTORY_STATUS_SOURCE_MISSING')}"
        return tr("HISTORY_STATUS_SOURCE_MISSING")


    def _history_submodule_text(self, submodule_id: str) -> str:

        key = str(submodule_id or "").strip()
        if not key:
            return ""
        mapping = SIDEBAR_MODULE_TEXT.get(key)
        if isinstance(mapping, dict):
            return _lang_text(mapping, key)
        return key


    def _history_technique_text(self, technique_id: str) -> str:

        key = str(technique_id or "").strip()
        if not key:
            return ""
        return TECHNIQUE_LABELS.get(key, key.upper())


    def _history_status_label(self, record) -> str:

        raw_status = str(record.get("status") or "").strip().lower() if isinstance(record, dict) else ""
        key = {
            "completed": "SAMPLE_RUN_STATUS_COMPLETED",
            "pending": "SAMPLE_RUN_STATUS_PENDING",
            "failed": "SAMPLE_RUN_STATUS_FAILED",
        }.get(raw_status)
        label = tr(key) if key else (str(record.get("status") or "").strip() if isinstance(record, dict) else "")
        if not label or raw_status != "completed" or not isinstance(record, dict):
            return label
        if str(record.get("technique") or "").strip().lower() != "saxs":
            return label

        metrics = self._history_result_metrics(record)
        lc_status = self._saxs_lc_status_text(metrics.get("lc_reliability_status") or record.get("lc_reliability_status"))
        lc_method = self._saxs_calibration_method_text(metrics.get("lc_method") or record.get("lc_method"))
        fallback_active = metrics.get("calibrated_fallback_active")
        suffix_bits = [bit for bit in [lc_status, lc_method] if bit]
        if not suffix_bits and fallback_active is not None:
            suffix_bits.append("回退" if get_language() == "zh" else "fallback")
        if suffix_bits:
            label = f"{label} | " + " | ".join(suffix_bits[:3])
        return label


    def _history_restore_tooltip(self, record) -> str:

        if not isinstance(record, dict):
            return tr("HISTORY_TOOLTIP_SELECT")
        if not self._history_has_available_source(record):
            return tr("HISTORY_TOOLTIP_SOURCE_MISSING")
        return tr("HISTORY_RESTORE_TOOLTIP")


    def _history_rerun_tooltip(self, record) -> str:

        if not isinstance(record, dict):
            return tr("HISTORY_TOOLTIP_SELECT")
        if not self._history_has_available_source(record):
            return tr("HISTORY_TOOLTIP_SOURCE_MISSING")
        return tr("HISTORY_RERUN_TOOLTIP")


    def _history_compare_tooltip(self, record) -> str:

        if not isinstance(record, dict):
            return tr("HISTORY_TOOLTIP_SELECT")
        if not self._history_has_comparison_target(record):
            return tr("HISTORY_TOOLTIP_COMPARE_UNAVAILABLE")
        return tr("HISTORY_COMPARE_TOOLTIP")


    def _history_copy_summary_tooltip(self, record) -> str:

        if not isinstance(record, dict):
            return tr("HISTORY_TOOLTIP_SELECT")
        return tr("HISTORY_COPY_SUMMARY_TOOLTIP")


    def _history_result_metrics(self, record):

        summary = record.get("results_summary") if isinstance(record, dict) else {}
        if not isinstance(summary, dict):
            summary = {}

        payload = summary.get("result") if isinstance(summary.get("result"), dict) else {}
        candidate = payload.get("parameters") if isinstance(payload.get("parameters"), dict) else {}
        evidence = self._history_record_analysis_evidence(record)
        record_params = record.get("parameters") if isinstance(record, dict) and isinstance(record.get("parameters"), dict) else {}
        if isinstance(record_params, dict) and record_params:
            for key, value in self._flatten_params(record_params):
                if key not in candidate:
                    candidate[key] = value
        excluded_summary_keys = {
            "result",
            "data_file",
            "project_label",
            "status",
            "polymer_type",
            "technique",
            "submodule",
            "confirmed",
            "validation_passed",
            "validation_summary",
            "validation_warnings",
            "quality_flags",
            "result_origin",
            "ai_tuned",
            "history_context",
            "review_summary",
            "work_memory_summary",
            "comparison_summary",
            "benchmark_summary",
            "benchmark_text",
            "tuning_context",
            "tuning_goal",
            "tuning_goal_label",
            "stop_reason",
            "remaining_risks",
            "next_goal",
            "joint_ai_context",
            "joint_summary",
        }
        for key, value in summary.items():
            if key in excluded_summary_keys or key in candidate:
                continue
            if isinstance(value, (dict, list, tuple, set)):
                continue
            candidate[key] = value
        if not candidate:
            candidate = {
                key: value
                for key, value in summary.items()
                if key not in excluded_summary_keys
            }
        if isinstance(evidence, dict) and evidence and str(record.get("technique") or "").strip().lower() == "waxs":
            for key in (
                "n_peaks",
                "Xc_pct",
                "D_Scherrer_nm",
                "peak_support_score",
                "background_stability_score",
                "phase_support_score",
                "size_support_score",
                "waxs_support_score",
            ):
                value = evidence.get(key)
                if value is not None and key not in candidate:
                    candidate[key] = value
            feature_evidence = evidence.get("feature_evidence", {})
            if not isinstance(feature_evidence, dict):
                feature_evidence = {}
            sequence_evidence = feature_evidence.get("sequence_evidence", {})
            if not isinstance(sequence_evidence, dict):
                sequence_evidence = {}
            peak_family_evidence = feature_evidence.get("peak_family_evidence", {})
            if not isinstance(peak_family_evidence, dict):
                peak_family_evidence = {}
            trend_evidence = feature_evidence.get("trend_evidence", feature_evidence.get("crystallinity_trend_evidence", {}))
            if not isinstance(trend_evidence, dict):
                trend_evidence = {}
            scherrer_trend_evidence = feature_evidence.get("scherrer_trend_evidence", {})
            if not isinstance(scherrer_trend_evidence, dict):
                scherrer_trend_evidence = {}
            transition_evidence = feature_evidence.get("transition_evidence", {})
            if not isinstance(transition_evidence, dict):
                transition_evidence = {}
            for key, source in (
                ("temperature_axis_confidence", sequence_evidence),
                ("peak_family_continuity_score", peak_family_evidence),
                ("Xc_trend_support_score", trend_evidence),
                ("D_trend_support_score", scherrer_trend_evidence),
                ("transition_support_score", transition_evidence),
            ):
                value = source.get(key) if isinstance(source, dict) else None
                if value is not None and key not in candidate:
                    candidate[key] = value
        elif isinstance(evidence, dict) and evidence and str(record.get("technique") or "").strip().lower() == "saxs":
            feature_evidence = evidence.get("feature_evidence", {})
            if not isinstance(feature_evidence, dict):
                feature_evidence = {}
            condition_evidence = feature_evidence.get("condition_evidence", {})
            if not isinstance(condition_evidence, dict):
                condition_evidence = {}
            strain_structure_evidence = feature_evidence.get("strain_structure_evidence", {})
            if not isinstance(strain_structure_evidence, dict):
                strain_structure_evidence = {}
            if condition_evidence.get("condition_label") == "strain" or strain_structure_evidence:
                for key in (
                    "strain_axis_confidence",
                    "strain_monotonic",
                    "strain_missing_count",
                    "strain_duplicate_count",
                    "strain_min_pct",
                    "strain_max_pct",
                ):
                    value = condition_evidence.get(key)
                    if value is None and key not in candidate:
                        value = evidence.get(key)
                    if value is not None and key not in candidate:
                        candidate[key] = value
                for key in (
                    "Q_star_rel_mean",
                    "Q_star_rel_span",
                    "phi_void_mean",
                    "phi_void_span",
                    "void_detected_frames",
                    "f_Herman_mean",
                    "f_Herman_span",
                    "porod_slope_mean",
                    "porod_slope_span",
                ):
                    value = strain_structure_evidence.get(key)
                    if value is not None and key not in candidate:
                        candidate[key] = value
        if isinstance(candidate, dict):
            candidate = {
                key: value
                for key, value in candidate.items()
                if key not in {
                    "validation_passed",
                    "validation_summary",
                    "validation_warnings",
                    "quality_flags",
                }
            }

        rows = {}
        for key, value in self._flatten_params(candidate):
            rows[str(key)] = "" if value is None else str(value)
        return rows

    def _history_validation_summary(self, record) -> str:
        if not isinstance(record, dict):
            return ""
        summary = record.get("results_summary") if isinstance(record.get("results_summary"), dict) else {}
        if not isinstance(summary, dict):
            summary = {}

        candidates = [
            summary.get("validation_summary"),
            summary.get("result", {}).get("validation_summary") if isinstance(summary.get("result"), dict) else "",
            record.get("validation_summary"),
        ]
        validation_summary = ""
        for candidate in candidates:
            text = str(candidate or "").strip()
            if text:
                validation_summary = text
                break

        validation_warnings = []
        for container in (
            summary,
            summary.get("result", {}) if isinstance(summary.get("result"), dict) else {},
            record,
        ):
            if not isinstance(container, dict):
                continue
            warnings = container.get("validation_warnings")
            if isinstance(warnings, list):
                validation_warnings.extend(str(item).strip() for item in warnings if str(item).strip())

        if not validation_summary:
            quality_flag_summary = ""
            result_payload = summary.get("result", {}) if isinstance(summary.get("result"), dict) else {}
            if isinstance(result_payload, dict) and result_payload:
                quality_flag_summary = self._quality_flag_summary_text(result_payload)
            if quality_flag_summary:
                return quality_flag_summary
            return ""
        if validation_summary == "All checks passed":
            result_payload = summary.get("result", {}) if isinstance(summary.get("result"), dict) else {}
            if isinstance(result_payload, dict) and result_payload:
                quality_flag_summary = self._quality_flag_summary_text(result_payload)
                if quality_flag_summary:
                    return quality_flag_summary
            return validation_summary
        validation_warnings = list(dict.fromkeys(validation_warnings))
        if validation_warnings:
            validation_summary = f"{validation_summary} | {', '.join(validation_warnings[:4])}"
        return validation_summary


    def _history_table_text_matrix(self):

        table = self._history_table
        cols = table.columnCount()
        rows = table.rowCount()
        if cols <= 0 or rows <= 0:
            return [], []

        headers = []
        for col in range(cols):
            header_item = table.horizontalHeaderItem(col)
            headers.append(header_item.text() if header_item is not None else "")

        matrix = []
        for row in range(rows):
            values = []
            for col in range(cols):
                item = table.item(row, col)
                values.append(item.text() if item is not None else "")
            matrix.append(values)
        return headers, matrix

    def _history_export_rows(self):

        headers, matrix = self._history_table_text_matrix()
        if not headers or not matrix:
            return [], []

        export_headers = list(headers) + ["Result origin", "AI tuned", "Source data", "Output dir"]
        rows = []
        cache = getattr(self, "_history_cache", [])
        for row_index, values in enumerate(matrix):
            record = cache[row_index] if row_index < len(cache) else {}
            summary = record.get("results_summary") if isinstance(record, dict) and isinstance(record.get("results_summary"), dict) else {}
            origin_label = self._history_result_origin_label(record) if isinstance(record, dict) else ""
            ai_tuned = "Yes" if bool(summary.get("ai_tuned")) else "No"
            source_data = str(summary.get("data_file") or "").strip() if isinstance(summary, dict) else ""
            output_dir = str(record.get("output_dir") or "").strip() if isinstance(record, dict) else ""
            rows.append(list(values) + [origin_label, ai_tuned, source_data, output_dir])
        return export_headers, rows


    def _export_history_table(self):

        self._refresh_history()
        headers, matrix = self._history_export_rows()
        if not headers or not matrix:
            return

        current_filter = ""
        if hasattr(self, "_history_filter_combo"):
            current_filter = str(self._history_filter_combo.currentData() or "").strip()
        suffix = current_filter or "all"
        default_name = f"history_{suffix}.tsv"
        start_dir = self._output_dir or self._get_last_dir()
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            tr("HISTORY_EXPORT_TITLE"),
            os.path.join(start_dir, default_name),
            tr("HISTORY_EXPORT_FILTER"),
        )
        if not path:
            return

        delimiter = "\t"
        lower_path = path.lower()
        if lower_path.endswith(".csv") or "csv" in str(selected_filter).lower():
            delimiter = ","
            if not lower_path.endswith(".csv"):
                path = f"{path}.csv"
        elif not lower_path.endswith(".tsv"):
            path = f"{path}.tsv"

        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh, delimiter=delimiter)
            writer.writerow(headers)
            writer.writerows(matrix)

        self._save_last_dir(os.path.dirname(path) or start_dir)
        self.log(tr("LOG_HISTORY_EXPORTED", len(matrix), path))


    def _copy_history_summary(self):

        record = self._selected_history_record()
        if not isinstance(record, dict):
            self.log(tr("LOG_HISTORY_SELECT_RUN"))
            return

        technique = self._history_technique_text(str(record.get("technique") or ""))
        context = self._history_record_context_text(record)
        created = self._format_history_timestamp(record.get("created_at"))
        metrics = self._history_metrics_tooltip(record, limit=6)
        lines = [part for part in [technique, context, created] if part]
        for part in self._history_context_lines(record):
            if part and part not in lines:
                lines.append(part)
        if metrics and metrics not in lines:
            lines.append(metrics)
        text = "\n".join(lines)
        QApplication.clipboard().setText(text)
        self.log(tr("LOG_HISTORY_SUMMARY_COPIED", context or technique or created))


    def _history_metrics_tooltip(self, record, *, limit=4):

        metrics = self._history_result_metrics(record)
        if not metrics:
            return ""

        technique = str(record.get("technique") or self._current_technique or "").strip().lower() if isinstance(record, dict) else ""
        if technique == "waxs":
            preferred = [
                "n_peaks",
                "Xc_pct",
                "D_Scherrer_nm",
                "temperature_axis_confidence",
                "peak_family_continuity_score",
                "transition_support_score",
                "Xc_trend_support_score",
                "D_trend_support_score",
                "peak_support_score",
                "background_stability_score",
                "phase_support_score",
                "size_support_score",
                "waxs_support_score",
            ]
        elif technique == "saxs":
            preferred = [
                "lc_nm",
                "lc_method",
                "lc_reliability_status",
                "calibrated_fallback_active",
                "calibration_skipped_reason",
                "lc_reliability_reason",
                "melting_window_status",
                "melting_window_reason",
                "Tm_onset_C",
                "Tm_peak_C",
                "Tm_end_C",
                "Xc_pct",
                "L_nm",
            ]
        else:
            preferred = [
                "L_nm",
                "lc_nm",
                "lc_reliability_status",
                "melting_window_status",
                "Xc_pct",
                "Xc",
                "D_Scherrer_nm",
                "Tm_C",
                "Tm_peak_C",
                "Tc_C",
                "Tc_peak_C",
                "Tg_C",
            ]
        ordered_keys = [key for key in preferred if key in metrics]
        ordered_keys.extend(key for key in metrics.keys() if key not in ordered_keys)
        max_items = max(1, int(limit or 0))
        if technique == "waxs":
            max_items = max(max_items, 8)
        parts = [f"{key}={metrics.get(key, '')}" for key in ordered_keys[:max_items]]
        return " | ".join(parts)


    def _show_history_comparison(self, current_record, baseline_record):

        current_metrics = self._history_result_metrics(current_record)
        baseline_metrics = self._history_result_metrics(baseline_record)
        keys = list(dict.fromkeys(list(current_metrics.keys()) + list(baseline_metrics.keys())))

        dialog = QDialog(self)
        dialog.setWindowTitle(tr("HISTORY_COMPARE_TITLE"))
        dialog.resize(760, 460)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(8)

        current_time = self._format_history_timestamp(current_record.get("created_at"))
        baseline_time = self._format_history_timestamp(baseline_record.get("created_at"))
        current_label = self._history_record_context_text(current_record)
        baseline_label = self._history_record_context_text(baseline_record)
        layout.addWidget(QLabel(tr("HISTORY_COMPARE_SUMMARY", current_time, current_label, baseline_time, baseline_label)))

        rows = []
        for key in keys:
            current_value = current_metrics.get(key, "")
            baseline_value = baseline_metrics.get(key, "")
            state = self._history_compare_state(current_value, baseline_value)
            rows.append((key, current_value, baseline_value, state))
        rows.sort(key=self._history_compare_sort_key)
        layout.addWidget(QLabel(self._history_compare_counts_text(rows)))

        table = QTableWidget(len(rows), 4)
        table.setHorizontalHeaderLabels([
            tr("HISTORY_COMPARE_COL_METRIC"),
            tr("HISTORY_COMPARE_COL_CURRENT"),
            tr("HISTORY_COMPARE_COL_BASELINE"),
            tr("HISTORY_COMPARE_COL_STATE"),
        ])
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        dialog._history_compare_copy_shortcut = QShortcut(QKeySequence.Copy, table)
        dialog._history_compare_copy_shortcut.activated.connect(
            lambda: self._copy_table_selection_to_clipboard(table)
        )

        for row_index, (key, current_value, baseline_value, state) in enumerate(rows):
            for col_index, value in enumerate([key, current_value, baseline_value, state]):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                if col_index == 3:
                    item.setForeground(self._history_compare_state_color(state))
                table.setItem(row_index, col_index, item)

        layout.addWidget(table, 1)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        dialog._history_compare_copy_button = QPushButton(tr("COMMON_COPY"))
        dialog._history_compare_copy_button.clicked.connect(
            lambda: self._copy_table_selection_to_clipboard(table)
        )
        button_row.addWidget(dialog._history_compare_copy_button)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        close_button = buttons.button(QDialogButtonBox.Close)
        if close_button is not None:
            close_button.setText(tr("COMMON_CLOSE"))
        button_row.addWidget(buttons)
        layout.addLayout(button_row)

        dialog.exec()


    def _copy_table_selection_to_clipboard(self, table):

        if table is None:
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


    def _history_compare_state(self, current_value: str, baseline_value: str) -> str:

        if current_value == baseline_value:
            return tr("HISTORY_COMPARE_STATE_SAME")
        if baseline_value == "":
            return tr("HISTORY_COMPARE_STATE_NEW")
        if current_value == "":
            return tr("HISTORY_COMPARE_STATE_REMOVED")
        return tr("HISTORY_COMPARE_STATE_CHANGED")


    def _history_compare_sort_key(self, row) -> tuple[int, str]:

        key, _current_value, _baseline_value, state = row
        priority = {
            tr("HISTORY_COMPARE_STATE_CHANGED"): 0,
            tr("HISTORY_COMPARE_STATE_NEW"): 1,
            tr("HISTORY_COMPARE_STATE_REMOVED"): 2,
            tr("HISTORY_COMPARE_STATE_SAME"): 3,
        }
        return (priority.get(state, 99), str(key))


    def _history_compare_counts_text(self, rows) -> str:

        counts = {
            tr("HISTORY_COMPARE_STATE_CHANGED"): 0,
            tr("HISTORY_COMPARE_STATE_NEW"): 0,
            tr("HISTORY_COMPARE_STATE_REMOVED"): 0,
            tr("HISTORY_COMPARE_STATE_SAME"): 0,
        }
        for _key, _current_value, _baseline_value, state in rows:
            counts[state] = counts.get(state, 0) + 1
        return tr(
            "HISTORY_COMPARE_COUNTS",
            counts.get(tr("HISTORY_COMPARE_STATE_CHANGED"), 0),
            counts.get(tr("HISTORY_COMPARE_STATE_NEW"), 0),
            counts.get(tr("HISTORY_COMPARE_STATE_REMOVED"), 0),
            counts.get(tr("HISTORY_COMPARE_STATE_SAME"), 0),
        )


    def _history_compare_state_color(self, state: str) -> QColor:

        colors = {
            tr("HISTORY_COMPARE_STATE_CHANGED"): QColor("#2563eb"),
            tr("HISTORY_COMPARE_STATE_NEW"): QColor("#16a34a"),
            tr("HISTORY_COMPARE_STATE_REMOVED"): QColor("#dc2626"),
            tr("HISTORY_COMPARE_STATE_SAME"): QColor(C_TEXT_MUTED),
        }
        return colors.get(state, QColor(C_TEXT_MUTED))


    def _history_record_context_text(self, record) -> str:

        if not isinstance(record, dict):
            return ""
        submodule = str(record.get("submodule") or "").strip()
        if submodule:
            return self._history_submodule_text(submodule)
        technique = str(record.get("technique") or "").strip()
        return self._history_technique_text(technique)


    def _on_history_compare_requested(self):

        record = self._selected_history_record()
        if record is None:
            self.log(tr("LOG_HISTORY_SELECT_RUN"))
            return

        baseline = self._history_compare_record(record)
        if baseline is None:
            self.log(tr("LOG_HISTORY_COMPARE_UNAVAILABLE"))
            return

        self._show_history_comparison(record, baseline)


    def _on_history_row_activated(self, row: int, col: int):

        try:
            if row < 0:
                return
            cache = getattr(self, "_history_cache", [])
            if row >= len(cache):
                return
            self._history_table.selectRow(row)
            self._update_history_action_state()
            self._restore_history_record(cache[row])
        except Exception as e:
            logger.warning("Failed to restore history record: %s", e)
            logger.warning("History restore traceback follows.", exc_info=True)


    def _persist_analysis_run(self, result):

        try:
            db = self._ensure_sample_db()

            if isinstance(result, dict):
                payload = self._result_to_jsonable(result)
            elif hasattr(result, "to_dict"):
                payload = self._result_to_jsonable(result.to_dict())
            else:
                payload = self._result_to_jsonable(getattr(result, "__dict__", {}))
            analysis_evidence = (
                payload.get("analysis_evidence")
                if isinstance(payload.get("analysis_evidence"), dict)
                else {}
            )

            technique = str(
                payload.get("technique")
                or self._current_technique
                or "unknown"
            )
            submodule = str(getattr(self, "_current_submodule_id", "") or "")
            data_file = Path(self._current_filepath) if self._current_filepath else None
            resolved_data_file = str(data_file.resolve()) if data_file is not None else ""
            polymer_name = str(
                payload.get("metadata", {}).get("polymer_name")
                if isinstance(payload.get("metadata"), dict) else ""
            ).strip()
            current_sample_name = str(getattr(self, "_current_sample_name", "") or "").strip()
            if current_sample_name:
                polymer_name = current_sample_name
            if not polymer_name:
                polymer_name = self._project_label.text().strip() or (
                    data_file.stem if data_file is not None else technique.upper()
                )

            existing_sample = db.find_sample_by_name(polymer_name)
            if existing_sample is not None:
                sample_id = existing_sample.get("id", "")
            else:
                sample_id = db.create_sample(
                    polymer_name,
                    tags=["gui_analysis", technique],
                    metadata={
                        "source": "gui_analysis",
                        "data_file": resolved_data_file,
                    },
                    temp=False,
                )

            batch_label = data_file.stem if data_file is not None else polymer_name
            existing_batch = None
            current_batch_id = str(getattr(self, "_current_batch_id", "") or "").strip()
            if current_batch_id:
                current_batch = db.get_batch(current_batch_id)
                if isinstance(current_batch, dict) and str(current_batch.get("sample_id", "") or "").strip() == sample_id:
                    existing_batch = current_batch
            if existing_batch is None:
                existing_batch = db.find_batch_for_source(
                    sample_id,
                    batch_label,
                    technique=technique,
                    file_path=resolved_data_file,
                )
            if existing_batch is not None:
                batch_id = existing_batch.get("id", "")
            else:
                condition_values = {
                    "technique": technique,
                    "submodule": submodule,
                }
                if self._current_sample_id:
                    condition_values["sample_id"] = str(self._current_sample_id)
                if self._current_batch_id:
                    condition_values["batch_id"] = str(self._current_batch_id)
                if self._current_sample_name:
                    condition_values["sample_name"] = str(self._current_sample_name)
                if self._current_batch_label:
                    condition_values["batch_label"] = str(self._current_batch_label)
                batch_id = db.create_batch(
                    sample_id,
                    label=batch_label,
                    instrument="PolyNexus GUI",
                    condition_type="analysis",
                    condition_values=condition_values,
                )

            if data_file is not None:
                existing_files = db.get_data_files(batch_id)
                has_file = any(
                    str(item.get("file_path", "")).strip() == resolved_data_file
                    and str(item.get("technique", "")).strip().lower() == technique.lower()
                    for item in existing_files
                )
                if not has_file:
                    db.add_data_file(
                        batch_id,
                        resolved_data_file,
                        technique,
                        submodule=submodule,
                        file_type=data_file.suffix.lower().lstrip("."),
                        import_order=len(existing_files),
                    )

            parameters = payload.get("parameters") if isinstance(payload.get("parameters"), dict) else {}
            parameters = dict(parameters)
            polymer_type = str(parameters.get("polymer_type") or "").strip()
            if not polymer_type:
                polymer_type = detect_polymer_type(polymer_name or self._infer_sample_name())
            parameters["polymer_type"] = polymer_type
            history_context = self._result_to_jsonable(self._history_context_snapshot())
            summary = {
                "technique": technique,
                "submodule": submodule,
                "data_file": resolved_data_file,
                "project_label": self._project_label.text().strip(),
                "sample_id": str(getattr(self, "_current_sample_id", "") or ""),
                "sample_name": polymer_name,
                "batch_id": str(getattr(self, "_current_batch_id", "") or ""),
                "batch_label": str(getattr(self, "_current_batch_label", "") or ""),
                "status": "completed",
                "result": payload,
                "r2": self._extract_result_r2(payload),
                "polymer_type": polymer_type,
                "ai_tuned": bool(getattr(self, "_last_ai_tuned_run", False)),
                "result_origin": "controlled_optimization_rerun" if bool(getattr(self, "_last_ai_tuned_run", False)) else "manual_run",
                "confirmed": bool(getattr(self, "_current_result_confirmed_flag", False)),
                "history_context": history_context,
            }
            db.create_analysis_run(
                batch_id,
                technique,
                submodule=submodule,
                parameters=self._result_to_jsonable(parameters),
                results_summary=self._result_to_jsonable(summary),
                analysis_evidence=self._result_to_jsonable(analysis_evidence),
                output_dir=self._output_dir,
                ai_tuned=bool(getattr(self, "_last_ai_tuned_run", False)),
                confirmed=bool(getattr(self, "_current_result_confirmed_flag", False)),
            )
            self._last_persisted_run_id = ""
            logger.info(
                "Analysis result persisted. technique=%s r2=%.4f",
                technique,
                self._extract_result_r2(payload),
            )
            self._refresh_history()
        except Exception as e:
            logger.warning("Failed to persist analysis result: %s", e)
            logger.warning("Analysis persistence traceback follows.", exc_info=True)


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


