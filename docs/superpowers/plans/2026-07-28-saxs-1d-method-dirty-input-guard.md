# SAXS 1D physical-helper dirty-input guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` (recommended). Each task keeps focused evidence and an explicit allowlist checkpoint.

**Goal:** Reuse the existing deterministic q/I sanitizer at invariant, Porod,
and Kratky helper boundaries without changing their scientific calculations.

**Architecture:** Keep the sanitizer as the sole data-preparation policy and
leave all physical windows, integration bounds, point gates, and evidence
builders unchanged. The helpers receive detached survivors; the normal
analysis result continues to report provenance through its existing quality
contract.

**Tech Stack:** Python, NumPy, Pytest, SAXS quality contracts, `verify.py`, and
`auto_commit.py`.

---

### Task 1: Write the failing dirty-input tests

**Files:**
- Create: `tests/test_saxs_1d_method_dirty_input.py`

- [ ] Add a dirty-profile fixture and tests for invariant, Porod, and Kratky.
- [ ] Add an empty Kratky test and caller-array immutability assertions.
- [ ] Run the focused tests to capture the expected RED behavior.

### Task 2: Add the existing sanitizer at helper boundaries

**Files:**
- Modify: `polynexus/core/saxs_engine/core.py`
- Modify: `polynexus/core/saxs_engine/saxs_physical_helpers.py`

- [ ] Sanitize q/I before existing invariant and Kratky calculations.
- [ ] Sanitize q/I before existing Porod window selection.
- [ ] Add only the empty-Kratky guard required to preserve a stable fail-closed
  result shape.

### Task 3: Verify compatibility and checkpoint

**Files:**
- Modify: task/spec/plan and `docs/agent/memory/active-work.md` for evidence.

- [ ] Run focused GREEN, exact SAXS, structured verifier, and `git diff --check`.
- [ ] Record limitations and untouched pre-existing paths.
- [ ] Create one `auto_commit.py` checkpoint using only the explicit allowlist.
