# Flexible DSC thermal qualification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove material-specific DSC conversion and execution blockers while preserving quality warnings and provenance.

**Architecture:** Canonical conversion retains all duration-qualified finite holds without a melt-temperature prerequisite. The DSC executor performs only hard structural validation and projects soft temperature warnings into result metadata/flags.

**Tech Stack:** Python, NumPy, pytest, existing canonical experiment and DSC contracts.

---

### Task 1: Regression tests for flexible conversion and execution

**Files:**
- Modify: `tests/test_dsc_canonical_isothermal_conversion.py`
- Modify: `tests/test_dsc_kinetics.py`

- [ ] Add tests showing a stable hold without a preceding 200 C hold is ready.
- [ ] Add tests showing noisy/offset holds remain ready with `quality_warnings`.
- [ ] Add a PA11-like hold test proving the canonical executor returns Avrami output.

### Task 2: Remove material-specific conversion gates

**Files:**
- Modify: `polynexus/core/canonical_experiments/dsc_isothermal.py`

- [ ] Remove the melt-temperature constant and `prepared` state from both conversion branches.
- [ ] Keep hard structural validation; attach soft temperature diagnostics as warnings in evidence and segment payloads.
- [ ] Preserve source ranges and conversion hashes.

### Task 3: Make executor qualification warning-based

**Files:**
- Modify: `polynexus/core/dsc.py`

- [ ] Keep minimum point/duration and array integrity checks.
- [ ] Stop rejecting offset/span/noise-only holds.
- [ ] Copy warning codes into scan metadata and Avrami quality flags.

### Task 4: Verify and record replay boundary

**Files:**
- Create: `docs/agent/tasks/2026-08-28-dsc-flexible-thermal-qualification.md`
- Create: `docs/acceptance/2026-08-28-dsc-flexible-thermal-qualification.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] Run focused DSC conversion/kinetics/ComputeRun tests.
- [ ] Replay PA11 and PA12-50 isothermal files and record statuses and warning counts.
- [ ] Run `python scripts/verify.py --task ... --changed --types` and checkpoint only allowlisted files.
