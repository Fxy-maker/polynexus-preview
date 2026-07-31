# Non-SAXS Real Published-Run Recheck Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. This is a verification-only task with no production-code change.

**Goal:** Re-run the existing non-SAXS real-fixture lifecycle on the current HEAD and capture complete evidence for DSC, WAXS, IR, and NMR through analysis, Manifest/Gallery, Editor, Export, and History restore.

**Architecture:** Reuse `tests/test_real_published_run_walkthrough.py` and its existing vendor/sample fixtures. Select only non-SAXS cases, use an external D: basetemp, and classify the result from the complete pytest summary and exit code. Preserve diagnostic-only and assignment-limited outcomes.

**Tech Stack:** Python, pytest, Qt offscreen, existing engine/publication services, Markdown task artifacts, `scripts/verify.py`, `scripts/test_storage.py`, and `git diff --check`.

---

### Task 1: Establish the evidence boundary

**Files:**
- Read: `tests/test_real_published_run_walkthrough.py`
- Create: this plan, the task card, and the acceptance record

- [x] Define the non-SAXS selector, external basetemp, complete-summary rule, and safe scientific limitations.
- [x] Exclude SAXS source, task, memory, and temporary-storage changes from the allowlist.

### Task 2: Replay real non-SAXS lifecycles

**Files:**
- Read-only: `tests/test_real_published_run_walkthrough.py` and `测试数据/`

- [x] Run the non-SAXS selector; the initial D: run recorded a storage failure, and the final C: `-p no:cacheprovider` run returned `12 passed, 3 deselected, 11 warnings in 291.31s`, exit `0`.
- [x] Require a complete pytest summary and exit code `0`; classify timeout, setup error, crash, or missing summary as incomplete.
- [x] Record the number of cases and any diagnostic-only/assignment-limited roles without promoting them.

### Task 3: Verify and checkpoint

**Files:**
- Modify: the task card, plan, and acceptance record

- [x] Run `python scripts/verify.py --task docs/agent/tasks/2026-07-31-nonsaxs-real-published-run-recheck.md --changed --types`; exit `0`, quality `297`, preprocessing `106`.
- [x] Run storage report and the authorized `clean --older-than-hours 24 --apply --json`; the apply removed eligible artifacts, skipped permission-locked historical directories, and left `eligible_bytes=0`.
- [ ] Run `python scripts/verify.py --task docs/agent/tasks/2026-07-31-nonsaxs-real-published-run-recheck.md --changed --types`.
- [x] Run `git diff --check` and perform a cumulative diff review.
- [x] Create one checkpoint using only this task's three documentation files.

### Task 4: Update the overall release audit

**Files:**
- Read: `docs/acceptance/2026-07-31-full-goal-release-evidence-audit.md`

- [x] Treat this evidence as automated real-fixture lifecycle proof only; retain the separate restarted-GUI, scientific, vendor-semantic, and final authorization gates.
