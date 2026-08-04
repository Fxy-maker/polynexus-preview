# SAXS Correctness Slice A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Repair deterministic SAXS intensity, temperature, extrapolation, I/O, and provenance contracts without changing unresolved scientific models.

**Architecture:** Keep preprocessing as the correction boundary and `analyze_single()` as the single smoothing boundary. Keep sequence ordering and reference selection in the temperature service, and expose explicit provenance for limits and geometry instead of inferring trust from container presence.

**Tech Stack:** Python, NumPy, pytest, existing SAXS DTO/evidence contracts, repository verifier.

---

### Task 1: Add failing physical-core regressions

**Files:**
- Modify: `tests/test_saxs_temperature_phase_dirty_input.py`
- Modify: `tests/test_saxs_gibbs_thomson_dirty_input.py`
- Modify: `tests/test_saxs_extrapolation_helpers.py`
- Create: `tests/test_saxs_preprocess_contracts.py`

- [ ] Add tests for polarization zero-angle identity, cooling-solid labeling, fixed Gibbs intercept, and correlation flag divergence.
- [ ] Run the focused tests and record the expected failures before changing production code.

### Task 2: Normalize the 2D analysis input boundary

**Files:**
- Modify: `polynexus/core/saxs.py`
- Modify: `tests/test_saxs_batch_parameters.py`

- [ ] Add a regression asserting directory payloads store `Iq_norm` as analysis input while retaining `Iq_smooth` for display/provenance.
- [ ] Change single-frame and directory paths to pass corrected normalized unsmoothed intensity to `analyze_single()`.
- [ ] Run the focused batch tests and confirm one smoothing boundary.

### Task 3: Fix polarization and temperature semantics

**Files:**
- Modify: `polynexus/core/saxs_engine/preprocess.py`
- Modify: `polynexus/core/saxs_engine/saxs_temperature.py`
- Modify: focused preprocessing and temperature tests

- [ ] Implement the azimuthally averaged polarization factor with a unit q=0 limit.
- [ ] Add `COOLING_SOLID`, correct cooling thresholds, preserve cooling/isothermal acquisition order, and select the minimum-temperature reference.
- [ ] Run the physical-core tests and then the existing temperature/dirty-input matrix.

### Task 4: Fix Gibbs-Thomson and correlation control contracts

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_temperature.py`
- Modify: `polynexus/core/saxs_engine/core.py`

- [ ] Convert lamellar thickness to metres before surface-energy calculation and honor optional fixed `Tm_inf`.
- [ ] Thread both extrapolation flags through low/high-q branches without changing defaults.
- [ ] Run focused Gibbs and correlation tests.

### Task 5: Align I/O and provenance boundaries

**Files:**
- Modify: `polynexus/core/saxs.py`
- Modify: `polynexus/core/saxs_engine/io.py`
- Modify: `tests/test_saxs_edf_metadata_quality.py` and focused I/O tests

- [ ] Accept the declared 1D/2D extensions at the single-file engine boundary.
- [ ] Record configured batch limits as explicit skipped/truncation provenance.
- [ ] Derive geometry confidence from field-level provenance and add incomplete-header coverage.
- [ ] Run focused I/O/provenance tests.

### Task 6: Full verification and checkpoint

**Files:**
- Modify: task/spec/plan and durable memory only if final state changed

- [ ] Run the focused SAXS matrix.
- [ ] Run `python -X utf8 scripts/verify.py --task docs/agent/tasks/2026-08-03-saxs-correctness-slice-a.md --changed --types`.
- [ ] Run `git diff --check` and review the cumulative diff.
- [ ] Create a local checkpoint with `scripts/auto_commit.py` using an explicit allowlist containing only this slice's files.
- [ ] Report unresolved scientific-model items and all pre-existing workspace changes left untouched.
