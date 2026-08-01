# SAXS AI Sequence Rescue Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transport existing deterministic temperature rescue candidates into the summary-only SAXS AI context without changing rescue behavior.

**Architecture:** Add a small whitelist projection beside the existing SAXS summary builder. Build the projection only for the temperature series, place it under `series.sequence_rescue_candidates`, and reuse the existing prompt sanitizer so Advisor sees the same detached JSON-safe evidence.

**Tech Stack:** Python, pytest, strict JSON serialization, existing SAXS rescue DTOs, and the repository structured verifier.

---

### Task 1: Lock the missing transport with RED tests

**Files:**
- Modify: `tests/test_saxs_ai_summary_context.py`
- Modify: `tests/test_advisor.py`

- [ ] Add a temperature result with one existing rescue candidate and assert
  the summary contains its ID, frame index, proposed value, candidate-only
  mode, and validation flags while excluding an injected raw field.
- [ ] Add an Advisor prompt regression asserting the candidate ID is present
  after prompt sanitization and the candidate-only/physical-validation flags
  remain present.
- [ ] Run the focused tests and confirm RED because the current builder does
  not project `sequence_rescue_candidates`.

### Task 2: Implement the detached whitelist projection

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_ai_rescue.py`

- [ ] Add a private projection that accepts only the documented candidate and
  parameter keys, recursively JSON-sanitizes values, and returns no record for
  malformed input.
- [ ] Add the projection to the temperature `series` payload only; leave static
  and strain contexts unchanged.
- [ ] Extend prompt-side compact sanitization with the same candidate fields so
  raw/unknown fields cannot cross the Advisor boundary.
- [ ] Rerun the focused tests and confirm GREEN.

### Task 3: Verify and checkpoint

- [ ] Run the combined Advisor/prompt/summary/live regression.
- [ ] Run the complete SAXS file matrix and task-scoped structured verifier.
- [ ] Run storage report and clean dry-run without `--apply`, plus diff audit.
- [ ] Update the task and acceptance evidence, review the explicit allowlist,
  and create one local `auto_commit.py` checkpoint.
