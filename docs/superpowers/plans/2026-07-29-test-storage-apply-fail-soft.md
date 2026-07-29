# Test-storage apply fail-soft Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make explicit test-storage apply continue safely after individual deletion failures and report partial results truthfully.

**Architecture:** Add immutable `CleanupFailure` and `CleanupApplyResult` records plus `apply_cleanup_detailed`. Keep `apply_cleanup` as a compatibility wrapper returning the existing list of removed paths. The CLI uses the detailed result to emit failures and return exit code `1` when any eligible deletion fails.

**Tech Stack:** Python dataclasses, `pathlib`, `shutil`, pytest, existing storage safety planner, and repository verification scripts.

---

### Task 1: Add failing storage regressions

**Files:**
- Modify: `tests/test_test_storage.py`

- [x] **Step 1: Add the continuation regression**

Create two directories under `tmp_path`, build an eligible plan in insertion
order, monkeypatch `scripts.test_storage.shutil.rmtree` to raise
`PermissionError("locked")` for the first path and call the original remover
for the second. Call `apply_cleanup_detailed(..., apply=True,
approved_roots=[tmp_path])` and assert the first path is absent from `removed`,
the second path is in `removed`, one failure contains the first path and
`PermissionError`, and the second directory no longer exists.

- [x] **Step 2: Add the CLI status/report regression**

Monkeypatch `_build_plan` with the same two-artifact plan and the remover
behavior above, call `main(["clean", "--root", str(tmp_path), "--apply", "--json"])`,
and assert exit code `1`, JSON `failures` contains the locked path, and the
successful path has `removed: true`.

- [x] **Step 3: Run the new tests and confirm RED**

Run:

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PN_storage_apply_fail_soft_red'
python -m pytest -q tests/test_test_storage.py -k "apply and (continues or reports)" -vv
```

Expected result: collection succeeds and the new tests fail because
`apply_cleanup_detailed` and the failure report do not yet exist.

### Task 2: Implement detailed fail-soft apply

**Files:**
- Modify: `scripts/test_storage.py`

- [x] **Step 1: Add immutable result records**

Add `CleanupFailure` and `CleanupApplyResult` dataclasses after
`CleanupDecision`. Use tuples in the result so callers cannot mutate the
recorded outcome, and expose `success` as `not self.failures`.

- [x] **Step 2: Add `apply_cleanup_detailed`**

Move the current safety-gated removal loop into `apply_cleanup_detailed`.
Attempt each eligible path independently; catch `OSError` only around the
individual `shutil.rmtree` call, append a `CleanupFailure`, and continue.
Keep symlink/outside-root paths skipped without creating a deletion failure.

- [x] **Step 3: Preserve the existing helper**

Implement `apply_cleanup` as a wrapper returning `list(apply_cleanup_detailed(...).removed)` so existing library tests and callers retain their current type and behavior.

- [x] **Step 4: Report failure results from the CLI**

Pass the detailed result into `_emit_report`. Add `failures` to JSON and
human-readable output, and return `1` after emitting the report if failures are
present; return `0` for a complete apply or dry-run.

- [x] **Step 5: Run focused GREEN tests**

Run:

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PN_storage_apply_fail_soft_green'
python -m pytest -q tests/test_test_storage.py -k "apply and (continues or reports)"
python -m pytest -q tests/test_test_storage.py
```

Expected result: both commands pass and the CLI regression observes exit code
`1` only for the simulated partial apply.

### Task 3: Verify and checkpoint

**Files:**
- Modify: `scripts/test_storage.py`
- Modify: `tests/test_test_storage.py`
- Add: this task card, design, and plan.

- [x] **Step 1:** Run task-scoped structured verification and `git diff --check`.
- [x] **Step 2:** Run the storage report and dry-run clean commands; do not
  delete real artifacts during this task.
- [x] **Step 3:** Audit the exact five-file allowlist and create one
  `scripts/auto_commit.py` checkpoint without parallel files.
- [x] **Step 4:** Update durable active-work state in a separate allowlisted
  documentation checkpoint with the real failure/verification evidence.

## Verification record

- RED: `1 failed, 27 deselected` for the detailed apply contract and `1 failed,
  28 deselected` for the CLI partial-apply contract.
- GREEN: `2 passed, 27 deselected`; full storage suite `28 passed, 1 skipped`.
- Structured verifier: quality `287`, preprocessing `106`, all selected checks
  passed.
- Storage dry-run: `301` artifacts, `8` eligible bytes, `0` cleanup failures;
  no real deletion was performed by this task.
