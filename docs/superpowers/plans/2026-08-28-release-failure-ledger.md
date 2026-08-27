# Release Failure Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended; not used for this documentation checkpoint) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record the current release boundary without hiding historical failures.

**Architecture:** Store exact verifier counts and a stable category summary in
an acceptance note, then link it from agent memory.

**Tech Stack:** Markdown, repository verifier.

---

### Task 1: Record verification

**Files:**
- Create: `docs/acceptance/2026-08-28-full-suite-release-boundary.md`
- Create: `docs/agent/tasks/2026-08-28-release-failure-ledger.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] Run the full boundary verifier.
- [x] Record exact pass/fail/skip counts and categories.
- [x] Run task-scoped verification and diff check.
