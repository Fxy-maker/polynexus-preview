# SAXS Herman Confidence Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a conservative SAXS Herman reliability gate that separates raw diagnostic values from effective table values.

**Architecture:** The anisotropy core computes raw Herman/axis diagnostics and decides whether the azimuthal evidence is usable. The strain adapter applies aligned 1D hard blockers and transports both raw and effective values. Existing evidence contracts carry the reasons; GUI consumers remain unchanged.

**Tech Stack:** Python dataclasses, NumPy/SciPy, existing SAXS quality contracts, pytest, `scripts/verify.py`, and `scripts/auto_commit.py`.

---

### Task 1: Add the confidence-gate contract and thresholds

**Files:**
- Modify: `polynexus/core/saxs_engine/config.py`
- Modify: `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- Test: `tests/test_saxs_2d_detector_orientation_evidence.py`

- [ ] **Step 1: Write failing contract tests.**

Add assertions that orientation evidence preserves `f_herman_raw`, records
`orientation_reliability_status` and reason codes, and remains strict JSON safe.
Use an accepted synthetic payload and a blocked payload with
`orientation_reliability_status="blocked"`.

- [ ] **Step 2: Run the focused tests and confirm the new assertions fail.**

Run:

```powershell
python -m pytest tests/test_saxs_2d_detector_orientation_evidence.py -q
```

Expected: failure because the evidence builder does not yet preserve the raw
field or reliability status.

- [ ] **Step 3: Add explicit configuration fields.**

Add finite defaults to `SAXSConfig`:

```python
        orientation_auto_min_significance: float = 2.0
orientation_min_coverage: float = 0.75
orientation_min_effective_bins: float = 8.0
orientation_max_axis_drift_deg: float = 20.0
```

Extend `build_orientation_evidence()` to preserve raw Herman and gate
diagnostics in `fit_evidence`/`physical_checks`; a blocked status must make the
metric non-applicable without deleting raw evidence.

- [ ] **Step 4: Run the focused tests to confirm the contract is green.**

Run the command from Step 2 and expect all tests to pass.

### Task 2: Implement azimuthal significance and stability diagnostics

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_anisotropy.py`
- Test: `tests/test_saxs_2d_detector_orientation_evidence.py`

- [ ] **Step 1: Write failing profile tests.**

Add tests for:

```python
def test_weak_noisy_profile_keeps_raw_but_blocks_effective_herman(): ...
def test_incomplete_azimuthal_coverage_blocks_effective_herman(): ...
def test_stable_synthetic_ring_keeps_effective_herman(): ...
```

The tests must assert that a strong synthetic ring has finite
`f_herman`/`f_herman_raw`, while weak or incomplete profiles have finite raw
evidence, `NaN` effective `f_herman`, and an explicit reason code.

- [ ] **Step 2: Run the profile tests and confirm the expected failures.**

Run:

```powershell
python -m pytest tests/test_saxs_2d_detector_orientation_evidence.py -q
```

- [ ] **Step 3: Implement the minimal diagnostics.**

Extend the existing second-harmonic result with effective weighted-bin count,
circular coverage, significance `strength * sqrt(effective_bins)`, and the
modulo-180 degree axis drift between even and odd profile bins. Keep the
existing 180-degree axis calculation and 2D Herman formula unchanged.

Store the calculated value in `f_herman_raw`. Set `f_herman` only when all
configured profile gates pass; otherwise leave it `NaN`, set the reliability
status to `blocked`, and attach reason codes. Explicit configured axes bypass
axis selection only; they do not bypass profile validity gates.

- [ ] **Step 4: Run the profile tests and confirm they pass.**

Run the command from Step 2 and expect all orientation tests to pass.

### Task 3: Apply 1D hard quality blockers in strain transport

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_strain.py`
- Test: `tests/test_saxs_batch_parameters.py`

- [ ] **Step 1: Write a failing strain transport regression.**

Construct a canonical `I_2d/q_2d/chi_rad` payload with a finite raw Herman
value and an aligned `data_quality_report` containing
`low_q_truncated=True` and `actions=["invalid_pairs_dropped"]`. Assert that
the resulting point has `f_herman_raw` finite, `f_herman` unavailable, and
orientation evidence includes the blocker reasons.

- [ ] **Step 2: Run the regression and confirm it fails.**

Run:

```powershell
python -m pytest tests/test_saxs_batch_parameters.py -q
```

- [ ] **Step 3: Add raw/effective transport.**

Add `f_herman_raw` to `StrainPointResult`, return it from the canonical
`herman_from_sector_data()` path, and apply the 1D quality blocker before
assigning the effective value and `f_herman_array`. Keep the raw value in the
orientation evidence payload; do not add a GUI-specific branch.

- [ ] **Step 4: Run the strain regression and full focused pair.**

Run:

```powershell
python -m pytest tests/test_saxs_2d_detector_orientation_evidence.py tests/test_saxs_batch_parameters.py -q
```

Expected: all tests pass.

### Task 4: Verify, review, and checkpoint

**Files:**
- Review: all files in the task-card allowlist

- [ ] **Step 1: Run the complete SAXS matrix.**

```powershell
python -m pytest (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q
```

- [ ] **Step 2: Run the structured verifier.**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-herman-confidence-gate.md --changed --types
```

- [ ] **Step 3: Review the cumulative diff and create one checkpoint.**

```powershell
python scripts/auto_commit.py --message "fix(saxs): gate unreliable Herman orientation values" --files polynexus/core/saxs_engine/config.py polynexus/core/saxs_engine/saxs_anisotropy.py polynexus/core/saxs_engine/saxs_quality_contracts.py polynexus/core/saxs_engine/saxs_strain.py tests/test_saxs_2d_detector_orientation_evidence.py tests/test_saxs_batch_parameters.py docs/superpowers/specs/2026-07-31-saxs-herman-confidence-gate-design.md docs/superpowers/plans/2026-07-31-saxs-herman-confidence-gate.md docs/agent/tasks/2026-07-31-saxs-herman-confidence-gate.md
```

Expected: one atomic commit containing only the explicit allowlist; parallel
memory, advisor, test-storage, and unrelated worktree changes remain unstaged.
