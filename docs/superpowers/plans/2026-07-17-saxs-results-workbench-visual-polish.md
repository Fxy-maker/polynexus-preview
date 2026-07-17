# SAXS Results Workbench Visual Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (\`- [ ]\`) syntax for tracking.

**Goal:** Restyle the SAXS temperature result area into a lighter, clearer workbench with one-row hero metrics, localized review hinting, compact status chips, and better table width usage.

**Architecture:** Keep HeroMetric, ResultTableSection, table sorting, copying, export, and scientific status production unchanged. Refactor only the Qt presentation layer in results_table_panel.py to use live ThemeEngine tokens, add an optional review-hint widget, and feed it from the existing result-summary labels for SAXS temperature runs.

**Tech Stack:** Python 3.11+, PySide6, pytest, existing ThemeEngine tokens, existing MainWindowOutputMixin summary flow.

---

## File map

- Modify polynexus/gui/widgets/results_table_panel.py: metric-card layout, theme-aware styles, review hint widget, status chips, table width policy.
- Modify polynexus/gui/main_window_output_mixin.py: pass existing SAXS temperature summary/risk/next text to the panel’s optional review hint; no new status calculation.
- Modify polynexus/gui/i18n.py: add only the review-hint title/action keys required by the new panel entry point.
- Modify tests/test_results_table_panel.py: red-green tests for layout, theme refresh, status chips, review hint, and table sizing.
- Modify tests/test_main_window_output_mixin.py: verify summary refresh feeds the hint and non-SAXS/non-temperature paths clear it.

Do not modify the existing chart-editor changes in the working tree, any polynexus/core SAXS algorithm, result models, export services, or history services.

### Task 1: Define the failing presentation tests

**Files:**
- Modify: tests/test_results_table_panel.py
- Modify: tests/test_main_window_output_mixin.py

- [ ] **Step 1: Add a four-hero one-row layout test.**

Append this test to tests/test_results_table_panel.py:

    def test_four_hero_metrics_share_one_row_and_keep_cards_light(app: QApplication) -> None:
        ResultsTablePanel, _ = _panel_types()
        panel = ResultsTablePanel()
        empty = ResultTableSection.empty()
        heroes = tuple(
            HeroMetric(str(index), f"Metric {index}", index, str(index))
            for index in range(4)
        )

        panel.set_content(heroes=heroes, primary=empty, detail=empty, diagnostics=empty)

        assert panel._metrics_layout.itemAtPosition(0, 3).widget() is not None
        assert panel._metrics_layout.itemAtPosition(1, 0) is None
        assert len(panel.hero_labels) == 4
        assert "background:" in panel.hero_labels[0].styleSheet()
        assert "#222538" not in panel.hero_labels[0].styleSheet()

- [ ] **Step 2: Add status-chip and table-width assertions.**

    def test_status_cells_use_compact_badges_and_tables_stretch_last_column(
        app: QApplication,
    ) -> None:
        ResultsTablePanel, _ = _panel_types()
        panel = ResultsTablePanel()
        primary = _section(
            (
                TableCell(1.0, "1.0", status="review"),
                TableCell("blocked", "blocked", status="blocked"),
            ),
            columns=(
                TableColumn("score", "Score", alignment="right"),
                TableColumn("status", "Status"),
            ),
        )

        panel.set_content(
            heroes=(),
            primary=primary,
            detail=ResultTableSection.empty(),
            diagnostics=ResultTableSection.empty(),
        )

        status_label = panel.primary_table.cellWidget(0, 0).findChild(
            QLabel, "result_cell_status_review"
        )
        assert "border-radius" in status_label.styleSheet()
        assert "background" in status_label.styleSheet()
        assert panel.primary_table.horizontalHeader().stretchLastSection()

- [ ] **Step 3: Add review-hint visibility and action tests.**

    def test_review_hint_hides_when_empty_and_exposes_primary_action(app: QApplication) -> None:
        ResultsTablePanel, _ = _panel_types()
        panel = ResultsTablePanel()

        panel.set_review_hint(
            title="当前判断",
            detail="1 帧需复核",
            next_text="先查看温度总览",
            status="review",
            action_text="查看温度总览",
            action=lambda: None,
        )

        assert not panel.review_hint_widget.isHidden()
        assert panel.review_hint_title.text() == "当前判断"
        assert panel.review_hint_action.text() == "查看温度总览"

        panel.clear_review_hint()

        assert panel.review_hint_widget.isHidden()

