# Canonical Capability Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a finite deterministic capability registry/executor and persist its item results on `ComputeRun`.

**Architecture:** Canonical measurements are the only input. A closed registry maps family-compatible capability ids to pure calculators; an executor isolates each item and emits `CapabilityItemResult`. `ComputeRun` stores the immutable tuple without changing legacy provider execution.

**Tech Stack:** Python dataclasses, standard-library hashing/JSON, pytest.

---

### Task 1: Lock the capability behavior with tests

**Files:**
- Create: `tests/test_capability_execution.py`

- [ ] **Step 1: Write tests for registry closure, deterministic outputs, failure isolation, and JSON-safe results.**
- [ ] **Step 2: Run `python -m pytest -p no:cacheprovider -q tests/test_capability_execution.py` and confirm collection fails because the capability module is absent.**

### Task 2: Implement the closed registry and executor

**Files:**
- Create: `polynexus/core/canonical_experiments/capabilities.py`
- Modify: `polynexus/core/canonical_experiments/__init__.py`

- [ ] **Step 1: Add frozen `CapabilitySpec`, `CapabilityRegistry`, and `CapabilityExecutor`.**
- [ ] **Step 2: Register `curve.summary.v1` and `curve.extrema.v1` for `spectrum_1d` and `scattering_1d`.**
- [ ] **Step 3: Run the focused capability tests and confirm they pass.**

### Task 3: Attach items to `ComputeRun`

**Files:**
- Modify: `polynexus/core/compute/models.py`
- Modify: `tests/test_compute_models.py`

- [ ] **Step 1: Add an immutable `capability_items` tuple with validation and JSON serialization.**
- [ ] **Step 2: Require items to be absent from non-completed runs and allow them on completed runs.**
- [ ] **Step 3: Run capability, compute-model, and compute-service tests.**

### Task 4: Verify and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-08-26-capability-execution.md`

- [ ] **Step 1: Run `python scripts/verify.py --task docs/agent/tasks/2026-08-26-capability-execution.md --changed --types`.**
- [ ] **Step 2: Run `git diff --check`.**
- [ ] **Step 3: Update completion evidence and create the allowlisted checkpoint with `scripts/auto_commit.py`.**
