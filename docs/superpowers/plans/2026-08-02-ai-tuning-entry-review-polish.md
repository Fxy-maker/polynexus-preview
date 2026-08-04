# AI Tuning Entry And Review Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the AI parameter-adjustment entry immediately discoverable and present completed candidate trials in a clear, professional review dialog without changing tuning behavior.

**Architecture:** Keep `MainWindowAITuningMixin` as the owner of execution and application behavior. Add a presentational entry panel in `MainWindowResultsMixin`, localize all new labels in `i18n.py`, and reorganize `SideTuningReportDialog` around existing report fields rather than introducing a new DTO or data path.

**Tech Stack:** Python 3.14, PySide6, existing PolyNexus i18n helpers, pytest-qt style GUI tests.

---

### Task 1: Lock the Results-entry contract with tests

**Files:**
- Modify: `tests/test_main_window_ai_tuning_mixin.py`
- Modify: `tests/test_main_window_persistence.py`
- Modify: `polynexus/gui/main_window_results_mixin.py`

- [ ] **Step 1: Write the failing Results-entry regression**

Add a GUI test that constructs `MainWindow`, reads the new entry button and supporting label, and asserts that the primary text is `tr("AI_TUNING_ENTRY_BUTTON")`, the helper text is `tr("AI_TUNING_ENTRY_DESCRIPTION")`, and the button calls `on_ai_tune_clicked`.

```python
def test_results_page_exposes_ai_parameter_adjustment_entry(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    assert window._ai_tuning_entry_button.text() == tr("AI_TUNING_ENTRY_BUTTON")
    assert window._ai_tuning_entry_description.text() == tr("AI_TUNING_ENTRY_DESCRIPTION")
    assert window._ai_tuning_entry_button.isVisible()
```

- [ ] **Step 2: Run the focused test to verify the old UI fails**

Run: `python -m pytest tests/test_main_window_ai_tuning_mixin.py -k results_page_exposes_ai_parameter_adjustment_entry -q`

Expected: FAIL because the Results entry panel and its attributes do not yet exist.

- [ ] **Step 3: Add the Result-page action panel**

Create a compact, unframed Results-page action band before the result summary. It must contain the localized title/description, a primary `AI 调整参数` button, a short boundary label stating that candidates are tried within allowed ranges, and the existing click handler. Preserve `_btn_ai_tune` as a bottom-of-page compatibility control, changing it to the same localized label.

```python
self._ai_tuning_entry_button = QPushButton(tr("AI_TUNING_ENTRY_BUTTON"))
self._ai_tuning_entry_button.clicked.connect(self.on_ai_tune_clicked)
self._ai_tuning_entry_description = QLabel(tr("AI_TUNING_ENTRY_DESCRIPTION"))
self._ai_tuning_entry_description.setWordWrap(True)
```

- [ ] **Step 4: Run the focused test to verify the entry contract passes**

Run: `python -m pytest tests/test_main_window_ai_tuning_mixin.py -k results_page_exposes_ai_parameter_adjustment_entry -q`

Expected: PASS.

### Task 2: Rename the start flow in user language

**Files:**
- Modify: `polynexus/gui/i18n.py`
- Modify: `polynexus/gui/main_window.py`
- Modify: `polynexus/gui/main_window_ai_tuning_mixin.py`
- Test: `tests/test_main_window_ai_tuning_mixin.py`

- [ ] **Step 1: Write failing localization/goal-dialog assertions**

Add tests for the Chinese and English translations that confirm the start flow says `AI 调整参数` / `AI Parameter Adjustment`, describes candidate trials within allowed ranges, and labels the dialog confirmation as `开始分析` / `Start analysis`.

```python
def test_ai_parameter_adjustment_start_copy_is_explicit():
    set_language("zh")
    assert tr("AI_TUNING_ENTRY_BUTTON") == "AI 调整参数"
    assert tr("AI_TUNING_GOAL_DIALOG_TITLE") == "AI 调整参数"
    assert tr("AI_TUNING_GOAL_START") == "开始分析"
```

- [ ] **Step 2: Run the localization test to verify it fails**

Run: `python -m pytest tests/test_main_window_ai_tuning_mixin.py -k ai_parameter_adjustment_start_copy_is_explicit -q`

Expected: FAIL because the localization keys are absent or retain the old terminology.

- [ ] **Step 3: Localize the entry and goal dialog**

