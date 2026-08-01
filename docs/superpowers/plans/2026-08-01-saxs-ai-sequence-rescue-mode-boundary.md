# SAXS AI Sequence Rescue Mode Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep existing sequence-rescue candidates in the AI prompt only for temperature contexts.

**Architecture:** Normalize the incoming mode inside the existing summary sanitizer and apply the candidate projection only for `temperature`. Add a direct sanitizer regression alongside the existing builder and prompt tests.

**Tech Stack:** Python, pytest, strict JSON, existing SAXS summary sanitizer, and the repository structured verifier.

---

### Task 1: Reproduce the mode leak

**Files:**
- Modify: `tests/test_saxs_ai_summary_context.py`

- [ ] Pass a static summary payload containing a sequence candidate directly
  to `sanitize_saxs_ai_summary_context()` and assert the candidate is absent.
- [ ] Run the test and observe the expected RED because the sanitizer currently
  projects candidates without checking mode.

### Task 2: Add the fail-closed mode guard

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_ai_rescue.py`

- [ ] Normalize the incoming mode once inside the sanitizer.
- [ ] Project `sequence_rescue_candidates` only when that mode is
  `temperature`; leave all existing metric and raw-field sanitization intact.
- [ ] Run the focused summary/Advisor/prompt regression and confirm GREEN.

### Task 3: Verify and checkpoint

- [ ] Run the complete SAXS matrix and task-scoped structured verifier.
- [ ] Run storage report/clean dry-run without `--apply`, diff audit, and create
  one explicit allowlist checkpoint.
