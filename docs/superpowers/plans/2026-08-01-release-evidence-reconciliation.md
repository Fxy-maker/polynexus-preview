# Current Release Evidence Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (recommended) to execute this documentation task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconcile the current release ledger with the latest complete formal verification while preserving conditional scientific disposition.

**Architecture:** Add a dated acceptance record and link it to a structured task card and design note. Existing historical audit records remain unchanged; no production or test behavior is touched.

**Tech Stack:** Markdown task/spec/plan/acceptance records, `task_check.py`, `verify.py`, `boundary_audit.py`.

---

### Task 1: Establish the evidence sources

**Files:**
- Read: `docs/agent/tasks/2026-07-31-formal-pytest-temp-collection-boundary.md`
- Read: `docs/agent/tasks/2026-07-31-saxs-2d-ai-context-bridge.md`
- Read: `docs/agent/tasks/2026-07-31-full-goal-release-evidence-audit.md`

- [x] **Step 1: Record the authoritative current summaries**

Use the formal task's latest current-head result: `3303 passed, 18 skipped,
12 warnings in 2244.54s`, wrapper exit `0`, quality `297`, preprocessing
`106`, and boundary audit exit `0`. Use the SAXS bridge task's checkpoint
`edad9a9`, latest focused `26 passed`, and latest SAXS matrix `710 passed`.

### Task 2: Write the current evidence record

**Files:**
- Create: `docs/acceptance/2026-08-01-release-evidence-reconciliation.md`
- Create: `docs/superpowers/specs/2026-08-01-release-evidence-reconciliation-design.md`
- Create: `docs/agent/tasks/2026-08-01-release-evidence-reconciliation.md`

- [x] **Step 1: Preserve historical timeout meaning**

State that the old `124`/no-summary run remains historical incomplete evidence
and is superseded for current classification by the complete exit-`0` run.

- [x] **Step 2: Preserve scientific gates**

State the IR, NMR solid-C, Joint, restarted-GUI, and owner-authorization
conditions exactly as existing policy records define them. Do not add inferred
coordinates, assignments, conflict precedence, or publication promotion.

### Task 3: Verify and checkpoint

**Files:**
- Modify: the four files in the explicit task allowlist.

- [x] **Step 1: Run task and structural verification**

```powershell
python scripts/task_check.py --task docs/agent/tasks/2026-08-01-release-evidence-reconciliation.md
python scripts/verify.py --task docs/agent/tasks/2026-08-01-release-evidence-reconciliation.md --changed --types
python scripts/boundary_audit.py --root D:\PolyNexus --json
git diff --check
```

Expected: all commands exit `0`; quality and preprocessing gates remain
`297`/`106`.

Observed: task-check, structured verifier, boundary audit, and diff all exited
`0`; quality and preprocessing gates were `297`/`106`.

- [x] **Step 2: Checkpoint the exact allowlist**

```powershell
python scripts/auto_commit.py --message "docs(release): reconcile current verification evidence" --files docs/agent/tasks/2026-08-01-release-evidence-reconciliation.md docs/superpowers/specs/2026-08-01-release-evidence-reconciliation-design.md docs/superpowers/plans/2026-08-01-release-evidence-reconciliation.md docs/acceptance/2026-08-01-release-evidence-reconciliation.md
```
