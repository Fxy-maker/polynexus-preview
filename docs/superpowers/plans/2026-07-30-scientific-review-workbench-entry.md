# Scientific Review Workbench Entry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist validated reviewer-owned decisions from Results Workbench against one exact analysis run.

**Architecture:** Expose the existing core review schema to a generic Qt dialog, then update one SampleDB run transactionally. The saved record is visible to History/Export but does not republish or promote figures.

**Tech Stack:** Python dataclasses, SQLite, PySide6, pytest, existing Results Workbench and review presentation adapters.

---

### Task 1: Expose the review schema

**Files:**
- Modify: `polynexus/core/scientific_review.py`
- Test: `tests/test_scientific_review.py`

- [x] Add a failing test for `required_decision_keys(scope)` and
  `review_scope_for_context(technique, submodule)` covering IR mapping, NMR
  solid-C, Joint, and an un-gated standard technique.
- [x] Run `python -m pytest tests/test_scientific_review.py -k "required_decision or scope_for_context" -q` and observe the missing-helper failure.
- [x] Implement tuple-returning helpers backed by the existing private mapping;
  unsupported or SAXS contexts return an empty tuple/`None` for this task.
- [x] Rerun the focused tests and assert callers cannot mutate the returned
  schema.

### Task 2: Add transactional run persistence

**Files:**
- Modify: `polynexus/data/sample_db.py`
- Test: `tests/test_scientific_review_workbench.py`

- [x] Write a failing test that creates two analysis runs, updates one with a
  valid serialized review, and asserts only that run's `analysis_evidence` and
  `results_summary.result.metadata` contain the record and decision snapshot.
- [x] Run the focused database test and observe the missing update method.
- [x] Implement `update_analysis_scientific_review(run_id, record_payload,
  decision_snapshot)` with one SQL transaction and JSON-safe serialization.
- [x] Add a not-found assertion and verify the second run is byte-equivalent.

### Task 3: Build the generic dialog

**Files:**
- Create: `polynexus/gui/scientific_review_dialog.py`
- Test: `tests/test_scientific_review_workbench.py`

- [x] Write a failing offscreen Qt test for dialog construction, valid record
  emission, and invalid required decision rejection.
- [x] Run the test to confirm the dialog module is absent.
- [x] Implement a scope-driven form using the core helpers, a JSON-safe text
  editor for each required decision, and a validated `accepted` signal/result.
- [x] Rerun the offscreen tests and preserve cancelled/invalid no-write paths.

### Task 4: Wire Workbench and presentation refresh

**Files:**
- Modify: `polynexus/gui/main_window_results_mixin.py`
- Modify: `polynexus/gui/analysis_history_service.py`
- Modify: `polynexus/gui/export_context_service.py`
- Test: `tests/test_scientific_review_workbench.py`

- [x] Add a failing integration assertion for a gated current run exposing an
  enabled review action and refreshed History/Export text after save.
- [x] Add the action only for IR mapping, NMR solid-C, and Joint; pass the
  current run id and source context into the dialog.
- [x] On acceptance, update the in-memory result payload, call the DB method,
  refresh History and review labels, and leave Figure assets/roles untouched.
- [x] Run the focused integration test and the existing review/history/export
  matrices.

### Task 5: Acceptance and checkpoint

**Files:**
- Create: `docs/acceptance/2026-07-30-scientific-review-workbench-entry.md`
- Modify: task/spec/plan and `docs/agent/memory/active-work.md`

- [x] Run the focused tests, `python scripts/verify.py --task ... --changed
  --types`, and `git diff --check` with external D: basetemp. The focused
  non-SAXS matrix passed `62` tests; the structured verifier passed quality
  `290` and preprocessing `106`.
- [x] Record exact outcomes and explicitly state that SAXS was excluded.
- [x] Create one `scripts/auto_commit.py` checkpoint with only the explicit
  allowlist from the task card.
