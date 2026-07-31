# Full Goal Release Evidence Audit Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. This document records a documentation-only audit; it does not authorize scientific promotion, data deletion, or release.

**Goal:** Align the six technique modules and shared Results Workbench against the full-goal acceptance model and record which gates are automated, structurally evidenced, visually reviewed, scientifically confirmed, or still conditional.

**Architecture:** Use existing task cards, acceptance notes, durable memory references, and current test evidence as the source of truth. Keep software evidence separate from human scientific approval, vendor-native semantics, and final publication authorization. The audit changes only its own task, plan, and acceptance files.

**Tech Stack:** Markdown task/plan/acceptance records, `scripts/verify.py`, `scripts/boundary_audit.py`, and `git diff --check`.

---

### Task 1: Inventory the existing evidence

**Files:**
- Read: `docs/agent/tasks/2026-07-29-full-goal-requirements-audit.md`
- Read: `docs/agent/tasks/2026-07-29-release-decision-packet.md`
- Read: `docs/agent/tasks/2026-07-30-nmr-solid-c-readiness.md`
- Read: `docs/agent/tasks/2026-07-30-ir-mapping-results-provenance.md`
- Read: `docs/agent/tasks/2026-07-28-joint-evidence-weighted-conflicts.md`
- Read: latest SAXS task and acceptance records after the parallel thread finishes

- [x] Record each module's automated lifecycle, evidence, figure/manifest, gallery/editor/export, fallback, real-data, and visual evidence references in the task card.
- [x] Preserve every missing source-native or human gate as conditional rather than inferring a scientific value.

### Task 2: Classify the release boundaries

**Files:**
- Modify: `docs/agent/tasks/2026-07-31-full-goal-release-evidence-audit.md`

- [x] Classify each gate as `automated`, `structural-only`, `visual-review`, `scientific-review`, or `release-approval`.
- [x] State the allowed publication consequence for each open gate: diagnostic-only, assignment-limited, conditional, or not yet authorized.
- [x] Keep SAXS parallel changes outside this task's changed-file allowlist.

### Task 3: Verify the audit record

**Files:**
- Read: task, plan, and acceptance files in this audit

- [x] Run `python scripts/boundary_audit.py --root D:\PolyNexus --json` and record the real exit code `0`.
- [x] Run `python scripts/verify.py --task docs/agent/tasks/2026-07-31-full-goal-release-evidence-audit.md --changed --types` and record the real exit code `0` and selected gates.
- [x] Run `git diff --check` and record the real exit code `0`.
- [x] Do not claim a full repository pass from a task-scoped verifier or from a process that produced no pytest summary.

### Task 4: Publish the conditional acceptance note

**Files:**
- Create: `docs/acceptance/2026-07-31-full-goal-release-evidence-audit.md`

- [x] Link the evidence matrix, verification commands, exact observed outcomes, and remaining gates.
- [x] State that the audit is complete only as an evidence classification; the project release remains conditional until the listed scientific, visual, and owner-approval gates close.
- [x] Create one explicit allowlist checkpoint containing only this audit's task, plan, and acceptance files.
