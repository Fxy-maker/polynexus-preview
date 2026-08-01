# SAXS Sequence Rescue Reference Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a pure, fail-closed resolver from an advisory candidate ID to one existing deterministic temperature rescue candidate.

**Architecture:** Keep candidate identity checks beside the existing sequence candidate builder and gate validator. Materialize a fresh `RescueCandidate` from the current full record, reject incomplete or ambiguous records, and leave validation/execution to existing downstream callers.

**Tech Stack:** Python dataclasses, existing SAXS rescue contracts, pytest, strict detached mappings, and the repository structured verifier.

---

### Task 1: Write the resolver RED tests

**Files:**
- Modify: `tests/test_saxs_sequence_rescue.py`

- [x] Add a test that builds one existing temperature candidate, resolves it
  from its serialized record, and verifies the result has the same identity
  markers while being a newly materialized object.
- [x] Add parameterized fail-closed cases for an unknown ID, unsupported mode,
  AI kind, missing source, missing candidate-only marker, and duplicate matches.
- [x] Run the new tests and confirm failure because the resolver is not yet
  defined/exported.

### Task 2: Implement the core resolver

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_sequence_rescue.py`
- Modify: `polynexus/core/saxs_engine/__init__.py`

- [x] Accept a sequence of `RescueCandidate` objects or serialized mappings,
  normalize the requested ID/mode, and return `None` for unsupported inputs.
- [x] Materialize mappings with `RescueCandidate.from_dict`, collect exact ID
  matches, and reject malformed or ambiguous matches.
- [x] Enforce only the existing deterministic source/axis/metric/candidate-only
  identity markers; do not calculate or compare new numeric thresholds.
- [x] Return the candidate only after all identity checks pass; do not call any
  analysis engine or validation gate.
- [x] Export the resolver through the existing SAXS engine package API.

### Task 3: Verify and checkpoint

- [x] Run sequence-rescue, AI summary/Advisor, confirmed-rerun safety, and
  orchestrator focused tests.
- [x] Run the complete SAXS matrix and task-scoped structured verifier.
- [x] Run storage report and clean dry-run without `--apply`, then inspect
  `git diff --check` and the explicit allowlist.
- [x] Update acceptance evidence and create one local checkpoint containing
  only the resolver, focused test, package export, and task documents.
