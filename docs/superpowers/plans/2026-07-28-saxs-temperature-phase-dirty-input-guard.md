# SAXS temperature-phase dirty-input guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `detect_temperature_phase()` tolerate malformed scalar SAXS indicators without changing its phase thresholds or enum contract.

**Architecture:** Reuse `_coerce_optional_float()` for the four numeric inputs, then execute the existing branch logic unchanged on local floats. The experiment type remains a caller-controlled string.

**Tech Stack:** Python, NumPy, pytest, SAXS temperature analysis, `verify.py`, and `auto_commit.py`.

---

### Task 1: Write and run the failing regression

**Files:**
- Create: `tests/test_saxs_temperature_phase_dirty_input.py`

- [ ] Add tests for numeric-string inputs, malformed Q*/L tokens, non-finite
  values, clean branch equivalence, and unknown experiment-type fallback.
- [ ] Run `python -m pytest -q tests/test_saxs_temperature_phase_dirty_input.py --basetemp=D:\PolyNexus_saxs_temperature_phase_red` and record the expected pre-fix TypeError failures.

### Task 2: Apply the minimal scalar guard

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_temperature.py:587-634`

- [ ] Coerce `Q_star`, `Q_star_solid`, `L`, and `L_solid` with
  `_coerce_optional_float()`.
- [ ] Leave Q*/Qsolid normalization, heating/cooling/isothermal conditions,
  cold-crystallization threshold, enum members, and default branch unchanged.
- [ ] Run the focused regression and confirm GREEN.

### Task 3: Verify, document, and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-28-saxs-temperature-phase-dirty-input-guard.md`
- Modify: `docs/superpowers/specs/2026-07-28-saxs-temperature-phase-dirty-input-guard-design.md`
- Modify: `docs/superpowers/plans/2026-07-28-saxs-temperature-phase-dirty-input-guard.md`
- Create: `docs/acceptance/2026-07-28-saxs-temperature-phase-dirty-input-guard.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] Run focused, temperature, exact SAXS, structured verifier, diff, and
  test-storage report/dry-run commands.
- [ ] Record exact outcomes and any full/boundary limitation from actual
  output, then create one explicit allowlist checkpoint.
