# SAXS Stability Map and Scientific Correctness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the AI tuning entry point run a strict, evidence-based SAXS stability study and close the identified physical/data-contract defects.

**Architecture:** Keep scientific behavior in `saxs_engine` and the stability evaluator in a core service module. The GUI receives a serializable report and delegates all mutations to `PreprocessTransactionService`. Use deterministic seeded sampling, bounded active refinement, cache keys, and explicit report decisions.

**Tech Stack:** Python 3.14, NumPy, PySide6, pytest, existing PolyNexus preprocessing contracts.

---

### Task 1: Scientific regression contracts

**Files:**
- Modify: `tests/test_saxs_scientific_correctness_repair.py`
- Modify: `tests/test_saxs_scientific_correctness_closure.py`
- Modify: `tests/test_saxs_preprocess.py`
- Create: `tests/test_saxs_stability_map.py`

- [x] Add failing tests for the upper crystallinity root, signed temperature invariant, signed correlation input, common q-unit spellings, unsupported-bin NaN/support output, periodic chi wrap, Porod gate evidence, and public Kp publication.
- [x] Run the new tests individually and record the expected failures.
- [x] Keep each test synthetic and independent of external data.

### Task 2: Physical and input-contract fixes

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_physical_helpers.py`
- Modify: `polynexus/core/saxs_engine/saxs_temperature.py`
- Modify: `polynexus/core/saxs_engine/core.py`
- Modify: `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- Modify: `polynexus/core/saxs_engine/io.py`
- Modify: `polynexus/core/saxs.py`

- [x] Select the invariant root using `cfg.crystallinity_gt_half` and pass the configured flag through the structure calculation.
- [x] Remove positive-only filtering from invariant/Fourier source preparation while keeping log fits positive-only.
- [x] Normalize reciprocal-length spellings through one shared parser and preserve fail-closed reasons.
- [x] Include `Kp` in static parameter output without changing its units.
- [x] Run the Task 1 physical tests until green, then run the existing focused scientific matrix.

### Task 3: Detector support and Porod/orientation fixes

**Files:**
- Modify: `polynexus/core/saxs_engine/preprocess.py`
- Modify: `polynexus/core/saxs_engine/saxs_strain.py`
- Modify: `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- Modify: `polynexus/core/saxs_engine/saxs_anisotropy.py`

- [x] Make manual 1D and sector integration return NaN for unsupported bins and emit support counts.
- [x] Copy per-frame strain configuration and pass explicit Porod limits to the Porod estimator.
- [x] Require slope tolerance and Iq4 plateau evidence before quantitative Porod status.
- [x] Use wrapped chi distance at the -pi/pi boundary.
- [x] Run detector, strain, orientation, and scientific regressions.

### Task 4: Stability study service

**Files:**
- Create: `polynexus/core/preprocess_optimization/stability.py`
- Modify: `polynexus/core/preprocess_optimization/__init__.py`
- Create: `tests/test_saxs_stability_map.py`

- [x] Define frozen request, trial, plateau, bootstrap, continuity, and report dataclasses with strict JSON-safe `to_dict()` output.
- [x] Implement seeded Latin-hypercube global points, bounded active refinement, explicit local confirmation grid, and canonical-config caching.
- [x] Implement plateau connectedness, parameter bounds, bootstrap confidence intervals, and per-trial cross-frame continuity gates.
- [x] Map evidence to `auto_accept`, `request_confirmation`, or `keep_original`; failed or incomplete studies cannot auto-apply.
- [x] Test deterministic output, cache reuse, disconnected plateaus, and each decision outcome.

### Task 5: AI entry integration

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_ai_rescue.py`
- Modify: `polynexus/gui/main_window_ai_tuning_mixin.py`
- Modify: `polynexus/gui/main_window.py`
- Modify: `polynexus/gui/i18n.py`
- Modify: `tests/test_ai_preprocessing_mainline.py`

- [x] Convert the bounded AI candidate into a `StabilityStudyRequest` in strict mode, without changing the existing candidate-only contract.
- [x] Run the study through the real rerun/evidence adapter and attach the report to the existing preprocessing decision payload.
- [x] Route confirmation and auto-accept only through `PreprocessTransactionService`; preserve hash checks and rollback.
- [x] Show plateau/bootstrap/continuity evidence in the existing candidate review surface.
- [x] Test the one-button route and verify no direct config mutation occurs before confirmation.

### Task 6: Verification and checkpoint

**Files:**
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md`
- Modify: `docs/agent/tasks/2026-08-05-saxs-stability-map-scientific-correctness.md`

- [x] Run focused red/green matrices and the complete SAXS matrix (focused
  green; complete matrix recorded with 14 real-data/legacy-contract failures).
- [x] Run `python scripts/verify.py --task docs/agent/tasks/2026-08-05-saxs-stability-map-scientific-correctness.md --changed --types`.
- [x] Review cumulative diff and record known limitations and human scientific-review requirements.
- [ ] Create the atomic checkpoint with `python scripts/auto_commit.py --message "feat(saxs): add stability map and scientific correctness guards" --files ...` using the explicit changed-file allowlist.
