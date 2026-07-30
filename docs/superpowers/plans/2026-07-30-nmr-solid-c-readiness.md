# NMR Solid-C Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make existing NMR solid-C assignment and axis limitations visible in shared evidence and Results review text.

**Architecture:** Add a pure status projection to `_nmr_analysis_bundle()`, copy it into assignment and structure evidence, and add a localized NMR branch to `result_review_round_support_summary_text()`. Existing assignment gates, axis decisions, review records, and figure roles remain the source of truth.

**Tech Stack:** Python dictionaries, existing NMR evidence contracts, i18n, pytest.

---

### Task 1: Add RED tests

**Files:**
- Modify: `tests/test_analysis_evidence.py`
- Modify: `tests/test_results_review_service.py`

- [x] Assert supported, assignment-limited, and missing solid-C states expose the expected JSON-safe readiness object.
- [x] Assert Results review text includes readiness and axis provenance for NMR evidence.
- [x] Run the focused tests and observe the missing readiness/text behavior.

### Task 2: Implement the core evidence projection

**Files:**
- Modify: `polynexus/core/analysis_evidence_nmr.py`

- [x] Classify only the existing `Xc_assignment_status` and sample/nucleus context.
- [x] Attach the same object to `assignment_evidence["readiness"]` and `structure_evidence["assignment_readiness"]`.
- [x] Preserve all existing fields and numerical behavior.

### Task 3: Implement the shared Results review summary

**Files:**
- Modify: `polynexus/gui/results_review_service.py`
- Modify: `polynexus/gui/i18n.py`

- [x] Add a localized NMR branch that presents readiness plus axis source/calibration state.
- [x] Keep the summary compact and use existing JSON-safe evidence only.

### Task 4: Verify and checkpoint

**Files:**
- Create: `docs/agent/tasks/2026-07-30-nmr-solid-c-readiness.md`
- Create: `docs/acceptance/2026-07-30-nmr-solid-c-readiness.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] Run focused evidence/GUI tests, NMR lifecycle/figure tests, task verifier, boundary audit, and diff checks.
- [x] Record that no assignment or axis scientific semantics were invented.
- [ ] Create one explicit allowlist checkpoint excluding SAXS and real data.
