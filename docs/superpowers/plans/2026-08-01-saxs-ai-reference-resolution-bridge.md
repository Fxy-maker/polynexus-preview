# SAXS AI Reference Resolution Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Attach a fail-closed, detached resolution record for AI SAXS sequence-candidate references to the current orchestrator round.

**Architecture:** Add a pure adapter beside the existing resolver in `saxs_ai_rescue.py`. It reads only current result candidates and normalized advisory IDs, then attach its JSON-safe output in `orchestrator_run_round.py` after `Advisor.advise()` returns. Existing AI normalization, analysis, validation, and configuration mutation remain unchanged.

**Tech Stack:** Python mappings/dataclasses, existing `RescueCandidate` contract, pytest, and the repository structured verifier.

---

### Task 1: Write the bridge RED tests

**Files:**
- Modify: `tests/test_saxs_ai_rescue_bridge.py`
- Modify: `tests/test_saxs_orchestrator_loop.py`

- [ ] Add a test in `tests/test_saxs_ai_rescue_bridge.py` that supplies one full temperature result candidate and one exact advisory ID, then asserts one detached resolved record.
- [ ] Add tests for unknown/non-string IDs, missing candidates, non-temperature modes, and incomplete candidate provenance; assert unresolved IDs/reason codes and no candidate fabrication.
- [ ] Add an orchestrator regression in `tests/test_saxs_orchestrator_loop.py` proving the diagnostic field is attached after advice and that the engine's analysis/config state is unchanged.
- [ ] Run the focused tests before implementation and confirm the expected missing-adapter or missing-field failure.

### Task 2: Implement the pure bridge

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_ai_rescue.py`
- Modify: `polynexus/core/saxs_engine/__init__.py` if the public package API exposes the adapter

- [ ] Add `resolve_saxs_ai_candidate_references(result, advice, *, mode)` with a strict mapping return type.
- [ ] Read `saxs_candidate_references` only from a mapping, normalize exact strings without inventing IDs, and resolve each against the current temperature candidate records through `resolve_sequence_rescue_candidate`.
- [ ] Return detached JSON-safe candidate dictionaries, stable unresolved IDs, and reason codes; never call analysis or validation.
- [ ] Run the bridge focused tests and confirm GREEN.

### Task 3: Attach diagnostic evidence to one round

**Files:**
- Modify: `polynexus/orchestrator_run_round.py`
- Test: focused orchestrator regression from Task 1

- [ ] Copy the Advisor mapping and add `saxs_candidate_reference_resolution` only for SAXS advice, preserving the original response fields.
- [ ] Pass the current engine/result and the existing mode to the pure bridge; keep all non-SAXS and unsupported-mode behavior unchanged.
- [ ] Run focused Advisor, prompt, rescue, and orchestrator tests.

### Task 4: Verify and checkpoint

- [ ] Run `python scripts/verify.py --task docs/agent/tasks/2026-08-01-saxs-ai-reference-resolution-bridge.md --changed --types`.
- [ ] Run the complete `test_saxs_*.py` matrix and record its complete pytest summary.
- [ ] Run storage report and clean dry-run only; never run `test_storage.py --apply`.
- [ ] Run `git diff --check`, inspect the explicit allowlist, write the acceptance note, and create one `scripts/auto_commit.py` checkpoint.
