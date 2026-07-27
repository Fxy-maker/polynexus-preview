# SAXS EDF Herman Orientation Source Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate valid azimuthal evidence from EDF frames so existing strain Herman transport produces numeric orientation factors.

**Architecture:** The preprocessing layer creates a canonical `I_2d/q_2d/chi_rad` payload for anisotropic images, using pyFAI when available and a bounded NumPy geometry fallback otherwise. The strain layer delegates that payload to the existing `analyze_anisotropy()` algorithm and leaves the established result-table transport unchanged.

**Tech Stack:** Python, NumPy, SciPy, pytest, existing SAXS geometry and result contracts.

---

## File map

- Create: `docs/superpowers/specs/2026-07-27-saxs-edf-herman-source-design.md`
- Create: `docs/agent/tasks/2026-07-27-saxs-edf-herman-source.md`
- Modify: `polynexus/core/saxs_engine/preprocess.py`
  - Add a manual azimuthal-bin fallback and attach canonical 2D payload data.
- Modify: `polynexus/core/saxs_engine/saxs_strain.py`
  - Consume canonical 2D payloads through `analyze_anisotropy()`.
- Modify: `tests/test_saxs_preprocess.py`
  - Verify manual 2D integration and canonical payload shape.
- Modify: `tests/test_saxs_batch_parameters.py`
  - Verify finite Herman output from the canonical payload and preserve
    unavailable behavior.

## Task 1: Write the failing preprocessing contract

**Files:** `tests/test_saxs_preprocess.py`

- [x] Add a test with a small synthetic image and valid manual geometry that
  monkeypatches `build_integrator` to `None`, runs `preprocess_pipeline()`, and
  asserts `sector_data` contains `I_2d`, `q_2d`, and `chi_rad` with matching
  dimensions and at least eight azimuth bins.
- [x] Run the test and confirm it fails because the current payload has only
  `q/I_full/I_merid/I_equat` and no canonical 2D arrays.

## Task 2: Implement the minimal 2D source path

**Files:** `polynexus/core/saxs_engine/preprocess.py`

- [x] Add a manual branch to `integrate_chi_sectors()` that computes pixel
  `q_map` and `chi_rad`, bins valid positive pixels into `n_chi_sectors × n_pt`
  mean intensities, and returns `(q_centers, intensity_2d, chi_centers)`.
- [x] Keep pyFAI's existing `integrate2d()` path unchanged, converting its
  azimuth axis to radians when it is reported in degrees.
- [x] In `preprocess_pipeline()`, for non-isotropic input, call the helper and
  attach the canonical arrays. Catch a failed 2D branch as unavailable without
  failing the existing radial analysis.

## Task 3: Write and verify the failing Herman consumer regression

**Files:** `tests/test_saxs_batch_parameters.py`

- [x] Add a test that builds a canonical payload from a synthetic azimuthal
  intensity pattern, passes it in `sector_data_list` to `analyze_strain_series`,
  and asserts a finite `f_herman`.
- [x] Run the new test before the consumer change and confirm the current
  `herman_from_sector_data()` returns non-finite for this canonical payload.

## Task 4: Connect the existing anisotropy algorithm

**Files:** `polynexus/core/saxs_engine/saxs_strain.py`

- [x] In `herman_from_sector_data()`, detect canonical `I_2d/q_2d/chi_rad`
  payloads and call `analyze_anisotropy()` with the existing radial profile.
- [x] Return the algorithm's finite `f_herman`, `f_herman_sub`, and
  `f_herman_eq` values in the same dictionary consumed by
  `analyze_strain_series()`.
- [x] Preserve legacy nested-sector handling and return non-finite values for
  malformed or insufficient payloads.

## Task 5: Verify end to end

**Files:** task card and plan only

- [x] Run the focused preprocessing/strain/table matrix with an isolated
  basetemp.
- [x] Run the full SAXS matrix and record its exact result.
- [x] Run `python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-edf-herman-source.md --changed --types` with an isolated basetemp.
- [x] Review cumulative diff and create one `scripts/auto_commit.py` checkpoint
  with the explicit allowlist in the task card. Do not include parallel memory
  edits or temporary directories.

## Verification evidence

- Focused matrix: `82 passed`.
- Complete SAXS matrix: `344 passed, 4 warnings`.
- Structured verifier: quality `282`, preprocessing `106`, Ruff, compile/type,
  task/memory, and whitespace checks passed.
