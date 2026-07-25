from __future__ import annotations

from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from .analysis_history_service import (
    current_result_history_context as resolve_current_result_history_context,
    current_result_origin as resolve_current_result_origin,
    current_result_tuning_context as resolve_current_result_tuning_context,
    current_results_payload as build_current_results_payload,
    current_results_record as build_current_results_record,
    find_analysis_evidence,
    current_result_confirmation_label as build_current_result_confirmation_label,
    history_confirmation_translation_key,
    history_record_analysis_evidence,
    history_record_confirmed,
    result_origin_translation_key,
    result_comparison_record_label as build_result_comparison_record_label,
    result_comparison_summary as build_result_comparison_summary,
    result_compare_candidate_id,
    result_compare_candidate_label as build_result_compare_candidate_label,
    result_comparison_baseline as select_result_comparison_baseline,
    result_comparison_candidates as collect_result_comparison_candidates,
)
from .i18n import tr
from .widgets.results_table_panel import ResultsTablePanel
from .results_review_service import (
    build_result_review_panel_texts_from_window,
)
from .styles import C_TEXT_MUTED, C_TEXT_PRIMARY
from ..core.engine import logger


class MainWindowResultsMixin:
    @staticmethod
    def _main_window_module():
        from . import main_window as main_window_module

        return main_window_module

    @classmethod
    def _is_default_project_label_fn(cls):
        return cls._main_window_module()._is_default_project_label

    def _current_results_payload(self) -> dict:
        technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
        contexts = getattr(self, "_result_contexts", {})
        if technique in contexts and not self._result_context_is_current(technique):
            self._update_results_context_banner()
            return {}
        result = self._results.get(technique)
        self._update_results_context_banner()
        return build_current_results_payload(result)

    def _update_results_context_banner(self) -> None:
        banner = getattr(self, "_results_context_banner", None)
        if banner is None:
            return
        technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
        contexts = getattr(self, "_result_contexts", {})
        stale = technique in contexts and not self._result_context_is_current(technique)
        banner.setVisible(stale)
        if stale:
            owner = contexts.get(technique)
            banner.setText(
                tr(
                    "WORKSPACE_RESULT_STALE",
                    owner.technique if owner is not None else technique,
                    owner.run_id if owner is not None else "-",
                )
            )

    def _current_results_record(self) -> dict:
        technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
        payload = self._current_results_payload()
        return build_current_results_record(
            payload,
            technique=technique,
            submodule=str(getattr(self, "_current_submodule_id", "") or ""),
            project_label=self._project_label.text().strip(),
            inferred_sample_name=self._infer_sample_name(),
            current_file=str(self._current_filepath or ""),
            output_dir=str(self._output_dir or ""),
            result_origin=self._current_result_origin(),
            confirmed=bool(getattr(self, "_current_result_confirmed_flag", False)),
            run_id=str(getattr(self, "_last_persisted_run_id", "") or "current"),
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            is_default_project_label_fn=self._is_default_project_label_fn(),
        )

    def _current_result_history_context(self, current=None) -> dict:
        current = current if isinstance(current, dict) else self._current_results_record()
        return resolve_current_result_history_context(current)

    def _current_result_tuning_context(self, current=None) -> dict:
        current = current if isinstance(current, dict) else self._current_results_record()
        return resolve_current_result_tuning_context(
            current,
            live_tuning_context=getattr(self, "_last_ai_tuning_context", {}),
        )

    def _current_analysis_evidence(self):
        current = self._current_results_record()
        if not isinstance(current, dict) or not current:
            return {}
        return find_analysis_evidence(current)

    def _current_result_origin(self) -> str:
        technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
        current_result = self._results.get(technique)
        return resolve_current_result_origin(
            current_result,
            last_ai_tuned_run=bool(getattr(self, "_last_ai_tuned_run", False)),
        )

    def _current_result_origin_label(self) -> str:
        origin = self._current_result_origin()
        if not origin:
            return ""
        return self._result_origin_label(origin)

    def _result_origin_label(self, origin: str) -> str:
        key = str(origin or "").strip()
        translation_key = result_origin_translation_key(key)
        if translation_key:
            return tr(translation_key)
        return key or "Unknown"

    def _build_results_tab(self):

        w = QWidget()

        layout = QVBoxLayout(w)
        self._work_memory_panel = self._build_work_memory_panel()
        layout.addWidget(self._work_memory_panel)

        self._results_context_banner = QLabel()
        self._results_context_banner.setObjectName("workspace_result_context_banner")
        self._results_context_banner.setWordWrap(True)
        self._results_context_banner.setVisible(False)
        layout.addWidget(self._results_context_banner)

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

        for col, widget in enumerate(
            [
                self._joint_metric_batches,
                self._joint_metric_checks,
                self._joint_metric_warnings,
                self._joint_metric_errors,
            ]
        ):

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

        self._results_panel = ResultsTablePanel()
        self._results_panel.figure_link_requested.connect(self._on_results_figure_link)
        self._results_panel.review_action_requested.connect(self._on_results_profile_action)
        self._results_table = self._results_panel.primary_table
        self._current_results_table_model = None
        self._current_results_table_source = None
        self._results_copy_shortcut = QShortcut(QKeySequence.Copy, self._results_table)
        self._results_copy_shortcut.activated.connect(self._copy_results_table_to_clipboard)

        layout.addWidget(self._results_panel)

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
        self._btn_ai_tune = QPushButton(tr("AI_TUNING_BUTTON"))
        self._btn_ai_tune.setObjectName("secondary_btn")
        self._btn_ai_tune.clicked.connect(self.on_ai_tune_clicked)
        action_row.addWidget(self._btn_ai_tune)
        layout.addLayout(action_row)

        return w

    def _build_joint_metric_label(self):

        label = QLabel()

        label.setMinimumHeight(34)

        label.setAlignment(Qt.AlignCenter)

        label.setStyleSheet(
            "QLabel { padding: 6px 10px; border: 1px solid #3a4553; "
            "border-radius: 4px; font-weight: 600; }"
        )

        return label

    def _results_compare_candidates(self, *, create_db=True) -> list:

        current = self._current_results_record()
        if not current:
            return []
        db = self._ensure_sample_db() if create_db else getattr(self, "_sample_db", None)
        if db is None:
            return []
        try:
            return collect_result_comparison_candidates(
                current,
                db,
                inferred_sample_name=self._infer_sample_name(),
            )
        except Exception:
            logger.warning("Failed to collect result comparison candidates.", exc_info=True)
            return []


    def _results_compare_candidate_id(self, record) -> str:

        return result_compare_candidate_id(record)


    def _results_compare_candidate_label(self, record, index=None) -> str:

        label = self._result_comparison_record_label(record)
        return build_result_compare_candidate_label(
            label,
            index=index,
            empty_label=tr("RESULTS_COMPARE_EMPTY"),
        )


    def _results_compare_selected_candidate_id(self) -> str:

        return str(getattr(self, "_results_compare_selected_run_id", "") or "").strip()


    def _current_result_comparison_baseline(self, candidates=None):

        if candidates is None:
            candidates = self._results_compare_candidates()
        return select_result_comparison_baseline(
            candidates,
            selected_id=self._results_compare_selected_candidate_id(),
        )


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

        return build_result_comparison_record_label(
            record,
            context_label=self._history_record_context_text(record),
            origin_label=self._history_result_origin_label(record),
        )


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
                tr(history_confirmation_translation_key(confirmed))
            )
        if hasattr(self, "_results_confirm_btn"):
            self._results_confirm_btn.setText(tr("RESULTS_CONFIRM_CLEAR") if confirmed else tr("RESULTS_CONFIRM_MARK"))
            self._results_confirm_btn.setToolTip(
                tr("RESULTS_CONFIRM_TOOLTIP_CLEAR") if confirmed else tr("RESULTS_CONFIRM_TOOLTIP_SET")
            )
            self._results_confirm_btn.setEnabled(has_current)
        self._update_results_review_panel()


    def _results_confirm_state_text(self) -> str:
        return tr(history_confirmation_translation_key(self._is_current_result_confirmed()))


    def _history_confirmation_label(self, record) -> str:

        return tr(history_confirmation_translation_key(history_record_confirmed(record)))


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
        return build_current_result_confirmation_label(
            self._current_results_record(),
            inferred_sample_name=self._infer_sample_name(),
            technique_label=self._history_technique_text(str(self._current_technique or "")),
        )


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


    def _update_results_review_panel(self):
        current = self._current_results_record()
        if not hasattr(self, "_results_review_group"):
            return
        if not isinstance(current, dict) or not current:
            self._results_review_group.setVisible(False)
            return

        panel_texts = build_result_review_panel_texts_from_window(self)

        if hasattr(self, "_results_review_meta"):
            self._results_review_meta.setText(panel_texts.meta_text)
            self._results_review_meta.setVisible(bool(panel_texts.meta_text))
        if hasattr(self, "_results_review_benchmark"):
            self._results_review_benchmark.setText(panel_texts.benchmark_text)
            self._results_review_benchmark.setVisible(bool(panel_texts.benchmark_text))
        if hasattr(self, "_results_review_chain"):
            self._results_review_chain.setText(panel_texts.chain_text)
            self._results_review_chain.setVisible(bool(panel_texts.chain_text))
        if hasattr(self, "_results_review_trend"):
            self._results_review_trend.setText(panel_texts.trend_text)
            self._results_review_trend.setVisible(bool(panel_texts.trend_text))
        if hasattr(self, "_results_review_boundary"):
            self._results_review_boundary.setText(panel_texts.boundary_text)
            self._results_review_boundary.setVisible(bool(panel_texts.boundary_text))
        if hasattr(self, "_results_review_joint"):
            self._results_review_joint.setText(panel_texts.joint_text)
            self._results_review_joint.setVisible(panel_texts.joint_visible)
        if hasattr(self, "_results_review_risk"):
            self._results_review_risk.setText(panel_texts.risk_text)
            self._results_review_risk.setVisible(bool(panel_texts.risk_text))
        if hasattr(self, "_results_review_next"):
            self._results_review_next.setText(panel_texts.next_text)
            self._results_review_next.setVisible(bool(panel_texts.next_text))
        if hasattr(self, "_results_review_title"):
            self._results_review_title.setText(panel_texts.title_text)
        self._results_review_group.setVisible(True)


    def _result_comparison_summary(self) -> str:

        current = self._current_results_record()
        if not isinstance(current, dict) or not current:
            return ""
        current_label = self._result_comparison_record_label(current) or self._current_result_label_for_confirmation()
        baseline = self._current_result_comparison_baseline(self._results_compare_candidates(create_db=False))
        baseline_label = self._result_comparison_record_label(baseline) if baseline else ""
        current_metrics = self._history_result_metrics(current)
        baseline_metrics = self._history_result_metrics(baseline) if isinstance(baseline, dict) else {}
        technique = str(current.get("technique") or "").strip().lower()
        current_evidence = history_record_analysis_evidence(current)
        strain_active = False
        if technique == "saxs":
            strain_active = bool(self._saxs_strain_evidence_snapshot(current.get("parameters"), current_evidence).get("active"))
        return build_result_comparison_summary(
            current_label=current_label,
            baseline_label=baseline_label,
            current_metrics=current_metrics,
            baseline_metrics=baseline_metrics,
            technique=technique,
            strain_active=strain_active,
        )
