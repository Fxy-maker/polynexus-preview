# Aggressive Test Storage Lifecycle Design

## Goal

Prevent pytest output from filling C: and D: while preserving the small set of
artifacts needed for debugging, GUI review, real-data review, and release
acceptance.

## Context

The repository already assigns ordinary pytest runs to an external basetemp and
has a dry-run-first storage scanner. The current 24-hour cleanup policy is too
slow for the current test volume: D: is near capacity and historical basetemp
directories exist on both drives. The new design must remove disposable output
at the end of a successful ordinary test run instead of waiting for a periodic
cleanup.

## Non-goals

- Do not delete source files, real regression datasets, worktrees, Codex data,
  or system-managed files.
- Do not infer that a test result is scientific or release evidence merely
  because pytest exits with code 0.
- Do not delete evidence directories automatically.
- Do not introduce a background Windows service in the first implementation.

## Retention policy

Every managed run has one retention profile and one terminal outcome.

| Profile | Passed | Failed or interrupted | Intended use |
|---|---:|---:|---|
| `ephemeral` | Delete after pytest releases the directory | Keep 24 hours | Ordinary unit, integration, quality, and preprocessing tests |
| `review` | Keep 7 days | Keep 7 days | GUI, native, performance, or real-data review runs |
| `evidence` | Keep permanently | Keep permanently | Release, acceptance, and explicit `quality_evidence` runs |
| `legacy` | Keep until the 24-hour safe-cleanup sweep | Keep until the 24-hour safe-cleanup sweep | Existing directories without a run manifest |

`ephemeral` is the default for new ordinary pytest runs. A caller opts into a
longer profile with `POLYNEXUS_TEST_RETENTION=review` or
`POLYNEXUS_TEST_RETENTION=evidence`. The explicit setting must be recorded in
the run manifest and must override name-based guesses. Unknown values fail
closed to `review`, not `ephemeral`.

When the free space on the target volume falls below 10%, emergency cleanup
may shorten `ephemeral` failure retention from 24 hours to 2 hours. It must
never shorten `review` or `evidence`, and it must never remove a running,
tracked, protected, or user-owned path.

## Lifecycle

```text
created -> running -> passed -> removed (ephemeral)
                    |        -> retained (review/evidence)
                    -> failed/interrupted -> retained until profile deadline
```

At run creation, the storage helper writes a small `run_state.json` beside the
basetemp. It contains only operational metadata:

- schema version and run ID;
- absolute artifact path and storage volume;
- PID and process start time;
- Git HEAD and repository root;
- task identifier when supplied;
- retention profile, status, exit code, timestamps, and keep-until time.

At pytest session finish, the root `conftest.py` records the terminal outcome.
For a passed `ephemeral` run it attempts immediate removal only after pytest
has released its own files. If Windows still reports a lock, it records
`cleanup_pending` and leaves the directory for the normal janitor. A process
crash or forced termination leaves the manifest in `running`; the janitor
reclassifies it as `interrupted` only after confirming that the recorded
process and its child processes no longer exist.

## Safety gates

Immediate removal and scheduled cleanup share the same independent gates:

1. The path is under the managed external test root or matches an exact
   registered legacy prefix.
2. The resolved path is not a symlink and remains inside the approved root.
3. No live process or child process references the path.
4. The path is not Git-tracked and is not inside a protected dataset,
   baseline, evidence, or worktree path.
5. The manifest's recorded path, profile, status, and Git HEAD still match the
   filesystem and current run registry.
6. The retention deadline has elapsed, except for passed `ephemeral` runs
   whose terminal cleanup is explicitly authorized by the profile.
7. A failed safety check produces a report reason and never falls back to
   deletion.

The existing dry-run/report commands remain the authoritative inspection path.
`--apply` remains mandatory for janitor deletion, while pytest's immediate
`ephemeral` cleanup is limited to the run directory it created and owns.

## Legacy migration

Existing C: and D: directories without manifests remain `legacy`; their result
cannot be guessed from directory names. The first migration pass will:

1. report counts, sizes, ages, active references, and protected reasons;
2. preserve anything active, dirty, tracked, or evidence-like;
3. delete only unreferenced legacy directories past the 24-hour cooldown after
   an explicit `--apply` run;
4. leave branches, source worktrees, and unknown non-test directories alone.

Future pytest runs will use the lifecycle manifest and will not join this
unknown legacy pool.

## Implementation boundaries

- `scripts/test_storage.py`: profiles, manifest schema, discovery, status
  reconciliation, emergency threshold, and shared deletion gates.
- `conftest.py`: create the manifest and perform owned `ephemeral` terminal
  cleanup without changing explicit `--basetemp` semantics.
- `tests/test_test_storage.py`: profile resolution, manifest transitions,
  active-process protection, failure retention, emergency behavior, and
  symlink/root-boundary rejection.
- `README.md` and `AGENTS.md`: document the profiles, opt-in evidence command,
  emergency behavior, and legacy migration procedure.
- `docs/agent/tasks/`: implementation task card with the exact allowlist.

## Verification requirements

The implementation must demonstrate:

- a passed `ephemeral` run is removed after the session releases its files;
- a failed/interrupted run remains with a manifest and expiry deadline;
- `review` and `evidence` are never removed by automatic cleanup;
- active, tracked, protected, symlinked, and outside-root paths are rejected;
- emergency mode removes only eligible `ephemeral` artifacts;
- legacy dry-run remains non-destructive;
- `python scripts/verify.py --changed --types` passes with exact output
  reported before checkpointing.

This design does not authorize the first legacy migration deletion. That action
will use a separately reviewed dry-run report and the explicit `--apply` flag.
