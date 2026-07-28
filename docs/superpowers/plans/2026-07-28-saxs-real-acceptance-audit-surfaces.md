# Real SAXS Acceptance Audit Surface Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Verify final audit consistency across real SAXS parameters, Figure/Manifest documents, and quality export.

**Architecture:** A real-fixture regression replays each mode into an external pytest root, reads only generated JSON contracts, and compares the existing detached audit snapshots. No production code is changed unless the regression proves lifecycle staleness.

**Tech Stack:** Python, Pytest, SAXSEngine, Figure Manifest JSON, SAXS export bundle, strict JSON.

---

### Task 1: Add the real consistency regression

**Files:**
- Create: `tests/test_saxs_real_acceptance_audit_surfaces.py`

- [x] **Step 1: Define real fixture sources and mode IDs**

Resolve the existing Static EDF, temperature directory, and strain directory
under `测试数据/saxs`; skip an unavailable fixture without creating data.

- [x] **Step 2: Replay and compare contracts**

For each available mode, run `get_engine(...).run_pipeline()` into `tmp_path`,
assert strict-JSON final parameters, inspect each Figure Manifest document,
call `export_saxs_bundle()` into a second temporary directory, and compare the
exported audit and registered `quality_evidence.json` to the final parameter
audit.

- [x] **Step 3: Run the focused real test**

```powershell
python -m pytest -q tests/test_saxs_real_acceptance_audit_surfaces.py -vv --basetemp C:\Temp\PolyNexus_saxs_real_acceptance_audit_surfaces_redgreen
```

Expected: real available modes pass, or a failure identifies an actual
pre/post-validation audit inconsistency; unavailable fixtures are skipped.

### Task 2: Verify and checkpoint

**Files:**
- Modify: task card, acceptance record, and `active-work.md`.

- [x] **Step 1: Run structured verifier and diff check**

Record task/memory, Ruff, compile, type baseline, quality/preprocessing, and
whitespace results exactly.

- [x] **Step 2: Run test-storage dry-run**

Confirm the real output root is external and do not delete pre-existing
artifacts.

- [x] **Step 3: Create the explicit allowlist checkpoint**

Use `scripts/auto_commit.py` with exactly this task card's allowlist and no
push.
