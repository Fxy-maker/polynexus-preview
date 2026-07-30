# SAXS Engine Confirmed Mask Rerun Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transport one confirmed static-image SAXS mask candidate through the normal engine and worker rerun path.

**Architecture:** Keep candidate validation and mask application in the existing SAXS preprocessing contract. Add a transient per-invocation candidate on `SAXSEngine`, and add an optional worker keyword that is forwarded only when present. No GUI or sequence-wide state is added.

**Tech Stack:** Python, NumPy, PySide6 `QThread`, pytest, existing SAXS quality contracts.

---

### Task 1: Define the engine and worker boundary tests

**Files:**
- Create: `tests/test_saxs_engine_confirmed_mask_rerun.py`

- [x] **Step 1: Write RED tests**

Cover engine forwarding into `preprocess()`, cleanup after a failed run,
plot-only non-application, and worker forwarding of the optional candidate.

- [x] **Step 2: Run the focused RED command**

```powershell
python -m pytest -q tests/test_saxs_engine_confirmed_mask_rerun.py -o addopts= --basetemp=D:\PolyNexus-test-runs\pytest\saxs-engine-mask-rerun-red
```

Expected failure: `SAXSEngine.run_pipeline` and `AnalysisWorker` do not yet
accept/forward `mask_edit_candidate`.

### Task 2: Thread the candidate through the normal static pipeline

**Files:**
- Modify: `polynexus/core/saxs.py`
- Modify: `polynexus/gui/main_window_workers.py`
- Test: `tests/test_saxs_engine_confirmed_mask_rerun.py`

- [x] **Step 1: Add a transient engine candidate slot**

Store the optional mapping only around `super().run_pipeline()` and restore it
in `finally`; `preprocess()` passes it to `preprocess_pipeline()` only for the
2D image path.

- [x] **Step 2: Add optional worker forwarding**

Add `mask_edit_candidate=None` to `AnalysisWorker`. Build the existing
`run_pipeline` keyword arguments and add the candidate keyword only when it is
not `None`, so non-SAXS engines keep their current call contract.

- [x] **Step 3: Run focused GREEN**

```powershell
python -m pytest -q tests/test_saxs_engine_confirmed_mask_rerun.py -o addopts= --basetemp=D:\PolyNexus-test-runs\pytest\saxs-engine-mask-rerun-green
```

Expected: all boundary tests pass and the transient candidate is cleared.

Observed: `6 passed` after adding explicit 1D and sequence no-op coverage.

### Task 3: Verify and checkpoint

**Files:**
- Modify: `docs/acceptance/2026-07-30-saxs-engine-confirmed-mask-rerun.md`
- Modify: `docs/agent/tasks/2026-07-30-saxs-engine-confirmed-mask-rerun.md`
- Modify: `docs/superpowers/plans/2026-07-30-saxs-engine-confirmed-mask-rerun.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] **Step 1: Run task-scoped verification**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-engine-confirmed-mask-rerun.md --changed --types
```

Observed: exit code `0`; quality `292 passed`, preprocessing `106 passed`,
Ruff, compile, memory/task, type baseline, and whitespace checks passed.

- [x] **Step 2: Run the exact SAXS matrix, storage report/dry-run, and diff check**

Require a complete pytest summary and exit code `0`; do not use
`test_storage.py --apply`.

Observed: all `tests/test_saxs*.py` returned `642 passed, 6 warnings` in
`559.53s`; storage report had `54` artifacts and `eligible_bytes=0`; cleanup
dry-run removed nothing; `git diff --check` passed. A prior 120-second tool
timeout had no pytest summary and is not counted as evidence.

- [x] **Step 3: Create one explicit allowlist checkpoint**

```powershell
python scripts/auto_commit.py --message "feat(saxs): thread confirmed mask reruns" --files polynexus/core/saxs.py polynexus/gui/main_window_workers.py tests/test_saxs_engine_confirmed_mask_rerun.py docs/superpowers/specs/2026-07-30-saxs-engine-confirmed-mask-rerun-design.md docs/superpowers/plans/2026-07-30-saxs-engine-confirmed-mask-rerun.md docs/agent/tasks/2026-07-30-saxs-engine-confirmed-mask-rerun.md docs/acceptance/2026-07-30-saxs-engine-confirmed-mask-rerun.md docs/agent/memory/active-work.md
```

The allowlist checkpoint is the commit created by this command after the
verification above. The hash remains available in Git history and is not
duplicated in this task's mutable evidence files.
