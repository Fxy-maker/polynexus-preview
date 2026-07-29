---
kind: task
status: completed
date: 2026-07-29
title: Automate aggressive pytest test-storage lifecycle
---

# Aggressive pytest test-storage lifecycle

## Goal

Prevent ordinary pytest output from accumulating on C: and D: while retaining
failed runs, review artifacts, explicit evidence, and unknown legacy output
according to a recorded policy.

## Non-goals

- Do not delete or move existing C: or D: legacy directories during this task.
- Do not infer scientific, release, or acceptance evidence from a pytest exit
  code or directory name.
- Do not delete source files, real datasets, worktrees, Codex data, or
  user-owned paths.
- Do not add a background service or an autonomous AI coding runner.

## Affected boundaries

- `conftest.py`: create and finalize manifests for automatically-created
  basetemps; remove only a successful owned `ephemeral` run.
- `scripts/test_storage.py`: retention policy, manifest discovery, cleanup
  decisions, JSON/human reports, and approved-root deletion gates.
- `tests/test_test_storage.py`: lifecycle, safety, profile, discovery, and
  report regressions.
- `AGENTS.md` and `README.md`: operator-facing storage contract.
- `docs/agent/tasks/2026-07-29-aggressive-test-storage.md`: this acceptance
  record.

## Retention contract

| Profile | Passed | Failed/interrupted |
| --- | --- | --- |
| `ephemeral` | remove after pytest releases the exact owned run | 24 hours |
| `review` | 7 days | 7 days |
| `evidence` | permanent | permanent |
| `legacy` | 24-hour janitor cooldown | 24-hour janitor cooldown |

`ephemeral` is the default. `POLYNEXUS_TEST_RETENTION` selects a profile;
unknown values resolve to `review`. Below 10% free space, only failed or
interrupted `ephemeral` runs may use a two-hour deadline.

## Implementation plan

1. Add retention profiles and a JSON run-state manifest for managed pytest
   basetemps.
2. Register only automatically-created basetemps from `conftest.py`, finalize
   their outcome, and remove successful owned ephemeral runs after teardown.
3. Add interruption reconciliation, emergency-pressure deadlines, and shared
   cleanup gates for symlink and approved-root safety.
4. Extend discovery and reports with manifest metadata and profile/reason/byte
   summaries while keeping CLI cleanup dry-run by default.
5. Document the operator contract, run the storage matrix and structured
   verifier, and record a read-only legacy inventory.

## Acceptance criteria

- [x] Managed runs write operational `run_state.json` metadata.
- [x] Successful owned ephemeral runs are removed after pytest teardown;
  explicit `--basetemp` runs remain untouched.
- [x] Failed, interrupted, review, and evidence runs follow their profile
  deadlines and evidence is never auto-deleted.
- [x] Cleanup rejects active, tracked, protected, symlinked, invalid-manifest,
  and outside-approved-root paths.
- [x] CLI JSON and human reports include manifest metadata plus total bytes,
  eligible bytes, and profile/reason summaries.
- [x] Documentation and task checks pass.
- [x] The full storage matrix and repository verifier pass.
- [x] A real legacy inventory is recorded in dry-run mode without deletion.

## Verification

```powershell
python -m pytest -q tests/test_test_storage.py
python scripts/task_check.py --task docs/agent/tasks/2026-07-29-aggressive-test-storage.md
python scripts/verify.py --task docs/agent/tasks/2026-07-29-aggressive-test-storage.md --changed --types
git diff --check
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
```

The legacy commands are read-only until a separately reviewed concrete
inventory is explicitly authorized with `--apply`.

## Explicit changed-file allowlist

- `conftest.py`
- `scripts/test_storage.py`
- `tests/test_test_storage.py`
- `AGENTS.md`
- `README.md`
- `docs/agent/tasks/2026-07-29-aggressive-test-storage.md`

## Explicit exclusions

Existing pytest output, real datasets, worktrees, `.superpowers/`,
`docs/agent/memory/current-state.md`, and unrelated task/spec/plan files are
outside this task's allowlist and remain untouched.

## Pre-existing workspace changes

The shared worktree already contains unrelated modified memory/source files,
many untracked pytest output directories, `.superpowers/`, and historical task
artifacts. They must remain outside the atomic checkpoint.

## Checkpoints

- `f685908`: retention profiles and run-state contract.
- `6d7290c`: pytest lifecycle registration and owned ephemeral cleanup.
- `6ed7700`: safety gates, emergency pressure, and interruption reconciliation.
- `a305d37`: discovery, profile-aware cleanup, approved roots, and reports.

## Verification evidence

- Storage regression: `26 passed, 1 skipped in 1.32s`.
- Task check: valid task card, exit code `0`.
- Structured verifier: exit code `0`; memory check passed, Ruff and compile
  passed, quality gate `287 passed`, preprocessing gate `106 passed`, and
  whitespace check passed.
- Legacy report dry-run: `350` artifacts, `34,812,315,097` total bytes,
  `19,128,640,281` eligible bytes before active-process revalidation.
- Legacy clean dry-run: `350` artifacts, `34,812,315,097` total bytes,
  `19,128,640,281` eligible bytes, `49` eligible artifacts, `9` active-process
  references, and `removed: []`.
- No `--apply` cleanup, migration, move, push, merge, or deployment was run.
