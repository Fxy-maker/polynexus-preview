# SAXS export dirty-profile guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep SAXS profile bundle export usable and diagnostic when q/I tokens
are malformed after canonical projection.

**Architecture:** `_profile_items()` will prefer the existing canonical profile
q array. `_write_profiles()` will use the shared elementwise coercion helper for
the fallback path, while retaining its current CSV schema and provenance
payload.

**Tech Stack:** Python, NumPy, CSV/JSON export, pytest, repository verifier.

---

### Task 1: Add the failing export regression

**Files:**
- Modify: `tests/test_saxs_export_bundle.py`

- [ ] **Step 1: Build a dirty canonical profile fixture.**

Create an engine with object q/I lists containing malformed tokens and a
`ProcessedProfile` containing the same positions as `NaN`. Assert export keeps
the caller-owned arrays unchanged.

- [ ] **Step 2: Run RED.**

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_export_dirty_profile_red'
python -m pytest -q tests/test_saxs_export_bundle.py -k dirty_profile_export
```

Expected before implementation: export returns `failed` because `_write_profiles`
performs whole-array float conversion on the dirty q list.

### Task 2: Use canonical projection and elementwise fallback at export

**Files:**
- Modify: `polynexus/core/saxs_export_bundle.py`

- [ ] **Step 1: Prefer canonical q.**

When a processed profile is present, use its read-only q array for the profile
item instead of the parallel raw q list.

- [ ] **Step 2: Harden fallback conversion.**

Use `_coerce_numeric_array()` for q and all profile layers before writing CSV;
retain the current row-index alignment and empty-cell representation.

- [ ] **Step 3: Run GREEN.**

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_export_dirty_profile_green'
python -m pytest -q tests/test_saxs_export_bundle.py -k dirty_profile_export
```

### Task 3: Verify and checkpoint

**Files:**
- Modify: `polynexus/core/saxs_export_bundle.py`
- Modify: `tests/test_saxs_export_bundle.py`
- Add: task/spec/plan/acceptance and `docs/agent/memory/active-work.md`

- [ ] Run the export consumer matrix, exact SAXS matrix, structured verifier,
  and `git diff --check` with external basetemps.
- [ ] Record exact results and the bounded/full limitation honestly.
- [ ] Create one `auto_commit.py` checkpoint with only the explicit allowlist.
