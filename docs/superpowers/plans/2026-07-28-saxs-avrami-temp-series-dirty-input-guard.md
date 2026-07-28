# SAXS Avrami temperature-series dirty-input guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `avrami_from_temp_series()` tolerate dirty numeric series without changing its temperature selection or Avrami science contract.

**Architecture:** Reuse `_as_1d_float_array()` for all three aligned axes, slice detached arrays to the common prefix, retain finite observations selected by the existing temperature tolerance, and delegate the unchanged fit to `avrami_kinetics()`.

**Tech Stack:** Python, NumPy, pytest, SAXS temperature analysis, `verify.py`, and `test_storage.py`.

---

### Task 1: Write and run the failing regression

**Files:**
- Create: `tests/test_saxs_avrami_temp_series_dirty_input.py`

- [ ] Add tests that call the public wrapper with a malformed temperature token, non-finite time/Xc values, mismatched lengths, and clean reference data.
- [ ] Assert selected observation order and relative-time anchoring through equality with an explicit survivor reference.
- [ ] Assert insufficient survivors remain invalid and caller-owned object arrays are unchanged.
- [ ] Run `python -m pytest -q tests/test_saxs_avrami_temp_series_dirty_input.py --basetemp=D:\PolyNexus_saxs_avrami_temp_series_red` and confirm the malformed/mismatched cases fail before production code changes.

### Task 2: Apply the minimal wrapper-boundary guard

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_temperature.py:809-827`

- [ ] Coerce the three inputs with `_as_1d_float_array()` and slice them to `min(size)`.
- [ ] Build `selected = isfinite(temp) & (abs(temp - Tc_target) <= tolerance)` and then retain finite time/Xc survivors in original order.
- [ ] Return the existing invalid result shape for fewer than five selected observations; otherwise subtract the first retained time and call `avrami_kinetics()`.
- [ ] Run the focused regression and confirm GREEN without changing `avrami_kinetics()`.

### Task 3: Verify, document, and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-28-saxs-avrami-temp-series-dirty-input-guard.md`
- Modify: `docs/superpowers/specs/2026-07-28-saxs-avrami-temp-series-dirty-input-guard-design.md`
- Modify: `docs/superpowers/plans/2026-07-28-saxs-avrami-temp-series-dirty-input-guard.md`
- Create: `docs/acceptance/2026-07-28-saxs-avrami-temp-series-dirty-input-guard.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] Run the focused test, all `test_saxs_temperature*.py`, all `test_saxs_*.py`, structured verification, `git diff --check`, and storage report/dry-run.
- [ ] Record exact output and any timeout limitation; never reuse historical full/boundary evidence as fresh evidence.
- [ ] Execute `scripts/auto_commit.py` with exactly the explicit task allowlist after verification.
