# SAXS Post-Review-Consumer Real Boundary Re-audit Implementation Plan

> **For agentic workers:** This is a read-only scientific re-audit. No production implementation is authorized by this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Confirm current real SAXS scientific boundaries after 2D reviewer-consumer propagation.

**Architecture:** Reuse the existing PAD8 acceptance contract and real lifecycle walkthrough. Persist only the observed evidence in task and acceptance documents; never derive a new scientific decision from test success.

**Tech Stack:** Python, pytest, existing SAXS acceptance contracts, external Windows basetemp, Markdown evidence records.

---

### Task 1: Run the existing PAD8 boundary contract

**Files:**
- Test: `tests/test_saxs_real_2d_scientific_acceptance.py`
- Output: `D:\PolyNexus_saxs_post_review_real2d_focus`

- [x] **Step 1: Run the focused real boundary test**

  Run the exact command in the task card with an external basetemp. Require a
  final pytest summary and exit code `0`; record the result without changing
  the fixture or its output semantics.

### Task 2: Run the real SAXS lifecycle matrix

**Files:**
- Test: `tests/test_real_published_run_walkthrough.py`
- Output: `D:\PolyNexus_saxs_post_review_walkthrough`

- [x] **Step 1: Run only the three SAXS lifecycle cases**

  Use `-k saxs` and the explicit external basetemp. Require the three selected
  cases to pass and retain the existing role/diagnostic assertions.

### Task 3: Record the evidence and checkpoint only documents

**Files:**
- Modify: `docs/agent/tasks/2026-07-29-saxs-post-review-real-boundary-reaudit.md`
- Create: `docs/superpowers/specs/2026-07-29-saxs-post-review-real-boundary-reaudit-design.md`
- Create: `docs/superpowers/plans/2026-07-29-saxs-post-review-real-boundary-reaudit.md`
- Create: `docs/acceptance/2026-07-29-saxs-post-review-real-boundary-reaudit.md`

- [x] **Step 1: Write the durable evidence**

  Include exact commands, summaries, exit codes, read-only fixture statement,
  and the remaining human gates. Do not add `active-work.md` or
  `current-state.md` because parallel edits to those files are pre-existing.

- [ ] **Step 2: Run documentation hygiene and explicit allowlist checkpoint**

  Run `git diff --check`, then use `scripts/auto_commit.py` with only the four
  listed document paths. No source, test, scratch, or generated file may enter
  the checkpoint.
