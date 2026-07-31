# SAXS Review Warning Reduction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the SAXS review surface reflect the confirmed strain filename axis and distinguish expected detector exclusions from actual defects.

**Architecture:** Keep the existing EDF-driven preprocessing and scientific gates. Narrow condition-pattern eligibility by experiment type, make raw-detector provenance statuses structural rather than calibration claims, and deduplicate only the presentation text.

**Tech Stack:** Python, NumPy, dataclasses, pytest, repository verifier.

---

### Task 1: Add RED tests for condition semantics

**Files:**
- Modify: `tests/test_saxs_condition_recovery.py`

- [x] Add a strain-mode path test for `610-005-S_0_00000.edf` asserting value `5.0`, source `path_filename`, and source key `strain_dash_S_suffix`.
- [x] Add a static-mode path test asserting the strain-only filename pattern is not selected.
- [x] Run `python -m pytest -q tests/test_saxs_condition_recovery.py -vv`; confirm the new strain precedence test fails because the directory pattern currently wins.

### Task 2: Add RED tests for raw report semantics

**Files:**
- Modify: `tests/test_saxs_edf_metadata_quality.py`
- Modify: `tests/test_saxs_raw_detector_quality_transport.py`

- [x] Add a test image containing only the declared floor plus a shape-matched configured mask and assert the raw counts remain while the report does not contain an unexpected nonpositive reason.
- [x] Add an assertion for a new unexpected-nonpositive count when a zero or non-floor negative is present.
- [x] Assert complete EDF provenance uses the new structural status and missing/invalid headers remain conservative.
- [x] Run `python -m pytest -q tests/test_saxs_edf_metadata_quality.py -vv`; confirm the new assertions fail before implementation.

### Task 3: Add RED test for audit deduplication

**Files:**
- Modify: `tests/test_saxs_workbench_detector_provenance_audit.py`

- [x] Supply four identical raw detector audit records and assert each presentation field contains one serialized audit detail.
- [x] Run the focused test and confirm it fails because the formatter currently joins all four records.

### Task 4: Implement the minimal production changes

**Files:**
- Modify: `polynexus/core/saxs_engine/config.py`
- Modify: `polynexus/core/saxs_engine/io.py`
- Modify: `polynexus/core/saxs_engine/preprocess.py`
- Modify: `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- Modify: `polynexus/gui/saxs_results_table_service.py`

- [x] Reorder strain filename precedence and scope strain/temperature pattern names to their matching experiment type in both condition parsing paths.
- [x] Add `unexpected_nonpositive_pixel_count`, keep raw nonpositive/floor/mask counts, and emit defect reasons only for unexpected values or invalid mask shape.
- [x] Add structural provenance statuses accepted by the audit without calling them physically calibrated; keep `Saturation=0` advisory and missing/invalid metadata conservative.
- [x] Deduplicate detector audit detail strings per output field without changing audit data contracts.
- [x] Run the focused tests and confirm the new behavior is green.

### Task 5: Verify and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-31-saxs-review-warning-reduction.md`

- [x] Run the focused SAXS tests from the task card.
- [x] Run `python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-review-warning-reduction.md --changed --types`.
- [x] Run `git diff --check` and review the allowlist-only diff.
- [x] Update the task card with exact command outcomes and create a local checkpoint using `scripts/auto_commit.py` with the explicit allowlist.
