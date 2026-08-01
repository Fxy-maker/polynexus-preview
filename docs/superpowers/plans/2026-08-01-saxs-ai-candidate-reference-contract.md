# SAXS AI Candidate Reference Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Normalize only current, existing SAXS temperature rescue candidate IDs into an advisory AI output field.

**Architecture:** Keep the existing summary projection as the source of candidate identity. Add a small Advisor-side allowlist normalizer and a SAXS prompt contract; do not add an execution route. The existing orchestrator will continue to dispatch only its established changes, action, and preprocess-intent fields, so reference-only advice is recorded but cannot run a trial.

**Tech Stack:** Python, existing Advisor/PromptBuilder contracts, strict JSON-compatible dictionaries, pytest, and the repository structured verifier.

---

### Task 1: Add the failing contract tests

**Files:**
- Modify: `tests/test_advisor.py`
- Modify: `tests/test_saxs_prompt_builder.py`

- [x] Add an Advisor provider fixture that returns valid, duplicate, unknown,
  and non-string `saxs_candidate_references` for a temperature context with
  one existing candidate. Assert only the exact existing ID remains once,
  `changes` stays empty, and no preprocess intent is created.
- [x] Add a static or missing-context case with the same provider field and
  assert the normalized references are empty.
- [x] Add a prompt assertion requiring exact current candidate IDs and stating
  that references are diagnostic-only and cannot apply, rerun, or mutate a
  configuration.
- [x] Run the focused tests and confirm RED because the current Advisor drops
  the field and the current SAXS prompt has no reference contract.

### Task 2: Implement the minimal Advisor allowlist

**Files:**
- Modify: `rag/advisor.py`

- [x] Extract allowed IDs only from a SAXS temperature context's
  `series.sequence_rescue_candidates` mappings.
- [x] Add a normalizer that keeps only string IDs in that set, preserves first
  occurrence order, and returns no more than the existing context list; do not
  echo unknown values or candidate payloads.
- [x] Pass the allowed set through both provider and fallback normalization.
- [x] Keep the direct `_normalize_advice` compatibility path unchanged when no
  SAXS context allowlist is supplied.

### Task 3: Add the prompt contract

**Files:**
- Modify: `rag/prompt_builder.py`

- [x] Add a SAXS-only response field example for
  `saxs_candidate_references` containing IDs already shown in the summary.
- [x] State that the field is diagnostic-only and cannot execute, rerun,
  interpolate, repair, or change configuration; keep raw q/I and detector
  exclusion language intact.

### Task 4: Verify and checkpoint

- [x] Run the Advisor/prompt/SAXS summary/orchestrator focused matrix and
  record the complete pytest summary and exit code.
- [x] Run the complete SAXS matrix and the task-scoped structured verifier.
- [x] Run storage report and clean dry-run without `--apply`, then run
  `git diff --check`.
- [x] Update the task/acceptance evidence and create one explicit allowlist
  checkpoint containing only this task's changed files.
