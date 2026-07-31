# SAXS 2D Review Context Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Project existing SAXS 2D detector/orientation evidence and review state into one safe DTO consumed by the Results Workbench.

**Architecture:** Add a pure core adapter with fixed field allowlists and fail-closed status projection. Add a defaulted presentation field so existing GUI consumers remain source-compatible; the GUI does not inspect detector or orientation internals.

**Tech Stack:** Python 3.12, dataclasses, existing SAXS quality contracts, existing scientific-review helpers, pytest, repository verifier.

---

### Task 1: Define the failing core contract

**Files:**
- Create: `tests/test_saxs_2d_review_context.py`
- Create: `polynexus/core/saxs_engine/saxs_2d_review_context.py` only after RED is observed

- [x] **Step 1: Add complete-evidence RED coverage**

Build `DetectorQualityReport` and orientation `MetricEvidence` payloads from
existing dictionaries, attach an accepted `saxs.2d` review record, and assert
the returned DTO exposes only the documented summary fields.

- [x] **Step 2: Add degradation and security RED coverage**

Exercise missing detector/orientation fields, `not_assessed` provenance,
Diagnostic/Unusable levels, scope/source mismatch, raw q/I/pixel/path fields,
non-finite values, and input mutation. Assert `json.dumps(...,
allow_nan=False)` succeeds and no raw field survives.

- [x] **Step 3: Run RED and record the real failure**

Run:

```powershell
$env:POLYNEXUS_TEST_ROOT='C:\PolyNexus-test-runs-saxs-2d-context-red-20260731'
$env:POLYNEXUS_TEST_RETENTION='review'
python -m pytest -q tests/test_saxs_2d_review_context.py -o addopts=
```

Expected: collection fails because `build_saxs_2d_review_context` is not yet
available. Correct any test import error until the failure is the missing
contract, then retain the observed result in the task card.

### Task 2: Implement the pure DTO adapter

**Files:**
- Create: `polynexus/core/saxs_engine/saxs_2d_review_context.py`
- Modify: `polynexus/core/saxs_engine/__init__.py`

- [x] **Step 1: Implement detached JSON-safe projection**

Unwrap mappings, result wrappers, and parameters without reading raw arrays or
paths. Use fixed allowlists for detector, provenance, orientation, gate, and
review fields. Convert non-finite numeric values to `None`, omit unknown/raw
fields, and preserve missing evidence as explicit unavailable/not-assessed
states.

- [x] **Step 2: Reuse existing review validation**

Use `review_record_from_payload()` and `review_decision_snapshot()` for a
serialized or object review record. When only an existing decision snapshot is
available, project it without upgrading its status. Always use expected scope
`saxs.2d` and the supplied `source_ref`.

- [x] **Step 3: Export the helper**

Export `build_saxs_2d_review_context` from `polynexus.core.saxs_engine` and
keep the adapter free of GUI imports and analysis calls.

- [x] **Step 4: Run GREEN**

Run the same focused command from Task 1. Expected: all new tests pass with a
complete pytest summary and exit code `0`.

### Task 3: Bind the DTO to the Workbench presentation

**Files:**
- Modify: `polynexus/gui/result_table_models.py`
- Modify: `polynexus/gui/saxs_results_table_service.py`
- Modify: `tests/test_saxs_2d_review_context.py`

- [x] **Step 1: Add a defaulted presentation field**

Add `saxs_2d_review_context: dict[str, Any] = field(default_factory=dict)` at
the end of `ResultsTablePresentation`, preserving existing positional and
keyword construction.

- [x] **Step 2: Populate it from existing parameters**

Call the core adapter from `build_saxs_results_presentation()` with the
parameters mapping. Keep all existing text sections and table rows unchanged.

- [x] **Step 3: Add compatibility assertions**

Assert a 2D payload exposes the DTO, while a normal 1D or empty payload keeps
the field empty and existing risk/next text unchanged.

- [x] **Step 4: Run the Workbench-focused GREEN suite**

Run:

```powershell
$env:POLYNEXUS_TEST_ROOT='C:\PolyNexus-test-runs-saxs-2d-context-green-20260731'
$env:POLYNEXUS_TEST_RETENTION='review'
python -m pytest -q tests/test_saxs_2d_review_context.py tests/test_saxs_workbench_detector_provenance_audit.py tests/test_saxs_2d_review_consumer_propagation.py tests/test_result_table_models.py -o addopts=
```

Expected: complete summary and exit code `0`.

### Task 4: Verify and checkpoint

**Files:**
- Update: `docs/agent/tasks/2026-07-31-saxs-2d-review-context-projection.md`
- Update: `docs/superpowers/specs/2026-07-31-saxs-2d-review-context-projection-design.md`
- Update: `docs/superpowers/plans/2026-07-31-saxs-2d-review-context-projection.md`

- [x] **Step 1: Run the focused and SAXS matrices**

Run the Workbench-focused command above, then:

```powershell
$env:POLYNEXUS_TEST_ROOT='C:\PolyNexus-test-runs-saxs-2d-context-saxs-20260731'
$env:POLYNEXUS_TEST_RETENTION='review'
python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName }) -o addopts=
```

Count only a complete pytest summary with exit code `0`.

- [x] **Step 2: Run structured verification and hygiene checks**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-2d-review-context-projection.md --changed --types
git diff --check
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
```

Storage commands remain dry-run; no `--apply` is part of this task.

- [x] **Step 3: Review the explicit allowlist**

The checkpoint allowlist is exactly:

```text
polynexus/core/saxs_engine/saxs_2d_review_context.py
polynexus/core/saxs_engine/__init__.py
polynexus/gui/result_table_models.py
polynexus/gui/saxs_results_table_service.py
tests/test_saxs_2d_review_context.py
docs/superpowers/specs/2026-07-31-saxs-2d-review-context-projection-design.md
docs/superpowers/plans/2026-07-31-saxs-2d-review-context-projection.md
docs/agent/tasks/2026-07-31-saxs-2d-review-context-projection.md
```

- [x] **Step 4: Create the checkpoint**

```powershell
python scripts/auto_commit.py --message "feat(saxs): project 2d review context" --files polynexus/core/saxs_engine/saxs_2d_review_context.py polynexus/core/saxs_engine/__init__.py polynexus/gui/result_table_models.py polynexus/gui/saxs_results_table_service.py tests/test_saxs_2d_review_context.py docs/superpowers/specs/2026-07-31-saxs-2d-review-context-projection-design.md docs/superpowers/plans/2026-07-31-saxs-2d-review-context-projection.md docs/agent/tasks/2026-07-31-saxs-2d-review-context-projection.md
```
