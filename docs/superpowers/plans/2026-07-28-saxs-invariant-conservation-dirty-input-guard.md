# SAXS invariant-conservation dirty-input guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `check_invariant_conservation()` safely degrade dirty strain/Q* arrays without changing its invariant calculation or physical gates.

**Architecture:** Reuse `_as_1d_float_array()` and `_coerce_strain_value()` at the public boundary, align a detached common prefix, retain finite pairs in order, and run the unchanged conservation summary.

**Tech Stack:** Python, NumPy, pytest, SAXS strain analysis, `verify.py`, and `auto_commit.py`.

---

### Task 1: Write and run the failing regression

**Files:**
- Create: `tests/test_saxs_invariant_conservation_dirty_input.py`

- [ ] Add dirty-token, non-finite-pair, mismatch, tolerance, insufficient,
  clean-equivalence, order, and immutability assertions.
- [ ] Run `python -m pytest -q tests/test_saxs_invariant_conservation_dirty_input.py --basetemp=D:\PolyNexus_saxs_invariant_conservation_red` and record the expected raw-array failures.

### Task 2: Apply the minimal pair-boundary guard

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_strain.py:754-790`

- [ ] Coerce both arrays and the scalar tolerance with existing helpers.
- [ ] Align the common prefix and filter finite pairs without adding a Q*
  positivity rule or changing result keys.
- [ ] Run focused GREEN and confirm clean/reference equivalence.

### Task 3: Verify, document, and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-28-saxs-invariant-conservation-dirty-input-guard.md`
- Modify: `docs/superpowers/specs/2026-07-28-saxs-invariant-conservation-dirty-input-guard-design.md`
- Modify: `docs/superpowers/plans/2026-07-28-saxs-invariant-conservation-dirty-input-guard.md`
- Create: `docs/acceptance/2026-07-28-saxs-invariant-conservation-dirty-input-guard.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] Run focused, strain/temperature, exact SAXS, structured verifier,
  targeted lint/compile, diff, and storage report/dry-run checks.
- [ ] Record unrelated changed-file verifier limitations if present and create
  one explicit allowlist checkpoint.
