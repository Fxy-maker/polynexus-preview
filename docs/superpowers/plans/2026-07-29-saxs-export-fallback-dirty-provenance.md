# SAXS export fallback dirty-provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep legacy SAXS export fallback profiles diagnostically transparent
when q/I conversion fails at the CSV boundary.

**Architecture:** Extend the existing `_write_profiles()` export pass to retain
elementwise invalid counts from the shared coercion helper. Merge those counts
into a detached diagnostics mapping and return the adjusted profile provenance;
leave the CSV schema and analysis object untouched.

**Tech Stack:** Python, NumPy, CSV/JSON export, pytest, repository verifier.

---

### Task 1: Add the failing fallback regression

**Files:**
- Modify: `tests/test_saxs_export_bundle.py`

- [x] Add a legacy analysis fixture with dirty q/raw object arrays, no canonical
  profile, and a clean quality flag. Assert export succeeds but currently lacks
  the expected invalid-value diagnostics.
- [x] Run RED:

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_export_fallback_dirty_red'
python -m pytest -q tests/test_saxs_export_bundle.py -k fallback_dirty_provenance
```

### Task 2: Preserve fallback conversion provenance

**Files:**
- Modify: `polynexus/core/saxs_export_bundle.py`

- [x] Return per-item invalid counts from `_write_profiles()` while retaining
  existing profile files and row positions.
- [x] Merge counts into detached diagnostics and set fallback profile status to
  `WARN` only when conversion failures exist and the prior status is `OK` or
  `unknown`.
- [x] Run GREEN and the existing export/processed-profile consumer matrix.

### Task 3: Verify and checkpoint

**Files:**
- Modify: `polynexus/core/saxs_export_bundle.py`
- Modify: `tests/test_saxs_export_bundle.py`
- Add: task/spec/plan/acceptance and active-work evidence.

- [x] Run structured verification, `git diff --check`, and storage report-only
  dry-run.
- [x] Attempt the exact SAXS matrix with an external basetemp; record timeout
  or final summary honestly.
- [x] Create one explicit allowlist checkpoint with `auto_commit.py`.
