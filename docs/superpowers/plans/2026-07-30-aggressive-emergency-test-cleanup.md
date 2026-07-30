# Aggressive Emergency Test Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the test-storage janitor reclaim known disposable test output after a two-hour emergency cooldown when the target volume has less than 10% free space, while preserving review/evidence and active or protected paths.

**Architecture:** Keep `scripts/test_storage.py` as the policy, discovery, reconciliation, reporting, and deletion boundary. Compute current disk pressure while building every cleanup plan, reconcile managed manifests against a supplied active-PID snapshot, and mark only known test-class legacy paths as emergency-eligible. Keep `conftest.py` unchanged except where an existing public contract requires compatibility.

**Tech Stack:** Python 3.12+, `pathlib`, dataclasses, JSON manifests, Windows process inspection, `shutil.disk_usage`, pytest, Ruff, and the repository verifier.

---

## File map

- Modify `scripts/test_storage.py`: emergency decision timing, known legacy discovery, PID reconciliation inputs, report fields, and safety-preserving cleanup behavior.
- Modify `tests/test_test_storage.py`: focused policy, discovery, reconciliation, report, and failure regressions using temporary roots and mocked pressure/process state.
- Modify `AGENTS.md` and `README.md`: document emergency legacy cleanup and the retained safety gates.
- Create `docs/agent/tasks/2026-07-30-aggressive-emergency-test-cleanup.md`: structured task card with allowlist and evidence.
- Create no files outside the task/spec/plan/documentation allowlist and do not edit current scientific-review changes or test output directories.

## Task 1: Extend the artifact decision contract for emergency mode

**Files:**

- Modify: `scripts/test_storage.py`
- Test: `tests/test_test_storage.py`

- [ ] **Step 1: Add failing decision tests.**

Add tests that construct `TestArtifact` values with explicit `finished_at` and
exercise the plan without touching a real drive:

```python
def test_emergency_releases_failed_ephemeral_after_two_hours(tmp_path):
    finished = NOW - timedelta(hours=3)
    artifact = TestArtifact(
        tmp_path / "run-failed",
        "managed",
        100,
        finished,
        profile="ephemeral",
        status="failed",
        finished_at=finished,
        keep_until=NOW + timedelta(hours=21),
    )
    plan = build_cleanup_plan(
        [artifact],
        now=NOW,
        older_than=timedelta(hours=24),
        emergency=True,
    )
    assert plan[artifact].eligible is True
    assert plan[artifact].emergency is True
```

Add companion assertions that a one-hour-old failed ephemeral artifact is not
eligible, and that `review`, `evidence`, active, tracked, protected, and
invalid artifacts remain ineligible even with `emergency=True`.

- [ ] **Step 2: Run the focused tests and confirm the expected RED result.**

Run:

```powershell
python -m pytest -q tests/test_test_storage.py -k "emergency or cleanup_plan"
```

Expected: collection/assertion failures because `TestArtifact` has no
`finished_at`, `CleanupDecision` has no emergency marker, and
`build_cleanup_plan()` does not accept `emergency`.

- [ ] **Step 3: Implement the minimal decision fields and override.**

Add `finished_at: datetime | None = None` to `TestArtifact` and
`emergency: bool = False` to `CleanupDecision`. Extend the function signature:

```python
def build_cleanup_plan(
    artifacts: Iterable[TestArtifact],
    *,
    now: datetime,
    older_than: timedelta,
    emergency: bool = False,
    active_command_lines: Iterable[str] = (),
    tracked_paths: Iterable[Path] = (),
    protected_paths: Iterable[Path] = (),
) -> dict[TestArtifact, CleanupDecision]:
```

Use a two-hour emergency deadline only for failed/interrupted `ephemeral`
artifacts and known legacy artifacts where `artifact.kind` is `legacy` or
`legacy-external` and `manifest_error` is absent. Do not require a non-null
`artifact.profile` for an unmanifested legacy directory. Use `finished_at` for
managed terminal states and `modified_at` for legacy directories. Keep the existing
`evidence`, active, tracked, protected, symlink, invalid-manifest, and passed
ephemeral branches ahead of emergency age evaluation. Set reason to
`eligible (emergency)` and `emergency=True` only when the override is what made
the candidate eligible.

- [ ] **Step 4: Run the GREEN tests and commit the atomic change.**

Run:

```powershell
python -m pytest -q tests/test_test_storage.py -k "emergency or cleanup_plan"
git diff --check
python scripts/auto_commit.py --message "feat(testing): add emergency cleanup decisions" --files scripts/test_storage.py tests/test_test_storage.py
```

Expected: focused tests pass and the commit contains only the two listed
files.

## Task 2: Reconcile manifests and discover known legacy output

**Files:**

- Modify: `scripts/test_storage.py`
- Test: `tests/test_test_storage.py`

- [ ] **Step 1: Add failing lifecycle and discovery tests.**

Add tests that pass an explicit active-PID set to discovery:

