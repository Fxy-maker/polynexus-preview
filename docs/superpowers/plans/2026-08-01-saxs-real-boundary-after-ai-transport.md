# SAXS Real Boundary After AI Transport Implementation Plan

> **For agentic workers:** This is a verification-only plan. Execute each task in order and preserve exact command summaries in the acceptance record.

**Goal:** Recheck real SAXS method, PAD8 scientific-boundary, and shared lifecycle evidence on the current head after AI context transport.

**Architecture:** Reuse the existing real-fixture tests and existing acceptance audit. Keep all scientific interpretation outside the automated slice and write only durable documentation evidence.

**Tech Stack:** Python, pytest, PowerShell, `scripts/verify.py`, and the repository test-storage dry-run CLI.

---

### Task 1: Establish the documentation allowlist

**Files:**
- Create: `docs/agent/tasks/2026-08-01-saxs-real-boundary-after-ai-transport.md`
- Create: `docs/superpowers/specs/2026-08-01-saxs-real-boundary-after-ai-transport-design.md`
- Create: `docs/superpowers/plans/2026-08-01-saxs-real-boundary-after-ai-transport.md`
- Create: `docs/acceptance/2026-08-01-saxs-real-boundary-after-ai-transport.md`

- [x] **Step 1: Record the four-file allowlist and non-goals**

  The task card, design, and this plan define a documentation-only slice. No
  production or test source file is eligible for the checkpoint.

- [x] **Step 2: Verify the task card before running tests**

  Run:

  ```powershell
  python scripts/task_check.py --task docs/agent/tasks/2026-08-01-saxs-real-boundary-after-ai-transport.md
  ```

  Expected: the task card is valid.

### Task 2: Replay real method evidence

**Files:**
- Read-only: `tests/test_saxs_real_method_evidence_surfaces.py`
- Write output only under: `D:\PolyNexus-test-runs\saxs-real-boundary-methods-20260801`

- [x] **Step 1: Run the real method replay**

  Run:

  ```powershell
  python -m pytest -q tests/test_saxs_real_method_evidence_surfaces.py -vv -o addopts= --basetemp=D:\PolyNexus-test-runs\saxs-real-boundary-methods-20260801
  ```

  Expected: a complete summary and exit code `0`; record the exact number of
  real mode cases and any warnings. A missing fixture or tool failure is
  recorded as incomplete.

### Task 3: Replay the PAD8 boundary

**Files:**
- Read-only: `tests/test_saxs_real_2d_scientific_acceptance.py`
- Read-only fixture: `D:\PolyNexus\测试数据\saxs\PAD8原位拉伸`
- Write output only under: `D:\PolyNexus-test-runs\saxs-real-boundary-pad8-20260801`

- [x] **Step 1: Run PAD8 acceptance tests**

  Run:

  ```powershell
  python -m pytest -q tests/test_saxs_real_2d_scientific_acceptance.py -vv -o addopts= --basetemp=D:\PolyNexus-test-runs\saxs-real-boundary-pad8-20260801
  ```

  Expected: a complete summary and exit code `0`. Verify from the test output
  and source contract that the scientific audit remains diagnostic-only and
  publication flags remain conservative.

### Task 4: Replay the shared SAXS lifecycle

**Files:**
- Read-only: `tests/test_real_published_run_walkthrough.py`
- Write output only under: `D:\PolyNexus-test-runs\saxs-real-boundary-lifecycle-20260801`

- [x] **Step 1: Run the SAXS lifecycle selector**

  Run:

  ```powershell
  python -m pytest -q tests/test_real_published_run_walkthrough.py -k saxs -vv -o addopts= --basetemp=D:\PolyNexus-test-runs\saxs-real-boundary-lifecycle-20260801
  ```

  Expected: a complete summary and exit code `0` for the three SAXS lifecycle
  cases. Do not count deselected cases as executed evidence.

### Task 5: Verify the documentation checkpoint

**Files:**
- Modify: the four documentation files in the explicit allowlist only

- [x] **Step 1: Run structured verification**

  Run:

  ```powershell
  python scripts/verify.py --task docs/agent/tasks/2026-08-01-saxs-real-boundary-after-ai-transport.md --changed --types
  ```

  Expected: task/memory, Ruff, compile, type baseline, quality, preprocessing,
  and whitespace checks complete successfully.

- [x] **Step 2: Run storage inventory and dry-run clean**

  Run:

  ```powershell
  python scripts/test_storage.py report --json
  python scripts/test_storage.py clean --older-than-hours 24 --json
  ```

  Expected: both are dry-run, `removed=0`, and any failures are recorded.
  Never add `--apply`.

- [x] **Step 3: Check the disjoint diff**

  Run:

  ```powershell
  git diff --check
  git diff --name-only
  ```

  Expected: only the four documentation files from this task are changed by
  the task; pre-existing memory and untracked directories remain untouched.

- [x] **Step 4: Record exact evidence in the acceptance note**

  Copy only complete command summaries, exit codes, warnings, and limitations
  into `docs/acceptance/2026-08-01-saxs-real-boundary-after-ai-transport.md`.
  Mark all human scientific/release gates explicitly open.

- [x] **Step 5: Create the explicit checkpoint**

  Run:

  ```powershell
  python scripts/auto_commit.py --message "docs(saxs): refresh real boundary evidence" --files docs/superpowers/specs/2026-08-01-saxs-real-boundary-after-ai-transport-design.md docs/superpowers/plans/2026-08-01-saxs-real-boundary-after-ai-transport.md docs/agent/tasks/2026-08-01-saxs-real-boundary-after-ai-transport.md docs/acceptance/2026-08-01-saxs-real-boundary-after-ai-transport.md
  ```

  Expected: one documentation-only commit and no push.
