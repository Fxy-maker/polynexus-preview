# Results Review Hint Long-Token Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent the Results Workbench review-hint row from expanding the scrollable workspace to thousands of pixels when its detail contains delimiter-free diagnostic tokens.

**Architecture:** Reuse one display-only wrapped evidence QLabel for MainWindow Summary/Review labels and ResultsTablePanel review-hint detail/next labels. The shared class keeps the original `.text()` contract and adds only invisible display break opportunities. No analysis, evidence, or review semantics change.

**Tech Stack:** Python, PySide6, pytest, real SAXS temperature restore flow, repository verification scripts.

---

### Task 1: Reproduce the review-hint width expansion

**Files:**
- Modify: `tests/test_results_table_panel.py`

- [x] **Step 1: Add the failing layout regression**

Create a `ResultsTablePanel`, set a long delimiter-free detail string, and
assert that the detail's source text is preserved while its minimum width fits
within a 640-pixel workbench column:

```python
def test_review_hint_long_detail_token_wraps_without_expanding_minimum_width():
    ResultsTablePanel, _ = _panel_types()
    panel = ResultsTablePanel()
    detail = "Risk note | reasons=" + ("automated_validation_failed," * 40)
    panel.set_review_hint(title="summary", detail=detail)
    panel.review_hint_detail.setFixedWidth(640)
    QApplication.processEvents()

    assert panel.review_hint_detail.text() == detail
    assert panel.review_hint_detail.minimumSizeHint().width() <= 640
```

- [x] **Step 2: Run the test and confirm RED**

```powershell
$env:QT_QPA_PLATFORM='offscreen'
python -m pytest -q tests/test_results_table_panel.py::test_review_hint_long_detail_token_wraps_without_expanding_minimum_width -vv
```

Expected result before the fix: failure because the ordinary QLabel minimum
width is several thousand pixels.

### Task 2: Share the wrapped evidence label

**Files:**
- Create: `polynexus/gui/widgets/wrapped_evidence_label.py`
- Modify: `polynexus/gui/widgets/results_table_panel.py`
- Modify: `polynexus/gui/main_window_results_mixin.py`

- [x] **Step 1: Move the display-only QLabel behavior into the shared widget**

Create `_WrappedEvidenceLabel(QLabel)` with the existing source-text storage,
zero-width display break opportunities, and exact `.text()` override. Import
it from both GUI consumers, remove the duplicate MainWindow-local class, and
use it for `review_hint_detail` and `review_hint_next`.

### Task 3: Verify the real boundary

**Files:**
- Create: `docs/agent/tasks/2026-07-30-results-review-hint-long-token-layout.md`
- Create: `docs/acceptance/2026-07-30-results-review-hint-long-token-layout.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] **Step 1: Run focused widget and GUI tests**

```powershell
$env:QT_QPA_PLATFORM='offscreen'
python -m pytest -q tests/test_results_table_panel.py tests/test_saxs_results_evidence_layout.py tests/test_main_window_results_mixin.py -vv
```

- [x] **Step 2: Run the real SAXS temperature restore geometry probe**

Use the existing temperature fixture and external D: output to confirm the
Results Workbench page and review-hint labels no longer report multi-thousand
pixel minimum widths. Record actual values; do not alter the fixture.

- [x] **Step 3: Run the structured verifier and create one allowlisted checkpoint**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-30-results-review-hint-long-token-layout.md --changed --types
git diff --check
python scripts/auto_commit.py --message "fix(gui): constrain review hint evidence" --files polynexus/gui/widgets/wrapped_evidence_label.py polynexus/gui/widgets/results_table_panel.py polynexus/gui/main_window_results_mixin.py tests/test_results_table_panel.py docs/superpowers/plans/2026-07-30-results-review-hint-long-token-layout.md docs/agent/tasks/2026-07-30-results-review-hint-long-token-layout.md docs/acceptance/2026-07-30-results-review-hint-long-token-layout.md docs/agent/memory/active-work.md
```

## Scope audit

- No scientific algorithms, thresholds, evidence severity, publication roles,
  raw datasets, test-storage cleanup, or external integrations change.
- Preserve the pre-existing uncommitted `docs/agent/memory/current-state.md`
  change and all scratch/capture directories outside the allowlist.
