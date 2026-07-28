# SAXS Strain Dirty-Frame Post-Processing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reuse the deterministic q/I sanitizer for strain-series 1D post-processing while retaining raw-frame provenance.

**Architecture:** `analyze_strain_series()` keeps original q/I for `analyze_single()` and creates a detached sanitized profile for only reference/per-frame invariant, phase detection, and void detection. The existing 2D sector/Herman path and all physical thresholds remain unchanged.

**Tech Stack:** Python, NumPy, pytest, SAXS quality contracts, repository verifier.

---

### Task 1: Establish the dirty-frame regression

**Files:**

- Create: `tests/test_saxs_strain_dirty_frame_postprocessing.py`
- Read: `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- Read: `polynexus/core/saxs_engine/saxs_strain.py`

- [x] **Step 1: Write the failing test.** Construct two strain frames with `q=[0.04, nan, 0.02, 0.03]` and `I=[4.0, 5.0, -1.0, 3.0]`. Monkeypatch `analyze_single()` to build the existing quality report from the original arrays, and monkeypatch invariant, phase, and void helpers to assert finite positive sorted q/I before returning existing-shaped values. Record the original arrays separately and assert `invalid_pairs_dropped`/`q_sorted` remain in the frame report.

- [x] **Step 2: Run the RED test.**

Run:

```powershell
python -m pytest tests/test_saxs_strain_dirty_frame_postprocessing.py::test_strain_postprocessing_uses_sanitized_profile_and_keeps_quality_actions -q
```

Expected: FAIL because `analyze_strain_series()` currently passes raw q/I to the reference/frame invariant, phase, and void helpers.

### Task 2: Route the existing sanitizer through strain 1D consumers

**Files:**

- Modify: `polynexus/core/saxs_engine/saxs_strain.py`
- Test: `tests/test_saxs_strain_dirty_frame_postprocessing.py`

- [x] **Step 1: Import the existing contract.** Add `sanitize_1d_profile` to the existing quality-contract import; do not create a second sanitizer.

- [x] **Step 2: Build detached profiles after length validation.** Add:

```python
sanitized_profiles = [
    sanitize_1d_profile(q_values, intensity_values)
    for q_values, intensity_values in zip(q_list, I_list)
]
reference_profile = sanitized_profiles[0]
Q_ref = scattering_invariant(
    reference_profile.q,
    reference_profile.intensity,
    cfg=cfg,
)
```

- [x] **Step 3: Route the four existing consumers.** Keep `q`/`I` for `analyze_single()`, set `profile = sanitized_profiles[i]`, and pass `profile.q`/`profile.intensity` to `scattering_invariant`, `detect_strain_phase`, and `detect_voids`. Do not change sector-data calls.

### Task 3: Verify empty and clean boundaries

**Files:**

- Test: `tests/test_saxs_strain_dirty_frame_postprocessing.py`

- [x] **Step 1: Add the empty-profile regression.** Supply an all-invalid frame, assert Q* is NaN/unavailable, no void value is fabricated, and the original quality actions remain visible.
- [x] **Step 2: Add clean/source alignment assertions.** Use unsorted strain values with clean profiles and assert the existing frame order and source indices remain unchanged.
- [x] **Step 3: Run the focused GREEN matrix.** Run the new file together with existing strain evidence and method evidence tests; expected output is zero failures with only existing warnings.

### Task 4: Full verification and checkpoint

**Files:**

- Update: task card, spec, plan, `docs/agent/memory/active-work.md`, and `docs/agent/memory/current-state.md`.

- [x] **Step 1: Run the focused and exact SAXS matrices with an isolated writable basetemp.** Record exact counts and warnings: focused `9 passed, 1 warning`; exact SAXS `428 passed, 8 warnings`.
- [x] **Step 2: Run the task-scoped verifier and `git diff --check`.** Record task/memory, Ruff, compile, type baseline, quality `283`, preprocessing `106`, and whitespace outcomes; all passed.
- [x] **Step 3: Run fresh `--full --boundary`.** The fresh D:-isolated verifier returned `2869 passed, 17 skipped, 12 warnings` in `1686.81s`, exit code `0`; boundary audit passed.
- [x] **Step 4: Review cumulative diff and create one `scripts/auto_commit.py` checkpoint using only the explicit allowlist.** Leave parallel GUI/Joint/editor/scratch files untouched; the allowlisted checkpoint is created for this task.

## Self-review

- Every acceptance criterion maps to a focused test or existing contract.
- No new scientific threshold, interpolation, q aggregation, or rescue action
  is introduced.
- The plan leaves the 2D sector/Herman path separate from the 1D sanitizer.
- Missing or empty observations remain visible and unavailable rather than
  being inferred from neighboring strain frames.
