# Joint Conclusion Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Project a reviewer-owned, fail-closed Joint conclusion class without inventing scientific conflict precedence.

**Architecture:** Add a pure `classify_joint_conclusion()` boundary that consumes the existing review snapshot, row review payloads, validation rows, and technique issue rows. Attach its JSON-safe result to the existing Joint report and AI context while leaving formulas, thresholds, Figure roles, and `scientific_review` promotion unchanged.

**Tech Stack:** Python mappings/dataclasses already used by Joint, pytest, JSON-safe provenance.

---

### Task 1: Lock classification behavior with RED tests

**Files:**
- Modify: `tests/test_joint_hub_dataset.py`

- [x] Add tests for missing review, accepted review with WARN, accepted review with ERROR, and accepted review with no issues.
- [x] Run the focused tests and confirm failure because `joint_conclusion` is absent.

### Task 2: Implement the pure conclusion boundary

**Files:**
- Create: `polynexus/core/joint/conclusion.py`
- Modify: `polynexus/core/joint/__init__.py`

- [x] Parse only valid `scope="joint"` review records.
- [x] Preserve the three reviewer policy strings and record metadata without evaluating their text.
- [x] Return `review_required`, `rejected`, `blocked`, `conditional`, or `accepted` using existing review status and issue severity.

### Task 3: Attach the projection to the report

**Files:**
- Modify: `polynexus/core/joint/dataset.py`
- Modify: `tests/test_joint_hub_dataset.py`

- [x] Build the projection once per report and expose it at `joint_conclusion` and `ai_context["joint_conclusion"]`.
- [x] Keep existing `scientific_review`, `ai_boundary`, validation rows, formulas, and figure promotion behavior unchanged.
- [x] Run the Joint focused/lifecycle/figure/provenance matrix.

### Task 4: Verify, document, and checkpoint

**Files:**
- Create: `docs/agent/tasks/2026-07-30-joint-conclusion-policy.md`
- Create: `docs/acceptance/2026-07-30-joint-conclusion-policy.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] Run task-scoped verifier, boundary audit, and diff checks.
- [x] Record exact counts and the limitation that the policy does not supply scientific values.
- [x] Create one explicit allowlist checkpoint with no SAXS or real-dataset paths.
