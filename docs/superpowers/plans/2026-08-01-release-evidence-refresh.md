# Release Evidence Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Synchronize the full-goal acceptance ledger with the latest verified SAXS 2D checkpoint and current incomplete full-boundary evidence.

**Architecture:** Documentation-only update. The existing full-goal acceptance note remains authoritative; the task adds a dated evidence amendment and links the source task/checkpoint without changing release policy.

**Tech Stack:** Markdown, repository task checker, boundary audit, structured verifier.

---

### Task 1: Record current evidence

**Files:**
- Modify: `docs/acceptance/2026-07-31-full-goal-release-evidence-audit.md`
- Create: `docs/agent/tasks/2026-08-01-release-evidence-refresh.md`
- Create: `docs/superpowers/specs/2026-08-01-release-evidence-refresh-design.md`
- Create: `docs/superpowers/plans/2026-08-01-release-evidence-refresh.md`

- [x] **Step 1: Add the dated amendment**

Record checkpoint `a9e0743`, focused `58 passed`, full SAXS `700 passed, 6 warnings in 530.15s`, and structured quality/preprocessing `297/106` evidence.

- [x] **Step 2: Preserve incomplete and human gates**

Record the 40-minute full/boundary timeout as incomplete and retain IR mapping, NMR solid-C, Joint, restarted-GUI, and owner-approval gates.

### Task 2: Verify and checkpoint

- [x] **Step 1: Run task and repository checks**

Run `python scripts/task_check.py --task docs/agent/tasks/2026-08-01-release-evidence-refresh.md`, `python scripts/verify.py --task docs/agent/tasks/2026-08-01-release-evidence-refresh.md --changed --types`, `python scripts/boundary_audit.py --root D:\PolyNexus --json`, and `git diff --check`.

- [x] **Step 2: Create the explicit checkpoint**

Run `python scripts/auto_commit.py --message "docs(release): refresh current evidence ledger" --files docs/acceptance/2026-07-31-full-goal-release-evidence-audit.md docs/agent/tasks/2026-08-01-release-evidence-refresh.md docs/superpowers/specs/2026-08-01-release-evidence-refresh-design.md docs/superpowers/plans/2026-08-01-release-evidence-refresh.md`.
