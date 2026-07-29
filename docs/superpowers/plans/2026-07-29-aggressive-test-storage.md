# Aggressive Test Storage Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make ordinary successful pytest runs delete their own disposable
basetemp immediately while retaining failures, review artifacts, and evidence
according to explicit profiles.

**Architecture:** Keep `scripts/test_storage.py` as the single policy and
safety boundary. The root `conftest.py` creates a manifest for agent-owned
basetemps and finalizes it at pytest shutdown; it may only delete the run it
created. The CLI remains the dry-run-first janitor for failed, interrupted, and
legacy directories.

**Tech Stack:** Python 3.12+, pytest hooks, `pathlib`, JSON manifests,
Windows process inspection, `shutil.disk_usage`, pytest, Ruff, and the
repository verifier.

---

## Task 1: Add retention profiles and run-state contracts

**Files:**

- Modify: `scripts/test_storage.py`
- Test: `tests/test_test_storage.py`

- [ ] **Step 1: Write failing profile-resolution tests.**

Add tests for the public behavior below:

```python
def test_resolve_retention_profile_defaults_to_ephemeral():
    assert resolve_retention_profile({}) == "ephemeral"


def test_resolve_retention_profile_accepts_review_and_evidence():
    assert resolve_retention_profile({"POLYNEXUS_TEST_RETENTION": "review"}) == "review"
    assert resolve_retention_profile({"POLYNEXUS_TEST_RETENTION": "evidence"}) == "evidence"


def test_resolve_retention_profile_fails_closed_to_review():
    assert resolve_retention_profile({"POLYNEXUS_TEST_RETENTION": "unknown"}) == "review"
```

Run:

```powershell
python -m pytest -q tests/test_test_storage.py -k retention_profile
```

Expected: collection or assertion failures because the resolver and profile
contracts do not exist yet.

- [ ] **Step 2: Define the minimal policy and manifest types.**

Add these stable values and data shapes to `scripts/test_storage.py`:

```python
RETENTION_ENV = "POLYNEXUS_TEST_RETENTION"
RETENTION_PROFILES = {"ephemeral", "review", "evidence", "legacy"}


@dataclass(frozen=True)
class RetentionPolicy:
    name: str
    success_after: timedelta | None
    failure_after: timedelta | None


@dataclass(frozen=True)
class RunState:
    schema_version: int
    run_id: str
    path: Path
    project_root: Path
    git_head: str
    pid: int
    process_started_at: datetime
    profile: str
    status: str
    exit_code: int | None
    created_at: datetime
    finished_at: datetime | None
    keep_until: datetime | None
```

Use this policy table:

```python
RETENTION_POLICIES = {
    "ephemeral": RetentionPolicy("ephemeral", None, timedelta(hours=24)),
    "review": RetentionPolicy("review", timedelta(days=7), timedelta(days=7)),
    "evidence": RetentionPolicy("evidence", None, None),
    "legacy": RetentionPolicy("legacy", timedelta(hours=24), timedelta(hours=24)),
}
```

`None` means no automatic expiry. Unknown environment values must resolve to
`review`. Add `run_state_path()`, `write_run_state()`, and
`read_run_state()` using ISO-8601 UTC timestamps and JSON-safe strings; never
serialize secrets, raw logs, or test payloads.

- [ ] **Step 3: Run the focused tests and round-trip coverage.**

Add a temporary `RunState` round-trip test using `tmp_path`, then run:

```powershell
python -m pytest -q tests/test_test_storage.py -k "retention_profile or run_state"
```

Expected: all new profile and manifest tests pass.

- [ ] **Step 4: Create the atomic checkpoint.**

```powershell
python scripts/auto_commit.py `
  --message "feat(testing): add retention state contracts" `
  --files scripts/test_storage.py tests/test_test_storage.py
```

## Task 2: Register and finalize agent-owned pytest runs

**Files:**

- Modify: `conftest.py`
- Modify: `scripts/test_storage.py`
- Test: `tests/test_test_storage.py`

- [ ] **Step 1: Write failing lifecycle tests.**

Test the policy boundary without launching a real large suite:

```python
def test_finalize_run_removes_owned_ephemeral_success(tmp_path, monkeypatch):
    run = begin_run_state(tmp_path, project_root=tmp_path, profile="ephemeral")
    finalize_run_state(run, exit_code=0, now=NOW, process_active=False)
    assert not run.path.exists()


def test_finalize_run_keeps_ephemeral_failure_with_deadline(tmp_path):
    run = begin_run_state(tmp_path, project_root=tmp_path, profile="ephemeral")
    finalize_run_state(run, exit_code=1, now=NOW, process_active=False)
    state = read_run_state(run.path)
    assert state.status == "failed"
    assert state.keep_until == NOW + timedelta(hours=24)


def test_finalize_run_never_removes_evidence(tmp_path):
    run = begin_run_state(tmp_path, project_root=tmp_path, profile="evidence")
    finalize_run_state(run, exit_code=0, now=NOW, process_active=False)
    assert run.path.exists()
```

