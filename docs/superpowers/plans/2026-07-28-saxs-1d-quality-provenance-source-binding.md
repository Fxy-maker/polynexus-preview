# SAXS 1D quality provenance source binding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bind available SAXS 1D quality reports to their original frame/file across static, temperature, and strain paths without changing analysis semantics.

**Architecture:** Keep provenance in the existing `DataQualityReport`. Add optional source arguments at the single-profile boundary, optional aligned source sequences at the two series boundaries, and derive the high-level engine's mappings from `_file_list`. Existing report-copy and figure/export projections remain the only consumer path.

**Tech Stack:** Python, NumPy, dataclasses, Pytest, existing SAXS DTOs, Ruff, and the repository verifier.

---

### Task 1: Lock the source-binding contract with RED tests

**Files:**
- Create: `tests/test_saxs_1d_quality_provenance.py`
- Modify: `tests/test_saxs_temperature_status.py` (compatibility-only test-double signature)

- [x] **Step 1: Write failing tests**

Add tests that assert direct `analyze_single(..., source_id="frame-4", raw_data_ref="raw/frame-4.edf")` stores both values, that temperature preserves `source_index` and report source after sorting, that strain binds positional sources, and that omitted/mismatched source lists leave report provenance empty. Add one high-level static-batch test that passes `_file_list` and observes the report source.

- [x] **Step 2: Run the RED command**

Run:

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=C:\Temp\PolyNexus_saxs_provenance_red'
python -m pytest -q tests/test_saxs_1d_quality_provenance.py
```

Expected: collection succeeds and the new source-binding assertions fail because `analyze_single()` and series APIs do not yet accept or forward source metadata.

### Task 2: Add provenance at the analysis boundaries

**Files:**
- Modify: `polynexus/core/saxs_engine/core.py`
- Modify: `polynexus/core/saxs_engine/saxs_temperature.py`
- Modify: `polynexus/core/saxs_engine/saxs_strain.py`

- [x] **Step 1: Add optional direct source arguments**

Extend `analyze_single()` with keyword-only `source_id` and `raw_data_ref` arguments and pass them to the existing `build_data_quality_report()` call. Do not alter sanitization or any numeric method.

- [x] **Step 2: Add aligned source sequences to temperature and strain**

Add optional `source_ids` and `raw_data_refs` arguments. Accept a sequence only when its length equals the frame count. Temperature uses each sorted frame's original index when constructing the `analyze_single()` keyword arguments; strain uses its loop index. Leave absent or mismatched metadata empty.

- [x] **Step 3: Run focused GREEN tests**

Run:

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=C:\Temp\PolyNexus_saxs_provenance_focus'
python -m pytest -q tests/test_saxs_1d_quality_provenance.py tests/test_saxs_dirty_profile_sanitization.py tests/test_saxs_quality_contracts.py tests/test_saxs_temperature_guinier_evidence.py
```

Expected: all focused tests pass; existing tests that monkeypatch the analysis function must remain compatible when no source sequences are supplied.

### Task 3: Thread real engine file mappings and verify consumers

**Files:**
- Modify: `polynexus/core/saxs.py`
- Modify: `tests/test_saxs_1d_quality_provenance.py`
- Modify: `docs/agent/tasks/2026-07-28-saxs-1d-quality-provenance-source-binding.md`
- Modify: `docs/agent/memory/current-state.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] **Step 1: Add a small high-level source helper**

Derive `frame-{index}` plus the exact `_file_list[index]` only when a file path is present. Store the single-file load path separately so static single analysis can use the same contract. Pass the resulting source arrays through all static, temperature, and strain engine calls, including public series methods.

- [x] **Step 2: Run the exact SAXS matrix**

```powershell
$saxsTests = Get-ChildItem tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests --basetemp=C:\Temp\PolyNexus_saxs_provenance_matrix
```

Expected: zero failures; existing warnings may remain and must be reported.

- [x] **Step 3: Run structured verification and diff check**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-1d-quality-provenance-source-binding.md --changed --types
git diff --check
```

- [x] **Step 4: Create the explicit checkpoint**

After fresh verification, run `scripts/auto_commit.py` with exactly the task card's explicit allowlist. The checkpoint must not include pre-existing GUI/editor/release drafts, scratch directories, or unrelated parallel files.
