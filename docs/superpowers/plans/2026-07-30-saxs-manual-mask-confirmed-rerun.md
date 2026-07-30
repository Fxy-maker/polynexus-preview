# SAXS Manual Mask Confirmed Rerun Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a strict, candidate-only-then-confirmed SAXS detector mask boundary to the existing preprocessing pipeline.

**Architecture:** Keep mask editing as a pure core contract that serializes explicit pixel changes against a base digest. Preprocessing validates and applies only confirmed candidates to a copied mask, then sends that mask through the existing full, sector, and azimuthal integration functions and detector quality report.

**Tech Stack:** Python, NumPy, dataclasses, SHA-256, pytest, existing SAXS quality contracts.

---

### Task 1: Define the failing mask contract tests

**Files:**
- Create: `tests/test_saxs_manual_mask_confirmed_rerun.py`

- [x] **Step 1: Write the failing tests**

Cover four behaviors: strict candidate serialization, pending candidate no-op,
digest mismatch fail-closed, and confirmed candidate propagation into the
existing detector report through `preprocess_pipeline`.

- [ ] **Step 2: Run the focused test file**

Run:

```powershell
python -m pytest -q tests/test_saxs_manual_mask_confirmed_rerun.py -o addopts= --basetemp=D:\PolyNexus-test-runs\pytest\saxs-manual-mask-red
```

Expected: failures because the mask contract module and preprocessing argument
do not exist yet.

### Task 2: Implement the pure candidate contract

**Files:**
- Create: `polynexus/core/saxs_engine/saxs_mask_edit.py`

- [x] **Step 1: Add strict mask digest and normalization helpers**

Normalize only two-dimensional boolean masks, include shape in a SHA-256 digest,
and reject non-array-like or shape-mismatched inputs with a typed
`MaskEditValidationError`.

- [x] **Step 2: Add candidate build/confirm/apply functions**

Return detached JSON-safe mappings with explicit `[row, column, masked]`
operations. Require `confirmed=True` in the apply function and never mutate the
input mask.

- [x] **Step 3: Run the focused contract tests**

Run the RED command from Task 1 and confirm the contract-only assertions pass
while the preprocessing assertion remains the only failure.

### Task 3: Thread confirmed masks through preprocessing

**Files:**
- Modify: `polynexus/core/saxs_engine/preprocess.py`
- Modify: `tests/test_saxs_manual_mask_confirmed_rerun.py`

- [x] **Step 1: Add an optional candidate parameter to `preprocess_pipeline`**

Resolve the configured mask first. Ignore pending/invalid candidates for
integration and add an explicit edit status to the existing mask provenance.
For a confirmed candidate, apply a copied mask and pass it to every current
full, sector, and azimuthal integration path.

- [x] **Step 2: Run the focused GREEN test**

Run:

```powershell
python -m pytest -q tests/test_saxs_manual_mask_confirmed_rerun.py -o addopts= --basetemp=D:\PolyNexus-test-runs\pytest\saxs-manual-mask-green
```

Expected: all focused tests pass with no raw image mutation.

### Task 4: Verify and checkpoint the atomic slice

**Files:**
- Modify: `docs/acceptance/2026-07-30-saxs-manual-mask-confirmed-rerun.md`
- Modify: `docs/agent/tasks/2026-07-30-saxs-manual-mask-confirmed-rerun.md`

- [x] **Step 1: Run task-scoped verification**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-manual-mask-confirmed-rerun.md --changed --types
```

- [x] **Step 2: Run the exact SAXS matrix and storage dry-run**

Use the repository's current `tests/test_saxs_*.py` enumeration and run
`python scripts/test_storage.py report --json` followed by the non-applying
clean command. Require complete summaries and exit codes.

- [x] **Step 3: Run diff hygiene and create the allowlist checkpoint**

```powershell
git diff --check
python scripts/auto_commit.py --message "feat(saxs): add confirmed manual mask boundary" --files polynexus/core/saxs_engine/saxs_mask_edit.py polynexus/core/saxs_engine/preprocess.py polynexus/core/saxs_engine/__init__.py tests/test_saxs_manual_mask_confirmed_rerun.py docs/superpowers/specs/2026-07-30-saxs-manual-mask-confirmed-rerun-design.md docs/superpowers/plans/2026-07-30-saxs-manual-mask-confirmed-rerun.md docs/agent/tasks/2026-07-30-saxs-manual-mask-confirmed-rerun.md docs/acceptance/2026-07-30-saxs-manual-mask-confirmed-rerun.md docs/agent/memory/active-work.md
```
