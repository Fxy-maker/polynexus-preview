# SAXS Real 2D Evidence Transport Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve the existing sector-map detector report through real SAXS
strain point and series results.

**Architecture:** Reuse the detector report created by
`analyze_anisotropy`; return it from the existing sector-data adapter and copy
it into `StrainPointResult` before the existing series rollup. No new contract,
threshold, or 2D calculation is introduced.

**Tech Stack:** Python dataclasses, NumPy, Pytest, existing SAXS evidence and
series aggregation helpers.

---

### Task 1: Lock the real sector-map transport boundary with RED tests

**Files:**
- Modify: `tests/test_saxs_2d_evidence_propagation.py`

- [x] Add a real-code regression using a finite sector map and assert that
  `analyze_strain_series` exposes a `sector_map` detector report on each point
  and on the series summary, with `json.dumps(..., allow_nan=False)` succeeding.
- [x] Run the focused regression and confirm it fails because the helper does
  not currently return the detector report and the point remains `None`.

Run:

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=C:\Temp\PolyNexus_saxs_real_2d_transport_red'
python -m pytest tests/test_saxs_2d_evidence_propagation.py -q
```

Expected RED: the new sector-map transport assertion fails with a missing
`detector_quality_report`; existing propagation tests remain green.

### Task 2: Implement the minimal transport fix

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_strain.py`

- [x] In the canonical `I_2d` branch of `herman_from_sector_data`, include
  `orientation.detector_quality_report` in the returned mapping.
- [x] In `analyze_strain_series`, copy that mapping into
  `sp.detector_quality_report` before the existing series aggregation.
- [x] Leave the absent-sector and exception paths unchanged so no 2D evidence
  is fabricated.

The minimal implementation shape is:

```python
return {
    # existing Herman/orientation fields...
    "detector_quality_report": getattr(
        orientation, "detector_quality_report", None
    ),
}
```

and, after the existing orientation assignment:

```python
if herman.get("detector_quality_report") is not None:
    sp.detector_quality_report = herman["detector_quality_report"]
```

### Task 3: Verify the GREEN slice and consumers

**Files:**
- Test: `tests/test_saxs_2d_evidence_propagation.py`
- Verify: existing SAXS consumers and task verifier

- [x] Run the focused propagation matrix and confirm all tests pass.
- [x] Run the exact `tests/test_saxs_*.py` matrix with an external basetemp.
- [x] Run the structured task verifier, `git diff --check`, and record exact
  counts plus any existing warnings.
- [x] Replay the real PAD8 strain directory to an external output root and
  confirm the result now contains a non-null sector-map detector summary while
  geometry/saturation/mask provenance remains conservative.

### Task 4: Checkpoint only the explicit allowlist

**Files:**
- Modify: `docs/agent/tasks/2026-07-27-saxs-real-2d-evidence-transport.md`
- Modify: `docs/superpowers/specs/2026-07-27-saxs-real-2d-evidence-transport-design.md`
- Modify: `docs/superpowers/plans/2026-07-27-saxs-real-2d-evidence-transport.md`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md`
- Modify: `polynexus/core/saxs_engine/saxs_strain.py`
- Modify: `tests/test_saxs_2d_evidence_propagation.py`

- [x] Review the cumulative diff for the seven-file allowlist.
- [x] Use `scripts/auto_commit.py`; do not stage untracked pytest directories,
  GUI/editor drafts, `tests/_tmp_phase3/`, or parallel task files.

## Verification result (2026-07-27)

- RED: `1 failed, 11 passed`; GREEN focused propagation: `12 passed`.
- Exact SAXS matrix: `365 passed, 4 warnings in 29.96s`.
- Structured verifier: exit 0; quality `283 passed`, preprocessing `106
  passed`, task/memory/Ruff/compile/type/whitespace passed.
- Real PAD8 replay: five frame and one series detector reports transported as
  `sector_map`; the series remains `Unusable` with explicit missing saturation,
  beam-center, and nonpositive-pixel reasons.
- The final checkbox is intentionally pending until the explicit allowlist
  checkpoint is created.

## Known limitations after this slice

The resulting report still describes a `sector_map`, not raw detector quality.
Real mask propagation, detector calibration validity, and human scientific
interpretation remain separate acceptance gates.