```python
def test_discover_reconciles_dead_running_manifest(tmp_path):
    run_path = tmp_path / "test-root" / "pytest" / "run-dead"
    state = begin_run_state(run_path, project_root=tmp_path, profile="ephemeral", now=NOW, pid=1234)
    artifacts = discover_artifacts(
        tmp_path,
        test_root=tmp_path / "test-root",
        legacy_roots=[tmp_path],
        active_pids=set(),
        now=NOW + timedelta(hours=3),
    )
    artifact = next(item for item in artifacts if item.path == run_path)
    assert artifact.status == "interrupted"
    assert artifact.finished_at == NOW + timedelta(hours=3)


def test_discover_keeps_live_running_manifest(tmp_path):
    run_path = tmp_path / "test-root" / "pytest" / "run-live"
    begin_run_state(run_path, project_root=tmp_path, profile="ephemeral", now=NOW, pid=1234)
    artifacts = discover_artifacts(
        tmp_path,
        test_root=tmp_path / "test-root",
        legacy_roots=[tmp_path],
        active_pids={1234},
        now=NOW,
    )
    artifact = next(item for item in artifacts if item.path == run_path)
    assert artifact.status == "running"
```

Add discovery fixtures for `PolyNexus_saxs_demo_matrix`,
`PN_SAXS_MATRIX_X`, and `PolyNexus_demo_pytest`, and assert that names
containing `archive`, `evidence`, or `review` are not included by the
emergency legacy pattern set.

- [ ] **Step 2: Run the tests and confirm the expected RED result.**

Run:

```powershell
python -m pytest -q tests/test_test_storage.py -k "discover or manifest"
```

Expected: failures because discovery has no active-PID/clock parameters, does
not reconcile dead manifests, and does not recognize the new known-test names.

- [ ] **Step 3: Add process and pattern helpers.**

Add a Windows-only `running_process_ids()` helper that returns one set of
integer PIDs from a single process snapshot. On non-Windows systems it returns
an empty set. Extend `discover_artifacts()` with optional `active_pids`, `now`,
and `emergency` parameters; `None` for `active_pids` means no process
reclassification for library callers, while the CLI supplies the snapshot and
current emergency flag.

Add one explicit known-name predicate for configured legacy roots. It accepts
only the documented `PolyNexus_*_matrix*`, `PolyNexus_*_pytest*`,
`PN_*_MATRIX*`, and existing historical temp patterns. It rejects names with
`archive`, `review`, `evidence`, or `baseline` before adding an artifact.

- [ ] **Step 4: Reconcile managed state without deleting during discovery.**

When `active_pids` is supplied, transform a `running` state whose PID is not
present into an in-memory `interrupted` artifact with `finished_at=now` and a
failure deadline computed from the current emergency flag. Keep a live PID as
`running`. Preserve malformed manifests as `manifest-invalid`. Do not write
manifests or remove directories during `report` discovery.

Populate `TestArtifact.finished_at` from valid manifests and preserve all
existing metadata fields.

- [ ] **Step 5: Run the GREEN tests and commit the atomic change.**

Run:

```powershell
python -m pytest -q tests/test_test_storage.py -k "discover or manifest"
git diff --check
python scripts/auto_commit.py --message "feat(testing): reconcile stale test runs" --files scripts/test_storage.py tests/test_test_storage.py
```

Expected: all focused lifecycle and discovery tests pass.

## Task 3: Wire current pressure into the CLI plan and reports

**Files:**

- Modify: `scripts/test_storage.py`
- Test: `tests/test_test_storage.py`

- [ ] **Step 1: Add failing CLI/report tests.**

Mock `emergency_pressure()` and `running_process_ids()` while invoking the
CLI against a temporary test root. Assert that JSON includes:

```python
assert payload["emergency"] is True
assert payload["summary"]["emergency_eligible_bytes"] == 100
assert artifact["emergency"] is True
assert artifact["reason"] == "eligible (emergency)"
```

Add a test that a normal-pressure report keeps the same artifact ineligible
until its ordinary `keep_until` deadline.

- [ ] **Step 2: Run the tests and confirm the expected RED result.**

Run:

```powershell
python -m pytest -q tests/test_test_storage.py -k "report or cli"
```

Expected: failures because `_build_plan()` does not compute pressure or pass
active PIDs, and report summaries do not expose emergency fields.

- [ ] **Step 3: Wire pressure and PIDs through `_build_plan()`.**

Compute `emergency = emergency_pressure(test_root)` once per plan build, call
`running_process_ids()` once, pass both values to discovery and
`build_cleanup_plan()`, and return the emergency flag alongside the existing
project root, plan, and approved roots. Use the managed test root volume even
when no directory exists yet.

- [ ] **Step 4: Extend JSON and human reports.**

Add top-level `emergency`, per-artifact `emergency`, and summary
`emergency_eligible_bytes`/`emergency_eligible_count` fields. Keep existing
fields and make the human report state whether emergency mode is active. The
report must remain read-only.

- [ ] **Step 5: Run the GREEN tests and commit the atomic change.**

Run:

```powershell
python -m pytest -q tests/test_test_storage.py -k "report or cli"
git diff --check
python scripts/auto_commit.py --message "feat(testing): apply emergency pressure during cleanup" --files scripts/test_storage.py tests/test_test_storage.py
```

