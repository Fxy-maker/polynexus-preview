# SAXS Strain Feature Tracking Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a single continuously tracked lamellar peak authoritative for SAXS strain long period, feature-local orientation, directional diagnostics, figures, and GUI rows.

**Architecture:** Extend the existing `LongPeriodResult` and `StrainPointResult` evidence instead of adding GUI scientific logic. `analyze_strain_series()` performs the only total-profile analysis, passes its accepted q peak into anisotropy and sector diagnostics, and retains the `SAXSResult` for downstream reuse. Compatibility readers may accept legacy invariant aliases, while new strain output uses explicit invariant names.

**Tech Stack:** Python 3.14, NumPy, SciPy peak detection, pytest, PySide6 result DTOs, existing SAXS evidence contracts.

---

### Task 1: Lock the authoritative peak contract

**Files:**
- Create: `tests/test_saxs_strain_feature_tracking_closure.py`
- Modify: `polynexus/core/saxs_engine/core.py`
- Modify: `polynexus/core/saxs_engine/saxs_strain.py`

- [x] Write a failing synthetic two-peak test asserting that each point retains
  one `analysis_result`, a finite `q_peak_total_nm1`, and continuity from the
  previous accepted peak.
- [x] Run the exact test and confirm failure from missing result fields.
- [x] Add `q_peak_nm1` and selection evidence to `LongPeriodResult`; attach the
  authoritative `SAXSResult` and tracking fields to `StrainPointResult`.
- [x] Pass the previous accepted q into the next `analyze_single()` call and
  fail closed when a credible continuous candidate is unavailable.
- [x] Run the focused test and existing core/strain tests.

### Task 2: Share the tracked q with orientation and sectors

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_anisotropy.py`
- Modify: `polynexus/core/saxs_engine/saxs_strain.py`
- Test: `tests/test_saxs_strain_feature_tracking_closure.py`

- [x] Add a failing test where independent Bragg selection would choose a
  competing peak but the orientation evidence must use `q_peak_total_nm1`.
- [x] Add a keyword-only `q_target_nm1` input to `analyze_anisotropy()` and
  `herman_from_sector_data()`; use internal peak selection only when absent.
- [x] Derive meridional/equatorial q and L against the same accepted feature
  anchor and preserve unavailable values when sectors are missing.
- [x] Run anisotropy, sector, and tracking regressions.

### Task 3: Remove the second strain analysis chain

**Files:**
- Modify: `polynexus/core/saxs.py`
- Test: `tests/test_saxs_strain_feature_tracking_closure.py`
- Test: `tests/test_saxs_batch_parameters.py`

- [x] Add a failing engine test asserting one `analyze_single()` call per frame
  and equality between GUI row `L_nm` and series `L_array`.
- [x] Reuse each point's authoritative `analysis_result` in
  `_run_strain_pipeline()` and remove the second per-frame analysis call.
- [x] Supply `frame_source_indices=range(frame_count)` to the strain series.
- [x] Project total and sector q/L plus tracking status into `_batch_data`.
- [x] Run focused engine and transport tests.

### Task 4: Correct invariant names and detector preview scaling

**Files:**
- Modify: `polynexus/core/saxs.py`
- Modify: `polynexus/core/saxs_engine/figure_strain.py`
- Modify: `polynexus/gui/result_table_templates.py`
- Test: `tests/test_saxs_strain_feature_tracking_closure.py`
- Test: `tests/test_saxs_results_table_service.py`

- [x] Add failing output tests requiring `invariant_Q`/`invariant_Q_rel` and
  rejecting reciprocal-length labeling for the invariant.
- [x] Emit explicit invariant fields from the series-owned value and update
  strain figures/tables to consume them.
- [x] Add a preview test proving nonpositive log sentinels do not determine
  detector heatmap display limits, then implement finite percentile bounds.
- [x] Run figure, table, and output tests.

### Task 5: Verify EDF 8 and create the checkpoint

**Files:**
- Test: `tests/test_saxs_strain_feature_tracking_closure.py`
- Modify: `docs/agent/tasks/2026-08-06-saxs-strain-feature-tracking-closure.md`
- Modify: `docs/agent/memory/current-state.md`
- Create: `docs/acceptance/2026-08-06-saxs-strain-feature-tracking-closure.md`

- [x] Add a read-only external-data test that explicitly skips when
  `Desktop/edf/8` is absent and otherwise checks shared feature q, valid source
  indices, and core/GUI L equality.
- [x] Run the focused matrix and record exact outcomes.
- [x] Run the structured verifier and `git diff --check`.
- [x] Review the cumulative explicit allowlist and create one local checkpoint
  with `scripts/auto_commit.py`; do not push or merge.

## Plan self-review

- Every acceptance criterion maps to a task and a failing test before code.
- Field names are consistent across core, engine rows, figures, and tables.
- No placeholder, inferred physical axis, or unrelated refactor is included.
