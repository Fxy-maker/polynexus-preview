# SAXS Existing Review Evidence Synchronization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Synchronize a newly saved SAXS Workbench review into already-published Figure documents through the existing manifest index.

**Architecture:** Keep scientific review data in the existing `AnalysisResult` and SampleDB contracts. Add a core service that uses the structural manifest to locate ready documents, projects review evidence with existing fail-closed rules, and atomically changes only the review provenance field; the GUI only invokes the service after its existing in-memory update.

**Tech Stack:** Python, JSON, dataclasses, PySide6 GUI mixins, pytest, existing SAXS figure evidence and FigurePipeline contracts.

---

### Task 1: Record the task boundary

**Files:**
- Create: `docs/agent/tasks/2026-07-31-saxs-existing-review-sync.md`
- Create: `docs/superpowers/specs/2026-07-31-saxs-existing-review-sync-design.md`
- Create: `docs/superpowers/plans/2026-07-31-saxs-existing-review-sync.md`

- [ ] **Step 1: Review the scope**

Confirm that only existing Figure document review provenance is mutable. The
manifest remains a structural index and no publication or physical gate is
changed.

- [ ] **Step 2: Keep parallel work disjoint**

Before each edit, use `git diff --name-only` and allowlist only the task files
listed in this plan plus the focused test and implementation files below.

### Task 2: Write and verify the RED regression

**Files:**
- Modify: `tests/test_saxs_figure_evidence_binding.py`
- Modify: `tests/test_scientific_review_workbench.py`

- [ ] **Step 1: Add the existing-document test**

Create a Figure run without `scientific_review`, attach its manifest path to a
SAXS engine result, call the same engine review-sync entry point used by the
Workbench, and assert that the linked document contains the accepted review.
Also snapshot the manifest and document fields outside the review subtree.

- [ ] **Step 2: Add fail-closed cases**

Cover a source mismatch and a `cancelled`/missing review. Assert
`allowed is False`, retain the original document fields, and assert the helper
does not raise when the manifest or document is absent.

- [ ] **Step 3: Run the RED test**

Run:

```powershell
python -m pytest -q tests/test_saxs_figure_evidence_binding.py -k existing_review_sync -vv
```

Expected result before production changes: failure because the engine review
sync entry point does not yet update an existing document.

### Task 3: Implement the core synchronization service

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_evidence.py`
- Modify: `polynexus/core/saxs.py`

- [ ] **Step 1: Add a detached sync result**

Add a small JSON-safe result shape containing `status`, `updated_count`,
`skipped_count`, and diagnostic reason codes. It must not expose executable AI
candidate data or mutate input mappings.

- [ ] **Step 2: Resolve only manifest-owned ready documents**

Read the manifest JSON, accept only ready entries with safe run-relative
document paths under the manifest directory, and skip invalid/missing paths.
Do not glob outside the manifest entries and do not follow an arbitrary path
from a document payload.

- [ ] **Step 3: Project review evidence**

Use the existing current frame views and `build_saxs_review_evidence()` with
`expected_scope="saxs.2d"` for detector/orientation entries and
`"saxs.1d"` otherwise. Replace only the existing
`recipe.evidence.quality_provenance.scientific_review` key. Preserve every
other JSON field exactly.

- [ ] **Step 4: Write atomically**

Use the repository's temporary-file plus `os.replace` pattern. A malformed
document is skipped with a diagnostic reason; a single bad document must not
erase the review in other documents.

- [ ] **Step 5: Add the SAXSEngine entry point**

Read `result.metadata["figure_manifest"]`, call the core service with
`frame_views_from_engine(self)`, and return the detached diagnostic result. A
missing path returns a non-raising no-op result.

### Task 4: Connect the Workbench save route

**Files:**
- Modify: `polynexus/gui/main_window_results_mixin.py`
- Modify: `tests/test_scientific_review_workbench.py`

- [ ] **Step 1: Invoke only for SAXS**

After `_apply_scientific_review_to_current_result()` completes, call the cached
SAXS engine's callable sync method when the current technique is SAXS. Do not
branch on technique-specific algorithm state or alter the review persistence
result if synchronization is unavailable.

- [ ] **Step 2: Add route-level regression coverage**

Use a lightweight mixin owner with a cached engine and assert the review is
updated in the existing document. Assert a non-SAXS owner does not call the
SAXS service and that a sync exception is converted to a log/diagnostic path,
not a failed review persistence.

### Task 5: Verify and checkpoint

**Files:**
- Create: `docs/acceptance/2026-07-31-saxs-existing-review-sync.md`
- Create: `docs/agent/memory/lessons/2026-07-31-saxs-existing-review-sync.md`

- [ ] **Step 1: Run focused tests**

Run:

```powershell
$env:POLYNEXUS_TEST_ROOT='C:\PolyNexus-test-runs-saxs-existing-review-sync'
$env:RUFF_CACHE_DIR='C:\PolyNexus-ruff-cache-saxs-existing-review-sync'
$env:PYTHONPYCACHEPREFIX='C:\PolyNexus-pycache-saxs-existing-review-sync'
python -m pytest -q tests/test_saxs_figure_evidence_binding.py tests/test_scientific_review_workbench.py -k 'existing_review_sync or scientific_review' -vv
```

Record the actual result; do not infer a pass from timeout or partial output.

- [ ] **Step 2: Run the exact SAXS matrix**

Use the repository's SAXS test selection and record the exact summary. A
timeout or infrastructure failure is a limitation, not a pass.

- [ ] **Step 3: Run the structured verifier**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-existing-review-sync.md --changed --types
```

- [ ] **Step 4: Inspect storage without mutation**

```powershell
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

Do not use `--apply` and do not delete or move test directories.

- [ ] **Step 5: Create an explicit checkpoint**

After verification, call `scripts/auto_commit.py` with only the source, tests,
task/spec/plan, acceptance, and lesson files changed by this task. Do not stage
memory files modified before this task or any scratch/test-storage directory.