- [ ] **Step 4: Add the output-mixin wiring contract test.**

Use a fake panel with set_review_hint and clear_review_hint recorders and a fake window with _current_technique="saxs", _current_submodule_id="saxs.temperature", and summary/risk/next inputs. Assert SAXS temperature calls set_review_hint with the existing text and other techniques call clear_review_hint.

- [ ] **Step 5: Run the new tests to verify red state.**

Run:

    python -m pytest tests/test_results_table_panel.py -k "four_hero or status_cells or review_hint" tests/test_main_window_output_mixin.py -q

Expected: collection or execution fails because set_review_hint, clear_review_hint, and the new layout/style behavior do not exist yet.

### Task 2: Implement the theme-aware metric area and status chips

**Files:**
- Modify: polynexus/gui/widgets/results_table_panel.py
- Test: tests/test_results_table_panel.py

- [ ] **Step 1: Replace static result-card colors with live theme tokens.**

Import ThemeEngine and connect the singleton signal in ResultsTablePanel.__init__:

    self._theme_engine = ThemeEngine.instance()
    self._theme_engine.theme_changed.connect(self._refresh_visual_theme)

Add:

    def _refresh_visual_theme(self, _theme_name: str = "") -> None:
        self._apply_metric_styles()
        self._apply_status_styles()
        self._apply_review_hint_style()

Use self._theme_engine.tokens.bg_card, bg_surface, border_light, text_primary, text_muted, success, warning, and danger. Do not hard-code C_BG_CARD for the new metric cards or chips.

- [ ] **Step 2: Make four or fewer hero metrics occupy four columns.**

Change _set_heroes so the column count is 4 for 1–4 metrics and 3 for 5–6 metrics. Keep the existing six-metric cap and hero_labels compatibility. Add consistent minimum height, padding, 10px radius, and left-aligned label/value hierarchy while keeping the metric text accessible.

