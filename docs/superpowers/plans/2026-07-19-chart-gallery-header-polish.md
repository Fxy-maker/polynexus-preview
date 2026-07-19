# Chart Gallery Header Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the chart page a clear gallery header and visually grouped toolbar without changing chart data, filtering semantics, or signals.

**Architecture:** Keep the page shell in `MainWindow._build_plots_tab()` and keep gallery-specific controls inside `ChartGallery`. Add a small `ChartGallery.summary_text()` presentation helper so the page header can display the current visible figure count without reaching into technique-specific state. The existing `load_entries()` and filter reload path remain the source of truth.

**Tech Stack:** PySide6 widgets, existing i18n strings, Qt offscreen pytest.

---

### Task 1: Define the header contract with tests

**Files:**
- Modify: `tests/test_chart_viewer.py`
- Modify: `tests/test_main_window_figure_mixin.py` or the closest existing MainWindow GUI test module after locating the builder test.

- [ ] **Step 1: Write the failing gallery summary test**

Add a test that loads two `FigureGalleryEntry` values into `ChartGallery`, calls `summary_text()`, and asserts the returned text contains `2` and the localized figure label. Add a filtered state assertion after selecting the per-frame category so the summary reflects visible entries.

- [ ] **Step 2: Run the focused test and confirm the expected failure**

Run `pytest tests/test_chart_viewer.py -q -k summary_text`. Expected result: failure because `ChartGallery.summary_text` does not exist.

- [ ] **Step 3: Add the minimal summary implementation**

Implement `ChartGallery.summary_text()` in `polynexus/gui/widgets/chart_viewer.py` using the already computed `self._entries`; return a localized, human-readable count and use zero when no entries are visible. Do not inspect files or rebuild gallery entries in this helper.

- [ ] **Step 4: Run the focused test and confirm it passes**

Run `pytest tests/test_chart_viewer.py -q -k summary_text`. Expected result: PASS.

### Task 2: Add the page header and group the top-level action

**Files:**
- Modify: `polynexus/gui/main_window.py` in `_build_plots_tab()`.
- Modify: `tests/test_main_window_figure_mixin.py` or the existing MainWindow construction test that can inspect `_btn_legacy_recovery` and `_chart_gallery`.

- [ ] **Step 1: Write the failing page-header test**

Assert the plots tab creates a non-empty gallery title label, a gallery summary label, and keeps the legacy recovery button connected and visible. The test must not assert exact pixel geometry.

- [ ] **Step 2: Run the test and confirm it fails**

Run the single test with `pytest <test-file>::<test-name> -q`. Expected result: failure because the new header widgets are not present.

- [ ] **Step 3: Implement the smallest header**

Create a header row before the existing recovery toolbar containing a title label, a muted summary label, and a stretch. Move the recovery button into the existing toolbar and give the toolbar a named container widget so the existing button remains in the same signal path. Connect gallery loading/reloading to refresh the summary label through a small MainWindow helper that reads `self._chart_gallery.summary_text()`.

- [ ] **Step 4: Run the focused MainWindow test**

Run the single test again and expect PASS, then run `pytest tests/test_main_window_figure_mixin.py -q` to catch existing page wiring regressions.

### Task 3: Apply the light toolbar container treatment

**Files:**
- Modify: `polynexus/gui/widgets/chart_viewer.py`.
- Modify: `tests/test_chart_viewer.py`.

- [ ] **Step 1: Add a structural style assertion**

Assert that `ChartGallery` exposes an object name for the toolbar container and that the scroll area remains borderless. This locks the styling boundary without snapshot testing.

- [ ] **Step 2: Run the test and confirm it fails**

Run `pytest tests/test_chart_viewer.py -q -k toolbar_container`. Expected result: failure because the toolbar container is not yet a widget with the expected object name.

- [ ] **Step 3: Implement the toolbar container**

Wrap the current filter/action layout in a `QWidget` named `gallery_toolbar`, apply theme-token background/border/radius/padding through `_apply_gallery_chrome()`, and refresh that style on theme changes. Keep the existing combo boxes and buttons as children of the same toolbar layout.

- [ ] **Step 4: Run the full focused suite**

Run `pytest tests/test_chart_viewer.py tests/test_main_window_figure_mixin.py -q` and expect all tests to pass.

### Task 4: Update task evidence and verify

**Files:**
- Modify: `docs/agent/tasks/2026-07-19-chart-gallery-visual-polish.md`.
- Modify: `docs/agent/memory/active-work.md`.

- [ ] **Step 1: Record the second-wave acceptance evidence**

Add the header, summary, and toolbar-container acceptance notes plus exact test commands; explicitly retain the missing `scripts/verify.py` limitation if it remains absent.

- [ ] **Step 2: Run final verification**

Run:

```bash
pytest tests/test_chart_viewer.py tests/test_main_window_figure_mixin.py -q
python -m compileall -q polynexus/gui/main_window.py polynexus/gui/widgets/chart_viewer.py
python scripts/verify.py --changed --types
git diff --check
```

Report the actual result of each command and do not claim the unavailable verifier passed.

- [ ] **Step 3: Create the local checkpoint**

Run `python scripts/auto_commit.py --message "feat(gui): add chart gallery header" --files polynexus/gui/main_window.py polynexus/gui/widgets/chart_viewer.py tests/test_chart_viewer.py tests/test_main_window_figure_mixin.py docs/agent/tasks/2026-07-19-chart-gallery-visual-polish.md docs/agent/memory/active-work.md` using only files that actually changed.

## Self-review

- The plan changes only the page shell and gallery presentation boundary; chart data and public signals are untouched.
- The summary uses filtered `self._entries`, so the count follows the existing filter path.
- Every behavior change has a named Qt regression test and a red-green sequence.
- The missing repository verifier is recorded as a limitation rather than treated as a pass.
