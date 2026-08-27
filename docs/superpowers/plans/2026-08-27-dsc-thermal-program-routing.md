# DSC thermal program routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Route all role-tagged `thermal_program.v1` DSC segments through one deterministic execution path.

**Architecture:** Extend the existing Mettler canonical converter to emit ramp and hold roles, add a unified DSCEngine template method that reuses `analyze_scan` and existing kinetics, and make ComputeRun prefer that method while retaining the old compatibility name.

**Tech Stack:** Python, NumPy, existing PolyNexus DSC engine, pytest.

---

### Task 1: Add failing converter tests

**Files:**
- Modify: `tests/test_dsc_canonical_isothermal_conversion.py`

- [ ] **Step 1: Write the failing test** for a thermal-cycle export producing role-tagged ramp segments and multiline sample mass.
- [ ] **Step 2: Run** `python -m pytest -q tests/test_dsc_canonical_isothermal_conversion.py -k thermal_cycle` and confirm failure because only isothermal holds are emitted.

### Task 2: Extend the canonical converter

**Files:**
- Modify: `polynexus/core/canonical_experiments/dsc_isothermal.py`
- Test: `tests/test_dsc_canonical_isothermal_conversion.py`

- [ ] **Step 1: Implement role segmentation and multiline mass extraction using the existing parsed rows; preserve old hold behavior and provenance.
- [ ] **Step 2: Run the focused converter tests and confirm green.

### Task 3: Add unified template execution

**Files:**
- Modify: `polynexus/core/dsc.py`
- Modify: `polynexus/core/compute/service.py`
- Test: `tests/test_dsc_kinetics.py`
- Test: `tests/test_compute_service.py`

- [ ] **Step 1: Add a failing mixed-role execution test.
- [ ] **Step 2: Implement `run_thermal_program_template`; dispatch heating/cooling through `analyze_scan`, isothermal holds through existing Avrami code, and preserve canonical provenance.
- [ ] **Step 3: Delegate `run_isothermal_template` to the new method and prefer the unified method in ComputeRun.
- [ ] **Step 4: Run focused tests.

### Task 4: Verify workflow compatibility and checkpoint

**Files:**
- Modify: `polynexus/core/agent_workflow/tpae.py` only if the public method/route contract requires it.
- Modify: `docs/agent/memory/active-work.md`
- Create: `docs/acceptance/2026-08-27-dsc-thermal-program-routing.md`

- [ ] **Step 1: Run** `python scripts/verify.py --task docs/agent/tasks/2026-08-27-dsc-thermal-program-routing.md --changed --types`.
- [ ] **Step 2: Record exact results and limitations in the acceptance note.
- [ ] **Step 3: Commit with** `python scripts/auto_commit.py --message "fix(dsc): route thermal program segments" --files ...`.
