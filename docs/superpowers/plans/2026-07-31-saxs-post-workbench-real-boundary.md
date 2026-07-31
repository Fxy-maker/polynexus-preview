# Post-Workbench Real SAXS Boundary Evidence Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use TDD only for behavior changes; this documentation-only audit has no production-code change. Record complete pytest summaries and checkpoint only the explicit document allowlist.

**Goal:** Refresh PAD8 and real SAXS lifecycle evidence after the Workbench scientific-review entry checkpoint.

**Architecture:** Execute two existing read-only pytest contracts with separate external D: basetemps, then record their exact summaries and limitations in task evidence. No production files are in scope.

**Tech Stack:** Python, pytest, existing SAXS fixtures, Markdown task artifacts, `scripts/verify.py`, and `scripts/auto_commit.py`.

---

### Task 1: Establish the documentation boundary

**Files:**
- Read: `tests/test_saxs_real_2d_scientific_acceptance.py`
- Read: `tests/test_real_published_run_walkthrough.py`
- Create: the spec, plan, task card, and acceptance record listed in the task allowlist

- [x] Define the two existing test shards, their external basetemps, pass-evidence rule, non-goals, and human scientific limitations.

### Task 2: Replay PAD8 and real SAXS lifecycle

**Files:**
- Read-only test fixtures and test modules

- [x] Run `python -m pytest -q tests/test_saxs_real_2d_scientific_acceptance.py -vv --basetemp=D:\PolyNexus-test-runs\saxs-post-workbench-pad8-20260731`; it returned `4 passed in 18.60s`, exit `0`.
- [x] Run `python -m pytest -q tests/test_real_published_run_walkthrough.py -k saxs -vv --basetemp=D:\PolyNexus-test-runs\saxs-post-workbench-lifecycle-20260731`; it returned `3 passed, 12 deselected in 90.79s`, exit `0`.
- [x] Treat any timeout, setup error, crash, or missing summary as incomplete rather than pass evidence.

### Task 3: Verify and checkpoint the evidence

**Files:**
- Modify: `docs/agent/tasks/2026-07-31-saxs-post-workbench-real-boundary.md`
- Modify: `docs/superpowers/plans/2026-07-31-saxs-post-workbench-real-boundary.md`
- Modify: `docs/acceptance/2026-07-31-saxs-post-workbench-real-boundary.md`
- Create/modify: `docs/superpowers/specs/2026-07-31-saxs-post-workbench-real-boundary-design.md`

- [x] Record exact test output, exit codes, storage/diff verification, and known limitations.
- [x] Run `python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-post-workbench-real-boundary.md --changed --types` and `git diff --check`.
- [x] Run `python scripts/test_storage.py report --json` and `python scripts/test_storage.py clean --older-than-hours 24 --json`; no `--apply` was used.
- [x] Create one local checkpoint with the explicit four-document allowlist.
