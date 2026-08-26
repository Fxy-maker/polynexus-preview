# Optional Vendor Converter Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route generic 1-D table exports into canonical templates and leave vendor formats behind an explicit compatibility boundary.

**Architecture:** The converter registry chooses the deterministic generic table converter for supported IR/SAXS/WAXS table formats. It preserves `needs_input` rather than masking it and retains the old raw envelope only for formats/directories outside the generic converter. A small capability handoff executes the finite curve registry for ready templates.

**Tech Stack:** Python dataclasses, existing canonical converters, pytest.

---

### Task 1: Lock generic-first routing

**Files:**
- Modify: `tests/test_canonical_converter_registry.py`

- [ ] **Step 1: Update the CSV fixture to contain two numeric points and assert `spectrum_1d.v1` with measurement provenance.**
- [ ] **Step 2: Add a test proving ambiguous generic mapping returns `needs_input` rather than `raw-file-envelope`.**
- [ ] **Step 3: Add a vendor-like extension/directory test proving the compatibility envelope remains available.**
- [ ] **Step 4: Run the focused registry tests and observe the new expectations fail before implementation.**

### Task 2: Implement registry routing and capability handoff

**Files:**
- Modify: `polynexus/core/canonical_experiments/registry.py`
- Modify: `polynexus/core/canonical_experiments/capabilities.py`
- Modify: `tests/test_capability_execution.py`

- [ ] **Step 1: Route supported table extensions through `convert_one_dimensional_table`; preserve non-ready outcomes.**
- [ ] **Step 2: Add `execute_ready_template` using `CapabilityExecutor` and return item results without provider invocation.**
- [ ] **Step 3: Add a test that converts an IR table and obtains deterministic summary/extrema items.**
- [ ] **Step 4: Run focused tests and confirm all pass.**

### Task 3: Verify and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-08-26-optional-vendor-converters.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] **Step 1: Run the focused matrix and structured verifier.**
- [ ] **Step 2: Run `git diff --check`.**
- [ ] **Step 3: Record limitations and create the allowlisted checkpoint.**
