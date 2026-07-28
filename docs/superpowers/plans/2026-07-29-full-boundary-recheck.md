# Full/boundary recheck classification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox syntax for tracking.

**Goal:** Classify a current full/boundary verification attempt using real command and process evidence.

**Architecture:** Run the repository verifier with a D: basetemp, capture its wrapper result, and use a bounded process check only to distinguish lingering work from completion. No source mutation is part of this task.

**Tech Stack:** PowerShell, Python pytest, repository verifier.

---

### Task 1: Execute and classify

**Files:**
- Read: `scripts/verify.py`
- Create: external D: pytest basetemp only.

- [x] Launch the full/boundary command.
- [x] Record the tool timeout and exit code exactly.
- [x] Confirm child process exit in a bounded follow-up window without claiming
      a test result.

### Task 2: Record the limitation

**Files:**
- Create: `docs/agent/tasks/2026-07-29-full-boundary-recheck.md`
- Create: `docs/acceptance/2026-07-29-full-boundary-recheck.md`

- [x] Preserve the distinction between timeout, failure, and pass.
- [x] Run task validation and diff checks.
- [x] Create an allowlisted documentation checkpoint.
