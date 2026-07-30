# Project Release Decision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an append-only, batch-scoped release decision record and project it through the existing non-SAXS Results/History/Export paths.

**Architecture:** Reuse the immutable `ScientificReviewRecord` with `scope="release"` as the only public schema. Store its validated record and decision snapshot in a dedicated SampleDB table keyed by `batch_id`; hydrate the latest snapshot into run consumers as detached provenance. Add a separate Results Workbench action that targets the current persisted run's batch without changing figure or scientific promotion state.

**Tech Stack:** Python, SQLite, PySide6, pytest, existing PolyNexus review/provenance adapters.

---

### Task 1: Lock the release contract with tests

**Files:**
- Modify: `tests/test_scientific_review.py`
- Modify: `tests/test_scientific_review_workbench.py`

- [ ] **Step 1: Add a failing status/decision consistency test**

Add a test that constructs an accepted `release` record with
`release_decision="conditional"` and asserts `validate_review_record` raises a
`ValueError` mentioning the mismatch. Add a parametrized accepted/conditional/
rejected table proving the matching values are valid.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
python -m pytest -q tests/test_scientific_review.py -k release
```

Expected: the new mismatch test fails because release status/decision
consistency is not yet enforced.

### Task 2: Implement core release validation

**Files:**
- Modify: `polynexus/core/scientific_review.py`

- [ ] **Step 1: Add the minimal release consistency check**

After required decision presence is checked, map `accepted` to `approve`,
`conditional` to `conditional`, and `rejected` to `reject`; raise a
`ValueError` if the supplied `release_decision` differs. Leave pending records
unchanged and preserve all existing non-release scopes.

- [ ] **Step 2: Run the focused core tests and verify GREEN**

Run:

```powershell
python -m pytest -q tests/test_scientific_review.py -k release
```

Expected: all release contract tests pass.

### Task 3: Add append-only SampleDB release storage

**Files:**
- Modify: `polynexus/data/sample_db.py`
- Modify: `tests/test_scientific_review_workbench.py`

- [ ] **Step 1: Add the failing storage round-trip test**

Create a sample and batch, save two validated release records with distinct
record ids, assert both are listed in insertion order, and assert a run lookup
hydrates only the newest snapshot. Assert an unknown batch returns `False` and
does not insert a row.

- [ ] **Step 2: Run the storage test and verify RED**

Run:

```powershell
python -m pytest -q tests/test_scientific_review_workbench.py -k release_storage
```

Expected: failure because the release table and methods do not exist.

- [ ] **Step 3: Implement the table and methods**

Create `scientific_release_reviews` with `record_id` primary key, `batch_id`
foreign key, `record_json`, `snapshot_json`, and `created_at`. Add methods to
append a validated JSON-safe record, list batch records, and return the latest
projection for an analysis run by joining its batch id. Use one transaction and
never update or delete an older record.

- [ ] **Step 4: Run the focused storage tests and verify GREEN**

Run:

```powershell
python -m pytest -q tests/test_scientific_review_workbench.py -k release_storage
```

Expected: all storage tests pass.

### Task 4: Expose the release action in Results Workbench

**Files:**
- Modify: `polynexus/gui/scientific_review_dialog.py`
- Modify: `polynexus/gui/main_window_results_mixin.py`
- Modify: `tests/test_scientific_review_workbench.py`

- [ ] **Step 1: Add the failing Workbench save test**

Build a lightweight mixin instance with `_last_persisted_run_id`, current
batch id, and a fake dialog/DB. Assert the release action sends
`scope="release"`, the current batch id, and the first canonical source ref
to SampleDB; assert it does not call the run-scoped scientific-review update.

- [ ] **Step 2: Run the test and verify RED**

Run:

```powershell
python -m pytest -q tests/test_scientific_review_workbench.py -k release_workbench
```

Expected: failure because no project release action exists.

- [ ] **Step 3: Implement the minimal action**

Add a separate Workbench release button and handler. Require a persisted run
and a non-empty batch id, reuse `ScientificReviewDialog("release")`, validate
the record, build a release snapshot with its first source ref, append it to
SampleDB, update the current result's detached metadata/evidence, and refresh
History/Work memory. Do not alter figure definitions or result values.

- [ ] **Step 4: Run focused GUI tests and verify GREEN**

Run:

```powershell
python -m pytest -q tests/test_scientific_review_workbench.py -k release_workbench
```

Expected: all release Workbench tests pass.

### Task 5: Propagate release provenance to History and Export

**Files:**
- Modify: `polynexus/gui/scientific_review_presentation.py`
- Modify: `polynexus/gui/main_window_history_mixin.py`
- Modify: `polynexus/gui/export_context_service.py`
- Modify: `tests/test_scientific_review_workbench.py`
- Modify: focused export/history tests

- [ ] **Step 1: Add failing consumer tests**

Assert a run with a stored release record displays its record id and decision
in History and includes the exact snapshot in export context. Assert a run
without a record returns `release_missing` and does not appear approved.

- [ ] **Step 2: Run consumer tests and verify RED**

Run the focused test selectors for release history and export. Expected:
`release_missing` or missing snapshot assertions fail before implementation.

- [ ] **Step 3: Implement detached consumer projection**

Add a JSON-safe release display adapter and include the latest batch projection
in restored run payloads and export context. Keep existing scientific-review
display unchanged and keep missing/invalid states fail-closed.

- [ ] **Step 4: Run focused consumer tests and verify GREEN**

Run the same focused selectors and expect all to pass.

### Task 6: Verify and checkpoint

**Files:**
- Modify: `docs/acceptance/2026-07-30-project-release-decision.md`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/tasks/2026-07-30-project-release-decision.md`

- [ ] **Step 1: Run the focused non-SAXS matrix**

Run the exact task-card commands, `git diff --check`, and the relevant
non-SAXS tests. Record actual counts and exit codes; do not count SAXS tests.

- [ ] **Step 2: Run the structured verifier and boundary audit**

Run:

```powershell
python scripts/boundary_audit.py --root D:\PolyNexus --json
python scripts/verify.py --task docs/agent/tasks/2026-07-30-project-release-decision.md --changed --types
```

Record limitations: no scientific values were supplied and final human
approval remains open.

- [ ] **Step 3: Create the explicit checkpoint**

Use `scripts/auto_commit.py` with only the changed release files and tests in
the allowlist. Do not include any SAXS path, pre-existing `current-state.md`
change, or untracked test artifact.