Add the new entry strings in both language maps. Change the current goal-dialog title, description, goal labels, and OK button to state the user-facing action directly, while retaining the existing goal identifiers (`symptom`, `risk`, `joint`, `stability`) and worker invocation unchanged.

```python
buttons.button(QDialogButtonBox.Ok).setText(tr("AI_TUNING_GOAL_START"))
```

- [ ] **Step 4: Run the localization and launch-flow tests**

Run: `python -m pytest tests/test_main_window_ai_tuning_mixin.py -k "ai_parameter_adjustment_start_copy_is_explicit or ai_tune_clicked" -q`

Expected: PASS, including the existing worker-context tests.

### Task 3: Rebuild the candidate-review dialog around existing report data

**Files:**
- Modify: `polynexus/gui/main_window.py`
- Modify: `polynexus/gui/i18n.py`
- Test: `tests/test_main_window_persistence.py`

- [ ] **Step 1: Write failing dialog-content tests**

Add a focused test that supplies a report containing `history`, `best_config`, `benchmark_summary`, and a remaining-risk value. Verify that the dialog contains a recommendation summary, evidence summary, risk label, `保留当前结果`, and `应用推荐配置并重跑` controls.

```python
dialog = SideTuningReportDialog(report)
assert dialog._recommendation_title.text() == tr("AI_TUNING_RECOMMENDATION_TITLE")
assert dialog._risk_label.isVisible()
assert dialog._apply_button.text() == tr("AI_TUNING_APPLY_AND_RERUN")
```

- [ ] **Step 2: Run the dialog test to verify it fails**

Run: `python -m pytest tests/test_main_window_persistence.py -k ai_tuning_review_dialog -q`

Expected: FAIL because the current dialog does not expose the new structured controls.

- [ ] **Step 3: Implement a four-section review dialog**

Use the report already passed to `SideTuningReportDialog`. Add a completion status block, a recommended-candidate block that renders changed values, an evidence/benchmark block, and a wrapped amber risk block. Retain `best_config()` and `QDialog.Accepted` behavior, but rename its actions so accepting explicitly means apply-and-rerun.

```python
self._apply_button = QPushButton(tr("AI_TUNING_APPLY_AND_RERUN"))
self._keep_button = QPushButton(tr("AI_TUNING_KEEP_CURRENT"))
self._keep_button.clicked.connect(self.reject)
self._apply_button.clicked.connect(self.accept)
```

- [ ] **Step 4: Run focused dialog and rerun behavior tests**

Run: `python -m pytest tests/test_main_window_persistence.py -k "ai_tuning_review_dialog or ai_tune_finished_returns_to_config_before_rerun" -q`

Expected: PASS; the existing assertion that the accepted dialog returns to Config and starts a rerun remains green.

### Task 4: Verify the user-facing GUI slice and checkpoint

**Files:**
- Modify: `docs/agent/memory/current-state.md`
- Modify: `docs/acceptance/2026-08-02-ai-tuning-entry-review-polish.md`

- [ ] **Step 1: Run the complete focused GUI slice**

Run: `python -m pytest tests/test_main_window_ai_tuning_mixin.py tests/test_main_window_persistence.py tests/test_saxs_ai_confirmation_gui_route.py -q`

Expected: PASS with no failures.

- [ ] **Step 2: Run the required structured verifier**

Run: `python scripts/verify.py --task docs/agent/tasks/2026-08-02-ai-tuning-entry-review-polish.md --changed --types`

Expected: exit code `0`.

- [ ] **Step 3: Record durable evidence**

Write the exact test/verifier results, changed-file allowlist, and remaining limitation: this is a discoverability and presentation change, not a scientific-data repair or autonomous result-confirmation feature.

- [ ] **Step 4: Create the local checkpoint**

Run:

```powershell
python scripts/auto_commit.py `
  --message "feat(gui): clarify AI parameter adjustment workflow" `
  --files polynexus/gui/main_window.py polynexus/gui/main_window_results_mixin.py polynexus/gui/main_window_ai_tuning_mixin.py polynexus/gui/i18n.py tests/test_main_window_ai_tuning_mixin.py tests/test_main_window_persistence.py docs/agent/tasks/2026-08-02-ai-tuning-entry-review-polish.md docs/acceptance/2026-08-02-ai-tuning-entry-review-polish.md docs/agent/memory/current-state.md docs/superpowers/specs/2026-08-02-ai-tuning-entry-and-review-polish-design.md docs/superpowers/plans/2026-08-02-ai-tuning-entry-review-polish.md
```

Expected: a local commit only; no push, merge, deploy, or deletion.