Run the new tests and confirm the expected failures before implementation.

- [ ] **Step 2: Register only automatically-created basetemps.**

In `conftest.py`, preserve the existing explicit `--basetemp` branch exactly.
For an absent basetemp, create the external run directory, write a `running`
manifest, and retain the state on the pytest config object:

```python
def pytest_configure(config) -> None:
    if getattr(config.option, "basetemp", None) is not None:
        return
    base = create_run_basetemp(Path(__file__).resolve().parent)
    config.option.basetemp = str(base)
    config._polynexus_run_state = begin_run_state(
        base,
        project_root=Path(__file__).resolve().parent,
        profile=resolve_retention_profile(),
    )
```

Add `pytest_sessionfinish()` to store the exit code and `pytest_unconfigure()`
to call `finalize_run_state()` after fixtures and test execution have ended.
Only the config-owned path may receive immediate `ephemeral` cleanup. If
Windows reports a lock, write `cleanup_pending` and leave the run to the CLI
janitor; never retry by deleting a parent directory.

- [ ] **Step 3: Verify lifecycle and explicit-basetemp compatibility.**

Run:

```powershell
python -m pytest -q tests/test_test_storage.py -k "finalize_run or explicit_basetemp or pytest_hook"
```

Expected: passed ephemeral runs disappear, failed/evidence runs remain, and an
explicit `--basetemp` is still untouched.

- [ ] **Step 4: Create the atomic checkpoint.**

```powershell
python scripts/auto_commit.py `
  --message "feat(testing): finalize owned pytest runs" `
  --files conftest.py scripts/test_storage.py tests/test_test_storage.py
```

## Task 3: Harden shared cleanup gates and emergency pressure behavior

**Files:**

- Modify: `scripts/test_storage.py`
- Test: `tests/test_test_storage.py`

- [ ] **Step 1: Write failing safety and pressure tests.**

Cover these exact cases:

```python
def test_cleanup_rejects_symlinked_artifact(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    artifact = TestArtifact(link, "managed", 1, NOW - timedelta(days=2))

    removed = apply_cleanup(
        {artifact: CleanupDecision(eligible=True, reason="test")},
        apply=True,
        approved_roots=[tmp_path],
    )

    assert removed == []
    assert target.exists()


def test_cleanup_rejects_path_outside_approved_root(tmp_path):
    outside = tmp_path.parent / "outside"
    outside.mkdir()
    artifact = TestArtifact(outside, "managed", 1, NOW - timedelta(days=2))

    removed = apply_cleanup(
        {artifact: CleanupDecision(eligible=True, reason="test")},
        apply=True,
        approved_roots=[tmp_path],
    )

    assert removed == []
    assert outside.exists()


def test_emergency_mode_shortens_only_ephemeral_failure_deadline():
    assert failure_deadline("ephemeral", NOW, emergency=True) == NOW + timedelta(hours=2)


def test_emergency_mode_never_removes_review_or_evidence():
    assert failure_deadline("review", NOW, emergency=True) == NOW + timedelta(days=7)
    assert failure_deadline("evidence", NOW, emergency=True) is None


def test_running_manifest_becomes_interrupted_only_after_process_exit(tmp_path):
    run = begin_run_state(tmp_path, project_root=tmp_path, profile="ephemeral")
    assert reconcile_run_state(run, process_active=True).status == "running"
    assert reconcile_run_state(run, process_active=False).status == "interrupted"
```

Use `monkeypatch` for `shutil.disk_usage` and process inspection; tests must
not inspect or delete the real C: or D: roots.

- [ ] **Step 2: Add root and process revalidation.**

Extend the shared cleanup decision to require an approved-root list, reject
symlinks, and re-resolve the candidate immediately before deletion. Preserve
the existing tracked/protected/active-process reasons. `apply_cleanup()` must
refuse a candidate when its resolved path is outside the approved root even if
the caller supplied `eligible=True`.

- [ ] **Step 3: Add volume-pressure policy.**

Implement a helper with this contract:

```python
def emergency_pressure(path: Path, *, threshold: float = 0.10) -> bool:
    usage = shutil.disk_usage(path.anchor or path)
    return usage.free / usage.total < threshold
```

When pressure is true, only `ephemeral` failures may use a two-hour deadline.
`review`, `evidence`, active, tracked, protected, symlinked, and legacy paths
remain governed by their normal safety rules.

- [ ] **Step 4: Run focused safety tests and commit.**

```powershell
python -m pytest -q tests/test_test_storage.py -k "safety or emergency or interrupted"
python scripts/auto_commit.py `
  --message "feat(testing): harden storage cleanup gates" `
  --files scripts/test_storage.py tests/test_test_storage.py
```

## Task 4: Extend discovery, reports, and the CLI janitor

**Files:**

- Modify: `scripts/test_storage.py`
- Test: `tests/test_test_storage.py`

- [ ] **Step 1: Write failing discovery/report tests.**

