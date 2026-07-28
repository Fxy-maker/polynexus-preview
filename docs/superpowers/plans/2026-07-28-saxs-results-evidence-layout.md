# SAXS Results evidence layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep long SAXS Results evidence readable within the available Qt
viewport without changing the evidence contract.

**Architecture:** Retain the existing labels and `_set_results_summary()` data
flow. Configure the labels at Results-tab construction time with a zero minimum
width and an ignored horizontal size policy, allowing `wordWrap` to follow the
parent viewport instead of the longest evidence string.

**Tech Stack:** Python, PySide6, Pytest, Ruff, and `scripts/verify.py`.

---

### Task 1: Lock the geometry contract with RED

**Files:**
- Create: `tests/test_saxs_results_evidence_layout.py`

- [x] **Step 1: Write the failing test**

Instantiate `MainWindow`, set long risk/next text, and assert the summary
evidence labels use `QSizePolicy.Ignored`, retain word wrapping, preserve the
exact input strings, and keep the visible group's minimum size below a bounded
viewport threshold.

- [x] **Step 2: Run the focused test**

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_results_evidence_layout_red'
python -m pytest -q tests/test_saxs_results_evidence_layout.py
```

Expected: one failure on the current `Preferred` horizontal size policy or
the resulting oversized group, proving the test detects the existing defect.

### Task 2: Apply the minimal GUI layout fix

**Files:**
- Modify: `polynexus/gui/main_window_results_mixin.py` in
  `_build_results_tab()`.

- [x] **Step 1: Configure existing evidence labels**

After the summary and review labels are created, set each evidence label's
minimum width to zero and its policy to `QSizePolicy.Ignored,
QSizePolicy.Preferred`. Keep every existing `setWordWrap(True)` call and do
not alter any text assignment or evidence service.

- [x] **Step 2: Run the focused GREEN test**

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_results_evidence_layout_focus'
python -m pytest -q tests/test_saxs_results_evidence_layout.py tests/test_main_window_results_mixin.py tests/test_saxs_workbench_review_readability.py tests/test_saxs_results_table_service.py
```

Expected: all tests pass and the new geometry assertion is green.

### Task 3: Verify and checkpoint

- [x] **Step 1: Run the complete SAXS matrix**

Run the exact `test_saxs_*.py` matrix from the task card and record the actual
count, warnings, duration, and exit code. Do not substitute historical native
GUI or full/boundary evidence for this fresh result.

- [x] **Step 2: Run the structured verifier and diff check**

Run `python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-results-evidence-layout.md --changed --types` and `git diff --check`, recording quality/preprocessing gates and any limitation.

- [x] **Step 3: Update durable memory**

The concurrently edited `docs/agent/memory/active-work.md` is outside this
task's disjoint boundary, so do not modify or checkpoint it. Record the
deferral and exact evidence in this task card instead; leave both that file
and the pre-existing `current-state.md` modification alone.

- [x] **Step 4: Create the explicit allowlist checkpoint**

```powershell
python scripts/auto_commit.py --message "fix(gui): keep SAXS evidence readable" --files polynexus/gui/main_window_results_mixin.py tests/test_saxs_results_evidence_layout.py docs/agent/tasks/2026-07-28-saxs-results-evidence-layout.md docs/superpowers/specs/2026-07-28-saxs-results-evidence-layout-design.md docs/superpowers/plans/2026-07-28-saxs-results-evidence-layout.md
```

Do not stage or commit any pre-existing runtime directory, capture, harness,
`.superpowers/`, or `current-state.md` change.