The layout rule is:

    column_count = 4 if len(heroes) <= 4 else 3
    for index, label in enumerate(self.hero_labels):
        self._metrics_layout.addWidget(label, index // column_count, index % column_count)

- [ ] **Step 3: Render status cells as compact badges without changing raw values.**

Keep TypedTableWidgetItem raw values, status roles, tooltips, and sorting unchanged. In _status_cell_widget, style only the status label with a theme-aware chip:

    status_label.setStyleSheet(
        f"background: {tokens.bg_surface}; "
        f"color: {color}; "
        f"border: 1px solid {tokens.border_light}; "
        "border-radius: 9px; padding: 1px 6px; font-weight: 600;"
    )

The numeric/display label must keep primary text color and existing alignment. Unknown/neutral status must not get a warning or danger color.

- [ ] **Step 4: Make the table use available width.**

After resizeColumnsToContents(), set a minimum readable width for each column, then call header.setStretchLastSection(True). Preserve horizontal scrolling for wide tables and do not enable editing.

- [ ] **Step 5: Run presentation tests and verify green.**

Run:

    python -m pytest tests/test_results_table_panel.py -q

Expected: the existing panel tests and the new layout/chip tests pass.

### Task 3: Add the optional review hint and SAXS temperature wiring

**Files:**
- Modify: polynexus/gui/widgets/results_table_panel.py
- Modify: polynexus/gui/main_window_output_mixin.py
- Modify: polynexus/gui/i18n.py
- Modify: tests/test_main_window_output_mixin.py
- Test: tests/test_results_table_panel.py

- [ ] **Step 1: Build a hidden review-hint widget above the result tabs.**

In ResultsTablePanel.__init__, create review_hint_widget before self.tabs with these child attributes:

    review_hint_status
    review_hint_title
    review_hint_detail
    review_hint_next
    review_hint_action

Keep it hidden initially. The layout must be a horizontal row with the status dot/label and text on the left and one optional primary button on the right.

- [ ] **Step 2: Add the public hint API.**

Implement:

    def set_review_hint(
        self,
        *,
        title: str,
        detail: str = "",
        next_text: str = "",
        status: str = "neutral",
        action_text: str = "",
        action=None,
    ) -> None:
        self.review_hint_title.setText(title)
        self.review_hint_detail.setText(detail)
        self.review_hint_next.setText(next_text)
        self.review_hint_action.setText(action_text)
        self._set_review_hint_status(status)
        self._connect_review_hint_action(action)
        self.review_hint_widget.setVisible(bool(title or detail or next_text))

    def clear_review_hint(self) -> None:
        self.review_hint_widget.hide()
        self.review_hint_action.hide()
        self._disconnect_review_hint_action()

Before reconnecting an action, use a stored QMetaObject.Connection or an equivalent safe disconnect strategy so repeated result refreshes do not accumulate click handlers. Hide the whole widget when all text is empty.

- [ ] **Step 3: Add bilingual hint title/action keys.**

Add these keys to both language dictionaries in polynexus/gui/i18n.py:

    "SAXS_RESULTS_REVIEW_HINT_TITLE": "当前判断",
    "SAXS_RESULTS_REVIEW_HINT_ACTION": "查看温度总览",

Use natural English values in the English dictionary and do not add science/status logic to i18n.

- [ ] **Step 4: Feed existing summary text into the hint.**

At the end of MainWindowOutputMixin._set_results_summary, after the existing result-summary updates, add a helper that:

    panel = getattr(self, "_results_panel", None)
    if panel is None:
        return
    if (
        str(getattr(self, "_current_technique", "")).strip().lower() == "saxs"
        and str(getattr(self, "_current_submodule_id", "")).strip().lower()
        in {"temperature", "saxs.temperature"}
    ):
        panel.set_review_hint(
            title=tr("SAXS_RESULTS_REVIEW_HINT_TITLE"),
            detail=str(risk_text or summary),
            next_text=str(next_step or ""),
            status="review" if risk_text else "neutral",
            action_text=tr("SAXS_RESULTS_REVIEW_HINT_ACTION"),
            action=lambda: self._jump_to_tab(3),
        )
    else:
        panel.clear_review_hint()

Use the existing parameters passed to _set_results_summary; do not calculate a new risk state. Keep the action a tab jump only.

- [ ] **Step 5: Run wiring and panel tests.**

Run:

    python -m pytest tests/test_results_table_panel.py tests/test_main_window_output_mixin.py -q

Expected: all panel and output-mixin tests pass, including repeated refresh without duplicate callbacks.

### Task 4: Verify the scoped visual polish and regression surface

**Files:** No additional files expected.

- [ ] **Step 1: Run focused result-panel and SAXS presentation tests.**

    python -m pytest tests/test_results_table_panel.py tests/test_results_table_service.py tests/test_saxs_results_table_service.py tests/test_main_window_output_mixin.py tests/test_main_window_results_mixin.py -q

Expected: exit code 0 with zero failures.

- [ ] **Step 2: Run compile and lint checks on changed files.**

    python -m compileall -q polynexus/gui/widgets/results_table_panel.py polynexus/gui/main_window_output_mixin.py polynexus/gui/i18n.py
    ruff check polynexus/gui/widgets/results_table_panel.py polynexus/gui/main_window_output_mixin.py polynexus/gui/i18n.py tests/test_results_table_panel.py tests/test_main_window_output_mixin.py
    git diff --check

Expected: all commands exit 0.

- [ ] **Step 3: Run the full suite and record unrelated failures exactly.**

    python -m pytest -q

Expected: exit code 0. If unrelated existing failures occur, record exact node IDs and compare changed-file scope before reporting them; do not change chart-editor files or unrelated services to make this visual task green.

- [ ] **Step 4: Manually inspect light and dark themes.**

Launch the GUI, open a SAXS temperature result with four hero metrics, switch light/dark themes, and confirm: four metric cards remain on one row, status chips remain readable, the hint appears only when summary text exists, the table uses available width, and sorting/copy/export still work.

- [ ] **Step 5: Review final status and commit only scoped files.**

    git status --short
    git diff --stat
    git add polynexus/gui/widgets/results_table_panel.py polynexus/gui/main_window_output_mixin.py polynexus/gui/i18n.py tests/test_results_table_panel.py tests/test_main_window_output_mixin.py
    git commit -m "feat: polish SAXS results workbench"

Expected: pre-existing chart-editor changes remain unstaged and untouched; only the listed result-panel files enter the commit.
