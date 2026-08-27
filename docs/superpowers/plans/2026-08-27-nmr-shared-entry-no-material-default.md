# NMR Shared Entry Without Material Defaults Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route NMR through the shared canonical/ComputeRun path without inventing material identity.

**Architecture:** Reuse the generic table converter for ppm spectra and add a source-bound envelope for opaque NMR inputs. Keep the existing NMR provider and optional shift library unchanged except for explicit-scope behavior.

**Tech Stack:** Python, dataclasses, pandas, pytest, existing canonical experiment and ComputeRun contracts.

---

### Task 1: Protect the NMR conversion contract

**Files:**
- Create: `tests/test_nmr_shared_entry.py`

- [ ] Write tests for ppm-table conversion, opaque FID envelope conversion, and no-material generic metrics/Xc behavior.
- [ ] Run the focused tests and observe the expected failures.

### Task 2: Extend the generic one-dimensional converter

**Files:**
- Modify: `polynexus/core/canonical_experiments/one_dimensional.py`
- Modify: `polynexus/core/canonical_experiments/registry.py`

- [ ] Add NMR ppm aliases and `nmr.spectrum.v1` family/template selection.
- [ ] Add NMR to the generic table technique set without changing IR/SAXS/WAXS behavior.
- [ ] Add a source-bound `raw-file-envelope.nmr.v1` registry path for FID/vendor inputs.
- [ ] Run conversion and registry tests.

### Task 3: Attach NMR templates in ComputeRun

**Files:**
- Modify: `polynexus/core/compute/service.py`

- [ ] Include NMR in the shared conversion dispatch and preserve provider execution.
- [ ] Verify serialized template/result linkage and compatibility with direct NMR runs.
- [ ] Run ComputeRun and CLI/Batch consumer tests.

### Task 4: Verify material-neutral provider semantics

**Files:**
- Modify: `polynexus/core/nmr_engine/core.py` only if the new tests expose a material-default regression.

- [ ] Confirm no-material runs keep generic metrics and do not claim library assignments.
- [ ] Confirm explicit context material is a hint and Xc remains gated by phase support.
- [ ] Run NMR focused tests and structural verification.

### Task 5: Record and checkpoint

- [ ] Update task completion evidence and durable memory if behavior changed.
- [ ] Run `git diff --check` and the task verifier.
- [ ] Create one allowlisted local checkpoint with `scripts/auto_commit.py`.