Expected: CLI/report tests pass and no real drive is touched.

## Task 4: Preserve per-path failure evidence and expand safety regressions

**Files:**

- Modify: `scripts/test_storage.py`
- Test: `tests/test_test_storage.py`

- [ ] **Step 1: Add failure-isolation tests.**

Mock `shutil.rmtree` so one approved eligible path raises `PermissionError`
and the next eligible path succeeds. Assert that the result records one
failure, removes the other path, and does not raise before reporting all
results. Add tests for symlink and outside-approved-root rejection under
emergency mode.

- [ ] **Step 2: Run the tests and confirm the expected RED result.**

Run:

```powershell
python -m pytest -q tests/test_test_storage.py -k "cleanup or safety or failure"
```

Expected: the new failure-isolation and emergency safety assertions fail
until the detailed apply/report contract is complete.

- [ ] **Step 3: Keep deletion gates independent and report failures.**

Ensure `apply_cleanup_detailed()` re-resolves every path immediately before
deletion, rejects symlinks and outside roots, continues after `OSError`, and
returns the exact path, exception type, and message for each failure. Keep the
compatibility wrapper returning only removed paths. Expose failure records in
JSON and human output, and return exit code `1` when apply has any failure.

- [ ] **Step 4: Run the GREEN safety tests and commit the atomic change.**

Run:

```powershell
python -m pytest -q tests/test_test_storage.py -k "cleanup or safety or failure"
git diff --check
python scripts/auto_commit.py --message "feat(testing): report emergency cleanup failures" --files scripts/test_storage.py tests/test_test_storage.py
```

Expected: all focused safety tests pass without modifying real storage.

## Task 5: Document operation and create the structured task card

**Files:**

- Modify: `AGENTS.md`
- Modify: `README.md`
- Create: `docs/agent/tasks/2026-07-30-aggressive-emergency-test-cleanup.md`

- [ ] **Step 1: Document the emergency contract.**

Update both operator documents to state that below 10% free space, known
test-class legacy and failed/interrupted ephemeral paths older than two hours
may be cleaned. State that review/evidence, live, tracked, protected,
symlinked, invalid, unknown, and archive-like paths remain protected. Include
the dry-run and explicit `--apply` commands and explain that the first real
emergency apply must be reviewed from JSON output.

- [ ] **Step 2: Create the task card with the exact allowlist.**

Create the task card with goal, non-goals, affected boundaries, acceptance
criteria, verification commands, pre-existing changes, and this allowlist:

- `scripts/test_storage.py`
- `tests/test_test_storage.py`
- `AGENTS.md`
- `README.md`
- `docs/agent/tasks/2026-07-30-aggressive-emergency-test-cleanup.md`
- `docs/superpowers/specs/2026-07-30-aggressive-emergency-test-cleanup-design.md`
- `docs/superpowers/plans/2026-07-30-aggressive-emergency-test-cleanup.md`

- [ ] **Step 3: Validate and commit documentation.**

Run:

```powershell
python scripts/task_check.py --task docs/agent/tasks/2026-07-30-aggressive-emergency-test-cleanup.md
git diff --check
python scripts/auto_commit.py --message "docs(testing): document emergency cleanup policy" --files AGENTS.md README.md docs/agent/tasks/2026-07-30-aggressive-emergency-test-cleanup.md
```

Expected: task card valid and documentation checkpoint contains only its
three listed files.

## Task 6: Final verification without real emergency deletion

**Files:**

- No source edits; use the task allowlist from Task 5.

- [ ] **Step 1: Stop or wait for active pytest before verification.**

Confirm no active Python/pytest process is writing the managed test root. Do
not terminate a scientific or review run automatically; record its PID as a
blocker if it is still active.

- [ ] **Step 2: Run the focused storage matrix.**

Run:

```powershell
python -m pytest -q tests/test_test_storage.py
```

Expected: all storage tests pass. Test output must use an external temporary
root and no command may use the real emergency `--apply` path.

- [ ] **Step 3: Run the repository verifier and task checks.**

Run:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-30-aggressive-emergency-test-cleanup.md --changed --types
python scripts/task_check.py --task docs/agent/tasks/2026-07-30-aggressive-emergency-test-cleanup.md
git diff --check
```

Expected: exit code `0` for the verifier, valid task card, and no whitespace
errors. Report exact quality/preprocessing counts.

- [ ] **Step 4: Run real storage reporting only.**

Run:

```powershell
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
```

Summarize emergency status, ordinary/emergency eligible bytes, active
references, and failure records. Do not run `--apply` against real C: or D:
data in this task.

- [ ] **Step 5: Commit final task evidence.**

Update the task card with exact verification results and use an explicit
allowlist checkpoint. Do not include existing scientific-review changes,
memory edits, worktrees, or generated test directories.

## Handoff

After this plan is approved, execute it inline with
`superpowers:executing-plans` or use fresh subagents with
`superpowers:subagent-driven-development`. The first emergency deletion on a
real volume remains a separate explicit operation after reviewing its JSON
inventory.
