# SAXS strain-axis fail-closed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve SAXS strain frames and downgrade malformed or empty strain
axes instead of aborting analysis.

**Architecture:** Keep profile analysis and existing phase classification intact.
Normalize only the condition axis, reuse the shared series condition-axis
evidence builder, and guard the reference calculation when there are no
frames.

**Tech Stack:** Python, NumPy, Pytest, SAXS quality contracts, Ruff, and the
structured repository verifier.

---

### Task 1: Capture malformed and empty axes with RED

**Files:**
- Create: `tests/test_saxs_strain_axis_fail_closed.py`

- [ ] **Step 1: Write the failing tests**

Use valid q/I profiles and a fake per-frame analysis result. Assert that
`["0", "bad", np.inf]` retains three points, leaves the latter two axis
values as `NaN`, and records `series_metric_condition_axis_invalid`; assert an
empty input returns no points and `series_no_frames` evidence.

- [ ] **Step 2: Run RED**

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_strain_axis_red'
python -m pytest -q tests/test_saxs_strain_axis_fail_closed.py
```

Expected: malformed input fails during the current `dtype=float` conversion
and the empty input fails at the current `sanitized_profiles[0]` access.

### Task 2: Implement conservative strain-axis handling

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_strain.py` in
  `analyze_strain_series()`.

- [ ] **Step 1: Normalize values without changing frame order**

Convert each item through a finite-float helper, returning `np.nan` on
`TypeError`, `ValueError`, or non-finite results. Keep the resulting array the
same length as `strains`.

- [ ] **Step 2: Guard empty reference handling and phase boundaries**

Set the reference invariant to `NaN` when there are no profiles. Only record a
phase boundary when the current strain is finite; do not invent a substitute
coordinate or remove the point.

- [ ] **Step 3: Bind existing condition-axis evidence**

Pass `frame_source_indices` only if an existing source mapping is available,
and pass `condition_name="strain_pct"` plus the normalized `result.strains`
to `build_series_metric_evidence()`.

- [ ] **Step 4: Run GREEN**

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_strain_axis_focus'
python -m pytest -q tests/test_saxs_strain_axis_fail_closed.py tests/test_saxs_strain_dirty_frame_postprocessing.py tests/test_saxs_1d_quality_provenance.py tests/test_saxs_2d_evidence_propagation.py
```

Expected: all focused strain tests pass.

### Task 3: Verify and checkpoint

- [x] **Step 1: Run exact SAXS matrix and structured verifier**

Use the task card commands and record fresh counts, warnings, quality and
preprocessing gates, and any timeout as a limitation rather than a pass.

- [x] **Step 2: Run `git diff --check` and storage report**

Confirm no whitespace errors. Run `python scripts/test_storage.py report --json`
in dry-run mode; do not delete or move any pre-existing artifacts.

- [x] **Step 3: Create the explicit allowlist checkpoint**

```powershell
python scripts/auto_commit.py --message "fix(saxs): fail closed on invalid strain axes" --files polynexus/core/saxs_engine/saxs_strain.py tests/test_saxs_strain_axis_fail_closed.py docs/agent/tasks/2026-07-28-saxs-strain-axis-fail-closed.md docs/superpowers/specs/2026-07-28-saxs-strain-axis-fail-closed-design.md docs/superpowers/plans/2026-07-28-saxs-strain-axis-fail-closed.md
```

Do not include concurrent memory, GUI, runtime, generated, or scratch files.
