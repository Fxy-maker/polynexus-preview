# Release State Evidence Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Reconcile the current release-state evidence across all techniques without changing scientific or publication semantics.

**Architecture:** Documentation-only snapshot. The task card is the decision index, the acceptance record contains exact outcomes, and the design note fixes the fail-closed boundary. Existing task cards remain the source records; no new approval field is introduced.

**Tech Stack:** Markdown, repository verifier, boundary audit, Git diff checks.

---

### Task 1: Establish the evidence boundary

**Files:**
- Create: `docs/superpowers/specs/2026-07-31-release-state-reconciliation-design.md`
- Create: `docs/superpowers/plans/2026-07-31-release-state-reconciliation.md`
- Create: `docs/agent/tasks/2026-07-31-release-state-reconciliation.md`
- Create: `docs/acceptance/2026-07-31-release-state-reconciliation.md`

- [x] **Step 1: Record source documents**

Link the current full-goal audit, non-SAXS lifecycle, Joint real-data, native
visual, release-decision, and latest SAXS evidence records.

- [x] **Step 2: Preserve classifications**

Use `automated`, `structural/visual`, `scientific-review`, and
`release-approval` as separate classes. Record the SAXS full-matrix timeout as
incomplete evidence.

### Task 2: Record safe publication consequences

**Files:**
- Modify: `docs/agent/tasks/2026-07-31-release-state-reconciliation.md`
- Modify: `docs/acceptance/2026-07-31-release-state-reconciliation.md`

- [x] **Step 1: Keep IR mapping diagnostic-only**

Require source-matched native coordinates, dimension/origin/ROI/flattening
semantics, and calibration before promotion.

- [x] **Step 2: Keep NMR solid-C assignment-limited**

Require a source-linked assignment truth set and confirmed calibrated ppm axis
before any Xc promotion.

- [x] **Step 3: Keep Joint fail-closed**

Require reviewer-confirmed conflict interpretation; assign no automatic
scientific priority to DSC, SAXS, or WAXS.

### Task 3: Verify and checkpoint

**Files:**
- The four files above only.

- [x] **Step 1: Run the boundary audit**

Run `python scripts/boundary_audit.py --root D:\PolyNexus --json` and record
its real exit code.

- [x] **Step 2: Run the structured verifier**

Run `python scripts/verify.py --task docs/agent/tasks/2026-07-31-release-state-reconciliation.md --changed --types` and record any baseline limitation without repairing unrelated files.

- [x] **Step 3: Check the diff**

Run `git diff --check` and inspect the explicit changed-file allowlist.

- [x] **Step 4: Create one checkpoint**

Use `scripts/auto_commit.py` with only the four documentation paths above.
Never include parallel SAXS, memory, scratch, or test-storage paths.
