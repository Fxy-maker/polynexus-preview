# SAXS AI Orchestrator Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development and superpowers:verification-before-completion. Steps use checkbox syntax.

**Goal:** Route SAXS AI preprocessing through the SAXS-specific bridge and
preserve candidate-only plan/decision provenance for reports and export.

**Architecture:** Add a public validator to the existing bridge. The shared
orchestrator uses that validator, keeps its existing adapter/trial/transaction
flow, then stores the exact generated candidates in a `SAXSAIRescuePlan` and
wraps the existing decision outcome with `SAXSAIRescueDecision`.

**Tech Stack:** Python dataclasses, existing preprocessing contracts, pytest.

---

### Task 1: Add a public SAXS intent validator

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_ai_rescue.py`
- Test: `tests/test_saxs_ai_rescue_bridge.py`

- [x] Write a test that calls the validator with a valid SAXS payload and a
  payload missing `physical_parameters`.
- [x] Run the focused test and confirm the missing-feature case fails.
- [x] Refactor the existing private validation logic into the public validator
  and reuse it from `build_saxs_ai_rescue_plan`.
- [x] Run the focused bridge suite and confirm all tests pass.

### Task 2: Integrate the validator and plan/decision audit

**Files:**
- Modify: `polynexus/orchestrator_preprocess.py`
- Create: `tests/test_saxs_ai_orchestrator_handoff.py`

- [x] Add a fake SAXS orchestrator test that proves an invalid protected-field
  payload fails before trial-engine creation.
- [x] Add a valid shadow test that proves the report and source engine carry
  JSON-safe candidate-only plan/decision fields.
- [x] Run the new suite to establish the failing integration behavior.
- [x] Invoke the SAXS validator before generic parsing; collect the exact
  generated candidates into `SAXSAIRescuePlan`.
- [x] Wrap the selected shared decision with `assess_saxs_ai_candidate` and
  attach plain dictionaries to the report and engine.
- [x] Run the new suite and the existing orchestrator automation suite.

### Task 3: Verify and checkpoint

**Files:**
- Update: task card, spec/plan, and durable memory.

- [x] Run the SAXS AI, orchestrator, export, and structured verifier commands.
- [x] Review `git diff --check` and preserve all pre-existing untracked files.
- [ ] Create one allowlist-only local checkpoint with `scripts/auto_commit.py`.
