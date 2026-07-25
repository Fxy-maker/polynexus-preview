# Preprocessing Fallback Safety Matrix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a shared fail-closed fallback guard to AI-assisted preprocessing.

**Architecture:** Normalize fallback signals in the shared adapter contract, enforce the guard in the shared decision function, and test all five optimization techniques through one parameterized matrix. Joint remains a report-level AI review surface.

**Tech Stack:** Python, dataclasses, NumPy, pytest.

---

### Task 1: Red matrix

**Files:**
- Create: `tests/test_preprocess_cross_technique_matrix.py`

- [ ] Parameterize supported policies/adapters for AI-off, failed-run, and
  fallback-active evidence.
- [ ] Assert fallback-active evidence is rejected and reason round-trips.
- [ ] Run the new file and observe the fallback assertions fail.

### Task 2: Contract and adapter normalization

**Files:**
- Modify: `polynexus/core/preprocess_optimization/contracts.py`
- Modify: `polynexus/core/preprocess_optimization/adapters/base.py`

- [ ] Add optional fallback fields with safe defaults.
- [ ] Extract active/reason signals from candidate output/evidence without
  changing technique-specific metrics.
- [ ] Run the contract and adapter tests.

### Task 3: Fail-closed decision guard

**Files:**
- Modify: `polynexus/core/preprocess_optimization/decision.py`
- Test: `tests/test_preprocess_optimization_decision.py`

- [ ] Reject fallback-active evidence before score computation.
- [ ] Preserve existing shadow, confirmation, hard-guard, and audit behavior.
- [ ] Run the full focused preprocessing matrix.

### Task 4: Verify and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-25-preprocess-fallback-safety-matrix.md`
- Create: `docs/acceptance/2026-07-25-preprocess-fallback-safety-matrix.md`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md`

- [ ] Record exact counts and the Joint N/A boundary.
- [ ] Run `scripts/auto_commit.py` with the explicit allowlist.
