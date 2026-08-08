# SAXS Tensile-Aligned Peak Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Track lamellar q/L peaks in tensile-axis-aligned and transverse sectors without replacing the total-profile feature.

**Architecture:** Add a small core helper that creates support-aware radial profiles from canonical 2D sector data and reuse the existing bounded Bragg tracker. Transport new per-frame fields through `StrainPointResult` and SAXS batch rows; keep GUI presentation diagnostic-only.

**Tech Stack:** Python, NumPy, SciPy, PySide6 result-table DTOs, pytest.

---

### Task 1: Lock the directional contract with a failing test

**Files:**
- Modify: `tests/test_saxs_batch_parameters.py`
- Modify: `tests/test_saxs_results_table_service.py`

- [x] Add a canonical 2D synthetic frame whose q peak at the configured tensile axis differs from the transverse q peak; assert `q_peak_tensile_nm1`, `L_tensile_nm`, `q_peak_transverse_nm1`, and `L_transverse_nm` are distinct and that total q remains unchanged.
- [x] Assert a frame without `tensile_axis_deg` publishes no aligned peak as a formal value.
- [x] Assert the new scalar fields appear in Diagnostics, not the existing primary tuple.
- [x] Run the focused tests and observe the expected missing-field failure.

### Task 2: Implement support-aware tensile/transverse peak extraction

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_strain.py`

- [x] Add a helper using pi-periodic detector-sector semantics and support/azimuth-overlap-weighted q averaging for a sector centered at an arbitrary detector angle.
- [x] Call the helper only for canonical `I_2d/q_2d/chi_rad/support_count` payloads and finite `tensile_axis_deg`; use the existing relative-step bound anchored to total q.
- [x] Add explicit unavailable/reason fields for missing axis, malformed support, or missing canonical 2D data.
- [x] Keep fixed detector meridional/equatorial fields and total-profile tracking unchanged; reuse them when their configured sector exactly matches the requested axis.

### Task 3: Transport and present evidence

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_strain.py`
- Modify: `polynexus/core/saxs.py`
- Modify: `polynexus/gui/saxs_results_table_service.py`

- [x] Add typed/defaulted per-frame fields and rounded batch DTO values.
- [x] Add new names to the diagnostics-key allowlist; do not expand the primary table contract.
- [x] Preserve JSON-safe values and source/status metadata.

### Task 4: Verify and checkpoint

**Files:**
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md`
- Create: `docs/agent/tasks/2026-08-08-saxs-tensile-aligned-peak-tracking.md`

- [x] Run focused SAXS strain/result-table tests.
- [x] Run `python scripts/verify.py --changed --types` and `git diff --check`.
- [x] Commit only the explicit task allowlist with `scripts/auto_commit.py`; do not push or merge.