Add managed-run fixtures containing `run_state.json` and assert that report
records include `profile`, `status`, `exit_code`, `keep_until`, and `reason`.
Add a legacy fixture without a manifest and assert that it remains `legacy`.

- [ ] **Step 2: Reconcile manifests during discovery.**

Extend `TestArtifact` with optional profile/status/keep-until fields with
backward-compatible defaults. `discover_artifacts()` reads only the manifest
metadata for managed runs; it still computes directory size and modified time
for reporting. A malformed manifest yields `manifest-invalid` and is never
eligible for deletion.

- [ ] **Step 3: Apply profile-aware cleanup decisions.**

`build_cleanup_plan()` must use manifest status and profile before age checks:

```text
evidence                         -> protected: evidence profile
review before 7 days             -> younger than retention
ephemeral passed                 -> eligible only for owned terminal cleanup
ephemeral failed before 24 hours -> younger than retention
legacy before 24 hours           -> younger than retention
manifest invalid or missing path -> protected: invalid manifest
```

Keep `report` dry-run and keep `clean --apply` as the only CLI deletion path.
Add a summary section to JSON and human output with total bytes, eligible
bytes, and counts by profile/reason.

- [ ] **Step 4: Verify the CLI without touching real storage.**

Run against a temporary root:

```powershell
$storageSandbox = Join-Path $env:TEMP "polynexus-storage-plan-cli"
$testSandbox = Join-Path $storageSandbox "test-root"
New-Item -ItemType Directory -Force -Path $testSandbox | Out-Null
python scripts/test_storage.py report --root $storageSandbox --test-root $testSandbox --json
python scripts/test_storage.py clean --root $storageSandbox --test-root $testSandbox --older-than-hours 24
```

Expected: report is non-destructive and the clean command remains dry-run.

- [ ] **Step 5: Create the atomic checkpoint.**

```powershell
python scripts/auto_commit.py `
  --message "feat(testing): add profile-aware storage janitor" `
  --files scripts/test_storage.py tests/test_test_storage.py
```

## Task 5: Document operation and prepare legacy migration

**Files:**

- Modify: `AGENTS.md`
- Modify: `README.md`
- Create: `docs/agent/tasks/2026-07-29-aggressive-test-storage.md`

- [ ] **Step 1: Add the operator contract.**

Document the four profiles, the environment variable, the emergency threshold,
and the distinction between owned immediate cleanup and CLI `--apply` cleanup.
Include these commands:

```powershell
$env:POLYNEXUS_TEST_RETENTION="review"
pytest tests/test_gui_route.py

python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
python scripts/test_storage.py clean --older-than-hours 24 --apply
```

Document that existing C:/D: legacy directories are not assigned a guessed
passed/failed result and require the legacy dry-run migration.

- [ ] **Step 2: Create the structured task card.**

The task card must list the exact changed-file allowlist, acceptance criteria,
and verification commands. It must explicitly exclude existing test output,
real datasets, worktrees, and memory files with unrelated user changes.

- [ ] **Step 3: Run documentation and task checks.**

```powershell
python scripts/task_check.py --task docs/agent/tasks/2026-07-29-aggressive-test-storage.md
git diff --check
```

- [ ] **Step 4: Create the documentation checkpoint.**

```powershell
python scripts/auto_commit.py `
  --message "docs(testing): document retention profiles" `
  --files AGENTS.md README.md docs/agent/tasks/2026-07-29-aggressive-test-storage.md
```

## Task 6: Final verification and legacy migration dry-run

**Files:**

- No source edits; use the task allowlist from the task card.

- [ ] **Step 1: Run the focused storage matrix.**

```powershell
python -m pytest -q tests/test_test_storage.py
```

Expected: all storage tests pass, with ordinary pytest output placed under the
external D: test root and the successful ephemeral run cleaned after teardown.

- [ ] **Step 2: Run the prescribed repository verifier.**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-29-aggressive-test-storage.md --changed --types
```

Record the exact quality/preprocessing counts and exit code. Do not claim a
full/boundary pass unless that exact command is separately run to completion.

- [ ] **Step 3: Inspect the real legacy inventory in dry-run mode.**

```powershell
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
```

Review eligible paths and total bytes. Do not run `--apply` in this task until
the user separately authorizes the concrete inventory; the design only
authorizes the implementation and a non-destructive migration report.

- [ ] **Step 4: Create the final allowlisted checkpoint.**

```powershell
python scripts/auto_commit.py `
  --message "feat(testing): automate aggressive test storage lifecycle" `
  --files conftest.py scripts/test_storage.py tests/test_test_storage.py AGENTS.md README.md docs/agent/tasks/2026-07-29-aggressive-test-storage.md
```

## Handoff

After this plan is approved, choose one execution mode:

1. **Subagent-driven:** dispatch one fresh worker per task and review each
   checkpoint before the next task.
2. **Inline:** execute the tasks in this session with verification after each
   checkpoint.

The first legacy deletion remains a separate explicit operation after the
final dry-run inventory is reviewed.
