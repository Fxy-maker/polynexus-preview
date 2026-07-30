# Current-head Full/Boundary Post-cleanup Recheck Implementation Plan

> **For agentic workers:** This is a verification-only plan. Execute each task in order and checkpoint only the explicit documentation allowlist.

**Goal:** Establish fresh current-HEAD full/boundary evidence after the test-storage policy update without mutating code or test data.

**Architecture:** Use the existing `scripts/verify.py` and `scripts/boundary_audit.py` contracts. Classify outcomes from complete stdout, stderr, process exit codes, and actual summaries; keep storage inspection separate and dry-run only.

**Tech Stack:** PowerShell, Python, pytest, repository verification scripts, Markdown audit records.

---

### Task 1: Establish the audit boundary

**Files:**
- Read: `AGENTS.md`, `README.md`, existing SAXS/full-boundary task cards and memory.
- Create: `docs/superpowers/specs/2026-07-30-current-head-full-boundary-post-cleanup-recheck-design.md`
- Create: `docs/superpowers/plans/2026-07-30-current-head-full-boundary-post-cleanup-recheck.md`
- Create: `docs/agent/tasks/2026-07-30-current-head-full-boundary-post-cleanup-recheck.md`

- [x] Confirm current branch, parallel changes, active Python/pytest processes, D: free space, and dry-run storage inventory.
- [x] Keep the allowlist limited to this audit's spec, plan, task, acceptance, and durable audit-memory entry.

### Task 2: Run authoritative verification

**Files:**
- Read: `scripts/verify.py`, `scripts/boundary_audit.py` output.
- Write: dedicated external test output only through the verifier's configured basetemp.

- [ ] Run `python scripts/verify.py --changed --types --full --boundary` after confirming no other pytest process is active.
- [ ] Require a complete pytest summary, wrapper exit code `0`, quality/preprocessing summaries, and boundary success before classifying the run as pass.
- [ ] Preserve exact failure, timeout, disk, setup, or incomplete-output classifications when any gate does not complete.

### Task 3: Verify and checkpoint

**Files:**
- Create: `docs/acceptance/2026-07-30-current-head-full-boundary-post-cleanup-recheck.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] Run `python scripts/verify.py --task docs/agent/tasks/2026-07-30-current-head-full-boundary-post-cleanup-recheck.md --changed --types`.
- [ ] Run `git diff --check`.
- [ ] Run storage report and clean dry-run again; do not pass `--apply`.
- [ ] Review the cumulative diff and create one explicit documentation-only checkpoint with `scripts/auto_commit.py`.
