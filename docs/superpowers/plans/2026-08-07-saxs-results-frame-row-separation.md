# SAXS Results Frame Row Separation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make SAXS strain result-table row counts follow actual analyzed frames without mixing in detached orientation-track observations.

**Architecture:** Keep the engine payload and scientific evidence contracts unchanged. Correct only `build_saxs_results_presentation()` so its tabular view is built from frame rows plus the existing summary row, while nested tracking evidence remains available to diagnostic serialization.

**Tech Stack:** Python 3.14, PySide6 presentation DTOs, pytest

---

### Task 1: Add the frame-only row regression

**Files:**
- Modify: `tests/test_saxs_results_table_service.py`

- [x] **Step 1: Replace the old tracking-row projection expectation**

Create a five-frame `_batch_data` payload with repeated
`_orientation_tracking_rows` observations and nested
`orientation_tracking_evidence`. Assert that the primary section has five
rows, detail and diagnostic sections have six rows including the summary, no
detail row has an `orientation_track_id`, nested evidence is serialized in the
summary diagnostic row, and the source payload is unchanged.

- [x] **Step 2: Run the regression and verify RED**

Run:

```powershell
python -m pytest -p no:cacheprovider -q tests/test_saxs_results_table_service.py::test_strain_tables_keep_dynamic_frame_rows_separate_from_orientation_tracks
```

Expected: FAIL because `build_saxs_results_presentation()` currently appends
tracking observations to `view_rows`.

### Task 2: Separate tracking observations from frame rows

**Files:**
- Modify: `polynexus/gui/saxs_results_table_service.py`
- Test: `tests/test_saxs_results_table_service.py`

- [x] **Step 1: Implement the minimal presentation fix**

Remove the `_orientation_tracking_rows` extension from
`build_saxs_results_presentation()`. Leave `_batch_view_rows()`, the primary
frame projection, nested diagnostic serialization, and the input payload
unchanged.

- [x] **Step 2: Run the focused regression and verify GREEN**

Run:

```powershell
python -m pytest -p no:cacheprovider -q tests/test_saxs_results_table_service.py::test_strain_tables_keep_dynamic_frame_rows_separate_from_orientation_tracks
```

Expected: PASS.

- [x] **Step 3: Run the complete result-table module**

Run:

```powershell
python -m pytest -p no:cacheprovider -q tests/test_saxs_results_table_service.py
```

Expected: all tests pass.

### Task 3: Verify and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-08-07-saxs-results-frame-row-separation.md`
- Create: `docs/acceptance/2026-08-07-saxs-results-frame-row-separation.md`
- Modify: `docs/agent/memory/current-state.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] **Step 1: Run structured verification**

Run:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-07-saxs-results-frame-row-separation.md --changed --types
git diff --check
```

Expected: exit code 0 for both commands.

- [x] **Step 2: Record exact evidence**

Update the task checklist, acceptance note, and durable memory with the exact
commands, pass counts, known limitations, and presentation-only boundary.

- [ ] **Step 3: Create the explicit-file checkpoint**

Run `scripts/auto_commit.py` with only the source, regression, task, plan,
acceptance, and memory files changed by this task. Do not push or merge.

## Plan self-review

- Every design acceptance criterion is covered by Task 1 or Task 2.
- Paths, function names, commands, and expected outcomes are concrete.
- No placeholder, unrelated refactor, or scientific-semantics change remains.
