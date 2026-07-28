# SAXS strain sector fail-closed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert malformed optional strain sector data into explicit Unusable
orientation evidence without aborting the strain series.

**Architecture:** Keep the existing `herman_from_sector_data()` public shape
and legacy scalar fields. Add a private invalid-payload path backed by the
shared detector/orientation evidence builders, then attach its detached fields
to the current `StrainPointResult`.

**Tech Stack:** Python, NumPy, Pytest, PySide-free SAXS core contracts, Ruff,
and `scripts/verify.py`.

---

### Task 1: Add RED regressions

**Files:**
- Create: `tests/test_saxs_strain_sector_fail_closed.py`

- [x] **Step 1: Write tests**

Call `herman_from_sector_data({"meridional": None})` and assert it returns an
Unusable orientation payload with `strain_sector_data_invalid`; run the same
payload through `analyze_strain_series()` and assert the frame remains.

- [x] **Step 2: Run RED**

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_strain_sector_red'
python -m pytest -q tests/test_saxs_strain_sector_fail_closed.py
```

Expected: the current fallback raises `AttributeError` on `mer_data.get()`.

### Task 2: Implement the minimal evidence downgrade

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_strain.py`.

- [x] **Step 1: Build invalid sector evidence from existing contracts**

Use `build_detector_quality_report(np.empty((0, 0)), source_kind="sector_map")`
and `build_orientation_evidence({}, detector, applicability="supported")`,
then append the deterministic input-validation reason without mutating the
returned contract.

- [x] **Step 2: Validate nested mappings and guard the series call**

Return the invalid payload when the outer/nested structure is malformed. Keep
the existing valid canonical and sector integration paths unchanged, and use
the invalid payload in the series consumer's exception boundary.

- [x] **Step 3: Run GREEN**

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_strain_sector_focus'
python -m pytest -q tests/test_saxs_strain_sector_fail_closed.py tests/test_saxs_strain_axis_fail_closed.py tests/test_saxs_2d_detector_orientation_evidence.py tests/test_saxs_2d_evidence_propagation.py tests/test_saxs_batch_parameters.py
```

Expected: all focused tests pass.

### Task 3: Verify and checkpoint

- [x] **Step 1: Run structured verification and diff check**

Run the task verifier and `git diff --check`, recording exact quality and
preprocessing gate counts.

- [x] **Step 2: Run storage dry-run**

Run `python scripts/test_storage.py report --json`; do not delete or move
pre-existing artifacts.

- [x] **Step 3: Create the explicit allowlist checkpoint**

```powershell
python scripts/auto_commit.py --message "fix(saxs): degrade malformed strain sector data" --files polynexus/core/saxs_engine/saxs_strain.py tests/test_saxs_strain_sector_fail_closed.py docs/agent/tasks/2026-07-28-saxs-strain-sector-fail-closed.md docs/superpowers/specs/2026-07-28-saxs-strain-sector-fail-closed-design.md docs/superpowers/plans/2026-07-28-saxs-strain-sector-fail-closed.md
```

Do not include memory, GUI, NMR, Joint, generated, or scratch files.
