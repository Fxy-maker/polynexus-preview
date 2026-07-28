# SAXS melting-range dirty-input guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `detect_melting_from_saxs()` tolerate dirty temperature and peak-intensity arrays without changing its melting thresholds or result contract.

**Architecture:** Coerce only the two axes consumed by the helper with the existing `_as_1d_float_array()` policy, align their common prefix, retain finite pairs in source order, and pass the survivors through the unchanged median/threshold logic.

**Tech Stack:** Python, NumPy, pytest, SAXS temperature analysis, `verify.py`, and `auto_commit.py`.

---

### Task 1: Write and run the failing regression

**Files:**
- Create: `tests/test_saxs_melting_dirty_input.py`

- [ ] Cover malformed temperature/peak tokens, non-finite pair removal,
  mismatched lengths, insufficient finite pairs, clean equivalence, order,
  and caller immutability.
- [ ] Run `python -m pytest -q tests/test_saxs_melting_dirty_input.py --basetemp=D:\PolyNexus_saxs_melting_red` and record the expected pre-fix failures.

### Task 2: Apply the minimal numeric boundary guard

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_temperature.py:851-900`

- [ ] Coerce temperatures and peak intensities with `_as_1d_float_array()`.
- [ ] Slice detached arrays to their common prefix and use a finite-pair mask
  without reordering or filtering finite negative intensities.
- [ ] Leave the initial median, normalization, sustained thresholds, result
  keys, and melting-range calculation unchanged.
- [ ] Run the focused regression and confirm GREEN.

### Task 3: Verify and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-28-saxs-melting-dirty-input-guard.md`
- Modify: `docs/superpowers/specs/2026-07-28-saxs-melting-dirty-input-guard-design.md`
- Modify: `docs/superpowers/plans/2026-07-28-saxs-melting-dirty-input-guard.md`
- Create: `docs/acceptance/2026-07-28-saxs-melting-dirty-input-guard.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] Run focused, all temperature, exact SAXS, structured verifier, diff,
  and test-storage report/dry-run commands.
- [ ] Record exact results and any full/boundary limitation from actual output.
- [ ] Create one local checkpoint with `scripts/auto_commit.py` and exactly
  the explicit allowlist.
